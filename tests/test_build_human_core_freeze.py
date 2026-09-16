"""Focused tests for the researcher-authorized Human Core Gold freeze."""

from __future__ import annotations

import unittest
from argparse import Namespace
import hashlib
import json
from pathlib import Path

from src.annotation.publication_pilot1.build_human_core_freeze import SELECTED_IDS, build_freeze, write_primary_package_definition
from src.annotation.publication_pilot1.calibration.contracts import load_annotation_contracts
from src.annotation.publication_pilot1.calibration import (
    HUMAN_CORE_PRIMARY_NAMESPACE,
    HUMAN_CORE_PRIMARY_SESSION_ID,
    HUMAN_CORE_SUPPLEMENTAL_NAMESPACE,
    HUMAN_CORE_SUPPLEMENTAL_SESSION_ID,
    human_core_session_namespace,
    metadata_versions,
)
from src.annotation.publication_pilot1.calibration.app import build_service
from src.annotation.publication_pilot1.calibration.contracts import AnnotationContractError


ROOT = Path(__file__).resolve().parents[1]


class HumanCoreFreezeTests(unittest.TestCase):
    """Protect the distinct Human Core component and its fixed partitions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.freeze = build_freeze(ROOT)

    def test_authorized_n5_is_fixed_and_not_pilot_wide(self) -> None:
        decision = self.freeze["researcherDecision"]
        self.assertEqual(tuple(item["sourceUnitID"] for item in self.freeze["selectedUnits"]), SELECTED_IDS)
        self.assertTrue(decision["selectedBeforeSemanticInspection"])
        self.assertTrue(decision["notRepresentativeOfAllPrimaryPublications"])
        self.assertIn("superseded_for_this_distinct_human_core_component_only", decision["legacyPilot1PerArtifactRepresentation"])

    def test_reliability_pair_is_deterministic_and_coverage_is_complete(self) -> None:
        self.assertEqual(len(self.freeze["reliabilitySubset"]["sourceUnitIDs"]), 2)
        self.assertTrue(self.freeze["reliabilitySubset"]["independentAnnotationRequired"])
        coverage = self.freeze["coverage"]
        self.assertEqual((coverage["distinctPaperCount"], coverage["samplingStratumCount"]), (5, 5))
        self.assertEqual((coverage["routedScoredNodeTargetCount"], coverage["routedScoredRelationTargetCount"]), (19, 16))
        self.assertEqual(coverage["uncoveredRoutedScoredNodeOperationalTargetIDs"], [])
        self.assertEqual(coverage["uncoveredRoutedScoredRelationOperationalTargetIDs"], [])

    def test_package_definition_binds_freeze_and_human_core_application_mode(self) -> None:
        freeze_path = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json"
        package_path = write_primary_package_definition(ROOT, freeze_path)
        self.assertTrue(package_path.is_file())
        payload = json.loads(package_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["packageDefinitionVersion"], "1.1.0")
        self.assertEqual(payload["guide"]["version"], "1.1")
        guide_bytes = (ROOT / payload["guide"]["path"]).read_bytes()
        self.assertEqual(payload["guide"]["sha256"], hashlib.sha256(guide_bytes).hexdigest())
        self.assertEqual(payload["guide"]["supersedes"]["version"], "1.0")

    def test_guide_v11_records_the_pre_annotation_operational_rules(self) -> None:
        guide = (ROOT / "docs/publication_human_core_expert_annotation_guide.md").read_text(encoding="utf-8")
        self.assertIn("Human Core Expert Annotation Guide v1.1", guide)
        self.assertIn("prospectively supersedes Guide v1.0 before any Human Core annotation was", guide)
        self.assertIn("not every numeric or result\ncell in a table", guide)
        self.assertIn("multiple bounded-context requests", guide)
        self.assertIn("Context is claim-scoped, not an additional annotation surface", guide)
        self.assertIn("smallest sufficient literal canonical span", guide)

    def test_human_core_application_mode_loads_only_the_frozen_units(self) -> None:
        contracts = load_annotation_contracts(ROOT, mode="human-core")
        self.assertEqual(contracts.mode, "human-core")
        self.assertEqual(contracts.unit_order, SELECTED_IDS)

    def test_human_core_metadata_versions_are_guide_v1(self) -> None:
        self.assertEqual(metadata_versions("human-core"), ("1.1", "1.1"))
        self.assertEqual(metadata_versions("calibration"), ("0.1.1", "0.1.2"))

    def test_human_core_primary_identity_is_exact(self) -> None:
        args = Namespace(
            mode="human-core", activation_file=None,
            annotator_id="DIFFERENT_ANNOTATOR", annotation_session_id="DIFFERENT_SESSION",
        )
        with self.assertRaisesRegex(AnnotationContractError, "HUMAN_CORE_PRIMARY_IDENTITY_MISMATCH"):
            build_service(args)

    def test_supplemental_session_identity_and_namespace_are_isolated(self) -> None:
        """Supplemental state/export paths cannot alias the preserved primary baseline."""

        self.assertEqual(human_core_session_namespace(HUMAN_CORE_PRIMARY_SESSION_ID), HUMAN_CORE_PRIMARY_NAMESPACE)
        self.assertEqual(human_core_session_namespace(HUMAN_CORE_SUPPLEMENTAL_SESSION_ID), HUMAN_CORE_SUPPLEMENTAL_NAMESPACE)
        self.assertNotEqual(HUMAN_CORE_PRIMARY_SESSION_ID, HUMAN_CORE_SUPPLEMENTAL_SESSION_ID)
        self.assertNotEqual(HUMAN_CORE_PRIMARY_NAMESPACE, HUMAN_CORE_SUPPLEMENTAL_NAMESPACE)
        primary_export = ROOT / "var/publication_pilot1_annotation" / HUMAN_CORE_PRIMARY_NAMESPACE / "exports" / f"{HUMAN_CORE_PRIMARY_SESSION_ID}.annotation.json"
        supplemental_export = ROOT / "var/publication_pilot1_annotation" / HUMAN_CORE_SUPPLEMENTAL_NAMESPACE / "exports" / f"{HUMAN_CORE_SUPPLEMENTAL_SESSION_ID}.annotation.json"
        self.assertNotEqual(primary_export, supplemental_export)
        self.assertEqual(hashlib.sha256(primary_export.read_bytes()).hexdigest(), "9d71ae66c3218c4b8be21a3ea10b4015cb5502fce5eaf75f6bb0ac9922bc4e74")


if __name__ == "__main__":
    unittest.main()
