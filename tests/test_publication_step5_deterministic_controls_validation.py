"""Focused tests for the Section 17.7 fixture-only validation harness."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.extraction.llm.publications.step5_deterministic_controls_validation import (
    DeterministicControlsError,
    OUTPUT_PATH,
    build_validation_artifact,
    c1_provenance_key,
    materialize,
    select_representative,
)


class Step5DeterministicControlsValidationTests(unittest.TestCase):
    """Protect the prospective Section 17.7 control evidence."""

    def test_all_section_17_7_checks_pass_and_are_no_execution(self) -> None:
        """The artifact records each required control with explicit PASS evidence."""

        artifact = build_validation_artifact()
        self.assertEqual(artifact["providerModelCalls"], 0)
        self.assertEqual(len(artifact["checks"]), 15)
        self.assertTrue(all(row["status"] == "PASS" for row in artifact["checks"]))
        self.assertTrue(artifact["artifactSha256"])

    def test_representative_provenance_fails_closed(self) -> None:
        """Missing and duplicate fully qualified provenance cannot choose a member."""

        provenance = {"runID": "run", "requestID": "request", "outputID": "output", "primarySourceUnitID": "unit", "recordType": "candidate_node", "candidateID": "candidate"}
        self.assertEqual(c1_provenance_key(provenance), "c1|run|request|output|unit|candidate_node|candidate")
        with self.assertRaisesRegex(DeterministicControlsError, "MISSING_PROVENANCE_COMPONENT"):
            c1_provenance_key({**provenance, "requestID": ""})
        with self.assertRaisesRegex(DeterministicControlsError, "NON_UNIQUE_PROVENANCE_KEY"):
            select_representative([provenance, dict(provenance)])

    def test_materialization_is_idempotent(self) -> None:
        """A temporary artifact path reproduces byte-identical deterministic evidence."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "controls.json"
            first = materialize(path)
            second = materialize(path)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertTrue(json.loads(first.read_text(encoding="utf-8"))["artifactSha256"])

    def test_tracked_artifact_matches_the_deterministic_builder(self) -> None:
        """The checked-in freeze record is exactly the current fixture-only result."""

        self.assertEqual(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")), build_validation_artifact())


if __name__ == "__main__":
    unittest.main()
