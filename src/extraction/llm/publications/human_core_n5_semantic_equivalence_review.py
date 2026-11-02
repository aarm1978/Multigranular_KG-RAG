"""Build a neutral post-hoc semantic-equivalence review package for Human Core N=5.

The package is a deterministic, read-only view over strict Step 7B v0.1.1.  It
does not infer equivalence or calculate replacement metrics; researchers supply
all future dispositions outside this generated package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[4]
GOLD_ROOT = PROJECT_ROOT / "data/curation/papers/m2/human_core_gold"
STRICT_JSON = GOLD_ROOT / "publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze_v0.1.1.json"
STRICT_REPORT = GOLD_ROOT / "publication_human_core_n5_c1_confirmatory_evaluation_pre_freeze_v0.1.1.md"
STRICT_JSON_SHA256 = "3ad2db463d6a6d1fcbd6ba838e3f9a3288ea1f379a5aeee68b97c10add60978c"
STRICT_REPORT_SHA256 = "88d2ed4e7f9fd383a2202584d74546437c2b6f2e4846a1bcd9ba5023ffd597e9"
PROTOCOL_PATH = PROJECT_ROOT / "docs/publication_human_core_posthoc_semantic_equivalence_sensitivity_protocol_v0.1.md"
DEFAULT_OUTPUT = GOLD_ROOT / "publication_human_core_n5_posthoc_semantic_equivalence_review_package_v0.1.0.json"
DEFAULT_REPORT = GOLD_ROOT / "publication_human_core_n5_posthoc_semantic_equivalence_review_package_v0.1.0.md"
CORRESPONDENCE_DISPOSITIONS = (
    "semantic_equivalent",
    "not_equivalent",
    "target_or_class_disagreement",
    "insufficient_to_decide",
)
PREDICTION_SUPPORT_DISPOSITIONS = (
    "supported_as_proposed",
    "not_supported_as_proposed",
    "insufficient_evidence_to_decide",
)
OPTIONAL_EXPLANATORY_CODES = ("E1", "E2", "E3", "M1", "T1", "T2", "R1", "R2", "P1", "P2")


class ReviewPackageError(ValueError):
    """Raised when the strict authority cannot safely seed a neutral package."""


def _sha256(path: Path) -> str:
    """Return a file SHA-256 or fail closed when it is absent."""
    if not path.is_file():
        raise ReviewPackageError(f"missing required authority: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_strict_result() -> dict[str, Any]:
    """Load and validate the byte-preserved strict Step 7B v0.1.1 authority."""
    if _sha256(STRICT_JSON) != STRICT_JSON_SHA256 or _sha256(STRICT_REPORT) != STRICT_REPORT_SHA256:
        raise ReviewPackageError("strict Step 7B v0.1.1 authority differs from its preserved byte hashes")
    try:
        result = json.loads(STRICT_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewPackageError(f"strict authority is not valid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise ReviewPackageError("strict authority is not a JSON object")
    if result.get("artifactVersion") != "0.1.1" or result.get("status") != "PRE_FREEZE":
        raise ReviewPackageError("strict authority is not the expected PRE-FREEZE v0.1.1 result")
    if result.get("step7CExecuted") is not False or result.get("freezeOrClosureRecordCreated") is not False:
        raise ReviewPackageError("strict authority is not an open Step 7 PRE-FREEZE result")
    if result.get("providerModelCalls") != 0:
        raise ReviewPackageError("strict authority records unexpected provider/model calls")
    units = {row.get("sourceUnitID") for row in result.get("scoringOpportunities", [])}
    if len(units) != 5 or None in units:
        raise ReviewPackageError("strict authority does not bind exactly the frozen N=5 units")
    return result


def _item_id(prefix: str, strict_key: str) -> str:
    """Return a stable review identifier derived only from immutable provenance."""
    digest = hashlib.sha256(f"{prefix}|{strict_key}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _validate_record(record: Any) -> dict[str, Any]:
    """Validate the minimal stable fields carried from strict audit records."""
    if not isinstance(record, dict):
        raise ReviewPackageError("strict review source contains a non-object record")
    required = ("key", "kind", "sourceUnitID", "sourceArtifactID", "operationalTargetID", "candidateID", "evidence")
    if any(not record.get(field) for field in required):
        raise ReviewPackageError("strict review source lacks required record provenance")
    if record["kind"] not in {"node", "relation"}:
        raise ReviewPackageError("strict review source has an unsupported record kind")
    if record["kind"] == "node" and not record.get("ontologyClassID"):
        raise ReviewPackageError("strict node record lacks ontology class")
    if record["kind"] == "relation" and not record.get("ontologyRelationID"):
        raise ReviewPackageError("strict relation record lacks ontology relation type")
    return record


def _same_structural_bucket(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Select a neutral candidate bucket without asserting semantic equivalence."""
    if left["kind"] != right["kind"] or left["sourceUnitID"] != right["sourceUnitID"]:
        return False
    if left["operationalTargetID"] != right["operationalTargetID"]:
        return False
    if left["kind"] == "node":
        return left["ontologyClassID"] == right["ontologyClassID"]
    return left["ontologyRelationID"] == right["ontologyRelationID"]


