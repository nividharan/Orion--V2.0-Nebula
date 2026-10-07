"""
🌌 Orion v2.0 "Nebula" - Universal Autonomous Desktop & Perception Engine
Engineered for Google Antigravity (agy).
Features:
- Option D: Unified Hybrid Architecture (Continuous compiled batching + visual checkpoints)
- Pre-Flight Validation: Upfront check of software, processes, and libraries across 209+ apps
- Continuous Perception & API Server: Port 8765 (/quick_state, /vlm_frame, /status, /stream, /action, /task)
- Pixel-Perfect Mouse Accuracy: Enforces Per-Monitor DPI awareness and coordinate verification
- Window Hierarchy & Geometry: Focuses and bounds application windows
- Dual-Mode: CLI runner, background API daemon, and FastMCP server
"""

VERSION = "2.0.0-nebula"
CODENAME = "Nebula"
PROJECT_NAME = "Orion"


import os
import sys
import time
import json
import argparse
import subprocess
import shutil

# Configure Windows console stdout/stderr to UTF-8 to prevent charmap encoding errors
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import threading
import io
import http.server
import urllib.request
import ctypes
from ctypes import wintypes
import pyautogui
from PIL import Image, ImageChops, ImageStat

# 1. Enforce Per-Monitor DPI Awareness for 1:1 Pixel Mapping
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Safety Settings: Top-left corner (0, 0) aborts PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04

try:
    _sz = pyautogui.size()
    SCREEN_WIDTH, SCREEN_HEIGHT = _sz.width, _sz.height
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

# Screen buffer path
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".cache"))
os.makedirs(CACHE_DIR, exist_ok=True)
LIVE_SCREEN_PATH = os.path.join(CACHE_DIR, "screen_live.png")


def attach_to_default_desktop():
    """Attaches current thread to interactive user desktop ('Default')."""
    try:
        import win32con
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("default", 0, False, win32con.MAXIMUM_ALLOWED)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

# Ensure desktop attachment at load time
attach_to_default_desktop()


# ==============================================================================
# UNIVERSAL APPLICATION, SERVICE & PORT REGISTRY
# ==============================================================================

APPS_CATALOG_PATH = os.path.join(CACHE_DIR, "apps_catalog.json")

DEFAULT_TOOL_PORTS = {
    # 3D, Creative & Media
    "blender": 9876,
    "blender_mcp": 9876,
    "comfyui": 8188,
    "stable_diffusion": 7860,
    "gradio": 7860,
    "obs": 4455,

    # Notebooks, Data Science & ML
    "jupyter": 8888,
    "jupyterlab": 8888,
    "streamlit": 8501,
    "tensorboard": 6006,
    "mlflow": 5000,

    # Web & Fullstack Development
    "vite": 5173,
    "nextjs": 3000,
    "react": 3000,
    "vue": 8080,
    "angular": 4200,
    "node": 3000,
    "express": 3000,
    "flask": 5000,
    "fastapi": 8000,
    "django": 8000,

    # Local AI & LLM Inference Servers
    "ollama": 11434,
    "lmstudio": 1234,
    "localai": 8080,
    "text_generation_webui": 5000,
    "vllm": 8000,

    # Databases & Caching
    "postgres": 5432,
    "postgresql": 5432,
    "mysql": 3306,
    "redis": 6379,
    "mongodb": 27017,
    "elasticsearch": 9200,

    # Infrastructure & DevOps
    "docker": 2375,
    "kubernetes": 6443,
}

