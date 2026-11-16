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
    def test_refresh_preserves_evidence_and_adds_only_applicable_predicates(self):
        """Version/variant options follow actual types, without changing scientific inputs."""
        spec=w.yaml.safe_load(w.SPEC.read_text())
        for cls,expected in [('ProcessBasedModel','D-27'),('Algorithm','D-28'),('Workflow',None)]:
            body,_=fixture();payload=json.loads(body['input'])
            for e in payload['occurrences']:e['ontologyClass']=cls
            payload['allowedPredicates']=[];body['input']=json.dumps(payload)
            before=json.dumps(body)
            new=w.refresh_body(body,spec);updated=json.loads(new['input'])
            self.assertEqual(updated['occurrences'],payload['occurrences'])
            self.assertEqual(json.dumps(body),before)
            ids={x['id'] for x in updated['allowedPredicates']}
            if expected:self.assertIn(expected,ids)
            else:self.assertEqual(ids,set())
            self.assertIn('abstention',new['text']['format']['schema']['properties']['assessments']['items']['properties']['category']['enum'])
            self.assertNotIn('D-16',ids)

    def test_cleanup_and_resolution_all_output_sections(self):
        """Aliases round-trip all typed endpoint fields without altering evidence or granularity output."""
        body,value=fixture();payload=json.loads(body['input'])
        for e in payload['occurrences']:e['granularity']='unspecified_requires_context_review'
        for rel in payload['allowedPredicates']:rel['signatureID']=rel['id']
        body['input']=json.dumps(payload)
        new,bindings=w.clean_body(body);clean=json.loads(new['input'])
        self.assertEqual(bindings,{'E1':'model','E2':'repo'})
        self.assertNotIn('versions',clean['occurrences'][0])
        self.assertNotIn('granularity',clean['occurrences'][0])
        self.assertNotIn('id',clean['allowedPredicates'][0])
        self.assertEqual(clean['occurrences'][0]['evidence'],payload['occurrences'][0]['evidence'])
        value['ontologyGaps']=[dict(occurrenceIDs=['model','repo'],proposedMeaning='A supported but unrepresented distinction',evidenceIDs=['E1Q1','E2Q1'],uncertainty='Hypothesis')]
        aliased=w.resolve_output(value,{v:k for k,v in bindings.items()})
        w.validate(aliased,new)
        self.assertEqual(w.resolve_output(aliased,bindings),value)
        with self.assertRaises(KeyError):w.resolve_output(aliased,{'E1':'model'})

    def test_source_artifact_aliases_preserve_semantic_payload(self):
        """Shared artifacts get shared local aliases, distinct artifacts never collapse."""
        body,_=fixture();body,aliases=w.clean_body(body)
        def provenance(a,b):
            return {o:dict(endpoint=dict(sourceArtifacts=[v]),member=dict(sourceArtifacts=[v])) for o,v in [('model',a),('repo',b)]}
        for a,b,expected in [('artifact-a','artifact-a',['S1','S1']),('artifact-a','artifact-b',['S1','S2'])]:
            updated,bindings=w.source_context_body(body,aliases,provenance(a,b))
            old=json.loads(body['input']);new=json.loads(updated['input'])
            self.assertEqual([e['sourceArtifactRef'] for e in new['occurrences']],expected)
            for e in new['occurrences']:e.pop('sourceArtifactRef')
            self.assertEqual(old,new)
            self.assertEqual(body['text'],updated['text'])
            self.assertNotIn('artifact-a',updated['input'])
            self.assertEqual(bindings['S1'],a)
        bad=provenance('a','b');bad['model']['endpoint']['sourceArtifacts']=['a','c']
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):w.source_context_body(body,aliases,bad)
        bad=provenance('a','b');bad['model']['member']['sourceArtifacts']=['other']
        with self.assertRaisesRegex(ValueError,'DISAGREEMENT'):w.source_context_body(body,aliases,bad)

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
        value['ontologyGaps']=[dict(occurrenceIDs=['model','repo'],proposedMeaning='Local hypothesis',evidenceIDs=['E1Q1','E2Q1'],uncertainty='Unreviewed')]
        body,bindings=w.clean_body(body)
        body,_=w.source_context_body(body,bindings,{o:dict(endpoint=dict(sourceArtifacts=['source']),member=dict(sourceArtifacts=['source'])) for o in bindings.values()})
        value=w.resolve_output(value,{v:k for k,v in bindings.items()})
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
            w.live.save(root/'alias-bindings.json',{u:bindings for u in ('W00001','W00002')})
            w.live.write(root/'requests.jsonl',b''.join(w.live.encode(dict(custom_id=u,body=body))+b'\n' for u in ('W00001','W00002')))
            with patch.object(w,'verify',return_value={}):
                w.operate(root,'live',['W00001'],api)
                with self.assertRaises(ValueError):w.operate(root,'submit',['W00001'],api)
                w.operate(root,'submit',api=api)
                self.assertEqual(api.live,api.batch)
                report=w.operate(root,'retrieve',api=api)
                self.assertEqual(report['missing'],[])
                for uid in ('W00001','W00002'):
                    resolved=w.live.load(root/'execution'/f'{uid}.resolved-hypotheses.json')
                    self.assertEqual(resolved,w.resolve_output(value,bindings))
                self.assertEqual(report['results']['W00002']['usage'],{'input_tokens':10})

    def test_schema_rejects_approvals(self):
        body,value=fixture();w.Draft202012Validator.check_schema(body['text']['format']['schema'])
        value['approved']=True
        with self.assertRaises(Exception):w.validate(value,body)


if __name__=='__main__':unittest.main()
