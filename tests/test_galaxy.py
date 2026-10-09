"""
test_galaxy.py — Unit and Integration Tests for Galaxy 3D Agent & Screen Watcher
================================================================================
Validates:
1. GalaxyAgent instantiation and singleton retrieval.
2. NebulaModel intent compilation routing to Galaxy Model for 3D tasks.
3. Closed-loop Screen Watcher perception verification (delta %, verdict, latency).
4. Human-level Blender operations mocking and execution flow.
"""

from unittest.mock import MagicMock, patch
import pytest

from galaxy import GalaxyAgent, get_galaxy_agent
from orion_autogen import NebulaModel
from verify.page_watcher import Verdict


@pytest.fixture
def galaxy_agent():
    """Returns a GalaxyAgent with mocked hardware drivers for fast test runs."""
    with patch("galaxy.OrionSubstrate") as mock_sub_cls:
        mock_sub = MagicMock()
        mock_sub_cls.return_value = mock_sub

        # Mock blender adapter
        mock_blender = MagicMock()
        mock_sub.get_adapter.return_value = mock_blender

        # Mock screen capture with synthetic bytes
        mock_sub.sc.capture_screen.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest1"
        mock_sub.sc.capture_window.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest2"

        # Mock window manager
        mock_sub.wm.set_foreground.return_value = True

        agent = GalaxyAgent(human_speed=False)
        return agent


def test_galaxy_singleton():
    """Verify singleton factory returns consistent instance."""
    agent1 = get_galaxy_agent()
    agent2 = get_galaxy_agent()
    assert agent1 is agent2
    assert isinstance(agent1, GalaxyAgent)


def test_galaxy_initialization(galaxy_agent):
    """Verify GalaxyAgent initializes components properly."""
    assert galaxy_agent.blender is not None
    assert galaxy_agent.mouse is not None
    assert galaxy_agent.keyboard is not None
    assert galaxy_agent.sc is not None
    assert galaxy_agent.wm is not None
    assert len(galaxy_agent.perception_history) == 0


def test_galaxy_execute_with_screen_watcher(galaxy_agent):
    """Verify closed-loop Screen Watcher perception evaluates action and logs visual delta."""
    with patch("galaxy.calculate_visual_diff_pct", return_value=5.4):
        action_fn = MagicMock(return_value=True)

        res = galaxy_agent.execute_with_screen_watcher("Mock Orbit", action_fn, min_delta_pct=0.1)

        assert res["action"] == "Mock Orbit"
        assert res["success"] is True
        assert res["visual_delta_pct"] == 5.4
        assert res["verdict"] == Verdict.OK.value
        assert len(galaxy_agent.perception_history) == 1
        assert galaxy_agent.perception_history[0].dead_click is False


def test_galaxy_execute_dead_click(galaxy_agent):
    """Verify dead click is detected when visual delta is below threshold."""
    with patch("galaxy.calculate_visual_diff_pct", return_value=0.0):
        action_fn = MagicMock(return_value=True)

        res = galaxy_agent.execute_with_screen_watcher("Mock Dead Click", action_fn, min_delta_pct=0.1)

        assert res["visual_delta_pct"] == 0.0
        assert res["verdict"] == Verdict.UNCERTAIN.value
        assert galaxy_agent.perception_history[-1].dead_click is True


def test_galaxy_human_operations(galaxy_agent):
    """Verify high-level 3D operations trigger respective hotkeys and actions."""
    with patch("galaxy.calculate_visual_diff_pct", return_value=12.0):
        # 1. Open Add Menu
        res_add = galaxy_agent.open_add_menu()
        assert res_add["success"] is True

        # 2. Add Mesh Primitive
        res_mesh = galaxy_agent.add_mesh_primitive("uv_sphere")
        assert res_mesh["success"] is True

        # 3. Orbit 3D Viewport
        res_orbit = galaxy_agent.orbit_3d_viewport(100, -50)
        assert res_orbit["success"] is True

        # 4. Pan 3D Viewport
        res_pan = galaxy_agent.pan_3d_viewport(50, 0)
        assert res_pan["success"] is True

        # 5. Zoom 3D Viewport
        res_zoom = galaxy_agent.zoom_3d_viewport(3)
        assert res_zoom["success"] is True

        # 6. Set Shading
        res_shade = galaxy_agent.set_viewport_shading("rendered")
        assert res_shade["success"] is True

        # 7. Grab and Move
        res_grab = galaxy_agent.grab_and_move(axis="x", dx=40, dy=0)
        assert res_grab["success"] is True

        # 8. Scale Object
        res_scale = galaxy_agent.scale_object("2.0")
        assert res_scale["success"] is True

        # 9. Rotate Object
        res_rotate = galaxy_agent.rotate_object(axis="z", degrees="90")
        assert res_rotate["success"] is True

        # 10. Select All and Delete
        res_clear = galaxy_agent.select_all_and_delete()
        assert res_clear["success"] is True

        # 11. Trigger Render
        res_render = galaxy_agent.trigger_render()
        assert res_render["success"] is True


def test_nebula_intent_compilation_galaxy_3d():
    """Verify Nebula Model accurately routes 3D goals to Galaxy Model."""
    nebula = NebulaModel(use_voice=False, minimal=True)

    # Test Case 1: Add Sphere in Blender
    steps = nebula.decompose_goal("open blender and add sphere")
    agents = [s["agent"] for s in steps]
    actions = [s["action"] for s in steps]

    assert "Galaxy Model" in agents
    assert "launch" in actions
    assert "focus" in actions
    assert "add_mesh" in actions

    # Verify sphere was detected
    add_step = next(s for s in steps if s.get("action") == "add_mesh")
    assert add_step["mesh"] == "uv_sphere"

    # Test Case 2: Orbit viewport and rendered shading
    steps2 = nebula.decompose_goal("galaxy model orbit viewport and switch shading to rendered")
    actions2 = [s["action"] for s in steps2]
    assert "orbit" in actions2
    assert "shading" in actions2
