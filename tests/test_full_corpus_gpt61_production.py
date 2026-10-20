"""Focused offline production-controller tests; no real provider dispatch."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import full_corpus_gpt61_production as run
from src.extraction.llm.publications.resumable_production_journal import journal_class


class ProductionControllerTests(unittest.TestCase):
    """Use real journal framing/locking with small deterministic response fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load only verified local implementations with networking blocked."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')):
            cls.paired, cls.stream, cls.native, cls.parent = run.dependencies()

    def setUp(self) -> None:
        """Create an isolated synthetic two-request queue."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prepared = {}
        self.entries = []
        for rid in ('request-one', 'request-two'):
            p = dict(request={'requestID': rid, 'requestInputSha256': rid}, schema={},
                     body={'model': 'gpt-6.1-sol', 'stream': True}, binding={}, providerInput=b'fixture')
            self.prepared[rid] = p
            self.entries.append(dict(identity=self.stream.fingerprint(p), estimatedCostUSD=1.0))
        self.manifest = dict(generatorPins=self.stream.versions(), requests=self.entries,
                             pricing=run.PRICING, meaningfulSampleRequests=2)
        self.calls = []
        self.process_calls = []
        self.Journal = journal_class(self.native, self.verify_prepared, self.verify_outcome)

    def verify_prepared(self, p, e):
        """Assert exact synthetic bundle preservation."""
        run.require(self.stream.fingerprint(p) == e['identity'], 'FIXTURE_IDENTITY_DRIFT')

    def verify_outcome(self, p, response, outcome, number):
        """Check fixture processing identity without substituting a scientific validator."""
        run.require(outcome['number'] == number and outcome['responseID'] == response['providerResponse']['id'], 'FIXTURE_OUTCOME_DRIFT')

    def journal(self):
        """Open the same manifest and path for every restart."""
        data = run.canonical_json(self.manifest) + b'\n'
        return self.Journal(self.root / 'execution.jsonl', data, run.sha256_bytes(data))

    def transport(self, log, rid, body):
        """Persist a synthetic completed terminal event, with no network call."""
        self.calls.append((rid, log.number(rid)))
        response = dict(id=rid + '-' + str(log.number(rid)), status='completed', model='gpt-6.1-sol',
                        service_tier='default', usage={'input_tokens': 1, 'output_tokens': 1})
        log.append('stream_trace', rid, {'terminalEvent': {'type': 'response.completed', 'response': response}, 'elapsedSeconds': 1.0})
        return response

    def record(self, response, p, elapsed):
        """Use a known synthetic cost for state-machine accounting checks."""
        return dict(providerResponse=response, usage=response['usage'], pricing=run.PRICING,
                    cost={'estimatedUSD': 1.0, 'basis': 'synthetic_fixture'})

    def process(self, p, response, n, first):
        """Preserve deterministic fixture output, marking only explicit incomplete responses retryable."""
        self.process_calls.append((p['request']['requestID'], n))
        return dict(number=n, responseID=response['providerResponse']['id'], attempt={'attemptNumber': n},
                    retryEligible=n == 1 and response['providerResponse']['status'] == 'incomplete',
                    processable=response['providerResponse']['status'] == 'completed', productionResult={'fixture': True})

    def execute(self, log, **overrides):
        """Inject only deterministic local fixtures into the production loop."""
        args = dict(rebuild=lambda e: deepcopy(self.prepared[e['identity']['requestID']]),
                    transport=self.transport, process=self.process, record_response=self.record,
                    bundle=self.native.bundle, fingerprint=self.stream.fingerprint)
        args.update(overrides)
        run.execute(log, self.entries, **args)

    def test_restart_skips_and_preserves_completed_output(self):
        """Same command resumes without callbacks or journal-byte changes for completions."""
        with self.journal() as log:
            self.execute(log)
            self.assertEqual(run.progress(log)['completed'], 2)
            self.assertEqual(log.spent, 2)
        data = (self.root / 'execution.jsonl').read_bytes()
        with self.journal() as log:
            self.execute(log)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.process_calls), 2)
        self.assertEqual(data, (self.root / 'execution.jsonl').read_bytes())

    def test_local_dispatch_preflight_failure_remains_safe_to_resume(self):
        """Missing local credentials must not fabricate an uncertain provider attempt."""
        def unavailable():
            raise ValueError('LOCAL_CREDENTIAL_UNAVAILABLE')
        with self.assertRaisesRegex(ValueError, 'LOCAL_CREDENTIAL'), self.journal() as log:
            self.execute(log, prepare_dispatch=unavailable)
        with self.journal() as log:
            self.assertEqual(log.state['request-one'], 'prepared')
            self.assertFalse(log.unknown_usage)
            self.execute(log)
        self.assertEqual(len(self.calls), 2)

    def test_two_incomplete_attempts_stop_without_third_dispatch(self):
        """Retry exhaustion remains a technical STOP across restarts."""
        def incomplete(log, rid, body):
            self.calls.append((rid, log.number(rid)))
            response = dict(id='incomplete-' + str(log.number(rid)), status='incomplete',
                            model='gpt-6.1-sol', service_tier='default', usage={})
            log.append('stream_trace', rid, {'terminalEvent': {'type': 'response.incomplete', 'response': response}})
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'NATIVE_TERMINAL_PROCESSING_FAILURE_STOP'), self.journal() as log:
                self.execute(log, transport=incomplete)
        self.assertEqual(self.calls, [('request-one', 1), ('request-one', 2)])

    def test_recover_completed_terminal_before_processing_without_redispatch(self):
        """A crash after durable response.completed is recovered as the same attempt."""
        def interrupted(log, rid, body):
            self.transport(log, rid, body)
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt), self.journal() as log:
            self.execute(log, transport=interrupted)
        with self.journal() as log:
            self.execute(log)
            self.assertEqual(log.spent, 2)
        self.assertEqual(self.calls, [('request-one', 1), ('request-two', 1)])

    def test_completed_stream_validation_failure_remains_stop(self):
        """A terminal event must not override the transport's subsequent validation failure."""
        def rejected(log, rid, body):
            self.transport(log, rid, body)
            log.append('stream_trace', rid, {'type': 'transport_failure'})
            raise ValueError('STREAM_STOP_FAILURE')
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'COMPLETED_STREAM_VALIDATION_FAILURE_STOP'), self.journal() as log:
                self.execute(log, transport=rejected)
        self.assertEqual(self.calls, [('request-one', 1)])
        self.assertFalse(self.process_calls)

    def test_recover_persisted_response_before_native_outcome(self):
        """Native processing resumes from persisted evidence rather than a new response."""
        with self.assertRaises(RuntimeError), self.journal() as log:
            self.execute(log, process=lambda *args: (_ for _ in ()).throw(RuntimeError('interrupted')))
        with self.journal() as log:
            self.execute(log)
        self.assertEqual(len(self.calls), 2)

    def test_incomplete_response_gets_one_same_request_retry_and_cost(self):
        """A durable incomplete attempt retains usage and permits at most attempt two."""
        def incomplete(log, rid, body):
            if rid == 'request-one' and log.number(rid) == 1:
                self.calls.append((rid, 1))
                response = dict(id='incomplete', status='incomplete', model='gpt-6.1-sol', service_tier='default', usage={})
                log.append('stream_trace', rid, {'terminalEvent': {'type': 'response.incomplete', 'response': response}})
                raise ValueError('transport rejected incomplete')
            return self.transport(log, rid, body)
        with self.journal() as log:
            self.execute(log, transport=incomplete)
            self.assertEqual(log.spent, 3)
            self.assertEqual(log.estimated_processed, 2)
            self.assertEqual(log.number('request-one'), 2)
        self.assertEqual(self.calls, [('request-one', 1), ('request-one', 2), ('request-two', 1)])
        with self.journal() as log:
            self.execute(log)
        self.assertEqual(len(self.calls), 3)

    def test_uncertain_attempt_never_silently_redispatches(self):
        """No terminal evidence remains an explicit STOP across restarts."""
        with self.assertRaisesRegex(ValueError, 'UNCERTAIN'), self.journal() as log:
            self.execute(log, transport=lambda *args: (_ for _ in ()).throw(OSError('timeout')))
        with self.assertRaisesRegex(ValueError, 'UNCERTAIN'), self.journal() as log:
            self.execute(log)
        self.assertEqual(self.calls, [])

    def test_cost_anomaly_before_next_dispatch_survives_restart(self):
        """The revised relative stop uses total retry-inclusive cost, never an absolute budget."""
        self.manifest['meaningfulSampleRequests'] = 1
        def expensive(*args):
            row = self.record(*args)
            row['cost']['estimatedUSD'] = 3
            return row
        with self.journal() as log:
            self.execute(log, record_response=expensive)
            self.assertTrue(run.anomaly(log))
            self.assertEqual(run.progress(log)['completed'], 1)
        with self.journal() as log:
            self.execute(log)
        self.assertEqual(self.calls, [('request-one', 1)])

    def test_staging_recovery_and_incomplete_temporary_discard(self):
        """Complete staged bytes repair a torn append; only incomplete staging is discarded."""
        with self.journal() as log:
            p = self.prepared['request-one']
            payload = self.native.bundle(p)
            payload['executionIdentity'] = self.stream.fingerprint(p)
            log.append('prepared', 'request-one', payload)
            rec = dict(seq=log.seq + 1, previous=log.head, event='dispatch_intent', requestID='request-one',
                       attemptID='request-one/attempt-01', payload=dict(identity=self.stream.fingerprint(p), unixTime=time.time()))
        data = run.canonical_json(dict(record=rec, sha256=run.sha256_bytes(run.canonical_json(rec)))) + b'\n'
        (self.root / 'pending-event.json').write_bytes(data)
        with (self.root / 'execution.jsonl').open('ab') as handle:
            handle.write(data[:len(data)//2])
        with self.journal() as log:
            self.assertEqual(log.state['request-one'], 'dispatch_intent')
        self.assertTrue((self.root / 'execution.jsonl').read_bytes().endswith(data))
        before = (self.root / 'execution.jsonl').read_bytes()
        (self.root / 'pending-event.json').write_bytes(b'{partial')
        with self.journal():
            pass
        self.assertEqual((self.root / 'execution.jsonl').read_bytes(), before)
        self.assertFalse((self.root / 'pending-event.json').exists())

    def test_lock_and_journal_corruption_stop(self):
        """A second writer and malformed committed history remain fail closed."""
        with self.journal():
            with self.assertRaises(BlockingIOError):
                with self.journal():
                    pass
        with (self.root / 'execution.jsonl').open('ab') as handle:
            handle.write(b'{torn')
        before = (self.root / 'execution.jsonl').read_bytes()
        with self.assertRaisesRegex(ValueError, 'TRUNCATED_JOURNAL'):
            with self.journal():
                pass
        self.assertEqual((self.root / 'execution.jsonl').read_bytes(), before)

    def test_missing_usage_blocks_further_dispatch(self):
        """Unknown cost is never silently counted as a zero-cost completed request."""
        def unknown(*args):
            row = self.record(*args)
            row['cost']['estimatedUSD'] = None
            return row
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_USAGE'), self.journal() as log:
            self.execute(log, record_response=unknown)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_USAGE'), self.journal() as log:
            self.execute(log)
        self.assertEqual(len(self.calls), 1)


class NativeModelContractTests(unittest.TestCase):
    """One real frozen JIT request through the reused native model adapter, offline."""

    def test_jit_model_identity_native_retry_and_determinism(self):
        """No scientific content changes; native retry retains truthful attempt/model provenance."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')):
            paired, stream, journal, parent = run.dependencies()
            env, routing = stream.load()
            e = parent['requests'][0]
            row = next(r for r in routing['records'] if r['sourceUnitID'] == e['sourceUnitID'])
            menu = next(m for m in row['menus'] if m['passIdentity'] == e['passIdentity'])
            original = stream.reconstruct(env, row, menu, e)
            p = run.model_variant(original, paired)
            run.verify_variant(p, e, stream)
            self.assertEqual(p['request'], original['request'])
            self.assertEqual(p['schema'], original['schema'])
            self.assertEqual(p['providerInput'], original['providerInput'])
            bad = deepcopy(p)
            bad['body']['input'] += 'changed'
            with self.assertRaisesRegex(ValueError, 'BINDING_DRIFT'):
                run.verify_variant(bad, e, stream)
            raw = json.dumps(dict(candidateNodes=[], candidateEdges=[], evidenceSpans=[], abstentions=[], deferredRecords=[]))
            response = dict(id='offline-fixture', status='completed', model='gpt-6.1-sol', service_tier='default', created_at=1,
                            usage=dict(input_tokens=100, output_tokens=10, input_tokens_details={'cached_tokens': 0, 'cache_write_tokens': 0}),
                            output=[dict(type='message', content=[dict(type='output_text', text=raw)])])
            record = run.response_record(response, p, paired, 1.0)
            first = run.process_native(p, record, 1, None, paired, stream)
            run.verify_outcome(p, record, first, 1)
            self.assertTrue(first['processable'])
            self.assertEqual(first, run.process_native(p, record, 1, None, paired, stream))
            incomplete = deepcopy(response)
            incomplete.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
            failed = run.process_native(p, run.response_record(incomplete, p, paired, 1.0), 1, None, paired, stream)
            self.assertTrue(failed['retryEligible'])
            retried = run.process_native(p, record, 2, failed['attempt'], paired, stream)
            self.assertEqual(retried['productionResult']['attemptSelection']['selectedAttemptNumber'], 2)
            self.assertEqual(retried['attempt']['requestedModel'], 'gpt-6.1-sol')
            run.verify_outcome(p, record, retried, 2)
