"""Build the offline M2-C2C generic ``mentions`` impact audit.

This module reads only frozen ontology, Publication screening/routing,
calibration, and M2 development artifacts.  It produces prospective audit
records without changing ontology declarations, historical human decisions,
model output, or graph data.  It has no provider or network execution path.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.request_builder import (  # noqa: E402
    ONTOLOGY_SPEC_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    canonical_json_file,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (  # noqa: E402
    C1B_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR as C2A_OUTPUT_DIR,
    _tree_snapshot,
)


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c2c"
C2B_OUTPUT_DIR = PROJECT_ROOT / "data/curation/papers/m2/c2b"
PILOT1_DIR = PROJECT_ROOT / "data/curation/papers/pilot1"
REVIEWED_SCREENING_CSV = (
    PROJECT_ROOT
    / "var/publication_pilot1_screening/exports/"
    "publication_pilot1_screening_worklist_reviewed.csv"
)
SCREENING_JSONL = PILOT1_DIR / "publication_pilot1_screening.jsonl"
ROUTING_JSONL = PILOT1_DIR / "publication_pilot1_unit_routing.jsonl"
SCREENING_WORKLIST = PILOT1_DIR / "publication_pilot1_screening_worklist.csv"
CALIBRATION_MANIFEST = PILOT1_DIR / "publication_pilot1_calibration_manifest.json"
C2B_CANDIDATES = C2B_OUTPUT_DIR / "publication_node_semantic_review_candidates.json"
C2B_EVIDENCE_GROUPS = (
    C2B_OUTPUT_DIR / "publication_node_semantic_review_evidence_groups.json"
)

AUDIT_LABELS = [
    "AUDIT_ONLY",
    "NO_ONTOLOGY_CHANGE",
    "NO_SCREENING_CHANGE",
    "NO_CALIBRATION_CHANGE",
    "NO_MODEL_CALL",
]
STATUS = "researcher_review_pending"

DISCOURSE_CLASSES = [
    "Background",
    "Theme",
    "ResearchProblem",
    "ResearchQuestion",
    "ResearchGoal",
    "ResearchSignificance",
    "Definition",
    "TheoreticalBasis",
    "Method",
    "Experiment",
    "Examples",
    "Finding",
    "Discussion",
    "RelatedResearch",
    "Limitation",
    "Conclusion",
    "Contribution",
    "FutureWork",
    "Hypothesis",
    "Claim",
    "DataDescription",
]

RANGE_GROUPS: dict[str, list[str]] = {
    "ComputationalModelAndSubtypes": [
        "ComputationalModel",
        "ProcessBasedModel",
        "ConceptualModel",
        "StatisticalModel",
        "MLModel",
    ],
    "Tool": ["Tool"],
    "DatasetMention": ["DatasetMention"],
    "DatasetResource": ["DatasetResource"],
    "Variable": ["Variable"],
    "Concept": ["Concept"],
    "HydrologicFeatureAndSubtypes": [
        "HydrologicFeature",
        "Watershed",
        "RiverReach",
        "Gauge",
        "WaterBody",
        "Aquifer",
        "VPU",
    ],
    "NamedPlace": ["NamedPlace"],
    "EvaluationMetric": ["EvaluationMetric"],
    "Parameter": ["Parameter"],
    "Algorithm": ["Algorithm"],
    "Repository": ["Repository"],
}
MENTIONABLE_CLASS_NAMES = {
    class_name for values in RANGE_GROUPS.values() for class_name in values
}

STRONGER_BY_RANGE_GROUP: dict[str, list[str]] = {
    "ComputationalModelAndSubtypes": [
        "usesModel",
        "appliesTo",
        "describesModel",
        "implementsMethod",
    ],
    "Tool": ["usesTool", "describesTool", "catalogs"],
    "DatasetMention": ["usesDataset"],
    "DatasetResource": [
        "usesDataset",
        "referencesDataset",
        "describesDataset",
    ],
    "Variable": ["containsVariable"],
    "Concept": ["hasSubject"],
    "HydrologicFeatureAndSubtypes": ["studiesFeature", "referencesFeature"],
    "NamedPlace": ["studiesPlace"],
    "EvaluationMetric": ["reportsMetric", "evaluates"],
    "Parameter": ["hasParameter", "usesParameter"],
    "Algorithm": ["usesAlgorithm", "describesAlgorithm"],
    "Repository": [
        "referencesRepository",
        "hasCodeRepository",
        "documents",
        "implementedBy",
    ],
}

RELEVANT_RELATION_NAMES = {
    "hasSubject",
    "reports",
    "relatesTo",
    "usesModel",
    "appliesTo",
    "usesTool",
    "mentionsVariable",
    "studiesFeature",
    "studiesPlace",
    "hasSpatialCoverage",
    "usesDataset",
    "mentionsModel",
    "mentionsDataset",
    "reportsMetric",
    "evaluates",
    "hasParameter",
    "usesAlgorithm",
    "referencesDataset",
    "mentionsConcept",
    "mentionsTool",
    "referencesRepository",
    "hasCodeRepository",
    "referencesFeature",
    "containsVariable",
    "isExecutedBy",
    "executes",
    "describesAlgorithm",
    "usesParameter",
    "mentionsParameter",
    "describesTool",
    "describesModel",
    "catalogs",
    "hasComponent",
    "describesDataset",
    "implementsMethod",
    "documents",
    "implementedBy",
    "consolidatesTo",
}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one deterministic canonical JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_file(value))


def _with_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    """Attach a canonical self-content hash without recursive inclusion."""

    result = deepcopy(dict(value))
    result.pop("canonicalContentSha256", None)
    result["canonicalContentSha256"] = sha256_bytes(canonical_json(result))
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one UTF-8 JSON Lines authority."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _as_list(value: Any) -> list[str]:
    """Normalize a scalar or list ontology endpoint declaration to strings."""

    return [str(item) for item in value] if isinstance(value, list) else [str(value)]


def _pipe_values(value: str) -> list[str]:
    """Parse the frozen reviewed-screening pipe-delimited target cells."""

    return [] if not value else value.split("|")


def _module_for_relation(relation_id: str) -> str:
    """Return the frozen artifact/global module represented by a relation ID."""

    if relation_id.startswith("C-DC"):
        return "documentation"
    if relation_id.startswith("C-P"):
        return "publication"
    if relation_id.startswith("C-D"):
        return "dataset"
    if relation_id.startswith("C-C"):
        return "repository"
    if relation_id.startswith("D-"):
        return "global_cross_artifact"
    return "common_or_provenance"


def _semantic_strength(relation: Mapping[str, Any]) -> str:
    """Classify only the relation's documented structural semantic strength."""

    name = str(relation["name"])
    if name.startswith("mentions"):
        return "weak_explicit_mention"
    if name.startswith("references"):
        return "explicit_reference_stronger_than_generic_mention"
    if name in {"hasSubject", "hasSpatialCoverage", "consolidatesTo"}:
        return "metadata_or_consolidation_not_generic_mention"
    return "role_specific_stronger_than_generic_mention"


