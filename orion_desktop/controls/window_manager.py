"""
orion_desktop/controls/window_manager.py — Window Tracking & Foreground Focus Controller
========================================================================================
Enumerates visible application windows, safely acquires foreground focus via
AttachThreadInput bypass, and manages window geometry.
"""

from __future__ import annotations

import sys
import time
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger("Orion.WindowManager")


class WindowManager:
    """Manages desktop window discovery, geometry, and foreground focus."""

    def __init__(self):
        self._is_windows = sys.platform == "win32"
        self._mock_windows: List[Dict[str, Any]] = []

    def enumerate_windows(self) -> List[Dict[str, Any]]:
        """Returns list of visible top-level windows with title, class name, and HWND."""
        if self._mock_windows:
            return list(self._mock_windows)
        if not self._is_windows:
            return list(self._mock_windows)

        windows = []
        try:
            import ctypes
            import ctypes.wintypes as w
            u32 = getattr(ctypes.windll, "user32")

            def _enum_proc(hwnd, lparam):
                if u32.IsWindowVisible(hwnd):
                    length = u32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        u32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value

                        class_buff = ctypes.create_unicode_buffer(256)
                        u32.GetClassNameW(hwnd, class_buff, 256)
                        class_name = class_buff.value

                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "class_name": class_name,
                        })
                return True

            enum_type = ctypes.WINFUNCTYPE(ctypes.c_bool, w.HWND, w.LPARAM)
            u32.EnumWindows(enum_type(_enum_proc), 0)
        except Exception as e:
            logger.debug(f"EnumWindows error: {e}")

        return windows

    def find_window_by_title(self, pattern: str) -> Optional[int]:
        """Finds first window HWND matching a regex or substring in title."""
        import re
        for win in self.enumerate_windows():
            if re.search(pattern, win["title"], re.IGNORECASE):
                return win["hwnd"]
        return None

    def find_window_by_class(self, class_name: str) -> Optional[int]:
        """Finds first window HWND matching window class (e.g. 'GHOST_WindowClass' for Blender)."""
        for win in self.enumerate_windows():
            if win.get("class_name", "").lower() == class_name.lower():
                return win["hwnd"]
        return None

    def get_window_rect(self, hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Returns window bounding box (x, y, width, height)."""
        if any(w.get("hwnd") == hwnd for w in self._mock_windows) or not self._is_windows:
            return (100, 100, 1280, 720)

        try:
            import ctypes
            import ctypes.wintypes as w
            rect = w.RECT()
            u32 = getattr(ctypes.windll, "user32")
            if u32.GetWindowRect(hwnd, ctypes.byref(rect)):
                x = rect.left
                y = rect.top
                w_ = rect.right - rect.left
                h_ = rect.bottom - rect.top
                return (x, y, w_, h_)
        except Exception as e:
            logger.debug(f"GetWindowRect error: {e}")
        return None

    def set_foreground(self, hwnd: int) -> bool:
        """
        Brings window to active foreground using AttachThreadInput bypass to ensure
        Windows does not block focus or just flash the taskbar icon yellow.
        """
        if any(w.get("hwnd") == hwnd for w in self._mock_windows) or not self._is_windows:
            return True

        try:
            import ctypes
            u32 = getattr(ctypes.windll, "user32")
            k32 = getattr(ctypes.windll, "kernel32")

            # Check if already foreground
            fore_hwnd = u32.GetForegroundWindow()
            if fore_hwnd == hwnd:
                return True

            # If minimized, restore it
            SW_RESTORE = 9
            u32.ShowWindow(hwnd, SW_RESTORE)

            # Thread attachment bypass
            current_thread = k32.GetCurrentThreadId()
            target_thread = u32.GetWindowThreadProcessId(hwnd, None)

            attached = False
            if current_thread != target_thread and target_thread != 0:
                attached = bool(u32.AttachThreadInput(current_thread, target_thread, True))

            try:
                u32.BringWindowToTop(hwnd)
                u32.SetForegroundWindow(hwnd)
                u32.SetActiveWindow(hwnd)
            finally:
                if attached:
                    u32.AttachThreadInput(current_thread, target_thread, False)

            # Verify
            time.sleep(0.05)
            return u32.GetForegroundWindow() == hwnd
        except Exception as e:
            logger.debug(f"set_foreground error: {e}")
            return False

    def minimize(self, hwnd: int) -> bool:
        if any(w.get("hwnd") == hwnd for w in self._mock_windows) or not self._is_windows:
            return True
        try:
            import ctypes
            SW_MINIMIZE = 6
            u32 = getattr(ctypes.windll, "user32")
            return bool(u32.ShowWindow(hwnd, SW_MINIMIZE))
        except Exception:
            return False

    def maximize(self, hwnd: int) -> bool:
        if any(w.get("hwnd") == hwnd for w in self._mock_windows) or not self._is_windows:
            return True
        try:
            import ctypes
            SW_MAXIMIZE = 3
            u32 = getattr(ctypes.windll, "user32")
            return bool(u32.ShowWindow(hwnd, SW_MAXIMIZE))
        except Exception:
            return False

    def add_mock_window(self, hwnd: int, title: str, class_name: str = "") -> None:
        """Helper for test mock injection."""
        self._mock_windows.append({"hwnd": hwnd, "title": title, "class_name": class_name})

    def clear_mocks(self) -> None:
        self._mock_windows.clear()
