"""Local loopback UI for a bounded joint Step 8 reconciliation session."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

try:  # Package import in the repository; direct import in the self-contained ZIP.
    from .reconciliation import ReconciliationError, ReconciliationService
except ImportError:  # pragma: no cover - exercised by the distributable launcher.
    from reconciliation import ReconciliationError, ReconciliationService


STATIC = Path(__file__).with_name("reconciliation_static")
ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}


def runtime_hash() -> str:
    """Bind the reconciliation executable and static UI files exactly."""

    paths = [Path(__file__), Path(__file__).with_name("reconciliation.py"), *(STATIC / name for name, _ in ASSETS.values())]
    files = {path.name if path.parent == STATIC else path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_handler(service: ReconciliationService) -> type[BaseHTTPRequestHandler]:
    """Serve fixed local reconciliation routes with same-origin write protection."""

    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        """Serve only frozen items and local final decisions."""

        def reply(self, status: int, value: bytes, mime: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(value)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(value)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/api/state":
                    self.reply(200, json.dumps({**service.state(), "csrfToken": csrf}).encode())
                elif path == "/api/package":
                    self.reply(200, json.dumps(sorted(service.items)).encode())
                elif path.startswith("/api/item/"):
                    self.reply(200, json.dumps(service.item(unquote(path[len("/api/item/"):]))).encode())
                elif path in ASSETS:
                    name, mime = ASSETS[path]
                    self.reply(200, (STATIC / name).read_bytes(), mime)
                else:
                    self.reply(404, b'{"error":"NOT_FOUND"}')
            except ReconciliationError as exc:
                self.reply(409, json.dumps({"error": str(exc)}).encode())

        def do_POST(self) -> None:
            origin = self.headers.get("Origin")
            expected_origin = "http://" + str(self.headers.get("Host"))
            if self.path != "/api/decision" or self.headers.get("X-Reconciliation-Token") != csrf or (origin and origin != expected_origin):
                self.reply(403, b'{"error":"ACTION_NOT_AUTHORIZED"}')
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                if not isinstance(body, dict) or set(body) != {"expectedRevision", "judgmentItemID", "decision"}:
                    raise ReconciliationError("INVALID_RECONCILIATION_REQUEST")
                self.reply(200, json.dumps(service.decide(body["expectedRevision"], body["judgmentItemID"], body["decision"])).encode())
            except (ReconciliationError, ValueError, TypeError) as exc:
                self.reply(409, json.dumps({"error": str(exc) if isinstance(exc, ReconciliationError) else "INVALID_RECONCILIATION_REQUEST"}).encode())

    return Handler


def main() -> int:
    """Start the local UI or write a final export from the same package-local state."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "start", "final"))
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    try:
        service = ReconciliationService(args.package, args.state)
        if args.action == "verify":
            print(json.dumps({"packageSha256": service.package_hash, **service.state()}, sort_keys=True))
        elif args.action == "final":
            if args.export is None:
                raise ReconciliationError("RECONCILIATION_EXPORT_PATH_REQUIRED")
            data = service.export(runtime_hash())
            if args.export.exists() and args.export.read_bytes() != data:
                raise ReconciliationError("RECONCILIATION_EXPORT_CONFLICT")
            args.export.parent.mkdir(parents=True, exist_ok=True)
            args.export.write_bytes(data)
            print(args.export)
        else:
            server = HTTPServer(("127.0.0.1", args.port), make_handler(service))
            print(f"Step 8 reconciliation at http://127.0.0.1:{server.server_port}")
            try:
                server.serve_forever()
            finally:
                server.server_close()
        return 0
    except (ReconciliationError, OSError, ValueError) as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
