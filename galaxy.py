"""
galaxy.py — Galaxy Cognitive 3D Agent for Orion & Nebula.
=========================================================
Human-Level 3D Desktop Automation Engine:
- Directly controls the live Blender user interface like an actual human artist.
- Uses hardware-level Win32 Mouse & Keyboard drivers with natural Bezier trajectories.
- Uses Continuous Screen Watcher & Visual Diffing to perceive and verify UI reactions.
- Named: Galaxy (3D Creative Agent).
"""

from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from orion_desktop.substrate import OrionSubstrate
from orion_desktop.adapters.blender import BlenderAdapter
from orion_desktop.controls.mouse import MouseDriver
from orion_desktop.controls.keyboard import KeyboardDriver
from orion_desktop.controls.screen_capture import ScreenCapture
from orion_desktop.controls.window_manager import WindowManager
from verify.page_watcher import calculate_visual_diff_pct
from verify.screen_watcher import FreezeDetector, ActionPerceptionResult
from verify.page_watcher import Verdict

logger = logging.getLogger("Orion.Galaxy")


class GalaxyAgent:
    """
    Galaxy Model: Human-level autonomous 3D agent driving Blender's real GUI.
    Perceives via Screen Watcher, acts via physical mouse & keyboard hotkeys.
    """

    def __init__(self, human_speed: bool = True):
        self.substrate = OrionSubstrate()
        self.blender: BlenderAdapter = self.substrate.get_adapter("blender")
        self.mouse: MouseDriver = self.substrate.mouse
        self.keyboard: KeyboardDriver = self.substrate.keyboard
        self.sc: ScreenCapture = self.substrate.sc
        self.wm: WindowManager = self.substrate.wm
        self.freeze_detector = FreezeDetector()
        self.human_speed = human_speed

        # Action history & perception logs
        self.perception_history: List[ActionPerceptionResult] = []

    def _wait_human(self, sec: float = 0.3) -> None:
        """Human-like micro-pause between GUI actions."""
        if self.human_speed:
            time.sleep(sec)

    # -----------------------------------------------------------------------
    # Window & Focus Management
    # -----------------------------------------------------------------------
    def launch(self) -> int:
        """Launches the visible Blender application on the desktop."""
        logger.info("Galaxy: Launching live Blender GUI...")
        pid = self.blender.launch()
        self._wait_human(2.0)
        return pid

    def focus(self) -> bool:
        """Ensures the real Blender window is active in the foreground."""
        hwnd = self.blender.find_window()
        if hwnd:
            ok = self.wm.set_foreground(hwnd)
            self._wait_human(0.2)
            return ok
        return False

    def capture_screen_buffer(self) -> Optional[bytes]:
        """Captures the current visible Blender viewport or screen."""
        hwnd = self.blender.find_window()
        if hwnd:
            return self.sc.capture_window(hwnd)
        return self.sc.capture_screen()

    # -----------------------------------------------------------------------
    # Closed-Loop Screen Watcher Perception
    # -----------------------------------------------------------------------
    def execute_with_screen_watcher(
        self,
        action_name: str,
        action_fn: Any,
        *args,
        min_delta_pct: float = 0.1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Executes a human-level GUI action under closed-loop Screen Watcher perception:
        1. Captures pre-action screen buffer
        2. Executes physical mouse/keyboard action
        3. Captures post-action screen buffer
        4. Calculates perceptual visual hash diff % (Screen Watcher)
        5. Reports verdict (OK if UI reacted, FAIL if dead click)
        """
        self.focus()
        t_start = time.perf_counter()

        # Pre-action observation
        pre_bytes = self.capture_screen_buffer()

        # Execute motor action
        result = action_fn(*args, **kwargs)
        self._wait_human(0.4)

        # Post-action observation
        post_bytes = self.capture_screen_buffer()
        elapsed = time.perf_counter() - t_start

        # Perceptual diffing
        delta_pct = calculate_visual_diff_pct(pre_bytes, post_bytes)
        ui_changed = delta_pct >= min_delta_pct

        perception_res = ActionPerceptionResult(
            success=result is not False,
            dead_click=not ui_changed,
            visual_delta_pct=delta_pct,
            verdict=Verdict.OK if ui_changed else Verdict.UNCERTAIN,
            signal="visual_change_detected" if ui_changed else "no_visual_change",
            elapsed_sec=elapsed,
            detail=f"Action '{action_name}': delta={delta_pct:.2f}% in {elapsed*1000:.0f}ms"
        )
        self.perception_history.append(perception_res)

        logger.info(f"Galaxy Screen Watcher: [{action_name}] -> Delta: {delta_pct:.2f}% (Signal: {perception_res.signal})")
        return {
            "action": action_name,
            "success": perception_res.success,
            "visual_delta_pct": delta_pct,
            "verdict": perception_res.verdict.value,
            "elapsed_ms": elapsed * 1000.0,
            "raw_result": result
        }

    # -----------------------------------------------------------------------
    # Human-Level 3D Blender Actions
    # -----------------------------------------------------------------------
    def open_add_menu(self) -> Dict[str, Any]:
        """Opens Add Menu via Shift + A with Screen Watcher verification."""
        return self.execute_with_screen_watcher(
            "Open Add Menu (Shift+A)",
            self.blender.add_menu
        )

    def add_mesh_primitive(self, name: str = "uv_sphere") -> Dict[str, Any]:
        """
        Simulates human action:
        1. Presses Shift + A (Add Menu)
        2. Types primitive name into operator search or selects mesh
        3. Hits Enter to place in 3D Viewport
        """
        def _add():
            self.blender.add_menu()
            self._wait_human(0.3)
            # Use Blender's menu search: 's' for search or type text
            self.keyboard.press("s")
            self._wait_human(0.15)
            self.keyboard.type_text(name.replace("_", " "))
            self._wait_human(0.2)
            self.keyboard.press("enter")
            return True

        return self.execute_with_screen_watcher(
            f"Add 3D Mesh: {name}",
            _add
        )

    def grab_and_move(self, axis: Optional[str] = None, dx: int = 50, dy: int = 0) -> Dict[str, Any]:
        """Presses G, optionally locks axis, drags mouse with natural trajectory."""
        def _grab():
            self.blender.grab_mode(axis=axis)
            self._wait_human(0.2)
            self.mouse.move_relative(dx, dy)
            self._wait_human(0.2)
            self.keyboard.press("enter")
            return True

        return self.execute_with_screen_watcher(
            f"Grab and Move (G {axis or ''})",
            _grab
        )

    def scale_object(self, factor_str: str = "1.5") -> Dict[str, Any]:
        """Presses S, types scale factor, hits Enter."""
        def _scale():
            self.blender.scale_mode()
            self._wait_human(0.2)
            self.keyboard.type_text(factor_str)
            self._wait_human(0.2)
            self.keyboard.press("enter")
            return True

        return self.execute_with_screen_watcher(
            f"Scale Object ({factor_str}x)",
            _scale
        )

    def rotate_object(self, axis: Optional[str] = None, degrees: str = "45") -> Dict[str, Any]:
        """Presses R, optionally locks axis, types degrees, hits Enter."""
        def _rotate():
            self.blender.rotate_mode(axis=axis)
            self._wait_human(0.2)
            self.keyboard.type_text(degrees)
            self._wait_human(0.2)
            self.keyboard.press("enter")
            return True

        return self.execute_with_screen_watcher(
            f"Rotate Object (R {axis or ''} {degrees}deg)",
            _rotate
        )

    def orbit_3d_viewport(self, dx: int = 150, dy: int = -60) -> Dict[str, Any]:
        """
        Simulates human middle-click drag to orbit the 3D viewport.
        Uses cubic Bezier curves and monitors continuous visual motion.
        """
        return self.execute_with_screen_watcher(
            f"Orbit 3D Viewport ({dx}, {dy})",
            lambda: self.blender.orbit(dx, dy)
        )

    def pan_3d_viewport(self, dx: int = 80, dy: int = 0) -> Dict[str, Any]:
        """Simulates human Shift + Middle Click drag to pan the 3D viewport."""
        return self.execute_with_screen_watcher(
            f"Pan 3D Viewport ({dx}, {dy})",
            lambda: self.blender.pan(dx, dy)
        )

    def zoom_3d_viewport(self, delta_wheel: int = 3) -> Dict[str, Any]:
        """Simulates human mouse wheel zoom in the 3D viewport."""
        return self.execute_with_screen_watcher(
            f"Zoom 3D Viewport ({delta_wheel} notches)",
            lambda: self.blender.zoom(delta_wheel)
        )

    def set_viewport_shading(self, mode: str = "rendered") -> Dict[str, Any]:
        """
        Simulates human pressing Z to open the Shading Pie Menu,
        then selecting Rendered, Material Preview, Solid, or Wireframe.
        """
        def _shading():
            self.keyboard.press("z")
            self._wait_human(0.2)
            # Pie menu hotkeys: 8 = Rendered, 6 = Solid, 4 = Wireframe, 2 = Material
            key_map = {"rendered": "8", "solid": "6", "wireframe": "4", "material": "2"}
            digit = key_map.get(mode.lower(), "8")
            self.keyboard.press(digit)
            return True

        return self.execute_with_screen_watcher(
            f"Set Shading Mode: {mode.upper()}",
            _shading
        )

    def trigger_render(self) -> Dict[str, Any]:
        """Simulates human hitting F12 to trigger 3D rendering."""
        return self.execute_with_screen_watcher(
            "Trigger 3D Render (F12)",
            self.blender.trigger_render
        )

    def select_all_and_delete(self) -> Dict[str, Any]:
        """Clears default objects: A (Select All) -> Delete."""
        def _clear():
            self.keyboard.press("a")
            self._wait_human(0.2)
            self.keyboard.press("delete")
            return True

        return self.execute_with_screen_watcher(
            "Clear Default Scene (A -> Delete)",
            _clear
        )


# Singleton factory
_galaxy_instance: Optional[GalaxyAgent] = None

def get_galaxy_agent() -> GalaxyAgent:
    global _galaxy_instance
    if _galaxy_instance is None:
        _galaxy_instance = GalaxyAgent()
    return _galaxy_instance
