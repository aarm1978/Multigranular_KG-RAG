"""New sequential orchestration only: synthetic source and injected transport."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import scierc_official_runner as r


class OfficialRunnerTests(unittest.TestCase):
    """Never use an official document or provider in orchestration fixtures."""

    def setUp(self):
        """Create 100 source-only synthetic requests and test-only authorizations."""
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "official"
        self.documents = []
        rows = []
        for index in range(100):
            doc = r.a.parse_processed_document({"doc_key": f"fixture-{index:03d}", "sentences": [["Synthetic", "tokens"]]}, include_gold=False)
            body = r.a.canonical_json(r.a.build_request_body(doc))
            self.documents.append((doc,body))
            rows.append({"documentID": doc.document_id, "providerRequestBodySha256": r.a.sha256_bytes(body)})
        self.candidate = {"manifestSha256": "fixture", "requests": rows}
        prep = patch.object(r,"prepare",return_value=(self.candidate,self.documents)); prep.start(); self.addCleanup(prep.stop)
        guard = patch("socket.socket.connect",side_effect=AssertionError("NETWORK_PROHIBITED")); guard.start(); self.addCleanup(guard.stop)
        binding = r.binding(self.candidate,self.root)
        self.acceptance = {"kind":"runtime_acceptance","approved":True,"recordID":"TEST-ACCEPTANCE","binding":binding}
        self.authorization = {"kind":"live_authorization","approved":True,"recordID":"TEST-AUTHORIZATION","binding":binding,"acceptanceRecordID":"TEST-ACCEPTANCE"}
        self.calls = []; self.progress = io.StringIO()

    def response(self, doc_id, text=None):
        """Construct synthetic provider output, not semantic benchmark predictions."""
        return {"id":"resp_fixture", "model":"gpt-5.6-sol", "status":"completed", "error":None,
                "usage":{"input_tokens":10,"output_tokens":5,"total_tokens":15},
                "output":[{"type":"message","content":[{"type":"output_text", "text":text if text is not None else json.dumps({"documentID":doc_id,"entities":[],"relations":[]})}]}]}

    def transport(self,key,body,timeout):
        """Assert exact outgoing order/body and durable marker before returning bytes."""
        index=len(self.calls); doc,expected=self.documents[index]
        self.assertEqual(body,expected); self.assertEqual(timeout,600)
        self.assertTrue((r.document_root(self.root,doc.document_id)/"dispatch_started.json").exists())
        self.calls.append(doc.document_id)
        return r.s.TransportReply(r.a.canonical_json(self.response(doc.document_id)),200,"req_fixture")

    def execute(self, transport=None):
        """Capture progress while running with test-only credentials and transport."""
        with contextlib.redirect_stdout(self.progress):
            return r.execute(acceptance=self.acceptance,authorization=self.authorization,api_key="test-secret",root=self.root,transport=transport or self.transport)

    def test_success_order_progress_and_restart(self):
        """All 100 complete in order; reopening is report-only with no resend."""
        result=self.execute()
        self.assertTrue(result["allOutputsValid"]); self.assertTrue(result["completedTraversal"])
        self.assertEqual(self.calls,[doc.document_id for doc,_ in self.documents])
        self.assertEqual(len(self.progress.getvalue().splitlines()),200)
        self.assertIn("[100/100] fixture-099 completed_valid",self.progress.getvalue())
        self.assertIn("successful=100 failed=0",self.progress.getvalue())
        saved=(self.root/"summary.json").read_bytes()
        again=self.execute(); self.assertEqual(len(self.calls),100)
        self.assertEqual(again["globalStop"],"EXISTING_STATE_NO_REDISPATCH")
        self.assertEqual(saved,(self.root/"summary.json").read_bytes())

    def test_success_failure_success_continues(self):
        """A malformed model output does not stop unrelated documents or disappear."""
        def send(*args):
            reply=self.transport(*args)
            if len(self.calls)==2:
                return r.s.TransportReply(r.a.canonical_json(self.response(self.calls[-1],"{bad")),200,"req_bad")
            return reply
        result=self.execute(send)
        self.assertEqual(result["counts"],{"successful":99,"failed_uncertain":1,"not_started":0})
        self.assertTrue(result["completedTraversal"]); self.assertFalse(result["allOutputsValid"])
        failure=json.loads((self.root/"failures.jsonl").read_bytes())
        self.assertEqual(failure["documentID"],"fixture-001"); self.assertEqual(failure["failureStage"],"model_json")
        self.assertEqual(failure["providerRequestID"],"req_bad")
        self.assertEqual(result["documents"][2]["classification"],"successful")

    def test_global_authentication_quota_and_contract_stops(self):
        """Shared HTTP blockers stop before the second request, with 99 not started."""
        for status in (400,401,403,429):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                self.root=Path(directory)/"official"; self.calls=[]
                for record in (self.acceptance,self.authorization): record["binding"]=r.binding(self.candidate,self.root)
                def send(*args):
                    self.transport(*args)
                    return r.s.TransportReply(b'{"error":{"code":"fixture"}}',status,"req_error")
                result=self.execute(send)
                self.assertEqual(len(self.calls),1); self.assertEqual(result["counts"]["not_started"],99)
                self.assertEqual(result["globalStop"],"SHARED_PROVIDER_BLOCKER")
                self.assertEqual(len(result["documents"]),100)

    def test_interruption_and_no_redispatch(self):
        """An interrupted durable attempt stays uncertain on restart."""
        def send(*args):
            self.transport(*args)
            raise KeyboardInterrupt()
        result=self.execute(send)
        self.assertEqual(result["counts"],{"successful":0,"failed_uncertain":1,"not_started":99})
        self.assertEqual(result["documents"][0]["delivery"],"unknown")
        self.execute(); self.assertEqual(len(self.calls),1)

    def test_persistence_and_shared_code_stop(self):
        """Persistence and unexpected implementation exceptions never continue dispatch."""
        original=r.s._write_new
        def write(path,data):
            if path.name=="provider_response.bin": raise OSError("fixture disk failure")
            return original(path,data)
        with patch.object(r.s,"_write_new",side_effect=write): result=self.execute()
        self.assertEqual(len(self.calls),1)
        self.assertEqual(result["counts"]["not_started"],99)
        self.assertIn("OSError",result["globalStop"])

    def test_shared_code_failure_preserves_available_metadata(self):
        """Unexpected validator code failure stops while preserving response evidence."""
        with patch.object(r.a,"validate_prediction",side_effect=RuntimeError("fixture shared bug")):
            result=self.execute()
        self.assertEqual(len(self.calls),1)
        self.assertIn("RuntimeError",result["globalStop"])
        self.assertEqual(result["documents"][0]["responseID"],"resp_fixture")
        self.assertEqual(result["documents"][0]["providerRequestID"],"req_fixture")
        self.assertEqual(result["documents"][0]["usage"]["total_tokens"],15)

    def test_model_mismatch_is_shared_contract_stop(self):
        """Returning a different model cannot continue an unchanged official contract."""
        def send(*args):
            self.transport(*args)
            response=self.response(self.calls[-1]); response["model"]="wrong-model"
            return r.s.TransportReply(r.a.canonical_json(response),200,"req_wrong")
        result=self.execute(send)
        self.assertEqual(len(self.calls),1); self.assertEqual(result["globalStop"],"SHARED_PROVIDER_BLOCKER")

    def test_summary_persistence_failure_is_explicit(self):
        """A failed final write cannot report durable success or trigger redispatch."""
        original=r.s._write_new
        def write(path,data):
            if path.name=="summary.json": raise OSError("fixture")
            return original(path,data)
        with patch.object(r.s,"_write_new",side_effect=write): result=self.execute()
        self.assertEqual(result["globalStop"],"SUMMARY_PERSISTENCE_FAILURE")
        self.assertFalse(result["summaryPersisted"])
        self.assertEqual(len(result["documents"]),100)
        self.execute(); self.assertEqual(len(self.calls),100)

    def test_invalid_schema_is_document_local(self):
        """A malformed model schema remains an isolated output defect."""
        def send(*args):
            reply=self.transport(*args)
            if len(self.calls)==2:
                return r.s.TransportReply(r.a.canonical_json(self.response(self.calls[-1],"{}")),200)
            return reply
        result=self.execute(send)
        self.assertEqual(len(self.calls),100)
        self.assertEqual(result["documents"][1]["failureStage"],"prediction_validation")
        self.assertEqual(result["counts"]["successful"],99)

    def test_timeout_isolated_and_no_retry(self):
        """Unknown delivery is preserved but other documents may proceed."""
        def send(*args):
            reply=self.transport(*args)
            if len(self.calls)==2: raise TimeoutError()
            return reply
        result=self.execute(send)
        self.assertEqual(len(self.calls),100); self.assertEqual(result["counts"]["successful"],99)
        self.assertEqual(result["documents"][1]["delivery"],"unknown")

    def test_missing_authorization_and_conflicting_state(self):
        """No approved binding or a conflicting root means zero dispatch."""
        with self.assertRaises(ValueError):
            r.execute(root=self.root,transport=self.transport)
        self.assertFalse(self.root.exists())
        self.root.mkdir()
        with self.assertRaisesRegex(ValueError,"EXISTING_STATE_CONFLICT"): self.execute()
        self.assertEqual(self.calls,[])

    def test_cli_without_execute_has_no_effect(self):
        """Import/default CLI does not load credentials or dispatch."""
        with patch.object(r,"execute") as run, contextlib.redirect_stdout(self.progress): r.main([])
        run.assert_not_called(); self.assertFalse(self.root.exists())

    def test_progress_is_flushed(self):
        """Both before/after progress events explicitly request immediate flushing."""
        with patch("builtins.print") as printer: result=self.execute()
        self.assertTrue(result["completedTraversal"])
        self.assertEqual(printer.call_count,200)
        self.assertTrue(all(call.kwargs.get("flush") is True for call in printer.call_args_list))
