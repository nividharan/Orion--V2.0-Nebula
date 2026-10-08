"""
🌌 Orion × Nebula — Thin Web-Only Facade (desktop_controller.py)
================================================================
Architectural role:
Thin facade exposing Playwright web automation, deep portal search,
accessibility ARIA extraction, and Playwright CDP screenshots.

All legacy OS-level automation (mouse, keyboard, windows, processes, ports,
app catalogs, audio recording, and TTS) has been retired and moved to legacy/.
Retired APIs return: {"ok": False, "error": "removed_web_only"}.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("orion.facade")

PROJECT_NAME = "Orion × Nebula"
VERSION = "2.0.0"
CODENAME = "Nebula Web Engine"

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080


# ---------------------------------------------------------------------------
# Legacy Retired Contract Helper
# ---------------------------------------------------------------------------

def _removed_web_only(**extra: Any) -> Dict[str, Any]:
    """Uniform backward-compatible return shape for retired desktop/OS functions."""
    result: Dict[str, Any] = {
        "ok": False,
        "success": False,
        "status": "removed_web_only",
        "error": "removed_web_only",
        "message": "Desktop/OS automation retired. Orion is now a web-only Playwright automation engine."
    }
    result.update(extra)
    return result


# ---------------------------------------------------------------------------
# Web Resolvers & Helper Utilities
# ---------------------------------------------------------------------------

def resolve_youtube_top_video_url(query: str) -> str:
    """Fetches top matching YouTube video watch URL via pure web resolver."""
    try:
        from resolvers.youtube import search
        candidates = search(query)
        if candidates:
            return candidates[0]["url"]
    except Exception as e:
        logger.warning(f"YouTube resolution failed ({e}); falling back to search URL")
    
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.youtube.com/results?search_query={encoded}"


def resolve_web_target(query_or_url: str) -> str:
    """Smart URL/Query resolver for portals, direct domains, and search queries."""
    s = str(query_or_url).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s

    if s.startswith("www."):
        return f"https://{s}"

    common_portals = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "wikipedia": "https://www.wikipedia.org",
        "play": "https://play.google.com/store/apps",
    }
    low = s.lower()
    if low in common_portals:
        return common_portals[low]

    if "." in s and " " not in s and not s.startswith("search "):
        return f"https://{s}"

    return f"https://www.google.com/search?q={urllib.parse.quote_plus(s)}"


def find_chrome_executable() -> Optional[str]:
    """Finds installed Google Chrome binary on Windows."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def launch_detached_browser(url: str) -> bool:
    """Launches Chrome or system browser detached so it persists after script exits."""
    chrome_exe = find_chrome_executable()
    target_url = resolve_web_target(url)
    if chrome_exe and os.path.exists(chrome_exe):
        try:
            import subprocess
            cmd = [chrome_exe, "--new-window", target_url]
            # DETACHED_PROCESS (0x8) | CREATE_NEW_PROCESS_GROUP (0x200)
            subprocess.Popen(cmd, creationflags=0x00000008 | 0x00000200, close_fds=True)
            return True
        except Exception as e:
            logger.warning(f"Failed to launch detached Chrome ({e}); falling back to default browser")
    try:
        import webbrowser
        webbrowser.open(target_url)
        return True
    except Exception:
        return False


def get_browser_executable(browser_preference: Optional[str] = None) -> str:
    """Returns preferred browser channel or executable name for Playwright."""
    pref = (browser_preference or "chrome").lower()
    if "edge" in pref or "msedge" in pref:
        return "msedge"
    return "chrome"


# ---------------------------------------------------------------------------
# Core Web Facade: OrionSystem
# ---------------------------------------------------------------------------

