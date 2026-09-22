"""Focused tests for frozen Human Core N=2 pre-adjudication matching."""

from __future__ import annotations

import json
import unittest

from src.extraction.llm.publications.human_core_n2_reliability import (
    Record,
    _composed_target_states,
    _endpoint_correspondence,
    _node_index,
    compute,
    pair_nodes,
    span_metrics,
)


UNIT = "pub:34:sec:0015:unit:0001"
ARTIFACT = "https://example.test/paper"


def node(candidate: str, start: int, end: int, class_id: str, *, role: str = "annotator_a", partition: str = "primaryV014", session: str = "session", treatments: dict[str, str] | None = None, states: dict[str, str] | None = None) -> Record:
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
    return Record(role, partition, session, UNIT, "node", value, evidence, ARTIFACT, treatments or {}, states or {})


def relation(candidate: str, source: str, target: str, *, role: str, partition: str, session: str) -> Record:
    """Build a minimal relation fixture with local candidate endpoints."""
    evidence = {"evidence-1": {"startOffsetInUnit": 0, "endOffsetInUnit": 10, "sourceUnitID": UNIT, "sourceArtifactID": ARTIFACT}}
    value = {"candidateID": candidate, "evidenceSpanIDs": ["evidence-1"], "source": {"referenceType": "candidate_node", "referenceID": source}, "target": {"referenceType": "candidate_node", "referenceID": target}, "ontologyRelationID": "C-P1", "operationalRelationID": "TARGET-R"}
    return Record(role, partition, session, UNIT, "relation", value, evidence, ARTIFACT, {}, {})


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

    def test_reversed_endpoints_are_unordered_for_assignment_but_not_direction(self) -> None:
        a1, a2 = node("a1", 0, 10, "A"), node("a2", 20, 30, "A")
        b1 = node("b1", 0, 10, "A", role="annotator_b", partition="reliabilityV015", session="b")
        b2 = node("b2", 20, 30, "A", role="annotator_b", partition="reliabilityV015", session="b")
        ar = relation("ar", "a1", "a2", role="annotator_a", partition="primaryV014", session="session")
        br = relation("br", "b2", "b1", role="annotator_b", partition="reliabilityV015", session="b")
        pairs = {(a1.key, b1.key), (a2.key, b2.key)}
        view = _endpoint_correspondence(ar, br, _node_index([a1, a2, b1, b2]), pairs)
        self.assertEqual(view["unorderedCount"], 2)
        self.assertFalse(view["direction"])

    def test_cross_partition_duplicate_candidate_id_does_not_match_bare_id(self) -> None:
        primary = node("node-1", 0, 10, "A", partition="primaryV014")
        supplemental = node("node-1", 20, 30, "A", partition="supplementalV015", session="supp")
        bnode = node("node-b", 0, 10, "A", role="annotator_b", partition="reliabilityV015", session="b")
        ar = relation("ar", "node-1", "node-1", role="annotator_a", partition="supplementalV015", session="supp")
        br = relation("br", "node-b", "node-b", role="annotator_b", partition="reliabilityV015", session="b")
        view = _endpoint_correspondence(ar, br, _node_index([primary, supplemental, bnode]), {(primary.key, bnode.key)})
        self.assertEqual(view["unorderedCount"], 0)

    def test_supplemental_target_state_composes_with_primary_and_monitor_stays_separate(self) -> None:
        primary = node("p", 0, 10, "A", treatments={"E": "extract_and_evaluate", "M": "extract_and_monitor"}, states={"E": "reviewed_positive", "M": "monitored_review_complete"})
        supplemental = node("s", 20, 30, "A", partition="supplementalV015", session="supp", treatments={"E": "extract_and_evaluate", "S": "extract_and_evaluate"}, states={"E": "reviewed_no_positive", "S": "reviewed_positive"})
        treatments, states = _composed_target_states([primary, supplemental], "annotator_a", UNIT)
        self.assertEqual(treatments["S"], "extract_and_evaluate")
        self.assertEqual(states["E"], "reviewed_positive")
        result = compute()["exhaustivePresenceAbsence"]
        self.assertIn("extractAndMonitorPositiveSet", result)
        self.assertEqual(result["extractAndMonitorPositiveSet"]["scope"], "non-exhaustive positive-set view; absent annotations are not negatives")


if __name__ == "__main__":
    unittest.main()
