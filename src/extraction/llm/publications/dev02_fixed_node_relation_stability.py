"""Prepare the no-call DEV-02 fixed-node relation stability diagnostic.

This module is deliberately isolated from the production extractor.  It freezes a
single relation-only provider body, duplicates its exact bytes into prospective R1
and R2 roots, and reuses the existing endpoint/evidence binders and V1--V12.
"""

from __future__ import annotations

from copy import deepcopy
import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema

from src.extraction.llm.publications.model_authorable_schema import (
    ModelAuthorableSchemaError,
    audit_openai_structured_outputs_schema,
)
from src.extraction.llm.publications.openai_provider import (
    REASONING_EFFORT,
    REQUESTED_MODEL,
    STORE,
    build_provider_input,
    build_responses_api_request,
)
from src.extraction.llm.publications.prospective_endpoint_binding_schema import (
    derive_prospective_endpoint_binding_schema,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    load_c0_bindings, model_authorable_relation_target_ids,
)
from src.extraction.llm.publications.request_builder import build_development_request


DIAGNOSTIC_VERSION = "dev02-fixed-node-relation-stability-0.1.0"
REGISTRY_PATH = PROJECT_ROOT / "data/curation/papers/m2/diagnostics/dev02_fixed_node_relation_stability/fixed_node_registry.json"
EXPECTED_REGISTRY_SHA256 = "3cc2e1e0e386ac656754496f4b418cf5c221d901abcf74ca5ffdd3adfb3e778a"
PROMPT_PATH = PROJECT_ROOT / "src/extraction/llm/publications/prompts/dev02_fixed_node_relation_stability_v0.1.0.txt"
OUTPUT_ROOT = REGISTRY_PATH.parent
RUN_IDS = ("R1", "R2")
DIAGNOSTIC_MAX_OUTPUT_TOKENS = 32768


