"""Backend semantic, context, attribute, endpoint, and evidence validation."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Mapping, Sequence

from . import (
    ANNOTATION_OUTPUT_SCHEMA_VERSION,
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    GUIDELINE_VERSION,
    HANDBOOK_VERSION,
    INTERFACE_VERSION,
    ROUTING_VERSION,
)
from .contracts import AnnotationContractError, AnnotationContracts


NODE_ID = re.compile(r"^node-[0-9]{4}$")
EDGE_ID = re.compile(r"^edge-[0-9]{4}$")
ALLOWED_INPUT_FIELDS = {"workflowState", "nodes", "relations", "targetStates", "uncertainties"}
FORBIDDEN_FIELDS = {
    "model", "modelname", "prompt", "rawresponse", "gold", "goldlabel", "agreement", "disagreement",
    "adjudicatedanswer", "aggregatepositivecount", "sameas", "archivedas", "mergewith", "consolidatesto",
    "confidence", "probability", "experimentarm", "negativeassertion",
}
WORKFLOW_STATES = {"reading", "node_pass", "relation_pass", "review", "submitted", "reopened"}
UNCERTAINTY_CATEGORIES = {
    "ambiguous_class", "ambiguous_relation", "ambiguous_atomicity", "insufficient_evidence",
    "unresolved_endpoint", "source_conversion_problem", "possible_local_duplicate", "target_boundary_unclear",
}
AUTHORIZED_ATTRIBUTES = {
    "EvaluationMetric": {"value"},
    "Parameter": {"value", "range", "calibrationStatus"},
    "Repository": {"fork", "commitSHA"},
}
EXTERNAL_ARTIFACT_CLASSES = {"DatasetMention", "DatasetResource", "Repository", "Tool"}
DOCUMENT_CONTEXT_REASONS = {
    "distributed_assertion_evidence", "cross_section_coreference",
    "relation_endpoint_reconciliation", "document_local_entity_reconciliation",
}


def _reject_forbidden_fields(value: object) -> None:
    """Reject model, gold, negative, consolidation, and feedback fields recursively."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).replace("_", "").lower() in FORBIDDEN_FIELDS:
                raise AnnotationContractError(f"ANNOTATION_FORBIDDEN_FIELD:{key}")
            _reject_forbidden_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_forbidden_fields(nested)


def _require_list(value: object, code: str) -> list[Any]:
    """Return a list or raise one stable code."""

    if not isinstance(value, list):
        raise AnnotationContractError(code)
    return value


def _evidence(
    raw: object, *, contracts: AnnotationContracts, primary_source_unit_id: str,
    exposed_context_ids: Sequence[str],
) -> dict[str, Any]:
    """Validate one source-unit-bound code-point span and both canonical slices."""

    if not isinstance(raw, Mapping):
        raise AnnotationContractError("ANNOTATION_EVIDENCE_OBJECT_REQUIRED")
    fields = {"sourceUnitID", "sourceUnitTextHash", "startOffset", "endOffset", "exactText"}
    if set(raw) != fields:
        raise AnnotationContractError("ANNOTATION_EVIDENCE_FIELDS_INVALID")
    source_unit_id = raw["sourceUnitID"]
    if not isinstance(source_unit_id, str) or source_unit_id not in contracts.authorized_context_ids(
        primary_source_unit_id, exposed_context_ids
    ):
        raise AnnotationContractError("ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED")
    unit = contracts.units_by_id[source_unit_id]
    if raw["sourceUnitTextHash"] != unit["textHash"]:
        raise AnnotationContractError("ANNOTATION_EVIDENCE_SOURCE_UNIT_HASH_MISMATCH")
    source_text = contracts.source_text(source_unit_id)
    start, end, exact = raw["startOffset"], raw["endOffset"], raw["exactText"]
    if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
        raise AnnotationContractError("ANNOTATION_EVIDENCE_OFFSET_TYPE_INVALID")
    if start < 0 or end <= start or end > len(source_text):
        raise AnnotationContractError("ANNOTATION_EVIDENCE_CODEPOINT_RANGE_INVALID")
    if not isinstance(exact, str) or not exact:
        raise AnnotationContractError("ANNOTATION_EVIDENCE_TEXT_REQUIRED")
    if source_text[start:end] != exact:
        raise AnnotationContractError("ANNOTATION_EVIDENCE_EXACT_TEXT_MISMATCH")
    document_start = int(unit["startOffsetInDocument"]) + start
    document_end = int(unit["startOffsetInDocument"]) + end
    if contracts.canonical_document_text(source_unit_id)[document_start:document_end] != exact:
        raise AnnotationContractError("ANNOTATION_EVIDENCE_DOCUMENT_SLICE_MISMATCH")
    return {
        "sourceArtifactID": unit["canonicalArtifactID"], "sourceUnitID": source_unit_id,
        "sourceUnitTextHash": unit["textHash"], "canonicalDocumentHash": contracts.canonical_document_hash(source_unit_id),
        "sectionID": unit["sectionID"], "sectionTitle": unit.get("sectionTitleRaw"),
        "evidenceText": exact, "startOffsetInUnit": start, "endOffsetInUnit": end,
        "startOffsetInDocument": document_start, "endOffsetInDocument": document_end,
        "evidenceHash": hashlib.sha256(exact.encode("utf-8")).hexdigest(),
    }


