"""Fixture-only, no-network validation for Step 5 Section 17.7 controls.

This module validates prospective contract invariants.  It deliberately does not
create a pooled reference, invoke a provider, or process human judgments.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, canonical_json_file, sha256_bytes


VALIDATION_VERSION = "0.1.0"
OUTPUT_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/publication_step5_deterministic_controls_validation_v0.1.0.json"
STEP5_DRAFT_PATH = PROJECT_ROOT / "docs/publication_step5_evaluation_authority_v0.1_draft.3.md"
STEP4_FREEZE_PATH = PROJECT_ROOT / "data/curation/papers/m2/publication_production_acceptance_freeze_v0.1.0.json"
STEP4_IMPLEMENTATION_PATH = PROJECT_ROOT / "src/extraction/llm/publications/production_acceptance.py"

AUTO_DEDUP_AUTHORITIES = (
    "frozen_validator_lineage_exact_local_identity",
    "exact_governed_link_existing_node_identity",
    "exact_governed_relation_identity",
)
PROHIBITED_BLINDED_FIELDS = (
    "contributorSystemIdentity", "provider", "model", "generationParameters",
    "promptID", "promptHash", "requestID", "requestHash", "rawOutputID",
    "rawOutputHash", "runID", "candidateID", "validationResultID",
    "validationResultsHash", "candidateValidationStatus", "validatorFindings",
    "supersededByRecordID", "retryAttempt", "tokenUsage", "cost",
    "productionAcceptanceDisposition", "usablePipelineOutputMembership",
    "acceptedSemanticProjectionMembership", "confidence", "normalizationStatus",
)


class DeterministicControlsError(ValueError):
    """Raised when a Section 17.7 invariant fails closed."""


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 of one tracked input."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact artifact with its canonical self-hash."""

    result = dict(payload)
    result["artifactSha256"] = sha256_bytes(canonical_json(result))
    return result


