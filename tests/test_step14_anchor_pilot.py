"""Focused offline bindings and shared-transport regression tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_anchor_pilot as p


def fixture():
    """Two source-bound occurrences, with intentionally different versions."""
    unit = dict(occurrences=[dict(occurrenceID=o, ontologyClass='ProcessBasedModel',
        names=['NWM'], sourceFamilies=[f], versions={}, granularity='unspecified',
        evidence=[dict(evidenceID=e, text=t)]) for o,f,e,t in (
            ('a','publications','E1Q1','National Water Model version 2.1'),
            ('b','ciroh_hub','E2Q1','National Water Model version 3.0'))])
    body = dict(input=json.dumps(unit), text=dict(format=dict(schema=p.schema(unit))))
    value = dict(assessments=[dict(category='broader_correspondence', occurrenceIDs=['a','b'],
        broaderReferent='National Water Model', granularity='family; separate versions',
        supportingEvidenceIDs=['E1Q1','E2Q1'], contradictoryEvidenceIDs=[],
        rationale='Different versions of a proposed common model family.', uncertainty='Hypothesis, not approval.')])
    return body,value


class PilotTests(unittest.TestCase):
    def test_broader_hypothesis_preserves_versions(self):
        body,value=fixture(); original=json.dumps(body)
        self.assertFalse(p.validate(value,body)['semanticValidation'])
        self.assertEqual(original,json.dumps(body))

    def test_missing_and_misbound_evidence(self):
        for citations in (['E1Q1'],['E1Q1','E9Q1']):
            body,value=fixture(); value['assessments'][0]['supportingEvidenceIDs']=citations
            with self.assertRaises(ValueError):p.validate(value,body)

    def test_unassessed_and_class_mismatch(self):
        body,value=fixture(); a=value['assessments'][0]
        a.update(category='abstention',broaderReferent=None,occurrenceIDs=['a'],supportingEvidenceIDs=[])
        with self.assertRaises(ValueError):p.validate(value,body)
        body,value=fixture(); unit=json.loads(body['input']);unit['occurrences'][1]['ontologyClass']='Tool';body['input']=json.dumps(unit)
        value['assessments'][0].update(category='strict_identity',broaderReferent=None)
        with self.assertRaises(ValueError):p.validate(value,body)

    def test_schema_and_duplicate_keys(self):
        body,value=fixture();p.Draft202012Validator.check_schema(body['text']['format']['schema'])
        with self.assertRaises(ValueError):p.transport.decode(b'{"a":1,"a":2}')
        value['approved']=True
        with self.assertRaises(Exception):p.validate(value,body)

    def test_transport_parity_and_once_only(self):
        body,value=fixture()
        response=dict(status='completed', usage=dict(input_tokens=1,output_tokens=2),output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])])
        class FakeAPI:
            """No network; exercise the native live and Batch interfaces."""
            def request(self,method,path,data):
                self.live_body=json.loads(data);return p.live.encode(response)
            def upload(self,path):
                self.batch_body=json.loads(path.read_text())['body'];return dict(id='file')
            def create(self,file_id,metadata):return dict(id='batch')
            def retrieve(self,batch_id):return dict(status='completed',output_file_id='output')
            def content(self,file_id):return p.live.encode(dict(custom_id='U02',response=dict(body=response)))+b'\n'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);api=FakeAPI()
            for uid in ('U01','U02'):p.live.save(root/'requests'/f'{uid}.json',body)
            p.live.write(root/'requests.jsonl',b''.join(p.live.encode(dict(custom_id=u,body=body))+b'\n' for u in ('U01','U02')))
            with patch.object(p,'verify',return_value=dict(units=[dict(unitID='U01'),dict(unitID='U02')])):
                p.live.save(root/'manifest.json',{})
                p.operate(root,'live',['U01'],api)
                with self.assertRaises(ValueError):p.operate(root,'submit',['U01'],api)
                p.operate(root,'submit',api=api)
                self.assertEqual(api.live_body,api.batch_body)
                self.assertEqual(p.operate(root,'retrieve',api=api)['missing'],[])
                self.assertEqual(p.operate(root,'retrieve',api=api)['results']['U02']['identityApprovals'],0)

    def test_selection_strata_and_no_union(self):
        groups={};components=[];endpoints={};pairs=[];ineligible=set()
        for c in range(6):
            ids=[f'c{c}o{i}' for i in range(3 if c<3 else 14)]
            for i,o in enumerate(ids):
                endpoints[o]=dict(sourceFamilies=['publications' if c==2 or i%2 else 'github'], selectedEvidence=[dict(literalExcerpt='model')])
            keys=[]
            for i in range(1,len(ids)):
                key=f'g{c}-{i}';keys.append(key)
                groups[key]=dict(occurrenceIDs=[ids[0],ids[i]],originalGroupIDs=[key])
            components.append(dict(groupIDs=keys))
        for i in range(6):
            ids=[f'p{i}a',f'p{i}b']
            for o in ids:endpoints[o]=dict(sourceFamilies=['publications'],selectedEvidence=[dict(literalExcerpt='model version 2 different')])
            pairs.append(dict(occurrenceIDs=ids,pairKeySha256=str(i),identityScope='within_family' if i==5 else 'between_families',category='same_entity_candidate' if i<4 else 'different_entities_candidate'))
            if i<4:ineligible.add(str(i))
        selected=p.select(groups,components,endpoints,pairs,ineligible)
        self.assertEqual([u['stratum'] for u in selected],list('AAAAAABBBBCC'))
        ids=[o for u in selected for o in u['occurrenceIDs']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertLessEqual(len(ids),120)
        self.assertTrue(all(len(u['occurrenceIDs'])<=12 for u in selected))
        self.assertEqual(selected,p.select(groups,components,endpoints,pairs,ineligible))

    def test_claim_blocks_other_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p.claim(root,'U01','live')
            with self.assertRaises(FileExistsError):p.claim(root,'U01','batch')


if __name__=='__main__':unittest.main()
