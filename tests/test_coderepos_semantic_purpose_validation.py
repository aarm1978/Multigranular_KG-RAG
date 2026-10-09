"""Four synthetic tests; no corpus, provider or graph processing."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos.source_units import read_repository_sources
from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary, validate_purpose_candidates


class PurposeValidationTests(unittest.TestCase):
    """Exercise vocabulary separation and source-bound proposal checks."""

    def setUp(self) -> None:
        """Build a trusted reader result from a synthetic Phase A README only."""
        text = "# Purpose\n\nThis repository processes café 🌊 scientific data. Repeat Repeat.\n"
        repo = {"repo_id": 17, "name": "Demo", "full_name": "Example/Demo",
                "archive": {"frozen_commit_sha": "a" * 40}, "files": {"downloaded": []},
                "readme": {"source_path": "README.md", "text": text, "present": True}}
        self.reader = read_repository_sources(repo, Path("/synthetic-unused-root"))
        self.unit = self.reader["sourceUnits"][0]
        self.owner = {key: self.unit[key] for key in ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")}
        self.candidate = {"candidateID": "purpose-1", "sourceID": "github:repo:17",
            "sourceUnitID": self.unit["sourceUnitID"], "relation": "hasPurpose", "inventoryId": "C-C07",
            "categoryKey": "data_processing", "targetID": "repo-purpose:1.0.0:data_processing",
            "evidence": [{"evidenceText": "This repository processes café 🌊 scientific data."}]}

    def validate(self, candidates=None, reader=None, owner=None) -> dict:
        """Check synthetic proposals using explicitly separate trusted inputs."""
        return validate_purpose_candidates(self.reader if reader is None else reader,
            self.unit["sourceUnitID"], [self.candidate] if candidates is None else candidates,
            accepted_repository=self.owner if owner is None else owner)

    def test_exact_vocabulary_and_stability(self) -> None:
        """Freeze exact category identities/labels independently of repositories."""
        expected = {
            "model_implementation": "Model implementation", "data_processing": "Data processing",
            "scientific_experimentation": "Scientific experimentation", "workflow_orchestration": "Workflow orchestration",
            "software_infrastructure": "Software infrastructure", "tutorial_demonstration": "Tutorial / demonstration"}
        records = purpose_vocabulary()
        self.assertEqual({r["categoryKey"]: r["label"] for r in records}, expected)
        self.assertEqual(len(records), 6)
        for record in records:
            self.assertEqual(record["nodeID"], "repo-purpose:1.0.0:" + record["categoryKey"])
            self.assertEqual((record["schemeID"], record["schemeVersion"]), ("ciroh-repository-purpose", "1.0.0"))
            self.assertEqual(record["extractionMethod"], "controlled_vocabulary_seed")
            self.assertNotIn("evidenceText", record)
        self.assertEqual(purpose_vocabulary(records), records)
        with self.assertRaises(ValueError):
            purpose_vocabulary([{"id": records[0]["nodeID"], "class": "Tool"}])
        records[0]["label"] = "changed"
        self.assertEqual(purpose_vocabulary()[0]["label"], "Model implementation")
        self.assertEqual(self.validate([])["vocabularyRecords"], purpose_vocabulary())

    def test_evidence_and_independent_endpoint_binding(self) -> None:
        """Bind evidence to original authority coordinates, not model offsets."""
        result = self.validate()
        check = result["candidateChecks"][0]
        self.assertEqual(check["status"], "validated")
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        self.assertFalse(result["graphAcceptance"])
        evidence = check["boundEvidence"][0]
        text = self.reader["authorities"][0]["text"]
        self.assertEqual(evidence["startOffsetInAuthority"], text.index("This repository"))
        self.assertEqual(evidence["startLine"], 3)
        self.assertEqual(text[evidence["startOffsetInAuthority"]:evidence["endOffsetInAuthority"]], evidence["evidenceText"])
        for key in ("path", "frozenCommitSha", "authorityTextSha256"):
            self.assertEqual(evidence[key], self.unit[key])
        for field, value in (("sourceID", "github:repo:99"), ("targetID", "repo-purpose:1.0.0:other"),
                             ("relation", "mentions"), ("startOffsetInAuthority", 0)):
            altered = {**self.candidate, field: value}
            self.assertEqual(self.validate([altered])["candidateChecks"][0]["status"], "rejected_invalid_assertion")

    def test_invalid_quotes_categories_duplicates_and_unresolved(self) -> None:
        """Preserve invalid and unresolved proposals without inventing categories."""
        for evidence in ([{"evidenceText": "fabricated"}], [{"evidenceText": "Repeat"}], [{}]):
            result = self.validate([{**self.candidate, "evidence": evidence}])
            self.assertEqual(result["candidateChecks"][0]["status"], "failed_source_or_evidence_binding")
        located = {**self.candidate, "evidence": [{"evidenceText": "Repeat", "locatorAnchor": "Repeat."}]}
        self.assertEqual(self.validate([located])["candidateChecks"][0]["status"], "validated")
        for change in ({"categoryKey": "other"}, {"evidence": []},
                       {"evidence": [{"evidenceText": "Repeat", "startOffsetInUnit": 0}]}):
            self.assertEqual(self.validate([{**self.candidate, **change}])["candidateChecks"][0]["status"], "rejected_invalid_assertion")
        duplicate = {**self.candidate, "candidateID": "purpose-2"}
        result = self.validate([self.candidate, duplicate])
        self.assertEqual([c["status"] for c in result["candidateChecks"]], ["validated", "rejected_invalid_assertion"])
        self.assertEqual(result["candidateChecks"][1]["duplicateOf"], "purpose-1")
        self.assertTrue(result["candidateChecks"][1]["boundEvidence"])
        for mode in ("unclassified", "ambiguous"):
            candidate = {**self.candidate, "classification": mode, "categoryKey": None, "targetID": None,
                         "reason": "Caller-supplied unresolved classification"}
            check = self.validate([candidate])["candidateChecks"][0]
            self.assertEqual(check["status"], "unresolved_category")
            self.assertEqual(check["originalCandidate"], candidate)

    def test_source_failures_review_immutability_and_zero_effects(self) -> None:
        """Source checks are separate; inputs and acquisition-integrity limits persist."""
        before = deepcopy((self.reader, self.candidate, self.owner))
        with patch("builtins.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.validate()
            self.assertEqual(result, self.validate())
        self.assertEqual((self.reader, self.candidate, self.owner), before)
        self.assertEqual(result["source"]["textIntegrityStatus"], "computed_only")
        for field, value in (("text", "tampered"), ("startOffsetInAuthority", 0), ("frozenCommitSha", "0" * 40)):
            reader = deepcopy(self.reader)
            reader["sourceUnits"][0][field] = value
            self.assertEqual(self.validate(reader=reader)["status"], "failed_source_or_evidence_binding")
        reader = deepcopy(self.reader)
        reader["authorities"][0]["text"] += "tampered"
        self.assertEqual(self.validate(reader=reader)["status"], "failed_source_or_evidence_binding")
        for status in ("needs_review", "failed_source_or_evidence_binding"):
            reader = deepcopy(self.reader)
            reader["diagnostics"].append({"path": "README.md", "cellIndex": None, "status": status, "reason": "synthetic"})
            checked = self.validate(reader=reader)
            self.assertEqual(checked["status"], status)
            self.assertEqual(checked["candidateChecks"], [])
        reader = deepcopy(self.reader)
        reader["sourceUnits"][0]["eligibility"] = "needs_review"
        self.assertEqual(self.validate(reader=reader)["status"], "needs_review")
        self.assertEqual(self.validate(owner={**self.owner, "repo_id": 99})["status"], "failed_source_or_evidence_binding")
        result["originalCandidates"][0]["categoryKey"] = "modified"
        self.assertEqual(self.candidate, before[1])
        self.assertNotIn("edges", result)
        self.assertNotIn("abstained_no_evidence", repr(result))


if __name__ == "__main__":
    unittest.main()
