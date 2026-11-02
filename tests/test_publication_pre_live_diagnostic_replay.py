"""Non-regression tests for the isolated no-call pre-live replay."""

import json
from pathlib import Path
import tempfile
import unittest

from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, load_yaml_object
from src.extraction.llm.publications.run_publication_pre_live_diagnostic_replay import (
    DEFAULT_OUTPUT_DIR,
    run_replay,
)


class PublicationPreLiveDiagnosticReplayTests(unittest.TestCase):
    """Protect labels, measured outcomes, and target-universe boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the committed deterministic replay summary once."""

        cls.summary = json.loads(
            (DEFAULT_OUTPUT_DIR / "publication_pre_live_diagnostic_replay_summary.json").read_text(
                encoding="utf-8"
            )
        )

    def test_replay_is_zero_call_counterfactual_not_gold(self) -> None:
        """Every artifact-level status preserves the no-call diagnostic boundary."""

        self.assertEqual(self.summary["artifactClass"], "DEVELOPMENT_DIAGNOSTIC_REPLAY")
        self.assertEqual(self.summary["transportMethod"], "COUNTERFACTUAL_TRANSPORT_EMULATION")
        self.assertEqual(self.summary["authenticity"], "NOT_AUTHENTIC_NEW_MODEL_OUTPUT")
        self.assertEqual(self.summary["goldStatus"], "NOT_GOLD")
        self.assertEqual(self.summary["evaluationStatus"], "NOT_FORMAL_EVALUATION")
        self.assertEqual(self.summary["providerCalls"], 0)
        self.assertFalse(self.summary["modelCallMade"])
        self.assertEqual(self.summary["acceptanceBasis"], "DEVELOPMENT_VALIDATOR_USABLE_PROXY")
        self.assertEqual(self.summary["acceptanceStatus"], "NOT_FORMAL_ACCEPTANCE")

    def test_measured_validator_outcomes_and_dev05_residual(self) -> None:
        """The replay reports measured 252/254 and preserves genuine DEV-05 defects."""

        units = {row["developmentID"]: row for row in self.summary["units"]}
        self.assertEqual(sum(row["totalCandidates"] for row in units.values()), 254)
        self.assertEqual(sum(row["validatedCandidates"] for row in units.values()), 252)
        self.assertEqual(sum(row["rejectedCandidates"] for row in units.values()), 2)
        self.assertEqual(
            units["DEV-05"]["validationFindingCodeCounts"],
            {
                "EVIDENCE_NOT_LITERAL": 1,
                "NODE_EVIDENCE_INVALID": 2,
                "OFFSET_MISMATCH_IN_DOCUMENT": 1,
                "OFFSET_MISMATCH_IN_UNIT": 1,
            },
        )
        self.assertEqual(
            units["DEV-06"]["validationFindingCodeCounts"],
            {"UNREFERENCED_EVIDENCE_SPAN": 1},
        )
        self.assertEqual(
            units["DEV-09"]["validationFindingCodeCounts"],
            {"SEMANTIC_NORMALIZATION_PENDING_REVIEW": 1},
        )

    def test_only_title_is_emulated_and_current_authority_is_used(self) -> None:
        """All units bind current ontology bytes and list only title JSON pointers."""

        for row in self.summary["units"]:
            self.assertTrue(row["providerFacingSchemaAccepted"])
            self.assertTrue(row["allOtherAuthenticSemanticPayloadFieldsByteEquivalent"])
            self.assertFalse(row["postGenerationRepairApplied"])
            self.assertEqual(row["currentOntologyAuthority"]["version"], "0.1.4")
            self.assertEqual(
                row["currentOntologyAuthority"]["validatedOwlSha256"],
                "7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635",
            )
            self.assertTrue(row["changedJsonPointers"])
            self.assertTrue(all(pointer.endswith("/sectionTitle") for pointer in row["changedJsonPointers"]))

    def test_replay_is_deterministic_and_preserves_c1b(self) -> None:
        """A fresh isolated run is canonical-byte identical to the committed summary."""

        with tempfile.TemporaryDirectory() as directory:
            replay = run_replay(Path(directory))
        self.assertEqual(canonical_json(replay), canonical_json(self.summary))
        self.assertTrue(replay["authenticC1bTreeByteIdentical"])

    def test_target_universe_and_d26_non_authorability_are_unchanged(self) -> None:
        """The profile retains 46/40/4/2 node routing and no generic relation target."""

        profile = load_yaml_object(
            PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
        )
        candidate_nodes = [row for row in profile["node_targets"] if row.get("allowed_actions")]
        direct = [row for row in candidate_nodes if row.get("emission_mode") == "llm_candidate"]
        deterministic = [row for row in candidate_nodes if row.get("emission_mode") == "deterministic_context"]
        deferred = [row for row in candidate_nodes if row.get("emission_mode") == "resolver_mediated_candidate"]
        self.assertEqual((len(candidate_nodes), len(direct), len(deterministic), len(deferred)), (46, 40, 4, 2))
        relation_names = {
            formal["name"]
            for row in profile["relation_targets"]
            for formal in row.get("formal_relations", [])
            if row.get("allowed_actions")
        }
        self.assertNotIn("mentions", relation_names)


if __name__ == "__main__":
    unittest.main()
