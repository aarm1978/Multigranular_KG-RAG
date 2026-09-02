"""Run M2-C1B full DEV-SET-0 multi-target Publication node development.

The batch consumes all ten accepted M2-C0 plan rows under one prospective v0.1.4
configuration. Each unit has isolated preflight, provider, downstream, and replay
artifacts. Provider calls are available only through an explicit ``--live-unit`` action;
ordinary preparation, aggregation, and replay modes are network-free.

The historical default remains C1B node-only.  The prospective ``--full-semantic`` mode
uses the same request/provider/parser/validator path with the 40 current open-discovery
nodes, all 26 model-authorable relations, and one trusted source-Paper endpoint.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
import json
import os
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
from src.extraction.llm.publications.evidence_coordinate_guide import (  # noqa: E402
    COORDINATE_GUIDE_VERSION,
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
    coordinate_guide_record,
)
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans  # noqa: E402
from src.extraction.llm.publications.prospective_evidence_binding_schema import (  # noqa: E402
    PROSPECTIVE_EVIDENCE_BINDING_SCHEMA_VERSION,
    derive_prospective_evidence_binding_schema,
    prospective_evidence_binding_schema_record,
)
from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    audit_openai_structured_outputs_schema,
    validate_model_authorable_payload,
)
from src.extraction.llm.publications.openai_provider import (  # noqa: E402
    MAX_OUTPUT_TOKENS,
    PROVIDER_ADAPTER_VERSION,
    PROVIDER_NAME,
    REASONING_EFFORT,
    REQUESTED_MODEL,
    STORE,
    OpenAIHTTPError,
    OpenAIProviderError,
    OpenAIProviderResponseError,
    ResponseRetrieveTransport,
    Transport,
    bind_live_response_metadata,
    build_provider_input,
    build_responses_api_request,
    call_openai_background_responses_detailed,
    call_openai_responses_detailed,
    load_openai_api_key,
    provider_input_projection,
    resume_openai_background_response_detailed,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    REQUEST_BUILDER_VERSION,
    TARGET_INVENTORY_PATH,
    build_development_request,
    canonical_json,
    canonical_json_file,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (  # noqa: E402
    TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
    derive_trusted_evidence_metadata_schema,
    trusted_evidence_metadata_schema_record,
)
from src.extraction.llm.publications.response_parser import (  # noqa: E402
    PARSER_VERSION,
    canonical_parsed_envelope,
    parse_recorded_response,
)
from src.extraction.llm.publications.run_publication_multitarget_node_development import (  # noqa: E402
    C0_PLAN_PATH,
    C0_POLICY_PATH,
    C1A_MAX_OUTPUT_TOKENS,
    EXPECTED_DIRECT_NODE_TARGET_COUNT,
    _exposed_targets,
    _projection_hash,
    build_descriptive_diagnostics,
)


DEV_IDS = tuple(f"DEV-{index:02d}" for index in range(1, 11))
RUN_ID = "publication-full-devset0-multitarget-node-development/0.1.0"
FULL_SEMANTIC_RUN_ID = "publication-full-devset0-semantic-development/0.1.0"
PROMPT_VERSION = "publication-development-0.1.5"
PROMPT_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.5.txt"
)
BASE_PROMPT_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.4.txt"
)
HISTORICAL_PROMPT_V013_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/prompts/publication_development_v0.1.3.txt"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c1b"
FULL_SEMANTIC_OUTPUT_DIR = (
    PROJECT_ROOT / "data/curation/papers/m2/future_full_semantic_devset0"
)
C1B_MAX_OUTPUT_TOKENS = C1A_MAX_OUTPUT_TOKENS
EXPECTED_MODEL_AUTHORABLE_RELATION_TARGET_COUNT = 26
OLD_SENTENCE = (
    "No emitted candidate for a target is not an explicit negative presence-or-absence assessment."
)
NEW_SENTENCE = (
    "The absence of an emitted candidate for a target is not an explicit negative "
    "presence-or-absence assessment."
)


def _downstream(
    raw_output: bytes, request: Mapping[str, Any], *, evidence_binding: bool = False
) -> tuple[dict[str, Any], bytes | None, dict[str, Any], dict[str, Any]]:
    """Parse, bind prospective literal evidence, then run unchanged validation."""

    parser_result = parse_recorded_response(raw_output, request)
    if evidence_binding and parser_result.get("parseStatus") == "parsed":
        payload = parser_result.get("parsedDocument")
        if isinstance(payload, Mapping):
            bound_payload, binding = bind_evidence_spans(payload, request["sourceUnit"])
            parser_result["evidenceBinding"] = binding
            if binding["bindingStatus"] == "bound":
                parser_result["parsedEnvelope"].update(bound_payload)
                parser_result["bindingOperations"].append({
                    "operation": "bind_model_authored_literal_evidence",
                    "bindingVersion": binding["bindingVersion"],
                })
            else:
                parser_result["parseStatus"] = "processing_failed"
                parser_result["processingCode"] = "EVIDENCE_BINDING_FAILED"
                parser_result["error"] = "one or more model-authored evidence spans could not bind exactly"
    parsed_bytes = canonical_parsed_envelope(parser_result) if parser_result.get("parseStatus") == "parsed" else None
    validation = validate_candidate_envelope(parser_result, request)
    usable = materialize_usable_pipeline_output(parser_result.get("parsedEnvelope", {}), validation)
    return parser_result, parsed_bytes, validation, usable


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with one trailing line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_durable_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Persist one lifecycle record and force it to stable storage before dispatch."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(canonical_json_file(value))
        handle.flush()
        os.fsync(handle.fileno())


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _unit_paths(
    output_dir: Path,
    development_id: str,
    *,
    artifact_prefix: str = "publication_m2c1b",
) -> dict[str, Path]:
    """Return isolated artifact paths for one DEV unit."""

    unit_dir = output_dir / development_id
    prefix = f"{artifact_prefix}_{development_id.lower().replace('-', '')}"
    return {
        "unitDir": unit_dir,
        "request": unit_dir / f"{prefix}_live_request.json",
        "providerInput": unit_dir / f"{prefix}_exact_provider_input.txt",
        "c0Binding": unit_dir / f"{prefix}_c0_policy_plan_binding.json",
        "coordinateGuide": unit_dir / f"{prefix}_evidence_coordinate_guide.json",
        "coordinateGuideRecord": unit_dir / f"{prefix}_evidence_coordinate_guide_record.json",
        "modelSchema": unit_dir / f"{prefix}_request_specialized_schema.json",
        "modelSchemaRecord": unit_dir / f"{prefix}_request_specialized_schema_record.json",
        "preflight": unit_dir / f"{prefix}_provider_input_preflight.json",
        "attempt": unit_dir / f"{prefix}_attempt_record.json",
        "providerResponse": unit_dir / f"{prefix}_provider_api_response.json",
        "providerMetadata": unit_dir / f"{prefix}_provider_metadata.json",
        "rawModelOutput": unit_dir / f"{prefix}_exact_structured_model_output.json",
        "parserResult": unit_dir / f"{prefix}_parser_result.json",
        "parsedCandidate": unit_dir / f"{prefix}_parsed_candidate.json",
        "validationResults": unit_dir / f"{prefix}_validation_results.json",
        "usablePipelineOutput": unit_dir / f"{prefix}_usable_pipeline_output.json",
        "diagnostics": unit_dir / f"{prefix}_unit_diagnostics.json",
        "reproducibility": unit_dir / f"{prefix}_reproducibility_record.json",
        "providerFailureResponse": unit_dir / f"{prefix}_provider_failure_response.json",
        "providerFailureMetadata": unit_dir / f"{prefix}_provider_failure_metadata.json",
    }


def _root_paths(
    output_dir: Path, *, full_semantic: bool = False
) -> dict[str, Path]:
    """Return C1B aggregate and prompt-provenance paths."""

    prefix = (
        "publication_full_semantic"
        if full_semantic
        else "publication_m2c1b"
    )
    return {
        "promptDiff": output_dir / f"{prefix}_prompt_v0.1.4_semantic_diff.json",
        "preflight": output_dir / f"{prefix}_full_offline_preflight.json",
        "aggregate": output_dir / f"{prefix}_aggregate_development_diagnostics.json",
        "replay": output_dir / f"{prefix}_replay_summary.json",
    }


def build_historical_prompt_v014_diff() -> dict[str, Any]:
    """Prove the frozen v0.1.3 to v0.1.4 one-sentence correction."""

    base_bytes = HISTORICAL_PROMPT_V013_PATH.read_bytes()
    prompt_bytes = BASE_PROMPT_PATH.read_bytes()
    base = base_bytes.decode("utf-8")
    prompt = prompt_bytes.decode("utf-8")
    expected = base.replace(
        "Publication semantic extraction development prompt v0.1.3",
        "Publication semantic extraction development prompt v0.1.4", 1,
    ).replace(OLD_SENTENCE, NEW_SENTENCE, 1)
    if base.count(OLD_SENTENCE) != 1 or prompt != expected:
        raise ValueError("historical v0.1.3 to v0.1.4 prompt correction drifted")
    return {
        "basePromptVersion": "publication-development-0.1.3",
        "basePromptSha256": sha256_bytes(base_bytes),
        "newPromptVersion": "publication-development-0.1.4",
        "newPromptSha256": sha256_bytes(prompt_bytes),
        "oldSentence": OLD_SENTENCE,
        "newSentence": NEW_SENTENCE,
        "semanticSentenceChangeCount": 1,
        "basePromptOtherwiseByteIdentical": True,
    }


def build_prompt_semantic_diff() -> dict[str, Any]:
    """Record and constrain the prospective v0.1.4 to v0.1.5 transition."""

    base_bytes = BASE_PROMPT_PATH.read_bytes()
    prompt_bytes = PROMPT_PATH.read_bytes()
    base = base_bytes.decode("utf-8")
    prompt = prompt_bytes.decode("utf-8")
    target_block_start = "COMPLETE AUTHORIZED TARGET-SPACE SEARCH\n"
    abstention_start = "Abstain with an authorized reason"
    def _target_search_paragraph(value: str) -> str:
        """Extract only the immutable authorized-target search paragraph."""

        start = value.index(target_block_start) + len(target_block_start)
        end = value.index("\n\n", start)
        return value[start:end]
    target_block_unchanged = (
        _target_search_paragraph(base) == _target_search_paragraph(prompt)
    )
    abstention_block_unchanged = base[base.index(abstention_start):] == prompt[prompt.index(abstention_start):]
    if not target_block_unchanged or not abstention_block_unchanged:
        raise ValueError("prospective prompt changed an unauthorized semantic instruction block")
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "prospective_deterministic_evidence_binding_prompt_transition",
        "developmentOnly": True,
        "basePromptVersion": "publication-development-0.1.4",
        "basePromptSha256": sha256_bytes(base_bytes),
        "newPromptVersion": PROMPT_VERSION,
        "newPromptSha256": sha256_bytes(prompt_bytes),
        "versionTitleUpdated": True,
        "coordinateGuidanceRemovedFromProviderInput": True,
        "evidenceRulesChanged": True,
        "evidenceChange": "model authors exact evidenceText; pipeline binds coordinates and hash",
        "authorizedTargetRulesChanged": not target_block_unchanged,
        "extractionCompletenessInstructionsChanged": not target_block_unchanged,
        "abstentionRulesChanged": not abstention_block_unchanged,
        "targetDefinitionContentChanged": False,
        "unrelatedSemanticInstructionsChanged": False,
        "basePromptOtherwiseByteIdentical": False,
        "historicalV014Regression": build_historical_prompt_v014_diff(),
    }


def load_c0_bindings() -> list[dict[str, Any]]:
    """Load all ten exact unit bindings mechanically from accepted C0 artifacts."""

    policy = load_json_object(C0_POLICY_PATH)
    plan = load_json_object(C0_PLAN_PATH)
    if policy.get("status") != "approved_for_development":
        raise ValueError("C0 policy is not approved_for_development")
    if policy.get("policySha256") != _projection_hash(policy, "policySha256"):
        raise ValueError("C0 policy self-hash mismatch")
    if plan.get("planSha256") != _projection_hash(plan, "planSha256"):
        raise ValueError("C0 plan self-hash mismatch")
    rows = {row["developmentID"]: row for row in plan.get("units", [])}
    if tuple(sorted(rows)) != DEV_IDS:
        raise ValueError("C0 plan does not contain exactly DEV-01 through DEV-10")
    bindings = []
    for development_id in DEV_IDS:
        unit = rows[development_id]
        eligible = list(unit.get("eligibleNodeOperationalTargetIDs", []))
        exclusions = {
            row["reason"]: list(row["targetIDs"])
            for row in unit.get("excludedTargetsByReason", [])
        }
        deterministic = exclusions.get("exact_deterministic_endpoint_binding_absent", [])
        deferred = exclusions.get(
            "deferred_only_target_in_open_discovery_and_no_deferred_record_binding", []
        )
        if len(eligible) != EXPECTED_DIRECT_NODE_TARGET_COUNT:
            raise ValueError(f"{development_id} does not authorize exactly 40 nodes")
        if len(deterministic) != 4 or len(deferred) != 2:
            raise ValueError(f"{development_id} exclusion counts differ from 40/4/2")
        if unit.get("unresolvedApplicabilityTargetIDs"):
            raise ValueError(f"{development_id} has unresolved applicability")
        if unit.get("extractionChannel") != "open_discovery":
            raise ValueError(f"{development_id} is not open_discovery")
        metadata = unit["trustedMetadataUsed"]
        if metadata.get("deterministicNodeRefs") or metadata.get("deferredRecordRefs"):
            raise ValueError(f"{development_id} unexpectedly has trusted route bindings")
        bindings.append(
            {
                "bindingSchemaVersion": "0.1.0",
                "artifactRole": "accepted_c0_policy_plan_unit_binding",
                "developmentOnly": True,
                "policyVersion": policy["policyVersion"],
                "policySha256": policy["policySha256"],
                "policyArtifactSha256": sha256_bytes(C0_POLICY_PATH.read_bytes()),
                "planVersion": plan["planVersion"],
                "planSha256": plan["planSha256"],
                "planArtifactSha256": sha256_bytes(C0_PLAN_PATH.read_bytes()),
                "policyDecisionID": "C0-POLICY-DECISION-001",
                "developmentID": development_id,
                "sourceUnitID": unit["sourceUnitID"],
                "publicationArtifactID": unit["publicationArtifactID"],
                "sectionRole": metadata["sectionRole"],
                "extractionChannel": "open_discovery",
                "eligibleNodeOperationalTargetIDs": eligible,
                "eligibleNodeOperationalTargetIDCount": len(eligible),
                "eligibleNodeOperationalTargetIDsSha256": sha256_bytes(
                    canonical_json(eligible)
                ),
                "excludedDeterministicContextTargetIDs": deterministic,
                "excludedDeferredOnlyTargetIDs": deferred,
                "unresolvedApplicabilityTargetIDs": [],
            }
        )
    return bindings


def build_c1b_request(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Build one historical v0.1.4 node-only request from its C0 binding."""

    development_id = str(binding["developmentID"])
    request = build_development_request(
        str(binding["sourceUnitID"]),
        binding["eligibleNodeOperationalTargetIDs"],
        run_id=f"{RUN_ID}/{development_id.lower()}",
        prompt_path=BASE_PROMPT_PATH,
    )
    bound = deepcopy(request)
    bound["developmentID"] = development_id
    bound["prompt"]["version"] = "publication-development-0.1.4"
    definitions = list(bound["targetDefinitions"])
    if any(row.get("emission_mode") != "llm_candidate" for row in definitions):
        raise ValueError(f"{development_id} request contains non-direct targets")
    if any(not str(row.get("operational_id", "")).startswith("PUB-N-") for row in definitions):
        raise ValueError(f"{development_id} request contains relation targets")
    bound["applicabilityPolicyBinding"] = {
        key: value
        for key, value in binding.items()
        if key not in {"artifactRole", "developmentOnly"}
    }
    bound["applicabilityPolicyBinding"]["targetDefinitionsSha256"] = sha256_bytes(
        canonical_json(definitions)
    )
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def model_authorable_relation_target_ids() -> list[str]:
    """Derive the exact current relation universe from the frozen target profile."""

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    relation_ids = [
        str(row["operational_id"])
        for row in profile["relation_targets"]
        if row.get("production_responsibility") == "llm"
        and row.get("emission_mode") == "llm_candidate"
        and row.get("pilot_treatment")
        in {"extract_and_evaluate", "extract_and_monitor"}
    ]
    if len(relation_ids) != EXPECTED_MODEL_AUTHORABLE_RELATION_TARGET_COUNT:
        raise ValueError("frozen model-authorable relation universe is not exactly 26")
    return relation_ids


