"""Focused offline readiness checks for the Step 6A Production runner."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications.production_runner import (
    MAX_OUTPUT_TOKENS, _prepared_request, _targets, derive_production_preflight, execute_with_provider_fixture, main,
)
from src.extraction.llm.publications.openai_provider import OpenAIProviderError
from src.extraction.llm.publications.step5_freeze_materialization import _inputs


class ProductionRunnerTests(unittest.TestCase):
    def test_monitor_targets_are_selected_via_frozen_target_authority(self) -> None:
        """Monitor membership is target metadata, never a substring of an ID."""
        from src.extraction.llm.publications.authority_bundle import V015_SCHEMA013
        from src.extraction.llm.publications.request_builder import load_yaml_object
        profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
        rows = {row["operational_id"]: row for row in [*profile["node_targets"], *profile["relation_targets"]]}
        _, routing = _inputs()
        self.assertTrue(any(any(rows[target]["pilot_treatment"] == "extract_and_monitor" for target in _targets(route, rows)) for route in routing.values() if any(target in rows for target in [*route["eligibleNodeOperationalTargetIDs"], *route["eligibleRelationOperationalTargetIDs"]])))

    def test_population_and_frozen_n6_reproduction(self) -> None:
        preflight = derive_production_preflight()
        self.assertEqual(preflight["populationAuthority"]["count"], 227)
        self.assertEqual(len(preflight["humanCoreN5PrimarySourceUnitIDs"]), 5)
        self.assertEqual(len(preflight["complementaryN6PrimarySourceUnitIDs"]), 6)
        self.assertTrue(all(row["matched"] for row in preflight["n6FrozenEnvelopeReproduction"]))
        p46 = next(row for row in preflight["n6FrozenEnvelopeReproduction"] if row["primarySourceUnitID"] == "pub:46:sec:0006:unit:0001")
        self.assertEqual(p46["publication46SameSectionContext"], ["pub:46:sec:0006:unit:0002"])
        self.assertEqual(preflight["productionConfiguration"]["maxOutputTokens"], 32768)
        from src.extraction.llm.publications.authority_bundle import V015_SCHEMA013
        from src.extraction.llm.publications.request_builder import load_yaml_object
        profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
        treatments = {row["operational_id"]: row.get("pilot_treatment") for row in [*profile["node_targets"], *profile["relation_targets"]]}
        self.assertTrue(any(treatments[target] == "extract_and_monitor" for row in preflight["requests"] for target in row["productionTargetIDs"]))
        self.assertTrue(all(row["requestID"] in row["outputID"] or row["requestInputSha256"][:20] in row["outputID"] for row in preflight["requests"]))

    def test_fixture_provider_receives_explicit_32768_and_stops_at_processable_response(self) -> None:
        inventory, routing = _inputs()
        prepared = _prepared_request("pub:276:sec:0019:unit:0001", inventory, routing)
        calls = []
        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        def fixture(body, budget):
            calls.append((body["max_output_tokens"], budget, body.get("tools")))
            return json.dumps(payload).encode("utf-8")
        result = execute_with_provider_fixture(prepared, fixture)
        self.assertEqual(calls, [(MAX_OUTPUT_TOKENS, MAX_OUTPUT_TOKENS, None)])
        self.assertEqual(result["attemptSelection"]["selectedAttemptNumber"], 1)

    def test_technical_failure_is_preserved_and_retried_once(self) -> None:
        inventory, routing = _inputs()
        prepared = _prepared_request("pub:276:sec:0019:unit:0001", inventory, routing)
        calls = []
        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        def fixture(_body, _budget):
            calls.append(True)
            if len(calls) == 1:
                raise OpenAIProviderError("transport unavailable")
            return json.dumps(payload).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            result = execute_with_provider_fixture(prepared, fixture, artifact_root=Path(directory))
            self.assertEqual(len(result["attemptSelection"]["attempts"]), 2)
            self.assertTrue((Path(directory) / "attempt-01" / "lifecycle.json").exists())

    def test_deterministic_downstream_exception_does_not_retry(self) -> None:
        inventory, routing = _inputs()
        prepared = _prepared_request("pub:276:sec:0019:unit:0001", inventory, routing)
        with patch("src.extraction.llm.publications.production_runner._downstream", side_effect=AssertionError("binding defect")):
            with self.assertRaisesRegex(AssertionError, "binding defect"):
                execute_with_provider_fixture(prepared, lambda _body, _budget: b"{}")

    def test_detailed_fixture_durably_preserves_authentic_attempt_artifacts(self) -> None:
        inventory, routing = _inputs()
        prepared = _prepared_request("pub:276:sec:0019:unit:0001", inventory, routing)
        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        detailed = {"rawOutput": json.dumps(payload).encode("utf-8"), "providerResponse": {"id": "resp-fixture", "status": "completed"}, "providerMetadata": {"responseID": "resp-fixture", "returnedModel": "gpt-5.6-sol"}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            execute_with_provider_fixture(prepared, lambda _body, _budget: detailed, artifact_root=root)
            attempt = root / "attempt-01"
            for name in ("provider_request.json", "provider_response.json", "provider_metadata.json", "raw_model_output.json", "lifecycle.json", "parser_result.json", "validation_results.json", "usable_pipeline_output.json"):
                self.assertTrue((attempt / name).exists(), name)

    def test_cli_requires_explicit_live_flag(self) -> None:
        with patch("src.extraction.llm.publications.production_runner.materialize_run_manifest", return_value={"manifestSha256": "fixture"}) as materialize, patch("src.extraction.llm.publications.production_runner.execute_live_run") as execute:
            self.assertEqual(main([]), 0)
            materialize.assert_called_once()
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
