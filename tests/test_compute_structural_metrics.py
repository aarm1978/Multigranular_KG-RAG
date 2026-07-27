"""Tests for schema-agnostic structural metrics and result recording."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation.compute_structural_metrics import (
    EVALUATOR_VERSION,
    FILE_INVENTORY_CLASSES,
    SNAPSHOT_SCHEMA_VERSION,
    build_attribute_accounting,
    build_results_record,
    compute_structural_metrics,
    count_informative_attributes,
    load_snapshot,
    load_snapshot_records,
    partition_file_inventory,
    render_trajectory_markdown,
    sha256_sorted_ids,
    update_trajectory_table,
    validate_snapshot,
    write_results_record,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HYDROSHARE_INPUT = PROJECT_ROOT / "data/interim/datasets/hydroshare_nodes_edges.json"
GITHUB_INPUT = PROJECT_ROOT / "data/interim/coderepos/github_nodes_edges.json"
CUMULATIVE_INPUT = PROJECT_ROOT / "data/interim/evaluation/hydroshare_github_deterministic.json"
CUMULATIVE_HUB_INPUT = PROJECT_ROOT / "data/interim/evaluation/hydroshare_github_hub_deterministic.json"
CUMULATIVE_PUBLICATIONS_INPUT = PROJECT_ROOT / "data/interim/evaluation/hydroshare_github_hub_publications_deterministic.json"


def node(
    node_id: str,
    class_name: str,
    attributes: dict[str, object],
    inventory_id: str | None = None,
) -> dict[str, object]:
    """Build a minimal metrics-compatible node."""
    result: dict[str, object] = {
        "id": node_id,
        "class": class_name,
        "attributes": attributes,
    }
    if inventory_id is not None:
        result["inventoryId"] = inventory_id
    return result


def edge(edge_id: str, source: str, target: str, relation: str = "relatedTo") -> dict[str, str]:
    """Build a minimal metrics-compatible edge."""
    return {"id": edge_id, "source": source, "target": target, "relation": relation}


class StructuralMetricsUnitTests(unittest.TestCase):
    """Exercise validation, policy, diagnostics, and rendering in isolation."""

    def test_graph_validation_and_duplicate_edge_rejection(self) -> None:
        """Valid endpoints pass while duplicate edge IDs fail."""
        validate_snapshot({"nodes": [node("a", "Thing", {})], "edges": []})
        graph = {
            "nodes": [node("a", "Thing", {}), node("b", "Thing", {})],
            "edges": [edge("e", "a", "b"), edge("e", "b", "a")],
        }
        with self.assertRaisesRegex(ValueError, "Duplicate edge ID"):
            validate_snapshot(graph)

    def test_unresolved_endpoint_rejection(self) -> None:
        """Every edge endpoint must resolve."""
        with self.assertRaisesRegex(ValueError, "target does not resolve"):
            validate_snapshot(
                {"nodes": [node("a", "Thing", {})], "edges": [edge("e", "a", "missing")]}
            )

    def test_file_inventory_policy_and_filtering_integrity(self) -> None:
        """Class policy, not degree or relation name, controls endpoint filtering."""
        graph = {
            "nodes": [
                node("repository", "Repository", {}),
                node("page", "DocumentationPage", {}),
                node("file", "File", {}, "A-C02"),
                node("dataset-file", "DatasetFile", {}, "A-D03"),
                node("repo-file", "RepoFile", {}, "A-C02"),
                node("leaf", "UnrelatedLeaf", {}),
                node("non-file", "ManifestEntry", {}),
            ],
            "edges": [
                edge("file-custom", "repository", "file", "customInventoryRelation"),
                edge("dataset-has-file", "repository", "dataset-file", "hasFile"),
                edge("repo-file-owner", "repository", "repo-file", "hasFile"),
                edge("repo-file-page", "page", "repo-file", "hasSourceFile"),
                edge("leaf-edge", "repository", "leaf", "relatedTo"),
                edge("non-file-has-file", "repository", "non-file", "hasFile"),
            ],
        }
        retained, audit = partition_file_inventory(graph)
        full_node_ids = {item["id"] for item in graph["nodes"]}
        retained_node_ids = {item["id"] for item in retained["nodes"]}
        excluded_node_ids = full_node_ids - retained_node_ids
        full_edge_ids = {item["id"] for item in graph["edges"]}
        retained_edge_ids = {item["id"] for item in retained["edges"]}
        excluded_edge_ids = full_edge_ids - retained_edge_ids

        self.assertEqual(FILE_INVENTORY_CLASSES, {"DatasetFile", "File", "RepoFile"})
        self.assertEqual(excluded_node_ids, {"file", "dataset-file", "repo-file"})
        self.assertTrue(retained_node_ids.isdisjoint(excluded_node_ids))
        self.assertEqual(retained_node_ids | excluded_node_ids, full_node_ids)
        self.assertTrue(retained_edge_ids.isdisjoint(excluded_edge_ids))
        self.assertEqual(retained_edge_ids | excluded_edge_ids, full_edge_ids)
        self.assertIn("leaf", retained_node_ids)
        self.assertIn("non-file", retained_node_ids)
        self.assertIn("non-file-has-file", retained_edge_ids)
        self.assertIn("file-custom", excluded_edge_ids)
        self.assertEqual(audit["excludedNodeCount"], 3)
        self.assertEqual(audit["excludedEdgeCount"], 4)
        self.assertEqual(
            audit["excludedEdgeCountsByRelation"],
            {
                "customInventoryRelation": 1,
                "hasFile": 2,
                "hasSourceFile": 1,
            },
        )
        for item in retained["edges"]:
            self.assertIn(item["source"], retained_node_ids)
            self.assertIn(item["target"], retained_node_ids)

    def test_approved_file_class_with_unexpected_inventory_id_fails(self) -> None:
        """Inventory IDs audit approved classes without becoming filter selectors."""
        for class_name, expected_id in {
            "DatasetFile": "A-D03",
            "File": "A-C02",
            "RepoFile": "A-C02",
        }.items():
            with self.subTest(class_name=class_name):
                invalid = {
                    "nodes": [node("x", class_name, {}, expected_id + "-wrong")],
                    "edges": [],
                }
                with self.assertRaisesRegex(ValueError, "must use inventoryId"):
                    validate_snapshot(invalid)

    def test_no_file_inventory_nodes_produce_identical_variants(self) -> None:
        """The sensitivity variant is a deterministic no-op without policy classes."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "graph.json"
            graph = {
                "nodes": [node("a", "Thing", {"name": "A"})],
                "edges": [],
            }
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            record = build_results_record(
                graph, input_path, "noop", "No-op", 1, "mentionCount", "pre_consolidation"
            )
        self.assertEqual(record["variants"]["full"], record["variants"]["fileInventoryExcluded"])
        audit = record["evaluationPolicy"]["fileInventorySensitivity"]
        self.assertEqual(audit["excludedNodeCount"], 0)
        self.assertEqual(audit["excludedEdgeCount"], 0)
        empty_digest = "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"
        self.assertEqual(audit["excludedNodeIdsSha256"], empty_digest)
        self.assertEqual(audit["excludedEdgeIdsSha256"], empty_digest)
        self.assertEqual(sha256_sorted_ids([]), empty_digest)

    def test_filtered_metrics_and_consolidation_are_recomputed(self) -> None:
        """Filtered metrics use retained numerators, denominators, and classes."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "graph.json"
            graph = {
                "nodes": [
                    node("thing", "Thing", {"name": "retained", "mentionCount": 2}),
                    node("file", "File", {"extension": ".md", "mentionCount": 3}, "A-C02"),
                ],
                "edges": [edge("e", "thing", "file", "hasFile")],
            }
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            record = build_results_record(
                graph, input_path, "filtered", "Filtered", 1, "mentionCount", "after_alignment"
            )
        full = record["variants"]["full"]
        filtered = record["variants"]["fileInventoryExcluded"]
        self.assertEqual(full["counts"], {"nodes": 2, "edges": 1})
        self.assertEqual(filtered["counts"], {"nodes": 1, "edges": 0})
        self.assertEqual(full["metrics"]["informationDensity"]["combinedAveragePerNode"], 2.0)
        self.assertEqual(filtered["metrics"]["informationDensity"]["combinedAveragePerNode"], 1.0)
        self.assertEqual(filtered["metrics"]["informationDensity"]["averageIncidentEdgesPerNode"], 0.0)
        self.assertEqual(filtered["metrics"]["relationalRichness"]["averageDistinctRelationTypesPerNode"], 0.0)
        self.assertEqual(filtered["metrics"]["consolidation"]["global"]["ratio"], 0.5)
        self.assertEqual(filtered["metrics"]["consolidation"]["perEntityType"]["Thing"]["ratio"], 0.5)
        self.assertNotIn("File", filtered["metrics"]["byEntityType"])
        self.assertNotIn("File", filtered["metrics"]["consolidation"]["perEntityType"])
        self.assertNotIn("File", filtered["attributeAccounting"]["counted"])

    def test_false_boolean_policy(self) -> None:
        """Informative False counts, while globally excluded False does not."""
        self.assertEqual(count_informative_attributes("Repository", {"archived": False}), 1)
        self.assertEqual(count_informative_attributes("File", {"downloaded": False}), 0)

    def test_global_and_class_specific_exclusions(self) -> None:
        """Global and contextual rules exclude only their declared keys."""
        self.assertEqual(
            count_informative_attributes("Person", {"name": "Ada", "sourceRepoId": 1}),
            1,
        )

    def test_focused_tool_and_repository_exclusions(self) -> None:
        """Source representations are contextual while semantic values still count."""
        tool_attributes = {
            "declaredLicenseKind": "text",
            "declaredLicenseSourceValue": {"text": "MIT"},
            "repository": "https://github.com/example/tool",
            "repositoryCode": "https://github.com/example/tool",
            "declaredLicense": "MIT",
        }
        repository_attributes = {
            "owner": "example",
            "forkParent": "https://github.com/example/upstream",
            "name": "tool",
        }
        self.assertEqual(count_informative_attributes("Tool", tool_attributes), 1)
        self.assertEqual(count_informative_attributes("Repository", repository_attributes), 1)
        self.assertEqual(count_informative_attributes("Other", {"owner": "example"}), 1)
        self.assertEqual(
            count_informative_attributes("Other", {"repository": "https://example.test"}),
            1,
        )
        accounting = build_attribute_accounting(
            [node("tool", "Tool", tool_attributes), node("repo", "Repository", repository_attributes)]
        )
        for class_name, keys in {
            "Tool": (
                "declaredLicenseKind",
                "declaredLicenseSourceValue",
                "repository",
                "repositoryCode",
            ),
            "Repository": ("owner", "forkParent"),
        }.items():
            for key in keys:
                self.assertEqual(
                    accounting["excluded"][class_name][key]["rule"],
                    "class_specific_administrative",
                )
        self.assertEqual(accounting["counted"]["Tool"]["declaredLicense"], 1)
        self.assertEqual(accounting["counted"]["Repository"]["name"], 1)
        self.assertEqual(
            count_informative_attributes(
                "ExecutionEnvironment", {"prefix": "/tmp/env", "kind": "conda"}
            ),
            1,
        )

    def test_file_policy_preserves_semantic_structure(self) -> None:
        """File extension/role count while identity and storage fields do not."""
        attributes = {
            "fileName": "README.md",
            "extension": ".md",
            "fileRole": "readme",
            "downloaded": False,
            "contentAvailable": False,
            "sizeBytes": 10,
            "selectionReason": None,
            "path": "docs/README.md",
            "sourceRepoId": 1,
        }
        self.assertEqual(count_informative_attributes("File", attributes), 2)

    def test_identifier_value_and_type_are_contextually_excluded(self) -> None:
        """Identifier identity fields do not inflate descriptive density."""
        self.assertEqual(
            count_informative_attributes("Identifier", {"idType": "doi", "value": "10/x"}),
            0,
        )

    def test_by_class_totals_reconcile_with_global_totals(self) -> None:
        """Per-class structural totals sum exactly to global totals."""
        graph = {
            "nodes": [node("a", "A", {"name": "a"}), node("b", "B", {"flag": False})],
            "edges": [edge("e", "a", "b")],
        }
        metrics = compute_structural_metrics(graph)
        by_type = metrics["byEntityType"]
        self.assertEqual(
            sum(value["nodeCount"] for value in by_type.values()), len(graph["nodes"])
        )
        self.assertEqual(
            sum(value["informationDensity"]["totalInformativeAttributes"] for value in by_type.values()),
            metrics["informationDensity"]["totalInformativeAttributes"],
        )
        self.assertEqual(
            sum(value["informationDensity"]["totalIncidentEdgeOccurrences"] for value in by_type.values()),
            metrics["informationDensity"]["totalIncidentEdgeOccurrences"],
        )
        self.assertEqual(
            sum(value["relationalRichness"]["totalPerNodeDistinctRelationTypes"] for value in by_type.values()),
            metrics["relationalRichness"]["totalPerNodeDistinctRelationTypes"],
        )
        for values in by_type.values():
            density = values["informationDensity"]
            self.assertEqual(
                density["combinedAveragePerNode"],
                round(
                    (
                        density["totalInformativeAttributes"]
                        + density["totalIncidentEdgeOccurrences"]
                    )
                    / values["nodeCount"],
                    6,
                ),
            )

    def test_attribute_accounting_is_deterministic(self) -> None:
        """Accounting is class/key sorted and independent of input order."""
        nodes = [node("b", "File", {"fileRole": "readme", "fileName": "x"}), node("a", "File", {"extension": ".md"})]
        self.assertEqual(build_attribute_accounting(nodes), build_attribute_accounting(list(reversed(nodes))))
        accounting = build_attribute_accounting(nodes)
        self.assertEqual(accounting["counted"]["File"], {"extension": 1, "fileRole": 1})
        self.assertEqual(accounting["excluded"]["File"]["fileName"]["count"], 1)

    def test_record_series_and_consolidation_rendering(self) -> None:
        """Modules stay isolated and mention-level trajectory ratios render as a dash."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "graph.json"
            graph = {"nodes": [node("a", "Thing", {"name": "a"})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            module = build_results_record(graph, input_path, "module", "Module", 5, "mentionCount", "pre_consolidation", "module")
            write_results_record(module, root / "results", "module")
            self.assertFalse((root / "results/trajectory.md").exists())
            trajectory = build_results_record(graph, input_path, "trajectory", "Trajectory", 10, "mentionCount", "pre_consolidation", "trajectory")
            write_results_record(trajectory, root / "results", "trajectory")
            update_trajectory_table(root / "results/snapshots", root / "results/trajectory.md")
            markdown = (root / "results/trajectory.md").read_text(encoding="utf-8")
            self.assertIn("Trajectory", markdown)
            self.assertNotIn("| Module |", markdown)
            self.assertIn("1.000000 (mention level pre consolidation)", markdown)

    def test_explicit_mentions_render_numeric_ratio(self) -> None:
        """Post-alignment explicit mention counts render numerically."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "graph.json"
            graph = {"nodes": [node("a", "Thing", {"mentionCount": 2})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            record = build_results_record(graph, input_path, "aligned", "Aligned", 1, "mentionCount", "after_alignment")
            markdown = render_trajectory_markdown([record])
            self.assertIn("0.500000 (explicit mention counts)", markdown)

    def test_consolidation_definition_has_correct_direction_and_caveat(self) -> None:
        """The stored methodology explains ratio direction without claiming quality."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "graph.json"
            graph = {"nodes": [node("a", "Thing", {})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            record = build_results_record(
                graph,
                input_path,
                "definition",
                "Definition",
                1,
                "mentionCount",
                "pre_consolidation",
            )
            definition = record["methodology"]["consolidationRatioDefinition"]
            self.assertIn("Lower values indicate greater consolidation", definition)
            self.assertIn("over-merging can also reduce it", definition)
            self.assertNotIn("Higher", definition)

    def test_cumulative_trajectory_has_two_rows_and_no_module(self) -> None:
        """Only cumulative records render in each of the three deterministic tables."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "graph.json"
            graph = {"nodes": [node("a", "Thing", {})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            results_dir = root / "results"
            hydro = build_results_record(graph, input_path, "hydro", "HydroShare (det.)", 10, "mentionCount", "pre_consolidation", "trajectory")
            cumulative = build_results_record(graph, input_path, "cumulative", "+ GitHub (det.)", 20, "mentionCount", "pre_consolidation", "trajectory")
            module = build_results_record(graph, input_path, "github", "GitHub (det., module only)", 1, "mentionCount", "pre_consolidation", "module")
            write_results_record(cumulative, results_dir, "trajectory")
            write_results_record(hydro, results_dir, "trajectory")
            write_results_record(module, results_dir, "module")
            update_trajectory_table(results_dir / "snapshots", results_dir / "trajectory.md")
            markdown = (results_dir / "trajectory.md").read_text(encoding="utf-8")
            self.assertIn("Table A — Full KG", markdown)
            self.assertIn("Table B — File-inventory-excluded sensitivity analysis", markdown)
            self.assertIn("Table C — Sensitivity effect", markdown)
            self.assertEqual(markdown.count("| HydroShare (det.) |"), 3)
            self.assertEqual(markdown.count("| + GitHub (det.) |"), 3)
            self.assertNotIn("module only", markdown)

    def test_schema_12_contract_has_two_variants_and_no_legacy_roots(self) -> None:
        """Schema 1.2 records expose policy audit metadata without duplicate roots."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "graph.json"
            graph = {"nodes": [node("a", "Thing", {})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            record = build_results_record(
                graph, input_path, "contract", "Contract", 1, "mentionCount", "pre_consolidation"
            )
        self.assertEqual(record["schemaVersion"], SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(record["schemaVersion"], "1.2")
        self.assertEqual(record["evaluatorVersion"], EVALUATOR_VERSION)
        self.assertEqual(record["evaluatorVersion"], "1.2.0")
        self.assertEqual(set(record["variants"]), {"full", "fileInventoryExcluded"})
        self.assertNotIn("counts", record)
        self.assertNotIn("metrics", record)
        self.assertNotIn("attributeAccounting", record)
        audit = record["evaluationPolicy"]["fileInventorySensitivity"]
        for key in (
            "excludedClasses",
            "expectedInventoryIdsByClass",
            "edgeExclusionRule",
            "excludedNodeCount",
            "excludedNodeCountsByClass",
            "excludedEdgeCount",
            "excludedEdgeCountsByRelation",
            "excludedNodeIdsSha256",
            "excludedEdgeIdsSha256",
        ):
            self.assertIn(key, audit)

    def test_trajectory_loader_rejects_every_non_12_snapshot(self) -> None:
        """Schema migration cannot silently mix old and new metric records."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, version in (("old-a", "1.1"), ("current", "1.2"), ("old-b", "1.1")):
                (root / f"{name}.json").write_text(
                    json.dumps({"label": name, "schemaVersion": version}),
                    encoding="utf-8",
                )
            with self.assertRaises(ValueError) as context:
                load_snapshot_records(root)
            message = str(context.exception)
            self.assertIn("old-a.json", message)
            self.assertIn("old-b.json", message)
            self.assertNotIn("current.json", message)

    def test_snapshot_json_and_markdown_are_deterministic(self) -> None:
        """Equivalent runs produce byte-identical JSON and Markdown."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "graph.json"
            graph = {"nodes": [node("a", "Thing", {"name": "A"})], "edges": []}
            input_path.write_text(json.dumps(graph), encoding="utf-8")
            first = build_results_record(
                graph, input_path, "stable", "Stable", 1, "mentionCount", "pre_consolidation"
            )
            second = build_results_record(
                graph, input_path, "stable", "Stable", 1, "mentionCount", "pre_consolidation"
            )
            first_path = write_results_record(first, root / "one", "trajectory")
            second_path = write_results_record(second, root / "two", "trajectory")
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(render_trajectory_markdown([first]), render_trajectory_markdown([second]))


@unittest.skipUnless(HYDROSHARE_INPUT.exists(), "HydroShare frozen graph unavailable")
class FrozenMetricsRegressionTests(unittest.TestCase):
    """Check the ratified policy against frozen source-module graphs."""

    def test_hydroshare_regression(self) -> None:
        """HydroShare metrics match the revised policy anchors."""
        graph = load_snapshot(HYDROSHARE_INPUT)
        validate_snapshot(graph)
        metrics = compute_structural_metrics(graph)
        density = metrics["informationDensity"]
        richness = metrics["relationalRichness"]
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (1288, 1613))
        self.assertEqual(density["totalInformativeAttributes"], 1662)
        self.assertEqual(density["averageInformativeAttributesPerNode"], 1.290373)
        self.assertEqual(density["averageIncidentEdgesPerNode"], 2.504658)
        self.assertEqual(density["combinedAveragePerNode"], 3.795031)
        self.assertEqual(richness["averageDistinctRelationTypesPerNode"], 1.346273)
        self.assertEqual(richness["totalPerNodeDistinctRelationTypes"], 1734)
        self.assertEqual(
            metrics["byEntityType"]["DatasetResource"]["informationDensity"]["combinedAveragePerNode"],
            21.674419,
        )

    @unittest.skipUnless(GITHUB_INPUT.exists(), "GitHub frozen graph unavailable")
    def test_github_file_accounting_regression(self) -> None:
        """GitHub File administration is excluded while extension and role remain."""
        graph = load_snapshot(GITHUB_INPUT)
        validate_snapshot(graph)
        accounting = build_attribute_accounting(graph["nodes"])
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (12708, 12670))
        for key in ("downloaded", "contentAvailable", "fileName", "sizeBytes", "selectionReason", "path", "sourceRepoId"):
            self.assertIn(key, accounting["excluded"]["File"])
        self.assertEqual(accounting["counted"]["File"]["extension"], 11443)
        self.assertEqual(accounting["counted"]["File"]["fileRole"], 11702)

    @unittest.skipUnless(GITHUB_INPUT.exists(), "GitHub frozen graph unavailable")
    def test_github_focused_policy_regression(self) -> None:
        """GitHub density and affected class diagnostics match the frozen policy."""
        graph = load_snapshot(GITHUB_INPUT)
        metrics = compute_structural_metrics(graph)
        density = metrics["informationDensity"]
        richness = metrics["relationalRichness"]
        self.assertEqual(density["totalInformativeAttributes"], 25188)
        self.assertEqual(density["averageInformativeAttributesPerNode"], 1.982059)
        self.assertEqual(density["averageIncidentEdgesPerNode"], 1.994020)
        self.assertEqual(density["combinedAveragePerNode"], 3.976078)
        self.assertEqual(richness["averageDistinctRelationTypesPerNode"], 1.017469)
        self.assertEqual(richness["totalPerNodeDistinctRelationTypes"], 12930)
        tool = metrics["byEntityType"]["Tool"]
        repository = metrics["byEntityType"]["Repository"]
        self.assertEqual(tool["informationDensity"]["totalInformativeAttributes"], 81)
        self.assertEqual(tool["informationDensity"]["combinedAveragePerNode"], 4.0)
        self.assertEqual(repository["informationDensity"]["totalInformativeAttributes"], 444)
        self.assertEqual(repository["informationDensity"]["combinedAveragePerNode"], 233.089286)
        self.assertEqual(
            metrics["byEntityType"]["Person"]["informationDensity"]["combinedAveragePerNode"],
            1.751825,
        )

    @unittest.skipUnless(GITHUB_INPUT.exists(), "GitHub frozen graph unavailable")
    def test_github_focused_attribute_accounting(self) -> None:
        """All six focused keys are excluded with observed frozen counts."""
        accounting = build_attribute_accounting(load_snapshot(GITHUB_INPUT)["nodes"])
        expected = {
            "Tool": {
                "declaredLicenseKind": 27,
                "declaredLicenseSourceValue": 21,
                "repository": 0,
                "repositoryCode": 0,
            },
            "Repository": {"owner": 5, "forkParent": 0},
        }
        for class_name, keys in expected.items():
            for key, count in keys.items():
                self.assertNotIn(key, accounting["counted"].get(class_name, {}))
                self.assertEqual(accounting["excluded"][class_name][key]["count"], count)
                self.assertEqual(
                    accounting["excluded"][class_name][key]["rule"],
                    "class_specific_administrative",
                )

    @unittest.skipUnless(CUMULATIVE_INPUT.exists(), "Cumulative frozen graph unavailable")
    def test_cumulative_focused_policy_regression(self) -> None:
        """Cumulative density and affected classes match the corrected policy."""
        graph = load_snapshot(CUMULATIVE_INPUT)
        metrics = compute_structural_metrics(graph)
        density = metrics["informationDensity"]
        richness = metrics["relationalRichness"]
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (13996, 14283))
        self.assertEqual(density["totalInformativeAttributes"], 26850)
        self.assertEqual(density["averageInformativeAttributesPerNode"], 1.918405)
        self.assertEqual(density["averageIncidentEdgesPerNode"], 2.041012)
        self.assertEqual(density["combinedAveragePerNode"], 3.959417)
        self.assertEqual(richness["averageDistinctRelationTypesPerNode"], 1.047728)
        self.assertEqual(richness["totalPerNodeDistinctRelationTypes"], 14664)
        tool = metrics["byEntityType"]["Tool"]
        repository = metrics["byEntityType"]["Repository"]
        self.assertEqual(tool["informationDensity"]["totalInformativeAttributes"], 84)
        self.assertEqual(tool["informationDensity"]["combinedAveragePerNode"], 3.941176)
        self.assertEqual(repository["informationDensity"]["totalInformativeAttributes"], 448)
        self.assertEqual(repository["informationDensity"]["combinedAveragePerNode"], 217.716667)
        self.assertEqual(
            metrics["byEntityType"]["Person"]["informationDensity"]["combinedAveragePerNode"],
            2.203704,
        )

    @unittest.skipUnless(CUMULATIVE_HUB_INPUT.exists(), "Hub cumulative graph unavailable")
    def test_hub_cumulative_full_and_filtered_regression(self) -> None:
        """The accepted Hub full values remain fixed and sensitivity values are anchored."""
        graph = load_snapshot(CUMULATIVE_HUB_INPUT)
        retained, audit = partition_file_inventory(graph)
        full = compute_structural_metrics(graph)
        filtered = compute_structural_metrics(retained)
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (18663, 20836))
        self.assertEqual(full["informationDensity"]["combinedAveragePerNode"], 5.567219)
        self.assertEqual(full["informationDensity"]["averageInformativeAttributesPerNode"], 3.334351)
        self.assertEqual(full["informationDensity"]["averageIncidentEdgesPerNode"], 2.232867)
        self.assertEqual(full["relationalRichness"]["averageDistinctRelationTypesPerNode"], 1.152869)
        self.assertEqual((len(retained["nodes"]), len(retained["edges"])), (5962, 7893))
        self.assertEqual(filtered["informationDensity"]["combinedAveragePerNode"], 8.748071)
        self.assertEqual(filtered["relationalRichness"]["averageDistinctRelationTypesPerNode"], 1.382254)
        self.assertEqual(audit["excludedNodeCountsByClass"], {"DatasetFile": 757, "File": 11702, "RepoFile": 242})
        self.assertEqual(audit["excludedEdgeCountsByRelation"], {"hasFile": 12701, "hasSourceFile": 242})

    @unittest.skipUnless(
        CUMULATIVE_PUBLICATIONS_INPUT.exists(),
        "Four-module cumulative graph unavailable",
    )
    def test_publications_cumulative_full_and_filtered_regression(self) -> None:
        """The complete deterministic trajectory point has frozen variant anchors."""
        graph = load_snapshot(CUMULATIVE_PUBLICATIONS_INPUT)
        retained, audit = partition_file_inventory(graph)
        full = compute_structural_metrics(graph)
        filtered = compute_structural_metrics(retained)
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (28319, 32608))
        self.assertEqual(full["informationDensity"]["combinedAveragePerNode"], 5.51499)
        self.assertEqual(full["informationDensity"]["averageInformativeAttributesPerNode"], 3.212084)
        self.assertEqual(full["informationDensity"]["averageIncidentEdgesPerNode"], 2.302906)
        self.assertEqual(full["relationalRichness"]["averageDistinctRelationTypesPerNode"], 1.133656)
        self.assertEqual((len(retained["nodes"]), len(retained["edges"])), (15618, 19665))
        self.assertEqual(filtered["informationDensity"]["combinedAveragePerNode"], 6.686772)
        self.assertEqual(filtered["relationalRichness"]["averageDistinctRelationTypesPerNode"], 1.205596)
        self.assertEqual(audit["excludedNodeCount"], 12701)
        self.assertEqual(audit["excludedEdgeCount"], 12943)

    def test_frozen_file_inventory_degree_distributions(self) -> None:
        """Frozen inventory classes retain the audited counts and degrees."""
        cases = (
            (HYDROSHARE_INPUT, "DatasetFile", 757, {1: 757}, {"hasFile"}),
            (GITHUB_INPUT, "File", 11702, {1: 11702}, {"hasFile"}),
            (PROJECT_ROOT / "data/interim/documents/ciroh_hub_nodes_edges.json", "RepoFile", 242, {2: 242}, {"hasFile", "hasSourceFile"}),
        )
        for path, class_name, expected_count, expected_degrees, expected_relations in cases:
            with self.subTest(class_name=class_name):
                graph = load_snapshot(path)
                class_ids = {item["id"] for item in graph["nodes"] if item["class"] == class_name}
                incident_by_id = {node_id: [] for node_id in class_ids}
                for item in graph["edges"]:
                    for endpoint in {item["source"], item["target"]}:
                        if endpoint in incident_by_id:
                            incident_by_id[endpoint].append(item)
                degree_counts: dict[int, int] = {}
                relations: set[str] = set()
                for node_id in class_ids:
                    incident = incident_by_id[node_id]
                    degree_counts[len(incident)] = degree_counts.get(len(incident), 0) + 1
                    relations.update(str(item["relation"]) for item in incident)
                self.assertEqual(len(class_ids), expected_count)
                self.assertEqual(degree_counts, expected_degrees)
                self.assertEqual(relations, expected_relations)


if __name__ == "__main__":
    unittest.main()
