"""Focused offline readiness checks for the Step 6A Production runner."""

import json
import socket
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications.production_runner import (
    DEFAULT_LIVE_ROOT, MAX_OUTPUT_TOKENS, _prepared_request, _targets, derive_production_preflight, execute_with_provider_fixture, main, recover_timeout_request,
)
from src.extraction.llm.publications.openai_provider import OpenAIProviderError, _http_post_json
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

    def test_socket_timeout_is_provider_error(self) -> None:
        with patch("src.extraction.llm.publications.openai_provider.urlopen", side_effect=socket.timeout("The read operation timed out")):
            with self.assertRaises(OpenAIProviderError):
                _http_post_json("fixture-key", {"model": "gpt-5.6-sol"})

    def test_timeout_recovery_preserves_attempt_one_and_only_dispatches_two(self) -> None:
        request_id = "publication-c1-request-9d725039aaeef06d1a46"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(DEFAULT_LIVE_ROOT / "publication_c1_run_manifest.json", root / "publication_c1_run_manifest.json")
            source = DEFAULT_LIVE_ROOT / "requests" / request_id / "attempt-01"
            target = root / "requests" / request_id / "attempt-01"; target.parent.mkdir(parents=True)
            shutil.copytree(source, target)
            before = {path.name: path.read_bytes() for path in target.iterdir()}
            inventory, routing = _inputs(); prepared = _prepared_request("pub:54:sec:0022:unit:0001", inventory, routing)
            payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}; calls=[]
            with patch("src.extraction.llm.publications.production_runner._prepared_request", return_value=prepared):
                result = recover_timeout_request(request_id, root, provider_call=lambda body, budget: calls.append((body, budget)) or json.dumps(payload).encode())
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], 32768)
            self.assertEqual(result["attemptSelection"]["selectedAttemptNumber"], 2)
            self.assertEqual(before, {path.name: path.read_bytes() for path in target.iterdir()})
            self.assertTrue((root / "requests" / request_id / "attempt-02" / "lifecycle.json").exists())

    def test_timeout_recovery_hash_drift_fails_closed_and_live_flag_is_required(self) -> None:
        request_id = "publication-c1-request-9d725039aaeef06d1a46"
        with self.assertRaises(SystemExit):
            main(["--recover-timeout-request", request_id])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy2(DEFAULT_LIVE_ROOT / "publication_c1_run_manifest.json", root / "publication_c1_run_manifest.json")
            source = DEFAULT_LIVE_ROOT / "requests" / request_id / "attempt-01"; target = root / "requests" / request_id / "attempt-01"; target.parent.mkdir(parents=True); shutil.copytree(source, target)
            lifecycle = json.loads((target / "lifecycle.json").read_text()); lifecycle["requestInputSha256"] = "drift"; (target / "lifecycle.json").write_text(json.dumps(lifecycle))
            with self.assertRaisesRegex(ValueError, "drift"):
                recover_timeout_request(request_id, root, provider_call=lambda _body, _budget: self.fail("must not dispatch"))


if __name__ == "__main__":
    unittest.main()
