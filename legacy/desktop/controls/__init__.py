"""desktop/controls/__init__.py — re-export all control primitives."""

from .windows import WindowController
from .audio import AudioController
from .clipboard import ClipboardController
from .screenshot import take_screenshot
from .keyboard_mouse import KeyboardMouseController
from .files import FileController
from .processes import ProcessController

__all__ = [
    "WindowController",
    "AudioController",
    "ClipboardController",
    "take_screenshot",
    "KeyboardMouseController",
    "FileController",
    "ProcessController",
]
