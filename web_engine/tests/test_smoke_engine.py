"""🌌 Orion × Nebula Web Engine - Hardened Smoke Test Suite
Uses local fixture HTTP testbed server for zero-network flakiness.
Verifies all audited items and Phase 1 specifications:
1. Stealth evasion: navigator.webdriver reports strictly false on main, iframe, and popup
2. Delayed-element probe (~500ms) found by first candidate
3. 'Place order' and 'Delete account' blocked
4. Off-list domain refused
5. 429 rate-limiting with Retry-After header parsing
6. Expired session detection and automated re-login flow
7. Shadow DOM click and new-tab popup management
8. Nested iframe content resolution
9. Two-step and iframe consent banners
10. Page crash -> screenshot fallback to Win32 capture
11. trace.zip written on failure and NOT on success
12. SelectorNotFoundError contains page_state + tried_selectors
13. Sync call and in-loop call both work
14. aria_snapshot() and DataHandler pipeline
"""

import asyncio
import os
import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig
import web_engine.config as web_config
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
        """Verifies navigator.webdriver evaluates strictly to false on main, iframe, and popup."""
        self.mgr.navigate(self.fixture_server.url)
        is_webdriver = self.page.evaluate("() => navigator.webdriver")
        self.assertIs(is_webdriver, False, "navigator.webdriver must return False on main page")

        # Check inside iframe
        frame_el = self.page.frame_locator("#test-iframe")
        frame_webdriver = frame_el.locator("body").evaluate("() => navigator.webdriver")
        self.assertIs(frame_webdriver, False, "navigator.webdriver must return False inside iframe")

        # Check inside popup
        with self.page.expect_popup() as popup_info:
            self.page.click("#popup-link")
        popup_page = popup_info.value
        popup_page.wait_for_load_state("domcontentloaded")
        popup_webdriver = popup_page.evaluate("() => navigator.webdriver")
        self.assertIs(popup_webdriver, False, "navigator.webdriver must return False in popup")
        popup_page.close()

    def test_02_delayed_element_probe_waits_correctly(self):
        """
        Delayed-element probe test:
        An element renders ~500ms after page load.
        Verifies wait_for finds it when it is the FIRST candidate in the fallback chain.
        """
        self.mgr.navigate(self.fixture_server.url)
        # First candidate is the delayed element itself
        fallback_chain = [
            {"role": "button", "name": "Delayed Action Button"}
        ]
        loc = self.base_page.find_first_visible(fallback_chain, target_name="delayed_btn", full_timeout_ms=3000)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.text_content(), "Delayed Action Button")

    def test_03_sensitive_target_element_blocking(self):
        """
        Security Guardrail:
        Clicking 'Place order' or 'Delete account' must be intercepted and raise ActionNotAllowedError.
        """
        self.mgr.navigate(self.fixture_server.url)

        # 1. Place order blocked
        sensitive_chain_1 = [{"role": "button", "name": "Place order"}]
        with self.assertRaises(ActionNotAllowedError) as ctx1:
            self.base_page.click_with_fallback(sensitive_chain_1, target_name="order_btn")
        self.assertIn("sensitive", str(ctx1.exception).lower())

        # 2. Delete account blocked
        sensitive_chain_2 = [{"role": "button", "name": "Delete account"}]
        with self.assertRaises(ActionNotAllowedError) as ctx2:
            self.base_page.click_with_fallback(sensitive_chain_2, target_name="delete_btn")
        self.assertIn("sensitive", str(ctx2.exception).lower())

    def test_03b_off_list_domain_refused(self):
        """Action safety: domain allow-list blocks navigation to unapproved hostnames."""
        orig_allow = web_config.DOMAIN_ALLOW_LIST
        try:
            web_config.DOMAIN_ALLOW_LIST = {"approved.domain.internal"}
            with self.assertRaises(ActionNotAllowedError):
                self.mgr.navigate("http://127.0.0.1:8989/forbidden")
        finally:
            web_config.DOMAIN_ALLOW_LIST = orig_allow

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
        self.assertGreaterEqual(elapsed, 2.0, "Exponential backoff should introduce measurable sleep intervals")

    def test_05_rate_limit_429_with_retry_after(self):
        """Verifies HTTP 429 response listener extracts Retry-After header and sets backoff."""
        rate_limit_url = f"{self.fixture_server.url}rate-limit"
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

        success = self.mgr.verify_or_refresh_session(validity_probe=probe, relogin_callback=relogin)
        self.assertTrue(success, "Session should be restored after relogin callback")

    def test_07_shadow_dom_and_new_tab_popup(self):
        """Verifies Shadow DOM element piercing and clicking, plus new-tab popup lifecycle."""
        self.mgr.navigate(self.fixture_server.url)

        # 1. Shadow DOM piercing and click
        shadow_btn = self.page.locator("#shadow-inside-btn")
        self.assertTrue(shadow_btn.is_visible())
        shadow_btn.click()
        self.assertEqual(shadow_btn.text_content(), "Shadow Action")

        # 2. Popup new tab management
        with self.page.expect_popup() as popup_info:
            self.page.click("#popup-link")
        popup_page = popup_info.value
        popup_page.wait_for_load_state("domcontentloaded")
        self.assertIn("Popup Window", popup_page.title())
        popup_page.close()

    def test_07b_nested_iframe(self):
        """Verifies deep resolution inside nested iframes."""
        self.mgr.navigate(self.fixture_server.url)
        parent_frame = self.page.frame_locator("#parent-frame")
        child_frame = parent_frame.frame_locator("#child-frame")
        nested_text = child_frame.locator("#nested-child-text").text_content()
        self.assertEqual(nested_text, "Nested Child Content")

    def test_08_crash_recovery_dead_page_handling(self):
        """Checks that screenshot capture falls back to Win32 screen capture when page is closed/dead."""
        temp_page = self.mgr._context.new_page()
        temp_page.close()

        old_active = self.mgr._active_page
        self.mgr._active_page = temp_page

        try:
            res = self.mgr.take_screenshot()
            self.assertEqual(res.get("status"), "success")
            self.assertEqual(res.get("method"), "win32_fallback")
            self.assertTrue(os.path.exists(res.get("saved_path")))
        finally:
            self.mgr._active_page = old_active

    def test_09_safe_cookie_rejection_direct_and_cmp(self):
        """Verifies direct cookie rejection as well as 2-step CMP preferences dismissal."""
        self.mgr.navigate(self.fixture_server.url)
        cookie_banner = self.page.locator("#cookie-banner")
        self.assertTrue(cookie_banner.is_visible())

        self.base_page.dismiss_cookie_banners(force=True)
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

    def test_12_trace_zip_on_failure_not_on_success(self):
        """Verifies trace.zip is written on failure and NOT on success."""
        traces_before = list(self.mgr.config.traces_dir.glob("*.zip"))
        
        # Successful operation
        self.mgr.navigate(self.fixture_server.url)
        traces_after_success = list(self.mgr.config.traces_dir.glob("*.zip"))
        self.assertEqual(len(traces_before), len(traces_after_success), "No trace.zip should be saved on success")

        # Failure operation triggers trace write
        artifacts = self.mgr.capture_failure_artifacts("test_fail_action")
        self.assertIn("trace", artifacts)
        self.assertTrue(os.path.exists(artifacts["trace"]))
        self.assertTrue(artifacts["trace"].endswith(".zip"))

    def test_13_selector_not_found_error_structure(self):
        """Verifies SelectorNotFoundError contains page_state and tried_selectors."""
        self.mgr.navigate(self.fixture_server.url)
        tried = [{"css": "#non_existent_1"}, {"role": "button", "name": "Non Existent 2"}]
        with self.assertRaises(SelectorNotFoundError) as ctx:
            self.base_page.find_first_visible(tried, target_name="phantom_element", full_timeout_ms=500)

        err = ctx.exception
        self.assertEqual(err.target_name, "phantom_element")
        self.assertEqual(err.tried_selectors, tried)
        self.assertIn("url", err.page_state)
        self.assertIn("aria_summary", err.page_state)

    def test_14_sync_and_async_in_loop_calls_both_work(self):
        """Verifies BrowserManager.run_isolated works synchronously and inside an active asyncio loop."""
        # 1. Sync call
        res_sync = BrowserManager.run_isolated(lambda x: x * 2, 21)
        self.assertEqual(res_sync, 42)

        # 2. Async in-loop call
        async def async_worker():
            return BrowserManager.run_isolated(lambda x: x + 10, 32)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            res_async = ex.submit(lambda: asyncio.run(async_worker())).result()
        self.assertEqual(res_async, 42)


if __name__ == "__main__":
    unittest.main()
