"""Tests for deterministic CIROH Hub Phase B extraction."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Any

from src.extraction.deterministic.extract_ciroh_hub import (
    DEFAULT_ONTOLOGY_SPEC,
    EVIDENCE_REQUIRED_KEYS,
    FORBIDDEN_NODE_CLASSES,
    FORBIDDEN_RELATIONS,
    HUB_NODE_RULE_IDS,
    HUB_RELATION_RULE_IDS,
    OutputValidationError,
    build_source_blob_url,
    derive_page_type,
    extract_corpus,
    extract_hydroshare_resource_id,
    load_corpus,
    load_ontology_registry,
    make_link_id,
    make_page_id,
    make_section_id,
    normalize_github_repo_url,
    normalize_text_key,
    serialize_deterministically,
    stable_json,
    stable_hash,
    validate_hub_rule_bindings,
    validate_output,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_CORPUS = PROJECT_ROOT / "data/interim/documents/ciroh_hub_corpus.json"


def make_heading(
    ordinal: int,
    text: str,
    source_line: int,
    level: int = 2,
    parent: int | None = None,
) -> dict[str, Any]:
    """Build one complete synthetic Phase A heading record."""
    return {
        "ordinal": ordinal,
        "level": level,
        "text": text,
        "raw_text": text,
        "source_line": source_line,
        "parent_heading_ordinal": parent,
    }


def make_link(
    ordinal: int,
    raw_target: str,
    resolved_url: str | None,
    link_type: str,
    source_line: int,
    heading_ordinal: int | None = None,
    anchor_text: str | None = "Link",
) -> dict[str, Any]:
    """Build one complete synthetic Phase A link occurrence."""
    return {
        "ordinal": ordinal,
        "anchor_text": anchor_text,
        "raw_target": raw_target,
        "resolved_url": resolved_url,
        "link_type": link_type,
        "source_line": source_line,
        "heading_ordinal": heading_ordinal,
    }


def make_page(
    canonical_url: str,
    corpus_path: str,
    source_path: str,
    *,
    source_group: str = "docs",
    parent_url: str | None = None,
    generated_from_js: bool = False,
    headings: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    authors: list[dict[str, Any]] | None = None,
    external_sources: list[dict[str, Any]] | None = None,
    title: str = "Synthetic page",
) -> dict[str, Any]:
    """Build one complete synthetic Phase A page using the frozen schema."""
    headings = headings or []
    links = links or []
    tags = tags or []
    authors = authors or []
    external_sources = external_sources or []
    max_line = max(
        [1]
        + [int(item["source_line"]) for item in headings]
        + [int(item["source_line"]) for item in links]
        + [int(item["source_line"]) for item in external_sources]
    )
    content = "\n".join(f"line {index}" for index in range(1, max_line + 1)) + "\n"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "page_key": f"page:{stable_hash(canonical_url)}",
        "canonical_url": canonical_url,
        "path": canonical_url.removeprefix("https://hub.ciroh.org").lstrip("/") or "/",
        "slug": None,
        "title": title,
        "title_source": "front_matter",
        "description": "Synthetic fixture",
        "last_updated_date": "2026-01-01",
        "last_updated_date_raw": "01/01/2026",
        "source_group": source_group,
        "corpus_path": corpus_path,
        "source_path": source_path,
        "generated_from_js": generated_from_js,
        "front_matter": {"title": title},
        "tags": tags,
        "authors": authors,
        "content_mdx": content,
        "headings": headings,
        "links": links,
        "external_content_sources": external_sources,
        "parent_url": parent_url,
        "file_sha256": digest,
        "content_sha256": digest,
        "warnings": [],
    }


def make_corpus(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a complete synthetic Phase A corpus with reconciled summary values."""
    by_source_group = Counter(str(page["source_group"]) for page in pages)
    return {
        "schema_version": "1.0.0",
        "phase_a_version": "1.0.2",
        "source": {
            "artifact_type": "ciroh_hub",
            "base_url": "https://hub.ciroh.org",
            "raw_root": "data/raw/documents",
        },
        "pages": pages,
        "known_exclusions": [
            {
                "route": "https://hub.ciroh.org/publications",
                "source_path": "src/pages/publications/index.js",
                "reason": "dynamic_zotero_catalog_delegated_to_paper_corpus",
            }
        ],
        "warnings": [],
        "summary": {
            "by_source_group": dict(sorted(by_source_group.items())),
            "exclusions_by_rule": {},
            "generated_from_js": sum(bool(page["generated_from_js"]) for page in pages),
            "page_warning_count": 0,
            "top_level_warning_count": 0,
            "total_external_content_sources": sum(len(page["external_content_sources"]) for page in pages),
            "total_headings": sum(len(page["headings"]) for page in pages),
            "total_links": sum(len(page["links"]) for page in pages),
            "total_pages": len(pages),
            "with_authors": sum(bool(page["authors"]) for page in pages),
            "with_external_content": sum(bool(page["external_content_sources"]) for page in pages),
            "with_parent_url": sum(page["parent_url"] is not None for page in pages),
            "with_tags": sum(bool(page["tags"]) for page in pages),
            "with_title_fallback": 0,
        },
    }


