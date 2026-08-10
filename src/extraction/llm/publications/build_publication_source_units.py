"""Build the deterministic Publication Pilot 1 canonical source-unit inventory."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.source_units import (  # noqa: E402
    PILOT_ARTIFACT_IDS,
    SourceUnitError,
    build_inventory,
    serialize_inventory,
    serialize_manifest,
    sha256_bytes,
    write_outputs_atomically,
)


DEFAULT_CORPUS = Path("data/interim/papers/ciroh_publication_corpus.json")
DEFAULT_INVENTORY = Path("data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl")
DEFAULT_MANIFEST = Path("data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json")
DEFAULT_PHASE_B = Path("data/interim/papers/publication_nodes_edges.json")


def resolve_path(path: Path) -> Path:
    """Resolve a CLI path against the repository root when it is relative."""

    return path if path.is_absolute() else PROJECT_ROOT / path


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the deterministic Publication source-unit CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-a-corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--artifact-ids", nargs="+", default=list(PILOT_ARTIFACT_IDS))
    parser.add_argument("--output-inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--phase-b-artifact", type=Path, default=DEFAULT_PHASE_B)
    parser.add_argument("--generation-timestamp", help="Recorded ISO-8601 run timestamp; inject this for byte-stable manifests.")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Build and validate in memory, then atomically write both outputs if requested."""

    args = build_argument_parser().parse_args(argv)
    timestamp = args.generation_timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        units, manifest = build_inventory(
            PROJECT_ROOT,
            resolve_path(args.phase_a_corpus),
            args.artifact_ids,
            timestamp,
            resolve_path(args.phase_b_artifact),
            verify_frozen_authorities=True,
        )
        inventory_bytes = serialize_inventory(units)
        manifest_bytes = serialize_manifest(manifest)
        json.loads(manifest_bytes)
        for line in inventory_bytes.splitlines():
            json.loads(line)
        if not args.validate_only:
            write_outputs_atomically(((resolve_path(args.output_inventory), inventory_bytes), (resolve_path(args.output_manifest), manifest_bytes)))
    except (OSError, json.JSONDecodeError, SourceUnitError, KeyError, TypeError) as exc:
        print(f"publication source-unit build failed: {exc}", file=sys.stderr)
        return 1
    print(f"validation status: valid")
    print(f"artifacts: {manifest['artifactCount']}")
    print(f"source units: {manifest['sourceUnitCount']}")
    print(f"inventory SHA-256: {manifest['sourceUnitInventoryHash']}")
    print(f"mode: {'validate-only' if args.validate_only else 'materialized'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
