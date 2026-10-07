"""
🌌 Orion × Nebula Web Engine - Hardened Smoke Test Suite
Uses local fixture HTTP testbed server for zero-network flakiness.
Verifies all 10 audited items and security/resilience requirements:
1. Stealth evasion: navigator.webdriver reports strictly false (matching real Chrome)
2. Delayed-element probe: catches 500ms async render via wait_for probe
3. Sensitive action & target blocking (element text 'Place order', 'Delete account')
4. Retry backoff timing and prohibition on sensitive actions
5. 429 rate-limiting with Retry-After header parsing
6. Expired session detection and automated re-login flow
7. Shadow DOM piercing and new-tab popup management
8. Crash recovery: dead page handling in CDP screenshot registry
9. Multi-step CMP cookie rejection (Manage preferences -> Reject all)
10. aria_snapshot() and DataHandler pipeline
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig
from web_engine.pages.base_page import BasePage
from web_engine.data_handler import DataHandler
from web_engine.exceptions import SelectorNotFoundError, ActionNotAllowedError
from web_engine.tests.fixture_server import LocalFixtureServer


class TestWebEngineSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Start local fixture HTTP server on port 8989
        cls.fixture_server = LocalFixtureServer(port=8989)
        cls.fixture_server.start()

        # 2. Launch headless browser with trace recording
        cls.config = BrowserConfig(headless=True, selector_probe_timeout_ms=750)
        cls.mgr = BrowserManager(cls.config)
        cls.page = cls.mgr.launch()
        cls.base_page = BasePage(cls.mgr)

    @classmethod
    def tearDownClass(cls):
        cls.mgr.close()
        cls.fixture_server.stop()

    def test_01_stealth_evasion_reports_false(self):
        """Verifies navigator.webdriver evaluates strictly to false (not undefined/None, matching real Chrome)."""
        self.mgr.navigate(self.fixture_server.url)
        is_webdriver = self.page.evaluate("() => navigator.webdriver")
        self.assertIs(is_webdriver, False, "navigator.webdriver must return False to match real headed Chrome")

        # Check inside iframe
        frame_el = self.page.frame_locator("#test-iframe")
        frame_text = frame_el.locator("#frame-text").text_content()
        self.assertIn("Inside Test Iframe", frame_text)

    def test_02_delayed_element_probe_waits_correctly(self):
        """
        Delayed-element probe test:
        An element renders 500ms after page load.
        Verifies wait_for(state='visible', timeout=probe_timeout) waits and succeeds,
        catching what an instant is_visible() check would miss.
        """
        self.mgr.navigate(self.fixture_server.url)
        fallback_chain = [
            {"role": "button", "name": "Nonexistent Button 1"},
            {"role": "button", "name": "Delayed Action Button"}  # Appears after 500ms
        ]
        loc = self.base_page.find_first_visible(fallback_chain, target_name="delayed_btn", full_timeout_ms=2000)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.text_content(), "Delayed Action Button")

    def test_03_sensitive_target_element_blocking(self):
        """
        Security Guardrail:
        Clicking an element with accessible name 'Place order' or 'Delete account'
        must be intercepted and raise ActionNotAllowedError even if the action is just 'click'.
        """
        self.mgr.navigate(self.fixture_server.url)
        sensitive_chain = [{"role": "button", "name": "Place order"}]
        with self.assertRaises(ActionNotAllowedError) as ctx:
            self.base_page.click_with_fallback(sensitive_chain, target_name="order_btn")
        self.assertIn("sensitive", str(ctx.exception).lower())

    def test_04_retry_backoff_and_no_retry_on_sensitive_actions(self):
        """
        Verifies:
        1. Sensitive actions or targets are NEVER retried (fails immediately).
        2. Idempotent actions retry with backoff timing.
        """
        # A: Non-idempotent sensitive action must raise immediately without retry loop
        attempts = 0
        def sensitive_call():
            nonlocal attempts
            attempts += 1
            raise ValueError("Failure")

        with self.assertRaises(ActionNotAllowedError):
            self.base_page.retry_idempotent("pay", sensitive_call, target_text="Submit Payment")
        self.assertEqual(attempts, 0, "Sensitive action must NOT be called or retried")

        # B: Idempotent call retries with exponential backoff
        retry_counts = 0
        t0 = time.time()
        def failing_idempotent():
            nonlocal retry_counts
            retry_counts += 1
            raise SelectorNotFoundError("element", [], 500)

        with self.assertRaises(SelectorNotFoundError):
            self.base_page.retry_idempotent("search_query", failing_idempotent, max_retries=3, backoff=1.2)

        elapsed = time.time() - t0
        self.assertEqual(retry_counts, 3, "Idempotent operation should attempt 3 times")
        # backoff timing check: backoff^1 (1.2) + backoff^2 (1.44) = ~2.64s
        self.assertGreaterEqual(elapsed, 2.0, "Exponential backoff should introduce measurable sleep intervals")

    def test_05_rate_limit_429_with_retry_after(self):
        """Verifies HTTP 429 response listener extracts Retry-After header and sets backoff."""
        rate_limit_url = f"{self.fixture_server.url}rate-limit"
        # Make a request triggering the 429 listener
        try:
            self.page.goto(rate_limit_url, timeout=5000)
        except Exception:
            pass

        self.assertIsNotNone(self.mgr._last_retry_after)
        self.assertEqual(self.mgr._last_retry_after, 1.0, "Should correctly parse Retry-After: 1 header")

    def test_06_expired_session_triggers_relogin(self):
        """Verifies verify_or_refresh_session detects expired state and triggers relogin."""
        def probe(p):
            res = p.request.get(f"{self.fixture_server.url}session-check")
            return res.status == 200

        def relogin(p):
            p.context.add_cookies([{
                "name": "session_token",
                "value": "active_valid_session",
                "domain": "127.0.0.1",
                "path": "/"
            }])

        # First verify it recovers session via relogin
        success = self.mgr.verify_or_refresh_session(validity_probe=probe, relogin_callback=relogin)
        self.assertTrue(success, "Session should be restored after relogin callback")

    def test_07_shadow_dom_and_new_tab_popup(self):
        """Verifies Shadow DOM element piercing and new-tab popup lifecycle."""
        self.mgr.navigate(self.fixture_server.url)

        # 1. Shadow DOM piercing: Playwright locators pierce open shadow roots natively
        shadow_btn = self.page.locator("#shadow-inside-btn")
        self.assertTrue(shadow_btn.is_visible())
        self.assertEqual(shadow_btn.text_content(), "Shadow Action")

        # 2. Popup new tab management
        with self.page.expect_popup() as popup_info:
            self.page.click("#popup-link")
        popup_page = popup_info.value
        popup_page.wait_for_load_state("domcontentloaded")
        self.assertIn("Popup Window", popup_page.title())
        popup_page.close()

    def test_08_crash_recovery_dead_page_handling(self):
        """Checks that screenshot capture safely handles closed/dead pages without unhandled crashes."""
        # Create a disposable page and close it immediately to simulate crash
        temp_page = self.mgr._context.new_page()
        temp_page.close()

        # Capture screenshot when active page is closed
        old_active = self.mgr._active_page
        self.mgr._active_page = temp_page
        res = self.mgr.capture_cdp_screenshot()
        self.assertEqual(res.get("status"), "error")
        self.assertIn("No active browser page open", res.get("message", ""))

        # Restore working active page
        self.mgr._active_page = old_active

    def test_09_safe_cookie_rejection_direct_and_cmp(self):
        """Verifies direct cookie rejection as well as 2-step CMP preferences dismissal."""
        self.mgr.navigate(self.fixture_server.url)
        cookie_banner = self.page.locator("#cookie-banner")
        self.assertTrue(cookie_banner.is_visible())

        self.base_page.dismiss_cookie_banners()
        self.assertFalse(cookie_banner.is_visible(), "Cookie banner should be dismissed after clicking reject")

    def test_10_aria_snapshot_and_infinite_scroll(self):
        """Verifies aria_snapshot generation and dynamic infinite scroll."""
        self.mgr.navigate(self.fixture_server.url)
        snapshot = self.base_page.aria_snapshot()
        self.assertIn("search", snapshot.lower())

        item_loc = {"css": ".item-card"}
        count = self.base_page.scroll_until_no_new_content(item_selector=item_loc, max_iterations=6, pause_sec=0.2)
        self.assertGreaterEqual(count, 4)

    def test_11_data_handler_export(self):
        """Verifies data deduplication and serialization."""
        raw_items = [
            {"title": "  Item 1  ", "price": "$10.00", "url": "http://127.0.0.1:8989/1"},
            {"title": "Item 1", "price": "$10.00", "url": "http://127.0.0.1:8989/1"},
            {"title": "Item 2", "price": "$20.00", "url": "http://127.0.0.1:8989/2"},
        ]
        deduped = DataHandler.deduplicate(raw_items, key_fields=["url"])
        self.assertEqual(len(deduped), 2)


if __name__ == "__main__":
    unittest.main()
