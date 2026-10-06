---
name: voice-desktop-automation
description: Autonomous hands-free desktop GUI, CLI, and engine automation across ALL installed Windows applications, local services, and network ports using Option D (Unified Hybrid System) - Pre-flight validation, universal application lifecycle management, socket port probing, continuous compiled batch execution, and milestone checkpointing.
---

# Voice & Desktop Autonomous Control Skill (Universal Multi-Tool Engine)

## Purpose
Delivers high-efficiency, hands-free desktop and service automation for Google Antigravity across **ALL tools and applications** on the system (browsers, office productivity, media/creative, engineering/CAD, developer IDEs, local AI/LLM servers, and 3D packages).
Eliminates stop-and-go model round-trip latency by enforcing **upfront requirement checks**, **universal window lifecycle guarantees**, **network/socket port health checks**, **continuous compiled batch execution**, and **milestone checkpointing**.

---

## Supported Tool Categories (Universal Scope)

The engine automatically discovers, launches, focuses, and controls all 209+ applications on Windows:

| Category | Example Target Tools | Interaction Routes |
| :--- | :--- | :--- |
| **Web Browsers** | Google Chrome, Microsoft Edge | GUI Automation (`deskctl batch`), CDP, Keyboard Shortcuts |
| **Productivity & Office** | Excel, Word, PowerPoint, OneNote, Notion, To Do | Batch Keystrokes, Hotkeys, Paste, Ribbon GUI Clicks |
| **Creative & Media** | Paint, Paint 3D, VLC Media Player, OBS Studio, CapCut, Clipchamp | GUI Clicks, Hotkeys, Media Control, OBS WebSocket (Port 4455) |
| **Engineering & CAD** | KiCad (PCB/Schematic), MATLAB, NI LabVIEW, Arduino IDE | Canvas Navigation, Menu Batch Clicks, CLI Automation |
| **Developer IDEs & Terminals**| Antigravity IDE, Visual Studio Code, Terminal, PowerShell, Git Bash | CLI (`run_command`), Direct Keystrokes, Hotkeys, File Edits |
| **Data & Local AI Servers** | Jupyter (8888), Streamlit (8501), Ollama (11434), LM Studio (1234) | Socket Probes (`deskctl port`), Browser GUI, REST/HTTP APIs |
| **3D & Creative Suites** | Blender (9876), 3D Viewer, ComfyUI (8188) | Direct Socket IPC / Python API + GUI Fallback |

---

## The 4-Stage Universal Execution Protocol

```
[Voice / User Request for ANY Tool]
              │
              ▼
Stage 1: Universal Pre-Flight Check
  - Run: deskctl preflight <app1> <app2:port> <port>
  - Validates:
      1. Is application installed on Windows? (Catalog of 209 apps)
      2. Is process running?
      3. Is visible window rendered on the live desktop?
      4. Is required socket port listening? (e.g. 8888, 11434, 9876, 5173)
              │
              ▼
Stage 2: Live Screen Window & Service Activation
  - If app window is missing or running as headless zombie:
      Execute: deskctl open <app> (e.g. deskctl open vlc / deskctl open excel / deskctl open obs)
  - Engine automatically:
      * Terminates hung windowless background instances
      * Launches application via shell:AppsFolder
      * Polls until visible HWND exists
      * Restores/Unminimizes and foregrounds window onto live screen
              │
              ▼
Stage 3: Strategy Routing & Continuous Machine-Speed Execution
  ┌─────────────────────────────────┴─────────────────────────────────┐
  ▼                                                                   ▼
[Route A: Direct Socket / API / IPC]               [Route B: Continuous Compiled Batch]
(For tools with active ports/APIs:                  (For GUI interactions across any tool:
 Jupyter, Ollama, Blender bpy, OBS WS, etc.)         Compile all actions into JSON array
 Run direct payload via socket / REST / CLI           and run uninterrupted at machine speed)
  │                                                                   │
  └─────────────────────────────────┬─────────────────────────────────┘
                                    ▼
Stage 4: Milestone Checkpoint & Reporting
  - Screen snapshot captured strictly to: .cache/screen_live.png
  - Visual verification of final state
  - Optional Windows SAPI spoken voice summary: deskctl speak "<msg>"
```

---

## Core Operational Rules

1. **Mandatory Universal Application Verification**:
   - Before interacting with ANY application, verify that it is physically open and visible on screen (`window_visible == true`).
   - If closed or hidden, call `deskctl open <app>` (supports fuzzy names, e.g. `chrome`, `vlc`, `excel`, `word`, `obs`, `paint`, `matlab`, `kicad`, `notion`, `blender`).
   - NEVER send blind clicks or keys if the window is not confirmed in the foreground.

2. **Mandatory Port & Socket Verification**:
   - For any tool that runs a local server, MCP socket, or web backend (Jupyter: 8888, Streamlit: 8501, Ollama: 11434, ComfyUI: 8188, Blender: 9876, Dev Server: 3000/5173, etc.):
     ALWAYS verify port readiness with `deskctl port <port>` before calling socket APIs.
   - If the port is closed, alert the user or start the backend daemon before issuing commands.

