"""Run the one-call M2-A live OpenAI development smoke for Publication DEV-04.

Inputs are the approved M1 development manifest, frozen authorities, unchanged prompt,
and ``OPENAI_API_KEY``. Outputs are development-only live artifacts under M2; they are
not annotation, gold data, or formal evaluation. Replaying an existing preserved output
with ``--replay-only`` performs no provider call.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
from src.extraction.llm.publications.openai_provider import (  # noqa: E402
    PROVIDER_ADAPTER_VERSION,
    PROVIDER_NAME,
    REASONING_EFFORT,
    REQUESTED_MODEL,
    RESPONSE_FORMAT,
    STORE,
    OpenAIProviderError,
    Transport,
    bind_live_response_metadata,
    build_provider_input,
    call_openai_responses,
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


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2"
SOURCE_UNIT_ID = "pub:36:sec:0026:unit:0001"
DEVELOPMENT_ID = "DEV-04"
AUTHORIZED_TARGETS = ["PUB-N-A-P16-FINDING"]
RUN_ID = "publication-live-development-smoke/0.1.0"


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with exactly one final LF."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact provider input or model output bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    """Return the fixed, M2-only artifact path inventory."""

    return {
        "request": output_dir / "publication_m2a_live_request.json",
        "providerInput": output_dir / "publication_m2a_exact_provider_input.txt",
        "providerResponse": output_dir / "publication_m2a_provider_api_response.json",
        "rawModelOutput": output_dir / "publication_m2a_exact_raw_model_output.json",
        "parserResult": output_dir / "publication_m2a_parser_result.json",
        "parsedCandidate": output_dir / "publication_m2a_parsed_candidate.json",
        "validationResults": output_dir / "publication_m2a_validation_results.json",
        "usablePipelineOutput": output_dir / "publication_m2a_usable_pipeline_output.json",
        "reproducibility": output_dir / "publication_m2a_reproducibility_record.json",
    }


def _downstream(
    raw_output: bytes, request: Mapping[str, Any]
) -> tuple[dict[str, Any], bytes | None, dict[str, Any], dict[str, Any]]:
    """Run the unchanged strict parser, V1-V12 validator, and usable materializer."""

    parser_result = parse_recorded_response(raw_output, request)
    parsed_bytes = (
        canonical_parsed_envelope(parser_result)
        if parser_result.get("parseStatus") == "parsed"
        else None
    )
    validation = validate_candidate_envelope(parser_result, request)
    envelope = parser_result.get("parsedEnvelope", {})
    usable = materialize_usable_pipeline_output(envelope, validation)
    return parser_result, parsed_bytes, validation, usable


def _reproducibility_record(
    request: Mapping[str, Any],
    provider_input: bytes,
    response_record: Mapping[str, Any],
    raw_output: bytes,
    parser_result: Mapping[str, Any],
    parsed_bytes: bytes | None,
    validation: Mapping[str, Any],
    usable: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the live-call binding and downstream deterministic hash record."""

    authorities = request["authorities"]
    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": "publication_live_development_smoke",
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
        "validatorVersion": VALIDATOR_VERSION,
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION,
        "providerAdapterVersion": PROVIDER_ADAPTER_VERSION,
        "provider": PROVIDER_NAME,
        "requestedModel": REQUESTED_MODEL,
        "returnedModel": response_record["returnedModel"],
        "reasoningEffort": REASONING_EFFORT,
        "toolConfiguration": "none",
        "store": STORE,
        "structuredOutput": {
            "mode": RESPONSE_FORMAT,
            "jsonSchemaUsed": False,
            "reason": "The frozen schema contains pipeline-owned metadata and conditionals not safely exposable as a strict provider schema; the unchanged prompt requests strict textual JSON and the unchanged parser remains authoritative.",
        },
        "apiResponseID": response_record["responseID"],
        "apiStatus": response_record["status"],
        "tokenUsage": response_record["usage"],
        "retryCount": response_record["retryCount"],
        "costUSD": None,
        "rawModelOutputSha256": sha256_bytes(raw_output),
        "parsedCandidateSha256": sha256_bytes(parsed_bytes) if parsed_bytes is not None else None,
        "validationResultsHash": validation.get("validationResultsHash"),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"),
        "parseStatus": parser_result.get("parseStatus"),
    }
    record["reproducibilityRecordHash"] = sha256_bytes(canonical_json(record))
    return record


