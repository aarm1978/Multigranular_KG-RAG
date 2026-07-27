"""Build a deterministic cumulative pre-alignment nodes/edges snapshot.

Each ``--component LABEL=PATH`` input is validated independently, then its nodes
and edges are concatenated without consolidation, alignment, target resolution,
or canonical-key matching. Duplicate IDs and unresolved endpoints fail loudly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.evaluation.compute_structural_metrics import (
    JsonDict,
    load_snapshot,
    portable_path,
    sha256_file,
    validate_label,
    validate_snapshot,
)


CUMULATIVE_SNAPSHOT_SCHEMA_VERSION = "1.0"
CUMULATIVE_SNAPSHOT_TYPE = "cumulative_pre_alignment"


def parse_component(value: str) -> tuple[str, Path]:
    """Parse and validate one ``LABEL=PATH`` component argument."""
    label, separator, path_text = value.partition("=")
    if not separator or not path_text:
        raise argparse.ArgumentTypeError("Component must use LABEL=PATH")
    try:
        validate_label(label)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return label, Path(path_text)


def build_cumulative_snapshot(components: Sequence[tuple[str, Path]]) -> JsonDict:
    """Validate and concatenate components without semantic deduplication."""
    if not components:
        raise ValueError("At least one component is required")
    labels = [label for label, _ in components]
    if len(labels) != len(set(labels)):
        duplicate = next(label for label in labels if labels.count(label) > 1)
        raise ValueError(f"Duplicate component label: {duplicate}")

    combined_nodes: list[JsonDict] = []
    combined_edges: list[JsonDict] = []
    component_records: list[JsonDict] = []
    node_origins: dict[str, str] = {}
    edge_origins: dict[str, str] = {}

    for label, path in sorted(components, key=lambda item: item[0]):
        graph = load_snapshot(path)
        validate_snapshot(graph)
        for node in graph["nodes"]:
            node_id = str(node["id"])
            if node_id in node_origins:
                raise ValueError(
                    f"Duplicate node ID across components: {node_id} "
                    f"({node_origins[node_id]} and {label})"
                )
            node_origins[node_id] = label
            combined_nodes.append(node)
        for edge in graph["edges"]:
            edge_id = str(edge["id"])
            if edge_id in edge_origins:
                raise ValueError(
                    f"Duplicate edge ID across components: {edge_id} "
                    f"({edge_origins[edge_id]} and {label})"
                )
            edge_origins[edge_id] = label
            combined_edges.append(edge)
        component_records.append(
            {
                "label": label,
                "path": portable_path(path),
                "sha256": sha256_file(path),
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
            }
        )

    combined_nodes.sort(key=lambda node: str(node["id"]))
    combined_edges.sort(key=lambda edge: str(edge["id"]))
    combined_graph: JsonDict = {"nodes": combined_nodes, "edges": combined_edges}
    validate_snapshot(combined_graph)
    return {
        "snapshot_schema_version": CUMULATIVE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_type": CUMULATIVE_SNAPSHOT_TYPE,
        "components": component_records,
        "nodes": combined_nodes,
        "edges": combined_edges,
    }


def write_cumulative_snapshot(snapshot: JsonDict, output_path: Path) -> None:
    """Write a cumulative snapshot with stable UTF-8 JSON serialization."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    """Parse cumulative snapshot builder arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--component",
        action="append",
        required=True,
        type=parse_component,
        metavar="LABEL=PATH",
        help="Labeled source graph; repeat for each cumulative component",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    """Build, validate, write, and summarize a cumulative snapshot."""
    args = parse_args()
    snapshot = build_cumulative_snapshot(args.component)
    write_cumulative_snapshot(snapshot, args.output)
    print(f"Snapshot type: {snapshot['snapshot_type']}")
    for component in snapshot["components"]:
        print(
            f"Component {component['label']}: "
            f"{component['nodes']} nodes, {component['edges']} edges, "
            f"sha256={component['sha256']}"
        )
    print(f"Nodes: {len(snapshot['nodes'])}")
    print(f"Edges: {len(snapshot['edges'])}")
    print(f"Valid: True")
    print(f"Wrote: {portable_path(args.output)}")


if __name__ == "__main__":
    main()
