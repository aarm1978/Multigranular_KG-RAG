"""Offline exact-body recovery, once-only concurrency and scientific selection tests."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
from src.evaluation import step14_live_recovery as x
from test_step14_queue_compatibility_pilot import body,recommendation

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        """Block networking for every fixture, including injected execution."""
        for method in ('connect','connect_ex'):
            mock=patch.object(socket.socket,method,side_effect=AssertionError('NO_NETWORK'));mock.start();self.addCleanup(mock.stop)

    def test_roster_exact_counts_and_fail_closed(self):
        entries={str(i):dict(identity={'requestID':str(i)},pairs=4 if i<7 else 3) for i in range(14549)}
        outcomes={rid:dict(status='validation_failed' if int(rid)<21 else 'validated_recommendation_only',processable=int(rid)>=21) for rid in entries}
        self.assertEqual(sum(e['pairs'] for e in x.roster(entries,outcomes)),70)
        outcomes['0']['status']='provider_incomplete_or_failed'
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_OUTCOME'):x.roster(entries,outcomes)
        outcomes.pop('0')
        with self.assertRaisesRegex(ValueError,'OUTCOME_COVERAGE'):x.roster(entries,outcomes)

    def test_exact_body_reuse_completed_and_uncertain_no_redispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=body();before=deepcopy(request);path=root/'request.json';x.c.live.save(path,request)
            case=dict(unitID='U1',requestID='r',requestPath=str(path),pairs=2)
            calls=[]
            def call(actual):
                calls.append(actual);raise TimeoutError('no credentials here')
            with patch.object(x,'verify',return_value={'cases':[case]}),patch.object(x,'status',return_value={}):
                x.execute(root,4,call=call);x.execute(root,4,call=call)
                self.assertEqual(calls,[before]);self.assertEqual(request,before)
                self.assertEqual(x.c.live.load(root/'attempts/U1/outcome.json')['status'],'remote_outcome_unknown')
                with self.assertRaisesRegex(ValueError,'WORKER_LIMIT'):x.execute(root,5,call=call)
                with self.assertRaisesRegex(ValueError,'LIVE_FLAG'):x.execute(root,1)

    def test_completed_attempt_validation_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'attempt';request=body();value=recommendation()
            response=dict(id='resp-fixture',model=request['model'],status='completed',usage={'input_tokens':10,'output_tokens':20},
                output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])])
            calls=[]
            def call(actual):calls.append(actual);return response
            first=x.c.p.attempt(folder,request,call);second=x.c.p.attempt(folder,request,call)
            self.assertEqual(first,second);self.assertEqual(len(calls),1)
            self.assertEqual(x.c.result(folder,request)[1],value)
            self.assertEqual(x.c.live.load(folder/'response.json'),response)

    def test_consolidation_binding_duplicates_and_invalid_evidence(self):
        request=body();p=dict(body=request,binding={'pairs':{'P1':'global1','P2':'global2'}});seen=set();value=recommendation()
        row=x.selected_row('r',p,value,{'origin':'batch'},seen)
        self.assertFalse(row['identityApproved']);self.assertEqual(seen,{'global1','global2'})
        with self.assertRaisesRegex(ValueError,'DUPLICATE_ASSESSED_PAIR'):x.selected_row('r2',p,value,{},seen)
        bad=deepcopy(value);bad['assessments'][0]['evidenceIDs']=['foreign']
        with self.assertRaisesRegex(ValueError,'FOREIGN_OR_UNKNOWN'):x.selected_row('r',p,bad,{},set())
        p['binding']['pairs']['P2']='global1'
        with self.assertRaisesRegex(ValueError,'DUPLICATE_ASSESSED_PAIR'):x.selected_row('r',p,value,{},set())

if __name__=='__main__':unittest.main()
