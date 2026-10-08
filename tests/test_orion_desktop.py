"""
tests/test_orion_desktop.py — Unit & Integration Tests for Orion Desktop Substrate
===================================================================================
Verifies OrionSubstrate, hardware keyboard/mouse drivers, 3D viewport operators,
window manager, process manager, dialog detector, and pluggable adapters (Chrome & Blender).
All tests execute cleanly offline with zero external dependencies.
"""

import sys
import pytest
from typing import List, Dict, Any

from orion_desktop import (
    OrionSubstrate,
    BaseAppAdapter,
    GenericAppAdapter,
    ChromeAdapter,
    BlenderAdapter,
    KeyboardDriver,
    MouseDriver,
    WindowManager,
    ProcessManager,
    ScreenCapture,
    DialogDetector,
)


class TestKeyboardDriver:
    """Verifies hardware keyboard simulation, scan codes, chords, and typing cadences."""

    def test_key_press_and_log(self):
        kb = KeyboardDriver(human_cadence=False)
        assert kb.press("a") is True
        log = kb.get_sent_log()
        assert len(log) == 2
        assert log[0]["event"] == "key_down"
        assert log[0]["key"] == "a"
        assert log[1]["event"] == "key_up"

    def test_hotkey_chord_sequences(self):
        kb = KeyboardDriver(human_cadence=False)
        # Shift + A (Blender Add Menu)
        assert kb.hotkey("shift", "a") is True
        log = kb.get_sent_log()
        assert len(log) == 4
        assert log[0]["key"] == "shift" and log[0]["event"] == "key_down"
        assert log[1]["key"] == "a" and log[1]["event"] == "key_down"
        assert log[2]["key"] == "a" and log[2]["event"] == "key_up"
        assert log[3]["key"] == "shift" and log[3]["event"] == "key_up"

    def test_type_text_cadence(self):
        kb = KeyboardDriver(human_cadence=False)
        assert kb.type_text("Hello\n") is True
        log = kb.get_sent_log()
        keys_pressed = [item["key"] for item in log if item["event"] == "key_down"]
        assert "shift" in keys_pressed  # 'H' triggers shift
        assert "enter" in keys_pressed  # '\n' triggers enter


class TestMouseDriver:
    """Verifies mouse movements, Bezier curves, coordinate normalization, and 3D operators."""

    def test_cursor_position_and_click(self):
        mouse = MouseDriver(human_trajectories=False)
        pos = mouse.get_position()
        assert len(pos) == 2
        assert mouse.click(500, 300) is True
        log = mouse.get_sent_log()
        assert len(log) >= 3  # move, down, up

    def test_bezier_trajectory_motion(self):
        mouse = MouseDriver(human_trajectories=True)
        assert mouse.move_to(800, 600, duration_s=0.05) is True
        log = mouse.get_sent_log()
        assert len(log) >= 5  # intermediate Bezier steps

    def test_drag_and_drop_slider(self):
        mouse = MouseDriver(human_trajectories=False)
        assert mouse.drag_and_drop(100, 200, 300, 200) is True
        log = mouse.get_sent_log()
        assert any(item["flags"] & 0x0002 for item in log)  # LEFTDOWN
        assert any(item["flags"] & 0x0004 for item in log)  # LEFTUP

    def test_blender_3d_viewport_operators(self):
        mouse = MouseDriver(human_trajectories=False)
        # Orbit 3D viewport (middle click drag)
        assert mouse.orbit_3d(dx=50, dy=-30, duration_s=0.01) is True
        # Zoom 3D viewport (wheel delta)
        assert mouse.zoom_3d(delta_wheel=2) is True
        log = mouse.get_sent_log()
        assert any(item["flags"] & 0x0020 for item in log)  # MIDDLEDOWN
        assert any(item["flags"] & 0x0800 for item in log)  # WHEEL


