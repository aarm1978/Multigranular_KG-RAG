"""Regression tests for the corrected pre-review instrument, without semantic judgments."""

import copy
import json
import unittest

from src.extraction.llm.publications import human_core_n5_semantic_equivalence_review_v011 as review


class CorrectedReviewTests(unittest.TestCase):
    """Exercise selection validation, neutral populations and immutable authorities."""

    @classmethod
    def setUpClass(cls) -> None:
        """Generate one read-only fixture from the frozen authorities."""
        cls.package = review.build_package()

    def test_determinism_and_byte_preservation(self) -> None:
        """Both generations preserve every strict and unused v0.1.0 artifact."""
        review.verify_preservation()
        self.assertEqual(json.dumps(self.package, sort_keys=True), json.dumps(review.build_package(), sort_keys=True))
        review.verify_preservation()

    def test_every_prediction_has_exactly_one_support_item(self) -> None:
        """All 102 nodes and 59 relations, including 35 strict TPs, are independent items."""
        support = review.items(self.package, 'predictionSourceSupportReviewItems')
        keys = [item['c1Record']['key'] for item in support]
        self.assertEqual(len(keys), 161)
        self.assertEqual(len(set(keys)), 161)
        self.assertEqual(set(keys), set(self.package['predictionRecordsByKey']))
        self.assertEqual(sum(item['c1Record']['kind'] == 'node' for item in support), 102)
        self.assertEqual(sum(item['c1Record']['kind'] == 'relation' for item in support), 59)
        self.assertEqual(sum(item['strictMatchStatus'] == 'strict_true_positive' for item in support), 35)

    def test_all_researcher_fields_and_metrics_are_unset(self) -> None:
        """Strict TPs do not prepopulate selection, disposition or source support."""
        correspondence = review.items(self.package, 'correspondenceReviewItems')
        self.assertEqual(len(correspondence), 179)
        for item in correspondence:
            for field in ('reviewedC1RecordKey', 'researcherDisposition', 'researcherNote', 'optionalExplanatoryCode'):
                self.assertIsNone(item[field])
        for item in review.items(self.package, 'predictionSourceSupportReviewItems'):
            for field in ('predictionSourceSupportJudgment', 'researcherNote', 'optionalExplanatoryCode'):
                self.assertIsNone(item[field])
        metrics = self.package['secondaryMetricDefinitions']
        self.assertIsNone(metrics['humanCoreSemanticRecovery']['values'])
        self.assertIsNone(metrics['c1SourceSupportedPredictionRate']['values'])
        self.assertIsNone(metrics['c1SourceSupportedPredictionRate']['unsupportedCounts'])
        self.assertIsNone(metrics['c1SourceSupportedPredictionRate']['insufficientCounts'])

    def test_selected_keys_resolve_and_are_eligible(self) -> None:
        """Synthetic selections exercise validation only, not actual researcher decisions."""
        package = copy.deepcopy(self.package)
        item = next(item for item in review.items(package, 'correspondenceReviewItems') if item['plausibleSameTargetClassCandidates'])
        item['researcherDisposition'] = 'semantic_equivalent'
        for invalid in (None, 'missing-key'):
            item['reviewedC1RecordKey'] = invalid
            with self.assertRaises(review.prior.ReviewPackageError):
                review.validate_selections(package)
        item['reviewedC1RecordKey'] = item['plausibleSameTargetClassCandidates'][0]['key']
        review.validate_selections(package)
        other = next(record for record in package['predictionRecordsByKey'].values()
                     if record['sourceUnitID'] == item['humanCoreRecord']['sourceUnitID']
                     and not review.prior._same_structural_bucket(item['humanCoreRecord'], record))
        item['reviewedC1RecordKey'] = other['key']
        with self.assertRaises(review.prior.ReviewPackageError):
            review.validate_selections(package)
        item['researcherDisposition'] = 'target_or_class_disagreement'
        review.validate_selections(package)
        item['reviewedC1RecordKey'] = next(key for key, record in package['predictionRecordsByKey'].items()
                                         if record['sourceUnitID'] != item['humanCoreRecord']['sourceUnitID'])
        with self.assertRaises(review.prior.ReviewPackageError):
            review.validate_selections(package)

    def test_global_one_to_one_rejects_competing_keys(self) -> None:
        """Fully qualified identities detect competition across review items."""
        package = copy.deepcopy(self.package)
        owners = {}
        for item in review.items(package, 'correspondenceReviewItems'):
            for candidate in item['plausibleSameTargetClassCandidates']:
                key = candidate['key']
                if key in owners:
                    for selected in (owners[key], item):
                        selected['researcherDisposition'] = 'semantic_equivalent'
                        selected['reviewedC1RecordKey'] = key
                    with self.assertRaises(review.prior.ReviewPackageError):
                        review.validate_selections(package)
                    return
                owners[key] = item
        self.fail('fixture must contain competing structural candidates')

    def test_relation_endpoint_context_including_baseline_aliases(self) -> None:
        """Both endpoints expose exact identities and all resolvable node context."""
        views = [item['humanCoreRecord'] for item in review.items(self.package, 'correspondenceReviewItems')]
        views += list(self.package['predictionRecordsByKey'].values())
        aliases = 0
        for view in views:
            if view['kind'] != 'relation':
                continue
            self.assertEqual(set(view['endpointContext']), {'source', 'target'})
            for context in view['endpointContext'].values():
                self.assertTrue(context['stableEndpointIdentity'])
                if context['stableEndpointIdentity'][0] == 'node':
                    record = context['record']
                    self.assertEqual(record['key'], context['stableEndpointIdentity'][1])
                    for field in ('label', 'operationalTargetID', 'ontologyClassID', 'evidence'):
                        self.assertTrue(record[field])
                if context['authoredEndpoint']['referenceID'].startswith('baseline:'):
                    aliases += 1
                    self.assertEqual(context['record']['partition'], 'primaryV014')
        self.assertGreater(aliases, 0)


if __name__ == '__main__':
    unittest.main()
