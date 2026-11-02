"""Focused tests for the neutral Human Core N=5 sensitivity review package."""

from __future__ import annotations

import json
import unittest

from src.extraction.llm.publications.human_core_n5_semantic_equivalence_review import (
    STRICT_JSON,
    STRICT_JSON_SHA256,
    STRICT_REPORT,
    STRICT_REPORT_SHA256,
    _sha256,
    _same_structural_bucket,
    build_package,
)


class HumanCoreN5SemanticEquivalenceReviewTests(unittest.TestCase):
    """Verify deterministic neutral package construction without reviewer judgments."""

    def test_strict_v011_is_preserved_before_and_after_package_build(self) -> None:
        """The secondary package is read-only with respect to strict evaluation bytes."""
        self.assertEqual(_sha256(STRICT_JSON), STRICT_JSON_SHA256)
        self.assertEqual(_sha256(STRICT_REPORT), STRICT_REPORT_SHA256)
        build_package()
        self.assertEqual(_sha256(STRICT_JSON), STRICT_JSON_SHA256)
        self.assertEqual(_sha256(STRICT_REPORT), STRICT_REPORT_SHA256)

    def test_package_is_deterministic_and_neutral(self) -> None:
        """Stable source inputs produce stable, disposition-free review material."""
        first = build_package()
        second = build_package()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["status"], "RESEARCHER_REVIEW_PENDING")
        self.assertEqual(first["counts"], {
            "sourceUnitCount": 5,
            "strictTruePositivePairs": 35,
            "unmatchedHumanCoreRecords": 144,
            "c1OnlyAssertions": 126,
            "correspondenceReviewItems": 179,
            "reviewItems": 305,
            "candidateGroups": 305,
        })
        self.assertEqual(first["providerModelCalls"], 0)
        self.assertFalse(first["step7CExecuted"])
        self.assertFalse(first["freezeOrClosureRecordCreated"])
        for unit in first["reviewGroupsByUnitAndOperationalTarget"]:
            for target in unit["targets"]:
                for item in target["correspondenceReviewItems"]:
                    self.assertIsNone(item["researcherDisposition"])
                    self.assertIsNone(item["optionalExplanatoryCode"])
                    self.assertIsNone(item["researcherNote"])
                for item in target["c1OnlySourceSupportReviewItems"]:
                    self.assertIsNone(item["predictionSourceSupportJudgment"])
                    self.assertIsNone(item["optionalExplanatoryCode"])
                    self.assertIsNone(item["researcherNote"])

    def test_structural_candidates_do_not_allow_target_or_class_substitution(self) -> None:
        """Candidate grouping is a neutral same-scope/type filter, never a rescue rule."""
        node = {
            "kind": "node", "sourceUnitID": "unit", "operationalTargetID": "target",
            "ontologyClassID": "class",
        }
        self.assertTrue(_same_structural_bucket(node, dict(node)))
        self.assertFalse(_same_structural_bucket(node, {**node, "operationalTargetID": "other-target"}))
        self.assertFalse(_same_structural_bucket(node, {**node, "ontologyClassID": "other-class"}))
        relation = {
            "kind": "relation", "sourceUnitID": "unit", "operationalTargetID": "relation-target",
            "ontologyRelationID": "relation-type",
        }
        self.assertTrue(_same_structural_bucket(relation, dict(relation)))
        self.assertFalse(_same_structural_bucket(relation, {**relation, "ontologyRelationID": "other-type"}))


if __name__ == "__main__":
    unittest.main()
