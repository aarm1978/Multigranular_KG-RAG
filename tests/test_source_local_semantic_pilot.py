"""One focused native transport integration test; no external calls or corpus runs."""
import base64
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import source_local_semantic_pilot as run
from src.extraction.llm import source_local_semantics as semantic
from test_source_local_semantics import template


class ProspectiveTransportTests(unittest.TestCase):
    """Exercise the new queue binding with existing live and Batch controllers."""
    def test_pinned_queue_native_live_resume_offline_review_and_immutability(self):
        """Use one synthetic request and fake wire response; preserve raw journals on resume."""
        with tempfile.TemporaryDirectory() as temp, patch.object(socket.socket,'connect',side_effect=AssertionError('NO_NETWORK')), patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NO_NETWORK')):
            repo=Path(temp);base=run.BASE;root=repo/base;(root/'queue').mkdir(parents=True)
            prepared=semantic.build([template('github','No semantic claims are stated.')])
            raw=run.canonical(prepared)+b'\n';name=run.digest(raw)+'.json';(root/'queue'/name).write_bytes(raw)
            item,line=run.adapter.batch.input_line(prepared,1,run.adapter.fingerprint)
            (root/'batch-input.jsonl').write_bytes(line)
            parent=dict(version=semantic.VERSION,inputPins={},implementationPins={},requests=[dict(family='github',
                bundleFile=name,bundleSha256=run.digest(raw),identity=run.adapter.fingerprint(prepared),batchItem=item,cost=run.sizing.costs(prepared))],batchInputSha256=run.digest(line))
            wire=run.canonical(parent)+b'\n';(root/'queue-manifest.json').write_bytes(wire);sha=run.digest(wire)
            for mode in ('live','batch'):
                r=run.operate('preflight',mode,sha,repo=repo);self.assertEqual(r['requests'],1)
            self.assertFalse((root/'execution').exists())
            calls=[]
            def call(key,body,save):
                """Return exact synthetic provider bytes through the native journal callback."""
                calls.append(body)
                payload=json.dumps(dict(schemaVersion=semantic.VERSION,candidateNodes=[],candidateEdges=[],abstentions=[]))
                response=dict(id='synthetic-response',model=body['model'],service_tier='default',status='completed',
                    usage={'input_tokens':10,'output_tokens':2},error=None,output=[{'type':'message','content':[{'type':'output_text','text':payload}]}])
                save(dict(kind='response',bytesBase64=base64.b64encode(json.dumps(response).encode()).decode()))
            run.operate('submit','live',sha,repo=repo,live_call=call)
            journal=root/'execution/live/execution.jsonl';before=journal.read_bytes()
            run.operate('submit','live',sha,repo=repo,live_call=call)
            self.assertEqual(len(calls),1);self.assertEqual(journal.read_bytes(),before)
            review=run.review_live(sha,repo=repo);self.assertEqual(review['requests'],1);self.assertEqual(review['acceptedNodes'],0)
            with self.assertRaises(FileExistsError):run.review_live(sha,repo=repo)
            with self.assertRaises(ValueError):run.load_queue(repo,base,'0'*64)
            self.assertEqual(journal.read_bytes(),before)


if __name__=='__main__':unittest.main()
