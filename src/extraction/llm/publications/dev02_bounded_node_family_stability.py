"""Prepare the no-call DEV-02 bounded-node-family stability diagnostic.

This development-only harness freezes twelve prospective synchronous Responses
requests.  It deliberately has no dispatch path and does not alter production
extraction, historical artifacts, or the ontology.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
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
    build_responses_api_request,
)
from src.extraction.llm.publications.prospective_evidence_binding_schema import (
    derive_prospective_evidence_binding_schema,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_json_object,
    sha256_bytes,
    build_development_request,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    load_c0_bindings,
)


DIAGNOSTIC_VERSION = "dev02-bounded-node-family-stability-0.1.0"
OUTPUT_ROOT = PROJECT_ROOT / "data/curation/papers/m2/diagnostics/dev02_bounded_node_family_stability"
PROMPT_PATH = PROJECT_ROOT / "src/extraction/llm/publications/prompts/dev02_bounded_node_family_stability_v0.1.0.txt"
RUN_IDS = ("R1", "R2")
DIAGNOSTIC_MAX_OUTPUT_TOKENS = 32768

# These are the researcher-specified, mutually exclusive 40 direct-open-discovery
# targets.  Keep operational IDs as the authority; class names are checked from the
# current target inventory rather than independently recreated.
FAMILIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "F1": ("Study framing and intent", (
        "PUB-N-A-P05-BACKGROUND", "PUB-N-A-P06-THEME", "PUB-N-A-P07-RESEARCHPROBLEM",
        "PUB-N-A-P08-RESEARCHQUESTION", "PUB-N-A-P09-RESEARCHGOAL",
        "PUB-N-A-P10-RESEARCHSIGNIFICANCE", "PUB-N-A-P23-HYPOTHESIS",
    )),
    "F2": ("Conceptual and scholarly context", (
        "PUB-N-A-P11-DEFINITION", "PUB-N-A-P12-THEORETICALBASIS",
        "PUB-N-A-P18-RELATEDRESEARCH", "PUB-N-A-DOM05-CONCEPT",
    )),
    "F3": ("Methods, design, and computational entities", (
        "PUB-N-A-P13-METHOD", "PUB-N-A-P14-EXPERIMENT", "PUB-N-A-P15-EXAMPLES",
        "PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE", "PUB-N-A-DOM03A-PROCESSBASEDMODEL",
        "PUB-N-A-DOM03B-CONCEPTUALMODEL", "PUB-N-A-DOM03C-STATISTICALMODEL",
        "PUB-N-A-DOM03D-MLMODEL", "PUB-N-A-DOM13-ALGORITHM",
    )),
    "F4": ("Results, interpretation, and argument", (
        "PUB-N-A-P16-FINDING", "PUB-N-A-P17-DISCUSSION", "PUB-N-A-P19-LIMITATION",
        "PUB-N-A-P20-CONCLUSION", "PUB-N-A-P21-CONTRIBUTION", "PUB-N-A-P22-FUTUREWORK",
        "PUB-N-A-P24-CLAIM",
    )),
    "F5": ("Data and quantitative entities", (
        "PUB-N-A-P26-DATADESCRIPTION", "PUB-N-A-DOM11-EVALUATIONMETRIC",
        "PUB-N-A-DOM12-PARAMETER", "PUB-N-A-DOM04-VARIABLE",
        "PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE",
        "PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY",
    )),
    "F6": ("Spatial and hydrologic entities", (
        "PUB-N-A-DOM07A-WATERSHED", "PUB-N-A-DOM07B-RIVERREACH", "PUB-N-A-DOM07C-GAUGE",
        "PUB-N-A-DOM07D-WATERBODY", "PUB-N-A-DOM07E-AQUIFER", "PUB-N-A-DOM07F-VPU",
        "PUB-N-A-DOM08-NAMEDPLACE",
    )),
}

HISTORICAL_RUNS: dict[str, Path] = {
    "A4": PROJECT_ROOT / "data/curation/papers/m2/future_full_semantic_devset0/DEV-02/researcher_authorized_verification_001/DEV-02/publication_full_semantic_dev02_parsed_candidate.json",
    "A7": PROJECT_ROOT / "data/curation/papers/m2/future_full_semantic_devset0/DEV-02/researcher_authorized_retest_replacement_002/DEV-02/publication_full_semantic_dev02_parsed_candidate.json",
    "A8": PROJECT_ROOT / "data/curation/papers/m2/future_full_semantic_devset0/DEV-02/researcher_authorized_retest_replication_002/DEV-02/publication_full_semantic_dev02_parsed_candidate.json",
}
FIXED_REGISTRY_PATH = PROJECT_ROOT / "data/curation/papers/m2/diagnostics/dev02_fixed_node_relation_stability/fixed_node_registry.json"


class BoundedNodeFamilyDiagnosticError(ValueError):
    """Report a fail-closed diagnostic authority or specialization error."""


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with a single trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact transport bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _empty_array_schema() -> dict[str, Any]:
    """Return a strict schema that structurally permits only an empty array."""

    return {"type": "array", "items": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "maxItems": 0}


def _referenced_definitions(value: Any) -> set[str]:
    """Return local ``$defs`` names referenced anywhere in one schema value."""

    names: set[str] = set()
    if isinstance(value, Mapping):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            names.add(reference.removeprefix("#/$defs/"))
        for child in value.values():
            names.update(_referenced_definitions(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_referenced_definitions(child))
    return names


def _prune_unreachable_definitions(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Retain exactly the transitive definition closure reachable from schema root."""

    pruned = deepcopy(dict(schema))
    definitions = pruned.get("$defs", {})
    root = {key: value for key, value in pruned.items() if key != "$defs"}
    pending = sorted(_referenced_definitions(root))
    reachable: set[str] = set()
    while pending:
        name = pending.pop(0)
        if name in reachable:
            continue
        if name not in definitions:
            raise BoundedNodeFamilyDiagnosticError(f"schema root references missing definition: {name}")
        reachable.add(name)
        pending.extend(sorted(_referenced_definitions(definitions[name]) - reachable - set(pending)))
    pruned["$defs"] = {name: definitions[name] for name in sorted(reachable)}
    return pruned


