"""Run the one-call M2-B2 request-specialized OpenAI smoke on DEV-04."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    audit_openai_structured_outputs_schema,
    derive_model_authorable_schema,
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
from src.extraction.llm.publications.request_specialized_schema import (  # noqa: E402
    REQUEST_SPECIALIZED_SCHEMA_VERSION,
    derive_request_specialized_schema,
    request_specialized_schema_record,
)
from src.extraction.llm.publications.response_parser import PARSER_VERSION  # noqa: E402
from src.extraction.llm.publications.candidate_validation import (  # noqa: E402
    VALIDATION_CONTRACT_VERSION,
    VALIDATOR_VERSION,
)
from src.extraction.llm.publications.run_publication_structured_development_smoke import (  # noqa: E402
    AUTHORIZED_TARGETS,
    DEVELOPMENT_ID,
    M2A_OUTPUT_DIR,
    PROMPT_PATH,
    PROMPT_VERSION,
    SOURCE_UNIT_ID,
    _downstream,
    _finding_count,
    _status_counts,
    _structural_observations,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/b2"
M2B1_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/b1"
RUN_ID = "publication-live-request-specialized-development-smoke/0.1.0"


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with one final line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact provider or model bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    """Return isolated M2-B2 development artifact paths."""

    prefix = "publication_m2b2"
    return {
        "request": output_dir / f"{prefix}_live_request.json",
        "providerInput": output_dir / f"{prefix}_exact_provider_input.txt",
        "genericSchemaComparison": output_dir / f"{prefix}_generic_specialized_schema_comparison.json",
        "modelSchema": output_dir / f"{prefix}_request_specialized_schema.json",
        "modelSchemaRecord": output_dir / f"{prefix}_request_specialized_schema_record.json",
        "providerResponse": output_dir / f"{prefix}_provider_api_response.json",
        "providerMetadata": output_dir / f"{prefix}_provider_metadata.json",
        "rawModelOutput": output_dir / f"{prefix}_exact_structured_model_output.json",
        "parserResult": output_dir / f"{prefix}_parser_result.json",
        "parsedCandidate": output_dir / f"{prefix}_parsed_candidate.json",
        "validationResults": output_dir / f"{prefix}_validation_results.json",
        "usablePipelineOutput": output_dir / f"{prefix}_usable_pipeline_output.json",
        "comparison": output_dir / f"{prefix}_m2a_m2b1_m2b2_descriptive_comparison.json",
        "reproducibility": output_dir / f"{prefix}_reproducibility_record.json",
        "providerFailureResponse": output_dir / f"{prefix}_provider_failure_response.json",
        "providerFailureMetadata": output_dir / f"{prefix}_provider_failure_metadata.json",
    }


def build_m2b2_request() -> dict[str, Any]:
    """Build DEV-04 with the unchanged v0.1.1 prompt and a distinct M2-B2 run ID."""

    request = build_development_request(SOURCE_UNIT_ID, AUTHORIZED_TARGETS, run_id=RUN_ID, prompt_path=PROMPT_PATH)
    request = deepcopy(request)
    request["prompt"]["version"] = PROMPT_VERSION
    request.pop("requestInputSha256", None)
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    if request["eligibleOperationalTargetIDs"] != AUTHORIZED_TARGETS:
        raise ValueError("M2-B2 request is not bounded to Finding")
    return request


def build_schema_comparison(generic: Mapping[str, Any], specialized: Mapping[str, Any]) -> dict[str, Any]:
    """Compare canonical schema size and exposed operational identifiers."""

    def exposed(schema: Mapping[str, Any], field: str) -> list[str]:
        """Collect const/enum values for one operational identifier property."""

        values: set[str] = set()
        def walk(value: Any) -> None:
            """Walk schema-valued positions without resolving references."""
            if not isinstance(value, Mapping):
                return
            properties = value.get("properties", {})
            if field in properties:
                definition = properties[field]
                if isinstance(definition, Mapping):
                    if isinstance(definition.get("const"), str):
                        values.add(definition["const"])
                    values.update(item for item in definition.get("enum", []) if isinstance(item, str))
            for child in properties.values(): walk(child)
            if isinstance(value.get("items"), Mapping): walk(value["items"])
            for branch in value.get("anyOf", []): walk(branch)
            for child in value.get("$defs", {}).values(): walk(child)
        walk(schema)
        return sorted(values)

    def summary(schema: Mapping[str, Any]) -> dict[str, Any]:
        """Return one deterministic schema summary."""
        encoded = canonical_json(schema)
        audit = audit_openai_structured_outputs_schema(schema)
        return {
            "canonicalSchemaBytes": len(encoded), "schemaSha256": sha256_bytes(encoded),
            "exposedNodeOperationalTargetIDs": exposed(schema, "operationalTargetID"),
            "exposedRelationOperationalTargetIDs": exposed(schema, "operationalRelationID"),
            "objectPropertyCount": audit["metrics"]["totalObjectPropertyCount"],
            "enumValueCount": audit["metrics"]["totalEnumValueCount"],
        }
    return {"comparisonSchemaVersion": "0.1.0", "purpose": "transport_schema_size_and_target_exposure_not_evaluation", "genericM2B1": summary(generic), "requestSpecializedM2B2": summary(specialized)}


def _observation(payload: Mapping[str, Any], validation: Mapping[str, Any], usable: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize one preserved development observation without formal metrics."""

    evidence_results = validation.get("evidenceResults", [])
    return {
        "candidateCount": len(payload.get("candidateNodes", [])) + len(payload.get("candidateEdges", [])),
        "schemaValidationFailureCount": _finding_count(validation, "SCHEMA_VALIDATION_FAILED"),
        "validEvidenceSpanCount": sum(row.get("valid") is True for row in evidence_results),
        "evidenceSpanCount": len(evidence_results), "validationEnvelopeStatus": validation.get("envelopeStatus"),
        "validationStatusCounts": _status_counts(validation),
        "usableCandidateCount": len(usable.get("candidateNodes", [])) + len(usable.get("candidateEdges", [])),
        "structuralObservations": _structural_observations(payload),
    }


