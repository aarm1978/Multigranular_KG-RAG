"""Static integration tests for the Publication Pilot 1 contract artifacts.

These tests do not implement extraction or source-unit construction. They check
that the binding machine-readable target inventory remains within the frozen
ontology and human-approved Pilot 1 scope, and that the source-unit contract
retains its methodological invariants.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
import unittest
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
TARGET_PROFILE_PATH = (
    PROJECT_ROOT / "src/extraction/llm/publications/publication_target_inventory.yaml"
)
TARGET_INVENTORY_PATH = PROJECT_ROOT / "docs/publication_llm_extraction_target_inventory.md"
SOURCE_UNIT_CONTRACT_PATH = PROJECT_ROOT / "docs/publication_source_unit_contract.md"
PHASE_A_CORPUS_PATH = PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json"

EXPECTED_SAMPLE_IDS = (
    "10", "15", "16", "18", "34", "37", "46", "54", "79", "276", "87",
    "87-corrigendum",
)
EXPECTED_TREATMENT_COUNTS = {
    "node_targets": {
        "context_only": 9,
        "deferred_resolution": 2,
        "extract_and_evaluate": 19,
        "extract_and_monitor": 21,
        "out_of_scope": 5,
        "required_infrastructure": 5,
    },
    "relation_targets": {
        "context_only": 8,
        "deferred_resolution": 1,
        "extract_and_evaluate": 16,
        "extract_and_monitor": 10,
        "out_of_scope": 3,
        "required_infrastructure": 5,
        "separate_follow_on_protocol": 1,
    },
}
EXPECTED_AUTHORITY_ORDER = [
    "frozen ontology 0.1.3 specification and generated OWL",
    "frozen deterministic Phase B outputs and tests",
    "final Publication Pilot 1 human-readable target inventory",
    "publication ontology observations register",
    "LLM extraction decision record",
    "this machine-readable profile",
    "source-unit contract",
]
BUILTIN_OR_PROFILE_TYPES = {"AcceptedAssertion", "owl:Thing", "prov:Activity"}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load one UTF-8 YAML mapping."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"Expected a YAML mapping at {path}")
    return loaded


def target_rows(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all operational node and relation rows in declared order."""
    return [*profile["node_targets"], *profile["relation_targets"]]


