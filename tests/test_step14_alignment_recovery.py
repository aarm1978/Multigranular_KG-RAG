"""Offline once-only recovery and full-coverage consolidation regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_alignment_recovery as r
from test_step14_alignment_workflow import fixture


def setup(root):
    """Prepare a small aliased scientific response for unchanged workflow validation."""
    body,value=fixture();body,bindings=r.w.clean_body(body)
    value=r.w.resolve_output(value,{v:k for k,v in bindings.items()})
    r.w.live.save(root/'alias-bindings.json',{'U1':bindings,'U2':bindings})
    response=dict(status='completed',usage=dict(input_tokens=10),output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])])
    return body,response,bindings


class RecoveryTests(unittest.TestCase):
    def test_exact_roster_and_coverage(self):
        reports={'a':{'status':r.VALID},'b':{'status':r.INVALID}}
        self.assertEqual(r.select({'a':{},'b':{}},reports,2,1),['b'])
        with self.assertRaises(ValueError):r.select({'a':{}},reports,2,1)
        with self.assertRaises(ValueError):r.select({'a':{},'b':{}},reports,2,2)

    def test_body_immutability_reconstruction_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body,response,bindings=setup(root);before=r.w.live.encode(body)
            class API:
                calls=0
                def request(self,method,path,data):
                    self.calls+=1
                    assert data==before
                    return r.w.live.encode(response)
            api=API()
            self.assertEqual(r.attempt(root,'U1',body,api),r.VALID)
            self.assertEqual(r.attempt(root,'U1',body,api),r.VALID)
            self.assertEqual(api.calls,1);self.assertEqual(r.w.live.encode(body),before)
            resolved=r.w.live.load(root/'execution/U1.resolved-hypotheses.json')
            self.assertEqual(resolved['typedRelations'][0]['subject'],'model')
            # An interrupted finalization resumes from the durable response without a send.
            r.w.pilot.claim(root,'U2','isolated_live_recovery')
            r.w.live.write(root/'execution/U2.raw-response.json',r.w.live.encode(response))
            self.assertEqual(r.attempt(root,'U2',body,api),r.VALID);self.assertEqual(api.calls,1)

    def test_changed_recovery_body_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body,_,_=setup(root)
            path=root/'requests/U1.json';r.w.live.save(path,body)
            r.w.live.save(root/'manifest.json',dict(inputHashes={},outputHashes={},roster=['U1'],bodyHashes={'U1':r.w.live.token(body)}))
            r.verify(root)
            changed=dict(body,instructions='changed prompt');path.write_bytes(r.w.live.encode(changed))
            with self.assertRaisesRegex(ValueError,'BODY_DRIFT'):r.verify(root)

    def test_uncertain_send_is_never_repeated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body,_,_=setup(root)
            class API:
                calls=0
                def request(self,*args):self.calls+=1;raise TimeoutError()
            api=API()
            self.assertEqual(r.attempt(root,'U1',body,api),'uncertain_no_resubmission')
            self.assertEqual(r.attempt(root,'U1',body,api),'uncertain_no_resubmission')
            self.assertEqual(api.calls,1)

    def test_invalid_evidence_is_not_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);body,response,_=setup(root)
            value=json.loads(response['output'][0]['content'][0]['text']);value['typedRelations'][0]['evidenceIDs']=['invented']
            response['output'][0]['content'][0]['text']=json.dumps(value)
            class API:
                def request(self,*args):return r.w.live.encode(response)
            self.assertEqual(r.attempt(root,'U1',body,API()),r.INVALID)
            self.assertFalse((root/'execution/U1.hypotheses.json').exists())

    def test_consolidation_preserves_originals_and_all_units(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'recovery';root.mkdir();source=Path(d)/'source';source.mkdir()
            body,response,bindings=setup(root);r.w.live.save(source/'alias-bindings.json',{'U1':bindings,'U2':bindings})
            r.w.live.save(root/'manifest.json',{})
            r.w.live.write(source/'requests.jsonl',b''.join(r.w.live.encode(dict(custom_id=u,body=body))+b'\n' for u in ('U1','U2')))
            r.w.process(source,'U1',body,response)
            r.w.process(source,'U2',body,{'status':'incomplete'})
            originals={u:dict(status=status,artifacts={s:str(source/'execution'/f'{u}.{s}') for s in
                (('response.json','validation.json','hypotheses.json','resolved-hypotheses.json') if status==r.VALID else ('response.json','validation.json'))}) for u,status in [('U1',r.VALID),('U2',r.INVALID)]}
            m=dict(source=str(source),roster=['U2'],originals=originals)
            with patch.object(r,'verify',return_value=m):
                before=r.consolidate(root,root/'before');self.assertEqual(before['counts']['unresolved'],1)
                class API:
                    def request(self,*args):return r.w.live.encode(response)
                r.attempt(root,'U2',body,API())
                after=r.consolidate(root,root/'after');self.assertEqual(after['total'],2)
                self.assertEqual(after['counts']['valid'],2);self.assertEqual(after['counts']['recovery'],1)
                self.assertEqual(r.w.live.load(source/'execution/U2.validation.json')['status'],r.INVALID)


if __name__=='__main__':unittest.main()
