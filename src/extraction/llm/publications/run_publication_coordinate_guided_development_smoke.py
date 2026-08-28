"""Run the one-call M2-B3 coordinate-guided OpenAI smoke on Publication DEV-04."""

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

from src.extraction.llm.publications.candidate_validation import (  # noqa: E402
    VALIDATION_CONTRACT_VERSION,
    VALIDATOR_VERSION,
)
from src.extraction.llm.publications.evidence_coordinate_guide import (  # noqa: E402
    COORDINATE_GUIDE_VERSION,
    audit_evidence_coordinate_guide,
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
    coordinate_guide_record,
)
from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    audit_openai_structured_outputs_schema,
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
    DEVELOPMENT_MANIFEST_PATH,
    REQUEST_BUILDER_VERSION,
    build_development_request,
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
)
from src.extraction.llm.publications.request_specialized_schema import (  # noqa: E402
    REQUEST_SPECIALIZED_SCHEMA_VERSION,
    derive_request_specialized_schema,
    request_specialized_schema_record,
)
from src.extraction.llm.publications.response_parser import PARSER_VERSION  # noqa: E402
from src.extraction.llm.publications.run_publication_request_specialized_development_smoke import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as M2B2_OUTPUT_DIR,
    _observation,
)
from src.extraction.llm.publications.run_publication_structured_development_smoke import (  # noqa: E402
    AUTHORIZED_TARGETS,
    DEVELOPMENT_ID,
    SOURCE_UNIT_ID,
    _downstream,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/b3"
PROMPT_PATH = PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.2.txt"
PROMPT_VERSION = "publication-development-0.1.2"
RUN_ID = "publication-live-coordinate-guided-development-smoke/0.1.0"
SIZE_REPORT_RUN_ID = "publication-coordinate-guide-size-diagnostic/0.1.0"


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with exactly one final line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    """Return isolated M2-B3 development artifact paths."""

    prefix = "publication_m2b3"
    return {
        "request": output_dir / f"{prefix}_live_request.json",
        "providerInput": output_dir / f"{prefix}_exact_provider_input.txt",
        "coordinateGuide": output_dir / f"{prefix}_evidence_coordinate_guide.json",
        "coordinateGuideRecord": output_dir / f"{prefix}_evidence_coordinate_guide_record.json",
        "sizeReport": output_dir / f"{prefix}_dev01_dev10_coordinate_guide_size_report.json",
        "modelSchema": output_dir / f"{prefix}_request_specialized_schema.json",
        "modelSchemaRecord": output_dir / f"{prefix}_request_specialized_schema_record.json",
        "providerResponse": output_dir / f"{prefix}_provider_api_response.json",
        "providerMetadata": output_dir / f"{prefix}_provider_metadata.json",
        "rawModelOutput": output_dir / f"{prefix}_exact_structured_model_output.json",
        "parserResult": output_dir / f"{prefix}_parser_result.json",
        "parsedCandidate": output_dir / f"{prefix}_parsed_candidate.json",
        "validationResults": output_dir / f"{prefix}_validation_results.json",
        "usablePipelineOutput": output_dir / f"{prefix}_usable_pipeline_output.json",
        "comparison": output_dir / f"{prefix}_m2b2_m2b3_descriptive_comparison.json",
        "reproducibility": output_dir / f"{prefix}_reproducibility_record.json",
        "providerFailureResponse": output_dir / f"{prefix}_provider_failure_response.json",
        "providerFailureMetadata": output_dir / f"{prefix}_provider_failure_metadata.json",
    }


def _bind_prompt_version(request: Mapping[str, Any]) -> dict[str, Any]:
    """Bind v0.1.2 while preserving the established request-builder semantics."""

    bound = deepcopy(dict(request))
    bound["prompt"]["version"] = PROMPT_VERSION
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def build_m2b3_request() -> dict[str, Any]:
    """Build the one authorized DEV-04 request with prompt v0.1.2."""

    request = build_development_request(
        SOURCE_UNIT_ID,
        AUTHORIZED_TARGETS,
        run_id=RUN_ID,
        prompt_path=PROMPT_PATH,
    )
    request = _bind_prompt_version(request)
    if request["eligibleOperationalTargetIDs"] != AUTHORIZED_TARGETS:
        raise ValueError("M2-B3 request is not bounded to Finding")
    return request


def build_dev_size_report() -> dict[str, Any]:
    """Measure guide/input bytes for DEV-01 through DEV-10 without network access."""

    rows = []
    manifest = load_json_object(DEVELOPMENT_MANIFEST_PATH)
    for manifest_row in manifest["units"]:
        development_id = manifest_row["developmentId"]
        request = build_development_request(
            manifest_row["sourceUnitID"],
            AUTHORIZED_TARGETS,
            run_id=f"{SIZE_REPORT_RUN_ID}/{development_id.lower()}",
            prompt_path=PROMPT_PATH,
        )
        request = _bind_prompt_version(request)
        guide = build_evidence_coordinate_guide(request["sourceUnit"])
        audit = audit_evidence_coordinate_guide(request["sourceUnit"], guide)
        if not audit["valid"]:
            raise ValueError(f"coordinate guide audit failed for {development_id}")
        current_input = build_provider_input(request)
        guided_input = build_coordinate_guided_provider_input(request, guide)
        rows.append(
            {
                "developmentID": development_id,
                "sourceUnitID": manifest_row["sourceUnitID"],
                "sourceUnitCharacterCount": len(request["sourceUnit"]["text"]),
                "coordinateGuideEntryCount": audit["entryCount"],
                "canonicalCoordinateGuideBytes": audit["canonicalBytes"],
                "currentProviderInputBytes": len(current_input),
                "providerInputBytesWithGuide": len(guided_input),
                "providerInputByteIncrease": len(guided_input) - len(current_input),
            }
        )
    return {
        "reportSchemaVersion": "0.1.0",
        "purpose": "offline_coordinate_guide_size_diagnostic_not_evaluation",
        "networkCalls": 0,
        "coordinateGuideVersion": COORDINATE_GUIDE_VERSION,
        "promptVersion": PROMPT_VERSION,
        "diagnosticTargetBinding": list(AUTHORIZED_TARGETS),
        "diagnosticTargetBindingPurpose": "constant_request_shape_for_byte_comparison_only",
        "units": rows,
    }


def build_b2_b3_comparison(
    payload: Mapping[str, Any], validation: Mapping[str, Any], usable: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare B3 descriptively with immutable B2, without accuracy claims."""

    b2_payload = json.loads(
        (M2B2_OUTPUT_DIR / "publication_m2b2_exact_structured_model_output.json").read_text()
    )
    b2_validation = json.loads(
        (M2B2_OUTPUT_DIR / "publication_m2b2_validation_results.json").read_text()
    )
    b2_usable = json.loads(
        (M2B2_OUTPUT_DIR / "publication_m2b2_usable_pipeline_output.json").read_text()
    )
    return {
        "comparisonSchemaVersion": "0.1.0",
        "purpose": "descriptive_development_comparison_not_formal_evaluation",
        "m2b2": _observation(b2_payload, b2_validation, b2_usable),
        "m2b3": _observation(payload, validation, usable),
        "formalAccuracyClaimed": False,
    }


def _reproducibility_record(
    request: Mapping[str, Any],
    provider_input: bytes,
    guide: Mapping[str, Any],
    guide_record: Mapping[str, Any],
    schema: Mapping[str, Any],
    schema_record: Mapping[str, Any],
    response: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    raw_output: bytes,
    parser: Mapping[str, Any],
    parsed: bytes | None,
    validation: Mapping[str, Any],
    usable: Mapping[str, Any],
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind stochastic generation to deterministic guide and downstream hashes."""

    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": "publication_coordinate_guided_live_development_smoke",
        "developmentOnly": True,
        "liveOpenAIOutput": True,
        "notAnnotation": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "liveGenerationDeterministic": False,
        "coordinateGuideConstructionDeterministic": True,
        "downstreamReplayDeterministic": True,
        "runID": RUN_ID,
        "developmentID": DEVELOPMENT_ID,
        "sourceUnitID": request["primarySourceUnitID"],
        "requestID": request["requestID"],
        "requestInputSha256": request["requestInputSha256"],
        "providerInputSha256": sha256_bytes(provider_input),
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "coordinateGuideVersion": guide["coordinateGuideVersion"],
        "coordinateGuideSha256": sha256_bytes(canonical_json(guide)),
        "coordinateGuideEntryCount": len(guide["entries"]),
        "coordinateGuideRecordSha256": sha256_bytes(canonical_json(guide_record)),
        "requestSpecializedSchemaVersion": REQUEST_SPECIALIZED_SCHEMA_VERSION,
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
        "modelAuthorableSchemaRecordHash": schema_record["recordSha256"],
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "providerAdapterVersion": PROVIDER_ADAPTER_VERSION,
        "provider": PROVIDER_NAME,
        "requestedModel": REQUESTED_MODEL,
        "returnedModel": response["returnedModel"],
        "reasoningEffort": REASONING_EFFORT,
        "toolConfiguration": "none",
        "store": STORE,
        "structuredOutput": {
            "enabled": True,
            "apiField": "text.format",
            "type": "json_schema",
            "strict": True,
            "requestSpecialized": True,
        },
        "apiResponseID": response["responseID"],
        "apiStatus": response["status"],
        "tokenUsage": response["usage"],
        "retryCount": response["retryCount"],
        "costUSD": None,
        "providerResponseSha256": sha256_bytes(canonical_json(raw_response)),
        "rawModelOutputSha256": sha256_bytes(raw_output),
        "parserResultSha256": sha256_bytes(canonical_json(parser)),
        "parsedCandidateSha256": sha256_bytes(parsed) if parsed else None,
        "validationResultsHash": validation.get("validationResultsHash"),
        "validationArtifactSha256": sha256_bytes(canonical_json(validation)),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"),
        "usableArtifactSha256": sha256_bytes(canonical_json(usable)),
        "comparisonSha256": sha256_bytes(canonical_json(comparison)),
        "parseStatus": parser.get("parseStatus"),
    }
    record["reproducibilityRecordHash"] = sha256_bytes(canonical_json(record))
    return record


def _persist_pre_live_artifacts(output_dir: Path) -> dict[str, Any]:
    """Build, audit, and preserve every deterministic pre-live B3 artifact."""

    paths = _artifact_paths(output_dir)
    request = build_m2b3_request()
    guide = build_evidence_coordinate_guide(request["sourceUnit"])
    guide_record = coordinate_guide_record(request["sourceUnit"], guide)
    provider_input = build_coordinate_guided_provider_input(request, guide)
    schema = derive_request_specialized_schema(request)
    schema_record = request_specialized_schema_record(request)
    schema_audit = audit_openai_structured_outputs_schema(schema)
    if not schema_audit["compatible"]:
        raise ValueError("M2-B3 request-specialized schema failed provider audit")
    if validate_model_authorable_payload(
        json.loads((M2B2_OUTPUT_DIR / "publication_m2b2_exact_structured_model_output.json").read_text()),
        schema,
    ):
        raise ValueError("known structured fixture no longer fits the B3 request schema")
    size_report = build_dev_size_report()
    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["coordinateGuide"], guide)
    _write_canonical(paths["coordinateGuideRecord"], guide_record)
    _write_canonical(paths["sizeReport"], size_report)
    _write_canonical(paths["modelSchema"], schema)
    _write_canonical(paths["modelSchemaRecord"], schema_record)
    return {
        "paths": paths,
        "request": request,
        "guide": guide,
        "guideRecord": guide_record,
        "providerInput": provider_input,
        "schema": schema,
        "schemaRecord": schema_record,
        "schemaAudit": schema_audit,
        "sizeReport": size_report,
    }


