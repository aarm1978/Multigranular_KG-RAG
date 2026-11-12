"""Synthetic tests for offline triage; no corpus execution or model calls."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.evaluation import step14_adjudication_triage as t


class TriageTests(unittest.TestCase):
    """Protect exact scopes, overlap accounting, and bounded nondecisions."""

    def block(self, bid, ids, oversized=False):
        """Construct an original direct-key block."""
        return dict(blockID=bid, occurrenceIDs=ids, memberCount=len(ids),
                    membershipSha256=t.r.candidates.token(sorted(ids)),
                    key=[t.queue.LEXICAL, 'Tool', bid],
                    status='oversized_not_expanded' if oversized else 'ambiguous_candidates_only')

    def pair(self, ids, state='validated_recommendation'):
        """Construct one explicit existing pair."""
        return dict(occurrenceIDs=ids, pairKeySha256=t.r.candidates.token(ids),
                    coverageState=state, origin='alias_extended')

    def endpoint(self, oid, family='hub', artifact='one'):
        """Construct source-bound metadata without inferring referent specificity."""
        return dict(occurrenceID=oid, ontologyClass='Tool', sourceFamilies=[family],
                    sourceArtifacts=[artifact], versions={}, granularity='unspecified_requires_context_review')

    def test_routes_overlap_without_pair_expansion(self):
        """Count one selected pair once even when two original blocks contain it."""
        blocks = [self.block('a', ['1', '2', '3']), self.block('b', ['1', '2']), self.block('large', [], True)]
        blocks[-1]['memberCount'] = 1000000
        pairs = [self.pair(['1', '2']), self.pair(['3', '4'], 'invalid_unresolved')]
        before = copy.deepcopy((blocks, pairs))
        rows, represented = t.reconcile_blocks(blocks, pairs)
        self.assertEqual(len(represented), 1)
        self.assertEqual(sum(len(r['selectedPairKeys']) for r in rows), 2)
        self.assertEqual(rows[-1]['overlapStatus'], 'unknown_not_expanded')
        self.assertEqual(rows[-1]['selectedPairKeys'], [])
        self.assertEqual((blocks, pairs), before)
        self.assertEqual(t.reconcile_blocks(list(reversed(blocks)), pairs), (rows, represented))

    def test_approval_intersections_do_not_union(self):
        """Overlapping approved subsets do not approve a bridge or a larger block."""
        decisions = [dict(decisionID='d1', occurrenceIDs=['1', '2']), dict(decisionID='d2', occurrenceIDs=['2', '3'])]
        result = t.exact_approvals(['1', '3'], decisions)
        self.assertFalse(any(r['entireCandidateWithinSubset'] for r in result))
        result = t.exact_approvals(['1', '2', '3'], decisions)
        self.assertTrue(all(r['entireSubsetPresent'] for r in result))
        self.assertFalse(any(r['entireCandidateWithinSubset'] for r in result))

    def test_bad_membership_fails_closed(self):
        """Hash drift and duplicate block identities fail rather than normalize."""
        block = self.block('a', ['1', '2'])
        block['occurrenceIDs'] = ['1', '3']
        with self.assertRaisesRegex(ValueError, 'BLOCK_HASH_DRIFT'):
            t.reconcile_blocks([block], [])
        block = self.block('a', ['1', '2'])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_BLOCK'):
            t.reconcile_blocks([block, block], [])

    def test_risks_and_scope_are_nondecisions(self):
        """Versions and model conflicts stay attributed, not repaired or approved."""
        endpoints = {'1': self.endpoint('1'), '2': self.endpoint('2', 'paper', 'two')}
        endpoints['1']['versions'] = {'version': '2.1'}
        endpoints['2']['versions'] = {'version': '3.0'}
        assessment = dict(recommendation='same_entity_candidate', identityLevel='conceptual',
                          missingInformation=['implementation'], conflictEvidenceIDs=['Q1'])
        row = t.pair_triage(self.pair(['1', '2']), endpoints, assessment, [])
        self.assertEqual(row['status'], t.NONDECISION)
        self.assertIn('structured_versions_differ_no_automatic_identity', row['risks'])
        self.assertIn('category_identity_level_tension_requires_review', row['risks'])
        self.assertEqual(row['familyCombination'], ['hub', 'paper'])
        self.assertEqual(row['identityScope'], t.retrieval.SCOPES[2])
        endpoints['2']['ontologyClass'] = 'Algorithm'
        with self.assertRaisesRegex(ValueError, 'PAIR_CLASS_DRIFT'):
            t.pair_triage(self.pair(['1', '2']), endpoints, assessment, [])

    def test_invalid_is_unassessed_not_rejection(self):
        """No assessment is fabricated for an invalid comparison."""
        endpoints = {x:self.endpoint(x) for x in ('1', '2')}
        row = t.pair_triage(self.pair(['1', '2']), endpoints, None, [])
        self.assertEqual(row['category'], 'unassessed')
        self.assertIsNone(row['modelIdentityLevel'])
        self.assertEqual(row['status'], t.NONDECISION)

    def test_complete_scopes_and_workload_caps(self):
        """Never shrink a group to fill the remaining review budget."""
        groups = [dict(groupID=str(i), occurrenceIDs=list(map(str, range(i))), priority=1) for i in range(2, 11)]
        groups.append(dict(groupID='invalid', occurrenceIDs=['a', 'b'], priority=0))
        before = copy.deepcopy(groups)
        selected = t.prioritize(groups, limit=3, members=9)
        self.assertEqual(selected[0]['groupID'], 'invalid')
        self.assertLessEqual(sum(len(g['occurrenceIDs']) for g in selected), 9)
        self.assertTrue(all(len(g['occurrenceIDs']) <= 8 for g in selected))
        self.assertEqual(groups, before)
        self.assertEqual(selected, t.prioritize(list(reversed(groups)), limit=3, members=9))

    def test_synthetic_saved_artifact_run(self):
        """Exercise bindings, SQLite dispositions, hashes, outputs and repeatability."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            def write(path, value, lines=False):
                """Create a small fixture without reading the real corpus."""
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b''.join(t.r.identity.encoded(x)+b'\n' for x in value)
                                 if lines else t.r.identity.encoded(value)+b'\n')

            ep = {x:self.endpoint(x) for x in ('a', 'b', 'c')}
            pairs = [self.pair(['a', 'b']), self.pair(['b', 'c']), self.pair(['a', 'c'])]
            bindings = [dict(unitID='U1', pairs={'P1':pairs[0]['pairKeySha256']},
                             entities={x:dict(occurrenceID=x, endpointRecordSha256=t.r.candidates.token(ep[x])) for x in ('a','b')}),
                        dict(unitID='U2', pairs={'P1':pairs[1]['pairKeySha256']},
                             entities={x:dict(occurrenceID=x, endpointRecordSha256=t.r.candidates.token(ep[x])) for x in ('b','c')})]
            root = base/'unified-review-queue/v1'
            write(root/'endpoint-provenance.jsonl', list(ep.values()), True)
            write(root/'unit-bindings.jsonl', bindings, True)
            write(root/'prior-decisions.jsonl', [], True)
            with sqlite3.connect(root/'coverage.sqlite') as db:
                db.execute('CREATE TABLE candidates(pairkey TEXT PRIMARY KEY, detail TEXT, disposition TEXT, origin TEXT, unit TEXT)')
                for i,pair in enumerate(pairs):
                    db.execute('INSERT INTO candidates VALUES(?,?,?,?,?)',
                               (pair['pairKeySha256'],json.dumps(pair),
                                'queued' if i<2 else 'prior_group_assessment_overlap',
                                pair['origin'], 'U'+str(i+1) if i<2 else None))
            block = self.block('block', ['a','b'])
            large = self.block('large', [], True); large['memberCount']=10000
            write(base/'semantic-candidates/v1/candidate-blocks.jsonl', [block,large], True)
            write(base/'referent-groups/v1/groups.jsonl', [dict(proposalID='block', occurrenceIDs=['a','b'], conflicts=[])], True)
            write(base/'referent-groups/v1/members.jsonl', [dict(ep[x], identifierDeclarations=[],
                  priorMemberships={}, originalReference={'file':'fixture'}, evidencePointers=[]) for x in ep], True)
            write(base/'referent-groups/v1/prior-decisions.jsonl', [], True)
            write(base/'next-review-queue/v1/block-inventory.jsonl', [dict(block, directReviewedCaseIDs=[],
                  reviewedOccurrenceIDs=['a'],newOccurrenceIDs=['b'])], True)
            write(base/'next-review-queue/v1/oversized-inventory.jsonl', [large], True)
            for package in ('semantic-candidates','referent-groups','unified-review-queue','next-review-queue'):
                directory=base/package/'v1'
                write(directory/'manifest.json', dict(inputHashes={},summary={},
                      outputHashes={p.name:t.r.identity.sha(p) for p in directory.iterdir()}))
            consolidated=base/'consolidated'
            write(consolidated/'recommendations.jsonl', [dict(binding=bindings[0], requestID='step14:U1',
                  identityApproved=False, provenance={'origin':'batch'}, recommendations=dict(caseID='U1',
                  assessments=[dict(pairID='P1',recommendation='same_entity_candidate',identityLevel='entity')]))], True)
            write(consolidated/'summary.json', dict(datasetSha256=t.r.identity.sha(consolidated/'recommendations.jsonl'),
                  uniqueAssessedPairs=1,validatedUnits=1,origins={'batch':1},remaining=[dict(requestID='step14:U2',pairs=1)]))
            ledger=base/'ledger.jsonl'; document=base/'document.json'
            write(ledger, [], True); write(document,{})
            with patch.object(t,'BASE',base), patch.object(t,'ROOT',base/'out'), \
                 patch.object(t,'CONSOLIDATED',consolidated), \
                 patch.object(t.queue.approvals,'APPROVALS',ledger), \
                 patch.object(t.queue.approvals,'DOCUMENT',document), \
                 patch.object(t.queue.approvals,'validate_approvals'), \
                 patch.object(t.socket.socket,'connect',side_effect=AssertionError('network forbidden')):
                summary=t.run(base/'out/first')
                self.assertEqual(summary['validatedRecommendationPairs'],1)
                self.assertEqual(summary['pairCoverageStates'],dict(validated_recommendation=1,invalid_unresolved=1,prior_group_assessment_overlap=1))
                self.assertEqual(summary['selectedPairsInOrdinaryBlocks'],1)
                invalid=list(t.r.rows(base/'out/first/invalid-pairs.jsonl'))
                self.assertEqual(invalid[0]['occurrenceIDs'],['b','c'])
                self.assertIsNone(invalid[0]['assessment'])
                self.assertEqual(t.run(base/'out/second'),summary)
                for path in (base/'out/first').iterdir():
                    self.assertEqual(path.read_bytes(),(base/'out/second'/path.name).read_bytes())
                # Mutating a consumed pinned sidecar fails before output creation.
                (root/'endpoint-provenance.jsonl').write_text('{}\n')
                with self.assertRaises(ValueError):
                    t.run(base/'out/bad')
                self.assertFalse((base/'out/bad').exists())

    def test_fresh_destination_guard(self):
        """Reject an existing destination before consuming any artifacts."""
        with tempfile.TemporaryDirectory() as tmp, patch.object(t, 'ROOT', Path(tmp)):
            with self.assertRaisesRegex(ValueError, 'FRESH_OUTPUT_REQUIRED'):
                t.run(Path(tmp))


if __name__ == '__main__':
    unittest.main()
