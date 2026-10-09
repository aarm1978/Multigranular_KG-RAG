"""Focused offline wave tests: synthetic transport only, never real credentials."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import pilot_wave as wave
from src.extraction.llm import pilot_terminal as terminal
from src.extraction.llm.pilot_preflight import canonical, digest


class WaveTests(unittest.TestCase):
    """Exercise complete-wave approvals and the existing durable one-request executor."""

    def setUp(self):
        """Build only temporary synthetic preflights and fake credentials."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.calls = []
        self.results = {}
        for rid in wave.REQUEST_IDS:
            result = dict(wireBytes=rid.encode(), inputBytes=b'input', semanticRequestBytes=b'semantic',
                schemaSha256=digest(b'schema'), providerEnvelopeSha256=digest(rid.encode()),
                providerInputSha256=digest(b'input'), semanticRequestSha256=digest(b'semantic'),
                requestVersion=('hydroshare-request/1.1.0' if rid.startswith('HS') else 'github-request/1.0.0' if rid.startswith('GH') else 'ciroh_hub-request/1.0.0'),
                providerInputProjectionVersion='github-provider-input/1.0.0' if rid.startswith('GH') and rid != 'GH-01' else None,
                promptIdentifier='clarification' if rid.startswith('HS') else None,
                calibrationManifestSha256=wave.MANIFEST_SHA256, calibrationRequestID=rid,
                calibrationWave=wave.wave_for(rid), conservativeInputTokenAllowance=100)
            self.results[rid] = result
        self.addCleanup(patch.stopall)
        patch.object(terminal, 'load_selected', side_effect=lambda root, rid: deepcopy(self.results[rid])).start()
        patch('socket.create_connection', side_effect=AssertionError('network forbidden')).start()
        patch('src.extraction.llm.publications.openai_provider.load_openai_api_key',
              side_effect=AssertionError('real credentials forbidden')).start()

    def approval(self, name='A'):
        """Authorize synthetic fixtures only; never write researcher authorization."""
        value = wave.prepare_wave_a(self.root)
        if name != 'A':
            template = deepcopy(value['requests']['GH-02'])
            value['requests'] = {rid: {**template, **{k:self.results[rid][k] for k in wave.HASH_VERSION_FIELDS}, 'wave':name}
                                 for rid in wave.wave_ids(name)}
            value['waves'] = {name:dict(authorized=False, requestIDs=list(value['requests']), reservedCostCap=20)}
            value['totalCostCap'] = 20
        now = datetime.now(timezone.utc)
        value.update(authorized=True, approvalID='synthetic', researcher='fixture',
                     approvedAt=(now-timedelta(minutes=1)).isoformat(), expiresAt=(now+timedelta(hours=1)).isoformat())
        value['waves'][name]['authorized'] = True
        return value

    def send(self, wire, key, timeout):
        """Return authentic-shaped synthetic bytes without network access."""
        self.assertEqual(key, 'synthetic-key')
        self.calls.append(wire.decode())
        return 200, canonical(dict(id='fixture', model='gpt-5.6-sol', status='completed',
            output=[dict(type='message', content=[dict(type='output_text', text='{"fixture":true}')])]))

    def run_wave(self, approval, name='A', **kwargs):
        """Route through the actual one-request executor with a synthetic transport."""
        raw = canonical(approval)
        return wave.execute_wave(self.root, name, raw, digest(raw), send=kwargs.pop('send', self.send),
            key_loader=kwargs.pop('key_loader', lambda:'synthetic-key'), progress=lambda message:None, **kwargs)

    def test_draft_exact_wave_hashes_limits_and_no_authorization(self):
        """Draft is deterministic, pins eleven versions/hashes and cannot execute."""
        draft = wave.prepare_wave_a(self.root)
        self.assertEqual(draft, wave.prepare_wave_a(self.root))
        self.assertEqual(tuple(draft['requests']), ('HS-02','HS-03','HS-04','GH-01','GH-02','GH-03','GH-04','HUB-01','HUB-02','HUB-03','HUB-04'))
        self.assertFalse(draft['authorized']); self.assertFalse(draft['waves']['A']['authorized'])
        for rid, row in draft['requests'].items():
            self.assertEqual(row['contextTokenLimit'], 1050000)
            self.assertEqual(row['outputTokenCeiling'], 32768)
            for key in wave.HASH_VERSION_FIELDS: self.assertEqual(row[key], self.results[rid][key])
        with self.assertRaises(ValueError): self.run_wave(draft)
        self.assertFalse((self.root/wave.STATE_DIRECTORY).exists())
        self.results['HUB-04']['conservativeInputTokenAllowance'] = 1050000
        with self.assertRaisesRegex(ValueError, 'context_limit'): wave.prepare_wave_a(self.root)

    def test_complete_sequence_durable_summary_no_reuse_or_historical_dispatch(self):
        """Only confirmed responses advance; attempts and summary cannot be overwritten."""
        approval = self.approval(); original = deepcopy(approval)
        path = self.run_wave(approval)
        report = json.loads(path.read_bytes())
        self.assertEqual(self.calls, list(wave.wave_ids('A')))
        self.assertEqual(report['status'], 'wave_responses_recorded')
        self.assertEqual(report['remainingUnattemptedIDs'], [])
        self.assertTrue(all(a['responseStatus']=='completed' for a in report['attempts']))
        self.assertEqual(approval, original)
        before = path.read_bytes()
        with self.assertRaises(RuntimeError): self.run_wave(approval)
        self.assertEqual(before, path.read_bytes()); self.assertEqual(len(self.calls),11)
        self.assertFalse((self.root/wave.STATE_DIRECTORY/'HS-01').exists())
        self.assertNotIn(b'synthetic-key', path.read_bytes())

    def test_all_members_verified_before_first_dispatch(self):
        """Late-member drift, subsets, versions, caps or digest mismatch reject globally."""
        approval = self.approval()
        for field, value in [('providerEnvelopeSha256','0'*64),('requestVersion','unknown'),
                              ('reservedMaximumCost',999),('contextTokenLimit',1),('maximumAttempts',2)]:
            bad=deepcopy(approval);bad['requests']['HUB-04'][field]=value
            with self.assertRaises(ValueError): self.run_wave(bad)
        bad=deepcopy(approval);del bad['requests']['HUB-04'];bad['waves']['A']['requestIDs'].remove('HUB-04')
        with self.assertRaises(ValueError): self.run_wave(bad)
        raw=canonical(approval)
        with self.assertRaises(ValueError):wave.verify_wave(self.root,'A',raw,'0'*64)
        self.assertEqual(self.calls,[])

    def test_later_waves_require_independent_clearances(self):
        """Current frozen B/C versions require researcher decisions, not transport success."""
        for name, required in [('B',['A']), ('C',['A','B'])]:
            approval=self.approval(name)
            for prior in required:
                with self.assertRaises(ValueError):wave.verify_wave(self.root,name,canonical(approval),digest(canonical(approval)))
                approval['waveClearances'][prior]=dict(decision='cleared_for_next_wave',researcher='fixture',
                    clearedAt=datetime.now(timezone.utc).isoformat(),reviewRecordSha256='a'*64)
            self.assertEqual(tuple(wave.verify_wave(self.root,name,canonical(approval),digest(canonical(approval)))),wave.wave_ids(name))
        self.assertEqual(self.calls,[])

    def test_noncompleted_and_timeout_stop_without_next_dispatch(self):
        """Incomplete provider response and ambiguous exception preserve stop artifacts."""
        for mode in ('incomplete','timeout'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                self.root=Path(folder);self.calls=[]
                def send(wire,key,timeout):
                    """Fail the second call only; first independent result survives."""
                    if len(self.calls)==1:
                        self.calls.append(wire.decode())
                        if mode=='timeout':raise TimeoutError('secret transport text')
                        return 200,canonical(dict(status='incomplete',output=[]))
                    return self.send(wire,key,timeout)
                approval=self.approval()
                with self.assertRaises(RuntimeError):self.run_wave(approval,send=send)
                report=json.loads(next((self.root/wave.STATE_DIRECTORY/'waves').rglob('summary.json')).read_bytes())
                self.assertEqual(len(self.calls),2);self.assertEqual(len(report['remainingUnattemptedIDs']),9)
                self.assertEqual(report['attempts'][0]['outcome'],'response_recorded')
                self.assertTrue((self.root/wave.STATE_DIRECTORY/'STOP').exists())
                self.assertNotIn('secret transport text',str(report))

    def test_missing_credential_and_existing_attempt_stop_without_dispatch(self):
        """No credential consumes no request attempt or STOP; existing attempts never skip."""
        approval=self.approval()
        with self.assertRaises(RuntimeError):self.run_wave(approval,key_loader=lambda:None)
        state=self.root/wave.STATE_DIRECTORY
        self.assertFalse((state/'HS-02').exists());self.assertFalse((state/'STOP').exists())
        self.assertEqual(self.calls,[])
        approval['approvalID']='second-review'
        (state/'HUB-04').mkdir()
        with self.assertRaises(RuntimeError):self.run_wave(approval)
        self.assertEqual(self.calls,[])

    def test_concurrent_wrappers_standalone_and_stop_are_blocked(self):
        """Wave lease blocks other wrappers and standalone dispatch; global lock survives."""
        approval=self.approval();raw=canonical(approval);state=self.root/wave.STATE_DIRECTORY
        (state/'wave.lock').mkdir(parents=True);(state/'wave.lock/owner').write_text('other')
        with self.assertRaises(FileExistsError):self.run_wave(approval)
        with self.assertRaisesRegex(ValueError,'wave_dispatch'):
            terminal.execute(self.root,'HS-02',raw,digest(raw),send=self.send,key_loader=lambda:'synthetic-key')
        self.assertFalse((state/'HS-02').exists());self.assertEqual(self.calls,[])
        (state/'wave.lock/owner').unlink();(state/'wave.lock').rmdir();(state/'STOP').write_text('hold')
        with self.assertRaises(RuntimeError):self.run_wave(approval)
        self.assertEqual(self.calls,[])

    def test_return_value_and_artifacts_both_required(self):
        """Zero exit-like values and false success/mismatched artifacts never advance."""
        for value in (0, 'response_recorded'):
            with tempfile.TemporaryDirectory() as folder:
                self.root=Path(folder)
                with patch.object(terminal,'execute',return_value=value) as execute:
                    with self.assertRaises(RuntimeError):self.run_wave(self.approval())
                    self.assertEqual(execute.call_count,1)
        self.assertEqual(self.calls,[])

    def test_recorded_artifact_tampering_stops_and_preserves_global_lock(self):
        """Actual transport success cannot mask altered evidence or bypass an active lock."""
        approval=self.approval()
        real_execute=terminal.execute
        def altered(*args, **kwargs):
            """Corrupt one temporary synthetic artifact after the real executor returns."""
            outcome=real_execute(*args, **kwargs)
            (self.root/wave.STATE_DIRECTORY/args[1]/'provider-input.txt').write_bytes(b'changed')
            return outcome
        with patch.object(terminal,'execute',side_effect=altered):
            with self.assertRaises(RuntimeError):self.run_wave(approval)
        self.assertEqual(self.calls,['HS-02'])
        self.assertTrue((self.root/wave.STATE_DIRECTORY/'STOP').exists())
        with tempfile.TemporaryDirectory() as folder:
            self.root=Path(folder);self.calls=[]
            lock=self.root/wave.STATE_DIRECTORY/'dispatch.lock';lock.mkdir(parents=True)
            with self.assertRaises(RuntimeError):self.run_wave(approval)
            self.assertTrue(lock.exists());self.assertEqual(self.calls,[])


if __name__ == '__main__':
    unittest.main()
