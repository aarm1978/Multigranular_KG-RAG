"""Small offline tests for evidence-bound selection, never identity adjudication."""
from copy import deepcopy
from collections import Counter
import hashlib
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_evidence_review_batch as b
from test_step14_retrieval_reconciliation import endpoint, nomination


def named(oid,label,family='github',quote=None):
    """Prepare literal name/context metadata for a synthetic original occurrence."""
    row=endpoint(oid,family);row['labels']=[label]
    text=quote or f'{label} provides documented routing functionality for streamflow simulations.'
    row['selectedEvidence']=[dict(literalExcerpt=text,labelPresent=label in text,fullQuoteSha256=b.retrieval.digest(text))]
    return row


def pair(left,right,score=.8,approved=False):
    """Build the existing unordered reconciliation shape without induced grouping."""
    ids=sorted([left['occurrenceID'],right['occurrenceID']]);scope=b.retrieval.pair_scope(left,right)
    review=b.reconciliation.review_status(left,right)
    return dict(pairKeySha256=b.retrieval.candidates.token(ids),occurrenceIDs=ids,scope=scope,
        ontologyClass=left['ontologyClass'],sourceFamilyPair=' | '.join(sorted([left['sourceFamilies'][0],right['sourceFamilies'][0]])),
        review=review,directions=[dict(sourceLine=1,sourceLineSha256='synthetic',nomination=nomination(left,right,scores=dict(name=score,evidence=score)))],
        nominationViews=['name','evidence'],identityDecision=None,automaticMergeEligible=False)