def run_live_smoke(
    api_key: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Make exactly one provider call, preserve it, and traverse the M1 pipeline."""

    base_request = build_development_request(
        SOURCE_UNIT_ID, AUTHORIZED_TARGETS, run_id=RUN_ID
    )
    if base_request["eligibleOperationalTargetIDs"] != AUTHORIZED_TARGETS:
        raise ValueError("DEV-04 request is not bounded to the authorized Finding target")
    provider_input = build_provider_input(base_request)
    call_kwargs = {} if transport is None else {"transport": transport}
    raw_output, response_record = call_openai_responses(
        api_key, provider_input, **call_kwargs
    )
    request = bind_live_response_metadata(base_request, response_record)
    if build_provider_input(request) != provider_input:
        raise ValueError("provider input changed while binding response metadata")
    parser_result, parsed_bytes, validation, usable = _downstream(raw_output, request)
    replay_one = _downstream(raw_output, request)
    replay_two = _downstream(raw_output, request)
    replay_hashes_one = (
        sha256_bytes(canonical_json(replay_one[0])),
        sha256_bytes(replay_one[1]) if replay_one[1] is not None else None,
        sha256_bytes(canonical_json(replay_one[2])),
        sha256_bytes(canonical_json(replay_one[3])),
    )
    replay_hashes_two = (
        sha256_bytes(canonical_json(replay_two[0])),
        sha256_bytes(replay_two[1]) if replay_two[1] is not None else None,
        sha256_bytes(canonical_json(replay_two[2])),
        sha256_bytes(canonical_json(replay_two[3])),
    )
    if replay_hashes_one != replay_hashes_two:
        raise ValueError("downstream replay is not byte-identical")

    reproducibility = _reproducibility_record(
        request,
        provider_input,
        response_record,
        raw_output,
        parser_result,
        parsed_bytes,
        validation,
        usable,
    )
    reproducibility["replayArtifactSha256"] = {
        "parserResult": replay_hashes_one[0],
        "parsedCandidate": replay_hashes_one[1],
        "validationResults": replay_hashes_one[2],
        "usablePipelineOutput": replay_hashes_one[3],
    }
    reproducibility.pop("reproducibilityRecordHash")
    reproducibility["reproducibilityRecordHash"] = sha256_bytes(
        canonical_json(reproducibility)
    )

    paths = _artifact_paths(output_dir)
    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["providerResponse"], response_record)
    _write_exact(paths["rawModelOutput"], raw_output)
    _write_canonical(paths["parserResult"], parser_result)
    if parsed_bytes is not None:
        _write_exact(paths["parsedCandidate"], parsed_bytes)
    _write_canonical(paths["validationResults"], validation)
    _write_canonical(paths["usablePipelineOutput"], usable)
    _write_canonical(paths["reproducibility"], reproducibility)
    return {
        "request": request,
        "providerResponse": response_record,
        "rawModelOutput": raw_output,
        "parserResult": parser_result,
        "validation": validation,
        "usablePipelineOutput": usable,
        "reproducibility": reproducibility,
        "artifactPaths": {key: str(value) for key, value in paths.items()},
    }


def replay_preserved(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay preserved raw output twice without any provider call."""

    paths = _artifact_paths(output_dir)
    request = json.loads(paths["request"].read_text(encoding="utf-8"))
    raw_output = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw_output, request)
    second = _downstream(raw_output, request)
    first_bytes = [canonical_json(first[0]), first[1], canonical_json(first[2]), canonical_json(first[3])]
    second_bytes = [canonical_json(second[0]), second[1], canonical_json(second[2]), canonical_json(second[3])]
    if first_bytes != second_bytes:
        raise ValueError("preserved downstream replay is not byte-identical")
    return {
        "byteIdentical": True,
        "parserResultSha256": sha256_bytes(first_bytes[0]),
        "parsedCandidateSha256": sha256_bytes(first_bytes[1]) if first_bytes[1] is not None else None,
        "validationResultsSha256": sha256_bytes(first_bytes[2]),
        "usablePipelineOutputSha256": sha256_bytes(first_bytes[3]),
    }


def _status_counts(validation: Mapping[str, Any]) -> dict[str, int]:
    """Count candidate and non-candidate validation statuses for CLI reporting."""

    counts: Counter[str] = Counter()
    for result in validation.get("recordResults", []):
        status = result.get("candidateValidationStatus", result.get("recordValidationStatus"))
        if status:
            counts[str(status)] += 1
    return dict(sorted(counts.items()))


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the M2-A live/replay command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replay-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one live smoke or a no-network preserved replay."""

    args = build_argument_parser().parse_args(argv)
    try:
        if args.replay_only:
            print(json.dumps(replay_preserved(args.output_dir), sort_keys=True))
            return 0
        api_key = load_openai_api_key()
        result = run_live_smoke(api_key, output_dir=args.output_dir)
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-A live smoke failed: {exc}", file=sys.stderr)
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
