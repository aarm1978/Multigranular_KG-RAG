"""Focused tests for Publication Pilot 1 Block A infrastructure."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import unittest

import jsonschema
import yaml

from src.extraction.llm.publications import publication_pilot1_block_a as block_a


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/curation/papers/pilot1"
INVENTORY = DATA / "publication_pilot1_source_unit_inventory.jsonl"
WORKLIST = DATA / "publication_pilot1_screening_worklist.csv"
MAPPING = DATA / "publication_pilot1_target_family_mapping.yaml"
CATALOG = DATA / "publication_pilot1_target_display_catalog.yaml"
SELECTION = DATA / "publication_pilot1_selection_policy.yaml"
GATE0 = DATA / "publication_pilot1_gate0_policy.yaml"
PROFILE = ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"


class PublicationPilot1BlockATests(unittest.TestCase):
    """Protect the first-run human-screening boundary and deterministic contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load generated infrastructure and frozen inputs once."""

        cls.inventory = [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines()]
        with WORKLIST.open(encoding="utf-8", newline="") as handle:
            cls.worklist = list(csv.DictReader(handle))
        cls.mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
        cls.catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        cls.selection = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
        cls.gate0 = yaml.safe_load(GATE0.read_text(encoding="utf-8"))
        cls.profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
        cls.manifest = json.loads((DATA / "publication_pilot1_source_unit_manifest.json").read_text(encoding="utf-8"))
        cls.conversion_by_paper = block_a._conversion_by_paper(cls.manifest)

    def test_worklist_has_all_358_units_once_with_preserved_hashes(self) -> None:
        """Every accepted unit and exact text hash appears once."""

        self.assertEqual(len(self.worklist), 358)
        self.assertEqual(len({row["sourceUnitID"] for row in self.worklist}), 358)
        expected = {row["sourceUnitID"]: row["textHash"] for row in self.inventory}
        self.assertEqual({row["sourceUnitID"]: row["sourceUnitTextHash"] for row in self.worklist}, expected)
        inventory_by_id = {row["sourceUnitID"]: row for row in self.inventory}
        for row in self.worklist:
            source = inventory_by_id[row["sourceUnitID"]]
            self.assertEqual(row["sourceArtifactID"], source["canonicalArtifactID"])
            self.assertEqual(row["paperID"], source["paperID"])
            self.assertEqual(row["sourceConversionStatus"], self.conversion_by_paper[source["paperID"]])

    def test_human_semantic_fields_are_blank_for_every_open_unit(self) -> None:
        """The generator never semantically screens the accepted real population."""

        semantic = (
            "likelyExhaustiveEmptyTargetIDs", "likelyRecurringDistinctions",
            "expectedAssertionDensity", "expectedRelationDensity", "routingComplexity",
            "distributedEvidenceLikely", "sectionContextUseful", "deterministicEndpointLikely",
            "routedNodeOperationalTargetIDs", "routedRelationOperationalTargetIDs",
        )
        open_rows = [row for row in self.worklist if row["sourceEligibility"] == "eligible"]
        self.assertEqual(len(open_rows), 267)
        for row in open_rows:
            self.assertTrue(all(row[field] == "" for field in semantic))
            self.assertEqual(row["screeningStatus"], "")
            self.assertNotIn("likelyReportingFamilies", row)
            self.assertNotIn("likelySamplingStrata", row)

    def test_structural_units_are_not_open_and_publication34_review_stays_blocked(self) -> None:
        """Accepted context/exclusion decisions and three review blocks cannot leak into routing."""

        counts = {}
        for row in self.worklist:
            counts[row["sourceEligibility"]] = counts.get(row["sourceEligibility"], 0) + 1
        self.assertEqual(counts, {"context_only": 49, "eligible": 267, "excluded": 39, "needs_review": 3})
        blocked = [row for row in self.worklist if row["sourceEligibility"] == "needs_review"]
        self.assertEqual({row["paperID"] for row in blocked}, {"34"})
        self.assertTrue(all(row["screeningStatus"] == "blocked_needs_review" for row in blocked))
        self.assertTrue(all(not row["routedNodeOperationalTargetIDs"] and not row["routedRelationOperationalTargetIDs"] for row in blocked))

    def test_target_mapping_covers_profile_once_and_uses_exact_families(self) -> None:
        """All 105 targets satisfy family/role conditional rules without an eleventh family."""

        expected = [target["operational_id"] for key in ("node_targets", "relation_targets") for target in self.profile[key]]
        rows = self.mapping["targets"]
        self.assertEqual(len(rows), 105)
        self.assertCountEqual([row["operationalTargetID"] for row in rows], expected)
        self.assertEqual(tuple(self.mapping["reportingFamilies"]), block_a.REPORTING_FAMILIES)
        block_a.validate_target_mapping(rows, self.profile)
        for row in rows:
            if row["decisionRole"] in {"blocking", "monitored"}:
                self.assertIn(row["reportingFamily"], block_a.REPORTING_FAMILIES)
            else:
                self.assertIsNone(row["reportingFamily"])

    def test_display_catalog_is_complete_unique_and_relation_safe(self) -> None:
        """Human-visible IDs are unique and every relation retains signatures."""

        rows = self.catalog["targets"]
        visible = [row for row in rows if row["humanVisible"]]
        self.assertEqual(len(rows), 105)
        self.assertEqual(len(visible), len({row["operationalTargetID"] for row in visible}))
        relations = [row for row in rows if row["targetKind"] == "relation"]
        self.assertTrue(all(row["domainClasses"] and row["rangeClasses"] and row["operationalSignatures"] for row in relations))
        self.assertIn("never truncate", self.catalog["menuPolicy"])

    def _synthetic_row(self, routed_nodes: list[str] | None = None) -> tuple[dict[str, str], dict[str, object]]:
        """Create a source-independent synthetic human-reviewed routing fixture."""

        source = dict(self.inventory[0])
        source.update({
            "paperID": "synthetic", "sourceUnitID": "pub:synthetic:sec:0001:unit:0001",
            "canonicalArtifactID": "https://example.org/synthetic",
            "sectionID": "pub:synthetic:sec:0001", "sectionRole": "methods",
            "eligibility": "eligible", "requestEligible": True, "reviewRequired": False,
            "reviewReasons": [], "deterministicNodeRefs": [], "deterministicEdgeRefs": [],
            "deferredRecordRefs": [], "textHash": "a" * 64,
        })
        conversion = {"synthetic": "canonical_markdown_available"}
        generated = block_a.build_worklist([source], conversion).decode("utf-8")
        row = next(csv.DictReader(io.StringIO(generated)))
        row.update({
            "screeningReviewerID": "synthetic-reviewer", "screenedAt": "2026-01-01T00:00:00Z",
            "screeningStatus": "reviewed", "screeningRationale": "synthetic fixture",
            "likelyExhaustiveEmptyTargetIDs": "", "likelyRecurringDistinctions": "Model/Method/Algorithm/Tool",
            "expectedAssertionDensity": "medium",
            "expectedRelationDensity": "low", "routingComplexity": "high",
            "distributedEvidenceLikely": "false", "sectionContextUseful": "true",
            "deterministicEndpointLikely": "false",
            "routedNodeOperationalTargetIDs": "|".join(routed_nodes or []),
            "routedRelationOperationalTargetIDs": "", "screeningNotes": "",
        })
        return row, source

    def test_routing_rejects_unknown_targets_but_does_not_truncate_at_twelve(self) -> None:
        """Profile validation is strict while the interface menu size is not a semantic cap."""

        open_nodes = [target["operational_id"] for target in self.profile["node_targets"] if target["pilot_treatment"] in block_a.SEMANTIC_TREATMENTS][:13]
        row, source = self._synthetic_row(open_nodes)
        _, routes = block_a._validate_reviewed_rows(
            [row], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertEqual(routes[0]["menuDiagnostics"]["nodeTargetCount"], 13)
        self.assertTrue(routes[0]["routingDoesNotAssertPresence"])
        self.assertEqual(routes[0]["likelyReportingFamilies"], [
            "discourse_structure", "findings_conclusions_limitations_and_future_work",
            "methods_and_experiments", "research_framing",
        ])
        self.assertEqual(routes[0]["likelySamplingStrata"], ["core_discourse_nodes"])
        bad = dict(row, routedNodeOperationalTargetIDs="PUB-N-UNKNOWN")
        with self.assertRaisesRegex(block_a.BlockAValidationError, "ROUTING_UNKNOWN_OPERATIONAL_TARGET"):
            block_a._validate_reviewed_rows(
                [bad], [source], self.profile, {"synthetic": "canonical_markdown_available"}
            )

    def test_no_target_and_deferred_only_reviews_are_not_primary_candidates(self) -> None:
        """Human-reviewed zero-primary routes remain outside calibration and candidate pools."""

        row, source = self._synthetic_row([])
        _, routes = block_a._validate_reviewed_rows(
            [row], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertEqual(routes[0]["routingStatus"], "reviewed_no_eligible_target")
        selected, _ = block_a._select_calibration(
            [{"sourceUnitID": source["sourceUnitID"]}], routes, [source]
        )
        self.assertEqual(selected, [])

        deferred = dict(
            row,
            routedNodeOperationalTargetIDs="PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B",
        )
        _, deferred_routes = block_a._validate_reviewed_rows(
            [deferred], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertEqual(deferred_routes[0]["routingStatus"], "reviewed_no_eligible_target")
        self.assertEqual(deferred_routes[0]["primaryEligibleOperationalTargetIDs"], [])
        self.assertEqual(deferred_routes[0]["likelyReportingFamilies"], [])
        self.assertEqual(deferred_routes[0]["likelySamplingStrata"], [])

    def test_artifact_versions_are_explicit_and_independent(self) -> None:
        """Changed and unchanged Block A artifacts retain their own correct versions."""

        self.assertEqual(block_a.BLOCK_A_INFRASTRUCTURE_VERSION, "0.1.2")
        self.assertEqual(block_a.SCREENING_SCHEMA_VERSION, "0.1.1")
        self.assertEqual(block_a.ROUTING_SCHEMA_VERSION, "0.1.1")
        self.assertEqual(block_a.SELECTION_POLICY_VERSION, "0.1.2")
        self.assertEqual(block_a.CANDIDATE_ORDER_VERSION, "0.1.1")
        self.assertEqual(block_a.CALIBRATION_MANIFEST_VERSION, "0.1.1")
        self.assertEqual(block_a.DEFAULT_EXHAUSTIVE_TREATMENTS, {"extract_and_evaluate"})
        self.assertEqual(block_a.SEMANTIC_TREATMENTS, {"extract_and_evaluate", "extract_and_monitor"})
        self.assertEqual(self.mapping["mappingVersion"], "0.1.0")
        self.assertEqual(self.catalog["catalogVersion"], "0.1.0")
        self.assertEqual(self.gate0["gate0PolicyVersion"], "0.1.0")

    def test_exhaustive_empty_expectation_uses_default_exhaustive_treatment_only(self) -> None:
        """Only routed evaluate targets may carry prospective exhaustive-empty expectations."""

        row, source = self._synthetic_row([])
        evaluate = dict(
            row,
            routedNodeOperationalTargetIDs="PUB-N-A-P13-METHOD",
            likelyExhaustiveEmptyTargetIDs="PUB-N-A-P13-METHOD",
        )
        screening, routes = block_a._validate_reviewed_rows(
            [evaluate], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertEqual(screening[0]["likelyExhaustiveEmptyTargetIDs"], ["PUB-N-A-P13-METHOD"])
        self.assertEqual(routes[0]["routingStatus"], "routed")

        monitor_id = "PUB-N-A-P05-BACKGROUND"
        monitor_empty = dict(
            row,
            routedNodeOperationalTargetIDs=monitor_id,
            likelyExhaustiveEmptyTargetIDs=monitor_id,
        )
        with self.assertRaisesRegex(block_a.BlockAValidationError, "EXHAUSTIVE_EMPTY_TARGET_NOT_DEFAULT_EXHAUSTIVE"):
            block_a._validate_reviewed_rows(
                [monitor_empty], [source], self.profile, {"synthetic": "canonical_markdown_available"}
            )

        for target_id in (
            "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B",
            "PUB-N-A-ID01-IDENTIFIER",
        ):
            bad = dict(row, likelyExhaustiveEmptyTargetIDs=target_id)
            with self.assertRaisesRegex(block_a.BlockAValidationError, "EXHAUSTIVE_EMPTY_TARGET_NOT_DEFAULT_EXHAUSTIVE"):
                block_a._validate_reviewed_rows(
                    [bad], [source], self.profile, {"synthetic": "canonical_markdown_available"}
                )

    def test_monitored_target_remains_routable_and_primary_eligible(self) -> None:
        """Completeness restrictions do not narrow ordinary monitored routing semantics."""

        monitor_id = "PUB-N-A-P05-BACKGROUND"
        row, source = self._synthetic_row([monitor_id])
        screening, routes = block_a._validate_reviewed_rows(
            [row], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertEqual(routes[0]["routingStatus"], "routed")
        self.assertEqual(routes[0]["primaryEligibleOperationalTargetIDs"], [monitor_id])
        self.assertEqual(screening[0]["likelyReportingFamilies"], ["research_framing"])
        self.assertEqual(screening[0]["likelySamplingStrata"], ["core_discourse_nodes"])

    def test_schemas_exclude_gold_and_model_fields_and_validate_synthetic_records(self) -> None:
        """Strict schemas keep screening/routing separate from gold and predictions."""

        forbidden = {"actualNodeAnnotations", "actualRelationAnnotations", "evidenceSpans", "goldLabels", "modelPredictions", "modelConfidence"}
        for name in ("publication_pilot1_screening_record.schema.json", "publication_pilot1_unit_routing.schema.json"):
            schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            self.assertTrue(forbidden.isdisjoint(schema["properties"]))
            self.assertFalse(schema["additionalProperties"])
        routing_schema = json.loads((ROOT / "schemas/publication_pilot1_unit_routing.schema.json").read_text(encoding="utf-8"))
        fixtures = [json.loads(line) for line in (ROOT / "tests/fixtures/publication_pilot1_block_a_synthetic_routing.jsonl").read_text(encoding="utf-8").splitlines()]
        for fixture in fixtures:
            jsonschema.validate(fixture, routing_schema)
        self.assertEqual(fixtures[0]["menuDiagnostics"]["nodeTargetCount"], 13)

    def test_selection_policy_is_model_blind_per_artifact_and_block_b_safe(self) -> None:
        """The prospective policy cannot consume model/timing results or select final partitions."""

        text = SELECTION.read_text(encoding="utf-8")
        self.assertIn("post-Gate-0 ordering is per artifact", text)
        self.assertIn("Timing never enters the order", text)
        self.assertIn("experiment arm", text)
        self.assertIn("reliabilitySourceUnitIDs", self.selection["blockBOnlyFields"])
        self.assertIn("at least one routed blocking/monitored target", self.selection["eligiblePrimaryRule"])
        self.assertIn("canonicalArtifactID", self.selection["artifactIdentityRule"])
        self.assertEqual(
            self.selection["calibrationSelectionRule"]["knownRecurringAnnotationDistinctions"],
            list(block_a.RECURRING_DISTINCTIONS),
        )
        self.assertEqual(
            self.selection["prospectiveCompletenessRule"]["defaultExhaustiveTreatments"],
            ["extract_and_evaluate"],
        )
        self.assertEqual(
            self.selection["prospectiveCompletenessRule"]["defaultNonExhaustiveMonitorTreatments"],
            ["extract_and_monitor"],
        )
        dimensions = self.selection["calibrationSelectionRule"]["dimensions"]
        for dimension in (
            "expectedAssertionDensity", "routingComplexity", "sourceConversionStatus",
            "likelyRecurringDistinctions",
        ):
            self.assertIn(dimension, dimensions)
        self.assertNotIn("experimentArm:", text)
        self.assertNotIn("modelPrediction:", text)

    def test_context_flags_are_independent_human_inputs(self) -> None:
        """Section-context usefulness is not derived from distributed-evidence likelihood."""

        row, source = self._synthetic_row(["PUB-N-A-P13-METHOD"])
        self.assertEqual(row["distributedEvidenceLikely"], "false")
        self.assertEqual(row["sectionContextUseful"], "true")
        screening, routes = block_a._validate_reviewed_rows(
            [row], [source], self.profile, {"synthetic": "canonical_markdown_available"}
        )
        self.assertFalse(screening[0]["distributedEvidenceLikely"])
        self.assertTrue(screening[0]["sectionContextUseful"])
        self.assertFalse(routes[0]["contextFlags"]["distributedEvidenceLikely"])
        self.assertTrue(routes[0]["contextFlags"]["sectionContextUseful"])

    def test_calibration_selection_is_deterministic_and_disjointable(self) -> None:
        """A fixed synthetic reviewed fixture always produces the same selected IDs."""

        inventory, screening, routing = [], [], []
        for index in range(20):
            uid = f"pub:synthetic:sec:{index:04d}:unit:0001"
            inventory.append({"sourceUnitID": uid, "paperID": str(index % 3), "characterCount": 1000 + index * 500, "sectionRole": ("methods", "results", "discussion")[index % 3]})
            screening.append({
                "sourceUnitID": uid,
                "expectedAssertionDensity": ("low", "medium", "high")[index % 3],
                "expectedRelationDensity": ("low", "medium", "high")[index % 3],
                "routingComplexity": ("low", "medium", "high")[index % 3],
                "sourceConversionStatus": "canonical_markdown_available" if index % 4 else "canonical_markdown_sanitized_forbidden_controls",
                "likelyReportingFamilies": [block_a.REPORTING_FAMILIES[index % 10]],
                "likelySamplingStrata": [block_a.SAMPLING_STRATA[index % 5]],
                "likelyRecurringDistinctions": [block_a.RECURRING_DISTINCTIONS[index % 5]],
                "likelyExhaustiveEmptyTargetIDs": [] if index % 4 else ["synthetic-target"],
                "distributedEvidenceLikely": index % 2 == 0,
                "sectionContextUseful": index % 2 == 1,
                "deterministicEndpointLikely": index % 3 == 0,
            })
            routing.append({"sourceUnitID": uid, "routingStatus": "routed", "eligibleNodeOperationalTargetIDs": ["synthetic"] * (index % 5 + 1), "eligibleRelationOperationalTargetIDs": []})
        first, _ = block_a._select_calibration(screening, routing, inventory)
        second, _ = block_a._select_calibration(screening, routing, inventory)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertTrue(set(first).isdisjoint({row["sourceUnitID"] for row in inventory if row["sourceUnitID"] not in first}))

    def test_gate0_thresholds_percentiles_and_zero_assertion_diagnostic(self) -> None:
        """Gate 0 is exact, nearest-rank, Publication-only, and has no hidden lower quota."""

        decisions = self.gate0["decisions"]
        self.assertEqual(decisions["GREEN"]["condition"], "P50 <= 15 AND P75 <= 20 AND P90 <= 30")
        self.assertEqual(decisions["AMBER"]["condition"], "GREEN fails AND P50 <= 20 AND P75 <= 25 AND P90 <= 40")
        self.assertEqual(decisions["RED"]["condition"], "P50 > 20 OR P75 > 25 OR P90 > 40")
        self.assertEqual(decisions["GREEN"]["publicationUnitsPerArtifact"], 5)
        self.assertEqual(decisions["AMBER"]["publicationUnitsPerArtifact"], 4)
        self.assertIsNone(decisions["RED"]["publicationUnitsPerArtifact"])
        self.assertEqual(self.gate0["percentiles"]["algorithm"], "nearest_rank")
        self.assertEqual(block_a.nearest_rank([1, 2, 3, 4], .75), 3)
        self.assertIsNone(block_a.timing_diagnostics(10, 0, 0)["minutesPerAssertion"])

    def test_sample_scaffold_remains_candidate_and_upstream_hashes_are_unchanged(self) -> None:
        """The first-run gate neither completes Block A nor changes protected bytes."""

        scaffold = (ROOT / "docs/publication_pilot1_sample_input_freeze.md").read_text(encoding="utf-8")
        self.assertIn("**Status:** candidate; not yet frozen", scaffold)
        self.assertIn("**Document version:** 0.2.6", scaffold)
        self.assertEqual(hashlib.sha256(INVENTORY.read_bytes()).hexdigest(), block_a.INVENTORY_HASH)
        self.assertEqual(hashlib.sha256(PROFILE.read_bytes()).hexdigest(), block_a.TARGET_PROFILE_HASH)


if __name__ == "__main__":
    unittest.main()
