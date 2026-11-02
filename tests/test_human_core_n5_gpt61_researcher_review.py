"""Focused offline validation of exact GPT-6.1 researcher-ledger materialization."""
from __future__ import annotations

from copy import deepcopy
import inspect
import socket
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import human_core_n5_gpt61_researcher_review as review


class GPT61ResearcherReviewTests(unittest.TestCase):
    """Test mechanics only; synthetic mutations are never written to research artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        """Verify byte-identical materialization with network and strict scoring disabled."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')), \
             patch.object(review.instrument.evaluation.scorer, 'compute', side_effect=AssertionError('NO_STRICT_RESCORING')):
            cls.artifact = review.run(verify=True)
            cls.ledger, cls.source = review.load_authorities()
            cls.logic = review.implementation()

    def test_373_identities_and_exact_fields(self) -> None:
        """Every selected key, disposition, code and note equals the pinned ledger exactly."""
        source_index = self.logic._index_source(self.source)
        output_index = self.logic._index_source(self.artifact)
        ledger_index = self.logic._ledger_entries(self.ledger)
        self.assertEqual(len(ledger_index), 373)
        self.assertEqual(set(source_index), set(output_index))
        self.assertEqual(set(source_index), set(ledger_index))
        for identity, (pass_name, entry) in ledger_index.items():
            fields = ('researcherDisposition', 'reviewedPredictionRecordKey', 'optionalExplanatoryCode', 'researcherNote') if pass_name.startswith(('A_', 'C_')) else ('predictionSourceSupportJudgment', 'optionalExplanatoryCode', 'researcherNote')
            item = deepcopy(output_index[identity][1])
            for field in fields:
                self.assertEqual(item[field], entry[field])
                item[field] = None
            self.assertEqual(item, source_index[identity][1])
        self.assertEqual(self.artifact['reviewProvenance'], self.ledger['reviewProvenance'])

    def test_frozen_implementation_reuse(self) -> None:
        """Exact-copy and metric functions are unchanged; only explicit cohort guards differ."""
        adapted = review.adapted_sources()
        for name, source in adapted.items():
            expected = inspect.getsource(getattr(review.original, name))
            for before, after in review.SUBSTITUTIONS.get(name, []):
                expected = expected.replace(before, after)
            self.assertEqual(source, expected)
        for name in ('_validate_and_apply', '_metrics'):
            self.assertEqual(adapted[name], inspect.getsource(getattr(review.original, name)))
        self.assertEqual(review.original.EXPECTED_POPULATION['B_nodePredictionSourceSupport'], 109)

    def test_metrics_and_frozen_comparison(self) -> None:
        """The four original formulas use their complete authorized model-specific populations."""
        expected = {'humanCoreNodeSemanticRecovery': (78, 118), 'humanCoreRelationSemanticRecovery': (41, 61),
                    'correctedNodePredictionSourceSupportedRate': (120, 127),
                    'correctedRelationPredictionSourceSupportedRate': (65, 67)}
        self.assertEqual(self.artifact['secondaryMetrics'], self.logic._metrics(self.artifact))
        for name, (numerator, denominator) in expected.items():
            self.assertEqual(self.artifact['secondaryMetrics'][name],
                             dict(numerator=numerator, denominator=denominator, value=numerator / denominator))
        self.assertEqual(self.artifact['comparisonWithFrozenGPT56']['secondaryMetrics'],
                         review.read(review.original.OUTPUT)['secondaryMetrics'])
        self.assertFalse(self.artifact['step7CReopened'])
        self.assertFalse(self.artifact['semanticJudgmentsPerformedByMaterializer'])
        self.assertEqual(self.artifact['providerModelCalls'], 0)

    def test_provenance_population_and_missing_judgments_fail_closed(self) -> None:
        """Reject missing identities, incorrect units/keys, pass counts and unpopulated decisions."""
        for mutation in ('id', 'unit', 'record', 'missing', 'population'):
            ledger = deepcopy(self.ledger)
            rows = ledger['passes']['A_nodeCorrespondence']
            if mutation == 'id':
                rows[0]['reviewItemID'] = 'unbound-review-id'
            elif mutation == 'unit':
                rows[0]['sourceUnitID'] = 'pub:999:sec:0001:unit:0001'
            elif mutation == 'record':
                rows[0]['humanCoreRecordKey'] = 'unbound-record'
            elif mutation == 'missing':
                rows[0]['researcherDisposition'] = None
            else:
                rows.pop()
            with self.assertRaises(review.original.prior.ReviewPackageError):
                self.logic._validate_and_apply(ledger, self.source)

    def test_selections_one_to_one_and_relation_context(self) -> None:
        """Require 119 exact unique eligible selections and reject duplicate or absent context."""
        self.logic._validate_materialized(self.artifact, self.ledger)
        correspondence = review.instrument.items(self.artifact, 'correspondenceReviewItems')
        selected = [x for x in correspondence if x['researcherDisposition'] == 'semantic_equivalent']
        self.assertEqual(len(selected), 119)
        self.assertEqual(len({x['reviewedPredictionRecordKey'] for x in selected}), 119)
        for mutation in ('duplicate', 'endpoint'):
            artifact = deepcopy(self.artifact)
            rows = [x for x in review.instrument.items(artifact, 'correspondenceReviewItems')
                    if x['researcherDisposition'] == 'semantic_equivalent']
            if mutation == 'duplicate':
                rows[1]['reviewedPredictionRecordKey'] = rows[0]['reviewedPredictionRecordKey']
            else:
                next(x for x in rows if x['humanCoreRecord']['kind'] == 'relation')['humanCoreRecord']['endpointContext'] = {}
            with self.assertRaises(review.original.prior.ReviewPackageError):
                self.logic._validate_materialized(artifact, self.ledger)

    def test_hash_guards_and_source_neutrality(self) -> None:
        """Pinned sources cannot drift; source instrument remains neutral after materialization."""
        for constant in ('LEDGER_SHA', 'INSTRUMENT_SHA', 'IMPLEMENTATION_SHA', 'BASELINE_SHA'):
            with patch.object(review, constant, '0' * 64):
                with self.assertRaisesRegex(ValueError, 'AUTHORITY_DRIFT'):
                    review.load_authorities()
        review.instrument.assert_neutral(review.read(review.instrument.OUTPUT))
        self.assertEqual(review.original._sha256(review.LEDGER), review.LEDGER_SHA)


if __name__ == '__main__':
    unittest.main()
