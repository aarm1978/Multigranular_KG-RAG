"""Focused offline request/recorded-response contract checks for coderepos."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos import request_contract as contract
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH


class RequestContractTests(unittest.TestCase):
    """Exercise deterministic source context and untrusted response boundaries."""

    def setUp(self):
        """Create only a synthetic Phase A README; never read the real corpus."""
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = {"repo_id": 7, "name": "Demo", "full_name": "Example/Demo", "archive": {"frozen_commit_sha": "a" * 40},
                "readme": {"source_path": "README.md", "text": "# Guide\n\nA café 🌊 tool.\n"}, "files": {"downloaded": []}}
        reader = read_repository_sources(repo, Path(tmp.name))
        unit = reader["sourceUnits"][0]
        self.uid = unit["sourceUnitID"]
        owner = {k: unit[k] for k in ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")}
        self.inputs = {"reader_result": reader, "accepted_repository": owner, "selected_unit_ids": [self.uid], "input_complete": True}
        self.request = self.build()

    def build(self, **kwargs):
        """Use only an already materialized synthetic reader result."""
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
        edge = {"candidateID": "edge", "inventoryId": "C-C11", "relation": "usesTool",
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

    def test_purpose_method_modelversion_and_source_failure_scope(self):
        """Seed identities and pending gates survive request construction."""
        body = self.request["request"]
        self.assertEqual(len(body["purposeVocabulary"]), 6)
        self.assertEqual({s["nodeID"] for s in body["purposeVocabulary"]},
                         {e["endpointID"] for e in body["acceptedEndpoints"]})
        self.assertIn("accepted_publication_method_endpoint", body["targetProfile"]["relations"]["C-C16"]["requiredGates"])
        self.assertIn("own_repository_product", body["targetProfile"]["entities"]["A-C10"]["requiredGates"])
        reader = deepcopy(self.inputs["reader_result"])
        reader["diagnostics"].append({"status": "failed_source_or_evidence_binding", "path": "missing.md", "reason": "downloaded_file_missing"})
        reader["inputComplete"] = False
        self.assertFalse(self.build(reader_result=reader)["request"]["sourceCompleteness"]["inputComplete"])
        reader["diagnostics"][-1]["path"] = "README.md"
        self.assertEqual(self.build(reader_result=reader)["status"], "request_failed")
        reader = deepcopy(self.inputs["reader_result"])
        reader["sourceUnits"][0]["frozenCommitSha"] = "b" * 40
        self.assertEqual(self.build(reader_result=reader)["status"], "request_failed")

    def test_unclassified_purpose_and_seed_reuse(self):
        """Explicit unresolved classification survives without invented categories."""
        endpoints = self.request["request"]["acceptedEndpoints"]
        request = self.build(accepted_endpoints=endpoints)
        self.assertEqual(request, self.request)
        self.assertEqual(self.build(accepted_endpoints=[{"endpointID": "other", "inventoryId": "A-C07", "class": "RepositoryPurpose"}])["status"], "request_failed")
        payload = self.response()
        payload["candidateEdges"] = [{"candidateID": "purpose", "inventoryId": "C-C07", "relation": "hasPurpose",
            "source": {"referenceType": "accepted_endpoint", "referenceID": self.inputs["accepted_repository"]["canonicalArtifactID"]},
            "target": None, "categoryKey": None, "classification": "unclassified", "reason": "No fitting category",
            "evidence": [{"sourceUnitID": self.uid, "evidenceText": "café 🌊"}]}]
        self.assertEqual(self.parse(payload)["candidateRecords"][1]["parseDisposition"], "pending_validation")
        node = payload["candidateNodes"][0]
        node.update(inventoryId="A-C10", productRepositoryID=self.inputs["accepted_repository"]["canonicalArtifactID"], **{"class": "ModelVersion"})
        self.assertEqual(self.parse(payload)["candidateRecords"][0]["parseDisposition"], "pending_validation")
        node["ownRepositoryProduct"] = True
        self.assertEqual(self.parse(payload)["candidateRecords"][0]["parseDisposition"], "local_candidate_error")

    def test_notebook_authority_context_preservation(self):
        """Original Markdown-cell coordinates/hash survive; code is never context."""
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contents = root / "Demo" / "contents"
            contents.mkdir(parents=True)
            raw = json.dumps({"cells": [{"cell_type": "code", "source": "HIDDEN_CODE_SENTINEL"},
                                      {"cell_type": "markdown", "source": ["# Intro\n", "The café 🌊 tool provides notebook prose.\n"]}]}).encode()
            (contents / "guide.ipynb").write_bytes(raw)
            repo = {"repo_id": 7, "name": "Demo", "full_name": "Example/Demo", "archive": {"frozen_commit_sha": "a" * 40},
                    "files": {"downloaded": [{"path": "guide.ipynb", "extension": ".ipynb", "downloaded": True,
                    "selection_reason": "allowed_top_level_notebook", "file_role": "notebook"}]}}
            reader = read_repository_sources(repo, root)
        uid = reader["sourceUnits"][0]["sourceUnitID"]
        request = self.build(reader_result=reader, selected_unit_ids=[uid])
        self.assertEqual(request["status"], "request_ready")
        unit = request["request"]["sourceUnits"][0]
        self.assertEqual(unit["cellIndex"], 1)
        self.assertEqual(unit["rawFileSha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(unit, reader["sourceUnits"][0])
        self.assertNotIn("HIDDEN_CODE_SENTINEL", json.dumps(request))


if __name__ == "__main__":
    unittest.main()
