"""Synthetic T1/T2 tests for documents deterministic offline replay."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.documents import offline_pipeline as pipeline
from src.extraction.llm.documents import request_contract as contract
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH


class OfflineReplayTests(unittest.TestCase):
    """Verify stage isolation, exact provenance and immutable offline reports."""

    def setUp(self):
        """Create an in-memory frozen page with an exact accepted Section."""
        from src.extraction.llm.documents.source_units import read_page_source_units
        self.quote, self.other_quote = "The café 🌊 tool is used.", "An alternative tool is used."
        text = "# Guide\n" + self.quote + "\n" + self.other_quote + "\n"
        url = "https://example.test/guide"
        suffix = hashlib.sha256(url.encode()).hexdigest()[:20]
        self.owner = "hub:page:" + suffix
        page = {"page_key": "hub-page:" + url, "canonical_url": url, "corpus_path": "guide.mdx", "source_path": "guide.mdx",
            "source_group": "docs", "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "headings": [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]}
        mapping = {k: page[k] for k in ("page_key", "canonical_url", "content_sha256")}
        mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": "hub:section:" + suffix + ":0001"}]
        reader = read_page_source_units(page, accepted_section_mapping=mapping)
        self.uid = next(u["sourceUnitID"] for u in reader["sourceUnits"] if self.quote in u["text"])
        self.other_uid = next(u["sourceUnitID"] for u in reader["sourceUnits"] if self.other_quote in u["text"])
        self.inputs = {"page": page, "reader_result": reader, "accepted_page_id": self.owner,
            "accepted_section_mapping": mapping, "selected_unit_ids": [self.uid], "input_complete": True}

    def payload(self):
        """Create independently supported Tool and owner-to-Tool proposals."""
        evidence = [{"sourceUnitID": self.uid, "evidenceText": self.quote}]
        return {"schemaVersion": contract.RESPONSE_VERSION, "candidateNodes": [
            {"candidateID": "tool", "inventoryId": "A-DOM02", "class": "Tool", "label": "Tool",
             "evidence": deepcopy(evidence)}], "candidateEdges": [
            {"candidateID": "edge", "inventoryId": "C-DC07", "relation": "describesTool",
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

    def test_parent_path_parse_failure_isolation_and_section_binding(self):
        """A rejected parent edge holds its dependents and leaves a valid Tool intact."""
        payload = self.payload()
        procedure = deepcopy(payload["candidateNodes"][0])
        procedure.update(candidateID="procedure", inventoryId="A-DC05", **{"class": "Procedure"})
        example = deepcopy(procedure)
        example.update(candidateID="example", inventoryId="A-DC08", **{"class": "Example"}, parentPath=[
            {"referenceType": "candidate_edge", "referenceID": "parent"}, {"referenceType": "candidate_edge", "referenceID": "attachment"}])
        parent = deepcopy(payload["candidateEdges"][0])
        parent.update(candidateID="parent", inventoryId="C-DC20", relation="hasProcedure",
            target={"referenceType": "candidate_node", "referenceID": "procedure"})
        attachment = deepcopy(parent)
        attachment.update(candidateID="attachment", inventoryId="C-DC12", relation="hasExample",
            source={"referenceType": "candidate_node", "referenceID": "procedure"},
            target={"referenceType": "candidate_node", "referenceID": "example"})
        payload["candidateNodes"].extend([procedure, example])
        payload["candidateEdges"].extend([parent, attachment])
        records = self.records(self.replay(payload))
        self.assertEqual(records["example"]["finalDisposition"], "unresolved_condition")
        self.assertEqual(records["attachment"]["finalDisposition"], "unresolved_condition")
        self.assertEqual(records["tool"]["validationRecord"]["boundEvidence"][0]["sectionID"],
                         self.inputs["accepted_section_mapping"]["sections"][0]["section_id"])
        parent["sourceMetadata"] = {"page": "forged"}
        records = self.records(self.replay(payload))
        self.assertEqual(records["parent"]["finalDisposition"], "rejected_invalid_assertion")
        self.assertEqual(records["example"]["finalDisposition"], "unresolved_endpoint")
        self.assertEqual(records["attachment"]["finalDisposition"], "unresolved_endpoint")
        self.assertEqual(records["tool"]["finalDisposition"], "validated")
        reader = deepcopy(self.inputs["reader_result"])
        reader["diagnostics"].append({"status": "needs_review", "sourceUnitID": self.other_uid, "reason": "uncertain"})
        report = self.replay(reader_result=reader).to_record()
        self.assertFalse(report["sourceCompleteness"]["inputComplete"])
        self.assertTrue(report["sourceDiagnostics"])
        self.assertEqual(report["finalRecords"][0]["finalDisposition"], "validated")

    def test_accepted_duplicate_and_physical_selected_projection(self):
        """Retain existing assertion IDs and pass only selected units to validation."""
        payload = self.payload()
        endpoint = {"endpointID": "accepted-tool", "inventoryId": "A-DOM02", "class": "Tool"}
        payload["candidateNodes"][0]["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": "accepted-tool"}
        accepted = {"assertionID": "accepted-edge", "inventoryId": "C-DC07", "relation": "describesTool",
                    "sourceID": self.owner, "targetID": "accepted-tool"}
        with patch.object(pipeline, "validate_hub_candidates", wraps=pipeline.validate_hub_candidates) as validator:
            report = self.replay(payload, accepted_endpoints=[endpoint], accepted_assertions=[accepted])
        projected = [u["sourceUnitID"] for u in validator.call_args.args[1]["sourceUnits"]]
        self.assertEqual(projected, [self.uid])
        record = self.records(report)["edge"]
        self.assertEqual(record["finalDisposition"], "suppressed_duplicate")
        self.assertEqual(record["validationRecord"]["duplicateOf"], ["accepted-edge"])
        self.assertTrue(record["validationRecord"]["boundEvidence"])
        self.assertEqual(report.to_record()["endpointMapping"]["acceptedAssertions"], [accepted])


    def test_integrated_visible_fence_and_parent_context(self):
        """Replay visible prose and displayed examples while holding parent gates."""
        from src.extraction.llm.documents.source_units import read_page_source_units
        page = deepcopy(self.inputs["page"])
        page["content_mdx"] += "\n<!-- HIDDEN_COMMENT -->\n{runtimeValue}\n\n```python\nprint('example')\n```\n"
        page["content_sha256"] = hashlib.sha256(page["content_mdx"].encode()).hexdigest()
        mapping = deepcopy(self.inputs["accepted_section_mapping"])
        mapping["content_sha256"] = page["content_sha256"]
        reader = read_page_source_units(page, accepted_section_mapping=mapping)
        visible = next(u for u in reader["sourceUnits"] if self.quote in u["text"])
        other = next(u for u in reader["sourceUnits"] if self.other_quote in u["text"])
        fence = next(u for u in reader["sourceUnits"] if "print('example')" in u["text"])
        self.assertNotIn("HIDDEN_COMMENT", repr(reader["sourceUnits"]))
        self.assertNotIn("runtimeValue", repr(reader["sourceUnits"]))
        payload = self.payload()
        payload["candidateNodes"][0]["evidence"] = [{"sourceUnitID": visible["sourceUnitID"], "evidenceText": self.quote}]
        payload["candidateEdges"][0]["evidence"] = [{"sourceUnitID": other["sourceUnitID"], "evidenceText": self.other_quote}]
        procedure = deepcopy(payload["candidateNodes"][0])
        procedure.update(candidateID="procedure", inventoryId="A-DC05", **{"class": "Procedure"})
        parent = deepcopy(payload["candidateEdges"][0])
        parent.update(candidateID="parent", inventoryId="C-DC20", relation="hasProcedure",
                      target={"referenceType": "candidate_node", "referenceID": "procedure"})
        payload["candidateNodes"].append(procedure)
        payload["candidateEdges"].append(parent)
        for cid, inventory, name, relation, rid in (("example", "A-DC08", "Example", "hasExample", "C-DC12"),
                                                   ("parameter", "A-DOM12", "Parameter", "hasParameter", "C-DC11")):
            node = deepcopy(procedure)
            node.update(candidateID=cid, inventoryId=inventory, **{"class": name},
                evidence=[{"sourceUnitID": fence["sourceUnitID"], "evidenceText": "print('example')"}],
                parentPath=[{"referenceType": "candidate_edge", "referenceID": ref} for ref in ("parent", cid + "-edge")])
            edge = deepcopy(parent)
            edge.update(candidateID=cid + "-edge", inventoryId=rid, relation=relation,
                        source={"referenceType": "candidate_node", "referenceID": "procedure"},
                        target={"referenceType": "candidate_node", "referenceID": cid})
            payload["candidateNodes"].append(node)
            payload["candidateEdges"].append(edge)
        before = deepcopy((page, reader, payload))
        report = self.replay(payload, page=page, reader_result=reader, accepted_section_mapping=mapping,
                             selected_unit_ids=[visible["sourceUnitID"], other["sourceUnitID"], fence["sourceUnitID"]])
        records = self.records(report)
        self.assertEqual(records["tool"]["finalDisposition"], "validated")
        self.assertEqual(records["parent"]["finalDisposition"], "validated")
        self.assertEqual(records["example"]["finalDisposition"], "unresolved_condition")
        self.assertEqual(records["example"]["validationRecord"]["contextDisposition"], "possible_example_context")
        self.assertEqual(records["parameter"]["finalDisposition"], "needs_review")
        self.assertNotEqual(records["parameter-edge"]["finalDisposition"], "validated")
        for cid in ("tool", "parent", "example"):
            span = records[cid]["validationRecord"]["boundEvidence"][0]
            self.assertEqual(span["authorityTextSha256"], page["content_sha256"])
            self.assertEqual(span["startOffsetInAuthority"], page["content_mdx"].index(span["evidenceText"]))
            self.assertEqual(span["sectionID"], mapping["sections"][0]["section_id"])
        self.assertEqual(before, (page, reader, payload))
        self.assertFalse(report.to_record()["kgAuthorization"])


if __name__ == "__main__":
    unittest.main()
