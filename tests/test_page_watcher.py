"""
tests/test_page_watcher.py — Phase 6 exit criteria
===================================================
Deterministic test suite for verify/page_watcher.py.
Covers:
  ✓ DOM-state checks: error pages (404/500/503), dialogs/modals, login redirects.
  ✓ Page screenshot hash diff: detect no-change-after-action.
  ✓ Detect frozen page across consecutive frame history.
  ✓ Sensitive page guards: password/payment protection.
  ✓ Zero disk bloat on success; screenshot saved only on fail/uncertain.
  ✓ 24-hour artifact retention cleanup.
  ✓ Playwright integration with local video_fixture.html.
"""

import io
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

from verify.page_watcher import (
    PageWatcher,
    WatchResult,
    Verdict,
    calculate_visual_diff_pct,
    _compute_image_hash,
    _calculate_pixel_delta_pct,
)
from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig


def _create_dummy_png(color: str = "white", size: tuple = (100, 100)) -> bytes:
    """Creates in-memory PNG bytes of a solid color image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestPageWatcherDOMChecks(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = PROJECT_ROOT / ".cache" / "test_watcher_tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.watcher = PageWatcher(artifacts_dir=self.tmp_dir)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_page_none_or_closed_fails(self):
        res, signal, ev = self.watcher.check_dom_state(None)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "page_closed")

        mock_page = MagicMock()
        mock_page.is_closed.return_value = True
        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "page_closed")

    def test_error_page_detected_in_title(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/missing"
        mock_page.title.return_value = "404 Not Found - Error"
        mock_page.locator.return_value.count.return_value = 0
        mock_page.locator.return_value.all.return_value = []
        mock_page.locator.return_value.inner_text.return_value = ""

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "error_page")
        self.assertIn("detail", ev)

    def test_error_page_detected_in_body(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/status"
        mock_page.title.return_value = "Status Page"
        
        # When checking password/dialogs count is 0; when checking body inner_text is 503
        def mock_locator(selector):
            loc = MagicMock()
            if selector == "body":
                loc.inner_text.return_value = "503 Service Unavailable - The server is temporarily busy"
            else:
                loc.count.return_value = 0
                loc.all.return_value = []
                loc.inner_text.return_value = ""
            return loc

        mock_page.locator.side_effect = mock_locator

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "error_page")

    def test_login_redirect_detected_by_url(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/signin?redirect=home"
        mock_page.title.return_value = "Welcome"

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "login_redirect")

    def test_login_redirect_detected_by_password_field(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/gateway"
        mock_page.title.return_value = "Portal"

        def mock_locator(selector):
            loc = MagicMock()
            if "password" in selector:
                loc.count.return_value = 1
            else:
                loc.count.return_value = 0
                loc.all.return_value = []
                loc.inner_text.return_value = ""
            return loc

        mock_page.locator.side_effect = mock_locator

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "login_redirect")

    def test_unexpected_dialog_detected(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/dashboard"
        mock_page.title.return_value = "Dashboard"

        mock_dialog = MagicMock()
        mock_dialog.is_visible.return_value = True
        mock_dialog.inner_text.return_value = "Blocking Modal Dialog Message"

        def mock_locator(selector):
            loc = MagicMock()
            loc.count.return_value = 0
            if "[role='dialog']" in selector:
                loc.all.return_value = [mock_dialog]
            else:
                loc.all.return_value = []
                loc.inner_text.return_value = ""
            return loc

        mock_page.locator.side_effect = mock_locator

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "dialog_detected")
        self.assertIn("Blocking Modal Dialog Message", ev.get("modal_sample", ""))

    def test_clean_page_dom_ok(self):
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com/articles"
        mock_page.title.return_value = "Articles Archive"

        def mock_locator(selector):
            loc = MagicMock()
            loc.count.return_value = 0
            loc.all.return_value = []
            loc.inner_text.return_value = "Welcome to our knowledge archive"
            return loc

        mock_page.locator.side_effect = mock_locator

        res, signal, ev = self.watcher.check_dom_state(mock_page)
        self.assertEqual(res, Verdict.OK)
        self.assertEqual(signal, "ok")


class TestPageWatcherVisualDiff(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = PROJECT_ROOT / ".cache" / "test_watcher_visual"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.watcher = PageWatcher(artifacts_dir=self.tmp_dir)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_calculate_visual_diff_pct(self):
        img_white = _create_dummy_png("white")
        img_black = _create_dummy_png("black")

        # Identical
        self.assertEqual(calculate_visual_diff_pct(img_white, img_white), 0.0)
        # Maximal difference (white vs black)
        self.assertEqual(calculate_visual_diff_pct(img_white, img_black), 100.0)
        # Empty/None
        self.assertEqual(calculate_visual_diff_pct(None, img_white), 100.0)

    def test_identical_screenshots_expect_change_fails_and_saves_artifact(self):
        img_white = _create_dummy_png("white")

        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Normal"
        mock_page.locator.return_value.count.return_value = 0
        mock_page.locator.return_value.all.return_value = []
        mock_page.locator.return_value.inner_text.return_value = ""

        result: WatchResult = self.watcher.verify_action_result(
            mock_page,
            before_screenshot=img_white,
            after_screenshot=img_white,
            expect_visual_change=True,
        )

        self.assertEqual(result.verdict, Verdict.FAIL)
        self.assertEqual(result.signal, "no_change")
        self.assertIsNotNone(result.screenshot_path)
        self.assertTrue(Path(result.screenshot_path).exists())

    def test_identical_screenshots_no_expect_change_passes(self):
        img_white = _create_dummy_png("white")

        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Normal"
        mock_page.locator.return_value.count.return_value = 0
        mock_page.locator.return_value.all.return_value = []
        mock_page.locator.return_value.inner_text.return_value = ""

        result: WatchResult = self.watcher.verify_action_result(
            mock_page,
            before_screenshot=img_white,
            after_screenshot=img_white,
            expect_visual_change=False,
        )

        self.assertEqual(result.verdict, Verdict.OK)
        self.assertEqual(result.signal, "ok")
        # Zero disk bloat on success
        self.assertIsNone(result.screenshot_path)

    def test_differing_screenshots_passes(self):
        img_white = _create_dummy_png("white")
        img_black = _create_dummy_png("black")

        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.url = "https://example.com"
        mock_page.title.return_value = "Normal"
        mock_page.locator.return_value.count.return_value = 0
        mock_page.locator.return_value.all.return_value = []
        mock_page.locator.return_value.inner_text.return_value = ""

        result: WatchResult = self.watcher.verify_action_result(
            mock_page,
            before_screenshot=img_white,
            after_screenshot=img_black,
            expect_visual_change=True,
        )

        self.assertEqual(result.verdict, Verdict.OK)
        self.assertEqual(result.signal, "ok")
        self.assertGreater(result.evidence.get("hash_delta", 0), 0)
        self.assertIsNone(result.screenshot_path)


class TestPageWatcherFrozenDetection(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = PROJECT_ROOT / ".cache" / "test_watcher_frozen"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.watcher = PageWatcher(artifacts_dir=self.tmp_dir)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_frozen_frames_detected_and_saved(self):
        frame = _create_dummy_png("blue")
        history = [frame, frame, frame, frame]

        res = self.watcher.detect_frozen_page(history, interval_sec=1.0)
        self.assertEqual(res.verdict, Verdict.FAIL)
        self.assertEqual(res.signal, "frozen")
        self.assertEqual(res.evidence.get("frames"), 4)
        self.assertIsNotNone(res.screenshot_path)
        self.assertTrue(Path(res.screenshot_path).exists())

    def test_moving_frames_return_ok(self):
        f1 = _create_dummy_png("red")
        f2 = _create_dummy_png("green")
        history = [f1, f2]

        res = self.watcher.detect_frozen_page(history)
        self.assertEqual(res.verdict, Verdict.OK)
        self.assertEqual(res.signal, "ok")
        self.assertIsNone(res.screenshot_path)

    def test_single_frame_returns_ok(self):
        f1 = _create_dummy_png("white")
        res = self.watcher.detect_frozen_page([f1])
        self.assertEqual(res.verdict, Verdict.OK)


class TestPageWatcherSensitiveGuard(unittest.TestCase):
    def setUp(self):
        self.watcher = PageWatcher()

    def test_sensitive_keywords_detected(self):
        mock_page = MagicMock()
        mock_page.url = "https://example.com/checkout/step2"
        mock_page.title.return_value = "Checkout Order"
        mock_page.locator.return_value.count.return_value = 0

        self.assertTrue(self.watcher._is_sensitive_page(mock_page))

    def test_sensitive_password_input_detected(self):
        mock_page = MagicMock()
        mock_page.url = "https://example.com/account"
        mock_page.title.return_value = "Settings"

        def mock_locator(sel):
            loc = MagicMock()
            loc.count.return_value = 1 if "password" in sel else 0
            return loc

        mock_page.locator.side_effect = mock_locator
        self.assertTrue(self.watcher._is_sensitive_page(mock_page))

    def test_sensitive_credit_card_detected(self):
        mock_page = MagicMock()
        mock_page.url = "https://example.com/subscribe"
        mock_page.title.return_value = "Plans"

        def mock_locator(sel):
            loc = MagicMock()
            loc.count.return_value = 1 if "cc-number" in sel else 0
            return loc

        mock_page.locator.side_effect = mock_locator
        self.assertTrue(self.watcher._is_sensitive_page(mock_page))

    def test_non_sensitive_page_passes(self):
        mock_page = MagicMock()
        mock_page.url = "https://example.com/search?q=weather"
        mock_page.title.return_value = "Weather Report"
        mock_page.locator.return_value.count.return_value = 0

        self.assertFalse(self.watcher._is_sensitive_page(mock_page))


class TestPageWatcherArtifactRetention(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = PROJECT_ROOT / ".cache" / "test_watcher_retention"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.watcher = PageWatcher(retention_hours=24.0, artifacts_dir=self.tmp_dir)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cleanup_old_images_deletes_expired(self):
        # 1. Create an old image (25 hours ago)
        old_file = self.tmp_dir / "fail_old_123.png"
        old_file.write_bytes(b"dummy_png_bytes")
        old_time = time.time() - (25 * 3600)
        os.utime(str(old_file), (old_time, old_time))

        # 2. Create a recent image (1 hour ago)
        new_file = self.tmp_dir / "fail_recent_456.png"
        new_file.write_bytes(b"dummy_png_bytes")
        new_time = time.time() - (1 * 3600)
        os.utime(str(new_file), (new_time, new_time))

        deleted = self.watcher.cleanup_old_images()
        self.assertEqual(deleted, 1)
        self.assertFalse(old_file.exists())
        self.assertTrue(new_file.exists())


class TestPageWatcherPlaywrightFixtureIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "video_fixture.html"
        cls.fixture_url = cls.fixture_path.resolve().as_uri()

        cls.config = BrowserConfig(headless=True, selector_probe_timeout_ms=750)
        cls.mgr = BrowserManager(cls.config)
        cls.page = cls.mgr.launch()

    @classmethod
    def tearDownClass(cls):
        cls.mgr.close()

    def setUp(self):
        self.tmp_dir = PROJECT_ROOT / ".cache" / "test_watcher_pw"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.watcher = PageWatcher(artifacts_dir=self.tmp_dir)
        self.mgr.navigate(self.fixture_url)

    def tearDown(self):
        if self.tmp_dir.exists():
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_fixture_modal_dialog_detected(self):
        # Trigger consent modal blocked state
        self.page.evaluate("() => window.setMockState('consent_blocked')")
        res, signal, ev = self.watcher.check_dom_state(self.page)
        self.assertEqual(res, Verdict.FAIL)
        self.assertEqual(signal, "dialog_detected")
        self.assertIn("modal_sample", ev)

    def test_fixture_sensitive_section_detected(self):
        # The fixture contains password and credit card inputs
        self.assertTrue(self.watcher._is_sensitive_page(self.page))

    def test_watch_page_action_helper(self):
        # Dismiss cookie banner via button click inside watch_page_action
        self.page.evaluate("() => window.setMockState('consent_blocked')")
        
        # When banner is showing, check_dom_state is FAIL.
        res_before = self.watcher.verify_action_result(self.page, expect_visual_change=False)
        self.assertEqual(res_before.verdict, Verdict.FAIL)

        # Now dismiss banner via action
        action_res = self.watcher.watch_page_action(
            self.page,
            action=lambda: self.page.evaluate("() => window.setMockState('active_playing')"),
            expect_visual_change=False
        )
        self.assertEqual(action_res.verdict, Verdict.OK)


if __name__ == "__main__":
    unittest.main()
