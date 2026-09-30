"""Audit and freeze the authentic corrected Pilot 1 evaluation realization.

This materializer is read-only with respect to the durable execution namespace. It
does not reconstruct requests, invoke a provider, or reprocess raw model output.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes


FREEZE_VERSION = "1.0.0"
SOURCE_ROOT = PROJECT_ROOT / "var/publication_pilot1_evaluation_execution"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation"
FREEZE_NAME = "publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json"
PREDICTIONS_NAME = "publication_pilot1_corrected_evaluation_canonical_predictions_v1.0.0.jsonl"
LIFECYCLE_NAME = "publication_pilot1_corrected_evaluation_lifecycle_ledger_v1.0.0.jsonl"
INDEX_NAME = "publication_pilot1_corrected_evaluation_result_index_v1.0.0.jsonl"
BINDING_NAME = "publication_pilot1_evaluation_execution_binding_v0.1.0.json"
EXPECTED_BINDING_SHA256 = "74b88b08eb51982e9d94fc1025128b1636aed9c06b3be7c80d1ab823993715b9"
EXPECTED_SUBSET_SHA256 = "d47d0c592a67c39cb7059d2b9e1cf68844a4f7126527bc5abb3a342446497f94"
IDENTITY_FIELDS = (
    "requestID", "requestInputSha256", "providerRequestBodySha256",
    "modelAuthorableSchemaSha256", "productionTargetIDs", "contextSourceUnitIDs",
)


class Pilot1EvaluationRealizationFreezeError(ValueError):
    """Report missing, nonterminal, or provenance-inconsistent execution state."""


def _load(path: Path) -> dict[str, Any]:
    """Load one required JSON object."""

    if not path.is_file():
        raise Pilot1EvaluationRealizationFreezeError(f"REQUIRED_ARTIFACT_ABSENT:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Pilot1EvaluationRealizationFreezeError(f"REQUIRED_ARTIFACT_NOT_OBJECT:{path}")
    return value


def _self_hash(value: Mapping[str, Any], field: str) -> None:
    """Verify a self-hashed durable artifact."""

    body = dict(value)
    expected = body.pop(field, None)
    if expected != sha256_bytes(canonical_json(body)):
        raise Pilot1EvaluationRealizationFreezeError(f"SELF_HASH_DRIFT:{field}")


def _record(value: Mapping[str, Any], record_type: str) -> dict[str, Any]:
    """Create one canonical tracked record with a provenance hash."""

    result = {"recordType": record_type, "recordVersion": FREEZE_VERSION, **dict(value)}
    result["recordSha256"] = sha256_bytes(canonical_json(result))
    return result


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    """Encode stable JSONL with a final line feed."""

    return b"".join(canonical_json(dict(row)) + b"\n" for row in rows)


def _write_immutable(path: Path, data: bytes) -> None:
    """Write a deterministic output once and reject a divergent replacement."""

    if path.exists() and path.read_bytes() != data:
        raise Pilot1EvaluationRealizationFreezeError(f"FREEZE_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _source_inventory(root: Path) -> dict[str, str]:
    """Hash every durable source artifact for read-only preservation verification."""

    return {
        str(path.relative_to(root)): sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def _file_binding(path: Path, record_count: int | None = None) -> dict[str, Any]:
    """Return a stable tracked-artifact binding."""

    try:
        logical_path = str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        logical_path = path.name
    result: dict[str, Any] = {
        "path": logical_path,
        "sha256": sha256_bytes(path.read_bytes()),
        "byteCount": path.stat().st_size,
    }
    if record_count is not None:
        result["recordCount"] = record_count
    return result


def _selected_attempt(selection: Mapping[str, Any], request_root: Path) -> tuple[int, dict[str, Any]]:
    """Require one terminal, processable selected attempt and its durable lifecycle."""

    _self_hash(selection, "attemptSelectionHash")
    selected = selection.get("selectedAttemptNumber")
    if not isinstance(selected, int) or selected < 1 or selected > 2:
        raise Pilot1EvaluationRealizationFreezeError("NONPROCESSABLE_OR_NONTERMINAL_SELECTION")
    if selection.get("selectionDisposition") != "first_processable_response_selected":
        raise Pilot1EvaluationRealizationFreezeError("UNEXPECTED_TERMINAL_SELECTION_DISPOSITION")
    attempts = selection.get("attempts", [])
    if not isinstance(attempts, list) or not 1 <= len(attempts) <= 2:
        raise Pilot1EvaluationRealizationFreezeError("INVALID_PROVIDER_ATTEMPT_COUNT")
    selected_record = next((row for row in attempts if isinstance(row, Mapping) and row.get("attemptNumber") == selected), None)
    if not isinstance(selected_record, Mapping):
        raise Pilot1EvaluationRealizationFreezeError("SELECTED_ATTEMPT_ABSENT")
    for row in attempts:
        if not isinstance(row, Mapping) or not isinstance(row.get("attemptNumber"), int):
            raise Pilot1EvaluationRealizationFreezeError("INVALID_ATTEMPT_RECORD")
        lifecycle = _load(request_root / f"attempt-{row['attemptNumber']:02d}" / "lifecycle.json")
        if lifecycle != row:
            raise Pilot1EvaluationRealizationFreezeError("ATTEMPT_SELECTION_LIFECYCLE_DRIFT")
    return selected, dict(selected_record)


def _build_records(ordinal: int, binding_record: Mapping[str, Any], source_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Audit one selected authentic request and project tracked freeze records."""

    request_id = binding_record.get("requestID")
    if not isinstance(request_id, str) or not request_id:
        raise Pilot1EvaluationRealizationFreezeError("BINDING_REQUEST_ID_INVALID")
    cohort = binding_record.get("executionCohort")
    if cohort not in {"human_core_n5", "step5_n6"}:
        raise Pilot1EvaluationRealizationFreezeError("EXECUTION_COHORT_INVALID")
    request_root = source_root / "requests" / request_id
    selection = _load(request_root / "attempt_selection.json")
    selected_number, selected = _selected_attempt(selection, request_root)
    attempt_root = request_root / f"attempt-{selected_number:02d}"
    required = {
        "provider_request.json", "provider_response.json", "provider_metadata.json",
        "raw_model_output.json", "parser_result.json", "validation_results.json",
        "usable_pipeline_output.json", "lifecycle.json", "parsed_candidate.json",
        "accepted_semantic_projection.json", "unresolved_identity_sidecar.json",
    }
    if any(not (attempt_root / name).is_file() for name in required - {"accepted_semantic_projection.json", "unresolved_identity_sidecar.json"}) or any(not (request_root / name).is_file() for name in {"accepted_semantic_projection.json", "unresolved_identity_sidecar.json"}):
        raise Pilot1EvaluationRealizationFreezeError(f"SELECTED_ATTEMPT_PROVENANCE_ABSENT:{request_id}")
    provider_request = _load(attempt_root / "provider_request.json")
    provider_response = _load(attempt_root / "provider_response.json")
    provider_metadata = _load(attempt_root / "provider_metadata.json")
    parser = _load(attempt_root / "parser_result.json")
    validation = _load(attempt_root / "validation_results.json")
    usable = _load(attempt_root / "usable_pipeline_output.json")
    projection = _load(request_root / "accepted_semantic_projection.json")
    sidecar = _load(request_root / "unresolved_identity_sidecar.json")
    for value, field in ((validation, "validationResultsHash"), (usable, "usablePipelineOutputHash"),
                         (projection, "acceptedSemanticProjectionHash"), (sidecar, "unresolvedIdentitySidecarHash")):
        _self_hash(value, field)
    raw = (attempt_root / "raw_model_output.json").read_bytes()
    raw_hash = sha256_bytes(raw)
    body_hash = sha256_bytes(canonical_json(provider_request))
    schema = provider_request.get("text", {}).get("format", {}).get("schema")
    if not isinstance(schema, Mapping):
        raise Pilot1EvaluationRealizationFreezeError("PROVIDER_SCHEMA_ABSENT")
    checks = {
        "requestID": request_id,
        "requestInputSha256": binding_record["requestInputSha256"],
        "providerRequestBodySha256": body_hash,
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
        "rawOutputSha256": raw_hash,
        "providerMetadataSha256": sha256_bytes(canonical_json(provider_metadata)),
        "providerResponseSha256": sha256_bytes(canonical_json(provider_response)),
    }
    if checks["providerRequestBodySha256"] != binding_record["providerRequestBodySha256"] or checks["modelAuthorableSchemaSha256"] != binding_record["modelAuthorableSchemaSha256"]:
        raise Pilot1EvaluationRealizationFreezeError("FROZEN_REQUEST_BODY_OR_SCHEMA_DRIFT")
    if provider_request.get("max_output_tokens") != 32768 or selected.get("maxOutputTokens") != 32768:
        raise Pilot1EvaluationRealizationFreezeError("FROZEN_MAX_OUTPUT_TOKENS_DRIFT")
    if provider_metadata.get("rawModelOutputSha256") != raw_hash or provider_metadata.get("rawProviderResponseSha256") != checks["providerResponseSha256"]:
        raise Pilot1EvaluationRealizationFreezeError("PROVIDER_RAW_METADATA_DRIFT")
    if any(selected.get(field) != value for field, value in checks.items() if field not in {"requestID", "providerRequestBodySha256"}):
        raise Pilot1EvaluationRealizationFreezeError("SELECTED_ATTEMPT_PROVENANCE_DRIFT")
    if selected.get("parserResult") != parser or selected.get("validation") != validation or selected.get("usablePipelineOutput") != usable:
        raise Pilot1EvaluationRealizationFreezeError("SELECTED_PROCESSING_ARTIFACT_DRIFT")
    if parser.get("parseStatus") != "parsed" or selected.get("status") != "processed":
        raise Pilot1EvaluationRealizationFreezeError("SELECTED_ATTEMPT_NOT_PROCESSABLE")
    if projection.get("requestID") != request_id or projection.get("selectedProviderAttempt", {}).get("attemptNumber") != selected_number:
        raise Pilot1EvaluationRealizationFreezeError("ACCEPTED_PROJECTION_IDENTITY_DRIFT")
    if projection.get("attemptSelectionHash") != selection.get("attemptSelectionHash") or projection.get("validationResultsHash") != validation.get("validationResultsHash") or projection.get("usablePipelineOutputHash") != usable.get("usablePipelineOutputHash"):
        raise Pilot1EvaluationRealizationFreezeError("ACCEPTED_PROJECTION_PROVENANCE_DRIFT")
    if sidecar.get("selectedAttemptNumber") != selected_number or sidecar.get("validationResultsHash") != validation.get("validationResultsHash"):
        raise Pilot1EvaluationRealizationFreezeError("UNRESOLVED_SIDECAR_PROVENANCE_DRIFT")
    if projection.get("acceptanceStatus") != "production_accepted":
        raise Pilot1EvaluationRealizationFreezeError("PRODUCTION_ACCEPTANCE_NOT_ACCEPTED")

    prediction = _record({
        "ordinal": ordinal, "executionCohort": cohort,
        "primarySourceUnitID": binding_record["primarySourceUnitID"],
        "requestID": request_id, "requestInputSha256": binding_record["requestInputSha256"],
        "acceptedSemanticProjection": projection, "unresolvedIdentitySidecar": sidecar,
    }, "publication_pilot1_corrected_evaluation_canonical_prediction")
    lifecycle = _record({
        "ordinal": ordinal, "executionCohort": cohort, "requestID": request_id,
        "requestInputSha256": binding_record["requestInputSha256"],
        "selectionDisposition": selection["selectionDisposition"], "selectedAttemptNumber": selected_number,
        "providerAttemptCount": len(selection["attempts"]),
        "attempts": [{
            "attemptNumber": row["attemptNumber"], "status": row.get("status"),
            "parseStatus": row.get("parserResult", {}).get("parseStatus"),
            "processingCode": row.get("parserResult", {}).get("processingCode"),
            "envelopeStatus": row.get("validation", {}).get("envelopeStatus"),
            "rawOutputSha256": row.get("rawOutputSha256"),
            "providerMetadataSha256": row.get("providerMetadataSha256"),
            "providerResponseSha256": row.get("providerResponseSha256"),
        } for row in selection["attempts"]],
        "terminalProcessingFailures": [],
    }, "publication_pilot1_corrected_evaluation_lifecycle")
    index = _record({
        "ordinal": ordinal, "executionCohort": cohort,
        "primarySourceUnitID": binding_record["primarySourceUnitID"],
        "requestID": request_id, "requestInputSha256": binding_record["requestInputSha256"],
        "providerRequestBodySha256": binding_record["providerRequestBodySha256"],
        "modelAuthorableSchemaSha256": binding_record["modelAuthorableSchemaSha256"],
        "contextSourceUnitIDs": binding_record["contextSourceUnitIDs"],
        "productionTargetIDs": binding_record["productionTargetIDs"],
        "providerAttemptCount": len(selection["attempts"]), "selectedAttemptNumber": selected_number,
        "selectionDisposition": selection["selectionDisposition"], "parserStatus": parser["parseStatus"],
        "envelopeStatus": validation.get("envelopeStatus"), "productionAcceptanceStatus": projection["acceptanceStatus"],
        "rawOutputSha256": raw_hash, "providerMetadataSha256": checks["providerMetadataSha256"],
        "providerResponseSha256": checks["providerResponseSha256"],
        "acceptedNodeCount": len(projection.get("acceptedNodes", [])),
        "acceptedEdgeCount": len(projection.get("acceptedEdges", [])),
        "unresolvedIdentityCount": len(sidecar.get("records", [])),
        "terminalProcessingFailureCount": 0,
        "acceptedSemanticProjectionSha256": sha256_bytes((request_root / "accepted_semantic_projection.json").read_bytes()),
        "unresolvedIdentitySidecarSha256": sha256_bytes((request_root / "unresolved_identity_sidecar.json").read_bytes()),
    }, "publication_pilot1_corrected_evaluation_result_index")
    return prediction, lifecycle, index


