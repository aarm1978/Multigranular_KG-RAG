"""Derive the approved M2-C0 Publication development applicability policy.

This module uses only frozen target metadata and trusted source-unit routing metadata.
It deliberately does not read or classify source-unit prose, use lexical triggers, or
perform network/model calls. The resulting policy is approved for prospective development
use, but is not a final Pilot-1 production policy.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    DEVELOPMENT_INVENTORY_PATH,
    DEVELOPMENT_MANIFEST_PATH,
    ONTOLOGY_SPEC_PATH,
    PROJECT_ROOT,
    SOURCE_UNIT_CONTRACT_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    canonical_json_file,
    load_development_inventory,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)


POLICY_VERSION = "publication-node-target-applicability-0.1.0"
AUDIT_VERSION = "publication-node-target-applicability-audit-0.1.0"
PLAN_VERSION = "publication-devset0-node-request-plan-0.1.0"
POLICY_STATUS = "approved_for_development"
EXPECTED_CANDIDATE_AUTHORABLE_NODE_COUNT = 46

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c0"
REQUEST_BUILDER_PATH = PROJECT_ROOT / "src/extraction/llm/publications/request_builder.py"
SOURCE_UNIT_BUILDER_PATH = PROJECT_ROOT / "src/extraction/llm/publications/source_units.py"
BLOCK_A_ROUTING_PATH = PROJECT_ROOT / "src/extraction/llm/publications/publication_pilot1_block_a.py"

RULE_SOURCE_ELIGIBLE = "C0-NODE-SOURCE-001"
RULE_OPEN_UNIVERSAL = "C0-NODE-OPEN-001"
RULE_NO_SECTION_NARROWING = "C0-NODE-OPEN-002"
RULE_DETERMINISTIC_BOUND = "C0-NODE-CONTEXT-001"
RULE_DETERMINISTIC_ABSENT = "C0-NODE-CONTEXT-002"
RULE_DEFERRED_ONLY = "C0-NODE-DEFERRED-001"
RULE_DEFERRED_EXACT = "C0-NODE-DEFERRED-002"
RULE_NON_AUTHORABLE = "C0-NODE-SCOPE-001"
POLICY_DECISION_UNIVERSAL_OPEN = "C0-POLICY-DECISION-001"


def _authority_inputs() -> list[dict[str, str]]:
    """Return the exact frozen inputs inspected by the policy derivation."""

    roles = {
        ONTOLOGY_SPEC_PATH: "ontology_class_authority",
        TARGET_INVENTORY_PATH: "publication_operational_target_authority",
        CANDIDATE_SCHEMA_PATH: "candidate_authorability_and_lifecycle_authority",
        SOURCE_UNIT_CONTRACT_PATH: "source_unit_and_routing_metadata_contract",
        DEVELOPMENT_INVENTORY_PATH: "devset0_materialized_source_unit_authority",
        DEVELOPMENT_MANIFEST_PATH: "approved_devset0_identity_authority",
        REQUEST_BUILDER_PATH: "development_request_channel_and_binding_contract",
        SOURCE_UNIT_BUILDER_PATH: "source_unit_metadata_materialization_implementation",
        BLOCK_A_ROUTING_PATH: "existing_channel_and_deferred_routing_rule_implementation",
    }
    return [
        {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "role": role,
            "sha256": sha256_bytes(path.read_bytes()),
        }
        for path, role in sorted(roles.items(), key=lambda item: str(item[0]))
    ]


def _candidate_authorable_nodes(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Select the frozen 46 node targets that can appear in candidate processing."""

    rows = [
        dict(row)
        for row in profile["node_targets"]
        if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"}
        or "link_existing" in row.get("allowed_actions", [])
    ]
    rows.sort(key=lambda row: row["operational_id"])
    if len(rows) != EXPECTED_CANDIDATE_AUTHORABLE_NODE_COUNT:
        raise ValueError(
            "frozen candidate-authorable node count drifted from the reviewed M2-C0 universe"
        )
    if any(not row.get("direct_instantiation") for row in rows):
        raise ValueError("candidate-authorable node universe contains an abstract target")
    return rows


