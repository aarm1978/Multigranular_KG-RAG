"""Build and validate Publication Pilot 1 Block A artifacts.

Inputs are the accepted source-unit inventory and frozen target profile.  The
first-stage generator writes only deterministic infrastructure and a CSV worklist;
it deliberately leaves semantic screening fields blank for human review.  A later
call to :func:`compile_reviewed_worklist` validates a completed worklist and
materializes routing, coverage, calibration, and candidate-order artifacts.
"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml


BLOCK_A_INFRASTRUCTURE_VERSION = "0.1.4"
SCREENING_SCHEMA_VERSION = "0.1.1"
SCREENING_VERSION = "0.1.1"
ROUTING_SCHEMA_VERSION = "0.1.2"
ROUTING_VERSION = "0.1.2"
SELECTION_POLICY_VERSION = "0.1.4"
TARGET_MAPPING_VERSION = "0.1.0"
TARGET_DISPLAY_CATALOG_VERSION = "0.1.0"
CANDIDATE_ORDER_VERSION = "0.1.3"
CALIBRATION_MANIFEST_VERSION = "0.1.3"
GATE0_POLICY_VERSION = "0.1.0"
ARTIFACT_QUOTA_ROLE_POLICY_VERSION = "0.1.0"
TARGET_COVERAGE_MATRIX_VERSION = "0.1.0"
DEFERRED_ROUTE_UNAVAILABLE_REASON = "deferred_record_binding_absent"

INVENTORY_HASH = "7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e"
MANIFEST_HASH = "42684d340af99440d5f72129a5c5299edcb237d77ce2b3d36456b049bee83823"
TARGET_PROFILE_HASH = "3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760"

REPORTING_FAMILIES = (
    "research_framing",
    "discourse_structure",
    "methods_and_experiments",
    "models_algorithms_and_tools",
    "findings_conclusions_limitations_and_future_work",
    "metrics_parameters_and_variables",
    "datasets_and_repositories",
    "concepts_and_geography",
    "discourse_relations",
    "use_mention_reference_relations",
)
SAMPLING_STRATA = (
    "core_discourse_nodes",
    "scientific_entity_nodes",
    "core_discourse_relations",
    "entity_role_and_study_context_relations",
    "measurement_context_relations",
)
OPEN_TREATMENTS = {"extract_and_evaluate", "extract_and_monitor", "deferred_resolution"}
SEMANTIC_TREATMENTS = {"extract_and_evaluate", "extract_and_monitor"}
DEFAULT_EXHAUSTIVE_TREATMENTS = {"extract_and_evaluate"}
SCREENING_STATUSES = {
    "reviewed",
    "not_open_annotation_target",
    "blocked_needs_review",
}
DENSITIES = {"none", "low", "medium", "high", "not_applicable"}
ROUTING_COMPLEXITIES = {"low", "medium", "high", "not_applicable"}
TIMING_EVENTS = (
    "unit_opened", "reading_complete", "node_pass_started", "node_pass_completed",
    "relation_pass_started", "relation_pass_completed", "review_started", "submitted",
    "pause_started", "pause_ended", "technical_interruption_started",
    "technical_interruption_ended",
)
RECURRING_DISTINCTIONS = (
    "Model/Method/Algorithm/Tool",
    "Finding/Conclusion",
    "ResearchProblem/ResearchGoal",
    "use/mention/reference",
    "EvaluationMetric/Parameter",
)
SECTION_GROUP_MAPPING = {
    "framing": ["abstract", "introduction", "background", "related_work"],
    "methods_data": ["methods", "data", "study_area"],
    "results": ["results"],
    "interpretation": ["discussion", "conclusion", "limitations", "future_work"],
    "other_eligible": ["other"],
}
CONVERSION_STATUS_SUMMARIES = {
    "canonical_markdown_available",
    "canonical_markdown_sanitized_forbidden_controls",
}

DETERMINISTIC_COLUMNS = (
    "screeningSchemaVersion", "screeningVersion", "sourceArtifactID", "paperID", "sourceUnitID",
    "sourceUnitTextHash", "sectionID", "sectionTitle", "sectionRole", "characterCount",
    "contentTypes", "sourceEligibility", "requestEligible", "reviewRequired",
    "reviewReasons", "sourceConversionStatus", "sourceTextPath", "startOffsetInDocument",
    "endOffsetInDocument", "inputHash", "deterministicNodeRefs",
    "deterministicEdgeRefs", "deferredRecordRefs",
)
HUMAN_COLUMNS = (
    "screeningReviewerID", "screenedAt", "screeningStatus", "screeningRationale",
    "likelyExhaustiveEmptyTargetIDs", "likelyRecurringDistinctions", "expectedAssertionDensity",
    "expectedRelationDensity", "routingComplexity", "distributedEvidenceLikely",
    "sectionContextUseful", "deterministicEndpointLikely", "routedNodeOperationalTargetIDs",
    "routedRelationOperationalTargetIDs", "screeningNotes",
)

_NODE_FAMILY_BY_LABEL = {
    **{name: "research_framing" for name in (
        "Background", "Theme", "ResearchProblem", "ResearchQuestion", "ResearchGoal",
        "ResearchSignificance", "Hypothesis", "Claim")},
    **{name: "discourse_structure" for name in (
        "Definition", "TheoreticalBasis", "Examples", "Discussion", "RelatedResearch")},
    **{name: "methods_and_experiments" for name in ("Method", "Experiment", "DataDescription")},
    **{name: "models_algorithms_and_tools" for name in (
        "Tool — new from publication prose", "ProcessBasedModel", "ConceptualModel",
        "StatisticalModel", "MLModel", "Algorithm")},
    **{name: "findings_conclusions_limitations_and_future_work" for name in (
        "Finding", "Limitation", "Conclusion", "Contribution", "FutureWork")},
    **{name: "metrics_parameters_and_variables" for name in (
        "EvaluationMetric", "Parameter", "Variable")},
    **{name: "datasets_and_repositories" for name in (
        "DatasetMention — new from prose", "Repository — named without exact identity")},
    **{name: "concepts_and_geography" for name in (
        "Concept", "Watershed", "RiverReach", "Gauge", "WaterBody", "Aquifer", "VPU",
        "NamedPlace")},
}


class BlockAValidationError(ValueError):
    """Report a stable Block A validation failure."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file without changing it."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Serialize JSON deterministically with a terminal newline."""

    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_if_changed(path: Path, content: bytes) -> None:
    """Write deterministic bytes only when the destination differs."""

    if path.exists() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _yaml_bytes(value: Any) -> bytes:
    """Serialize YAML deterministically while preserving declared order."""

    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=110).encode("utf-8")


def _split_multi(value: str) -> list[str]:
    """Parse the documented pipe-delimited worklist representation."""

    return sorted({item.strip() for item in value.split("|") if item.strip()})


def _join_multi(value: Iterable[Any]) -> str:
    """Serialize a multi-valued worklist field in stable lexical order."""

    return "|".join(sorted(str(item) for item in value))


def _parse_bool(value: str, field: str) -> bool:
    """Parse the worklist's lowercase boolean vocabulary."""

    if value == "true":
        return True
    if value == "false":
        return False
    raise BlockAValidationError(f"SCREENING_INVALID_BOOLEAN:{field}:{value}")