def build_full_semantic_request(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Build one prospective combined node-and-relation DEV request."""

    development_id = str(binding["developmentID"])
    relation_ids = model_authorable_relation_target_ids()
    target_ids = list(binding["eligibleNodeOperationalTargetIDs"]) + relation_ids
    request = build_development_request(
        str(binding["sourceUnitID"]),
        target_ids,
        run_id=f"{FULL_SEMANTIC_RUN_ID}/{development_id.lower()}",
        prompt_path=PROMPT_PATH,
    )
    bound = deepcopy(request)
    bound["developmentID"] = development_id
    bound["prompt"]["version"] = PROMPT_VERSION
    bound["deterministicEndpoints"] = [
        {
            "nodeID": bound["sourceArtifactID"],
            "className": "Paper",
            "artifactID": bound["sourceArtifactID"],
        }
    ]
    definitions = list(bound["targetDefinitions"])
    if any(row.get("emission_mode") != "llm_candidate" for row in definitions):
        raise ValueError(f"{development_id} request contains non-direct targets")
    relation_definitions = [
        row
        for row in definitions
        if str(row.get("operational_id", "")).startswith("PUB-R-")
    ]
    if [row["operational_id"] for row in relation_definitions] != relation_ids:
        raise ValueError(f"{development_id} relation universe drifted")
    bound["applicabilityPolicyBinding"] = {
        key: value
        for key, value in binding.items()
        if key not in {"artifactRole", "developmentOnly"}
    }
    bound["applicabilityPolicyBinding"].update(
        {
            "eligibleRelationOperationalTargetIDs": relation_ids,
            "eligibleRelationOperationalTargetIDCount": len(relation_ids),
            "eligibleRelationOperationalTargetIDsSha256": sha256_bytes(
                canonical_json(relation_ids)
            ),
            "relationApplicabilityBasis": (
                "frozen model-authorable relation universe; routing asserts "
                "eligibility, not semantic presence"
            ),
            "targetDefinitionsSha256": sha256_bytes(canonical_json(definitions)),
        }
    )
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def _preflight_record(
    binding: Mapping[str, Any],
    request: Mapping[str, Any],
    provider_input: bytes,
    guide_record: Mapping[str, Any],
    schema: Mapping[str, Any],
    schema_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one fail-closed schema, guide, and provider-input preflight record."""

    schema_bytes = canonical_json(schema)
    bounded_request = canonical_json(provider_input_projection(request))
    target_definitions = canonical_json(request["targetDefinitions"])
    nodes = _exposed_targets(schema, "operationalTargetID")
    relations = _exposed_targets(schema, "operationalRelationID")
    if nodes != sorted(binding["eligibleNodeOperationalTargetIDs"]):
        raise ValueError(f"{binding['developmentID']} schema target exposure mismatch")
    expected_relations = sorted(
        binding.get("eligibleRelationOperationalTargetIDs", [])
    )
    full_semantic = bool(expected_relations)
    if relations != expected_relations:
        raise ValueError(
            f"{binding['developmentID']} schema relation exposure mismatch"
        )
    if not schema_audit["compatible"]:
        raise ValueError(f"{binding['developmentID']} provider schema is incompatible")
    explicit = schema_audit["explicitTypeAudit"]
    refs = schema_audit["refAudit"]
    metrics = schema_audit["metrics"]
    missing_types = (
        explicit["constSchemasLackingExplicitType"]
        + explicit["enumSchemasLackingExplicitType"]
        + explicit["directlyConstrainedSchemasLackingCompatibleType"]
    )
    body = build_responses_api_request(
        provider_input,
        model_authorable_schema=schema,
        max_output_tokens=C1B_MAX_OUTPUT_TOKENS,
    )
    historical_provider_input = build_coordinate_guided_provider_input(
        request, build_evidence_coordinate_guide(request["sourceUnit"])
    )
    historical_schema = derive_trusted_evidence_metadata_schema(request)
    historical_body = build_responses_api_request(
        historical_provider_input, model_authorable_schema=historical_schema,
        max_output_tokens=C1B_MAX_OUTPUT_TOKENS, background=True,
    )
    source_text_bytes = len(request["sourceUnit"]["text"].encode("utf-8"))
    api_body_bytes = len(canonical_json(body))
    historical_provider_bytes = len(historical_provider_input)
    historical_api_bytes = len(canonical_json(historical_body))
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": (
            "prospective_full_semantic_unit_offline_preflight"
            if full_semantic
            else "c1b_unit_offline_preflight"
        ),
        "developmentOnly": True,
        "networkCalls": 0,
        "developmentID": binding["developmentID"],
        "sourceUnitID": binding["sourceUnitID"],
        "publicationArtifactID": binding["publicationArtifactID"],
        "sectionRole": binding["sectionRole"],
        "c0PolicySha256": binding["policySha256"],
        "c0PlanSha256": binding["planSha256"],
        "eligibleNodeTargetIDsSha256": binding[
            "eligibleNodeOperationalTargetIDsSha256"
        ],
        "targetDefinitionsSha256": request["applicabilityPolicyBinding"][
            "targetDefinitionsSha256"
        ],
        "boundedRequestCanonicalBytes": len(bounded_request),
        "targetDefinitionCanonicalBytes": len(target_definitions),
        "sourceTextBytes": source_text_bytes,
        "specializedSchemaCanonicalBytes": len(schema_bytes),
        "coordinateGuideCanonicalBytes": guide_record["canonicalBytes"],
        "providerInputBytes": len(provider_input),
        "totalApiBodyBytes": api_body_bytes,
        "coordinateGuideBytesExcludedFromTransport": (
            guide_record["canonicalBytes"] + len("\n\nDeterministic trusted evidence-coordinate guide JSON:\n".encode("utf-8"))
            if full_semantic else 0
        ),
        "reductionVersusCommittedCoordinateGuideTransport": {
            "providerInputBytes": historical_provider_bytes - len(provider_input),
            "providerInputPercent": round(100 * (historical_provider_bytes - len(provider_input)) / historical_provider_bytes, 4),
            "totalApiBodyBytes": historical_api_bytes - api_body_bytes,
            "totalApiBodyPercent": round(100 * (historical_api_bytes - api_body_bytes) / historical_api_bytes, 4),
        },
        "providerInputSha256": sha256_bytes(provider_input),
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "maxOutputTokens": C1B_MAX_OUTPUT_TOKENS,
        "historicalProviderDefaultMaxOutputTokens": MAX_OUTPUT_TOKENS,
        "outputBudgetOverrideScope": (
            "future_full_semantic_DEVSET0_only"
            if full_semantic
            else "M2-C1B_only_prospective"
        ),
        "schemaSha256": sha256_bytes(schema_bytes),
        "exposedNodeOperationalTargetIDs": nodes,
        "exposedNodeTargetCount": len(nodes),
        "exposedRelationOperationalTargetIDs": relations,
        "exposedRelationTargetCount": len(relations),
        "schemaObjectPropertyCount": metrics["totalObjectPropertyCount"],
        "schemaEnumValueCount": metrics["totalEnumValueCount"],
        "schemaMaximumDepth": metrics["maxNestingDepth"],
        "schemaStringBudget": metrics["aggregateSchemaStringBudget"],
        "schemaRefSiblingCount": refs["refSiblingNodes"],
        "schemaUnresolvedReferenceCount": refs["unresolvedRefTargets"],
        "schemaMissingExplicitTypeCount": missing_types,
        "schemaInvalidAnyOfBranchCount": explicit["invalidAnyOfBranchCount"],
        "coordinateGuideVersion": guide_record["coordinateGuideVersion"],
        "coordinateGuideEntryCount": guide_record["entryCount"],
        "coordinateGuideSha256": guide_record["coordinateGuideSha256"],
        "providerSettings": {
            "model": body["model"],
            "reasoningEffort": body["reasoning"]["effort"],
            "maxOutputTokens": body["max_output_tokens"],
            "store": body["store"],
            "tools": "none",
            "web": False,
            "externalRetrieval": False,
            "structuredOutputsStrict": body["text"]["format"]["strict"],
        },
        "providerCompatibilityGate": "PASS",
    }