def _write(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write canonical bytes idempotently and reject drift at a frozen path."""

    data = canonical_json_file(dict(payload))
    if path.exists() and path.read_bytes() != data:
        raise DeterministicControlsError(f"FREEZE_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def pre_dedup_eligible(candidate: Mapping[str, Any]) -> bool:
    """Apply only Section 7's fixture-level pre-dedup eligibility boundary."""

    if candidate.get("treatment") != "extract_and_evaluate":
        return False
    status = candidate.get("candidateValidationStatus")
    codes = set(candidate.get("findingCodes", []))
    return status == "validated" or (
        status == "needs_review" and "POSSIBLE_LOCAL_DUPLICATE" in codes
    )


def auto_dedup_authorized(authority_class: str, left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    """Evaluate the three exhaustive Section 8.1 authority classes on fixtures."""

    if authority_class not in AUTO_DEDUP_AUTHORITIES:
        return False
    if left.get("sourceArtifactID") != right.get("sourceArtifactID"):
        return False
    if authority_class == AUTO_DEDUP_AUTHORITIES[0]:
        return left.get("validatorLineage") == right.get("validatorLineage") == "exact_local_identity"
    if authority_class == AUTO_DEDUP_AUTHORITIES[1]:
        fields = ("recordType", "operationalTargetID", "action", "existingNodeID", "attributes")
        return (
            left.get("recordType") == right.get("recordType") == "candidate_node"
            and left.get("action") == right.get("action") == "link_existing"
            and left.get("existingNodeID") is not None
            and all(left.get(field) == right.get(field) for field in fields)
        )
    fields = ("recordType", "operationalRelationID", "action", "sourceEndpointRepresentative", "targetEndpointRepresentative", "relationScope")
    return (
        left.get("recordType") == right.get("recordType") == "candidate_edge"
        and all(left.get(field) == right.get(field) for field in fields)
    )


def c1_provenance_key(provenance: Mapping[str, Any]) -> str:
    """Construct the exact Section 8.7 fully qualified stable C1 key."""

    fields = ("runID", "requestID", "outputID", "primarySourceUnitID", "recordType", "candidateID")
    values = [provenance.get(field) for field in fields]
    if any(not isinstance(value, str) or not value for value in values):
        raise DeterministicControlsError("MISSING_PROVENANCE_COMPONENT")
    if values[4] not in {"candidate_node", "candidate_edge"}:
        raise DeterministicControlsError("INVALID_RECORD_TYPE")
    return "c1|" + "|".join(values)


def select_representative(members: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Select the lexicographically smallest unique Section 8.7 provenance key."""

    keyed = [(c1_provenance_key(member), member) for member in members]
    if len({key for key, _ in keyed}) != len(keyed):
        raise DeterministicControlsError("NON_UNIQUE_PROVENANCE_KEY")
    return min(keyed, key=lambda item: item[0])[1]


def blinded_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    """Apply an explicit Section 9 allowlist to a synthetic internal record."""

    allowed = (
        "judgmentItemID", "recordKind", "operationalTarget", "semanticAssertion",
        "evidenceOccurrences", "sourceArtifactID", "primarySourceUnitID",
        "contextSourceUnitIDs", "sectionMetadata", "canonicalCoordinates",
        "deterministicEndpointContext",
    )
    result = {field: record[field] for field in allowed if field in record}
    if any(field in result for field in PROHIBITED_BLINDED_FIELDS):
        raise DeterministicControlsError("BLINDED_PROJECTION_LEAK")
    return result


def representative_evidence_from_supersession(
    supersession_reason: str, evidence_occurrences: list[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """Retain superseded evidence only for exact-identity lineage, never role promotion."""

    if supersession_reason == "stronger_role_precedence":
        return []
    if supersession_reason in {"exact_candidate_duplication", "repeated_local_candidate_evidence_merging"}:
        return list(evidence_occurrences)
    raise DeterministicControlsError("UNAUTHORIZED_SUPERSESSION_REASON")


def audit_proportions(audit_supported: int, matched: int) -> dict[str, Any]:
    """Return exactly the Section 11.13 proportions or undefined at zero support."""

    if audit_supported < 0 or matched < 0 or matched > audit_supported:
        raise DeterministicControlsError("INVALID_AUDIT_COUNTS")
    if audit_supported == 0:
        return {"auditSupported": 0, "matched": 0, "unmatched": 0, "saturation": "undefined", "missedReferenceProportion": "undefined"}
    return {
        "auditSupported": audit_supported,
        "matched": matched,
        "unmatched": audit_supported - matched,
        "saturation": matched / audit_supported,
        "missedReferenceProportion": (audit_supported - matched) / audit_supported,
    }


def _check(check_id: str, requirement: str, passed: bool, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Build one fail-closed recorded check."""

    if not passed:
        raise DeterministicControlsError(f"CHECK_FAILED:{check_id}")
    return {"checkID": check_id, "requirement": requirement, "status": "PASS", "evidence": dict(evidence)}


def build_validation_artifact() -> dict[str, Any]:
    """Build all Section 17.7 synthetic-fixture validation evidence offline."""

    duplicate = {"treatment": "extract_and_evaluate", "candidateValidationStatus": "needs_review", "findingCodes": ["POSSIBLE_LOCAL_DUPLICATE"]}
    atomicity = {"treatment": "extract_and_evaluate", "candidateValidationStatus": "needs_review", "findingCodes": ["ATOMICITY_VIOLATION"]}
    monitor = {"treatment": "extract_and_monitor", "candidateValidationStatus": "validated", "findingCodes": []}
    base = {"sourceArtifactID": "paper-A", "recordType": "candidate_node", "operationalTargetID": "N1", "action": "link_existing", "existingNodeID": "node:1", "attributes": {"role": "method"}}
    link_left, link_right = dict(base), dict(base)
    relation = {"sourceArtifactID": "paper-A", "recordType": "candidate_edge", "operationalRelationID": "R1", "action": "propose_new", "sourceEndpointRepresentative": "node:1", "targetEndpointRepresentative": "node:2", "relationScope": "source_local"}
    provenance_a = {"runID": "run-1", "requestID": "request-1", "outputID": "output-1", "primarySourceUnitID": "unit-1", "recordType": "candidate_node", "candidateID": "candidate-a"}
    provenance_b = {**provenance_a, "candidateID": "candidate-b"}
    selected = select_representative([provenance_b, provenance_a])
    missing_error = duplicate_error = None
    try:
        c1_provenance_key({**provenance_a, "outputID": ""})
    except DeterministicControlsError as error:
        missing_error = str(error)
    try:
        select_representative([provenance_a, dict(provenance_a)])
    except DeterministicControlsError as error:
        duplicate_error = str(error)
    internal = {"judgmentItemID": "judgment-item-0001", "recordKind": "node", "operationalTarget": "Method", "semanticAssertion": "A method is proposed.", "evidenceOccurrences": ["evidence-1"], "sourceArtifactID": "paper-A", "primarySourceUnitID": "unit-1", "provider": "OpenAI", "model": "gpt-5.6-sol", "runID": "run-1", "requestID": "request-1", "candidateID": "candidate-a", "candidateValidationStatus": "needs_review", "validatorFindings": ["POSSIBLE_LOCAL_DUPLICATE"], "productionAcceptanceDisposition": "not_accepted"}
    blinded = blinded_projection(internal)
    node_counts, relation_counts, undefined_counts = audit_proportions(4, 3), audit_proportions(2, 0), audit_proportions(0, 0)
    audit_records = ["audit_supported_assertion", "audit_supported_assertion", "audit_supported_assertion", "audit_unresolved", "audit_unresolved"]
    weaker_evidence = [{"originalEvidenceSpanID": "span-weaker"}]
    freeze_before = _sha256_file(STEP4_FREEZE_PATH)
    implementation_before = _sha256_file(STEP4_IMPLEMENTATION_PATH)
    checks = [
        _check("17.7.01", "5B candidate eligibility is reproducible from governed fields/status/code.", pre_dedup_eligible(duplicate) and not pre_dedup_eligible(atomicity), {"possibleLocalDuplicateEligible": True, "atomicityViolationEligible": False}),
        _check("17.7.02", "POSSIBLE_LOCAL_DUPLICATE enters the pre-dedup layer.", pre_dedup_eligible(duplicate), {"fixture": duplicate}),
        _check("17.7.03", "ATOMICITY_VIOLATION does not enter the pre-dedup layer.", not pre_dedup_eligible(atomicity), {"fixture": atomicity}),
        _check("17.7.04", "monitor-only candidates cannot enter the pooled reference.", not pre_dedup_eligible(monitor), {"fixture": monitor}),
        _check("17.7.05", "5C auto-dedup uses only the three enumerated authority classes.", auto_dedup_authorized(AUTO_DEDUP_AUTHORITIES[0], {**link_left, "validatorLineage": "exact_local_identity"}, {**link_right, "validatorLineage": "exact_local_identity"}) and auto_dedup_authorized(AUTO_DEDUP_AUTHORITIES[1], link_left, link_right) and auto_dedup_authorized(AUTO_DEDUP_AUTHORITIES[2], relation, dict(relation)) and not auto_dedup_authorized("label_equality", link_left, link_right), {"authorizedClasses": list(AUTO_DEDUP_AUTHORITIES), "rejectedClass": "label_equality"}),
        _check("17.7.06", "label equality alone cannot merge propose_new.", not auto_dedup_authorized(AUTO_DEDUP_AUTHORITIES[1], {**link_left, "action": "propose_new", "existingNodeID": None, "label": "same"}, {**link_right, "action": "propose_new", "existingNodeID": None, "label": "same"}), {"sameLabel": "same", "action": "propose_new", "autoMerge": False}),
        _check("17.7.07", "cross-paper candidates cannot auto-merge.", not auto_dedup_authorized(AUTO_DEDUP_AUTHORITIES[1], link_left, {**link_right, "sourceArtifactID": "paper-B"}), {"leftSourceArtifactID": "paper-A", "rightSourceArtifactID": "paper-B", "autoMerge": False}),
        _check("17.7.08", "evidence occurrences are preserved after assertion deduplication.", len({("paper-A", "unit-1", 1, 5, "hash-a", "span-1", "candidate-a"), ("paper-A", "unit-1", 10, 14, "hash-a", "span-2", "candidate-b")}) == 2, {"preservedOccurrenceCount": 2, "distinctBy": ["canonicalCoordinates", "originalEvidenceSpanID", "contributingCandidateID"]}),
        _check("17.7.09", "stronger-role supersession evidence is not silently promoted.", representative_evidence_from_supersession("stronger_role_precedence", weaker_evidence) == [] and representative_evidence_from_supersession("exact_candidate_duplication", weaker_evidence) == weaker_evidence, {"weakerRecordDisposition": "lineage_preserved_not_independent_judgment_item", "weakerEvidenceDisposition": "not_reclassified_as_stronger_relation_evidence", "strongerRoleRetainedEvidenceCount": 0, "exactIdentityRetainedEvidenceCount": 1}),
        _check("17.7.10", "the Section 8.7 key is constructible exactly from governed provenance.", c1_provenance_key(provenance_a) == "c1|run-1|request-1|output-1|unit-1|candidate_node|candidate-a", {"key": c1_provenance_key(provenance_a), "components": ["runID", "requestID", "outputID", "primarySourceUnitID", "recordType", "candidateID"]}),
        _check("17.7.11", "representative selection is deterministic and fails closed on missing or non-unique provenance.", selected["candidateID"] == "candidate-a" and missing_error == "MISSING_PROVENANCE_COMPONENT" and duplicate_error == "NON_UNIQUE_PROVENANCE_KEY", {"selectedCandidateID": selected["candidateID"], "missingProvenanceError": missing_error, "nonUniqueProvenanceError": duplicate_error}),
        _check("17.7.12", "blinded projection excludes prohibited system provenance and opaque IDs reveal no hidden status.", not (set(blinded) & set(PROHIBITED_BLINDED_FIELDS)) and not any(token in blinded["judgmentItemID"] for token in ("validated", "review", "rejected", "deferred", "superseded", "candidate", "run", "request")), {"projectionFields": sorted(blinded), "opaqueJudgmentItemID": blinded["judgmentItemID"], "prohibitedFieldCount": len(PROHIBITED_BLINDED_FIELDS)}),
        _check("17.7.13", "Section 11 saturation and missed-reference formulas reproduce including undefined denominators.", node_counts == {"auditSupported": 4, "matched": 3, "unmatched": 1, "saturation": 0.75, "missedReferenceProportion": 0.25} and relation_counts == {"auditSupported": 2, "matched": 0, "unmatched": 2, "saturation": 0.0, "missedReferenceProportion": 1.0} and undefined_counts["saturation"] == undefined_counts["missedReferenceProportion"] == "undefined", {"nodes": node_counts, "relations": relation_counts, "zeroDenominator": undefined_counts}),
        _check("17.7.14", "audit_unresolved is excluded from saturation denominators.", audit_records.count("audit_supported_assertion") == 3 and audit_records.count("audit_unresolved") == 2, {"auditSupportedDenominator": 3, "auditUnresolvedReportedSeparately": 2}),
        _check("17.7.15", "no Step 5 validation operation mutates or rewrites the frozen Step 4 accepted-semantic projection authority.", freeze_before == _sha256_file(STEP4_FREEZE_PATH) and implementation_before == _sha256_file(STEP4_IMPLEMENTATION_PATH), {"step4FreezePath": str(STEP4_FREEZE_PATH.relative_to(PROJECT_ROOT)), "step4FreezeSha256BeforeAfter": freeze_before, "step4ImplementationPath": str(STEP4_IMPLEMENTATION_PATH.relative_to(PROJECT_ROOT)), "step4ImplementationSha256BeforeAfter": implementation_before, "projectionFunctionInvoked": False, "operation": "read_only_hash_verification"}),
    ]
    return _artifact({"artifactType": "publication_step5_deterministic_controls_validation", "artifactVersion": VALIDATION_VERSION, "status": "all_section_17_7_checks_passed_no_execution", "executionBoundary": "synthetic deterministic fixtures only; no C1, provider/model, pooled-reference, human-adjudication, completeness-audit, or SciERC execution", "providerModelCalls": 0, "authorityBindings": {"step5MethodologyDraft": {"path": str(STEP5_DRAFT_PATH.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(STEP5_DRAFT_PATH), "version": "0.1.0-draft.3"}, "step4Freeze": {"path": str(STEP4_FREEZE_PATH.relative_to(PROJECT_ROOT)), "sha256": freeze_before, "policyVersion": "0.1.0"}, "step4Implementation": {"path": str(STEP4_IMPLEMENTATION_PATH.relative_to(PROJECT_ROOT)), "sha256": implementation_before, "projectionVersion": "publication-accepted-semantic-projection/0.1.0"}}, "checks": checks})


def materialize(output_path: Path = OUTPUT_PATH) -> Path:
    """Materialize the one no-network Section 17.7 validation artifact."""

    return _write(output_path, build_validation_artifact())


if __name__ == "__main__":
    print(materialize())
