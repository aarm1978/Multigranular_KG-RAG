"""Focused tests for frozen Human Core N=2 pre-adjudication matching."""

from __future__ import annotations

import json
import unittest

from src.extraction.llm.publications.human_core_n2_reliability import (
    Record,
    compute,
    pair_nodes,
    span_metrics,
)


UNIT = "pub:34:sec:0015:unit:0001"
ARTIFACT = "https://example.test/paper"


def node(candidate: str, start: int, end: int, class_id: str) -> Record:
    """Build a minimal provenance-complete node fixture."""
    mention = {
        "startOffsetInUnit": start,
        "endOffsetInUnit": end,
        "sourceUnitID": UNIT,
        "sourceArtifactID": ARTIFACT,
        "exactText": "x" * (end - start),
    }
    evidence = {"evidence-1": mention}
    value = {
        "candidateID": candidate,
        "mentionSpan": mention,
        "evidenceSpanIDs": ["evidence-1"],
        "ontologyClassID": class_id,
        "operationalTargetID": f"TARGET-{class_id}",
        "identityScope": "source_local",
        "artifactScope": "source_artifact",
        "existingNodeID": None,
    }
    return Record("annotator_a", "primaryV014", "session", UNIT, "node", value, evidence, ARTIFACT, {}, {})


class HumanCoreN2ReliabilityTests(unittest.TestCase):
    def test_span_thresholds_are_joint_and_exact_is_separate(self) -> None:
        exact = span_metrics(node("a", 0, 10, "A").value["mentionSpan"], node("b", 0, 10, "B").value["mentionSpan"])
        edge = span_metrics(node("a", 0, 10, "A").value["mentionSpan"], node("b", 3, 13, "B").value["mentionSpan"])
        self.assertTrue(exact["qualifies"])
        self.assertTrue(exact["exact"])
        self.assertFalse(edge["qualifies"])
        self.assertFalse(edge["exact"])

    def test_node_assignment_ignores_class_but_stays_one_to_one(self) -> None:
        left = [node("a-1", 0, 10, "CLASS-A"), node("a-2", 0, 10, "CLASS-B")]
        right = [node("b-1", 0, 10, "CLASS-C")]
        pairs = pair_nodes(left, right)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0].value["candidateID"], "a-1")
        self.assertEqual(pairs[0][1].value["candidateID"], "b-1")

    def test_frozen_analysis_recomputes_byte_stably(self) -> None:
        first = json.dumps(compute(), sort_keys=True, separators=(",", ":"))
        second = json.dumps(compute(), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
