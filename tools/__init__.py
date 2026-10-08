"""
tools/ package — Typed Async Tools, Agent Safeguards, and Multi-Agent Orchestration
====================================================================================
Phase 7: AutoGen Restructure
"""

from .typed_tools import (
    ToolRegistry,
    web_navigate,
    web_search,
    media_resolve_and_play,
    media_verify_playback,
    media_heal_playback,
    web_verify_page,
    web_screenshot,
    desktop_announce,
)
from .agent_society import (
    AgentRole,
    AgentSafeguards,
    SocietyCoordinator,
    UnauthorizedToolError,
    MaxTurnsExceededError,
    KillSwitchTriggeredError,
)

__all__ = [
    "ToolRegistry",
    "web_navigate",
    "web_search",
    "media_resolve_and_play",
    "media_verify_playback",
    "media_heal_playback",
    "web_verify_page",
    "web_screenshot",
    "desktop_announce",
    "AgentRole",
    "AgentSafeguards",
    "SocietyCoordinator",
    "UnauthorizedToolError",
    "MaxTurnsExceededError",
    "KillSwitchTriggeredError",
]
