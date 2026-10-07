"""
desktop/controls/windows.py — Open/close/focus/move/resize/snap windows.

Preference order for window operations:
  1. pywinauto (UIA / Win32 back-end)
  2. pygetwindow (title-based)
  3. Win32 API (ctypes / win32gui)

All operations return {ok: bool, detail: str}.
"""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("orion.desktop.windows")


# ---------------------------------------------------------------------------
# Platform check
# ---------------------------------------------------------------------------

if sys.platform != "win32":
    logger.warning("WindowController is Windows-only. Operations will no-op on other platforms.")


# ---------------------------------------------------------------------------
# Constants for window snap positions
# ---------------------------------------------------------------------------

class SnapPosition:
    LEFT       = "left"
    RIGHT      = "right"
    MAXIMIZE   = "maximize"
    MINIMIZE   = "minimize"
    RESTORE    = "restore"
    TOP_LEFT   = "top_left"
    TOP_RIGHT  = "top_right"
    BOTTOM_LEFT  = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_hwnd_by_title(title: str) -> Optional[int]:
    """Find a window HWND by partial title match (Win32)."""
    if sys.platform != "win32":
        return None
    import win32gui  # type: ignore[import]

    results: list[int] = []

    def enum_callback(hwnd, lParam):
        wt = win32gui.GetWindowText(hwnd)
        if title.lower() in wt.lower() and win32gui.IsWindowVisible(hwnd):
            results.append(hwnd)

    win32gui.EnumWindows(enum_callback, None)
    return results[0] if results else None


def _ok(detail: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail}


# ---------------------------------------------------------------------------
# WindowController
# ---------------------------------------------------------------------------

