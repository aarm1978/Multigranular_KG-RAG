"""Build a self-contained macOS ZIP for the bounded Step 8 joint reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from src.extraction.llm.publications.request_builder import PROJECT_ROOT
from src.extraction.llm.publications import step8_reconciliation_package as package_builder


ROOT = PROJECT_ROOT
PACKAGE = package_builder.OUTPUT
VERSION = "1.0.1"
DEFAULT_OUTPUT = ROOT / "var/publication_step8_reconciliation_distribution/v1.0.1"
MANIFEST = ROOT / "data/curation/papers/m2/publication_step8_reconciliation/publication_step8_reconciliation_distribution_manifest_v1.0.1.json"
RUNTIME_FILES = ("reconciliation.py", "reconciliation_app.py")
STATIC = Path(__file__).with_name("reconciliation_static")


class ReconciliationDistributionError(ValueError):
    """Report a bounded distribution build or immutable-output failure."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _copy(source: Path, destination: Path) -> None:
    relative = source.relative_to(ROOT) if source.is_relative_to(ROOT) else Path("runtime") / source.name
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _python_shell() -> str:
    return '''select_python() {
  for candidate in python3 python /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if command -v "$candidate" >/dev/null 2>&1; then resolved="$(command -v "$candidate")"; if "$resolved" -c 'import sys; assert sys.version_info >= (3,10)' >/dev/null 2>&1; then printf '%s\\n' "$resolved"; return 0; fi; fi
  done
  echo "Python 3.10 or newer is required. Contact the researcher for a compatible Python installation." >&2; return 2
}
PYTHON_EXECUTABLE="$(select_python)" || exit 2
'''


def _script(action: str) -> str:
    command = {"start": 'start --package data/curation/papers/m2/publication_step8_reconciliation/publication_step8_reconciliation_package_v1.0.0.json --state state/reconciliation-state.json',
               "final": 'final --package data/curation/papers/m2/publication_step8_reconciliation/publication_step8_reconciliation_package_v1.0.0.json --state state/reconciliation-state.json --export exports/STEP8_FINAL_RECONCILIATION.json'}[action]
    return f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
{_python_shell()}
"$PYTHON_EXECUTABLE" runtime/reconciliation_app.py verify --package data/curation/papers/m2/publication_step8_reconciliation/publication_step8_reconciliation_package_v1.0.0.json --state state/reconciliation-state.json >/dev/null
"$PYTHON_EXECUTABLE" runtime/reconciliation_app.py {command}
'''


def _readme() -> str:
    return '''# Step 8 joint reconciliation

1. Unzip this private folder on the meeting Mac and keep its contents together.
2. Double-click `START_RECONCILIATION.command`; approve macOS once if needed. A local browser page opens.
3. Resolve each of the 11 listed disagreements using only the assertion, cited evidence, authorized primary/context text, target criterion, and boundary shown. Do not edit or repair assertions and do not use external search.
4. Choices save locally. When all 11 have a final status, stop the local server with Control-C, then double-click `EXPORT_FINAL.command`.
5. Return only `exports/STEP8_FINAL_RECONCILIATION.json`. Do not return this whole package or the `state` directory.

The final exporter fails closed until all 11 decisions are present. This package contains no positive reference and does not change either initial review or the pre-reconciliation agreement.
'''


def _zip(folder: Path, output: Path) -> None:
    temporary = output.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(value for value in folder.rglob("*") if value.is_file()):
            info = zipfile.ZipInfo(path.relative_to(folder.parent).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o100755 if path.suffix == ".command" else 0o100600) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    if output.exists() and output.read_bytes() != temporary.read_bytes():
        temporary.unlink(); raise ReconciliationDistributionError("RECONCILIATION_ZIP_OUTPUT_CONFLICT")
    os.replace(temporary, output)


def build(output: Path, checkpoint: str) -> tuple[Path, dict[str, Any]]:
    """Create one package-local reconciliation ZIP without creating decisions."""

    package_builder.materialize()
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name) / "step8_joint_reconciliation_v1"; folder.mkdir()
        _copy(ROOT / PACKAGE, folder)
        for filename in RUNTIME_FILES:
            target = folder / "runtime" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(__file__).with_name(filename), target)
        for source in STATIC.iterdir():
            target = folder / "runtime" / "reconciliation_static" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for filename, action in (("START_RECONCILIATION.command", "start"), ("EXPORT_FINAL.command", "final")):
            path=folder/filename; path.write_text(_script(action)); os.chmod(path, 0o755)
        (folder / "README_RECONCILIATION.md").write_text(_readme())
        files={path.relative_to(folder).as_posix():_sha(path) for path in sorted(folder.rglob("*")) if path.is_file()}
        manifest={"packageSchemaVersion":VERSION,"buildCheckpoint":checkpoint,"reconciliationPackageSha256":_sha(ROOT/PACKAGE),"files":files,"stateDirectory":"state","exportsDirectory":"exports"}
        (folder/"PACKAGE_MANIFEST.json").write_bytes(_canonical(manifest))
        output.parent.mkdir(parents=True,exist_ok=True); _zip(folder,output)
    return output,manifest


def materialize(output_dir: Path = DEFAULT_OUTPUT, checkpoint: str = "UNBOUND") -> dict[str, Any]:
    """Build the ZIP and its tracked self-hashed distribution manifest."""

    zip_path, package_manifest = build(output_dir / "step8_joint_reconciliation_v1.zip", checkpoint)
    body = {"artifactType": "publication_step8_reconciliation_distribution_manifest", "artifactVersion": VERSION,
            "buildCheckpoint": checkpoint, "reconciliationPackage": {"path": PACKAGE.as_posix(), "sha256": _sha(ROOT / PACKAGE)},
            "zipPath": str(zip_path.relative_to(ROOT)), "zipSha256": _sha(zip_path),
            "packageManifest": {key: package_manifest[key] for key in ("packageSchemaVersion", "reconciliationPackageSha256", "files")},
            "boundary": {"reconciliationDecisionsCreated": False, "positiveReferenceAssembled": False, "providerModelCallsOccurred": False}}
    body["artifactSha256"] = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    data = _canonical(body)
    if MANIFEST.exists() and MANIFEST.read_bytes() != data:
        raise ReconciliationDistributionError("RECONCILIATION_MANIFEST_OUTPUT_CONFLICT")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_bytes(data)
    return body
