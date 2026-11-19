"""Item isolation, source roles and provenance under the offline v4 contract."""
from copy import deepcopy
import json
import unittest

from src.evaluation import step14_collective_item_replay as replay

ALIASES = {c: 'source-'+c for c in 'ABC'}


def assessment(category, ids, support):
    return dict(category=category, occurrenceIDs=list(ids), broaderReferent='Original description',
                supportingEvidenceIDs=list(support), contradictoryEvidenceIDs=[], granularity='model',
                rationale='Original reasoning', uncertainty='Original uncertainty')


def fixture():
    ends = [dict(occurrenceID=o, names=['M'], ontologyClass='ComputationalModel', sourceArtifactRef='S1',
                 evidence=[dict(evidenceID=o+'Q', text='original '+o)]) for o in ALIASES]
    sig = dict(signatureID='R',name='uses', compatibleSubjectClasses=['ComputationalModel'],
               compatibleObjectClasses=['ComputationalModel'])
    payload = dict(occurrences=ends,allowedPredicates=[sig])
    body = dict(input=json.dumps(payload),text=dict(format=dict(schema=replay.v3.legacy.schema(payload))))
    members = {oid:dict(ontologyClass='ComputationalModel',inventoryId='model',versions={}) for oid in ALIASES.values()}
    prov = {oid:dict(member=dict(occurrenceID=oid),endpoint=dict(occurrenceID=oid,sourceArtifacts=['artifact'],ontologyClass='ComputationalModel',
                                  selectedEvidence=[dict(literalExcerpt='original '+o,reference='quote/'+o,
                                                         fullQuoteSha256=o)])) for o,oid in ALIASES.items()}
    refs = replay.bind(payload, ALIASES, {'S1':'artifact'}, prov)
    value = dict(assessments=[assessment('strict_identity','AB',['AQ','BQ']),
                              assessment('abstention','C',['AQ'])],typedRelations=[],ontologyGaps=[])
    return value,body,refs,members


def run(data):
    value,body,refs,members=data
    return replay.items_for(value,body,ALIASES,refs,members)


class ItemReplayTests(unittest.TestCase):
    def test_independent_context_and_exact_provenance(self):
        data=fixture();before=deepcopy(data)
        (identity,abstain),layers=run(data)
        self.assertTrue(layers['partitionExact'])
        self.assertEqual((identity['status'],abstain['status']),(replay.VALID,'abstention'))
        self.assertEqual(abstain['externalEvidenceIDs'],['AQ'])
        self.assertEqual(abstain['citations'][0]['binding']['reference'],'quote/A')
        self.assertEqual(identity['modelItem'],before[0]['assessments'][0])
        self.assertEqual(data,before)

    def test_relation_endpoint_context_separation(self):
        for refs,valid in [(['AQ','CQ','BQ'],True),(['AQ','CQ'],False)]:
            data=fixture()
            data[0]['typedRelations']=[dict(subject='A',object='B',signatureID='R',evidenceIDs=refs,
                                            rationale='Asserted direction',uncertainty='possible')]
            rows,_=run(data)
            self.assertEqual(rows[0]['status'],replay.VALID)
            self.assertEqual(rows[-1]['status']==replay.VALID,valid)
            self.assertEqual(rows[-1]['externalEvidenceIDs'],['CQ'])

    def test_contradiction_or_external_strict_support_is_held(self):
        for field,ref,reason in [('contradictoryEvidenceIDs','CQ','CONTRADICTORY_IDENTITY'),
                                 ('supportingEvidenceIDs','CQ','AMBIGUOUS_EXTERNAL_IDENTITY_EVIDENCE')]:
            data=fixture();data[0]['assessments'][0][field].append(ref)
            rows,_=run(data)
            self.assertIn(reason,rows[0]['reasons'])
            self.assertEqual(rows[1]['status'],'abstention')

    def test_singleton_and_invalid_gaps(self):
        for ids,refs,status in [('A',['AQ'],'unresolved_observation'),('AB',['AQ'],replay.HELD)]:
            data=fixture()
            data[0]['ontologyGaps']=[dict(occurrenceIDs=list(ids),evidenceIDs=refs,
                                           proposedMeaning='Target missing',uncertainty='unknown')]
            rows,_=run(data)
            self.assertEqual(rows[-1]['status'],status)
            self.assertEqual(rows[-1]['modelItem']['proposedMeaning'],'Target missing')
            self.assertEqual(rows[0]['status'],replay.VALID)

    def test_unknown_reference_only_blocks_dependent_item(self):
        data=fixture();data[0]['assessments'][1]['supportingEvidenceIDs']=['invented']
        rows,layers=run(data)
        self.assertEqual(layers['unknownEvidenceIDs'],['invented'])
        self.assertEqual(rows[0]['status'],replay.VALID)
        self.assertIn('UNKNOWN_EVIDENCE',rows[1]['reasons'])

    def test_overlap_omission_and_malformed_assessment(self):
        data=fixture()
        data[0]['assessments']=[assessment('distinct','A',['AQ']),assessment('distinct','B',['BQ']),
                                dict(occurrenceIDs=['B'])]
        rows,layers=run(data)
        self.assertEqual(layers['overlappingAliases'],['B'])
        self.assertEqual(layers['omittedAliases'],['C'])
        self.assertEqual(rows[0]['status'],replay.VALID)
        self.assertTrue(all('PARTITION_OVERLAP' in r['reasons'] for r in rows[1:]))

    def test_multiple_windows_and_historical_protection(self):
        from collections import defaultdict
        row=run(fixture())[0][0]
        a,b=row['occurrenceIDs']
        scopes=defaultdict(set,{a:{(a,b),(a,'other')},b:{(a,b)}})
        flags,permitted=replay.reconciliation_gate(row,{a},scopes,{(a,b):{'other-unit'}})
        self.assertFalse(permitted)
        self.assertEqual(set(flags),{'protected_membership','competing_complete_membership','opposed_or_held_membership'})
        self.assertEqual(row['occurrenceIDs'],[a,b])
        scopes[a].remove((a,'other'))
        self.assertEqual(replay.reconciliation_gate(row,set(),scopes,{}),([],True))

    def test_distinct_member_contradiction_requires_review(self):
        data=fixture()
        item=assessment('distinct','C',['CQ','AQ'])
        data[0]['assessments'][1]=item
        self.assertEqual(run(data)[0][1]['status'],replay.VALID)
        item['contradictoryEvidenceIDs']=['CQ']
        self.assertIn('AMBIGUOUS_DISTINCT_CONTRADICTION',run(data)[0][1]['reasons'])
