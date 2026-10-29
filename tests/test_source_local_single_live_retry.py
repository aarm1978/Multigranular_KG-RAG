"""Offline tests of one-dispatch supplemental recovery; sockets are forbidden."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.evaluation import source_local_single_live_retry as r


class SingleRetryTests(unittest.TestCase):
    def setUp(self):
        """Use synthetic prepared inputs and block networking."""
        for name in ('connect', 'connect_ex'):
            p = patch.object(socket.socket, name, side_effect=AssertionError('NO_NETWORK'))
            p.start(); self.addCleanup(p.stop)
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.output = Path(tmp.name) / 'recovery'
        self.prepared = dict(body=dict(model='gpt-6.1-sol', store=False, max_output_tokens=32768,
            input='exact input', reasoning={'effort': 'medium'}, text={'format': {'schema': {}}}),
            semanticRequest={'requestSha256': 'original'})
        self.response = dict(id='resp-test', model='gpt-6.1-sol', status='completed', usage={'output_tokens': 1},
            incomplete_details=None, output=[dict(type='message', status='completed',
                content=[dict(type='output_text', text='{}')])])
        self.client = Mock()
        self.client.responses.create.return_value.model_dump.return_value = self.response

    def run_once(self):
        """Exercise the synthetic dispatch."""
        return r.execute(self.prepared, self.output, self.client, authorized=True)

    def test_exact_envelope_intent_before_post_replay_and_duplicate_block(self):
        """No provider fields change, and replay must finish before usability is recorded."""
        original = copy.deepcopy(self.prepared)
        def create(**kwargs):
            self.assertTrue((self.output / 'intent.json').exists())
            self.assertEqual(kwargs, original['body'])
            return Mock(model_dump=Mock(return_value=self.response))
        self.client.responses.create.side_effect = create
        with patch.object(r.specialized, 'replay', return_value={'projection': {}}) as replay:
            self.assertTrue(self.run_once()['usable'])
            replay.assert_called_once_with(self.prepared, b'{}', expected_request_sha256='original')
        with self.assertRaisesRegex(ValueError, 'PRIOR_INTENT_STOP'): self.run_once()
        self.client.responses.create.assert_called_once()
        self.assertEqual(self.prepared, original)
        self.assertEqual(json.loads((self.output / 'response.json').read_bytes()), self.response)

    def test_uncertain_post_is_permanently_blocked_and_redacted(self):
        """A connection failure preserves intent, safe evidence and prohibits retry."""
        self.client.responses.create.side_effect = OSError(32, 'SECRET')
        with self.assertRaisesRegex(ValueError, 'UNCERTAIN_OUTCOME'): self.run_once()
        with self.assertRaisesRegex(ValueError, 'PRIOR_INTENT_STOP'): self.run_once()
        self.client.responses.create.assert_called_once()
        raw = (self.output / 'outcome.json').read_text()
        self.assertNotIn('SECRET', raw)
        self.assertFalse(json.loads(raw)['usable'])

    def test_incomplete_response_saved_but_not_usable(self):
        """Preserve incomplete output and usage without replay or another dispatch."""
        self.response.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'})
        with patch.object(r.specialized, 'replay') as replay:
            with self.assertRaisesRegex(ValueError, 'NOT_USABLE'): self.run_once()
            replay.assert_not_called()
        self.assertEqual(json.loads((self.output / 'response.json').read_bytes()), self.response)

    def test_failed_semantic_replay_is_not_usable(self):
        """Schema or semantic replay errors cannot mark a supplemental result usable."""
        with patch.object(r.specialized, 'replay', side_effect=ValueError('bad schema')):
            with self.assertRaisesRegex(ValueError, 'NOT_USABLE'): self.run_once()
        self.assertFalse(json.loads((self.output / 'outcome.json').read_bytes())['usable'])

    def test_missing_authorization_and_failed_intent_never_dispatch(self):
        """Authorization and durable intent are prerequisites for any POST."""
        with self.assertRaises(ValueError): r.execute(self.prepared, self.output, self.client)
        with patch.object(r.files, 'seal', side_effect=OSError('disk')):
            with self.assertRaises(OSError): self.run_once()
        self.client.responses.create.assert_not_called()

    def test_cli_sdk_configuration(self):
        """The live entry point disables SDK retries and sets the required timeout."""
        import sys
        import openai
        with patch.object(r, 'load_original', return_value=self.prepared), \
             patch.object(r.files.openai_provider, 'load_openai_api_key', return_value='synthetic'), \
             patch.object(openai, 'OpenAI') as factory, \
             patch.object(r, 'execute', return_value={}) as execute, \
             patch.object(sys, 'argv', ['retry', '--authorize-one-post']), \
             patch('builtins.print'):
            r.main()
        factory.assert_called_once_with(api_key='synthetic', base_url='https://api.openai.com/v1',
                                        timeout=600, max_retries=0)
        execute.assert_called_once()

    def test_queue_drift_stops_offline(self):
        """Reject a modified original queue before accessing any bundle or provider."""
        root = self.output; queue = root / r.QUEUE; queue.mkdir(parents=True)
        (queue / 'queue-manifest.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'QUEUE_DRIFT'): r.load_original(root)


if __name__ == '__main__': unittest.main()
