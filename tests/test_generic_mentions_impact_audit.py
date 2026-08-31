"""Focused offline tests for the M2-C2C generic-mentions impact audit."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import build_generic_mentions_impact_audit as audit_module
from src.extraction.llm.publications.build_generic_mentions_impact_audit import (
    AUDIT_LABELS,
    C2B_OUTPUT_DIR,
    CALIBRATION_MANIFEST,
    REVIEWED_SCREENING_CSV,
    ROUTING_JSONL,
    SCREENING_JSONL,
    generate_audit,
    strict_evidence_containment,
)
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import DEV_IDS
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (
    C1B_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR as C2A_OUTPUT_DIR,
    _c1b_paths,
    _tree_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class GenericMentionsImpactAuditTests(unittest.TestCase):
    """Prove C2C is deterministic, offline, and historically non-mutating."""

    @classmethod
    def setUpClass(cls) -> None:
        """Generate one shared temporary audit with network access blocked."""

        cls._temporary_directory = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls._temporary_directory.name)
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=AssertionError("C2C tests must not use network"),
        ):
            cls.result = generate_audit(cls.output_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        """Release temporary audit output."""

        cls._temporary_directory.cleanup()

    def test_all_artifacts_are_prominently_audit_only(self) -> None:
        """Every JSON and Markdown artifact carries all five non-change labels."""

        for filename, artifact in self.result["artifacts"].items():
            with self.subTest(filename=filename):
                self.assertEqual(artifact["auditLabels"], AUDIT_LABELS)
                self.assertFalse(artifact["ontologyChanged"])
                self.assertFalse(artifact["screeningChanged"])
                self.assertFalse(artifact["calibrationChanged"])
                self.assertFalse(artifact["modelCallMade"])
        markdown = (self.output_dir / "generic_mentions_impact_audit.md").read_text()
        for label in AUDIT_LABELS:
            self.assertIn(label, markdown)

    def test_all_existing_mentions_relations_across_four_modules_are_audited(self) -> None:
        """The current audit captures all 16 frozen mentionsX relations."""

        audit = self.result["artifacts"]["generic_mentions_current_ontology_audit.json"]
        self.assertEqual(audit["allMentionsXRelationCount"], 16)
        self.assertEqual(
            audit["artifactModulesWithMentionsX"],
            ["dataset", "documentation", "publication", "repository"],
        )
        self.assertTrue(
            all(row["name"].startswith("mentions") for row in audit["allMentionsXRelations"])
        )

    def test_range_and_domain_audit_is_explicit_and_not_paper_only(self) -> None:
        """Every reviewed range class and all 21 discourse domains are explicit."""

        artifact = self.result["artifacts"]["generic_mentions_domain_range_audit.json"]
        range_strategy = artifact["rangeStrategy"]
        domain_strategy = artifact["domainStrategy"]
        self.assertFalse(range_strategy["owlThingUsed"])
        self.assertEqual(
            {row["ontologyClass"] for row in range_strategy["rangeRows"]},
            set(range_strategy["coverageScope"]),
        )
        self.assertFalse(domain_strategy["paperOnly"])
        self.assertEqual(len(domain_strategy["artifactContainers"]), 4)
        self.assertEqual(len(domain_strategy["fineGrainedSemanticContainers"]), 21)

    def test_screening_augmentation_is_derived_and_never_written_historically(self) -> None:
        """The 224-unit routing possibility remains separate from historical screening."""

        artifact = self.result["artifacts"]["generic_mentions_screening_recoverability.json"]
        self.assertEqual(artifact["humanScreenedUnitCount"], 267)
        self.assertEqual(artifact["recoverableUnitCount"], 224)
        self.assertEqual(artifact["notRecoverableUnitCount"], 43)
        self.assertFalse(artifact["optionBNeedsRoutingAugmentation"])
        for row in artifact["units"]:
            self.assertFalse(row["derivationIsNewHumanDecision"])
            self.assertFalse(row["derivationAssertsMentionPresence"])
            self.assertFalse(row["historicalArtifactsModified"])

    def test_reviewed_screening_routing_and_calibration_bytes_are_unchanged(self) -> None:
        """Private reviewed input and compiled/calibration authorities retain exact hashes."""

        expected = {
            REVIEWED_SCREENING_CSV: "2cba7bdb025f063b0cfbc0b05c375feee341231b34926abe43e7cd9790ce2c01",
            SCREENING_JSONL: "a34e2ca153a066cf58188f1d332e62b4077622bd5b3a2c1a68939a24c0a0db90",
            ROUTING_JSONL: "66725306608139ccf3647ac7fd4a9fc150df67426498b6e3e7408320cb8c4a1f",
            CALIBRATION_MANIFEST: "e9d761224b1c3c76c89bc6d7d63ca1f3b309e3155c4a191bbdfd66f380355d76",
        }
        for path, digest in expected.items():
            with self.subTest(path=path):
                self.assertEqual(sha256_bytes(path.read_bytes()), digest)

    def test_c1b_c2a_c2b_historical_trees_are_unchanged(self) -> None:
        """All accepted M2 inputs retain their reviewed tree hashes."""

        expected = {
            C1B_OUTPUT_DIR: "bee13c4501597cf7793d6c9e93f3d4a5b35a2881bc0cd98b1a0a24ea03682a28",
            C2A_OUTPUT_DIR: "5313dfba026eba38bb53b45b9260cb7ac419b052aa5d95a8bef7214d815d8454",
            C2B_OUTPUT_DIR: "efe067f490f585ea4194134f9d35b242437d5f7a1c30ceb342870f3b7d80173e",
        }
        for directory, digest in expected.items():
            with self.subTest(directory=directory):
                self.assertEqual(_tree_snapshot(directory)["treeInventorySha256"], digest)

    def test_all_254_model_authored_candidates_are_still_exact(self) -> None:
        """The C2B review rows remain exact projections of authentic C1B raw candidates."""

        review = json.loads(
            (C2B_OUTPUT_DIR / "publication_node_semantic_review_candidates.json").read_text()
        )
        indexed = {row["reviewCandidateKey"]: row for row in review["rows"]}
        count = 0
        for development_id in DEV_IDS:
            raw = json.loads(_c1b_paths(development_id)["raw"].read_text())
            for candidate in raw["candidateNodes"]:
                key = f"{development_id}:{candidate['candidateID']}"
                self.assertEqual(
                    canonical_json(indexed[key]["authenticModelAuthoredCandidate"]),
                    canonical_json(candidate),
                )
                count += 1
        self.assertEqual(count, 254)

    def test_evidence_containment_is_exact_and_deterministic(self) -> None:
        """Only same-unit valid unit-and-document containment creates a binding."""

        entity = {
            "sourceUnitID": "unit-1",
            "counterfactualEvidenceValid": True,
            "evidence": [
                {
                    "evidenceSpanID": "entity-evidence",
                    "startOffsetInUnit": 4,
                    "endOffsetInUnit": 8,
                    "startOffsetInDocument": 104,
                    "endOffsetInDocument": 108,
                }
            ],
        }
        discourse = {
            "sourceUnitID": "unit-1",
            "counterfactualEvidenceValid": True,
            "evidence": [
                {
                    "evidenceSpanID": "discourse-evidence",
                    "startOffsetInUnit": 1,
                    "endOffsetInUnit": 10,
                    "startOffsetInDocument": 101,
                    "endOffsetInDocument": 110,
                }
            ],
        }
        expected = [
            {
                "entityEvidenceSpanID": "entity-evidence",
                "discourseEvidenceSpanID": "discourse-evidence",
            }
        ]
        self.assertEqual(strict_evidence_containment(entity, discourse), expected)
        self.assertEqual(strict_evidence_containment(entity, discourse), expected)
        invalid_document = deepcopy_mapping(discourse)
        invalid_document["evidence"][0]["startOffsetInDocument"] = 105
        self.assertEqual(strict_evidence_containment(entity, invalid_document), [])
        other_unit = deepcopy_mapping(discourse)
        other_unit["sourceUnitID"] = "unit-2"
        self.assertEqual(strict_evidence_containment(entity, other_unit), [])

    def test_empirical_counts_and_dev01_cases_are_structural_only(self) -> None:
        """DEV statistics reproduce the bounded model-authored review universe."""

        artifact = self.result["artifacts"]["generic_mentions_devset_empirical_impact.json"]
        self.assertEqual(artifact["authenticC1BCandidateCount"], 254)
        self.assertEqual(artifact["c2bEvidenceGroupCount"], 135)
        self.assertEqual(artifact["mentionRangeModelAuthoredCandidateCount"], 129)
        self.assertEqual(artifact["mentionRangeC2AHypotheticallyUsableCandidateCount"], 128)
        self.assertEqual(artifact["potentialPaperMentionsEdgeCount"], 128)
        self.assertEqual(artifact["potentialDiscourseMentionsEdgeCount"], 133)
        self.assertEqual(
            [row["entityLabel"] for row in artifact["dev01RegionalPriorResearchCases"]],
            [
                "US Midwest",
                "Great Lakes regions",
                "coastal Southeast",
                "Southwest",
                "California",
            ],
        )
        self.assertFalse(artifact["formalAccuracyOrGoldJudgmentMade"])

    def test_calibration_repetition_is_not_required_for_option_b(self) -> None:
        """Option B avoids adding a relation choice to the frozen exercise."""

        artifact = self.result["artifacts"]["generic_mentions_calibration_impact.json"]
        self.assertEqual(artifact["calibrationUnitCount"], 16)
        self.assertEqual(artifact["optionAAffectedCalibrationUnitCount"], 14)
        self.assertTrue(artifact["optionACreatesInstructionMismatch"])
        self.assertTrue(artifact["optionBAvoidsInstructionMismatch"])
        self.assertFalse(artifact["repeatCalibrationRequiredUnderOptionB"])

    def test_generator_has_no_network_or_provider_execution_path(self) -> None:
        """The audit module imports no network/provider client and records zero calls."""

        tree = ast.parse(inspect.getsource(audit_module))
        forbidden = {"httpx", "openai", "requests", "socket", "urllib"}
        imported = set()
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.add(node.func.attr)
        self.assertTrue(imported.isdisjoint(forbidden))
        self.assertTrue(called.isdisjoint({"urlopen", "request", "OpenAI"}))
        for artifact in self.result["artifacts"].values():
            self.assertEqual(artifact["provenance"]["providerCalls"], 0)


def deepcopy_mapping(value: dict[str, object]) -> dict[str, object]:
    """Create a JSON-safe deep copy for compact synthetic test fixtures."""

    return json.loads(json.dumps(value))


if __name__ == "__main__":
    unittest.main()
