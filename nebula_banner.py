"""
nebula_banner.py — High-Aesthetic CLI Splash Banner for Nebula (v2.0)
Styled after the Google Antigravity (agy) CLI.
"""

import sys
import os
import re
import unicodedata
import ctypes

# 1. Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 2. Enable Windows Virtual Terminal Processing (ANSI TrueColor)
try:
    kernel32 = ctypes.windll.kernel32
    h_out = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
    kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
except Exception:
    pass

# Colors & Styles (Antigravity Cosmic Palette)
RST   = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
ITAL  = "\033[3m"

# Gradients & Highlights
V1    = "\033[38;2;124;58;237m"  # Deep Cosmic Violet (#7c3aed)
V2    = "\033[38;2;147;51;234m"  # Purple (#9333ea)
V3    = "\033[38;2;168;85;247m"  # Vivid Magenta-Violet (#a855f7)
V4    = "\033[38;2;192;132;252m" # Soft Lilac (#c084fc)
C1    = "\033[38;2;56;189;248m"   # Sky Cyan (#38bdf8)
C2    = "\033[38;2;45;212;191m"   # Emerald Teal (#2dd4bf)
GOLD  = "\033[38;2;251;191;36m"  # Solar Gold (#fbbf24)
GRAY  = "\033[38;2;148;163;184m" # Slate Gray (#94a3b8)
DARK  = "\033[38;2;71;85;105m"   # Dark Border Slate (#475569)
BG_P  = "\033[48;2;30;27;75m"    # Deep Indigo Pill BG
BG_C  = "\033[48;2;12;74;110m"   # Deep Cyan Pill BG
WHITE = "\033[38;2;248;250;252m" # Bright White

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub('', text)

def char_width(ch: str) -> int:
    w = unicodedata.east_asian_width(ch)
    if w in ('F', 'W'):
        return 2
    if ord(ch) in range(0x1F300, 0x1F9FF) or ord(ch) in range(0x2600, 0x27BF):
        return 2
    return 1

def visible_width(text: str) -> int:
    clean = strip_ansi(text).replace('\ufe0f', '')
    w = 0
    for ch in clean:
        w += char_width(ch)
    return w

def pad_line(content: str, target_width: int) -> str:
    vw = visible_width(content)
    pad = max(0, target_width - vw)
    return f"{content}{' ' * pad}"


