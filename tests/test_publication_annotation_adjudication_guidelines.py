"""Static semantic tests for the frozen Publication annotation guideline.

These tests protect methodological boundaries without freezing a full-document snapshot
or claiming that annotation software, gold data, or evaluation metrics exist.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUIDELINE_PATH = PROJECT_ROOT / "docs/publication_annotation_adjudication_guidelines.md"
README_PATH = PROJECT_ROOT / "README.md"
TARGET_PROFILE_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
)


def section(text: str, heading: str, next_heading: str | None = None) -> str:
    """Return one Markdown section delimited by exact level-two headings."""
    body = text.split(heading, maxsplit=1)[1]
    if next_heading is not None:
        body = body.split(next_heading, maxsplit=1)[0]
    return body


def checklist_counts(text: str, heading: str, next_heading: str) -> tuple[int, int]:
    """Return checked and unchecked item counts for one delimited checklist."""
    body = section(text, heading, next_heading)
    return body.count("- [x]"), body.count("- [ ]")


class PublicationAnnotationGuidelineTests(unittest.TestCase):
    """Protect the frozen guideline's Study 2 methodological invariants."""

    @classmethod
    def setUpClass(cls) -> None:
        """Read the complete frozen guideline and README as UTF-8 once."""
        cls.raw = GUIDELINE_PATH.read_bytes()
        cls.text = cls.raw.decode("utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")

    def assertContainsAll(self, *fragments: str) -> None:  # noqa: N802
        """Assert that each semantic anchor occurs in the guideline."""
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.text)

    def test_exists_is_utf8_and_has_initial_freeze_metadata(self) -> None:
        """The reviewed artifact is UTF-8 and records its approved initial freeze."""
        self.assertTrue(GUIDELINE_PATH.is_file())
        self.assertTrue(self.text)
        self.assertIn(
            "**Status:** final and binding for Publication Pilot 1 Study 2 annotation "
            "and adjudication",
            self.text,
        )
        self.assertIn("**Guideline version:** 0.1.1", self.text)
        self.assertIn("**Date frozen:** 2026-07-31", self.text)

    def test_study_boundaries_are_explicit(self) -> None:
        """Only Study 2 work is in scope; Study 3 QA and Study 4 review stay out."""
        self.assertContainsAll(
            "This guideline is limited to **Study 2**",
            "No Study 3 question-answering gold answers",
            "Study 4 expert\nevaluation is also out of scope",
            "KG-RAG retrieval",
            "question-answer benchmark construction",
        )

    def test_gold_standard_and_stratified_nested_sample_are_required(self) -> None:
        """The final benchmark is artifact-stratified and may contain nested units."""
        self.assertContainsAll(
            "ontology-aligned entity-and-relation gold-standard\nbenchmark",
            "final Study 2 benchmark is stratified by artifact family",
            "selected\nartifacts from every source type",
            "Source-unit annotations may be nested within those\nselected artifacts",
            "Annotation is exhaustive only within the source units selected",
            "they become part of the final Study 2 evaluation sample",
        )

    def test_two_review_design_and_reliability_subset_are_distinct(self) -> None:
        """Independent duplication is limited while every benchmark artifact is reviewed twice."""
        self.assertContainsAll(
            "Every artifact included in the final benchmark receives at least two\nhuman reviews",
            "reliability subset receives two fully independent annotations before\nadjudication",
            "one primary annotation plus\nan independent expert second review",
            "Inter-annotator agreement is computed only on the\n"
            "independently annotated reliability subset",
            "This is the only portion that requires full duplicate annotation",
        )

    def test_annotator_qualification_and_training_burden_are_bounded(self) -> None:
        """Relevant domain familiarity is required without full ontology mastery."""
        self.assertContainsAll(
            "Annotators require relevant domain familiarity",
            "hydrology, environmental science,\nwater resources, scientific computing",
            "They do not need to master the full ontology",
            "Model versus Method versus Algorithm versus Tool",
            "Finding versus Conclusion",
            "ResearchProblem versus ResearchGoal",
            "EvaluationMetric versus Parameter",
        )

    def test_ordinary_annotators_receive_derived_materials_not_raw_contracts(self) -> None:
        """Technical authorities are applied by expert roles, not assigned as annotator reading."""
        training = section(self.text, "### Phase A — Training and calibration", "### Phase B")
        for fragment in (
            "concise annotator handbook and calibration materials derived",
            "human-readable categories, examples, boundaries, and uncertainty guidance",
            "not expected to read or master the raw ontology, machine-readable target\n"
            "profile, source-unit contract, or evidence-validation contract",
            "expert adjudicator and annotation custodian are responsible",
            "handbook remains a later implementation artifact",
            "is not created in this guideline\nreview",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, training)

    def test_ordinary_actions_and_responsibility_classes_are_bounded(self) -> None:
        """Humans perform simple semantics while the pipeline supplies technical metadata."""
        roles = section(self.text, "## 21. Annotation-record minimum fields", "## 22.")
        self.assertContainsAll(
            "highlight exact source text",
            "select a human-readable node type",
            "connect already identified nodes using a human-readable relation",
            "mark uncertainty with an optional concise note",
            "human_entered",
            "pipeline_populated",
            "expert_adjudicator_entered",
        )
        self.assertIn("All identifiers, ontology/profile mappings, offsets, hashes", roles)
        self.assertNotIn("optional normalized-label suggestion", roles)

    def test_node_and_relation_work_are_separate_filtered_passes(self) -> None:
        """Annotators see routed human labels in node-first and relation-second passes."""
        self.assertContainsAll(
            "## 9. Two-pass human workflow",
            "Pass 1\n    Highlight exact source text and classify supported nodes",
            "Pass 2\n    Connect identified nodes or exact deterministic endpoints",
            "filtered by routed\neligible targets, section context, endpoint types, "
            "allowed domain/range",
            "does not present all 46 node targets and 27 relation targets simultaneously",
        )

    def test_exhaustive_absence_is_not_semantic_abstention(self) -> None:
        """An exhaustive zero count is recorded as absence, not annotator abstention."""
        coverage = section(self.text, "### 8.1 `extract_and_evaluate`", "### 8.2")
        self.assertIn(
            "If exhaustive review finds no positive instance for an eligible target, "
            "record the target\nas absent rather than as a semantic abstention.",
            coverage,
        )

    def test_gold_is_blinded_frozen_and_amendments_are_auditable(self) -> None:
        """Gold precedes model exposure and later corrections preserve version history."""
        self.assertContainsAll(
            "independent gold annotation\n-> gold adjudication\n-> initial gold freeze",
            "Gold annotators must not see",
            "model prompts",
            "validator findings for model candidates",
            "a new gold version and hash",
            "recomputation of all affected metrics",
            "performance against the initially frozen gold",
        )

    def test_validation_evidence_and_normalization_boundaries_are_preserved(self) -> None:
        """Automatic checks, human acceptance, edge evidence, and normalization stay separate."""
        self.assertContainsAll(
            "is not automatically accepted as\nscientifically correct",
            "Each non-derived\ngold edge requires evidence for the relation semantics",
            "zero-based half-open offsets measured in Unicode code points",
            "Node evidence does not automatically support an edge",
            "Normalization review is field-local and independent of candidate acceptance",
            "Ordinary annotators are not asked to normalize labels",
        )

    def test_evaluation_metrics_and_later_audits_remain_deferred(self) -> None:
        """The gold preserves inputs while later contracts own metrics and graph audits."""
        self.assertContainsAll(
            "Precision, Recall, F1, and entity/relation matching rules and formulas",
            "Information density and relational richness remain the two approved",
            "requires a later alignment/consolidation reference sample or\nhuman audit",
            "Study 2\nchain-level fact-recoverability evaluation",
            "This guideline does not define\nfact-recoverability scoring",
        )

    def test_resolves_direction_is_derived_from_the_frozen_target_profile(self) -> None:
        """Fact-recoverability examples follow the profile's operational direction."""
        profile = yaml.safe_load(TARGET_PROFILE_PATH.read_text(encoding="utf-8"))
        target = next(
            row
            for row in profile["relation_targets"]
            if row["operational_id"] == "PUB-R-C-P06-RESOLVES"
        )
        signature = target["operational_signatures"][0]
        domains = " / ".join(signature["domain"]["classes"])
        ranges = signature["range"]["classes"]
        self.assertEqual(len(ranges), 1)
        authoritative_direction = f"{domains} -> resolves -> {ranges[0]}"

        fact_section = section(self.text, "### 23.2 Semantic depth", "### 23.3")
        self.assertIn(authoritative_direction, fact_section)
        self.assertIn(
            "ResearchProblem <- resolves - Method -> produces -> Finding", fact_section
        )
        self.assertIn("Method / Experiment -> produces -> Finding", fact_section)
        self.assertNotIn("ResearchProblem -> resolves -> Method", self.text)

    def test_other_artifact_families_use_concise_annexes(self) -> None:
        """The core is reusable without forcing equal volume or complete rewrites."""
        annex = section(self.text, "## 24. Reuse across other Study 2 artifact families", "## 25.")
        for fragment in (
            "source-unit differences", "visible\n   categories", "eligible relations",
            "source-specific evidence boundaries", "artifact-specific\n   calibration examples",
            "artifact-specific reliability sample", "not rewritten from zero",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, annex)

    def test_stopping_rule_allows_only_one_controlled_revision_cycle(self) -> None:
        """The pilot cannot become an open-ended annotation refinement loop."""
        stopping = section(self.text, "## 25. Study 2 stopping rule", "## 26.")
        self.assertIn("one controlled revision cycle", stopping)
        self.assertIn("prohibits an open-ended annotation or protocol-refinement loop", stopping)
        self.assertIn("forthcoming evaluation-matching contract", stopping)

    def test_heading_and_checklist_counts_are_intentional(self) -> None:
        """Sequential headings and both gates retain their reviewed freeze states."""
        level_two = re.findall(r"^## (\d+)\. ", self.text, flags=re.MULTILINE)
        self.assertEqual([int(value) for value in level_two], list(range(1, 29)))
        self.assertEqual(len(re.findall(r"^### ", self.text, flags=re.MULTILINE)), 40)
        freeze = checklist_counts(self.text, "## 26. Contract-freeze gate", "## 27.")
        execution = checklist_counts(
            self.text, "## 27. Annotation-execution acceptance gate", "## 28."
        )
        self.assertEqual(freeze, (19, 0))
        self.assertEqual(execution, (0, 11))

    def test_no_production_implementation_is_claimed(self) -> None:
        """Guideline freeze does not imply annotation execution or software completion."""
        self.assertContainsAll(
            "does not define automatic validation",
            "production implementation",
            "Interface design and implementation remain later work",
            "may be implemented later",
        )

    def test_readme_reports_freeze_without_execution_or_gold_claims(self) -> None:
        """Active README status records the freeze while leaving later work incomplete."""
        guideline_link = (
            "[Publication Pilot 1 annotation and adjudication guidelines]"
            "(docs/publication_annotation_adjudication_guidelines.md)"
        )
        self.assertIn(guideline_link, self.readme)
        self.assertNotIn(f"{guideline_link} — candidate; not frozen", self.readme)
        self.assertIn(
            "| Publication Pilot 1 annotation and adjudication guidelines | "
            "Complete and frozen |",
            self.readme,
        )
        self.assertIn("annotator handbook has not yet been created", self.readme)
        self.assertIn("model/reproducibility policy are not yet frozen", self.readme)
        self.assertIn("Annotation execution and gold construction have not occurred", self.readme)
        self.assertIn(
            "- [ ] Execute human annotation, adjudication, and gold construction",
            self.readme,
        )


if __name__ == "__main__":
    unittest.main()
