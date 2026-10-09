"""Four synthetic T1/T2 groups for the bounded Hub Procedure validator."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from src.extraction.llm.documents.candidate_validation import validate_procedure_candidate
from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH, check_target


class HubProcedureValidationTests(unittest.TestCase):
    """Check structure, independent evidence and holds without semantic acceptance."""

    def setUp(self) -> None:
        """Create a frozen synthetic page with multiple visible and held units."""
        text = ("# Guide\nPrepare café 🌊 inputs for the run.\nThis page describes the preparation procedure.\n"
                "Save the prepared inputs. Repeat Repeat.\n<Unknown>\nHidden text.\n</Unknown>\n"
                "{runtime}\n```python\nprint('example')\n```\n")
        url = "https://example.test/guide"
        self.page = {"page_key": "hub-page:" + url, "canonical_url": url,
            "corpus_path": "docs/guide.mdx", "source_path": "docs/guide.mdx", "source_group": "docs",
            "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "file_sha256": "b" * 64,
            "headings": [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]}
        suffix = hashlib.sha256(url.encode()).hexdigest()[:20]
        self.page_id = "hub:page:" + suffix
        self.section = "hub:section:" + suffix + ":0001"
        self.mapping = {k: self.page[k] for k in ("page_key", "canonical_url", "content_sha256")}
        self.mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": self.section}]
        self.reader = read_page_source_units(self.page, accepted_section_mapping=self.mapping)
        self.payload = {
            "node": {"candidateID": "procedure-1", "class": "Procedure", "inventoryId": "A-DC05",
                     "label": "Prepare inputs", "evidence": [self.fragment("Prepare café 🌊 inputs for the run.")]},
            "edge": {"candidateID": "edge-1", "relation": "hasProcedure", "inventoryId": "C-DC20",
                     "sourceID": self.page_id, "targetCandidateID": "procedure-1",
                     "evidence": [self.fragment("This page describes the preparation procedure.")]}}

    def fragment(self, quote: str, **extra) -> dict:
        """Select a synthetic unit without inventing candidate coordinates."""
        unit = next(u for u in self.reader["sourceUnits"] if quote in u["text"])
        return {"sourceUnitID": unit["sourceUnitID"], "evidenceText": quote, **extra}

    def validate(self, payload=None, **kwargs) -> dict:
        """Pass the trusted page and reader independently of candidate content."""
        return validate_procedure_candidate(kwargs.pop("page", self.page), kwargs.pop("reader", self.reader),
            self.payload if payload is None else payload, accepted_page_id=kwargs.pop("page_id", self.page_id),
            accepted_section_mapping=kwargs.pop("mapping", self.mapping), **kwargs)

    def test_valid_structure_and_separate_evidence(self) -> None:
        """A validated pair establishes no procedural meaning or KG authorization."""
        result = self.validate()
        node, edge = result["candidates"]
        self.assertEqual([c["disposition"] for c in result["candidates"]], ["validated", "validated"])
        self.assertNotEqual(node["boundEvidence"][0]["evidenceText"], edge["boundEvidence"][0]["evidenceText"])
        self.assertTrue(edge["endpointsBound"])
        self.assertEqual(edge["targetProfileCheck"]["profileResult"], check_target("ciroh_hub", "C-DC20",
            relation_name="hasProcedure", source_class_id="A-DC01", target_class_id="A-DC05"))
        self.assertFalse(check_target("github", "C-DC20", relation_name="hasProcedure",
            source_class_id="A-DC01", target_class_id="A-DC05")["structuralScopePass"])
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        self.assertFalse(result["graphAcceptance"])
        self.assertFalse(result["kgAuthorization"])
        same = deepcopy(self.payload)
        same["edge"]["evidence"] = deepcopy(same["node"]["evidence"])
        checked = self.validate(same)
        self.assertEqual(checked["candidates"][1]["disposition"], "validated")
        self.assertEqual(len(checked["candidates"][1]["evidenceBindings"]), 1)

    def test_multiple_units_sections_and_original_coordinates(self) -> None:
        """Preserve each fragment and unverified contribution without joining text."""
        payload = deepcopy(self.payload)
        payload["node"]["evidence"][0]["contribution"] = "States preparation goal"
        payload["node"]["evidence"].append(self.fragment("Save the prepared inputs.", contribution="States final action"))
        checked = self.validate(payload)
        node = checked["candidates"][0]
        self.assertEqual(node["disposition"], "validated")
        self.assertEqual(len({s["sourceUnitID"] for s in node["boundEvidence"]}), 2)
        for index, span in enumerate(node["boundEvidence"]):
            quote = payload["node"]["evidence"][index]["evidenceText"]
            text = self.page["content_mdx"]
            start = text.index(quote)
            self.assertEqual((span["startOffsetInAuthority"], span["endOffsetInAuthority"]), (start, start + len(quote)))
            self.assertEqual(span["startLine"], text[:start].count("\n") + 1)
            self.assertEqual(span["endLine"], span["startLine"])
            self.assertEqual(span["sectionID"], self.section)
            self.assertEqual(span["sourceArtifactID"], self.page_id)
            self.assertEqual(span["authorityTextSha256"], self.page["content_sha256"])
            self.assertEqual(span["evidenceHash"], hashlib.sha256(quote.encode()).hexdigest())
            for key in ("page_key", "canonical_url", "content_sha256", "file_sha256", "source_path", "corpus_path"):
                self.assertEqual(span[key], self.page[key])
            self.assertEqual(node["evidenceBindings"][index]["originalFragment"], payload["node"]["evidence"][index])
        no_section = read_page_source_units(self.page)
        self.assertIsNone(self.validate(reader=no_section, mapping=None)["candidates"][0]["boundEvidence"][0]["sectionID"])
        del payload["node"]["evidence"][1]["contribution"]
        self.assertEqual(self.validate(payload)["candidates"][0]["disposition"], "rejected_invalid_assertion")

    def test_invalid_targets_endpoints_quotes_and_dependencies(self) -> None:
        """Retain specific failures and never validate an edge to an invalid node."""
        for kind, field, value in (("node", "class", "Step"), ("node", "inventoryId", "A-DC06"),
                ("node", "inventoryId", "A-DC08"), ("node", "inventoryId", "A-DOM12"),
                ("edge", "relation", "hasStep"), ("edge", "inventoryId", "C-DC10"),
                ("edge", "sourceID", "procedure-1"), ("edge", "sourceID", "hub:page:other"),
                ("node", "source_path", "injected")):
            payload = deepcopy(self.payload)
            payload[kind][field] = value
            checked = self.validate(payload)["candidates"]
            self.assertEqual(checked[0 if kind == "node" else 1]["disposition"], "rejected_invalid_assertion")
            if kind == "node":
                self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        for kind in ("node", "edge"):
            for quote in ("fabricated", "Repeat", ""):
                payload = deepcopy(self.payload)
                payload[kind]["evidence"] = [{**self.fragment("Repeat"), "evidenceText": quote}]
                checked = self.validate(payload)["candidates"]
                self.assertEqual(checked[0 if kind == "node" else 1]["disposition"], "failed_source_or_evidence_binding")
                if kind == "node":
                    self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        located = deepcopy(self.payload)
        located["node"]["evidence"] = [self.fragment("Repeat", locatorAnchor="Repeat.")]
        self.assertEqual(self.validate(located)["candidates"][0]["disposition"], "validated")
        for evidence in ([], [self.fragment("Prepare café", startOffsetInAuthority=8)],
                         [self.fragment("Prepare café", content_sha256=self.page["content_sha256"])],
                         [{"sourceUnitID": "other-page-unit", "evidenceText": "Prepare café"}]):
            payload = deepcopy(self.payload)
            payload["node"]["evidence"] = evidence
            checked = self.validate(payload)["candidates"]
            self.assertNotEqual(checked[0]["disposition"], "validated")
            self.assertEqual(checked[1]["disposition"], "unresolved_endpoint")
        for target in (None, "unknown"):
            payload = deepcopy(self.payload)
            payload["edge"]["targetCandidateID"] = target
            self.assertEqual(self.validate(payload)["candidates"][1]["disposition"], "unresolved_endpoint")
        payload = deepcopy(self.payload)
        payload["node"] = None
        payload["edge"]["evidence"][0]["evidenceText"] = "fake"
        result = self.validate(payload)
        self.assertIn("target_endpoint_unresolved", repr(result["diagnostics"]))
        self.assertIn("evidence_quote_unbound", repr(result["diagnostics"]))

    def test_visibility_integrity_immutability_and_zero_effects(self) -> None:
        """Review each unit; permit only ontology reads and no external effects."""
        self.assertTrue(self.reader["reviewRequired"])
        self.assertEqual(self.validate()["candidates"][0]["disposition"], "validated")
        held = deepcopy(self.payload)
        held["node"]["evidence"] = [self.fragment("print('example')")]
        result = self.validate(held)
        self.assertEqual(result["candidates"][0]["disposition"], "needs_review")
        self.assertEqual(result["candidates"][1]["disposition"], "unresolved_endpoint")
        mixed = deepcopy(self.payload)
        mixed["node"]["evidence"][0]["contribution"] = "Proposed goal"
        mixed["node"]["evidence"].append(self.fragment("print('example')", contribution="Proposed action"))
        partial = self.validate(mixed)["candidates"]
        self.assertEqual(partial[0]["disposition"], "needs_review")
        self.assertEqual(len(partial[0]["boundEvidence"]), 1)
        self.assertEqual(partial[1]["disposition"], "unresolved_endpoint")
        for kind in ("node", "edge"):
            reader = deepcopy(self.reader)
            reader["diagnostics"].append({"status": "needs_review", "reason": "uncertain visibility",
                "sourceUnitID": self.payload[kind]["evidence"][0]["sourceUnitID"]})
            self.assertEqual(self.validate(reader=reader)["candidates"][0 if kind == "node" else 1]["disposition"], "needs_review")
        for page in ({**self.page, "content_sha256": "0" * 64}, {**self.page, "content_mdx": "changed"},
                     {**self.page, "page_key": "other"}, {**self.page, "source_path": "other.mdx"}):
            self.assertEqual(self.validate(page=page)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.validate(page_id="wrong")["status"], "failed_source_or_evidence_binding")
        reader = deepcopy(self.reader)
        reader["sourceUnits"][1]["startOffsetInAuthority"] = 0
        self.assertEqual(self.validate(reader=reader)["candidates"][0]["disposition"], "failed_source_or_evidence_binding")
        before = deepcopy((self.page, self.reader, self.mapping, self.payload))
        original_open = io.open

        def authority_only(path, mode="r", *args, **kwargs):
            """Allow only read access to the frozen ontology specification."""
            self.assertEqual(Path(path), ONTOLOGY_PATH)
            self.assertEqual(mode, "rb")
            return original_open(path, mode, *args, **kwargs)

        with patch("io.open", side_effect=authority_only), patch("builtins.open", side_effect=AssertionError("No IO")), \
             patch("socket.socket", side_effect=AssertionError("No network")):
            first, second = self.validate(), self.validate()
        self.assertEqual(first, second)
        renamed = deepcopy(self.payload)
        renamed["node"]["candidateID"] = "procedure-2"
        renamed["edge"]["targetCandidateID"] = "procedure-2"
        other = self.validate(renamed)
        self.assertNotEqual(first["candidates"][0]["sourceLocalCandidateID"],
                            other["candidates"][0]["sourceLocalCandidateID"])
        altered_page = {**self.page, "content_mdx": self.page["content_mdx"] + "Additional prose.\n"}
        altered_page["content_sha256"] = hashlib.sha256(altered_page["content_mdx"].encode()).hexdigest()
        altered_mapping = {**self.mapping, "content_sha256": altered_page["content_sha256"]}
        altered_reader = read_page_source_units(altered_page, accepted_section_mapping=altered_mapping)
        revised = deepcopy(self.payload)
        for kind in ("node", "edge"):
            fragment = revised[kind]["evidence"][0]
            fragment["sourceUnitID"] = next(u["sourceUnitID"] for u in altered_reader["sourceUnits"]
                                            if fragment["evidenceText"] in u["text"])
        changed = self.validate(revised, page=altered_page, reader=altered_reader, mapping=altered_mapping)
        self.assertEqual(changed["candidates"][0]["disposition"], "validated")
        self.assertNotEqual(first["candidates"][0]["sourceLocalCandidateID"],
                            changed["candidates"][0]["sourceLocalCandidateID"])
        self.assertEqual((self.page, self.reader, self.mapping, self.payload), before)
        self.assertEqual(first["originalPayload"], self.payload)
        first["originalPayload"]["node"]["label"] = "changed copy"
        self.assertEqual(self.payload, before[3])
        self.assertNotIn("nodes", second)
        self.assertNotIn("edges", second)
        self.assertNotIn("abstained_no_evidence", repr(second))


if __name__ == "__main__":
    unittest.main()