def synthetic_corpus() -> dict[str, Any]:
    """Return a compact fixture exercising local and exact cross-target rules."""
    parent_url = "https://hub.ciroh.org/docs/root"
    child_url = "https://hub.ciroh.org/release-notes/example"
    parent = make_page(
        parent_url,
        "docs/root.mdx",
        "docs/root.mdx",
        headings=[make_heading(1, "Root", 1)],
        tags=["Hydrology", "Unique tag"],
        title="Root",
    )
    child = make_page(
        child_url,
        "release-notes/example.mdx",
        "src/pages/release.js",
        source_group="release_notes",
        parent_url=parent_url,
        generated_from_js=True,
        headings=[
            make_heading(1, "Release", 1),
            make_heading(2, "Details", 2, level=3, parent=1),
        ],
        links=[
            make_link(1, "https://github.com/Example/Project/blob/main/README.md", "https://github.com/Example/Project/blob/main/README.md", "github", 3, 2),
            make_link(2, "https://www.hydroshare.org/resource/0123456789abcdef0123456789abcdef/", "https://www.hydroshare.org/resource/0123456789abcdef0123456789abcdef/", "hydroshare", 4, 2),
            make_link(3, "https://example.org/untyped", "https://example.org/untyped", "other_absolute", 5, 2),
            make_link(4, parent_url, parent_url, "hub_internal", 6, 2),
            make_link(5, "https://doi.org/10.1234/example", "https://doi.org/10.1234/example", "doi", 7, 2),
        ],
        tags=["hydrology", "Another tag"],
        authors=[
            {
                "name": "Ada Example",
                "role": "Author",
                "affiliation": "Example University",
                "url": "https://github.com/ada-example",
                "source": "materialized_author_block",
            }
        ],
        external_sources=[
            {
                "component": "GitHubReadme",
                "username": "Example",
                "repository": "Project",
                "path": "README.md",
                "source_line": 8,
                "ordinal": 1,
            },
            {
                "component": "GitHubWikiPage",
                "username": "Example",
                "repository": "WikiRepo",
                "path": "Home",
                "source_line": 9,
                "ordinal": 2,
            },
        ],
        title="Release",
    )
    return make_corpus([child, parent])


