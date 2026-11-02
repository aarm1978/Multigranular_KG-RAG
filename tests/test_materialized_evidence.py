"""Focused offline amendment tests; historical defaults and exact evidence survive."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import test_source_local_semantics_v041 as fixtures
from test_source_local_semantics import template
from src.extraction.llm import materialized_evidence as m
from src.evaluation import source_local_supplemental_review_v4 as review


class BindingTests(unittest.TestCase):
    build=fixtures.CorrectionTests.build
    node=fixtures.CorrectionTests.node
    edge=fixtures.CorrectionTests.edge
    run_payload=fixtures.CorrectionTests.run_payload

    def setUp(self):
        """Block sockets and cache ontology only within each test."""
        fixtures.CorrectionTests.setUp(self)
        self.enterContext(review.old.production.ontology_parse_cache())

    def test_materialized_forms_and_original_offsets(self):
        """Literal explanatory text is eligible in every presentation, not inferred output."""
        q='RiverTool processes streamflow.'
        forms=['<Tabs><Tab>'+q+'</Tab></Tabs>', '<GitHubReadme>'+q+'</GitHubReadme>',
            '<!-- '+q+' -->', '<Unknown attr={state}>'+q+'</Unknown>', '<div>'+q,
            ':::unclosed\n'+q, '```config\n'+q+'\n```', 'Prose\n```code\n'+q+'\n```']
        for text in forms:
            p=self.build('ciroh_hub',text); original=deepcopy(p)
            with m.overlay():r=self.run_payload(p,[self.node(p,'A-DOM02','Tool',q)],[])
            self.assertEqual(len(r['projection']['nodes']),1,r['decisions'])
            e=r['projection']['nodes'][0]['boundEvidence'][0]
            self.assertEqual((e['startOffsetInAuthority'],e['endOffsetInAuthority']),(text.index(q),text.index(q)+len(q)))
            self.assertEqual(p,original)
        # Leaving the scope restores the historical opaque-wrapper hold.
        r=self.run_payload(p,[self.node(p,'A-DOM02','Tool',q)],[])
        self.assertFalse(r['projection']['nodes'])

    def test_parent_and_independent_edge(self):
        """Reuse the positive and broken-attachment regression under the new route."""
        with m.overlay():fixtures.CorrectionTests.test_positive_parameter_parent_path(self)

    def test_example_parent(self):
        """Parent-bound Examples still traverse normal closure."""
        with m.overlay():fixtures.CorrectionTests.test_example_remains_parent_bound(self)

    def test_identity_hash_and_absent_evidence(self):
        """No presentation decision can bypass trusted authority or literal matching."""
        p=self.build('ciroh_hub','RiverTool processes streamflow.')
        inputs=deepcopy(p['requestInputs']);inputs['page']['content_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'CONTENT_SHA256_DRIFT'):m.hub_binder(inputs)
        inputs=p['requestInputs'];bind=m.hub_binder(inputs)
        result=bind(inputs['page'],inputs['reader_result'],'wrong', [{'evidenceText':'RiverTool'}],accepted_page_id=inputs['accepted_page_id'])
        self.assertEqual(result['status'],'failed_source_or_evidence_binding')
        with m.overlay():r=self.run_payload(p,[self.node(p,'A-DOM02','Tool','Absent output')],[])
        self.assertFalse(r['projection']['nodes'])

    def test_github_code_format_and_method_hold(self):
        """Explanatory literal code-formatted content is eligible; Method is not invented."""
        q='Streamflow is the output variable.';p=self.build('github','```text\n'+q+'\n```')
        with m.overlay():r=self.run_payload(p,[self.node(p,'A-DOM04','Variable',q)],[])
        self.assertTrue(r['projection']['nodes'])
        self.assertFalse(self.run_payload(p,[self.node(p,'A-DOM04','Variable',q)],[])['projection']['nodes'])

    def test_independent_semantics_and_duplicate_gates(self):
        """Unresolved Method, structured versions and duplicate rules are unchanged."""
        from test_source_local_semantics import SourceLocalTests
        with m.overlay():
            SourceLocalTests.test_method_positive_unresolved(self)
            SourceLocalTests.test_model_version_requires_structured_own_product_proof(self)
            SourceLocalTests.test_independent_evidence_and_abstention(self)
            SourceLocalTests.test_stable_local_ids_and_duplicate_nodes(self)

    def test_semantic_gate_not_attested_by_binding(self):
        """Bound syntax never manufactures a positive semantic gate attestation."""
        p=self.build('ciroh_hub','<!-- start_date -->')
        parameter=self.node(p,'A-DOM12','Parameter','start_date')
        parameter['parentPath']=[]
        with m.overlay():r=self.run_payload(p,[parameter],[])
        self.assertFalse(r['projection']['nodes'])
        check=r['originalReplay']['validationResult']['candidateChecks'][0]
        self.assertIn('explanatory_parameter_prose',check['targetProfileCheck']['pendingGates'])
        self.assertTrue(check['boundEvidence'])
        self.assertTrue(r['unresolvedAssertions'])

    def test_prospective_envelopes_preserve_sources(self):
        """All specialized targets remain executable with a separately versioned prompt."""
        from src.extraction.llm import source_local_specialized as specialized
        for family in ('ciroh_hub','github','hydroshare'):
            t=template(family,'A complete source document.');original=deepcopy(t)
            bundles=m.build_specialized([t]);self.assertEqual(len(bundles),3)
            with m.prospective():
                for p in bundles:
                    specialized.verify(p)
                    body=p['semanticRequest']['request']
                    self.assertEqual(body['evidenceAuthority'],m.AUTHORITY)
                    self.assertIn(m.VERSION,body['promptIdentifier'])
                    self.assertNotIn('excludes code-only/dynamic/uncertain',' '.join(body['instructions']))
                    self.assertNotIn('A displayed fence may support only',' '.join(body['instructions']))
                    self.assertIn('Do not infer absent outputs, execution or scientific results.',' '.join(body['instructions']))
            self.assertEqual(t,original)

    def test_new_specialized_replay_and_complete_consolidation(self):
        """New envelopes have a reproducible executable validation and owner path."""
        from src.extraction.llm import source_local_specialized as specialized
        from src.extraction.llm.pilot_preflight import canonical
        bundles=m.build_specialized([template('ciroh_hub','No specified scientific assertion.')])
        reports=[]
        for p in bundles:
            raw=canonical(dict(schemaVersion=m.VERSION,candidateNodes=[],candidateEdges=[],abstentions=[]))
            report=m.replay_specialized(p,raw,expected_request_sha256=p['semanticRequest']['requestSha256'])
            self.assertEqual(report['evidenceAuthority'],m.AUTHORITY)
            reports.append((p,report))
        with m.prospective():
            owner=specialized.consolidate(reports)
            self.assertTrue(owner['zeroYield'])
            with self.assertRaisesRegex(ValueError,'INCOMPLETE_OWNER_GROUPS'):specialized.consolidate(reports[:1])
            with self.assertRaisesRegex(ValueError,'DUPLICATE_GROUP_REPORT'):specialized.consolidate(reports+[reports[0]])


class PublicationsTests(unittest.TestCase):
    def test_prospective_code_and_historical_restoration(self):
        """Code eligibility changes only in scope; genuine source-quality failures survive."""
        from src.extraction.llm.publications import source_units as s, materialized_source_units as p
        block=s.Span(0,12,'code')
        historical=s._eligibility('body',[block]);metadata=s._block_metadata([block],False)
        with p.overlay():
            self.assertEqual(s._eligibility('body',[block]),('eligible',[],True))
            self.assertTrue(s._block_metadata([block],False)[0]['evidenceEligible'])
            self.assertFalse(s._eligibility('references',[block])[2])
        self.assertEqual(s._eligibility('body',[block]),historical)
        self.assertEqual(s._block_metadata([block],False),metadata)

    def test_real_builder_preserves_exact_text_offsets(self):
        """The prospective builder produces new units without touching historical objects."""
        from test_publication_source_unit_builder import fixture_record
        from src.extraction.llm.publications import source_units as s, materialized_source_units as p
        raw=b'# Methods\n\n```text\nA named parameter selects the retrieval period.\n```\n'
        before,_=s.build_document_units(fixture_record(),raw,'1.1.0','1.0.9')
        original=deepcopy(before)
        after,metadata=p.build_document_units(fixture_record(),raw,'1.1.0','1.0.9')
        self.assertEqual(metadata['evidenceAuthority'],m.AUTHORITY)
        self.assertTrue(any(u['requestEligible'] for u in after))
        for u in after:
            self.assertEqual(u['text'],raw.decode()[u['startOffsetInDocument']:u['endOffsetInDocument']])
            self.assertEqual(u['contractVersion'],p.VERSION)
        self.assertEqual(before,original)
        self.assertEqual(before,s.build_document_units(fixture_record(),raw,'1.1.0','1.0.9')[0])


if __name__=='__main__':unittest.main()
