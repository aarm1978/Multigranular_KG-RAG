"""Focused successor freeze, replication, and historical-preservation checks."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.extraction.llm.publications import step8_full_secondary_review as full
from src.extraction.llm.publications import step8_blinded_adjudication as historical
from src.annotation.publication_step8.contracts import PACKAGES


class FullSecondaryReviewTests(unittest.TestCase):
    """Verify the prospective successor without authoring any human judgments."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build only the new successor from its accepted frozen primary."""

        cls.artifacts = full.build()
        cls.primary = json.loads((full.PROJECT_ROOT / full.PRIMARY).read_text())

    def test_exact_full_replication_and_ui_binding(self) -> None:
        """Both roles share precisely the same accepted assertions and scope."""

        second, scope = self.artifacts["secondary"], self.artifacts["scope"]
        selection = json.loads((full.PROJECT_ROOT / full.SELECTION).read_text())
        self.assertEqual(scope["selectedPrimarySourceUnitIDs"], sorted(row["primarySourceUnitID"] for row in selection["selectedUnits"]))
        for field in ("primarySourceUnitIDs", "judgmentItems", "duplicateReviewGroups"):
            self.assertEqual(second[field], self.primary[field])
        self.assertEqual((len(second["primarySourceUnitIDs"]), len(second["judgmentItems"])), (6, 182))
        self.assertEqual(Counter(item["recordKind"] for item in second["judgmentItems"]), {"node": 133, "relation": 49})
        self.assertEqual(second["duplicateReviewGroups"], [])
        self.assertEqual(scope["judgmentItemIDs"], [item["judgmentItemID"] for item in second["judgmentItems"]])
        self.assertNotIn("pub:46:sec:0006:unit:0002", scope["selectedPrimarySourceUnitIDs"])
        self.assertEqual(PACKAGES["primary"], (full.PRIMARY.name, full.PRIMARY_SHA256))
        self.assertEqual(PACKAGES["second"], (full.OUTPUTS["secondary"].name, self.artifacts["freeze"]["secondaryReviewPackage"]["sha256"]))

    def test_frozen_history_and_primary_bytes_preserved(self) -> None:
        """Every pinned historical authority/package remains byte-identical."""

        for path, expected in full.PRESERVED.items():
            self.assertEqual(full.binding(path)["sha256"], expected, str(path))
        old = json.loads((full.PROJECT_ROOT / full.PACKAGE_DIR / historical.FILES["secondary"]).read_text())
        subset = json.loads(historical.SUBSET.read_text())
        self.assertEqual((len(old["primarySourceUnitIDs"]), len(old["judgmentItems"])), (2, 45))
        self.assertEqual(set(old["primarySourceUnitIDs"]), set(subset["selectedPrimarySourceUnitIDs"]))

    def test_freeze_integrity_and_deterministic_materialization(self) -> None:
        """The frozen bytes reproduce and every direct binding is exact."""

        self.assertEqual(self.artifacts, full.build())
        for key, value in self.artifacts.items():
            self.assertTrue(historical._self_hash(value))
            self.assertEqual((full.PROJECT_ROOT / full.OUTPUTS[key]).read_bytes(), full.canonical_json(value) + b"\n")
        freeze = self.artifacts["freeze"]
        for key in ("authority", "amendment", "primaryReviewPackage", "secondaryReviewPackage",
                    "secondaryReviewScope", "reviewerInstructions", "materializer"):
            bound = freeze[key]
            self.assertEqual(full.binding(Path(bound["path"]))["sha256"], bound["sha256"])
        predecessor = json.loads(historical.AUTHORITY.read_text())
        retained = dict(predecessor["frozenBindings"])
        retained.pop("secondaryReviewSubset")
        self.assertEqual(freeze["retainedFrozenBindings"], retained)
        self.assertFalse(any(freeze["executionBoundary"].values()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in [*full.PRESERVED, full.AUTHORITY_DOC, full.AMENDMENT_DOC,
                             Path(freeze["materializer"]["path"])]:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(full.PROJECT_ROOT / relative, destination)
            full.materialize(root)
            full.materialize(root)
            for key, path in full.OUTPUTS.items():
                self.assertEqual((root / path).read_bytes(), full.canonical_json(self.artifacts[key]) + b"\n")
            # A divergent output is never overwritten, even when otherwise valid JSON.
            (root / full.OUTPUTS["secondary"]).write_bytes(b"{}\n")
            with self.assertRaisesRegex(historical.Step8BlindingError, "OUTPUT_ARTIFACT_CONFLICT"):
                full.materialize(root)
            (root / full.PRIMARY).write_bytes(b"{}\n")
            with self.assertRaisesRegex(historical.Step8BlindingError, "FROZEN_BINDING_DRIFT"):
                full.build(root)

    def test_blinding_and_unchanged_judgment_instructions(self) -> None:
        """No internal binding metadata enters the new reviewer package."""

        package = self.artifacts["secondary"]
        self.assertEqual(set(package), set(self.primary))
        forbidden = {"provider", "modelName", "modelVersion", "requestID", "candidateID", "candidateKey",
                     "runID", "outputID", "validationLineage", "candidateValidationStatus", "normalizationStatus",
                     "selectedAttemptNumber", "productionAcceptanceStatus", "supersededByRecordID", "pooledItemID"}

        def inspect(value: object) -> None:
            """Reject internal provenance recursively in reviewer-visible objects."""

            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        inspect(package)
        for item in package["judgmentItems"]:
            self.assertEqual(set(item), historical.ITEM_FIELDS)
            self.assertTrue(all(set(evidence) == historical.EVIDENCE_FIELDS for evidence in item["evidenceOccurrences"]))
        old = json.loads((full.PROJECT_ROOT / full.PACKAGE_DIR / historical.FILES["instructions"]).read_text())
        for field in ("ordinaryJudgments", "duplicateDecisions", "duplicateGroupInstruction", "boundary"):
            self.assertEqual(self.artifacts["instructions"][field], old[field])

    def test_successor_predeclares_only_candidate_support_agreement(self) -> None:
        """Frozen declarations retain the requested denominators and interpretation."""

        authority = (full.PROJECT_ROOT / full.AUTHORITY_DOC).read_text()
        amendment = (full.PROJECT_ROOT / full.AMENDMENT_DOC).read_text()
        for document in (authority, amendment):
            self.assertIn("**FROZEN/CLOSED**", document)
            self.assertIn("182", document)
            self.assertIn("133", document)
            self.assertIn("49", document)
            self.assertIn("Cohen's kappa", document)
            self.assertIn("Human Core", document)
        self.assertIn("p_e = 1", authority)
        self.assertIn("do not impute or silently drop missing", authority)
        self.assertIn("not\nextraction IAA", authority)
        self.assertIn("before any Step 8 production", authority)


if __name__ == "__main__":
    unittest.main()
