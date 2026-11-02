"""Synthetic displayed-fence context checks; no accepted Example assertions."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch

from src.extraction.llm.documents.source_units import read_page_source_units
from src.extraction.llm.documents.evidence_binding import bind_hub_evidence
from src.extraction.llm.documents.example_context_binding import bind_example_context


class ExampleContextTests(unittest.TestCase):
    """Verify fence provenance and separate possible context from semantics."""

    def setUp(self):
        """Prepare static prose, uncertain markup and a displayed literal fence."""
        text = "# Guide\nVisible procedure prose.\n<Unknown>\nHidden text.\n</Unknown>\n```python\nprint('café 🌊')\nflow flow\n```\n"
        url = "https://example.test/guide"
        self.page = {"page_key": "hub-page:" + url, "canonical_url": url,
            "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_path": "guide.mdx", "corpus_path": "docs/guide.mdx", "source_group": "docs",
            "headings": [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]}
        self.page_id = "hub:page:" + hashlib.sha256(url.encode()).hexdigest()[:20]
        self.mapping = {k: self.page[k] for k in ("page_key", "canonical_url", "content_sha256")}
        self.mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": "accepted-section-1"}]
        self.reader = read_page_source_units(self.page, accepted_section_mapping=self.mapping)
        self.unit = next(u for u in self.reader["sourceUnits"] if u["contentKind"] == "fenced_snippet")

    def bind(self, quotes=None, reader=None, uid=None):
        """Bind only to synthetic trusted page records."""
        return bind_example_context(self.page, self.reader if reader is None else reader,
            self.unit["sourceUnitID"] if uid is None else uid,
            [{"evidenceText": "café 🌊"}] if quotes is None else quotes,
            accepted_page_id=self.page_id, accepted_section_mapping=self.mapping)

    def test_context_unicode_section_and_pending_parent_gates(self):
        """Exact context binding never accepts Example or interprets code."""
        result = self.bind()
        self.assertEqual(result["status"], "example_context_bound")
        self.assertEqual(result["disposition"], "possible_example_context")
        self.assertEqual(len(result["pendingGates"]), 3)
        self.assertFalse(result["kgAuthorization"])
        span = result["evidenceSpans"][0]
        self.assertEqual(span["sectionID"], "accepted-section-1")
        self.assertEqual(span["startOffsetInAuthority"], self.page["content_mdx"].index("café"))
        self.assertEqual(span["startLine"], 7)
        self.assertEqual(span["authorityTextSha256"], self.page["content_sha256"])
        self.assertEqual(span["evidenceHash"], hashlib.sha256("café 🌊".encode()).hexdigest())
        held = bind_hub_evidence(self.page, self.reader, self.unit["sourceUnitID"], [{"evidenceText": "café 🌊"}],
            accepted_page_id=self.page_id, accepted_section_mapping=self.mapping)
        self.assertEqual(held["status"], "needs_review")
        self.assertEqual(held["evidenceSpans"], [])

    def test_literals_and_nonfenced_isolation(self):
        """No fabricated quote, model coordinates or ordinary prose route."""
        for quotes in ([{"evidenceText": "flow"}], [{"evidenceText": "fake"}], [{"evidenceText": "café", "startLine": 7}]):
            self.assertEqual(self.bind(quotes)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.bind([{"evidenceText": "flow", "locatorAnchor": "flow flow"}])["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.bind([{"evidenceText": "print('café 🌊')"}])["status"], "example_context_bound")
        prose = next(u for u in self.reader["sourceUnits"] if u["contentKind"] == "prose")
        self.assertEqual(self.bind([{"evidenceText": "Visible"}], uid=prose["sourceUnitID"])["status"], "needs_review")

    def test_scoped_visibility_and_integrity(self):
        """Unrelated warnings do not release uncertain fenced units or poison good ones."""
        self.assertTrue(self.reader["reviewRequired"])
        self.assertEqual(self.bind()["status"], "example_context_bound")
        reader = deepcopy(self.reader)
        reader["diagnostics"].append({"status": "needs_review", "sourceUnitID": self.unit["sourceUnitID"], "reason": "uncertain"})
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")
        reader["diagnostics"][-1] = {"status": "failed_source_or_evidence_binding", "sourceUnitID": "other-unit", "reason": "other"}
        self.assertEqual(self.bind(reader=reader)["status"], "example_context_bound")
        reader["diagnostics"][-1].pop("sourceUnitID")
        self.assertEqual(self.bind(reader=reader)["status"], "failed_source_or_evidence_binding")
        self.page["content_sha256"] = "0" * 64
        self.assertEqual(self.bind()["status"], "failed_source_or_evidence_binding")

    def test_inputs_and_external_effects(self):
        """No writes, execution, provider requests or caller input mutation."""
        before = deepcopy((self.page, self.reader, self.mapping))
        with patch("builtins.open", side_effect=AssertionError("No IO")), patch("io.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.bind()
            self.assertEqual(result, self.bind())
        self.assertEqual(before, (self.page, self.reader, self.mapping))
        self.assertNotIn("nodes", result)
        self.assertNotIn("edges", result)
