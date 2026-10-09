"""Synthetic full-profile GitHub batch validation; no corpus/provider execution."""
from __future__ import annotations

from copy import deepcopy
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from src.extraction.llm.coderepos.candidate_validation import validate_repository_candidates
from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary
from src.extraction.llm.coderepos.source_units import read_repository_sources
from src.extraction.llm.semantic_target_profiles import ONTOLOGY_PATH, get_profile


class RepositoryBatchTests(unittest.TestCase):
    """Exercise exact endpoints, pending gates and independent candidate survival."""

    CLASSES = {"A-DOM02": "Tool", "A-DOM03a": "ProcessBasedModel", "A-DOM03b": "ConceptualModel",
        "A-DOM03c": "StatisticalModel", "A-DOM03d": "MLModel", "A-DOM03e": "AgentBasedModel",
        "A-D01": "DatasetResource", "A-C11": "Workflow", "A-C08": "Function", "A-DOM13": "Algorithm",
        "A-C10": "ModelVersion", "A-P13": "Method"}
    RELATIONS = {"C-C07": ("hasPurpose", "A-C07"), "C-C11": ("usesTool", "A-DOM02"),
        "C-C22": ("mentionsTool", "A-DOM02"), "D-22": ("implementedBy", "A-DOM02"),
        "C-C21": ("usesModel", "A-DOM03a"), "C-C23": ("mentionsModel", "A-DOM03b"),
        "C-C15": ("usesDataset", "A-D01"), "C-C10": ("explainsWorkflow", "A-C11"),
        "C-C08": ("describesFunction", "A-C08"), "C-C20": ("describesAlgorithm", "A-DOM13"),
        "C-C09": ("hasModelVersion", "A-C10"), "C-C16": ("implementsMethod", "A-P13")}

    def setUp(self) -> None:
        """Create only an in-memory Phase A README with two independent units."""
        self.text = "# Entities\nCafé 🌊 describes " + ", ".join("[" + n + "]" for n in self.CLASSES.values()) + ". Repeat Repeat.\n\n"
        self.text += "# Relations\nThis repository documents " + ", ".join(n for n, _ in self.RELATIONS.values()) + ".\n"
        repo = {"repo_id": 17, "name": "Demo", "full_name": "Example/Demo", "archive": {"frozen_commit_sha": "a" * 40},
            "readme": {"source_path": "README.md", "text": self.text}, "files": {"downloaded": []}}
        self.reader = read_repository_sources(repo, Path("/synthetic-unused"))
        self.owner = {k: self.reader["sourceUnits"][0][k] for k in ("canonicalArtifactID", "repo_id", "full_name", "frozenCommitSha")}
        self.endpoints = [{"endpointID": "dataset-exact", "inventoryId": "A-D01", "class": "DatasetResource"},
                          {"endpointID": "publication-method-exact", "inventoryId": "A-P13", "class": "Method"}]
        self.payload = {"candidateNodes": [self.node(i) for i in self.CLASSES],
                        "candidateEdges": [self.edge(i) for i in self.RELATIONS]}

    def fragment(self, quote: str, **extra) -> dict:
        """Reference one exact source unit; no model-authored coordinates."""
        unit = next(u for u in self.reader["sourceUnits"] if quote in u["text"])
        return {"sourceUnitID": unit["sourceUnitID"], "evidenceText": quote, **extra}

    def node(self, identifier: str, cid=None) -> dict:
        """Create local candidates except source-exact DatasetResource/Method endpoints."""
        row = {"candidateID": cid or identifier, "inventoryId": identifier, "class": self.CLASSES[identifier],
               "label": self.CLASSES[identifier], "evidence": [self.fragment("[" + self.CLASSES[identifier] + "]")]}
        if identifier in {"A-D01", "A-P13"}:
            row["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": "dataset-exact" if identifier == "A-D01" else "publication-method-exact"}
        if identifier == "A-C10":
            row["productRepositoryID"] = self.owner["canonicalArtifactID"]
        return row

    def edge(self, identifier: str, cid=None) -> dict:
        """Give each relation its own quotation and explicit direction."""
        name, target = self.RELATIONS[identifier]
        row = {"candidateID": cid or identifier, "inventoryId": identifier, "relation": name,
               "source": {"referenceType": "accepted_endpoint", "referenceID": self.owner["canonicalArtifactID"]},
               "target": {"referenceType": "candidate_node", "referenceID": target}, "evidence": [self.fragment(name)]}
        if identifier == "D-22":
            row["source"], row["target"] = row["target"], row["source"]
        if identifier == "C-C07":
            row["categoryKey"] = "data_processing"
            row["target"] = {"referenceType": "accepted_endpoint", "referenceID": "repo-purpose:1.0.0:data_processing"}
        return row

    def validate(self, payload=None, **kw) -> dict:
        """Supply trusted owner/endpoints separately from untrusted proposals."""
        return validate_repository_candidates(kw.pop("reader", self.reader), self.payload if payload is None else payload,
            accepted_repository=self.owner, accepted_endpoints=kw.pop("accepted_endpoints", self.endpoints), **kw)

    def test_complete_allowlist_signatures_and_seed_stability(self) -> None:
        """Cover every frozen class/relation without making gates true."""
        result = self.validate()
        profile = get_profile("github")
        self.assertEqual(set(profile["entities"]), set(self.CLASSES) | {"A-C07"})
        self.assertEqual(set(profile["relations"]), set(self.RELATIONS))
        self.assertEqual(result["vocabularyRecords"], purpose_vocabulary())
        checks = {r["candidateID"]: r for r in result["candidateChecks"]}
        conditional_nodes = {"A-C08", "A-DOM13", "A-C10", "A-P13"}
        for identifier in self.CLASSES:
            expected = "unresolved_condition" if identifier in conditional_nodes else "suppressed_duplicate" if identifier == "A-D01" else "validated"
            self.assertEqual(checks[identifier]["disposition"], expected, identifier)
        for identifier in self.RELATIONS:
            expected = "unresolved_condition" if identifier == "C-C07" else "unresolved_endpoint" if identifier in {"C-C08", "C-C20", "C-C09", "C-C16"} else "validated"
            self.assertEqual(checks[identifier]["disposition"], expected, identifier)
            self.assertTrue(checks[identifier]["boundEvidence"])
        self.assertEqual(checks["C-C07"]["purposeChecks"][0]["result"]["candidateChecks"][0]["status"], "validated")
        self.assertEqual(checks["C-C07"]["targetProfileCheck"]["pendingGates"],
            ["repository_specific_purpose_evidence", "approved_category_endpoint"])
        payload = {"candidateNodes": [self.node(i) for i in self.CLASSES if i.startswith("A-DOM03")], "candidateEdges": []}
        for model in ("A-DOM03a", "A-DOM03b", "A-DOM03c", "A-DOM03d", "A-DOM03e"):
            for relation in ("C-C21", "C-C23", "D-22"):
                row = self.edge(relation, model + relation)
                row["source" if relation == "D-22" else "target"]["referenceID"] = model
                payload["candidateEdges"].append(row)
        self.assertTrue(all(c["disposition"] == "validated" for c in self.validate(payload)["candidateChecks"]))

    def test_wrong_targets_endpoints_and_direction(self) -> None:
        """Reject unsupported IDs, wrong signatures, invented identities and seed proposals."""
        payload = {"candidateNodes": [self.node("A-DOM02")], "candidateEdges": []}
        for index, (identifier, name) in enumerate((("A-C07", "RepositoryPurpose"), ("A-DOM03", "ComputationalModel"), ("A-D13", "DataService"))):
            row = self.node("A-DOM02", "bad-node-" + str(index))
            row.update(inventoryId=identifier, **{"class": name})
            payload["candidateNodes"].append(row)
        for index, identifier in enumerate(("D-26", "C-D26", "C-D29", "C-C15")):
            row = self.edge("C-C11", "bad-edge-" + str(index))
            row["inventoryId"] = identifier
            payload["candidateEdges"].append(row)
        row = self.edge("D-22", "reversed")
        row["source"], row["target"] = row["target"], row["source"]
        payload["candidateEdges"].append(row)
        checks = self.validate(payload)["candidateChecks"]
        self.assertEqual(checks[0]["disposition"], "validated")
        self.assertTrue(all(c["disposition"] == "rejected_invalid_assertion" for c in checks[1:]))
        for endpoints in ([], [self.endpoints[0], self.endpoints[0]]):
            checks = self.validate({"candidateNodes": [self.node("A-D01")], "candidateEdges": [self.edge("C-C15")]}, accepted_endpoints=endpoints)["candidateChecks"]
            self.assertTrue(all(c["disposition"] == "unresolved_endpoint" for c in checks))
        row = self.node("A-D01")
        del row["endpoint"]
        self.assertEqual(self.validate({"candidateNodes": [row], "candidateEdges": []})["candidateChecks"][0]["disposition"], "unresolved_endpoint")

    def test_conditional_own_product_and_method_nonresolution(self) -> None:
        """Neither own-ID claims, literal support nor trusted Method typing grant acceptance."""
        version = self.node("A-C10")
        version["productRepositoryID"] = "dependency-repo"
        self.assertEqual(self.validate({"candidateNodes": [version], "candidateEdges": []})["candidateChecks"][0]["disposition"], "rejected_invalid_assertion")
        version["productRepositoryID"] = self.owner["canonicalArtifactID"]
        version["gates"] = {"own_repository_product": True}
        checked = self.validate({"candidateNodes": [version], "candidateEdges": []})["candidateChecks"][0]
        self.assertEqual(checked["disposition"], "rejected_invalid_assertion")
        self.assertIn("own_repository_product", checked["targetProfileCheck"]["pendingGates"])
        row = self.edge("C-C16")
        row["target"] = {"referenceType": "accepted_endpoint", "referenceID": "publication-method-exact"}
        row.update(methodSurfaceForm="named method", candidatePublicationIdentifier="doi:synthetic")
        result = self.validate({"candidateNodes": [], "candidateEdges": [row]})["candidateChecks"][0]
        self.assertEqual(result["disposition"], "unresolved_endpoint")
        self.assertEqual(result["resolutionStatus"], "unresolved_endpoint_non_KG")
        self.assertTrue(result["targetProfileCheck"]["pendingGates"])
        self.assertEqual(result["originalCandidate"], row)
        accepted = {"assertionID": "method-edge-already-accepted", "inventoryId": "C-C16", "relation": "implementsMethod",
                    "sourceID": self.owner["canonicalArtifactID"], "targetID": "publication-method-exact"}
        duplicate = self.validate({"candidateNodes": [], "candidateEdges": [row]}, accepted_assertions=[accepted])["candidateChecks"][0]
        self.assertTrue(duplicate["suppressedDuplicate"])
        self.assertEqual(duplicate["disposition"], "unresolved_endpoint")
        self.assertFalse(duplicate["kgAuthorization"])
        row["target"]["referenceID"] = "unknown-method"
        self.assertIn("trusted_endpoint_missing_invalid_or_ambiguous", repr(self.validate({"candidateNodes": [], "candidateEdges": [row]})))
        # The formal Tool -> Method union branch is inspected but still unresolved.
        row["target"]["referenceID"] = "publication-method-exact"
        row["source"] = {"referenceType": "candidate_node", "referenceID": "A-DOM02"}
        checked = self.validate({"candidateNodes": [self.node("A-DOM02")], "candidateEdges": [row]})["candidateChecks"][1]
        self.assertTrue(checked["targetProfileCheck"]["targetStructuralCompatibility"])
        self.assertEqual(checked["disposition"], "unresolved_endpoint")

    def test_purpose_delegation_unresolved_categories_and_duplicates(self) -> None:
        """Reuse six seeds, preserve purpose dispositions/gates and every duplicate citation."""
        row = self.edge("C-C07")
        duplicate = deepcopy(row)
        duplicate["candidateID"] = "purpose-again"
        accepted = {"assertionID": "accepted-purpose", "inventoryId": "C-C07", "relation": "hasPurpose",
                    "sourceID": self.owner["canonicalArtifactID"], "targetID": "repo-purpose:1.0.0:data_processing"}
        result = self.validate({"candidateNodes": [], "candidateEdges": [row, duplicate]}, accepted_assertions=[accepted])
        for record in result["candidateChecks"]:
            self.assertEqual(record["disposition"], "unresolved_condition")
            self.assertTrue(record["suppressedDuplicate"])
            self.assertEqual(record["duplicateOf"], ["accepted-purpose"])
            self.assertTrue(record["boundEvidence"])
        for classification in ("unclassified", "ambiguous"):
            held = {**row, "classification": classification, "categoryKey": None, "target": None, "reason": "unresolved synthetic category"}
            result = self.validate({"candidateNodes": [], "candidateEdges": [held]})["candidateChecks"][0]
            self.assertEqual(result["disposition"], "unresolved_category")
        bad = {**row, "categoryKey": "other"}
        self.assertEqual(self.validate({"candidateNodes": [], "candidateEdges": [bad]})["candidateChecks"][0]["disposition"], "rejected_invalid_assertion")
        # Exact accepted node/edge identity suppresses only equivalent assertions.
        tool = {"endpointID": "tool-exact", "inventoryId": "A-DOM02", "class": "Tool"}
        node = self.node("A-DOM02")
        node["endpoint"] = {"referenceType": "accepted_endpoint", "referenceID": "tool-exact"}
        edge = self.edge("C-C11")
        duplicate = {**deepcopy(edge), "candidateID": "uses-again"}
        result = self.validate({"candidateNodes": [node], "candidateEdges": [edge, duplicate, self.edge("C-C22")]}, accepted_endpoints=[tool])
        self.assertEqual([c["disposition"] for c in result["candidateChecks"]], ["suppressed_duplicate", "validated", "suppressed_duplicate", "validated"])
        self.assertTrue(all(c["boundEvidence"] for c in result["candidateChecks"]))

    def test_failure_isolation_scoped_sources_and_global_envelopes(self) -> None:
        """Only true dependents fail; unrelated source warnings remain diagnostic."""
        tool, model = self.node("A-DOM02"), self.node("A-DOM03a")
        tool["evidence"][0]["evidenceText"] = "fabricated"
        payload = {"candidateNodes": [tool, model], "candidateEdges": [self.edge("C-C11"), self.edge("C-C21"), self.edge("C-C07")]}
        reader = deepcopy(self.reader)
        reader["diagnostics"] = [{"status": "needs_review", "path": "README.md", "startLine": 1, "endLine": 1, "reason": "heading only"},
                                 {"status": "failed_source_or_evidence_binding", "path": "missing.md", "reason": "file missing"}]
        result = self.validate(payload, reader=reader)
        self.assertFalse(result["inputComplete"])
        self.assertEqual(result["sourceDiagnostics"], reader["diagnostics"])
        self.assertEqual([r["disposition"] for r in result["candidateChecks"]],
                         ["failed_source_or_evidence_binding", "validated", "unresolved_endpoint", "validated", "unresolved_condition"])
        self.assertEqual(result["candidateChecks"][2]["dependencies"], ["A-DOM02"])
        # A damaged first unit does not poison purpose evidence in the second unit.
        damaged = deepcopy(self.reader)
        damaged["sourceUnits"][0]["text"] = "tampered"
        checked = self.validate(payload, reader=damaged)
        self.assertEqual(checked["candidateChecks"][-1]["disposition"], "unresolved_condition")
        self.assertFalse(checked["inputComplete"])
        for malformed in ({}, {"candidateNodes": [None], "candidateEdges": []},
                          {"candidateNodes": [model, model], "candidateEdges": []}):
            result = self.validate(malformed)
            self.assertEqual(result["status"], "processing_failed")
            self.assertEqual(result["candidateChecks"], [])
        # Unknown/global scope must hold even otherwise valid purpose evidence.
        reader["diagnostics"] = [{"status": "needs_review", "reason": "unscoped"}]
        self.assertEqual(self.validate({"candidateNodes": [], "candidateEdges": [self.edge("C-C07")]}, reader=reader)["candidateChecks"][0]["disposition"], "needs_review")

    def test_literals_identity_immutability_and_zero_effects(self) -> None:
        """No evidence repair, metadata injection, file IO or provider effects."""
        row = self.node("A-DOM02")
        row["evidence"] = [self.fragment("Café 🌊", contribution="context"),
                           self.fragment("usesTool", contribution="role"), self.fragment("usesTool", contribution="duplicate citation")]
        payload = {"candidateNodes": [row], "candidateEdges": [self.edge("C-C11")]}
        before = deepcopy((payload, self.reader, self.owner, self.endpoints))
        original_open = io.open

        def ontology_only(path, mode="r", *args, **kwargs):
            """Permit frozen ontology reads only."""
            self.assertEqual(Path(path), ONTOLOGY_PATH)
            self.assertEqual(mode, "rb")
            return original_open(path, mode, *args, **kwargs)

        with patch("io.open", side_effect=ontology_only), patch("builtins.open", side_effect=AssertionError("No IO")), patch("socket.socket", side_effect=AssertionError("No network")):
            result = self.validate(payload)
            self.assertEqual(result, self.validate(payload))
        self.assertEqual(before, (payload, self.reader, self.owner, self.endpoints))
        spans = result["candidateChecks"][0]["boundEvidence"]
        self.assertEqual(len(spans), 3)
        for span in spans:
            self.assertEqual(self.text[span["startOffsetInAuthority"]:span["endOffsetInAuthority"]], span["evidenceText"])
            self.assertEqual(span["frozenCommitSha"], self.owner["frozenCommitSha"])
            self.assertTrue(span["authorityTextSha256"])
        self.assertEqual(spans[1]["evidenceHash"], spans[2]["evidenceHash"])
        self.assertFalse(result["kgAuthorization"])
        self.assertEqual(result["semanticStatus"], "not_evaluated")
        for evidence in ([], [self.fragment("Repeat")], [self.fragment("Repeat", startLine=2)]):
            altered = {**row, "evidence": evidence}
            checked = self.validate({"candidateNodes": [altered], "candidateEdges": []})["candidateChecks"][0]
            self.assertNotEqual(checked["disposition"], "validated")
        located = {**row, "evidence": [self.fragment("Repeat", locatorAnchor="Repeat.")]}
        self.assertEqual(self.validate({"candidateNodes": [located], "candidateEdges": []})["candidateChecks"][0]["disposition"], "validated")
        renamed = {**row, "candidateID": "other-id"}
        checked = self.validate({"candidateNodes": [renamed], "candidateEdges": []})["candidateChecks"][0]
        self.assertNotEqual(result["candidateChecks"][0]["sourceLocalCandidateID"], checked["sourceLocalCandidateID"])
        result["originalPayload"]["candidateNodes"][0]["label"] = "mutated copy"
        self.assertEqual(payload, before[0])
        self.assertNotIn("abstained_no_evidence", repr(result))


if __name__ == "__main__":
    unittest.main()
