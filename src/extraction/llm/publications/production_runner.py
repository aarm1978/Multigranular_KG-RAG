"""Offline preflight and injectable execution seam for frozen Publication C1.

This module deliberately does not load credentials or call a provider.  It derives the
complete production request population from the frozen sampling universe and routing
authorities, and leaves dispatch to an explicitly supplied callable at Step 6B.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from src.extraction.llm.publications.openai_provider import (
    PROVIDER_NAME, REASONING_EFFORT, REQUESTED_MODEL, STORE, build_provider_input,
    build_responses_api_request,
)
from src.extraction.llm.publications.production_acceptance import (
    derive_accepted_semantic_projection, derive_unresolved_identity_sidecar,
    run_attempt_controller,
)
from src.extraction.llm.publications.prospective_evidence_binding_schema import derive_prospective_evidence_binding_schema
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, load_yaml_object, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import _downstream
from src.extraction.llm.publications.step5_freeze_materialization import _inputs, _request_for, _scored_target_ids


RUNNER_VERSION = "publication-production-runner/0.1.0"
MAX_OUTPUT_TOKENS = 32768
SAMPLING_PATH = PROJECT_ROOT / "data/curation/papers/m2/human_core_sampling_analysis/publication_human_core_sampling_analysis_v0.1.0.json"
HUMAN_CORE_PATH = PROJECT_ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json"
N6_ENVELOPES_PATH = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json"


class ProductionPreflightError(ValueError):
    """Raised when a frozen production authority cannot be reproduced exactly."""


def _load(path: Path) -> dict[str, Any]:
    """Load one required frozen JSON mapping."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProductionPreflightError(f"authority is not a JSON object: {path}")
    return value


