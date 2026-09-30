"""Focused deterministic contract tests for the Step 8 internal candidate pool."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications import step8_internal_candidate_pool as pool


class Step8InternalCandidatePoolTests(unittest.TestCase):
    """Protect the retained v0.1.3 candidate-layer boundaries."""

    def test_eligibility_is_independent_of_production_acceptance(self) -> None:
        """Lifecycle and routing, not a production disposition, decide eligibility."""

        record = {"deferredRecordID": None}
        validation = {"candidateValidationStatus": "validated", "findings": [], "normalizationStatus": "pending_review"}
        self.assertEqual(pool.eligibility_disposition(record, validation, "extract_and_evaluate"), ("eligible", "validated"))
        self.assertEqual(pool.eligibility_disposition(record, validation, "extract_and_monitor"), ("excluded", "not_routed_extract_and_evaluate"))

    def test_eligibility_boundaries_preserve_possible_duplicates_and_exclude_atomicity(self) -> None:
        """The frozen lifecycle boundary cannot be repaired into eligibility."""

        record = {"deferredRecordID": None}
        self.assertEqual(pool.eligibility_disposition(record, {"candidateValidationStatus": "needs_review", "findings": [{"code": "POSSIBLE_LOCAL_DUPLICATE"}]}, "extract_and_evaluate"), ("eligible", "possible_local_duplicate"))
        self.assertEqual(pool.eligibility_disposition(record, {"candidateValidationStatus": "needs_review", "findings": [{"code": "ATOMICITY_VIOLATION"}]}, "extract_and_evaluate"), ("excluded", "atomicity_violation"))
        self.assertEqual(pool.eligibility_disposition(record, {"candidateValidationStatus": "superseded", "findings": []}, "extract_and_evaluate"), ("excluded", "superseded"))

    def test_exact_source_local_deduplication_only(self) -> None:
        """Only exact governed link-existing identity is automatically collapsed."""

        def member(key: str, source: str, action: str, existing: str | None) -> dict[str, object]:
            return {"candidateKey": key, "sourceArtifactID": source, "recordKind": "candidate_node", "candidate": {"action": action, "operationalTargetID": "T", "existingNodeID": existing, "attributes": []}, "eligibilityReason": "validated", "evidenceOccurrences": []}
        retained, groups = pool.deduplicate([member("a", "paper-a", "link_existing", "x"), member("b", "paper-a", "link_existing", "x"), member("c", "paper-b", "link_existing", "x"), member("d", "paper-a", "propose_new", None)])
        self.assertEqual(len(retained), 3)
        self.assertEqual(groups, [])
        self.assertEqual(next(item for item in retained if item["candidateKey"] == "a")["memberCandidateKeys"], ["a", "b"])

    def test_possible_local_duplicates_remain_separate_group_members(self) -> None:
        """No automatic collapse converts uncertainty into an assertion identity."""

        base = {"sourceArtifactID": "paper-a", "recordKind": "candidate_node", "candidate": {"action": "propose_new", "operationalTargetID": "T", "existingNodeID": None, "attributes": []}, "evidenceOccurrences": [], "eligibilityReason": "possible_local_duplicate"}
        retained, groups = pool.deduplicate([{**base, "candidateKey": "a"}, {**base, "candidateKey": "b"}])
        self.assertEqual([item["candidateKey"] for item in retained], ["a", "b"])
        self.assertEqual(groups[0]["memberCandidateKeys"], ["a", "b"])

    def test_materialized_pool_preserves_reconstruction_lineage(self) -> None:
        """Every retained item retains candidate, evidence, parser, and raw lineage."""

        with tempfile.TemporaryDirectory() as directory:
            paths = pool.materialize(output_root=Path(directory))
            artifact = json.loads(paths["pool"].read_text(encoding="utf-8"))
        self.assertGreater(len(artifact["retainedPooledItems"]), 0)
        item = artifact["retainedPooledItems"][0]
        self.assertIn("candidateKey", item)
        self.assertIn("validationLineage", item)
        self.assertIn("providerRawSha256", item)
        self.assertTrue(item["evidenceOccurrences"])

    def test_fails_closed_on_frozen_binding_drift(self) -> None:
        """A changed tracked binding cannot be used to construct a pool."""

        with patch.object(pool, "_hash", return_value="drift"):
            with self.assertRaisesRegex(pool.Step8CandidatePoolError, "FROZEN_BINDING_HASH_DRIFT"):
                pool.build()


if __name__ == "__main__":
    unittest.main()
