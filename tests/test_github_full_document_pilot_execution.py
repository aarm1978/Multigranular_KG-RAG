"""Offline mocked transport and recovery tests for the pinned GitHub pilot."""
import base64
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import github_full_document_pilot_execution as run
from test_full_corpus_gpt61_batch import FakeAPI


class ExecutionTests(unittest.TestCase):
    """Test new dispatch behavior only, with sockets blocked throughout."""
    def setUp(self):
        """Create eight synthetic immutable bundles and separate execution directories."""
        guard=patch.object(socket,'socket',side_effect=AssertionError('NO_NETWORK'));guard.start();self.addCleanup(guard.stop)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.repo=Path(temp.name)
        self.root=self.repo/run.pilot.BASE;(self.root/'queue').mkdir(parents=True)
        self.bodies=[];entries=[];lines=[]
        for n in range(8):
            p=dict(request={'requestID':f'github-pilot-{n}'},semanticRequest={'requestSha256':str(n),
                'request':{'schemaVersion':run.pilot.VERSION}},requestInputs={},binding={},
                body=dict(model='gpt-6.1-sol',input=f'complete source {n}',reasoning={'effort':'medium'},
                          max_output_tokens=32768,store=False,text={'format':{'strict':True}}))
            wire=run.canonical(p)+b'\n';digest=run.sha(wire);self.bodies.append(p['body'])
            (self.root/'queue'/f'{digest}.json').write_bytes(wire)
            item,line=run.batch.input_line(p,1,run.hub.adapter.fingerprint);lines.append(line)
            entries.append(dict(identity=run.hub.adapter.fingerprint(p),bundleFile=f'{digest}.json',
                bundleSha256=digest,batchItem=item,cost={'costUSD':{'pooled':.1}}))
        raw=b''.join(lines);(self.root/'batch-input.jsonl').write_bytes(raw)
        manifest=dict(version=run.pilot.VERSION,requests=entries,inputPins={},implementationPins={},
                      batchInputSha256=run.sha(raw),pricing=run.batch.PRICING)
        wire=run.canonical(manifest)+b'\n';(self.root/'queue-manifest.json').write_bytes(wire)
        pin=patch.object(run,'QUEUE_SHA',run.sha(wire));pin.start();self.addCleanup(pin.stop)
        self.calls=[]
        silence=contextlib.redirect_stdout(io.StringIO());silence.__enter__();self.addCleanup(silence.__exit__,None,None,None)

    def response(self,body):
        """Provide raw whitespace-preserving JSON with exact output/error/usage fields."""
        return json.dumps(dict(id='response-'+body['input'],model=body['model'],service_tier='default',
            status='completed',usage={'input_tokens':10,'output_tokens':2},error=None,
            output=[{'type':'message','content':[{'type':'output_text','text':'unrepaired model output'}]}]),indent=2).encode()

    def call(self,key,body,save):
        """Record the exact body and deliver synthetic raw bytes without a provider."""
        self.calls.append(deepcopy(body))
        save(dict(kind='response',bytesBase64=base64.b64encode(self.response(body)).decode()))

    def operate(self,mode='submit',transport='live',**kwargs):
        """Use the real controller with only its network call mocked."""
        return run.operate(mode,transport,repo=self.repo,live_call=self.call,**kwargs)

    def test_preflight_is_offline_and_creates_no_execution_records(self):
        """Both preflights verify immutable requests without loading credentials."""
        with patch.object(run.provider,'load_openai_api_key',side_effect=AssertionError('NO_KEY_NEEDED')):
            for transport in ('batch','live'):self.assertTrue(self.operate('preflight',transport)['verified'])
        self.assertFalse((self.root/'execution').exists());self.assertEqual(self.calls,[])

    def test_live_exact_bodies_bytes_usage_and_restart_skips(self):
        """Completed live requests are never sent twice; raw model output is unchanged."""
        result=self.operate();self.assertEqual(self.calls,self.bodies)
        self.assertGreater(result['usagePricedUSD'],0)
        journal=self.root/'execution/live/execution.jsonl';before=journal.read_bytes()
        self.operate();self.operate('preflight');self.operate('status')
        self.assertEqual(self.calls,self.bodies);self.assertEqual(journal.read_bytes(),before)
        events=[json.loads(l)['record'] for l in before.splitlines()]
        raws=[r['payload'] for r in events if r['event']=='raw']
        self.assertEqual(base64.b64decode(raws[0]['bytesBase64']),self.response(self.bodies[0]))
        self.assertEqual([e['event'] for e in events[:4]],['header','intent','raw','result'])

    def test_uncertain_intent_and_transport_error_never_retry(self):
        """Crashes and timeouts cannot become automatic resubmissions."""
        def crash(*args):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            run.operate('submit','live',repo=self.repo,live_call=crash)
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS_SUBMISSION_STOP'):self.operate()
        self.assertEqual(self.calls,[])

    def test_response_capture_recovered_without_resubmit(self):
        """A crash after saving exact response bytes resumes local accounting only."""
        def crash(key,body,save):
            self.call(key,body,save);raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):run.operate('submit','live',repo=self.repo,live_call=crash)
        self.operate();self.assertEqual(self.calls,self.bodies)

    def test_incomplete_and_http_errors_are_durable_holds(self):
        """HTTP failures and incomplete responses retain their evidence and stop."""
        def http(key,body,save):
            raise run.provider.OpenAIHTTPError({'httpStatus':429,'responseBodyBase64':base64.b64encode(b'original error').decode()})
        with self.assertRaisesRegex(ValueError,'LIVE_TERMINAL_HOLD'):
            run.operate('submit','live',repo=self.repo,live_call=http)
        with self.assertRaisesRegex(ValueError,'LIVE_TERMINAL_HOLD'):self.operate()
        self.assertEqual(self.calls,[])
        self.assertIn(b'http_error',(self.root/'execution/live/execution.jsonl').read_bytes())
        parent,bundles=run.bound_helpers()['load_queue'](self.repo);p=next(iter(bundles.values()))
        paired,_,_=run.hub.adapter.infrastructure()
        body=json.loads(self.response(p['body']));body['status']='incomplete'
        out=run.live_result(dict(kind='response',bytesBase64=base64.b64encode(json.dumps(body).encode()).decode()),p,paired)
        self.assertEqual(out['status'],'incomplete');self.assertFalse(out['kgAuthorization'])

    def test_timeout_and_duplicate_response_identity_stop(self):
        """A transport exception remains ambiguous; duplicate response IDs fail closed."""
        def timeout(*args):raise TimeoutError('synthetic timeout')
        with self.assertRaisesRegex(ValueError,'LIVE_TERMINAL_HOLD'):
            run.operate('submit','live',repo=self.repo,live_call=timeout)
        with self.assertRaisesRegex(ValueError,'LIVE_TERMINAL_HOLD'):self.operate()
        self.assertEqual(self.calls,[])
        status=self.operate('status')
        self.assertEqual(status['requests'][0]['status'],'ambiguous_submission')

    def test_duplicate_response_ids_preserve_raw_and_stop(self):
        """Returned response IDs cannot be silently associated with two requests."""
        def duplicate(key,body,save):
            raw=json.loads(self.response(body));raw['id']='same-response-id'
            save(dict(kind='response',bytesBase64=base64.b64encode(json.dumps(raw).encode()).decode()))
        with self.assertRaisesRegex(ValueError,'DUPLICATE_RESPONSE_ID'):
            run.operate('submit','live',repo=self.repo,live_call=duplicate)
        events=[json.loads(line)['record'] for line in (self.root/'execution/live/execution.jsonl').read_bytes().splitlines()]
        self.assertEqual(sum(e['event']=='raw' for e in events),2)
        self.assertEqual(sum(e['event']=='result' for e in events),1)

    def test_manifest_drift_fails_before_either_transport(self):
        """The exact pinned manifest is checked before all dispatch paths."""
        path=self.root/'queue-manifest.json';path.write_bytes(path.read_bytes()+b' ')
        for transport in ('batch','live'):
            with self.assertRaisesRegex(ValueError,'QUEUE_MANIFEST_DRIFT'):self.operate(transport=transport)
        self.assertEqual(self.calls,[])

    def test_batch_native_recovery_and_transport_isolation(self):
        """Lost Batch acknowledgement uses existing recovery without duplicate POST."""
        api=FakeAPI();api.lose_create=True
        with self.assertRaises(OSError):self.operate(transport='batch',capacity=100,api=api)
        self.operate(transport='batch',api=api);self.operate(transport='batch',api=api)
        self.assertEqual(api.creates,1)
        self.operate('collect','batch',api=api)
        self.assertFalse((self.root/'execution/live').exists())
        before=(self.root/'execution/batch/execution.jsonl').read_bytes()
        self.operate()
        self.assertEqual((self.root/'execution/batch/execution.jsonl').read_bytes(),before)
        self.assertEqual(self.calls,self.bodies)

    def test_synchronous_native_client_exact_wire_capture(self):
        """The existing client constructs the request; capture preserves exact HTTP bytes."""
        raw=self.response(self.bodies[0]);saved=[]
        class Response(io.BytesIO):
            """Mock the HTTP response context manager only."""
        def opened(request,timeout):
            self.assertEqual(json.loads(request.data),self.bodies[0]);return Response(raw)
        original=run.provider.urlopen
        with patch.object(run.provider,'urlopen',side_effect=opened):
            run.synchronous_call('synthetic-key',self.bodies[0],saved.append)
        self.assertIs(run.provider.urlopen,original)
        self.assertEqual(base64.b64decode(saved[0]['bytesBase64']),raw)


if __name__=='__main__':unittest.main()
