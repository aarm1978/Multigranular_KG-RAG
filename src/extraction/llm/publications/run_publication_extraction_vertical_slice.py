"""Execute the deterministic offline Publication M1 vertical slice on DEV-04."""

from __future__ import annotations

import argparse
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


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m1"
DEFAULT_RAW_RESPONSE = DEFAULT_OUTPUT_DIR / "publication_m1_recorded_raw_response.json"
DEFAULT_PROVENANCE = DEFAULT_OUTPUT_DIR / "publication_m1_recorded_raw_response_provenance.json"
SOURCE_UNIT_ID = "pub:36:sec:0026:unit:0001"
AUTHORIZED_TARGETS = ["PUB-N-A-P16-FINDING"]
RUN_ID = "publication-m1-dev04-recorded-v0.1.0"


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact only when its bytes changed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_file(value)
    if not path.exists() or path.read_bytes() != payload:
        path.write_bytes(payload)


def _hash_file(path: Path) -> str:
    """Hash one required M1 authority or runtime input file."""

    return sha256_bytes(path.read_bytes())


def run_vertical_slice(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    raw_response_path: Path = DEFAULT_RAW_RESPONSE,
    provenance_path: Path = DEFAULT_PROVENANCE,
) -> dict[str, Any]:
    """Run request, strict parse, V1-V12 validation, usable output, and provenance."""

    provenance = __import__("json").loads(provenance_path.read_text(encoding="utf-8"))
    required_flags = {
        "developmentOnly": True,
        "manuallyConstructedForDeterministicPipelineExecution": True,
        "notAnnotation": True,
        "notEvaluation": True,
        "notGold": True,
        "notLlmExperimentalResult": True,
        "providerCallPerformed": False,
    }
    if any(provenance.get(key) != value for key, value in required_flags.items()):
        raise ValueError("recorded-response provenance is not development-only provider-neutral metadata")

    request = build_development_request(
        SOURCE_UNIT_ID,
        AUTHORIZED_TARGETS,
        run_id=RUN_ID,
    )
    raw_response = raw_response_path.read_bytes()
    parser_result = parse_recorded_response(raw_response, request)
    if parser_result.get("parseStatus") != "parsed" or parser_result.get("parsedEnvelope") is None:
        raise ValueError("recorded response did not produce a parsed candidate envelope")
    parsed_envelope = parser_result["parsedEnvelope"]
    validation = validate_candidate_envelope(parser_result, request)
    usable = materialize_usable_pipeline_output(parsed_envelope, validation)
    if validation["envelopeStatus"] != "valid" or not usable["candidateNodes"]:
        raise ValueError("real development vertical slice did not produce usable output")

    prompt_artifact = {
        "artifactRole": "publication_development_prompt",
        "status": "development_not_frozen",
        "promptVersion": request["prompt"]["version"],
        "promptPath": request["prompt"]["path"],
        "promptSha256": request["prompt"]["sha256"],
        "promptText": request["prompt"]["text"],
    }
    request_path = output_dir / "publication_m1_request.json"
    prompt_path = output_dir / "publication_m1_prompt_artifact.json"
    parsed_path = output_dir / "publication_m1_parsed_candidate.json"
    validation_path = output_dir / "publication_m1_validation_results.json"
    usable_path = output_dir / "publication_m1_usable_pipeline_output.json"
    _write_canonical(request_path, request)
    _write_canonical(prompt_path, prompt_artifact)
    parsed_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_path.write_bytes(canonical_parsed_envelope(parser_result))
    _write_canonical(validation_path, validation)
    _write_canonical(usable_path, usable)

    artifact_hashes = {
        "canonicalRequest": _hash_file(request_path),
        "parsedCandidate": _hash_file(parsed_path),
        "promptArtifact": _hash_file(prompt_path),
        "recordedRawResponse": _hash_file(raw_response_path),
        "recordedRawResponseProvenance": _hash_file(provenance_path),
        "usablePipelineOutput": _hash_file(usable_path),
        "validationResults": _hash_file(validation_path),
    }
    reproducibility: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": "publication_m1_offline_vertical_slice",
        "developmentOnly": True,
        "providerCallPerformed": False,
        "runID": RUN_ID,
        "sourceUnitID": SOURCE_UNIT_ID,
        "sourceUnitTextHash": request["sourceUnit"]["textHash"],
        "canonicalDocumentSha256": request["sourceUnit"]["canonicalTextSha256"],
        "operationalTargetIDs": AUTHORIZED_TARGETS,
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "requestInputSha256": request["requestInputSha256"],
        "rawResponseSha256": parser_result["rawResponseSha256"],
        "parsedCandidateSha256": sha256_bytes(canonical_json(parsed_envelope)),
        "validationResultsHash": validation["validationResultsHash"],
        "usablePipelineOutputHash": usable["usablePipelineOutputHash"],
        "authorities": {
            "candidateSchema": request["authorities"]["candidateSchema"],
            "developmentManifest": request["developmentManifest"],
            "developmentInventory": request["developmentInventory"],
            "evidenceValidationContract": request["authorities"]["evidenceValidationContract"],
            "evaluationMatchingContract": request["authorities"]["evaluationMatchingContract"],
            "ontology": request["authorities"]["ontology"],
            "sourceUnitContract": request["authorities"]["sourceUnitContract"],
            "targetInventory": request["authorities"]["targetInventory"],
        },
        "artifactSha256": artifact_hashes,
    }
    reproducibility["reproducibilityRecordHash"] = sha256_bytes(canonical_json(reproducibility))
    reproducibility_path = output_dir / "publication_m1_reproducibility_record.json"
    _write_canonical(reproducibility_path, reproducibility)
    return {
        "request": request,
        "parsedEnvelope": parsed_envelope,
        "validation": validation,
        "usablePipelineOutput": usable,
        "reproducibility": reproducibility,
        "reproducibilityPath": str(reproducibility_path),
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the deterministic offline M1 orchestration CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--raw-response", type=Path, default=DEFAULT_RAW_RESPONSE)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute M1 and print its deterministic acceptance summary."""

    args = build_argument_parser().parse_args(argv)
    try:
        result = run_vertical_slice(
            output_dir=args.output_dir,
            raw_response_path=args.raw_response,
            provenance_path=args.provenance,
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"publication M1 vertical slice failed: {exc}", file=sys.stderr)
        return 1
    print(f"source unit: {SOURCE_UNIT_ID}")
    print(f"request SHA-256: {result['request']['requestInputSha256']}")
    print(f"envelope status: {result['validation']['envelopeStatus']}")
    print(f"usable candidates: {len(result['usablePipelineOutput']['candidateNodes']) + len(result['usablePipelineOutput']['candidateEdges'])}")
    print(f"usable output hash: {result['usablePipelineOutput']['usablePipelineOutputHash']}")
    print(f"reproducibility record hash: {result['reproducibility']['reproducibilityRecordHash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
