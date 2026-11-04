"""Synthetic accepted-relation diagnostics; no corpus processing or provider calls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import json
import socket
import unittest
from unittest.mock import patch

import yaml
from src.evaluation import step14_alignment_opportunities as m
from tests.test_step14_semantic_review import occurrence

SPEC = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
CLASSES = {c['name']:c['id'] for c in SPEC['classes']}


def node(nid, cls='Paper', family='publications', curated=True, **attrs):
    """Create an accepted node with explicit independent source provenance."""
    source = 'paper:' + nid if family == 'publications' else 'hydroshare:' + nid
    return dict(id=nid, **{'class':cls}, inventoryId=CLASSES[cls], attributes=attrs,
        curationStatus='curated' if curated else 'referenced',
        internalLineage={'localPaperId':nid} if family == 'publications' else {},
        evidence=dict(sourceArtifact=source,evidenceText='Evidence '+nid))


def edge(eid='e', source='source', target='target', predicate='cites', inventory='C-P21', quote='accepted quote'):
    """Create an exact accepted predicate and its inline evidence."""
    return dict(id=eid,source=source,target=target,relation=predicate,inventoryId=inventory,
                internalLineage={'localPaperId':source},evidence=dict(sourceArtifact='paper:'+source,evidenceText=quote))


def block(cls, index, families=('publications','hydroshare')):
    """Create an existing lexical dossier fixture with bounded evidence references."""
    members=[]
    for j,f in enumerate(families):
        row=occurrence(f'{cls}:{index}:{j}',f,label=str(index));row['ontologyClass']=cls
        members.append(m.review.compact_member(row))
    return dict(blockID=f'{cls}:{index:03d}',key=['lexical_similarity_only',cls,str(index)],ontologyClass=cls,
        candidateMechanism='lexical_similarity_only',members=members,occurrenceIDs=[r['occurrenceID'] for r in members],
        membershipSha256='fixture-membership',memberCount=len(members),sourceFamilyCombination=list(families),existingBlockFlags=[])


class OpportunityTests(unittest.TestCase):
    def setUp(self):
        """Prevent networking in every test."""
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NETWORK')))

    def inventory(self,nodes,edges,native=None,derived=None,dossier=None,triages=None):
        """Check every input is preserved by the diagnostic."""
        args=[dict(nodes=nodes,edges=edges),native or [],derived or [],dossier or [],triages or [],[],SPEC]
        saved=deepcopy(args);result=m.inventory(*args);self.assertEqual(args,saved)
        self.assertEqual(sum(r['acceptedOccurrences'] for r in result['relationInventory']),len(edges))
        return result

    def test_external_target_vs_ambiguous_locator(self):
        """Typed own DOI differs from a URL-only stub; schema cross is not instance proof."""
        source=node('source');target=node('target',family='hydroshare',curated=False,doi='10.1234/target')
        result=self.inventory([source,target],[edge()])
        self.assertEqual(result['tierCounts'][m.TIERS[0]],1)
        self.assertEqual(result['summary']['directIndependentArtifactConnections'],0)
        target['attributes']={'url':'https://example.test/portal'}
        result=self.inventory([source,target],[edge()])
        self.assertEqual(result['tierCounts'][m.TIERS[4]],1)

    def test_direct_observed_artifact_vs_owner_mention(self):
        """Curated independent targets count separately; source DOI never transfers."""
        source=node('source',doi='10.1234/source');target=node('target',family='hydroshare',doi='10.1234/target')
        result=self.inventory([source,target],[edge()])
        self.assertEqual(result['summary']['directIndependentArtifactConnections'],1)
        target=node('target',curated=False,citation='10.1234/source')
        result=self.inventory([source,target],[edge()])
        self.assertEqual(result['tierCounts'][m.TIERS[0]],0)
        self.assertEqual(result['summary']['directIndependentArtifactConnections'],0)

    def test_stub_strong_candidate_to_owner(self):
        """Only an existing unadjudicated strong block supplies the possible owner match."""
        nodes=[node('source'),node('target',curated=False,doi='10.1234/x'),node('owner',family='hydroshare',doi='10.1234/x')]
        triage=dict(occurrenceIDs=['target','owner'],provisionalReviewCategory='strong_record_identity_candidate',identifierScope={})
        result=self.inventory(nodes,[edge()],triages=[triage])
        self.assertEqual(result['tierCounts'][m.TIERS[1]],1)
        self.assertEqual(result['summary']['directIndependentArtifactConnections'],0)
        self.assertEqual(result['summary']['possibleCrossFamilyAlignmentOccurrences'],1)

    def test_weak_predicates_never_promoted(self):
        """All weak and strong input predicates remain byte-exact in summaries/examples."""
        nodes=[node('source','Repository'),node('target','Tool',curated=False)]
        edges=[edge('weak',predicate='mentionsTool',inventory='C-C22'),edge('strong',predicate='usesTool',inventory='C-C11')]
        result=self.inventory(nodes,edges)
        self.assertEqual({r['predicate'] for r in result['relationInventory']},{'mentionsTool','usesTool'})
        for r in result['relationInventory']:
            self.assertEqual(r['predicate'],r['examples'][0]['acceptedPredicate'])
        # Deliberately do not infer a repository or dataset predicate from an existing one.
        edges=[edge('repo',predicate='referencesRepository',inventory='unknown'),edge('dataset',predicate='referencesDataset',inventory='C-P29')]
        result=self.inventory(nodes,edges)
        self.assertEqual({r['predicate'] for r in result['relationInventory']},{'referencesRepository','referencesDataset'})

    def test_class_compatibility_and_missing_provenance(self):
        """Incompatible endpoints and absent origin records remain unresolved."""
        nodes=[node('source'),node('target','Tool',curated=False,doi='10.1234/x')]
        result=self.inventory(nodes,[edge()])
        self.assertEqual(result['relationInventory'][0]['signatureStatus'],'class_incompatible')
        self.assertEqual(result['tierCounts'][m.TIERS[4]],1)
        nodes[1]=node('target',curated=False,doi='10.1234/x');nodes[1].pop('evidence')
        result=self.inventory(nodes,[edge()])
        self.assertEqual(result['summary']['endpointProvenanceUnresolved'],1)
        self.assertEqual(result['tierCounts'][m.TIERS[0]],0)

    def test_duplicate_evidence_not_independent(self):
        """Repeated quotations retain occurrence counts but are reported as reused."""
        nodes=[node('source'),node('target',curated=False,doi='10.1234/x')]
        result=self.inventory(nodes,[edge('e1'),edge('e2')])
        self.assertEqual(result['summary']['acceptedRelationOccurrences'],2)
        self.assertEqual(result['summary']['quoteHashesReusedByMultipleEdges'],1)
        self.assertEqual(result['summary']['edgeOccurrencesWithReusedQuote'],2)

    def test_native_and_derived_evidence_recovery(self):
        """Projected edges use their native/derived sidecars without predicate rewriting."""
        nodes=[node('source'),node('target',curated=False,doi='10.1234/x')]
        e=edge();e.pop('evidence');e.pop('internalLineage')
        record=dict(evidenceOccurrences=[dict(canonicalPaperID='paper:source',evidenceText='accepted')])
        row=dict(kind='edges',graphID='e',nativeRecord=record,nativeRecordSha256=m.candidates.token(record),provenance={'family':'publications'})
        result=self.inventory(nodes,[e],native=[row])
        self.assertEqual(result['summary']['evidenceProvenanceConfirmed'],1)
        self.assertEqual(result['relationInventory'][0]['examples'][0]['evidenceReferences'][0]['channel'],'native-provenance')
        derived=dict(edgeID='e',disposition='emitted',rule='D26-Paper',evidence=record['evidenceOccurrences'],provenance={})
        self.assertEqual(self.inventory(nodes,[e],derived=[derived])['summary']['evidenceProvenanceConfirmed'],1)
        row['nativeRecordSha256']='drift'
        with self.assertRaisesRegex(ValueError,'NATIVE_HASH_DRIFT'):
            self.inventory(nodes,[e],native=[row])

    def test_local_locator_and_lexical_peers(self):
        """Only existing class-compatible, cross-origin candidates enter weak tiers."""
        nodes=[node('source','Repository'),node('target','Tool',curated=False),node('peer','Tool',family='hydroshare',curated=False)]
        e=edge(predicate='mentionsTool',inventory='C-C22')
        local=dict(occurrenceIDs=['target','peer'],provisionalReviewCategory='exact_locator_candidate_only',identifierScope={'source_local_literal_declaration':2})
        result=self.inventory(nodes,[e],triages=[local])
        self.assertEqual(result['tierCounts'][m.TIERS[2]],1)
        b=block('Tool',1);b['occurrenceIDs']=['target','peer']
        result=self.inventory(nodes,[e],dossier=[b])
        self.assertEqual(result['tierCounts'][m.TIERS[3]],1)
        nodes[2]=node('peer','Algorithm',family='hydroshare',curated=False)
        self.assertEqual(self.inventory(nodes,[e],triages=[local])['tierCounts'][m.TIERS[2]],0)

    def test_reproducible_stratified_selection(self):
        """Thirty cases cover requested classes without asserting any true identity."""
        blocks=[block(cls,i) for cls in m.PRIORITY_CLASSES for i in range(10)]
        queue,coverage=m.pilot_queue(blocks,{})
        self.assertEqual(len(queue),30)
        self.assertEqual(coverage['selectedByClass'],{c:6 for c in m.PRIORITY_CLASSES})
        self.assertEqual((queue,coverage),m.pilot_queue(blocks[::-1],{}))
        self.assertTrue(all(r['identityDecision']=='unadjudicated' for r in queue))
        self.assertTrue(all(len(rep['excerpt'])<=400 for r in queue for rep in r['representatives']))

    def test_fixture_writer_hashes_and_oversized_separation(self):
        """Run IO only on tiny saved fixtures, retaining oversized summaries unexpanded."""
        base=Path('var/study2_step14/alignment-opportunities');base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            root=Path(temp);native=root/'native.jsonl';native.write_text('')
            (root/'derivation-provenance.jsonl').write_text('')
            (root/'review-dossier.jsonl').write_text('')
            (root/'identifier-triage.jsonl').write_text('')
            oversized=dict(blockID='large',crossFamily=True,memberCount=1000,membershipSha256='saved')
            (root/'oversized-summary.jsonl').write_bytes(m.identity.encoded(oversized)+b'\n')
            tm=dict(version=m.triage.VERSION,inputHashes={},implementationSha256=m.identity.sha(Path(m.triage.__file__)),
                    outputHashes={'identifier-triage.jsonl':m.identity.sha(root/'identifier-triage.jsonl')})
            (root/'manifest.json').write_bytes(m.identity.encoded(tm));pin=m.identity.sha(root/'manifest.json')
            rm=dict(outputHashes={'oversized-summary.jsonl':m.identity.sha(root/'oversized-summary.jsonl')})
            graph=dict(nodes=[node('source'),node('target',curated=False,doi='10.1234/x')],edges=[edge()])
            before={p.name:p.read_bytes() for p in root.iterdir()}
            with patch.object(m.identity,'verified_inputs',return_value=(graph,SPEC,native,{})), patch.object(m.triage,'inputs',return_value=(rm,SPEC,{})), patch.object(m.triage,'ROOT',root), patch.object(m.triage,'OUTPUT',root), patch.object(m.identity,'ROOT',root), patch.object(m,'TRIAGE_PIN',pin):
                a=root/'a';b=root/'b';m.run(a);m.run(b)
                for p in a.iterdir():
                    self.assertEqual(p.read_bytes(),(b/p.name).read_bytes())
                inv=json.loads((a/'inventory.json').read_bytes())
                self.assertEqual(inv['oversizedCoverage'],dict(allBlocks=1,crossFamilyBlocks=1,membersExpanded=0))
                self.assertEqual(inv['oversizedCrossFamily'],[oversized])
                self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir() if p.is_file()})
                (root/'identifier-triage.jsonl').write_text('drift')
                with self.assertRaisesRegex(ValueError,'INPUT_HASH_DRIFT'):
                    m.run(root/'c')
                self.assertFalse((root/'c').exists())

    def test_no_imputed_queue_or_opportunities(self):
        """Unavailable strata/opportunities are zero rather than manufactured."""
        result=self.inventory([node('source')],[])
        self.assertFalse(result['pilotQueue'])
        self.assertTrue(all(n==0 for n in result['tierCounts'].values()))
        queue,coverage=m.pilot_queue([block('Tool',1)],{})
        self.assertEqual(len(queue),1)
        self.assertEqual(coverage['availableByClass'],{'Tool':1})


if __name__=='__main__':
    unittest.main()
