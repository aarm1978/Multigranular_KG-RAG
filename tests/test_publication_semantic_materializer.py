"""Tests for post-acceptance pipeline-derived Publication generic mentions."""

from copy import deepcopy
import json
import unittest

from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.semantic_materializer import (
    CONTAINMENT_TERM,
    SemanticMaterializationError,
    exact_coordinate_containment,
    materialize_generic_mentions,
)


PAPER = "https://doi.org/10.example/paper"
UNIT = "pub:1:sec:1:unit:1"


def evidence(
    evidence_id: str,
    start_unit: int,
    end_unit: int,
    start_document: int,
    end_document: int,
    *,
    paper: str = PAPER,
    unit: str = UNIT,
    valid: bool = True,
) -> dict:
    """Return one accepted-projection evidence occurrence."""

    return {
        "evidenceSpanID": evidence_id,
        "canonicalPaperID": paper,
        "sourceUnitID": unit,
        "startOffsetInUnit": start_unit,
        "endOffsetInUnit": end_unit,
        "startOffsetInDocument": start_document,
        "endOffsetInDocument": end_document,
        "valid": valid,
    }


def projection() -> dict:
    """Return a valid discourse/entity accepted-semantic fixture."""

    return {
        "projectionVersion": "publication-accepted-semantic-projection/0.1.0",
        "acceptanceBasis": "TEST_ACCEPTANCE",
        "paperEndpoints": [
            {"nodeID": "paper-1", "canonicalPaperID": PAPER, "resolutionSource": "fixture"}
        ],
        "acceptedNodes": [
            {
                "nodeID": "discourse-1",
                "className": "RelatedResearch",
                "ontologyClassID": "A-P18",
                "accepted": True,
                "evidenceOccurrences": [evidence("d-1", 0, 100, 1000, 1100)],
            },
            {
                "nodeID": "entity-1",
                "className": "NamedPlace",
                "ontologyClassID": "A-DOM08",
                "accepted": True,
                "evidenceOccurrences": [evidence("e-1", 20, 40, 1020, 1040)],
            },
        ],
        "acceptedEdges": [],
    }


