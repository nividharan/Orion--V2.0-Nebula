"""
control_channel.py — Local IPC Control Channel for Running Session (Optional)
==============================================================================
Allows a secondary terminal to send commands to an active running session:
- Binds strictly to 127.0.0.1 (localhost only).
- Off by default (enabled via config.control_channel_enabled).
- Authenticated via random cryptographic token saved to owner-only file in .cache/.
- Enforces domain allow-list, action validation, and blocks sensitive actions over control channel.
"""

from __future__ import annotations

import os
import sys
import json
import secrets
import logging
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

from config import CACHE_DIR
from session import NebulaSession

logger = logging.getLogger("Orion.ControlChannel")
DEFAULT_PORT = 8769
TOKEN_FILE = CACHE_DIR / "control_token"


class ControlChannelHandler(BaseHTTPRequestHandler):
    """Local HTTP request handler bound strictly to 127.0.0.1."""
    session: Optional[NebulaSession] = None
    auth_token: str = ""

    def log_message(self, format, *args):
        # Suppress standard logging to keep REPL clean
        pass

    def do_POST(self):
        client_address = self.client_address[0]
        if client_address not in ("127.0.0.1", "localhost", "::1"):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error": "forbidden", "message": "Only localhost is permitted."}')
            return

        provided_token = self.headers.get("X-Nebula-Token", "")
        if not secrets.compare_digest(provided_token, self.auth_token):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error": "unauthorized", "message": "Invalid authentication token."}')
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            data = json.loads(body)
            cmd = data.get("command", "").strip()
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "bad_request", "message": "Invalid JSON payload."}')
            return

        if not cmd:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "bad_request", "message": "Missing command."}')
            return

        if not self.session:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'{"error": "unavailable", "message": "No active session."}')
            return

        # Execute command through session with strict non-interactive approval denial
        result = self.session.execute_command_string(cmd, approver=None)
        resp_bytes = json.dumps(result).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)


class LocalControlServer:
    """Manages lifecycle of local 127.0.0.1 HTTP control server."""

    def __init__(self, session: NebulaSession, port: int = DEFAULT_PORT):
        self.session = session
        self.port = port
        self.token = secrets.token_hex(24)
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts server in background thread and saves owner-only token file."""
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(self.token, encoding="utf-8")
        try:
            # Set owner-only permissions on Windows / POSIX
            os.chmod(TOKEN_FILE, 0o600)
        except Exception:
            pass

        class ConfiguredHandler(ControlChannelHandler):
            session = self.session
            auth_token = self.token

        self.server = HTTPServer(("127.0.0.1", self.port), ConfiguredHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="NebulaControlServer")
        self.thread.start()
        logger.info(f"Local control channel listening on http://127.0.0.1:{self.port}")

    def stop(self) -> None:
        """Shuts down server and removes token file."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if TOKEN_FILE.exists():
            try:
                TOKEN_FILE.unlink()
            except Exception:
                pass


def send_command_to_running_session(command: str, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Sends command string from secondary terminal to running session."""
    if not TOKEN_FILE.exists():
        return {"ok": False, "error": "not_running", "message": "No active session control token found in .cache/."}

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    url = f"http://127.0.0.1:{port}/command"
    payload = json.dumps({"command": command}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "X-Nebula-Token": token},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as he:
        body = he.read().decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {"ok": False, "error": f"http_{he.code}", "message": str(he)}
    except Exception as e:
        return {"ok": False, "error": "connection_error", "message": str(e)}
