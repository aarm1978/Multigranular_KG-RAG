"""Focused contract tests for Human Core N=5 extractor evaluation."""

from __future__ import annotations

import unittest

from src.extraction.llm.publications.human_core_n5_evaluation import (
    EvaluationRecord,
    FrozenInputs,
    _metrics,
    compute,
    load_frozen_inputs,
    pair_nodes,
    pair_relations,
    span_metrics,
)


UNIT = "pub:15:sec:0004:unit:0001"
ARTIFACT = "https://example.test/paper"
ROUTES = {UNIT: {"paperID": "15", "sourceArtifactID": ARTIFACT}}


def evidence(start: int, end: int, text: str | None = None) -> dict[str, object]:
    """Build one canonical evidence span."""
    return {
        "startOffsetInUnit": start,
        "endOffsetInUnit": end,
        "sourceUnitID": UNIT,
        "sourceArtifactID": ARTIFACT,
        "exactText": text or "x" * (end - start),
    }


def node(side: str, candidate: str, start: int, end: int, *, target: str = "PUB-N-TEST", class_id: str = "A-TEST", partition: str | None = None) -> EvaluationRecord:
    """Build a provenance-complete local node record."""
    value = {
        "candidateID": candidate,
        "operationalTargetID": target,
        "ontologyClassID": class_id,
        "identityScope": "source_local",
        "artifactScope": "source_artifact",
        "existingNodeID": None,
        "label": candidate,
    }
    return EvaluationRecord(
        side, partition or ("primaryV014" if side == "reference" else "acceptedSemanticProjection"),
        "human-session" if side == "reference" else "canonical-run", None if side == "reference" else "request-1",
        UNIT, ARTIFACT, "node", value, (evidence(start, end),),
    )


def relation(side: str, candidate: str, source: dict[str, object], target: dict[str, object], *, start: int = 0, end: int = 10) -> EvaluationRecord:
    """Build a provenance-complete relation record."""
    value = {
        "candidateID": candidate,
        "operationalRelationID": "PUB-R-TEST",
        "ontologyRelationID": "C-TEST",
        "source": source,
        "target": target,
    }
    return EvaluationRecord(
        side, "primaryV014" if side == "reference" else "acceptedSemanticProjection",
        "human-session" if side == "reference" else "canonical-run", None if side == "reference" else "request-1",
        UNIT, ARTIFACT, "relation", value, (evidence(start, end),),
    )


class HumanCoreN5EvaluationTests(unittest.TestCase):
    def test_frozen_span_thresholds_are_joint(self) -> None:
        """F1 alone cannot override the frozen precision and recall floors."""
        exact = span_metrics(evidence(0, 10), evidence(0, 10))
        shifted = span_metrics(evidence(0, 10), evidence(3, 13))
        self.assertTrue(exact["exact"])
        self.assertTrue(exact["qualifies"])
        self.assertFalse(shifted["qualifies"])

    def test_node_matching_requires_target_class_evidence_and_one_to_one(self) -> None:
        """Wrong class/target records cannot consume a reference."""
        references = [node("reference", "h1", 0, 10), node("reference", "h2", 0, 10)]
        predictions = [
            node("prediction", "p1", 0, 10),
            node("prediction", "wrong-class", 0, 10, class_id="A-WRONG"),
            node("prediction", "wrong-target", 0, 10, target="PUB-N-WRONG"),
        ]
        pairs = pair_nodes(references, predictions)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0].candidate_id, "h1")
        self.assertEqual(pairs[0][1].candidate_id, "p1")

    def test_relation_requires_directed_endpoint_node_correspondence(self) -> None:
        """Reversed otherwise-compatible endpoints are not a relation TP."""
        h1, h2 = node("reference", "h1", 0, 10), node("reference", "h2", 20, 30)
        p1, p2 = node("prediction", "p1", 0, 10), node("prediction", "p2", 20, 30)
        node_pairs = pair_nodes([h1, h2], [p1, p2])
        human = relation("reference", "hr", {"referenceType": "candidate_node", "referenceID": "h1"}, {"referenceType": "candidate_node", "referenceID": "h2"})
        predicted = relation("prediction", "pr", {"referenceType": "candidate_node", "referenceID": "p2"}, {"referenceType": "candidate_node", "referenceID": "p1"})
        pairs = pair_relations([h1, h2, human], [p1, p2, predicted], node_pairs, ROUTES, {})
        self.assertEqual(pairs, [])

    def test_current_paper_aliases_are_exact_authority_mapped_identity(self) -> None:
        """Human paper:<id> and C1 artifact ID resolve through frozen routing."""
        human = relation("reference", "hr", {"referenceType": "deterministic_node", "referenceID": "paper:15", "artifactID": ARTIFACT}, {"referenceType": "deterministic_node", "referenceID": "paper:15", "artifactID": ARTIFACT})
        predicted = relation("prediction", "pr", {"referenceType": "deterministic_node", "referenceID": ARTIFACT, "artifactID": ARTIFACT}, {"referenceType": "deterministic_node", "referenceID": ARTIFACT, "artifactID": ARTIFACT})
        pairs = pair_relations([human], [predicted], [], ROUTES, {})
        self.assertEqual([(left.candidate_id, right.candidate_id) for left, right, _ in pairs], [("hr", "pr")])

    def test_scoring_scope_excludes_monitor_targets(self) -> None:
        """Only explicit unit-level extract_and_evaluate opportunities enter metrics."""
        evaluated_h = node("reference", "he", 0, 10, target="PUB-N-EVAL")
        evaluated_p = node("prediction", "pe", 0, 10, target="PUB-N-EVAL")
        monitor_h = node("reference", "hm", 20, 30, target="PUB-N-MONITOR")
        monitor_p = node("prediction", "pm", 20, 30, target="PUB-N-MONITOR")
        inputs = FrozenInputs(
            (evaluated_h, monitor_h), (evaluated_p, monitor_p),
            {UNIT: {"PUB-N-EVAL": "node"}}, ROUTES, {}, {},
        )
        result = compute(inputs)
        self.assertEqual(result["aggregate"]["nodes"], _metrics(1, 1, 1))
        self.assertNotIn("PUB-N-MONITOR", result["byTarget"])

    def test_zero_denominators_are_undefined(self) -> None:
        """The contract never invents a zero or one for absent denominators."""
        result = _metrics(0, 0, 0)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["f1"])

    def test_preflight_derives_exact_five_unit_opportunities(self) -> None:
        """Authority loading succeeds without computing or inspecting metrics."""
        inputs = load_frozen_inputs()
        self.assertEqual(len(inputs.opportunities), 5)
        self.assertEqual(set(inputs.opportunities), set(inputs.routes))
        self.assertTrue(all(kind in {"node", "relation"} for rows in inputs.opportunities.values() for kind in rows.values()))


if __name__ == "__main__":
    unittest.main()
