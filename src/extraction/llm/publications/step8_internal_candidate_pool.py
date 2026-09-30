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


VERSION = "1.0.1"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2/publication_step8_internal_candidate_pool"
POOL_NAME = "publication_step8_internal_pre_review_candidate_pool_v1.0.1.json"
SUMMARY_NAME = "publication_step8_internal_pre_review_candidate_pool_summary_v1.0.1.json"
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


def _lineage_target(member: Mapping[str, Any], codes: set[str]) -> str | None:
    """Read an exact paired record ID from frozen V10 findings only."""

    lineage = member["validationLineage"]
    matches = [finding for finding in lineage.get("findings", [])
               if finding.get("stage") == "V10" and finding.get("code") in codes]
    if not matches:
        return None
    targets = {finding.get("expected") for finding in matches}
    if len(targets) != 1 or not isinstance(next(iter(targets)), str):
        raise Step8CandidatePoolError("INVALID_VALIDATOR_DUPLICATE_LINEAGE")
    target = next(iter(targets))
    if lineage.get("supersededByRecordID") not in (None, target):
        raise Step8CandidatePoolError("CONFLICTING_VALIDATOR_DUPLICATE_LINEAGE")
    return target


def _merge(values: Sequence[dict[str, Any]], reason: str) -> dict[str, Any]:
    """Retain one authentic representative and every original evidence membership."""

    ordered = sorted(values, key=lambda item: item["candidateKey"])
    representative = dict(ordered[0])
    representative["deduplicationDisposition"] = reason if len(ordered) > 1 else "retained_no_auto_deduplication"
    representative["memberCandidateKeys"] = [item["candidateKey"] for item in ordered]
    representative["memberValidationLineage"] = {item["candidateKey"]: item["validationLineage"] for item in ordered}
    representative["normalizationUsedForIdentity"] = False
    representative["evidenceOccurrences"] = [
        {**occurrence, "contributingCandidateKey": item["candidateKey"]}
        for item in ordered for occurrence in item["evidenceOccurrences"]
    ]
    return representative


