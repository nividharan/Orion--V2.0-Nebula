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
from .page_watcher import (
    PageWatcher,
    WatchResult,
    Verdict,
    calculate_visual_diff_pct,
)

__all__ = [
    "PlaybackState",
    "verify_playback",
    "heal_playback",
    "capture_playback_viewport_safe",
    "dismiss_consent_modals",
    "skip_ad_if_available",
    "ensure_video_playing",
    "PageWatcher",
    "WatchResult",
    "Verdict",
    "calculate_visual_diff_pct",
]
