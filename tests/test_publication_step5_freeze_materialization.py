"""Focused deterministic checks for Step 5 freeze-time artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.extraction.llm.publications.step5_freeze_materialization import (
    MODEL_CONTEXT_BUDGET_TOKENS,
    SELECTION_IDS,
    materialize,
)


class Step5FreezeMaterializationTests(unittest.TestCase):
    """Verify no-network artifact materialization and approved C1 input bounds."""

    def test_materializes_six_bounded_envelopes_idempotently(self) -> None:
        """Every frozen C1 envelope is singleton-section and stays below the budget."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = materialize(root)
            second = materialize(root)
            self.assertEqual(first, second)
            envelopes = json.loads(first["envelopes"].read_text(encoding="utf-8"))
        self.assertEqual([row["primarySourceUnitID"] for row in envelopes["envelopes"]], list(SELECTION_IDS))
        self.assertTrue(all(row["contextSourceUnitIDs"] == [] for row in envelopes["envelopes"]))
        self.assertTrue(all(row["includedCompleteSection"] for row in envelopes["envelopes"]))
        self.assertTrue(all(row["estimatedInputTokens"] <= MODEL_CONTEXT_BUDGET_TOKENS for row in envelopes["envelopes"]))

    def test_second_review_and_scierc_adapter_bindings_are_exact(self) -> None:
        """The approved neutral subset and SciERC/C1 configuration stay linked."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = materialize(Path(temporary_directory))
            second = json.loads(paths["second_review"].read_text(encoding="utf-8"))
            source = json.loads(paths["scierc_source"].read_text(encoding="utf-8"))
            adapter = json.loads(paths["scierc_adapter"].read_text(encoding="utf-8"))
        self.assertEqual(second["selectedPrimarySourceUnitIDs"], ["pub:46:sec:0030:unit:0001", "pub:37:sec:0016:unit:0001"])
        self.assertEqual(source["splits"]["test"]["documentCount"], 100)
        self.assertTrue(adapter["schemaIndependentConfigurationMatchesC1"])
