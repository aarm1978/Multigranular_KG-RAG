"""Focused tests for the frozen Pilot 1 execution-scope projection."""

from __future__ import annotations

import json
import unittest

from src.extraction.llm.publications import pilot1_evaluation_execution_subset as subset


class Pilot1EvaluationExecutionSubsetTests(unittest.TestCase):
    """Verify the subset is an exact, offline manifest projection."""

    @classmethod
    def setUpClass(cls) -> None:
        """Derive the subset once; the implementation has no request builder or dispatch."""

        cls.artifact = subset.derive_execution_subset()
        cls.manifest = json.loads(subset.MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_scope_is_the_exact_frozen_n5_plus_n6_union(self) -> None:
        """The five and six frozen source IDs form eleven unique execution requests."""

        authorities = self.artifact["selectionAuthorities"]
        expected = authorities["humanCoreN5"]["sourceUnitIDs"] + authorities["step5N6"]["sourceUnitIDs"]
        self.assertEqual(self.artifact["subsetRequestCount"], 11)
        self.assertEqual([row["primarySourceUnitID"] for row in self.artifact["requests"]], expected)
        self.assertEqual(len(set(expected)), 11)
        self.assertEqual([row["executionCohort"] for row in self.artifact["requests"]], ["human_core_n5"] * 5 + ["step5_n6"] * 6)

    def test_every_record_is_an_exact_corrected_manifest_identity_projection(self) -> None:
        """Request IDs, hashes, targets, and context are copied exactly from the manifest."""

        manifest_by_unit = {row["primarySourceUnitID"]: row for row in self.manifest["requests"]}
        for record in self.artifact["requests"]:
            source = manifest_by_unit[record["primarySourceUnitID"]]
            for field in subset.IDENTITY_FIELDS:
                self.assertEqual(record[field], source[field])
        self.assertEqual(
            self.artifact["correctedProductionManifest"]["manifestSha256"], self.manifest["manifestSha256"]
        )

    def test_artifact_is_self_hashed_and_no_provider_execution_occurs(self) -> None:
        """The scope freeze is internally verifiable and explicitly offline."""

        self.assertEqual(self.artifact["artifactSha256"], subset._self_hash(self.artifact, "artifactSha256"))
        self.assertEqual(self.artifact["providerModelCalls"], 0)
        self.assertEqual(self.manifest["providerModelCalls"], 0)
        self.assertFalse(self.manifest["c1Execution"])
        self.assertEqual(self.artifact["remainingCorrectedProductionRequestsNotRequiredForCurrentEvaluation"], 251)


if __name__ == "__main__":
    unittest.main()
