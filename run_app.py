"""
Orion × Nebula — Native Desktop Application Launcher.
Boots the local FastAPI telemetry server and launches the borderless application window.
"""

import os
import sys
import time
import subprocess
import threading
import urllib.request
import webbrowser
from pathlib import Path

PORT = 8000
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"


def start_server():
    """Starts the Uvicorn server in a background thread."""
    import uvicorn
    # Set web directory
    os.environ["WEB_HEADLESS"] = "false"
    uvicorn.run("api_server:app", host=HOST, port=PORT, log_level="warning")


def wait_for_server(timeout=10.0):
    """Waits for the HTTP health check to return 200 OK."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{URL}/health", timeout=1.0) as res:
                if res.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def find_browser_app_executable():
    """Locates Chrome or Edge to launch in dedicated desktop application mode."""
    candidates = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def launch_window():
    """Launches the standalone application window."""
    browser_exe = find_browser_app_executable()
    if browser_exe:
        print(f"🌌 Launching Native Desktop Window via {Path(browser_exe).name}...")
        subprocess.Popen([
            browser_exe,
            f"--app={URL}",
            "--window-size=1380,900"
        ])
    else:
        print(f"🌌 Opening Autonomous Deck in default browser at {URL}...")
        webbrowser.open(URL)


def main():
    print("=" * 64)
    print("  🌌 ORION SYSTEM × NEBULA MODEL (v2.0) — AUTONOMOUS APP")
    print("  Local Telemetry Deck & Perception Engine")
    print(f"  URL: {URL}")
    print("=" * 64)

    # 1. Start background server thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 2. Wait for server readiness
    if not wait_for_server(timeout=10.0):
        print("❌ Error: API server failed to start within timeout.")
        sys.exit(1)

    print("✓ Local API Gateway & WebSocket Server Ready.")

    # 3. Launch UI Window
    launch_window()

    print("\n✨ Autonomous Application is running.")
    print("👉 Press Ctrl+C in this terminal to shut down.\n")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n🌌 Shutting down Orion × Nebula Autonomous Application...")
        sys.exit(0)


if __name__ == "__main__":
    main()
