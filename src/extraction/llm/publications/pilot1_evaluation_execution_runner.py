"""Execute only the frozen Pilot 1 11-request evaluation subset.

The runner reconstructs every request through the corrected request builders and
fails closed unless it exactly matches the corrected production manifest.  Provider
execution is available only through ``--execute-live``; the default path is an
offline authority and identity preflight.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, Union

from src.extraction.llm.publications import corrected_production_preflight as corrected
from src.extraction.llm.publications.openai_provider import (
    build_provider_input,
    call_openai_responses_detailed,
    load_openai_api_key,
)
from src.extraction.llm.publications.pilot1_evaluation_execution_subset import (
    IDENTITY_FIELDS,
    MANIFEST_PATH,
    OUTPUT_DIRECTORY,
    OUTPUT_NAME,
)
from src.extraction.llm.publications.production_runner import (
    MAX_OUTPUT_TOKENS,
    _prepared_request,
    _terminal_request,
    execute_with_provider_fixture,
)
from src.extraction.llm.publications.publication_artifacts import write_durable_canonical
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes
from src.extraction.llm.publications.step5_freeze_materialization import _inputs


RUNNER_VERSION = "publication-pilot1-evaluation-execution-runner/0.1.0"
DEFAULT_LIVE_ROOT = PROJECT_ROOT / "var/publication_pilot1_evaluation_execution"
SUBSET_PATH = OUTPUT_DIRECTORY / OUTPUT_NAME
EXECUTION_BINDING_NAME = "publication_pilot1_evaluation_execution_binding_v0.1.0.json"
REQUIRED_SUBSET_COUNT = 11


class Pilot1EvaluationExecutionError(ValueError):
    """Report frozen-scope, request-identity, or resume-state drift."""


ProviderCall = Callable[[Mapping[str, Any], int], Union[bytes, Mapping[str, Any]]]


def _load(path: Path) -> dict[str, Any]:
    """Load one JSON-object artifact."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Pilot1EvaluationExecutionError(f"EXPECTED_JSON_OBJECT:{path}")
    return value


def _self_hash(payload: Mapping[str, Any], field: str) -> str:
    """Return the canonical hash after omitting a self-hash field."""

    value = dict(payload)
    value.pop(field, None)
    return sha256_bytes(canonical_json(value))


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    """Durably write a new canonical artifact and reject divergent replacement."""

    data = canonical_json(dict(payload)) + b"\n"
    if path.exists() and path.read_bytes() != data:
        raise Pilot1EvaluationExecutionError(f"EXECUTION_ARTIFACT_CONFLICT:{path}")
    write_durable_canonical(path, payload)


