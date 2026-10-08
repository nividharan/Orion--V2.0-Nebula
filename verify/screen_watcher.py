"""
Continuous Screen Watcher & Freeze Detector for Orion & Nebula.
Phase 3 Implementation:
- Pre- and post-action perceptual hash (pHash) diffing to detect dead clicks.
- Rolling freeze detector across multi-frame observation windows.
- Browser crash banner & unresponsive tab detector ("Aw, Snap!", "STATUS_ACCESS_VIOLATION").
- Universal multi-surface perception (Playwright Web & Native Desktop HWND).
"""

import asyncio
import io
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from verify.page_watcher import PageWatcher, WatchResult, Verdict, calculate_visual_diff_pct

logger = logging.getLogger("nebula.screen_watcher")

CRASH_BANNER_PATTERNS = [
    r"aw,\s+snap!",
    r"status_access_violation",
    r"he's\s+dead,\s+jim!",
    r"result_code_killed",
    r"page\s+unresponsive",
    r"out\s+of\s+memory",
    r"err_connection_refused",
    r"err_name_not_resolved",
]


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


@dataclass
class FreezeReport:
    """Outcome of a viewport freeze check."""
    is_frozen: bool
    frames_captured: int
    duration_sec: float
    max_delta_pct: float
    crashed: bool
    crash_reason: Optional[str] = None


class CrashBannerDetector:
    """Scans web page DOM, window title, or text buffers for browser crash banners."""

    @classmethod
    def check_crash(cls, text_or_title: str) -> Tuple[bool, Optional[str]]:
        lowered = text_or_title.lower()
        for pat in CRASH_BANNER_PATTERNS:
            if re.search(pat, lowered):
                return True, pat
        return False, None


class FreezeDetector:
    """
    Monitors a viewport over an observation window to detect frozen rendering pipelines
    (e.g., stalled video playback, locked 3D viewports, or frozen loading spinners).
    """

    def __init__(self, sample_interval_sec: float = 0.5, freeze_threshold_pct: float = 0.05):
        self.sample_interval = sample_interval_sec
        self.freeze_threshold = freeze_threshold_pct

    async def check_surface_activity(
        self,
        capture_fn: Callable[[], Any],
        duration_sec: float = 2.0,
        page_or_text: Optional[Any] = None
    ) -> FreezeReport:
        """
        Samples the viewport at regular intervals. If visual delta across all frames remains
        below the freeze threshold, reports is_frozen=True.
        """
        start_time = time.perf_counter()
        frames: List[bytes] = []

        # Check for crash banner first
        if page_or_text:
            text_sample = ""
            if isinstance(page_or_text, str):
                text_sample = page_or_text
            elif hasattr(page_or_text, "title"):
                try:
                    title_res = page_or_text.title()
                    text_sample = await title_res if asyncio.iscoroutine(title_res) else str(title_res)
                except Exception:
                    pass

            crashed, reason = CrashBannerDetector.check_crash(text_sample)
            if crashed:
                return FreezeReport(
                    is_frozen=True,
                    frames_captured=0,
                    duration_sec=0.0,
                    max_delta_pct=0.0,
                    crashed=True,
                    crash_reason=f"Crash banner detected: {reason}"
                )

        while (time.perf_counter() - start_time) < duration_sec:
            try:
                frame = capture_fn()
                if asyncio.iscoroutine(frame):
                    frame = await frame
                if frame and isinstance(frame, bytes):
                    frames.append(frame)
            except Exception as e:
                logger.debug("Frame capture failed during freeze check: %s", e)
            await asyncio.sleep(self.sample_interval)

        if len(frames) < 2:
            return FreezeReport(
                is_frozen=False,
                frames_captured=len(frames),
                duration_sec=time.perf_counter() - start_time,
                max_delta_pct=0.0,
                crashed=False,
                crash_reason="Insufficient frames to evaluate"
            )

        # Compute deltas between successive frames
        max_delta = 0.0
        for i in range(1, len(frames)):
            delta = calculate_visual_diff_pct(frames[i - 1], frames[i])
            if delta > max_delta:
                max_delta = delta

        is_frozen = max_delta < self.freeze_threshold
        elapsed = time.perf_counter() - start_time

        return FreezeReport(
            is_frozen=is_frozen,
            frames_captured=len(frames),
            duration_sec=elapsed,
            max_delta_pct=max_delta,
            crashed=False,
            crash_reason=None if not is_frozen else f"Visual delta ({max_delta:.2f}%) did not change over {elapsed:.1f}s"
        )


class ScreenWatcher:
    """
    Continuous visual supervisor comparing pre- and post-action visual states
    to confirm whether DOM and desktop interactions produced actual rendering changes.
    """

    def __init__(self, page_watcher: Optional[PageWatcher] = None, dead_click_threshold_pct: float = 0.5):
        self.page_watcher = page_watcher or PageWatcher()
        self.dead_click_threshold = dead_click_threshold_pct
        self.freeze_detector = FreezeDetector()

    async def capture_page_bytes(self, page: Any) -> Optional[bytes]:
        """Safely captures screenshot bytes from active Playwright page or desktop window."""
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