def _ordered_json_object(fields: Sequence[tuple[str, Any]]) -> bytes:
    """Serialize a deterministic object while preserving explicitly supplied key order."""

    return b"{" + b",".join(
        canonical_json(key) + b":" + canonical_json(value) for key, value in fields
    ) + b"}"


def _longest_common_prefix_byte_count(values: Sequence[bytes]) -> int:
    """Return the exact shared leading-byte count for a non-empty sequence."""

    if not values:
        raise BoundedNodeFamilyDiagnosticError("cannot measure an empty provider-input collection")
    return next((index for index, column in enumerate(zip(*values)) if len(set(column)) != 1), min(len(value) for value in values))


def build_family_provider_input(request: Mapping[str, Any]) -> tuple[bytes, int, int]:
    """Serialize a source-first diagnostic-only provider input for fair cache measurement.

    Unlike the production serializer, this intentionally preserves a prescribed outer
    field order.  The complete trusted source-unit object itself remains canonical.
    """

    common_fields: list[tuple[str, Any]] = [
        ("purpose", request["purpose"]),
        ("sourcePublicationID", request["sourcePublicationID"]),
        ("sourceArtifactID", request["sourceArtifactID"]),
        ("primarySourceUnitID", request["primarySourceUnitID"]),
        ("contextSourceUnitIDs", list(request["contextSourceUnitIDs"])),
        ("requestScope", request["requestScope"]),
        ("includedCompleteSection", request["includedCompleteSection"]),
        ("extractionChannel", request["extractionChannel"]),
        ("deterministicEndpoints", list(request["deterministicEndpoints"])),
        ("acceptedLocalCandidateEndpoints", list(request["acceptedLocalCandidateEndpoints"])),
        ("deferredRecords", list(request["deferredRecords"])),
        ("sourceUnit", request["sourceUnit"]),
    ]
    family_fields: list[tuple[str, Any]] = [
        ("familyID", request["familyID"]),
        ("familyName", request["familyName"]),
        ("runID", request["runID"]),
        ("eligibleOperationalTargetIDs", list(request["eligibleOperationalTargetIDs"])),
        ("targetDefinitions", list(request["targetDefinitions"])),
    ]
    prompt_prefix = str(request["prompt"]["text"]).encode("utf-8") + b"\n\nBounded trusted development request JSON:\n"
    common_block = _ordered_json_object(common_fields)
    prefix = prompt_prefix + b'{"commonRequest":' + common_block + b',"familyRequest":'
    provider_input = prefix + _ordered_json_object(family_fields) + b"}"
    return provider_input, len(prefix), len(canonical_json(request["sourceUnit"]))


