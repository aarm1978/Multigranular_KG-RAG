"""Focused offline pair coverage, independent projection and once-only dispatch tests."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_queue_compatibility_pilot as p


def payload():
    """Construct a small existing queue payload with literal evidence and shared guidance."""
    return dict(instructions='original',entities=[dict(id=x,ontologyClass='Tool',names=[x],sourceFamilies=['github'],sources=['S1'],
        evidence=[dict(id=x+'Q1',text='literal documented '+x)],incidentRelations=[],recordedVersionOrImplementation={},
        granularity='unspecified_requires_context_review',sourceRole='Source-local occurrence; referent role must be established from quotation.') for x in ('E1','E2','E3')],
        pairs=[dict(id='P1',entities=['E1','E2']),dict(id='P2',entities=['E1','E3'])])


def body():
    """Use the original five-category schema adapter with explicit pairs."""
    x=p.project(payload())
    return dict(model=p.live.MODEL,input=json.dumps(x),text={'format':{'schema':p.schema_for('C01',x)}})


def recommendation():
    """A structurally valid independent assessment for each explicitly listed pair."""
    return dict(status='recommendation_only',caseID='C01',assessments=[dict(pairID=f'P{i}',identityLevel='entity',recommendation='same_entity_candidate',
        granularityAssessment='named software',versionAssessment='unspecified',ownerReferenceAssessment='documented reference',
        evidenceIDs=['E1Q1',f'E{i+1}Q1'],conflictEvidenceIDs=[],rationale='Both literal records describe the proposed referent.',missingInformation=[]) for i in (1,2)])


class PilotTests(unittest.TestCase):
    def setUp(self):
        """All test provider behavior is injected and network calls are forbidden."""
        for method in ('connect','connect_ex'):
            mock=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'));mock.start();self.addCleanup(mock.stop)

    def test_selection_coverage_and_four_hash_units(self):
        """Select exactly 16 reproducibly, including a non-curated hash component."""
        rows=[dict(unitID=f'U{i}',tags=[f't{i%8}']) for i in range(40)]
        result=p.choose(rows)
        self.assertEqual(len(result),16);self.assertEqual(len({x['unitID'] for x in result}),16)
        self.assertEqual(sum(x['selection']=='hash_selected' for x in result),4)
        self.assertEqual(result,p.choose(list(reversed(rows))))

    def test_referent_tags_ignore_incidental_mentions(self):
        """Coverage labels require candidate names, not unrelated words in quotations."""
        x=payload();x['entities'][0]['evidence'][0]['text']='NWM LSTM NextGen NGIAB'
        t=p.tags(x,{'alias_extended'})
        self.assertFalse({'NWM','LSTM','NextGen','NGIAB'}&t)
        x['entities'][0]['names']=['NWM v2.1'];x['entities'][1]['names']=['NWM v3.0']
        self.assertIn('recorded_specificity_difference',p.tags(x,{'alias_extended'}))

    def test_projection_preserves_science_and_original(self):
        """Remove only known redundant fields and independently retain literals and pairs."""
        original=payload();before=deepcopy(original);x=p.project(original)
        self.assertEqual(original,before);self.assertEqual(x['pairs'],original['pairs'])
        for source,target in zip(original['entities'],x['entities']):
            self.assertEqual(source['evidence'],target['evidence']);self.assertNotIn('sourceRole',target)
            self.assertNotIn('recordedVersionOrImplementation',target)
        original['entities'][0]['recordedVersionOrImplementation']={'version':'2'}
        self.assertEqual(p.project(original)['entities'][0]['recordedVersionOrImplementation'],{'version':'2'})

    def test_pair_coverage_citations_scope_and_abstention(self):
        """No omissions, duplicate pairs, foreign citations or unexplained abstention."""
        request=body();valid=recommendation();self.assertEqual(p.validate(valid,request)['assessedPairs'],2)
        for change in ('duplicate','foreign','single_endpoint','scope','empty'):
            x=deepcopy(valid)
            if change=='duplicate':x['assessments'][1]['pairID']='P1'
            if change=='foreign':x['assessments'][0]['evidenceIDs']=['E1Q1','E3Q1']
            if change=='single_endpoint':x['assessments'][0]['evidenceIDs']=['E1Q1']
            if change=='scope':x['assessments'][0]['identityLevel']='conceptual'
            if change=='empty':x['assessments'][0]['rationale']=' '
            with self.subTest(change=change),self.assertRaises(ValueError):p.validate(x,request)
        valid['assessments'][0].update(recommendation='abstain',identityLevel='unresolved',evidenceIDs=[],missingInformation=['entity version unknown'])
        self.assertEqual(p.validate(valid,request)['abstentions'],1)

    def test_ambiguous_post_never_repeated(self):
        """An uncertain intent is durable and permanently blocks automatic redispatch."""
        calls=[]
        def fail(request):
            calls.append(request);raise OSError('sensitive exception text')
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'attempt'
            with self.assertRaisesRegex(ValueError,'UNCERTAIN_OUTCOME_STOP'):p.attempt(folder,body(),fail)
            with self.assertRaisesRegex(ValueError,'UNCERTAIN_OUTCOME_STOP'):p.attempt(folder,body(),fail)
            self.assertEqual(len(calls),1)
            self.assertNotIn('sensitive exception', (folder/'outcome.json').read_text())

    def test_completed_resume_and_usage_latency(self):
        """Authentic response and usage persist; a resumed command does not POST again."""
        calls=[]
        def call(request):
            calls.append(request)
            return dict(id='resp_fixture',model=p.live.MODEL,status='completed',incomplete_details=None,error=None,
                usage={'input_tokens':100,'output_tokens':50,'total_tokens':150},
                output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(recommendation()))])])
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'attempt';first=p.attempt(folder,body(),call)
            self.assertEqual(first['status'],'validated_recommendation_only')
            self.assertEqual(first['tokens']['inputTokens'],100);self.assertGreaterEqual(first['latencySeconds'],0)
            self.assertEqual(p.attempt(folder,body(),call),first);self.assertEqual(len(calls),1)
            changed=body();changed['model']='different'
            with self.assertRaisesRegex(ValueError,'INTENT_DRIFT'):p.attempt(folder,changed,call)


if __name__=='__main__':unittest.main()
