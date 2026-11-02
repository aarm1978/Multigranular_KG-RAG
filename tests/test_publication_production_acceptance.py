"""Focused tests for Step 4 deterministic production acceptance."""

from copy import deepcopy
import unittest

from src.extraction.llm.publications.production_acceptance import (
    ProductionAcceptanceError,
    derive_accepted_semantic_projection,
    derive_unresolved_identity_sidecar,
    run_attempt_controller,
)
from src.extraction.llm.publications.request_builder import canonical_json


def request() -> dict:
    """Return a minimal trusted request fixture."""

    return {
        "requestID": "request-1", "requestInputSha256": "request-hash",
        "authorityBundleID": "bundle-1", "authorities": {"ontology": {"version": "0.1.5"}},
        "sourceArtifactID": "paper-1", "sourceUnit": {"sourceUnitID": "unit-1"},
    }


def parsed_attempt(number: int = 1) -> dict:
    """Return one processable attempt with every relevant lifecycle state."""

    envelope = {
        "candidateNodes": [
            {"candidateID": "valid", "className": "Method", "ontologyClassID": "A-P06", "operationalTargetID": "N1", "evidenceSpanIDs": ["e1"]},
            {"candidateID": "rejected", "className": "Method", "evidenceSpanIDs": ["e1"]},
            {"candidateID": "review", "className": "Method", "evidenceSpanIDs": ["e1"]},
            {"candidateID": "superseded", "className": "Method", "evidenceSpanIDs": ["e1"]},
            {"candidateID": "deferred", "className": "Method", "evidenceSpanIDs": ["e1"]},
        ],
        "candidateEdges": [
            {"candidateID": "edge-valid", "relationName": "usesModel", "ontologyRelationID": "C-P13", "operationalRelationID": "R1", "source": {"referenceType": "candidate_node", "referenceID": "valid"}, "target": {"referenceType": "deterministic_node", "referenceID": "paper-node", "artifactID": "paper-1"}, "evidenceSpanIDs": ["e1"]},
            {"candidateID": "edge-rejected", "relationName": "usesModel", "ontologyRelationID": "C-P13", "operationalRelationID": "R1", "source": {"referenceType": "candidate_node", "referenceID": "valid"}, "target": {"referenceType": "deterministic_node", "referenceID": "paper-node", "artifactID": "paper-1"}, "evidenceSpanIDs": ["e1"]},
        ],
        "evidenceSpans": [{"evidenceSpanID": "e1", "sourceUnitID": "unit-1", "evidenceText": "method", "startOffsetInUnit": 0, "endOffsetInUnit": 6, "startOffsetInDocument": 10, "endOffsetInDocument": 16}],
        "abstentions": [{"abstentionID": "a1"}], "deferredRecords": [{"deferredRecordID": "d1"}],
    }
    results = [
        {"recordType": "candidate_node", "recordID": "valid", "candidateValidationStatus": "validated", "findings": []},
        {"recordType": "candidate_node", "recordID": "rejected", "candidateValidationStatus": "rejected", "findings": []},
        {"recordType": "candidate_node", "recordID": "review", "candidateValidationStatus": "needs_review", "findings": [{"code": "POSSIBLE_LOCAL_DUPLICATE"}]},
        {"recordType": "candidate_node", "recordID": "superseded", "candidateValidationStatus": "superseded", "findings": []},
        {"recordType": "candidate_node", "recordID": "deferred", "candidateValidationStatus": "deferred", "findings": []},
        {"recordType": "candidate_edge", "recordID": "edge-valid", "candidateValidationStatus": "validated", "findings": []},
        {"recordType": "candidate_edge", "recordID": "edge-rejected", "candidateValidationStatus": "rejected", "findings": []},
        {"recordType": "abstention", "recordID": "a1", "recordValidationStatus": "validated", "findings": []},
        {"recordType": "deferred_record", "recordID": "d1", "recordValidationStatus": "deferred", "findings": []},
    ]
    return {
        "attemptNumber": number, "requestInputSha256": "request-hash", "providerInputSha256": "provider-hash",
        "authorityBundleID": "bundle-1", "requestedModel": "model", "reasoningEffort": "medium", "maxOutputTokens": 100,
        "modelAuthorableSchemaSha256": "schema-hash", "provider": "OpenAI", "toolConfiguration": "none", "store": False,
        "parserResult": {"parseStatus": "parsed", "parsedEnvelope": envelope},
        "validation": {"validationResultsHash": "validation-hash", "recordResults": results, "evidenceResults": [{"evidenceSpanID": "e1", "valid": True}]},
        "usablePipelineOutput": {"outputStage": "usable_pipeline_output", "requestID": "request-1", "outputID": "output-1", "validationResultsHash": "validation-hash", "usablePipelineOutputHash": "usable-hash", "candidateNodes": [deepcopy(envelope["candidateNodes"][0])], "candidateEdges": [deepcopy(envelope["candidateEdges"][0])]},
    }


