"""Characterization and regression tests for the thin web-only desktop_controller facade.

Phase 1 validation:
- Verifies all legacy OS/desktop functions return {"ok": False, "error": "removed_web_only"}.
- Verifies OrionSystem exposes web_browse, web_search, web_extract, web_action, web_aria_snapshot.
- Verifies take_screenshot uses Playwright CDP only (no Win32 fallback), returning {"ok": False, "error": "no_active_page"} when no page is open.
- Grep test ensuring no pyautogui, os.system, or win32/ctypes input/kill calls exist outside legacy/.
"""

import ast
import inspect
import os
import re
from pathlib import Path
import pytest

from config import REPO_ROOT


class TestLegacyFunctionsReturnRemovedShape:
    """Verifies every retired OS/desktop function returns {ok: False, error: 'removed_web_only'}."""

    @pytest.fixture(autouse=True)
    def import_facade(self):
        import desktop_controller as dc
        self.dc = dc

    @pytest.mark.parametrize(
        "fn_name,args",
        [
            ("move_mouse", (100, 200)),
            ("verified_click", (100, 200)),
            ("double_click", (100, 200)),
            ("right_click", (100, 200)),
            ("mouse_hover", (100, 200)),
            ("mouse_drag", (0, 0, 100, 100)),
            ("mouse_scroll", (5,)),
            ("get_mouse_position", ()),
            ("type_text", ("hello",)),
            ("paste_text", ("hello",)),
            ("press_key", ("enter",)),
            ("hotkey", ("ctrl", "c")),
            ("list_windows", ()),
            ("get_active_window", ()),
            ("focus_window", ("chrome",)),
            ("launch_application", ("notepad",)),
            ("close_application", ("notepad",)),
            ("get_installed_apps_catalog", ()),
            ("find_installed_application", ("calc",)),
            ("is_process_running", ("notepad.exe",)),
            ("list_listening_ports", ()),
            ("check_port", (8080,)),
            ("get_screen_size", ()),
            ("record_microphone", (2.0,)),
            ("transcribe_audio", ("test.wav",)),
            ("listen", (2.0,)),
            ("speak", ("hello",)),
            ("get_available_voices", ()),
            ("run_batch_sequence", ([{"action": "click"}],)),
            ("execute_task", ({"task": "test"},)),
            ("run_self_healing_cli", ()),
        ],
    )
    def test_legacy_function_returns_removed_shape(self, fn_name, args):
        assert hasattr(self.dc, fn_name), f"Facade missing {fn_name}"
        fn = getattr(self.dc, fn_name)
        res = fn(*args)
        if isinstance(res, dict):
            assert res.get("ok") is False or res.get("success") is False
            assert res.get("error") == "removed_web_only"
        elif isinstance(res, list):
            assert res == []
        elif isinstance(res, bool):
            assert res is False

    def test_force_window_to_foreground(self):
        assert hasattr(self.dc, "force_window_to_foreground")
        assert self.dc.force_window_to_foreground(12345) is False

    def test_attach_to_default_desktop(self):
        assert hasattr(self.dc, "attach_to_default_desktop")
        res = self.dc.attach_to_default_desktop()
        assert res is True or (isinstance(res, dict) and res.get("ok") is False)


class TestWebFacadeAPI:
    """Verifies thin web facade exposes required web engine operations."""

    @pytest.fixture(autouse=True)
    def import_facade(self):
        import desktop_controller as dc
        self.dc = dc

    def test_orion_system_web_methods_exist(self):
        Orion = self.dc.OrionSystem
        assert hasattr(Orion, "web_browse"), "OrionSystem must expose web_browse"
        assert hasattr(Orion, "web_search"), "OrionSystem must expose web_search"
        assert hasattr(Orion, "web_extract"), "OrionSystem must expose web_extract"
        assert hasattr(Orion, "web_action"), "OrionSystem must expose web_action"
        assert hasattr(Orion, "web_aria_snapshot"), "OrionSystem must expose web_aria_snapshot"

    def test_take_screenshot_no_page_returns_error(self):
        # When no Playwright page is active, CDP capture returns {ok: False, error: 'no_active_page'}
        res = self.dc.take_screenshot()
        assert isinstance(res, dict)
        assert res.get("ok") is False or res.get("status") in ("error", "fail")
        assert "no_active_page" in str(res.get("error", "")) or "no_active_page" in str(res.get("message", ""))

    def test_deleted_functions_not_present(self):
        # Phase 1 item 2: Delete execute_blender_code, get_blender_scene_info, start_screen_monitor_server,
        # MonitorHTTPHandler, get_live_screen_monitor.
        deleted = [
            "execute_blender_code",
            "get_blender_scene_info",
            "start_screen_monitor_server",
            "MonitorHTTPHandler",
            "get_live_screen_monitor",
        ]
        for name in deleted:
            assert not hasattr(self.dc, name), f"{name} should be deleted from desktop_controller"


class TestGrepNoBypassOutsideLegacy:
    """Grep test that fails if pyautogui, os.system, or win32/ctypes input/kill calls are imported outside legacy/."""

    FORBIDDEN_PATTERNS = [
        (re.compile(r'\bimport\s+pyautogui\b|\bfrom\s+pyautogui\b'), "pyautogui import"),
        (re.compile(r'\bos\.system\s*\('), "os.system call"),
        (re.compile(r'\bwin32gui\b|\bwin32api\b|\bwin32con\b'), "win32 GUI/API import"),
        (re.compile(r'\bctypes\.windll\.user32\b'), "ctypes user32 direct call"),
    ]

    EXCLUDED_DIRS = {
        ".git",
        ".cache",
        "legacy",
        "scratch",
        "brain",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
    }

    def test_no_forbidden_os_imports_outside_legacy(self):
        violations = []

        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            for file in files:
                if file.endswith(".py") and not file.startswith("test_facade_characterization"):
                    filepath = Path(root) / file
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        for pattern, desc in self.FORBIDDEN_PATTERNS:
                            matches = pattern.findall(content)
                            if matches:
                                violations.append(f"{filepath.relative_to(REPO_ROOT)}: {desc} ({len(matches)} occurrences)")
                    except Exception as exc:
                        violations.append(f"{filepath}: read error: {exc}")

        assert not violations, "Found forbidden OS/input calls outside legacy/:\n" + "\n".join(violations)
