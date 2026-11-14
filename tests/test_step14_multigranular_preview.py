"""Synthetic checks for the proposed overlay; no corpus or provider access."""
import copy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.evaluation import step14_multigranular_preview as p


class OverlayTests(unittest.TestCase):
    """Preserve versions, evidence and exact candidate scopes."""

    def endpoint(self, oid, label, text, cls='ProcessBasedModel'):
        """Create a minimal original evidence-bound occurrence."""
        return dict(occurrenceID=oid,labels=[label],ontologyClass=cls,
            selectedEvidence=[dict(literalExcerpt=text,reference={'file':'fixture','line':1})])

    def pair(self, a, b):
        """Create an already nominated exact comparison."""
        return dict(occurrenceIDs=[a,b],ontologyClass='ProcessBasedModel',familyCombination=['github','publications'],
                    identityScope='between_families',recommendationReference={'file':'model'},bindingReference={'file':'bindings'})

    def test_nwm_versions_and_local_explicit_alias(self):
        """Distinct releases support a family hypothesis, never version identity."""
        left=self.endpoint('a','National Water Model v2.1','National Water Model (NWM) version 2.1 is available.')
        right=self.endpoint('b','NWM v3.0','NWM version 3.0 is available.')
        original=copy.deepcopy((left,right))
        result=p.broader_support(left,right)
        self.assertEqual(result['status'],'broader_candidate')
        self.assertEqual(result['anchorDescriptor']['literalName'],'national water model')
        self.assertEqual([x['evidence'][0]['qualifier'] for x in result['links']],['2.1','3.0'])
        self.assertEqual((left,right),original)
        right['selectedEvidence'][0]['literalExcerpt']='NWM provides simulations.'
        self.assertEqual(p.broader_support(left,right)['status'],'held')

    def test_family_source_not_narrower_correspondence(self):
        """An explicit family source supports an anchor without a false specialization."""
        result=p.broader_support(self.endpoint('a','NWM','NWM model family is described here.'),
                                 self.endpoint('b','NWM v3.0','NWM version 3.0 is described here.'))
        self.assertEqual(result['links'][0]['relationIntent'],'family_anchor_identity_candidate')
        self.assertEqual(result['links'][1]['relationIntent'],'broader_correspondence_candidate')

    def test_safe_exact_alias_remains_exact_candidate(self):
        """A saved exact candidate does not need invented family evidence."""
        endpoints={x:self.endpoint(x,'NWM','Named model used in this study.') for x in ('a','b')}
        group=dict(simulationID='original',occurrenceIDs=['a','b'],selectedPairKeys=['ab'],preOverlapState=p.baseline.ACCEPTED)
        before=copy.deepcopy(group)
        rows,links,summary=p.overlay({'ab':self.pair('a','b')},endpoints,[group])
        self.assertEqual(rows[0]['status'],'exact_candidate')
        self.assertEqual(links,[])
        self.assertEqual(group,before)
        self.assertEqual(summary['identityDecisions'],0)

    def test_overlaps_are_diagnostics_not_unions(self):
        """Compatible individual correspondences survive, without an induced A-C pair."""
        endpoints={x:self.endpoint(x,'NWM v'+v,'NWM version '+v+' is documented.') for x,v in [('a','2.1'),('b','3.0'),('c','4.0')]}
        pairs={'ab':self.pair('a','b'),'bc':self.pair('b','c')}
        rows,links,summary=p.overlay(pairs,endpoints,[])
        self.assertEqual(len(rows),2)
        self.assertEqual(summary['broaderUniqueOccurrences'],3)
        self.assertEqual(summary['distinctAnchorHypotheses'],2)
        self.assertEqual(summary['proposedNonidentityLinks'],4)
        groups=[dict(simulationID=k,occurrenceIDs=v['occurrenceIDs']) for k,v in pairs.items()]
        before=copy.deepcopy(groups)
        components=p.overlap_components(groups)
        self.assertEqual(components[0]['bridgeOccurrences'],['b'])
        self.assertEqual(groups,before)

    def test_incompatible_class_and_unaffirmed_referent_hold(self):
        """Common names/superclasses and architecture mentions are insufficient."""
        left=self.endpoint('a','NWM','NWM version 2.1 is available.')
        right=self.endpoint('b','NWM','NWM version 3.0 is available.',cls='Tool')
        self.assertEqual(p.broader_support(left,right)['status'],'held')
        right=self.endpoint('b','Other','Other version 3.0 is available.')
        self.assertEqual(p.broader_support(left,right)['status'],'held')
        right=self.endpoint('b','NWM','NWM version 3.0 is not supported.')
        self.assertEqual(p.broader_support(left,right)['status'],'held')

    def test_missing_support_does_not_modify_evidence(self):
        """Unsupported sources remain held and original model bindings stay attached."""
        endpoints={x:self.endpoint(x,'NWM','NWM') for x in ('a','b')}
        pairs={'ab':self.pair('a','b')};before=copy.deepcopy((pairs,endpoints))
        rows,_,summary=p.overlay(pairs,endpoints,[])
        self.assertEqual(rows[0]['originalBindingReference'],pairs['ab']['bindingReference'])
        self.assertEqual(rows[0]['status'],'held')
        self.assertEqual((pairs,endpoints),before)
        self.assertEqual(summary['graphWrites'],0)

    def test_ambiguous_bridge_holds_only_affected_links(self):
        """Contradictory local alias expansions cannot merge family hypotheses."""
        endpoints={
            'a':self.endpoint('a','Model Alpha','Model Alpha (M) version 1 is available.'),
            'b':self.endpoint('b','M','M version 2 is available.'),
            'c':self.endpoint('c','Model Beta','Model Beta (M) version 3 is available.')}
        rows,links,summary=p.overlay({'ab':self.pair('a','b'),'bc':self.pair('b','c')},endpoints,[])
        self.assertEqual(summary['incompatibleAnchorOccurrences'],['b'])
        self.assertEqual(summary['proposedNonidentityLinks'],2)
        self.assertTrue(all(x['status']=='held_ambiguous_anchor_bridge' for x in rows))
        self.assertEqual({x['occurrenceID'] for x in links if x['status']=='proposed_nonidentity_correspondence'},{'a','c'})

    def test_saved_artifact_roundtrip_preserves_approvals(self):
        """Exercise the actual consumer on tiny pinned artifacts, not corpus data."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'baseline';triage=root/'triage'
            def write(path,value,lines=False):
                """Write synthetic canonical fixture bytes."""
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b''.join(p.r.identity.encoded(x)+b'\n' for x in value) if lines
                                 else p.r.identity.encoded(value)+b'\n')
            ep=root/'unified-review-queue/v1/endpoint-provenance.jsonl'
            write(ep,[self.endpoint(x,'NWM','NWM version '+v+' is available.') for x,v in [('a','2.1'),('b','3.0')]],True)
            pair=dict(self.pair('a','b'),pairKeySha256='ab')
            write(triage/'pair-inventory.jsonl',[pair],True)
            write(triage/'manifest.json',dict(outputHashes={'pair-inventory.jsonl':p.r.identity.sha(triage/'pair-inventory.jsonl')}))
            group=dict(simulationID='g',occurrenceIDs=['a','b'],selectedPairKeys=['ab'],preOverlapState=p.baseline.ACCEPTED,state=p.baseline.ACCEPTED, routes=['alias_extended'],ontologyClass=['ProcessBasedModel'],familyCombination=['github','publications'],identityScope='between_families')
            approvals=[dict(decisionID='historical',occurrenceIDs=['a'],authority='unchanged')]
            for name,rows in [('group-simulations.jsonl',[group]),('prior-decisions.jsonl',approvals),('oversized-inventory.jsonl',[])]:
                write(source/name,rows,True)
            write(source/'summary.json',dict(candidateCompleteScopes=1,preOverlapAcceptedGroups=1,
                overlapBlockedGroups=0,provisionalAcceptedGroups=1,acceptedByRoute={},explicitPairCoverage={},preservedTriageAccounting={}))
            pins={str(triage/'manifest.json'):p.r.identity.sha(triage/'manifest.json'),str(ep):p.r.identity.sha(ep)}
            pins.update({name:p.r.identity.sha(Path(name)) for name in ('src/ontology/ontology_spec.yaml','src/ontology/ciroh_ontology.owl')})
            write(source/'manifest.json',dict(inputHashes=pins,outputHashes={x.name:p.r.identity.sha(x) for x in source.iterdir()}))
            before=(source/'prior-decisions.jsonl').read_bytes()
            with patch.object(p.baseline.triage,'BASE',root),patch.object(p.baseline.triage,'ROOT',triage.parent),patch.object(p,'ROOT',root/'out'):
                # Consumer's established triage path is ROOT/v1.
                with patch.object(p.baseline.triage,'ROOT',root/'triage-root'):
                    target=root/'triage-root/v1';target.parent.mkdir();triage.rename(target)
                    manifest=p.r.load(source/'manifest.json')
                    manifest['inputHashes'][str(target/'manifest.json')]=manifest['inputHashes'].pop(str(triage/'manifest.json'))
                    write(source/'manifest.json',manifest)
                    summary=p.run(source,root/'out/first')
                    self.assertEqual(summary['proposedNonidentityLinks'],2)
                    self.assertEqual((root/'out/first/prior-decisions.jsonl').read_bytes(),before)
                    self.assertEqual(p.run(source,root/'out/second'),summary)
                    for path in (root/'out/first').iterdir():
                        self.assertEqual(path.read_bytes(),(root/'out/second'/path.name).read_bytes())
                    self.assertEqual((source/'prior-decisions.jsonl').read_bytes(),before)

if __name__=='__main__':unittest.main()
