"""Materialize the bounded Step 8 internal pre-review candidate pool.

This module is deliberately read-only with respect to the authentic execution
namespace.  It consumes only the six frozen ``step5_n6`` selected attempts and
does not create a reviewer projection, a reference, or any human judgment.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


VERSION = "1.0.0"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2/publication_step8_internal_candidate_pool"
POOL_NAME = "publication_step8_internal_pre_review_candidate_pool_v1.0.0.json"
SUMMARY_NAME = "publication_step8_internal_pre_review_candidate_pool_summary_v1.0.0.json"
REALIZATION = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json"
PREDICTIONS = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_canonical_predictions_v1.0.0.jsonl"
LIFECYCLE = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_lifecycle_ledger_v1.0.0.jsonl"
INDEX = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_result_index_v1.0.0.jsonl"
ENVELOPES = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.2.json"
AUTHORITY_FREEZE = PROJECT_ROOT / "data/curation/papers/m2/publication_step5_evaluation_authority_freeze_v0.1.3.json"
TARGETS = PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml"
EXECUTION_ROOT = PROJECT_ROOT / "var/publication_pilot1_evaluation_execution"

EXPECTED = {
    "realization": "6707e288e0333155ea53aca42edf3fa0063e287019e82cf4c63c922eec3f9345",
    "predictions": "e888c4c4c68ede19cb4c65275b96637fd183e64f887d9a649f70e57f98eadb86",
    "lifecycle": "8bc201fc687005b6543ad9d89b5a5c8a500e96d361705dc5aa07ffc93b58bb01",
    "index": "6d9e8ae7d6c513ca0e3a543f176d78eefda8166c5530856141e8fcd806870fac",
    "envelopes": "05262e9abce80feac5c6b78c641e60e1392953157a1cc47231e455808867eba4",
}
EXPECTED_ARTIFACT_HASHES = {"realization": "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842", "envelopes": "ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce"}
EXPECTED_AUTHORITY_FREEZE_SHA256 = "798adb18b0429f5c985a844b62d9f9db4048b98436d306db31769cf2f71da94e"


class Step8CandidatePoolError(ValueError):
    """Raised when a frozen binding or authentic candidate lineage drifts."""


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise Step8CandidatePoolError(f"REQUIRED_ARTIFACT_ABSENT:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Step8CandidatePoolError(f"REQUIRED_ARTIFACT_NOT_OBJECT:{path}")
    return value


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Step8CandidatePoolError(f"REQUIRED_ARTIFACT_ABSENT:{path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    data = canonical_json(dict(payload)) + b"\n"
    if path.exists() and path.read_bytes() != data:
        raise Step8CandidatePoolError(f"OUTPUT_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _treatments(target_path: Path) -> dict[str, str]:
    payload = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Step8CandidatePoolError("TARGET_INVENTORY_NOT_OBJECT")
    records = list(payload.get("node_targets", [])) + list(payload.get("relation_targets", []))
    result = {row["operational_id"]: row["pilot_treatment"] for row in records if isinstance(row, dict)}
    if not result:
        raise Step8CandidatePoolError("TARGET_INVENTORY_EMPTY")
    return result


def eligibility_disposition(record: Mapping[str, Any], validation: Mapping[str, Any], treatment: str | None) -> tuple[str, str]:
    """Return the frozen pre-review eligibility disposition without acceptance input."""

    if treatment != "extract_and_evaluate":
        return "excluded", "not_routed_extract_and_evaluate"
    status = validation.get("candidateValidationStatus")
    codes = {str(item.get("code")) for item in validation.get("findings", []) if isinstance(item, Mapping)}
    if status == "superseded":
        return "excluded", "superseded"
    if status == "validated":
        return "eligible", "validated"
    if status == "needs_review" and codes == {"POSSIBLE_LOCAL_DUPLICATE"}:
        return "eligible", "possible_local_duplicate"
    if status == "needs_review" and "ATOMICITY_VIOLATION" in codes:
        return "excluded", "atomicity_violation"
    if status == "rejected":
        return "excluded", "rejected"
    if record.get("deferredRecordID"):
        return "excluded", "unresolved_deferred"
    return "excluded", "ineligible_lifecycle"


def _exact_key(member: Mapping[str, Any]) -> tuple[Any, ...] | None:
    """Return only an explicitly authorized exact auto-deduplication key."""

    candidate = member["candidate"]
    if member["recordKind"] == "candidate_node" and candidate.get("action") == "link_existing":
        return ("link_existing", member["sourceArtifactID"], candidate.get("operationalTargetID"), candidate.get("existingNodeID"), canonical_json(candidate.get("attributes", [])))
    # Authority A is represented only by explicit frozen validator lineage.  Current
    # selected records carry no such exact-identity marker, so no inferred key exists.
    return None


def deduplicate(members: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply only exact source-local Authority B collapse; retain uncertainty groups."""

    keyed: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    singles: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for member in members:
        if member["eligibilityReason"] == "possible_local_duplicate":
            singles.append(member)
            groups.append({"memberCandidateKeys": [member["candidateKey"]]})
            continue
        key = _exact_key(member)
        (singles if key is None else keyed[key]).append(member)
    retained = list(singles)
    for key, values in sorted(keyed.items(), key=lambda item: repr(item[0])):
        values.sort(key=lambda item: item["candidateKey"])
        representative = dict(values[0])
        representative["deduplicationDisposition"] = "collapsed_exact_governed_link_existing" if len(values) > 1 else "retained_no_auto_deduplication"
        representative["memberCandidateKeys"] = [item["candidateKey"] for item in values]
        representative["evidenceOccurrences"] = [occurrence for item in values for occurrence in item["evidenceOccurrences"]]
        retained.append(representative)
    for item in retained:
        item.setdefault("deduplicationDisposition", "retained_no_auto_deduplication")
        item.setdefault("memberCandidateKeys", [item["candidateKey"]])
    # Group only candidates whose validator lineage actually says POSSIBLE_LOCAL_DUPLICATE.
    possible = [item for item in members if item["eligibilityReason"] == "possible_local_duplicate"]
    if possible:
        groups = [{"duplicateReviewGroupID": "duplicate-review-group-0001", "memberCandidateKeys": sorted(item["candidateKey"] for item in possible), "basis": "frozen_validator_lineage_possible_local_duplicate"}]
    return sorted(retained, key=lambda item: item["candidateKey"]), groups