def _rules() -> list[dict[str, Any]]:
    """Return stable answer-independent applicability rules with authority citations."""

    return [
        {
            "ruleID": RULE_SOURCE_ELIGIBLE,
            "decision": "permit_policy_evaluation",
            "when": {
                "sourceUnit.eligibility": "eligible",
                "sourceUnit.requestEligible": True,
                "sourceUnit.validationResults.valid": True,
            },
            "authorityFields": [
                "source-unit contract: eligibility",
                "source-unit contract: requestEligible",
                "source-unit contract: validationResults.valid",
                "request_builder.build_development_request",
            ],
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_OPEN_UNIVERSAL,
            "ruleNature": "researcher_approved_extraction_policy_consequence",
            "policyDecisionID": POLICY_DECISION_UNIVERSAL_OPEN,
            "decision": "include_in_open_discovery",
            "when": {
                "target.emission_mode": "llm_candidate",
                "target.pilot_treatment": ["extract_and_evaluate", "extract_and_monitor"],
                "target.direct_instantiation": True,
                "profile.source_scope": "publications",
            },
            "authorityFields": [
                "publication_target_inventory.source_scope",
                "node_targets[].emission_mode",
                "node_targets[].pilot_treatment",
                "node_targets[].direct_instantiation",
            ],
            "rationale": (
                "The cited frozen fields establish the target scope and reveal no binding "
                "narrower restriction. The universal-eligibility consequence is imposed by "
                "the researcher-approved extraction-policy decision, not by a frozen ontology "
                "axiom or literal target-inventory rule."
            ),
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_NO_SECTION_NARROWING,
            "decision": "do_not_narrow_by_section_role",
            "when": {"target.emission_mode": "llm_candidate"},
            "authorityFields": [
                "publication_target_inventory.routing_categories[].typical_region",
                "sourceUnit.sectionRole",
            ],
            "rationale": (
                "routing_categories.typical_region is descriptive ('typical'), not a frozen "
                "exclusive applicability constraint; sectionRole cannot exclude a target."
            ),
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_DETERMINISTIC_BOUND,
            "decision": "include_as_link_existing_context_only",
            "when": {
                "target.emission_mode": "deterministic_context",
                "target.allowed_actions contains": "link_existing",
                "sourceUnit.deterministicNodeRefs": "contains exact resolvable endpoint bound to this operational target",
            },
            "authorityFields": [
                "node_targets[].emission_mode",
                "node_targets[].allowed_actions",
                "node_targets[].pilot_treatment",
                "sourceUnit.deterministicNodeRefs",
            ],
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_DETERMINISTIC_ABSENT,
            "decision": "exclude_from_request",
            "when": {
                "target.emission_mode": "deterministic_context",
                "matching exact deterministic endpoint binding": "absent",
            },
            "authorityFields": [
                "node_targets[].emission_mode",
                "sourceUnit.deterministicNodeRefs",
            ],
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_DEFERRED_ONLY,
            "decision": "exclude_from_open_discovery",
            "when": {
                "target.emission_mode": "resolver_mediated_candidate",
                "target.pilot_treatment": "deferred_resolution",
            },
            "authorityFields": [
                "node_targets[].emission_mode",
                "node_targets[].pilot_treatment",
                "request.extractionChannel",
            ],
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_DEFERRED_EXACT,
            "decision": "include_in_deferred_resolution_only",
            "when": {
                "request.extractionChannel": "deferred_resolution",
                "sourceUnit.deferredRecordRefs": "contains exact trusted deferred record",
                "deferred record operational target": "equals requested target",
            },
            "authorityFields": [
                "sourceUnit.deferredRecordRefs",
                "request.deferredRecordIDs",
                "request.deferredRecords",
                "request.extractionChannel",
                "publication_pilot1_block_a.DEFERRED_ROUTE_UNAVAILABLE_REASON",
            ],
            "semanticContentUsed": False,
        },
        {
            "ruleID": RULE_NON_AUTHORABLE,
            "decision": "exclude_from_node_candidate_policy",
            "when": {
                "target": "not in candidate-authorable node universe or not directly instantiable"
            },
            "authorityFields": [
                "node_targets[].emission_mode",
                "node_targets[].allowed_actions",
                "node_targets[].direct_instantiation",
                "candidate schema $defs.candidateNode",
            ],
            "semanticContentUsed": False,
        },
    ]


