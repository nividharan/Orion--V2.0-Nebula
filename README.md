# 🌌 Orion v2.0 `"Nebula"`
### Universal Autonomous Desktop, Service & Perception Engine for Google Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)
[![Antigravity: Enabled](https://img.shields.io/badge/Antigravity-v1.3.0+-8A2BE2.svg)](https://github.com)
[![Latency: Sub--10ms](https://img.shields.io/badge/Reaction%20Time-%3C10ms-00C853.svg)](#low-latency-api-engine-port-8765)

---

## 🌟 Overview

**Orion v2.0 `"Nebula"`** is an enterprise-grade autonomous desktop GUI, CLI, and engine automation system engineered for **Google Antigravity (`agy`)**.

Built upon **Option D (The Unified Hybrid Architecture)**, Orion completely eliminates the slow, fragile "Stop-and-Go" vision loops of traditional automation. Instead of uploading 5MB screenshots after every click and waiting seconds for model round-trips, Orion operates as a **dual-layer cybernetic system**:
1. **The In-Memory Nervous System (Port `8765`):** Continuously tracks foreground windows, processes, and visual frame deltas in RAM with <1% CPU and executes actions in **6ms–15ms**.
2. **The 5-Stage Closed-Loop Protocol:** Guarantees that applications are physically rendered on screen, socket ports are connected, machine-speed batches execute uninterrupted, and **expected outputs are strictly verified** before completing.

Orion dynamically controls all **209+ software applications, local AI servers, and development tools** installed on Windows.

---

## 🚀 The 5-Stage Closed-Loop Protocol

```
[User Voice / Text Instruction]
              │
              ▼
Stage 1: Upfront Pre-Flight Validation (<0.18s)
  - Asserts application presence (catalog of 209 apps), process health, and socket ports.
              │
              ▼
Stage 2: Live Screen Window & Service Activation
  - Terminates headless zombie instances, launches via shell:AppsFolder,
    guarantees a physical HWND rendered on your live screen (WinSta0\Default).
              │
              ▼
Stage 3: Continuous Machine-Speed Execution (0.05s–0.15s/action)
  - Direct Engine IPC (if APIs/sockets exist) OR Continuous Compiled Batch GUI.
              │
              ▼
Stage 4: Milestone Checkpointing & Live Perception Streaming
  - Rolling screen frame saved strictly to: .cache/screen_live.png (Zero workspace clutter).
  - Live video and telemetry streamed to: http://localhost:8765/
              │
              ▼
Stage 5: Expected Output Validation Engine
  - Validates output files (existence, size, path).
  - Validates active window states & titles.
  - Validates socket port readiness & HTTP endpoints.
  - Validates visual motion delta (detects if animations/streams are active).
```

---

## ⚡ Low-Latency API Engine (Port 8765)

Orion runs a lightweight, persistent in-memory perception and execution server:

| Endpoint | Method | Latency | Description |
| :--- | :--- | :--- | :--- |
| **`/quick_state`** | `GET` | **~6ms** | Micro-telemetry (Active window, PID, mouse coords, motion delta) for instant decisions. |
| **`/vlm_frame`** | `GET` | **~35ms** | Optimized 50KB JPEG frame (100× smaller than PNG) for fast multimodal AI vision. |
| **`/action`** | `POST` | **~15ms** | Direct in-process execution (click, paste, type, press, focus, hotkey) with zero startup lag. |
| **`/batch`** | `POST` | Machine speed | Continuous compiled multi-step action sequence. |
| **`/task`** | `POST` | Closed loop | Full 5-stage task runner with output verification. |
| **`/status`** | `GET` | **~1ms** | Full workstation JSON telemetry and animation detection. |
| **`/stream`** | `GET` | Real-time | Live MJPEG video stream accessible from any web browser. |
| **`/`** | `GET` | Real-time | Interactive Web Dashboard with live preview and status cards. |

---

## 🛠️ CLI Reference: `orion` (also `deskctl` / `desk`)

Orion entrypoints are globally deployed to PATH:

```powershell
# 1. Instant Status & Perception (In-Memory Fast Path)
orion quick                               # Instant 6ms micro-telemetry JSON
orion status                              # Full workstation telemetry and motion delta
orion shot                                # Ultra-fast screen capture to .cache/screen_live.png

# 2. Window & Application Lifecycle
orion open vlc                            # Launches GUI window, clears zombies, restores to front
orion focus Chrome                        # Instantly brings window to foreground (<50ms)
orion windows                             # List all active top-level windows with HWNDs

# 3. Universal Discovery
orion apps kicad                          # Search across 209 installed Windows applications
orion ports                               # Netstat scan of all listening TCP ports in 0.05s
orion port 8888                           # Test TCP socket connectivity

# 4. Closed-Loop Autonomous Task Runner
orion task --file task.json               # Execute 5-stage task with expected output validation

# 5. Natural Language AI Agent Delegation (Antigravity CLI)
orion "open excel and create a monthly expense table"
orion "open blender and animate a rotating gold cube"
```

---

## 🌐 Universal Tool Matrix

Orion is completely application-agnostic:

* **Web Browsers:** Google Chrome, Microsoft Edge
* **Productivity & Office:** Excel, Word, PowerPoint, OneNote, Outlook, Access, Notion, To Do
* **Creative & Media:** Paint, Paint 3D, VLC Media Player, OBS Studio, CapCut, Clipchamp
* **Engineering & CAD:** KiCad 10.0 (PCB & Schematic), MATLAB R2026a, NI LabVIEW 2026 Q3, Arduino IDE
* **Developer IDEs:** Antigravity IDE, Visual Studio Code, Terminal, PowerShell, Git Bash
* **Data Science & AI:** Jupyter (8888), Streamlit (8501), Ollama (11434), LM Studio (1234)
* **3D & Modeling:** Blender 5.2.2 (9876), ComfyUI (8188)

---

## 📁 Repository Structure

```
c:\skill\
├── desktop_controller.py      # Core Orion in-memory controller & API server (Port 8765)
├── orion.ps1 / orion.cmd      # Official Orion CLI entrypoint wrappers
├── deskctl.ps1 / deskctl.cmd  # Power-user CLI aliases
├── desk.cmd                   # Legacy CMD wrapper
├── Project_Definition.txt     # Architecture & system specifications
├── README.md                  # System documentation & usage guide
├── .gitignore                 # Workspace hygiene (excludes cache & loose screenshots)
├── .cache/                    # Ephemeral runtime buffer (screen_live.png, catalogs)
└── .gemini/skills/
    └── voice-desktop-automation/
        └── SKILL.md           # Antigravity skill specification
```

---

## 📜 License

Distributed under the **MIT License**. Created with precision for **Google Antigravity**.
