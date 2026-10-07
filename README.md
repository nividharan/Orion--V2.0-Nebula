<p align="center">
  <img src="assets/orion_banner.jpg" alt="Orion System × Nebula Model Banner" width="100%" />
</p>

# 🌌 Orion System × Nebula Model (v2.0)
### High-Performance Desktop Automation Substrate & Cognitive Chrome Agent Society

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)

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

* **Chrome-Specialized Operations**: Built specifically for Google Chrome browsing, portal searching, tab controls, address bar navigation, in-page typing, scrolling, and verification.
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

---

## 🚀 Quick Start

### 1. Run the Nebula Cognitive Model (Natural Language Chrome Goals)
Use the `nebula` CLI to run natural language tasks directly through the 5-agent society:

```powershell
# Search Google Play Store directly
nebula "open google play and search for free fire"

# Search YouTube for music or tutorials
nebula "open youtube and search for lofi beats"

# Search GitHub repositories
nebula "search github for autogen"

# Tab and page controls
nebula "open new tab and go to wikipedia.org"
nebula "scroll down in chrome and take screenshot"
nebula "close tab and announce done"
```

### 2. Run the Orion System Layer (Fast Primitives)
Use the `orion` CLI for direct system operations:

```powershell
# Direct Web Navigation (<50ms)
orion browse "play store free fire"              # Resolves to Google Play search
orion browse "youtube lofi hip hop"              # Resolves to YouTube search
orion browse "https://github.com"                # Direct URL launch in Chrome

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

## 🌐 Local Perception Server (Port 8765)

Start the lightweight background server for real-time web dashboard streaming:

```powershell
orion api
```
Open **`http://localhost:8765/`** in your browser to inspect live screen streaming, frame settlement, and workstation telemetry.

---

## 📦 Installation & Setup

```powershell
# Clone the repository
git clone https://github.com/nividharan/Orion--V2.0-Nebula.git
cd Orion--V2.0-Nebula

# Install dependencies
pip install -r requirements.txt

# Add to user PATH (Optional)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$PWD", "User")
```

---

## 📜 License

Distributed under the **MIT License**.
