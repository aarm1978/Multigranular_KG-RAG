"""Minimal prospective HydroShare corrections and historical isolation."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from src.extraction.deterministic.extract_hydroshare import (
    DEFAULT_INPUT, DEFAULT_OUTPUT, HISTORICAL_OUTPUT, extract_corpus,
    make_edge_id, normalize_own_doi, write_output,
)
from src.evaluation.build_cumulative_snapshot import build_cumulative_snapshot
from src.evaluation.compute_structural_metrics import (
    build_results_record, compute_structural_metrics, partition_file_inventory,
    render_trajectory_markdown, validate_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/fixtures/hydroshare/pre_v016_hashes.json"


def resource() -> dict:
    """Return a minimal resource with existing contributor and award assertions."""
    return {
        "resource_id": "a" * 32, "resource_type": "CompositeResource",
        "identifier": "https://www.hydroshare.org/resource/" + "a" * 32,
        "contributors": [{"name": "Example Contributor"}],
        "awards": [{"number": "1", "funding_agency_name": "Example Agency"}],
    }


class OwnDoiTests(unittest.TestCase):
    """Check lexical acceptance, exact evidence, identity and frozen-path safety."""

    def test_complete_tokens_and_rejections(self) -> None:
        """Prose, foreign hosts, malformed types and partial DOI tokens fail closed."""
        for value in ("10.1234/ABC-1", "doi:10.1234/ABC-1", "https://doi.org/10.1234/ABC-1", " HTTP://DX.DOI.ORG/10.1234/ABC-1 "):
            self.assertEqual(normalize_own_doi(value), "10.1234/abc-1")
        for value in (None, 12, [], {}, "", "10.123/x", "10.1234/", "10.1234/a b", "See 10.1234/abc", "https://example.org/10.1234/abc", "https://doi.org.evil/10.1234/abc", "https://doi.org/10.1234/abc?x=1", "10.1234/x#y", "10.1234/abc.", "10.1234/(abc"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_own_doi(value))

    def test_exact_evidence_and_duplicate_forms(self) -> None:
        """Only one own DOI assertion survives equivalent identifier/URL fields."""
        r = resource()
        raw = "  DOI:10.1234/ABC-1  "
        r.update(system_metadata={"doi": raw}, identifier="https://doi.org/10.1234/abc-1", url="10.1234/ABC-1")
        graph, _ = extract_corpus([r, copy.deepcopy(r)])
        identifiers = [n for n in graph["nodes"] if n["class"] == "Identifier"]
        self.assertEqual(len(identifiers), 1)
        n = identifiers[0]
        self.assertEqual(n["attributes"], {"identifierValue": "10.1234/abc-1", "identifierType": "DOI"})
        edges = [e for e in graph["edges"] if e["relation"] == "hasIdentifier"]
        self.assertEqual(len(edges), 1)
        for item in (n, edges[0]):
            self.assertEqual(item["evidence"]["evidenceText"], raw)
            self.assertEqual(item["evidence"]["sourceLocation"], r["resource_id"] + ":system_metadata.doi")
            self.assertEqual(item["evidence"]["sourceArtifact"], "hydroshare:" + r["resource_id"])
        self.assertEqual(edges[0]["source"], r["resource_id"])
        self.assertEqual(edges[0]["inventoryId"], "C-D04")
        self.assertFalse(any(n["class"] == "Paper" for n in graph["nodes"]))
        self.assertEqual(sum(n["class"] == "DatasetResource" for n in graph["nodes"]), 1)

    def test_missing_invalid_and_foreign_resource_doi_add_nothing(self) -> None:
        """Invalid own metadata cannot become an external Paper or dataset stub."""
        baseline, _ = extract_corpus([resource()])
        for value in (None, [], 123, "See 10.1234/a", "https://example.org/10.1234/a", "10.4211/hs." + "b" * 32):
            r = resource()
            r["system_metadata"] = {"doi": value}
            self.assertEqual(extract_corpus([r])[0], baseline)

    def test_doi_identity_is_source_local_and_punctuation_distinct(self) -> None:
        """No slug collision or cross-resource identity resolution is introduced."""
        a, b = resource(), resource()
        a["system_metadata"] = {"doi": "10.1234/a-b"}
        b["resource_id"] = "b" * 32
        b["system_metadata"] = {"doi": "10.1234/a.b"}
        graph, _ = extract_corpus([a, b])
        ids = [n["id"] for n in graph["nodes"] if n["attributes"].get("identifierType") == "DOI"]
        self.assertEqual(len(set(ids)), 2)
        b["system_metadata"] = a["system_metadata"]
        graph, _ = extract_corpus([a, b])
        self.assertEqual(sum(n["attributes"].get("identifierType") == "DOI" for n in graph["nodes"]), 2)

    def test_inventory_alignment_and_edge_identity(self) -> None:
        """Only the two approved branch IDs apply to their original endpoints."""
        graph, _ = extract_corpus([resource()])
        nodes = {n["id"]: n for n in graph["nodes"]}
        for edge in graph["edges"]:
            self.assertEqual(edge["id"], make_edge_id(edge["source"], edge["relation"], edge["target"], edge["inventoryId"]))
            if edge["relation"] == "hasContributor":
                self.assertEqual(edge["inventoryId"], "C-D27")
                self.assertEqual(nodes[edge["source"]]["class"], "DatasetResource")
            if edge["relation"] == "fundedBy":
                expected = "C-D28" if nodes[edge["source"]]["class"] == "Award" else "C-D09 / A-AG-R2"
                self.assertEqual(edge["inventoryId"], expected)

    def test_historical_path_is_protected(self) -> None:
        """Default and explicit output writes cannot silently replace the baseline."""
        self.assertNotEqual(DEFAULT_OUTPUT, HISTORICAL_OUTPUT)
        with self.assertRaisesRegex(ValueError, "Frozen HydroShare"):
            write_output({"nodes": [], "edges": []}, HISTORICAL_OUTPUT)


@unittest.skipUnless(DEFAULT_INPUT.exists() and HISTORICAL_OUTPUT.exists(), "Local HydroShare inputs unavailable")
class ProspectiveCorpusTests(unittest.TestCase):
    """Prove the bounded corpus delta and unchanged cumulative metric policy."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the prospective graph in memory, never overwrite a frozen file."""
        cls.resources = json.loads(DEFAULT_INPUT.read_text())
        cls.old = json.loads(HISTORICAL_OUTPUT.read_text())
        cls.new, _ = extract_corpus(cls.resources)

    def test_all_historical_hashes_unchanged(self) -> None:
        """Protect source graphs, historical cumulative snapshots, OWL and metrics."""
        for name, digest in json.loads(MANIFEST.read_text()).items():
            with self.subTest(path=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)

    def test_only_authorized_corpus_delta(self) -> None:
        """Fifteen DOI nodes/edges are added; 18+21 existing branch IDs change."""
        validate_snapshot(self.new)
        old_nodes = {n["id"]: n for n in self.old["nodes"]}
        new_nodes = {n["id"]: n for n in self.new["nodes"]}
        self.assertEqual({k: new_nodes[k] for k in old_nodes}, old_nodes)
        added = set(new_nodes) - set(old_nodes)
        self.assertEqual(len(added), 15)
        self.assertTrue(all(new_nodes[k]["class"] == "Identifier" for k in added))
        old_edges = { (e["source"], e["relation"], e["target"]): e for e in self.old["edges"] }
        new_edges = { (e["source"], e["relation"], e["target"]): e for e in self.new["edges"] }
        changed = {"C-D27": 0, "C-D28": 0}
        for key, old in old_edges.items():
            actual = new_edges[key]
            expected = copy.deepcopy(old)
            if old["relation"] == "hasContributor":
                expected["inventoryId"] = "C-D27"
            elif old["relation"] == "fundedBy" and old_nodes[old["source"]]["class"] == "Award":
                expected["inventoryId"] = "C-D28"
            if expected["inventoryId"] != old["inventoryId"]:
                changed[expected["inventoryId"]] += 1
                expected["id"] = make_edge_id(old["source"], old["relation"], old["target"], expected["inventoryId"])
            self.assertEqual(actual, expected)
        self.assertEqual(changed, {"C-D27": 18, "C-D28": 21})
        extra = [new_edges[k] for k in set(new_edges) - set(old_edges)]
        self.assertEqual(len(extra), 15)
        self.assertTrue(all(e["relation"] == "hasIdentifier" and e["target"] in added for e in extra))
        metadata = {r["resource_id"]: r.get("system_metadata", {}).get("doi") for r in self.resources}
        for edge in extra:
            self.assertEqual(edge["evidence"]["evidenceText"], metadata[edge["source"]])

    def test_reproducible_cli_and_frozen_input_isolation(self) -> None:
        """Independent processes serialize identical prospective outputs."""
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp) / f"run{i}.json" for i in range(2)]
            for path in paths:
                subprocess.run([sys.executable, "-B", "src/extraction/deterministic/extract_hydroshare.py", "--output", str(path), "--log-level", "ERROR"], cwd=ROOT, check=True)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(json.loads(paths[0].read_text()), self.new)

    def test_cumulative_full_and_filtered_delta(self) -> None:
        """Each cumulative point gains only DOI connectivity; file policy is fixed."""
        history = ROOT / "results/metrics/history/pre_hydroshare_v016/snapshots"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hydroshare_v016.json"
            write_output(self.new, path)
            for record_path in sorted(history.glob("*.json")):
                old = json.loads(record_path.read_text())
                components = old["input"].get("cumulativeProvenance", {}).get("components")
                graph = build_cumulative_snapshot([(c["label"], path if c["label"] == "hydroshare" else ROOT / c["path"]) for c in components]) if components else self.new
                validate_snapshot(graph)
                filtered, audit = partition_file_inventory(graph)
                for name, data in (("full", graph), ("fileInventoryExcluded", filtered)):
                    prior = old["variants"][name]
                    self.assertEqual(len(data["nodes"]), prior["counts"]["nodes"] + 15)
                    self.assertEqual(len(data["edges"]), prior["counts"]["edges"] + 15)
                    metrics = compute_structural_metrics(data)
                    self.assertEqual(metrics["informationDensity"]["totalInformativeAttributes"], prior["metrics"]["informationDensity"]["totalInformativeAttributes"])
                self.assertEqual(len(graph["nodes"]) - len(filtered["nodes"]), audit["excludedNodeCount"])

    def test_prospective_branch_ids_resolve_in_frozen_ontology(self) -> None:
        """The new inventory IDs name the existing merged relations in v0.1.6."""
        ns = {"owl": "http://www.w3.org/2002/07/owl#", "c": "https://w3id.org/ciroh/ontology#"}
        rdf = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
        root = ET.parse(ROOT / "src/ontology/ciroh_ontology.owl").getroot()
        self.assertEqual(root.find("owl:Ontology/owl:versionInfo", ns).text, "0.1.6")
        for inventory_id, name in (("C-D27", "hasContributor"), ("C-D28", "fundedBy"), ("C-D04", "hasIdentifier")):
            matches = [p for p in root.findall("owl:ObjectProperty", ns) if inventory_id in {e.text for e in p.findall("c:inventoryId", ns)}]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].get(rdf + "about"), "#" + name)

    @unittest.skipUnless(DEFAULT_OUTPUT.exists(), "Prospective artifacts not yet generated")
    def test_saved_prospective_snapshots_metrics_and_trajectory(self) -> None:
        """Accepted HydroShare results remain reproducible in the pre-enrichment archive."""
        self.assertEqual(json.loads(DEFAULT_OUTPUT.read_text()), self.new)
        expectation = json.loads((ROOT / "tests/fixtures/hydroshare/prospective_v016_hashes.json").read_text())
        for name, digest in expectation.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        records = []
        for record_path in (ROOT / "results/metrics/history/pre_reference_enrichment_v1/snapshots").glob("*.json"):
            record = json.loads(record_path.read_text())
            input_path = ROOT / record["input"]["path"]
            self.assertTrue(input_path.stem.endswith("_v016"))
            graph = json.loads(input_path.read_text())
            if "components" in graph:
                expected = build_cumulative_snapshot([(c["label"], ROOT / c["path"]) for c in graph["components"]])
                self.assertEqual(graph, expected)
            rebuilt = build_results_record(graph, input_path, record["label"], record["displayName"], record["trajectoryOrder"], "mentionCount", "pre_consolidation")
            self.assertEqual(record, rebuilt)
            records.append(record)
        records.sort(key=lambda r: r["trajectoryOrder"])
        self.assertEqual((ROOT / "results/metrics/history/pre_reference_enrichment_v1/trajectory.md").read_text(), render_trajectory_markdown(records))


if __name__ == "__main__":
    unittest.main()
