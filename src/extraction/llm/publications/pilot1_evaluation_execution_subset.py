"""Freeze the Pilot 1 execution scope from the corrected production manifest.

This module selects no new units and never constructs or dispatches a provider
request.  It projects the already-frozen Human Core N=5 and Step 5 N=6 source
unit identities onto their exact records in the corrected 262-request manifest.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


ARTIFACT_VERSION = "0.1.0"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data/curation/papers/m2/publication_v015_corrected_production"
OUTPUT_NAME = "publication_pilot1_evaluation_execution_subset_v0.1.0.json"
MANIFEST_PATH = OUTPUT_DIRECTORY / "publication_v015_corrected_production_run_manifest_v0.1.0.json"
HUMAN_CORE_N5_PATH = PROJECT_ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json"
STEP5_N6_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.2.json"
IDENTITY_FIELDS = (
    "requestID",
    "requestInputSha256",
    "providerRequestBodySha256",
    "modelAuthorableSchemaSha256",
    "productionTargetIDs",
    "contextSourceUnitIDs",
)


class Pilot1ExecutionSubsetError(ValueError):
    """Report a frozen-authority or manifest identity binding failure."""


def _load(path: Path) -> dict[str, Any]:
    """Load one JSON-object artifact."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Pilot1ExecutionSubsetError(f"EXPECTED_JSON_OBJECT:{path}")
    return value


def _self_hash(payload: Mapping[str, Any], field: str) -> str:
    """Recompute a canonical self-hash after excluding its assigned field."""

    value = dict(payload)
    value.pop(field, None)
    return sha256_bytes(canonical_json(value))


def _file_hash(path: Path) -> str:
    """Return the byte hash for an authority without a self-hash field."""

    return sha256_bytes(path.read_bytes())


def _source_ids() -> tuple[list[str], list[str]]:
    """Read the preserved N=5 and N=6 unit identities in their frozen order."""

    human_core = _load(HUMAN_CORE_N5_PATH)
    if human_core.get("packageIdentity") != "publication-human-core-gold-n5-primary-v1":
        raise Pilot1ExecutionSubsetError("HUMAN_CORE_N5_AUTHORITY_DRIFT")
    n5_ids = [str(row["sourceUnitID"]) for row in human_core.get("selectedUnits", [])]
    step5 = _load(STEP5_N6_PATH)
    if step5.get("artifactVersion") != "0.1.2" or step5.get("providerModelCalls") != 0:
        raise Pilot1ExecutionSubsetError("STEP5_N6_AUTHORITY_DRIFT")
    n6_ids = [str(row["primarySourceUnitID"]) for row in step5.get("envelopes", [])]
    if len(n5_ids) != 5 or len(n6_ids) != 6 or len(set(n5_ids + n6_ids)) != 11:
        raise Pilot1ExecutionSubsetError("PILOT1_EXECUTION_SCOPE_COUNT_DRIFT")
    return n5_ids, n6_ids


def derive_execution_subset() -> dict[str, Any]:
    """Project the 11 frozen evaluation requests from the corrected manifest."""

    manifest = _load(MANIFEST_PATH)
    if manifest.get("manifestVersion") != "0.1.0" or manifest.get("providerModelCalls") != 0:
        raise Pilot1ExecutionSubsetError("CORRECTED_MANIFEST_AUTHORITY_DRIFT")
    if manifest.get("manifestSha256") != _self_hash(manifest, "manifestSha256"):
        raise Pilot1ExecutionSubsetError("CORRECTED_MANIFEST_HASH_DRIFT")
    records = manifest.get("requests", [])
    by_unit = {str(row["primarySourceUnitID"]): row for row in records}
    if len(by_unit) != len(records) or manifest.get("populationCount") != len(records):
        raise Pilot1ExecutionSubsetError("CORRECTED_MANIFEST_REQUEST_IDENTITY_DRIFT")

    n5_ids, n6_ids = _source_ids()
    subset: list[dict[str, Any]] = []
    for cohort, source_unit_ids in (("human_core_n5", n5_ids), ("step5_n6", n6_ids)):
        for source_unit_id in source_unit_ids:
            manifest_record = by_unit.get(source_unit_id)
            if manifest_record is None:
                raise Pilot1ExecutionSubsetError(f"PILOT1_UNIT_MISSING_FROM_MANIFEST:{source_unit_id}")
            record = {
                "executionCohort": cohort,
                "primarySourceUnitID": source_unit_id,
                **{field: manifest_record[field] for field in IDENTITY_FIELDS},
            }
            if any(record[field] != manifest_record[field] for field in IDENTITY_FIELDS):
                raise Pilot1ExecutionSubsetError(f"PILOT1_MANIFEST_IDENTITY_MISMATCH:{source_unit_id}")
            subset.append(record)

    artifact = {
        "artifactType": "publication_pilot1_evaluation_execution_subset",
        "artifactVersion": ARTIFACT_VERSION,
        "status": "frozen_execution_scope_no_provider_execution",
        "providerModelCalls": 0,
        "scopeStatement": "Exactly the frozen Human Core N=5 plus Step 5 N=6 primary source units; no new selection.",
        "correctedProductionManifest": {
            "path": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
            "manifestSha256": manifest["manifestSha256"],
            "populationCount": manifest["populationCount"],
        },
        "selectionAuthorities": {
            "humanCoreN5": {
                "path": str(HUMAN_CORE_N5_PATH.relative_to(PROJECT_ROOT)),
                "fileSha256": _file_hash(HUMAN_CORE_N5_PATH),
                "sourceUnitIDs": n5_ids,
            },
            "step5N6": {
                "path": str(STEP5_N6_PATH.relative_to(PROJECT_ROOT)),
                "artifactSha256": _load(STEP5_N6_PATH)["artifactSha256"],
                "sourceUnitIDs": n6_ids,
            },
        },
        "subsetRequestCount": len(subset),
        "requests": subset,
        "remainingCorrectedProductionRequestsNotRequiredForCurrentEvaluation": manifest["populationCount"] - len(subset),
        "fullPublicationKGPopulationBoundary": "A separate full-corpus production over the 228-artifact corpus remains required.",
    }
    artifact["artifactSha256"] = sha256_bytes(canonical_json(artifact))
    return artifact


def materialize(output_path: Path = OUTPUT_DIRECTORY / OUTPUT_NAME) -> Path:
    """Write the new subset artifact without changing its source authorities."""

    payload = canonical_json(derive_execution_subset()) + b"\n"
    if output_path.exists() and output_path.read_bytes() != payload:
        raise Pilot1ExecutionSubsetError(f"PILOT1_EXECUTION_SUBSET_CONFLICT:{output_path.name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return output_path


def main(argv: Sequence[str] | None = None) -> int:
    """Materialize only the offline execution-scope artifact."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_DIRECTORY / OUTPUT_NAME)
    args = parser.parse_args(argv)
    print(materialize(args.output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
