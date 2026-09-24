"""Deterministic Step 4 Publication production-acceptance controls.

This module deliberately contains no provider client.  It selects at most one
technical retry supplied by an orchestration callback, then derives immutable
accepted-semantic and unresolved-identity artifacts from the selected attempt.
Frozen parsing, trusted bindings, and V1--V12 validation remain upstream.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


POLICY_ID = "publication-production-acceptance-policy"
POLICY_VERSION = "0.1.0-draft.2"
CONTROLLER_VERSION = "publication-production-attempt-controller/0.1.0"
PROJECTION_VERSION = "publication-accepted-semantic-projection/0.1.0"
SIDECAR_VERSION = "publication-unresolved-identity-sidecar/0.1.0"
POLICY_PATH = PROJECT_ROOT / "docs/publication_production_acceptance_policy_v0.1.md"
IMMUTABLE_ATTEMPT_FIELDS = (
    "requestInputSha256",
    "providerInputSha256",
    "authorityBundleID",
    "requestedModel",
    "reasoningEffort",
    "maxOutputTokens",
)


class ProductionAcceptanceError(ValueError):
    """Raised when an attempt or accepted projection cannot be reconstructed."""


AttemptRunner = Callable[[int], Mapping[str, Any]]


def _hash_record(value: dict[str, Any], field: str) -> dict[str, Any]:
    """Return a copy with a canonical content hash in ``field``."""

    result = deepcopy(value)
    result[field] = sha256_bytes(canonical_json(result))
    return result


def _attempt_identity(attempt: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable provider configuration identity for one attempt."""

    missing = [
        field
        for field in IMMUTABLE_ATTEMPT_FIELDS
        if field != "maxOutputTokens"
        and (not isinstance(attempt.get(field), str) or not attempt[field])
    ]
    if not isinstance(attempt.get("maxOutputTokens"), int):
        missing.append("maxOutputTokens")
    if missing:
        raise ProductionAcceptanceError(f"attempt lacks immutable identity fields: {', '.join(sorted(set(missing)))}")
    return {field: attempt[field] for field in IMMUTABLE_ATTEMPT_FIELDS}


def _is_processable(attempt: Mapping[str, Any]) -> bool:
    """Return whether trusted parsing/binding produced a semantic envelope.

    Candidate rejection, review, deferral, abstention, and an empty usable output
    remain processable semantic outcomes and therefore cannot trigger resampling.
    """

    parser = attempt.get("parserResult")
    return isinstance(parser, Mapping) and parser.get("parseStatus") == "parsed"


def run_attempt_controller(run_attempt: AttemptRunner) -> dict[str, Any]:
    """Run one initial attempt and at most one technical retry.

    ``run_attempt`` receives attempt number 1 or 2 and must return an auditable
    attempt record.  The second invocation occurs only when the first attempt is
    not processable.  The function never calls a provider itself.
    """

    attempts: list[dict[str, Any]] = []
    first = deepcopy(dict(run_attempt(1)))
    if first.get("attemptNumber") != 1:
        raise ProductionAcceptanceError("initial attempt must declare attemptNumber 1")
    identity = _attempt_identity(first)
    attempts.append(first)
    if not _is_processable(first):
        second = deepcopy(dict(run_attempt(2)))
        if second.get("attemptNumber") != 2:
            raise ProductionAcceptanceError("technical retry must declare attemptNumber 2")
        if _attempt_identity(second) != identity:
            raise ProductionAcceptanceError("technical retry changed immutable request/provider identity")
        attempts.append(second)

    selected = next((row for row in attempts if _is_processable(row)), None)
    result: dict[str, Any] = {
        "controllerVersion": CONTROLLER_VERSION,
        "policyID": POLICY_ID,
        "policyVersion": POLICY_VERSION,
        "maximumProviderAttempts": 2,
        "attempts": attempts,
        "selectedAttemptNumber": selected.get("attemptNumber") if selected else None,
        "selectionDisposition": (
            "first_processable_response_selected" if selected else "retry_exhausted_processing_failure"
        ),
    }
    return _hash_record(result, "attemptSelectionHash")


