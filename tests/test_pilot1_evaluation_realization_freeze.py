"""Focused read-only tests for the corrected Pilot 1 realization freeze."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.extraction.llm.publications import pilot1_evaluation_realization_freeze as freeze


class Pilot1EvaluationRealizationFreezeTests(unittest.TestCase):
    """Audit only the authentic durable execution artifacts."""

    @classmethod
    def setUpClass(cls) -> None:
        """Derive the read-only audit once from the completed execution namespace."""

        cls.binding, cls.predictions, cls.lifecycles, cls.indexes = freeze.derive_realization()

    def test_frozen_execution_binding_and_subset_identities_are_exact(self) -> None:
        """The audit is anchored to the accepted binding and exact 11-request subset."""

        self.assertEqual(self.binding["artifactSha256"], freeze.EXPECTED_BINDING_SHA256)
        self.assertEqual(self.binding["executionSubset"]["artifactSha256"], freeze.EXPECTED_SUBSET_SHA256)
        self.assertEqual(len(self.indexes), 11)

    def test_all_requests_are_terminal_processable_and_accepted(self) -> None:
        """Every authentic request has one selected processable provider attempt."""

        for row in self.indexes:
            self.assertEqual(row["providerAttemptCount"], 1)
            self.assertEqual(row["selectedAttemptNumber"], 1)
            self.assertEqual(row["selectionDisposition"], "first_processable_response_selected")
            self.assertEqual(row["parserStatus"], "parsed")
            self.assertEqual(row["productionAcceptanceStatus"], "production_accepted")
            self.assertEqual(row["terminalProcessingFailureCount"], 0)

    def test_prediction_projection_preserves_execution_cohort_and_sidecar(self) -> None:
        """Predictions retain N=5/N=6 membership without model-output regeneration."""

        self.assertEqual([row["executionCohort"] for row in self.predictions].count("human_core_n5"), 5)
        self.assertEqual([row["executionCohort"] for row in self.predictions].count("step5_n6"), 6)
        self.assertTrue(all(row["unresolvedIdentitySidecar"]["records"] == [] for row in self.predictions))

    def test_materialization_is_read_only_and_tracks_all_four_outputs(self) -> None:
        """Freeze outputs are deterministic and leave the durable source inventory unchanged."""

        before = freeze._source_inventory(freeze.SOURCE_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            with patch("socket.socket.connect", side_effect=AssertionError("no network")):
                outputs = freeze.materialize(output_root=Path(directory))
            self.assertEqual(set(outputs), {"freeze", "predictions", "lifecycle", "index"})
            artifact = json.loads(outputs["freeze"].read_text())
            self.assertEqual(artifact["canonicalCounts"]["totalAcceptedNodes"], 276)
            self.assertEqual(artifact["canonicalCounts"]["totalAcceptedEdges"], 135)
            self.assertEqual(artifact["providerModelCallsDuringFreeze"], 0)
        self.assertEqual(freeze._source_inventory(freeze.SOURCE_ROOT), before)

    def test_missing_selected_raw_provenance_fails_closed(self) -> None:
        """A partial durable request cannot be frozen or silently regenerated."""

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "execution"
            shutil.copytree(freeze.SOURCE_ROOT, source)
            binding = json.loads((source / freeze.BINDING_NAME).read_text())
            raw = source / "requests" / binding["requests"][0]["requestID"] / "attempt-01" / "raw_model_output.json"
            raw.unlink()
            with self.assertRaisesRegex(freeze.Pilot1EvaluationRealizationFreezeError, "SELECTED_ATTEMPT_PROVENANCE_ABSENT"):
                freeze.derive_realization(source)


if __name__ == "__main__":
    unittest.main()