3. **Continuous Batch Compilation (No Micro-Step Round-Trips)**:
   - NEVER execute one keypress or click, pause for an AI turn, view a screenshot, and execute another.
   - Always calculate the complete step sequence and execute it in **one continuous batch** via `deskctl batch --file <steps.json>`.

4. **Fail-Safe Abort on Window Mismatch**:
   - If a target window cannot be brought to the foreground, the batch sequence immediately halts rather than misclicking background applications.

5. **Clean Workspace Rule**:
   - Never write loose `.png` files in the workspace root.
   - All live screen captures stream strictly to the rolling buffer: `c:\skill\.cache\screen_live.png`.

6. **Hardware Fail-Safe**:
   - PyAutoGUI fail-safe is always active. Moving the physical mouse to `(0, 0)` immediately halts execution.

---

## Universal CLI Reference (`desk` / `deskctl`)

| Function | Command | Description |
| :--- | :--- | :--- |
| **List Installed Apps** | `deskctl apps [filter]` | Searches all 209 installed Windows applications |
| **List Active Ports** | `deskctl ports` | Scans all listening TCP ports and owning processes in 0.05s |
| **Universal Pre-Flight**| `deskctl preflight <items...>` | Validates any combo of apps, ports, and tools (e.g. `chrome obs 8080`) |
| **Launch Any App** | `deskctl open <app>` | Cleans windowless zombies, opens GUI, brings to front |
| **Check Any Port** | `deskctl port <port>` | Tests TCP socket connectivity on `127.0.0.1` |
| **Continuous Batch Run**| `deskctl batch --file <steps.json>` | Executes full action sequence uninterrupted |
| **Live Screen Buffer** | `deskctl shot` | Captures screen to `.cache/screen_live.png` |
| **Window Listing** | `deskctl windows` | Lists all visible top-level windows with HWNDs |
| **Window Focus** | `deskctl focus "<title>"` | Restores and brings target window to front |
| **Verified Click** | `deskctl click --x <x> --y <y>` | Pixel-accurate click with DPI awareness |
| **Unicode Paste** | `deskctl paste "<string>"` | Instant clipboard paste |
| **Live Telemetry & Status** | `deskctl status` | Real-time JSON: active window, process, PID, mouse, motion delta |
| **Start Perception API** | `deskctl api [port]` | Launches HTTP/MJPEG live stream server (default port 8765) |
| **Autonomous Task Runner**| `deskctl task --file <task.json>` | Executes end-to-end task with expected output verification |
| **Voice Feedback (TTS)**| `deskctl speak "<msg>"` | Windows SAPI audio spoken response |

---

## Low-Latency Decision & Action API Reference (Port 8765)

For sub-second autonomous decision-making without LLM image round-trip bottlenecks:

| Method & Endpoint | Payload / Params | Latency | Purpose |
| :--- | :--- | :--- | :--- |
| `GET /quick_state` | None | **~6ms** | Micro-telemetry for instant heuristic state-machine decisions. |
| `GET /vlm_frame` | `?crop=window` (optional) | **~35ms** | Optimized 50KB JPEG frame for fast Multimodal AI inference (100× smaller than PNG). |
| `POST /action` | `{"action": "click|paste|focus|hotkey|..."}` | **~15ms** | In-process action execution (bypasses Python VM process spawn overhead). |
| `POST /batch` | `{"steps": [...]}` | **Machine speed** | In-process continuous sequence execution. |
| `POST /task` | `{"tool": "...", "steps": [...], "expected": {...}}` | **Closed-loop** | Full task execution with expected output validation. |
| `GET /status` | None | **~1ms** | Full JSON workstation telemetry and motion delta. |

---

## Batch Sequence Schema Examples (`steps.json`)

### Example 1: Web Browser Search & Navigation (Chrome / Edge)
```json
[
  {"action": "open", "app": "chrome"},
  {"action": "focus", "title": "Chrome"},
  {"action": "hotkey", "keys": ["ctrl", "t"]},
  {"action": "paste", "text": "https://github.com\n"},
  {"action": "wait", "seconds": 1.0},
  {"action": "checkpoint"}
]
```

### Example 2: Productivity Data Entry (Excel / Notepad / Word)
```json
[
  {"action": "open", "app": "excel"},
  {"action": "focus", "title": "Excel"},
  {"action": "wait", "seconds": 0.5},
  {"action": "paste", "text": "Revenue\tCost\tProfit\n1000\t600\t=A2-B2\n"},
  {"action": "checkpoint"}
]
```

### Example 3: Local AI & Data Science Server Verification
```json
[
  {"action": "port", "port": 8888, "require_open": true},
  {"action": "open", "app": "chrome"},
  {"action": "focus", "title": "Chrome"},
  {"action": "hotkey", "keys": ["ctrl", "l"]},
  {"action": "paste", "text": "http://localhost:8888\n"},
  {"action": "checkpoint"}
]
```

Supported actions in batch: `open`, `port`, `focus`, `click`, `double_click`, `right_click`, `move`, `hover`, `drag`, `scroll`, `paste`, `type`, `press`, `hotkey`, `wait`, `checkpoint`.