def _load_inputs(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Load and hash-check the immutable inventory, profile, and manifest."""

    inventory_path = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl"
    profile_path = root / "src/extraction/llm/publications/publication_target_inventory.yaml"
    manifest_path = root / "data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json"
    if sha256_file(inventory_path) != INVENTORY_HASH:
        raise BlockAValidationError("BLOCK_A_SOURCE_UNIT_INVENTORY_HASH_DRIFT")
    if sha256_file(profile_path) != TARGET_PROFILE_HASH:
        raise BlockAValidationError("BLOCK_A_TARGET_PROFILE_HASH_DRIFT")
    if sha256_file(manifest_path) != MANIFEST_HASH:
        raise BlockAValidationError("BLOCK_A_SOURCE_UNIT_MANIFEST_HASH_DRIFT")
    records = [json.loads(line) for line in inventory_path.read_text(encoding="utf-8").splitlines() if line]
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(records) != 358 or len({record["sourceUnitID"] for record in records}) != 358:
        raise BlockAValidationError("BLOCK_A_INVENTORY_CARDINALITY_MISMATCH")
    return records, profile, manifest


def _conversion_by_paper(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Return each artifact's frozen manifest conversion-status summary."""

    result = {
        record["paperID"]: record["conversionStatusSummary"]
        for record in manifest["artifactRecords"]
    }
    if set(result.values()) - CONVERSION_STATUS_SUMMARIES:
        raise BlockAValidationError("BLOCK_A_UNKNOWN_CONVERSION_STATUS_SUMMARY")
    return result


def _decision_role(treatment: str) -> str:
    """Map the frozen treatment to its approved decision role."""

    if treatment == "extract_and_evaluate":
        return "blocking"
    if treatment == "extract_and_monitor":
        return "monitored"
    if treatment == "deferred_resolution":
        return "deferred_resolution_only"
    return "excluded_or_follow_on"


def _relation_family(target: Mapping[str, Any]) -> str:
    """Assign an open relation to one of the two frozen relation families."""

    relation = str(target["operational_relation"]).lower()
    if any(token in relation for token in ("use", "mention", "reference", "hascoderepository")):
        return "use_mention_reference_relations"
    return "discourse_relations"


def _sampling_stratum(kind: str, target: Mapping[str, Any], family: str | None) -> str | None:
    """Return the decision-neutral optional balancing stratum."""

    if family is None:
        return None
    if kind == "node":
        return "core_discourse_nodes" if family in {
            "research_framing", "discourse_structure", "methods_and_experiments",
            "findings_conclusions_limitations_and_future_work",
        } else "scientific_entity_nodes"
    if target["operational_relation"].split(" —", 1)[0] in {"reportsMetric", "evaluates", "hasParameter"}:
        return "measurement_context_relations"
    if family == "discourse_relations" and target["operational_relation"].split(" —", 1)[0] in {
        "resolves", "produces", "testedBy", "supports", "relatesTo", "hasLimitation",
    }:
        return "core_discourse_relations"
    return "entity_role_and_study_context_relations"


def build_target_mapping(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Create the complete 105-target family/role/stratum mapping."""

    rows: list[dict[str, Any]] = []
    for kind, key in (("node", "node_targets"), ("relation", "relation_targets")):
        for target in profile[key]:
            role = _decision_role(target["pilot_treatment"])
            family: str | None = None
            if role in {"blocking", "monitored"}:
                family = _NODE_FAMILY_BY_LABEL.get(target["operational_target"]) if kind == "node" else _relation_family(target)
                if family is None:
                    raise BlockAValidationError(f"TARGET_MAPPING_MISSING_FAMILY:{target['operational_id']}")
            rows.append({
                "operationalTargetID": target["operational_id"],
                "targetKind": kind,
                "reportingFamily": family,
                "decisionRole": role,
                "samplingStratum": _sampling_stratum(kind, target, family),
                "pilotTreatment": target["pilot_treatment"],
                "productionResponsibility": target["production_responsibility"],
            })
    validate_target_mapping(rows, profile)
    return {
        "mappingVersion": TARGET_MAPPING_VERSION,
        "targetProfileHash": TARGET_PROFILE_HASH,
        "reportingFamilies": list(REPORTING_FAMILIES),
        "samplingStrata": list(SAMPLING_STRATA),
        "targets": rows,
    }


def validate_target_mapping(rows: Sequence[Mapping[str, Any]], profile: Mapping[str, Any]) -> None:
    """Validate mapping completeness and conditional family rules."""

    expected = [target["operational_id"] for key in ("node_targets", "relation_targets") for target in profile[key]]
    actual = [str(row["operationalTargetID"]) for row in rows]
    if len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise BlockAValidationError("TARGET_MAPPING_PROFILE_COVERAGE_MISMATCH")
    for row in rows:
        role, family, stratum = row["decisionRole"], row["reportingFamily"], row["samplingStratum"]
        if role in {"blocking", "monitored"} and family not in REPORTING_FAMILIES:
            raise BlockAValidationError(f"TARGET_MAPPING_INVALID_REPORTING_FAMILY:{row['operationalTargetID']}")
        if role not in {"blocking", "monitored"} and family is not None:
            raise BlockAValidationError(f"TARGET_MAPPING_FORBIDDEN_REPORTING_FAMILY:{row['operationalTargetID']}")
        if stratum is not None and stratum not in SAMPLING_STRATA:
            raise BlockAValidationError(f"TARGET_MAPPING_INVALID_SAMPLING_STRATUM:{row['operationalTargetID']}")


def build_display_catalog(profile: Mapping[str, Any], mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Build the human-interface catalog without changing frozen target meanings."""

    mapped = {row["operationalTargetID"]: row for row in mapping["targets"]}
    targets: list[dict[str, Any]] = []
    display_order = 0
    for kind, key in (("node", "node_targets"), ("relation", "relation_targets")):
        for target in profile[key]:
            row = mapped[target["operational_id"]]
            visible = target["pilot_treatment"] in OPEN_TREATMENTS
            if visible:
                display_order += 1
            item: dict[str, Any] = {
                "operationalTargetID": target["operational_id"],
                "targetKind": kind,
                "displayLabel": target.get("operational_target", target.get("operational_relation")),
                "shortDefinition": target["positive_criterion"],
                "boundaryHint": target["boundary"],
                "pilotTreatment": target["pilot_treatment"],
                "decisionRole": row["decisionRole"],
                "reportingFamily": row["reportingFamily"],
                "samplingStratum": row["samplingStratum"],
                "humanVisible": visible,
                "displayGroup": row["reportingFamily"] or row["decisionRole"],
                "displayOrder": display_order if visible else None,
            }
            if kind == "node":
                item["ontologyClassIDs"] = target["ontology_ids"]
                item["backendClasses"] = [entry["name"] for entry in target["formal_classes"]]
                item["directInstantiation"] = target["direct_instantiation"]
            else:
                signatures = target["operational_signatures"]
                item["operationalRelation"] = target["operational_relation"]
                item["domainClasses"] = sorted({c for sig in signatures for c in sig["domain"]["classes"]})
                item["rangeClasses"] = sorted({c for sig in signatures for c in sig["range"]["classes"]})
                item["operationalSignatures"] = signatures
                item["requiresDeterministicEndpoint"] = target["pilot_treatment"] == "deferred_resolution" or any(
                    "endpoint" in constraint
                    for sig in signatures
                    for side in ("domain", "range")
                    for constraint in sig[side].get("constraints", [])
                )
            targets.append(item)
    return {
        "catalogVersion": TARGET_DISPLAY_CATALOG_VERSION,
        "targetProfileHash": TARGET_PROFILE_HASH,
        "menuPolicy": "Group legitimate targets; never truncate semantic routing at 12.",
        "targets": targets,
    }


def _structural_human_defaults(record: Mapping[str, Any]) -> dict[str, str]:
    """Return only non-semantic defaults for a structurally non-open unit."""

    blank = {column: "" for column in HUMAN_COLUMNS}
    if record["eligibility"] == "eligible" and record["requestEligible"]:
        return blank
    blank.update({
        "screeningStatus": "blocked_needs_review" if record["eligibility"] == "needs_review" else "not_open_annotation_target",
        "screeningRationale": "structurally_blocked_by_accepted_source_unit_inventory",
        "likelyExhaustiveEmptyTargetIDs": "",
        "likelyRecurringDistinctions": "",
        "expectedAssertionDensity": "not_applicable",
        "expectedRelationDensity": "not_applicable",
        "routingComplexity": "not_applicable",
        "distributedEvidenceLikely": "false",
        "sectionContextUseful": "false",
        "deterministicEndpointLikely": "false",
        "routedNodeOperationalTargetIDs": "",
        "routedRelationOperationalTargetIDs": "",
    })
    return blank


def build_worklist(records: Sequence[Mapping[str, Any]], conversion_by_paper: Mapping[str, str]) -> bytes:
    """Create the byte-reproducible 358-row human screening worklist."""

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=DETERMINISTIC_COLUMNS + HUMAN_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = {
            "screeningSchemaVersion": SCREENING_SCHEMA_VERSION,
            "screeningVersion": SCREENING_VERSION,
            "sourceArtifactID": record["canonicalArtifactID"],
            "paperID": record["paperID"],
            "sourceUnitID": record["sourceUnitID"],
            "sourceUnitTextHash": record["textHash"],
            "sectionID": record["sectionID"],
            "sectionTitle": record["sectionTitleRaw"] or record["sectionTitleNormalized"],
            "sectionRole": record["sectionRole"],
            "characterCount": record["characterCount"],
            "contentTypes": _join_multi(record["contentTypes"]),
            "sourceEligibility": record["eligibility"],
            "requestEligible": str(record["requestEligible"]).lower(),
            "reviewRequired": str(record["reviewRequired"]).lower(),
            "reviewReasons": _join_multi(record["reviewReasons"]),
            "sourceConversionStatus": conversion_by_paper[record["paperID"]],
            "sourceTextPath": record["sourceFile"],
            "startOffsetInDocument": record["startOffsetInDocument"],
            "endOffsetInDocument": record["endOffsetInDocument"],
            "inputHash": record["inputHash"],
            "deterministicNodeRefs": _join_multi(record["deterministicNodeRefs"]),
            "deterministicEdgeRefs": _join_multi(record["deterministicEdgeRefs"]),
            "deferredRecordRefs": _join_multi(record["deferredRecordRefs"]),
        }
        row.update(_structural_human_defaults(record))
        writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def build_artifact_quota_role_policy(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Derive auditable quota roles from accepted manifest artifact record types."""

    artifacts: list[dict[str, Any]] = []
    for record in manifest["artifactRecords"]:
        is_corrigendum = record["recordType"] == "corrigendum"
        artifacts.append({
            "paperID": record["paperID"],
            "sourceArtifactID": record["canonicalArtifactID"],
            "recordType": record["recordType"],
            "artifactQuotaRole": "corrigendum_diagnostic" if is_corrigendum else "primary_publication",
            "quotaBearing": not is_corrigendum,
            "postCalibrationAllowedBlockBPartitions": (
                ["reserved_diagnostic"] if is_corrigendum else
                ["reliability", "remaining_evaluation", "reserved_diagnostic"]
            ),
        })
    return {
        "artifactQuotaRolePolicyVersion": ARTIFACT_QUOTA_ROLE_POLICY_VERSION,
        "derivationRule": {
            "recordType=corrigendum": "corrigendum_diagnostic; non-quota-bearing; reserved_diagnostic only",
            "allOtherAcceptedPublicationRecordTypes": "primary_publication; quota-bearing",
        },
        "artifacts": artifacts,
    }


def selection_policy(artifact_quota_roles: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the prospective, timing-blind selection policy."""

    return {
        "blockAInfrastructureVersion": BLOCK_A_INFRASTRUCTURE_VERSION,
        "policyVersion": SELECTION_POLICY_VERSION,
        "status": "draft_pending_human_screening",
        "populationHash": INVENTORY_HASH,
        "screening": {"version": SCREENING_VERSION, "hash": None},
        "routing": {"version": ROUTING_VERSION, "hash": None},
        "eligiblePrimaryRule": (
            "sourceEligibility=eligible AND requestEligible=true AND screeningStatus=reviewed "
            "AND at least one routed blocking/monitored target"
        ),
        "artifactIdentityRule": (
            "sourceArtifactID is canonicalArtifactID; paperID is the local grouping key for "
            "per-artifact candidate order and quota activation"
        ),
        "artifactQuotaRoles": artifact_quota_roles,
        "routingMetadataDerivationRule": (
            "likelyReportingFamilies and likelySamplingStrata are sorted unique values derived "
            "from routed blocking/monitored targets through target-family mapping 0.1.0; "
            "deferred-resolution-only targets contribute neither"
        ),
        "effectiveRoutingAvailabilityRule": {
            "humanRouteHistory": (
                "Human-screened operational target IDs remain preserved in routing provenance."
            ),
            "deferredResolution": (
                "A deferred_resolution target enters effective routing only when the accepted "
                "source-unit record has at least one exact deferredRecordRef."
            ),
            "unavailableReason": DEFERRED_ROUTE_UNAVAILABLE_REASON,
            "downstreamUse": (
                "Only effective operational targets contribute prospective coverage, calibration "
                "selection, or candidate ordering."
            ),
        },
        "prospectiveCompletenessRule": {
            "defaultExhaustiveTreatments": sorted(DEFAULT_EXHAUSTIVE_TREATMENTS),
            "defaultNonExhaustiveMonitorTreatments": ["extract_and_monitor"],
            "monitorPromotion": "requires explicit pre-annotation promotion not implemented in Block A 0.1.4",
            "likelyExhaustiveEmptyTargetIDs": "may contain only routed default-exhaustive targets",
        },
        "calibrationSelectionRule": {
            "targetCount": 16,
            "allowedRange": [12, 16],
            "method": "deterministic greedy maximum new prospective coverage, then lowest exposure, then lexical sourceUnitID",
            "dimensions": [
                "lengthBand", "sectionGroup", "routingLoadBand", "expectedAssertionDensity",
                "expectedRelationDensity", "routingComplexity",
                "likelyReportingFamilies", "likelySamplingStrata", "likelyExhaustiveEmptyCapability",
                "likelyRecurringDistinctions", "routedOperationalTargetIDs", "deterministicEndpointLikely",
                "distributedEvidenceLikely", "sectionContextUseful", "sourceConversionStatus",
            ],
            "knownRecurringAnnotationDistinctions": list(RECURRING_DISTINCTIONS),
            "deferredResolutionRule": "Deferred-resolution-only routing does not establish primary-candidate eligibility.",
            "noEligibleTargetRule": (
                "A reviewed structurally eligible unit with zero blocking/monitored routed targets "
                "receives reviewed_no_eligible_target and is excluded from calibration and candidate order."
            ),
            "exclusions": ["primary extraction metrics", "IAA"],
        },
        "postCalibrationCandidateOrderingRule": (
            "Within each artifact, greedily rank greatest new prospective coverage contribution; "
            "then higher routing load, then lexical sourceUnitID. Timing never enters the order."
        ),
        "selectionTierDefinitions": {
            "must_cover": "adds a previously uncovered reporting family, sampling stratum, or section group within the artifact",
            "preferred": "adds another prospective coverage dimension",
            "reserve": "adds no new prospective dimension at its rank",
        },
        "coverageDimensions": [
            "artifact identity", "section group", "source-unit length", "likely reporting families",
            "likely sampling strata", "expected assertion density", "expected relation density",
            "routing complexity", "deterministic endpoint presence", "distributed-evidence likelihood",
            "likely exhaustive-empty capability", "source conversion/special condition",
        ],
        "sectionGroupMapping": SECTION_GROUP_MAPPING,
        "tieBreakRule": "lexical sourceUnitID after all predeclared criteria",
        "artifactRepresentationRule": (
            "Calibration need not cover every artifact. Gate-0 quota activation is per quota-bearing "
            "primary publication artifact. Corrigendum post-calibration candidates remain ordered but "
            "are eligible only for reserved_diagnostic assignment in Block B."
        ),
        "leakageControls": [
            "no model prediction, confidence, validator output, annotation count, gold, or timing value",
            "screening expectations are prospective and never gold",
        ],
        "armBlindnessRule": "No experiment arm, model, or prompt-result field is accepted or emitted.",
        "gate0HandoffRule": (
            "Gate 0 activates quota 5 or 4 only for artifacts with quotaBearing=true; Block B takes "
            "prefixes of their frozen per-artifact orders without reranking. Non-quota-bearing "
            "corrigendum candidates may be assigned only to reserved_diagnostic."
        ),
        "blockBOnlyFields": [
            "reliabilitySourceUnitIDs", "remainingEvaluationSourceUnitIDs", "reservedDiagnosticSourceUnitIDs",
            "finalPublicationUnitQuotaPerArtifact", "finalSampleSelectionManifest", "completenessModeByTarget",
        ],
    }


def gate0_policy() -> dict[str, Any]:
    """Return the predeclared Publication-only timing gate."""

    return {
        "gate0PolicyVersion": GATE0_POLICY_VERSION,
        "artifactFamily": "publications_only",
        "status": "frozen_before_timing_observation",
        "annotatorsPerUnit": 2,
        "independentTimingRequired": True,
        "activeAnnotationMinutes": "readingMinutes + nodePassMinutes + relationPassMinutes + reviewSubmitMinutes",
        "excludedMinutes": ["pauseIdleMinutes", "trainingMinutes", "jointDiscussionMinutes", "technicalInterruptionMinutes"],
        "unitTimingMinutes": "(annotator1ActiveAnnotationMinutes + annotator2ActiveAnnotationMinutes) / 2",
        "percentiles": {"algorithm": "nearest_rank", "rank": "ceil(p * N)", "indexing": "sorted_1_indexed", "values": [50, 75, 90]},
        "decisions": {
            "GREEN": {"condition": "P50 <= 15 AND P75 <= 20 AND P90 <= 30", "publicationUnitsPerArtifact": 5},
            "AMBER": {"condition": "GREEN fails AND P50 <= 20 AND P75 <= 25 AND P90 <= 40", "publicationUnitsPerArtifact": 4},
            "RED": {
                "condition": "P50 > 20 OR P75 > 25 OR P90 > 40",
                "publicationUnitsPerArtifact": None,
                "action": "pause Block B; reassess or cut ICLR scope; do not invent a smaller quota",
            },
        },
        "diagnostics": {
            "minutesPerNode": "activeAnnotationMinutes / positiveNodes when positiveNodes > 0; otherwise undefined",
            "minutesPerRelation": "activeAnnotationMinutes / positiveRelations when positiveRelations > 0; otherwise undefined",
            "minutesPerAssertion": "activeAnnotationMinutes / (positiveNodes + positiveRelations) when assertions > 0; otherwise undefined",
            "thresholdRole": "diagnostic_only",
        },
        "timingEventContract": {
            "eventTypes": list(TIMING_EVENTS),
            "requiredFields": [
                "annotationSessionID", "annotatorID", "sourceUnitID", "sourceUnitTextHash",
                "interfaceVersion", "guidelineVersion", "handbookVersion", "routingVersion",
                "timestamp", "eventType",
            ],
        },
    }


def nearest_rank(values: Sequence[float], percentile: float) -> float:
    """Compute a nearest-rank percentile over non-empty numeric values."""

    if not values or not 0 < percentile <= 1:
        raise BlockAValidationError("GATE0_INVALID_PERCENTILE_INPUT")
    ordered = sorted(float(value) for value in values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def timing_diagnostics(active_minutes: float, nodes: int, relations: int) -> dict[str, float | None]:
    """Compute non-threshold timing diagnostics with undefined zero denominators."""

    assertions = nodes + relations
    return {
        "minutesPerNode": active_minutes / nodes if nodes else None,
        "minutesPerRelation": active_minutes / relations if relations else None,
        "minutesPerAssertion": active_minutes / assertions if assertions else None,
    }


def materialize_infrastructure(root: Path) -> dict[str, Any]:
    """Write all deterministic artifacts allowed before human screening."""

    records, profile, manifest = _load_inputs(root)
    output = root / "data/curation/papers/pilot1"
    mapping = build_target_mapping(profile)
    catalog = build_display_catalog(profile, mapping)
    paths = {
        "worklist": output / "publication_pilot1_screening_worklist.csv",
        "mapping": output / "publication_pilot1_target_family_mapping.yaml",
        "catalog": output / "publication_pilot1_target_display_catalog.yaml",
        "selectionPolicy": output / "publication_pilot1_selection_policy.yaml",
        "gate0Policy": output / "publication_pilot1_gate0_policy.yaml",
    }
    _write_if_changed(paths["worklist"], build_worklist(records, _conversion_by_paper(manifest)))
    _write_if_changed(paths["mapping"], _yaml_bytes(mapping))
    _write_if_changed(paths["catalog"], _yaml_bytes(catalog))
    _write_if_changed(
        paths["selectionPolicy"],
        _yaml_bytes(selection_policy(build_artifact_quota_role_policy(manifest))),
    )
    _write_if_changed(paths["gate0Policy"], _yaml_bytes(gate0_policy()))
    return {
        "sourceUnitCount": len(records),
        "structuralStatusCounts": dict(Counter(
            "pending_human_review" if r["eligibility"] == "eligible" else
            "blocked_needs_review" if r["eligibility"] == "needs_review" else
            "not_open_annotation_target" for r in records
        )),
        "targetMappingCount": len(mapping["targets"]),
        "displayCatalogCount": len(catalog["targets"]),
        "humanVisibleTargetCount": sum(t["humanVisible"] for t in catalog["targets"]),
        "paths": {key: str(path) for key, path in paths.items()},
    }


def _validate_reviewed_rows(
    rows: Sequence[Mapping[str, str]], inventory: Sequence[Mapping[str, Any]],
    profile: Mapping[str, Any], conversion_by_paper: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate human rows and return screening and routing records."""

    by_id = {record["sourceUnitID"]: record for record in inventory}
    if len(rows) != len(by_id) or len({row.get("sourceUnitID") for row in rows}) != len(rows):
        raise BlockAValidationError("SCREENING_MISSING_OR_DUPLICATE_RECORD")
    if {row.get("sourceUnitID") for row in rows} != set(by_id):
        raise BlockAValidationError("SCREENING_UNKNOWN_OR_MISSING_SOURCE_UNIT")
    targets = {t["operational_id"]: (kind, t) for kind, key in (("node", "node_targets"), ("relation", "relation_targets")) for t in profile[key]}
    target_dimensions = {
        row["operationalTargetID"]: row
        for row in build_target_mapping(profile)["targets"]
    }
    screening: list[dict[str, Any]] = []
    routing: list[dict[str, Any]] = []
    allowed_columns = set(DETERMINISTIC_COLUMNS + HUMAN_COLUMNS)
    unknown_columns = set(rows[0]) - allowed_columns
    if unknown_columns:
        raise BlockAValidationError(f"SCREENING_UNKNOWN_OR_FORBIDDEN_FIELD:{sorted(unknown_columns)[0]}")
    for row in rows:
        source = by_id[row["sourceUnitID"]]
        generated_row = next(csv.DictReader(io.StringIO(build_worklist([source], conversion_by_paper).decode("utf-8"))))
        for field in DETERMINISTIC_COLUMNS:
            if row.get(field) != generated_row[field]:
                raise BlockAValidationError(f"SCREENING_FROZEN_FIELD_DRIFT:{row['sourceUnitID']}:{field}")
        status = row["screeningStatus"]
        if status not in SCREENING_STATUSES:
            raise BlockAValidationError(f"SCREENING_INVALID_STATUS:{row['sourceUnitID']}:{status}")
        open_unit = source["eligibility"] == "eligible" and source["requestEligible"]
        if open_unit and status != "reviewed":
            raise BlockAValidationError(f"SCREENING_OPEN_UNIT_NOT_REVIEWED:{row['sourceUnitID']}")
        if open_unit and any(not row[field].strip() for field in ("screeningReviewerID", "screenedAt", "screeningRationale")):
            raise BlockAValidationError(f"SCREENING_REQUIRED_HUMAN_FIELD_EMPTY:{row['sourceUnitID']}")
        if not open_unit:
            expected_status = "blocked_needs_review" if source["eligibility"] == "needs_review" else "not_open_annotation_target"
            if status != expected_status:
                raise BlockAValidationError(f"SCREENING_STRUCTURAL_STATUS_MISMATCH:{row['sourceUnitID']}")
        exhaustive_empty_ids = _split_multi(row["likelyExhaustiveEmptyTargetIDs"])
        for target_id in exhaustive_empty_ids:
            if target_id not in targets:
                raise BlockAValidationError(f"SCREENING_UNKNOWN_EXHAUSTIVE_EMPTY_TARGET:{row['sourceUnitID']}")
            if targets[target_id][1]["pilot_treatment"] not in DEFAULT_EXHAUSTIVE_TREATMENTS:
                raise BlockAValidationError(f"SCREENING_EXHAUSTIVE_EMPTY_TARGET_NOT_DEFAULT_EXHAUSTIVE:{row['sourceUnitID']}:{target_id}")
        recurring_distinctions = _split_multi(row["likelyRecurringDistinctions"])
        if any(value not in RECURRING_DISTINCTIONS for value in recurring_distinctions):
            raise BlockAValidationError(f"SCREENING_UNKNOWN_RECURRING_DISTINCTION:{row['sourceUnitID']}")
        human_node_ids = _split_multi(row["routedNodeOperationalTargetIDs"])
        human_relation_ids = _split_multi(row["routedRelationOperationalTargetIDs"])
        all_human_routed = human_node_ids + human_relation_ids
        if not set(exhaustive_empty_ids).issubset(all_human_routed):
            raise BlockAValidationError(f"SCREENING_EXHAUSTIVE_EMPTY_TARGET_NOT_ROUTED:{row['sourceUnitID']}")
        for target_id in all_human_routed:
            if target_id not in targets:
                raise BlockAValidationError(f"ROUTING_UNKNOWN_OPERATIONAL_TARGET:{row['sourceUnitID']}:{target_id}")
            kind, target = targets[target_id]
            expected_kind = "node" if target_id in human_node_ids else "relation"
            if kind != expected_kind:
                raise BlockAValidationError(f"ROUTING_TARGET_KIND_MISMATCH:{row['sourceUnitID']}:{target_id}")
            if target["pilot_treatment"] not in OPEN_TREATMENTS:
                raise BlockAValidationError(f"ROUTING_TARGET_NOT_OPEN:{row['sourceUnitID']}:{target_id}")
            if kind == "node" and not target["direct_instantiation"]:
                raise BlockAValidationError(f"ROUTING_ABSTRACT_CLASS:{row['sourceUnitID']}:{target_id}")
        if not open_unit and all_human_routed:
            raise BlockAValidationError(f"ROUTING_STRUCTURALLY_BLOCKED_UNIT:{row['sourceUnitID']}")
        for field, vocabulary in (("expectedAssertionDensity", DENSITIES), ("expectedRelationDensity", DENSITIES), ("routingComplexity", ROUTING_COMPLEXITIES)):
            if row[field] not in vocabulary:
                raise BlockAValidationError(f"SCREENING_INVALID_CONTROLLED_VALUE:{row['sourceUnitID']}:{field}")
            if open_unit and row[field] == "not_applicable":
                raise BlockAValidationError(f"SCREENING_OPEN_UNIT_NOT_APPLICABLE:{row['sourceUnitID']}:{field}")
            if not open_unit and row[field] != "not_applicable":
                raise BlockAValidationError(f"SCREENING_BLOCKED_UNIT_APPLICABILITY:{row['sourceUnitID']}:{field}")
        distributed = _parse_bool(row["distributedEvidenceLikely"], "distributedEvidenceLikely")
        section_context = _parse_bool(row["sectionContextUseful"], "sectionContextUseful")
        endpoint = _parse_bool(row["deterministicEndpointLikely"], "deterministicEndpointLikely")
        unavailable: list[dict[str, str]] = []
        effective_node_ids: list[str] = []
        effective_relation_ids: list[str] = []
        has_deferred_binding = bool(source["deferredRecordRefs"])
        for kind, human_ids, effective_ids in (
            ("node", human_node_ids, effective_node_ids),
            ("relation", human_relation_ids, effective_relation_ids),
        ):
            for target_id in human_ids:
                treatment = targets[target_id][1]["pilot_treatment"]
                if treatment == "deferred_resolution" and not has_deferred_binding:
                    unavailable.append({
                        "operationalTargetID": target_id,
                        "targetKind": kind,
                        "pilotTreatment": treatment,
                        "reason": DEFERRED_ROUTE_UNAVAILABLE_REASON,
                    })
                else:
                    effective_ids.append(target_id)
        effective_routed_ids = effective_node_ids + effective_relation_ids
        primary_routed_ids = [
            target_id for target_id in effective_routed_ids
            if targets[target_id][1]["pilot_treatment"] in SEMANTIC_TREATMENTS
        ]
        families = sorted({
            target_dimensions[target_id]["reportingFamily"]
            for target_id in primary_routed_ids
            if target_dimensions[target_id]["reportingFamily"] is not None
        })
        strata = sorted({
            target_dimensions[target_id]["samplingStratum"]
            for target_id in primary_routed_ids
            if target_dimensions[target_id]["samplingStratum"] is not None
        })
        routing_status = (
            "routed" if open_unit and primary_routed_ids else
            "reviewed_no_eligible_target" if open_unit else expected_status
        )
        screening.append({
            "screeningSchemaVersion": SCREENING_SCHEMA_VERSION, "screeningVersion": SCREENING_VERSION,
            "sourceArtifactID": source["canonicalArtifactID"], "paperID": source["paperID"],
            "sourceUnitID": source["sourceUnitID"],
            "sourceUnitTextHash": source["textHash"], "sectionID": source["sectionID"],
            "sectionRole": source["sectionRole"], "sourceEligibility": source["eligibility"],
            "screeningReviewerID": row["screeningReviewerID"], "screenedAt": row["screenedAt"],
            "screeningStatus": status, "screeningRationale": row["screeningRationale"],
            "likelyReportingFamilies": families, "likelySamplingStrata": strata,
            "likelyExhaustiveEmptyTargetIDs": exhaustive_empty_ids,
            "likelyRecurringDistinctions": recurring_distinctions,
            "expectedAssertionDensity": row["expectedAssertionDensity"], "expectedRelationDensity": row["expectedRelationDensity"],
            "routingComplexity": row["routingComplexity"], "distributedEvidenceLikely": distributed,
            "sectionContextUseful": section_context,
            "deterministicEndpointLikely": endpoint, "sourceConversionStatus": row["sourceConversionStatus"],
            "screeningNotes": row["screeningNotes"],
        })
        routing.append({
            "routingSchemaVersion": ROUTING_SCHEMA_VERSION, "routingVersion": ROUTING_VERSION,
            "sourceArtifactID": source["canonicalArtifactID"], "paperID": source["paperID"],
            "sourceUnitID": source["sourceUnitID"],
            "sourceUnitTextHash": source["textHash"], "sectionID": source["sectionID"],
            "sectionRole": source["sectionRole"],
            "routingStatus": routing_status,
            "routingBasis": "human_screened" if open_unit else "structurally_blocked",
            "humanScreenedNodeOperationalTargetIDs": human_node_ids,
            "humanScreenedRelationOperationalTargetIDs": human_relation_ids,
            "eligibleNodeOperationalTargetIDs": effective_node_ids,
            "eligibleRelationOperationalTargetIDs": effective_relation_ids,
            "primaryEligibleOperationalTargetIDs": sorted(primary_routed_ids),
            "structurallyUnavailableOperationalTargets": sorted(
                unavailable, key=lambda item: item["operationalTargetID"]
            ),
            "likelyReportingFamilies": families, "likelySamplingStrata": strata,
            "likelyRecurringDistinctions": recurring_distinctions,
            "sourceConversionStatus": row["sourceConversionStatus"],
            "deterministicEndpointRefs": sorted(source["deterministicNodeRefs"] + source["deferredRecordRefs"]),
            "contextFlags": {"sectionContextUseful": section_context, "distributedEvidenceLikely": distributed, "deterministicEndpointLikely": endpoint},
            "menuDiagnostics": {
                "nodeTargetCount": len(effective_node_ids),
                "relationTargetCountBeforeEndpointFiltering": len(effective_relation_ids),
                "humanScreenedNodeTargetCount": len(human_node_ids),
                "humanScreenedRelationTargetCount": len(human_relation_ids),
                "structurallyUnavailableTargetCount": len(unavailable),
            },
            "routingDoesNotAssertPresence": True,
        })
    return screening, routing


def _section_group(role: str) -> str:
    """Map a frozen section role to the selection policy's group."""

    for group, roles in SECTION_GROUP_MAPPING.items():
        if role in roles:
            return group
    return "other_eligible"


def _coverage_tokens(screen: Mapping[str, Any], route: Mapping[str, Any], source: Mapping[str, Any]) -> set[str]:
    """Create prospective selection tokens without annotation or model data."""

    length = "short" if source["characterCount"] < 2000 else "medium" if source["characterCount"] < 6000 else "long"
    load = len(route["eligibleNodeOperationalTargetIDs"]) + len(route["eligibleRelationOperationalTargetIDs"])
    load_band = "low" if load <= 5 else "medium" if load <= 12 else "high"
    tokens = {f"length:{length}", f"section:{_section_group(source['sectionRole'])}", f"routing:{load_band}", f"relation:{screen['expectedRelationDensity']}"}
    tokens.add(f"assertion:{screen['expectedAssertionDensity']}")
    tokens.add(f"routing_complexity:{screen['routingComplexity']}")
    tokens.add(f"conversion:{screen['sourceConversionStatus']}")
    tokens.update(f"family:{value}" for value in screen["likelyReportingFamilies"])
    tokens.update(f"stratum:{value}" for value in screen["likelySamplingStrata"])
    tokens.update(f"distinction:{value}" for value in screen["likelyRecurringDistinctions"])
    tokens.update(f"target:{value}" for value in route["eligibleNodeOperationalTargetIDs"])
    tokens.update(f"target:{value}" for value in route["eligibleRelationOperationalTargetIDs"])
    if screen["likelyExhaustiveEmptyTargetIDs"]:
        tokens.add("likely_exhaustive_empty:true")
    if screen["distributedEvidenceLikely"]:
        tokens.add("distributed:true")
    if screen["sectionContextUseful"]:
        tokens.add("section_context:true")
    if screen["deterministicEndpointLikely"]:
        tokens.add("endpoint:true")
    return tokens


def _select_calibration(
    screening: Sequence[Mapping[str, Any]], routing: Sequence[Mapping[str, Any]], inventory: Sequence[Mapping[str, Any]], count: int = 16
) -> tuple[list[str], dict[str, list[str]]]:
    """Select a varied calibration set with a deterministic greedy objective."""

    s_by = {x["sourceUnitID"]: x for x in screening}
    r_by = {x["sourceUnitID"]: x for x in routing}
    i_by = {x["sourceUnitID"]: x for x in inventory}
    candidates = sorted(uid for uid, route in r_by.items() if route["routingStatus"] == "routed")
    selected: list[str] = []
    covered: set[str] = set()
    exposure: Counter[str] = Counter()
    contribution: dict[str, list[str]] = {}
    while candidates and len(selected) < count:
        def score(uid: str) -> tuple[int, int, str]:
            """Prefer new coverage, then lower artifact exposure, then lexical ID."""

            tokens = _coverage_tokens(s_by[uid], r_by[uid], i_by[uid])
            return (-len(tokens - covered), exposure[i_by[uid]["paperID"]], uid)
        chosen = min(candidates, key=score)
        new = sorted(_coverage_tokens(s_by[chosen], r_by[chosen], i_by[chosen]) - covered)
        contribution[chosen] = new
        covered.update(new)
        exposure[i_by[chosen]["paperID"]] += 1
        selected.append(chosen)
        candidates.remove(chosen)
    return selected, contribution


def compile_reviewed_worklist(root: Path, reviewed_worklist: Path) -> dict[str, Any]:
    """Validate human screening and materialize the remaining Block A artifacts."""

    inventory, profile, manifest = _load_inputs(root)
    with reviewed_worklist.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    screening, routing = _validate_reviewed_rows(
        rows, inventory, profile, _conversion_by_paper(manifest)
    )
    output = root / "data/curation/papers/pilot1"
    screening_bytes = b"".join(canonical_json(record) for record in screening)
    routing_bytes = b"".join(canonical_json(record) for record in routing)
    _write_if_changed(output / "publication_pilot1_screening.jsonl", screening_bytes)
    _write_if_changed(output / "publication_pilot1_unit_routing.jsonl", routing_bytes)
    s_by, r_by, i_by = ({x["sourceUnitID"]: x for x in values} for values in (screening, routing, inventory))
    calibration, contribution = _select_calibration(screening, routing, inventory)
    calibration_set = set(calibration)
    artifact_quota_policy = build_artifact_quota_role_policy(manifest)
    quota_by_paper = {
        artifact["paperID"]: artifact
        for artifact in artifact_quota_policy["artifacts"]
    }
    orders: dict[str, list[dict[str, Any]]] = {}
    coverage_rows: list[dict[str, Any]] = []
    for paper_id in sorted({x["paperID"] for x in inventory}):
        candidates = sorted(uid for uid, route in r_by.items() if route["paperID"] == paper_id and route["routingStatus"] == "routed" and uid not in calibration_set)
        covered: set[str] = set()
        ordered: list[dict[str, Any]] = []
        while candidates:
            chosen = min(candidates, key=lambda uid: (
                -len(_coverage_tokens(s_by[uid], r_by[uid], i_by[uid]) - covered),
                -(len(r_by[uid]["eligibleNodeOperationalTargetIDs"]) + len(r_by[uid]["eligibleRelationOperationalTargetIDs"])),
                uid,
            ))
            new = sorted(_coverage_tokens(s_by[chosen], r_by[chosen], i_by[chosen]) - covered)
            tier = "must_cover" if any(x.startswith(("family:", "stratum:", "section:")) for x in new) else "preferred" if new else "reserve"
            ordered.append({
                "sourceArtifactID": i_by[chosen]["canonicalArtifactID"], "paperID": paper_id,
                "artifactQuotaRole": quota_by_paper[paper_id]["artifactQuotaRole"],
                "quotaBearing": quota_by_paper[paper_id]["quotaBearing"],
                "postCalibrationAllowedBlockBPartitions": quota_by_paper[paper_id]["postCalibrationAllowedBlockBPartitions"],
                "sourceUnitID": chosen, "sourceUnitTextHash": i_by[chosen]["textHash"],
                "candidateRankWithinArtifact": len(ordered) + 1, "selectionTier": tier,
                "coverageContribution": new, "sectionGroup": _section_group(i_by[chosen]["sectionRole"]),
                "likelyReportingFamilies": s_by[chosen]["likelyReportingFamilies"],
                "likelySamplingStrata": s_by[chosen]["likelySamplingStrata"],
                "likelyRecurringDistinctions": s_by[chosen]["likelyRecurringDistinctions"],
                "expectedAssertionDensity": s_by[chosen]["expectedAssertionDensity"],
                "expectedRelationDensity": s_by[chosen]["expectedRelationDensity"],
                "routingComplexity": s_by[chosen]["routingComplexity"],
                "sourceConversionStatus": s_by[chosen]["sourceConversionStatus"],
                "expectedSpecialConditions": sorted(x for x in (
                    f"source_conversion:{s_by[chosen]['sourceConversionStatus']}",
                    "distributed_evidence" if s_by[chosen]["distributedEvidenceLikely"] else "",
                    "section_context_useful" if s_by[chosen]["sectionContextUseful"] else "",
                    "deterministic_endpoint" if s_by[chosen]["deterministicEndpointLikely"] else "",
                ) if x),
                "deterministicTieBreakKey": chosen,
            })
            covered.update(_coverage_tokens(s_by[chosen], r_by[chosen], i_by[chosen]))
            candidates.remove(chosen)
        orders[paper_id] = ordered
    for paper_id, order_rows in orders.items():
        quota_role = quota_by_paper[paper_id]
        if quota_role["quotaBearing"] and len(order_rows) < 5:
            raise BlockAValidationError(
                f"BLOCK_A_QUOTA_BEARING_ARTIFACT_CAPACITY_BELOW_GREEN:{paper_id}:{len(order_rows)}"
            )
    for source in inventory:
        uid = source["sourceUnitID"]
        route, screen = r_by[uid], s_by[uid]
        partition = (
            "calibration" if uid in calibration_set else
            "post_gate0_candidate" if route["routingStatus"] == "routed" else
            "not_open_annotation_target" if route["routingStatus"] == "reviewed_no_eligible_target" else
            route["routingStatus"]
        )
        coverage_rows.append({
            "targetCoverageMatrixVersion": TARGET_COVERAGE_MATRIX_VERSION,
            "blockAInfrastructureVersion": BLOCK_A_INFRASTRUCTURE_VERSION,
            "routingVersion": ROUTING_VERSION,
            "selectionPolicyVersion": SELECTION_POLICY_VERSION,
            "sourceArtifactID": source["canonicalArtifactID"], "paperID": source["paperID"],
            "artifactQuotaRole": quota_by_paper[source["paperID"]]["artifactQuotaRole"],
            "quotaBearing": str(quota_by_paper[source["paperID"]]["quotaBearing"]).lower(),
            "postCalibrationAllowedBlockBPartitions": _join_multi(
                quota_by_paper[source["paperID"]]["postCalibrationAllowedBlockBPartitions"]
            ),
            "sourceUnitID": uid, "sectionTitle": source["sectionTitleRaw"] or source["sectionTitleNormalized"],
            "sourceEligibility": source["eligibility"], "partitionStatus": partition,
            "eligibleNodeOperationalTargetIDs": _join_multi(route["eligibleNodeOperationalTargetIDs"]),
            "eligibleRelationOperationalTargetIDs": _join_multi(route["eligibleRelationOperationalTargetIDs"]),
            "structurallyUnavailableOperationalTargetIDs": _join_multi(
                item["operationalTargetID"]
                for item in route["structurallyUnavailableOperationalTargets"]
            ),
            "likelyReportingFamilies": _join_multi(screen["likelyReportingFamilies"]), "likelySamplingStrata": _join_multi(screen["likelySamplingStrata"]),
            "screeningVersion": SCREENING_VERSION, "screeningStatus": screen["screeningStatus"], "sourceConversionStatus": screen["sourceConversionStatus"],
            "observedDeterministicMetadata": _join_multi(source["contentTypes"]),
            "expectedSemanticCoverage": _join_multi(screen["likelyReportingFamilies"]), "coverageStatus": "prospective" if route["routingStatus"] == "routed" else "not_applicable",
            "likelyRecurringDistinctions": _join_multi(screen["likelyRecurringDistinctions"]),
            "expectedAssertionDensity": screen["expectedAssertionDensity"],
            "expectedRelationDensity": screen["expectedRelationDensity"],
            "routingComplexity": screen["routingComplexity"],
            "expectedSpecialCondition": _join_multi(x for x in (
                f"source_conversion:{screen['sourceConversionStatus']}",
                "distributed_evidence" if screen["distributedEvidenceLikely"] else "",
                "section_context_useful" if screen["sectionContextUseful"] else "",
                "deterministic_endpoint" if screen["deterministicEndpointLikely"] else "",
            ) if x),
            "primaryEvaluationRepresentationSatisfied": "pending_block_b",
        })
    coverage_stream = io.StringIO(newline="")
    writer = csv.DictWriter(coverage_stream, fieldnames=list(coverage_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(coverage_rows)
    _write_if_changed(output / "publication_pilot1_target_coverage_matrix.csv", coverage_stream.getvalue().encode())
    screening_hash, routing_hash = hashlib.sha256(screening_bytes).hexdigest(), hashlib.sha256(routing_bytes).hexdigest()
    reviewed_policy = selection_policy(artifact_quota_policy)
    reviewed_policy["status"] = "candidate_for_review"
    reviewed_policy["screening"]["hash"] = screening_hash
    reviewed_policy["routing"]["hash"] = routing_hash
    _write_if_changed(output / "publication_pilot1_selection_policy.yaml", _yaml_bytes(reviewed_policy))
    selection_policy_hash = sha256_file(output / "publication_pilot1_selection_policy.yaml")
    order = {
        "candidateOrderVersion": CANDIDATE_ORDER_VERSION, "status": "candidate_for_review",
        "sourceUnitInventoryHash": INVENTORY_HASH, "screeningHash": screening_hash,
        "routingVersion": ROUTING_VERSION, "routingHash": routing_hash,
        "selectionPolicyHash": selection_policy_hash,
        "artifactQuotaRolePolicyVersion": ARTIFACT_QUOTA_ROLE_POLICY_VERSION,
        "artifactQuotaRoles": artifact_quota_policy["artifacts"],
        "ordersByArtifact": orders,
    }
    _write_if_changed(output / "publication_pilot1_pre_gate0_candidate_order.json", canonical_json(order))
    manifest = {
        "calibrationManifestVersion": CALIBRATION_MANIFEST_VERSION, "status": "candidate_for_review", "sourceUnitInventoryHash": INVENTORY_HASH,
        "screeningHash": screening_hash, "routingVersion": ROUTING_VERSION,
        "routingHash": routing_hash,
        "selectionPolicyHash": selection_policy_hash,
        "artifactQuotaRolePolicyVersion": ARTIFACT_QUOTA_ROLE_POLICY_VERSION,
        "calibrationSourceUnitIDs": calibration, "sourceUnitHashes": {uid: i_by[uid]["textHash"] for uid in calibration},
        "artifactExposure": {
            paper_id: {
                "sourceArtifactID": next(i_by[uid]["canonicalArtifactID"] for uid in calibration if i_by[uid]["paperID"] == paper_id),
                "unitCount": count,
            }
            for paper_id, count in sorted(Counter(i_by[uid]["paperID"] for uid in calibration).items())
        },
        "coverageSummary": sorted({token for uid in calibration for token in _coverage_tokens(s_by[uid], r_by[uid], i_by[uid])}),
        "selectionRationale": {uid: contribution[uid] for uid in calibration},
        "timingProtocolRef": "publication_pilot1_gate0_policy.yaml", "createdAt": "deterministic_compilation; repository history records wall-clock creation",
    }
    _write_if_changed(output / "publication_pilot1_calibration_manifest.json", canonical_json(manifest))
    return {"screeningCount": len(screening), "routingCount": len(routing), "coverageCount": len(coverage_rows), "candidateCount": sum(map(len, orders.values())), "calibrationCount": len(calibration)}
