"""Static semantic tests for the frozen Publication evaluation matching contract.

These checks protect methodological invariants without implementing matching, creating
gold annotations, selecting source units, executing the pilot, or freezing the candidate
sample document. The ignored generated Publication Phase B graph is protected, when
materialized, by its dedicated Phase B and frozen-snapshot tests rather than by this
portable static contract suite.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "docs/publication_evaluation_matching_contract.md"
SAMPLE_PATH = PROJECT_ROOT / "docs/publication_pilot1_sample_input_freeze.md"
PROFILE_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
)
SCHEMA_PATH = PROJECT_ROOT / "schemas/publication_candidate_output.schema.json"
GUIDELINE_PATH = (
    PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines.md"
)
PHASE_B_METRICS_MANIFEST_PATH = (
    PROJECT_ROOT
    / "results/metrics/snapshots/hydroshare_github_hub_publications_deterministic.json"
)
PHASE_B_LOCAL_GRAPH_PATH = "data/interim/papers/publication_nodes_edges.json"
PHASE_B_EXPECTED_SHA256 = (
    "675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf"
)
MATCHING_CONTRACT_EXPECTED_SHA256 = (
    "47fff44da3d3c2643b5e8c86930b0e0f09410c160869ac1f1d4f6d3a4a7ad177"
)

FROZEN_HASHES = {
    "src/ontology/ciroh_ontology.owl": (
        "7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635"
    ),
    "src/extraction/llm/publications/publication_target_inventory.yaml": (
        "6401c15b861c2362b67e03d56acd4a7304964f595d706311fd4f149eb69b3a5e"
    ),
    "docs/publication_source_unit_contract.md": (
        "8132be14b06153957697310ec8df16a07e72462ce7a98ae46b8d4f26aa188172"
    ),
    "schemas/publication_candidate_output.schema.json": (
        "50132ce01a16a21736f65e4b5d4b0354b3d1c53f07878352159d6ff36e94fce2"
    ),
    "docs/publication_evidence_validation_contract.md": (
        "61b2606e08849f9b04d04e20b20ac04e6d972e3cd04df81d29dfdd3df16c32b5"
    ),
    "docs/publication_annotation_adjudication_guidelines.md": (
        "1553e633022de2579cfa1866c33b1cfda8b4972103141b19cbc0c7241b6d9f27"
    ),
}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load one UTF-8 YAML mapping."""
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected mapping at {path}")
    return value


def markdown_section(text: str, heading: str, next_heading: str | None = None) -> str:
    """Return text after one exact Markdown heading and before an optional next heading."""
    body = text.split(heading, maxsplit=1)[1]
    return body if next_heading is None else body.split(next_heading, maxsplit=1)[0]


