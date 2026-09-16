"""Regression checks for the completed immutable Human Core supplemental export."""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_supplemental_annotation_preservation_v0.1.5.json"


class HumanCoreSupplementalPreservationTests(unittest.TestCase):
    """Protect the completed supplemental delta and its distinct primary baseline."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the versioned record and immutable local export without writing either."""

        cls.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
        cls.export_path = ROOT / cls.record["supplementalDeterministicSessionExport"]["path"]
        cls.export = json.loads(cls.export_path.read_text(encoding="utf-8"))

    def test_supplemental_export_hash_and_completion_are_exact(self) -> None:
        """The local supplemental export is byte-bound and all five records are submitted."""

        expected = self.record["supplementalDeterministicSessionExport"]["sha256"]
        self.assertEqual(hashlib.sha256(self.export_path.read_bytes()).hexdigest(), expected)
        self.assertEqual(self.export["annotationSessionID"], "HUMAN_CORE_N5_SUPPLEMENTAL_V015")
        self.assertEqual(len(self.export["annotations"]), 5)
        self.assertEqual({row["status"] for row in self.export["annotations"]}, {"submitted"})
        self.assertTrue(self.record["completion"]["allFiveAnnotationsSubmitted"])

    def test_supplemental_node_and_relation_counts_are_exact(self) -> None:
        """The preservation record matches the completed bounded delta exactly."""

        nodes: Counter[str] = Counter()
        relations: Counter[str] = Counter()
        for row in self.export["annotations"]:
            nodes.update(node["className"] for node in row["annotation"]["nodes"])
            relations.update(edge["operationalRelationID"] for edge in row["annotation"]["relations"])
        self.assertEqual(nodes, Counter({"Organization": 15, "AgentBasedModel": 1}))
        expected = self.record["completion"]["relationCounts"]
        self.assertEqual(sum(relations.values()), expected["total"])
        for target_id, count in expected.items():
            if target_id != "total":
                self.assertEqual(relations[target_id], count)

    def test_primary_export_hash_remains_distinct_and_preserved(self) -> None:
        """The v0.1.4 primary export remains byte-exact and is never merged into this export."""

        primary = self.record["immutablePrimaryBaseline"]
        primary_path = ROOT / primary["exportPath"]
        self.assertEqual(hashlib.sha256(primary_path.read_bytes()).hexdigest(), primary["exportSha256"])
        self.assertNotEqual(primary_path, self.export_path)
        self.assertTrue(self.record["referenceComposition"]["primaryAndSupplementalExportsRemainDistinct"])
        self.assertFalse(self.record["referenceComposition"]["destructiveMergeAuthorized"])
