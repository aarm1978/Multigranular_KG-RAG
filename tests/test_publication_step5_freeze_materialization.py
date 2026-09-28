"""Focused deterministic checks for Step 5 freeze-time artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.extraction.llm.publications.step5_freeze_materialization import (
    MODEL_CONTEXT_BUDGET_TOKENS,
    _optimized_selection,
    materialize,
)


class Step5FreezeMaterializationTests(unittest.TestCase):
    """Verify no-network artifact materialization and approved C1 input bounds."""

    def test_selects_the_unique_frozen_minimax_optimum(self) -> None:
        """Selection is derived from governed inputs, not a fixed accepted tuple."""

        selected, proof = _optimized_selection()
        self.assertEqual(selected, (
            "pub:18:sec:0002:unit:0001", "pub:276:sec:0019:unit:0001",
            "pub:37:sec:0014:unit:0001", "pub:46:sec:0006:unit:0001",
            "pub:54:sec:0019:unit:0001", "pub:87:sec:0007:unit:0001",
        ))
        self.assertEqual(proof, {
            "eligibleUniverseSourceUnitCount": 210,
            "eligibleCombinationCount": 7045,
            "minimumMaximumPerUnitRoutedScoredTargetExposure": 15,
            "minimumTotalRoutedScoredTargetExposure": 57,
            "optimumCombinationCount": 1,
        })

    def test_materializes_six_bounded_envelopes_with_complete_section_context(self) -> None:
        """Every corrected C1 envelope is bounded and includes eligible section context."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = materialize(root)
            envelopes = json.loads(paths["envelopes"].read_text(encoding="utf-8"))
            second = json.loads(paths["second_review"].read_text(encoding="utf-8"))
            adapter = json.loads(paths["scierc_adapter"].read_text(encoding="utf-8"))
        self.assertEqual([row["primarySourceUnitID"] for row in envelopes["envelopes"]], [
            "pub:18:sec:0002:unit:0001", "pub:276:sec:0019:unit:0001",
            "pub:37:sec:0014:unit:0001", "pub:46:sec:0006:unit:0001",
            "pub:54:sec:0019:unit:0001", "pub:87:sec:0007:unit:0001",
        ])
        row_46 = next(row for row in envelopes["envelopes"] if row["primarySourceUnitID"] == "pub:46:sec:0006:unit:0001")
        self.assertEqual(row_46["contextSourceUnitIDs"], ["pub:46:sec:0006:unit:0002"])
        self.assertEqual(row_46["contextSelectionReason"], "complete_section_all_eligible_units")
        self.assertTrue(all(row["includedCompleteSection"] for row in envelopes["envelopes"]))
        self.assertTrue(all(row["estimatedInputTokens"] <= MODEL_CONTEXT_BUDGET_TOKENS for row in envelopes["envelopes"]))
        self.assertEqual(second["selectedPrimarySourceUnitIDs"], ["pub:46:sec:0006:unit:0001", "pub:276:sec:0019:unit:0001"])
        self.assertTrue(adapter["schemaIndependentConfigurationMatchesC1"])