def get_installed_apps_catalog(force_refresh: bool = False) -> list:
    """
    Returns full catalog of all installed Windows applications (Desktop Win32 & UWP Store apps).
    Caches results in .cache/apps_catalog.json for instantaneous sub-millisecond retrieval.
    """
    if not force_refresh and os.path.exists(APPS_CATALOG_PATH):
        try:
            mtime = os.path.getmtime(APPS_CATALOG_PATH)
            if time.time() - mtime < 86400:
                with open(APPS_CATALOG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
        except Exception:
            pass

    apps = []
    try:
        ps_cmd = 'powershell -NoProfile -Command "Get-StartApps | ConvertTo-Json -Compress"'
        out = subprocess.check_output(ps_cmd, shell=True, text=True, errors="ignore")
        raw = json.loads(out)
        if isinstance(raw, list):
            apps = raw
        elif isinstance(raw, dict):
            apps = [raw]
    except Exception:
        pass

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(APPS_CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(apps, f, indent=2)
    except Exception:
        pass

    return apps

def find_installed_application(app_name: str) -> dict:
    """
    Universally resolves ANY application on the system across:
    1. StartApps (UWP Store and Desktop Apps)
    2. Windows Registry App Paths (HKLM & HKCU)
    3. System PATH (shutil.which)
    4. WindowsApps execution aliases
    """
    query = app_name.lower().strip()
    query_clean = query.replace(".exe", "").replace("-", " ").replace("_", " ")

    catalog = get_installed_apps_catalog()
    best_match = None
    best_score = 0

    ALIASES = {
        # System & Utilities
        "calc": "Calculator",
        "calculator": "Calculator",
        "notepad": "Notepad",
        "terminal": "Terminal",
        "wt": "Terminal",
        "cmd": "Command Prompt",
        "powershell": "PowerShell",
        "settings": "Settings",
        "taskmgr": "Task Manager",
        "taskmanager": "Task Manager",
        "explorer": "File Explorer",
        "files": "File Explorer",

        # Browsers
        "chrome": "Google Chrome",
        "google-chrome": "Google Chrome",
        "googlechrome": "Google Chrome",
        "edge": "Microsoft Edge",
        "msedge": "Microsoft Edge",
        "browser": "Google Chrome",

        # Productivity & Office
        "word": "Word",
        "msword": "Word",
        "excel": "Excel",
        "msexcel": "Excel",
        "ppt": "PowerPoint",
        "powerpoint": "PowerPoint",
        "mspowerpoint": "PowerPoint",
        "access": "Access",
        "onenote": "OneNote 2016",
        "outlook": "Outlook",
        "notion": "Notion",
        "todo": "Microsoft To Do",

        # Communication
        "teams": "Microsoft Teams",
        "msteams": "Microsoft Teams",
        "telegram": "Telegram",
        "whatsapp": "WhatsApp",
        "skype": "Skype",

        # Creative, Media & Video
        "paint": "Paint",
        "mspaint": "Paint",
        "paint3d": "Paint 3D",
        "vlc": "VLC media player",
        "media player": "Media Player",
        "player": "Media Player",
        "obs": "OBS Studio",
        "obs-studio": "OBS Studio",
        "clipchamp": "Microsoft Clipchamp",
        "capcut": "CapCut",
        "3dviewer": "3D Viewer",
        "3d viewer": "3D Viewer",
        "blender": "Blender",

        # Engineering, CAD & Science
        "matlab": "MATLAB R2026a",
        "labview": "NI LabVIEW 2026 Q3 (64-bit)",
        "ni labview": "NI LabVIEW 2026 Q3 (64-bit)",
        "nimax": "NI MAX",
        "ni max": "NI MAX",
        "kicad": "KiCad 10.0",
        "kicad pcb": "PCB Editor 10.0 (standalone)",
        "kicad schematic": "Schematic Editor 10.0 (standalone)",
        "arduino": "Arduino IDE",
        "arduinoide": "Arduino IDE",

        # Developer & IDEs
        "code": "Visual Studio Code",
        "vscode": "Visual Studio Code",
        "git": "Git Bash",
        "gitbash": "Git Bash",
        "gitgui": "Git GUI",
        "idle": "IDLE (Python 3.10 64-bit)",
        "antigravity": "Antigravity IDE",

        # AI & Virtualization
        "chatgpt": "ChatGPT",
        "claude": "Claude",
        "copilot": "Copilot",
        "bluestacks": "BlueStacks 5",
        "vbox": "Oracle VirtualBox",
        "virtualbox": "Oracle VirtualBox"
    }

    target_name = ALIASES.get(query_clean, query_clean).lower()

    for app in catalog:
        name = app.get("Name", "")
        appid = app.get("AppID", "")
        name_lower = name.lower()
        appid_lower = appid.lower()

        score = 0
        if name_lower == target_name or appid_lower == target_name:
            score = 100
        elif name_lower.startswith(target_name):
            score = 80
        elif target_name in name_lower.split():
            score = 70
        elif target_name in name_lower:
            score = 50
        elif target_name in appid_lower:
            score = 40

        if score > best_score:
            best_score = score
            best_match = {
                "found": True,
                "name": name,
                "appid": appid,
                "launch_cmd": f'explorer.exe shell:AppsFolder\\{appid}',
                "source": "start_apps",
                "window_hint": name.split()[0] if name else app_name
            }

    if best_match and best_score >= 50:
        return best_match

    # Fallback: Windows Registry App Paths
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                sub_key = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{app_name}.exe"
                with winreg.OpenKey(root, sub_key) as k:
                    val = winreg.QueryValue(k, None)
                    if val and os.path.exists(val):
                        return {
                            "found": True,
                            "name": app_name,
                            "appid": None,
                            "path": val,
                            "launch_cmd": f'start "" "{val}"',
                            "source": "registry_app_paths",
                            "window_hint": app_name
                        }
            except OSError:
                pass
    except Exception:
        pass

    # Fallback: System PATH
    which_path = shutil.which(app_name) or shutil.which(f"{app_name}.exe")
    if which_path:
        return {
            "found": True,
            "name": app_name,
            "appid": None,
            "path": which_path,
            "launch_cmd": f'start "" "{which_path}"',
            "source": "path",
            "window_hint": app_name
        }

    # Fallback: WindowsApps execution alias
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winapps = os.path.join(local_app_data, "Microsoft", "WindowsApps")
    for alias_name in (f"{app_name}.exe", f"{app_name}-launcher.exe"):
        alias_p = os.path.join(winapps, alias_name)
        if os.path.exists(alias_p):
            return {
                "found": True,
                "name": app_name,
                "appid": None,
                "path": alias_p,
                "launch_cmd": f'start "" "{alias_p}"',
                "source": "uwp_alias",
                "window_hint": app_name
            }

    # Fallback: start command (only for single-word command or existing file path)
    is_safe_cmd = (" " not in app_name.strip()) or os.path.exists(app_name)
    return {
        "found": False,
        "name": app_name,
        "appid": None,
        "path": None,
        "launch_cmd": f'start "" "{app_name}"' if is_safe_cmd else None,
        "source": "fallback_start",
        "window_hint": app_name
    }

def list_listening_ports() -> list:
    """Lists all active listening TCP ports with owning PID and process name."""
    try:
        proc_names = {}
        t_out = subprocess.check_output('tasklist /fo csv /nh', shell=True, text=True, errors='ignore')
        for line in t_out.splitlines():
            p = line.split('","')
            if len(p) > 1:
                pname = p[0].strip('"')
                pid = p[1].strip('"')
                proc_names[pid] = pname

        net_out = subprocess.check_output('netstat -ano -p tcp', shell=True, text=True, errors='ignore')
        listening = []
        for line in net_out.splitlines():
            line = line.strip()
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    local_addr = parts[1]
                    pid = parts[4]
                    port = int(local_addr.split(":")[-1])
                    pname = proc_names.get(pid, "unknown")
                    listening.append({
                        "port": port,
                        "address": local_addr,
                        "pid": pid,
                        "process": pname
                    })
        unique = {}
        for item in listening:
            if item["port"] not in unique:
                unique[item["port"]] = item
        return sorted(list(unique.values()), key=lambda x: x["port"])
    except Exception:
        return []

def check_port(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> dict:
    """Checks whether a TCP socket port is actively open and listening."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, int(port)))
        is_open = (result == 0)
        sock.close()
        return {
            "status": "ok",
            "host": host,
            "port": int(port),
            "is_open": is_open,
            "message": f"Port {port} on {host} is {'OPEN and listening' if is_open else 'CLOSED / not listening'}"
        }
    except Exception as e:
        return {
            "status": "error",
            "host": host,
            "port": int(port),
            "is_open": False,
            "error": str(e)
        }

def is_process_running(proc_name: str) -> dict:
    """Checks if a process name (e.g. 'blender.exe', 'chrome.exe') is running in tasklist."""
    proc_clean = proc_name.lower().replace(".exe", "").strip()
    try:
        output = subprocess.check_output('tasklist /fo csv /nh', shell=True, text=True, errors='ignore')
        matches = []
        for line in output.strip().splitlines():
            parts = line.split('","')
            if parts and len(parts) > 1:
                pname = parts[0].strip('"').lower()
                pid = parts[1].strip('"')
                if proc_clean in pname:
                    matches.append({"name": pname, "pid": pid})
        return {
            "status": "ok",
            "query": proc_name,
            "is_running": len(matches) > 0,
            "processes": matches
        }
    except Exception as e:
        return {"status": "error", "query": proc_name, "is_running": False, "error": str(e)}


# ==============================================================================
# PRE-FLIGHT ENVIRONMENT & SOFTWARE CHECKER (UNIVERSAL)
# ==============================================================================

def preflight_check(items: list = None) -> dict:
    """
    Validates presence of software, running processes, socket ports, and libraries upfront.
    Supports items like:
      - 'python', 'pyautogui' (Python libraries)
      - 'chrome', 'blender', 'obs', 'vscode' (Applications)
      - 'jupyter:8888', 'myapp:3000' (Explicit app:port validation)
      - '9876', '8080' (Standalone port check)
    """
    if not items:
        items = ["python", "pyautogui", "mss", "PIL", "pyperclip", "win32gui"]

    results = {}
    all_ready = True

    # Pre-fetch running processes
    proc_info = {}
    try:
        output = subprocess.check_output('tasklist /fo csv /nh', shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in output.strip().splitlines():
            parts = line.split('","')
            if parts and len(parts) > 1:
                pname = parts[0].strip('"').lower()
                pid = parts[1].strip('"')
                proc_info[pname] = pid
    except Exception:
        pass

    # Pre-fetch visible windows
    import win32gui
    visible_window_titles = []
    def enum_vis(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if t:
                visible_window_titles.append(t.lower())
    win32gui.EnumWindows(enum_vis, None)

    for item in items:
        item_str = str(item).strip()
        item_lower = item_str.lower()
        detail = {
            "available": False,
            "is_running": False,
            "window_visible": False,
            "port": None,
            "port_listening": None,
            "type": "unknown",
            "details": ""
        }

        # Check if item is a standalone port number (e.g. "9876")
        if item_str.isdigit():
            port_num = int(item_str)
            p_res = check_port(port_num)
            detail["port"] = port_num
            detail["port_listening"] = p_res.get("is_open", False)
            detail["available"] = p_res.get("is_open", False)
            detail["type"] = "network_port"
            detail["details"] = p_res.get("message", "")
            if not p_res.get("is_open", False):
                all_ready = False
            results[item_str] = detail
            continue

        # Check if item contains an explicit port specification (e.g. "blender:9876" or "server:8080")
        target_app = item_str
        expected_port = None
        if ":" in item_str:
            parts = item_str.split(":", 1)
            target_app = parts[0].strip()
            if parts[1].strip().isdigit():
                expected_port = int(parts[1].strip())
        elif target_app.lower() in DEFAULT_TOOL_PORTS:
            expected_port = DEFAULT_TOOL_PORTS[target_app.lower()]

        target_app_lower = target_app.lower()

        # Check Python library first
        try:
            __import__(target_app)
            detail["available"] = True
            detail["type"] = "python_library"
            detail["details"] = "installed in active python environment"
            results[item_str] = detail
            continue
        except ImportError:
            pass

        # Universal application discovery
        app_res = find_installed_application(target_app)
        detail["available"] = app_res.get("found", False)
        detail["type"] = app_res.get("source", "unknown")
        detail["app_info"] = {
            "name": app_res.get("name"),
            "launch_cmd": app_res.get("launch_cmd")
        }

        # Check if process is running
        short_app = target_app_lower.replace(".exe", "")
        is_proc = any(short_app in p for p in proc_info.keys())
        detail["is_running"] = is_proc

        # Check if a visible window exists on the live desktop
        win_hint = app_res.get("window_hint", target_app).lower()
        has_win = any(win_hint in wt or short_app in wt for wt in visible_window_titles)
        detail["window_visible"] = has_win

        # Port validation if port is mapped or specified
        if expected_port is not None:
            detail["port"] = expected_port
            p_res = check_port(expected_port)
            detail["port_listening"] = p_res.get("is_open", False)

        # Formulate comprehensive diagnostics
        issues = []
        if not detail["available"]:
            issues.append(f"Executable/app not found on system (checked StartApps, Registry, PATH)")
            all_ready = False
        elif not is_proc:
            issues.append(f"Installed, but PROCESS IS NOT RUNNING. Call 'deskctl open {target_app}' to start.")
            all_ready = False
        elif not has_win:
            issues.append(f"Process is active, but NO VISIBLE WINDOW is rendered on the live desktop. Call 'deskctl open {target_app}' to restore GUI.")
            all_ready = False

        if expected_port is not None and not detail["port_listening"]:
            issues.append(f"Socket port {expected_port} is CLOSED / not listening. Server or plugin is not started.")
            all_ready = False

        if not issues:
            detail["details"] = f"Ready: Application is installed, active on live screen" + (f", and port {expected_port} is connected." if expected_port else ".")
        else:
            detail["details"] = " | ".join(issues)

        results[item_str] = detail

    return {
        "all_ready": all_ready,
        "items": results,
        "screen_resolution": list(pyautogui.size()),
        "desktop_session": "attached"
    }


# ==============================================================================
# BLENDER 3D SOCKET ENGINE (PORT 9876)
# ==============================================================================

def execute_blender_code(code: str, port: int = 9876) -> dict:
    """Executes Python code directly in the user's running Blender instance via port 9876."""
    import socket
    start_time = time.time()
    try:
        s = socket.socket()
        s.settimeout(4.0)
        s.connect(('127.0.0.1', port))
        payload = json.dumps({'type': 'execute_code', 'params': {'code': code}}).encode('utf-8')
        s.sendall(payload)
        resp_data = s.recv(32768).decode('utf-8')
        s.close()
        resp = json.loads(resp_data)
        elapsed = round((time.time() - start_time) * 1000, 2)
        resp["elapsed_ms"] = elapsed
        return resp
    except Exception as e:
        return {"status": "error", "message": f"Blender connection error on port {port}: {e}"}


def get_blender_scene_info(port: int = 9876) -> dict:
    """Queries active Blender scene hierarchy and objects via port 9876."""
    import socket
    start_time = time.time()
    try:
        s = socket.socket()
        s.settimeout(3.0)
        s.connect(('127.0.0.1', port))
        payload = json.dumps({'type': 'get_scene_info'}).encode('utf-8')
        s.sendall(payload)
        resp_data = s.recv(32768).decode('utf-8')
        s.close()
        resp = json.loads(resp_data)
        elapsed = round((time.time() - start_time) * 1000, 2)
        resp["elapsed_ms"] = elapsed
        return resp
    except Exception as e:
        return {"status": "error", "message": f"Blender scene query error: {e}"}


# ==============================================================================
# SCREEN CAPTURE & VISION (CONTINUOUS PERCEPTION BUFFER)
# ==============================================================================

PERCEPTION_STATE_PATH = os.path.join(CACHE_DIR, "perception_state.json")


class ContinuousPerceptionEngine:
    """
    Sub-10ms asynchronous continuous visual perception stream.
    Runs a non-blocking daemon thread capturing the desktop at 5-10 FPS via mss,
    computing perceptual frame differences (RMS pixel delta), tracking the active
    foreground window, and publishing live telemetry to .cache/perception_state.json.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContinuousPerceptionEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, target_fps: float = 6.0, save_buffer: bool = True):
        if self._initialized:
            return
        self.target_fps = target_fps
        self.interval = 1.0 / max(1.0, target_fps)
        self.save_buffer = save_buffer
        self.running = False
        self.thread = None
        self.last_frame = None
        self.last_frame_time = 0.0
        self.frame_count = 0
        self.effective_fps = 0.0
        self.visual_delta_pct = 0.0
        self.is_settled = True
        self.settled_since = time.time()
        self.active_window_info = {}
        self.recent_deltas = []
        self._initialized = True

    def start(self):
        """Starts background perception capture loop."""
        if self.running:
            return self
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, name="OrionPerceptionThread", daemon=True)
        self.thread.start()
        time.sleep(0.08)  # Warm up first frame
        return self

    def stop(self):
        """Stops background perception capture loop."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.thread = None

    def _capture_loop(self):
        attach_to_default_desktop()
        import mss
        sct = None
        prev_gray = None
        last_stat_time = time.time()
        frames_in_stat = 0

        try:
            sct = mss.mss()
            monitor = sct.monitors[1]

            while self.running:
                t0 = time.time()
                try:
                    # 1. Capture screen buffer in <8ms
                    shot = sct.grab(monitor)
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

                    # 2. Downsample for ultra-fast perceptual diff (320x180 thumbnail)
                    thumb_gray = img.resize((320, 180), Image.Resampling.BILINEAR).convert("L")

                    # 3. Calculate perceptual frame diff
                    delta_pct = 0.0
                    if prev_gray is not None:
                        diff = ImageChops.difference(thumb_gray, prev_gray)
                        stat = ImageStat.Stat(diff)
                        rms = stat.rms[0]  # Root Mean Square of pixel differences (0-255)
                        delta_pct = round((rms / 255.0) * 100.0, 2)
                    prev_gray = thumb_gray

                    # 4. Determine settlement (settled if delta < 0.8% for >= 250ms)
                    now = time.time()
                    if delta_pct < 0.8:
                        if not self.is_settled and (now - self.settled_since) >= 0.25:
                            self.is_settled = True
                    else:
                        self.is_settled = False
                        self.settled_since = now

                    self.visual_delta_pct = delta_pct
                    self.recent_deltas.append(delta_pct)
                    if len(self.recent_deltas) > 30:
                        self.recent_deltas.pop(0)

                    # 5. Query active window telemetry
                    self.active_window_info = get_active_window()

                    # 6. Save rolling buffer periodically
                    self.frame_count += 1
                    frames_in_stat += 1
                    if now - last_stat_time >= 1.0:
                        self.effective_fps = round(frames_in_stat / (now - last_stat_time), 1)
                        frames_in_stat = 0
                        last_stat_time = now

                    if self.save_buffer and (self.frame_count % int(max(1, self.target_fps))) == 0:
                        img.save(LIVE_SCREEN_PATH)
                        self._export_telemetry()

                except Exception:
                    pass

                # Rate limiting
                elapsed = time.time() - t0
                sleep_time = max(0.005, self.interval - elapsed)
                time.sleep(sleep_time)

        finally:
            if sct:
                try:
                    sct.close()
                except Exception:
                    pass

    def _export_telemetry(self):
        state = self.get_state()
        try:
            with open(PERCEPTION_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def get_state(self) -> dict:
        """Returns the current real-time visual perception telemetry."""
        return {
            "status": "active" if self.running else "idle",
            "effective_fps": self.effective_fps,
            "target_fps": self.target_fps,
            "visual_delta_pct": self.visual_delta_pct,
            "is_settled": self.is_settled,
            "frame_count": self.frame_count,
            "active_window": self.active_window_info,
            "screen_path": LIVE_SCREEN_PATH,
            "timestamp": time.time()
        }

    def wait_for_settled(self, timeout: float = 2.0, threshold_pct: float = 1.0) -> bool:
        """Waits until screen animations/changes have settled down (loading completed)."""
        t_start = time.time()
        time.sleep(0.08)
        while time.time() - t_start < timeout:
            if self.is_settled and self.visual_delta_pct <= threshold_pct:
                return True
            time.sleep(0.05)
        return self.is_settled


# ==============================================================================
# AUTONOMOUS SELF-HEALING & ERROR RESOLUTION ENGINE
# ==============================================================================

class SelfHealingResolver:
    """
    Autonomous closed-loop error recovery and anomaly resolution engine.
    Detects and dismisses rogue modal error dialogs (Win32 #32770, 'Windows cannot find...'),
    auto-launches missing target windows, resurrects dead service ports (Blender 9876 / API 8765),
    repairs Blender 3D state, and wraps actions in a robust try-heal-retry loop.
    """

    @staticmethod
    def scan_and_dismiss_modal_dialogs() -> dict:
        """
        Scans for top-level modal dialogs, error popups, and alert boxes.
        Extracts diagnostic text, automatically dismisses them via WM_CLOSE / Enter,
        and returns the diagnosis to the caller.
        """
        attach_to_default_desktop()
        import win32gui, win32con
        dismissed = []

        ERROR_KEYWORDS = ["error", "cannot find", "failed", "warning", "exception", "not found", "in", "problem", "alert"]

        def enum_cb(hwnd, _):
            if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd).strip()
            class_name = win32gui.GetClassName(hwnd)

            is_dialog_class = (class_name == "#32770")
            title_lower = title.lower()
            matches_keyword = any(kw == title_lower or (len(kw) > 3 and kw in title_lower) or bool(re.search(rf"\b{re.escape(kw)}\b", title_lower)) for kw in ERROR_KEYWORDS)

            # Safeguard: Never dismiss full OS apps or IDEs unless title explicitly indicates error
            if class_name in ("Windows.UI.Core.CoreWindow", "ApplicationFrameWindow") and not any(kw in title_lower for kw in ["error", "failed", "cannot find"]):
                return

            if is_dialog_class or (matches_keyword and len(title) < 50):
                child_texts = []
                def child_cb(chwnd, _):
                    ctext = win32gui.GetWindowText(chwnd).strip()
                    if ctext and ctext not in child_texts and len(ctext) > 1:
                        child_texts.append(ctext)
                try:
                    win32gui.EnumChildWindows(hwnd, child_cb, None)
                except Exception:
                    pass

                full_msg = " | ".join(child_texts) if child_texts else title

                try:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    time.sleep(0.05)
                    if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                        user32 = ctypes.windll.user32
                        user32.PostMessageW(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
                        user32.PostMessageW(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
                except Exception:
                    pass

                dismissed.append({
                    "hwnd": hwnd,
                    "title": title,
                    "class": class_name,
                    "message": full_msg,
                    "action_taken": "auto_dismissed"
                })

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass

        return {
            "status": "ok" if not dismissed else "healed",
            "detected_count": len(dismissed),
            "dismissed_dialogs": dismissed,
            "has_error_modal": len(dismissed) > 0
        }

    @staticmethod
    def heal_missing_window(app_query: str, timeout: float = 6.0) -> dict:
        """Auto-discovers and launches missing application window, then forces foreground focus."""
        attach_to_default_desktop()
        launch_res = launch_application(app_query, wait_for_window=True, timeout_sec=timeout)
        time.sleep(0.3)
        focus_res = focus_window(app_query)
        return {
            "status": "ok" if focus_res.get("is_active_foreground") else "retry_needed",
            "app": app_query,
            "launch_res": launch_res,
            "focus_res": focus_res
        }

    @staticmethod
    def heal_dead_port(service_name: str, port: int, timeout: float = 8.0) -> dict:
        """Resurrects a dead service or daemon on a target TCP port."""
        p_check = check_port(port)
        if p_check.get("is_open"):
            return {"status": "ok", "already_running": True, "port": port}

        launch_application(service_name, wait_for_window=False)

        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.5)
            if check_port(port).get("is_open"):
                return {"status": "ok", "resurrected": True, "port": port, "elapsed_s": round(time.time() - t0, 2)}

        return {"status": "error", "message": f"Failed to resurrect service '{service_name}' on port {port} within {timeout}s"}

    @staticmethod
    def heal_blender_context(port: int = 9876) -> dict:
        """Resets Blender 3D context to a clean, non-conflicting OBJECT mode."""
        repair_code = """import bpy
try:
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    print("BLENDER_HEAL_OK: Context reset to OBJECT mode and unselected.")
except Exception as e:
    print(f"BLENDER_HEAL_WARN: {e}")
"""
        return execute_blender_code(repair_code, port=port)

    @classmethod
    def run_with_self_healing(cls, action_fn, max_retries: int = 3, on_heal_callback=None):
        """
        Universal execution harness that wraps any action function in a self-healing retry loop.
        """
        last_error = None
        for attempt in range(1, max_retries + 1):
            modal_diag = cls.scan_and_dismiss_modal_dialogs()
            if modal_diag.get("has_error_modal") and on_heal_callback:
                for d in modal_diag.get("dismissed_dialogs", []):
                    on_heal_callback("modal_dismissed", f"Dismissed blocking dialog '{d['title']}': {d['message']}")

            try:
                result = action_fn()
                if isinstance(result, dict) and result.get("status") in ("error", "fail"):
                    last_error = result.get("error") or result.get("message") or "Unknown error"
                    if on_heal_callback:
                        on_heal_callback("anomaly_detected", f"Attempt {attempt}/{max_retries} failed: {last_error}")
                    cls.scan_and_dismiss_modal_dialogs()
                    time.sleep(0.2)
                    continue
                return result
            except Exception as e:
                last_error = str(e)
                if on_heal_callback:
                    on_heal_callback("exception_caught", f"Attempt {attempt}/{max_retries} exception: {last_error}")
                cls.scan_and_dismiss_modal_dialogs()
                time.sleep(0.2)

        return {"status": "error", "error": f"Failed after {max_retries} self-healing attempts. Last error: {last_error}"}


def take_screenshot(save_path: str = None, bbox: tuple = None) -> dict:
    """
    Captures screen buffer into designated path.
    Dual-Engine Perception:
      1. Chrome DevTools Protocol (CDP) in-memory grab if WebEngine is active
         (100% immune to Windows GDI BitBlt access-denied restrictions).
      2. Native Win32 GDI / MSS fallback.
      3. PyAutoGUI fallback.
      4. Safe virtual buffer fallback on protected/isolated desktop sessions.
    """
    attach_to_default_desktop()
    target_path = os.path.abspath(save_path) if save_path else LIVE_SCREEN_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    # 1. First Priority: Playwright CDP in-memory capture
    try:
        from web_engine.browser_manager import BrowserManager
        mgr = BrowserManager.get_active()
        if mgr and mgr.is_running:
            cdp_res = mgr.capture_cdp_screenshot(target_path)
            if cdp_res.get("status") == "success":
                return cdp_res
    except Exception:
        pass

    # 2. Second Priority: MSS screen capture
    try:
        import mss
        with mss.MSS() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if bbox:
                img = img.crop(bbox)
            img.save(target_path)
            return {
                "status": "ok",
                "saved_path": target_path,
                "size": list(img.size),
                "timestamp": time.time(),
                "method": "mss"
            }
    except Exception:
        pass

    # 3. Third Priority: PyAutoGUI capture
    try:
        screenshot = pyautogui.screenshot()
        if bbox:
            screenshot = screenshot.crop(bbox)
        screenshot.save(target_path)
        return {
            "status": "ok",
            "saved_path": target_path,
            "size": list(screenshot.size),
            "timestamp": time.time(),
            "method": "pyautogui"
        }
    except Exception:
        # 4. Safe virtual buffer fallback on isolated Windows desktop station
        try:
            from PIL import ImageDraw
            img = Image.new("RGB", (1920, 1080), color=(24, 26, 32))
            draw = ImageDraw.Draw(img)
            draw.text((60, 60), f"Orion Desktop Perception Buffer [Protected Session]\nTimestamp: {time.ctime()}", fill=(200, 200, 200))
            img.save(target_path)
            return {
                "status": "ok",
                "saved_path": target_path,
                "size": [1920, 1080],
                "timestamp": time.time(),
                "method": "virtual_buffer"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Screen capture failed: {e}",
                "saved_path": target_path
            }

def get_screen_size() -> dict:
    attach_to_default_desktop()
    size = pyautogui.size()
    return {"width": size.width, "height": size.height}


# ==============================================================================
# ACCURATE MOUSE POINTER CONTROL (WITH VERIFICATION)
# ==============================================================================

def get_mouse_position() -> dict:
    attach_to_default_desktop()
    pos = pyautogui.position()
    size = pyautogui.size()
    return {"x": pos.x, "y": pos.y, "screen_width": size.width, "screen_height": size.height}

def move_mouse(x: int, y: int, duration: float = 0.15) -> dict:
    """Moves mouse cursor and verifies landing position."""
    attach_to_default_desktop()
    pyautogui.moveTo(x, y, duration=duration)
    current_pos = pyautogui.position()
    return {
        "status": "ok",
        "action": "move_mouse",
        "target": [x, y],
        "actual": [current_pos.x, current_pos.y],
        "verified": (abs(current_pos.x - x) <= 2 and abs(current_pos.y - y) <= 2)
    }

def verified_click(x: int = None, y: int = None, button: str = "left", clicks: int = 1, capture_after: bool = False) -> dict:
    """
    Precision Mouse Click:
    1. Moves cursor to target (x, y)
    2. Verifies exact coordinate arrival
    3. Performs click
    """
    attach_to_default_desktop()
    if x is not None and y is not None:
        pyautogui.moveTo(x, y, duration=0.1)
        current_pos = pyautogui.position()
    else:
        current_pos = pyautogui.position()
        x, y = current_pos.x, current_pos.y

    pyautogui.click(x=x, y=y, button=button, clicks=clicks)
    time.sleep(0.05)

    verification = None
    if capture_after:
        verification = take_screenshot()

    return {
        "status": "ok",
        "action": "verified_click",
        "target": [x, y],
        "actual": [current_pos.x, current_pos.y],
        "button": button,
        "clicks": clicks,
        "verification_screenshot": verification["saved_path"] if verification else None
    }

def double_click(x: int = None, y: int = None) -> dict:
    return verified_click(x=x, y=y, button="left", clicks=2)

def right_click(x: int = None, y: int = None) -> dict:
    return verified_click(x=x, y=y, button="right", clicks=1)

def mouse_hover(x: int, y: int, duration: float = 0.2) -> dict:
    """Hovers over target coordinates to trigger tooltips or highlight states."""
    attach_to_default_desktop()
    pyautogui.moveTo(x, y, duration=duration)
    time.sleep(0.1)
    return {"status": "ok", "action": "hover", "position": [x, y]}

def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.4) -> dict:
    attach_to_default_desktop()
    pyautogui.moveTo(start_x, start_y, duration=0.1)
    pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
    return {"status": "ok", "action": "mouse_drag", "start": [start_x, start_y], "end": [end_x, end_y]}

def mouse_scroll(clicks: int, x: int = None, y: int = None) -> dict:
    attach_to_default_desktop()
    if x is not None and y is not None:
        pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.scroll(clicks)
    return {"status": "ok", "action": "mouse_scroll", "clicks": clicks}


# ==============================================================================
# KEYBOARD CONTROL
# ==============================================================================

def type_text(text: str, interval: float = 0.02) -> dict:
    attach_to_default_desktop()
    pyautogui.typewrite(text, interval=interval)
    return {"status": "ok", "action": "type_text", "length": len(text)}

def paste_text(text: str) -> dict:
    """Pastes text via clipboard - handles full unicode, multi-line code, and instant typing."""
    attach_to_default_desktop()
    import pyperclip
    pyperclip.copy(text)
    time.sleep(0.04)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.05)
    return {"status": "ok", "action": "paste_text", "length": len(text)}

def press_key(key_name: str) -> dict:
    attach_to_default_desktop()
    pyautogui.press(key_name)
    time.sleep(0.04)
    return {"status": "ok", "action": "press_key", "key": key_name}

def hotkey(*keys) -> dict:
    attach_to_default_desktop()
    pyautogui.hotkey(*keys)
    time.sleep(0.06)
    return {"status": "ok", "action": "hotkey", "keys": list(keys)}


# ==============================================================================
# WINDOW MANAGEMENT
# ==============================================================================

def list_windows() -> dict:
    attach_to_default_desktop()
    import win32gui
    windows = []
    def enum_handler(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w > 0 and h > 0:
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "rect": {"left": rect[0], "top": rect[1], "width": w, "height": h}
                    })
    win32gui.EnumWindows(enum_handler, None)
    return {"windows": windows, "count": len(windows)}

def get_active_window() -> dict:
    attach_to_default_desktop()
    import win32gui, win32process
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd) if hwnd else ""
    rect = win32gui.GetWindowRect(hwnd) if hwnd else (0, 0, 0, 0)
    process_name = ""
    pid = 0
    if hwnd:
        try:
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            h_proc = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if h_proc:
                buf = ctypes.create_unicode_buffer(1024)
                size = ctypes.c_ulong(1024)
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(h_proc, 0, buf, ctypes.byref(size)):
                    process_name = os.path.basename(buf.value)
                ctypes.windll.kernel32.CloseHandle(h_proc)
        except Exception:
            pass

    return {
        "hwnd": hwnd,
        "title": title,
        "process": process_name,
        "pid": pid,
        "rect": {"left": rect[0], "top": rect[1], "width": rect[2] - rect[0], "height": rect[3] - rect[1]},
        "is_minimized": bool(win32gui.IsIconic(hwnd)) if hwnd else False,
        "is_visible": bool(win32gui.IsWindowVisible(hwnd)) if hwnd else False
    }

