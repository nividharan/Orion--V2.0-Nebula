"""
Unit and integration tests for Nebula Web Engine (Chrome Model) components.
Covers:
- Human-grade interactions (Gaussian delays, smooth scrolling, date injection)
- AuthManager (2FA, OTP detection, human handover)
- CheckoutGuard (financial barriers, payment detection, safety locking)
- ScreenWatcher (pre/post pHash perception, dead-click detection)
- GeminiVisionClient (privacy boundaries, schema parsing, zero-cost gating)
- TelemetryHub & HUD channels
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from web_engine.human_interactions import HumanInteractions
from web_engine.auth_manager import AuthManager
from web_engine.checkout_guard import CheckoutGuard
from verify.screen_watcher import ScreenWatcher, ActionPerceptionResult
from verify.gemini_vision import GeminiVisionClient, VisionRemediation
from hud.telemetry_hub import TelemetryHub, TelemetryState
from hud.terminal_hud import TerminalHUD
from hud.desktop_hud import DesktopHUD


# =========================================================================
# 1. Human-Grade Interactions
# =========================================================================

class TestHumanInteractions:
    def test_keystroke_delay_bounds(self):
        delays = [HumanInteractions.calculate_keystroke_delay(min_ms=20.0, mean_ms=65.0, std_ms=22.0) for _ in range(50)]
        for d in delays:
            assert d >= 0.020  # min delay is 20ms = 0.02s

    @pytest.mark.asyncio
    async def test_human_type(self):
        mock_page = MagicMock()
        mock_keyboard = MagicMock()
        mock_keyboard.type = AsyncMock()
        mock_keyboard.press = AsyncMock()
        mock_page.keyboard = mock_keyboard

        ok = await HumanInteractions.human_type(mock_page, "Hello", clear_first=True, min_ms=1.0, mean_ms=2.0, std_ms=0.5)
        assert ok is True
        assert mock_keyboard.type.call_count == 5

    @pytest.mark.asyncio
    async def test_human_scroll(self):
        mock_page = MagicMock()
        mock_mouse = MagicMock()
        mock_mouse.wheel = AsyncMock()
        mock_page.mouse = mock_mouse

        ok = await HumanInteractions.human_scroll(mock_page, delta_y=300, steps=3)
        assert ok is True
        assert mock_mouse.wheel.call_count == 3

    @pytest.mark.asyncio
    async def test_inject_date(self):
        mock_page = MagicMock()
        mock_page.evaluate = AsyncMock(return_value=True)

        ok = await HumanInteractions.inject_date(mock_page, "input#depDate", "2026-11-15")
        assert ok is True
        mock_page.evaluate.assert_called_once()


# =========================================================================
# 2. AuthManager & 2FA Handover
# =========================================================================

class TestAuthManager:
    @pytest.mark.asyncio
    async def test_detects_otp_input(self):
        mock_page = MagicMock()

        def mock_locator(sel):
            loc = MagicMock()
            if 'one-time-code' in sel:
                loc.count = AsyncMock(return_value=1)
            else:
                loc.count = AsyncMock(return_value=0)
            return loc

        mock_page.locator = mock_locator
        result = await AuthManager.check_auth_required(mock_page)
        assert result["required"] is True
        assert result["type"] == "2fa_input"

    @pytest.mark.asyncio
    async def test_detects_auth_text(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.inner_text = AsyncMock(return_value="Please check your phone for verification code.")

        result = await AuthManager.check_auth_required(mock_page)
        assert result["required"] is True
        assert result["type"] == "auth_challenge_text"

    @pytest.mark.asyncio
    async def test_no_auth_required_on_clean_page(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.inner_text = AsyncMock(return_value="Welcome to Dashboard! Browse catalog items.")

        result = await AuthManager.check_auth_required(mock_page)
        assert result["required"] is False


# =========================================================================
# 3. CheckoutGuard Financial Barrier
# =========================================================================

class TestCheckoutGuard:
    @pytest.mark.asyncio
    async def test_payment_detection(self):
        mock_page = MagicMock()

        def mock_locator(sel):
            loc = MagicMock()
            if 'stripe.com' in sel:
                loc.count = AsyncMock(return_value=1)
            else:
                loc.count = AsyncMock(return_value=0)
            return loc

        mock_page.locator = mock_locator
        mock_page.inner_text = AsyncMock(return_value="Order total: $149.00. Place order now.")

        scan = await CheckoutGuard.scan_payment_surface(mock_page)
        assert scan["payment_detected"] is True
        assert scan["safety_lock_active"] is True

    @pytest.mark.asyncio
    async def test_blocks_action_when_unarmed(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.inner_text = AsyncMock(return_value="Click to Pay Now")

        decision = await CheckoutGuard.verify_action_permitted(mock_page, "submit_payment", armed=False)
        assert decision["allowed"] is False
        assert decision["blocked_reason"] == "checkout_guard_tripped"

    @pytest.mark.asyncio
    async def test_allows_action_when_armed(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=0)
        mock_page.locator = MagicMock(return_value=mock_locator)
        mock_page.inner_text = AsyncMock(return_value="Click to Pay Now")

        decision = await CheckoutGuard.verify_action_permitted(mock_page, "submit_payment", armed=True)
        assert decision["allowed"] is True


# =========================================================================
# 4. ScreenWatcher & Dead-Click Perception
# =========================================================================

class TestScreenWatcher:
    @pytest.mark.asyncio
    async def test_detects_dead_click(self):
        from PIL import Image
        import io

        # 100x100 white image
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        white_bytes = buf.getvalue()

        mock_page = MagicMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.screenshot = AsyncMock(return_value=white_bytes)
        mock_page.url = "https://example.com"
        mock_page.title = MagicMock(return_value="Example Domain")
        mock_loc = MagicMock()
        mock_loc.count = MagicMock(return_value=0)
        mock_loc.inner_text = MagicMock(return_value="Hello world")
        mock_loc.all = MagicMock(return_value=[])
        mock_page.locator = MagicMock(return_value=mock_loc)

        watcher = ScreenWatcher(dead_click_threshold_pct=0.5)

        async def noop_click():
            pass

        result = await watcher.observe_action(mock_page, noop_click, expect_visual_change=True, settle_time_sec=0.01)
        # Before and after are identical white images -> delta is 0% -> dead click flagged!
        assert result.dead_click is True
        assert result.signal == "dead_click_detected"


# =========================================================================
# 5. GeminiVisionClient & Privacy Boundaries
# =========================================================================

class TestGeminiVision:
    def test_privacy_boundary(self):
        client = GeminiVisionClient()
        assert client.is_sensitive_content("https://bank.com/login", "Online Banking") is True
        assert client.is_sensitive_content("https://store.com/checkout", "Cart Checkout") is True
        assert client.is_sensitive_content("https://example.com/blog", "Tech Article") is False

    @pytest.mark.asyncio
    async def test_offline_mode_returns_safe_remediation(self):
        client = GeminiVisionClient(api_key="")
        remediation = await client.analyze_obstacle(b"fake_image", page_url="https://example.com")
        assert remediation.obstacle_detected is False
        assert remediation.recommended_action == "continue"

    @pytest.mark.asyncio
    async def test_sensitive_page_refuses_cloud_call(self):
        client = GeminiVisionClient(api_key="mock_key")
        remediation = await client.analyze_obstacle(b"fake_image", page_url="https://bank.com/signin")
        assert remediation.obstacle_detected is True
        assert remediation.obstacle_type == "sensitive_surface"
        assert remediation.recommended_action == "manual_handover"


# =========================================================================
# 6. TelemetryHub & HUD
# =========================================================================

class TestTelemetryAndHUD:
    def test_telemetry_hub_event_broadcast(self):
        hub = TelemetryHub()
        received = []

        def callback(state):
            received.append(state.status)

        hub.subscribe(callback)
        hub.update(status="RUNNING", current_step="Typing search query")

        assert len(received) == 1
        assert received[0] == "RUNNING"
        assert hub.state.status_emoji == "🟢"

    def test_terminal_hud_format(self):
        hub = TelemetryHub()
        term = TerminalHUD(hub)
        state = TelemetryState(agent_name="Nebula", status="RUNNING", status_emoji="🟢", current_step="Navigating to YouTube")
        formatted = term.format_bar(state)
        assert "[Nebula]" in formatted
        assert "Navigating to YouTube" in formatted

    def test_desktop_hud_instantiation(self):
        hub = TelemetryHub()
        hud = DesktopHUD(hub)
        assert hud._is_running is False


# =========================================================================
# 7. Phase 3: FreezeDetector & CrashBannerDetector
# =========================================================================

class TestFreezeAndCrashDetectors:
    def test_crash_banner_detection(self):
        from verify.screen_watcher import CrashBannerDetector
        crashed, pattern = CrashBannerDetector.check_crash("Google Chrome error: Aw, Snap! Something went wrong.")
        assert crashed is True
        assert "aw" in pattern

        crashed, _ = CrashBannerDetector.check_crash("Welcome to Google Home")
        assert crashed is False

    @pytest.mark.asyncio
    async def test_freeze_detector_on_static_surface(self):
        from verify.screen_watcher import FreezeDetector
        from PIL import Image
        import io

        img = Image.new("RGB", (60, 60), (100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        frame_bytes = buf.getvalue()

        detector = FreezeDetector(sample_interval_sec=0.01, freeze_threshold_pct=0.05)
        report = await detector.check_surface_activity(lambda: frame_bytes, duration_sec=0.05)

        assert report.is_frozen is True
        assert report.max_delta_pct == 0.0


# =========================================================================
# 8. Phase 4: PIIRedactor in GeminiVision
# =========================================================================

class TestPIIRedaction:
    def test_redact_sensitive_rectangles(self):
        from verify.gemini_vision import PIIRedactor
        from PIL import Image
        import io

        # 100x100 white image
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        orig_bytes = buf.getvalue()

        # Redact a 20x20 box at (10, 10)
        rects = [{"x": 10, "y": 10, "width": 20, "height": 20}]
        redacted_bytes = PIIRedactor.redact_boxes(orig_bytes, rects)
        assert len(redacted_bytes) > 0

        # Verify pixels in redacted area are black
        out_img = Image.open(io.BytesIO(redacted_bytes))
        pixel = out_img.getpixel((15, 15))
        assert pixel == (0, 0, 0)  # Pure black fill


# =========================================================================
# 9. Phase 5: API Server Endpoints
# =========================================================================

class TestApiServer:
    @pytest.mark.asyncio
    async def test_health_and_telemetry_endpoints(self):
        from fastapi.testclient import TestClient
        import api_server
        client = TestClient(api_server.app)

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ok"

        telemetry_resp = client.get("/telemetry")
        assert telemetry_resp.status_code == 200
        assert "status" in telemetry_resp.json()

        kill_resp = client.post("/kill")
        assert kill_resp.status_code == 200
        assert kill_resp.json()["status"] == "stopped"


# =========================================================================
# 10. Phase 6: AutoGen Society 3D Blender Routing
# =========================================================================

class TestAutoGenSocietyRouter:
    def test_routes_blender_3d_goal(self):
        from orion_autogen import NebulaModel
        model = NebulaModel(use_voice=False, minimal=True)

        plan = model.decompose_goal("open blender and add cube and render")
        agents = [s["agent"] for s in plan]
        actions = [s["action"] for s in plan]

        assert "Blender Executor" in agents
        assert "launch" in actions
        assert "hotkey" in actions
        assert "render" in actions
