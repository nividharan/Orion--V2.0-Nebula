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

Orion works through three simple layers:

### 1. Smart Intent Router
When you type a command, Orion understands what you want to do right away:
* **Web Searching & Browsing**: Type `orion "open chrome swayam nptel"` or `orion browse "machine learning"` and Orion opens the website directly in under 40 milliseconds without any mouse clicking loops.
* **App Launching**: Type `orion open notepad` or `orion open blender` to launch any installed application on your system.
* **Window Focusing**: Type `orion focus "Visual Studio Code"` to instantly bring any open window to the front.
* **Voice Speech**: Type `orion speak "Task completed"` to hear updates spoken out loud in a natural, professional voice.

### 2. Live Screen Perception
Orion runs a lightweight server in the background:
* **Live Telemetry**: Checks which window is currently open, where the mouse is, and if animations are playing on your screen.
* **Fast Vision Frames**: Takes small, high-quality snapshots (50 KB) so AI vision models can inspect your screen with low delay.
* **Web Dashboard**: Lets you view your live screen stream and system status in your browser at `http://localhost:8765/`.

### 3. Closed-Loop Task Verification
Whenever Orion completes an action, it automatically verifies that:
* The window actually appeared on the screen.
* The expected files were created.
* The required network ports or servers are running.

---

## 🛠️ How to Use (Commands)

You can use `orion` (or the aliases `nebula`, `deskctl`, and `dskctl`) directly in your terminal:

### Web Browsing & Search
```powershell
orion browse "swayam nptel"                # Opens exact portal directly
orion browse "https://github.com"          # Opens website in default browser
orion browse "machine learning"            # Searches Google instantly
orion "open chrome swayam nptel"           # Opens in Google Chrome
```

### Voice Speech
```powershell
orion speak "System is online and ready."          # Professional George voice (Default)
orion speak "Process finished successfully." -v Susan  # Professional Susan voice
orion speak "Hello world." -v Zira                 # Clear American voice
orion voices                                       # List all available voices
```

### Application & Window Control
```powershell
orion open blender                         # Launch any installed app
orion focus Chrome                         # Bring Chrome to the front
orion windows                              # List all open windows
orion apps code                            # Search your installed apps
orion ports                                # Scan listening network ports
```

### Screen & System Status
```powershell
orion quick                                # Instant 6ms screen status
orion status                               # Full system telemetry
orion shot                                 # Quick screenshot capture
```

### Natural Language Tasks
If a command requires complex steps, Orion automatically forwards it to the Antigravity AI agent:
```powershell
orion "create a monthly expense budget in excel"
orion "generate a 3d model in blender"
```

---

## 📜 License

Distributed under the **MIT License**.
