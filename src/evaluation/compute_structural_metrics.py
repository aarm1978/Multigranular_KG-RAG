"""Compute schema-agnostic structural metrics for an interim KG snapshot.

The input must use the project's source-agnostic interim format: top-level
``nodes`` and ``edges`` arrays, node records with ``id``, ``class``, and
``attributes``, and edge records with ``source``, ``target``, and ``relation``.

For each labeled snapshot, this script:

1. validates the graph structure;
2. computes information density, its attribute and edge components, relational
   richness, and mention-level or post-consolidation ratios;
3. writes a deterministic JSON record under ``results/metrics/snapshots``; and
4. rebuilds the human-readable trajectory table from all snapshot records.

The administrative/identifier exclusion set is a public constant so the exact
same counting policy can later be reused for Microsoft GraphRAG snapshots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results/metrics"
SNAPSHOT_SCHEMA_VERSION = "1.0"
METRIC_DECIMAL_PLACES = 6

# These fields identify, administer, locate, or provenance-track entities rather
# than describe their semantic content. Keep this set fixed across the
# multi-granular KG and GraphRAG comparison unless the evaluation contract is
# explicitly revised. Exact keys are recorded in every snapshot JSON.
ADMINISTRATIVE_ATTRIBUTE_KEYS = frozenset(
    {
        # Internal graph and source identifiers.
        "id",
        "internalId",
        "nodeId",
        "edgeId",
        "resourceId",
        "hydroshareResourceId",
        "hydroshareUserId",
        "inventoryId",
        # External identifiers and identity bookkeeping.
        "identifier",
        "identifiers",
        "identifierValue",
        "identifierType",
        "identifierRegime",
        "normalizedValue",
        "doi",
        "orcid",
        "ror",
        "spdxId",
        # Storage and integrity details.
        "checksum",
        "filePath",
        "path",
        "bagUrl",
        "downloadUrl",
        # URLs used primarily as identifiers or operational endpoints.
        "url",
        "host",
        "launchURL",
        "fundingAgencyUrl",
        "requestUrlBase",
        "requestUrlBaseFile",
        "toolIconUrl",
        # Provenance and pipeline administration.
        "sourceArtifact",
        "sourceLocation",
        "extractionMethod",
        "curationStatus",
        "mentionCount",
        # Administrative timestamps. Domain dates such as start/end remain.
        "createdAt",
        "updatedAt",
        "modifiedAt",
        "timestamp",
    }
)

EXTERNAL_URL_STUB_NOTE = (
    "Because url and host are excluded as identifier/administrative fields, "
    "external-URL stub nodes may have near-zero informative-attribute density. "
    "This is intentional and honest: unresolved stubs are information-poor, "
    "while their incident relations still contribute to structural density."
)

JsonDict = dict[str, Any]


def load_snapshot(path: Path) -> JsonDict:
    """Load a nodes/edges snapshot from JSON."""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object at {path}, found {type(data).__name__}")
    return data


def validate_snapshot(data: JsonDict) -> None:
    """Validate required graph fields and endpoint integrity."""
    nodes = data.get("nodes")
    edges = data.get("edges")
    if not isinstance(nodes, list):
        raise ValueError("Snapshot must contain a top-level 'nodes' array")
    if not isinstance(edges, list):
        raise ValueError("Snapshot must contain a top-level 'edges' array")

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"nodes[{index}] must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"nodes[{index}].id must be a non-empty string")
        if node_id in node_ids:
            raise ValueError(f"Duplicate node ID: {node_id}")
        node_ids.add(node_id)
        class_name = node.get("class")
        if not isinstance(class_name, str) or not class_name:
            raise ValueError(f"nodes[{index}].class must be a non-empty string")
        attributes = node.get("attributes", {})
        if not isinstance(attributes, dict):
            raise ValueError(f"nodes[{index}].attributes must be an object")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"edges[{index}] must be an object")
        relation = edge.get("relation")
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(relation, str) or not relation:
            raise ValueError(f"edges[{index}].relation must be a non-empty string")
        if source not in node_ids:
            raise ValueError(f"edges[{index}].source does not resolve to a node: {source!r}")
        if target not in node_ids:
            raise ValueError(f"edges[{index}].target does not resolve to a node: {target!r}")


def is_nonempty(value: Any) -> bool:
    """Return whether an attribute value contains countable information."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def count_informative_attributes(
    attributes: JsonDict,
    excluded_keys: frozenset[str] = ADMINISTRATIVE_ATTRIBUTE_KEYS,
) -> int:
    """Count nonempty attribute keys not in the exclusion set."""
    return sum(
        1
        for key, value in attributes.items()
        if key not in excluded_keys and is_nonempty(value)
    )


