"""New synthetic tests for prospective GitHub documentary context and binding."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import github_full_document_pilot as p
from src.extraction.llm.pilot_preflight import strict_schema
from src.extraction.llm.coderepos.evidence_binding import bind_repository_evidence


class FullDocumentTests(unittest.TestCase):
    """Keep sockets disabled and all fixtures independent of the real corpus."""

    def setUp(self):
        """Create a trusted tiny authority and unchanged comparison configuration."""
        guard=patch.object(socket,'socket',side_effect=AssertionError('NO_NETWORK'))
        guard.start();self.addCleanup(guard.stop)
        self.owner=dict(canonicalArtifactID='github:repo:1',repo_id=1,full_name='test/repo',frozenCommitSha='a'*40)
        self.text='# Heading\n\n| Function | Role |\n| route_flow | Routes water through channels |\n\n```python\nroute_flow(x)\n```\n'
        self.authority=self.make_authority(self.text)
        historical=dict(authorities=[self.authority],sourceUnits=[],reads=[],diagnostics=[],inputComplete=False)
        semantic=p.contract._finish(dict(self.owner,endpointID='github:repo:1',inventoryId='A-C01',**{'class':'Repository'}),
            [],[],{},[],[],[],request_version=p.contract.WAVE_C_REQUEST_VERSION)
        self.template=dict(semanticRequest=semantic,requestInputs=dict(reader_result=historical,
            accepted_repository=self.owner,accepted_endpoints=[],accepted_assertions=[]),
            body=dict(model='gpt-6.1-sol',reasoning={'effort':'medium'},max_output_tokens=32768,store=False,
            text={'format':{'strict':True,'type':'json_schema','schema':strict_schema(p.contract._schema(),semantic['request']['targetProfile'])}},input='old'))

    def make_authority(self,text,path='README.md',cell=None):
        """Retain original cell index and physical versus decoded hashes separately."""
        return dict(self.owner,artifactFamily='github',contractID=p.sources.CONTRACT_ID,path=path,
            cellIndex=cell,text=text,authorityTextSha256=p.digest(text.encode()),
            authorityKind='phase_a_readme' if path=='README.md' else 'downloaded_file',
            extension=Path(path).suffix,selection_reason='allowed_path_prefix',rawFileSha256='b'*64,
            decodePolicy='unchanged fixture')

    def build(self,authorities=None):
        """Construct only this prospective synthetic request."""
        return p.build(self.template,authorities or [self.authority])

    def bind(self,prepared,quote,**extra):
        """Bind against the new full documentary authority, not historical units."""
        reader=prepared['requestInputs']['prospectiveReader'];uid=reader['sourceUnits'][0]['sourceUnitID']
        return p.bind_document_evidence(reader,uid,[dict(evidenceText=quote,**extra)],accepted_repository=self.owner)

    def test_complete_context_and_unchanged_profile_schema_settings(self):
        """Full text remains exact; historical selection metadata stays private."""
        before=deepcopy(self.template);prepared=self.build();payload=json.loads(prepared['body']['input'])
        self.assertEqual(payload['sourceUnits'][0]['text'],self.text)
        self.assertNotIn('sourceDiagnostics',payload)
        self.assertEqual(self.template,before)
        for key in ('model','reasoning','max_output_tokens','store','text'):
            self.assertEqual(prepared['body'][key],self.template['body'][key])
        self.assertEqual(payload['targetProfile'],self.template['semanticRequest']['request']['targetProfile'])
        self.assertIn('NOT an eligibility prerequisite',' '.join(payload['instructions']))
        self.assertEqual(prepared['requestInputs']['reader_result']['sourceUnits'],[])

    def test_outside_historical_units_binds_original_offsets(self):
        """Markup-filtered explanation is bindable without a historical-unit gate."""
        prepared=self.build();quote='Routes water through channels';bound=self.bind(prepared,quote)
        self.assertEqual(bound['status'],'evidence_bound')
        span=bound['evidenceSpans'][0]
        self.assertEqual(span['startOffsetInAuthority'],self.text.index(quote))
        self.assertEqual(span['frozenCommitSha'],'a'*40)
        self.assertFalse(bound['kgAuthorization'])
        self.assertEqual(bound['semanticStatus'],'not_evaluated')

    def test_code_only_and_ambiguous_quotes_do_not_pass(self):
        """Explicit code is held; ambiguity never fabricates coordinates."""
        self.assertEqual(self.bind(self.build(),'route_flow(x)')['status'],'needs_review')
        repeated=self.build([self.make_authority('repeat repeat')])
        self.assertEqual(self.bind(repeated,'repeat')['status'],'failed_source_or_evidence_binding')
        self.assertEqual(self.bind(repeated,'missing')['evidenceSpans'],[])
        self.assertEqual(self.bind(repeated,'repeat',locatorAnchor='repeat repeat')['status'],'failed_source_or_evidence_binding')
        rst=self.build([self.make_authority('Description.\n\n.. code-block:: python\n\n    route_flow(x)\n','docs/test.rst')])
        self.assertEqual(self.bind(rst,'route_flow(x)')['status'],'needs_review')

    def test_notebook_original_markdown_indices_and_empty_cell(self):
        """All supplied original Markdown cells retain independent cell coordinates."""
        authorities=[self.make_authority('First explanation','docs/test.ipynb',0),
                     self.make_authority('','docs/test.ipynb',2),
                     self.make_authority('# Last explanation','docs/test.ipynb',5)]
        prepared=self.build(authorities);units=prepared['semanticRequest']['request']['sourceUnits']
        self.assertEqual([u['cellIndex'] for u in units],[0,2,5])
        self.assertEqual([u['text'] for u in units],[a['text'] for a in authorities])
        reader=prepared['requestInputs']['prospectiveReader']
        bound=p.bind_document_evidence(reader,units[2]['sourceUnitID'],[{'evidenceText':'Last explanation'}],accepted_repository=self.owner)
        self.assertEqual(bound['evidenceSpans'][0]['cellIndex'],5)
        self.assertEqual(bound['evidenceSpans'][0]['startOffsetInAuthority'],2)

    def test_notebook_full_markdown_and_no_code_outputs(self):
        """Raw original cells must exactly match the complete selected Markdown set."""
        raw=json.dumps({'cells':[{'cell_type':'markdown','source':['First',' explanation']},
            {'cell_type':'code','source':'SECRET_CODE','outputs':['SECRET_OUTPUT']},
            {'cell_type':'markdown','source':'Last explanation'}]}).encode()
        authorities=[self.make_authority('First explanation','docs/test.ipynb',0),
                     self.make_authority('Last explanation','docs/test.ipynb',2)]
        p.verify_notebook(raw,authorities)
        visible=self.build(authorities)['body']['input']
        self.assertNotIn('SECRET_CODE',visible);self.assertNotIn('SECRET_OUTPUT',visible)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_NOTEBOOK_MARKDOWN'):
            p.verify_notebook(raw,authorities[:1])
        authorities[0]['text']='normalized'
        with self.assertRaisesRegex(ValueError,'NOTEBOOK_TEXT_DRIFT'):
            p.verify_notebook(raw,authorities)

    def test_hash_identity_exclusions_and_output_isolation(self):
        """Technical drift and special eligibility cannot be bypassed by this pilot."""
        changed=deepcopy(self.authority);changed['text']+='changed'
        with self.assertRaisesRegex(ValueError,'HASH_DRIFT'):self.build([changed])
        changed=deepcopy(self.authority);changed['frozenCommitSha']='c'*40
        with self.assertRaisesRegex(ValueError,'OWNER_DRIFT'):self.build([changed])
        for name in ('CHANGELOG.md','CONTRIBUTING.md','ODbl.md','LICENSE.txt','.github/guide.md','code.py','requirements.txt','config.yaml'):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'FILE_NOT_PILOT_ELIGIBLE'):
                    self.build([self.make_authority('Excluded',name)])
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);out=repo/p.BASE;out.mkdir(parents=True);(out/'keep').write_text('original')
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):p.prepare(repo)
            self.assertEqual((out/'keep').read_text(),'original')

    def test_native_candidate_semantic_gates_and_historical_binder_unchanged(self):
        """Only the call-local binder changes; semantic gates and invalid targets survive."""
        prepared=self.build();uid=prepared['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID']
        node=dict(candidateID='function',inventoryId='A-C08',**{'class':'Function'},label='route_flow',
            evidence=[dict(sourceUnitID=uid,evidenceText='Routes water through channels')])
        result=p.validate_candidates(prepared,dict(candidateNodes=[node],candidateEdges=[]))
        check=result['candidateChecks'][0]
        self.assertTrue(check['boundEvidence'])
        self.assertTrue(any(f['reason']=='semantic_gates_pending' for f in check['findings']))
        self.assertFalse(result['kgAuthorization'])
        self.assertIs(p.validation.bind_repository_evidence,bind_repository_evidence)
        node['class']='InventedClass'
        bad=p.validate_candidates(prepared,dict(candidateNodes=[node],candidateEdges=[]))
        self.assertEqual(bad['candidateChecks'][0]['disposition'],'rejected_invalid_assertion')
        self.assertEqual(p.contract.parse_recorded_response('{}',request=prepared['semanticRequest'])['status'],'processing_failed')

    def test_prospective_response_schema_and_abstention_preservation(self):
        """Use the actual copied strict schema without calling the historical parser."""
        from jsonschema import ValidationError
        prepared=self.build()
        payload=dict(schemaVersion=p.contract.RESPONSE_VERSION,candidateNodes=[],candidateEdges=[],abstentions=[])
        raw=json.dumps(payload).encode()
        with patch.object(p.contract,'parse_recorded_response',side_effect=AssertionError('NO_HISTORICAL_PARSER')):
            result=p.validate_recorded_response(prepared,raw)
        self.assertEqual(result['responseSha256'],p.digest(raw))
        self.assertEqual(result['originalAbstentions'],[])
        self.assertFalse(result['kgAuthorization'])
        payload['kgAuthorization']=True
        with self.assertRaises(ValidationError):
            p.validate_recorded_response(prepared,json.dumps(payload).encode())

    def test_purpose_projection_keeps_category_and_endpoint_checks(self):
        """Purpose reuse changes no seed identity or repository-specific semantic gate."""
        prepared=self.build();uid=prepared['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID']
        edge=dict(candidateID='purpose',inventoryId='C-C07',relation='hasPurpose',classification='proposed',
            categoryKey='software_infrastructure',source={'referenceType':'accepted_endpoint','referenceID':'github:repo:1'},
            target={'referenceType':'accepted_endpoint','referenceID':'repo-purpose:1.0.0:software_infrastructure'},
            evidence=[dict(sourceUnitID=uid,evidenceText='Routes water through channels')])
        result=p.validate_candidates(prepared,dict(candidateNodes=[],candidateEdges=[edge]))
        check=result['candidateChecks'][0]
        self.assertTrue(check['boundEvidence'])
        self.assertEqual(check['purposeChecks'][0]['result']['diagnostics'],[])
        self.assertEqual(check['disposition'],'unresolved_condition')
        edge['categoryKey']='invented'
        bad=p.validate_candidates(prepared,dict(candidateNodes=[],candidateEdges=[edge]))
        self.assertEqual(bad['candidateChecks'][0]['disposition'],'rejected_invalid_assertion')


if __name__=='__main__':unittest.main()
