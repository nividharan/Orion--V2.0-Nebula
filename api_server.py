"""
API Gateway & Real-Time Telemetry Server for Orion & Nebula.
Phase 5 Implementation:
- FastAPI REST API + WebSocket streaming for live telemetry HUD.
- Controls execution dispatch, emergency kill-switch, and floating HUD pill.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hud.telemetry_hub import TelemetryHub, TelemetryState
from hud.desktop_hud import DesktopHUD

logger = logging.getLogger("orion.api_server")

app = FastAPI(
    title="Orion × Nebula Autonomous API Gateway",
    version="2.0.0",
    description="REST & WebSocket API Gateway for Universal Desktop & Chrome Automation."
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


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "system": "Orion",
        "model": "Nebula",
        "version": "2.0.0",
        "telemetry_state": TelemetryHub.get_instance().state.status
    }


@app.get("/telemetry")
async def get_telemetry() -> Dict[str, Any]:
    return TelemetryHub.get_instance().to_dict()


@app.post("/execute")
async def execute_goal(req: CommandRequest) -> Dict[str, Any]:
    """Dispatches a goal to the AutoGen Multi-Agent Society."""
    try:
        from orion_autogen import NebulaModel
        model = NebulaModel(use_voice=req.use_voice, minimal=req.minimal)
        result = model.run_collaborative_workflow(req.goal)
        return {"ok": True, "result": result}
    except Exception as e:
        logger.error("Execution failed: %s", e)
        TelemetryHub.get_instance().update(status="ERROR", current_step=f"Error: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/kill")
async def trigger_kill_switch() -> Dict[str, Any]:
    """Emergency kill switch to halt active automation."""
    TelemetryHub.get_instance().update(status="PAUSED", current_step="Emergency Kill Switch Triggered")
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
    # Send initial state
    await websocket.send_json(TelemetryHub.get_instance().to_dict())

    try:
        while True:
            # Keep-alive loop receiving client pings
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
