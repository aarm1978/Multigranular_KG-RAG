"""Focused offline request/recorded-response contract checks for documents."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.documents import request_contract as contract
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH


class RequestContractTests(unittest.TestCase):
    """Exercise deterministic source context and untrusted response boundaries."""

    def setUp(self):
        """Build a synthetic visible MDX page including an isolated fence."""
        from src.extraction.llm.documents.source_units import read_page_source_units
        text = "# Guide\nA café 🌊 tool.\n```python\nprint('context')\n```\n"
        url = "https://example.test/guide"
        page = {"page_key": "hub-page:" + url, "canonical_url": url, "corpus_path": "guide.mdx", "source_path": "guide.mdx",
                "source_group": "docs", "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest()}
        suffix = hashlib.sha256(url.encode()).hexdigest()[:20]
        page["headings"] = [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]
        mapping = {k: page[k] for k in ("page_key", "canonical_url", "content_sha256")}
        mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": "hub:section:" + suffix + ":0001"}]
        reader = read_page_source_units(page, accepted_section_mapping=mapping)
        self.uid = next(u["sourceUnitID"] for u in reader["sourceUnits"] if "café" in u["text"])
        self.inputs = {"page": page, "reader_result": reader, "accepted_section_mapping": mapping, "accepted_page_id": "hub:page:" + hashlib.sha256(url.encode()).hexdigest()[:20],
                       "selected_unit_ids": [self.uid], "input_complete": True}
        self.request = self.build()

    def build(self, **kwargs):
        """Request only verified in-memory source units."""
        return contract.build_request(**{**self.inputs, **kwargs})

    def response(self):
        """Supply an exact synthetic envelope, without any inferred abstention."""
        return {"schemaVersion": contract.RESPONSE_VERSION, "candidateNodes": [
            {"candidateID": "node", "inventoryId": "A-DOM02", "class": "Tool", "label": "café tool",
             "evidence": [{"sourceUnitID": self.uid, "evidenceText": "café 🌊"}]}],
             "candidateEdges": [], "abstentions": []}

    def parse(self, payload=None, raw=None, request=None):
        """Parse records without executing candidate validation."""
        return contract.parse_recorded_response(json.dumps(self.response() if payload is None else payload,
            ensure_ascii=False) if raw is None else raw, request=self.request if request is None else request)

    def test_profile_hashes_context_and_immutability(self):
        """Hashes cover versioned instructions, exact Unicode context and inventories."""
        self.assertEqual(self.request["status"], "request_ready", self.request)
        before = deepcopy(self.inputs)
        again = self.build()
        self.assertEqual(again, self.request)
        self.assertEqual(self.inputs, before)
        body = again["request"]
        encoded = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        self.assertEqual(again["requestSha256"], hashlib.sha256(encoded).hexdigest())
        self.assertEqual(body["artifactFamily"], contract.FAMILY)
        self.assertEqual(body["selectedSourceUnitIDs"], [self.uid])
        self.assertEqual(body["sourceUnits"][0]["sourceUnitID"], self.uid)
        self.assertIn("café 🌊", body["sourceUnits"][0]["text"])
        self.assertEqual(body["targetProfile"]["ontologyVersion"], "0.1.6")
        self.assertEqual(body["targetProfile"]["inactive"]["A-D13"], "DataService")
        self.assertFalse(body["kgAuthorization"])
        self.assertNotEqual(self.build(input_complete=False)["requestSha256"], self.request["requestSha256"])
        body["sourceUnits"][0]["text"] = "detached"
        body["responseContract"]["referenceTypes"].append("injected")
        body["responseContract"]["specialFields"]["node:injected"] = ["gates"]
        self.assertEqual(self.inputs, before)
        self.assertEqual(self.build(), self.request)

    def test_strict_json_and_unidentifiable_envelopes(self):
        """No fence stripping, duplicate-key repair or fabricated empty success."""
        for raw in ('{}', '[]', '```json\n{}\n```', '{"schemaVersion":1,"schemaVersion":2}',
                    '{"x":NaN}', '{"x":1e999}', '{', '{"x":1} trailing', b'\xff'):
            result = self.parse(raw=raw)
            self.assertEqual(result["status"], "processing_failed", result)
            self.assertEqual(result["originalResponse"], raw)
            data = raw if isinstance(raw, bytes) else raw.encode()
            self.assertEqual(result["responseSha256"], hashlib.sha256(data).hexdigest())
            self.assertIsNone(result["candidatePayload"])
        for change in ({"provider": "forged"}, {"schemaVersion": "other"}, {"candidateNodes": [{}]},
                       {"candidateEdges": "bad"}):
            payload = self.response()
            payload.update(change)
            self.assertEqual(self.parse(payload)["status"], "processing_failed")
        payload = self.response()
        payload["candidateNodes"].append(deepcopy(payload["candidateNodes"][0]))
        self.assertEqual(self.parse(payload)["status"], "processing_failed")
        request = deepcopy(self.request)
        request["request"]["sourceUnits"][0]["text"] += "tampered"
        self.assertEqual(self.parse(request=request)["status"], "processing_failed")

    def test_local_errors_preserve_authentic_candidates_and_evidence(self):
        """Identifiable bad fields remain local; metadata never becomes trusted."""
        payload = self.response()
        invalid = deepcopy(payload["candidateNodes"][0])
        invalid.update(candidateID="bad", provenance={"source": "fabricated"}, gates={"accepted": True}, kgAuthorization=True)
        invalid["evidence"][0].update(startLine=99, evidenceText="not repaired")
        payload["candidateNodes"].append(invalid)
        before = deepcopy(payload)
        raw = ' \n' + json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
        result = self.parse(raw=raw.encode())
        self.assertEqual(result["status"], "response_parsed")
        self.assertEqual(result["candidatePayload"]["candidateNodes"], before["candidateNodes"])
        self.assertEqual(result["originalResponse"], raw.encode())
        self.assertEqual(result["responseText"], raw)
        self.assertEqual(result["responseSha256"], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual([r["parseDisposition"] for r in result["candidateRecords"]],
                         ["pending_validation", "local_candidate_error"])
        self.assertTrue(result["candidateRecords"][1]["eligibleForLocalizedValidation"])
        self.assertFalse(result["kgAuthorization"])
        self.assertEqual(payload, before)
        result["candidatePayload"]["candidateNodes"][0]["label"] = "detached"
        self.assertEqual(result["originalParsedResponse"], before)
        # Quotation truth and target/signature checks belong to Package 3B.
        payload = self.response()
        payload["candidateNodes"][0]["evidence"][0]["evidenceText"] = "fabricated quotation"
        self.assertEqual(self.parse(payload)["candidateRecords"][0]["parseDisposition"], "pending_validation")

    def test_edge_fragments_and_reserved_reference_fields(self):
        """Keep independent edge quotations and reject nested authority injection."""
        payload = self.response()
        owner = self.request["request"]["owner"]["endpointID"]
        edge = {"candidateID": "edge", "inventoryId": "C-DC07", "relation": "describesTool",
                "source": {"referenceType": "accepted_endpoint", "referenceID": owner},
                "target": {"referenceType": "candidate_node", "referenceID": "node"},
                "evidence": [{"sourceUnitID": self.uid, "evidenceText": "café 🌊", "contribution": "role"},
                             {"sourceUnitID": self.uid, "evidenceText": "tool", "contribution": "identity"}]}
        payload["candidateEdges"] = [edge]
        parsed = self.parse(payload)
        self.assertEqual([r["parseDisposition"] for r in parsed["candidateRecords"]],
                         ["pending_validation", "pending_validation"])
        self.assertEqual(parsed["candidatePayload"]["candidateEdges"], [edge])
        edge["target"]["providerMetadata"] = {"id": "invented"}
        parsed = self.parse(payload)
        self.assertEqual(parsed["candidateRecords"][0]["parseDisposition"], "pending_validation")
        self.assertEqual(parsed["candidateRecords"][1]["parseDisposition"], "local_candidate_error")
        edge["target"].pop("providerMetadata")
        edge["evidence"][1].pop("contribution")
        self.assertIn("evidence_fields_invalid", self.parse(payload)["candidateRecords"][1]["diagnostics"])

    def test_explicit_abstentions_and_incomplete_input_boundary(self):
        """Abstentions are unverified records, never inferred semantic outcomes."""
        payload = self.response()
        payload["candidateNodes"] = []
        self.assertEqual(self.parse(payload)["abstentionRecords"], [])
        claim = {"abstentionID": "absence", "inventoryId": "A-DOM02", "sourceUnitIDs": [self.uid],
                 "disposition": "abstained_no_evidence", "reason": "No supported tool in selected text"}
        payload["abstentions"] = [claim]
        parsed = self.parse(payload)
        self.assertEqual(parsed["abstentionRecords"][0]["parseDisposition"], "recorded_claim_pending_validation")
        partial = self.build(input_complete=False)
        parsed = self.parse(payload, request=partial)
        self.assertIn("no_evidence_precondition_unverified", parsed["abstentionRecords"][0]["diagnostics"])
        self.assertEqual(parsed["abstentionRecords"][0]["originalAbstention"], claim)
        claim["disposition"] = "abstained_ambiguous_semantics"
        self.assertEqual(self.parse(payload, request=partial)["abstentionRecords"][0]["parseDisposition"], "recorded_claim_pending_validation")
        claim["providerMetadata"] = {"id": "invented"}
        self.assertEqual(self.parse(payload)["abstentionRecords"][0]["parseDisposition"], "local_abstention_error")
        self.assertEqual(self.build(selected_unit_ids=[])["status"], "request_failed")
        self.assertEqual(self.build(selected_unit_ids=[self.uid, self.uid])["status"], "request_failed")

    def test_offline_effects_and_inventory_boundary(self):
        """Request building reads only ontology; parsing does no IO at all."""
        original_open = io.open

        def checked_open(file, mode="r", *args, **kwargs):
            """Allow the frozen ontology specification only."""
            self.assertEqual(Path(file).resolve(), ONTOLOGY_PATH.resolve())
            self.assertNotIn("w", mode)
            return original_open(file, mode, *args, **kwargs)

        with patch("socket.socket", side_effect=AssertionError("network")), patch("io.open", side_effect=checked_open):
            self.assertEqual(self.build(), self.request)
        with patch("builtins.open", side_effect=AssertionError("IO")), patch("io.open", side_effect=AssertionError("IO")):
            self.assertEqual(self.parse()["status"], "response_parsed")
        self.assertEqual(self.build(accepted_endpoints=[{"endpointID": "bad", "inventoryId": "A-D13", "class": "DataService"}])["status"], "request_failed")
        endpoint = {"endpointID": "exact-tool", "inventoryId": "A-DOM02", "class": "Tool"}
        added = self.build(accepted_endpoints=[endpoint])
        self.assertEqual(added["status"], "request_ready")
        self.assertNotEqual(added["requestSha256"], self.request["requestSha256"])
        self.assertEqual(self.build(accepted_endpoints=[endpoint, endpoint])["status"], "request_failed")

    def test_visibility_fences_parent_paths_and_source_integrity(self):
        """Fences are possible Example context, not ordinary procedural evidence."""
        reader = deepcopy(self.inputs["reader_result"])
        fence = next(u for u in reader["sourceUnits"] if u["contentKind"] == "fenced_snippet")
        request = self.build(selected_unit_ids=[fence["sourceUnitID"], self.uid])
        self.assertEqual(request["status"], "request_ready")
        self.assertEqual(request["request"]["sourceUnits"][0]["eligibility"], "possible_example_context")
        self.assertEqual(request["request"]["sourceUnits"][0]["sectionID"], self.inputs["accepted_section_mapping"]["sections"][0]["section_id"])
        self.assertIn("accepted_procedure_or_step_parent", request["request"]["targetProfile"]["entities"]["A-DC08"]["requiredGates"])
        reader["diagnostics"].append({"status": "failed_source_or_evidence_binding", "sourceUnitID": fence["sourceUnitID"], "reason": "local_failure"})
        self.assertFalse(self.build(reader_result=reader)["request"]["sourceCompleteness"]["inputComplete"])
        reader["diagnostics"][-1]["sourceUnitID"] = self.uid
        self.assertEqual(self.build(reader_result=reader)["status"], "request_failed")
        page = deepcopy(self.inputs["page"])
        page["content_mdx"] += "tamper"
        self.assertEqual(self.build(page=page)["status"], "request_failed")
        reader = deepcopy(self.inputs["reader_result"])
        reader["diagnostics"].append({"status": "needs_review", "sourceUnitID": self.uid, "reason": "uncertain_visibility"})
        self.assertEqual(self.build(reader_result=reader)["status"], "request_failed")

    def test_parent_path_recording_and_hidden_context_exclusion(self):
        """Parent references are claims; hidden MDX never expands prompt context."""
        from src.extraction.llm.documents.source_units import read_page_source_units
        payload = self.response()
        node = payload["candidateNodes"][0]
        node.update(inventoryId="A-DC08", parentPath=[{"referenceType": "candidate_edge", "referenceID": "parent"}], **{"class": "Example"})
        parsed = self.parse(payload)
        self.assertEqual(parsed["candidateRecords"][0]["parseDisposition"], "pending_validation")
        self.assertEqual(parsed["semanticStatus"], "not_evaluated")
        node["parentPath"][0]["sectionID"] = "invented"
        self.assertEqual(self.parse(payload)["candidateRecords"][0]["parseDisposition"], "local_candidate_error")
        page = deepcopy(self.inputs["page"])
        page["content_mdx"] += "<!-- HIDDEN_MDX_SENTINEL -->\n{runtimeValue}\n"
        page["content_sha256"] = hashlib.sha256(page["content_mdx"].encode()).hexdigest()
        reader = read_page_source_units(page)
        uid = next(u["sourceUnitID"] for u in reader["sourceUnits"] if "café" in u["text"])
        request = self.build(page=page, reader_result=reader, selected_unit_ids=[uid], accepted_section_mapping=None)
        self.assertEqual(request["status"], "request_ready")
        self.assertFalse(request["request"]["sourceCompleteness"]["inputComplete"])
        self.assertNotIn("HIDDEN_MDX_SENTINEL", json.dumps(request))


if __name__ == "__main__":
    unittest.main()
