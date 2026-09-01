"""Focused synthetic and offline-real tests for Publication M1 extraction."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
import unittest
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.candidate_validation import (  # noqa: E402
    DECLARED_BUT_NOT_CURRENTLY_EMITTED_CODES,
    NOT_AUTHORABLE_IN_M1_VALIDATOR_CODES,
    STRUCTURALLY_EXPRESSIBLE_NOT_DETERMINISTICALLY_EMITTED_CODES,
    _authorization_findings,
    _edge_findings,
    materialize_usable_pipeline_output,
    validate_candidate_envelope,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    RequestBuildError,
    build_development_request,
    canonical_json,
    load_yaml_object,
    sha256_bytes,
    TARGET_INVENTORY_PATH,
)
from src.extraction.llm.publications.response_parser import (  # noqa: E402
    parse_recorded_response,
)
from src.extraction.llm.publications.run_publication_extraction_vertical_slice import (  # noqa: E402
    DEFAULT_PROVENANCE,
    DEFAULT_RAW_RESPONSE,
    run_vertical_slice,
)


FINDING_TARGET = "PUB-N-A-P16-FINDING"
METHOD_TARGET = "PUB-N-A-P13-METHOD"
PRODUCES_TARGET = "PUB-R-C-P07-PRODUCES"


def synthetic_request(
    text: str,
    targets: Sequence[str] = (FINDING_TARGET,),
) -> dict[str, Any]:
    """Return a trusted request with a wholly synthetic canonical source document."""

    request = build_development_request(
        "pub:36:sec:0026:unit:0001",
        [FINDING_TARGET],
        run_id="synthetic-m1-test",
    )
    prefix = "Synthetic header\n"
    document = prefix + text + "\nSynthetic footer\n"
    unit = {
        "contractVersion": "0.1.2",
        "paperID": "synthetic",
        "canonicalArtifactID": "paper:synthetic",
        "sourceUnitID": "pub:synthetic:sec:0001:unit:0001",
        "sourceFile": "synthetic-not-read.md",
        "sectionID": "pub:synthetic:sec:0001",
        "sectionTitleRaw": "Synthetic Results",
        "sectionOrdinal": 1,
        "chunkNumber": 1,
        "text": text,
        "textHash": sha256_bytes(text.encode("utf-8")),
        "canonicalTextSha256": sha256_bytes(document.encode("utf-8")),
        "startOffsetInDocument": len(prefix),
        "endOffsetInDocument": len(prefix) + len(text),
        "eligibility": "eligible",
        "requestEligible": True,
        "validationResults": {"valid": True, "errorCodes": []},
    }
    request.update(
        {
            "sourcePublicationID": "synthetic",
            "sourceArtifactID": "paper:synthetic",
            "primarySourceUnitID": unit["sourceUnitID"],
            "sourceUnit": unit,
            "canonicalDocumentText": document,
            "eligibleOperationalTargetIDs": list(targets),
            "requestID": "publication-request-synthetic",
            "runID": "synthetic-m1-test",
        }
    )
    request.pop("requestInputSha256", None)
    request["requestInputSha256"] = sha256_bytes(canonical_json(request))
    return request


def evidence(request: dict[str, Any], value: str, *, occurrence: int = 0, evidence_id: str = "evidence-0001") -> dict[str, Any]:
    """Return exact synthetic evidence for a selected literal occurrence."""

    positions: list[int] = []
    offset = 0
    while True:
        found = request["sourceUnit"]["text"].find(value, offset)
        if found < 0:
            break
        positions.append(found)
        offset = found + 1
    start = positions[occurrence]
    document_start = request["sourceUnit"]["startOffsetInDocument"] + start
    return {
        "evidenceSpanID": evidence_id,
        "sourceArtifactID": request["sourceArtifactID"],
        "sourceUnitID": request["primarySourceUnitID"],
        "sourceUnitTextHash": request["sourceUnit"]["textHash"],
        "sectionID": request["sourceUnit"]["sectionID"],
        "sectionTitle": request["sourceUnit"]["sectionTitleRaw"],
        "evidenceText": value,
        "startOffsetInUnit": start,
        "endOffsetInUnit": start + len(value),
        "startOffsetInDocument": document_start,
        "endOffsetInDocument": document_start + len(value),
        "evidenceHash": None,
    }


def node(
    candidate_id: str,
    label: str,
    *,
    target: str = FINDING_TARGET,
    ontology_id: str = "A-P16",
    class_name: str = "Finding",
    evidence_ids: Sequence[str] = ("evidence-0001",),
) -> dict[str, Any]:
    """Return one schema-shaped synthetic candidate node."""

    return {
        "candidateID": candidate_id,
        "action": "propose_new",
        "origin": "open_discovery",
        "operationalTargetID": target,
        "ontologyClassID": ontology_id,
        "className": class_name,
        "label": label,
        "labelMode": "verbatim",
        "normalizedLabelProposal": None,
        "identityScope": "source_local",
        "artifactScope": "source_artifact",
        "provisionalIdentity": False,
        "existingNodeID": None,
        "deferredRecordID": None,
        "attributes": [],
        "evidenceSpanIDs": list(evidence_ids),
    }


def edge(
    relation_target: str = PRODUCES_TARGET,
    relation_id: str = "C-P07",
    relation_name: str = "produces",
) -> dict[str, Any]:
    """Return one intra-source edge between two synthetic candidate nodes."""

    return {
        "candidateID": "edge-0001",
        "action": "propose_edge",
        "origin": "open_discovery",
        "operationalRelationID": relation_target,
        "ontologyRelationID": relation_id,
        "relationName": relation_name,
        "relationScope": "intra_source",
        "source": {"referenceType": "candidate_node", "referenceID": "node-0001", "artifactID": None},
        "target": {"referenceType": "candidate_node", "referenceID": "node-0002", "artifactID": None},
        "deferredRecordID": None,
        "evidenceSpanIDs": ["evidence-0001"],
    }


def payload(
    nodes: Sequence[dict[str, Any]],
    spans: Sequence[dict[str, Any]],
    *,
    edges: Sequence[dict[str, Any]] = (),
    abstentions: Sequence[dict[str, Any]] = (),
    deferred: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Return the exact provider-neutral semantic response shape."""

    return {
        "candidateNodes": list(nodes),
        "candidateEdges": list(edges),
        "evidenceSpans": list(spans),
        "abstentions": list(abstentions),
        "deferredRecords": list(deferred),
    }


