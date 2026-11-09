"""Offline direct-key grouping regression tests; no identity decisions."""
from copy import deepcopy
import socket
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from src.evaluation import step14_referent_groups as g


def record(oid, family='github', cls='Tool'):
    """Construct an exact synthetic occurrence reference."""
    return dict(occurrenceID=oid, ontologyClass=cls, inventoryId='A', lane='semantic_comparison',
        labels=['RiverEngine'], versions={}, granularity='unspecified_requires_context_review',
        sourceFamilies=[family], sourceArtifacts=['source:'+oid], identifierDeclarations=[],
        declaredExistingNodeIDs=[], preparationFlags=[], nativeReferences=[{'original':'unchanged'}],
        evidenceReferences=[dict(evidenceText='RiverEngine routes streamflow.', start=17, end=45)])


def block(ids, name='RiverEngine', kind='lexical_similarity_only'):
    """Create a direct block, not a connected component."""
    key=[kind,'Tool',name] if kind=='lexical_similarity_only' else [kind,'Tool','url',name]
    return dict(blockID=g.r.candidates.token(key), key=key, occurrenceIDs=ids,
        membershipSha256=g.r.candidates.token(ids), memberCount=len(ids), flags=[])


class GroupsTests(unittest.TestCase):
    def setUp(self):
        """Block network for all tests."""
        for method in ('connect','connect_ex'):
            p=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'))
            p.start();self.addCleanup(p.stop)

    def test_four_families_provenance_and_no_decisions(self):
        """Every original reference survives without a canonical assignment."""
        originals=[record(str(i),f) for i,f in enumerate(('github','hydroshare','ciroh_hub','publications'))]
        before=deepcopy(originals)
        rows={x['occurrenceID']:g.member(x,i+1) for i,x in enumerate(originals)}
        result=g.propose(block(list(rows)),rows)
        self.assertEqual(len(result['sourceFamilies']),4)
        self.assertIsNone(result['canonicalID']);self.assertIsNone(result['identityDecision'])
        self.assertEqual(originals,before)
        self.assertEqual(rows['0']['evidencePointers'][0]['recordSha256'],g.r.candidates.token(originals[0]['evidenceReferences'][0]))
        self.assertEqual(g.propose(block(list(rows)),rows),result)

    def test_no_transitive_or_approval_union(self):
        """A-B and B-C never imply A-C or an expanded approval."""
        rows={x:g.member(record(x),i) for i,x in enumerate('abc')}
        groups=[g.propose(block(['a','b'],'RiverEngine'),rows),g.propose(block(['b','c'],'OtherEngine'),rows)]
        approval=dict(decisionID='D',occurrenceIDs=['a','b'])
        g.attach_approvals(groups,[approval])
        self.assertEqual([x['occurrenceIDs'] for x in groups],[['a','b'],['b','c']])
        self.assertFalse(groups[1]['exactApprovalSubsets'][0]['fullOriginalSubsetPresent'])
        self.assertEqual(groups[1]['exactApprovalSubsets'][0]['overlap'],['b'])

    def test_generic_version_and_class_guards(self):
        """Generic names are omitted; version/class differences cannot become merges."""
        rows={x:g.member(record(x),i) for i,x in enumerate('ab')}
        self.assertIsNone(g.propose(block(['a','b'],'model'),rows))
        rows['b']['versions']={'version':'2'}
        result=g.propose(block(['a','b']),rows)
        self.assertIn('recorded_version_metadata_differs_no_bridge_authorized',result['conflicts'])
        rows['b']['ontologyClass']='Algorithm'
        with self.assertRaisesRegex(ValueError,'CLASS_DRIFT'):g.propose(block(['a','b']),rows)

    def test_identifier_lane_and_corrupt_membership(self):
        """Own identifiers remain distinct from source-local declarations."""
        a=record('a');a['identifierDeclarations']=[dict(basis='deterministic_entity_own_field',scheme='doi',value='x')]
        b=record('b');b['identifierDeclarations']=[dict(basis='accepted_source_local_candidate',scheme='literal_exactIdentifier',value='x')]
        rows={x['occurrenceID']:g.member(x,i) for i,x in enumerate((a,b))}
        self.assertTrue(rows['a']['deterministicIdentityLane']);self.assertFalse(rows['b']['deterministicIdentityLane'])
        result=g.propose(block(['a','b'],'x','identifier_declaration_only'),rows)
        self.assertEqual(result['status'],'unresolved_proposal')
        bad=block(['a','b']);bad['membershipSha256']='bad'
        with self.assertRaisesRegex(ValueError,'MEMBERSHIP_HASH_DRIFT'):g.propose(bad,rows)

    def test_existing_output_refused_before_reading_inputs(self):
        """Repeated execution cannot overwrite a preparation."""
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)
            with patch.object(g,'ROOT',path):
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):g.run(path)

    def test_set_counts_not_group_sums(self):
        """Overlapping proposal membership does not inflate occurrence coverage."""
        rows={x:g.member(record(x),i) for i,x in enumerate('abcd')}
        groups=[g.propose(block(['a','b']),rows),g.propose(block(['b','c'],'OtherEngine'),rows)]
        result=g.summarize(groups,rows,{})
        self.assertEqual(result['occurrenceCoverage'],3)
        self.assertEqual(result['ungroupedOccurrences'],1)
        self.assertEqual(result['identityDecisions'],0)


if __name__=='__main__':unittest.main()