def _mention_span(
    raw: object, *, contracts: AnnotationContracts, primary_source_unit_id: str,
    exposed_context_ids: Sequence[str],
) -> dict[str, Any]:
    """Validate the singular exact textual identity of a human-created node."""

    if not isinstance(raw, Mapping):
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_OBJECT_REQUIRED")
    fields = {"sourceUnitID", "sourceUnitTextHash", "startOffset", "endOffset", "exactText"}
    if set(raw) != fields:
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_FIELDS_INVALID")
    source_unit_id = raw["sourceUnitID"]
    if not isinstance(source_unit_id, str) or source_unit_id not in contracts.authorized_context_ids(
        primary_source_unit_id, exposed_context_ids
    ):
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_CONTEXT_NOT_AUTHORIZED")
    unit = contracts.units_by_id[source_unit_id]
    if raw["sourceUnitTextHash"] != unit["textHash"]:
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_SOURCE_UNIT_HASH_MISMATCH")
    source_text = contracts.source_text(source_unit_id)
    start, end, exact = raw["startOffset"], raw["endOffset"], raw["exactText"]
    if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_OFFSET_TYPE_INVALID")
    if start < 0 or end <= start or end > len(source_text):
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_CODEPOINT_RANGE_INVALID")
    if not isinstance(exact, str) or not exact:
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_TEXT_REQUIRED")
    if source_text[start:end] != exact:
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_EXACT_TEXT_MISMATCH")
    document_start = int(unit["startOffsetInDocument"]) + start
    document_end = int(unit["startOffsetInDocument"]) + end
    if contracts.canonical_document_text(source_unit_id)[document_start:document_end] != exact:
        raise AnnotationContractError("ANNOTATION_NODE_MENTION_DOCUMENT_SLICE_MISMATCH")
    return {
        "sourceArtifactID": unit["canonicalArtifactID"], "sourceUnitID": source_unit_id,
        "sourceUnitTextHash": unit["textHash"], "canonicalDocumentHash": contracts.canonical_document_hash(source_unit_id),
        "sectionID": unit["sectionID"], "sectionTitle": unit.get("sectionTitleRaw"),
        "exactText": exact, "startOffsetInUnit": start, "endOffsetInUnit": end,
        "startOffsetInDocument": document_start, "endOffsetInDocument": document_end,
        "spanHash": hashlib.sha256(exact.encode("utf-8")).hexdigest(),
    }


def _class_name(target: Mapping[str, Any]) -> str:
    """Return the one concrete formal class for a node target."""

    classes = target.get("formal_classes", [])
    if len(classes) != 1 or not target.get("direct_instantiation"):
        raise AnnotationContractError("ANNOTATION_ABSTRACT_NODE_TARGET_FORBIDDEN")
    return str(classes[0]["name"])


def _endpoint_matches(actual: str, specification: Mapping[str, Any], expansions: Mapping[str, Sequence[str]]) -> bool:
    """Check an endpoint class against one accepted operational signature side."""

    classes = [str(value) for value in specification.get("classes", [])]
    if specification.get("match") == "any" or "owl:Thing" in classes:
        return True
    allowed = set(classes)
    for class_name in classes:
        allowed.update(expansions.get(class_name, ()))
    return actual in allowed


