"""Focused tests for the deterministic Publication Pilot 1 source-unit builder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications import source_units as source  # noqa: E402


REAL_CORPUS = PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json"
CLI = PROJECT_ROOT / "src/extraction/llm/publications/build_publication_source_units.py"
def fixture_record(markdown_path: str = "paper.md") -> dict[str, object]:
    """Return a minimal valid Phase A publication record for unit tests."""

    return {
        "local_paper_id": "10", "canonical_artifact_id": "https://doi.org/example",
        "record_type": "journal_article", "source_files": {
            "markdown_path": markdown_path, "chunks_path": None,
            "chunks_meta_path": None, "markdown_meta_path": None,
        },
    }


def build_fixture(raw: bytes) -> tuple[list[dict[str, object]], str]:
    """Build source units directly from one synthetic canonical document."""

    units, _ = source.build_document_units(fixture_record(), raw, "1.1.0", "1.0.9")
    return units, source.normalize_canonical_text(raw)


class CanonicalTextTests(unittest.TestCase):
    """Validate canonical decoding and Unicode offset behavior."""

    def test_bom_newlines_and_controls_are_normalized_only_as_frozen(self) -> None:
        """One BOM, CRLF/CR, and forbidden C0 controls receive exact treatment."""

        raw = b"\xef\xbb\xbf# A\r\nalpha\x00beta\r\ngamma\rdelta\tend\n"
        self.assertEqual(source.normalize_canonical_text(raw), "# A\nalpha beta\ngamma\ndelta\tend\n")

    def test_invalid_utf8_fails(self) -> None:
        """Invalid UTF-8 is a contract-breaking source failure."""

        with self.assertRaisesRegex(source.SourceUnitError, "INVALID_UTF8"):
            source.normalize_canonical_text(b"\xff")

    def test_offsets_count_unicode_code_points(self) -> None:
        """Offsets slice the Python string rather than its UTF-8 bytes."""

        units, text = build_fixture("# Résumé\n\n💧 café\n".encode())
        for unit in units:
            self.assertEqual(unit["text"], text[unit["startOffsetInDocument"]:unit["endOffsetInDocument"]])
        self.assertNotEqual(len(text), len(text.encode("utf-8")))


class SectionTests(unittest.TestCase):
    """Validate the exact section partition and routing metadata."""

    def test_front_matter_and_noisy_heading_path(self) -> None:
        """Front matter is ordinal zero and noisy heading levels are preserved."""

        text = "title\n\n# One\nbody\n\n### Deep\nx\n\n## Mid\ny\n"
        sections = source.segment_sections(text, "10")
        self.assertEqual([item["ordinal"] for item in sections], [0, 1, 2, 3])
        self.assertEqual(sections[0]["role"], "front_matter")
        self.assertEqual(sections[2]["path"], ["pub:10:sec:0001", "pub:10:sec:0002"])
        self.assertEqual(sections[3]["path"], ["pub:10:sec:0001", "pub:10:sec:0003"])

    def test_heading_inside_fence_does_not_split(self) -> None:
        """ATX-looking code is not recognized as a section heading."""

        text = "# Real\n```python\n# Not a heading\n```\n## Next\n"
        self.assertEqual([item["raw"] for item in source.recognized_headings(text)], ["Real", "Next"])

    def test_reference_scope_resets_for_appendix_at_noisy_level(self) -> None:
        """Appendix semantics end references even under a deeper heading level."""

        sections = source.segment_sections("# Body\nx\n## References\nr\n### Item\nr2\n#### Appendix A\na\n", "10")
        self.assertEqual([item["role"] for item in sections], ["other", "references", "references", "appendix"])

    def test_phase_a_reference_provenance_marks_post_reset_boundary_ambiguous(self) -> None:
        """Reference provenance cannot override reset and instead records ambiguity."""

        text = "## References\n- First citation\n# Converted running header\n- Second citation\n- Third citation\n"
        sections = source.segment_sections(text, "fixture", ((4, 4), (5, 5)))
        self.assertEqual(sections[-1]["role"], "other")
        self.assertEqual(sections[-1]["role_rule"], "normalized_heading_default")
        self.assertTrue(sections[-1]["reference_boundary_ambiguous"])

        record = fixture_record()
        record["content"] = {"reference_dois": [{"occurrences": [
            {"source_location": {"section": "References", "line_start": 4, "line_end": 4}},
            {"source_location": {"section": "References", "line_start": 5, "line_end": 5}},
        ]}]}
        units, _ = source.build_document_units(record, text.encode(), "1.1.0", "1.0.9")
        ambiguous = [unit for unit in units if unit["sectionOrdinal"] == 2]
        self.assertTrue(ambiguous)
        for unit in ambiguous:
            self.assertEqual(unit["sectionRole"], "other")
            self.assertEqual(unit["eligibility"], "needs_review")
            self.assertFalse(unit["requestEligible"])
            self.assertTrue(unit["reviewRequired"])
            self.assertEqual(unit["reviewReasons"], ["ambiguous_reference_section_boundary"])
            self.assertEqual(unit["validationResults"], {"valid": True, "errorCodes": []})

    def test_genuine_structural_and_semantic_reference_resets_remain(self) -> None:
        """Absent continuation evidence and explicit semantic resets still end references."""

        scientific = source.segment_sections(
            "## References\n- Citation\n# Results\n- Scientific item\n",
            "fixture",
        )
        self.assertEqual(scientific[-1]["role"], "results")
        self.assertFalse(scientific[-1]["reference_boundary_ambiguous"])
        for heading, expected in (("### Appendix A", "appendix"), ("### Supplementary Material", "appendix"), ("### Supporting Information", "appendix")):
            with self.subTest(heading=heading):
                text = f"## References\n- Citation\n{heading}\n- Supplemental item\n"
                sections = source.segment_sections(text, "fixture", ((4, 4),))
                self.assertEqual(sections[-1]["role"], expected)
                self.assertFalse(sections[-1]["reference_boundary_ambiguous"])


class BlockAndUnitTests(unittest.TestCase):
    """Validate block recognition, preservation, splitting, and eligibility."""

    def test_supported_block_families_and_blank_lines_reconstruct(self) -> None:
        """Representative Markdown blocks partition the source without gaps."""

        text = "# H\n\nParagraph.\n\n- one\n  continuation\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n> quote\n\n$$\nx=1\n$$\n\n<div>html</div>\n\nFigure 1: Caption.\n"
        blocks = source.parse_blocks(text)
        self.assertEqual("".join(text[b.start:b.end] for b in blocks), text)
        self.assertTrue({"heading", "prose", "list", "table", "blockquote", "equation", "html", "caption"} <= {b.kind for b in blocks})

    def test_page_anchor_prefixes_preserve_and_release_same_line_content(self) -> None:
        """Only exact leading anchors are metadata; their suffixes remain classified evidence."""

        anchor = '<span id="page-2-0"></span>'
        cases = (
            (anchor + "\n", ["metadata"]),
            (anchor + "Scientific result.\n", ["metadata", "prose"]),
            (anchor + "Figure 2: Recovered caption.\n", ["metadata", "caption"]),
            (anchor + "Table 2: Recovered caption.\n", ["metadata", "caption"]),
            (anchor + "![](figure.png)\n", ["metadata", "prose"]),
            (anchor + "<img src='figure.png'>\n", ["metadata", "html"]),
            (anchor + '<span id="page-2-1"></span>More evidence.\n', ["metadata", "prose"]),
            ("Before " + anchor + " remains prose.\n", ["prose"]),
        )
        for text, kinds in cases:
            with self.subTest(text=text):
                blocks = source.parse_blocks(text)
                self.assertEqual([block.kind for block in blocks], kinds)
                self.assertEqual("".join(text[block.start:block.end] for block in blocks), text)
                self.assertEqual([(block.start, block.end) for block in blocks], [(blocks[index - 1].end if index else 0, block.end) for index, block in enumerate(blocks)])
        units, _ = build_fixture(("# Results\n\n" + anchor + "Scientific result.\n").encode())
        substantive = next(block for block in units[0]["blockMetadata"] if block["blockType"] == "prose")
        self.assertTrue(substantive["evidenceEligible"])
        self.assertEqual(units[0]["eligibility"], "eligible")

    def test_arbitrary_span_id_is_not_page_metadata(self) -> None:
        """Only supported page IDs receive special metadata-prefix treatment."""

        arbitrary = '<span id="arbitrary-anchor"></span>Scientific result.\n'
        arbitrary_blocks = source.parse_blocks(arbitrary)
        self.assertEqual([block.kind for block in arbitrary_blocks], ["html"])
        self.assertEqual(arbitrary[arbitrary_blocks[0].start:arbitrary_blocks[0].end], arbitrary)
        supported = '<span id="page-2-0"></span>Scientific result.\n'
        supported_blocks = source.parse_blocks(supported)
        self.assertEqual([block.kind for block in supported_blocks], ["metadata", "prose"])
        self.assertEqual("".join(supported[block.start:block.end] for block in supported_blocks), supported)

    def test_page_anchor_split_near_preferred_unit_boundary_is_exact(self) -> None:
        """Anchor splitting near 10,000 characters preserves offsets and the full partition."""

        anchor = '<span id="page-3-0"></span>'
        raw = ("# Results\n\n" + "a" * 9_950 + "\n\n" + anchor + "Recovered evidence.\n").encode()
        units, text = build_fixture(raw)
        self.assertEqual("".join(unit["text"] for unit in units), text)
        blocks = [block for unit in units for block in unit["blockMetadata"]]
        anchor_block = next(block for block in blocks if text[block["startOffsetInDocument"]:block["endOffsetInDocument"]] == anchor)
        following = next(block for block in blocks if block["startOffsetInDocument"] == anchor_block["endOffsetInDocument"])
        self.assertEqual(anchor_block["blockType"], "metadata")
        self.assertEqual(following["blockType"], "prose")
        self.assertEqual(text[following["startOffsetInDocument"]:following["endOffsetInDocument"]], "Recovered evidence.\n")

    def test_visual_only_and_mixed_visual_units(self) -> None:
        """Images are non-evidence; independent prose can keep a mixed unit eligible."""

        visual, _ = build_fixture(b"# Figure\n\n![plot](plot.png)\n")
        self.assertEqual(visual[0]["eligibility"], "excluded")
        self.assertIn("visual_only_evidence", visual[0]["exclusionReasons"])
        self.assertFalse(next(block for block in visual[0]["blockMetadata"] if block["visualOnly"])["evidenceEligible"])
        mixed, _ = build_fixture(b"# Results\n\nExplanation.\n\n<img src='plot.png'>\n")
        self.assertEqual(mixed[0]["eligibility"], "eligible")
        self.assertTrue(any(not block["evidenceEligible"] and block["visualOnly"] for block in mixed[0]["blockMetadata"]))

    def test_table_quality_variants_and_escaped_pipes(self) -> None:
        """Table alignment handles outer and escaped pipes without unsafe repair."""

        valid = "A | B\n---|---\nx\\|y | z\n"
        outer = "| A | B |\n|---|---|\n| x | y |\n"
        partial = "| A | B |\n|---|---|\n| x | y |\n| broken |\n"
        mismatch = "| A | B |\n|---|\n| x | y |\n"
        self.assertEqual(source.classify_pipe_table(valid)[0], "well_formed")
        self.assertEqual(source.classify_pipe_table(outer)[0], "well_formed")
        self.assertEqual(source.classify_pipe_table(partial)[0], "partially_recoverable")
        self.assertEqual(source.classify_pipe_table(mismatch)[0], "broken")
        partial_units, _ = build_fixture(("# Data\n" + partial).encode())
        self.assertEqual(partial_units[0]["eligibility"], "needs_review")
        broken_units, _ = build_fixture(("# Data\n" + mismatch).encode())
        self.assertEqual(broken_units[0]["tableQuality"], "broken")
        self.assertEqual(broken_units[0]["eligibility"], "excluded")
        self.assertIn("unrecoverable_table_structure", broken_units[0]["exclusionReasons"])
        self.assertFalse(broken_units[0]["requestEligible"])
        self.assertNotEqual(broken_units[0]["tableQuality"], "mixed")

    def test_converter_padding_table_and_unit_eligibility_are_separate(self) -> None:
        """A short empty padding column is partial while independent prose remains usable."""

        partial = "| A | B |  |\n|---|---|--|\n| x | y |  |\n"
        meaningful = "| A | B | C |\n|---|---|--|\n| x | y | z |\n"
        broken = "| A | B |\n|---|--|\n| x | y |\n"
        self.assertEqual(source.classify_pipe_table(partial)[0], "partially_recoverable")
        self.assertEqual(source.classify_pipe_table(meaningful)[0], "broken")
        for prose, table, eligibility in (
            ("Explanation.\n\n", partial, "eligible"),
            ("Explanation.\n\n", broken, "eligible"),
            ("", partial, "needs_review"),
            ("", broken, "excluded"),
        ):
            with self.subTest(prose=bool(prose), table=table.splitlines()[1]):
                raw = ("# Data\n\n" + prose + table).encode()
                units, text = build_fixture(raw)
                self.assertEqual(units[0]["eligibility"], eligibility)
                self.assertEqual("".join(unit["text"] for unit in units), text)
                table_block = next(block for block in units[0]["blockMetadata"] if block["blockType"] == "table")
                self.assertFalse(table_block["evidenceEligible"])

    def test_malformed_fences_equations_and_html_require_review(self) -> None:
        """Bounded unclosed structures remain exact but cannot be requested."""

        fixtures = (
            b"# M\n```python\nunclosed\n", b"# M\n~~~text\nunclosed\n",
            b"# M\n$$\nx=1\n", b"# M\n\\[\nx=1\n",
            b"# M\n<div>\nunclosed\n",
        )
        for raw in fixtures:
            with self.subTest(raw=raw):
                units, text = build_fixture(raw)
                self.assertEqual(units[0]["eligibility"], "needs_review")
                self.assertFalse(units[0]["requestEligible"])
                self.assertTrue(units[0]["reviewRequired"])
                self.assertEqual("".join(unit["text"] for unit in units), text)

    def test_equation_support_is_block_aware(self) -> None:
        """Only same-unit prose makes equation blocks evidence eligible."""

        cases = (
            (b"# E\n\n$$x$$\n", "excluded", False),
            (b"# E\n\n$$x$$\n\n- item\n", "eligible", False),
            (b"# E\n\n$$x$$\n\n| A |\n|---|\n| 1 |\n", "eligible", False),
            (b"# E\n\nThe balance is:\n\n$$x$$\n", "eligible", True),
            (b"# E\n\nExplanation.\n\n$$x$$\n\n$$y$$\n", "eligible", True),
        )
        for raw, eligibility, equation_evidence in cases:
            with self.subTest(raw=raw):
                units, _ = build_fixture(raw)
                self.assertEqual(units[0]["eligibility"], eligibility)
                equations = [block for block in units[0]["blockMetadata"] if block["blockType"] == "equation"]
                self.assertTrue(equations)
                self.assertTrue(all(block["evidenceEligible"] is equation_evidence for block in equations))

    def test_exact_evidence_slicing_for_supported_blocks_and_repeated_text(self) -> None:
        """Representative evidence spans agree in unit and document coordinates."""

        raw = b"# Results\n\nrepeat prose\n\n- repeat item\n\n| A |\n|---|\n| repeat |\n\nFigure 1: repeat caption\n\nExplanation repeat.\n\n$$repeat$$\n"
        units, document = build_fixture(raw)
        unit = units[0]
        for evidence in ("repeat prose", "repeat item", "repeat |", "repeat caption", "repeat$$"):
            local_start = unit["text"].index(evidence)
            local_end = local_start + len(evidence)
            document_start = unit["startOffsetInDocument"] + local_start
            document_end = unit["startOffsetInDocument"] + local_end
            self.assertEqual(unit["text"][local_start:local_end], evidence)
            self.assertEqual(document[document_start:document_end], evidence)
            self.assertEqual(document_start, unit["startOffsetInDocument"] + local_start)
            self.assertEqual(document_end, unit["startOffsetInDocument"] + local_end)
        repeated = [match.start() for match in __import__("re").finditer("repeat", unit["text"])]
        self.assertGreater(len(set(repeated)), 2)

    def test_fenced_code_is_one_block(self) -> None:
        """A complete fenced region stays atomic, including heading-like lines."""

        blocks = source.parse_blocks("```\n# code\n\ntext\n```\n")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].kind, "code")

    def test_preferred_boundary_and_complete_oversized_block(self) -> None:
        """Blocks around 10,000 characters follow preferred-boundary semantics."""

        below = "a" * 9_999 + "\n"
        above = "b" * 10_001 + "\n"
        blocks = [source.Span(0, len(below), "prose"), source.Span(len(below), len(below) + len(above), "prose")]
        units = source.unitize_blocks(blocks, below + above)
        self.assertEqual([len(item) for item in units], [1, 1])
        self.assertFalse(units[1][0].needs_review)

    def test_atomic_hard_boundary_and_oversized_prose_review(self) -> None:
        """At 20,000 is allowed; above it unsplittable prose requires review."""

        text = "a" * 20_000 + "b" * 20_001
        units = source.unitize_blocks([source.Span(0, 20_000, "prose"), source.Span(20_000, len(text), "prose")], text)
        self.assertFalse(units[0][0].needs_review)
        self.assertTrue(units[1][0].needs_review)

    def test_large_table_splits_only_between_rows(self) -> None:
        """Oversized well-formed tables retain complete row boundaries."""

        rows = [f"| {index} | {'x' * 200} |\n" for index in range(150)]
        text = "| A | B |\n|---|---|\n" + "".join(rows)
        block = source.Span(0, len(text), "table", "well_formed")
        parts = source.unitize_blocks([block], text)
        flattened = [item for unit in parts for item in unit]
        self.assertEqual("".join(text[item.start:item.end] for item in flattened), text)
        self.assertTrue(all(text[item.start:item.end].endswith("\n") for item in flattened))
        self.assertTrue(all(item.split_from_oversize for item in flattened))

    def test_large_list_splits_only_between_items(self) -> None:
        """Oversized lists split at item starts and exactly reconstruct."""

        text = "".join(f"- item {index} {'x' * 200}\n" for index in range(150))
        parts = source.unitize_blocks([source.Span(0, len(text), "list")], text)
        flattened = [item for unit in parts for item in unit]
        self.assertEqual("".join(text[item.start:item.end] for item in flattened), text)
        self.assertTrue(all(text[item.start:item.end].startswith("- item") for item in flattened))

    def test_reference_units_are_materialized_but_excluded(self) -> None:
        """Reference text remains present and is never request eligible."""

        units, _ = build_fixture(b"# References\n\nCitation.\n")
        self.assertTrue(units)
        self.assertTrue(all(unit["eligibility"] == "excluded" for unit in units))
        self.assertTrue(all(unit["exclusionReasons"] == ["reference_section"] for unit in units))

    def test_partition_required_keys_ids_hashes_and_adjacency(self) -> None:
        """Rows are complete, stable, exact, and linked only by unit references."""

        raw = b"front\n\n# Methods\n\nalpha\n\n" + b"b" * 10_001 + b"\n"
        first, text = build_fixture(raw)
        second, _ = build_fixture(raw)
        self.assertEqual(source.serialize_inventory(first), source.serialize_inventory(second))
        self.assertEqual("".join(item["text"] for item in first), text)
        for unit in first:
            self.assertLessEqual(source.REQUIRED_SOURCE_UNIT_FIELDS, set(unit))
            self.assertEqual(unit["textHash"], hashlib.sha256(unit["text"].encode()).hexdigest())
            self.assertRegex(unit["sourceUnitID"], r"^pub:10:sec:\d{4}:unit:\d{4}$")


class BuilderAndCliTests(unittest.TestCase):
    """Validate population, atomic output, CLI behavior, and real integration."""

    def _fixture_corpus(self, root: Path) -> Path:
        """Create a twelve-record fixture corpus with explicit, non-inferred paths."""

        publications = []
        for artifact_id in source.PILOT_ARTIFACT_IDS:
            path = root / f"input-{artifact_id}.md"
            path.write_text(f"# Abstract\n\nArtifact {artifact_id}.\n", encoding="utf-8")
            record = fixture_record(str(path))
            record["local_paper_id"] = artifact_id
            record["canonical_artifact_id"] = f"https://example.test/{artifact_id}"
            publications.append(record)
        corpus = root / "corpus.json"
        corpus.write_text(json.dumps({"schema_version": "1.1.0", "phase_a_version": "1.0.9", "publications": publications}), encoding="utf-8")
        return corpus

    def _copy_frozen_authorities(self, root: Path) -> Path:
        """Copy the four direct authorities into an isolated strict-mode fixture."""

        relative_paths = (
            "docs/publication_source_unit_contract.md",
            "src/extraction/llm/publications/publication_target_inventory.yaml",
            "src/ontology/ciroh_ontology.owl",
            "data/interim/papers/publication_nodes_edges.json",
        )
        for relative in relative_paths:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT_ROOT / relative, destination)
        return root / relative_paths[-1]

    def test_population_validation_and_missing_path_fail(self) -> None:
        """The builder rejects non-twelve populations and absent canonical files."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = self._fixture_corpus(root)
            with self.assertRaisesRegex(source.SourceUnitError, "exactly twelve"):
                source.build_inventory(root, corpus, ["10"], "fixed", verify_frozen_authorities=False)
            (root / "input-10.md").unlink()
            with self.assertRaisesRegex(source.SourceUnitError, "SOURCE_FILE_NOT_FOUND"):
                source.build_inventory(root, corpus, source.PILOT_ARTIFACT_IDS, "fixed", verify_frozen_authorities=False)

    def test_cli_exposes_no_frozen_authority_bypass(self) -> None:
        """Production command-line arguments cannot disable protected-authority checks."""

        help_result = subprocess.run([sys.executable, str(CLI), "--help"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(help_result.returncode, 0)
        self.assertNotIn("authority", help_result.stdout.casefold())
        bypass = subprocess.run([sys.executable, str(CLI), "--verify-frozen-authorities", "false"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        self.assertNotEqual(bypass.returncode, 0)

    def test_strict_authority_verification_blocks_missing_hash_and_version_drift(self) -> None:
        """Every missing anchor and both byte/version drift identify their exact cause."""

        relative_paths = (
            "docs/publication_source_unit_contract.md",
            "src/extraction/llm/publications/publication_target_inventory.yaml",
            "src/ontology/ciroh_ontology.owl",
            "data/interim/papers/publication_nodes_edges.json",
        )
        for relative in relative_paths:
            with self.subTest(missing=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                phase_b = self._copy_frozen_authorities(root)
                (root / relative).unlink()
                with self.assertRaisesRegex(source.SourceUnitError, rf"path={relative} reason=missing"):
                    source._verify_frozen_authorities(root, phase_b)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            phase_b = self._copy_frozen_authorities(root)
            contract = root / relative_paths[0]
            contract.write_bytes(contract.read_bytes() + b"\n")
            with self.assertRaisesRegex(source.SourceUnitError, r"path=docs/publication_source_unit_contract.md reason=hash_mismatch"):
                source._verify_frozen_authorities(root, phase_b)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            phase_b = self._copy_frozen_authorities(root)
            value = json.loads(phase_b.read_text(encoding="utf-8"))
            value["phase_b_version"] = "wrong"
            phase_b.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(source.SourceUnitError, r"path=data/interim/papers/publication_nodes_edges.json reason=version_mismatch"):
                source._verify_frozen_authorities(root, phase_b)

    def test_atomic_output_preparation_failure_preserves_existing_files(self) -> None:
        """Failure before replacement leaves both existing outputs untouched."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a", root / "b"
            first.write_bytes(b"old-a")
            second.write_bytes(b"old-b")
            with self.assertRaises(OSError):
                source.write_outputs_atomically(((first, b"new-a"), (second / "child", b"new-b")))
            self.assertEqual(first.read_bytes(), b"old-a")
            self.assertEqual(second.read_bytes(), b"old-b")

    def test_atomic_output_replacement_failure_rolls_back_both_files(self) -> None:
        """A second replacement failure restores both destinations and removes debris."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.jsonl", root / "b.json"
            first.write_bytes(b"old-a")
            second.write_bytes(b"old-b")
            real_replace = source.os.replace
            destination_replacements = 0

            def fail_second_destination(src: object, dst: object) -> None:
                """Fail once on the second non-backup destination replacement."""

                nonlocal destination_replacements
                if Path(dst) in {first, second} and ".backup." not in str(src):
                    destination_replacements += 1
                    if destination_replacements == 2:
                        raise OSError("controlled replacement failure")
                real_replace(src, dst)

            with mock.patch.object(source.os, "replace", side_effect=fail_second_destination):
                with self.assertRaisesRegex(OSError, "controlled replacement failure"):
                    source.write_outputs_atomically(((first, b"new-a"), (second, b"new-b")))
            self.assertEqual(first.read_bytes(), b"old-a")
            self.assertEqual(second.read_bytes(), b"old-b")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["a.jsonl", "b.json"])

    def test_cli_validate_only_writes_nothing_and_bad_population_is_nonzero(self) -> None:
        """Validation mode is read-only and contract failures return nonzero."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = self._fixture_corpus(root)
            inventory, manifest = root / "inventory.jsonl", root / "manifest.json"
            valid = subprocess.run([sys.executable, str(CLI), "--phase-a-corpus", str(corpus), "--output-inventory", str(inventory), "--output-manifest", str(manifest), "--validate-only", "--generation-timestamp", "fixed"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertFalse(inventory.exists())
            invalid = subprocess.run([sys.executable, str(CLI), "--phase-a-corpus", str(corpus), "--artifact-ids", "10", "--validate-only"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
            self.assertNotEqual(invalid.returncode, 0)

    def test_real_corpus_materialization_when_local_inputs_exist(self) -> None:
        """The complete fixed population validates against actual canonical files."""

        if not REAL_CORPUS.is_file():
            self.skipTest("local generated Publication Phase A corpus is unavailable")
        units, manifest = source.build_inventory(PROJECT_ROOT, REAL_CORPUS, source.PILOT_ARTIFACT_IDS, "fixed", PROJECT_ROOT / "data/interim/papers/publication_nodes_edges.json")
        self.assertEqual(manifest["artifactCount"], 12)
        self.assertEqual({item["paperID"] for item in units}, set(source.PILOT_ARTIFACT_IDS))
        self.assertEqual(manifest["sourceUnitInventoryHash"], source.sha256_bytes(source.serialize_inventory(units)))


if __name__ == "__main__":
    unittest.main()
