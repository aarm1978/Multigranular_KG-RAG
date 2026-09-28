"""Focused offline canonical lifecycle, isolation, and frozen witness regressions."""
from copy import deepcopy
import inspect
import json
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import publication_semantic_pipeline as pipeline
from src.extraction.llm.publications import production_runner
from src.extraction.llm.publications.canonical_production_replay import DEV_ROOT, require_parity, verify_dev_witnesses
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans


class CanonicalSemanticPipelineTests(unittest.TestCase):
    source = {"text": "alpha beta alpha gamma", "startOffsetInDocument": 40,
              "canonicalArtifactID": "paper:test", "sourceUnitID": "unit:test",
              "textHash": "a" * 64, "sectionID": "section:test", "sectionTitleRaw": "Test"}

    def test_dev09_dev10_frozen_schema013_witness_parity(self):
        """Canonical processing reproduces both frozen authentic witness results."""
        self.assertEqual(verify_dev_witnesses(), {
            "DEV-09": {"parity": True, "usableCandidateCount": 36},
            "DEV-10": {"parity": True, "usableCandidateCount": 22}})

    def test_legacy_metadata_api_preserves_frozen_dev_request_hash_and_content(self):
        """The historical metadata entry point is now a byte-equivalent shared facade."""
        from src.extraction.llm.publications.openai_provider import bind_live_response_metadata
        for dev in ("09", "10"):
            root = DEV_ROOT/f"DEV-{dev}"
            request = json.loads((root/f"publication_full_semantic_dev{dev}_live_request.json").read_text())
            metadata = json.loads((root/f"publication_full_semantic_dev{dev}_provider_metadata.json").read_text())
            self.assertEqual(bind_live_response_metadata(request, metadata, max_output_tokens=32768), request)

    def test_all_four_local_failures_are_isolated_with_exact_rules_unchanged(self):
        """No bad literal/anchor is repaired, and the old binder remains fatal."""
        cases = [("missing", None), ("alpha", None), ("beta", "absent"), ("alpha", "alpha beta alpha gamma")]
        for literal, anchor in cases:
            with self.subTest(literal=literal, anchor=anchor):
                raw = {"evidenceSpans": [{"evidenceSpanID": "bad", "evidenceText": literal, "locatorAnchor": anchor},
                                         {"evidenceSpanID": "good", "evidenceText": "gamma", "locatorAnchor": None}]}
                before = deepcopy(raw)
                bound, binding = bind_evidence_spans(raw, self.source)
                self.assertEqual(binding["bindingStatus"], "failed")
                projected, audit = pipeline.isolate_evidence_failures(bound, binding)
                self.assertEqual([x["evidenceSpanID"] for x in projected["evidenceSpans"]], ["good"])
                self.assertEqual(audit["failedEvidenceSpanIDs"], ["bad"])
                self.assertEqual(audit["bindingFindings"], binding["findings"])
                self.assertEqual(raw, before)

    def test_nested_and_all_record_type_dependencies_are_excluded_without_repair(self):
        """Nested attribute references trigger whole-record exclusion before validation."""
        payload = {"evidenceSpans": [{"evidenceSpanID": "bad", "evidenceText": "absent"}, {"evidenceSpanID": "good", "evidenceText": "beta"}],
                   "candidateNodes": [{"candidateID": "n1", "evidenceSpanIDs": ["good"], "attributes": {"x": {"evidenceSpanIDs": ["bad"]}}}, {"candidateID": "n2", "evidenceSpanIDs": ["good"]}],
                   "candidateEdges": [{"candidateID": "e1", "evidenceSpanIDs": ["bad"]}],
                   "abstentions": [{"abstentionID": "a1", "evidenceSpanIDs": ["bad"]}],
                   "deferredRecords": [{"deferredRecordID": "d1", "evidenceSpanIDs": ["bad"]}]}
        bound, binding = bind_evidence_spans(payload, self.source)
        projected, audit = pipeline.isolate_evidence_failures(bound, binding)
        self.assertEqual(projected["candidateNodes"], [payload["candidateNodes"][1]])
        self.assertEqual(len(audit["excludedRecords"]), 4)
        self.assertEqual(audit["excludedRecords"][0]["failedEvidenceDependencies"][0]["pointer"], "/attributes/x/evidenceSpanIDs/0")

    def test_structural_and_unidentifiable_failures_remain_response_level(self):
        """Duplicate IDs, missing IDs and structural failures cannot be isolated."""
        for spans in ([None], [{"evidenceText": "missing"}], [{"evidenceSpanID": "x", "evidenceText": "missing"}]*2,
                      [{"evidenceSpanID": "x", "evidenceText": ""}]):
            bound, binding = bind_evidence_spans({"evidenceSpans": spans}, self.source)
            self.assertIsNone(pipeline.isolate_evidence_failures(bound, binding))

    def test_parity_gate_detects_semantic_change_but_allows_derived_hash(self):
        """A changed status must block recovery; derived hashes are provenance only."""
        require_parity({"validationResultsHash": "a", "status": "valid"}, {"validationResultsHash": "b", "status": "valid"}, "fixture")
        with self.assertRaisesRegex(ValueError, "parity mismatch"):
            require_parity({"status": "valid"}, {"status": "rejected"}, "fixture")

    def test_empty_isolated_projection_is_processable_and_legacy_mode_is_fatal(self):
        """Empty safe semantics cannot trigger a technical retry under the amendment."""
        request = json.loads((DEV_ROOT/"DEV-09/publication_full_semantic_dev09_live_request.json").read_text())
        raw = json.dumps({"candidateNodes": [], "candidateEdges": [], "abstentions": [], "deferredRecords": [],
                          "evidenceSpans": [{"evidenceSpanID": "evidence-0001", "evidenceText": "UNMATCHABLE_FIXTURE", "locatorAnchor": None}]}).encode()
        result = pipeline.semantic_attempt(raw, request)
        self.assertEqual(result[0]["parseStatus"], "parsed")
        self.assertEqual(result[0]["parsedEnvelope"]["evidenceSpans"], [])
        self.assertEqual(result[3]["candidateNodes"], [])
        legacy = pipeline.semantic_attempt(raw, request, isolate_failures=False)
        self.assertEqual(legacy[0]["processingCode"], "EVIDENCE_BINDING_FAILED")

    def test_nested_dependency_is_removed_before_validator_and_raw_document_is_retained(self):
        """The validator sees safe records only; parsedDocument remains the raw payload."""
        request = json.loads((DEV_ROOT/"DEV-09/publication_full_semantic_dev09_live_request.json").read_text())
        payload = json.loads((DEV_ROOT/"DEV-09/publication_full_semantic_dev09_exact_structured_model_output.json").read_text())
        node = payload["candidateNodes"][0]
        node["attributes"].append({"evidenceSpanIDs": ["evidence-9999"]})
        payload["evidenceSpans"].append({"evidenceSpanID": "evidence-9999", "evidenceText": "UNMATCHABLE_FIXTURE", "locatorAnchor": None})
        raw = json.dumps(payload).encode()
        parser, _, validation, usable = pipeline.semantic_attempt(raw, request)
        self.assertEqual(parser["parsedDocument"], payload)
        self.assertEqual(parser["parseStatus"], "parsed")
        self.assertNotIn(node["candidateID"], [x["recordID"] for x in validation["recordResults"]])
        self.assertEqual(parser["evidenceIsolation"]["excludedRecords"][0]["recordID"], node["candidateID"])
        self.assertEqual(json.loads(raw), payload)

    def test_canonical_cli_cannot_be_combined_with_live_execution(self):
        """Replay is a separate no-call action even when flags are combined."""
        with self.assertRaises(SystemExit), patch.object(production_runner, "execute_live_run", side_effect=AssertionError("must not call")):
            production_runner.main(["--replay-canonical-semantics", "--execute-live"])

    def test_timeout_reconstructed_failure_and_attempt_two_survive_canonical_replay(self):
        """Offline replay must preserve attempt one and the selected authentic retry."""
        from src.extraction.llm.publications.canonical_production_replay import _replay_one
        from src.extraction.llm.publications.step5_freeze_materialization import _inputs
        root = production_runner.DEFAULT_LIVE_ROOT
        manifest = json.loads((root/"publication_c1_run_manifest.json").read_text())
        record = next(x for x in manifest["requests"] if x["requestID"] == "publication-c1-request-9d725039aaeef06d1a46")
        request_root = root/"requests"/record["requestID"]
        before = (request_root/"attempt_selection.json").read_bytes()
        original = json.loads(before)
        inventory, routing = _inputs()
        prepared = production_runner._prepared_request(record["primarySourceUnitID"], inventory, routing)
        with patch("socket.socket.connect", side_effect=AssertionError("no network")):
            artifacts = _replay_one(request_root, record, prepared, original, False)
        selected = artifacts["attempt_selection.json"]
        self.assertEqual(selected["selectedAttemptNumber"], 2)
        self.assertEqual(selected["attempts"][0], original["attempts"][0])
        self.assertEqual(len(selected["attempts"]), 2)
        self.assertEqual(before, (request_root/"attempt_selection.json").read_bytes())

    def test_production_and_schema013_dev_delegate_to_canonical_pipeline(self):
        """Production must not regain its private DEV downstream dependency."""
        from src.extraction.llm.publications.run_publication_full_devset0_node_development import _downstream
        self.assertNotIn("run_publication_full_devset0_node_development", inspect.getsource(production_runner))
        self.assertIn("semantic_pipeline.semantic_attempt", inspect.getsource(production_runner.execute_with_provider_fixture))
        with patch.object(pipeline, "semantic_attempt", return_value="canonical") as call:
            self.assertEqual(_downstream(b"{}", {"authorityBundleID": "publication-semantic-v0.1.5-schema-v0.1.3"}), "canonical")
        call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
