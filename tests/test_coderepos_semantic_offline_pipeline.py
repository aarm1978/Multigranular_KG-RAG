"""Synthetic T1/T2 tests for coderepos deterministic offline replay."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos import offline_pipeline as pipeline
from src.extraction.llm.coderepos import request_contract as contract
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH


class OfflineReplayTests(unittest.TestCase):
    """Verify stage isolation, exact provenance and immutable offline reports."""

    def setUp(self):
        """Read only a synthetic Phase A README into caller-owned source records."""
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        self.quote, self.other_quote = "The café 🌊 tool is used.", "An alternative tool is used."
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = {"repo_id": 7, "name": "Demo", "full_name": "Example/Demo", "archive": {"frozen_commit_sha": "a" * 40},
            "readme": {"source_path": "README.md", "text": "# Guide\n\n" + self.quote + "\n\n" + self.other_quote + "\n"},
            "files": {"downloaded": []}}
        reader = read_repository_sources(repo, Path(tmp.name))
        self.uid, self.other_uid = [u["sourceUnitID"] for u in reader["sourceUnits"]]
        owner = {k: reader["sourceUnits"][0][k] for k in ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")}
        self.owner = owner["canonicalArtifactID"]
        self.inputs = {"reader_result": reader, "accepted_repository": owner, "selected_unit_ids": [self.uid], "input_complete": True}

    def payload(self):
        """Create independently supported Tool and owner-to-Tool proposals."""
        evidence = [{"sourceUnitID": self.uid, "evidenceText": self.quote}]
        return {"schemaVersion": contract.RESPONSE_VERSION, "candidateNodes": [
            {"candidateID": "tool", "inventoryId": "A-DOM02", "class": "Tool", "label": "Tool",
             "evidence": deepcopy(evidence)}], "candidateEdges": [
            {"candidateID": "edge", "inventoryId": "C-C11", "relation": "usesTool",
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

    def test_seed_endpoint_mapping_purpose_and_unresolved_method(self):
        """Deterministic seeds bypass external inventory; Method stays non-KG."""
        from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary
        seeds = purpose_vocabulary()
        seed = seeds[0]
        payload = self.payload()
        purpose = deepcopy(payload["candidateEdges"][0])
        purpose.update(candidateID="purpose", inventoryId="C-C07", relation="hasPurpose", categoryKey=seed["categoryKey"],
            target={"referenceType": "accepted_endpoint", "referenceID": seed["nodeID"]})
        method = deepcopy(payload["candidateEdges"][0])
        method.update(candidateID="method", inventoryId="C-C16", relation="implementsMethod",
            target={"referenceType": "accepted_endpoint", "referenceID": "accepted-method"}, methodSurfaceForm="Method")
        payload["candidateEdges"].extend([purpose, method])
        endpoint = {"endpointID": "accepted-method", "inventoryId": "A-P13", "class": "Method"}
        seed_endpoint = {"endpointID": seed["nodeID"], "inventoryId": "A-C07", "class": "RepositoryPurpose"}
        report = self.replay(payload, accepted_endpoints=[endpoint, seed_endpoint]).to_record()
        self.assertEqual(report["status"], "replay_completed")
        self.assertEqual(report["endpointMapping"]["validatorAcceptedEndpoints"], [endpoint])
        self.assertEqual(len(report["endpointMapping"]["controlledSeedEndpoints"]), 6)
        self.assertEqual(report["endpointMapping"]["callerAcceptedEndpoints"], [endpoint, seed_endpoint])
        records = {r["candidateID"]: r for r in report["finalRecords"]}
        self.assertEqual(records["purpose"]["finalDisposition"], "unresolved_condition")
        self.assertEqual(records["method"]["finalDisposition"], "unresolved_endpoint")
        self.assertTrue(records["method"]["validationRecord"]["targetProfileCheck"]["pendingGates"])
        reader = deepcopy(self.inputs["reader_result"])
        reader["diagnostics"].append({"status": "failed_source_or_evidence_binding", "path": "missing.md", "reason": "downloaded_file_missing"})
        reader["inputComplete"] = False
        partial = self.replay(reader_result=reader).to_record()
        self.assertFalse(partial["sourceCompleteness"]["inputComplete"])
        self.assertTrue(partial["sourceDiagnostics"])
        self.assertEqual(partial["finalRecords"][0]["finalDisposition"], "validated")

    def test_accepted_duplicate_and_physical_selected_projection(self):
        """Retain existing assertion IDs and pass only selected units to validation."""
        payload = self.payload()
        endpoint = {"endpointID": "accepted-tool", "inventoryId": "A-DOM02", "class": "Tool"}
        payload["candidateNodes"][0]["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": "accepted-tool"}
        accepted = {"assertionID": "accepted-edge", "inventoryId": "C-C11", "relation": "usesTool",
                    "sourceID": self.owner, "targetID": "accepted-tool"}
        with patch.object(pipeline, "validate_repository_candidates", wraps=pipeline.validate_repository_candidates) as validator:
            report = self.replay(payload, accepted_endpoints=[endpoint], accepted_assertions=[accepted])
        projected = [u["sourceUnitID"] for u in validator.call_args.args[0]["sourceUnits"]]
        self.assertEqual(projected, [self.uid])
        record = self.records(report)["edge"]
        self.assertEqual(record["finalDisposition"], "suppressed_duplicate")
        self.assertEqual(record["validationRecord"]["duplicateOf"], ["accepted-edge"])
        self.assertTrue(record["validationRecord"]["boundEvidence"])
        self.assertEqual(report.to_record()["endpointMapping"]["acceptedAssertions"], [accepted])


    def test_integrated_downloaded_authorities_and_own_product(self):
        """Replay raw prose and notebook Markdown with exact channel provenance."""
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contents = root / "Demo" / "contents"
            texts = {"workshops/Flow.markdown": "Café 🌊 workflow processes discharge.\n",
                     "docs/README.md": "This guide describes a river tool.\n",
                     "CITATION.txt": "This repository supports hydrologic research.\n"}
            notebook_text = "# Notebook\n\nThe notebook documents river processing.\n"
            raw = {p: t.encode() for p, t in texts.items()}
            raw["notebooks/Flow.ipynb"] = json.dumps({"cells": [
                {"cell_type": "code", "source": "HIDDEN_CODE", "outputs": ["HIDDEN_OUTPUT"]},
                {"cell_type": "markdown", "source": notebook_text}]}).encode()
            raw["examples/run.py"] = b"HIDDEN_CODE"
            for path, data in raw.items():
                file = contents / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
            repo = {"repo_id": 7, "name": "Demo", "full_name": "Example/Demo",
                "archive": {"frozen_commit_sha": "a" * 40},
                "readme": {"source_path": "README.md", "text": self.quote},
                "files": {"downloaded": [{"path": p, "extension": Path(p).suffix, "downloaded": True,
                    "selection_reason": "allowed_semantic_folder", "file_role": "other"}
                    for p in ["README.md", *raw, "docs/missing.md"]]}}
            reader = read_repository_sources(repo, root)
        units = reader["sourceUnits"]
        self.assertEqual({u["path"] for u in units}, {"README.md", *texts, "notebooks/Flow.ipynb"})
        self.assertEqual(sum(u["path"] == "README.md" for u in units), 1)
        self.assertNotIn("HIDDEN", repr(reader))
        payload = self.payload()
        payload["candidateNodes"] = []
        payload["candidateEdges"] = []
        for i, unit in enumerate(units):
            payload["candidateNodes"].append({"candidateID": str(i), "inventoryId": "A-DOM02", "class": "Tool",
                "label": "Tool", "evidence": [{"sourceUnitID": unit["sourceUnitID"], "evidenceText": unit["text"].strip()}]})
        for cid, owner in (("own", self.owner), ("dependency", "another-repo")):
            version = deepcopy(payload["candidateNodes"][0])
            version.update(candidateID=cid, inventoryId="A-C10", **{"class": "ModelVersion"}, productRepositoryID=owner)
            payload["candidateNodes"].append(version)
        before = deepcopy((reader, payload))
        report = self.replay(payload, reader_result=reader, selected_unit_ids=[u["sourceUnitID"] for u in units])
        records = self.records(report)
        for i, unit in enumerate(units):
            self.assertEqual(records[str(i)]["finalDisposition"], "validated")
            span = records[str(i)]["validationRecord"]["boundEvidence"][0]
            authority = next(a for a in reader["authorities"] if a["path"] == unit["path"])
            self.assertEqual(span["authorityTextSha256"], authority["authorityTextSha256"])
            self.assertEqual(span["startOffsetInAuthority"], authority["text"].index(span["evidenceText"]))
            self.assertEqual(span["frozenCommitSha"], "a" * 40)
            self.assertEqual(span["cellIndex"], unit["cellIndex"])
            if unit["path"] in raw:
                self.assertEqual(span["rawFileSha256"], hashlib.sha256(raw[unit["path"]]).hexdigest())
        self.assertEqual(records["own"]["finalDisposition"], "unresolved_condition")
        self.assertEqual(records["dependency"]["finalDisposition"], "rejected_invalid_assertion")
        self.assertFalse(report.to_record()["sourceCompleteness"]["inputComplete"])
        self.assertEqual(report.to_record()["abstentionRecords"], [])
        self.assertEqual(before, (reader, payload))


if __name__ == "__main__":
    unittest.main()