def prepare_unit(
    binding: Mapping[str, Any],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    full_semantic: bool = False,
) -> dict[str, Any]:
    """Construct and persist one unit's deterministic no-network artifacts."""

    development_id = str(binding["developmentID"])
    artifact_prefix = (
        "publication_full_semantic"
        if full_semantic
        else "publication_m2c1b"
    )
    paths = _unit_paths(
        output_dir, development_id, artifact_prefix=artifact_prefix
    )
    request = (
        build_full_semantic_request(binding)
        if full_semantic
        else build_c1b_request(binding)
    )
    effective_binding = deepcopy(dict(binding))
    if full_semantic:
        relation_ids = model_authorable_relation_target_ids()
        effective_binding["eligibleRelationOperationalTargetIDs"] = relation_ids
        effective_binding["eligibleRelationOperationalTargetIDCount"] = len(
            relation_ids
        )
        effective_binding["eligibleRelationOperationalTargetIDsSha256"] = (
            sha256_bytes(canonical_json(relation_ids))
        )
    guide = build_evidence_coordinate_guide(request["sourceUnit"])
    guide_record = coordinate_guide_record(request["sourceUnit"], guide)
    provider_input = build_provider_input(request) if full_semantic else build_coordinate_guided_provider_input(request, guide)
    schema = derive_prospective_evidence_binding_schema(request) if full_semantic else derive_trusted_evidence_metadata_schema(request)
    schema_record = prospective_evidence_binding_schema_record(request) if full_semantic else trusted_evidence_metadata_schema_record(request)
    schema_audit = audit_openai_structured_outputs_schema(schema)
    preflight = _preflight_record(
        effective_binding,
        request,
        provider_input,
        guide_record,
        schema,
        schema_audit,
    )
    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["c0Binding"], effective_binding)
    _write_canonical(paths["coordinateGuide"], guide)
    _write_canonical(paths["coordinateGuideRecord"], guide_record)
    _write_canonical(paths["modelSchema"], schema)
    _write_canonical(paths["modelSchemaRecord"], schema_record)
    _write_canonical(paths["preflight"], preflight)
    return {
        "paths": paths,
        "binding": effective_binding,
        "request": request,
        "guide": guide,
        "guideRecord": guide_record,
        "providerInput": provider_input,
        "schema": schema,
        "schemaRecord": schema_record,
        "schemaAudit": schema_audit,
        "preflight": preflight,
    }


