"""
desktop/controls/clipboard.py — Read/write system clipboard.

Uses pyperclip with win32clipboard fallback (Windows).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("orion.desktop.clipboard")


def _ok(detail: str = "", data: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail, "data": data}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail, "data": ""}


class ClipboardController:
    """
    Read/write clipboard text.
    All public methods return {ok: bool, detail: str, data: str}.
    """

    def get_text(self) -> Dict[str, Any]:
        """Read current clipboard text."""
        try:
            import pyperclip  # type: ignore[import]
            text = pyperclip.paste()
            return _ok(f"Clipboard read ({len(text)} chars)", data=text)
        except Exception:
            try:
                import win32clipboard  # type: ignore[import]
                win32clipboard.OpenClipboard()
                text = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return _ok(f"Clipboard read ({len(text)} chars)", data=text)
            except Exception as exc:
                return _fail(f"get_text failed: {exc}")

    def set_text(self, text: str) -> Dict[str, Any]:
        """Write text to clipboard."""
        if not isinstance(text, str):
            return _fail("set_text: only string values are accepted")
        try:
            import pyperclip  # type: ignore[import]
            pyperclip.copy(text)
            return _ok(f"Clipboard written ({len(text)} chars)")
        except Exception:
            try:
                import win32clipboard  # type: ignore[import]
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return _ok(f"Clipboard written ({len(text)} chars)")
            except Exception as exc:
                return _fail(f"set_text failed: {exc}")

    def clear(self) -> Dict[str, Any]:
        """Clear clipboard contents."""
        return self.set_text("")
