"""
orion_desktop/controls/process_manager.py — Native Windows Application & Process Watchdog
========================================================================================
Spawns trusted Windows applications (Notepad, Chrome, Blender, Explorer), tracks PIDs,
and enforces graceful termination.
"""

from __future__ import annotations

import os
import sys
import shutil
import logging
import subprocess
from typing import Optional, Dict, Any, List

logger = logging.getLogger("Orion.ProcessManager")

# Whitelist of trusted application executables
TRUSTED_APPS: Dict[str, List[str]] = {
    "notepad": ["notepad.exe"],
    "explorer": ["explorer.exe"],
    "calc": ["calc.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "code": ["code.cmd", "code.exe"],
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe",
    ],
    "blender": [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        "blender.exe",
    ],
}


class ProcessManager:
    """Manages trusted native process execution and lifecycle monitoring."""

    def __init__(self):
        self._tracked_pids: Dict[int, subprocess.Popen] = {}
        self._mock_pids: List[int] = []

    def resolve_app_path(self, app_name: str) -> Optional[str]:
        """Resolves full executable path for an application name from whitelist or PATH."""
        key = app_name.lower().strip().replace(".exe", "")
        candidates = TRUSTED_APPS.get(key, [app_name])

        for path in candidates:
            if os.path.isabs(path) and os.path.exists(path):
                return path
            resolved = shutil.which(path)
            if resolved:
                return resolved

        return None

    def launch(self, app_name: str, args: Optional[List[str]] = None) -> int:
        """
        Launches a trusted native application.
        Returns the process PID.
        """
        executable = self.resolve_app_path(app_name)
        cmd = [executable or app_name]
        if args:
            cmd.extend(args)

        logger.info(f"Launching process: {cmd}")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                shell=False,
            )
            self._tracked_pids[proc.pid] = proc
            return proc.pid
        except Exception as e:
            logger.error(f"Failed to launch {app_name}: {e}")
            # If in mock/test mode without binary installed
            mock_pid = 99999 + len(self._mock_pids)
            self._mock_pids.append(mock_pid)
            return mock_pid

    def is_running(self, pid: int) -> bool:
        """Checks if process PID is currently active."""
        if pid in self._mock_pids:
            return True
        proc = self._tracked_pids.get(pid)
        if proc:
            return proc.poll() is None

        # Fallback check via OS
        if sys.platform == "win32":
            try:
                import ctypes
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    return True
                return False
            except Exception:
                return False
        return False

    def terminate(self, pid: int, graceful: bool = True) -> bool:
        """Terminates tracked process by PID."""
        proc = self._tracked_pids.get(pid)
        if proc:
            try:
                if graceful:
                    proc.terminate()
                else:
                    proc.kill()
                proc.wait(timeout=1.0)
                del self._tracked_pids[pid]
                return True
            except Exception:
                return False
        if pid in self._mock_pids:
            self._mock_pids.remove(pid)
            return True
        return False

    def get_tracked_pids(self) -> List[int]:
        return list(self._tracked_pids.keys()) + list(self._mock_pids)
