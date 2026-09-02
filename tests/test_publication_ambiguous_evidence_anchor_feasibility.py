"""Focused no-network tests for ambiguous authentic-evidence locator anchors."""

from __future__ import annotations

import unittest

from src.extraction.llm.publications.audit_ambiguous_evidence_anchor_feasibility import (
    build_audit,
)


class AmbiguousEvidenceAnchorFeasibilityTests(unittest.TestCase):
    """Prove all committed ambiguous cases receive exact, unique locator anchors."""

    def test_all_ambiguous_spans_have_minimal_unique_exact_anchors(self) -> None:
        """Every anchor retains its unchanged literal and avoids guide/model coordinates."""

        audit = build_audit()
        self.assertEqual(audit["providerCalls"], 0)
        self.assertEqual(len(audit["cases"]), 3)
        for row in audit["cases"]:
            with self.subTest(evidenceSpanID=row["evidenceSpanID"]):
                anchor = row["minimumUniqueLocatorAnchor"]
                self.assertEqual(anchor["exactOccurrenceCount"], 1)
                self.assertIn(row["originalEvidenceText"], anchor["anchorText"])
                self.assertGreater(
                    anchor["anchorCodePointLength"], row["originalCodePointLength"]
                )
                self.assertTrue(
                    row["locatorAnchorVerification"]["deterministicCoordinatesRecoverableFromUniqueAnchor"]
                )
                self.assertFalse(row["locatorAnchorVerification"]["usesCoordinateGuide"])
                self.assertEqual(
                    row["semanticEvidenceExtension"]["determination"],
                    "not_established_fail_closed",
                )


if __name__ == "__main__":
    unittest.main()