def _context_units(unit: Mapping[str, Any], inventory: Mapping[str, Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Return the frozen complete-section eligible context in stable order."""

    return sorted(
        (candidate for candidate in inventory.values() if candidate["sectionID"] == unit["sectionID"]
         and candidate["sourceUnitID"] != unit["sourceUnitID"] and candidate.get("eligibility") == "eligible"),
        key=lambda candidate: str(candidate["sourceUnitID"]),
    )


def _prepared_request(unit_id: str, inventory: Mapping[str, Mapping[str, Any]], routing: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Build one authoritative routed extract-and-evaluate C1 request, offline."""

    unit, route = inventory.get(unit_id), routing.get(unit_id)
    if unit is None or route is None:
        raise ProductionPreflightError(f"missing frozen source/routing row: {unit_id}")
    try:
        request, prepared = _request_for(unit, route, _context_units(unit, inventory))
    except KeyError as exc:
        # The established freeze helper specializes a relation transport schema.
        # Build the equally governed node-only variant from its request template.
        if exc.args != ("edgeEndpoint",):
            raise
        template_unit = inventory["pub:276:sec:0019:unit:0001"]
        template_route = routing["pub:276:sec:0019:unit:0001"]
        request, _ = _request_for(template_unit, template_route, [])
        request = deepcopy(request)
        node_ids, relation_ids = _scored_target_ids()
        target_ids = sorted((set(route["eligibleNodeOperationalTargetIDs"]) & node_ids) |
                            (set(route["eligibleRelationOperationalTargetIDs"]) & relation_ids))
        profile = load_yaml_object(PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml")
        definitions = {str(row["operational_id"]): dict(row) for row in [*profile["node_targets"], *profile["relation_targets"]]}
        request.update({"sourcePublicationID": str(unit["paperID"]), "sourceArtifactID": unit["canonicalArtifactID"],
                        "primarySourceUnitID": unit["sourceUnitID"], "contextSourceUnitIDs": [], "contextUnits": [],
                        "sourceUnit": dict(unit), "eligibleOperationalTargetIDs": target_ids,
                        "targetDefinitions": [definitions[target_id] for target_id in target_ids],
                        "deterministicEndpoints": [{"nodeID": unit["canonicalArtifactID"], "className": "Paper", "artifactID": unit["canonicalArtifactID"]}],
                        "runID": f"publication-step5-c1-evaluation/0.1.1/{unit['sourceUnitID']}"})
        prepared = {}
    # The frozen helper intentionally omits downstream-only identities.  They are
    # not provider-input fields, so attaching them after its exact body construction
    # preserves every frozen N=6 body hash.
    request = deepcopy(request)
    request["offlineResponseMetadata"] = {
        "provider": PROVIDER_NAME, "modelName": REQUESTED_MODEL, "modelVersion": None,
        "generationParameters": {"maxOutputTokens": MAX_OUTPUT_TOKENS}, "tokenUsage": {},
        "costUSD": None, "retryCount": 0, "responseCreatedAt": None,
    }
    request["requestID"] = f"publication-c1-request-{sha256_bytes(canonical_json(request))[:20]}"
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    # Node-only routed units have no edgeEndpoint definition.  Their specialized
    # transport schema is the existing evidence-binding schema; edge binding below
    # remains a no-op because such a payload cannot contain an edge.
    if not any(str(value).startswith("PUB-R-") for value in request["eligibleOperationalTargetIDs"]):
        schema = derive_prospective_evidence_binding_schema(request)
        provider_input = build_provider_input(request)
        body = build_responses_api_request(provider_input, model_authorable_schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
        prepared = {"schema": schema, "body": body, "bodyBytes": canonical_json(body)}
    body = prepared["body"]
    if body.get("max_output_tokens") != MAX_OUTPUT_TOKENS:
        raise ProductionPreflightError("provider body did not receive explicit 32768 max_output_tokens")
    return {"request": request, "schema": prepared["schema"], "providerInput": build_provider_input(request), "body": body}


def _envelope_view(prepared: Mapping[str, Any]) -> dict[str, Any]:
    """Return the fields whose values are frozen by the N=6 C1 envelope authority."""

    request, body, schema = prepared["request"], prepared["body"], prepared["schema"]
    return {
        "primarySourceUnitID": request["primarySourceUnitID"],
        "contextSourceUnitIDs": request["contextSourceUnitIDs"],
        "routedExtractAndEvaluateTargetIDs": request["eligibleOperationalTargetIDs"],
        "maxOutputTokens": body["max_output_tokens"],
        "requestEnvelopeSha256": sha256_bytes(canonical_json({key: request[key] for key in (
            "authorityBundleID", "runID", "primarySourceUnitID", "contextSourceUnitIDs", "requestScope",
            "includedCompleteSection", "eligibleOperationalTargetIDs", "prompt")})),
        "providerRequestBodySha256": sha256_bytes(canonical_json(body)),
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)),
    }


def derive_production_preflight() -> dict[str, Any]:
    """Derive all authorized C1 requests and verify frozen N=5/N=6 memberships."""

    sampling, human_core, frozen_n6 = _load(SAMPLING_PATH), _load(HUMAN_CORE_PATH), _load(N6_ENVELOPES_PATH)
    universe = sampling.get("eligibleUniverse", {})
    ids = universe.get("sourceUnitIDs")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ProductionPreflightError("frozen eligible production population is missing or non-unique")
    inventory, routing = _inputs()
    node_ids, relation_ids = _scored_target_ids()
    if set(universe.get("routedScoredNodeOperationalTargetIDs", [])) != node_ids or set(universe.get("routedScoredRelationOperationalTargetIDs", [])) != relation_ids:
        raise ProductionPreflightError("sampling and frozen routed-target authority disagree")
    n5 = sorted(str(row["sourceUnitID"]) for row in human_core.get("selectedUnits", []))
    n6_rows = frozen_n6.get("envelopes", [])
    n6 = sorted(str(row["primarySourceUnitID"]) for row in n6_rows)
    population_ids = sorted(map(str, ids))
    if len(n5) != 5 or len(n6) != 6 or set(n5) & set(n6) or not (set(n5) | set(n6)) <= set(population_ids):
        raise ProductionPreflightError("frozen Human Core/N=6 membership is not a disjoint production subset")
    frozen_by_id = {str(row["primarySourceUnitID"]): row for row in n6_rows}
    reproduction: list[dict[str, Any]] = []
    for unit_id in n6:
        actual, expected = _envelope_view(_prepared_request(unit_id, inventory, routing)), frozen_by_id.get(unit_id)
        if expected is None:
            raise ProductionPreflightError(f"missing frozen N=6 envelope: {unit_id}")
        fields = tuple(actual)
        matched = all(actual[field] == expected.get(field) for field in fields)
        reproduction.append({"primarySourceUnitID": unit_id, "matched": matched, "fields": fields,
                             "publication46SameSectionContext": actual["contextSourceUnitIDs"] if unit_id == "pub:46:sec:0006:unit:0001" else None})
    if not all(row["matched"] for row in reproduction):
        raise ProductionPreflightError("one or more production requests drift from frozen Step 5 envelopes")
    if next(row for row in reproduction if row["primarySourceUnitID"] == "pub:46:sec:0006:unit:0001")["publication46SameSectionContext"] != ["pub:46:sec:0006:unit:0002"]:
        raise ProductionPreflightError("Publication 46 same-section context binding drifted")
    records = []
    for unit_id in population_ids:
        unit, route = inventory[unit_id], routing[unit_id]
        target_ids = sorted((set(route["eligibleNodeOperationalTargetIDs"]) & node_ids) |
                            (set(route["eligibleRelationOperationalTargetIDs"]) & relation_ids))
        request_id = f"publication-c1-request-{sha256_bytes(unit_id.encode('utf-8'))[:20]}"
        records.append({"primarySourceUnitID": unit_id, "requestID": request_id,
                        "outputID": f"publication-c1-output-{request_id.rsplit('-', 1)[-1]}",
                        "requestIdentityBasis": "SHA-256(exact primarySourceUnitID); exact request/body hashes materialize at no-call dispatch preflight",
                        "contextSourceUnitIDs": [str(row["sourceUnitID"]) for row in _context_units(unit, inventory)],
                        "routedExtractAndEvaluateTargetIDs": target_ids})
    return {
        "runnerVersion": RUNNER_VERSION, "providerModelCalls": 0, "c1Execution": False,
        "populationAuthority": {"samplingAnalysis": str(SAMPLING_PATH.relative_to(PROJECT_ROOT)), "count": len(records),
                                "basis": "frozen eligibleUniverse.sourceUnitIDs; frozen source inventory, unit routing, target-family extract_and_evaluate routing, and complete-section context authority"},
        "productionConfiguration": {"model": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT, "maxOutputTokens": MAX_OUTPUT_TOKENS,
                                    "store": STORE, "tools": "none", "web": False, "externalRetrieval": False},
        "humanCoreN5PrimarySourceUnitIDs": n5, "complementaryN6PrimarySourceUnitIDs": n6,
        "n6FrozenEnvelopeReproduction": reproduction, "requests": records,
        "artifactLayout": {"root": "data/curation/papers/m2/production_c1/<runID>/<requestID>",
                            "attempts": "attempt-01|attempt-02/{lifecycle,provider_request,provider_response,raw_output,parser,validation,usable_pipeline_output}.json",
                            "selected": "attempt_selection.json", "acceptedProjection": "accepted_semantic_projection.json",
                            "unresolvedIdentity": "unresolved_identity_sidecar.json", "terminal": "terminal_processing_failure.json"},
    }


ProviderCall = Callable[[Mapping[str, Any], int], bytes]


def execute_with_provider_fixture(prepared: Mapping[str, Any], provider_call: ProviderCall) -> dict[str, Any]:
    """Exercise the production path with an injected provider only (Step 6B seam).

    The callable receives the exact body and explicit 32768 budget.  This function is
    intentionally not a CLI and performs no credential lookup or network I/O itself.
    """

    request, schema, body = prepared["request"], prepared["schema"], prepared["body"]
    provider_input_hash = sha256_bytes(build_provider_input(request))
    def one_attempt(number: int) -> dict[str, Any]:
        raw = provider_call(deepcopy(body), MAX_OUTPUT_TOKENS)
        parser, _parsed, validation, usable = _downstream(raw, request, endpoint_binding=True, evidence_binding=True)
        return {"attemptNumber": number, "requestInputSha256": request["requestInputSha256"], "providerInputSha256": provider_input_hash,
                "authorityBundleID": request["authorityBundleID"], "requestedModel": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT,
                "maxOutputTokens": MAX_OUTPUT_TOKENS, "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(schema)), "provider": PROVIDER_NAME,
                "toolConfiguration": "none", "store": STORE, "parserResult": parser, "validation": validation, "usablePipelineOutput": usable,
                "rawOutputSha256": sha256_bytes(raw)}
    selection = run_attempt_controller(one_attempt)
    result: dict[str, Any] = {"attemptSelection": selection}
    if selection["selectedAttemptNumber"] is not None:
        result["acceptedSemanticProjection"] = derive_accepted_semantic_projection(selection, request)
        result["unresolvedIdentitySidecar"] = derive_unresolved_identity_sidecar(selection, request)
    return result