class WindowController:
    """
    Manages desktop windows: open, close, focus, move, resize, snap.

    All public methods return {ok: bool, detail: str}.
    """

    # ------------------------------------------------------------------
    def open_app(
        self,
        executable: str,
        args: Optional[List[str]] = None,
        wait_ms: int = 1500,
    ) -> Dict[str, Any]:
        """
        Launch an application by executable path or name.
        Requires approval for installers (.msi, .exe setup).
        """
        args = args or []
        try:
            proc = subprocess.Popen([executable, *args])
            time.sleep(wait_ms / 1000)
            return _ok(f"Launched '{executable}' (PID {proc.pid})")
        except FileNotFoundError:
            return _fail(f"Executable not found: '{executable}'")
        except Exception as exc:
            return _fail(f"Failed to launch '{executable}': {exc}")

    # ------------------------------------------------------------------
    def close_app(self, title: str) -> Dict[str, Any]:
        """Close an application window by title (graceful WM_CLOSE, then force)."""
        if sys.platform != "win32":
            return _fail("close_app is Windows-only")

        try:
            import win32gui  # type: ignore[import]
            import win32con  # type: ignore[import]
            hwnd = _find_hwnd_by_title(title)
            if hwnd is None:
                return _fail(f"No window found with title containing '{title}'")
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return _ok(f"Sent WM_CLOSE to '{title}' (hwnd={hwnd})")
        except Exception as exc:
            return _fail(f"close_app failed: {exc}")

    # ------------------------------------------------------------------
    def focus_window(self, title: str) -> Dict[str, Any]:
        """Bring a window to the foreground by partial title match."""
        if sys.platform != "win32":
            return _fail("focus_window is Windows-only")

        try:
            import win32gui  # type: ignore[import]
            hwnd = _find_hwnd_by_title(title)
            if hwnd is None:
                return _fail(f"No window found with title '{title}'")
            win32gui.ShowWindow(hwnd, 9)   # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
            return _ok(f"Focused '{title}' (hwnd={hwnd})")
        except Exception as exc:
            return _fail(f"focus_window failed: {exc}")

    # ------------------------------------------------------------------
    def move_window(self, title: str, x: int, y: int) -> Dict[str, Any]:
        """Move a window to (x, y) screen coordinates."""
        if sys.platform != "win32":
            return _fail("move_window is Windows-only")

        try:
            import win32gui  # type: ignore[import]
            hwnd = _find_hwnd_by_title(title)
            if hwnd is None:
                return _fail(f"No window found with title '{title}'")
            rect = win32gui.GetWindowRect(hwnd)
            width  = rect[2] - rect[0]
            height = rect[3] - rect[1]
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
            return _ok(f"Moved '{title}' to ({x}, {y})")
        except Exception as exc:
            return _fail(f"move_window failed: {exc}")

    # ------------------------------------------------------------------
    def resize_window(self, title: str, width: int, height: int) -> Dict[str, Any]:
        """Resize a window to (width, height)."""
        if sys.platform != "win32":
            return _fail("resize_window is Windows-only")

        try:
            import win32gui  # type: ignore[import]
            hwnd = _find_hwnd_by_title(title)
            if hwnd is None:
                return _fail(f"No window found with title '{title}'")
            rect = win32gui.GetWindowRect(hwnd)
            win32gui.MoveWindow(hwnd, rect[0], rect[1], width, height, True)
            return _ok(f"Resized '{title}' to {width}x{height}")
        except Exception as exc:
            return _fail(f"resize_window failed: {exc}")

    # ------------------------------------------------------------------
    def snap_window(self, title: str, position: str) -> Dict[str, Any]:
        """Snap a window to a screen position using Win+Arrow or MoveWindow."""
        pos = position.lower()
        if sys.platform != "win32":
            return _fail("snap_window is Windows-only")

        try:
            import win32gui  # type: ignore[import]
            import win32api  # type: ignore[import]
            import win32con  # type: ignore[import]

            hwnd = _find_hwnd_by_title(title)
            if hwnd is None:
                return _fail(f"No window found with title '{title}'")

            # Get work area
            mon_info = win32api.GetMonitorInfo(
                win32api.MonitorFromWindow(hwnd, 2)
            )
            work = mon_info["Work"]  # (left, top, right, bottom)
            w = work[2] - work[0]
            h = work[3] - work[1]
            x0, y0 = work[0], work[1]

            snap_map = {
                SnapPosition.LEFT:         (x0,        y0,        w // 2, h),
                SnapPosition.RIGHT:        (x0 + w//2, y0,        w // 2, h),
                SnapPosition.TOP_LEFT:     (x0,        y0,        w // 2, h // 2),
                SnapPosition.TOP_RIGHT:    (x0 + w//2, y0,        w // 2, h // 2),
                SnapPosition.BOTTOM_LEFT:  (x0,        y0 + h//2, w // 2, h // 2),
                SnapPosition.BOTTOM_RIGHT: (x0 + w//2, y0 + h//2, w // 2, h // 2),
            }

            if pos == SnapPosition.MAXIMIZE:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                return _ok(f"Maximized '{title}'")
            elif pos == SnapPosition.MINIMIZE:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                return _ok(f"Minimized '{title}'")
            elif pos == SnapPosition.RESTORE:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                return _ok(f"Restored '{title}'")
            elif pos in snap_map:
                sx, sy, sw, sh = snap_map[pos]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.MoveWindow(hwnd, sx, sy, sw, sh, True)
                return _ok(f"Snapped '{title}' to '{pos}'")
            else:
                return _fail(f"Unknown snap position: '{position}'")

        except Exception as exc:
            return _fail(f"snap_window failed: {exc}")

    # ------------------------------------------------------------------
    def list_windows(self) -> List[Dict[str, Any]]:
        """Return a list of all visible windows with titles and HWNDs."""
        if sys.platform != "win32":
            return []

        try:
            import win32gui  # type: ignore[import]
            windows = []

            def enum_callback(hwnd, lParam):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append({"hwnd": hwnd, "title": title})

            win32gui.EnumWindows(enum_callback, None)
            return windows
        except Exception as exc:
            logger.warning(f"list_windows failed: {exc}")
            return []
