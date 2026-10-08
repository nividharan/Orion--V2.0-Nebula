"""
tools/agent_society.py — Phase 7: Multi-Agent Society & Safeguards
==================================================================
Principle:
  - Role Specialization:
      Commander: Plans once via NebulaBrain (or local parser).
      Executor: Runs tools directly without LLM tool-reflection loops (reflect_on_tool_use=False).
      Verifier: Performs closed-loop verification and self-healing.
  - Safeguards:
      Per-agent tool allow-lists (prevents unauthorized execution).
      Max-turn limit (guards against infinite recursion).
      Kill switch (instant synchronous abort).
  - Exit Criteria: 5-step task completes in 1–2 LLM calls.
"""

from __future__ import annotations

import time
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field

from schemas import Plan, Step, ActionType, IntentType
from nebula_brain import NebulaBrain
from .typed_tools import ToolRegistry

logger = logging.getLogger("Orion.AgentSociety")


class AgentRole(str, Enum):
    COMMANDER = "COMMANDER"
    EXECUTOR = "EXECUTOR"
    VERIFIER = "VERIFIER"


# Strict per-agent tool allow-lists
ROLE_TOOL_ALLOW_LIST: Dict[AgentRole, Set[str]] = {
    AgentRole.COMMANDER: set(),  # Commander only outputs plans, executes zero tools
    AgentRole.EXECUTOR: {
        "web_navigate",
        "web_search",
        "media_resolve_and_play",
        "desktop_announce",
    },
    AgentRole.VERIFIER: {
        "media_verify_playback",
        "media_heal_playback",
        "web_verify_page",
        "web_screenshot",
    },
}


class UnauthorizedToolError(PermissionError):
    """Raised when an agent role attempts to call a tool outside its allowed list."""
    pass


class MaxTurnsExceededError(RuntimeError):
    """Raised when task coordination exceeds max turn safety limit."""
    pass


class KillSwitchTriggeredError(RuntimeError):
    """Raised when execution is aborted via emergency kill switch."""
    pass


@dataclass
class AgentSafeguards:
    max_turns: int = 5
    kill_switch_active: bool = False
    enforce_allow_lists: bool = True

    def check_kill_switch(self) -> None:
        if self.kill_switch_active:
            raise KillSwitchTriggeredError("Emergency kill switch active. Aborting task immediately.")

    def authorize_tool(self, role: AgentRole, tool_name: str) -> None:
        self.check_kill_switch()
        if not self.enforce_allow_lists:
            return

        allowed = ROLE_TOOL_ALLOW_LIST.get(role, set())
        if tool_name not in allowed:
            raise UnauthorizedToolError(
                f"Role '{role.value}' is unauthorized to invoke tool '{tool_name}'. Allowed: {sorted(allowed)}"
            )


@dataclass
class SocietyResult:
    goal: str
    success: bool
    plan: Optional[Plan] = None
    steps_executed: int = 0
    llm_calls: int = 0
    total_elapsed_ms: float = 0.0
    error: Optional[str] = None
    verification_state: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "llm_calls": self.llm_calls,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "error": self.error,
            "verification_state": self.verification_state,
        }


