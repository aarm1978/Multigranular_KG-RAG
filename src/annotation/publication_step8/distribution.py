"""Build checkpoint-bound, self-contained macOS Step 8 reviewer ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import INTERFACE_VERSION
from .contracts import INVENTORY, INVENTORY_HASH, PACKAGE_ROOT, PACKAGES, TARGET_INVENTORY, TARGET_INVENTORY_HASH, ReviewInputs, digest
from .service import activation_requirements


ROOT = Path(__file__).resolve().parents[3]
VERSION = "1.0.0"
ACCEPTED_RUNTIME_CHECKPOINT = "03ed4372c40d4d22ce0309fe5719f6260afc4692"
MANIFEST_PATH = ROOT / "data/curation/papers/m2/publication_step8_review_distribution_manifest_v1.0.0.json"
DEFAULT_OUTPUT = ROOT / "var/publication_step8_distribution"
ASSIGNMENTS = {
    "reviewer_1": {"role": "primary", "session": "step8-production-reviewer-1-v1"},
    "reviewer_2": {"role": "second", "session": "step8-production-reviewer-2-v1"},
}


class DistributionBuildError(ValueError):
    """Report an immutable distribution build or package boundary failure."""


def _canonical(value: Any) -> bytes:
    """Serialize canonical JSON bytes with one trailing newline."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) .encode("utf-8") + b"\n"


