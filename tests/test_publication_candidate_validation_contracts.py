"""Static tests for the Publication Pilot 1 candidate and validation contracts.

These tests intentionally do not implement parsing or validation. They exercise
the candidate JSON Schema with small provider-neutral fixtures and verify that
the two candidate contracts remain faithful to the frozen target profile and
source-unit interface.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import unittest
from pathlib import Path
from typing import Any

import jsonschema
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas/publication_candidate_output.schema.json"
VALIDATION_CONTRACT_PATH = (
    PROJECT_ROOT / "docs/publication_evidence_validation_contract.md"
)
TARGET_PROFILE_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
)
SOURCE_UNIT_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_source_unit_contract.md"

TARGET_PROFILE_SHA256 = (
    "6401c15b861c2362b67e03d56acd4a7304964f595d706311fd4f149eb69b3a5e"
)
SOURCE_UNIT_CONTRACT_SHA256 = (
    "8132be14b06153957697310ec8df16a07e72462ce7a98ae46b8d4f26aa188172"
)
SHA256_ZERO = "0" * 64


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object at {path}")
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    """Load one UTF-8 YAML mapping."""
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a YAML mapping at {path}")
    return value


def metadata() -> dict[str, Any]:
    """Return minimal pipeline-owned metadata for candidate fixtures."""
    return {
        "outputID": "output-0001",
        "requestID": "request-0001",
        "runID": "run-0001",
        "sourceArtifactID": "paper:fixture",
        "primarySourceUnitID": "pub:fixture:sec:0001:unit:0001",
        "contextSourceUnitIDs": [],
        "requestScope": "local_unit",
        "includedCompleteSection": True,
        "extractionChannel": "open_discovery",
        "eligibleOperationalTargetIDs": [],
        "deferredRecordIDs": [],
        "ontologyVersion": "0.1.4",
        "ontologySha256": (
            "7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635"
        ),
        "targetInventoryProfileID": "publication-pilot1-target-inventory",
        "targetInventorySchemaVersion": "0.1.0",
        "targetInventorySha256": TARGET_PROFILE_SHA256,
        "sourceUnitContractVersion": "0.1.2",
        "sourceUnitContractSha256": SOURCE_UNIT_CONTRACT_SHA256,
        "candidateSchemaVersion": "0.1.0",
        "candidateSchemaSha256": SHA256_ZERO,
        "promptVersion": "fixture-prompt-0",
        "promptSha256": SHA256_ZERO,
        "requestInputSha256": SHA256_ZERO,
        "rawResponseSha256": SHA256_ZERO,
        "provider": "fixture-provider",
        "modelName": "fixture-model",
        "modelVersion": None,
        "generationParameters": {
            "temperature": 0,
            "topP": 1,
            "seed": 1,
            "maxOutputTokens": 100,
            "responseFormat": "structured_json",
        },
        "tokenUsage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
        "costUSD": None,
        "retryCount": 0,
        "responseCreatedAt": "2026-07-30T12:00:00Z",
    }


def evidence(
    evidence_id: str = "evidence-0001", *, start: int = 0, document_start: int = 100
) -> dict[str, Any]:
    """Return one structurally valid exact evidence-span fixture."""
    text = "The method produced a finding."
    return {
        "evidenceSpanID": evidence_id,
        "sourceArtifactID": "paper:fixture",
        "sourceUnitID": "pub:fixture:sec:0001:unit:0001",
        "sourceUnitTextHash": SHA256_ZERO,
        "sectionID": "pub:fixture:sec:0001",
        "sectionTitle": "Methods",
        "evidenceText": text,
        "startOffsetInUnit": start,
        "endOffsetInUnit": start + len(text),
        "startOffsetInDocument": document_start,
        "endOffsetInDocument": document_start + len(text),
        "evidenceHash": None,
    }


def node(
    candidate_id: str,
    target_id: str,
    ontology_id: str,
    class_name: str,
    *,
    action: str = "propose_new",
    origin: str = "open_discovery",
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return one minimal candidate-node fixture."""
    return {
        "candidateID": candidate_id,
        "action": action,
        "origin": origin,
        "operationalTargetID": target_id,
        "ontologyClassID": ontology_id,
        "className": class_name,
        "label": class_name,
        "labelMode": "verbatim",
        "identityScope": (
            "exact_existing_endpoint" if action == "link_existing" else "source_local"
        ),
        "artifactScope": "source_artifact",
        "provisionalIdentity": False,
        "existingNodeID": "det:node:1" if action == "link_existing" else None,
        "deferredRecordID": None,
        "attributes": [],
        "evidenceSpanIDs": evidence_ids or ["evidence-0001"],
    }


