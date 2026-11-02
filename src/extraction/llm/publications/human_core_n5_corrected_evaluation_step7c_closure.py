"""Freeze and close corrected Human Core N=5 Step 7 deterministically."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import human_core_n5_corrected_evaluation_researcher_review as review
from .human_core_n5_evaluation import load_frozen_inputs


ROOT = review.prior.GOLD_ROOT
STRICT = review.instrument.STRICT_JSON
STRICT_SHA256 = review.instrument.STRICT_JSON_SHA256
REVIEWED = review.OUTPUT
REVIEWED_SHA256 = "ef28c77f05b5647c5f15a963902d3b6188946f40675dbce7f2db2584edc2d2af"
REALIZATION_FREEZE = review.prior.PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json"
OUTPUT = ROOT / "publication_human_core_n5_corrected_evaluation_step7c_closure_v1.0.0.json"
REPORT = OUTPUT.with_suffix(".md")


def _sha256(path: Path) -> str:
    """Return the exact SHA-256 of a required authority."""
    return review._sha256(path)


def _load(path: Path) -> dict[str, Any]:
    """Load one JSON object authority."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise review.prior.ReviewPackageError(f"closure authority is not an object: {path}")
    return value


def build_closure() -> dict[str, Any]:
    """Validate all frozen inputs and return the minimal Step 7C closure record."""
    inputs = load_frozen_inputs()
    review.instrument.verify_historical_preservation()
    if _sha256(STRICT) != STRICT_SHA256 or _sha256(REVIEWED) != REVIEWED_SHA256:
        raise review.prior.ReviewPackageError("strict or reviewed Step 7 input differs from its frozen SHA-256")
    strict, reviewed = _load(STRICT), _load(REVIEWED)
    if (
        strict.get("status") != "PRE_FREEZE"
        or strict.get("providerModelCalls") != 0
        or strict.get("step7CExecuted") is not False
        or strict.get("freezeOrClosureRecordCreated") is not False
    ):
        raise review.prior.ReviewPackageError("strict Step 7B is not an unchanged PRE-FREEZE authority")
    if (
        reviewed.get("status") != "RESEARCHER_REVIEW_COMPLETE / SECONDARY_METRICS_COMPUTED / STEP7C_PENDING"
        or reviewed.get("providerModelCalls") != 0
        or reviewed.get("step7CExecuted") is not False
        or reviewed.get("freezeOrClosureRecordCreated") is not False
        or reviewed.get("sourceReviewPackage", {}).get("sha256") != review.SOURCE_PACKAGE_SHA256
        or reviewed.get("researcherJudgmentLedger", {}).get("sha256") != review.LEDGER_SHA256
    ):
        raise review.prior.ReviewPackageError("completed secondary review is not an unchanged Step 7C input")
    metrics = reviewed.get("secondaryMetrics")
    expected_metrics = {
        "humanCoreNodeSemanticRecovery": (64, 118),
        "humanCoreRelationSemanticRecovery": (33, 61),
        "correctedNodePredictionSourceSupportedRate": (103, 109),
        "correctedRelationPredictionSourceSupportedRate": (66, 68),
    }
    if not isinstance(metrics, dict) or any(
        metrics.get(name, {}).get("numerator") != numerator or metrics.get(name, {}).get("denominator") != denominator
        for name, (numerator, denominator) in expected_metrics.items()
    ):
        raise review.prior.ReviewPackageError("completed secondary review metrics differ from their frozen values")
    realization = _load(REALIZATION_FREEZE)
    strict_inputs = strict.get("frozenInputs", {})
    if (
        strict_inputs != inputs.provenance
        or strict_inputs.get("canonicalPredictions", {}).get("sha256") != review.instrument.STRICT_PREDICTIONS_SHA256
        or strict_inputs.get("matchingContractSHA256") != _sha256(review.prior.PROJECT_ROOT / strict_inputs.get("matchingContract", ""))
        or realization.get("artifactSha256") != strict_inputs.get("realizationFreeze", {}).get("artifactSha256")
    ):
        raise review.prior.ReviewPackageError("corrected N=5 evaluation view or realization authority mismatch")
    return {
        "artifactType": "publication_human_core_n5_corrected_evaluation_step7c_closure",
        "artifactVersion": "1.0.0",
        "status": "FROZEN_CLOSED",
        "scope": "deterministic Step 7C freeze and closure of corrected Human Core N=5 evaluation; strict Step 7B remains primary and secondary reviewed metrics remain secondary",
        "frozenInputs": {
            "humanCoreEvaluationView": {"mode": "read_only_non_destructive_primary_v014_plus_supplemental_v015", "compositeReferenceProjection": {"path": "data/curation/papers/m2/human_core_gold/publication_human_core_v0.1.5_composite_reference_projection.json", "sha256": _sha256(ROOT / "publication_human_core_v0.1.5_composite_reference_projection.json")}, "scoringAuthority": strict_inputs},
            "correctedEvaluationRealization": {"path": str(REALIZATION_FREEZE.relative_to(review.prior.PROJECT_ROOT)), "fileSha256": _sha256(REALIZATION_FREEZE), "artifactSha256": realization["artifactSha256"], "canonicalPredictions": strict_inputs["canonicalPredictions"]},
            "strictStep7B": {"path": str(STRICT.relative_to(review.prior.PROJECT_ROOT)), "sha256": STRICT_SHA256, "primary": True},
            "completedSecondaryReview": {"path": str(REVIEWED.relative_to(review.prior.PROJECT_ROOT)), "sha256": REVIEWED_SHA256, "secondary": True},
            "matchingContract": {"path": strict_inputs["matchingContract"], "sha256": strict_inputs["matchingContractSHA256"]},
        },
        "secondaryMetricSummary": {name: {"numerator": numerator, "denominator": denominator} for name, (numerator, denominator) in expected_metrics.items()},
        "providerModelCalls": 0,
        "step7CExecuted": True,
        "step8Executed": False,
        "freezeOrClosureRecordCreated": True,
        "preservation": {"strictStep7BModified": False, "secondaryReviewModified": False, "humanCoreModified": False, "correctedPredictionsModified": False, "matchingContractModified": False, "historicalC1ArtifactsModified": False},
        "nextAuthorizedMilestone": "Step 8",
    }


def render_report(closure: dict[str, Any]) -> str:
    """Render a concise closure record without duplicating detailed metrics."""
    lines = ["# Corrected Human Core N=5 Step 7C Closure", "", "Status: **FROZEN/CLOSED**.", "", "This deterministic closure binds the corrected N=5 realization, Human Core evaluation view, strict Step 7B primary result, frozen matching contract, and completed secondary review. Detailed results remain in their bound artifacts.", "", "Strict Step 7B remains primary; researcher-reviewed metrics remain secondary. No provider/model calls occurred. Step 8 was not executed.", ""]
    return "\n".join(lines)


def main() -> None:
    """Materialize the immutable Step 7C closure once."""
    if OUTPUT.exists() or REPORT.exists():
        raise review.prior.ReviewPackageError("Step 7C closure output already exists")
    closure = build_closure()
    OUTPUT.write_text(json.dumps(closure, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(render_report(closure), encoding="utf-8")


if __name__ == "__main__":
    main()