def prepare_all(
    output_dir: Path = DEFAULT_OUTPUT_DIR, *, full_semantic: bool = False
) -> dict[str, Any]:
    """Construct all ten exact provider inputs and aggregate their offline sizes."""

    prompt_diff = (
        build_prompt_semantic_diff()
        if full_semantic
        else build_historical_prompt_v014_diff()
    )
    states = [
        prepare_unit(
            binding, output_dir=output_dir, full_semantic=full_semantic
        )
        for binding in load_c0_bindings()
    ]
    rows = [state["preflight"] for state in states]
    aggregate = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": (
            "prospective_full_semantic_devset0_offline_preflight"
            if full_semantic
            else "c1b_full_devset0_offline_preflight"
        ),
        "developmentOnly": True,
        "networkCalls": 0,
        "promptSemanticDiff": prompt_diff,
        "unitCount": len(rows),
        "allProviderCompatibilityGatesPass": all(
            row["providerCompatibilityGate"] == "PASS" for row in rows
        ),
        "allUnitsExposeFortyNodesAndZeroRelations": all(
            row["exposedNodeTargetCount"] == 40
            and row["exposedRelationTargetCount"] == 0
            for row in rows
        ),
        "allUnitsExposeExpectedTargets": all(
            row["exposedNodeTargetCount"] == 40
            and row["exposedRelationTargetCount"]
            == (EXPECTED_MODEL_AUTHORABLE_RELATION_TARGET_COUNT if full_semantic else 0)
            for row in rows
        ),
        "aggregateBoundedRequestCanonicalBytes": sum(
            row["boundedRequestCanonicalBytes"] for row in rows
        ),
        "aggregateTargetDefinitionCanonicalBytes": sum(
            row["targetDefinitionCanonicalBytes"] for row in rows
        ),
        "aggregateSpecializedSchemaCanonicalBytes": sum(
            row["specializedSchemaCanonicalBytes"] for row in rows
        ),
        "aggregateCoordinateGuideCanonicalBytes": sum(
            row["coordinateGuideCanonicalBytes"] for row in rows
        ),
        "aggregateProviderInputBytes": sum(row["providerInputBytes"] for row in rows),
        "units": rows,
    }
    root_paths = _root_paths(output_dir, full_semantic=full_semantic)
    _write_canonical(root_paths["promptDiff"], prompt_diff)
    _write_canonical(root_paths["preflight"], aggregate)
    return {"promptDiff": prompt_diff, "states": states, "preflight": aggregate}


