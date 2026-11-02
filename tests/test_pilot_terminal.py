"""Offline terminal gating and durability checks with injected synthetic transport."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from src.extraction.llm import pilot_terminal as runner
from src.extraction.llm.pilot_preflight import canonical, digest, check_schema_limits


class TerminalTests(unittest.TestCase):
    """Never access real credentials, corpora or networks."""
    def setUp(self):
        """Prepare synthetic approval and bytes, not a live approval artifact."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.result = {k:digest(k.encode()) for k in ('semanticRequestSha256','providerEnvelopeSha256','providerInputSha256','schemaSha256')}
        self.result.update(wireBytes=b'{"synthetic":true}',inputBytes=b'input',semanticRequestBytes=b'request')
        now = datetime.now(timezone.utc)
        self.approval = dict(schemaVersion='step12c-terminal-approval/1',authorized=True,approvalID='synthetic',researcher='fixture',
            approvedAt=(now-timedelta(minutes=1)).isoformat(),expiresAt=(now+timedelta(hours=1)).isoformat(),currency='TEST',
            pricingReference='synthetic only',totalCostCap=2,requests={'GH-01':dict(maximumAttempts=1,reservedMaximumCost=1,
                semanticRequestSha256=self.result['semanticRequestSha256'],providerEnvelopeSha256=self.result['providerEnvelopeSha256'])})
        self.response = canonical(dict(id='fake',model='fake',status='completed',usage={'input_tokens':3,'output_tokens':4},
            output=[dict(type='message',content=[dict(type='output_text',text=' {"original":true}\n')])]))

    def run_attempt(self, send, **kwargs):
        """Inject fake key/transport; any accidental network or key lookup fails."""
        raw = canonical(self.approval)
        with patch.object(runner,'load_selected',return_value=deepcopy(self.result)), patch('socket.socket',side_effect=AssertionError('network')):
            return runner.execute(self.root,'GH-01',raw,digest(raw),send=send,key_loader=lambda:'FAKE_TEST_KEY',**kwargs)

    def test_approval_fail_closed_before_dispatch(self):
        """Wrong hashes, missing caps, expiry and unauthorized IDs fail offline."""
        ambiguous = b'{"authorized":false,"authorized":true}'
        with self.assertRaisesRegex(ValueError, 'duplicate_approval_field'):
            runner.verify_approval(ambiguous,digest(ambiguous),'GH-01',self.result)
        raw = canonical(self.approval)
        with self.assertRaises(ValueError):
            runner.verify_approval(raw,'0'*64,'GH-01',self.result)
        for change in ({'authorized':False},{'expiresAt':'2000-01-01T00:00:00Z'}, {'totalCostCap':0}, {'currency':''}):
            approval = {**self.approval,**change}
            raw = canonical(approval)
            with self.assertRaises(ValueError):
                runner.verify_approval(raw,digest(raw),'GH-01',self.result)
        raw = canonical(self.approval)
        with self.assertRaises(ValueError):
            runner.verify_approval(raw,digest(raw),'HUB-01',self.result)

    def test_exact_bytes_raw_preservation_and_no_overwrite(self):
        """Persist raw response before pure extraction, and prevent a second call."""
        calls=[]
        def send(wire,key,timeout):
            """Record only a synthetic invocation."""
            calls.append(wire)
            return 200,self.response
        self.assertEqual(self.run_attempt(send),'response_recorded')
        folder=self.root/'var/study2_step12c/terminal/GH-01'
        self.assertEqual((folder/'response.raw').read_bytes(),self.response)
        self.assertEqual((folder/'provider-envelope.json').read_bytes(),self.result['wireBytes'])
        self.assertEqual((folder/'model-output.utf8').read_bytes(),b' {"original":true}\n')
        self.assertEqual(json.loads((folder/'provider-metadata.json').read_bytes())['usage']['output_tokens'],4)
        self.assertNotIn('FAKE_TEST_KEY',''.join(p.read_text() for p in folder.iterdir()))
        with self.assertRaises(FileExistsError):
            self.run_attempt(send)
        self.assertEqual(len(calls),1)

    def test_progress_and_ambiguous_timeout_blocks_dispatch(self):
        """An elapsed-time deadline stops without a retry or replacement."""
        messages=[]
        def slow(*args):
            """Simulate an uncertain pending request; no provider involved."""
            time.sleep(.1)
            return 200,self.response
        with self.assertRaises(RuntimeError):
            self.run_attempt(slow,timeout=.04,progress_interval=.01,progress=messages.append)
        self.assertTrue(messages)
        self.assertTrue((self.root/'var/study2_step12c/terminal/STOP').exists())
        with self.assertRaisesRegex(ValueError,'dispatch_blocked'):
            self.run_attempt(lambda *args:self.fail('must not dispatch'))

    def test_http_error_preserved_without_retry(self):
        """Complete error response is stored and blocks further dispatch."""
        raw=b'{"error":{"message":"synthetic refusal"}}'
        self.assertEqual(self.run_attempt(lambda *args:(429,raw)),'response_requires_review')
        self.assertEqual((self.root/'var/study2_step12c/terminal/GH-01/response.raw').read_bytes(),raw)
        self.assertTrue((self.root/'var/study2_step12c/terminal/STOP').exists())

    def test_documented_structural_limits(self):
        """Check depth, properties, enum and string limits without remote claims."""
        schema={'type':'object','properties':{'x':{'type':'string'}}}
        self.assertEqual(check_schema_limits(schema)['depth'],1)
        for bad in ({'type':'object','properties':{str(i):{'type':'string'} for i in range(5001)}},
                    {'enum':list(range(1001))}, {'enum':['x'*61+str(i) for i in range(251)]},
                    {'type':'object','properties':{'x'*120001:{'type':'string'}}}):
            with self.assertRaises(ValueError):
                check_schema_limits(bad)
        for _ in range(10):
            schema={'type':'object','properties':{'x':schema}}
        with self.assertRaises(ValueError):
            check_schema_limits(schema)

    def test_cli_dry_run_never_dispatches(self):
        """Dry-run verifies stored input only and cannot touch credentials/transport."""
        def environment(key, default=None):
            """Permit argparse locale defaults, but no credential lookup."""
            if key == 'OPENAI_API_KEY':
                raise AssertionError('credentials forbidden')
            return default
        with patch('sys.argv',['pilot_terminal','dry-run','--request-id','GH-01']), \
             patch.object(runner,'load_selected',return_value=self.result), \
             patch.object(runner,'execute',side_effect=AssertionError('execute forbidden')), \
             patch('os.environ.get',side_effect=environment), \
             patch('builtins.print'):
            runner.main()

    def test_missing_credentials_leave_approved_attempt_available(self):
        """Default Publications loader failure occurs before any attempt state."""
        from src.extraction.llm.publications.openai_provider import OpenAIProviderError
        raw = canonical(self.approval)
        state = self.root / 'var/study2_step12c/terminal'
        with patch.object(runner, 'load_selected', return_value=self.result), \
             patch('src.extraction.llm.publications.openai_provider.load_openai_api_key',
                   side_effect=OpenAIProviderError('OPENAI_API_KEY is unavailable')) as loader, \
             patch('socket.socket', side_effect=AssertionError('network')):
            with self.assertRaises(OpenAIProviderError):
                runner.execute(self.root, 'GH-01', raw, digest(raw),
                               send=lambda *args: self.fail('must not dispatch'))
            loader.assert_called_once_with(env_path=self.root / '.env')
        self.assertFalse(state.exists())
        self.assertEqual(self.run_attempt(lambda *args: (200, self.response)), 'response_recorded')
        self.assertFalse((state / 'STOP').exists())

    def test_default_loader_after_approval_before_attempt(self):
        """Resolve the shared environment/.env behavior only on approved execution."""
        raw = canonical(self.approval)
        calls = []
        state = self.root / 'var/study2_step12c/terminal'

        def load(**kwargs):
            """Stand in for the tested loader without inspecting real credentials."""
            self.assertFalse(state.exists())
            self.assertEqual(kwargs, {'env_path': self.root / '.env'})
            calls.append('credential')
            return 'SYNTHETIC_KEY'

        def send(wire, key, timeout):
            """Check dispatch follows credential resolution and durable preparation."""
            self.assertEqual(calls, ['credential'])
            self.assertEqual(key, 'SYNTHETIC_KEY')
            self.assertEqual((state / 'GH-01/provider-envelope.json').read_bytes(), wire)
            calls.append('dispatch')
            return 200, self.response

        with patch.object(runner, 'load_selected', return_value=self.result), \
             patch('src.extraction.llm.publications.openai_provider.load_openai_api_key', side_effect=load) as loader, \
             patch('socket.socket', side_effect=AssertionError('network')):
            invalid = canonical({**self.approval, 'authorized': False})
            with self.assertRaises(ValueError):
                runner.execute(self.root, 'GH-01', invalid, digest(invalid), send=send)
            loader.assert_not_called()
            self.assertEqual(runner.execute(self.root, 'GH-01', raw, digest(raw), send=send), 'response_recorded')
        self.assertEqual(calls, ['credential', 'dispatch'])
        self.assertNotIn('SYNTHETIC_KEY', ''.join(p.read_text() for p in (state / 'GH-01').iterdir()))
