"""Deterministically project accepted Step 8A items for blinded Step 8B review.

No judgments, interface, reconciliation, or positive reference are constructed here.
Only explicit reviewer-field whitelists cross the internal-to-reviewer boundary.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


VERSION = "1.0.0"
POOL = PROJECT_ROOT / "data/curation/papers/m2/publication_step8_internal_candidate_pool/publication_step8_internal_pre_review_candidate_pool_v1.0.1.json"
SUBSET = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_subset_freeze_v0.1.1.json"
AUTHORITY = PROJECT_ROOT / "data/curation/papers/m2/publication_step5_evaluation_authority_freeze_v0.1.3.json"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2/publication_step8_blinded_adjudication"
POOL_SHA256 = "feb045ca031f1d40743725d70c57f9f613ea11df1f720481f97447944d9e12f7"
SUBSET_SHA256 = "b0ab52ab15c91a58a082c2ef6c33f0e4954e82292a86fb0f7cc2852097824b24"
AUTHORITY_SHA256 = "798adb18b0429f5c985a844b62d9f9db4048b98436d306db31769cf2f71da94e"
FILES = {
    "primary": "publication_step8b_blinded_primary_review_v1.0.0.json",
    "secondary": "publication_step8b_blinded_second_review_v1.0.0.json",
    "mapping": "publication_step8b_internal_opaque_lineage_map_v1.0.0.json",
    "instructions": "publication_step8b_reviewer_instructions_v1.0.0.json",
}
ITEM_FIELDS = frozenset({"judgmentItemID", "recordKind", "operationalTarget", "ontologyTerm", "assertion", "evidenceOccurrences", "sourceArtifactID", "primarySourceUnitID", "authorizedContextSourceUnitIDs", "duplicateReviewGroupIDs"})
EVIDENCE_FIELDS = frozenset({"evidenceText", "sourceArtifactID", "sourceUnitID", "sectionID", "sectionTitle", "startOffsetInUnit", "endOffsetInUnit", "startOffsetInDocument", "endOffsetInDocument", "sourceUnitTextHash", "evidenceHash"})


class Step8BlindingError(ValueError):
    """Report a binding, source boundary, or blinded-projection violation."""


def _load(path: Path, expected: str) -> dict[str, Any]:
    """Load a bound JSON object only when its exact tracked bytes match."""

    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise Step8BlindingError(f"FROZEN_BINDING_DRIFT:{path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Step8BlindingError(f"INVALID_BOUND_OBJECT:{path.name}")
    return value


def _self_hash(value: Mapping[str, Any]) -> bool:
    """Check the canonical self-hash without changing the bound artifact."""

    body = dict(value)
    expected = body.pop("artifactSha256", None)
    return isinstance(expected, str) and expected == sha256_bytes(canonical_json(body))


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a deterministic self-hash to a new Step 8B artifact."""

    body = dict(payload)
    body["artifactSha256"] = sha256_bytes(canonical_json(body))
    return body


