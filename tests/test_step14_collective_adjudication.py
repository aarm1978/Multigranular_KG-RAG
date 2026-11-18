"""Focused partition, binding, blocking and transport regressions; no provider calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_collective_adjudication as c


def body():
    """Return two source-bound synthetic occurrences."""
    payload=dict(occurrences=[dict(occurrenceID=f'E{i}',names=['Model'],ontologyClass='ComputationalModel',versions={},evidence=[dict(evidenceID=f'E{i}Q1',text='Model source evidence')]) for i in (1,2)],allowedPredicates=[])
    return dict(input=json.dumps(payload),text=dict(format=dict(schema=c.schema(payload))))


def assessment(ids,category='strict_identity'):
    """Construct an explicit partition assignment."""
    return dict(category=category,occurrenceIDs=ids,broaderReferent=None,granularity='named model',supportingEvidenceIDs=[o+'Q1' for o in ids],contradictoryEvidenceIDs=[],rationale='Independent source support',uncertainty='prediction')


def answer(rows):
    """Wrap partition assignments in the reused relation envelope."""
    return dict(assessments=rows,typedRelations=[],ontologyGaps=[])


class PartitionTests(unittest.TestCase):
    def test_complete_identity_and_singletons(self):
        for rows in ([assessment(['E1','E2'])],[assessment(['E1'],'distinct'),assessment(['E2'],'abstention')]):
            self.assertFalse(c.validate(answer(rows),body())['semanticValidation'])

    def test_omission_overlap_invention_and_misbinding(self):
        for rows in ([assessment(['E1'],'distinct')],[assessment(['E1','E2']),assessment(['E2'],'abstention')],[assessment(['E1','E3'])]):
            with self.assertRaises(Exception):c.validate(answer(rows),body())
        a=assessment(['E1','E2']);a['supportingEvidenceIDs']=['E1Q1']
        with self.assertRaises(ValueError):c.validate(answer([a]),body())

    def test_conflicts_and_granularity(self):
        b=body();p=json.loads(b['input']);p['occurrences'][0]['granularity']='family';p['occurrences'][1]['granularity']='version';b['input']=json.dumps(p)
        with self.assertRaises(ValueError):c.validate(answer([assessment(['E1','E2'])]),b)
        a=assessment(['E1','E2']);a['contradictoryEvidenceIDs']=['E2Q1']
        with self.assertRaises(ValueError):c.validate(answer([a]),body())

    def test_boundaries_deterministic_no_transitive_entity(self):
        scopes=[dict(candidateID='a',occurrenceIDs=['a','b']),dict(candidateID='b',occurrenceIDs=['b','c'])]
        units,bounds=c.windows(scopes,2)
        self.assertEqual(units,[['a','b'],['c']]);self.assertEqual(bounds[1]['windows'],[0,1])
        self.assertEqual(c.windows(scopes,2),c.windows(scopes,2))

    def test_alias_reconstruction(self):
        result=c.w.resolve_output(answer([assessment(['E1','E2'])]),{'E1':'original-a','E2':'original-b'})
        self.assertEqual(result['assessments'][0]['occurrenceIDs'],['original-a','original-b'])
        self.assertEqual(result['assessments'][0]['supportingEvidenceIDs'],['E1Q1','E2Q1'])

    def test_saved_invalid_output_not_repaired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'execution').mkdir()
            c.w.live.save(root/'alias-bindings.json',{'C1':{'E1':'a','E2':'b'}})
            response=dict(status='completed',usage={'total_tokens':4})
            with patch.object(c.w,'validate',c.validate),patch.object(c.w.live.provider,'extract_model_output',return_value=json.dumps(answer([assessment(['E1'],'distinct')]))):
                report=c.w.process(root,'C1',body(),response)
            self.assertEqual(report['status'],'invalid_or_incomplete')
            self.assertEqual(c.w.live.load(root/'execution/C1.response.json'),response)
            self.assertFalse((root/'execution/C1.hypotheses.json').exists())

    def test_preparation_shards_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);source=base/'decision-stage/v2';prepared=base/'previous';spec=base/'spec.yaml'
            spec.write_text('ontology: {version: "0.1.8"}\nclasses: [{name: ComputationalModel, iri: "ex:Model"}]\nrelations: []\n')
            def artifact(folder,files):
                folder.mkdir(parents=True,exist_ok=True)
                for name,rows in files.items():
                    (folder/name).write_bytes(b''.join(c.w.live.encode(x)+b'\n' for x in rows))
                c.w.live.save(folder/'manifest.json',dict(outputHashes={name:c.w.r.identity.sha(folder/name) for name in files}))
            endpoints=[];members=[];groups=[]
            for i in range(24):
                oid=f'o{i:02}';art=f'source{i//2}'
                endpoints.append(dict(occurrenceID=oid,labels=['Model'],ontologyClass='ComputationalModel',sourceFamilies=['papers'],versions={},granularity='unspecified_requires_context_review',selectedEvidence=[dict(literalExcerpt='Exact source span')],sourceArtifacts=[art]))
                members.append(dict(occurrenceID=oid,sourceArtifacts=[art]))
            for i in range(12):groups.append(dict(simulationID=f'g{i}',state='held_undetermined',holdReasons=['overlapping_eligible_complete_scopes_no_union'],occurrenceIDs=[f'o{i*2:02}',f'o{i*2+1:02}']))
            artifact(source,{'decision-ledger.jsonl':groups,'historical-approvals.jsonl':[],'pair-inventory.jsonl':[],'typed-relation-proposals.jsonl':[]})
            artifact(base/'unified-review-queue/v1',{'endpoint-provenance.jsonl':endpoints})
            artifact(base/'referent-groups/v1',{'members.jsonl':members})
            template=body();template.update(model='saved-model',reasoning={'effort':'medium'})
            artifact(prepared,{'requests.jsonl':[dict(body=template)]})
            root=base/'collective-adjudication/v1'
            with patch.object(c.w,'BASE',base),patch.object(c.w,'ROOT',prepared),patch.object(c.w,'SPEC',spec):
                summary=c.prepare(root,source);c.verify(root)
                self.assertEqual(summary['requests'],12);self.assertEqual(summary['packages'],{'pilot':10,'batch-001':2})
                rows=list(c.w.r.rows(root/'requests.jsonl'))
                self.assertTrue(all(r['body']['model']=='saved-model' for r in rows))
                payload=json.loads(rows[0]['body']['input'])
                self.assertEqual(payload['occurrences'][0]['evidence'][0]['text'],'Exact source span')
                self.assertEqual(payload['occurrences'][0]['sourceArtifactRef'],payload['occurrences'][1]['sourceArtifactRef'])
                self.assertNotIn('holdReasons',rows[0]['body']['input'])
                shard=root/'batch-001'
                with patch.object(c.w,'verify',c.verify),patch.object(c.w,'validate',c.validate):
                    class API:
                        def request(self,*args):
                            return c.w.live.encode(dict(status='incomplete',usage={}))
                    ids=[r['custom_id'] for r in c.w.r.rows(shard/'requests.jsonl')]
                    c.w.operate(shard,'live',ids,API())
                    with self.assertRaises(ValueError):c.w.operate(shard,'live',ids,API())
                    class Batch:
                        def upload(self,path):
                            self.requests=list(c.w.r.rows(path));return {'id':'file-local'}
                        def create(self,*args):return {'id':'batch-local'}
                        def retrieve(self,*args):return {'status':'completed','output_file_id':'results'}
                        def content(self,*args):
                            return b''.join(c.w.live.encode(dict(custom_id=r['custom_id'],response=dict(body=dict(status='completed',usage={'total_tokens':10}))))+b'\n' for r in self.requests)
                    api=Batch();folder=root/'pilot'
                    c.w.operate(folder,'submit',api=api)
                    with patch.object(c.w.live.provider,'extract_model_output',return_value=json.dumps(answer([assessment(['E1','E2'])]))):
                        result=c.w.operate(folder,'retrieve',api=api)
                    self.assertEqual(result['missing'],[])
                    for uid,report in result['results'].items():
                        self.assertEqual(report['status'],'validated_hypotheses_only')
                        resolved=c.w.live.load(folder/'execution'/f'{uid}.resolved-hypotheses.json')
                        self.assertTrue(all(o.startswith('o') for o in resolved['assessments'][0]['occurrenceIDs']))



if __name__=='__main__':unittest.main()