def _hash_record(record: Mapping[str, Any], hash_field: str) -> str:
    """Hash a canonical record projection that omits its own hash field."""

    projection = dict(record)
    projection.pop(hash_field, None)
    return sha256_bytes(canonical_json(projection))


def derive_policy() -> dict[str, Any]:
    """Derive the approved deterministic policy from authorities plus one policy decision."""

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    nodes = _candidate_authorable_nodes(profile)
    authority_inputs = _authority_inputs()
    counts = Counter(row["emission_mode"] for row in nodes)
    policy: dict[str, Any] = {
        "policyVersion": POLICY_VERSION,
        "status": POLICY_STATUS,
        "scope": {
            "artifactFamily": "scientific_publications",
            "targetKind": "node",
            "relationsIncluded": False,
            "developmentSet": "DEV-SET-0",
        },
        "methodologicalBoundary": {
            "answerInformedTargetSelectionAllowed": False,
            "sourceProseInspectedForApplicability": False,
            "semanticClassifierAllowed": False,
            "keywordOrLexicalTriggerAllowed": False,
            "embeddingAllowed": False,
            "llmAllowed": False,
            "networkAllowed": False,
            "routingDoesNotAssertPresence": True,
            "semanticPrescreeningRequired": False,
            "semanticPrescreeningAuthorized": False,
        },
        "statusSemantics": {
            "DETERMINISTICALLY_APPLICABLE": "Applicable only when an exact trusted non-semantic binding named by its rule exists.",
            "DETERMINISTICALLY_EXCLUDED": "Excluded for the evaluated request because an explicit structural/channel prerequisite is absent.",
            "UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL": "Eligible throughout the Publication source scope in its named channel under the researcher-approved coverage-preserving extraction-policy decision.",
            "DEFERRED_ONLY": "Never eligible for open discovery; requires an exact trusted deferred record and deferred-resolution request.",
            "APPLICABILITY_RULE_UNDERDETERMINED": "Frozen authorities cannot justify inclusion, exclusion, or universal channel eligibility without a new decision.",
        },
        "authorityInputs": authority_inputs,
        "authorityInputAggregateSha256": sha256_bytes(canonical_json(authority_inputs)),
        "researcherApprovedExtractionPolicyDecisions": [
            {
                "decisionID": POLICY_DECISION_UNIVERSAL_OPEN,
                "decisionType": "prospective_extraction_policy",
                "approvalStatus": "researcher_approved",
                "authorityDerivedFacts": [
                    "publication_target_inventory.source_scope is publications",
                    "target.emission_mode is llm_candidate",
                    "target.direct_instantiation is true",
                    "target.pilot_treatment is extract_and_evaluate or extract_and_monitor",
                    "no binding answer-independent narrower applicability restriction exists",
                ],
                "policyConsequence": (
                    "Retain each active direct Publication llm_candidate target as eligible "
                    "throughout structurally eligible Publication source units in open_discovery."
                ),
                "rationale": [
                    "preserve recall opportunity",
                    "avoid answer-informed false exclusions",
                    "preserve an a-priori ontology-authorized extraction space",
                ],
                "notOntologyAxiom": True,
                "notLiteralTargetInventoryRule": True,
                "doesNotAssertInstancePresence": True,
                "semanticPrescreeningAuthorized": False,
            }
        ],
        "rules": _rules(),
        "candidateAuthorableNodeTargetCount": len(nodes),
        "policyClassCounts": {
            "universallyEligibleWithinOpenDiscovery": counts["llm_candidate"],
            "deterministicContextConditional": counts["deterministic_context"],
            "deferredOnly": counts["resolver_mediated_candidate"],
            "applicabilityRuleUnderdetermined": 0,
        },
        "sufficiencyConclusion": {
            "fullyDeterministicAnswerIndependentCoarsePolicySupported": True,
            "narrowSectionSpecificPolicySupported": False,
            "underdeterminedTargetsForCoarsePolicy": [],
            "targetsWithoutNarrowerFrozenApplicabilityRule": [
                row["operational_id"]
                for row in nodes
                if row["emission_mode"] == "llm_candidate"
            ],
            "gapClassification": "extraction_policy_decision_or_target_inventory_clarification_required_for_narrowing",
            "semanticPrescreeningRequiredForCoarsePolicy": False,
            "semanticPrescreeningWouldBeAnswerInformed": True,
        },
        "coverageSemantics": {
            "auditableClaim": (
                "Every structurally eligible source unit receives its complete applicable "
                "ontology-authorized node target space under the approved extraction policy."
            ),
            "requestLevelTargetSpaceCoverage": True,
            "targetLevelExplicitNegativeAssessmentRequired": False,
            "eligibilityAssertsInstancePresence": False,
            "oneAbstentionRequiredForEveryEligibleAbsentTarget": False,
            "noCandidateAndNoAbstentionPermitted": True,
            "prohibitedClaim": (
                "The model explicitly confirmed presence or absence for every eligible target."
            ),
        },
        "prospectiveVersioning": {
            "laterChangesRequireNewPolicyVersion": True,
            "laterChangesMustBeProspective": True,
            "preserveThisApprovedVersionAndHash": True,
            "retroactiveCompletedDevOutputChangesAllowed": False,
            "finalPilot1ProductionPolicy": False,
        },
    }
    policy["policySha256"] = _hash_record(policy, "policySha256")
    return policy


