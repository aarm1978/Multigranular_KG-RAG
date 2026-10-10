"""Focused final-version and Wave C amendment tests; synthetic/offline only."""
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


class FinalPromptTests(unittest.TestCase):
    """Test only newly changed routes and their immediate legacy boundary."""

    def fixture(self, family):
        """Reuse synthetic fixtures without running their historical test suites."""
        module=importlib.import_module(f'test_{family}_semantic_offline_pipeline')
        f=module.OfflineReplayTests();f.setUp();self.addCleanup(f.doCleanups)
        return module.contract,f

    def test_exact_append_defaults_hashes_and_response_contract(self):
        """Final versions append the authorized wording; legacy defaults/schemas stay fixed."""
        doc=Path('docs/study2_step12c_wave_c_calibration_implementation_v1.0.0.md').read_text()
        for family,heading in [('coderepos','GitHub'),('documents','CIROH Hub')]:
            contract,f=self.fixture(family)
            section=doc.split('### '+heading+'\n')[1].split('\n##')[0]
            text='\n'.join(line[2:] if line.startswith('> ') else '' for line in section.splitlines() if line.startswith('>'))
            self.assertEqual(list(contract.WAVE_C_INSTRUCTIONS),text.split('\n\n'))
            original=contract.build_request(**f.inputs)
            self.assertEqual(original,contract.build_request(**f.inputs,request_version=contract.REQUEST_VERSION))
            b=contract.build_request(**f.inputs,request_version=contract.WAVE_B_REQUEST_VERSION)
            c=contract.build_request(**f.inputs,request_version=contract.WAVE_C_REQUEST_VERSION)
            self.assertEqual(c['request']['instructions'],b['request']['instructions']+list(contract.WAVE_C_INSTRUCTIONS))
            self.assertEqual(c,contract.build_request(**f.inputs,request_version=contract.WAVE_C_REQUEST_VERSION))
            self.assertNotEqual(c['requestSha256'],b['requestSha256'])
            for k,v in b['request'].items():
                if k not in ('schemaVersion','instructions','promptIdentifier'):self.assertEqual(v,c['request'][k])
            self.assertEqual(build_preflight(b,output_ceiling=32768)['schemaSha256'],build_preflight(c,output_ceiling=32768)['schemaSha256'])
            parsed=contract.parse_recorded_response(canonical(f.payload()),request=c)
            self.assertEqual(parsed['status'],'response_parsed')
            self.assertEqual(parsed['requestContractVersion'],contract.WAVE_C_REQUEST_VERSION)
        from src.extraction.llm.datasets import request_contract as hs
        self.assertEqual(amendment.WAVE_C_VERSIONS['hydroshare'],hs.WAVE_B_REQUEST_VERSION)
        self.assertFalse(hasattr(hs,'WAVE_C_INSTRUCTIONS'))

    def test_invalid_pairings_and_identifiable_parse_errors(self):
        """New versions preserve candidate-local failures; a valid hash does not repair a bad prompt."""
        for family in ('coderepos','documents'):
            contract,f=self.fixture(family)
            q=contract.build_request(**f.inputs,request_version=contract.WAVE_C_REQUEST_VERSION)
            for version in ('unknown','1.2.0',[],None):
                self.assertEqual(contract.build_request(**f.inputs,request_version=version)['status'],'request_failed')
            payload=f.payload();payload['candidateNodes'].append({'candidateID':'local-bad','inventoryId':'unknown'})
            parsed=contract.parse_recorded_response(canonical(payload),request=q)
            b=contract.build_request(**f.inputs,request_version=contract.WAVE_B_REQUEST_VERSION)
            self.assertEqual(parsed['candidateRecords'],contract.parse_recorded_response(canonical(payload),request=b)['candidateRecords'])
            self.assertNotEqual(parsed['status'],'processing_failed')
            for key,value in [('promptIdentifier',contract.WAVE_B_PROMPT_IDENTIFIER),('instructions',b['request']['instructions']),('schemaVersion','unknown')]:
                bad=deepcopy(q);bad['request'][key]=value;bad['requestSha256']=digest(base.semantic_bytes(bad['request']))
                self.assertEqual(contract.parse_recorded_response(canonical(payload),request=bad)['status'],'processing_failed')

    def test_all_projection_pairings_exact_text_and_failure_warnings(self):
        """C adds only a request-version route; audit behavior and selected evidence remain unchanged."""
        contract,f=self.fixture('coderepos')
        source=deepcopy(f.inputs)
        source['reader_result']['diagnostics'].append({'status':'source_failure','reason':'synthetic_failure','path':'other.md'})
        for version,projection in [(contract.REQUEST_VERSION,'github-provider-input/1.0.0'),
                (contract.WAVE_B_REQUEST_VERSION,'github-provider-input/1.1.0'),(contract.WAVE_C_REQUEST_VERSION,'github-provider-input/1.2.0')]:
            q=contract.build_request(**source,request_version=version)
            original=deepcopy(q);p=project_provider_input(q,version=projection);body=json.loads(p['inputBytes'])
            self.assertEqual(body['sourceUnits'],q['request']['sourceUnits'])
            self.assertEqual(body['instructions'],q['request']['instructions'])
            self.assertIn(source['reader_result']['diagnostics'][-1],body['sourceDiagnostics'])
            self.assertEqual(p['semanticRequestSha256'],q['requestSha256'])
            self.assertEqual(p['providerInputSha256'],digest(p['inputBytes']))
            self.assertEqual(q,original)
            for wrong in ('github-provider-input/1.0.0','github-provider-input/1.1.0','github-provider-input/1.2.0'):
                if wrong!=projection:
                    with self.assertRaises(ValueError):project_provider_input(q,version=wrong)


