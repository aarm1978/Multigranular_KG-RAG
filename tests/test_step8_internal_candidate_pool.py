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
            return {"candidateKey": key, "requestID": "r", "sourceArtifactID": source, "recordKind": "candidate_node", "candidate": {"action": action, "operationalTargetID": "T", "existingNodeID": existing, "attributes": []}, "validationLineage": {"findings": []}, "eligibilityDisposition": "eligible", "eligibilityReason": "validated", "evidenceOccurrences": [{"evidenceSpanID": key}]}
        retained, groups = pool.deduplicate([member("a", "paper-a", "link_existing", "x"), member("b", "paper-a", "link_existing", "x"), member("c", "paper-b", "link_existing", "x"), member("d", "paper-a", "propose_new", None)])
        self.assertEqual(len(retained), 3)
        self.assertEqual(groups, [])
        self.assertEqual(next(item for item in retained if item["candidateKey"] == "a")["memberCandidateKeys"], ["a", "b"])
        self.assertEqual({row["contributingCandidateKey"] for row in retained[0]["evidenceOccurrences"]}, {"a", "b"})

    def test_possible_local_duplicates_remain_separate_group_members(self) -> None:
        """No automatic collapse converts uncertainty into an assertion identity."""

        base = {"requestID": "r", "sourceArtifactID": "paper-a", "recordKind": "candidate_node", "candidate": {"action": "propose_new", "operationalTargetID": "T", "existingNodeID": None, "attributes": []}, "evidenceOccurrences": [], "eligibilityDisposition": "eligible", "eligibilityReason": "validated"}
        first = {**base, "candidateKey": "r|candidate_node|a", "validationLineage": {"findings": []}}
        second = {**base, "candidateKey": "r|candidate_node|b", "eligibilityReason": "possible_local_duplicate", "validationLineage": {"findings": [{"stage": "V10", "code": "POSSIBLE_LOCAL_DUPLICATE", "expected": "a"}]}}
        third = {**base, "candidateKey": "r|candidate_node|c", "validationLineage": {"findings": []}}
        fourth = {**base, "candidateKey": "r|candidate_node|d", "eligibilityReason": "possible_local_duplicate", "validationLineage": {"findings": [{"stage": "V10", "code": "POSSIBLE_LOCAL_DUPLICATE", "expected": "c"}]}}
        retained, groups = pool.deduplicate([first, second, third, fourth])
        self.assertEqual(len(retained), 4)
        self.assertEqual([group["memberCandidateKeys"] for group in groups], [["r|candidate_node|a", "r|candidate_node|b"], ["r|candidate_node|c", "r|candidate_node|d"]])

    def test_validator_exact_identity_and_superseded_evidence(self) -> None:
        """Authority A attaches only V10 exact identity and preserves source evidence."""

        base = {"requestID": "r", "sourceArtifactID": "paper", "recordKind": "candidate_node", "candidate": {"action": "propose_new", "operationalTargetID": "T", "existingNodeID": None}, "eligibilityDisposition": "eligible", "eligibilityReason": "validated"}
        first = {**base, "candidateKey": "r|candidate_node|a", "validationLineage": {"findings": []}, "evidenceOccurrences": [{"evidenceSpanID": "e1"}]}
        second = {**base, "candidateKey": "r|candidate_node|b", "eligibilityDisposition": "excluded", "eligibilityReason": "superseded", "validationLineage": {"supersededByRecordID": "a", "findings": [{"stage": "V10", "code": "EXACT_DUPLICATE_NODE", "expected": "a"}]}, "evidenceOccurrences": [{"evidenceSpanID": "e2"}]}
        retained, _ = pool.deduplicate([first], [second])
        self.assertEqual(retained[0]["memberCandidateKeys"], [first["candidateKey"], second["candidateKey"]])
        self.assertEqual({row["evidenceSpanID"] for row in retained[0]["evidenceOccurrences"]}, {"e1", "e2"})

    def test_possible_duplicate_pair_cannot_cross_source(self) -> None:
        """Even explicit pair lineage cannot create a cross source review group."""

        first = {"candidateKey": "r|candidate_node|a", "requestID": "r", "sourceArtifactID": "paper-a", "recordKind": "candidate_node", "candidate": {"action": "propose_new"}, "validationLineage": {"findings": []}, "eligibilityDisposition": "eligible", "eligibilityReason": "validated", "evidenceOccurrences": []}
        second = {**first, "candidateKey": "r|candidate_node|b", "sourceArtifactID": "paper-b", "eligibilityReason": "possible_local_duplicate", "validationLineage": {"findings": [{"stage": "V10", "code": "POSSIBLE_LOCAL_DUPLICATE", "expected": "a"}]}}
        with self.assertRaisesRegex(pool.Step8CandidatePoolError, "VALIDATOR_DUPLICATE_TARGET_DRIFT"):
            pool.deduplicate([first, second])

    def test_exact_relation_identity_after_node_representatives(self) -> None:
        """Authority C maps only nodes joined by A/B before relation identity."""

        def node(identifier: str) -> dict[str, object]:
            return {"candidateKey": f"r|candidate_node|{identifier}", "requestID": "r", "sourceArtifactID": "paper", "recordKind": "candidate_node", "candidate": {"action": "link_existing", "operationalTargetID": "T", "existingNodeID": "exact", "attributes": []}, "validationLineage": {"findings": []}, "eligibilityDisposition": "eligible", "eligibilityReason": "validated", "evidenceOccurrences": []}
        def edge(identifier: str, target: str) -> dict[str, object]:
            return {"candidateKey": f"r|candidate_edge|{identifier}", "requestID": "r", "sourceArtifactID": "paper", "recordKind": "candidate_edge", "candidate": {"action": "propose_edge", "operationalRelationID": "R", "relationScope": "intra_source", "source": {"referenceType": "deterministic_node", "referenceID": "paper", "artifactID": "paper"}, "target": {"referenceType": "candidate_node", "referenceID": target}}, "validationLineage": {"findings": []}, "eligibilityDisposition": "eligible", "eligibilityReason": "validated", "evidenceOccurrences": [{"evidenceSpanID": identifier}]}
        retained, _ = pool.deduplicate([node("n1"), node("n2"), edge("e1", "n1"), edge("e2", "n2")])
        relations = [item for item in retained if item["recordKind"] == "candidate_edge"]
        self.assertEqual(len(relations), 1)
        self.assertEqual({row["evidenceSpanID"] for row in relations[0]["evidenceOccurrences"]}, {"e1", "e2"})

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
        self.assertIn("authorizedContextSourceUnitIDs", item)
        self.assertTrue(all(item["c1Provenance"].get(field) for field in ("runID", "requestID", "outputID", "provider", "modelName", "modelVersion", "providerResponseID")))
        self.assertTrue(item["evidenceOccurrences"])

    def test_fails_closed_on_frozen_binding_drift(self) -> None:
        """A changed tracked binding cannot be used to construct a pool."""

        with patch.object(pool, "_hash", return_value="drift"):
            with self.assertRaisesRegex(pool.Step8CandidatePoolError, "FROZEN_BINDING_HASH_DRIFT"):
                pool.build()


if __name__ == "__main__":
    unittest.main()
