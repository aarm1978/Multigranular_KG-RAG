"""Focused tests for deterministic corrected Step 7 researcher-review materialization."""

from __future__ import annotations

import copy
import unittest

from src.extraction.llm.publications import human_core_n5_corrected_evaluation_researcher_review as review


class CorrectedResearcherReviewTests(unittest.TestCase):
    """Ensure exact ledger copying, validation, and secondary metric computation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the reviewed artifact from immutable authorities without writing it."""
        cls.artifact = review.build_reviewed_artifact()

    def test_exact_ledger_source_identity_and_356_item_coverage(self) -> None:
        """Both decision source and source instrument must match their frozen hashes."""
        ledger, source = review._load_authorities()
        self.assertEqual(review._sha256(review.LEDGER), review.LEDGER_SHA256)
        self.assertEqual(review._sha256(review.SOURCE_PACKAGE), review.SOURCE_PACKAGE_SHA256)
        self.assertEqual(len(review._index_source(source)), 356)
        self.assertEqual(len(review._ledger_entries(ledger)), 356)
        self.assertEqual(self.artifact["sourceReviewPackage"]["modified"], False)
        self.assertEqual(self.artifact["researcherJudgmentLedger"]["modified"], False)

    def test_exact_decision_counts_and_metrics(self) -> None:
        """All A/B/C/D counts and frozen rates are deterministically reproduced."""
        correspondence = review.instrument.items(self.artifact, "correspondenceReviewItems")
        support = review.instrument.items(self.artifact, "predictionSourceSupportReviewItems")
        nodes = [item for item in correspondence if item["humanCoreRecord"]["kind"] == "node"]
        relations = [item for item in correspondence if item["humanCoreRecord"]["kind"] == "relation"]
        node_support = [item for item in support if item["predictionRecord"]["kind"] == "node"]
        relation_support = [item for item in support if item["predictionRecord"]["kind"] == "relation"]
        self.assertEqual(len(nodes), 118)
        self.assertEqual(len(node_support), 109)
        self.assertEqual(len(relations), 61)
        self.assertEqual(len(relation_support), 68)
        metrics = self.artifact["secondaryMetrics"]
        self.assertEqual(metrics["humanCoreNodeSemanticRecovery"], {"numerator": 64, "denominator": 118, "value": 64 / 118})
        self.assertEqual(metrics["humanCoreRelationSemanticRecovery"], {"numerator": 33, "denominator": 61, "value": 33 / 61})
        self.assertEqual(metrics["correctedNodePredictionSourceSupportedRate"], {"numerator": 103, "denominator": 109, "value": 103 / 109})
        self.assertEqual(metrics["correctedRelationPredictionSourceSupportedRate"], {"numerator": 66, "denominator": 68, "value": 66 / 68})

    def test_exact_selected_keys_global_one_to_one_and_relation_context(self) -> None:
        """Semantic selections remain exact, eligible, unique, and endpoint-contextualized."""
        review._validate_materialized(self.artifact, review._load_authorities()[0])
        correspondence = review.instrument.items(self.artifact, "correspondenceReviewItems")
        for kind, expected in (("node", 64), ("relation", 33)):
            selected = [item for item in correspondence if item["humanCoreRecord"]["kind"] == kind and item["researcherDisposition"] == "semantic_equivalent"]
            keys = [item["reviewedPredictionRecordKey"] for item in selected]
            self.assertEqual(len(keys), expected)
            self.assertEqual(len(set(keys)), expected)
            for item in selected:
                prediction = self.artifact["predictionRecordsByKey"][item["reviewedPredictionRecordKey"]]
                self.assertTrue(review.prior._same_structural_bucket(item["humanCoreRecord"], prediction))
                if kind == "relation":
                    self.assertEqual(set(item["humanCoreRecord"]["endpointContext"]), {"source", "target"})
                    self.assertEqual(set(prediction["endpointContext"]), {"source", "target"})

    def test_duplicate_selected_prediction_fails_closed(self) -> None:
        """A copied semantic prediction key may not consume two Human Core records."""
        modified = copy.deepcopy(self.artifact)
        selected = [item for item in review.instrument.items(modified, "correspondenceReviewItems") if item["humanCoreRecord"]["kind"] == "node" and item["researcherDisposition"] == "semantic_equivalent"]
        selected[1]["reviewedPredictionRecordKey"] = selected[0]["reviewedPredictionRecordKey"]
        with self.assertRaises(review.prior.ReviewPackageError):
            review._validate_materialized(modified, review._load_authorities()[0])

    def test_source_and_historical_artifacts_are_preserved(self) -> None:
        """Materialization reads but never rewrites its source or historical C1 artifacts."""
        before_source = review._sha256(review.SOURCE_PACKAGE)
        review.instrument.verify_historical_preservation()
        rebuilt = review.build_reviewed_artifact()
        self.assertEqual(before_source, review._sha256(review.SOURCE_PACKAGE))
        self.assertEqual(rebuilt["secondaryMetrics"], self.artifact["secondaryMetrics"])
        review.instrument.verify_historical_preservation()


if __name__ == "__main__":
    unittest.main()