class FixedNodeDiagnosticError(ValueError):
    """Report a fail-closed diagnostic authority or topology error."""


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write a canonical JSON artifact with exactly one trailing line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact diagnostic transport bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def load_fixed_node_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the researcher-frozen registry only when its pinned hash matches."""

    raw = path.read_bytes()
    actual = sha256_bytes(raw)
    if actual != EXPECTED_REGISTRY_SHA256:
        raise FixedNodeDiagnosticError(
            f"fixed-node registry SHA-256 mismatch: expected {EXPECTED_REGISTRY_SHA256}, got {actual}"
        )
    registry = load_json_object(path)
    nodes = registry.get("nodes")
    if registry.get("developmentID") != "DEV-02" or registry.get("nodeCount") != 46:
        raise FixedNodeDiagnosticError("fixed-node registry DEV-02/node-count authority mismatch")
    if not isinstance(nodes, list) or len(nodes) != 46:
        raise FixedNodeDiagnosticError("fixed-node registry must contain exactly 46 nodes")
    identifiers = [node.get("diagnosticNodeID") for node in nodes if isinstance(node, Mapping)]
    if len(identifiers) != 46 or len(set(identifiers)) != 46 or any(not isinstance(value, str) or not value for value in identifiers):
        raise FixedNodeDiagnosticError("fixed-node registry IDs must be unique non-empty strings")
    return registry


def _fixed_endpoint(node: Mapping[str, Any], source_artifact_id: str) -> dict[str, Any]:
    """Map one registry node to the existing accepted-local endpoint authority."""

    identifier = str(node["diagnosticNodeID"])
    return {
        "candidateID": identifier,
        "artifactID": source_artifact_id,
        "diagnosticArtifactID": f"diagnostic:dev02-fixed-node-relation-stability:{identifier}",
        "className": node["className"],
        "canonicalLabel": node["canonicalLabel"],
        "operationalTargetID": node["operationalTargetID"],
        "ontologyClassID": node["ontologyClassID"],
        "diagnosticNodeGroundingEvidenceTexts": node["evidenceTexts"],
        "registryProvenance": {
            "sourceRuns": node["sourceRuns"],
            "sourceCandidates": node["sourceCandidates"],
            "status": node["status"],
            "purpose": node["purpose"],
        },
    }


def _endpoint_schema(reference_type: str, identifiers: list[str]) -> dict[str, Any]:
    """Constrain one endpoint side to a single trusted reference route."""

    if not identifiers:
        raise FixedNodeDiagnosticError("attempted to create an endpoint schema with no compatible endpoints")
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "referenceType": {"type": "string", "const": reference_type},
            "referenceID": {"type": "string", "enum": identifiers},
        },
        "required": ["referenceType", "referenceID"],
    }


def _side_schema(endpoints: Sequence[Mapping[str, Any]], classes: set[str], paper_id: str) -> dict[str, Any]:
    """Return the exact diagnostic endpoint alternatives compatible with a signature side."""

    alternatives: list[dict[str, Any]] = []
    if "Paper" in classes:
        alternatives.append(_endpoint_schema("deterministic_node", [paper_id]))
    accepted = sorted(str(row["candidateID"]) for row in endpoints if row["className"] in classes)
    if accepted:
        alternatives.append(_endpoint_schema("accepted_local_candidate", accepted))
    if not alternatives:
        raise FixedNodeDiagnosticError("relation signature has no compatible fixed endpoints")
    return alternatives[0] if len(alternatives) == 1 else {"anyOf": alternatives}


def derive_relation_only_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Specialize current relation branches to fixed compatible endpoint IDs only."""

    schema = deepcopy(derive_prospective_endpoint_binding_schema(request))
    schema["properties"]["candidateNodes"] = {
        "type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0,
    }
    relation_ids = list(request["eligibleOperationalTargetIDs"])
    # Restrict the remaining model-authored side channels to relation work too.
    # Deferred-resolution is not part of the fixed-endpoint diagnostic.
    schema["properties"]["deferredRecords"] = {
        "type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0,
    }
    abstention = schema["$defs"]["abstention"]
    abstention["properties"]["operationalTargetID"]["anyOf"][0]["enum"] = relation_ids
    abstention["properties"]["competingOperationalTargetIDs"]["items"]["enum"] = relation_ids
    abstention["properties"]["relatedCandidateIDs"]["items"] = {"type": "string", "pattern": "^edge-[0-9]{4}$"}
    paper_id = str(request["sourceArtifactID"])
    endpoints = request["acceptedLocalCandidateEndpoints"]
    branches = schema["properties"]["candidateEdges"]["items"]
    branches = branches.get("anyOf", [branches])
    active: list[dict[str, Any]] = []
    for branch in branches:
        relation_id = branch["properties"]["operationalRelationID"]["const"]
        target = next(row for row in request["targetDefinitions"] if row["operational_id"] == relation_id)
        signatures = target["operational_signatures"]
        valid_signatures: list[tuple[set[str], set[str]]] = []
        for signature in signatures:
            domain = set(signature["domain"]["classes"])
            range_ = set(signature["range"]["classes"])
            has_source = "Paper" in domain or any(row["className"] in domain for row in endpoints)
            has_target = "Paper" in range_ or any(row["className"] in range_ for row in endpoints)
            if has_source and has_target:
                valid_signatures.append((domain, range_))
        for domain, range_ in valid_signatures:
            narrowed = deepcopy(branch)
            narrowed["properties"]["source"] = _side_schema(endpoints, domain, paper_id)
            narrowed["properties"]["target"] = _side_schema(endpoints, range_, paper_id)
            active.append(narrowed)
    if not active:
        raise FixedNodeDiagnosticError("no relation branches remain after fixed endpoint domain/range pruning")
    schema["properties"]["candidateEdges"] = {"type": "array", "items": active[0] if len(active) == 1 else {"anyOf": active}}
    # The generic endpoint definition is no longer reachable after all relation
    # branches receive fixed endpoint schemas; retaining it would advertise the
    # forbidden candidate_node route to the model.
    schema["$defs"].pop("edgeEndpoint", None)
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(f"fixed-node diagnostic schema incompatible: {audit['findings']}")
    return schema


