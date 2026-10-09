"""Focused synthetic projection checks; no corpus, credential or network calls."""
from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch
import test_coderepos_semantic_offline_pipeline as fixture_module
from src.extraction.llm.coderepos import provider_input as projection
from src.extraction.llm import pilot_preflight as preflight


class ProviderProjectionTests(unittest.TestCase):
    """Protect exact evidence, conservative warning scope and historical replay."""

    def setUp(self):
        """Reuse only the small synthetic GitHub fixture."""
        self.fixture = fixture_module.OfflineReplayTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request = fixture_module.contract.build_request(**self.fixture.inputs)

    def resign(self, request):
        """Model caller-trusted request changes, never model-authored attestations."""
        request['requestSha256'] = hashlib.sha256(projection._bytes(request['request'], ascii_only=True)).hexdigest()
        return request

    def project(self, request=None):
        """Always opt in explicitly."""
        return projection.project_provider_input(self.request if request is None else request,
                                                version=projection.PROJECTION_VERSION)

    def test_exact_selected_units_and_separate_bytes_hashes(self):
        """Only audit lists change; all scientific text/provenance stays byte-exact."""
        before = deepcopy(self.request)
        with patch('socket.socket', side_effect=AssertionError('network')), patch('builtins.open', side_effect=AssertionError('IO')):
            result = self.project()
            self.assertEqual(result, self.project())
        body = json.loads(result['inputBytes'])
        for key, value in before['request'].items():
            if key not in ('sourceDiagnostics', 'sourceCompleteness'):
                self.assertEqual(value, body[key])
        self.assertEqual(self.request, before)
        self.assertEqual(result['semanticRequestBytes'], projection._bytes(before['request'], ascii_only=True))
        self.assertEqual(result['semanticRequestSha256'], before['requestSha256'])
        self.assertEqual(result['providerInputSha256'], hashlib.sha256(result['inputBytes']).hexdigest())
        self.assertEqual(body['sourceUnits'][0]['text'].encode(), before['request']['sourceUnits'][0]['text'].encode())
        body['sourceUnits'][0]['text'] = 'mutation'
        self.assertEqual(self.request, before)

    def test_scoped_warnings_failures_and_unknowns_survive(self):
        """Never hide selected, whole-file, global, unknown or conflicting warnings."""
        q = deepcopy(self.request)
        u = q['request']['sourceUnits'][0]
        base = {'status':'needs_review', 'reason':'content_kind_or_purpose_requires_review'}
        selected = {**base, 'path':u['path'], 'cellIndex':None,
                    'startOffsetInAuthority':u['startOffsetInAuthority'], 'endOffsetInAuthority':u['endOffsetInAuthority']}
        disjoint = {**base, 'path':u['path'], 'cellIndex':None,
                    'startOffsetInAuthority':u['endOffsetInAuthority'], 'endOffsetInAuthority':u['endOffsetInAuthority']+5}
        keep = [selected, base, {**base,'path':u['path']},
                {**base,'path':'other.md','reason':'new_visibility_rule'},
                {**base,'path':'other.md','sourceUnitID':u['sourceUnitID']},
                {**base,'path':'other.md','unexpectedDetail':'preserve'},
                {'status':'failed_source_or_evidence_binding','reason':'downloaded_file_missing','path':'other.md'}]
        q['request']['sourceDiagnostics'] = keep + [disjoint, {**base,'path':'other.md'}]
        q['request']['sourceCompleteness'].update(inputComplete=False, readerInputComplete=False,
                                                 reads=deepcopy(q['request']['sourceDiagnostics']))
        result = self.project(self.resign(q)); body=json.loads(result['inputBytes'])
        self.assertEqual(body['sourceDiagnostics'], keep)
        self.assertEqual(body['sourceCompleteness']['reads'], keep)
        self.assertFalse(body['sourceCompleteness']['inputComplete'])
        summary = body['providerInputProjection']['sourceDiagnostics']
        self.assertEqual(summary['omittedCount'], 2)
        self.assertEqual(summary['originalCount'], len(keep)+2)
        self.assertEqual(summary['originalRecordsSha256'], hashlib.sha256(projection._bytes(q['request']['sourceDiagnostics'],ascii_only=True)).hexdigest())
        # Cell-wide warning must not be compared to another cell's local offsets.
        unit = {**u,'cellIndex':2}
        self.assertFalse(projection._disjoint({**disjoint,'cellIndex':None},[unit]))
        self.assertTrue(projection._disjoint({**base,'path':u['path'],'cellIndex':3},[unit]))
        self.assertFalse(projection._disjoint({**base,'path':u['path'],'cellIndex':2},[unit]))

    def test_explicit_version_and_legacy_envelope_unchanged(self):
        """No silent projection; bind exact projected bytes to a separate envelope."""
        original=preflight.build_preflight(self.request,output_ceiling=32768)
        self.assertEqual(original['inputBytes'],preflight.canonical(self.request['request']))
        self.assertNotIn('providerInputProjectionVersion',original)
        projected=preflight.build_preflight(self.request,output_ceiling=32768,projection_version=projection.PROJECTION_VERSION)
        self.assertEqual(projected['semanticRequestBytes'],original['semanticRequestBytes'])
        self.assertEqual(projected['inputBytes'],self.project()['inputBytes'])
        self.assertEqual(json.loads(projected['wireBytes'])['input'].encode(),projected['inputBytes'])
        self.assertEqual(projected['providerEnvelopeSha256'],hashlib.sha256(projected['wireBytes']).hexdigest())
        for version in ('', 'unknown', [], None):
            with self.assertRaises(ValueError):projection.project_provider_input(self.request,version=version)
        corrupt=deepcopy(self.request);corrupt['request']['sourceUnits'][0]['text']='drift'
        with self.assertRaisesRegex(ValueError,'digest_mismatch'):self.project(corrupt)
        corrupt=deepcopy(self.request);corrupt['request']['artifactFamily']='hydroshare'
        with self.assertRaisesRegex(ValueError,'contract_mismatch'):self.project(self.resign(corrupt))
        with self.assertRaises(ValueError):self.project({'status':'request_failed'})

    def test_parser_and_replay_failure_isolation_unchanged(self):
        """Projection is transport only: full request still owns parse/replay failures."""
        payload=self.fixture.payload();bad=deepcopy(payload['candidateNodes'][0])
        bad.update(candidateID='bad',evidence=[{'sourceUnitID':'unselected','evidenceText':'invented'}])
        payload['candidateNodes'].append(bad)
        raw=json.dumps(payload).encode()
        before=self.fixture.replay(raw=raw)
        self.project()
        self.assertEqual(before,self.fixture.replay(raw=raw))
        rows=self.fixture.records(before)
        self.assertEqual(rows['tool']['finalDisposition'],'validated')
        self.assertEqual(rows['bad']['finalDisposition'],'rejected_invalid_assertion')
        parsed=fixture_module.contract.parse_recorded_response(raw,request=self.request)
        self.assertEqual(parsed['candidateRecords'][1]['parseDisposition'],'local_candidate_error')

    def test_notebook_code_and_outputs_never_enter_projection(self):
        """Only exact Markdown text and original cell coordinates reach transport."""
        import tempfile
        from pathlib import Path
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); contents=root/'Demo'/'contents'; contents.mkdir(parents=True)
            notebook={'cells':[{'cell_type':'code','source':['SECRET_CODE_SENTINEL()'],
                                'outputs':[{'text':['SECRET_OUTPUT_SENTINEL']}], 'execution_count':1},
                               {'cell_type':'markdown','source':['A café notebook describes a tool.\n']}]}
            (contents/'guide.ipynb').write_text(json.dumps(notebook))
            repo={'repo_id':7,'name':'Demo','full_name':'Example/Demo',
                  'archive':{'frozen_commit_sha':'a'*40}, 'readme':None,
                  'files':{'downloaded':[{'path':'guide.ipynb','downloaded':True,
                                        'selection_reason':'allowed_top_level_notebook','file_role':'notebook','extension':'.ipynb'}]}}
            reader=read_repository_sources(repo,root)
            unit=reader['sourceUnits'][0]
            owner={k:unit[k] for k in ('canonicalArtifactID','repo_id','full_name','frozenCommitSha')}
            q=fixture_module.contract.build_request(reader,accepted_repository=owner,
                 selected_unit_ids=[unit['sourceUnitID']],input_complete=False)
            result=self.project(q)
            for raw in (result['inputBytes'],result['semanticRequestBytes']):
                self.assertNotIn(b'SECRET_CODE_SENTINEL',raw)
                self.assertNotIn(b'SECRET_OUTPUT_SENTINEL',raw)
            self.assertEqual(json.loads(result['inputBytes'])['sourceUnits'],q['request']['sourceUnits'])
            self.assertEqual(unit['cellIndex'],1)
            self.assertEqual(unit['startOffsetInAuthority'],0)
