"""Canonical prospective Publication semantic attempt, independent of batch runners.

Authority: DEVSET0 schema013 closure (7d48e94 / ddb2511). The additive
evidence isolation amendment changes failure granularity, never literal grounding.
This module has no provider execution or credential-loading path.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .candidate_validation import materialize_usable_pipeline_output, validate_candidate_envelope
from .deterministic_endpoint_binding import bind_edge_endpoint_artifact_ids
from .deterministic_evidence_binding import bind_evidence_spans
from .openai_provider import PROVIDER_NAME, REQUESTED_MODEL
from .request_builder import canonical_json, sha256_bytes
from .response_parser import canonical_parsed_envelope, parse_recorded_response

PIPELINE_VERSION = "publication-semantic-pipeline/1.0.0"
ISOLATION_VERSION = "publication-evidence-failure-isolation/1.0.0"
ISOLATABLE_CODES = frozenset({
    "EVIDENCE_BINDING_LITERAL_NOT_FOUND",
    "EVIDENCE_BINDING_AMBIGUOUS_LITERAL_REQUIRES_LOCATOR_ANCHOR",
    "EVIDENCE_BINDING_INVALID_LOCATOR_ANCHOR",
    "EVIDENCE_BINDING_AMBIGUOUS_LITERAL_WITHIN_LOCATOR_ANCHOR",
})
RECORD_COLLECTIONS = {
    "candidateNodes": ("candidate_node", "candidateID"),
    "candidateEdges": ("candidate_edge", "candidateID"),
    "abstentions": ("abstention", "abstentionID"),
    "deferredRecords": ("deferred_record", "deferredRecordID"),
}


def bind_response_metadata(request: Mapping[str, Any], metadata: Mapping[str, Any], *,
                           production: bool = False, attempt_number: int = 1,
                           max_output_tokens: int = 32768) -> dict[str, Any]:
    """Bind authentic metadata; retain frozen production identity and DEV semantics."""
    if production and (request.get("requestScope") != "complete_section" or request.get("includedCompleteSection") is not True):
        raise ValueError("production scope compatibility mapping is not authorized")
    if not isinstance(attempt_number, int) or attempt_number < 1:
        raise ValueError("downstream validation requires an attempt number")
    if any(key not in metadata for key in ("returnedModel", "createdAt", "inputTokens", "outputTokens", "retryCount")) or not isinstance(metadata.get("usage"), Mapping):
        raise ValueError("authentic provider metadata is incomplete")
    view = deepcopy(dict(request))
    if production:
        view["requestScope"] = "section_context"
    view["offlineResponseMetadata"] = {
        "provider": PROVIDER_NAME, "modelName": REQUESTED_MODEL,
        "modelVersion": metadata["returnedModel"],
        "generationParameters": {"temperature": None, "topP": None, "seed": None,
                                 "maxOutputTokens": max_output_tokens, "responseFormat": "structured_json"},
        "tokenUsage": {"inputTokens": metadata["inputTokens"], "outputTokens": metadata["outputTokens"],
                       "totalTokens": metadata["usage"].get("total_tokens")},
        "costUSD": None, "retryCount": metadata["retryCount"], "responseCreatedAt": metadata["createdAt"],
    }
    if not production:
        view.pop("requestInputSha256", None)
        view["requestInputSha256"] = sha256_bytes(canonical_json(view))
        return view
    view["downstreamCompatibilityProjection"] = {
        "projectionVersion": "production-downstream-metadata-binding/0.1.0",
        "scopeCompatibility": "complete_section -> section_context", "selectedAttemptNumber": attempt_number,
        "providerMetadataSha256": sha256_bytes(canonical_json(metadata)), "providerRequestMutated": False,
    }
    return view


def _dependencies(value: Any, failed: set[str], pointer: str = "") -> list[dict[str, str]]:
    """Find explicit evidence references at any nesting depth without editing them."""
    found = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = pointer + "/" + str(key)
            if key == "evidenceSpanIDs" and isinstance(child, list):
                found.extend({"evidenceSpanID": item, "pointer": path + f"/{i}"}
                             for i, item in enumerate(child) if isinstance(item, str) and item in failed)
            elif key == "evidenceSpanID" and isinstance(child, str) and child in failed:
                found.append({"evidenceSpanID": child, "pointer": path})
            else:
                found.extend(_dependencies(child, failed, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_dependencies(child, failed, pointer + f"/{index}"))
    return found


def isolate_evidence_failures(bound: Mapping[str, Any], binding: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Project identifiable span-local failures out; structural uncertainty stays fatal."""
    spans = bound.get("evidenceSpans")
    if not isinstance(spans, list) or any(not isinstance(x, Mapping) or not isinstance(x.get("evidenceSpanID"), str) or not x["evidenceSpanID"] for x in spans):
        return None
    ids = [x["evidenceSpanID"] for x in spans]
    if len(set(ids)) != len(ids):
        return None
    failed = set()
    for finding in binding.get("findings", []):
        parts = finding.get("pointer", "").split("/")
        if finding.get("code") not in ISOLATABLE_CODES or len(parts) < 3 or parts[1] != "evidenceSpans" or not parts[2].isdigit() or int(parts[2]) >= len(ids):
            return None
        failed.add(ids[int(parts[2])])
    if not failed:
        return None
    projection = deepcopy(dict(bound)); excluded = []
    for collection, (record_type, id_field) in RECORD_COLLECTIONS.items():
        records = projection.get(collection, [])
        if not isinstance(records, list):
            return None
        retained = []
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                return None
            dependencies = _dependencies(record, failed)
            if dependencies:
                if not isinstance(record.get(id_field), str) or not record[id_field]:
                    return None
                excluded.append({"recordID": record[id_field], "recordType": record_type,
                                 "originalPointer": f"/{collection}/{index}",
                                 "reason": "UNBINDABLE_EVIDENCE_DEPENDENCY", "failedEvidenceDependencies": dependencies,
                                 "record": deepcopy(dict(record))})
            else:
                retained.append(record)
        projection[collection] = retained
    projection["evidenceSpans"] = [span for span in spans if span["evidenceSpanID"] not in failed]
    return projection, {"amendmentVersion": ISOLATION_VERSION, "failedEvidenceSpanIDs": sorted(failed),
                        "bindingFindings": deepcopy(binding["findings"]), "excludedRecords": excluded,
                        "rawEvidenceSpanCount": len(spans), "rawModelOutputChanged": False}