def deduplicate(members: Sequence[dict[str, Any]], excluded: Sequence[dict[str, Any]] = ()) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply only validator identity, exact linked nodes, and exact relations."""

    by_key = {item["candidateKey"]: item for item in (*members, *excluded)}
    if len(by_key) != len(members) + len(excluded):
        raise Step8CandidatePoolError("NON_UNIQUE_CANDIDATE_KEY")
    parent = {item["candidateKey"]: item["candidateKey"] for item in members}

    def root(key: str) -> str:
        while parent[key] != key:
            key = parent[key]
        return key

    def join(left: str, right: str) -> None:
        parent[root(right)] = root(left)

    def paired_key(item: Mapping[str, Any], target_id: str) -> str:
        key = f"{item['requestID']}|{item['recordKind']}|{target_id}"
        target = by_key.get(key)
        if target is None or target["sourceArtifactID"] != item["sourceArtifactID"]:
            raise Step8CandidatePoolError("VALIDATOR_DUPLICATE_TARGET_DRIFT")
        return key

    # A: a frozen V10 exact-identity finding, never a reconstructed similarity key.
    attached: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in (*members, *excluded):
        target_id = _lineage_target(item, {"EXACT_DUPLICATE_NODE", "EXACT_DUPLICATE_EDGE", "REPEATED_LOCAL_CANDIDATE_EVIDENCE_MERGED"})
        if target_id is None:
            continue
        target_key = paired_key(item, target_id)
        if item["eligibilityDisposition"] == "eligible" and target_key in parent:
            join(target_key, item["candidateKey"])
        elif item["eligibilityReason"] == "superseded" and target_key in parent:
            attached[target_key].append(item)

    # B: the exact governed existing-node ID and all material node fields.
    linked: dict[tuple[Any, ...], str] = {}
    for item in members:
        candidate = item["candidate"]
        if item["recordKind"] != "candidate_node" or item["eligibilityReason"] == "possible_local_duplicate" or candidate.get("action") != "link_existing":
            continue
        existing = candidate.get("existingNodeID")
        if not isinstance(existing, str) or not existing:
            continue
        key = (item["sourceArtifactID"], candidate.get("operationalTargetID"), existing,
               canonical_json({field: value for field, value in candidate.items()
                               if field not in {"candidateID", "evidenceSpanIDs", "label", "normalizedLabelProposal", "deferredRecordID"}}))
        if key in linked:
            join(linked[key], item["candidateKey"])
        else:
            linked[key] = item["candidateKey"]

    node_map = {item["candidateKey"]: root(item["candidateKey"]) for item in members if item["recordKind"] == "candidate_node"}

    def endpoint(item: Mapping[str, Any], value: Mapping[str, Any]) -> tuple[Any, ...]:
        reference = value.get("referenceID")
        if value.get("referenceType") != "candidate_node":
            return (value.get("referenceType"), value.get("artifactID"), reference)
        key = f"{item['requestID']}|candidate_node|{reference}"
        return ("candidate_node", node_map.get(key, key))

    # C: exact relation material fields after the A/B node representative map.
    relations: dict[tuple[Any, ...], str] = {}
    for item in members:
        candidate = item["candidate"]
        if item["recordKind"] != "candidate_edge" or item["eligibilityReason"] == "possible_local_duplicate":
            continue
        if not isinstance(candidate.get("source"), Mapping) or not isinstance(candidate.get("target"), Mapping):
            continue
        material = {field: value for field, value in candidate.items()
                    if field not in {"candidateID", "evidenceSpanIDs", "source", "target", "deferredRecordID"}}
        key = (item["sourceArtifactID"], canonical_json(material), endpoint(item, candidate["source"]), endpoint(item, candidate["target"]))
        if key in relations:
            join(relations[key], item["candidateKey"])
        else:
            relations[key] = item["candidateKey"]

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in members:
        components[root(item["candidateKey"])].append(item)
    retained = []
    for values in components.values():
        attachments = [extra for value in values for extra in attached.get(value["candidateKey"], [])]
        reason = "retained_no_auto_deduplication"
        if len(values) > 1:
            reason = "collapsed_exact_governed_relation_identity" if values[0]["recordKind"] == "candidate_edge" else "collapsed_exact_governed_node_identity"
        merged = _merge(values + attachments, reason)
        merged["retainedRepresentativeCandidateKey"] = min(value["candidateKey"] for value in values)
        merged["pooledItemID"] = "pooled-item-" + sha256_bytes(canonical_json(sorted(value["candidateKey"] for value in values)))[:16]
        retained.append(merged)

    # Uncertain pairs are taken solely from V10 finding links, by source artifact.
    group_pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item in members:
        if item["eligibilityReason"] != "possible_local_duplicate":
            continue
        target_id = _lineage_target(item, {"POSSIBLE_LOCAL_DUPLICATE"})
        if target_id is None:
            raise Step8CandidatePoolError("POSSIBLE_DUPLICATE_LINEAGE_ABSENT")
        target_key = paired_key(item, target_id)
        if target_key not in parent:
            raise Step8CandidatePoolError("POSSIBLE_DUPLICATE_TARGET_INELIGIBLE")
        group_pairs[item["sourceArtifactID"]].add(tuple(sorted((item["candidateKey"], target_key))))
    groups = []
    for source, pairs in sorted(group_pairs.items()):
        for left, right in sorted(pairs):
            group_id = "duplicate-review-group-" + sha256_bytes(canonical_json((source, left, right)))[:16]
            groups.append({"duplicateReviewGroupID": group_id, "sourceArtifactID": source,
                           "memberCandidateKeys": [left, right], "basis": "frozen_validator_lineage_possible_local_duplicate"})
            for item in retained:
                if item["retainedRepresentativeCandidateKey"] in (left, right):
                    item.setdefault("duplicateReviewGroupIDs", []).append(group_id)
    return sorted(retained, key=lambda item: item["retainedRepresentativeCandidateKey"]), groups


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
        required = {name: root / name for name in ("raw_model_output.json", "provider_response.json", "provider_metadata.json", "parser_result.json", "parsed_candidate.json", "validation_results.json", "lifecycle.json")}
        if any(not path.is_file() for path in required.values()):
            raise Step8CandidatePoolError(f"SELECTED_ATTEMPT_PROVENANCE_ABSENT:{request_id}")
        if _hash(required["raw_model_output.json"]) != index.get("rawOutputSha256") or sha256_bytes(canonical_json(_load(required["provider_response.json"]))) != index.get("providerResponseSha256"):
            raise Step8CandidatePoolError(f"SELECTED_PROVIDER_RAW_DRIFT:{request_id}")
        parser, parsed, validation, attempt = (_load(required["parser_result.json"]), _load(required["parsed_candidate.json"]), _load(required["validation_results.json"]), _load(required["lifecycle.json"]))
        provider_metadata = _load(required["provider_metadata.json"])
        if attempt.get("parserResult") != parser or attempt.get("validation") != validation or parser.get("parseStatus") != "parsed" or validation.get("validationResultsHash") != prediction["acceptedSemanticProjection"].get("validationResultsHash"):
            raise Step8CandidatePoolError(f"PARSER_VALIDATION_LINEAGE_DRIFT:{request_id}")
        envelope = envelope_by_unit[index["primarySourceUnitID"]]
        metadata = parsed.get("metadata", {})
        projection = prediction["acceptedSemanticProjection"]
        if (metadata.get("primarySourceUnitID") != index["primarySourceUnitID"]
                or metadata.get("contextSourceUnitIDs") != index.get("contextSourceUnitIDs")
                or index.get("contextSourceUnitIDs") != envelope.get("contextSourceUnitIDs")
                or metadata.get("sourceArtifactID") != envelope.get("sourceArtifactID")):
            raise Step8CandidatePoolError(f"ENVELOPE_SOURCE_SCOPE_DRIFT:{request_id}")
        provenance = {"runID": metadata.get("runID"), "requestID": request_id,
                      "outputID": metadata.get("outputID"), "provider": metadata.get("provider"),
                      "modelName": metadata.get("modelName"), "modelVersion": metadata.get("modelVersion"),
                      "providerResponseID": provider_metadata.get("responseID"),
                      "selectedAttemptNumber": index.get("selectedAttemptNumber")}
        if any(not isinstance(value, str) or not value for key, value in provenance.items() if key != "selectedAttemptNumber"):
            raise Step8CandidatePoolError(f"C1_PROVENANCE_MAPPING_ABSENT:{request_id}")
        if (metadata.get("requestID") != request_id or provenance["outputID"] != projection.get("outputID")
                or provenance["provider"] != attempt.get("provider")
                or provenance["modelName"] != attempt.get("requestedModel")
                or provider_metadata.get("returnedModel") != provenance["modelVersion"]
                or sha256_bytes(canonical_json(provider_metadata)) != index.get("providerMetadataSha256")):
            raise Step8CandidatePoolError(f"C1_PROVENANCE_MAPPING_DRIFT:{request_id}")
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
                    if evidence[evidence_id].get("sourceUnitID") not in {index["primarySourceUnitID"], *index["contextSourceUnitIDs"]}:
                        raise Step8CandidatePoolError(f"EVIDENCE_OUTSIDE_AUTHORIZED_CONTEXT:{request_id}:{candidate_id}:{evidence_id}")
                    occurrences.append({"evidenceSpanID": evidence_id, **evidence[evidence_id]})
                all_members.append({
                    "candidateKey": f"{request_id}|{kind}|{candidate_id}", "requestID": request_id,
                    "primarySourceUnitID": index["primarySourceUnitID"], "sourceArtifactID": parsed["metadata"]["sourceArtifactID"],
                    "authorizedContextSourceUnitIDs": index["contextSourceUnitIDs"],
                    "c1Provenance": provenance,
                    "recordKind": kind, "candidate": candidate, "validationLineage": record_validation,
                    "providerRawSha256": index["rawOutputSha256"], "providerResponseSha256": index["providerResponseSha256"],
                    "parserStatus": parser["parseStatus"], "selectedAttemptNumber": 1,
                    "eligibilityDisposition": disposition, "eligibilityReason": reason, "evidenceOccurrences": occurrences,
                })
    eligible = [member for member in all_members if member["eligibilityDisposition"] == "eligible"]
    retained, duplicate_groups = deduplicate(eligible, [item for item in all_members if item["eligibilityDisposition"] == "excluded"])
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
