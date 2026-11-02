"""Fast synthetic feasibility checks; no corpus, readers, provider or network."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import hub_full_content_feasibility as f


class FeasibilityTests(unittest.TestCase):
    """Protect exact full-text accounting and distinct production denominators."""

    def setUp(self):
        """Block sockets for every test, including optional tokenizer discovery."""
        for target,name in ((socket.socket,'connect'),(socket.socket,'connect_ex'),(socket,'create_connection')):
            blocker=patch.object(target,name,side_effect=AssertionError('NO_NETWORK'))
            blocker.start()
            self.addCleanup(blocker.stop)

    def page(self,key='a',text='Full café 😀\n<GitHubReadme repo="x" />\n{dynamic()}'):
        """Build an exact synthetic authority, including unfiltered MDX syntax."""
        return dict(page_key=key,canonical_url='https://example.test/'+key,corpus_path=key+'.mdx',
                    content_mdx=text,content_sha256=f.sha(text))

    def test_complete_unicode_utf8_accounting_and_ordering(self):
        """Count all markup and Unicode, preserving deterministic identity order."""
        a,b=self.page(),self.page('b','')
        result=f.page_inventory([b,a],lambda text:len(text)//2)
        self.assertEqual([p['pageKey'] for p in result],['a','b'])
        self.assertEqual(result[0]['unicodeCharacters'],len(a['content_mdx']))
        self.assertEqual(result[0]['utf8Bytes'],len(a['content_mdx'].encode()))
        self.assertEqual(result[0]['offlineTokens'],len(a['content_mdx'])//2)
        self.assertTrue(result[1]['emptyContent'])
        self.assertEqual(result,f.page_inventory([a,b],lambda text:len(text)//2))
        self.assertIsNone(f.sizes('abc')['offlineTokens'])

    def test_hash_missing_malformed_and_duplicate_identities_fail_closed(self):
        """Never normalize, silently drop, or repair invalid authority records."""
        for alteration,message in [({'content_sha256':'bad'},'CONTENT_SHA256_DRIFT'),
                                    ({'content_mdx':None},'MISSING_OR_MALFORMED_CONTENT'),
                                    ({'content_mdx':'\ud800'},'MALFORMED_UNICODE_CONTENT'),
                                    ({'page_key':''},'PAGE_IDENTITY')]:
            with self.subTest(alteration=alteration),self.assertRaisesRegex(ValueError,message):
                f.page_inventory([{**self.page(),**alteration}])
        for field in ('page_key','canonical_url','corpus_path'):
            other=self.page('b');other[field]=self.page()[field]
            with self.assertRaisesRegex(ValueError,'DUPLICATE_PAGE_IDENTITY'):
                f.page_inventory([self.page(),other])

    def test_percentiles_and_unavailable_tokens(self):
        """Define interpolation explicitly rather than silently choosing quantiles."""
        stats=f.distribution([30,0,20,10])
        for key,value in zip(('min','median','P90','P95','max'),(0,15,27,28.5,30)):
            self.assertAlmostEqual(stats[key],value)
        self.assertIsNone(f.distribution([None])['median'])
        self.assertEqual(f.distribution([4])['P95'],4)

    def production(self):
        """Three pages: zero, one, and two requests, with distinct delivery outcomes."""
        pages=f.page_inventory([self.page(k) for k in ('a','b','c')])
        owners,requests,entries=[],[],[]
        for index,page in enumerate(pages):
            grouped=[]
            for n in range(index):
                rid=f'{index}-{n}';identity={'requestID':rid}
                entry=dict(ownerID=page['ownerID'],identity=identity,bundleSha256='bundle')
                entries.append(entry)
                deliveries=[dict(number=1,responseStatus='completed')]
                if n==1:
                    deliveries.insert(0,dict(number=0,responseStatus='incomplete'))
                requests.append(dict(requestID=rid,**entry,state='completion',processable=True,deliveries=deliveries))
                grouped.append(dict(requestID=rid))
            owners.append(dict(family='ciroh_hub',ownerID=page['ownerID'],requests=index,sealedCoverage=dict(
                ownerID=page['ownerID'],readerSourceUnitIDs=['u'] if index else [],groups=grouped,
                diagnostics=[{'reason':'uncertain_component_visibility'}] if not index else [])))
        return pages,owners,requests,entries

    def test_reconciliation_does_not_assume_one_request_per_page(self):
        """Show the difference as missing request pages minus additional requests."""
        args=self.production();summary=f.reconcile(*args)
        self.assertEqual((summary['pages'],summary['requests'],summary['pagesWithoutRequests'],
                          summary['additionalRequestsBeyondOnePerRepresentedPage']),(3,3,1,1))
        self.assertEqual(summary['completedRequests'],3)
        self.assertEqual(summary['recordedResponseDeliveries'],4)
        self.assertEqual(summary['providerCompletedResponses'],3)
        self.assertEqual(summary['noRequestPages'][0]['production']['noRequestExplanation'],'no_reader_admitted_units')
        self.assertEqual(summary['difference'],0)

    def test_reconciliation_rejects_missing_duplicate_and_misassociated_requests(self):
        """Reject count and identity inconsistencies instead of explaining them away."""
        for change in ('missing','duplicate','owner'):
            args=self.production()
            if change=='missing':args[2].pop()
            if change=='duplicate':args[2].append(deepcopy(args[2][0]))
            if change=='owner':args[2][0]['ownerID']='unknown'
            with self.subTest(change=change),self.assertRaises(ValueError):
                f.reconcile(*args)
        args=self.production();args[1].pop()
        with self.assertRaisesRegex(ValueError,'PRODUCTION_PAGE_IDENTITY_DRIFT'):
            f.reconcile(*args)

    def test_overhead_is_measured_without_modifying_original_envelope(self):
        """Retain fixed schema/prompt overhead and mark variable metadata estimates."""
        payload={k:k for k in ('instructions','responseContract','targetProfile','contractID','promptIdentifier','schemaVersion')}
        payload['sourceUnits']=[{'text':'FULL TEXT','sourceUnitID':'u'}]
        original={'body':{'input':json.dumps(payload),'text':{'format':{'strict':True}},'model':'original-model'}}
        before=deepcopy(original)
        measured=f.overhead(original,len)
        self.assertEqual(original,before)
        self.assertGreater(measured['fixedPromptSchema']['utf8Bytes'],0)
        payload['sourceUnits'][0]['text']='LONGER TEXT'*50
        other=deepcopy(original);other['body']['input']=json.dumps(payload)
        self.assertEqual(f.overhead(other,len),measured)
        self.assertIn('not a sendable',measured['interpretation'])

    def test_cached_tokenizer_no_download_and_output_overwrite_rejection(self):
        """Availability is optional; existing output must be rejected before analysis."""
        count,metadata=f.tokenizer()
        self.assertEqual(metadata['available'],count is not None)
        if count:
            self.assertGreater(count('Some test text.'),0)
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary);output=repo/f.OUTPUT;output.mkdir(parents=True)
            with patch.object(f,'analyze',side_effect=AssertionError('ANALYSIS_NOT_ALLOWED')):
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):
                    f.run(repo,repo/f.REPORTS,repo/f.QUEUE,output)

    def test_synthetic_file_analysis_hashes_ordering_and_no_input_writes(self):
        """Exercise joins and overhead ranges with tiny fake persisted records only."""
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary);reports=repo/f.REPORTS;queue=repo/f.QUEUE
            reports.mkdir(parents=True);(queue/'queue').mkdir(parents=True)
            sources=[self.page(k) for k in ('a','b','c')]
            _,owners,requests,entries=self.production()
            for source,owner in zip(sources,owners):
                owner['sealedCoverage'].update(family='ciroh_hub',sourceRecordSha256=f.digest(f.canonical(source)))
            payload={k:k for k in ('instructions','responseContract','targetProfile','contractID','promptIdentifier','schemaVersion')}
            payload['sourceUnits']=[{'text':'original selected text'}]
            prepared=dict(body=dict(input=json.dumps(payload),text={'format':{}},model='historical-model'))
            wire=f.canonical(prepared)
            for index,entry in enumerate(entries):
                entry.update(family='ciroh_hub',bundleFile=str(index)+'.json',bundleSha256=f.digest(wire))
                requests[index]['family']='ciroh_hub';requests[index]['bundleSha256']=entry['bundleSha256']
                (queue/'queue'/entry['bundleFile']).write_bytes(wire)
            manifest=dict(requests=entries,coverage=[o['sealedCoverage'] for o in owners],
                          sizing=dict(maxSelectedTextBytes=10,maxEnvelopeBytes=1000000))
            (queue/'queue-manifest.json').write_bytes(f.canonical(manifest))
            corpus=repo/f.CORPUS;corpus.parent.mkdir(parents=True);corpus.write_text(json.dumps({'pages':sources}))
            verification=dict(persistedSourcePins={str(f.CORPUS):f.file_hash(corpus)},
                              inputHashes={'queue-manifest.json':f.file_hash(queue/'queue-manifest.json')})
            (reports/'verification.json').write_text(json.dumps(verification))
            for name,values in [('family-owner',owners),('requests',requests)]:
                (reports/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in values))
            before={p:p.read_bytes() for p in repo.rglob('*') if p.is_file()}
            # The unchanged shared bundle verifier is independently accepted; no contract construction here.
            with patch.object(f,'checked_prepared') as check:
                pages,summary=f.analyze(repo,reports,queue,len,{'available':True,'encoding':'synthetic'})
                self.assertEqual(check.call_count,3)
            self.assertEqual(summary['reconciliation']['pagesWithoutRequests'],1)
            self.assertEqual(len(summary['potentialMechanicalSplitPages']),3)
            self.assertEqual(pages[0]['completeRequestApproximation']['baselineBasis'],'all-Hub observed baseline range')
            self.assertEqual([p['pageKey'] for p in pages],['a','b','c'])
            self.assertEqual({p:p.read_bytes() for p in before},before)
            (queue/'queue/0.json').write_text('{}')
            with patch.object(f,'checked_prepared'),self.assertRaisesRegex(ValueError,'PERSISTED_BUNDLE_HASH_DRIFT'):
                f.analyze(repo,reports,queue)


if __name__=='__main__':
    unittest.main()
