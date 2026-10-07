"""
verify/ package — Web perception, DOM playback verification, and self-healing.
"""

from .playback import (
    PlaybackState,
    verify_playback,
    heal_playback,
    capture_playback_viewport_safe,
    dismiss_consent_modals,
    skip_ad_if_available,
    ensure_video_playing,
)

__all__ = [
    "PlaybackState",
    "verify_playback",
    "heal_playback",
    "capture_playback_viewport_safe",
    "dismiss_consent_modals",
    "skip_ad_if_available",
    "ensure_video_playing",
]
