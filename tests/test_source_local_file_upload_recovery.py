"""Focused offline file-only recovery tests; no live provider or Batch operations."""
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import source_local_file_upload_recovery as r


class Files:
    """Simulate only file listing, upload and exact-content retrieval."""
    def __init__(self, test):
        """Keep synthetic source and immutable recovery paths for assertions."""
        self.test = test; self.rows = []; self.posts = 0; self.fail = False; self.bad = False

    def listing(self, resource):
        """Return the fake fully paginated listing."""
        assert resource == 'files'
        return self.rows

    def content(self, file_id):
        """Supply exact content or a deliberate mismatch."""
        return b'wrong' if self.bad else self.test.data

    def upload(self, path):
        """Require an already durable intent before simulating the single POST."""
        assert json.loads((self.test.sidecar / 'intent.json').read_bytes())['attempts'] == 1
        self.posts += 1
        if self.fail: raise TimeoutError('uncertain')
        return self.test.row


class FileRecoveryTests(unittest.TestCase):
    """Check one-attempt semantics, exact binding and Files-only transport restrictions."""
    def setUp(self):
        """Block sockets and create a tiny synthetic sealed file."""
        for name in ('connect', 'connect_ex'):
            blocker = patch.object(socket.socket, name, side_effect=AssertionError('NO_NETWORK'))
            blocker.start(); self.addCleanup(blocker.stop)
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.path = self.root / 'sealed.jsonl'
        self.data = b'{"test":"exact"}\n'; self.path.write_bytes(self.data)
        self.binding = dict(filename=self.path.name, bytes=len(self.data), sha256=r.digest(self.data), timeoutSeconds=600)
        self.row = dict(id='file-exact', filename=self.path.name, bytes=len(self.data), purpose='batch')
        self.sidecar = self.root / 'sidecars/job'; self.api = Files(self)

    def run_recovery(self, allowed=True):
        """Invoke recovery against synthetic Files responses only."""
        return r.recover(self.path, self.binding, self.sidecar, self.api, allow_one_upload=allowed)

    def test_one_explicit_upload_and_later_reuse(self):
        """Zero matches require explicit permission; a later match reuses verified bytes."""
        with self.assertRaisesRegex(ValueError, 'explicit --allow-one-upload'):
            self.run_recovery(False)
        self.assertEqual(self.api.posts, 0)
        result = self.run_recovery()
        self.assertEqual(result['status'], 'verified_upload'); self.assertFalse(result['batchSubmitted'])
        self.assertEqual(self.api.posts, 1)
        self.assertEqual(json.loads((self.sidecar/'outcome.json').read_bytes())['status'], 'response_received')
        self.api.rows = [self.row]
        self.assertEqual(self.run_recovery()['status'], 'verified_reuse')
        self.assertEqual(self.api.posts, 1)
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_uncertain_post_is_never_repeated_even_on_explicit_rerun(self):
        """Persistent intent blocks another POST; a later exact match can be reconciled."""
        self.api.fail = True
        with self.assertRaisesRegex(ValueError, 'UPLOAD_OUTCOME_UNCERTAIN'): self.run_recovery()
        self.assertEqual(json.loads((self.sidecar/'outcome.json').read_bytes())['status'], 'uncertain')
        self.api.fail = False
        with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'): self.run_recovery()
        self.assertEqual(self.api.posts, 1)
        self.api.rows = [self.row]
        self.assertEqual(self.run_recovery()['status'], 'verified_reuse')
        self.assertEqual(self.api.posts, 1)

    def test_multiple_matches_and_bad_remote_content_stop(self):
        """Ambiguity and metadata/content mismatches never authorize an upload."""
        self.api.rows = [self.row, dict(self.row, id='file-second')]
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_MATCHING_FILES'): self.run_recovery()
        self.api.rows = [self.row]; self.api.bad = True
        with self.assertRaisesRegex(ValueError, 'REMOTE_CONTENT_DRIFT'): self.run_recovery()
        self.api.bad = False; self.api.rows = [dict(self.row, purpose='assistants')]
        with self.assertRaisesRegex(ValueError, 'REMOTE_METADATA_DRIFT'): self.run_recovery()
        self.assertEqual(self.api.posts, 0)

    def test_local_drift_partial_intent_and_fsync_failure_fail_closed(self):
        """Never POST when sealed bytes or durable intent creation are uncertain."""
        self.path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SEALED_FILE_DRIFT'): self.run_recovery()
        self.path.write_bytes(self.data)
        with patch.object(r.os, 'fsync', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError): self.run_recovery()
        self.sidecar.mkdir(parents=True, exist_ok=True)
        (self.sidecar/'intent.json').write_bytes(b'{')
        with self.assertRaises(ValueError): self.run_recovery()
        self.assertEqual(self.api.posts, 0)

    def test_long_timeout_no_post_retry_and_forbidden_endpoints(self):
        """The client permits Files only and sends one POST with 600-second timeout."""
        api = r.FileOnlyAPI('synthetic-key')
        with patch.object(r, 'urlopen', return_value=io.BytesIO(r.canonical(self.row))) as call:
            self.assertEqual(api.upload(self.path), self.row)
            self.assertEqual(call.call_count, 1); self.assertEqual(call.call_args.kwargs['timeout'], 600)
            self.assertEqual(call.call_args.args[0].full_url, 'https://api.openai.com/v1/files')
        with patch.object(r, 'urlopen', side_effect=TimeoutError) as call:
            with self.assertRaisesRegex(ValueError, 'UPLOAD_OUTCOME_UNCERTAIN'): api.upload(self.path)
            self.assertEqual(call.call_count, 1)
        for method, path in [('POST','/batches'),('POST','/responses'),('POST','/responses/input_tokens'),('GET','/batches?limit=100')]:
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'FILE_ONLY_ENDPOINT_REQUIRED'):
                api.request(method, path)

    def test_listing_is_fully_paginated_and_malformed_page_stops(self):
        """A match on the final page is retained; absence requires an explicit final page."""
        api = r.FileOnlyAPI('synthetic-key')
        first = dict(self.row, id='file-other', filename='other.jsonl')
        pages = [dict(data=[first], has_more=True), dict(data=[self.row], has_more=False)]
        with patch.object(r.transport, 'urlopen', side_effect=[io.BytesIO(r.canonical(p)) for p in pages]) as call:
            self.assertEqual(api.listing('files'), [first, self.row])
            self.assertIn('after=file-other', call.call_args.args[0].full_url)
        with patch.object(r.transport, 'urlopen', return_value=io.BytesIO(b'{"data":[]}')):
            with self.assertRaisesRegex(ValueError, 'INCOMPLETE_FILE_LISTING'): api.listing('files')

    def test_manual_second_attempt_is_numbered_and_never_repeated(self):
        """An explicit second attempt preserves first evidence and cannot authorize a third."""
        self.api.fail = True
        with self.assertRaises(ValueError): self.run_recovery()
        originals = {p.name: p.read_bytes() for p in self.sidecar.iterdir()}
        with self.assertRaisesRegex(ValueError, 'ACK_REQUIRED'):
            r.manual_retry(self.path, self.binding, self.sidecar, self.api)
        retry = self.sidecar / 'manual-retry-000002'
        api = r.FileOnlyAPI('synthetic-secret')
        from urllib.error import URLError
        with patch.object(api, 'listing', return_value=[]), patch.object(
                r, 'urlopen', side_effect=URLError(ConnectionResetError(54, 'SECRET'))) as post:
            with self.assertRaisesRegex(ValueError, 'UPLOAD_OUTCOME_UNCERTAIN'):
                r.manual_retry(self.path, self.binding, self.sidecar, api,
                               acknowledge_previous_uncertain=True)
            self.assertEqual(post.call_count, 1)
            self.assertEqual(post.call_args.kwargs['timeout'], 600)
            with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'):
                r.manual_retry(self.path, self.binding, self.sidecar, api,
                               acknowledge_previous_uncertain=True)
            self.assertEqual(post.call_count, 1)
        outcome = json.loads((retry / 'outcome.json').read_bytes())
        self.assertEqual(outcome['exceptionType'], 'URLError')
        self.assertEqual(outcome['transportCauseType'], 'ConnectionResetError')
        self.assertEqual(outcome['transportCauseErrno'], 54)
        self.assertNotIn('SECRET', (retry / 'outcome.json').read_text())
        auth = json.loads((retry / 'authorization.json').read_bytes())
        self.assertEqual(auth['recoveryAttempt'], 2)
        for name, raw in originals.items():
            self.assertEqual((self.sidecar / name).read_bytes(), raw)
        self.api.rows = [self.row]
        result = r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                                acknowledge_previous_uncertain=True)
        self.assertEqual(result['status'], 'verified_reuse')
        self.assertEqual(self.api.posts, 1)

    def test_manual_retry_reconciliation_and_success(self):
        """Ambiguous files stop; exact files reuse; zero matches allow one verified upload."""
        self.api.fail = True
        with self.assertRaises(ValueError): self.run_recovery()
        self.api.fail = False
        def run():
            return r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                                  acknowledge_previous_uncertain=True)
        self.api.rows = [self.row, self.row]
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_MATCHING_FILES'): run()
        self.api.rows = [self.row]; self.api.bad = True
        with self.assertRaisesRegex(ValueError, 'REMOTE_CONTENT_DRIFT'): run()
        self.api.bad = False; self.api.rows = []
        result = run()
        self.assertEqual(result['fileID'], self.row['id'])
        self.assertEqual(result['status'], 'verified_upload')
        self.assertEqual(self.api.posts, 2)
        with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'): run()
        self.assertEqual(self.api.posts, 2)

    def test_safe_http_diagnostics_exclude_response_body(self):
        """HTTP diagnostics retain status without sensitive response text."""
        diagnostic = r.safe_diagnostic(r.transport.HTTPFailure(503, b'SECRET'))
        self.assertEqual(diagnostic, dict(exceptionType='HTTPFailure', httpStatus=503))

    def test_new_job_checkpoint_protects_submitted_jobs(self):
        """Only the pinned third-job interruption permits recovery of the 207 unsent items."""
        from types import SimpleNamespace
        jobs = {
            r.JOB: {'plan': {'items': [None] * 444},
                    'submitted': {'id': 'batch_6ae2c345e7708190af156b2f997a1052'}},
            'job-000002': {'plan': {'items': [None] * 354},
                    'submitted': {'id': 'batch_6ae2c46899248190b47c536cc4a2c5bd'}},
            'job-000003': {'plan': {'items': [None] * 207}, 'upload_intent': {}},
        }
        log = SimpleNamespace(seq=2023,
            head='4f2b6f4602d2b85a631d385e8648ec175878a3703ed6ee31f53b224569d28be2',
            jobs=jobs, job=lambda jid, event: jobs[jid][event])
        self.assertEqual(r.recovery_checkpoint(log, 'job-000003')[2]['bytes'], 13994550)
        with self.assertRaisesRegex(ValueError, 'UNAUTHORIZED_RECOVERY_JOB'):
            r.recovery_checkpoint(log, 'job-000002')
        jobs['job-000003']['submitted'] = {}
        with self.assertRaisesRegex(ValueError, 'JOB_STATE_DRIFT'):
            r.recovery_checkpoint(log, 'job-000003')
        del jobs['job-000003']['submitted']
        jobs[r.JOB]['submitted']['id'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'SUBMITTED_BATCH_DRIFT'):
            r.recovery_checkpoint(log, 'job-000003')

    def test_read_only_reconcile_and_separate_new_job_records(self):
        """Reconciliation cannot upload; third-job records never touch the first job."""
        original = self.sidecar / 'preserved.json'
        self.sidecar.mkdir(parents=True)
        original.write_bytes(b'original evidence')
        self.assertEqual(r.reconcile(self.binding, self.api)['matchingFiles'], 0)
        self.api.rows = [self.row]
        self.assertEqual(r.reconcile(self.binding, self.api)['fileID'], self.row['id'])
        self.api.rows.append(self.row)
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_MATCHING_FILES'):
            r.reconcile(self.binding, self.api)
        self.assertEqual(self.api.posts, 0)
        self.api.rows = []
        new_sidecar = self.sidecar.parent / 'job-000003'
        with self.assertRaisesRegex(ValueError, 'explicit --allow-one-upload'):
            r.recover(self.path, self.binding, new_sidecar, self.api)
        # Fake uploader checks the selected job's durable intent before its POST.
        self.sidecar = new_sidecar
        r.recover(self.path, self.binding, new_sidecar, self.api, allow_one_upload=True)
        with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'):
            r.recover(self.path, self.binding, new_sidecar, self.api, allow_one_upload=True)
        self.assertEqual(self.api.posts, 1)
        self.assertEqual(original.read_bytes(), b'original evidence')

    def test_sdk_stream_configuration_and_numbered_authorization(self):
        """SDK upload streams exact bytes once after reconciliation and durable authorization."""
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.binding['jobID'] = 'job-000003'
        self.api.fail = True
        with self.assertRaises(ValueError): self.run_recovery()
        originals = {p.name: p.read_bytes() for p in self.sidecar.iterdir()}
        retry = self.sidecar / 'sdk-retry-000002'
        client = Mock()
        def create(**kwargs):
            self.assertTrue((retry / 'intent.json').exists())
            auth = json.loads((retry / 'authorization.json').read_bytes())
            self.assertEqual(auth['maxRetries'], 0)
            self.assertEqual(auth['sdkVersion'], '1.109.1')
            filename, stream, media_type = kwargs['file']
            self.assertEqual(filename, self.path.name)
            self.assertEqual(stream.read(), self.data)
            self.assertFalse(stream.closed)
            self.assertEqual(media_type, 'application/jsonl')
            self.assertEqual(kwargs['purpose'], 'batch')
            self.assertEqual(kwargs['timeout'], 600)
            return SimpleNamespace(model_dump=lambda **kw: self.row)
        client.files.create.side_effect = create
        factory = Mock(return_value=client)
        with patch.dict(sys.modules, {'openai': SimpleNamespace(__version__='1.109.1', OpenAI=factory)}):
            api = r.SDKFilesAPI('synthetic-key')
        factory.assert_called_once_with(api_key='synthetic-key', base_url='https://api.openai.com/v1',
                                        timeout=600, max_retries=0)
        with patch.object(api, 'listing', return_value=[]) as listing, patch.object(api, 'content', return_value=self.data):
            result = r.manual_retry(self.path, self.binding, self.sidecar, api,
                                    acknowledge_previous_uncertain=True, sdk=True)
            self.assertEqual(result['status'], 'verified_upload')
            listing.assert_called_once_with('files')
            with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'):
                r.manual_retry(self.path, self.binding, self.sidecar, api,
                               acknowledge_previous_uncertain=True, sdk=True)
        client.files.create.assert_called_once()
        api.close(); client.close.assert_called_once()
        for name, raw in originals.items(): self.assertEqual((self.sidecar / name).read_bytes(), raw)

    def test_sdk_uncertain_error_records_status_and_blocks_retry(self):
        """SDK exceptions expose numeric status only and cannot consume another authorization."""
        self.binding['jobID'] = 'job-000003'
        self.api.fail = True
        with self.assertRaises(ValueError): self.run_recovery()
        class SDKError(Exception):
            status_code = 503
        with patch.object(self.api, 'upload', side_effect=SDKError('SECRET')) as upload:
            for expected in ('UPLOAD_OUTCOME_UNCERTAIN', 'PRIOR_RECOVERY_INTENT_STOP'):
                with self.assertRaisesRegex(ValueError, expected):
                    r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                                   acknowledge_previous_uncertain=True, sdk=True)
            upload.assert_called_once()
        raw = (self.sidecar / 'sdk-retry-000002/outcome.json').read_text()
        self.assertNotIn('SECRET', raw)
        self.assertEqual(json.loads(raw)['httpStatus'], 503)

    def prepare_third_sdk_attempt(self):
        """Create two synthetic uncertain attempts without real provider traffic."""
        self.binding['jobID'] = 'job-000003'
        self.api.fail = True
        with self.assertRaises(ValueError): self.run_recovery()
        with self.assertRaises(ValueError):
            r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                           acknowledge_previous_uncertain=True, sdk=True)
        return {p: p.read_bytes() for p in self.sidecar.rglob('*') if p.is_file()}

    def third_sdk_attempt(self):
        """Invoke only the explicitly numbered authorization."""
        return r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                              acknowledge_previous_uncertain=True, sdk=True, attempt=3)

    def test_sdk_third_attempt_isolated_and_permanently_blocked_after_uncertainty(self):
        """Earlier records remain immutable and a third-attempt intent cannot be reused."""
        originals = self.prepare_third_sdk_attempt()
        with self.assertRaisesRegex(ValueError, 'UPLOAD_OUTCOME_UNCERTAIN'):
            self.third_sdk_attempt()
        self.assertEqual(self.api.posts, 3)
        with self.assertRaisesRegex(ValueError, 'PRIOR_RECOVERY_INTENT_STOP'):
            self.third_sdk_attempt()
        self.assertEqual(self.api.posts, 3)
        auth = json.loads((self.sidecar / 'sdk-retry-000003/authorization.json').read_bytes())
        self.assertEqual(auth['recoveryAttempt'], 3)
        self.assertEqual(len(auth['previousRecordSha256']), 5)
        self.assertEqual(auth['binding'], self.binding)
        for path, raw in originals.items(): self.assertEqual(path.read_bytes(), raw)

    def test_sdk_third_attempt_remote_reuse_and_reconciliation_failures(self):
        """Remote failures or ambiguity cannot dispatch; exact bytes permit reuse only."""
        self.prepare_third_sdk_attempt()
        with patch.object(self.api, 'listing', side_effect=OSError('offline')):
            with self.assertRaises(OSError): self.third_sdk_attempt()
        self.api.rows = [self.row, self.row]
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_MATCHING_FILES'): self.third_sdk_attempt()
        self.api.rows = [self.row]; self.api.bad = True
        with self.assertRaisesRegex(ValueError, 'REMOTE_CONTENT_DRIFT'): self.third_sdk_attempt()
        self.api.bad = False
        self.assertEqual(self.third_sdk_attempt()['status'], 'verified_reuse')
        self.assertEqual(self.api.posts, 2)
        self.assertFalse((self.sidecar / 'sdk-retry-000003/intent.json').exists())

    def test_sdk_third_attempt_requires_prior_uncertain_authorization(self):
        """No arbitrary retry numbers or altered prior authority can authorize a POST."""
        self.prepare_third_sdk_attempt()
        prior = self.sidecar / 'sdk-retry-000002/authorization.json'
        record = json.loads(prior.read_bytes()); record['maxRetries'] = 1
        prior.write_bytes(r.canonical(record))
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_SDK_AUTHORIZATION_DRIFT'):
            self.third_sdk_attempt()
        with self.assertRaisesRegex(ValueError, 'UNAUTHORIZED_RECOVERY_ATTEMPT'):
            r.manual_retry(self.path, self.binding, self.sidecar, self.api,
                           acknowledge_previous_uncertain=True, sdk=True, attempt=4)
        self.assertEqual(self.api.posts, 2)

    def test_installed_sdk_mock_transport(self):
        """Exercise the real pinned SDK without sockets when installed in the new environment."""
        import openai
        if getattr(openai, '__version__', None) != '1.109.1':
            self.skipTest('Run in multigranular-kg for real SDK MockTransport validation')
        import httpx
        api = r.SDKFilesAPI('synthetic-key')
        api.client.close()
        seen = []
        def handler(request):
            seen.append(request)
            self.assertEqual(request.url.path, '/v1/files')
            self.assertEqual(request.method, 'POST')
            body = request.read()
            self.assertIn(self.path.name.encode(), body)
            self.assertIn(self.data, body)
            return httpx.Response(200, json=self.row)
        api.client = openai.OpenAI(api_key='synthetic-key', timeout=600, max_retries=0,
                                  http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            self.assertEqual(api.upload(self.path)['id'], self.row['id'])
            self.assertEqual(len(seen), 1)
        finally: api.close()

    def test_wrong_queue_checkpoint_fails_before_network(self):
        """The local verifier accepts only the exact sealed v6 manifest."""
        queue = self.root/r.QUEUE; queue.mkdir(parents=True)
        (queue/'queue-manifest.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'QUEUE_DRIFT'):
            with r.sealed_job(self.root): pass


if __name__ == '__main__': unittest.main()