def _evidence_occurrences(
    envelope: Mapping[str, Any], validation: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Bind validated evidence spans to trusted canonical-Paper provenance."""

    valid_ids = {
        str(row.get("evidenceSpanID"))
        for row in validation.get("evidenceResults", [])
        if isinstance(row, Mapping) and row.get("valid") is True
    }
    result: dict[str, dict[str, Any]] = {}
    for row in envelope.get("evidenceSpans", []):
        if not isinstance(row, Mapping) or not isinstance(row.get("evidenceSpanID"), str):
            continue
        occurrence = deepcopy(dict(row))
        occurrence["canonicalPaperID"] = request["sourceArtifactID"]
        occurrence["valid"] = row["evidenceSpanID"] in valid_ids
        result[row["evidenceSpanID"]] = occurrence
    return result


def _candidate_evidence(candidate: Mapping[str, Any], evidence: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a candidate's referenced evidence in stable identifier order."""

    return [deepcopy(evidence[evidence_id]) for evidence_id in sorted(candidate.get("evidenceSpanIDs", [])) if evidence_id in evidence]


def _node_id(request: Mapping[str, Any], candidate_id: str) -> str:
    """Return a request-qualified local node identity."""

    return f"{request['requestID']}#node#{candidate_id}"


def _endpoint_id(request: Mapping[str, Any], endpoint: Mapping[str, Any]) -> str:
    """Resolve an accepted edge endpoint without semantic normalization."""

    reference_type = endpoint.get("referenceType")
    reference_id = endpoint.get("referenceID")
    if not isinstance(reference_id, str) or not reference_id:
        raise ProductionAcceptanceError("accepted edge endpoint lacks referenceID")
    if reference_type == "candidate_node":
        return _node_id(request, reference_id)
    if reference_type == "deterministic_node":
        artifact_id = endpoint.get("artifactID")
        if not isinstance(artifact_id, str) or not artifact_id:
            raise ProductionAcceptanceError("deterministic endpoint lacks trusted artifactID")
        return f"deterministic:{artifact_id}:{reference_id}"
    raise ProductionAcceptanceError("accepted edge endpoint has unsupported referenceType")


def derive_accepted_semantic_projection(
    selection: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    """Derive the one immutable production projection from the selected attempt."""

    selected_number = selection.get("selectedAttemptNumber")
    if not isinstance(selected_number, int):
        raise ProductionAcceptanceError("cannot derive a projection without a processable attempt")
    selected = next(
        (row for row in selection.get("attempts", []) if isinstance(row, Mapping) and row.get("attemptNumber") == selected_number),
        None,
    )
    if selected is None or not _is_processable(selected):
        raise ProductionAcceptanceError("selected attempt is not processable")
    if selected.get("requestInputSha256") != request.get("requestInputSha256"):
        raise ProductionAcceptanceError("selected attempt request identity differs from projection request")
    usable = selected.get("usablePipelineOutput")
    parser = selected.get("parserResult")
    validation = selected.get("validation")
    if not isinstance(usable, Mapping) or not isinstance(parser, Mapping) or not isinstance(validation, Mapping):
        raise ProductionAcceptanceError("selected attempt lacks usable, parser, or validation output")
    envelope = parser.get("parsedEnvelope")
    if not isinstance(envelope, Mapping):
        raise ProductionAcceptanceError("processable attempt lacks parsed envelope")
    evidence = _evidence_occurrences(envelope, validation, request)
    nodes: list[dict[str, Any]] = []
    for candidate in usable.get("candidateNodes", []):
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("candidateID"), str):
            raise ProductionAcceptanceError("usable node lacks candidateID")
        candidate_id = candidate["candidateID"]
        nodes.append({
            "nodeID": _node_id(request, candidate_id),
            "candidateID": candidate_id,
            "className": candidate.get("className"),
            "ontologyClassID": candidate.get("ontologyClassID"),
            "operationalTargetID": candidate.get("operationalTargetID"),
            "accepted": True,
            "acceptanceBasis": "frozen_v12_usable_pipeline_output",
            "evidenceOccurrences": _candidate_evidence(candidate, evidence),
            "candidate": deepcopy(dict(candidate)),
        })
    edges: list[dict[str, Any]] = []
    for candidate in usable.get("candidateEdges", []):
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("candidateID"), str):
            raise ProductionAcceptanceError("usable edge lacks candidateID")
        source, target = candidate.get("source"), candidate.get("target")
        if not isinstance(source, Mapping) or not isinstance(target, Mapping):
            raise ProductionAcceptanceError("usable edge lacks endpoint records")
        edges.append({
            "edgeID": f"{request['requestID']}#edge#{candidate['candidateID']}",
            "candidateID": candidate["candidateID"],
            "relationName": candidate.get("relationName"),
            "ontologyRelationID": candidate.get("ontologyRelationID"),
            "operationalRelationID": candidate.get("operationalRelationID"),
            "sourceID": _endpoint_id(request, source),
            "targetID": _endpoint_id(request, target),
            "sourceEndpoint": deepcopy(dict(source)),
            "targetEndpoint": deepcopy(dict(target)),
            "accepted": True,
            "acceptanceBasis": "frozen_v12_usable_pipeline_output",
            "evidenceOccurrences": _candidate_evidence(candidate, evidence),
            "candidate": deepcopy(dict(candidate)),
        })
    projection = {
        "projectionVersion": PROJECTION_VERSION,
        "policyID": POLICY_ID,
        "policyVersion": POLICY_VERSION,
        "policySha256": sha256_bytes(POLICY_PATH.read_bytes()),
        "acceptanceBasis": "frozen_v12_usable_pipeline_output",
        "acceptanceStatus": "production_accepted",
        "authorityBundleID": request.get("authorityBundleID"),
        "authorityBundle": deepcopy(request.get("authorities", {})),
        "requestID": request["requestID"],
        "outputID": usable.get("outputID"),
        "selectedProviderAttempt": {
            "attemptNumber": selected_number,
            **_attempt_identity(selected),
            **{
                field: selected[field]
                for field in (
                    "provider", "returnedModel", "runID", "responseID",
                    "providerResponseSha256", "rawModelOutputSha256",
                )
                if field in selected
            },
        },
        "attemptSelectionHash": selection.get("attemptSelectionHash"),
        "validationResultsHash": usable.get("validationResultsHash"),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"),
        "sourceArtifactID": request["sourceArtifactID"],
        "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
        "paperEndpoints": [{
            "nodeID": f"paper:{request['sourceArtifactID']}",
            "canonicalPaperID": request["sourceArtifactID"],
            "resolutionSource": "trusted_request.sourceArtifactID",
        }],
        "acceptedNodes": sorted(nodes, key=lambda row: row["nodeID"]),
        "acceptedEdges": sorted(edges, key=lambda row: row["edgeID"]),
        "step7PredictionContent": True,
    }
    return _hash_record(projection, "acceptedSemanticProjectionHash")


