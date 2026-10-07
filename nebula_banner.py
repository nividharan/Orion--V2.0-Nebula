"""
nebula_banner.py — Ultra-Clean Minimalist CLI Header for Nebula (v2.0)
Styled after the Google Antigravity (agy) & Claude Code developer CLIs:
- Clean 2-line header with '✦ nebula' symbol and muted status pills.
- Zero bulky block ASCII art.
- Fast, instant, lightweight, and developer-focused.
"""

import sys
import os
import re
import ctypes

# 1. Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 2. Enable Windows Virtual Terminal Processing (ANSI Colors)
try:
    kernel32 = ctypes.windll.kernel32
    h_out = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
    kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
except Exception:
    pass

# Colors (Antigravity Clean Theme)
RST   = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

PURPLE = "\033[38;2;168;85;247m"  # Nebula Violet (#a855f7)
CYAN   = "\033[38;2;56;189;248m"   # Sky Cyan (#38bdf8)
GOLD   = "\033[38;2;251;191;36m"  # Star Gold (#fbbf24)
GRAY   = "\033[38;2;148;163;184m" # Muted Slate (#94a3b8)
DARK   = "\033[38;2;71;85;105m"   # Divider Line Slate (#475569)
WHITE  = "\033[38;2;248;250;252m" # Crisp White (#f8fafc)
GREEN  = "\033[38;2;52;211;153m"  # Ready Emerald (#34d399)

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)

def visible_width(text: str) -> int:
    return len(strip_ansi(text))

def pad_line(content: str, target_width: int) -> str:
    vw = visible_width(content)
    pad = max(0, target_width - vw)
    return f"{content}{' ' * pad}"


def get_nebula_splash(goal: str = None, verbose: bool = False) -> str:
    """
    Renders the ultra-clean Antigravity-style header for Nebula.
    """
    bar = f"{DARK}{'─' * 62}{RST}"
    
    header_line = (
        f"{GOLD}✦{RST} {BOLD}{PURPLE}nebula{RST} {GRAY}(v2.0){RST} "
        f"{DARK}·{RST} {GRAY}orion substrate{RST} "
        f"{DARK}·{RST} {GREEN}5 agents ready{RST}"
    )

    if goal:
        mode_pill = f" {GOLD}[verbose]{RST}" if verbose else ""
        goal_line = f"  {CYAN}›{RST} {WHITE}\"{goal}\"{RST}{mode_pill}"
        return f"\n{header_line}\n{goal_line}\n  {bar}\n"
    
    # Welcome / Help view
    desc_line = f"  {GRAY}Cognitive autonomous desktop & Chrome operations engine{RST}"
    help_body = [
        "",
        f"{header_line}",
        f"{desc_line}",
        f"  {bar}",
        f"  {BOLD}Usage:{RST}",
        f"    {PURPLE}nebula{RST} {CYAN}\"<goal>\"{RST}            {GRAY}Run autonomous Chrome task (minimal mode){RST}",
        f"    {PURPLE}nebula{RST} {CYAN}--verbose \"<goal>\"{RST}  {GRAY}Stream live multi-agent telemetry{RST}",
        f"    {PURPLE}orion{RST} {CYAN}browse <target>{RST}      {GRAY}Instant sub-50ms web navigation{RST}",
        f"    {PURPLE}orion{RST} {CYAN}watch{RST}                {GRAY}Inspect live 6 FPS perception buffer{RST}",
        "",
        f"  {BOLD}Examples:{RST}",
        f"    {PURPLE}nebula{RST} {CYAN}\"play kangal neeye on youtube\"{RST}",
        f"    {PURPLE}nebula{RST} {CYAN}\"open google play and search for free fire\"{RST}",
        f"    {PURPLE}nebula{RST} {CYAN}\"search github for autogen\"{RST}",
        f"  {bar}",
        "",
    ]
    return "\n".join(help_body)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "help":
        print(get_nebula_splash(goal=" ".join(sys.argv[1:])))
    else:
        print(get_nebula_splash())