class PublicationSemanticMaterializerTests(unittest.TestCase):
    """Protect D-26 derivation, suppression, provenance, and determinism."""

    def test_valid_paper_and_discourse_derivation(self) -> None:
        """Accepted valid entity evidence yields Paper and contained discourse edges."""

        result = materialize_generic_mentions(projection())
        self.assertEqual(result["derivationCounts"]["paperAfterSuppression"], 1)
        self.assertEqual(result["derivationCounts"]["discourseAfterSuppression"], 1)
        discourse = next(row for row in result["derivedEdges"] if row["derivationKind"] == "discourse_entity")
        binding = discourse["exactCoordinateContainmentBindings"][0]
        self.assertEqual(binding["containmentRule"], CONTAINMENT_TERM)
        self.assertEqual(binding["discourseEvidenceSpanID"], "d-1")
        self.assertEqual(binding["entityEvidenceSpanID"], "e-1")

    def test_equality_boundaries_are_contained(self) -> None:
        """Exact coordinate containment permits equality at both boundaries."""

        outer = evidence("d", 10, 20, 110, 120)
        inner = evidence("e", 10, 20, 110, 120)
        self.assertTrue(exact_coordinate_containment(outer, inner))

    def test_partial_overlap_is_rejected(self) -> None:
        """Partial overlap is not exact coordinate containment."""

        self.assertFalse(
            exact_coordinate_containment(
                evidence("d", 10, 20, 110, 120), evidence("e", 15, 25, 115, 125)
            )
        )

    def test_unit_only_and_document_only_containment_are_rejected(self) -> None:
        """Both coordinate systems must independently contain the entity span."""

        outer = evidence("d", 0, 100, 1000, 1100)
        unit_only = evidence("e1", 20, 40, 900, 920)
        document_only = evidence("e2", 120, 140, 1020, 1040)
        self.assertFalse(exact_coordinate_containment(outer, unit_only))
        self.assertFalse(exact_coordinate_containment(outer, document_only))

    def test_cross_unit_cross_paper_and_invalid_evidence_are_rejected(self) -> None:
        """Trusted provenance and validity are mandatory for containment."""

        outer = evidence("d", 0, 100, 1000, 1100)
        self.assertFalse(exact_coordinate_containment(outer, evidence("e1", 20, 40, 1020, 1040, unit="other")))
        self.assertFalse(exact_coordinate_containment(outer, evidence("e2", 20, 40, 1020, 1040, paper="other")))
        self.assertFalse(exact_coordinate_containment(outer, evidence("e3", 20, 40, 1020, 1040, valid=False)))

    def test_endpoint_coexistence_without_containment_emits_no_discourse_edge(self) -> None:
        """Same-unit endpoints alone do not authorize discourse mention."""

        value = projection()
        value["acceptedNodes"][1]["evidenceOccurrences"] = [evidence("e-1", 120, 140, 1120, 1140)]
        result = materialize_generic_mentions(value)
        self.assertEqual(result["derivationCounts"]["paperAfterSuppression"], 1)
        self.assertEqual(result["derivationCounts"]["discourseAfterSuppression"], 0)

    def test_missing_and_ambiguous_paper_provenance_fail_closed(self) -> None:
        """A mentionable accepted entity must resolve to exactly one Paper endpoint."""

        missing = projection()
        missing["acceptedNodes"][1]["evidenceOccurrences"] = []
        with self.assertRaises(SemanticMaterializationError):
            materialize_generic_mentions(missing)
        ambiguous = projection()
        ambiguous["acceptedNodes"][1]["evidenceOccurrences"].append(
            evidence("e-2", 20, 40, 1020, 1040, paper="other-paper")
        )
        with self.assertRaises(SemanticMaterializationError):
            materialize_generic_mentions(ambiguous)

    def test_missing_paper_endpoint_fails_closed(self) -> None:
        """The materializer never invents a Paper node or identifier."""

        value = projection()
        value["paperEndpoints"] = []
        with self.assertRaises(SemanticMaterializationError):
            materialize_generic_mentions(value)

    def test_cross_paper_nodes_do_not_produce_discourse_edge(self) -> None:
        """Discourse and entity evidence in distinct Papers cannot be paired."""

        value = projection()
        value["paperEndpoints"].append(
            {"nodeID": "paper-2", "canonicalPaperID": "other-paper", "resolutionSource": "fixture"}
        )
        value["acceptedNodes"][1]["evidenceOccurrences"] = [
            evidence("e-1", 20, 40, 1020, 1040, paper="other-paper")
        ]
        result = materialize_generic_mentions(value)
        self.assertEqual(result["derivationCounts"]["discourseAfterSuppression"], 0)

    def test_stronger_role_suppresses_same_endpoint_fallback(self) -> None:
        """An accepted stronger semantic edge suppresses only its exact pair."""

        value = projection()
        value["acceptedEdges"] = [
            {"edgeID": "strong-1", "sourceID": "discourse-1", "targetID": "entity-1", "relationName": "relatesTo", "accepted": True}
        ]
        result = materialize_generic_mentions(value)
        self.assertEqual(result["derivationCounts"]["paperAfterSuppression"], 1)
        self.assertEqual(result["derivationCounts"]["discourseAfterSuppression"], 0)
        self.assertEqual(result["suppressedDerivations"][0]["suppressedBy"][0]["relationName"], "relatesTo")

    def test_specialized_mentions_suppresses_parent(self) -> None:
        """OWL-specialized mentionsX makes an explicit parent edge redundant."""

        value = projection()
        value["acceptedEdges"] = [
            {"edgeID": "special-1", "sourceID": "paper-1", "targetID": "entity-1", "relationName": "mentionsConcept", "accepted": True}
        ]
        result = materialize_generic_mentions(value)
        self.assertEqual(result["derivationCounts"]["paperAfterSuppression"], 0)
        self.assertEqual(result["derivationCounts"]["discourseAfterSuppression"], 1)

    def test_no_stronger_edge_emits_generic_fallback(self) -> None:
        """The fallback is explicit when no accepted stronger pair exists."""

        self.assertEqual(len(materialize_generic_mentions(projection())["derivedEdges"]), 2)

    def test_identity_order_provenance_and_idempotence(self) -> None:
        """Canonical output is complete, stable, ordered, and byte-identical."""

        first = materialize_generic_mentions(projection())
        second = materialize_generic_mentions(deepcopy(projection()))
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["derivedEdges"], sorted(first["derivedEdges"], key=lambda row: row["edgeID"]))
        for edge in first["derivedEdges"]:
            self.assertTrue(edge["edgeID"].startswith("derived-mentions-"))
            self.assertEqual(edge["ontologyRelationID"], "D-26")
            self.assertEqual(edge["relationName"], "mentions")
            self.assertEqual(edge["canonicalPaperID"], PAPER)
            self.assertEqual(edge["sourcePaperProvenance"]["nodeID"], "paper-1")
            self.assertTrue(edge["entityEvidenceSpanIDs"])
            self.assertIn("policyAuthority", edge)
            self.assertEqual(edge["ontologyAuthority"]["version"], "0.1.4")
        json.dumps(first, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
