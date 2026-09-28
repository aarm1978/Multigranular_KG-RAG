"""Materialize the tracked, deterministic Publication Step 6C production freeze."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.extraction.llm.publications.canonical_production_replay import (
    NAMESPACE,
    original_hashes,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    sha256_bytes,
)


FREEZE_VERSION = "1.0.0"
ACCEPTED_IMPLEMENTATION_CHECKPOINT = "5c7edc83ea394bac111d2873451624d28eb3ed9f"
EXPECTED_MANIFEST_SHA256 = "c37ba564ef9a52ea3cc594b0618a96ab55cf7140ff9123014fd350671589754b"
PIPELINE_VERSION = "publication-semantic-pipeline/1.0.0"
ISOLATION_VERSION = "publication-evidence-failure-isolation/1.0.0"
SOURCE_ROOT = PROJECT_ROOT / "var/publication_c1_production"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2"
FREEZE_PATH = OUTPUT_ROOT / "publication_step6c_canonical_c1_freeze_v1.0.0.json"
PREDICTIONS_PATH = OUTPUT_ROOT / "publication_c1_canonical_predictions_v1.0.0.jsonl"
LIFECYCLE_PATH = OUTPUT_ROOT / "publication_c1_canonical_lifecycle_ledger_v1.0.0.jsonl"
INDEX_PATH = OUTPUT_ROOT / "publication_c1_canonical_result_index_v1.0.0.jsonl"


class Step6CFreezeError(ValueError):
    """Raised when canonical C1 cannot be frozen without provenance drift."""


def _load(path: Path) -> dict[str, Any]:
    """Load one required JSON object."""
    if not path.is_file():
        raise Step6CFreezeError(f"required artifact absent: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Step6CFreezeError(f"required artifact is not an object: {path}")
    return value


def _self_hashed(value: Mapping[str, Any], field: str) -> None:
    """Verify an artifact whose hash excludes its own hash field."""
    body = dict(value)
    expected = body.pop(field, None)
    if expected != sha256_bytes(canonical_json(body)):
        raise Step6CFreezeError(f"self-hash mismatch: {field}")


def _record(value: Mapping[str, Any], record_type: str) -> dict[str, Any]:
    """Add stable type/version and a canonical record hash."""
    result = {"recordType": record_type, "recordVersion": FREEZE_VERSION, **dict(value)}
    result["recordSha256"] = sha256_bytes(canonical_json(result))
    return result


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    """Encode stable canonical JSONL with a final line feed."""
    return b"".join(canonical_json(dict(row)) + b"\n" for row in rows)


def _write_idempotent(path: Path, data: bytes) -> None:
    """Write deterministic freeze bytes, failing closed on an existing conflict."""
    if path.exists() and path.read_bytes() != data:
        raise Step6CFreezeError(f"freeze artifact conflict: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _file_binding(path: Path, rows: int | None = None) -> dict[str, Any]:
    """Bind one tracked freeze artifact by repository path, size, hash, and rows."""
    try:
        logical_path = path.relative_to(PROJECT_ROOT)
    except ValueError:
        logical_path = Path("data/curation/papers/m2") / path.name
    result: dict[str, Any] = {
        "path": str(logical_path),
        "sha256": sha256_bytes(path.read_bytes()),
        "byteCount": path.stat().st_size,
    }
    if rows is not None:
        result["recordCount"] = rows
    return result


def _attempt_lifecycle(attempt: Mapping[str, Any]) -> dict[str, Any]:
    """Project one attempt without duplicating its semantic payloads."""
    parser = attempt.get("parserResult", {})
    validation = attempt.get("validation", {})
    return {
        "attemptNumber": attempt.get("attemptNumber"),
        "status": attempt.get("status"),
        "provider": attempt.get("provider"),
        "requestedModel": attempt.get("requestedModel"),
        "reasoningEffort": attempt.get("reasoningEffort"),
        "maxOutputTokens": attempt.get("maxOutputTokens"),
        "store": attempt.get("store"),
        "toolConfiguration": attempt.get("toolConfiguration"),
        "authorityBundleID": attempt.get("authorityBundleID"),
        "modelAuthorableSchemaSha256": attempt.get("modelAuthorableSchemaSha256"),
        "parseStatus": parser.get("parseStatus"),
        "processingCode": parser.get("processingCode"),
        "envelopeStatus": validation.get("envelopeStatus"),
        "requestInputSha256": attempt.get("requestInputSha256"),
        "providerInputSha256": attempt.get("providerInputSha256"),
        "providerResponseSha256": attempt.get("providerResponseSha256"),
        "providerMetadataSha256": attempt.get("providerMetadataSha256"),
        "rawOutputSha256": attempt.get("rawOutputSha256"),
        "recoveryProvenanceSha256": attempt.get("recoveryProvenanceSha256"),
        "providerFailure": attempt.get("providerFailure"),
    }


def _candidate_source(envelope: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Index every canonical candidate and non-candidate record by type and ID."""
    result: dict[str, Mapping[str, Any]] = {}
    for collection, field in (("candidateNodes", "candidateID"), ("candidateEdges", "candidateID"),
                              ("abstentions", "abstentionID"), ("deferredRecords", "deferredRecordID")):
        for row in envelope.get(collection, []):
            if isinstance(row, Mapping) and isinstance(row.get(field), str):
                result[f"{collection}:{row[field]}"] = row
    return result


