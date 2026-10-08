"""
orion_desktop/controls/mouse.py — Hardware-Level Win32 Mouse & Viewport Controller
==================================================================================
Direct SendInput mouse simulation with 65535 coordinate normalization, cubic
Bezier curves, precision slider drags, and 3D viewport orbit/pan operations.
"""

from __future__ import annotations

import sys
import time
import math
import random
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger("Orion.Mouse")

# Win32 Mouse Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000


class MouseDriver:
    """Hardware mouse driver using SendInput on Windows, mockable in tests."""

    def __init__(self, human_trajectories: bool = True):
        self.human_trajectories = human_trajectories
        self._is_windows = sys.platform == "win32"
        self._sent_log: List[Dict[str, Any]] = []
        self._sim_x = 960
        self._sim_y = 540

    def get_position(self) -> Tuple[int, int]:
        """Returns the current mouse cursor position (x, y)."""
        if not self._is_windows:
            return (self._sim_x, self._sim_y)

        try:
            import ctypes
            import ctypes.wintypes as w
            pt = w.POINT()
            u32 = getattr(ctypes.windll, "user32")
            u32.GetCursorPos(ctypes.byref(pt))
            return (pt.x, pt.y)
        except Exception:
            return (self._sim_x, self._sim_y)

    def _normalize_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Maps physical pixel coordinates to normalized 0-65535 virtual desktop space."""
        if not self._is_windows:
            return (int(x * 65535 / 1920), int(y * 65535 / 1080))

        try:
            import ctypes
            u32 = getattr(ctypes.windll, "user32")
            v_x = u32.GetSystemMetrics(76)       # SM_XVIRTUALSCREEN
            v_y = u32.GetSystemMetrics(77)       # SM_YVIRTUALSCREEN
            v_w = u32.GetSystemMetrics(78) or 1  # SM_CXVIRTUALSCREEN
            v_h = u32.GetSystemMetrics(79) or 1  # SM_CYVIRTUALSCREEN

            norm_x = int((x - v_x) * 65535 / v_w)
            norm_y = int((y - v_y) * 65535 / v_h)
            return (max(0, min(65535, norm_x)), max(0, min(65535, norm_y)))
        except Exception:
            return (x, y)

    def _send_mouse_event(self, flags: int, x: int = 0, y: int = 0, data: int = 0) -> bool:
        """Sends raw Win32 mouse event via SendInput."""
        self._sent_log.append({"flags": flags, "x": x, "y": y, "data": data})
        if not self._is_windows:
            if flags & MOUSEEVENTF_ABSOLUTE:
                self._sim_x, self._sim_y = x, y
            return True

        try:
            import ctypes
            import ctypes.wintypes as w
            from .keyboard import _INPUT, _InputUnion, _MOUSEINPUT

            norm_x, norm_y = self._normalize_coords(x, y) if (flags & MOUSEEVENTF_ABSOLUTE) else (x, y)
            full_flags = flags | MOUSEEVENTF_VIRTUALDESK if (flags & MOUSEEVENTF_ABSOLUTE) else flags

            extra = ctypes.c_ulong(0)
            ii_ = _InputUnion()
            ii_.mi = _MOUSEINPUT(
                w.LONG(norm_x),
                w.LONG(norm_y),
                w.DWORD(data),
                w.DWORD(full_flags),
                w.DWORD(0),
                ctypes.pointer(extra)
            )
            inp = _INPUT(ctypes.c_ulong(0), ii_)
            u32 = getattr(ctypes.windll, "user32")
            u32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))
            return True
        except Exception as e:
            logger.debug(f"Mouse send error: {e}")
            return False

    def move_to(self, x: int, y: int, duration_s: float = 0.15) -> bool:
        """Moves cursor to target coordinates using humanized cubic Bezier curve."""
        start_x, start_y = self.get_position()
        dist = math.hypot(x - start_x, y - start_y)

        if dist < 4 or not self.human_trajectories or duration_s <= 0:
            return self._send_mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, x, y)

        # Generate 2 random Bezier control points to mimic human arm arc
        ctrl_offset = dist * 0.25
        cx1 = start_x + (x - start_x) * 0.3 + random.uniform(-ctrl_offset, ctrl_offset)
        cy1 = start_y + (y - start_y) * 0.3 + random.uniform(-ctrl_offset, ctrl_offset)
        cx2 = start_x + (x - start_x) * 0.7 + random.uniform(-ctrl_offset, ctrl_offset)
        cy2 = start_y + (y - start_y) * 0.7 + random.uniform(-ctrl_offset, ctrl_offset)

        steps = max(8, int(duration_s * 60))
        for i in range(1, steps + 1):
            t = i / steps
            # Cubic Bezier formula: B(t) = (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
            bx = (1 - t)**3 * start_x + 3 * (1 - t)**2 * t * cx1 + 3 * (1 - t) * t**2 * cx2 + t**3 * x
            by = (1 - t)**3 * start_y + 3 * (1 - t)**2 * t * cy1 + 3 * (1 - t) * t**2 * cy2

            # Add subtle micro-jitter
            if i < steps:
                bx += random.uniform(-0.5, 0.5)
                by += random.uniform(-0.5, 0.5)

            self._send_mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, int(bx), int(by))
            time.sleep(duration_s / steps)

        return True

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Moves to (x, y) if specified, and performs a left click."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(0.02)
        cur_x, cur_y = self.get_position()
        self._send_mouse_event(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        time.sleep(random.uniform(0.02, 0.04))
        self._send_mouse_event(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        return True

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs a right click (context menu)."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(0.02)
        cur_x, cur_y = self.get_position()
        self._send_mouse_event(MOUSEEVENTF_RIGHTDOWN | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        time.sleep(random.uniform(0.02, 0.04))
        self._send_mouse_event(MOUSEEVENTF_RIGHTUP | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        return True

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs a double click."""
        self.click(x, y)
        time.sleep(0.08)
        self.click()
        return True

    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs a middle mouse click."""
        if x is not None and y is not None:
            self.move_to(x, y)
            time.sleep(0.02)
        cur_x, cur_y = self.get_position()
        self._send_mouse_event(MOUSEEVENTF_MIDDLEDOWN | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        time.sleep(0.03)
        self._send_mouse_event(MOUSEEVENTF_MIDDLEUP | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        return True

    def drag_and_drop(self, x1: int, y1: int, x2: int, y2: int, duration_s: float = 0.3) -> bool:
        """Drags mouse from (x1, y1) to (x2, y2). Ideal for UI sliders and box selection."""
        self.move_to(x1, y1)
        time.sleep(0.05)
        self._send_mouse_event(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_ABSOLUTE, x1, y1)
        time.sleep(0.05)
        self.move_to(x2, y2, duration_s=duration_s)
        time.sleep(0.05)
        self._send_mouse_event(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_ABSOLUTE, x2, y2)
        return True

    # -----------------------------------------------------------------------
    # 3D Viewport Specialized Operators (Blender Viewport Navigation)
    # -----------------------------------------------------------------------
    def orbit_3d(self, dx: int, dy: int, duration_s: float = 0.25) -> bool:
        """
        Orbits the 3D viewport in Blender by holding Middle Mouse and dragging relative delta.
        """
        start_x, start_y = self.get_position()
        self._send_mouse_event(MOUSEEVENTF_MIDDLEDOWN | MOUSEEVENTF_ABSOLUTE, start_x, start_y)
        time.sleep(0.03)
        self.move_to(start_x + dx, start_y + dy, duration_s=duration_s)
        time.sleep(0.03)
        cur_x, cur_y = self.get_position()
        self._send_mouse_event(MOUSEEVENTF_MIDDLEUP | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y)
        return True

    def pan_3d(self, dx: int, dy: int, duration_s: float = 0.25) -> bool:
        """
        Pans the 3D viewport in Blender by chording Shift + Middle Mouse drag.
        """
        try:
            from .keyboard import KeyboardDriver
            kb = KeyboardDriver(human_cadence=False)
            kb.key_down("shift")
            time.sleep(0.02)
            self.orbit_3d(dx, dy, duration_s=duration_s)
        finally:
            kb.key_up("shift")
        return True

    def zoom_3d(self, delta_wheel: int) -> bool:
        """
        Zooms 3D Viewport or scrolls document via mouse wheel delta.
        Positive = zoom in / scroll up; Negative = zoom out / scroll down.
        """
        cur_x, cur_y = self.get_position()
        # Wheel delta is in multiples of 120 (WHEEL_DELTA)
        data = delta_wheel * 120
        self._send_mouse_event(MOUSEEVENTF_WHEEL | MOUSEEVENTF_ABSOLUTE, cur_x, cur_y, data=data)
        return True

    def get_sent_log(self) -> List[Dict[str, Any]]:
        return list(self._sent_log)

    def clear_log(self) -> None:
        self._sent_log.clear()
