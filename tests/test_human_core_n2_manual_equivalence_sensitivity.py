"""Focused tests for the bounded researcher-reviewed N=2 sensitivity artifact."""

from __future__ import annotations

import hashlib
import json
import unittest

from src.extraction.llm.publications.human_core_n2_manual_equivalence_sensitivity import (
    OUTPUT_PATH,
    PRIMARY_PATH,
    SYNTHESIS_PATH,
    build,
    render_synthesis,
)


class HumanCoreN2ManualEquivalenceSensitivityTests(unittest.TestCase):
    """Protect authority binding without changing frozen deterministic matching."""

    def test_checked_in_artifact_is_deterministic_and_primary_is_unmutated(self) -> None:
        result = build()
        self.assertEqual(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")), result)
        self.assertEqual(result["primaryFrozenDeterministicReliability"]["sha256"], hashlib.sha256(PRIMARY_PATH.read_bytes()).hexdigest())
        self.assertEqual(render_synthesis(result), SYNTHESIS_PATH.read_text(encoding="utf-8"))

    def test_exact_case_count_unique_provenance_and_no_primary_overlap(self) -> None:
        result = build()
        additions = result["approvedAdditionalEquivalences"]
        rows = [*additions["extractAndEvaluate"]["nodes"], *additions["extractAndEvaluate"]["relations"], *additions["extractAndMonitor"]["nodes"], *additions["extractAndMonitor"]["relations"]]
        self.assertEqual(len(rows), 26)
        self.assertEqual(len({row["caseID"] for row in rows}), 26)
        for bucket in additions.values():
            for kind_rows in bucket.values():
                self.assertEqual(len({row["annotatorAKey"] for row in kind_rows}), len(kind_rows))
                self.assertEqual(len({row["annotatorBKey"] for row in kind_rows}), len(kind_rows))
        primary = json.loads(PRIMARY_PATH.read_text(encoding="utf-8"))
        pairs = {(row["annotatorAKey"], row["annotatorBKey"]) for kind in ("nodes", "relations") for row in primary["pairings"][kind]}
        self.assertFalse(pairs & {(row["annotatorAKey"], row["annotatorBKey"]) for row in rows})

    def test_b_relation_bindings_and_frozen_sensitivity_totals(self) -> None:
        result = build()
        relations = result["approvedAdditionalEquivalences"]["extractAndEvaluate"]["relations"]
        self.assertEqual([row["annotatorBKey"].rsplit("|", 1)[1] for row in relations], ["edge-0009", "edge-0007", "edge-0008", "edge-0002", "edge-0011", "edge-0004", "edge-0003", "edge-0005", "edge-0006", "edge-0007"])
        expected = {("extractAndEvaluate", "nodes"): (39, 0.7572815533980582), ("extractAndEvaluate", "relations"): (23, 0.8679245283018868), ("extractAndMonitor", "nodes"): (11, 0.5945945945945946), ("extractAndMonitor", "relations"): (3, 0.6666666666666666)}
        for (bucket, kind), (matched, f1) in expected.items():
            row = result["derivedSensitivity"][bucket][kind]
            self.assertEqual((row["sensitivityMatchedSupport"], row["symmetricPairwiseF1"]), (matched, f1))


if __name__ == "__main__":
    unittest.main()
