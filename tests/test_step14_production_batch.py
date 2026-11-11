"""Focused offline binding, packing, count projection and native journal tests."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from src.evaluation import step14_production_batch as x
from test_step14_queue_compatibility_pilot import body,recommendation

class ProductionTests(unittest.TestCase):
    def test_selection_and_stable_native_ids(self):
        p=dict(request={'requestID':'step14:U1'},body=body(),binding={'pairs':{'P1':'key'}})
        self.assertEqual(x.INSTRUCTIONS,x.c.variant({'instructions':x.c.p.PROMPT})['instructions'])
        from src.evaluation.step14_category_calibration import CLARIFICATION
        self.assertNotIn(CLARIFICATION,x.INSTRUCTIONS)
        self.assertEqual(x.b.input_line(p,1,x.fingerprint),x.b.input_line(p,1,x.fingerprint))
        old=x.b.input_line(p,1,x.fingerprint)[0];p['binding']['pairs']['P1']='different'
        self.assertNotEqual(old['custom_id'],x.b.input_line(p,1,x.fingerprint)[0]['custom_id'])

    def test_exact_twenty_million_boundary(self):
        a=b'a'*19_999_998+b'\n';b=b'\n'
        self.assertEqual([len(z) for z in x.packed([a,b,b])],[20_000_000,1])
        with self.assertRaisesRegex(ValueError,'OVERSIZED'):list(x.packed([b'a'*20_000_000+b'\n']))
        with patch.object(x.b,'MAX_REQUESTS',1):self.assertEqual(len(list(x.packed([b,b]))),2)

    def test_count_includes_instructions(self):
        request=body();request['instructions']=x.INSTRUCTIONS;request['reasoning']={'effort':'medium'}
        api=x.API('fixture-not-a-key')
        with patch.object(api,'request',return_value=b'{"object":"response.input_tokens","input_tokens":5}') as call:
            self.assertEqual(api.count(request)['input_tokens'],5)
            self.assertEqual(json.loads(call.call_args.args[2])['instructions'],x.INSTRUCTIONS)

    def test_pair_validation_and_no_automatic_retry(self):
        p={'body':body()};value=recommendation()
        def receipt(v):return {'providerResponse':{'status':'completed'},'rawModelOutputBase64':base64.b64encode(json.dumps(v).encode()).decode()}
        result=x.process(p,receipt(value),1)
        self.assertTrue(result['processable']);self.assertFalse(result['identityApproved'])
        value['assessments'][0]['evidenceIDs']=['foreign']
        result=x.process(p,receipt(value),1)
        self.assertFalse(result['processable']);self.assertFalse(result['retryEligible'])
        self.assertEqual(result['status'],'validation_failed')
        result=x.process(p,{'providerResponse':{'status':'incomplete'}},1)
        self.assertFalse(result['processable']);self.assertFalse(result['retryEligible'])

    def test_native_journal_duplicate_and_reservation(self):
        paired,native,pins=x.shared.infrastructure()
        p=dict(request={'requestID':'r'},body=body(),binding={})
        e=dict(identity=x.fingerprint(p),estimatedCostUSD=1)
        mf=dict(generatorPins=pins,requests=[e],queuedTokenLimit=15000000000)
        def check(p,e):x.require(x.fingerprint(p)==e['identity'],'DRIFT')
        J=x.batch_journal(native,check,x.fingerprint,lambda *a:None)
        with tempfile.TemporaryDirectory() as tmp:
            data=x.encode(mf)+b'\n'
            with J(Path(tmp)/'execution.jsonl',data,x.sha(data)) as log:
                log.append('prepared','r',p)
                log.append('token_count','r',dict(provider={'input_tokens':5},bodySha256=x.fingerprint(p)['bodySha256']))
                jid=x.b.make_job(log,None,None,native,x.fingerprint,15000000000,50000)
                self.assertEqual(log.reserved_tokens(),5)
                self.assertIsNone(x.b.make_job(log,None,None,native,x.fingerprint,15000000000,50000))
                log.append('upload_intent',jid,dict(filename=log.job(jid,'plan')['filename'],sha256=log.job(jid,'plan')['sha256']))
                self.assertEqual(log.reserved_tokens(),5)
                api=Mock();api.listing.return_value=[]
                with self.assertRaisesRegex(ValueError,'UNCERTAIN_UPLOAD_STOP'):x.b.submit(log,jid,api)
                api.upload.assert_not_called();api.create.assert_not_called()
            with J(Path(tmp)/'execution.jsonl',data,x.sha(data)) as log:self.assertEqual(log.reserved_tokens(),5)

if __name__=='__main__':unittest.main()
