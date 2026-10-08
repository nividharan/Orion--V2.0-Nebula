"""
Terminal Live ANSI Status Bar for Nebula & Orion.
Renders unbuffered live telemetry updates directly to stdout.
"""

import sys
from hud.telemetry_hub import TelemetryHub, TelemetryState


class TerminalHUD:
    """Renders single-line or multi-line live ANSI status bar for terminal users."""

    def __init__(self, hub: TelemetryHub):
        self.hub = hub
        self._enabled = sys.stdout.isatty()

    def format_bar(self, state: TelemetryState) -> str:
        """Formats single-line ANSI status bar."""
        # ANSI styles
        CYAN = "\033[96m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
        DIM = "\033[2m"

        step_display = state.current_step[:45] + ("..." if len(state.current_step) > 45 else "")
        delta_str = f"Δ:{state.visual_delta_pct:.1f}%" if state.visual_delta_pct > 0 else ""

        line = (
            f"\r{state.status_emoji} {BOLD}[{state.agent_name}]{RESET} "
            f"{CYAN}{state.status}{RESET} | {step_display} "
            f"{DIM}({state.elapsed_sec:.1f}s {delta_str}){RESET}"
        )
        return line

    def render(self, state: TelemetryState) -> None:
        """Writes formatted bar to stdout without newline."""
        try:
            bar = self.format_bar(state)
            sys.stdout.write(bar)
            sys.stdout.flush()
        except Exception:
            pass

    def start(self) -> None:
        """Subscribes to telemetry hub updates."""
        self.hub.subscribe(self.render)

    def stop(self) -> None:
        """Unsubscribes from telemetry hub and cleans up line."""
        self.hub.unsubscribe(self.render)
        try:
            sys.stdout.write("\n")
            sys.stdout.flush()
        except Exception:
            pass
