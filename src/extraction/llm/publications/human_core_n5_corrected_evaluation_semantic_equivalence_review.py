"""Build a neutral review instrument for corrected Pilot 1 Step 7B results."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import human_core_n5_semantic_equivalence_review as prior
from . import human_core_n5_semantic_equivalence_review_v011 as historical
from .human_core_n5_evaluation import (
    V010_OUTPUT,
    V010_OUTPUT_SHA256,
    V010_REPORT,
    V010_REPORT_SHA256,
    _endpoint_identity,
    _node_indexes,
    _record_view,
    load_frozen_inputs,
)


STRICT_JSON = prior.GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_step7b_pre_freeze_v1.0.0.json"
STRICT_REPORT = STRICT_JSON.with_suffix(".md")
STRICT_JSON_SHA256 = "5d03aa098e0218614a92ea1c096cd1b22a5df2e56973a471fc9aa15eecdad7ca"
STRICT_PREDICTIONS_SHA256 = "e888c4c4c68ede19cb4c65275b96637fd183e64f887d9a649f70e57f98eadb86"
PROTOCOL = historical.PROTOCOL
OUTPUT = prior.GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_posthoc_semantic_equivalence_review_package_v1.0.0.json"
REPORT = OUTPUT.with_suffix(".md")
HISTORICAL_V011_PACKAGE_SHA256 = "d376ef1912e617d4f92320d34c3e2facacbbbe89b1eaf571e82ee2308b5ce6d9"
HISTORICAL_V011_REPORT_SHA256 = "e1b8cc7570fe1ac83d088010e537e7b996a2d9a00038b7eeff6882ad545bf675"
CODES = historical.CODES


def _sha256(path: Path) -> str:
    """Return a file digest through the historical fail-closed helper."""
    return prior._sha256(path)


def verify_historical_preservation() -> None:
    """Fail closed if any historical C1 Step 7/review authority changed."""
    historical.verify_preservation()
    for path, digest in (
        (V010_OUTPUT, V010_OUTPUT_SHA256),
        (V010_REPORT, V010_REPORT_SHA256),
        (historical.PROTOCOL, "940499ad028cfadefe00e49f12fb95e5a5b7150047977910e56667f53834f656"),
        (historical.OUTPUT, HISTORICAL_V011_PACKAGE_SHA256),
        (historical.REPORT, HISTORICAL_V011_REPORT_SHA256),
    ):
        if _sha256(path) != digest:
            raise prior.ReviewPackageError(f"preserved historical artifact changed: {path}")


def _load_corrected_strict_result() -> dict[str, Any]:
    """Load and validate the sole corrected strict Step 7B authority."""
    if _sha256(STRICT_JSON) != STRICT_JSON_SHA256:
        raise prior.ReviewPackageError("corrected strict Step 7B result differs from its frozen hash")
    value = json.loads(STRICT_JSON.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise prior.ReviewPackageError("corrected strict Step 7B result is not an object")
    if (
        value.get("artifactType") != "publication_human_core_n5_corrected_evaluation_step7b_pre_freeze"
        or value.get("artifactVersion") != "1.0.0"
        or value.get("status") != "PRE_FREEZE"
        or value.get("providerModelCalls") != 0
        or value.get("step7CExecuted") is not False
        or value.get("freezeOrClosureRecordCreated") is not False
    ):
        raise prior.ReviewPackageError("corrected strict Step 7B result has an invalid identity or status")
    frozen = value.get("frozenInputs", {})
    if (
        frozen.get("predictionAuthority") != "corrected_pilot1_evaluation"
        or frozen.get("canonicalPredictions", {}).get("sha256") != STRICT_PREDICTIONS_SHA256
    ):
        raise prior.ReviewPackageError("corrected strict result is not bound to the corrected prediction source")
    aggregate = value.get("aggregate", {})
    if (
        aggregate.get("nodes", {}).get("referenceSupport") != 118
        or aggregate.get("nodes", {}).get("predictionSupport") != 109
        or aggregate.get("relations", {}).get("referenceSupport") != 61
        or aggregate.get("relations", {}).get("predictionSupport") != 68
    ):
        raise prior.ReviewPackageError("corrected strict result differs from fixed review denominators")
    return value


def items(package: dict[str, Any], field: str) -> list[dict[str, Any]]:
    """Flatten one corrected review population in deterministic group order."""
    return [item for unit in package["reviewGroupsByUnitAndOperationalTarget"]
            for target in unit["targets"] for item in target[field]]


def validate_selections(package: dict[str, Any]) -> None:
    """Validate optional researcher selections without making a judgment."""
    predictions = package["predictionRecordsByKey"]
    used: set[str] = set()
    references: set[str] = set()
    for item in items(package, "correspondenceReviewItems"):
        reference = item["humanCoreRecord"]
        if reference["key"] in references:
            raise prior.ReviewPackageError("duplicate Human Core identity")
        references.add(reference["key"])
        disposition, selected = item["researcherDisposition"], item["reviewedPredictionRecordKey"]
        if disposition is not None and disposition not in prior.CORRESPONDENCE_DISPOSITIONS:
            raise prior.ReviewPackageError("unknown correspondence disposition")
        if disposition == "semantic_equivalent" and selected is None:
            raise prior.ReviewPackageError("semantic_equivalent requires a selected prediction key")
        if selected is None:
            continue
        prediction = predictions.get(selected)
        if prediction is None or prediction["sourceUnitID"] != reference["sourceUnitID"]:
            raise prior.ReviewPackageError("selected prediction key does not resolve in the same unit")
        if disposition != "target_or_class_disagreement" and not prior._same_structural_bucket(reference, prediction):
            raise prior.ReviewPackageError("selected prediction record is ineligible for correspondence")
        if disposition == "semantic_equivalent":
            if selected in used:
                raise prior.ReviewPackageError("semantic-equivalent selections are not one-to-one")
            used.add(selected)


def build_package() -> dict[str, Any]:
    """Build the corrected, judgment-free secondary review instrument."""
    verify_historical_preservation()
    strict = _load_corrected_strict_result()
    matched = strict.get("matchedRecords")
    unmatched_references = strict.get("unmatchedReferenceRecords")
    unmatched_predictions = strict.get("unmatchedPredictionRecords")
    if not isinstance(matched, dict) or not isinstance(unmatched_references, list) or not isinstance(unmatched_predictions, list):
        raise prior.ReviewPackageError("corrected strict authority lacks auditable match/unmatch records")

    references: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    strict_prediction_for_reference: dict[str, dict[str, Any]] = {}
    strict_evidence_for_reference: dict[str, dict[str, Any]] = {}
    matched_prediction_keys: set[str] = set()
    for plural, kind in (("nodes", "node"), ("relations", "relation")):
        for pair in matched.get(plural, []):
            reference = prior._validate_record(pair.get("reference"))
            prediction = prior._validate_record(pair.get("prediction"))
            if reference["kind"] != kind or prediction["kind"] != kind:
                raise prior.ReviewPackageError("corrected strict matched pair kind is inconsistent")
            references.append(reference)
            predictions.append(prediction)
            strict_prediction_for_reference[reference["key"]] = prediction
            strict_evidence_for_reference[reference["key"]] = pair.get("evidence", {})
            matched_prediction_keys.add(prediction["key"])
    references.extend(prior._validate_record(record) for record in unmatched_references)
    predictions.extend(prior._validate_record(record) for record in unmatched_predictions)
    if len({row["key"] for row in references}) != len(references) or len({row["key"] for row in predictions}) != len(predictions):
        raise prior.ReviewPackageError("corrected strict review population contains duplicate stable keys")

    inputs = load_frozen_inputs()
    all_records = {record.key: record for record in inputs.references + inputs.predictions}
    node_index = _node_indexes(all_records.values())

    def enrich(view: dict[str, Any]) -> dict[str, Any]:
        """Expose exact relation endpoint context without inferring equivalence."""
        if view["kind"] != "relation":
            return prior._record_view(view)
        relation = all_records.get(view["key"])
        if relation is None:
            raise prior.ReviewPackageError("corrected strict relation is absent from bound input authority")
        contexts: dict[str, Any] = {}
        for role in ("source", "target"):
            endpoint = relation.value[role]
            identity = _endpoint_identity(relation, endpoint, node_index, inputs.routes, inputs.baseline_aliases)
            node = all_records.get(identity[1]) if identity[0] == "node" else None
            contexts[role] = {
                "authoredEndpoint": endpoint,
                "stableEndpointIdentity": list(identity),
                "record": _record_view(node) if node else None,
                "resolution": "exact_node_record" if node else "deterministic_identity_context",
                "deterministicContext": None if node else {
                    "referenceID": endpoint["referenceID"], "artifactID": endpoint.get("artifactID"),
                    "label": None, "operationalTargetID": None, "ontologyClassID": None, "evidence": [],
                },
            }
        return {**prior._record_view(view), "endpointContext": contexts}

    grouped: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"correspondenceReviewItems": [], "predictionSourceSupportReviewItems": []}
    )
    prediction_views = {row["key"]: enrich(row) for row in predictions}
    for reference in sorted(references, key=lambda row: row["key"]):
        strict_prediction = strict_prediction_for_reference.get(reference["key"])
        item = {
            "reviewItemID": prior._item_id("corrected-correspondence", reference["key"]),
            "reviewItemType": "human_core_to_corrected_prediction_correspondence",
            "strictMatchStatus": "strict_true_positive" if strict_prediction else "strict_unmatched_human_core",
            "candidateSelectionBasis": "same frozen source unit, operational target, and ontology class for nodes; same frozen source unit, operational target, and ontology relation type for relations; structural candidacy is not a semantic judgment",
            "humanCoreRecord": enrich(reference),
            "strictPredictionRecord": enrich(strict_prediction) if strict_prediction else None,
            "strictEvidenceDiagnostics": strict_evidence_for_reference.get(reference["key"]),
            "plausibleSameTargetClassCandidates": [prediction_views[row["key"]] for row in sorted(predictions, key=lambda row: row["key"]) if prior._same_structural_bucket(reference, row)],
            "reviewedPredictionRecordKey": None,
            **prior._reviewer_fields("correspondence"),
        }
        grouped[(reference["sourceUnitID"], reference["operationalTargetID"], reference["kind"])]["correspondenceReviewItems"].append(item)
    for key, prediction in prediction_views.items():
        grouped[(prediction["sourceUnitID"], prediction["operationalTargetID"], prediction["kind"])]["predictionSourceSupportReviewItems"].append({
            "reviewItemID": prior._item_id("corrected-prediction-source-support", key),
            "reviewItemType": "independent_prediction_source_support",
            "strictMatchStatus": "strict_true_positive" if key in matched_prediction_keys else "strict_prediction_only",
            "predictionRecord": prediction,
            "sourceSupportRule": "Researcher judges support for this corrected prediction as proposed. This item cannot add to, merge with, or rewrite Human Core, and a relation cannot be rescued merely because its nodes exist.",
            **prior._reviewer_fields("prediction_support"),
        })

    units = []
    for unit in sorted({key[0] for key in grouped}):
        targets = []
        for _, target, kind in sorted(key for key in grouped if key[0] == unit):
            contents = grouped[(unit, target, kind)]
            targets.append({"operationalTargetID": target, "kind": kind, **contents})
        units.append({"sourceUnitID": unit, "targets": targets})
    correspondence = items({"reviewGroupsByUnitAndOperationalTarget": units}, "correspondenceReviewItems")
    support = items({"reviewGroupsByUnitAndOperationalTarget": units}, "predictionSourceSupportReviewItems")
    reference_counts = dict(Counter(item["humanCoreRecord"]["kind"] for item in correspondence))
    prediction_counts = dict(Counter(item["predictionRecord"]["kind"] for item in support))
    if reference_counts != {"node": 118, "relation": 61} or prediction_counts != {"node": 109, "relation": 68}:
        raise prior.ReviewPackageError("corrected review population differs from fixed denominators")
    package = {
        "artifactType": "publication_human_core_n5_corrected_evaluation_posthoc_semantic_equivalence_review_package",
        "artifactVersion": "1.0.0",
        "status": "RESEARCHER_REVIEW_PENDING",
        "scope": "post-hoc secondary researcher-reviewed semantic-equivalence sensitivity package; not strict Step 7B scoring",
        "correctedStrictEvaluation": {"path": str(STRICT_JSON.relative_to(prior.PROJECT_ROOT)), "sha256": STRICT_JSON_SHA256, "reportPath": str(STRICT_REPORT.relative_to(prior.PROJECT_ROOT)), "modified": False},
        "correctedPredictionAuthority": {"sha256": STRICT_PREDICTIONS_SHA256, "cohort": "human_core_n5", "excludedCohort": "step5_n6"},
        "protocol": {"path": str(PROTOCOL.relative_to(prior.PROJECT_ROOT)), "sha256": _sha256(PROTOCOL), "reusedReviewSemantics": "v0.1.1", "explanatoryCodeDefinitions": CODES},
        "historicalC1ArtifactsPreserved": True,
        "predictionRecordsByKey": dict(sorted(prediction_views.items())),
        "endpointContextAuthorities": inputs.provenance,
        "secondaryMetricDefinitions": {
            "status": "FIXED_BEFORE_REVIEW",
            "humanCoreSemanticRecovery": {"numerator": "one-to-one researcher-confirmed semantic_equivalent Human Core records", "denominators": reference_counts, "values": None},
            "correctedPredictionSourceSupportedRate": {"numerator": "supported_as_proposed corrected predictions", "denominators": prediction_counts, "values": None, "unsupportedCounts": None, "insufficientCounts": None},
            "computationGate": "All researcher judgments complete and global one-to-one selections validated",
        },
        "counts": {"sourceUnitCount": len(units), "strictTruePositivePairs": len(matched_prediction_keys), "unmatchedHumanCoreRecords": len(unmatched_references), "correctedPredictionAssertions": len(support), "correspondenceReviewItems": len(correspondence), "predictionSourceSupportReviewItems": len(support), "reviewItems": len(correspondence) + len(support), "humanCoreByKind": reference_counts, "predictionsByKind": prediction_counts},
        "reviewGroupsByUnitAndOperationalTarget": units,
        "providerModelCalls": 0,
        "step7CExecuted": False,
        "freezeOrClosureRecordCreated": False,
    }
    validate_selections(package)
    verify_historical_preservation()
    return package


def render_report(package: dict[str, Any]) -> str:
    """Render the corrected-evaluation review index without judgments."""
    lines = ["# Human Core N=5 Corrected Evaluation Secondary Review Instrument", "", "Review pending. This reuses v0.1.1 review semantics against the corrected Step 7B realization; no historical C1 artifact or researcher judgment is modified.", "", "Human-Core semantic recovery: confirmed one-to-one equivalents / 118 nodes or 61 relations.", "Corrected prediction source-supported rate: supported_as_proposed / 109 nodes or 68 relations.", "All researcher selections, dispositions, explanatory codes, notes, and secondary metric values are unset.", "", "## Populations", "", json.dumps(package["counts"], sort_keys=True), ""]
    for unit in package["reviewGroupsByUnitAndOperationalTarget"]:
        lines.extend((f"## {unit['sourceUnitID']}", ""))
        for target in unit["targets"]:
            lines.append(f"- {target['operationalTargetID']}: {len(target['correspondenceReviewItems'])} correspondence; {len(target['predictionSourceSupportReviewItems'])} support items.")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Materialize the new corrected-evaluation instrument without overwriting history."""
    if OUTPUT.exists() or REPORT.exists():
        raise prior.ReviewPackageError("corrected review output already exists; refusing to overwrite review material")
    package = build_package()
    OUTPUT.write_text(json.dumps(package, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(package), encoding="utf-8")
    verify_historical_preservation()


if __name__ == "__main__":
    main()
