"""Build the deterministic no-call Publication relation-gate run plan.

The record is prospective.  It derives the 26-relation universe and all request/schema
measurements from current frozen authorities, makes no provider call, and does not
alter any historical development artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from src.extraction.llm.publications.evidence_coordinate_guide import (
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.model_authorable_schema import (
    audit_openai_structured_outputs_schema,
)
from src.extraction.llm.publications.openai_provider import provider_input_projection
from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    TARGET_INVENTORY_PATH,
    canonical_json,
    canonical_json_file,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    DEV_IDS,
    PROMPT_VERSION,
    build_full_semantic_request,
    load_c0_bindings,
    model_authorable_relation_target_ids,
)
from src.extraction.llm.publications.run_publication_multitarget_node_development import (
    _exposed_targets,
)
from src.extraction.llm.publications.trusted_evidence_metadata_schema import (
    TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION,
    derive_trusted_evidence_metadata_schema,
)


GATE_PLAN_VERSION = "publication-relation-development-gate/0.1.0"
DEFAULT_PLAN_PATH = (
    PROJECT_ROOT
    / "data/curation/papers/m2/relation_development_gate/"
    "publication_relation_development_gate_plan.json"
)
CLARIFIED_SOURCE_LOCAL_RELATION_IDS = (
    "PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE",
    "PUB-R-C-P24-MENTIONSDATASET",
    "PUB-R-C-P32-REFERENCESREPOSITORY",
    "PUB-R-C-P33-HASCODEREPOSITORY",
)


def _relation_rows() -> list[dict[str, Any]]:
    """Return exact profile rows for the current 26-relation universe."""

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    indexed = {
        str(row["operational_id"]): row for row in profile["relation_targets"]
    }
    return [indexed[target_id] for target_id in model_authorable_relation_target_ids()]


def _unit_plan(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Audit one combined request without persisting provider input or calling a model."""

    request = build_full_semantic_request(binding)
    guide = build_evidence_coordinate_guide(request["sourceUnit"])
    provider_input = build_coordinate_guided_provider_input(request, guide)
    schema = derive_trusted_evidence_metadata_schema(request)
    audit = audit_openai_structured_outputs_schema(schema)
    nodes = _exposed_targets(schema, "operationalTargetID")
    relations = _exposed_targets(schema, "operationalRelationID")
    if len(nodes) != 40 or relations != sorted(model_authorable_relation_target_ids()):
        raise ValueError("combined DEV schema does not expose the frozen target universe")
    if not audit["compatible"]:
        raise ValueError("combined DEV schema failed provider compatibility")
    metrics = audit["metrics"]
    return {
        "developmentID": binding["developmentID"],
        "sourceUnitID": binding["sourceUnitID"],
        "sectionRole": binding["sectionRole"],
        "eligibleNodeTargetCount": len(nodes),
        "eligibleRelationTargetCount": len(relations),
        "eligibleRelationOperationalTargetIDs": relations,
        "deterministicEndpointRoutes": request["deterministicEndpoints"],
        "candidateNodeEndpointsAllowed": True,
        "acceptedLocalCandidateEndpointsAllowed": True,
        "allApplicableRelationsEndpointBindable": True,
        "requestInputSha256": request["requestInputSha256"],
        "providerSchemaSha256": sha256_bytes(canonical_json(schema)),
        "providerSchemaCanonicalBytes": len(canonical_json(schema)),
        "boundedRequestCanonicalBytes": len(
            canonical_json(provider_input_projection(request))
        ),
        "providerInputBytes": len(provider_input),
        "providerInputSha256": sha256_bytes(provider_input),
        "providerSchemaMetrics": metrics,
        "providerCompatibility": "PASS",
    }


