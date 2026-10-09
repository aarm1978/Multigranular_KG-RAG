"""Focused synthetic manifest/wave integration; never uses real credentials or HTTP."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import calibration_preflight as calibration
from src.extraction.llm import pilot_terminal as runner
from src.extraction.llm.pilot_preflight import build_preflight, canonical, digest
import test_coderepos_semantic_offline_pipeline as gh_fixture
import test_datasets_semantic_offline_pipeline as hs_fixture
import test_documents_semantic_offline_pipeline as hub_fixture


class CalibrationTests(unittest.TestCase):
    """Verify frozen routing, exact bytes, independent authorization and attempts."""

    def setUp(self):
        """Use an isolated temporary directory and synthetic owner data."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def row(self, q):
        """Derive a small trusted manifest row from a synthetic request."""
        b=q['request']; units=[]
        for i,u in enumerate(b['sourceUnits'],1):
            units.append({**{k:v for k,v in u.items() if k not in ('text','headingContext')},
                'selectionOrder':i,'selectedTextCharacters':len(u['text']),
                'selectedTextUtf8Bytes':len(u['text'].encode()),'selectedTextSha256':digest(u['text'].encode())})
        return {'artifactFamily':b['artifactFamily'],'owner':b['owner'],
            'acceptedEndpoint':{'id':b['owner']['endpointID']},'requestVersion':b['schemaVersion'],
            'selectedSourceUnitIDs':b['selectedSourceUnitIDs'],'orderedUnits':units,
            'semanticRequestSha256':q['requestSha256'],'inputCompleteness':b['sourceCompleteness'],
            'endpointInventories':{'acceptedEndpoints':b['acceptedEndpoints'],'acceptedAssertions':[], 'authorizedStubs':[]},
            'acceptedSectionMapping':b.get('acceptedSectionMapping')}

    def fixture(self, module):
        """Reuse existing synthetic reader inputs without collecting its tests."""
        obj=module.OfflineReplayTests(); obj.setUp();self.addCleanup(obj.doCleanups)
        return obj

    def test_manifest_digest_and_all_thirty_routes_fail_closed(self):
        """Pin bytes and reject swapped family, wave, version, owner or ID."""
        rows=[]
        for rid in calibration.REQUEST_IDS:
            prefix=rid.split('-')[0]
            family,cls,version={'HS':('hydroshare','DatasetResource','hydroshare-request/1.0.0' if rid=='HS-01' else 'hydroshare-request/1.1.0'),
                'GH':('github','Repository','github-request/1.0.0'), 'HUB':('ciroh_hub','DocumentationPage','ciroh_hub-request/1.0.0')}[prefix]
            rows.append({'requestID':rid,'artifactFamily':family,'wave':calibration.wave_for(rid),'requestVersion':version,
                'acceptedEndpoint':{'id':rid,'class':cls},'owner':{'endpointID':rid},
                'selectedSourceUnitIDs':[rid+'unit'],'orderedUnits':[{'sourceUnitID':rid+'unit'}]})
        manifest={'schemaVersion':'study2-step12c-calibration-selection/0.2','requests':rows}
        file=self.root/calibration.MANIFEST_PATH;file.parent.mkdir(parents=True)
        def check(value):
            """Pin synthetic bytes independently for structural-negative tests."""
            raw=canonical(value);file.write_bytes(raw)
            with patch.object(calibration,'MANIFEST_SHA256',digest(raw)):
                return calibration.load_manifest(self.root)
        self.assertEqual(check(manifest),manifest)
        with self.assertRaises(ValueError):calibration.load_manifest(self.root)
        for key,value in [('wave','C'),('artifactFamily','github'),('requestVersion','unknown'),('requestID','../escape')]:
            changed=deepcopy(manifest);changed['requests'][0][key]=value
            with self.assertRaises(ValueError):check(changed)
        for rid in calibration.REQUEST_IDS:
            expected=calibration.PROJECTION_VERSION if rid.startswith('GH-') and rid!='GH-01' else None
            self.assertEqual(calibration.projection_for(rid),expected)
        with self.assertRaises(ValueError):calibration.wave_for('GH-11')

    def test_three_family_construction_versions_and_fidelity(self):
        """Build legacy/new HydroShare and frozen GH/Hub through actual adapters."""
        f=self.fixture(hs_fixture)
        source={'resource_id':f.owner,'abstract':f.quote,'documentation':{'readme_files':[
            {'source_file':'README.txt','readme_text_raw':f.other_quote}]}}
        for version in ('hydroshare-request/1.0.0','hydroshare-request/1.1.0'):
            q=hs_fixture.contract.build_request(**f.inputs,request_version=version)
            self.assertEqual(calibration.construct_request(self.root,self.row(q),source),q)
        f=self.fixture(gh_fixture);q=gh_fixture.contract.build_request(**f.inputs)
        source={'repo_id':7,'name':'Demo','full_name':'Example/Demo','archive':{'frozen_commit_sha':'a'*40},
            'readme':{'source_path':'README.md','text':'# Guide\n\n'+f.quote+'\n\n'+f.other_quote+'\n'},'files':{'downloaded':[]}}
        self.assertEqual(calibration.construct_request(self.root,self.row(q),source),q)
        f=self.fixture(hub_fixture);q=hub_fixture.contract.build_request(**f.inputs)
        self.assertEqual(calibration.construct_request(self.root,self.row(q),f.inputs['page']),q)

    def test_unit_hash_order_snapshot_and_nonoverwrite(self):
        """Drift cannot refresh stored artifacts or silently choose new text."""
        f=self.fixture(gh_fixture);q=gh_fixture.contract.build_request(**f.inputs);row=self.row(q)
        calibration.verify_request(q,row)
        for field,value in [('selectedTextSha256','0'*64),('startOffsetInAuthority',0),('selectionOrder',2)]:
            bad=deepcopy(row);bad['orderedUnits'][0][field]=value
            with self.assertRaises(ValueError):calibration.verify_request(q,bad)
        with self.assertRaises(FileNotFoundError):calibration._verified_bytes(self.root,'missing','0'*64)
        p=self.root/'snapshot';p.write_bytes(b'changed')
        with self.assertRaises(ValueError):calibration._verified_bytes(self.root,'snapshot','0'*64)
        result=build_preflight(q,output_ceiling=32768)
        with patch.object(calibration,'build_case',return_value=(q,result)),patch.object(calibration,'load_manifest',return_value={}):
            calibration.write_case(self.root,{},'GH-02')
            self.assertEqual(calibration.load_case(self.root,'GH-02'),result)
            calibration.write_case(self.root,{},'GH-02')
            target=self.root/calibration.PREFLIGHT_DIRECTORY/'GH-02/provider-input.txt'
            target.write_bytes(b'corrupted')
            with self.assertRaises(ValueError):calibration.write_case(self.root,{},'GH-02')
            with self.assertRaises(ValueError):calibration.load_case(self.root,'GH-02')
            self.assertEqual(target.read_bytes(),b'corrupted')

    def test_projected_routing_and_original_envelope_compatibility(self):
        """GH-01 is unchanged; new GH envelopes explicitly link projection/full hash."""
        f=self.fixture(gh_fixture);q=gh_fixture.contract.build_request(**f.inputs)
        legacy=build_preflight(q,output_ceiling=32768)
        path=self.root/'var/study2_step12c/preflight/GH-01/provider-envelope.json';path.parent.mkdir(parents=True);path.write_bytes(legacy['wireBytes'])
        with patch.object(calibration,'rebuild_request',return_value=q):
            _,old=calibration.build_case(self.root,{},'GH-01')
            _,new=calibration.build_case(self.root,{},'GH-02')
        self.assertEqual(old['wireBytes'],legacy['wireBytes'])
        self.assertIsNone(old['providerInputProjectionVersion'])
        self.assertEqual(new['providerInputProjectionVersion'],calibration.PROJECTION_VERSION)
        self.assertEqual(new['semanticRequestSha256'],q['requestSha256'])
        self.assertEqual(new['semanticRequestBytes'],old['semanticRequestBytes'])
        self.assertNotEqual(new['providerInputSha256'],old['providerInputSha256'])
        self.assertEqual(path.read_bytes(),legacy['wireBytes'])

    def approval(self,rid):
        """Create explicitly synthetic v2 authorization with synthetic context caps."""
        wave=calibration.wave_for(rid);now=datetime.now(timezone.utc)
        result={k:digest(k.encode()) for k in ('semanticRequestSha256','providerEnvelopeSha256','providerInputSha256','schemaSha256')}
        result.update(calibrationManifestSha256=calibration.MANIFEST_SHA256,calibrationRequestID=rid,
            calibrationWave=wave,requestVersion='github-request/1.0.0',promptIdentifier=None,
            providerInputProjectionVersion=calibration.projection_for(rid),conservativeInputTokenAllowance=100,
            wireBytes=b'wire',inputBytes=b'input',semanticRequestBytes=b'full request')
        selected={k:result[k] for k in ('semanticRequestSha256','providerEnvelopeSha256','providerInputSha256','schemaSha256',
            'requestVersion','promptIdentifier','providerInputProjectionVersion')}
        selected.update(wave=wave,maximumAttempts=1,reservedMaximumCost=1,inputTokenAllowance=110,
            providerOverheadTokenAllowance=10,contextTokenLimit=32878,outputTokenCeiling=32768)
        a=dict(schemaVersion='step12c-terminal-approval/2',authorized=True,approvalID='synthetic',researcher='fixture',
            approvedAt=(now-timedelta(minutes=1)).isoformat(),expiresAt=(now+timedelta(hours=1)).isoformat(),
            currency='TEST',pricingReference='synthetic',totalCostCap=2,manifestSha256=calibration.MANIFEST_SHA256,
            requests={rid:selected},waves={wave:dict(authorized=True,requestIDs=[rid],reservedCostCap=2)},waveClearances={})
        return a,result

    def verify(self,a,rid,result):
        """Check only synthetic reviewed bytes; no actual authorization is written."""
        raw=canonical(a);return runner.verify_approval(raw,digest(raw),rid,result)

    def test_wave_authorization_prior_clearance_and_no_auto_promotion(self):
        """Transport success is never prior-wave researcher clearance."""
        for rid,required in [('GH-02',[]),('GH-05',['A']),('GH-08',['A','B'])]:
            a,r=self.approval(rid)
            for prior in required:
                with self.assertRaisesRegex(ValueError,'clearance_required'):self.verify(a,rid,r)
                a['waveClearances'][prior]={'decision':'cleared_for_next_wave','researcher':'fixture',
                    'clearedAt':datetime.now(timezone.utc).isoformat(),'reviewRecordSha256':'a'*64}
            self.verify(a,rid,r)
            a['waves'][calibration.wave_for(rid)]['authorized']=False
            with self.assertRaises(ValueError):self.verify(a,rid,r)

    def test_v2_hash_version_wave_context_budget_fail_closed(self):
        """No caps, wrong projection or omitted per-ID authority can trigger a call."""
        a,r=self.approval('GH-02');self.verify(a,'GH-02',r)
        for key,value in [('manifestSha256','0'*64),('schemaVersion','step12c-terminal-approval/1'),('totalCostCap',.5)]:
            with self.assertRaises(ValueError):self.verify({**a,key:value},'GH-02',r)
        for key,value in [('providerInputSha256','0'*64),('requestVersion','other'),('wave','C'),
            ('providerInputProjectionVersion',None),('inputTokenAllowance',100),('contextTokenLimit',200),
            ('outputTokenCeiling',100),('providerOverheadTokenAllowance',0),('maximumAttempts',2)]:
            bad=deepcopy(a);bad['requests']['GH-02'][key]=value
            with self.assertRaises(ValueError):self.verify(bad,'GH-02',r)
        bad=deepcopy(a);bad['waves']['A']['requestIDs']=['GH-03']
        with self.assertRaises(ValueError):self.verify(bad,'GH-02',r)

    def test_historical_execution_blocked_before_sources_credentials_or_transport(self):
        """HS-01 cannot acquire a fresh attempt under any approval namespace."""
        with patch.object(runner,'load_selected',side_effect=AssertionError('source read')):
            with self.assertRaisesRegex(ValueError,'historical_request_not_dispatchable'):
                runner.execute(self.root,'HS-01',b'{}','x',key_loader=lambda:self.fail('key'),send=lambda *a:self.fail('network'))
        self.assertFalse((self.root/'var').exists())

    def test_v2_attempt_durability_credential_order_and_global_state(self):
        """One selected call persists associations and cannot be repeated or bypass STOP."""
        a,r=self.approval('GH-02');raw=canonical(a);calls=[]
        state=self.root/'var/study2_step12c/terminal'
        def key():
            """Credential resolution precedes the irreversible per-ID reservation."""
            self.assertFalse((state/'GH-02').exists());return 'SYNTHETIC'
        def send(*args):
            """Return an injected offline response; never HTTP."""
            calls.append(args[0]);return 200,canonical({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{}'}]}]})
        with patch.object(runner,'load_selected',return_value=r),patch('socket.socket',side_effect=AssertionError('network')):
            invalid=canonical({**a,'authorized':False})
            with self.assertRaises(ValueError):runner.execute(self.root,'GH-02',invalid,digest(invalid),key_loader=lambda:self.fail('key'),send=send)
            self.assertEqual(runner.execute(self.root,'GH-02',raw,digest(raw),key_loader=key,send=send),'response_recorded')
            with self.assertRaises(FileExistsError):runner.execute(self.root,'GH-02',raw,digest(raw),key_loader=lambda:'SYNTHETIC',send=send)
            (state/'dispatch.lock').mkdir()
            with self.assertRaises(FileExistsError):runner.execute(self.root,'GH-02',raw,digest(raw),key_loader=lambda:'SYNTHETIC',send=send)
            self.assertTrue((state/'dispatch.lock').is_dir())
            (state/'dispatch.lock').rmdir()
            (state/'STOP').write_text('test stop')
            with self.assertRaisesRegex(ValueError,'dispatch_blocked'):runner.execute(self.root,'GH-02',raw,digest(raw),key_loader=lambda:'SYNTHETIC',send=send)
        self.assertEqual(len(calls),1)
        association=json.loads((state/'GH-02/association.json').read_bytes())
        self.assertEqual(association['calibrationManifestSha256'],calibration.MANIFEST_SHA256)
        self.assertEqual(association['providerInputProjectionVersion'],calibration.PROJECTION_VERSION)
