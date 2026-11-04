"""No-network tests for concise context, immutable binding and durable live-run resumption."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from src.evaluation import step14_identity_live as m
from tests.test_step14_semantic_identity_pilot import occurrence, hub, node, SPEC


class LiveTests(unittest.TestCase):
    def setUp(self):
        """Block all networking; every provider response below is synthetic."""
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NETWORK')))
        self.schema=json.loads(m.pilot.SCHEMA.read_bytes())
        nodes=[node('a',doi='10.1234/x'),node('b',curated=False,doi='10.1234/x')]
        groups=m.pilot.select_groups([(1,hub())],{'pilotQueue':[]},{})
        self.package=m.pilot.prepare(groups,dict(nodes=nodes,edges=[]),[occurrence(n) for n in nodes],[],[],SPEC,self.schema)
        self.case=self.package['cases'][0]
        self.a=m.assemble(self.case,self.package['occurrences'],[],self.schema,'C001',16384)

    def recommendation(self, assembled=None):
        """Abstain explicitly on every exact request-local occurrence."""
        a=assembled or self.a;visible=json.loads(a['body']['input'])
        return dict(status='recommendation_only',caseID=a['custom_id'],assessments=[],
            unassessedOccurrenceIDs=[r['occurrenceID'] for r in visible['occurrences']],abstentionReason='Insufficient detail')

    def response(self, assembled=None):
        """Return a completed mock Responses object with actual usage fields."""
        return dict(id='fixture-response',model=m.MODEL,status='completed',usage={'input_tokens':100,'output_tokens':20,'total_tokens':120},
            output=[{'type':'message','content':[{'type':'output_text','text':json.dumps(self.recommendation(assembled))}]}])

    def layout(self, root, assembled=None):
        """Write a tiny hash-protected run, avoiding actual corpus preparation."""
        aa=assembled or [self.a]
        for a in aa:
            m.save(root/'requests'/f"{a['custom_id']}.json",a['body']);m.save(root/'audit'/f"{a['custom_id']}.json",a['audit'])
        m.save(root/'recommendation.schema.json',self.schema)
        manifest=dict(version=m.VERSION,runnerSha256=m.identity.sha(Path(m.__file__)),sourceManifestSha256=m.INPUT_PIN,
            model=m.MODEL,reasoningEffort='medium',inputHashes={},implementationHashes={},
            outputHashes={str(p.relative_to(root)):m.identity.sha(p) for p in root.rglob('*') if p.is_file()},
            cases=[{'caseID':a['custom_id']} for a in aa],smokeCaseIDs=[aa[0]['custom_id']])
        m.save(root/'manifest.json',manifest)

    def test_compaction_preserves_evidence_scope_without_hash_narrative(self):
        """Remove administrative wrappers while keeping complete scientific text and versions."""
        occ=deepcopy(self.package['occurrences']);occ[0]['evidence'][0]['excerpt']='full original text '*10000
        occ[0]['fields']['attributes']['value'].update(version='2',description='technical detail',internalLineage={'phaseAVersion':'history'},authoritySha256='administrative')
        occ[0]['fields']['identifierDeclarations']['value']=[{'scheme':'literal','value':'https://example.org','basis':'accepted_source_local_candidate'}]
        before=deepcopy(occ);a=m.assemble(self.case,occ,[],self.schema,'C001',16384);v=json.loads(a['body']['input'])
        self.assertEqual(occ,before);self.assertGreater(a['sizes']['requestBytes'],96000)
        self.assertEqual(v['evidence'][0]['text'],occ[0]['evidence'][0]['excerpt'])
        self.assertEqual(v['occurrences'][0]['attributes']['version'],'2')
        self.assertEqual(v['occurrences'][0]['identifierDeclarations'][0]['recordedIdentifierScope'],'source_local_literal_declaration')
        for forbidden in ('caseSha256','recordSha256','internalLineage','authoritySha256','canonicalJsonExcerpt'):
            self.assertNotIn(forbidden,a['body']['input'])
        self.assertEqual(m.encode(a['body']).__len__(),a['sizes']['requestBytes'])
        self.assertEqual(a['body']['reasoning'],{'effort':'medium'});self.assertFalse(a['body']['store'])

    def test_original_field_and_evidence_hydration(self):
        """Exact pointers restore truncated values; any hash drift fails closed."""
        occ=deepcopy(self.package['occurrences']);field=occ[0]['fields']['attributes'];value={'label':'full','description':'all details'}
        field.update(truncated=True,valueSha256=m.pilot.candidates.token(value));field.pop('value')
        resolved=lambda refs,pins:{m.token(field['reference']):value}
        expanded,_=m.materialize_context(occ,[],{},resolved)
        self.assertEqual(expanded[0]['fields']['attributes']['value'],value)
        field['valueSha256']='wrong'
        with self.assertRaisesRegex(ValueError,'FIELD_HASH_DRIFT'):m.materialize_context(occ,[],{},resolved)

    def test_alias_binding_preserves_contract_and_raw_object(self):
        """Headers are application-bound only; no model assessment is repaired or accepted."""
        rec=self.recommendation();raw=json.dumps(rec).encode()
        bound=m.bind_recommendation(raw,self.a['body'],self.a['audit'],self.schema)
        self.assertEqual(bound['modelAuthored'],rec)
        self.assertEqual(bound['applicationBound']['unassessedOccurrenceIDs'],['a','b'])
        self.assertEqual(bound['applicationBound']['caseID'],self.case['caseID'])
        rec['unassessedOccurrenceIDs']=['O999']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_ALIAS'):m.bind_recommendation(json.dumps(rec).encode(),self.a['body'],self.a['audit'],self.schema)
        rec=self.recommendation();rec['unassessedOccurrenceIDs']=['O001','O001','O002']
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):m.bind_recommendation(json.dumps(rec).encode(),self.a['body'],self.a['audit'],self.schema)

    def test_completed_resume_does_not_call_and_usage_survives(self):
        """A completed recommendation is protected; raw text and every usage record persist."""
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp)):
            root=Path(temp)/'run';self.layout(root);calls=[]
            def call(body):
                """Count a single synthetic dispatch."""
                calls.append(body);return self.response()
            result=m.execute(root,call=call);again=m.execute(root,call=call)
            self.assertEqual(len(calls),1);self.assertEqual(result,again)
            self.assertEqual(result['knownUsage']['total_tokens'],120)
            attempt=root/'attempts'/'C001'/'0001'
            self.assertEqual((attempt/'raw-model-output.txt').read_bytes(),json.dumps(self.recommendation()).encode())
            self.assertTrue((attempt/'validated-recommendation.json').exists())
            (root/'requests'/'C001.json').write_text('drift')
            with self.assertRaisesRegex(ValueError,'INPUT_HASH_DRIFT'):m.execute(root,call=call)

    def test_raw_response_crash_replays_without_post(self):
        """If the provider response was durable, recovery performs only local validation."""
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.layout(root)
            attempt=root/'attempts'/'C001'/'0001';m.save(attempt/'request.json',self.a['body'])
            m.save(attempt/'started.json',{'requestBodySha256':m.token(self.a['body'])});m.save(attempt/'provider-response.json',self.response())
            def forbidden(body):
                """Any repost would be a regression."""
                raise AssertionError('REPOST')
            result=m.attempt_case(root,'C001',forbidden)
            self.assertEqual(result['status'],'validated_recommendation_only')

    def test_ambiguous_timeout_never_automatically_reposts(self):
        """Unknown remote outcomes need an explicit duplicate-risk acknowledgement."""
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.layout(root);calls=[]
            def fail(body):
                """Simulate a timeout after a possibly accepted POST."""
                calls.append(body);raise TimeoutError()
            self.assertEqual(m.attempt_case(root,'C001',fail)['status'],'remote_outcome_unknown')
            m.attempt_case(root,'C001',fail);self.assertEqual(len(calls),1)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_RISK_ACK_REQUIRED'):m.attempt_case(root,'C001',fail,retry=True)
            result=m.attempt_case(root,'C001',lambda b:self.response(),retry=True,allow_duplicate_risk=True)
            self.assertEqual(result['status'],'validated_recommendation_only')
            self.assertTrue((root/'attempts'/'C001'/'0001'/'transport-error.json').exists())

    def test_refusal_incomplete_and_wrong_model_keep_raw_without_recommendations(self):
        """Provider failures retain auditable usage/output and never become recommendations."""
        for mutation in ({'status':'incomplete','incomplete_details':{'reason':'max_output_tokens'}},{'model':'other-model'}):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.layout(root);response=self.response();response.update(mutation)
                result=m.attempt_case(root,'C001',lambda b:response)
                self.assertEqual(result['status'],'validation_failed');self.assertEqual(result['usage']['total_tokens'],120)
                self.assertTrue((root/'attempts'/'C001'/'0001'/'raw-model-output.txt').exists())
                self.assertFalse((root/'attempts'/'C001'/'0001'/'validated-recommendation.json').exists())

    def test_explicit_live_gate_and_bounded_concurrency(self):
        """No implicit key load/call; selected requests run at the configured bound."""
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp)):
            root=Path(temp)/'run';assembled=[m.assemble(self.case,self.package['occurrences'],[],self.schema,f'C{i:03d}',16384) for i in range(1,5)];self.layout(root,assembled)
            with patch.object(m.provider,'load_openai_api_key',side_effect=AssertionError('KEY')):
                with self.assertRaisesRegex(ValueError,'LIVE_FLAG_REQUIRED'):m.execute(root)
            active=0;peak=0;lock=threading.Lock();lookup={a['custom_id']:a for a in assembled}
            def call(body):
                """Measure simultaneous mocked requests."""
                nonlocal active,peak
                with lock:active+=1;peak=max(peak,active)
                time.sleep(.01)
                cid=json.loads(body['input'])['caseID']
                with lock:active-=1
                return self.response(lookup[cid])
            result=m.execute(root,selection='all',concurrency=2,call=call)
            self.assertLessEqual(peak,2);self.assertEqual(result['statusCounts'],{'validated_recommendation_only':4})

    def test_offline_preparation_hashes_batch_identity_and_oversize_reconstruction(self):
        """Reconstruct a withheld payload from audit files, with no provider or key use."""
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'pilot';source.mkdir()
            files={'review-cases.jsonl':self.package['cases'],'occurrence-context.jsonl':self.package['occurrences'],
                'accepted-relation-context.jsonl':self.package['relations'],
                'review-requests.jsonl':[dict(caseID=self.case['caseID'],requestSizeExceeded=True,payload=None)]}
            for name,rows in files.items():m.write(source/name,b''.join(m.encode(r)+b'\n' for r in rows))
            m.save(source/'recommendation.schema.json',self.schema)
            m.save(source/'manifest.json',dict(inputHashes={},outputHashes={p.name:m.identity.sha(p) for p in source.iterdir()}))
            before={p.name:p.read_bytes() for p in source.iterdir()}
            with patch.object(m,'INPUT',source),patch.object(m,'INPUT_PIN',m.identity.sha(source/'manifest.json')),patch.object(m,'ROOT',root/'out'),patch.object(m.provider,'load_openai_api_key',side_effect=AssertionError('KEY')):
                a=root/'out'/'a';b=root/'out'/'b';manifest=m.prepare(a);m.prepare(b)
                self.assertEqual({str(p.relative_to(a)):p.read_bytes() for p in a.rglob('*') if p.is_file()},
                                 {str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file()})
                self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})
                request=json.loads((a/'batch-compatible-requests.jsonl').read_text())
                self.assertEqual(request['body'],m.load(a/'requests'/'C001.json'))
                self.assertTrue(manifest['cases'][0]['previouslyWithheld']);self.assertFalse(manifest['cases'][0]['contextGaps'])
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):m.prepare(a)
                (source/'review-cases.jsonl').write_text('drift')
                with self.assertRaisesRegex(ValueError,'INPUT_HASH_DRIFT'):m.prepare(root/'out'/'c')

    def test_accepted_declaration_quotes_are_not_dropped_as_metadata(self):
        """Additional accepted declaration text gets an exact evidence binding, without shortening."""
        occ=deepcopy(self.package['occurrences']);decl={'evidenceText':'recorded quote '*200,'sourceArtifact':'paper:other','citationRole':'reference','version':'snapshot'}
        occ[0]['fields']['attributes']['value']['sourceDeclarations']=[decl]
        hydrated,_=m.materialize_context(occ,[],{},lambda refs,pins:{})
        a=m.assemble(self.case,hydrated,[],self.schema,'C001',16384);visible=json.loads(a['body']['input'])
        self.assertIn(decl['evidenceText'],[e['text'] for e in visible['evidence']])
        self.assertEqual(a['audit']['recoveredAcceptedDeclarationQuotes'],1)
        rec=self.recommendation(a);rec['unassessedOccurrenceIDs']=[]
        ev=next(e['evidenceID'] for e in visible['evidence'] if e['text']==decl['evidenceText'])
        rec['assessments']=[dict(occurrenceIDs=['O001','O002'],identityLevel='reference_target',recommendation='shared_reference_target_only',
            granularityAssessment='record',versionAssessment='unknown',ownerReferenceAssessment='reference',evidenceIDs=[ev],
            conflictEvidenceIDs=[],rationale='fixture recommendation only',missingInformation=[])]
        bound=m.bind_recommendation(json.dumps(rec).encode(),a['body'],a['audit'],self.schema)
        self.assertEqual(bound['applicationBound']['assessments'][0]['occurrenceIDs'],['a','b'])

    def test_process_lock_excludes_second_runner(self):
        """Two concurrent processes cannot POST the same prepared run."""
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp)):
            root=Path(temp)/'run';self.layout(root)
            with (root/'.execution.lock').open('a') as lock:
                m.fcntl.flock(lock,m.fcntl.LOCK_EX|m.fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,'RUN_ALREADY_ACTIVE'):m.execute(root,call=lambda body:self.response())
            self.assertFalse((root/'attempts').exists())


if __name__=='__main__':unittest.main()
