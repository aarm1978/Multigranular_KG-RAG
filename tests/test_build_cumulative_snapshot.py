"""Tests for deterministic cumulative pre-alignment snapshot construction."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation.build_cumulative_snapshot import (
    build_cumulative_snapshot,
    write_cumulative_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HYDROSHARE_INPUT = PROJECT_ROOT / "data/interim/datasets/hydroshare_nodes_edges.json"
GITHUB_INPUT = PROJECT_ROOT / "data/interim/coderepos/github_nodes_edges.json"
CIROH_HUB_INPUT = PROJECT_ROOT / "data/interim/documents/ciroh_hub_nodes_edges.json"
PUBLICATIONS_INPUT = PROJECT_ROOT / "data/interim/papers/publication_nodes_edges.json"


def graph(node_id: str, edge_id: str | None = None, target: str | None = None) -> dict[str, object]:
    """Build one minimal component graph."""
    nodes = [{"id": node_id, "class": "Thing", "attributes": {"canonicalKey": "shared"}}]
    edges = [] if edge_id is None else [{"id": edge_id, "source": node_id, "target": target or node_id, "relation": "relatedTo"}]
    return {"nodes": nodes, "edges": edges}


def write_graph(path: Path, value: dict[str, object]) -> None:
    """Write a temporary component graph."""
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class CumulativeSnapshotUnitTests(unittest.TestCase):
    """Exercise strict validation and no-dedup cumulative semantics."""

    def test_builder_performs_no_semantic_deduplication(self) -> None:
        """Distinct IDs survive even when canonical attributes match."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.json", root / "b.json"
            write_graph(first, graph("a"))
            write_graph(second, graph("b"))
            snapshot = build_cumulative_snapshot([("a", first), ("b", second)])
            self.assertEqual([item["id"] for item in snapshot["nodes"]], ["a", "b"])

    def test_cross_component_node_collision_rejected(self) -> None:
        """Identical node IDs across components fail loudly."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.json", root / "b.json"
            write_graph(first, graph("same"))
            write_graph(second, graph("same"))
            with self.assertRaisesRegex(ValueError, "Duplicate node ID across components"):
                build_cumulative_snapshot([("a", first), ("b", second)])

    def test_cross_component_edge_collision_rejected(self) -> None:
        """Identical edge IDs across components fail loudly."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.json", root / "b.json"
            write_graph(first, graph("a", "same-edge"))
            write_graph(second, graph("b", "same-edge"))
            with self.assertRaisesRegex(ValueError, "Duplicate edge ID across components"):
                build_cumulative_snapshot([("a", first), ("b", second)])

    def test_unresolved_component_endpoint_rejected(self) -> None:
        """A component cannot carry an unresolved endpoint into the cumulative graph."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            write_graph(path, graph("a", "e", "missing"))
            with self.assertRaisesRegex(ValueError, "target does not resolve"):
                build_cumulative_snapshot([("bad", path)])

    def test_component_order_independence_and_byte_stability(self) -> None:
        """Input ordering cannot affect the wrapper or serialized bytes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.json", root / "b.json"
            write_graph(first, graph("a", "ea"))
            write_graph(second, graph("b", "eb"))
            forward = build_cumulative_snapshot([("a", first), ("b", second)])
            reverse = build_cumulative_snapshot([("b", second), ("a", first)])
            self.assertEqual(forward, reverse)
            output_one, output_two = root / "one.json", root / "two.json"
            write_cumulative_snapshot(forward, output_one)
            write_cumulative_snapshot(reverse, output_two)
            self.assertEqual(output_one.read_bytes(), output_two.read_bytes())
            self.assertEqual(
                hashlib.sha256(output_one.read_bytes()).hexdigest(),
                hashlib.sha256(output_two.read_bytes()).hexdigest(),
            )


@unittest.skipUnless(
    HYDROSHARE_INPUT.exists() and GITHUB_INPUT.exists(),
    "Frozen source-module graphs unavailable",
)
class FrozenCumulativeRegressionTests(unittest.TestCase):
    """Validate the current HydroShare + GitHub cumulative graph anchors."""

    def test_frozen_cumulative_counts_and_component_sums(self) -> None:
        """The frozen components concatenate without collisions or removals."""
        snapshot = build_cumulative_snapshot(
            [("hydroshare", HYDROSHARE_INPUT), ("github", GITHUB_INPUT)]
        )
        self.assertEqual(len(snapshot["nodes"]), 13996)
        self.assertEqual(len(snapshot["edges"]), 14283)
        self.assertEqual(sum(item["nodes"] for item in snapshot["components"]), 13996)
        self.assertEqual(sum(item["edges"] for item in snapshot["components"]), 14283)

    @unittest.skipUnless(
        CIROH_HUB_INPUT.exists() and PUBLICATIONS_INPUT.exists(),
        "All four frozen source-module graphs unavailable",
    )
    def test_four_component_cumulative_provenance_and_counts(self) -> None:
        """The complete point retains deterministic component paths and hashes."""
        components = [
            ("publications", PUBLICATIONS_INPUT),
            ("hydroshare", HYDROSHARE_INPUT),
            ("ciroh_hub", CIROH_HUB_INPUT),
            ("github", GITHUB_INPUT),
        ]
        snapshot = build_cumulative_snapshot(components)
        self.assertEqual(snapshot["snapshot_schema_version"], "1.0")
        self.assertEqual(snapshot["snapshot_type"], "cumulative_pre_alignment")
        self.assertEqual(len(snapshot["nodes"]), 28319)
        self.assertEqual(len(snapshot["edges"]), 32608)
        self.assertEqual(
            [item["label"] for item in snapshot["components"]],
            ["ciroh_hub", "github", "hydroshare", "publications"],
        )
        for record in snapshot["components"]:
            self.assertIn("path", record)
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(record["nodes"], 0)
            self.assertGreater(record["edges"], 0)


if __name__ == "__main__":
    unittest.main()
