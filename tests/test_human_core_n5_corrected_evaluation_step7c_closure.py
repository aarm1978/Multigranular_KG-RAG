"""Focused tests for corrected Human Core N=5 Step 7C closure."""

from __future__ import annotations

import unittest

from src.extraction.llm.publications import human_core_n5_corrected_evaluation_step7c_closure as closure


class Step7CClosureTests(unittest.TestCase):
    """Verify exact closure bindings without changing any bound authority."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the closure in memory after all fail-closed checks."""
        cls.record = closure.build_closure()

    def test_exact_frozen_authorities_are_bound(self) -> None:
        """Closure references the sole corrected realization, strict result, and review."""
        inputs = self.record["frozenInputs"]
        self.assertEqual(inputs["strictStep7B"]["sha256"], closure.STRICT_SHA256)
        self.assertEqual(inputs["completedSecondaryReview"]["sha256"], closure.REVIEWED_SHA256)
        realization = inputs["correctedEvaluationRealization"]
        self.assertEqual(realization["artifactSha256"], "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842")
        self.assertEqual(realization["canonicalPredictions"]["sha256"], closure.review.instrument.STRICT_PREDICTIONS_SHA256)
        self.assertEqual(inputs["matchingContract"]["sha256"], "12ab089ac87cd26a1dbb133d1a381ea5a97d63eb7b54f2cc447d8d81c35efa56")

    def test_closure_status_and_secondary_metrics(self) -> None:
        """Closure keeps strict primary and reviewed metrics secondary without Step 8."""
        self.assertEqual(self.record["status"], "FROZEN_CLOSED")
        self.assertTrue(self.record["step7CExecuted"])
        self.assertFalse(self.record["step8Executed"])
        self.assertEqual(self.record["secondaryMetricSummary"], {
            "humanCoreNodeSemanticRecovery": {"numerator": 64, "denominator": 118},
            "humanCoreRelationSemanticRecovery": {"numerator": 33, "denominator": 61},
            "correctedNodePredictionSourceSupportedRate": {"numerator": 103, "denominator": 109},
            "correctedRelationPredictionSourceSupportedRate": {"numerator": 66, "denominator": 68},
        })

    def test_bound_inputs_remain_unchanged(self) -> None:
        """Closure creation leaves strict, reviewed, and historical artifacts untouched."""
        strict_hash, reviewed_hash = closure._sha256(closure.STRICT), closure._sha256(closure.REVIEWED)
        closure.review.instrument.verify_historical_preservation()
        self.assertEqual(closure.build_closure(), self.record)
        self.assertEqual(closure._sha256(closure.STRICT), strict_hash)
        self.assertEqual(closure._sha256(closure.REVIEWED), reviewed_hash)
        closure.review.instrument.verify_historical_preservation()


if __name__ == "__main__":
    unittest.main()
