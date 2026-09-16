"""Focused regression tests for the additive Publication v0.1.5 authority bundle."""

from __future__ import annotations

import unittest

from src.annotation.publication_pilot1.human_core_reference_composition import compose_human_core_reference
from src.extraction.llm.publications.authority_bundle import V015
from src.extraction.llm.publications.request_builder import load_yaml_object
from src.extraction.llm.publications.semantic_materializer import materialize_generic_mentions


class PublicationV015AuthorityBundleTests(unittest.TestCase):
    """Protect new targets while leaving the v0.1.4 bundle untouched."""

    def test_expected_target_counts_and_full_component_signature(self) -> None:
        """The successor exposes exactly the authorized additive target universe."""

        profile = load_yaml_object(V015.target_inventory_path)
        nodes = [row for row in profile["node_targets"] if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"} or "link_existing" in row.get("allowed_actions", [])]
        relations = [row for row in profile["relation_targets"] if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"} or "link_existing" in row.get("allowed_actions", [])]
        direct = [row for row in nodes if row.get("emission_mode") == "llm_candidate"]
        production = [row for row in relations if row.get("production_responsibility") == "llm" and row.get("emission_mode") == "llm_candidate"]
        self.assertEqual((len(nodes), len(direct), len(relations), len(production)), (48, 42, 28, 27))
        component = next(row for row in production if row["operational_id"] == "PUB-R-C-P34-HASCOMPONENT")
        self.assertEqual(set(component["operational_signatures"][0]["domain"]["classes"]), {"Tool", "ProcessBasedModel", "ConceptualModel", "StatisticalModel", "MLModel", "AgentBasedModel"})

    def test_organization_mentions_are_pipeline_derived(self) -> None:
        """Organization produces Paper and contained-discourse D-26 edges only after acceptance."""

        projection = {"projectionVersion": "publication-accepted-semantic-projection/0.1.0", "authorityBundleID": V015.identifier, "acceptanceBasis": "test", "paperEndpoints": [{"nodeID": "paper", "canonicalPaperID": "p"}], "acceptedEdges": [], "acceptedNodes": [
            {"nodeID": "d", "className": "Method", "accepted": True, "evidenceOccurrences": [{"evidenceSpanID": "d1", "canonicalPaperID": "p", "sourceUnitID": "u", "startOffsetInUnit": 0, "endOffsetInUnit": 20, "startOffsetInDocument": 0, "endOffsetInDocument": 20, "valid": True}]},
            {"nodeID": "o", "className": "Organization", "accepted": True, "evidenceOccurrences": [{"evidenceSpanID": "o1", "canonicalPaperID": "p", "sourceUnitID": "u", "startOffsetInUnit": 2, "endOffsetInUnit": 8, "startOffsetInDocument": 2, "endOffsetInDocument": 8, "valid": True}]},
        ]}
        result = materialize_generic_mentions(projection)
        self.assertTrue(result["notModelAuthored"])
        self.assertEqual({edge["derivationKind"] for edge in result["derivedEdges"]}, {"paper_entity", "discourse_entity"})

    def test_composite_reference_is_partitioned_and_hashed(self) -> None:
        """The Human Core projection verifies immutable inputs without merging them."""

        result = compose_human_core_reference()
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["destructiveMergeAuthorized"])
        self.assertEqual([row["partition"] for row in result["partitions"]], ["primary_v014", "supplemental_v015"])
        self.assertTrue(result["projectionSha256"])


if __name__ == "__main__":
    unittest.main()