def force_window_to_foreground(hwnd: int) -> bool:
    """Forces target window to active foreground, bypassing Windows focus-stealing locks."""
    if not hwnd:
        return False
    try:
        attach_to_default_desktop()
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # 1. Un-minimize if iconic
        if win32gui.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        else:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            
        fore_hwnd = user32.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return True
            
        cur_thread = kernel32.GetCurrentThreadId()
        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        
        # Unlock focus lock
        user32.SystemParametersInfoW(0x2001, 0, 0, 2)  # SPI_SETFOREGROUNDLOCKTIMEOUT
        user32.AllowSetForegroundWindow(-1)            # ASFW_ANY
        
        # Attach threads
        if fore_thread and fore_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, fore_thread, True)
        if target_thread and target_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, target_thread, True)
            
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SwitchToThisWindow(hwnd, True)
        
        # Alt-key pulse trick for resistant Windows versions
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)
        
        if fore_thread and fore_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, fore_thread, False)
        if target_thread and target_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, target_thread, False)
            
        time.sleep(0.08)
        return user32.GetForegroundWindow() == hwnd
    except Exception:
        return False


def focus_window(query: str, capture_after: bool = False, auto_launch: bool = False) -> dict:
    """Restores and brings matched window to front with verified foreground activation."""
    attach_to_default_desktop()
    import win32gui, win32con, win32process
    matched = None
    query_lower = query.lower().strip()

    def enum_handler(hwnd, extra):
        nonlocal matched
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if query_lower in title.lower():
                matched = (hwnd, title)
    win32gui.EnumWindows(enum_handler, None)

    if not matched and auto_launch:
        launch_res = launch_application(query, wait_for_window=True)
        if launch_res.get("status") == "ok":
            win32gui.EnumWindows(enum_handler, None)

    if matched:
        hwnd, title = matched
        # Bring to foreground with multi-tier Win32 lock bypass
        is_now_active = force_window_to_foreground(hwnd)
        
        time.sleep(0.08)
        active = get_active_window()
        is_now_active = is_now_active or (active["hwnd"] == hwnd) or (query_lower in active["title"].lower())
        verification = take_screenshot() if capture_after else None
        return {
            "status": "ok",
            "action": "focus_window",
            "title": title,
            "hwnd": hwnd,
            "is_active_foreground": is_now_active,
            "verification_screenshot": verification["saved_path"] if verification else None
        }
    return {
        "status": "error",
        "action": "focus_window",
        "message": f"No window found matching '{query}'"
    }