def _direct_targets() -> tuple[dict[str, Any], list[str], list[str]]:
    """Resolve the exact DEV-02 direct targets and excluded target IDs."""

    binding = next(row for row in load_c0_bindings() if row["developmentID"] == "DEV-02")
    all_ids = list(binding["eligibleNodeOperationalTargetIDs"])
    deterministic = list(binding["excludedDeterministicContextTargetIDs"])
    deferred = list(binding["excludedDeferredOnlyTargetIDs"])
    if len(all_ids) != 40 or len(deterministic) != 4 or len(deferred) != 2:
        raise BoundedNodeFamilyDiagnosticError("DEV-02 does not retain the required 40/4/2 target topology")
    return binding, all_ids, deterministic + deferred


def family_definition_authority() -> dict[str, Any]:
    """Build and mechanically validate the six-family target authority."""

    binding, direct_ids, excluded_ids = _direct_targets()
    flattened = [target for _, targets in FAMILIES.values() for target in targets]
    if len(flattened) != 40 or len(set(flattened)) != 40 or set(flattened) != set(direct_ids):
        raise BoundedNodeFamilyDiagnosticError("family partition is not an exact non-overlapping 40-target partition")
    if set(flattened) & set(excluded_ids):
        raise BoundedNodeFamilyDiagnosticError("deterministic-context or deferred target entered a family")
    probe = build_development_request(binding["sourceUnitID"], direct_ids, run_id=f"{DIAGNOSTIC_VERSION}/authority")
    rows = {str(row["operational_id"]): row for row in probe["targetDefinitions"]}
    families = []
    for identifier, (name, targets) in FAMILIES.items():
        families.append({"familyID": identifier, "familyName": name, "targets": [
            {"operationalTargetID": target, "className": rows[target]["operational_target"], "ontologyClassID": rows[target]["ontology_ids"][0]}
            for target in targets
        ]})
    authority: dict[str, Any] = {
        "artifactRole": "development_only_bounded_node_family_definition_authority",
        "diagnosticVersion": DIAGNOSTIC_VERSION,
        "developmentID": "DEV-02", "ontologyVersion": probe["authorities"]["ontology"]["version"],
        "directOpenDiscoveryTargetCount": 40,
        "excludedDeterministicContextTargetIDs": binding["excludedDeterministicContextTargetIDs"],
        "excludedDeferredResolutionTargetIDs": binding["excludedDeferredOnlyTargetIDs"],
        "families": families,
        "partitionAssertions": {"all40ExactlyOnce": True, "noFamilyOverlap": True, "excludedTargetsAbsent": True},
    }
    authority["authoritySha256"] = sha256_bytes(canonical_json(authority))
    return authority


