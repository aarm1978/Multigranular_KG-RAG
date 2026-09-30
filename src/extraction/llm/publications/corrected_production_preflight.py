"""Freeze corrected Publication production requests without provider execution.

This prospective builder leaves the historical C1 runner, manifest, outputs, and
v0.1.1 Step 5 envelopes untouched.  It binds only the accepted corrected routing
authority and Step 5 v0.1.2 N=6 envelopes to existing schema013 request mechanics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.openai_provider import build_provider_input, build_responses_api_request
from src.extraction.llm.publications.production_runner import (
    CONTEXT_BUDGET,
    MAX_OUTPUT_TOKENS,
    REASONING_EFFORT,
    REQUESTED_MODEL,
    RUNNER_VERSION as HISTORICAL_RUNNER_VERSION,
    STORE,
    _prepared_request,
)
from src.extraction.llm.publications.publication_v015_routing_migration import (
    AUTHORITY_OUTPUT_NAME as ROUTING_AUTHORITY_NAME,
    OUTPUT_DIRECTORY as ROUTING_OUTPUT_DIRECTORY,
)
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, sha256_bytes
from src.extraction.llm.publications.step5_freeze_materialization import _inputs
from src.extraction.llm.publications.step5_v012_routing_correction import (
    ARTIFACT_VERSION as STEP5_V012_VERSION,
    ENVELOPES_OUTPUT_NAME,
    FREEZE_ROOT,
    _context_units,
    _request_for as _step5_request_for,
)


PREFLIGHT_VERSION = "publication-corrected-production-preflight/0.1.0"
MANIFEST_VERSION = "0.1.0"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data/curation/papers/m2/publication_v015_corrected_production"
PREFLIGHT_OUTPUT_NAME = "publication_v015_corrected_production_preflight_v0.1.0.json"
MANIFEST_OUTPUT_NAME = "publication_v015_corrected_production_run_manifest_v0.1.0.json"
ROUTING_PATH = ROUTING_OUTPUT_DIRECTORY / "publication_v015_corrected_unit_routing_v0.1.0.jsonl"
ROUTING_AUTHORITY_PATH = ROUTING_OUTPUT_DIRECTORY / ROUTING_AUTHORITY_NAME
N6_ENVELOPES_PATH = FREEZE_ROOT / ENVELOPES_OUTPUT_NAME
PRODUCTION_RECORD_TYPES = frozenset({"journal_article", "book_chapter"})


class CorrectedProductionPreflightError(ValueError):
    """Report a corrected-production authority or request binding failure."""


def _load(path: Path) -> dict[str, Any]:
    """Load one JSON-object authority artifact."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CorrectedProductionPreflightError(f"expected JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one canonical JSONL artifact."""

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise CorrectedProductionPreflightError(f"invalid JSONL artifact: {path}")
    return rows


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a self-hashed canonical artifact."""

    result = dict(payload)
    result["artifactSha256"] = sha256_bytes(canonical_json(result))
    return result


