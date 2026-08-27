"""Frozen V1-V12 Publication candidate validation and usable-output materialization.

The validator loads the frozen target profile, ontology specification, and candidate
schema. It does not reproduce their target, class, relation, or signature tables in
Python and never converts automatic validation into graph-level acceptance.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Mapping, MutableMapping, Sequence

import jsonschema

from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    EVIDENCE_VALIDATION_CONTRACT_PATH,
    ONTOLOGY_SPEC_PATH,
    PROJECT_ROOT,
    TARGET_INVENTORY_PATH,
    canonical_json,
    expected_candidate_metadata,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.source_units import normalize_canonical_text


VALIDATOR_VERSION = "0.1.2"
RULE_VERSION = "publication-evidence-validation-0.1.0"
VALIDATION_CONTRACT_VERSION = "0.1.0"
PROCESSING_CODES = {
    "INVALID_JSON",
    "TIMEOUT",
    "API_ERROR",
    "TRUNCATED_RESPONSE",
    "TOKEN_LIMIT",
    "RETRY_EXHAUSTED",
}

HARD_FINDING_CODES = {
    "SCHEMA_VALIDATION_FAILED",
    "FORBIDDEN_FIELD",
    "REQUEST_ID_MISMATCH",
    "RUN_ID_MISMATCH",
    "SOURCE_ARTIFACT_MISMATCH",
    "PRIMARY_SOURCE_UNIT_MISMATCH",
    "CONTEXT_SOURCE_UNIT_MISMATCH",
    "TARGET_PROFILE_VERSION_MISMATCH",
    "TARGET_PROFILE_HASH_MISMATCH",
    "SOURCE_UNIT_CONTRACT_VERSION_MISMATCH",
    "SOURCE_UNIT_CONTRACT_HASH_MISMATCH",
    "CANDIDATE_SCHEMA_VERSION_MISMATCH",
    "CANDIDATE_SCHEMA_HASH_MISMATCH",
    "ONTOLOGY_VERSION_MISMATCH",
    "ONTOLOGY_HASH_MISMATCH",
    "PROMPT_HASH_MISMATCH",
    "REQUEST_INPUT_HASH_MISMATCH",
    "RAW_RESPONSE_HASH_MISMATCH",
    "SOURCE_UNIT_NOT_FOUND",
    "SOURCE_UNIT_NOT_IN_REQUEST",
    "SOURCE_UNIT_HASH_MISMATCH",
    "SECTION_ID_MISMATCH",
    "SECTION_TITLE_MISMATCH",
    "EVIDENCE_TEXT_EMPTY",
    "EVIDENCE_NOT_LITERAL",
    "OFFSET_OUT_OF_BOUNDS",
    "OFFSET_MISMATCH_IN_UNIT",
    "OFFSET_MISMATCH_IN_DOCUMENT",
    "UNIT_DOCUMENT_OFFSET_INCONSISTENT",
    "EVIDENCE_HASH_MISMATCH",
    "EVIDENCE_FROM_EXCLUDED_UNIT",
    "EVIDENCE_FROM_NEEDS_REVIEW_UNIT",
    "CROSS_UNIT_EVIDENCE_SPAN",
    "CANDIDATE_ID_DUPLICATE",
    "UNKNOWN_OPERATIONAL_TARGET",
    "TARGET_NOT_INCLUDED_IN_REQUEST",
    "TARGET_NOT_EMITTABLE",
    "OUT_OF_SCOPE_TARGET",
    "FOLLOW_ON_TARGET",
    "ONTOLOGY_ID_MISMATCH",
    "CLASS_NAME_MISMATCH",
    "RELATION_NAME_MISMATCH",
    "ACTION_NOT_ALLOWED",
    "ABSTRACT_CLASS_OUTPUT",
    "DETERMINISTIC_MUTATION_ATTEMPT",
    "NODE_EVIDENCE_MISSING",
    "NODE_EVIDENCE_INVALID",
    "LABEL_EMPTY",
    "VERBATIM_LABEL_NOT_IN_EVIDENCE",
    "PROPOSE_NEW_HAS_EXISTING_ENDPOINT",
    "LINK_EXISTING_ENDPOINT_MISSING",
    "LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED",
    "LINK_EXISTING_CLASS_MISMATCH",
    "INVALID_IDENTITY_SCOPE",
    "INVALID_PROVISIONAL_IDENTITY",
    "ATTRIBUTE_NOT_ALLOWED_FOR_TARGET",
    "ATTRIBUTE_EVIDENCE_MISSING",
    "ENDPOINT_REFERENCE_MISSING",
    "ENDPOINT_REFERENCE_AMBIGUOUS",
    "ENDPOINT_CLASS_UNRESOLVED",
    "ENDPOINT_LIFECYCLE_INVALID",
    "EDGE_EVIDENCE_MISSING",
    "EDGE_EVIDENCE_INVALID",
    "RELATION_EVIDENCE_INSUFFICIENT",
    "INVALID_DOMAIN",
    "INVALID_RANGE",
    "RELATION_SCOPE_MISMATCH",
    "UNAUTHORIZED_RELATION_BRANCH",
    "NEGATIVE_SUPPORT_NOT_AUTHORIZED",
    "SUMMARY_RELATION_NOT_AUTHORIZED",
    "THEORY_GROUNDING_RELATION_NOT_AUTHORIZED",
    "CONFLICTING_RELATION_ROLES",
    "UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY",
    "NORMALIZATION_RULE_NOT_APPROVED",
    "NORMALIZATION_RULE_OUTPUT_MISMATCH",
    "ABSTENTION_REASON_INVALID",
    "ABSTENTION_SCOPE_INVALID",
    "ABSTENTION_TARGET_MISMATCH",
    "ABSTENTION_EVIDENCE_INVALID",
    "PROCESSING_FAILURE_MISCLASSIFIED_AS_ABSTENTION",
    "DEFERRED_RECORD_NOT_FOUND",
    "DEFERRED_RECORD_NOT_IN_REQUEST",
    "DEFERRED_DISPOSITION_INVALID",
    "DEFERRED_ACCEPTED_WITHOUT_VALIDATED_CANDIDATE",
    "DEFERRED_CANDIDATE_MISMATCH",
}

# These frozen vocabulary members have no deterministic emission rule in M1. Some are
# structurally expressible, while the others require operations or rule-selection fields
# absent from the closed M1 candidate schema. The validator deliberately does not invent
# semantic proxies for either category.
STRUCTURALLY_EXPRESSIBLE_NOT_DETERMINISTICALLY_EMITTED_CODES = frozenset(
    {"CONFLICTING_RELATION_ROLES", "RELATION_EVIDENCE_INSUFFICIENT"}
)
NOT_AUTHORABLE_IN_M1_VALIDATOR_CODES = frozenset(
    {
        "DETERMINISTIC_MUTATION_ATTEMPT",
        "SUMMARY_RELATION_NOT_AUTHORIZED",
        "THEORY_GROUNDING_RELATION_NOT_AUTHORIZED",
        "UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY",
        "NORMALIZATION_RULE_NOT_APPROVED",
        "NORMALIZATION_RULE_OUTPUT_MISMATCH",
    }
)
DECLARED_BUT_NOT_CURRENTLY_EMITTED_CODES = frozenset(
    STRUCTURALLY_EXPRESSIBLE_NOT_DETERMINISTICALLY_EMITTED_CODES
    | NOT_AUTHORABLE_IN_M1_VALIDATOR_CODES
)


def _finding(
    stage: str,
    code: str,
    pointer: str,
    expected: Any,
    observed: Any,
    *,
    severity: str = "error",
) -> dict[str, Any]:
    """Create one deterministic public validation finding without hidden reasoning."""

    safe_observed = observed
    if isinstance(observed, str) and len(observed) > 200:
        safe_observed = {"sha256": sha256_bytes(observed.encode("utf-8"))}
    return {
        "stage": stage,
        "code": code,
        "severity": severity,
        "message": code.replace("_", " ").lower(),
        "jsonPointer": pointer,
        "expected": expected,
        "observed": safe_observed,
    }


def _result_hash(result: Mapping[str, Any]) -> str:
    """Hash a validation-result projection excluding its self-hash."""

    return sha256_bytes(canonical_json({k: v for k, v in result.items() if k != "validationResultHash"}))


def _finish_result(result: MutableMapping[str, Any]) -> dict[str, Any]:
    """Return a copied validation result with its deterministic self-hash."""

    finished = dict(result)
    finished["validationResultHash"] = _result_hash(finished)
    return finished


def _target_indexes(profile: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Index frozen node and relation rows by operational identifier."""

    return (
        {row["operational_id"]: row for row in profile["node_targets"]},
        {row["operational_id"]: row for row in profile["relation_targets"]},
    )


