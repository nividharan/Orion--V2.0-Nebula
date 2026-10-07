"""
desktop/executor.py — run_plan() step-loop with kill-switch, limits, checkpoint/resume.

Implements Global Rule 4:
  validate -> risk-check -> (approve if needed) -> execute -> verify (CODE first) -> log -> checkpoint.

Features:
  - KillSwitch integration (Ctrl+Shift+K)
  - TaskLimits enforcement (max steps, wall-time, LLM call cap)
  - Dry-run mode: stops before sensitive actions, reports what WOULD happen
  - Checkpoint/resume: atomic JSON state in .cache/tasks/<task_id>.json
  - Undo history: one-step reverse for completed actions
  - Approval gate: HIGH-risk actions default DENY
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import TASKS_DIR, atomic_write
from desktop.action_log import ActionLog, ActionRecord, RiskLevel, classify_risk
from desktop.kill_switch import KillSwitch, KillSwitchActivated, TaskLimits
from desktop.undo import UndoHistory
from desktop.controls.windows import WindowController
from desktop.controls.audio import AudioController
from desktop.controls.clipboard import ClipboardController
from desktop.controls.screenshot import take_screenshot
from desktop.controls.keyboard_mouse import KeyboardMouseController
from desktop.controls.files import FileController
from desktop.controls.processes import ProcessController

logger = logging.getLogger("orion.desktop.executor")


# ---------------------------------------------------------------------------
# TaskResult
# ---------------------------------------------------------------------------

@dataclass
class TaskResult:
    """Structured result returned by run_plan()."""
    task_id:    str
    status:     str             # ok | fail | killed | dry_run | partial
    steps_done: int = 0
    data:       Dict[str, Any] = field(default_factory=dict)
    errors:     List[str]      = field(default_factory=list)
    cost:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id":    self.task_id,
            "status":     self.status,
            "steps_done": self.steps_done,
            "data":       self.data,
            "errors":     self.errors,
            "cost":       self.cost,
        }


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _checkpoint_path(task_id: str) -> Path:
    return TASKS_DIR / f"{task_id}.json"


def _save_checkpoint(task_id: str, state: dict) -> None:
    """Atomically write task checkpoint to .cache/tasks/<task_id>.json."""
    try:
        atomic_write(_checkpoint_path(task_id), state)
    except Exception as exc:
        logger.warning(f"Checkpoint write failed for task {task_id}: {exc}")


def _load_checkpoint(task_id: str) -> Optional[dict]:
    """Load an existing checkpoint, or return None."""
    cp = _checkpoint_path(task_id)
    if not cp.exists():
        return None
    try:
        return json.loads(cp.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Checkpoint read failed for task {task_id}: {exc}")
        return None


def _clear_checkpoint(task_id: str) -> None:
    cp = _checkpoint_path(task_id)
    try:
        cp.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# DesktopExecutor
# ---------------------------------------------------------------------------

class DesktopExecutor:
    """
    Executes a sequence of desktop automation steps with full safety guardrails.

    Args:
        allowed_file_roots: Paths the FileController is allowed to touch.
        kill_switch:        Shared KillSwitch instance (or None for auto-create).
        undo:               Shared UndoHistory (or None for auto-create).
        action_log:         Shared ActionLog (or None for auto-create).
        dry_run:            If True, validate and log but NEVER execute actions.
        approval_callback:  Optional async/sync callable(action, params) -> bool
                            called for HIGH-risk actions. Default: always deny.
        limits:             TaskLimits instance. Defaults to TaskLimits().
    """

    def __init__(
        self,
        allowed_file_roots: Optional[List[Path]] = None,
        kill_switch: Optional[KillSwitch] = None,
        undo: Optional[UndoHistory] = None,
        action_log: Optional[ActionLog] = None,
        dry_run: bool = False,
        approval_callback: Optional[Callable[[str, dict], bool]] = None,
        limits: Optional[TaskLimits] = None,
    ) -> None:
        self._allowed_roots = allowed_file_roots or []
        self._ks = kill_switch or KillSwitch()
        self._undo = undo or UndoHistory()
        self._log = action_log or ActionLog()
        self._dry_run = dry_run
        self._approve = approval_callback or (lambda action, params: False)  # default DENY
        self._limits = limits or TaskLimits()

        # Controls
        self._windows = WindowController()
        self._audio = AudioController()
        self._clipboard = ClipboardController()
        self._km = KeyboardMouseController()
        self._files = FileController(self._allowed_roots, undo=self._undo)
        self._procs = ProcessController()

    # ------------------------------------------------------------------
    def _dispatch(self, step: dict) -> Dict[str, Any]:
        """Route a step dict to the appropriate control method."""
        action = str(step.get("action", "")).lower().strip()
        params = step.get("params", {}) or {}

        # Window controls
        if action == "open_app":
            return self._windows.open_app(
                params.get("executable", ""),
                args=params.get("args", []),
                wait_ms=params.get("wait_ms", 1500),
            )
        if action == "close_app":
            return self._windows.close_app(params.get("title", ""))
        if action == "focus_window":
            return self._windows.focus_window(params.get("title", ""))
        if action == "move_window":
            return self._windows.move_window(
                params.get("title", ""),
                int(params.get("x", 0)),
                int(params.get("y", 0)),
            )
        if action == "resize_window":
            return self._windows.resize_window(
                params.get("title", ""),
                int(params.get("width", 800)),
                int(params.get("height", 600)),
            )
        if action == "snap_window":
            return self._windows.snap_window(
                params.get("title", ""),
                params.get("position", "maximize"),
            )

        # Audio controls
        if action == "set_volume":
            return self._audio.set_volume(float(params.get("level", 0.5)))
        if action == "mute":
            return self._audio.mute()
        if action == "unmute":
            return self._audio.unmute()
        if action == "get_volume":
            return self._audio.get_volume()

        # Clipboard
        if action == "get_clipboard":
            return self._clipboard.get_text()
        if action == "set_clipboard":
            return self._clipboard.set_text(str(params.get("text", "")))

        # Screenshot
        if action == "screenshot":
            return take_screenshot(
                window_title=str(params.get("title", "")),
                save_path=params.get("save_path"),
            )

        # Keyboard / mouse
        if action == "type_text":
            return self._km.type_text(
                str(params.get("text", "")),
                interval=float(params.get("interval", 0.02)),
            )
        if action == "hotkey":
            keys = params.get("keys", [])
            return self._km.hotkey(*keys)
        if action == "press_key":
            return self._km.press_key(str(params.get("key", "")))
        if action == "click":
            return self._km.click(
                int(params.get("x", 0)),
                int(params.get("y", 0)),
                button=params.get("button", "left"),
            )
        if action == "double_click":
            return self._km.double_click(int(params.get("x", 0)), int(params.get("y", 0)))
        if action == "scroll":
            return self._km.scroll(
                int(params.get("x", 0)),
                int(params.get("y", 0)),
                int(params.get("clicks", 3)),
            )
        if action == "click_element":
            return self._km.click_element_by_name(
                str(params.get("app_title", "")),
                str(params.get("element_name", "")),
                control_type=str(params.get("control_type", "Button")),
            )

        # File ops
        if action == "create_file":
            return self._files.create_file(
                params.get("path", ""),
                content=str(params.get("content", "")),
            )
        if action == "create_folder":
            return self._files.create_folder(params.get("path", ""))
        if action == "copy_file":
            return self._files.copy_file(params.get("src", ""), params.get("dst", ""))
        if action == "move_file":
            return self._files.move_file(params.get("src", ""), params.get("dst", ""))
        if action == "rename_file":
            return self._files.rename_file(params.get("path", ""), params.get("new_name", ""))
        if action == "delete":
            # HIGH risk — handled by approval gate above; always approved here
            return self._files.delete_file(params.get("path", ""), approved=True)
        if action == "read_file":
            return self._files.read_file(params.get("path", ""))

        # Process ops
        if action == "list_processes":
            procs = self._procs.list_processes(name_filter=params.get("name_filter"))
            return {"ok": True, "detail": f"Found {len(procs)} processes", "data": procs}
        if action == "kill_process":
            return self._procs.kill_process(
                pid=params.get("pid"),
                name=params.get("name"),
                approved=True,   # approval gate handles this
            )

        return {"ok": False, "detail": f"Unknown action: '{action}'"}

    # ------------------------------------------------------------------
    def run_plan(
        self,
        steps: List[Dict[str, Any]],
        task_id: Optional[str] = None,
        resume: bool = False,
    ) -> TaskResult:
        """
        Execute a list of step dicts following the Global Rule 4 loop.

        Each step dict must have at minimum: {action: str, params: dict}.
        Optional fields: {expect: str, on_fail: retry|skip|abort, approved: bool}
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        self._limits.reset_counters()
        self._ks.arm()

        result = TaskResult(task_id=task_id, status="ok")
        start_index = 0

        # --- Resume from checkpoint ---
        if resume:
            cp = _load_checkpoint(task_id)
            if cp:
                start_index = cp.get("steps_done", 0)
                result.steps_done = start_index
                logger.info(f"Resuming task {task_id} from step {start_index}")

        # --- Dry-run header ---
        if self._dry_run:
            logger.info(f"DRY-RUN mode — task {task_id}: will validate {len(steps)} steps")

        try:
            for idx, step in enumerate(steps[start_index:], start=start_index):
                # ── Kill-switch + limit check ──────────────────────────────
                try:
                    self._limits.check_all(kill_switch=self._ks)
                except KillSwitchActivated as e:
                    result.status = "killed"
                    result.errors.append(str(e))
                    logger.warning(f"Task {task_id} killed at step {idx}")
                    return result
                except RuntimeError as e:
                    result.status = "fail"
                    result.errors.append(str(e))
                    logger.error(f"Task {task_id} limit violated at step {idx}: {e}")
                    return result

                action = str(step.get("action", "")).lower()
                params = step.get("params", {}) or {}
                on_fail = step.get("on_fail", "abort")
                explicitly_approved = bool(step.get("approved", False))

                risk = classify_risk(action, params)

                # ── Approval gate for HIGH-risk ────────────────────────────
                if risk == RiskLevel.HIGH:
                    if self._dry_run:
                        logger.info(
                            f"[DRY-RUN] Step {idx}: '{action}' is HIGH-RISK — "
                            "would require approval here."
                        )
                        result.steps_done += 1
                        self._limits.increment_step()
                        continue

                    if not explicitly_approved:
                        approved = self._approve(action, params)
                    else:
                        approved = True

                    if not approved:
                        err = (
                            f"Step {idx}: '{action}' is HIGH-RISK and was DENIED. "
                            "Pass approved=True or configure an approval_callback."
                        )
                        logger.error(err)
                        record = ActionRecord(
                            task_id=task_id, step_index=idx, action=action,
                            params=params, risk=risk, approved=False,
                            status="skipped", detail="Denied by approval gate",
                        )
                        self._log.log(record)
                        if on_fail == "skip":
                            result.errors.append(err)
                            continue
                        result.status = "fail"
                        result.errors.append(err)
                        return result

                # ── Dry-run: skip execution ────────────────────────────────
                if self._dry_run:
                    logger.info(
                        f"[DRY-RUN] Step {idx}: '{action}' (risk={risk.value}) — skipped"
                    )
                    result.steps_done += 1
                    self._limits.increment_step()
                    continue

                # ── Execute ───────────────────────────────────────────────
                t0 = time.time()
                try:
                    exec_result = self._dispatch(step)
                except Exception as exc:
                    exec_result = {"ok": False, "detail": str(exc)}

                duration_ms = (time.time() - t0) * 1000
                step_ok = bool(exec_result.get("ok", False))
                detail = str(exec_result.get("detail", ""))

                # ── Log ───────────────────────────────────────────────────
                record = ActionRecord(
                    task_id=task_id,
                    step_index=idx,
                    action=action,
                    params=params,
                    risk=risk,
                    approved=explicitly_approved or risk != RiskLevel.HIGH,
                    status="ok" if step_ok else "fail",
                    detail=detail,
                    duration_ms=duration_ms,
                )
                self._log.log(record)
                self._limits.increment_step()

                if step_ok:
                    result.steps_done += 1
                    if exec_result.get("data"):
                        result.data[f"step_{idx}"] = exec_result["data"]

                    # ── Checkpoint ────────────────────────────────────────
                    _save_checkpoint(task_id, {
                        "task_id": task_id,
                        "steps_done": result.steps_done,
                        "timestamp": time.time(),
                    })
                else:
                    err = f"Step {idx} '{action}' failed: {detail}"
                    result.errors.append(err)
                    logger.warning(err)

                    if on_fail == "abort":
                        result.status = "partial"
                        return result
                    elif on_fail == "retry":
                        # Idempotent retry once (never for destructive actions)
                        if risk == RiskLevel.LOW:
                            time.sleep(1.0)
                            retry_result = self._dispatch(step)
                            if not retry_result.get("ok"):
                                result.status = "partial"
                                return result
                        # else fall through
                    # on_fail == "skip": continue to next step

        except KillSwitchActivated as e:
            result.status = "killed"
            result.errors.append(str(e))

        finally:
            self._ks.disarm()
            if result.status == "ok":
                _clear_checkpoint(task_id)

        result.cost = {
            "steps_done":    result.steps_done,
            "elapsed_s":     round(self._limits.elapsed_seconds, 2),
            "llm_calls":     self._limits._llm_calls,
            "tokens_used":   self._limits._tokens_used,
        }

        logger.info(
            f"Task {task_id} complete: status={result.status}, "
            f"steps={result.steps_done}/{len(steps)}, "
            f"errors={len(result.errors)}"
        )
        return result


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_plan(
    steps: List[Dict[str, Any]],
    task_id: Optional[str] = None,
    allowed_file_roots: Optional[List[Path]] = None,
    dry_run: bool = False,
    approval_callback: Optional[Callable] = None,
    limits: Optional[TaskLimits] = None,
    resume: bool = False,
) -> TaskResult:
    """
    Create a DesktopExecutor and run a plan in one call.

    This is the primary entry point for the desktop executor.
    """
    executor = DesktopExecutor(
        allowed_file_roots=allowed_file_roots,
        dry_run=dry_run,
        approval_callback=approval_callback,
        limits=limits,
    )
    return executor.run_plan(steps, task_id=task_id, resume=resume)