def build_incident_indexes(
    node_ids: Iterable[str],
    edges: list[JsonDict],
) -> tuple[Counter[str], dict[str, set[str]]]:
    """Build incident-edge counts and distinct incident-relation sets per node.

    A self-loop contributes one incident edge and one relation type to its node.
    """
    incident_edge_counts: Counter[str] = Counter({node_id: 0 for node_id in node_ids})
    incident_relation_types: dict[str, set[str]] = {
        node_id: set() for node_id in node_ids
    }

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        relation = edge["relation"]
        incident_edge_counts[source] += 1
        incident_relation_types[source].add(relation)
        if target != source:
            incident_edge_counts[target] += 1
            incident_relation_types[target].add(relation)

    return incident_edge_counts, incident_relation_types


def round_metric(value: float) -> float:
    """Round a reported metric consistently."""
    return round(value, METRIC_DECIMAL_PLACES)


def safe_average(total: int | float, count: int) -> float:
    """Return a rounded average, using zero for an empty graph."""
    return round_metric(float(total) / count) if count else 0.0


def compute_structural_metrics(data: JsonDict) -> JsonDict:
    """Compute density components and relational richness."""
    nodes: list[JsonDict] = data["nodes"]
    edges: list[JsonDict] = data["edges"]
    node_ids = [node["id"] for node in nodes]
    incident_counts, incident_types = build_incident_indexes(node_ids, edges)

    attribute_counts = {
        node["id"]: count_informative_attributes(node.get("attributes", {}))
        for node in nodes
    }
    total_attributes = sum(attribute_counts.values())
    total_incident_edges = sum(incident_counts.values())
    total_distinct_relation_types = sum(
        len(incident_types[node_id]) for node_id in node_ids
    )
    node_count = len(nodes)

    average_attributes = safe_average(total_attributes, node_count)
    average_incident_edges = safe_average(total_incident_edges, node_count)

    return {
        "informationDensity": {
            "combinedAveragePerNode": round_metric(
                average_attributes + average_incident_edges
            ),
            "averageInformativeAttributesPerNode": average_attributes,
            "averageIncidentEdgesPerNode": average_incident_edges,
            "totalInformativeAttributes": total_attributes,
            "totalIncidentEdgeOccurrences": total_incident_edges,
        },
        "relationalRichness": {
            "averageDistinctRelationTypesPerNode": safe_average(
                total_distinct_relation_types, node_count
            ),
            "totalPerNodeDistinctRelationTypes": total_distinct_relation_types,
        },
    }


def get_mention_count(node: JsonDict, attribute_name: str) -> int:
    """Return a positive mention count, defaulting to one per node."""
    attributes = node.get("attributes", {})
    value = attributes.get(attribute_name, 1)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            f"Node {node['id']!r} has invalid {attribute_name!r}: {value!r}; "
            "expected a positive integer"
        )
    return value


def make_ratio_record(unique_entities: int, total_mentions: int) -> JsonDict:
    """Create one consolidation-ratio result record."""
    ratio = float(unique_entities) / total_mentions if total_mentions else 0.0
    return {
        "uniqueCanonicalEntities": unique_entities,
        "totalEntityMentions": total_mentions,
        "ratio": round_metric(ratio),
    }


def compute_consolidation_metrics(
    nodes: list[JsonDict],
    mention_count_attribute: str,
    stage: str,
) -> JsonDict:
    """Compute global and per-class consolidation ratios."""
    unique_by_class: Counter[str] = Counter()
    mentions_by_class: Counter[str] = Counter()

    for node in nodes:
        class_name = node["class"]
        unique_by_class[class_name] += 1
        mentions_by_class[class_name] += get_mention_count(
            node, mention_count_attribute
        )

    total_unique = sum(unique_by_class.values())
    total_mentions = sum(mentions_by_class.values())
    per_type = {
        class_name: make_ratio_record(
            unique_by_class[class_name], mentions_by_class[class_name]
        )
        for class_name in sorted(unique_by_class)
    }

    uses_explicit_mentions = any(
        mention_count_attribute in node.get("attributes", {}) for node in nodes
    )
    interpretation = (
        "explicit_mention_counts"
        if uses_explicit_mentions
        else "mention_level_pre_consolidation"
    )

    return {
        "stage": stage,
        "interpretation": interpretation,
        "mentionCountAttribute": mention_count_attribute,
        "global": make_ratio_record(total_unique, total_mentions),
        "perEntityType": per_type,
    }


