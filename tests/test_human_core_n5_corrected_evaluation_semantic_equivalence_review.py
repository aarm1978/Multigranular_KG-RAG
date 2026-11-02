"""Focused tests for the corrected-evaluation secondary review instrument."""

from __future__ import annotations

import copy
import json
import unittest

from src.extraction.llm.publications import human_core_n5_corrected_evaluation_semantic_equivalence_review as review


class CorrectedEvaluationReviewTests(unittest.TestCase):
    """Verify fixed populations, null judgments, and historical preservation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build a deterministic, in-memory reviewer packet."""
        cls.package = review.build_package()

    def test_exact_corrected_population_and_authority_binding(self) -> None:
        """Only the corrected N=5 strict result and prediction source are admitted."""
        counts = self.package["counts"]
        self.assertEqual(counts["humanCoreByKind"], {"node": 118, "relation": 61})
        self.assertEqual(counts["predictionsByKind"], {"node": 109, "relation": 68})
        self.assertEqual(counts["correspondenceReviewItems"], 179)
        self.assertEqual(counts["predictionSourceSupportReviewItems"], 177)
        self.assertEqual(counts["reviewItems"], 356)
        self.assertEqual(self.package["correctedStrictEvaluation"]["sha256"], review.STRICT_JSON_SHA256)
        self.assertEqual(self.package["correctedPredictionAuthority"], {
            "sha256": review.STRICT_PREDICTIONS_SHA256,
            "cohort": "human_core_n5",
            "excludedCohort": "step5_n6",
        })
        self.assertEqual(self.package["endpointContextAuthorities"]["predictionAuthority"], "corrected_pilot1_evaluation")

    def test_all_researcher_fields_and_metrics_are_null(self) -> None:
        """Strict context cannot prepopulate a semantic or source-support judgment."""
        for item in review.items(self.package, "correspondenceReviewItems"):
            for field in ("reviewedPredictionRecordKey", "researcherDisposition", "optionalExplanatoryCode", "researcherNote"):
                self.assertIsNone(item[field])
        for item in review.items(self.package, "predictionSourceSupportReviewItems"):
            for field in ("predictionSourceSupportJudgment", "optionalExplanatoryCode", "researcherNote"):
                self.assertIsNone(item[field])
        metrics = self.package["secondaryMetricDefinitions"]
        self.assertIsNone(metrics["humanCoreSemanticRecovery"]["values"])
        prediction_metric = metrics["correctedPredictionSourceSupportedRate"]
        self.assertIsNone(prediction_metric["values"])
        self.assertIsNone(prediction_metric["unsupportedCounts"])
        self.assertIsNone(prediction_metric["insufficientCounts"])

    def test_prediction_support_items_are_independent_and_complete(self) -> None:
        """Every corrected prediction, including strict TPs, has one support item."""
        support = review.items(self.package, "predictionSourceSupportReviewItems")
        keys = [item["predictionRecord"]["key"] for item in support]
        self.assertEqual(len(keys), 177)
        self.assertEqual(len(set(keys)), 177)
        self.assertEqual(set(keys), set(self.package["predictionRecordsByKey"]))
        self.assertEqual(sum(item["predictionRecord"]["kind"] == "node" for item in support), 109)
        self.assertEqual(sum(item["predictionRecord"]["kind"] == "relation" for item in support), 68)
        self.assertEqual(sum(item["strictMatchStatus"] == "strict_true_positive" for item in support), 36)

    def test_selection_validation_enforces_structure_and_global_one_to_one(self) -> None:
        """Synthetic keys exercise validation without recording any researcher judgment."""
        package = copy.deepcopy(self.package)
        items = review.items(package, "correspondenceReviewItems")
        item = next(row for row in items if row["plausibleSameTargetClassCandidates"])
        item["researcherDisposition"] = "semantic_equivalent"
        item["reviewedPredictionRecordKey"] = item["plausibleSameTargetClassCandidates"][0]["key"]
        review.validate_selections(package)
        other = next(record for record in package["predictionRecordsByKey"].values()
                     if record["sourceUnitID"] == item["humanCoreRecord"]["sourceUnitID"]
                     and not review.prior._same_structural_bucket(item["humanCoreRecord"], record))
        item["reviewedPredictionRecordKey"] = other["key"]
        with self.assertRaises(review.prior.ReviewPackageError):
            review.validate_selections(package)
        item["researcherDisposition"] = "target_or_class_disagreement"
        review.validate_selections(package)
        candidates: dict[str, dict] = {}
        for row in review.items(self.package, "correspondenceReviewItems"):
            for candidate in row["plausibleSameTargetClassCandidates"]:
                if candidate["key"] in candidates:
                    duplicate = copy.deepcopy(self.package)
                    first, second = candidates[candidate["key"]], row
                    duplicate_items = {entry["reviewItemID"]: entry for entry in review.items(duplicate, "correspondenceReviewItems")}
                    for original in (first, second):
                        selected = duplicate_items[original["reviewItemID"]]
                        selected["researcherDisposition"] = "semantic_equivalent"
                        selected["reviewedPredictionRecordKey"] = candidate["key"]
                    with self.assertRaises(review.prior.ReviewPackageError):
                        review.validate_selections(duplicate)
                    return
                candidates[candidate["key"]] = row
        self.fail("corrected fixture must contain competing structural candidates")

    def test_relation_endpoint_context_and_historical_bytes_are_preserved(self) -> None:
        """Endpoint context is exact, while all C1 history stays byte-identical."""
        review.verify_historical_preservation()
        for view in ([item["humanCoreRecord"] for item in review.items(self.package, "correspondenceReviewItems")]
                     + list(self.package["predictionRecordsByKey"].values())):
            if view["kind"] != "relation":
                continue
            self.assertEqual(set(view["endpointContext"]), {"source", "target"})
            for context in view["endpointContext"].values():
                self.assertTrue(context["stableEndpointIdentity"])
                if context["stableEndpointIdentity"][0] == "node":
                    self.assertEqual(context["record"]["key"], context["stableEndpointIdentity"][1])
        self.assertEqual(json.dumps(self.package, sort_keys=True), json.dumps(review.build_package(), sort_keys=True))
        review.verify_historical_preservation()


if __name__ == "__main__":
    unittest.main()
