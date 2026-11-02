"""Focused Step 8 intake, immutable assembly, and closure integration checks."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.extraction.llm.publications import step8_closure as c


class Step8ClosureTests(unittest.TestCase):
    """Use synthetic decisions against frozen bindings; never edit a human return."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load accepted artifacts once and create a synthetic export in memory."""
        cls.frozen = c.load_inputs()
        package = cls.frozen["package"]
        cls.export = {"exportType": "publication_step8_final_reconciliation", "exportVersion": "1.0.0",
                      "complete": True, "itemCount": 11, "reconciliationPackageSha256": c.HASHES["package"],
                      "sourceDisagreementPackage": c.binding("disagreements"), "sourceAgreement": c.binding("agreement"),
                      "runtimeSha256": c.shipped_runtime_hash(cls.frozen["manifest"]),
                      "finalDecisions": {key: c.CATEGORIES[i % 4] for i, key in enumerate(package["judgmentItemIDs"])}}

    def test_shipped_runtime_convention_and_real_exporter_schema(self) -> None:
        """Pin the shipped hash, not the hash of a later initial-review UI runtime."""
        self.assertEqual(self.export["runtimeSha256"], "5b19c57e5073dacfa43348d86045833638947080bd68f0fb39a67be727585ded")
        self.assertEqual(c.validate_intake(c.canonical(self.export), self.frozen), self.export)
        self.assertNotIn("reviewerID", self.export)
        self.assertNotIn("meetingDate", self.export)

    def test_invalid_schema_and_bindings_fail_closed(self) -> None:
        """Every emitted binding and completion field is required exactly."""
        mutations = {"exportType": "backup", "exportVersion": "2", "complete": False,
                     "itemCount": 10, "reconciliationPackageSha256": "0" * 64,
                     "runtimeSha256": "0" * 64, "sourceAgreement": {}, "sourceDisagreementPackage": {}}
        for key, bad in mutations.items():
            with self.subTest(key=key):
                value = copy.deepcopy(self.export)
                value[key] = bad
                with self.assertRaises(c.ClosureError):
                    c.validate_intake(c.canonical(value), self.frozen)
        for field in self.export:
            value = copy.deepcopy(self.export)
            del value[field]
            with self.assertRaises(c.ClosureError):
                c.validate_intake(c.canonical(value), self.frozen)
        for key, bad in (("complete", 1), ("itemCount", 11.0), ("unknownField", "unexpected")):
            value = {**self.export, key: bad}
            with self.assertRaises(c.ClosureError):
                c.validate_intake(c.canonical(value), self.frozen)

    def test_strict_json_and_decision_membership(self) -> None:
        """Reject duplicates, malformed JSON, missing/extra decisions and invalid values."""
        for raw in (b'{', b'[]', b'{"x":1,"x":2}', b'{"finalDecisions":{"id":1,"id":2}}', b'{"x":NaN}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(c.ClosureError):
                c.validate_intake(raw, self.frozen)
        first = next(iter(self.export["finalDecisions"]))
        for mode in ("missing", "extra", "invalid", "list"):
            value = copy.deepcopy(self.export)
            if mode == "missing":
                del value["finalDecisions"][first]
            elif mode == "extra":
                value["finalDecisions"]["judgment-item-9999"] = c.CATEGORIES[0]
            else:
                value["finalDecisions"][first] = [] if mode == "list" else "repaired"
            with self.subTest(mode=mode), self.assertRaises(c.ClosureError):
                c.validate_intake(c.canonical(value), self.frozen)

    def test_exact_171_plus_11_and_all_four_outcomes(self) -> None:
        """Preserve agreeing originals and use only explicit returned choices otherwise."""
        rows = c.assemble(self.frozen, self.export)
        self.assertEqual(Counter(row["recordKind"] for row in rows), {"node": 133, "relation": 49})
        self.assertEqual(Counter(row["finalStatusSource"] for row in rows), {"initial_agreement": 171, "joint_reconciliation": 11})
        self.assertEqual(set(row["finalStatus"] for row in rows), set(c.CATEGORIES))
        for row in rows:
            key = row["judgmentItemID"]
            a = self.frozen["reviewer_1"]["judgments"][key]
            b = self.frozen["reviewer_2"]["judgments"][key]
            self.assertEqual(row["initialJudgments"], {"reviewer_1": a, "reviewer_2": b})
            self.assertEqual(row["finalStatus"], a if a == b else self.export["finalDecisions"][key])

    def test_positive_only_partition_and_unchanged_content_lineage(self) -> None:
        """No endpoint promotion or judgment cascade; every outcome retains exact content."""
        artifacts = c.build(c.canonical(self.export))
        positive = c.strict_json(artifacts["positive"])["items"]
        excluded = c.strict_json(artifacts["exclusions"])["items"]
        self.assertTrue(all(row["finalStatus"] == c.CATEGORIES[0] for row in positive))
        self.assertTrue(all(row["finalStatus"] != c.CATEGORIES[0] for row in excluded))
        self.assertEqual(len(positive) + len(excluded), 182)
        self.assertFalse({row["judgmentItemID"] for row in positive} & {row["judgmentItemID"] for row in excluded})
        originals = {item["judgmentItemID"]: item for item in self.frozen["primary"]["judgmentItems"]}
        mapping = {item["judgmentItemID"]: item for item in self.frozen["lineage"]["items"]}
        pool = {item["pooledItemID"]: item for item in self.frozen["pool"]["retainedPooledItems"]}
        for row in positive + excluded:
            self.assertEqual(row["judgmentItem"], originals[row["judgmentItemID"]])
            self.assertEqual(row["lineage"], mapping[row["judgmentItemID"]])
            original = pool[row["lineage"]["step8APooledItemID"]]
            self.assertEqual(original["memberCandidateKeys"], row["lineage"]["memberCandidateKeys"])
            evidence = [{key: ev[key] for key in row["judgmentItem"]["evidenceOccurrences"][0]} for ev in original["evidenceOccurrences"]]
            self.assertEqual(evidence, row["judgmentItem"]["evidenceOccurrences"])

    def test_closure_is_not_gated_on_favorable_status(self) -> None:
        """Unresolved and insufficient outcomes remain results, permitting closure."""
        value = copy.deepcopy(self.export)
        value["finalDecisions"] = {key: "adjudication_unresolved" for key in value["finalDecisions"]}
        result = c.build(c.canonical(value))
        closure = c.strict_json(result["closure"])
        self.assertTrue(all(closure["gates"].values()))
        self.assertEqual(closure["excludedItemCount"], 11)
        self.assertEqual(closure["finalStatusCounts"]["overall"]["adjudication_unresolved"], 11)
        self.assertEqual(closure["researcherAcceptance"], "pending")

    def test_immutable_outputs_idempotency_and_closure_bindings(self) -> None:
        """Byte-exact originals, deterministic output and all-or-nothing conflict preflight."""
        before = {key: (c.ROOT / path).read_bytes() for key, path in c.PATHS.items()}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            intake = root / "returned.json"
            raw = json.dumps(self.export, indent=2).encode() + b'\n\n'
            intake.write_bytes(raw)
            output = root / "out"
            first = c.materialize(intake, destination=output)
            second = c.materialize(intake, destination=output)
            self.assertEqual(first, second)
            self.assertEqual((output / c.OUTPUTS["received"]).read_bytes(), raw)
            closure = c.strict_json(first["closure"])
            for bound in closure["outputBindings"].values():
                self.assertEqual(c.sha((output / bound["path"]).read_bytes()), bound["sha256"])
            for bound in closure["sourceBindings"].values():
                self.assertEqual(c.sha((c.ROOT / bound["path"]).read_bytes()), bound["sha256"])
            conflict = root / "conflict" / c.OUTPUTS["closure"]
            conflict.parent.mkdir(parents=True)
            conflict.write_bytes(b'{}')
            with self.assertRaisesRegex(c.ClosureError, "IMMUTABLE_OUTPUT_CONFLICT"):
                c.materialize(intake, destination=root / "conflict")
            self.assertFalse((root / "conflict" / c.OUTPUTS["received"]).exists())
            intake.write_bytes(b'{"broken":true}')
            with self.assertRaises(c.ClosureError):
                c.materialize(intake, destination=root / "bad")
            self.assertFalse((root / "bad").exists())
        for key, path in c.PATHS.items():
            self.assertEqual((c.ROOT / path).read_bytes(), before[key])

    def test_frozen_input_drift_rejected(self) -> None:
        """Pinned manifest and original artifact hashes cannot be silently replaced."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, path in c.PATHS.items():
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(c.ROOT / path, root / path)
            (root / c.PATHS["manifest"]).write_bytes(b'{}')
            with self.assertRaisesRegex(c.ClosureError, "FROZEN_BINDING_DRIFT"):
                c.load_inputs(root)


if __name__ == "__main__":
    unittest.main()