def run_coordinate_guided_live_smoke(
    api_key: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Make exactly one guarded M2-B3 call and replay downstream stages twice."""

    state = _persist_pre_live_artifacts(output_dir)
    paths = state["paths"]
    kwargs = {} if transport is None else {"transport": transport}
    try:
        raw_output, response, raw_response = call_openai_responses_detailed(
            api_key,
            state["providerInput"],
            model_authorable_schema=state["schema"],
            **kwargs,
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
        raise
    except OpenAIProviderResponseError as exc:
        metadata = dict(exc.response_record)
        metadata["providerRunFailureCode"] = exc.failure_code
        _write_canonical(paths["providerFailureResponse"], exc.response)
        _write_canonical(paths["providerFailureMetadata"], metadata)
        raise
    response["retryCount"] = 0
    request = bind_live_response_metadata(state["request"], response)
    if build_coordinate_guided_provider_input(request, state["guide"]) != state["providerInput"]:
        raise ValueError("provider input changed while binding response metadata")
    payload = json.loads(raw_output.decode("utf-8"))
    if validate_model_authorable_payload(payload, state["schema"]):
        raise ValueError("structured output violated supplied request schema")
    first = _downstream(raw_output, request)
    parsed_payload = first[0].get("parsedDocument", {})
    comparison = build_b2_b3_comparison(parsed_payload, first[2], first[3])
    record = _reproducibility_record(
        request, state["providerInput"], state["guide"], state["guideRecord"],
        state["schema"], state["schemaRecord"], response, raw_response, raw_output,
        first[0], first[1], first[2], first[3], comparison,
    )
    replay_one = _downstream(raw_output, request)
    replay_two = _downstream(raw_output, request)
    record_one = _reproducibility_record(
        request, state["providerInput"], state["guide"], state["guideRecord"],
        state["schema"], state["schemaRecord"], response, raw_response, raw_output,
        replay_one[0], replay_one[1], replay_one[2], replay_one[3], comparison,
    )
    record_two = _reproducibility_record(
        request, state["providerInput"], state["guide"], state["guideRecord"],
        state["schema"], state["schemaRecord"], response, raw_response, raw_output,
        replay_two[0], replay_two[1], replay_two[2], replay_two[3], comparison,
    )
    replay_values_one = (
        replay_one[1], canonical_json(replay_one[2]), canonical_json(replay_one[3]), canonical_json(record_one)
    )
    replay_values_two = (
        replay_two[1], canonical_json(replay_two[2]), canonical_json(replay_two[3]), canonical_json(record_two)
    )
    if replay_values_one != replay_values_two or canonical_json(record) != canonical_json(record_one):
        raise ValueError("M2-B3 downstream replay is not byte-identical")
    _write_canonical(paths["request"], request)
    _write_canonical(paths["providerResponse"], raw_response)
    _write_canonical(paths["providerMetadata"], response)
    _write_exact(paths["rawModelOutput"], raw_output)
    _write_canonical(paths["parserResult"], first[0])
    if first[1] is not None:
        _write_exact(paths["parsedCandidate"], first[1])
    _write_canonical(paths["validationResults"], first[2])
    _write_canonical(paths["usablePipelineOutput"], first[3])
    _write_canonical(paths["comparison"], comparison)
    _write_canonical(paths["reproducibility"], record)
    return {
        **state,
        "request": request,
        "providerResponse": response,
        "rawProviderResponse": raw_response,
        "rawModelOutput": raw_output,
        "parserResult": first[0],
        "validation": first[2],
        "usablePipelineOutput": first[3],
        "comparison": comparison,
        "reproducibility": record,
        "replayByteIdentical": True,
    }


def replay_preserved(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay preserved M2-B3 output twice without making a provider call."""

    paths = _artifact_paths(output_dir)
    request = json.loads(paths["request"].read_text())
    raw = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw, request)
    second = _downstream(raw, request)
    values_one = (first[1], canonical_json(first[2]), canonical_json(first[3]))
    values_two = (second[1], canonical_json(second[2]), canonical_json(second[3]))
    if values_one != values_two:
        raise ValueError("preserved M2-B3 downstream replay differs")
    return {
        "byteIdentical": True,
        "parsedCandidateSha256": sha256_bytes(values_one[0]) if values_one[0] else None,
        "validationResultsSha256": sha256_bytes(values_one[1]),
        "usablePipelineOutputSha256": sha256_bytes(values_one[2]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one M2-B3 call, pre-live preparation, or no-network replay."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.prepare_only:
            state = _persist_pre_live_artifacts(args.output_dir)
            result = {
                "coordinateGuideSha256": state["guideRecord"]["coordinateGuideSha256"],
                "coordinateGuideEntryCount": state["guideRecord"]["entryCount"],
                "providerInputSha256": sha256_bytes(state["providerInput"]),
                "promptSha256": state["request"]["prompt"]["sha256"],
                "schemaSha256": sha256_bytes(canonical_json(state["schema"])),
            }
        elif args.replay_only:
            result = replay_preserved(args.output_dir)
        else:
            live = run_coordinate_guided_live_smoke(
                load_openai_api_key(), output_dir=args.output_dir
            )
            result = {
                "responseID": live["providerResponse"]["responseID"],
                "parseStatus": live["parserResult"]["parseStatus"],
                "envelopeStatus": live["validation"]["envelopeStatus"],
                "usableCandidates": len(live["usablePipelineOutput"]["candidateNodes"])
                + len(live["usablePipelineOutput"]["candidateEdges"]),
                "rawOutputSha256": live["reproducibility"]["rawModelOutputSha256"],
            }
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-B3 coordinate-guided smoke failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
