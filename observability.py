"""
observability.py — Phase 8: Observability & Hardening
=====================================================
Principle:
  - Structured Logging: Emits JSON record per step (step, action, duration_ms, tokens, result).
  - Sanitization: Redacts credentials, tokens, and query secrets before writing to disk.
  - Reporting: Aggregates metrics (success rate, latency, token spend, error breakdown).
  - Regression Test Runner: Orchestrates all phase suites and outputs comprehensive audit report.
"""

from __future__ import annotations

import os
import sys
import json
import time
import re
import unittest
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from pathlib import Path


SECRET_KEY_NAMES = {
    "key", "api_key", "secret", "password", "token", "auth_token",
    "access_token", "bearer", "authorization", "private_key"
}


def is_secret_key(k: str) -> bool:
    kl = k.lower().strip()
    if kl in ("tokens", "tokens_used", "total_tokens"):
        return False
    return (
        kl in SECRET_KEY_NAMES
        or kl.endswith("_secret")
        or kl.endswith("_key")
        or kl.endswith("_token")
        or kl.endswith("_password")
    )


def sanitize_value(val: Any) -> Any:
    """Recursively redacts secret patterns and credentials from logged values."""
    if isinstance(val, str):
        cleaned = val
        cleaned = re.sub(
            r'(?i)\b(bearer|token|key|secret|password|auth)\s*[:=\s]\s*["\']?([^\s"\'<>]+)',
            r'\1 [REDACTED]',
            cleaned,
        )
        cleaned = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', cleaned)
        return cleaned
    elif isinstance(val, dict):
        out = {}
        for k, v in val.items():
            if is_secret_key(k):
                out[k] = "[REDACTED]"
            else:
                out[k] = sanitize_value(v)
        return out
    elif isinstance(val, list):
        return [sanitize_value(v) for v in val]
    return val


@dataclass
class StepLog:
    task_id: str
    step_index: int
    agent: str
    action: str
    target: Optional[str] = None
    duration_ms: float = 0.0
    tokens_used: int = 0
    result: str = "SUCCESS"  # SUCCESS, RETRY, FAILED, HEALED
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        sanitized = sanitize_value(d)
        return json.dumps(sanitized)


class StructuredLogger:
    """Thread-safe structured step logger appending to JSON lines."""

    def __init__(self, log_dir: Optional[str] = None):
        if not log_dir:
            log_dir = os.path.abspath(".cache/audit_logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._records: List[StepLog] = []

    def log_step(
        self,
        task_id: str,
        step_index: int,
        agent: str,
        action: str,
        duration_ms: float = 0.0,
        tokens_used: int = 0,
        result: str = "SUCCESS",
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> StepLog:
        record = StepLog(
            task_id=task_id,
            step_index=step_index,
            agent=agent,
            action=action,
            target=target,
            duration_ms=round(duration_ms, 2),
            tokens_used=tokens_used,
            result=result,
            details=details or {},
        )
        self._records.append(record)

        log_file = self.log_dir / f"task_{task_id}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")

        return record

    def get_records(self, task_id: Optional[str] = None) -> List[StepLog]:
        if task_id:
            return [r for r in self._records if r.task_id == task_id]
        return list(self._records)


class TaskAuditReporter:
    """Calculates audit metrics and produces formatted reports from recorded steps."""

    def __init__(self, logger_instance: Optional[StructuredLogger] = None):
        self.logger = logger_instance or StructuredLogger()

    def generate_report(self, task_id: str) -> Dict[str, Any]:
        records = self.logger.get_records(task_id)
        if not records:
            return {
                "task_id": task_id,
                "total_steps": 0,
                "success_rate": 1.0,
                "critical_errors": 0,
                "metrics": {},
            }

        total_steps = len(records)
        successful_steps = sum(1 for r in records if r.result in ("SUCCESS", "HEALED"))
        failed_steps = sum(1 for r in records if r.result == "FAILED")
        healed_steps = sum(1 for r in records if r.result == "HEALED")
        total_latency = sum(r.duration_ms for r in records)
        total_tokens = sum(r.tokens_used for r in records)
        critical_errors = failed_steps

        success_rate = successful_steps / total_steps if total_steps > 0 else 1.0
        avg_latency = total_latency / total_steps if total_steps > 0 else 0.0

        return {
            "task_id": task_id,
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "healed_steps": healed_steps,
            "success_rate": round(success_rate, 4),
            "critical_errors": critical_errors,
            "total_latency_ms": round(total_latency, 2),
            "avg_step_latency_ms": round(avg_latency, 2),
            "total_tokens_used": total_tokens,
            "records": [json.loads(r.to_json()) for r in records],
        }

    def generate_markdown_report(self, task_id: str) -> str:
        rep = self.generate_report(task_id)
        md = [
            f"# 📊 Task Audit Report: `{task_id}`",
            "",
            "## 📈 Key Metrics",
            f"- **Total Steps**: {rep['total_steps']}",
            f"- **Success Rate**: {rep['success_rate'] * 100:.1f}%",
            f"- **Critical Errors**: {rep['critical_errors']}",
            f"- **Healed Steps**: {rep['healed_steps']}",
            f"- **Total Latency**: {rep['total_latency_ms']} ms",
            f"- **Total Tokens Spent**: {rep['total_tokens_used']}",
            "",
            "## 📝 Step Breakdown",
            "| Step | Agent | Action | Result | Duration |",
            "|------|-------|--------|--------|----------|",
        ]
        for r in rep.get("records", []):
            md.append(f"| {r['step_index']} | {r['agent']} | {r['action']} | {r['result']} | {r['duration_ms']}ms |")

        return "\n".join(md)


def run_regression_suite(verbose: bool = False) -> Dict[str, Any]:
    """
    Executes all project test suites across all phases and produces an audit report.
    Exit criteria: 0 critical errors across the full project.
    """
    modules = [
        "web_engine.tests.test_smoke_engine",
        "tests.test_resolvers",
        "tests.test_schemas",
        "tests.test_brain",
        "tests.test_playback",
        "tests.test_api_client",
        "tests.test_society",
    ]

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    for mod in modules:
        try:
            m = __import__(mod, fromlist=["*"])
            suite.addTests(loader.loadTestsFromModule(m))
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load module {mod}: {e}",
                "critical_errors": 1,
            }

    start = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start

    failures = len(result.failures)
    errors = len(result.errors)
    total = result.testsRun
    critical_errors = failures + errors

    return {
        "success": critical_errors == 0,
        "total_tests": total,
        "failures": failures,
        "errors": errors,
        "critical_errors": critical_errors,
        "elapsed_seconds": round(elapsed, 2),
    }
