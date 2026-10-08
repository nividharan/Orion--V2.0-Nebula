"""
repl.py — Interactive REPL Loop for Nebula/Orion Session
=========================================================
Provides the `nebula> ` interactive command console:
- Handles built-in commands with zero LLM/API calls
- Routes user commands through input pipeline, plan, and validation
- Handles Ctrl+C (stops running task when active; asks "Exit? (y/N)" when idle)
- Handles approvals with timeout & default DENY
- Handles clarifications with numbered candidate options
- Supports non-TTY / piped stdin execution without hanging
"""

from __future__ import annotations

import os
import sys
import time
import select
import signal
import threading
from typing import Any, Callable, Dict, List, Optional

from session import NebulaSession, SessionConfig
import media_control


BUILTIN_COMMANDS = {
    "help", "status", "tabs", "switch", "pause", "resume", "play",
    "stop", "undo", "history", "mode", "dry-run", "screenshot", "close", "exit", "quit"
}


def interactive_approver(prompt_msg: str, step: Any, timeout_sec: float = 15.0) -> bool:
    """
    Prompts the user for approval with default DENY and timeout.
    If stdin is not a TTY, strictly returns False.
    """
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        sys.stdout.write(f"\n[Security Gate] Approval required for '{step.action.value}': No interactive terminal. DENIED.\n")
        sys.stdout.flush()
        return False

    target_str = str(step.target or "")
    url_str = getattr(step, "url", None) or "(active page)"
    sys.stdout.write("\n" + "=" * 60 + "\n")
    sys.stdout.write("⚠️  [Security Approval Required]\n")
    sys.stdout.write(f"  Action: {step.action.value}\n")
    sys.stdout.write(f"  Target: {target_str}\n")
    sys.stdout.write(f"  Location: {url_str}\n")
    sys.stdout.write(f"  Read-back: {prompt_msg}\n")
    sys.stdout.write(f"  Approve? (y/N) [Timeout in {int(timeout_sec)}s, default No]: ")
    sys.stdout.flush()

    # Simple cross-platform prompt with timed check where available
    try:
        user_input = input().strip().lower()
        if user_input in ("y", "yes"):
            sys.stdout.write("  ✓ Approved by user.\n")
            sys.stdout.flush()
            return True
    except (KeyboardInterrupt, EOFError):
        pass

    sys.stdout.write("  ✗ Denied (default safe).\n")
    sys.stdout.flush()
    return False


def start_interactive_repl(session: Optional[NebulaSession] = None, initial_goal: Optional[str] = None) -> None:
    """
    Main REPL loop for interactive session.
    """
    owns_session = False
    if session is None:
        session = NebulaSession()
        owns_session = True

    try:
        sys.stdout.write("\n✦ nebula (v2.0) · interactive session active\n")
        sys.stdout.write("  Type a goal, or 'help' for built-in commands. 'exit' to quit.\n\n")
        sys.stdout.flush()

        # If an initial goal was supplied, run it first
        if initial_goal:
            _execute_line(session, initial_goal)

        is_tty = bool(sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty())

        while not session.closed:
            try:
                if is_tty:
                    sys.stdout.write("nebula> ")
                    sys.stdout.flush()
                    line = input()
                else:
                    line = sys.stdin.readline()
                    if not line:
                        # EOF on pipe / non-TTY
                        break

                cmd = line.strip()
                if not cmd:
                    continue

                if cmd.lower() in ("exit", "quit", "q"):
                    sys.stdout.write("Exiting session. Goodbye!\n")
                    break

                _execute_line(session, cmd)

            except KeyboardInterrupt:
                if session.is_command_running:
                    session.kill_switch_active.set()
                    sys.stdout.write("\n[Kill Switch] Stopping active command...\n")
                else:
                    if is_tty:
                        try:
                            sys.stdout.write("\nExit session? (y/N): ")
                            sys.stdout.flush()
                            ans = input().strip().lower()
                            if ans in ("y", "yes"):
                                break
                        except (KeyboardInterrupt, EOFError):
                            break
                    else:
                        break
            except EOFError:
                break

    finally:
        if owns_session:
            session.close()


