"""Freeze the researcher-authorized Publication Human Core N=5 sample.

The builder reads IDs, hashes, routing, scored target IDs, and structural metadata only;
it deliberately never reads canonical source text, section titles, model outputs, or
candidate results while freezing the sample or choosing the reliability subset.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import yaml


FREEZE_VERSION = "1.0.0"
PACKAGE_ID = "publication-human-core-gold-n5-primary-v1"
SELECTED_IDS = (
    "pub:10:sec:0008:unit:0001",
    "pub:15:sec:0004:unit:0001",
    "pub:16:sec:0033:unit:0001",
    "pub:34:sec:0015:unit:0001",
    "pub:79:sec:0004:unit:0001",
)


def sha256_file(path: Path) -> str:
    """Return a SHA-256 hash for one declared input artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split(value: str) -> set[str]:
    """Decode a stable pipe-delimited coverage-matrix cell."""

    return {item for item in value.split("|") if item}


def _scored_targets(mapping_path: Path) -> tuple[set[str], set[str]]:
    """Return frozen extract-and-evaluate node and relation IDs."""

    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    nodes = {item["operationalTargetID"] for item in mapping["targets"]
             if item["targetKind"] == "node" and item["pilotTreatment"] == "extract_and_evaluate"}
    relations = {item["operationalTargetID"] for item in mapping["targets"]
                 if item["targetKind"] == "relation" and item["pilotTreatment"] == "extract_and_evaluate"}
    return nodes, relations


def build_freeze(root: Path) -> dict[str, Any]:
    """Build the exact Human Core freeze and metadata-only reliability choice."""

    pilot = root / "data/curation/papers/pilot1"
    analysis = root / "data/curation/papers/m2/human_core_sampling_analysis/publication_human_core_sampling_analysis_v0.1.0.json"
    mapping_path = pilot / "publication_pilot1_target_family_mapping.yaml"
    matrix_path = pilot / "publication_pilot1_target_coverage_matrix.csv"
    inventory_path = pilot / "publication_pilot1_source_unit_inventory.jsonl"
    routing_path = pilot / "publication_pilot1_unit_routing.jsonl"
    guide_path = root / "docs/publication_human_core_expert_annotation_guide.md"
    schema_path = root / "schemas/publication_pilot1_annotation_record.schema.json"
    input_paths = {
        "samplingAnalysis": analysis, "targetFamilyMapping": mapping_path,
        "coverageMatrix": matrix_path, "sourceUnitInventory": inventory_path,
        "unitRouting": routing_path, "expertGuide": guide_path, "annotationSchema": schema_path,
    }
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        coverage = {row["sourceUnitID"]: row for row in csv.DictReader(handle)}
    inventory = {row["sourceUnitID"]: row for row in (
        json.loads(line) for line in inventory_path.read_text(encoding="utf-8").splitlines() if line
    )}
    routes = {row["sourceUnitID"]: row for row in (
        json.loads(line) for line in routing_path.read_text(encoding="utf-8").splitlines() if line
    )}
    analysis_data = json.loads(analysis.read_text(encoding="utf-8"))
    n5 = next(item for item in analysis_data["comparisons"] if item["sampleSize"] == 5)
    if tuple(n5["deterministicBestCandidateSet"]["sourceUnitIDs"]) != SELECTED_IDS:
        raise ValueError("HUMAN_CORE_FREEZE_SAMPLING_ANALYSIS_SELECTION_DRIFT")
    scored_nodes, scored_relations = _scored_targets(mapping_path)
    selected = []
    for unit_id in SELECTED_IDS:
        if unit_id not in coverage or unit_id not in inventory or unit_id not in routes:
            raise ValueError(f"HUMAN_CORE_FREEZE_UNIT_PROVENANCE_MISSING:{unit_id}")
        row, unit, route = coverage[unit_id], inventory[unit_id], routes[unit_id]
        if unit_id in set(json.loads((pilot / "publication_pilot1_calibration_manifest.json").read_text(encoding="utf-8"))["calibrationSourceUnitIDs"]):
            raise ValueError(f"HUMAN_CORE_FREEZE_CALIBRATION_CONTAMINATION:{unit_id}")
        nodes = set(route["eligibleNodeOperationalTargetIDs"]) & scored_nodes
        relations = set(route["eligibleRelationOperationalTargetIDs"]) & scored_relations
        selected.append({
            "sourceUnitID": unit_id, "paperID": unit["paperID"],
            "sourceArtifactID": unit["canonicalArtifactID"], "sourceUnitTextHash": unit["textHash"],
            "canonicalDocumentHash": unit["canonicalTextSha256"], "sectionID": unit["sectionID"],
            "startOffsetInDocument": unit["startOffsetInDocument"], "endOffsetInDocument": unit["endOffsetInDocument"],
            "characterCount": unit["characterCount"], "sourceConversionStatus": row["sourceConversionStatus"],
            "observedDeterministicMetadata": sorted(_split(row["observedDeterministicMetadata"])),
            "samplingStrata": sorted(_split(row["likelySamplingStrata"])),
            "routedScoredNodeOperationalTargetIDs": sorted(nodes),
            "routedScoredRelationOperationalTargetIDs": sorted(relations),
        })
    def pair_score(pair: tuple[dict[str, Any], dict[str, Any]]) -> tuple[Any, ...]:
        nodes = set(pair[0]["routedScoredNodeOperationalTargetIDs"]) | set(pair[1]["routedScoredNodeOperationalTargetIDs"])
        relations = set(pair[0]["routedScoredRelationOperationalTargetIDs"]) | set(pair[1]["routedScoredRelationOperationalTargetIDs"])
        strata = set(pair[0]["samplingStrata"]) | set(pair[1]["samplingStrata"])
        return (-(len(nodes) + len(relations)), -len(nodes), -len(relations), -len(strata), tuple(item["sourceUnitID"] for item in pair))
    reliability_pair = min(itertools.combinations(selected, 2), key=pair_score)
    reliability_ids = {item["sourceUnitID"] for item in reliability_pair}
    for item in selected:
        item["partition"] = "reliability" if item["sourceUnitID"] in reliability_ids else "remaining_evaluation"
    all_nodes = set().union(*(set(item["routedScoredNodeOperationalTargetIDs"]) for item in selected))
    all_relations = set().union(*(set(item["routedScoredRelationOperationalTargetIDs"]) for item in selected))
    all_strata = set().union(*(set(item["samplingStrata"]) for item in selected))
    return {
        "humanCoreSampleFreezeVersion": FREEZE_VERSION,
        "status": "final_and_binding_for_human_core_gold_only",
        "packageIdentity": PACKAGE_ID,
        "researcherDecision": {
            "sampleSize": 5, "selectedBeforeSemanticInspection": True,
            "humanCoreAdequacyRule": "model_blind_selection + five_distinct_papers + five_of_five_strata + complete_routed_scored_target_coverage",
            "legacyPilot1PerArtifactRepresentation": "superseded_for_this_distinct_human_core_component_only; retained unchanged for the historical Pilot 1 evaluation-sample design",
            "notRepresentativeOfAllPrimaryPublications": True,
        },
        "authorities": {
            "expertGuide": {"path": str(guide_path.relative_to(root)), "version": "1.0", "sha256": sha256_file(guide_path)},
            "annotationSchema": {"path": str(schema_path.relative_to(root)), "version": "0.1.2", "sha256": sha256_file(schema_path)},
            "interfaceVersion": "publication-pilot1-annotation-calibration/0.1.3",
            "samplingAnalysis": {"path": str(analysis.relative_to(root)), "sha256": sha256_file(analysis)},
        },
        "inputArtifacts": {key: {"path": str(path.relative_to(root)), "sha256": sha256_file(path)} for key, path in input_paths.items()},
        "selectedUnits": selected,
        "reliabilitySubset": {
            "sourceUnitIDs": sorted(reliability_ids),
            "selectionRule": "maximize union routed scored node/relation target coverage; then node coverage; then relation coverage; then strata coverage; then lexicographically smallest sourceUnitID tuple",
            "independentAnnotationRequired": True,
        },
        "coverage": {
            "distinctPaperCount": len({item["paperID"] for item in selected}),
            "samplingStratumCount": len(all_strata), "samplingStrata": sorted(all_strata),
            "routedScoredNodeTargetCount": len(all_nodes), "routedScoredRelationTargetCount": len(all_relations),
            "uncoveredRoutedScoredNodeOperationalTargetIDs": sorted(scored_nodes - all_nodes),
            "uncoveredRoutedScoredRelationOperationalTargetIDs": sorted(scored_relations - all_relations),
        },
        "package": {
            "kind": "primary_researcher_human_core_annotation_package",
            "stateNamespace": "human-core/primary-researcher",
            "guide": "Publication Pilot 1 — Human Core Expert Annotation Guide v1.0",
            "modelBlind": True,
            "historicalCalibrationSeparation": "No CAL_A, CAL_B, or CORE_FEAS unit, session, export, or provenance is included or modified.",
        },
    }


