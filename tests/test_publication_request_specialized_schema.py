"""Tests for request-bound Publication Structured Outputs specialization."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import jsonschema

from src.extraction.llm.publications.model_authorable_schema import (
    audit_openai_structured_outputs_schema,
    derive_model_authorable_schema,
    validate_model_authorable_payload,
)
from src.extraction.llm.publications.request_builder import (
    CANDIDATE_SCHEMA_PATH,
    TARGET_INVENTORY_PATH,
    canonical_json,
    load_json_object,
    load_yaml_object,
    sha256_bytes,
)
from src.extraction.llm.publications.request_specialized_schema import (
    derive_request_specialized_schema,
    request_specialized_schema_record,
)
from src.extraction.llm.publications.run_publication_structured_development_smoke import (
    build_m2b1_request,
)
from src.extraction.llm.publications.run_publication_request_specialized_development_smoke import (
    build_m2b2_request,
    build_three_way_comparison,
    run_request_specialized_live_smoke,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
M2A_FIXTURE = PROJECT_ROOT / "data/curation/papers/m2/publication_m2a_exact_raw_model_output.json"
M2B1_FIXTURE = PROJECT_ROOT / "data/curation/papers/m2/b1/publication_m2b1_attempt4_exact_structured_model_output.json"


def _request_for(row: dict[str, object]) -> dict[str, object]:
    """Build a minimal trusted request projection for one authoritative target row."""

    request = deepcopy(build_m2b1_request())
    request["eligibleOperationalTargetIDs"] = [row["operational_id"]]
    request["targetDefinitions"] = [deepcopy(row)]
    if row.get("emission_mode") == "resolver_mediated_candidate":
        request["extractionChannel"] = "deferred_resolution"
        request["deferredRecordIDs"] = ["deferred-0001"]
    request.pop("requestInputSha256", None)
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    return request


def _node(row: dict[str, object], action: str, origin: str) -> dict[str, object]:
    """Create one frozen-shape node configuration from a target row."""

    formal = row["formal_classes"][0]  # type: ignore[index]
    resolver = row.get("emission_mode") == "resolver_mediated_candidate"
    named = str(row["operational_id"]).endswith("NAMED-WITHOUT-EXACT-IDENTITY")
    identity = "exact_existing_endpoint" if action == "link_existing" else "resolver_pending" if resolver else "source_local"
    return {
        "candidateID": "node-0001", "action": action, "origin": origin,
        "operationalTargetID": row["operational_id"], "ontologyClassID": formal["id"],
        "className": formal["name"], "label": "literal", "labelMode": "verbatim",
        "normalizedLabelProposal": None, "identityScope": identity,
        "artifactScope": "source_artifact" if identity == "source_local" else "external_artifact",
        "provisionalIdentity": named, "existingNodeID": "existing-1" if action == "link_existing" else None,
        "deferredRecordID": "deferred-0001" if origin == "deferred_resolution" else None,
        "attributes": [], "evidenceSpanIDs": ["evidence-0001"],
    }


def _edge(row: dict[str, object], action: str, origin: str) -> dict[str, object]:
    """Create one frozen-shape edge configuration from a target row."""

    formal = row["formal_relations"][0]  # type: ignore[index]
    formal_type = formal.get("type")
    scope = "inter_source" if formal_type == "cross" else "intra_source"
    endpoint = {"referenceType": "candidate_node", "referenceID": "node-0001", "artifactID": None}
    return {
        "candidateID": "edge-0001", "action": action, "origin": origin,
        "operationalRelationID": row["operational_id"], "ontologyRelationID": formal["id"],
        "relationName": formal["name"], "relationScope": scope,
        "source": endpoint, "target": deepcopy(endpoint),
        "deferredRecordID": "deferred-0001" if origin == "deferred_resolution" else None,
        "evidenceSpanIDs": ["evidence-0001"],
    }


def _payload(*, node: dict[str, object] | None = None, edge: dict[str, object] | None = None) -> dict[str, object]:
    """Wrap one candidate in the complete model-authorable envelope shape."""

    return {"candidateNodes": [node] if node else [], "candidateEdges": [edge] if edge else [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}


class RequestSpecializedSchemaTests(unittest.TestCase):
    """Prove specialization narrows transport choices using frozen authorities."""

    def setUp(self) -> None:
        """Load immutable authorities once per test."""

        self.profile = load_yaml_object(TARGET_INVENTORY_PATH)
        self.frozen = load_json_object(CANDIDATE_SCHEMA_PATH)

    def test_dev04_is_deterministic_and_only_exposes_finding(self) -> None:
        """DEV-04 binds Finding and its frozen false provisional identity."""

        request = build_m2b1_request()
        first = derive_request_specialized_schema(request)
        second = derive_request_specialized_schema(request)
        self.assertEqual(canonical_json(first), canonical_json(second))
        properties = first["properties"]["candidateNodes"]["items"]["properties"]
        self.assertEqual(properties["operationalTargetID"]["const"], "PUB-N-A-P16-FINDING")
        self.assertIs(properties["provisionalIdentity"]["const"], False)
        self.assertEqual(first["properties"]["candidateEdges"]["maxItems"], 0)
        self.assertEqual(request_specialized_schema_record(request), request_specialized_schema_record(request))

    def test_actual_schema_passes_complete_provider_audit(self) -> None:
        """The actual DEV-04 projection satisfies every generic transport invariant."""

        audit = audit_openai_structured_outputs_schema(derive_request_specialized_schema(build_m2b1_request()))
        self.assertTrue(audit["compatible"], audit["findings"])
        self.assertEqual(audit["refAudit"]["refSiblingNodes"], 0)
        self.assertEqual(audit["explicitTypeAudit"]["constSchemasLackingExplicitType"], 0)
        self.assertEqual(audit["explicitTypeAudit"]["enumSchemasLackingExplicitType"], 0)
        self.assertEqual(audit["explicitTypeAudit"]["invalidAnyOfBranchCount"], 0)

    def test_every_active_node_target_preserves_valid_actions_and_rejects_others(self) -> None:
        """Every frozen candidate node action is representable without action broadening."""

        frozen_validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/candidateNode", "$defs": self.frozen["$defs"]})
        for row in self.profile["node_targets"]:
            if not row.get("allowed_actions"):
                continue
            request = _request_for(row)
            specialized = derive_request_specialized_schema(request)
            specialized_validator = jsonschema.Draft202012Validator(specialized)
            for action in row["allowed_actions"]:
                candidate = _node(row, action, request["extractionChannel"])
                with self.subTest(target=row["operational_id"], action=action):
                    self.assertTrue(frozen_validator.is_valid(candidate), list(frozen_validator.iter_errors(candidate)))
                    self.assertTrue(specialized_validator.is_valid(_payload(node=candidate)), list(specialized_validator.iter_errors(_payload(node=candidate))))
            candidate = _node(row, "invalid_action", request["extractionChannel"])
            self.assertFalse(specialized_validator.is_valid(_payload(node=candidate)), row["operational_id"])

    def test_every_active_relation_target_preserves_valid_actions_and_rejects_others(self) -> None:
        """Every model-authorable frozen relation action is represented without broadening."""

        frozen_ids = set(self.frozen["$defs"]["candidateEdge"]["properties"]["operationalRelationID"]["enum"])
        frozen_validator = jsonschema.Draft202012Validator({"$ref": "#/$defs/candidateEdge", "$defs": self.frozen["$defs"]})
        for row in self.profile["relation_targets"]:
            if row["operational_id"] not in frozen_ids:
                continue
            request = _request_for(row)
            specialized = derive_request_specialized_schema(request)
            specialized_validator = jsonschema.Draft202012Validator(specialized)
            for action in row["allowed_actions"]:
                candidate = _edge(row, action, request["extractionChannel"])
                with self.subTest(target=row["operational_id"], action=action):
                    self.assertTrue(frozen_validator.is_valid(candidate), list(frozen_validator.iter_errors(candidate)))
                    self.assertTrue(specialized_validator.is_valid(_payload(edge=candidate)), list(specialized_validator.iter_errors(_payload(edge=candidate))))
            wrong = "invalid_action"
            self.assertFalse(specialized_validator.is_valid(_payload(edge=_edge(row, wrong, request["extractionChannel"]))), row["operational_id"])

    def test_relation_scope_remains_endpoint_derived_for_every_relation_target(self) -> None:
        """Ontology relation type never fixes assertion-level artifact scope."""

        frozen_ids = set(
            self.frozen["$defs"]["candidateEdge"]["properties"][
                "operationalRelationID"
            ]["enum"]
        )
        for row in self.profile["relation_targets"]:
            if row["operational_id"] not in frozen_ids:
                continue
            request = _request_for(row)
            validator = jsonschema.Draft202012Validator(
                derive_request_specialized_schema(request)
            )
            candidate = _edge(
                row, row["allowed_actions"][0], request["extractionChannel"]
            )
            for scope in ("intra_source", "inter_source"):
                candidate["relationScope"] = scope
                with self.subTest(target=row["operational_id"], scope=scope):
                    self.assertTrue(
                        validator.is_valid(_payload(edge=candidate)),
                        list(validator.iter_errors(_payload(edge=candidate))),
                    )

    def test_known_fixture_still_validates_and_m2a_shape_still_fails(self) -> None:
        """A Finding fixture remains representable while authentic M2-A remains malformed."""

        request = build_m2b1_request()
        schema = derive_request_specialized_schema(request)
        row = request["targetDefinitions"][0]
        payload = {"candidateNodes": [_node(row, "propose_new", "open_discovery")], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        self.assertEqual(validate_model_authorable_payload(payload, schema), [])
        malformed = json.loads(M2A_FIXTURE.read_text(encoding="utf-8"))
        self.assertTrue(validate_model_authorable_payload(malformed, schema))

    def test_frozen_files_and_generic_projection_are_not_modified(self) -> None:
        """Specialization is read-only with respect to both semantic authorities."""

        before_schema = CANDIDATE_SCHEMA_PATH.read_bytes()
        before_inventory = TARGET_INVENTORY_PATH.read_bytes()
        generic = canonical_json(derive_model_authorable_schema())
        derive_request_specialized_schema(build_m2b1_request())
        self.assertEqual(CANDIDATE_SCHEMA_PATH.read_bytes(), before_schema)
        self.assertEqual(TARGET_INVENTORY_PATH.read_bytes(), before_inventory)
        self.assertEqual(canonical_json(derive_model_authorable_schema()), generic)

    def test_mocked_live_runner_uses_specialized_schema_without_network(self) -> None:
        """A synthetic completed response traverses the unchanged downstream pipeline."""

        payload = json.loads(M2B1_FIXTURE.read_text(encoding="utf-8"))
        for node in payload["candidateNodes"]:
            node["provisionalIdentity"] = False

        def transport(_api_key: str, body: dict[str, object]) -> dict[str, object]:
            """Return one completed exact-model response and inspect request controls."""
            schema = body["text"]["format"]["schema"]  # type: ignore[index]
            target = schema["properties"]["candidateNodes"]["items"]["properties"]["operationalTargetID"]  # type: ignore[index]
            self.assertEqual(target["const"], "PUB-N-A-P16-FINDING")
            self.assertNotIn("tools", body)
            return {"id": "resp_m2b2_synthetic", "object": "response", "created_at": 1787922000,
                    "status": "completed", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None,
                    "output": [{"type": "message", "id": "msg_m2b2_synthetic", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": canonical_json(payload).decode("utf-8")}]}],
                    "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200, "output_tokens_details": {"reasoning_tokens": 10}}}

        with tempfile.TemporaryDirectory() as directory:
            result = run_request_specialized_live_smoke("synthetic-secret", output_dir=Path(directory), transport=transport)
        self.assertEqual(build_m2b2_request()["eligibleOperationalTargetIDs"], ["PUB-N-A-P16-FINDING"])
        self.assertEqual(result["parserResult"]["parseStatus"], "parsed")
        self.assertTrue(result["replayByteIdentical"])

    def test_comparison_uses_authoritative_evidence_valid_boolean(self) -> None:
        """Historical summaries count evidence from the validator's ``valid`` field."""

        b2_dir = PROJECT_ROOT / "data/curation/papers/m2/b2"
        payload = json.loads(
            (b2_dir / "publication_m2b2_exact_structured_model_output.json").read_text(
                encoding="utf-8"
            )
        )
        validation = json.loads(
            (b2_dir / "publication_m2b2_validation_results.json").read_text(
                encoding="utf-8"
            )
        )
        usable = json.loads(
            (b2_dir / "publication_m2b2_usable_pipeline_output.json").read_text(
                encoding="utf-8"
            )
        )
        comparison = build_three_way_comparison(payload, validation, usable)
        b1 = comparison["m2b1Attempt4"]
        b2 = comparison["m2b2"]
        self.assertEqual((b1["validEvidenceSpanCount"], b1["evidenceSpanCount"]), (4, 4))
        self.assertEqual((b2["validEvidenceSpanCount"], b2["evidenceSpanCount"]), (0, 4))
        self.assertEqual(
            (b1["candidateCount"], b1["schemaValidationFailureCount"], b1["usableCandidateCount"]),
            (4, 4, 0),
        )
        self.assertEqual(
            (b2["candidateCount"], b2["schemaValidationFailureCount"], b2["usableCandidateCount"]),
            (4, 0, 0),
        )


if __name__ == "__main__":
    unittest.main()
