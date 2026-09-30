"""Focused offline fixture tests for the frozen Pilot 1 execution runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications import pilot1_evaluation_execution_runner as runner


EMPTY_PAYLOAD = {
    "candidateNodes": [], "candidateEdges": [], "evidenceSpans": [],
    "abstentions": [], "deferredRecords": [],
}


class Pilot1EvaluationExecutionRunnerTests(unittest.TestCase):
    """Exercise only reconstructed frozen-scope requests with offline fixtures."""

    def test_n5_and_n6_requests_reconstruct_with_exact_frozen_identities(self) -> None:
        """Both execution cohorts use their correct builders and parent-manifest hashes."""

        subset, _manifest = runner.load_frozen_execution_scope()
        n5 = next(row for row in subset["requests"] if row["executionCohort"] == "human_core_n5")
        n6 = next(row for row in subset["requests"] if row["executionCohort"] == "step5_n6")
        for record in (n5, n6):
            prepared = runner.prepare_verified_request(record)
            self.assertEqual(prepared["request"]["requestID"], record["requestID"])
            self.assertEqual(prepared["request"]["eligibleOperationalTargetIDs"], record["productionTargetIDs"])
            self.assertEqual(prepared["request"]["contextSourceUnitIDs"], record["contextSourceUnitIDs"])

    def test_all_eleven_process_with_fixture_and_preserve_durable_provenance(self) -> None:
        """The existing canonical pipeline and acceptance controller process both cohorts."""

        calls: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = runner.execute_subset_with_provider_fixture(
                root,
                lambda body, _budget: calls.append(str(body["model"])) or json.dumps(EMPTY_PAYLOAD).encode("utf-8"),
            )
            self.assertEqual(result["completedRequestCount"], 11)
            self.assertEqual(len(calls), 11)
            binding = json.loads((root / runner.EXECUTION_BINDING_NAME).read_text())
            for record in binding["requests"]:
                request_root = root / "requests" / record["requestID"]
                self.assertTrue((request_root / "attempt_selection.json").is_file())
                for name in ("provider_request.json", "raw_model_output.json", "parser_result.json", "validation_results.json", "usable_pipeline_output.json", "lifecycle.json"):
                    self.assertTrue((request_root / "attempt-01" / name).is_file(), name)

    def test_reconstructed_identity_drift_fails_before_provider_dispatch(self) -> None:
        """A tampered subset record or rebuilt request cannot reach a live dispatch."""

        subset, _manifest = runner.load_frozen_execution_scope()
        bad = dict(subset["requests"][0])
        bad["requestInputSha256"] = "0" * 64
        with self.assertRaisesRegex(runner.Pilot1EvaluationExecutionError, "NOT_FROZEN_SUBSET_MEMBER"):
            runner.prepare_verified_request(bad)
        n5 = next(row for row in subset["requests"] if row["executionCohort"] == "human_core_n5")
        original = runner._prepared_request

        def body_drift(*args, **kwargs):
            prepared = deepcopy(original(*args, **kwargs))
            prepared["body"]["model"] = "unexpected-model"
            return prepared

        with patch.object(runner, "_prepared_request", side_effect=body_drift):
            with self.assertRaisesRegex(runner.Pilot1EvaluationExecutionError, "RECONSTRUCTED_REQUEST_IDENTITY_DRIFT"):
                runner.prepare_verified_request(n5)

    def test_interrupted_nonterminal_state_blocks_redispatch(self) -> None:
        """Resume skips only terminal selections and never duplicates an uncertain call."""

        subset, _manifest = runner.load_frozen_execution_scope()
        first = subset["requests"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner.materialize_execution_binding(root)
            interrupted = root / "requests" / first["requestID"] / "attempt-01"
            interrupted.mkdir(parents=True)
            calls: list[bool] = []
            with self.assertRaisesRegex(runner.Pilot1EvaluationExecutionError, "AMBIGUOUS_INTERRUPTED_REQUEST_STATE"):
                runner.execute_subset_with_provider_fixture(root, lambda _body, _budget: calls.append(True) or b"{}")
            self.assertEqual(calls, [])

    def test_cli_never_loads_credentials_without_explicit_opt_in(self) -> None:
        """The default CLI creates only a no-call binding artifact."""

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(runner, "load_openai_api_key", side_effect=self.fail):
                self.assertEqual(runner.main(["--root", directory]), 0)


if __name__ == "__main__":
    unittest.main()
