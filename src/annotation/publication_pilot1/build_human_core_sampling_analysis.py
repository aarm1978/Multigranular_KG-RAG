"""Build the prospective, model-blind Human Core sampling comparison.

Only whitelisted provenance, routing, target-ID, and structural metadata fields are
read.  In particular, this analysis never reads canonical unit text, section titles,
screening prose, model outputs, candidate results, or provider artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


ANALYSIS_VERSION = "0.1.0"
SAMPLE_SIZES = (4, 5, 6)
ELIGIBLE_PARTITION = "remaining_evaluation"
CORE_FEAS_SUBSUMPTION = (
    "Researcher-authorized: CORE_FEAS used only units already contained in the "
    "frozen 16-unit Publication Calibration manifest (CORE_FEAS subset Calibration); "
    "therefore no separate CORE_FEAS exclusion manifest is created or required."
)
CSV_FIELDS = (
    "sourceArtifactID",
    "paperID",
    "artifactQuotaRole",
    "postCalibrationAllowedBlockBPartitions",
    "sourceUnitID",
    "sourceEligibility",
    "eligibleNodeOperationalTargetIDs",
    "eligibleRelationOperationalTargetIDs",
    "likelySamplingStrata",
    "observedDeterministicMetadata",
    "sourceConversionStatus",
)


@dataclass(frozen=True)
class Unit:
    """The whitelisted non-semantic and routing metadata for one source unit."""

    source_unit_id: str
    paper_id: str
    node_targets: frozenset[str]
    relation_targets: frozenset[str]
    strata: frozenset[str]
    content_types: frozenset[str]
    conversion_status: str


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for a declared input artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_multi(value: str) -> frozenset[str]:
    """Decode the stable pipe-delimited projection used by the coverage matrix."""

    return frozenset(item for item in value.split("|") if item)


def _read_json(path: Path) -> dict[str, Any]:
    """Read a declared provenance manifest."""

    return json.loads(path.read_text(encoding="utf-8"))


def _load_development_ids(path: Path) -> set[str]:
    """Load exact development-unit IDs from the approved development-only manifest."""

    return {str(unit["sourceUnitID"]) for unit in _read_json(path)["units"]}


def _load_calibration_ids(path: Path) -> set[str]:
    """Load exact calibration-unit IDs from the frozen calibration manifest."""

    return {str(unit_id) for unit_id in _read_json(path)["calibrationSourceUnitIDs"]}


def _load_matrix(path: Path) -> list[dict[str, str]]:
    """Read only the explicit sampling-analysis whitelist from the coverage matrix."""

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(CSV_FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"COVERAGE_MATRIX_MISSING_FIELDS:{','.join(sorted(missing))}")
        return [{field: row[field] for field in CSV_FIELDS} for row in reader]


def _load_scored_target_ids(path: Path) -> tuple[set[str], set[str]]:
    """Load the frozen extract-and-evaluate target IDs by target kind."""

    mapping = yaml.safe_load(path.read_text(encoding="utf-8"))
    nodes = {
        str(target["operationalTargetID"])
        for target in mapping["targets"]
        if target["targetKind"] == "node" and target["pilotTreatment"] == "extract_and_evaluate"
    }
    relations = {
        str(target["operationalTargetID"])
        for target in mapping["targets"]
        if target["targetKind"] == "relation" and target["pilotTreatment"] == "extract_and_evaluate"
    }
    if not nodes or not relations:
        raise ValueError("TARGET_FAMILY_MAPPING_HAS_NO_SCORED_TARGETS")
    return nodes, relations


def _exclude_and_materialize(
    rows: Iterable[dict[str, str]], calibration_ids: set[str], development_ids: set[str],
    scored_node_ids: set[str], scored_relation_ids: set[str],
) -> tuple[list[Unit], dict[str, list[str]]]:
    """Apply the complete ID-based exclusion ledger and make the eligible universe."""

    eligible: list[Unit] = []
    exclusions: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        unit_id = row["sourceUnitID"]
        partitions = _split_multi(row["postCalibrationAllowedBlockBPartitions"])
        node_targets = _split_multi(row["eligibleNodeOperationalTargetIDs"]) & scored_node_ids
        relation_targets = _split_multi(row["eligibleRelationOperationalTargetIDs"]) & scored_relation_ids
        if unit_id in calibration_ids:
            reason = "calibration_manifest"
        elif unit_id in development_ids:
            reason = "development_or_stability_diagnostic_manifest"
        elif row["sourceEligibility"] != "eligible":
            reason = f"source_eligibility:{row['sourceEligibility']}"
        elif row["artifactQuotaRole"] != "primary_publication" or ELIGIBLE_PARTITION not in partitions:
            reason = "reserved_nonprimary_artifact"
        elif not node_targets and not relation_targets:
            reason = "no_routed_scored_target"
        else:
            eligible.append(Unit(
                source_unit_id=unit_id,
                paper_id=row["paperID"],
                node_targets=node_targets,
                relation_targets=relation_targets,
                strata=_split_multi(row["likelySamplingStrata"]),
                content_types=_split_multi(row["observedDeterministicMetadata"]),
                conversion_status=row["sourceConversionStatus"],
            ))
            continue
        exclusions[reason].append(unit_id)
    return sorted(eligible, key=lambda unit: unit.source_unit_id), {
        reason: sorted(unit_ids) for reason, unit_ids in sorted(exclusions.items())
    }


def _metrics(units: Iterable[Unit]) -> tuple[int, int, int, int]:
    """Return node, relation, stratum, and paper diversity counts."""

    selected = tuple(units)
    return (
        len(set().union(*(unit.node_targets for unit in selected))),
        len(set().union(*(unit.relation_targets for unit in selected))),
        len(set().union(*(unit.strata for unit in selected))),
        len({unit.paper_id for unit in selected}),
    )


def _greedy_completion(seed: Unit, universe: list[Unit], sample_size: int) -> tuple[Unit, ...]:
    """Complete one seed with stable, coverage-first greedy selection.

    The score maximizes newly covered routed scored targets, then source strata and
    papers.  Source-unit ID makes every residual tie deterministic.
    """

    selected = [seed]
    remaining = [unit for unit in universe if unit != seed]
    while len(selected) < sample_size:
        current_nodes = set().union(*(unit.node_targets for unit in selected))
        current_relations = set().union(*(unit.relation_targets for unit in selected))
        current_strata = set().union(*(unit.strata for unit in selected))
        current_papers = {unit.paper_id for unit in selected}
        chosen = min(
            remaining,
            key=lambda unit: (
                -len((unit.node_targets - current_nodes) | (unit.relation_targets - current_relations)),
                -len(unit.node_targets - current_nodes),
                -len(unit.relation_targets - current_relations),
                -len(unit.strata - current_strata),
                -(unit.paper_id not in current_papers),
                unit.source_unit_id,
            ),
        )
        selected.append(chosen)
        remaining.remove(chosen)
    return tuple(sorted(selected, key=lambda unit: unit.source_unit_id))


def _dominates(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> bool:
    """Return whether all explicit optimization dimensions weakly improve and one improves."""

    return all(a >= b for a, b in zip(left, right)) and any(a > b for a, b in zip(left, right))


def _candidate_record(selected: tuple[Unit, ...], universe_nodes: set[str], universe_relations: set[str]) -> dict[str, Any]:
    """Make a transparent candidate record without reading source or semantic outcomes."""

    nodes = set().union(*(unit.node_targets for unit in selected))
    relations = set().union(*(unit.relation_targets for unit in selected))
    strata = set().union(*(unit.strata for unit in selected))
    content_types = set().union(*(unit.content_types for unit in selected))
    conversion_counts = Counter(unit.conversion_status for unit in selected)
    per_unit_load = [
        {
            "sourceUnitID": unit.source_unit_id,
            "routedNodeTargetCount": len(unit.node_targets),
            "routedRelationTargetCount": len(unit.relation_targets),
            "routedTargetCount": len(unit.node_targets) + len(unit.relation_targets),
            "observedDeterministicContentTypes": sorted(unit.content_types),
            "sourceConversionStatus": unit.conversion_status,
        }
        for unit in selected
    ]
    return {
        "sourceUnitIDs": [unit.source_unit_id for unit in selected],
        "paperIDs": sorted({unit.paper_id for unit in selected}),
        "metrics": {
            "routedScoredNodeTargetCount": len(nodes),
            "routedScoredRelationTargetCount": len(relations),
            "samplingStratumCount": len(strata),
            "distinctPaperCount": len({unit.paper_id for unit in selected}),
        },
        "coveredNodeOperationalTargetIDs": sorted(nodes),
        "coveredRelationOperationalTargetIDs": sorted(relations),
        "uncoveredNodeOperationalTargetIDs": sorted(universe_nodes - nodes),
        "uncoveredRelationOperationalTargetIDs": sorted(universe_relations - relations),
        "structuralBurdenIndicators": {
            "perUnitRoutedTargetCounts": per_unit_load,
            "unionObservedDeterministicContentTypes": sorted(content_types),
            "sourceConversionStatusCounts": dict(sorted(conversion_counts.items())),
        },
    }


def _rank_key(record: dict[str, Any]) -> tuple[Any, ...]:
    """Return the published stable tie-breaker for nondominated candidate records."""

    metrics = record["metrics"]
    return (
        -(metrics["routedScoredNodeTargetCount"] + metrics["routedScoredRelationTargetCount"]),
        -metrics["samplingStratumCount"],
        -metrics["distinctPaperCount"],
        -metrics["routedScoredNodeTargetCount"],
        -metrics["routedScoredRelationTargetCount"],
        tuple(record["sourceUnitIDs"]),
    )


def _compare_size(universe: list[Unit], sample_size: int) -> dict[str, Any]:
    """Produce the seed-complete greedy Pareto frontier for one prospective size."""

    universe_nodes = set().union(*(unit.node_targets for unit in universe))
    universe_relations = set().union(*(unit.relation_targets for unit in universe))
    candidates = {
        tuple(unit.source_unit_id for unit in selected): _candidate_record(selected, universe_nodes, universe_relations)
        for selected in (_greedy_completion(seed, universe, sample_size) for seed in universe)
    }
    records = list(candidates.values())
    metrics_by_record = {
        tuple(record["sourceUnitIDs"]): tuple(record["metrics"].values()) for record in records
    }
    frontier = [
        record for record in records
        if not any(
            _dominates(metrics_by_record[tuple(other["sourceUnitIDs"])], metrics_by_record[tuple(record["sourceUnitIDs"])])
            for other in records if other is not record
        )
    ]
    frontier.sort(key=_rank_key)
    frontier_vectors = sorted({
        tuple(record["metrics"].values())
        for record in frontier
    }, reverse=True)
    return {
        "sampleSize": sample_size,
        "feasible": len(universe) >= sample_size,
        "availableSamplingStrata": sorted(set().union(*(unit.strata for unit in universe))),
        "availablePaperCount": len({unit.paper_id for unit in universe}),
        "greedySeedCount": len(universe),
        "uniqueGreedyCandidateCount": len(records),
        "nondominatedGreedyCandidateCount": len(frontier),
        "nondominatedMetricVectors": [
            {
                "routedScoredNodeTargetCount": vector[0],
                "routedScoredRelationTargetCount": vector[1],
                "samplingStratumCount": vector[2],
                "distinctPaperCount": vector[3],
            }
            for vector in frontier_vectors
        ],
        "deterministicBestCandidateSet": frontier[0],
    }


def build_analysis(project_root: Path) -> dict[str, Any]:
    """Build the complete prospective comparison from declared, allowed inputs."""

    pilot = project_root / "data/curation/papers/pilot1"
    paths = {
        "coverageMatrix": pilot / "publication_pilot1_target_coverage_matrix.csv",
        "targetFamilyMapping": pilot / "publication_pilot1_target_family_mapping.yaml",
        "calibrationManifest": pilot / "publication_pilot1_calibration_manifest.json",
        "developmentManifest": project_root / "data/curation/papers/publication_llm_development_only_manifest.json",
    }
    rows = _load_matrix(paths["coverageMatrix"])
    calibration_ids = _load_calibration_ids(paths["calibrationManifest"])
    development_ids = _load_development_ids(paths["developmentManifest"])
    scored_node_ids, scored_relation_ids = _load_scored_target_ids(paths["targetFamilyMapping"])
    eligible, exclusions = _exclude_and_materialize(
        rows, calibration_ids, development_ids, scored_node_ids, scored_relation_ids
    )
    matrix_ids = {row["sourceUnitID"] for row in rows}
    eligible_nodes = sorted(set().union(*(unit.node_targets for unit in eligible)))
    eligible_relations = sorted(set().union(*(unit.relation_targets for unit in eligible)))
    return {
        "analysisVersion": ANALYSIS_VERSION,
        "status": "prospective_comparison_not_sample_freeze",
        "scope": {
            "usesOnly": [
                "unit_and_paper_IDs", "artifact_role_and_partition_metadata",
                "source_eligibility", "routed_scored_operational_target_IDs",
                "likely_sampling_strata", "observed_deterministic_structural_metadata",
                "source_conversion_status",
            ],
            "doesNotUse": [
                "canonical_source_text", "section_titles", "LLM_or_provider_outputs",
                "candidate_counts", "semantic_extraction_results", "external_sources",
            ],
        },
        "inputArtifacts": {
            label: {"path": str(path.relative_to(project_root)), "sha256": _sha256(path)}
            for label, path in paths.items()
        },
        "reservedRoleProvenance": {
            "coreFeasibilitySubsumption": CORE_FEAS_SUBSUMPTION,
            "calibrationManifestUnitCount": len(calibration_ids),
            "developmentManifestUnitCount": len(development_ids),
            "developmentUnitsPresentInFixedPopulation": sorted(development_ids & matrix_ids),
            "diagnosticExclusionRule": "All stability diagnostics are excluded through their DEV provenance; no diagnostic-only unit overlaps the fixed population.",
        },
        "exclusionLedger": {
            "fixedPopulationUnitCount": len(rows),
            "eligibleUnitCount": len(eligible),
            "excludedByReason": exclusions,
        },
        "eligibleUniverse": {
            "sourceUnitIDs": [unit.source_unit_id for unit in eligible],
            "paperIDs": sorted({unit.paper_id for unit in eligible}),
            "samplingStrata": sorted(set().union(*(unit.strata for unit in eligible))),
            "routedScoredNodeOperationalTargetIDs": eligible_nodes,
            "routedScoredRelationOperationalTargetIDs": eligible_relations,
            "unroutedScoredNodeOperationalTargetIDs": sorted(scored_node_ids - set(eligible_nodes)),
            "unroutedScoredRelationOperationalTargetIDs": sorted(scored_relation_ids - set(eligible_relations)),
        },
        "candidateConstruction": {
            "method": "one coverage-first greedy completion from every eligible source-unit seed, followed by nondominated filtering",
            "optimizationDimensions": [
                "routed_scored_node_target_coverage", "routed_scored_relation_target_coverage",
                "sampling_stratum_coverage", "distinct_paper_coverage",
            ],
            "stableTieBreaker": [
                "higher_total_routed_scored_target_coverage", "higher_sampling_stratum_coverage",
                "higher_distinct_paper_coverage", "higher_node_target_coverage",
                "higher_relation_target_coverage", "lexicographically_smaller_sourceUnitID_tuple",
            ],
        },
        "comparisons": [_compare_size(eligible, sample_size) for sample_size in SAMPLE_SIZES],
    }


def _markdown(analysis: dict[str, Any]) -> str:
    """Render a concise, ID-only review projection of the JSON analysis."""

    universe = analysis["eligibleUniverse"]
    exclusions = analysis["exclusionLedger"]
    lines = [
        "# Publication Pilot 1 — Prospective Human Core Sampling Analysis v0.1.0",
        "",
        "**Status:** prospective comparison only; not a sample freeze and not an annotation package.",
        "",
        "## Boundary",
        "",
        "This is a deterministic, model-blind comparison. It reads only the whitelist declared in the companion JSON and does not read canonical unit text, section titles, model/provider material, candidate counts, or semantic extraction results.",
        "",
        f"{analysis['reservedRoleProvenance']['coreFeasibilitySubsumption']}",
        "",
        "## Eligible universe and exclusions",
        "",
        f"- Fixed population: {exclusions['fixedPopulationUnitCount']} units.",
        f"- Eligible routed prospective universe: {exclusions['eligibleUnitCount']} units across {len(universe['paperIDs'])} papers.",
        f"- Available sampling strata ({len(universe['samplingStrata'])}): {', '.join(universe['samplingStrata'])}.",
        f"- Routed scored target universe: {len(universe['routedScoredNodeOperationalTargetIDs'])} node IDs and {len(universe['routedScoredRelationOperationalTargetIDs'])} relation IDs.",
        "",
        "| Exclusion reason | Units |",
        "| --- | ---: |",
    ]
    for reason, unit_ids in exclusions["excludedByReason"].items():
        lines.append(f"| `{reason}` | {len(unit_ids)} |")
    lines.extend(["", "## N comparison", ""])
    for comparison in analysis["comparisons"]:
        best = comparison["deterministicBestCandidateSet"]
        metrics = best["metrics"]
        lines.extend([
            f"### N={comparison['sampleSize']}",
            "",
            f"- Feasible: `{str(comparison['feasible']).lower()}`; all {len(comparison['availableSamplingStrata'])} available strata are represented by the deterministic best candidate.",
            f"- Best candidate: `{', '.join(best['sourceUnitIDs'])}`.",
            f"- Papers: {metrics['distinctPaperCount']}; node targets: {metrics['routedScoredNodeTargetCount']}; relation targets: {metrics['routedScoredRelationTargetCount']}; strata: {metrics['samplingStratumCount']}.",
            f"- Uncovered target IDs: node `{', '.join(best['uncoveredNodeOperationalTargetIDs']) or 'none'}`; relation `{', '.join(best['uncoveredRelationOperationalTargetIDs']) or 'none'}`.",
            f"- Nondominated greedy candidates: {comparison['nondominatedGreedyCandidateCount']} (from {comparison['uniqueGreedyCandidateCount']} unique seed completions); the published candidate is the stable tie-break representative.",
            "",
        ])
    lines.extend([
        "## Structural/burden indicators",
        "",
        "The JSON records each candidate’s per-unit routed node/relation/total target counts, union of observed deterministic content types, and source-conversion-status counts. These indicators are shown separately and are not combined into a burden score.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "PYTHONPATH=. python -m src.annotation.publication_pilot1.build_human_core_sampling_analysis",
        "```",
        "",
    ])
    return "\n".join(lines)


def write_analysis(project_root: Path) -> tuple[Path, Path]:
    """Build and write the canonical JSON analysis plus its Markdown review projection."""

    analysis = build_analysis(project_root)
    output = project_root / "data/curation/papers/m2/human_core_sampling_analysis"
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "publication_human_core_sampling_analysis_v0.1.0.json"
    markdown_path = output / "publication_human_core_sampling_analysis_v0.1.0.md"
    json_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(analysis), encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    """Run the deterministic prospective comparison from the repository root."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    json_path, markdown_path = write_analysis(args.project_root.resolve())
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
