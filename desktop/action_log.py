"""
desktop/action_log.py — Append-only JSON action log + risk classifier.

Global Rules 4 & 6:
  - Every step: validate -> risk-check -> (approve if needed) -> execute -> verify -> log -> checkpoint.
  - High-risk actions ALWAYS require approval (default DENY).

RiskLevel classifies each action. ActionLog writes one JSON record per step
to a rotating NDJSON file under LOGS_DIR (from config).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from config import LOGS_DIR, atomic_write

logger = logging.getLogger("orion.desktop.action_log")


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# Actions that ALWAYS require explicit approval (default DENY — Global Rule 6)
_HIGH_RISK_ACTIONS: frozenset[str] = frozenset({
    "delete",
    "recycle",
    "shutdown",
    "restart",
    "install",
    "uninstall",
    "run_command",
    "send_message",
    "send_email",
    "post",
    "submit_payment",
    "place_order",
    "checkout",
    "create_account",
    "delete_account",
    "change_password",
    "grant_permission",
    "format_drive",
    "overwrite_file",
})

_MEDIUM_RISK_ACTIONS: frozenset[str] = frozenset({
    "move_file",
    "rename_file",
    "copy_file",
    "download_file",
    "upload_file",
    "click_submit",
    "fill_form",
    "create_file",
    "create_folder",
    "close_app",
    "kill_process",
})


def classify_risk(action: str, params: Optional[Dict[str, Any]] = None) -> RiskLevel:
    """Return the RiskLevel for a given action name."""
    action_lower = action.lower().strip()
    if action_lower in _HIGH_RISK_ACTIONS:
        return RiskLevel.HIGH
    if action_lower in _MEDIUM_RISK_ACTIONS:
        return RiskLevel.MEDIUM
    # Heuristic: any action string containing risky keywords
    risky_keywords = ("delete", "remove", "drop", "destroy", "purge", "format",
                      "shutdown", "restart", "pay", "checkout", "install")
    for kw in risky_keywords:
        if kw in action_lower:
            return RiskLevel.HIGH
    return RiskLevel.LOW


# ---------------------------------------------------------------------------
# Action record
# ---------------------------------------------------------------------------

@dataclass
class ActionRecord:
    """One logged step."""

    task_id:    str
    step_index: int
    action:     str
    params:     Dict[str, Any]
    risk:       RiskLevel
    approved:   bool          = False
    status:     str           = "pending"   # pending | ok | fail | skipped
    detail:     str           = ""
    timestamp:  float         = field(default_factory=time.time)
    duration_ms: float        = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["timestamp_iso"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)
        )
        return d


# ---------------------------------------------------------------------------
# Action log
# ---------------------------------------------------------------------------

_LOG_FILENAME = "desktop_actions.ndjson"


class ActionLog:
    """
    Thread-safe append-only JSON action log.

    One NDJSON file per run under LOGS_DIR.  Each line is a JSON ActionRecord.
    High-risk actions are refused unless ``approved=True`` is passed.
    """

    def __init__(self, log_path: Optional[Path] = None) -> None:
        self._path = Path(log_path) if log_path else LOGS_DIR / _LOG_FILENAME
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def log(self, record: ActionRecord) -> None:
        """Append one ActionRecord to the log file (thread-safe)."""
        line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
        with self._lock:
            try:
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
            except Exception as exc:
                logger.error(f"ActionLog write failed: {exc}")

    # ------------------------------------------------------------------
    def require_approval(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        approved: bool = False,
    ) -> None:
        """
        Enforce Global Rule 6: High-risk actions require explicit approval.

        Raises PermissionError if the action is HIGH risk and approved=False.
        """
        risk = classify_risk(action, params)
        if risk == RiskLevel.HIGH and not approved:
            raise PermissionError(
                f"High-risk action '{action}' requires explicit approval "
                f"(approved=True). Default is DENY."
            )

    # ------------------------------------------------------------------
    def read_all(self) -> list[ActionRecord]:
        """Read all records from the log (for testing/auditing)."""
        records = []
        if not self._path.exists():
            return records
        with self._lock:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        records.append(ActionRecord(
                            task_id    = d["task_id"],
                            step_index = d["step_index"],
                            action     = d["action"],
                            params     = d.get("params", {}),
                            risk       = RiskLevel(d["risk"]),
                            approved   = d.get("approved", False),
                            status     = d.get("status", "pending"),
                            detail     = d.get("detail", ""),
                            timestamp  = d.get("timestamp", 0.0),
                            duration_ms = d.get("duration_ms", 0.0),
                        ))
                    except Exception as exc:
                        logger.warning(f"Skipping malformed log line: {exc}")
        return records
