"""Focused alias-nomination tests; no semantic identity decisions."""
from copy import deepcopy
import socket
import unittest
from unittest.mock import patch
from src.evaluation import step14_explicit_alias_preview as a
from test_step14_evidence_review_batch import named


class AliasTests(unittest.TestCase):
    def setUp(self):
        """Block network access for all fixtures."""
        for method in ('connect','connect_ex'):
            p=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'))
            p.start();self.addCleanup(p.stop)

    def test_explicit_alias_forms(self):
        """Recover explicit formatting, acronym and whole-base qualifier cases."""
        for left,right,kind in [('GEE','Google Earth Engine (GEE)','explicit_parenthetical'),
            ('HEC-HMS','Hydrologic Modeling System (HEC-HMS)','explicit_parenthetical'),
            ('Google Earth Engine','Google Earth Engine (GEE)','explicit_parenthetical'),
            ('NextGen','NextGen framework','base_with_descriptive_qualifier'),
            ('Backpropagation','backpropagation','format_variant'),
            ('HEC-HMS','HEC HMS','format_variant')]:
            with self.subTest(left=left):
                self.assertEqual(a.alias_cue(left,right)['kind'],kind)

    def test_false_positive_and_version_risks(self):
        """Generic overlap, unasserted acronyms and distinct numeric releases do not qualify."""
        for left,right in [('model','model framework'),('LSTM','ARLSTM'),
            ('National Water Model','National Weather Model'),('GEE','Google Earth Engine'),
            ('NWM v2.1','NWM v3.0'),('ModelX 1.0','ModelX 10'),('River Tool','River Model')]:
            with self.subTest(left=left,right=right):self.assertIsNone(a.alias_cue(left,right))
        self.assertFalse(a.grounded_name('LSTM','ARLSTM is used here'))

    def test_thin_context_and_structured_versions_preserved(self):
        """Thin but literal context can nominate; specificity stays unresolved and unchanged."""
        left=named('a','NextGen',quote='NextGen');right=named('b','NextGen framework')
        left['versions']={'version':'2'};right['versions']={'version':'3'}
        original=deepcopy((left,right))
        result=a.nominate(left,right)
        self.assertTrue(result['nominated'])
        self.assertIn('thin_context_requires_review',result['flags'])
        self.assertIn('version_metadata_differs_or_missing',result['flags'])
        self.assertIsNone(result['identityDecision']);self.assertEqual((left,right),original)

    def test_grounding_and_class_fail_closed(self):
        """Label assertions without traceable literal support do not trigger the route."""
        left=named('a','GEE',quote='a different tool is described')
        right=named('b','Google Earth Engine (GEE)')
        self.assertFalse(a.nominate(left,right)['nominated'])
        right['ontologyClass']='Algorithm'
        with self.assertRaisesRegex(ValueError,'CLASS_DRIFT'):a.nominate(left,right)

    def test_controls_do_not_become_new_submissions(self):
        """Exact approval exclusions remain even when a format alias rescues a missed control."""
        left=named('a','Backpropagation');right=named('b','backpropagation')
        left['priorMemberships']['approved']=right['priorMemberships']['approved']=['D1']
        review=a.baseline.reconciliation.review_status(left,right)
        sig=dict(dual=False,exceptionalSingle=False,contextualBoth=True,reciprocal=True,
                 distinctiveSharedTokens=['backpropagation'],sharedLiteralReferences=[])
        detail=dict(pairKeySha256=a.r.candidates.token(['a','b']),occurrenceIDs=['a','b'],
            ontologyClass=left['ontologyClass'],scope=a.r.pair_scope(left,right),sourceFamilyPair='github | github',
            originalReference={'line':1},originalPriorReview=review,
            assessment=dict(eligible={'alias_extended':False},priorStatus=review['primary'],
                selectionSignals=sig,scores={'name':.94,'evidence':.6}))
        result=a.inspect_row(detail,{'a':left,'b':right},False)
        self.assertTrue(result['alias']['nominated']);self.assertFalse(result['incrementalEligible'])
        self.assertFalse(result['combinedEligible']);self.assertEqual(result['controlFailureReasons'],['score_gate'])
        right['priorMemberships']['approved']=[]
        detail['originalPriorReview']=a.baseline.reconciliation.review_status(left,right)
        self.assertTrue(a.inspect_row(detail,{'a':left,'b':right},False)['incrementalEligible'])


if __name__=='__main__':unittest.main()
