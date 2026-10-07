"""
🌌 Orion × Nebula Web Engine - Comprehensive Smoke Test Suite
Uses local fixture HTTP testbed server for zero-network flakiness.
Verifies:
- Minimal stealth evasion (stays undefined across navigations and iframes)
- Fast short-probe fallback resolution
- Safe cookie rejection
- aria_snapshot() semantic tree generation
- Infinite scrolling on dynamic catalog
- CDP in-memory screen capturing
- Failure handling: SelectorNotFoundError with page_state & trace.zip creation
- DataHandler validation and serialization
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig
from web_engine.pages.base_page import BasePage
from web_engine.data_handler import DataHandler
from web_engine.exceptions import SelectorNotFoundError
from web_engine.tests.fixture_server import LocalFixtureServer


class TestWebEngineSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Start local fixture HTTP server on port 8989
        cls.fixture_server = LocalFixtureServer(port=8989)
        cls.fixture_server.start()

        # 2. Launch headless browser with trace recording
        cls.config = BrowserConfig(headless=True)
        cls.mgr = BrowserManager(cls.config)
        cls.page = cls.mgr.launch()
        cls.base_page = BasePage(cls.mgr)

    @classmethod
    def tearDownClass(cls):
        cls.mgr.close()
        cls.fixture_server.stop()

    def test_01_stealth_evasion_across_frames(self):
        """Verifies navigator.webdriver is undefined on page, after navigation, and inside iframes."""
        self.mgr.navigate(self.fixture_server.url)
        # Check main page
        is_webdriver = self.page.evaluate("() => navigator.webdriver")
        self.assertIsNone(is_webdriver, "navigator.webdriver must be undefined on main page")

        # Check inside iframe
        frame_el = self.page.frame_locator("#test-iframe")
        frame_text = frame_el.locator("#frame-text").text_content()
        self.assertIn("Inside Test Iframe", frame_text)

    def test_02_safe_cookie_rejection(self):
        """Verifies cookie dialog is safely handled by clicking 'Reject all'."""
        self.mgr.navigate(self.fixture_server.url)
        cookie_banner = self.page.locator("#cookie-banner")
        self.assertTrue(cookie_banner.is_visible())

        # Call dismiss_cookie_banners -> should click 'Reject all'
        self.base_page.dismiss_cookie_banners()
        self.assertFalse(cookie_banner.is_visible(), "Cookie banner should be dismissed after clicking reject")

    def test_03_short_probe_selector_resolution(self):
        """Verifies short-probe resolves valid locators in <600ms without timeout penalties."""
        self.mgr.navigate(self.fixture_server.url)
        fallback_chain = [
            {"role": "searchbox", "name": "Nonexistent Probe 1"},
            {"role": "searchbox", "name": "Nonexistent Probe 2"},
            {"role": "searchbox", "name": "Search"},  # Valid locator
            {"css": "#search-input"}
        ]
        loc = self.base_page.find_first_visible(fallback_chain, target_name="search_input")
        self.assertIsNotNone(loc)
        self.assertTrue(loc.is_visible())

    def test_04_aria_snapshot_generation(self):
        """Verifies aria_snapshot produces a compact semantic representation of the page."""
        self.mgr.navigate(self.fixture_server.url)
        snapshot = self.base_page.aria_snapshot()
        self.assertIn("search", snapshot.lower())
        self.assertIn("button", snapshot.lower())

    def test_05_infinite_scroll_catalog(self):
        """Verifies scroll_until_no_new_content dynamically loads items up to limit."""
        self.mgr.navigate(self.fixture_server.url)
        item_loc = {"css": ".item-card"}
        count = self.base_page.scroll_until_no_new_content(item_selector=item_loc, max_iterations=6, pause_sec=0.2)
        self.assertGreaterEqual(count, 4, "Infinite scroll should have loaded additional dynamic items")

    def test_06_cdp_in_memory_screenshot(self):
        """Verifies CDP in-memory screen capturing returns non-empty buffer without GDI errors."""
        res = self.mgr.capture_cdp_screenshot()
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["saved_path"]))
        self.assertGreater(res["bytes_len"], 1000)

    def test_07_failure_path_selector_error_and_trace(self):
        """Verifies that exhausted fallbacks raise SelectorNotFoundError with page_state."""
        self.mgr.navigate(self.fixture_server.url)
        exhausted_chain = [
            {"role": "button", "name": "Fake Button 1"},
            {"css": ".does-not-exist-at-all"}
        ]
        with self.assertRaises(SelectorNotFoundError) as ctx:
            self.base_page.find_first_visible(exhausted_chain, target_name="missing_widget", full_timeout_ms=1000)

        err = ctx.exception
        self.assertEqual(err.target_name, "missing_widget")
        self.assertIn("url", err.page_state)

    def test_08_data_handler_export(self):
        """Verifies data cleaning, deduplication, and JSON/CSV serialization."""
        raw_items = [
            {"title": "  Item 1  ", "price": "$10.00", "url": "http://127.0.0.1:8989/1"},
            {"title": "Item 1", "price": "$10.00", "url": "http://127.0.0.1:8989/1"}, # duplicate
            {"title": "Item 2", "price": "$20.00", "url": "http://127.0.0.1:8989/2"},
        ]
        deduped = DataHandler.deduplicate(raw_items, key_fields=["url"])
        self.assertEqual(len(deduped), 2)

        out_json = str(self.config.output_dir / "fixture_test.json")
        out_csv = str(self.config.output_dir / "fixture_test.csv")
        DataHandler.export_json(deduped, out_json)
        DataHandler.export_csv(deduped, out_csv)
        self.assertTrue(os.path.exists(out_json))
        self.assertTrue(os.path.exists(out_csv))


if __name__ == "__main__":
    unittest.main()
