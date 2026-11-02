"""Focused no-network checks for the full-semantic input-contract audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.extraction.llm.publications.audit_full_semantic_input_contract_efficiency import (
    build_audit,
    write_audit,
)
from src.extraction.llm.publications.request_builder import canonical_json


class FullSemanticInputContractEfficiencyAuditTests(unittest.TestCase):
    """Prove the audit is deterministic, complete, and explicitly no-call."""

    def test_audit_is_deterministic_and_decomposes_each_provider_input(self) -> None:
        """All ten current full-semantic inputs have exact internally consistent sizes."""

        audit = build_audit()
        self.assertEqual(audit["networkCalls"], 0)
        self.assertEqual(audit["providerCalls"], 0)
        self.assertEqual(len(audit["units"]), 10)
        self.assertEqual(audit["auditSha256"], __import__("hashlib").sha256(
            canonical_json({key: value for key, value in audit.items() if key != "auditSha256"})
        ).hexdigest())
        for row in audit["units"]:
            with self.subTest(developmentID=row["developmentID"]):
                self.assertTrue(row["compositionCheck"]["providerInputEqualsComponents"])
                self.assertTrue(row["compositionCheck"]["boundedRequestEqualsCategories"])
                self.assertGreater(row["exactBytes"]["backgroundResponsesApiBody"], row["exactBytes"]["providerInput"])
                self.assertIn("literalOnlyOffsetRule", row["literalOffsetAmbiguity"])

    def test_write_audit_emits_both_requested_artifacts(self) -> None:
        """The development-only audit has machine-readable and concise report forms."""

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            audit = write_audit(output)
            self.assertTrue((output / "publication_full_semantic_input_contract_efficiency_audit.json").exists())
            report = (output / "publication_full_semantic_input_contract_efficiency_report.md").read_text()
        self.assertIn(audit["auditSha256"], canonical_json(audit).decode("utf-8"))
        self.assertIn("Literal evidence", report)


if __name__ == "__main__":
    unittest.main()
