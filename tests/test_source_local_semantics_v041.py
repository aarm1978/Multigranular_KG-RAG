"""Focused correction regressions; synthetic inputs and blocked network access."""
from copy import deepcopy
import unittest
from jsonschema import ValidationError
from test_source_local_semantics import SourceLocalTests, template
from src.extraction.llm import source_local_semantics as s
from src.extraction.llm.pilot_preflight import canonical,digest
from src.extraction.llm.source_local_prompts import instructions
from src.extraction.llm.source_local_hub_evidence import regions


class CorrectionTests(unittest.TestCase):
    """Exercise only corrected prompt, evidence, and derived-construction boundaries."""
    setUp=SourceLocalTests.setUp
    build=SourceLocalTests.build
    node=SourceLocalTests.node
    edge=SourceLocalTests.edge
    run_payload=SourceLocalTests.run_payload

    def test_recovered_static_mdx_outside_historical_units(self):
        """Static nested HTML and text next to comments need no historical unit membership."""
        for text in ['<div><strong>RiverTool processes streamflow.</strong></div>',
                     'RiverTool processes streamflow. <!-- editorial note -->']:
            p=self.build('ciroh_hub',text);q='RiverTool processes streamflow.'
            self.assertFalse(any(q in u['text'] for u in p['requestInputs']['reader_result']['sourceUnits']))
            r=self.run_payload(p,[self.node(p,'A-DOM02','Tool',q)],[self.edge(p,'C-DC07','describesTool',q)])
            self.assertEqual(len(r['projection']['nodes']),1,r['decisions'])
            self.assertEqual(len(r['projection']['edges']),1,r['decisions'])
            e=r['projection']['nodes'][0]['boundEvidence'][0]
            self.assertEqual(text[e['startOffsetInAuthority']:e['endOffsetInAuthority']],q)
            self.assertEqual(e['fullAuthoritySha256'],digest(text.encode()))

    def test_positive_parameter_parent_path(self):
        """Full-page explanatory evidence admits independently bound dependent Parameters."""
        q='To retrieve a time series, choose the station and request its observations.'
        meaning='Set start_date to the first date of the retrieval period.'
        p=self.build('ciroh_hub',q+'\n\n'+meaning)
        procedure=self.node(p,'A-DC05','Procedure',q,cid='proc')
        parameter=self.node(p,'A-DOM12','Parameter',meaning,cid='param',parentPath=[dict(referenceType='candidate_edge',referenceID=x) for x in ('parent','attach')])
        parent=self.edge(p,'C-DC20','hasProcedure',q,target='proc',cid='parent')
        attach=self.edge(p,'C-DC11','hasParameter',meaning,target='param',cid='attach')
        attach['source']=dict(referenceType='candidate_node',referenceID='proc')
        r=self.run_payload(p,[procedure,parameter],[parent,attach])
        self.assertEqual(len(r['projection']['nodes']),2,r['decisions']);self.assertEqual(len(r['projection']['edges']),2,r['decisions'])
        bad=deepcopy(attach);bad['evidence'][0]['evidenceText']='Invented attachment.'
        r=self.run_payload(p,[procedure,parameter],[parent,bad])
        self.assertNotIn('param',[n['candidateID'] for n in r['projection']['nodes']])

    def test_inadmissible_regions_and_example_only_boundary(self):
        """Dynamic/comment/code/unknown-component evidence cannot become semantic Tools."""
        for text in ['{condition && "RiverTool processes streamflow."}',
                     '<Widget>RiverTool processes streamflow.</Widget>',
                     '<div hidden>RiverTool processes streamflow.</div>',
                     '<!-- RiverTool processes streamflow. -->',
                     '```python\nRiverTool processes streamflow.\n```',
                     '    RiverTool processes streamflow.',
                     '`RiverTool processes streamflow.`']:
            p=self.build('ciroh_hub',text)
            r=self.run_payload(p,[self.node(p,'A-DOM02','Tool','RiverTool processes streamflow.')],[])
            self.assertFalse(r['projection']['nodes'],text);self.assertTrue(r['unresolvedAssertions'])
        self.assertEqual(set(regions('<div>unclosed')),{'uncertain'})

    def test_example_remains_parent_bound(self):
        """A literal displayed Example retains its supported procedural path."""
        q='To retrieve observations, choose a station and run the displayed example.'
        p=self.build('ciroh_hub',q+'\n\n```python\nfetch(station)\n```')
        procedure=self.node(p,'A-DC05','Procedure',q,cid='proc')
        example=self.node(p,'A-DC08','Example','fetch(station)',cid='example',parentPath=[dict(referenceType='candidate_edge',referenceID=x) for x in ('parent','attach')])
        parent=self.edge(p,'C-DC20','hasProcedure',q,target='proc',cid='parent')
        attach=self.edge(p,'C-DC12','hasExample',q,target='example',cid='attach')
        attach['source']=dict(referenceType='candidate_node',referenceID='proc')
        r=self.run_payload(p,[procedure,example],[parent,attach])
        self.assertEqual(len(r['projection']['nodes']),2,r['decisions'])
        self.assertEqual(len(r['projection']['edges']),2,r['decisions'])
        from src.extraction.llm.source_local_hub_evidence import binder
        heading=self.build('ciroh_hub','# start_date parameter')
        inputs=heading['requestInputs'];uid=heading['semanticRequest']['request']['sourceUnits'][0]['sourceUnitID']
        binding=binder(inputs)(inputs['page'],inputs['reader_result'],uid,[dict(evidenceText='start_date parameter')],accepted_page_id=inputs['accepted_page_id'])
        self.assertEqual(binding['status'],'evidence_bound')
        self.assertFalse(binding['explanatoryProse'])

    def test_prompt_positive_criteria_and_superseded_restrictions(self):
        """Provider-visible prompts carry calibrated positive distinctions with no old bans."""
        expected={'hydroshare':['A notebook may qualify','No Measurement yield is required','do not require runtime logs'],
                  'github':['named programming function','do not categorically exclude tutorials','scientific_experimentation'],
                  'ciroh_hub':['Narrative instructions are admissible','Do not duplicate a Procedure as a Workflow','Parameter identity and procedural role']}
        for family,needles in expected.items():
            p=self.build(family,'A complete source document.');body=p['semanticRequest']['request']
            joined=' '.join(body['instructions'])
            for needle in needles:self.assertIn(needle,joined)
            self.assertEqual(body['instructions'],instructions(family,s.INSTRUCTIONS))
            for forbidden in ['No cross-page workflow assembly or DOI/citation enrichment',
                              'usesDataset/C-C15 needs an exact identifiable dataset endpoint',
                              'absent from deterministic assertions','No code/output/runtime interpretation, dependency manifests']:
                self.assertNotIn(forbidden,joined)
            self.assertIn('complete supplied-authority context',joined.lower().replace('complete supplied authorities govern context coverage','complete supplied-authority context'))

    def test_weak_dataset_construction_input_and_precedence(self):
        """Weak DatasetMention has a traceable nonredundant pipeline-derived input."""
        q='The River Archive dataset is mentioned.';use='We use River Archive to train the model.'
        p=self.build('github',q+' '+use)
        n=self.node(p,'A-P25','DatasetMention',q)
        r=self.run_payload(p,[n,{**deepcopy(n),'candidateID':'duplicate'}],[])
        d=r['derivedConstructionInput'];self.assertEqual(len(d['assertions']),1)
        self.assertEqual(d['requiredAcceptedProjectionSha256'],r['projectionSha256'])
        self.assertEqual(r['derivedConstructionInputSha256'],digest(canonical(d)))
        self.assertEqual(len(d['assertions'][0]['supportingOccurrences']),2)
        self.assertEqual(d['assertions'][0]['boundEvidence'][0]['evidenceText'],q)
        self.assertEqual(d['assertions'][0]['sourceContainment'][0]['ownerID'],p['semanticRequest']['request']['owner']['endpointID'])
        edge=self.edge(p,'C-C15','usesDataset',use)
        stronger=self.run_payload(p,[n],[edge]);self.assertFalse(stronger['derivedMentions'])
        edge['evidence'][0]['evidenceText']='Invented use claim.'
        held=self.run_payload(p,[n],[edge]);self.assertEqual(len(held['derivedMentions']),1)
        with self.assertRaises(ValidationError):self.run_payload(p,[n],[self.edge(p,'D-26','mentions',q)])

    def test_exact_reuse_derived_occurrence(self):
        """An admitted duplicate endpoint retains independently bound occurrence evidence."""
        q='The River Archive dataset is mentioned.'
        endpoint=dict(endpointID='det:mention',inventoryId='A-P25',**{'class':'DatasetMention'})
        p=self.build('github',q,deterministic_endpoints=[endpoint])
        n=self.node(p,'A-P25','DatasetMention',q,endpoint=dict(referenceType='accepted_endpoint',referenceID='det:mention'))
        r=self.run_payload(p,[n],[])
        self.assertFalse(r['projection']['nodes'])
        self.assertEqual(r['derivedMentions'][0]['targetID'],'det:mention')
        self.assertFalse(r['zeroYield'])


if __name__=='__main__':unittest.main()