def _execute_line(session: NebulaSession, cmd_line: str) -> None:
    """Dispatches a single command line: either built-in or full pipeline."""
    parts = cmd_line.split()
    first_word = parts[0].lower()

    # -------------------------------------------------------------
    # Built-in Commands (Zero LLM / Exact Match)
    # -------------------------------------------------------------
    if first_word == "help":
        sys.stdout.write("\nAvailable Commands:\n")
        sys.stdout.write("  help              Show this help menu\n")
        sys.stdout.write("  status            Show session metrics, active page title & URL\n")
        sys.stdout.write("  tabs              List all open tabs\n")
        sys.stdout.write("  switch <n>        Switch to tab by index\n")
        sys.stdout.write("  pause             Pause video on active player\n")
        sys.stdout.write("  resume / play     Resume video playback\n")
        sys.stdout.write("  stop              Stop active running task (kill switch)\n")
        sys.stdout.write("  undo              Undo last reversible action\n")
        sys.stdout.write("  history           Show recent commands\n")
        sys.stdout.write("  mode <s|n|q>      Set reasoning mode (spark, nova, quasar)\n")
        sys.stdout.write("  dry-run <on|off>  Toggle dry-run planning mode\n")
        sys.stdout.write("  screenshot        Capture CDP screen buffer to cache\n")
        sys.stdout.write("  close             Close browser window (keeps REPL)\n")
        sys.stdout.write("  exit / quit       Close browser and exit session\n")
        sys.stdout.write("  <natural language> Natural language browser automation goal\n\n")
        sys.stdout.flush()
        return

    elif first_word == "status":
        page = session.browser_manager.page if session.browser_manager.is_running else None
        url = page.url if page else "(no active page)"
        title = page.title() if page else "(no active page)"
        sys.stdout.write("\n🌌 Session Status:\n")
        sys.stdout.write(f"  Session ID:   {session.session_id}\n")
        sys.stdout.write(f"  Active URL:   {url}\n")
        sys.stdout.write(f"  Page Title:   {title}\n")
        sys.stdout.write(f"  Mode:         {session.config.mode.upper()}\n")
        sys.stdout.write(f"  Dry Run:      {session.config.dry_run}\n")
        sys.stdout.write(f"  Commands Run: {session.total_commands}\n")
        sys.stdout.write(f"  Steps Run:    {session.total_steps}\n")
        sys.stdout.write(f"  LLM Calls:    {session.total_llm_calls}\n\n")
        sys.stdout.flush()
        return

    elif first_word == "tabs":
        tabs = session.get_tabs()
        if not tabs:
            sys.stdout.write("No open tabs.\n")
        else:
            sys.stdout.write("\nOpen Tabs:\n")
            for t in tabs:
                marker = " [*]" if t["active"] else ""
                sys.stdout.write(f"  [{t['index']}] {t['title']} — {t['url']}{marker}\n")
            sys.stdout.write("\n")
        sys.stdout.flush()
        return

    elif first_word == "switch" and len(parts) > 1 and parts[1].isdigit():
        idx = int(parts[1])
        ok = session.switch_tab(idx)
        if ok:
            sys.stdout.write(f"Switched to tab [{idx}]: {session.last_known_url}\n")
        else:
            sys.stdout.write(f"Failed to switch to tab [{idx}]. Check tab list with 'tabs'.\n")
        sys.stdout.flush()
        return

    elif first_word == "pause":
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.pause_video(page)
            sys.stdout.write(f"  {res.get('message', 'Pause complete.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word in ("resume", "play") and len(parts) == 1:
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.resume_video(page)
            sys.stdout.write(f"  {res.get('message', 'Resume complete.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word == "next":
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.next_video(page)
            sys.stdout.write(f"  {res.get('message', 'Next video complete.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word == "volume" and len(parts) > 1 and parts[1].isdigit():
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.set_volume(page, int(parts[1]))
            sys.stdout.write(f"  {res.get('message', 'Volume adjusted.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word == "mute":
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.mute_video(page)
            sys.stdout.write(f"  {res.get('message', 'Mute complete.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word in ("skip-ad", "skip_ad") or (first_word == "skip" and len(parts) > 1 and parts[1].lower() == "ad"):
        page = session.player_page or session.browser_manager.page
        if page:
            res = media_control.skip_ad(page)
            sys.stdout.write(f"  {res.get('message', 'Skip ad complete.')}\n")
        else:
            sys.stdout.write("  No active page or player.\n")
        sys.stdout.flush()
        return

    elif first_word == "stop":
        session.kill_switch_active.set()
        sys.stdout.write("  [Kill Switch] Active task stopped. Browser remains open.\n")
        sys.stdout.flush()
        return

    elif first_word == "undo":
        res = session.undo_last_action()
        sys.stdout.write(f"  {res.get('message', 'Undo action complete.')}\n")
        sys.stdout.flush()
        return

    elif first_word == "history":
        sys.stdout.write("\nRecent Commands:\n")
        for i, h in enumerate(session.turn_history, 1):
            sys.stdout.write(f"  {i}. {h['raw_cmd']} ({h['steps_count']} steps)\n")
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    elif first_word == "mode":
        if len(parts) > 1 and parts[1].lower() in ("spark", "nova", "quasar"):
            session.config.mode = parts[1].lower()
            sys.stdout.write(f"Reasoning mode set to: {session.config.mode.upper()}\n")
        else:
            sys.stdout.write(f"Current mode: {session.config.mode.upper()} (options: spark, nova, quasar)\n")
        sys.stdout.flush()
        return

    elif first_word == "dry-run":
        if len(parts) > 1 and parts[1].lower() in ("on", "true", "1"):
            session.config.dry_run = True
            sys.stdout.write("Dry-run mode ENABLED.\n")
        elif len(parts) > 1 and parts[1].lower() in ("off", "false", "0"):
            session.config.dry_run = False
            sys.stdout.write("Dry-run mode DISABLED.\n")
        else:
            sys.stdout.write(f"Dry-run mode is: {'ON' if session.config.dry_run else 'OFF'}\n")
        sys.stdout.flush()
        return

    elif first_word == "screenshot":
        import desktop_controller as orion_core
        shot = orion_core.take_screenshot()
        sys.stdout.write(f"  Screenshot saved: {shot.get('saved_path')}\n")
        sys.stdout.flush()
        return

    elif first_word == "close":
        session.close_browser_keep_session()
        sys.stdout.write("  Closed browser window. Session remains open for next command.\n")
        sys.stdout.flush()
        return

    # -------------------------------------------------------------
    # Full Goal Execution Pipeline
    # -------------------------------------------------------------
    def progress_callback(step_num: int, total_steps: int, step_obj: Any, summary: Dict[str, Any]):
        sys.stdout.write(f"  🌌 [{step_num}/{total_steps}] {step_obj.description} ({summary['duration_ms']:.0f}ms) ✓\n")
        sys.stdout.flush()

    res = session.execute_command_string(
        cmd_line,
        approver=interactive_approver,
        progress_cb=progress_callback
    )

    if res.get("status") == "ask":
        sys.stdout.write(f"\n❓ {res.get('question')}\n")
        opts = res.get("options", [])
        for o in opts:
            sys.stdout.write(f"   [{o.get('index', 1)}] {o.get('label')}\n")
        sys.stdout.flush()
        # Accept clarification input
        try:
            choice = input("Select an option (1-3): ").strip()
            if choice.isdigit() and int(choice) <= len(opts):
                chosen_label = opts[int(choice) - 1].get("label")
                _execute_line(session, chosen_label)
        except (KeyboardInterrupt, EOFError):
            pass

    elif res.get("status") == "success":
        sys.stdout.write(f"  Done ({res.get('total_elapsed_ms', 0):.0f}ms) ✓\n\n")
        sys.stdout.flush()

    elif res.get("status") in ("stopped", "cancelled", "denied"):
        sys.stdout.write(f"  Notice: {res.get('message')}\n\n")
        sys.stdout.flush()

    elif res.get("status") == "error":
        sys.stdout.write(f"  Error: {res.get('error')}\n\n")
        sys.stdout.flush()
