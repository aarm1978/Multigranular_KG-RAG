"""Materialize researcher-confirmed corrected Step 7 secondary review decisions."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import human_core_n5_corrected_evaluation_semantic_equivalence_review as instrument
from . import human_core_n5_semantic_equivalence_review as prior


LEDGER = prior.GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_researcher_judgment_ledger_v1.0.0.json"
LEDGER_REPORT = LEDGER.with_suffix(".md")
LEDGER_SHA256 = "122319d188e4ee049ab6414b5bf2424382f0ff00634c003963f2aee3451db757"
SOURCE_PACKAGE = instrument.OUTPUT
SOURCE_PACKAGE_SHA256 = "c3aefd029973da10b1cccd45b4558f864e9bcc75d55e3d2c5c219b753ec6a03b"
OUTPUT = prior.GOLD_ROOT / "publication_human_core_n5_corrected_evaluation_posthoc_semantic_equivalence_researcher_review_v1.0.0.json"
REPORT = OUTPUT.with_suffix(".md")
PASS_CONFIGURATION = {
    "A_nodeCorrespondence": ("correspondenceReviewItems", "node", "researcherDisposition"),
    "B_nodePredictionSourceSupport": ("predictionSourceSupportReviewItems", "node", "predictionSourceSupportJudgment"),
    "C_relationCorrespondence": ("correspondenceReviewItems", "relation", "researcherDisposition"),
    "D_relationPredictionSourceSupport": ("predictionSourceSupportReviewItems", "relation", "predictionSourceSupportJudgment"),
}
EXPECTED_POPULATION = {"A_nodeCorrespondence": 118, "B_nodePredictionSourceSupport": 109, "C_relationCorrespondence": 61, "D_relationPredictionSourceSupport": 68}


def _sha256(path: Path) -> str:
    """Return a required artifact SHA-256 or fail closed."""
    return prior._sha256(path)


def _load_json(path: Path) -> dict[str, Any]:
    """Load one object-only JSON authority."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise prior.ReviewPackageError(f"authority is not an object: {path}")
    return value


def _load_authorities() -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify immutable ledger and source-package identities before materialization."""
    instrument.verify_historical_preservation()
    if _sha256(LEDGER) != LEDGER_SHA256:
        raise prior.ReviewPackageError("researcher judgment ledger differs from its required SHA-256")
    if _sha256(SOURCE_PACKAGE) != SOURCE_PACKAGE_SHA256:
        raise prior.ReviewPackageError("source review package differs from its required SHA-256")
    ledger, source = _load_json(LEDGER), _load_json(SOURCE_PACKAGE)
    if ledger.get("status") != "RESEARCHER_CONFIRMED_READY_FOR_MATERIALIZATION":
        raise prior.ReviewPackageError("researcher ledger is not ready for deterministic materialization")
    if ledger.get("sourceInstrument", {}).get("sha256") != SOURCE_PACKAGE_SHA256:
        raise prior.ReviewPackageError("ledger source instrument binding differs from the source package")
    if ledger.get("boundAuthorities", {}).get("correctedStrictEvaluationSha256") != instrument.STRICT_JSON_SHA256:
        raise prior.ReviewPackageError("ledger strict Step 7B binding is invalid")
    if ledger.get("boundAuthorities", {}).get("correctedCanonicalPredictionsSha256") != instrument.STRICT_PREDICTIONS_SHA256:
        raise prior.ReviewPackageError("ledger corrected prediction binding is invalid")
    if source.get("counts", {}).get("humanCoreByKind") != {"node": 118, "relation": 61} or source.get("counts", {}).get("predictionsByKind") != {"node": 109, "relation": 68}:
        raise prior.ReviewPackageError("source review package population differs from the frozen denominator")
    if source.get("counts", {}).get("reviewItems") != 356:
        raise prior.ReviewPackageError("source review package does not contain exactly 356 review items")
    return ledger, source


def _index_source(source: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Index source review items only by exact reviewItemID and pass identity."""
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for pass_name, (field, kind, _) in PASS_CONFIGURATION.items():
        for item in instrument.items(source, field):
            record = item["humanCoreRecord"] if field == "correspondenceReviewItems" else item["predictionRecord"]
            if record.get("kind") != kind:
                continue
            review_id = item.get("reviewItemID")
            if not isinstance(review_id, str) or review_id in index:
                raise prior.ReviewPackageError("source review item identity is absent or duplicated")
            index[review_id] = (pass_name, item)
    if len(index) != 356:
        raise prior.ReviewPackageError("source review-item index does not contain exactly 356 identities")
    return index


