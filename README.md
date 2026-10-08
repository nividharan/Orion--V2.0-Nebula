<p align="center">
  <img src="assets/orion_banner.jpg" alt="Orion System × Nebula Model Banner" width="100%" />
</p>

# 🌌 Orion System × Nebula Model (v2.0)
### High-Performance Desktop Automation Substrate & Cognitive Chrome Agent Society

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)
[![Tests: 293 passing](https://img.shields.io/badge/tests-293%20passing-brightgreen.svg)](#-phase-roadmap)
[![Phases: 8 complete](https://img.shields.io/badge/phases-8%20complete-blueviolet.svg)](#-phase-roadmap)

---

## 🏛️ System & Model Architecture

Orion v2.0 establishes a clean separation between the **OS System Layer** and the **Cognitive Model Layer**:

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

* **Orion (The System)**: The low-level operating system substrate. Controls Win32 window management, native Google Chrome execution (`--new-window`), continuous visual perception buffer (6.0 FPS rolling stream), autonomous self-healing modal dialog dismissal, and audio I/O.
* **Nebula (The Model)**: The cognitive intelligence and multi-agent reasoning layer. Specializes exclusively in natural language intent decomposition, web portal search routing, Chrome tab lifecycle management, and closed-loop visual verification. In future updates, next-generation reasoning models can slot directly into the Nebula layer while Orion remains the reliable OS controller.

---

## ⚡ Key Capabilities

* **Hardened Playwright Web Engine (`web_engine`)**: Auto-waiting locator chains (`locators/`), short-probe dynamic element resolution with `wait_for`, multi-step CMP cookie consent handlers (OneTrust / Cookiebot), anti-bot stealth evasions (`navigator.webdriver` strictly reports `false`), atomic state persistence, 7-day artifact auto-pruning, and startup Git exposure guards.
* **Dual-Engine Screen Perception**: Direct Chrome DevTools Protocol (CDP) in-memory framebuffer capture (100% immune to Windows GDI BitBlt access-denied restrictions) combined with hardened Win32 desktop capture.
* **Security Guardrails**: Action allow-lists, domain allow-lists, and accessible-name target guards that intercept sensitive actions (e.g., "Place order", "Delete account", payments) before execution.
* **Structured Data Extraction**: Clean JSON and CSV dataset exports with deduplication, currency normalization, and ISO timestamps.
* **Zero Distraction / Pure Execution**: Purged of irrelevant 3D routines to guarantee reliable execution of your exact browser commands.
* **5-Agent Collaborative Society**:
  1. `Commander Nebula` [🧠 Cognitive Planner & Chrome Intent Decomposer]
  2. `Chrome Executor` [🌐 Orion System Chrome & Desktop Driver]
  3. `Perception Inspector` [👁️ Live Screen Perception Stream & Verification]
  4. `Studio Narrator` [🎙️ Microsoft George HD Speech Engine]
  5. `Verifier Critic` [⚖️ Closed-Loop Evaluator & Self-Healing QA]
* **Continuous Visual Perception**: 6.0 FPS non-blocking rolling screen buffer tracking visual deltas, frame settlement, and foreground process registration.
* **Autonomous Self-Healing**: Actively detects and dismisses blocking Windows error dialogs, repairs lost window focus, and retries operations.
* **Sub-20ms In-Memory Fast Paths**: Instant query execution via local REST API (`http://127.0.0.1:8765`).
* **Structured Observability**: Per-step JSON audit logs with automatic secret redaction, latency/token metrics, and a single-call full regression runner across all 12 test modules.

---

## 🗺️ Phase Roadmap

| Phase | Title | Status | Tests |
|-------|-------|--------|-------|
| 0 | Safety, cleanup, atomic writes, cache tracking | ✅ Complete | 8 |
| 1 | Web-only Playwright facade, stealth, consent, guardrails | ✅ Complete | 27 |
| 2 | Media resolver — ad filtering, scoring, TTL, API fallback | ✅ Complete | 18 |
| 3–4 | Intent alias normalization, AI planning, retry/fallback | ✅ Complete | 38 |
| 5 | Input pipeline — bilingual cleaning, reference resolution | ✅ Complete | 100 |
| 6 | Page watcher — DOM error/modal/login detection, visual diff, 24h retention | ✅ Complete | 22 |
| 7 | Agent society — `web_verify_page` wired into `SocietyCoordinator` | ✅ Complete | 17 |
| 8 | Observability — structured JSON logging, secret redaction, regression audit | ✅ Complete | 4 + 293 |

> **Phase 8 exit criteria**: `run_regression_suite()` reports **0 critical errors** across all 293 tests spanning every phase.

---

## 📁 Project Structure

```
Orion--V2.0-Nebula/
├── orion_autogen.py          # Main 5-agent society entry point (nebula CLI)
├── desktop_controller.py     # Orion system layer CLI (orion / deskctl)
├── nebula_brain.py           # NebulaBrain — AI planning, local parser, pick_candidate
├── schemas.py                # Typed Plan/Step/ActionType/IntentType + validate_plan
├── input_pipeline.py         # 8-stage NL input pipeline (clean→understand→gate)
├── api_client.py             # YouTube Data API v3 + fallback scraper client
├── config.py                 # Paths, atomic_write, cache management, git guards
├── observability.py          # Structured JSON logging, audit metrics, regression runner
│
├── web_engine/               # Hardened Playwright engine (stealth, consent, locators)
├── verify/
│   ├── page_watcher.py       # DOM error/modal/login detection, perceptual visual diff
│   └── playback.py           # YouTube playback verify, heal, ad-skip, consent dismiss
├── resolvers/
│   └── youtube.py            # YouTube search resolver with scoring, TTL, caching
├── tools/
│   ├── typed_tools.py        # All agent tools (web_verify_page, media_*, web_*, desktop_*)
│   ├── agent_society.py      # SocietyCoordinator, AgentRole, AgentSafeguards
│   └── __init__.py           # Public tool + society exports
│
├── tests/                    # 12 test modules — 293 tests total
│   ├── test_phase0_safety.py
│   ├── test_schemas.py
│   ├── test_brain.py
│   ├── test_input_pipeline.py
│   ├── test_resolvers.py
│   ├── test_playback.py
│   ├── test_page_watcher.py
│   ├── test_api_client.py
│   ├── test_society.py
│   ├── test_observability.py
│   ├── test_banner.py
│   └── test_facade_characterization.py
│
├── legacy/                   # Archived desktop-only modules (disabled by default)
├── profiles/                 # Browser state persistence (cookies, localStorage)
├── .cache/                   # Artifact cache — auto-pruned at 7 days
└── logs/                     # Structured JSON audit logs per task
```

---

## 🚀 Quick Start

### 1. Run the Nebula Cognitive Model (Natural Language Chrome Goals)
Use `python orion_autogen.py` or the `nebula` CLI to run natural language tasks directly through the 5-agent society:

```powershell
# Direct Video / Media Playback (Resolves to top YouTube video with autoplay & active focus)
python orion_autogen.py "play kangal neeye on youtube"
python orion_autogen.py "chrome play song"
python orion_autogen.py "open chrome and play tamil songs in youtube"

# System & API Diagnostics (Check Zero-Key Status & Health)
python orion_autogen.py doctor

# Search Google Play Store directly
python orion_autogen.py "open google play and search for free fire"

# Search YouTube for music or tutorials
python orion_autogen.py "open youtube and search for lofi beats"

# Search GitHub repositories
python orion_autogen.py "search github for autogen"

# Tab and page controls
python orion_autogen.py "open new tab and go to wikipedia.org"
python orion_autogen.py "scroll down in chrome and take screenshot"
python orion_autogen.py "close tab and announce done"

# Verbose Multi-Agent Telemetry Mode
python orion_autogen.py --verbose "play believer on youtube"
```

### 2. Run the Orion System Layer (Fast Primitives)
Use `python desktop_controller.py` or the `orion` CLI for direct system operations:

```powershell
# Direct Media Playback (<800ms resolution directly to watch URL)
python desktop_controller.py browse "play kangal neeye on youtube"
python desktop_controller.py browse "chrome play song"

# System Diagnostics
python desktop_controller.py doctor

# Direct Web Navigation (<50ms)
python desktop_controller.py browse "play store free fire"              # Resolves to Google Play search
python desktop_controller.py browse "youtube lofi hip hop"              # Resolves to YouTube search
python desktop_controller.py browse "https://github.com"                # Direct URL launch in Chrome

# Dedicated Chrome-Native Controls
orion chrome new_tab "https://github.com"        # Open new tab to URL
orion chrome close_tab                           # Close active tab (Ctrl+W)
orion chrome reopen_tab                          # Restore closed tab (Ctrl+Shift+T)
orion chrome next_tab                            # Switch to next tab (Ctrl+Tab)
orion chrome prev_tab                            # Switch to previous tab
orion chrome reload                              # Refresh page (Ctrl+R)
orion chrome scroll_down                         # Smooth mouse scroll down
orion chrome scroll_up                           # Smooth mouse scroll up
orion chrome zoom_in                             # Zoom in (Ctrl++)
orion chrome zoom_out                            # Zoom out (Ctrl+-)
orion chrome fullscreen                          # Toggle fullscreen (F11)
orion chrome devtools                            # Toggle Developer Tools (F12)
orion chrome close                               # Gracefully close Chrome

# System Perception & Self-Healing
orion watch                                      # Live 6 FPS screen perception telemetry
orion heal                                       # Scan & auto-dismiss blocking error dialogs
orion shot                                       # Capture live screen buffer
orion status                                     # Full workstation status JSON

# Application & Window Control
orion open notepad                               # Launch application
orion focus chrome                               # Bring Chrome to foreground
orion close chrome                               # Gracefully terminate application
```

### 3. Run the Full Regression Suite
```powershell
# Run all 293 tests across all 12 modules
python -m pytest

# Run Phase 8 regression audit (all phases, single call)
python -c "from observability import run_regression_suite; r = run_regression_suite(verbose=True); print(r)"
```

---

## 🎙️ Studio Voice Engine (TTS & STT)

Orion features Microsoft OneCore SAPI text-to-speech with high-definition voices:

```powershell
orion speak "All systems operational, sir."      # Microsoft George (Executive HD)
orion speak "Task completed." -v Susan           # Microsoft Susan (British)
orion speak "Visual frame verified." -v Zira     # Microsoft Zira (American)
orion voices                                     # List installed voices

# Microphone Audio Transcription
orion listen 5                                   # Listen for 5s and transcribe speech
orion record 4                                   # Record 4s of audio to WAV
```

---

## 🧵 Async vs Sync Architecture & Thread Safety

Orion is engineered for complex agent environments (AutoGen, asyncio, multi-agent frameworks) where calling Playwright's sync API from inside an active event loop normally causes `Synchronous event loop error`.

To solve this:
* **Dedicated Worker Thread / Event Loop**: `BrowserManager.run_isolated(func, *args, **kwargs)` dispatches browser operations to a dedicated worker thread with its own independent lifecycle.
* **Thread-Safe Facade**: `BrowserManager` encapsulates Playwright in a thread-safe mutex wrapper, ensuring safe concurrent invocation across async agents and sync CLI runners.
* **CDP In-Memory Perception**: `take_screenshot()` captures directly from the active Chrome page via Chrome DevTools Protocol (CDP), avoiding GDI/Win32 restrictions.

---

## 📦 Installation & Setup

```powershell
# Clone the repository
git clone https://github.com/nividharan/Orion--V2.0-Nebula.git
cd Orion--V2.0-Nebula

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (first time only)
python -m playwright install chromium

# Add to user PATH (Optional)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$PWD", "User")
```

---

## 📋 Changelog

### v2.0 — Full Phase 0–8 Refactor (October 2026)

**Phase 8 — Observability & Hardening**
- `observability.py`: `StructuredLogger` (JSON-lines per step), `TaskAuditReporter` (success rate, latency, token spend, healed steps), automatic secret/key/token redaction
- `run_regression_suite()`: single-call runner across all 12 test modules — 293 tests, 0 critical errors
- **Bug fix**: `_normalize_tamil_query` guarded against English-prefixed commands to eliminate `"play play X"` double-word artefact

**Phase 7 — Agent Society Integration**
- `tools/typed_tools.py`: `web_verify_page()` tool wrapping `PageWatcher.verify_action_result()`
- `tools/agent_society.py`: `SocietyCoordinator` verifier now branches on intent — media → `media_verify_playback` + heal loop; all others → `web_verify_page`
- `tools/__init__.py`: `web_verify_page` exported to public surface

**Phase 6 — Page Watcher**
- `verify/page_watcher.py`: DOM-based error page detection, blocking modal/dialog detection, login-wall detection, perceptual visual diff (imagehash phash), frozen-frame detection, 24h log retention

**Phase 5 — Input Pipeline**
- `input_pipeline.py`: 8-stage pipeline (capture → clean → cancel → split → resolve → understand → validate → confidence gate)
- Bilingual Tamil/English normalization, phonetic typo correction (`tamol→tamil`), conversational reference resolution, 100-command eval suite

**Phase 3–4 — Intent Normalization & AI Brain**
- `nebula_brain.py`: AI planning with retry, local fallback parser, `pick_candidate` deterministic scoring
- Intent alias normalization: `media_play→media_playback`, `tab_operation→tab_management`

**Phase 2 — Media Resolver**
- `resolvers/youtube.py`: YouTube search with ad filtering, relevance scoring, TTL caching, API + scraper fallback

**Phase 1 — Web Engine Refactor**
- Scoped to web-only Playwright facade; removed desktop executor from hot path
- Anti-bot stealth, CMP consent handlers, atomic state persistence, Git exposure guards

**Phase 0 — Safety & Cleanup**
- Atomic writes, owner-only file permissions, cache tracking, `.gitignore` hardening

---

## 📜 License

Distributed under the **MIT License**.
