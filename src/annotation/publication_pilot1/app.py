"""Run the local Publication Pilot 1 human screening web interface."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import ContractError, PROTECTED_HASHES, load_contracts
from .service import ScreeningService
from .store import DraftStore


def repository_root() -> Path:
    """Return the repository root from this module's stable location."""

    return Path(__file__).resolve().parents[3]


def _audit_hashes(observed: dict[str, str]) -> dict[str, str]:
    """Map protected path hashes to the sidecar's named contract fields."""

    return {
        "canonicalWorklistHash": observed["data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv"],
        "targetDisplayCatalogHash": observed["data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml"],
        "targetFamilyMappingHash": observed["data/curation/papers/pilot1/publication_pilot1_target_family_mapping.yaml"],
        "screeningSchemaHash": observed["schemas/publication_pilot1_screening_record.schema.json"],
        "selectionPolicyHash": observed["data/curation/papers/pilot1/publication_pilot1_selection_policy.yaml"],
    }


def make_handler(service: ScreeningService) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to one application service."""

    static_dir = Path(__file__).with_name("static")

    class Handler(BaseHTTPRequestHandler):
        """Serve the local static UI and its JSON API."""

        def _json(self, status: int, payload: object) -> None:
            """Send one UTF-8 JSON response."""

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict[str, object]:
            """Read a bounded JSON request body."""

            length = int(self.headers.get("Content-Length", "0"))
            if length > 2_000_000:
                raise ContractError("REQUEST_BODY_TOO_LARGE")
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict):
                raise ContractError("JSON_OBJECT_REQUIRED")
            return value

        def do_GET(self) -> None:  # noqa: N802
            """Serve application state, one validated unit, or a local static asset."""

            try:
                parsed = urlparse(self.path)
                if parsed.path == "/api/bootstrap":
                    self._json(HTTPStatus.OK, service.bootstrap())
                    return
                if parsed.path.startswith("/api/units/"):
                    self._json(HTTPStatus.OK, service.unit(unquote(parsed.path.removeprefix("/api/units/"))))
                    return
                asset = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                path = (static_dir / asset).resolve()
                if static_dir.resolve() not in path.parents or not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except (ContractError, ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            """Handle deliberate reviewer changes, exports, and dry-run resets."""

            try:
                body = self._body()
                if self.path == "/api/reviewer":
                    service.store.change_reviewer(str(body.get("reviewerID", "")))
                    self._json(HTTPStatus.OK, {
                        "reviewerID": service.store.reviewer_id(),
                        "reviewerLocked": service.store.reviewer_locked(),
                    })
                    return
                if self.path == "/api/export":
                    path = service.export(complete=body.get("kind") == "complete")
                    self._json(HTTPStatus.OK, {"path": str(path), "complete": body.get("kind") == "complete"})
                    return
                if self.path == "/api/dry-run/reset":
                    if not service.dry_run:
                        raise ContractError("PRODUCTION_RESET_FORBIDDEN")
                    service.store.reset()
                    self._json(HTTPStatus.OK, {"reset": True})
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except (ContractError, ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def do_PUT(self) -> None:  # noqa: N802
            """Autosave or complete one open unit."""

            try:
                if not self.path.startswith("/api/units/"):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = self._body()
                payload = body.get("draft", {})
                if not isinstance(payload, dict):
                    raise ContractError("DRAFT_OBJECT_REQUIRED")
                result = service.save(
                    unquote(urlparse(self.path).path.removeprefix("/api/units/")),
                    payload,
                    bool(body.get("markReviewed", False)),
                )
                self._json(HTTPStatus.OK, result)
            except (ContractError, ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def log_message(self, format_string: str, *args: object) -> None:
            """Write concise local request logs to stderr."""

            sys.stderr.write(f"screening-ui: {format_string % args}\n")

    return Handler


def build_service(
    root: Path, state_dir: Path, export_dir: Path, dry_run: bool, reset_dry_run: bool = False
) -> ScreeningService:
    """Validate upstream inputs and initialize one isolated application service."""

    contracts = load_contracts(root)
    namespace = "dry-run" if dry_run else "production"
    store_path = state_dir / f"{namespace}.sqlite3"
    if reset_dry_run:
        if not dry_run:
            raise ContractError("PRODUCTION_RESET_FORBIDDEN")
        DraftStore.remove_dry_run_state(store_path)
    store = DraftStore(store_path, namespace, _audit_hashes(dict(contracts.protected_hashes)))
    return ScreeningService(contracts, store, export_dir, dry_run)


def main() -> int:
    """Validate contracts, initialize local state, and start the loopback server."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repository_root())
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--export-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Use an isolated non-production draft namespace.")
    parser.add_argument("--reset-dry-run", action="store_true", help="Delete only dry-run drafts, then exit.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = args.root.resolve()
    state_dir = (args.state_dir or root / "var/publication_pilot1_screening").resolve()
    export_dir = (args.export_dir or state_dir / "exports").resolve()
    try:
        service = build_service(
            root,
            state_dir,
            export_dir,
            args.dry_run or args.reset_dry_run,
            reset_dry_run=args.reset_dry_run,
        )
        if args.reset_dry_run:
            service.store.close()
            print("Publication Pilot 1 dry-run state reinitialized; production drafts were untouched.")
            return 0
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ContractError("SCREENING_MVP_LOOPBACK_BIND_REQUIRED")
        server = HTTPServer((args.host, args.port), make_handler(service))
        print(f"Publication Pilot 1 screening interface ({'dry-run' if args.dry_run else 'production'})")
        print(f"Protected upstream contracts validated: {len(PROTECTED_HASHES)}")
        print(f"Local URL: http://{args.host}:{server.server_port}/")
        print(f"Private draft state: {service.store.path}")
        try:
            server.serve_forever()
        finally:
            service.store.close()
        return 0
    except (ContractError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
