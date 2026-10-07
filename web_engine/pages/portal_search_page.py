"""
🌌 Orion × Nebula Web Engine - Portal Search Page Object
Specialized Page Object for Google Play Store, YouTube, and generic search portals.
Handles input injection, auto-waiting for results, and CDP screen verification.
"""

import time
import urllib.parse
from typing import List, Dict, Any, Optional

from .base_page import BasePage
from ..browser_manager import BrowserManager
from ..selectors.google_play_selectors import (
    PLAY_STORE_SEARCH_BAR, PLAY_STORE_SEARCH_BUTTON,
    PLAY_STORE_APP_CARDS, PLAY_STORE_APP_TITLE, PLAY_STORE_APP_DEVELOPER, PLAY_STORE_APP_RATING
)
from ..selectors.youtube_selectors import (
    YOUTUBE_SEARCH_BAR, YOUTUBE_SEARCH_BUTTON,
    YOUTUBE_VIDEO_CARDS, YOUTUBE_VIDEO_TITLE, YOUTUBE_CHANNEL_NAME
)
from ..selectors.base_selectors import GENERIC_SEARCH_INPUTS


class PortalSearchPage(BasePage):
    """Encapsulates portal searching and result verification across web portals."""

    def search_google_play(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Executes Google Play Store search, waits for results to settle,
        extracts top app listings, and captures CDP verification screenshot.
        """
        encoded_query = urllib.parse.quote_plus(query.strip())
        direct_url = f"https://play.google.com/store/search?q={encoded_query}&c=apps"

        # 1. Direct navigation
        self.mgr.navigate(direct_url, wait_until="domcontentloaded")
        self.dismiss_cookie_banners()
        self.wait_for_network_idle(5000)

        # 2. Extract results
        results = []
        try:
            cards_loc = self.resolve_locator(PLAY_STORE_APP_CARDS[0])
            cards_loc.first.wait_for(state="visible", timeout=6000)
            count = min(limit, cards_loc.count())

            for i in range(count):
                card = cards_loc.nth(i)
                title = ""
                developer = ""
                rating = ""
                href = card.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = f"https://play.google.com{href}"

                try:
                    title_loc = self.resolve_locator(PLAY_STORE_APP_TITLE[0], context=card)
                    title = title_loc.text_content() or ""
                except Exception:
                    pass

                try:
                    dev_loc = self.resolve_locator(PLAY_STORE_APP_DEVELOPER[0], context=card)
                    developer = dev_loc.text_content() or ""
                except Exception:
                    pass

                try:
                    rat_loc = self.resolve_locator(PLAY_STORE_APP_RATING[0], context=card)
                    rating = rat_loc.text_content() or ""
                except Exception:
                    pass

                if title:
                    results.append({
                        "rank": i + 1,
                        "title": title.strip(),
                        "developer": developer.strip(),
                        "rating": rating.strip(),
                        "url": href
                    })
        except Exception:
            pass

        # 3. Capture CDP verification screenshot
        shot = self.mgr.capture_cdp_screenshot()

        return {
            "portal": "Google Play Store",
            "query": query,
            "results_count": len(results),
            "results": results,
            "url": self.page.url,
            "title": self.page.title(),
            "screenshot": shot.get("saved_path")
        }

    def search_youtube(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Executes YouTube search, auto-waits for video renderers,
        extracts titles and channels, and captures CDP verification screenshot.
        """
        encoded_query = urllib.parse.quote_plus(query.strip())
        direct_url = f"https://www.youtube.com/results?search_query={encoded_query}"

        self.mgr.navigate(direct_url, wait_until="domcontentloaded")
        self.dismiss_cookie_banners()
        self.wait_for_network_idle(5000)

        results = []
        try:
            titles_loc = self.resolve_locator(YOUTUBE_VIDEO_TITLE[0])
            titles_loc.first.wait_for(state="visible", timeout=7000)
            count = min(limit, titles_loc.count())

            for i in range(count):
                el = titles_loc.nth(i)
                t_text = el.text_content() or ""
                href = el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = f"https://www.youtube.com{href}"
                if t_text.strip():
                    results.append({
                        "rank": i + 1,
                        "title": t_text.strip(),
                        "url": href
                    })
        except Exception:
            pass

        shot = self.mgr.capture_cdp_screenshot()
        return {
            "portal": "YouTube",
            "query": query,
            "results_count": len(results),
            "results": results,
            "url": self.page.url,
            "title": self.page.title(),
            "screenshot": shot.get("saved_path")
        }

    def search_generic(self, url: str, query: str) -> Dict[str, Any]:
        """Navigates to URL and performs search via generic search inputs."""
        self.mgr.navigate(url, wait_until="load")
        self.dismiss_cookie_banners()
        self.fill_with_fallback(GENERIC_SEARCH_INPUTS, query, target_name="search_box", press_enter=True)
        self.wait_for_network_idle(6000)
        shot = self.mgr.capture_cdp_screenshot()
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "query": query,
            "screenshot": shot.get("saved_path")
        }
