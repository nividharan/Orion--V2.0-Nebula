"""
verify/page_watcher.py — Phase 6: Page Verification & Screen Watcher
=====================================================================
Perception & Verification Engine:
1. DOM-state checks: error pages (404/500/503), unexpected popups/dialogs, login redirects.
2. Page screenshot hash diff: detect no-change-after-action, frozen page.
3. Vision fallback only if inconclusive, strictly cropped, NEVER on login/payment pages.
4. Structured Verdict: {verdict: ok|uncertain|fail, evidence: dict}.
5. Save images ONLY on fail/uncertain, auto-delete after 24h.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from config import CACHE_DIR, TRACES_DIR

logger = logging.getLogger("Orion.PageWatcher")


class Verdict(str, Enum):
    OK = "ok"
    UNCERTAIN = "uncertain"
    FAIL = "fail"


@dataclass
class WatchResult:
    """Structured report returned by PageWatcher."""
    verdict: Verdict
    signal: str  # ok, no_change, frozen, error_page, dialog_detected, login_redirect
    evidence: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value if isinstance(self.verdict, Verdict) else str(self.verdict),
            "signal": self.signal,
            "evidence": self.evidence,
            "screenshot_path": self.screenshot_path,
        }


# Error page indicator patterns in DOM text or title
ERROR_PAGE_PATTERNS = [
    r"404\s+not\s+found",
    r"page\s+not\s+found",
    r"500\s+internal\s+server\s+error",
    r"502\s+bad\s+gateway",
    r"503\s+service\s+unavailable",
    r"access\s+denied",
    r"403\s+forbidden",
    r"server\s+error",
    r"an\s+unexpected\s+error\s+has\s+occurred",
]

# Sensitive login / payment patterns where Vision must NEVER run
SENSITIVE_VISION_BLOCK_KEYWORDS = [
    "password", "cvv", "credit card", "billing", "signin", "login", "checkout", "payment"
]


def _compute_image_hash(image_bytes: bytes) -> str:
    """Fast SHA-256 over raw image bytes as deterministic visual hash."""
    if not image_bytes:
        return ""
    return hashlib.sha256(image_bytes).hexdigest()


def _calculate_pixel_delta_pct(hash1: str, hash2: str) -> float:
    """Calculates difference metric between two image hashes."""
    if not hash1 or not hash2:
        return 100.0
    if hash1 == hash2:
        return 0.0
    max_len = max(len(hash1), len(hash2))
    diff = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    diff += abs(len(hash1) - len(hash2))
    return round((diff / max(max_len, 1)) * 100.0, 2)


def calculate_visual_diff_pct(bytes1: Optional[bytes], bytes2: Optional[bytes]) -> float:
    """
    Calculates perceptual normalized difference percentage between two image buffers (0.0% to 100.0%).
    Uses Pillow 16x16 grayscale pixel downsampling with SHA-256 fallback.
    """
    if not bytes1 or not bytes2:
        return 100.0
    if bytes1 == bytes2:
        return 0.0
    try:
        from PIL import Image
        t1 = Image.open(io.BytesIO(bytes1)).convert("L").resize((16, 16)).tobytes()
        t2 = Image.open(io.BytesIO(bytes2)).convert("L").resize((16, 16)).tobytes()
        diff = sum(abs(a - b) for a, b in zip(t1, t2))
        return round((diff / (len(t1) * 255.0)) * 100.0, 2)
    except Exception:
        h1 = hashlib.sha256(bytes1).hexdigest()
        h2 = hashlib.sha256(bytes2).hexdigest()
        return 0.0 if h1 == h2 else 100.0


class PageWatcher:
    """
    Watches page DOM state and visual diffs to detect failures, stalls, and unexpected states.
    """

    def __init__(
        self,
        retention_hours: float = 24.0,
        artifacts_dir: Optional[Path] = None,
        vision_enabled: bool = False
    ):
        self.retention_hours = retention_hours
        self.artifacts_dir = artifacts_dir or (CACHE_DIR / "watcher_artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.vision_enabled = vision_enabled
        self._last_hash: Optional[str] = None
        self._last_capture_time: float = 0.0

    def cleanup_old_images(self) -> int:
        """Deletes watcher images older than retention_hours (24 hours)."""
        cutoff = time.time() - (self.retention_hours * 3600)
        deleted = 0
        try:
            for item in self.artifacts_dir.glob("*.png"):
                if item.stat().st_mtime < cutoff:
                    item.unlink(missing_ok=True)
                    deleted += 1
        except Exception as e:
            logger.warning(f"Error cleaning watcher images: {e}")
        return deleted

    def check_dom_state(self, page: Any) -> Tuple[Verdict, str, Dict[str, Any]]:
        """
        Stage 1: Deterministic DOM checks.
        Detects error pages, unexpected dialogs, and login redirects.
        """
        if not page or (callable(getattr(page, "is_closed", None)) and page.is_closed()):
            return Verdict.FAIL, "page_closed", {"reason": "Page is closed or crashed"}

        url = ""
        title = ""
        try:
            url = getattr(page, "url", "") or ""
            title = page.title() if callable(getattr(page, "title", None)) else (getattr(page, "title", "") or "")
        except Exception:
            return Verdict.FAIL, "page_crashed", {"reason": "Page communication failed"}

        evidence: Dict[str, Any] = {"url": url, "title": title}

        # 1. Login redirect check
        login_indicators = ["/login", "/signin", "/auth/login", "/session/new", "/challenge", "accounts.google.com"]
        if any(ind in url.lower() for ind in login_indicators):
            return Verdict.FAIL, "login_redirect", {**evidence, "detail": f"Redirected to login: {url}"}

        # Check for visible password field
        try:
            pwd_locator = page.locator("input[type='password']")
            count = pwd_locator.count() if callable(getattr(pwd_locator, "count", None)) else 0
            if count > 0:
                all_pwds = list(pwd_locator.all()) if callable(getattr(pwd_locator, "all", None)) else []
                if all_pwds:
                    visible_pwds = [p for p in all_pwds if (p.is_visible() if callable(getattr(p, "is_visible", None)) else True)]
                    if visible_pwds:
                        return Verdict.FAIL, "login_redirect", {**evidence, "detail": "Visible password field present on page"}
                else:
                    return Verdict.FAIL, "login_redirect", {**evidence, "detail": "Password field present on page"}
        except Exception:
            pass

        # 2. Error page check (title + body text)
        title_low = title.lower()
        for pat in ERROR_PAGE_PATTERNS:
            if re.search(pat, title_low):
                return Verdict.FAIL, "error_page", {**evidence, "detail": f"Error pattern '{pat}' found in title"}

        try:
            body_locator = page.locator("body")
            body_text = (body_locator.inner_text() if callable(getattr(body_locator, "inner_text", None)) else "")[:4000].lower()
            for pat in ERROR_PAGE_PATTERNS:
                if re.search(pat, body_text):
                    return Verdict.FAIL, "error_page", {**evidence, "detail": f"Error pattern '{pat}' found in body"}
        except Exception:
            pass

        # 3. Unexpected dialog / modal check
        try:
            dialogs = page.locator("[role='dialog'], [aria-modal='true'], .modal-open, tp-yt-paper-dialog")
            all_dialogs = dialogs.all() if callable(getattr(dialogs, "all", None)) else []
            visible_dialogs = [d for d in all_dialogs if (d.is_visible() if callable(getattr(d, "is_visible", None)) else True)]
            if visible_dialogs:
                modal_text = (visible_dialogs[0].inner_text() if callable(getattr(visible_dialogs[0], "inner_text", None)) else "")[:300]
                return Verdict.FAIL, "dialog_detected", {**evidence, "modal_sample": modal_text}
        except Exception:
            pass

        return Verdict.OK, "ok", evidence

    def verify_action_result(
        self,
        page: Any,
        before_screenshot: Optional[bytes] = None,
        after_screenshot: Optional[bytes] = None,
        expect_visual_change: bool = True
    ) -> WatchResult:
        """
        Stage 2: Combined DOM check and page-screenshot hash diff.
        Detects no-change-after-action or frozen pages.
        """
        self.cleanup_old_images()

        # Step 1: DOM Check
        dom_verdict, signal, evidence = self.check_dom_state(page)
        if dom_verdict == Verdict.FAIL:
            shot_path = self._maybe_save_image(page, after_screenshot, f"fail_{signal}")
            return WatchResult(verdict=Verdict.FAIL, signal=signal, evidence=evidence, screenshot_path=shot_path)

        # Step 2: Visual Hash Diff
        if before_screenshot and after_screenshot:
            delta = calculate_visual_diff_pct(before_screenshot, after_screenshot)
            evidence["hash_delta"] = delta
            evidence["before_hash"] = _compute_image_hash(before_screenshot)
            evidence["after_hash"] = _compute_image_hash(after_screenshot)

            if expect_visual_change and delta == 0.0:
                # No change detected after action was executed!
                shot_path = self._maybe_save_image(page, after_screenshot, "fail_no_change")
                return WatchResult(
                    verdict=Verdict.FAIL,
                    signal="no_change",
                    evidence={**evidence, "detail": "Screenshot identical before and after action"},
                    screenshot_path=shot_path
                )

        # Step 3: Vision fallback (only if inconclusive and allowed)
        if self.vision_enabled and not self._is_sensitive_page(page):
            vision_verdict = self._run_vision_heuristic(page)
            if vision_verdict != Verdict.OK:
                shot_path = self._maybe_save_image(page, after_screenshot, "uncertain_vision")
                return WatchResult(
                    verdict=vision_verdict,
                    signal="vision_inconclusive",
                    evidence=evidence,
                    screenshot_path=shot_path
                )

        # Verdict OK: Do NOT save screenshot (zero disk bloat on success)
        return WatchResult(verdict=Verdict.OK, signal="ok", evidence=evidence, screenshot_path=None)

    def watch_page_action(
        self,
        page: Any,
        action: Optional[Callable[[], Any]] = None,
        expect_visual_change: bool = True,
    ) -> WatchResult:
        """
        Executes an action callable surrounded by before/after perception captures
        and returns a structured WatchResult verdict.
        """
        before_bytes = None
        if page and callable(getattr(page, "screenshot", None)):
            try:
                before_bytes = page.screenshot()
            except Exception:
                pass

        if action:
            action()

        after_bytes = None
        if page and callable(getattr(page, "screenshot", None)):
            try:
                after_bytes = page.screenshot()
            except Exception:
                pass

        return self.verify_action_result(
            page,
            before_screenshot=before_bytes,
            after_screenshot=after_bytes,
            expect_visual_change=expect_visual_change,
        )

    def detect_frozen_page(self, frame_bytes_history: List[bytes], interval_sec: float = 1.0) -> WatchResult:
        """Detects if multiple consecutive frames over time are completely static."""
        if len(frame_bytes_history) < 2:
            return WatchResult(verdict=Verdict.OK, signal="ok")

        all_identical = all(
            calculate_visual_diff_pct(frame_bytes_history[0], f) == 0.0
            for f in frame_bytes_history[1:]
        )

        if all_identical:
            saved_path = None
            if frame_bytes_history:
                dest = self.artifacts_dir / f"fail_frozen_{int(time.time()*1000)}.png"
                dest.write_bytes(frame_bytes_history[-1])
                saved_path = str(dest)
            return WatchResult(
                verdict=Verdict.FAIL,
                signal="frozen",
                evidence={"duration_sec": len(frame_bytes_history) * interval_sec, "frames": len(frame_bytes_history)},
                screenshot_path=saved_path
            )

        return WatchResult(verdict=Verdict.OK, signal="ok")

    def _is_sensitive_page(self, page: Any) -> bool:
        """Redaction guard: Checks if current page has password or payment fields."""
        try:
            url = getattr(page, "url", "").lower()
            title = (page.title() if callable(getattr(page, "title", None)) else getattr(page, "title", "")).lower()
            for kw in SENSITIVE_VISION_BLOCK_KEYWORDS:
                if kw in url or kw in title:
                    return True
            try:
                pwd_loc = page.locator("input[type='password']")
                if (pwd_loc.count() if callable(getattr(pwd_loc, "count", None)) else 0) > 0:
                    return True
            except Exception:
                pass
            try:
                cc_loc = page.locator("input[autocomplete='cc-number']")
                if (cc_loc.count() if callable(getattr(cc_loc, "count", None)) else 0) > 0:
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _run_vision_heuristic(self, page: Any) -> Verdict:
        """Crop-only vision check (stubbed for safety; never runs on sensitive pages)."""
        return Verdict.OK

    def _maybe_save_image(self, page: Any, image_bytes: Optional[bytes], prefix: str) -> Optional[str]:
        """Saves image to artifacts only on failure/uncertain state."""
        try:
            data = image_bytes
            if not data and page and not (callable(getattr(page, "is_closed", None)) and page.is_closed()):
                if callable(getattr(page, "screenshot", None)):
                    data = page.screenshot()
            if data:
                filename = f"{prefix}_{int(time.time()*1000)}.png"
                dest = self.artifacts_dir / filename
                dest.write_bytes(data)
                return str(dest)
        except Exception as e:
            logger.warning(f"Could not save watcher image: {e}")
        return None
