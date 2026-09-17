"""Build the primary-blind N=2 Human Core reliability package under ontology v0.1.5."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


PACKAGE_RELATIVE = "data/curation/papers/m2/human_core_gold/publication_human_core_reliability_annotation_package_v0.1.5.json"
GUIDE_RELATIVE = "docs/publication_human_core_reliability_annotation_guide_v0.1.5.md"
DELTA_NODES = {"PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-N-A-AG02-ORGANIZATION-PROSE"}
DELTA_RELATIONS = {"PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "PUB-R-C-P13-USESMODEL-METHOD-BRANCH", "PUB-R-C-P14-APPLIESTO", "PUB-R-C-P23-MENTIONSMODEL", "PUB-R-C-P26-EVALUATES", "PUB-R-C-P27-HASPARAMETER", "PUB-R-C-P34-HASCOMPONENT"}


def _sha(path: Path) -> str:
    """Return a file SHA-256."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ui_target(row: dict[str, Any], display: dict[str, Any]) -> dict[str, Any]:
    """Attach the annotator-facing fields used by the existing application."""

    value = dict(row)
    value["displayLabel"] = display.get("displayLabel", value["operational_id"])
    value["shortDefinition"] = display.get("shortDefinition", value.get("operational_relation", value.get("operational_target", "")))
    value["boundaryHint"] = display.get("boundaryHint", value.get("boundary", "Use exact canonical evidence."))
    return value


