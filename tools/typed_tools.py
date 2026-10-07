"""
tools/typed_tools.py — Phase 7: Typed Async Tools
==================================================
Principle:
  - All tools are strictly typed with comprehensive docstrings.
  - Domain allow-lists and sensitive action policies enforced prior to execution.
  - Safe error handling returning structured dicts instead of unhandled crashes.
"""

from __future__ import annotations

import os
import time
import logging
import urllib.parse
from typing import Optional, Dict, Any, Callable, List

from schemas import ALLOWED_DOMAINS
from resolvers.youtube import Candidate, search
from verify.playback import (
    verify_playback,
    heal_playback,
    capture_playback_viewport_safe,
    PlaybackState,
)

logger = logging.getLogger("Orion.TypedTools")


class ToolSecurityError(ValueError):
    """Raised when a tool call violates domain allow-lists or safety boundaries."""
    pass


def _validate_target_url(url: str) -> None:
    """Enforces domain allow-list for tool URLs."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return  # Allow relative or non-URL targets (e.g. desktop commands)

    matched = any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)
    if not matched:
        raise ToolSecurityError(f"Target URL domain '{host}' is not in ALLOWED_DOMAINS")


# ---------------------------------------------------------------------------
# Individual Typed Tools
# ---------------------------------------------------------------------------

async def web_navigate(url: str, page=None) -> Dict[str, Any]:
    """
    Navigates the browser to an approved web address.

    Args:
        url: Fully-qualified HTTP/HTTPS URL within ALLOWED_DOMAINS.
        page: Optional active Playwright Page instance.

    Returns:
        Dict containing success status, resolved url, and elapsed time in ms.
    """
    _validate_target_url(url)
    start = time.perf_counter()

    if page is not None:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            elapsed = (time.perf_counter() - start) * 1000
            return {"success": True, "action": "navigate", "url": url, "elapsed_ms": round(elapsed, 2)}
        except Exception as e:
            return {"success": False, "action": "navigate", "url": url, "error": str(e)}

    # Headless simulation if no page attached
    return {"success": True, "action": "navigate", "url": url, "simulated": True}


async def web_search(portal: str, query: str, page=None) -> Dict[str, Any]:
    """
    Constructs an authoritative search URL for a portal and navigates.

    Args:
        portal: Known portal name (e.g. 'youtube', 'github', 'wikipedia', 'google').
        query: Search keywords or query string.
        page: Optional active Playwright Page instance.

    Returns:
        Dict containing success status, resolved search URL, and portal used.
    """
    p = portal.lower().strip()
    q = urllib.parse.quote_plus(query.strip())

    if "youtube" in p:
        target_url = f"https://www.youtube.com/results?search_query={q}"
    elif "github" in p:
        target_url = f"https://github.com/search?q={q}"
    elif "wikipedia" in p:
        target_url = f"https://en.wikipedia.org/wiki/Special:Search?search={q}"
    else:
        target_url = f"https://www.google.com/search?q={q}"

    return await web_navigate(target_url, page=page)


async def media_resolve_and_play(
    query: str,
    page=None,
    fixture_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolves YouTube search candidates, selects the top match, and initiates playback.

    Args:
        query: Track title or artist keywords.
        page: Optional active Playwright Page instance.
        fixture_path: Optional offline JSON fixture path for deterministic tests.

    Returns:
        Dict with top candidate details, watch URL, and playback status.
    """
    start = time.perf_counter()

    # Step 1: Resolve candidates
    from resolvers.youtube import search_from_fixture
    if fixture_path and os.path.exists(fixture_path):
        import json
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        candidates = search_from_fixture(data, query, max_results=5)
    else:
        candidates = search(query, max_results=5)

    if not candidates:
        return {"success": False, "query": query, "error": "No candidates found"}

    top = candidates[0]
    watch_url = top["url"]

    # Step 2: Navigate to watch URL
    nav_res = await web_navigate(watch_url, page=page)
    if not nav_res.get("success", False):
        return {"success": False, "candidate": dict(top), "error": nav_res.get("error")}

    elapsed = (time.perf_counter() - start) * 1000
    return {
        "success": True,
        "query": query,
        "candidate": dict(top),
        "watch_url": watch_url,
        "elapsed_ms": round(elapsed, 2),
    }


async def media_verify_playback(page=None) -> Dict[str, Any]:
    """
    Performs DOM-first perception check on current media playback state.

    Args:
        page: Optional active Playwright Page instance.

    Returns:
        Dict representing PlaybackState (is_playing, is_paused, ad_showing, status).
    """
    if page is None:
        return {
            "success": True,
            "simulated": True,
            "state": {"is_playing": True, "status": "PLAYING", "has_video": True}
        }

    state: PlaybackState = verify_playback(page)
    return {"success": True, "state": state.to_dict()}


async def media_heal_playback(page=None) -> Dict[str, Any]:
    """
    Surgically self-heals playback by dismissing consent modals, skipping ads,
    or unpausing the video element directly.

    Args:
        page: Optional active Playwright Page instance.

    Returns:
        Dict containing recovered PlaybackState.
    """
    if page is None:
        return {
            "success": True,
            "simulated": True,
            "state": {"is_playing": True, "status": "PLAYING"}
        }

    healed_state: PlaybackState = heal_playback(page, max_retries=2)
    return {"success": True, "state": healed_state.to_dict()}


async def web_screenshot(
    page=None,
    output_path: Optional[str] = None,
    redact_inputs: bool = True
) -> Dict[str, Any]:
    """
    Captures a safe viewport screenshot with sensitive credentials blurred.

    Args:
        page: Optional active Playwright Page instance.
        output_path: Target path on disk for PNG file.
        redact_inputs: Whether to mask passwords and card inputs.

    Returns:
        Dict containing saved file path.
    """
    if page is None:
        return {"success": True, "simulated": True, "path": output_path or "screenshot.png"}

    saved_path = capture_playback_viewport_safe(
        page, output_path=output_path, redact_inputs=redact_inputs
    )
    return {"success": True, "path": saved_path}


async def desktop_announce(message: str) -> Dict[str, Any]:
    """
    Announces a task status message or milestone to narrator/console.

    Args:
        message: Human-readable notification text.

    Returns:
        Dict confirming announcement dispatch.
    """
    logger.info("[Narrator] %s", message)
    return {"success": True, "message": message}


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry mapping tool names to typed async callable implementations."""

    _REGISTRY: Dict[str, Callable] = {
        "web_navigate": web_navigate,
        "web_search": web_search,
        "media_resolve_and_play": media_resolve_and_play,
        "media_verify_playback": media_verify_playback,
        "media_heal_playback": media_heal_playback,
        "web_screenshot": web_screenshot,
        "desktop_announce": desktop_announce,
    }

    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        return cls._REGISTRY.get(name)

    @classmethod
    def list_tools(cls) -> List[str]:
        return sorted(cls._REGISTRY.keys())
