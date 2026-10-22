"""Offline delivery-policy regressions; authentic observations are not synthetic evidence."""
from contextlib import contextmanager
from copy import deepcopy
import base64
import json
import unittest
from unittest.mock import patch

from test_full_corpus_gpt61_batch import BatchControllerTests, FakeAPI
from src.extraction.llm.publications import full_corpus_gpt61_batch as run
from src.extraction.llm.publications import batch_recovery as recovery


class RecoveryTests(unittest.TestCase):
    """Real locked journal and mocked transport, with Publications-only recovery enabled."""
    setUpClass = classmethod(BatchControllerTests.setUpClass.__func__)
    verify = BatchControllerTests.verify
    verify_outcome = BatchControllerTests.verify_outcome
    process = BatchControllerTests.process

    def record(self, row, p, bid, n):
        """Keep missing billing usage unknown, including HTTP error response bodies."""
        receipt = run.response_record(row, p, self.paired, bid, n)
        if isinstance(receipt['usage'], dict):
            receipt['cost'] = dict(estimatedUSD=1, basis='reported_cache_details')
        return receipt

    def setUp(self):
        """Use tiny original-queue fixtures and the additive journal subclass."""
        BatchControllerTests.setUp(self)
        self.mf.update(implementationPins={'fixture': 'a' * 64}, queuedTokenLimit=100)
        self.Journal = recovery.journal_type(self.Journal, self.verify_outcome, self.stream.fingerprint)

    @contextmanager
    def journal(self):
        """Activate the prospective policy once, retaining every legacy event."""
        data = run.canonical_json(self.mf) + b'\n'
        with self.Journal(self.root / 'execution.jsonl', data, run.sha256_bytes(data)) as log:
            recovery.migrate(log, self.mf)
            yield log

    def submit(self, log):
        """Dispatch fixture work with real scheduling and no network."""
        with patch.object(run, 'save_status'):
            return run.submit_all(log, self.api, lambda e: deepcopy(self.prepared[e['identity']['requestID']]),
                                  self.native, self.stream.fingerprint)

    def collect(self, log, code=None, process=None):
        """Optionally emit exact nonexecution errors in simulated provider output files."""
        original = self.api.retrieve
        def retrieve(bid):
            remote = original(bid)
            if code:
                fid = remote.get('output_file_id') or remote.get('error_file_id')
                rows = [dict(custom_id=json.loads(line)['custom_id'], response=None,
                             error={'code': code, 'message': 'provider fixture'})
                        for line in self.api.contents[fid].splitlines()]
                if code == 'credit_balance_exhausted':
                    for row in rows:
                        row['response'] = dict(status_code=429, body={'error': row['error']})
                        row['error'] = None
                self.api.contents[fid] = b''.join(run.canonical_json(r) + b'\n' for r in rows)
            return remote
        with patch.object(self.api, 'retrieve', side_effect=retrieve):
            return run.collect_once(log, self.api, process or self.process, self.record)

    def test_nonexecution_delivery_preserves_native_attempt_and_unknown_billing(self):
        """Billing delivery 1 and expiry delivery 2 do not consume scientific attempt 1."""
        with self.journal() as log:
            self.submit(log)
            self.assertEqual(self.collect(log, 'credit_balance_exhausted'), [])
            self.assertEqual(len(log.unknown_usage), 3)
            self.assertEqual(log.native_first, {})
            self.assertFalse(log.recovery_blocked())
            self.assertEqual(self.processed, [])
            original = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log, patch.object(self.api, 'count', side_effect=AssertionError('NO_RECOUNT')):
            with patch.object(run, 'save_status'):
                run.submit_all(log, self.api, lambda e: self.fail('NO_REBUILD'), self.native, self.stream.fingerprint)
            self.assertEqual(self.collect(log, 'batch_expired'), [])
            self.submit(log)
            self.assertEqual(self.collect(log), [])
            self.assertTrue(all(n == 1 for _, n in self.processed))
            self.assertEqual(len(log.receipts), 9)
            self.assertEqual(len(log.unknown_usage), 3)
            self.assertEqual(log.spent, 3)
            self.assertIsNone(run.summary(log)['actualUSD'])
            self.assertTrue(all(s == 'completion' for s in log.state.values()))
            creates, seq = self.api.creates, log.seq
            self.submit(log)
            self.collect(log)
            self.assertEqual((self.api.creates, log.seq), (creates, seq))
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().startswith(original))

    def test_native_retry_limit_and_terminal_failure_isolation(self):
        """Native attempt 2 stays bounded; terminal exceptions do not block unrelated requests."""
        def failure(p, receipt, n, first):
            return dict(cid=receipt['row']['custom_id'], n=n, attempt={'attemptNumber': n},
                        processable=False, retryEligible=n == 1, productionResult=None)
        with self.journal() as log:
            self.submit(log)
            self.collect(log, process=failure)
            self.submit(log)
            self.collect(log, process=failure)
            self.assertEqual(self.api.creates, 2)
            self.submit(log)
            self.assertEqual(self.api.creates, 2)
            self.assertEqual(recovery.recovery_counts(log)['terminalReviewRequired'], 3)
            self.assertFalse(run.dispatch_blocked(log))

    def test_cost_anomaly_still_blocks_later_dispatch(self):
        """Ignoring confirmed nonexecution uncertainty does not disable the relative cost gate."""
        self.mf['queuedTokenLimit'] = 20
        with self.journal() as log:
            self.submit(log)
            self.collect(log, 'credit_balance_exhausted')
            self.submit(log)
            def expensive(row, p, bid, n):
                receipt = self.record(row, p, bid, n)
                receipt['cost']['estimatedUSD'] = 3
                return receipt
            run.collect_once(log, self.api, self.process, expensive)
            self.assertEqual(self.submit(log), 'cost_anomaly_stop')
            self.assertEqual(self.api.creates, 2)

    def test_unknown_errors_are_not_nonexecution(self):
        """An arbitrary missing-usage error remains unresolved execution uncertainty."""
        with self.journal() as log:
            self.submit(log)
            self.collect(log, 'server_error')
            self.assertTrue(log.recovery_blocked())
            self.assertEqual(self.submit(log), 'technical_stop')
            self.assertEqual(self.api.creates, 1)

    def test_nonexecution_requires_exact_evidence_without_model_output(self):
        """An error-like code cannot override returned model output or a success status."""
        row = dict(response=dict(status_code=429, body={'error': {'code': 'credit_balance_exhausted'}}), error=None)
        self.assertEqual(recovery.nonexecution({'row': row}), 'credit_balance_exhausted')
        row['response']['body']['output'] = []
        self.assertIsNone(recovery.nonexecution({'row': row}))
        row['response']['body'].pop('output')
        row['response']['status_code'] = 200
        self.assertIsNone(recovery.nonexecution({'row': row}))

    def test_legacy_receipts_and_both_migrations_replay_without_rewriting(self):
        """Historical UNKNOWN_USAGE outcomes remain intact while new delivery uses native attempt 1."""
        legacy = run.baseline.read(run.OPERATIONAL_COMPATIBILITY)['publicationsLegacyPins']
        self.mf['implementationPins'] = legacy
        data = run.canonical_json(self.mf) + b'\n'
        base = self.Journal.__mro__[1]
        with base(self.root / 'execution.jsonl', data, run.sha256_bytes(data)) as log:
            log.append('implementation_migration', None, dict(version='unsubmitted-upload-repack/1.0',
                       manifestSha256=log.pin, previousImplementationPins=legacy,
                       implementationPins=legacy, maxNewFileBytes=20000000))
            self.submit(log)
            def hold(p, receipt, n, first):
                return dict(cid=receipt['row']['custom_id'], n=n, processable=False, retryEligible=False,
                            productionResult=None, transportHold='UNKNOWN_USAGE')
            self.collect(log, 'credit_balance_exhausted', process=hold)
        prefix = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log:
            self.assertEqual(recovery.recovery_counts(log)['billingRecoverable'], 3)
            self.submit(log)
            self.collect(log)
            self.assertEqual(len(log.accepted), 3)
            self.assertTrue(all(n == 1 for _, n in self.processed))
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().startswith(prefix))
        before = (self.root / 'execution.jsonl').read_bytes()
        result = recovery.preview(self.Journal, self.native, self.root / 'execution.jsonl', data, self.mf)
        self.assertEqual(result['completedProtected'], 3)
        self.assertEqual((self.root / 'execution.jsonl').read_bytes(), before)

    def rejection(self):
        """Return the exact supported HTTP billing error shape."""
        return run.batch_transport.HTTPFailure(400, b'{"error":{"code":"billing_hard_limit_reached"}}')

    def test_creation_billing_rejection_collect_and_recovery(self):
        """job-000034's generic evidence pattern permits one reconciled new creation identity."""
        with self.journal() as log, patch.object(self.api, 'create', side_effect=self.rejection()):
            with self.assertRaisesRegex(ValueError, 'BILLING_UNAVAILABLE'):
                self.submit(log)
            old_intent = log.job('job-000001', 'submit_intent')
            self.assertEqual(self.collect(log), [])
            self.assertEqual(recovery.recovery_counts(log)['expectedUniqueEligible'], 3)
            with self.assertRaisesRegex(ValueError, 'BILLING_UNAVAILABLE'):
                self.submit(log)
            self.assertEqual(self.api.uploads, 1)
        with self.journal() as log:
            self.submit(log)
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(self.api.uploads, 1)
            self.assertNotEqual(log.job('job-000001', 'submit_intent')['metadata'], old_intent['metadata'])
            self.submit(log)
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(self.collect(log), [])

    def test_creation_adopts_existing_remote_before_retry(self):
        """Exact accepted remote identity takes precedence over a persisted rejection."""
        original = self.api.create
        def accepted_then_error(fid, metadata):
            original(fid, metadata)
            raise self.rejection()
        with self.journal() as log, patch.object(self.api, 'create', side_effect=accepted_then_error):
            with self.assertRaises(ValueError):
                self.submit(log)
        with self.journal() as log:
            self.submit(log)
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(self.collect(log), [])

    def test_capacity_rejection_reconciles_before_new_creation(self):
        """Explicit capacity rejection uses the same exact-identity reconciliation policy."""
        error = run.batch_transport.CapacityRejected(429, {'error': {'code': 'token_limit_exceeded'}})
        with self.journal() as log, patch.object(self.api, 'create', side_effect=error):
            with self.assertRaises(run.batch_transport.CapacityRejected):
                self.submit(log)
        with self.journal() as log:
            self.assertEqual(self.collect(log), [])
            self.submit(log)
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(self.api.uploads, 1)

    def test_ambiguous_post_never_blindly_retried(self):
        """No remote match plus network uncertainty still prohibits another mutating POST."""
        with self.journal() as log, patch.object(self.api, 'create', side_effect=OSError('uncertain')):
            with self.assertRaises(OSError):
                self.submit(log)
        with self.journal() as log:
            self.assertEqual(recovery.recovery_counts(log)['categories']['ambiguous_transport'], 3)
            with self.assertRaisesRegex(ValueError, 'UNCERTAIN_SUBMISSION'):
                self.submit(log)
            self.assertEqual(self.api.creates, 0)

    def test_recovery_transition_interruption_does_not_duplicate_delivery(self):
        """Crash after definitive reconciliation and before the next intent resumes once."""
        with self.journal() as log, patch.object(self.api, 'create', side_effect=self.rejection()):
            with self.assertRaises(ValueError):
                self.submit(log)
        with self.journal() as log:
            log.reconcile_creation('job-000001', self.api, True)
        self.api.lose_create = True
        with self.journal() as log:
            with self.assertRaises(OSError):
                self.submit(log)
        with self.journal() as log:
            self.submit(log)
            self.assertEqual(self.api.creates, 1)
            self.assertEqual(self.collect(log), [])

    def test_reported_population_conservation_and_protection(self):
        """Representative synthetic state mirrors the reported totals; no production claim."""
        with self.journal() as log:
            log.entries = {str(i): {} for i in range(10893)}
            log.accepted = {str(i) for i in range(7210)}
            log.offsets = {str(i): {} for i in range(8624)}
            log.tokens = {str(i): 1 for i in range(8624)}
            log.jobs = {'settled': {'submitted': 1, 'settled': 2}, 'rejected': {'submit_intent': 3, 'submission_error': 4}}
            intent = {'metadata': {'fixture': 'job-000034'}}
            error = dict(self.rejection().evidence, intentSha256=run.sha256_bytes(run.canonical_json(intent)))
            payloads = {3: intent, 4: error}
            log.payload_at = lambda off: payloads[off]
            for i in range(7210, 8350):
                rid = str(i); key = rid, 1
                log.current_delivery[rid] = 1
                log.assignments[key] = ('settled', {})
                log.outcomes[key] = 10
                log.latest[rid] = key
                log.outcome_flags[key] = 8344 <= i < 8348
                if i < 8344:
                    log.nonexecutions[key] = 'credit_balance_exhausted'
                    log.unknown_usage.add(key)
            for i in range(8350, 8618):
                log.current_delivery[str(i)] = 1
                log.assignments[str(i), 1] = ('rejected', {})
            result = recovery.recovery_counts(log)
            self.assertEqual(sum(result['categories'].values()), 10893)
            self.assertEqual([result[k] for k in ('completedProtected', 'billingRecoverable', 'nativeRetryEligible',
                'terminalReviewRequired', 'neverSubmitted', 'expectedUniqueEligible')], [7210,1134,4,2,2543,3681])
            self.assertTrue(all(not log.ready(str(i)) for i in range(7210)))
            self.assertEqual(result['categories']['never_prepared'], 2269)


if __name__ == '__main__':
    unittest.main()
