"""Focused offline tests for the corrected Publication production manifest."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from src.extraction.llm.publications import corrected_production_preflight as corrected


ROOT = Path(__file__).resolve().parents[1]
N6_IDS = {
    "pub:18:sec:0002:unit:0001", "pub:276:sec:0019:unit:0001", "pub:37:sec:0014:unit:0001",
    "pub:46:sec:0006:unit:0001", "pub:54:sec:0019:unit:0001", "pub:87:sec:0007:unit:0001",
}


class CorrectedProductionPreflightTests(unittest.TestCase):
    """Verify complete offline request construction and corrected N=6 binding."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build every corrected request once; this never dispatches a provider call."""

        cls.preflight = corrected.derive_preflight()
        cls.manifest = corrected.build_manifest(cls.preflight)

    def test_every_derived_population_request_builds_with_complete_identities(self) -> None:
        """All derived requests have unique IDs, hashes, targets, context, and schemas."""

        requests = self.preflight["requests"]
        self.assertEqual(self.preflight["productionPopulation"]["count"], len(requests))
        self.assertTrue(requests)
        self.assertEqual(len({row["requestID"] for row in requests}), len(requests))
        for row in requests:
            self.assertTrue(row["productionTargetIDs"])
            for field in ("requestInputSha256", "modelAuthorableSchemaSha256", "providerRequestBodySha256"):
                self.assertRegex(row[field], r"^[0-9a-f]{64}$")

    def test_all_six_n6_requests_reproduce_v012_envelopes_exactly(self) -> None:
        """The corrected realization never falls back to the historical v0.1.1 envelopes."""

        reproduction = self.preflight["n6EnvelopeReproduction"]
        self.assertEqual({row["primarySourceUnitID"] for row in reproduction}, N6_IDS)
        self.assertTrue(all(row["matched"] for row in reproduction))
        self.assertEqual({row["envelopeArtifactSha256"] for row in reproduction}, {"ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce"})
        self.assertEqual(self.preflight["n6EnvelopeAuthority"]["artifactVersion"], "0.1.2")
        self.assertFalse(self.preflight["historicalC1Preserved"]["v011EnvelopesUsed"])

    def test_historical_c1_authorities_remain_unchanged_and_no_provider_call_occurs(self) -> None:
        """The prospective preflight is isolated from frozen historical C1 state."""

        historical_manifest = ROOT / "var/publication_c1_production/publication_c1_run_manifest.json"
        self.assertEqual(hashlib.sha256(historical_manifest.read_bytes()).hexdigest(), "4c7cbc372f928b65c44232e7e77c88c1d01f5d9320389ef3de744d6f3109e990")
        self.assertEqual(self.preflight["providerModelCalls"], 0)
        self.assertEqual(self.manifest["providerModelCalls"], 0)
        self.assertFalse(self.manifest["c1Execution"])
        self.assertFalse(self.preflight["historicalC1Preserved"]["historicalManifestModified"])
        self.assertFalse(self.preflight["historicalC1Preserved"]["historicalOutputsModified"])

    def test_manifest_binds_the_exact_preflight_request_set(self) -> None:
        """The immutable manifest is a complete identity-preserving preflight projection."""

        self.assertEqual(self.manifest["populationCount"], self.preflight["productionPopulation"]["count"])
        self.assertEqual(self.manifest["requests"], self.preflight["requests"])
        self.assertEqual(self.manifest["preflightArtifactSha256"], self.preflight["artifactSha256"])
        self.assertEqual(self.manifest["n6EnvelopeAuthority"], self.preflight["n6EnvelopeAuthority"])


if __name__ == "__main__":
    unittest.main()