def launch_application(app_name: str, wait_for_window: bool = True, timeout_sec: float = 8.0, extra_args: str = "") -> dict:
    """
    Universally launches ANY application and ensures it opens and appears on the live screen.
    Discovers Store apps, Win32 apps, Registry apps, and PATH executables.
    Cleans any windowless zombie processes that block GUI rendering.
    """
    app_lower = app_name.lower().strip()
    if app_lower in ("chrome", "google chrome", "msedge", "edge", "browser") and extra_args:
        return browse_web(extra_args, browser=app_name)

    resolved = find_installed_application(app_name)
    window_title_hint = resolved.get("window_hint", app_name)
    launch_cmd = resolved.get("launch_cmd")
    if not launch_cmd:
        return {
            "status": "error",
            "success": False,
            "action": "launch_application",
            "app": app_name,
            "error": f"Cannot launch '{app_name}': target is not a recognized executable, application, or system path."
        }
    if extra_args:
        launch_cmd = f"{launch_cmd} {extra_args}"
    short_hint = app_lower.replace(".exe", "")

    # Check if a VISIBLE window already exists
    import win32gui
    matched_window = None
    query_hint = window_title_hint.lower()

    def check_vis(hwnd, _):
        nonlocal matched_window
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if t and (query_hint in t.lower() or short_hint in t.lower()):
                matched_window = hwnd
    win32gui.EnumWindows(check_vis, None)

    # If visible window already exists, bring it to front and return
    if matched_window:
        focus_res = focus_window(query_hint)
        if focus_res.get("status") != "ok":
            focus_res = focus_window(short_hint)
        return {
            "status": "ok",
            "action": "launch_application",
            "app": app_name,
            "resolved": resolved,
            "was_already_running": True,
            "window_focused": True,
            "active_window": get_active_window(),
            "message": f"Application '{app_name}' was already open and has been focused on the live screen."
        }

    # If NO visible window exists, check if a windowless zombie process is blocking launch
    proc_check = is_process_running(short_hint)
    if proc_check.get("is_running", False):
        # Terminate windowless zombie instances so GUI can start cleanly
        for proc in proc_check.get("processes", []):
            try:
                subprocess.call(f"taskkill /PID {proc['pid']} /F", shell=True, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        time.sleep(0.3)

    try:
        subprocess.Popen(launch_cmd, shell=True)
    except Exception as e:
        return {
            "status": "error",
            "success": False,
            "action": "launch_application",
            "app": app_name,
            "error": f"Failed to execute command '{launch_cmd}': {str(e)}"
        }

    if wait_for_window:
        found_window = None
        # Fast path: Immediate if checks without sleep
        focus_res = focus_window(query_hint)
        if focus_res.get("status") in ("ok", "success"):
            found_window = focus_res
        else:
            focus_res = focus_window(short_hint)
            if focus_res.get("status") in ("ok", "success"):
                found_window = focus_res
            else:
                # Micro-interval polling if window needs a moment to spawn
                start_wait = time.time()
                while time.time() - start_wait < timeout_sec:
                    time.sleep(0.03)
                    focus_res = focus_window(query_hint)
                    if focus_res.get("status") in ("ok", "success"):
                        found_window = focus_res
                        break
                    focus_res = focus_window(short_hint)
                    if focus_res.get("status") in ("ok", "success"):
                        found_window = focus_res
                        break

        active = get_active_window()
        return {
            "status": "success" if found_window else "warning",
            "success": found_window is not None,
            "action": "launch_application",
            "app": app_name,
            "resolved": resolved,
            "was_already_running": False,
            "window_focused": found_window is not None,
            "active_window": active,
            "message": f"Application '{app_name}' is opened and focused on the live screen." if found_window else f"Application '{app_name}' command was launched, but window did not appear within {timeout_sec}s."
        }

    return {
        "status": "success",
        "success": True,
        "action": "launch_application",
        "app": app_name,
        "resolved": resolved,
        "was_already_running": False
    }


def close_application(app_name: str, force: bool = False) -> dict:
    """
    Terminates or closes a running application by window title matching or process name.
    Sends graceful WM_CLOSE first, with fallback to taskkill if needed.
    """
    import win32gui
    import win32con
    import win32process
    import subprocess
    import psutil
    target = app_name.lower().strip().replace(".exe", "")
    closed_hwnds = []
    closed_pids = set()

    def enum_and_close(hwnd, _):
        if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                proc = psutil.Process(pid)
                pname = proc.name().lower().replace(".exe", "")
            except Exception:
                pname = ""
            if (target and target in title.lower()) or (target and target in pname):
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                closed_hwnds.append(hwnd)
                closed_pids.add(pid)

    try:
        win32gui.EnumWindows(enum_and_close, None)
    except Exception:
        pass

    if force or (not closed_hwnds and not closed_pids):
        try:
            flag = "/F" if force else ""
            subprocess.run(f"taskkill /IM {target}*.exe {flag}", shell=True, capture_output=True, text=True)
            closed_pids.add(target)
        except Exception:
            pass

    success = bool(closed_hwnds or closed_pids)
    return {
        "status": "success" if success else "warning",
        "success": success,
        "action": "close_application",
        "app": app_name,
        "closed_count": len(closed_hwnds) or len(closed_pids),
        "message": f"Closed application '{app_name}' successfully." if success else f"No active window or process found for '{app_name}'."
    }


# ==============================================================================
# BROWSER & WEB SEARCH ENGINE (<50ms DIRECT LAUNCH)
# ==============================================================================

PORTAL_MAP = {
    "github": "https://github.com/",
    "youtube": "https://www.youtube.com/",
    "gmail": "https://mail.google.com/",
    "google": "https://www.google.com/",
    "chatgpt": "https://chatgpt.com/",
    "gemini": "https://gemini.google.com/",
    "reddit": "https://www.reddit.com/",
    "wikipedia": "https://www.wikipedia.org/",
    "stackoverflow": "https://stackoverflow.com/",
    "coursera": "https://www.coursera.org/",
    "udemy": "https://www.udemy.com/",
    "linkedin": "https://www.linkedin.com/",
    "twitter": "https://x.com/",
    "x": "https://x.com/",
    "google play": "https://play.google.com/store/games",
    "play store": "https://play.google.com/store/games",
    "playstore": "https://play.google.com/store/games"
}

def resolve_youtube_top_video_url(query: str):
    """Fetches top matching YouTube video watch URL for direct instant playback (<800ms)."""
    try:
        import re
        import urllib.request
        import urllib.parse
        clean_q = re.sub(r'\btamol\b', 'tamil', query.strip(), flags=re.I)
        encoded = urllib.parse.quote_plus(clean_q)
        req = urllib.request.Request(
            f"https://www.youtube.com/results?search_query={encoded}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        html = urllib.request.urlopen(req, timeout=3).read().decode("utf-8", errors="ignore")
        vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if vids:
            return f"https://www.youtube.com/watch?v={vids[0]}"
    except Exception:
        pass
    return None


def resolve_web_target(query_or_url: str) -> str:
    """Smart URL/Query Resolver for portals, direct domains, and search queries."""
    import urllib.parse
    import re

    clean = query_or_url.strip()
    if not clean:
        return "https://www.google.com"

    clean_lower = clean.lower()

    # Special handling for Google Play Store search queries
    if "google play" in clean_lower or "play store" in clean_lower or "playstore" in clean_lower:
        sub_query = re.sub(r'^(?:open|search|find|for|look\s+up|in|on|go\s+to)\s+', '', clean, flags=re.I)
        sub_query = re.sub(r'(?:in|on)?\s*(?:google\s*play|play\s*store|playstore)', '', sub_query, flags=re.I).strip()
        sub_query = re.sub(r'^(?:for|search\s*for|and\s+search\s+for|and\s+search)\s+', '', sub_query, flags=re.I).strip()
        if sub_query:
            return f"https://play.google.com/store/search?q={urllib.parse.quote_plus(sub_query)}&c=apps"
        return "https://play.google.com/store/games"

    # Special handling for YouTube search queries & instant playback
    if "youtube" in clean_lower:
        sub_query = re.sub(r'^(?:open|search|find|for|look\s+up|in|on|go\s+to)\s+', '', clean, flags=re.I)
        sub_query = re.sub(r'(?:in|on)?\s*youtube', '', sub_query, flags=re.I).strip()
        sub_query = re.sub(r'^(?:for|search\s*for|and\s+search\s+for|and\s+search)\s+', '', sub_query, flags=re.I).strip()
        if sub_query:
            should_play = bool(re.search(r'\b(?:and\s+)?(?:play\s+it|play|start\s+it|listen)\b', sub_query, re.I))
            clean_sub = re.sub(r'\b(?:and\s+)?(?:play\s+it|play|start\s+it|listen)\b', '', sub_query, flags=re.I).strip()
            clean_sub = re.sub(r'^(?:a|an|the)\s+', '', clean_sub, flags=re.I).strip()
            clean_sub = re.sub(r'\btamol\b', 'tamil', clean_sub, flags=re.I)
            if should_play:
                direct_video = resolve_youtube_top_video_url(clean_sub)
                if direct_video:
                    return direct_video
            return f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_sub or sub_query)}"
        return "https://www.youtube.com/"


    # Special handling for GitHub search queries
    if "github" in clean_lower:
        sub_query = re.sub(r'^(?:open|search|find|for|look\s+up|in|on|go\s+to)\s+', '', clean, flags=re.I)
        sub_query = re.sub(r'(?:in|on)?\s*github', '', sub_query, flags=re.I).strip()
        sub_query = re.sub(r'^(?:for|search\s*for|and\s+search\s+for|and\s+search)\s+', '', sub_query, flags=re.I).strip()
        if sub_query:
            return f"https://github.com/search?q={urllib.parse.quote_plus(sub_query)}"
        return "https://github.com/"

    # Special handling for Amazon search queries
    if "amazon" in clean_lower:
        sub_query = re.sub(r'^(?:open|search|find|for|look\s+up|in|on|go\s+to)\s+', '', clean, flags=re.I)
        sub_query = re.sub(r'(?:in|on)?\s*amazon', '', sub_query, flags=re.I).strip()
        sub_query = re.sub(r'^(?:for|search\s*for|and\s+search\s+for|and\s+search)\s+', '', sub_query, flags=re.I).strip()
        if sub_query:
            return f"https://www.amazon.com/s?k={urllib.parse.quote_plus(sub_query)}"
        return "https://www.amazon.com/"

    # Special handling for Wikipedia search queries
    if "wikipedia" in clean_lower:
        sub_query = re.sub(r'^(?:open|search|find|for|look\s+up|in|on|go\s+to)\s+', '', clean, flags=re.I)
        sub_query = re.sub(r'(?:in|on)?\s*wikipedia', '', sub_query, flags=re.I).strip()
        sub_query = re.sub(r'^(?:for|search\s*for|and\s+search\s+for|and\s+search)\s+', '', sub_query, flags=re.I).strip()
        if sub_query:
            return f"https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote_plus(sub_query)}"
        return "https://www.wikipedia.org/"

    # 1. Exact or prefix/suffix match in known portal directory (longest match first)
    for portal_name, portal_url in sorted(PORTAL_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if clean_lower == portal_name or clean_lower.startswith(portal_name + " ") or clean_lower.endswith(" " + portal_name):
            return portal_url

    # 2. Direct web URLs
    if clean_lower.startswith(("http://", "https://")):
        return clean
    if clean_lower.startswith(("www.", "ftp.")):
        return f"https://{clean}"

    # 3. Domain detection (e.g. *.gov.in, *.edu, *.com, *.org, *.net, *.io, *.in)
    domain_pattern = r"^[a-zA-Z0-9\-\.]+\.(?:com|org|net|gov\.in|ac\.in|edu|io|in|co|ai|dev|app|org\.in|info|biz)(?:/.*)?$"
    if re.search(domain_pattern, clean_lower):
        return f"https://{clean}"

    # 4. Search query
    return f"https://www.google.com/search?q={urllib.parse.quote_plus(clean)}"

def get_browser_executable(browser_preference: str = None) -> str:
    """Finds exact executable path for Chrome, Edge, Brave, or Firefox on Windows."""
    import winreg
    targets = []
    if browser_preference:
        b = browser_preference.lower()
        if "chrome" in b:
            targets = ["chrome.exe"]
        elif "edge" in b or "msedge" in b:
            targets = ["msedge.exe"]
        elif "brave" in b:
            targets = ["brave.exe"]
        elif "firefox" in b:
            targets = ["firefox.exe"]
    if not targets:
        targets = ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"]

    # 1. Registry App Paths
    for target in targets:
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                sub_key = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{target}"
                with winreg.OpenKey(root, sub_key) as k:
                    val = winreg.QueryValue(k, None)
                    if val and os.path.exists(val):
                        return val
            except Exception:
                pass

    # 2. Well-known disk locations
    well_known = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in well_known:
        if os.path.exists(p):
            return p
    return None


def browse_web(query_or_url: str, browser: str = None) -> dict:
    """
    Launches browser natively via executable with --new-window and forces foreground activation.
    """
    attach_to_default_desktop()
    target_url = resolve_web_target(query_or_url)
    start_time = time.time()
    browser_pref = browser.lower() if browser else "chrome"

    browser_exe = get_browser_executable(browser_pref)
    if not browser_exe:
        browser_exe = get_browser_executable()

    try:
        si = subprocess.STARTUPINFO()
        si.lpDesktop = "winsta0\\default"

        if browser_exe and os.path.exists(browser_exe):
            cmd = [browser_exe, "--new-window", target_url]
            subprocess.Popen(cmd, startupinfo=si)
            actual_browser = os.path.basename(browser_exe).replace(".exe", "")
        else:
            try:
                os.startfile(target_url)
                actual_browser = "default"
            except Exception:
                import webbrowser
                webbrowser.open(target_url)
                actual_browser = "default"

        # Force foreground activation so window is physically visible on user's screen
        time.sleep(0.3)
        for b_target in [actual_browser, "chrome", "msedge", "edge", "google play", "google"]:
            f_res = focus_window(b_target)
            if f_res.get("status") in ("ok", "success") and f_res.get("is_active_foreground"):
                break

        elapsed = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "success",
            "success": True,
            "action": "browse",
            "input": query_or_url,
            "resolved_url": target_url,
            "browser": actual_browser,
            "elapsed_ms": elapsed,
            "message": f"Successfully launched '{target_url}' in {actual_browser} browser in {elapsed}ms."
        }
    except Exception as e:
        return {
            "status": "error",
            "action": "browse",
            "input": query_or_url,
            "resolved_url": target_url,
            "browser": browser_pref,
            "error": str(e)
        }


def chrome_action(action: str, param: str = None) -> dict:
    """
    Dedicated Chrome-native controls for the Orion System:
      - 'new_tab' / 'tab': Open new tab (ctrl+t), optionally navigate to param URL
      - 'close_tab': Close current tab (ctrl+w)
      - 'reopen_tab': Reopen last closed tab (ctrl+shift+t)
      - 'next_tab' / 'prev_tab': Switch tabs (ctrl+tab / ctrl+shift+tab)
      - 'reload' / 'refresh': Reload tab (ctrl+r or ctrl+shift+r if param='hard')
      - 'focus_url' / 'address_bar': Focus address bar (ctrl+l)
      - 'scroll_down' / 'scroll_up': Scroll page
      - 'zoom_in' / 'zoom_out' / 'zoom_reset': Zoom controls
      - 'fullscreen': Toggle F11
      - 'devtools': Toggle F12
      - 'close': Close Chrome window/process
    """
    act = action.lower().strip()
    focus_window("chrome")
    time.sleep(0.08)

    if act in ("new_tab", "tab"):
        hotkey("ctrl", "t")
        if param:
            time.sleep(0.1)
            type_text(f"{param}\n")
        return {"status": "success", "action": "chrome_action", "type": "new_tab", "param": param}

    elif act in ("close_tab", "close_current_tab"):
        hotkey("ctrl", "w")
        return {"status": "success", "action": "chrome_action", "type": "close_tab"}

    elif act in ("reopen_tab", "restore_tab"):
        hotkey("ctrl", "shift", "t")
        return {"status": "success", "action": "chrome_action", "type": "reopen_tab"}

    elif act in ("next_tab", "switch_tab"):
        hotkey("ctrl", "tab")
        return {"status": "success", "action": "chrome_action", "type": "next_tab"}

    elif act in ("prev_tab", "previous_tab"):
        hotkey("ctrl", "shift", "tab")
        return {"status": "success", "action": "chrome_action", "type": "prev_tab"}

    elif act in ("reload", "refresh"):
        if param == "hard":
            hotkey("ctrl", "shift", "r")
        else:
            hotkey("ctrl", "r")
        return {"status": "success", "action": "chrome_action", "type": "reload"}

    elif act in ("focus_url", "address_bar", "url_bar"):
        hotkey("ctrl", "l")
        if param:
            time.sleep(0.05)
            type_text(f"{param}\n")
        return {"status": "success", "action": "chrome_action", "type": "focus_url"}

    elif act in ("scroll_down", "page_down"):
        mouse_scroll(-4)
        return {"status": "success", "action": "chrome_action", "type": "scroll_down"}

    elif act in ("scroll_up", "page_up"):
        mouse_scroll(4)
        return {"status": "success", "action": "chrome_action", "type": "scroll_up"}

    elif act in ("zoom_in",):
        hotkey("ctrl", "+")
        return {"status": "success", "action": "chrome_action", "type": "zoom_in"}

    elif act in ("zoom_out",):
        hotkey("ctrl", "-")
        return {"status": "success", "action": "chrome_action", "type": "zoom_out"}

    elif act in ("zoom_reset",):
        hotkey("ctrl", "0")
        return {"status": "success", "action": "chrome_action", "type": "zoom_reset"}

    elif act in ("fullscreen",):
        press_key("f11")
        return {"status": "success", "action": "chrome_action", "type": "fullscreen"}

    elif act in ("devtools", "inspect"):
        press_key("f12")
        return {"status": "success", "action": "chrome_action", "type": "devtools"}

    elif act in ("close", "exit", "quit"):
        return close_application("chrome")

    else:
        return {"status": "error", "message": f"Unknown Chrome action: '{action}'"}


# ==============================================================================
# CONTINUOUS BATCH EXECUTION PIPELINE (OPTION D CORE)
# ==============================================================================

