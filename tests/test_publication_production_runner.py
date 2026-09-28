"""Focused offline readiness checks for the Step 6A Production runner."""

import json
import unittest

from src.extraction.llm.publications.production_runner import (
    MAX_OUTPUT_TOKENS, _prepared_request, derive_production_preflight, execute_with_provider_fixture,
)
from src.extraction.llm.publications.step5_freeze_materialization import _inputs


class ProductionRunnerTests(unittest.TestCase):
    def test_population_and_frozen_n6_reproduction(self) -> None:
        preflight = derive_production_preflight()
        self.assertEqual(preflight["populationAuthority"]["count"], 210)
        self.assertEqual(len(preflight["humanCoreN5PrimarySourceUnitIDs"]), 5)
        self.assertEqual(len(preflight["complementaryN6PrimarySourceUnitIDs"]), 6)
        self.assertTrue(all(row["matched"] for row in preflight["n6FrozenEnvelopeReproduction"]))
        p46 = next(row for row in preflight["n6FrozenEnvelopeReproduction"] if row["primarySourceUnitID"] == "pub:46:sec:0006:unit:0001")
        self.assertEqual(p46["publication46SameSectionContext"], ["pub:46:sec:0006:unit:0002"])
        self.assertEqual(preflight["productionConfiguration"]["maxOutputTokens"], 32768)

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


if __name__ == "__main__":
    unittest.main()