def _provenance() -> dict[str, Any]:
    """Bind the audit to all immutable ontology and project inputs."""

    if not REVIEWED_SCREENING_CSV.exists():
        raise FileNotFoundError(
            "authoritative reviewed screening CSV is unavailable; audit cannot proceed"
        )
    return {
        "ontologySpecSha256": sha256_bytes(ONTOLOGY_SPEC_PATH.read_bytes()),
        "ontologyInventorySha256": sha256_bytes(
            (PROJECT_ROOT / "docs/ontology_inventory.md").read_bytes()
        ),
        "publicationTargetInventorySha256": sha256_bytes(
            TARGET_INVENTORY_PATH.read_bytes()
        ),
        "reviewedScreeningCsvSha256": sha256_bytes(
            REVIEWED_SCREENING_CSV.read_bytes()
        ),
        "screeningWorklistSha256": sha256_bytes(SCREENING_WORKLIST.read_bytes()),
        "compiledScreeningJsonlSha256": sha256_bytes(SCREENING_JSONL.read_bytes()),
        "compiledRoutingJsonlSha256": sha256_bytes(ROUTING_JSONL.read_bytes()),
        "calibrationManifestSha256": sha256_bytes(
            CALIBRATION_MANIFEST.read_bytes()
        ),
        "c1bTreeSha256": _tree_snapshot(C1B_OUTPUT_DIR)["treeInventorySha256"],
        "c2aTreeSha256": _tree_snapshot(C2A_OUTPUT_DIR)["treeInventorySha256"],
        "c2bTreeSha256": _tree_snapshot(C2B_OUTPUT_DIR)["treeInventorySha256"],
        "c2bCandidateArtifactSha256": sha256_bytes(C2B_CANDIDATES.read_bytes()),
        "c2bEvidenceGroupArtifactSha256": sha256_bytes(
            C2B_EVIDENCE_GROUPS.read_bytes()
        ),
        "sourceScope": "preserved local project authorities only",
        "providerCalls": 0,
        "externalDataUsed": False,
    }


