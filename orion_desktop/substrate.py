"""
orion_desktop/substrate.py — Central Orion Universal Desktop Substrate
=======================================================================
Unified facade managing hardware controls, window tracking, screen capture,
and pluggable application adapters (Chrome, Blender, Notepad).
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from .adapters.base import BaseAppAdapter
from .adapters.generic import GenericAppAdapter
from .adapters.chrome import ChromeAdapter
from .adapters.blender import BlenderAdapter
from .controls.keyboard import KeyboardDriver
from .controls.mouse import MouseDriver
from .controls.window_manager import WindowManager
from .controls.process_manager import ProcessManager
from .controls.screen_capture import ScreenCapture
from .controls.dialog_detector import DialogDetector

logger = logging.getLogger("Orion.Substrate")


class OrionSubstrate:
    """
    The Universal Operating System & Desktop Automation Substrate.
    Powers both Nebula (Chrome) and the Blender Model (3D).
    """

    def __init__(self, human_cadence: bool = True):
        # Direct OS Controls
        self.keyboard = KeyboardDriver(human_cadence=human_cadence)
        self.mouse = MouseDriver(human_trajectories=human_cadence)
        self.wm = WindowManager()
        self.pm = ProcessManager()
        self.sc = ScreenCapture()
        self.dialogs = DialogDetector(window_manager=self.wm)

        # Registered Application Adapters
        self._adapters: Dict[str, BaseAppAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        self.register_adapter(ChromeAdapter())
        self.register_adapter(BlenderAdapter())
        self.register_adapter(GenericAppAdapter("notepad"))

    def register_adapter(self, adapter: BaseAppAdapter) -> None:
        """Registers an application adapter."""
        name = adapter.app_name.lower().strip()
        self._adapters[name] = adapter
        logger.info(f"Registered Orion App Adapter: '{name}'")

    def get_adapter(self, app_name: str) -> BaseAppAdapter:
        """Retrieves adapter by application name, creating a generic one if unregistered."""
        key = app_name.lower().strip()
        if key in self._adapters:
            return self._adapters[key]
        # Auto-create generic adapter for unknown app
        adapter = GenericAppAdapter(target_app=key)
        self._adapters[key] = adapter
        return adapter

    def list_adapters(self) -> List[str]:
        """Returns list of registered application adapter names."""
        return sorted(list(self._adapters.keys()))

    # -----------------------------------------------------------------------
    # Direct OS Control Primitives
    # -----------------------------------------------------------------------
    def type_text(self, text: str) -> bool:
        """Types text via hardware SendInput."""
        return self.keyboard.type_text(text)

    def press(self, key: str) -> bool:
        """Presses and releases a single key."""
        return self.keyboard.press(key)

    def hotkey(self, *keys: str) -> bool:
        """Presses and releases a key chord (e.g. 'ctrl', 'c' or 'shift', 'a')."""
        return self.keyboard.hotkey(*keys)

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Moves to (x, y) if specified and performs a left click."""
        return self.mouse.click(x, y)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs right click."""
        return self.mouse.right_click(x, y)

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs double click."""
        return self.mouse.double_click(x, y)

    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs middle click."""
        return self.mouse.middle_click(x, y)

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Drags mouse from (x1, y1) to (x2, y2)."""
        return self.mouse.drag_and_drop(x1, y1, x2, y2)

    def move_to(self, x: int, y: int) -> bool:
        """Moves cursor to (x, y) along a humanized Bezier curve."""
        return self.mouse.move_to(x, y)

    def get_cursor_position(self) -> tuple[int, int]:
        """Returns current mouse position."""
        return self.mouse.get_position()

    def capture_screen(self) -> Optional[bytes]:
        """Captures desktop screen as PNG bytes."""
        return self.sc.capture_screen()

    def check_dialogs(self) -> Dict[str, Any]:
        """Checks for native Windows system dialogs (#32770)."""
        return self.dialogs.check_for_dialogs()

    def launch_app(self, app_name: str) -> int:
        """Launches a trusted Windows application, returns PID."""
        return self.pm.launch(app_name)

    def focus_window(self, title_or_class: str) -> bool:
        """Brings a window matching title or class to active foreground."""
        hwnd = self.wm.find_window_by_title(title_or_class) or self.wm.find_window_by_class(title_or_class)
        if hwnd:
            return self.wm.set_foreground(hwnd)
        return False