def _endpoint(
    endpoint_id: object, node_classes: Mapping[str, str], node_artifact_scopes: Mapping[str, str],
    deterministic: Mapping[str, Mapping[str, str]], source_artifact_id: str,
) -> tuple[dict[str, Any], str, bool]:
    """Resolve a local candidate or exact deterministic endpoint and artifact scope."""

    if not isinstance(endpoint_id, str) or not endpoint_id:
        raise AnnotationContractError("ANNOTATION_RELATION_ENDPOINT_MISSING")
    if endpoint_id in node_classes:
        return (
            {"referenceType": "candidate_node", "referenceID": endpoint_id, "artifactID": None},
            node_classes[endpoint_id], node_artifact_scopes[endpoint_id] == "external_artifact",
        )
    if endpoint_id in deterministic:
        item = deterministic[endpoint_id]
        return (
            {"referenceType": "deterministic_node", "referenceID": endpoint_id, "artifactID": item["artifactID"]},
            item["className"], item["artifactID"] != source_artifact_id,
        )
    raise AnnotationContractError(f"ANNOTATION_RELATION_ENDPOINT_UNKNOWN:{endpoint_id}")


def _discovery(
    contracts: AnnotationContracts, primary_source_unit_id: str, evidence_rows: Sequence[Mapping[str, Any]],
    supplied_scope: object, distributed_reason: object, exposed_context_ids: Sequence[str],
) -> tuple[str, str | None]:
    """Derive and validate discovery scope and distributed-support rationale."""

    unit_ids = [str(row["sourceUnitID"]) for row in evidence_rows]
    scope = contracts.discovery_scope(primary_source_unit_id, unit_ids, exposed_context_ids)
    if supplied_scope not in (None, "") and supplied_scope != scope:
        raise AnnotationContractError("ANNOTATION_DISCOVERY_SCOPE_MISMATCH")
    distributed = len(set(unit_ids)) > 1
    if distributed:
        if not isinstance(distributed_reason, str) or not distributed_reason.strip():
            raise AnnotationContractError("ANNOTATION_DISTRIBUTED_EVIDENCE_REASON_REQUIRED")
        return scope, distributed_reason.strip()
    if distributed_reason not in (None, ""):
        raise AnnotationContractError("ANNOTATION_DISTRIBUTED_EVIDENCE_REASON_NOT_APPLICABLE")
    return scope, None