def build_package(root: Path) -> dict[str, Any]:
    """Construct the two-unit target union from frozen routes and v0.1.5 deltas only."""

    freeze_path = root / "data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    reliability_ids = tuple(freeze["reliabilitySubset"]["sourceUnitIDs"])
    selected = {row["sourceUnitID"]: row for row in freeze["selectedUnits"]}
    if reliability_ids != ("pub:34:sec:0015:unit:0001", "pub:79:sec:0004:unit:0001"):
        raise ValueError("HUMAN_CORE_RELIABILITY_FREEZE_IDENTITY_DRIFT")
    profile = yaml.safe_load((root / "src/extraction/llm/publications/publication_target_inventory.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load((root / "data/curation/papers/pilot1/publication_pilot1_target_display_catalog.yaml").read_text(encoding="utf-8"))
    display = {row["operationalTargetID"]: row for row in catalog["targets"]}
    source_nodes = {row["operational_id"]: _ui_target(row, display.get(row["operational_id"], {})) for row in profile["node_targets"]}
    source_relations = {row["operational_id"]: _ui_target(row, display.get(row["operational_id"], {})) for row in profile["relation_targets"]}
    source_nodes["PUB-N-A-DOM03E-AGENTBASEDMODEL"] = {"operational_id": "PUB-N-A-DOM03E-AGENTBASEDMODEL", "formal_classes": [{"id": "A-DOM03e", "name": "AgentBasedModel"}], "operational_target": "AgentBasedModel", "displayLabel": "AgentBasedModel", "shortDefinition": "Named agent-based simulation model (including ABM).", "boundaryHint": "Do not use for MLModel or an unspecified model; canonical text must support an agent-based model identity.", "direct_instantiation": True, "pilot_treatment": "extract_and_evaluate", "evaluation_mode": "target_level_metrics", "allowed_actions": ["propose_new"]}
    source_nodes["PUB-N-A-AG02-ORGANIZATION-PROSE"] = {"operational_id": "PUB-N-A-AG02-ORGANIZATION-PROSE", "formal_classes": [{"id": "A-AG02", "name": "Organization"}], "operational_target": "Organization", "displayLabel": "Organization (publication prose)", "shortDefinition": "Evidence-backed organization occurrence in publication prose.", "boundaryHint": "Create the Organization node when supported. Do not manually annotate generic D-26 Paper → mentions → Organization; that edge is pipeline-derived.", "direct_instantiation": True, "pilot_treatment": "extract_and_evaluate", "evaluation_mode": "target_level_metrics", "allowed_actions": ["propose_new"]}
    source_relations["PUB-R-C-P34-HASCOMPONENT"] = {"operational_id": "PUB-R-C-P34-HASCOMPONENT", "operational_relation": "hasComponent", "displayLabel": "hasComponent", "shortDefinition": "Explicit model/tool composition in publication prose.", "boundaryHint": "Never infer composition from co-occurrence; Tool or ComputationalModel endpoints only.", "raw_operational_signature": "Tool/ComputationalModel → Tool/ComputationalModel", "operational_signatures": [{"domain": {"classes": ["Tool", "ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel", "AgentBasedModel"], "match": "one_of_or_concrete_subclass_of", "ontology_parent": "ComputationalModel"}, "range": {"classes": ["Tool", "ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel", "AgentBasedModel"], "match": "one_of_or_concrete_subclass_of", "ontology_parent": "ComputationalModel"}}], "pilot_treatment": "extract_and_evaluate", "evaluation_mode": "target_level_metrics", "allowed_actions": ["propose_edge"]}
    units = []
    all_nodes: set[str] = set(); all_relations: set[str] = set()
    for unit_id in reliability_ids:
        original_nodes = set(selected[unit_id]["routedScoredNodeOperationalTargetIDs"])
        original_relations = set(selected[unit_id]["routedScoredRelationOperationalTargetIDs"])
        node_ids, relation_ids = sorted(original_nodes | DELTA_NODES), sorted(original_relations | DELTA_RELATIONS)
        effective_signatures = {}
        for target_id in DELTA_RELATIONS - {"PUB-R-C-P34-HASCOMPONENT"}:
            signature = dict(source_relations[target_id]["operational_signatures"][0])
            domain, range_ = dict(signature["domain"]), dict(signature["range"])
            changed = domain if target_id == "PUB-R-C-P27-HASPARAMETER" else range_
            changed["classes"] = (list(changed["classes"]) + ["AgentBasedModel"]) if target_id in original_relations else ["AgentBasedModel"]
            if target_id not in original_relations:
                changed["match"] = "exact"
                changed.pop("ontology_parent", None)
            if target_id == "PUB-R-C-P27-HASPARAMETER":
                signature["domain"] = changed
            else:
                signature["range"] = changed
            effective_signatures[target_id] = [signature]
        effective_signatures["PUB-R-C-P34-HASCOMPONENT"] = source_relations["PUB-R-C-P34-HASCOMPONENT"]["operational_signatures"]
        all_nodes.update(node_ids); all_relations.update(relation_ids)
        units.append({"sourceUnitID": unit_id, "sourceUnitTextHash": selected[unit_id]["sourceUnitTextHash"], "originalRoutedScoredNodeOperationalTargetIDs": sorted(original_nodes), "originalRoutedScoredRelationOperationalTargetIDs": sorted(original_relations), "v015DeltaNodeOperationalTargetIDs": sorted(DELTA_NODES), "v015DeltaRelationOperationalTargetIDs": sorted(DELTA_RELATIONS), "eligibleNodeOperationalTargetIDs": node_ids, "eligibleRelationOperationalTargetIDs": relation_ids, "effectiveRelationSignatures": effective_signatures})
    paths = {"ontologySpec": root / "src/ontology/ontology_spec.yaml", "ontologyOwl": root / "src/ontology/ciroh_ontology.owl", "guide": root / GUIDE_RELATIVE, "sampleFreeze": freeze_path, "targetInventory": root / "src/extraction/llm/publications/publication_target_inventory.yaml", "unitRouting": root / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl"}
    return {"packageDefinitionVersion": "0.1.5.0", "packageIdentity": "publication-human-core-gold-n2-reliability-v015", "status": "ready_for_independent_annotator_2", "session": {"annotationSessionID": "HUMAN_CORE_N2_RELIABILITY_V015", "annotatorID": "HUMAN_CORE_RELIABILITY_ANNOTATOR_2", "mode": "human-core-reliability", "stateNamespace": "human-core/reliability-annotator-2"}, "authorities": {key: {"path": str(path.relative_to(root)), "sha256": _sha(path), **({"version": "0.1.5"} if key in {"ontologySpec", "ontologyOwl"} else ({"version": "0.1.5"} if key == "guide" else {}))} for key, path in paths.items()}, "independence": {"fromScratch": True, "forbiddenInputs": ["primary annotations", "supplemental annotations", "baseline nodes", "adjudications", "provider or model output"], "noBaselineEndpointProjection": True}, "organizationBoundary": "Publication-prose Organization is human-annotated as a node. Generic D-26 Paper -> mentions -> Organization is pipeline-derived and MUST NOT be manually annotated; its absence from the human record is expected.", "routing": {"units": units}, "coverage": {"consolidatedNodeTargetCount": len(all_nodes), "consolidatedRelationTargetCount": len(all_relations)}, "targets": {"class_expansions": {**profile["class_expansions"], "ComputationalModel": ["ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel", "AgentBasedModel"]}, "node_targets": [source_nodes[key] for key in sorted(all_nodes)], "relation_targets": [source_relations[key] for key in sorted(all_relations)]}}


def write_package(root: Path) -> Path:
    """Write the deterministic tracked package definition."""

    path = root / PACKAGE_RELATIVE
    path.write_text(json.dumps(build_package(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_package(Path.cwd()))
