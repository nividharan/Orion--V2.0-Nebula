"""
tests/test_society.py — Phase 7 exit criteria
==============================================
Deterministic test suite for tools/ package and agent society coordination.
No live external network, no live LLM API keys required.

Exit criteria (from plan):
  ✓ Typed Async Tools wrapped with docstrings and domain security.
  ✓ Role Specialization: Commander plans once, Executor runs tools, Verifier evaluates.
  ✓ Safeguards: Per-agent tool allow-lists, max-turn limit, kill switch.
  ✓ 5-step task finishes in 1–2 LLM calls (reflect_on_tool_use=False).
"""

import os
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas import Plan, Step, ActionType, IntentType
from nebula_brain import NebulaBrain
from tools import (
    ToolRegistry,
    web_navigate,
    web_search,
    media_resolve_and_play,
    media_verify_playback,
    media_heal_playback,
    web_verify_page,
    web_screenshot,
    desktop_announce,
    AgentRole,
    AgentSafeguards,
    SocietyCoordinator,
    UnauthorizedToolError,
    MaxTurnsExceededError,
    KillSwitchTriggeredError,
)
from tools.typed_tools import ToolSecurityError


class TestTypedTools(unittest.IsolatedAsyncioTestCase):
    async def test_web_navigate_allowed_domain(self):
        res = await web_navigate("https://www.youtube.com/watch?v=123")
        self.assertTrue(res["success"])
        self.assertEqual(res["url"], "https://www.youtube.com/watch?v=123")

    async def test_web_navigate_disallowed_domain_raises(self):
        with self.assertRaises(ToolSecurityError):
            await web_navigate("https://malicious-site.com/exploit")

    async def test_web_search_portal_url(self):
        res = await web_search("youtube", "tamil songs")
        self.assertTrue(res["success"])
        self.assertIn("youtube.com/results?search_query=", res["url"])

    async def test_media_resolve_and_play_with_fixture(self):
        fixture_file = str(
            PROJECT_ROOT / "tests" / "fixtures" / "youtube_search_kangal_neeye.json"
        )
        res = await media_resolve_and_play("kangal neeye tamil song", fixture_path=fixture_file)
        self.assertTrue(res["success"])
        self.assertIn("watch?v=", res["watch_url"])
        self.assertIn("candidate", res)

    async def test_media_verify_and_heal_simulation(self):
        v_res = await media_verify_playback()
        self.assertTrue(v_res["success"])
        self.assertTrue(v_res["state"]["is_playing"])

        h_res = await media_heal_playback()
        self.assertTrue(h_res["success"])

    async def test_web_verify_page_simulation(self):
        res = await web_verify_page()
        self.assertTrue(res["success"])
        self.assertEqual(res["verdict"], "ok")

    async def test_desktop_announce(self):
        res = await desktop_announce("Task complete")
        self.assertTrue(res["success"])
        self.assertEqual(res["message"], "Task complete")

    def test_registry_contains_all_tools(self):
        tools = ToolRegistry.list_tools()
        expected = [
            "desktop_announce",
            "media_heal_playback",
            "media_resolve_and_play",
            "media_verify_playback",
            "web_navigate",
            "web_screenshot",
            "web_search",
            "web_verify_page",
        ]
        self.assertEqual(tools, expected)


class TestAgentSafeguards(unittest.TestCase):
    def setUp(self):
        self.safeguards = AgentSafeguards(max_turns=5, enforce_allow_lists=True)

    def test_commander_cannot_execute_tools(self):
        with self.assertRaises(UnauthorizedToolError):
            self.safeguards.authorize_tool(AgentRole.COMMANDER, "web_navigate")

    def test_executor_cannot_execute_verifier_tools(self):
        with self.assertRaises(UnauthorizedToolError):
            self.safeguards.authorize_tool(AgentRole.EXECUTOR, "media_verify_playback")

    def test_executor_can_execute_allowed_tools(self):
        # Should not raise
        self.safeguards.authorize_tool(AgentRole.EXECUTOR, "web_navigate")
        self.safeguards.authorize_tool(AgentRole.EXECUTOR, "media_resolve_and_play")

    def test_verifier_can_execute_allowed_tools(self):
        # Should not raise
        self.safeguards.authorize_tool(AgentRole.VERIFIER, "media_verify_playback")
        self.safeguards.authorize_tool(AgentRole.VERIFIER, "media_heal_playback")
        self.safeguards.authorize_tool(AgentRole.VERIFIER, "web_verify_page")

    def test_kill_switch_blocks_execution(self):
        self.safeguards.kill_switch_active = True
        with self.assertRaises(KillSwitchTriggeredError):
            self.safeguards.authorize_tool(AgentRole.EXECUTOR, "web_navigate")