def _attributes(
    raw_attributes: object, class_name: str,
    register: Callable[[object], tuple[str, Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[Mapping[str, Any]]]:
    """Validate the six frozen structured attributes and their independent evidence."""

    rows = _require_list(raw_attributes, "ANNOTATION_NODE_ATTRIBUTES_ARRAY_REQUIRED")
    allowed = AUTHORIZED_ATTRIBUTES.get(class_name, set())
    seen: set[str] = set(); cleaned: list[dict[str, Any]] = []; evidence_rows: list[Mapping[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or set(raw) != {"attributeName", "value", "evidence"}:
            raise AnnotationContractError("ANNOTATION_NODE_ATTRIBUTE_FIELDS_INVALID")
        name, value = raw["attributeName"], raw["value"]
        if name not in {"value", "range", "calibrationStatus", "fork", "commitSHA"}:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_UNSUPPORTED:{name}")
        if name not in allowed:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_CLASS_INCOMPATIBLE:{class_name}:{name}")
        if name in seen:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_DUPLICATE:{name}")
        if name == "fork":
            if not isinstance(value, bool):
                raise AnnotationContractError("ANNOTATION_NODE_ATTRIBUTE_VALUE_INVALID:fork")
        elif name == "calibrationStatus":
            if value not in {"calibrated", "default"}:
                raise AnnotationContractError("ANNOTATION_NODE_ATTRIBUTE_VALUE_INVALID:calibrationStatus")
        elif not isinstance(value, str) or not value:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_VALUE_INVALID:{name}")
        raw_evidence = _require_list(raw["evidence"], "ANNOTATION_NODE_ATTRIBUTE_EVIDENCE_ARRAY_REQUIRED")
        if not raw_evidence:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_EVIDENCE_REQUIRED:{name}")
        span_ids: list[str] = []
        attribute_evidence: list[Mapping[str, Any]] = []
        for item in raw_evidence:
            span_id, evidence = register(item)
            span_ids.append(span_id); evidence_rows.append(evidence); attribute_evidence.append(evidence)
        if name in {"value", "range", "commitSHA"} and value not in {
            evidence["evidenceText"] for evidence in attribute_evidence
        }:
            raise AnnotationContractError(f"ANNOTATION_NODE_ATTRIBUTE_EXACT_SOURCE_VALUE_REQUIRED:{name}")
        cleaned.append({"attributeName": name, "value": value, "evidenceSpanIDs": span_ids}); seen.add(str(name))
    return cleaned, evidence_rows


def _target_states(raw_states: object, routed: set[str], treatments: Mapping[str, str]) -> list[dict[str, str]]:
    """Validate actual completion state independently from screening expectations."""

    rows = _require_list(raw_states, "ANNOTATION_TARGET_STATES_ARRAY_REQUIRED")
    seen: set[str] = set(); result: list[dict[str, str]] = []
    for raw in rows:
        if not isinstance(raw, Mapping) or set(raw) != {"operationalTargetID", "state"}:
            raise AnnotationContractError("ANNOTATION_TARGET_STATE_FIELDS_INVALID")
        target_id, state = raw["operationalTargetID"], raw["state"]
        if target_id not in routed:
            raise AnnotationContractError(f"ANNOTATION_TARGET_STATE_NOT_ROUTED:{target_id}")
        if target_id in seen:
            raise AnnotationContractError(f"ANNOTATION_TARGET_STATE_DUPLICATE:{target_id}")
        allowed = {"reviewed_positive", "abstained"}; treatment = treatments[str(target_id)]
        allowed.add("reviewed_no_positive" if treatment == "extract_and_evaluate" else (
            "monitored_review_complete" if treatment == "extract_and_monitor" else "deferred_task_review_complete"
        ))
        if state not in allowed:
            raise AnnotationContractError(f"ANNOTATION_TARGET_STATE_INCOMPATIBLE:{target_id}")
        seen.add(str(target_id)); result.append({"operationalTargetID": str(target_id), "state": str(state)})
    return sorted(result, key=lambda row: row["operationalTargetID"])


def validate_annotation(
    contracts: AnnotationContracts, source_unit_id: str, payload: Mapping[str, Any], *,
    annotation_session_id: str, annotator_id: str, require_complete: bool = False,
    context_exposures: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Validate and normalize one primary-unit-bound independent annotation."""

    if not isinstance(payload, Mapping):
        raise AnnotationContractError("ANNOTATION_PAYLOAD_OBJECT_REQUIRED")
    _reject_forbidden_fields(payload)
    unknown = set(payload) - ALLOWED_INPUT_FIELDS
    if unknown:
        raise AnnotationContractError(f"ANNOTATION_UNKNOWN_FIELD:{sorted(unknown)[0]}")
    if source_unit_id not in contracts.unit_order:
        code = "CALIBRATION_NON_MEMBER_UNIT_FORBIDDEN" if contracts.mode == "calibration" else "ANNOTATION_SYNTHETIC_UNIT_UNKNOWN"
        raise AnnotationContractError(f"{code}:{source_unit_id}")
    unit, route = contracts.units_by_id[source_unit_id], contracts.routes_by_id[source_unit_id]
    canonical_document_hash = contracts.canonical_document_hash(source_unit_id)
    if route.get("routingStatus") != "routed":
        raise AnnotationContractError("ANNOTATION_STRUCTURALLY_BLOCKED_UNIT")
    if route.get("sourceUnitTextHash") != unit.get("textHash"):
        raise AnnotationContractError("ANNOTATION_SOURCE_UNIT_HASH_DRIFT")
    contracts.source_text(source_unit_id)
    routed_nodes = set(route["eligibleNodeOperationalTargetIDs"]); routed_relations = set(route["eligibleRelationOperationalTargetIDs"])
    unavailable_ids = {row["operationalTargetID"] for row in route["structurallyUnavailableOperationalTargets"]}
    if (routed_nodes | routed_relations) & unavailable_ids:
        raise AnnotationContractError("ANNOTATION_STRUCTURALLY_UNAVAILABLE_TARGET_EFFECTIVE")
    if routed_nodes - set(contracts.node_targets) or routed_relations - set(contracts.relation_targets):
        raise AnnotationContractError("ANNOTATION_EFFECTIVE_ROUTE_TARGET_CONTRACT_MISMATCH")
    workflow = payload.get("workflowState", "reading")
    if workflow not in WORKFLOW_STATES:
        raise AnnotationContractError("ANNOTATION_WORKFLOW_STATE_INVALID")

    cleaned_exposures: list[dict[str, Any]] = []
    exposed_context_ids: list[str] = []
    exposure_fields = {
        "exposureID", "primarySourceUnitID", "contextSourceUnitID", "contextScope",
        "contextPolicyName", "contextPolicyVersion", "contextSelectionReason",
        "taskBindingType", "taskBindingID", "exposedAt",
    }
    for exposure in context_exposures:
        if not isinstance(exposure, Mapping) or set(exposure) != exposure_fields:
            raise AnnotationContractError("ANNOTATION_CONTEXT_EXPOSURE_FIELDS_INVALID")
        context_id = exposure["contextSourceUnitID"]
        if exposure["primarySourceUnitID"] != source_unit_id:
            raise AnnotationContractError("ANNOTATION_CONTEXT_EXPOSURE_PRIMARY_MISMATCH")
        candidates = set(contracts.context_candidate_ids(source_unit_id))
        if context_id not in candidates:
            raise AnnotationContractError("ANNOTATION_CONTEXT_UNIT_NOT_AUTHORIZED")
        context = contracts.units_by_id[str(context_id)]
        same_section = context["sectionID"] == unit["sectionID"]
        expected_scope = "section_context" if same_section else "document_reconciliation"
        if exposure["contextScope"] != expected_scope:
            raise AnnotationContractError("ANNOTATION_CONTEXT_EXPOSURE_SCOPE_MISMATCH")
        if exposure["contextPolicyName"] != CONTEXT_POLICY_NAME or exposure["contextPolicyVersion"] != CONTEXT_POLICY_VERSION:
            raise AnnotationContractError("ANNOTATION_CONTEXT_POLICY_BINDING_MISMATCH")
        binding_type, binding_id = exposure["taskBindingType"], exposure["taskBindingID"]
        if same_section:
            if exposure["contextSelectionReason"] != "same_section_context" or binding_type is not None or binding_id is not None:
                raise AnnotationContractError("ANNOTATION_SECTION_CONTEXT_EXPOSURE_INVALID")
        else:
            if exposure["contextSelectionReason"] not in DOCUMENT_CONTEXT_REASONS:
                raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_REASON_INVALID")
            if binding_type == "operational_target":
                if binding_id not in routed_nodes | routed_relations:
                    raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_TARGET_NOT_ROUTED")
            elif binding_type == "unresolved_assertion":
                if not isinstance(binding_id, str) or not (NODE_ID.fullmatch(binding_id) or EDGE_ID.fullmatch(binding_id)):
                    raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_ASSERTION_ID_INVALID")
            else:
                raise AnnotationContractError("ANNOTATION_DOCUMENT_CONTEXT_TASK_BINDING_REQUIRED")
        cleaned_exposures.append(dict(exposure))
        if str(context_id) not in exposed_context_ids:
            exposed_context_ids.append(str(context_id))
    contracts.authorized_context_ids(source_unit_id, exposed_context_ids)

    evidence_spans: list[dict[str, Any]] = []
    evidence_by_key: dict[tuple[str, int, int], tuple[str, Mapping[str, Any]]] = {}

    def register(raw: object) -> tuple[str, Mapping[str, Any]]:
        """Validate and de-duplicate one canonical span within the annotation envelope."""

        validated = _evidence(
            raw, contracts=contracts, primary_source_unit_id=source_unit_id,
            exposed_context_ids=exposed_context_ids,
        )
        key = (validated["sourceUnitID"], validated["startOffsetInUnit"], validated["endOffsetInUnit"])
        if key in evidence_by_key:
            prior_id, prior = evidence_by_key[key]
            if prior["evidenceText"] != validated["evidenceText"]:
                raise AnnotationContractError("ANNOTATION_EVIDENCE_CONFLICTING_DUPLICATE")
            return prior_id, prior
        span_id = f"evidence-{len(evidence_spans) + 1:04d}"; row = {"evidenceSpanID": span_id, **validated}
        evidence_spans.append(row); evidence_by_key[key] = (span_id, row)
        return span_id, row

    deterministic = {
        f"paper:{unit['paperID']}": {"className": "Paper", "artifactID": unit["canonicalArtifactID"], "displayLabel": "Current paper"},
        **contracts.deterministic_endpoints(source_unit_id, exposed_context_ids),
    }
    deferred_refs = {
        ref for context_id in contracts.authorized_context_ids(source_unit_id, exposed_context_ids)
        for ref in contracts.units_by_id[context_id].get("deferredRecordRefs", [])
    }
    node_classes: dict[str, str] = {}; node_artifact_scopes: dict[str, str] = {}
    node_ids: set[str] = set(); positive_targets: set[str] = set(); cleaned_nodes: list[dict[str, Any]] = []
    for raw in _require_list(payload.get("nodes", []), "ANNOTATION_NODES_ARRAY_REQUIRED"):
        if not isinstance(raw, Mapping):
            raise AnnotationContractError("ANNOTATION_NODE_OBJECT_REQUIRED")
        allowed_fields = {
            "localID", "operationalTargetID", "action", "existingNodeID", "deferredRecordID", "evidence",
            "mentionSpan", "attributes", "discoveryScope", "distributedEvidenceReason",
        }
        if set(raw) - allowed_fields:
            raise AnnotationContractError("ANNOTATION_NODE_FIELDS_INVALID")
        local_id, target_id = raw.get("localID"), raw.get("operationalTargetID")
        if not isinstance(local_id, str) or not NODE_ID.fullmatch(local_id):
            raise AnnotationContractError("ANNOTATION_NODE_LOCAL_ID_INVALID")
        if local_id in node_ids:
            raise AnnotationContractError(f"ANNOTATION_DUPLICATE_LOCAL_ID:{local_id}")
        if target_id in unavailable_ids:
            raise AnnotationContractError(f"ANNOTATION_STRUCTURALLY_UNAVAILABLE_TARGET_FORBIDDEN:{target_id}")
        if target_id not in routed_nodes:
            raise AnnotationContractError(f"ANNOTATION_NODE_TARGET_NOT_EFFECTIVELY_ROUTED:{target_id}")
        target = contracts.node_targets[str(target_id)]; class_name = _class_name(target)
        action, existing_node_id = raw.get("action", "propose_new"), raw.get("existingNodeID")
        if action not in target.get("allowed_actions", []):
            raise AnnotationContractError(f"ANNOTATION_NODE_ACTION_NOT_ALLOWED:{target_id}")
        if action == "link_existing" and (
            existing_node_id not in deterministic or deterministic[str(existing_node_id)]["className"] != class_name
        ):
            raise AnnotationContractError("ANNOTATION_LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED")
        if action == "propose_new" and existing_node_id not in (None, ""):
            raise AnnotationContractError("ANNOTATION_PROPOSE_NEW_EXISTING_ID_FORBIDDEN")
        deferred_id = raw.get("deferredRecordID")
        if target["pilot_treatment"] == "deferred_resolution":
            if not deferred_id or deferred_id not in deferred_refs:
                raise AnnotationContractError("ANNOTATION_DEFERRED_RECORD_EXACT_BINDING_REQUIRED")
            origin = "deferred_resolution"
        else:
            if deferred_id not in (None, ""):
                raise AnnotationContractError("ANNOTATION_DEFERRED_RECORD_NOT_ROUTED")
            deferred_id, origin = None, "open_discovery"
        if "mentionSpan" not in raw:
            raise AnnotationContractError(f"ANNOTATION_NODE_MENTION_REQUIRED:{local_id}")
        mention_span = _mention_span(
            raw["mentionSpan"], contracts=contracts, primary_source_unit_id=source_unit_id,
            exposed_context_ids=exposed_context_ids,
        )
        raw_evidence = _require_list(raw.get("evidence", []), "ANNOTATION_NODE_EVIDENCE_ARRAY_REQUIRED")
        if not raw_evidence:
            raise AnnotationContractError(f"ANNOTATION_NODE_EVIDENCE_REQUIRED:{local_id}")
        span_ids: list[str] = []; assertion_evidence: list[Mapping[str, Any]] = []
        for item in raw_evidence:
            span_id, evidence = register(item); span_ids.append(span_id); assertion_evidence.append(evidence)
        attributes, attribute_evidence = _attributes(raw.get("attributes", []), class_name, register)
        scope, distributed_reason = _discovery(
            contracts, source_unit_id, [mention_span] + assertion_evidence + attribute_evidence,
            raw.get("discoveryScope"), raw.get("distributedEvidenceReason"), exposed_context_ids,
        )
        artifact_scope = "external_artifact" if class_name in EXTERNAL_ARTIFACT_CLASSES else "source_artifact"
        if action == "link_existing" and deterministic[str(existing_node_id)]["artifactID"] == unit["canonicalArtifactID"]:
            artifact_scope = "source_artifact"
        cleaned_nodes.append({
            "candidateID": local_id, "action": action, "origin": origin,
            "operationalTargetID": target_id, "ontologyClassID": target["ontology_ids"][0],
            "className": class_name, "label": mention_span["exactText"], "labelMode": "verbatim",
            "normalizedLabelProposal": None,
            "identityScope": "exact_existing_endpoint" if action == "link_existing" else ("resolver_pending" if deferred_id else "source_local"),
            "artifactScope": artifact_scope, "provisionalIdentity": action == "propose_new",
            "existingNodeID": existing_node_id or None, "deferredRecordID": deferred_id,
            "discoveryScope": scope, "distributedEvidenceReason": distributed_reason,
            "mentionSpan": mention_span, "attributes": attributes, "evidenceSpanIDs": span_ids,
        })
        node_ids.add(local_id); node_classes[local_id] = class_name; node_artifact_scopes[local_id] = artifact_scope
        positive_targets.add(str(target_id))

    cleaned_relations: list[dict[str, Any]] = []; edge_ids: set[str] = set()
    for raw in _require_list(payload.get("relations", []), "ANNOTATION_RELATIONS_ARRAY_REQUIRED"):
        if not isinstance(raw, Mapping):
            raise AnnotationContractError("ANNOTATION_RELATION_OBJECT_REQUIRED")
        allowed_fields = {
            "localID", "operationalTargetID", "sourceEndpointID", "targetEndpointID", "deferredRecordID", "evidence",
            "discoveryScope", "distributedEvidenceReason", "relationScope",
        }
        if set(raw) - allowed_fields:
            raise AnnotationContractError("ANNOTATION_RELATION_FIELDS_INVALID")
        local_id, target_id = raw.get("localID"), raw.get("operationalTargetID")
        if not isinstance(local_id, str) or not EDGE_ID.fullmatch(local_id):
            raise AnnotationContractError("ANNOTATION_RELATION_LOCAL_ID_INVALID")
        if local_id in edge_ids or local_id in node_ids:
            raise AnnotationContractError(f"ANNOTATION_DUPLICATE_LOCAL_ID:{local_id}")
        if target_id in unavailable_ids:
            raise AnnotationContractError(f"ANNOTATION_STRUCTURALLY_UNAVAILABLE_TARGET_FORBIDDEN:{target_id}")
        if target_id not in routed_relations:
            raise AnnotationContractError(f"ANNOTATION_RELATION_TARGET_NOT_EFFECTIVELY_ROUTED:{target_id}")
        source, source_class, source_external = _endpoint(
            raw.get("sourceEndpointID"), node_classes, node_artifact_scopes, deterministic, unit["canonicalArtifactID"]
        )
        target_endpoint, target_class, target_external = _endpoint(
            raw.get("targetEndpointID"), node_classes, node_artifact_scopes, deterministic, unit["canonicalArtifactID"]
        )
        relation = contracts.relation_targets[str(target_id)]
        if not any(
            _endpoint_matches(source_class, signature["domain"], contracts.class_expansions)
            and _endpoint_matches(target_class, signature["range"], contracts.class_expansions)
            for signature in relation["operational_signatures"]
        ):
            raise AnnotationContractError(f"ANNOTATION_RELATION_DOMAIN_RANGE_MISMATCH:{local_id}")
        relation_scope = "inter_source" if source_external or target_external else "intra_source"
        if raw.get("relationScope") not in (None, "") and raw.get("relationScope") != relation_scope:
            raise AnnotationContractError("ANNOTATION_RELATION_SCOPE_MISMATCH")
        deferred_id = raw.get("deferredRecordID")
        if relation["pilot_treatment"] == "deferred_resolution":
            if not deferred_id or deferred_id not in deferred_refs:
                raise AnnotationContractError("ANNOTATION_DEFERRED_RECORD_EXACT_BINDING_REQUIRED")
            action, origin = "resolve_deferred", "deferred_resolution"
        else:
            if deferred_id not in (None, ""):
                raise AnnotationContractError("ANNOTATION_DEFERRED_RECORD_NOT_ROUTED")
            deferred_id, action, origin = None, "propose_edge", "open_discovery"
        if action not in relation["allowed_actions"]:
            raise AnnotationContractError(f"ANNOTATION_RELATION_ACTION_NOT_ALLOWED:{target_id}")
        raw_evidence = _require_list(raw.get("evidence", []), "ANNOTATION_RELATION_EVIDENCE_ARRAY_REQUIRED")
        if not raw_evidence:
            raise AnnotationContractError(f"ANNOTATION_RELATION_EDGE_EVIDENCE_REQUIRED:{local_id}")
        span_ids: list[str] = []; assertion_evidence: list[Mapping[str, Any]] = []
        for item in raw_evidence:
            span_id, evidence = register(item); span_ids.append(span_id); assertion_evidence.append(evidence)
        scope, distributed_reason = _discovery(
            contracts, source_unit_id, assertion_evidence, raw.get("discoveryScope"),
            raw.get("distributedEvidenceReason"), exposed_context_ids,
        )
        cleaned_relations.append({
            "candidateID": local_id, "action": action, "origin": origin,
            "operationalRelationID": target_id, "ontologyRelationID": relation["ontology_ids"][0],
            "relationName": relation["operational_relation"], "relationScope": relation_scope,
            "source": source, "target": target_endpoint, "deferredRecordID": deferred_id,
            "discoveryScope": scope, "distributedEvidenceReason": distributed_reason,
            "evidenceSpanIDs": span_ids,
        })
        edge_ids.add(local_id); positive_targets.add(str(target_id))

    routed_all = routed_nodes | routed_relations
    treatments = {
        target_id: (contracts.node_targets.get(target_id) or contracts.relation_targets[target_id])["pilot_treatment"]
        for target_id in routed_all
    }
    target_states = _target_states(payload.get("targetStates", []), routed_all, treatments)
    state_by_id = {row["operationalTargetID"]: row["state"] for row in target_states}
    for target_id in positive_targets:
        if state_by_id.get(target_id) not in {None, "reviewed_positive"}:
            raise AnnotationContractError(f"ANNOTATION_POSITIVE_TARGET_STATE_CONFLICT:{target_id}")
    for target_id, state in state_by_id.items():
        if state == "reviewed_positive" and target_id not in positive_targets:
            raise AnnotationContractError(f"ANNOTATION_TARGET_STATE_POSITIVE_MISSING_INSTANCE:{target_id}")

    uncertainties: list[dict[str, Any]] = []
    for index, raw in enumerate(_require_list(payload.get("uncertainties", []), "ANNOTATION_UNCERTAINTIES_ARRAY_REQUIRED"), start=1):
        if not isinstance(raw, Mapping) or set(raw) != {"operationalTargetID", "category", "note", "evidence"}:
            raise AnnotationContractError("ANNOTATION_UNCERTAINTY_FIELDS_INVALID")
        if raw["operationalTargetID"] not in routed_all:
            raise AnnotationContractError("ANNOTATION_UNCERTAINTY_TARGET_NOT_EFFECTIVELY_ROUTED")
        if raw["category"] not in UNCERTAINTY_CATEGORIES:
            raise AnnotationContractError("ANNOTATION_UNCERTAINTY_CATEGORY_INVALID")
        uncertainty_span_ids = [register(item)[0] for item in _require_list(raw["evidence"], "ANNOTATION_UNCERTAINTY_EVIDENCE_ARRAY_REQUIRED")]
        uncertainties.append({
            "uncertaintyID": f"uncertainty-{index:04d}", "operationalTargetID": raw["operationalTargetID"],
            "category": raw["category"], "note": str(raw["note"] or ""), "evidenceSpanIDs": uncertainty_span_ids,
        })
    if require_complete:
        missing = routed_all - set(state_by_id)
        if missing:
            raise AnnotationContractError(f"ANNOTATION_SUBMIT_TARGET_REVIEW_INCOMPLETE:{sorted(missing)[0]}")
        if workflow not in {"review", "reopened", "submitted"}:
            raise AnnotationContractError("ANNOTATION_SUBMIT_REVIEW_PHASE_REQUIRED")

    context_bindings = []
    for context_id in contracts.authorized_context_ids(source_unit_id, exposed_context_ids):
        context = contracts.units_by_id[context_id]
        context_bindings.append({
            "sourceUnitID": context_id, "sourceUnitTextHash": context["textHash"],
            "canonicalDocumentHash": contracts.canonical_document_hash(context_id),
            "sectionID": context["sectionID"], "sectionTitle": context.get("sectionTitleRaw"),
            "startOffsetInDocument": int(context["startOffsetInDocument"]),
            "endOffsetInDocument": int(context["endOffsetInDocument"]),
            "authorizationScope": contracts.discovery_scope(source_unit_id, [context_id], exposed_context_ids),
        })
    return {
        "annotationSchemaVersion": ANNOTATION_OUTPUT_SCHEMA_VERSION,
        "annotationSessionID": annotation_session_id, "annotatorID": annotator_id,
        "sourceArtifactID": unit["canonicalArtifactID"], "sourceUnitID": source_unit_id,
        "primarySourceUnitID": source_unit_id, "contextSourceUnitIDs": exposed_context_ids,
        "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
        "contextExposureEvents": cleaned_exposures,
        "sourceUnitTextHash": unit["textHash"], "canonicalDocumentHash": canonical_document_hash,
        "sectionID": unit["sectionID"], "sectionTitle": unit.get("sectionTitleRaw"),
        "authorizedContextUnits": context_bindings,
        "interfaceVersion": INTERFACE_VERSION, "guidelineVersion": GUIDELINE_VERSION,
        "handbookVersion": HANDBOOK_VERSION, "routingVersion": ROUTING_VERSION,
        "workflowState": workflow, "completenessTreatmentByTarget": treatments,
        "nodes": cleaned_nodes, "relations": cleaned_relations, "evidenceSpans": evidence_spans,
        "targetStates": target_states, "uncertainties": uncertainties,
    }
