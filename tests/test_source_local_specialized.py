"""Focused offline specialization regressions; reuse synthetic native source fixtures."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator,ValidationError

from test_source_local_semantics import SourceLocalTests
from src.extraction.llm import source_local_specialized as s
from src.extraction.llm import source_local_semantics as base
from src.extraction.llm.pilot_preflight import canonical,digest


class SpecializedTests(unittest.TestCase):
    """No provider calls; native parsing, evidence and acceptance are exercised offline."""
    setUp=SourceLocalTests.setUp
    build_context=SourceLocalTests.build
    node=SourceLocalTests.node
    edge=SourceLocalTests.edge

    def payload(self,nodes=None,edges=None,abstentions=None):
        """Supply explicit contributions without repairing a recorded response."""
        return dict(schemaVersion=s.VERSION,candidateNodes=nodes or [],candidateEdges=edges or [],abstentions=abstentions or [])

    def contribute(self,row):
        """Author synthetic positive fragments with their independent roles stated."""
        for fragment in row['evidence']:fragment['contribution']='Identifies this assertion in its source context.'
        return row

    def replay(self,p,payload):
        """Bind authentic synthetic bytes to the specialized request."""
        return s.replay(p,canonical(payload),expected_request_sha256=p['semanticRequest']['requestSha256'])

    def test_multifragment_v041_failure_and_corrected_schema(self):
        """Old strict schema passes missing contributions that the native validator holds."""
        q='Streamflow is the output variable. It is measured in cubic metres per second.'
        context=self.build_context('github',q);n=self.node(context,'A-DOM04','Variable','Streamflow is the output variable.')
        n['evidence'].append({**n['evidence'][0],'evidenceText':'It is measured in cubic metres per second.'})
        old={**self.payload([n]),'schemaVersion':base.VERSION}
        Draft202012Validator(context['body']['text']['format']['schema']).validate(old)
        r=base.replay(context,canonical(old),expected_request_sha256=context['semanticRequest']['requestSha256'])
        self.assertFalse(r['projection']['nodes'])
        self.assertTrue(any(f['reason']=='fragment_contribution_missing_or_malformed' for f in r['originalReplay']['validationResult']['candidateChecks'][0]['findings']))
        p=s.build(context,'quantities_and_concepts')
        with self.assertRaises(ValidationError):self.replay(p,self.payload([n]))
        self.contribute(n);r=self.replay(p,self.payload([n]))
        self.assertEqual(len(r['projection']['nodes']),1)
        self.assertEqual(r['responseSha256'],digest(canonical(self.payload([n]))))
        self.assertEqual(r['nativeValidationView']['originalReplay']['finalRecords'][0]['originalCandidate'],n)
        n['evidence'][0]['contribution']='   '
        with self.assertRaises(ValidationError):self.replay(p,self.payload([n]))
        self.assertEqual(base.VERSION,'study2-source-local-semantics/0.4.1')

    def test_complete_inventory_and_dependency_closure(self):
        """All current targets are assigned; branch omissions and parent gaps fail closed."""
        for family in s.GROUPS:
            context=self.build_context(family,'Complete source context.')
            groups=s.inventory(family);profile=context['semanticRequest']['request']['targetProfile']
            for key in ('entities','relations'):
                self.assertEqual(set().union(*(set(g[key]) for g in groups.values())),set(profile[key]))
            for group,scope in groups.items():
                schema=s.group_schema(context,group)
                for branch in schema['$defs']['fragment']['anyOf']:self.assertIn('contribution',branch['required'])
                self.assertNotIn('D-26',scope['relations'])
        changed=deepcopy(s.GROUPS);changed['github']['quantities_and_concepts'][0].remove('A-DOM04')
        with patch.object(s,'GROUPS',changed),self.assertRaisesRegex(ValueError,'COVERAGE_GAP'):s.inventory('github')
        changed=deepcopy(s.GROUPS);changed['ciroh_hub']['procedures_and_dependents'][0].remove('A-DC05')
        changed['ciroh_hub']['products_and_references'][0].append('A-DC05')
        with patch.object(s,'GROUPS',changed),self.assertRaisesRegex(ValueError,'ENDPOINT_GAP|PARENT_PATH_GAP'):s.inventory('ciroh_hub')

    def test_exact_owner_consolidation_derived_precedence_and_diagnostics(self):
        """Repeated exact local entities consolidate; weak edges never duplicate across groups."""
        q='We use River Archive data to train the model.'
        context=self.build_context('github',q+' This repository implements the routing method.')
        pairs=[]
        for group in s.GROUPS['github']:
            p=s.build(context,group);nodes=[];edges=[];abstentions=[]
            if group!='quantities_and_concepts':
                nodes=[self.contribute(self.node(p,'A-P25','DatasetMention',q,cid='same-run-local-id'))]
            else:
                abstentions=[dict(abstentionID='a',inventoryId='C-C24',sourceUnitIDs=p['semanticRequest']['request']['selectedSourceUnitIDs'],disposition='abstained_no_evidence',reason='No named parameter is stated.')]
            if group=='software_roles_and_use':
                edges=[self.contribute(self.edge(p,'C-C16','implementsMethod','This repository implements the routing method.',target='unresolved-method',methodSurfaceForm='routing method'))]
            pairs.append((p,self.replay(p,self.payload(nodes,edges,abstentions))))
        result=s.consolidate(pairs)
        self.assertEqual(len(result['nodes']),1)
        self.assertEqual(len(result['nodes'][0]['records']),2)
        self.assertEqual(len(result['derivedConstructionInputs']),1)
        self.assertEqual(len(result['derivedConstructionInputs'][0]['constructionInputs']),2)
        self.assertTrue(any(r['unresolvedAssertions'] for r in result['groupReports']))
        self.assertTrue(any(r['abstentions'] for r in result['groupReports']))
        self.assertEqual(result,s.consolidate(list(reversed(pairs))))
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OWNER_GROUPS'):s.consolidate(pairs[:-1])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_GROUP_REPORT'):s.consolidate(pairs+[pairs[0]])
        # Native local identities are unchanged; a strong accepted edge in another group wins.
        p,_=pairs[0];node=self.contribute(self.node(p,'A-P25','DatasetMention',q,cid='renamed-candidate'))
        edge=self.contribute(self.edge(p,'C-C15','usesDataset',q,target='renamed-candidate'))
        strong=self.replay(p,self.payload([node],[edge]));changed=[(p,strong)]+pairs[1:]
        final=s.consolidate(changed)
        self.assertEqual(len(final['nodes']),1);self.assertEqual(len(final['edges']),1)
        self.assertFalse(final['derivedConstructionInputs']);self.assertEqual(len(final['suppressedDerivedMentions']),1)
        corrupt=deepcopy(changed);corrupt[0][1]['responseSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'GROUP_REPORT_DRIFT'):s.consolidate(corrupt)

    def test_hydroshare_positive_and_scope_rejection(self):
        """A specialized Gauge relation uses the unchanged native positive route."""
        q='USGS stream gage 10109000 measures discharge.'
        context=self.build_context('hydroshare',q);p=s.build(context,'observations_and_geography')
        n=self.contribute(self.node(p,'A-DOM07c','Gauge',q));e=self.contribute(self.edge(p,'C-D15','referencesFeature',q))
        r=self.replay(p,self.payload([n],[e]))
        self.assertEqual((len(r['projection']['nodes']),len(r['projection']['edges'])),(1,1))
        outside=self.contribute(self.node(p,'A-DOM02','Tool',q))
        with self.assertRaises(ValidationError):self.replay(p,self.payload([outside]))
        self.assertEqual(p['semanticRequest']['request']['sourceUnits'],context['semanticRequest']['request']['sourceUnits'])

    def test_hub_local_parameter_dependency(self):
        """Procedure and its dependent are jointly available; cross-group references stay held."""
        q='To retrieve observations, choose a station.';meaning='Set start_date to the first retrieval date.'
        context=self.build_context('ciroh_hub',q+' '+meaning);p=s.build(context,'procedures_and_dependents')
        procedure=self.contribute(self.node(p,'A-DC05','Procedure',q,cid='proc'))
        parameter=self.contribute(self.node(p,'A-DOM12','Parameter',meaning,cid='param',parentPath=[dict(referenceType='candidate_edge',referenceID=x) for x in ('parent','attach')]))
        parent=self.contribute(self.edge(p,'C-DC20','hasProcedure',q,target='proc',cid='parent'))
        attach=self.contribute(self.edge(p,'C-DC11','hasParameter',meaning,target='param',cid='attach'))
        attach['source']=dict(referenceType='candidate_node',referenceID='proc')
        r=self.replay(p,self.payload([procedure,parameter],[parent,attach]))
        self.assertEqual((len(r['projection']['nodes']),len(r['projection']['edges'])),(2,2))
        parameter['parentPath'][0]['referenceID']='another-group-parent'
        r=self.replay(p,self.payload([procedure,parameter],[parent,attach]))
        self.assertNotIn('param',[n['candidateID'] for n in r['projection']['nodes']])


if __name__=='__main__':unittest.main()
