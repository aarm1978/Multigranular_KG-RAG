"""Corruption tests for every frozen Publication source-unit error code."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications import source_units as source  # noqa: E402


def baseline() -> tuple[str, bytes, list[dict[str, object]], list[dict[str, object]]]:
    """Return one valid document, its raw bytes, sections, and emitted records."""

    raw = b"# Results\n\nEvidence.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    record = {
        "local_paper_id": "10", "canonical_artifact_id": "https://doi.org/example",
        "record_type": "journal_article", "source_files": {"markdown_path": "paper.md"},
    }
    units, _ = source.build_document_units(record, raw, "1.1.0", "1.0.9")
    text = source.normalize_canonical_text(raw)
    return text, raw, source.segment_sections(text, "10"), units


class FrozenValidationCodeTests(unittest.TestCase):
    """Exercise each stable code through an actual validator or input check."""

    def test_all_frozen_codes_are_exercised(self) -> None:
        """Every frozen code is produced by a deliberately corrupted valid fixture."""

        covered: set[str] = set()
        text, raw, sections, units = baseline()

        def collect(changed_text: str = text, changed_sections: object = None, changed_units: object = None, **kwargs: object) -> set[str]:
            """Run the reusable validator and accumulate its stable codes."""

            errors = set(source.collect_validation_errors(
                changed_text,
                changed_sections if changed_sections is not None else deepcopy(sections),
                changed_units if changed_units is not None else deepcopy(units),
                raw=kwargs.pop("raw", raw), expected_source_file=kwargs.pop("expected_source_file", "paper.md"),
                **kwargs,
            ))
            covered.update(errors)
            return errors

        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.md"
            with self.assertRaisesRegex(source.SourceUnitError, "SOURCE_FILE_NOT_FOUND"):
                source.validate_source_file(missing, "missing.md", "missing.md")
            covered.add("SOURCE_FILE_NOT_FOUND")
            with self.assertRaisesRegex(source.SourceUnitError, "SOURCE_PATH_MISMATCH"):
                source.validate_source_file(missing, "wrong.md", "expected.md")
            covered.add("SOURCE_PATH_MISMATCH")
        with self.assertRaisesRegex(source.SourceUnitError, "INVALID_UTF8"):
            source.normalize_canonical_text(b"\xff")
        covered.add("INVALID_UTF8")

        changed = deepcopy(units); changed[0]["rawFileSha256"] = "0" * 64
        self.assertIn("RAW_FILE_HASH_MISMATCH", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["canonicalTextSha256"] = "0" * 64
        self.assertIn("CANONICAL_TEXT_HASH_MISMATCH", collect(changed_units=changed))
        self.assertIn("FORBIDDEN_CONTROL_CHARACTER_UNSANITIZED", collect(changed_text=text + "\x01"))

        changed_sections = deepcopy(sections); changed_sections[0]["start"] = 1
        self.assertIn("SECTION_PARTITION_GAP", collect(changed_sections=changed_sections))
        overlap_sections = [deepcopy(sections[0]), deepcopy(sections[0])]
        overlap_sections[1]["id"] = "pub:10:sec:9999"
        self.assertIn("SECTION_PARTITION_OVERLAP", collect(changed_sections=overlap_sections))

        changed = deepcopy(units); changed[0]["startOffsetInDocument"] += 1
        self.assertIn("UNIT_PARTITION_GAP", collect(changed_units=changed))
        duplicate = deepcopy(units); duplicate.append(deepcopy(units[0])); duplicate[-1]["sourceUnitID"] += "-duplicate"
        self.assertIn("UNIT_PARTITION_OVERLAP", collect(changed_units=duplicate))
        changed = deepcopy(units); changed[0]["endOffsetInDocument"] = changed[0]["sectionEndOffsetInDocument"] + 1
        self.assertIn("UNIT_OUTSIDE_SECTION", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["text"] = "corrupt"
        self.assertIn("UNIT_TEXT_MISMATCH", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["startOffsetInSection"] += 1
        self.assertIn("OFFSET_MISMATCH", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["startLine"] += 1
        self.assertIn("LINE_RANGE_MISMATCH", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["textHash"] = "0" * 64
        self.assertIn("TEXT_HASH_MISMATCH", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["inputHash"] = "0" * 64
        self.assertIn("INPUT_HASH_MISMATCH", collect(changed_units=changed))

        changed = deepcopy(units); changed[0]["sectionRole"] = "unknown"
        self.assertIn("UNKNOWN_SECTION_ROLE", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["contentTypes"] = ["unknown"]
        self.assertIn("UNKNOWN_CONTENT_TYPE", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["eligibility"] = "unknown"
        self.assertIn("UNKNOWN_ELIGIBILITY", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["eligibleCategories"] = ["B-P99"]
        self.assertIn("UNKNOWN_ROUTING_CATEGORY", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["eligibleOperationalTargetIDs"] = ["UNKNOWN"]
        self.assertIn("UNKNOWN_OPERATIONAL_TARGET", collect(changed_units=changed, known_operational_targets={"KNOWN"}))
        changed = deepcopy(units); changed[0]["eligibleOperationalTargetIDs"] = ["OUT"]
        self.assertIn("OUT_OF_SCOPE_TARGET_ROUTED", collect(changed_units=changed, known_operational_targets={"OUT"}, out_of_scope_targets={"OUT"}))
        changed = deepcopy(units); changed[0]["eligibleOperationalTargetIDs"] = ["ABSTRACT"]
        self.assertIn("ABSTRACT_TARGET_ROUTED", collect(changed_units=changed, known_operational_targets={"ABSTRACT"}, abstract_targets={"ABSTRACT"}))
        changed = deepcopy(units); changed[0]["sectionRole"] = "references"; changed[0]["sectionRoleRule"] = "uncertain"
        self.assertIn("REFERENCE_SCOPE_AMBIGUOUS", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["blockMetadata"][0]["endOffsetInDocument"] = 20_001; changed[0]["blockMetadata"][0]["splitFromOversize"] = False
        self.assertIn("OVERSIZE_ATOMIC_BLOCK", collect(changed_units=changed))
        changed = deepcopy(units); changed[0]["blockMetadata"][-1]["tableQuality"] = "unknown"; changed[0]["tableQuality"] = "unknown"
        self.assertIn("BROKEN_TABLE_STRUCTURE", collect(changed_units=changed))

        expected = {
            "SOURCE_FILE_NOT_FOUND", "SOURCE_PATH_MISMATCH", "INVALID_UTF8",
            "RAW_FILE_HASH_MISMATCH", "CANONICAL_TEXT_HASH_MISMATCH",
            "FORBIDDEN_CONTROL_CHARACTER_UNSANITIZED", "SECTION_PARTITION_GAP",
            "SECTION_PARTITION_OVERLAP", "UNIT_PARTITION_GAP", "UNIT_PARTITION_OVERLAP",
            "UNIT_OUTSIDE_SECTION", "UNIT_TEXT_MISMATCH", "OFFSET_MISMATCH",
            "LINE_RANGE_MISMATCH", "TEXT_HASH_MISMATCH", "INPUT_HASH_MISMATCH",
            "UNKNOWN_SECTION_ROLE", "UNKNOWN_CONTENT_TYPE", "UNKNOWN_ELIGIBILITY",
            "UNKNOWN_ROUTING_CATEGORY", "UNKNOWN_OPERATIONAL_TARGET",
            "OUT_OF_SCOPE_TARGET_ROUTED", "ABSTRACT_TARGET_ROUTED",
            "REFERENCE_SCOPE_AMBIGUOUS", "OVERSIZE_ATOMIC_BLOCK", "BROKEN_TABLE_STRUCTURE",
        }
        self.assertEqual(len(source.STABLE_ERROR_CODES), 26)
        self.assertEqual(set(source.STABLE_ERROR_CODES), expected)
        self.assertEqual(covered, expected)

    def test_every_required_field_is_shape_checked_before_stable_validation(self) -> None:
        """Each omitted canonical field produces a deterministic non-stable shape failure."""

        text, raw, sections, units = baseline()
        for field in sorted(source.REQUIRED_SOURCE_UNIT_FIELDS):
            with self.subTest(field=field):
                changed = deepcopy(units)
                del changed[0][field]
                with self.assertRaisesRegex(source.SourceUnitError, rf"required source-unit fields missing: {field}$"):
                    source.validate_document_units(text, sections, changed, raw=raw, expected_source_file="paper.md")
        changed = deepcopy(units)
        del changed[0]["text"]
        del changed[0]["paperID"]
        with self.assertRaisesRegex(source.SourceUnitError, "required source-unit fields missing: paperID, text$"):
            source.validate_document_units(text, sections, changed, raw=raw, expected_source_file="paper.md")


if __name__ == "__main__":
    unittest.main()