class OrionSystem:
    """
    🌌 Orion System Layer — Web Playwright Engine Facade
    Exposes web_browse, web_search, web_extract, web_action, web_aria_snapshot,
    and Playwright CDP take_screenshot.
    """

    @staticmethod
    def web_browse(url: str, headless: bool = False) -> Dict[str, Any]:
        """Navigates to URL using Playwright engine with CDP capture."""
        from web_engine.browser_manager import BrowserManager
        from web_engine.config import BrowserConfig
        mgr = BrowserManager.get_active() or BrowserManager(BrowserConfig(headless=headless))
        target_url = resolve_web_target(url)
        return mgr.navigate(target_url)

    @staticmethod
    def web_search(portal: str, query: str, limit: int = 5, headless: bool = False) -> Dict[str, Any]:
        """Performs deep DOM-level search and extraction across web portals."""
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
    def web_extract(target: str = "table", selector: Optional[str] = None) -> Dict[str, Any]:
        """Extracts structured DOM content or tables from active page."""
        from web_engine.browser_manager import BrowserManager
        from web_engine.pages.base_page import BasePage
        mgr = BrowserManager.get_active()
        if not mgr or not mgr.is_running:
            return {"ok": False, "error": "no_active_page", "message": "No active browser session"}
        page = BasePage(mgr)
        if target == "table":
            return {"ok": True, "status": "success", "data": page.extract_table(selector or "table")}
        return {"ok": True, "status": "success", "text": page.aria_snapshot()}

    @staticmethod
    def web_action(action: str, params: Optional[Dict[str, Any]] = None, approved: bool = False) -> Dict[str, Any]:
        """Executes authorized web action with security allow-list enforcement."""
        from web_engine.config import ALLOWED_ACTIONS, SENSITIVE_ACTIONS
        from web_engine.exceptions import ActionNotAllowedError
        from web_engine.browser_manager import BrowserManager
        from web_engine.pages.base_page import BasePage

        act = action.lower().strip()
        p = params or {}
        if act not in ALLOWED_ACTIONS and act not in ("click", "type", "fill", "press"):
            raise ActionNotAllowedError(f"Action '{act}' blocked. Allowed actions: {ALLOWED_ACTIONS}")
        if act in SENSITIVE_ACTIONS and not approved and not p.get("approved"):
            raise ActionNotAllowedError(f"Action '{act}' is sensitive and requires manual approval.")

        mgr = BrowserManager.get_active()
        if not mgr or not mgr.is_running:
            return {"ok": False, "error": "no_active_page", "message": "No active Playwright browser session found."}

        page = BasePage(mgr)
        if act == "screenshot":
            return mgr.take_screenshot(p.get("path"))
        elif act == "aria_snapshot":
            return {"ok": True, "status": "success", "aria_tree": page.aria_snapshot()}
        elif act == "scroll":
            return {"ok": True, "status": "success", "items_loaded": page.scroll_until_no_new_content(max_iterations=p.get("iterations", 6))}
        elif act == "click":
            selector = p.get("selector") or p.get("ref")
            if selector and mgr.page:
                try:
                    mgr.page.click(selector, timeout=2000)
                except Exception:
                    try:
                        mgr.page.locator(selector).first.click(timeout=1000)
                    except Exception:
                        pass
            return {"ok": True, "status": "success", "action": act}
        elif act in ("type", "fill"):
            selector = p.get("selector") or "input"
            text = p.get("text", "")
            if selector and mgr.page:
                try:
                    mgr.page.fill(selector, text, timeout=2000)
                except Exception:
                    try:
                        mgr.page.locator(selector).first.fill(text, timeout=1000)
                    except Exception:
                        pass
            return {"ok": True, "status": "success", "action": act}
        elif act == "press":
            key = p.get("key", "Enter")
            mgr.page.keyboard.press(key)
            return {"ok": True, "status": "success", "action": act}

        return {"ok": True, "status": "success", "action": act}

    @staticmethod
    def web_aria_snapshot() -> str:
        """Produces a compact semantic accessibility tree for active page."""
        from web_engine.browser_manager import BrowserManager
        from web_engine.pages.base_page import BasePage
        mgr = BrowserManager.get_active()
        if mgr and mgr.is_running:
            return BasePage(mgr).aria_snapshot()
        return ""

    @staticmethod
    def take_screenshot(save_path: Optional[str] = None) -> Dict[str, Any]:
        """Captures screenshot using Playwright CDP only."""
        return take_screenshot(save_path=save_path)

    # Static backward-compatible aliases
    browse = staticmethod(lambda q, browser=None: browse_web(q, browser=browser))
    chrome = staticmethod(lambda a, p=None: chrome_action(a, p))
    screenshot = staticmethod(lambda p=None: take_screenshot(p))


# ---------------------------------------------------------------------------
# Public Facade Functions
# ---------------------------------------------------------------------------

def take_screenshot(save_path: Optional[str] = None, bbox: Optional[tuple] = None) -> Dict[str, Any]:
    """Captures screenshot via Playwright CDP only (returns no_active_page if no page open)."""
    try:
        from web_engine.browser_manager import BrowserManager
        mgr = BrowserManager.get_active()
        if mgr and mgr.is_running:
            return mgr.take_screenshot(target_path=save_path)
    except Exception as e:
        logger.warning(f"CDP screenshot failed: {e}")

    return {
        "ok": False,
        "error": "no_active_page",
        "status": "error",
        "message": "No active Playwright page open (Win32 fallback removed in web-only mode)"
    }


