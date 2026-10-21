"""Focused deterministic Batch tests; sockets blocked and provider API fully simulated."""
from __future__ import annotations

from copy import deepcopy
import json
import io
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import full_corpus_gpt61_batch as run
from src.extraction.llm.publications.batch_journal import batch_journal


class FakeAPI:
    """Simulate exact remote artifacts, including ambiguous submission acknowledgements."""

    def __init__(self):
        """Start with an empty account and deterministic counters."""
        self.files, self.batches, self.contents = {}, {}, {}
        self.creates = 0
        self.uploads = 0
        self.counts = 0
        self.lose_create = False
        self.lose_upload = False
        self.reverse = True
        self.status = 'completed'
        self.omit = False
        self.duplicate = False
        self.expired = False
        self.foreign = False

    def count(self, body):
        """Return deterministic schema-aware count fixture."""
        self.counts += 1
        return dict(object='response.input_tokens', input_tokens=10)

    def upload(self, path):
        """Retain exact uploaded bytes before optionally losing the acknowledgement."""
        self.uploads += 1
        fid = 'file-' + str(self.uploads)
        self.files[fid] = dict(id=fid, filename=path.name, bytes=path.stat().st_size)
        self.contents[fid] = path.read_bytes()
        if self.lose_upload:
            self.lose_upload = False
            raise OSError('lost upload acknowledgement')
        return self.files[fid]

    def create(self, file_id, metadata):
        """Create one remote job; simulated loss must never cause another create."""
        self.creates += 1
        bid = 'batch-' + str(self.creates)
        batch = dict(id=bid, input_file_id=file_id, metadata=metadata, endpoint='/v1/responses',
                     status='in_progress', output_file_id=None, error_file_id=None)
        self.batches[bid] = batch
        if self.lose_create:
            self.lose_create = False
            raise OSError('lost create acknowledgement')
        return deepcopy(batch)

    def retrieve(self, bid):
        """Generate authentic-shape fixture rows in reverse order, optionally expired/partial."""
        batch = self.batches[bid]
        if batch['status'] == 'in_progress' and self.status != 'in_progress':
            batch['status'] = self.status
            lines = [json.loads(line) for line in self.contents[batch['input_file_id']].splitlines()]
            rows = []
            for line in lines:
                if self.expired:
                    rows.append(dict(custom_id=line['custom_id'], response=None,
                                     error=dict(code='batch_expired', message='could not execute')))
                else:
                    rows.append(dict(custom_id=line['custom_id'], error=None, response=dict(status_code=200,
                        request_id='req-' + line['custom_id'], body=dict(id='resp-' + line['custom_id'],
                        model='gpt-6.1-sol', status='completed', created_at=1, service_tier='default', usage={'input_tokens': 10, 'output_tokens': 1}))))
            if self.reverse:
                rows.reverse()
            if self.omit:
                rows.pop()
            if self.duplicate:
                rows += rows[:1]
            fid = 'output-' + bid
            batch['error_file_id' if self.expired else 'output_file_id'] = fid
            self.contents[fid] = b''.join(run.canonical_json(r) + b'\n' for r in rows)
        return deepcopy(batch)

    def listing(self, resource):
        """Fully visible fixture account; optionally includes an unrelated active job."""
        if resource == 'files':
            return list(self.files.values())
        result = deepcopy(list(self.batches.values()))
        if self.foreign:
            result.append(dict(id='foreign', status='in_progress'))
        return result

    def content(self, fid):
        """Return stored bytes without changing ordering or content."""
        return self.contents[fid]