def _sha(path: Path) -> str:
    """Return the SHA-256 digest for an exact file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    """Run one bounded git read command from the repository root."""

    return subprocess.run(["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout.strip()


def _clean_checkpoint(root: Path) -> str:
    """Require a clean tracked checkout and return its exact distribution checkpoint."""

    if _git(root, "status", "--porcelain"):
        raise DistributionBuildError("DISTRIBUTION_BUILD_WORKTREE_NOT_CLEAN")
    return _git(root, "rev-parse", "HEAD")


def _python_source_files() -> list[Path]:
    """Return the minimal runtime source closure needed by the accepted UI."""

    step8 = ROOT / "src/annotation/publication_step8"
    return [path for path in sorted(step8.rglob("*")) if path.suffix in {".py", ".js", ".css", ".html"}] + [
        ROOT / "src/annotation/__init__.py",
        ROOT / "src/extraction/llm/publications/request_builder.py",
        ROOT / "src/extraction/llm/publications/authority_bundle.py",
    ]


def _source_files(role: str) -> list[Path]:
    """Return all and only role-authorized reviewer-visible source dependencies."""

    package = ROOT / PACKAGE_ROOT / PACKAGES[role][0]
    visible = json.loads(package.read_text(encoding="utf-8"))
    allowed = set(visible["primarySourceUnitIDs"]) | {context for item in visible["judgmentItems"]
                                                         for context in item["authorizedContextSourceUnitIDs"]}
    records = [json.loads(line) for line in (ROOT / INVENTORY).read_text(encoding="utf-8").splitlines()]
    source_files = {ROOT / row["sourceFile"] for row in records if row["sourceUnitID"] in allowed}
    if len(source_files) != 6 or any(not path.is_file() for path in source_files):
        raise DistributionBuildError("DISTRIBUTION_SOURCE_CLOSURE_INVALID")
    return [package, ROOT / INVENTORY, ROOT / TARGET_INVENTORY, *sorted(source_files)]


def _vendor_yaml(destination: Path) -> None:
    """Copy the pure Python PyYAML runtime into the bundle without native binaries."""

    if yaml.__version__ != "6.0":
        raise DistributionBuildError("DISTRIBUTION_PYYAML_VERSION_DRIFT")
    source = Path(yaml.__file__).resolve().parent
    target = destination / "vendor" / "yaml"
    for path in source.rglob("*.py"):
        relative = path.relative_to(source)
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out)


def _copy(source: Path, destination: Path) -> None:
    """Copy one repository-relative file into an unpacked package."""

    relative = source.relative_to(ROOT)
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _python_shell() -> str:
    """Return bounded macOS Python 3.10+ discovery with no installation side effects."""

    return '''select_python() {
  if [ -n "${STEP8_REVIEW_PYTHON:-}" ] && [ -x "$STEP8_REVIEW_PYTHON" ] && "$STEP8_REVIEW_PYTHON" -c 'import sys; assert sys.version_info >= (3,10)' >/dev/null 2>&1; then
    printf '%s\\n' "$STEP8_REVIEW_PYTHON"; return 0
  fi
  for candidate in python3 python /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      resolved="$(command -v "$candidate")"
      if "$resolved" -c 'import sys; assert sys.version_info >= (3,10)' >/dev/null 2>&1; then printf '%s\\n' "$resolved"; return 0; fi
    fi
  done
  echo "Python 3.10 or newer is required. PyYAML is included in this package; do not install or edit anything. Contact the researcher for a compatible Python installation." >&2
  return 2
}
PYTHON_EXECUTABLE="$(select_python)" || exit 2
export PYTHONPATH="$PWD/vendor:$PWD"
'''


def _script(action: str) -> str:
    """Return a double-clickable role-free command for one package-local action."""

    return f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
{_python_shell()}
"$PYTHON_EXECUTABLE" -m src.annotation.publication_step8.distribution_runtime verify --package-root . >/dev/null
"$PYTHON_EXECUTABLE" -m src.annotation.publication_step8.distribution_runtime {action} --package-root .
'''


def _readme(reviewer: str, role: str, session: str) -> str:
    """Return concise non-developer instructions without exposing internal role labels."""

    return f'''# Step 8 review package

You are **{reviewer}**. This package is private to you. It contains your local review session and must not be shared with the other reviewer.

## Start or resume

1. Unzip this folder somewhere private on your Mac. Keep the folder name and its contents unchanged.
2. Double-click **START_REVIEW.command**. If macOS asks, Control-click it, choose **Open**, and confirm once.
3. Your browser opens a local page. Leave the Terminal window open while reviewing. Your work saves automatically in this folder.
4. To resume later, double-click **START_REVIEW.command** again.

The review is private and runs only on your computer. It does not need a Git checkout, command-line arguments, an activation edit, or any repository files. The package includes PyYAML. It needs a local Python 3.10 or newer; it never installs Python or dependencies. If the launcher says Python is unavailable, send that message to the researcher.

## Backup and final return

- Double-click **EXPORT_BACKUP.command** at any time for a recovery copy. Its filename and contents say **NON_FINAL_BACKUP**. Do not return it as your completed result.
- When every assigned item is finished, double-click **EXPORT_FINAL.command**. It fails if any of the 182 decisions is incomplete.
- Return only `exports/STEP8_FINAL_EXPORT.json` to the researcher using the agreed private transfer method. Do not return the `state` folder, SQLite database, the activation file, or this whole package.

Your fixed session identifier is `{session}`. It exists only to let you safely resume this same local review.
'''


def _zip_directory(package: Path, output: Path) -> Path:
    """Create deterministic ZIP bytes with fixed timestamps and modes."""

    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in package.rglob("*") if item.is_file()):
            relative = path.relative_to(package.parent).as_posix()
            mode = 0o755 if path.suffix == ".command" else 0o600
            info = zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0))
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    if output.exists():
        if output.read_bytes() == temporary.read_bytes():
            temporary.unlink()
            return output
        temporary.unlink()
        raise DistributionBuildError("DISTRIBUTION_ZIP_OUTPUT_CONFLICT")
    os.replace(temporary, output)
    os.chmod(output, 0o600)
    return output


def build_package(reviewer: str, output: Path, *, checkpoint: str, root: Path = ROOT) -> tuple[Path, dict[str, Any]]:
    """Build one role-isolated self-contained reviewer ZIP without opening review state."""

    if root != ROOT:
        raise DistributionBuildError("DISTRIBUTION_ROOT_OVERRIDE_UNSUPPORTED")
    assignment = ASSIGNMENTS.get(reviewer)
    if assignment is None:
        raise DistributionBuildError("DISTRIBUTION_REVIEWER_UNKNOWN")
    role, session = assignment["role"], assignment["session"]
    inputs = ReviewInputs(role, root=root)
    activation = activation_requirements(inputs, session, reviewer)
    with tempfile.TemporaryDirectory() as temporary_name:
        package = Path(temporary_name) / f"step8_review_{reviewer}_v1"
        package.mkdir()
        for source in [*_python_source_files(), *_source_files(role)]:
            _copy(source, package)
        _vendor_yaml(package)
        activation_path = package / "activation" / "production_activation.json"
        activation_path.parent.mkdir(parents=True, exist_ok=True)
        activation_path.write_bytes(_canonical(activation))
        scripts = {"START_REVIEW.command": _script("start"), "EXPORT_BACKUP.command": _script("backup"),
                   "EXPORT_FINAL.command": _script("final")}
        for name, content in scripts.items():
            path = package / name
            path.write_text(content, encoding="utf-8")
            os.chmod(path, 0o755)
        (package / "README_REVIEWER.md").write_text(_readme(reviewer, role, session), encoding="utf-8")
        files = {path.relative_to(package).as_posix(): _sha(path) for path in sorted(package.rglob("*")) if path.is_file()}
        manifest = {"packageSchemaVersion": VERSION, "distributionBuildCheckpoint": checkpoint,
                    "acceptedRuntimeCheckpoint": ACCEPTED_RUNTIME_CHECKPOINT, "reviewerID": reviewer,
                    "reviewRole": role, "reviewSessionID": session, **activation,
                    "files": files, "stateDirectory": "state", "exportsDirectory": "exports",
                    "privateOpaqueLineageIncluded": False, "zipRoot": package.name}
        (package / "PACKAGE_MANIFEST.json").write_bytes(_canonical(manifest))
        output.parent.mkdir(parents=True, exist_ok=True)
        zip_path = _zip_directory(package, output)
    return zip_path, manifest


def materialize(output_dir: Path = DEFAULT_OUTPUT, *, checkpoint: str | None = None) -> dict[str, Any]:
    """Build both ZIPs and write a tracked, self-hashed distribution manifest."""

    checkpoint = checkpoint or _clean_checkpoint(ROOT)
    records = {}
    for reviewer in ASSIGNMENTS:
        path, package = build_package(reviewer, output_dir / f"step8_review_{reviewer}_v1.zip", checkpoint=checkpoint)
        records[reviewer] = {"reviewerID": reviewer, "reviewRole": package["reviewRole"],
                             "reviewSessionID": package["reviewSessionID"], "zipPath": str(path.relative_to(ROOT)),
                             "zipSha256": _sha(path), "packageManifest": {key: package[key] for key in (
                                 "inputPackageSha256", "runtimeSha256", "sourceInventorySha256", "interfaceVersion", "files")}}
    body = {"artifactType": "publication_step8_reviewer_distribution_manifest", "artifactVersion": VERSION,
            "distributionBuildCheckpoint": checkpoint, "acceptedRuntimeCheckpoint": ACCEPTED_RUNTIME_CHECKPOINT,
            "interfaceVersion": INTERFACE_VERSION, "reviewerBundles": records,
            "boundary": {"productionJudgmentsCreated": False, "reconciliationCreated": False,
                         "privateOpaqueLineageIncluded": False, "providerModelCallsOccurred": False}}
    body["artifactSha256"] = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    data = _canonical(body)
    if MANIFEST_PATH.exists() and MANIFEST_PATH.read_bytes() != data:
        raise DistributionBuildError("DISTRIBUTION_MANIFEST_OUTPUT_CONFLICT")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_bytes(data)
    return body


def main() -> int:
    """Build the two reviewer ZIPs from a clean checkpoint-bound checkout."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(materialize(args.output_dir), indent=2, sort_keys=True))
        return 0
    except (DistributionBuildError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
