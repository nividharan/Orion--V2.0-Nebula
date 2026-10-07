"""
🌌 Orion × Nebula Web Engine - Catalog Scraper Page Object
Handles dynamic listing extraction with infinite scroll, deduplication, and schema validation.
"""

from typing import List, Dict, Any, Callable, Optional
from .base_page import BasePage


class CatalogScraperPage(BasePage):
    """Scrapes dynamic catalogs, product feeds, and search listings with infinite scroll."""

    def scrape_catalog(
        self,
        url: str,
        container_selector: Dict[str, Any],
        extract_fn: Callable[[Any], Dict[str, Any]],
        max_scrolls: int = 10,
        pause_sec: float = 0.8,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Navigates to URL, continuously scrolls down until no new content or max_scrolls reached,
        and applies extract_fn to each discovered element container.
        """
        self.mgr.navigate(url, wait_until="load")
        self.dismiss_cookie_banners()
        self.wait_for_network_idle(5000)

        # Execute infinite scroll
        self.scroll_until_no_new_content(
            item_selector=container_selector,
            max_iterations=max_scrolls,
            pause_sec=pause_sec
        )

        # Extract items
        items = []
        try:
            cards = self.resolve_locator(container_selector)
            count = min(limit, cards.count())

            for i in range(count):
                card = cards.nth(i)
                try:
                    data = extract_fn(card)
                    if data:
                        items.append(data)
                except Exception:
                    continue
        except Exception:
            pass

        return items
