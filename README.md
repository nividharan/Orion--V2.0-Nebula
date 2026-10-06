<p align="center">
  <img src="assets/orion_banner.jpg" alt="Orion v2.0 Nebula Banner" width="100%" />
</p>

# 🌌 Orion v2.0 "Nebula"
### Fast Desktop Automation & Screen Perception System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)

---

## 🌟 What is Orion?

**Orion v2.0 "Nebula"** is a smart desktop automation assistant for Windows. It lets you control applications, browse the web, speak with professional studio voices, and track your screen activity using simple commands or voice instructions.

Instead of slow, clunky automation, Orion responds instantly (in under 50 milliseconds) using an efficient local background server.

---

## ⚡ Technologies Used

Orion is powered by modern, reliable technologies:

* **Python 3.10+**: Core automation engine, web search resolver, and task coordinator.
* **PowerShell & Windows Command Line**: Fast command-line interface with instant regex intent routing.
* **Windows OneCore & SAPI Speech API**: High-definition studio text-to-speech engine (featuring Microsoft George, Susan, Zira, Heera, and Ravi).
* **Windows Win32 GUI APIs**: Pixel-accurate window focusing, mouse control, and keyboard typing.
* **Lightweight Local REST API (Port 8765)**: In-memory perception server delivering live screen data and video streaming.
* **Google Antigravity (`agy`) Integration**: Natural language AI fallback for complex multi-step user tasks.

---

## 🚀 How It Works

Orion operates through three integrated systems:

### 1. Smart Intent Router
When you run a command, Orion immediately determines the intent:
* **Web Searching & Browsing**: Directly resolves URLs or search queries and opens the browser in under 40 milliseconds without mouse simulation.
* **App Launching**: Starts any installed Windows application directly.
* **Window Focusing**: Finds and brings any open window to the front.
* **Voice Speech**: Synthesizes speech using high-definition Windows OneCore voices.

### 2. Live Screen Perception (Port 8765)
A lightweight background server continuously tracks:
* **Live Telemetry**: Foreground window, process PID, mouse coordinates, and motion activity.
* **Fast Vision Frames**: Lightweight JPEG snapshots for AI vision inspection.
* **Web Dashboard**: Real-time screen video stream and workstation status at `http://localhost:8765/`.

### 3. Closed-Loop Task Verification
Every automated action validates results:
* Checks that target windows physically appear on the screen.
* Checks that requested files are generated.
* Checks that required network ports are active.

---

## 📥 Download Antigravity CLI (`agy`)

Orion seamlessly connects with **Google Antigravity CLI (`agy`)** to carry out complex natural language tasks.

### Install `agy` on Windows:
```powershell
# Install via official PowerShell script
irm https://antigravity.google/install.ps1 | iex
```
*Alternatively, download the Windows installer from [https://antigravity.google/docs/cli](https://antigravity.google/docs/cli).*

### Verify CLI:
```powershell
agy --version
```

---

## 📦 Installation & Setup

### 1. Clone the Repository
```powershell
git clone https://github.com/nividharan/Orion--V2.0-Nebula.git
cd Orion--V2.0-Nebula
```

### 2. Install Required Python Packages
```powershell
pip install -r requirements.txt
```

---

## 🚀 How to Start Orion

You can launch and interact with Orion in two ways:

### Method 1: Start the Live Perception Server (Recommended)
Starting the background server gives you sub-10ms response times and live screen streaming:
```powershell
python desktop_controller.py api --port 8765
```
*Or using the Orion wrapper:*
```powershell
orion api
```
> Once running, open **`http://localhost:8765/`** in your browser to view the live screen video stream and real-time workstation status dashboard.

### Method 2: Run Commands Directly
You can also run commands straight from your terminal:
```powershell
orion version                                   # Check Orion version
orion quick                                     # Instant screen status check
orion speak "Orion online"                      # Test voice synthesizer
orion browse "https://github.com"               # Test browser launcher
```

### (Optional) Add Orion to Your System PATH
To type `orion` from any terminal folder on your machine:
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$PWD", "User")
```

---

## 🛠️ Command Reference

Use `orion` (or the aliases `nebula`, `deskctl`, and `dskctl`) from your terminal:

### Web Browsing & Search
```powershell
orion browse "https://github.com"                # Open URL in default browser
orion browse "documentation"                    # Search Google instantly
orion browse --browser chrome "https://example.com"  # Open in Google Chrome
orion browse --browser edge "search query"      # Open in Microsoft Edge
```

### Voice Speech (TTS)
```powershell
orion speak "<message>"                         # Executive George voice (Default)
orion speak "<message>" -v Susan                # Professional British Susan voice
orion speak "<message>" -v Zira                 # Clear American Zira voice
orion speak "<message>" -v Heera                # Natural Heera voice
orion voices                                    # List all available voices
```

### Application & Window Control
```powershell
orion open <app_name>                           # Launch any installed application
orion focus "<window_title>"                    # Bring window to foreground
orion windows                                   # List active top-level windows
orion apps [filter]                             # Search installed applications
orion ports                                     # Scan listening network ports
```

### Continuous Screen Perception & Monitoring
```powershell
orion watch                                     # Real-time continuous screen perception monitor (FPS, Delta %, Settled status)
orion watch --fps 8                             # Monitor screen at 8 FPS
orion quick                                     # Fast 6ms workstation telemetry
orion status                                    # Full system status JSON
orion shot                                      # Instant screen capture
```

### Autonomous Self-Healing & Error Resolution
```powershell
orion heal                                      # Diagnostic scan: auto-dismisses modal error popups & repairs context
```

### Natural Language, AutoGen Society & 3D Automation
```powershell
# Run with 5-agent collaborative team (with continuous perception & auto-healing)
orion team "open chrome to https://github.com, launch notepad, and announce status"

# Native Blender 3D automation over local socket port 9876
orion team "in the opened blender create a red circle"
orion team "in the opened blender create a blue cube"

# General in-app natural language actions
orion "in notepad type Hello Orion, and announce completion"
```

### Microphone Audio Input & Speech
```powershell
orion listen                                    # Listen to microphone and transcribe speech
orion listen 6                                  # Listen for 6 seconds
orion record 5                                  # Record 5 seconds of microphone audio to WAV
orion transcribe --audio "meeting.wav"          # Transcribe audio file
```

---

## 📜 License

Distributed under the **MIT License**.
