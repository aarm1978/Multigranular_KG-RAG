"""Focused no-call tests for prospective trusted edge endpoint binding."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from src.extraction.llm.publications.deterministic_endpoint_binding import (
    bind_edge_endpoint_artifact_ids,
)
from src.extraction.llm.publications.model_authorable_schema import (
    validate_model_authorable_payload,
)
from src.extraction.llm.publications.prospective_endpoint_binding_schema import (
    derive_prospective_endpoint_binding_schema,
)
from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    _downstream,
    build_full_semantic_request,
    build_prompt_semantic_diff,
    load_c0_bindings,
    write_prospective_endpoint_binding_transition_record,
)


def _request() -> dict[str, object]:
    """Return a compact trusted request with distinct non-paper endpoint identities."""

    return {
        "sourceArtifactID": "paper:never-a-fallback",
        "deterministicEndpoints": [{"nodeID": "paper:trusted", "artifactID": "paper:trusted", "className": "Paper"}],
        "acceptedLocalCandidateEndpoints": [{"candidateID": "accepted-0001", "artifactID": "paper:other", "className": "Method"}],
    }


def _payload(source: dict[str, object], target: dict[str, object]) -> dict[str, object]:
    """Return one minimal model-authored endpoint payload."""

    return {
        "candidateNodes": [{"candidateID": "node-0001"}],
        "candidateEdges": [{"candidateID": "edge-0001", "source": source, "target": target}],
    }


class DeterministicEndpointBindingTests(unittest.TestCase):
    """Prove endpoint metadata is exact, trusted, and fail-closed."""

    def test_candidate_node_reference_binds_null_and_missing_or_malformed_fail(self) -> None:
        request = _request()
        bound, result = bind_edge_endpoint_artifact_ids(
            _payload({"referenceType": "candidate_node", "referenceID": "node-0001"}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), request
        )
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertIsNone(bound["candidateEdges"][0]["source"]["artifactID"])
        for reference_id in ("node-9999", "wrong"):
            with self.subTest(reference_id=reference_id):
                _, failed = bind_edge_endpoint_artifact_ids(
                    _payload({"referenceType": "candidate_node", "referenceID": reference_id}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), request
                )
                self.assertEqual(failed["bindingStatus"], "failed")

    def test_deterministic_endpoint_requires_exact_authorized_identity_without_fallback(self) -> None:
        request = _request()
        bound, result = bind_edge_endpoint_artifact_ids(
            _payload({"referenceType": "deterministic_node", "referenceID": "paper:trusted"}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), request
        )
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual(bound["candidateEdges"][0]["source"]["artifactID"], "paper:trusted")
        _, failed = bind_edge_endpoint_artifact_ids(
            _payload({"referenceType": "deterministic_node", "referenceID": "paper:unknown"}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), request
        )
        self.assertEqual(failed["bindingStatus"], "failed")
        self.assertNotIn("paper:never-a-fallback", json.dumps(failed))

    def test_model_authored_artifact_id_fails_closed_instead_of_being_overwritten(self) -> None:
        """A forbidden provider field is not treated as harmless endpoint repair."""

        payload = _payload(
            {"referenceType": "deterministic_node", "referenceID": "paper:trusted", "artifactID": "paper:forged"},
            {"referenceType": "candidate_node", "referenceID": "node-0001"},
        )
        _, result = bind_edge_endpoint_artifact_ids(payload, _request())
        self.assertEqual(result["bindingStatus"], "failed")
        self.assertIn("ENDPOINT_BINDING_MODEL_AUTHORED_ARTIFACT_ID", [row["code"] for row in result["findings"]])

    def test_accepted_local_endpoint_requires_exact_unique_authorized_identity(self) -> None:
        request = _request()
        bound, result = bind_edge_endpoint_artifact_ids(
            _payload({"referenceType": "accepted_local_candidate", "referenceID": "accepted-0001"}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), request
        )
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual(bound["candidateEdges"][0]["source"]["artifactID"], "paper:other")
        for modified in (
            {**request, "acceptedLocalCandidateEndpoints": []},
            {**request, "acceptedLocalCandidateEndpoints": [*request["acceptedLocalCandidateEndpoints"], *request["acceptedLocalCandidateEndpoints"]]},
        ):
            _, failed = bind_edge_endpoint_artifact_ids(
                _payload({"referenceType": "accepted_local_candidate", "referenceID": "accepted-0001"}, {"referenceType": "candidate_node", "referenceID": "node-0001"}), modified
            )
            self.assertEqual(failed["bindingStatus"], "failed")

    def test_provider_schema_hides_artifact_id_and_prompt_preserves_semantic_authorship(self) -> None:
        request = build_full_semantic_request(load_c0_bindings()[1])
        schema = derive_prospective_endpoint_binding_schema(request)
        endpoint = schema["$defs"]["edgeEndpoint"]
        self.assertNotIn("artifactID", endpoint["properties"])
        self.assertNotIn("artifactID", endpoint["required"])
        self.assertEqual(validate_model_authorable_payload({"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}, schema), [])
        transition = build_prompt_semantic_diff()
        self.assertTrue(transition["endpointArtifactIDAuthorshipChanged"])
        self.assertFalse(transition["endpointReferenceTypeReferenceIDSemanticAuthorshipChanged"])
        self.assertFalse(transition["evidenceMetadataAuthorshipChanged"])
        self.assertFalse(transition["extractionCompletenessInstructionsChanged"])

    def test_transition_record_is_deterministic_and_preserves_v016_provenance(self) -> None:
        """The new transition is separate from the retained evidence-binding transition."""

        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            write_prospective_endpoint_binding_transition_record(first)
            write_prospective_endpoint_binding_transition_record(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
        record = build_prompt_semantic_diff()
        self.assertEqual(record["historicalV016TransitionPreserved"]["newPromptVersion"], "publication-development-0.1.6")

    def test_synthetic_dev02_topology_binds_all_36_candidate_and_16_deterministic_endpoints(self) -> None:
        request = build_full_semantic_request(load_c0_bindings()[1])
        topology = {"candidateNodes": [{"candidateID": "node-0001"}], "candidateEdges": []}
        endpoints = ([{"referenceType": "candidate_node", "referenceID": "node-0001"}] * 36 + [{"referenceType": "deterministic_node", "referenceID": request["sourceArtifactID"]}] * 16)
        for index in range(26):
            topology["candidateEdges"].append({"candidateID": f"edge-{index + 1:04d}", "source": deepcopy(endpoints[index * 2]), "target": deepcopy(endpoints[index * 2 + 1])})
        bound, result = bind_edge_endpoint_artifact_ids(topology, request)
        self.assertEqual(result["bindingStatus"], "bound")
        values = [endpoint["artifactID"] for edge in bound["candidateEdges"] for endpoint in (edge["source"], edge["target"])]
        self.assertEqual(values.count(None), 36)
        self.assertEqual(values.count(request["sourceArtifactID"]), 16)

    def test_endpoint_then_evidence_binding_precedes_unchanged_validation(self) -> None:
        """A current request binds endpoint IDs before literal evidence and V1--V12."""

        request = build_full_semantic_request(load_c0_bindings()[0])
        source_text = request["sourceUnit"]["text"]
        literal = source_text[:20]
        payload = {
            "candidateNodes": [], "candidateEdges": [],
            "evidenceSpans": [{"evidenceSpanID": "evidence-0001", "evidenceText": literal, "locatorAnchor": None}],
            "abstentions": [], "deferredRecords": [],
        }
        parser, _, validation, _ = _downstream(json.dumps(payload).encode("utf-8"), request, endpoint_binding=True, evidence_binding=True)
        self.assertEqual(parser["endpointBinding"]["bindingStatus"], "bound")
        self.assertEqual(parser["evidenceBinding"]["bindingStatus"], "bound")
        self.assertEqual([row["operation"] for row in parser["bindingOperations"][-2:]], ["bind_trusted_edge_endpoint_artifact_metadata", "bind_model_authored_literal_evidence"])
        self.assertEqual(validation["envelopeStatus"], "valid")

    def test_authorized_dev02_payload_binds_relation_endpoints_and_validates(self) -> None:
        """A no-call DEV-02-shaped payload reaches V1--V12 after both binders."""

        fixture = Path("data/curation/papers/m2/c1b/DEV-02/publication_m2c1b_dev02_exact_structured_model_output.json")
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        request = build_full_semantic_request(load_c0_bindings()[1])
        for span in payload["evidenceSpans"]:
            for key in list(span):
                if key not in {"evidenceSpanID", "evidenceText", "locatorAnchor"}:
                    span.pop(key)
            span.setdefault("locatorAnchor", None)
        payload["candidateEdges"] = [{
            "candidateID": "edge-0001", "action": "propose_edge",
            "operationalRelationID": "PUB-R-C-P31-MENTIONSTOOL", "ontologyRelationID": "C-P31",
            "relationName": "mentionsTool", "relationScope": "intra_source", "origin": "open_discovery",
            "source": {"referenceType": "deterministic_node", "referenceID": request["sourceArtifactID"]},
            "target": {"referenceType": "candidate_node", "referenceID": "node-0003"},
            "deferredRecordID": None, "evidenceSpanIDs": ["evidence-0007"],
        }]
        parser, _, validation, usable = _downstream(
            json.dumps(payload).encode("utf-8"), request,
            endpoint_binding=True, evidence_binding=True,
        )
        edge = parser["parsedEnvelope"]["candidateEdges"][0]
        self.assertEqual(edge["source"]["artifactID"], request["sourceArtifactID"])
        self.assertIsNone(edge["target"]["artifactID"])
        self.assertEqual(validation["envelopeStatus"], "valid")
        self.assertEqual((len(usable["candidateNodes"]), len(usable["candidateEdges"])), (35, 1))

    def test_authentic_dev02_attempt3_topology_binds_to_accepted_counterfactual_values(self) -> None:
        """Bind a stripped copy of the preserved attempt-3 topology without mutation."""

        root = Path("data/curation/papers/m2/future_full_semantic_devset0/DEV-02")
        authentic_root = root / "researcher_authorized_recovery_002/DEV-02"
        raw_path = authentic_root / "publication_full_semantic_dev02_exact_structured_model_output.json"
        request_path = authentic_root / "publication_full_semantic_dev02_live_request.json"
        diagnostic_path = root / "researcher_authorized_recovery_002_diagnostic/dev02_attempt3_endpoint_counterfactual_and_semantic_review.json"
        raw_bytes = raw_path.read_bytes()
        authentic = json.loads(raw_bytes)
        prospective = deepcopy(authentic)
        authentic_references: dict[tuple[str, str], tuple[object, object]] = {}
        for edge in authentic["candidateEdges"]:
            for side in ("source", "target"):
                endpoint = edge[side]
                authentic_references[(edge["candidateID"], side)] = (
                    endpoint["referenceType"], endpoint["referenceID"],
                )
        for edge in prospective["candidateEdges"]:
            for side in ("source", "target"):
                edge[side].pop("artifactID")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        bound, result = bind_edge_endpoint_artifact_ids(prospective, request)
        self.assertEqual(result["bindingStatus"], "bound")
        self.assertEqual(raw_path.read_bytes(), raw_bytes)

        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        accepted_changes = {
            (row["edgeCandidateID"], row["endpoint"]): row["toArtifactID"]
            for row in diagnostic["counterfactualChange"]["changes"]
        }
        self.assertEqual(len(accepted_changes), 36)
        deterministic = {row["nodeID"]: row["artifactID"] for row in request["deterministicEndpoints"]}
        accepted_local = {row["candidateID"]: row["artifactID"] for row in request["acceptedLocalCandidateEndpoints"]}
        candidate_keys: set[tuple[str, str]] = set()
        for edge in bound["candidateEdges"]:
            for side in ("source", "target"):
                endpoint = edge[side]
                key = (edge["candidateID"], side)
                self.assertEqual(
                    (endpoint["referenceType"], endpoint["referenceID"]),
                    authentic_references[key],
                )
                if endpoint["referenceType"] == "candidate_node":
                    candidate_keys.add(key)
                    self.assertIsNone(endpoint["artifactID"])
                    self.assertIsNone(accepted_changes[key])
                elif endpoint["referenceType"] == "deterministic_node":
                    self.assertEqual(endpoint["artifactID"], deterministic[endpoint["referenceID"]])
                else:
                    self.assertEqual(endpoint["artifactID"], accepted_local[endpoint["referenceID"]])
        self.assertEqual(candidate_keys, set(accepted_changes))

    def test_historical_dev02_v04_and_attempt_artifacts_match_existing_pinned_hashes(self) -> None:
        """Verify only hashes already asserted by accepted lifecycle/provenance records."""

        root = Path("data/curation/papers/m2/future_full_semantic_devset0/DEV-02")
        attempt1 = root / "publication_full_semantic_dev02_attempt_record.json"
        attempt2_root = root / "researcher_authorized_recovery_001/DEV-02"
        attempt2 = attempt2_root / "publication_full_semantic_dev02_attempt_record.json"
        attempt3_root = root / "researcher_authorized_recovery_002/DEV-02"
        attempt3 = json.loads((attempt3_root / "publication_full_semantic_dev02_attempt_record.json").read_text(encoding="utf-8"))
        reproducibility = json.loads((attempt3_root / "publication_full_semantic_dev02_reproducibility_record.json").read_text(encoding="utf-8"))
        schema_record = json.loads((attempt3_root / "publication_full_semantic_dev02_request_specialized_schema_record.json").read_text(encoding="utf-8"))
        schema = json.loads((attempt3_root / "publication_full_semantic_dev02_request_specialized_schema.json").read_text(encoding="utf-8"))
        attempt2_record = json.loads(attempt2.read_text(encoding="utf-8"))

        self.assertEqual(hashlib.sha256(attempt1.read_bytes()).hexdigest(), attempt2_record["recoveryOf"]["priorAttemptSha256"])
        self.assertEqual(hashlib.sha256(attempt2.read_bytes()).hexdigest(), attempt3["recoveryOf"]["priorAttemptSha256"])
        self.assertEqual(schema_record["prospectiveSchemaSha256"], "7c0b8ff150dc0af790a5c27a7c8046c287a317eb3ff3b4bcf40c16556d21f4b7")
        self.assertEqual(hashlib.sha256(canonical_json(schema)).hexdigest(), schema_record["prospectiveSchemaSha256"])
        for filename, record_key, expected, canonical in (
            ("publication_full_semantic_dev02_exact_structured_model_output.json", "rawModelOutputSha256", "e9ce2dcdce26ad3307a9ef44a2bdcd829b01aaae5a6fbbc3b111174776ad20d8", False),
            ("publication_full_semantic_dev02_validation_results.json", "validationArtifactSha256", None, True),
            ("publication_full_semantic_dev02_usable_pipeline_output.json", "usableArtifactSha256", None, True),
            ("publication_full_semantic_dev02_provider_api_response.json", "providerResponseSha256", None, True),
        ):
            with self.subTest(filename=filename):
                artifact = (attempt3_root / filename).read_bytes()
                actual = hashlib.sha256(canonical_json(json.loads(artifact)) if canonical else artifact).hexdigest()
                self.assertEqual(actual, reproducibility[record_key])
                if expected is not None:
                    self.assertEqual(actual, expected)
        failure_metadata = json.loads((attempt2_root / "publication_full_semantic_dev02_provider_failure_metadata.json").read_text(encoding="utf-8"))
        failure_response = attempt2_root / "publication_full_semantic_dev02_provider_failure_response.json"
        self.assertEqual(
            hashlib.sha256(canonical_json(json.loads(failure_response.read_bytes()))).hexdigest(),
            failure_metadata["rawProviderResponseSha256"],
        )


if __name__ == "__main__":
    unittest.main()