def build_three_way_comparison(payload: Mapping[str, Any], validation: Mapping[str, Any], usable: Mapping[str, Any]) -> dict[str, Any]:
    """Describe M2-A, M2-B1, and M2-B2 without accuracy claims."""

    def load(directory: Path, stem: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Load one historical observation's immutable artifacts."""
        return (
            json.loads((directory / f"{stem}_exact_raw_model_output.json").read_text()) if stem == "publication_m2a" else json.loads((directory / f"{stem}_exact_structured_model_output.json").read_text()),
            json.loads((directory / f"{stem}_validation_results.json").read_text()),
            json.loads((directory / f"{stem}_usable_pipeline_output.json").read_text()),
        )
    m2a = load(M2A_OUTPUT_DIR, "publication_m2a")
    m2b1 = load(M2B1_OUTPUT_DIR, "publication_m2b1_attempt4")
    return {"comparisonSchemaVersion": "0.1.0", "purpose": "descriptive_development_comparison_not_formal_evaluation", "m2a": _observation(*m2a), "m2b1Attempt4": _observation(*m2b1), "m2b2": _observation(payload, validation, usable), "formalAccuracyClaimed": False}


def _reproducibility_record(request: Mapping[str, Any], provider_input: bytes, schema: Mapping[str, Any], schema_record: Mapping[str, Any], response: Mapping[str, Any], raw_response: Mapping[str, Any], raw_output: bytes, parser: Mapping[str, Any], parsed: bytes | None, validation: Mapping[str, Any], usable: Mapping[str, Any], comparison: Mapping[str, Any]) -> dict[str, Any]:
    """Bind the live call and deterministic M1 downstream artifact hashes."""

    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0", "purpose": "publication_request_specialized_live_development_smoke",
        "developmentOnly": True, "liveOpenAIOutput": True, "notAnnotation": True, "notGold": True, "notFormalEvaluation": True,
        "liveGenerationDeterministic": False, "downstreamReplayDeterministic": True, "runID": RUN_ID,
        "developmentID": DEVELOPMENT_ID, "sourceUnitID": request["primarySourceUnitID"], "requestID": request["requestID"],
        "requestInputSha256": request["requestInputSha256"], "providerInputSha256": sha256_bytes(provider_input),
        "promptVersion": request["prompt"]["version"], "promptSha256": request["prompt"]["sha256"],
        "requestSpecializedSchemaVersion": REQUEST_SPECIALIZED_SCHEMA_VERSION, "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
        "modelAuthorableSchemaRecordHash": schema_record["recordSha256"], "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION, "validatorVersion": VALIDATOR_VERSION, "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "providerAdapterVersion": PROVIDER_ADAPTER_VERSION, "provider": PROVIDER_NAME, "requestedModel": REQUESTED_MODEL,
        "returnedModel": response["returnedModel"], "reasoningEffort": REASONING_EFFORT, "toolConfiguration": "none", "store": STORE,
        "structuredOutput": {"enabled": True, "apiField": "text.format", "type": "json_schema", "strict": True, "requestSpecialized": True},
        "apiResponseID": response["responseID"], "apiStatus": response["status"], "tokenUsage": response["usage"], "retryCount": response["retryCount"], "costUSD": None,
        "providerResponseSha256": sha256_bytes(canonical_json(raw_response)), "rawModelOutputSha256": sha256_bytes(raw_output),
        "parserResultSha256": sha256_bytes(canonical_json(parser)), "parsedCandidateSha256": sha256_bytes(parsed) if parsed else None,
        "validationResultsHash": validation.get("validationResultsHash"), "validationArtifactSha256": sha256_bytes(canonical_json(validation)),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"), "usableArtifactSha256": sha256_bytes(canonical_json(usable)),
        "comparisonSha256": sha256_bytes(canonical_json(comparison)), "parseStatus": parser.get("parseStatus"),
    }
    record["reproducibilityRecordHash"] = sha256_bytes(canonical_json(record))
    return record


