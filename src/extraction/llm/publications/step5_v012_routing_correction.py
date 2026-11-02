"""Materialize the narrow prospective Step 5 v0.1.2 routing-envelope correction.

The frozen v0.1.1 Step 5 selection and artifacts are read-only historical inputs.
This module reuses the frozen selection rule and context/configuration authorities,
substituting only the accepted v0.1.5 corrected routing authority for envelope target
sets.  It never dispatches a provider request.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from src.extraction.llm.publications.publication_v015_routing_migration import (
    AUTHORITY_OUTPUT_NAME as ROUTING_AUTHORITY_NAME,
    MIGRATION_VERSION,
    OUTPUT_DIRECTORY as ROUTING_OUTPUT_DIRECTORY,
    derive_corrected_routing,
)
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    canonical_json_file,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.step5_freeze_materialization import (
    CONTEXT_POLICY_NAME,
    CONTEXT_POLICY_VERSION,
    ESTIMATED_INPUT_TOKENS_METHOD,
    FREEZE_ROOT,
    MAX_OUTPUT_TOKENS,
    MODEL_CONTEXT_BUDGET_TOKENS,
    MODEL_CONTEXT_WINDOW_TOKENS,
    _inputs,
    _optimized_selection_ids,
    _sha256_file,
    _scierc_adapter,
)


CORRECTION_VERSION = "publication-step5-v015-routing-envelope-correction/0.1.2"
ARTIFACT_VERSION = "0.1.2"
SELECTION_PATH = FREEZE_ROOT / "publication_pool_n6_selection_freeze_v0.1.1.json"
BASE_ENVELOPES_PATH = FREEZE_ROOT / "publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json"
SCIERC_SOURCE_PATH = FREEZE_ROOT / "scierc_external_anchor_source_freeze_v0.1.0.json"
ENVELOPES_OUTPUT_NAME = "publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.2.json"
SCIERC_ADAPTER_OUTPUT_NAME = "scierc_external_anchor_adapter_freeze_v0.1.2.json"
CORRECTION_OUTPUT_NAME = "publication_step5_v015_routing_envelope_correction_v0.1.2.json"


class Step5V012CorrectionError(ValueError):
    """Report an unsafe departure from the frozen v0.1.1 Step 5 authority."""


def _load(path: Path) -> dict[str, Any]:
    """Load one JSON-object authority artifact."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Step5V012CorrectionError(f"expected JSON object: {path}")
    return value


