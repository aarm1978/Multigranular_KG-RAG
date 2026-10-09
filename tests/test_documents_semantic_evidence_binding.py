"""Four synthetic T1/T2 checks for Hub literal evidence binding."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from src.extraction.llm.documents.evidence_binding import bind_hub_evidence
from src.extraction.llm.documents.source_units import read_page_source_units


class HubEvidenceBindingTests(unittest.TestCase):
    """Verify exact authority and visibility without semantic or graph effects."""

    def setUp(self) -> None:
        """Prepare a synthetic page with both visible and uncertain regions."""
        text = "# Guide\nCafé 🌊 flow flow.\n<Unknown>\nHidden words.\n</Unknown>\n{dynamic}\n```python\nprint('literal')\n```\nFinal prose.\n"
        url = "https://example.test/guide"
        self.page = {"page_key": "hub-page:" + url, "canonical_url": url,
            "corpus_path": "docs/guide.mdx", "source_path": "docs/guide.mdx", "source_group": "docs",
            "file_sha256": "b" * 64, "content_mdx": text, "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "headings": [{"ordinal": 1, "source_line": 1, "raw_text": "Guide", "level": 1}]}
        self.page_id = "hub:page:" + hashlib.sha256(url.encode()).hexdigest()[:20]
        self.section_id = "hub:section:" + hashlib.sha256(url.encode()).hexdigest()[:20] + ":0001"
        self.mapping = {key: self.page[key] for key in ("page_key", "canonical_url", "content_sha256")}
        self.mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": self.section_id}]
        self.reader = read_page_source_units(self.page, accepted_section_mapping=self.mapping)
        self.unit = self.reader["sourceUnits"][1]

    def bind(self, quotes=None, *, page=None, reader=None, unit_id=None, page_id=None, mapping=None) -> dict:
        """Bind using only caller-supplied synthetic records."""
        return bind_hub_evidence(self.page if page is None else page, self.reader if reader is None else reader,
            self.unit["sourceUnitID"] if unit_id is None else unit_id,
            [{"evidenceText": "Café 🌊"}] if quotes is None else quotes,
            accepted_page_id=self.page_id if page_id is None else page_id,
            accepted_section_mapping=self.mapping if mapping is None else mapping)

    def test_unicode_hash_and_locator_binding(self) -> None:
        """Bind code-point coordinates and preserve exact quotation bytes."""
        result = self.bind()
        self.assertEqual(result["status"], "evidence_bound")
        span = result["evidenceSpans"][0]
        self.assertEqual(span["evidenceHash"], hashlib.sha256("Café 🌊".encode()).hexdigest())
        self.assertEqual((span["startOffsetInAuthority"], span["endOffsetInAuthority"]), (8, 14))
        self.assertEqual((span["startLine"], span["endLine"]), (2, 2))
        for quote in ("flow", "fabricated", ""):
            self.assertEqual(self.bind([{"evidenceText": quote}])["status"], "failed_source_or_evidence_binding")
        located = self.bind([{"evidenceText": "flow", "locatorAnchor": "flow."}])
        self.assertEqual(located["status"], "evidence_bound")
        self.assertEqual(located["evidenceSpans"][0]["startOffsetInAuthority"], self.page["content_mdx"].index("flow."))
        self.assertEqual(self.bind([{"evidenceText": "flow", "startOffsetInUnit": 7}])["status"], "failed_source_or_evidence_binding")

    def test_integrity_identity_offsets_and_provenance(self) -> None:
        """Reject mismatched accepted page IDs, source slices and authority hashes."""
        self.assertEqual(self.bind(page_id="hub:page:wrong")["status"], "failed_source_or_evidence_binding")
        for field, value in (("content_mdx", "changed"), ("content_sha256", "0" * 64),
                             ("source_path", "wrong.mdx"), ("page_key", "other")):
            self.assertEqual(self.bind(page={**self.page, field: value})["status"], "failed_source_or_evidence_binding")
        for field, value in (("startOffsetInAuthority", 0), ("text", "fabricated"), ("authorityTextSha256", "0" * 64),
                             ("startLine", 99), ("source_path", "wrong.mdx")):
            reader = deepcopy(self.reader)
            reader["sourceUnits"][1][field] = value
            self.assertEqual(self.bind(reader=reader)["status"], "failed_source_or_evidence_binding")
        reader = deepcopy(self.reader)
        reader["authority"]["file_sha256"] = "0" * 64
        self.assertEqual(self.bind(reader=reader)["status"], "failed_source_or_evidence_binding")

    def test_static_hidden_dynamic_fences_and_scoped_review(self) -> None:
        """An unrelated warning does not invalidate a reproducibly visible unit."""
        self.assertTrue(self.reader["reviewRequired"])
        self.assertEqual(self.bind()["status"], "evidence_bound")
        fence = next(u for u in self.reader["sourceUnits"] if u["contentKind"] == "fenced_snippet")
        held = self.bind(unit_id=fence["sourceUnitID"], quotes=[{"evidenceText": "print('literal')"}])
        self.assertEqual(held["status"], "needs_review")
        self.assertEqual(held["evidenceSpans"], [])
        for literal in ("Hidden words.", "{dynamic}"):
            reader = deepcopy(self.reader)
            fake = deepcopy(self.unit)
            start = self.page["content_mdx"].index(literal)
            end = start + len(literal)
            identity = json.dumps([self.page["page_key"], self.page["content_sha256"], start, end, "prose"], separators=(",", ":"))
            fake.update(text=literal, startOffsetInAuthority=start, endOffsetInAuthority=end,
                        startLine=self.page["content_mdx"][:start].count("\n") + 1,
                        endLine=self.page["content_mdx"][:end].count("\n") + 1,
                        sourceUnitID="hub:unit:" + hashlib.sha256(identity.encode()).hexdigest())
            reader["sourceUnits"].append(fake)
            self.assertEqual(self.bind(reader=reader, unit_id=fake["sourceUnitID"])["status"], "needs_review")
        reader = deepcopy(self.reader)
        reader["diagnostics"].append({"status": "needs_review", "sourceUnitID": self.unit["sourceUnitID"], "reason": "uncertain"})
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")
        reader["diagnostics"][-1] = {"status": "needs_review", "sourceLine": 2, "reason": "uncertain"}
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")
        reader["diagnostics"][-1] = {"status": "needs_review", "reason": "unknown scope"}
        self.assertEqual(self.bind(reader=reader)["status"], "needs_review")

    def test_sections_immutability_and_zero_external_effects(self) -> None:
        """Carry verified Sections without mutating inputs or invoking external IO."""
        quotes = [{"evidenceText": "Café 🌊"}]
        before = deepcopy((self.page, self.reader, self.mapping, quotes))
        with patch("builtins.open", side_effect=AssertionError("No files")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.bind(quotes)
        self.assertEqual((self.page, self.reader, self.mapping, quotes), before)
        span = result["evidenceSpans"][0]
        self.assertEqual(span["sectionID"], self.section_id)
        self.assertEqual(span["sourceArtifactID"], self.page_id)
        for key in ("page_key", "canonical_url", "content_sha256", "file_sha256", "source_path", "corpus_path"):
            self.assertEqual(span[key], self.page[key])
        reader = read_page_source_units(self.page)
        no_section = bind_hub_evidence(self.page, reader, self.unit["sourceUnitID"], quotes, accepted_page_id=self.page_id)
        self.assertIsNone(no_section["evidenceSpans"][0]["sectionID"])
        self.assertEqual(self.bind(mapping={**self.mapping, "content_sha256": "0" * 64})["status"], "failed_source_or_evidence_binding")
        span["source_path"] = "changed copy"
        self.assertEqual(self.page, before[0])
        self.assertNotIn("nodes", result)
        self.assertNotIn("edges", result)


if __name__ == "__main__":
    unittest.main()