def _result_source_key(row: Mapping[str, Any]) -> str:
    """Map a validation result to its canonical parsed-envelope collection."""
    collection = {"candidate_node": "candidateNodes", "candidate_edge": "candidateEdges",
                  "abstention": "abstentions", "deferred_record": "deferredRecords"}.get(str(row.get("recordType")))
    return f"{collection}:{row.get('recordID')}"


def _build_request_records(ordinal: int, manifest_row: Mapping[str, Any], request_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Counter[str]]:
    """Build prediction, lifecycle, and index records for one canonical request."""
    replay = request_root / NAMESPACE
    required = ("provenance.json", "parser_result.json", "validation_results.json",
                "usable_pipeline_output.json", "attempt_selection.json",
                "accepted_semantic_projection.json", "unresolved_identity_sidecar.json")
    if any(not (replay / name).is_file() for name in required):
        raise Step6CFreezeError(f"canonical request artifacts absent: {manifest_row['requestID']}")
    provenance = _load(replay / "provenance.json")
    parser = _load(replay / "parser_result.json")
    validation = _load(replay / "validation_results.json")
    usable = _load(replay / "usable_pipeline_output.json")
    selection = _load(replay / "attempt_selection.json")
    projection = _load(replay / "accepted_semantic_projection.json")
    sidecar = _load(replay / "unresolved_identity_sidecar.json")
    for value, field in ((selection, "attemptSelectionHash"), (validation, "validationResultsHash"),
                         (usable, "usablePipelineOutputHash"), (projection, "acceptedSemanticProjectionHash"),
                         (sidecar, "unresolvedIdentitySidecarHash")):
        _self_hashed(value, field)
    selected = selection.get("selectedAttemptNumber")
    if selected not in (1, 2) or selection.get("selectionDisposition") != "first_processable_response_selected":
        raise Step6CFreezeError("canonical selection is not processable")
    authentic_attempt = request_root / f"attempt-{selected:02d}"
    raw = authentic_attempt / "raw_model_output.json"
    provider_metadata = authentic_attempt / "provider_metadata.json"
    provider_response = authentic_attempt / "provider_response.json"
    provider_request = authentic_attempt / "provider_request.json"
    if any(not path.is_file() for path in (raw, provider_metadata, provider_response, provider_request)):
        raise Step6CFreezeError("selected attempt lacks authentic provider artifacts")
    authentic_raw_hash = sha256_bytes(raw.read_bytes())
    bindings = {
        "requestID": manifest_row["requestID"],
        "requestInputSha256": manifest_row["requestInputSha256"],
        "providerRequestBodySha256": manifest_row["providerRequestBodySha256"],
        "selectedAttemptNumber": selected,
        "rawOutputSha256": authentic_raw_hash,
        "providerMetadataSha256": sha256_bytes(canonical_json(_load(provider_metadata))),
        "providerResponseSha256": sha256_bytes(canonical_json(_load(provider_response))),
    }
    if any(provenance.get(key) != value for key, value in bindings.items() if key != "providerResponseSha256"):
        raise Step6CFreezeError("canonical/authentic provenance binding mismatch")
    if sha256_bytes(canonical_json(_load(provider_request))) != bindings["providerRequestBodySha256"]:
        raise Step6CFreezeError("authentic provider request does not match manifest")
    if projection.get("requestID") != bindings["requestID"] or projection.get("selectedProviderAttempt", {}).get("attemptNumber") != selected:
        raise Step6CFreezeError("accepted projection identity mismatch")
    selected_record = next((row for row in selection.get("attempts", []) if row.get("attemptNumber") == selected), None)
    if not isinstance(selected_record, Mapping) or any(selected_record.get(key) != value for key, value in {
        "requestInputSha256": bindings["requestInputSha256"],
        "rawOutputSha256": bindings["rawOutputSha256"],
        "providerMetadataSha256": bindings["providerMetadataSha256"],
        "providerResponseSha256": bindings["providerResponseSha256"],
    }.items()):
        raise Step6CFreezeError("canonical selected attempt does not bind authentic provider artifacts")

    prediction = _record({
        "ordinal": ordinal,
        "requestID": bindings["requestID"],
        "requestInputSha256": bindings["requestInputSha256"],
        "acceptedSemanticProjection": projection,
        "unresolvedIdentitySidecar": sidecar,
    }, "publication_c1_canonical_prediction")

    envelope = parser.get("parsedEnvelope", {})
    source_records = _candidate_source(envelope) if isinstance(envelope, Mapping) else {}
    nonaccepted = []
    status_counts: Counter[str] = Counter()
    for row in validation.get("recordResults", []):
        if not isinstance(row, Mapping):
            raise Step6CFreezeError("validation result is not an object")
        status = str(row.get("candidateValidationStatus", row.get("recordValidationStatus")))
        status_counts[status] += 1
        if status != "validated" or row.get("recordType") in {"abstention", "deferred_record"}:
            nonaccepted.append({"validationResult": row, "canonicalRecord": source_records.get(_result_source_key(row))})
    isolation = parser.get("evidenceIsolation", {}) if isinstance(parser.get("evidenceIsolation"), Mapping) else {}
    failures = []
    for attempt in selection.get("attempts", []):
        if attempt.get("parserResult", {}).get("parseStatus") != "parsed":
            failures.append({"attemptNumber": attempt.get("attemptNumber"),
                             "parserResult": attempt.get("parserResult"),
                             "validation": attempt.get("validation"),
                             "providerFailure": attempt.get("providerFailure")})
    original_selection = _load(request_root / "attempt_selection.json")
    lifecycle = _record({
        "ordinal": ordinal,
        "requestID": bindings["requestID"],
        "requestInputSha256": bindings["requestInputSha256"],
        "originalSelectionDisposition": original_selection.get("selectionDisposition"),
        "originalSelectedAttemptNumber": original_selection.get("selectedAttemptNumber"),
        "canonicalSelectionDisposition": selection["selectionDisposition"],
        "canonicalSelectedAttemptNumber": selected,
        "authenticAttempts": [_attempt_lifecycle(row) for row in original_selection.get("attempts", [])],
        "canonicalAttempts": [_attempt_lifecycle(row) for row in selection.get("attempts", [])],
        "envelopeStatus": validation.get("envelopeStatus"),
        "validationDispositionCounts": dict(sorted(status_counts.items())),
        "nonAcceptedRecords": nonaccepted,
        "evidenceIsolation": isolation,
        "processingFailureRecords": failures,
        "abstentions": envelope.get("abstentions", []) if isinstance(envelope, Mapping) else [],
        "deferredRecords": envelope.get("deferredRecords", []) if isinstance(envelope, Mapping) else [],
    }, "publication_c1_canonical_lifecycle")

    index = _record({
        "ordinal": ordinal,
        "primarySourceUnitID": manifest_row["primarySourceUnitID"],
        "runID": manifest_row["runID"],
        "outputID": manifest_row["outputID"],
        **bindings,
        "authenticAttemptCount": len(original_selection.get("attempts", [])),
        "authenticAttemptNumbers": [row.get("attemptNumber") for row in original_selection.get("attempts", [])],
        "canonicalParserSha256": sha256_bytes((replay / "parser_result.json").read_bytes()),
        "canonicalValidationSha256": sha256_bytes((replay / "validation_results.json").read_bytes()),
        "canonicalValidationResultsHash": validation["validationResultsHash"],
        "canonicalUsableOutputSha256": sha256_bytes((replay / "usable_pipeline_output.json").read_bytes()),
        "canonicalUsablePipelineOutputHash": usable["usablePipelineOutputHash"],
        "canonicalAttemptSelectionSha256": sha256_bytes((replay / "attempt_selection.json").read_bytes()),
        "canonicalAttemptSelectionHash": selection["attemptSelectionHash"],
        "canonicalAcceptedProjectionSha256": sha256_bytes((replay / "accepted_semantic_projection.json").read_bytes()),
        "canonicalAcceptedProjectionHash": projection["acceptedSemanticProjectionHash"],
        "canonicalUnresolvedSidecarSha256": sha256_bytes((replay / "unresolved_identity_sidecar.json").read_bytes()),
        "canonicalUnresolvedSidecarHash": sidecar["unresolvedIdentitySidecarHash"],
        "predictionRecordSha256": prediction["recordSha256"],
        "lifecycleRecordSha256": lifecycle["recordSha256"],
        "selectionDisposition": selection["selectionDisposition"],
        "envelopeStatus": validation.get("envelopeStatus"),
        "acceptedNodeCount": len(projection.get("acceptedNodes", [])),
        "acceptedEdgeCount": len(projection.get("acceptedEdges", [])),
        "unresolvedIdentityCount": len(sidecar.get("records", [])),
        "excludedEvidenceDependencyCount": len(isolation.get("excludedRecords", [])),
        "validationDispositionCounts": dict(sorted(status_counts.items())),
        "abstentionCount": len(envelope.get("abstentions", [])),
        "deferredRecordCount": len(envelope.get("deferredRecords", [])),
        "processingFailureRecordCount": len(failures),
    }, "publication_c1_canonical_result_index")
    return prediction, lifecycle, index, status_counts


