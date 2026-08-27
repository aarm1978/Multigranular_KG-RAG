"""Run the one-call M2-B1 structured OpenAI development smoke on DEV-04.

This runner derives its model-authorable transport schema from the frozen M1 candidate
schema, uses prompt v0.1.1, preserves the exact provider response and model output, and
passes the authentic output through the unchanged M1 parser and V1-V12 validator.
Artifacts are development-only and are not annotation, gold, or formal evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.candidate_validation import (  # noqa: E402
    VALIDATION_CONTRACT_VERSION,
    VALIDATOR_VERSION,
    materialize_usable_pipeline_output,
    validate_candidate_envelope,
)
from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    MODEL_AUTHORABLE_SCHEMA_VERSION,
    derive_model_authorable_schema,
    model_authorable_schema_record,
    validate_model_authorable_payload,
)
from src.extraction.llm.publications.openai_provider import (  # noqa: E402
    PROVIDER_ADAPTER_VERSION,
    PROVIDER_NAME,
    REASONING_EFFORT,
    REQUESTED_MODEL,
    STORE,
    OpenAIHTTPError,
    OpenAIProviderError,
    OpenAIProviderResponseError,
    Transport,
    bind_live_response_metadata,
    build_provider_input,
    call_openai_responses_detailed,
    load_openai_api_key,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    REQUEST_BUILDER_VERSION,
    build_development_request,
    canonical_json,
    canonical_json_file,
    sha256_bytes,
)
from src.extraction.llm.publications.response_parser import (  # noqa: E402
    PARSER_VERSION,
    canonical_parsed_envelope,
    parse_recorded_response,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/b1"
M2A_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2"
PROMPT_PATH = (
    PROJECT_ROOT
    / "src/extraction/llm/publications/prompts/publication_development_v0.1.1.txt"
)
PROMPT_VERSION = "publication-development-0.1.1"
SOURCE_UNIT_ID = "pub:36:sec:0026:unit:0001"
DEVELOPMENT_ID = "DEV-04"
AUTHORIZED_TARGETS = ["PUB-N-A-P16-FINDING"]
RUN_ID = "publication-live-structured-development-smoke/0.1.0"


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with exactly one final LF."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact model-authored or provider-input bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    """Return attempt-4 paths without overwriting preserved prior evidence."""

    return {
        "request": output_dir / "publication_m2b1_attempt4_live_request.json",
        "providerInput": output_dir / "publication_m2b1_attempt4_exact_provider_input.txt",
        "modelSchema": output_dir / "publication_m2b1_attempt4_model_authorable_schema.json",
        "modelSchemaRecord": output_dir / "publication_m2b1_attempt4_model_authorable_schema_record.json",
        "providerResponse": output_dir / "publication_m2b1_attempt4_provider_api_response.json",
        "providerMetadata": output_dir / "publication_m2b1_attempt4_provider_metadata.json",
        "rawModelOutput": output_dir / "publication_m2b1_attempt4_exact_structured_model_output.json",
        "parserResult": output_dir / "publication_m2b1_attempt4_parser_result.json",
        "parsedCandidate": output_dir / "publication_m2b1_attempt4_parsed_candidate.json",
        "validationResults": output_dir / "publication_m2b1_attempt4_validation_results.json",
        "usablePipelineOutput": output_dir / "publication_m2b1_attempt4_usable_pipeline_output.json",
        "comparison": output_dir / "publication_m2a_m2b1_attempt4_descriptive_comparison.json",
        "reproducibility": output_dir / "publication_m2b1_attempt4_reproducibility_record.json",
        "providerFailureResponse": output_dir / "publication_m2b1_attempt4_provider_failure_response.json",
        "providerFailureMetadata": output_dir / "publication_m2b1_attempt4_provider_failure_metadata.json",
        "attemptHistory": output_dir / "publication_m2b1_attempt_history.json",
    }


def _attempt_one_record() -> dict[str, Any]:
    """Record the historical pre-generation HTTP 400 without inventing diagnostics."""

    return {
        "attemptNumber": 1,
        "classification": "provider_transport_schema_failure_pre_generation",
        "httpRequestMade": True,
        "httpStatus": 400,
        "diagnosticBodyAvailable": False,
        "semanticResponseReceived": False,
        "modelAuthoredOutputProduced": False,
        "reportedTokenUsage": None,
        "parserEntered": False,
        "validatorEntered": False,
        "extractionObservation": False,
        "note": "Diagnostic body unavailable because the prior adapter discarded it.",
    }


def _write_attempt_history(
    path: Path, attempt_four: Mapping[str, Any]
) -> dict[str, Any]:
    """Persist all four attempts without erasing prior failure observations."""

    history = {
        "attemptHistorySchemaVersion": "0.1.0",
        "developmentID": DEVELOPMENT_ID,
        "sourceUnitID": SOURCE_UNIT_ID,
        "attempts": [
            _attempt_one_record(),
            {
                "attemptNumber": 2,
                "classification": "provider_transport_schema_failure_pre_generation",
                "httpRequestMade": True,
                "httpStatus": 400,
                "providerErrorCode": "invalid_json_schema",
                "providerErrorMessage": (
                    "Invalid schema ... In context=('anyOf', '0', 'properties', "
                    "'attributeName'), schema must have a 'type' key."
                ),
                "xRequestID": "req_bd16955f70f247b181d597630b79de2e",
                "diagnosticBodyAvailable": True,
                "semanticResponseReceived": False,
                "modelAuthoredOutputProduced": False,
                "reportedTokenUsage": None,
                "parserEntered": False,
                "validatorEntered": False,
                "extractionObservation": False,
            },
            {
                "attemptNumber": 3,
                "classification": "provider_transport_schema_failure_pre_generation",
                "httpRequestMade": True,
                "httpStatus": 400,
                "providerErrorCode": "invalid_json_schema",
                "providerErrorMessage": (
                    "Invalid schema ... context=('properties', 'sectionTitle'), "
                    "$ref cannot have keywords {'description'}."
                ),
                "xRequestID": "req_e888c69b30124734930e70231374200f",
                "diagnosticBodyAvailable": True,
                "semanticResponseReceived": False,
                "modelAuthoredOutputProduced": False,
                "reportedTokenUsage": None,
                "parserEntered": False,
                "validatorEntered": False,
                "extractionObservation": False,
            },
            deepcopy(dict(attempt_four)),
        ],
    }
    _write_canonical(path, history)
    return history


def build_m2b1_request() -> dict[str, Any]:
    """Build the trusted DEV-04 M1 request and bind development prompt v0.1.1."""

    request = build_development_request(
        SOURCE_UNIT_ID,
        AUTHORIZED_TARGETS,
        run_id=RUN_ID,
        prompt_path=PROMPT_PATH,
    )
    request = deepcopy(request)
    request["prompt"]["version"] = PROMPT_VERSION
    request.pop("requestInputSha256", None)
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    if request["eligibleOperationalTargetIDs"] != AUTHORIZED_TARGETS:
        raise ValueError("DEV-04 request is not bounded to the authorized Finding target")
    return request


def _downstream(
    raw_output: bytes, request: Mapping[str, Any]
) -> tuple[dict[str, Any], bytes | None, dict[str, Any], dict[str, Any]]:
    """Run the unchanged strict parser, validator, and usable-output materializer."""

    parser_result = parse_recorded_response(raw_output, request)
    parsed_bytes = (
        canonical_parsed_envelope(parser_result)
        if parser_result.get("parseStatus") == "parsed"
        else None
    )
    validation = validate_candidate_envelope(parser_result, request)
    usable = materialize_usable_pipeline_output(
        parser_result.get("parsedEnvelope", {}), validation
    )
    return parser_result, parsed_bytes, validation, usable


def _finding_count(validation: Mapping[str, Any], code: str) -> int:
    """Count one stable finding code throughout a validation artifact."""

    count = sum(item.get("code") == code for item in validation.get("globalFindings", []))
    for result in validation.get("evidenceResults", []):
        count += sum(item.get("code") == code for item in result.get("findings", []))
    for result in validation.get("recordResults", []):
        count += sum(item.get("code") == code for item in result.get("findings", []))
    return count


def _status_counts(validation: Mapping[str, Any]) -> dict[str, int]:
    """Count candidate and other record statuses deterministically."""

    counts: Counter[str] = Counter()
    for result in validation.get("recordResults", []):
        status = result.get("candidateValidationStatus", result.get("recordValidationStatus"))
        if status:
            counts[str(status)] += 1
    return dict(sorted(counts.items()))


def _structural_observations(payload: Mapping[str, Any]) -> dict[str, int]:
    """Count the concrete schema-shape defects observed in the M2-A response."""

    nodes = [row for row in payload.get("candidateNodes", []) if isinstance(row, Mapping)]
    edges = [row for row in payload.get("candidateEdges", []) if isinstance(row, Mapping)]
    evidence = [row for row in payload.get("evidenceSpans", []) if isinstance(row, Mapping)]
    candidates = [*nodes, *edges]
    target_definition_fields = {
        "kind",
        "directInstantiation",
        "emissionMode",
        "endpointUsage",
        "evidenceRequirement",
    }
    incorrect_candidate_fields = {"ontologyID", "evidenceSpanIndices"}
    incorrect_evidence_fields = {"text"}
    return {
        "missingCandidateIDs": sum("candidateID" not in row for row in candidates),
        "missingEvidenceIDs": sum("evidenceSpanID" not in row for row in evidence),
        "forbiddenTargetDefinitionFields": sum(
            len(set(row) & target_definition_fields) for row in candidates
        ),
        "incorrectCandidateFieldNames": sum(
            len(set(row) & incorrect_candidate_fields) for row in candidates
        ),
        "incorrectEvidenceFieldNames": sum(
            len(set(row) & incorrect_evidence_fields) for row in evidence
        ),
    }


def build_descriptive_comparison(
    m2b1_payload: Mapping[str, Any],
    m2b1_validation: Mapping[str, Any],
    m2b1_usable: Mapping[str, Any],
    *,
    m2a_output_dir: Path = M2A_OUTPUT_DIR,
) -> dict[str, Any]:
    """Compare M2-A and M2-B1 structure without formal evaluation metrics."""

    m2a_payload = json.loads(
        (m2a_output_dir / "publication_m2a_exact_raw_model_output.json").read_text(
            encoding="utf-8"
        )
    )
    m2a_validation = json.loads(
        (m2a_output_dir / "publication_m2a_validation_results.json").read_text(
            encoding="utf-8"
        )
    )
    m2a_usable = json.loads(
        (m2a_output_dir / "publication_m2a_usable_pipeline_output.json").read_text(
            encoding="utf-8"
        )
    )

    def summary(
        payload: Mapping[str, Any],
        validation: Mapping[str, Any],
        usable: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Summarize one development observation without quality metrics."""

        return {
            "candidateCount": len(payload.get("candidateNodes", []))
            + len(payload.get("candidateEdges", [])),
            "schemaValidationFailureCount": _finding_count(
                validation, "SCHEMA_VALIDATION_FAILED"
            ),
            "validationEnvelopeStatus": validation.get("envelopeStatus"),
            "validationStatusCounts": _status_counts(validation),
            "usableCandidateCount": len(usable.get("candidateNodes", []))
            + len(usable.get("candidateEdges", [])),
            "structuralObservations": _structural_observations(payload),
        }

    comparison = {
        "comparisonSchemaVersion": "0.1.0",
        "purpose": "descriptive_development_comparison_not_formal_evaluation",
        "m2a": summary(m2a_payload, m2a_validation, m2a_usable),
        "m2b1": summary(m2b1_payload, m2b1_validation, m2b1_usable),
        "semanticImprovementClaimed": False,
    }
    comparison["structuralErrorsObservedInM2AEliminated"] = all(
        value == 0 for value in comparison["m2b1"]["structuralObservations"].values()
    )
    return comparison


