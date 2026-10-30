"""Synthetic offline tests for exact identity transformation, not semantic evaluation."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import build_step13_pre_alignment as m


def baseline():
    """A tiny frozen graph with an explicit curated source inventory lineage."""
    return dict(nodes=[dict(id='paper-native',**{'class':'Paper'},inventoryId='A-P01',
        attributes=dict(canonicalArtifactId='https://example.test/paper',title='Paper'),
        curationStatus='curated',internalLineage=dict(localPaperId='7'),
        evidence=dict(sourceArtifact='https://example.test/paper'))],edges=[])


def projection(rid='request-1'):
    """Native request-qualified IDs repeat labels but never imply equivalence."""
    artifact='https://example.test/paper';candidate=dict(candidateID='node-0001',label='Same model',attributes=[])
    n=dict(nodeID=rid+'#node#node-0001',candidateID='node-0001',className='Tool',ontologyClassID='A-DOM02',accepted=True,candidate=candidate,evidenceOccurrences=[dict(evidenceText='exact quote',evidenceHash='preserved')])
    source=dict(referenceType='deterministic_node',referenceID=artifact,artifactID=artifact)
    target=dict(referenceType='candidate_node',referenceID='node-0001',artifactID=None)
    edge=dict(edgeID=rid+'#edge#edge-0001',candidateID='edge-0001',accepted=True,
        sourceEndpoint=source,targetEndpoint=target,sourceID='deterministic:'+artifact+':'+artifact,
        targetID=n['nodeID'],relationName='mentionsTool',ontologyRelationID='C-P24')
    return dict(requestID=rid,sourceArtifactID=artifact,acceptanceStatus='production_accepted',acceptedNodes=[n],acceptedEdges=[edge])


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        """Disallow all network calls during the synthetic suite."""
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NO_NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NO_NETWORK')))
        self.sidecar=io.StringIO();self.original=baseline();self.s=m.Snapshot(self.original,self.sidecar)

    def test_request_identity_not_label_deduplication(self):
        """Same label in distinct requests remains two local occurrences, not one entity."""
        p=projection();saved=deepcopy(p)
        self.s.publication(p,dict(requestID=p['requestID']),paper_id='7')
        self.s.publication(projection('request-2'),{},paper_id='7')
        graph=self.s.finish();self.assertEqual(len(graph['nodes']),3);self.assertEqual(len(graph['edges']),2)
        self.assertEqual(p,saved);self.assertEqual(self.original,baseline())
        self.assertTrue(all(e['source']=='paper-native' for e in graph['edges']))
        self.assertIn('deterministic:https://example.test/paper',self.sidecar.getvalue())
        self.assertIn('preserved',self.sidecar.getvalue())

    def test_repeated_exact_projection_preserves_occurrences(self):
        """An identical request record is one graph identity with two provenance records."""
        for _ in range(2):self.s.publication(projection(),{},paper_id=7)
        graph=self.s.finish();self.assertEqual(len(graph['nodes']),2);self.assertEqual(len(graph['edges']),1)
        self.assertEqual(len(self.sidecar.getvalue().splitlines()),4)
        self.assertEqual(self.s.counts['nodes_repeated_exact_id'],1)

    def test_conflicting_identity_blocks(self):
        """Different attributes under one exact ID cannot silently replace a record."""
        self.s.publication(projection(),{},paper_id=7)
        p=projection();p['acceptedNodes'][0]['candidate']['label']='Different model'
        self.s.publication(p,{},paper_id=7)
        self.assertIsNone(self.s.finish());self.assertEqual(self.s.blockers[0]['reason'],'conflicting_exact_identity')

    def test_missing_endpoint_is_not_invented(self):
        """Wrong inventory lineage does not trigger DOI or label lookup."""
        self.s.publication(projection(),{},paper_id=999)
        self.assertIsNone(self.s.finish());self.assertEqual(self.s.blockers[0]['reason'],'missing_exact_endpoint')
        self.assertEqual(len(self.s.nodes),2)

    def test_lineage_authority_mismatch(self):
        """The same inventory ID cannot resolve a different source artifact."""
        self.s.paper_lineage['7']['attributes']['canonicalArtifactId']='other'
        with self.assertRaisesRegex(ValueError,'LINEAGE_AUTHORITY_DRIFT'):self.s.publication(projection(),{},paper_id=7)

    def test_existing_output_is_immutable(self):
        """No output or historical trajectory is overwritten."""
        with tempfile.TemporaryDirectory() as root:
            path=Path(root);dest=path/'var/output';dest.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):m.build(path,Path('var/output'))
            self.assertEqual(list(dest.iterdir()),[])

    def test_owner_consolidation_keeps_evidence_and_exact_id(self):
        """Two supporting group records retain their provenance with one native endpoint."""
        native=dict(candidateID='n',originalCandidate=dict(label='Local tool'),resolvedEndpoint=dict(endpointID='local:tool',**{'class':'Tool'},inventoryId='A-DOM02'),boundEvidence=[dict(evidenceText='literal')])
        records=[dict(requestID=r,groupID='g',record=deepcopy(native)) for r in ('a','b')]
        self.s.owner(dict(nodes=[dict(records=records)],edges=[],derivedConstructionInputs=[dict(assertionID='not-consumed')]),{})
        graph=self.s.finish();self.assertEqual(len(graph['nodes']),2);self.assertFalse(graph['edges'])
        self.assertEqual(len(self.sidecar.getvalue().splitlines()),2)
        self.assertNotIn('boundEvidence',graph['nodes'][0].get('attributes',{}))

    def test_existing_metric_policy_and_order50(self):
        """Use the unchanged full/filtered evaluator and pre-consolidation accounting."""
        graph=baseline();graph['nodes'].append(dict(id='file',**{'class':'File'},inventoryId='A-C02',attributes=dict(fileName='x')))
        graph['edges'].append(dict(id='e',source='paper-native',target='file',relation='hasFile'))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.json';path.write_text(json.dumps(graph))
            record=m.metrics.build_results_record(graph,path,'step13_pre_alignment','Step 13 provisional',50,'mentionCount','pre_consolidation')
            self.assertEqual(record['trajectoryOrder'],50)
            self.assertEqual(record['variants']['full']['counts']['nodes'],2)
            self.assertEqual(record['variants']['fileInventoryExcluded']['counts']['nodes'],1)

    def test_journal_last_outcome_and_hash_guard(self):
        """Index latest recorded outcome once per request; chain changes fail closed."""
        previous='0'*64;lines=[]
        for seq,event in enumerate(('header','outcome','outcome'),1):
            record=dict(seq=seq,previous=previous,event=event,requestID='r',payload={})
            previous=m.digest(m.canonical(record));lines.append(m.canonical(dict(record=record,sha256=previous))+b'\n')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'journal';raw=b''.join(lines);p.write_bytes(raw)
            result=m.publication_offsets(p,m.digest(raw),dict(seq=3,headSha256=previous))
            self.assertEqual(result,dict(r=len(lines[0])+len(lines[1])))
            with self.assertRaisesRegex(ValueError,'AUTHORITY_DRIFT'):m.publication_offsets(p,'bad',dict(seq=3,headSha256=previous))


if __name__=='__main__':unittest.main()
