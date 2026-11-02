"""Focused no-network checks for authentic evidence-binding feasibility audit."""

from __future__ import annotations

import unittest

from src.extraction.llm.publications.audit_authentic_evidence_binding_feasibility import (
    audit_unit,
    build_audit,
)


class AuthenticEvidenceBindingFeasibilityAuditTests(unittest.TestCase):
    """Prove the audit is read-only and preserves unique/ambiguous distinctions."""

    def test_full_audit_is_no_call_and_has_consistent_coverage(self) -> None:
        """The complete preserved-output audit reports all C1B span classifications."""

        audit = build_audit()
        total = audit["aggregate"]
        self.assertEqual(audit["providerCalls"], 0)
        self.assertEqual(audit["networkCalls"], 0)
        self.assertEqual(len(audit["units"]), 10)
        self.assertEqual(
            total["authenticEvidenceSpanCount"],
            total["exactlyOneOccurrenceCount"]
            + total["multipleExactOccurrenceCount"]
            + total["zeroExactOccurrenceCount"],
        )
        self.assertGreater(total["exactlyOneOccurrenceCount"], 0)
        self.assertGreater(total["multipleExactOccurrenceCount"], 0)

    def test_dev05_unique_literal_offset_mismatch_is_prospectively_bindable(self) -> None:
        """DEV-05's known failure is a unique literal with incorrect returned offsets."""

        unit = audit_unit("DEV-05")
        span = next(row for row in unit["evidenceSpanRows"] if row["evidenceSpanID"] == "evidence-0003")
        self.assertEqual(span["classification"], "exactly_one_occurrence")
        self.assertEqual(span["derivedOffsets"]["startOffsetInUnit"], 541)
        self.assertEqual(span["returnedOffsets"]["startOffsetInUnit"], 545)
        self.assertFalse(span["coordinateAgreement"]["all"])
        self.assertEqual(
            unit["summary"]["conservativeC2ACandidateFailuresProspectivelyPreventedByUniqueCoordinateBinding"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