def build_family_request(family_id: str) -> dict[str, Any]:
    """Build one family-only node-discovery request without provider dispatch."""

    if family_id not in FAMILIES:
        raise BoundedNodeFamilyDiagnosticError(f"unknown family: {family_id}")
    binding, _, _ = _direct_targets()
    name, target_ids = FAMILIES[family_id]
    request = build_development_request(binding["sourceUnitID"], list(target_ids), run_id=f"{DIAGNOSTIC_VERSION}/{family_id}/provider-body", prompt_path=PROMPT_PATH)
    bound = deepcopy(request)
    bound["purpose"] = "development_only_dev02_bounded_node_family_stability"
    bound["developmentID"] = "DEV-02"
    bound["familyID"] = family_id
    bound["familyName"] = name
    bound["prompt"]["version"] = "dev02-bounded-node-family-stability-0.1.0"
    bound["diagnosticAuthority"] = {"developmentOnly": True, "notEvaluationGold": True, "notProductionAuthority": True, "providerCalls": 0}
    bound["applicabilityPolicyBinding"] = {
        "familyOperationalTargetIDs": list(target_ids), "familyOperationalTargetIDCount": len(target_ids),
        "candidateEdgesRequiredEmpty": True, "deferredRecordsRequiredEmpty": True,
        "excludedMechanisms": ["deterministic_context", "deferred_resolution"],
    }
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def derive_family_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    """Specialize the current node-only transport to exactly one family."""

    eligible = list(request["eligibleOperationalTargetIDs"])
    schema = deepcopy(derive_prospective_evidence_binding_schema(request))
    branches = schema["properties"]["candidateNodes"]["items"].get("anyOf", [])
    exposed = {branch["properties"]["operationalTargetID"]["const"] for branch in branches}
    if exposed != set(eligible):
        raise BoundedNodeFamilyDiagnosticError("provider-facing node target set and schema node branches diverge")
    schema["properties"]["candidateEdges"] = _empty_array_schema()
    schema["properties"]["deferredRecords"] = _empty_array_schema()
    abstention = schema["$defs"]["abstention"]["properties"]
    abstention["scope"] = {"type": "string", "const": "operational_target"}
    abstention["operationalTargetID"] = {"anyOf": [{"type": "string", "enum": eligible}, {"type": "null"}]}
    abstention["competingOperationalTargetIDs"] = {"type": "array", "items": {"type": "string", "enum": eligible}}
    abstention["relatedCandidateIDs"] = {"type": "array", "items": {"type": "string", "pattern": "^node-[0-9]{4}$"}}
    schema = _prune_unreachable_definitions(schema)
    jsonschema.Draft202012Validator.check_schema(schema)
    audit = audit_openai_structured_outputs_schema(schema)
    if not audit["compatible"]:
        raise ModelAuthorableSchemaError(f"family diagnostic schema incompatible: {audit['findings']}")
    return schema


