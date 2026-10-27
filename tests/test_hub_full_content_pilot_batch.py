"""Focused socket-blocked tests of the isolated raw-only Hub Batch adapter."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import hub_full_content_pilot_batch as run
from test_full_corpus_gpt61_batch import FakeAPI


class PilotBatchTests(unittest.TestCase):
    """Use synthetic sealed requests and the existing simulated Batch provider."""

    def setUp(self):
        """Create an isolated eight-request queue without corpus or provider access."""
        sockets = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        sockets.start(); self.addCleanup(sockets.stop)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.root = self.repo/run.QUEUE
        (self.root/'queue').mkdir(parents=True)
        (self.root/'production').mkdir()
        (self.root/'production/execution.jsonl').touch()
        entries, lines = [], []
        for n in range(8):
            prepared = dict(request={'requestID':f'pilot-{n}'},
                semanticRequest={'requestSha256':str(n), 'request':{'schemaVersion':run.pilot.VERSION}},
                requestInputs={'private':'reader'}, binding={'private':'binding'},
                body=dict(model='gpt-6.1-sol', input=f'exact source {n}', reasoning={'effort':'medium'},
                          max_output_tokens=32768, store=False, text={}))
            wire = run.canonical(prepared)+b'\n'; digest = run.sha(wire)
            (self.root/'queue'/f'{digest}.json').write_bytes(wire)
            item, line = run.batch.input_line(prepared, 1, run.adapter.fingerprint)
            entries.append(dict(identity=run.adapter.fingerprint(prepared),bundleFile=f'{digest}.json',
                bundleSha256=digest,batchItem=item,cost={'costUSD':{'pooled':.1}}))
            lines.append(line)
        raw = b''.join(lines); (self.root/'batch-input.jsonl').write_bytes(raw)
        manifest = dict(version=run.pilot.VERSION, requests=entries,inputPins={},implementationPins={},
                        batchInputSha256=run.sha(raw),pricing=run.batch.PRICING,costUSD={'pooled':.8})
        wire = run.canonical(manifest)+b'\n'; (self.root/'queue-manifest.json').write_bytes(wire)
        pin = patch.object(run, 'QUEUE_SHA', run.sha(wire)); pin.start(); self.addCleanup(pin.stop)
        self.api = FakeAPI()
        silence = contextlib.redirect_stdout(io.StringIO()); silence.__enter__()
        self.addCleanup(silence.__exit__, None, None, None)

    def call(self, mode, capacity=None):
        """Invoke the actual wrapper against fixture directories and mocked transport."""
        return run.operate(mode, capacity, repo=self.repo, api=self.api)

    def test_offline_preflight_and_explicit_dispatch(self):
        """Preflight does not initialize execution or instantiate a provider client."""
        with patch.object(run.batch.batch_transport, 'BatchAPI', side_effect=AssertionError('NO_CLIENT')):
            self.assertTrue(self.call('preflight')['verified'])
        self.assertEqual((self.root/'production/execution.jsonl').read_bytes(),b'')
        self.assertFalse((self.root/'production/run-manifest.json').exists())
        self.assertEqual(self.api.creates,0)
        with self.assertRaisesRegex(ValueError,'SUPPLY_--queued-token-limit'):
            self.call('submit')

    def test_repeated_submit_collect_and_read_only_preflight(self):
        """Durable native journals prevent duplicate dispatch and collection."""
        self.call('submit',100)
        self.call('submit')
        self.assertEqual((self.api.creates,self.api.uploads,self.api.counts),(1,1,8))
        status = self.call('status')
        self.assertEqual(status['counts'],{'awaiting_collection':8})
        self.assertFalse(list((self.root/'production').glob('*output*')))
        result = self.call('collect')
        self.assertEqual(result['counts'],{'completed':8})
        journal = self.root/'production/execution.jsonl'
        before = journal.read_bytes()
        self.call('collect'); self.call('preflight'); self.call('submit')
        self.assertEqual(before,journal.read_bytes())
        self.assertEqual(self.api.creates,1)
        self.assertTrue(all(not r['kgAuthorization'] for r in result['requests']))
        self.assertGreater(result['accounting']['cumulativeUsagePricedUSD'],0)

    def test_manifest_bundle_and_batch_input_drift(self):
        """All immutable artifacts are checked before even provider reads."""
        for path in (self.root/'queue-manifest.json',next((self.root/'queue').glob('*.json')),
                     self.root/'batch-input.jsonl'):
            original = path.read_bytes(); path.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'DRIFT'):
                self.call('submit',100)
            path.write_bytes(original)
        self.assertEqual(self.api.creates,0)
        self.call('submit',100)
        path = self.root/'queue-manifest.json'; path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'QUEUE_MANIFEST_DRIFT'):
            self.call('collect')

    def test_uncertain_submission_and_upload_recovery(self):
        """Restart uses native remote reconciliation instead of repeating POSTs."""
        self.api.lose_upload = True
        with self.assertRaises(OSError): self.call('submit',100)
        self.api.lose_create = True
        with self.assertRaises(OSError): self.call('submit')
        self.call('submit'); self.call('submit')
        self.assertEqual((self.api.creates,self.api.uploads,self.api.counts),(1,1,8))
        self.assertEqual(self.call('collect')['counts'],{'completed':8})

    def test_partial_completion_preserved_and_never_resubmitted(self):
        """Missing rows STOP collection while available exact receipts remain durable."""
        self.call('submit',100); self.api.omit = True
        with self.assertRaisesRegex(ValueError,'MISSING_BATCH_RESULTS_STOP'):
            self.call('collect')
        result = self.call('preflight')
        self.assertEqual(result['counts'],{'completed':7,'missing':1})
        before = (self.root/'production/execution.jsonl').read_bytes()
        with self.assertRaisesRegex(ValueError,'MISSING_BATCH_RESULTS_STOP'):
            self.call('collect')
        self.assertEqual(before,(self.root/'production/execution.jsonl').read_bytes())
        self.call('submit'); self.assertEqual(self.api.creates,1)

    def test_duplicate_and_unknown_response_identity(self):
        """Validate all response IDs before storing any per-request receipts."""
        self.call('submit',100); self.api.duplicate = True
        with self.assertRaisesRegex(ValueError,'UNKNOWN_OR_DUPLICATE_CUSTOM_ID'):
            self.call('collect')
        self.assertEqual(self.call('preflight')['counts'],{'missing':8})

    def test_unknown_identity_and_download_tampering(self):
        """Foreign response IDs are rejected and preserved downloads cannot drift."""
        self.call('submit',100)
        original = self.api.content
        def foreign(fid):
            """Inject a foreign row into an authentic-shaped downloaded fixture."""
            raw = original(fid)
            if fid.startswith('output-'):
                rows = [json.loads(line) for line in raw.splitlines()]
                rows[0]['custom_id'] = 'foreign-request'
                return b''.join(run.canonical(row)+b'\n' for row in rows)
            return raw
        with patch.object(self.api,'content',side_effect=foreign):
            with self.assertRaisesRegex(ValueError,'UNKNOWN_OR_DUPLICATE_CUSTOM_ID'):
                self.call('collect')
        path = next((self.root/'production').glob('*output*.jsonl'))
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'RESULT_FILE_HASH_DRIFT'):
            self.call('preflight')
        with self.assertRaisesRegex(ValueError,'RESULT_FILE_HASH_DRIFT'):
            self.call('collect')

    def test_transport_categories_remain_scientifically_held(self):
        """Incomplete/failed/expired/completed never imply semantic acceptance."""
        parent,bundles=run.load_queue(self.repo); p=next(iter(bundles.values()))
        receipt=dict(providerResponse={'status':'completed','model':'gpt-6.1-sol','service_tier':'batch'},
            row={'response':{'status_code':200}},metadataError=None,cost={'estimatedUSD':.01})
        for status in ('completed','incomplete','failed'):
            changed=deepcopy(receipt);changed['providerResponse']['status']=status
            out=run.raw_outcome(p,changed,1)
            self.assertEqual(out['transportStatus'],status)
            self.assertFalse(out['retryEligible']);self.assertFalse(out['kgAuthorization'])
            self.assertEqual(out['evidenceDisposition'],'held')
        receipt['row']={'error':{'code':'batch_expired'}};receipt['providerResponse']=None
        self.assertEqual(run.raw_outcome(p,receipt,1)['transportStatus'],'expired')
        with self.assertRaisesRegex(ValueError,'RETRY_FORBIDDEN'):run.raw_outcome(p,receipt,2)


if __name__=='__main__':unittest.main()
