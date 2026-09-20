"""Focused contract tests for the independent N=2 Human Core reliability package."""

from __future__ import annotations

import hashlib
import json
import unittest
from argparse import Namespace
from pathlib import Path

from src.annotation.publication_pilot1.calibration import (
    HUMAN_CORE_RELIABILITY_NAMESPACE,
    HUMAN_CORE_RELIABILITY_SESSION_ID,
    human_core_session_namespace,
    metadata_versions,
)
from src.annotation.publication_pilot1.calibration.app import build_service
from src.annotation.publication_pilot1.calibration.service import AnnotationService
from src.annotation.publication_pilot1.calibration.contracts import (
    AnnotationContractError,
    HUMAN_CORE_RELIABILITY_PACKAGE_RELATIVE,
    load_annotation_contracts,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = ("pub:34:sec:0015:unit:0001", "pub:79:sec:0004:unit:0001")
DELTA_NODES = {"PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-N-A-AG02-ORGANIZATION-PROSE"}
DELTA_RELATIONS = {"PUB-R-C-P13-USESMODEL-PAPER-BRANCH", "PUB-R-C-P13-USESMODEL-METHOD-BRANCH", "PUB-R-C-P14-APPLIESTO", "PUB-R-C-P23-MENTIONSMODEL", "PUB-R-C-P26-EVALUATES", "PUB-R-C-P27-HASPARAMETER", "PUB-R-C-P34-HASCOMPONENT"}


class HumanCoreReliabilityV015Tests(unittest.TestCase):
    """Protect the independent N=2 construction boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.package = json.loads((ROOT / HUMAN_CORE_RELIABILITY_PACKAGE_RELATIVE).read_text(encoding="utf-8"))
        cls.contracts = load_annotation_contracts(ROOT, mode="human-core-reliability")

    def test_exact_n2_identity_and_isolated_namespace(self) -> None:
        self.assertEqual(self.contracts.unit_order, EXPECTED_IDS)
        self.assertEqual(self.package["session"]["annotationSessionID"], HUMAN_CORE_RELIABILITY_SESSION_ID)
        self.assertEqual(human_core_session_namespace(HUMAN_CORE_RELIABILITY_SESSION_ID), HUMAN_CORE_RELIABILITY_NAMESPACE)
        self.assertEqual(metadata_versions("human-core-reliability"), ("0.1.5", "0.1.5"))

    def test_original_delta_and_consolidated_target_unions_are_exact(self) -> None:
        expected = {EXPECTED_IDS[0]: (12, 9, 17, 15), EXPECTED_IDS[1]: (11, 8, 19, 15)}
        for row in self.package["routing"]["units"]:
            unit_id = row["sourceUnitID"]
            self.assertEqual((len(row["originalRoutedScoredNodeOperationalTargetIDs"]), len(row["originalRoutedScoredRelationOperationalTargetIDs"]), len(row["eligibleNodeOperationalTargetIDs"]), len(row["eligibleRelationOperationalTargetIDs"])), expected[unit_id])
            self.assertTrue(DELTA_NODES <= set(row["eligibleNodeOperationalTargetIDs"]))
            self.assertTrue(DELTA_RELATIONS <= set(row["eligibleRelationOperationalTargetIDs"]))

    def test_v015_authorities_are_hash_bound(self) -> None:
        authorities = self.package["authorities"]
        self.assertEqual(authorities["ontologySpec"]["version"], "0.1.5")
        self.assertEqual(authorities["ontologyOwl"]["version"], "0.1.5")
        for authority in authorities.values():
            self.assertEqual(hashlib.sha256((ROOT / authority["path"]).read_bytes()).hexdigest(), authority["sha256"])

    def test_package_and_runtime_exclude_primary_supplemental_and_provider_data(self) -> None:
        serialized = json.dumps(self.package, sort_keys=True).lower()
        for forbidden in ("human_core_n5_primary", "supplemental-researcher", "primarybaseline", "rawresponse", "prompt"):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(self.contracts.baseline_endpoints(EXPECTED_IDS[0]))
        self.assertTrue(self.package["independence"]["fromScratch"])
        self.assertTrue(self.package["independence"]["noBaselineEndpointProjection"])

    def test_organization_node_and_d26_boundary_are_explicit(self) -> None:
        organization = self.contracts.node_targets["PUB-N-A-AG02-ORGANIZATION-PROSE"]
        self.assertEqual(organization["formal_classes"][0]["name"], "Organization")
        self.assertNotIn("PUB-R-D26-MENTIONS", self.contracts.relation_targets)
        boundary = self.package["organizationBoundary"]
        self.assertIn("human-annotated as a node", boundary)
        self.assertIn("MUST NOT be manually annotated", boundary)

    def test_effective_relation_signatures_match_original_plus_exact_delta_per_unit(self) -> None:
        expected_delta_only = {
            EXPECTED_IDS[0]: {"PUB-R-C-P13-USESMODEL-METHOD-BRANCH", "PUB-R-C-P14-APPLIESTO", "PUB-R-C-P23-MENTIONSMODEL"},
            EXPECTED_IDS[1]: {"PUB-R-C-P13-USESMODEL-METHOD-BRANCH", "PUB-R-C-P14-APPLIESTO", "PUB-R-C-P23-MENTIONSMODEL", "PUB-R-C-P26-EVALUATES"},
        }
        affected = DELTA_RELATIONS - {"PUB-R-C-P34-HASCOMPONENT"}
        for unit_id in EXPECTED_IDS:
            original = set(self.contracts.routes_by_id[unit_id]["originalRoutedScoredRelationOperationalTargetIDs"])
            for target_id in affected:
                signature = self.contracts.effective_relation_target(unit_id, target_id)["operational_signatures"][0]
                changed = signature["domain"] if target_id == "PUB-R-C-P27-HASPARAMETER" else signature["range"]
                if target_id in expected_delta_only[unit_id]:
                    self.assertEqual(changed, {"classes": ["AgentBasedModel"], "match": "exact"})
                else:
                    self.assertIn(target_id, original)
                    self.assertEqual(changed["classes"][-1], "AgentBasedModel")
            component = self.contracts.effective_relation_target(unit_id, "PUB-R-C-P34-HASCOMPONENT")["operational_signatures"][0]
            self.assertEqual(component["domain"]["classes"], ["Tool", "ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel", "AgentBasedModel"])
            self.assertEqual(component["range"]["classes"], component["domain"]["classes"])

    def test_ui_uses_the_same_route_level_relation_projection(self) -> None:
        service = AnnotationService.__new__(AnnotationService)
        service.contracts = self.contracts
        target_id = "PUB-R-C-P26-EVALUATES"
        shown = service._display_target(target_id, relation=True, source_unit_id=EXPECTED_IDS[1])
        self.assertEqual(shown["signatures"], self.contracts.effective_relation_target(EXPECTED_IDS[1], target_id)["operational_signatures"])

    def test_application_rejects_another_annotator_identity(self) -> None:
        with self.assertRaisesRegex(AnnotationContractError, "HUMAN_CORE_RELIABILITY_IDENTITY_MISMATCH"):
            build_service(Namespace(mode="human-core-reliability", activation_file=None, annotator_id="OTHER", annotation_session_id=HUMAN_CORE_RELIABILITY_SESSION_ID))


if __name__ == "__main__":
    unittest.main()
