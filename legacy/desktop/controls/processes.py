"""
desktop/controls/processes.py — Process list and safe kill via psutil.

kill_process() is MEDIUM risk (requires approval for non-owned processes).
Returns structured {ok, detail} on every call.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("orion.desktop.processes")


def _ok(detail: str = "") -> Dict[str, Any]:
    return {"ok": True, "detail": detail}


def _fail(detail: str) -> Dict[str, Any]:
    return {"ok": False, "detail": detail}


class ProcessController:
    """
    Process introspection and management using psutil.

    All public methods return {ok: bool, detail: str}.
    """

    # ------------------------------------------------------------------
    def list_processes(
        self,
        name_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return a list of running processes.

        Args:
            name_filter: If given, only return processes whose name contains
                         this string (case-insensitive).
        """
        try:
            import psutil  # type: ignore[import]
            procs = []
            for p in psutil.process_iter(["pid", "name", "status", "username"]):
                try:
                    info = p.info
                    if name_filter and name_filter.lower() not in (info.get("name") or "").lower():
                        continue
                    procs.append({
                        "pid":      info["pid"],
                        "name":     info.get("name", ""),
                        "status":   info.get("status", ""),
                        "username": info.get("username", ""),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return procs
        except Exception as exc:
            logger.warning(f"list_processes failed: {exc}")
            return []

    # ------------------------------------------------------------------
    def is_running(self, name: str) -> bool:
        """Return True if a process with the given name is currently running."""
        return len(self.list_processes(name_filter=name)) > 0

    # ------------------------------------------------------------------
    def get_pid(self, name: str) -> Optional[int]:
        """Return the PID of the first matching process, or None."""
        procs = self.list_processes(name_filter=name)
        return procs[0]["pid"] if procs else None

    # ------------------------------------------------------------------
    def kill_process(
        self,
        pid: Optional[int] = None,
        name: Optional[str] = None,
        approved: bool = False,
    ) -> Dict[str, Any]:
        """
        Terminate a process by PID or name.

        HIGH RISK if the process is not owned by the current user.
        Requires approved=True to proceed.
        """
        if not approved:
            return _fail(
                "kill_process requires approved=True (HIGH RISK action)."
            )

        if pid is None and name is None:
            return _fail("kill_process: specify pid or name")

        try:
            import psutil  # type: ignore[import]

            if pid is None:
                procs = self.list_processes(name_filter=name)
                if not procs:
                    return _fail(f"No process found with name '{name}'")
                pid = procs[0]["pid"]

            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()

            return _ok(f"Terminated process '{proc_name}' (PID {pid})")

        except psutil.NoSuchProcess:
            return _fail(f"Process PID {pid} does not exist")
        except psutil.AccessDenied:
            return _fail(f"Access denied terminating PID {pid}")
        except Exception as exc:
            return _fail(f"kill_process failed: {exc}")

    # ------------------------------------------------------------------
    def get_memory_usage_mb(self, pid: int) -> Optional[float]:
        """Return RSS memory usage in MB for the given PID, or None."""
        try:
            import psutil  # type: ignore[import]
            proc = psutil.Process(pid)
            return proc.memory_info().rss / (1024 * 1024)
        except Exception:
            return None

    # ------------------------------------------------------------------
    def get_cpu_percent(self, pid: int, interval: float = 0.5) -> Optional[float]:
        """Return CPU% for the given PID over ``interval`` seconds, or None."""
        try:
            import psutil  # type: ignore[import]
            proc = psutil.Process(pid)
            return proc.cpu_percent(interval=interval)
        except Exception:
            return None