def sha256_file(path: Path) -> str:
    """Compute a file's SHA-256 digest without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    """Return a project-relative path when possible, otherwise the given path."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_results_record(
    data: JsonDict,
    input_path: Path,
    label: str,
    display_name: str,
    order: int,
    mention_count_attribute: str,
    consolidation_stage: str,
) -> JsonDict:
    """Build the complete deterministic snapshot results record."""
    structural = compute_structural_metrics(data)
    consolidation = compute_consolidation_metrics(
        data["nodes"], mention_count_attribute, consolidation_stage
    )

    return {
        "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
        "label": label,
        "displayName": display_name,
        "trajectoryOrder": order,
        "input": {
            "path": portable_path(input_path),
            "sha256": sha256_file(input_path),
        },
        "counts": {
            "nodes": len(data["nodes"]),
            "edges": len(data["edges"]),
        },
        "metrics": {
            **structural,
            "consolidation": consolidation,
        },
        "methodology": {
            "administrativeAttributeExclusionSet": sorted(
                ADMINISTRATIVE_ATTRIBUTE_KEYS
            ),
            "informationDensityDefinition": (
                "Average per node of nonempty informative attribute keys plus "
                "incident edge instances. Incoming and outgoing edges count; "
                "a self-loop counts once for its node."
            ),
            "informativeAttributeDefinition": (
                "Each nonempty node.attributes key not in the exclusion set "
                "counts once, regardless of value length."
            ),
            "relationalRichnessDefinition": (
                "Average per node of distinct incoming or outgoing relation names."
            ),
            "consolidationRatioDefinition": (
                "Unique canonical entity nodes divided by extracted entity "
                "mentions, globally and per class."
            ),
            "externalUrlStubNote": EXTERNAL_URL_STUB_NOTE,
        },
    }