def _canonical_document(request: Mapping[str, Any]) -> str:
    """Load the exact canonical document, allowing explicit synthetic test text."""

    if "canonicalDocumentText" in request:
        value = request["canonicalDocumentText"]
        if not isinstance(value, str):
            raise TypeError("canonicalDocumentText must be a string")
        return value
    source_path = PROJECT_ROOT / str(request["sourceUnit"]["sourceFile"])
    return normalize_canonical_text(source_path.read_bytes())


def _metadata_binding_findings(
    envelope: Mapping[str, Any], request: Mapping[str, Any], raw_hash: str
) -> list[dict[str, Any]]:
    """Validate every frozen V3 candidate-metadata binding against trusted inputs."""

    metadata = envelope.get("metadata", {})
    expected = expected_candidate_metadata(request, raw_hash)
    codes = {
        "outputID": "REQUEST_ID_MISMATCH",
        "requestID": "REQUEST_ID_MISMATCH",
        "runID": "RUN_ID_MISMATCH",
        "sourceArtifactID": "SOURCE_ARTIFACT_MISMATCH",
        "primarySourceUnitID": "PRIMARY_SOURCE_UNIT_MISMATCH",
        "contextSourceUnitIDs": "CONTEXT_SOURCE_UNIT_MISMATCH",
        "requestScope": "REQUEST_INPUT_HASH_MISMATCH",
        "includedCompleteSection": "REQUEST_INPUT_HASH_MISMATCH",
        "extractionChannel": "REQUEST_INPUT_HASH_MISMATCH",
        "targetInventoryProfileID": "TARGET_PROFILE_VERSION_MISMATCH",
        "targetInventorySchemaVersion": "TARGET_PROFILE_VERSION_MISMATCH",
        "targetInventorySha256": "TARGET_PROFILE_HASH_MISMATCH",
        "sourceUnitContractVersion": "SOURCE_UNIT_CONTRACT_VERSION_MISMATCH",
        "sourceUnitContractSha256": "SOURCE_UNIT_CONTRACT_HASH_MISMATCH",
        "candidateSchemaVersion": "CANDIDATE_SCHEMA_VERSION_MISMATCH",
        "candidateSchemaSha256": "CANDIDATE_SCHEMA_HASH_MISMATCH",
        "ontologyVersion": "ONTOLOGY_VERSION_MISMATCH",
        "ontologySha256": "ONTOLOGY_HASH_MISMATCH",
        "promptVersion": "PROMPT_HASH_MISMATCH",
        "promptSha256": "PROMPT_HASH_MISMATCH",
        "requestInputSha256": "REQUEST_INPUT_HASH_MISMATCH",
        "rawResponseSha256": "RAW_RESPONSE_HASH_MISMATCH",
        "provider": "REQUEST_INPUT_HASH_MISMATCH",
        "modelName": "REQUEST_INPUT_HASH_MISMATCH",
        "modelVersion": "REQUEST_INPUT_HASH_MISMATCH",
        "generationParameters": "REQUEST_INPUT_HASH_MISMATCH",
        "tokenUsage": "REQUEST_INPUT_HASH_MISMATCH",
        "costUSD": "REQUEST_INPUT_HASH_MISMATCH",
        "retryCount": "REQUEST_INPUT_HASH_MISMATCH",
        "responseCreatedAt": "REQUEST_INPUT_HASH_MISMATCH",
    }
    findings: list[dict[str, Any]] = []
    for field, code in codes.items():
        if metadata.get(field) != expected.get(field):
            findings.append(
                _finding("V3", code, f"/metadata/{field}", expected.get(field), metadata.get(field))
            )
    if metadata.get("eligibleOperationalTargetIDs") != expected["eligibleOperationalTargetIDs"]:
        findings.append(
            _finding(
                "V3",
                "TARGET_NOT_INCLUDED_IN_REQUEST",
                "/metadata/eligibleOperationalTargetIDs",
                expected["eligibleOperationalTargetIDs"],
                metadata.get("eligibleOperationalTargetIDs"),
            )
        )
    if metadata.get("deferredRecordIDs") != expected["deferredRecordIDs"]:
        findings.append(
            _finding(
                "V3",
                "DEFERRED_RECORD_NOT_IN_REQUEST",
                "/metadata/deferredRecordIDs",
                expected["deferredRecordIDs"],
                metadata.get("deferredRecordIDs"),
            )
        )
    return findings


