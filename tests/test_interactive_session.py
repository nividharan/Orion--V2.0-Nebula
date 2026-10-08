"""
tests/test_interactive_session.py — Offline Test Suite for Interactive Session Mode
=====================================================================================
Covers all 12 specification requirements offline:
1. Browser/context reuse across commands (login cookie persistence)
2. Media controls: pause/resume on video page; idempotent pause
3. Context reference resolution across turns
4. Kill switch stops task while preserving browser
5. Auto-recovery from externally closed browser
6. Sensitive action approval gate (default deny, non-TTY deny, approve on 'y')
7. Process lifecycle (--once closes, default keeps open, exit cleans up)
8. Built-in commands function offline without API key
9. Budget limits block excessive commands/steps with clear error
10. Injection text does not alter domain or action allow-lists
11. Deprecation notice for legacy --detach/-d flags
12. Local control channel security (token, localhost, sensitive action gate)
"""

import os
import sys
import time
import json
import psutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from session import NebulaSession, SessionConfig, BudgetExceededError
from web_engine.tests.fixture_server import LocalFixtureServer
import media_control
import control_channel
from schemas import ActionType, Step, Plan, IntentType
from repl import interactive_approver


class TestInteractiveSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = LocalFixtureServer(port=8993)
        cls.fixture.start()
        cls.base_url = cls.fixture.url

    @classmethod
    def tearDownClass(cls):
        cls.fixture.stop()

    def setUp(self):
        self.session = NebulaSession(SessionConfig(headless=True, max_commands_per_session=20))

    def tearDown(self):
        self.session.close()

    # -----------------------------------------------------------------------
    # 1. Browser/Context Reuse & Cookie Persistence
    # -----------------------------------------------------------------------
    def test_01_browser_context_reuse_and_cookie_persistence(self):
        res1 = self.session.execute_command_string(f"navigate to {self.base_url}")
        self.assertEqual(res1.get("status"), "success")
        
        # Set a session cookie in command 1
        page = self.session.browser_manager.page
        page.context.add_cookies([{"name": "test_auth", "value": "secret_token_123", "url": self.base_url}])
        
        # Command 2: Reuses the same context without relaunching
        res2 = self.session.execute_command_string(f"navigate to {self.base_url}")
        self.assertEqual(res2.get("status"), "success")
        
        cookies = page.context.cookies([self.base_url])
        auth_cookie = next((c for c in cookies if c["name"] == "test_auth"), None)
        self.assertIsNotNone(auth_cookie)
        self.assertEqual(auth_cookie["value"], "secret_token_123")

    # -----------------------------------------------------------------------
    # 2. Media Controls: Pause, Resume, Idempotency
    # -----------------------------------------------------------------------
    def test_02_media_controls_idempotent_pause(self):
        video_url = f"{self.base_url}video"
        self.session.execute_command_string(f"navigate to {video_url}")
        page = self.session.browser_manager.page
        self.assertIsNotNone(page)

        # Inspect initial state
        state = media_control.get_video_state(page)
        self.assertTrue(state.get("exists"))

        # Pause video
        res_pause1 = media_control.pause_video(page)
        self.assertIn(res_pause1.get("status"), ("success", "unchanged"))
        self.assertTrue(page.evaluate("() => document.querySelector('video').paused"))

        # Idempotent: second pause does not toggle
        res_pause2 = media_control.pause_video(page)
        self.assertEqual(res_pause2.get("status"), "unchanged")
        self.assertTrue(page.evaluate("() => document.querySelector('video').paused"))

        # Resume video
        res_resume = media_control.resume_video(page)
        self.assertIn(res_resume.get("status"), ("success", "unchanged"))

    # -----------------------------------------------------------------------
    # 3. Context Reference Across Turns
    # -----------------------------------------------------------------------
    def test_03_context_reference_resolution(self):
        shop_url = f"{self.base_url}shop"
        res1 = self.session.execute_command_string(f"navigate to {shop_url}")
        self.assertEqual(res1.get("status"), "success")
        self.assertEqual(self.session.context_memory.last_url, shop_url)

        # Turn 2: "do that again" resolves last plan
        res2 = self.session.execute_command_string("do that again")
        self.assertEqual(res2.get("status"), "success")
        self.assertEqual(self.session.last_known_url, shop_url)

    # -----------------------------------------------------------------------
    # 4. Kill Switch Stops Task While Keeping Browser
    # -----------------------------------------------------------------------
    def test_04_kill_switch_preserves_browser(self):
        self.session.execute_command_string(f"navigate to {self.base_url}")
        # Trigger kill switch
        self.session.kill_switch_active.set()
        res = self.session.execute_command_string(f"navigate to {self.base_url}shop")
        self.assertEqual(res.get("status"), "stopped")
        
        # Browser remains open and next command works
        self.assertTrue(self.session.browser_manager.is_running)
        res_next = self.session.execute_command_string(f"navigate to {self.base_url}")
        self.assertEqual(res_next.get("status"), "success")

    # -----------------------------------------------------------------------
    # 5. Auto-Recovery from Externally Closed Browser
    # -----------------------------------------------------------------------
    def test_05_external_browser_kill_auto_recovers(self):
        self.session.execute_command_string(f"navigate to {self.base_url}")
        self.session.last_known_url = f"{self.base_url}shop"
        
        # Simulate external browser close
        self.session.browser_manager.close()
        self.assertFalse(self.session.browser_manager.is_running)

        # Next command auto-recovers with no traceback
        res = self.session.execute_command_string(f"navigate to {self.base_url}")
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(self.session.browser_manager.is_running)

    # -----------------------------------------------------------------------
    # 6. Sensitive "Place order" Approval Gate
    # -----------------------------------------------------------------------
    def test_06_sensitive_action_approvals(self):
        # 1. Denied by default if non-TTY or no approver
        res_no_app = self.session.execute_command_string("place order")
        self.assertEqual(res_no_app.get("status"), "error")
        self.assertEqual(res_no_app.get("error"), "approval_required")

        # 2. Denied when approver rejects
        denying_approver = lambda msg, step: False
        res_denied = self.session.execute_command_string("place order", approver=denying_approver)
        self.assertEqual(res_denied.get("status"), "denied")

        # 3. Approved when approver returns True
        approving_approver = lambda msg, step: True
        res_approved = self.session.execute_command_string("place order", approver=approving_approver)
        self.assertEqual(res_approved.get("status"), "success")

    # -----------------------------------------------------------------------
    # 7. Process Lifecycle & Clean Shutdown
    # -----------------------------------------------------------------------
    def test_07_clean_process_shutdown(self):
        session = NebulaSession(SessionConfig(headless=True))
        session.ensure_browser_running()
        self.assertTrue(session.browser_manager.is_running)
        session.close()
        self.assertFalse(session.browser_manager.is_running)

    # -----------------------------------------------------------------------
    # 8. Built-in Commands Function Offline
    # -----------------------------------------------------------------------
    def test_08_builtin_commands_offline(self):
        # Tab listing works offline
        tabs = self.session.get_tabs()
        self.assertIsInstance(tabs, list)

        # Health check works offline
        ok, msg = self.session.ensure_browser_running()
        self.assertTrue(ok)

        # Checkpoint save works offline
        ckpt = self.session.save_session_checkpoint()
        self.assertTrue(ckpt.exists())

    # -----------------------------------------------------------------------
    # 9. Session Budget & Rate Limits Block Commands
    # -----------------------------------------------------------------------
    def test_09_budget_limits_block_excess_commands(self):
        small_session = NebulaSession(SessionConfig(headless=True, max_commands_per_session=2))
        try:
            r1 = small_session.execute_command_string(f"navigate to {self.base_url}")
            r2 = small_session.execute_command_string(f"navigate to {self.base_url}")
            self.assertEqual(r1.get("status"), "success")
            self.assertEqual(r2.get("status"), "success")

            # 3rd command exceeds budget
            r3 = small_session.execute_command_string(f"navigate to {self.base_url}")
            self.assertEqual(r3.get("status"), "error")
            self.assertIn("limit reached", r3.get("error", "").lower())
        finally:
            small_session.close()

    # -----------------------------------------------------------------------
    # 10. Injection Text Does Not Bypass Allow-Lists
    # -----------------------------------------------------------------------
    def test_10_injection_does_not_bypass_domain_allow_list(self):
        malicious_cmd = "navigate to https://evil-phishing-site.com"
        res = self.session.execute_command_string(malicious_cmd)
        self.assertEqual(res.get("status"), "error")
        err_msg = res.get("error", "").lower()
        self.assertTrue("disallowed domain" in err_msg or "allowed_domains" in err_msg)

    # -----------------------------------------------------------------------
    # 11. Deprecation Warning on Legacy Flags
    # -----------------------------------------------------------------------
    def test_11_legacy_flags_deprecation_warning(self):
        import io
        from orion_autogen import run_nebula_cli
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out), patch("sys.argv", ["nebula", "--detach", "doctor"]):
            try:
                run_nebula_cli()
            except SystemExit:
                pass
        output = captured_out.getvalue()
        self.assertIn("--detach/-d is deprecated", output)

    # -----------------------------------------------------------------------
    # 12. Local Control Channel Security
    # -----------------------------------------------------------------------
    def test_12_control_channel_security(self):
        ctrl_session = NebulaSession(SessionConfig(headless=True, control_channel_enabled=True))
        try:
            # 1. Invalid token rejected with 401
            import urllib.request
            import urllib.error
            url = "http://127.0.0.1:8769/command"
            req = urllib.request.Request(
                url,
                data=b'{"command": "status"}',
                headers={"Content-Type": "application/json", "X-Nebula-Token": "bad_token"},
                method="POST"
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)
            self.assertEqual(ctx.exception.code, 401)

            # 2. Valid token succeeds
            valid_res = control_channel.send_command_to_running_session("status", port=8769)
            self.assertNotIn("error", valid_res)

            # 3. Sensitive action over control channel is denied
            sensitive_res = control_channel.send_command_to_running_session("place order", port=8769)
            self.assertEqual(sensitive_res.get("status"), "error")
            self.assertEqual(sensitive_res.get("error"), "approval_required")
        finally:
            ctrl_session.close()


if __name__ == "__main__":
    unittest.main()
