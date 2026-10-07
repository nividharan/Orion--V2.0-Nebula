"""
desktop/controls/keyboard_mouse.py — Keyboard + mouse control.

Preference order (Phase 5 spec):
  1. pywinauto UIAutomation by element accessible-name (preferred — no coordinates)
  2. pyautogui keyboard / mouse (coordinate fallback)

All methods return {ok: bool, detail: str}.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("orion.desktop.keyboard_mouse")


def _ok(detail: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail}


class KeyboardMouseController:
    """
    Keyboard and mouse control using pywinauto (UIA) with pyautogui fallback.

    All public methods return {ok: bool, detail: str}.
    """

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def type_text(self, text: str, interval: float = 0.02) -> Dict[str, Any]:
        """Type text at the current focus point using pyautogui."""
        if not isinstance(text, str):
            return _fail("type_text: text must be a string")
        # Security: reject text that looks like credentials (Global Rule 8)
        lower = text.lower()
        if any(kw in lower for kw in ("password", "secret", "api_key", "token")):
            return _fail(
                "type_text: text appears to contain credential-like content — rejected."
            )
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.typewrite(text, interval=interval)
            return _ok(f"Typed {len(text)} chars")
        except Exception as exc:
            return _fail(f"type_text failed: {exc}")

    def hotkey(self, *keys: str) -> Dict[str, Any]:
        """Press a keyboard shortcut (e.g. hotkey('ctrl', 'c'))."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.hotkey(*keys)
            return _ok(f"Hotkey: {'+'.join(keys)}")
        except Exception as exc:
            return _fail(f"hotkey failed: {exc}")

    def press_key(self, key: str) -> Dict[str, Any]:
        """Press and release a single key (e.g. 'enter', 'esc', 'tab')."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.press(key)
            return _ok(f"Pressed '{key}'")
        except Exception as exc:
            return _fail(f"press_key failed: {exc}")

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def move_to(self, x: int, y: int, duration: float = 0.3) -> Dict[str, Any]:
        """Move the mouse to (x, y) screen coordinates."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.moveTo(x, y, duration=duration)
            return _ok(f"Mouse moved to ({x}, {y})")
        except Exception as exc:
            return _fail(f"move_to failed: {exc}")

    def click(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """Click at (x, y). button: 'left' | 'right' | 'middle'."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.click(x, y, button=button)
            return _ok(f"{button.capitalize()} click at ({x}, {y})")
        except Exception as exc:
            return _fail(f"click failed: {exc}")

    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        """Double-click at (x, y)."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.doubleClick(x, y)
            return _ok(f"Double-click at ({x}, {y})")
        except Exception as exc:
            return _fail(f"double_click failed: {exc}")

    def right_click(self, x: int, y: int) -> Dict[str, Any]:
        """Right-click at (x, y)."""
        return self.click(x, y, button="right")

    def scroll(self, x: int, y: int, clicks: int) -> Dict[str, Any]:
        """Scroll at (x, y). Positive = up, negative = down."""
        try:
            import pyautogui  # type: ignore[import]
            pyautogui.scroll(clicks, x=x, y=y)
            return _ok(f"Scrolled {clicks} clicks at ({x}, {y})")
        except Exception as exc:
            return _fail(f"scroll failed: {exc}")

    # ------------------------------------------------------------------
    # UIAutomation by name (preferred over coordinates)
    # ------------------------------------------------------------------

    def click_element_by_name(
        self,
        app_title: str,
        element_name: str,
        control_type: str = "Button",
    ) -> Dict[str, Any]:
        """
        Click a UI element by accessible name using pywinauto UIAutomation.

        Args:
            app_title:    Partial window title to find the app.
            element_name: Accessible name / label of the element.
            control_type: pywinauto control type (default: 'Button').
        """
        try:
            from pywinauto import Application  # type: ignore[import]
            app = Application(backend="uia").connect(title_re=f".*{app_title}.*")
            window = app.top_window()
            ctrl = window.child_window(title=element_name, control_type=control_type)
            ctrl.click_input()
            return _ok(f"Clicked '{element_name}' ({control_type}) in '{app_title}'")
        except Exception as exc:
            return _fail(f"click_element_by_name failed: {exc}")

    def type_into_element(
        self,
        app_title: str,
        element_name: str,
        text: str,
        control_type: str = "Edit",
    ) -> Dict[str, Any]:
        """
        Type text into a named UI element using pywinauto.
        Rejects credential-like text (Global Rule 8).
        """
        lower = text.lower()
        if any(kw in lower for kw in ("password", "secret", "api_key", "token")):
            return _fail(
                "type_into_element: text appears to contain credentials — rejected."
            )
        try:
            from pywinauto import Application  # type: ignore[import]
            app = Application(backend="uia").connect(title_re=f".*{app_title}.*")
            window = app.top_window()
            ctrl = window.child_window(title=element_name, control_type=control_type)
            ctrl.set_edit_text(text)
            return _ok(f"Typed into '{element_name}' in '{app_title}'")
        except Exception as exc:
            return _fail(f"type_into_element failed: {exc}")