def _parser_binding_findings(parser_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Reject raw attempts to author fields owned by the trusted pipeline."""

    return [
        _finding(
            "V2",
            "FORBIDDEN_FIELD",
            f"/{field}",
            "pipeline-owned field omitted from provider payload",
            "model-authored value was ignored and preserved only in parsedDocument",
        )
        for field in parser_result.get("pipelineOwnedFieldInjectionAttempts", [])
    ]


def _validate_evidence(
    evidence: Mapping[str, Any],
    pointer: str,
    request: Mapping[str, Any],
    canonical_document: str,
) -> tuple[bool, list[dict[str, Any]]]:
    """Apply all exact V4 source, literal, coordinate, and hash checks to one span."""

    unit = request["sourceUnit"]
    findings: list[dict[str, Any]] = []
    if evidence.get("sourceArtifactID") != request["sourceArtifactID"]:
        findings.append(_finding("V4", "SOURCE_ARTIFACT_MISMATCH", pointer + "/sourceArtifactID", request["sourceArtifactID"], evidence.get("sourceArtifactID")))
    allowed_units = {request["primarySourceUnitID"], *request.get("contextSourceUnitIDs", [])}
    if evidence.get("sourceUnitID") not in allowed_units:
        findings.append(_finding("V4", "SOURCE_UNIT_NOT_IN_REQUEST", pointer + "/sourceUnitID", sorted(allowed_units), evidence.get("sourceUnitID")))
    if evidence.get("sourceUnitID") != unit["sourceUnitID"]:
        findings.append(_finding("V4", "SOURCE_UNIT_NOT_FOUND", pointer + "/sourceUnitID", unit["sourceUnitID"], evidence.get("sourceUnitID")))
    if evidence.get("sourceUnitTextHash") != unit["textHash"]:
        findings.append(_finding("V4", "SOURCE_UNIT_HASH_MISMATCH", pointer + "/sourceUnitTextHash", unit["textHash"], evidence.get("sourceUnitTextHash")))
    if evidence.get("sectionID") != unit["sectionID"]:
        findings.append(_finding("V4", "SECTION_ID_MISMATCH", pointer + "/sectionID", unit["sectionID"], evidence.get("sectionID")))
    if evidence.get("sectionTitle") != unit["sectionTitleRaw"]:
        findings.append(_finding("V4", "SECTION_TITLE_MISMATCH", pointer + "/sectionTitle", unit["sectionTitleRaw"], evidence.get("sectionTitle")))
    text = evidence.get("evidenceText")
    if not isinstance(text, str) or not text:
        findings.append(_finding("V4", "EVIDENCE_TEXT_EMPTY", pointer + "/evidenceText", "non-empty string", text))
        return False, findings
    start = evidence.get("startOffsetInUnit")
    end = evidence.get("endOffsetInUnit")
    document_start = evidence.get("startOffsetInDocument")
    document_end = evidence.get("endOffsetInDocument")
    offsets = (start, end, document_start, document_end)
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in offsets):
        findings.append(_finding("V4", "OFFSET_OUT_OF_BOUNDS", pointer, "integer offsets", offsets))
        return False, findings
    if start < 0 or end <= start or end > len(unit["text"]):
        findings.append(_finding("V4", "OFFSET_OUT_OF_BOUNDS", pointer, f"0 <= start < end <= {len(unit['text'])}", [start, end]))
    else:
        if unit["text"][start:end] != text:
            findings.append(_finding("V4", "OFFSET_MISMATCH_IN_UNIT", pointer, text, unit["text"][start:end]))
            findings.append(_finding("V4", "EVIDENCE_NOT_LITERAL", pointer + "/evidenceText", "literal unit slice", text))
    expected_document_start = unit["startOffsetInDocument"] + start
    expected_document_end = unit["startOffsetInDocument"] + end
    if document_start != expected_document_start or document_end != expected_document_end:
        findings.append(_finding("V4", "UNIT_DOCUMENT_OFFSET_INCONSISTENT", pointer, [expected_document_start, expected_document_end], [document_start, document_end]))
    if document_start < unit["startOffsetInDocument"] or document_end > unit["endOffsetInDocument"]:
        findings.append(_finding("V4", "CROSS_UNIT_EVIDENCE_SPAN", pointer, [unit["startOffsetInDocument"], unit["endOffsetInDocument"]], [document_start, document_end]))
    if 0 <= document_start < document_end <= len(canonical_document):
        if canonical_document[document_start:document_end] != text:
            findings.append(_finding("V4", "OFFSET_MISMATCH_IN_DOCUMENT", pointer, text, canonical_document[document_start:document_end]))
    else:
        findings.append(_finding("V4", "OFFSET_OUT_OF_BOUNDS", pointer, f"canonical document length {len(canonical_document)}", [document_start, document_end]))
    evidence_hash = evidence.get("evidenceHash")
    computed_hash = sha256_bytes(text.encode("utf-8"))
    if evidence_hash is not None and evidence_hash != computed_hash:
        findings.append(_finding("V4", "EVIDENCE_HASH_MISMATCH", pointer + "/evidenceHash", computed_hash, evidence_hash))
    if unit.get("eligibility") == "excluded":
        findings.append(_finding("V4", "EVIDENCE_FROM_EXCLUDED_UNIT", pointer, "eligible source unit", "excluded"))
    if unit.get("eligibility") == "needs_review":
        findings.append(_finding("V4", "EVIDENCE_FROM_NEEDS_REVIEW_UNIT", pointer, "eligible source unit", "needs_review"))
    return not any(item["code"] in HARD_FINDING_CODES for item in findings), findings


def _authorization_findings(
    candidate: Mapping[str, Any],
    pointer: str,
    target: Mapping[str, Any] | None,
    request: Mapping[str, Any],
    *,
    edge: bool,
) -> list[dict[str, Any]]:
    """Apply V5 frozen target, ontology identity, action, and emission authorization."""

    findings: list[dict[str, Any]] = []
    target_field = "operationalRelationID" if edge else "operationalTargetID"
    target_id = candidate.get(target_field)
    if target is None:
        return [_finding("V5", "UNKNOWN_OPERATIONAL_TARGET", pointer + f"/{target_field}", "frozen operational target", target_id)]
    if target_id not in request["eligibleOperationalTargetIDs"]:
        findings.append(_finding("V5", "TARGET_NOT_INCLUDED_IN_REQUEST", pointer + f"/{target_field}", request["eligibleOperationalTargetIDs"], target_id))
    if target.get("emission_mode") not in {"llm_candidate", "resolver_mediated_candidate"} and not (not edge and candidate.get("action") == "link_existing"):
        findings.append(_finding("V5", "TARGET_NOT_EMITTABLE", pointer + f"/{target_field}", "candidate-emittable target", target.get("emission_mode")))
    treatment = target.get("pilot_treatment")
    if treatment == "out_of_scope":
        findings.append(_finding("V5", "OUT_OF_SCOPE_TARGET", pointer + f"/{target_field}", "in-scope treatment", treatment))
    if treatment == "separate_follow_on_protocol":
        findings.append(_finding("V5", "FOLLOW_ON_TARGET", pointer + f"/{target_field}", "M1 target", treatment))
    if candidate.get("action") not in target.get("allowed_actions", []):
        findings.append(_finding("V5", "ACTION_NOT_ALLOWED", pointer + "/action", target.get("allowed_actions", []), candidate.get("action")))
    formal_key = "formal_relations" if edge else "formal_classes"
    id_field = "ontologyRelationID" if edge else "ontologyClassID"
    name_field = "relationName" if edge else "className"
    formal = target.get(formal_key, [])
    ids = {row["id"] for row in formal}
    names = {row["name"] for row in formal}
    if candidate.get(id_field) not in ids:
        findings.append(_finding("V5", "ONTOLOGY_ID_MISMATCH", pointer + f"/{id_field}", sorted(ids), candidate.get(id_field)))
    if candidate.get(name_field) not in names:
        code = "RELATION_NAME_MISMATCH" if edge else "CLASS_NAME_MISMATCH"
        findings.append(_finding("V5", code, pointer + f"/{name_field}", sorted(names), candidate.get(name_field)))
    if not edge and target.get("direct_instantiation") is False and candidate.get("action") == "propose_new":
        findings.append(_finding("V5", "ABSTRACT_CLASS_OUTPUT", pointer, "concrete directly instantiable class", candidate.get("className")))
    return findings


def _referenced_evidence_findings(
    evidence_ids: Sequence[str],
    pointer: str,
    evidence_validity: Mapping[str, bool],
    missing_code: str,
    invalid_code: str,
    stage: str,
) -> list[dict[str, Any]]:
    """Validate candidate-specific evidence presence and resolved V4 validity."""

    if not evidence_ids:
        return [_finding(stage, missing_code, pointer, "at least one evidence span", [])]
    invalid = [value for value in evidence_ids if not evidence_validity.get(value, False)]
    return [_finding(stage, invalid_code, pointer, "valid evidence span IDs", invalid)] if invalid else []


def _authorized_attributes(target: Mapping[str, Any] | None) -> set[str]:
    """Load the exact attribute names authorized by one frozen target row."""

    if target is None:
        return set()
    return {
        attribute["name"]
        for formal in target.get("formal_classes", [])
        for attribute in formal.get("attributes", [])
    }


def _source_exact_attribute_names(target: Mapping[str, Any] | None) -> set[str]:
    """Return attributes named by the target's frozen exact-string identity policy."""

    if target is None:
        return set()
    authorized = _authorized_attributes(target)
    preserved = set(
        target.get("identity_policy", {}).get("preserve_exact_source_strings", [])
    )
    return authorized & preserved


def _is_contextual_occurrence_target(target: Mapping[str, Any] | None) -> bool:
    """Identify target-profile classes whose identity includes local context."""

    return bool(
        target
        and any(
            formal.get("name") in {"EvaluationMetric", "Parameter"}
            for formal in target.get("formal_classes", [])
        )
    )


def _node_findings(
    node: Mapping[str, Any],
    pointer: str,
    target: Mapping[str, Any] | None,
    request: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    evidence_validity: Mapping[str, bool],
) -> tuple[list[dict[str, Any]], str, str | None, str, str | None]:
    """Apply V6 node evidence, action, identity, attribute, atomicity, and normalization rules."""

    findings = _referenced_evidence_findings(node.get("evidenceSpanIDs", []), pointer + "/evidenceSpanIDs", evidence_validity, "NODE_EVIDENCE_MISSING", "NODE_EVIDENCE_INVALID", "V6")
    label = node.get("label")
    if not isinstance(label, str) or not label:
        findings.append(_finding("V6", "LABEL_EMPTY", pointer + "/label", "non-empty verbatim label", label))
    elif not any(label in str(evidence_by_id.get(ref, {}).get("evidenceText", "")) for ref in node.get("evidenceSpanIDs", [])):
        findings.append(_finding("V6", "VERBATIM_LABEL_NOT_IN_EVIDENCE", pointer + "/label", "literal substring of cited evidence", label))
    action = node.get("action")
    existing = node.get("existingNodeID")
    identity_scope = node.get("identityScope")
    if action == "propose_new":
        if existing is not None:
            findings.append(_finding("V6", "PROPOSE_NEW_HAS_EXISTING_ENDPOINT", pointer + "/existingNodeID", None, existing))
        allowed_scopes = {"source_local", "resolver_pending"}
        if identity_scope not in allowed_scopes:
            findings.append(_finding("V6", "INVALID_IDENTITY_SCOPE", pointer + "/identityScope", sorted(allowed_scopes), identity_scope))
    elif action == "link_existing":
        if not existing:
            findings.append(_finding("V6", "LINK_EXISTING_ENDPOINT_MISSING", pointer + "/existingNodeID", "authorized endpoint ID", existing))
        endpoints = {row.get("nodeID"): row for row in request.get("deterministicEndpoints", [])}
        endpoints.update({row.get("candidateID"): row for row in request.get("acceptedLocalCandidateEndpoints", [])})
        endpoint = endpoints.get(existing)
        if endpoint is None:
            findings.append(_finding("V6", "LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED", pointer + "/existingNodeID", sorted(value for value in endpoints if value), existing))
        elif endpoint.get("className") != node.get("className"):
            findings.append(_finding("V6", "LINK_EXISTING_CLASS_MISMATCH", pointer + "/existingNodeID", node.get("className"), endpoint.get("className")))
        if identity_scope != "exact_existing_endpoint":
            findings.append(_finding("V6", "INVALID_IDENTITY_SCOPE", pointer + "/identityScope", "exact_existing_endpoint", identity_scope))
    if node.get("artifactScope") == "external_artifact" and identity_scope == "source_local":
        findings.append(_finding("V6", "INVALID_IDENTITY_SCOPE", pointer + "/artifactScope", "source_artifact for source-local identity", node.get("artifactScope")))
    if node.get("origin") == "deferred_resolution":
        deferred_id = node.get("deferredRecordID")
        if deferred_id not in request.get("deferredRecordIDs", []):
            findings.append(_finding("V11", "DEFERRED_RECORD_NOT_IN_REQUEST", pointer + "/deferredRecordID", request.get("deferredRecordIDs", []), deferred_id))
    expected_provisional = bool(str(node.get("operationalTargetID", "")).endswith("NAMED-WITHOUT-EXACT-IDENTITY"))
    if bool(node.get("provisionalIdentity")) != expected_provisional:
        findings.append(_finding("V6", "INVALID_PROVISIONAL_IDENTITY", pointer + "/provisionalIdentity", expected_provisional, node.get("provisionalIdentity")))
    allowed_attributes = _authorized_attributes(target)
    source_exact_attributes = _source_exact_attribute_names(target)
    for index, attribute in enumerate(node.get("attributes", [])):
        attribute_pointer = f"{pointer}/attributes/{index}"
        if attribute.get("attributeName") not in allowed_attributes:
            findings.append(_finding("V6", "ATTRIBUTE_NOT_ALLOWED_FOR_TARGET", attribute_pointer + "/attributeName", sorted(allowed_attributes), attribute.get("attributeName")))
        findings.extend(_referenced_evidence_findings(attribute.get("evidenceSpanIDs", []), attribute_pointer + "/evidenceSpanIDs", evidence_validity, "ATTRIBUTE_EVIDENCE_MISSING", "ATTRIBUTE_EVIDENCE_MISSING", "V6"))
        attribute_name = attribute.get("attributeName")
        attribute_value = attribute.get("value")
        if attribute_name in source_exact_attributes and isinstance(attribute_value, str):
            cited_text = [
                str(evidence_by_id.get(reference, {}).get("evidenceText", ""))
                for reference in attribute.get("evidenceSpanIDs", [])
                if evidence_validity.get(reference, False)
            ]
            if not any(attribute_value in text for text in cited_text):
                findings.append(
                    _finding(
                        "V6",
                        "ATTRIBUTE_EVIDENCE_MISSING",
                        attribute_pointer + "/value",
                        "source-exact value present in cited attribute evidence",
                        attribute_value,
                    )
                )
    if isinstance(label, str) and label.count(". ") > 1:
        findings.append(_finding("V6", "ATOMICITY_VIOLATION", pointer + "/label", "one atomic semantic unit", label, severity="review"))
    normalized = node.get("normalizedLabelProposal")
    if normalized is None:
        normalization = ("not_applicable", None, "none", None)
    elif normalized == label:
        normalization = ("validated", normalized, "deterministic_rule", "exact_verbatim_identity_v0.1.0")
    else:
        normalization = ("pending_review", normalized, "llm_proposed_semantic", None)
        findings.append(_finding("V6", "SEMANTIC_NORMALIZATION_PENDING_REVIEW", pointer + "/normalizedLabelProposal", "approved deterministic normalization or later review", normalized, severity="info"))
    return findings, normalization[0], normalization[1], normalization[2], normalization[3]


def _resolve_endpoint(
    endpoint: Mapping[str, Any],
    pointer: str,
    request: Mapping[str, Any],
    node_by_id: Mapping[str, Mapping[str, Any]],
    node_status: Mapping[str, str],
) -> tuple[str | None, str | None, str | None, list[dict[str, Any]]]:
    """Resolve one V7 endpoint only through an explicitly authorized reference route."""

    reference_type = endpoint.get("referenceType")
    reference_id = endpoint.get("referenceID")
    findings: list[dict[str, Any]] = []
    if not reference_id:
        return None, None, None, [_finding("V7", "ENDPOINT_REFERENCE_MISSING", pointer, "explicit endpoint reference", reference_id)]
    resolved: Mapping[str, Any] | None = None
    if reference_type == "candidate_node":
        resolved = node_by_id.get(str(reference_id))
        if resolved is not None and node_status.get(str(reference_id)) not in {"validated", "needs_review"}:
            findings.append(_finding("V7", "ENDPOINT_LIFECYCLE_INVALID", pointer, "valid candidate endpoint", node_status.get(str(reference_id))))
    elif reference_type == "deterministic_node":
        rows = [row for row in request.get("deterministicEndpoints", []) if row.get("nodeID") == reference_id]
        if len(rows) == 1:
            resolved = rows[0]
        elif len(rows) > 1:
            findings.append(_finding("V7", "ENDPOINT_REFERENCE_AMBIGUOUS", pointer, "one deterministic endpoint", len(rows)))
    elif reference_type == "accepted_local_candidate":
        rows = [row for row in request.get("acceptedLocalCandidateEndpoints", []) if row.get("candidateID") == reference_id]
        if len(rows) == 1:
            resolved = rows[0]
        elif len(rows) > 1:
            findings.append(_finding("V7", "ENDPOINT_REFERENCE_AMBIGUOUS", pointer, "one accepted local endpoint", len(rows)))
    if resolved is None and not findings:
        findings.append(_finding("V7", "ENDPOINT_REFERENCE_MISSING", pointer, "authorized request endpoint", reference_id))
    class_name = resolved.get("className") if resolved else None
    if resolved is not None and not class_name:
        findings.append(_finding("V7", "ENDPOINT_CLASS_UNRESOLVED", pointer, "endpoint className", class_name))
    artifact_id: str | None = None
    if resolved is not None:
        trusted_artifact = resolved.get("artifactID")
        if reference_type == "candidate_node":
            if resolved.get("artifactScope") == "source_artifact":
                trusted_artifact = request["sourceArtifactID"]
            elif resolved.get("artifactScope") == "external_artifact":
                trusted_artifact = f"external-candidate:{reference_id}"
        if trusted_artifact is not None:
            artifact_id = str(trusted_artifact)
        authored_artifact = endpoint.get("artifactID")
        if authored_artifact is not None and authored_artifact != artifact_id:
            findings.append(
                _finding(
                    "V7",
                    "RELATION_SCOPE_MISMATCH",
                    pointer + "/artifactID",
                    artifact_id,
                    authored_artifact,
                )
            )
    return str(reference_id), str(class_name) if class_name else None, artifact_id, findings


def _signature_allows(class_name: str | None, constraint: Mapping[str, Any]) -> bool:
    """Evaluate a class against one frozen operational signature constraint."""

    return class_name is not None and class_name in set(constraint.get("classes", []))


def _edge_findings(
    edge: Mapping[str, Any],
    pointer: str,
    target: Mapping[str, Any] | None,
    request: Mapping[str, Any],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    evidence_validity: Mapping[str, bool],
    node_by_id: Mapping[str, Mapping[str, Any]],
    node_status: Mapping[str, str],
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Apply V7 endpoint and V8 operational signature, scope, and evidence rules."""

    findings = _referenced_evidence_findings(edge.get("evidenceSpanIDs", []), pointer + "/evidenceSpanIDs", evidence_validity, "EDGE_EVIDENCE_MISSING", "EDGE_EVIDENCE_INVALID", "V8")
    if edge.get("origin") == "deferred_resolution":
        deferred_id = edge.get("deferredRecordID")
        if deferred_id not in request.get("deferredRecordIDs", []):
            findings.append(_finding("V11", "DEFERRED_RECORD_NOT_IN_REQUEST", pointer + "/deferredRecordID", request.get("deferredRecordIDs", []), deferred_id))
    source_id, source_class, source_artifact, source_findings = _resolve_endpoint(edge.get("source", {}), pointer + "/source", request, node_by_id, node_status)
    target_id, target_class, target_artifact, target_findings = _resolve_endpoint(edge.get("target", {}), pointer + "/target", request, node_by_id, node_status)
    findings.extend(source_findings)
    findings.extend(target_findings)
    if target is not None and source_class and target_class:
        signatures = target.get("operational_signatures", [])
        domain_match = any(_signature_allows(source_class, item["domain"]) for item in signatures)
        range_match = any(_signature_allows(target_class, item["range"]) for item in signatures)
        pair_match = any(_signature_allows(source_class, item["domain"]) and _signature_allows(target_class, item["range"]) for item in signatures)
        if not domain_match:
            findings.append(_finding("V8", "INVALID_DOMAIN", pointer + "/source", [item["domain"]["classes"] for item in signatures], source_class))
        if not range_match:
            findings.append(_finding("V8", "INVALID_RANGE", pointer + "/target", [item["range"]["classes"] for item in signatures], target_class))
        if domain_match and range_match and not pair_match:
            findings.append(_finding("V8", "UNAUTHORIZED_RELATION_BRANCH", pointer, "one exact operational signature", [source_class, target_class]))
    if source_artifact is not None and target_artifact is not None:
        expected_scope = "intra_source" if source_artifact == target_artifact else "inter_source"
        if edge.get("relationScope") != expected_scope:
            findings.append(_finding("V8", "RELATION_SCOPE_MISMATCH", pointer + "/relationScope", expected_scope, edge.get("relationScope")))
    evidence_text = " ".join(str(evidence_by_id.get(ref, {}).get("evidenceText", "")) for ref in edge.get("evidenceSpanIDs", []))
    lowered = evidence_text.casefold()
    if edge.get("relationName") == "supports" and any(token in lowered for token in ("does not support", "not support", "refutes")):
        findings.append(_finding("V8", "NEGATIVE_SUPPORT_NOT_AUTHORIZED", pointer, "positive support", evidence_text))
    return findings, source_id, target_id


def _precedence_map(profile: Mapping[str, Any]) -> dict[str, str]:
    """Derive weaker-to-stronger relation roles from frozen profile global rules."""

    rules = profile["global_rules"]["use_mention_reference_precedence"]
    derived: dict[str, str] = {}
    for stronger, description in rules.items():
        if "_and_" in stronger or description == "may coexist":
            continue
        marker = "supersedes "
        if marker in description:
            weaker = description.split(marker, 1)[1].split(" ", 1)[0]
            derived[weaker] = stronger
        elif stronger == "hasCodeRepository" and "referencesRepository" in description:
            derived["referencesRepository"] = stronger
    return derived


def _duplicate_key(
    record: Mapping[str, Any],
    source_artifact_id: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    *,
    edge: bool,
) -> bytes:
    """Build the exact frozen V10 duplicate projection for one candidate."""

    coordinates = sorted(
        (
            evidence_by_id.get(reference, {}).get("sourceUnitID"),
            evidence_by_id.get(reference, {}).get("startOffsetInUnit"),
            evidence_by_id.get(reference, {}).get("endOffsetInUnit"),
        )
        for reference in record.get("evidenceSpanIDs", [])
    )
    if edge:
        projection = {
            "sourceArtifactID": source_artifact_id,
            "operationalRelationID": record.get("operationalRelationID"),
            "action": record.get("action"),
            "source": record.get("source"),
            "target": record.get("target"),
            "evidenceCoordinates": coordinates,
        }
    else:
        projection = {
            "sourceArtifactID": source_artifact_id,
            "operationalTargetID": record.get("operationalTargetID"),
            "action": record.get("action"),
            "existingNodeID": record.get("existingNodeID"),
            "label": record.get("label"),
            "attributes": record.get("attributes", []),
            "evidenceCoordinates": coordinates,
        }
    return canonical_json(projection)


def _base_result(
    request: Mapping[str, Any],
    envelope: Mapping[str, Any],
    record_type: str,
    record_id: str,
    record: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Construct common deterministic provenance for one validation record."""

    authorities = request["authorities"]
    return {
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "ruleVersion": RULE_VERSION,
        "requestID": request["requestID"],
        "requestSha256": request["requestInputSha256"],
        "outputID": envelope.get("metadata", {}).get("outputID"),
        "parsedOutputSha256": sha256_bytes(canonical_json(envelope)),
        "recordType": record_type,
        "recordID": record_id,
        "findings": list(findings),
        "inputRecordHash": sha256_bytes(canonical_json(record)),
        "ontologySha256": authorities["ontology"]["validatedOwlSha256"],
        "targetInventorySha256": authorities["targetInventory"]["sha256"],
        "sourceUnitContractSha256": authorities["sourceUnitContract"]["sha256"],
        "candidateSchemaSha256": authorities["candidateSchema"]["sha256"],
    }


def validate_candidate_envelope(
    parser_result: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    """Execute frozen V1-V12 validation and return deterministic result records."""

    if parser_result.get("parseStatus") != "parsed":
        code = str(parser_result.get("processingCode") or "INVALID_JSON")
        if code not in PROCESSING_CODES:
            code = "INVALID_JSON"
        processing = {
            "validationContractVersion": VALIDATION_CONTRACT_VERSION,
            "validatorVersion": VALIDATOR_VERSION,
            "ruleVersion": RULE_VERSION,
            "requestID": request["requestID"],
            "requestSha256": request["requestInputSha256"],
            "recordType": "processing_failure",
            "recordID": "processing-failure-0001",
            "recordValidationStatus": "processing_failed",
            "findings": [_finding("V1", code, "", "strict JSON response", parser_result.get("error"))],
            "inputRecordHash": sha256_bytes(canonical_json(dict(parser_result))),
        }
        return {
            "validationContractVersion": VALIDATION_CONTRACT_VERSION,
            "validatorVersion": VALIDATOR_VERSION,
            "envelopeStatus": "processing_failed",
            "recordResults": [_finish_result(processing)],
            "validationResultsHash": "",
        } | {
            "validationResultsHash": sha256_bytes(canonical_json([_finish_result(processing)]))
        }

    parsed_document = parser_result["parsedEnvelope"]
    envelope: Mapping[str, Any] = (
        parsed_document if isinstance(parsed_document, Mapping) else {}
    )
    schema = load_json_object(CANDIDATE_SCHEMA_PATH)
    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    ontology = load_yaml_object(ONTOLOGY_SPEC_PATH)
    if not ontology.get("classes") or not ontology.get("relations"):
        raise ValueError("frozen ontology specification is incomplete")
    schema_validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    schema_errors = sorted(schema_validator.iter_errors(parsed_document), key=lambda error: list(error.absolute_path))
    global_findings: list[dict[str, Any]] = _parser_binding_findings(parser_result)
    for error in schema_errors:
        pointer = "".join(f"/{part}" for part in error.absolute_path)
        code = "FORBIDDEN_FIELD" if error.validator == "additionalProperties" else "SCHEMA_VALIDATION_FAILED"
        global_findings.append(_finding("V2", code, pointer, error.validator_value, error.message))
    raw_hash = str(parser_result["rawResponseSha256"])
    if isinstance(parsed_document, Mapping):
        global_findings.extend(_metadata_binding_findings(envelope, request, raw_hash))

    canonical_document = _canonical_document(request)
    if sha256_bytes(canonical_document.encode("utf-8")) != request["sourceUnit"]["canonicalTextSha256"]:
        global_findings.append(_finding("V4", "SOURCE_UNIT_HASH_MISMATCH", "/sourceUnit/canonicalTextSha256", request["sourceUnit"]["canonicalTextSha256"], sha256_bytes(canonical_document.encode("utf-8"))))
    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    evidence_validity: dict[str, bool] = {}
    evidence_findings: dict[str, list[dict[str, Any]]] = {}
    evidence_counts = Counter(str(row.get("evidenceSpanID")) for row in envelope.get("evidenceSpans", []) if isinstance(row, dict))
    for index, evidence in enumerate(envelope.get("evidenceSpans", [])):
        if not isinstance(evidence, dict):
            continue
        evidence_id = str(evidence.get("evidenceSpanID"))
        pointer = f"/evidenceSpans/{index}"
        valid, findings = _validate_evidence(evidence, pointer, request, canonical_document)
        if evidence_counts[evidence_id] > 1:
            findings.append(_finding("V4", "EVIDENCE_SPAN_ID_DUPLICATE", pointer + "/evidenceSpanID", "unique evidence ID", evidence_id))
            valid = False
        evidence_by_id[evidence_id] = evidence
        evidence_validity[evidence_id] = valid
        evidence_findings[evidence_id] = findings
    evidence_coordinate_seen: dict[tuple[Any, Any, Any], str] = {}
    for evidence_id in sorted(evidence_by_id):
        evidence_row = evidence_by_id[evidence_id]
        coordinate_key = (
            evidence_row.get("sourceUnitID"),
            evidence_row.get("startOffsetInUnit"),
            evidence_row.get("endOffsetInUnit"),
        )
        if coordinate_key in evidence_coordinate_seen:
            evidence_findings[evidence_id].append(
                _finding(
                    "V10",
                    "EXACT_DUPLICATE_EVIDENCE_SPAN",
                    "/evidenceSpans",
                    evidence_coordinate_seen[coordinate_key],
                    evidence_id,
                    severity="suppression",
                )
            )
        else:
            evidence_coordinate_seen[coordinate_key] = evidence_id

    node_targets, relation_targets = _target_indexes(profile)
    node_by_id = {str(row.get("candidateID")): row for row in envelope.get("candidateNodes", []) if isinstance(row, dict)}
    candidate_counts = Counter(
        str(row.get("candidateID"))
        for group in (envelope.get("candidateNodes", []), envelope.get("candidateEdges", []))
        for row in group
        if isinstance(row, dict)
    )
    candidates_by_id: dict[str, list[Mapping[str, Any]]] = {}
    for group in (envelope.get("candidateNodes", []), envelope.get("candidateEdges", [])):
        for candidate in group:
            if isinstance(candidate, dict):
                candidates_by_id.setdefault(str(candidate.get("candidateID")), []).append(candidate)
    record_results: list[dict[str, Any]] = []
    node_status: dict[str, str] = {}
    node_result_indexes: dict[str, int] = {}
    for index, node in enumerate(envelope.get("candidateNodes", [])):
        if not isinstance(node, dict):
            continue
        candidate_id = str(node.get("candidateID"))
        pointer = f"/candidateNodes/{index}"
        target = node_targets.get(str(node.get("operationalTargetID")))
        findings = _authorization_findings(node, pointer, target, request, edge=False)
        if candidate_counts[candidate_id] > 1:
            findings.append(_finding("V5", "CANDIDATE_ID_DUPLICATE", pointer + "/candidateID", "unique candidate ID", candidate_id))
            if len({canonical_json(row) for row in candidates_by_id[candidate_id]}) > 1:
                findings.append(_finding("V10", "INCOMPATIBLE_DUPLICATE_ID", pointer + "/candidateID", "one material record per candidate ID", candidate_id))
        node_values = _node_findings(node, pointer, target, request, evidence_by_id, evidence_validity)
        findings.extend(node_values[0])
        hard = any(item["code"] in HARD_FINDING_CODES for item in findings) or bool(schema_errors) or any(item["code"] in HARD_FINDING_CODES for item in global_findings)
        review = any(item["severity"] == "review" for item in findings)
        status = "rejected" if hard else "needs_review" if review else "validated"
        result = _base_result(request, envelope, "candidate_node", candidate_id, node, findings)
        result.update({
            "candidateValidationStatus": status,
            "normalizationStatus": node_values[1],
            "normalizedLabel": node_values[2],
            "normalizationMethod": node_values[3],
            "normalizationRuleID": node_values[4],
            "validatedEvidenceSpanIDs": [ref for ref in node.get("evidenceSpanIDs", []) if evidence_validity.get(ref)],
            "resolvedSourceEndpointID": None,
            "resolvedTargetEndpointID": None,
            "supersededByRecordID": None,
        })
        node_status[candidate_id] = status
        node_result_indexes[candidate_id] = len(record_results)
        record_results.append(result)

    for index, edge in enumerate(envelope.get("candidateEdges", [])):
        if not isinstance(edge, dict):
            continue
        candidate_id = str(edge.get("candidateID"))
        pointer = f"/candidateEdges/{index}"
        target = relation_targets.get(str(edge.get("operationalRelationID")))
        findings = _authorization_findings(edge, pointer, target, request, edge=True)
        if candidate_counts[candidate_id] > 1:
            findings.append(_finding("V5", "CANDIDATE_ID_DUPLICATE", pointer + "/candidateID", "unique candidate ID", candidate_id))
            if len({canonical_json(row) for row in candidates_by_id[candidate_id]}) > 1:
                findings.append(_finding("V10", "INCOMPATIBLE_DUPLICATE_ID", pointer + "/candidateID", "one material record per candidate ID", candidate_id))
        edge_values = _edge_findings(edge, pointer, target, request, evidence_by_id, evidence_validity, node_by_id, node_status)
        findings.extend(edge_values[0])
        hard = any(item["code"] in HARD_FINDING_CODES for item in findings) or bool(schema_errors) or any(item["code"] in HARD_FINDING_CODES for item in global_findings)
        status = "rejected" if hard else "validated"
        result = _base_result(request, envelope, "candidate_edge", candidate_id, edge, findings)
        result.update({
            "candidateValidationStatus": status,
            "validatedEvidenceSpanIDs": [ref for ref in edge.get("evidenceSpanIDs", []) if evidence_validity.get(ref)],
            "resolvedSourceEndpointID": edge_values[1],
            "resolvedTargetEndpointID": edge_values[2],
            "supersededByRecordID": None,
        })
        record_results.append(result)

    candidate_records = [*envelope.get("candidateNodes", []), *envelope.get("candidateEdges", [])]
    candidate_results = [result for result in record_results if result["recordType"] in {"candidate_node", "candidate_edge"}]
    duplicate_seen: dict[tuple[str, bytes], str] = {}
    for record, result in zip(candidate_records, candidate_results):
        if result["candidateValidationStatus"] != "validated":
            continue
        is_edge = result["recordType"] == "candidate_edge"
        key = (
            result["recordType"],
            _duplicate_key(
                record,
                request["sourceArtifactID"],
                evidence_by_id,
                edge=is_edge,
            ),
        )
        if key in duplicate_seen:
            code = "EXACT_DUPLICATE_EDGE" if is_edge else "EXACT_DUPLICATE_NODE"
            result["candidateValidationStatus"] = "superseded"
            result["supersededByRecordID"] = duplicate_seen[key]
            result["findings"].append(_finding("V10", code, "", duplicate_seen[key], result["recordID"], severity="suppression"))
        else:
            duplicate_seen[key] = result["recordID"]

    node_records = list(envelope.get("candidateNodes", []))
    node_results = [result for result in candidate_results if result["recordType"] == "candidate_node"]
    for later_index, (later_record, later_result) in enumerate(zip(node_records, node_results)):
        if later_result["candidateValidationStatus"] != "validated":
            continue
        for earlier_record, earlier_result in zip(node_records[:later_index], node_results[:later_index]):
            if earlier_result["candidateValidationStatus"] not in {"validated", "superseded"}:
                continue
            same_core = (
                later_record.get("operationalTargetID") == earlier_record.get("operationalTargetID")
                and later_record.get("action") == earlier_record.get("action")
                and later_record.get("existingNodeID") == earlier_record.get("existingNodeID")
                and later_record.get("attributes", []) == earlier_record.get("attributes", [])
            )
            if not same_core:
                continue
            target = node_targets.get(str(later_record.get("operationalTargetID")))
            if _is_contextual_occurrence_target(target):
                continue
            if later_record.get("label") == earlier_record.get("label"):
                later_result["candidateValidationStatus"] = "superseded"
                later_result["supersededByRecordID"] = earlier_result["recordID"]
                later_result["findings"].append(_finding("V10", "REPEATED_LOCAL_CANDIDATE_EVIDENCE_MERGED", "", earlier_result["recordID"], later_result["recordID"], severity="suppression"))
            elif str(later_record.get("label", "")).casefold() == str(earlier_record.get("label", "")).casefold():
                later_result["candidateValidationStatus"] = "needs_review"
                later_result["findings"].append(_finding("V10", "POSSIBLE_LOCAL_DUPLICATE", "", earlier_result["recordID"], later_result["recordID"], severity="review"))
            if later_result["candidateValidationStatus"] != "validated":
                break

    precedence = _precedence_map(profile)
    edge_records = list(envelope.get("candidateEdges", []))
    edge_results = [result for result in candidate_results if result["recordType"] == "candidate_edge"]
    for weak_record, weak_result in zip(edge_records, edge_results):
        stronger = precedence.get(weak_record.get("relationName"))
        if not stronger or weak_result["candidateValidationStatus"] != "validated":
            continue
        for strong_record, strong_result in zip(edge_records, edge_results):
            if strong_result["candidateValidationStatus"] != "validated" or strong_record.get("relationName") != stronger:
                continue
            if weak_record.get("source") == strong_record.get("source") and weak_record.get("target") == strong_record.get("target"):
                weak_result["candidateValidationStatus"] = "superseded"
                weak_result["supersededByRecordID"] = strong_result["recordID"]
                weak_result["findings"].append(_finding("V9", "WEAKER_RELATION_SUPERSEDED", "", stronger, weak_record.get("relationName"), severity="suppression"))
                break

    used_evidence = {
        ref
        for group in (envelope.get("candidateNodes", []), envelope.get("candidateEdges", []), envelope.get("abstentions", []), envelope.get("deferredRecords", []))
        for record in group
        if isinstance(record, dict)
        for ref in record.get("evidenceSpanIDs", [])
    }
    for evidence_id, findings in evidence_findings.items():
        if evidence_id not in used_evidence:
            findings.append(_finding("V4", "UNREFERENCED_EVIDENCE_SPAN", "/evidenceSpans", "referenced evidence", evidence_id, severity="warning"))

    valid_candidate_ids = {result["recordID"] for result in candidate_results if result["candidateValidationStatus"] == "validated"}
    abstention_reasons = set(profile["semantic_abstention_reasons"])
    abstention_scopes = set(schema["$defs"]["abstention"]["properties"]["scope"]["enum"])
    for index, abstention in enumerate(envelope.get("abstentions", [])):
        if not isinstance(abstention, dict):
            continue
        pointer = f"/abstentions/{index}"
        findings: list[dict[str, Any]] = []
        if abstention.get("reason") not in abstention_reasons:
            findings.append(_finding("V11", "ABSTENTION_REASON_INVALID", pointer + "/reason", sorted(abstention_reasons), abstention.get("reason")))
        if abstention.get("reason") in {value.casefold() for value in PROCESSING_CODES}:
            findings.append(_finding("V11", "PROCESSING_FAILURE_MISCLASSIFIED_AS_ABSTENTION", pointer + "/reason", "semantic abstention reason", abstention.get("reason")))
        if abstention.get("scope") not in abstention_scopes:
            findings.append(_finding("V11", "ABSTENTION_SCOPE_INVALID", pointer + "/scope", sorted(abstention_scopes), abstention.get("scope")))
        target_id = abstention.get("operationalTargetID")
        if target_id is not None and target_id not in request["eligibleOperationalTargetIDs"]:
            findings.append(_finding("V11", "ABSTENTION_TARGET_MISMATCH", pointer + "/operationalTargetID", request["eligibleOperationalTargetIDs"], target_id))
        invalid_refs = [ref for ref in abstention.get("evidenceSpanIDs", []) if not evidence_validity.get(ref, False)]
        if invalid_refs:
            findings.append(_finding("V11", "ABSTENTION_EVIDENCE_INVALID", pointer + "/evidenceSpanIDs", "valid optional evidence", invalid_refs))
        status = "rejected" if any(item["code"] in HARD_FINDING_CODES for item in findings) or bool(schema_errors) else "validated"
        result = _base_result(request, envelope, "abstention", str(abstention.get("abstentionID")), abstention, findings)
        result["recordValidationStatus"] = status
        record_results.append(result)

    dispositions = {"resolved_accepted", "resolved_rejected", "remain_deferred", "insufficient_evidence", "out_of_scope", "type_conflict", "unsupported_role"}
    trusted_deferred = {str(row.get("deferredRecordID")): row for row in request.get("deferredRecords", [])}
    for index, deferred in enumerate(envelope.get("deferredRecords", [])):
        if not isinstance(deferred, dict):
            continue
        pointer = f"/deferredRecords/{index}"
        deferred_id = str(deferred.get("deferredRecordID"))
        findings: list[dict[str, Any]] = []
        if deferred_id not in request.get("deferredRecordIDs", []):
            findings.append(_finding("V11", "DEFERRED_RECORD_NOT_IN_REQUEST", pointer + "/deferredRecordID", request.get("deferredRecordIDs", []), deferred_id))
        elif deferred_id not in trusted_deferred:
            findings.append(_finding("V11", "DEFERRED_RECORD_NOT_FOUND", pointer + "/deferredRecordID", sorted(trusted_deferred), deferred_id))
        if deferred.get("proposedDisposition") not in dispositions:
            findings.append(_finding("V11", "DEFERRED_DISPOSITION_INVALID", pointer + "/proposedDisposition", sorted(dispositions), deferred.get("proposedDisposition")))
        related = set(deferred.get("relatedCandidateIDs", []))
        candidate_by_id = {
            str(record.get("candidateID")): record
            for record in candidate_records
            if isinstance(record, dict)
        }
        mismatched = sorted(
            candidate_id
            for candidate_id in related
            if candidate_id not in candidate_by_id
            or candidate_by_id[candidate_id].get("deferredRecordID") != deferred_id
        )
        if mismatched:
            findings.append(_finding("V11", "DEFERRED_CANDIDATE_MISMATCH", pointer + "/relatedCandidateIDs", deferred_id, mismatched))
        if deferred.get("proposedDisposition") == "resolved_accepted" and not related.intersection(valid_candidate_ids):
            findings.append(_finding("V11", "DEFERRED_ACCEPTED_WITHOUT_VALIDATED_CANDIDATE", pointer + "/relatedCandidateIDs", sorted(valid_candidate_ids), sorted(related)))
        status = "rejected" if any(item["code"] in HARD_FINDING_CODES for item in findings) or bool(schema_errors) else "deferred" if deferred.get("proposedDisposition") in {"remain_deferred", "insufficient_evidence", "type_conflict", "unsupported_role"} else "validated"
        result = _base_result(request, envelope, "deferred_record", deferred_id, deferred, findings)
        result["recordValidationStatus"] = status
        record_results.append(result)
        if status == "deferred":
            for candidate_result in candidate_results:
                if (
                    candidate_result["recordID"] in related
                    and candidate_result["candidateValidationStatus"] == "validated"
                ):
                    candidate_result["candidateValidationStatus"] = "deferred"

    active_node_ids = {
        result["recordID"]
        for result in candidate_results
        if result["recordType"] == "candidate_node"
        and result["candidateValidationStatus"] == "validated"
    }
    for edge_record, edge_result in zip(edge_records, edge_results):
        if edge_result["candidateValidationStatus"] != "validated":
            continue
        inactive_endpoints = sorted(
            str(endpoint.get("referenceID"))
            for endpoint in (edge_record.get("source", {}), edge_record.get("target", {}))
            if endpoint.get("referenceType") == "candidate_node"
            and str(endpoint.get("referenceID")) not in active_node_ids
        )
        if inactive_endpoints:
            edge_result["candidateValidationStatus"] = "rejected"
            edge_result["findings"].append(
                _finding(
                    "V12",
                    "ENDPOINT_LIFECYCLE_INVALID",
                    "",
                    "validated active candidate endpoints",
                    inactive_endpoints,
                )
            )

    for index, result in enumerate(record_results):
        record_results[index] = _finish_result(result)
    candidate_statuses = [result["candidateValidationStatus"] for result in record_results if "candidateValidationStatus" in result]
    hard_global = bool(schema_errors) or any(item["code"] in HARD_FINDING_CODES for item in global_findings)
    if hard_global or (
        candidate_statuses
        and all(status in {"rejected", "needs_review"} for status in candidate_statuses)
    ):
        envelope_status = "invalid"
    elif any(status == "validated" for status in candidate_statuses) and any(
        status in {"rejected", "needs_review", "deferred"}
        for status in candidate_statuses
    ):
        envelope_status = "partially_valid"
    else:
        envelope_status = "valid"
    validation: dict[str, Any] = {
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "ruleVersion": RULE_VERSION,
        "requestID": request["requestID"],
        "requestSha256": request["requestInputSha256"],
        "outputID": envelope.get("metadata", {}).get("outputID"),
        "parsedOutputSha256": sha256_bytes(canonical_json(parsed_document)),
        "envelopeStatus": envelope_status,
        "globalFindings": global_findings,
        "evidenceResults": [
            {
                "evidenceSpanID": evidence_id,
                "valid": evidence_validity[evidence_id],
                "computedEvidenceHash": sha256_bytes(str(evidence_by_id[evidence_id].get("evidenceText", "")).encode("utf-8")),
                "findings": evidence_findings[evidence_id],
            }
            for evidence_id in sorted(evidence_by_id)
        ],
        "recordResults": record_results,
    }
    validation["validationResultsHash"] = sha256_bytes(canonical_json(validation))
    return validation


def materialize_usable_pipeline_output(
    envelope: Mapping[str, Any], validation: Mapping[str, Any]
) -> dict[str, Any]:
    """Materialize only V12-validated active candidates before adjudication."""

    statuses = {
        result["recordID"]: result.get("candidateValidationStatus")
        for result in validation.get("recordResults", [])
        if result.get("recordType") in {"candidate_node", "candidate_edge"}
    }
    active_node_ids = {
        row.get("candidateID")
        for row in envelope.get("candidateNodes", [])
        if statuses.get(row.get("candidateID")) == "validated"
    }

    def edge_dependencies_are_active(edge: Mapping[str, Any]) -> bool:
        """Return whether every candidate-node endpoint remains V12 active."""

        return all(
            endpoint.get("referenceType") != "candidate_node"
            or endpoint.get("referenceID") in active_node_ids
            for endpoint in (edge.get("source", {}), edge.get("target", {}))
        )

    usable = {
        "outputStage": "usable_pipeline_output",
        "requestID": validation.get("requestID"),
        "outputID": validation.get("outputID"),
        "validationResultsHash": validation.get("validationResultsHash"),
        "candidateNodes": [deepcopy(row) for row in envelope.get("candidateNodes", []) if statuses.get(row.get("candidateID")) == "validated"],
        "candidateEdges": [
            deepcopy(row)
            for row in envelope.get("candidateEdges", [])
            if statuses.get(row.get("candidateID")) == "validated"
            and edge_dependencies_are_active(row)
        ],
    }
    usable["usablePipelineOutputHash"] = sha256_bytes(canonical_json(usable))
    return usable
