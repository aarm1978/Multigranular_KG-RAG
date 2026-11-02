"""Focused Wave B contracts and amendment routing; synthetic inputs, no live calls."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import calibration_preflight as base, wave_b_amendment as amendment
from src.extraction.llm import pilot_terminal as terminal, pilot_wave as wave
from src.extraction.llm.pilot_preflight import canonical, digest, build_preflight
from src.extraction.llm.coderepos.provider_input import project_provider_input
import test_calibration_terminal as approval_fixture


class PromptVersions(unittest.TestCase):
    """Use accepted family fixtures without collecting unrelated tests."""

    def fixture(self, family):
        """Instantiate one existing synthetic reader fixture."""
        module = importlib.import_module(f'test_{family}_semantic_offline_pipeline')
        fixture = module.OfflineReplayTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return module, fixture

    def test_versions_hashes_unchanged_schema_and_candidate_isolation(self):
        """Only new version/prompt instructions change; candidate semantics never do."""
        for family in ('datasets', 'coderepos', 'documents'):
            with self.subTest(family=family):
                module, f = self.fixture(family)
                before = deepcopy(f.inputs)
                contract = module.contract
                old = contract.build_request(**f.inputs)
                new = contract.build_request(**f.inputs, request_version=contract.WAVE_B_REQUEST_VERSION)
                self.assertEqual(old, contract.build_request(**f.inputs, request_version=contract.REQUEST_VERSION))
                self.assertNotEqual(old['requestSha256'], new['requestSha256'])
                self.assertEqual(new, contract.build_request(**f.inputs, request_version=contract.WAVE_B_REQUEST_VERSION))
                for key, value in old['request'].items():
                    if key not in ('schemaVersion', 'instructions'):
                        self.assertEqual(value, new['request'][key])
                self.assertEqual(build_preflight(old, output_ceiling=32768)['schemaSha256'],
                                 build_preflight(new, output_ceiling=32768)['schemaSha256'])
                # An identifiable malformed row must not poison an independent valid row.
                payload = f.payload()
                payload['candidateNodes'].append({'candidateID': 'local-bad', 'inventoryId': 'UNKNOWN'})
                raw = canonical(payload)
                legacy = module.pipeline.replay_recorded_response(raw, request_inputs=f.inputs)
                prospective = module.pipeline.replay_recorded_response(raw,
                    request_inputs={**f.inputs, 'request_version': contract.WAVE_B_REQUEST_VERSION},
                    expected_request_sha256=new['requestSha256'])
                self.assertEqual(legacy.to_record()['finalRecords'], prospective.to_record()['finalRecords'])
                self.assertEqual(legacy.to_record()['validationResult'], prospective.to_record()['validationResult'])
                self.assertEqual(prospective.to_record()['status'], 'replay_completed')
                self.assertFalse(prospective.to_record()['kgAuthorization'])
                self.assertEqual(before, f.inputs)
                if family == 'datasets':
                    intermediate = contract.build_request(**f.inputs, request_version=contract.PROSPECTIVE_REQUEST_VERSION)
                    self.assertEqual(intermediate['request']['instructions'], contract.INSTRUCTIONS + list(contract.CLARIFICATION_INSTRUCTIONS))
                    self.assertEqual(new['request']['instructions'], intermediate['request']['instructions'] + list(contract.WAVE_B_INSTRUCTIONS))

    def test_exact_approved_wording_and_refinement(self):
        """Compare all paragraphs to the approved proposal, applying only one refinement."""
        doc = Path('docs/study2_step12c_wave_b_prompt_calibration_candidate_v0.1.md').read_text()
        for family, heading in [('datasets', 'HydroShare'), ('coderepos', 'GitHub'), ('documents', 'CIROH Hub')]:
            module = importlib.import_module(f'src.extraction.llm.{family}.request_contract')
            section = doc.split('### ' + heading + ' —')[1].split('\n##')[0]
            quoted = '\n'.join(line[2:] if line.startswith('> ') else '' for line in section.splitlines() if line.startswith('>'))
            paragraphs = [' '.join(p.splitlines()) for p in quoted.split('\n\n')]
            if family == 'coderepos':
                paragraphs[0] = paragraphs[0].replace('named software function or method described in eligible prose, including its stated role.',
                    'named programming function or object-oriented method explicitly described in eligible prose, including its stated computational role. A scientific Method is not a software Function.')
            self.assertEqual(list(module.WAVE_B_INSTRUCTIONS), paragraphs)

    def test_unknown_versions_and_rehashed_invalid_pairings_fail_closed(self):
        """Digest correctness never legitimizes an unknown version or substituted prompt."""
        for family in ('datasets', 'coderepos', 'documents'):
            module, f = self.fixture(family)
            contract = module.contract
            for version in (None, [], 1, 'unknown', contract.WAVE_B_REQUEST_VERSION + ' '):
                result = contract.build_request(**f.inputs, request_version=version)
                self.assertEqual(result['status'], 'request_failed')
            q = contract.build_request(**f.inputs, request_version=contract.WAVE_B_REQUEST_VERSION)
            raw = canonical(f.payload())
            for field, value in [('schemaVersion', 'unknown'), ('promptIdentifier', 'wrong'), ('instructions', [])]:
                bad = deepcopy(q)
                bad['request'][field] = value
                bad['requestSha256'] = digest(base.semantic_bytes(bad['request']))
                self.assertEqual(contract.parse_recorded_response(raw, request=bad)['status'], 'processing_failed')
            legacy = contract.build_request(**f.inputs)
            legacy['request']['promptIdentifier'] = contract.WAVE_B_PROMPT_IDENTIFIER
            legacy['requestSha256'] = digest(base.semantic_bytes(legacy['request']))
            self.assertEqual(contract.parse_recorded_response(raw, request=legacy)['status'], 'processing_failed')

    def test_projection_version_pairing_and_exact_selected_text(self):
        """Audit reduction changes no selected text or legacy projection behavior."""
        module, f = self.fixture('coderepos')
        old = module.contract.build_request(**f.inputs)
        new = module.contract.build_request(**f.inputs, request_version=module.contract.WAVE_B_REQUEST_VERSION)
        for q, version in [(old, 'github-provider-input/1.0.0'), (new, amendment.PROJECTION)]:
            before = deepcopy(q)
            projected = project_provider_input(q, version=version)
            body = json.loads(projected['inputBytes'])
            self.assertEqual(body['sourceUnits'], q['request']['sourceUnits'])
            self.assertEqual(body['instructions'], q['request']['instructions'])
            self.assertEqual(projected['semanticRequestSha256'], q['requestSha256'])
            self.assertEqual(projected['providerInputSha256'], digest(projected['inputBytes']))
            self.assertEqual(projected, project_provider_input(q, version=version))
            self.assertEqual(q, before)
        for q, version in [(old, amendment.PROJECTION), (new, 'github-provider-input/1.0.0')]:
            with self.assertRaises(ValueError):
                project_provider_input(q, version=version)


class AmendmentBoundary(unittest.TestCase):
    """Explicit digest, fingerprint, approval and one-attempt boundaries."""

    def setUp(self):
        """Use only isolated files and synthetic approval data."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.addCleanup(patch.stopall)
        patch('socket.socket', side_effect=AssertionError('network forbidden')).start()
        patch('src.extraction.llm.publications.openai_provider.load_openai_api_key', side_effect=AssertionError('real credentials forbidden')).start()

    def fixture(self):
        """Minimal versioned amendment with explicit original-selection references."""
        rows = [{'requestID': rid, 'artifactFamily': {'HS':'hydroshare','GH':'github','HUB':'ciroh_hub'}[rid.split('-')[0]],
                 'semanticRequestSha256': digest(rid.encode())} for rid in amendment.REQUEST_IDS]
        manifest = {'requests': rows, 'authorityFiles': {}, 'implementationFiles': {}}
        record = {'schemaVersion': amendment.VERSION, 'wave': 'B', 'authorized': False,
            'baseManifestPath': base.MANIFEST_PATH, 'baseManifestSha256': base.MANIFEST_SHA256,
            'authorityFiles': {}, 'implementation': {'fixture': 'verified'}, 'requests': [
                {'requestID': r['requestID'], 'baseSelectionRecordSha256': digest(base.semantic_bytes(r)),
                 'originalSemanticRequestSha256': r['semanticRequestSha256'], 'requestVersion': amendment.VERSIONS[r['artifactFamily']]} for r in rows]}
        path = self.root / 'amendment.json'
        return manifest, record, path

    def test_exact_digest_scope_selections_versions_and_fingerprints(self):
        """Rehashed malformed amendments cannot silently repin original selection."""
        manifest, record, path = self.fixture()
        with patch.object(base, 'load_manifest', return_value=manifest), patch.object(amendment, 'implementation_record', return_value={'fixture':'verified'}):
            raw = canonical(record); path.write_bytes(raw)
            self.assertEqual(amendment.load_amendment(self.root, path, digest(raw)), (manifest, record))
            with self.assertRaisesRegex(ValueError, 'digest'):
                amendment.load_amendment(self.root, path, '0' * 64)
            for field, value in [('baseManifestSha256', '0'*64), ('wave', 'A'), ('implementation', {}), ('authorized', True)]:
                bad = {**record, field: value}; raw = canonical(bad); path.write_bytes(raw)
                with self.assertRaises(ValueError): amendment.load_amendment(self.root, path, digest(raw))
            for field, value in [('requestID', 'HS-01'), ('baseSelectionRecordSha256', '0'*64), ('requestVersion', 'unknown')]:
                bad = deepcopy(record); bad['requests'][0][field] = value
                raw = canonical(bad); path.write_bytes(raw)
                with self.assertRaises(ValueError): amendment.load_amendment(self.root, path, digest(raw))

    def test_historical_fingerprints_cannot_be_replaced_silently(self):
        """Base preflight rejects changed files; compatibility also verifies original pins."""
        p = self.root / 'contract.py'; p.write_bytes(b'new')
        manifest = {'requests':[{'requestID':'HS-05'}], 'authorityFiles':{}, 'implementationFiles':{'contract.py':digest(b'old')}}
        with self.assertRaisesRegex(ValueError, 'snapshot_drift'):
            base.rebuild_request(self.root, manifest, 'HS-05')
        with patch.object(amendment, 'RUNTIME_FILES', ()), patch.object(amendment, '_old_bytes', return_value=b'old'):
            records = amendment.implementation_record(self.root, manifest)
            self.assertEqual(records['changedFiles'], ['contract.py'])
            manifest['implementationFiles']['contract.py'] = digest(b'invalid old')
            with self.assertRaisesRegex(ValueError, 'historical_implementation_fingerprint_invalid'):
                amendment.implementation_record(self.root, manifest)

    def approval(self):
        """Synthetic v3 extends the existing v2 boundary without writing live approval."""
        f = approval_fixture.CalibrationTests()
        a, r = f.approval('GH-05')
        a['schemaVersion'] = 'step12c-terminal-approval/3'
        a['executionAmendmentSha256'] = r['executionAmendmentSha256'] = digest(b'amendment')
        a['executionAmendmentVersion'] = r['executionAmendmentVersion'] = amendment.VERSION
        a['requests']['GH-05']['executionAmendmentSha256'] = r['executionAmendmentSha256']
        a['waveClearances']['A'] = {'decision':'cleared_for_next_wave', 'researcher':'synthetic',
            'clearedAt':datetime.now(timezone.utc).isoformat(), 'reviewRecordSha256':'a'*64}
        return a, r

    def test_approval_v3_requires_clearance_amendment_hash_and_version(self):
        """No v2 authorization can approve new versions or missing Wave A clearance."""
        a, r = self.approval()
        def verify(value):
            """Verify synthetic reviewed bytes, never contact a provider."""
            raw = canonical(value)
            return terminal.verify_approval(raw, digest(raw), 'GH-05', r)
        verify(a)
        for key, value in [('schemaVersion','step12c-terminal-approval/2'),('executionAmendmentSha256','0'*64),
                           ('executionAmendmentVersion','unknown'),('waveClearances',{}),('authorized',False)]:
            with self.assertRaises(ValueError): verify({**a, key:value})
        for key, value in [('executionAmendmentSha256','0'*64),('requestVersion','unknown'),('reservedMaximumCost',0),('inputTokenAllowance',1)]:
            bad = deepcopy(a); bad['requests']['GH-05'][key] = value
            with self.assertRaises(ValueError): verify(bad)

    def test_no_dispatch_with_invalid_amendment_and_no_wave_a_route(self):
        """Invalid amendment stops before keys, attempts or HTTP; A cannot use B routing."""
        a, _ = self.approval(); raw = canonical(a)
        path = self.root / 'amendment.json'; path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'amendment_digest_mismatch'):
            terminal.execute(self.root, 'GH-05', raw, digest(raw), amendment=path, amendment_sha256='0'*64,
                key_loader=lambda: self.fail('credential'), send=lambda *a:self.fail('provider'))
        with self.assertRaisesRegex(ValueError, 'amendment_wave_b_only'):
            wave.verify_wave(self.root, 'A', raw, digest(raw), amendment=path, amendment_sha256=digest(b'{}'))
        self.assertFalse((self.root / 'var').exists())

    def test_amended_one_attempt_transport_preserves_association(self):
        """An injected synthetic transport retains new provenance and original attempt path."""
        a, result = self.approval(); raw = canonical(a)
        path = self.root / 'amendment.json'; path.write_bytes(b'amendment')
        calls = []
        def send(wire, key, timeout):
            """Return synthetic transport data only."""
            calls.append(wire)
            return 200, canonical({'status':'completed', 'output':[{'type':'message', 'content':[{'type':'output_text','text':'{}'}]}]})
        with patch.object(terminal, 'load_selected', return_value=result):
            outcome = terminal.execute(self.root, 'GH-05', raw, digest(raw), amendment=path,
                amendment_sha256=digest(b'amendment'), key_loader=lambda:'SYNTHETIC', send=send)
            self.assertEqual(outcome, 'response_recorded')
            with self.assertRaises(FileExistsError):
                terminal.execute(self.root, 'GH-05', raw, digest(raw), amendment=path,
                    amendment_sha256=digest(b'amendment'), key_loader=lambda:'SYNTHETIC', send=send)
        attempt = self.root / 'var/study2_step12c/terminal/GH-05'
        self.assertEqual((attempt / 'execution-amendment.json').read_bytes(), b'amendment')
        self.assertEqual(json.loads((attempt / 'association.json').read_bytes())['executionAmendmentSha256'], digest(b'amendment'))
        self.assertEqual(len(calls), 1)

    def test_complete_wave_b_uses_existing_sequential_transport(self):
        """Nine synthetic completed responses advance sequentially under v3 only."""
        import test_pilot_wave as fixture_module
        f = fixture_module.WaveTests(); f.setUp(); self.addCleanup(f.doCleanups)
        path = f.root / 'amendment.json'; path.write_bytes(b'amendment')
        for rid in amendment.REQUEST_IDS:
            f.results[rid].update(executionAmendmentSha256=digest(b'amendment'), executionAmendmentVersion=amendment.VERSION)
        approval = f.approval('B')
        approval.update(schemaVersion='step12c-terminal-approval/3', executionAmendmentSha256=digest(b'amendment'),
                        executionAmendmentVersion=amendment.VERSION)
        approval['waveClearances']['A'] = {'decision':'cleared_for_next_wave','researcher':'synthetic',
            'clearedAt':datetime.now(timezone.utc).isoformat(),'reviewRecordSha256':'a'*64}
        for row in approval['requests'].values(): row['executionAmendmentSha256'] = digest(b'amendment')
        raw = canonical(approval)
        def load(root, rid, **route):
            """Synthetic preflight with explicit propagation of selected amendment."""
            self.assertEqual(route, {'amendment':path, 'amendment_sha256':digest(b'amendment')})
            return deepcopy(f.results[rid])
        with patch.object(terminal, 'load_selected', side_effect=load):
            result = wave.execute_wave(f.root, 'B', raw, digest(raw), amendment=path, amendment_sha256=digest(b'amendment'),
                send=f.send, key_loader=lambda:'synthetic-key', progress=lambda message:None)
        summary = json.loads(result.read_bytes())
        self.assertEqual(summary['status'], 'wave_responses_recorded')
        self.assertEqual(summary['executionAmendmentSha256'], digest(b'amendment'))
        self.assertEqual(f.calls, list(amendment.REQUEST_IDS))
        self.assertFalse(summary['remainingUnattemptedIDs'])
        self.assertFalse((f.root / 'var/study2_step12c/terminal/HS-01').exists())

    def test_selection_drift_and_artifact_overwrite_fail_closed(self):
        """A prospective builder cannot change source content or refresh an existing file."""
        fixture = PromptVersions(); self.addCleanup(fixture.doCleanups)
        module, f = fixture.fixture('coderepos')
        old = module.contract.build_request(**f.inputs)
        changed = module.contract.build_request(**f.inputs, request_version=module.contract.WAVE_B_REQUEST_VERSION)
        changed['request']['sourceUnits'][0]['text'] = 'replaced'
        with patch.object(amendment, 'legacy_request', return_value=(old, f.inputs)), patch.object(module.contract, 'build_request', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'source_or_contract_drift'):
                amendment.prospective_case(self.root, {}, 'GH-05')
        request = old; result = build_preflight(old, output_ceiling=32768)
        path = self.root / 'amendment.json'; path.write_bytes(b'fixture')
        sha = digest(b'fixture')
        with patch.object(amendment, 'build_case', return_value=(request, result)):
            amendment.write_case(self.root, 'GH-05', path, sha)
            self.assertEqual(amendment.load_case(self.root, 'GH-05', path, sha), result)
            changed_path = amendment.case_folder(self.root, 'GH-05', sha) / 'provider-input.txt'
            changed_path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'stored_amendment_preflight_drift'):
                amendment.write_case(self.root, 'GH-05', path, sha)
            self.assertEqual(changed_path.read_bytes(), b'changed')
