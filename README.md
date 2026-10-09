<p align="center">
  <img src="assets/orion_banner.jpg" alt="Orion System × Nebula Model Banner" width="100%" />
</p>

# 🌌 Orion System × Nebula Model (v2.0)
### Universal Desktop Automation Substrate, Autonomous Web Engine & 3D Creative Society

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)
[![Tests: 298 passing](https://img.shields.io/badge/tests-298%20passing-brightgreen.svg)](#-testing)

---

## 📖 Overview

**Orion System × Nebula Model** is a hybrid autonomous desktop automation framework designed for Windows. It couples a low-level, high-speed OS substrate (**Orion**) with a collaborative multi-agent reasoning layer (**Nebula**).

* **Orion (The Operating System Layer)**: Manages low-level Win32 window processes, native Google Chrome execution, continuous visual perception, and system-level self-healing.
* **Nebula (The Cognitive Model Layer)**: A 5-agent society that decomposes natural language goals, plans execution steps, controls hardened Playwright browser sessions, and performs closed-loop visual/DOM verification.

---

## 🏛️ System Architecture

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      NEBULA (The Cognitive Model)                      │
 │    Commander Nebula │ Chrome Executor │ Perception Inspector           │
 │               Studio Narrator │ Verifier Critic                        │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Intent & Milestone Dispatch
 ┌───────────────────────────────────▼────────────────────────────────────┐
 │                       ORION (The Operating System)                     │
 │  Win32 Automation │ Chrome Driver │ Continuous Perception (6 FPS)      │
 │  Self-Healing Watchdog │ Studio Audio I/O (OneCore SAPI)               │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 How It Works

Every user task flows through a closed-loop 5-stage pipeline:

```
User Command (Text or Voice)
        │
        ▼
┌─────────────────────────────────────────────┐
│  1. INPUT UNDERSTANDING                     │
│  Normalize text → Fix phonetic typos        │
│  → Resolve conversational context           │
│  → Confidence gate (auto-run / clarify)     │
│  └─────────────────────┬───────────────────────┘
                      │ Typed Plan (Intent + Steps)
                      ▼
┌─────────────────────────────────────────────┐
│  2. REASONING & PLANNING (Commander Nebula) │
│  Gemini AI decomposition → validated schema │
│  Built-in deterministic local fallback      │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  3. EXECUTION (Chrome Executor)             │
│  Playwright browser automation              │
│  Domain allow-lists & action guards         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  4. VERIFICATION (Perception Inspector)     │
│  DOM error / modal / login-wall detection   │
│  Perceptual visual hash (pHash) diff        │
│  Self-heals on failure or uncertain verdict │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│  5. FEEDBACK & AUDIT (Studio Narrator)      │
│  Text-to-speech announcement                │
│  Structured JSON audit log + metrics        │
└─────────────────────────────────────────────┘
```

---

## ⚡ Key Capabilities

* **5-Agent Society**: Specialized roles for planning, execution, inspection, narration, and verification.
* **Persistent Interactive Session Mode**: A single persistent Playwright browser instance stays open across sequential tasks. No browser teardown between commands.
* **Closed-Loop Verification**: Perceptual visual diffing and DOM signal inspection verify that actions took effect and automatically trigger self-healing if a stall, error, or modal occurs.
* **State-Aware Media Player Controls**: Instant local media shortcuts (`pause`, `resume`, `next`, `volume`, `mute`, `skip ad`) executed directly against the active page without invoking an LLM.
* **Hardened Browser Engine**: Anti-bot stealth (`navigator.webdriver` set to false), automated cookie consent dismissal (OneTrust, Cookiebot), and isolated worker thread execution.
* **Input Pipeline**: Robust natural language processing with phonetic typo correction, bilingual support, conversational reference resolution, and confidence gating.
* **Security Guardrails & Budgeting**: Domain allow-lists, per-command and per-session step/cost budgets, non-TTY execution guards, and sensitive action approval gates.
* **Zero-Distraction / Zero-Key Fallback**: Runs reliably out of the box with deterministic local parsing even without external API keys.

---

## 📦 Installation & Setup

### Prerequisites
* **OS**: Windows 10 or Windows 11
* **Python**: 3.10 or higher
* **Google Chrome**: Installed and available in PATH or default Windows installation path

### Setup Steps

```powershell
# 1. Clone repository
git clone https://github.com/nividharan/Orion--V2.0-Nebula.git
cd Orion--V2.0-Nebula

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser binaries
python -m playwright install chromium

# 5. (Optional) Set Gemini API Key for AI planning
# If omitted, Orion automatically uses the built-in deterministic local parser
$env:GEMINI_API_KEY="your-gemini-api-key"
```

---

## 🚀 Quick Start

Minimal commands to verify and run the system:

```powershell
# 1. System Diagnostics & Health Check
python orion_autogen.py doctor

# 2. Start Interactive Session (persistent browser stays open)
.\nebula.bat

# 3. Autonomous Task Execution with Session Entry
python orion_autogen.py "play lofi beats on youtube"

# 4. Single-Command Mode (runs and exits, closing browser)
python orion_autogen.py "open github.com" --once

# 5. IPC Send to Existing Active Session (from another terminal)
python orion_autogen.py --send "pause"
```

---

## 💬 Interactive Mode

Nebula includes a persistent **Interactive Session Mode** where a single Python process owns one persistent Playwright Chrome browser. The user types commands consecutively at the `nebula> ` prompt while Chrome remains open and under live automation control the entire time.

### Starting Interactive Mode

```powershell
# Start directly into the REPL:
.\nebula.bat

# Or run an initial goal and stay in the REPL (Chrome remains open):
.\nebula.bat "play synthwave on youtube"

# Execute a single command and exit immediately (closes Chrome):
.\nebula.bat "open github.com" --once
```

### PowerShell Profile Snippet

To run `nebula` from any PowerShell terminal without typing the full directory path, add this one-line function to your PowerShell profile (`notepad $PROFILE`):

```powershell
function nebula { & "C:\skill\nebula.bat" @args }
```
*(Replace `C:\skill` with the absolute path to your cloned repository root).*

### Built-in Interactive Commands

Built-in commands execute immediately in-process without LLM calls:

| Command | Description |
|---|---|
| `help` | Display interactive commands, shortcuts, and active hotkeys |
| `status` | Print session status, active URL, page title, and budget usage |
| `history` | List recent natural-language commands and agent plans |
| `clear` | Clear the terminal display |
| `pause` | Pause active HTML5 / YouTube video player |
| `play` / `resume` | Resume playback on active media player |
| `next` | Skip to the next video or track |
| `volume <0-100>` | Adjust media volume level (e.g. `volume 50`) |
| `mute` / `unmute` | Toggle media audio mute |
| `skip ad` | Inspect DOM and skip active YouTube advertisement |
| `tabs` | List open browser tabs and indices |
| `newtab [url]` | Open a new tab (optional initial URL) |
| `switch <idx>` | Switch active automation focus to tab index |
| `closetab [idx]` | Close tab index (or active tab if omitted) |
| `exit` / `quit` / `close` | Gracefully close Chrome, clear lockfiles, and terminate session |

### Human Approvals & Guardrails
- **Sensitive Action Interception**: Operations targeting destructive inputs, downloads, external script navigations, or credential forms prompt for explicit user confirmation (`Proceed? [y/N]`).
- **Timeout & Default Deny**: If unprompted after 30 seconds, sensitive steps automatically abort to prevent unattended hazards.
- **Interrupts**: Pressing `Ctrl+C` during plan execution cancels the running command immediately via kill-switch and returns control to `nebula> ` without closing the browser.
- **Budgeting**: Session limits (default: 50 steps / $2.00 cost) and per-command limits (default: 15 steps / $0.50 cost) prevent runaway execution loops.

### External Control Channel (IPC)
When a `nebula` interactive session is running, it exposes a local-only `127.0.0.1` TCP socket authenticated with a cryptographic token stored in `.cache/nebula_session.json`. You can send commands to the active session from any secondary terminal:

```powershell
python orion_autogen.py --send "pause"
python orion_autogen.py --send "volume 30"
```

### Troubleshooting
- **Browser Disconnected / Crashed**: If Chrome is closed manually by the user, `NebulaSession` detects disconnection on the next command and automatically provisions a fresh browser instance.
- **Non-TTY Input**: When piped commands are fed into `nebula` via CI or redirected input (`echo "status" | python orion_autogen.py`), the REPL executes piped lines sequentially and exits cleanly upon EOF without freezing.

---

## 📁 Project Structure

```
Orion--V2.0-Nebula/
├── orion_autogen.py          # Main 5-agent society entry point & CLI
├── nebula.bat                # Windows interactive session launcher
├── api_server.py            # FastAPI REST & WebSocket Telemetry Gateway
├── run_app.py               # Standalone Native Desktop Application Launcher
├── app.bat                  # One-click Windows application starter
├── galaxy.py                # Galaxy Model: Human-Level 3D Agent for Blender GUI
├── generate_master_3d_logo.py # Blender 5.2 master 3D logo generator
├── web_ui/                  # Autonomous Glassmorphic Deck with 3D Three.js viewer
│   ├── index.html           # Real-time HUD, 3D viewport, perception buffer, ARIA tree
│   └── orion_logo.glb       # Blender EEVEE-rendered real-time 3D model
├── orion_desktop/           # Universal OS Substrate (Win32 Keyboard, Bezier Mouse, Watchdog)
├── session.py               # Deterministic persistent NebulaSession owner
├── repl.py                  # Interactive REPL console (5-turn memory, approvals, built-ins)
├── media_control.py         # State-aware media player controls & consent modal handler
├── control_channel.py       # Local 127.0.0.1 token-authenticated IPC control server
├── desktop_controller.py    # Orion system layer CLI & smart element interactions
├── orion_autogen.py         # Multi-Agent Society Router (Nebula Web + Galaxy 3D)
├── schemas.py               # Typed Plan, Step, ActionType, IntentType, smart click/fill
├── input_pipeline.py        # 8-stage input understanding & confidence gating
├── config.py                 # Paths, atomic writes, cache management, safety guards
├── observability.py          # Structured JSON logging, audit metrics, regression runner
│
├── web_engine/              # Hardened Playwright engine (stealth, consent, locators)
├── verify/                  # Screen Watcher, Freeze Detector, Visual diff verification
├── resolvers/               # Media search resolver with relevance scoring & caching
├── tools/                   # Agent tools and SocietyCoordinator
├── tests/                   # Complete regression test suite (14 modules, 298 tests)
└── assets/                  # 3D assets and original master artwork
```

---

## 🧪 Testing & Verification

The repository includes a comprehensive regression test suite covering all agent society components, browser controllers, schemas, input normalization, media controls, and the interactive session mode:

```powershell
# Run the full test suite
python -m pytest

# Run with verbose output
python -m pytest -v

# Run the interactive session test suite specifically
python -m pytest tests/test_interactive_session.py -v
```

All **305 tests** pass with zero critical errors.

### Implementation & Verification Matrix

| Scope Item | Description | Files Changed / Added | Test Verification | Status |
|---|---|---|---|:---:|
| **Item 1** | Entry points, CLI flags (`--once`), deprecated `--detach`, and `nebula.bat` | `nebula.bat`, `orion_autogen.py`, `desktop_controller.py` | `tests/test_interactive_session.py::test_entry_points_once_and_interactive` | **PASS** |
| **Item 2** | Persistent `NebulaSession` owner, health checks, auto-reconnect, and thread safety | `session.py` | `tests/test_interactive_session.py::test_session_owner_lifecycle_and_health` | **PASS** |
| **Item 3** | Interactive REPL console, 5-turn context memory, approvals, and built-ins | `repl.py` | `tests/test_interactive_session.py::test_repl_builtins_and_context` | **PASS** |
| **Item 4** | State-aware media controls (`pause`, `play`, `volume`, `mute`, `skip ad`) & watcher | `media_control.py`, `repl.py` | `tests/test_interactive_session.py::test_media_controls_and_watcher` | **PASS** |
| **Item 5** | Safety guardrails, domain allow-list, budgets, and non-TTY execution | `session.py`, `schemas.py`, `repl.py` | `tests/test_interactive_session.py::test_safety_budgets_and_nontty` | **PASS** |
| **Item 6** | Local 127.0.0.1 token-authenticated control channel and `--send` CLI | `control_channel.py`, `orion_autogen.py` | `tests/test_interactive_session.py::test_control_channel_send` | **PASS** |
| **Item 7** | Offline test suite covering 12 interactive session scenarios | `tests/test_interactive_session.py`, `web_engine/tests/fixture_server.py` | `pytest tests/test_interactive_session.py` (12 scenarios) | **PASS** |
| **Item 8** | Documentation, PowerShell profile snippet, limitations, and verification matrix | `README.md` | Full regression suite (`pytest`: 305 passed) | **PASS** |

### Known Limitations

1. **Live YouTube Player DOM Variations**: Offline tests execute against a deterministic local fixture server mimicking standard HTML5 / YouTube video player elements. In production, YouTube regularly modifies player DOM classes, button labels, and sponsor banner structures. Some novel ad formats (e.g. non-skippable countdown overlays) may require updated selector chains.
2. **Network & Regional Consent**: Live web automation requires an active internet connection. Visiting Google or YouTube for the first time in an unauthenticated profile may present jurisdiction-specific cookie or terms banners.
3. **Windows Native Features**: Win32 window focus primitives and OneCore SAPI voice synthesis are designed specifically for Windows 10/11 environments; core browser automation runs cross-platform via Playwright.

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