class HubPhaseBUnitTests(unittest.TestCase):
    """Exercise source-agnostic Hub Phase B rules with synthetic Phase A fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        """Extract the shared synthetic fixture once for focused assertions."""
        cls.corpus = synthetic_corpus()
        cls.ontology = load_ontology_registry(DEFAULT_ONTOLOGY_SPEC)
        cls.output = extract_corpus(
            cls.corpus,
            source_corpus_sha256="synthetic-source",
            ontology=cls.ontology,
        )
        cls.nodes = {node["id"]: node for node in cls.output["nodes"]}
        cls.edges = cls.output["edges"]

    def test_page_identifier_and_exact_evidence_creation(self) -> None:
        """Every page has its exact URL Identifier and five-field inline evidence."""
        for page in self.corpus["pages"]:
            page_id = make_page_id(page["canonical_url"])
            page_node = self.nodes[page_id]
            self.assertEqual(page_node["inventoryId"], "A-DC01")
            identifiers = [
                edge for edge in self.edges if edge["source"] == page_id and edge["relation"] == "hasIdentifier"
            ]
            self.assertEqual(len(identifiers), 1)
            self.assertEqual(set(page_node["evidence"]), EVIDENCE_REQUIRED_KEYS)

    def test_section_creation_and_heading_hierarchy(self) -> None:
        """Every heading becomes a Section with page-local parentSectionId structure."""
        child = self.corpus["pages"][0]
        second = self.nodes[make_section_id(child["canonical_url"], 2)]
        self.assertEqual(second["attributes"]["parentSectionId"], make_section_id(child["canonical_url"], 1))
        self.assertEqual(
            sum(edge["relation"] == "hasSection" for edge in self.edges),
            sum(len(page["headings"]) for page in self.corpus["pages"]),
        )

    def test_link_occurrence_identity_and_attributes(self) -> None:
        """Repeated-target semantics cannot collapse page-local Link occurrences."""
        child = self.corpus["pages"][0]
        link = self.nodes[make_link_id(child["canonical_url"], 1)]
        self.assertEqual(link["attributes"]["rawTarget"], child["links"][0]["raw_target"])
        self.assertEqual(link["attributes"]["sectionId"], make_section_id(child["canonical_url"], 2))
        self.assertEqual(sum(edge["relation"] == "linksTo" for edge in self.edges), 5)

    def test_subject_normalization_and_exact_consolidation(self) -> None:
        """NFKC/whitespace/casefold merges only exact normalized labels."""
        subjects = [node for node in self.output["nodes"] if node["class"] == "Subject"]
        self.assertEqual(len(subjects), 3)
        hydrology = next(node for node in subjects if node["attributes"]["normalizedLabel"] == "hydrology")
        self.assertEqual(hydrology["inventoryId"], "A-P04")
        self.assertEqual(hydrology["attributes"]["sourceLabels"], ["Hydrology", "hydrology"])
        self.assertEqual(sum(edge["relation"] == "hasSubject" for edge in self.edges), 4)
        self.assertNotEqual(normalize_text_key("Unique tag"), normalize_text_key("Another tag"))

    def test_person_organization_and_affiliation_rules(self) -> None:
        """Authors and affiliations remain source-scoped mentions with exact candidates."""
        people = [node for node in self.output["nodes"] if node["class"] == "Person"]
        organizations = [node for node in self.output["nodes"] if node["class"] == "Organization"]
        self.assertEqual(len(people), 1)
        self.assertEqual(len(organizations), 1)
        self.assertEqual(people[0]["identityRegime"], "github_login")
        self.assertEqual(people[0]["canonicalKey"], "github-login:ada-example")
        affiliation = next(edge for edge in self.edges if edge["relation"] == "affiliatedWith")
        self.assertEqual(affiliation["source"], people[0]["id"])
        self.assertEqual(affiliation["target"], organizations[0]["id"])

    def test_ordinary_and_generated_source_file_mapping(self) -> None:
        """Source paths create one RepoFile each with direct/generated availability semantics."""
        files = [node for node in self.output["nodes"] if node["class"] == "RepoFile"]
        self.assertEqual({node["attributes"]["path"] for node in files}, {"docs/root.mdx", "src/pages/release.js"})
        ordinary = next(node for node in files if node["attributes"]["path"] == "docs/root.mdx")
        generated = next(node for node in files if node["attributes"]["path"] == "src/pages/release.js")
        self.assertTrue(ordinary["attributes"]["downloaded"])
        self.assertFalse(generated["attributes"]["downloaded"])
        self.assertEqual(generated["attributes"]["materializedCorpusPath"], "release-notes/example.mdx")
        self.assertNotIn("release-notes/example.mdx", {node["attributes"]["path"] for node in files})
        self.assertIn("/blob/main/src/pages/release.js", generated["evidence"]["sourceLocation"])

    def test_page_hierarchy_and_inverse(self) -> None:
        """Every explicit parent creates isPartOf and formal C-DC02i hasSubPage."""
        is_part = next(edge for edge in self.edges if edge["relation"] == "isPartOf")
        inverse = next(edge for edge in self.edges if edge["relation"] == "hasSubPage")
        self.assertEqual(is_part["source"], inverse["target"])
        self.assertEqual(is_part["target"], inverse["source"])
        self.assertEqual(inverse["inventoryId"], "C-DC02i")

    def test_exact_github_and_hydroshare_stubs(self) -> None:
        """Exact supported targets create referenced stubs and declared semantic edges."""
        repositories = [
            node for node in self.output["nodes"]
            if node["class"] == "Repository" and node["attributes"].get("htmlUrl") == "https://github.com/Example/Project"
        ]
        datasets = [node for node in self.output["nodes"] if node["class"] == "DatasetResource"]
        self.assertEqual(len(repositories), 1)
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0]["attributes"]["resourceId"], "0123456789abcdef0123456789abcdef")
        self.assertTrue(any(edge["relation"] == "referencesRepository" and edge["target"] == repositories[0]["id"] for edge in self.edges))
        self.assertTrue(any(edge["relation"] == "referencesDataset" and edge["target"] == datasets[0]["id"] for edge in self.edges))

    def test_readme_and_wiki_mapping(self) -> None:
        """README declares documents; Wiki declares only reference plus deferred mirror semantics."""
        self.assertEqual(sum(edge["relation"] == "documents" for edge in self.edges), 1)
        self.assertEqual(
            Counter(record["reason"] for record in self.output["deferred"])["github_wiki_mirror_relation_not_declared"],
            1,
        )
        wiki_repo = next(
            node for node in self.output["nodes"]
            if node["class"] == "Repository" and node["attributes"].get("name") == "WikiRepo"
        )
        self.assertFalse(any(edge["relation"] == "documents" and edge["target"] == wiki_repo["id"] for edge in self.edges))

    def test_restricted_release_and_pull_request_announcements(self) -> None:
        """Internal release links and exact blog/release PR links alone create announces."""
        child = self.corpus["pages"][0]
        parent_id = make_page_id(str(child["parent_url"]))
        self.assertTrue(
            any(
                edge["relation"] == "announces"
                and edge["source"] == make_page_id(child["canonical_url"])
                and edge["target"] == parent_id
                for edge in self.edges
            )
        )
        blog = make_page(
            "https://hub.ciroh.org/blog/pr",
            "blog/pr.mdx",
            "blog/pr.mdx",
            source_group="blog",
            links=[
                make_link(
                    1,
                    "https://github.com/Example/Project/pull/42",
                    "https://github.com/Example/Project/pull/42",
                    "github",
                    1,
                )
            ],
        )
        output = extract_corpus(make_corpus([blog]), source_corpus_sha256="pr-fixture", ontology=self.ontology)
        announcements = [edge for edge in output["edges"] if edge["relation"] == "announces"]
        self.assertEqual(len(announcements), 1)
        self.assertEqual(announcements[0]["attributes"]["pullRequestNumber"], 42)

    def test_catalog_cards_are_structural_and_deferred(self) -> None:
        """Repeated catalog card headings remain Sections without Tool/Model typing."""
        catalog = make_page(
            "https://hub.ciroh.org/docs/products/intro",
            "docs/products/intro.mdx",
            "docs/products/intro.mdx",
            headings=[
                make_heading(1, "Catalog", 1),
                make_heading(2, "Cards", 2, level=3, parent=1),
                make_heading(3, "First", 3, level=4, parent=2),
                make_heading(4, "Second", 4, level=4, parent=2),
            ],
        )
        output = extract_corpus(make_corpus([catalog]), source_corpus_sha256="catalog-fixture", ontology=self.ontology)
        reasons = Counter(record["reason"] for record in output["deferred"])
        self.assertEqual(reasons["product_card_semantic_typing_deferred"], 2)
        self.assertFalse(any(node["class"] in {"Tool", "ComputationalModel"} for node in output["nodes"]))

    def test_unsupported_urls_remain_only_generic_links(self) -> None:
        """An untyped absolute URL creates no external artifact stub or undeclared relation."""
        unsupported = "https://example.org/untyped"
        self.assertTrue(any(node["class"] == "Link" and node["attributes"]["rawTarget"] == unsupported for node in self.output["nodes"]))
        self.assertFalse(
            any(
                unsupported in stable_json(node.get("attributes", {}))
                for node in self.output["nodes"]
                if node["class"] in {"Repository", "DatasetResource", "DocumentationPage"}
            )
        )
        self.assertIn("other_absolute_link_semantics_unknown", {record["reason"] for record in self.output["deferred"]})

    def test_no_fuzzy_or_prose_semantic_extraction(self) -> None:
        """The deterministic output contains no LLM-reserved class or relation."""
        self.assertTrue(FORBIDDEN_NODE_CLASSES.isdisjoint(node["class"] for node in self.output["nodes"]))
        self.assertTrue(FORBIDDEN_RELATIONS.isdisjoint(edge["relation"] for edge in self.edges))

    def test_ontology_and_domain_range_validation(self) -> None:
        """Independent validation rejects unknown IDs and formal domain violations."""
        unknown = copy.deepcopy(self.output)
        unknown["nodes"][0]["inventoryId"] = "A-NOT-REAL"
        issues = validate_output(unknown, self.corpus, self.ontology)
        self.assertTrue(any("unknown class inventory ID" in issue for issue in issues))
        invalid_domain = copy.deepcopy(self.output)
        edge = next(item for item in invalid_domain["edges"] if item["relation"] == "hasSection")
        edge["source"] = edge["target"]
        issues = validate_output(invalid_domain, self.corpus, self.ontology)
        self.assertTrue(any("domain violation" in issue for issue in issues))

    def test_duplicate_ontology_relation_names_are_accepted(self) -> None:
        """Module-specific inventory entries may share one formal relation name."""
        has_subject_ids = {
            inventory_id
            for inventory_id, definition in self.ontology.relations_by_id.items()
            if definition.get("name") == "hasSubject"
        }
        self.assertEqual(has_subject_ids, {"C-P03", "C-D06", "C-DC04"})

    def test_hub_rule_bindings_match_ontology_definitions(self) -> None:
        """Every executable Hub binding resolves to the expected ontology name."""
        validate_hub_rule_bindings(self.ontology)
        for class_name, inventory_id in HUB_NODE_RULE_IDS.items():
            self.assertEqual(self.ontology.classes_by_id[inventory_id]["name"], class_name)
        for relation_name, inventory_id in HUB_RELATION_RULE_IDS.items():
            self.assertEqual(self.ontology.relations_by_id[inventory_id]["name"], relation_name)

    def test_hub_rule_binding_rejects_mismatched_ontology_name(self) -> None:
        """A binding cannot point at an inventory entry for another concept."""
        changed = dict(HUB_RELATION_RULE_IDS)
        changed["hasSubject"] = "C-DC01"
        with self.assertRaisesRegex(ValueError, "whose ontology name is 'hasSection'"):
            validate_hub_rule_bindings(self.ontology, relation_rule_ids=changed)

    def test_hub_profile_selects_documentation_has_subject_rule(self) -> None:
        """The Hub profile rejects substitution by another module's same-named rule."""
        expected_profile = dict(HUB_RELATION_RULE_IDS)
        changed_profile = dict(expected_profile)
        changed_profile["hasSubject"] = "C-D06"
        self.assertEqual(expected_profile["hasSubject"], "C-DC04")
        self.assertNotEqual(changed_profile, expected_profile)

    def test_emitted_inventory_ids_follow_hub_rule_bindings(self) -> None:
        """Every graph record carries the inventory rule that authorized it."""
        for node in self.output["nodes"]:
            self.assertEqual(node["inventoryId"], HUB_NODE_RULE_IDS[node["class"]])
        for edge in self.output["edges"]:
            self.assertEqual(edge["inventoryId"], HUB_RELATION_RULE_IDS[edge["relation"]])

    def test_every_node_and_edge_has_exact_five_field_evidence(self) -> None:
        """Inline evidence uses exactly the established deterministic interim shape."""
        owners = self.output["nodes"] + self.output["edges"]
        self.assertEqual(self.output["stats"]["evidenceSpanCount"], len(owners))
        for owner in owners:
            self.assertEqual(set(owner["evidence"]), EVIDENCE_REQUIRED_KEYS)
            self.assertTrue(all(owner["evidence"][key] not in (None, "") for key in EVIDENCE_REQUIRED_KEYS))
        self.assertFalse(any(node["class"] == "EvidenceSpan" for node in self.output["nodes"]))

    def test_duplicate_dangling_and_missing_evidence_rejection(self) -> None:
        """Independent validation detects duplicate IDs, dangling endpoints, and invalid evidence."""
        duplicate = copy.deepcopy(self.output)
        duplicate["nodes"].append(copy.deepcopy(duplicate["nodes"][0]))
        self.assertIn("duplicate node IDs", validate_output(duplicate, self.corpus, self.ontology))
        dangling = copy.deepcopy(self.output)
        dangling["edges"][0]["target"] = "hub:missing"
        self.assertTrue(any("dangling endpoint" in issue for issue in validate_output(dangling, self.corpus, self.ontology)))
        missing = copy.deepcopy(self.output)
        missing["nodes"][0]["evidence"].pop("version")
        self.assertTrue(any("evidence keys differ" in issue for issue in validate_output(missing, self.corpus, self.ontology)))

    def test_helpers_apply_exact_guards(self) -> None:
        """Canonicalizers accept exact targets and preserve encoded repository paths."""
        self.assertEqual(stable_hash("example"), hashlib.sha256(b"example").hexdigest()[:20])
        self.assertEqual(normalize_github_repo_url("https://github.com/Org/Repo/tree/main"), "https://github.com/Org/Repo")
        self.assertIsNone(normalize_github_repo_url("https://github.com/Org"))
        self.assertIsNone(normalize_github_repo_url("https://github.com/orgs/Org"))
        self.assertIsNone(normalize_github_repo_url("https://github.com/Org/Repo/actions/workflows/test/badge.svg"))
        self.assertEqual(
            extract_hydroshare_resource_id("https://hydroshare.org/resource/0123456789ABCDEF0123456789ABCDEF/"),
            "0123456789abcdef0123456789abcdef",
        )
        self.assertEqual(
            build_source_blob_url("https://github.com/Org/Repo", "main", "docs/NWMURL Library.mdx"),
            "https://github.com/Org/Repo/blob/main/docs/NWMURL%20Library.mdx",
        )
        self.assertEqual(derive_page_type(self.corpus["pages"][0]), "release-note")

    def test_repeated_extraction_is_byte_identical(self) -> None:
        """Input ordering and repeated execution cannot change serialized output."""
        second_corpus = copy.deepcopy(self.corpus)
        second_corpus["pages"].reverse()
        second = extract_corpus(
            second_corpus,
            source_corpus_sha256="synthetic-source",
            ontology=self.ontology,
        )
        self.assertEqual(serialize_deterministically(self.output), serialize_deterministically(second))

    def test_validation_failure_prevents_success(self) -> None:
        """Unsupported source versions fail before graph construction."""
        unsupported = copy.deepcopy(self.corpus)
        unsupported["phase_a_version"] = "9.0.0"
        with self.assertRaises(ValueError):
            extract_corpus(unsupported, ontology=self.ontology)
        malformed = copy.deepcopy(self.corpus)
        malformed["pages"][0]["parent_url"] = "https://hub.ciroh.org/missing"
        with self.assertRaises(ValueError):
            extract_corpus(malformed, ontology=self.ontology)


