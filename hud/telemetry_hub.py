"""
Central Telemetry Hub for Orion & Nebula.
Event bus broadcasting state updates to Desktop HUD, Terminal ANSI bar, and WebSocket streams.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nebula.telemetry_hub")


@dataclass
class TelemetryState:
    """Current snapshot of system execution state."""
    agent_name: str = "Nebula"
    status: str = "IDLE"  # IDLE, RUNNING, PAUSED, 2FA_WAIT, ERROR, SUCCESS
    status_emoji: str = "⚪"  # 🟢, 🟡, 🔴, ⚪, 🔒
    current_step: str = "Awaiting instructions"
    reasoning: str = ""
    visual_delta_pct: float = 0.0
    elapsed_sec: float = 0.0
    timestamp: float = 0.0


class TelemetryHub:
    """Thread-safe and async-compatible event publisher for HUD channels."""

    _instance: Optional["TelemetryHub"] = None

    def __init__(self):
        self.state = TelemetryState()
        self._subscribers: List[Callable[[TelemetryState], Any]] = []
        self._start_time = time.perf_counter()

    @classmethod
    def get_instance(cls) -> "TelemetryHub":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, callback: Callable[[TelemetryState], Any]) -> None:
        """Registers a callback subscriber to receive telemetry broadcasts."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[TelemetryState], Any]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def update(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        current_step: Optional[str] = None,
        reasoning: Optional[str] = None,
        visual_delta_pct: Optional[float] = None
    ) -> TelemetryState:
        """Updates current telemetry state and broadcasts to all subscribers."""
        if agent_name is not None:
            self.state.agent_name = agent_name
        if status is not None:
            self.state.status = status
            if status == "RUNNING":
                self.state.status_emoji = "🟢"
            elif status in ("PAUSED", "2FA_WAIT"):
                self.state.status_emoji = "🟡"
            elif status == "ERROR":
                self.state.status_emoji = "🔴"
            elif status == "SUCCESS":
                self.state.status_emoji = "✅"
            else:
                self.state.status_emoji = "⚪"

        if current_step is not None:
            self.state.current_step = current_step
        if reasoning is not None:
            self.state.reasoning = reasoning
        if visual_delta_pct is not None:
            self.state.visual_delta_pct = visual_delta_pct

        self.state.elapsed_sec = time.perf_counter() - self._start_time
        self.state.timestamp = time.time()

        # Notify subscribers
        for sub in list(self._subscribers):
            try:
                sub(self.state)
            except Exception as e:
                logger.debug("Telemetry subscriber error: %s", e)

        return self.state

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.state)
