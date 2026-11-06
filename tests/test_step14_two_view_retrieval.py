"""Quick offline contracts for two-view nomination; no embeddings or identities inferred."""
from copy import deepcopy
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.evaluation import step14_two_view_retrieval as r
from test_step14_embedding_preflight import occurrence, SPEC


class TwoViewTests(unittest.TestCase):
    """Protect frozen provenance, bounded retrieval and fail-closed dispatch recovery."""

    def setUp(self):
        """Block networking even for mocked provider-execution tests."""
        for method in ('connect','connect_ex'):
            p = patch.object(socket.socket,method,side_effect=AssertionError('NO_NETWORK'))
            p.start(); self.addCleanup(p.stop)

    def project(self, row):
        """Use the existing occurrence schema and synthetic ontology."""
        return r.project(row,7,SPEC)

    def test_exact_windows_and_original_provenance(self):
        """Offsets select exact original text and hash the full original evidence."""
        row = occurrence('a',quote='x'*800+' tool is documented here '+ 'y'*800)
        row['evidenceReferences'][0].update(sourceUnitID='unit',startOffsetInDocument=100,evidenceHash='original')
        row['nativeReferences']=[dict(source='native',hash='original')]
        before = deepcopy(row); result = self.project(row); chosen = result['selectedEvidence'][0]
        quote = row['evidenceReferences'][0]['evidenceText']
        self.assertEqual(chosen['literalExcerpt'],quote[chosen['quoteStart']:chosen['quoteEnd']])
        self.assertIn('tool',chosen['literalExcerpt']); self.assertEqual(len(chosen['literalExcerpt']),600)
        self.assertEqual(chosen['reference']['evidenceRecordSha256'],r.candidates.token(row['evidenceReferences'][0]))
        self.assertEqual(result['originalReference']['recordSha256'],r.candidates.token(row))
        self.assertEqual(row,before)
        self.assertEqual(result,self.project(deepcopy(row)))
        self.assertIsNone(result['identityDecision']); self.assertFalse(result['automaticMergeEligible'])

    def test_label_priority_multiple_labels_and_no_generated_descriptions(self):
        """Original aliases survive; label-containing evidence precedes fallback."""
        row = occurrence('a',quote='unrelated context',description='DO NOT EMBED GENERATED DESCRIPTION')
        row['labels']=['Tool alias','tool','tool']
        row['evidenceReferences'].append(dict(evidenceText='TOOL is a documented computational application.'))
        result=self.project(row)
        self.assertEqual(result['texts']['name'],'Tool\nTool alias\ntool')
        self.assertTrue(result['selectedEvidence'][0]['labelPresent'])
        self.assertNotIn('DO NOT EMBED',result['texts']['evidence'])
        self.assertIn('multiple_original_labels_requires_review',result['flags'])

    def test_missing_weak_abstract_and_class_flags(self):
        """Weak text is flagged; absent source/class/evidence eligibility is held."""
        weak=self.project(occurrence('w',quote='A method is discussed without naming it.'))
        self.assertTrue(weak['eligible']); self.assertIn('weak_context_no_literal_label_match',weak['flags'])
        for field,value in [('evidenceReferences',[]),('sourceArtifacts',[]),('labels',[]),('inventoryId','wrong'),('preparationFlags',['missing_provenance'])]:
            row=occurrence('a');row[field]=value
            with self.subTest(field=field):self.assertFalse(self.project(row)['eligible'])
        row=occurrence('a');row['ontologyClass']='ComputationalModel';row['inventoryId']='C'
        self.assertIn('incompatible_or_abstract_class',self.project(row)['holds'])
        row=occurrence('a');row['snapshotRecordSha256']='bad'
        with self.assertRaisesRegex(ValueError,'SNAPSHOT_HASH_DRIFT'):self.project(row)

    def test_unicode_offsets_and_oversize_name_hold(self):
        """Case matching does not mutate Unicode coordinates or truncate labels."""
        row=occurrence('a',label='Straße',quote='İ'*800+' Straße '+ 'z'*800)
        result=self.project(row);piece=result['selectedEvidence'][0]
        self.assertIn('Straße',piece['literalExcerpt'])
        self.assertEqual(piece['literalExcerpt'],row['evidenceReferences'][0]['evidenceText'][piece['quoteStart']:piece['quoteEnd']])
        row['labels']=['😀'*3000]
        result=self.project(row)
        self.assertIn('input_exceeds_conservative_8191_byte_limit',result['holds'])
        self.assertIn(row['labels'][0],result['texts']['name'])

    def test_scopes_and_version_flags_do_not_approve(self):
        """All three scopes and version conflicts remain nomination metadata."""
        a=self.project(occurrence('a'));b=self.project(occurrence('b'))
        self.assertEqual(r.pair_scope(a,b),r.SCOPES[1])
        b['sourceFamilies']=['hydroshare'];self.assertEqual(r.pair_scope(a,b),r.SCOPES[2])
        b['sourceArtifacts']=a['sourceArtifacts'];self.assertEqual(r.pair_scope(a,b),r.SCOPES[0])
        b['ontologyClass']='Algorithm';self.assertIsNone(r.pair_scope(a,b))
        self.assertIsNone(r.pair_scope(a,a))
        a['versions']={'version':'1'};b['versions']={'version':'2'}
        self.assertIn('structured_versions_differ_no_automatic_identity',r.pair_flags(a,b))

    def test_preview_includes_weak_missing_and_versioned(self):
        """Deterministic diagnostic strata take precedence over arbitrary easy cases."""
        values=[self.project(occurrence('a',quote='')),self.project(occurrence('b',quote='weak'))]
        versioned=occurrence('v',quote='tool version one');versioned['versions']={'version':'1'}
        values.append(self.project(versioned))
        self.assertEqual(r.preview_select(values),r.preview_select(values[::-1]))
        self.assertEqual(len(r.preview_select(values)),3)

    def test_prepare_deduplication_immutable_and_hash_checks(self):
        """One payload has many postings; original inventory and provenance stay intact."""
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); source=base/'source';source.mkdir()
            original=[occurrence('a',quote='tool'),occurrence('b','publications',quote='tool')]
            raw=b''.join(r.identity.encoded(x)+b'\n' for x in original)
            (source/'occurrences.jsonl').write_bytes(raw)
            r.write(source/'manifest.json',dict(coverage={'preparedOccurrences':2}))
            pins={str(source/'occurrences.jsonl'):r.identity.sha(source/'occurrences.jsonl')}
            output=base/'prepared'
            with patch.object(r,'ROOT',base),patch.object(r.preflight.review,'INPUT',source),patch.object(r,'verified_inputs',return_value=(pins,SPEC)):
                summary=r.prepare(output)
                self.assertEqual(summary['eligible'],2)
                self.assertEqual(len(list(r.rows(output/'inputs.jsonl'))),2)
                manifest,inputs,records=r.verify_prepared(output)
                self.assertEqual(len(records),2)
                self.assertEqual(records[0]['textHashes'],records[1]['textHashes'])
                self.assertEqual((source/'occurrences.jsonl').read_bytes(),raw)
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):r.prepare(output)
                (source/'occurrences.jsonl').write_bytes(raw+b' ')
                with self.assertRaises(ValueError):r.verify_prepared(output)

    def response(self,count,dimension=r.DIMENSIONS):
        """Build a mock SDK object without importing or constructing a live client."""
        body=dict(model=r.MODEL,data=[dict(index=i,embedding=[1.0]+[0.0]*(dimension-1)) for i in range(count)],usage={'total_tokens':10})
        return SimpleNamespace(model_dump=lambda **kw:deepcopy(body),_request_id='mock-request')

    def test_completed_resume_and_request_configuration(self):
        """A completed receipt reuses exact vectors and makes no second POST."""
        batch=[dict(text='Tool',textSha256=r.digest('Tool'))]; create=Mock(return_value=self.response(1))
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/'batch'
            result=r.execute_batch(folder,batch,'manifest',create)
            self.assertEqual(result,r.execute_batch(folder,batch,'manifest',create))
            self.assertEqual(create.call_count,1)
            self.assertEqual(create.call_args.kwargs,dict(model=r.MODEL,dimensions=3072,encoding_format='float',input=['Tool']))
            self.assertEqual(r.load(folder/'intent.json')['timeoutSeconds'],600)
            self.assertEqual(r.load(folder/'intent.json')['maxRetries'],0)
            with self.assertRaisesRegex(ValueError,'INTENT_BINDING_DRIFT'):r.execute_batch(folder,batch,'other',create)
            (folder/'response.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'RESPONSE_HASH_DRIFT'):r.execute_batch(folder,batch,'manifest',create)

    def test_uncertain_dispatch_blocked_and_error_sanitized(self):
        """Uncertain intents cannot redispatch; messages and sensitive data never persist."""
        create=Mock(side_effect=OSError(32,'SENSITIVE URL AND KEY'))
        batch=[dict(text='Tool',textSha256=r.digest('Tool'))]
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)/'batch'
            with self.assertRaisesRegex(ValueError,'EMBEDDING_STOP'):r.execute_batch(folder,batch,'m',create)
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            with self.assertRaisesRegex(ValueError,'UNCERTAIN_BATCH_STOP'):r.execute_batch(folder,batch,'m',create)
            self.assertEqual(create.call_count,1)
            self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})
            self.assertNotIn('SENSITIVE',str(before));self.assertEqual(r.load(folder/'outcome.json')['errno'],32)

    def test_orphan_receipt_never_dispatches(self):
        """A response without its intent is corruption, not a fresh request."""
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);r.write(folder/'response.json',{'preserved':True});create=Mock()
            with self.assertRaisesRegex(ValueError,'ORPHAN_RECEIPT_STOP'):
                r.execute_batch(folder,[dict(text='Tool',textSha256=r.digest('Tool'))],'m',create)
            create.assert_not_called();self.assertFalse((folder/'intent.json').exists())

    def test_sdk_execution_configuration_without_network(self):
        """The timeout and no-retry settings reach the SDK constructor itself."""
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);r.write(root/'manifest.json',dict(test=True))
            inputs=[dict(text='Tool',textSha256=r.digest('Tool'))]
            client=Mock();client.embeddings.create.return_value=self.response(1)
            context=Mock();context.__enter__=Mock(return_value=client);context.__exit__=Mock(return_value=False)
            constructor=Mock(return_value=context)
            with patch.dict(sys.modules,{'openai':SimpleNamespace(OpenAI=constructor)}),patch.object(r,'verify_prepared',return_value=({},inputs,[])):
                self.assertEqual(r.embed(root,1)['newBatches'],1)
                self.assertEqual(r.embed(root,1)['newBatches'],0)
            self.assertEqual(client.embeddings.create.call_count,1)
            constructor.assert_called_with(timeout=600,max_retries=0,base_url='https://api.openai.com/v1')

    def test_bad_vectors_and_batch_limits(self):
        """Do not accept missing/duplicate indices, nonfinite vectors or empty inputs."""
        response=self.response(2).model_dump();response['data'][1]['index']=0
        with self.assertRaises(ValueError):r.validate_response(response,2)
        response=self.response(1).model_dump();response['data'][0]['embedding'][0]=float('nan')
        with self.assertRaises(ValueError):r.validate_response(response,1)
        many=[dict(text='a'*8000,textSha256='placeholder') for _ in range(70)]
        self.assertEqual([len(b) for b in r.batches(many)],[30,30,10])