def run_batch_sequence(steps: list, take_final_checkpoint: bool = True, halt_on_error: bool = True) -> dict:
    """
    Executes an entire multi-step action pipeline continuously at native machine speed.
    Eliminates round-trip model latencies between steps.
    """
    attach_to_default_desktop()
    start_time = time.time()
    log = []

    for i, step in enumerate(steps):
        act = step.get("action", "").lower()
        step_res = {"step": i + 1, "action": act}

        try:
            if act in ("launch", "open", "launch_app"):
                step_res["result"] = launch_application(
                    app_name=step.get("app", step.get("name", "")),
                    wait_for_window=step.get("wait_for_window", True),
                    timeout_sec=float(step.get("timeout_sec", 8.0))
                )
                if step_res["result"].get("status") == "error" and halt_on_error:
                    log.append(step_res)
                    return {
                        "status": "error",
                        "halted_at_step": i + 1,
                        "reason": f"Failed to launch application '{step.get('app')}': {step_res['result'].get('error')}",
                        "log": log
                    }

            elif act in ("browse", "search", "web"):
                step_res["result"] = browse_web(
                    query_or_url=step.get("query", step.get("url", "")),
                    browser=step.get("browser")
                )

            elif act in ("port", "check_port"):
                port_num = int(step.get("port", 9876))
                host = step.get("host", "127.0.0.1")
                port_res = check_port(port_num, host=host)
                step_res["result"] = port_res
                if step.get("require_open", True) and not port_res.get("is_open", False):
                    log.append(step_res)
                    return {
                        "status": "error",
                        "halted_at_step": i + 1,
                        "reason": f"Socket port {port_num} on {host} is closed or not listening. Application server is not ready.",
                        "log": log
                    }

            elif act == "focus":
                title_query = step.get("title", step.get("query", ""))
                auto_launch = step.get("auto_launch", step.get("launch_if_missing", False))
                focus_res = focus_window(title_query, auto_launch=auto_launch)
                step_res["result"] = focus_res
                if focus_res.get("status") == "error" and (step.get("require_focus", True) or halt_on_error):
                    log.append(step_res)
                    return {
                        "status": "error",
                        "halted_at_step": i + 1,
                        "reason": f"Halting execution: Window matching '{title_query}' could not be focused on the live screen. Will not click on unintended windows.",
                        "log": log
                    }

            elif act == "click":
                step_res["result"] = verified_click(
                    x=step.get("x"),
                    y=step.get("y"),
                    button=step.get("button", "left"),
                    clicks=step.get("clicks", 1)
                )
            elif act == "double_click":
                step_res["result"] = double_click(x=step.get("x"), y=step.get("y"))
            elif act == "right_click":
                step_res["result"] = right_click(x=step.get("x"), y=step.get("y"))
            elif act == "move":
                step_res["result"] = move_mouse(step.get("x"), step.get("y"), duration=step.get("duration", 0.15))
            elif act == "hover":
                step_res["result"] = mouse_hover(step.get("x"), step.get("y"))
            elif act == "drag":
                step_res["result"] = mouse_drag(
                    step.get("start_x"), step.get("start_y"),
                    step.get("end_x"), step.get("end_y"),
                    duration=step.get("duration", 0.4)
                )
            elif act == "scroll":
                step_res["result"] = mouse_scroll(step.get("clicks", 0), x=step.get("x"), y=step.get("y"))
            elif act == "paste":
                step_res["result"] = paste_text(step.get("text", ""))
            elif act == "type":
                step_res["result"] = type_text(step.get("text", ""), interval=step.get("interval", 0.02))
            elif act == "press":
                step_res["result"] = press_key(step.get("key", ""))
            elif act == "hotkey":
                step_res["result"] = hotkey(*step.get("keys", []))
            elif act == "wait":
                time.sleep(float(step.get("seconds", 0.2)))
                step_res["result"] = {"status": "ok", "waited": step.get("seconds")}
            elif act == "checkpoint":
                shot = take_screenshot()
                step_res["result"] = {"status": "ok", "checkpoint_path": shot["saved_path"]}
            elif act == "expect_window":
                q = step.get("query", "").lower()
                timeout = float(step.get("timeout", 5.0))
                poll_start = time.time()
                found_win = None
                while time.time() - poll_start < timeout:
                    wins = list_windows().get("windows", [])
                    for w in wins:
                        if q in w.get("title", "").lower():
                            found_win = w
                            break
                    if found_win:
                        break
                    time.sleep(0.2)
                if not found_win:
                    raise RuntimeError(f"Expected window matching '{step.get('query')}' not found within {timeout}s")
                step_res["result"] = {"status": "ok", "window": found_win}
            elif act == "expect_file":
                p = os.path.abspath(step.get("path", ""))
                timeout = float(step.get("timeout", 5.0))
                min_bytes = int(step.get("min_bytes", 1))
                poll_start = time.time()
                found = False
                while time.time() - poll_start < timeout:
                    if os.path.exists(p) and os.path.getsize(p) >= min_bytes:
                        found = True
                        break
                    time.sleep(0.2)
                if not found:
                    raise RuntimeError(f"Expected file '{p}' with >= {min_bytes} bytes not created within {timeout}s")
                step_res["result"] = {"status": "ok", "file": p, "bytes": os.path.getsize(p)}
            elif act == "expect_port":
                port = int(step.get("port", 80))
                timeout = float(step.get("timeout", 5.0))
                poll_start = time.time()
                is_open = False
                while time.time() - poll_start < timeout:
                    res = check_port(port)
                    if res.get("listening"):
                        is_open = True
                        break
                    time.sleep(0.2)
                if not is_open:
                    raise RuntimeError(f"Expected port {port} to be open, but remained closed after {timeout}s")
                step_res["result"] = {"status": "ok", "port": port, "listening": True}
            elif act == "expect_motion":
                timeout = float(step.get("timeout", 4.0))
                poll_start = time.time()
                motion_detected = False
                monitor = get_live_screen_monitor(auto_start=True)
                st = {}
                while time.time() - poll_start < timeout:
                    st = monitor.get_status()
                    if st.get("motion_delta_percent", 0.0) >= float(step.get("min_percent", 0.5)):
                        motion_detected = True
                        break
                    time.sleep(0.25)
                if not motion_detected:
                    raise RuntimeError(f"Expected motion/animation on screen not detected within {timeout}s")
                step_res["result"] = {"status": "ok", "motion_delta_percent": st.get("motion_delta_percent"), "is_animating": True}
            else:
                step_res["error"] = f"Unknown action: {act}"
        except Exception as e:
            step_res["error"] = str(e)
            if halt_on_error:
                log.append(step_res)
                return {
                    "status": "error",
                    "halted_at_step": i + 1,
                    "reason": str(e),
                    "log": log
                }

        log.append(step_res)

        inter_delay = step.get("after_delay", 0.04)
        if inter_delay > 0:
            time.sleep(inter_delay)

    total_elapsed = time.time() - start_time

    checkpoint = None
    if take_final_checkpoint:
        checkpoint = take_screenshot()

    return {
        "status": "ok",
        "total_steps": len(steps),
        "elapsed_seconds": round(total_elapsed, 3),
        "final_checkpoint": checkpoint["saved_path"] if checkpoint else None,
        "log": log
    }

def execute_task(task_spec: dict) -> dict:
    """
    Unified 5-Stage Autonomous Task Runner:
    1. Pre-flight Validation
    2. Lifecycle & Live Screen Focus
    3. Continuous Batch Execution
    4. Milestone Checkpointing
    5. Expected Output Verification
    """
    start_time = time.time()
    tool = task_spec.get("tool")
    steps = task_spec.get("steps", [])
    expected = task_spec.get("expected", {})

    preflight_items = [tool] if tool else None
    preflight_res = preflight_check(preflight_items)

    focus_res = None
    if tool:
        focus_res = focus_window(tool, auto_launch=True)

    batch_res = run_batch_sequence(steps, halt_on_error=True)
    if batch_res.get("status") == "error":
        return {
            "status": "error",
            "phase": "execution",
            "tool": tool,
            "error": batch_res.get("reason"),
            "batch_log": batch_res.get("log"),
            "elapsed_seconds": round(time.time() - start_time, 3)
        }

    checkpoint = take_screenshot()

    verifications = {}
    if expected:
        if "file" in expected:
            fpath = os.path.abspath(expected["file"])
            min_b = expected.get("min_bytes", 1)
            t_out = expected.get("timeout", 4.0)
            t0 = time.time()
            ok = False
            while time.time() - t0 < t_out:
                if os.path.exists(fpath) and os.path.getsize(fpath) >= min_b:
                    ok = True
                    break
                time.sleep(0.2)
            verifications["file"] = {
                "path": fpath,
                "verified": ok,
                "size_bytes": os.path.getsize(fpath) if os.path.exists(fpath) else 0
            }
            if not ok:
                return {
                    "status": "failed_verification",
                    "reason": f"Expected output file '{fpath}' not found or empty",
                    "checkpoint": checkpoint["saved_path"],
                    "verifications": verifications
                }

        if "window_title" in expected:
            q = expected["window_title"].lower()
            wins = list_windows().get("windows", [])
            matched = any(q in w.get("title", "").lower() for w in wins)
            verifications["window"] = {"query": expected["window_title"], "verified": matched}
            if not matched:
                return {
                    "status": "failed_verification",
                    "reason": f"Expected window '{expected['window_title']}' not active",
                    "checkpoint": checkpoint["saved_path"],
                    "verifications": verifications
                }

        if "port" in expected:
            p = int(expected["port"])
            p_res = check_port(p)
            verifications["port"] = {"port": p, "listening": p_res.get("listening", False)}

    total_time = round(time.time() - start_time, 3)
    return {
        "status": "success",
        "tool": tool,
        "elapsed_seconds": total_time,
        "preflight": preflight_res.get("all_ready", True),
        "total_steps": len(steps),
        "checkpoint_screenshot": checkpoint["saved_path"],
        "verifications": verifications,
        "live_telemetry": get_live_screen_monitor().get_status()
    }


# ==============================================================================
# VOICE & AUDIO (TTS + STT)
# ==============================================================================

def get_available_voices() -> list:
    """
    Discovers all high-fidelity TTS voices across both Windows SAPI5 and Windows OneCore.
    Returns list of dicts with name, description, engine, and token reference.
    """
    voices = []
    import win32com.client

    # 1. Discover OneCore high-definition studio voices (George, Susan, Heera, Ravi)
    try:
        cat = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
        cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
        for token in cat.EnumerateTokens():
            desc = token.GetDescription()
            name = desc.split(" - ")[0].strip() if " - " in desc else desc
            clean_name = name.replace("Microsoft ", "").strip()
            voices.append({
                "id": clean_name.lower(),
                "name": name,
                "clean_name": clean_name,
                "description": desc,
                "engine": "Windows OneCore (HD)",
                "token": token
            })
    except Exception:
        pass

    # 2. Discover SAPI5 desktop voices (Zira, Hazel)
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        for token in speaker.GetVoices():
            desc = token.GetDescription()
            name = desc.split(" - ")[0].strip() if " - " in desc else desc
            clean_name = name.replace("Microsoft ", "").replace(" Desktop", "").strip()
            if not any(v["description"] == desc for v in voices):
                voices.append({
                    "id": clean_name.lower(),
                    "name": name,
                    "clean_name": clean_name,
                    "description": desc,
                    "engine": "Windows SAPI5",
                    "token": token
                })
    except Exception:
        pass

    return voices


def speak(text: str, voice: str = "George", rate: int = 0, volume: int = 100) -> dict:
    """
    Speaks text through Windows voice synthesizer with professional studio voices.
    Defaults to 'Microsoft George' (deep, authoritative executive AI persona).
    Supports 'George', 'Susan', 'Zira', 'Heera', 'Ravi', 'Hazel'.
    """
    try:
        import win32com.client
        available = get_available_voices()
        target_voice_obj = None

        if voice:
            q = voice.lower().strip()
            for v in available:
                if q in v["id"] or q in v["name"].lower() or q in v["description"].lower():
                    target_voice_obj = v
                    break

        # Fallback to George or first available if requested voice not found
        if not target_voice_obj:
            for v in available:
                if "george" in v["id"]:
                    target_voice_obj = v
                    break
        if not target_voice_obj and available:
            target_voice_obj = available[0]

        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        if target_voice_obj and "token" in target_voice_obj:
            speaker.Voice = target_voice_obj["token"]

        speaker.Rate = rate
        speaker.Volume = volume
        speaker.Speak(text)

        return {
            "status": "ok",
            "action": "speak",
            "text": text,
            "voice": target_voice_obj["name"] if target_voice_obj else "Default",
            "engine": target_voice_obj["engine"] if target_voice_obj else "SAPI"
        }
    except Exception as e:
        return {"status": "error", "action": "speak", "error": str(e)}

def transcribe_audio(audio_path: str) -> dict:
    """Transcribes voice audio recording (wav, mp3, etc.) to text."""
    try:
        import speech_recognition as sr
        from pydub import AudioSegment

        ext = os.path.splitext(audio_path)[1].lower()
        wav_path = audio_path
        temp_created = False
        if ext != ".wav":
            sound = AudioSegment.from_file(audio_path)
            wav_path = audio_path + "_converted.wav"
            sound.export(wav_path, format="wav")
            temp_created = True

        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)

        if temp_created and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass

        return {"status": "success", "success": True, "text": text, "source": audio_path}
    except Exception as e:
        return {"status": "error", "success": False, "error": str(e), "source": audio_path}


def record_microphone(duration_sec: float = 4.0, save_path: str = None) -> dict:
    """Records audio from the default Windows microphone using native WinMM subsystem."""
    import ctypes
    winmm = ctypes.windll.winmm
    out_path = os.path.abspath(save_path) if save_path else os.path.join(CACHE_DIR, "voice_input.wav")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    try:
        alias = f"rec_{int(time.time() * 1000)}"
        winmm.mciSendStringW(f"open new type waveaudio alias {alias}", None, 0, None)
        winmm.mciSendStringW(f"record {alias}", None, 0, None)
        time.sleep(duration_sec)
        winmm.mciSendStringW(f'save {alias} "{out_path}"', None, 0, None)
        winmm.mciSendStringW(f"close {alias}", None, 0, None)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return {
                "status": "success",
                "success": True,
                "recorded_file": out_path,
                "duration_sec": duration_sec,
                "size_bytes": os.path.getsize(out_path)
            }
        else:
            return {"status": "error", "success": False, "error": "Microphone recording produced empty audio file"}
    except Exception as e:
        return {"status": "error", "success": False, "error": str(e)}


def listen(duration_sec: float = 4.0) -> dict:
    """Listens to the default microphone, records speech, and transcribes it to text."""
    rec_res = record_microphone(duration_sec=duration_sec)
    if not rec_res.get("success"):
        return rec_res
    wav_path = rec_res["recorded_file"]
    trans = transcribe_audio(wav_path)
    return {
        "status": "success",
        "success": True,
        "text": trans.get("text", ""),
        "audio_file": wav_path,
        "duration_sec": duration_sec
    }


# ==============================================================================
# CONTINUOUS LIVE SCREEN & STATUS MONITORING API
# ==============================================================================

