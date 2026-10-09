"""Four synthetic checks for bounded HydroShare candidate validation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import io
import unittest
from unittest.mock import patch

from src.extraction.llm.datasets.candidate_validation import validate_variable_candidate, validate_dataset_candidates
from src.extraction.llm.semantic_target_profiles import check_target, get_profile, ONTOLOGY_PATH
from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units


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


class DatasetBatchValidationTests(unittest.TestCase):
    """Table-driven full-profile checks with only synthetic trusted sources."""

    CLASSES = {
        "A-DOM04": "Variable", "A-D12": "Measurement", "A-DOM02": "Tool",
        "A-DOM03a": "ProcessBasedModel", "A-DOM03b": "ConceptualModel",
        "A-DOM03c": "StatisticalModel", "A-DOM03d": "MLModel", "A-DOM03e": "AgentBasedModel",
        "A-C11": "Workflow", "A-C01": "Repository"}
    RELATIONS = {
        "C-D16": ("containsVariable", "A-DOM04"), "C-D17": ("hasMeasurement", "A-D12"),
        "C-D18": ("usesTool", "A-DOM02"), "C-D24": ("mentionsTool", "A-DOM02"),
        "C-D25": ("usesModel", "A-DOM03a"), "C-D26": ("mentionsModel", "A-DOM03b"),
        "C-D22": ("explainsWorkflow", "A-C11"), "D-17": ("generatedBy", "A-C01")}

    def setUp(self) -> None:
        """Build immutable synthetic abstract/README authorities and exact endpoints."""
        self.owner = "resource-1"
        self.provenance = {"snapshotID": "frozen-1", "sourceVersion": "v1"}
        text = "Café 🌊 documents " + ", ".join("[" + name + "]" for name in self.CLASSES.values()) + ". "
        text += "Dataset " + ", ".join(r[0] for r in self.RELATIONS.values()) + ". Repeat Repeat."
        self.unit = build_abstract_source_unit({"resource_id": self.owner, "abstract": text},
            accepted_owner_id=self.owner, provenance=self.provenance)["unit"]
        self.readme = read_readme_source_units({"resource_id": self.owner, "source_path": "README.md", "text": "# Data\n" + text},
            accepted_owner_id=self.owner, provenance={**self.provenance, "sourceVerified": True})
        self.repo = {"endpointID": "github:repo:17", "class": "Repository", "inventoryId": "A-C01"}
        self.payload = {"candidateNodes": [self.node(i) for i in self.CLASSES],
                        "candidateEdges": [self.edge(i) for i in self.RELATIONS]}

    def fragment(self, quote: str, readme: bool = False, **extra) -> dict:
        """Supply only an exact unit reference, literal and optional contribution."""
        return {"sourceUnitID": self.readme["sourceUnits"][0]["sourceUnitID"] if readme else self.unit.source_unit_id,
                "evidenceText": quote, **extra}

    def node(self, identifier: str, cid=None) -> dict:
        """Create one source-local proposal or exact Repository endpoint reference."""
        row = {"candidateID": cid or identifier, "inventoryId": identifier, "class": self.CLASSES[identifier],
               "label": self.CLASSES[identifier], "evidence": [self.fragment("[" + self.CLASSES[identifier] + "]", identifier == "A-D12")]}
        if identifier == "A-C01":
            row["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": self.repo["endpointID"]}
        return row

    def edge(self, identifier: str, cid=None) -> dict:
        """Keep relation evidence independent of its target node evidence."""
        name, target = self.RELATIONS[identifier]
        return {"candidateID": cid or identifier, "inventoryId": identifier, "relation": name,
            "source": {"referenceType": "accepted_endpoint", "referenceID": self.owner},
            "target": {"referenceType": "candidate_node", "referenceID": target},
            "evidence": [self.fragment(name, identifier == "C-D17")]}

    def validate(self, payload=None, **kwargs) -> dict:
        """Validate a synthetic batch with independent trusted context."""
        return validate_dataset_candidates(self.payload if payload is None else payload,
            accepted_owner_id=self.owner, trusted_provenance=self.provenance,
            abstract_units=kwargs.pop("abstract_units", [self.unit]), readme_results=kwargs.pop("readme_results", [self.readme]),
            accepted_endpoints=kwargs.pop("accepted_endpoints", [self.repo]), **kwargs)

    def test_complete_allowlist_and_independent_evidence(self) -> None:
        """Every active inventory ID is exercised; Measurement semantics stay pending."""
        result = self.validate()
        checks = {r["candidateID"]: r for r in result["candidateChecks"]}
        profile = get_profile("hydroshare")
        self.assertEqual(set(self.CLASSES), set(profile["entities"]))
        self.assertEqual(set(self.RELATIONS), set(profile["relations"]))
        for identifier in self.CLASSES:
            expected = "unresolved_condition" if identifier == "A-D12" else "suppressed_duplicate" if identifier == "A-C01" else "validated"
            self.assertEqual(checks[identifier]["disposition"], expected, identifier)
        for identifier in self.RELATIONS:
            self.assertEqual(checks[identifier]["disposition"], "unresolved_endpoint" if identifier == "C-D17" else "validated", identifier)
            self.assertNotEqual(checks[identifier]["boundEvidence"][0]["evidenceText"],
                               checks[self.RELATIONS[identifier][1]]["boundEvidence"][0]["evidenceText"])
        self.assertEqual(checks["A-D12"]["targetProfileCheck"]["pendingGates"], ["explicit_readme_measurement"])
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        self.assertFalse(result["kgAuthorization"])
        self.assertTrue(result["inputComplete"])
        # Check model inheritance against both model predicates for all concrete subtypes.
        payload = deepcopy(self.payload)
        payload["candidateEdges"] = []
        for model in ("A-DOM03a", "A-DOM03b", "A-DOM03c", "A-DOM03d", "A-DOM03e"):
            for relation in ("C-D25", "C-D26"):
                edge = self.edge(relation, model + relation)
                edge["target"]["referenceID"] = model
                payload["candidateEdges"].append(edge)
        self.assertTrue(all(r["disposition"] == "validated" for r in self.validate(payload)["candidateChecks"] if r["kind"] == "edge"))

    def test_wrong_signatures_and_forbidden_targets(self) -> None:
        """Wrong direction, class, inactive and pipeline IDs fail locally."""
        payload = {"candidateNodes": [self.node("A-DOM04"), self.node("A-DOM02")], "candidateEdges": []}
        for index, (identifier, name) in enumerate((("A-D13", "DataService"), ("A-DOM03", "ComputationalModel"),
                                                   ("A-C07", "RepositoryPurpose"))):
            row = self.node("A-DOM04", "bad-node-" + str(index))
            row.update(inventoryId=identifier, **{"class": name})
            payload["candidateNodes"].append(row)
        for index, identifier in enumerate(("C-D16", "D-26", "C-D29", "C-C07")):
            row = self.edge("C-D16", "bad-edge-" + str(index))
            row["inventoryId"] = identifier
            row["target"]["referenceID"] = "A-DOM02"
            payload["candidateEdges"].append(row)
        reversed_edge = self.edge("C-D16", "reversed")
        reversed_edge["source"], reversed_edge["target"] = reversed_edge["target"], reversed_edge["source"]
        payload["candidateEdges"].append(reversed_edge)
        checks = self.validate(payload)["candidateChecks"]
        self.assertEqual([c["disposition"] for c in checks[:2]], ["validated", "validated"])
        self.assertTrue(all(c["disposition"] == "rejected_invalid_assertion" for c in checks[2:]))

    def test_readme_gating_and_source_failure_isolation(self) -> None:
        """README channel is necessary but never proves an individuating observation."""
        payload = {"candidateNodes": [self.node("A-D12"), self.node("A-DOM04")], "candidateEdges": [self.edge("C-D16"), self.edge("C-D17")]}
        payload["candidateNodes"][0]["evidence"] = [self.fragment("[Measurement]")]
        payload["candidateEdges"][1]["evidence"] = [self.fragment("hasMeasurement")]
        checks = {c["candidateID"]: c for c in self.validate(payload)["candidateChecks"]}
        self.assertEqual(checks["A-D12"]["disposition"], "rejected_invalid_assertion")
        self.assertEqual(checks["C-D17"]["disposition"], "rejected_invalid_assertion")
        self.assertEqual(checks["C-D16"]["disposition"], "validated")
        payload["candidateNodes"][0] = self.node("A-D12")
        payload["candidateEdges"][1] = self.edge("C-D17")
        for field, value in (("authorityTextSha256", "0" * 64), ("resource_id", "other"), ("snapshotID", "other")):
            bad = deepcopy(self.readme)
            bad["authority"][field] = value
            result = self.validate(payload, readme_results=[bad])
            checks = {c["candidateID"]: c for c in result["candidateChecks"]}
            self.assertFalse(result["inputComplete"])
            self.assertEqual(checks["A-D12"]["disposition"], "failed_source_or_evidence_binding")
            self.assertEqual(checks["A-DOM04"]["disposition"], "validated")
            self.assertEqual(checks["C-D16"]["disposition"], "validated")
        # An accepted Measurement endpoint still does not establish the new relation's semantics.
        edge = self.edge("C-D17")
        edge["target"] = {"referenceType": "accepted_endpoint", "referenceID": "measurement-accepted"}
        accepted = {"assertionID": "accepted-measurement-edge", "inventoryId": "C-D17", "relation": "hasMeasurement",
                    "sourceID": self.owner, "targetID": "measurement-accepted"}
        held = self.validate({"candidateNodes": [], "candidateEdges": [edge]},
            accepted_endpoints=[{"endpointID": "measurement-accepted", "inventoryId": "A-D12", "class": "Measurement"}],
            accepted_assertions=[accepted])["candidateChecks"][0]
        self.assertEqual(held["disposition"], "unresolved_condition")
        self.assertTrue(held["suppressedDuplicate"])
        self.assertTrue(held["boundEvidence"])
        payload["candidateNodes"][0]["gates"] = {"explicit_readme_measurement": True}
        checked = self.validate(payload)["candidateChecks"][0]
        self.assertEqual(checked["disposition"], "rejected_invalid_assertion")
        self.assertTrue(checked["targetProfileCheck"]["pendingGates"])

    def test_exact_endpoints_authorized_stubs_and_duplicate_citations(self) -> None:
        """Reuse exact identities only; suppress duplicates while preserving every quote."""
        payload = {"candidateNodes": [self.node("A-C01")], "candidateEdges": [self.edge("D-17"), self.edge("D-17", "again")]}
        accepted = {"assertionID": "accepted-edge-1", "inventoryId": "D-17", "relation": "generatedBy",
                    "sourceID": self.owner, "targetID": self.repo["endpointID"]}
        result = self.validate(payload, accepted_assertions=[accepted])
        self.assertTrue(all(c["disposition"] == "suppressed_duplicate" for c in result["candidateChecks"]))
        self.assertTrue(all(c["boundEvidence"] for c in result["candidateChecks"]))
        self.assertEqual(result["candidateChecks"][2]["duplicateOf"], ["accepted-edge-1"])
        result = self.validate(payload)
        self.assertEqual(result["candidateChecks"][1]["disposition"], "validated")
        self.assertEqual(result["candidateChecks"][2]["duplicateOf"], ["D-17"])
        for endpoints in ([], [self.repo, self.repo]):
            result = self.validate(payload, accepted_endpoints=endpoints)
            self.assertEqual(result["candidateChecks"][0]["disposition"], "unresolved_endpoint")
            self.assertEqual(result["candidateChecks"][1]["disposition"], "unresolved_endpoint")
        stub = {"endpointID": "source-scoped-repo-1", "inventoryId": "A-C01", "class": "Repository",
                "resource_id": self.owner, **self.provenance, "authorizationID": "trusted-authorization-1"}
        payload["candidateNodes"][0]["endpoint"] = {"referenceType": "authorized_stub", "referenceID": stub["endpointID"]}
        self.assertEqual(self.validate(payload, authorized_stubs=[stub])["candidateChecks"][0]["disposition"], "validated")
        for changes in ({"resource_id": "wrong"}, {"authorizationID": ""}, {"snapshotID": "wrong"}):
            self.assertEqual(self.validate(payload, authorized_stubs=[{**stub, **changes}])["candidateChecks"][0]["disposition"], "unresolved_endpoint")
        # The model cannot invent a Repository occurrence or authorize its own stub.
        del payload["candidateNodes"][0]["endpoint"]
        self.assertEqual(self.validate(payload)["candidateChecks"][0]["disposition"], "unresolved_endpoint")

    def test_mixed_failures_dependencies_and_global_unidentifiable_inputs(self) -> None:
        """Isolate local evidence failure and keep only true node dependencies held."""
        payload = {"candidateNodes": [self.node("A-DOM04"), self.node("A-DOM02")],
                   "candidateEdges": [self.edge("C-D16"), self.edge("C-D18"), self.edge("C-D24")]}
        payload["candidateNodes"][1]["evidence"] = [self.fragment("fabricated")]
        payload["candidateEdges"][2]["evidence"] = [self.fragment("Repeat")]
        result = self.validate(payload)
        checks = {c["candidateID"]: c for c in result["candidateChecks"]}
        self.assertEqual(checks["A-DOM04"]["disposition"], "validated")
        self.assertEqual(checks["C-D16"]["disposition"], "validated")
        self.assertEqual(checks["A-DOM02"]["disposition"], "failed_source_or_evidence_binding")
        self.assertEqual(checks["C-D18"]["disposition"], "unresolved_endpoint")
        self.assertEqual(checks["C-D24"]["disposition"], "failed_source_or_evidence_binding")
        self.assertIn("dependent_node_not_validated", repr(checks["C-D24"]["findings"]))
        self.assertEqual(checks["C-D18"]["dependencies"], ["A-DOM02"])
        for malformed in ({}, {"candidateNodes": [None], "candidateEdges": []},
                          {"candidateNodes": [self.node("A-DOM04"), self.node("A-DOM04")], "candidateEdges": []}):
            checked = self.validate(malformed)
            self.assertEqual(checked["status"], "processing_failed")
            self.assertEqual(checked["candidateChecks"], [])
        invalid = {"candidateNodes": [self.node("A-DOM04"), self.node("A-DOM02", "no-evidence")],
                   "candidateEdges": [self.edge("C-D16"), self.edge("C-D16", "malformed-reference")]}
        invalid["candidateNodes"][1]["evidence"] = []
        invalid["candidateEdges"][1]["target"]["referenceType"] = []
        checks = self.validate(invalid)["candidateChecks"]
        self.assertEqual([r["disposition"] for r in checks],
            ["validated", "rejected_invalid_assertion", "validated", "unresolved_endpoint"])
        invalid["candidateNodes"][0]["evidence"][0]["startLine"] = 1
        self.assertEqual(self.validate(invalid)["candidateChecks"][0]["disposition"], "rejected_invalid_assertion")
        # An exact accepted endpoint is independent of a failed candidate with the same type.
        payload["candidateEdges"][1]["target"] = {"referenceType": "accepted_endpoint", "referenceID": "tool-accepted"}
        endpoints = [self.repo, {"endpointID": "tool-accepted", "inventoryId": "A-DOM02", "class": "Tool"}]
        self.assertEqual(self.validate(payload, accepted_endpoints=endpoints)["candidateChecks"][3]["disposition"], "validated")

    def test_originals_coordinates_identity_and_no_external_effects(self) -> None:
        """Keep original payloads, repeated citations, coordinates and stable IDs."""
        payload = {"candidateNodes": [self.node("A-DOM04")], "candidateEdges": [self.edge("C-D16")]}
        payload["candidateNodes"][0]["evidence"] = [self.fragment("Café 🌊", contribution="context"),
            self.fragment("[Variable]", readme=True, contribution="quantity"), self.fragment("[Variable]", readme=True, contribution="repeated quote")]
        before = deepcopy((payload, self.unit, self.readme, self.provenance, self.repo))
        original_open = io.open

        def authority_only(path, mode="r", *args, **kwargs):
            """Permit only frozen ontology reads, never corpus/graph/provider IO."""
            self.assertEqual(Path(path), ONTOLOGY_PATH)
            self.assertEqual(mode, "rb")
            return original_open(path, mode, *args, **kwargs)

        with patch("io.open", side_effect=authority_only), patch("builtins.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            first = self.validate(payload)
            self.assertEqual(first, self.validate(payload))
        self.assertEqual(before, (payload, self.unit, self.readme, self.provenance, self.repo))
        spans = first["candidateChecks"][0]["boundEvidence"]
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0]["endOffsetInAuthority"] - spans[0]["startOffsetInAuthority"], len("Café 🌊"))
        for span in spans:
            text = self.unit.text if span["sourceField"] == "abstract" else self.readme["authority"]["text"]
            self.assertEqual(text[span["startOffsetInAuthority"]:span["endOffsetInAuthority"]], span["evidenceText"])
            self.assertEqual(span["sourceVersion"], "v1")
        self.assertEqual(spans[1]["evidenceHash"], spans[2]["evidenceHash"])
        changed = deepcopy(payload)
        changed["candidateNodes"][0]["candidateID"] = "different"
        self.assertNotEqual(first["candidateChecks"][0]["sourceLocalCandidateID"], self.validate(changed)["candidateChecks"][0]["sourceLocalCandidateID"])
        first["originalPayload"]["candidateNodes"][0]["label"] = "changed copy"
        self.assertEqual(before[0], payload)
        self.assertNotIn("abstained_no_evidence", repr(first))
        self.assertFalse(first["kgAuthorization"])


if __name__ == "__main__":
    unittest.main()
