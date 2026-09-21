"""Materialize the read-only Annotator A Human Core N=2 composite view."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GOLD_ROOT = ROOT / "data/curation/papers/m2/human_core_gold"
PRIMARY_EXPORT = ROOT / "var/publication_pilot1_annotation/human-core/primary-researcher/exports/HUMAN_CORE_N5_PRIMARY_V1.annotation.json"
SUPPLEMENTAL_EXPORT = ROOT / "var/publication_pilot1_annotation/human-core/supplemental-researcher/exports/HUMAN_CORE_N5_SUPPLEMENTAL_V015.annotation.json"
PRIMARY_BASELINE = GOLD_ROOT / "publication_human_core_primary_annotation_baseline_v1.0.json"
SUPPLEMENTAL_PRESERVATION = GOLD_ROOT / "publication_human_core_supplemental_annotation_preservation_v0.1.5.json"
PRIMARY_PACKAGE = GOLD_ROOT / "publication_human_core_primary_annotation_package_v1.1.json"
SUPPLEMENTAL_PACKAGE = GOLD_ROOT / "publication_human_core_supplemental_annotation_package_v0.1.5.json"
SAMPLE_FREEZE = GOLD_ROOT / "publication_human_core_gold_sample_freeze_v1.0.json"
DEFAULT_OUTPUT = GOLD_ROOT / "publication_human_core_annotator_a_n2_composite_view_v0.1.5.json"

N2_UNITS = (
    "pub:34:sec:0015:unit:0001",
    "pub:79:sec:0004:unit:0001",
)


class AnnotatorAN2ViewError(ValueError):
    """Report a frozen-source or exact-membership violation."""


def _sha256(path: Path) -> str:
    """Return the SHA-256 of one file's exact bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object, rejecting other top-level values."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AnnotatorAN2ViewError(f"invalid JSON authority: {path.name}")
    return value


def _verify_bound_file(path: Path, expected: str, label: str) -> None:
    """Fail closed unless a versioned authority binds these exact bytes."""

    if _sha256(path) != expected:
        raise AnnotatorAN2ViewError(f"{label} hash mismatch: {path.name}")


def _selected_rows(export: dict[str, Any], session_id: str, label: str) -> dict[str, dict[str, Any]]:
    """Return exactly the submitted N=2 records from one immutable A export."""

    if export.get("annotationSessionID") != session_id:
        raise AnnotatorAN2ViewError(f"{label} session identity mismatch")
    if export.get("annotatorID") != "HUMAN_CORE_PRIMARY_RESEARCHER":
        raise AnnotatorAN2ViewError(f"{label} annotator identity mismatch")
    rows = export.get("annotations")
    if not isinstance(rows, list):
        raise AnnotatorAN2ViewError(f"{label} annotations are invalid")
    by_unit = {str(row.get("sourceUnitID")): row for row in rows if isinstance(row, dict)}
    if len(by_unit) != len(rows) or set(N2_UNITS) - set(by_unit):
        raise AnnotatorAN2ViewError(f"{label} exact N=2 records are unavailable")
    selected = {unit: by_unit[unit] for unit in N2_UNITS}
    if {row.get("status") for row in selected.values()} != {"submitted"}:
        raise AnnotatorAN2ViewError(f"{label} N=2 records are not all submitted")
    return selected


def build_annotator_a_n2_view() -> dict[str, Any]:
    """Build an immutable-source projection without changing any assertion data."""

    primary_baseline = _load_json(PRIMARY_BASELINE)
    supplemental_preservation = _load_json(SUPPLEMENTAL_PRESERVATION)
    _verify_bound_file(PRIMARY_EXPORT, primary_baseline["deterministicSessionExport"]["sha256"], "primary export")
    _verify_bound_file(SUPPLEMENTAL_EXPORT, supplemental_preservation["supplementalDeterministicSessionExport"]["sha256"], "supplemental export")
    _verify_bound_file(PRIMARY_PACKAGE, primary_baseline["packageAuthority"]["sha256"], "primary package")
    _verify_bound_file(SUPPLEMENTAL_PACKAGE, supplemental_preservation["authorities"]["supplementalPackage"]["sha256"], "supplemental package")
    _verify_bound_file(SAMPLE_FREEZE, primary_baseline["packageAuthority"]["freezeSha256"], "sample freeze")

    freeze = _load_json(SAMPLE_FREEZE)
    primary_package = _load_json(PRIMARY_PACKAGE)
    if tuple(primary_package["freeze"]["reliabilitySourceUnitIDs"]) != N2_UNITS:
        raise AnnotatorAN2ViewError("primary package does not bind the exact N=2 membership")
    if tuple(freeze["reliabilitySubset"]["sourceUnitIDs"]) != N2_UNITS:
        raise AnnotatorAN2ViewError("sample freeze does not bind the exact N=2 membership")

    primary = _load_json(PRIMARY_EXPORT)
    supplemental = _load_json(SUPPLEMENTAL_EXPORT)
    primary_rows = _selected_rows(primary, "HUMAN_CORE_N5_PRIMARY_V1", "primary")
    supplemental_rows = _selected_rows(supplemental, "HUMAN_CORE_N5_SUPPLEMENTAL_V015", "supplemental")
    result: dict[str, Any] = {
        "artifactType": "read_only_annotator_a_human_core_n2_composite_view",
        "artifactVersion": "0.1.5.0",
        "readOnly": True,
        "destructiveMergeAuthorized": False,
        "assertionTreatment": "verbatim_partitioned_source_records; no normalization_deduplication_relabeling_repair_inference_or_adjudication",
        "sourceAuthorities": {
            "primaryV014": {
                "preservationRecord": {"path": str(PRIMARY_BASELINE.relative_to(ROOT)), "sha256": _sha256(PRIMARY_BASELINE)},
                "package": {"path": str(PRIMARY_PACKAGE.relative_to(ROOT)), "sha256": _sha256(PRIMARY_PACKAGE)},
                "export": {"path": str(PRIMARY_EXPORT.relative_to(ROOT)), "sha256": _sha256(PRIMARY_EXPORT), "annotationSessionID": primary["annotationSessionID"]},
            },
            "supplementalV015": {
                "preservationRecord": {"path": str(SUPPLEMENTAL_PRESERVATION.relative_to(ROOT)), "sha256": _sha256(SUPPLEMENTAL_PRESERVATION)},
                "package": {"path": str(SUPPLEMENTAL_PACKAGE.relative_to(ROOT)), "sha256": _sha256(SUPPLEMENTAL_PACKAGE)},
                "export": {"path": str(SUPPLEMENTAL_EXPORT.relative_to(ROOT)), "sha256": _sha256(SUPPLEMENTAL_EXPORT), "annotationSessionID": supplemental["annotationSessionID"]},
            },
            "n2MembershipFreeze": {"path": str(SAMPLE_FREEZE.relative_to(ROOT)), "sha256": _sha256(SAMPLE_FREEZE)},
        },
        "sourceUnitIDs": list(N2_UNITS),
        "units": [
            {"sourceUnitID": unit, "primaryV014": primary_rows[unit], "supplementalV015": supplemental_rows[unit]}
            for unit in N2_UNITS
        ],
    }
    return result


def serialize_annotator_a_n2_view() -> bytes:
    """Return stable UTF-8 bytes for the deterministic projection."""

    return (json.dumps(build_annotator_a_n2_view(), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_annotator_a_n2_view(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Write the derived view only after all source checks pass."""

    data = serialize_annotator_a_n2_view()
    path.write_bytes(data)
    return json.loads(data)


if __name__ == "__main__":
    write_annotator_a_n2_view()