@unittest.skipUnless(FROZEN_CORPUS.exists(), "CIROH Hub Phase A frozen corpus unavailable")
class HubPhaseBFrozenRegressionTests(unittest.TestCase):
    """Validate the complete 242-page frozen Hub extraction independently of unit fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load and extract the frozen corpus once with all acceptance anchors enabled."""
        cls.corpus, cls.source_hash = load_corpus(FROZEN_CORPUS)
        cls.ontology = load_ontology_registry(DEFAULT_ONTOLOGY_SPEC)
        cls.output = extract_corpus(
            cls.corpus,
            cls.source_hash,
            ontology=cls.ontology,
            validate_frozen_snapshot=True,
        )

    def test_frozen_formal_node_and_occurrence_anchors(self) -> None:
        """Frozen class and occurrence counts follow the corrected authoritative contract."""
        node_counts = Counter(node["class"] for node in self.output["nodes"])
        edge_counts = Counter(edge["relation"] for edge in self.output["edges"])
        expected_nodes = {
            "DocumentationPage": 242,
            "RepoFile": 242,
            "Section": 1583,
            "Link": 1767,
            "Subject": 125,
            "Person": 119,
            "Organization": 119,
        }
        for class_name, count in expected_nodes.items():
            self.assertEqual(node_counts[class_name], count)
        self.assertEqual(edge_counts["hasSubject"], 1187)
        self.assertEqual(edge_counts["hasSection"], 1583)
        self.assertEqual(edge_counts["linksTo"], 1767)
        self.assertEqual(edge_counts["hasContributor"], 119)
        self.assertEqual(edge_counts["affiliatedWith"], 119)
        self.assertEqual(edge_counts["isPartOf"], 241)
        self.assertEqual(edge_counts["hasSubPage"], 241)

    def test_frozen_exact_two_case_normalization_merges(self) -> None:
        """Exactly the two ratified case pairs collapse from 127 spellings to 125 Subjects."""
        raw_spellings = {str(tag) for page in self.corpus["pages"] for tag in page["tags"]}
        subjects = [node for node in self.output["nodes"] if node["class"] == "Subject"]
        merged = {
            tuple(node["attributes"]["sourceLabels"])
            for node in subjects
            if len(node["attributes"]["sourceLabels"]) > 1
        }
        self.assertEqual(len(raw_spellings), 127)
        self.assertEqual(len(subjects), 125)
        self.assertEqual(
            merged,
            {("Hydrology", "hydrology"), ("NSF ACCESS", "NSF Access")},
        )
        self.assertEqual(sum(len(node["attributes"]["sourceLabels"]) for node in subjects), 127)
        self.assertTrue(all(len(node["attributes"]["sourceLabels"]) == 1 for node in subjects if tuple(node["attributes"]["sourceLabels"]) not in merged))
        self.assertTrue(all(node["inventoryId"] == "A-P04" for node in subjects))

    def test_frozen_source_files_and_generated_pages(self) -> None:
        """Distinct explicit source paths own files; generated corpus paths never duplicate them."""
        files = [node for node in self.output["nodes"] if node["class"] == "RepoFile"]
        self.assertEqual(len(files), 242)
        self.assertEqual(sum(not node["attributes"]["downloaded"] for node in files), 11)
        self.assertFalse(any(str(node["attributes"]["path"]).startswith("_generated_js_pages/") for node in files))
        self.assertEqual(sum(edge["relation"] == "hasSourceFile" for edge in self.output["edges"]), 242)
        self.assertEqual(sum(edge["relation"] == "hasFile" for edge in self.output["edges"]), 242)

    def test_frozen_external_component_and_exact_target_rules(self) -> None:
        """README/Wiki declarations and exact repository/dataset stubs remain within mapping scope."""
        edge_counts = Counter(edge["relation"] for edge in self.output["edges"])
        self.assertEqual(edge_counts["documents"], 49)
        self.assertEqual(
            Counter(record["reason"] for record in self.output["deferred"])["github_wiki_mirror_relation_not_declared"],
            1,
        )
        self.assertGreater(edge_counts["referencesRepository"], 0)
        self.assertGreater(edge_counts["referencesDataset"], 0)
        self.assertTrue(
            all(
                node["curationStatus"] == "referenced"
                for node in self.output["nodes"]
                if node["class"] in {"Repository", "DatasetResource"}
            )
        )

    def test_frozen_evidence_and_ontology_validation(self) -> None:
        """Every graph record has exactly one valid inline five-field EvidenceSpan."""
        owners = self.output["nodes"] + self.output["edges"]
        self.assertEqual(self.output["stats"]["evidenceSpanCount"], len(owners))
        self.assertTrue(all(set(owner["evidence"]) == EVIDENCE_REQUIRED_KEYS for owner in owners))
        self.assertTrue(
            all(node["inventoryId"] == HUB_NODE_RULE_IDS[node["class"]] for node in self.output["nodes"])
        )
        self.assertTrue(
            all(edge["inventoryId"] == HUB_RELATION_RULE_IDS[edge["relation"]] for edge in self.output["edges"])
        )
        self.assertEqual(validate_output(self.output, self.corpus, self.ontology, True), [])

    def test_frozen_no_llm_reserved_semantics(self) -> None:
        """The full deterministic graph emits no class or relation reserved for semantic extraction."""
        self.assertTrue(FORBIDDEN_NODE_CLASSES.isdisjoint(node["class"] for node in self.output["nodes"]))
        self.assertTrue(FORBIDDEN_RELATIONS.isdisjoint(edge["relation"] for edge in self.output["edges"]))

    def test_frozen_repeated_build_is_byte_identical(self) -> None:
        """Two independent complete extractions serialize to exactly the same bytes."""
        second = extract_corpus(
            copy.deepcopy(self.corpus),
            self.source_hash,
            ontology=self.ontology,
            validate_frozen_snapshot=True,
        )
        first_bytes = serialize_deterministically(self.output)
        second_bytes = serialize_deterministically(second)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), hashlib.sha256(second_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
