"""
orion_desktop/adapters/base.py — Abstract App Adapter Interface
================================================================
Defines the contract that specialized application adapters (Chrome, Blender,
Notepad, etc.) must implement to interface with the Orion Substrate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple


class BaseAppAdapter(ABC):
    """
    Abstract Base Class for application-specific adapters in Orion.
    Enables specialized cognitive models (Nebula for Chrome, Blender Model for 3D)
    to command target applications through a unified API.
    """

    @property
    @abstractmethod
    def app_name(self) -> str:
        """Unique identifier for the target application (e.g. 'chrome', 'blender', 'notepad')."""
        ...

    @abstractmethod
    def launch(self, *args, **kwargs) -> int:
        """
        Launches the target application process.
        Returns the process ID (PID).
        """
        ...

    @abstractmethod
    def find_window(self) -> Optional[int]:
        """
        Locates the primary application window handle (HWND).
        Returns None if window is not found or not visible.
        """
        ...

    @abstractmethod
    def focus(self) -> bool:
        """
        Safely brings the target application to active foreground.
        Returns True if focus was successfully acquired.
        """
        ...

    @abstractmethod
    def capture_viewport(self) -> Optional[bytes]:
        """
        Captures the visual viewport bounding box of the target application.
        Returns PNG/JPEG image bytes, or None on failure.
        """
        ...

    @abstractmethod
    def hotkey(self, *keys: str) -> bool:
        """
        Sends application-specific shortcut key chord (e.g. 'ctrl', 'c' or 'shift', 'a').
        Returns True if dispatched successfully.
        """
        ...

    @abstractmethod
    def type_text(self, text: str) -> bool:
        """
        Types text into the currently focused element of the application.
        Returns True if dispatched successfully.
        """
        ...

    @abstractmethod
    def close(self, graceful: bool = True) -> bool:
        """
        Closes the application process.
        Returns True if closed successfully.
        """
        ...

    def get_status(self) -> Dict[str, Any]:
        """Returns diagnostic metadata about the application state."""
        hwnd = self.find_window()
        return {
            "app_name": self.app_name,
            "running": hwnd is not None,
            "hwnd": hwnd,
        }
