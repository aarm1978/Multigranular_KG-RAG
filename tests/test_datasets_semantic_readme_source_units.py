"""Synthetic README source/evidence checks; no corpus or external effects."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch

from src.extraction.llm.datasets.source_units import read_readme_source_units, bind_readme_evidence


class ReadmeTests(unittest.TestCase):
    """Check original authority, sections and explicit absence/failure semantics."""

    def setUp(self):
        """Prepare a caller-verified synthetic README."""
        self.text = "# Observations\r\nCafé 🌊 measured flow flow.\r\n"
        self.readme = {"resource_id": "resource-1", "source_path": "docs/README.md", "text": self.text}
        self.provenance = {"snapshotID": "frozen", "sourceVersion": "1", "sourceVerified": True}
        self.digest = hashlib.sha256(self.text.encode()).hexdigest()

    def read(self, readme=None, **kw):
        """Read the supplied fixture with optional overrides."""
        return read_readme_source_units(self.readme if readme is None else readme,
            accepted_owner_id="resource-1", provenance=self.provenance, **kw)

    def test_authority_sections_identity_and_coordinates(self):
        """Keep exact CRLF/Unicode and stable original section coordinates."""
        start = self.text.index("Café")
        sections = [{"startOffsetInAuthority": start, "endOffsetInAuthority": len(self.text), "headingContext": "Observations"}]
        result = self.read(sections=sections, expected_authority_text_sha256=self.digest)
        unit = result["sourceUnits"][0]
        self.assertEqual(result, self.read(sections=sections, expected_authority_text_sha256=self.digest))
        self.assertEqual(unit["text"], self.text[start:])
        self.assertEqual(unit["authorityTextSha256"], self.digest)
        self.assertEqual(unit["integrityStatus"], "matched_trusted_digest")
        bound = bind_readme_evidence(result, unit["sourceUnitID"], [{"evidenceText": "Café 🌊"}])
        span = bound["evidenceSpans"][0]
        self.assertEqual((span["startOffsetInAuthority"], span["endOffsetInAuthority"]), (start, start + 6))
        self.assertEqual((span["startLine"], span["endLine"]), (2, 2))
        self.assertIsNone(span["sectionID"])
        self.assertNotEqual(unit["sourceUnitID"], self.read()["sourceUnits"][0]["sourceUnitID"])
        self.assertEqual(self.read()["authority"]["integrityStatus"], "computed_only")

    def test_optional_missing_malformed_and_integrity(self):
        """Optional absence differs from malformed or required source failures."""
        for required, status in ((False, "optional_input_absent"), (True, "failed_source_or_evidence_binding")):
            self.assertEqual(read_readme_source_units(None, accepted_owner_id="resource-1",
                provenance=self.provenance, required=required)["status"], status)
        for readme in ({}, {**self.readme, "text": None}, {**self.readme, "resource_id": "wrong"}):
            self.assertEqual(self.read(readme)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.read(expected_authority_text_sha256="0" * 64)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.read(sections=[{"startOffsetInAuthority": 0, "endOffsetInAuthority": 999}])["status"], "failed_source_or_evidence_binding")
        self.provenance["sourceVerified"] = False
        self.assertEqual(self.read()["status"], "failed_source_or_evidence_binding")

    def test_literal_binding_and_tampering(self):
        """No quotation repair or model coordinate acceptance."""
        result = self.read()
        uid = result["sourceUnits"][0]["sourceUnitID"]
        for evidence in ([{"evidenceText": "flow"}], [{"evidenceText": "fake"}], [{"evidenceText": "Café", "startLine": 2}]):
            self.assertEqual(bind_readme_evidence(result, uid, evidence)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(bind_readme_evidence(result, uid, [{"evidenceText": "flow", "locatorAnchor": "flow."}])["status"], "evidence_bound")
        result["sourceUnits"][0]["text"] = "tampered"
        self.assertEqual(bind_readme_evidence(result, uid, [{"evidenceText": "tampered"}])["status"], "failed_source_or_evidence_binding")

    def test_immutability_no_external_effects(self):
        """No readme acquisition, graph writes or provider access."""
        before = deepcopy((self.readme, self.provenance))
        with patch("builtins.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.read()
            bound = bind_readme_evidence(result, result["sourceUnits"][0]["sourceUnitID"], [{"evidenceText": "Café"}])
        self.assertEqual(bound["status"], "evidence_bound")
        self.assertEqual(before, (self.readme, self.provenance))
        self.assertNotIn("abstained_no_evidence", repr(bound))
        self.assertNotIn("nodes", bound)
