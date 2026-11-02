"""Static invariants for the frozen amended Human Core matching contract."""

from __future__ import annotations

import unittest
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/publication_human_core_amended_matching_contract_v0.1.md"
AMENDMENT = ROOT / "docs/study2_evaluation_protocol_amendment_v0.1.md"
PILOT_SUCCESSOR = ROOT / "docs/publication_evaluation_matching_contract_v0.1.5.md"


class HumanCoreAmendedMatchingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = CONTRACT.read_text(encoding="utf-8")
        cls.amendment = AMENDMENT.read_text(encoding="utf-8")
        cls.pilot_successor = PILOT_SUCCESSOR.read_text(encoding="utf-8")
        cls.normalized_contract = re.sub(r"\s+", " ", cls.contract)
        cls.normalized_successor = re.sub(r"\s+", " ", cls.pilot_successor)

    def test_contract_is_frozen_and_pre_adjudication(self) -> None:
        self.assertIn("**Status:** FINAL AND FROZEN", self.contract)
        self.assertIn("frozen before A-versus-B disagreement inspection", self.contract)
        self.assertIn("descriptive and pre-adjudication", self.contract)
        self.assertIn("There is no IAA threshold", self.contract)

    def test_node_pairing_uses_mention_and_context_not_class(self) -> None:
        self.assertIn("primary mentionSpan values satisfy the qualifying", self.contract)
        self.assertIn("occurrence/contextual identities are compatible", self.contract)
        self.assertIn(
            "Class, ontology class ID, operational target ID, and label similarity are ignored",
            self.normalized_contract,
        )

    def test_relation_detection_keeps_endpoints_out_of_eligibility(self) -> None:
        self.assertIn(
            "selected endpoints are ignored as hard eligibility conditions",
            self.normalized_contract,
        )
        self.assertIn(
            "Evidence overlap admits a relation pair to a proposition-assignment component; it does not by itself declare",
            self.normalized_contract,
        )
        self.assertIn(
            "greater unordered endpoint-occurrence correspondence",
            self.normalized_contract,
        )
        endpoint_pos = self.contract.index("greater unordered endpoint-occurrence correspondence")
        generic_span_pos = self.contract.index("greater relation-specific evidence-set F1")
        self.assertLess(endpoint_pos, generic_span_pos)

    def test_evidence_views_are_separate(self) -> None:
        self.assertIn("Node mention-boundary agreement", self.contract)
        self.assertIn("Node supporting-evidence agreement", self.contract)
        self.assertIn("Relation-specific evidence agreement", self.contract)

    def test_distributed_evidence_does_not_create_retrospective_joint_gate(self) -> None:
        self.assertIn(
            "do not automatically mean that every span or source unit is jointly required",
            self.normalized_contract,
        )
        self.assertIn(
            "No joint-evidence obligation may be inferred retrospectively from distributedEvidenceReason alone",
            self.normalized_contract,
        )

    def test_tie_breaks_require_fully_qualified_provenance(self) -> None:
        self.assertIn("Fully qualified stable provenance keys", self.contract)
        self.assertIn("Bare local candidate IDs are not assumed globally unique", self.contract)
        self.assertIn("primaryV014 or supplementalV015", self.contract)
        self.assertIn("Input order is never a tie breaker", self.contract)

    def test_monitor_absence_is_not_negative(self) -> None:
        self.assertIn("Absence of a monitor annotation is not a confirmed negative", self.contract)
        self.assertIn(
            "extract_and_monitor is excluded from confirmatory N=5 micro P/R/F1",
            self.contract,
        )

    def test_amendment_and_historical_scope_are_updated(self) -> None:
        self.assertIn("**FROZEN — 2026-09-21**", self.amendment)
        self.assertIn("publication_human_core_amended_matching_contract_v0.1.md", self.amendment)
        self.assertIn(
            "historical Publication Pilot 1 compatibility successor",
            self.normalized_successor,
        )
        self.assertIn(
            "does not govern the amended Human Core reliability analysis",
            self.normalized_successor,
        )


if __name__ == "__main__":
    unittest.main()
