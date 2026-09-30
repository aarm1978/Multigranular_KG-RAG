"""Focused deterministic tests for the prospective Step 5 v0.1.2 envelope correction."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.extraction.llm.publications import step5_v012_routing_correction as correction


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ADDITIONS = {
    "pub:18:sec:0002:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-R-C-P34-HASCOMPONENT"},
    "pub:276:sec:0019:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-R-C-P34-HASCOMPONENT"},
    "pub:37:sec:0014:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-R-C-P34-HASCOMPONENT"},
    "pub:46:sec:0006:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-R-C-P34-HASCOMPONENT"},
    "pub:54:sec:0019:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-R-C-P34-HASCOMPONENT"},
    "pub:87:sec:0007:unit:0001": {"PUB-N-A-AG02-ORGANIZATION-PROSE", "PUB-N-A-DOM03E-AGENTBASEDMODEL", "PUB-R-C-P34-HASCOMPONENT"},
}


class Step5V012RoutingCorrectionTests(unittest.TestCase):
    """Protect the unchanged N=6 selection and exact audited envelope delta."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the correction in memory without provider execution."""

        cls.envelopes, cls.binding = correction.build_envelopes()
        cls.base = json.loads((ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json").read_text(encoding="utf-8"))

    def test_selection_ids_are_the_unchanged_frozen_six(self) -> None:
        """The frozen v0.1.1 minimax result remains exactly intact."""

        expected = [row["primarySourceUnitID"] for row in self.base["envelopes"]]
        self.assertEqual(self.envelopes["selectionIDsUnchanged"], expected)
        self.assertEqual(self.binding["selectionIDsUnchanged"], expected)
        self.assertEqual(self.envelopes["selectionArtifactSha256"], "653a4e01548759dd49594676e8fa8ee3383b8a5244544b615243b787999579f8")

    def test_target_deltas_are_only_the_accepted_additions_with_no_removals(self) -> None:
        """Every corrected envelope adds exactly the audited targets and removes none."""

        base_by_id = {row["primarySourceUnitID"]: row for row in self.base["envelopes"]}
        corrected_by_id = {row["primarySourceUnitID"]: row for row in self.envelopes["envelopes"]}
        self.assertEqual(set(corrected_by_id), set(EXPECTED_ADDITIONS))
        for source_unit_id, expected_added in EXPECTED_ADDITIONS.items():
            old = set(base_by_id[source_unit_id]["routedExtractAndEvaluateTargetIDs"])
            new = set(corrected_by_id[source_unit_id]["routedExtractAndEvaluateTargetIDs"])
            self.assertEqual(new - old, expected_added)
            self.assertFalse(old - new)
            self.assertEqual(self.envelopes["envelopeTargetDeltas"][source_unit_id]["addedTargetIDs"], sorted(expected_added))
            self.assertEqual(self.envelopes["envelopeTargetDeltas"][source_unit_id]["removedTargetIDs"], [])

    def test_configuration_and_context_policy_are_preserved(self) -> None:
        """Only corrected routing targets and their mechanical request hashes differ."""

        for field in ("commonAuthorityBindings", "productionConfiguration", "contextBudgetAuthority"):
            self.assertEqual(self.envelopes[field], self.base[field])
        self.assertEqual(self.envelopes["providerModelCalls"], 0)
        self.assertFalse(self.binding["unchangedMethodology"]["productionAcceptanceModified"])
        self.assertFalse(self.binding["unchangedMethodology"]["sciercSemanticsModified"])

    def test_scierc_binding_changes_only_for_the_corrected_envelope_hash(self) -> None:
        """The new adapter binds the new envelope without changing benchmark semantics."""

        adapter = correction.build_scierc_adapter(self.envelopes)
        self.assertEqual(adapter["c1EnvelopeArtifactSha256"], self.envelopes["artifactSha256"])
        self.assertTrue(adapter["correctionProvenance"]["semanticsAndConfigurationUnchanged"])
        self.assertEqual(adapter["baseLLM"], self.base["productionConfiguration"]["model"])

    def test_materialization_is_idempotent_and_does_not_write_v011(self) -> None:
        """The correction produces only new v0.1.2 artifact names."""

        frozen_before = (ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            outputs = correction.materialize(Path(directory))
            self.assertEqual(set(outputs), {"envelopes", "binding", "scierc_adapter"})
            self.assertTrue(all(path.name.endswith("v0.1.2.json") for path in outputs.values()))
            correction.materialize(Path(directory))
        self.assertEqual((ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json").read_bytes(), frozen_before)


if __name__ == "__main__":
    unittest.main()