def derive_realization(source_root: Path = SOURCE_ROOT) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Read-only audit of all durable authentic requests and derived freeze records."""

    binding = _load(source_root / BINDING_NAME)
    _self_hash(binding, "artifactSha256")
    if binding.get("artifactSha256") != EXPECTED_BINDING_SHA256:
        raise Pilot1EvaluationRealizationFreezeError("EXECUTION_BINDING_IDENTITY_DRIFT")
    subset = binding.get("executionSubset", {})
    if subset.get("artifactSha256") != EXPECTED_SUBSET_SHA256 or subset.get("requestCount") != 11:
        raise Pilot1EvaluationRealizationFreezeError("EXECUTION_SUBSET_IDENTITY_DRIFT")
    records = binding.get("requests", [])
    if not isinstance(records, list) or len(records) != 11 or len({row.get("requestID") for row in records if isinstance(row, Mapping)}) != 11:
        raise Pilot1EvaluationRealizationFreezeError("EXECUTION_BINDING_REQUEST_COUNT_DRIFT")
    predictions: list[dict[str, Any]] = []
    lifecycles: list[dict[str, Any]] = []
    indexes: list[dict[str, Any]] = []
    for ordinal, record in enumerate(records, start=1):
        prediction, lifecycle, index = _build_records(ordinal, record, source_root)
        predictions.append(prediction); lifecycles.append(lifecycle); indexes.append(index)
    if len({row["requestID"] for row in indexes}) != 11:
        raise Pilot1EvaluationRealizationFreezeError("EXECUTION_REQUESTS_NOT_EXACTLY_ONCE")
    return binding, predictions, lifecycles, indexes


def materialize(source_root: Path = SOURCE_ROOT, output_root: Path = OUTPUT_ROOT) -> dict[str, Path]:
    """Freeze the audited realization without mutating the execution namespace."""

    before = _source_inventory(source_root)
    binding, predictions, lifecycles, indexes = derive_realization(source_root)
    prediction_path = output_root / PREDICTIONS_NAME
    lifecycle_path = output_root / LIFECYCLE_NAME
    index_path = output_root / INDEX_NAME
    _write_immutable(prediction_path, _jsonl_bytes(predictions))
    _write_immutable(lifecycle_path, _jsonl_bytes(lifecycles))
    _write_immutable(index_path, _jsonl_bytes(indexes))
    if _source_inventory(source_root) != before:
        raise Pilot1EvaluationRealizationFreezeError("DURABLE_EXECUTION_NAMESPACE_MUTATED")
    counts = {
        "requestCount": len(indexes), "authenticProviderAttemptCount": sum(row["providerAttemptCount"] for row in indexes),
        "selectedAttemptDistribution": dict(sorted(Counter(str(row["selectedAttemptNumber"]) for row in indexes).items())),
        "terminalDispositionDistribution": dict(sorted(Counter(row["selectionDisposition"] for row in indexes).items())),
        "parserStatusDistribution": dict(sorted(Counter(row["parserStatus"] for row in indexes).items())),
        "envelopeStatusDistribution": dict(sorted(Counter(str(row["envelopeStatus"]) for row in indexes).items())),
        "productionAcceptanceDistribution": dict(sorted(Counter(row["productionAcceptanceStatus"] for row in indexes).items())),
        "totalAcceptedNodes": sum(row["acceptedNodeCount"] for row in indexes),
        "totalAcceptedEdges": sum(row["acceptedEdgeCount"] for row in indexes),
        "unresolvedIdentityRecords": sum(row["unresolvedIdentityCount"] for row in indexes),
        "terminalProcessingFailures": sum(row["terminalProcessingFailureCount"] for row in indexes),
        "cohorts": {cohort: {"requestCount": sum(row["executionCohort"] == cohort for row in indexes), "acceptedNodes": sum(row["acceptedNodeCount"] for row in indexes if row["executionCohort"] == cohort), "acceptedEdges": sum(row["acceptedEdgeCount"] for row in indexes if row["executionCohort"] == cohort)} for cohort in ("human_core_n5", "step5_n6")},
    }
    freeze = {
        "artifactType": "publication_pilot1_corrected_evaluation_realization_freeze",
        "artifactVersion": FREEZE_VERSION, "status": "FROZEN_CLOSED",
        "executionBinding": {"path": str((source_root / BINDING_NAME).relative_to(PROJECT_ROOT)), "artifactSha256": binding["artifactSha256"], "requestCount": 11},
        "executionSubset": dict(binding["executionSubset"]),
        "correctedProductionManifest": dict(binding["correctedProductionManifest"]),
        "trackedArtifacts": {"predictions": _file_binding(prediction_path, 11), "lifecycleLedger": _file_binding(lifecycle_path, 11), "resultIndex": _file_binding(index_path, 11)},
        "canonicalProcessingAuthorities": list(binding["canonicalProcessingAuthorities"]),
        "canonicalCounts": counts,
        "providerModelCallsDuringFreeze": 0,
        "providerRedispatchDuringFreeze": False,
        "durableExecutionArtifactsByteIdentical": True,
        "durableExecutionArtifactInventory": {"artifactCount": len(before), "sha256": sha256_bytes(canonical_json(before))},
        "nextAction": "Step 7 Human Core N=5 confirmatory scoring using the frozen corrected-evaluation canonical predictions",
    }
    freeze["artifactSha256"] = sha256_bytes(canonical_json(freeze))
    freeze_path = output_root / FREEZE_NAME
    _write_immutable(freeze_path, canonical_json(freeze) + b"\n")
    return {"freeze": freeze_path, "predictions": prediction_path, "lifecycle": lifecycle_path, "index": index_path}


if __name__ == "__main__":
    for name, path in materialize().items():
        print(f"{name}: {path}")
