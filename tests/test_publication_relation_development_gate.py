"""Tests for the no-call Publication full-semantic relation gate."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.extraction.llm.publications.publication_relation_development_gate import (
    CLARIFIED_SOURCE_LOCAL_RELATION_IDS,
    V015_PLAN_PATH,
    V015_SCHEMA012_PLAN_PATH,
    build_relation_development_gate_plan,
    write_relation_development_gate_plan,
)
from src.extraction.llm.publications.authority_bundle import V015, V015_SCHEMA012
from src.extraction.llm.publications.request_builder import canonical_json, canonical_json_file, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    build_c1b_request,
    build_full_semantic_request,
    load_c0_bindings,
    model_authorable_relation_target_ids,
    prepare_unit,
)


class PublicationRelationDevelopmentGateTests(unittest.TestCase):
    """Prove the prospective path exposes exactly 40 nodes and 26 relations."""

    def test_successor_gate_path_is_distinct_and_canonical_check_is_ready(self) -> None:
        """The schema successor cannot overwrite the original V015 gate."""

        self.assertNotEqual(V015_SCHEMA012_PLAN_PATH, V015_PLAN_PATH)
        self.assertEqual(V015_SCHEMA012.identifier, "publication-semantic-v0.1.5-schema-v0.1.2")

    def test_successor_gate_requires_locally_regenerated_canonical_bytes(self) -> None:
        """Run after the researcher generates the distinct successor gate artifact."""

        plan = build_relation_development_gate_plan(V015_SCHEMA012)
        self.assertEqual(plan["authorityBundleID"], V015_SCHEMA012.identifier)
        self.assertEqual((plan["nodePolicy"]["directOpenDiscoveryTargetCount"], plan["modelAuthorableRelationTargetCount"]), (42, 27))
        self.assertIn("PUB-R-C-P34-HASCOMPONENT", plan["modelAuthorableRelationOperationalTargetIDs"])
        self.assertNotIn("D-26", plan["modelAuthorableRelationOperationalTargetIDs"])
        self.assertEqual(plan["providerCalls"], 0)
        self.assertTrue(all(row["providerCompatibility"] == "PASS" for row in plan["units"]))
        self.assertEqual(plan["authorityBindings"]["candidateSchemaSha256"], "d0dd8a402c690f62b4981de665d3247ff03e673fe13a489c0ea258a08b6f31cb")
        self.assertEqual(V015_SCHEMA012_PLAN_PATH.read_bytes(), canonical_json_file(plan))

    def test_relation_universe_and_plan_are_exact_and_deterministic(self) -> None:
        """The plan is stable, call-free, and excludes pipeline-derived D-26."""

        first = build_relation_development_gate_plan()
        second = build_relation_development_gate_plan()
        self.assertEqual(canonical_json_file(first), canonical_json_file(second))
        self.assertEqual(first["status"], "FRESH_DEVSET0_FULL_SEMANTIC_RUN_READY")
        self.assertEqual(first["providerCalls"], 0)
        self.assertFalse(first["modelCallMade"])
        self.assertEqual(first["modelAuthorableRelationTargetCount"], 26)
        self.assertEqual(len(first["relationCoverage"]), 26)
        self.assertFalse(first["genericMentionsModelAuthorable"])
        self.assertNotIn("D-26", canonical_json_file(first).decode("utf-8"))
        self.assertTrue(
            all(row["structuralFixtureCoverage"] for row in first["relationCoverage"])
        )

    def test_every_dev_request_exposes_combined_targets_and_trusted_paper(self) -> None:
        """All ten requests contain exact current targets and one trusted Paper endpoint."""

        relation_ids = model_authorable_relation_target_ids()
        for binding in load_c0_bindings():
            request = build_full_semantic_request(binding)
            with self.subTest(developmentID=binding["developmentID"]):
                self.assertEqual(len(request["eligibleOperationalTargetIDs"]), 66)
                self.assertEqual(
                    request["eligibleOperationalTargetIDs"][-26:], relation_ids
                )
                self.assertEqual(
                    request["deterministicEndpoints"],
                    [
                        {
                            "nodeID": request["sourceArtifactID"],
                            "className": "Paper",
                            "artifactID": request["sourceArtifactID"],
                        }
                    ],
                )
                self.assertNotIn("D-26", request["eligibleOperationalTargetIDs"])

    def test_prepare_path_is_provider_compatible_without_a_call(self) -> None:
        """The actual runner prepares combined schemas while making no provider call."""

        binding = load_c0_bindings()[0]
        with tempfile.TemporaryDirectory() as directory:
            state = prepare_unit(
                binding,
                output_dir=Path(directory),
                full_semantic=True,
            )
        self.assertEqual(state["preflight"]["exposedNodeTargetCount"], 40)
        self.assertEqual(state["preflight"]["exposedRelationTargetCount"], 26)
        self.assertEqual(state["preflight"]["providerCompatibilityGate"], "PASS")
        self.assertEqual(state["preflight"]["networkCalls"], 0)

    def test_historical_default_request_remains_node_only(self) -> None:
        """Prospective combined mode does not mutate the historical C1B default."""

        binding = load_c0_bindings()[0]
        historical = build_c1b_request(binding)
        prospective = build_full_semantic_request(binding)
        self.assertEqual(len(historical["eligibleOperationalTargetIDs"]), 40)
        self.assertEqual(len(prospective["eligibleOperationalTargetIDs"]), 66)
        self.assertEqual(historical["deterministicEndpoints"], [])

    def test_clarified_paths_record_both_endpoint_ownership_modes(self) -> None:
        """Each formerly blocked target records local and exact external paths."""

        plan = build_relation_development_gate_plan()
        paths = {
            row["operationalRelationID"]: row
            for row in plan["clarifiedEndpointPaths"]
        }
        self.assertEqual(tuple(paths), CLARIFIED_SOURCE_LOCAL_RELATION_IDS)
        for row in paths.values():
            self.assertEqual(
                row["sourceLocalCandidatePath"]["relationScope"], "intra_source"
            )
            self.assertEqual(
                row["exactOrResolverExternalPath"]["relationScope"], "inter_source"
            )

    def test_written_plan_matches_in_memory_canonical_bytes(self) -> None:
        """The tracked plan is reproducible from current authorities."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            plan = write_relation_development_gate_plan(path)
            self.assertEqual(path.read_bytes(), canonical_json_file(plan))

    def test_v015_gate_uses_the_authority_aware_preparation_path(self) -> None:
        """The successor plan records V015 coverage without a provider call."""

        plan = build_relation_development_gate_plan(V015)
        self.assertEqual(plan["authorityBundleID"], V015.identifier)
        self.assertEqual(plan["ontologyVersion"], "0.1.5")
        self.assertEqual(plan["promptVersion"], "publication-development-0.1.8")
        self.assertEqual(plan["nodePolicy"], {
            "candidateAuthorableNodeTargetCount": 48,
            "directOpenDiscoveryTargetCount": 42,
            "deterministicContextTargetCount": 4,
            "deferredResolutionTargetCount": 2,
        })
        self.assertEqual(plan["candidateAuthorableRelationTargetCount"], 28)
        self.assertEqual(plan["modelAuthorableRelationTargetCount"], 27)
        self.assertIn("PUB-R-C-P34-HASCOMPONENT", plan["modelAuthorableRelationOperationalTargetIDs"])
        self.assertNotIn("D-26", plan["modelAuthorableRelationOperationalTargetIDs"])
        self.assertTrue(all(row["providerCompatibility"] == "PASS" for row in plan["units"]))

    def test_tracked_v015_plan_is_current_and_hashes_its_authorities(self) -> None:
        """A changed V015 authority cannot leave the tracked gate stale."""

        plan = build_relation_development_gate_plan(V015)
        self.assertEqual(V015_PLAN_PATH.read_bytes(), canonical_json_file(plan))
        projection = dict(plan)
        recorded_hash = projection.pop("planSha256")
        self.assertEqual(recorded_hash, sha256_bytes(canonical_json(projection)))
        self.assertEqual(plan["authorityBindings"], {
            "targetInventorySha256": "84aa773f0a4931fafc50d27240d784b2c977ef29767f3d9e80f3f4a42ef8e6e0",
            "candidateSchemaSha256": "5c7640e80d4f622fcf55c497235ecf2080ee4d99a45e5eca852fa08a22bab66c",
            "promptSha256": "5f8d48d7f95192ce9ec1622a3fe8be8980573afee3f80436cc4869ec2e7bd540",
            "ontologyVersion": "0.1.5",
            "ontologyOwlSha256": "ce5f6d3d8ac926dc8ff872c9a36066758a86068b6681417bf7edc6aaeccf1e71",
        })


if __name__ == "__main__":
    unittest.main()
