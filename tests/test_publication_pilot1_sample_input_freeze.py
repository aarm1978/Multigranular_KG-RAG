"""Static tests for the candidate Publication Pilot 1 sample/input scaffold.

These checks protect the materialized population and methodological boundaries without
selecting the sample, creating gold, inspecting model output, or freezing the record.
"""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = PROJECT_ROOT / "docs/publication_pilot1_sample_input_freeze.md"
MATCHING_PATH = PROJECT_ROOT / "docs/publication_evaluation_matching_contract.md"
README_PATH = PROJECT_ROOT / "README.md"

ARTIFACT_IDS = [
    "10", "15", "16", "18", "34", "37", "46", "54", "79", "276", "87",
    "87-corrigendum",
]

FROZEN_HASHES = {
    "src/ontology/ciroh_ontology.owl": "ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57",
    "src/extraction/llm/publications/publication_target_inventory.yaml": "3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760",
    "docs/publication_source_unit_contract.md": "31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a",
    "schemas/publication_candidate_output.schema.json": "affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d",
    "docs/publication_evidence_validation_contract.md": "3529484f74f9c482bd38c68c9bafbc08723e6dfd960e3c8d5faa70e1b6d28ce2",
    "docs/publication_annotation_adjudication_guidelines.md": "67d693edf8e42318a763aac58190675c90b944440dc12fce164212cf9552bd60",
    "docs/publication_evaluation_matching_contract.md": "10f8dca24bf41acfb21f8d20c5cda7b022392040446a2e2e4bac137365c076d0",
}


