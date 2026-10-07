"""
🌌 Orion × Nebula Web Engine - Base Page Object Model (POM)
Implements auto-waiting, fallback selector resolution, cookie/modal dismissal,
infinite scrolling safeguards, and resilient retry decorators.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page, Locator

from ..browser_manager import BrowserManager
from ..exceptions import SelectorNotFoundError, WebEngineError
from ..selectors.base_selectors import COOKIE_CONSENT_BUTTONS, MODAL_CLOSE_BUTTONS

logger = logging.getLogger("Orion.BasePage")


class BasePage:
    """Base class for all Page Object Models."""

    def __init__(self, browser_mgr: BrowserManager):
        self.mgr = browser_mgr

    @property
    def page(self) -> Page:
        p = self.mgr.page
        if not p or p.is_closed():
            return self.mgr.launch()
        return p

    def resolve_locator(self, selector_def: Dict[str, Any], context: Optional[Any] = None) -> Locator:
        """Translates a selector dictionary into a Playwright Locator."""
        root = context or self.page

        if "role" in selector_def:
            role = selector_def["role"]
            name = selector_def.get("name")
            exact = selector_def.get("exact", False)
            if name:
                return root.get_by_role(role, name=name, exact=exact)
            return root.get_by_role(role)

        if "text" in selector_def:
            return root.get_by_text(selector_def["text"], exact=selector_def.get("exact", False))

        if "testid" in selector_def:
            return root.get_by_test_id(selector_def["testid"])

        if "label" in selector_def:
            return root.get_by_label(selector_def["label"])

        if "placeholder" in selector_def:
            return root.get_by_placeholder(selector_def["placeholder"])

        if "css" in selector_def:
            return root.locator(selector_def["css"])

        if "xpath" in selector_def:
            return root.locator(selector_def["xpath"])

        raise ValueError(f"Invalid selector definition: {selector_def}")

    def find_first_visible(
        self,
        fallback_chain: List[Dict[str, Any]],
        target_name: str = "element",
        timeout_ms: int = 5000,
        context: Optional[Any] = None
    ) -> Locator:
        """
        Attempts each selector in fallback_chain sequentially.
        Returns the first Locator that resolves to a visible element within timeout_ms.
        """
        per_selector_timeout = max(800, int(timeout_ms / len(fallback_chain)))
        tried = []

        for sel in fallback_chain:
            tried.append(sel)
            try:
                loc = self.resolve_locator(sel, context=context)
                # Auto-wait for visibility
                loc.first.wait_for(state="visible", timeout=per_selector_timeout)
                return loc.first
            except Exception:
                continue

        # If none matched, check for blocking modals before failing
        self.dismiss_cookie_banners()
        for sel in fallback_chain[:2]:
            try:
                loc = self.resolve_locator(sel, context=context)
                loc.first.wait_for(state="visible", timeout=1200)
                return loc.first
            except Exception:
                continue

        raise SelectorNotFoundError(target_name, tried, timeout_ms)

    def click_with_fallback(
        self,
        fallback_chain: List[Dict[str, Any]],
        target_name: str = "button",
        timeout_ms: int = 6000
    ):
        """Finds visible element from fallback chain and clicks with auto-waiting."""
        self.dismiss_cookie_banners()
        loc = self.find_first_visible(fallback_chain, target_name, timeout_ms)
        loc.scroll_into_view_if_needed()
        self.mgr.human_delay(0.1, 0.25)
        loc.click(timeout=timeout_ms)
        self.mgr.human_delay(0.15, 0.3)

    def fill_with_fallback(
        self,
        fallback_chain: List[Dict[str, Any]],
        value: str,
        target_name: str = "input_field",
        timeout_ms: int = 6000,
        press_enter: bool = False
    ):
        """Finds visible input element, clears it, and types value."""
        self.dismiss_cookie_banners()
        loc = self.find_first_visible(fallback_chain, target_name, timeout_ms)
        loc.scroll_into_view_if_needed()
        loc.click()
        loc.fill("")
        self.mgr.human_delay(0.08, 0.2)
        loc.type(value, delay=35)
        if press_enter:
            self.mgr.human_delay(0.1, 0.2)
            loc.press("Enter")
        self.mgr.human_delay(0.15, 0.3)

    def dismiss_cookie_banners(self):
        """Scans and dismisses cookie consent banners and overlay popups."""
        for sel in COOKIE_CONSENT_BUTTONS:
            try:
                loc = self.resolve_locator(sel)
                if loc.first.is_visible(timeout=250):
                    logger.info(f"Dismissed cookie consent banner via {sel}.")
                    loc.first.click(timeout=800)
                    self.mgr.human_delay(0.1, 0.2)
                    break
            except Exception:
                continue

        for sel in MODAL_CLOSE_BUTTONS:
            try:
                loc = self.resolve_locator(sel)
                if loc.first.is_visible(timeout=150):
                    loc.first.click(timeout=500)
                    break
            except Exception:
                continue

    def scroll_until_no_new_content(
        self,
        item_selector: Optional[Dict[str, Any]] = None,
        max_iterations: int = 12,
        pause_sec: float = 0.8
    ) -> int:
        """
        Infinite scroll helper with safeguard max-iteration limits.
        Scrolls down dynamically until page height ceases to change or item count stabilizes.
        Returns final count of items or scroll iterations.
        """
        logger.info(f"Starting infinite scroll (max {max_iterations} iterations)...")
        last_height = self.page.evaluate("() => document.body.scrollHeight")
        last_count = 0
        iterations = 0

        while iterations < max_iterations:
            # Scroll down to bottom
            self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(pause_sec)

            # Check new height
            new_height = self.page.evaluate("() => document.body.scrollHeight")

            # Check item count if item selector provided
            current_count = 0
            if item_selector:
                try:
                    loc = self.resolve_locator(item_selector)
                    current_count = loc.count()
                except Exception:
                    pass

            iterations += 1

            # Termination condition: height unchanged and item count hasn't grown
            if new_height == last_height:
                if item_selector and current_count > last_count:
                    # Still items loading
                    last_count = current_count
                    last_height = new_height
                    continue
                logger.info(f"Page scroll settled at iteration {iterations}.")
                break

            last_height = new_height
            last_count = current_count

        return current_count if item_selector else iterations

    def wait_for_network_idle(self, timeout_ms: int = 10000):
        """Waits for all pending network connections to settle."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass
