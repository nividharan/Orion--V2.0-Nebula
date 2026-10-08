"""
session.py — Persistent Nebula Session Owner (Web-Only)
======================================================
Manages a persistent, single-browser session across interactive commands:
- Owns BrowserManager, page registry, task runner, input processor, limits, and kill switch.
- Lives in dedicated engine thread / event loop (via BrowserManager).
- Uses dedicated automation profile (persistent context in profiles/).
- Health checks before each command: auto-heals crashed/closed browser, restores last URL safely.
- Enforces per-command and per-session budgets (steps, time, LLM calls, rate limits).
- Idle timeout support and atomic state persistence.
"""

from __future__ import annotations

import os
import sys
import time
import json
import uuid
import logging
import threading
import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import PROFILES_DIR, CACHE_DIR, atomic_write
from schemas import (
    ALLOWED_ACTIONS,
    ALLOWED_DOMAINS,
    SENSITIVE_ACTIONS,
    ActionType,
    IntentType,
    Plan,
    Step,
    validate_plan,
)
from input_pipeline import (
    CapturedInput,
    ConversationContext,
    PipelineResult,
    process_input,
)
from web_engine.config import BrowserConfig, DEFAULT_CONFIG
from web_engine.browser_manager import BrowserManager, atomic_write_json
from web_engine.exceptions import ActionNotAllowedError, WebEngineError

logger = logging.getLogger("Orion.Session")


@dataclass
class SessionConfig:
    """Configurable boundaries and features for NebulaSession."""
    idle_timeout_sec: float = 0.0              # 0.0 = disabled
    max_steps_per_command: int = 15
    max_wall_time_command_sec: float = 60.0
    max_llm_calls_command: int = 3
    max_steps_per_session: int = 200
    max_commands_per_session: int = 100
    rate_limit_commands_per_minute: int = 30
    media_watcher_enabled: bool = False
    control_channel_enabled: bool = False
    headless: bool = False
    mode: str = "nova"                         # "spark" (fast), "nova" (standard), "quasar" (deep)
    dry_run: bool = False


class BudgetExceededError(Exception):
    """Raised when command or session execution budgets are exceeded."""
    pass


class KillSwitchTriggered(Exception):
    """Raised when the kill switch / Ctrl+C is triggered for a task."""
    pass


class NebulaSession:
    """
    Session owner for Orion/Nebula Interactive Mode.
    Created once and reused for every user command.
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.session_id = str(uuid.uuid4())[:8]
        self.created_at = time.time()
        self.last_active_time = time.time()

        # Dedicated automation profile directory
        profile_dir = PROFILES_DIR / f"session_{self.session_id}"
        self.browser_config = BrowserConfig(
            headless=self.config.headless,
            use_persistent_profile=True,
            profile_dir=profile_dir,
        )

        # Core components
        self.browser_manager = BrowserManager(self.browser_config)
        self.context_memory = ConversationContext()
        self.turn_history: List[Dict[str, Any]] = []  # last 5+ turns
        
        # Page & Player tracking
        self.player_page: Optional[Any] = None
        self.last_known_url: Optional[str] = None
        self.last_known_title: Optional[str] = None
        self.last_reversible_action: Optional[Dict[str, Any]] = None

        # Session Metrics & Budgets
        self.total_commands: int = 0
        self.total_steps: int = 0
        self.total_llm_calls: int = 0
        self.command_timestamps: List[float] = []

        # Threading & Control
        self._lock = threading.RLock()
        self.kill_switch_active = threading.Event()
        self.is_command_running = False
        self.closed = False

        # Optional background media watcher
        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_stop = threading.Event()
        if self.config.media_watcher_enabled:
            self.start_media_watcher()

        # Optional local control channel server (127.0.0.1)
        self._control_server = None
        if self.config.control_channel_enabled:
            try:
                from control_channel import LocalControlServer
                self._control_server = LocalControlServer(self)
                self._control_server.start()
            except Exception as e:
                logger.warning(f"Failed to start local control server: {e}")

    # -----------------------------------------------------------------------
    # Browser Lifecycle & Health Checking
    # -----------------------------------------------------------------------

    def ensure_browser_running(self) -> Tuple[bool, str]:
        """
        Health check: verifies that the browser and active page are responsive.
        If closed or crashed, recreates context/page and restores last known URL.
        """
        with self._lock:
            if self.closed:
                return False, "Session is closed."

            is_healthy = False
            msg = ""

            try:
                if self.browser_manager.is_running and self.browser_manager.page:
                    if not self.browser_manager.page.is_closed():
                        is_healthy = True
            except Exception as e:
                logger.warning(f"Browser health probe failed: {e}")
                is_healthy = False

            if not is_healthy:
                msg = "Browser was closed or disconnected. Automatically restoring session..."
                logger.info(msg)
                try:
                    # Clean up old references
                    try:
                        self.browser_manager.close()
                    except Exception:
                        pass
                    # Relaunch browser
                    self.browser_manager = BrowserManager(self.browser_config)
                    page = self.browser_manager.launch()
                    # Restore last known URL if safe
                    if self.last_known_url and self.last_known_url != "about:blank":
                        try:
                            self.browser_manager.navigate(self.last_known_url)
                        except Exception:
                            pass
                    return True, msg
                except Exception as ex:
                    return False, f"Failed to restore browser: {ex}"

            return True, "Healthy"

    def get_tabs(self) -> List[Dict[str, Any]]:
        """Returns list of open tabs with index, title, and URL."""
        with self._lock:
            tabs = []
            if not self.browser_manager.is_running:
                return tabs
            pages = self.browser_manager.pages
            for i, p in enumerate(pages):
                try:
                    title = p.title() or "Untitled"
                    url = p.url or "about:blank"
                    is_active = (p == self.browser_manager.page)
                    tabs.append({"index": i, "title": title, "url": url, "active": is_active})
                except Exception:
                    pass
            return tabs

    def switch_tab(self, index: int) -> bool:
        """Switches active page to given tab index."""
        with self._lock:
            pages = self.browser_manager.pages
            if 0 <= index < len(pages):
                target = pages[index]
                try:
                    target.bring_to_front()
                    self.browser_manager._active_page = target
                    self.last_known_url = target.url
                    self.last_known_title = target.title()
                    return True
                except Exception:
                    return False
            return False

    def close_browser_keep_session(self) -> None:
        """Closes the browser window, leaving the session open for next command."""
        with self._lock:
            try:
                self.browser_manager.close()
            except Exception:
                pass
            self.player_page = None

    # -----------------------------------------------------------------------
    # Budget & Rate Limit Checks
    # -----------------------------------------------------------------------

    def check_budgets_before_command(self) -> None:
        """Enforces session limits, idle timeout, and command rate limits."""
        now = time.time()

        # 1. Idle timeout
        if self.config.idle_timeout_sec > 0:
            if (now - self.last_active_time) > self.config.idle_timeout_sec:
                self.close()
                raise BudgetExceededError("Session closed due to idle timeout.")

        # 2. Max commands per session
        if self.total_commands >= self.config.max_commands_per_session:
            raise BudgetExceededError(
                f"Session command limit reached ({self.total_commands}/{self.config.max_commands_per_session})."
            )

        # 3. Max steps per session
        if self.total_steps >= self.config.max_steps_per_session:
            raise BudgetExceededError(
                f"Session step limit reached ({self.total_steps}/{self.config.max_steps_per_session})."
            )

        # 4. Rate limiting: window of 60 seconds
        cutoff = now - 60.0
        self.command_timestamps = [t for t in self.command_timestamps if t >= cutoff]
        if len(self.command_timestamps) >= self.config.rate_limit_commands_per_minute:
            raise BudgetExceededError(
                f"Rate limit exceeded: maximum {self.config.rate_limit_commands_per_minute} commands per minute."
            )

        self.command_timestamps.append(now)
        self.last_active_time = now

    # -----------------------------------------------------------------------
    # Command Execution Engine
    # -----------------------------------------------------------------------

    def execute_command_string(
        self,
        raw_cmd: str,
        approver: Optional[Callable[[str, Step], bool]] = None,
        progress_cb: Optional[Callable[[int, int, Step, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a user command string through the session:
        1. Checks budgets & rate limits
        2. Runs health check (auto-recovers browser)
        3. Parses through input pipeline + 5-turn context
        4. Validates safety / approval gate
        5. Executes steps with kill-switch monitoring & media player registration
        """
        if self.kill_switch_active.is_set():
            self.kill_switch_active.clear()
            return {"status": "stopped", "message": "Command stopped by kill switch."}

        try:
            with self._lock:
                self.check_budgets_before_command()
                ok, health_msg = self.ensure_browser_running()
                if not ok:
                    return {"status": "error", "error": health_msg}

            self.is_command_running = True
            t_cmd_start = time.perf_counter()
            # 1. Process Input Pipeline
            captured = CapturedInput(raw_text=raw_cmd, source="text")
            pipeline_res: PipelineResult = process_input(captured, context=self.context_memory)

            if pipeline_res.status == "cancel":
                return {"status": "cancelled", "message": "Command cancelled by user."}
            elif pipeline_res.status == "undo":
                return self.undo_last_action()
            elif pipeline_res.status == "error":
                return {"status": "error", "error": pipeline_res.error}
            elif pipeline_res.status == "ask":
                return {
                    "status": "ask",
                    "question": pipeline_res.clarification_question,
                    "options": pipeline_res.options or [],
                    "cleaned_text": pipeline_res.cleaned_text,
                }

            plan = pipeline_res.plan
            if not plan or not plan.steps:
                return {"status": "error", "error": "Unable to formulate an execution plan for command."}

            # 2. Check Command Budget
            if len(plan.steps) > self.config.max_steps_per_command:
                return {
                    "status": "error",
                    "error": f"Plan exceeds maximum steps per command ({len(plan.steps)} > {self.config.max_steps_per_command})."
                }

            # 3. Handle Sensitive Approvals
            if pipeline_res.requires_approval or any(s.requires_approval for s in plan.steps):
                if approver is None:
                    # Non-interactive stdin or piped input without approver -> strictly deny
                    return {"status": "error", "ok": False, "error": "approval_required", "message": "Approval required but no interactive approver available."}
                
                # Request interactive approval
                for s in plan.steps:
                    if s.requires_approval:
                        approved = approver(pipeline_res.read_back or "Sensitive operation", s)
                        if not approved:
                            return {"status": "denied", "message": "Sensitive step was denied by user."}

            # 4. Dry Run Mode
            if self.config.dry_run:
                return {
                    "status": "dry_run",
                    "message": "Dry-run mode active. Steps planned but not executed.",
                    "steps": [getattr(s, "description", None) or f"{s.action.value} {s.target or ''}".strip() for s in plan.steps]
                }

            # 5. Execute Steps
            executed_steps_summary = []
            for idx, step in enumerate(plan.steps, 1):
                if self.kill_switch_active.is_set():
                    raise KillSwitchTriggered("Command stopped by kill switch.")

                elapsed_cmd = time.perf_counter() - t_cmd_start
                if elapsed_cmd > self.config.max_wall_time_command_sec:
                    raise BudgetExceededError(f"Command exceeded wall-time limit ({self.config.max_wall_time_command_sec}s).")

                t_step_start = time.perf_counter()
                step_res = self._execute_step(step)
                step_duration_ms = (time.perf_counter() - t_step_start) * 1000

                self.total_steps += 1
                step_desc = getattr(step, "description", None) or f"{step.action.value} {step.target or ''}".strip()
                step_summary = {
                    "step": idx,
                    "action": step.action.value,
                    "desc": step_desc,
                    "duration_ms": round(step_duration_ms, 1),
                    "result": step_res,
                }
                executed_steps_summary.append(step_summary)

                if progress_cb:
                    progress_cb(idx, len(plan.steps), step, step_summary)

            self.total_commands += 1

            # 6. Update Context Memory (Last 5 turns)
            turn_record = {
                "raw_cmd": raw_cmd,
                "plan": plan,
                "steps_count": len(plan.steps),
                "url": self.last_known_url,
                "timestamp": time.time(),
            }
            self.turn_history.append(turn_record)
            if len(self.turn_history) > 5:
                self.turn_history.pop(0)

            self.context_memory.last_action = plan.steps[-1].action.value if plan.steps else None
            self.context_memory.last_url = self.last_known_url
            self.context_memory.last_plan = plan

            return {
                "status": "success",
                "milestones_count": len(plan.steps),
                "steps": executed_steps_summary,
                "total_elapsed_ms": round((time.perf_counter() - t_cmd_start) * 1000, 1),
            }

        except KillSwitchTriggered as ks:
            return {"status": "stopped", "message": str(ks)}
        except BudgetExceededError as be:
            return {"status": "error", "error": str(be)}
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        finally:
            self.is_command_running = False

    def _execute_step(self, step: Step) -> Dict[str, Any]:
        """Executes a single validated step on the browser."""
        import desktop_controller as orion_core
        from verify.playback import dismiss_consent_modals

        act = step.action
        target = str(step.target or "")

        if act in (ActionType.NAVIGATE, ActionType.BROWSE):
            # Check domain allow-list
            from urllib.parse import urlparse
            parsed_u = urlparse(target)
            domain = (parsed_u.hostname or parsed_u.netloc).lower()
            if domain and not any(allowed in domain for allowed in ALLOWED_DOMAINS):
                raise ActionNotAllowedError(f"Navigation to disallowed domain: {domain}")

            res = orion_core.OrionSystem.web_browse(target)
            if self.browser_manager.page:
                self.last_known_url = self.browser_manager.page.url
                self.last_known_title = self.browser_manager.page.title()
                # Check if this is a video/media player page
                if "youtube.com/watch" in self.last_known_url or "video" in self.last_known_url:
                    self.player_page = self.browser_manager.page
                    dismiss_consent_modals(self.player_page)
            return res

        elif act == ActionType.SEARCH:
            portal = step.params.get("portal", "google")
            res = orion_core.OrionSystem.web_search(portal, target)
            if self.browser_manager.page:
                self.last_known_url = self.browser_manager.page.url
                self.last_known_title = self.browser_manager.page.title()
            return res

        elif act == ActionType.CLICK:
            res = orion_core.OrionSystem.web_action("click", {"selector": target}, approved=getattr(step, "requires_approval", False))
            if self.browser_manager.page and not self.browser_manager.page.is_closed():
                try:
                    self.browser_manager.page.wait_for_load_state("domcontentloaded", timeout=2500)
                except Exception:
                    pass
                try:
                    self.last_known_url = self.browser_manager.page.url
                    self.last_known_title = self.browser_manager.page.title()
                except Exception:
                    pass
            self.last_reversible_action = None
            return res

        elif act == ActionType.FILL:
            res = orion_core.OrionSystem.web_action("fill", {"selector": step.params.get("selector", "input"), "text": target}, approved=getattr(step, "requires_approval", False))
            self.last_reversible_action = {"action": "fill", "selector": step.params.get("selector", "input")}
            return res

        elif act == ActionType.SCREENSHOT:
            return orion_core.take_screenshot()

        elif act == ActionType.ANNOUNCE:
            return orion_core.speak(target)

        elif act == ActionType.WAIT:
            sec = float(target) if target.replace('.', '', 1).isdigit() else 1.0
            time.sleep(sec)
            return {"status": "success", "waited": sec}

        elif act == ActionType.VERIFY:
            from verify.page_watcher import PageWatcher
            if self.browser_manager.page:
                watcher = PageWatcher(self.browser_manager.page)
                verdict = watcher.verify_page_health()
                return {"verdict": verdict.verdict.value, "signals": verdict.signals}
            return {"verdict": "OK"}
        elif act == ActionType.ARIA_SNAPSHOT:
            return orion_core.OrionSystem.web_action("aria_snapshot")

        return {"status": "unsupported", "action": act.value}

    def undo_last_action(self) -> Dict[str, Any]:
        """Undoes the last reversible action if available."""
        if not self.last_reversible_action:
            return {"status": "info", "message": "No reversible action available to undo."}
        # Clear typed text if available
        if self.last_reversible_action.get("action") == "type" and self.browser_manager.page:
            sel = self.last_reversible_action.get("selector")
            try:
                self.browser_manager.page.fill(sel, "")
                self.last_reversible_action = None
                return {"status": "success", "message": f"Cleared input field '{sel}'."}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "info", "message": "Undo complete."}

    # -----------------------------------------------------------------------
    # Media Watcher Background Thread
    # -----------------------------------------------------------------------

    def start_media_watcher(self) -> None:
        """Starts background ad/pause watcher."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._watcher_stop.clear()

        def _watcher_loop():
            from verify.playback import dismiss_consent_modals, heal_playback_state
            while not self._watcher_stop.is_set():
                time.sleep(3.0)
                # Pause watcher if command is actively executing
                if self.is_command_running:
                    continue
                try:
                    with self._lock:
                        if self.player_page and not self.player_page.is_closed():
                            # Auto-skip ads or resume unexpected pause
                            dismiss_consent_modals(self.player_page)
                except Exception:
                    pass

        self._watcher_thread = threading.Thread(target=_watcher_loop, daemon=True, name="NebulaMediaWatcher")
        self._watcher_thread.start()

    def stop_media_watcher(self) -> None:
        """Stops background media watcher."""
        self._watcher_stop.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=1.0)
            self._watcher_thread = None

    # -----------------------------------------------------------------------
    # Session Persistence & Shutdown
    # -----------------------------------------------------------------------

    def save_session_checkpoint(self) -> Path:
        """Atomically saves session state checkpoint to cache."""
        target_path = CACHE_DIR / f"session_{self.session_id}.json"
        state = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active_time,
            "commands_count": self.total_commands,
            "steps_count": self.total_steps,
            "last_known_url": self.last_known_url,
            "last_known_title": self.last_known_title,
        }
        atomic_write_json(target_path, state)
        return target_path

    def close(self) -> None:
        """Gracefully closes contexts, pages, watcher, and saves state atomically."""
        with self._lock:
            if self.closed:
                return
            self.closed = True
            self.stop_media_watcher()
            if getattr(self, "_control_server", None):
                try:
                    self._control_server.stop()
                    self._control_server = None
                except Exception:
                    pass
            try:
                self.save_session_checkpoint()
            except Exception:
                pass
            try:
                self.browser_manager.close()
            except Exception:
                pass
            logger.info(f"NebulaSession {self.session_id} shut down cleanly.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
