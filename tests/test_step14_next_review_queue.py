"""Synthetic queue reconciliation tests; no corpus discovery or network calls."""
from copy import deepcopy
import socket
import unittest
from unittest.mock import patch

from src.evaluation import step14_next_review_queue as queue


def block(name, ids=('a', 'b'), mechanism=queue.LEXICAL, cls='Tool'):
    """Build a small saved-dossier-shaped fixture with explicit provenance."""
    members = [dict(occurrenceID=n, ontologyClass=cls, sourceFamilies=[f'family{i%2}'],
                    sourceArtifacts=['artifact:'+n], evidenceExcerpts=[dict(missingEvidenceText=False)],
                    identifierDeclarations=dict(truncated=False, value=[dict(scheme='doi', value=name,
                        basis='accepted_source_local_candidate')])) for i,n in enumerate(ids)]
    return dict(blockID=name, key=[mechanism, cls, *(['doi', name] if mechanism == queue.ID else [name])],
                candidateMechanism=mechanism, ontologyClass=cls, occurrenceIDs=list(ids), members=members,
                memberCount=len(ids), membershipSha256=queue.candidates.token(sorted(ids)),
                sourceFamilyDistribution={f'family{i}':sum(j%2==i for j in range(len(ids))) for i in range(2)},
                sourceArtifacts=['artifact:'+n for n in ids], existingBlockFlags=[])


def case(candidate='other', ids=('a', 'b')):
    """A reviewed case can have a different original candidate mechanism."""
    return dict(caseID='case1', occurrenceIDs=list(ids), originalCandidateIDs=[candidate], ontologyClass='Tool')


class QueueTests(unittest.TestCase):
    """Protect scope, deterministic selection, overlap, and nonmutation."""

    def setUp(self):
        """Forbid any accidental provider/network call."""
        patcher = patch.object(socket.socket, 'connect', side_effect=AssertionError('No calls'))
        patcher.start(); self.addCleanup(patcher.stop)

    def test_direct_review_vs_full_overlap(self):
        """Full overlap from a hub case is not a direct ordinary-block review."""
        row = block('new', mechanism=queue.ID)
        result = queue.reconcile([row], [], [case()], [])
        self.assertEqual(result['summary']['unreviewedBlocks'], 1)
        self.assertEqual(result['summary']['unreviewedWithFullOccurrenceOverlap'], 1)
        self.assertEqual(result['selectedBlockIDs'], [])
        self.assertEqual(queue.reconcile([row], [], [case('new')], [])['summary']['directlyReviewedBlocks'], 1)

    def test_partial_overlap_does_not_extend_approval(self):
        """Only the exact approved occurrence receives a prior-decision pointer."""
        result = queue.reconcile([block('new', ('a','c'))], [], [case()],
                                 [dict(caseID='case1', occurrenceIDs=['a'], decisionID='decision1')])
        row = result['blocks'][0]
        self.assertEqual(row['newOccurrenceIDs'], ['c'])
        self.assertEqual(row['priorApprovalDecisionIDsByOccurrence'], {'a':['decision1']})
        self.assertEqual(row['identityState'], 'no_new_decision_prior_approvals_do_not_extend')

    def test_scope_is_key_specific_and_truncation_unresolved(self):
        """An unrelated authoritative identifier cannot upgrade a local locator."""
        row = block('x', mechanism=queue.ID); member = row['members'][0]
        member['identifierDeclarations']['value'].append(dict(scheme='doi', value='different', basis='C-D04'))
        self.assertEqual(queue.scope_for_key(member, row['key']), 'source_local_literal_declaration')
        member['identifierDeclarations']['truncated'] = True
        self.assertEqual(queue.scope_for_key(member, row['key']), 'unresolved_declaration_scope')

    def test_oversized_not_expanded(self):
        """Saved summary membership hashes survive without constructing members/pairs."""
        oversized = dict(blockID='big', sourceFamilyDistribution={'x':90,'y':80}, crossFamily=True,
                         membershipVerified=True, memberCount=170, membershipSha256='saved', pairsGenerated=0)
        result = queue.reconcile([], [oversized], [], [])['oversized'][0]
        self.assertNotIn('occurrenceIDs', result)
        self.assertEqual(result['membershipSha256'], 'saved')
        self.assertEqual(result['overlapStatus'], 'not_recomputed_membership_not_expanded')

    def test_order_nonmutation_and_caps(self):
        """Order changes cannot change selected complete blocks; large blocks stay whole."""
        rows = [block(str(i), (f'a{i}',f'b{i}'), cls='Tool' if i%2 else 'Algorithm') for i in range(25)]
        rows.append(block('large', tuple(str(i) for i in range(10))))
        before = deepcopy(rows)
        result = queue.reconcile(rows, [], [], [])
        self.assertEqual(result, queue.reconcile(list(reversed(rows)), [], [], []))
        self.assertEqual(before, rows)
        self.assertEqual(len(result['selectedBlockIDs']), 18)
        self.assertNotIn('large', result['selectedBlockIDs'])
        self.assertEqual(len(queue.select_sample(result['blocks'], total_limit=4)), 2)

    def test_missing_provenance_retained_not_selected(self):
        """Incomplete context is visible in inventory rather than silently dropped."""
        row = block('gap'); row['members'][0]['sourceArtifacts'] = []
        result = queue.reconcile([row], [], [], [])
        self.assertEqual(result['blocks'][0]['contextGapOccurrenceIDs'], ['a'])
        self.assertEqual(result['selectedBlockIDs'], [])

    def test_hash_class_and_duplicate_fail_closed(self):
        """Malformed saved membership cannot enter a prospective queue."""
        for change in (lambda r:r.update(membershipSha256='wrong'),
                       lambda r:r['members'][0].update(ontologyClass='Paper')):
            row = block('x'); change(row)
            with self.assertRaises(ValueError):
                queue.reconcile([row], [], [], [])
        with self.assertRaises(ValueError):
            queue.reconcile([block('x'), block('x')], [], [], [])


if __name__ == '__main__':
    unittest.main()