def validate(request: dict[str, Any], response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Strictly parse and validate a synthetic provider-neutral response."""

    parsed = parse_recorded_response(canonical_json(response), request)
    validation = validate_candidate_envelope(parsed, request)
    usable = materialize_usable_pipeline_output(parsed["parsedEnvelope"], validation)
    return parsed, validation, usable


def codes(validation: dict[str, Any]) -> set[str]:
    """Collect every stable finding code from one validation artifact."""

    found = {item["code"] for item in validation.get("globalFindings", [])}
    for evidence_result in validation.get("evidenceResults", []):
        found.update(item["code"] for item in evidence_result["findings"])
    for result in validation.get("recordResults", []):
        found.update(item["code"] for item in result["findings"])
    return found


class PublicationRequestAndParserTests(unittest.TestCase):
    """Exercise approved development routing and strict parser behavior."""

    def test_approved_request_is_deterministic_and_binds_frozen_target(self) -> None:
        """An approved unit builds twice to byte-identical bounded request JSON."""

        first = build_development_request("pub:36:sec:0026:unit:0001", [FINDING_TARGET], run_id="test-run")
        second = build_development_request("pub:36:sec:0026:unit:0001", [FINDING_TARGET], run_id="test-run")
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["eligibleOperationalTargetIDs"], [FINDING_TARGET])

    def test_nondevelopment_pilot_and_unknown_target_are_rejected(self) -> None:
        """Development mode rejects unapproved, Pilot 1, and unknown target inputs."""

        for unit_id, targets in (
            ("pub:5:sec:0001:unit:0001", [FINDING_TARGET]),
            ("pub:10:sec:0001:unit:0001", [FINDING_TARGET]),
            ("pub:36:sec:0026:unit:0001", ["PUB-N-UNKNOWN"]),
        ):
            with self.subTest(unit=unit_id, targets=targets):
                with self.assertRaises(RequestBuildError):
                    build_development_request(unit_id, targets, run_id="test-run")

    def test_strict_parser_accepts_json_but_never_repairs_malformed_json(self) -> None:
        """Valid JSON parses while fenced or truncated JSON remains processing failure."""

        request = synthetic_request("A finding.")
        valid = parse_recorded_response(canonical_json(payload([], [])), request)
        self.assertEqual(valid["parseStatus"], "parsed")
        for raw in (b'{"candidateNodes": [', b'```json\n{}\n```'):
            with self.subTest(raw=raw):
                failed = parse_recorded_response(raw, request)
                self.assertEqual(failed["parseStatus"], "processing_failed")
                self.assertEqual(failed["processingCode"], "INVALID_JSON")

    def test_schema_invalid_parsed_document_remains_invalid(self) -> None:
        """Strict parsing does not make a structurally incomplete payload valid."""

        request = synthetic_request("A finding.")
        parsed = parse_recorded_response(b'{"candidateNodes":[]}', request)
        validation = validate_candidate_envelope(parsed, request)
        self.assertEqual(validation["envelopeStatus"], "invalid")
        self.assertIn("SCHEMA_VALIDATION_FAILED", codes(validation))

    def test_json_array_passes_v1_and_fails_v2(self) -> None:
        """A valid JSON value with the wrong top-level shape is a V2 failure."""

        request = synthetic_request("A finding.")
        parsed = parse_recorded_response(b"[]", request)
        validation = validate_candidate_envelope(parsed, request)
        self.assertEqual(parsed["parseStatus"], "parsed")
        self.assertEqual(validation["envelopeStatus"], "invalid")
        self.assertIn("SCHEMA_VALIDATION_FAILED", codes(validation))
        self.assertNotIn("INVALID_JSON", codes(validation))

    def test_raw_payload_cannot_overwrite_pipeline_owned_fields(self) -> None:
        """Pipeline metadata survives raw injection and the attempt fails V2."""

        request = synthetic_request("A finding.")
        response = payload([], []) | {
            "metadata": {"requestID": "attacker-authored"},
            "schemaVersion": "attacker-authored",
            "outputStage": "usable_pipeline_output",
        }
        parsed = parse_recorded_response(canonical_json(response), request)
        self.assertEqual(parsed["parsedEnvelope"]["metadata"]["requestID"], request["requestID"])
        self.assertEqual(parsed["parsedEnvelope"]["schemaVersion"], "0.1.0")
        self.assertEqual(parsed["parsedEnvelope"]["outputStage"], "parsed_candidate")
        self.assertEqual(parsed["pipelineOwnedFieldInjectionAttempts"], ["metadata", "outputStage", "schemaVersion"])
        validation = validate_candidate_envelope(parsed, request)
        self.assertEqual(validation["envelopeStatus"], "invalid")
        self.assertIn("FORBIDDEN_FIELD", codes(validation))

    def test_complete_trusted_metadata_binding_mismatches_fail_v3(self) -> None:
        """Every newly enforced frozen request/run metadata field is trusted."""

        request = synthetic_request("A finding.")
        fields = (
            "outputID", "requestScope", "includedCompleteSection", "extractionChannel",
            "targetInventoryProfileID", "targetInventorySchemaVersion",
            "targetInventorySha256", "promptVersion", "promptSha256", "provider", "modelName",
            "modelVersion", "generationParameters", "tokenUsage", "costUSD",
            "retryCount", "responseCreatedAt",
        )
        for field in fields:
            parsed = parse_recorded_response(canonical_json(payload([], [])), request)
            parsed["parsedEnvelope"]["metadata"][field] = "mismatch"
            validation = validate_candidate_envelope(parsed, request)
            with self.subTest(field=field):
                self.assertEqual(validation["envelopeStatus"], "invalid")
                self.assertTrue(any(item["jsonPointer"] == f"/metadata/{field}" for item in validation["globalFindings"]))


class PublicationEvidenceAndAuthorizationTests(unittest.TestCase):
    """Exercise exact Unicode evidence and frozen target authorization failures."""

    def test_exact_unicode_and_repeated_occurrence_evidence_validate(self) -> None:
        """Code-point coordinates select the requested repeated non-ASCII occurrence."""

        request = synthetic_request("α flood β flood produced a finding.")
        span = evidence(request, "flood", occurrence=1)
        response = payload([node("node-0001", "flood")], [span])
        _, validation, usable = validate(request, response)
        self.assertEqual(validation["envelopeStatus"], "valid")
        self.assertEqual(len(usable["candidateNodes"]), 1)
        self.assertEqual(span["startOffsetInUnit"], request["sourceUnit"]["text"].rindex("flood"))

    def test_evidence_literal_offsets_and_hash_fail_independently(self) -> None:
        """Unit, document, literal, and evidence-hash corruption receive stable codes."""

        request = synthetic_request("The finding is 27 ± 1 units.")
        base = evidence(request, "The finding is 27 ± 1 units.")
        mutations = (
            ("unit", lambda item: item.update(startOffsetInUnit=1), "OFFSET_MISMATCH_IN_UNIT"),
            ("document", lambda item: item.update(startOffsetInDocument=item["startOffsetInDocument"] + 1), "UNIT_DOCUMENT_OFFSET_INCONSISTENT"),
            ("literal", lambda item: item.update(evidenceText="The finding is 28 units."), "EVIDENCE_NOT_LITERAL"),
            ("hash", lambda item: item.update(evidenceHash="0" * 64), "EVIDENCE_HASH_MISMATCH"),
        )
        for name, mutate, expected in mutations:
            span = deepcopy(base)
            mutate(span)
            _, validation, _ = validate(request, payload([node("node-0001", "finding")], [span]))
            with self.subTest(case=name):
                self.assertIn(expected, codes(validation))
                self.assertEqual(validation["envelopeStatus"], "invalid")

    def test_unknown_unauthorized_identity_action_and_abstract_targets_fail(self) -> None:
        """V5 rejects unknown, unrouted, mismatched, forbidden, and abstract targets."""

        request = synthetic_request("A finding.")
        span = evidence(request, "A finding.")
        cases: list[tuple[dict[str, Any], dict[str, Any], str]] = []
        unknown = node("node-0001", "finding")
        unknown["operationalTargetID"] = "PUB-N-UNKNOWN"
        cases.append((request, unknown, "UNKNOWN_OPERATIONAL_TARGET"))
        unauthorized_request = synthetic_request("A finding.", [METHOD_TARGET])
        cases.append((unauthorized_request, node("node-0001", "finding"), "TARGET_NOT_INCLUDED_IN_REQUEST"))
        mismatch = node("node-0001", "finding")
        mismatch["ontologyClassID"] = "A-P13"
        mismatch["className"] = "Method"
        cases.append((request, mismatch, "ONTOLOGY_ID_MISMATCH"))
        forbidden = node("node-0001", "finding")
        forbidden.update(action="link_existing", existingNodeID="det:1", identityScope="exact_existing_endpoint")
        cases.append((request, forbidden, "ACTION_NOT_ALLOWED"))
        abstract_request = synthetic_request("software entity", ["PUB-N-A-DOM01-SOFTWAREENTITY"])
        abstract = node("node-0001", "software entity", target="PUB-N-A-DOM01-SOFTWAREENTITY", ontology_id="A-DOM01", class_name="SoftwareEntity")
        cases.append((abstract_request, abstract, "ABSTRACT_CLASS_OUTPUT"))
        for case_request, candidate, expected in cases:
            case_span = evidence(case_request, case_request["sourceUnit"]["text"])
            _, validation, _ = validate(case_request, payload([candidate], [case_span]))
            with self.subTest(expected=expected):
                self.assertIn(expected, codes(validation))


class PublicationNodeRelationLifecycleTests(unittest.TestCase):
    """Exercise V6-V12 nodes, endpoints, edges, conflicts, and lifecycle output."""

    def test_valid_node_source_local_and_pending_normalization(self) -> None:
        """A valid source-local node survives while semantic normalization stays pending."""

        request = synthetic_request("A finding was observed.")
        candidate = node("node-0001", "finding")
        candidate["normalizedLabelProposal"] = "Observed finding"
        _, validation, usable = validate(request, payload([candidate], [evidence(request, "A finding was observed.")]))
        result = validation["recordResults"][0]
        self.assertEqual(result["candidateValidationStatus"], "validated")
        self.assertEqual(result["normalizationStatus"], "pending_review")
        self.assertIn("SEMANTIC_NORMALIZATION_PENDING_REVIEW", codes(validation))
        self.assertEqual(len(usable["candidateNodes"]), 1)

    def test_invalid_node_actions_endpoint_and_attribute_evidence(self) -> None:
        """V6 rejects invalid new/link actions and attributes without valid evidence."""

        request = synthetic_request("RMSE was 4.", ["PUB-N-A-DOM11-EVALUATIONMETRIC"])
        span = evidence(request, "RMSE was 4.")
        metric = node("node-0001", "RMSE", target="PUB-N-A-DOM11-EVALUATIONMETRIC", ontology_id="A-DOM11", class_name="EvaluationMetric")
        metric["attributes"] = [{"attributeName": "value", "value": "4", "evidenceSpanIDs": ["evidence-9999"]}]
        _, validation, _ = validate(request, payload([metric], [span]))
        self.assertIn("ATTRIBUTE_EVIDENCE_MISSING", codes(validation))

        proposed = node("node-0001", "RMSE", target="PUB-N-A-DOM11-EVALUATIONMETRIC", ontology_id="A-DOM11", class_name="EvaluationMetric")
        proposed["existingNodeID"] = "det:metric:1"
        _, proposed_validation, _ = validate(request, payload([proposed], [span]))
        self.assertIn("PROPOSE_NEW_HAS_EXISTING_ENDPOINT", codes(proposed_validation))

        tool_target = "PUB-N-A-DOM02-TOOL-EXISTING-EXACT-ENDPOINT"
        link_request = synthetic_request("ToolX", [tool_target])
        linked = node("node-0001", "ToolX", target=tool_target, ontology_id="A-DOM02", class_name="Tool")
        linked.update(action="link_existing", existingNodeID="det:missing", identityScope="exact_existing_endpoint")
        _, linked_validation, _ = validate(link_request, payload([linked], [evidence(link_request, "ToolX")]))
        self.assertIn("LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED", codes(linked_validation))

    def test_source_exact_attributes_are_grounded_without_universal_normalization_rule(self) -> None:
        """Metric strings are literal while an authorized boolean may normalize."""

        metric_target = "PUB-N-A-DOM11-EVALUATIONMETRIC"
        request = synthetic_request("RMSE was 4.", [metric_target])
        span = evidence(request, "RMSE was 4.")
        metric = node("node-0001", "RMSE", target=metric_target, ontology_id="A-DOM11", class_name="EvaluationMetric")
        metric["attributes"] = [{"attributeName": "value", "value": "4", "evidenceSpanIDs": ["evidence-0001"]}]
        _, valid_result, _ = validate(request, payload([metric], [span]))
        self.assertEqual(valid_result["recordResults"][0]["candidateValidationStatus"], "validated")

        unsupported = deepcopy(metric)
        unsupported["attributes"][0]["value"] = "5"
        _, unsupported_result, _ = validate(request, payload([unsupported], [span]))
        self.assertIn("ATTRIBUTE_EVIDENCE_MISSING", codes(unsupported_result))

        repository_target = "PUB-N-A-C01-REPOSITORY-EXISTING-EXACT-ENDPOINT"
        repository_request = synthetic_request("The repository is a fork.", [repository_target])
        repository_request["deterministicEndpoints"] = [{"nodeID": "repo:1", "className": "Repository", "artifactID": "repo:1"}]
        repository_request.pop("requestInputSha256")
        repository_request["requestInputSha256"] = sha256_bytes(canonical_json(repository_request))
        repository = node("node-0001", "repository", target=repository_target, ontology_id="A-C01", class_name="Repository")
        repository.update(action="link_existing", existingNodeID="repo:1", identityScope="exact_existing_endpoint", artifactScope="external_artifact")
        repository["attributes"] = [{"attributeName": "fork", "value": True, "evidenceSpanIDs": ["evidence-0001"]}]
        _, repository_result, _ = validate(repository_request, payload([repository], [evidence(repository_request, "The repository is a fork.")]))
        self.assertNotIn("ATTRIBUTE_EVIDENCE_MISSING", codes(repository_result))

    def test_parameter_exact_values_and_evidence_supported_calibration_status(self) -> None:
        """Only identity-policy fields require literal Parameter attribute values."""

        parameter_target = "PUB-N-A-DOM12-PARAMETER"
        text = "The coefficient value was 0.25 and was fitted during calibration."
        request = synthetic_request(text, [parameter_target])
        span = evidence(request, text)
        parameter = node(
            "node-0001",
            "coefficient",
            target=parameter_target,
            ontology_id="A-DOM12",
            class_name="Parameter",
        )
        parameter["attributes"] = [
            {"attributeName": "value", "value": "0.25", "evidenceSpanIDs": ["evidence-0001"]},
            {"attributeName": "calibrationStatus", "value": "calibrated", "evidenceSpanIDs": ["evidence-0001"]},
        ]
        _, valid_result, valid_usable = validate(request, payload([parameter], [span]))
        self.assertNotIn("ATTRIBUTE_EVIDENCE_MISSING", codes(valid_result))
        self.assertEqual(len(valid_usable["candidateNodes"]), 1)

        unsupported = deepcopy(parameter)
        unsupported["attributes"][0]["value"] = "0.50"
        _, unsupported_result, unsupported_usable = validate(request, payload([unsupported], [span]))
        self.assertIn("ATTRIBUTE_EVIDENCE_MISSING", codes(unsupported_result))
        self.assertEqual(unsupported_usable["candidateNodes"], [])

    def test_atomicity_review_is_not_usable_output(self) -> None:
        """A clearly multi-proposition discourse label is review-only, not usable."""

        label = "Finding one. Finding two. Finding three."
        request = synthetic_request(label)
        _, validation, usable = validate(request, payload([node("node-0001", label)], [evidence(request, label)]))
        result = validation["recordResults"][0]
        self.assertEqual(result["candidateValidationStatus"], "needs_review")
        self.assertIn("ATOMICITY_VIOLATION", codes(validation))
        self.assertEqual(usable["candidateNodes"], [])

    def test_valid_relation_and_synonym_evidence_without_lexical_proxy(self) -> None:
        """A valid relation is not rejected because evidence uses a synonym."""

        request = synthetic_request("method produced finding", [METHOD_TARGET, FINDING_TARGET, PRODUCES_TARGET])
        span = evidence(request, "method produced finding")
        nodes = [
            node("node-0001", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
            node("node-0002", "finding"),
        ]
        _, validation, usable = validate(request, payload(nodes, [span], edges=[edge()]))
        self.assertEqual(validation["envelopeStatus"], "valid")
        self.assertEqual(len(usable["candidateEdges"]), 1)

        model_target = "PUB-N-A-DOM03D-MLMODEL"
        uses_target = "PUB-R-C-P13-USESMODEL-METHOD-BRANCH"
        synonym_request = synthetic_request("method employed model", [METHOD_TARGET, model_target, uses_target])
        synonym_nodes = [
            node("node-0001", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
            node("node-0002", "model", target=model_target, ontology_id="A-DOM03d", class_name="MLModel"),
        ]
        synonym_edge = edge(uses_target, "C-P13", "usesModel")
        _, synonym_validation, synonym_usable = validate(
            synonym_request,
            payload(synonym_nodes, [evidence(synonym_request, "method employed model")], edges=[synonym_edge]),
        )
        self.assertNotIn("RELATION_EVIDENCE_INSUFFICIENT", codes(synonym_validation))
        self.assertEqual(len(synonym_usable["candidateEdges"]), 1)

    def test_edge_evidence_need_not_repeat_candidate_endpoint_labels(self) -> None:
        """Acronym-only edge evidence does not trigger an endpoint-label proxy."""

        model_target = "PUB-N-A-DOM03D-MLMODEL"
        uses_target = "PUB-R-C-P13-USESMODEL-METHOD-BRANCH"
        text = (
            "The routing method used the National Water Model. "
            "NWM was employed to generate forecasts."
        )
        request = synthetic_request(text, [METHOD_TARGET, model_target, uses_target])
        spans = [
            evidence(request, "The routing method used the National Water Model."),
            evidence(
                request,
                "NWM was employed to generate forecasts.",
                evidence_id="evidence-0002",
            ),
        ]
        nodes = [
            node("node-0001", "routing method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
            node("node-0002", "National Water Model", target=model_target, ontology_id="A-DOM03d", class_name="MLModel"),
        ]
        relation = edge(uses_target, "C-P13", "usesModel")
        relation["evidenceSpanIDs"] = ["evidence-0002"]
        _, validation, usable = validate(request, payload(nodes, spans, edges=[relation]))
        self.assertNotIn("RELATION_EVIDENCE_INSUFFICIENT", codes(validation))
        self.assertEqual(len(usable["candidateEdges"]), 1)

    def test_expressible_relation_roles_have_no_unfrozen_conflict_heuristic(self) -> None:
        """Role coexistence remains valid absent a frozen deterministic conflict rule."""

        model_target = "PUB-N-A-DOM03D-MLMODEL"
        uses_target = "PUB-R-C-P13-USESMODEL-METHOD-BRANCH"
        applies_target = "PUB-R-C-P14-APPLIESTO"
        text = "method used model. method calibrated model."
        request = synthetic_request(
            text,
            [METHOD_TARGET, model_target, uses_target, applies_target],
        )
        spans = [
            evidence(request, "method used model."),
            evidence(request, "method calibrated model.", evidence_id="evidence-0002"),
        ]
        nodes = [
            node("node-0001", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
            node("node-0002", "model", target=model_target, ontology_id="A-DOM03d", class_name="MLModel"),
        ]
        uses = edge(uses_target, "C-P13", "usesModel")
        applies = edge(applies_target, "C-P14", "appliesTo")
        applies["candidateID"] = "edge-0002"
        applies["evidenceSpanIDs"] = ["evidence-0002"]
        _, validation, usable = validate(
            request,
            payload(nodes, spans, edges=[uses, applies]),
        )
        self.assertNotIn("CONFLICTING_RELATION_ROLES", codes(validation))
        self.assertEqual(len(usable["candidateEdges"]), 2)

    def test_invalid_domain_range_direction_and_endpoint(self) -> None:
        """V7-V8 reject unresolved endpoints and reversed operational signatures."""

        request = synthetic_request("finding produced method", [METHOD_TARGET, FINDING_TARGET, PRODUCES_TARGET])
        span = evidence(request, "finding produced method")
        reversed_nodes = [node("node-0001", "finding"), node("node-0002", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method")]
        _, reversed_validation, _ = validate(request, payload(reversed_nodes, [span], edges=[edge()]))
        self.assertIn("INVALID_DOMAIN", codes(reversed_validation))
        self.assertIn("INVALID_RANGE", codes(reversed_validation))

        missing_edge = edge()
        missing_edge["source"] = {"referenceType": "deterministic_node", "referenceID": "det:missing", "artifactID": "paper:synthetic"}
        _, missing_validation, _ = validate(request, payload(reversed_nodes, [span], edges=[missing_edge]))
        self.assertIn("ENDPOINT_REFERENCE_MISSING", codes(missing_validation))

    def test_relation_scope_uses_trusted_endpoint_artifact_ownership(self) -> None:
        """Model-authored artifact IDs cannot override trusted endpoint ownership."""

        request = synthetic_request("method yielded finding", [PRODUCES_TARGET])
        request["deterministicEndpoints"] = [
            {"nodeID": "method:1", "className": "Method", "artifactID": "paper:synthetic"},
            {"nodeID": "finding:1", "className": "Finding", "artifactID": "paper:synthetic"},
        ]
        request.pop("requestInputSha256")
        request["requestInputSha256"] = sha256_bytes(canonical_json(request))
        relation = edge()
        relation["relationScope"] = "inter_source"
        relation["source"] = {"referenceType": "deterministic_node", "referenceID": "method:1", "artifactID": "attacker:artifact"}
        relation["target"] = {"referenceType": "deterministic_node", "referenceID": "finding:1", "artifactID": "paper:synthetic"}
        _, validation, usable = validate(request, payload([], [evidence(request, "method yielded finding")], edges=[relation]))
        self.assertIn("RELATION_SCOPE_MISMATCH", codes(validation))
        self.assertEqual(usable["candidateEdges"], [])

    def test_negative_support_is_prohibited(self) -> None:
        """The positive-only supports branch rejects explicit negative evidence."""

        support_target = "PUB-R-C-P09-SUPPORTS"
        claim_target = "PUB-N-A-P24-CLAIM"
        request = synthetic_request("finding does not support claim", [FINDING_TARGET, claim_target, support_target])
        span = evidence(request, "finding does not support claim")
        nodes = [node("node-0001", "finding"), node("node-0002", "claim", target=claim_target, ontology_id="A-P24", class_name="Claim")]
        relation = edge(support_target, "C-P09", "supports")
        _, validation, _ = validate(request, payload(nodes, [span], edges=[relation]))
        self.assertIn("NEGATIVE_SUPPORT_NOT_AUTHORIZED", codes(validation))

    def test_exact_duplicate_mergeable_repeat_and_possible_duplicate(self) -> None:
        """V10 distinguishes exact, repeated-evidence, and possible local duplicates."""

        exact_request = synthetic_request("finding")
        exact_spans = [
            evidence(exact_request, "finding"),
            evidence(exact_request, "finding", evidence_id="evidence-0002"),
        ]
        exact_nodes = [
            node("node-0001", "finding"),
            node("node-0002", "finding", evidence_ids=("evidence-0002",)),
        ]
        _, exact_validation, exact_usable = validate(exact_request, payload(exact_nodes, exact_spans))
        self.assertIn("EXACT_DUPLICATE_NODE", codes(exact_validation))
        self.assertIn("EXACT_DUPLICATE_EVIDENCE_SPAN", codes(exact_validation))
        self.assertEqual(len(exact_usable["candidateNodes"]), 1)

        repeat_request = synthetic_request("finding then finding")
        spans = [evidence(repeat_request, "finding", occurrence=0), evidence(repeat_request, "finding", occurrence=1, evidence_id="evidence-0002")]
        repeat_nodes = [node("node-0001", "finding"), node("node-0002", "finding", evidence_ids=("evidence-0002",))]
        _, repeat_validation, repeat_usable = validate(repeat_request, payload(repeat_nodes, spans))
        self.assertIn("REPEATED_LOCAL_CANDIDATE_EVIDENCE_MERGED", codes(repeat_validation))
        self.assertEqual(len(repeat_usable["candidateNodes"]), 1)

        possible_request = synthetic_request("Finding and finding")
        possible_spans = [evidence(possible_request, "Finding"), evidence(possible_request, "finding", evidence_id="evidence-0002")]
        possible_nodes = [node("node-0001", "Finding"), node("node-0002", "finding", evidence_ids=("evidence-0002",))]
        _, possible_validation, possible_usable = validate(possible_request, payload(possible_nodes, possible_spans))
        self.assertIn("POSSIBLE_LOCAL_DUPLICATE", codes(possible_validation))
        self.assertEqual(len(possible_usable["candidateNodes"]), 1)

    def test_contextual_occurrences_with_same_label_remain_distinct(self) -> None:
        """Metric occurrences in distinct coordinates are not silently reconciled."""

        metric_target = "PUB-N-A-DOM11-EVALUATIONMETRIC"
        request = synthetic_request("RMSE for Model A; RMSE for Model B", [metric_target])
        spans = [
            evidence(request, "RMSE for Model A"),
            evidence(request, "RMSE for Model B", evidence_id="evidence-0002"),
        ]
        metrics = [
            node("node-0001", "RMSE", target=metric_target, ontology_id="A-DOM11", class_name="EvaluationMetric"),
            node("node-0002", "RMSE", target=metric_target, ontology_id="A-DOM11", class_name="EvaluationMetric", evidence_ids=("evidence-0002",)),
        ]
        _, validation, usable = validate(request, payload(metrics, spans))
        self.assertNotIn("REPEATED_LOCAL_CANDIDATE_EVIDENCE_MERGED", codes(validation))
        self.assertEqual(len(usable["candidateNodes"]), 2)

    def test_edges_close_over_superseded_needs_review_and_deferred_endpoints(self) -> None:
        """V12 excludes edges whose candidate endpoint later becomes inactive."""

        duplicate_request = synthetic_request("method produced finding", [METHOD_TARGET, FINDING_TARGET, PRODUCES_TARGET])
        duplicate_span = evidence(duplicate_request, "method produced finding")
        duplicate_nodes = [
            node("node-0001", "finding"),
            node("node-0002", "finding"),
            node("node-0003", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
        ]
        duplicate_edge = edge()
        duplicate_edge["source"]["referenceID"] = "node-0003"
        _, duplicate_validation, duplicate_usable = validate(
            duplicate_request, payload(duplicate_nodes, [duplicate_span], edges=[duplicate_edge])
        )
        edge_result = next(item for item in duplicate_validation["recordResults"] if item["recordID"] == "edge-0001")
        self.assertEqual(edge_result["candidateValidationStatus"], "rejected")
        self.assertIn("ENDPOINT_LIFECYCLE_INVALID", codes(duplicate_validation))
        self.assertEqual(duplicate_usable["candidateEdges"], [])

        review_label = "Finding one. Finding two. Finding three."
        review_request = synthetic_request(f"method produced {review_label}", [METHOD_TARGET, FINDING_TARGET, PRODUCES_TARGET])
        review_nodes = [
            node("node-0001", "method", target=METHOD_TARGET, ontology_id="A-P13", class_name="Method"),
            node("node-0002", review_label),
        ]
        _, review_validation, review_usable = validate(
            review_request,
            payload(review_nodes, [evidence(review_request, review_request["sourceUnit"]["text"])], edges=[edge()]),
        )
        review_edge_result = next(item for item in review_validation["recordResults"] if item["recordID"] == "edge-0001")
        self.assertEqual(review_edge_result["candidateValidationStatus"], "rejected")
        self.assertEqual(review_usable["candidateEdges"], [])

        dataset_target = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
        references_target = "PUB-R-C-P29-REFERENCESDATASET-EXACT-OMITTED-IDENTIFIER"
        deferred_request = synthetic_request("Paper references dataset", [dataset_target, references_target])
        deferred_request["deterministicEndpoints"] = [{"nodeID": "paper:synthetic", "className": "Paper", "artifactID": "paper:synthetic"}]
        deferred_request["deferredRecordIDs"] = ["deferred:1"]
        deferred_request["deferredRecords"] = [{"deferredRecordID": "deferred:1", "reason": "identifier omitted"}]
        deferred_request.pop("requestInputSha256")
        deferred_request["requestInputSha256"] = sha256_bytes(canonical_json(deferred_request))
        dataset = node("node-0001", "dataset", target=dataset_target, ontology_id="A-D01", class_name="DatasetResource")
        dataset.update(origin="deferred_resolution", identityScope="resolver_pending", artifactScope="external_artifact", deferredRecordID="deferred:1")
        reference = edge(references_target, "C-P29", "referencesDataset")
        reference.update(action="resolve_deferred", origin="deferred_resolution", relationScope="inter_source", deferredRecordID="deferred:1")
        reference["source"] = {"referenceType": "deterministic_node", "referenceID": "paper:synthetic", "artifactID": "paper:synthetic"}
        reference["target"] = {"referenceType": "candidate_node", "referenceID": "node-0001", "artifactID": None}
        deferred_record = {"deferredRecordID": "deferred:1", "proposedDisposition": "remain_deferred", "proposedOperationalTargetID": None, "relatedCandidateIDs": ["node-0001"], "evidenceSpanIDs": [], "rationale": "Identity remains unresolved."}
        _, deferred_validation, deferred_usable = validate(
            deferred_request,
            payload([dataset], [evidence(deferred_request, "Paper references dataset")], edges=[reference], deferred=[deferred_record]),
        )
        deferred_edge_result = next(item for item in deferred_validation["recordResults"] if item["recordID"] == "edge-0001")
        self.assertEqual(deferred_edge_result["candidateValidationStatus"], "rejected")
        self.assertEqual(deferred_usable["candidateEdges"], [])

    def test_stronger_role_precedence_abstention_and_deferred(self) -> None:
        """V9/V11 apply stronger-role suppression and controlled non-candidate states."""

        model_target = "PUB-N-A-DOM03D-MLMODEL"
        uses_target = "PUB-R-C-P13-USESMODEL-PAPER-BRANCH"
        mentions_target = "PUB-R-C-P23-MENTIONSMODEL"
        request = synthetic_request("Paper mentions model and uses model", [model_target, uses_target, mentions_target])
        request["deterministicEndpoints"] = [{"nodeID": "paper:synthetic", "className": "Paper", "artifactID": "paper:synthetic"}]
        request.pop("requestInputSha256")
        request["requestInputSha256"] = sha256_bytes(canonical_json(request))
        span = evidence(request, "Paper mentions model and uses model")
        model = node("node-0001", "model", target=model_target, ontology_id="A-DOM03d", class_name="MLModel")
        uses = edge(uses_target, "C-P13", "usesModel")
        mentions = deepcopy(uses)
        for index, relation in enumerate((uses, mentions), start=1):
            relation["candidateID"] = f"edge-{index:04d}"
            relation["source"] = {"referenceType": "deterministic_node", "referenceID": "paper:synthetic", "artifactID": "paper:synthetic"}
            relation["target"] = {"referenceType": "candidate_node", "referenceID": "node-0001", "artifactID": None}
        mentions.update(operationalRelationID=mentions_target, ontologyRelationID="C-P23", relationName="mentionsModel")
        _, precedence_validation, precedence_usable = validate(request, payload([model], [span], edges=[uses, mentions]))
        self.assertIn("WEAKER_RELATION_SUPERSEDED", codes(precedence_validation))
        self.assertEqual(len(precedence_usable["candidateEdges"]), 1)

        abstention_request = synthetic_request("No defensible finding.")
        abstention = {"abstentionID": "abstention-0001", "scope": "operational_target", "operationalTargetID": FINDING_TARGET, "deferredRecordID": None, "reason": "insufficient_evidence", "evidenceSpanIDs": [], "competingOperationalTargetIDs": [], "relatedCandidateIDs": [], "rationale": "No direct result is stated."}
        _, abstention_validation, abstention_usable = validate(abstention_request, payload([], [], abstentions=[abstention]))
        self.assertEqual(abstention_validation["envelopeStatus"], "valid")
        self.assertEqual(abstention_usable["candidateNodes"], [])

        deferred_request = synthetic_request("Unresolved dataset.", ["PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"])
        deferred_request["deferredRecordIDs"] = ["deferred:1"]
        deferred_request["deferredRecords"] = [{"deferredRecordID": "deferred:1", "reason": "identifier omitted"}]
        deferred_request.pop("requestInputSha256")
        deferred_request["requestInputSha256"] = sha256_bytes(canonical_json(deferred_request))
        deferred_span = evidence(deferred_request, "dataset")
        deferred_node = node(
            "node-0001",
            "dataset",
            target="PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B",
            ontology_id="A-D01",
            class_name="DatasetResource",
        )
        deferred_node.update(
            origin="deferred_resolution",
            identityScope="resolver_pending",
            artifactScope="external_artifact",
            deferredRecordID="deferred:1",
        )
        deferred_record = {"deferredRecordID": "deferred:1", "proposedDisposition": "remain_deferred", "proposedOperationalTargetID": None, "relatedCandidateIDs": ["node-0001"], "evidenceSpanIDs": [], "rationale": "Exact identity remains unresolved."}
        _, deferred_validation, deferred_usable = validate(deferred_request, payload([deferred_node], [deferred_span], deferred=[deferred_record]))
        self.assertEqual(deferred_validation["recordResults"][0]["candidateValidationStatus"], "deferred")
        self.assertEqual(deferred_validation["recordResults"][1]["recordValidationStatus"], "deferred")
        self.assertEqual(deferred_validation["envelopeStatus"], "valid")
        self.assertEqual(deferred_usable["candidateNodes"], [])

    def test_processing_failure_is_not_abstention_and_hashes_are_stable(self) -> None:
        """V1 processing failure stays distinct and repeated V12 outputs hash identically."""

        request = synthetic_request("finding")
        failed_parse = parse_recorded_response(b"{", request)
        failed = validate_candidate_envelope(failed_parse, request)
        self.assertEqual(failed["envelopeStatus"], "processing_failed")
        self.assertEqual(failed["recordResults"][0]["recordType"], "processing_failure")

        response = payload([node("node-0001", "finding")], [evidence(request, "finding")])
        first = validate(request, response)
        second = validate(request, response)
        self.assertEqual(canonical_json(first[1]), canonical_json(second[1]))
        self.assertEqual(first[1]["validationResultsHash"], second[1]["validationResultsHash"])
        self.assertEqual(first[2]["usablePipelineOutputHash"], second[2]["usablePipelineOutputHash"])
        for result in first[1]["recordResults"]:
            projection = {key: value for key, value in result.items() if key != "validationResultHash"}
            self.assertEqual(result["validationResultHash"], sha256_bytes(canonical_json(projection)))


class PublicationRelationSignatureCoverageTests(unittest.TestCase):
    """Generate structural relation-signature checks from the frozen profile."""

    def test_every_active_relation_signature_accepts_exact_and_rejects_invalid_domain(self) -> None:
        """Each candidate relation signature receives positive and negative coverage."""

        profile = load_yaml_object(TARGET_INVENTORY_PATH)
        active_rows = [
            row
            for row in profile["relation_targets"]
            if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"}
            and row.get("pilot_treatment") not in {"out_of_scope", "separate_follow_on_protocol"}
        ]
        signature_count = 0
        for row in active_rows:
            for signature in row["operational_signatures"]:
                signature_count += 1
                source_class = signature["domain"]["classes"][0]
                target_class = signature["range"]["classes"][0]
                relation = {
                    "operationalRelationID": row["operational_id"],
                    "ontologyRelationID": row["formal_relations"][0]["id"],
                    "relationName": row["formal_relations"][0]["name"],
                    "action": row["allowed_actions"][0],
                    "origin": "deferred_resolution" if row["allowed_actions"][0] == "resolve_deferred" else "open_discovery",
                    "deferredRecordID": "deferred:1" if row["allowed_actions"][0] == "resolve_deferred" else None,
                    "relationScope": "intra_source",
                    "source": {"referenceType": "deterministic_node", "referenceID": "source:1", "artifactID": "paper:synthetic"},
                    "target": {"referenceType": "deterministic_node", "referenceID": "target:1", "artifactID": "paper:synthetic"},
                    "evidenceSpanIDs": ["evidence-0001"],
                }
                request = {
                    "sourceArtifactID": "paper:synthetic",
                    "eligibleOperationalTargetIDs": [row["operational_id"]],
                    "deferredRecordIDs": ["deferred:1"] if relation["deferredRecordID"] else [],
                    "deterministicEndpoints": [
                        {"nodeID": "source:1", "className": source_class, "artifactID": "paper:synthetic"},
                        {"nodeID": "target:1", "className": target_class, "artifactID": "paper:synthetic"},
                    ],
                    "acceptedLocalCandidateEndpoints": [],
                }
                authorization = _authorization_findings(relation, "/candidateEdges/0", row, request, edge=True)
                valid_findings, _, _ = _edge_findings(
                    relation,
                    "/candidateEdges/0",
                    row,
                    request,
                    {"evidence-0001": {"evidenceText": "positive relation evidence"}},
                    {"evidence-0001": True},
                    {},
                    {},
                )
                with self.subTest(target=row["operational_id"], case="valid"):
                    self.assertEqual(authorization, [])
                    self.assertNotIn("INVALID_DOMAIN", {item["code"] for item in valid_findings})
                    self.assertNotIn("INVALID_RANGE", {item["code"] for item in valid_findings})

                invalid_request = deepcopy(request)
                invalid_request["deterministicEndpoints"][0]["className"] = "NotAnAuthorizedDomain"
                invalid_findings, _, _ = _edge_findings(
                    relation,
                    "/candidateEdges/0",
                    row,
                    invalid_request,
                    {"evidence-0001": {"evidenceText": "positive relation evidence"}},
                    {"evidence-0001": True},
                    {},
                    {},
                )
                with self.subTest(target=row["operational_id"], case="invalid-domain"):
                    self.assertIn("INVALID_DOMAIN", {item["code"] for item in invalid_findings})
        self.assertEqual((len(active_rows), signature_count), (27, 27))

    def test_stable_code_vocabulary_distinguishes_executable_conditions(self) -> None:
        """Separate executable, expressible-only, and unavailable stable codes."""

        contract = (PROJECT_ROOT / "docs/publication_evidence_validation_contract.md").read_text(encoding="utf-8")
        section = contract.split("## 18. Stable validation codes", 1)[1].split("## 19. Validation-result record", 1)[0]
        declared = {
            line
            for block in re.findall(r"```text\n(.*?)```", section, flags=re.DOTALL)
            for line in block.splitlines()
            if re.fullmatch(r"[A-Z][A-Z0-9_]+", line)
        }
        self.assertEqual(len(declared), 102)
        self.assertTrue(DECLARED_BUT_NOT_CURRENTLY_EMITTED_CODES <= declared)
        self.assertEqual(
            STRUCTURALLY_EXPRESSIBLE_NOT_DETERMINISTICALLY_EMITTED_CODES,
            {"CONFLICTING_RELATION_ROLES", "RELATION_EVIDENCE_INSUFFICIENT"},
        )
        self.assertEqual(len(NOT_AUTHORABLE_IN_M1_VALIDATOR_CODES), 6)
        self.assertEqual(len(declared - DECLARED_BUT_NOT_CURRENTLY_EMITTED_CODES), 94)


class PublicationRealVerticalSliceTests(unittest.TestCase):
    """Prove the approved real DEV-04 path and all artifacts are reproducible."""

    def test_real_dev04_vertical_slice_is_byte_identical(self) -> None:
        """Two isolated executions produce identical canonical downstream artifacts."""

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_vertical_slice(output_dir=Path(first_dir), raw_response_path=DEFAULT_RAW_RESPONSE, provenance_path=DEFAULT_PROVENANCE)
            second = run_vertical_slice(output_dir=Path(second_dir), raw_response_path=DEFAULT_RAW_RESPONSE, provenance_path=DEFAULT_PROVENANCE)
            names = (
                "publication_m1_request.json",
                "publication_m1_prompt_artifact.json",
                "publication_m1_parsed_candidate.json",
                "publication_m1_validation_results.json",
                "publication_m1_usable_pipeline_output.json",
                "publication_m1_reproducibility_record.json",
            )
            for name in names:
                with self.subTest(artifact=name):
                    self.assertEqual((Path(first_dir) / name).read_bytes(), (Path(second_dir) / name).read_bytes())
            self.assertEqual(first["validation"]["envelopeStatus"], "valid")
            self.assertEqual(len(first["usablePipelineOutput"]["candidateNodes"]), 1)
            self.assertEqual(first["reproducibility"]["reproducibilityRecordHash"], second["reproducibility"]["reproducibilityRecordHash"])


if __name__ == "__main__":
    unittest.main()
