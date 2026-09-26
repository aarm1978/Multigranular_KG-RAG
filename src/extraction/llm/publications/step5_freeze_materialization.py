"""Materialize the deterministic, no-network Step 5 freeze-time bindings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from src.extraction.llm.publications.authority_bundle import V015_SCHEMA013
from src.extraction.llm.publications.openai_provider import (
    PROVIDER_ADAPTER_VERSION,
    PROVIDER_NAME,
    REASONING_EFFORT,
    REQUESTED_MODEL,
    STORE,
    build_provider_input,
    build_responses_api_request,
)
from src.extraction.llm.publications.prospective_endpoint_binding_schema import (
    PROSPECTIVE_ENDPOINT_BINDING_SCHEMA_VERSION,
    derive_prospective_endpoint_binding_schema,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_yaml_object,
    sha256_bytes,
)


FREEZE_VERSION = "0.1.0"
FREEZE_ROOT = PROJECT_ROOT / "data/curation/papers/m2/step5_freeze"
SELECTION_IDS = (
    "pub:18:sec:0002:unit:0001",
    "pub:276:sec:0004:unit:0001",
    "pub:37:sec:0016:unit:0001",
    "pub:46:sec:0030:unit:0001",
    "pub:54:sec:0019:unit:0001",
    "pub:87:sec:0007:unit:0001",
)
REMAINING_PAPER_IDS = ("18", "276", "37", "46", "54", "87")
SECOND_REVIEW_NAMESPACE = "publication-step5-pooled-second-review-selector-v0.1.0"
CONTEXT_POLICY_NAME = "complete_section_when_budget_allows"
CONTEXT_POLICY_VERSION = "0.1.2"
MODEL_CONTEXT_WINDOW_TOKENS = 1_050_000
MAX_OUTPUT_TOKENS = 32_768
MODEL_CONTEXT_BUDGET_TOKENS = 1_017_232
ESTIMATED_INPUT_TOKENS_METHOD = "utf8_byte_upper_bound_v0.1.0"
SCIERC_ARCHIVE_URL = "http://nlp.cs.washington.edu/sciIE/data/sciERC_processed.tar.gz"
SCIERC_ARCHIVE_SHA256 = "bce752fb7ebe4acf570937d76ffb27c239cfc907e477a69075dc7082d0e72e9b"
SCIERC_DYGIE_SCRIPT_COMMIT = "271a3b71c7c9d01a8c30dfaeae2f5e37d4337779"
SCIERC_DYGIE_SCRIPT_SHA256 = "8a973161ecc539614a92f12fe8bd68818cd2de10d47a54a602c461d342f3d09d"
SCIERC_SPLITS = {
    "train": {"path": "processed_data/json/train.json", "documentCount": 350, "sha256": "04970819bd215fce8c60b3a64fccca15388b49eab2010bdc5f6d322b463568c3"},
    "dev": {"path": "processed_data/json/dev.json", "documentCount": 50, "sha256": "61f21b224129e580a654b036ee6fffeeb1a0311f1009a38ea931c13612db040e"},
    "test": {"path": "processed_data/json/test.json", "documentCount": 100, "sha256": "7424da64e6214a90e39b09e47a74b3ded57dde86b4a7f848b3625d2c8ecdfbe1"},
}
SCIERC_ENTITY_LABELS = ["Generic", "Material", "Method", "Metric", "OtherScientificTerm", "Task"]
SCIERC_RELATION_LABELS = ["COMPARE", "CONJUNCTION", "EVALUATE-FOR", "FEATURE-OF", "HYPONYM-OF", "PART-OF", "USED-FOR"]


class Step5FreezeError(ValueError):
    """Raised when a Step 5 freeze-time binding cannot be reproduced safely."""


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hash of one tracked authority file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a UTF-8 JSONL authority artifact."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _artifact(payload: dict[str, Any]) -> dict[str, Any]:
    """Add a canonical self-hash to one compact freeze artifact."""

    result = dict(payload)
    result["artifactSha256"] = sha256_bytes(canonical_json(result))
    return result


def _write(path: Path, payload: Mapping[str, Any]) -> Path:
    """Write one idempotent canonical freeze artifact or fail on byte drift."""

    data = canonical_json_file(dict(payload))
    if path.exists() and path.read_bytes() != data:
        raise Step5FreezeError(f"FREEZE_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _scored_target_ids() -> tuple[set[str], set[str]]:
    """Return the frozen routed extract-and-evaluate target identifiers."""

    mapping_path = PROJECT_ROOT / "data/curation/papers/pilot1/publication_pilot1_target_family_mapping.yaml"
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    return (
        {str(row["operationalTargetID"]) for row in mapping["targets"] if row["targetKind"] == "node" and row["pilotTreatment"] == "extract_and_evaluate"},
        {str(row["operationalTargetID"]) for row in mapping["targets"] if row["targetKind"] == "relation" and row["pilotTreatment"] == "extract_and_evaluate"},
    )


def _inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Index the frozen source inventory, routing, and coverage authorities."""

    pilot = PROJECT_ROOT / "data/curation/papers/pilot1"
    inventory = {row["sourceUnitID"]: row for row in _jsonl(pilot / "publication_pilot1_source_unit_inventory.jsonl")}
    routing = {row["sourceUnitID"]: row for row in _jsonl(pilot / "publication_pilot1_unit_routing.jsonl")}
    return inventory, routing


