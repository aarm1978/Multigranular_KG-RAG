"""Small offline reconciliation fixtures; no full retrieval scan or identity review."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_retrieval_reconciliation as r
from test_step14_embedding_preflight import occurrence, SPEC


def endpoint(oid, family='github'):
    """Create an existing, exactly referenced occurrence without new entity IDs."""
    row=r.retrieval.project(occurrence(oid,family,label='identical label',quote='identical label is documented'),1,SPEC)
    row['priorMemberships']={k:[] for k in ('approved','reviewed','reserved','queued','blocks')}
    return row


def nomination(a,b,views=None,scores=None):
    """Construct the authentic retrieval output shape with exact endpoint references."""
    return dict(queryID=a['occurrenceID'],targetID=b['occurrenceID'],ontologyClass=a['ontologyClass'],
        scope=r.retrieval.pair_scope(a,b),scores=scores or dict(name=.8,evidence=.6),nominatedBy=views or ['name','evidence'],
        queryReference=a['originalReference'],targetReference=b['originalReference'],
        queryTextHashes=a['textHashes'],targetTextHashes=b['textHashes'],flags=r.retrieval.pair_flags(a,b),
        identityDecision=None,automaticMergeEligible=False)


class ReconciliationTests(unittest.TestCase):
    """Check exact membership, accounting, provenance and bounded diagnostic choices."""
    def setUp(self):
        """Fail immediately if any test attempts a network request."""
        for name in ('connect','connect_ex'):
            p=patch.object(socket.socket,name,side_effect=AssertionError('OFFLINE'))
            p.start();self.addCleanup(p.stop)

    def run_fixture(self, root, values, endpoints, size=6):
        """Stream tiny JSONL via SQLite and return summary and exact pair records."""
        root.mkdir(); source=root/'source.jsonl'
        raw=b''.join(r.retrieval.identity.encoded(v)+b'\n' for v in values); source.write_bytes(raw)
        counts={scope:dict(directedNominations=sum(v['scope']==scope for v in values)) for scope in r.retrieval.SCOPES}
        expected=dict(outputHashes={'candidates.jsonl':hashlib.sha256(raw).hexdigest()},scopes=counts)
        with sqlite3.connect(root/'scratch.sqlite') as connection:
            r.ingest(connection,source,endpoints,expected)
            summary=r.summarize(connection,endpoints,root,size)
        self.assertEqual(source.read_bytes(),raw)
        return summary,list(r.retrieval.rows(root/'pairs.jsonl')),r.retrieval.load(root/'shortlist.json')

    def test_reciprocal_preservation_and_no_label_merge(self):
        """Reciprocal rows collapse only as pair bookkeeping, retaining both scores."""
        a,b,c=[endpoint(x) for x in 'abc']; values=[nomination(a,b,['name']),nomination(b,a,['evidence'],dict(name=.800001,evidence=.600001)),nomination(a,c)]
        original=deepcopy(values)
        with tempfile.TemporaryDirectory() as directory:
            summary,pairs,short=self.run_fixture(Path(directory)/'one',values,{x['occurrenceID']:x for x in (a,b,c)})
            self.assertEqual((summary['uniqueUnorderedPairs'],summary['directedNominations'],summary['reciprocalPairs']),(2,3,1))
            self.assertEqual([d['nomination'] for d in pairs[0]['directions']],values[:2])
            self.assertEqual(pairs[0]['directions'][0]['sourceLineSha256'],hashlib.sha256(r.retrieval.identity.encoded(values[0])+b'\n').hexdigest())
            self.assertEqual(summary['directedNominationViewCounts'],{'name':1,'evidence':1,'evidence+name':1})
            self.assertEqual(summary['counts']['reviewStatus'],{'new_pair_relative_to_pinned_authorities':2})
            self.assertTrue(all(p['identityDecision'] is None and not p['automaticMergeEligible'] for p in pairs))
            self.assertEqual(values,original)
            self.assertIn('originalReference',short['pairs'][0]['endpoints'][0])

    def test_exact_approval_subsets_no_transitive_or_endpoint_approval(self):
        """A-B and B-C approvals never approve A-C; co-review is not adjudication."""
        a,b,c=[endpoint(x) for x in 'abc']
        a['priorMemberships']['approved']=['ab'];b['priorMemberships']['approved']=['ab','bc'];c['priorMemberships']['approved']=['bc']
        self.assertEqual(r.review_status(a,b)['primary'],'same_explicit_approved_subset')
        self.assertTrue(r.review_status(a,c)['newPair'])
        a['priorMemberships']['reviewed']=['case'];c['priorMemberships']['reviewed']=['case']
        self.assertEqual(r.review_status(a,c)['primary'],'same_prior_pilot_case')
        self.assertFalse(r.review_status(a,c)['sharedMemberships']['approved'])
        c['priorMemberships']['reviewed']=['different-case'];self.assertTrue(r.review_status(a,c)['newPair'])

    def test_queue_and_oversized_membership_without_pair_expansion(self):
        """A shared saved block suppresses shortlist novelty, not entity separation."""
        a,b=endpoint('a'),endpoint('b')
        for field,status in [('blocks','same_existing_candidate_block'),('queued','same_existing_queue_block'),('reserved','same_reserved_queue_block')]:
            a['priorMemberships'][field]=b['priorMemberships'][field]=['exact-group']
            self.assertEqual(r.review_status(a,b)['primary'],status)
        indexed=r.index_members([dict(caseID='large',occurrenceIDs=[str(i) for i in range(1000)])],'caseID')
        self.assertEqual(len(indexed),1000);self.assertEqual(indexed['0'],{'large'})

    def test_corrupt_hash_duplicate_direction_and_missing_endpoint_stop(self):
        """Fail closed on broken retrieval bindings instead of repairing nominations."""
        a,b=endpoint('a'),endpoint('b');row=nomination(a,b);ends={'a':a,'b':b}
        for field,value in [('targetID','missing'),('scope','between_families'),('ontologyClass','Algorithm'),
                            ('queryReference',{}),('queryTextHashes',{}),('identityDecision','approved')]:
            broken=deepcopy(row);broken[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):r.validate_nomination(broken,ends)
        for value in (float('nan'),True,1.5):
            broken=deepcopy(row);broken['scores']['name']=value
            with self.assertRaisesRegex(ValueError,'INVALID_COSINE_SCORE'):r.validate_nomination(broken,ends)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_DIRECTED_NOMINATION'):self.run_fixture(root/'duplicate',[row,row],ends)
            source=root/'wronghash.jsonl';source.write_bytes(r.retrieval.identity.encoded(row)+b'\n')
            with sqlite3.connect(':memory:') as connection,self.assertRaisesRegex(ValueError,'NOMINATION_HASH_DRIFT'):
                r.ingest(connection,source,ends,dict(outputHashes={'candidates.jsonl':'wrong'},scopes={}))

    def test_balanced_new_only_shortlist_all_scopes_and_challenges(self):
        """Balance scopes and include ambiguity; prior shared reviews cannot enter."""
        ends={str(i):endpoint(str(i),'github' if i<4 else 'hydroshare') for i in range(6)}
        ends['1']['sourceArtifacts']=ends['0']['sourceArtifacts']
        ends['2']['versions']={'version':'v1'};ends['3']['versions']={'version':'v2'}
        ends['4']['flags'].append('weak_context_no_literal_label_match')
        ends['0']['priorMemberships']['reviewed']=['old'];ends['5']['priorMemberships']['reviewed']=['old']
        values=[nomination(ends[a],ends[b]) for a,b in [('0','1'),('2','3'),('0','4'),('0','5')]]
        with tempfile.TemporaryDirectory() as directory:
            summary,pairs,short=self.run_fixture(Path(directory)/'one',values,ends,3)
            self.assertEqual(summary['shortlistByScope'],{s:1 for s in r.retrieval.SCOPES})
            self.assertTrue(all(p['review']['newPair'] for p in short['pairs']))
            self.assertNotIn(['0','5'],[p['occurrenceIDs'] for p in short['pairs']])
            self.assertIn('different_structured_version_metadata_requires_scope_review',[p['challenge'] for p in short['pairs']])
            other,_,second=self.run_fixture(Path(directory)/'two',values,ends,3)
            self.assertEqual(summary,other);self.assertEqual(short,second)

    def test_score_descriptions_and_roundoff(self):
        """Histogram accounting preserves values, including endpoint float roundoff."""
        dist=r.Distribution()
        for value in (-1.,0.,1.0000001):dist.add(value)
        report=dist.report()
        self.assertEqual(report['count'],3);self.assertEqual(sum(report['histogramCounts']),3)
        self.assertEqual(report['maximum'],1.0000001)
        self.assertAlmostEqual(report['mean'],.0000001/3)

    def test_existing_output_refused_before_inputs(self):
        """Never overwrite a prior local reconciliation, even if incomplete."""
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'verify_sources') as verify:
            with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):r.run(Path(directory))
            verify.assert_not_called()


if __name__=='__main__':unittest.main()
