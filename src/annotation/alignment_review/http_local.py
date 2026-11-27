"""Portable adaptation of the Study 2 loopback review API for an isolated evaluator."""

from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse


def review_handler(service, static: Path, assets: dict) -> type[BaseHTTPRequestHandler]:
    """Bind a single service; no endpoint can select another reviewer or file."""

    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        """Serve fixed local assets and the bounded blinded review API."""

        def reply(
            self, status: int, value: bytes, mime: str = "application/json"
        ) -> None:
            """Send non-cacheable responses with same-origin resource restrictions."""

            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(value)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(value)

        def do_GET(self) -> None:
            """Read only session-local state, exact unit content, or export."""

            path = urlparse(self.path).path
            try:
                if path == "/api/state":
                    self.reply(
                        200, json.dumps({**service.state(), "csrfToken": csrf}).encode()
                    )
                elif path.startswith("/api/unit/"):
                    self.reply(
                        200,
                        json.dumps(
                            service.unit(unquote(path[len("/api/unit/") :]))
                        ).encode(),
                    )
                elif path == "/api/export":
                    self.reply(200, service.export())
                elif path in assets:
                    name, mime = assets[path]
                    self.reply(200, (static / name).read_bytes(), mime)
                else:
                    self.reply(404, b'{"error":"NOT_FOUND"}')
            except ValueError as exc:
                self.reply(409, json.dumps({"error": str(exc)}).encode())

        def do_POST(self) -> None:
            """Persist deliberate same-origin actions with revision checks."""

            origin = self.headers.get("Origin")
            expected_origin = "http://" + str(self.headers.get("Host"))
            if (
                self.path != "/api/action"
                or self.headers.get("X-Review-Token") != csrf
                or (origin and origin != expected_origin)
            ):
                self.reply(403, b'{"error":"ACTION_NOT_AUTHORIZED"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("INVALID_BODY_LENGTH")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("JSON_OBJECT_REQUIRED")
                self.reply(200, json.dumps(service.change(body)).encode())
            except (KeyError, ValueError, TypeError) as exc:
                message = str(exc) if isinstance(exc, ValueError) else "INVALID_REQUEST"
                self.reply(409, json.dumps({"error": message}).encode())

    return Handler
