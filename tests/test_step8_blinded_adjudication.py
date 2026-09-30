"""Focused deterministic Step 8B blinding and binding tests."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications import step8_blinded_adjudication as step8b


class Step8BlindedAdjudicationTests(unittest.TestCase):
    """Verify reviewer whitelists and exact frozen subset derivation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build one deterministic in-memory projection for focused checks."""

        cls.artifacts = step8b.build()

    def test_exact_counts_membership_and_shared_ids(self) -> None:
        """Second review is exactly the frozen subset of the primary package."""

        primary = self.artifacts["primary"]
        secondary = self.artifacts["secondary"]
        subset = json.loads(step8b.SUBSET.read_text(encoding="utf-8"))
        self.assertEqual(len(primary["judgmentItems"]), 182)
        self.assertEqual(len(secondary["judgmentItems"]), 45)
        self.assertEqual(set(secondary["primarySourceUnitIDs"]), set(subset["selectedPrimarySourceUnitIDs"]))
        selected = [item for item in primary["judgmentItems"] if item["primarySourceUnitID"] in subset["selectedPrimarySourceUnitIDs"]]
        self.assertEqual(secondary["judgmentItems"], selected)
        self.assertEqual(len(primary["duplicateReviewGroups"]), 0)

    def test_opaque_ids_are_stable_unique_and_do_not_encode_system_identity(self) -> None:
        """Neutral item IDs remain identical across builds and reviewer packages."""

        first = [item["judgmentItemID"] for item in self.artifacts["primary"]["judgmentItems"]]
        second = [item["judgmentItemID"] for item in step8b.build()["primary"]["judgmentItems"]]
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(set(first)))
        self.assertEqual(first, [f"judgment-item-{number:04d}" for number in range(1, len(first) + 1)])

    def test_review_whitelist_and_recursive_leakage(self) -> None:
        """Only source and semantic fields cross into either reviewer package."""

        forbidden = {"candidateID", "candidateKey", "requestID", "runID", "outputID", "provider", "modelName", "modelVersion", "validationLineage", "candidateValidationStatus", "supersededByRecordID", "normalizationStatus", "contributingCandidateKey", "evidenceSpanID", "selectedAttemptNumber", "providerRawSha256", "pooledItemID", "productionAcceptanceStatus"}

        def inspect(value: object) -> None:
            """Reject hidden keys at any nesting depth."""

            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        for package in (self.artifacts["primary"], self.artifacts["secondary"]):
            inspect(package)
            for item in package["judgmentItems"]:
                self.assertEqual(set(item), step8b.ITEM_FIELDS)
                self.assertTrue(all(set(evidence) == step8b.EVIDENCE_FIELDS for evidence in item["evidenceOccurrences"]))

    def test_source_and_context_bounds(self) -> None:
        """Context evidence stays under its primary item and creates no new unit."""

        package = self.artifacts["primary"]
        primary_units = set(package["primarySourceUnitIDs"])
        self.assertEqual(len(primary_units), 6)
        context_units = set()
        for item in package["judgmentItems"]:
            context_units.update(item["authorizedContextSourceUnitIDs"])
            for evidence in item["evidenceOccurrences"]:
                self.assertIn(evidence["sourceUnitID"], {item["primarySourceUnitID"], *item["authorizedContextSourceUnitIDs"]})
        self.assertTrue(context_units.isdisjoint(primary_units))
        self.assertNotIn("pub:46:sec:0006:unit:0002", primary_units)

    def test_private_mapping_reconstructs_step8a_lineage(self) -> None:
        """Every opaque ID maps to exactly one preserved internal pooled item."""

        pool = json.loads(step8b.POOL.read_text(encoding="utf-8"))
        by_id = {item["pooledItemID"]: item for item in pool["retainedPooledItems"]}
        mapping = self.artifacts["mapping"]
        self.assertEqual(mapping["accessScope"], "internal_only")
        self.assertEqual(mapping["bindings"]["step8APoolArtifactSha256"], pool["artifactSha256"])
        self.assertEqual(len(mapping["items"]), len(by_id))
        for row in mapping["items"]:
            original = by_id[row["step8APooledItemID"]]
            self.assertEqual(row["memberCandidateKeys"], original["memberCandidateKeys"])
            self.assertEqual(row["c1Provenance"], original["c1Provenance"])

    def test_duplicate_group_projection_is_neutral(self) -> None:
        """Synthetic groups expose only opaque IDs and a neutral instruction."""

        group = {"duplicateReviewGroupID": "private-group", "sourceArtifactID": "paper", "memberCandidateKeys": ["r|candidate_node|a", "r|candidate_node|b"]}
        opaque = {"r|candidate_node|a": "judgment-item-0001", "r|candidate_node|b": "judgment-item-0002"}
        candidates = {key: {"sourceArtifactID": "paper", "primarySourceUnitID": "unit"} for key in opaque}
        projected, group_ids = step8b._project_groups([group], opaque, candidates)
        visible = projected[0]
        self.assertEqual(group_ids["private-group"], "duplicate-group-0001")
        self.assertEqual(set(visible), {"duplicateReviewGroupID", "judgmentItemIDs", "instruction"})
        self.assertNotIn("private-group", json.dumps(visible))
        self.assertNotIn("POSSIBLE_LOCAL_DUPLICATE", json.dumps(visible))
        changed = copy.deepcopy(candidates)
        changed["r|candidate_node|b"]["sourceArtifactID"] = "other-paper"
        with self.assertRaisesRegex(step8b.Step8BlindingError, "DUPLICATE_GROUP_SOURCE_SCOPE_DRIFT"):
            step8b._project_groups([group], opaque, changed)

    def test_fails_closed_on_binding_and_evidence_drift(self) -> None:
        """Altered frozen bytes or evidence outside the envelope halt projection."""

        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "pool.json"
            changed.write_bytes(step8b.POOL.read_bytes() + b" ")
            with self.assertRaisesRegex(step8b.Step8BlindingError, "FROZEN_BINDING_DRIFT"):
                step8b.build(pool_path=changed)
        source = json.loads(step8b.POOL.read_text(encoding="utf-8"))["retainedPooledItems"][0]
        altered = copy.deepcopy(source)
        altered["evidenceOccurrences"][0]["sourceUnitID"] = "outside"
        with self.assertRaisesRegex(step8b.Step8BlindingError, "EVIDENCE_OUTSIDE_AUTHORIZED_SCOPE"):
            step8b._project_item(altered, "judgment-item-0001", [], {}, {}, {source["primarySourceUnitID"]})


if __name__ == "__main__":
    unittest.main()