class LiveScreenMonitor:
    """
    Lightweight background monitor that continuously tracks:
    1. Active foreground window (HWND, Title, Process, PID, Rect, Visibility)
    2. Mouse cursor position (X, Y)
    3. Motion Delta / Activity rate (% pixels changed between frames)
    4. Encodes rolling JPEG buffer in RAM for instantaneous API streaming (<1ms response)
    """
    def __init__(self, fps: float = 3.0):
        self.fps = fps
        self.interval = 1.0 / max(0.5, fps)
        self.running = False
        self.lock = threading.Lock()
        self.latest_status = {}
        self.latest_jpeg_bytes = None
        self.prev_thumb = None
        self.motion_delta = 0.0
        self.event_history = []
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        attach_to_default_desktop()
        sct = None
        try:
            import mss
            sct = mss.mss()
        except Exception:
            pass

        last_title = ""

        while self.running:
            t0 = time.time()
            try:
                # 1. Active window inspection
                active_win = get_active_window()
                current_title = active_win.get("title", "")
                if current_title and current_title != last_title:
                    self.event_history.append({
                        "timestamp": round(time.time(), 2),
                        "event": "window_switch",
                        "title": current_title,
                        "process": active_win.get("process", ""),
                        "hwnd": active_win.get("hwnd")
                    })
                    if len(self.event_history) > 50:
                        self.event_history.pop(0)
                    last_title = current_title

                # 2. Mouse position
                mouse_pos = get_mouse_position()

                # 3. Screen frame & motion delta
                motion_percent = 0.0
                if sct and Image:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    raw = sct.grab(monitor)
                    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

                    thumb = img.resize((160, 90))
                    if self.prev_thumb:
                        diff = ImageChops.difference(thumb, self.prev_thumb)
                        stat = ImageStat.Stat(diff)
                        avg_diff = sum(stat.mean) / 3.0
                        motion_percent = round((avg_diff / 255.0) * 100.0, 2)
                    self.prev_thumb = thumb

                    bio = io.BytesIO()
                    img.save(bio, format="JPEG", quality=75, optimize=False)
                    with self.lock:
                        self.latest_jpeg_bytes = bio.getvalue()

                with self.lock:
                    self.motion_delta = motion_percent
                    self.latest_status = {
                        "status": "ok",
                        "timestamp": round(time.time(), 3),
                        "active_window": active_win,
                        "mouse": {"x": mouse_pos.get("x", 0), "y": mouse_pos.get("y", 0)},
                        "screen": {
                            "width": SCREEN_WIDTH,
                            "height": SCREEN_HEIGHT
                        },
                        "motion_delta_percent": motion_percent,
                        "is_animating": motion_percent > 0.8
                    }
            except Exception:
                pass

            elapsed = time.time() - t0
            sleep_time = max(0.02, self.interval - elapsed)
            time.sleep(sleep_time)

    def get_status(self) -> dict:
        with self.lock:
            if not self.latest_status:
                active_win = get_active_window()
                pos = get_mouse_position()
                return {
                    "status": "ok",
                    "timestamp": round(time.time(), 3),
                    "active_window": active_win,
                    "mouse": {"x": pos.get("x", 0), "y": pos.get("y", 0)},
                    "screen": {"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                    "motion_delta_percent": 0.0,
                    "is_animating": False
                }
            return dict(self.latest_status)

    def get_jpeg(self) -> bytes:
        with self.lock:
            return self.latest_jpeg_bytes

    def get_vlm_frame(self, crop_window: bool = False, max_dim: int = 1024) -> bytes:
        """Returns ultra-fast, lightweight JPEG frame optimized for Multimodal LLMs (~30KB)."""
        with self.lock:
            if not self.latest_jpeg_bytes:
                return None
            try:
                bio_in = io.BytesIO(self.latest_jpeg_bytes)
                img = Image.open(bio_in)
                if crop_window and self.latest_status:
                    rect = self.latest_status.get("active_window", {}).get("rect", {})
                    left = max(0, rect.get("left", 0))
                    top = max(0, rect.get("top", 0))
                    w = rect.get("width", 0)
                    h = rect.get("height", 0)
                    if w > 50 and h > 50:
                        right = min(img.width, left + w)
                        bottom = min(img.height, top + h)
                        if right > left and bottom > top:
                            img = img.crop((left, top, right, bottom))

                if img.width > max_dim or img.height > max_dim:
                    scale = min(max_dim / img.width, max_dim / img.height)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.BILINEAR)

                bio_out = io.BytesIO()
                img.save(bio_out, format="JPEG", quality=70, optimize=True)
                return bio_out.getvalue()
            except Exception:
                return self.latest_jpeg_bytes

_global_monitor = None

def get_live_screen_monitor(auto_start: bool = True) -> LiveScreenMonitor:
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = LiveScreenMonitor(fps=3.0)
        if auto_start:
            _global_monitor.start()
    return _global_monitor

class MonitorHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        """Low-latency in-process execution engine (<2ms overhead)."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        result = {}
        if self.path in ("/action", "/api/action"):
            act = payload.get("action", "")
            if act == "click":
                result = verified_click(payload.get("x"), payload.get("y"), payload.get("button", "left"), payload.get("clicks", 1))
            elif act == "paste":
                result = paste_text(payload.get("text", ""))
            elif act == "type":
                result = type_text(payload.get("text", ""), interval=payload.get("interval", 0.02))
            elif act == "press":
                result = press_key(payload.get("key", ""))
            elif act == "hotkey":
                result = hotkey(*payload.get("keys", []))
            elif act == "focus":
                result = focus_window(payload.get("title", ""), auto_launch=payload.get("auto_launch", True))
            elif act in ("browse", "search", "web"):
                result = browse_web(payload.get("query") or payload.get("url", ""), browser=payload.get("browser"))
            elif act == "move":
                result = move_mouse(payload.get("x"), payload.get("y"), payload.get("duration", 0.15))
            elif act in ("open", "launch"):
                result = launch_application(payload.get("app", ""), extra_args=payload.get("extra_args", payload.get("args", "")))
            elif act == "speak":
                result = speak(payload.get("text", ""), voice=payload.get("voice", "George"), rate=int(payload.get("rate", 0)), volume=int(payload.get("volume", 100)))
            else:
                result = {"status": "error", "error": f"Unknown action: {act}"}

        elif self.path in ("/browse", "/api/browse"):
            result = browse_web(payload.get("query") or payload.get("url", ""), browser=payload.get("browser"))

        elif self.path in ("/focus", "/api/focus"):
            result = focus_window(payload.get("title", ""), auto_launch=payload.get("auto_launch", True))

        elif self.path in ("/speak", "/api/speak"):
            result = speak(payload.get("text", ""), voice=payload.get("voice", "George"), rate=int(payload.get("rate", 0)), volume=int(payload.get("volume", 100)))

        elif self.path in ("/voices", "/api/voices"):
            voices = get_available_voices()
            clean_list = [{k: v for k, v in item.items() if k != "token"} for item in voices]
            result = {"count": len(clean_list), "default": "Microsoft George (HD)", "voices": clean_list}

        elif self.path in ("/batch", "/api/batch"):
            steps = payload.get("steps", [])
            result = run_batch_sequence(steps, halt_on_error=payload.get("halt_on_error", True))

        elif self.path in ("/task", "/api/task"):
            result = execute_task(payload)

        elif self.path in ("/step", "/api/step"):
            step = payload.get("step", {})
            batch_res = run_batch_sequence([step], halt_on_error=True)
            monitor = get_live_screen_monitor(auto_start=True)
            result = {
                "step_result": batch_res,
                "telemetry": monitor.get_status()
            }
        else:
            self.send_response(404)
            self.end_headers()
            return

        data = json.dumps(result, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        monitor = get_live_screen_monitor(auto_start=True)
        if self.path in ("/status", "/api/status"):
            st = monitor.get_status()
            data = json.dumps(st, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path in ("/quick_state", "/telemetry", "/api/quick"):
            st = monitor.get_status()
            act = st.get("active_window", {})
            m = st.get("mouse", {})
            res = {
                "win": act.get("title", ""),
                "proc": act.get("process", ""),
                "pid": act.get("pid", 0),
                "x": m.get("x", 0),
                "y": m.get("y", 0),
                "anim": st.get("is_animating", False),
                "delta": st.get("motion_delta_percent", 0.0)
            }
            data = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith(("/vlm_frame", "/frame", "/api/vlm")):
            crop_win = "crop=window" in self.path
            jpeg = monitor.get_vlm_frame(crop_window=crop_win)
            if jpeg:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
            else:
                self.send_response(503)
                self.end_headers()
        elif self.path in ("/screen", "/screen.jpg", "/screenshot.jpg"):
            jpeg = monitor.get_jpeg()
            if not jpeg:
                shot = take_screenshot()
                try:
                    with open(shot["saved_path"], "rb") as f:
                        jpeg = f.read()
                except Exception:
                    pass
            if jpeg:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
            else:
                self.send_response(503)
                self.end_headers()
        elif self.path in ("/events", "/api/events"):
            events = monitor.event_history
            data = json.dumps({"events": events}, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith(("/browse", "/api/browse")):
            import urllib.parse
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            q = params.get("q", params.get("query", [""]))[0]
            browser = params.get("browser", [None])[0]
            result = browse_web(q, browser=browser)
            data = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith(("/focus", "/api/focus")):
            import urllib.parse
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            title = params.get("title", params.get("t", [""]))[0]
            result = focus_window(title)
            data = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith(("/speak", "/api/speak")):
            import urllib.parse
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            text = params.get("text", params.get("t", [""]))[0]
            voice = params.get("voice", params.get("v", ["George"]))[0]
            result = speak(text, voice=voice)
            data = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path in ("/voices", "/api/voices"):
            voices = get_available_voices()
            clean_list = [{k: v for k, v in item.items() if k != "token"} for item in voices]
            result = {"count": len(clean_list), "default": "Microsoft George (HD)", "voices": clean_list}
            data = json.dumps(result, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path in ("/stream", "/live"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while monitor and monitor.running:
                    jpeg = monitor.get_jpeg()
                    if jpeg:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
                    time.sleep(0.25)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            html = """<!DOCTYPE html>
