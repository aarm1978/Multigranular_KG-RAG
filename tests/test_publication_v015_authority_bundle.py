"""Focused regression tests for the additive Publication v0.1.5 authority bundle."""

from __future__ import annotations

import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from unittest.mock import patch
from collections import Counter

from src.annotation.publication_pilot1.human_core_reference_composition import compose_human_core_reference
from src.extraction.llm.publications.authority_bundle import (
    PublicationAuthorityBundle, V014, V015, V015_SCHEMA012, V015_SCHEMA013,
    bundle_for_identifier, is_v015_semantic_family,
)
from src.extraction.llm.publications.request_builder import load_yaml_object
from src.extraction.llm.publications.semantic_materializer import materialize_generic_mentions
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    load_c0_bindings,
    main,
    prepare_unit,
)
from pathlib import Path
import tempfile


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

    def test_schema_successor_bundle_is_canonical_and_fail_closed(self) -> None:
        """Only registered canonical V015-family objects select successor semantics."""

        self.assertIs(bundle_for_identifier(V015_SCHEMA012.identifier), V015_SCHEMA012)
        self.assertIsNot(V014, V015); self.assertIsNot(V015, V015_SCHEMA012)
        self.assertTrue(is_v015_semantic_family(V015))
        self.assertTrue(is_v015_semantic_family(V015_SCHEMA012))
        clone = PublicationAuthorityBundle(*tuple(V015_SCHEMA012.__dict__.values()))
        self.assertFalse(is_v015_semantic_family(clone))
        self.assertTrue(V015.candidate_schema_path.name.endswith("v0.1.1.json"))
        self.assertTrue(V015_SCHEMA012.candidate_schema_path.name.endswith("v0.1.2.json"))
        import hashlib
        self.assertEqual(hashlib.sha256(V015.candidate_schema_path.read_bytes()).hexdigest(), "5c7640e80d4f622fcf55c497235ecf2080ee4d99a45e5eca852fa08a22bab66c")
        self.assertEqual(hashlib.sha256(V015_SCHEMA012.candidate_schema_path.read_bytes()).hexdigest(), "d0dd8a402c690f62b4981de665d3247ff03e673fe13a489c0ea258a08b6f31cb")

    def test_schema013_repairs_only_the_missing_generic_component_enums(self) -> None:
        """The DEV-08 repair is limited to the authorized C-P34 edge pair."""

        import hashlib
        old = json.loads(V015_SCHEMA012.candidate_schema_path.read_text())
        new = json.loads(V015_SCHEMA013.candidate_schema_path.read_text())
        self.assertIs(bundle_for_identifier(V015_SCHEMA013.identifier), V015_SCHEMA013)
        self.assertIsNot(V015_SCHEMA013, V015_SCHEMA012)
        self.assertTrue(is_v015_semantic_family(V015_SCHEMA013))
        self.assertFalse(is_v015_semantic_family(
            PublicationAuthorityBundle(*tuple(V015_SCHEMA013.__dict__.values()))
        ))
        self.assertEqual(
            hashlib.sha256(V015_SCHEMA012.candidate_schema_path.read_bytes()).hexdigest(),
            "d0dd8a402c690f62b4981de665d3247ff03e673fe13a489c0ea258a08b6f31cb",
        )
        self.assertEqual(
            hashlib.sha256(V015_SCHEMA013.candidate_schema_path.read_bytes()).hexdigest(),
            "cca85195d6d4833cf754907480b1b25faba8aa10c050856a3bd4f373d05277dd",
        )
        old_props = old["$defs"]["candidateEdge"]["properties"]
        new_props = new["$defs"]["candidateEdge"]["properties"]
        self.assertNotIn("C-P34", old_props["ontologyRelationID"]["enum"])
        self.assertNotIn("hasComponent", old_props["relationName"]["enum"])
        self.assertIn("C-P34", new_props["ontologyRelationID"]["enum"])
        self.assertIn("hasComponent", new_props["relationName"]["enum"])
        self.assertEqual(
            set(new_props["ontologyRelationID"]["enum"]) - set(old_props["ontologyRelationID"]["enum"]),
            {"C-P34"},
        )
        self.assertEqual(
            set(new_props["relationName"]["enum"]) - set(old_props["relationName"]["enum"]),
            {"hasComponent"},
        )
        self.assertEqual(new_props["operationalRelationID"]["enum"], old_props["operationalRelationID"]["enum"])

    def test_schema013_completely_represents_v015_family_target_authorities(self) -> None:
        """Every candidate-authorable V015 target has a representable schema identity."""

        profile = load_yaml_object(V015_SCHEMA013.target_inventory_path)
        schema013 = json.loads(V015_SCHEMA013.candidate_schema_path.read_text())
        schema012 = json.loads(V015_SCHEMA012.candidate_schema_path.read_text())
        node_props = schema013["$defs"]["candidateNode"]["properties"]
        edge_props = schema013["$defs"]["candidateEdge"]["properties"]
        for row in profile["node_targets"]:
            if row.get("emission_mode") not in {"llm_candidate", "resolver_mediated_candidate"} and "link_existing" not in row.get("allowed_actions", []):
                continue
            for formal in row["formal_classes"]:
                self.assertIn(formal["name"], node_props["className"]["enum"])
            for ontology_id in row["ontology_ids"]:
                self.assertIn(ontology_id, node_props["ontologyClassID"]["enum"])
        missing012: set[tuple[str, str]] = set()
        old_edge_props = schema012["$defs"]["candidateEdge"]["properties"]
        for row in profile["relation_targets"]:
            if row.get("emission_mode") not in {"llm_candidate", "resolver_mediated_candidate"} and "link_existing" not in row.get("allowed_actions", []):
                continue
            for formal in row["formal_relations"]:
                pair = (formal["id"], formal["name"])
                self.assertIn(pair[0], edge_props["ontologyRelationID"]["enum"])
                self.assertIn(pair[1], edge_props["relationName"]["enum"])
                if pair[0] not in old_edge_props["ontologyRelationID"]["enum"] or pair[1] not in old_edge_props["relationName"]["enum"]:
                    missing012.add(pair)
            self.assertIn(row["operational_id"], edge_props["operationalRelationID"]["enum"])
        self.assertEqual(missing012, {("C-P34", "hasComponent")})

    def test_schema_successor_represents_every_direct_v015_node(self) -> None:
        """The mechanical 0.1.2 enum successor covers all direct V015 targets."""

        import json
        old = json.loads(V015.candidate_schema_path.read_text())
        new = json.loads(V015_SCHEMA012.candidate_schema_path.read_text())
        old_props = old["$defs"]["candidateNode"]["properties"]
        new_props = new["$defs"]["candidateNode"]["properties"]
        self.assertNotIn("Organization", old_props["className"]["enum"])
        self.assertNotIn("A-AG02", old_props["ontologyClassID"]["enum"])
        self.assertIn("Organization", new_props["className"]["enum"])
        self.assertIn("AgentBasedModel", new_props["className"]["enum"])
        self.assertIn("A-AG02", new_props["ontologyClassID"]["enum"])
        self.assertIn("A-DOM03e", new_props["ontologyClassID"]["enum"])
        profile = load_yaml_object(V015.target_inventory_path)
        for row in profile["node_targets"]:
            if row.get("emission_mode") == "llm_candidate":
                self.assertIn(row["formal_classes"][0]["name"], new_props["className"]["enum"])
                self.assertIn(row["ontology_ids"][0], new_props["ontologyClassID"]["enum"])

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

    def test_real_full_semantic_preflight_is_v015_and_offline(self) -> None:
        """The same future-live preparation path selects only V015 authorities."""
        with tempfile.TemporaryDirectory() as directory:
            state = prepare_unit(load_c0_bindings()[0], output_dir=Path(directory), full_semantic=True, authority_bundle=V015)
        request, preflight = state["request"], state["preflight"]
        self.assertEqual(request["authorityBundleID"], V015.identifier)
        self.assertEqual((preflight["exposedNodeTargetCount"], preflight["exposedRelationTargetCount"]), (42, 27))
        self.assertEqual(request["prompt"]["version"], "publication-development-0.1.8")
        self.assertIn("PUB-R-C-P34-HASCOMPONENT", request["eligibleOperationalTargetIDs"])
        self.assertNotIn("D-26", request["eligibleOperationalTargetIDs"])
        self.assertEqual(preflight["providerCompatibilityGate"], "PASS")

    def test_successor_metadata_binds_the_repaired_inventory(self) -> None:
        """The V015 profile/schema chain records its actual operational counts."""

        profile = load_yaml_object(V015.target_inventory_path)
        self.assertEqual(profile["operational_row_counts"]["nodes"]["total"], 62)
        self.assertEqual(profile["operational_row_counts"]["relations"]["total"], 45)
        self.assertEqual(
            profile["cross_category_targets"][0]["operational_id"],
            "PUB-N-A-AG02-ORGANIZATION-PROSE",
        )

    def test_all_stored_count_summaries_match_actual_inventory_rows(self) -> None:
        """V015 count metadata is derived from, and agrees with, target rows."""

        profile = load_yaml_object(V015.target_inventory_path)
        expected = {
            "nodes": Counter(row["pilot_treatment"] for row in profile["node_targets"]),
            "relations": Counter(row["pilot_treatment"] for row in profile["relation_targets"]),
        }
        legacy = profile["counts"]
        for kind, rows_key, legacy_key in (
            ("nodes", "node_targets", "nodes_by_treatment"),
            ("relations", "relation_targets", "relations_by_treatment"),
        ):
            actual = expected[kind]
            self.assertEqual(profile["operational_row_counts"][kind]["total"], len(profile[rows_key]))
            self.assertEqual(dict(profile["operational_row_counts"][kind]["by_pilot_treatment"]), dict(actual))
            self.assertEqual(legacy[f"{kind[:-1]}_operational_rows"], len(profile[rows_key]))
            self.assertEqual(dict(legacy[legacy_key]), dict(actual))

    def test_cli_requires_authority_and_prepares_v015_without_network(self) -> None:
        """The real CLI cannot silently choose V014 for a full-semantic run."""

        with self.assertRaises(SystemExit) as missing:
            with redirect_stderr(StringIO()):
                main(["--prepare-only", "--full-semantic"])
        self.assertEqual(missing.exception.code, 2)

        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()) as stdout:
            # A single binding proves the real CLI path without repeating the
            # all-ten-unit batch already covered by the gate.
            with patch(
                "src.extraction.llm.publications.run_publication_full_devset0_node_development.load_c0_bindings",
                return_value=[load_c0_bindings()[0]],
            ):
                status = main([
                    "--prepare-only", "--full-semantic",
                    "--authority-bundle", V015.identifier,
                    "--output-dir", directory,
                ])
                result = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(result["networkCalls"], 0)
        self.assertTrue(result["allProviderCompatibilityGatesPass"])
        first = result["units"][0]
        self.assertEqual((first["exposedNodeTargetCount"], first["exposedRelationTargetCount"]), (42, 27))
        self.assertEqual(first["authorityBundleID"], V015.identifier)
        self.assertEqual(first["promptVersion"], "publication-development-0.1.8")
        self.assertEqual(first["candidateSchemaVersion"], "0.1.1")
        self.assertEqual(first["ontologyVersion"], "0.1.5")
        self.assertIn("PUB-R-C-P34-HASCOMPONENT", first["exposedRelationOperationalTargetIDs"])
        self.assertIn("PUB-N-A-DOM03E-AGENTBASEDMODEL", first["exposedNodeOperationalTargetIDs"])
        self.assertIn("PUB-N-A-AG02-ORGANIZATION-PROSE", first["exposedNodeOperationalTargetIDs"])
        self.assertNotIn("D-26", first["exposedRelationOperationalTargetIDs"])


if __name__ == "__main__":
    unittest.main()