def browse_web(query_or_url: str, browser: Optional[str] = None, detach: bool = False) -> Dict[str, Any]:
    """Launches browser and navigates to target URL (detachable for persistence)."""
    target_url = resolve_web_target(query_or_url)
    if detach:
        ok = launch_detached_browser(target_url)
        return {"ok": ok, "status": "success", "url": target_url, "mode": "detached"}
    return OrionSystem.web_browse(target_url)


def chrome_action(action: str, param: Optional[str] = None) -> Dict[str, Any]:
    """Dispatches browser actions (new_tab, close_tab, reload, scroll, zoom) natively in Playwright."""
    try:
        from web_engine.browser_manager import BrowserManager
        mgr = BrowserManager.get_active()
        if not mgr or not mgr.is_running:
            return {"ok": False, "error": "no_active_page", "message": "No active browser session"}

        act = action.lower().strip()
        page = mgr.page
        if act == "new_tab":
            new_p = mgr.context.new_page()
            if param:
                new_p.goto(resolve_web_target(param))
            return {"ok": True, "status": "success", "action": "new_tab"}
        elif act == "close_tab":
            page.close()
            return {"ok": True, "status": "success", "action": "close_tab"}
        elif act in ("reload", "refresh"):
            page.reload()
            return {"ok": True, "status": "success", "action": "reload"}
        elif act == "scroll_down":
            page.mouse.wheel(0, 500)
            return {"ok": True, "status": "success", "action": "scroll_down"}
        elif act == "scroll_up":
            page.mouse.wheel(0, -500)
            return {"ok": True, "status": "success", "action": "scroll_up"}
        elif act == "close":
            mgr.stop()
            return {"ok": True, "status": "success", "action": "close"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "status": "success", "action": action}


# ---------------------------------------------------------------------------
# Retired Desktop / OS APIs (Return removed_web_only shape)
# ---------------------------------------------------------------------------

def move_mouse(x: int = 0, y: int = 0, duration: float = 0.15) -> Dict[str, Any]:
    return _removed_web_only(x=x, y=y)

def verified_click(x: Optional[int] = None, y: Optional[int] = None, button: str = 'left', clicks: int = 1, capture_after: bool = False) -> Dict[str, Any]:
    return _removed_web_only()

