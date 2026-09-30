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
LIFECYCLE = ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_lifecycle_ledger_v1.0.0.jsonl"
RESULT_INDEX = ROOT / "data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_result_index_v1.0.0.jsonl"
STEP7C = ROOT / "data/curation/papers/m2/human_core_gold/publication_human_core_n5_corrected_evaluation_step7c_closure_v1.0.0.json"
DECISIONS = ROOT / "docs/evaluation_decisions.md"
FREEZE_RECORD = ROOT / "data/curation/papers/m2/publication_step5_evaluation_authority_freeze_v0.1.2.json"

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

    def test_frozen_status_and_frozen_v011_preservation(self) -> None:
        """The approved authority is closed and leaves v0.1.1's known bytes intact."""

        self.assertIn("**Status:** **FROZEN/CLOSED**", AUTHORITY.read_text(encoding="utf-8"))
        self.assertIn("**Status:** **FROZEN/CLOSED**", AMENDMENT.read_text(encoding="utf-8"))
        self.assertEqual(sha256(V011), "f946b6d9a6cc0928bd575f6eefffaab68d70d905fff9deaae2db1cd984fa83c3")

    def test_freeze_record_binds_finalized_authorities_and_execution_boundary(self) -> None:
        """The closure record fails closed on authority, binding, or execution drift."""

        record = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
        bindings = record["frozenBindings"]
        self.assertEqual(record["status"], "frozen_closed")
        self.assertEqual(record["researcherApprovedCheckpoint"], "0f4b612")
        self.assertEqual(record["authority"]["sha256"], sha256(AUTHORITY))
        self.assertEqual(record["amendment"]["sha256"], sha256(AMENDMENT))
        self.assertEqual(bindings["n6Selection"]["artifactSha256"], "653a4e01548759dd49594676e8fa8ee3383b8a5244544b615243b787999579f8")
        self.assertEqual(bindings["correctedN6Envelopes"]["artifactSha256"], "ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce")
        self.assertEqual(bindings["correctedRouting"]["routingSha256"], "7a43f371ae9d70573082319ae26e2d2294ff58b1e801da23d662e27a4c01ec62")
        realization = bindings["selectedProcessableStep5N6Realization"]
        self.assertEqual(realization["executionCohort"], "step5_n6")
        self.assertEqual(realization["selectedProcessableAttemptCount"], 6)
        self.assertEqual(realization["realizationArtifactSha256"], "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842")
        self.assertEqual(bindings["secondaryReviewSubset"]["artifactSha256"], "2c9371f1893367f89f667aa9e871c970638d33b93e0d7f3f63dfbbf9d08a87e2")
        self.assertEqual(bindings["scierc"]["adapterArtifactSha256"], "0f68abc78415b0c119ec75340d707dce1a8e0cea0df1e2124d0c5908140c5104")
        self.assertEqual(bindings["step7CClosure"]["status"], "FROZEN_CLOSED")
        tracked_bindings = [
            bindings["n6Selection"],
            bindings["correctedN6Envelopes"],
            bindings["correctedRouting"],
            bindings["secondaryReviewSubset"],
            bindings["step7CClosure"],
        ]
        for binding in tracked_bindings:
            self.assertEqual(sha256(ROOT / binding["path"]), binding["trackedFileSha256"])
        for key in ("lifecycleLedger", "resultIndex", "canonicalAcceptedSemanticProjection"):
            provenance = realization[key]
            self.assertEqual(sha256(ROOT / provenance["path"]), provenance["sha256"])
        scierc = bindings["scierc"]
        self.assertEqual(sha256(ROOT / scierc["adapterPath"]), scierc["adapterTrackedFileSha256"])
        self.assertEqual(sha256(ROOT / scierc["sourcePath"]), scierc["sourceTrackedFileSha256"])
        boundary = record["closureExecutionBoundary"]
        self.assertFalse(boundary["providerModelCallsOccurred"])
        self.assertFalse(boundary["step8Executed"])

    def test_corrected_selected_attempts_and_frozen_bindings(self) -> None:
        """The six selected processable attempts, not only their projection, bind the pool."""

        envelopes = json.loads(ENVELOPES.read_text(encoding="utf-8"))
        secondary = json.loads(SECONDARY.read_text(encoding="utf-8"))
        realization = json.loads(REALIZATION.read_text(encoding="utf-8"))
        scierc = json.loads(SCIERC.read_text(encoding="utf-8"))
        step7c = json.loads(STEP7C.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in PREDICTIONS.read_text(encoding="utf-8").splitlines()]
        lifecycle_rows = [json.loads(line) for line in LIFECYCLE.read_text(encoding="utf-8").splitlines()]
        index_rows = [json.loads(line) for line in RESULT_INDEX.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(envelopes["artifactSha256"], "ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce")
        self.assertEqual(envelopes["selectionIDsUnchanged"], N6_IDS)
        self.assertEqual(secondary["selectedPrimarySourceUnitIDs"], [N6_IDS[3], N6_IDS[1]])
        self.assertEqual(realization["artifactSha256"], "5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842")
        self.assertEqual(scierc["c1EnvelopeArtifactSha256"], envelopes["artifactSha256"])
        self.assertEqual(step7c["status"], "FROZEN_CLOSED")
        self.assertEqual(sha256(PREDICTIONS), realization["trackedArtifacts"]["predictions"]["sha256"])
        step5_rows = [row for row in rows if row["executionCohort"] == "step5_n6"]
        step5_lifecycle = [row for row in lifecycle_rows if row["executionCohort"] == "step5_n6"]
        step5_index = [row for row in index_rows if row["executionCohort"] == "step5_n6"]
        self.assertEqual(len(step5_rows), 6)
        self.assertEqual(sorted(row["primarySourceUnitID"] for row in step5_rows), sorted(N6_IDS))
        self.assertEqual(len(step5_lifecycle), 6)
        self.assertEqual(len(step5_index), 6)
        self.assertEqual({row["selectedAttemptNumber"] for row in step5_lifecycle}, {1})
        self.assertEqual({row["selectionDisposition"] for row in step5_lifecycle}, {"first_processable_response_selected"})
        self.assertTrue(all(row["attempts"][0]["status"] == "processed" for row in step5_lifecycle))
        self.assertEqual({row["attempts"][0]["parseStatus"] for row in step5_lifecycle}, {"parsed"})
        self.assertTrue(all(row["providerResponseSha256"] and row["rawOutputSha256"] for row in step5_index))

    def test_candidate_eligibility_is_not_production_acceptance(self) -> None:
        """The retained v0.1.1 lifecycle boundary governs human-review eligibility."""

        authority = AUTHORITY.read_text(encoding="utf-8")
        self.assertIn("eligibility is evaluated independently of Production Acceptance", authority)
        self.assertIn("`validated`", authority)
        self.assertIn("`normalizationStatus = pending_review`", authority)
        self.assertIn("`needs_review / POSSIBLE_LOCAL_DUPLICATE`", authority)
        self.assertIn("`needs_review / ATOMICITY_VIOLATION`", authority)
        self.assertIn("`rejected`, unresolved deferred content", authority)
        self.assertIn("independently presented `superseded`", authority)
        self.assertIn("No candidate gains eligibility through manual correction", authority)
        self.assertIn("MUST NOT silently narrow the human-review candidate layer", authority)
        self.assertIn("accepted-semantic\nprojection and provenance authority", authority)

    def test_no_live_completeness_audit_requirement_is_carried_forward(self) -> None:
        """The prospective documents retain no audit ordering, matching, or statistics."""

        authority = AUTHORITY.read_text(encoding="utf-8").lower()
        amendment = AMENDMENT.read_text(encoding="utf-8").lower()
        for phrase in ["audit-to-pool matching", "saturation", "missed-reference proportion", "completeness statistic"]:
            self.assertNotIn("must " + phrase, authority)
            self.assertNotIn("must " + phrase, amendment)
        self.assertIn("excluded from recall, f1, completeness, saturation", authority)
        self.assertIn("no standalone exhaustive/model-blind completeness procedure", amendment)

    def test_decisions_record_separates_n6_from_human_core_metrics(self) -> None:
        """The current decisions record keeps N=6 out of the strict metric table."""

        decisions = DECISIONS.read_text(encoding="utf-8")
        self.assertNotIn("completeness-audit boundaries", decisions)
        self.assertIn("prospective architecture in amendment v0.2", decisions)
        self.assertIn("#### Strict Human Core N=5 metrics", decisions)
        self.assertNotIn("| Complementary N=6 pooled validation", decisions)
        self.assertIn("does not produce Recall, F1, completeness, saturation, or\nmissed-reference statistics", decisions)


if __name__ == "__main__":
    unittest.main()
