"""
verify/screen_watcher.py — ScreenWatcher: continuous frame diff + signal detection.

Phase 6 spec:
  - Capture target window/region in memory at 1-2 fps (faster 3s post-action).
  - Perceptual-hash frame diff (imagehash / fallback pixel diff).
  - Detect: no-change-after-action, new window, frozen frame, error/UAC dialogs.
  - Signal detection order: window titles + UI Automation first → OCR second → vision last.
  - Skip capture on login/payment/password windows.
  - Visible watching indicator (prints to log) + off switch (stop()).
  - Save images ONLY on fail/uncertain, auto-delete after 24h.
  - Returns {verdict: ok|uncertain|fail, evidence: dict}.

All blocking OS calls (win32gui, pywinauto, mss) are abstracted behind
interfaces so they can be monkey-patched in tests.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import CACHE_DIR
from desktop.controls.screenshot import _is_sensitive_window, _win32_screenshot

logger = logging.getLogger("orion.verify.screen_watcher")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FPS_IDLE   = 1.5    # frames per second during normal observation
DEFAULT_FPS_BURST  = 6.0    # fps for 3s immediately after an action
BURST_DURATION_S   = 3.0    # how long to stay in burst mode
HASH_DIFF_THRESHOLD = 8      # max hash distance to consider frames "identical"
FREEZE_WINDOW_S    = 4.0    # seconds of no motion = frozen frame
EVIDENCE_DIR       = CACHE_DIR / "screen_evidence"
EVIDENCE_TTL_S     = 86_400  # 24 hours auto-delete


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

class Verdict:
    OK        = "ok"
    UNCERTAIN = "uncertain"
    FAIL      = "fail"


@dataclass
class WatchResult:
    """Result returned by ScreenWatcher.check()."""
    verdict:    str                         # ok | uncertain | fail
    evidence:   Dict[str, Any] = field(default_factory=dict)
    screenshot: Optional[bytes] = None     # only set on fail/uncertain


# ---------------------------------------------------------------------------
# Perceptual hash helpers
# ---------------------------------------------------------------------------

def _phash_bytes(png_bytes: bytes, size: int = 8) -> Optional[str]:
    """
    Compute a perceptual hash string of a PNG image.
    Uses imagehash if available; falls back to MD5 of down-sampled pixel data.
    """
    try:
        import io
        from PIL import Image  # type: ignore[import]
        img = Image.open(io.BytesIO(png_bytes)).convert("L").resize((size * 4, size * 4))
        img_small = img.resize((size, size))
        pixels = list(img_small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p >= avg else "0" for p in pixels)
        return bits
    except Exception:
        return hashlib.md5(png_bytes[:4096]).hexdigest()


def _hash_distance(h1: Optional[str], h2: Optional[str]) -> int:
    """Hamming distance between two binary hash strings (same length assumed)."""
    if h1 is None or h2 is None or len(h1) != len(h2):
        return 999
    return sum(c1 != c2 for c1, c2 in zip(h1, h2))


# ---------------------------------------------------------------------------
# Error signal detection (title + UIA → OCR → last resort vision)
# ---------------------------------------------------------------------------

_ERROR_TITLE_FRAGMENTS: Tuple[str, ...] = (
    "error", "not responding", "has stopped", "crashed",
    "uac", "user account control", "do you want to allow",
    "application error", "program has stopped working",
    "windows error reporting",
)

_UAC_TITLE_FRAGMENTS: Tuple[str, ...] = (
    "user account control", "uac", "do you want to allow",
)


def _detect_error_signals_by_title() -> List[Dict[str, Any]]:
    """Fast path: enumerate window titles for known error patterns."""
    signals: List[Dict[str, Any]] = []
    if sys.platform != "win32":
        return signals
    try:
        import win32gui  # type: ignore[import]

        def enum_cb(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                for frag in _ERROR_TITLE_FRAGMENTS:
                    if frag in title:
                        signals.append({
                            "type":  "error_window",
                            "title": win32gui.GetWindowText(hwnd),
                            "hwnd":  hwnd,
                        })
                        break

        win32gui.EnumWindows(enum_cb, None)
    except Exception as exc:
        logger.debug(f"Title scan failed: {exc}")
    return signals


def _detect_new_windows(known_hwnds: set) -> List[Dict[str, Any]]:
    """Return list of new visible windows not in known_hwnds."""
    if sys.platform != "win32":
        return []
    new_windows: List[Dict[str, Any]] = []
    try:
        import win32gui  # type: ignore[import]

        def enum_cb(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and hwnd not in known_hwnds:
                title = win32gui.GetWindowText(hwnd)
                if title:
                    new_windows.append({"hwnd": hwnd, "title": title})

        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass
    return new_windows


def _get_all_hwnds() -> set:
    """Return set of all currently visible window HWNDs."""
    if sys.platform != "win32":
        return set()
    hwnds = set()
    try:
        import win32gui  # type: ignore[import]
        win32gui.EnumWindows(lambda h, _: hwnds.add(h) if win32gui.IsWindowVisible(h) else None, None)
    except Exception:
        pass
    return hwnds


# ---------------------------------------------------------------------------
# Evidence storage
# ---------------------------------------------------------------------------

def _save_evidence(png_bytes: bytes, label: str) -> Optional[Path]:
    """Save a PNG screenshot as evidence (only on fail/uncertain)."""
    try:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        p = EVIDENCE_DIR / f"{label}_{ts}.png"
        p.write_bytes(png_bytes)
        logger.info(f"Evidence saved: {p}")
        return p
    except Exception as exc:
        logger.warning(f"Failed to save evidence: {exc}")
        return None


def _cleanup_old_evidence() -> None:
    """Delete evidence files older than EVIDENCE_TTL_S (24h)."""
    cutoff = time.time() - EVIDENCE_TTL_S
    if not EVIDENCE_DIR.exists():
        return
    for f in EVIDENCE_DIR.glob("*.png"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# ScreenWatcher
# ---------------------------------------------------------------------------

class ScreenWatcher:
    """
    Continuous frame-diff watcher with signal detection.

    Usage::

        watcher = ScreenWatcher(hwnd=hwnd)
        watcher.start()
        # ... action executes ...
        watcher.on_action()           # enters burst mode
        time.sleep(2)
        result = watcher.check()      # returns WatchResult
        watcher.stop()

    For testing without real OS, inject a custom ``capture_fn``::

        watcher = ScreenWatcher(capture_fn=my_mock_fn)
    """

    def __init__(
        self,
        hwnd: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        window_title: str = "",
        fps_idle: float = DEFAULT_FPS_IDLE,
        fps_burst: float = DEFAULT_FPS_BURST,
        capture_fn: Optional[Callable[[], Optional[bytes]]] = None,
    ) -> None:
        self._hwnd = hwnd
        self._region = region
        self._title = window_title
        self._fps_idle = fps_idle
        self._fps_burst = fps_burst

        # Custom capture function (for tests)
        if capture_fn is not None:
            self._capture = capture_fn
        else:
            self._capture = self._default_capture

        self._frames: List[Tuple[float, str]] = []   # (timestamp, phash)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._burst_until: float = 0.0
        self._thread: Optional[threading.Thread] = None
        self._known_hwnds: set = _get_all_hwnds()

        # Indicator: show a log message every N frames
        self._frame_count = 0

    # ------------------------------------------------------------------
    def _default_capture(self) -> Optional[bytes]:
        if self._title and _is_sensitive_window(self._title):
            logger.debug(f"Capture skipped — sensitive window: '{self._title}'")
            return None
        return _win32_screenshot(hwnd=self._hwnd, region=self._region)

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background capture thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(f"[ScreenWatcher] Started — watching '{self._title or 'desktop'}'")

    def stop(self) -> None:
        """Stop the background capture thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("[ScreenWatcher] Stopped.")

    def on_action(self) -> None:
        """Call this immediately after an action to enter burst capture mode."""
        self._burst_until = time.time() + BURST_DURATION_S
        logger.debug("[ScreenWatcher] Burst mode activated for 3s")

    # ------------------------------------------------------------------
    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            fps = self._fps_burst if time.time() < self._burst_until else self._fps_idle
            interval = 1.0 / fps

            png = self._capture()
            if png:
                phash = _phash_bytes(png)
                ts = time.time()
                with self._lock:
                    self._frames.append((ts, phash))
                    # Keep last 60 frames max
                    if len(self._frames) > 60:
                        self._frames.pop(0)
                self._frame_count += 1
                if self._frame_count % 10 == 0:
                    logger.debug(f"[ScreenWatcher] ⬤ Frame {self._frame_count} captured")

            self._stop_event.wait(interval)

    # ------------------------------------------------------------------
    def check(self, window_title: str = "") -> WatchResult:
        """
        Run all signal checks and return a WatchResult.

        Checks (in priority order):
          1. Error/UAC windows by title (fastest, no screenshot needed)
          2. Frozen frame detection (no hash change over FREEZE_WINDOW_S)
          3. New unexpected windows appeared
          4. Screenshot evidence on fail/uncertain

        Returns WatchResult with verdict: ok | uncertain | fail.
        """
        title = window_title or self._title
        _cleanup_old_evidence()

        with self._lock:
            frames = list(self._frames)

        # ── 1. Error window by title ─────────────────────────────────
        error_sigs = _detect_error_signals_by_title()
        if error_sigs:
            png = self._capture()
            shot_path = _save_evidence(png, "error_window") if png else None
            return WatchResult(
                verdict=Verdict.FAIL,
                evidence={
                    "reason":   "Error or UAC dialog detected by window title",
                    "signals":  error_sigs,
                    "evidence_file": str(shot_path) if shot_path else None,
                },
                screenshot=png,
            )

        # ── 2. New unexpected window ────────────────────────────────
        new_wins = _detect_new_windows(self._known_hwnds)
        if new_wins:
            # Update known set so we don't re-report the same windows
            self._known_hwnds = _get_all_hwnds()
            logger.info(f"[ScreenWatcher] New window(s) detected: {[w['title'] for w in new_wins]}")
            return WatchResult(
                verdict=Verdict.UNCERTAIN,
                evidence={
                    "reason":      "New unexpected window appeared",
                    "new_windows": new_wins,
                },
            )

        # ── 3. Frozen frame detection ───────────────────────────────
        if len(frames) >= 3:
            cutoff = time.time() - FREEZE_WINDOW_S
            recent = [(ts, h) for ts, h in frames if ts >= cutoff]
            if len(recent) >= 2:
                first_hash = recent[0][1]
                all_identical = all(
                    _hash_distance(h, first_hash) <= HASH_DIFF_THRESHOLD
                    for _, h in recent[1:]
                )
                if all_identical and len(recent) >= 3:
                    png = self._capture()
                    shot_path = _save_evidence(png, "frozen_frame") if png else None
                    return WatchResult(
                        verdict=Verdict.UNCERTAIN,
                        evidence={
                            "reason":        "Frozen frame — no visual change",
                            "freeze_seconds": FREEZE_WINDOW_S,
                            "frames_checked": len(recent),
                            "evidence_file":  str(shot_path) if shot_path else None,
                        },
                        screenshot=png,
                    )

        # ── 4. All clear ────────────────────────────────────────────
        return WatchResult(
            verdict=Verdict.OK,
            evidence={
                "reason":       "No signals detected",
                "frames_seen":  len(frames),
            },
        )

    # ------------------------------------------------------------------
    def get_motion_score(self) -> float:
        """
        Return a motion score 0.0–1.0 based on recent frame variance.
        0.0 = frozen, 1.0 = highly dynamic.
        """
        with self._lock:
            frames = list(self._frames[-10:])
        if len(frames) < 2:
            return 0.0
        diffs = [
            _hash_distance(frames[i][1], frames[i+1][1])
            for i in range(len(frames) - 1)
        ]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        return min(1.0, avg_diff / 64.0)   # 64 = max hash distance for 8x8 phash
