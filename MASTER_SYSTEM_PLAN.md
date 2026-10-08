# 🌌 Orion × Nebula × AutoGen: Complete Master Architecture Plan
## Universal Substrate for Web (Nebula), 3D (Blender), and Desktop Automation

## 1. System Vision & Tripartite Role Separation

The system divides all responsibilities into three distinct, specialized tiers, where **Orion** serves as the universal OS substrate powering multiple specialized models:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER INPUT & CLIENTS                            │
│           (PowerShell CLI · Interactive REPL · REST/WebSocket API)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Goal Ingestion
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            AUTOGEN MULTI-AGENT COGNITIVE SOCIETY (The Brain)            │
│  - 8-stage input normalization, typo repair, intent resolution         │
│  - High-level multi-step plan decomposition (Typed Steps)              │
│  - Reactive OODA Loop (Observe-Orient-Decide-Act, not static plans)    │
│  - Step Dispatcher: Routes Web ➔ Nebula, 3D ➔ Blender Model, OS ➔ Orion │
└───────────────┬────────────────────────┬───────────────────────────────┘
                │                        │
       [Web Tasks]                       │ [3D / Modeling Tasks]
                ▼                        ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│     NEBULA MODEL             │  │     BLENDER MODEL (Future)   │
│   (Chrome & Web Engine)      │  │   (3D Ops, bpy, Viewports)   │
└───────────────┬──────────────┘  └──────────────┬───────────────┘
                │                                │
                └────────────────┬───────────────┘
                                 │ Direct Hardware / OS Calls
                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ORION UNIVERSAL DESKTOP SUBSTRATE                    │
│  - Win32 Hardware `SendInput` Typing (Cadence & Chords: Shift+A, F12)  │
│  - Cubic Bezier Mouse Trajectories & 3D Viewport Orbit/Pan Drag        │
│  - App Adapter Layer: [ChromeAdapter] [BlenderAdapter] [WinAdapter]    │
│  - Window Focus & Enum (SetForegroundWindow, AttachThreadInput)        │
│  - Native Process Launcher (chrome.exe, blender.exe, notepad.exe)      │
│  - Desktop GDI Visual Screen Capture & Viewport Cropping               │
└────────────────────────────────┬───────────────────────────────────────┘

                    │                                    │
                    └──────────────────┬─────────────────┘
                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│               CONTINUOUS SCREEN WATCHER (Perception Engine)            │
│  - Sub-10ms perceptual hash diffing (`pHash`) pre/post action          │
│  - Dead-click & stall detector (diff < 0.5% after 1.5s = frozen)       │
│  - Crash detector (Chrome "Aw, Snap!", HTTP 404/500, OS "#32770" box)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Obstacle / Anomaly Detected
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│           GEMINI MULTIMODAL VISION INTELLIGENCE (Cloud "Eyes")         │
│  - 0-Token Local Gating: Only called when local watcher is stuck       │
│  - Inspects cropped screenshot & detects obstacle type (e.g. cookie)   │
│  - Returns structured remediation: {"action": "click", "coord": [x,y]} │
│  - Strict Privacy Guard: Password inputs & credit cards NEVER sent     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Live Telemetry Stream
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   REAL-TIME LIVE HEADS-UP DISPLAY (HUD)                │
│  - Desktop Floating Glassmorphic Pill (Always-on-top, non-focus-steal) │
│  - Terminal Live ANSI Status Bar (Unbuffered, zero-flicker)            │
│  - WebSocket Telemetry Stream (Broadcasts live milestones to web UI)   │
│  - Shows: Active Agent, Current Step, Health (🟢/🟡/🔴), Live Reason   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Comprehensive Inventory of Project Files & Their Roles

### A. Existing Project Files to Reuse & Enhance

