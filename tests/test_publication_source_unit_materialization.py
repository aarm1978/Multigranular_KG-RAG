"""Integration checks for the corrected Publication Pilot 1 materialization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications import source_units as source  # noqa: E402


CORRECTED_ROOT = PROJECT_ROOT / "data/curation/papers/pilot1"
OLD_ROOT = PROJECT_ROOT / "data" / "curation" / "publications" / "pilot1"
INVENTORY = CORRECTED_ROOT / "publication_pilot1_source_unit_inventory.jsonl"
MANIFEST = CORRECTED_ROOT / "publication_pilot1_source_unit_manifest.json"
OVERRIDES = PROJECT_ROOT / "data/curation/papers/publication_curation_overrides.yaml"
OVERRIDES_HASH = "418bff362e3965a78caf5f3f2a761ad8d2fb27b2ee6a062ee60f561e72a27871"


class CorrectedMaterializationTests(unittest.TestCase):
    """Validate final paths, bytes, provenance, and known corrected visual units."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load real outputs or skip explicitly when ignored canonical inputs are absent."""

        corpus = PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json"
        if not corpus.is_file():
            raise unittest.SkipTest("local generated Publication Phase A corpus is unavailable")
        if not INVENTORY.is_file() or not MANIFEST.is_file():
            raise unittest.SkipTest("corrected real-corpus source-unit materialization is unavailable")
        cls.rows = [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines()]
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.by_id = {row["sourceUnitID"]: row for row in cls.rows}

    def test_corrected_path_is_exclusive_and_override_is_unchanged(self) -> None:
        """Only the papers-family location exists and the Phase A override is untouched."""

        self.assertFalse(OLD_ROOT.exists())
        self.assertTrue(OVERRIDES.is_file())
        self.assertEqual(hashlib.sha256(OVERRIDES.read_bytes()).hexdigest(), OVERRIDES_HASH)

    def test_manifest_hashes_and_aliases_preserve_historical_authority(self) -> None:
        """The accepted fifth materialization retains its exact ontology-0.1.3 provenance."""

        manifest = self.manifest
        self.assertEqual(manifest["builderVersion"], "0.1.4")
        self.assertEqual(manifest["generatorVersion"], "0.1.4")
        self.assertEqual(manifest["contractVersion"], manifest["sourceUnitContractVersion"])
        self.assertEqual(manifest["configurationSha256"], manifest["sourceUnitBuilderConfigurationHash"])
        self.assertEqual(manifest["generatedAt"], manifest["generationTimestamp"])
        self.assertEqual(
            manifest["targetInventoryHash"],
            "3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760",
        )
        self.assertEqual(manifest["ontologyVersion"], "0.1.3")
        self.assertEqual(
            manifest["ontologyOwlSha256"],
            "ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57",
        )
        self.assertNotEqual(manifest["targetInventoryHash"], source.TARGET_INVENTORY_HASH)
        self.assertNotEqual(manifest["ontologyOwlSha256"], source.ONTOLOGY_OWL_HASH)
        self.assertEqual(manifest["phaseBArtifactHash"], source.PHASE_B_HASH)
        self.assertEqual(manifest["phaseBVersion"], source.PHASE_B_VERSION)
        self.assertEqual(hashlib.sha256(INVENTORY.read_bytes()).hexdigest(), manifest["sourceUnitInventoryHash"])
        self.assertEqual(hashlib.sha256((PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json").read_bytes()).hexdigest(), manifest["canonicalCorpusSha256"])

    def test_population_and_validation_are_complete(self) -> None:
        """Exactly the fixed population is present with successful row validation."""

        self.assertEqual(self.manifest["artifactCount"], 12)
        self.assertEqual(self.manifest["sectionCount"], 330)
        self.assertEqual(self.manifest["sourceUnitCount"], len(self.rows))
        self.assertEqual(self.manifest["eligibilityCounts"], {"context_only": 49, "eligible": 267, "excluded": 39, "needs_review": 3})
        self.assertEqual(self.manifest["needsReviewCount"], 3)
        self.assertEqual(self.manifest["contentAuditSummary"]["imageContainingUnitCount"], 88)
        self.assertEqual(self.manifest["contentAuditSummary"]["tableQualityCounts"], {"partially_recoverable": 3, "well_formed": 23})
        self.assertEqual(self.manifest["contentAuditSummary"]["equationContainingUnitCount"], 30)
        self.assertEqual({row["paperID"] for row in self.rows}, set(source.PILOT_ARTIFACT_IDS))
        self.assertEqual(len({row["sourceUnitID"] for row in self.rows}), len(self.rows))
        self.assertTrue(all(row["validationResults"] == {"valid": True, "errorCodes": []} for row in self.rows))
        self.assertTrue(all(source.REQUIRED_SOURCE_UNIT_FIELDS <= set(row) for row in self.rows))

    def test_page_anchor_content_is_recovered_in_real_rows(self) -> None:
        """Known scientific spans are eligible and no metadata block retains anchor suffix text."""

        known = (
            "pub:16:sec:0004:unit:0002", "pub:16:sec:0031:unit:0001",
            "pub:16:sec:0032:unit:0001", "pub:37:sec:0008:unit:0001",
            "pub:37:sec:0010:unit:0001",
        )
        for source_unit_id in known:
            unit = self.by_id[source_unit_id]
            self.assertEqual(unit["eligibility"], "eligible")
            self.assertIn("prose", unit["contentTypes"])
            self.assertTrue(any(block["blockType"] == "prose" and block["evidenceEligible"] for block in unit["blockMetadata"]))

    def test_supported_page_anchor_metadata_retains_no_substantive_suffix(self) -> None:
        """Every real page-marker metadata block contains anchors and whitespace only."""

        for unit in self.rows:
            for block in unit["blockMetadata"]:
                if block["blockType"] != "metadata":
                    continue
                start = block["startOffsetInDocument"] - unit["startOffsetInDocument"]
                end = block["endOffsetInDocument"] - unit["startOffsetInDocument"]
                block_text = unit["text"][start:end]
                if not source.PAGE_ANCHOR_TOKEN_RE.search(block_text):
                    continue
                residual = source.PAGE_ANCHOR_TOKEN_RE.sub("", block_text)
                self.assertFalse(residual.strip(), unit["sourceUnitID"])

    def test_publication_34_reference_boundary_is_structurally_reset_for_review(self) -> None:
        """Phase A conflict preserves the reset and makes all affected units review-only."""

        for ordinal in (1, 2, 3):
            unit = self.by_id[f"pub:34:sec:0031:unit:{ordinal:04d}"]
            self.assertEqual(unit["sectionRole"], "other")
            self.assertEqual(unit["sectionRoleRule"], "normalized_heading_default")
            self.assertEqual(unit["eligibility"], "needs_review")
            self.assertEqual(unit["exclusionReasons"], ["ambiguous_reference_section_boundary"])
            self.assertFalse(unit["requestEligible"])
            self.assertTrue(unit["reviewRequired"])
            self.assertEqual(unit["reviewReasons"], ["ambiguous_reference_section_boundary"])
            self.assertEqual(unit["validationResults"], {"valid": True, "errorCodes": []})

    def test_reviewed_converter_padding_tables_are_partial_but_units_are_eligible(self) -> None:
        """The three padding tables are partial blocks alongside independent eligible prose."""

        for source_unit_id in (
            "pub:18:sec:0014:unit:0001", "pub:54:sec:0033:unit:0001",
            "pub:87:sec:0008:unit:0001",
        ):
            unit = self.by_id[source_unit_id]
            self.assertEqual(unit["eligibility"], "eligible")
            self.assertEqual(unit["tableQuality"], "partially_recoverable")
            table = next(block for block in unit["blockMetadata"] if block["blockType"] == "table")
            self.assertEqual(table["blockEligibility"], "needs_review")
            self.assertFalse(table["evidenceEligible"])

    def test_eight_known_visual_only_units_are_excluded(self) -> None:
        """Every known pure-image unit is excluded, including the reference case."""

        ids = (
            "pub:10:sec:0002:unit:0001", "pub:15:sec:0000:unit:0001",
            "pub:16:sec:0000:unit:0001", "pub:16:sec:0003:unit:0001",
            "pub:16:sec:0037:unit:0003", "pub:34:sec:0000:unit:0001",
            "pub:37:sec:0000:unit:0001", "pub:79:sec:0000:unit:0001",
        )
        for source_unit_id in ids:
            with self.subTest(sourceUnitID=source_unit_id):
                unit = self.by_id[source_unit_id]
                self.assertEqual(unit["eligibility"], "excluded")
                self.assertIn("visual_only_evidence", unit["exclusionReasons"])
                self.assertFalse(unit["requestEligible"])

    def test_table_vocabulary_and_review_requests_are_safe(self) -> None:
        """Table projections are authorized and review units never become requests."""

        qualities = {row["tableQuality"] for row in self.rows if row["tableQuality"] is not None}
        self.assertLessEqual(qualities, set(source.TABLE_QUALITY_ORDER))
        self.assertNotIn("mixed", qualities)
        self.assertTrue(all(not row["requestEligible"] for row in self.rows if row["reviewRequired"]))


if __name__ == "__main__":
    unittest.main()
