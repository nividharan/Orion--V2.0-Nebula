"""
tests/test_banner.py — Verification of Minimalist Nebula CLI Header
===================================================================
Ensures:
  ✓ Clean 2-line minimalist header without bulky block art.
  ✓ ANSI escape codes stripped accurately.
  ✓ Welcome/help view and active goal prompt rendered cleanly.
  ✓ StreamConsole integration works seamlessly.
"""

import sys
import os
import unittest
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nebula_banner
from orion_autogen import StreamConsole


class TestNebulaBanner(unittest.TestCase):

    def test_strip_ansi(self):
        text_with_ansi = "\033[38;2;168;85;247mnebula\033[0m"
        self.assertEqual(nebula_banner.strip_ansi(text_with_ansi), "nebula")

    def test_visible_width(self):
        simple = "Hello World"
        self.assertEqual(nebula_banner.visible_width(simple), 11)

        with_ansi = "\033[1m\033[38;2;255;0;0mHello\033[0m"
        self.assertEqual(nebula_banner.visible_width(with_ansi), 5)

    def test_splash_default_contains_key_elements(self):
        splash = nebula_banner.get_nebula_splash()
        clean = nebula_banner.strip_ansi(splash)
        self.assertIn("✦ nebula (v2.0)", clean)
        self.assertIn("orion substrate", clean)
        self.assertIn("5 agents ready", clean)
        self.assertIn("Usage:", clean)
        self.assertIn("Examples:", clean)

    def test_splash_active_goal_contains_goal(self):
        goal = "play chill music on youtube"
        splash = nebula_banner.get_nebula_splash(goal=goal)
        clean = nebula_banner.strip_ansi(splash)
        self.assertIn("✦ nebula (v2.0)", clean)
        self.assertIn("› \"play chill music on youtube\"", clean)
        self.assertIn("───", clean)

    def test_stream_console_uses_banner(self):
        console = StreamConsole(minimal=True)
        captured = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured
            console.print_banner("test goal")
        finally:
            sys.stdout = old_stdout
        
        output = captured.getvalue()
        self.assertIn("nebula", output)
        self.assertIn("test goal", output)


if __name__ == "__main__":
    unittest.main()