def semantic_attempt(raw: bytes, request: Mapping[str, Any], *, provider_metadata: Mapping[str, Any] | None = None,
                     production: bool = False, attempt_number: int = 1,
                     endpoint_binding: bool = True, evidence_binding: bool = True,
                     isolate_failures: bool = True) -> tuple[dict[str, Any], bytes | None, dict[str, Any], dict[str, Any]]:
    """Bind metadata, parse, bind endpoints/evidence, run frozen V1–V12, materialize."""
    view = bind_response_metadata(request, provider_metadata, production=production, attempt_number=attempt_number) if provider_metadata is not None else request
    parser = parse_recorded_response(raw, view)
    if endpoint_binding and parser.get("parseStatus") == "parsed":
        payload = parser.get("parsedDocument")
        if isinstance(payload, Mapping):
            bound, binding = bind_edge_endpoint_artifact_ids(payload, view)
            parser["endpointBinding"] = binding
            if binding["bindingStatus"] == "bound":
                parser["parsedEnvelope"].update(bound)
                parser["bindingOperations"].append({"operation": "bind_trusted_edge_endpoint_artifact_metadata", "bindingVersion": binding["bindingVersion"]})
            else:
                parser.update(parseStatus="processing_failed", processingCode="ENDPOINT_BINDING_FAILED", error="one or more model-authored edge endpoint references could not bind exactly")
    if evidence_binding and parser.get("parseStatus") == "parsed":
        payload = parser.get("parsedEnvelope")
        if isinstance(payload, Mapping):
            bound, binding = bind_evidence_spans(payload, view["sourceUnit"])
            parser["evidenceBinding"] = binding
            isolated = isolate_evidence_failures(bound, binding) if binding["bindingStatus"] == "failed" and isolate_failures else None
            if binding["bindingStatus"] == "bound" or isolated is not None:
                if isolated is not None:
                    bound, parser["evidenceIsolation"] = isolated
                    parser["evidenceBinding"] = {**binding, "bindingStatus": "isolated", "isolationVersion": ISOLATION_VERSION}
                parser["parsedEnvelope"].update(bound)
                parser["bindingOperations"].append({"operation": "bind_model_authored_literal_evidence", "bindingVersion": binding["bindingVersion"]})
            else:
                parser.update(parseStatus="processing_failed", processingCode="EVIDENCE_BINDING_FAILED", error="one or more model-authored evidence spans could not bind exactly")
    parsed = canonical_parsed_envelope(parser) if parser.get("parseStatus") == "parsed" else None
    validation = validate_candidate_envelope(parser, view)
    usable = materialize_usable_pipeline_output(parser.get("parsedEnvelope", {}), validation)
    return parser, parsed, validation, usable
