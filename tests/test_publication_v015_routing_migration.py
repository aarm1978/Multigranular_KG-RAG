"""Focused deterministic tests for the bounded Publication v0.1.5 routing correction."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.extraction.llm.publications import publication_v015_routing_migration as migration
from src.extraction.llm.publications.production_runner import _prepared_request
from src.extraction.llm.publications.step5_freeze_materialization import _inputs


ROOT = Path(__file__).resolve().parents[1]


class PublicationV015RoutingMigrationTests(unittest.TestCase):
    """Protect the accepted v0.1.5 delta and unchanged historical routing."""

    @classmethod
    def setUpClass(cls) -> None:
        """Derive the prospective authority once without provider interaction."""

        cls.corrected, cls.authority = migration.derive_corrected_routing()
        cls.baseline = {
            row["sourceUnitID"]: row
            for row in map(json.loads, (ROOT / "data/curation/papers/pilot1/publication_pilot1_unit_routing.jsonl").read_text(encoding="utf-8").splitlines())
        }
        cls.inventory = {
            row["sourceUnitID"]: row
            for row in map(json.loads, (ROOT / "data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl").read_text(encoding="utf-8").splitlines())
        }

    def test_organization_is_global_for_every_eligible_source_unit_only(self) -> None:
        """Organization prose follows its cross-category v0.1.5 authority rule."""

        for row in self.corrected:
            open_source = self.inventory[row["sourceUnitID"]]["eligibility"] == "eligible" and self.inventory[row["sourceUnitID"]]["requestEligible"]
            self.assertEqual(
                migration.ORGANIZATION_TARGET in row["eligibleNodeOperationalTargetIDs"],
                open_source,
            )

    def test_agent_based_model_is_limited_to_existing_model_channels(self) -> None:
        """AgentBasedModel does not create a new routing category or lexical classifier."""

        for row in self.corrected:
            base = self.baseline[row["sourceUnitID"]]
            source = self.inventory[row["sourceUnitID"]]
            expected = (
                source["eligibility"] == "eligible"
                and source["requestEligible"]
                and (
                    bool(set(base["eligibleNodeOperationalTargetIDs"]) & migration.EXISTING_MODEL_NODE_TARGETS)
                    or bool(set(base["eligibleRelationOperationalTargetIDs"]) & migration.AGENT_BASED_MODEL_RELATION_TARGETS)
                )
            )
            self.assertEqual(migration.AGENT_BASED_MODEL_TARGET in row["eligibleNodeOperationalTargetIDs"], expected)

    def test_has_component_is_limited_to_existing_tool_or_model_endpoint_channels(self) -> None:
        """C-P34 is routed only where its frozen endpoint families are already open."""

        for row in self.corrected:
            base = self.baseline[row["sourceUnitID"]]
            source = self.inventory[row["sourceUnitID"]]
            expected = (
                source["eligibility"] == "eligible"
                and source["requestEligible"]
                and (
                    bool(set(base["eligibleNodeOperationalTargetIDs"]) & (migration.EXISTING_MODEL_NODE_TARGETS | migration.TOOL_TARGETS))
                    or bool(set(base["eligibleRelationOperationalTargetIDs"]) & migration.AGENT_BASED_MODEL_RELATION_TARGETS)
                )
            )
            self.assertEqual(migration.HAS_COMPONENT_TARGET in row["eligibleRelationOperationalTargetIDs"], expected)

    def test_every_existing_agent_based_model_relation_branch_has_the_new_endpoint_target(self) -> None:
        """Every routed affected relation can now reference an AgentBasedModel candidate."""

        for row in self.corrected:
            routed_relations = set(row["eligibleRelationOperationalTargetIDs"])
            if routed_relations & migration.AGENT_BASED_MODEL_RELATION_TARGETS:
                self.assertIn(migration.AGENT_BASED_MODEL_TARGET, row["eligibleNodeOperationalTargetIDs"])
        for target_id in migration.AGENT_BASED_MODEL_RELATION_TARGETS:
            self.assertIn("AgentBasedModel", json.dumps(self._target(target_id)["operational_signatures"], sort_keys=True))

    def test_non_delta_routing_is_identical_and_unrouted_targets_remain_unrouted(self) -> None:
        """The overlay preserves every historical non-delta target decision exactly."""

        self.assertTrue(self.authority["nonDeltaRoutingProof"]["unchanged"])
        self.assertEqual(
            self.authority["nonDeltaRoutingProof"]["baselineProjectionSha256"],
            self.authority["nonDeltaRoutingProof"]["correctedProjectionSha256"],
        )
        unchanged_zero_targets = {
            "PUB-N-A-DOM07E-AQUIFER",
            "PUB-N-A-DOM07F-VPU",
            "PUB-R-C-P12-HASLIMITATION-FINDING-BRANCH",
            "PUB-R-C-P17-STUDIESFEATURE-METHOD-BRANCH",
            "PUB-R-C-P18-STUDIESPLACE-METHOD-BRANCH",
        }
        for target_id in unchanged_zero_targets:
            self.assertFalse(any(target_id in [*row["eligibleNodeOperationalTargetIDs"], *row["eligibleRelationOperationalTargetIDs"]] for row in self.corrected))
        self.assertFalse(any("PUB-R-D-26" in target_id or target_id.endswith("-MENTIONS") for row in self.corrected for target_id in row["eligibleRelationOperationalTargetIDs"]))

    def test_preflight_is_offline_and_reports_only_the_accepted_delta(self) -> None:
        """The preflight contains no provider activity and no target-set expansion."""

        preflight = migration.build_preflight(self.corrected, self.authority)
        self.assertEqual(preflight["providerModelCalls"], 0)
        self.assertTrue(preflight["readyForSeparateProductionRequestPreflight"])
        self.assertEqual(set(preflight["opportunityCounts"]["allOpenSourceUnits"]), {migration.ORGANIZATION_TARGET, migration.AGENT_BASED_MODEL_TARGET, migration.HAS_COMPONENT_TARGET, *migration.AGENT_BASED_MODEL_RELATION_TARGETS})
        self.assertEqual(preflight["nonDeltaRoutingProof"], self.authority["nonDeltaRoutingProof"])

    def test_corrected_routes_build_existing_request_format_without_pipeline_changes(self) -> None:
        """The existing request constructor accepts the corrected route records unchanged."""

        inventory, _ = _inputs()
        routing = {row["sourceUnitID"]: row for row in self.corrected}
        selected = next(
            row for row in self.corrected
            if migration.AGENT_BASED_MODEL_TARGET in row["eligibleNodeOperationalTargetIDs"]
            and set(row["eligibleRelationOperationalTargetIDs"]) & migration.AGENT_BASED_MODEL_RELATION_TARGETS
        )
        request = _prepared_request(selected["sourceUnitID"], inventory, routing)["request"]
        self.assertEqual(request["authorityBundleID"], "publication-semantic-v0.1.5-schema-v0.1.3")
        self.assertIn(migration.AGENT_BASED_MODEL_TARGET, request["eligibleOperationalTargetIDs"])
        self.assertTrue(set(request["eligibleOperationalTargetIDs"]) & migration.AGENT_BASED_MODEL_RELATION_TARGETS)
        self.assertEqual(request["requestScope"], "complete_section")

    @staticmethod
    def _target(target_id: str) -> dict:
        """Load one frozen v0.1.5 target definition for a signature assertion."""

        import yaml

        profile = yaml.safe_load((ROOT / "src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml").read_text(encoding="utf-8"))
        return next(row for row in [*profile["node_targets"], *profile["relation_targets"]] if row["operational_id"] == target_id)


if __name__ == "__main__":
    unittest.main()
