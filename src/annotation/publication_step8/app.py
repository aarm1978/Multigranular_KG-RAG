"""Run one isolated local Step 8 initial human-review session."""

from __future__ import annotations

import argparse
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import ROOT, ReviewError, ReviewInputs
from .service import ReviewService, activation_requirements

STATIC = Path(__file__).with_name("static")
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}


def make_handler(service: ReviewService) -> type[BaseHTTPRequestHandler]:
    """Bind a single service; no endpoint can select another reviewer or file."""

    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        """Serve fixed local assets and the bounded blinded review API."""

        def reply(self, status: int, value: bytes, mime: str = "application/json") -> None:
            """Send non-cacheable responses with same-origin resource restrictions."""

            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(value)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(value)

        def do_GET(self) -> None:
            """Read only session-local state, exact unit content, or export."""

            path = urlparse(self.path).path
            try:
                service.guard()
                if path == "/api/state":
                    self.reply(200, json.dumps({**service.state(), "csrfToken": csrf}).encode())
                elif path.startswith("/api/unit/"):
                    self.reply(200, json.dumps(service.unit(unquote(path[len("/api/unit/"):]))).encode())
                elif path == "/api/export":
                    self.reply(200, service.export())
                elif path in ASSETS:
                    name, mime = ASSETS[path]
                    self.reply(200, (STATIC / name).read_bytes(), mime)
                else:
                    self.reply(404, b'{"error":"NOT_FOUND"}')
            except ReviewError as exc:
                self.reply(409, json.dumps({"error": str(exc)}).encode())

        def do_POST(self) -> None:
            """Persist deliberate same-origin actions with revision checks."""

            origin = self.headers.get("Origin")
            expected_origin = "http://" + str(self.headers.get("Host"))
            if self.path != "/api/action" or self.headers.get("X-Review-Token") != csrf or (origin and origin != expected_origin):
                self.reply(403, b'{"error":"ACTION_NOT_AUTHORIZED"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ReviewError("INVALID_BODY_LENGTH")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ReviewError("JSON_OBJECT_REQUIRED")
                self.reply(200, json.dumps(service.change(body)).encode())
            except (ReviewError, ValueError, TypeError) as exc:
                message = str(exc) if isinstance(exc, ReviewError) else "INVALID_REQUEST"
                self.reply(409, json.dumps({"error": message}).encode())

    return Handler


def main() -> None:
    """Default to dry-run; production requires an exact operator activation file."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("primary", "second"), required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--mode", choices=("dry-run", "production"), default="dry-run")
    parser.add_argument("--activation-file", type=Path)
    parser.add_argument("--state-root", type=Path, default=ROOT / "var/publication_step8_review")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--print-activation-requirements", action="store_true")
    args = parser.parse_args()
    inputs = ReviewInputs(args.role)
    if args.print_activation_requirements:
        print(json.dumps(activation_requirements(inputs, args.session_id, args.reviewer_id), indent=2))
        return
    service = ReviewService(inputs, args.state_root, args.session_id, args.reviewer_id, args.mode, args.activation_file)
    server = HTTPServer(("127.0.0.1", args.port), make_handler(service))
    print(f"{args.mode} {args.role} review at http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