class PublicationPilot1SampleInputFreezeTests(unittest.TestCase):
    """Protect the reviewed candidate scaffold and its unfrozen boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the complete UTF-8 documents used by these checks."""
        cls.raw = SAMPLE_PATH.read_bytes()
        cls.text = cls.raw.decode("utf-8")
        cls.matching = MATCHING_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def assert_contains_all(self, *fragments: str) -> None:
        """Assert that every required semantic anchor occurs in the scaffold."""
        normalized_text = re.sub(r"\s+", " ", self.text)
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                normalized_fragment = re.sub(r"\s+", " ", fragment)
                self.assertIn(normalized_fragment, normalized_text)

    def test_document_exists_utf8_and_remains_candidate(self) -> None:
        """The reviewed record exists but is neither final nor frozen."""
        self.assertTrue(SAMPLE_PATH.is_file())
        self.assertTrue(self.raw)
        self.assertIn("**Status:** candidate; not yet frozen", self.text)
        self.assertIn("**Document version:** 0.2.6", self.text)
        self.assertNotIn("**Status:** final and binding", self.text)

    def test_matching_contract_is_final_binding_predecessor(self) -> None:
        """The predecessor gate remains satisfied at the exact frozen version."""
        self.assertIn("**Status:** final and binding", self.matching)
        self.assertIn("**Contract version:** 0.1.0", self.matching)
        self.assertIn("**Date frozen:** 2026-07-31", self.matching)
        self.assertIn("The preceding matching contract is final and binding", self.text)

    def test_fixed_pool_contains_each_artifact_once(self) -> None:
        """The fixed-pool code block has exactly the twelve authorized IDs."""
        block = self.text.split("## 5. Fixed artifact pool", 1)[1].split("```text", 1)[1].split("```", 1)[0]
        values = [line.strip() for line in block.splitlines() if line.strip()]
        self.assertEqual(values, ARTIFACT_IDS)
        self.assertEqual(len(values), len(set(values)))
        self.assertIn("eleven primary-publication records", self.text)
        self.assertIn("Artifact `15`, the off-domain but deliberately curated member", self.text)

    def test_corrigendum_does_not_reopen_deterministic_corrects(self) -> None:
        """The pair is retained without recreating deterministic correction semantics."""
        self.assert_contains_all(
            "deterministic `corrects` relation",
            "must not be recreated as a semantic candidate",
            "never reopens deterministic `corrects`",
        )

    def test_population_and_four_partitions_are_distinct(self) -> None:
        """Population, scored sample, and unit-level partitions are operationally distinct."""
        self.assert_contains_all(
            "pilot population", "evaluation sample", "calibration set",
            "reliability subset", "remaining evaluation set", "reserved diagnostic set",
            "mutually exclusive at source-unit level", "exactly one partition",
        )

    def test_no_selected_units_or_sample_size_are_invented(self) -> None:
        """Population materialization does not invent the selected evaluation sample."""
        self.assertIsNone(re.search(r"pub:[^\s:]+:sec:\d{4}:unit:\d{4}", self.text))
        self.assertIn("Exact sample sizes are intentionally not frozen", self.text)
        self.assertIn("The complete population source-unit IDs are materialized", self.text)
        self.assertIn("Exact selected sample unit IDs\nremain pending blinded screening and sample selection", self.text)
        self.assertNotRegex(self.text, r"(?mi)^exactSampleSize\s*:")

    def test_support_is_prospective_and_insufficient_support_is_preserved(self) -> None:
        """Screening cannot guarantee future gold-dependent support."""
        self.assert_contains_all(
            "support objectives from the matching contract, not guaranteed positive counts",
            "`INSUFFICIENT_SUPPORT`", "not realized support",
            "does not by itself guarantee any of those realized gold-dependent denominators",
        )

    def test_model_output_cannot_influence_selection_or_screening(self) -> None:
        """The sample is selected without model- or validator-result leakage."""
        self.assert_contains_all(
            "without access to model outputs", "model predictions", "model confidence",
            "candidate-validator results", "model-result-driven resampling",
        )

    def test_screening_is_versioned_and_distinct_from_gold(self) -> None:
        """Expert screening is explicit and cannot become hidden gold annotation."""
        self.assert_contains_all(
            "Versioned source-unit screening", "screeningReviewerID", "screeningVersion",
            "screeningStatus", "screeningRationale", "likelyReportingFamilies",
            "likelySamplingStrata",
            "sourceConversionStatus", "it is not gold annotation",
        )

    def test_completeness_is_prospective_and_monitor_promotion_is_preannotation(self) -> None:
        """Absence scoring is authorized only by frozen unit-target completeness."""
        self.assert_contains_all(
            "selected-unit/operational-target level", "exhaustive",
            "non_exhaustive_monitor", "not_applicable",
            "promoted to\n`exhaustive` before annotation begins",
            "missing annotations never imply\ncompleteness",
        )

    def test_calibration_reliability_second_review_and_diagnostics_are_guarded(self) -> None:
        """All human-review and diagnostic roles remain non-contaminating."""
        self.assert_contains_all(
            "Calibration units never\nenter primary metrics",
            "blind, independent, and completed before adjudication",
            "The second review is not counted", "primary record is never silently rewritten",
            "diagnostic units can never migrate", "Diagnostic results must not be merged",
        )

    def test_deterministic_context_is_exact_role_visible_and_name_safe(self) -> None:
        """Endpoint context is exact, role-scoped, symmetric when scored, and prediction-free."""
        self.assert_contains_all(
            "deterministicEndpointID", "endpointClass", "endpointProvenance",
            "visibilityRoles", "requiredForLinkExisting", "deferredRecordID",
            "readOnlyCitationOrCorrigendumContext", "supplied\nsymmetrically",
            "Name-only similarity does not authorize an exact endpoint",
            "Context may never contain model\npredictions",
        )

    def test_evidence_group_capability_precedes_future_gold_groups(self) -> None:
        """The sample freezes interface capability, not unknowable gold group modes."""
        self.assert_contains_all(
            "evidenceGroupCapabilityRequired", "`jointly_required`", "`alternatives`",
            "Actual `goldEvidenceGroups`", "created only during blinded annotation",
            "candidate-output schema\nis unchanged",
        )
        self.assertNotIn("goldEvidenceGroupMode", self.text)

    def test_sample_precedes_model_policy_and_later_manifest_binds_hashes(self) -> None:
        """The immutable sample is bound to model and prompt policy only later."""
        self.assert_contains_all(
            "sample and input freeze\n→ model/reproducibility policy",
            "sampleFreezeVersion", "sampleFreezeHash", "modelPolicyVersion",
            "modelPolicyHash", "promptVersion", "promptHash",
            "does not require or permit modification",
        )

    def test_named_assignments_are_deferred_but_assignment_policy_is_required(self) -> None:
        """Sample freeze owns policy while the execution manifest owns people."""
        self.assert_contains_all(
            "does not require named annotator\nassignments",
            "Named or pseudonymous IDs and\nexact assignments belong exclusively",
            "annotatorAssignmentPolicy", "annotation_assignment_manifest.json",
        )

    def test_required_manifests_mappings_and_hashes_are_explicit(self) -> None:
        """Population, selection, coverage, family roles, and hashes are separately frozen."""
        self.assert_contains_all(
            "publication_pilot1_source_unit_inventory.jsonl",
            "publication_pilot1_source_unit_manifest.json",
            "publication_pilot1_target_coverage_matrix.csv",
            "publication_pilot1_sample_selection_manifest.json",
            "publication_pilot1_target_family_mapping.yaml",
            "SHA-256 of each",
        )

    def test_reporting_families_decision_roles_and_sampling_strata_are_distinct(self) -> None:
        """Reporting, decisions, and optional sample balancing have separate authority."""
        self.assert_contains_all(
            "Reporting families, decision roles, and sampling strata",
            "reportingFamily", "decisionRole", "samplingStratum",
            "Controls reporting and family-level interpretation",
            "Controls blocking, monitoring, deferred, or excluded treatment",
            "Supports practical sample balancing only and has no direct metric or decision authority",
        )

    def test_reporting_family_vocabulary_is_exactly_the_frozen_ten(self) -> None:
        """The scaffold uses the matching contract's ten families and no eleventh."""
        expected = [
            "research_framing",
            "discourse_structure",
            "methods_and_experiments",
            "models_algorithms_and_tools",
            "findings_conclusions_limitations_and_future_work",
            "metrics_parameters_and_variables",
            "datasets_and_repositories",
            "concepts_and_geography",
            "discourse_relations",
            "use_mention_reference_relations",
        ]
        section = self.text.split("#### 12.1.1 Frozen reporting families", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
        values = [line.strip() for line in block.splitlines() if line.strip()]
        self.assertEqual(values, expected)
        self.assertIn("No eleventh reporting family is\nauthorized", section)

    def test_decision_roles_are_exact_and_descriptive_is_behavior(self) -> None:
        """Descriptive reporting does not become a mutually exclusive target role."""
        section = self.text.split("#### 12.1.2 Decision roles", 1)[1]
        block = section.split("```text", 1)[1].split("```", 1)[0]
        values = [line.strip() for line in block.splitlines() if line.strip()]
        self.assertEqual(
            values,
            ["blocking", "monitored", "deferred_resolution_only", "excluded_or_follow_on"],
        )
        self.assertNotIn("descriptive", values)
        self.assert_contains_all(
            "Descriptive reporting is an evaluation behavior",
            "It is not an exclusive target-level `decisionRole`",
        )

    def test_five_broad_groups_are_sampling_strata_only(self) -> None:
        """The audit's broad groups can balance selection but cannot control metrics."""
        self.assert_contains_all(
            "retained only as\noptional `samplingStratum` values",
            "core_discourse_nodes", "scientific_entity_nodes",
            "core_discourse_relations", "entity_role_and_study_context_relations",
            "measurement_context_relations",
            "do not replace reporting families",
            "govern the frozen family-level\nF1 floor",
            "hide weak performance in a\nfrozen reporting family",
        )

    def test_mapping_requires_every_profile_target_exactly_once(self) -> None:
        """The future mapping is total and one-to-one over frozen operational IDs."""
        self.assert_contains_all(
            "validated against every current operational ID",
            "both `node_targets` and `relation_targets`",
            "Every\noperational target appears exactly once",
            "exactly one valid `decisionRole`",
            "Validation fails for a missing,\nduplicate, or unknown operational ID",
        )

    def test_reporting_family_is_conditional_on_decision_role(self) -> None:
        """Only primary and monitored targets receive a frozen reporting family."""
        self.assert_contains_all(
            "For `blocking` and `monitored` targets, `reportingFamily` is required, non-null",
            "contains exactly one authorized value",
            "For `deferred_resolution_only` and\n`excluded_or_follow_on` targets",
            "required to be `null`",
            "no artificial\nreporting-family assignment",
            "For\n`deferred_resolution_only` and `excluded_or_follow_on`, `reportingFamily` is `null`",
        )

    def test_sampling_stratum_remains_optional_and_decision_neutral(self) -> None:
        """Sampling strata remain nullable aids with no metric or decision authority."""
        self.assert_contains_all(
            "`samplingStratum` is optional for every target",
            "contains at most one authorized value or\n`null`",
            "has no metric or decision authority",
        )

    def test_freeze_gate_and_coverage_checklist_are_prospective(self) -> None:
        """Sample freeze certifies design adequacy without claiming realized support."""
        completion = self.text.split("## 27. Candidate-completion checklist", 1)[1].split("## 28.", 1)[0]
        freeze_gate = self.text.split("## 28. Final freeze gate", 1)[1].split("## 29.", 1)[0]
        self.assertIn("prospective target and reporting-family coverage is verified", completion)
        self.assertNotIn("target coverage is verified", completion)
        self.assertIn("prospectively designed to support the approved metrics", freeze_gate)
        self.assertIn("blinded screening, frozen coverage objectives", freeze_gate)
        self.assertIn("prospectively sufficient to attempt the approved IAA", freeze_gate)
        self.assertIn("without guaranteeing realized gold-dependent denominators", freeze_gate)
        self.assertNotIn("the selected sample supports the approved metrics", freeze_gate)
        self.assertNotIn("the reliability subset supports the approved IAA", freeze_gate)

    def test_realized_support_is_handled_only_after_annotation(self) -> None:
        """Realized sufficiency controls interpretation, never frozen-sample replacement."""
        self.assert_contains_all(
            "Realized support is evaluated only after annotation",
            "realized support sufficient",
            "Compute and interpret the corresponding metric under the frozen matching contract",
            "realized support insufficient",
            "Report INSUFFICIENT_SUPPORT",
            "Do not replace frozen units",
            "Do not add units after model exposure",
            "Do not reinterpret screening expectations as gold",
            "certifies prospective design adequacy only",
            "does not certify realized\ngold counts",
        )

    def test_every_artifact_requires_primary_evaluation_representation(self) -> None:
        """Calibration or diagnostics alone cannot represent a fixed artifact."""
        self.assert_contains_all(
            "Every artifact in the fixed twelve-artifact pool must contribute at least one eligible source unit",
            "either the `reliability` or `remaining_evaluation` partition",
            "Calibration and `reserved_diagnostic` units",
            "do not\nsatisfy this primary-evaluation representation requirement",
            "primaryEvaluationRepresentationSatisfied",
            "An artifact need not contribute to both primary partitions",
        )

    def test_exhaustive_empty_cases_are_established_only_after_review(self) -> None:
        """Screening proposes likely empty cases but never certifies semantic absence."""
        self.assert_contains_all(
            "Screening does not certify semantic absence",
            "likelyExhaustiveEmptyTargetIDs",
            "becomes an exhaustive-empty case only after",
            "independent annotation and review process establishes zero supported instances",
            "expected empty case that is not realized remains in the frozen reliability subset",
            "the unit is not replaced",
            "screening is not\nreinterpreted as gold",
        )

    def test_calibration_partition_vocabulary_is_normalized(self) -> None:
        """Calibration is a permanent partition, never an exclusion or eligibility state."""
        forbidden = "calibration" + "_only"
        self.assertNotIn(forbidden, self.text)
        self.assert_contains_all(
            "partition: calibration | reliability | remaining_evaluation | reserved_diagnostic | null",
            "partitioned explicitly as `calibration`",
            "excluded from primary extraction metrics",
            "may be discussed jointly",
            "does not move the unit out of the frozen calibration partition",
        )

    def test_diagnostic_annotations_are_separate_debugging_records(self) -> None:
        """Authorized diagnostic annotation cannot contaminate primary gold or metrics."""
        self.assert_contains_all(
            "separately versioned diagnostic annotation and expert review",
            "support debugging only",
            "never enter the primary gold, primary evaluation sample, or\nprimary metrics",
            "Diagnostic annotations remain separate",
            "diagnostic labels cannot retroactively alter primary gold",
            "cannot migrate into the primary evaluation sample",
        )

    def test_upstream_frozen_hashes_remain_exact(self) -> None:
        """No frozen authority changed during the downstream audit."""
        for relative_path, expected in FROZEN_HASHES.items():
            with self.subTest(path=relative_path):
                raw = (PROJECT_ROOT / relative_path).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
                self.assertIn(expected, self.text)

    def test_final_freeze_gate_remains_unchecked_and_execution_unclaimed(self) -> None:
        """The audit does not claim materialization, annotation, gold, or model execution."""
        final_gate = self.text.split("## 28. Final freeze gate", 1)[1].split("## 29.", 1)[0]
        self.assertNotIn("- [x]", final_gate)
        self.assert_contains_all(
            "[x] canonical source units are materialized", "[ ] exact source-unit IDs are selected",
            "Until that gate passes", "candidate scaffold",
        )

    def test_readme_status_remains_candidate_not_frozen(self) -> None:
        """README discoverability reports review readiness without claiming freeze."""
        self.assertIn(
            "Publication Pilot 1 sample and input freeze record | Candidate; not frozen",
            self.readme,
        )
        self.assertIn("population materialized, screening and selection not started", self.readme)


if __name__ == "__main__":
    unittest.main()