class BatchTests(unittest.TestCase):
    """Protect priority/evidence signals, exact pair boundaries and anchor isolation."""
    def setUp(self):
        """Prevent every network operation during tests."""
        for name in ('connect','connect_ex'):
            p=patch.object(socket.socket,name,side_effect=AssertionError('OFFLINE'))
            p.start();self.addCleanup(p.stop)

    def test_named_context_before_high_similarity(self):
        """Distinct compared entities do not outrank a distinctive shared named cue."""
        a=named('a','RiverEngine');c=named('c','RiverEngine routing')
        x=named('x','LightGradientBoost',quote='LightGradientBoost and RFE are compared across several evaluation settings.')
        y=named('y','RFE',quote='LightGradientBoost and RFE are compared across several evaluation settings.')
        occurrences={r['occurrenceID']:r for r in (a,c,x,y)}
        frequencies=Counter(w for r in occurrences.values() for w in b.name_tokens(r))
        good=pair(a,c,.65);contrast=pair(x,y,.99)
        for p in (good,contrast):p['selectionFeatures']=b.features(p,occurrences,frequencies)
        self.assertLess(b.rank(good),b.rank(contrast))
        self.assertFalse(contrast['selectionFeatures']['sharedNameTokens'])
        self.assertIn('may compare distinct',contrast['selectionFeatures']['caveat'])
        self.assertIsNone(good['identityDecision'])

    def test_missing_context_and_versions_not_identity_decisions(self):
        """Names alone are insufficient for batch actionability; conflicts are surfaced."""
        a=named('a','RiverEngine',quote='RiverEngine');c=named('c','RiverEngine routing')
        rows={'a':a,'c':c};before=deepcopy(rows)
        f=b.features(pair(a,c),rows,Counter(riverengine=2))
        self.assertFalse(f['actionable']);self.assertEqual(rows,before)
        a['selectedEvidence']=deepcopy(c['selectedEvidence']);a['versions']={'version':'1'};c['versions']={'version':'2'}
        f=b.features(pair(a,c),rows,Counter(riverengine=2))
        self.assertTrue(f['recordedVersionMetadataDiffers']);self.assertEqual(f['priorityVector'][0],0)
        self.assertTrue(f['sharedFullQuoteHashes'])
        self.assertEqual(f['recordedGranularityAssessment'],'unspecified_requires_review')

    def test_bound_pool_and_deterministic_priority(self):
        """A repeated label cue cannot expand a pool quadratically or imply grouping."""
        with patch.object(b,'POOL_LIMIT',2):
            pool={}
            for i in range(10):
                item=dict(pairKeySha256=str(i),selectionFeatures=dict(labelCueForDiversityOnly=str(i),priorityVector=[i]))
                b.retain(pool,item)
            self.assertEqual(set(pool),{'8','9'})
            b.retain(pool,dict(pairKeySha256='other',selectionFeatures=dict(labelCueForDiversityOnly='9',priorityVector=[-1])))
            self.assertEqual(pool['9']['pairKeySha256'],'9')

    def stream(self,path,values,occurrences,limit=1):
        """Run a tiny pinned, sorted reconciliation stream."""
        values=sorted(values,key=lambda p:p['occurrenceIDs'])
        raw=b''.join(b.retrieval.identity.encoded(p)+b'\n' for p in values);path.write_bytes(raw)
        summary=dict(uniqueUnorderedPairs=len(values),counts=dict(reviewStatus=dict(Counter(p['review']['primary'] for p in values)),scope=dict(Counter(p['scope'] for p in values))))
        result=b.select_stream(path,occurrences,dict(pairsSha256=hashlib.sha256(raw).hexdigest(),summary=summary),limit)
        self.assertEqual(path.read_bytes(),raw);return result

    def test_scope_balance_no_transitive_group_and_anchors_separate(self):
        """Use only explicit two-member pairs; retain anchors and unselected counts."""
        rows=[named('a','RiverEngine'),named('b','RiverEngine routing'),named('c','HydroRoute'),named('d','HydroRoute package'),
              named('e','SnowRunner'),named('f','SnowRunner product','hydroshare'),named('g','ApprovedTool'),named('h','ApprovedTool version')]
        occurrences={r['occurrenceID']:r for r in rows}
        rows[1]['sourceArtifacts']=rows[0]['sourceArtifacts']
        rows[6]['priorMemberships']['approved']=rows[7]['priorMemberships']['approved']=['original-subset']
        values=[pair(rows[i],rows[i+1]) for i in (0,2,4,6)]
        with tempfile.TemporaryDirectory() as directory:
            selected,anchors,counts=self.stream(Path(directory)/'pairs.jsonl',values,occurrences)
            self.assertEqual(len(selected),3);self.assertEqual({p['scope'] for p in selected},set(b.retrieval.SCOPES))
            self.assertEqual(len(anchors),1);self.assertTrue(all(len(p['occurrenceIDs'])==2 for p in selected+anchors))
            self.assertEqual(counts['newPairs'],3);self.assertEqual(counts['unselectedNewPairsNotRejected'],0)
            again=self.stream(Path(directory)/'again.jsonl',list(reversed(values)),occurrences)
            self.assertEqual([p['pairKeySha256'] for p in selected],[p['pairKeySha256'] for p in again[0]])
            endpoints={r['occurrenceID']:r for r in rows}
            approvals={'original-subset':{'originalRecord':{'decisionID':'original-subset','occurrenceIDs':['g','h'],'granularity':'original'}}}
            before=deepcopy(approvals)
            cases=b.package_cases(selected,endpoints);anchor=b.package_cases(anchors,endpoints,True,approvals)[0]
            self.assertTrue(all(c['decisionStatus']=='unreviewed' and c['canonicalID'] is None for c in cases))
            self.assertEqual(anchor['originalApprovals'][0],approvals['original-subset']);self.assertEqual(approvals,before)

    def test_hash_drift_and_existing_output_stop(self):
        """Do not repair a corrupt pair stream or overwrite an existing review."""
        a,c=named('a','RiverEngine'),named('c','RiverEngine routing');p=pair(a,c)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pairs';path.write_bytes(b.retrieval.identity.encoded(p)+b'\n')
            with self.assertRaisesRegex(ValueError,'PAIR_FILE_HASH_DRIFT'):
                b.select_stream(path,{'a':a,'c':c},dict(pairsSha256='wrong',summary={}),1)
            with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):b.run(Path(directory))

    def test_evidence_enrichment_exact_offsets_and_metadata(self):
        """Selected evidence is recovered from its pinned original row without rewriting."""
        from test_step14_embedding_preflight import occurrence,SPEC
        original=occurrence('a',label='RiverEngine',quote='RiverEngine supplies documented routing functions for simulations.')
        original['evidenceReferences'][0].update(sourceUnitID='unit',startOffsetInDocument=90,endOffsetInDocument=155)
        projection=b.retrieval.project(original,1,SPEC)
        with tempfile.TemporaryDirectory() as directory,patch.object(b.retrieval.preflight.review,'INPUT',Path(directory)):
            path=Path(directory)/'occurrences.jsonl';raw=b.retrieval.identity.encoded(original)+b'\n';path.write_bytes(raw)
            endpoints=b.enrich([dict(occurrenceIDs=['a'])],{'a':projection})
            self.assertEqual(endpoints['a']['evidenceSources'][0]['originalSourceMetadata']['startOffsetInDocument'],90)
            self.assertEqual(path.read_bytes(),raw)
            broken=deepcopy(projection);broken['selectedEvidence'][0]['quoteStart']=1
            with self.assertRaisesRegex(ValueError,'EVIDENCE_OFFSET_DRIFT'):b.enrich([dict(occurrenceIDs=['a'])],{'a':broken})


if __name__=='__main__':unittest.main()