def _reproducibility_record(
    state: Mapping[str, Any],
    request: Mapping[str, Any],
    response: Mapping[str, Any],
    raw_response: Mapping[str, Any],
    raw_output: bytes,
    parser: Mapping[str, Any],
    parsed: bytes | None,
    validation: Mapping[str, Any],
    usable: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    *,
    execution_mode: str,
) -> dict[str, Any]:
    """Bind one stochastic unit call to deterministic inputs and downstream hashes."""

    binding = state["binding"]
    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": (
            "publication_full_devset0_semantic_development"
            if state["preflight"]["exposedRelationTargetCount"]
            else "publication_full_devset0_multitarget_node_development"
        ),
        "developmentOnly": True,
        "liveOpenAIOutput": True,
        "notAnnotation": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "liveGenerationDeterministic": False,
        "coordinateGuideConstructionDeterministic": True,
        "coordinateGuideTransport": (
            "excluded_from_prospective_full_semantic_provider_input"
            if state["preflight"]["exposedRelationTargetCount"]
            else "included_for_historical_non_full_semantic_transport"
        ),
        "downstreamReplayDeterministic": True,
        "runID": request["runID"],
        "developmentID": binding["developmentID"],
        "sourceUnitID": binding["sourceUnitID"],
        "requestID": request["requestID"],
        "requestInputSha256": request["requestInputSha256"],
        "providerInputSha256": sha256_bytes(state["providerInput"]),
        "promptVersion": request["prompt"]["version"],
        "promptSha256": request["prompt"]["sha256"],
        "c0PolicySha256": binding["policySha256"],
        "c0PlanSha256": binding["planSha256"],
        "eligibleNodeOperationalTargetIDsSha256": binding[
            "eligibleNodeOperationalTargetIDsSha256"
        ],
        "eligibleRelationOperationalTargetIDsSha256": binding.get(
            "eligibleRelationOperationalTargetIDsSha256"
        ),
        "targetDefinitionsSha256": request["applicabilityPolicyBinding"][
            "targetDefinitionsSha256"
        ],
        "coordinateGuideVersion": COORDINATE_GUIDE_VERSION,
        "coordinateGuideSha256": state["guideRecord"]["coordinateGuideSha256"],
        "coordinateGuideEntryCount": state["guideRecord"]["entryCount"],
        "requestSpecializedSchemaVersion": (
            PROSPECTIVE_EVIDENCE_BINDING_SCHEMA_VERSION
            if state["preflight"]["exposedRelationTargetCount"]
            else TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION
        ),
        "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(state["schema"])),
        "modelAuthorableSchemaRecordHash": state["schemaRecord"]["recordSha256"],
        "requestBuilderVersion": REQUEST_BUILDER_VERSION,
        "parserVersion": PARSER_VERSION,
        "validatorVersion": VALIDATOR_VERSION,
        "validationContractVersion": VALIDATION_CONTRACT_VERSION,
        "providerAdapterVersion": PROVIDER_ADAPTER_VERSION,
        "provider": PROVIDER_NAME,
        "requestedModel": REQUESTED_MODEL,
        "returnedModel": response["returnedModel"],
        "reasoningEffort": REASONING_EFFORT,
        "maxOutputTokens": C1B_MAX_OUTPUT_TOKENS,
        "toolConfiguration": "none",
        "store": STORE,
        "executionMode": execution_mode,
        "apiResponseID": response["responseID"],
        "apiStatus": response["status"],
        "tokenUsage": response["usage"],
        "retryCount": 0,
        "providerResponseSha256": sha256_bytes(canonical_json(raw_response)),
        "rawModelOutputSha256": sha256_bytes(raw_output),
        "parserResultSha256": sha256_bytes(canonical_json(parser)),
        "parsedCandidateSha256": sha256_bytes(parsed) if parsed else None,
        "validationResultsHash": validation.get("validationResultsHash"),
        "validationArtifactSha256": sha256_bytes(canonical_json(validation)),
        "usablePipelineOutputHash": usable.get("usablePipelineOutputHash"),
        "usableArtifactSha256": sha256_bytes(canonical_json(usable)),
        "diagnosticsSha256": sha256_bytes(canonical_json(diagnostics)),
        "parseStatus": parser.get("parseStatus"),
        "postGenerationRepairApplied": False,
    }
    record["reproducibilityRecordHash"] = sha256_bytes(canonical_json(record))
    return record


def run_live_unit(
    development_id: str,
    api_key: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: Transport | None = None,
    retrieval_transport: ResponseRetrieveTransport | None = None,
    full_semantic: bool = False,
    recovery_of: Mapping[str, Any] | None = None,
    attempt_number: int = 1,
    resume: bool = False,
) -> dict[str, Any]:
    """Make exactly one guarded provider attempt for one selected DEV unit."""

    bindings = {row["developmentID"]: row for row in load_c0_bindings()}
    if development_id not in bindings:
        raise ValueError(f"unsupported development ID: {development_id}")
    artifact_prefix = (
        "publication_full_semantic"
        if full_semantic
        else "publication_m2c1b"
    )
    paths = _unit_paths(
        output_dir, development_id, artifact_prefix=artifact_prefix
    )
    attempt_markers = (
        paths["attempt"], paths["providerResponse"], paths["providerFailureMetadata"]
    )
    existing_attempt = paths["attempt"] if paths["attempt"].exists() else None
    if any(path.exists() for path in attempt_markers) and not resume:
        raise ValueError(f"{development_id} already has a provider-attempt artifact")
    if resume:
        if not full_semantic or existing_attempt is None:
            raise ValueError("only a submitted full-semantic attempt can be resumed")
        if paths["providerResponse"].exists() or paths["providerFailureMetadata"].exists():
            raise ValueError(f"{development_id} already has a terminal provider artifact")
    state = prepare_unit(
        bindings[development_id],
        output_dir=output_dir,
        full_semantic=full_semantic,
    )
    initiated_attempt: dict[str, Any] = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "provider_attempt_lifecycle",
        "developmentID": development_id,
        "attemptCount": attempt_number,
        "status": "initiated",
        "semanticResponseProduced": False,
        "retryCount": 0,
        "requestInputSha256": state["request"]["requestInputSha256"],
        "providerInputSha256": sha256_bytes(state["providerInput"]),
        "modelAuthorableSchemaSha256": sha256_bytes(
            canonical_json(state["schema"])
        ),
        "requestedModel": REQUESTED_MODEL,
        "reasoningEffort": REASONING_EFFORT,
        "maxOutputTokens": C1B_MAX_OUTPUT_TOKENS,
        "store": STORE,
    }
    if recovery_of is not None:
        initiated_attempt["recoveryOf"] = deepcopy(dict(recovery_of))
    if resume:
        initiated_attempt = load_json_object(existing_attempt)
        if initiated_attempt.get("status") != "submitted":
            raise ValueError(f"{development_id} attempt is not submitted for resumption")
        if not isinstance(initiated_attempt.get("responseID"), str):
            raise ValueError(f"{development_id} submitted attempt lacks response ID")
    else:
        _write_durable_canonical(paths["attempt"], initiated_attempt)
    kwargs = {} if transport is None else {"transport": transport}
    lifecycle_attempt = initiated_attempt
    try:
        if full_semantic:
            background_kwargs: dict[str, Any] = {}
            if transport is not None and not resume:
                background_kwargs["creation_transport"] = transport
            if retrieval_transport is not None:
                background_kwargs["retrieval_transport"] = retrieval_transport

            def persist_background_response_id(
                created: Mapping[str, Any], _body: Mapping[str, Any]
            ) -> None:
                """Durably bind the provider response ID before polling it."""

                nonlocal lifecycle_attempt
                lifecycle_attempt = {
                    **initiated_attempt,
                    "status": "submitted",
                    "responseID": created["id"],
                    "creationStatus": created.get("status"),
                    "executionMode": "background",
                }
                _write_durable_canonical(paths["attempt"], lifecycle_attempt)

            if resume:
                raw_output, response, raw_response = resume_openai_background_response_detailed(
                    api_key, initiated_attempt["responseID"], state["providerInput"],
                    model_authorable_schema=state["schema"],
                    max_output_tokens=C1B_MAX_OUTPUT_TOKENS,
                    **background_kwargs,
                )
            else:
                raw_output, response, raw_response = call_openai_background_responses_detailed(
                    api_key,
                    state["providerInput"],
                    model_authorable_schema=state["schema"],
                    max_output_tokens=C1B_MAX_OUTPUT_TOKENS,
                    on_response_created=persist_background_response_id,
                    **background_kwargs,
                )
            execution_mode = "background"
        else:
            raw_output, response, raw_response = call_openai_responses_detailed(
                api_key,
                state["providerInput"],
                model_authorable_schema=state["schema"],
                max_output_tokens=C1B_MAX_OUTPUT_TOKENS,
                **kwargs,
            )
            execution_mode = "synchronous"
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
        attempt = {
            **lifecycle_attempt,
            "status": "provider_failed",
            "httpStatus": diagnostic["httpStatus"],
            "xRequestID": diagnostic["xRequestID"],
            "semanticResponseProduced": False,
            "retryCount": 0,
        }
        _write_canonical(paths["attempt"], attempt)
        raise
    except OpenAIProviderResponseError as exc:
        metadata = dict(exc.response_record)
        metadata["providerRunFailureCode"] = exc.failure_code
        _write_canonical(paths["providerFailureResponse"], exc.response)
        _write_canonical(paths["providerFailureMetadata"], metadata)
        status = "incomplete" if exc.failure_code in {
            "STATUS_NOT_COMPLETED", "INCOMPLETE_DETAILS_PRESENT"
        } else "provider_failed"
        attempt = {
            **lifecycle_attempt,
            "status": status,
            "providerFailureCode": exc.failure_code,
            "semanticResponseProduced": False,
            "retryCount": 0,
        }
        _write_canonical(paths["attempt"], attempt)
        raise
    except OpenAIProviderError as exc:
        attempt = {
            **lifecycle_attempt,
            "status": "provider_failed",
            "safeFailureMessage": str(exc),
            "semanticResponseProduced": False,
            "retryCount": 0,
        }
        _write_canonical(paths["attempt"], attempt)
        raise
    response["retryCount"] = 0
    request = bind_live_response_metadata(
        state["request"], response, max_output_tokens=C1B_MAX_OUTPUT_TOKENS
    )
    if (build_provider_input(request) if full_semantic else build_coordinate_guided_provider_input(request, state["guide"])) != state["providerInput"]:
        raise ValueError("provider input changed while binding live response metadata")
    payload = json.loads(raw_output.decode("utf-8"))
    if validate_model_authorable_payload(payload, state["schema"]):
        raise ValueError("provider output violated the supplied request-specialized schema")
    first = _downstream(raw_output, request, evidence_binding=full_semantic)
    parsed_payload = first[0].get("parsedDocument", {})
    diagnostics = build_descriptive_diagnostics(
        request, parsed_payload, first[2], first[3], response
    )
    record = _reproducibility_record(
        state, request, response, raw_response, raw_output,
        first[0], first[1], first[2], first[3], diagnostics,
        execution_mode=execution_mode,
    )
    replay_one = _downstream(raw_output, request, evidence_binding=full_semantic)
    replay_two = _downstream(raw_output, request, evidence_binding=full_semantic)
    first_values = (
        replay_one[1], canonical_json(replay_one[2]), canonical_json(replay_one[3])
    )
    second_values = (
        replay_two[1], canonical_json(replay_two[2]), canonical_json(replay_two[3])
    )
    if first_values != second_values:
        raise ValueError(f"{development_id} downstream replay differs")
    replay_record = _reproducibility_record(
        state, request, response, raw_response, raw_output,
        replay_one[0], replay_one[1], replay_one[2], replay_one[3], diagnostics,
        execution_mode=execution_mode,
    )
    if canonical_json(record) != canonical_json(replay_record):
        raise ValueError(f"{development_id} reproducibility replay differs")
    attempt = {
        **lifecycle_attempt,
        "status": "completed",
        "responseID": response["responseID"],
        "semanticResponseProduced": True,
        "retryCount": 0,
    }
    _write_canonical(paths["request"], request)
    _write_canonical(paths["attempt"], attempt)
    _write_canonical(paths["providerResponse"], raw_response)
    _write_canonical(paths["providerMetadata"], response)
    _write_exact(paths["rawModelOutput"], raw_output)
    _write_canonical(paths["parserResult"], first[0])
    if first[1] is not None:
        _write_exact(paths["parsedCandidate"], first[1])
    _write_canonical(paths["validationResults"], first[2])
    _write_canonical(paths["usablePipelineOutput"], first[3])
    _write_canonical(paths["diagnostics"], diagnostics)
    _write_canonical(paths["reproducibility"], record)
    return {
        "developmentID": development_id,
        "providerResponse": response,
        "diagnostics": diagnostics,
        "reproducibility": record,
        "replayByteIdentical": True,
    }


