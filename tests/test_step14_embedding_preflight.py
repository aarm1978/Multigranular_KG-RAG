"""Synthetic-only tests: never scan the real occurrence corpus or generate vectors."""
from copy import deepcopy
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_embedding_preflight as preflight

SPEC = {'classes': [dict(name='Tool',id='T'), dict(name='Algorithm',id='A'),
    dict(name='ComputationalModel',id='C',abstract=True),
    dict(name='MLModel',id='M',parent='ciroh:ComputationalModel'), dict(name='Paper',id='P')]}


def occurrence(oid, family='github', cls='Tool', label='tool', quote='Explicit context', description=''):
    """Construct the established saved-occurrence projection without extraction."""
    node = dict(id=oid, **{'class':cls}, attributes={})
    labels = [label] if label else []; descriptions = [description] if description else []
    return dict(occurrenceID=oid, ontologyClass=cls, inventoryId={'Tool':'T','Algorithm':'A','MLModel':'M','Paper':'P'}[cls],
        lane='identity_declaration' if cls=='Paper' else 'semantic_comparison', sourceFamilies=[family],
        sourceArtifacts=['artifact:'+oid], labels=labels, contextualDescriptions=descriptions,
        evidenceReferences=[{'evidenceText':quote}], embeddingText='\n'.join([cls,*labels,*descriptions,*([quote] if quote else [])]),
        normalizedLabels=labels, identifierDeclarations=[], nativeReferences=[], versions={},
        originalSnapshotRecord=node, snapshotRecordSha256=preflight.candidates.token(node),
        preparationFlags=[], granularity='unspecified_requires_context_review')


def analyze(rows, **kwargs):
    """Use empty saved memberships unless a test supplies them explicitly."""
    args=dict(blocks=[],cases=[],reserved=[],decisions=[],hubs=[],spec=SPEC);args.update(kwargs)
    return preflight.analyze(iter(rows),**args)


class PreflightTests(unittest.TestCase):
    """Protect text accounting, scope, reconciliation, and offline behavior."""

    def setUp(self):
        """Fail on any network attempt in synthetic checks."""
        for method in ('connect','connect_ex'):
            p=patch.object(socket.socket,method,side_effect=AssertionError('No network'))
            p.start();self.addCleanup(p.stop)

    def test_class_only_and_label_only_not_context(self):
        """A nonempty class prefix cannot masquerade as eligible semantic evidence."""
        result=analyze([occurrence('a',label='',quote=''),occurrence('b',quote='')])
        self.assertEqual([r['textKind'] for r in result['occurrences']],['class_only','label_only'])
        self.assertEqual(result['summary']['workload']['proposedEligibleUniquePayloads'],0)

    def test_duplication_cache_not_identity(self):
        """Exact payload reuse reduces estimated work, never occurrence cardinality."""
        result=analyze([occurrence('a'),occurrence('b','publications')])
        self.assertEqual(result['summary']['coverage']['occurrences'],2)
        self.assertEqual(result['summary']['workload']['proposedEligibleUniquePayloads'],1)
        self.assertEqual(result['duplicateTexts'][0]['identityImplication'],'none')
        self.assertEqual(result['summary']['duplication']['evidenceQuotationsAcrossMultipleArtifacts'],1)

    def test_identity_lane_and_provenance_holds(self):
        """Identity-bearing classes are inventoried without expanding embedding scope."""
        paper=occurrence('p',cls='Paper');missing=occurrence('m');missing['sourceArtifacts']=[]
        multi=occurrence('f');multi['sourceFamilies']=['github','publications']
        result=analyze([paper,missing,multi])
        self.assertTrue(all(not r['proposedIndexEligible'] for r in result['occurrences']))

    def test_review_and_reservation_do_not_approve_neighbors(self):
        """Reviewed/reserved occurrences remain indexed but do not become new queries."""
        rows=[occurrence('a'),occurrence('b','publications'),occurrence('c','hydroshare')]
        result=analyze(rows,cases=[dict(caseID='case',occurrenceIDs=['a'])],
            reserved=[dict(blockID='reserved',occurrenceIDs=['b'])],
            decisions=[dict(decisionID='approved',occurrenceIDs=['a'])],
            hubs=[dict(targetIDs=['a','c'],identityScope='reference',evidenceTier='B')])
        self.assertEqual([r['proposedQueryEligible'] for r in result['occurrences']],[False,False,True])
        self.assertEqual(result['occurrences'][2]['priorApprovalDecisionIDs'],[])
        self.assertTrue(result['occurrences'][2]['sharedReferenceGroupIDs'])

    def test_oversized_membership_linear_and_fail_closed(self):
        """Reconstruct membership hashes without emitting an induced pair set."""
        rows=[occurrence(str(i),'github' if i%2 else 'publications') for i in range(40)]
        ids=sorted(r['occurrenceID'] for r in rows)
        block=dict(blockID='oversized',key=['lexical_similarity_only','Tool','tool'],
                   status='oversized_not_expanded',occurrenceIDs=[],memberCount=40,
                   membershipSha256=preflight.candidates.token(ids))
        result=analyze(rows,blocks=[block])
        self.assertEqual(len(result['occurrences']),40)
        self.assertTrue(all(r['oversizedBlockIDs']==['oversized'] for r in result['occurrences']))
        self.assertNotIn('pairs',result)
        block['membershipSha256']='drift'
        with self.assertRaises(ValueError):analyze(rows,blocks=[block])

    def test_text_budget_does_not_truncate(self):
        """Long evidence is retained by exact reference and held, not silently shortened."""
        row=occurrence('a',quote='z'*9000);before=deepcopy(row)
        result=analyze([row])['occurrences'][0]
        self.assertIn('above_proposed_text_budget_no_truncation',result['eligibilityHolds'])
        self.assertEqual(result['textCharacters'],len(row['embeddingText']))
        self.assertEqual(before,row)

    def test_class_and_family_peer_pools(self):
        """Other classes or same-family records do not supply compatible peer pools."""
        result=analyze([occurrence('a'),occurrence('b',cls='Algorithm',family='publications')])
        self.assertEqual(result['summary']['workload']['potentialCrossFamilyQueryOccurrences'],0)

    def test_determinism_nonmutation_and_original_versions(self):
        """Preserve unknown granularity and versions without inferring entity equality."""
        rows=[occurrence('a',cls='MLModel'),occurrence('b','publications',cls='MLModel')]
        rows[0]['versions']={'version':'v2.1'};rows[1]['versions']={'version':'v3.0'}
        before=deepcopy(rows)
        self.assertEqual(analyze(rows),analyze(rows));self.assertEqual(before,rows)
        self.assertEqual(analyze(rows)['occurrences'][0]['versions'],{'version':'v2.1'})

    def test_input_drift_and_duplicate_occurrences(self):
        """Reuse existing hash verification; malformed saved text is refused."""
        row=occurrence('a')
        with self.assertRaises(ValueError):analyze([row,row])
        row['embeddingText']='changed'
        with self.assertRaises(ValueError):analyze([row])
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'input';path.write_text('original');digest=preflight.identity.sha(path)
            preflight.pilot.verify(path,digest,{})
            path.write_text('changed')
            with self.assertRaises(ValueError):preflight.pilot.verify(path,digest,{})


if __name__=='__main__':
    unittest.main()
