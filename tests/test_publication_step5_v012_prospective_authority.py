"""Focused consistency checks for the prospective Step 5 v0.1.2 draft."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "docs/publication_step5_evaluation_authority_v0.1.2.md"
AMENDMENT = ROOT / "docs/study2_evaluation_protocol_amendment_v0.2.md"
V011 = ROOT / "docs/publication_step5_evaluation_authority_v0.1.1.md"
ENVELOPES = ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.2.json"
SECONDARY = ROOT / "data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_subset_freeze_v0.1.1.json"
SCIERC = ROOT / "data/curation/papers/m2/step5_freeze/scierc_external_anchor_adapter_freeze_v0.1.2.json"
REALIZATION = ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json"
PREDICTIONS = ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_canonical_predictions_v1.0.0.jsonl"
STEP7C = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_n5_corrected_evaluation_step7c_closure_v1.0.0.json"

N6_IDS = [
    "pub:18:sec:0002:unit:0001",
    "pub:276:sec:0019:unit:0001",
    "pub:37:sec:0014:unit:0001",
    "pub:46:sec:0006:unit:0001",
    "pub:54:sec:0019:unit:0001",
    "pub:87:sec:0007:unit:0001",
]


def sha256(path: Path) -> str:
    """Return the SHA-256 of one frozen tracked file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublicationStep5V012ProspectiveAuthorityTests(unittest.TestCase):
    """Ensure the draft binds frozen inputs and omits a live completeness procedure."""

    def test_draft_status_and_frozen_v011_preservation(self) -> None:
        """The new authority is a draft and leaves v0.1.1's known bytes intact."""

        self.assertIn("**Status:** **DRAFT — NOT FROZEN**", AUTHORITY.read_text(encoding="utf-8"))
        self.assertEqual(sha256(V011), "f946b6d9a6cc0928bd575f6eefffaab68d70d905fff9deaae2db1cd984fa83c3")

    def test_corrected_n6_candidate_source_and_frozen_bindings(self) -> None:
        """Only the corrected realization's six step5_n6 records are candidates."""

        envelopes = json.loads(ENVELOPES.read_text(encoding="utf-8"))
        secondary = json.loads(SECONDARY.read_text(encoding="utf-8"))
        realization = json.loads(REALIZATION.read_text(encoding="utf-8"))
        scierc = json.loads(SCIERC.read_text(encoding="utf-8"))
        step7c = json.loads(STEP7C.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in PREDICTIONS.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(envelopes["artifactSha256"], "ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce")
        self.assertEqual(envelopes["selectionIDsUnchanged"], N6_IDS)
        self.assertEqual(secondary["selectedPrimarySourceUnitIDs"], [N6_IDS[3], N6_IDS[1]])
        self.assertEqual(realization["artifactSha256"], "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842")
        self.assertEqual(scierc["c1EnvelopeArtifactSha256"], envelopes["artifactSha256"])
        self.assertEqual(step7c["status"], "FROZEN_CLOSED")
        self.assertEqual(sha256(PREDICTIONS), realization["trackedArtifacts"]["predictions"]["sha256"])
        step5_rows = [row for row in rows if row["executionCohort"] == "step5_n6"]
        self.assertEqual(len(step5_rows), 6)
        self.assertEqual(sorted(row["primarySourceUnitID"] for row in step5_rows), sorted(N6_IDS))

    def test_no_live_completeness_audit_requirement_is_carried_forward(self) -> None:
        """The prospective documents retain no audit ordering, matching, or statistics."""

        authority = AUTHORITY.read_text(encoding="utf-8").lower()
        amendment = AMENDMENT.read_text(encoding="utf-8").lower()
        for phrase in ["audit-to-pool matching", "saturation", "missed-reference proportion", "completeness statistic"]:
            self.assertNotIn("must " + phrase, authority)
            self.assertNotIn("must " + phrase, amendment)
        self.assertIn("excluded from recall, f1, completeness, saturation", authority)
        self.assertIn("no standalone exhaustive/model-blind completeness procedure", amendment)


if __name__ == "__main__":
    unittest.main()