class BatchControllerTests(unittest.TestCase):
    """Exercise the real durable journal and scheduler with tiny independent fixtures."""

    @classmethod
    def setUpClass(cls):
        """Load pinned local modules once, without network access."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')):
            cls.paired, cls.stream, cls.native, cls.parent = run.baseline.dependencies()

    def setUp(self):
        """Use a temporary run, three requests, and a two-request queue capacity."""
        self.block = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        self.block.start()
        self.addCleanup(self.block.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prepared = {}
        self.entries = []
        for n in range(3):
            rid = 'request-' + str(n)
            p = dict(request=dict(requestID=rid, requestInputSha256=rid), schema={}, binding={},
                     providerInput=b'fixture', body=dict(model='gpt-6.1-sol', reasoning={'effort': 'medium'},
                     store=False, max_output_tokens=32768, input='fixture', text={'format': {'schema': {}}}))
            self.prepared[rid] = p
            self.entries.append(dict(identity=self.stream.fingerprint(p), estimatedCostUSD=1))
        self.mf = dict(generatorPins=self.stream.versions(), requests=self.entries, pricing=run.PRICING,
                       queuedTokenLimit=20, meaningfulSampleRequests=2)
        self.api = FakeAPI()
        self.processed = []
        self.Journal = batch_journal(self.native, self.verify, self.stream.fingerprint, self.verify_outcome)

    def verify(self, p, entry):
        """Require exact preserved fixture identity."""
        run.require(self.stream.fingerprint(p) == entry['identity'], 'IDENTITY_DRIFT')

    def verify_outcome(self, p, receipt, outcome, n):
        """Check fixture outcome-to-receipt binding; native logic has its own contract test."""
        run.require(outcome['cid'] == receipt['row']['custom_id'] and outcome['n'] == n, 'OUTCOME_DRIFT')

    def journal(self):
        """Reopen exactly the same manifest and journal for restarts."""
        data = run.canonical_json(self.mf) + b'\n'
        return self.Journal(self.root / 'execution.jsonl', data, run.sha256_bytes(data))

    def process(self, p, receipt, n, first):
        """Simulate deterministic native success/technical retry, never semantic judgments."""
        self.processed.append((p['request']['requestID'], n))
        expired = (receipt['row'].get('error') or {}).get('code') == 'batch_expired'
        return dict(cid=receipt['row']['custom_id'], n=n, attempt={'attemptNumber': n},
                    processable=not expired, retryEligible=expired and n == 1, productionResult={'fixture': True})

    def record(self, row, p, bid, n):
        """Use exact synthetic costs for state accounting."""
        record = run.response_record(row, p, self.paired, bid, n)
        if row.get('response'):
            record['cost'] = dict(estimatedUSD=1, basis='reported_cache_details')
        return record

    def cycle(self, log, process=None, record=None, pilot_only=False):
        """Invoke the actual scheduler with no network-capable callback."""
        return run.cycle(log, self.api, lambda e: deepcopy(self.prepared[e['identity']['requestID']]),
                         process or self.process, record or self.record, self.native, self.stream.fingerprint, pilot_only)

    def pilot_queue(self):
        """Extend the fixture beyond request 100 to detect unintended corpus dispatch."""
        for n in range(3, 105):
            rid = 'request-' + str(n)
            p = deepcopy(self.prepared['request-0'])
            p['request'].update(requestID=rid, requestInputSha256=rid)
            self.prepared[rid] = p
            self.entries.append(dict(identity=self.stream.fingerprint(p), estimatedCostUSD=1))
        self.mf['queuedTokenLimit'] = 500

    def finish_pilot(self, log):
        """Bound pilot fixture cycles, retaining the real production scheduler."""
        for _ in range(10):
            if self.cycle(log, pilot_only=True) == 'pilot_complete':
                return
        self.fail('pilot failed to complete')

    def submit_all(self, log, workers=8):
        """Run the new submit-only scheduler with a simulated provider."""
        return run.submit_all(log, self.api, lambda e: deepcopy(self.prepared[e['identity']['requestID']]),
                              self.native, self.stream.fingerprint, workers)

    def test_submit_all_bypasses_ramp_collect_is_separate_and_idempotent(self):
        """Every original entry passes request 100 without collecting; restart preserves all IDs."""
        self.pilot_queue()
        self.mf['queuedTokenLimit'] = 15_000_000_000
        with patch.object(run, 'MAX_REQUESTS', 40), self.journal() as log:
            with patch.object(self.api, 'retrieve', side_effect=AssertionError('SUBMIT_MUST_NOT_COLLECT')):
                self.assertEqual(self.submit_all(log), 'all_admissible_submitted')
            self.assertEqual(len(log.assignments), 105)
            self.assertEqual(len(log.receipts), 0)
            self.assertIsNone(run.summary(log)['actualUSD'])
            order = [i['rid'] for j in log.jobs for i in log.job(j, 'plan')['items']]
            self.assertEqual(order, list(self.prepared))
        prefix = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log:
            self.submit_all(log)
            self.assertEqual(self.api.creates, 3)
            self.assertEqual(self.api.counts, 105)
            with patch.object(self.api, 'create', side_effect=AssertionError('COLLECT_MUST_NOT_SUBMIT')), \
                 patch.object(self.api, 'upload', side_effect=AssertionError('COLLECT_MUST_NOT_UPLOAD')):
                self.assertEqual(run.collect_once(log, self.api, self.process, self.record), [])
                seq = log.seq
                self.assertEqual(run.collect_once(log, self.api, self.process, self.record), [])
                self.assertEqual(log.seq, seq)
            self.assertEqual(run.summary(log)['completed'], 105)
            self.assertEqual(log.spent, 105)
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().startswith(prefix))

    def test_submit_only_capacity_stop_then_continue_after_collect(self):
        """Finite operational capacity yields unsent counts, then collection releases capacity."""
        with self.journal() as log:
            self.assertEqual(self.submit_all(log), 'operational_capacity_full')
            self.assertEqual(run.summary(log)['unsentRequests'], 1)
            self.api.status = 'in_progress'
            self.assertEqual(run.collect_once(log, self.api, self.process, self.record), [])
            self.assertEqual(len(log.receipts), 0)
            self.api.status = 'completed'
            run.collect_once(log, self.api, self.process, self.record)
            self.submit_all(log)
            self.assertEqual(self.api.creates, 2)

    def test_expired_collect_defers_bounded_retry_until_submit(self):
        """Collect never retries even when expiration makes a native retry eligible."""
        self.mf['queuedTokenLimit'] = 100
        self.api.expired, self.api.status = True, 'expired'
        with self.journal() as log:
            self.submit_all(log)
            run.collect_once(log, self.api, self.process, self.record)
            self.assertEqual(self.api.creates, 1)
            self.assertTrue(all(s == 'retry' for s in log.state.values()))
            self.submit_all(log)
            run.collect_once(log, self.api, self.process, self.record)
            self.assertEqual(self.submit_all(log), 'technical_stop')
            self.assertEqual(self.api.creates, 2)

    def test_definitive_capacity_rejection_stops_then_explicit_resume(self):
        """A rejected POST is durable, distinct from uncertainty, and never blindly repeated."""
        error = run.batch_transport.CapacityRejected(429, {'error': {'code': 'token_limit_exceeded'}})
        with self.journal() as log, patch.object(self.api, 'create', side_effect=error):
            with self.assertRaises(run.batch_transport.CapacityRejected):
                self.submit_all(log)
            self.assertIn('submission_rejected', log.jobs['job-000001'])
        with self.journal() as log:
            with self.assertRaisesRegex(ValueError, 'PROVIDER_CAPACITY_STOP'):
                run.submit(log, 'job-000001', self.api)
            self.assertEqual(run.collect_once(log, self.api, self.process, self.record), [])
            run.increase_capacity(log, 15_000_000_000)
            self.submit_all(log)
            self.assertEqual(self.api.uploads, 2)
            self.assertEqual(self.api.creates, 2)
            self.assertEqual(log.queue_capacity, 15_000_000_000)

    def test_collect_recovers_uncertain_submission_without_post(self):
        """Lost create acknowledgement can be adopted by collect without dispatch."""
        self.api.lose_create = True
        with self.journal() as log:
            with self.assertRaises(OSError):
                self.submit_all(log)
            self.assertIsNone(run.summary(log)['actualUSD'])
            self.assertEqual(run.summary(log)['uncertainSubmissionRequests'], 2)
        with self.journal() as log, patch.object(self.api, 'create', side_effect=AssertionError('NO_POST')):
            self.assertEqual(run.collect_once(log, self.api, self.process, self.record), [])
            self.assertEqual(len(log.receipts), 2)
            self.assertEqual(self.api.creates, 1)

    def test_collect_continues_other_jobs_after_missing_results(self):
        """One defective job cannot hide available evidence from later jobs."""
        self.mf['queuedTokenLimit'] = 100
        with patch.object(run, 'MAX_REQUESTS', 1), self.journal() as log:
            self.submit_all(log)
            self.api.omit = True
            self.api.retrieve('batch-1')
            self.api.omit = False
            errors = run.collect_once(log, self.api, self.process, self.record)
            self.assertEqual(len(errors), 1)
            self.assertIn('MISSING_BATCH_RESULTS', errors[0]['reason'])
            self.assertEqual(len(log.receipts), 2)
            self.assertEqual(self.api.creates, 3)

    def test_token_window_interruption_reuses_durable_counts(self):
        """Only acknowledged read-only counts are repeated; nothing is submitted early."""
        self.mf['queuedTokenLimit'] = 100
        def count(body):
            if body['input'] == 'fail':
                raise OSError('count interrupted')
            return dict(object='response.input_tokens', input_tokens=10)
        self.prepared['request-1']['body']['input'] = 'fail'
        self.entries[1]['identity'] = self.stream.fingerprint(self.prepared['request-1'])
        with self.journal() as log, patch.object(self.api, 'count', side_effect=count):
            with self.assertRaises(OSError):
                self.submit_all(log)
            self.assertEqual(set(log.tokens), {'request-0'})
            self.assertEqual(self.api.creates, 0)
        with self.journal() as log:
            self.submit_all(log)
            self.assertEqual(self.api.counts, 2)

    def test_uncertain_http_evidence_is_preserved_without_retry(self):
        """HTTP errors retain their bytes and cannot authorize another mutating POST."""
        failure = run.batch_transport.HTTPFailure(500, b'{"error":"uncertain"}')
        with self.journal() as log, patch.object(self.api, 'create', side_effect=failure):
            with self.assertRaises(run.batch_transport.HTTPFailure):
                self.submit_all(log)
            self.assertIsNone(run.summary(log)['actualUSD'])
        events = [json.loads(line)['record'] for line in (self.root / 'execution.jsonl').read_bytes().splitlines()]
        evidence = next(e['payload'] for e in events if e['event'] == 'submission_error')
        self.assertEqual(evidence['bodyBase64'], failure.evidence['bodyBase64'])
        with self.journal() as log:
            with self.assertRaisesRegex(ValueError, 'UNCERTAIN_SUBMISSION'):
                self.submit_all(log)
            self.assertEqual(self.api.creates, 0)

    def test_submit_all_anomaly_stops_later_retry_dispatch(self):
        """The diagnostic cannot prevent accepted spend but blocks subsequent dispatch."""
        with self.journal() as log:
            self.submit_all(log)
            def expensive(*args):
                receipt = self.record(*args)
                receipt['cost']['estimatedUSD'] = 3
                return receipt
            run.collect_once(log, self.api, self.process, expensive)
            self.assertEqual(self.submit_all(log), 'cost_anomaly_stop')
            self.assertEqual(self.api.creates, 1)

    def test_historical_compatibility_is_read_only_and_capacity_independent(self):
        """The authentic 1M check validates without modifying any historical file."""
        before = {p: run.sha256_bytes(p.read_bytes()) for p in run.CHECK.rglob('*') if p.is_file()}
        Journal = batch_journal(self.native, lambda p, e: run.verify_variant(p, e, self.stream),
                                self.stream.fingerprint, run.verify_outcome,
                                lambda p, r: run.require(r == run.response_record(r['row'], p, self.paired,
                                                        r['batchID'], r['number']), 'RECEIPT_DRIFT'))
        run.verify_compatibility(Journal, self.native, self.parent, self.stream)
        manifest = run.manifest(self.parent, self.stream, 15_000_000_000, False)
        self.assertEqual(len(manifest['requests']), 10893)
        self.assertEqual(manifest['queuedTokenLimit'], 15_000_000_000)
        self.assertIn('not a verified account limit', manifest['capacitySource'])
        self.assertEqual(before, {p: run.sha256_bytes(p.read_bytes()) for p in run.CHECK.rglob('*') if p.is_file()})

    def test_cli_modes_bind_production_capacity_without_mutating_check(self):
        """Real CLI wiring accepts 15B, resumes the same manifest, and separates callbacks."""
        production = self.root / 'production'
        with patch.object(run, 'RUN', production), \
             patch.object(run.baseline, 'dependencies', return_value=(self.paired, self.stream, self.native, self.parent)), \
             patch.object(run.baseline.provider, 'load_openai_api_key', return_value='offline-dummy'), \
             patch.object(run.batch_transport, 'BatchAPI', return_value=self.api), \
             patch.object(self.stream, 'load', return_value=({}, {'records': []})), \
             patch.object(run, 'submit_all', return_value='all_admissible_submitted') as submit, \
             patch.object(run, 'collect_once', return_value=[]) as collect:
            with patch.object(run.sys, 'argv', ['batch', '--submit-all', '--queued-token-limit', '15000000000']):
                run.main()
                run.main()
            self.assertEqual(submit.call_count, 2)
            collect.assert_not_called()
            self.assertEqual(run.baseline.read(production / 'run-manifest.json')['queuedTokenLimit'], 15_000_000_000)
            with patch.object(run.sys, 'argv', ['batch', '--collect']):
                run.main()
            self.assertEqual(submit.call_count, 2)
            self.assertEqual(collect.call_count, 1)

    def test_pilot_exact_100_restart_then_full_production(self):
        """Pilot output stays production output; normal continuation starts at request 101."""
        self.pilot_queue()
        with self.journal() as log:
            self.cycle(log, pilot_only=True)
            self.assertEqual(len(log.assignments), 50)
        with self.journal() as log:
            self.finish_pilot(log)
            self.assertEqual(set(log.state), set(list(self.prepared)[:100]))
            self.assertTrue(all(s == 'completion' for s in log.state.values()))
            self.assertEqual(len(log.receipts), 100)
        pilot_bytes = (self.root / 'execution.jsonl').read_bytes()
        creates = self.api.creates
        with self.journal() as log:
            self.assertEqual(self.cycle(log, pilot_only=True), 'pilot_complete')
        self.assertEqual(self.api.creates, creates)
        self.assertEqual((self.root / 'execution.jsonl').read_bytes(), pilot_bytes)
        with self.journal() as log:
            self.finish(log)
            self.assertEqual(len(log.receipts), 105)
            self.assertEqual(log.spent, 105)
        self.assertEqual(len(self.processed), 105)
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().startswith(pilot_bytes))
        self.assertEqual(self.api.creates, creates + 1)

    def test_capacity_increase_preserves_manifest_jobs_and_restart(self):
        """A provisional-to-confirmed increase is a monotone, idempotent journal event."""
        self.pilot_queue()
        original_manifest = run.canonical_json(self.mf)
        with self.journal() as log:
            self.cycle(log, pilot_only=True)
            old_job = log.job('job-000001', 'submitted')
            pin = log.pin
        prefix = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log:
            run.increase_capacity(log, 1000)
            seq = log.seq
            run.increase_capacity(log, 1000)
            self.assertEqual(log.seq, seq)
            with self.assertRaisesRegex(ValueError, 'DECREASE'):
                run.increase_capacity(log, 500)
            self.assertEqual(log.pin, pin)
            self.assertEqual(run.canonical_json(log.manifest), original_manifest)
            self.assertEqual(log.job('job-000001', 'submitted'), old_job)
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().startswith(prefix))
        with self.journal() as log:
            self.assertEqual(log.queue_capacity, 1000)
            self.assertEqual(log.manifest['queuedTokenLimit'], 500)
            self.finish_pilot(log)
            self.finish(log)
            self.assertEqual(len(log.receipts), 105)
        events = [json.loads(line)['record'] for line in (self.root / 'execution.jsonl').read_bytes().splitlines()]
        changes = [e['payload'] for e in events if e['event'] == 'capacity_increase']
        self.assertEqual(len(changes), 1)
        self.assertEqual((changes[0]['previous'], changes[0]['new']), (500, 1000))
        self.assertEqual(changes[0]['manifestSha256'], pin)
        self.assertEqual(len(self.processed), 105)

    def test_pilot_retries_stay_inside_first_100(self):
        """Technical retries do not consume the pilot scope or admit request 101."""
        self.pilot_queue()
        self.api.expired = True
        self.api.status = 'expired'
        with self.journal() as log:
            self.cycle(log, pilot_only=True)
            self.cycle(log, pilot_only=True)
            self.api.expired = False
            self.api.status = 'completed'
            self.finish_pilot(log)
            self.assertEqual(len(log.receipts), 150)
            self.assertEqual(set(log.state), set(list(self.prepared)[:100]))
            self.assertTrue(all(s == 'completion' for s in log.state.values()))

    def test_pilot_refuses_preexisting_out_of_scope_job(self):
        """Pilot cannot submit or silently adopt a previously planned full-corpus job."""
        self.pilot_queue()
        with self.journal() as log:
            self.finish_pilot(log)
            self.cycle(log)
            creates = self.api.creates
            with self.assertRaisesRegex(ValueError, 'OUT_OF_PILOT_JOB'):
                self.cycle(log, pilot_only=True)
            self.assertEqual(self.api.creates, creates)

    def test_capacity_cli_is_offline_and_keeps_initial_manifests(self):
        """The real CLI replays an increase without requiring credentials or rewriting manifests."""
        check, production = self.root / 'check', self.root / 'production'
        check.mkdir()
        production.mkdir()
        initial = 1000000
        check_bytes = run.canonical_json(run.manifest(self.parent, self.stream, initial, True)) + b'\n'
        prod_bytes = run.canonical_json(run.manifest(self.parent, self.stream, initial, False)) + b'\n'
        (check / 'run-manifest.json').write_bytes(check_bytes)
        (production / 'run-manifest.json').write_bytes(prod_bytes)
        with self.Journal(production / 'execution.jsonl', prod_bytes, run.sha256_bytes(prod_bytes)):
            pass
        with patch.object(run, 'CHECK', check), patch.object(run, 'RUN', production), \
             patch.object(run.baseline, 'dependencies', return_value=(self.paired, self.stream, self.native, self.parent)), \
             patch.object(run.baseline.provider, 'load_openai_api_key', side_effect=AssertionError('NO_CREDENTIAL_ACCESS')), \
             patch.object(run.sys, 'argv', ['batch', '--increase-queue-capacity', '2000000']):
            run.main()
            data = (production / 'execution.jsonl').read_bytes()
            run.main()
            self.assertEqual((production / 'execution.jsonl').read_bytes(), data)
            self.assertEqual(run.offline_status(production)['operationalQueueCapacity'], 2000000)
        self.assertEqual((check / 'run-manifest.json').read_bytes(), check_bytes)
        self.assertEqual((production / 'run-manifest.json').read_bytes(), prod_bytes)

    def finish(self, log):
        """Bound fixture cycles so a scheduling deadlock fails the test."""
        for _ in range(10):
            result = self.cycle(log)
            if result == 'complete':
                return
        self.fail('did not complete: ' + result)

    def test_jsonl_identity_capacity_reordering_restart(self):
        """One independent body per line; output order cannot alter association or output bytes."""
        with self.journal() as log:
            self.assertEqual(self.cycle(log), 'waiting')
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(log.reserved_tokens(), 20)
            job = log.job('job-000001', 'plan')
            lines = [json.loads(x) for x in (self.root / job['filename']).read_bytes().splitlines()]
            self.assertEqual(len(lines), 2)
            for line, item in zip(lines, job['items']):
                self.assertEqual(line['body'], self.prepared[item['rid']]['body'])
                self.assertEqual(line['custom_id'], item['custom_id'])
                self.assertNotIn('stream', line['body'])
        with self.journal() as log:
            self.finish(log)
            self.assertEqual(log.spent, 3)
            self.assertEqual(run.summary(log)['completed'], 3)
        original = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log:
            self.assertEqual(self.cycle(log), 'complete')
        self.assertEqual(original, (self.root / 'execution.jsonl').read_bytes())
        self.assertEqual(len(self.processed), 3)
        self.assertEqual(self.api.creates, 2)

    def test_lost_create_acknowledgement_adopts_without_duplicate(self):
        """A remote submitted job is recovered by exact metadata after an interrupted POST."""
        self.api.lose_create = True
        with self.assertRaises(OSError), self.journal() as log:
            self.cycle(log)
        with self.journal() as log:
            self.finish(log)
        self.assertEqual(self.api.creates, 2)

    def test_lost_upload_acknowledgement_adopts_exact_file(self):
        """A content-verified uploaded file is reused, not reuploaded."""
        self.api.lose_upload = True
        with self.assertRaises(OSError), self.journal() as log:
            self.cycle(log)
        with self.journal() as log:
            self.finish(log)
        self.assertEqual(self.api.uploads, 2)

    def test_uncertain_submission_without_remote_match_stops(self):
        """Absence from listing does not prove a POST was never accepted."""
        self.api.lose_create = True
        with self.assertRaises(OSError), self.journal() as log:
            self.cycle(log)
        self.api.batches.clear()
        with self.assertRaisesRegex(ValueError, 'UNCERTAIN_SUBMISSION'), self.journal() as log:
            self.cycle(log)
        self.assertEqual(self.api.creates, 1)

    def test_running_batch_is_not_resubmitted(self):
        """Polling and restarts leave still-running jobs and reservations intact."""
        self.api.status = 'in_progress'
        for _ in range(3):
            with self.journal() as log:
                self.cycle(log)
        self.assertEqual(self.api.creates, 1)

    def test_duplicate_custom_ids_stop_before_native_processing(self):
        """Even identical duplicates cannot be silently accepted."""
        self.api.duplicate = True
        with self.journal() as log:
            self.cycle(log)
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_CUSTOM_ID'):
                self.cycle(log)
            self.assertFalse(self.processed)

    def test_missing_results_preserve_partial_and_never_redispatch(self):
        """Available outputs are durable; missing outputs remain an explicit STOP."""
        self.api.omit = True
        with self.journal() as log:
            self.cycle(log)
            with self.assertRaisesRegex(ValueError, 'MISSING_BATCH_RESULTS'):
                self.cycle(log)
            self.assertEqual(len(log.receipts), 1)
            self.assertEqual(log.spent, 1)
        with self.assertRaisesRegex(ValueError, 'MISSING_BATCH_RESULTS'), self.journal() as log:
            self.cycle(log)
        self.assertEqual(self.api.creates, 1)

    def test_expiration_is_bounded_and_zero_unexecuted_cost(self):
        """Explicit per-request expiration receives only the original bounded retry."""
        self.api.expired = True
        self.api.status = 'expired'
        with self.journal() as log:
            for _ in range(4):
                state = self.cycle(log)
                if state == 'technical_stop':
                    break
            self.assertEqual(state, 'technical_stop')
            self.assertEqual(log.spent, 0)
            self.assertTrue(all(n <= 2 for _, n in log.assignments))
        count = self.api.creates
        with self.journal() as log:
            self.cycle(log)
        self.assertEqual(self.api.creates, count)

    def test_failed_batch_stops_without_resubmission(self):
        """A terminal failed Batch is not treated as a successful execution."""
        self.api.status = 'failed'
        with self.journal() as log:
            self.cycle(log)
            with self.assertRaisesRegex(ValueError, 'FAILED_OR_CANCELLED'):
                self.cycle(log)
        self.assertEqual(self.api.creates, 1)

    def test_cost_anomaly_stops_after_sample_and_persists(self):
        """Costs compare against processed requests, include all attempts, and survive restart."""
        def expensive(*args):
            result = self.record(*args)
            result['cost']['estimatedUSD'] = 3
            return result
        with self.journal() as log:
            self.cycle(log, record=expensive)
            self.assertEqual(self.cycle(log, record=expensive), 'cost_anomaly_stop')
            self.assertEqual(log.spent, 6)
            self.assertEqual(log.estimated_processed, 2)
        with self.journal() as log:
            self.assertEqual(self.cycle(log), 'cost_anomaly_stop')
        self.assertEqual(self.api.creates, 1)

    def test_interrupted_processing_uses_durable_downloads(self):
        """Interrupted native processing resumes without provider resubmission."""
        with self.journal() as log:
            self.cycle(log)
            with self.assertRaises(RuntimeError):
                self.cycle(log, process=lambda *args: (_ for _ in ()).throw(RuntimeError('interrupt')))
            self.assertEqual(len(log.receipts), 2)
        with self.journal() as log:
            self.finish(log)
        self.assertEqual(self.api.creates, 2)

    def test_foreign_jobs_wait_without_assuming_capacity(self):
        """Unknown external reservations cause a wait, not overcommit."""
        self.api.foreign = True
        with self.journal() as log:
            self.assertEqual(self.cycle(log), 'waiting_foreign_batches')
        self.assertEqual(self.api.creates, 0)

    def test_byte_and_count_file_limits(self):
        """Packing uses exact serialized bytes and enforces count limits."""
        self.mf['queuedTokenLimit'] = 100
        with patch.object(run, 'MAX_REQUESTS', 1), self.journal() as log:
            self.cycle(log)
            self.assertEqual(self.api.creates, 3)
            self.assertTrue(all(len(log.job(j, 'plan')['items']) == 1 for j in log.jobs))

    def test_serialized_byte_limit_splits_files(self):
        """Two fitting requests cannot exceed the exact per-file byte bound together."""
        self.mf['queuedTokenLimit'] = 100
        length = len(run.input_line(self.prepared['request-0'], 1, self.stream.fingerprint)[1])
        with patch.object(run, 'MAX_BYTES', length + 1), self.journal() as log:
            self.cycle(log)
            self.assertEqual(self.api.creates, 3)
            self.assertTrue(all(log.job(j, 'plan')['bytes'] <= length + 1 for j in log.jobs))

    def test_small_sample_must_finish_before_scaling(self):
        """Large capacity does not bypass the measured initial group."""
        self.mf['queuedTokenLimit'] = 100
        with patch.object(run, 'SAMPLE', 2), self.journal() as log:
            self.cycle(log)
            self.assertEqual(len(log.assignments), 2)
            self.assertEqual(self.api.creates, 1)
            self.cycle(log)
            self.assertEqual(len(log.assignments), 3)
            self.assertEqual(log.spent, 2)

    def test_unknown_usage_holds_and_prevents_more_dispatch(self):
        """An error without usage evidence is never silently priced at zero."""
        def unknown(*args):
            r = self.record(*args)
            r['cost'] = dict(estimatedUSD=None, basis='missing_usage')
            return r
        with self.journal() as log:
            self.cycle(log)
            self.assertEqual(self.cycle(log, record=unknown), 'technical_stop')
            self.assertEqual(len(log.unknown_usage), 2)
        self.assertEqual(self.api.creates, 1)

    def test_single_writer_and_corrupt_results_fail_closed(self):
        """No second writer or altered downloaded response can enter native processing."""
        with self.journal() as log:
            with self.assertRaises(BlockingIOError):
                with self.journal():
                    pass
            self.cycle(log)
            with self.assertRaises(RuntimeError):
                self.cycle(log, process=lambda *args: (_ for _ in ()).throw(RuntimeError('interrupt')))
            file = log.job('job-000001', 'downloads')['files'][0]
            (self.root / file['filename']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'RESULT_FILE_HASH_DRIFT'), self.journal() as log:
            self.cycle(log)

    def test_transport_cost_missing_metadata_is_preserved(self):
        """Invalid metadata preserves raw body and real usage instead of losing the response."""
        row = dict(custom_id='x', error=None, response=dict(status_code=200,
                   body=dict(model='gpt-6.1-sol', usage={'input_tokens': 10, 'output_tokens': 1})))
        receipt = run.response_record(row, self.prepared['request-0'], self.paired, 'batch', 1)
        self.assertEqual(receipt['row'], row)
        self.assertEqual(receipt['metadataError'], 'INVALID_PROVIDER_METADATA')
        self.assertGreater(receipt['cost']['estimatedUSD'], 0)

    def test_staged_submission_record_recovers_without_duplicate(self):
        """A fully staged acknowledgement survives a crash partway through journal append."""
        self.api.lose_create = True
        with self.assertRaises(OSError), self.journal() as log:
            self.cycle(log)
        with self.journal() as log:
            payload = deepcopy(self.api.batches['batch-1'])
            rec = dict(seq=log.seq + 1, previous=log.head, event='submitted', requestID='job-000001',
                       attemptID='job-000001/attempt-01', payload=payload)
            line = run.canonical_json(dict(record=rec, sha256=run.sha256_bytes(run.canonical_json(rec)))) + b'\n'
            log.staging.write_bytes(line)
            log.file.seek(0, 2)
            log.file.write(line[:30])
            log.file.flush()
        with self.journal() as log:
            self.assertEqual(log.job('job-000001', 'submitted'), payload)
            self.finish(log)
        self.assertEqual(self.api.creates, 2)


class BatchTransportTests(unittest.TestCase):
    """HTTP adapter contract tests use mocked responses only."""

    def test_count_projection_contains_schema_and_reasoning(self):
        """Token counting preserves all input-bearing request fields without generation."""
        api = run.batch_transport.BatchAPI('offline-dummy')
        body = dict(model='gpt-6.1-sol', input='original', reasoning={'effort': 'medium'},
                    text={'format': {'schema': {'type': 'object'}}}, max_output_tokens=32768, store=False)
        with patch.object(api, 'request', return_value=b'{"object":"response.input_tokens","input_tokens":42}') as request:
            self.assertEqual(api.count(body)['input_tokens'], 42)
        args, kwargs = request.call_args
        self.assertEqual(args[:2], ('POST', '/responses/input_tokens'))
        projected = json.loads(args[2])
        self.assertEqual(projected, {k: body[k] for k in ('model', 'input', 'reasoning', 'text')})
        self.assertTrue(kwargs['safe'])

    def test_submission_post_has_no_hidden_retry(self):
        """A lost Batch POST response is left for durable reconciliation."""
        api = run.batch_transport.BatchAPI('offline-dummy')
        with patch.object(run.batch_transport, 'urlopen', side_effect=TimeoutError()) as call:
            with self.assertRaisesRegex(ValueError, 'UNCERTAIN'):
                api.create('file-x', {'run': 'fixture'})
        self.assertEqual(call.call_count, 1)

    def test_capacity_http_rejection_is_distinct_from_uncertain_http(self):
        """Only explicit queued-token errors classify as definitive capacity rejection."""
        from urllib.error import HTTPError
        api = run.batch_transport.BatchAPI('offline-dummy')
        for code, expected in [('token_limit_exceeded', run.batch_transport.CapacityRejected),
                               ('rate_limit_exceeded', run.batch_transport.HTTPFailure)]:
            raw = run.canonical_json({'error': {'code': code}})
            error = HTTPError('https://offline.invalid', 429, 'fixture', {}, io.BytesIO(raw))
            with patch.object(run.batch_transport, 'urlopen', side_effect=error) as call:
                with self.assertRaises(expected) as raised:
                    api.create('file-x', {'run': 'fixture'})
            self.assertEqual(call.call_count, 1)
            self.assertEqual(raised.exception.evidence['status'], 429)

    def test_recovery_listing_paginates(self):
        """Recovery checks all pages instead of concluding absence prematurely."""
        api = run.batch_transport.BatchAPI('offline-dummy')
        with patch.object(api, 'request', side_effect=[b'{"data":[{"id":"a"}],"has_more":true}',
                                                     b'{"data":[{"id":"b"}],"has_more":false}']) as call:
            self.assertEqual(api.listing('batches'), [{'id': 'a'}, {'id': 'b'}])
        self.assertIn('after=a', call.call_args_list[1][0][1])


class BatchNativeTests(unittest.TestCase):
    """Focused real frozen JIT/native contract, no provider calls."""

    def test_transport_only_identity_native_success_and_expired_retry(self):
        """Batch metadata remains truthful and native deterministic acceptance is unchanged."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')):
            paired, stream, journal, parent = run.baseline.dependencies()
            env, routing = stream.load()
            e = parent['requests'][0]
            row = next(r for r in routing['records'] if r['sourceUnitID'] == e['sourceUnitID'])
            menu = next(m for m in row['menus'] if m['passIdentity'] == e['passIdentity'])
            original = stream.reconstruct(env, row, menu, e)
            p = run.variant(original, paired)
            run.verify_variant(p, e, stream)
            for key in ('request', 'schema', 'providerInput'):
                self.assertEqual(p[key], original[key])
            body = deepcopy(original['body'])
            body['model'] = 'gpt-6.1-sol'
            self.assertEqual(body, p['body'])
            item, line = run.input_line(p, 1, stream.fingerprint)
            self.assertEqual(json.loads(line)['body'], p['body'])
            bad = deepcopy(p)
            bad['body']['input'] += 'tampered'
            with self.assertRaises(ValueError):
                run.verify_variant(bad, e, stream)
            raw = json.dumps(dict(candidateNodes=[], candidateEdges=[], evidenceSpans=[], abstentions=[], deferredRecords=[]))
            body = dict(id='offline', status='completed', model='gpt-6.1-sol', service_tier='default', created_at=1,
                        usage=dict(input_tokens=100, output_tokens=10, input_tokens_details={'cached_tokens': 20, 'cache_write_tokens': 10}),
                        output=[dict(type='message', content=[dict(type='output_text', text=raw)])])
            result = dict(custom_id=item['custom_id'], error=None, response=dict(status_code=200, request_id='http-offline', body=body))
            record = run.response_record(result, p, paired, 'offline-batch', 1)
            self.assertAlmostEqual(record['cost']['estimatedUSD'], (70 + 1 + 12.5 + 50)/1e6)
            self.assertEqual(record['providerMetadata']['requestSettings']['executionMode'], 'batch')
            out = run.native_process(p, record, 1, None, paired, stream)
            self.assertTrue(out['processable'])
            run.verify_outcome(p, record, out, 1)
            self.assertEqual(out, run.native_process(p, record, 1, None, paired, stream))
            expired = dict(custom_id=item['custom_id'], response=None, error={'code': 'batch_expired'})
            er = run.response_record(expired, p, paired, 'expired-batch', 1)
            first = run.native_process(p, er, 1, None, paired, stream)
            self.assertTrue(first['retryEligible'])
            run.verify_outcome(p, er, first, 1)
            second = run.native_process(p, record, 2, first['attempt'], paired, stream)
            run.verify_outcome(p, record, second, 2)
            self.assertEqual(second['productionResult']['attemptSelection']['selectedAttemptNumber'], 2)
            http_error = deepcopy(result)
            http_error['response']['status_code'] = 500
            http_error['error'] = {'code': 'server_error'}
            known = run.response_record(http_error, p, paired, 'known-error-batch', 1)
            retry = run.native_process(p, known, 1, None, paired, stream)
            self.assertTrue(retry['retryEligible'])
            run.verify_outcome(p, known, retry, 1)