def _reproducibility_record(
    request: Mapping[str, Any],
    provider_input: bytes,
    schema: Mapping[str, Any],
    schema_record: Mapping[str, Any],
    response_record: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    raw_output: bytes,
    parser_result: Mapping[str, Any],
    parsed_bytes: bytes | None,
    validation: Mapping[str, Any],
    usable: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the deterministic M2-B1 live-call and downstream replay record."""

    authorities = request["authorities"]
    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": "publication_structured_live_development_smoke",
        "developmentOnly": True,
        "liveOpenAIOutput": True,
        "notAnnotation": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "liveGenerationDeterministic": False,
        "downstreamReplayDeterministic": True,
        "runID": RUN_ID,
        "developmentID": DEVELOPMENT_ID,
        "sourceUnitID": request["primarySourceUnitID"],
        "sourcePublicationID": request["sourcePublicationID"],
        "requestID": request["requestID"],
        "requestInputSha256": request["requestInputSha256"],
        "providerInputSha256": sha256_bytes(provider_input),
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "targetProfile": authorities["targetInventory"],
        "candidateSchema": authorities["candidateSchema"],
        "ontology": authorities["ontology"],
        "modelAuthorableSchemaVersion": MODEL_AUTHORABLE_SCHEMA_VERSION,
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
        "modelAuthorableSchemaRecordHash": schema_record["recordSha256"],
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "providerAdapterVersion": PROVIDER_ADAPTER_VERSION,
        "provider": PROVIDER_NAME,
        "requestedModel": REQUESTED_MODEL,
        "returnedModel": response_record["returnedModel"],
        "reasoningEffort": REASONING_EFFORT,
        "toolConfiguration": "none",
        "store": STORE,
        "structuredOutput": {
            "enabled": True,
            "apiField": "text.format",
            "type": "json_schema",
            "strict": True,
        },
        "apiResponseID": response_record["responseID"],
        "apiStatus": response_record["status"],
        "tokenUsage": response_record["usage"],
        "retryCount": response_record["retryCount"],
        "costUSD": None,
        "providerResponseSha256": sha256_bytes(canonical_json(raw_response)),
        "rawModelOutputSha256": sha256_bytes(raw_output),
        "parserResultSha256": sha256_bytes(canonical_json(parser_result)),
        "parsedCandidateSha256": (
            sha256_bytes(parsed_bytes) if parsed_bytes is not None else None
        ),
        "validationResultsHash": validation.get("validationResultsHash"),
        "validationArtifactSha256": sha256_bytes(canonical_json(validation)),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"),
        "usableArtifactSha256": sha256_bytes(canonical_json(usable)),
        "comparisonSha256": sha256_bytes(canonical_json(comparison)),
        "parseStatus": parser_result.get("parseStatus"),
    }
    record["reproducibilityRecordHash"] = sha256_bytes(canonical_json(record))
    return record


def run_structured_live_smoke(
    api_key: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Make one guarded structured call and traverse unchanged deterministic stages."""

    request = build_m2b1_request()
    schema = derive_model_authorable_schema()
    schema_record = model_authorable_schema_record()
    provider_input = build_provider_input(request)
    paths = _artifact_paths(output_dir)
    # Preserve the exact retry input and schema before network activity so a failed
    # transport attempt remains auditable without entering semantic processing.
    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["modelSchema"], schema)
    _write_canonical(paths["modelSchemaRecord"], schema_record)
    call_kwargs = {} if transport is None else {"transport": transport}
    try:
        raw_output, response_record, raw_response = call_openai_responses_detailed(
            api_key,
            provider_input,
            model_authorable_schema=schema,
            **call_kwargs,
        )
    except OpenAIHTTPError as exc:
        diagnostic = dict(exc.diagnostic)
        _write_canonical(paths["providerFailureMetadata"], diagnostic)
        _write_canonical(
            paths["providerFailureResponse"],
            {
                "responseBodyBase64": diagnostic["responseBodyBase64"],
                "responseBodyText": diagnostic["responseBodyText"],
                "decodedJSONError": diagnostic["decodedJSONError"],
                "credentialRedactionApplied": diagnostic["credentialRedactionApplied"],
            },
        )
        _write_attempt_history(
            paths["attemptHistory"],
            {
                "attemptNumber": 4,
                "classification": "provider_http_failure_pre_generation",
                "httpRequestMade": True,
                "httpStatus": diagnostic["httpStatus"],
                "xRequestID": diagnostic["xRequestID"],
                "diagnosticBodyAvailable": True,
                "semanticResponseReceived": False,
                "modelAuthoredOutputProduced": False,
                "reportedTokenUsage": None,
                "parserEntered": False,
                "validatorEntered": False,
                "extractionObservation": False,
            },
        )
        raise
    except OpenAIProviderResponseError as exc:
        failure_metadata = dict(exc.response_record)
        failure_metadata["providerRunFailureCode"] = exc.failure_code
        _write_canonical(paths["providerFailureResponse"], exc.response)
        _write_canonical(paths["providerFailureMetadata"], failure_metadata)
        _write_attempt_history(
            paths["attemptHistory"],
            {
                "attemptNumber": 4,
                "classification": "provider_semantic_response_rejected_by_guard",
                "httpRequestMade": True,
                "httpStatus": 200,
                "diagnosticBodyAvailable": True,
                "semanticResponseReceived": True,
                "modelAuthoredOutputProduced": False,
                "reportedTokenUsage": failure_metadata.get("usage"),
                "parserEntered": False,
                "validatorEntered": False,
                "extractionObservation": False,
                "providerRunFailureCode": exc.failure_code,
            },
        )
        raise

    response_record["retryCount"] = 3
    request = bind_live_response_metadata(request, response_record)
    if build_provider_input(request) != provider_input:
        raise ValueError("provider input changed while binding live response metadata")
    payload = json.loads(raw_output.decode("utf-8"))
    schema_errors = validate_model_authorable_payload(payload, schema)
    if schema_errors:
        raise ValueError("provider structured output violated its supplied JSON Schema")

    first = _downstream(raw_output, request)
    comparison = build_descriptive_comparison(first[0].get("parsedDocument", {}), first[2], first[3])
    first_reproducibility = _reproducibility_record(
        request,
        provider_input,
        schema,
        schema_record,
        response_record,
        raw_response,
        raw_output,
        first[0],
        first[1],
        first[2],
        first[3],
        comparison,
    )
    replay_one = _downstream(raw_output, request)
    replay_two = _downstream(raw_output, request)
    replay_one_reproducibility = _reproducibility_record(
        request,
        provider_input,
        schema,
        schema_record,
        response_record,
        raw_response,
        raw_output,
        replay_one[0],
        replay_one[1],
        replay_one[2],
        replay_one[3],
        comparison,
    )
    replay_two_reproducibility = _reproducibility_record(
        request,
        provider_input,
        schema,
        schema_record,
        response_record,
        raw_response,
        raw_output,
        replay_two[0],
        replay_two[1],
        replay_two[2],
        replay_two[3],
        comparison,
    )
    replay_bytes_one = (
        replay_one[1],
        canonical_json(replay_one[2]),
        canonical_json(replay_one[3]),
        canonical_json(replay_one_reproducibility),
    )
    replay_bytes_two = (
        replay_two[1],
        canonical_json(replay_two[2]),
        canonical_json(replay_two[3]),
        canonical_json(replay_two_reproducibility),
    )
    if replay_bytes_one != replay_bytes_two:
        raise ValueError("M2-B1 deterministic downstream replay is not byte-identical")
    if canonical_json(first_reproducibility) != replay_bytes_one[3]:
        raise ValueError("initial and replayed reproducibility records differ")

    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["modelSchema"], schema)
    _write_canonical(paths["modelSchemaRecord"], schema_record)
    _write_canonical(paths["providerResponse"], raw_response)
    _write_canonical(paths["providerMetadata"], response_record)
    _write_exact(paths["rawModelOutput"], raw_output)
    _write_canonical(paths["parserResult"], first[0])
    if first[1] is not None:
        _write_exact(paths["parsedCandidate"], first[1])
    _write_canonical(paths["validationResults"], first[2])
    _write_canonical(paths["usablePipelineOutput"], first[3])
    _write_canonical(paths["comparison"], comparison)
    _write_canonical(paths["reproducibility"], first_reproducibility)
    attempt_history = _write_attempt_history(
        paths["attemptHistory"],
        {
            "attemptNumber": 4,
            "classification": "completed_semantic_response",
            "httpRequestMade": True,
            "httpStatus": 200,
            "diagnosticBodyAvailable": True,
            "semanticResponseReceived": True,
            "modelAuthoredOutputProduced": True,
            "reportedTokenUsage": response_record["usage"],
            "parserEntered": True,
            "validatorEntered": True,
            "extractionObservation": True,
            "responseID": response_record["responseID"],
        },
    )
    return {
        "request": request,
        "providerResponse": response_record,
        "rawProviderResponse": raw_response,
        "rawModelOutput": raw_output,
        "parserResult": first[0],
        "validation": first[2],
        "usablePipelineOutput": first[3],
        "comparison": comparison,
        "reproducibility": first_reproducibility,
        "replayByteIdentical": True,
        "attemptHistory": attempt_history,
        "artifactPaths": {key: str(value) for key, value in paths.items()},
    }


