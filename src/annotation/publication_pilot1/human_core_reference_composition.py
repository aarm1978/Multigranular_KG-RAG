"""Build a read-only, fail-closed Human Core v0.1.5 reference projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import yaml

from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes


ROOT = Path(__file__).resolve().parents[3]
PRIMARY = ROOT / "var/publication_pilot1_annotation/human-core/primary-researcher/exports/HUMAN_CORE_N5_PRIMARY_V1.annotation.json"
SUPPLEMENTAL = ROOT / "var/publication_pilot1_annotation/human-core/supplemental-researcher/exports/HUMAN_CORE_N5_SUPPLEMENTAL_V015.annotation.json"
PRIMARY_SHA256 = "9d71ae66c3218c4b8be21a3ea10b4015cb5502fce5eaf75f6bb0ac9922bc4e74"
SUPPLEMENTAL_SHA256 = "8d637084d3f14cae958b9a9bbe3acb8c74ca741a2c43a990ec939699266707a2"
SUPPLEMENTAL_PACKAGE = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_supplemental_annotation_package_v0.1.5.json"
DEFAULT_OUTPUT = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_v0.1.5_composite_reference_projection.json"


class HumanCoreCompositionError(ValueError):
    """Report a violated immutable-reference composition invariant."""


def _load(path: Path, expected: str) -> dict[str, Any]:
    """Read one immutable export after exact byte verification."""

    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise HumanCoreCompositionError(f"immutable export hash mismatch: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("annotations"), list):
        raise HumanCoreCompositionError(f"invalid immutable export: {path.name}")
    return value


def compose_human_core_reference() -> dict[str, Any]:
    """Return a derived manifest/projection without modifying either source export."""

    primary, supplemental = _load(PRIMARY, PRIMARY_SHA256), _load(SUPPLEMENTAL, SUPPLEMENTAL_SHA256)
    primary_by_unit = {str(row.get("sourceUnitID")): row for row in primary["annotations"]}
    if len(primary_by_unit) != len(primary["annotations"]):
        raise HumanCoreCompositionError("primary source-unit identities are not unique")
    package = json.loads(SUPPLEMENTAL_PACKAGE.read_text(encoding="utf-8"))
    primary_profile = yaml.safe_load((ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml").read_text(encoding="utf-8"))
    primary_treatments = {row["operational_id"]: {"pilot_treatment": row["pilot_treatment"], "evaluation_mode": row["evaluation_mode"], "partition": "primary_v014"} for group in ("node_targets", "relation_targets") for row in primary_profile[group]}
    authorized = {row["operational_id"] for group in ("node_targets", "relation_targets") for row in package["targets"][group]}
    treatments = {row["operational_id"]: {"pilot_treatment": row["pilot_treatment"], "evaluation_mode": row["evaluation_mode"], "partition": "supplemental_v015"} for group in ("node_targets", "relation_targets") for row in package["targets"][group]}
    aliases: dict[str, str] = {}
    for row in supplemental["annotations"]:
        unit = str(row.get("sourceUnitID"))
        if unit not in primary_by_unit:
            raise HumanCoreCompositionError("supplemental unit lacks immutable primary counterpart")
        annotation = row.get("annotation", {})
        observed = {str(item.get("operationalTargetID", item.get("operationalRelationID"))) for group in ("nodes", "relations") for item in annotation.get(group, [])}
        if not observed <= authorized:
            raise HumanCoreCompositionError("supplemental annotation contains an unauthorized delta target")
        nodes = primary_by_unit[unit].get("annotation", {}).get("nodes", [])
        ids = {str(node.get("candidateID")) for node in nodes if isinstance(node, dict)}
        for edge in row.get("annotation", {}).get("relations", []):
            for side in ("source", "target"):
                ref = edge.get(side, {}) if isinstance(edge, dict) else {}
                value = str(ref.get("referenceID", ""))
                prefix = f"baseline:{unit}:"
                if value.startswith("baseline:"):
                    if not value.startswith(prefix) or value.removeprefix(prefix) not in ids:
                        raise HumanCoreCompositionError("baseline alias is not a same-unit immutable primary node")
                    primary_id = value.removeprefix(prefix)
                    if value in aliases and aliases[value] != primary_id:
                        raise HumanCoreCompositionError("baseline alias has conflicting primary mapping")
                    aliases[value] = primary_id
    result: dict[str, Any] = {
        "projectionVersion": "human-core-reference-composition/0.1.0",
        "readOnly": True,
        "destructiveMergeAuthorized": False,
        "partitions": [
            {"partition": "primary_v014", "path": str(PRIMARY.relative_to(ROOT)), "sha256": PRIMARY_SHA256, "annotationSessionID": primary.get("annotationSessionID")},
            {"partition": "supplemental_v015", "path": str(SUPPLEMENTAL.relative_to(ROOT)), "sha256": SUPPLEMENTAL_SHA256, "annotationSessionID": supplemental.get("annotationSessionID")},
        ],
        "targetTreatmentPreserved": True,
        "baselineAliases": [{"alias": alias, "primaryLocalID": primary_id} for alias, primary_id in sorted(aliases.items())],
        "authorizedSupplementalDeltaTargetIDs": sorted(authorized),
        "supplementalTargetTreatment": treatments,
        "primaryTargetTreatment": primary_treatments,
        "partitionAnnotationCounts": {"primary_v014": len(primary["annotations"]), "supplemental_v015": len(supplemental["annotations"])},
    }
    result["projectionSha256"] = sha256_bytes(canonical_json(result))
    return result


def write_composed_human_core_reference(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Write only a derived manifest/projection; immutable exports are never rewritten."""

    result = compose_human_core_reference()
    path.write_bytes(canonical_json(result) + b"\n")
    return result
