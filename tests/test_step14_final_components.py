"""Regression tests for whole-component judgments and item-level recovery."""
from copy import deepcopy
import json
import unittest

from src.evaluation import step14_final_components as f


def fixture(n=5):
    """Make source-local quotes, including a repeated literal owned by different records."""
    ids=[f'o{i}' for i in range(n)]
    members={o:dict(occurrenceID=o,ontologyClass='ComputationalModel',inventoryId='M',
                    versions={},sourceArtifacts=[o]) for o in ids}
    ends={o:dict(occurrenceID=o,ontologyClass='ComputationalModel',labels=['Model'],
                 sourceArtifacts=[o],sourceFamilies=['papers'],selectedEvidence=[
                     dict(literalExcerpt='The same text',reference=o,fullQuoteSha256='hash')]) for o in ids}
    b,aliases,sources=f.previous.request(ids,[ids],ends,members,
                                          dict(text=dict(format={}),instructions='',max_output_tokens=16384))
    refs=f.replay.bind(json.loads(b['input']),aliases,sources,{o:dict(member=members[o],endpoint=e) for o,e in ends.items()})
    return f.final_body(b,aliases,[],[]),dict(aliases=aliases,evidence=refs,members=members,protectedMemberships=[],priorTargets={})


def group(*ids):
    return dict(category='strict_identity' if len(ids)>1 else 'distinct',occurrenceIDs=list(ids),
                supportingEvidenceIDs=[o+'Q1' for o in ids],qualifyingEvidenceIDs=[],contradictoryEvidenceIDs=[],
                broaderReferent=None,granularity='entity',rationale='direct evidence',uncertainty='prediction',
                conflictAssessment='no_conflict')


class FinalComponentTests(unittest.TestCase):
    def test_qualification_and_multiple_groups(self):
        body,b=fixture()
        first=group('E1','E2')
        first.update(qualifyingEvidenceIDs=['E2Q1'],conflictAssessment='compatible_qualification')
        v=dict(assessments=[first,group('E3','E4'),group('E5')],relationLeads=[])
        before=deepcopy(v)
        result=f.evaluate(v,body,b)
        self.assertEqual(result['status'],'complete_prediction')
        self.assertEqual(result['assignments'][0]['qualificationBindings'][0]['binding']['occurrenceID'],'o1')
        self.assertEqual(v,before)

    def test_material_conflict_preserves_other_group_and_lead(self):
        body,b=fixture()
        a=group('E1','E2')
        a.update(contradictoryEvidenceIDs=['E2Q1'],conflictAssessment='material_conflict')
        lead=dict(subject='E3',object='E5',evidenceIDs=['E3Q1','E5Q1'],explanation='source-supported dependence')
        v=dict(assessments=[a,group('E3','E4'),group('E5')],relationLeads=[lead,dict(lead,subject='E9')])
        result=f.evaluate(v,body,b)
        self.assertEqual(result['mechanicallyUnresolved'],['o0','o1'])
        self.assertEqual(result['assignments'][1]['status'],f.replay.VALID)
        self.assertEqual([l['status'] for l in result['relationLeads']],['evidence_lead','mechanically_unresolved'])

    def test_substantive_ambiguity_abstention_and_protection(self):
        body,b=fixture()
        b['protectedMemberships']=[['o0','o1']]
        a=group('E1','E2','E3')
        singleton=dict(group('E4'),category='abstention',conflictAssessment='unresolved_ambiguity')
        result=f.evaluate(dict(assessments=[a,singleton,group('E5')],relationLeads=[]),body,b)
        self.assertIn('PROTECTED_MEMBERSHIP_CHANGE',result['assignments'][0]['reasons'])
        self.assertEqual(result['assignments'][1]['status'],'abstention')
        self.assertNotIn('o3',result['mechanicallyUnresolved'])

    def test_large_exact_coverage_and_bad_lead(self):
        body,b=fixture(348);payload=json.loads(body['input'])
        self.assertEqual(len(payload['textTable']),1)
        self.assertLess(f.pilot_preflight.check_schema_limits(body['text']['format']['schema'])['enums'],1000)
        value=dict(assessments=[group(*b['aliases'])],relationLeads=[{'broken':True}])
        self.assertEqual(f.evaluate(value,body,b)['status'],'complete_prediction')
        value['assessments']=[group(*list(b['aliases'])[:-1])]
        self.assertEqual(f.evaluate(value,body,b)['mechanicallyUnresolved'],['o347'])
