"""
ARYx AGENT - Web UI adapter (Section 16.7).

FastAPI was the spec's suggestion, but a dependency-free stdlib
server keeps the base install light and the UI a single HTML file
with no build step. Trade-off, stated honestly: this v1 answers
with normal request/response (the browser polls the reply) rather
than WebSocket streaming. The agent, memory and approvals are the
same as every other channel.

Auth: one token (from gateway.toml [webui] auth_token), passed as
?token= or the X-ARYx-Token header. Default bind is 127.0.0.1 only.
"""

from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from aryx.gateway.core import GatewayCore
from aryx.gateway.types import IncomingMessage

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "webui.html"

_FALLBACK_HTML = """<!doctype html><html><body style="background:#0d1117;color:#e6edf3;font-family:monospace">
<h2>ARYx Web UI</h2><p>Template file missing. Use /api/chat with your token.</p>
</body></html>"""


class WebUIAdapter:
    def __init__(
        self,
        core: GatewayCore,
        host: str = "127.0.0.1",
        port: int = 8765,
        auth_token: str = "",
    ) -> None:
        if not auth_token:
            raise ValueError(
                "Web UI needs an auth token. Run `aryx gateway setup` or set "
                "[webui] auth_token in gateway.toml."
            )
        self.core = core
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    # -- HTTP plumbing ------------------------------------------------------
    def _handler_class(self) -> Any:
        adapter = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:
                pass  # Gateway logs live in gateway.log, not stdout spam.

            def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _authed(self, query: Dict[str, Any], body: Dict[str, Any]) -> bool:
                token = body.get("token") or query.get("token", [None])[0]
                header = self.headers.get("X-ARYx-Token", "")
                candidate = token or header
                return bool(candidate) and secrets.compare_digest(str(candidate), adapter.auth_token)

            def _read_json(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length") or 0)
                if not length:
                    return {}
                try:
                    return json.loads(self.rfile.read(length) or b"{}")
                except (json.JSONDecodeError, ValueError):
                    return {}

            def do_GET(self) -> None:  # noqa: N802
                from urllib.parse import urlparse, parse_qs

                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if parsed.path == "/":
                    html = _FALLBACK_HTML
                    if _TEMPLATE_PATH.exists():
                        html = _TEMPLATE_PATH.read_text(encoding="utf-8")
                    body = html.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed.path == "/api/status":
                    if not self._authed(query, {}):
                        self._send_json({"ok": False, "error": "unauthorized"}, 401)
                        return
                    status = adapter.core.status_table()
                    self._send_json({"ok": True, "status": status})
                    return
                self._send_json({"ok": False, "error": "not found"}, 404)

            def do_POST(self) -> None:  # noqa: N802
                from urllib.parse import urlparse, parse_qs

                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                body = self._read_json()
                if not self._authed(query, body):
                    self._send_json({"ok": False, "error": "unauthorized"}, 401)
                    return
                if parsed.path == "/api/chat":
                    text = str(body.get("text", ""))
                    incoming = IncomingMessage(
                        channel="webui", user_id="webui", username="web", text=text
                    )
                    reply = adapter.core.handle_message(incoming)
                    if reply is None:
                        self._send_json({"ok": True, "reply": "", "buttons": []})
                    else:
                        self._send_json(
                            {
                                "ok": True,
                                "reply": reply.text,
                                "buttons": reply.buttons,
                                "approval": reply.approval is not None,
                            }
                        )
                    return
                if parsed.path == "/api/approve":
                    approved = bool(body.get("approved"))
                    incoming = IncomingMessage(
                        channel="webui",
                        user_id="webui",
                        username="web",
                        text="",
                        callback_data="approve" if approved else "reject",
                    )
                    reply = adapter.core.handle_message(incoming)
                    self._send_json(
                        {"ok": True, "reply": reply.text if reply else "", "buttons": reply.buttons if reply else []}
                    )
                    return
                self._send_json({"ok": False, "error": "not found"}, 404)

        return Handler

    def url(self) -> str:
        return f"http://{self.host}:{self.port}/?token={self.auth_token}"

    def run_forever(self) -> None:
        """Blocking. `aryx gateway start` runs this in a thread."""
        self._server = ThreadingHTTPServer((self.host, self.port), self._handler_class())
        self._server.serve_forever()

    def start_in_thread(self) -> threading.Thread:
        self._thread = threading.Thread(target=self.run_forever, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
