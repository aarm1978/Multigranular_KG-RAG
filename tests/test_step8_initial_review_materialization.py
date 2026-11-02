"""Focused fail-closed tests for Step 8 completed initial-review intake."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.annotation.publication_step8 import INTERFACE_VERSION
from src.annotation.publication_step8.contracts import PACKAGES, ReviewInputs
from src.extraction.llm.publications import step8_initial_review_materialization as intake


class Step8InitialReviewMaterializationTests(unittest.TestCase):
    """Exercise production binding, preservation, agreement, and blinding boundaries."""

    def setUp(self) -> None:
        """Create two role-bound synthetic completed exports in a temporary intake."""

        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        manifest = json.loads((intake.PROJECT_ROOT / intake.DISTRIBUTION_MANIFEST).read_text())
        self.paths: list[Path] = []
        for ordinal, reviewer in enumerate(("reviewer_1", "reviewer_2")):
            bundle = manifest["reviewerBundles"][reviewer]
            role = bundle["reviewRole"]
            package = json.loads((intake.PROJECT_ROOT / "data/curation/papers/m2/publication_step8_blinded_adjudication" / PACKAGES[role][0]).read_text())
            judgments = {item["judgmentItemID"]: "supported_as_proposed" for item in package["judgmentItems"]}
            if ordinal == 1:
                judgments[sorted(judgments)[0]] = "not_supported_as_proposed"
            events = [{"reviewerID": reviewer, "reviewRole": role, "reviewSessionID": bundle["reviewSessionID"],
                       "action": "judgment", "judgmentItemID": item_id, "judgment": value, "revision": index}
                      for index, (item_id, value) in enumerate(sorted(judgments.items()), 1)]
            value = {"exportVersion": INTERFACE_VERSION, "mode": "production", "syntheticDryRun": False,
                     "reviewerID": reviewer, "reviewRole": role, "reviewSessionID": bundle["reviewSessionID"],
                     "inputPackageSha256": PACKAGES[role][1], "runtimeSha256": bundle["packageManifest"]["runtimeSha256"],
                     "sourceInventorySha256": bundle["packageManifest"]["sourceInventorySha256"],
                     "interfaceVersion": INTERFACE_VERSION, "judgments": judgments, "duplicateDecisions": {},
                     "complete": True, "unitCompletion": {unit: True for unit in package["primarySourceUnitIDs"]},
                     "currentPaperEndpointBindings": ReviewInputs(role).endpoint_bindings, "revision": len(events), "revisions": events}
            path = self.root / f"{reviewer}.json"
            path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
            self.paths.append(path)

    def tearDown(self) -> None:
        """Discard synthetic exports without touching received human-review files."""

        self.temporary.cleanup()

    def test_validates_complete_production_pair_and_materializes_immutable_outputs(self) -> None:
        """The exact 6/182 pair yields preservation, agreement, and blinded disagreements."""

        output = self.root / "output"
        paths = intake.materialize(tuple(self.paths), output_root=output)
        preserved = json.loads(paths["preservation"].read_text())
        agreement = json.loads(paths["agreement"].read_text())
        disagreement = json.loads(paths["disagreements"].read_text())
        self.assertEqual([row["judgmentItemCount"] for row in preserved["reviews"]], [182, 182])
        self.assertEqual([row["complete"] for row in preserved["reviews"]], [True, True])
        self.assertEqual({name: row["pairedItemCount"] for name, row in agreement["strata"].items()},
                         {"overall": 182, "nodes": 133, "relations": 49})
        self.assertEqual(disagreement["itemCount"], 1)
        item = disagreement["items"][0]
        self.assertNotIn("reviewerID", json.dumps(item))
        self.assertEqual(set(item["blindedInitialJudgments"]), {"initialReviewA", "initialReviewB"})
        self.assertIn("reviewGuidance", item["judgmentItem"])
        self.assertIn("paragraphContexts", item["judgmentItem"])
        self.assertEqual(paths, intake.materialize(tuple(self.paths), output_root=output))

    def test_rejects_package_drift_before_writing_outputs(self) -> None:
        """A changed production package binding prevents every downstream artifact."""

        value = json.loads(self.paths[0].read_text())
        value["inputPackageSha256"] = "0" * 64
        self.paths[0].write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(intake.Step8InitialReviewError, "REVIEW_PRODUCTION_BINDING_DRIFT"):
            intake.materialize(tuple(self.paths), output_root=self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_rejects_incomplete_item_or_unit_membership(self) -> None:
        """Neither a missing judgment nor an incomplete formal unit can enter analysis."""

        first_original = self.paths[0].read_text()
        value = json.loads(self.paths[0].read_text())
        value["judgments"].pop(next(iter(value["judgments"])))
        self.paths[0].write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(intake.Step8InitialReviewError, "REVIEW_JUDGMENT_MEMBERSHIP_DRIFT"):
            intake.validate_received(tuple(self.paths))
        self.paths[0].write_text(first_original, encoding="utf-8")
        value = json.loads(self.paths[1].read_text())
        value["unitCompletion"][next(iter(value["unitCompletion"]))] = False
        self.paths[1].write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(intake.Step8InitialReviewError, "REVIEW_COMPLETION_DRIFT"):
            intake.validate_received(tuple(self.paths))


if __name__ == "__main__":
    unittest.main()
