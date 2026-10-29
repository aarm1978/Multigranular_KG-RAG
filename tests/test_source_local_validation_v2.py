"""Focused prospective correction tests; authentic fields are never repaired."""
from copy import deepcopy
import unittest
import test_source_local_semantics as fixtures
from src.evaluation import source_local_supplemental_review_v2 as review


class CorrectionTests(unittest.TestCase):
    setUp=fixtures.SourceLocalTests.setUp
    build=fixtures.SourceLocalTests.build
    node=fixtures.SourceLocalTests.node
    edge=fixtures.SourceLocalTests.edge
    run_payload=fixtures.SourceLocalTests.run_payload

    def test_quarantine_keeps_valid_candidates_and_exact_invalid_fields(self):
        """A bad abstention source cannot repair itself or invalidate independent evidence."""
        p=self.build('github','Streamflow is an output variable.')
        n=self.node(p,'A-DOM04','Variable','Streamflow is an output variable.')
        bad=dict(abstentionID='a',inventoryId='C-C24',sourceUnitIDs=['invented source'],
                 disposition='abstained_no_evidence',reason='No parameter evidence')
        original=deepcopy(bad)
        before=self.run_payload(p,[n],[])
        after=self.run_payload(p,[n],[],[bad])
        self.assertEqual(before['decisions'],after['decisions'])
        self.assertEqual(len(after['projection']['nodes']),1)
        self.assertEqual(after['abstentions'],[])
        self.assertEqual(after['quarantinedAbstentions'][0]['originalAbstention'],original)
        self.assertEqual(after['quarantinedAbstentions'][0]['reasons'],['abstention_source_unit_not_selected'])
        self.assertFalse(after['quarantinedAbstentions'][0]['countsAsNoEvidence'])
        self.assertEqual(bad,original)

    def test_null_unclassified_purpose_stays_non_kg(self):
        """Authorized null target diagnostics do not crash or become accepted edges."""
        for classification in ('unclassified','ambiguous'):
            p=self.build('github','This repository contains assorted scripts.')
            e=self.edge(p,'C-C07','hasPurpose','This repository contains assorted scripts.')
            e.update(target=None,categoryKey=None,classification=classification,reason='No supported category')
            report=self.run_payload(p,[],[e])
            self.assertFalse(report['projection']['nodes'])
            self.assertFalse(report['projection']['edges'])
            self.assertTrue(all(d['disposition']!='accepted' for d in report['decisions']))

    def test_global_identity_and_schema_checks_remain_strict(self):
        """Quarantine is applied only after strict schema and unique-identity validation."""
        p=self.build('github','Streamflow is an output variable.')
        n=self.node(p,'A-DOM04','Variable','Streamflow is an output variable.',cid='same')
        bad=dict(abstentionID='same',inventoryId='C-C24',sourceUnitIDs=['invalid'],
                 disposition='abstained_no_evidence',reason='None')
        with self.assertRaisesRegex(ValueError,'ambiguous_candidate_identity'):
            self.run_payload(p,[n],[],[bad])
        bad['abstentionID']='a';bad['unexpected']='not allowed'
        with self.assertRaises(Exception):self.run_payload(p,[n],[],[bad])

    def test_independent_evidence_holds_unchanged(self):
        """Quarantining an abstention cannot release an invalid candidate's evidence gate."""
        p=self.build('github','Streamflow is an output variable.')
        e=self.edge(p,'C-C12','mentionsVariable','invented quote')
        n=self.node(p,'A-DOM04','Variable','Streamflow is an output variable.')
        before=self.run_payload(p,[n],[e])
        after=self.run_payload(p,[n],[e],[dict(abstentionID='a',inventoryId='C-C24',sourceUnitIDs=['bad'],
                    disposition='abstained_no_evidence',reason='none')])
        self.assertEqual(before['decisions'],after['decisions'])
        self.assertFalse(after['projection']['edges'])

    def test_regression_gate_stops_changed_acceptance(self):
        """Unexpected historical changes must escape ordinary per-request error reporting."""
        native=dict(decisions=[{'disposition':'held'}],projection={},unresolvedAssertions=[],derivedConstructionInput={})
        a=dict(requestID='r',nativeValidationView=native,abstentions=[])
        b=deepcopy(a);b['quarantinedAbstentions']=[]
        review.assert_same_decisions(a,b)
        b['nativeValidationView']['decisions'][0]['disposition']='accepted'
        with self.assertRaises(review.RegressionStop):review.assert_same_decisions(a,b)


if __name__=='__main__':unittest.main()
