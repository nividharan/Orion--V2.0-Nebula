"""
desktop/kill_switch.py — Global kill-switch hotkey and task-limits enforcement.

Global Rule 3: Every task has hard limits: max steps, wall-time cap, max LLM calls,
token budget, global kill-switch hotkey (Ctrl+Shift+K).

The KillSwitch registers a system-level hotkey. When pressed, it sets an event
that every executor loop checks. Any executor that respects the kill switch will
abort on the next loop iteration.

Usage (from executor)::

    ks = KillSwitch()
    ks.arm()           # starts listener thread
    ...
    if ks.is_killed():
        raise KillSwitchActivated("User pressed kill switch")
    ks.disarm()        # stops listener on clean exit

TaskLimits: data class enforced by run_plan().
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("orion.desktop.kill_switch")

# Default global kill-switch hotkey identifier (used for matching only)
KILL_HOTKEY = "ctrl+shift+k"


class KillSwitchActivated(RuntimeError):
    """Raised when the global kill-switch is triggered."""


class KillSwitch:
    """
    Thread-safe global kill-switch.

    Listens for the kill hotkey using keyboard module (if installed) or
    provides a manual software trigger (``trigger()``).
    """

    def __init__(self, hotkey: str = KILL_HOTKEY) -> None:
        self._hotkey = hotkey
        self._killed = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None
        self._armed = False

    # ------------------------------------------------------------------
    def arm(self) -> None:
        """Start the hotkey listener thread."""
        if self._armed:
            return
        self._armed = True
        self._killed.clear()

        try:
            import keyboard  # type: ignore[import]
            keyboard.add_hotkey(self._hotkey, self.trigger, suppress=True)
            logger.info(f"Kill-switch armed on hotkey: {self._hotkey}")
        except Exception as exc:
            # keyboard library may not be installed or may require admin rights
            logger.warning(
                f"Could not register kill-switch hotkey ({exc}). "
                "Use KillSwitch.trigger() to manually activate."
            )

    def disarm(self) -> None:
        """Stop the hotkey listener."""
        if not self._armed:
            return
        self._armed = False
        try:
            import keyboard  # type: ignore[import]
            keyboard.remove_hotkey(self._hotkey)
        except Exception:
            pass
        logger.info("Kill-switch disarmed.")

    def trigger(self) -> None:
        """Programmatically trigger the kill switch (also called by hotkey)."""
        self._killed.set()
        logger.warning("KILL SWITCH ACTIVATED — aborting current task.")

    def is_killed(self) -> bool:
        """Returns True if the kill switch has been activated."""
        return self._killed.is_set()

    def reset(self) -> None:
        """Reset after being triggered (use with care)."""
        self._killed.clear()

    def check(self) -> None:
        """Raise KillSwitchActivated if triggered."""
        if self.is_killed():
            raise KillSwitchActivated("Global kill-switch was activated.")


@dataclass
class TaskLimits:
    """
    Hard limits for a single task execution (Phase 5 / Global Rule 3).

    Attributes:
        max_steps:         Maximum number of executor steps allowed.
        wall_time_seconds: Maximum wall-clock seconds for the whole task.
        max_llm_calls:     Maximum calls to any LLM during this task.
        token_budget:      Maximum total LLM tokens (input + output) consumed.
    """

    max_steps: int = 30
    wall_time_seconds: float = 300.0    # 5 minutes default
    max_llm_calls: int = 10
    token_budget: int = 50_000

    # Runtime counters — reset at task start
    _steps_done: int = field(default=0, init=False, repr=False)
    _llm_calls: int = field(default=0, init=False, repr=False)
    _tokens_used: int = field(default=0, init=False, repr=False)
    _start_time: float = field(default_factory=time.time, init=False, repr=False)

    def reset_counters(self) -> None:
        """Reset all runtime counters (call at task start)."""
        self._steps_done = 0
        self._llm_calls = 0
        self._tokens_used = 0
        self._start_time = time.time()

    # ------------------------------------------------------------------
    def increment_step(self) -> None:
        self._steps_done += 1

    def increment_llm(self, tokens: int = 0) -> None:
        self._llm_calls += 1
        self._tokens_used += tokens

    # ------------------------------------------------------------------
    def check_step_limit(self) -> None:
        if self._steps_done >= self.max_steps:
            raise RuntimeError(
                f"Step limit reached ({self._steps_done}/{self.max_steps}). Task aborted."
            )

    def check_wall_time(self) -> None:
        elapsed = time.time() - self._start_time
        if elapsed > self.wall_time_seconds:
            raise RuntimeError(
                f"Wall-time limit exceeded ({elapsed:.1f}s > {self.wall_time_seconds}s). Task aborted."
            )

    def check_llm_limit(self) -> None:
        if self._llm_calls >= self.max_llm_calls:
            raise RuntimeError(
                f"LLM call limit reached ({self._llm_calls}/{self.max_llm_calls}). Task aborted."
            )

    def check_token_budget(self) -> None:
        if self._tokens_used >= self.token_budget:
            raise RuntimeError(
                f"Token budget exhausted ({self._tokens_used}/{self.token_budget}). Task aborted."
            )

    def check_all(self, kill_switch: Optional[KillSwitch] = None) -> None:
        """Check all limits plus kill switch. Raises RuntimeError on violation."""
        if kill_switch:
            kill_switch.check()
        self.check_step_limit()
        self.check_wall_time()

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def steps_done(self) -> int:
        return self._steps_done
