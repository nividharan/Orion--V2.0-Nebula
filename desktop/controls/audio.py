"""
desktop/controls/audio.py — System volume control via pycaw + Win32.

Supports get/set master volume (0.0–1.0) and mute/unmute.
Falls back gracefully if pycaw is unavailable (non-Windows or missing install).
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger("orion.desktop.audio")


def _ok(detail: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail}


class AudioController:
    """
    System volume control using pycaw (Windows Core Audio API).

    All public methods return {ok: bool, detail: str}.
    """

    def _get_volume_interface(self):
        """Return the pycaw ISimpleAudioVolume interface for the default endpoint."""
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore[import]
        from comtypes import CLSCTX_ALL  # type: ignore[import]
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        from ctypes import cast, POINTER
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume

    # ------------------------------------------------------------------
    def get_volume(self) -> Dict[str, Any]:
        """Return current master volume level (0.0–1.0)."""
        if sys.platform != "win32":
            return _fail("get_volume is Windows-only")
        try:
            vol = self._get_volume_interface()
            level = vol.GetMasterVolumeLevelScalar()
            return {"ok": True, "detail": f"Volume: {level:.2f}", "volume": round(level, 4)}
        except Exception as exc:
            return _fail(f"get_volume failed: {exc}")

    # ------------------------------------------------------------------
    def set_volume(self, level: float) -> Dict[str, Any]:
        """Set master volume. level must be between 0.0 and 1.0."""
        if sys.platform != "win32":
            return _fail("set_volume is Windows-only")
        level = max(0.0, min(1.0, float(level)))
        try:
            vol = self._get_volume_interface()
            vol.SetMasterVolumeLevelScalar(level, None)
            return _ok(f"Volume set to {level:.0%}")
        except Exception as exc:
            return _fail(f"set_volume failed: {exc}")

    # ------------------------------------------------------------------
    def mute(self) -> Dict[str, Any]:
        """Mute system audio."""
        if sys.platform != "win32":
            return _fail("mute is Windows-only")
        try:
            vol = self._get_volume_interface()
            vol.SetMute(1, None)
            return _ok("Audio muted")
        except Exception as exc:
            return _fail(f"mute failed: {exc}")

    # ------------------------------------------------------------------
    def unmute(self) -> Dict[str, Any]:
        """Unmute system audio."""
        if sys.platform != "win32":
            return _fail("unmute is Windows-only")
        try:
            vol = self._get_volume_interface()
            vol.SetMute(0, None)
            return _ok("Audio unmuted")
        except Exception as exc:
            return _fail(f"unmute failed: {exc}")

    # ------------------------------------------------------------------
    def is_muted(self) -> Optional[bool]:
        """Return mute state or None on error."""
        if sys.platform != "win32":
            return None
        try:
            vol = self._get_volume_interface()
            return bool(vol.GetMute())
        except Exception:
            return None