def _artifact(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical artifact with a self-hash."""

    result = dict(payload)
    result["artifactSha256"] = sha256_bytes(canonical_json(result))
    return result


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    """Write one new canonical artifact without permitting divergent replacement."""

    data = canonical_json_file(dict(payload))
    if path.exists() and path.read_bytes() != data:
        raise Step5V012CorrectionError(f"STEP5_V012_ARTIFACT_CONFLICT:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _extract_and_evaluate_target_ids() -> set[str]:
    """Return v0.1.5 direct model-authorable extract-and-evaluate targets."""

    profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
    return {
        str(row["operational_id"])
        for row in [*profile["node_targets"], *profile["relation_targets"]]
        if row.get("production_responsibility") in {"llm", "hybrid"}
        and row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"}
        and row.get("pilot_treatment") == "extract_and_evaluate"
    }


def _validate_selection(selection: Mapping[str, Any], corrected_routing: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Re-run the frozen v0.1.1 minimax rule and require its exact six IDs."""

    inventory, _ = _inputs()
    selected_ids, _ = _optimized_selection_ids(inventory, corrected_routing)
    frozen_ids = [str(row["primarySourceUnitID"]) for row in selection["selectedUnits"]]
    if list(selected_ids) != frozen_ids:
        raise Step5V012CorrectionError("STEP5_V012_SELECTION_CHANGED")
    if selection["artifactSha256"] != _load(SELECTION_PATH)["artifactSha256"]:
        raise Step5V012CorrectionError("STEP5_V012_SELECTION_ARTIFACT_DRIFT")
    return frozen_ids


def _context_units(unit: Mapping[str, Any], inventory: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Apply the unchanged complete-section context selection policy."""

    return [
        dict(candidate)
        for candidate in sorted(
            (
                candidate
                for candidate in inventory.values()
                if candidate["sectionID"] == unit["sectionID"]
                and candidate["sourceUnitID"] != unit["sourceUnitID"]
                and candidate.get("eligibility") == "eligible"
            ),
            key=lambda candidate: str(candidate["sourceUnitID"]),
        )
    ]


def _request_for(unit: Mapping[str, Any], route: Mapping[str, Any], context_units: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build one corrected no-dispatch C1 envelope request using unchanged mechanics."""

    target_ids = sorted(
        (set(route["eligibleNodeOperationalTargetIDs"]) | set(route["eligibleRelationOperationalTargetIDs"]))
        & _extract_and_evaluate_target_ids()
    )
    profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
    target_rows = {str(row["operational_id"]): dict(row) for row in [*profile["node_targets"], *profile["relation_targets"]]}
    if not target_ids or any(target_id not in target_rows for target_id in target_ids):
        raise Step5V012CorrectionError(f"STEP5_V012_ROUTED_TARGET_BINDING_FAILED:{unit['sourceUnitID']}")
    prompt_bytes = V015_SCHEMA013.prompt_path.read_bytes()
    candidate_schema = V015_SCHEMA013.candidate_schema_path
    ontology_spec = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
    source_contract = PROJECT_ROOT / "docs/publication_source_unit_contract.md"
    ontology = load_yaml_object(ontology_spec)
    request: dict[str, Any] = {
        "requestSchemaVersion": "0.1.0", "requestBuilderVersion": "publication-step5-freeze-envelope/0.1.0",
        "authorityBundleID": V015_SCHEMA013.identifier, "purpose": "publication_step5_c1_evaluation",
        "runID": f"publication-step5-c1-evaluation/{ARTIFACT_VERSION}/{unit['sourceUnitID']}",
        "sourcePublicationID": str(unit["paperID"]), "sourceArtifactID": unit["canonicalArtifactID"],
        "primarySourceUnitID": unit["sourceUnitID"], "contextSourceUnitIDs": [str(row["sourceUnitID"]) for row in context_units], "contextUnits": [dict(row) for row in context_units],
        "requestScope": "complete_section", "includedCompleteSection": True, "extractionChannel": "open_discovery",
        "eligibleOperationalTargetIDs": target_ids, "sourceUnit": dict(unit),
        "deterministicEndpoints": [{"nodeID": unit["canonicalArtifactID"], "className": "Paper", "artifactID": unit["canonicalArtifactID"]}],
        "acceptedLocalCandidateEndpoints": [], "deferredRecords": [], "deferredRecordIDs": [],
        "targetDefinitions": [target_rows[target_id] for target_id in target_ids],
        "prompt": {"path": str(V015_SCHEMA013.prompt_path.relative_to(PROJECT_ROOT)), "version": V015_SCHEMA013.prompt_version, "sha256": sha256_bytes(prompt_bytes), "text": prompt_bytes.decode("utf-8")},
        "authorities": {
            "candidateSchema": {"path": str(candidate_schema.relative_to(PROJECT_ROOT)), "version": "0.1.3", "sha256": _sha256_file(candidate_schema)},
            "targetInventory": {"path": str(V015_SCHEMA013.target_inventory_path.relative_to(PROJECT_ROOT)), "profileID": profile["profile_id"], "version": str(profile["schema_version"]), "sha256": _sha256_file(V015_SCHEMA013.target_inventory_path)},
            "ontology": {"path": str(ontology_spec.relative_to(PROJECT_ROOT)), "version": str(ontology["ontology"]["version"]), "specSha256": _sha256_file(ontology_spec), "validatedOwlSha256": profile["ontology"]["validated_owl_sha256"]},
            "sourceUnitContract": {"path": str(source_contract.relative_to(PROJECT_ROOT)), "version": "0.1.2", "sha256": _sha256_file(source_contract)},
            "evidenceValidationContract": {"path": str(V015_SCHEMA013.evidence_contract_path.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(V015_SCHEMA013.evidence_contract_path)},
            "evaluationMatchingContract": {"path": str(V015_SCHEMA013.evaluation_contract_path.relative_to(PROJECT_ROOT)), "sha256": _sha256_file(V015_SCHEMA013.evaluation_contract_path)},
        },
    }
    schema = derive_prospective_endpoint_binding_schema(request)
    body = build_responses_api_request(build_provider_input(request), model_authorable_schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
    body_bytes = canonical_json(body)
    if len(body_bytes) > MODEL_CONTEXT_BUDGET_TOKENS:
        raise Step5V012CorrectionError(f"STEP5_V012_CONTEXT_BUDGET_EXCEEDED:{unit['sourceUnitID']}")
    return request, {"schema": schema, "bodyBytes": body_bytes}


def build_envelopes() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the corrected envelopes and a binding record without modifying v0.1.1."""

    selection = _load(SELECTION_PATH)
    base_envelopes = _load(BASE_ENVELOPES_PATH)
    corrected_rows, routing_authority = derive_corrected_routing()
    corrected_routing = {str(row["sourceUnitID"]): row for row in corrected_rows}
    selected_ids = _validate_selection(selection, corrected_routing)
    inventory, _ = _inputs()
    base_by_id = {str(row["primarySourceUnitID"]): row for row in base_envelopes["envelopes"]}
    rows: list[dict[str, Any]] = []
    common_authorities: dict[str, Any] | None = None
    deltas: dict[str, dict[str, list[str]]] = {}
    for source_unit_id in selected_ids:
        request, prepared = _request_for(inventory[source_unit_id], corrected_routing[source_unit_id], _context_units(inventory[source_unit_id], inventory))
        current_authorities = {"authorityBundleID": request["authorityBundleID"], "prompt": {key: request["prompt"][key] for key in ("path", "version", "sha256")}, "authorities": request["authorities"]}
        if common_authorities is None:
            common_authorities = current_authorities
        elif canonical_json(common_authorities) != canonical_json(current_authorities):
            raise Step5V012CorrectionError("STEP5_V012_COMMON_AUTHORITY_BINDING_DRIFT")
        old_targets = set(base_by_id[source_unit_id]["routedExtractAndEvaluateTargetIDs"])
        new_targets = set(request["eligibleOperationalTargetIDs"])
        removed = sorted(old_targets - new_targets)
        added = sorted(new_targets - old_targets)
        if removed:
            raise Step5V012CorrectionError(f"STEP5_V012_UNEXPECTED_TARGET_REMOVAL:{source_unit_id}")
        deltas[source_unit_id] = {"addedTargetIDs": added, "removedTargetIDs": removed}
        context_units = _context_units(inventory[source_unit_id], inventory)
        rows.append({
            "envelopeID": f"publication-step5-c1-envelope-{sha256_bytes(prepared['bodyBytes'])[:20]}",
            "primarySourceUnitID": source_unit_id, "sourceArtifactID": inventory[source_unit_id]["canonicalArtifactID"], "sectionID": inventory[source_unit_id]["sectionID"],
            "contextSourceUnitIDs": list(request["contextSourceUnitIDs"]), "omittedEligibleSourceUnitIDs": [], "includedCompleteSection": True,
            "contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION,
            "contextSelectionReason": "singleton_primary_section_complete" if not context_units else "complete_section_all_eligible_units",
            "modelContextWindowTokens": MODEL_CONTEXT_WINDOW_TOKENS, "maxOutputTokens": MAX_OUTPUT_TOKENS, "modelContextBudgetTokens": MODEL_CONTEXT_BUDGET_TOKENS,
            "estimatedInputTokens": len(prepared["bodyBytes"]), "estimatedInputTokensMethod": ESTIMATED_INPUT_TOKENS_METHOD,
            "estimatedInputTokensInterpretation": "conservative UTF-8 byte upper bound; not exact provider tokenization",
            "sourceUnitTextHash": inventory[source_unit_id]["textHash"], "canonicalDocumentHash": inventory[source_unit_id]["canonicalTextSha256"],
            "routedExtractAndEvaluateTargetIDs": request["eligibleOperationalTargetIDs"],
            "requestEnvelopeSha256": sha256_bytes(canonical_json({key: request[key] for key in ("authorityBundleID", "runID", "primarySourceUnitID", "contextSourceUnitIDs", "requestScope", "includedCompleteSection", "eligibleOperationalTargetIDs", "prompt")})),
            "providerRequestBodySha256": sha256_bytes(prepared["bodyBytes"]), "modelAuthorableSchemaSha256": sha256_bytes(canonical_json(prepared["schema"])),
        })
    envelopes = _artifact({
        "artifactType": "publication_pool_n6_c1_evaluation_envelopes_freeze", "artifactVersion": ARTIFACT_VERSION,
        "status": "prospective_v015_routing_corrected_no_provider_execution", "providerModelCalls": 0,
        "selectionArtifactSha256": selection["artifactSha256"], "baseEnvelopeArtifactSha256": base_envelopes["artifactSha256"],
        "correctedRoutingAuthority": {"path": str((ROUTING_OUTPUT_DIRECTORY / ROUTING_AUTHORITY_NAME).relative_to(PROJECT_ROOT)), "sha256": routing_authority["artifactSha256"], "routingSha256": routing_authority["routing"]["sha256"], "routingVersion": MIGRATION_VERSION},
        "commonAuthorityBindings": common_authorities,
        "productionConfiguration": {"provider": PROVIDER_NAME, "providerAdapterVersion": PROVIDER_ADAPTER_VERSION, "model": REQUESTED_MODEL, "reasoningEffort": REASONING_EFFORT, "store": STORE, "tools": "none", "web": False, "externalRetrieval": False, "structuredOutputsStrict": True, "authorityBundleID": V015_SCHEMA013.identifier, "requestSpecializedSchemaVersion": PROSPECTIVE_ENDPOINT_BINDING_SCHEMA_VERSION},
        "contextBudgetAuthority": {"contextPolicyName": CONTEXT_POLICY_NAME, "contextPolicyVersion": CONTEXT_POLICY_VERSION, "modelContextWindowTokens": MODEL_CONTEXT_WINDOW_TOKENS, "maxOutputTokens": MAX_OUTPUT_TOKENS, "modelContextBudgetTokens": MODEL_CONTEXT_BUDGET_TOKENS, "estimatedInputTokensMethod": ESTIMATED_INPUT_TOKENS_METHOD, "failClosedWhenEstimatedInputTokensExceedBudget": True},
        "selectionIDsUnchanged": selected_ids, "envelopeTargetDeltas": deltas, "envelopes": rows,
    })
    binding = _artifact({
        "artifactType": "publication_step5_v015_routing_envelope_correction", "artifactVersion": ARTIFACT_VERSION,
        "status": "prospective_step5_envelope_correction_no_provider_execution", "providerModelCalls": 0,
        "baseStep5EnvelopeArtifact": {"path": str(BASE_ENVELOPES_PATH.relative_to(PROJECT_ROOT)), "sha256": base_envelopes["artifactSha256"], "artifactVersion": "0.1.1"},
        "selectionArtifact": {"path": str(SELECTION_PATH.relative_to(PROJECT_ROOT)), "sha256": selection["artifactSha256"], "unchanged": True},
        "correctedRoutingAuthority": dict(envelopes["correctedRoutingAuthority"]),
        "correctedEnvelopeArtifact": {"path": str((FREEZE_ROOT / ENVELOPES_OUTPUT_NAME).relative_to(PROJECT_ROOT)), "sha256": envelopes["artifactSha256"]},
        "selectionIDsUnchanged": selected_ids, "envelopeTargetDeltas": deltas,
        "unchangedMethodology": {"contextPolicy": f"{CONTEXT_POLICY_NAME}/{CONTEXT_POLICY_VERSION}", "authorityBundleID": V015_SCHEMA013.identifier, "model": REQUESTED_MODEL, "promptVersion": V015_SCHEMA013.prompt_version, "productionAcceptanceModified": False, "sciercSemanticsModified": False},
    })
    return envelopes, binding


def build_scierc_adapter(envelopes: Mapping[str, Any]) -> dict[str, Any]:
    """Rebind only the mechanically dependent SciERC adapter envelope hash."""

    source = _load(SCIERC_SOURCE_PATH)
    adapter = _scierc_adapter(envelopes, source)
    payload = deepcopy(adapter)
    payload.pop("artifactSha256")
    payload["artifactVersion"] = ARTIFACT_VERSION
    payload["correctionProvenance"] = {"baseArtifactPath": str((FREEZE_ROOT / "scierc_external_anchor_adapter_freeze_v0.1.1.json").relative_to(PROJECT_ROOT)), "baseEnvelopeArtifactSha256": _load(BASE_ENVELOPES_PATH)["artifactSha256"], "correctedEnvelopeArtifactSha256": envelopes["artifactSha256"], "semanticsAndConfigurationUnchanged": True}
    return _artifact(payload)


def materialize(output_root: Path = FREEZE_ROOT) -> dict[str, Path]:
    """Write only new v0.1.2 prospective replacement bindings."""

    envelopes, binding = build_envelopes()
    adapter = build_scierc_adapter(envelopes)
    values = {
        "envelopes": (ENVELOPES_OUTPUT_NAME, envelopes),
        "binding": (CORRECTION_OUTPUT_NAME, binding),
        "scierc_adapter": (SCIERC_ADAPTER_OUTPUT_NAME, adapter),
    }
    for filename, payload in values.values():
        _write(output_root / filename, payload)
    return {name: output_root / filename for name, (filename, _) in values.items()}


def main(argv: Sequence[str] | None = None) -> int:
    """Materialize the no-network Step 5 v0.1.2 correction."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=FREEZE_ROOT)
    args = parser.parse_args(argv)
    for name, path in materialize(args.output_root).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