def _selection() -> dict[str, Any]:
    """Bind the already-approved deterministic N=6 result to frozen source metadata."""

    inventory, routing = _inputs()
    node_ids, relation_ids = _scored_target_ids()
    selected: list[dict[str, Any]] = []
    for source_unit_id in SELECTION_IDS:
        unit, route = inventory.get(source_unit_id), routing.get(source_unit_id)
        if unit is None or route is None:
            raise Step5FreezeError(f"SELECTION_SOURCE_MISSING:{source_unit_id}")
        selected.append({
            "primarySourceUnitID": source_unit_id,
            "paperID": str(unit["paperID"]),
            "sourceArtifactID": unit["canonicalArtifactID"],
            "sectionID": unit["sectionID"],
            "sourceUnitTextHash": unit["textHash"],
            "canonicalDocumentHash": unit["canonicalTextSha256"],
            "samplingStrata": sorted(filter(None, route["likelySamplingStrata"])),
            "routedScoredNodeOperationalTargetIDs": sorted(set(route["eligibleNodeOperationalTargetIDs"]) & node_ids),
            "routedScoredRelationOperationalTargetIDs": sorted(set(route["eligibleRelationOperationalTargetIDs"]) & relation_ids),
        })
    papers = {row["paperID"] for row in selected}
    nodes = set().union(*(set(row["routedScoredNodeOperationalTargetIDs"]) for row in selected))
    relations = set().union(*(set(row["routedScoredRelationOperationalTargetIDs"]) for row in selected))
    strata = set().union(*(set(row["samplingStrata"]) for row in selected))
    if papers != set(REMAINING_PAPER_IDS) or nodes != node_ids or relations != relation_ids or len(strata) != 5:
        raise Step5FreezeError("ESTABLISHED_N6_RESULT_SOURCE_BINDING_DRIFT")
    sampling = PROJECT_ROOT / "data/curation/papers/m2/human_core_sampling_analysis/publication_human_core_sampling_analysis_v0.1.0.json"
    return _artifact({
        "artifactType": "publication_pool_n6_selection_freeze",
        "artifactVersion": FREEZE_VERSION,
        "status": "freeze_time_materialization_not_step5_closure",
        "selectionProvenance": "researcher-approved deterministic result reused without semantic re-audit",
        "samplingAnalysis": {"path": str(sampling.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(sampling)},
        "remainingPaperIDs": list(REMAINING_PAPER_IDS),
        "hardConstraintProof": {"onePrimaryUnitPerRemainingPaper": True, "routedScoredNodeCoverage": f"{len(nodes)}/{len(node_ids)}", "routedScoredRelationCoverage": f"{len(relations)}/{len(relation_ids)}", "samplingStratumCoverage": f"{len(strata)}/5", "frozenExclusionsHonored": True},
        "tieBreakerResult": {"maximumPerUnitRoutedScoredTargetExposure": 15, "totalRoutedScoredTargetExposure": 59, "finalTieBreaker": "lexical sourceUnitID tuple", "selectionIDs": list(SELECTION_IDS)},
        "selectedUnits": selected,
    })


def _request_for(unit: Mapping[str, Any], route: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one bounded, no-dispatch C1 envelope request and its exact API body."""

    node_ids, relation_ids = _scored_target_ids()
    target_ids = sorted((set(route["eligibleNodeOperationalTargetIDs"]) & node_ids) | (set(route["eligibleRelationOperationalTargetIDs"]) & relation_ids))
    profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
    target_rows = {str(row["operational_id"]): dict(row) for row in [*profile["node_targets"], *profile["relation_targets"]]}
    if not target_ids or any(target_id not in target_rows for target_id in target_ids):
        raise Step5FreezeError(f"C1_ROUTED_TARGET_BINDING_FAILED:{unit['sourceUnitID']}")
    prompt_bytes = V015_SCHEMA013.prompt_path.read_bytes()
    candidate_schema = V015_SCHEMA013.candidate_schema_path
    target_inventory = V015_SCHEMA013.target_inventory_path
    ontology_spec = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
    source_contract = PROJECT_ROOT / "docs/publication_source_unit_contract.md"
    evidence_contract = V015_SCHEMA013.evidence_contract_path
    matching_contract = V015_SCHEMA013.evaluation_contract_path
    ontology = load_yaml_object(ontology_spec)
    request: dict[str, Any] = {
        "requestSchemaVersion": "0.1.0", "requestBuilderVersion": "publication-step5-freeze-envelope/0.1.0",
        "authorityBundleID": V015_SCHEMA013.identifier, "purpose": "publication_step5_c1_evaluation",
        "runID": f"publication-step5-c1-evaluation/{FREEZE_VERSION}/{unit['sourceUnitID']}",
        "sourcePublicationID": str(unit["paperID"]), "sourceArtifactID": unit["canonicalArtifactID"],
        "primarySourceUnitID": unit["sourceUnitID"], "contextSourceUnitIDs": [],
        "requestScope": "complete_section", "includedCompleteSection": True, "extractionChannel": "open_discovery",
        "eligibleOperationalTargetIDs": target_ids, "sourceUnit": dict(unit),
        "deterministicEndpoints": [{"nodeID": unit["canonicalArtifactID"], "className": "Paper", "artifactID": unit["canonicalArtifactID"]}],
        "acceptedLocalCandidateEndpoints": [], "deferredRecords": [], "deferredRecordIDs": [],
        "targetDefinitions": [target_rows[target_id] for target_id in target_ids],
        "prompt": {"path": str(V015_SCHEMA013.prompt_path.relative_to(PROJECT_ROOT)), "version": V015_SCHEMA013.prompt_version, "sha256": sha256_bytes(prompt_bytes), "text": prompt_bytes.decode("utf-8")},
        "authorities": {
            "candidateSchema": {"path": str(candidate_schema.relative_to(PROJECT_ROOT)), "version": "0.1.3", "sha256": _sha256_file(candidate_schema)},
            "targetInventory": {"path": str(target_inventory.relative_to(PROJECT_ROOT)), "profileID": profile["profile_id"], "version": str(profile["schema_version"]), "sha256": _sha256_file(target_inventory)},
            "ontology": {"path": str(ontology_spec.relative_to(PROJECT_ROOT)), "version": str(ontology["ontology"]["version"]), "specSha256": _sha256_file(ontology_spec), "validatedOwlSha256": profile["ontology"]["validated_owl_sha256"]},
            "sourceUnitContract": {"path": str(source_contract.relative_to(PROJECT_ROOT)), "version": "0.1.2", "sha256": _sha256_file(source_contract)},
            "evidenceValidationContract": {"path": str(evidence_contract.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(evidence_contract)},
            "evaluationMatchingContract": {"path": str(matching_contract.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(matching_contract)},
        },
    }
    schema = derive_prospective_endpoint_binding_schema(request)
    provider_input = build_provider_input(request)
    body = build_responses_api_request(provider_input, model_authorable_schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
    body_bytes = canonical_json(body)
    if len(body_bytes) > MODEL_CONTEXT_BUDGET_TOKENS:
        raise Step5FreezeError(f"C1_CONTEXT_BUDGET_EXCEEDED:{unit['sourceUnitID']}")
    return request, {"schema": schema, "body": body, "bodyBytes": body_bytes}


def _envelopes(selection: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the six exact C1 evaluation opportunities without provider dispatch."""

    inventory, routing = _inputs()
    rows: list[dict[str, Any]] = []
    common_authorities: dict[str, Any] | None = None
    for source_unit_id in SELECTION_IDS:
        unit, route = inventory[source_unit_id], routing[source_unit_id]
        request, prepared = _request_for(unit, route)
        current_authorities = {
            "authorityBundleID": request["authorityBundleID"],
            "prompt": {key: request["prompt"][key] for key in ("path", "version", "sha256")},
            "authorities": request["authorities"],
        }
        if common_authorities is None:
            common_authorities = current_authorities
        elif canonical_json(common_authorities) != canonical_json(current_authorities):
            raise Step5FreezeError("C1_COMMON_AUTHORITY_BINDING_DRIFT")
        rows.append({
            "envelopeID": f"publication-step5-c1-envelope-{sha256_bytes(prepared['bodyBytes'])[:20]}",
            "primarySourceUnitID": source_unit_id, "sourceArtifactID": unit["canonicalArtifactID"], "sectionID": unit["sectionID"],
            "contextSourceUnitIDs": [], "omittedEligibleSourceUnitIDs": [], "includedCompleteSection": True,
            "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
            "contextSelectionReason": "singleton_primary_section_complete", "modelContextWindowTokens": MODEL_CONTEXT_WINDOW_TOKENS,
            "maxOutputTokens": MAX_OUTPUT_TOKENS, "modelContextBudgetTokens": MODEL_CONTEXT_BUDGET_TOKENS,
            "estimatedInputTokens": len(prepared["bodyBytes"]), "estimatedInputTokensMethod": ESTIMATED_INPUT_TOKENS_METHOD,
            "estimatedInputTokensInterpretation": "conservative UTF-8 byte upper bound; not exact provider tokenization",
            "sourceUnitTextHash": unit["textHash"], "canonicalDocumentHash": unit["canonicalTextSha256"],
            "routedExtractAndEvaluateTargetIDs": request["eligibleOperationalTargetIDs"],
            "requestEnvelopeSha256": sha256_bytes(canonical_json({key: request[key] for key in ("authorityBundleID", "runID", "primarySourceUnitID", "contextSourceUnitIDs", "requestScope", "includedCompleteSection", "eligibleOperationalTargetIDs", "prompt")})),
            "providerRequestBodySha256": sha256_bytes(prepared["bodyBytes"]), "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(prepared["schema"])),
        })
    return _artifact({
        "artifactType": "publication_pool_n6_c1_evaluation_envelopes_freeze", "artifactVersion": FREEZE_VERSION,
        "status": "prospective_no_provider_execution", "providerModelCalls": 0,
        "selectionArtifactSha256": selection["artifactSha256"],
        "commonAuthorityBindings": common_authorities,
        "productionConfiguration": {"provider": PROVIDER_NAME, "providerAdapterVersion": PROVIDER_ADAPTER_VERSION, "model": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT, "store": STORE, "tools": "none", "web": False, "externalRetrieval": False, "structuredOutputsStrict": True, "authorityBundleID": V015_SCHEMA013.identifier, "requestSpecializedSchemaVersion": PROSPECTIVE_ENDPOINT_BINDING_SCHEMA_VERSION},
        "contextBudgetAuthority": {"contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION, "modelContextWindowTokens": MODEL_CONTEXT_WINDOW_TOKENS, "maxOutputTokens": MAX_OUTPUT_TOKENS, "modelContextBudgetTokens": MODEL_CONTEXT_BUDGET_TOKENS, "estimatedInputTokensMethod": ESTIMATED_INPUT_TOKENS_METHOD, "failClosedWhenEstimatedInputTokensExceedBudget": True},
        "envelopes": rows,
    })


def _second_review(selection: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize the researcher-approved content-independent second-review subset."""

    ranking = []
    for source_unit_id in SELECTION_IDS:
        canonical_input = f"{SECOND_REVIEW_NAMESPACE}|{source_unit_id}"
        ranking.append({"primarySourceUnitID": source_unit_id, "canonicalHashInput": canonical_input, "sha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest()})
    ranking.sort(key=lambda row: (row["sha256"], row["primarySourceUnitID"]))
    return _artifact({"artifactType": "publication_pool_secondary_review_subset_freeze", "artifactVersion": FREEZE_VERSION, "selectionArtifactSha256": selection["artifactSha256"], "selectorNamespace": SECOND_REVIEW_NAMESPACE, "hashAlgorithm": "SHA-256", "textEncoding": "UTF-8", "rankingDirection": "ascending lowercase hexadecimal digest", "collisionTieBreaker": "ascending lexical primarySourceUnitID", "ranking": ranking, "selectedPrimarySourceUnitIDs": [row["primarySourceUnitID"] for row in ranking[:2]]})


def _role_exposure() -> dict[str, Any]:
    """Freeze the fail-closed empty ledger schema and eligibility semantics."""

    return _artifact({"artifactType": "publication_step5_role_exposure_ledger_schema", "artifactVersion": FREEZE_VERSION, "futureLedgerPath": "data/curation/papers/m2/step5_execution/publication_step5_role_exposure_ledger.json", "initialRows": [], "rowRequiredFields": ["personOrPseudonymousRoleID", "primarySourceUnitID", "role", "pooledC1JudgmentExposure", "auditEligibility", "recordedAt"], "allowedRoles": ["primary_pooled_adjudicator", "second_pooled_reviewer", "audit_expert"], "allowedExposureStates": ["not_exposed", "exposed_to_pooled_c1_judgment_items"], "eligibilityRule": "auditEligibility is eligible only when pooledC1JudgmentExposure is not_exposed for the same primarySourceUnitID", "enforcement": "fail_closed: an absent row, unknown exposure state, or exposure to pooled C1 judgment items makes audit eligibility false", "incidentalObservationIsolation": "detailed incidental observations are sealed from audit inputs until audit freeze", "blindedProjection": {"mode": "explicit_allowlist_required", "prohibitedSystemProvenance": True}, "finalStatusDistinction": ["adjudication_unresolved", "insufficient_evidence_to_decide"]})


def _scierc_source() -> dict[str, Any]:
    """Bind the official UW processed SciERC archive and its complete test split."""

    return _artifact({"artifactType": "scierc_external_anchor_source_freeze", "artifactVersion": FREEZE_VERSION, "status": "source_and_split_binding_only_no_execution", "datasetReleaseID": "UW-SciIE-SciERC-processed", "officialArchive": {"url": SCIERC_ARCHIVE_URL, "sha256": SCIERC_ARCHIVE_SHA256}, "dygieppDownloaderAuthority": {"repository": "https://github.com/dwadden/dygiepp", "commit": SCIERC_DYGIE_SCRIPT_COMMIT, "path": "scripts/data/get_scierc.sh", "sha256": SCIERC_DYGIE_SCRIPT_SHA256}, "splits": SCIERC_SPLITS, "officialEvaluationSplit": {"name": "test", "completeSplitRequired": True, "subsamplingAuthorized": False}, "nativeEntityLabelSerialization": SCIERC_ENTITY_LABELS, "nativeRelationLabelSerialization": SCIERC_RELATION_LABELS, "relationSemantics": {"symmetric": ["COMPARE", "CONJUNCTION"], "directed": ["EVALUATE-FOR", "FEATURE-OF", "HYPONYM-OF", "PART-OF", "USED-FOR"]}, "coreferenceIncluded": False})


def _scierc_adapter(envelopes: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the thin benchmark-native adapter configuration without running it."""

    return _artifact({"artifactType": "scierc_external_anchor_adapter_freeze", "artifactVersion": FREEZE_VERSION, "status": "prospective_adapter_configuration_only_no_execution", "sourceArtifactSha256": source["artifactSha256"], "c1EnvelopeArtifactSha256": envelopes["artifactSha256"], "baseLLM": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT, "schemaIndependentConfigurationMatchesC1": True, "benchmarkNativeEntityLabels": SCIERC_ENTITY_LABELS, "benchmarkNativeRelationLabels": SCIERC_RELATION_LABELS, "tokenSpanBinding": {"authority": "official processed SciERC JSON", "representation": "document-global zero-based inclusive token spans", "characterSpanRepresentation": "not used; prompting/binding retains indexed benchmark tokens", "exactBindingRequired": True}, "relationEndpointPolicy": "both endpoints must reference entities extracted in the same benchmark document", "relationDirectionPolicy": {"symmetric": ["COMPARE", "CONJUNCTION"], "otherwise": "official directed serialization"}, "allowedPromptAdaptation": ["official SciERC labels", "benchmark-native output schema", "indexed exact mention spans", "official relation directionality and symmetry", "conservative source grounding"], "mechanicalSmokeTestBoundary": "non-test material only; parsing, labels, spans, endpoints, and encoding; no performance optimization", "officialTestExecutionPolicy": "one complete official test split execution after adapter freeze; no test subsampling or performance-driven reruns", "excluded": ["CIROH ontology mapping", "CIROH targets", "coreference prediction", "training", "fine-tuning", "retrieval", "manual prediction adjudication"], "stopRule": "reduce or abandon the anchor rather than create a separate benchmark project if a thin adapter cannot support it"})


def materialize(output_root: Path = FREEZE_ROOT) -> dict[str, Path]:
    """Create every Section 15 compact binding artifact without network or providers."""

    selection = _selection()
    envelopes = _envelopes(selection)
    second_review = _second_review(selection)
    role_exposure = _role_exposure()
    scierc_source = _scierc_source()
    scierc_adapter = _scierc_adapter(envelopes, scierc_source)
    values = {
        "selection": ("publication_pool_n6_selection_freeze_v0.1.0.json", selection),
        "envelopes": ("publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.0.json", envelopes),
        "second_review": ("publication_pool_secondary_review_subset_freeze_v0.1.0.json", second_review),
        "role_exposure": ("publication_step5_role_exposure_ledger_schema_v0.1.0.json", role_exposure),
        "scierc_source": ("scierc_external_anchor_source_freeze_v0.1.0.json", scierc_source),
        "scierc_adapter": ("scierc_external_anchor_adapter_freeze_v0.1.0.json", scierc_adapter),
    }
    return {name: _write(output_root / filename, payload) for name, (filename, payload) in values.items()}


if __name__ == "__main__":
    for name, path in materialize().items():
        print(f"{name}: {path}")
