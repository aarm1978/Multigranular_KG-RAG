"""Focused offline preparation, signature and execution checks."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_alignment_workflow as w


def fixture():
    """An implementation relationship with source-bound evidence on both endpoints."""
    payload=dict(occurrences=[dict(occurrenceID=o,ontologyClass=c,names=[o],sourceFamilies=['github'],versions={},granularity='unspecified',
        evidence=[dict(evidenceID=e,text='Repository R implements the NWM model.')]) for o,c,e in
        [('model','ProcessBasedModel','E1Q1'),('repo','Repository','E2Q1')]],allowedPredicates=[dict(id='D-22',name='implementedBy',
            compatibleSubjectClasses=['ProcessBasedModel'],compatibleObjectClasses=['Repository'])])
    body=dict(input=json.dumps(payload),text=dict(format=dict(schema=w.response_schema(payload))))
    assessments=[dict(category='abstention',occurrenceIDs=[o],broaderReferent=None,granularity='unspecified',
        supportingEvidenceIDs=[],contradictoryEvidenceIDs=[],rationale='No identity claim.',uncertainty='Separate referents.') for o in ('model','repo')]
    value=dict(assessments=assessments,typedRelations=[dict(subject='model',object='repo',signatureID='D-22',
        evidenceIDs=['E1Q1','E2Q1'],rationale='Explicit implementation statement.',uncertainty='Not human validated.')],ontologyGaps=[])
    return body,value


class WorkflowTests(unittest.TestCase):
    def test_existing_hierarchy_and_signature(self):
        spec=w.yaml.safe_load(w.SPEC.read_text());h=w.ancestors(spec)
        self.assertTrue(w.fits('ProcessBasedModel','ComputationalModel',h))
        self.assertFalse(w.fits('DatasetResource','ComputationalModel',h))
        endpoints={'a':dict(ontologyClass='MLModel'),'b':dict(ontologyClass='Tool')}
        rels=w.allowed_relations(['a','b'],endpoints,spec,h)
        self.assertIn('hasComponent',{x['name'] for x in rels})
        self.assertNotIn('isMemberOf',{x['name'] for x in rels})
        self.assertNotIn('consolidatesTo',{x['name'] for x in rels})

    def test_directed_evidence_bound_relation(self):
        body,value=fixture();self.assertFalse(w.validate(value,body)['semanticValidation'])
        value['typedRelations'][0].update(subject='repo',object='model')
        with self.assertRaisesRegex(ValueError,'SIGNATURE'):w.validate(value,body)

    def test_evidence_and_gap_fail_closed(self):
        body,value=fixture();value['typedRelations'][0]['evidenceIDs']=['E1Q1']
        with self.assertRaisesRegex(ValueError,'UNCITED'):w.validate(value,body)
        body,value=fixture();value['ontologyGaps']=[dict(occurrenceIDs=['model','repo'],proposedMeaning='Unsupported family relation',evidenceIDs=['E1Q1','FAKE'],uncertainty='Unreviewed')]
        with self.assertRaisesRegex(ValueError,'BINDING'):w.validate(value,body)

    def test_packing_no_transitive_union_and_edge_coverage(self):
        edges={(f'o{i}',f'o{i+1}') for i in range(30)}
        units=w.pack_edges(edges)
        self.assertTrue(all(len(x)<=12 for x in units))
        self.assertTrue(all(any({a,b}<=set(u) for u in units) for a,b in edges))
        self.assertEqual(units,w.pack_edges(edges))
        original=[dict(occurrenceIDs=list(e)) for e in sorted(edges)]
        before=json.dumps(original)
        neighborhoods=w.component_units(original)
        self.assertEqual({o for x in neighborhoods for o in x},{o for e in edges for o in e})
        self.assertEqual(json.dumps(original),before)
        self.assertGreater(len(neighborhoods),1)

    def test_negative_relational_cues_need_both_entities_and_affirmation(self):
        def endpoints(text):
            return {o:dict(occurrenceID=o,labels=[o],selectedEvidence=[dict(literalExcerpt=text)]) for o in ('Alpha','Beta')}
        pair=dict(occurrenceIDs=['Alpha','Beta'])
        self.assertTrue(w.affirmative_lead(pair,endpoints('Alpha uses Beta.')))
        self.assertFalse(w.affirmative_lead(pair,endpoints('Alpha does not use Beta.')))
        self.assertFalse(w.affirmative_lead(pair,endpoints('Alpha uses Gamma. Beta exists.')))
        same=endpoints('Alpha uses inputs.');same['Beta']['labels']=['Alpha']
        self.assertFalse(w.affirmative_lead(pair,same))

    def test_live_batch_identical_bodies_and_no_double_dispatch(self):
        body,value=fixture()
        response=dict(status='completed',usage=dict(input_tokens=10),output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])])
        class API:
            def request(self,method,path,data):
                self.live=json.loads(data);return w.live.encode(response)
            def upload(self,path):
                self.batch=json.loads(path.read_text())['body'];return dict(id='file')
            def create(self,file_id,metadata):return dict(id='batch')
            def retrieve(self,batch_id):return dict(status='completed',output_file_id='out')
            def content(self,file_id):return w.live.encode(dict(custom_id='W00002',response=dict(body=response)))+b'\n'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);api=API();w.live.save(root/'manifest.json',{})
            w.live.write(root/'requests.jsonl',b''.join(w.live.encode(dict(custom_id=u,body=body))+b'\n' for u in ('W00001','W00002')))
            with patch.object(w,'verify',return_value={}):
                w.operate(root,'live',['W00001'],api)
                with self.assertRaises(ValueError):w.operate(root,'submit',['W00001'],api)
                w.operate(root,'submit',api=api)
                self.assertEqual(api.live,api.batch)
                report=w.operate(root,'retrieve',api=api)
                self.assertEqual(report['missing'],[])
                self.assertEqual(report['results']['W00002']['usage'],{'input_tokens':10})

    def test_schema_rejects_approvals(self):
        body,value=fixture();w.Draft202012Validator.check_schema(body['text']['format']['schema'])
        value['approved']=True
        with self.assertRaises(Exception):w.validate(value,body)


if __name__=='__main__':unittest.main()