def load_frozen_execution_scope() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and verify the execution subset and its immutable parent manifest."""

    subset, manifest = _load(SUBSET_PATH), _load(MANIFEST_PATH)
    if subset.get("artifactSha256") != _self_hash(subset, "artifactSha256"):
        raise Pilot1EvaluationExecutionError("EXECUTION_SUBSET_HASH_DRIFT")
    if manifest.get("manifestSha256") != _self_hash(manifest, "manifestSha256"):
        raise Pilot1EvaluationExecutionError("CORRECTED_MANIFEST_HASH_DRIFT")
    if subset.get("providerModelCalls") != 0 or manifest.get("providerModelCalls") != 0:
        raise Pilot1EvaluationExecutionError("FROZEN_AUTHORITY_PROVIDER_CALLS_DRIFT")
    parent = subset.get("correctedProductionManifest", {})
    if parent.get("manifestSha256") != manifest.get("manifestSha256") or parent.get("populationCount") != manifest.get("populationCount"):
        raise Pilot1EvaluationExecutionError("EXECUTION_SUBSET_PARENT_MANIFEST_DRIFT")
    records = subset.get("requests", [])
    if not isinstance(records, list) or subset.get("subsetRequestCount") != len(records) or len(records) != REQUIRED_SUBSET_COUNT:
        raise Pilot1EvaluationExecutionError("EXECUTION_SUBSET_COUNT_DRIFT")
    if len({row.get("requestID") for row in records if isinstance(row, Mapping)}) != len(records):
        raise Pilot1EvaluationExecutionError("EXECUTION_SUBSET_DUPLICATE_REQUEST_ID")
    manifest_by_unit = {str(row["primarySourceUnitID"]): row for row in manifest.get("requests", [])}
    for record in records:
        if not isinstance(record, Mapping):
            raise Pilot1EvaluationExecutionError("EXECUTION_SUBSET_RECORD_NOT_OBJECT")
        parent_record = manifest_by_unit.get(str(record.get("primarySourceUnitID")))
        if parent_record is None or any(record.get(field) != parent_record.get(field) for field in IDENTITY_FIELDS):
            raise Pilot1EvaluationExecutionError(f"EXECUTION_SUBSET_MANIFEST_IDENTITY_DRIFT:{record.get('primarySourceUnitID')}")
    return subset, manifest


def prepare_verified_request(record: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild one request through corrected mechanics and verify every frozen identity."""

    subset, manifest = load_frozen_execution_scope()
    subset_record = next((row for row in subset["requests"] if row["requestID"] == record.get("requestID")), None)
    manifest_record = next((row for row in manifest["requests"] if row["requestID"] == record.get("requestID")), None)
    if subset_record is None or manifest_record is None or dict(record) != subset_record:
        raise Pilot1EvaluationExecutionError("EXECUTION_RECORD_NOT_FROZEN_SUBSET_MEMBER")

    inventory, _ = _inputs()
    routing, _routing_authority, n6_envelopes = corrected._load_authorities()
    source_unit_id = str(record["primarySourceUnitID"])
    unit, route = inventory.get(source_unit_id), routing.get(source_unit_id)
    if unit is None or route is None:
        raise Pilot1EvaluationExecutionError(f"EXECUTION_SOURCE_OR_ROUTING_MISSING:{source_unit_id}")
    if source_unit_id in n6_envelopes:
        prepared = corrected._prepared_n6_request(unit, route, inventory, n6_envelopes[source_unit_id])
    else:
        prepared = _prepared_request(source_unit_id, inventory, routing)
    prepared = dict(prepared)
    prepared["providerInput"] = build_provider_input(prepared["request"])
    actual = {
        "requestID": prepared["request"]["requestID"],
        "requestInputSha256": prepared["request"]["requestInputSha256"],
        "providerRequestBodySha256": sha256_bytes(canonical_json(prepared["body"])),
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(prepared["schema"])),
        "productionTargetIDs": prepared["request"]["eligibleOperationalTargetIDs"],
        "contextSourceUnitIDs": prepared["request"]["contextSourceUnitIDs"],
    }
    if any(actual[field] != record.get(field) or actual[field] != manifest_record.get(field) for field in IDENTITY_FIELDS):
        raise Pilot1EvaluationExecutionError(f"RECONSTRUCTED_REQUEST_IDENTITY_DRIFT:{source_unit_id}")
    return prepared


def materialize_execution_binding(root: Path = DEFAULT_LIVE_ROOT) -> dict[str, Any]:
    """Create the immutable, no-call execution binding in its separate namespace."""

    subset, manifest = load_frozen_execution_scope()
    binding = {
        "artifactType": "publication_pilot1_evaluation_execution_binding",
        "artifactVersion": "0.1.0",
        "runnerVersion": RUNNER_VERSION,
        "status": "ready_for_explicit_live_execution",
        "providerModelCalls": 0,
        "executionSubset": {
            "path": str(SUBSET_PATH.relative_to(PROJECT_ROOT)),
            "artifactSha256": subset["artifactSha256"],
            "requestCount": subset["subsetRequestCount"],
        },
        "correctedProductionManifest": {
            "path": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
            "manifestSha256": manifest["manifestSha256"],
            "populationCount": manifest["populationCount"],
        },
        "requests": list(subset["requests"]),
        "resumePolicy": "skip only durable terminal attempt selection; any nonterminal request directory fails closed without redispatch",
        "canonicalProcessingAuthorities": [
            "publication-semantic-pipeline/1.0.0",
            "publication-evidence-failure-isolation/1.0.0",
            "publication-production-acceptance-policy/0.1.0",
        ],
    }
    binding["artifactSha256"] = sha256_bytes(canonical_json(binding))
    _write_immutable(root / EXECUTION_BINDING_NAME, binding)
    return binding


