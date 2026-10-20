"""Focused offline checks of neutral GPT-6.1 review-instrument adaptation."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import inspect
import socket
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import human_core_n5_gpt61_secondary_review as review


class GPT61SecondaryReviewTests(unittest.TestCase):
    """Protect frozen review semantics while supplying the new prediction population."""

    @classmethod
    def setUpClass(cls) -> None:
        """Reproduce the instrument with network, scoring and semantic review disabled."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')), \
             patch.object(review.evaluation.scorer, 'compute', side_effect=AssertionError('NO_NEW_SCORING')), \
             patch.object(review.evaluation, 'evaluate', side_effect=AssertionError('NO_NEW_EVALUATION')):
            cls.package = review.run(verify=True)

    def test_original_builder_and_validator_reused(self) -> None:
        """Only the explicitly authorized prediction-count guard changes in builder code."""
        original = inspect.getsource(review.original.build_package)
        specialized = review.adapted_builder_source()
        self.assertEqual(specialized.replace(review.NEW_GUARD, review.OLD_GUARD, 1), original)
        self.assertIs(review.validate_selections, review.original.validate_selections)
        self.assertEqual(self.package['protocol']['explanatoryCodeDefinitions'], review.original.CODES)
        self.assertEqual(self.package['protocol']['sha256'], review.PROTOCOL_SHA)

    def test_exact_pass_counts_and_authority_bindings(self) -> None:
        """Passes bind exactly the published GPT-6.1 scoring population, not all accepted output."""
        self.assertEqual(self.package['reviewPassCounts'], {'A': 118, 'B': 127, 'C': 61, 'D': 67})
        self.assertEqual(self.package['counts']['reviewItems'], 373)
        self.assertEqual(self.package['counts']['sourceUnitCount'], 5)
        self.assertEqual(self.package['modelSpecificStrictEvaluation']['sha256'], review.STRICT_SHA)
        self.assertEqual(self.package['modelSpecificPredictionAuthority']['sha256'], review.PREDICTIONS_SHA)
        self.assertEqual(self.package['endpointContextAuthorities']['predictionAuthority'], review.evaluation.REALIZATION)

    def test_all_review_fields_and_secondary_values_null(self) -> None:
        """Strict context and candidate buckets must not become reviewer judgments."""
        review.assert_neutral(self.package)
        for field, judgment_fields in [
            ('correspondenceReviewItems', ('researcherDisposition', 'reviewedPredictionRecordKey', 'optionalExplanatoryCode', 'researcherNote')),
            ('predictionSourceSupportReviewItems', ('predictionSourceSupportJudgment', 'optionalExplanatoryCode', 'researcherNote')),
        ]:
            for item in review.items(self.package, field):
                self.assertTrue(all(item[name] is None for name in judgment_fields))
        metrics = self.package['secondaryMetricDefinitions']
        self.assertIsNone(metrics['humanCoreSemanticRecovery']['values'])
        for field in ('values', 'unsupportedCounts', 'insufficientCounts'):
            self.assertIsNone(metrics['predictionSourceSupportedRate'][field])
        self.assertFalse(self.package['semanticJudgmentsPerformed'])
        self.assertFalse(self.package['historicalResearcherJudgmentsUsed'])

    def test_support_and_strict_true_positive_population_complete(self) -> None:
        """All 194 predictions have independent support items, including all 39 strict TPs."""
        support = review.items(self.package, 'predictionSourceSupportReviewItems')
        keys = [item['predictionRecord']['key'] for item in support]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), set(self.package['predictionRecordsByKey']))
        self.assertTrue(all(review.evaluation.REALIZATION in key for key in keys))
        for field, record_field in [('correspondenceReviewItems', 'humanCoreRecord'),
                                    ('predictionSourceSupportReviewItems', 'predictionRecord')]:
            counts = Counter(item[record_field]['kind'] for item in review.items(self.package, field)
                             if item['strictMatchStatus'] == 'strict_true_positive')
            self.assertEqual(counts, {'node': 32, 'relation': 7})

    def test_buckets_and_endpoint_context_exact(self) -> None:
        """Buckets remain purely structural and relation endpoints retain exact context."""
        predictions = self.package['predictionRecordsByKey']
        for item in review.items(self.package, 'correspondenceReviewItems'):
            reference = item['humanCoreRecord']
            expected = {key for key, prediction in predictions.items()
                        if review.original.prior._same_structural_bucket(reference, prediction)}
            self.assertEqual({p['key'] for p in item['plausibleSameTargetClassCandidates']}, expected)
        records = [item['humanCoreRecord'] for item in review.items(self.package, 'correspondenceReviewItems')]
        records += list(predictions.values())
        for record in records:
            if record['kind'] == 'relation':
                self.assertEqual(set(record['endpointContext']), {'source', 'target'})
                for role, context in record['endpointContext'].items():
                    self.assertEqual(context['authoredEndpoint'], record[role])
                    if context['stableEndpointIdentity'][0] == 'node':
                        self.assertEqual(context['record']['key'], context['stableEndpointIdentity'][1])

    def test_original_global_selection_rules(self) -> None:
        """Synthetic mutations only: reject missing, ineligible and competing selections."""
        package = deepcopy(self.package)
        rows = review.items(package, 'correspondenceReviewItems')
        row = next(x for x in rows if x['plausibleSameTargetClassCandidates'])
        row['researcherDisposition'] = 'semantic_equivalent'
        with self.assertRaises(review.original.prior.ReviewPackageError):
            review.validate_selections(package)
        row['reviewedPredictionRecordKey'] = row['plausibleSameTargetClassCandidates'][0]['key']
        review.validate_selections(package)
        other = next(p for p in package['predictionRecordsByKey'].values()
                     if p['sourceUnitID'] == row['humanCoreRecord']['sourceUnitID']
                     and not review.original.prior._same_structural_bucket(row['humanCoreRecord'], p))
        row['reviewedPredictionRecordKey'] = other['key']
        with self.assertRaises(review.original.prior.ReviewPackageError):
            review.validate_selections(package)
        row['researcherDisposition'] = 'target_or_class_disagreement'
        review.validate_selections(package)
        package = deepcopy(self.package)
        seen = {}
        for item in review.items(package, 'correspondenceReviewItems'):
            for candidate in item['plausibleSameTargetClassCandidates']:
                key = candidate['key']
                if key in seen:
                    for selected in (item, seen[key]):
                        selected['researcherDisposition'] = 'semantic_equivalent'
                        selected['reviewedPredictionRecordKey'] = key
                    with self.assertRaisesRegex(review.original.prior.ReviewPackageError, 'one-to-one'):
                        review.validate_selections(package)
                    review.assert_neutral(self.package)
                    return
                seen[key] = item
        self.fail('Expected competing structural candidate fixture')

    def test_authority_drift_fails_closed(self) -> None:
        """A changed strict or prediction binding cannot produce another instrument."""
        for constant in ('STRICT_SHA', 'PREDICTIONS_SHA', 'BUILDER_SHA', 'PROTOCOL_SHA'):
            with patch.object(review, constant, '0' * 64):
                with self.assertRaisesRegex(ValueError, 'REVIEW_AUTHORITY_DRIFT'):
                    review.load_inputs()


if __name__ == '__main__':
    unittest.main()