def _write_immutable(path: Path, value: Mapping[str, Any]) -> None:
    """Write canonical bytes idempotently, rejecting a divergent replacement."""

    data = canonical_json(dict(value)) + b"\n"
    if path.exists() and path.read_bytes() != data:
        raise Step8BlindingError(f"OUTPUT_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _neutral_ids(items: list[dict[str, Any]], pool_hash: str) -> dict[str, str]:
    """Assign opaque sequential IDs in a stable hash order unrelated to status."""

    identities = [item.get("pooledItemID") for item in items]
    if any(not isinstance(value, str) or not value for value in identities) or len(set(identities)) != len(identities):
        raise Step8BlindingError("NON_UNIQUE_POOL_ITEM_IDENTITY")
    ranked = sorted(identities, key=lambda value: (sha256_bytes(canonical_json([pool_hash, value])), value))
    return {value: f"judgment-item-{number:04d}" for number, value in enumerate(ranked, 1)}


def _endpoint(value: Mapping[str, Any], item: Mapping[str, Any], candidates: Mapping[str, Mapping[str, Any]], opaque_by_candidate: Mapping[str, str]) -> dict[str, Any]:
    """Render an exact endpoint without exposing original candidate references."""

    kind, reference = value.get("referenceType"), value.get("referenceID")
    if kind == "deterministic_node":
        if not isinstance(reference, str) or not reference:
            raise Step8BlindingError("DETERMINISTIC_ENDPOINT_ID_ABSENT")
        return {"endpointKind": "deterministic_node", "sourceArtifactID": value.get("artifactID"), "exactNodeID": reference}
    if kind != "candidate_node" or not isinstance(reference, str):
        raise Step8BlindingError("UNRESOLVED_RELATION_ENDPOINT")
    key = f"{item['requestID']}|candidate_node|{reference}"
    node = candidates.get(key)
    if node is None or node.get("sourceArtifactID") != item.get("sourceArtifactID"):
        raise Step8BlindingError("CANDIDATE_ENDPOINT_MAPPING_DRIFT")
    candidate = node["candidate"]
    result = {"endpointKind": "candidate_node", "label": candidate.get("label"),
              "className": candidate.get("className"), "ontologyClassID": candidate.get("ontologyClassID")}
    if key in opaque_by_candidate:
        result["judgmentItemID"] = opaque_by_candidate[key]
    return result


def _assertion(item: Mapping[str, Any], candidates: Mapping[str, Mapping[str, Any]], opaque_by_candidate: Mapping[str, str]) -> dict[str, Any]:
    """Project only human-readable, governed semantic assertion fields."""

    candidate = item["candidate"]
    if item["recordKind"] == "candidate_node":
        attributes = [{"attributeName": row.get("attributeName"), "value": row.get("value")}
                      for row in candidate.get("attributes", [])]
        result = {"action": candidate.get("action"), "label": candidate.get("label"), "attributes": attributes}
        if candidate.get("action") == "link_existing":
            result["exactExistingNodeID"] = candidate.get("existingNodeID")
        return result
    if item["recordKind"] == "candidate_edge":
        return {"action": candidate.get("action"), "relationName": candidate.get("relationName"),
                "relationScope": candidate.get("relationScope"),
                "sourceEndpoint": _endpoint(candidate.get("source", {}), item, candidates, opaque_by_candidate),
                "targetEndpoint": _endpoint(candidate.get("target", {}), item, candidates, opaque_by_candidate)}
    raise Step8BlindingError("UNKNOWN_RECORD_KIND")


def _project_item(item: Mapping[str, Any], judgment_id: str, groups: list[str], candidates: Mapping[str, Mapping[str, Any]], opaque_by_candidate: Mapping[str, str], primary_units: set[str]) -> dict[str, Any]:
    """Apply the Section 9 reviewer whitelist and source/context boundary."""

    primary = item.get("primarySourceUnitID")
    contexts = item.get("authorizedContextSourceUnitIDs")
    if primary not in primary_units or not isinstance(contexts, list) or any(context in primary_units or context == primary for context in contexts):
        raise Step8BlindingError("PRIMARY_CONTEXT_SCOPE_DRIFT")
    evidence = []
    for occurrence in item.get("evidenceOccurrences", []):
        if occurrence.get("sourceUnitID") not in {primary, *contexts} or occurrence.get("sourceArtifactID") != item.get("sourceArtifactID"):
            raise Step8BlindingError("EVIDENCE_OUTSIDE_AUTHORIZED_SCOPE")
        evidence.append({field: occurrence.get(field) for field in EVIDENCE_FIELDS})
    if not evidence:
        raise Step8BlindingError("ITEM_EVIDENCE_ABSENT")
    candidate = item["candidate"]
    target = candidate.get("operationalTargetID") if item["recordKind"] == "candidate_node" else candidate.get("operationalRelationID")
    term = candidate.get("ontologyClassID") if item["recordKind"] == "candidate_node" else candidate.get("ontologyRelationID")
    human_target = candidate.get("className") if item["recordKind"] == "candidate_node" else candidate.get("relationName")
    projected = {"judgmentItemID": judgment_id, "recordKind": "node" if item["recordKind"] == "candidate_node" else "relation",
                 "operationalTarget": {"operationalID": target, "name": human_target}, "ontologyTerm": term,
                 "assertion": _assertion(item, candidates, opaque_by_candidate),
                 "evidenceOccurrences": evidence, "sourceArtifactID": item["sourceArtifactID"],
                 "primarySourceUnitID": primary, "authorizedContextSourceUnitIDs": contexts,
                 "duplicateReviewGroupIDs": groups}
    if set(projected) != ITEM_FIELDS:
        raise Step8BlindingError("REVIEWER_WHITELIST_DRIFT")
    return projected


def _project_groups(groups: list[dict[str, Any]], opaque_by_candidate: Mapping[str, str], candidates: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Blind only existing source-local Step 8A duplicate-review groups."""

    group_ids: dict[str, str] = {}
    visible = []
    for number, group in enumerate(sorted(groups, key=lambda value: value["duplicateReviewGroupID"]), 1):
        members = group.get("memberCandidateKeys", [])
        if len(members) < 2 or any(key not in opaque_by_candidate or key not in candidates for key in members):
            raise Step8BlindingError("DUPLICATE_GROUP_MEMBER_DRIFT")
        sources = {candidates[key]["sourceArtifactID"] for key in members}
        units = {candidates[key]["primarySourceUnitID"] for key in members}
        if len(sources) != 1 or len(units) != 1 or sources != {group.get("sourceArtifactID")}:
            raise Step8BlindingError("DUPLICATE_GROUP_SOURCE_SCOPE_DRIFT")
        opaque_id = f"duplicate-group-{number:04d}"
        group_ids[group["duplicateReviewGroupID"]] = opaque_id
        visible.append({"duplicateReviewGroupID": opaque_id,
                        "judgmentItemIDs": sorted({opaque_by_candidate[key] for key in members}),
                        "instruction": "These source-local assertions require a same-source duplicate decision before final reference counting."})
    return visible, group_ids


def build(pool_path: Path = POOL, subset_path: Path = SUBSET, authority_path: Path = AUTHORITY) -> dict[str, dict[str, Any]]:
    """Construct two blinded packages, a private map, and review instructions."""

    pool = _load(pool_path, POOL_SHA256)
    subset = _load(subset_path, SUBSET_SHA256)
    authority = _load(authority_path, AUTHORITY_SHA256)
    if not all(_self_hash(value) for value in (pool, subset)):
        raise Step8BlindingError("FROZEN_SELF_HASH_DRIFT")
    bound = authority.get("frozenBindings", {}).get("secondaryReviewSubset", {})
    if bound.get("artifactSha256") != subset.get("artifactSha256") or bound.get("trackedFileSha256") != SUBSET_SHA256:
        raise Step8BlindingError("SECOND_REVIEW_AUTHORITY_BINDING_DRIFT")
    items = pool.get("retainedPooledItems", [])
    candidates = {item["candidateKey"]: item for item in pool.get("candidates", [])}
    if len(candidates) != len(pool.get("candidates", [])):
        raise Step8BlindingError("NON_UNIQUE_SOURCE_CANDIDATES")
    primary_units = {item["primarySourceUnitID"] for item in pool.get("candidates", [])}
    if len(primary_units) != pool.get("source", {}).get("selectedAttemptCount") or {item["primarySourceUnitID"] for item in items} != primary_units:
        raise Step8BlindingError("PRIMARY_UNIT_BINDING_DRIFT")
    secondary_units = subset.get("selectedPrimarySourceUnitIDs", [])
    if not isinstance(secondary_units, list) or len(secondary_units) != 2 or len(set(secondary_units)) != 2 or not set(secondary_units) <= primary_units:
        raise Step8BlindingError("SECOND_REVIEW_UNIT_BINDING_DRIFT")
    opaque = _neutral_ids(items, pool["artifactSha256"])
    opaque_by_candidate = {key: opaque[item["pooledItemID"]] for item in items for key in item["memberCandidateKeys"]}
    groups = pool.get("unresolvedDuplicateReviewGroups", [])
    visible_groups, group_ids = _project_groups(groups, opaque_by_candidate, candidates)
    membership = {key: group_ids[group["duplicateReviewGroupID"]] for group in groups for key in group["memberCandidateKeys"]}
    projected = []
    mapping = []
    for item in items:
        judgment_id = opaque[item["pooledItemID"]]
        group_refs = sorted({membership[key] for key in item["memberCandidateKeys"] if key in membership})
        projected.append(_project_item(item, judgment_id, group_refs, candidates, opaque_by_candidate, primary_units))
        mapping.append({"judgmentItemID": judgment_id, "step8APooledItemID": item["pooledItemID"],
                        "representativeCandidateKey": item["retainedRepresentativeCandidateKey"],
                        "memberCandidateKeys": item["memberCandidateKeys"], "c1Provenance": item["c1Provenance"],
                        "primarySourceUnitID": item["primarySourceUnitID"], "sourceArtifactID": item["sourceArtifactID"]})
    projected.sort(key=lambda value: value["judgmentItemID"])
    mapping.sort(key=lambda value: value["judgmentItemID"])
    source = {"step8APoolArtifactSha256": pool["artifactSha256"], "secondarySubsetArtifactSha256": subset["artifactSha256"]}
    primary = _artifact({"artifactType": "publication_step8b_blinded_primary_review", "artifactVersion": VERSION,
                         "primarySourceUnitIDs": sorted(primary_units), "judgmentItems": projected,
                         "duplicateReviewGroups": visible_groups})
    secondary_items = [item for item in projected if item["primarySourceUnitID"] in secondary_units]
    secondary_ids = {item["judgmentItemID"] for item in secondary_items}
    secondary = _artifact({"artifactType": "publication_step8b_blinded_second_review", "artifactVersion": VERSION,
                           "primarySourceUnitIDs": sorted(secondary_units), "judgmentItems": secondary_items,
                           "duplicateReviewGroups": [{**group, "judgmentItemIDs": [value for value in group["judgmentItemIDs"] if value in secondary_ids]}
                                                    for group in visible_groups if any(value in secondary_ids for value in group["judgmentItemIDs"])]})
    private = _artifact({"artifactType": "publication_step8b_internal_opaque_lineage_map", "artifactVersion": VERSION,
                         "accessScope": "internal_only", "bindings": source, "items": mapping,
                         "duplicateReviewGroups": [{"opaqueGroupID": group_ids[group["duplicateReviewGroupID"]],
                                                    "step8AGroupID": group["duplicateReviewGroupID"], "memberCandidateKeys": group["memberCandidateKeys"]}
                                                   for group in groups]})
    instructions = _artifact({"artifactType": "publication_step8b_reviewer_instructions", "artifactVersion": VERSION,
                              "reviewScope": "Judge each proposed assertion as written using its cited evidence and authorized source units. The second reviewer independently reviews only the bound two-unit subset.",
                              "ordinaryJudgments": ["supported_as_proposed", "not_supported_as_proposed", "insufficient_evidence_to_decide"],
                              "duplicateDecisions": ["same_source_local_assertion", "distinct_assertions", "insufficient_evidence_to_resolve_duplicate_status"],
                              "duplicateGroupInstruction": "Grouped assertions require a same-source duplicate decision before final reference counting. Grouping does not decide identity.",
                              "boundary": "Review the proposed assertion without editing, splitting, reclassifying, relinking, normalizing, or adding assertions. Use only the cited evidence and authorized primary/context source units.",
                              "summary": {"primaryUnits": len(primary_units), "primaryItems": len(projected), "secondReviewUnits": len(secondary_units), "secondReviewItems": len(secondary_items), "duplicateReviewGroups": len(groups)}})
    return {"primary": primary, "secondary": secondary, "mapping": private, "instructions": instructions}


def materialize(output_root: Path = OUTPUT_ROOT) -> dict[str, Path]:
    """Write only the four deterministic Step 8B artifacts."""

    artifacts = build()
    paths = {key: output_root / name for key, name in FILES.items()}
    for key, path in paths.items():
        _write_immutable(path, artifacts[key])
    return paths