def _base(role: str, provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Return common audit-only labels and immutable input provenance."""

    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": role,
        "status": STATUS,
        "auditLabels": list(AUDIT_LABELS),
        "auditOnly": True,
        "ontologyChanged": False,
        "screeningChanged": False,
        "calibrationChanged": False,
        "modelCallMade": False,
        "semanticAdjudicationPerformed": False,
        "provenance": deepcopy(dict(provenance)),
    }


def build_current_ontology_audit(
    spec: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit current relevant and all specialized mention relations."""

    all_relations = list(spec["relations"])
    mention_relations = [
        relation
        for relation in all_relations
        if str(relation["name"]).startswith("mentions")
        and str(relation["name"]) != "mentions"
    ]
    relevant = [
        relation
        for relation in all_relations
        if str(relation["name"]) in RELEVANT_RELATION_NAMES
        or "mention" in str(relation["name"]).lower()
    ]

    def project(relation: Mapping[str, Any]) -> dict[str, Any]:
        """Project one frozen relation without changing its semantics."""

        return {
            "relationID": relation["id"],
            "name": relation["name"],
            "domain": deepcopy(relation["domain"]),
            "range": deepcopy(relation["range"]),
            "status": relation["status"],
            "statusNote": relation.get("status_note"),
            "module": _module_for_relation(str(relation["id"])),
            "consolidationEnabled": relation.get("consol") is True,
            "globalMapping": relation.get("maps_to"),
            "subpropertyOf": relation.get("subproperty_of"),
            "evidenceAuthority": relation.get("evidence"),
            "currentSemanticStrength": _semantic_strength(relation),
            "frozenNote": relation.get("note"),
        }

    return _with_hash(
        {
            **_base("generic_mentions_current_ontology_audit", provenance),
            "ontologyRelationCount": len(all_relations),
            "auditRelevantRelationCount": len(relevant),
            "relations": [project(row) for row in relevant],
            "allMentionsXRelationCount": len(mention_relations),
            "allMentionsXRelations": [project(row) for row in mention_relations],
            "artifactModulesWithMentionsX": sorted(
                {_module_for_relation(str(row["id"])) for row in mention_relations}
            ),
            "observation": (
                "The frozen ontology has specialized mention relations in all four "
                "artifact modules but no generic mentions superproperty."
            ),
            "proposalMadeHere": False,
        }
    )


def _relations_for_classes(
    relations: Iterable[Mapping[str, Any]], class_names: set[str]
) -> list[Mapping[str, Any]]:
    """Return relations whose frozen range intersects the supplied class names."""

    return [
        relation
        for relation in relations
        if set(_as_list(relation["range"])) & class_names
    ]


def build_domain_range_audit(
    spec: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit a bounded non-``owl:Thing`` range and non-Paper-only domains."""

    relations = list(spec["relations"])
    range_rows = []
    for group_name, class_names in RANGE_GROUPS.items():
        classes = set(class_names)
        relevant = _relations_for_classes(relations, classes)
        stronger = sorted(
            {
                str(row["name"])
                for row in relevant
                if str(row["name"]) in STRONGER_BY_RANGE_GROUP[group_name]
            }
        )
        mentions = sorted(
            {
                str(row["name"])
                for row in relevant
                if str(row["name"]).startswith("mentions")
            }
        )
        for class_name in class_names:
            range_rows.append(
                {
                    "classGroup": group_name,
                    "ontologyClass": class_name,
                    "existingStrongerRoleRelations": stronger,
                    "existingSpecializedMentionRelations": mentions,
                    "representationGapWhenOnlyExplicitlyMentioned": True,
                    "genericMentionsClosesGap": True,
                    "candidateGenericMentionRangeDecision": "inside",
                    "reason": (
                        "An explicit name-bearing occurrence can be represented without "
                        "asserting use, study role, evaluation, configuration, or reference."
                    ),
                    "currentRelationIDs": sorted(str(row["id"]) for row in relevant),
                }
            )
    container_domains = []
    for class_name in ("Paper", "Repository", "DocumentationPage", "DatasetResource"):
        existing = sorted(
            str(row["id"])
            for row in relations
            if class_name in _as_list(row["domain"])
            and (
                str(row["name"]).startswith("mentions")
                or str(row["name"]) in RELEVANT_RELATION_NAMES
            )
        )
        container_domains.append(
            {
                "ontologyClass": class_name,
                "granularity": "artifact_or_source_container",
                "genericMentionMeaning": "meaningful",
                "existingRelevantRelationIDs": existing,
                "redundancyRule": "stronger accepted relation suppresses explicit generic fallback",
                "semanticallyInappropriate": False,
            }
        )
    stronger_by_discourse = {
        "Method": [
            "usesModel",
            "appliesTo",
            "studiesFeature",
            "studiesPlace",
            "hasParameter",
            "usesAlgorithm",
        ],
        "Experiment": ["reportsMetric", "hasParameter"],
        "Finding": ["reportsMetric"],
        "DataDescription": ["mentionsVariable"],
        "RelatedResearch": ["relatesTo"],
    }
    discourse_domains = [
        {
            "ontologyClass": class_name,
            "granularity": "fine_grained_semantic_container",
            "genericMentionMeaning": "meaningful_with_strict_evidence_containment",
            "existingStrongerOrSpecializedRelations": stronger_by_discourse.get(
                class_name, []
            ),
            "redundantWhenStrongerAccepted": bool(
                stronger_by_discourse.get(class_name)
            ),
            "semanticallyInappropriate": False,
        }
        for class_name in DISCOURSE_CLASSES
    ]
    return _with_hash(
        {
            **_base("generic_mentions_domain_range_audit", provenance),
            "rangeStrategy": {
                "owlThingUsed": False,
                "candidateRangeClassGroups": list(RANGE_GROUPS),
                "rangeRows": range_rows,
                "coverageScope": sorted(MENTIONABLE_CLASS_NAMES),
            },
            "domainStrategy": {
                "paperOnly": False,
                "artifactContainers": container_domains,
                "fineGrainedSemanticContainers": discourse_domains,
                "provisionalFormalizationChoice": (
                    "Use an explicitly governed named mentionable-entity range and an "
                    "explicitly governed container domain, or equivalent reviewed class "
                    "expressions; do not use owl:Thing merely for convenience."
                ),
            },
        }
    )


def build_option_comparison(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Compare LLM-authored and deterministic pipeline-derived implementations."""

    precedence = [
        ("Method", "Algorithm", "usesAlgorithm"),
        ("Paper|Method", "NamedPlace", "studiesPlace"),
        ("Paper|Method", "HydrologicFeature", "studiesFeature"),
        ("Finding|Experiment", "EvaluationMetric", "reportsMetric|evaluates"),
        ("Method|Experiment|ComputationalModel", "Parameter", "hasParameter"),
        ("Paper", "ComputationalModel", "usesModel|mentionsModel"),
        ("Paper", "Tool", "usesTool|mentionsTool"),
        (
            "Paper",
            "DatasetMention|DatasetResource",
            "usesDataset|referencesDataset|mentionsDataset",
        ),
        ("Paper", "Concept", "hasSubject|mentionsConcept"),
        ("Paper", "Repository", "hasCodeRepository|referencesRepository"),
        ("DataDescription", "Variable", "mentionsVariable"),
    ]
    return _with_hash(
        {
            **_base("generic_mentions_option_comparison", provenance),
            "optionA": {
                "name": "LLM-authored generic relation",
                "productionResponsibility": "llm",
                "emissionMode": "llm_candidate",
                "requiresIndependentEdgeEvidence": True,
                "requiresNewScreeningOrProspectiveRoutingDecision": True,
                "requiresNewCalibrationInstructionAndDecision": True,
                "advantages": ["independent relation assertion is explicit"],
                "risks": [
                    "conflicts with no-repeat screening and calibration constraints",
                    "duplicates node evidence that already proves lexical mention",
                    "adds output and annotation burden",
                ],
            },
            "optionB": {
                "name": "pipeline-derived generic relation",
                "productionResponsibility": "pipeline_generated",
                "emissionMode": "pipeline_derived",
                "requiresIndependentEdgeEvidence": False,
                "paperRule": (
                    "Derive Paper -> mentions -> entity only from an accepted entity "
                    "node with valid evidence whose trusted provenance is that Paper."
                ),
                "discourseRule": (
                    "Derive DiscourseElement -> mentions -> entity only when both accepted "
                    "nodes belong to the same canonical Paper, both evidence records are "
                    "valid, and an entity evidence occurrence is wholly contained in a "
                    "discourse evidence occurrence in unit and document coordinates."
                ),
                "endpointCoexistenceAloneSufficient": False,
                "analogy": (
                    "Matches the accepted C-P05 reports pattern: accepted node provenance "
                    "supports a deterministic structural relation without an independent "
                    "LLM edge decision."
                ),
                "avoidsNewHumanDecision": True,
            },
            "precedencePolicy": {
                "genericMaterializationMode": "fallback_only",
                "specializedMentionsXAsSubproperties": True,
                "materializeParentAndChildTogether": False,
                "owlSuperpropertyInferencePermitted": True,
                "rows": [
                    {
                        "sourcePattern": source,
                        "targetPattern": target,
                        "strongerRelationPrecedence": stronger,
                        "genericAction": "suppress explicit generic edge when stronger edge is accepted",
                    }
                    for source, target, stronger in precedence
                ],
            },
            "auditRecommendation": "OPTION_B_PIPELINE_DERIVED_GENERIC_RELATION",
            "recommendationImplemented": False,
        }
    )


def _mentionable_target_index(
    profile: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Derive mentionable Publication node targets solely from the range audit."""

    result = {}
    for target in profile["node_targets"]:
        names = sorted(
            {
                str(row["name"])
                for row in target["formal_classes"]
                if str(row["name"]) in MENTIONABLE_CLASS_NAMES
            }
        )
        if names:
            result[str(target["operational_id"])] = {
                "ontologyClasses": names,
                "pilotTreatment": target["pilot_treatment"],
                "emissionMode": target["emission_mode"],
            }
    return result


def build_screening_recoverability(
    profile: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Derive prospective applicability from immutable human node routing decisions."""

    with REVIEWED_SCREENING_CSV.open(newline="", encoding="utf-8") as handle:
        reviewed_rows = list(csv.DictReader(handle))
    screening_rows = _read_jsonl(SCREENING_JSONL)
    routing_rows = _read_jsonl(ROUTING_JSONL)
    if len(reviewed_rows) != 358 or len(screening_rows) != 358 or len(routing_rows) != 358:
        raise ValueError("Pilot 1 screening/routing authorities must each contain 358 rows")
    reviewed_by_id = {row["sourceUnitID"]: row for row in reviewed_rows}
    screening_by_id = {row["sourceUnitID"]: row for row in screening_rows}
    human_routes = [row for row in routing_rows if row["routingBasis"] == "human_screened"]
    if len(human_routes) != 267:
        raise ValueError(f"expected 267 human-screened units, found {len(human_routes)}")
    mentionable = _mentionable_target_index(profile)
    rows = []
    by_class: Counter[str] = Counter()
    by_paper: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    for route in human_routes:
        source_unit_id = str(route["sourceUnitID"])
        reviewed = reviewed_by_id[source_unit_id]
        screening = screening_by_id[source_unit_id]
        reviewed_nodes = _pipe_values(reviewed["routedNodeOperationalTargetIDs"])
        reviewed_relations = _pipe_values(
            reviewed["routedRelationOperationalTargetIDs"]
        )
        if reviewed_nodes != route["humanScreenedNodeOperationalTargetIDs"]:
            raise ValueError(f"reviewed node-route drift for {source_unit_id}")
        if reviewed_relations != route["humanScreenedRelationOperationalTargetIDs"]:
            raise ValueError(f"reviewed relation-route drift for {source_unit_id}")
        if screening["screeningStatus"] != "reviewed":
            raise ValueError(f"compiled screening is not reviewed for {source_unit_id}")
        causes = sorted(set(reviewed_nodes) & set(mentionable))
        classes = sorted(
            {
                class_name
                for target_id in causes
                for class_name in mentionable[target_id]["ontologyClasses"]
            }
        )
        applicable = bool(causes)
        if applicable:
            by_paper[str(route["paperID"])] += 1
            by_role[str(route["sectionRole"])] += 1
            by_class.update(classes)
        rows.append(
            {
                "sourceUnitID": source_unit_id,
                "paperID": route["paperID"],
                "sourceArtifactID": route["sourceArtifactID"],
                "sectionRole": route["sectionRole"],
                "humanScreenedNodeOperationalTargetIDs": reviewed_nodes,
                "humanScreenedRelationOperationalTargetIDs": reviewed_relations,
                "effectiveNodeOperationalTargetIDs": route[
                    "eligibleNodeOperationalTargetIDs"
                ],
                "effectiveRelationOperationalTargetIDs": route[
                    "eligibleRelationOperationalTargetIDs"
                ],
                "derivedGenericMentionApplicability": applicable,
                "derivationCausingNodeTargetIDs": causes,
                "derivationCausingOntologyClasses": classes,
                "derivationIsNewHumanDecision": False,
                "derivationAssertsMentionPresence": False,
                "historicalArtifactsModified": False,
            }
        )
    recoverable = sum(row["derivedGenericMentionApplicability"] for row in rows)
    return _with_hash(
        {
            **_base("generic_mentions_screening_recoverability", provenance),
            "humanScreenedUnitCount": len(rows),
            "mentionableNodeTargetCount": len(mentionable),
            "mentionableNodeTargets": mentionable,
            "recoverableUnitCount": recoverable,
            "recoverableUnitPercentage": round(100 * recoverable / len(rows), 6),
            "notRecoverableUnitCount": len(rows) - recoverable,
            "unitsWithMultipleMentionableNodeTargets": sum(
                len(row["derivationCausingNodeTargetIDs"]) >= 2 for row in rows
            ),
            "recoverableCountsByOntologyClass": dict(sorted(by_class.items())),
            "recoverableCountsByPaper": dict(sorted(by_paper.items())),
            "recoverableCountsBySectionRole": dict(sorted(by_role.items())),
            "units": rows,
            "optionBNeedsRoutingAugmentation": False,
            "optionBReason": (
                "Pipeline derivation follows accepted entity-node evidence; the derived "
                "screening augmentation is necessary only to approximate Option A routing."
            ),
        }
    )


def build_calibration_impact(
    profile: Mapping[str, Any], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    """Audit the frozen 16-unit calibration implications without modifying it."""

    calibration = load_json_object(CALIBRATION_MANIFEST)
    routing = {row["sourceUnitID"]: row for row in _read_jsonl(ROUTING_JSONL)}
    mentionable = _mentionable_target_index(profile)
    rows = []
    for source_unit_id in calibration["calibrationSourceUnitIDs"]:
        route = routing[source_unit_id]
        causes = sorted(
            set(route["eligibleNodeOperationalTargetIDs"]) & set(mentionable)
        )
        rows.append(
            {
                "sourceUnitID": source_unit_id,
                "mentionableEffectiveNodeTargetIDs": causes,
                "optionAWouldAddHumanRelationDecision": bool(causes),
                "optionBAddsHumanRelationDecision": False,
            }
        )
    contract_paths = [
        PROJECT_ROOT / "schemas/publication_pilot1_annotation_record.schema.json",
        PROJECT_ROOT / "docs/publication_pilot1_annotation_calibration_handbook.md",
        PROJECT_ROOT / "docs/publication_pilot1_annotation_calibration_interface.md",
        PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines.md",
    ]
    return _with_hash(
        {
            **_base("generic_mentions_calibration_impact", provenance),
            "calibrationUnitCount": len(rows),
            "units": rows,
            "optionAAffectedCalibrationUnitCount": sum(
                row["optionAWouldAddHumanRelationDecision"] for row in rows
            ),
            "optionACreatesInstructionMismatch": True,
            "optionAReason": (
                "Generic mentions was not an available calibration relation decision."
            ),
            "optionBAvoidsInstructionMismatch": True,
            "optionBReason": (
                "No new annotator decision is requested; derivation occurs only after "
                "accepted node evidence and provenance checks."
            ),
            "repeatCalibrationRequiredUnderOptionB": False,
            "nodeEligibilityPolicyIssueIsSeparate": True,
            "contractAuthorityHashes": {
                str(path.relative_to(PROJECT_ROOT)): sha256_bytes(path.read_bytes())
                for path in contract_paths
            },
        }
    )


def strict_evidence_containment(
    entity_candidate: Mapping[str, Any], discourse_candidate: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Return exact valid evidence-occurrence containment bindings deterministically."""

    if entity_candidate["sourceUnitID"] != discourse_candidate["sourceUnitID"]:
        return []
    if not entity_candidate["counterfactualEvidenceValid"]:
        return []
    if not discourse_candidate["counterfactualEvidenceValid"]:
        return []
    bindings = []
    for entity_evidence in entity_candidate["evidence"]:
        for discourse_evidence in discourse_candidate["evidence"]:
            unit_contained = (
                discourse_evidence["startOffsetInUnit"]
                <= entity_evidence["startOffsetInUnit"]
                and entity_evidence["endOffsetInUnit"]
                <= discourse_evidence["endOffsetInUnit"]
            )
            document_contained = (
                discourse_evidence["startOffsetInDocument"]
                <= entity_evidence["startOffsetInDocument"]
                and entity_evidence["endOffsetInDocument"]
                <= discourse_evidence["endOffsetInDocument"]
            )
            if unit_contained and document_contained:
                bindings.append(
                    {
                        "entityEvidenceSpanID": entity_evidence["evidenceSpanID"],
                        "discourseEvidenceSpanID": discourse_evidence["evidenceSpanID"],
                    }
                )
    return sorted(
        bindings,
        key=lambda row: (
            row["entityEvidenceSpanID"], row["discourseEvidenceSpanID"]
        ),
    )


def build_devset_empirical_impact(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Measure prospective generic edges from preserved C1B/C2B candidates offline."""

    candidate_artifact = load_json_object(C2B_CANDIDATES)
    evidence_artifact = load_json_object(C2B_EVIDENCE_GROUPS)
    candidates = list(candidate_artifact["rows"])
    if len(candidates) != 254:
        raise ValueError("C2B candidate universe no longer contains exactly 254 rows")
    entity_candidates = [
        row for row in candidates if row["className"] in MENTIONABLE_CLASS_NAMES
    ]
    accepted_entities = [
        row for row in entity_candidates if row["counterfactualHypotheticallyUsable"]
    ]
    accepted_discourse = [
        row
        for row in candidates
        if row["className"] in DISCOURSE_CLASSES
        and row["counterfactualHypotheticallyUsable"]
    ]
    class_counts = {}
    for class_name in sorted(MENTIONABLE_CLASS_NAMES):
        class_rows = [row for row in entity_candidates if row["className"] == class_name]
        class_counts[class_name] = {
            "modelAuthoredCandidateCount": len(class_rows),
            "authenticUsableCandidateCount": sum(
                row["authenticUsable"] for row in class_rows
            ),
            "c2aHypotheticallyUsableCandidateCount": sum(
                row["counterfactualHypotheticallyUsable"] for row in class_rows
            ),
        }
    paper_edges = [
        {
            "developmentID": row["developmentID"],
            "sourceArtifactID": row["sourceArtifactID"],
            "sourceUnitID": row["sourceUnitID"],
            "entityCandidateKey": row["reviewCandidateKey"],
            "entityClass": row["className"],
            "entityLabel": row["label"],
            "entityEvidence": deepcopy(row["evidence"]),
            "edgeIdentityScope": "candidate_local_not_consolidated",
            "derivationBasis": "accepted entity evidence with trusted Paper provenance",
        }
        for row in accepted_entities
    ]
    discourse_edges = []
    for entity in accepted_entities:
        for discourse in accepted_discourse:
            bindings = strict_evidence_containment(entity, discourse)
            if bindings:
                discourse_edges.append(
                    {
                        "developmentID": entity["developmentID"],
                        "sourceUnitID": entity["sourceUnitID"],
                        "discourseCandidateKey": discourse["reviewCandidateKey"],
                        "discourseClass": discourse["className"],
                        "discourseLabel": discourse["label"],
                        "entityCandidateKey": entity["reviewCandidateKey"],
                        "entityClass": entity["className"],
                        "entityLabel": entity["label"],
                        "entityEvidence": deepcopy(entity["evidence"]),
                        "discourseEvidence": deepcopy(discourse["evidence"]),
                        "edgeIdentityScope": "candidate_local_not_consolidated",
                        "containmentBindings": bindings,
                    }
                )
    entity_group_keys = {
        (row["developmentID"], evidence_id)
        for row in entity_candidates
        for evidence_id in row["evidenceSpanIDs"]
    }
    accepted_group_keys = {
        (row["developmentID"], evidence_id)
        for row in accepted_entities
        for evidence_id in row["evidenceSpanIDs"]
    }
    dev01_regions = [
        edge
        for edge in discourse_edges
        if edge["developmentID"] == "DEV-01"
        and edge["discourseClass"] == "RelatedResearch"
        and edge["entityClass"] == "NamedPlace"
    ]
    information_rows = []
    for class_name in sorted(MENTIONABLE_CLASS_NAMES):
        class_entities = [
            row for row in accepted_entities if row["className"] == class_name
        ]
        class_edges = [
            row for row in discourse_edges if row["entityClass"] == class_name
        ]
        representative = class_edges[0] if class_edges else (
            {
                "developmentID": class_entities[0]["developmentID"],
                "entityCandidateKey": class_entities[0]["reviewCandidateKey"],
                "entityLabel": class_entities[0]["label"],
            }
            if class_entities
            else None
        )
        information_rows.append(
            {
                "ontologyClass": class_name,
                "acceptedEntityCandidateCount": len(class_entities),
                "strictDiscourseContainmentEdgeCount": len(class_edges),
                "currentlyPreservedAs": (
                    ["raw_evidence_text", "unconnected_entity_candidate"]
                    + (["discourse_node_same_or_containing_evidence"] if class_edges else [])
                ),
                "nodeCoverageGapObservedForEmittedCandidate": False,
                "relationCoverageGapObserved": bool(class_entities),
                "notStructurallyRepresentedCasesMeasurableWithoutGold": False,
                "representativeCase": representative,
            }
        )
    return _with_hash(
        {
            **_base("generic_mentions_devset_empirical_impact", provenance),
            "authenticC1BCandidateCount": len(candidates),
            "c2bEvidenceGroupCount": len(evidence_artifact["rows"]),
            "mentionRangeModelAuthoredCandidateCount": len(entity_candidates),
            "mentionRangeAuthenticUsableCandidateCount": sum(
                row["authenticUsable"] for row in entity_candidates
            ),
            "mentionRangeC2AHypotheticallyUsableCandidateCount": len(
                accepted_entities
            ),
            "candidateCountsByClass": class_counts,
            "mentionRangeEvidenceGroupCount": len(entity_group_keys),
            "acceptedMentionRangeEvidenceGroupCount": len(accepted_group_keys),
            "developmentUnitsAffected": sorted(
                {row["developmentID"] for row in entity_candidates}
            ),
            "potentialPaperMentionsEdgeCount": len(paper_edges),
            "potentialPaperMentionsEdges": paper_edges,
            "potentialDiscourseMentionsEdgeCount": len(discourse_edges),
            "potentialDiscourseMentionsEdges": discourse_edges,
            "strongerAcceptedRelationEdgesInferableFromC1BNodeOnlyData": 0,
            "strongerRelationInferenceReason": (
                "C1B contains node candidates and no accepted semantic relation edges; "
                "use, study, metric, parameter, and reference roles cannot be inferred "
                "from endpoint coexistence or evidence containment alone."
            ),
            "genericFallbackPaperEdgeCountAfterKnownPrecedence": len(paper_edges),
            "genericFallbackDiscourseEdgeCountAfterKnownPrecedence": len(
                discourse_edges
            ),
            "dev01RegionalPriorResearchCases": dev01_regions,
            "dev01Interpretation": (
                "The RelatedResearch evidence strictly contains mentions of US Midwest, "
                "Great Lakes regions, coastal Southeast, Southwest, and California. "
                "Generic RelatedResearch-to-NamedPlace edges preserve that local mention "
                "without incorrectly asserting that the current study studies each place."
            ),
            "informationCoverageByClass": information_rows,
            "formalAccuracyOrGoldJudgmentMade": False,
        }
    )


def build_change_surface(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Enumerate prospective ontology and pipeline surfaces without editing them."""

    components = [
        "ontology spec",
        "ontology inventory",
        "target inventory",
        "candidate-output schema",
        "screening mapping/catalog",
        "routing",
        "calibration interface",
        "annotation schema/guidelines",
        "evidence validator",
        "evaluation matching",
        "LLM request builder",
        "LLM prompt",
        "graph materialization",
        "relation-count/information-density diagnostics",
    ]
    option_a_changed = set(components)
    option_b_changed = {
        "ontology spec",
        "ontology inventory",
        "target inventory",
        "evidence validator",
        "evaluation matching",
        "graph materialization",
        "relation-count/information-density diagnostics",
    }
    return _with_hash(
        {
            **_base("generic_mentions_change_surface", provenance),
            "minimumProspectiveOntologySurface": {
                "relationID": "UNASSIGNED_PROSPECTIVE_STABLE_ID",
                "relationName": "mentions",
                "placement": "global_cross_artifact",
                "domain": (
                    "reviewed explicit artifact/source and discourse-container strategy; "
                    "not Paper-only"
                ),
                "range": sorted(MENTIONABLE_CLASS_NAMES),
                "owlThingRangeRejected": True,
                "existingMentionsXAction": "retain and declare as subproperties",
                "existingSpecializedRelationRemoval": False,
                "duplicateParentChildMaterialization": False,
                "reasoningImplication": (
                    "A specialized mentionsX assertion entails generic mentions through "
                    "the superproperty; consumers should query inference or materialize only "
                    "one nonredundant edge."
                ),
                "owlProfileConsiderations": [
                    "HermiT can check explicit union class expressions.",
                    "ELK compatibility must be rechecked if union domain/range expressions are used.",
                    "A named governed MentioningContainer/MentionableEntity strategy may preserve EL-friendly subclassing but adds class declarations.",
                    "Multiple independent rdfs:domain/range axioms must not be used to encode a union because they imply intersection membership.",
                ],
                "competencyQuestionsNeedReview": True,
                "synchronizedFiles": [
                    "src/ontology/ontology_spec.yaml",
                    "docs/ontology_inventory.md",
                    "generated OWL/formalization outputs",
                    "ontology validation and competency-question records",
                ],
                "finalOntologyVersionAssigned": False,
            },
            "optionAComponentImpact": [
                {
                    "component": component,
                    "changeRequired": component in option_a_changed,
                    "reason": "new independent LLM/human relation decision",
                }
                for component in components
            ],
            "optionBComponentImpact": [
                {
                    "component": component,
                    "changeRequired": component in option_b_changed,
                    "reason": (
                        "generic ontology/materialization/validation provenance support"
                        if component in option_b_changed
                        else "no new LLM or human decision surface"
                    ),
                }
                for component in components
            ],
            "recommendation": {
                "choice": "B_GENERIC_MENTIONS_AS_PIPELINE_DERIVED_RELATION",
                "reScreeningRequired": False,
                "repeatCalibrationRequired": False,
                "historicalProvenancePreserved": True,
                "specializedMentionsXPreserved": True,
                "paperOnlyDomainRejected": True,
                "graphInflationControl": (
                    "fallback-only explicit materialization plus superproperty inference"
                ),
                "implementationAuthorized": False,
            },
        }
    )


def _markdown(
    current: Mapping[str, Any],
    domain_range: Mapping[str, Any],
    options: Mapping[str, Any],
    screening: Mapping[str, Any],
    calibration: Mapping[str, Any],
    empirical: Mapping[str, Any],
    change: Mapping[str, Any],
) -> str:
    """Render the complete human-readable audit without semantic adjudication."""

    lines = [
        "# M2-C2C — Generic `mentions` ontology and operational impact audit",
        "",
        "**AUDIT_ONLY · NO_ONTOLOGY_CHANGE · NO_SCREENING_CHANGE · "
        "NO_CALIBRATION_CHANGE · NO_MODEL_CALL**",
        "",
        "Status: `researcher_review_pending`",
        "",
        "## Current ontology",
        "",
        f"The frozen ontology contains {current['ontologyRelationCount']} relations. "
        f"This audit identifies {current['allMentionsXRelationCount']} existing `mentionsX` "
        "relations across Publication, dataset, repository, and documentation modules. "
        "No generic `mentions` superproperty currently exists.",
        "",
        "| ID | Relation | Domain | Range | Module | Strength |",
        "|---|---|---|---|---|---|",
    ]
    for row in current["relations"]:
        lines.append(
            f"| `{row['relationID']}` | `{row['name']}` | "
            f"`{json.dumps(row['domain'], ensure_ascii=False)}` | "
            f"`{json.dumps(row['range'], ensure_ascii=False)}` | "
            f"`{row['module']}` | `{row['currentSemanticStrength']}` |"
        )
    lines.extend(
        [
            "",
            "## Domain and range audit",
            "",
            "The bounded candidate range includes models and subtypes, tools, dataset "
            "mentions/resources, variables, concepts, hydrologic features and concrete "
            "subtypes, named places, metrics, parameters, algorithms, and repositories. "
            "It does not use `owl:Thing`.",
            "",
            "The domain is not Paper-only. Existing ontology evidence supports Paper, "
            "Repository, DocumentationPage, and DatasetResource as artifact containers. "
            "All accepted Publication discourse classes have a clear containment-bound "
            "generic-mention meaning, while their stronger role-specific relations retain "
            "precedence.",
            "",
            "## Operational options",
            "",
            f"Recommendation: `{options['auditRecommendation']}`.",
            "",
            "Option A creates a new independent LLM edge and human relation decision. "
            "Option B derives the weak edge from accepted entity evidence and trusted "
            "provenance. Discourse-to-entity derivation additionally requires exact valid "
            "evidence containment; endpoint coexistence is never sufficient.",
            "",
            "Generic edges should be fallback-only. Existing specialized `mentionsX` "
            "relations remain and may become subproperties; stronger accepted relations "
            "suppress explicit generic materialization.",
            "",
            "## Screening recoverability",
            "",
            f"Of {screening['humanScreenedUnitCount']} completed human-screened units, "
            f"{screening['recoverableUnitCount']} "
            f"({screening['recoverableUnitPercentage']:.6f}%) have at least one previously "
            "screened node target inside the candidate generic range. "
            f"{screening['notRecoverableUnitCount']} do not. "
            f"{screening['unitsWithMultipleMentionableNodeTargets']} have multiple causing "
            "targets.",
            "",
            "This is derived routing possibility, not new screening and not evidence that "
            "a mention exists. Option B does not require this routing augmentation.",
            "",
            "## Calibration impact",
            "",
            f"Option A would introduce a relation decision in "
            f"{calibration['optionAAffectedCalibrationUnitCount']} of "
            f"{calibration['calibrationUnitCount']} frozen calibration units and therefore "
            "mismatches the instructions shown to annotators. Option B introduces no new "
            "annotator decision and does not require repeating calibration.",
            "",
            "## DEV-SET-0 empirical impact",
            "",
            f"The 254 C1B candidates contain "
            f"{empirical['mentionRangeModelAuthoredCandidateCount']} model-authored entity "
            "candidates in the candidate range; "
            f"{empirical['mentionRangeAuthenticUsableCandidateCount']} were authentically "
            "usable and "
            f"{empirical['mentionRangeC2AHypotheticallyUsableCandidateCount']} are usable "
            "under the diagnostic C2A title-only counterfactual. The latter support "
            f"{empirical['potentialPaperMentionsEdgeCount']} potential Paper edges and "
            f"{empirical['potentialDiscourseMentionsEdgeCount']} strict-containment "
            "discourse edges.",
            "",
            "DEV-01 demonstrates the motivating gap: RelatedResearch evidence contains "
            "US Midwest, Great Lakes regions, coastal Southeast, Southwest, and California. "
            "A generic RelatedResearch-to-NamedPlace mention preserves that local context "
            "without asserting current-study `studiesPlace` semantics.",
            "",
            "## Change surface and recommendation",
            "",
            f"Recommended design: `{change['recommendation']['choice']}`. It preserves "
            "all historical screening and calibration provenance, retains specialized "
            "mention relations, rejects a Paper-only domain, and controls graph inflation "
            "through fallback-only materialization and superproperty inference.",
            "",
            "No ontology ID/version is assigned and no recommendation is implemented by "
            "this audit.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def generate_audit(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Generate all deterministic M2-C2C audit artifacts offline."""

    provenance = _provenance()
    spec = load_yaml_object(ONTOLOGY_SPEC_PATH)
    profile = load_yaml_object(TARGET_INVENTORY_PATH)
    current = build_current_ontology_audit(spec, provenance)
    domain_range = build_domain_range_audit(spec, provenance)
    options = build_option_comparison(provenance)
    screening = build_screening_recoverability(profile, provenance)
    calibration = build_calibration_impact(profile, provenance)
    empirical = build_devset_empirical_impact(provenance)
    change = build_change_surface(provenance)
    artifacts = {
        "generic_mentions_current_ontology_audit.json": current,
        "generic_mentions_domain_range_audit.json": domain_range,
        "generic_mentions_option_comparison.json": options,
        "generic_mentions_screening_recoverability.json": screening,
        "generic_mentions_calibration_impact.json": calibration,
        "generic_mentions_devset_empirical_impact.json": empirical,
        "generic_mentions_change_surface.json": change,
    }
    for filename, artifact in artifacts.items():
        _write_json(output_dir / filename, artifact)
    markdown = _markdown(
        current, domain_range, options, screening, calibration, empirical, change
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "generic_mentions_impact_audit.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    return {
        "artifacts": artifacts,
        "markdownSha256": sha256_bytes(markdown_path.read_bytes()),
        "outputFileSha256": {
            path.name: sha256_bytes(path.read_bytes())
            for path in sorted(output_dir.iterdir())
            if path.is_file()
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the offline generic-mentions audit builder."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    result = generate_audit(args.output_dir)
    print(canonical_json(result["outputFileSha256"]).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