def _active_relation_rows(
    target_definitions: Sequence[Mapping[str, Any]], endpoints: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Retain only frozen relation rows with one compatible fixed endpoint pair."""

    active: list[dict[str, Any]] = []
    for row in target_definitions:
        signatures = row.get("operational_signatures", [])
        compatible = any(
            ("Paper" in signature["domain"]["classes"] or any(endpoint["className"] in signature["domain"]["classes"] for endpoint in endpoints))
            and ("Paper" in signature["range"]["classes"] or any(endpoint["className"] in signature["range"]["classes"] for endpoint in endpoints))
            for signature in signatures
        )
        if compatible:
            active.append(dict(row))
    return active


def _assert_relation_universe(request: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    """Fail closed unless every model-facing relation surface has identical rows."""

    expected = set(str(row["operational_id"]) for row in request["targetDefinitions"])
    surfaces = {
        "eligibleOperationalTargetIDs": set(request["eligibleOperationalTargetIDs"]),
        "applicabilityPolicyBinding": set(request["applicabilityPolicyBinding"]["relationUniverseOperationalTargetIDs"]),
        "candidateEdgeSchema": set(_active_relation_ids(schema)),
        "abstentionOperationalTargetID": set(schema["$defs"]["abstention"]["properties"]["operationalTargetID"]["anyOf"][0]["enum"]),
        "abstentionCompetingOperationalTargetIDs": set(schema["$defs"]["abstention"]["properties"]["competingOperationalTargetIDs"]["items"]["enum"]),
    }
    if len(expected) != 21 or len(request["targetDefinitions"]) != 21:
        raise FixedNodeDiagnosticError("fixed endpoint pruning must retain exactly 21 relation rows")
    if request["applicabilityPolicyBinding"]["relationUniverseCount"] != 21:
        raise FixedNodeDiagnosticError("relation universe count must be exactly 21")
    mismatches = {name: sorted(values) for name, values in surfaces.items() if values != expected}
    if mismatches:
        raise FixedNodeDiagnosticError(f"model-facing relation universe drifted: {mismatches}")
    return sorted(expected)


def build_diagnostic_request() -> dict[str, Any]:
    """Build the fixed-endpoint relation-only request without any provider call."""

    registry = load_fixed_node_registry()
    relation_ids = model_authorable_relation_target_ids()
    binding = next(row for row in load_c0_bindings() if row["developmentID"] == "DEV-02")
    request = build_development_request(
        str(binding["sourceUnitID"]), relation_ids, run_id=f"{DIAGNOSTIC_VERSION}/provider-body",
        prompt_path=PROMPT_PATH,
    )
    bound = deepcopy(request)
    bound["purpose"] = "development_only_dev02_fixed_node_relation_stability"
    bound["prompt"]["version"] = "dev02-fixed-node-relation-stability-0.1.0"
    bound["developmentID"] = "DEV-02"
    bound["diagnosticAuthority"] = {
        "registryPath": str(REGISTRY_PATH.relative_to(PROJECT_ROOT)),
        "registrySha256": EXPECTED_REGISTRY_SHA256,
        "developmentOnly": True,
        "notEvaluationGold": True,
        "notProductionTruth": True,
        "noProductionGraphNodes": True,
    }
    bound["deterministicEndpoints"] = [{
        "nodeID": bound["sourceArtifactID"], "artifactID": bound["sourceArtifactID"],
        "className": "Paper", "diagnosticArtifactID": "diagnostic:dev02-fixed-node-relation-stability:paper",
    }]
    bound["acceptedLocalCandidateEndpoints"] = [_fixed_endpoint(node, bound["sourceArtifactID"]) for node in registry["nodes"]]
    active_definitions = _active_relation_rows(bound["targetDefinitions"], bound["acceptedLocalCandidateEndpoints"])
    active_ids = [str(row["operational_id"]) for row in active_definitions]
    bound["eligibleOperationalTargetIDs"] = active_ids
    bound["targetDefinitions"] = active_definitions
    bound["applicabilityPolicyBinding"] = {
        "relationUniverseOperationalTargetIDs": active_ids,
        "relationUniverseCount": len(active_ids),
        "endpointCount": 46,
        "endpointReferenceTypes": ["accepted_local_candidate", "deterministic_node"],
        "candidateNodesRequiredEmpty": True,
    }
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def _active_relation_ids(schema: Mapping[str, Any]) -> list[str]:
    """Return stable operational rows exposed after domain/range pruning."""

    items = schema["properties"]["candidateEdges"]["items"]
    branches = items.get("anyOf", [items])
    return sorted({branch["properties"]["operationalRelationID"]["const"] for branch in branches})


def prepare() -> dict[str, Any]:
    """Persist byte-identical prospective R1/R2 no-call dispatch artifacts."""

    request = build_diagnostic_request()
    schema = derive_relation_only_schema(request)
    active_rows = _assert_relation_universe(request, schema)
    provider_input = build_provider_input(request)
    body = build_responses_api_request(provider_input, model_authorable_schema=schema, max_output_tokens=DIAGNOSTIC_MAX_OUTPUT_TOKENS)
    body_bytes = canonical_json(body)
    record: dict[str, Any] = {
        "artifactRole": "development_only_dev02_fixed_node_relation_stability_preflight",
        "diagnosticVersion": DIAGNOSTIC_VERSION,
        "providerCalls": 0,
        "executionModeIntended": "responses_synchronous_structured_output; not dispatched",
        "fixedRegistrySha256": EXPECTED_REGISTRY_SHA256,
        "providerInputSha256": sha256_bytes(provider_input),
        "specializedSchemaSha256": sha256_bytes(canonical_json(schema)),
        "completeRequestBodySha256": sha256_bytes(body_bytes),
        "model": body["model"], "reasoningEffort": body["reasoning"]["effort"],
        "maxOutputTokens": body["max_output_tokens"], "store": body["store"],
        "activeRelationOperationalRows": active_rows,
        "activeRelationOperationalRowCount": len(active_rows),
        "fixedEndpointCount": len(request["acceptedLocalCandidateEndpoints"]),
        "requestByteIdentityAssertion": True,
        "relationUniverseSurfacesIdentical": True,
        "candidateNodesRequiredEmpty": True,
        "permittedEndpointReferenceTypes": ["accepted_local_candidate", "deterministic_node"],
    }
    record["preflightSha256"] = sha256_bytes(canonical_json(record))
    protocol = {
        "artifactRole": "development_only_dev02_fixed_node_relation_stability_analysis_protocol",
        "diagnosticVersion": DIAGNOSTIC_VERSION, "preObserved": True,
        "primaryOutcome": {
            "measure": "set Jaccard R1 vs R2 after deterministic duplicate collapse",
            "edgeIdentityTuple": [
                "operationalRelationID", "source.referenceType", "source.referenceID",
                "target.referenceType", "target.referenceID",
            ],
            "excludes": ["evidenceSpanIDs", "evidence wording"],
        },
        "secondaryOutcomes": ["edge counts", "shared / R1-only / R2-only", "relation-type distribution", "same endpoints / different predicate", "same predicate / different endpoint", "present-vs-absent relation instability", "evidence disagreement", "abstentions", "validator findings", "usable-edge counts", "token usage and cost"],
        "referenceComparison": "Previously observed byte-identical joint A7↔A8 extraction had semantic edge Jaccard approximately 0.36.",
        "noPostHocAcceptanceThreshold": True,
        "sourceSupportReviewRequiredForRunOnlyAssertions": True,
    }
    protocol["protocolSha256"] = sha256_bytes(canonical_json(protocol))
    for run_id in RUN_IDS:
        root = OUTPUT_ROOT / run_id
        _write_canonical(root / "dev02_fixed_node_relation_stability_request.json", request)
        _write_canonical(root / "dev02_fixed_node_relation_stability_specialized_schema.json", schema)
        _write_exact(root / "dev02_fixed_node_relation_stability_provider_input.txt", provider_input)
        _write_exact(root / "dev02_fixed_node_relation_stability_complete_request_body.json", body_bytes)
        _write_canonical(root / "dev02_fixed_node_relation_stability_preflight.json", record)
    _write_canonical(OUTPUT_ROOT / "dev02_fixed_node_relation_stability_analysis_protocol.json", protocol)
    if (OUTPUT_ROOT / "R1" / "dev02_fixed_node_relation_stability_complete_request_body.json").read_bytes() != (OUTPUT_ROOT / "R2" / "dev02_fixed_node_relation_stability_complete_request_body.json").read_bytes():
        raise FixedNodeDiagnosticError("R1/R2 provider request bodies are not byte-identical")
    return record


def main(argv: Sequence[str] | None = None) -> int:
    """Provide the sole no-provider-call preparation entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="write prospective R1/R2 no-call artifacts")
    args = parser.parse_args(argv)
    if not args.prepare:
        parser.error("only --prepare is supported; this harness never dispatches a provider call")
    print(canonical_json(prepare()).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