def write_freeze(root: Path) -> Path:
    """Write canonical, deterministic Human Core sample-freeze provenance."""

    output = root / "data/curation/papers/m2/human_core_gold"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "publication_human_core_gold_sample_freeze_v1.0.json"
    payload = (json.dumps(build_freeze(root), indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != payload:
        raise ValueError("HUMAN_CORE_FREEZE_OUTPUT_EXISTS_CONFLICT")
    path.write_bytes(payload)
    return path


def write_primary_package_definition(root: Path, freeze_path: Path) -> Path:
    """Write the immutable primary-researcher package definition.

    Mutable local state and any later private delivery archive remain outside version
    control; this tracked definition is the reproducible package identity and binding.
    """

    freeze = build_freeze(root)
    payload = {
        "packageDefinitionVersion": "1.0.0",
        "packageIdentity": PACKAGE_ID,
        "status": "ready_for_primary_researcher_local_use",
        "application": {
            "module": "src.annotation.publication_pilot1.calibration.app",
            "mode": "human-core",
            "interfaceVersion": freeze["authorities"]["interfaceVersion"],
            "annotationSchemaVersion": freeze["authorities"]["annotationSchema"]["version"],
            "stateNamespace": freeze["package"]["stateNamespace"],
        },
        "freeze": {
            "path": str(freeze_path.relative_to(root)),
            "sha256": sha256_file(freeze_path),
            "selectedSourceUnitIDs": [item["sourceUnitID"] for item in freeze["selectedUnits"]],
            "reliabilitySourceUnitIDs": freeze["reliabilitySubset"]["sourceUnitIDs"],
        },
        "guide": freeze["authorities"]["expertGuide"],
        "modelBlind": True,
        "localStateAndExports": "ignored var/publication_pilot1_annotation/human-core/primary-researcher/ only",
        "historicalSeparation": freeze["package"]["historicalCalibrationSeparation"],
    }
    path = freeze_path.with_name("publication_human_core_primary_annotation_package_v1.0.json")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != encoded:
        raise ValueError("HUMAN_CORE_PACKAGE_DEFINITION_OUTPUT_EXISTS_CONFLICT")
    path.write_bytes(encoded)
    return path


def main() -> None:
    """Materialize the Human Core N=5 freeze."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    root = parser.parse_args().project_root.resolve()
    freeze_path = write_freeze(root)
    print(freeze_path)
    print(write_primary_package_definition(root, freeze_path))


if __name__ == "__main__":
    main()