def _assert_family_surfaces(request: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Fail closed unless every exposed target surface is the same family universe."""

    expected = set(request["eligibleOperationalTargetIDs"])
    branches = schema["properties"]["candidateNodes"]["items"].get("anyOf", [])
    surfaces = {
        "targetDefinitions": {row["operational_id"] for row in request["targetDefinitions"]},
        "candidateNodeSchema": {branch["properties"]["operationalTargetID"]["const"] for branch in branches},
        "abstentionOperationalTargetID": set(schema["$defs"]["abstention"]["properties"]["operationalTargetID"]["anyOf"][0]["enum"]),
        "abstentionCompetingOperationalTargetIDs": set(schema["$defs"]["abstention"]["properties"]["competingOperationalTargetIDs"]["items"]["enum"]),
    }
    if any(values != expected for values in surfaces.values()):
        raise BoundedNodeFamilyDiagnosticError(f"family target universe drifted: {surfaces}")
    if schema["properties"]["candidateEdges"].get("maxItems") != 0 or schema["properties"]["deferredRecords"].get("maxItems") != 0:
        raise BoundedNodeFamilyDiagnosticError("relations or deferred records are not structurally empty")
    root = {key: value for key, value in schema.items() if key != "$defs"}
    reachable = _referenced_definitions(root)
    definitions = set(schema.get("$defs", {}))
    pending = list(reachable)
    while pending:
        name = pending.pop()
        if name not in schema["$defs"]:
            raise BoundedNodeFamilyDiagnosticError(f"reachable schema definition is absent: {name}")
        for child in _referenced_definitions(schema["$defs"][name]):
            if child not in reachable:
                reachable.add(child)
                pending.append(child)
    if definitions != reachable:
        raise BoundedNodeFamilyDiagnosticError("schema retains a $defs entry unreachable from its root")
    serialized = canonical_json(schema).decode("utf-8")
    relation_ids = re.findall(r"PUB-R-[A-Za-z0-9-]+", serialized)
    node_ids = set(re.findall(r"PUB-N-[A-Za-z0-9-]+", serialized))
    if relation_ids:
        raise BoundedNodeFamilyDiagnosticError("relation operational ID leaked into complete family schema")
    if not node_ids <= expected:
        raise BoundedNodeFamilyDiagnosticError("out-of-family node operational ID leaked into complete family schema")


def build_historical_diagnostic_pool() -> dict[str, Any]:
    """Preserve A4/A7/A8 node outputs without semantic merging or new judgments."""

    _, direct_ids, _ = _direct_targets()
    entries: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    for run, path in HISTORICAL_RUNS.items():
        raw = path.read_bytes()
        payload = load_json_object(path)
        spans = {span["evidenceSpanID"]: span for span in payload.get("evidenceSpans", [])}
        nodes = [node for node in payload.get("candidateNodes", []) if node.get("operationalTargetID") in direct_ids]
        provenance.append({"sourceRun": run, "parsedCandidatePath": str(path.relative_to(PROJECT_ROOT)), "parsedCandidateSha256": sha256_bytes(raw), "retainedNodeCount": len(nodes)})
        for node in nodes:
            entries.append({
                "sourceRun": run, "sourceCandidateID": node["candidateID"], "node": node,
                "evidenceSpans": [spans[span_id] for span_id in node.get("evidenceSpanIDs", []) if span_id in spans],
            })
    pool: dict[str, Any] = {
        "artifactRole": "development_only_historical_diagnostic_node_pool",
        "diagnosticVersion": DIAGNOSTIC_VERSION, "developmentID": "DEV-02",
        "status": "unreconciled_historical_pool", "diagnostic": True, "nonGold": True,
        "nonExhaustive": True, "notProductionAuthority": True,
        "semanticReconciliation": {"completeResearcherApprovedArtifactFound": False, "status": "pending", "note": "No complete A4/A7/A8 researcher-approved semantic reconciliation artifact was found; entries intentionally remain unmerged."},
        "sourceRunProvenance": provenance, "entries": entries,
    }
    pool["poolSha256"] = sha256_bytes(canonical_json(pool))
    return pool


def build_fixed_node_reference() -> dict[str, Any]:
    """Copy only the fixed registry's diagnostic, non-gold reference information."""

    raw = FIXED_REGISTRY_PATH.read_bytes()
    registry = load_json_object(FIXED_REGISTRY_PATH)
    if registry.get("nodeCount") != 46 or len(registry.get("nodes", [])) != 46:
        raise BoundedNodeFamilyDiagnosticError("secondary fixed-node reference must contain exactly 46 nodes")
    reference: dict[str, Any] = {
        "artifactRole": "development_only_secondary_high_confidence_fixed_node_reference",
        "diagnosticVersion": DIAGNOSTIC_VERSION, "diagnostic": True, "nonGold": True,
        "nonExhaustive": True, "notProductionAuthority": True, "nodeCount": 46,
        "sourceRegistryPath": str(FIXED_REGISTRY_PATH.relative_to(PROJECT_ROOT)),
        "sourceRegistrySha256": sha256_bytes(raw), "nodes": registry["nodes"],
        "purpose": "secondary high-confidence relation-eligible subset only; not the complete node benchmark",
    }
    reference["referenceSha256"] = sha256_bytes(canonical_json(reference))
    return reference


def analysis_protocol() -> dict[str, Any]:
    """Freeze outcomes, matching, diagnostics, guidance, and the stop rule."""

    protocol: dict[str, Any] = {
        "artifactRole": "development_only_dev02_bounded_node_family_stability_pre_observation_analysis_protocol",
        "diagnosticVersion": DIAGNOSTIC_VERSION, "preObserved": True, "noPostHocThresholdChanges": True,
        "primaryOutcome": {"measure": "semantic node proposition Jaccard", "replicateSets": {"N_R1": "union accepted/proposed F1-R1 through F6-R1 nodes", "N_R2": "union accepted/proposed F1-R2 through F6-R2 nodes"}, "historicalComparison": "A7/A8 semantic node Jaccard approximately 0.62"},
        "secondaryOutcome": {"measure": "strict deterministic node proposition Jaccard before reconciliation", "strictIdentity": ["className", "canonicalLabel after Unicode/case/surrounding-whitespace/mechanical-punctuation normalization only"], "prohibited": ["synonym expansion", "stemming", "ontology inference", "embedding similarity", "LLM judgment"]},
        "blindedReconciliation": {"unmatchedCandidates": "pooled, randomized, replicate provenance stripped", "packetFields": ["class", "canonicalLabel", "exact evidence", "relevant ontology definition/boundary"], "researcherMayAssign": ["semantic proposition-equivalence ID", "source-support disposition"], "unblindOnlyAfter": "reconciliation is frozen"},
        "coverageDiagnostics": {"labels": ["diagnostic", "non-gold", "non-exhaustive"], "historicalPoolRecovery": ["R1", "R2", "union where reconciliation exists"], "fixed46Recovery": ["R1", "R2", "union"], "novelCandidates": "same blinded source-support review; not automatically false positives", "errorDecomposition": ["discovery omission", "typing disagreement", "surface-label-only variation", "evidence-span variation", "unsupported candidate", "historical-pool incompleteness / genuinely new supported candidate"]},
        "decisionGuidance": {"stability": {">=0.80": "clear practical improvement over approximately 0.62", "0.70_to_<0.80": "partial improvement / researcher trade-off decision", "<0.70": "insufficient improvement to justify architecture expansion"}, "coverageSafeguardFixed46": {"eachCompleteReplicate": ">=80%", "union": ">=90%", "notGoldRecall": True}, "cost": {"formula": "C_six_family_node_discovery + C_one_fixed_node_relation_pass", "jointReferencePerRunUSD": 0.2845, "pricing": "actual provider usage and then-current documented pricing after runs", "<=1.25x": "practically comparable", ">1.25x_to_<=1.50x": "meaningful but potentially acceptable premium", ">1.50x": "substantial cost penalty"}},
        "stopRule": "After this one DEV-02 diagnostic is completed and interpreted, researcher must choose bounded-node discovery then deterministic consolidation then fixed-node relations, or retain joint extraction and document stochastic variability. No further extraction-method experiment opens automatically.",
    }
    protocol["protocolSha256"] = sha256_bytes(canonical_json(protocol))
    return protocol


def prepare() -> dict[str, Any]:
    """Materialize all no-call prospective artifacts and freeze their hashes."""

    authority = family_definition_authority()
    historical = build_historical_diagnostic_pool()
    fixed = build_fixed_node_reference()
    protocol = analysis_protocol()
    _write_canonical(OUTPUT_ROOT / "family_definition_authority.json", authority)
    _write_canonical(OUTPUT_ROOT / "historical_diagnostic_node_pool.json", historical)
    _write_canonical(OUTPUT_ROOT / "secondary_fixed_node_reference.json", fixed)
    _write_canonical(OUTPUT_ROOT / "pre_observation_analysis_protocol.json", protocol)
    _write_canonical(OUTPUT_ROOT / "later_lifecycle_materialization_locations.json", {
        "artifactRole": "development_only_later_lifecycle_materialization_locations",
        "diagnosticVersion": DIAGNOSTIC_VERSION, "providerCalls": 0,
        "note": "Locations are reserved only; this preparation creates no provider outputs or lifecycle claims.",
        "perFamilyReplicate": {
            "providerResponse": "{family}/{replicate}/later_provider_api_response.json",
            "rawStructuredOutput": "{family}/{replicate}/later_exact_structured_model_output.json",
            "parserResult": "{family}/{replicate}/later_parser_result.json",
            "validationResults": "{family}/{replicate}/later_validation_results.json",
            "usablePipelineOutput": "{family}/{replicate}/later_usable_pipeline_output.json",
            "attemptRecord": "{family}/{replicate}/later_attempt_record.json",
        },
        "postRunAnalysis": ["strict_match_projection.json", "blinded_reconciliation_packet.json", "frozen_reconciliation.json", "unblinded_diagnostic_report.json"],
    })
    records: list[dict[str, Any]] = []
    common_prefix_lengths: set[int] = set()
    source_unit_lengths: set[int] = set()
    common_prefix_bytes: bytes | None = None
    provider_inputs: list[bytes] = []
    for family_id in FAMILIES:
        request = build_family_request(family_id)
        schema = derive_family_schema(request)
        _assert_family_surfaces(request, schema)
        provider_input, common_prefix_length, source_unit_length = build_family_provider_input(request)
        common_prefix_lengths.add(common_prefix_length)
        source_unit_lengths.add(source_unit_length)
        provider_inputs.append(provider_input)
        if common_prefix_bytes is None:
            common_prefix_bytes = provider_input[:common_prefix_length]
        elif provider_input[:common_prefix_length] != common_prefix_bytes:
            raise BoundedNodeFamilyDiagnosticError("family inputs diverge before family-specific material")
        if b"historical_diagnostic" in provider_input or b"secondary_fixed_node" in provider_input:
            raise BoundedNodeFamilyDiagnosticError("historical references entered provider input")
        body = build_responses_api_request(provider_input, model_authorable_schema=schema, max_output_tokens=DIAGNOSTIC_MAX_OUTPUT_TOKENS)
        body_bytes = canonical_json(body)
        record: dict[str, Any] = {
            "artifactRole": "development_only_dev02_bounded_node_family_stability_preflight", "diagnosticVersion": DIAGNOSTIC_VERSION,
            "developmentID": "DEV-02", "familyID": family_id, "familyName": FAMILIES[family_id][0], "providerCalls": 0,
            "executionModeIntended": "responses_synchronous_structured_output; not dispatched", "model": body["model"],
            "reasoningEffort": body["reasoning"]["effort"], "maxOutputTokens": body["max_output_tokens"], "store": body["store"],
            "providerInputSha256": sha256_bytes(provider_input), "specializedSchemaSha256": sha256_bytes(canonical_json(schema)),
            "completeRequestBodySha256": sha256_bytes(body_bytes), "providerInputByteCount": len(provider_input),
            "specializedSchemaByteCount": len(canonical_json(schema)), "completeRequestBodyByteCount": len(body_bytes),
            "commonSourceMaterialPrefixByteCount": common_prefix_length, "sourceUnitByteCount": source_unit_length,
            "offlineTokenEstimate": None, "offlineTokenEstimateStatus": "not deterministically available from repository authority",
            "familyTargetCount": len(request["eligibleOperationalTargetIDs"]), "familyTargetUniverseEqualsSchemaUniverse": True,
            "candidateEdgesStructurallyEmpty": True, "deferredRecordsStructurallyEmpty": True, "historicalReferencesExcludedFromProviderInput": True,
            "requestByteIdentityAssertion": True, "retainedDefinitions": sorted(schema["$defs"]),
            "visiblePublicationNodeOperationalIDs": sorted(set(re.findall(r"PUB-N-[A-Za-z0-9-]+", canonical_json(schema).decode("utf-8")))),
            "visiblePublicationRelationOperationalIDCount": 0,
        }
        record["preflightSha256"] = sha256_bytes(canonical_json(record))
        for run_id in RUN_IDS:
            root = OUTPUT_ROOT / family_id / run_id
            _write_canonical(root / "request.json", request)
            _write_canonical(root / "specialized_schema.json", schema)
            _write_exact(root / "provider_input.txt", provider_input)
            _write_exact(root / "complete_request_body.json", body_bytes)
            _write_canonical(root / "preflight.json", record)
            _write_canonical(root / "frozen_sha_records.json", {"providerInputSha256": record["providerInputSha256"], "specializedSchemaSha256": record["specializedSchemaSha256"], "completeRequestBodySha256": record["completeRequestBodySha256"], "providerCalls": 0})
        if (OUTPUT_ROOT / family_id / "R1" / "complete_request_body.json").read_bytes() != (OUTPUT_ROOT / family_id / "R2" / "complete_request_body.json").read_bytes():
            raise BoundedNodeFamilyDiagnosticError(f"{family_id} R1/R2 request bodies are not byte-identical")
        records.append(record)
    if len(common_prefix_lengths) != 1 or len(source_unit_lengths) != 1:
        raise BoundedNodeFamilyDiagnosticError("family inputs do not share one common source-first prefix topology")
    summary: dict[str, Any] = {"artifactRole": "development_only_dev02_bounded_node_family_stability_preparation_summary", "diagnosticVersion": DIAGNOSTIC_VERSION, "providerCalls": 0, "commonProviderInputPrefixByteCount": _longest_common_prefix_byte_count(provider_inputs), "commonSourceMaterialPrefixByteCount": next(iter(common_prefix_lengths)), "sourceUnitByteCount": next(iter(source_unit_lengths)), "familyPreflights": records, "historicalPoolStatus": historical["semanticReconciliation"], "secondaryFixedNodeCount": fixed["nodeCount"]}
    summary["summarySha256"] = sha256_bytes(canonical_json(summary))
    _write_canonical(OUTPUT_ROOT / "preparation_summary.json", summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """Provide the sole no-provider-call preparation entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="write prospective no-call artifacts")
    args = parser.parse_args(argv)
    if not args.prepare:
        parser.error("only --prepare is supported; this harness never dispatches a provider call")
    print(canonical_json(prepare()).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