def execute_subset_with_provider_fixture(root: Path, provider_call: ProviderCall) -> dict[str, Any]:
    """Execute the exact subset with an injected provider transport or offline fixture.

    A terminal attempt-selection is safely resumable. Any other existing request
    directory is deliberately ambiguous and blocks re-dispatch.
    """

    binding = materialize_execution_binding(root)
    completed: list[str] = []
    for record in binding["requests"]:
        request_root = root / "requests" / record["requestID"]
        if _terminal_request(request_root):
            completed.append(record["requestID"])
            continue
        if request_root.exists():
            raise Pilot1EvaluationExecutionError(f"AMBIGUOUS_INTERRUPTED_REQUEST_STATE:{request_root}")
        prepared = prepare_verified_request(record)
        result = execute_with_provider_fixture(prepared, provider_call, artifact_root=request_root)
        if not _terminal_request(request_root) or "attemptSelection" not in result:
            raise Pilot1EvaluationExecutionError(f"EXECUTION_DID_NOT_REACH_TERMINAL_STATE:{record['requestID']}")
        completed.append(record["requestID"])
    return {
        "executionBindingSha256": binding["artifactSha256"],
        "executionSubsetSha256": binding["executionSubset"]["artifactSha256"],
        "completedRequestCount": len(completed),
        "subsetRequestCount": len(binding["requests"]),
    }


def execute_live_subset(root: Path = DEFAULT_LIVE_ROOT) -> dict[str, Any]:
    """Dispatch only the frozen subset through the existing detailed provider path."""

    binding = materialize_execution_binding(root)
    api_key = load_openai_api_key()

    def detailed(prepared: Mapping[str, Any]) -> ProviderCall:
        """Bind one verified reconstructed body to the existing provider adapter."""

        def call(body: Mapping[str, Any], budget: int) -> Mapping[str, Any]:
            if body != prepared["body"] or budget != MAX_OUTPUT_TOKENS:
                raise Pilot1EvaluationExecutionError("LIVE_PROVIDER_DISPATCH_IDENTITY_DRIFT")
            raw, metadata, response = call_openai_responses_detailed(
                api_key,
                prepared["providerInput"],
                model_authorable_schema=prepared["schema"],
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
            return {"rawOutput": raw, "providerMetadata": metadata, "providerResponse": response}

        return call

    # Keep the public live path separate from fixtures while retaining exact
    # per-record verification immediately before every provider dispatch.
    completed: list[str] = []
    for record in binding["requests"]:
        request_root = root / "requests" / record["requestID"]
        if _terminal_request(request_root):
            completed.append(record["requestID"])
            continue
        if request_root.exists():
            raise Pilot1EvaluationExecutionError(f"AMBIGUOUS_INTERRUPTED_REQUEST_STATE:{request_root}")
        prepared = prepare_verified_request(record)
        execute_with_provider_fixture(prepared, detailed(prepared), artifact_root=request_root)
        if not _terminal_request(request_root):
            raise Pilot1EvaluationExecutionError(f"EXECUTION_DID_NOT_REACH_TERMINAL_STATE:{record['requestID']}")
        completed.append(record["requestID"])
    return {
        "executionBindingSha256": binding["artifactSha256"],
        "executionSubsetSha256": binding["executionSubset"]["artifactSha256"],
        "completedRequestCount": len(completed),
        "subsetRequestCount": len(binding["requests"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Preflight by default; require an explicit flag for the 11 live requests."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_LIVE_ROOT)
    parser.add_argument("--execute-live", action="store_true")
    args = parser.parse_args(argv)
    if args.execute_live:
        print(execute_live_subset(args.root))
    else:
        binding = materialize_execution_binding(args.root)
        print({"executionBindingSha256": binding["artifactSha256"], "liveExecution": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
