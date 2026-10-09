"""Four synthetic checks for the in-memory Hub semantic context reader."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import unittest

from src.extraction.llm.documents.source_units import read_page_source_units


class DocumentSemanticSourceUnitTests(unittest.TestCase):
    """Check exact authority, trusted structure, visibility and diagnostics."""

    def page(self, text: str) -> dict:
        """Supply synthetic frozen Phase A metadata without accessing files."""
        return {"page_key": "hub-page:https://example.test/guide", "canonical_url": "https://example.test/guide",
                "corpus_path": "docs/guide.mdx", "source_path": "src/guide.js", "source_group": "docs",
                "generated_from_js": True, "file_sha256": "b" * 64, "content_mdx": text,
                "content_sha256": hashlib.sha256(text.encode()).hexdigest(), "headings": []}

    def test_hash_identity_provenance_and_unicode_coordinates(self) -> None:
        """Keep exact MDX, Unicode offsets and copied source lineage."""
        text = "# Café 🌊\r\n\r\n流量 e\u0301 is measured.\r\n"
        page = self.page(text)
        original = deepcopy(page)
        result = read_page_source_units(page)
        self.assertEqual(result["status"], "source_read_success")
        self.assertFalse(result["reviewRequired"])
        authority = result["authority"]
        self.assertEqual(authority["text"], text)
        self.assertEqual(authority["authorityTextSha256"], page["content_sha256"])
        self.assertEqual(authority["fileIntegrityStatus"], "not_checked")
        for key in ("page_key", "canonical_url", "corpus_path", "source_path", "source_group", "file_sha256", "generated_from_js"):
            self.assertEqual(authority[key], page[key])
        unit = result["sourceUnits"][1]
        self.assertEqual(unit["startOffsetInAuthority"], text.index("流量"))
        self.assertEqual((unit["startLine"], unit["endLine"]), (3, 3))
        self.assertEqual(text[unit["startOffsetInAuthority"]:unit["endOffsetInAuthority"]], unit["text"])
        self.assertEqual(read_page_source_units(page), result)
        changed = read_page_source_units(self.page(text + "Additional prose.\n"))
        self.assertNotEqual(result["sourceUnits"][0]["sourceUnitID"], changed["sourceUnits"][0]["sourceUnitID"])
        result["authority"]["source_path"] = "changed"
        self.assertEqual(page, original)

    def test_heading_section_binding_and_visible_units(self) -> None:
        """Bind supplied ordinals/Sections only to matching snapshot and headings."""
        text = ("# Guide\n\nVisible scientific prose.\n- Prepare the data.\n"
                "| Variable | Meaning |\n| --- | --- |\n| Q | Discharge |\n"
                ":::note Read carefully\nLiteral admonition explanation.\n:::\n"
                '<Admonition type="tip">\nStatic component explanation.\n</Admonition>\n'
                "<p>Another literal explanation.</p>\n## Details\nMore details here.\n")
        page = self.page(text)
        page["headings"] = [{"ordinal": 1, "level": 1, "raw_text": "Guide", "source_line": 1},
                            {"ordinal": 2, "level": 2, "raw_text": "Details", "source_line": 15}]
        mapping = {key: page[key] for key in ("page_key", "canonical_url", "content_sha256")}
        section_id = "hub:section:" + hashlib.sha256(page["canonical_url"].encode()).hexdigest()[:20] + ":0001"
        mapping["sections"] = [{"heading_ordinal": 1, "source_line": 1, "raw_text": "Guide", "section_id": section_id}]
        original = deepcopy((page, mapping))
        result = read_page_source_units(page, accepted_section_mapping=mapping)
        units = result["sourceUnits"]
        self.assertFalse(result["reviewRequired"])
        self.assertTrue({"heading", "prose", "list_text", "table_text", "component_text"} <= {u["contentKind"] for u in units})
        self.assertEqual(units[0]["sectionID"], section_id)
        self.assertEqual(units[-1]["headingOrdinal"], 2)
        self.assertIsNone(units[-1]["sectionID"])
        self.assertIn("Another literal explanation.", [u["text"] for u in units])
        for unit in units:
            self.assertEqual(text[unit["startOffsetInAuthority"]:unit["endOffsetInAuthority"]], unit["text"])
        self.assertEqual((page, mapping), original)
        self.assertTrue(all(u["sectionID"] is None for u in read_page_source_units(page)["sourceUnits"]))
        wrong = {**mapping, "content_sha256": "0" * 64}
        rejected = read_page_source_units(page, accepted_section_mapping=wrong)
        self.assertTrue(rejected["reviewRequired"])
        self.assertTrue(all(u["sectionID"] is None for u in rejected["sourceUnits"]))

    def test_visibility_exclusions_and_fenced_example_boundaries(self) -> None:
        """Never expose hidden/dynamic contents or infer semantics from snippets."""
        text = ("Visible beginning.\n<!-- HIDDEN html\nHIDDEN continuation --> <!-- HIDDEN second\nHIDDEN again -->\n"
                "{/* HIDDEN mdx */}\n{\n\n'RUNTIME expression'\n}\n"
                "export const result = (\n\n'RUNTIME value'\n);\n"
                "<Unknown>\nHIDDEN content\n<Unknown>HIDDEN nested</Unknown>\n</Unknown>\n"
                '<div hidden>\nHIDDEN scaffolding\n</div>\n<Generated />\n'
                "<p>{RUNTIME}</p>\n"
                ":::unknown\nHIDDEN admonition\n:::\n:::note {RUNTIME}\nHIDDEN dynamic title block\n:::\n"
                "Visible ending.\n```python\n# literal {example}\nprint('only displayed')\n```\n"
                "Final visible text.\n")
        result = read_page_source_units(self.page(text))
        selected = "".join(u["text"] for u in result["sourceUnits"])
        self.assertNotIn("HIDDEN", selected)
        self.assertNotIn("RUNTIME", selected)
        self.assertIn("Visible ending.", selected)
        self.assertIn("Final visible text.", selected)
        snippets = [u for u in result["sourceUnits"] if u["contentKind"] == "fenced_snippet"]
        self.assertEqual(len(snippets), 1)
        self.assertEqual(snippets[0]["text"], "```python\n# literal {example}\nprint('only displayed')\n```\n")
        self.assertEqual(snippets[0]["eligibility"], "possible_example_context")
        self.assertTrue(result["reviewRequired"])
        self.assertEqual(result["status"], "source_read_success")
        self.assertTrue(all(d["status"] == "needs_review" for d in result["diagnostics"]))
        incomplete = read_page_source_units(self.page("Visible.\n```python\nunfinished"))
        self.assertFalse(any(u["contentKind"] == "fenced_snippet" for u in incomplete["sourceUnits"]))
        self.assertEqual(incomplete["diagnostics"][0]["reason"], "unclosed_fence_visibility")
        unclosed = read_page_source_units(self.page("<Admonition>\nUncertain visibility.\n"))
        self.assertEqual(unclosed["sourceUnits"], [])
        self.assertTrue(unclosed["reviewRequired"])

    def test_failures_diagnostic_separation_and_immutability(self) -> None:
        """Source failures produce no units; review is not semantic abstention."""
        page = self.page("# Guide\nVisible prose.\n")
        for field, value in (("content_mdx", None), ("content_mdx", []), ("content_sha256", "bad"),
                             ("page_key", None), ("source_group", 3), ("file_sha256", [])):
            with self.subTest(field=field, value=value):
                malformed = {**page, field: value}
                before = deepcopy(malformed)
                result = read_page_source_units(malformed)
                self.assertEqual(result["status"], "failed_source_or_evidence_binding")
                self.assertEqual(result["sourceUnits"], [])
                self.assertIsNone(result["authority"])
                self.assertEqual(malformed, before)
        missing = deepcopy(page)
        del missing["content_mdx"]
        self.assertEqual(read_page_source_units(missing)["status"], "failed_source_or_evidence_binding")
        mismatch = read_page_source_units({**page, "content_sha256": "0" * 64})
        self.assertEqual(mismatch["diagnostics"][0]["reason"], "source_content_integrity_failure")
        self.assertEqual(mismatch["sourceUnits"], [])
        bad_heading = {**page, "headings": [{"ordinal": 1, "source_line": 2, "raw_text": "Guide", "level": 1}]}
        reviewed = read_page_source_units(bad_heading)
        self.assertEqual(reviewed["status"], "source_read_success")
        self.assertTrue(reviewed["reviewRequired"])
        self.assertTrue(all(u["sectionID"] is None for u in reviewed["sourceUnits"]))
        good = read_page_source_units(page)
        self.assertEqual(set(good), {"status", "authority", "sourceUnits", "diagnostics", "reviewRequired"})
        self.assertEqual(good["diagnostics"], [])
        self.assertNotIn("abstained_no_evidence", repr((good, mismatch, reviewed)))


if __name__ == "__main__":
    unittest.main()