def build(source_root: Path = EXECUTION_ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read, bind, and deterministically construct the internal non-blinded pool."""

    for name, path in (("realization", REALIZATION), ("predictions", PREDICTIONS), ("lifecycle", LIFECYCLE), ("index", INDEX), ("envelopes", ENVELOPES)):
        if _hash(path) != EXPECTED[name]:
            raise Step8CandidatePoolError(f"FROZEN_BINDING_HASH_DRIFT:{name}")
    if _hash(AUTHORITY_FREEZE) != EXPECTED_AUTHORITY_FREEZE_SHA256:
        raise Step8CandidatePoolError("FROZEN_BINDING_HASH_DRIFT:authority_freeze")
    authority_freeze, realization, envelopes = _load(AUTHORITY_FREEZE), _load(REALIZATION), _load(ENVELOPES)
    selected_binding = authority_freeze.get("frozenBindings", {}).get("selectedProcessableStep5N6Realization", {})
    if selected_binding.get("realizationArtifactSha256") != EXPECTED_ARTIFACT_HASHES["realization"] or selected_binding.get("selectedProcessableAttemptCount") != 6:
        raise Step8CandidatePoolError("AUTHORITY_SELECTED_ATTEMPT_BINDING_DRIFT")
    if realization.get("artifactSha256") != EXPECTED_ARTIFACT_HASHES["realization"] or envelopes.get("artifactSha256") != EXPECTED_ARTIFACT_HASHES["envelopes"]:
        raise Step8CandidatePoolError("FROZEN_BINDING_SELF_HASH_DRIFT")
    indexes = [row for row in _rows(INDEX) if row.get("executionCohort") == "step5_n6"]
    lifecycles = {row["requestID"]: row for row in _rows(LIFECYCLE) if row.get("executionCohort") == "step5_n6"}
    predictions = {row["requestID"]: row for row in _rows(PREDICTIONS) if row.get("executionCohort") == "step5_n6"}
    selected_units = [row["primarySourceUnitID"] for row in envelopes["envelopes"]]
    envelope_by_unit = {row["primarySourceUnitID"]: row for row in envelopes["envelopes"]}
    if len(indexes) != 6 or set(selected_units) != {row.get("primarySourceUnitID") for row in indexes} or len(lifecycles) != 6 or len(predictions) != 6:
        raise Step8CandidatePoolError("STEP5_N6_SELECTED_ATTEMPT_BINDING_DRIFT")
    treatments = _treatments(TARGETS)
    all_members: list[dict[str, Any]] = []
    for index in sorted(indexes, key=lambda row: row["primarySourceUnitID"]):
        request_id = index["requestID"]
        lifecycle, prediction = lifecycles.get(request_id), predictions.get(request_id)
        if lifecycle is None or prediction is None or lifecycle.get("selectedAttemptNumber") != index.get("selectedAttemptNumber") or index.get("selectedAttemptNumber") != 1:
            raise Step8CandidatePoolError(f"SELECTED_ATTEMPT_LINEAGE_DRIFT:{request_id}")
        root = source_root / "requests" / request_id / "attempt-01"
        required = {name: root / name for name in ("raw_model_output.json", "provider_response.json", "parser_result.json", "parsed_candidate.json", "validation_results.json", "lifecycle.json")}
        if any(not path.is_file() for path in required.values()):
            raise Step8CandidatePoolError(f"SELECTED_ATTEMPT_PROVENANCE_ABSENT:{request_id}")
        if _hash(required["raw_model_output.json"]) != index.get("rawOutputSha256") or sha256_bytes(canonical_json(_load(required["provider_response.json"]))) != index.get("providerResponseSha256"):
            raise Step8CandidatePoolError(f"SELECTED_PROVIDER_RAW_DRIFT:{request_id}")
        parser, parsed, validation, attempt = (_load(required["parser_result.json"]), _load(required["parsed_candidate.json"]), _load(required["validation_results.json"]), _load(required["lifecycle.json"]))
        if attempt.get("parserResult") != parser or attempt.get("validation") != validation or parser.get("parseStatus") != "parsed" or validation.get("validationResultsHash") != prediction["acceptedSemanticProjection"].get("validationResultsHash"):
            raise Step8CandidatePoolError(f"PARSER_VALIDATION_LINEAGE_DRIFT:{request_id}")
        envelope = envelope_by_unit[index["primarySourceUnitID"]]
        if parsed.get("metadata", {}).get("primarySourceUnitID") != index["primarySourceUnitID"] or index.get("contextSourceUnitIDs") != envelope.get("contextSourceUnitIDs"):
            raise Step8CandidatePoolError(f"ENVELOPE_SOURCE_SCOPE_DRIFT:{request_id}")
        evidence = {row["evidenceSpanID"]: row for row in parsed.get("evidenceSpans", [])}
        validation_by_id = {row["recordID"]: row for row in validation.get("recordResults", [])}
        for kind, records in (("candidate_node", parsed.get("candidateNodes", [])), ("candidate_edge", parsed.get("candidateEdges", []))):
            for candidate in records:
                candidate_id = candidate.get("candidateID")
                record_validation = validation_by_id.get(candidate_id)
                if not isinstance(record_validation, dict):
                    raise Step8CandidatePoolError(f"VALIDATION_RECORD_ABSENT:{request_id}:{candidate_id}")
                target_id = candidate.get("operationalTargetID") if kind == "candidate_node" else candidate.get("operationalRelationID")
                disposition, reason = eligibility_disposition(candidate, record_validation, treatments.get(target_id))
                occurrences = []
                for evidence_id in candidate.get("evidenceSpanIDs", []):
                    if evidence_id not in evidence:
                        raise Step8CandidatePoolError(f"EVIDENCE_OCCURRENCE_ABSENT:{request_id}:{candidate_id}:{evidence_id}")
                    occurrences.append({"evidenceSpanID": evidence_id, **evidence[evidence_id]})
                all_members.append({
                    "candidateKey": f"{request_id}|{kind}|{candidate_id}", "requestID": request_id,
                    "primarySourceUnitID": index["primarySourceUnitID"], "sourceArtifactID": parsed["metadata"]["sourceArtifactID"],
                    "recordKind": kind, "candidate": candidate, "validationLineage": record_validation,
                    "providerRawSha256": index["rawOutputSha256"], "providerResponseSha256": index["providerResponseSha256"],
                    "parserStatus": parser["parseStatus"], "selectedAttemptNumber": 1,
                    "eligibilityDisposition": disposition, "eligibilityReason": reason, "evidenceOccurrences": occurrences,
                })
    eligible = [member for member in all_members if member["eligibilityDisposition"] == "eligible"]
    retained, duplicate_groups = deduplicate(eligible)
    pool = {"artifactType": "publication_step8_internal_pre_review_candidate_pool", "artifactVersion": VERSION,
            "executionBoundary": "internal_pre_review_only_no_blinded_package_no_human_judgments_no_positive_reference", "source": {"realization": str(REALIZATION.relative_to(PROJECT_ROOT)), "realizationSha256": EXPECTED_ARTIFACT_HASHES["realization"], "selectedExecutionCohort": "step5_n6", "selectedAttemptCount": 6},
            "candidates": all_members, "retainedPooledItems": retained, "unresolvedDuplicateReviewGroups": duplicate_groups}
    pool["artifactSha256"] = sha256_bytes(canonical_json(pool))
    summary = {"artifactType": "publication_step8_internal_pre_review_candidate_pool_summary", "artifactVersion": VERSION,
               "sourcePoolSha256": pool["artifactSha256"],
               "counts": {"byPrimaryUnit": dict(sorted(Counter(item["primarySourceUnitID"] for item in all_members).items())), "byRecordKind": dict(sorted(Counter(item["recordKind"] for item in all_members).items())), "byEligibilityDispositionReason": dict(sorted(Counter(f"{item['eligibilityDisposition']}:{item['eligibilityReason']}" for item in all_members).items())), "excludedCandidates": len(all_members) - len(eligible), "exclusionReasons": dict(sorted(Counter(item["eligibilityReason"] for item in all_members if item["eligibilityDisposition"] == "excluded").items())), "byAutomaticDeduplicationDisposition": dict(sorted(Counter(item["deduplicationDisposition"] for item in retained).items())), "preDedupEligible": len(eligible), "retainedPooledItems": len(retained), "unresolvedDuplicateReviewGroups": len(duplicate_groups)}}
    summary["artifactSha256"] = sha256_bytes(canonical_json(summary))
    return pool, summary


def materialize(source_root: Path = EXECUTION_ROOT, output_root: Path = OUTPUT_ROOT) -> dict[str, Path]:
    """Materialize deterministic internal artifacts without touching upstream inputs."""

    pool, summary = build(source_root)
    paths = {"pool": output_root / POOL_NAME, "summary": output_root / SUMMARY_NAME}
    _write_immutable(paths["pool"], pool); _write_immutable(paths["summary"], summary)
    return paths
