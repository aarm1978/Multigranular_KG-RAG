"""Focused safeguards for the approved Publication development-only manifest."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURATION_ROOT = PROJECT_ROOT / "data/curation/papers"
DEVELOPMENT_MANIFEST = CURATION_ROOT / "publication_llm_development_only_manifest.json"
SOURCE_UNIT_INVENTORY = CURATION_ROOT / "publication_llm_development_only_source_unit_inventory.jsonl"
MATERIALIZATION_MANIFEST = CURATION_ROOT / "publication_llm_development_only_materialization_manifest.json"
PILOT1_ARTIFACT_IDS = {
    "10", "15", "16", "18", "34", "37", "46", "54", "79", "276", "87",
    "87-corrigendum",
}
DEVELOPMENT_POOL_IDS = {"5", "17", "36", "50", "58", "59", "100", "219", "220", "240", "243", "270"}
SELECTED_PUBLICATION_IDS = {"17", "36", "219", "243", "270"}


class PublicationDevelopmentOnlyManifestTests(unittest.TestCase):
    """Prove the approved units are valid and outside Publication Pilot 1."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the approved manifest and its development-only source inventory."""

        cls.manifest = json.loads(DEVELOPMENT_MANIFEST.read_text(encoding="utf-8"))
        cls.materialization_manifest = json.loads(
            MATERIALIZATION_MANIFEST.read_text(encoding="utf-8")
        )
        cls.inventory = [
            json.loads(line)
            for line in SOURCE_UNIT_INVENTORY.read_text(encoding="utf-8").splitlines()
        ]
        cls.inventory_by_id = {row["sourceUnitID"]: row for row in cls.inventory}

    def test_materialization_pool_is_exact_and_pilot1_disjoint(self) -> None:
        """The twelve-artifact materialization pool is exact and outside Pilot 1."""

        materialized_ids = {row["paperID"] for row in self.inventory}
        self.assertEqual(materialized_ids, DEVELOPMENT_POOL_IDS)
        self.assertTrue(materialized_ids.isdisjoint(PILOT1_ARTIFACT_IDS))
        self.assertTrue(
            all(
                row["validationResults"] == {"valid": True, "errorCodes": []}
                for row in self.inventory
            )
        )
        self.assertEqual(
            hashlib.sha256(SOURCE_UNIT_INVENTORY.read_bytes()).hexdigest(),
            self.materialization_manifest["sourceUnitInventoryHash"],
        )

    def test_manifest_cardinality_ownership_and_disjointness(self) -> None:
        """The approved set has ten unique bound units, two per intended publication."""

        units = self.manifest["units"]
        source_unit_ids = [row["sourceUnitID"] for row in units]
        publication_counts = Counter(row["sourcePublicationID"] for row in units)

        self.assertEqual(self.manifest["status"], "approved_for_development")
        self.assertTrue(self.manifest["pilot1ArtifactDisjoint"])
        self.assertEqual(set(self.manifest["pilot1ArtifactIds"]), PILOT1_ARTIFACT_IDS)
        self.assertEqual(len(units), 10)
        self.assertEqual(
            [row["developmentId"] for row in units],
            [f"DEV-{index:02d}" for index in range(1, 11)],
        )
        self.assertEqual(len(set(source_unit_ids)), 10)
        self.assertEqual(publication_counts, Counter({paper_id: 2 for paper_id in SELECTED_PUBLICATION_IDS}))
        self.assertTrue(set(publication_counts).isdisjoint(PILOT1_ARTIFACT_IDS))

        for proposed in units:
            with self.subTest(sourceUnitID=proposed["sourceUnitID"]):
                source = self.inventory_by_id[proposed["sourceUnitID"]]
                self.assertEqual(proposed["sourcePublicationID"], source["paperID"])
                self.assertEqual(source["validationResults"], {"valid": True, "errorCodes": []})


if __name__ == "__main__":
    unittest.main()
