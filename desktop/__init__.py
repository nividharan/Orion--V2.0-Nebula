"""
desktop/ — Phase 5: Desktop Executor
=====================================
Provides hardened desktop automation for Orion, organized as:

  desktop/
    __init__.py          — package init, exports
    kill_switch.py       — global hotkey kill-switch + task-limit enforcement
    action_log.py        — append-only JSON action log + risk classifier
    undo.py              — undo history (stack, 20-item cap, Recycle Bin delete)
    controls/
      __init__.py        — re-export surface
      windows.py         — open/close/focus/move/resize/snap windows
      audio.py           — volume via pycaw
      clipboard.py       — read/write clipboard
      screenshot.py      — dual-engine screenshot (CDP / Win32)
      keyboard_mouse.py  — pyautogui / pywinauto keyboard & mouse
      files.py           — allowed-folder file ops with undo
      processes.py       — process list / kill (psutil)
    executor.py          — run_plan() step-loop with kill-switch, limits, checkpoint
"""

from .kill_switch import KillSwitch, TaskLimits
from .action_log import ActionLog, ActionRecord, RiskLevel
from .undo import UndoHistory
from .executor import DesktopExecutor, run_plan

__all__ = [
    "KillSwitch",
    "TaskLimits",
    "ActionLog",
    "ActionRecord",
    "RiskLevel",
    "UndoHistory",
    "DesktopExecutor",
    "run_plan",
]