class WaveCBoundaryTests(unittest.TestCase):
    """No actual provider or credential paths may be exercised by these tests."""

    def setUp(self):
        """Isolate synthetic files and explicitly block network/real credential loading."""
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.addCleanup(patch.stopall)
        patch('socket.socket',side_effect=AssertionError('network forbidden')).start()
        patch('src.extraction.llm.publications.openai_provider.load_openai_api_key',side_effect=AssertionError('real credential access forbidden')).start()

    def fixture(self):
        """Build a synthetic C record that pins all nine original selection records."""
        rows=[{'requestID':rid,'artifactFamily':{'HS':'hydroshare','GH':'github','HUB':'ciroh_hub'}[rid.split('-')[0]],
               'semanticRequestSha256':digest(rid.encode())} for rid in amendment.WAVE_C_REQUEST_IDS]
        manifest={'requests':rows,'authorityFiles':{},'implementationFiles':{}}
        record={'schemaVersion':amendment.WAVE_C_VERSION,'wave':'C','authorized':False,
            'baseManifestPath':base.MANIFEST_PATH,'baseManifestSha256':base.MANIFEST_SHA256,
            'priorExecutionAmendmentPath':amendment.PRIOR_AMENDMENT_PATH,
            'priorExecutionAmendmentSha256':amendment.PRIOR_AMENDMENT_SHA256,
            'authorityFiles':{},'implementation':{'fixture':'verified'},'requests':[
                {'requestID':r['requestID'],'baseSelectionRecordSha256':digest(base.semantic_bytes(r)),
                 'originalSemanticRequestSha256':r['semanticRequestSha256'],'requestVersion':amendment.WAVE_C_VERSIONS[r['artifactFamily']]} for r in rows]}
        return manifest,record,self.root/'amendment.json'

    def test_chained_amendment_scope_versions_and_fingerprints(self):
        """Digest, prior B association, selections and new code pins all fail closed."""
        manifest,record,path=self.fixture()
        with patch.object(base,'load_manifest',return_value=manifest),patch.object(amendment,'implementation_record',return_value={'fixture':'verified'}):
            def load(value):
                """Use explicit synthetic pinned bytes for each negative case."""
                raw=canonical(value);path.write_bytes(raw)
                return amendment.load_amendment(self.root,path,digest(raw))
            self.assertEqual(load(record),(manifest,record))
            for key,value in [('priorExecutionAmendmentSha256','0'*64),('wave','B'),('schemaVersion',amendment.VERSION),('implementation',{}),('authorized',True)]:
                with self.assertRaises(ValueError):load({**record,key:value})
            for key,value in [('requestID','GH-05'),('baseSelectionRecordSha256','0'*64),('requestVersion','unknown')]:
                bad=deepcopy(record);bad['requests'][0][key]=value
                with self.assertRaises(ValueError):load(bad)
            with self.assertRaisesRegex(ValueError,'digest'):
                amendment.load_amendment(self.root,path,'0'*64)

    def test_prior_fingerprint_chain_and_strict_b_loader(self):
        """C proves B's accepted fingerprints, never replaces the old B check."""
        p=self.root/'contract.py';p.write_bytes(b'current')
        manifest={'implementationFiles':{'contract.py':digest(b'original')}}
        prior={'implementation':{'old':{'contract.py':digest(b'original')},'new':{'contract.py':digest(b'accepted B')}}}
        with patch.object(amendment,'RUNTIME_FILES',()),patch.object(amendment,'prior_amendment',return_value=prior),patch.object(amendment,'_old_bytes',return_value=b'accepted B'):
            record=amendment.implementation_record(self.root,manifest,wave='C')
            self.assertEqual(record['old'],prior['implementation']['new'])
            self.assertEqual(record['changedFiles'],['contract.py'])
            prior['implementation']['new']['contract.py']='0'*64
            with self.assertRaisesRegex(ValueError,'prior_amendment_implementation_mismatch'):
                amendment.implementation_record(self.root,manifest,wave='C')
            with self.assertRaisesRegex(ValueError,'historical_implementation_fingerprint_invalid'):
                amendment.implementation_record(self.root,manifest)  # unchanged B policy

    def approval(self):
        """Create synthetic v3 only; no real approval file is written."""
        f=approval_fixture.CalibrationTests();a,r=f.approval('GH-08')
        a.update(schemaVersion='step12c-terminal-approval/3',executionAmendmentSha256=digest(b'C'),
            executionAmendmentVersion=amendment.WAVE_C_VERSION,priorExecutionAmendmentSha256=amendment.PRIOR_AMENDMENT_SHA256)
        r.update(executionAmendmentSha256=digest(b'C'),executionAmendmentVersion=amendment.WAVE_C_VERSION,
                 priorExecutionAmendmentSha256=amendment.PRIOR_AMENDMENT_SHA256,
                 requestVersion='github-request/1.2.0',promptIdentifier='github-wave-c-role-purpose-clarification/0.1.0',providerInputProjectionVersion='github-provider-input/1.2.0')
        for key in ('executionAmendmentSha256','requestVersion','promptIdentifier','providerInputProjectionVersion'):a['requests']['GH-08'][key]=r[key]
        for w in ('A','B'):
            a['waveClearances'][w]={'decision':'cleared_for_next_wave','researcher':'synthetic','clearedAt':datetime.now(timezone.utc).isoformat(),'reviewRecordSha256':'a'*64}
        return a,r

    def test_two_clearances_exact_hashes_budget_and_window_required(self):
        """Neither completion nor B's approval clears C or supplies a monetary reservation."""
        a,r=self.approval()
        def verify(value):
            """Check a synthetic approval in memory only."""
            raw=canonical(value);return terminal.verify_approval(raw,digest(raw),'GH-08',r)
        verify(a)
        for missing in ('A','B'):
            bad=deepcopy(a);del bad['waveClearances'][missing]
            with self.assertRaisesRegex(ValueError,'clearance_required'):verify(bad)
        for key,value in [('executionAmendmentVersion',amendment.VERSION),('executionAmendmentSha256','0'*64),('priorExecutionAmendmentSha256','0'*64),('totalCostCap',0),('expiresAt','2000-01-01T00:00:00Z'),('authorized',False)]:
            with self.assertRaises(ValueError):verify({**a,key:value})
        for key,value in [('requestVersion','github-request/1.1.0'),('providerInputProjectionVersion','github-provider-input/1.1.0'),('semanticRequestSha256','0'*64),('inputTokenAllowance',1),('reservedMaximumCost',0)]:
            bad=deepcopy(a);bad['requests']['GH-08'][key]=value
            with self.assertRaises(ValueError):verify(bad)

    def test_no_dispatch_or_credentials_without_matching_amendment(self):
        """Bad C routing stops before credential access and before reserving any attempt."""
        a,r=self.approval();raw=canonical(a)
        path=self.root/'amendment.json';path.write_bytes(b'C')
        with self.assertRaisesRegex(ValueError,'digest'):
            terminal.execute(self.root,'GH-08',raw,digest(raw),amendment=path,amendment_sha256='0'*64,
                key_loader=lambda:self.fail('credentials'),send=lambda *a:self.fail('provider'))
        with self.assertRaisesRegex(ValueError,'wave_b_only'):
            wave.verify_wave(self.root,'A',raw,digest(raw),amendment=path,amendment_sha256=digest(b'C'))
        self.assertFalse((self.root/'var').exists())

    def test_wave_c_preparation_never_replays_prior_waves(self):
        """Nine C IDs only; preparing the amendment cannot invoke historical replay."""
        manifest,_,_=self.fixture()
        for row in manifest['requests']:
            directory=self.root/base.PREFLIGHT_DIRECTORY/row['requestID'];directory.mkdir(parents=True)
        result={k:'synthetic' for k in amendment.ASSOCIATION_FIELDS}
        with patch.object(base,'load_manifest',return_value=manifest),patch.object(amendment,'implementation_record',return_value={}),\
             patch.object(amendment,'verify_legacy_associations',side_effect=AssertionError('historical replay forbidden')),\
             patch.object(amendment,'prospective_case',return_value=({'request':{'instructions':['synthetic']}},result)) as build:
            record=amendment.prepare(self.root,wave='C')
        self.assertEqual([call.args[2] for call in build.call_args_list],list(amendment.WAVE_C_REQUEST_IDS))
        self.assertFalse(record['authorized']);self.assertEqual(record['priorExecutionAmendmentSha256'],amendment.PRIOR_AMENDMENT_SHA256)
        self.assertNotIn('legacyWaveAAssociations',record)

    def test_complete_c_wave_reuses_transport_and_records_prior_association(self):
        """Nine synthetic requests advance only via the existing confirmed-response path."""
        import test_pilot_wave as fixture_module
        f=fixture_module.WaveTests();f.setUp();self.addCleanup(f.doCleanups)
        path=f.root/'amendment.json';path.write_bytes(b'C')
        for rid in amendment.WAVE_C_REQUEST_IDS:
            family={'HS':'hydroshare','GH':'github','HUB':'ciroh_hub'}[rid.split('-')[0]]
            f.results[rid].update(executionAmendmentSha256=digest(b'C'),executionAmendmentVersion=amendment.WAVE_C_VERSION,
                priorExecutionAmendmentSha256=amendment.PRIOR_AMENDMENT_SHA256,requestVersion=amendment.WAVE_C_VERSIONS[family])
        approval=f.approval('C')
        approval.update(schemaVersion='step12c-terminal-approval/3',executionAmendmentSha256=digest(b'C'),
            executionAmendmentVersion=amendment.WAVE_C_VERSION,priorExecutionAmendmentSha256=amendment.PRIOR_AMENDMENT_SHA256)
        for row in approval['requests'].values():row['executionAmendmentSha256']=digest(b'C')
        for w in ('A','B'):
            approval['waveClearances'][w]={'decision':'cleared_for_next_wave','researcher':'synthetic',
                'clearedAt':datetime.now(timezone.utc).isoformat(),'reviewRecordSha256':'a'*64}
        raw=canonical(approval)
        def load(root,rid,**route):
            """Inject a source-verified synthetic preflight; never real files or credentials."""
            self.assertEqual(route,{'amendment':path,'amendment_sha256':digest(b'C')})
            return deepcopy(f.results[rid])
        with patch.object(terminal,'load_selected',side_effect=load):
            result=wave.execute_wave(f.root,'C',raw,digest(raw),amendment=path,amendment_sha256=digest(b'C'),
                send=f.send,key_loader=lambda:'synthetic-key',progress=lambda message:None)
        summary=json.loads(result.read_bytes())
        self.assertEqual(f.calls,list(amendment.WAVE_C_REQUEST_IDS));self.assertEqual(summary['status'],'wave_responses_recorded')
        self.assertEqual(summary['priorExecutionAmendmentSha256'],amendment.PRIOR_AMENDMENT_SHA256)
        for rid in amendment.WAVE_C_REQUEST_IDS:
            association=json.loads((f.root/wave.STATE_DIRECTORY/rid/'association.json').read_bytes())
            self.assertEqual(association['priorExecutionAmendmentSha256'],amendment.PRIOR_AMENDMENT_SHA256)
