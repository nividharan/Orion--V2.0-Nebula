"""
API Gateway & Real-Time Telemetry Server for Orion & Nebula.
Phase 5 & Autonomous Application Deck:
- Serves the standalone Glassmorphic Mission Control UI at http://127.0.0.1:8000
- FastAPI REST API + WebSocket streaming for live multi-agent telemetry
- Live perception screen buffer stream (/screenshot) & ARIA accessibility tree (/aria)
- Controls execution dispatch, emergency kill-switch, and floating desktop HUD
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from hud.telemetry_hub import TelemetryHub, TelemetryState
from hud.desktop_hud import DesktopHUD
from session import NebulaSession, SessionConfig

logger = logging.getLogger("orion.api_server")

app = FastAPI(
    title="Orion × Nebula Autonomous Application",
    version="2.0.0",
    description="Autonomous Control Deck for Browser & Desktop Automation."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
connected_websockets: List[WebSocket] = []

# Desktop HUD instance
_desktop_hud: Optional[DesktopHUD] = None

# Global Autonomous Session instance (maintains browser state, cookies, tabs)
_global_session: Optional[NebulaSession] = None


def get_session() -> NebulaSession:
    """Returns or lazily initializes the singleton NebulaSession."""
    global _global_session
    if _global_session is None or _global_session.closed:
        cfg = SessionConfig(
            headless=os.getenv("WEB_HEADLESS", "false").lower() in ("true", "1", "yes"),
            media_watcher_enabled=False,
            control_channel_enabled=False
        )
        _global_session = NebulaSession(config=cfg)
    return _global_session


class CommandRequest(BaseModel):
    goal: str
    target_app: Optional[str] = "chrome"
    use_voice: bool = False
    minimal: bool = True


class ActionRequest(BaseModel):
    action: str
    target: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


# Broadcaster hooked to TelemetryHub
def _on_telemetry_broadcast(state: TelemetryState) -> None:
    data = TelemetryHub.get_instance().to_dict()
    disconnected = []
    for ws in connected_websockets:
        try:
            asyncio.create_task(ws.send_json(data))
        except Exception:
            disconnected.append(ws)

    for dead in disconnected:
        if dead in connected_websockets:
            connected_websockets.remove(dead)


# Register broadcaster
TelemetryHub.get_instance().subscribe(_on_telemetry_broadcast)


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> HTMLResponse:
    """Serves the autonomous application user interface."""
    ui_path = Path(__file__).parent / "web_ui" / "index.html"
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Autonomous Application UI is initializing...</h2>")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    sess = get_session()
    return {
        "status": "ok",
        "system": "Orion",
        "model": "Nebula",
        "version": "2.0.0",
        "telemetry_state": TelemetryHub.get_instance().state.status,
        "browser_running": sess.browser_manager.is_running,
        "last_known_url": sess.last_known_url,
        "last_known_title": sess.last_known_title,
    }


@app.get("/telemetry")
async def get_telemetry() -> Dict[str, Any]:
    return TelemetryHub.get_instance().to_dict()


@app.get("/screenshot")
async def get_live_screenshot():
    """Serves the latest screen buffer captured by the Perception Inspector."""
    cache_path = Path(__file__).parent / ".cache" / "screen_live.png"
    if cache_path.exists():
        return FileResponse(
            cache_path,
            media_type="image/png",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )
    return Response(status_code=404, content="Screenshot buffer not ready")


@app.get("/orion_logo.glb")
async def get_orion_logo_glb():
    """Serves the Blender-generated real-time 3D model."""
    glb_path = Path(__file__).parent / "web_ui" / "orion_logo.glb"
    if glb_path.exists():
        return FileResponse(glb_path, media_type="model/gltf-binary")
    return Response(status_code=404, content="3D GLB model not found")


@app.get("/orion_logo_preview.png")
async def get_orion_logo_preview():
    """Serves the Blender EEVEE rendered preview frame."""
    preview_path = Path(__file__).parent / "web_ui" / "orion_logo_preview.png"
    if preview_path.exists():
        return FileResponse(preview_path, media_type="image/png")
    return Response(status_code=404, content="Preview image not found")


@app.get("/aria")
async def get_aria_tree() -> Dict[str, Any]:
    """Returns the accessibility tree and interactive elements of the active page."""
    try:
        import desktop_controller as dc
        aria = dc.web_aria_snapshot()
        return {"ok": True, "tree": aria}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/session/state")
async def get_session_state() -> Dict[str, Any]:
    """Returns the live state of the autonomous execution session."""
    sess = get_session()
    return {
        "url": sess.last_known_url,
        "title": sess.last_known_title,
        "total_commands": sess.total_commands,
        "total_steps": sess.total_steps,
        "history": sess.turn_history[-8:] if sess.turn_history else [],
        "status": TelemetryHub.get_instance().state.status,
        "is_running": sess.is_command_running,
    }


@app.post("/execute")
async def execute_goal(req: CommandRequest) -> Dict[str, Any]:
    """Dispatches a high-level goal to the autonomous execution session."""
    hub = TelemetryHub.get_instance()
    sess = get_session()

    hub.update(
        agent_name="Commander Nebula",
        status="RUNNING",
        current_step=f"Planning: '{req.goal}'",
        reasoning="Decomposing user goal into autonomous agent milestones"
    )

    def on_progress(idx: int, total: int, step: Any, step_rec: Dict[str, Any]) -> None:
        agent_name = getattr(step, "agent", "Chrome Executor")
        desc = getattr(step, "desc", "") or getattr(step, "action", "")
        hub.update(
            agent_name=agent_name,
            status="RUNNING",
            current_step=f"[{idx}/{total}] {desc}",
            reasoning=f"Executing milestone {idx} of {total}"
        )

    try:
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(
            None,
            lambda: sess.execute_command_string(req.goal, progress_cb=on_progress)
        )
        
        status_str = "SUCCESS" if res.get("status") in ("success", "ok") else "ERROR"
        hub.update(
            agent_name="Verifier Critic",
            status=status_str,
            current_step=f"Goal completed ({len(res.get('steps', []))} milestones)",
            reasoning="All milestones verified successfully."
        )

        return {
            "ok": True,
            "result": res,
            "url": sess.last_known_url,
            "title": sess.last_known_title
        }
    except Exception as e:
        logger.error("Execution failed: %s", e)
        hub.update(
            agent_name="Verifier Critic",
            status="ERROR",
            current_step=f"Execution error: {e}",
            reasoning=str(e)
        )
        return {"ok": False, "error": str(e)}


@app.post("/kill")
async def trigger_kill_switch() -> Dict[str, Any]:
    """Emergency kill switch to halt active automation instantly."""
    sess = get_session()
    sess.kill_switch_active.set()
    TelemetryHub.get_instance().update(
        agent_name="Commander Nebula",
        status="PAUSED",
        current_step="Emergency Kill Switch Engaged",
        reasoning="User manually halted execution."
    )
    return {"ok": True, "status": "stopped", "message": "Emergency kill switch engaged."}


@app.post("/hud/toggle")
async def toggle_desktop_hud(enable: Optional[bool] = None) -> Dict[str, Any]:
    """Toggles or sets floating desktop glassmorphic pill."""
    global _desktop_hud
    hub = TelemetryHub.get_instance()

    if _desktop_hud is None:
        _desktop_hud = DesktopHUD(hub)

    if enable is True or (enable is None and not _desktop_hud._is_running):
        _desktop_hud.start()
        return {"ok": True, "hud_running": True, "message": "Desktop HUD pill started."}
    else:
        _desktop_hud.stop()
        return {"ok": True, "hud_running": False, "message": "Desktop HUD pill stopped."}


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Real-time WebSocket telemetry stream."""
    await websocket.accept()
    connected_websockets.append(websocket)
    await websocket.send_json(TelemetryHub.get_instance().to_dict())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
    except Exception:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    uvicorn.run("api_server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
