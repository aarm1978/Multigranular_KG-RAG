"""Synthetic T1/T2 authorization/persistence/STOP checks; network prohibited."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.extraction.llm import compatibility_smoke as smoke
from src.extraction.llm.pilot_preflight import canonical, digest


class CompatibilitySmokeTests(unittest.TestCase):
    """Test the fixed three-attempt shell without any real credentials or calls."""

    def setUp(self):
        """Create a synthetic pinned bundle and an explicitly synthetic approval."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rows, self.files = [], {}
        for rid, family in zip(smoke.IDS, smoke.FAMILIES):
            envelope = canonical({'model': 'gpt-5.6-sol', 'input': '{}', 'reasoning': {'effort': 'medium'},
                                  'max_output_tokens': 100, 'store': False})
            row = {'requestID': rid, 'family': family, 'requestVersion': 'synthetic-request/1',
                **{k: digest((rid+k).encode()) for k in smoke.PINS},
                'modelSettings': {'model': 'gpt-5.6-sol', 'reasoning': {'effort': 'medium'},
                                  'max_output_tokens': 100, 'store': False},
                'contextAllowance': {'inputTokenAllowance': 1000, 'providerOverheadTokenAllowance': 10,
                                     'historicalPlanningContextTokenLimit': 2000}, 'outputTokenCeiling': 100}
            row['providerEnvelopeSha256'] = digest(envelope)
            self.rows.append(row)
            self.files[rid] = {'provider-envelope.json': envelope,
                              'canonical-schema.json': canonical({'type': 'object'})}
        self.manifest = {'requests': self.rows}
        path = self.root / smoke.MANIFEST
        path.parent.mkdir(parents=True)
        path.write_bytes(canonical(self.manifest))
        self.approval = smoke.approval_draft(self.manifest)
        now = datetime.now(timezone.utc)
        self.approval.update(authorized=True, approvalID='SYNTHETIC-ONLY', researcher='Synthetic Test',
            approvedAt=(now-timedelta(minutes=1)).isoformat(), expiresAt=(now+timedelta(hours=1)).isoformat(),
            pricingReference='synthetic test rates, not provider prices', inputUSDPerMillionTokens='1',
            outputUSDPerMillionTokens='2', totalCostCap='3')
        for row in self.approval['requests'].values():
            row['reservedMaximumCost'] = '1'
        self.real_loader = smoke.load_bundle
        self.loader = patch.object(smoke, 'load_bundle', return_value=(self.manifest, self.files)).start()
        self.addCleanup(patch.stopall)
        patch('socket.socket', side_effect=AssertionError('REAL NETWORK FORBIDDEN')).start()
        patch.object(smoke, 'replay_inputs', return_value={}).start()
        self.replay = patch.object(smoke, 'replay_and_project', side_effect=self.synthetic_replay).start()
        self.send = Mock(side_effect=self.response)
        self.keys = Mock(return_value='synthetic-secret-never-persist')

    def synthetic_replay(self, output, **kwargs):
        """Return a minimal synthetic processing result, not scientific evidence."""
        original = {'status': 'replay_completed', 'finalRecords': []}
        record = {'status': 'projection_completed', 'originalReplay': original, 'projectionSha256': digest(b'projection')}
        wire = canonical(record)
        return SimpleNamespace(report_json=wire.decode(), report_sha256=digest(wire), to_record=lambda: deepcopy(record))

    def response(self, wire, key, timeout):
        """Check that the durable intent exists before the fake network boundary."""
        index = self.send.call_count - 1
        rid = smoke.IDS[index]
        attempt = self.root / smoke.STATE / rid
        intent = json.loads((attempt / 'intent.json').read_bytes())
        self.assertEqual(intent['providerEnvelopeSha256'], digest(wire))
        self.assertEqual(wire, self.files[rid]['provider-envelope.json'])
        self.assertEqual(intent['attempt'], 1)
        return 200, canonical({'id': 'synthetic-response-'+rid, 'model': 'gpt-5.6-sol', 'status': 'completed',
            'created_at': 0, 'usage': {'input_tokens': 10, 'output_tokens': 5},
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{}'}]}]})

    def execute(self, approval=None):
        """Always inject synthetic transport and credential loading explicitly."""
        raw = canonical(self.approval if approval is None else approval)
        return smoke.execute(self.root, raw, digest(raw), send=self.send, key_loader=self.keys)

    def test_authorization_defaults_and_hash_expiry_budget_guards(self):
        """Drafts, stale pins, invalid dates and insufficient budgets cannot send."""
        invalid = [smoke.approval_draft(self.manifest)]
        for key, value in [('authorized', False), ('manifestSha256', 'wrong'), ('harnessSha256', 'wrong'),
                           ('expiresAt', '2000-01-01T00:00:00+00:00'), ('totalCostCap', '2'),
                           ('totalCostCap', 'NaN'), ('inputUSDPerMillionTokens', True)]:
            row = deepcopy(self.approval); row[key] = value; invalid.append(row)
        for key, value in [('attempts', 2), ('attempts', True), ('providerEnvelopeSha256', 'wrong'),
                           ('semanticRequestSha256', 'wrong'), ('reservedMaximumCost', '0.000001'),
                           ('inputTokenAllowance', 1), ('contextTokenLimit', 1), ('outputTokenCeiling', 101)]:
            row = deepcopy(self.approval); row['requests'][smoke.IDS[0]][key] = value; invalid.append(row)
        for approval in invalid:
            with self.subTest(approval=approval), self.assertRaises((ValueError, TypeError)):
                self.execute(approval)
        with self.assertRaises(ValueError):
            smoke.execute(self.root, canonical(self.approval), 'wrong', send=self.send, key_loader=self.keys)
        self.send.assert_not_called(); self.keys.assert_not_called()
        self.assertFalse((self.root / smoke.STATE).exists())

    def test_success_persists_all_associations_and_never_redispatches(self):
        """Three sequential sends leave all raw/provenance/replay artifacts durable."""
        with patch.object(smoke, 'sync_directory', wraps=smoke.sync_directory) as synced:
            self.execute()
        self.assertEqual(self.send.call_count, 3)
        self.assertGreater(synced.call_count, 20)
        for rid in smoke.IDS:
            folder = self.root / smoke.STATE / rid
            for name in ('intent.json', 'response.raw', 'http-result.json', 'provider-metadata.json',
                         'model-output.utf8', 'replay-report.json', 'acceptance-report.json',
                         'result-association.json', 'cost-record.json', 'schema-check.json', 'completed.json'):
                self.assertTrue((folder / name).exists(), name)
            association = json.loads((folder / 'result-association.json').read_bytes())
            self.assertEqual(association['responseSha256'], digest((folder / 'response.raw').read_bytes()))
        self.approval['approvalID'] = 'ANOTHER-SYNTHETIC-APPROVAL'
        with self.assertRaisesRegex(ValueError, 'no_redispatch'):
            self.execute()
        self.assertEqual(self.send.call_count, 3)
        self.assertNotIn('synthetic-secret-never-persist', ''.join(p.read_text() for p in (self.root / smoke.STATE).rglob('*') if p.is_file()))

    def test_uncertain_transport_stops_and_consumes_batch(self):
        """Timeout or interruption leaves intent, STOP and a permanent no-resend barrier."""
        self.send.side_effect = TimeoutError('uncertain')
        with self.assertRaises(RuntimeError): self.execute()
        self.assertTrue((self.root / smoke.STATE / 'STOP').exists())
        self.assertTrue((self.root / smoke.STATE / smoke.IDS[0] / 'intent.json').exists())
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.send.call_count, 1)

    def test_persistence_failure_before_send_consumes_batch_without_network(self):
        """An unsaved intent is never sent; failed attempts cannot be started again."""
        original = smoke.save
        def fail_intent(path, raw):
            """Inject a disk error at the irreversible-boundary journal."""
            if path.name == 'intent.json': raise OSError('disk')
            original(path, raw)
        with patch.object(smoke, 'save', side_effect=fail_intent), self.assertRaises(RuntimeError): self.execute()
        self.send.assert_not_called()
        with self.assertRaises(ValueError): self.execute()

    def test_raw_persistence_failure_after_send_stops_without_retry(self):
        """Losing a response write leaves an uncertain intent, never a fresh attempt."""
        original = smoke.save
        def fail_raw(path, raw):
            """Simulate storage failure after the one approved POST."""
            if path.name == 'response.raw': raise OSError('disk')
            original(path, raw)
        with patch.object(smoke, 'save', side_effect=fail_raw), self.assertRaises(RuntimeError): self.execute()
        self.assertEqual(self.send.call_count, 1)
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.send.call_count, 1)

    def test_http_failure_retains_raw_and_stops_following_requests(self):
        """HTTP failures preserve genuine bytes and status before halting the batch."""
        self.send.side_effect = lambda *args: (400, b'{"error":{"message":"synthetic schema failure"}}')
        with self.assertRaises(RuntimeError): self.execute()
        folder = self.root / smoke.STATE / smoke.IDS[0]
        self.assertTrue((folder / 'response.raw').exists())
        self.assertTrue((folder / 'provider-metadata.json').exists())
        self.assertEqual(self.send.call_count, 1)

    def test_bad_json_and_processing_failure_stop(self):
        """Malformed provider JSON is preserved; processing failure never permits the next send."""
        self.send.side_effect = lambda *args: (200, b'{')
        with self.assertRaises(RuntimeError): self.execute()
        self.assertEqual((self.root / smoke.STATE / smoke.IDS[0] / 'response.raw').read_bytes(), b'{')
        self.assertEqual(self.send.call_count, 1)

    def test_missing_usage_stops_after_replay_preservation(self):
        """Missing cost/usage evidence blocks continuation even for processable output."""
        def missing(*args):
            """Use valid fake output with absent usage."""
            status, raw = self.response(*args)
            parsed = json.loads(raw); del parsed['usage']
            return status, canonical(parsed)
        self.send.side_effect = missing
        with self.assertRaises(RuntimeError): self.execute()
        self.assertTrue((self.root / smoke.STATE / smoke.IDS[0] / 'acceptance-report.json').exists())
        self.assertEqual(self.send.call_count, 1)

    def test_pin_drift_before_second_send_stops(self):
        """A changed pin after the first response cannot permit another dispatch."""
        self.loader.side_effect = [(self.manifest, self.files), (self.manifest, self.files), ValueError('pin drift')]
        with self.assertRaises(RuntimeError): self.execute()
        self.assertEqual(self.send.call_count, 1)
        self.assertTrue((self.root / smoke.STATE / 'STOP').exists())

    def test_external_stop_between_intent_and_send_is_respected(self):
        """A STOP file arriving during persistence prevents the first POST."""
        original = smoke.persist
        def stop_after_intent(path, raw):
            """Model an operator STOP at the pre-send boundary."""
            original(path, raw)
            if path.name == 'intent.json':
                original(self.root / smoke.STATE / 'STOP', b'operator stop')
        with patch.object(smoke, 'persist', side_effect=stop_after_intent), self.assertRaises(RuntimeError): self.execute()
        self.send.assert_not_called()

    def test_existing_crash_directory_blocks_dispatch(self):
        """Even a partial empty run claim is an uncertain outcome, not permission."""
        (self.root / smoke.STATE).mkdir(parents=True)
        with self.assertRaises(ValueError): self.execute()
        self.send.assert_not_called(); self.keys.assert_not_called()

    def test_replay_failure_persists_results_before_stop(self):
        """Original parsing/acceptance failures cannot be bypassed by HTTP success."""
        original = self.synthetic_replay
        def failed(*args, **kwargs):
            """Supply an explicitly blocked synthetic replay."""
            result = original(*args, **kwargs).to_record()
            result['status'] = 'processing_blocked'
            wire = canonical(result)
            return SimpleNamespace(report_json=wire.decode(), report_sha256=digest(wire), to_record=lambda: result)
        self.replay.side_effect = failed
        with self.assertRaises(RuntimeError): self.execute()
        self.assertTrue((self.root / smoke.STATE / smoke.IDS[0] / 'acceptance-report.json').exists())
        self.assertEqual(self.send.call_count, 1)

    def test_real_replay_and_acceptance_integration_with_synthetic_source(self):
        """Exercise unchanged HydroShare replay/conformance with fake provider bytes."""
        import test_datasets_semantic_offline_pipeline as fixtures
        from src.extraction.llm.datasets.request_contract import build_request
        from src.extraction.llm.construction_acceptance import replay_and_project
        fixture = fixtures.OfflineReplayTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = build_request(**fixture.inputs)
        row = deepcopy(self.rows[0]); row['semanticRequestSha256'] = request['requestSha256']
        attempt = self.root / 'integration'; attempt.mkdir()
        payload = fixture.payload()
        raw = canonical({'id': 'synthetic-integration', 'model': 'gpt-5.6-sol', 'status': 'completed',
            'usage': {'input_tokens': 10, 'output_tokens': 5},
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': canonical(payload).decode()}]}]})
        self.replay.side_effect = replay_and_project
        with patch.object(smoke, 'replay_inputs', return_value=fixture.inputs):
            smoke.record_response(self.root, attempt, row, self.files[smoke.IDS[0]], 200, raw, self.approval)
        result = json.loads((attempt / 'acceptance-report.json').read_bytes())
        replay = json.loads((attempt / 'replay-report.json').read_bytes())
        self.assertEqual(replay['requestAssociation'], 'matched_caller_supplied_digest')
        self.assertEqual(replay['expectedRequestSha256'], request['requestSha256'])
        self.assertEqual(result['status'], 'projection_completed')
        self.assertEqual(len(result['projection']['nodes']), 1)
        self.assertEqual(len(result['projection']['edges']), 1)
        self.send.assert_not_called()

    def test_schema_nonconformance_stops_after_preserving_results(self):
        """A processable but structurally nonconformant response cannot continue."""
        self.files[smoke.IDS[0]]['canonical-schema.json'] = canonical({'type': 'object', 'required': ['missing']})
        with self.assertRaises(RuntimeError): self.execute()
        folder = self.root / smoke.STATE / smoke.IDS[0]
        self.assertFalse(json.loads((folder / 'schema-check.json').read_bytes())['canonicalSchemaConformant'])
        self.assertTrue((folder / 'acceptance-report.json').exists())
        self.assertEqual(self.send.call_count, 1)

    def test_real_pin_loader_rejects_tampered_manifest_without_dispatch(self):
        """Use the actual fixed-digest loader, not the synthetic bundle mock."""
        with patch.object(smoke, 'load_bundle', self.real_loader), self.assertRaisesRegex(ValueError, 'pinned_bytes_changed'):
            self.execute()
        self.send.assert_not_called(); self.keys.assert_not_called()

    def test_completed_response_with_incomplete_details_stops(self):
        """Reuse the provider validator so completed status cannot mask truncation."""
        def incomplete(*args):
            """Supply inconsistent fake completion metadata."""
            status, raw = self.response(*args)
            parsed = json.loads(raw); parsed['incomplete_details'] = {'reason': 'max_output_tokens'}
            return status, canonical(parsed)
        self.send.side_effect = incomplete
        with self.assertRaises(RuntimeError): self.execute()
        self.assertTrue((self.root / smoke.STATE / smoke.IDS[0] / 'provider-metadata.json').exists())
        self.assertEqual(self.send.call_count, 1)