def run_unresolved_attempt_recovery(
    development_id: str,
    api_key: str,
    *,
    output_dir: Path = FULL_SEMANTIC_OUTPUT_DIR,
    transport: Transport | None = None,
    retrieval_transport: ResponseRetrieveTransport | None = None,
) -> dict[str, Any]:
    """Create one explicitly requested recovery attempt beside an unresolved record."""

    paths = _unit_paths(
        output_dir, development_id, artifact_prefix="publication_full_semantic"
    )
    if not paths["attempt"].exists():
        raise ValueError(f"{development_id} has no unresolved attempt to recover")
    prior = load_json_object(paths["attempt"])
    if prior.get("status") not in {"initiated", "submitted"}:
        raise ValueError(f"{development_id} prior attempt is already terminal")
    recovery_root = paths["unitDir"] / "researcher_authorized_recovery_001"
    recovery_paths = _unit_paths(
        recovery_root, development_id, artifact_prefix="publication_full_semantic"
    )
    if any(
        path.exists()
        for path in (
            recovery_paths["attempt"], recovery_paths["providerResponse"],
            recovery_paths["providerFailureMetadata"],
        )
    ):
        raise ValueError(f"{development_id} recovery attempt already exists")
    recovery_of = {
        "priorAttemptPath": str(paths["attempt"].relative_to(output_dir)),
        "priorAttemptSha256": sha256_bytes(paths["attempt"].read_bytes()),
        "priorAttemptStatus": prior["status"],
        "priorAttemptResponseID": prior.get("responseID"),
    }
    return run_live_unit(
        development_id,
        api_key,
        output_dir=recovery_root,
        transport=transport,
        retrieval_transport=retrieval_transport,
        full_semantic=True,
        recovery_of=recovery_of,
        attempt_number=int(prior.get("attemptCount", 1)) + 1,
    )


def replay_unit(
    development_id: str, *, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> dict[str, Any]:
    """Replay one completed preserved output twice without a provider call."""

    paths = _unit_paths(output_dir, development_id)
    attempt = load_json_object(paths["attempt"])
    if attempt.get("status") != "completed":
        return {
            "developmentID": development_id,
            "status": attempt.get("status"),
            "replayApplicable": False,
        }
    request = load_json_object(paths["request"])
    raw = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw, request)
    second = _downstream(raw, request)
    values_one = (first[1], canonical_json(first[2]), canonical_json(first[3]))
    values_two = (second[1], canonical_json(second[2]), canonical_json(second[3]))
    if values_one != values_two:
        raise ValueError(f"preserved {development_id} replay differs")
    return {
        "developmentID": development_id,
        "status": "completed",
        "replayApplicable": True,
        "byteIdentical": True,
        "parsedCandidateSha256": sha256_bytes(values_one[0]) if values_one[0] else None,
        "validationResultsSha256": sha256_bytes(values_one[1]),
        "usablePipelineOutputSha256": sha256_bytes(values_one[2]),
    }