def derive_unresolved_identity_sidecar(
    selection: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    """Preserve only POSSIBLE_LOCAL_DUPLICATE records outside accepted content."""

    selected_number = selection.get("selectedAttemptNumber")
    selected = next(
        (row for row in selection.get("attempts", []) if isinstance(row, Mapping) and row.get("attemptNumber") == selected_number),
        None,
    )
    if selected is None or not _is_processable(selected):
        raise ProductionAcceptanceError("cannot derive a sidecar without a processable attempt")
    parser, validation = selected.get("parserResult"), selected.get("validation")
    if not isinstance(parser, Mapping) or not isinstance(validation, Mapping) or not isinstance(parser.get("parsedEnvelope"), Mapping):
        raise ProductionAcceptanceError("selected attempt lacks sidecar inputs")
    envelope = parser["parsedEnvelope"]
    candidates = {
        str(row.get("candidateID")): row
        for row in envelope.get("candidateNodes", [])
        if isinstance(row, Mapping) and isinstance(row.get("candidateID"), str)
    }
    evidence = _evidence_occurrences(envelope, validation, request)
    records: list[dict[str, Any]] = []
    for result in validation.get("recordResults", []):
        if not isinstance(result, Mapping) or result.get("recordType") != "candidate_node":
            continue
        codes = {str(item.get("code")) for item in result.get("findings", []) if isinstance(item, Mapping)}
        candidate_id = result.get("recordID")
        if result.get("candidateValidationStatus") != "needs_review" or "POSSIBLE_LOCAL_DUPLICATE" not in codes or candidate_id not in candidates:
            continue
        candidate = candidates[candidate_id]
        records.append({
            "recordID": candidate_id,
            "candidate": deepcopy(dict(candidate)),
            "validationRecord": deepcopy(dict(result)),
            "evidenceOccurrences": _candidate_evidence(candidate, evidence),
            "requestID": request["requestID"],
            "sourceArtifactID": request["sourceArtifactID"],
            "sourceUnitID": request["sourceUnit"]["sourceUnitID"],
        })
    sidecar = {
        "sidecarVersion": SIDECAR_VERSION,
        "policyID": POLICY_ID,
        "policyVersion": POLICY_VERSION,
        "artifactRole": "unresolved_identity_sidecar",
        "notAcceptedSemanticProjection": True,
        "notAcceptedKGContent": True,
        "notStep7PredictionContent": True,
        "selectedAttemptNumber": selected_number,
        "validationResultsHash": validation.get("validationResultsHash"),
        "records": sorted(records, key=lambda row: row["recordID"]),
    }
    return _hash_record(sidecar, "unresolvedIdentitySidecarHash")
