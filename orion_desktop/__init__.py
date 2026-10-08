"""
orion_desktop — Universal Operating System & Desktop Automation Substrate
==========================================================================
Powers both Nebula (Chrome) and the Blender Model (3D).
"""

from .substrate import OrionSubstrate
from .adapters.base import BaseAppAdapter
from .adapters.generic import GenericAppAdapter
from .adapters.chrome import ChromeAdapter
from .adapters.blender import BlenderAdapter
from .controls.keyboard import KeyboardDriver
from .controls.mouse import MouseDriver
from .controls.window_manager import WindowManager
from .controls.process_manager import ProcessManager
from .controls.screen_capture import ScreenCapture
from .controls.dialog_detector import DialogDetector

__all__ = [
    "OrionSubstrate",
    "BaseAppAdapter",
    "GenericAppAdapter",
    "ChromeAdapter",
    "BlenderAdapter",
    "KeyboardDriver",
    "MouseDriver",
    "WindowManager",
    "ProcessManager",
    "ScreenCapture",
    "DialogDetector",
]