| File Path | Current Status | Assigned Role in Master Architecture |
|---|---|---|
| [`orion_autogen.py`](file:///c:/skill/orion_autogen.py) | Active 5-Agent CLI | The Multi-Agent Cognitive Orchestrator. Coordinates Commander, Desktop Executor, Chrome Executor, Watcher, Narrator, and Critic. |
| [`desktop_controller.py`](file:///c:/skill/desktop_controller.py) | Active OS CLI | Orion's unified entry point. Exposes native Win32 primitives (`type`, `click`, `launch`, `focus`) alongside fast-path browser launch. |
| [`session.py`](file:///c:/skill/session.py) | Active Session Owner | Persistent Nebula Chrome browser session owner. Retains Playwright instance across sequential tasks on dedicated thread. |
| [`schemas.py`](file:///c:/skill/schemas.py) | Active Typed Schemas | Strictly typed schemas (`Plan`, `Step`, `ActionType`). Extended with desktop actions (`DESKTOP_TYPE`, `DESKTOP_CLICK`, `LAUNCH_APP`). |
| [`input_pipeline.py`](file:///c:/skill/input_pipeline.py) | Active Pipeline | 8-stage input understanding (phonetic typo repair, conversational reference resolution, confidence gating). |
| [`media_control.py`](file:///c:/skill/media_control.py) | Active Media Controller | Instant state-aware DOM shortcuts (`pause`, `resume`, `volume`, `mute`, `skip ad`) bypassing LLM latency. |
| [`nebula_brain.py`](file:///c:/skill/nebula_brain.py) | Active Brain Planner | Hybrid planner (0ms local regex parser + LLM escalation). Generates step sequences with explicit desktop vs web targets. |
| [`control_channel.py`](file:///c:/skill/control_channel.py) | Active Local Socket | Local 127.0.0.1 token-authenticated IPC socket for inter-process communication. |
| [`verify/page_watcher.py`](file:///c:/skill/verify/page_watcher.py) | Active Page Verifier | DOM error checks, HTTP 404/500 patterns, and baseline pHash visual diff calculation. |
| [`web_engine/`](file:///c:/skill/web_engine) | Active Browser Engine | Hardened Playwright engine with anti-bot stealth scripts and automated cookie consent dismissal. |
| [`resolvers/youtube.py`](file:///c:/skill/resolvers/youtube.py) | Active Media Resolver | Media search relevance scoring and candidate ranking. |
| [`tools/agent_society.py`](file:///c:/skill/tools/agent_society.py) | Active Tool Registry | Enforces per-role tool allow-lists, emergency kill switches, and per-command/session step budgets. |

---

### B. New Files to Create

| File Path | Component | Purpose |
|---|---|---|
| `orion_desktop/keyboard_mouse.py` | Orion Desktop | Win32 `SendInput` hardware typing, virtual key codes, modifier chords, and cubic Bezier mouse trajectories. |
| `orion_desktop/window_manager.py` | Orion Desktop | Windows enumeration (`EnumWindows`), window rects, positioning, and safe foreground focus acquisition (`AttachThreadInput`). |
| `orion_desktop/process_manager.py` | Orion Desktop | Native Windows application launcher (Notepad, Terminal, Explorer) and PID watchdog. |
| `orion_desktop/screen_capture.py` | Orion Desktop | High-speed GDI/Pillow desktop screenshot capture with multi-monitor bounding box resolution. |
| `orion_desktop/error_dialog_detector.py` | Orion Desktop | Detects native Windows system dialogs (`#32770`) indicating error boxes, crash alerts, or file prompts. |
| `web_engine/human_interactions.py` | Nebula Web | Gaussian distributed keystroke timing ($55\text{ ms} \pm 18\text{ ms}$), smooth wheel scrolling with deceleration, date-picker ISO injection. |
| `web_engine/auth_manager.py` | Nebula Web | Persistent Chrome user data directory management (`profiles/nebula_user`), 2FA/SSO login-wall detection, and human handover pause. |
| `web_engine/checkout_guard.py` | Nebula Web | Financial safety barrier: auto-detects credit card forms, Stripe/PayPal frames, and UPI QR codes, hard-stopping before payment submission. |
| `verify/screen_watcher.py` | Screen Watcher | Adaptive 2–6 FPS perception loop measuring pre/post-action visual deltas and flagging dead clicks ($\Delta < 0.5\%$). |
| `verify/gemini_vision.py` | Vision Intelligence | Gemini Multimodal Vision API client. Analyzes cropped obstacle screenshots and returns structured click coordinates `(x, y)` to clear barriers. |
| `hud/desktop_hud.py` | Live HUD | Floating, semi-transparent glassmorphic pill on Windows (always-on-top, `WS_EX_NOACTIVATE` so it never steals keyboard focus). |
| `hud/terminal_hud.py` | Live HUD | Unbuffered real-time ANSI status bar for CLI users showing active agent, health pill, and live reasoning. |
| `dispatcher.py` | Hybrid Dispatcher | Evaluates each step in the AutoGen plan and routes it cleanly to Orion (Desktop) or Nebula (Chrome). |
| `api_server.py` | Unified Gateway | FastAPI REST & WebSocket server (`POST /api/v1/task`, `GET /status`, `WS /stream`, `/desktop/execute`, `/nebula/execute`). |

---

## 3. High-Stakes Task Handling: Logins, Bookings & Safety

1. **Authentication & Logins (3-Tier Strategy)**:
   * **Tier 1 (Persistent Profile)**: Chrome runs from `profiles/nebula_user`. Log in once; cookies and tokens stay saved permanently across reboots.
   * **Tier 2 (2FA / SSO Handover)**: On OTP/SMS prompts, Nebula halts execution, announces via Studio Narrator: *"Authentication required. Please verify on your screen"*, and resumes automatically upon navigation to the authenticated app.
   * **Tier 3 (Vault)**: Plaintext passwords are never passed to the LLM.
2. **Ticket Bookings (Calendar Pickers & Seat Maps)**:
   * **Airport Dropdowns**: Types with humanized delay (60ms), pauses for async flyout selector, and uses `ArrowDown` + `Enter`.
   * **Date Pickers**: Dispatches native DOM events directly to hidden/underlying ISO date inputs (`YYYY-MM-DD`), bypassing multi-month calendar clicks.
   * **Seat Maps**: SVGs are selected via DOM attributes (`[data-seat="12B"]`); HTML5 Canvas maps default to a co-pilot prompt asking the user to click seats.
3. **Checkout Guard (Zero Autonomous Payment Policy)**:
   * **Hard Payment Stop**: The instant a payment screen (credit card inputs, UPI QR codes, Stripe iframes) is detected, automation halts immediately.
   * Takes an evidence screenshot, prints the final price and summary to the HUD/terminal, and transfers control to the human. The AI never submits payments.

---

## 4. Implementation Phasing Matrix

| Phase | Milestone | Primary Deliverables | Verification Strategy |
|:---:|---|---|---|
| **Phase 1** | Orion Native Desktop Substrate | `orion_desktop/` (`keyboard_mouse.py`, `window_manager.py`, `process_manager.py`, `screen_capture.py`) | Unit tests with mocked Win32 ctypes |
| **Phase 2** | Nebula Human-Grade Chrome Capabilities | `web_engine/` (`human_interactions.py`, `auth_manager.py`, `checkout_guard.py`) | Mocked payment DOM fixtures & typing tests |
| **Phase 3** | Continuous Screen Watcher & Freeze Detector | `verify/screen_watcher.py` | Dead-click & stall detection on local HTML fixture |
| **Phase 4** | Gemini Multimodal Vision Intelligence | `verify/gemini_vision.py` | Mocked vision response with coordinate remediation |
| **Phase 5** | Multi-Channel Live HUD Overlay | `hud/desktop_hud.py` & `hud/terminal_hud.py` | Thread-safe updates without focus stealing |
| **Phase 6** | AutoGen Reactive Dispatcher & Hybrid Society | `dispatcher.py` & `orion_autogen.py` | End-to-end hybrid goal execution (Desktop + Web) |
| **Phase 7** | Unified FastAPI & WebSocket Server | `api_server.py` | FastAPI `TestClient` REST & WebSocket streaming tests |
| **Phase 8** | Full Regression Suite & Documentation | Full regression run (305+ tests pass with 0 errors) | Pytest complete pass & `README.md` updates |