class TestWindowManager:
    """Verifies window enumeration, search by title/class, and geometry."""

    def test_mock_window_enumeration_and_search(self):
        wm = WindowManager()
        wm.add_mock_window(1001, "Google Chrome - New Tab", "Chrome_WidgetWin_1")
        wm.add_mock_window(2002, "Blender [4.2.0] - scene.blend", "GHOST_WindowClass")
        wm.add_mock_window(3003, "Untitled - Notepad", "Notepad")

        chrome_hwnd = wm.find_window_by_title("Chrome")
        assert chrome_hwnd == 1001

        blender_hwnd = wm.find_window_by_class("GHOST_WindowClass")
        assert blender_hwnd == 2002

        rect = wm.get_window_rect(1001)
        assert rect is not None and len(rect) == 4

        assert wm.set_foreground(2002) is True
        assert wm.minimize(2002) is True
        assert wm.maximize(2002) is True


class TestProcessManager:
    """Verifies trusted executable resolution, launching, and process tracking."""

    def test_app_path_resolution(self):
        pm = ProcessManager()
        # Notepad is available on all Windows installations
        if sys.platform == "win32":
            path = pm.resolve_app_path("notepad")
            assert path is not None and "notepad" in path.lower()

    def test_launch_and_tracking(self):
        pm = ProcessManager()
        pid = pm.launch("notepad")
        assert isinstance(pid, int)
        assert pm.is_running(pid) is True
        assert pid in pm.get_tracked_pids()
        assert pm.terminate(pid) is True


class TestScreenCaptureAndDialogDetector:
    """Verifies visual capture and system error dialog detection."""

    def test_screen_capture(self):
        sc = ScreenCapture()
        img = sc.capture_screen()
        assert img is not None
        assert img.startswith(b"\x89PNG")

    def test_dialog_detector(self):
        wm = WindowManager()
        wm.add_mock_window(5005, "Fatal Error Dialog", "#32770")
        detector = DialogDetector(window_manager=wm)
        report = detector.check_for_dialogs()
        assert report["detected"] is True
        assert report["count"] == 1
        assert report["dialogs"][0]["class_name"] == "#32770"


class TestAppAdapters:
    """Verifies Chrome and Blender adapters adhering to BaseAppAdapter."""

    def test_chrome_adapter_interface(self):
        adapter = ChromeAdapter()
        assert adapter.app_name == "chrome"
        assert adapter.new_tab() is True
        assert adapter.reload() is True
        assert adapter.close_tab() is True
        assert adapter.type_text("search query") is True

    def test_blender_adapter_3d_operators(self):
        blender = BlenderAdapter()
        assert blender.app_name == "blender"
        # 3D shortcuts
        assert blender.add_menu() is True
        assert blender.grab_mode("x") is True
        assert blender.rotate_mode("z") is True
        assert blender.scale_mode() is True
        assert blender.toggle_edit_mode() is True
        assert blender.trigger_render() is True
        assert blender.view_front() is True
        assert blender.view_side() is True
        assert blender.view_top() is True
        # 3D Viewport navigation
        assert blender.orbit(30, 20) is True
        assert blender.zoom(3) is True


class TestOrionSubstrateFacade:
    """Verifies the central OrionSubstrate facade."""

    def test_substrate_registry_and_convenience_methods(self):
        substrate = OrionSubstrate(human_cadence=False)
        assert "chrome" in substrate.list_adapters()
        assert "blender" in substrate.list_adapters()
        assert "notepad" in substrate.list_adapters()

        blender = substrate.get_adapter("blender")
        assert isinstance(blender, BlenderAdapter)

        # Direct desktop primitives
        assert substrate.press("enter") is True
        assert substrate.hotkey("ctrl", "s") is True
        assert substrate.type_text("Orion Substrate v2.0") is True
        assert substrate.click(400, 300) is True
        assert substrate.double_click(400, 300) is True
        assert substrate.right_click(400, 300) is True
        assert substrate.middle_click(400, 300) is True
        assert substrate.drag(100, 100, 200, 200) is True
        assert substrate.move_to(500, 500) is True
        assert substrate.capture_screen() is not None
        assert isinstance(substrate.check_dialogs(), dict)
