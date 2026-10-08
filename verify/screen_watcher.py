"""
Continuous Screen Watcher & Dead-Click Detector for Nebula Web Engine.
Captures pre- and post-action visual state, computes perceptual differences,
and flags dead clicks, frozen pages, or browser crash screens.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from verify.page_watcher import PageWatcher, WatchResult, Verdict, calculate_visual_diff_pct

logger = logging.getLogger("nebula.screen_watcher")


@dataclass
class ActionPerceptionResult:
    """Outcome of an action evaluated under continuous visual perception."""
    success: bool
    dead_click: bool
    visual_delta_pct: float
    verdict: Verdict
    signal: str
    elapsed_sec: float
    detail: Optional[str] = None


class ScreenWatcher:
    """
    Continuous visual supervisor that compares pre- and post-action visual states
    to confirm whether DOM interactions produced actual rendering changes.
    """

    def __init__(self, page_watcher: Optional[PageWatcher] = None, dead_click_threshold_pct: float = 0.5):
        self.page_watcher = page_watcher or PageWatcher()
        self.dead_click_threshold = dead_click_threshold_pct

    async def capture_page_bytes(self, page: Any) -> Optional[bytes]:
        """Safely captures screenshot bytes from the active page."""
        try:
            if hasattr(page, "screenshot"):
                shot = page.screenshot(type="png", timeout=5000)
                if asyncio.iscoroutine(shot):
                    return await shot
                return shot
            return None
        except Exception as e:
            logger.debug("Failed to capture page screenshot: %s", e)
            return None

    async def observe_action(
        self,
        page: Any,
        action_coro_or_fn: Callable[[], Any],
        expect_visual_change: bool = True,
        settle_time_sec: float = 0.5
    ) -> ActionPerceptionResult:
        """
        Executes an action wrapped in baseline and post-action perceptual captures.
        Evaluates whether a dead-click occurred or if the page froze.
        """
        start_time = time.perf_counter()

        # Step 1: Pre-action baseline snapshot
        before_bytes = await self.capture_page_bytes(page)

        # Step 2: Execute the action
        try:
            if asyncio.iscoroutinefunction(action_coro_or_fn) or asyncio.iscoroutine(action_coro_or_fn):
                await action_coro_or_fn() if callable(action_coro_or_fn) else await action_coro_or_fn
            elif callable(action_coro_or_fn):
                action_coro_or_fn()
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error("Action execution raised exception: %s", e)
            return ActionPerceptionResult(
                success=False,
                dead_click=False,
                visual_delta_pct=0.0,
                verdict=Verdict.FAIL,
                signal="action_exception",
                elapsed_sec=elapsed,
                detail=str(e)
            )

        # Allow DOM rendering / paint loop to settle
        if settle_time_sec > 0:
            await asyncio.sleep(settle_time_sec)

        # Step 3: Post-action snapshot
        after_bytes = await self.capture_page_bytes(page)
        elapsed = time.perf_counter() - start_time

        # Step 4: Calculate visual diff
        delta_pct = 0.0
        if before_bytes and after_bytes:
            delta_pct = calculate_visual_diff_pct(before_bytes, after_bytes)

        # Step 5: Evaluate via PageWatcher (DOM + crash checks)
        watch_result = self.page_watcher.verify_action_result(
            page,
            before_screenshot=before_bytes,
            after_screenshot=after_bytes,
            expect_visual_change=expect_visual_change
        )

        dead_click = False
        if expect_visual_change and (delta_pct < self.dead_click_threshold or watch_result.signal == "no_change"):
            dead_click = True
            return ActionPerceptionResult(
                success=False,
                dead_click=True,
                visual_delta_pct=delta_pct,
                verdict=Verdict.UNCERTAIN,
                signal="dead_click_detected",
                elapsed_sec=elapsed,
                detail=f"Visual delta ({delta_pct:.2f}%) below threshold ({self.dead_click_threshold}%). Click may have been swallowed."
            )

        return ActionPerceptionResult(
            success=(watch_result.verdict == Verdict.OK),
            dead_click=dead_click,
            visual_delta_pct=delta_pct,
            verdict=watch_result.verdict,
            signal=watch_result.signal,
            elapsed_sec=elapsed,
            detail=watch_result.evidence.get("detail")
        )