class SocietyCoordinator:
    """
    Coordinates Commander, Executor, and Verifier agents under strict safeguards.
    Guarantees deterministic execution where 5-step tasks finish in 1-2 LLM calls.
    """

    def __init__(
        self,
        brain: Optional[NebulaBrain] = None,
        safeguards: Optional[AgentSafeguards] = None,
        fixture_path: Optional[str] = None,
    ):
        self.brain = brain or NebulaBrain()
        self.safeguards = safeguards or AgentSafeguards()
        self.fixture_path = fixture_path
        self._llm_call_count = 0

    def trigger_kill_switch(self) -> None:
        self.safeguards.kill_switch_active = True

    async def execute_task(
        self,
        goal: str,
        page=None,
    ) -> SocietyResult:
        start = time.perf_counter()
        self.safeguards.check_kill_switch()

        # Step 1: Commander plans ONCE
        plan_start_calls = self.brain.stats["api_calls"]
        plan: Plan = self.brain.plan(goal)
        llm_calls = self.brain.stats["api_calls"] - plan_start_calls
        self._llm_call_count += llm_calls

        turn_count = 1
        steps_executed = 0

        # Step 2: Executor runs steps with NO tool-reflection loops
        for step in plan.steps:
            if turn_count > self.safeguards.max_turns:
                raise MaxTurnsExceededError(
                    f"Max turn limit ({self.safeguards.max_turns}) exceeded during step execution"
                )

            self.safeguards.check_kill_switch()

            # Map step action to typed tool
            tool_name = self._map_action_to_tool(step.action)
            self.safeguards.authorize_tool(AgentRole.EXECUTOR, tool_name)

            tool_fn = ToolRegistry.get(tool_name)
            if not tool_fn:
                raise RuntimeError(f"Tool implementation for '{tool_name}' not found in registry")

            # Execute tool directly (reflect_on_tool_use = False)
            kwargs = self._build_tool_args(step, page)
            res = await tool_fn(**kwargs)
            if not res.get("success", False):
                elapsed = (time.perf_counter() - start) * 1000
                return SocietyResult(
                    goal=goal,
                    success=False,
                    plan=plan,
                    steps_executed=steps_executed,
                    llm_calls=self._llm_call_count,
                    total_elapsed_ms=elapsed,
                    error=res.get("error", "Tool execution failed"),
                )

            steps_executed += 1
            turn_count += 1

        # Step 3: Verifier evaluates completion and heals if needed
        self.safeguards.check_kill_switch()
        if plan.intent in (IntentType.MEDIA_PLAY, IntentType.MEDIA_PLAYBACK):
            verifier_tool = "media_verify_playback"
            self.safeguards.authorize_tool(AgentRole.VERIFIER, verifier_tool)

            verify_fn = ToolRegistry.get(verifier_tool)
            verify_res = await verify_fn(page=page)
            v_state = verify_res.get("state", {})

            # Self-healing if needed
            if not v_state.get("is_playing", True):
                heal_tool = "media_heal_playback"
                self.safeguards.authorize_tool(AgentRole.VERIFIER, heal_tool)
                heal_fn = ToolRegistry.get(heal_tool)
                heal_res = await heal_fn(page=page)
                v_state = heal_res.get("state", v_state)
        else:
            verifier_tool = "web_verify_page"
            self.safeguards.authorize_tool(AgentRole.VERIFIER, verifier_tool)
            verify_fn = ToolRegistry.get(verifier_tool)
            verify_res = await verify_fn(page=page)
            v_state = verify_res

        elapsed = (time.perf_counter() - start) * 1000
        return SocietyResult(
            goal=goal,
            success=True,
            plan=plan,
            steps_executed=steps_executed,
            llm_calls=self._llm_call_count,
            total_elapsed_ms=elapsed,
            verification_state=v_state,
        )

    def _map_action_to_tool(self, action: ActionType) -> str:
        if action == ActionType.PLAY:
            return "media_resolve_and_play"
        elif action in (ActionType.BROWSE, ActionType.OPEN_APP):
            return "web_navigate"
        elif action == ActionType.SEARCH:
            return "web_search"
        elif action == ActionType.SPEAK:
            return "desktop_announce"
        elif action == ActionType.SCREENSHOT:
            return "web_screenshot"
        return "desktop_announce"

    def _build_tool_args(self, step: Step, page) -> Dict[str, Any]:
        action = step.action
        if action == ActionType.PLAY:
            return {
                "query": step.play or step.query or step.target or "music",
                "page": page,
                "fixture_path": self.fixture_path,
            }
        elif action in (ActionType.BROWSE, ActionType.OPEN_APP):
            target = step.target or "https://www.google.com"
            if not target.startswith("http"):
                target = f"https://www.{target}.com"
            return {"url": target, "page": page}
        elif action == ActionType.SEARCH:
            return {"portal": step.target or "google", "query": step.query or "", "page": page}
        elif action == ActionType.SPEAK:
            return {"message": step.target or "Notification"}
        elif action == ActionType.SCREENSHOT:
            return {"page": page}
        return {"message": step.target or ""}
