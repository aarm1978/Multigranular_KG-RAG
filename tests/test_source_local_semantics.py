"""Focused prospective end-to-end examples; synthetic sources and sockets blocked."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from jsonschema import ValidationError

from src.extraction.llm import source_local_semantics as s
from src.extraction.llm import source_local_profile as policy
from src.extraction.llm.pilot_preflight import canonical, digest


def template(family, text, endpoints=None, assertions=None):
    """Construct minimal real native source authorities, never provider fixtures."""
    contract=importlib.import_module('src.extraction.llm.'+s.DIRECTORIES[family]+'.request_contract')
    endpoints=endpoints or [];assertions=assertions or []
    if family=='github':
        from src.evaluation import github_full_document_pilot as full
        owner=dict(canonicalArtifactID='github:repo:1',repo_id=1,full_name='test/repo',frozenCommitSha='a'*40)
        authority=dict(owner,artifactFamily=family,contractID=full.sources.CONTRACT_ID,path='README.md',cellIndex=None,
            text=text,authorityTextSha256=digest(text.encode()),authorityKind='phase_a_readme',extension='.md',selection_reason='allowed_path_prefix',rawFileSha256='b'*64)
        inputs=dict(accepted_repository=owner,reader_result=dict(authorities=[authority],sourceUnits=[],reads=[],diagnostics=[],inputComplete=True))
        owner={**owner,'endpointID':owner['canonicalArtifactID'],'inventoryId':'A-C01','class':'Repository'}
        units=[];version=contract.WAVE_C_REQUEST_VERSION
    elif family=='ciroh_hub':
        from src.extraction.llm.documents.source_units import read_page_source_units
        url='https://example.test/page';oid='hub:page:'+digest(url.encode())[:20]
        page=dict(page_key='hub-page:'+url,canonical_url=url,content_mdx=text,content_sha256=digest(text.encode()),source_path='page.mdx',corpus_path='page.mdx',source_group='docs',headings=[],generated_from_js=False)
        reader=read_page_source_units(page)
        inputs=dict(page=page,reader_result=reader,accepted_page_id=oid,accepted_section_mapping=None)
        owner=dict(endpointID=oid,inventoryId='A-DC01',**{'class':'DocumentationPage'},page_key=page['page_key'],canonical_url=url)
        units=reader['sourceUnits'];version=contract.WAVE_C_REQUEST_VERSION
    else:
        from src.extraction.llm.datasets.source_units import build_abstract_source_unit
        oid='a'*32;provenance=dict(snapshotID='synthetic',sourceVersion='v1')
        result=build_abstract_source_unit(dict(resource_id=oid,abstract=text),accepted_owner_id=oid,provenance=provenance)
        inputs=dict(accepted_owner_id=oid,trusted_provenance=provenance,abstract_results=[result],readme_results=[])
        units=[result['unit'].to_record()];owner=dict(endpointID=oid,resource_id=oid,inventoryId='A-D01',**{'class':'DatasetResource'})
        version=contract.WAVE_B_REQUEST_VERSION
    # Legacy builder cannot accept newly approved endpoint types. Supply those only to v0.4 build.
    legacy=contract._finish(owner,units,[u['sourceUnitID'] for u in units],{},[],[],[],request_version=version)
    inputs.update(accepted_endpoints=[],accepted_assertions=[])
    return dict(semanticRequest=legacy,requestInputs=inputs,body=dict(model='gpt-6.1-sol',reasoning={'effort':'medium'},store=False,max_output_tokens=32768,text={},input=''))


class SourceLocalTests(unittest.TestCase):
    """Exercise the executable provider/parser/validator/acceptance route."""
    def setUp(self):
        """Block network access across all focused cases."""
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('NO_NETWORK'));blocker.start();self.addCleanup(blocker.stop)
        blocker=patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NO_NETWORK'));blocker.start();self.addCleanup(blocker.stop)

    def build(self,family,text,**kwargs):
        """Prepare a coherent owner request with exact complete text."""
        return s.build([template(family,text)],**kwargs)

    def node(self,p,id,cls,quote,cid='n',**extra):
        """Create a model-authored candidate with an independent literal fragment."""
        uid=p['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID']
        return dict(candidateID=cid,inventoryId=id,**{'class':cls},label=cls,evidence=[dict(sourceUnitID=uid,evidenceText=quote)],**extra)

    def edge(self,p,id,relation,quote,target='n',cid='e',**extra):
        """Reference the exact owner and a local candidate without name lookup."""
        uid=p['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID'];owner=p['semanticRequest']['request']['owner']['endpointID']
        return dict(candidateID=cid,inventoryId=id,relation=relation,source=dict(referenceType='accepted_endpoint',referenceID=owner),target=dict(referenceType='candidate_node',referenceID=target),evidence=[dict(sourceUnitID=uid,evidenceText=quote)],**extra)

    def run_payload(self,p,nodes,edges,abstentions=None):
        """Replay only synthetic recorded bytes, preserving their hash."""
        return s.replay(p,canonical(dict(schemaVersion=s.VERSION,candidateNodes=nodes,candidateEdges=edges,abstentions=abstentions or [])),expected_request_sha256=p['semanticRequest']['requestSha256'])

    def test_gauge(self):
        """A concrete HydroShare Gauge can traverse all operational stages."""
        text='USGS stream gage 10109000. This dataset records the gage discharge.'
        p=self.build('hydroshare',text)
        r=self.run_payload(p,[self.node(p,'A-DOM07c','Gauge','USGS stream gage 10109000.')],[self.edge(p,'C-D15','referencesFeature','This dataset records the gage discharge.')])
        self.assertEqual([d['disposition'] for d in r['decisions']],['accepted','accepted'],r['decisions'])

    def test_github_variable_and_parameter(self):
        """Previously omitted named quantities/parameters are explicit accepted targets."""
        p=self.build('github','Streamflow is the output variable. Set start_date to select the retrieval period.')
        nodes=[self.node(p,'A-DOM04','Variable','Streamflow is the output variable.',cid='v'),self.node(p,'A-DOM12','Parameter','Set start_date to select the retrieval period.',cid='p')]
        edges=[self.edge(p,'C-C12','mentionsVariable','Streamflow is the output variable.',target='v',cid='ev'),self.edge(p,'C-C24','usesParameter','Set start_date to select the retrieval period.',target='p',cid='ep')]
        r=self.run_payload(p,nodes,edges);self.assertTrue(all(d['disposition']=='accepted' for d in r['decisions']),r['decisions'])

    def test_external_dataset_and_named_occurrence(self):
        """Neither exact external datasets nor unresolved names require corpus membership."""
        for identifier,cls,extra in [('A-D01','DatasetResource',{'exactIdentifier':'https://example.test/data'}),('A-P25','DatasetMention',{})]:
            p=self.build('github','We use River Observations from https://example.test/data to train the model.')
            quote=p['semanticRequest']['request']['sourceUnits'][0]['text']
            r=self.run_payload(p,[self.node(p,identifier,cls,quote,**extra)],[self.edge(p,'C-C15','usesDataset',quote)])
            self.assertEqual(len(r['projection']['nodes']),1,r['decisions']);self.assertEqual(len(r['projection']['edges']),1,r['decisions'])

    def test_exact_reuse_and_no_name_merge(self):
        """Exact identifier reuses one deterministic endpoint; labels never do."""
        endpoint=dict(endpointID='det:data',inventoryId='A-D01',**{'class':'DatasetResource'},attributes={'url':'https://example.test/data'})
        p=self.build('github','We use https://example.test/data.',deterministic_endpoints=[endpoint])
        q='We use https://example.test/data.';n=self.node(p,'A-D01','DatasetResource',q,exactIdentifier='https://example.test/data')
        r=self.run_payload(p,[n],[self.edge(p,'C-C15','usesDataset',q)])
        self.assertFalse(r['projection']['nodes']);self.assertEqual(r['projection']['edges'][0]['resolvedTarget']['endpointID'],'det:data')
        self.assertEqual(r['originalReplay']['finalRecords'][0]['originalCandidate'],n)
        implicit=deepcopy(n);implicit.pop('exactIdentifier')
        reused=self.run_payload(p,[implicit],[self.edge(p,'C-C15','usesDataset',q)])
        self.assertFalse(reused['projection']['nodes'])
        self.assertEqual(reused['projection']['edges'][0]['resolvedTarget']['endpointID'],'det:data')

    def test_stable_local_ids_and_duplicate_nodes(self):
        """Changing candidate IDs is not a new entity; identical occurrences deduplicate."""
        p=self.build('github','Streamflow is an output variable.')
        a=self.node(p,'A-DOM04','Variable','Streamflow is an output variable.',cid='a');b={**deepcopy(a),'candidateID':'b'}
        r=self.run_payload(p,[a,b],[]);self.assertEqual(len(r['projection']['nodes']),1,r['decisions'])
        one=self.run_payload(p,[a],[]);two=self.run_payload(p,[b],[])
        self.assertEqual(one['projection']['nodes'][0]['sourceLocalCandidateID'],two['projection']['nodes'][0]['sourceLocalCandidateID'])

    def test_method_positive_unresolved(self):
        """Explicit implementation evidence remains an inspectable unresolved assertion."""
        p=self.build('github','This repository implements the scientific routing method.')
        e=self.edge(p,'C-C16','implementsMethod','This repository implements the scientific routing method.',target='unresolved-method',methodSurfaceForm='scientific routing method')
        r=self.run_payload(p,[],[e]);self.assertFalse(r['projection']['edges']);self.assertEqual(r['unresolvedAssertions'][0]['originalCandidate'],e)
        self.assertTrue(r['unresolvedAssertions'][0]['boundEvidence']);self.assertFalse(r['abstentions'])

    def test_hub_mentions_and_citation(self):
        """Weak model/dataset roles and explicit Paper citation reach construction."""
        p=self.build('ciroh_hub','The rainfall-runoff physical model routes flow. The River Archive dataset is mentioned. See Paper DOI 10.1234/example.')
        nodes=[self.node(p,'A-DOM03a','ProcessBasedModel','The rainfall-runoff physical model routes flow.',cid='m'),self.node(p,'A-P25','DatasetMention','The River Archive dataset is mentioned.',cid='d'),self.node(p,'A-P01','Paper','See Paper DOI 10.1234/example.',cid='p',exactIdentifier='10.1234/example')]
        edges=[self.edge(p,'C-DC24','mentionsModel','The rainfall-runoff physical model routes flow.',target='m',cid='em'),self.edge(p,'C-DC25','mentionsDataset','The River Archive dataset is mentioned.',target='d',cid='ed'),self.edge(p,'C-DC26','referencePublication','See Paper DOI 10.1234/example.',target='p',cid='ep')]
        r=self.run_payload(p,nodes,edges);self.assertEqual(len(r['projection']['nodes']),3,r['decisions']);self.assertEqual(len(r['projection']['edges']),3,r['decisions'])

    def test_hub_citation_without_invented_global_identifier(self):
        """A source-local bibliographic Paper need not already have a DOI or corpus node."""
        p=self.build('ciroh_hub','See Smith (2024), Routing rivers, Water Resources Research.')
        quote=p['semanticRequest']['request']['sourceUnits'][0]['text']
        r=self.run_payload(p,[self.node(p,'A-P01','Paper',quote)],[self.edge(p,'C-DC26','referencePublication',quote)])
        self.assertEqual(len(r['projection']['nodes']),1,r['decisions']);self.assertEqual(len(r['projection']['edges']),1)
        self.assertNotIn('exactIdentifier',r['projection']['nodes'][0]['resolvedEndpoint'])

    def test_independent_evidence_and_abstention(self):
        """A valid node never supplies a missing edge quote; zero yield is legitimate."""
        p=self.build('github','Streamflow is an output variable.')
        r=self.run_payload(p,[self.node(p,'A-DOM04','Variable','Streamflow is an output variable.')],[self.edge(p,'C-C12','mentionsVariable','fabricated relation quote')])
        self.assertEqual(len(r['projection']['nodes']),1);self.assertFalse(r['projection']['edges'])
        uid=p['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID']
        r=self.run_payload(p,[],[],[dict(abstentionID='a',inventoryId='C-C24',sourceUnitIDs=[uid],disposition='abstained_no_evidence',reason='No parameter evidence')])
        self.assertTrue(r['zeroYield']);self.assertEqual(len(r['abstentions']),1)

    def test_coverage_and_legacy_isolation(self):
        """Every inventory target is transmitted; legacy inventories remain unchanged."""
        for family in s.DIRECTORIES:
            p=self.build(family,'A complete source document.')
            schema=deepcopy(p['body']['text']['format']['schema'])
            policy.coverage(family,schema)
            del schema['properties']['candidateEdges']['items']['anyOf'][0]
            # Each edge has one branch unless optional fields create variants: remove all instances.
            target=next(iter(p['semanticRequest']['request']['targetProfile']['relations']))
            schema['properties']['candidateEdges']['items']['anyOf']=[b for b in schema['properties']['candidateEdges']['items']['anyOf'] if b['properties']['inventoryId']['enum']!=[target]]
            with self.assertRaises(ValueError):policy.coverage(family,schema)
        self.assertNotIn('C-C12',s.profiles.get_profile('github')['relations'])

    def test_native_batch_dispatch(self):
        """The existing source-family Batch adapter reconstructs and processes v0.4."""
        import base64
        from src.extraction.llm import source_family_batch as batch
        p=self.build('github','No scientific assertion.')
        self.assertEqual(p,batch.prepare(p['semanticRequest'],p['requestInputs']))
        raw=canonical(dict(schemaVersion=s.VERSION,candidateNodes=[],candidateEdges=[],abstentions=[]))
        receipt=dict(cost={'estimatedUSD':0.001},providerResponse={'model':'gpt-6.1-sol','service_tier':'batch','status':'completed'},
            row={'response':{'status_code':200}},rawModelOutputBase64=base64.b64encode(raw).decode())
        outcome=batch.process(p,receipt,1)
        self.assertTrue(outcome['processable']);self.assertTrue(outcome['productionResult']['zeroYield'])
        self.assertEqual(outcome['attempt']['authorityBundleID'],s.VERSION)
        for field in ('instructions','responseContract'):
            altered=deepcopy(p['semanticRequest'])
            altered['request'][field]=[] if field=='instructions' else {}
            altered['requestSha256']=digest(canonical(altered['request']))
            with self.assertRaisesRegex(ValueError,'PROSPECTIVE_CONTRACT_DRIFT'):
                batch.prepare(altered,p['requestInputs'])

    def test_purpose_remains_reachable(self):
        """Full-document binding must not silently lose the existing purpose route."""
        p=self.build('github','This repository exists to process scientific data.')
        e=self.edge(p,'C-C07','hasPurpose','This repository exists to process scientific data.',categoryKey='data_processing',classification='proposed')
        e['target']=dict(referenceType='accepted_endpoint',referenceID='repo-purpose:1.0.0:data_processing')
        r=self.run_payload(p,[],[e]);self.assertEqual(len(r['projection']['edges']),1,r['decisions'])

    def test_model_version_requires_structured_own_product_proof(self):
        """Root CFF metadata can verify reuse; a matching prose label cannot."""
        t=template('github','Our product release is 1.0.')
        owner=t['requestInputs']['accepted_repository'];text='title: Our product\nversion: "1.0"\n'
        authority=dict(owner,path='CITATION.cff',cellIndex=None,authorityKind='downloaded_file',
            text=text,rawFileSha256=digest(text.encode()),authorityTextSha256=digest(text.encode()))
        t['requestInputs']['versionAuthorities']=[authority]
        tool=dict(endpointID='tool:own',inventoryId='A-DOM02',**{'class':'Tool'},attributes=dict(sourceRepoId=1,sourcePath='CITATION.cff',title='Our product'))
        version=dict(endpointID='version:own:1',inventoryId='A-C10',**{'class':'ModelVersion'},attributes=dict(sourceRepoId=1,version='1.0',toolId='tool:own',sourcePath='CITATION.cff'))
        assertion=dict(assertionID='implementation',inventoryId='D-22',relation='implementedBy',sourceID='tool:own',targetID=owner['canonicalArtifactID'])
        p=s.build([t],deterministic_endpoints=[tool,version],deterministic_assertions=[assertion])
        n=self.node(p,'A-C10','ModelVersion','version: "1.0"',productRepositoryID=owner['canonicalArtifactID'],productEndpointID='tool:own',version='1.0')
        e=self.edge(p,'C-C09','hasModelVersion','version: "1.0"')
        uid=next(u['sourceUnitID'] for u in p['semanticRequest']['request']['sourceUnits'] if u['contentKind']=='structured_own_product_version')
        for c in (n,e):c['evidence'][0]['sourceUnitID']=uid
        r=self.run_payload(p,[n],[e])
        self.assertEqual([d['disposition'] for d in r['decisions']],['accepted','suppressed_duplicate'],r['decisions'])
        novel=s.build([t],deterministic_endpoints=[tool],deterministic_assertions=[assertion],
            deterministic_catalog_authority={'sha256':'c'*64,'completeOwnerCatalog':True})
        fresh=self.run_payload(novel,[n],[e]);self.assertEqual(len(fresh['projection']['nodes']),1,fresh['decisions'])
        self.assertEqual(len(fresh['projection']['edges']),1,fresh['decisions'])
        unproven=s.build([t],deterministic_endpoints=[tool],deterministic_assertions=[],
            deterministic_catalog_authority={'sha256':'c'*64,'completeOwnerCatalog':True})
        held=self.run_payload(unproven,[n],[e]);self.assertFalse(held['projection']['nodes']);self.assertFalse(held['projection']['edges'])
        n['evidence']=self.node(p,'A-C10','ModelVersion','Our product release is 1.0.')['evidence']
        r=self.run_payload(p,[n],[]);self.assertFalse(r['projection']['nodes']);self.assertIn('candidate_version_product_identity_not_established',r['decisions'][0]['blockingReasons'])

    def test_structured_version_formats_and_dependency_exclusion(self):
        """Root package fields bind exactly; nested dependencies are never version proof."""
        from src.extraction.llm.source_local_versions import fields
        for path,text in [('pyproject.toml','[project]\nname = "Own"\nversion = "1.2"\n[project.optional-dependencies]\ndev = ["other==9"]\n'),
                          ('package.json','{"name":"Own","version":"1.2","dependencies":{"other":"9"}}')]:
            values,location=fields(path,text)
            self.assertEqual(values,{'title':'Own','version':'1.2'})
            self.assertEqual(text[location['start']:location['end']],'1.2')
        for path,text in [('pyproject.toml','[tool.dependencies]\nname = "other"\nversion = "9"'),
                          ('package.json','{"name":"Own","dependencies":{"name":"other","version":"9"}}'),
                          ('CITATION.cff','title: Own\nversion: "1"\nversion: "2"')]:
            with self.assertRaises(ValueError):fields(path,text)

    def test_full_content_and_parent_holds(self):
        """Dynamic MDX remains in context, but exact text alone cannot release it."""
        text='Visible scientific text.\n\n{hiddenModel()}\n'
        p=self.build('ciroh_hub',text)
        self.assertEqual(p['semanticRequest']['request']['sourceUnits'][0]['text'],text)
        r=self.run_payload(p,[self.node(p,'A-DOM03a','ProcessBasedModel','hiddenModel')],[])
        self.assertFalse(r['projection']['nodes']);self.assertTrue(r['unresolvedAssertions'])

    def test_derived_mentions_only_approved_occurrences(self):
        """Generic mentions is a deterministic output, never a model schema branch."""
        p=self.build('hydroshare','The region studied is Western US.')
        r=self.run_payload(p,[self.node(p,'A-DOM08','NamedPlace','The region studied is Western US.')],[])
        self.assertEqual(len(r['derivedMentions']),1)
        self.assertNotIn('D-26',p['semanticRequest']['request']['targetProfile']['relations'])

    def test_multifile_identity_and_response_corruption(self):
        """Identical bytes at different paths remain distinct exact authorities."""
        t=template('github','Streamflow is the output variable.');second=deepcopy(t)
        a=second['requestInputs']['reader_result']['authorities'][0]
        a.update(path='docs/overview.md',authorityKind='downloaded_file')
        p=s.build([t,second]);self.assertEqual(len(p['semanticRequest']['request']['sourceUnits']),2)
        with self.assertRaises(ValueError):
            s.replay(p,b'{"schemaVersion":1,"schemaVersion":2}',expected_request_sha256=p['semanticRequest']['requestSha256'])

    def test_unverified_identifier_and_abstract_rejected(self):
        """No identifier invention or abstract-class bypass."""
        p=self.build('github','We use the River Archive dataset.')
        r=self.run_payload(p,[self.node(p,'A-D01','DatasetResource','We use the River Archive dataset.',exactIdentifier='10.1234/invented')],[])
        self.assertFalse(r['projection']['nodes']);self.assertTrue(r['unresolvedAssertions'])
        with self.assertRaises(ValidationError):self.run_payload(p,[self.node(p,'A-DOM03','ComputationalModel','We use the River Archive dataset.')],[])


if __name__=='__main__':unittest.main()
