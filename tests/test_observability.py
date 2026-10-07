"""
tests/test_observability.py — Phase 8 exit criteria
====================================================
Deterministic test suite for observability.py.
Exit criteria (from plan):
  ✓ Structured JSON logging per step.
  ✓ Automatic secret redaction for keys, passwords, and tokens.
  ✓ Summary audit metrics (success rate, latency, token spend).
  ✓ Comprehensive regression suite passes with 0 critical errors.
"""

import os
import sys
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from observability import (
    StepLog,
    StructuredLogger,
    TaskAuditReporter,
    sanitize_value,
    run_regression_suite,
)


class TestStructuredLogging(unittest.TestCase):
    def setUp(self):
        self.test_log_dir = PROJECT_ROOT / ".cache" / "test_audit_logs"
        self.logger = StructuredLogger(log_dir=str(self.test_log_dir))

    def tearDown(self):
        if self.test_log_dir.exists():
            for f in self.test_log_dir.glob("*.jsonl"):
                try:
                    f.unlink()
                except Exception:
                    pass

    def test_log_step_writes_valid_jsonl(self):
        rec = self.logger.log_step(
            task_id="task_123",
            step_index=1,
            agent="Executor",
            action="navigate",
            duration_ms=45.2,
            tokens_used=120,
            result="SUCCESS",
            target="https://www.youtube.com",
        )
        self.assertEqual(rec.task_id, "task_123")
        self.assertEqual(rec.action, "navigate")

        # Verify JSON line file
        log_file = self.test_log_dir / "task_task_123.jsonl"
        self.assertTrue(log_file.exists())
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["task_id"], "task_123")
        self.assertEqual(data["duration_ms"], 45.2)

    def test_secret_redaction_in_logs(self):
        sensitive_text = "Bearer secret_api_key_12345"
        rec = self.logger.log_step(
            task_id="task_sec",
            step_index=1,
            agent="Commander",
            action="plan",
            target=sensitive_text,
            details={"api_key": "AIzaSyD-1234567890abcdefghijklmnopqr"},
        )
        raw_json = rec.to_json()
        self.assertNotIn("secret_api_key_12345", raw_json)
        self.assertNotIn("AIzaSyD-1234567890", raw_json)
        self.assertIn("[REDACTED]", raw_json)


class TestTaskAuditReporter(unittest.TestCase):
    def setUp(self):
        self.logger = StructuredLogger(log_dir=str(PROJECT_ROOT / ".cache" / "test_rep_logs"))
        self.reporter = TaskAuditReporter(self.logger)

    def test_report_metrics_calculation(self):
        task_id = "task_metrics"
        self.logger.log_step(task_id, 1, "Commander", "plan", duration_ms=10.0, result="SUCCESS")
        self.logger.log_step(task_id, 2, "Executor", "browse", duration_ms=20.0, result="SUCCESS")
        self.logger.log_step(task_id, 3, "Executor", "play", duration_ms=30.0, result="HEALED")
        self.logger.log_step(task_id, 4, "Verifier", "verify", duration_ms=15.0, result="SUCCESS")

        rep = self.reporter.generate_report(task_id)
        self.assertEqual(rep["total_steps"], 4)
        self.assertEqual(rep["successful_steps"], 4)  # SUCCESS + HEALED
        self.assertEqual(rep["healed_steps"], 1)
        self.assertEqual(rep["failed_steps"], 0)
        self.assertEqual(rep["critical_errors"], 0)
        self.assertEqual(rep["success_rate"], 1.0)
        self.assertEqual(rep["total_latency_ms"], 75.0)

        # Markdown report check
        md = self.reporter.generate_markdown_report(task_id)
        self.assertIn("# 📊 Task Audit Report", md)
        self.assertIn("100.0%", md)


class TestFullProjectRegressionSuite(unittest.TestCase):
    def test_all_phases_pass_with_zero_critical_errors(self):
        """
        Phase 8 Exit Criteria: Comprehensive audit report generated with 0 critical errors.
        Runs all unit suites across Phase 1, 2, 3, 4, 5, 6, 7.
        """
        res = run_regression_suite(verbose=False)
        self.assertTrue(
            res["success"],
            f"Regression suite had failures: {res}"
        )
        self.assertEqual(res["critical_errors"], 0)
        self.assertGreater(res["total_tests"], 100)


if __name__ == "__main__":
    unittest.main()