class PublicationEvaluationMatchingContractTests(unittest.TestCase):
    """Protect the frozen contract's reviewed methodological boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load complete UTF-8 authorities used by the focused checks."""
        cls.raw = CONTRACT_PATH.read_bytes()
        cls.text = cls.raw.decode("utf-8")
        cls.sample = SAMPLE_PATH.read_text(encoding="utf-8")
        cls.profile = load_yaml(PROFILE_PATH)
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.guideline = GUIDELINE_PATH.read_text(encoding="utf-8")
        cls.phase_b_metrics_manifest = json.loads(
            PHASE_B_METRICS_MANIFEST_PATH.read_text(encoding="utf-8")
        )

    def assert_contains_all(self, *fragments: str) -> None:
        """Assert that every semantic anchor occurs in the frozen contract."""
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.text)

    def test_exists_utf8_final_binding_version_and_date(self) -> None:
        """The document is readable and frozen as final version 0.1.1."""
        self.assertTrue(CONTRACT_PATH.is_file())
        self.assertTrue(self.raw)
        self.assertIn(
            "**Status:** final and binding for Publication Pilot 1 evaluation matching "
            "and decision thresholds",
            self.text,
        )
        self.assertIn("**Contract version:** 0.1.2", self.text)
        self.assertIn("**Date frozen:** 2026-07-31", self.text)
        self.assertEqual(
            hashlib.sha256(self.raw).hexdigest(), MATCHING_CONTRACT_EXPECTED_SHA256
        )
        self.assertNotIn(
            "**Status:** candidate for methodological review; not yet frozen", self.text
        )

    def test_study_boundary_is_extraction_only(self) -> None:
        """Study 2 extraction is included while Study 3 and Study 4 remain excluded."""
        self.assert_contains_all(
            "Study 2 extraction evaluation only",
            "Study 3 question answering",
            "Study 4 expert evaluation is also out of scope",
            "does not test whether the final KG improves question answering",
        )

    def test_evaluated_system_boundary_has_all_lifecycle_states(self) -> None:
        """Raw, parsed, validated, usable, and adjudicated states are explicit."""
        self.assert_contains_all(
            "raw_response",
            "parsed_candidate_document",
            "parsed_candidate",
            "automatically_validated_candidate",
            "usable_pipeline_output",
            "human_adjudicated_candidate",
            "Primary end-to-end extraction metrics",
        )
        self.assertEqual(self.schema["properties"]["outputStage"]["const"], "parsed_candidate")

    def test_raw_and_usable_views_are_distinct_and_mandatory(self) -> None:
        """Validation cannot conceal model behavior or promote rejected records."""
        self.assert_contains_all(
            "mandatory raw parsed-output view",
            "before automatic filtering",
            "not usable output",
            "prevents automatic validation, duplicate suppression, or\nrole precedence",
            "No raw-view inspection authorizes malformed content to enter usable output",
        )

    def test_parse_and_invalid_candidate_consequences_are_explicit(self) -> None:
        """Failures have request, FP, FN, and denominator consequences."""
        invalid = markdown_section(self.text, "## 18. Invalid and non-validated model output", "## 19.")
        for fragment in (
            "request parse failure",
            "no invented FP",
            "otherwise-unmatched gold positive covered by the failed request is FN exactly once",
            "candidate-document schema failure",
            "candidate-level schema failure",
            "forbidden field",
            "nonliteral evidence",
            "invalid evidence offsets",
            "unknown ontology ID",
            "unknown operational target",
            "invalid domain or range",
            "abstract-class instantiation",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, invalid)

    def test_wrong_semantics_remain_fp_and_fn(self) -> None:
        """Wrong class, relation, direction, and endpoint choices cannot vanish as filtering."""
        self.assert_contains_all(
            "wrong class that is otherwise a valid target",
            "semantic `wrong_class`",
            "wrong relation that is otherwise a valid target",
            "semantic `wrong_relation`",
            "semantic `wrong_direction`",
            "semantic `wrong_endpoint`",
            "FP plus FN",
        )

    def test_evidence_views_thresholds_and_rationale_are_explicit(self) -> None:
        """Exact evidence is strict reporting and tolerant evidence is guarded primary matching."""
        self.assert_contains_all(
            "Exact span match",
            "Boundary-tolerant span match",
            "primary evidence criterion",
            "separate strict reproducibility view",
            "span_F1 >= 0.80",
            "span_precision >= 0.70",
            "span_recall >= 0.70",
            "limits a\ncontaining prediction to at most about 1.43 times the gold length",
            "evidence_set_F1 >= 0.80",
        )

    def test_distributed_evidence_is_unit_keyed_and_edge_specific(self) -> None:
        """Multi-unit evidence never intersects offsets across canonical units."""
        self.assert_contains_all(
            "separately for each canonical\n`sourceUnitID`",
            "coordinate keys `(sourceUnitID, offset)`",
            "jointly_required",
            "alternatives",
            "one predicted span cannot satisfy two jointly required gold spans",
            "Node evidence does not automatically support the edge",
            "union of endpoint-node evidence cannot be substituted for edge evidence",
        )

    def test_node_primary_match_requires_exact_target_and_class(self) -> None:
        """Primary entity metrics use exact target/class equality without partial credit."""
        self.assert_contains_all(
            "same operationalTargetID",
            "same ontology class",
            "Exact operational-target and class equality are mandatory",
            "earns\nno fractional credit",
            "normalized labels do not establish a match",
        )

    def test_relation_match_requires_direction_endpoints_scope_and_evidence(self) -> None:
        """Primary edge matches require the complete directed, grounded assertion."""
        self.assert_contains_all(
            "same operational direction",
            "source endpoint matched to the gold source endpoint",
            "target endpoint matched to the gold target endpoint",
            "valid relation-specific evidence",
            "same sourceArtifactID",
            "exact frozen ID\nequality is required",
        )

    def test_resolves_direction_is_derived_from_frozen_profile(self) -> None:
        """The authoritative resolves direction comes from YAML and the reverse is absent."""
        target = next(
            row
            for row in self.profile["relation_targets"]
            if row["operational_id"] == "PUB-R-C-P06-RESOLVES"
        )
        signature = target["operational_signatures"][0]
        direction = (
            f"{' / '.join(signature['domain']['classes'])} -> resolves -> "
            f"{signature['range']['classes'][0]}"
        )
        self.assertIn(direction, self.text)
        self.assertNotIn("ResearchProblem -> resolves -> Method", self.text)

    def test_one_to_one_assignment_is_deterministic_and_occurrence_safe(self) -> None:
        """Assignment cannot reuse predictions or merge repeated contextual occurrences."""
        self.assert_contains_all(
            "one-to-one bipartite assignment",
            "maximum-cardinality assignment",
            "lexicographically smallest sorted sequence",
            "One prediction cannot satisfy more\nthan one gold record",
            "Pooling never crosses source artifacts or operational targets",
            "Artifact pooling does not erase occurrence identity",
        )

    def test_duplicates_cannot_gain_usable_or_raw_credit(self) -> None:
        """Suppression protects output while the raw duplicate remains an FP."""
        self.assert_contains_all(
            "Extra model candidates that refer to an already matched gold assertion count as false\npositives",
            "every extra model-authored duplicate is FP",
            "duplicate-prediction rate",
            "first eligible record may match; every extra model-authored duplicate is FP",
        )

    def test_monitor_and_empty_gold_rules_are_separate(self) -> None:
        """Monitor absence is unknown and correct empty is not a true negative."""
        self.assert_contains_all(
            "Monitor targets do not determine GO/REVISE/NO-GO",
            "absence of gold is not treated as a confirmed negative",
            "`correct_empty` is not a true negative",
            "FN += 1",
        )

    def test_abstention_reasons_match_frozen_candidate_schema(self) -> None:
        """The evaluation contract does not invent a second abstention vocabulary."""
        expected = set(self.schema["$defs"]["abstention"]["properties"]["reason"]["enum"])
        body = markdown_section(self.text, "### 19.4 Abstention reasons", "## 20.")
        block = body.split("```text", maxsplit=1)[1].split("```", maxsplit=1)[0]
        observed = {line.strip() for line in block.splitlines() if line.strip()}
        self.assertEqual(observed, expected)

    def test_iaa_is_pre_adjudication_independent_and_non_tautological(self) -> None:
        """IAA uses blind duplicate work and pairs detections before comparing labels."""
        self.assert_contains_all(
            "IAA is computed before gold adjudication",
            "independent expert second review",
            "quality\ncontrol, not IAA",
            "ignores\noperational target and class when pairing nodes",
            "ignores operational relation target, relation type, and direction",
            "never\ncomputed on adjudicated gold",
        )
        self.assertIn(
            "Inter-annotator agreement is computed only on the\nindependently annotated reliability subset",
            self.guideline,
        )

    def test_iaa_support_and_required_outputs_are_explicit(self) -> None:
        """Sparse agreement is neither pass nor failure and raw disagreement is retained."""
        self.assert_contains_all(
            "INSUFFICIENT_SUPPORT",
            "neither a pass nor a fail",
            "raw 2×2 table",
            "observed agreement",
            "node-class agreement",
            "relation-type agreement",
            "relation-direction agreement",
            "endpoint agreement",
            "unit-level positive/absent agreement",
        )

    def test_node_relation_micro_macro_and_undefined_metrics_are_explicit(self) -> None:
        """Aggregation is separated, support-aware, and never fabricates values."""
        self.assert_contains_all(
            "node micro Precision / Recall / F1",
            "relation micro Precision / Recall / F1",
            "unweighted macro averages",
            "metric is `undefined`",
            "not silently set to zero or one",
            "list every zero-gold target",
            "support distribution",
        )

    def test_only_three_formal_decisions_and_one_revision_are_allowed(self) -> None:
        """Non-blocking notes remain GO and no second correction cycle is available."""
        decision = markdown_section(self.text, "## 29. Primary pilot decision thresholds", "## 30.")
        self.assertIn("The formal decision vocabulary is exactly", decision)
        vocabulary = decision.split("The formal decision vocabulary is exactly:", 1)[1]
        vocabulary = vocabulary.split("```", 2)[1]
        values = [line for line in vocabulary.splitlines() if line and line != "text"]
        self.assertEqual(values, ["GO", "REVISE", "NO_GO"])
        self.assertIn("formal decision remains `GO`", decision)
        self.assertIn("Only one controlled revision cycle", decision)
        self.assertIn("only formal outcomes are `GO` or `NO_GO`", decision)

    def test_thresholds_have_non_tautological_raw_and_safety_gates(self) -> None:
        """GO combines usable quality with pre-filter compliance and leakage safety."""
        self.assert_contains_all(
            "candidate-level evidence-valid rate >= 0.95",
            "candidate-level ontology-valid rate >= 0.95",
            "candidate-level target-eligible rate >= 0.95",
            "candidate-level domain/range-valid rate >= 0.95",
            "forbidden-field rate == 0.00",
            "usable-output invalid-leakage rate == 0.00",
            "former\ntautological requirements",
            "Precision is set higher than Recall",
        )
        self.assertNotIn("validated-candidate evidence-valid rate == 1.00", self.text)

    def test_systematic_rule_is_cross_artifact_and_strictly_above_five_percent(self) -> None:
        """Ordinary recurrence needs both conditions and does not contradict 95% validity."""
        decision = markdown_section(self.text, "## 29. Primary pilot decision thresholds", "## 30.")
        self.assertIn(
            "at least two instances across at least two source artifacts", decision
        )
        self.assertIn("more than 5% of the applicable raw denominator", decision)
        self.assertIn("Both conditions\nare required", decision)
        self.assertIn("An ordinary failure rate of exactly 5% is therefore not automatically\nsystematic", decision)
        self.assertIn("19 valid cases out of 20", decision)
        self.assertNotIn(
            "at least 5% of its applicable raw denominator, whichever condition is met first",
            decision,
        )

    def test_zero_tolerance_safety_failures_remain_count_independent(self) -> None:
        """A single forbidden field or leakage event still blocks GO."""
        decision = markdown_section(self.text, "## 29. Primary pilot decision thresholds", "## 30.")
        for fragment in (
            "block GO regardless of\ncount",
            "any forbidden-field behavior",
            "any structurally invalid record leaking into usable\noutput",
            "any model-output leakage into sample selection or gold construction",
            "do\nnot use the ordinary `systematic` frequency test",
            "Repeated reversed-direction",
            "abstract-class",
            "evidence-authority",
            "safety failure or methodological contradiction",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, decision)

    def test_fact_recoverability_is_exploratory_and_bounded(self) -> None:
        """Pilot chains are non-blocking and do not claim cross-source completion."""
        fact = markdown_section(self.text, "## 28. Fact-recoverability pilot measure", "## 29.")
        self.assertIn("exploratory", fact)
        self.assertIn("not a GO-blocking metric", fact)
        self.assertIn("Cross-source lineage and code-documentation chains remain later Study 2", fact)

    def test_candidate_adjudication_cannot_improve_primary_metrics(self) -> None:
        """Human edits remain burden analysis rather than corrected model predictions."""
        self.assert_contains_all(
            "Human edits, merges, reclassifications, endpoint corrections, and evidence corrections do\nnot improve",
            "No accepted, edited, linked,\nmerged, split, or otherwise human-adjudicated record replaces",
        )

    def test_contract_review_checklist_is_entirely_checked(self) -> None:
        """Every reviewed contract item is checked at explicit freeze."""
        checklist = markdown_section(self.text, "## 36. Contract-review checklist", "## 37.")
        self.assertGreater(checklist.count("- [x]"), 0)
        self.assertEqual(checklist.count("- [ ]"), 0)

    def test_sample_remains_unfrozen_without_exact_unit_ids(self) -> None:
        """The sample is a support-aware scaffold and contains no materialized unit IDs."""
        self.assertIn("**Status:** candidate; not yet frozen", self.sample)
        self.assertIn("**Document version:** 0.2.8", self.sample)
        self.assertIn(
            "Publication evaluation matching contract version:\n0.1.2", self.sample
        )
        self.assertIn(MATCHING_CONTRACT_EXPECTED_SHA256, self.sample)
        self.assertIn("Exact selected sample unit IDs\nremain pending Gate 0 and final sample selection", self.sample)
        self.assertIn("INSUFFICIENT_SUPPORT", self.sample)
        self.assertNotRegex(self.sample, r"pub:[^\s`]+:sec:\d{4}:unit:\d{4}")

    def test_sample_freezes_before_later_model_policy_binding(self) -> None:
        """The sample stays immutable while a later run manifest binds policy and prompt."""
        completion = markdown_section(
            self.sample, "## 27. Candidate-completion checklist", "## 28."
        )
        freeze_gate = markdown_section(self.sample, "## 28. Final freeze gate", "## 29.")
        self.assertNotIn("model-policy version and hash are recorded", completion)
        self.assertNotIn("modelPolicyHash", completion)
        self.assertNotIn("modelPolicyHash", freeze_gate)
        for fragment in (
            "The sample record remains immutable after its own freeze",
            "model/reproducibility policy\nis frozen separately and later",
            "Before model\nexecution, the run or evaluation manifest binds",
            "sampleFreezeVersion",
            "sampleFreezeHash",
            "modelPolicyVersion",
            "modelPolicyHash",
            "promptVersion",
            "promptHash",
            "does not require or permit modification of the\nalready frozen sample document",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.sample)

    def test_no_implementation_or_completed_gold_is_claimed(self) -> None:
        """Static method work claims no implementation, selection, gold, or execution."""
        self.assert_contains_all(
            "select the exact source-unit sample or execute Publication Pilot 1",
            "implement the source-unit builder, parser, validator, or extractor",
            "perform human annotation",
            "create gold data",
        )
        self.assertIn("source-unit builder must complete successfully before", self.sample)
        self.assertIn("Exact selected sample unit IDs\nremain pending Gate 0 and final sample selection", self.sample)
        self.assertIn("Exact sample sizes are intentionally not frozen", self.sample)
        self.assertIn("Before model execution", self.sample)

    def test_local_phase_b_graph_is_not_a_portability_requirement(self) -> None:
        """The focused suite checks a tracked manifest, never the ignored graph's presence."""
        self.assertNotIn(PHASE_B_LOCAL_GRAPH_PATH, FROZEN_HASHES)
        components = self.phase_b_metrics_manifest["input"]["cumulativeProvenance"][
            "components"
        ]
        publication = next(row for row in components if row["label"] == "publications")
        self.assertEqual(publication["path"], PHASE_B_LOCAL_GRAPH_PATH)
        self.assertEqual(publication["sha256"], PHASE_B_EXPECTED_SHA256)
        self.assertIn(PHASE_B_EXPECTED_SHA256, self.text)

    def test_frozen_upstream_hashes_are_unchanged(self) -> None:
        """Every version-controlled frozen authority matches its reviewed bytes."""
        for relative_path, expected in FROZEN_HASHES.items():
            path = PROJECT_ROOT / relative_path
            with self.subTest(path=relative_path):
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
                self.assertIn(expected, self.text)


if __name__ == "__main__":
    unittest.main()
