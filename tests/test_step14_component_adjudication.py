"""Complete partitions, independently attributed evidence and bounded staging."""
from copy import deepcopy
import json
import unittest

from src.evaluation import step14_component_adjudication as c


def fixture():
    """Prepare a complete A-B-C component with two version-specific source excerpts."""
    members={};ends={}
    for o, label in [('a','Model release 1'), ('b','Model release 1'), ('c','Model release 2')]:
        members[o]=dict(occurrenceID=o,ontologyClass='ComputationalModel',inventoryId='model',
                        versions={},sourceArtifacts=[o])
        ends[o]=dict(occurrenceID=o,ontologyClass='ComputationalModel',labels=[label],sourceArtifacts=[o],
                     sourceFamilies=['papers'],selectedEvidence=[dict(literalExcerpt=label,reference=o,fullQuoteSha256=o)])
    original=deepcopy((members,ends))
    template=dict(text=dict(format={}),instructions='',max_output_tokens=16384)
    body,aliases,sources=c.request(list(members),[('a','b'),('b','c')],ends,members,template)
    refs=c.replay.bind(json.loads(body['input']),aliases,sources,{o:dict(endpoint=e,member=members[o]) for o,e in ends.items()})
    assert original==(members,ends)
    return body,dict(aliases=aliases,sources=sources,evidence=refs,members=members,
                     protectedMemberships=[],priorMappings=[])


def prediction(*groups):
    """Create evidence-bound complete hypotheses in request-local IDs."""
    assessments=[]
    for ids in groups:
        assessments.append(dict(occurrenceIDs=list(ids),category='strict_identity' if len(ids)>1 else 'distinct',
                                granularity='named release',broaderReferent=None,
                                supportingEvidenceIDs=[o+'Q1' for o in ids],contradictoryEvidenceIDs=[],
                                rationale='Independent source statements',uncertainty='prediction'))
    return dict(assessments=assessments,relationLeads=[])


class ComponentTests(unittest.TestCase):
    def test_chain_is_one_question_with_two_hypotheses(self):
        scopes=[('a','b'),('b','c'),('d','e')]
        self.assertEqual(list(c.components(scopes,{scopes[0]})),[(['a','b','c'],scopes[:2])])
        body,_=fixture()
        self.assertEqual(json.loads(body['input'])['candidateMemberships'],[['E1','E2'],['E2','E3']])

    def test_alternative_partitions_and_complete_coverage(self):
        body,b=fixture()
        for value in (prediction(['E1','E2'],['E3']),prediction(['E1'],['E2'],['E3'])):
            self.assertEqual(c.evaluate(value,body,b)['partitionStatus'],'complete_prediction')
        for value in (prediction(['E1','E2']),prediction(['E1','E2'],['E2','E3'])):
            self.assertIn('INEXACT_PARTITION',c.evaluate(value,body,b)['partitionReasons'])

    def test_protected_boundary_and_version_specific_evidence(self):
        body,b=fixture()
        b['protectedMemberships']=[['a','b']]
        self.assertIn('PROTECTED_MEMBERSHIP_CHANGE',c.evaluate(prediction(['E1','E2','E3']),body,b)['partitionReasons'])
        result=c.evaluate(prediction(['E1','E2'],['E3']),body,b)
        self.assertEqual(result['partitionStatus'],'complete_prediction')
        self.assertEqual(result['assignments'][1]['citations'][0]['binding']['reference'],'c')
        self.assertEqual(json.loads(body['input'])['occurrences'][2]['evidence'][0]['text'],'Model release 2')
        b['members']['a']['granularity']='general model'
        b['members']['b']['granularity']='specific release'
        self.assertEqual(c.evaluate(prediction(['E1','E2'],['E3']),body,b)['partitionStatus'],'held')

    def test_optional_lead_validated_separately(self):
        body,b=fixture();v=prediction(['E1','E2'],['E3'])
        v['relationLeads']=[dict(subject='E1',object='E3',evidenceIDs=['E1Q1','E3Q1'],explanation='Release relationship'),
                            dict(subject='E1',object='E2',evidenceIDs=['no-such-quote'],explanation='Claim')]
        before=deepcopy(v)
        result=c.evaluate(v,body,b)
        self.assertEqual(result['partitionStatus'],'complete_prediction')
        first,second=result['relationLeads']
        self.assertEqual(first['endpoints'],['a','c']);self.assertEqual(first['status'],'evidence_lead')
        self.assertEqual(second['status'],'review_required');self.assertEqual(v,before)

    def test_staging_requires_global_final_or_unresolved(self):
        ids=[str(i) for i in range(80)]
        plan=c.staged_plan(ids,[dict(occurrenceIDs=ids)])
        self.assertEqual(plan['finalOccurrenceIDs'],ids)
        self.assertLessEqual(len(plan['evidenceReadings']),4)
        self.assertTrue(all(len(x)<=24 and plan['sharedOccurrence'] in x for x in plan['evidenceReadings']))
        self.assertEqual(set().union(*map(set,plan['evidenceReadings'])),set(ids))
        self.assertEqual(c.staged_plan(ids+['extra']*20,[])['status'],'unresolved_exceeds_bounded_plan')