def validate_label(label: str) -> str:
    """Validate that a snapshot label is safe as a filename and stable key."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", label):
        raise ValueError(
            "Label must start with an alphanumeric character and contain only "
            "letters, numbers, '.', '_', or '-'"
        )
    return label


def write_snapshot_record(record: JsonDict, snapshots_dir: Path) -> Path:
    """Write or replace one labeled snapshot JSON deterministically."""
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    output_path = snapshots_dir / f"{record['label']}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return output_path


def load_snapshot_records(snapshots_dir: Path) -> list[JsonDict]:
    """Load all valid metric snapshot records for trajectory rendering."""
    records: list[JsonDict] = []
    if not snapshots_dir.exists():
        return records
    for path in sorted(snapshots_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        if not isinstance(record, dict) or "label" not in record:
            raise ValueError(f"Invalid metric snapshot record: {path}")
        records.append(record)
    return sorted(
        records,
        key=lambda record: (
            int(record.get("trajectoryOrder", 1_000_000)),
            str(record["label"]),
        ),
    )


def format_metric(value: Any) -> str:
    """Format a metric value consistently for Markdown."""
    return f"{float(value):.{METRIC_DECIMAL_PLACES}f}"


def markdown_escape(value: str) -> str:
    """Escape table-sensitive characters in Markdown text."""
    return value.replace("|", "\\|").replace("\n", " ")


def render_trajectory_markdown(records: list[JsonDict]) -> str:
    """Render the §6.1 trajectory table with diagnostic density components."""
    exclusion_keys = ", ".join(
        f"`{key}`" for key in sorted(ADMINISTRATIVE_ATTRIBUTE_KEYS)
    )
    lines = [
        "# Structural Metrics Trajectory",
        "",
        "This table implements the internal trajectory structure from "
        "`docs/evaluation_decisions.md` §6.1. Information density is shown "
        "with its attribute and incident-edge components for diagnosis.",
        "",
        "| Construction point | Information density | Informative attributes / node | "
        "Incident edges / node | Relational richness | Consolidation ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for record in records:
        metrics = record["metrics"]
        density = metrics["informationDensity"]
        richness = metrics["relationalRichness"]
        consolidation = metrics["consolidation"]
        ratio = consolidation["global"]["ratio"]
        interpretation = consolidation["interpretation"].replace("_", " ")
        lines.append(
            "| {name} | {combined} | {attributes} | {edges} | {richness} | "
            "{ratio} ({interpretation}) |".format(
                name=markdown_escape(str(record["displayName"])),
                combined=format_metric(density["combinedAveragePerNode"]),
                attributes=format_metric(
                    density["averageInformativeAttributesPerNode"]
                ),
                edges=format_metric(density["averageIncidentEdgesPerNode"]),
                richness=format_metric(
                    richness["averageDistinctRelationTypesPerNode"]
                ),
                ratio=format_metric(ratio),
                interpretation=markdown_escape(interpretation),
            )
        )

    lines.extend(
        [
            "",
            "## Counting Policy",
            "",
            "Each nonempty informative attribute key counts once. Incoming and "
            "outgoing edge instances contribute to information density; distinct "
            "incident relation names contribute to relational richness. A self-loop "
            "counts once for its node.",
            "",
            f"**Administrative/identifier exclusion set:** {exclusion_keys}",
            "",
            f"**External URL stub note:** {EXTERNAL_URL_STUB_NOTE}",
            "",
        ]
    )
    return "\n".join(lines)


def update_trajectory_table(snapshots_dir: Path, table_path: Path) -> None:
    """Rebuild the trajectory Markdown table from all snapshot records."""
    records = load_snapshot_records(snapshots_dir)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.write_text(
        render_trajectory_markdown(records),
        encoding="utf-8",
    )


def print_summary(record: JsonDict, snapshot_path: Path, table_path: Path) -> None:
    """Print the principal metrics and per-class consolidation ratios."""
    counts = record["counts"]
    density = record["metrics"]["informationDensity"]
    richness = record["metrics"]["relationalRichness"]
    consolidation = record["metrics"]["consolidation"]

    print(f"Snapshot: {record['label']} ({record['displayName']})")
    print(f"Input: {record['input']['path']}")
    print(f"Nodes: {counts['nodes']}")
    print(f"Edges: {counts['edges']}")
    print(
        "Information density: "
        f"{format_metric(density['combinedAveragePerNode'])}"
    )
    print(
        "  Informative attributes per node: "
        f"{format_metric(density['averageInformativeAttributesPerNode'])}"
    )
    print(
        "  Incident edges per node: "
        f"{format_metric(density['averageIncidentEdgesPerNode'])}"
    )
    print(
        "Relational richness: "
        f"{format_metric(richness['averageDistinctRelationTypesPerNode'])}"
    )
    print(
        "Consolidation ratio (global): "
        f"{format_metric(consolidation['global']['ratio'])} "
        f"[{consolidation['interpretation']}]"
    )
    print("Consolidation ratio by entity type:")
    for class_name, values in consolidation["perEntityType"].items():
        print(
            f"  {class_name}: {format_metric(values['ratio'])} "
            f"({values['uniqueCanonicalEntities']}/"
            f"{values['totalEntityMentions']})"
        )
    print(f"Snapshot JSON: {portable_path(snapshot_path)}")
    print(f"Trajectory table: {portable_path(table_path)}")
    print(f"Note: {EXTERNAL_URL_STUB_NOTE}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Interim nodes/edges JSON snapshot")
    parser.add_argument(
        "--label",
        required=True,
        help="Stable snapshot key and output filename stem",
    )
    parser.add_argument(
        "--display-name",
        help="Human-readable trajectory row label; defaults to --label",
    )
    parser.add_argument(
        "--order",
        type=int,
        default=1_000,
        help="Numeric trajectory order used when rebuilding the Markdown table",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Directory containing snapshots/ and trajectory.md",
    )
    parser.add_argument(
        "--mention-count-attribute",
        default="mentionCount",
        help="Node attribute containing extracted mention counts after consolidation",
    )
    parser.add_argument(
        "--consolidation-stage",
        choices=("pre_consolidation", "after_alignment", "after_assembly"),
        default="pre_consolidation",
        help="Trajectory stage recorded with the consolidation metric",
    )
    return parser.parse_args()


def main() -> None:
    """Run structural metric computation and persist the labeled results."""
    args = parse_args()
    label = validate_label(args.label)
    display_name = args.display_name or label

    data = load_snapshot(args.input)
    validate_snapshot(data)
    record = build_results_record(
        data=data,
        input_path=args.input,
        label=label,
        display_name=display_name,
        order=args.order,
        mention_count_attribute=args.mention_count_attribute,
        consolidation_stage=args.consolidation_stage,
    )

    snapshots_dir = args.results_dir / "snapshots"
    snapshot_path = write_snapshot_record(record, snapshots_dir)
    table_path = args.results_dir / "trajectory.md"
    update_trajectory_table(snapshots_dir, table_path)
    print_summary(record, snapshot_path, table_path)


if __name__ == "__main__":
    main()