def load_phase_a_corpus(path: Path) -> dict[str, Any]:
    """Load the local Phase A corpus or skip when generated data is unavailable."""
    if not path.is_file():
        raise unittest.SkipTest(
            "local generated Publication Phase A corpus is unavailable in this environment"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_inventory_counts(text: str) -> dict[str, dict[str, int]]:
    """Parse the treatment-count tables from the binding Markdown inventory."""
    result: dict[str, dict[str, int]] = {}
    for heading, key in (
        ("### 6.1 Node operational rows by treatment", "node_targets"),
        ("### 6.2 Relation operational rows by treatment", "relation_targets"),
    ):
        section = text.split(heading, maxsplit=1)[1].split("###", maxsplit=1)[0]
        rows = re.findall(r"^\| ([a-z_]+) \| (\d+) \|$", section, flags=re.MULTILINE)
        result[key] = {treatment: int(count) for treatment, count in rows}
    return result


class PublicationTargetInventoryTests(unittest.TestCase):
    """Validate the executable Publication Pilot 1 target profile."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the frozen ontology and binding profile once."""
        cls.ontology = load_yaml(ONTOLOGY_PATH)
        cls.profile = load_yaml(TARGET_PROFILE_PATH)
        cls.classes_by_id = {item["id"]: item for item in cls.ontology["classes"]}
        cls.relations_by_id = {item["id"]: item for item in cls.ontology["relations"]}
        cls.classes_by_name = {item["name"]: item for item in cls.ontology["classes"]}

    def _ancestors(self, class_name: str) -> set[str]:
        """Return ontology class names above a named class."""
        ancestors: set[str] = set()
        current = self.classes_by_name.get(class_name)
        while current and current.get("parent"):
            parent_local_name = str(current["parent"]).split(":", maxsplit=1)[-1]
            ancestors.add(parent_local_name)
            current = self.classes_by_name.get(parent_local_name)
        return ancestors

    def test_profile_parses_and_operational_ids_are_unique(self) -> None:
        """The YAML is a mapping and every operational row has one unique ID."""
        self.assertEqual(self.profile["status"], "final_and_binding")
        operational_ids = [row["operational_id"] for row in target_rows(self.profile)]
        self.assertEqual(len(operational_ids), len(set(operational_ids)))

    def test_authority_order_matches_the_binding_integration_order(self) -> None:
        """The executable profile records every audit authority in binding order."""
        self.assertEqual(self.profile["authority_order"], EXPECTED_AUTHORITY_ORDER)

    def test_publication_funded_by_is_only_paper_to_award(self) -> None:
        """Publication Pilot 1 does not invent an Award-to-Organization signature."""
        target = next(
            row
            for row in self.profile["relation_targets"]
            if row["operational_id"] == "PUB-R-A-AG-R2-FUNDEDBY"
        )
        self.assertEqual(target["raw_operational_signature"], "Paper → Award")
        self.assertEqual(
            target["operational_signatures"],
            [{
                "domain": {"classes": ["Paper"], "match": "exact"},
                "range": {"classes": ["Award"], "match": "exact"},
            }],
        )
        self.assertEqual(target["production_responsibility"], "deterministic")
        self.assertEqual(target["pilot_treatment"], "out_of_scope")
        self.assertEqual(target["emission_mode"], "not_emitted")
        self.assertEqual(target["evaluation_mode"], "not_attempted")
        self.assertIn("not formally declared in ontology 0.1.3", target["boundary"])
        self.assertNotIn("Award → Organization", TARGET_INVENTORY_PATH.read_text(encoding="utf-8"))

    def test_reviewed_source_hashes_match_repository_bytes(self) -> None:
        """Pinned reviewed-source hashes identify the files actually under review."""
        for source in self.profile["reviewed_sources"]:
            path = PROJECT_ROOT / source["path"]
            with self.subTest(path=source["path"]):
                self.assertTrue(path.is_file())
                actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(actual_hash, source["sha256"])

    def test_all_ontology_ids_and_formal_declarations_exist(self) -> None:
        """Operational rows reference only frozen classes and relations."""
        known_ids = set(self.classes_by_id) | set(self.relations_by_id)
        for target in self.profile["node_targets"]:
            with self.subTest(target=target["operational_id"]):
                self.assertTrue(set(target["ontology_ids"]) <= known_ids)
                self.assertEqual(
                    {entry["id"] for entry in target["formal_classes"]},
                    set(target["ontology_ids"]),
                )
                for entry in target["formal_classes"]:
                    frozen = self.classes_by_id[entry["id"]]
                    for field in ("name", "iri", "kind", "status"):
                        self.assertEqual(entry.get(field), frozen.get(field))
        for target in self.profile["relation_targets"]:
            with self.subTest(target=target["operational_id"]):
                self.assertTrue(set(target["ontology_ids"]) <= known_ids)
                self.assertEqual(
                    {entry["id"] for entry in target["formal_relations"]},
                    set(target["ontology_ids"]),
                )
                for entry in target["formal_relations"]:
                    frozen = self.relations_by_id[entry["id"]]
                    self.assertEqual(entry["name"], frozen["name"])

    def test_signature_classes_exist_and_operational_signatures_are_compatible(self) -> None:
        """Operational endpoint restrictions narrow, but never broaden, frozen signatures."""
        known_class_names = set(self.classes_by_name) | BUILTIN_OR_PROFILE_TYPES
        for target in self.profile["relation_targets"]:
            relations = [self.relations_by_id[item] for item in target["ontology_ids"]]
            for signature in target["operational_signatures"]:
                for side in ("domain", "range"):
                    operational_classes = signature[side]["classes"]
                    with self.subTest(
                        target=target["operational_id"], side=side,
                        classes=operational_classes,
                    ):
                        self.assertTrue(set(operational_classes) <= known_class_names)

                compatible_relation_ids: list[str] = []
                for relation in relations:
                    relation_compatible = True
                    for side in ("domain", "range"):
                        endpoint = signature[side]
                        operational_classes = endpoint["classes"]
                        if endpoint.get("pipeline_pseudo_type"):
                            relation_compatible &= side == "domain" and operational_classes == [
                                "AcceptedAssertion"
                            ]
                            continue
                        frozen_values = relation[side]
                        frozen_classes = set(
                            frozen_values if isinstance(frozen_values, list) else [frozen_values]
                        )
                        for operational_class in operational_classes:
                            compatible = (
                                operational_class in frozen_classes
                                or bool(self._ancestors(operational_class) & frozen_classes)
                            )
                            relation_compatible &= compatible
                    if relation_compatible:
                        compatible_relation_ids.append(relation["id"])
                self.assertTrue(
                    compatible_relation_ids,
                    f"{target['operational_id']} signature is outside every frozen "
                    f"declaration {target['ontology_ids']}",
                )

    def test_abstract_classes_are_not_directly_instantiable(self) -> None:
        """Every abstract ontology class remains pipeline-derived in the profile."""
        for target in self.profile["node_targets"]:
            abstract = any(
                self.classes_by_id[class_id].get("abstract", False)
                for class_id in target["ontology_ids"]
            )
            if abstract:
                with self.subTest(target=target["operational_id"]):
                    self.assertFalse(target["direct_instantiation"])
                    self.assertEqual(target["production_responsibility"], "pipeline_generated")

    def test_controlled_vocabulary_values_and_actions_are_valid(self) -> None:
        """Responsibilities, treatments, actions, and evaluation modes are controlled."""
        vocabularies = self.profile["controlled_vocabularies"]
        for group, action_vocabulary in (
            ("node_targets", "entity_actions"),
            ("relation_targets", "relation_actions"),
        ):
            for target in self.profile[group]:
                with self.subTest(target=target["operational_id"]):
                    self.assertIn(
                        target["production_responsibility"],
                        vocabularies["production_responsibility"],
                    )
                    self.assertIn(target["pilot_treatment"], vocabularies["pilot_treatment"])
                    self.assertTrue(
                        set(target["allowed_actions"]) <= set(vocabularies[action_vocabulary])
                    )
                    self.assertIn(target["evaluation_mode"], vocabularies["evaluation_modes"])

    def test_all_routing_categories_reference_active_targets(self) -> None:
        """B-P01 through B-P13 route only to declared operational IDs."""
        routes = self.profile["routing_categories"]
        self.assertEqual([route["id"] for route in routes], [f"B-P{i:02d}" for i in range(1, 14)])
        operational_ids = {row["operational_id"] for row in target_rows(self.profile)}
        for route in routes:
            with self.subTest(route=route["id"]):
                self.assertTrue(route["active_operational_target_ids"])
                self.assertTrue(set(route["active_operational_target_ids"]) <= operational_ids)

    def test_treatment_counts_match_profile_and_binding_markdown(self) -> None:
        """Treatment totals match declared counts and the final Markdown inventory."""
        markdown_counts = markdown_inventory_counts(
            TARGET_INVENTORY_PATH.read_text(encoding="utf-8")
        )
        for group in ("node_targets", "relation_targets"):
            actual = dict(Counter(row["pilot_treatment"] for row in self.profile[group]))
            declared_key = "nodes_by_treatment" if group == "node_targets" else "relations_by_treatment"
            with self.subTest(group=group):
                self.assertEqual(actual, EXPECTED_TREATMENT_COUNTS[group])
                self.assertEqual(actual, self.profile["counts"][declared_key])
                self.assertEqual(actual, markdown_counts[group])

    def test_contextual_metric_parameter_and_repository_identity_rules_exist(self) -> None:
        """Contextual occurrences and provisional repository identity remain explicit."""
        global_rules = self.profile["global_rules"]
        self.assertIn("contextual occurrences", global_rules["metric_parameter_policy"])
        self.assertIn("exact source strings", global_rules["metric_parameter_policy"])
        by_id = {row["operational_id"]: row for row in self.profile["node_targets"]}
        provisional = by_id["PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY"]
        exact = by_id["PUB-N-A-C01-REPOSITORY-EXISTING-EXACT-ENDPOINT"]
        self.assertEqual(provisional["emission_mode"], "llm_candidate")
        self.assertIn("provisional", provisional["boundary"].lower())
        self.assertEqual(exact["emission_mode"], "deterministic_context")

    def test_precedence_and_derived_assertion_metadata_are_explicit(self) -> None:
        """Precedence suppression and derived provenance remain machine-readable."""
        rules = self.profile["global_rules"]
        precedence = rules["use_mention_reference_precedence"]
        self.assertEqual(set(precedence), {
            "usesModel", "usesTool", "usesDataset", "usesDataset_and_referencesDataset",
            "hasCodeRepository",
        })
        self.assertFalse(rules["derived_assertions_scored_as_llm_predictions"])
        for target in target_rows(self.profile):
            if target["production_responsibility"] == "pipeline_generated":
                with self.subTest(target=target["operational_id"]):
                    self.assertEqual(target["evaluation_mode"], "pipeline_validation")
                    self.assertNotEqual(target["emission_mode"], "llm_candidate")

    def test_evidence_and_evaluation_policies_are_complete(self) -> None:
        """Every row has evidence and each treatment uses its approved evaluation mode."""
        modes_by_treatment = {
            "required_infrastructure": {"pipeline_validation"},
            "context_only": {"not_scored_context"},
            "out_of_scope": {"not_attempted"},
            "extract_and_evaluate": {"target_level_metrics"},
            "extract_and_monitor": {"pooled_metrics_and_case_analysis"},
            "deferred_resolution": {"resolution_accuracy"},
            "separate_follow_on_protocol": {"follow_on_only"},
        }
        for target in target_rows(self.profile):
            with self.subTest(target=target["operational_id"]):
                self.assertTrue(str(target["evidence_requirement"]).strip())
                self.assertIn(target["evaluation_mode"], modes_by_treatment[target["pilot_treatment"]])

    def test_nonordinary_treatments_cannot_be_open_discovery_candidates(self) -> None:
        """Context, excluded, and follow-on rows never become ordinary LLM candidates."""
        forbidden_treatments = {"context_only", "out_of_scope", "separate_follow_on_protocol"}
        for target in target_rows(self.profile):
            if target["pilot_treatment"] in forbidden_treatments:
                with self.subTest(target=target["operational_id"]):
                    self.assertNotEqual(target["emission_mode"], "llm_candidate")


class PublicationSourceUnitContractTests(unittest.TestCase):
    """Validate static invariants in the Publication source-unit contract."""

    @classmethod
    def setUpClass(cls) -> None:
        """Read the frozen source-unit contract once."""
        cls.text = SOURCE_UNIT_CONTRACT_PATH.read_text(encoding="utf-8")

    def assertContainsAll(self, *fragments: str) -> None:  # noqa: N802
        """Assert that every required literal fragment occurs in the contract."""
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.text)

    def test_contract_version_is_consistent(self) -> None:
        """Metadata and serialized-record examples use contract version 0.1.1."""
        self.assertIn(
            "**Status:** final and binding for Publication Pilot 1 implementation",
            self.text,
        )
        self.assertIn("**Date frozen:** 2026-07-30", self.text)
        self.assertIn("**Contract version:** 0.1.1", self.text)
        serialized_versions = re.findall(r'"contractVersion": "([^"]+)"', self.text)
        self.assertTrue(serialized_versions)
        self.assertEqual(set(serialized_versions), {"0.1.1"})

    def test_authority_order_matches_the_binding_integration_order(self) -> None:
        """The source contract does not omit or reorder binding Pilot 1 authorities."""
        authority = self.text.split("Conflicts are resolved in this order:", maxsplit=1)[1]
        authority = authority.split("Reviewed inputs:", maxsplit=1)[0]
        observed = [
            re.sub(r"^\d+\.\s*", "", line).rstrip(";").rstrip(".")
            for line in authority.splitlines()
            if re.match(r"^\d+\.\s", line)
        ]
        self.assertEqual(observed, EXPECTED_AUTHORITY_ORDER)

    def test_reviewed_source_hashes_match_repository_bytes(self) -> None:
        """Reviewed file hashes in the source contract identify current repository bytes."""
        table = self.text.split("Reviewed inputs:", maxsplit=1)[1].split(
            "The reviewed Phase A corpus has:", maxsplit=1
        )[0]
        rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|", table, re.MULTILINE)
        self.assertTrue(rows)
        for relative_path, expected_hash in rows:
            path = PROJECT_ROOT / relative_path
            with self.subTest(path=relative_path):
                if path == PHASE_A_CORPUS_PATH and not path.is_file():
                    continue
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)

    def test_canonical_text_and_offset_semantics_are_frozen(self) -> None:
        """Canonical Markdown and exact code-point slicing remain authoritative."""
        self.assertContainsAll(
            "### 3.2 Canonical Markdown is authoritative",
            "zero-based",
            "half-open [start, end)",
            "measured in Unicode code points",
            "text[startOffset:endOffset] == evidenceText",
            "unit.text[startOffsetInUnit:endOffsetInUnit] == evidenceText",
            "canonicalDocument[startOffsetInDocument:endOffsetInDocument] == evidenceText",
        )

    def test_unitization_parameters_and_partition_rules_are_frozen(self) -> None:
        """The canonical partition remains section-aware, bounded, and non-overlapping."""
        expected = {
            "preferredUnitMaxCharacters": "10000",
            "atomicBlockHardMaxCharacters": "20000",
            "overlapCharacters": "0",
            "crossSectionUnitsAllowed": "false",
            "ordinaryParagraphSplittingAllowed": "false",
        }
        for key, value in expected.items():
            matches = re.findall(rf"^{key}:\s*(\S+)\s*$", self.text, flags=re.MULTILINE)
            with self.subTest(parameter=key):
                self.assertEqual(matches, [value])
        self.assertContainsAll(
            "Units never cross section-segment boundaries.",
            "Ordinary prose paragraphs are not split",
            "The canonical source-unit partition has zero overlap.",
            "append complete Markdown blocks in source order",
            "must not leave unaccounted gaps",
        )

    def test_source_unit_and_request_context_are_distinct(self) -> None:
        """Canonical unit identity is independent of model-specific request context."""
        self.assertContainsAll(
            "### 3.7 Source-unit size is distinct from request-context size",
            "complete_section_when_budget_allows",
            "one primary source unit",
            "additional complete source units from the same section",
            "neighboring units from adjacent sections",
            "selective document-level context pass",
            "modelContextBudgetTokens",
            "never changes source-unit identity or evidence offsets",
            "Model-specific token budgets are applied later to the request envelope.",
        )

    def test_distributed_evidence_and_stable_identity_are_required(self) -> None:
        """Multi-unit evidence uses separate spans and deterministic identifiers/hashes."""
        self.assertContainsAll(
            "distributed evidence is represented by multiple evidence spans",
            "one evidence span may not cross a unit boundary",
            "pub:<paperID>:sec:<sectionOrdinal padded to four digits>",
            "pub:<paperID>:sec:<sectionOrdinal four digits>:unit:<chunkNumber four digits>",
            "rawFileSha256",
            "canonicalTextSha256",
            "textHash",
            "inputHash",
            "ordered by natural `paperID`, then `sectionOrdinal`, then `chunkNumber`",
        )

    def test_structured_and_problematic_content_has_explicit_handling(self) -> None:
        """The contract covers scientific blocks, references, damage, and visuals."""
        self.assertContainsAll(
            "fenced code blocks",
            "contiguous Markdown pipe tables",
            "contiguous list items",
            "display equations",
            "ordinary paragraphs separated by blank lines",
            "A self-contained textual caption is eligible.",
            "Reference content remains materialized for auditability",
            "oversized unsplittable atomic blocks",
            "damaged text whose missing content changes interpretation",
            "malformed Markdown fences",
            "Visual figure content is out of scope.",
        )

    def test_design_sample_and_pipeline_boundaries_are_explicit(self) -> None:
        """The exact twelve artifacts and non-mutating pipeline boundary remain frozen."""
        sample_block = self.text.split("The working design sample contains:", maxsplit=1)[1]
        sample_block = sample_block.split("```", maxsplit=2)[1]
        sample_block = sample_block.removeprefix("text\n")
        observed = tuple(item.strip() for item in sample_block.strip().split(","))
        self.assertEqual(observed, EXPECTED_SAMPLE_IDS)
        self.assertContainsAll(
            "mutate frozen Phase B outputs",
            "write to Neo4j",
            "LLM-generated summary, paraphrase, or reconstruction",
            "These thresholds are source-unit engineering parameters",
            "Model-specific token budgets are applied later",
        )

    def test_stable_error_codes_are_unique(self) -> None:
        """A generated validation failure maps to one unambiguous stable code."""
        block = self.text.split("### 18.3 Stable source-unit error codes", maxsplit=1)[1]
        block = block.split("```", maxsplit=2)[1]
        codes = [line.strip() for line in block.splitlines() if line.strip()]
        self.assertEqual(len(codes), len(set(codes)))

    def test_contract_freeze_and_implementation_acceptance_are_separate(self) -> None:
        """Design freeze is static; production checks belong to the later acceptance gate."""
        contract_gate = self.text.split("### 22.1 Contract-freeze gate", maxsplit=1)[1]
        contract_gate, implementation_gate = contract_gate.split(
            "### 22.2 Implementation-acceptance gate", maxsplit=1
        )
        implementation_gate = implementation_gate.split("## 23. Acceptance statement", maxsplit=1)[0]
        self.assertNotIn("- [ ]", contract_gate)
        self.assertGreaterEqual(contract_gate.count("- [x]"), 1)
        self.assertNotIn("- [x]", implementation_gate)
        self.assertGreaterEqual(implementation_gate.count("- [ ]"), 1)
        self.assertIn("Production code is not required for this gate.", contract_gate)
        self.assertIn("no unresolved methodological contradiction remains", contract_gate)
        self.assertNotIn("builder is implemented", contract_gate)
        self.assertIn("production source-unit builder is implemented", implementation_gate)
        self.assertIn("all twelve design-sample artifacts", implementation_gate)
        self.assertIn("complete_section_when_budget_allows", implementation_gate)
        self.assertIn(
            "Implementation acceptance is not a prerequisite for freezing the design\ncontract.",
            self.text,
        )


