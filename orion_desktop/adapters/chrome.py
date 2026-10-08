"""
orion_desktop/adapters/chrome.py — Chrome Application Adapter for Orion & Nebula
================================================================================
Manages Google Chrome desktop window focus, process launching, and viewport capture.
"""

from __future__ import annotations

from typing import Optional

from .base import BaseAppAdapter
from ..controls.keyboard import KeyboardDriver
from ..controls.mouse import MouseDriver
from ..controls.window_manager import WindowManager
from ..controls.process_manager import ProcessManager
from ..controls.screen_capture import ScreenCapture


class ChromeAdapter(BaseAppAdapter):
    """Controls Chrome desktop window and process lifecycle for Nebula."""

    def __init__(self):
        self.keyboard = KeyboardDriver()
        self.mouse = MouseDriver()
        self.wm = WindowManager()
        self.pm = ProcessManager()
        self.sc = ScreenCapture()
        self._pid: Optional[int] = None

    @property
    def app_name(self) -> str:
        return "chrome"

    def launch(self, *args, **kwargs) -> int:
        self._pid = self.pm.launch("chrome")
        return self._pid

    def find_window(self) -> Optional[int]:
        # Chrome top-level window class name is Chrome_WidgetWin_1
        hwnd = self.wm.find_window_by_class("Chrome_WidgetWin_1")
        if hwnd:
            return hwnd
        return self.wm.find_window_by_title("Chrome")

    def focus(self) -> bool:
        hwnd = self.find_window()
        if hwnd:
            return self.wm.set_foreground(hwnd)
        return False

    def capture_viewport(self) -> Optional[bytes]:
        hwnd = self.find_window()
        if hwnd:
            return self.sc.capture_window(hwnd)
        return self.sc.capture_screen()

    def hotkey(self, *keys: str) -> bool:
        self.focus()
        return self.keyboard.hotkey(*keys)

    def type_text(self, text: str) -> bool:
        self.focus()
        return self.keyboard.type_text(text)

    def new_tab(self) -> bool:
        return self.hotkey("ctrl", "t")

    def close_tab(self) -> bool:
        return self.hotkey("ctrl", "w")

    def reload(self) -> bool:
        return self.hotkey("ctrl", "r")

    def close(self, graceful: bool = True) -> bool:
        if self._pid:
            return self.pm.terminate(self._pid, graceful=graceful)
        return False
