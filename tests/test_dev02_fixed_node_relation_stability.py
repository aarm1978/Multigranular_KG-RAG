"""Focused no-network tests for the DEV-02 fixed-node relation diagnostic."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.extraction.llm.publications.deterministic_endpoint_binding import bind_edge_endpoint_artifact_ids
from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
from src.extraction.llm.publications.dev02_fixed_node_relation_stability import (
    EXPECTED_REGISTRY_SHA256, FixedNodeDiagnosticError, build_diagnostic_request,
    derive_relation_only_schema, load_fixed_node_registry, prepare,
)
from src.extraction.llm.publications.model_authorable_schema import validate_model_authorable_payload
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import _downstream


class FixedNodeRelationStabilityTests(unittest.TestCase):
    """Prove the isolated diagnostic topology is fixed, narrow, and deterministic."""

    def test_registry_gate_and_endpoint_count(self) -> None:
        registry = load_fixed_node_registry()
        self.assertEqual(sha256_bytes(Path("data/curation/papers/m2/diagnostics/dev02_fixed_node_relation_stability/fixed_node_registry.json").read_bytes()), EXPECTED_REGISTRY_SHA256)
        self.assertEqual(len(registry["nodes"]), 46)
        with self.assertRaises(FixedNodeDiagnosticError):
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                path = Path(directory) / "registry.json"
                path.write_text("{}", encoding="utf-8")
                load_fixed_node_registry(path)

    def test_relation_only_schema_forbids_nodes_and_candidate_node_references(self) -> None:
        request = build_diagnostic_request()
        schema = derive_relation_only_schema(request)
        expected = set(request["eligibleOperationalTargetIDs"])
        self.assertEqual(len(expected), 21)
        self.assertEqual({row["operational_id"] for row in request["targetDefinitions"]}, expected)
        self.assertEqual(set(request["applicabilityPolicyBinding"]["relationUniverseOperationalTargetIDs"]), expected)
        self.assertEqual(request["applicabilityPolicyBinding"]["relationUniverseCount"], 21)
        items = schema["properties"]["candidateEdges"]["items"]
        branches = items.get("anyOf", [items])
        self.assertEqual({branch["properties"]["operationalRelationID"]["const"] for branch in branches}, expected)
        abstention = schema["$defs"]["abstention"]["properties"]
        self.assertEqual(set(abstention["operationalTargetID"]["anyOf"][0]["enum"]), expected)
        self.assertEqual(set(abstention["competingOperationalTargetIDs"]["items"]["enum"]), expected)
        self.assertEqual(schema["properties"]["candidateNodes"]["maxItems"], 0)
        self.assertTrue(validate_model_authorable_payload({"candidateNodes": [{"candidateID": "node-0001"}], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}, schema))
        text = json.dumps(schema)
        self.assertNotIn('"candidate_node"', text)
        self.assertIn('"accepted_local_candidate"', text)
        self.assertIn('"deterministic_node"', text)

    def test_registry_grounding_evidence_is_exact_and_preserved(self) -> None:
        """Fixed node grounding stays trusted context, not model-authored edge evidence."""

        registry = load_fixed_node_registry()
        request = build_diagnostic_request()
        source_text = request["sourceUnit"]["text"]
        endpoint_by_id = {row["candidateID"]: row for row in request["acceptedLocalCandidateEndpoints"]}
        self.assertEqual(len(endpoint_by_id), 46)
        for node in registry["nodes"]:
            evidence = node["evidenceTexts"]
            self.assertTrue(evidence)
            self.assertTrue(all(text in source_text for text in evidence))
            self.assertEqual(endpoint_by_id[node["diagnosticNodeID"]]["diagnosticNodeGroundingEvidenceTexts"], evidence)

    def test_endpoint_binding_and_unknown_endpoint_fail_closed(self) -> None:
        request = build_diagnostic_request()
        payload = {"candidateNodes": [], "candidateEdges": [{"source": {"referenceType": "deterministic_node", "referenceID": request["sourceArtifactID"]}, "target": {"referenceType": "accepted_local_candidate", "referenceID": "DEV02-FIXN-001"}}]}
        bound, result = bind_edge_endpoint_artifact_ids(payload, request)
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual(bound["candidateEdges"][0]["source"]["artifactID"], request["sourceArtifactID"])
        self.assertEqual(bound["candidateEdges"][0]["target"]["artifactID"], request["sourceArtifactID"])
        payload["candidateEdges"][0]["target"]["referenceID"] = "DEV02-FIXN-999"
        _, failed = bind_edge_endpoint_artifact_ids(payload, request)
        self.assertEqual(failed["bindingStatus"], "failed")

    def test_domain_range_incompatible_pair_is_rejected_by_schema(self) -> None:
        request = build_diagnostic_request()
        schema = derive_relation_only_schema(request)
        payload = {"candidateNodes": [], "candidateEdges": [{"candidateID": "edge-0001", "action": "propose_edge", "operationalRelationID": "PUB-R-C-P15-USESTOOL", "ontologyRelationID": "C-P15", "relationName": "usesTool", "relationScope": "intra_source", "origin": "open_discovery", "source": {"referenceType": "accepted_local_candidate", "referenceID": "DEV02-FIXN-001"}, "target": {"referenceType": "accepted_local_candidate", "referenceID": "DEV02-FIXN-001"}, "deferredRecordID": None, "evidenceSpanIDs": ["evidence-0001"]}], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        self.assertTrue(validate_model_authorable_payload(payload, schema))

    def test_preparation_byte_identity_and_deterministic_evidence_binding(self) -> None:
        first = prepare()
        second = prepare()
        self.assertEqual(first, second)
        root = Path("data/curation/papers/m2/diagnostics/dev02_fixed_node_relation_stability")
        self.assertEqual((root / "R1/dev02_fixed_node_relation_stability_complete_request_body.json").read_bytes(), (root / "R2/dev02_fixed_node_relation_stability_complete_request_body.json").read_bytes())
        self.assertEqual(first["maxOutputTokens"], 32768)
        self.assertTrue(first["relationUniverseSurfacesIdentical"])
        self.assertEqual(first["executionModeIntended"], "responses_synchronous_structured_output; not dispatched")
        body = json.loads((root / "R1/dev02_fixed_node_relation_stability_complete_request_body.json").read_text())
        self.assertFalse(body.get("background", False))
        request = build_diagnostic_request()
        literal = request["sourceUnit"]["text"][:20]
        payload = {"evidenceSpans": [{"evidenceSpanID": "evidence-0001", "evidenceText": literal, "locatorAnchor": None}]}
        self.assertEqual(bind_evidence_spans(deepcopy(payload), request["sourceUnit"]), bind_evidence_spans(deepcopy(payload), request["sourceUnit"]))

    def test_deterministic_replay_reuses_binders_and_v1_v12_without_provider_calls(self) -> None:
        """A fixed accepted-local edge follows the unmodified downstream sequence."""

        request = build_diagnostic_request()
        literal = request["sourceUnit"]["text"][:20]
        payload = {
            "candidateNodes": [],
            "candidateEdges": [{
                "candidateID": "edge-0001", "action": "propose_edge",
                "operationalRelationID": "PUB-R-C-P15-USESTOOL", "ontologyRelationID": "C-P15",
                "relationName": "usesTool", "relationScope": "intra_source", "origin": "open_discovery",
                "source": {"referenceType": "deterministic_node", "referenceID": request["sourceArtifactID"]},
                "target": {"referenceType": "accepted_local_candidate", "referenceID": "DEV02-FIXN-039"},
                "deferredRecordID": None, "evidenceSpanIDs": ["evidence-0001"],
            }],
            "evidenceSpans": [{"evidenceSpanID": "evidence-0001", "evidenceText": literal, "locatorAnchor": None}],
            "abstentions": [], "deferredRecords": [],
        }
        raw = canonical_json(payload)
        first = _downstream(raw, request, endpoint_binding=True, evidence_binding=True)
        second = _downstream(raw, request, endpoint_binding=True, evidence_binding=True)
        self.assertEqual(
            tuple(canonical_json(value) if isinstance(value, dict) else value for value in first),
            tuple(canonical_json(value) if isinstance(value, dict) else value for value in second),
        )
        self.assertEqual(first[0]["endpointBinding"]["bindingStatus"], "bound")
        self.assertEqual(first[0]["evidenceBinding"]["bindingStatus"], "bound")
        self.assertEqual(first[2]["envelopeStatus"], "valid")
        self.assertEqual(len(first[3]["candidateEdges"]), 1)
