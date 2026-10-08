"""
orion_desktop/controls/keyboard.py — Hardware-Level Win32 Keyboard Controller
=============================================================================
Direct hardware SendInput keyboard simulation with scan codes, modifier chords,
and natural human Gaussian cadences.
"""

from __future__ import annotations

import sys
import time
import random
import logging
from typing import List, Tuple, Optional, Dict, Set

logger = logging.getLogger("Orion.Keyboard")

# ---------------------------------------------------------------------------
# Virtual Key Codes (Win32)
# ---------------------------------------------------------------------------
VK_CODES: Dict[str, int] = {
    "backspace": 0x08, "tab": 0x09, "clear": 0x0C, "enter": 0x0D, "return": 0x0D,
    "shift": 0x10, "ctrl": 0x11, "control": 0x11, "alt": 0x12, "pause": 0x13,
    "caps_lock": 0x14, "escape": 0x1B, "esc": 0x1B, "space": 0x20, "spacebar": 0x20,
    "page_up": 0x21, "page_down": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "print_screen": 0x2C, "insert": 0x2D, "delete": 0x2E, "del": 0x2E,
    "win": 0x5B, "windows": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63, "numpad4": 0x64,
    "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67, "numpad8": 0x68, "numpad9": 0x69,
    "multiply": 0x6A, "add": 0x6B, "separator": 0x6C, "subtract": 0x6D, "decimal": 0x6E, "divide": 0x6F,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF, "`": 0xC0,
    "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}

# Add standard letters and numbers
for c in range(ord('a'), ord('z') + 1):
    VK_CODES[chr(c)] = ord(chr(c).upper())
for n in range(ord('0'), ord('9') + 1):
    VK_CODES[chr(n)] = n


class KeyboardDriver:
    """Hardware keyboard driver using SendInput on Windows, mockable in tests."""

    def __init__(self, human_cadence: bool = True):
        self.human_cadence = human_cadence
        self._is_windows = sys.platform == "win32"
        self._sent_log: List[Dict[str, Any]] = []

        if self._is_windows:
            self._init_win32()

    def _init_win32(self) -> None:
        try:
            import ctypes
            # Enable per-monitor DPI awareness v2 so coordinates and inputs match pixels
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    getattr(ctypes.windll, "user32").SetProcessDPIAware()
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Failed to set DPI awareness: {e}")

    def _get_vk(self, key: str) -> int:
        k = key.lower().strip()
        if k in VK_CODES:
            return VK_CODES[k]
        if len(k) == 1:
            return ord(k.upper())
        return 0

    def key_down(self, key: str) -> bool:
        """Sends physical key-down event."""
        vk = self._get_vk(key)
        self._sent_log.append({"event": "key_down", "key": key, "vk": vk})

        if not self._is_windows or vk == 0:
            return True

        try:
            import ctypes
            import ctypes.wintypes as w

            # KEYEVENTF_SCANCODE = 0x0008
            u32 = getattr(ctypes.windll, "user32")
            scan = u32.MapVirtualKeyW(vk, 0)
            extra = ctypes.c_ulong(0)
            ii_ = _InputUnion()
            ii_.ki = _KEYBDINPUT(w.WORD(vk), w.WORD(scan), w.DWORD(0x0008), w.DWORD(0), ctypes.pointer(extra))
            x = _INPUT(ctypes.c_ulong(1), ii_)
            u32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            return True
        except Exception as e:
            logger.debug(f"key_down error for {key}: {e}")
            return False

    def key_up(self, key: str) -> bool:
        """Sends physical key-up event."""
        vk = self._get_vk(key)
        self._sent_log.append({"event": "key_up", "key": key, "vk": vk})

        if not self._is_windows or vk == 0:
            return True

        try:
            import ctypes
            import ctypes.wintypes as w

            # KEYEVENTF_KEYUP = 0x0002 | KEYEVENTF_SCANCODE = 0x0008
            u32 = getattr(ctypes.windll, "user32")
            scan = u32.MapVirtualKeyW(vk, 0)
            extra = ctypes.c_ulong(0)
            ii_ = _InputUnion()
            ii_.ki = _KEYBDINPUT(w.WORD(vk), w.WORD(scan), w.DWORD(0x0002 | 0x0008), w.DWORD(0), ctypes.pointer(extra))
            x = _INPUT(ctypes.c_ulong(1), ii_)
            u32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            return True
        except Exception as e:
            logger.debug(f"key_up error for {key}: {e}")
            return False

    def press(self, key: str) -> bool:
        """Presses and releases a single key."""
        ok = self.key_down(key)
        # Micro-hold between press and release
        hold_time = random.uniform(0.015, 0.035) if self.human_cadence else 0.005
        time.sleep(hold_time)
        ok = self.key_up(key) and ok
        return ok

    def hotkey(self, *keys: str) -> bool:
        """
        Presses a chord of keys in sequence and releases in reverse.
        Example: hotkey("shift", "a") or hotkey("ctrl", "alt", "del")
        """
        keys_pressed = []
        try:
            for k in keys:
                if self.key_down(k):
                    keys_pressed.append(k)
                    time.sleep(0.01)

            # Hold chord momentarily
            time.sleep(0.03)
            return len(keys_pressed) == len(keys)
        finally:
            for k in reversed(keys_pressed):
                self.key_up(k)
                time.sleep(0.005)

    def type_text(self, text: str, delay: Optional[float] = None) -> bool:
        """
        Types a string of text with human Gaussian cadence.
        Handles uppercase characters by auto-chording Shift.
        """
        for ch in text:
            if ch == "\n":
                self.press("enter")
            elif ch == "\t":
                self.press("tab")
            elif ch.isupper() or ch in '~!@#$%^&*()_+{}|:"<>?':
                self.key_down("shift")
                self.press(ch.lower())
                self.key_up("shift")
            else:
                self.press(ch)

            # Cadence interval
            if delay is not None:
                time.sleep(delay)
            elif self.human_cadence:
                # Gaussian delay around 50ms (range ~25ms - 85ms)
                wait_s = max(0.020, random.gauss(0.050, 0.015))
                time.sleep(wait_s)
            else:
                time.sleep(0.002)

        return True

    def get_sent_log(self) -> List[Dict[str, Any]]:
        """Returns log of sent key events for assertions and audits."""
        return list(self._sent_log)

    def clear_log(self) -> None:
        self._sent_log.clear()


# ---------------------------------------------------------------------------
# Ctypes Structs for Win32 SendInput
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as w

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", w.WORD),
            ("wScan", w.WORD),
            ("dwFlags", w.DWORD),
            ("time", w.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class _HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", w.DWORD),
            ("wParamL", w.WORD),
            ("wParamH", w.WORD),
        ]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", w.LONG),
            ("dy", w.LONG),
            ("mouseData", w.DWORD),
            ("dwFlags", w.DWORD),
            ("time", w.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class _InputUnion(ctypes.Union):
        _fields_ = [
            ("mi", _MOUSEINPUT),
            ("ki", _KEYBDINPUT),
            ("hi", _HARDWAREINPUT),
        ]

    class _INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("union", _InputUnion),
        ]
else:
    # Stubs for non-Windows platforms
    class _InputUnion:
        pass
    class _INPUT:
        pass
    class _KEYBDINPUT:
        pass