def replay_preserved(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay preserved M2-B1 output twice without a provider call."""

    paths = _artifact_paths(output_dir)
    request = json.loads(paths["request"].read_text(encoding="utf-8"))
    raw_output = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw_output, request)
    second = _downstream(raw_output, request)
    first_bytes = (first[1], canonical_json(first[2]), canonical_json(first[3]))
    second_bytes = (second[1], canonical_json(second[2]), canonical_json(second[3]))
    if first_bytes != second_bytes:
        raise ValueError("preserved M2-B1 replay is not byte-identical")
    return {
        "byteIdentical": True,
        "parsedCandidateSha256": (
            sha256_bytes(first_bytes[0]) if first_bytes[0] is not None else None
        ),
        "validationResultsSha256": sha256_bytes(first_bytes[1]),
        "usablePipelineOutputSha256": sha256_bytes(first_bytes[2]),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the M2-B1 live/replay command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replay-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one structured live smoke or a no-network preserved replay."""

    args = build_argument_parser().parse_args(argv)
    try:
        if args.replay_only:
            print(json.dumps(replay_preserved(args.output_dir), sort_keys=True))
            return 0
        result = run_structured_live_smoke(
            load_openai_api_key(), output_dir=args.output_dir
        )
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-B1 structured smoke failed: {exc}", file=sys.stderr)
        return 1
    usable = result["usablePipelineOutput"]
    print(f"response ID: {result['providerResponse']['responseID']}")
    print(f"returned model: {result['providerResponse']['returnedModel']}")
    print(f"parse status: {result['parserResult']['parseStatus']}")
    print(f"envelope status: {result['validation']['envelopeStatus']}")
    print(f"status counts: {json.dumps(_status_counts(result['validation']), sort_keys=True)}")
    print(f"usable candidates: {len(usable['candidateNodes']) + len(usable['candidateEdges'])}")
    print(f"raw output SHA-256: {result['reproducibility']['rawModelOutputSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