def get_nebula_splash(goal: str = None, verbose: bool = False) -> str:
    """
    Renders the signature Antigravity-styled Nebula CLI splash image/banner.
    """
    WIDTH = 78
    lines = []
    
    top = f"{DARK}╭{'─' * WIDTH}╮{RST}"
    bottom = f"{DARK}╰{'─' * WIDTH}╯{RST}"
    div = f"{DARK}├{'─' * WIDTH}┤{RST}"

    # Stylized Isometric ASCII Wordmark
    # Gradient: V1 -> V2 -> V3 -> C1 -> C2
    logo_raw = [
        ("   ███╗   ██╗███████╗", V1, "██████╗ ", V2, "██╗   ██╗", V3, "██╗     ", C1, "█████╗   ", C2),
        ("   ████╗  ██║██╔════╝", V1, "██╔══██╗", V2, "██║   ██║", V3, "██║     ", C1, "██╔══██╗ ", C2),
        ("   ██╔██╗ ██║█████╗  ", V1, "██████╔╝", V2, "██║   ██║", V3, "██║     ", C1, "███████║ ", C2),
        ("   ██║╚██╗██║██╔══╝  ", V1, "██╔══██╗", V2, "██║   ██║", V3, "██║     ", C1, "██╔══██║ ", C2),
        ("   ██║ ╚████║███████╗", V1, "██████╔╝", V2, "╚██████╔╝", V3, "███████╗", C1, "██║  ██║ ", C2),
        ("   ╚═╝  ╚═══╝╚══════╝", DARK, "╚═════╝ ", DARK, " ╚═════╝ ", DARK, "╚══════╝", DARK, "╚═╝  ╚═╝ ", DARK),
    ]

    lines.append("")
    lines.append(top)
    
    # 1. Header pills & badges
    badge_line = (
        f"  {GOLD}✦{RST} {BOLD}{WHITE}NEBULA MODEL{RST} {DIM}×{RST} {BOLD}{C1}ORION OS{RST} "
        f"{DARK}│{RST} {BG_P}{V4} v2.0-nebula {RST} {BG_C}{C1} 5-Agent Fleet {RST} {DARK}│{RST} {C2}● Ready{RST}"
    )
    lines.append(f"{DARK}│{RST}{pad_line(badge_line, WIDTH)}{DARK}│{RST}")
    lines.append(div)

    # 2. Render ASCII Logo
    for segs in logo_raw:
        colored_seg = ""
        for i in range(0, len(segs), 2):
            text = segs[i]
            color = segs[i+1]
            colored_seg += f"{color}{text}{RST}"
        lines.append(f"{DARK}│{RST}{pad_line(colored_seg, WIDTH)}{DARK}│{RST}")

    # 3. Subtitle
    sub = f"    {DIM}Cognitive Autonomous Chrome Substrate & Win32 Automation Engine{RST}"
    lines.append(f"{DARK}│{RST}{pad_line(sub, WIDTH)}{DARK}│{RST}")
    lines.append(div)

    # 4. System Specs / Metadata
    r1 = f"  {V3}Model Layer{RST}   : {WHITE}Nebula Cognitive Planner & Intent Decomposer{RST}"
    r2 = f"  {C1}Substrate{RST}     : {WHITE}Orion Win32 Automation + Playwright CDP (6.0 FPS){RST}"
    r3a = f"  {GOLD}Agent Fleet{RST}   : {WHITE}Commander{RST} 🧠 [Plan] · {WHITE}Executor{RST} 🌐 [Browser Driver]"
    r3b = f"                {WHITE}Inspector{RST} 👁️ [Vision] · {WHITE}Critic{RST} ⚖️ [QA] · {WHITE}Narrator{RST} 🎙️ [Voice]"
    
    lines.append(f"{DARK}│{RST}{pad_line(r1, WIDTH)}{DARK}│{RST}")
    lines.append(f"{DARK}│{RST}{pad_line(r2, WIDTH)}{DARK}│{RST}")
    lines.append(f"{DARK}│{RST}{pad_line(r3a, WIDTH)}{DARK}│{RST}")
    lines.append(f"{DARK}│{RST}{pad_line(r3b, WIDTH)}{DARK}│{RST}")
    lines.append(div)

    # 5. Dynamic Section: Goal vs Help/Welcome
    if goal:
        mode_lbl = f"{GOLD}[Verbose Mode]{RST}" if verbose else f"{C2}[Autonomous Stream]{RST}"
        g_line = f"  {BOLD}{WHITE}Active Goal{RST}   : {C1}\"{goal}\"{RST} {mode_lbl}"
        lines.append(f"{DARK}│{RST}{pad_line(g_line, WIDTH)}{DARK}│{RST}")
    else:
        u1 = f"  {BOLD}{WHITE}Quick Usage{RST}   : {V3}nebula{RST} {C1}\"<natural language task>\"{RST}"
        u2 = f"                  {V3}nebula{RST} {V2}--verbose{RST} {C1}\"<natural language task>\"{RST}"
        u3 = f"  {GRAY}Primitives{RST}    : {C1}orion browse{RST} {DIM}<target>{RST}  {DARK}│{RST}  {C1}orion watch{RST}  {DARK}│{RST}  {C1}orion speak{RST}"
        lines.append(f"{DARK}│{RST}{pad_line(u1, WIDTH)}{DARK}│{RST}")
        lines.append(f"{DARK}│{RST}{pad_line(u2, WIDTH)}{DARK}│{RST}")
        lines.append(f"{DARK}│{RST}{pad_line(u3, WIDTH)}{DARK}│{RST}")

    lines.append(bottom)
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "help":
        print(get_nebula_splash(goal=" ".join(sys.argv[1:])))
    else:
        print(get_nebula_splash())
