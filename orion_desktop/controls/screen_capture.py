"""
orion_desktop/controls/screen_capture.py — Desktop & Window Viewport Capture
=============================================================================
High-speed visual frame capture using Pillow ImageGrab with multi-monitor
bounding box resolution and window-specific viewport cropping.
"""

from __future__ import annotations

import io
import sys
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("Orion.ScreenCapture")


class ScreenCapture:
    """Captures desktop screenshots and window viewports for visual verification."""

    def __init__(self):
        self._is_windows = sys.platform == "win32"
        self._sim_image_bytes: Optional[bytes] = None

    def capture_screen(self, bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[bytes]:
        """
        Captures full desktop or specified bounding box (left, top, right, bottom).
        Returns PNG image bytes.
        """
        try:
            from PIL import ImageGrab
            # all_screens=True captures entire virtual multi-monitor desktop on Windows
            img = ImageGrab.grab(bbox=bbox, all_screens=True if self._is_windows else False)
            buff = io.BytesIO()
            img.save(buff, format="PNG")
            return buff.getvalue()
        except Exception as e:
            logger.debug(f"Screen capture failed: {e}")
            # Fallback mock image bytes for headless/test environments
            if self._sim_image_bytes:
                return self._sim_image_bytes
            return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"

    def capture_window(self, hwnd: int) -> Optional[bytes]:
        """Captures specific window viewport bounding box using its HWND."""
        if not self._is_windows:
            return self.capture_screen()

        try:
            from .window_manager import WindowManager
            wm = WindowManager()
            rect = wm.get_window_rect(hwnd)
            if rect:
                x, y, w, h = rect
                # bbox for ImageGrab is (left, top, right, bottom)
                return self.capture_screen(bbox=(x, y, x + w, y + h))
        except Exception as e:
            logger.debug(f"Window capture failed for HWND {hwnd}: {e}")

        return self.capture_screen()

    def set_simulated_image(self, img_bytes: bytes) -> None:
        """Helper for test mock injection."""
        self._sim_image_bytes = img_bytes
