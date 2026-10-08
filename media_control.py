"""
media_control.py — Video & Media Player Control for Active Session
===================================================================
Inspects and controls video playback on active pages via DOM evaluation:
- Never blind-presses keys; inspects state first (video.paused, video.muted, etc.)
- pause: checks video.paused; if false, calls video.pause(); if already paused, does nothing (never toggles)
- resume/play: checks video.paused; if true, calls video.play()
- volume: sets video.volume to float between 0.0 and 1.0
- mute: toggles or sets video.muted = true
- skip_ad: clicks ad skip buttons if present
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from playwright.sync_api import Page

logger = logging.getLogger("Orion.MediaControl")


def get_video_state(page: Page) -> Dict[str, Any]:
    """Inspects the state of the first HTML5 video element on the page."""
    try:
        js = """() => {
            const v = document.querySelector('video');
            if (!v) return { exists: false };
            return {
                exists: true,
                paused: v.paused,
                muted: v.muted,
                volume: Math.round(v.volume * 100),
                currentTime: Math.round(v.currentTime),
                duration: Math.round(v.duration || 0),
                ended: v.ended
            };
        }"""
        return page.evaluate(js)
    except Exception as e:
        logger.warning(f"Error querying video state: {e}")
        return {"exists": False, "error": str(e)}


def pause_video(page: Page) -> Dict[str, Any]:
    """
    Idempotent pause: checks video.paused; if already paused, does not toggle.
    """
    state = get_video_state(page)
    if not state.get("exists"):
        return {"status": "not_found", "message": "No active video element found on page."}

    if state.get("paused"):
        return {"status": "unchanged", "paused": True, "message": "Video is already paused."}

    try:
        page.evaluate("() => { const v = document.querySelector('video'); if (v) v.pause(); }")
        return {"status": "success", "paused": True, "message": "Paused video playback."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def resume_video(page: Page) -> Dict[str, Any]:
    """
    Idempotent play/resume: checks video.paused; if paused, calls play().
    """
    state = get_video_state(page)
    if not state.get("exists"):
        return {"status": "not_found", "message": "No active video element found on page."}

    if not state.get("paused"):
        return {"status": "unchanged", "paused": False, "message": "Video is already playing."}

    try:
        page.evaluate("() => { const v = document.querySelector('video'); if (v) v.play(); }")
        return {"status": "success", "paused": False, "message": "Resumed video playback."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def set_volume(page: Page, level_0_to_100: int) -> Dict[str, Any]:
    """Sets video volume to integer between 0 and 100."""
    state = get_video_state(page)
    if not state.get("exists"):
        return {"status": "not_found", "message": "No active video element found on page."}

    clamped = max(0, min(100, level_0_to_100))
    vol_frac = clamped / 100.0
    try:
        page.evaluate(f"() => {{ const v = document.querySelector('video'); if (v) {{ v.volume = {vol_frac}; v.muted = false; }} }}")
        return {"status": "success", "volume": clamped, "message": f"Set volume to {clamped}%."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def mute_video(page: Page) -> Dict[str, Any]:
    """Mutes video playback without toggling to unmuted."""
    state = get_video_state(page)
    if not state.get("exists"):
        return {"status": "not_found", "message": "No active video element found on page."}

    try:
        page.evaluate("() => { const v = document.querySelector('video'); if (v) v.muted = true; }")
        return {"status": "success", "muted": True, "message": "Muted video playback."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def skip_ad(page: Page) -> Dict[str, Any]:
    """Clicks ad skip button if detected in DOM."""
    selectors = [
        ".ytp-ad-skip-button-modern",
        ".ytp-ad-skip-button",
        ".ytp-skip-ad-button",
        "button.ytp-ad-skip-button-text",
        "[aria-label*='Skip ad']",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.is_visible(timeout=500):
                loc.click()
                return {"status": "success", "message": "Clicked skip ad button."}
        except Exception:
            continue
    return {"status": "not_found", "message": "No visible skip ad button detected."}


def next_video(page: Page) -> Dict[str, Any]:
    """Navigates to next video in playlist or queue if present."""
    selectors = [
        ".ytp-next-button",
        "a.ytp-next-button",
        "[aria-label*='Next video']",
        "[aria-label*='Next (SHIFT+N)']",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.is_visible(timeout=500):
                loc.click()
                return {"status": "success", "message": "Triggered next video."}
        except Exception:
            continue
    return {"status": "not_found", "message": "No next video button detected."}
