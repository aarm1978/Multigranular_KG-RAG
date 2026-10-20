"""Focused offline tests for model-only historical Human Core extraction."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import human_core_n5_gpt61_extraction as runner


class HistoricalN5Tests(unittest.TestCase):
    """Protect exact scope, provenance, original processing and transport boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        """Reconstruct five requests once, with all network sockets blocked."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
            cls.manifest, cls.prepared = runner.verify()

    def test_exact_five_model_only_bodies(self) -> None:
        """Every provider body differs only by model and stream; identities remain frozen."""
        self.assertEqual(tuple(p['request']['primarySourceUnitID'] for p in self.prepared), runner.UNITS)
        for entry, p in zip(self.manifest['requests'], self.prepared):
            old = runner.read(runner.historical.DEFAULT_LIVE_ROOT / 'requests' / entry['requestID'] / 'attempt-01/provider_request.json')
            expected = deepcopy(old)
            expected.update(model=runner.MODEL, stream=True)
            self.assertEqual(p['body'], expected)
            self.assertEqual(p['request']['requestInputSha256'], entry['requestInputSha256'])
            self.assertEqual(p['request']['authorities']['ontology']['specSha256'], runner.ONTOLOGY_SHA)

    def test_original_processing_truthful_model_and_no_global_mutation(self) -> None:
        """Synthetic output traverses unchanged parser/validator/acceptance, with new metadata."""
        p = self.prepared[0]
        raw = json.dumps(dict(candidateNodes=[], candidateEdges=[], evidenceSpans=[], abstentions=[], deferredRecords=[])).encode()
        response = dict(id='synthetic-offline', model=runner.MODEL, status='completed', created_at=1,
                        usage=dict(input_tokens=100, output_tokens=10, total_tokens=110))
        metadata = runner.provider.provider_response_record(response, p['body'], raw, execution_mode='offline_fixture')
        old_path = runner.validator.ONTOLOGY_SPEC_PATH
        with tempfile.TemporaryDirectory() as directory, patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
            root = Path(directory)
            result = runner.execute_one(p, root, lambda body, budget: dict(rawOutput=raw, providerMetadata=metadata, providerResponse=response))
            self.assertEqual(result['attemptSelection']['selectedAttemptNumber'], 1)
            lifecycle = runner.read(root / 'attempt-01/lifecycle.json')
            self.assertEqual(lifecycle['requestedModel'], runner.MODEL)
            parsed = runner.read(root / 'attempt-01/parsed_candidate.json')
            self.assertIn(runner.MODEL, json.dumps(parsed))
            self.assertNotIn('gpt-5.6-sol', json.dumps(parsed))
            self.assertEqual((root / 'attempt-01/raw_model_output.json').read_bytes(), raw)
        self.assertEqual(runner.production.REQUESTED_MODEL, 'gpt-5.6-sol')
        self.assertEqual(runner.validator.ONTOLOGY_SPEC_PATH, old_path)

    def test_retry_never_dispatches(self) -> None:
        """Malformed output can request a native retry but cannot trigger another call."""
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'RETRY_REQUIRES'):
                runner.execute_one(self.prepared[0], Path(directory), lambda body, budget: calls.append(body) or b'not json')
        self.assertEqual(len(calls), 1)

    def test_drift_rejected(self) -> None:
        """The original frozen membership check and dependency pins remain fail closed."""
        record = deepcopy(runner.records()[0])
        record['requestInputSha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'NOT_FROZEN_SUBSET_MEMBER'):
            runner.rebuild(record)
        with self.assertRaisesRegex(ValueError, 'PIN_DRIFT'):
            runner.verify_pins({str(Path(runner.__file__).relative_to(runner.ROOT)): '0' * 64})

    def test_mocked_live_five_resume_and_uncertain_stop(self) -> None:
        """Mock the transport, exercise all five dispatches, durable resume and STOP."""
        raw = json.dumps(dict(candidateNodes=[], candidateEdges=[], evidenceSpans=[], abstentions=[], deferredRecords=[]))
        calls = []

        def transport(provider, log, rid, key, body):
            """Return a synthetic completed response without any network access."""
            calls.append(rid)
            return dict(id='fixture-' + rid, model=runner.MODEL, status='completed', created_at=1,
                        usage=dict(input_tokens=100, output_tokens=10, total_tokens=110),
                        output=[dict(type='message', content=[dict(type='output_text', text=raw)])])

        with tempfile.TemporaryDirectory(dir=runner.LOCAL) as directory:
            local = Path(directory) / 'local'
            output = Path(directory) / 'output'
            local.mkdir()
            (local / 'ontology_v0.1.5.yaml').write_bytes(runner.ontology_bytes())
            runner.save(local / 'dependencies.json', {})
            runner.save(local / 'preservation.json', {})
            with patch.object(runner, 'LOCAL', local), patch.object(runner, 'OUTPUT', output), \
                 patch.object(runner, 'verify', return_value=(self.manifest, self.prepared)), \
                 patch.object(runner, 'streaming_adapter', return_value=runner.SimpleNamespace(transport=transport)), \
                 patch.object(runner.provider, 'load_openai_api_key', return_value='offline-fixture'), \
                 patch.object(socket, 'socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):
                runner.execute_live()
                self.assertEqual(len(calls), 5)
                runner.execute_live()
                self.assertEqual(len(calls), 5)
                first = self.prepared[0]['request']['requestID']
                (output / (first + '.json')).unlink()
                with self.assertRaisesRegex(ValueError, 'UNCERTAIN_OR_UNEXPORTED'):
                    runner.execute_live()
                self.assertEqual(len(calls), 5)

    def test_stream_completion_and_partial_failure(self) -> None:
        """Reuse proven SSE parser: exact completed text required; partial text is never accepted."""
        adapter = runner.streaming_adapter()
        response = dict(id='synthetic', status='completed', output=[dict(content=[dict(text='{}')])])
        events = [dict(type='response.output_text.delta', response_id='synthetic', sequence_number=1,
                       output_index=0, content_index=0, delta='{}'),
                  dict(type='response.completed', sequence_number=2, response=response)]
        lines = []
        for event in events:
            lines.extend([('data: ' + json.dumps(event) + '\n').encode(), b'\n'])
        self.assertEqual(adapter.consume(lines, lambda _: None), response)
        with self.assertRaisesRegex(ValueError, 'WITHOUT_COMPLETED'):
            adapter.consume(lines[:2], lambda _: None)
        bad = deepcopy(events)
        bad[1]['response']['output'][0]['content'][0]['text'] = 'changed'
        lines = [line for event in bad for line in [('data: ' + json.dumps(event) + '\n').encode(), b'\n']]
        with self.assertRaisesRegex(ValueError, 'DELTA_COMPLETED_TEXT_MISMATCH'):
            adapter.consume(lines, lambda _: None)


if __name__ == '__main__':
    unittest.main()
