"""Synthetic T1/T2 tests for datasets deterministic offline replay."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.datasets import offline_pipeline as pipeline
from src.extraction.llm.datasets import request_contract as contract
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH


class OfflineReplayTests(unittest.TestCase):
    """Verify stage isolation, exact provenance and immutable offline reports."""

    def setUp(self):
        """Freeze synthetic abstract and unselected README source results."""
        from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units
        self.owner, self.quote, self.other_quote = "hs:one", "The café 🌊 tool is used.", "An alternative tool is used."
        provenance = {"snapshotID": "snapshot", "sourceVersion": "v1"}
        abstract = build_abstract_source_unit({"resource_id": self.owner, "abstract": self.quote},
            accepted_owner_id=self.owner, provenance=provenance)
        readme = read_readme_source_units({"resource_id": self.owner, "source_path": "README.txt", "text": self.other_quote},
            accepted_owner_id=self.owner, provenance={**provenance, "sourceVerified": True})
        self.uid, self.other_uid = abstract["unit"].source_unit_id, readme["sourceUnits"][0]["sourceUnitID"]
        self.inputs = {"accepted_owner_id": self.owner, "trusted_provenance": provenance, "abstract_results": [abstract],
            "readme_results": [readme], "selected_unit_ids": [self.uid], "input_complete": True}

    def payload(self):
        """Create independently supported Tool and owner-to-Tool proposals."""
        evidence = [{"sourceUnitID": self.uid, "evidenceText": self.quote}]
        return {"schemaVersion": contract.RESPONSE_VERSION, "candidateNodes": [
            {"candidateID": "tool", "inventoryId": "A-DOM02", "class": "Tool", "label": "Tool",
             "evidence": deepcopy(evidence)}], "candidateEdges": [
            {"candidateID": "edge", "inventoryId": "C-D18", "relation": "usesTool",
             "source": {"referenceType": "accepted_endpoint", "referenceID": self.owner},
             "target": {"referenceType": "candidate_node", "referenceID": "tool"}, "evidence": deepcopy(evidence)}],
             "abstentions": []}

    def replay(self, payload=None, raw=None, **changes):
        """Replay synthetic bytes without modifying caller-owned source records."""
        data = json.dumps(self.payload() if payload is None else payload, ensure_ascii=False).encode() if raw is None else raw
        return pipeline.replay_recorded_response(data, request_inputs={**self.inputs, **changes})

    def records(self, report):
        """Index only final replay dispositions, not untrusted response fields."""
        return {r["candidateID"]: r for r in report.to_record()["finalRecords"]}

    def test_roundtrip_hashes_and_frozen_report(self):
        """Bind exact bytes, immutable source identity and all stage records."""
        before = deepcopy(self.inputs)
        raw = (' \n' + json.dumps(self.payload(), ensure_ascii=False, indent=2) + '\n').encode()
        request = contract.build_request(**self.inputs)
        report = pipeline.replay_recorded_response(raw, request_inputs=self.inputs,
            expected_request_sha256=request["requestSha256"])
        result = report.to_record()
        self.assertEqual(result["status"], "replay_completed")
        self.assertEqual(result["requestSha256"], request["requestSha256"])
        self.assertEqual(result["responseSha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(report.response_bytes, raw)
        self.assertEqual(result["parseResult"]["originalResponse"], raw)
        self.assertEqual(result["sourceSnapshot"]["selectedSourceUnitIDs"], [self.uid])
        self.assertEqual([r["finalDisposition"] for r in result["finalRecords"]], ["validated", "validated"])
        self.assertEqual(report.report_sha256, hashlib.sha256(report.report_json.encode()).hexdigest())
        self.assertEqual(report, pipeline.replay_recorded_response(raw, request_inputs=self.inputs,
            expected_request_sha256=request["requestSha256"]))
        self.assertEqual(before, self.inputs)
        self.assertFalse(result["kgAuthorization"])
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        result["finalRecords"][0]["originalCandidate"]["label"] = "changed view"
        result["requestResult"]["request"]["sourceUnits"][0]["text"] = "changed view"
        self.assertEqual(report.to_record()["finalRecords"][0]["originalCandidate"]["label"], "Tool")
        with self.assertRaises(FrozenInstanceError):
            report.report_json = "mutation"
        bound = report.to_record()["finalRecords"][0]["validationRecord"]["boundEvidence"][0]
        self.assertEqual(bound["evidenceText"], self.quote)
        self.assertEqual(bound["authorityTextSha256"], request["request"]["sourceUnits"][0]["authorityTextSha256"])

    def test_local_parse_failure_and_actual_dependents(self):
        """Quarantine original invalid rows; independent assertions survive."""
        payload = self.payload()
        bad = deepcopy(payload["candidateNodes"][0])
        bad.update(candidateID="bad", providerMetadata={"id": "forged"}, gates={"accepted": True})
        payload["candidateNodes"].append(bad)
        edge = deepcopy(payload["candidateEdges"][0])
        edge.update(candidateID="dependent", target={"referenceType": "candidate_node", "referenceID": "bad"})
        payload["candidateEdges"].append(edge)
        before = deepcopy(payload)
        report = self.replay(payload)
        records = self.records(report)
        self.assertEqual(records["bad"]["finalDisposition"], "rejected_invalid_assertion")
        self.assertIsNone(records["bad"]["validationRecord"])
        self.assertNotIn(records["dependent"]["finalDisposition"], {"validated", "suppressed_duplicate"})
        self.assertEqual(records["tool"]["finalDisposition"], "validated")
        self.assertEqual(records["edge"]["finalDisposition"], "validated")
        self.assertEqual(records["bad"]["originalCandidate"], bad)
        self.assertEqual(report.to_record()["parseResult"]["originalParsedResponse"], before)
        self.assertEqual(payload, before)
        self.assertNotIn("bad", [r["candidateID"] for r in report.to_record()["validationPayload"]["candidateNodes"]])

    def test_selected_unit_boundary_and_validation_failure_isolation(self):
        """A larger trusted reader cannot authorize unselected evidence."""
        payload = self.payload()
        bad = deepcopy(payload["candidateNodes"][0])
        bad.update(candidateID="outside", evidence=[{"sourceUnitID": self.other_uid, "evidenceText": self.other_quote}])
        payload["candidateNodes"].append(bad)
        parsed = contract.parse_recorded_response(json.dumps(payload), request=contract.build_request(**self.inputs))
        self.assertEqual(parsed["candidateRecords"][1]["parseDisposition"], "local_candidate_error")
        records = self.records(self.replay(payload))
        self.assertEqual(records["outside"]["finalDisposition"], "rejected_invalid_assertion")
        self.assertIsNone(records["outside"]["validationRecord"])
        self.assertEqual(records["tool"]["finalDisposition"], "validated")
        # A separate adapter boundary is enforced even if a parser ever regresses.
        parsed["candidateRecords"][1].update(parseDisposition="pending_validation", diagnostics=[])
        with patch.object(pipeline, "parse_recorded_response", return_value=parsed):
            self.assertEqual(self.records(self.replay(payload))["outside"]["finalDisposition"], "rejected_invalid_assertion")
        payload["candidateNodes"][1]["evidence"] = [{"sourceUnitID": self.uid, "evidenceText": "fabricated literal"}]
        edge = deepcopy(payload["candidateEdges"][0])
        edge.update(candidateID="dependent", target={"referenceType": "candidate_node", "referenceID": "outside"})
        payload["candidateEdges"].append(edge)
        records = self.records(self.replay(payload))
        self.assertEqual(records["outside"]["finalDisposition"], "failed_source_or_evidence_binding")
        self.assertNotEqual(records["dependent"]["finalDisposition"], "validated")
        self.assertEqual(records["edge"]["finalDisposition"], "validated")

    def test_empty_abstentions_incomplete_and_processing_failures(self):
        """Source failures and empty output never become semantic abstention."""
        payload = self.payload()
        payload.update(candidateNodes=[], candidateEdges=[])
        report = self.replay(payload, input_complete=False).to_record()
        self.assertEqual(report["status"], "replay_completed")
        self.assertFalse(report["sourceCompleteness"]["inputComplete"])
        self.assertEqual(report["abstentionRecords"], [])
        payload["abstentions"] = [{"abstentionID": "absent", "inventoryId": "A-DOM02", "sourceUnitIDs": [self.uid],
            "disposition": "abstained_no_evidence", "reason": "No admissible evidence claimed"}]
        report = self.replay(payload, input_complete=False).to_record()
        self.assertEqual(report["abstentionRecords"][0]["finalDisposition"], "rejected_invalid_assertion")
        self.assertEqual(report["abstentionRecords"][0]["originalAbstention"], payload["abstentions"][0])
        payload["abstentions"][0]["disposition"] = "abstained_ambiguous_semantics"
        self.assertEqual(self.replay(payload).to_record()["abstentionRecords"][0]["finalDisposition"], "recorded_claim_pending_validation")
        for raw in (b'{', b'\xff', '{"candidateNodes": []}'):
            report = self.replay(raw=raw).to_record()
            self.assertEqual(report["status"], "processing_failed")
            self.assertIsNone(report["validationResult"])
            self.assertEqual(report["parseResult"]["originalResponse"], raw)
        raw = json.dumps(self.payload()).encode()
        report = pipeline.replay_recorded_response(raw, request_inputs=self.inputs, expected_request_sha256="0" * 64).to_record()
        self.assertEqual(report["requestAssociation"], "digest_mismatch")
        self.assertIsNone(report["validationResult"])
        report = self.replay(selected_unit_ids=["missing"]).to_record()
        self.assertEqual(report["status"], "processing_failed")
        self.assertTrue(report["sourceDiagnostics"])
        self.assertEqual(report["abstentionRecords"], [])

    def test_duplicate_decisions_and_zero_external_effects(self):
        """Preserve duplicate decisions/citations without touching external systems."""
        payload = self.payload()
        duplicate = deepcopy(payload["candidateEdges"][0])
        duplicate["candidateID"] = "duplicate"
        payload["candidateEdges"].append(duplicate)
        original_open = io.open

        def ontology_only(file, mode="r", *args, **kwargs):
            """Permit only the frozen ontology declaration read."""
            self.assertEqual(Path(file).resolve(), ONTOLOGY_PATH.resolve())
            self.assertNotIn("w", mode)
            return original_open(file, mode, *args, **kwargs)

        with patch("io.open", side_effect=ontology_only), patch("builtins.open", side_effect=AssertionError("IO")), patch("socket.socket", side_effect=AssertionError("provider")):
            records = self.records(self.replay(payload))
        self.assertEqual(records["duplicate"]["finalDisposition"], "suppressed_duplicate")
        self.assertTrue(records["duplicate"]["validationRecord"]["boundEvidence"])
        self.assertEqual(records["duplicate"]["validationRecord"]["duplicateOf"], ["edge"])
        self.assertFalse(records["duplicate"]["kgAuthorization"])

    def test_distinct_endpoint_stub_mapping_and_incomplete_read(self):
        """Keep trusted accepted endpoints and authorized source-local stubs separate."""
        from src.extraction.llm.datasets.source_units import read_readme_source_units
        endpoint = {"endpointID": "accepted-repo", "inventoryId": "A-C01", "class": "Repository"}
        stub = {"endpointID": "stub-repo", "inventoryId": "A-C01", "class": "Repository", "resource_id": self.owner,
            "snapshotID": "snapshot", "sourceVersion": "v1", "authorizationID": "accepted-stage"}
        payload = self.payload()
        payload["candidateNodes"][0].update(inventoryId="A-C01", **{"class": "Repository"},
            endpoint={"referenceType": "authorized_stub", "referenceID": "stub-repo"})
        payload["candidateEdges"][0].update(inventoryId="D-17", relation="generatedBy")
        failed = read_readme_source_units(None, accepted_owner_id=self.owner,
            provenance=self.inputs["trusted_provenance"], required=True)
        report = self.replay(payload, accepted_endpoints=[endpoint], authorized_stubs=[stub], readme_results=[failed]).to_record()
        self.assertEqual(report["status"], "replay_completed")
        self.assertEqual(report["endpointMapping"]["validatorAcceptedEndpoints"], [endpoint])
        self.assertEqual(report["endpointMapping"]["validatorAuthorizedStubs"], [stub])
        self.assertFalse(report["sourceCompleteness"]["inputComplete"])
        self.assertTrue(report["sourceDiagnostics"])
        self.assertEqual(report["finalRecords"][0]["finalDisposition"], "validated")
        self.assertEqual(report["finalRecords"][0]["validationRecord"]["resolvedEndpoint"]["referenceType"], "authorized_stub")
        self.assertEqual(report["finalRecords"][1]["finalDisposition"], "validated")
        self.assertEqual(report["abstentionRecords"], [])
        wrong = deepcopy(payload)
        wrong["candidateNodes"][0]["endpoint"]["referenceType"] = "accepted_endpoint"
        self.assertNotEqual(self.records(self.replay(wrong, authorized_stubs=[stub]))["tool"]["finalDisposition"], "validated")

    def test_accepted_duplicate_and_physical_selected_projection(self):
        """Retain existing assertion IDs and pass only selected units to validation."""
        payload = self.payload()
        endpoint = {"endpointID": "accepted-tool", "inventoryId": "A-DOM02", "class": "Tool"}
        payload["candidateNodes"][0]["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": "accepted-tool"}
        accepted = {"assertionID": "accepted-edge", "inventoryId": "C-D18", "relation": "usesTool",
                    "sourceID": self.owner, "targetID": "accepted-tool"}
        with patch.object(pipeline, "validate_dataset_candidates", wraps=pipeline.validate_dataset_candidates) as validator:
            report = self.replay(payload, accepted_endpoints=[endpoint], accepted_assertions=[accepted])
        projected = [u.source_unit_id for u in validator.call_args.kwargs["abstract_units"]]
        projected += [u["sourceUnitID"] for r in validator.call_args.kwargs["readme_results"] for u in r.get("sourceUnits", [])]
        self.assertEqual(projected, [self.uid])
        record = self.records(report)["edge"]
        self.assertEqual(record["finalDisposition"], "suppressed_duplicate")
        self.assertEqual(record["validationRecord"]["duplicateOf"], ["accepted-edge"])
        self.assertTrue(record["validationRecord"]["boundEvidence"])
        self.assertEqual(report.to_record()["endpointMapping"]["acceptedAssertions"], [accepted])


    def test_parse_invalid_cannot_inherit_downstream_success(self):
        """A permissive literal binder cannot override the recorded-response schema."""
        payload = self.payload()
        bad = deepcopy(payload["candidateNodes"][0])
        bad["candidateID"] = "nullable-anchor"
        bad["evidence"][0]["locatorAnchor"] = None
        # The accepted evidence interface treats an absent/null anchor alike;
        # the stricter response schema requires a nonempty string when supplied.
        downstream = pipeline.validate_dataset_candidates({"candidateNodes": [bad], "candidateEdges": []},
            accepted_owner_id=self.owner, trusted_provenance=self.inputs["trusted_provenance"],
            abstract_units=[self.inputs["abstract_results"][0]["unit"]])
        self.assertEqual(downstream["candidateChecks"][0]["disposition"], "validated")
        payload["candidateNodes"].append(bad)
        records = self.records(self.replay(payload))
        self.assertEqual(records["nullable-anchor"]["finalDisposition"], "rejected_invalid_assertion")
        self.assertIsNone(records["nullable-anchor"]["validationRecord"])
        self.assertEqual(records["nullable-anchor"]["originalCandidate"], bad)
        self.assertEqual(records["tool"]["finalDisposition"], "validated")


    def test_readme_measurement_gate_remains_pending(self):
        """README selection preserves provenance and cannot satisfy semantic gates."""
        from src.extraction.llm.datasets.source_units import read_readme_source_units
        quote = "An observation of 2 m is reported."
        reader = read_readme_source_units({"resource_id": self.owner, "source_path": "README.txt", "text": quote},
            accepted_owner_id=self.owner, provenance={**self.inputs["trusted_provenance"], "sourceVerified": True})
        uid = reader["sourceUnits"][0]["sourceUnitID"]
        payload = self.payload()
        payload["candidateNodes"][0].update(inventoryId="A-D12", label="Observation", **{"class": "Measurement"},
            evidence=[{"sourceUnitID": uid, "evidenceText": quote}])
        payload["candidateEdges"][0].update(inventoryId="C-D17", relation="hasMeasurement",
            evidence=[{"sourceUnitID": uid, "evidenceText": quote}])
        records = self.records(self.replay(payload, readme_results=[reader], selected_unit_ids=[uid]))
        self.assertEqual(records["tool"]["finalDisposition"], "unresolved_condition")
        self.assertNotIn(records["edge"]["finalDisposition"], {"validated", "suppressed_duplicate"})
        self.assertIn("explicit_readme_measurement", records["tool"]["validationRecord"]["targetProfileCheck"]["pendingGates"])
        self.assertEqual(records["tool"]["validationRecord"]["boundEvidence"][0]["sourceField"], "README")
        self.assertFalse(records["tool"]["kgAuthorization"])


if __name__ == "__main__":
    unittest.main()