def run_request_specialized_live_smoke(api_key: str, *, output_dir: Path = DEFAULT_OUTPUT_DIR, transport: Transport | None = None) -> dict[str, Any]:
    """Make exactly one guarded M2-B2 call and replay deterministic stages twice."""

    request = build_m2b2_request(); generic = derive_model_authorable_schema(); schema = derive_request_specialized_schema(request)
    schema_record = request_specialized_schema_record(request); schema_comparison = build_schema_comparison(generic, schema)
    provider_input = build_provider_input(request); paths = _artifact_paths(output_dir)
    _write_canonical(paths["request"], request); _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["modelSchema"], schema); _write_canonical(paths["modelSchemaRecord"], schema_record); _write_canonical(paths["genericSchemaComparison"], schema_comparison)
    kwargs = {} if transport is None else {"transport": transport}
    try:
        raw_output, response, raw_response = call_openai_responses_detailed(api_key, provider_input, model_authorable_schema=schema, **kwargs)
    except OpenAIHTTPError as exc:
        diagnostic = dict(exc.diagnostic); _write_canonical(paths["providerFailureMetadata"], diagnostic)
        _write_canonical(paths["providerFailureResponse"], {"responseBodyBase64": diagnostic["responseBodyBase64"], "responseBodyText": diagnostic["responseBodyText"], "decodedJSONError": diagnostic["decodedJSONError"], "credentialRedactionApplied": diagnostic["credentialRedactionApplied"]})
        raise
    except OpenAIProviderResponseError as exc:
        metadata = dict(exc.response_record); metadata["providerRunFailureCode"] = exc.failure_code
        _write_canonical(paths["providerFailureResponse"], exc.response); _write_canonical(paths["providerFailureMetadata"], metadata); raise
    response["retryCount"] = 0
    request = bind_live_response_metadata(request, response)
    if build_provider_input(request) != provider_input: raise ValueError("provider input changed while binding metadata")
    payload = json.loads(raw_output.decode("utf-8"))
    if validate_model_authorable_payload(payload, schema): raise ValueError("structured output violated supplied request schema")
    first = _downstream(raw_output, request); comparison = build_three_way_comparison(first[0].get("parsedDocument", {}), first[2], first[3])
    record = _reproducibility_record(request, provider_input, schema, schema_record, response, raw_response, raw_output, first[0], first[1], first[2], first[3], comparison)
    replay_one = _downstream(raw_output, request); replay_two = _downstream(raw_output, request)
    record_one = _reproducibility_record(request, provider_input, schema, schema_record, response, raw_response, raw_output, replay_one[0], replay_one[1], replay_one[2], replay_one[3], comparison)
    record_two = _reproducibility_record(request, provider_input, schema, schema_record, response, raw_response, raw_output, replay_two[0], replay_two[1], replay_two[2], replay_two[3], comparison)
    if (replay_one[1], canonical_json(replay_one[2]), canonical_json(replay_one[3]), canonical_json(record_one)) != (replay_two[1], canonical_json(replay_two[2]), canonical_json(replay_two[3]), canonical_json(record_two)) or canonical_json(record) != canonical_json(record_one):
        raise ValueError("M2-B2 downstream replay is not byte-identical")
    _write_canonical(paths["request"], request); _write_canonical(paths["providerResponse"], raw_response); _write_canonical(paths["providerMetadata"], response)
    _write_exact(paths["rawModelOutput"], raw_output); _write_canonical(paths["parserResult"], first[0])
    if first[1] is not None: _write_exact(paths["parsedCandidate"], first[1])
    _write_canonical(paths["validationResults"], first[2]); _write_canonical(paths["usablePipelineOutput"], first[3]); _write_canonical(paths["comparison"], comparison); _write_canonical(paths["reproducibility"], record)
    return {"request": request, "providerResponse": response, "rawProviderResponse": raw_response, "rawModelOutput": raw_output, "parserResult": first[0], "validation": first[2], "usablePipelineOutput": first[3], "comparison": comparison, "schemaComparison": schema_comparison, "reproducibility": record, "replayByteIdentical": True, "artifactPaths": {key: str(value) for key, value in paths.items()}}