class TestSocietyCoordinator(unittest.IsolatedAsyncioTestCase):
    async def test_five_step_task_finishes_in_at_most_two_llm_calls(self):
        """
        Exit criteria test: A 5-step task executes completely in 1-2 LLM calls.
        """
        # Create a mock brain that produces a 5-step plan with 1 LLM call
        mock_plan = Plan(
            intent=IntentType.MEDIA_PLAY,
            confidence=1.0,
            target_app="chrome",
            steps=[
                Step(action=ActionType.SPEAK, target="Starting media session"),
                Step(action=ActionType.BROWSE, target="https://www.youtube.com"),
                Step(action=ActionType.SEARCH, target="youtube", query="kangal neeye"),
                Step(action=ActionType.PLAY, target="kangal neeye"),
                Step(action=ActionType.SPEAK, target="Track is playing"),
            ]
        )

        brain = MagicMock()
        brain.stats = {"api_calls": 0}
        def mock_plan_fn(goal):
            brain.stats["api_calls"] += 1
            return mock_plan
        brain.plan.side_effect = mock_plan_fn

        fixture_file = str(
            PROJECT_ROOT / "tests" / "fixtures" / "youtube_search_kangal_neeye.json"
        )
        safeguards = AgentSafeguards(max_turns=10)
        coordinator = SocietyCoordinator(
            brain=brain,
            safeguards=safeguards,
            fixture_path=fixture_file,
        )

        result = await coordinator.execute_task("play kangal neeye on youtube")

        self.assertTrue(result.success)
        self.assertEqual(result.steps_executed, 5)
        # CRITICAL EXIT CRITERIA: Finished in 1 LLM call (<= 2)
        self.assertLessEqual(result.llm_calls, 2)
        self.assertEqual(result.llm_calls, 1)

    async def test_max_turns_exceeded_triggers_error(self):
        mock_plan = Plan(
            intent=IntentType.MEDIA_PLAY,
            confidence=1.0,
            target_app="chrome",
            steps=[
                Step(action=ActionType.SPEAK, target="Step 1"),
                Step(action=ActionType.SPEAK, target="Step 2"),
                Step(action=ActionType.SPEAK, target="Step 3"),
            ]
        )
        brain = MagicMock()
        brain.stats = {"api_calls": 1}
        brain.plan.return_value = mock_plan

        # Limit max turns to 2
        safeguards = AgentSafeguards(max_turns=2)
        coordinator = SocietyCoordinator(brain=brain, safeguards=safeguards)

        with self.assertRaises(MaxTurnsExceededError):
            await coordinator.execute_task("test goal")

    async def test_kill_switch_aborts_coordination(self):
        coordinator = SocietyCoordinator()
        coordinator.trigger_kill_switch()
        with self.assertRaises(KillSwitchTriggeredError):
            await coordinator.execute_task("test goal")

    async def test_web_navigation_task_routes_to_web_verify_page(self):
        mock_plan = Plan(
            intent=IntentType.WEB_TASK,
            confidence=1.0,
            target_app="chrome",
            steps=[
                Step(action=ActionType.BROWSE, target="https://www.google.com"),
                Step(action=ActionType.SPEAK, target="Navigation complete"),
            ]
        )
        brain = MagicMock()
        brain.stats = {"api_calls": 1}
        brain.plan.return_value = mock_plan

        coordinator = SocietyCoordinator(brain=brain)
        res = await coordinator.execute_task("open google")
        self.assertTrue(res.success)
        self.assertEqual(res.steps_executed, 2)
        self.assertIn("verdict", res.verification_state)
        self.assertEqual(res.verification_state["verdict"], "ok")


if __name__ == "__main__":
    unittest.main()