def replay_all(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay all completed C1B outputs and preserve one aggregate summary."""

    units = [replay_unit(development_id, output_dir=output_dir) for development_id in DEV_IDS]
    record = {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "c1b_deterministic_downstream_replay_summary",
        "developmentOnly": True,
        "providerCalls": 0,
        "allApplicableReplaysByteIdentical": all(
            not row["replayApplicable"] or row["byteIdentical"] for row in units
        ),
        "units": units,
    }
    _write_canonical(_root_paths(output_dir)["replay"], record)
    return record


def _candidate_target(candidate: Mapping[str, Any]) -> str | None:
    """Return a node or relation operational target ID."""

    value = candidate.get("operationalTargetID", candidate.get("operationalRelationID"))
    return str(value) if value is not None else None


def _validation_finding_code_counts(
    validation: Mapping[str, Any],
) -> Counter[str]:
    """Count every authoritative validator finding occurrence by code."""

    counts: Counter[str] = Counter()
    for finding in validation.get("globalFindings", []):
        if finding.get("code"):
            counts[str(finding["code"])] += 1
    for result_key in ("evidenceResults", "recordResults"):
        for result in validation.get(result_key, []):
            for finding in result.get("findings", []):
                if finding.get("code"):
                    counts[str(finding["code"])] += 1
    return counts


def build_aggregate_diagnostics(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Aggregate ten preserved unit observations without formal evaluation metrics."""

    bindings = load_c0_bindings()
    target_ids = list(bindings[0]["eligibleNodeOperationalTargetIDs"])
    target_counts = {
        target_id: {development_id: 0 for development_id in DEV_IDS}
        for target_id in target_ids
    }
    target_classes: dict[str, list[dict[str, str]]] = {}
    provider_counts = Counter()
    unit_rows: list[dict[str, Any]] = []
    validation_codes: Counter[str] = Counter()
    validation_units: defaultdict[str, set[str]] = defaultdict(set)
    total_usage = Counter()
    total_counts = Counter()
    exact_reuse_rows: list[dict[str, Any]] = []
    near_overlap_rows: list[dict[str, Any]] = []
    formal_duplicate_rows: list[dict[str, Any]] = []
    review_flags: list[dict[str, Any]] = []
    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    accepted_discourse = set(profile["class_expansions"]["accepted_discourse_node"])
    discourse_counts = Counter()

    for binding in bindings:
        development_id = binding["developmentID"]
        paths = _unit_paths(output_dir, development_id)
        attempt = load_json_object(paths["attempt"])
        provider_counts["attempted"] += 1
        status = str(attempt["status"])
        provider_counts[status] += 1
        if status != "completed":
            unit_rows.append(
                {
                    "developmentID": development_id,
                    "providerStatus": status,
                    "semanticOutputAvailable": False,
                }
            )
            review_flags.append(
                {
                    "developmentID": development_id,
                    "flag": "provider_failure_or_incompletion",
                    "automaticError": False,
                }
            )
            continue
        request = load_json_object(paths["request"])
        provider = load_json_object(paths["providerMetadata"])
        payload = load_json_object(paths["rawModelOutput"])
        validation = load_json_object(paths["validationResults"])
        usable = load_json_object(paths["usablePipelineOutput"])
        diagnostics = load_json_object(paths["diagnostics"])
        candidates = list(payload.get("candidateNodes", []))
        evidence = {row["evidenceSpanID"]: row for row in payload.get("evidenceSpans", [])}
        for definition in request["targetDefinitions"]:
            target_classes[definition["operational_id"]] = [
                {"ontologyClassID": item["id"], "className": item["name"]}
                for item in definition["formal_classes"]
            ]
        by_evidence: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for candidate in candidates:
            target_id = str(candidate["operationalTargetID"])
            target_counts[target_id][development_id] += 1
            class_name = str(candidate["className"])
            discourse_counts[
                "accepted_discourse_node"
                if class_name in accepted_discourse
                else "not_listed_in_accepted_discourse_node"
            ] += 1
            for evidence_id in candidate.get("evidenceSpanIDs", []):
                by_evidence[evidence_id].append(candidate)
        for evidence_id, supported in sorted(by_evidence.items()):
            classes = sorted({str(row["className"]) for row in supported})
            targets = sorted({str(row["operationalTargetID"]) for row in supported})
            if len(classes) > 1:
                row = {
                    "developmentID": development_id,
                    "evidenceSpanID": evidence_id,
                    "targetClasses": classes,
                    "operationalTargetIDs": targets,
                    "candidateIDs": sorted(str(item["candidateID"]) for item in supported),
                    "analysisType": "exact_evidence_span_reuse_descriptive_only",
                }
                exact_reuse_rows.append(row)
                if sum(name in accepted_discourse for name in classes) > 1:
                    review_flags.append(
                        {
                            "developmentID": development_id,
                            "flag": "same_evidence_reused_across_multiple_discourse_classes",
                            "evidenceSpanID": evidence_id,
                            "automaticError": False,
                        }
                    )
        evidence_ids = sorted(evidence)
        for index, left_id in enumerate(evidence_ids):
            for right_id in evidence_ids[index + 1 :]:
                left_text = evidence[left_id]["evidenceText"]
                right_text = evidence[right_id]["evidenceText"]
                if left_text == right_text:
                    continue
                ratio = SequenceMatcher(None, left_text, right_text, autojunk=False).ratio()
                left_classes = sorted({str(row["className"]) for row in by_evidence[left_id]})
                right_classes = sorted({str(row["className"]) for row in by_evidence[right_id]})
                if ratio >= 0.9 and set(left_classes) != set(right_classes):
                    near_overlap_rows.append(
                        {
                            "developmentID": development_id,
                            "evidenceSpanIDs": [left_id, right_id],
                            "sequenceMatcherRatio": ratio,
                            "leftTargetClasses": left_classes,
                            "rightTargetClasses": right_classes,
                            "analysisType": "additional_textual_overlap_development_diagnostic_not_validator_finding",
                        }
                    )
        unit_code_counts = _validation_finding_code_counts(validation)
        codes = sorted(unit_code_counts)
        for code, count in unit_code_counts.items():
            validation_codes[code] += count
            validation_units[code].add(development_id)
            if "DUPLICATE" in code:
                formal_duplicate_rows.append(
                    {
                        "developmentID": development_id,
                        "validatorFindingCode": code,
                        "occurrenceCount": count,
                    }
                )
        counts = diagnostics["candidateTotals"]
        status_counts = diagnostics["validation"]["candidateStatusCounts"]
        valid_evidence = diagnostics["validation"]["validEvidenceSpanCount"]
        evidence_count = diagnostics["validation"]["evidenceSpanCount"]
        usable_count = diagnostics["validation"]["usableCandidateCount"]
        total_counts.update(
            {
                "candidateNodes": counts["candidateNodes"],
                "evidenceSpans": evidence_count,
                "validatedCandidates": status_counts.get("validated", 0),
                "rejectedCandidates": status_counts.get("rejected", 0),
                "usableCandidates": usable_count,
                "validEvidenceSpans": valid_evidence,
            }
        )
        usage = provider["usage"]
        total_usage.update(
            {
                "inputTokens": usage.get("input_tokens", 0),
                "outputTokens": usage.get("output_tokens", 0),
                "reasoningTokens": usage.get("output_tokens_details", {}).get(
                    "reasoning_tokens", 0
                ),
            }
        )
        emitted_counts = Counter(
            str(row["operationalTargetID"]) for row in candidates
        )
        if candidates and max(emitted_counts.values()) / len(candidates) > 0.5:
            review_flags.append(
                {
                    "developmentID": development_id,
                    "flag": "candidate_concentration_over_50_percent_in_one_target",
                    "automaticError": False,
                }
            )
        flag_conditions = {
            "schema_contract_failure": diagnostics["validation"]["schemaValidationFailureCount"] > 0,
            "invalid_evidence": valid_evidence != evidence_count,
            "unauthorized_target": bool(diagnostics["unauthorizedTargetIDs"]),
            "rejected_candidate": status_counts.get("rejected", 0) > 0,
            "output_truncation_or_incompletion": diagnostics["outputCompleteness"][
                "incompleteDetails"
            ] is not None,
        }
        for flag, present in flag_conditions.items():
            if present:
                review_flags.append(
                    {
                        "developmentID": development_id,
                        "flag": flag,
                        "automaticError": False,
                    }
                )
        unit_rows.append(
            {
                "developmentID": development_id,
                "providerStatus": provider["status"],
                "responseID": provider["responseID"],
                "inputTokens": provider["inputTokens"],
                "outputTokens": provider["outputTokens"],
                "reasoningTokens": provider["reasoningTokens"],
                "incompleteDetails": provider["incompleteDetails"],
                "candidateNodes": counts["candidateNodes"],
                "candidateEdges": counts["candidateEdges"],
                "evidenceSpans": evidence_count,
                "validEvidenceSpans": valid_evidence,
                "schemaValidationFailures": diagnostics["validation"][
                    "schemaValidationFailureCount"
                ],
                "candidateValidationStatusCounts": status_counts,
                "usableCandidates": usable_count,
                "validationFindingCodes": codes,
                "targetsWithCandidates": diagnostics["targetsWithCandidateNodes"],
                "targetsWithNoCandidateEmitted": diagnostics[
                    "eligibleTargetsWithNoCandidateEmitted"
                ],
            }
        )

    utilization = []
    for target_id in target_ids:
        per_unit = target_counts[target_id]
        utilization.append(
            {
                "operationalTargetID": target_id,
                "ontologyClasses": target_classes.get(target_id, []),
                "unitCountWithCandidate": sum(value > 0 for value in per_unit.values()),
                "totalCandidates": sum(per_unit.values()),
                "candidateCountsByUnit": per_unit,
            }
        )
    completed_outputs = [row["outputTokens"] for row in unit_rows if "outputTokens" in row]
    aggregate: dict[str, Any] = {
        "reportSchemaVersion": "0.1.0",
        "artifactRole": "c1b_aggregate_development_diagnostics",
        "developmentOnly": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "formalAccuracyMetricsComputed": False,
        "providerRequests": {
            "attempted": provider_counts["attempted"],
            "completed": provider_counts["completed"],
            "failed": provider_counts["provider_failed"],
            "incomplete": provider_counts["incomplete"],
        },
        "aggregateCounts": dict(sorted(total_counts.items())),
        "units": unit_rows,
        "evidenceValidity": {
            "valid": total_counts["validEvidenceSpans"],
            "total": total_counts["evidenceSpans"],
        },
        "validationFindingCodeFrequencies": dict(sorted(validation_codes.items())),
        "validationFindingUnits": {
            code: sorted(units) for code, units in sorted(validation_units.items())
        },
        "targetUtilization": utilization,
        "candidateConcentration": {
            "candidateCountsPerTarget": {
                row["operationalTargetID"]: row["totalCandidates"] for row in utilization
            },
            "candidateCountsPerUnit": {
                row["developmentID"]: row.get("candidateNodes")
                for row in unit_rows
            },
            "mostFrequentTargetClasses": sorted(
                (
                    {
                        "operationalTargetID": row["operationalTargetID"],
                        "candidateCount": row["totalCandidates"],
                        "proportionOfAllCandidates": (
                            row["totalCandidates"] / total_counts["candidateNodes"]
                            if total_counts["candidateNodes"]
                            else 0
                        ),
                    }
                    for row in utilization
                ),
                key=lambda row: (-row["candidateCount"], row["operationalTargetID"]),
            ),
        },
        "frozenInventoryClassGrouping": {
            "authority": "publication_target_inventory.class_expansions.accepted_discourse_node",
            "acceptedDiscourseNodeCandidateCount": discourse_counts[
                "accepted_discourse_node"
            ],
            "notListedInAcceptedDiscourseNodeCandidateCount": discourse_counts[
                "not_listed_in_accepted_discourse_node"
            ],
            "newConcreteOrDomainTaxonomyInvented": False,
        },
        "multiClassEvidenceOverlap": {
            "exactEvidenceSpansReusedAcrossMultipleTargetClasses": len(exact_reuse_rows),
            "exactReuseRows": exact_reuse_rows,
            "nearIdenticalThreshold": 0.9,
            "nearIdenticalMethod": "difflib.SequenceMatcher_ratio_development_diagnostic",
            "nearIdenticalRows": near_overlap_rows,
            "formalErrorClaimed": False,
        },
        "duplicateDiagnostics": {
            "formalFrozenValidatorDuplicateFindings": formal_duplicate_rows,
            "additionalTextualOverlapIsDevelopmentDiagnosticOnly": True,
        },
        "tokenUsage": {
            "totals": dict(sorted(total_usage.items())),
            "perUnit": [
                {
                    key: row.get(key)
                    for key in (
                        "developmentID", "inputTokens", "outputTokens", "reasoningTokens"
                    )
                }
                for row in unit_rows
            ],
        },
        "outputBudgetPressure": {
            "configuredMaxOutputTokens": C1B_MAX_OUTPUT_TOKENS,
            "maximumObservedOutputTokens": max(completed_outputs, default=None),
            "anyUnitReachedCap": any(
                value == C1B_MAX_OUTPUT_TOKENS for value in completed_outputs
            ),
            "anyUnitApproachedCapAt98Percent": any(
                value >= int(C1B_MAX_OUTPUT_TOKENS * 0.98)
                for value in completed_outputs
            ),
        },
        "reviewFlags": review_flags,
    }
    aggregate["aggregateReportSha256"] = sha256_bytes(canonical_json(aggregate))
    _write_canonical(_root_paths(output_dir)["aggregate"], aggregate)
    return aggregate


def main(argv: Sequence[str] | None = None) -> int:
    """Prepare, run one explicit unit, aggregate, or replay without hidden calls."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--live-unit", choices=DEV_IDS)
    parser.add_argument("--recover-unresolved-unit", choices=DEV_IDS)
    parser.add_argument("--resume-unit", choices=DEV_IDS)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--replay-all", action="store_true")
    parser.add_argument(
        "--full-semantic",
        action="store_true",
        help="prospectively expose 40 nodes plus the frozen 26 relations",
    )
    args = parser.parse_args(argv)
    actions = sum(
        bool(value)
        for value in (
            args.prepare_only, args.live_unit, args.recover_unresolved_unit,
            args.resume_unit,
            args.aggregate_only, args.replay_all
        )
    )
    if actions != 1:
        parser.error("select exactly one action")
    if args.full_semantic and (args.aggregate_only or args.replay_all):
        parser.error("full-semantic aggregate/replay requires completed future outputs")
    output_dir = args.output_dir or (
        FULL_SEMANTIC_OUTPUT_DIR if args.full_semantic else DEFAULT_OUTPUT_DIR
    )
    try:
        if args.prepare_only:
            result = prepare_all(
                output_dir, full_semantic=args.full_semantic
            )["preflight"]
        elif args.live_unit:
            live = run_live_unit(
                args.live_unit,
                load_openai_api_key(),
                output_dir=output_dir,
                full_semantic=args.full_semantic,
            )
            result = {
                "developmentID": args.live_unit,
                "responseID": live["providerResponse"]["responseID"],
                "status": live["providerResponse"]["status"],
                "candidateNodes": live["diagnostics"]["candidateTotals"]["candidateNodes"],
                "usableCandidates": live["diagnostics"]["validation"]["usableCandidateCount"],
                "rawModelOutputSha256": live["reproducibility"]["rawModelOutputSha256"],
            }
        elif args.recover_unresolved_unit:
            if not args.full_semantic:
                parser.error("unresolved-attempt recovery is full-semantic only")
            live = run_unresolved_attempt_recovery(
                args.recover_unresolved_unit,
                load_openai_api_key(),
                output_dir=output_dir,
            )
            result = {
                "developmentID": args.recover_unresolved_unit,
                "recovery": True,
                "responseID": live["providerResponse"]["responseID"],
                "status": live["providerResponse"]["status"],
            }
        elif args.resume_unit:
            if not args.full_semantic:
                parser.error("background response resumption is full-semantic only")
            live = run_live_unit(
                args.resume_unit,
                load_openai_api_key(),
                output_dir=output_dir,
                full_semantic=True,
                resume=True,
            )
            result = {
                "developmentID": args.resume_unit,
                "resumed": True,
                "responseID": live["providerResponse"]["responseID"],
                "status": live["providerResponse"]["status"],
            }
        elif args.aggregate_only:
            result = build_aggregate_diagnostics(output_dir)
        else:
            result = replay_all(output_dir)
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-C1B operation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
