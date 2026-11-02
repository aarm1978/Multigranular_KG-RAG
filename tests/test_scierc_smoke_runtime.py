"""Offline-only single-request runtime tests; all transport responses are synthetic."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from http.client import IncompleteRead
from urllib.error import HTTPError
import io

from src.extraction.llm.publications import scierc_external_anchor as a
from src.extraction.llm.publications import scierc_smoke_runtime as r


class SmokeRuntimeTests(unittest.TestCase):
    """Exercise durable runtime transitions without model or network calls."""

    @classmethod
    def setUpClass(cls):
        """Prepare the real first dev source once, gold-free and offline."""
        with patch("socket.socket.connect", side_effect=AssertionError("NETWORK_PROHIBITED")):
            cls.prepared = r.prepare_smoke()

    def setUp(self):
        """Inject source preparation and isolate every synthetic attempt's artifacts."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "smoke"
        self.plan, self.document, self.body = self.prepared
        self.calls = 0
        self.prepare_patch = patch.object(r, "prepare_smoke", return_value=self.prepared)
        self.prepare_patch.start(); self.addCleanup(self.prepare_patch.stop)
        guard = patch("socket.socket.connect", side_effect=AssertionError("NETWORK_PROHIBITED"))
        guard.start(); self.addCleanup(guard.stop)
        binding = r.approval_binding(self.plan, self.root)
        self.acceptance = {"kind": "runtime_acceptance", "recordID": "TEST-ONLY-ACCEPTANCE", "approved": True, "binding": binding}
        self.authorization = {"kind": "live_authorization", "recordID": "TEST-ONLY-AUTHORIZATION", "approved": True,
                              "binding": binding, "acceptanceRecordID": "TEST-ONLY-ACCEPTANCE"}

    def response(self, text=None):
        """Return a synthetic completed provider object with full usage details."""
        if text is None:
            text = json.dumps({"documentID": self.document.document_id, "entities": [], "relations": []})
        return {"id": "resp_fixture", "model": "gpt-5.6-sol", "status": "completed", "error": None,
                "incomplete_details": None, "created_at": 1, "completed_at": 2,
                "usage": {"input_tokens": 100, "output_tokens": 25, "total_tokens": 125,
                          "input_tokens_details": {"cached_tokens": 20}, "output_tokens_details": {"reasoning_tokens": 10}},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}

    def transport(self, response, http_status=200):
        """Return a fixture transport that verifies exact bytes and pre-send artifacts."""
        def send(key, body, timeout):
            """Observe the body once without external transport."""
            self.calls += 1
            self.assertEqual(body, self.body)
            self.assertEqual(body, a.canonical_json(a.build_request_body(self.document)))
            self.assertEqual(json.loads(body)["text"]["format"]["name"], "scierc_native_payload")
            self.assertEqual(timeout, 180)
            self.assertTrue((self.root / "dispatch_started.json").exists())
            self.assertEqual((self.root / "provider_request.json").read_bytes(), body)
            return r.TransportReply(response if isinstance(response, bytes) else a.canonical_json(response), http_status, "req_fixture")
        return send

    def execute(self, transport, **kwargs):
        """Execute only with test-only approvals and injected transport."""
        return r.execute_smoke(self.plan, acceptance=self.acceptance, authorization=self.authorization,
                               api_key="fixture-secret-123", root=self.root, transport=transport, **kwargs)

    def test_valid_exact_body_full_provenance_and_restart(self):
        """Successful synthetic completion preserves bytes/usage and blocks every resend."""
        response = self.response()
        result = self.execute(self.transport(response))
        self.assertEqual(result["terminalStatus"], "completed_valid")
        self.assertEqual(result["usage"], response["usage"])
        self.assertEqual(result["usage"]["output_tokens"], 25)
        self.assertEqual(result["providerRequestID"], "req_fixture")
        self.assertEqual((self.root / "provider_response.bin").read_bytes(), a.canonical_json(response))
        self.assertEqual((self.root / "raw_model_output.bin").read_bytes(), response["output"][0]["content"][0]["text"].encode())
        self.assertTrue(result["startedAt"].endswith("Z")); self.assertGreaterEqual(result["elapsedMilliseconds"], 0)
        with self.assertRaisesRegex(r.SmokeRuntimeError, "NO_REDISPATCH"):
            self.execute(self.transport(response))
        self.assertEqual(self.calls, 1)

    def test_failures_preserve_raw_evidence(self):
        """JSON, schema, refusal, incomplete and model failures remain explicit."""
        cases = [(b"not json", "provider_json_invalid"), (self.response("{bad"), "model_json_invalid"),
                 (self.response('{}'), "prediction_invalid")]
        refusal = self.response(); refusal["output"][0]["content"] = [{"type": "refusal", "refusal": "fixture refusal"}]
        incomplete = self.response("{partial"); incomplete.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        wrong = self.response(); wrong["model"] = "different-model"
        error = self.response(); error["error"] = {"code": "fixture_error"}
        cases += [(refusal, "refusal_or_missing_output"), (incomplete, "incomplete_or_failed_response"),
                  (wrong, "returned_model_mismatch"), (error, "provider_error")]
        for i, (response, status) in enumerate(cases):
            with self.subTest(status=status):
                self.root = Path(self.temp.name) / str(i)
                binding = r.approval_binding(self.plan, self.root)
                self.acceptance["binding"] = binding; self.authorization["binding"] = binding
                result = self.execute(self.transport(response))
                self.assertEqual(result["terminalStatus"], status)
                self.assertTrue((self.root / "provider_response.bin").exists())
                if status == "incomplete_or_failed_response":
                    self.assertEqual((self.root / "raw_model_output.bin").read_bytes(), b"{partial")

    def test_invalid_spans_and_endpoints(self):
        """No prediction repair or record dropping occurs on structural failures."""
        for index, prediction in enumerate([
            {"documentID": self.document.document_id, "entities": [{"entityID": "e1", "entityType": "Method",
                "spanStart": 999999, "spanEnd": 999999, "mentionText": "fixture"}], "relations": []},
            {"documentID": self.document.document_id, "entities": [], "relations": [{"relationID": "r1", "relationType": "USED-FOR",
                "sourceEntityID": "missing", "targetEntityID": "missing"}]}]):
            self.root = Path(self.temp.name) / str(index)
            self.acceptance["binding"] = r.approval_binding(self.plan, self.root)
            self.authorization["binding"] = r.approval_binding(self.plan, self.root)
            result = self.execute(self.transport(self.response(json.dumps(prediction))))
            self.assertEqual(result["terminalStatus"], "prediction_invalid")
            self.assertFalse((self.root / "validated_prediction.json").exists())

    def test_unknown_transport_delivery_and_partial_evidence(self):
        """Timeout/partial response cannot authorize a second POST."""
        for i, exception in enumerate([TimeoutError("fixture-secret-123"), r.PartialTransportFailure(b'{"partial":')]):
            self.root = Path(self.temp.name) / str(i)
            self.acceptance["binding"] = r.approval_binding(self.plan, self.root)
            self.authorization["binding"] = r.approval_binding(self.plan, self.root)
            def fail(*args):
                """Raise a local synthetic transport failure."""
                self.calls += 1
                raise exception
            result = self.execute(fail)
            self.assertEqual(result["delivery"], "unknown")
            self.assertEqual(result["terminalStatus"], "transport_failure")
            self.assertNotIn("fixture-secret-123", (self.root / "terminal.json").read_text())
            if i:
                self.assertEqual((self.root / "partial_provider_response.bin").read_bytes(), b'{"partial":')
            with self.assertRaisesRegex(r.SmokeRuntimeError, "NO_REDISPATCH"):
                self.execute(fail)
        self.assertEqual(self.calls, 2)

    def test_http_failure_is_distinct_from_unknown_delivery(self):
        """HTTP failure is observed while remote processing is not guessed."""
        result = self.execute(self.transport({"error": {"code": "fixture"}}, 429))
        self.assertEqual(result["terminalStatus"], "http_failure")
        self.assertEqual(result["delivery"], "http_response_received")
        self.assertEqual(result["httpStatus"], 429)

    def test_missing_mismatched_and_unlinked_authorization(self):
        """Neither acceptance alone nor a different scope can dispatch."""
        for acceptance, authorization in [(None, None), (self.acceptance, None), (None, self.authorization)]:
            with self.assertRaises(r.SmokeRuntimeError):
                r.execute_smoke(self.plan, acceptance=acceptance, authorization=authorization,
                    api_key="fixture", root=self.root, transport=self.transport(self.response()))
        bad = deepcopy(self.authorization); bad["binding"]["maxGenerationPosts"] = 2
        with self.assertRaises(r.SmokeRuntimeError):
            r.check_approvals(self.plan, self.root, self.acceptance, bad)
        bad = deepcopy(self.authorization); bad["acceptanceRecordID"] = "wrong"
        with self.assertRaises(r.SmokeRuntimeError):
            r.check_approvals(self.plan, self.root, self.acceptance, bad)
        self.assertEqual(self.calls, 0); self.assertFalse(self.root.exists())

    def test_test_split_document_and_plan_cannot_enter_smoke(self):
        """Changing either scope or document fails before approval/transport."""
        for field, value in [("split", "test"), ("documentID", "synthetic-test-doc"), ("scope", "official_test")]:
            altered = {**self.plan, field: value}
            with self.assertRaisesRegex(r.SmokeRuntimeError, "IDENTITY_MISMATCH"):
                r.execute_smoke(altered, root=self.root, transport=self.transport(self.response()))
        self.assertEqual(self.calls, 0)

    def test_artifact_conflict_and_interrupted_nonterminal_state(self):
        """Existing artifacts and process death leave a durable no-resend claim."""
        self.root.mkdir(); (self.root / "provider_request.json").write_bytes(b"existing")
        with self.assertRaisesRegex(r.SmokeRuntimeError, "NO_REDISPATCH"):
            self.execute(self.transport(self.response()))
        self.assertEqual((self.root / "provider_request.json").read_bytes(), b"existing")
        self.root = Path(self.temp.name) / "interrupted"
        self.acceptance["binding"] = r.approval_binding(self.plan, self.root)
        self.authorization["binding"] = r.approval_binding(self.plan, self.root)
        def interrupt(*args):
            """Simulate process interruption after durable start, before response."""
            self.calls += 1
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.execute(interrupt)
        self.assertTrue((self.root / "dispatch_started.json").exists())
        self.assertFalse((self.root / "terminal.json").exists())
        with self.assertRaisesRegex(r.SmokeRuntimeError, "NO_REDISPATCH"):
            self.execute(self.transport(self.response()))
        self.assertEqual(self.calls, 1)

    def test_preservation_precedes_validation(self):
        """Raw evidence is durable before any prediction validation executes."""
        def validate(*args):
            """Inspect artifacts at the boundary, without evaluating semantics."""
            self.assertTrue((self.root / "raw_model_output.bin").exists())
            self.assertTrue((self.root / "provider_response.json").exists())
        with patch.object(a, "validate_prediction", side_effect=validate):
            self.assertEqual(self.execute(self.transport(self.response()))["terminalStatus"], "completed_valid")

    def test_plan_selection_and_gold_isolation(self):
        """Plan denotes only dev line one and retains unknown real accounting."""
        self.assertEqual(self.document.document_id, "ICCV_2003_158_abs")
        self.assertEqual(self.document.gold_entities, ())
        self.assertEqual(self.document.gold_relations, ())
        self.assertEqual(self.plan["plannedSmokeGenerationPosts"], 1)
        self.assertEqual(self.plan["separateOfficialTestLogicalRequests"], 100)
        self.assertFalse(self.plan["researcherLiveAuthorization"])
        self.assertIsNone(self.plan["accounting"]["observedUsage"])

    def test_exact_http_primitive_no_rebuild_redirect_or_retry(self):
        """Mock the HTTP opener itself to verify the exact outbound POST and timeout."""
        from unittest.mock import MagicMock
        opener = MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.read.return_value = b'{"fixture":true}'
        response.status = 200
        response.headers = {"x-request-id": "fixture-http-id"}
        with patch("urllib.request.build_opener", return_value=opener) as build:
            result = r.exact_post("fixture-secret", self.body, 180)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.data, self.body)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 180})
        self.assertEqual(opener.open.call_count, 1)
        redirect_handler = build.call_args.args[0]
        self.assertIsNone(redirect_handler.redirect_request(None, None, 307, "", {}, "https://example.invalid"))
        self.assertEqual(result.request_id, "fixture-http-id")
        opener.reset_mock()
        opener.open.side_effect = HTTPError("fixture", 429, "fixture error", {"x-request-id": "error-id"}, io.BytesIO(b'{"error":true}'))
        with patch("urllib.request.build_opener", return_value=opener):
            result = r.exact_post("fixture-secret", self.body, 180)
        self.assertEqual(result.http_status, 429)
        self.assertEqual(result.body, b'{"error":true}')
        self.assertEqual(opener.open.call_count, 1)

    def test_partial_http_read_retains_available_header_identity(self):
        """A partial HTTP body keeps observed status and request ID without retry."""
        from unittest.mock import MagicMock
        opener = MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status = 200; response.headers = {"x-request-id": "partial-id"}
        response.read.side_effect = IncompleteRead(b"partial", 100)
        with patch("urllib.request.build_opener", return_value=opener), self.assertRaises(r.PartialTransportFailure) as caught:
            r.exact_post("fixture-secret", self.body, 180)
        self.assertEqual(caught.exception.partial, b"partial")
        self.assertEqual(caught.exception.request_id, "partial-id")
        self.assertEqual(caught.exception.http_status, 200)
        self.assertEqual(opener.open.call_count, 1)

    def test_credential_echo_is_explicitly_redacted(self):
        """Failure evidence never persists a supplied credential or exception message."""
        response = self.response(); response["error"] = {"message": "fixture-secret-123"}
        result = self.execute(self.transport(response))
        self.assertTrue(result["credentialEchoRedacted"])
        for path in self.root.iterdir():
            self.assertNotIn(b"fixture-secret-123", path.read_bytes())

    def test_exclusive_writes_reject_overwrite(self):
        """Conflicting evidence files remain byte-identical."""
        path = Path(self.temp.name) / "evidence"
        r._write_new(path, b"first")
        with self.assertRaises(FileExistsError):
            r._write_new(path, b"replacement")
        self.assertEqual(path.read_bytes(), b"first")