def replay_preserved(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay preserved M2-B2 output twice without a provider call."""
    paths = _artifact_paths(output_dir); request = json.loads(paths["request"].read_text()); raw = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw, request); second = _downstream(raw, request)
    values1 = (first[1], canonical_json(first[2]), canonical_json(first[3])); values2 = (second[1], canonical_json(second[2]), canonical_json(second[3]))
    if values1 != values2: raise ValueError("preserved M2-B2 replay differs")
    return {"byteIdentical": True, "parsedCandidateSha256": sha256_bytes(values1[0]) if values1[0] else None, "validationResultsSha256": sha256_bytes(values1[1]), "usablePipelineOutputSha256": sha256_bytes(values1[2])}


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one M2-B2 call or a no-network replay."""
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR); parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = replay_preserved(args.output_dir) if args.replay_only else run_request_specialized_live_smoke(load_openai_api_key(), output_dir=args.output_dir)
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-B2 request-specialized smoke failed: {exc}", file=sys.stderr); return 1
    print(json.dumps(result if args.replay_only else {"responseID": result["providerResponse"]["responseID"], "parseStatus": result["parserResult"]["parseStatus"], "envelopeStatus": result["validation"]["envelopeStatus"], "usableCandidates": len(result["usablePipelineOutput"]["candidateNodes"]) + len(result["usablePipelineOutput"]["candidateEdges"]), "rawOutputSha256": result["reproducibility"]["rawModelOutputSha256"]}, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
