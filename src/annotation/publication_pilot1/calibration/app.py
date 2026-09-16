"""Run the local Publication Pilot 1 Annotation / Calibration interface."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..contracts import sha256_file
from .contracts import (
    ANNOTATION_MVP_BASE_CHECKPOINT,
    AnnotationContractError,
    canonical_json_hash,
    HUMAN_CORE_FREEZE_RELATIVE,
    HUMAN_CORE_PRIMARY_ANNOTATOR_ID,
    HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE,
    load_annotation_contracts,
    verify_production_activation,
)
from . import (
    HUMAN_CORE_SUPPLEMENTAL_ANNOTATOR_ID,
    HUMAN_CORE_SUPPLEMENTAL_SESSION_ID,
    human_core_session_namespace,
)
from .service import AnnotationService
from .store import AnnotationStore


def repository_root() -> Path:
    """Return the repository root from this module's stable location."""

    return Path(__file__).resolve().parents[4]


def _safe_component(value: str) -> str:
    """Convert an identity to a safe filename without changing stored identity."""

    safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in value)
    if not safe:
        raise AnnotationContractError("ANNOTATION_ID_FILENAME_COMPONENT_INVALID")
    return safe


def make_handler(service: AnnotationService) -> type[BaseHTTPRequestHandler]:
    """Create a bounded local HTTP handler for one independent session."""

    static_dir = Path(__file__).with_name("static")

    class Handler(BaseHTTPRequestHandler):
        """Serve the annotation UI and JSON API."""

        def _json(self, status: int, payload: object) -> None:
            """Send a no-store UTF-8 JSON response."""

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body)

        def _body(self) -> dict[str, object]:
            """Read one bounded JSON object."""

            length = int(self.headers.get("Content-Length", "0"))
            if length > 3_000_000:
                raise AnnotationContractError("ANNOTATION_REQUEST_BODY_TOO_LARGE")
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict):
                raise AnnotationContractError("ANNOTATION_JSON_OBJECT_REQUIRED")
            return value

        def do_GET(self) -> None:  # noqa: N802
            """Serve bootstrap, exact units, handbook, or static assets."""

            try:
                parsed = urlparse(self.path)
                if parsed.path == "/api/bootstrap":
                    self._json(HTTPStatus.OK, service.bootstrap()); return
                if parsed.path == "/handbook":
                    handbook = "docs/publication_human_core_expert_annotation_guide.md" if service.contracts.mode in {"human-core", "human-core-supplemental"} else "docs/publication_pilot1_annotation_calibration_handbook.md"
                    body = (service.contracts.root / handbook).read_bytes()
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers(); self.wfile.write(body); return
                if parsed.path.startswith("/api/units/"):
                    self._json(HTTPStatus.OK, service.unit(unquote(parsed.path.removeprefix("/api/units/")))); return
                asset = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                path = (static_dir / asset).resolve()
                if static_dir.resolve() not in path.parents or not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND); return
                body = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers(); self.wfile.write(body)
            except (AnnotationContractError, ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            """Handle save, timing, submission, reopen, export, and safe reset."""

            try:
                body = self._body()
                if self.path == "/api/save":
                    result = service.save(str(body.get("sourceUnitID", "")), body.get("annotation", {}))
                elif self.path == "/api/timing":
                    result = service.timing(str(body.get("sourceUnitID", "")), str(body.get("eventType", "")))
                elif self.path == "/api/context":
                    result = service.expose_context(
                        str(body.get("sourceUnitID", "")), str(body.get("contextSourceUnitID", "")),
                        context_selection_reason=str(body.get("contextSelectionReason", "")),
                        operational_target_id=(
                            str(body["operationalTargetID"]) if body.get("operationalTargetID") else None
                        ),
                        unresolved_assertion_id=(
                            str(body["unresolvedAssertionID"]) if body.get("unresolvedAssertionID") else None
                        ),
                    )
                elif self.path == "/api/submit":
                    result = service.submit(str(body.get("sourceUnitID", "")), body.get("annotation", {}))
                elif self.path == "/api/reopen":
                    result = service.reopen(str(body.get("sourceUnitID", "")), str(body.get("reason", "")))
                elif self.path == "/api/export":
                    result = {"path": str(service.export())}
                elif self.path == "/api/reset-synthetic":
                    service.store.reset(); result = {"reset": True}
                else:
                    self.send_error(HTTPStatus.NOT_FOUND); return
                self._json(HTTPStatus.OK, result)
            except (AnnotationContractError, ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

        def log_message(self, format_string: str, *args: object) -> None:
            """Keep local server output concise."""

            sys.stderr.write("annotation-calibration: " + format_string % args + "\n")

    return Handler


def build_service(args: argparse.Namespace) -> AnnotationService:
    """Validate contracts and activation before creating mutable state."""

    root = repository_root()
    if args.mode in {"human-core", "human-core-supplemental"}:
        expected_annotator = HUMAN_CORE_PRIMARY_ANNOTATOR_ID if args.mode == "human-core" else HUMAN_CORE_SUPPLEMENTAL_ANNOTATOR_ID
        expected_session = None if args.mode == "human-core" else HUMAN_CORE_SUPPLEMENTAL_SESSION_ID
        if args.annotator_id != expected_annotator:
            raise AnnotationContractError("HUMAN_CORE_PRIMARY_IDENTITY_MISMATCH" if args.mode == "human-core" else "HUMAN_CORE_SUPPLEMENTAL_IDENTITY_MISMATCH")
        if expected_session is not None and args.annotation_session_id != expected_session:
            raise AnnotationContractError("HUMAN_CORE_SUPPLEMENTAL_IDENTITY_MISMATCH")
        try:
            human_core_session_namespace(args.annotation_session_id)
        except ValueError as exc:
            raise AnnotationContractError("HUMAN_CORE_SESSION_ID_NOT_AUTHORIZED") from exc
    activation = None if args.activation_file is None else Path(args.activation_file).resolve()
    contracts = load_annotation_contracts(root, mode=args.mode, activation_path=activation)
    activation_payload = None
    if args.mode == "calibration":
        activation_payload = verify_production_activation(
            activation, root, annotator_id=args.annotator_id,
            annotation_session_id=args.annotation_session_id,
        )
    namespace = "synthetic" if args.mode == "synthetic" else (human_core_session_namespace(args.annotation_session_id) if args.mode in {"human-core", "human-core-supplemental"} else "calibration/production")
    runtime = root / "var/publication_pilot1_annotation" / namespace
    state_path = runtime / "sessions" / f"{_safe_component(args.annotation_session_id)}.sqlite3"
    bindings = {
        "sourceUnitInventoryHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"],
        "sampleFreezeHash": sha256_file(root / HUMAN_CORE_FREEZE_RELATIVE) if args.mode in {"human-core", "human-core-supplemental"} else contracts.hashes["data/curation/papers/pilot1/publication_pilot1_calibration_manifest.json"],
        "routingHash": contracts.hashes["data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"],
        "routingSchemaHash": contracts.hashes["schemas/publication_pilot1_unit_routing.schema.json"],
        "targetInventoryHash": contracts.hashes["src/extraction/llm/publications/publication_target_inventory.yaml"],
        "annotationHandbookHash": sha256_file(root / ("docs/publication_human_core_expert_annotation_guide.md" if args.mode == "human-core" else "docs/publication_pilot1_annotation_calibration_handbook.md")),
        "annotationSchemaHash": sha256_file(root / "schemas/publication_pilot1_annotation_record.schema.json"),
        "canonicalDocumentHashesHash": canonical_json_hash(dict(contracts.canonical_document_hashes)),
        "phaseBArtifactHash": contracts.hashes["data/interim/papers/publication_nodes_edges.json"],
        "annotationMVPBaseCheckpoint": ANNOTATION_MVP_BASE_CHECKPOINT,
    }
    if args.mode in {"human-core", "human-core-supplemental"}:
        package_relative = HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE if args.mode == "human-core-supplemental" else "data/curation/papers/m2/human_core_gold/publication_human_core_primary_annotation_package_v1.1.json"
        package = json.loads((root / package_relative).read_text(encoding="utf-8"))
        guide = package["authorities"]["guide"] if args.mode == "human-core-supplemental" else package["guide"]
        bindings["guideAuthorityVersion"] = str(guide["version"])
        bindings["guideAuthorityHash"] = str(guide["sha256"])
        if args.mode == "human-core-supplemental":
            bindings["supplementalPackageHash"] = sha256_file(root / HUMAN_CORE_SUPPLEMENTAL_PACKAGE_RELATIVE)
            bindings["primaryBaselineExportHash"] = str(package["authorities"]["primaryBaselineExport"]["sha256"])
    if activation_payload is not None:
        bindings["activationHash"] = canonical_json_hash(activation_payload)
        bindings["packageBuildCheckpoint"] = str(activation_payload["packageBuildCheckpoint"])
    store = AnnotationStore(
        state_path, mode=args.mode, annotation_session_id=args.annotation_session_id,
        annotator_id=args.annotator_id, bindings=bindings,
    )
    return AnnotationService(contracts, store, runtime / "exports")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse explicit identity and guarded mode options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("synthetic", "calibration", "human-core", "human-core-supplemental"), default="synthetic")
    parser.add_argument("--annotation-session-id", required=True)
    parser.add_argument("--annotator-id", required=True)
    parser.add_argument("--activation-file", help="Required exact local JSON binding for calibration mode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Start the local single-session application."""

    args = parse_args(argv)
    try:
        service = build_service(args)
    except (AnnotationContractError, ValueError) as exc:
        print(str(exc), file=sys.stderr); return 2
    server = HTTPServer((args.host, args.port), make_handler(service))
    print(f"Annotation / Calibration Mode ({args.mode}) at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close(); service.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
