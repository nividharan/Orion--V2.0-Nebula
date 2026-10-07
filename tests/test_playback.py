"""
tests/test_playback.py — Phase 5 exit criteria
================================================
Deterministic test suite for verify/playback.py using local video_fixture.html.
No external network, no live YouTube dependencies, 100% deterministic.

Exit criteria (from plan):
  ✓ Fixture video page tests cover paused, ad-playing, and active playback states.
  ✓ Surgical healing (dismiss consent, skip ad, video.play unpause) without blind keypresses.
  ✓ Viewport screenshot capture with sensitive input redaction.
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_engine.browser_manager import BrowserManager
from web_engine.config import BrowserConfig
from verify.playback import (
    PlaybackState,
    verify_playback,
    heal_playback,
    ensure_video_playing,
    skip_ad_if_available,
    dismiss_consent_modals,
    capture_playback_viewport_safe,
)


class TestPlaybackVerification(unittest.TestCase):
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
        self.mgr.navigate(self.fixture_url)
        # Reset to base state
        self.page.evaluate("() => window.setMockState('paused')")

    def test_01_verify_no_video_on_empty_page(self):
        """Verifies status is NO_VIDEO when no HTML5 video exists in DOM."""
        self.mgr.navigate("about:blank")
        state = verify_playback(self.page)
        self.assertFalse(state.has_video)
        self.assertFalse(state.is_playing)
        self.assertEqual(state.status, "NO_VIDEO")

    def test_02_verify_paused_state(self):
        """Verifies detection of paused video state."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('paused')")
        state = verify_playback(self.page)
        self.assertTrue(state.has_video)
        self.assertTrue(state.is_paused)
        self.assertFalse(state.is_playing)
        self.assertFalse(state.ad_showing)
        self.assertEqual(state.status, "PAUSED")

    def test_03_verify_active_playback_state(self):
        """Verifies detection of actively playing video state."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('active_playing')")
        state = verify_playback(self.page)
        self.assertTrue(state.has_video)
        self.assertFalse(state.is_paused)
        self.assertTrue(state.is_playing)
        self.assertEqual(state.status, "PLAYING")

    def test_04_verify_skippable_ad_state(self):
        """Verifies detection of skippable ad overlay."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('ad_skippable')")
        state = verify_playback(self.page)
        self.assertTrue(state.has_video)
        self.assertTrue(state.ad_showing)
        self.assertTrue(state.can_skip_ad)
        self.assertEqual(state.status, "AD_SKIPPABLE")

    def test_05_verify_unskippable_ad_state(self):
        """Verifies detection of ad showing before skip button appears."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('ad_unskippable')")
        state = verify_playback(self.page)
        self.assertTrue(state.has_video)
        self.assertTrue(state.ad_showing)
        self.assertFalse(state.can_skip_ad)
        self.assertEqual(state.status, "AD_PLAYING")

    def test_06_verify_consent_blocked_state(self):
        """Verifies detection of consent modal blocking video playback."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('consent_blocked')")
        state = verify_playback(self.page)
        self.assertTrue(state.has_consent_modal)
        self.assertEqual(state.status, "CONSENT_BLOCKED")

    def test_07_ensure_video_playing_unpauses(self):
        """Surgically calls video.play() to unpause without keyboard simulation."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('paused')")
        
        # Verify it is paused
        init_state = verify_playback(self.page)
        self.assertTrue(init_state.is_paused)

        # Call surgical ensure_video_playing
        success = ensure_video_playing(self.page)
        self.assertTrue(success)

        # Confirm state is now playing
        post_state = verify_playback(self.page)
        self.assertTrue(post_state.is_playing)
        self.assertFalse(post_state.is_paused)

    def test_08_skip_ad_if_available(self):
        """Clicks YouTube Skip Ad button and verifies ad is cleared."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('ad_skippable')")

        state_before = verify_playback(self.page)
        self.assertTrue(state_before.ad_showing)
        self.assertTrue(state_before.can_skip_ad)

        clicked = skip_ad_if_available(self.page)
        self.assertTrue(clicked)

        state_after = verify_playback(self.page)
        self.assertFalse(state_after.ad_showing)
        self.assertTrue(state_after.is_playing)

    def test_09_dismiss_consent_modals(self):
        """Clicks Reject/Accept on consent banner."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('consent_blocked')")

        state_before = verify_playback(self.page)
        self.assertTrue(state_before.has_consent_modal)

        dismissed = dismiss_consent_modals(self.page)
        self.assertTrue(dismissed)

        state_after = verify_playback(self.page)
        self.assertFalse(state_after.has_consent_modal)

    def test_10_heal_playback_from_paused(self):
        """End-to-end self-healing from paused video state."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('paused')")

        final_state = heal_playback(self.page, max_retries=2, probe_delay=0.1)
        self.assertTrue(final_state.is_playing)
        self.assertEqual(final_state.status, "PLAYING")

    def test_11_heal_playback_from_skippable_ad(self):
        """End-to-end self-healing from skippable ad state."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('ad_skippable')")

        final_state = heal_playback(self.page, max_retries=2, probe_delay=0.1)
        self.assertFalse(final_state.ad_showing)
        self.assertTrue(final_state.is_playing)
        self.assertEqual(final_state.status, "PLAYING")

    def test_12_heal_playback_from_consent_blocked(self):
        """End-to-end self-healing from consent-blocked state."""
        self.mgr.navigate(self.fixture_url)
        self.page.evaluate("() => window.setMockState('consent_blocked')")

        final_state = heal_playback(self.page, max_retries=2, probe_delay=0.1)
        self.assertFalse(final_state.has_consent_modal)
        self.assertTrue(final_state.is_playing)
        self.assertEqual(final_state.status, "PLAYING")

    def test_13_capture_playback_viewport_safe(self):
        """Captures safe viewport screenshot with sensitive fields redacted."""
        self.mgr.navigate(self.fixture_url)
        test_out = str(PROJECT_ROOT / ".cache" / "test_screenshot.png")
        
        path = capture_playback_viewport_safe(self.page, output_path=test_out, redact_inputs=True)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

        # Verify redaction style is cleaned up
        has_temp_style = self.page.evaluate("() => Boolean(document.getElementById('__orion_redact_style__'))")
        self.assertFalse(has_temp_style, "Temporary redaction style must be cleaned up after capture")

    def test_14_playback_state_to_dict(self):
        """Verifies PlaybackState serialization."""
        s = PlaybackState(
            has_video=True,
            is_playing=True,
            is_paused=False,
            ad_showing=False,
            can_skip_ad=False,
            current_time=12.345,
            duration=180.0,
            status="PLAYING"
        )
        d = s.to_dict()
        self.assertEqual(d["current_time"], 12.35)
        self.assertEqual(d["status"], "PLAYING")
        self.assertTrue(d["has_video"])


if __name__ == "__main__":
    unittest.main()