class RetrievalTests(unittest.TestCase):
    """Small exhaustive fixtures check scores against the complete pair population."""

    setUp = TwoViewTests.setUp
    project = TwoViewTests.project

    def test_exact_neighbors_scopes_blocks_and_ties(self):
        """Blocked search matches all-target search, includes both view scores."""
        import numpy as np
        data=[self.project(occurrence(str(i),'github' if i<3 else 'hydroshare',label=str(i),quote=str(i)+' context')) for i in range(5)]
        data[1]['sourceArtifacts']=data[0]['sourceArtifacts']
        inputs=sorted({h for row in data for h in row['textHashes'].values()});indices={h:i for i,h in enumerate(inputs)}
        vectors=np.ones((len(inputs),3),dtype=np.float32);vectors/=np.linalg.norm(vectors,axis=1,keepdims=True)
        small=list(r.neighbors(data,vectors,indices,1,1,2));large=list(r.neighbors(data,vectors,indices,1,20,20))
        self.assertEqual(small,large)
        first=[x for x in small if x['queryID']=='0']
        self.assertEqual([x['poolSize'] for x in first],[1,1,2])
        self.assertEqual([x['candidates'][0]['targetID'] for x in first],['1','2','3'])
        for group in small:
            for result in group['candidates']:
                self.assertEqual(set(result['scores']),{'name','evidence'})
                self.assertIsNone(result['identityDecision']);self.assertFalse(result['automaticMergeEligible'])
        self.assertEqual(sum(g['poolSize'] for g in small),20)
        self.assertEqual(sum(len(g['candidates']) for g in r.neighbors(data,vectors,indices,10,2,3)),20)

    def test_local_receipt_consumption_normalization_and_immutable_outputs(self):
        """Consume only complete pinned mock responses, with no offline redispatch."""
        import numpy as np
        data=[self.project(occurrence(str(i),label=str(i),quote=str(i)+' context')) for i in range(2)]
        before=deepcopy(data)
        payloads={row['textHashes'][v]:row['texts'][v] for row in data for v in r.VIEWS}
        inputs=[dict(textSha256=h,text=t) for h,t in sorted(payloads.items())]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prepared=root/'prepared';prepared.mkdir()
            r.write(prepared/'manifest.json',dict(test=True))
            output=root/'retrieved'
            with patch.object(r,'ROOT',root),patch.object(r,'verify_prepared',return_value=({},inputs,data)):
                with self.assertRaisesRegex(ValueError,'INCOMPLETE_EMBEDDINGS'):
                    r.retrieve(prepared,output,2,1,1)
                self.assertFalse(output.exists())
                for i,batch in enumerate(r.batches(inputs)):
                    body=dict(model=r.MODEL,usage={'total_tokens':1},data=[dict(index=j,embedding=[2.0]+[0.0]*3071) for j in range(len(batch))])
                    create=Mock(return_value=SimpleNamespace(model_dump=lambda **kw:body))
                    r.execute_batch(prepared/'embeddings'/f'batch-{i:06d}',batch,r.identity.sha(prepared/'manifest.json'),create)
                result=r.retrieve(prepared,output,2,1,1)
                self.assertEqual(result['scopes'][r.SCOPES[1]]['directedNominations'],2)
                self.assertTrue(np.allclose(np.linalg.norm(np.load(output/'normalized.npy'),axis=1),1))
                self.assertEqual(list(r.rows(output/'candidates.jsonl'))[0]['scores'],{'name':1.0,'evidence':1.0})
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):r.retrieve(prepared,output,2,1,1)
                self.assertEqual(data,before)

    def test_view_union_keeps_distinct_nominees(self):
        """A strong name match cannot hide a different evidence-view neighbor."""
        import numpy as np
        data=[self.project(occurrence(str(i),label=str(i),quote=str(i)+' context')) for i in range(3)]
        indices={};values=[]
        for i,row in enumerate(data):
            for view in r.VIEWS:
                indices[row['textHashes'][view]]=len(values)
                values.append([1.,0.] if i==0 or (i==1 and view=='name') or (i==2 and view=='evidence') else [0.,1.])
        groups=list(r.neighbors(data,np.array(values),indices,1,1,1))
        chosen=next(x for x in groups if x['queryID']=='0' and x['scope']==r.SCOPES[1])['candidates']
        self.assertEqual([x['nominatedBy'] for x in chosen],[['name'],['evidence']])


if __name__ == '__main__':
    unittest.main()