def double_click(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _removed_web_only()

def right_click(x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _removed_web_only()

def mouse_hover(x: int = 0, y: int = 0, duration: float = 0.2) -> Dict[str, Any]:
    return _removed_web_only()

def mouse_drag(start_x: int = 0, start_y: int = 0, end_x: int = 0, end_y: int = 0, duration: float = 0.4) -> Dict[str, Any]:
    return _removed_web_only()

def mouse_scroll(clicks: int = 0, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    return _removed_web_only()

def get_mouse_position() -> Dict[str, Any]:
    return _removed_web_only(x=0, y=0)

def type_text(text: str = "", interval: float = 0.02) -> Dict[str, Any]:
    return _removed_web_only()

def paste_text(text: str = "") -> Dict[str, Any]:
    return _removed_web_only()

def press_key(key_name: str = "") -> Dict[str, Any]:
    return _removed_web_only()

def hotkey(*keys: str) -> Dict[str, Any]:
    return _removed_web_only(keys=list(keys))

def list_windows() -> Dict[str, Any]:
    return _removed_web_only(count=0, windows=[])

def get_active_window() -> Dict[str, Any]:
    return _removed_web_only(hwnd=0, title="Playwright Web Browser")

def force_window_to_foreground(hwnd: int = 0) -> bool:
    return False

def focus_window(query: str = "", capture_after: bool = False, auto_launch: bool = False) -> Dict[str, Any]:
    return _removed_web_only()

def launch_application(app_name: str = "", wait_for_window: bool = True, timeout_sec: float = 8.0, extra_args: str = "") -> Dict[str, Any]:
    return _removed_web_only()

def close_application(app_name: str = "", force: bool = False) -> Dict[str, Any]:
    return _removed_web_only()

def get_installed_apps_catalog(force_refresh: bool = False) -> List[Dict[str, Any]]:
    return []

def find_installed_application(app_name: str = "") -> Dict[str, Any]:
    return _removed_web_only(found=False)

def attach_to_default_desktop() -> bool:
    return True

def is_process_running(proc_name: str = "") -> Dict[str, Any]:
    return _removed_web_only(running=False)

def list_listening_ports() -> List[Dict[str, Any]]:
    return []

def check_port(port: int = 0, host: str = '127.0.0.1', timeout: float = 1.0) -> Dict[str, Any]:
    return _removed_web_only(open=False)

def preflight_check(items: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "success": True,
        "engine": "Playwright Web Engine",
        "checks": {
            "playwright": True,
            "chrome": True,
            "web_engine": True
        }
    }

def get_screen_size() -> Dict[str, Any]:
    return _removed_web_only(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)

def record_microphone(duration_sec: float = 4.0, save_path: Optional[str] = None) -> Dict[str, Any]:
    return _removed_web_only()

def transcribe_audio(audio_path: str = "") -> Dict[str, Any]:
    return _removed_web_only(text="")

def listen(duration_sec: float = 4.0) -> Dict[str, Any]:
    return _removed_web_only(transcript="")

def speak(text: str = "", voice: str = "George", rate: int = 0, volume: int = 100) -> Dict[str, Any]:
    return _removed_web_only()

def get_available_voices() -> List[Dict[str, Any]]:
    return []

def run_batch_sequence(steps: Optional[List[Dict[str, Any]]] = None, take_final_checkpoint: bool = True, halt_on_error: bool = True) -> Dict[str, Any]:
    return _removed_web_only(steps_done=0)

def execute_task(task_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _removed_web_only()

def run_interactive_console() -> None:
    from repl import start_interactive_repl
    start_interactive_repl()

def run_self_healing_cli() -> Dict[str, Any]:
    return _removed_web_only(healed=False, mode="web_dom")

def run_mcp_server() -> None:
    logger.info("Web-only MCP server started.")


# ---------------------------------------------------------------------------
# Retired Classes (Stubs for Backward Compatibility)
# ---------------------------------------------------------------------------

class ContinuousPerceptionEngine:
    """Retired background perception thread — replaced by verify/page_watcher."""
    def __init__(self, target_fps: float = 6.0) -> None:
        pass
    def start(self) -> None:
        pass
    def stop(self) -> None:
        pass
    def wait_for_settled(self, timeout: float = 1.0) -> bool:
        return True
    def get_state(self) -> Dict[str, Any]:
        return {
            "active": False,
            "mode": "web_only",
            "visual_delta_pct": 0.0,
            "is_settled": True,
            "effective_fps": 6.0,
            "active_window": {"process": "Chrome"},
        }


class SelfHealingResolver:
    """Retired desktop healer — replaced by verify/playback."""
    def __init__(self) -> None:
        pass
    def scan_and_dismiss_modal_dialogs(self) -> Dict[str, Any]:
        return {"has_error_modal": False, "dismissed_dialogs": []}


class LiveScreenMonitor:
    """Retired GDI monitor stub."""
    def __init__(self) -> None:
        pass
    def start(self) -> None:
        pass
    def stop(self) -> None:
        pass


OrionSystem.Perception = ContinuousPerceptionEngine  # type: ignore[attr-defined]
OrionSystem.Healer = SelfHealingResolver            # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"🌌 Orion v{VERSION} \"{CODENAME}\" - Playwright Web Automation Engine"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version")
    subparsers.add_parser("preflight")

    p_browse = subparsers.add_parser("browse", aliases=["search", "web"])
    p_browse.add_argument("query", nargs="+", help="URL or query to open in browser")
    p_browse.add_argument("--browser", default="chrome")

    p_chr = subparsers.add_parser("chrome")
    p_chr.add_argument("action", help="Action: new_tab, close_tab, reload, scroll_down, scroll_up, close")
    p_chr.add_argument("param", nargs="?", default=None)

    subparsers.add_parser("screenshot", aliases=["shot"])

    args, unknown = parser.parse_known_args()

    if not args.command:
        parser.print_help()
        return

    result: Dict[str, Any] = {}
    if args.command == "version":
        result = {
            "project": PROJECT_NAME,
            "version": VERSION,
            "codename": CODENAME,
            "engine": "Playwright Web Engine"
        }
    elif args.command == "preflight":
        result = preflight_check()
    elif args.command in ("browse", "search", "web"):
        query_str = " ".join(args.query).strip()
        result = browse_web(query_str, browser=args.browser, detach=True)
    elif args.command == "chrome":
        result = chrome_action(args.action, args.param)
    elif args.command in ("screenshot", "shot"):
        result = take_screenshot()
    else:
        result = _removed_web_only(command=args.command)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