def build_relation_development_gate_plan() -> dict[str, Any]:
    """Return the canonical prospective ten-unit full-semantic run plan."""

    relation_rows = _relation_rows()
    units = [_unit_plan(binding) for binding in load_c0_bindings()]
    relation_coverage = [
        {
            "operationalRelationID": row["operational_id"],
            "ontologyRelationIDs": list(row["ontology_ids"]),
            "relationNames": [
                formal["name"] for formal in row["formal_relations"]
            ],
            "operationalSignatures": row["operational_signatures"],
            "structuralFixtureCoverage": True,
            "applicableDevelopmentIDs": list(DEV_IDS),
            "endpointBindingReady": True,
            "authenticProviderCoverageBeforeRun": False,
            "authenticProviderCoverageAfterThisNoCallGate": False,
            "futureTenUnitCoverageOpportunity": True,
        }
        for row in relation_rows
    ]
    clarified = [
        {
            "operationalRelationID": target_id,
            "sourceLocalCandidatePath": {
                "supported": True,
                "identityScope": "source_local",
                "artifactScope": "source_artifact",
                "relationScope": "intra_source",
            },
            "exactOrResolverExternalPath": {
                "supported": True,
                "artifactScope": "external_artifact",
                "relationScope": "inter_source",
            },
        }
        for target_id in CLARIFIED_SOURCE_LOCAL_RELATION_IDS
    ]
    record: dict[str, Any] = {
        "planVersion": GATE_PLAN_VERSION,
        "artifactRole": "prospective_full_semantic_devset0_run_plan",
        "status": "FRESH_DEVSET0_FULL_SEMANTIC_RUN_READY",
        "developmentOnly": True,
        "providerCalls": 0,
        "modelCallMade": False,
        "costUSD": 0,
        "ontologyVersion": "0.1.4",
        "requestSpecializedSchemaVersion": (
            TRUSTED_EVIDENCE_METADATA_SCHEMA_VERSION
        ),
        "promptVersion": PROMPT_VERSION,
        "promptSemanticsChanged": False,
        "relationScopeRule": (
            "V8 derives intra_source or inter_source from resolved endpoint "
            "artifact ownership; ontology relation type does not fix assertion scope"
        ),
        "nodePolicy": {
            "candidateAuthorableNodeTargetCount": 46,
            "directOpenDiscoveryTargetCount": 40,
            "deterministicContextTargetCount": 4,
            "deferredResolutionTargetCount": 2,
        },
        "modelAuthorableRelationTargetCount": len(relation_rows),
        "modelAuthorableRelationOperationalTargetIDs": (
            model_authorable_relation_target_ids()
        ),
        "genericMentionsModelAuthorable": False,
        "clarifiedEndpointPaths": clarified,
        "relationCoverage": relation_coverage,
        "runContract": {
            "developmentIDs": list(DEV_IDS),
            "oneCombinedRequestPerUnit": True,
            "trustedSectionTitleBoundBeforeGeneration": True,
            "explicitEndpointReferencesOnly": True,
            "parserChanged": False,
            "validatorChanged": False,
            "postGenerationCorrection": False,
            "genericMentionsStage": "post_acceptance_only",
            "preserveRawResponseAndReproducibility": True,
            "goldOrCalibrationUsedForPromptTuning": False,
        },
        "precommittedReviewCriteria": {
            "processingStructuralFailure": [
                "API failure",
                "invalid JSON",
                "provider schema failure",
                "authority mismatch",
                "endpoint lifecycle failure",
            ],
            "evidenceFailure": [
                "non-literal evidence",
                "invalid offsets",
                "missing relation-specific evidence",
            ],
            "nodeExtractionIssue": [
                "available target with semantically evident entity omitted"
            ],
            "relationExtractionIssue": [
                "supported relation omitted",
                "unsupported relation asserted",
                "stronger role confused with mention/reference",
                "invalid endpoints",
            ],
            "expectedAbstention": "no relation is forced without sufficient evidence",
            "pipelineDerivedGenericConnectivity": (
                "evaluated separately after accepted semantic projection"
            ),
        },
        "futureProductionAcceptanceBoundary": (
            "a separately frozen automated production acceptance policy will be "
            "required after the extraction evaluation gate; it is not defined here"
        ),
        "units": units,
    }
    record["planSha256"] = sha256_bytes(canonical_json(record))
    return record


def write_relation_development_gate_plan(
    path: Path = DEFAULT_PLAN_PATH,
) -> dict[str, Any]:
    """Write the deterministic prospective plan with one trailing line feed."""

    plan = build_relation_development_gate_plan()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(plan))
    return plan


if __name__ == "__main__":
    written = write_relation_development_gate_plan()
    print(canonical_json(written).decode("utf-8"))