def _write_immutable(path: Path, payload: Mapping[str, Any]) -> None:
    """Write one new canonical artifact without accepting divergent replacement."""

    data = canonical_json(dict(payload)) + b"\n"
    if path.exists() and path.read_bytes() != data:
        raise CorrectedProductionPreflightError(f"CORRECTED_PRODUCTION_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _load_authorities() -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    """Load corrected routing and v0.1.2 N=6 envelope authorities fail-closed."""

    authority = _load(ROUTING_AUTHORITY_PATH)
    routing_rows = _jsonl(ROUTING_PATH)
    canonical_routing_stream = b"".join(canonical_json(row) for row in routing_rows)
    if authority.get("routing", {}).get("sha256") != sha256_bytes(canonical_routing_stream):
        raise CorrectedProductionPreflightError("CORRECTED_ROUTING_HASH_DRIFT")
    if authority.get("routing", {}).get("recordCount") != len(routing_rows):
        raise CorrectedProductionPreflightError("CORRECTED_ROUTING_RECORD_COUNT_DRIFT")
    envelopes = _load(N6_ENVELOPES_PATH)
    if envelopes.get("artifactVersion") != STEP5_V012_VERSION or envelopes.get("providerModelCalls") != 0:
        raise CorrectedProductionPreflightError("STEP5_V012_ENVELOPE_AUTHORITY_DRIFT")
    envelope_rows = {str(row["primarySourceUnitID"]): row for row in envelopes.get("envelopes", [])}
    if len(envelope_rows) != 6:
        raise CorrectedProductionPreflightError("STEP5_V012_ENVELOPE_COUNT_DRIFT")
    return {str(row["sourceUnitID"]): row for row in routing_rows}, authority, envelope_rows


def _production_ids(inventory: Mapping[str, Mapping[str, Any]], routing: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Derive—not assume—the complete corrected production population."""

    ids = [
        source_unit_id
        for source_unit_id, unit in inventory.items()
        if unit.get("eligibility") == "eligible"
        and unit.get("requestEligible") is True
        and unit.get("recordType") in PRODUCTION_RECORD_TYPES
        and source_unit_id in routing
        and (routing[source_unit_id]["eligibleNodeOperationalTargetIDs"] or routing[source_unit_id]["eligibleRelationOperationalTargetIDs"])
    ]
    if not ids:
        raise CorrectedProductionPreflightError("CORRECTED_PRODUCTION_POPULATION_EMPTY")
    return sorted(ids)


def _add_request_identity(request: Mapping[str, Any]) -> dict[str, Any]:
    """Add the existing production runner's deterministic request identifiers."""

    result = dict(request)
    result["requestID"] = f"publication-c1-request-{sha256_bytes(canonical_json(result))[:20]}"
    result["offlineResponseMetadata"] = {
        "provider": "OpenAI", "modelName": REQUESTED_MODEL, "modelVersion": None,
        "generationParameters": {"maxOutputTokens": MAX_OUTPUT_TOKENS}, "tokenUsage": {},
        "costUSD": None, "retryCount": 0, "responseCreatedAt": None,
    }
    result["requestInputSha256"] = sha256_bytes(canonical_json(result))
    return result


def _prepared_n6_request(
    unit: Mapping[str, Any], route: Mapping[str, Any], inventory: Mapping[str, Mapping[str, Any]], envelope: Mapping[str, Any]
) -> dict[str, Any]:
    """Build one corrected N=6 request and require exact v0.1.2 envelope reproduction."""

    request, preliminary = _step5_request_for(unit, route, _context_units(unit, inventory))
    request = _add_request_identity(request)
    schema = preliminary["schema"]
    body = build_responses_api_request(build_provider_input(request), model_authorable_schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
    body_bytes = canonical_json(body)
    if len(body_bytes) > CONTEXT_BUDGET:
        raise CorrectedProductionPreflightError(f"CORRECTED_N6_CONTEXT_BUDGET_EXCEEDED:{unit['sourceUnitID']}")
    checks = {
        "routedExtractAndEvaluateTargetIDs": request["eligibleOperationalTargetIDs"],
        "contextSourceUnitIDs": request["contextSourceUnitIDs"],
        "providerRequestBodySha256": sha256_bytes(body_bytes),
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
        "requestEnvelopeSha256": sha256_bytes(canonical_json({key: request[key] for key in ("authorityBundleID", "runID", "primarySourceUnitID", "contextSourceUnitIDs", "requestScope", "includedCompleteSection", "eligibleOperationalTargetIDs", "prompt")})),
    }
    if any(envelope.get(key) != value for key, value in checks.items()):
        raise CorrectedProductionPreflightError(f"CORRECTED_N6_ENVELOPE_REPRODUCTION_FAILED:{unit['sourceUnitID']}")
    return {"request": request, "schema": schema, "body": body, "n6EnvelopeReproduced": True}


def derive_preflight() -> dict[str, Any]:
    """Build every corrected production request offline and validate all N=6 envelopes."""

    inventory, _ = _inputs()
    routing, routing_authority, n6_envelopes = _load_authorities()
    population = _production_ids(inventory, routing)
    if not set(n6_envelopes).issubset(population):
        raise CorrectedProductionPreflightError("CORRECTED_N6_OUTSIDE_PRODUCTION_POPULATION")
    records: list[dict[str, Any]] = []
    n6_reproduction: list[dict[str, Any]] = []
    for source_unit_id in population:
        unit, route = inventory[source_unit_id], routing[source_unit_id]
        if source_unit_id in n6_envelopes:
            prepared = _prepared_n6_request(unit, route, inventory, n6_envelopes[source_unit_id])
            n6_reproduction.append({"primarySourceUnitID": source_unit_id, "matched": True, "envelopeArtifactSha256": _load(N6_ENVELOPES_PATH)["artifactSha256"]})
        else:
            prepared = _prepared_request(source_unit_id, inventory, routing)
        request, schema, body = prepared["request"], prepared["schema"], prepared["body"]
        if len(canonical_json(body)) > CONTEXT_BUDGET:
            raise CorrectedProductionPreflightError(f"CORRECTED_PRODUCTION_CONTEXT_BUDGET_EXCEEDED:{source_unit_id}")
        records.append({
            "primarySourceUnitID": source_unit_id, "runID": request["runID"], "requestID": request["requestID"],
            "requestInputSha256": request["requestInputSha256"], "contextSourceUnitIDs": list(request["contextSourceUnitIDs"]),
            "productionTargetIDs": list(request["eligibleOperationalTargetIDs"]),
            "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
            "providerRequestBodySha256": sha256_bytes(canonical_json(body)),
        })
    if len({row["requestID"] for row in records}) != len(records):
        raise CorrectedProductionPreflightError("CORRECTED_PRODUCTION_DUPLICATE_REQUEST_ID")
    if len(n6_reproduction) != 6 or not all(row["matched"] for row in n6_reproduction):
        raise CorrectedProductionPreflightError("CORRECTED_N6_REPRODUCTION_INCOMPLETE")
    return _artifact({
        "artifactType": "publication_v015_corrected_production_preflight", "artifactVersion": MANIFEST_VERSION,
        "preflightVersion": PREFLIGHT_VERSION, "status": "all_requests_built_no_provider_execution", "providerModelCalls": 0,
        "historicalC1Preserved": {"historicalRunnerVersion": HISTORICAL_RUNNER_VERSION, "historicalManifestModified": False, "historicalOutputsModified": False, "v011EnvelopesUsed": False},
        "correctedRoutingAuthority": {"path": str(ROUTING_AUTHORITY_PATH.relative_to(PROJECT_ROOT)), "sha256": routing_authority["artifactSha256"], "routingSha256": routing_authority["routing"]["sha256"], "routingVersion": routing_authority["routingVersion"]},
        "n6EnvelopeAuthority": {"path": str(N6_ENVELOPES_PATH.relative_to(PROJECT_ROOT)), "sha256": _load(N6_ENVELOPES_PATH)["artifactSha256"], "artifactVersion": STEP5_V012_VERSION},
        "productionPopulation": {"count": len(records), "derivation": "eligible + requestEligible + journal_article|book_chapter + corrected routing with at least one target"},
        "productionConfiguration": {"model": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT, "maxOutputTokens": MAX_OUTPUT_TOKENS, "store": STORE, "tools": "none", "web": False, "externalRetrieval": False, "authorityBundleID": "publication-semantic-v0.1.5-schema-v0.1.3"},
        "n6EnvelopeReproduction": n6_reproduction, "requests": records,
    })


def build_manifest(preflight: Mapping[str, Any]) -> dict[str, Any]:
    """Bind an immutable corrected production run manifest to an exact preflight."""

    if preflight.get("providerModelCalls") != 0 or not all(row.get("matched") for row in preflight.get("n6EnvelopeReproduction", [])):
        raise CorrectedProductionPreflightError("CORRECTED_MANIFEST_PREFLIGHT_GATE_FAILED")
    manifest = {
        "artifactType": "publication_v015_corrected_production_run_manifest", "manifestVersion": MANIFEST_VERSION,
        "runnerVersion": PREFLIGHT_VERSION, "providerModelCalls": 0, "c1Execution": False,
        "preflightArtifactSha256": preflight["artifactSha256"], "populationCount": preflight["productionPopulation"]["count"],
        "correctedRoutingAuthority": dict(preflight["correctedRoutingAuthority"]), "n6EnvelopeAuthority": dict(preflight["n6EnvelopeAuthority"]),
        "productionConfiguration": dict(preflight["productionConfiguration"]), "n6EnvelopeReproduction": list(preflight["n6EnvelopeReproduction"]),
        "requests": list(preflight["requests"]), "historicalC1Preserved": dict(preflight["historicalC1Preserved"]),
    }
    manifest["manifestSha256"] = sha256_bytes(canonical_json(manifest))
    return manifest


def materialize(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, Path]:
    """Materialize the corrected preflight and immutable manifest with no dispatch."""

    preflight = derive_preflight()
    manifest = build_manifest(preflight)
    outputs = {"preflight": output_directory / PREFLIGHT_OUTPUT_NAME, "manifest": output_directory / MANIFEST_OUTPUT_NAME}
    _write_immutable(outputs["preflight"], preflight)
    _write_immutable(outputs["manifest"], manifest)
    return outputs


def main(argv: Sequence[str] | None = None) -> int:
    """Build only corrected offline request artifacts."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    args = parser.parse_args(argv)
    for name, path in materialize(args.output_directory).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
