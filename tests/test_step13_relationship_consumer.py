"""Focused offline tests; no production graph materialization."""
from copy import deepcopy
import io
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.evaluation import materialize_step13_relationships as m


def spec():
    """Tiny ontology preserving the authorized test signatures."""
    return dict(classes=[],relations=[
        dict(id='C-P05',name='reports',domain='Paper',range=['RelatedResearch','Limitation']),
        dict(id='C-P10',name='discussesRelatedWork',domain='Paper',range='RelatedResearch'),
        dict(id='C-P12',name='hasLimitation',domain=['Paper','Finding'],range='Limitation'),
        dict(id='D-26',name='mentions',domain=['Paper','RelatedResearch','DatasetResource'],range=['Organization','Parameter'])])


def node(identifier,cls,inventory='test'):
    """Create one unchanged native graph node."""
    return dict(id=identifier,**{'class':cls},inventoryId=inventory,attributes={})


def occurrence(cid,cls,start,end):
    """Build an authentic-shaped accepted occurrence and evidence."""
    nid='r#node#'+cid
    e=dict(valid=True,canonicalPaperID='paper-authority',sourceUnitID='unit',startOffsetInUnit=start,
           endOffsetInUnit=end,startOffsetInDocument=100+start,endOffsetInDocument=100+end,
           evidenceText='literal',evidenceSpanID='ev-'+cid)
    n=dict(accepted=True,nodeID=nid,candidateID=cid,className=cls,ontologyClassID='test',evidenceOccurrences=[e])
    return dict(graphID=nid,nativeRecord=n,nativeRecordSha256=m.digest(m.canonical(n)),provenance=dict(requestID='r'))


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        """Reject network even in synthetic tests."""
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NETWORK')))
        self.rows=[occurrence('d','RelatedResearch',0,10),occurrence('e','Organization',2,5),occurrence('l','Limitation',20,30)]
        self.paper=node('paper','Paper');self.paper.update(attributes={'canonicalArtifactId':'paper-authority'},evidence={'sourceArtifact':'paper-authority'})
        self.graph=dict(nodes=[self.paper]+[node(r['graphID'],r['nativeRecord']['className']) for r in self.rows],edges=[])
        self.policy=dict(stronger_role_relations=['usesTool'],specialized_subproperties=['mentionsTool'])

    def consumer(self,graph=None):
        """Use the unchanged graph and a detached provenance buffer."""
        return m.Consumer(graph or self.graph,spec(),self.policy,io.StringIO())

    def test_rules_provenance_preservation_and_reproducibility(self):
        """Required attachments and strict containment preserve inputs and deterministic IDs."""
        old=deepcopy(self.graph);rows=deepcopy(self.rows);a=self.consumer();b=self.consumer()
        for c in (a,b):c.publication(self.rows,self.paper)
        self.assertEqual(len(a.derived),6)
        self.assertEqual(m.canonical(a.derived),m.canonical(b.derived))
        self.assertEqual(a.sidecar.getvalue(),b.sidecar.getvalue())
        self.assertEqual(self.graph,old);self.assertEqual(self.rows,rows)
        self.assertIn('literal',a.sidecar.getvalue())
        a.publication(self.rows,self.paper)
        self.assertEqual(len(a.derived),6);self.assertEqual(a.counts['C-P05']['duplicate'],2)

    def test_containment_requires_both_coordinates_and_unit(self):
        """Partial overlap or mismatched document/unit cannot create discourse mentions."""
        for field,value in [('endOffsetInDocument',999),('sourceUnitID','elsewhere'),('endOffsetInUnit',11)]:
            rows=deepcopy(self.rows);rows[1]['nativeRecord']['evidenceOccurrences'][0][field]=value
            c=self.consumer();c.publication(rows,self.paper)
            self.assertNotIn('D26-discourse',c.counts)

    def test_precedence_and_missing_endpoints(self):
        """Stronger accepted relation suppresses generic only; endpoint drift is fatal."""
        self.graph['edges']=[dict(id='strong',source='paper',target='r#node#e',relation='usesTool')]
        c=self.consumer();c.publication(self.rows,self.paper)
        self.assertEqual(c.counts['D26-Paper']['strongerSuppressed'],1)
        with self.assertRaisesRegex(ValueError,'MISSING_DERIVED_ENDPOINT'):
            c.emit('x','D-26','missing','r#node#e',[{}],{})
        with self.assertRaisesRegex(ValueError,'SIGNATURE'):
            c.emit('x','C-P05','paper','r#node#e',[{}],{})

    def test_paper_evidence_and_identity_guards(self):
        """No guessed owning Paper or renamed occurrence."""
        for field,value in [('nodeID','wrong'),('accepted',False)]:
            rows=deepcopy(self.rows);rows[0]['nativeRecord'][field]=value
            with self.assertRaises(ValueError):self.consumer().publication(rows,self.paper)
        paper=deepcopy(self.paper);paper['attributes']['canonicalArtifactId']='other'
        with self.assertRaisesRegex(ValueError,'EVIDENCE_DRIFT'):self.consumer().publication(self.rows,paper)

    def test_nonpublication_projection_containment_and_precedence(self):
        """Governed inputs require accepted hashes, exact types, units and decisions."""
        source=node('dataset','DatasetResource','A-D01');target=node('parameter','Parameter','A-DOM12')
        decision=dict(candidateID='p',disposition='accepted')
        a=dict(assertionID='derived',inventoryId='D-26',relation='mentions',sourceID='dataset',targetID='parameter',
            resolvedSource=dict(endpointID='dataset',**{'class':'DatasetResource'},inventoryId='A-D01'),
            resolvedTarget=dict(endpointID='parameter',**{'class':'Parameter'},inventoryId='A-DOM12'),
            boundEvidence=[dict(sourceUnitID='u',evidenceText='literal',startOffsetInAuthority=0,endOffsetInAuthority=7)],
            sourceContainment=[dict(sourceUnitID='u',ownerID='dataset',sourceTextSha256=m.digest(b'literal'))],
            supportingOccurrences=[dict(candidateID='p',constructionDecision=decision)])
        projection=dict(nodes=[],edges=[]);sha=m.digest(m.canonical(projection))
        native=dict(projection=projection,projectionSha256=sha,decisions=[decision],
            derivedConstructionInput=dict(assertions=[a]),originalReplay=dict(requestResult=dict(request=dict(
                owner=dict(endpointID='dataset'),artifactFamily='hydroshare',sourceUnits=[dict(sourceUnitID='u',text='literal')]))))
        group=dict(nativeValidationView=native)
        item=dict(ownerID='dataset',ownerReportSha256='hash',originalInput=dict(assertionID='derived',targetID='parameter',
            constructionInputs=[dict(requestID='r',requiredAcceptedProjectionSha256=sha,assertion=a)]))
        scopes={'hydroshare':dict(genericOccurrences=['A-DOM12'])}
        graph=dict(nodes=[source,target],edges=[]);saved=deepcopy(item)
        c=self.consumer(graph);c.nonpublication(item,lambda _:group,scopes)
        c.nonpublication(item,lambda _:group,scopes)
        self.assertEqual(len(c.derived),1);self.assertEqual(c.counts['D26-hydroshare']['duplicate'],1)
        self.assertEqual(item,saved);self.assertIn('literal',c.sidecar.getvalue())
        for mutation in ('hash','quote','target','scope','decision'):
            bad=deepcopy(item);g=deepcopy(group);sc=deepcopy(scopes)
            if mutation=='hash':bad['originalInput']['constructionInputs'][0]['requiredAcceptedProjectionSha256']='bad'
            if mutation=='quote':g['nativeValidationView']['originalReplay']['requestResult']['request']['sourceUnits'][0]['text']='changed'
            if mutation=='target':sc['hydroshare']['genericOccurrences']=[]
            if mutation=='scope':g['nativeValidationView']['originalReplay']['requestResult']['request']['owner']['endpointID']='other'
            if mutation=='decision':g['nativeValidationView']['decisions'][0]['disposition']='held'
            with self.assertRaises(ValueError):self.consumer(graph).nonpublication(bad,lambda _:g,sc)
        graph['edges']=[dict(id='strong',source='dataset',target='parameter',relation='usesParameter')]
        c=self.consumer(graph);c.nonpublication(item,lambda _:group,scopes)
        self.assertFalse(c.derived);self.assertEqual(c.counts['D26-hydroshare']['strongerSuppressed'],1)

    def test_existing_output_refused(self):
        """Preserve incomplete or complete prior directories."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):m.run(Path(directory))

    def test_authority_and_historical_guards_unchanged(self):
        """Bounded local authority check; no corpus processing."""
        _,actual,_=m.authorities();self.assertEqual(actual['ontology']['version'],'0.1.7')
        from src.extraction.llm.publications import semantic_materializer as historical
        with self.assertRaisesRegex(historical.SemanticMaterializationError,'ontology version drift'):
            historical._ontology_authority(historical.V015_POLICY_PATH)


if __name__=='__main__':unittest.main()
