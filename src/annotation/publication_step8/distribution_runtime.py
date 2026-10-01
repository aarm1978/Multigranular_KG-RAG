"""Run and export one verified self-contained Step 8 reviewer distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import webbrowser
from http.server import HTTPServer
from pathlib import Path
from typing import Any

from .app import make_handler
from .contracts import ReviewError, ReviewInputs, canonical_json
from .service import ReviewService, activation_requirements


class DistributionError(ValueError):
    """Report a package, identity, or export boundary violation."""


def _digest(path: Path) -> str:
    """Return the SHA-256 digest of one package file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(package_root: Path) -> dict[str, Any]:
    """Read one package manifest without accepting a malformed payload."""

    try:
        value = json.loads((package_root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DistributionError("PACKAGE_MANIFEST_INVALID") from exc
    if not isinstance(value, dict) or value.get("packageSchemaVersion") != "1.0.0":
        raise DistributionError("PACKAGE_MANIFEST_INVALID")
    return value


def verify_package(package_root: Path) -> dict[str, Any]:
    """Verify immutable package content and exact role/session activation bindings."""

    package_root = package_root.resolve()
    manifest = _load_manifest(package_root)
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise DistributionError("PACKAGE_FILE_MANIFEST_INVALID")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise DistributionError("PACKAGE_FILE_MANIFEST_INVALID")
        path = (package_root / relative).resolve()
        if package_root not in path.parents or not path.is_file() or _digest(path) != expected:
            raise DistributionError(f"PACKAGE_FILE_HASH_MISMATCH:{relative}")
    if any("opaque_lineage" in path or "internal" in path.lower() for path in files):
        raise DistributionError("PACKAGE_PRIVATE_PROVENANCE_PRESENT")
    role, session, reviewer = (manifest.get(key) for key in ("reviewRole", "reviewSessionID", "reviewerID"))
    if role not in {"primary", "second"} or not all(isinstance(value, str) and value for value in (session, reviewer)):
        raise DistributionError("PACKAGE_IDENTITY_INVALID")
    activation_path = package_root / "activation" / "production_activation.json"
    try:
        activation = json.loads(activation_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DistributionError("PACKAGE_ACTIVATION_INVALID") from exc
    inputs = ReviewInputs(role, root=package_root)
    expected = activation_requirements(inputs, session, reviewer)
    if activation != expected:
        raise DistributionError("PACKAGE_ACTIVATION_BINDING_DRIFT")
    for key in ("reviewRole", "reviewSessionID", "reviewerID", "inputPackageSha256", "runtimeSha256", "sourceInventorySha256", "interfaceVersion"):
        if manifest.get(key) != expected.get(key):
            raise DistributionError(f"PACKAGE_MANIFEST_BINDING_DRIFT:{key}")
    return manifest


def _service(package_root: Path) -> tuple[ReviewService, dict[str, Any]]:
    """Open only the bound production service in package-local state."""

    manifest = verify_package(package_root)
    activation = package_root / "activation" / "production_activation.json"
    service = ReviewService(ReviewInputs(manifest["reviewRole"], root=package_root), package_root / "state",
                            manifest["reviewSessionID"], manifest["reviewerID"], "production", activation)
    return service, manifest


def start(package_root: Path, port: int = 8788) -> None:
    """Start the role-isolated production review server on loopback and open a browser."""

    service, _ = _service(package_root)
    try:
        server = HTTPServer(("127.0.0.1", port), make_handler(service))
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Step 8 review is open at {url}")
        webbrowser.open(url)
        server.serve_forever()
    finally:
        try:
            server.server_close()  # type: ignore[has-type]
        except UnboundLocalError:
            pass
        service.close()


def _write_immutable(path: Path, data: bytes) -> Path:
    """Write one deterministic local export without overwriting different bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return path
        raise DistributionError("EXPORT_OUTPUT_EXISTS_CONFLICT")
    path.write_bytes(data)
    os.chmod(path, 0o600)
    return path


def export(package_root: Path, *, final: bool) -> Path:
    """Create a bound backup or require complete state for the final reviewer export."""

    service, manifest = _service(package_root)
    try:
        state = service.state()
        if final and not state["complete"]:
            raise DistributionError("FINAL_EXPORT_REVIEW_INCOMPLETE")
        review_export = service.export()
        if final:
            filename, data = "STEP8_FINAL_EXPORT.json", review_export
        else:
            filename = "STEP8_NON_FINAL_BACKUP.json"
            data = canonical_json({"exportKind": "non_final_backup", "complete": state["complete"],
                                   "reviewExport": json.loads(review_export)}) + b"\n"
        return _write_immutable(package_root / "exports" / filename, data)
    finally:
        service.close()


def main() -> int:
    """Run a package-local reviewer action without exposing arguments to reviewers."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "start", "backup", "final"))
    parser.add_argument("--package-root", type=Path, default=Path("."))
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    try:
        if args.action == "verify":
            print(json.dumps(verify_package(args.package_root), indent=2, sort_keys=True))
        elif args.action == "start":
            start(args.package_root, args.port)
        else:
            print(export(args.package_root, final=args.action == "final"))
        return 0
    except (DistributionError, ReviewError, OSError, ValueError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
