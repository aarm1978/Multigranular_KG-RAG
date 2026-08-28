"""Run the one-call M2-C1A multi-target node extraction on Publication DEV-01.

The runner consumes the accepted M2-C0 machine-readable request plan, preserves the
accepted B3 coordinate-guide implementation, and uses an isolated 32,768-token output
capacity override. It does not alter historical request builders, prompts, or artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
    MAX_OUTPUT_TOKENS,
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
    build_responses_api_request,
    call_openai_responses_detailed,
    load_openai_api_key,
    provider_input_projection,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
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
from src.extraction.llm.publications.run_publication_structured_development_smoke import (  # noqa: E402
    _downstream,
)


DEVELOPMENT_ID = "DEV-01"
SOURCE_UNIT_ID = "pub:17:sec:0007:unit:0001"
RUN_ID = "publication-live-multitarget-node-development/0.1.0"
PROMPT_VERSION = "publication-development-0.1.3"
PROMPT_PATH = (
    PROJECT_ROOT
    / "src/extraction/llm/publications/prompts/publication_development_v0.1.3.txt"
)
BASE_PROMPT_PATH = (
    PROJECT_ROOT
    / "src/extraction/llm/publications/prompts/publication_development_v0.1.2.txt"
)
C0_POLICY_PATH = (
    PROJECT_ROOT
    / "data/curation/papers/m2/c0/publication_node_target_applicability_policy_v0.1.0.json"
)
C0_PLAN_PATH = (
    PROJECT_ROOT
    / "data/curation/papers/m2/c0/publication_devset0_node_request_plan_v0.1.0.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c1a"
C1A_MAX_OUTPUT_TOKENS = 32768
EXPECTED_DIRECT_NODE_TARGET_COUNT = 40
PROMPT_INSERTION_ANCHOR = "DETERMINISTIC EVIDENCE-COORDINATE GUIDANCE\n"
MULTI_TARGET_COVERAGE_BLOCK = (
    "COMPLETE AUTHORIZED TARGET-SPACE SEARCH\n\n"
    "Systematically consider the complete set of authorized operational targets supplied "
    "in the bounded request. Emit every distinct source-supported candidate found for any "
    "authorized target, not merely the most salient candidate or target. Continue to emit "
    "only assertions supported by explicit source evidence, and never emit a candidate for "
    "an unauthorized target. Authorization permits semantic search but does not imply that "
    "a target is present. Do not produce one abstention for every authorized target that "
    "lacks evidence. No emitted candidate for a target is not an explicit negative "
    "presence-or-absence assessment. Do not apply salience thresholds, quotas, section-role "
    "heuristics, or target-specific expectations.\n\n"
)


def _write_canonical(path: Path, value: Mapping[str, Any]) -> None:
    """Write one canonical JSON artifact with exactly one final line feed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _write_exact(path: Path, value: bytes) -> None:
    """Write exact bytes without normalization."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _artifact_paths(output_dir: Path) -> dict[str, Path]:
    """Return isolated M2-C1A development artifact paths."""

    prefix = "publication_m2c1a"
    return {
        "request": output_dir / f"{prefix}_live_request.json",
        "providerInput": output_dir / f"{prefix}_exact_provider_input.txt",
        "promptDiff": output_dir / f"{prefix}_prompt_v0.1.3_semantic_diff.json",
        "c0Binding": output_dir / f"{prefix}_c0_policy_plan_binding.json",
        "coordinateGuide": output_dir / f"{prefix}_evidence_coordinate_guide.json",
        "coordinateGuideRecord": output_dir / f"{prefix}_evidence_coordinate_guide_record.json",
        "modelSchema": output_dir / f"{prefix}_request_specialized_schema.json",
        "modelSchemaRecord": output_dir / f"{prefix}_request_specialized_schema_record.json",
        "preflight": output_dir / f"{prefix}_provider_input_preflight.json",
        "providerResponse": output_dir / f"{prefix}_provider_api_response.json",
        "providerMetadata": output_dir / f"{prefix}_provider_metadata.json",
        "rawModelOutput": output_dir / f"{prefix}_exact_structured_model_output.json",
        "parserResult": output_dir / f"{prefix}_parser_result.json",
        "parsedCandidate": output_dir / f"{prefix}_parsed_candidate.json",
        "validationResults": output_dir / f"{prefix}_validation_results.json",
        "usablePipelineOutput": output_dir / f"{prefix}_usable_pipeline_output.json",
        "diagnostics": output_dir / f"{prefix}_descriptive_diagnostics.json",
        "reproducibility": output_dir / f"{prefix}_reproducibility_record.json",
        "providerFailureResponse": output_dir / f"{prefix}_provider_failure_response.json",
        "providerFailureMetadata": output_dir / f"{prefix}_provider_failure_metadata.json",
    }


def _projection_hash(record: Mapping[str, Any], hash_field: str) -> str:
    """Hash one canonical record after removing its self-hash field."""

    projection = dict(record)
    projection.pop(hash_field, None)
    return sha256_bytes(canonical_json(projection))


def build_prompt_semantic_diff() -> dict[str, Any]:
    """Prove v0.1.3 is v0.1.2 plus only a version title and coverage block."""

    base_bytes = BASE_PROMPT_PATH.read_bytes()
    prompt_bytes = PROMPT_PATH.read_bytes()
    base = base_bytes.decode("utf-8")
    prompt = prompt_bytes.decode("utf-8")
    expected = base.replace(
        "Publication semantic extraction development prompt v0.1.2",
        "Publication semantic extraction development prompt v0.1.3",
        1,
    )
    if expected.count(PROMPT_INSERTION_ANCHOR) != 1:
        raise ValueError("prompt insertion anchor is not unique")
    expected = expected.replace(
        PROMPT_INSERTION_ANCHOR,
        MULTI_TARGET_COVERAGE_BLOCK + PROMPT_INSERTION_ANCHOR,
        1,
    )
    if prompt != expected:
        raise ValueError("prompt v0.1.3 contains an unrelated change from v0.1.2")
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "prospective_prompt_semantic_diff",
        "developmentOnly": True,
        "basePromptVersion": "publication-development-0.1.2",
        "basePromptSha256": sha256_bytes(base_bytes),
        "newPromptVersion": PROMPT_VERSION,
        "newPromptSha256": sha256_bytes(prompt_bytes),
        "titleVersionUpdateOnly": True,
        "insertionAnchor": PROMPT_INSERTION_ANCHOR.rstrip("\n"),
        "insertedInstructionSha256": sha256_bytes(MULTI_TARGET_COVERAGE_BLOCK.encode("utf-8")),
        "insertedInstruction": MULTI_TARGET_COVERAGE_BLOCK.rstrip("\n"),
        "removedSemanticInstructions": [],
        "unrelatedExtractionInstructionsChanged": False,
        "basePromptOtherwiseByteIdentical": True,
    }


def load_c0_dev01_binding() -> dict[str, Any]:
    """Load and validate DEV-01 target eligibility from the accepted C0 artifacts."""

    policy = load_json_object(C0_POLICY_PATH)
    plan = load_json_object(C0_PLAN_PATH)
    if policy.get("status") != "approved_for_development":
        raise ValueError("C0 policy is not approved_for_development")
    if policy.get("policySha256") != _projection_hash(policy, "policySha256"):
        raise ValueError("C0 policy self-hash mismatch")
    if plan.get("planSha256") != _projection_hash(plan, "planSha256"):
        raise ValueError("C0 plan self-hash mismatch")
    matches = [row for row in plan.get("units", []) if row.get("developmentID") == DEVELOPMENT_ID]
    if len(matches) != 1:
        raise ValueError("C0 plan must contain exactly one DEV-01 row")
    unit = matches[0]
    eligible = list(unit.get("eligibleNodeOperationalTargetIDs", []))
    excluded = {
        row["reason"]: list(row["targetIDs"])
        for row in unit.get("excludedTargetsByReason", [])
    }
    deterministic = excluded.get("exact_deterministic_endpoint_binding_absent", [])
    deferred = excluded.get(
        "deferred_only_target_in_open_discovery_and_no_deferred_record_binding", []
    )
    if unit.get("sourceUnitID") != SOURCE_UNIT_ID:
        raise ValueError("C0 DEV-01 source-unit binding drift")
    if unit.get("extractionChannel") != "open_discovery":
        raise ValueError("C0 DEV-01 channel is not open_discovery")
    if len(eligible) != EXPECTED_DIRECT_NODE_TARGET_COUNT or unit.get("eligibleNodeTargetCount") != len(eligible):
        raise ValueError("C0 DEV-01 does not authorize exactly 40 node targets")
    if len(deterministic) != 4 or len(deferred) != 2:
        raise ValueError("C0 DEV-01 deterministic/deferred exclusion counts drifted")
    if unit.get("unresolvedApplicabilityTargetIDs"):
        raise ValueError("C0 DEV-01 has unresolved applicability targets")
    return {
        "bindingSchemaVersion": "0.1.0",
        "artifactRole": "accepted_c0_policy_plan_binding",
        "developmentOnly": True,
        "policyVersion": policy["policyVersion"],
        "policySha256": policy["policySha256"],
        "policyArtifactSha256": sha256_bytes(C0_POLICY_PATH.read_bytes()),
        "planVersion": plan["planVersion"],
        "planSha256": plan["planSha256"],
        "planArtifactSha256": sha256_bytes(C0_PLAN_PATH.read_bytes()),
        "policyDecisionID": "C0-POLICY-DECISION-001",
        "developmentID": DEVELOPMENT_ID,
        "sourceUnitID": SOURCE_UNIT_ID,
        "extractionChannel": "open_discovery",
        "eligibleNodeOperationalTargetIDs": eligible,
        "eligibleNodeOperationalTargetIDCount": len(eligible),
        "eligibleNodeOperationalTargetIDsSha256": sha256_bytes(canonical_json(eligible)),
        "excludedDeterministicContextTargetIDs": deterministic,
        "excludedDeferredOnlyTargetIDs": deferred,
        "unresolvedApplicabilityTargetIDs": [],
        "historicalDev04SmokeBindingUsed": False,
    }


def build_c1a_request() -> dict[str, Any]:
    """Build DEV-01 from the exact accepted C0 plan and bind prompt v0.1.3."""

    binding = load_c0_dev01_binding()
    request = build_development_request(
        SOURCE_UNIT_ID,
        binding["eligibleNodeOperationalTargetIDs"],
        run_id=RUN_ID,
        prompt_path=PROMPT_PATH,
    )
    bound = deepcopy(request)
    bound["prompt"]["version"] = PROMPT_VERSION
    bound["applicabilityPolicyBinding"] = {
        key: value
        for key, value in binding.items()
        if key not in {"artifactRole", "developmentOnly"}
    }
    definitions = list(bound["targetDefinitions"])
    if any(row.get("emission_mode") != "llm_candidate" for row in definitions):
        raise ValueError("C1A request contains a non-direct node target")
    if any(not str(row.get("operational_id", "")).startswith("PUB-N-") for row in definitions):
        raise ValueError("C1A request contains a relation target")
    bound["applicabilityPolicyBinding"]["targetDefinitionsSha256"] = sha256_bytes(
        canonical_json(definitions)
    )
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


def _exposed_targets(schema: Mapping[str, Any], field: str) -> list[str]:
    """Collect operational IDs exposed by const/enum constraints in one schema."""

    values: set[str] = set()

    def walk(value: Any) -> None:
        """Recursively walk schema-valued containers."""

        if isinstance(value, Mapping):
            properties = value.get("properties", {})
            if isinstance(properties, Mapping) and field in properties:
                constrained = properties[field]
                if isinstance(constrained, Mapping):
                    if isinstance(constrained.get("const"), str):
                        values.add(constrained["const"])
                    values.update(
                        item for item in constrained.get("enum", []) if isinstance(item, str)
                    )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
    return sorted(values)


def _build_preflight_record(
    request: Mapping[str, Any],
    binding: Mapping[str, Any],
    provider_input: bytes,
    guide_record: Mapping[str, Any],
    schema: Mapping[str, Any],
    schema_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Record the complete no-network C1A provider-input and compatibility gate."""

    schema_bytes = canonical_json(schema)
    target_definitions = canonical_json(request["targetDefinitions"])
    bounded_projection = canonical_json(provider_input_projection(request))
    base_input = build_provider_input(request)
    node_ids = _exposed_targets(schema, "operationalTargetID")
    relation_ids = _exposed_targets(schema, "operationalRelationID")
    explicit = schema_audit["explicitTypeAudit"]
    refs = schema_audit["refAudit"]
    metrics = schema_audit["metrics"]
    body = build_responses_api_request(
        provider_input,
        model_authorable_schema=schema,
        max_output_tokens=C1A_MAX_OUTPUT_TOKENS,
    )
    if node_ids != sorted(binding["eligibleNodeOperationalTargetIDs"]):
        raise ValueError("specialized schema node target exposure differs from C0")
    if relation_ids:
        raise ValueError("specialized schema exposes relation targets")
    if not schema_audit["compatible"]:
        raise ValueError("C1A schema failed the established provider compatibility audit")
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "offline_provider_input_preflight",
        "developmentOnly": True,
        "networkCalls": 0,
        "developmentID": DEVELOPMENT_ID,
        "sourceUnitID": SOURCE_UNIT_ID,
        "c0PolicyVersion": binding["policyVersion"],
        "c0PolicySha256": binding["policySha256"],
        "c0PlanVersion": binding["planVersion"],
        "c0PlanSha256": binding["planSha256"],
        "eligibleNodeOperationalTargetIDs": node_ids,
        "eligibleNodeOperationalTargetCount": len(node_ids),
        "eligibleNodeOperationalTargetIDsSha256": binding[
            "eligibleNodeOperationalTargetIDsSha256"
        ],
        "deterministicContextTargetsIncluded": 0,
        "deferredOnlyTargetsIncluded": 0,
        "relationTargetsIncluded": len(relation_ids),
        "unresolvedApplicabilityTargets": 0,
        "targetDefinitionCanonicalBytes": len(target_definitions),
        "targetDefinitionsSha256": sha256_bytes(target_definitions),
        "boundedRequestProjectionCanonicalBytes": len(bounded_projection),
        "baseBoundedProviderInputBytes": len(base_input),
        "coordinateGuideVersion": guide_record["coordinateGuideVersion"],
        "coordinateGuideEntryCount": guide_record["entryCount"],
        "coordinateGuideCanonicalBytes": guide_record["canonicalBytes"],
        "coordinateGuideSha256": guide_record["coordinateGuideSha256"],
        "specializedSchemaCanonicalBytes": len(schema_bytes),
        "specializedSchemaSha256": sha256_bytes(schema_bytes),
        "schemaKeywordInventory": schema_audit["keywordInventory"],
        "schemaObjectPropertyCount": metrics["totalObjectPropertyCount"],
        "schemaEnumValueCount": metrics["totalEnumValueCount"],
        "schemaMaximumDepth": metrics["maxNestingDepth"],
        "schemaStringBudget": metrics["aggregateSchemaStringBudget"],
        "schemaRefSiblingCount": refs["refSiblingNodes"],
        "schemaUnresolvedRefCount": refs["unresolvedRefTargets"],
        "schemaConstMissingExplicitTypeCount": explicit[
            "constSchemasLackingExplicitType"
        ],
        "schemaEnumMissingExplicitTypeCount": explicit[
            "enumSchemasLackingExplicitType"
        ],
        "schemaIncompatibleDirectConstraintCount": explicit[
            "directlyConstrainedSchemasLackingCompatibleType"
        ],
        "schemaInvalidAnyOfBranchCount": explicit["invalidAnyOfBranchCount"],
        "providerInputBytes": len(provider_input),
        "providerInputSha256": sha256_bytes(provider_input),
        "promptVersion": PROMPT_VERSION,
        "promptSha256": request["prompt"]["sha256"],
        "historicalAdapterDefaultMaxOutputTokens": MAX_OUTPUT_TOKENS,
        "c1aMaxOutputTokens": C1A_MAX_OUTPUT_TOKENS,
        "outputBudgetOverrideScope": "M2-C1A_only_prospective",
        "outputBudgetIsCapacityNotQuota": True,
        "providerRequestBodySettings": {
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


def _persist_pre_live_artifacts(output_dir: Path) -> dict[str, Any]:
    """Build, audit, and preserve every deterministic pre-live C1A artifact."""

    paths = _artifact_paths(output_dir)
    prompt_diff = build_prompt_semantic_diff()
    binding = load_c0_dev01_binding()
    request = build_c1a_request()
    guide = build_evidence_coordinate_guide(request["sourceUnit"])
    guide_record = coordinate_guide_record(request["sourceUnit"], guide)
    provider_input = build_coordinate_guided_provider_input(request, guide)
    schema = derive_request_specialized_schema(request)
    schema_record = request_specialized_schema_record(request)
    schema_audit = audit_openai_structured_outputs_schema(schema)
    preflight = _build_preflight_record(
        request, binding, provider_input, guide_record, schema, schema_audit
    )
    _write_canonical(paths["request"], request)
    _write_exact(paths["providerInput"], provider_input)
    _write_canonical(paths["promptDiff"], prompt_diff)
    _write_canonical(paths["c0Binding"], binding)
    _write_canonical(paths["coordinateGuide"], guide)
    _write_canonical(paths["coordinateGuideRecord"], guide_record)
    _write_canonical(paths["modelSchema"], schema)
    _write_canonical(paths["modelSchemaRecord"], schema_record)
    _write_canonical(paths["preflight"], preflight)
    return {
        "paths": paths,
        "promptDiff": prompt_diff,
        "binding": binding,
        "request": request,
        "guide": guide,
        "guideRecord": guide_record,
        "providerInput": provider_input,
        "schema": schema,
        "schemaRecord": schema_record,
        "schemaAudit": schema_audit,
        "preflight": preflight,
    }


def _all_finding_codes(validation: Mapping[str, Any]) -> list[str]:
    """Return every distinct validation finding code in deterministic order."""

    codes: set[str] = set()
    for finding in validation.get("globalFindings", []):
        if finding.get("code"):
            codes.add(str(finding["code"]))
    for result_key in ("evidenceResults", "recordResults"):
        for result in validation.get(result_key, []):
            for finding in result.get("findings", []):
                if finding.get("code"):
                    codes.add(str(finding["code"]))
    return sorted(codes)


def _finding_count(validation: Mapping[str, Any], code: str) -> int:
    """Count occurrences of one validation finding code."""

    count = sum(row.get("code") == code for row in validation.get("globalFindings", []))
    for result_key in ("evidenceResults", "recordResults"):
        count += sum(
            finding.get("code") == code
            for result in validation.get(result_key, [])
            for finding in result.get("findings", [])
        )
    return count


def _literal_occurrences(text: str, literal: str) -> list[tuple[int, int]]:
    """Return exact overlapping literal occurrences without changing evidence."""

    if not literal:
        return []
    found: list[tuple[int, int]] = []
    offset = 0
    while True:
        start = text.find(literal, offset)
        if start < 0:
            return found
        found.append((start, start + len(literal)))
        offset = start + 1


def build_descriptive_diagnostics(
    request: Mapping[str, Any],
    payload: Mapping[str, Any],
    validation: Mapping[str, Any],
    usable: Mapping[str, Any],
    provider: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe authentic C1A output without formal accuracy or negative labels."""

    candidates = list(payload.get("candidateNodes", [])) + list(payload.get("candidateEdges", []))
    result_index = {row["recordID"]: row for row in validation.get("recordResults", [])}
    usable_ids = {
        row["candidateID"]
        for key in ("candidateNodes", "candidateEdges")
        for row in usable.get(key, [])
    }
    by_target = Counter(
        row.get("operationalTargetID")
        for row in payload.get("candidateNodes", [])
        if row.get("operationalTargetID")
    )
    definition_index = {
        row["operational_id"]: row for row in request["targetDefinitions"]
    }
    evidence_by_id = {
        row["evidenceSpanID"]: row for row in payload.get("evidenceSpans", [])
    }
    evidence_result_index = {
        row["evidenceSpanID"]: row for row in validation.get("evidenceResults", [])
    }
    text = request["sourceUnit"]["text"]
    document_start = request["sourceUnit"]["startOffsetInDocument"]
    invalid_evidence = []
    for evidence_id, result in sorted(evidence_result_index.items()):
        if result.get("valid") is True:
            continue
        evidence = evidence_by_id[evidence_id]
        occurrences = _literal_occurrences(text, evidence["evidenceText"])
        invalid_evidence.append(
            {
                "evidenceSpanID": evidence_id,
                "evidenceText": evidence["evidenceText"],
                "literalOccurrenceCount": len(occurrences),
                "modelAuthoredUnitOffsets": [
                    evidence["startOffsetInUnit"],
                    evidence["endOffsetInUnit"],
                ],
                "modelAuthoredDocumentOffsets": [
                    evidence["startOffsetInDocument"],
                    evidence["endOffsetInDocument"],
                ],
                "actualLiteralUnitOffsets": [list(span) for span in occurrences],
                "actualLiteralDocumentOffsets": [
                    [document_start + start, document_start + end]
                    for start, end in occurrences
                ],
                "candidateWasRepaired": False,
            }
        )
    candidate_rows = []
    for candidate in candidates:
        result = result_index.get(candidate["candidateID"], {})
        target_id = candidate.get("operationalTargetID", candidate.get("operationalRelationID"))
        candidate_rows.append(
            {
                "candidateID": candidate["candidateID"],
                "operationalTargetID": target_id,
                "ontologyClass": candidate.get("className", candidate.get("relationName")),
                "label": candidate.get("label"),
                "evidenceSpanIDs": list(candidate.get("evidenceSpanIDs", [])),
                "validationStatus": result.get("candidateValidationStatus"),
                "usable": candidate["candidateID"] in usable_ids,
            }
        )
    status_counts = Counter(
        row.get("candidateValidationStatus")
        for row in validation.get("recordResults", [])
        if row.get("candidateValidationStatus")
    )
    output_tokens = provider.get("outputTokens")
    return {
        "diagnosticSchemaVersion": "0.1.0",
        "purpose": "development_only_multitarget_diagnostics_not_formal_evaluation",
        "eligibleNodeTargetCount": len(request["eligibleOperationalTargetIDs"]),
        "targetsWithCandidateNodes": [
            {
                "operationalTargetID": target_id,
                "ontologyClasses": [
                    {"ontologyClassID": item["id"], "className": item["name"]}
                    for item in definition_index[target_id]["formal_classes"]
                ],
                "emittedCandidateCount": count,
            }
            for target_id, count in sorted(by_target.items())
        ],
        "eligibleTargetsWithNoCandidateEmitted": [
            {"operationalTargetID": target_id, "observation": "no candidate emitted"}
            for target_id in request["eligibleOperationalTargetIDs"]
            if target_id not in by_target
        ],
        "candidateTotals": {
            "candidateNodes": len(payload.get("candidateNodes", [])),
            "candidateEdges": len(payload.get("candidateEdges", [])),
            "evidenceSpans": len(payload.get("evidenceSpans", [])),
            "abstentions": len(payload.get("abstentions", [])),
            "deferredRecords": len(payload.get("deferredRecords", [])),
        },
        "validation": {
            "envelopeStatus": validation.get("envelopeStatus"),
            "schemaValidationFailureCount": _finding_count(
                validation, "SCHEMA_VALIDATION_FAILED"
            ),
            "validEvidenceSpanCount": sum(
                row.get("valid") is True for row in validation.get("evidenceResults", [])
            ),
            "evidenceSpanCount": len(validation.get("evidenceResults", [])),
            "candidateStatusCounts": dict(sorted(status_counts.items())),
            "usableCandidateCount": len(usable_ids),
            "findingCodes": _all_finding_codes(validation),
        },
        "candidates": candidate_rows,
        "invalidEvidenceDiagnostics": invalid_evidence,
        "outputCompleteness": {
            "providerStatus": provider.get("status"),
            "incompleteDetails": provider.get("incompleteDetails"),
            "outputTokens": output_tokens,
            "reasoningTokens": provider.get("reasoningTokens"),
            "configuredMaxOutputTokens": C1A_MAX_OUTPUT_TOKENS,
            "configuredMaximumReached": output_tokens == C1A_MAX_OUTPUT_TOKENS,
            "outputBudgetPlausiblyLimiting": (
                isinstance(output_tokens, int)
                and output_tokens >= int(C1A_MAX_OUTPUT_TOKENS * 0.98)
            ),
        },
        "unauthorizedTargetIDs": sorted(
            {
                row.get("operationalTargetID")
                for row in payload.get("candidateNodes", [])
                if row.get("operationalTargetID") not in request["eligibleOperationalTargetIDs"]
            }
        ),
        "postGenerationRepairApplied": False,
        "formalAccuracyClaimed": False,
    }


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
) -> dict[str, Any]:
    """Bind stochastic generation to deterministic policy, guide, and replay hashes."""

    record: dict[str, Any] = {
        "reproducibilitySchemaVersion": "0.1.0",
        "purpose": "publication_multitarget_node_live_development",
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
        "sourceUnitID": SOURCE_UNIT_ID,
        "requestID": request["requestID"],
        "requestInputSha256": request["requestInputSha256"],
        "providerInputSha256": sha256_bytes(state["providerInput"]),
        "promptVersion": PROMPT_VERSION,
        "promptSha256": request["prompt"]["sha256"],
        "c0PolicyVersion": state["binding"]["policyVersion"],
        "c0PolicySha256": state["binding"]["policySha256"],
        "c0PlanVersion": state["binding"]["planVersion"],
        "c0PlanSha256": state["binding"]["planSha256"],
        "eligibleNodeOperationalTargetIDsSha256": state["binding"][
            "eligibleNodeOperationalTargetIDsSha256"
        ],
        "targetDefinitionsSha256": request["applicabilityPolicyBinding"][
            "targetDefinitionsSha256"
        ],
        "coordinateGuideVersion": COORDINATE_GUIDE_VERSION,
        "coordinateGuideSha256": state["guideRecord"]["coordinateGuideSha256"],
        "coordinateGuideEntryCount": state["guideRecord"]["entryCount"],
        "requestSpecializedSchemaVersion": REQUEST_SPECIALIZED_SCHEMA_VERSION,
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
        "maxOutputTokens": C1A_MAX_OUTPUT_TOKENS,
        "toolConfiguration": "none",
        "store": STORE,
        "structuredOutput": {
            "enabled": True,
            "apiField": "text.format",
            "type": "json_schema",
            "strict": True,
            "requestSpecialized": True,
            "nodeOnly": True,
        },
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


def run_multitarget_node_live_extraction(
    api_key: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Make exactly one guarded C1A provider call and replay downstream twice."""

    state = _persist_pre_live_artifacts(output_dir)
    paths = state["paths"]
    kwargs = {} if transport is None else {"transport": transport}
    try:
        raw_output, response, raw_response = call_openai_responses_detailed(
            api_key,
            state["providerInput"],
            model_authorable_schema=state["schema"],
            max_output_tokens=C1A_MAX_OUTPUT_TOKENS,
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
    request = bind_live_response_metadata(
        state["request"], response, max_output_tokens=C1A_MAX_OUTPUT_TOKENS
    )
    if build_coordinate_guided_provider_input(request, state["guide"]) != state["providerInput"]:
        raise ValueError("provider input changed while binding live metadata")
    payload = json.loads(raw_output.decode("utf-8"))
    schema_findings = validate_model_authorable_payload(payload, state["schema"])
    if schema_findings:
        raise ValueError("structured output violated the supplied C1A schema")
    first = _downstream(raw_output, request)
    parsed_payload = first[0].get("parsedDocument", {})
    diagnostics = build_descriptive_diagnostics(
        request, parsed_payload, first[2], first[3], response
    )
    record = _reproducibility_record(
        state, request, response, raw_response, raw_output,
        first[0], first[1], first[2], first[3], diagnostics,
    )
    replay_one = _downstream(raw_output, request)
    replay_two = _downstream(raw_output, request)
    replay_values_one = (
        replay_one[1], canonical_json(replay_one[2]), canonical_json(replay_one[3])
    )
    replay_values_two = (
        replay_two[1], canonical_json(replay_two[2]), canonical_json(replay_two[3])
    )
    if replay_values_one != replay_values_two:
        raise ValueError("C1A deterministic downstream replay differs")
    replay_record = _reproducibility_record(
        state, request, response, raw_response, raw_output,
        replay_one[0], replay_one[1], replay_one[2], replay_one[3], diagnostics,
    )
    if canonical_json(record) != canonical_json(replay_record):
        raise ValueError("C1A reproducibility record replay differs")
    _write_canonical(paths["request"], request)
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
        **state,
        "request": request,
        "providerResponse": response,
        "rawProviderResponse": raw_response,
        "rawModelOutput": raw_output,
        "parserResult": first[0],
        "validation": first[2],
        "usablePipelineOutput": first[3],
        "diagnostics": diagnostics,
        "reproducibility": record,
        "replayByteIdentical": True,
    }


def replay_preserved(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Replay preserved C1A output twice without a provider call."""

    paths = _artifact_paths(output_dir)
    request = json.loads(paths["request"].read_text(encoding="utf-8"))
    raw = paths["rawModelOutput"].read_bytes()
    first = _downstream(raw, request)
    second = _downstream(raw, request)
    values_one = (first[1], canonical_json(first[2]), canonical_json(first[3]))
    values_two = (second[1], canonical_json(second[2]), canonical_json(second[3]))
    if values_one != values_two:
        raise ValueError("preserved C1A downstream replay differs")
    return {
        "byteIdentical": True,
        "parsedCandidateSha256": sha256_bytes(values_one[0]) if values_one[0] else None,
        "validationResultsSha256": sha256_bytes(values_one[1]),
        "usablePipelineOutputSha256": sha256_bytes(values_one[2]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one C1A call, deterministic preparation, or no-network replay."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.prepare_only:
            state = _persist_pre_live_artifacts(args.output_dir)
            result = state["preflight"]
        elif args.replay_only:
            result = replay_preserved(args.output_dir)
        else:
            live = run_multitarget_node_live_extraction(
                load_openai_api_key(), output_dir=args.output_dir
            )
            result = {
                "responseID": live["providerResponse"]["responseID"],
                "parseStatus": live["parserResult"]["parseStatus"],
                "envelopeStatus": live["validation"]["envelopeStatus"],
                "usableCandidates": live["diagnostics"]["validation"][
                    "usableCandidateCount"
                ],
                "rawOutputSha256": live["reproducibility"]["rawModelOutputSha256"],
            }
    except (OSError, KeyError, TypeError, ValueError, OpenAIProviderError) as exc:
        print(f"publication M2-C1A multi-target node extraction failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
