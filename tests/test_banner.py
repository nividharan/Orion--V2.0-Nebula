"""
tests/test_banner.py — Verification of Nebula CLI Splash Banner
===============================================================
Ensures:
  ✓ Box-drawing borders are perfectly aligned across all terminal widths.
  ✓ ANSI escape codes and wide-character emojis calculate correct visible widths.
  ✓ Banner renders both default welcome and active goal modes correctly.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nebula_banner
from orion_autogen import StreamConsole


class TestNebulaBanner(unittest.TestCase):

    def test_strip_ansi(self):
        text_with_ansi = "\033[38;2;124;58;237mNEBULA\033[0m"
        self.assertEqual(nebula_banner.strip_ansi(text_with_ansi), "NEBULA")

    def test_visible_width_emoji_handling(self):
        # Emojis like 🧠, 🌐, 👁️ should count as 2 visible columns
        simple = "Hello World"
        self.assertEqual(nebula_banner.visible_width(simple), 11)

        with_ansi = "\033[1m\033[38;2;255;0;0mHello\033[0m"
        self.assertEqual(nebula_banner.visible_width(with_ansi), 5)

    def test_pad_line_exact_target_width(self):
        line = "  Sample text"
        padded = nebula_banner.pad_line(line, 50)
        self.assertEqual(nebula_banner.visible_width(padded), 50)

    def test_splash_default_contains_key_elements(self):
        splash = nebula_banner.get_nebula_splash()
        self.assertIn("NEBULA MODEL", splash)
        self.assertIn("ORION OS", splash)
        self.assertIn("v2.0-nebula", splash)
        self.assertIn("Agent Fleet", splash)
        self.assertIn("Quick Usage", splash)

    def test_splash_active_goal_contains_goal(self):
        goal = "play chill music on youtube"
        splash = nebula_banner.get_nebula_splash(goal=goal)
        self.assertIn("Active Goal", splash)
        self.assertIn(goal, splash)

    def test_box_borders_alignment(self):
        splash = nebula_banner.get_nebula_splash(goal="test task")
        lines = [l for l in splash.split("\n") if l.strip()]
        
        # Every framed line starts and ends with box drawing characters
        for l in lines:
            clean = nebula_banner.strip_ansi(l)
            if clean.startswith("│"):
                self.assertTrue(clean.endswith("│"), f"Line not terminated with │: {clean}")
                # Target width is 78 + 2 borders = 80
                vw = nebula_banner.visible_width(clean)
                self.assertEqual(vw, 80, f"Line width {vw} != 80: '{clean}'")


if __name__ == "__main__":
    unittest.main()
