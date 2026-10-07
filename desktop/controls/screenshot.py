"""
desktop/controls/screenshot.py — Dual-engine screenshot capture.

Priority order (Phase 5 spec):
  1. Playwright CDP in-memory capture (if a live browser page is provided)
  2. Hardened Win32 / mss capture of the whole desktop or a window region

Returns a PIL Image or bytes. Skips capture on login/payment/password windows.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("orion.desktop.screenshot")

# Sensitive window titles — skip capture on these (Global Rule 5)
_SENSITIVE_TITLE_FRAGMENTS: tuple[str, ...] = (
    "password", "sign in", "log in", "login", "payment", "checkout",
    "credit card", "billing", "paypal", "two-factor", "2fa", "otp",
    "verify your identity", "bank", "stripe",
)


def _is_sensitive_window(title: str) -> bool:
    """Return True if the window title matches a sensitive pattern."""
    tl = title.lower()
    return any(frag in tl for frag in _SENSITIVE_TITLE_FRAGMENTS)


def _ok(detail: str = "", image=None) -> Dict[str, Any]:
    return {"ok": True, "detail": detail, "image": image}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail, "image": None}


# ---------------------------------------------------------------------------
# Engine 1: Playwright CDP capture
# ---------------------------------------------------------------------------

async def _cdp_screenshot(page) -> Optional[bytes]:
    """Capture a screenshot via Playwright CDP. Returns PNG bytes or None."""
    try:
        if page is None or page.is_closed():
            return None
        await page.bring_to_front()
        return await page.screenshot(type="png", full_page=False)
    except Exception as exc:
        logger.debug(f"CDP screenshot failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Engine 2: Win32 / mss desktop capture
# ---------------------------------------------------------------------------

def _win32_screenshot(
    hwnd: Optional[int] = None,
    region: Optional[tuple[int, int, int, int]] = None,
) -> Optional[bytes]:
    """
    Capture screen using mss (fast memory-mapped screenshot).

    hwnd:   capture just this window's bounding box (Win32)
    region: (left, top, width, height) — overrides hwnd
    """
    try:
        import mss  # type: ignore[import]
        import mss.tools  # type: ignore[import]

        monitor: dict[str, int] = {}
        if hwnd and sys.platform == "win32":
            try:
                import win32gui  # type: ignore[import]
                rect = win32gui.GetWindowRect(hwnd)
                monitor = {
                    "left": rect[0], "top": rect[1],
                    "width": rect[2] - rect[0], "height": rect[3] - rect[1],
                }
            except Exception:
                pass

        if region:
            left, top, width, height = region
            monitor = {"left": left, "top": top, "width": width, "height": height}

        with mss.mss() as sct:
            if monitor:
                shot = sct.grab(monitor)
            else:
                shot = sct.grab(sct.monitors[0])   # full desktop
            return mss.tools.to_png(shot.rgb, shot.size)
    except Exception as exc:
        logger.debug(f"mss screenshot failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def take_screenshot(
    page=None,
    hwnd: Optional[int] = None,
    region: Optional[tuple[int, int, int, int]] = None,
    save_path: Optional[Union[str, Path]] = None,
    window_title: str = "",
) -> Dict[str, Any]:
    """
    Capture a screenshot using the best available engine.

    Args:
        page:         Playwright Page object (if available). Async CDP path.
        hwnd:         Win32 HWND for window-region capture.
        region:       (left, top, width, height) override.
        save_path:    If given, save PNG to this path.
        window_title: Title of target window — checked against sensitive patterns.

    Returns:
        {ok: bool, detail: str, image: bytes | None}
    """
    # --- Safety check: skip on sensitive windows ---
    if window_title and _is_sensitive_window(window_title):
        return _fail(
            f"Screenshot blocked: window '{window_title}' matches a sensitive pattern "
            f"(login/payment/password). Capture skipped per security policy."
        )

    png_bytes: Optional[bytes] = None

    # Engine 2: Win32 / mss (synchronous — always available)
    png_bytes = _win32_screenshot(hwnd=hwnd, region=region)

    if not png_bytes:
        return _fail("All screenshot engines failed.")

    # Save if requested
    if save_path:
        dest = Path(save_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png_bytes)
        logger.info(f"Screenshot saved to {dest}")

    return _ok(f"Screenshot captured ({len(png_bytes):,} bytes)", image=png_bytes)


async def take_screenshot_async(
    page=None,
    hwnd: Optional[int] = None,
    region: Optional[tuple[int, int, int, int]] = None,
    save_path: Optional[Union[str, Path]] = None,
    window_title: str = "",
) -> Dict[str, Any]:
    """Async variant: tries Playwright CDP first, then falls back to Win32."""
    if window_title and _is_sensitive_window(window_title):
        return _fail(
            f"Screenshot blocked: sensitive window '{window_title}'. Skipped."
        )

    png_bytes: Optional[bytes] = None

    # Engine 1: Playwright CDP
    if page is not None:
        png_bytes = await _cdp_screenshot(page)

    # Engine 2: Win32 fallback
    if not png_bytes:
        png_bytes = _win32_screenshot(hwnd=hwnd, region=region)

    if not png_bytes:
        return _fail("All screenshot engines failed.")

    if save_path:
        dest = Path(save_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png_bytes)

    return _ok(f"Screenshot captured ({len(png_bytes):,} bytes)", image=png_bytes)
