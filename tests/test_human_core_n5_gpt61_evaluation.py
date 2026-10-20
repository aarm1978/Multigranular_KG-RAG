"""Focused offline integration checks for GPT-6.1 strict post-hoc scoring."""
from __future__ import annotations

from copy import deepcopy
import socket
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import human_core_n5_gpt61_evaluation as adapter


class GPT61PosthocTests(unittest.TestCase):
    """Reuse frozen matching and assert model-specific input isolation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Verify authenticity and byte-for-byte reproduction once with network disabled."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
            cls.result = adapter.run(verify_only=True)
            cls.package = adapter.read(adapter.PREDICTIONS)
            cls.frozen = adapter.scorer.load_frozen_inputs()

    def test_reference_inputs_and_opportunities_unchanged(self) -> None:
        """Only prediction records and their provenance are replaced."""
        inputs = adapter.prediction_inputs(self.frozen, self.package)
        for field in ('references', 'opportunities', 'routes', 'baseline_aliases'):
            self.assertIs(getattr(inputs, field), getattr(self.frozen, field))
        baseline = adapter.read(adapter.BASELINE)
        self.assertEqual(self.result['scoringOpportunities'], baseline['scoringOpportunities'])
        self.assertEqual(self.result['aggregate']['nodes']['referenceSupport'], 118)
        self.assertEqual(self.result['aggregate']['relations']['referenceSupport'], 61)
        self.assertEqual(self.result['comparisonWithFrozenGPT56']['aggregate'], baseline['aggregate'])

    def test_exact_native_compute_and_posthoc_labels(self) -> None:
        """All scoring results are exactly those of the original compute function."""
        native = adapter.scorer.compute(adapter.prediction_inputs(self.frozen, self.package))
        for field in ('aggregate', 'byUnit', 'byTarget', 'matchedRecords', 'unmatchedReferenceRecords',
                      'unmatchedPredictionRecords', 'distributedEvidenceDiagnostics'):
            self.assertEqual(self.result[field], native[field])
        self.assertEqual(self.result['status'], 'POST_HOC_MODEL_SENSITIVITY')
        self.assertFalse(self.result['confirmatoryStep7'])
        self.assertFalse(self.result['historicalResearcherJudgmentsUsed'])
        self.assertFalse(self.result['semanticEquivalenceReviewPerformed'])
        self.assertEqual(self.result['providerModelCalls'], 0)

    def test_scored_denominators_and_record_accounting(self) -> None:
        """Accepted monitoring records cannot inflate strict prediction support."""
        expected = {'nodes': (32, 95, 86, 127, 176), 'relations': (7, 60, 54, 67, 96)}
        for kind, singular in [('nodes', 'node'), ('relations', 'relation')]:
            tp, fp, fn, support, all_accepted = expected[kind]
            row = self.result['aggregate'][kind]
            self.assertEqual((row['TP'], row['FP'], row['FN'], row['predictionSupport']), (tp, fp, fn, support))
            self.assertEqual(self.result['predictionScopeAccounting'][kind]['allProductionAccepted'], all_accepted)
            self.assertEqual(len(self.result['matchedRecords'][kind]), tp)
            self.assertEqual(sum(r['kind'] == singular for r in self.result['unmatchedPredictionRecords']), fp)
            self.assertEqual(sum(r['kind'] == singular for r in self.result['unmatchedReferenceRecords']), fn)
            for breakdown in ('byUnit', 'byTarget'):
                self.assertEqual(sum(r.get(singular, {}).get('predictionSupport', 0) for r in self.result[breakdown].values()), support)

    def test_original_conversion_rejects_nonaccepted_record(self) -> None:
        """The original prediction converter remains the only record conversion path."""
        package = deepcopy(self.package)
        package['rows'][0]['acceptedSemanticProjection']['acceptedNodes'][0]['accepted'] = False
        with self.assertRaisesRegex(ValueError, 'nonaccepted'):
            adapter.prediction_inputs(self.frozen, package)

    def test_foreign_or_duplicate_unit_rejected(self) -> None:
        """Exactly five distinct historical unit identities are required."""
        for foreign in ('pub:999:sec:0001:unit:0001', adapter.extraction.UNITS[1]):
            package = deepcopy(self.package)
            package['rows'][0]['acceptedSemanticProjection']['sourceUnitID'] = foreign
            with self.assertRaisesRegex(ValueError, 'PREDICTION_SCOPE_DRIFT'):
                adapter.prediction_inputs(self.frozen, package)

    def test_result_provenance_and_projection_drift_rejected(self) -> None:
        """Changed model, selected attempt or accepted projection fails closed."""
        record = adapter.extraction.records()[0]
        prepared = adapter.extraction.rebuild(record)
        path = adapter.OUTPUT / (record['requestID'] + '.json')
        manifest = adapter.read(adapter.OUTPUT / 'extraction_manifest.json')
        for mutation, error in [('model', 'RESULT_IDENTITY_DRIFT'), ('attempt', 'SELECTION_DRIFT'),
                                ('projection', 'PERSISTED_PROJECTION_DRIFT')]:
            document = adapter.read(path)
            if mutation == 'model':
                document['model'] = 'gpt-5.6-sol'
            elif mutation == 'attempt':
                document['technicalResult']['attemptSelection']['selectedAttemptNumber'] = 2
            else:
                document['technicalResult']['acceptedSemanticProjection']['acceptedNodes'] = []
            with self.assertRaisesRegex(ValueError, error):
                adapter.verify_result(document, prepared, manifest)


if __name__ == '__main__':
    unittest.main()
