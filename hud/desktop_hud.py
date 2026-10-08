"""
Desktop Floating Glassmorphic HUD Pill for Windows.
Displays live agent status, reasoning subtitle, and health badge.
Uses WS_EX_NOACTIVATE style to ensure it NEVER steals focus from active applications.
"""

import ctypes
import logging
import platform
import threading
from typing import Optional

from hud.telemetry_hub import TelemetryHub, TelemetryState

logger = logging.getLogger("nebula.desktop_hud")

# Windows constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080


class DesktopHUD:
    """
    Floating desktop pill that renders real-time agent telemetry.
    Can run in a background thread without blocking main automation or stealing focus.
    """

    def __init__(self, hub: TelemetryHub):
        self.hub = hub
        self._root = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._status_var = None
        self._step_var = None

    def _apply_noactivate(self, hwnd: int) -> None:
        """Applies WS_EX_NOACTIVATE style so the window never steals input focus."""
        if platform.system() != "Windows":
            return
        try:
            user32 = getattr(ctypes.windll, "user32")
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW)
        except Exception as e:
            logger.debug("Failed to apply WS_EX_NOACTIVATE: %s", e)

    def _gui_loop(self) -> None:
        """Initializes Tkinter floating pill window."""
        try:
            import tkinter as tk
        except ImportError:
            logger.warning("Tkinter not available; DesktopHUD running in headless mode.")
            return

        try:
            self._root = tk.Tk()
            self._root.title("Orion Nebula HUD")
            self._root.geometry("340x70+20+20")  # Top-left corner
            self._root.overrideredirect(True)   # Borderless pill
            self._root.attributes("-topmost", True)
            self._root.attributes("-alpha", 0.90)  # Glassmorphism semi-transparency
            self._root.configure(bg="#1E1E24")

            self._status_var = tk.StringVar(value="🟢 Nebula: IDLE")
            self._step_var = tk.StringVar(value="Awaiting instructions...")

            frame = tk.Frame(self._root, bg="#1E1E24", padx=10, pady=6)
            frame.pack(fill=tk.BOTH, expand=True)

            status_lbl = tk.Label(
                frame,
                textvariable=self._status_var,
                font=("Segoe UI", 9, "bold"),
                fg="#61AFEF",
                bg="#1E1E24",
                anchor="w"
            )
            status_lbl.pack(fill=tk.X)

            step_lbl = tk.Label(
                frame,
                textvariable=self._step_var,
                font=("Segoe UI", 8),
                fg="#ABB2BF",
                bg="#1E1E24",
                anchor="w"
            )
            step_lbl.pack(fill=tk.X)

            # Apply focus protection once window handle is created
            self._root.update_idletasks()
            hwnd = self._root.winfo_id()
            self._apply_noactivate(hwnd)

            self._is_running = True
            self._root.mainloop()
        except Exception as e:
            logger.debug("DesktopHUD loop terminated: %s", e)
        finally:
            self._is_running = False

    def on_telemetry(self, state: TelemetryState) -> None:
        """Updates GUI labels safely from telemetry events."""
        if not self._is_running or not self._root:
            return
        try:
            status_text = f"{state.status_emoji} {state.agent_name}: {state.status}"
            step_text = f"{state.current_step} ({state.elapsed_sec:.1f}s)"
            if self._status_var and self._step_var:
                self._root.after(0, lambda: self._status_var.set(status_text))
                self._root.after(0, lambda: self._step_var.set(step_text))
        except Exception:
            pass

    def start(self) -> None:
        """Starts the HUD thread and hooks into TelemetryHub."""
        if self._thread and self._thread.is_alive():
            return
        self.hub.subscribe(self.on_telemetry)
        self._thread = threading.Thread(target=self._gui_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Gracefully shuts down the HUD."""
        self.hub.unsubscribe(self.on_telemetry)
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
        self._is_running = False
