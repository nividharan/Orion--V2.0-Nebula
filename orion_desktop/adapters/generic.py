"""
orion_desktop/adapters/generic.py — Generic Windows Application Adapter
========================================================================
Default adapter for standard Windows applications (Notepad, File Explorer, Calculator).
"""

from __future__ import annotations

from typing import Optional

from .base import BaseAppAdapter
from ..controls.keyboard import KeyboardDriver
from ..controls.mouse import MouseDriver
from ..controls.window_manager import WindowManager
from ..controls.process_manager import ProcessManager
from ..controls.screen_capture import ScreenCapture


class GenericAppAdapter(BaseAppAdapter):
    """Controls standard Windows applications via OS primitives."""

    def __init__(self, target_app: str = "notepad"):
        self._app_name = target_app
        self.keyboard = KeyboardDriver()
        self.mouse = MouseDriver()
        self.wm = WindowManager()
        self.pm = ProcessManager()
        self.sc = ScreenCapture()
        self._pid: Optional[int] = None

    @property
    def app_name(self) -> str:
        return self._app_name

    def launch(self, *args, **kwargs) -> int:
        self._pid = self.pm.launch(self._app_name)
        return self._pid

    def find_window(self) -> Optional[int]:
        return self.wm.find_window_by_title(self._app_name)

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

    def close(self, graceful: bool = True) -> bool:
        if self._pid:
            return self.pm.terminate(self._pid, graceful=graceful)
        return False