def _ledger_entries(ledger: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Index each ledger entry exactly once, retaining its declared pass."""
    passes = ledger.get("passes")
    if not isinstance(passes, dict) or set(passes) != set(PASS_CONFIGURATION):
        raise prior.ReviewPackageError("ledger passes differ from the frozen four-pass population")
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for pass_name, expected in EXPECTED_POPULATION.items():
        entries = passes[pass_name]
        if not isinstance(entries, list) or len(entries) != expected:
            raise prior.ReviewPackageError(f"ledger {pass_name} population differs from its fixed count")
        for entry in entries:
            review_id = entry.get("reviewItemID") if isinstance(entry, dict) else None
            if not isinstance(review_id, str) or review_id in index:
                raise prior.ReviewPackageError("ledger reviewItemID is absent or duplicated")
            index[review_id] = (pass_name, entry)
    if len(index) != 356:
        raise prior.ReviewPackageError("ledger does not contain exactly 356 review item identities")
    return index


def _validate_and_apply(ledger: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Copy ledger fields by exact identity, then validate every frozen invariant."""
    materialized = copy.deepcopy(source)
    source_index, ledger_index = _index_source(materialized), _ledger_entries(ledger)
    if set(source_index) != set(ledger_index):
        missing, extra = set(source_index) - set(ledger_index), set(ledger_index) - set(source_index)
        raise prior.ReviewPackageError(f"ledger/source reviewItemID mismatch: missing={len(missing)} extra={len(extra)}")
    for review_id, (pass_name, entry) in ledger_index.items():
        source_pass, item = source_index[review_id]
        field, kind, judgment_field = PASS_CONFIGURATION[pass_name]
        if source_pass != pass_name:
            raise prior.ReviewPackageError("ledger reviewItemID resolves to the wrong review pass")
        record = item["humanCoreRecord"] if field == "correspondenceReviewItems" else item["predictionRecord"]
        record_key = "humanCoreRecordKey" if field == "correspondenceReviewItems" else "predictionRecordKey"
        if entry.get("kind") != kind or entry.get("sourceUnitID") != record.get("sourceUnitID") or entry.get("operationalTargetID") != record.get("operationalTargetID") or entry.get(record_key) != record.get("key"):
            raise prior.ReviewPackageError("ledger entry does not exactly resolve to the bound source review record")
        if field == "correspondenceReviewItems":
            for name in ("researcherDisposition", "reviewedPredictionRecordKey", "optionalExplanatoryCode", "researcherNote"):
                item[name] = entry.get(name)
        else:
            for name in ("predictionSourceSupportJudgment", "optionalExplanatoryCode", "researcherNote"):
                item[name] = entry.get(name)
        if item.get(judgment_field) is None:
            raise prior.ReviewPackageError("ledger left a required researcher judgment unpopulated")
    _validate_materialized(materialized, ledger)
    return materialized


def _validate_materialized(package: dict[str, Any], ledger: dict[str, Any]) -> None:
    """Validate counts, exact selections, and one-to-one researcher decisions."""
    correspondence = instrument.items(package, "correspondenceReviewItems")
    support = instrument.items(package, "predictionSourceSupportReviewItems")
    node_correspondence = [item for item in correspondence if item["humanCoreRecord"]["kind"] == "node"]
    relation_correspondence = [item for item in correspondence if item["humanCoreRecord"]["kind"] == "relation"]
    node_support = [item for item in support if item["predictionRecord"]["kind"] == "node"]
    relation_support = [item for item in support if item["predictionRecord"]["kind"] == "relation"]
    if [len(node_correspondence), len(node_support), len(relation_correspondence), len(relation_support)] != [118, 109, 61, 68]:
        raise prior.ReviewPackageError("materialized review population differs from 118/109/61/68")
    expected = {
        "A": {"semantic_equivalent": 64, "target_or_class_disagreement": 7, "not_equivalent": 47},
        "B": {"supported_as_proposed": 103, "not_supported_as_proposed": 6, "insufficient_evidence_to_decide": 0},
        "C": {"semantic_equivalent": 33, "not_equivalent": 28},
        "D": {"supported_as_proposed": 66, "not_supported_as_proposed": 2, "insufficient_evidence_to_decide": 0},
    }
    observed = {
        "A": dict(Counter(item["researcherDisposition"] for item in node_correspondence)),
        "B": dict(Counter(item["predictionSourceSupportJudgment"] for item in node_support)),
        "C": dict(Counter(item["researcherDisposition"] for item in relation_correspondence)),
        "D": dict(Counter(item["predictionSourceSupportJudgment"] for item in relation_support)),
    }
    if any(
        {key: observed[pass_name].get(key, 0) for key in expected[pass_name]} != expected[pass_name]
        or any(key not in expected[pass_name] and value for key, value in observed[pass_name].items())
        for pass_name in expected
    ):
        raise prior.ReviewPackageError(f"materialized decision counts differ from the researcher ledger: observed={observed}")
    if Counter(item["optionalExplanatoryCode"] for item in relation_correspondence if item["researcherDisposition"] == "not_equivalent") != {"P1": 26, "P2": 2}:
        raise prior.ReviewPackageError("relation non-equivalence explanatory counts differ from P1=26/P2=2")
    if any(item[field] is None for collection, field in ((correspondence, "researcherDisposition"), (support, "predictionSourceSupportJudgment")) for item in collection):
        raise prior.ReviewPackageError("not all 356 researcher judgments are populated")
    instrument.validate_selections(package)
    selected_nodes = [item for item in node_correspondence if item["researcherDisposition"] == "semantic_equivalent"]
    selected_relations = [item for item in relation_correspondence if item["researcherDisposition"] == "semantic_equivalent"]
    predictions = package["predictionRecordsByKey"]
    for selected, expected_count in ((selected_nodes, 64), (selected_relations, 33)):
        keys = [item["reviewedPredictionRecordKey"] for item in selected]
        if len(keys) != expected_count or len(set(keys)) != expected_count or any(key not in predictions for key in keys):
            raise prior.ReviewPackageError("semantic-equivalent selected prediction keys are not exact and globally one-to-one")
        for item in selected:
            if not prior._same_structural_bucket(item["humanCoreRecord"], predictions[item["reviewedPredictionRecordKey"]]):
                raise prior.ReviewPackageError("semantic-equivalent selection violates same-unit/target/type eligibility")
    for item in selected_relations:
        selected_record = predictions[item["reviewedPredictionRecordKey"]]
        if set(item["humanCoreRecord"].get("endpointContext", {})) != {"source", "target"} or set(selected_record.get("endpointContext", {})) != {"source", "target"}:
            raise prior.ReviewPackageError("relation semantic-equivalent selection lacks reviewed endpoint context")
        if any(not item["humanCoreRecord"]["endpointContext"][role]["stableEndpointIdentity"] or not selected_record["endpointContext"][role]["stableEndpointIdentity"] for role in ("source", "target")):
            raise prior.ReviewPackageError("relation semantic-equivalent selection lacks exact endpoint identities")
    recovery_ineligible = [item for item in correspondence if item["researcherDisposition"] == "target_or_class_disagreement"]
    if any(item["researcherDisposition"] == "semantic_equivalent" for item in recovery_ineligible):
        raise prior.ReviewPackageError("target/class disagreement incorrectly entered semantic recovery")
    if ledger.get("validation", {}).get("readyForCodexMaterialization") is not True:
        raise prior.ReviewPackageError("ledger does not authorize materialization")


def _metrics(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compute only the four frozen secondary rates from validated decisions."""
    correspondence = instrument.items(package, "correspondenceReviewItems")
    support = instrument.items(package, "predictionSourceSupportReviewItems")
    groups = {
        "humanCoreNodeSemanticRecovery": ([item for item in correspondence if item["humanCoreRecord"]["kind"] == "node"], "researcherDisposition", "semantic_equivalent"),
        "humanCoreRelationSemanticRecovery": ([item for item in correspondence if item["humanCoreRecord"]["kind"] == "relation"], "researcherDisposition", "semantic_equivalent"),
        "correctedNodePredictionSourceSupportedRate": ([item for item in support if item["predictionRecord"]["kind"] == "node"], "predictionSourceSupportJudgment", "supported_as_proposed"),
        "correctedRelationPredictionSourceSupportedRate": ([item for item in support if item["predictionRecord"]["kind"] == "relation"], "predictionSourceSupportJudgment", "supported_as_proposed"),
    }
    return {name: {"numerator": sum(item[field] == positive for item in records), "denominator": len(records), "value": sum(item[field] == positive for item in records) / len(records)} for name, (records, field, positive) in groups.items()}


def build_reviewed_artifact() -> dict[str, Any]:
    """Materialize exact ledger decisions and compute validated secondary metrics."""
    ledger, source = _load_authorities()
    package = _validate_and_apply(ledger, source)
    metrics = _metrics(package)
    if {name: (value["numerator"], value["denominator"]) for name, value in metrics.items()} != {
        "humanCoreNodeSemanticRecovery": (64, 118), "humanCoreRelationSemanticRecovery": (33, 61),
        "correctedNodePredictionSourceSupportedRate": (103, 109), "correctedRelationPredictionSourceSupportedRate": (66, 68),
    }:
        raise prior.ReviewPackageError("computed secondary metrics differ from the frozen researcher-confirmed numerators")
    package.update({
        "artifactType": "publication_human_core_n5_corrected_evaluation_posthoc_semantic_equivalence_researcher_review",
        "artifactVersion": "1.0.0",
        "status": "RESEARCHER_REVIEW_COMPLETE / SECONDARY_METRICS_COMPUTED / STEP7C_PENDING",
        "sourceReviewPackage": {"path": str(SOURCE_PACKAGE.relative_to(prior.PROJECT_ROOT)), "sha256": SOURCE_PACKAGE_SHA256, "modified": False},
        "researcherJudgmentLedger": {"path": str(LEDGER.relative_to(prior.PROJECT_ROOT)), "sha256": LEDGER_SHA256, "modified": False},
        "secondaryMetrics": metrics,
        "providerModelCalls": 0,
        "step7CExecuted": False,
        "freezeOrClosureRecordCreated": False,
    })
    instrument.verify_historical_preservation()
    return package


def render_report(artifact: dict[str, Any]) -> str:
    """Render a concise status and metric record without adjudicating decisions."""
    lines = ["# Human Core N=5 Corrected Evaluation — Researcher-Confirmed Secondary Review", "", "Status: **RESEARCHER_REVIEW_COMPLETE / SECONDARY_METRICS_COMPUTED / STEP7C_PENDING**.", "", "The researcher judgment ledger was materialized by exact reviewItemID only. Strict Step 7B remains primary and unchanged; Step 7C was not executed.", "", "## Secondary metrics", ""]
    for name, value in artifact["secondaryMetrics"].items():
        lines.append(f"- {name}: {value['numerator']}/{value['denominator']} = {value['value']:.15f}")
    lines.extend(("", "All 356 ledger judgments were populated. No provider/model calls occurred.", ""))
    return "\n".join(lines)


def main() -> None:
    """Write the new reviewed artifact without overwriting source review material."""
    if OUTPUT.exists() or REPORT.exists():
        raise prior.ReviewPackageError("reviewed output already exists; refusing to overwrite researcher-reviewed material")
    artifact = build_reviewed_artifact()
    OUTPUT.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(artifact), encoding="utf-8")


if __name__ == "__main__":
    main()