def _record_view(record: dict[str, Any]) -> dict[str, Any]:
    """Copy only strict audit fields needed for a neutral human review."""
    fields = (
        "key", "side", "partition", "kind", "candidateID", "sourceUnitID",
        "sourceArtifactID", "operationalTargetID", "ontologyClassID",
        "ontologyRelationID", "label", "source", "target", "evidence",
    )
    return {field: record[field] for field in fields if field in record}


def _reviewer_fields(kind: str) -> dict[str, Any]:
    """Return intentionally unset researcher-only fields for one review item."""
    if kind == "correspondence":
        return {
            "researcherDisposition": None,
            "optionalExplanatoryCode": None,
            "researcherNote": None,
        }
    return {
        "predictionSourceSupportJudgment": None,
        "optionalExplanatoryCode": None,
        "researcherNote": None,
    }


def build_package() -> dict[str, Any]:
    """Build the deterministic neutral review package from strict v0.1.1 records."""
    strict = _load_strict_result()
    matched = strict.get("matchedRecords")
    unmatched_references = strict.get("unmatchedReferenceRecords")
    unmatched_predictions = strict.get("unmatchedPredictionRecords")
    if not isinstance(matched, dict) or not isinstance(unmatched_references, list) or not isinstance(unmatched_predictions, list):
        raise ReviewPackageError("strict authority lacks auditable match/unmatch record collections")

    references: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    strict_prediction_for_reference: dict[str, dict[str, Any]] = {}
    strict_evidence_for_reference: dict[str, dict[str, Any]] = {}
    matched_prediction_keys: set[str] = set()
    for plural, kind in (("nodes", "node"), ("relations", "relation")):
        for pair in matched.get(plural, []):
            if not isinstance(pair, dict):
                raise ReviewPackageError("strict authority has a malformed matched pair")
            reference, prediction = _validate_record(pair.get("reference")), _validate_record(pair.get("prediction"))
            if reference["kind"] != kind or prediction["kind"] != kind:
                raise ReviewPackageError("strict authority matched pair kind is inconsistent")
            references.append(reference)
            predictions.append(prediction)
            strict_prediction_for_reference[reference["key"]] = prediction
            strict_evidence_for_reference[reference["key"]] = pair.get("evidence", {})
            matched_prediction_keys.add(prediction["key"])
    for record in unmatched_references:
        references.append(_validate_record(record))
    for record in unmatched_predictions:
        predictions.append(_validate_record(record))

    reference_keys = [record["key"] for record in references]
    prediction_keys = [record["key"] for record in predictions]
    if len(reference_keys) != len(set(reference_keys)) or len(prediction_keys) != len(set(prediction_keys)):
        raise ReviewPackageError("strict authority review population contains duplicate stable record keys")

    grouped: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"correspondenceReviewItems": [], "c1OnlySourceSupportReviewItems": []}
    )
    for reference in sorted(references, key=lambda row: row["key"]):
        strict_prediction = strict_prediction_for_reference.get(reference["key"])
        candidates = [
            _record_view(prediction)
            for prediction in sorted(predictions, key=lambda row: row["key"])
            if _same_structural_bucket(reference, prediction)
        ]
        item = {
            "reviewItemID": _item_id("correspondence", reference["key"]),
            "reviewItemType": "human_core_to_c1_correspondence",
            "strictMatchStatus": "strict_true_positive" if strict_prediction else "strict_unmatched_human_core",
            "candidateSelectionBasis": "same frozen source unit, operational target, and ontology class for nodes; same frozen source unit, operational target, and ontology relation type for relations; structural candidacy is not a semantic judgment",
            "humanCoreRecord": _record_view(reference),
            "strictC1Record": _record_view(strict_prediction) if strict_prediction else None,
            "strictEvidenceDiagnostics": strict_evidence_for_reference.get(reference["key"]),
            "plausibleSameTargetClassCandidates": candidates,
            **_reviewer_fields("correspondence"),
        }
        grouped[(reference["sourceUnitID"], reference["operationalTargetID"], reference["kind"])]["correspondenceReviewItems"].append(item)

    for prediction in sorted(predictions, key=lambda row: row["key"]):
        if prediction["key"] in matched_prediction_keys:
            continue
        human_candidates = [
            _record_view(reference)
            for reference in sorted(references, key=lambda row: row["key"])
            if _same_structural_bucket(prediction, reference)
        ]
        item = {
            "reviewItemID": _item_id("c1-only-source-support", prediction["key"]),
            "reviewItemType": "c1_only_source_support",
            "strictMatchStatus": "strict_c1_only",
            "c1Record": _record_view(prediction),
            "sameTargetClassHumanCoreRecords": human_candidates,
            "sourceSupportRule": "Researcher judges support for this C1 assertion as proposed. This item cannot add to, merge with, or rewrite Human Core, and a relation cannot be rescued merely because its nodes exist.",
            **_reviewer_fields("prediction_support"),
        }
        grouped[(prediction["sourceUnitID"], prediction["operationalTargetID"], prediction["kind"])]["c1OnlySourceSupportReviewItems"].append(item)

    units: list[dict[str, Any]] = []
    for unit in sorted({key[0] for key in grouped}):
        targets: list[dict[str, Any]] = []
        for key in sorted(key for key in grouped if key[0] == unit):
            _, target, kind = key
            contents = grouped[key]
            targets.append({
                "operationalTargetID": target,
                "kind": kind,
                "correspondenceReviewItems": contents["correspondenceReviewItems"],
                "c1OnlySourceSupportReviewItems": contents["c1OnlySourceSupportReviewItems"],
            })
        units.append({"sourceUnitID": unit, "targets": targets})

    correspondence_items = sum(len(value["correspondenceReviewItems"]) for value in grouped.values())
    c1_only_items = sum(len(value["c1OnlySourceSupportReviewItems"]) for value in grouped.values())
    candidate_groups = sum(
        len(value["correspondenceReviewItems"]) + len(value["c1OnlySourceSupportReviewItems"])
        for value in grouped.values()
    )
    return {
        "artifactType": "publication_human_core_n5_posthoc_semantic_equivalence_review_package",
        "artifactVersion": "0.1.0",
        "status": "RESEARCHER_REVIEW_PENDING",
        "scope": "post-hoc secondary researcher-reviewed semantic-equivalence sensitivity package; not strict Step 7B scoring",
        "strictEvaluationPreserved": {
            "path": str(STRICT_JSON.relative_to(PROJECT_ROOT)),
            "sha256": STRICT_JSON_SHA256,
            "reportPath": str(STRICT_REPORT.relative_to(PROJECT_ROOT)),
            "reportSha256": STRICT_REPORT_SHA256,
            "modified": False,
            "superseded": False,
        },
        "protocol": {
            "path": str(PROTOCOL_PATH.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(PROTOCOL_PATH),
            "correspondenceDispositions": list(CORRESPONDENCE_DISPOSITIONS),
            "predictionSourceSupportDispositions": list(PREDICTION_SUPPORT_DISPOSITIONS),
            "optionalExplanatoryCodes": list(OPTIONAL_EXPLANATORY_CODES),
        },
        "guardrails": [
            "No semantic judgment, equivalence, rescue, merge, relabeling, normalization, inference, adjudication, or metric is computed automatically.",
            "Same-target/class structural candidates are prompts for researcher review, not automatic correspondences.",
            "C1-only source-support judgments are separate from Human Core and cannot rewrite it.",
            "No provider/model calls occurred; Step 7C was not executed.",
        ],
        "counts": {
            "sourceUnitCount": len(units),
            "strictTruePositivePairs": len(strict_prediction_for_reference),
            "unmatchedHumanCoreRecords": len(unmatched_references),
            "c1OnlyAssertions": c1_only_items,
            "correspondenceReviewItems": correspondence_items,
            "reviewItems": correspondence_items + c1_only_items,
            "candidateGroups": candidate_groups,
        },
        "reviewGroupsByUnitAndOperationalTarget": units,
        "providerModelCalls": 0,
        "step7CExecuted": False,
        "freezeOrClosureRecordCreated": False,
    }


def render_report(package: dict[str, Any]) -> str:
    """Render a concise researcher-facing index for the neutral JSON package."""
    lines = [
        "# Human Core N=5 Post-hoc Semantic-Equivalence Review Package", "",
        "This is a neutral, researcher-reviewed secondary sensitivity package. It does not modify, supersede, or recompute strict Step 7B v0.1.1.", "",
        "## Review instructions", "",
        "- Review every strict TP and unmatched Human Core item using the correspondence disposition field.",
        "- Review every C1-only item using its separate prediction source-support field.",
        "- Structural candidates are not automatic matches. Evidence boundaries may inform a judgment but are never sufficient by themselves.",
        "- Do not use a C1-only assertion to rewrite Human Core or rescue a relation merely because nodes exist.", "",
        "## Counts", "",
    ]
    for key, value in package["counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(("", "## Groups", ""))
    for unit in package["reviewGroupsByUnitAndOperationalTarget"]:
        lines.append(f"### `{unit['sourceUnitID']}`")
        lines.append("")
        for target in unit["targets"]:
            lines.append(
                f"- `{target['operationalTargetID']}` ({target['kind']}): "
                f"correspondence items={len(target['correspondenceReviewItems'])}; "
                f"C1-only source-support items={len(target['c1OnlySourceSupportReviewItems'])}."
            )
        lines.append("")
    lines.extend(("The JSON companion contains stable IDs, labels, evidence spans, strict-match status, and same-target/class structural candidate sets. All researcher disposition, explanatory-code, and note fields are intentionally unset.", ""))
    return "\n".join(lines)


def main() -> None:
    """Write the deterministic neutral review package and reviewer-facing index."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise ReviewPackageError("review package output already exists; refusing to overwrite researcher review material")
    package = build_package()
    args.output.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(render_report(package), encoding="utf-8")


if __name__ == "__main__":
    main()
