"""Four synthetic checks for bounded HydroShare candidate validation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import io
import unittest
from unittest.mock import patch

from src.extraction.llm.datasets.candidate_validation import validate_variable_candidate
from src.extraction.llm.semantic_target_profiles import check_target, get_profile, ONTOLOGY_PATH
from src.extraction.llm.datasets.source_units import build_abstract_source_unit


class DatasetCandidateValidationTests(unittest.TestCase):
    """Verify only structural/provenance/literal-evidence behavior."""

    def setUp(self) -> None:
        """Prepare a synthetic abstract and independently supplied evidence."""
        self.owner = "a" * 32
        self.provenance = {"snapshotID": "synthetic-frozen-1", "sourceVersion": "v1"}
        self.unit = build_abstract_source_unit(
            {"resource_id": self.owner, "abstract": "Discharge is a measured variable. This dataset contains discharge. Flow Flow."},
            accepted_owner_id=self.owner, provenance=self.provenance,
        )["unit"]
        metadata = self.unit.to_record()
        self.payload = {
            "provenance": {key: metadata[key] for key in ("resource_id", "snapshotID", "sourceVersion", "sourceUnitID", "authorityTextSha256")},
            "node": {"candidateID": "variable-1", "class": "Variable", "inventoryId": "A-DOM04", "label": "Discharge",
                     "evidence": [{"evidenceText": "Discharge is a measured variable."}]},
            "edge": {"candidateID": "edge-1", "relation": "containsVariable", "inventoryId": "C-D16",
                     "sourceID": self.owner, "targetCandidateID": "variable-1",
                     "evidence": [{"evidenceText": "This dataset contains discharge."}]},
        }

    def validate(self, payload=None, unit=None, owner=None, provenance=None) -> dict:
        """Validate synthetic values without external authority or corpus reads."""
        return validate_variable_candidate(self.unit if unit is None else unit,
            self.payload if payload is None else payload, accepted_owner_id=self.owner if owner is None else owner,
            trusted_provenance=self.provenance if provenance is None else provenance)

    def test_valid_proposal_and_independent_literal_evidence(self) -> None:
        """Valid means structural/literal checks, never semantic or KG acceptance."""
        result = self.validate()
        self.assertEqual([c["disposition"] for c in result["candidates"]], ["validated", "validated"])
        node, edge = result["candidates"]
        for candidate in (node, edge):
            scope = candidate["targetProfileCheck"]
            self.assertTrue(scope["targetStructuralCompatibility"])
            self.assertTrue(scope["profileResult"]["structuralScopePass"])
            self.assertEqual(scope["pendingGates"], [])
            self.assertFalse(scope["kgAuthorization"])
        self.assertTrue(edge["targetProfileCheck"]["endpointsBound"])
        self.assertEqual(node["targetProfileCheck"]["profileResult"], check_target("hydroshare", "A-DOM04"))
        self.assertEqual(edge["targetProfileCheck"]["profileResult"], check_target(
            "hydroshare", "C-D16", relation_name="containsVariable",
            source_class_id="A-D01", target_class_id="A-DOM04"))
        self.assertFalse(result["kgAuthorization"])
        self.assertNotEqual(node["boundEvidence"][0]["evidenceText"], edge["boundEvidence"][0]["evidenceText"])
        self.assertEqual(edge["originalCandidate"]["sourceID"], self.owner)
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        self.assertFalse(result["graphAcceptance"])
        self.assertEqual(result["source"]["integrityStatus"], "computed_only")
        shared = deepcopy(self.payload)
        shared["edge"]["evidence"] = deepcopy(shared["node"]["evidence"])
        self.assertEqual(self.validate(shared)["candidates"][1]["disposition"], "validated")

    def test_disallowed_targets_directions_and_owners(self) -> None:
        """Reject other targets and direction/owner changes; retain unresolved IDs."""
        for kind, field, value in (("node", "class", "Concept"), ("node", "inventoryId", "A-DOM05"),
                                  ("edge", "relation", "mentions"), ("edge", "inventoryId", "D-26"),
                                  ("edge", "sourceID", "variable-1"), ("edge", "sourceID", "b" * 32)):
            with self.subTest(kind=kind, field=field):
                payload = deepcopy(self.payload)
                payload[kind][field] = value
                result = self.validate(payload)
                self.assertEqual(result["candidates"][0 if kind == "node" else 1]["disposition"], "rejected_invalid_assertion")
        for family, source, target in (("github", "A-D01", "A-DOM04"),
                                        ("hydroshare", "A-DOM04", "A-D01")):
            self.assertFalse(check_target(family, "C-D16", relation_name="containsVariable",
                source_class_id=source, target_class_id=target)["structuralScopePass"])
        payload = deepcopy(self.payload)
        payload["node"].update({"class": "RepositoryPurpose", "inventoryId": "A-C07"})
        checked = self.validate(payload)
        self.assertFalse(checked["candidates"][0]["targetProfileCheck"]["targetStructuralCompatibility"])
        self.assertEqual(checked["candidates"][1]["disposition"], "unresolved_endpoint")
        for target in (None, "missing-variable"):
            payload = deepcopy(self.payload)
            payload["edge"]["targetCandidateID"] = target
            self.assertEqual(self.validate(payload)["candidates"][1]["disposition"], "unresolved_endpoint")
        self.assertEqual(self.validate(owner="b" * 32)["status"], "failed_source_or_evidence_binding")

    def test_missing_ambiguous_evidence_and_provenance_failures(self) -> None:
        """Do not repair literals or infer semantic absence from invalid inputs."""
        for kind in ("node", "edge"):
            for evidence, disposition in (([], "rejected_invalid_assertion"),
                    ([{"evidenceText": "fabricated"}], "failed_source_or_evidence_binding"),
                    ([{"evidenceText": "Flow"}], "failed_source_or_evidence_binding")):
                payload = deepcopy(self.payload)
                payload[kind]["evidence"] = evidence
                self.assertEqual(self.validate(payload)["candidates"][0 if kind == "node" else 1]["disposition"], disposition)
        located = deepcopy(self.payload)
        located["node"]["evidence"] = [{"evidenceText": "Flow", "locatorAnchor": "Flow."}]
        self.assertEqual(self.validate(located)["candidates"][0]["disposition"], "validated")
        for changes in ({"text": "changed"}, {"authority_text_sha256": "0" * 64},
                        {"source_unit_id": "fake"}, {"snapshot_id": "other"},
                        {"expected_authority_text_sha256": "0" * 64}, {"artifact_family": "github"}):
            self.assertEqual(self.validate(unit=replace(self.unit, **changes))["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.validate(provenance={})["status"], "failed_source_or_evidence_binding")
        payload = deepcopy(self.payload)
        payload["provenance"]["authorityTextSha256"] = "0" * 64
        self.assertEqual(self.validate(payload)["status"], "failed_source_or_evidence_binding")
        self.assertEqual(self.validate(payload={})["status"], "failed_source_or_evidence_binding")

    def test_identity_immutability_and_zero_external_effects(self) -> None:
        """Stable IDs remain source-local; only the frozen ontology is read; no provider or graph IO."""
        profile = get_profile("hydroshare")
        profile["ownerClassID"] = "A-C01"
        with patch("src.extraction.llm.datasets.candidate_validation.get_profile", return_value=profile):
            checked = self.validate()
        self.assertEqual(checked["candidates"][1]["disposition"], "rejected_invalid_assertion")
        self.assertIn("target_profile_incompatible", repr(checked["diagnostics"]))
        original_open = io.open

        def authority_only(path, mode="r", *args, **kwargs):
            """Permit only read access to the frozen ontology; no corpus/graph IO."""
            self.assertEqual(Path(path), ONTOLOGY_PATH)
            self.assertEqual(mode, "rb")
            return original_open(path, mode, *args, **kwargs)

        before = deepcopy((self.unit, self.payload, self.provenance))
        with patch("io.open", side_effect=authority_only), patch("builtins.open", side_effect=AssertionError("No file IO")), \
             patch("socket.socket", side_effect=AssertionError("No network")):
            first = self.validate()
            second = self.validate()
        self.assertEqual(first, second)
        self.assertEqual((self.unit, self.payload, self.provenance), before)
        other_provenance = {**self.provenance, "snapshotID": "synthetic-frozen-2"}
        other = build_abstract_source_unit({"resource_id": self.owner, "abstract": self.unit.text},
            accepted_owner_id=self.owner, provenance=other_provenance)["unit"]
        payload = deepcopy(self.payload)
        payload["provenance"].update(snapshotID=other.snapshot_id, sourceUnitID=other.source_unit_id)
        changed = self.validate(payload, unit=other, provenance=other_provenance)
        self.assertNotEqual(first["candidates"][0]["sourceLocalCandidateID"], changed["candidates"][0]["sourceLocalCandidateID"])
        first["originalPayload"]["node"]["label"] = "mutated copy"
        self.assertEqual(self.payload, before[1])
        self.assertNotIn("nodes", second)
        self.assertNotIn("edges", second)
        self.assertNotIn("abstained_no_evidence", repr(second))


if __name__ == "__main__":
    unittest.main()
