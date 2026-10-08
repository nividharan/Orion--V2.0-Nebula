"""
orion_desktop/controls/dialog_detector.py — Native Windows System Dialog Detector
=================================================================================
Scans visible windows for system dialog class names (#32770) indicating error
boxes, crash alerts, file overwrite warnings, or confirmation modals.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from .window_manager import WindowManager

logger = logging.getLogger("Orion.DialogDetector")


class DialogDetector:
    """Detects active Windows system dialogs (#32770)."""

    def __init__(self, window_manager: Optional[WindowManager] = None):
        self._wm = window_manager or WindowManager()

    def check_for_dialogs(self) -> Dict[str, Any]:
        """
        Scans all visible windows for dialog class names.
        Returns report with detected status and dialog details.
        """
        windows = self._wm.enumerate_windows()
        dialogs = []

        for win in windows:
            cls = win.get("class_name", "")
            title = win.get("title", "")
            # #32770 is the standard Windows dialog class
            if cls == "#32770" or "error" in title.lower() or "warning" in title.lower():
                dialogs.append({
                    "hwnd": win["hwnd"],
                    "title": title,
                    "class_name": cls,
                })

        return {
            "detected": len(dialogs) > 0,
            "count": len(dialogs),
            "dialogs": dialogs,
        }