def materialize(source_root: Path = SOURCE_ROOT, output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    """Verify all canonical inputs and write the exact tracked Step 6C realization."""
    manifest = _load(source_root / "publication_c1_run_manifest.json")
    _self_hashed(manifest, "manifestSha256")
    if manifest.get("manifestSha256") != EXPECTED_MANIFEST_SHA256 or manifest.get("populationCount") != 227:
        raise Step6CFreezeError("production run manifest identity/count drift")
    aggregate_path = source_root / NAMESPACE / "aggregate_report.json"
    aggregate = _load(aggregate_path)
    expected_aggregate = {
        "requestCount": 227, "canonicalDispositionDistribution": {"first_processable_response_selected": 227},
        "selectedAttemptDistribution": {"1": 226, "2": 1},
        "envelopeStatusDistribution": {"valid": 183, "partially_valid": 44},
        "usableOutputDistribution": {"nonempty": 224, "empty": 3},
        "totalUsableNodes": 5301, "totalUsableEdges": 2941,
        "originalEvidenceBindingFailureRequests": 10, "isolatedSpanCount": 18,
        "providerModelCalls": 0, "originalArtifactsUnchanged": True,
        "processableParity": {"required": 217, "passed": 217, "failed": 0},
    }
    if aggregate.get("pipelineVersion") != PIPELINE_VERSION or aggregate.get("evidenceIsolationVersion") != ISOLATION_VERSION or any(aggregate.get(k) != v for k, v in expected_aggregate.items()):
        raise Step6CFreezeError("accepted canonical aggregate drift")
    original_inventory = _load(source_root / NAMESPACE / "original_artifact_hashes.json")
    if original_hashes(source_root) != original_inventory:
        raise Step6CFreezeError("canonical replay preservation check failed")

    predictions, lifecycles, indexes = [], [], []
    all_statuses: Counter[str] = Counter()
    for ordinal, row in enumerate(manifest.get("requests", []), start=1):
        request_id = row.get("requestID")
        if not isinstance(request_id, str):
            raise Step6CFreezeError("manifest request lacks requestID")
        prediction, lifecycle, index, statuses = _build_request_records(ordinal, row, source_root / "requests" / request_id)
        predictions.append(prediction); lifecycles.append(lifecycle); indexes.append(index); all_statuses.update(statuses)
    if len({row["requestID"] for row in indexes}) != 227:
        raise Step6CFreezeError("canonical request representation is not exactly once")
    if sum(row["acceptedNodeCount"] for row in indexes) != 5301 or sum(row["acceptedEdgeCount"] for row in indexes) != 2941:
        raise Step6CFreezeError("accepted prediction totals drift")

    predictions_path = output_root / PREDICTIONS_PATH.name
    lifecycle_path = output_root / LIFECYCLE_PATH.name
    index_path = output_root / INDEX_PATH.name
    _write_idempotent(predictions_path, _jsonl_bytes(predictions))
    _write_idempotent(lifecycle_path, _jsonl_bytes(lifecycles))
    _write_idempotent(index_path, _jsonl_bytes(indexes))

    freeze = {
        "artifactType": "publication_step6c_canonical_c1_freeze",
        "artifactVersion": FREEZE_VERSION,
        "status": "FROZEN_CLOSED",
        "acceptedImplementationCheckpoint": ACCEPTED_IMPLEMENTATION_CHECKPOINT,
        "productionRunManifest": {"path": "var/publication_c1_production/publication_c1_run_manifest.json",
                                  "manifestSha256": EXPECTED_MANIFEST_SHA256, "requestCount": 227},
        "canonicalReplay": {"namespace": NAMESPACE, "aggregateReportSha256": sha256_bytes(aggregate_path.read_bytes()),
                            "originalArtifactInventorySha256": aggregate["originalArtifactInventorySha256"],
                            "originalArtifactCount": aggregate["originalArtifactCount"], "processableParity": aggregate["processableParity"]},
        "semanticAuthority": {"pipelinePath": "src/extraction/llm/publications/publication_semantic_pipeline.py",
                              "pipelineSha256": sha256_bytes((PROJECT_ROOT / "src/extraction/llm/publications/publication_semantic_pipeline.py").read_bytes()),
                              "pipelineVersion": PIPELINE_VERSION, "evidenceIsolationVersion": ISOLATION_VERSION,
                              "authorityBundleID": "publication-semantic-v0.1.5-schema-v0.1.3",
                              "promptVersion": "publication-development-0.1.8", "candidateSchemaVersion": "0.1.3",
                              "ontologyVersion": "0.1.5", "targetInventoryVersion": "0.1.5"},
        "frozenStepAuthorities": {"productionAcceptancePolicy": "publication-production-acceptance-policy/0.1.0",
                                  "step5EvaluationAuthority": "publication-step5-evaluation-authority/0.1.1"},
        "trackedArtifacts": {"predictions": _file_binding(predictions_path, 227),
                             "lifecycleLedger": _file_binding(lifecycle_path, 227),
                             "resultIndex": _file_binding(index_path, 227)},
        "canonicalCounts": {**expected_aggregate,
                            "validationDispositionCounts": dict(sorted(all_statuses.items())),
                            "unresolvedIdentityRecords": sum(row["unresolvedIdentityCount"] for row in indexes),
                            "excludedEvidenceDependencyRecords": sum(row["excludedEvidenceDependencyCount"] for row in indexes),
                            "abstentions": sum(row["abstentionCount"] for row in indexes),
                            "deferredRecords": sum(row["deferredRecordCount"] for row in indexes),
                            "preservedProcessingFailureRecords": sum(row["processingFailureRecordCount"] for row in indexes)},
        "amendmentProvenance": {
            "providerGenerationsChangedOrResampled": False,
            "metadataRepair": "deterministic downstream correction",
            "evidenceFailureIsolation": "deterministic downstream correction moving identifiable exact-binding failure isolation from response to dependent-record level",
            "exactEvidenceGroundingChanged": False,
            "formerTerminalResponsesRecovered": 10,
            "humanCoreOrEvaluationLabelsInformedCorrection": False,
        },
        "providerModelCallsDuringFreeze": 0,
        "materializer": {"path": "src/extraction/llm/publications/step6c_freeze_materialization.py",
                         "version": FREEZE_VERSION, "sha256": sha256_bytes(Path(__file__).read_bytes())},
        "originalProviderRawSelectionArtifactsByteIdentical": True,
        "step6Status": "FROZEN_CLOSED",
        "nextAction": "Step 7 Human Core N=5 evaluation",
        "step7Executed": False,
    }
    freeze["artifactSha256"] = sha256_bytes(canonical_json(freeze))
    freeze_path = output_root / FREEZE_PATH.name
    _write_idempotent(freeze_path, canonical_json_file(freeze))
    return freeze


def main() -> int:
    """Materialize and print the compact Step 6C freeze identity."""
    freeze = materialize()
    print({"artifactSha256": freeze["artifactSha256"], "requestCount": freeze["productionRunManifest"]["requestCount"],
           "providerModelCalls": freeze["providerModelCallsDuringFreeze"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