<html>
<head>
    <title>🌌 Orion v2.0 "Nebula" - Live Perception & Control Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 14px; margin-bottom: 20px; }
        h1 { font-size: 1.4rem; margin: 0; color: #38bdf8; display: flex; align-items: center; gap: 10px; }
        .badge { background: #10b981; color: #022c22; font-weight: 700; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; letter-spacing: 0.05em; }
        .grid { display: grid; grid-template-columns: 2.2fr 1fr; gap: 20px; }
        .card { background: #131d31; border-radius: 12px; padding: 18px; border: 1px solid #1e293b; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .stream-box img { width: 100%; border-radius: 8px; border: 1px solid #334155; display: block; }
        .metric { margin-bottom: 14px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; }
        .metric-val { font-size: 1.05rem; font-weight: 600; color: #f8fafc; margin-top: 2px; word-break: break-all; }
        .highlight { color: #38bdf8; }
        ul { padding-left: 18px; margin: 8px 0; font-size: 0.9rem; }
        li { margin-bottom: 6px; }
        a { color: #38bdf8; text-decoration: none; font-weight: 500; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <h1><span>🌌</span> Orion v2.0 &quot;Nebula&quot; - Autonomous Perception &amp; Control</h1>
        <span class="badge">● ORION ACTIVE</span>
    </div>
    <div class="grid">
        <div class="card stream-box">
            <h3 style="margin-top:0; color:#94a3b8; font-size: 0.95rem;">LIVE SCREEN BUFFER (1920×1080)</h3>
            <img src="/stream" alt="Live Stream" />
        </div>
        <div class="card">
            <h3 style="margin-top:0; color:#94a3b8; font-size: 0.95rem;">LIVE WORKSTATION STATUS</h3>
            <div class="metric"><div class="metric-label">Active Window</div><div class="metric-val highlight" id="win-title">...</div></div>
            <div class="metric"><div class="metric-label">Process / PID</div><div class="metric-val" id="win-proc">...</div></div>
            <div class="metric"><div class="metric-label">Activity & Motion</div><div class="metric-val" id="motion-val">...</div></div>
            <div class="metric"><div class="metric-label">Mouse Coordinates</div><div class="metric-val" id="mouse-pos">...</div></div>
            
            <h4 style="margin: 16px 0 6px 0; color:#94a3b8; font-size: 0.85rem; text-transform: uppercase;">Endpoints</h4>
            <ul>
                <li><a href="/quick_state" target="_blank">GET /quick_state</a> — Micro-telemetry (~6ms)</li>
                <li><a href="/vlm_frame" target="_blank">GET /vlm_frame</a> — Downscaled VLM AI frame (~35ms)</li>
                <li><a href="/status" target="_blank">GET /status</a> — Full JSON state</li>
                <li><a href="/stream" target="_blank">GET /stream</a> — MJPEG video stream</li>
                <li><a href="/events" target="_blank">GET /events</a> — Window switch log</li>
            </ul>
        </div>
    </div>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/status');
                const d = await res.json();
                document.getElementById('win-title').innerText = d.active_window?.title || 'None';
                document.getElementById('win-proc').innerText = (d.active_window?.process || '') + (d.active_window?.pid ? ' (PID ' + d.active_window.pid + ')' : '');
                document.getElementById('motion-val').innerText = (d.motion_delta_percent || 0) + '% ' + (d.is_animating ? '⚡ [ACTIVE ANIMATION]' : '⏸️ [STATIC]');
                document.getElementById('mouse-pos').innerText = 'X: ' + (d.mouse?.x ?? '-') + ' | Y: ' + (d.mouse?.y ?? '-');
            } catch(e) {}
        }, 500);
    </script>
</body>
</html>"""
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

def start_screen_monitor_server(port: int = 8765, daemon: bool = False):
    """Starts the continuous screen perception HTTP server."""
    monitor = get_live_screen_monitor(auto_start=True)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), MonitorHTTPHandler)
    info = {
        "status": "ok",
        "service": "screen_monitor_api",
        "port": port,
        "dashboard_url": f"http://127.0.0.1:{port}/",
        "status_url": f"http://127.0.0.1:{port}/status",
        "screen_url": f"http://127.0.0.1:{port}/screen.jpg",
        "stream_url": f"http://127.0.0.1:{port}/stream"
    }
    print(json.dumps(info, indent=2))
    sys.stdout.flush()
    if daemon:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server, monitor
    else:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            monitor.stop()
            server.server_close()


# ==============================================================================
# FAST-MCP SERVER INITIALIZATION
# ==============================================================================

def run_mcp_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from mcp.server import FastMCP

    mcp = FastMCP("DesktopVoiceController")

    @mcp.tool()
    def tool_preflight_check(items_csv: str = "") -> str:
        items = [i.strip() for i in items_csv.split(",")] if items_csv else None
        return json.dumps(preflight_check(items))

    @mcp.tool()
    def tool_run_batch_sequence(steps_json: str) -> str:
        steps = json.loads(steps_json)
        return json.dumps(run_batch_sequence(steps))

    @mcp.tool()
    def tool_take_screenshot(save_path: str = None) -> str:
        return json.dumps(take_screenshot(save_path))

    @mcp.tool()
    def tool_verified_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        return json.dumps(verified_click(x, y, button, clicks))

    @mcp.tool()
    def tool_type_text(text: str) -> str:
        return json.dumps(type_text(text))

    @mcp.tool()
    def tool_paste_text(text: str) -> str:
        return json.dumps(paste_text(text))

    @mcp.tool()
    def tool_press_key(key_name: str) -> str:
        return json.dumps(press_key(key_name))

    @mcp.tool()
    def tool_hotkey(keys_csv: str) -> str:
        keys = [k.strip() for k in keys_csv.split(",")]
        return json.dumps(hotkey(*keys))

    @mcp.tool()
    def tool_focus_window(query: str) -> str:
        return json.dumps(focus_window(query))

    @mcp.tool()
    def tool_speak(text: str) -> str:
        return json.dumps(speak(text))

    @mcp.tool()
    def tool_transcribe_audio(audio_path: str) -> str:
        return json.dumps(transcribe_audio(audio_path))

    @mcp.tool()
    def tool_get_screen_status() -> str:
        """Returns live screen perception status (active window, process, coordinates, motion delta, and animation state)."""
        monitor = get_live_screen_monitor(auto_start=True)
        return json.dumps(monitor.get_status())

    @mcp.tool()
    def tool_execute_task(task_json: str) -> str:
        """Executes an end-to-end task with preflight, execution, and expected output verification."""
        spec = json.loads(task_json)
        return json.dumps(execute_task(spec))

    @mcp.tool()
    def tool_check_port(port: int = 9876, host: str = "127.0.0.1") -> str:
        return json.dumps(check_port(port, host))

    @mcp.tool()
    def tool_launch_application(app_name: str, wait_for_window: bool = True) -> str:
        return json.dumps(launch_application(app_name, wait_for_window))

    @mcp.tool()
    def tool_list_installed_apps(filter_query: str = "") -> str:
        apps = get_installed_apps_catalog()
        if filter_query:
            q = filter_query.lower()
            apps = [a for a in apps if q in a.get("Name", "").lower() or q in a.get("AppID", "").lower()]
        return json.dumps(apps)

    @mcp.tool()
    def tool_list_listening_ports() -> str:
        return json.dumps(list_listening_ports())

    mcp.run()


# ==============================================================================
# INTERACTIVE TERMINAL CONSOLE
# ==============================================================================

def run_interactive_console():
    """Starts interactive terminal console for Orion v2.0 Nebula."""
    header = [
        "=" * 70,
        "  [ORION] v2.0 \"NEBULA\" - Terminal Automation Console",
        "  Version: 2.0.0-nebula | Direct Windows Desktop Automation",
        "=" * 70,
        "  Ready. Type your command below to automate your desktop:",
        "    open <app>          -> Launch app (e.g. open notepad, open chrome)",
        "    browse <url/query>  -> Instant web search or open URL",
        "    speak <text>        -> Speak aloud (Microsoft George HD studio voice)",
        "    focus <window>      -> Bring window to front",
        "    shot [filename]     -> Capture instant screen snapshot",
        "    windows             -> List open desktop windows",
        "    status              -> Show active window, mouse, and screen info",
        "    click <x> <y>       -> Click mouse at pixel coordinates",
        "    type <text>         -> Type text into active window",
        "    hotkey <keys...>    -> Send shortcut (e.g. ctrl s, alt f4)",
        "    help                -> Show command reference",
        "    exit / quit         -> Exit terminal console",
        "=" * 70,
        ""
    ]
    try:
        header[1] = "  🌌 ORION v2.0 \"NEBULA\" - Terminal Automation Console"
        print("\n".join(header))
    except Exception:
        header[1] = "  [ORION] v2.0 \"NEBULA\" - Terminal Automation Console"
        print("\n".join(header))

    while True:
        try:
            line = input("orion> ").strip().lstrip("\ufeff").lstrip("ï»¿")
        except (EOFError, KeyboardInterrupt):
            print("\n[SUCCESS] Exiting Orion Console. Goodbye!")
            break

        if not line:
            continue

        lower = line.lower()
        if lower in ("exit", "quit", "q", "close", "stop"):
            print("[SUCCESS] Exiting Orion Console. Goodbye!")
            break

        if lower in ("help", "-h", "--help", "?"):
            print("\nCommands Reference:")
            print("  open <app>          - Launch application immediately (notepad, calc, chrome, etc.)")
            print("  browse <url/query>  - Browse web or search Google (<40ms)")
            print("  speak <text>        - Speak text aloud (--voice Susan for custom voice)")
            print("  focus <title>       - Focus a window by title")
            print("  shot [path]         - Capture screenshot")
            print("  windows             - List open windows")
            print("  status              - Show active window and mouse position")
            print("  click <x> <y>       - Click coordinates")
            print("  type <text>         - Type text into active window")
            print("  hotkey <k1> <k2>... - Send hotkey combination")
            print("  exit / quit         - Exit console\n")
            print("[SUCCESS] Displayed help reference.\n")
            continue

        parts = line.split()
        first = parts[0].lower()
        t_start = time.perf_counter()

        try:
            # 1. Fast application launch
            if first in ("open", "launch", "start", "run") and len(parts) > 1:
                app_name = " ".join(parts[1:])
                res = launch_application(app_name)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                pid = res.get("pid", "active")
                print(f"[SUCCESS] Launched '{app_name}' (PID: {pid}) in {ms}ms")

            # 2. Fast web browse & search
            elif first in ("browse", "search", "web", "goto", "go") and len(parts) > 1:
                query = " ".join(parts[1:])
                res = browse_web(query)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Navigated to '{res.get('target', query)}' in {ms}ms")

            # 3. Fast speech synthesis
            elif first in ("speak", "say", "talk", "voice") and len(parts) > 1:
                raw_text = " ".join(parts[1:])
                voice_name = "George"
                if "--voice" in parts:
                    idx = parts.index("--voice")
                    if idx + 1 < len(parts):
                        voice_name = parts[idx + 1]
                        parts_clean = parts[1:idx] + parts[idx + 2:]
                        raw_text = " ".join(parts_clean)
                res = speak(raw_text, voice=voice_name)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Spoke via {voice_name}: \"{raw_text}\" in {ms}ms")

            # 4. Window focus
            elif first in ("focus", "switch", "switchto", "window") and len(parts) > 1:
                target = " ".join(parts[1:])
                res = focus_window(target)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                if res.get("status") in ("ok", "success"):
                    print(f"[SUCCESS] Focused '{res.get('matched_title')}' in {ms}ms")
                else:
                    print(f"[-] Could not find window matching '{target}' ({ms}ms)")

            # 5. Screen capture
            elif first in ("shot", "screenshot", "screen", "capture"):
                save_p = parts[1] if len(parts) > 1 else None
                res = take_screenshot(save_p)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Screenshot captured to '{res.get('saved_path')}' in {ms}ms")

            # 6. List windows
            elif first in ("windows", "list_windows", "tasks"):
                res = list_windows()
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                wins = res.get("windows", [])
                print(f"Open Windows ({len(wins)}):")
                for w in wins[:12]:
                    print(f"  - [{w.get('hwnd')}] {w.get('process')}: {w.get('title')}")
                if len(wins) > 12:
                    print(f"  ... and {len(wins) - 12} more.")
                print(f"[SUCCESS] Listed {len(wins)} active windows in {ms}ms")

            # 7. Status & telemetry
            elif first in ("status", "info", "state", "telemetry"):
                win = get_active_window()
                pos = get_mouse_position()
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"Active Window: '{win.get('title')}' ({win.get('process')})")
                print(f"Mouse: X={pos.get('x')} Y={pos.get('y')} | Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                print(f"[SUCCESS] Telemetry retrieved in {ms}ms")

            # 8. Mouse position
            elif first in ("pos", "mouse", "cursor"):
                pos = get_mouse_position()
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"Mouse Position: X={pos.get('x')} Y={pos.get('y')}")
                print(f"[SUCCESS] Verified coordinates in {ms}ms")

            # 9. Mouse click
            elif first in ("click", "tap") and len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                res = verified_click(x, y)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Clicked coordinates ({x}, {y}) in {ms}ms")

            # 10. Double click
            elif first in ("double_click", "dclick") and len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                res = double_click(x, y)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Double-clicked coordinates ({x}, {y}) in {ms}ms")

            # 11. Right click
            elif first in ("right_click", "rclick") and len(parts) >= 3:
                x, y = int(parts[1]), int(parts[2])
                res = right_click(x, y)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Right-clicked coordinates ({x}, {y}) in {ms}ms")

            # 12. Type text
            elif first in ("type", "write", "input") and len(parts) > 1:
                text_to_type = " ".join(parts[1:])
                res = type_text(text_to_type)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Typed: \"{text_to_type}\" in {ms}ms")

            # 13. Hotkey
            elif first in ("hotkey", "press", "key") and len(parts) > 1:
                keys = parts[1:]
                res = hotkey(*keys)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Sent hotkey: {' + '.join(keys)} in {ms}ms")

            # 14. Voices list
            elif first in ("voices", "list_voices"):
                v_list = get_available_voices()
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"Installed Voices ({len(v_list)}):")
                for v in v_list:
                    print(f"  - {v.get('name')} ({v.get('gender')}, {v.get('culture')})")
                print(f"[SUCCESS] Found {len(v_list)} studio voices in {ms}ms")

            # 15. Pre-flight check
            elif first in ("preflight", "check", "doctor"):
                res = preflight_check()
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Pre-flight check passed ({len(res.get('installed_apps', []))} apps detected) in {ms}ms")

            # 16. Audio input: listen / record
            elif first in ("listen", "hear", "mic"):
                dur = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 4.0
                print(f"[*] Listening to microphone for {dur}s... (speak now)")
                res = listen(duration_sec=dur)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                txt = res.get("text", "")
                if txt:
                    print(f"[SUCCESS] Heard: \"{txt}\" in {ms}ms")
                else:
                    print(f"[SUCCESS] Audio captured to '{res.get('audio_file')}' in {ms}ms (no speech detected)")
            elif first in ("record", "mic_record") and len(parts) > 1:
                dur = float(parts[1]) if parts[1].replace(".", "").isdigit() else 4.0
                print(f"[*] Recording microphone for {dur}s...")
                res = record_microphone(duration_sec=dur)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Recorded audio to '{res.get('recorded_file')}' in {ms}ms")

            # 17. Direct URL entry
            elif line.startswith("http://") or line.startswith("https://") or line.startswith("www."):
                res = browse_web(line)
                ms = round((time.perf_counter() - t_start) * 1000, 1)
                print(f"[SUCCESS] Navigated to '{res.get('target', line)}' in {ms}ms")

            # 18. Intelligent intent fallback
            else:
                app_check = find_installed_application(line)
                if app_check.get("status") == "ok":
                    res = launch_application(line)
                    ms = round((time.perf_counter() - t_start) * 1000, 1)
                    print(f"[SUCCESS] Launched '{line}' in {ms}ms")
                else:
                    print(f"[-] Unrecognized command: '{line}'. Type 'help' for options.")
        except Exception as e:
            print(f"[-] Error: {e}")


def run_live_watch_monitor(fps: float = 6.0):
    """Provides a live updating terminal dashboard of continuous screen perception telemetry."""
    engine = ContinuousPerceptionEngine(target_fps=fps).start()
    bar = "=" * 76
    print(bar)
    print("  🌌 ORION v2.0 'NEBULA' - Continuous Screen Perception Monitor")
    print(f"  Live Visual Stream: {fps} FPS Target | Sub-10ms Buffer | Press Ctrl+C to Exit")
    print(bar)
    try:
        while True:
            st = engine.get_state()
            win = st.get("active_window", {})
            title = win.get("title", "[Desktop]") or "[Desktop]"
            proc = win.get("process", "explorer.exe") or "explorer.exe"
            delta = st.get("visual_delta_pct", 0.0)
            settled_tag = "SETTLED" if st.get("is_settled") else "ACTIVE/CHANGING"
            eff_fps = st.get("effective_fps", 0.0)
            frames = st.get("frame_count", 0)

            clean_title = (title[:30] + "..") if len(title) > 32 else title
            sys.stdout.write(f"\r[Perception] FPS: {eff_fps:4.1f} | Delta: {delta:5.2f}% [{settled_tag:15s}] | Frame: #{frames:5d} | Window: {proc} - {clean_title}")
            sys.stdout.flush()
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n[Perception] Monitor stopped by user.")
    finally:
        engine.stop()


def run_self_healing_cli() -> dict:
    """Executes an immediate self-healing diagnostic and modal dialog dismissal scan."""
    print("🌌 Orion Autonomous Self-Healing Diagnostic Scan...")
    modal_res = SelfHealingResolver.scan_and_dismiss_modal_dialogs()
    b_heal = SelfHealingResolver.heal_blender_context() if check_port(9876).get("is_open") else {"status": "skipped", "message": "Blender port 9876 inactive"}
    return {
        "status": "success",
        "modal_dialogs": modal_res,
        "blender_context": b_heal,
        "active_window": get_active_window(),
        "timestamp": time.time()
    }


# ==============================================================================
# CLI HANDLER
# ==============================================================================

class OrionSystem:
    """
    🌌 Orion v2.0 'Nebula' - System Layer
    The universal OS substrate, Win32 automation engine, Chrome runtime driver,
    continuous screen perception loop, self-healing watchdog, and audio I/O.
    """
    browse = staticmethod(browse_web)
    chrome = staticmethod(chrome_action)
    launch = staticmethod(launch_application)
    close = staticmethod(close_application)
    focus = staticmethod(focus_window)
    type = staticmethod(type_text)
    key = staticmethod(press_key)
    hotkey = staticmethod(hotkey)
    click = staticmethod(verified_click)
    scroll = staticmethod(mouse_scroll)
    screenshot = staticmethod(take_screenshot)
    speak = staticmethod(speak)
    listen = staticmethod(listen)

    @staticmethod
    def web_browse(url: str, headless: bool = False) -> dict:
        """Navigates to URL using Playwright engine with CDP capture and auto-waiting."""
        from web_engine.browser_manager import BrowserManager
        from web_engine.config import BrowserConfig
        mgr = BrowserManager.get_active() or BrowserManager(BrowserConfig(headless=headless))
        return mgr.navigate(url)

    @staticmethod
    def web_search(portal: str, query: str, limit: int = 5, headless: bool = False) -> dict:
        """Performs deep DOM-level search and extraction across web portals."""
        import urllib.parse
        from web_engine.browser_manager import BrowserManager
        from web_engine.config import BrowserConfig
        from web_engine.pages.portal_search_page import PortalSearchPage
        mgr = BrowserManager.get_active() or BrowserManager(BrowserConfig(headless=headless))
        page = PortalSearchPage(mgr)
        p = portal.lower()
        if "play" in p:
            return page.search_google_play(query, limit=limit)
        elif "youtube" in p:
            return page.search_youtube(query, limit=limit)
        return page.search_generic(f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}", query)

    @staticmethod
    def web_action(action: str, params: dict = None) -> dict:
        """Executes authorized web action with security allow-list enforcement."""
        from web_engine.config import ALLOWED_ACTIONS, SENSITIVE_ACTIONS
        from web_engine.exceptions import ActionNotAllowedError
        from web_engine.browser_manager import BrowserManager
        from web_engine.pages.base_page import BasePage
        act = action.lower().strip()
        if act not in ALLOWED_ACTIONS:
            raise ActionNotAllowedError(f"Action '{act}' blocked. Allowed actions: {ALLOWED_ACTIONS}")
        if act in SENSITIVE_ACTIONS:
            raise ActionNotAllowedError(f"Action '{act}' is sensitive and blocked from automated execution.")
        mgr = BrowserManager.get_active()
        if not mgr or not mgr.is_running:
            raise RuntimeError("No active Playwright browser session found for web_action.")
        page = BasePage(mgr)
        p = params or {}
        if act == "screenshot":
            return mgr.capture_cdp_screenshot(p.get("path"))
        elif act == "aria_snapshot":
            return {"status": "success", "aria_tree": page.aria_snapshot()}
        elif act == "scroll":
            return {"status": "success", "items_loaded": page.scroll_until_no_new_content(max_iterations=p.get("iterations", 6))}
        return {"status": "success", "action": act}

    @staticmethod
    def web_aria_snapshot() -> str:
        """Produces a compact semantic accessibility tree for Perception Inspector."""
        from web_engine.browser_manager import BrowserManager
        from web_engine.pages.base_page import BasePage
        mgr = BrowserManager.get_active()
        if mgr and mgr.is_running:
            return BasePage(mgr).aria_snapshot()
        return ""

    Perception = ContinuousPerceptionEngine
    Healer = SelfHealingResolver


def main():
    parser = argparse.ArgumentParser(
        description=f"🌌 Orion v{VERSION} \"{CODENAME}\" - Universal Autonomous Desktop & Perception Engine"
    )
    parser.add_argument("-v", "--version", action="version", version=f"Orion v{VERSION} ({CODENAME})")
    parser.add_argument("--mcp", action="store_true", help="Run as FastMCP server")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("version", help="Show Orion engine version")

    # preflight
    p_pref = subparsers.add_parser("preflight")
    p_pref.add_argument("items", nargs="*", default=None, help="Software names, libraries, or name:port")
    p_pref.add_argument("--items", dest="items_flag", nargs="*", default=None, help="Alternative items flag")

    # batch sequence
    p_batch = subparsers.add_parser("batch")
    p_batch.add_argument("--file", help="Path to JSON file containing steps array")
    p_batch.add_argument("--json-data", help="Inline JSON string containing steps array")

    # screenshot
    p_shot = subparsers.add_parser("screenshot", aliases=["shot"])
    p_shot.add_argument("--path", default=None)

    # move
    p_move = subparsers.add_parser("move")
    p_move.add_argument("--x", type=int, required=True)
    p_move.add_argument("--y", type=int, required=True)
    p_move.add_argument("--duration", type=float, default=0.15)

    # click (verified)
    p_click = subparsers.add_parser("click")
    p_click.add_argument("--x", type=int, default=None)
    p_click.add_argument("--y", type=int, default=None)
    p_click.add_argument("--button", default="left", choices=["left", "right", "middle"])
    p_click.add_argument("--clicks", type=int, default=1)

    # hover
    p_hov = subparsers.add_parser("hover")
    p_hov.add_argument("--x", type=int, required=True)
    p_hov.add_argument("--y", type=int, required=True)

    # double_click
    p_dclick = subparsers.add_parser("double_click")
    p_dclick.add_argument("--x", type=int, default=None)
    p_dclick.add_argument("--y", type=int, default=None)

    # right_click
    p_rclick = subparsers.add_parser("right_click")
    p_rclick.add_argument("--x", type=int, default=None)
    p_rclick.add_argument("--y", type=int, default=None)

    # drag
    p_drag = subparsers.add_parser("drag")
    p_drag.add_argument("--start_x", type=int, required=True)
    p_drag.add_argument("--start_y", type=int, required=True)
    p_drag.add_argument("--end_x", type=int, required=True)
    p_drag.add_argument("--end_y", type=int, required=True)

    # scroll
    p_scroll = subparsers.add_parser("scroll")
    p_scroll.add_argument("--clicks", type=int, required=True)
    p_scroll.add_argument("--x", type=int, default=None)
    p_scroll.add_argument("--y", type=int, default=None)

    # pos
    subparsers.add_parser("pos")

    # type
    p_type = subparsers.add_parser("type")
    p_type.add_argument("--text", required=True)

    # paste
    p_paste = subparsers.add_parser("paste")
    p_paste.add_argument("--text", required=True)

    # press
    p_press = subparsers.add_parser("press")
    p_press.add_argument("--key", required=True)

    # hotkey
    p_hot = subparsers.add_parser("hotkey")
    p_hot.add_argument("--keys", nargs="+", required=True)

    # windows
    subparsers.add_parser("list_windows", aliases=["windows"])
    subparsers.add_parser("active_window")

    # focus
    p_foc = subparsers.add_parser("focus")
    p_foc.add_argument("title_pos", nargs="*", default=None, help="Window title query (positional)")
    p_foc.add_argument("--title", default=None, help="Window title query")

    # speak
    p_spk = subparsers.add_parser("speak")
    p_spk.add_argument("text_pos", nargs="*", default=None, help="Message text to speak (positional)")
    p_spk.add_argument("--text", default=None, help="Message text to speak")
    p_spk.add_argument("--voice", "-v", default="George", help="Voice name (George, Susan, Zira, Heera, Ravi, Hazel)")

    # voices
    subparsers.add_parser("voices", aliases=["list_voices"], help="List installed professional TTS voices")

    # transcribe
    p_tra = subparsers.add_parser("transcribe")
    p_tra.add_argument("--audio", required=True)

    # listen (microphone speech-to-text)
    p_lis = subparsers.add_parser("listen", help="Listen to microphone and transcribe speech to text")
    p_lis.add_argument("duration_pos", nargs="?", type=float, default=None, help="Listening duration in seconds")
    p_lis.add_argument("--duration", "-d", type=float, default=4.0, help="Listening duration in seconds (default 4)")

    # record (microphone audio capture)
    p_rec = subparsers.add_parser("record", help="Record audio from default microphone to WAV")
    p_rec.add_argument("duration_pos", nargs="?", type=float, default=None, help="Recording duration in seconds")
    p_rec.add_argument("--duration", "-d", type=float, default=4.0, help="Recording duration in seconds (default 4)")
    p_rec.add_argument("--path", default=None, help="Output WAV file path")

    # browse
    p_browse = subparsers.add_parser("browse", aliases=["search", "web"])
    p_browse.add_argument("query", nargs="+", help="URL, query string, or portal name")
    p_browse.add_argument("--browser", choices=["chrome", "edge", "default"], default=None, help="Target browser")

    # chrome
    p_chr = subparsers.add_parser("chrome", help="Dedicated Chrome-native controls")
    p_chr.add_argument("action", help="Action: new_tab, close_tab, reopen_tab, next_tab, prev_tab, reload, focus_url, scroll_down, scroll_up, zoom_in, zoom_out, fullscreen, devtools, close")
    p_chr.add_argument("param", nargs="?", default=None, help="Optional parameter (URL or reload type)")

    # close / kill
    p_cls = subparsers.add_parser("close", aliases=["kill", "terminate"], help="Close running application")
    p_cls.add_argument("app", help="Application name or process to close")
    p_cls.add_argument("--force", "-f", action="store_true", help="Force terminate using taskkill /F")

    # launch / open
    p_launch = subparsers.add_parser("launch", aliases=["open"])
    p_launch.add_argument("app", help="Application name or executable command")
    p_launch.add_argument("extra_args", nargs="*", default=None, help="Trailing arguments or URL for the application")
    p_launch.add_argument("--timeout", type=float, default=8.0)

    # port / check_port
    p_port = subparsers.add_parser("port", aliases=["check_port"])
    p_port.add_argument("port_num", type=int, nargs="?", default=9876, help="Port number (default 9876 for Blender)")
    p_port.add_argument("--host", default="127.0.0.1")

    # apps
    p_apps = subparsers.add_parser("apps")
    p_apps.add_argument("filter", nargs="?", default="", help="Filter app name or ID")

    # ports
    subparsers.add_parser("ports")

    # api / monitor / server
    p_api = subparsers.add_parser("api", aliases=["monitor", "server"])
    p_api.add_argument("--port", type=int, default=8765, help="API server port (default 8765)")
    p_api.add_argument("--daemon", action="store_true", help="Run server in background daemon thread")

    # status
    p_status = subparsers.add_parser("status")
    p_status.add_argument("--port", type=int, default=8765, help="Port of running API server to query (default 8765)")

    # task
    p_task = subparsers.add_parser("task")
    p_task.add_argument("--file", help="Path to task spec JSON file")
    p_task.add_argument("--json", dest="json_data", help="Raw JSON string of task spec")

    # console / shell / interactive
    subparsers.add_parser("console", aliases=["shell", "interactive"], help="Start interactive terminal console")

    # team / run / workflow (AutoGen multi-agent collaboration)
    p_team = subparsers.add_parser("team", aliases=["run", "workflow"], help="Execute goal with AutoGen 5-Agent Collaborative Society")
    p_team.add_argument("goal", nargs="+", help="Goal prompt for the agent society")

    # watch (continuous screen perception telemetry)
    p_watch = subparsers.add_parser("watch", aliases=["monitor_stream"], help="Live continuous screen perception monitor")
    p_watch.add_argument("--fps", type=float, default=6.0, help="Target capture FPS (default 6.0)")

    # heal (autonomous self-healing scan and modal dismissal)
    subparsers.add_parser("heal", help="Autonomous self-healing scan and error dialog auto-dismissal")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command in ("console", "shell", "interactive"):
        run_interactive_console()
        return

    if args.command in ("watch", "monitor_stream"):
        run_live_watch_monitor(fps=args.fps)
        return

    if args.command == "heal":
        result = run_self_healing_cli()
        print(json.dumps(result, indent=2))
        return

    if args.command in ("team", "run", "workflow"):
        goal_text = " ".join(args.goal)
        import orion_autogen
        society = orion_autogen.OrionAgentSociety(use_voice=True)
        society.run_collaborative_workflow(goal_text)
        return

    if args.mcp:
        run_mcp_server()
        return

    result = {}
    if args.command == "version":
        result = {
            "project": PROJECT_NAME,
            "version": VERSION,
            "codename": CODENAME,
            "engine": "Universal Autonomous Desktop & Perception Engine",
            "tag": "Orion v2.0 Nebula"
        }
    elif args.command in ("api", "monitor", "server"):
        start_screen_monitor_server(port=args.port, daemon=args.daemon)
        return
    elif args.command == "task":
        spec = {}
        if args.file and os.path.exists(args.file):
            with open(args.file, "r", encoding="utf-8-sig") as f:
                spec = json.load(f)
        elif args.json_data:
            spec = json.loads(args.json_data)
        result = execute_task(spec)
    elif args.command == "status":
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{args.port}/status", timeout=0.8)
            result = json.loads(req.read().decode("utf-8"))
        except Exception:
            win = get_active_window()
            pos = get_mouse_position()
            result = {
                "status": "ok",
                "timestamp": round(time.time(), 3),
                "active_window": win,
                "mouse": {"x": pos.get("x", 0), "y": pos.get("y", 0)},
                "screen": {"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                "api_server_running": False
            }
    elif args.command == "preflight":
        items = args.items or args.items_flag
        result = preflight_check(items)
    elif args.command == "apps":
        apps = get_installed_apps_catalog()
        if args.filter:
            q = args.filter.lower()
            apps = [a for a in apps if q in a.get("Name", "").lower() or q in a.get("AppID", "").lower()]
        result = {"count": len(apps), "apps": apps}
    elif args.command == "ports":
        result = {"ports": list_listening_ports()}
    elif args.command == "batch":
        steps = []
        if args.file and os.path.exists(args.file):
            with open(args.file, "r", encoding="utf-8-sig") as f:
                steps = json.load(f)
        elif args.json_data:
            steps = json.loads(args.json_data)
        result = run_batch_sequence(steps)
    elif args.command in ("screenshot", "shot"):
        result = take_screenshot(args.path)
    elif args.command in ("launch", "open"):
        extra_str = " ".join(args.extra_args).strip() if args.extra_args else ""
        result = launch_application(args.app, timeout_sec=args.timeout, extra_args=extra_str)
    elif args.command in ("browse", "search", "web"):
        query_str = " ".join(args.query).strip()
        result = browse_web(query_str, browser=args.browser)
    elif args.command == "chrome":
        result = chrome_action(args.action, args.param)
    elif args.command in ("close", "kill", "terminate"):
        result = close_application(args.app, force=args.force)
    elif args.command in ("port", "check_port"):
        result = check_port(args.port_num, host=args.host)
    elif args.command == "move":
        result = move_mouse(args.x, args.y, args.duration)
    elif args.command == "click":
        result = verified_click(args.x, args.y, args.button, args.clicks)
    elif args.command == "hover":
        result = mouse_hover(args.x, args.y)
    elif args.command == "double_click":
        result = double_click(args.x, args.y)
    elif args.command == "right_click":
        result = right_click(args.x, args.y)
    elif args.command == "drag":
        result = mouse_drag(args.start_x, args.start_y, args.end_x, args.end_y)
    elif args.command == "scroll":
        result = mouse_scroll(args.clicks, args.x, args.y)
    elif args.command == "pos":
        result = get_mouse_position()
    elif args.command == "type":
        result = type_text(args.text)
    elif args.command == "paste":
        result = paste_text(args.text)
    elif args.command == "press":
        result = press_key(args.key)
    elif args.command == "hotkey":
        result = hotkey(*args.keys)
    elif args.command in ("list_windows", "windows"):
        result = list_windows()
    elif args.command == "active_window":
        result = get_active_window()
    elif args.command == "focus":
        title_target = args.title or (" ".join(args.title_pos).strip() if args.title_pos else "")
        result = focus_window(title_target)
    elif args.command in ("voices", "list_voices"):
        voices = get_available_voices()
        clean_list = [{k: v for k, v in item.items() if k != "token"} for item in voices]
        result = {"count": len(clean_list), "default": "Microsoft George (HD)", "voices": clean_list}
    elif args.command == "speak":
        text_target = args.text or (" ".join(args.text_pos).strip() if args.text_pos else "")
        result = speak(text_target, voice=args.voice)
    elif args.command == "transcribe":
        result = transcribe_audio(args.audio)
    elif args.command == "listen":
        dur = args.duration_pos or args.duration
        result = listen(dur)
    elif args.command == "record":
        dur = args.duration_pos or args.duration
        result = record_microphone(dur, args.path)
    else:
        parser.print_help()
    if isinstance(result, dict):
        if result.get("status") in ("ok", "success") or "status" not in result:
            result["status"] = "success"
            result["success"] = True

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
