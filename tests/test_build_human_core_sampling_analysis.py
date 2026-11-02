"""Focused tests for the prospective, model-blind Human Core sampling analysis."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.annotation.publication_pilot1 import build_human_core_sampling_analysis as analysis


ROOT = Path(__file__).resolve().parents[1]


class HumanCoreSamplingAnalysisTests(unittest.TestCase):
    """Protect the bounded metadata-only sampling comparison."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build one deterministic in-memory analysis for focused assertions."""

        cls.result = analysis.build_analysis(ROOT)

    def test_reserved_provenance_is_complete_and_auditable(self) -> None:
        """Calibration subsumes CORE_FEAS and DEV diagnostics cannot leak into the pool."""

        provenance = self.result["reservedRoleProvenance"]
        exclusions = self.result["exclusionLedger"]["excludedByReason"]
        self.assertIn("CORE_FEAS subset Calibration", provenance["coreFeasibilitySubsumption"])
        self.assertEqual(provenance["calibrationManifestUnitCount"], 16)
        self.assertEqual(provenance["developmentManifestUnitCount"], 10)
        self.assertEqual(provenance["developmentUnitsPresentInFixedPopulation"], [])
        self.assertEqual(len(exclusions["calibration_manifest"]), 16)

    def test_analysis_is_metadata_only_and_has_five_strata(self) -> None:
        """The declared whitelist and eligible universe preserve the model-blind boundary."""

        scope = self.result["scope"]
        self.assertIn("canonical_source_text", scope["doesNotUse"])
        self.assertIn("section_titles", scope["doesNotUse"])
        self.assertIn("LLM_or_provider_outputs", scope["doesNotUse"])
        self.assertEqual(self.result["exclusionLedger"]["eligibleUnitCount"], 210)
        self.assertEqual(len(self.result["eligibleUniverse"]["samplingStrata"]), 5)

    def test_size_comparisons_are_feasible_deterministic_and_structural(self) -> None:
        """Each requested size has a stable best candidate and separate indicators."""

        comparisons = self.result["comparisons"]
        self.assertEqual([item["sampleSize"] for item in comparisons], [4, 5, 6])
        for comparison in comparisons:
            best = comparison["deterministicBestCandidateSet"]
            self.assertTrue(comparison["feasible"])
            self.assertEqual(len(best["sourceUnitIDs"]), comparison["sampleSize"])
            self.assertEqual(best["metrics"]["samplingStratumCount"], 5)
            self.assertGreater(comparison["nondominatedGreedyCandidateCount"], 0)
            self.assertTrue(comparison["nondominatedMetricVectors"])
            self.assertIn("perUnitRoutedTargetCounts", best["structuralBurdenIndicators"])
            self.assertNotIn("burdenScore", best["structuralBurdenIndicators"])
        self.assertEqual(self.result, analysis.build_analysis(ROOT))


if __name__ == "__main__":
    unittest.main()
