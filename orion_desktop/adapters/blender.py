"""
orion_desktop/adapters/blender.py — Blender 3D Application Adapter
==================================================================
Controls Blender desktop application window, processes, 3D viewport navigation,
and 3D modeling shortcut chords for the upcoming Blender Model.
"""

from __future__ import annotations

from typing import Optional, List

from .base import BaseAppAdapter
from ..controls.keyboard import KeyboardDriver
from ..controls.mouse import MouseDriver
from ..controls.window_manager import WindowManager
from ..controls.process_manager import ProcessManager
from ..controls.screen_capture import ScreenCapture


class BlenderAdapter(BaseAppAdapter):
    """Controls Blender 3D application window, 3D viewport, and hotkey chords."""

    def __init__(self):
        self.keyboard = KeyboardDriver()
        self.mouse = MouseDriver()
        self.wm = WindowManager()
        self.pm = ProcessManager()
        self.sc = ScreenCapture()
        self._pid: Optional[int] = None

    @property
    def app_name(self) -> str:
        return "blender"

    def launch(self, *args, **kwargs) -> int:
        self._pid = self.pm.launch("blender")
        return self._pid

    def find_window(self) -> Optional[int]:
        # Blender's native OpenGL/Vulkan window class is GHOST_WindowClass
        hwnd = self.wm.find_window_by_class("GHOST_WindowClass")
        if hwnd:
            return hwnd
        return self.wm.find_window_by_title("Blender")

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

    # -----------------------------------------------------------------------
    # Blender 3D Specific Hotkey Operators
    # -----------------------------------------------------------------------
    def add_menu(self) -> bool:
        """Opens Add Menu (Mesh, Light, Camera): Shift + A."""
        return self.hotkey("shift", "a")

    def grab_mode(self, axis: Optional[str] = None) -> bool:
        """Enters Grab/Move mode (G key), optionally locked to an axis ('x', 'y', 'z')."""
        self.focus()
        ok = self.keyboard.press("g")
        if axis:
            ok = self.keyboard.press(axis.lower()) and ok
        return ok

    def rotate_mode(self, axis: Optional[str] = None) -> bool:
        """Enters Rotate mode (R key), optionally locked to an axis."""
        self.focus()
        ok = self.keyboard.press("r")
        if axis:
            ok = self.keyboard.press(axis.lower()) and ok
        return ok

    def scale_mode(self, axis: Optional[str] = None) -> bool:
        """Enters Scale mode (S key), optionally locked to an axis."""
        self.focus()
        ok = self.keyboard.press("s")
        if axis:
            ok = self.keyboard.press(axis.lower()) and ok
        return ok

    def toggle_edit_mode(self) -> bool:
        """Toggles between Object Mode and Edit Mode: Tab key."""
        self.focus()
        return self.keyboard.press("tab")

    def trigger_render(self) -> bool:
        """Triggers single frame render: F12."""
        self.focus()
        return self.keyboard.press("f12")

    def trigger_render_animation(self) -> bool:
        """Triggers animation render: Ctrl + F12."""
        return self.hotkey("ctrl", "f12")

    def view_front(self) -> bool:
        """Numpad 1: Front orthographic view."""
        self.focus()
        return self.keyboard.press("numpad1")

    def view_side(self) -> bool:
        """Numpad 3: Right side orthographic view."""
        self.focus()
        return self.keyboard.press("numpad3")

    def view_top(self) -> bool:
        """Numpad 7: Top orthographic view."""
        self.focus()
        return self.keyboard.press("numpad7")

    # -----------------------------------------------------------------------
    # 3D Viewport Mouse Manipulation
    # -----------------------------------------------------------------------
    def orbit(self, dx: int, dy: int) -> bool:
        """Orbits the 3D viewport (middle-click drag)."""
        self.focus()
        return self.mouse.orbit_3d(dx, dy)

    def pan(self, dx: int, dy: int) -> bool:
        """Pans the 3D viewport (shift + middle-click drag)."""
        self.focus()
        return self.mouse.pan_3d(dx, dy)

    def zoom(self, delta_wheel: int) -> bool:
        """Zooms the 3D viewport (mouse wheel)."""
        self.focus()
        return self.mouse.zoom_3d(delta_wheel)

    def close(self, graceful: bool = True) -> bool:
        if self._pid:
            return self.pm.terminate(self._pid, graceful=graceful)
        return False