def failed_attempt(number: int) -> dict:
    """Return an auditable technical processing failure."""

    result = parsed_attempt(number)
    result["parserResult"] = {"parseStatus": "processing_failed", "processingCode": "TIMEOUT"}
    result["validation"] = {"envelopeStatus": "processing_failed", "recordResults": [{"recordType": "processing_failure"}]}
    result["usablePipelineOutput"] = {"candidateNodes": [], "candidateEdges": []}
    return result


def semantic_rejection_attempt(number: int) -> dict:
    """Return a processable response whose semantics are wholly rejected."""

    result = parsed_attempt(number)
    result["validation"]["envelopeStatus"] = "invalid"
    result["validation"]["recordResults"] = [
        {"recordType": "candidate_node", "recordID": "rejected", "candidateValidationStatus": "rejected", "findings": []}
    ]
    result["usablePipelineOutput"]["candidateNodes"] = []
    return result


class ProductionAcceptanceTests(unittest.TestCase):
    """Protect policy selection, lifecycle exclusion, and artifact separation."""

    def test_first_processable_response_stops_retry(self) -> None:
        calls: list[int] = []
        selection = run_attempt_controller(lambda number: calls.append(number) or parsed_attempt(number))
        self.assertEqual(calls, [1])
        self.assertEqual(selection["selectedAttemptNumber"], 1)
        self.assertEqual(selection["selectionDisposition"], "first_processable_response_selected")

    def test_processable_semantic_rejection_cannot_trigger_resampling(self) -> None:
        calls: list[int] = []
        selection = run_attempt_controller(
            lambda number: calls.append(number) or semantic_rejection_attempt(number)
        )
        self.assertEqual(calls, [1])
        self.assertEqual(selection["selectedAttemptNumber"], 1)

    def test_one_technical_retry_then_selection(self) -> None:
        calls: list[int] = []
        selection = run_attempt_controller(lambda number: calls.append(number) or (failed_attempt(number) if number == 1 else parsed_attempt(number)))
        self.assertEqual(calls, [1, 2])
        self.assertEqual(selection["selectedAttemptNumber"], 2)
        self.assertEqual(len(selection["attempts"]), 2)

    def test_only_approved_processing_codes_are_retry_eligible(self) -> None:
        for code in ("INVALID_JSON", "TIMEOUT", "API_ERROR", "TRUNCATED_RESPONSE", "TOKEN_LIMIT"):
            with self.subTest(code=code):
                calls: list[int] = []
                def runner(number: int) -> dict:
                    value = failed_attempt(number) if number == 1 else parsed_attempt(number)
                    value["parserResult"]["processingCode"] = code if number == 1 else value["parserResult"].get("processingCode")
                    calls.append(number)
                    return value
                selection = run_attempt_controller(runner)
                self.assertEqual(calls, [1, 2])
                self.assertEqual(selection["selectedAttemptNumber"], 2)

    def test_retry_exhaustion_has_no_selected_semantics(self) -> None:
        selection = run_attempt_controller(failed_attempt)
        self.assertIsNone(selection["selectedAttemptNumber"])
        self.assertEqual(selection["selectionDisposition"], "retry_exhausted_processing_failure")
        with self.assertRaises(ProductionAcceptanceError):
            derive_accepted_semantic_projection(selection, request())

    def test_binding_failures_are_terminal_and_do_not_retry(self) -> None:
        for code in ("ENDPOINT_BINDING_FAILED", "EVIDENCE_BINDING_FAILED"):
            with self.subTest(code=code):
                calls: list[int] = []
                def runner(number: int) -> dict:
                    value = failed_attempt(number)
                    value["parserResult"]["processingCode"] = code
                    calls.append(number)
                    return value
                selection = run_attempt_controller(runner)
                self.assertEqual(calls, [1])
                self.assertIsNone(selection["selectedAttemptNumber"])
                self.assertEqual(selection["selectionDisposition"], "terminal_non_retry_eligible_processing_failure")

    def test_retry_exhausted_is_terminal_and_does_not_retry(self) -> None:
        calls: list[int] = []
        def runner(number: int) -> dict:
            value = failed_attempt(number)
            value["parserResult"]["processingCode"] = "RETRY_EXHAUSTED"
            calls.append(number)
            return value
        selection = run_attempt_controller(runner)
        self.assertEqual(calls, [1])
        self.assertEqual(selection["selectionDisposition"], "terminal_non_retry_eligible_processing_failure")

    def test_retry_cannot_change_immutable_provider_identity(self) -> None:
        def runner(number: int) -> dict:
            value = failed_attempt(number) if number == 1 else parsed_attempt(number)
            if number == 2:
                value["providerInputSha256"] = "changed"
            return value
        with self.assertRaises(ProductionAcceptanceError):
            run_attempt_controller(runner)

    def test_retry_rejects_schema_and_provider_configuration_drift(self) -> None:
        for field, changed in (("modelAuthorableSchemaSha256", "other-schema"), ("provider", "OtherProvider"), ("toolConfiguration", "tool"), ("store", True)):
            with self.subTest(field=field):
                def runner(number: int) -> dict:
                    value = failed_attempt(number) if number == 1 else parsed_attempt(number)
                    if number == 2:
                        value[field] = changed
                    return value
                with self.assertRaises(ProductionAcceptanceError):
                    run_attempt_controller(runner)

    def test_projection_uses_only_v12_usable_validated_candidates(self) -> None:
        selection = run_attempt_controller(parsed_attempt)
        projection = derive_accepted_semantic_projection(selection, request())
        self.assertEqual([node["candidateID"] for node in projection["acceptedNodes"]], ["valid"])
        self.assertTrue(projection["step7PredictionContent"])
        self.assertEqual(projection["acceptedNodes"][0]["evidenceOccurrences"][0]["canonicalPaperID"], "paper-1")
        self.assertEqual(projection["acceptedNodes"][0]["candidate"]["candidateID"], "valid")
        self.assertEqual(selection["attempts"][0]["parserResult"]["parsedEnvelope"]["abstentions"][0]["abstentionID"], "a1")

    def test_projection_includes_only_validated_usable_edges(self) -> None:
        projection = derive_accepted_semantic_projection(
            run_attempt_controller(parsed_attempt), request()
        )
        self.assertEqual([edge["candidateID"] for edge in projection["acceptedEdges"]], ["edge-valid"])
        self.assertEqual(projection["acceptedEdges"][0]["sourceID"], "request-1#node#valid")
        self.assertNotIn(b"edge-rejected", canonical_json(projection))

    def test_attempt_audit_preserves_excluded_lifecycle_and_nonsemantic_records(self) -> None:
        selection = run_attempt_controller(parsed_attempt)
        results = selection["attempts"][0]["validation"]["recordResults"]
        statuses = {
            row["recordID"]: row.get("candidateValidationStatus", row.get("recordValidationStatus"))
            for row in results
        }
        self.assertEqual(
            statuses,
            {"valid": "validated", "rejected": "rejected", "review": "needs_review", "superseded": "superseded", "deferred": "deferred", "edge-valid": "validated", "edge-rejected": "rejected", "a1": "validated", "d1": "deferred"},
        )
        envelope = selection["attempts"][0]["parserResult"]["parsedEnvelope"]
        self.assertEqual(envelope["abstentions"], [{"abstentionID": "a1"}])
        self.assertEqual(envelope["deferredRecords"], [{"deferredRecordID": "d1"}])

    def test_projection_hash_is_deterministic(self) -> None:
        first = derive_accepted_semantic_projection(run_attempt_controller(parsed_attempt), request())
        second = derive_accepted_semantic_projection(run_attempt_controller(parsed_attempt), request())
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertTrue(first["acceptedSemanticProjectionHash"])

    def test_possible_duplicate_sidecar_is_separate_from_projection_and_step7(self) -> None:
        selection = run_attempt_controller(parsed_attempt)
        projection = derive_accepted_semantic_projection(selection, request())
        sidecar = derive_unresolved_identity_sidecar(selection, request())
        self.assertEqual([row["recordID"] for row in sidecar["records"]], ["review"])
        self.assertNotIn("review", [row["candidateID"] for row in projection["acceptedNodes"]])
        self.assertTrue(sidecar["notAcceptedSemanticProjection"])
        self.assertTrue(sidecar["notAcceptedKGContent"])
        self.assertTrue(sidecar["notStep7PredictionContent"])
        self.assertTrue(sidecar["unresolvedIdentitySidecarHash"])


if __name__ == "__main__":
    unittest.main()