def endpoint(reference_type: str, reference_id: str) -> dict[str, Any]:
    """Return an endpoint using one authorized explicit reference form."""
    return {
        "referenceType": reference_type,
        "referenceID": reference_id,
        "artifactID": None if reference_type == "candidate_node" else "paper:fixture",
    }


def edge(
    *,
    target_id: str = "PUB-R-C-P07-PRODUCES",
    ontology_id: str = "C-P07",
    relation_name: str = "produces",
    source: dict[str, Any] | None = None,
    target: dict[str, Any] | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return one minimal candidate-edge fixture."""
    return {
        "candidateID": "edge-0001",
        "action": "propose_edge",
        "origin": "open_discovery",
        "operationalRelationID": target_id,
        "ontologyRelationID": ontology_id,
        "relationName": relation_name,
        "relationScope": "intra_source",
        "source": source or endpoint("candidate_node", "node-0001"),
        "target": target or endpoint("candidate_node", "node-0002"),
        "deferredRecordID": None,
        "evidenceSpanIDs": evidence_ids or ["evidence-0001"],
    }


def envelope() -> dict[str, Any]:
    """Return a parseable empty candidate envelope."""
    return {
        "schemaVersion": "0.1.0",
        "outputStage": "parsed_candidate",
        "metadata": metadata(),
        "candidateNodes": [],
        "candidateEdges": [],
        "evidenceSpans": [],
        "abstentions": [],
        "deferredRecords": [],
    }


class PublicationCandidateSchemaTests(unittest.TestCase):
    """Validate schema syntax, authorization, and representative records."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the schema, profile, and a format-checking validator once."""
        cls.schema = load_json(SCHEMA_PATH)
        cls.profile = load_yaml(TARGET_PROFILE_PATH)
        cls.validator = jsonschema.Draft202012Validator(
            cls.schema, format_checker=jsonschema.FormatChecker()
        )

    def assertValid(self, instance: dict[str, Any]) -> None:  # noqa: N802
        """Assert that an instance has no schema errors."""
        errors = sorted(self.validator.iter_errors(instance), key=lambda item: list(item.path))
        self.assertEqual(errors, [], "\n".join(error.message for error in errors))

    def assertInvalid(self, instance: dict[str, Any]) -> None:  # noqa: N802
        """Assert that an instance violates at least one schema rule."""
        self.assertTrue(list(self.validator.iter_errors(instance)))

    def test_schema_is_json_and_valid_draft_2020_12(self) -> None:
        """The declared schema is a valid Draft 2020-12 schema."""
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(
            self.schema["$id"],
            "https://w3id.org/ciroh/schemas/publication-candidate-output/0.1.0",
        )
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_all_local_refs_resolve_and_all_defs_are_reachable(self) -> None:
        """Every local reference resolves and no definition is orphaned."""
        refs: list[str] = []

        def collect(value: Any) -> None:
            """Collect local references recursively."""
            if isinstance(value, dict):
                if "$ref" in value:
                    refs.append(value["$ref"])
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(self.schema)
        used = {ref.removeprefix("#/$defs/") for ref in refs}
        self.assertTrue(all(ref.startswith("#/$defs/") for ref in refs))
        self.assertEqual(used, set(self.schema["$defs"]))

    def test_top_level_envelope_is_closed_and_complete(self) -> None:
        """All six record groups and metadata are required; unknown fields fail."""
        expected = {
            "schemaVersion",
            "outputStage",
            "metadata",
            "candidateNodes",
            "candidateEdges",
            "evidenceSpans",
            "abstentions",
            "deferredRecords",
        }
        self.assertEqual(set(self.schema["required"]), expected)
        self.assertValid(envelope())
        invalid = envelope()
        invalid["validationStatus"] = "validated"
        self.assertInvalid(invalid)

    def test_target_enums_are_derived_exactly_from_frozen_profile(self) -> None:
        """Candidate target enums equal the profile-authorized candidate interface."""
        expected_nodes = {
            row["operational_id"]
            for row in self.profile["node_targets"]
            if row["emission_mode"] in {"llm_candidate", "resolver_mediated_candidate"}
            or "link_existing" in row["allowed_actions"]
        }
        expected_edges = {
            row["operational_id"]
            for row in self.profile["relation_targets"]
            if row["emission_mode"] in {"llm_candidate", "resolver_mediated_candidate"}
        }
        actual_nodes = set(
            self.schema["$defs"]["candidateNode"]["properties"]["operationalTargetID"][
                "enum"
            ]
        )
        actual_edges = set(
            self.schema["$defs"]["candidateEdge"]["properties"][
                "operationalRelationID"
            ]["enum"]
        )
        self.assertEqual(actual_nodes, expected_nodes)
        self.assertEqual(actual_edges, expected_edges)
        self.assertEqual((len(actual_nodes), len(actual_edges)), (46, 27))
        metadata_targets = set(
            self.schema["$defs"]["metadata"]["properties"]
            ["eligibleOperationalTargetIDs"]["items"]["enum"]
        )
        self.assertEqual(metadata_targets, actual_nodes | actual_edges)

    def test_nonordinary_profile_targets_are_not_ordinary_candidates(self) -> None:
        """Excluded, pipeline, follow-on, and context-only discovery targets stay out."""
        node_enum = set(
            self.schema["$defs"]["candidateNode"]["properties"]["operationalTargetID"][
                "enum"
            ]
        )
        edge_enum = set(
            self.schema["$defs"]["candidateEdge"]["properties"][
                "operationalRelationID"
            ]["enum"]
        )
        for group, emitted in (("node_targets", node_enum), ("relation_targets", edge_enum)):
            for row in self.profile[group]:
                if row["pilot_treatment"] in {
                    "out_of_scope",
                    "required_infrastructure",
                    "separate_follow_on_protocol",
                }:
                    self.assertNotIn(row["operational_id"], emitted)
                if row["pilot_treatment"] == "context_only" and "link_existing" not in row[
                    "allowed_actions"
                ]:
                    self.assertNotIn(row["operational_id"], emitted)
                if row["production_responsibility"] == "pipeline_generated":
                    self.assertNotIn(row["operational_id"], emitted)

    def test_ontology_ids_names_and_attributes_match_authorized_profile_rows(self) -> None:
        """Schema ontology vocabularies are exactly those reachable by candidate rows."""
        node_targets = set(
            self.schema["$defs"]["candidateNode"]["properties"]["operationalTargetID"]
            ["enum"]
        )
        edge_targets = set(
            self.schema["$defs"]["candidateEdge"]["properties"]["operationalRelationID"]
            ["enum"]
        )
        profile_nodes = [
            row for row in self.profile["node_targets"]
            if row["operational_id"] in node_targets
        ]
        profile_edges = [
            row for row in self.profile["relation_targets"]
            if row["operational_id"] in edge_targets
        ]
        node_def = self.schema["$defs"]["candidateNode"]["properties"]
        edge_def = self.schema["$defs"]["candidateEdge"]["properties"]
        self.assertEqual(
            set(node_def["ontologyClassID"]["enum"]),
            {item["id"] for row in profile_nodes for item in row["formal_classes"]},
        )
        self.assertEqual(
            set(node_def["className"]["enum"]),
            {item["name"] for row in profile_nodes for item in row["formal_classes"]},
        )
        self.assertEqual(
            set(edge_def["ontologyRelationID"]["enum"]),
            {item["id"] for row in profile_edges for item in row["formal_relations"]},
        )
        self.assertEqual(
            set(edge_def["relationName"]["enum"]),
            {item["name"] for row in profile_edges for item in row["formal_relations"]},
        )
        attribute_names = {
            branch["properties"]["attributeName"]["const"]
            for branch in self.schema["$defs"]["candidateAttribute"]["oneOf"]
        }
        authorized_attributes = {
            attribute["name"]
            for row in profile_nodes
            for formal_class in row["formal_classes"]
            for attribute in formal_class.get("attributes", [])
        }
        self.assertEqual(attribute_names, authorized_attributes)

    def test_valid_fixtures_cover_required_candidate_shapes(self) -> None:
        """Representative empty, node, edge, normalization, and deferred shapes pass."""
        fixtures: list[dict[str, Any]] = []

        empty_abstention = envelope()
        empty_abstention["abstentions"] = [{
            "abstentionID": "abstention-0001",
            "scope": "source_unit",
            "operationalTargetID": None,
            "deferredRecordID": None,
            "reason": "insufficient_evidence",
            "evidenceSpanIDs": [],
            "competingOperationalTargetIDs": [],
            "relatedCandidateIDs": [],
            "rationale": "No exact semantic evidence is present.",
        }]
        fixtures.append(empty_abstention)

        discourse = envelope()
        discourse["evidenceSpans"] = [evidence()]
        discourse["candidateNodes"] = [node(
            "node-0001", "PUB-N-A-P16-FINDING", "A-P16", "Finding"
        )]
        fixtures.append(discourse)

        linked = envelope()
        linked["evidenceSpans"] = [evidence()]
        linked["candidateNodes"] = [node(
            "node-0001",
            "PUB-N-A-DOM02-TOOL-EXISTING-EXACT-ENDPOINT",
            "A-DOM02",
            "Tool",
            action="link_existing",
        )]
        fixtures.append(linked)

        local_edge = envelope()
        local_edge["evidenceSpans"] = [evidence()]
        local_edge["candidateNodes"] = [
            node("node-0001", "PUB-N-A-P13-METHOD", "A-P13", "Method"),
            node("node-0002", "PUB-N-A-P16-FINDING", "A-P16", "Finding"),
        ]
        local_edge["candidateEdges"] = [edge()]
        fixtures.append(local_edge)

        deterministic_edge = deepcopy(local_edge)
        deterministic_edge["candidateEdges"] = [edge(
            target_id="PUB-R-C-P15-USESTOOL",
            ontology_id="C-P15",
            relation_name="usesTool",
            source=endpoint("candidate_node", "node-0001"),
            target=endpoint("deterministic_node", "det:tool:1"),
        )]
        fixtures.append(deterministic_edge)

        distributed = deepcopy(local_edge)
        distributed["evidenceSpans"] = [
            evidence("evidence-0001"),
            evidence("evidence-0002", start=40, document_start=140),
        ]
        distributed["candidateEdges"][0]["evidenceSpanIDs"] = [
            "evidence-0001", "evidence-0002"
        ]
        fixtures.append(distributed)

        normalized = deepcopy(discourse)
        normalized["candidateNodes"][0]["normalizedLabelProposal"] = "finding"
        fixtures.append(normalized)

        deferred = envelope()
        deferred["metadata"]["extractionChannel"] = "deferred_resolution"
        deferred["metadata"]["deferredRecordIDs"] = ["deferred:phase-b:1"]
        deferred["evidenceSpans"] = [evidence()]
        deferred_node = node(
            "node-0001",
            "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B",
            "A-D01",
            "DatasetResource",
            origin="deferred_resolution",
        )
        deferred_node["identityScope"] = "resolver_pending"
        deferred_node["artifactScope"] = "external_artifact"
        deferred_node["deferredRecordID"] = "deferred:phase-b:1"
        deferred["candidateNodes"] = [deferred_node]
        deferred["deferredRecords"] = [{
            "deferredRecordID": "deferred:phase-b:1",
            "proposedDisposition": "resolved_accepted",
            "proposedOperationalTargetID": (
                "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
            ),
            "relatedCandidateIDs": ["node-0001"],
            "evidenceSpanIDs": ["evidence-0001"],
            "rationale": "The exact identifier is present for resolver verification.",
        }]
        fixtures.append(deferred)

        for index, fixture in enumerate(fixtures):
            with self.subTest(fixture=index):
                self.assertValid(fixture)

    def test_invalid_fixtures_reject_forbidden_or_malformed_shapes(self) -> None:
        """Representative unauthorized, identity, evidence, and mutation shapes fail."""
        base = envelope()
        base["evidenceSpans"] = [evidence()]
        base["candidateNodes"] = [node(
            "node-0001", "PUB-N-A-P16-FINDING", "A-P16", "Finding"
        )]

        invalids: list[dict[str, Any]] = []
        abstract = deepcopy(base)
        abstract["candidateNodes"][0]["ontologyClassID"] = "A-DOM03"
        abstract["candidateNodes"][0]["className"] = "ComputationalModel"
        invalids.append(abstract)

        unauthorized = deepcopy(base)
        unauthorized["candidateNodes"][0]["operationalTargetID"] = "PUB-N-UNKNOWN"
        invalids.append(unauthorized)

        missing_existing = deepcopy(base)
        missing_existing["candidateNodes"][0]["action"] = "link_existing"
        missing_existing["candidateNodes"][0]["existingNodeID"] = None
        missing_existing["candidateNodes"][0]["identityScope"] = "exact_existing_endpoint"
        invalids.append(missing_existing)

        proposed_existing = deepcopy(base)
        proposed_existing["candidateNodes"][0]["existingNodeID"] = "det:node:1"
        invalids.append(proposed_existing)

        evidence_free = deepcopy(base)
        evidence_free["candidateNodes"][0]["evidenceSpanIDs"] = []
        invalids.append(evidence_free)

        name_endpoint = deepcopy(base)
        name_endpoint["candidateEdges"] = [edge()]
        name_endpoint["candidateEdges"][0]["source"] = {"name": "Method"}
        invalids.append(name_endpoint)

        for forbidden_field in (
            "validationStatus", "normalizationStatus", "adjudicationStatus", "sameAs",
            "mergeWith", "consolidatesTo", "neo4jID",
        ):
            invalid = deepcopy(base)
            invalid["candidateNodes"][0][forbidden_field] = "forbidden"
            invalids.append(invalid)

        pipeline_relation = deepcopy(base)
        pipeline_relation["candidateEdges"] = [edge()]
        pipeline_relation["candidateEdges"][0]["operationalRelationID"] = (
            "PUB-R-C-P05-REPORTS-PIPELINE"
        )
        invalids.append(pipeline_relation)

        out_of_scope = deepcopy(base)
        out_of_scope["candidateNodes"][0]["operationalTargetID"] = (
            "PUB-N-A-DOM01-SOFTWAREENTITY"
        )
        invalids.append(out_of_scope)

        malformed_offsets = deepcopy(base)
        malformed_offsets["evidenceSpans"][0]["startOffsetInUnit"] = -1
        invalids.append(malformed_offsets)

        authoritative_normalization = deepcopy(base)
        authoritative_normalization["candidateNodes"][0]["labelMode"] = "normalized"
        authoritative_normalization["candidateNodes"][0]["normalizedLabelProposal"] = "finding"
        invalids.append(authoritative_normalization)

        for index, fixture in enumerate(invalids):
            with self.subTest(fixture=index):
                self.assertInvalid(fixture)

    def test_actions_and_endpoint_reference_forms_are_constrained(self) -> None:
        """Ordinary targets cannot link, deferred edges cannot use ordinary actions."""
        wrong_node_action = envelope()
        wrong_node_action["evidenceSpans"] = [evidence()]
        wrong_node_action["candidateNodes"] = [node(
            "node-0001",
            "PUB-N-A-P16-FINDING",
            "A-P16",
            "Finding",
            action="link_existing",
        )]
        self.assertInvalid(wrong_node_action)

        wrong_edge_action = envelope()
        candidate_edge = edge(
            target_id="PUB-R-C-P29-REFERENCESDATASET-EXACT-OMITTED-IDENTIFIER",
            ontology_id="C-P29",
            relation_name="referencesDataset",
        )
        wrong_edge_action["candidateEdges"] = [candidate_edge]
        wrong_edge_action["evidenceSpans"] = [evidence()]
        self.assertInvalid(wrong_edge_action)

        invalid_endpoint = envelope()
        invalid_endpoint["evidenceSpans"] = [evidence()]
        invalid_endpoint["candidateEdges"] = [edge()]
        invalid_endpoint["candidateEdges"][0]["source"] = endpoint(
            "candidate_node", "det:node:1"
        )
        invalid_endpoint["candidateEdges"][0]["source"]["artifactID"] = "paper:fixture"
        self.assertInvalid(invalid_endpoint)

    def test_schema_action_conditions_match_each_profile_candidate_row(self) -> None:
        """Every authorized row accepts only its frozen profile actions."""
        node_enum = set(
            self.schema["$defs"]["candidateNode"]["properties"]["operationalTargetID"]
            ["enum"]
        )
        for row in self.profile["node_targets"]:
            if row["operational_id"] not in node_enum:
                continue
            formal_class = row["formal_classes"][0]
            for action in ("propose_new", "link_existing"):
                fixture = envelope()
                fixture["evidenceSpans"] = [evidence()]
                candidate = node(
                    "node-0001",
                    row["operational_id"],
                    formal_class["id"],
                    formal_class["name"],
                    action=action,
                )
                if row["emission_mode"] == "resolver_mediated_candidate":
                    candidate["origin"] = "deferred_resolution"
                    candidate["deferredRecordID"] = "deferred:phase-b:1"
                    if action == "propose_new":
                        candidate["identityScope"] = "resolver_pending"
                if row["operational_id"].endswith("NAMED-WITHOUT-EXACT-IDENTITY"):
                    candidate["provisionalIdentity"] = True
                fixture["candidateNodes"] = [candidate]
                with self.subTest(target=row["operational_id"], action=action):
                    if action in row["allowed_actions"]:
                        self.assertValid(fixture)
                    else:
                        self.assertInvalid(fixture)

        edge_enum = set(
            self.schema["$defs"]["candidateEdge"]["properties"]["operationalRelationID"]
            ["enum"]
        )
        for row in self.profile["relation_targets"]:
            if row["operational_id"] not in edge_enum:
                continue
            formal_relation = row["formal_relations"][0]
            for action in ("propose_edge", "resolve_deferred"):
                fixture = envelope()
                fixture["evidenceSpans"] = [evidence()]
                candidate = edge(
                    target_id=row["operational_id"],
                    ontology_id=formal_relation["id"],
                    relation_name=formal_relation["name"],
                )
                candidate["action"] = action
                if action == "resolve_deferred":
                    candidate["origin"] = "deferred_resolution"
                    candidate["deferredRecordID"] = "deferred:phase-b:1"
                fixture["candidateEdges"] = [candidate]
                with self.subTest(target=row["operational_id"], action=action):
                    if action in row["allowed_actions"]:
                        self.assertValid(fixture)
                    else:
                        self.assertInvalid(fixture)

    def test_label_and_evidence_interfaces_are_exactly_bounded(self) -> None:
        """Verbatim labels and source-unit evidence fields remain authoritative."""
        node_def = self.schema["$defs"]["candidateNode"]
        self.assertEqual(node_def["properties"]["labelMode"]["const"], "verbatim")
        self.assertNotIn("normalizedLabelProposal", node_def["required"])
        evidence_def = self.schema["$defs"]["evidenceSpan"]
        expected = {
            "evidenceSpanID",
            "sourceArtifactID",
            "sourceUnitID",
            "sourceUnitTextHash",
            "sectionID",
            "sectionTitle",
            "evidenceText",
            "startOffsetInUnit",
            "endOffsetInUnit",
            "startOffsetInDocument",
            "endOffsetInDocument",
            "evidenceHash",
        }
        self.assertEqual(set(evidence_def["required"]), expected)
        self.assertFalse(evidence_def["additionalProperties"])
        self.assertTrue(evidence_def["properties"]["evidenceHash"]["readOnly"])
        self.assertIn(
            "sourceUnit.sectionTitleRaw",
            evidence_def["properties"]["sectionTitle"]["description"],
        )

    def test_abstention_and_deferred_vocabularies_are_controlled(self) -> None:
        """Semantic abstentions and proposed deferred dispositions use enums."""
        abstention = self.schema["$defs"]["abstention"]
        deferred = self.schema["$defs"]["deferredRecordResolution"]
        self.assertEqual(
            set(abstention["properties"]["reason"]["enum"]),
            set(self.profile["semantic_abstention_reasons"]),
        )
        self.assertIn("proposedDisposition", deferred["required"])
        self.assertNotIn("disposition", deferred["properties"])


class PublicationValidationContractTests(unittest.TestCase):
    """Validate methodological invariants in the evidence-validation contract."""

    @classmethod
    def setUpClass(cls) -> None:
        """Read candidate and frozen source-unit contracts once."""
        cls.text = VALIDATION_CONTRACT_PATH.read_text(encoding="utf-8")
        cls.source_text = SOURCE_UNIT_CONTRACT_PATH.read_text(encoding="utf-8")

    def assertContainsAll(self, *fragments: str) -> None:  # noqa: N802
        """Assert that every contract fragment is present."""
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.text)

    def test_validation_is_separate_from_adjudication(self) -> None:
        """Automatic validation never becomes graph acceptance automatically."""
        self.assertContainsAll(
            "parsed candidate → automatically validated candidate",
            "It does not authorize direct graph loading",
            "The validator must not convert `validated` directly into `accepted`",
            "accepted` and `rejected` adjudication outcomes belong to the later adjudication",
        )

    def test_validation_sequence_and_evidence_equations_are_complete(self) -> None:
        """V1-V12 and both literal/offset-coordinate equations are explicit."""
        stages = re.findall(r"^V(\d+)\s", self.text, flags=re.MULTILINE)
        self.assertEqual(stages, [str(index) for index in range(1, 13)])
        self.assertContainsAll(
            "unit.text[startOffsetInUnit:endOffsetInUnit] == evidenceText",
            "canonicalDocument[startOffsetInDocument:endOffsetInDocument] == evidenceText",
            "== sourceUnit.startOffsetInDocument + startOffsetInUnit",
            "== sourceUnit.startOffsetInDocument + endOffsetInUnit",
            "Unicode code-point offsets",
            "A span may not cross a source-unit boundary.",
        )

    def test_candidate_and_normalization_status_are_independent(self) -> None:
        """Pending semantic normalization remains a localized non-blocking review."""
        self.assertContainsAll(
            "candidateValidationStatus",
            "normalizationStatus",
            "SEMANTIC_NORMALIZATION_PENDING_REVIEW",
            "UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY",
            "does not by itself assign\n`needs_review` to the candidate",
            "does not make the envelope\n`partially_valid`",
            "verbati",
        )

    def test_precedence_and_prohibited_relation_branches_are_documented(self) -> None:
        """Role precedence and frozen relation exclusions are explicit."""
        self.assertContainsAll(
            "usesModel supersedes mentionsModel",
            "usesTool supersedes mentionsTool",
            "usesDataset supersedes mentionsDataset",
            "hasCodeRepository supersedes referencesRepository",
            "`usesDataset` and `referencesDataset` may coexist",
            "does not permit `Finding → Hypothesis`",
            "positive-only",
            "no summary relation",
            "no summary relation or TheoreticalBasis-grounding relation is authorized",
            "`reports`, `discussesRelatedWork`, and `Paper → hasLimitation → Limitation`",
            "mutation of deterministic output",
        )

    def test_validation_result_can_report_required_diagnostics(self) -> None:
        """A separate deterministic result binds inputs and detailed stage findings."""
        self.assertContainsAll(
            "validation_results.jsonl",
            '"requestSha256"',
            '"parsedOutputSha256"',
            '"candidateValidationStatus"',
            '"stage"',
            '"code"',
            '"severity"',
            '"message"',
            '"jsonPointer"',
            '"expected"',
            '"observed"',
            '"validatorVersion"',
            '"ruleVersion"',
            '"ontologySha256"',
            '"targetInventorySha256"',
            '"sourceUnitContractSha256"',
            '"candidateSchemaSha256"',
        )

    def test_stable_validation_codes_are_unique_and_stage_owned(self) -> None:
        """The stable-code vocabulary has unique codes and required stage families."""
        section = self.text.split("## 18. Stable validation codes", maxsplit=1)[1]
        section = section.split("## 19. Validation-result record", maxsplit=1)[0]
        blocks = re.findall(r"```text\n(.*?)```", section, flags=re.DOTALL)
        codes = [
            line
            for block in blocks
            for line in block.splitlines()
            if re.fullmatch(r"[A-Z][A-Z0-9_]+", line)
        ]
        self.assertEqual(len(codes), len(set(codes)))
        for heading in (
            "Processing", "Schema", "Request and provenance binding", "Evidence spans",
            "Candidate nodes", "Endpoint resolution", "Candidate edges", "Precedence",
            "Duplicate", "Normalization", "Abstentions", "Deferred resolution",
        ):
            self.assertRegex(section, rf"### 18\.\d+ {re.escape(heading)}")

    def test_contracts_are_final_and_binding_at_frozen_versions(self) -> None:
        """Both artifacts record their approved initial freeze metadata."""
        schema = load_json(SCHEMA_PATH)
        contract_metadata = schema["x-ciroh-contract"]
        self.assertEqual(contract_metadata["status"], "final_and_binding")
        self.assertEqual(contract_metadata["dateFrozen"], "2026-07-30")
        self.assertEqual(schema["properties"]["schemaVersion"]["const"], "0.1.0")
        self.assertIn(
            "**Status:** final and binding for Publication Pilot 1 implementation",
            self.text,
        )
        self.assertIn("**Contract version:** 0.1.1", self.text)
        self.assertIn("**Date frozen:** 2026-07-30", self.text)

    def test_freeze_and_implementation_gates_have_exact_final_counts(self) -> None:
        """All 15 freeze checks pass while all 14 implementation checks remain open."""
        freeze_gate = self.text.split("## 24. Contract-freeze gate", maxsplit=1)[1]
        freeze_gate, implementation_gate = freeze_gate.split(
            "## 25. Implementation-acceptance gate", maxsplit=1
        )
        implementation_gate = implementation_gate.split(
            "## 26. Acceptance statement", maxsplit=1
        )[0]
        self.assertEqual(freeze_gate.count("- [x]"), 15)
        self.assertEqual(freeze_gate.count("- [ ]"), 0)
        self.assertEqual(implementation_gate.count("- [ ]"), 14)
        self.assertEqual(implementation_gate.count("- [x]"), 0)

    def test_reviewed_schema_and_frozen_binding_hashes_match_repository_bytes(self) -> None:
        """The candidate review row and frozen schema constants bind current bytes."""
        schema_hash = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
        self.assertIn(
            f"| `schemas/publication_candidate_output.schema.json` | `{schema_hash}` |",
            self.text,
        )
        schema = load_json(SCHEMA_PATH)
        metadata_properties = schema["$defs"]["metadata"]["properties"]
        self.assertEqual(
            metadata_properties["targetInventorySha256"]["const"], TARGET_PROFILE_SHA256
        )
        self.assertEqual(
            metadata_properties["sourceUnitContractSha256"]["const"],
            SOURCE_UNIT_CONTRACT_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