class PublicationPhaseAPortabilityTests(unittest.TestCase):
    """Validate clean-clone behavior without local generated publication data."""

    def test_missing_phase_a_corpus_raises_environment_skip(self) -> None:
        """A missing generated corpus produces SkipTest instead of a file error."""
        missing_path = PROJECT_ROOT / "data/interim/papers/__absent_phase_a_corpus__.json"
        with self.assertRaisesRegex(unittest.SkipTest, "local generated Publication Phase A"):
            load_phase_a_corpus(missing_path)


class PublicationPhaseACompatibilityTests(unittest.TestCase):
    """Check information availability in the real Phase A corpus and design sample."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the frozen Phase A corpus once."""
        cls.corpus = load_phase_a_corpus(PHASE_A_CORPUS_PATH)
        cls.publications = {
            str(publication["local_paper_id"]): publication
            for publication in cls.corpus["publications"]
        }

    def test_phase_a_has_canonical_paths_structure_and_identifiers(self) -> None:
        """Phase A supplies identity, headings, hierarchy hints, and canonical paths."""
        self.assertEqual(self.corpus["schema_version"], "1.1.0")
        self.assertEqual(self.corpus["phase_a_version"], "1.0.9")
        self.assertEqual(self.corpus["summary"]["publication_count"], 228)
        for paper_id in EXPECTED_SAMPLE_IDS:
            publication = self.publications[paper_id]
            with self.subTest(paper_id=paper_id):
                self.assertTrue(publication["canonical_artifact_id"])
                self.assertTrue(publication["source_files"]["markdown_path"])
                self.assertTrue(publication["content"]["headings"])
                self.assertIn("table_of_contents", publication["document_structure"])
                for heading in publication["content"]["headings"]:
                    self.assertGreaterEqual(heading["line_number"], 1)
                    self.assertIn(heading["level"], range(1, 7))

    def test_design_sample_markdown_and_marker_blocks_are_available_when_present(self) -> None:
        """Retained sample files expose canonical text and optional Marker block signals."""
        sample_root = PROJECT_ROOT / "data/raw/papers/markdowns"
        if not sample_root.exists():
            self.skipTest("third-party design-sample files are intentionally unavailable")
        for paper_id in EXPECTED_SAMPLE_IDS:
            publication = self.publications[paper_id]
            markdown_path = PROJECT_ROOT / publication["source_files"]["markdown_path"]
            chunks_path = PROJECT_ROOT / publication["source_files"]["chunks_path"]
            with self.subTest(paper_id=paper_id):
                self.assertTrue(markdown_path.is_file())
                self.assertTrue(chunks_path.is_file())
                self.assertTrue(markdown_path.read_text(encoding="utf-8-sig"))
                chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
                self.assertTrue(chunks["blocks"])
                self.assertFalse(
                    any(
                        key in block
                        for block in chunks["blocks"]
                        for key in ("startOffset", "endOffset", "char_start", "char_end")
                    )
                )

    def test_corrigendum_is_explicitly_represented(self) -> None:
        """The sample retains a distinct corrigendum and its corrected paper DOI."""
        corrigendum = self.publications["87-corrigendum"]
        self.assertEqual(corrigendum["record_type"], "corrigendum")
        correction = corrigendum["bibliographic_relations"]["correction_of"]
        self.assertEqual(correction["value"], "10.5194/hess-26-3377-2022")


if __name__ == "__main__":
    unittest.main()