def derive_target_audit(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Audit each of the 46 candidate-authorable node targets."""

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    rows = []
    for target in _candidate_authorable_nodes(profile):
        mode = target["emission_mode"]
        if mode == "llm_candidate":
            channels = ["open_discovery"]
            status = "UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL"
            rule_ids = [RULE_SOURCE_ELIGIBLE, RULE_OPEN_UNIVERSAL, RULE_NO_SECTION_NARROWING]
            rule = "Include for every structurally eligible Publication source unit in open_discovery."
            narrower = False
            consequence_source = POLICY_DECISION_UNIVERSAL_OPEN
            consequence_frozen = False
            narrower_requires_new_policy = True
        elif mode == "deterministic_context":
            channels = ["open_discovery"]
            status = "DETERMINISTICALLY_APPLICABLE"
            rule_ids = [RULE_SOURCE_ELIGIBLE, RULE_DETERMINISTIC_BOUND, RULE_DETERMINISTIC_ABSENT]
            rule = "Include only when an exact trusted deterministic endpoint ref resolves to this operational target; otherwise exclude."
            narrower = True
            consequence_source = "frozen_exact_deterministic_binding_authorities"
            consequence_frozen = True
            narrower_requires_new_policy = False
        else:
            channels = ["deferred_resolution"]
            status = "DEFERRED_ONLY"
            rule_ids = [RULE_DEFERRED_ONLY, RULE_DEFERRED_EXACT]
            rule = "Exclude from open_discovery; include only for an exact trusted deferred record routed to this operational target."
            narrower = True
            consequence_source = "frozen_exact_deferred_routing_authorities"
            consequence_frozen = True
            narrower_requires_new_policy = False
        formal = target["formal_classes"]
        rows.append(
            {
                "operationalTargetID": target["operational_id"],
                "ontologyClasses": [
                    {"ontologyClassID": row["id"], "className": row["name"]}
                    for row in formal
                ],
                "emissionMode": mode,
                "allowedActions": list(target["allowed_actions"]),
                "applicableExtractionChannels": channels,
                "authoritativeApplicabilityFields": [
                    "publication_target_inventory.source_scope",
                    "target.emission_mode",
                    "target.pilot_treatment",
                    "target.allowed_actions",
                    "target.direct_instantiation",
                    "sourceUnit.eligibility",
                    "sourceUnit.requestEligible",
                    "sourceUnit.validationResults.valid",
                ]
                + (["sourceUnit.deterministicNodeRefs"] if mode == "deterministic_context" else [])
                + (["sourceUnit.deferredRecordRefs", "request.deferredRecords"] if mode == "resolver_mediated_candidate" else []),
                "deterministicApplicabilityRule": rule,
                "policyRuleIDs": rule_ids,
                "authorityFactsFullyDerivableFromFrozenAuthorities": True,
                "applicabilityConsequenceSource": consequence_source,
                "applicabilityConsequenceFullyDerivableFromFrozenAuthorities": consequence_frozen,
                "universalEligibilityExplicitlyEncodedInFrozenAuthorities": False,
                "narrowerFrozenApplicabilityRuleExists": narrower,
                "narrowerApplicabilityRequiresNewPolicyOrAuthority": narrower_requires_new_policy,
                "semanticPrescreeningRequired": False,
                "semanticPrescreeningAuthorized": False,
                "status": status,
            }
        )
    audit: dict[str, Any] = {
        "auditVersion": AUDIT_VERSION,
        "status": POLICY_STATUS,
        "policyVersion": policy["policyVersion"],
        "policySha256": policy["policySha256"],
        "targetCount": len(rows),
        "targets": rows,
        "statusCounts": dict(sorted(Counter(row["status"] for row in rows).items())),
    }
    audit["auditSha256"] = _hash_record(audit, "auditSha256")
    return audit


def _trusted_source_metadata(source: Mapping[str, Any]) -> dict[str, Any]:
    """Project only non-semantic fields used by applicability rules."""

    fields = (
        "recordType",
        "paperID",
        "sectionID",
        "sectionRole",
        "sectionLevel",
        "contentTypes",
        "eligibility",
        "requestEligible",
        "reviewRequired",
        "validationResults",
        "deterministicNodeRefs",
        "deferredRecordRefs",
        "eligibleCategories",
        "eligibleOperationalTargetIDs",
        "textHash",
        "inputHash",
    )
    return {field: source[field] for field in fields}


def evaluate_node_target_applicability(
    source_metadata: Mapping[str, Any],
    *,
    extraction_channel: str,
    deterministic_endpoint_bindings: Sequence[Mapping[str, Any]] = (),
    deferred_record_bindings: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Evaluate exact metadata bindings for one source unit and channel.

    Binding records are trusted caller-supplied authority projections. A deterministic
    binding uses ``recordID`` and ``operationalTargetID``; a deferred binding uses
    ``deferredRecordID`` and ``operationalTargetID``. Merely supplying a target ID without
    the exact referenced record ID never authorizes it.
    """

    if extraction_channel not in {"open_discovery", "deferred_resolution"}:
        raise ValueError(f"unsupported extraction channel: {extraction_channel}")
    if not (
        source_metadata.get("eligibility") == "eligible"
        and source_metadata.get("requestEligible") is True
        and source_metadata.get("validationResults") == {"valid": True, "errorCodes": []}
    ):
        return {
            "eligibleTargetIDs": [],
            "excludedTargetIDsByReason": {
                "source_unit_not_structurally_request_eligible": [
                    row["operational_id"]
                    for row in _candidate_authorable_nodes(
                        load_yaml_object(TARGET_INVENTORY_PATH)
                    )
                ]
            },
            "unresolvedTargetIDs": [],
            "policyRuleIDs": [RULE_SOURCE_ELIGIBLE],
        }
    targets = _candidate_authorable_nodes(load_yaml_object(TARGET_INVENTORY_PATH))
    open_ids = sorted(
        row["operational_id"] for row in targets if row["emission_mode"] == "llm_candidate"
    )
    context_ids = {
        row["operational_id"] for row in targets if row["emission_mode"] == "deterministic_context"
    }
    deferred_ids = {
        row["operational_id"]
        for row in targets
        if row["emission_mode"] == "resolver_mediated_candidate"
    }
    exact_endpoint_refs = set(source_metadata.get("deterministicNodeRefs", []))
    exact_deferred_refs = set(source_metadata.get("deferredRecordRefs", []))
    bound_context = sorted(
        str(binding["operationalTargetID"])
        for binding in deterministic_endpoint_bindings
        if binding.get("recordID") in exact_endpoint_refs
        and binding.get("operationalTargetID") in context_ids
    )
    bound_deferred = sorted(
        str(binding["operationalTargetID"])
        for binding in deferred_record_bindings
        if binding.get("deferredRecordID") in exact_deferred_refs
        and binding.get("operationalTargetID") in deferred_ids
    )
    if extraction_channel == "open_discovery":
        return {
            "eligibleTargetIDs": sorted(open_ids + bound_context),
            "excludedTargetIDsByReason": {
                "exact_deterministic_endpoint_binding_absent": sorted(context_ids - set(bound_context)),
                "deferred_only_target_in_open_discovery": sorted(deferred_ids),
            },
            "unresolvedTargetIDs": [],
            "policyRuleIDs": [
                RULE_SOURCE_ELIGIBLE,
                RULE_OPEN_UNIVERSAL,
                RULE_NO_SECTION_NARROWING,
                RULE_DETERMINISTIC_BOUND,
                RULE_DETERMINISTIC_ABSENT,
                RULE_DEFERRED_ONLY,
            ],
        }
    return {
        "eligibleTargetIDs": bound_deferred,
        "excludedTargetIDsByReason": {
            "exact_deferred_record_binding_absent": sorted(deferred_ids - set(bound_deferred)),
            "target_not_deferred_resolution_authorable": sorted(set(open_ids) | context_ids),
        },
        "unresolvedTargetIDs": [],
        "policyRuleIDs": [RULE_DEFERRED_ONLY, RULE_DEFERRED_EXACT],
    }


def derive_devset0_plan(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the policy mechanically to the ten approved development units."""

    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    targets = _candidate_authorable_nodes(profile)
    open_ids = sorted(
        row["operational_id"] for row in targets if row["emission_mode"] == "llm_candidate"
    )
    deterministic_ids = sorted(
        row["operational_id"] for row in targets if row["emission_mode"] == "deterministic_context"
    )
    deferred_ids = sorted(
        row["operational_id"]
        for row in targets
        if row["emission_mode"] == "resolver_mediated_candidate"
    )
    manifest = load_json_object(DEVELOPMENT_MANIFEST_PATH)
    inventory = {row["sourceUnitID"]: row for row in load_development_inventory()}
    target_definitions = {row["operational_id"]: row for row in targets}
    units = []
    for manifest_row in manifest["units"]:
        source = inventory[manifest_row["sourceUnitID"]]
        metadata = _trusted_source_metadata(source)
        if not (
            metadata["eligibility"] == "eligible"
            and metadata["requestEligible"] is True
            and metadata["validationResults"] == {"valid": True, "errorCodes": []}
        ):
            raise ValueError(f"DEV unit is not structurally request eligible: {source['sourceUnitID']}")
        if metadata["deterministicNodeRefs"] or metadata["deferredRecordRefs"]:
            raise ValueError("DEV-SET-0 unexpectedly contains deterministic or deferred bindings")
        decision = evaluate_node_target_applicability(
            metadata, extraction_channel="open_discovery"
        )
        if decision["eligibleTargetIDs"] != open_ids:
            raise ValueError("DEV open-discovery applicability did not match the policy")
        definition_bytes = len(
            canonical_json([target_definitions[target_id] for target_id in open_ids])
        )
        units.append(
            {
                "developmentID": manifest_row["developmentId"],
                "sourceUnitID": source["sourceUnitID"],
                "publicationArtifactID": source["canonicalArtifactID"],
                "trustedMetadataUsed": metadata,
                "extractionChannel": "open_discovery",
                "eligibleNodeOperationalTargetIDs": open_ids,
                "eligibleNodeTargetCount": len(open_ids),
                "eligibleTargetDefinitionCanonicalBytes": definition_bytes,
                "excludedTargetsByReason": [
                    {
                        "reason": "exact_deterministic_endpoint_binding_absent",
                        "targetIDs": decision["excludedTargetIDsByReason"][
                            "exact_deterministic_endpoint_binding_absent"
                        ],
                        "policyRuleIDs": [RULE_DETERMINISTIC_BOUND, RULE_DETERMINISTIC_ABSENT],
                    },
                    {
                        "reason": "deferred_only_target_in_open_discovery_and_no_deferred_record_binding",
                        "targetIDs": decision["excludedTargetIDsByReason"][
                            "deferred_only_target_in_open_discovery"
                        ],
                        "policyRuleIDs": [RULE_DEFERRED_ONLY, RULE_DEFERRED_EXACT],
                    },
                ],
                "unresolvedApplicabilityTargetIDs": [],
                "inclusionPolicyRuleIDs": [
                    RULE_SOURCE_ELIGIBLE,
                    RULE_OPEN_UNIVERSAL,
                    RULE_NO_SECTION_NARROWING,
                ],
                "historicalSmokeBindingUsedAsPolicyEvidence": False,
            }
        )
    overlap = {
        target_id: sum(target_id in row["eligibleNodeOperationalTargetIDs"] for row in units)
        for target_id in open_ids
    }
    plan: dict[str, Any] = {
        "planVersion": PLAN_VERSION,
        "status": POLICY_STATUS,
        "purpose": "prospective_answer_independent_node_request_plan_not_semantic_extraction",
        "policyVersion": policy["policyVersion"],
        "policySha256": policy["policySha256"],
        "manifestSha256": sha256_bytes(DEVELOPMENT_MANIFEST_PATH.read_bytes()),
        "developmentInventorySha256": sha256_bytes(DEVELOPMENT_INVENTORY_PATH.read_bytes()),
        "sourceTextInspectedForApplicability": False,
        "networkCalls": 0,
        "semanticExtractionCalls": 0,
        "relationsPlanned": False,
        "coverageSemantics": dict(policy["coverageSemantics"]),
        "units": units,
        "coverageSummary": {
            "unitCount": len(units),
            "eligibleTargetCountPerUnit": {
                row["developmentID"]: row["eligibleNodeTargetCount"] for row in units
            },
            "eligibleTargetUnitOverlap": overlap,
            "targetsEligibleInAllUnits": sorted(
                target_id for target_id, count in overlap.items() if count == len(units)
            ),
            "distinctEligibleTargetSets": len(
                {tuple(row["eligibleNodeOperationalTargetIDs"]) for row in units}
            ),
            "deferredRecordBearingUnitCount": 0,
            "deterministicNodeRefBearingUnitCount": 0,
        },
    }
    plan["planSha256"] = _hash_record(plan, "planSha256")
    return plan


def render_devset0_plan_markdown(
    policy: Mapping[str, Any], audit: Mapping[str, Any], plan: Mapping[str, Any]
) -> str:
    """Render the approved development plan without consulting source prose."""

    lines = [
        "# Publication DEV-SET-0 Node Request Plan v0.1.0",
        "",
        f"Status: `{POLICY_STATUS}`",
        "",
        "This is a prospective applicability plan, not semantic extraction, annotation, gold, or evaluation.",
        "No source prose, keyword rule, embedding, LLM, network request, or historical DEV-04 answer was used.",
        "",
        "## Policy conclusion",
        "",
        "Frozen authorities establish the Publication scope, active target metadata, and absence of a binding narrower applicability restriction. Researcher-approved extraction-policy decision `C0-POLICY-DECISION-001` supplies the prospective consequence that all 40 direct LLM node targets remain universally eligible in `open_discovery`. Four exact-existing context targets require exact deterministic endpoint bindings; two resolver-mediated targets are `deferred_resolution` only.",
        "Universal eligibility is not asserted to be a frozen ontology axiom or a literal target-inventory rule, and it does not assert that any target instance exists in a unit.",
        "",
        f"Policy SHA-256: `{policy['policySha256']}`",
        f"Target audit SHA-256: `{audit['auditSha256']}`",
        f"Plan SHA-256: `{plan['planSha256']}`",
        "",
        "## DEV-SET-0 plan",
        "",
        "| Development ID | Source unit | Section role | Channel | Eligible nodes | Deterministic-context excluded | Deferred-only excluded | Unresolved |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for unit in plan["units"]:
        excluded = {row["reason"]: len(row["targetIDs"]) for row in unit["excludedTargetsByReason"]}
        lines.append(
            f"| {unit['developmentID']} | `{unit['sourceUnitID']}` | "
            f"{unit['trustedMetadataUsed']['sectionRole']} | `{unit['extractionChannel']}` | "
            f"{unit['eligibleNodeTargetCount']} | "
            f"{excluded['exact_deterministic_endpoint_binding_absent']} | "
            f"{excluded['deferred_only_target_in_open_discovery_and_no_deferred_record_binding']} | "
            f"{len(unit['unresolvedApplicabilityTargetIDs'])} |"
        )
    lines.extend(
        [
            "",
            "All ten units use inclusion rules `C0-NODE-SOURCE-001`, `C0-NODE-OPEN-001`, and `C0-NODE-OPEN-002`.",
            "Every deterministic exclusion is bound to the exact rule IDs recorded in the JSON plan.",
            "",
            "## Target-by-target audit",
            "",
            "| Operational target | Ontology class | Emission mode | Actions | Channels | Status | Rule IDs |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in audit["targets"]:
        classes = ", ".join(
            f"{item['ontologyClassID']} / {item['className']}" for item in row["ontologyClasses"]
        )
        lines.append(
            f"| `{row['operationalTargetID']}` | {classes} | `{row['emissionMode']}` | "
            f"{', '.join(row['allowedActions'])} | {', '.join(row['applicableExtractionChannels'])} | "
            f"`{row['status']}` | {', '.join(row['policyRuleIDs'])} |"
        )
    lines.extend(
        [
            "",
            "## Coverage implications",
            "",
            "The approved coarse policy preserves request-level target-space coverage and avoids answer-informed false exclusions, but it exposes 40 target definitions per unit. This increases provider-input and schema size compared with the historical one-target DEV-04 smoke. Future narrowing requires a new, versioned, prospective extraction-policy decision or binding target-inventory applicability clarification. Semantic pre-screening of a particular unit is not authorized.",
            "",
            "Request-level target-space coverage is distinct from target-level explicit negative assessment. The frozen abstention contract does not require one abstention for every eligible target that is absent. No candidate and no abstention remains permissible when no supported assertion is emitted. Accordingly, this plan supports the claim that every structurally eligible source unit receives its complete applicable ontology-authorized node target space; it does not claim that the model explicitly confirmed presence or absence for every target.",
            "",
        ]
    )
    return "\n".join(lines)


def write_policy_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, str]:
    """Write all four deterministic M2-C0 approved-development artifacts."""

    policy = derive_policy()
    audit = derive_target_audit(policy)
    plan = derive_devset0_plan(policy)
    markdown = render_devset0_plan_markdown(policy, audit, plan).encode("utf-8")
    paths = {
        "policy": output_dir / "publication_node_target_applicability_policy_v0.1.0.json",
        "audit": output_dir / "publication_node_target_applicability_audit_v0.1.0.json",
        "planJSON": output_dir / "publication_devset0_node_request_plan_v0.1.0.json",
        "planMarkdown": output_dir / "publication_devset0_node_request_plan_v0.1.0.md",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    paths["policy"].write_bytes(canonical_json_file(policy))
    paths["audit"].write_bytes(canonical_json_file(audit))
    paths["planJSON"].write_bytes(canonical_json_file(plan))
    paths["planMarkdown"].write_bytes(markdown)
    return {key: str(value) for key, value in paths.items()}


def main(argv: Sequence[str] | None = None) -> int:
    """Generate deterministic M2-C0 policy artifacts without network or model calls."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    print(json.dumps(write_policy_artifacts(args.output_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
