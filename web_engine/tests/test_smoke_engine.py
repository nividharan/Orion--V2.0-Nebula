"""
🌌 Orion × Nebula Web Engine - Smoke Test Suite
Verifies Playwright browser initialization, stealth evasions, CDP screen capturing,
Page Object resolution, and data export pipelines.
"""

import os
import sys
import unittest

# Ensure web_engine is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig
from web_engine.pages.portal_search_page import PortalSearchPage
from web_engine.data_handler import DataHandler


class TestWebEngineSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force headless for automated CI / test runner
        cls.config = BrowserConfig(headless=True)
        cls.mgr = BrowserManager(cls.config)
        cls.page = cls.mgr.launch()

    @classmethod
    def tearDownClass(cls):
        cls.mgr.close()

    def test_01_stealth_evasion(self):
        """Verifies that navigator.webdriver is removed and undefined."""
        self.mgr.navigate("https://example.com")
        webdriver_flag = self.page.evaluate("() => navigator.webdriver")
        self.assertIsNone(webdriver_flag, "navigator.webdriver should be undefined under stealth")

    def test_02_cdp_in_memory_screenshot(self):
        """Verifies that CDP captures real in-memory screenshot without GDI BitBlt errors."""
        res = self.mgr.capture_cdp_screenshot()
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["saved_path"]))
        self.assertGreater(res["bytes_len"], 1000, "Screenshot should contain non-trivial bytes")

    def test_03_portal_search_google_play(self):
        """Verifies Google Play Store search, auto-waiting, and result extraction."""
        portal_page = PortalSearchPage(self.mgr)
        res = portal_page.search_google_play("free fire", limit=3)
        self.assertEqual(res["portal"], "Google Play Store")
        self.assertIn("play.google.com", res["url"])
        self.assertTrue(os.path.exists(res["screenshot"]))

    def test_04_data_handler_export(self):
        """Verifies data cleaning, deduplication, and JSON/CSV serialization."""
        raw_items = [
            {"title": "  Free Fire MAX  ", "price": "Free", "url": "https://example.com/1"},
            {"title": "Free Fire MAX", "price": "$0.00", "url": "https://example.com/1"}, # duplicate
            {"title": "PUBG Mobile", "price": "$0.00", "url": "https://example.com/2"},
        ]
        deduped = DataHandler.deduplicate(raw_items, key_fields=["url"])
        self.assertEqual(len(deduped), 2)

        out_json = os.path.join(self.config.output_dir, "test_output.json")
        out_csv = os.path.join(self.config.output_dir, "test_output.csv")
        DataHandler.export_json(deduped, out_json)
        DataHandler.export_csv(deduped, out_csv)
        self.assertTrue(os.path.exists(out_json))
        self.assertTrue(os.path.exists(out_csv))


if __name__ == "__main__":
    unittest.main()
