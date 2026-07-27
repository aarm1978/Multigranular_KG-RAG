"""Tests for deterministic Publication Phase B extraction."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import src.extraction.deterministic.extract_publication as extraction_module

from src.extraction.deterministic.extract_publication import (
    CURATED,
    DEFAULT_ONTOLOGY_SPEC,
    EVIDENCE_REQUIRED_KEYS,
    Edge,
    FIELD_DISPOSITIONS,
    GraphBuilder,
    Node,
    OntologyRegistry,
    OutputValidationError,
    build_global_citation_target_registry,
    classify_cited_doi_target,
    classify_context_signals,
    extract_corpus,
    extract_doi_local_context,
    extract_hydroshare_resource_id,
    github_repository_identity_url,
    load_json,
    load_ontology,
    main,
    make_edge_id,
    make_person_mention_id,
    normalize_doi,
    normalize_github_repository_url,
    normalize_text_key,
    serialize_deterministically,
    stable_hash,
    validate_field_coverage,
    validate_output,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_CORPUS = PROJECT_ROOT / "data/interim/papers/ciroh_publication_corpus.json"


def source_location(line: int = 10, section: str = "References") -> dict[str, Any]:
    """Build one reference/keyword source location."""
    return {
        "source_artifact": "https://doi.org/10.1234/source",
        "section": section,
        "line_start": line,
        "line_end": line,
    }


def availability_location(line: int = 20) -> dict[str, Any]:
    """Build one availability source location."""
    return {
        "source_artifact": "https://doi.org/10.1234/source",
        "line_start": line,
        "line_end": line,
    }


def reference(doi: str, text: str, line: int = 10, occurrences: int = 1) -> dict[str, Any]:
    """Build one complete synthetic Phase A DOI record."""
    location = source_location(line)
    return {
        "doi": doi,
        "uri": f"https://doi.org/{doi}",
        "reference_text": text,
        "source_location": location,
        "occurrences": [
            {
                "reference_text": text,
                "source_location": source_location(line + index),
            }
            for index in range(occurrences)
        ],
    }


def availability(
    scheme: str,
    value: str,
    category: str = "data_availability",
    evidence: str | None = None,
    line: int = 20,
) -> dict[str, Any]:
    """Build one complete synthetic availability identifier."""
    uri = f"https://doi.org/{value}" if scheme == "doi" else value
    return {
        "identifier_scheme": scheme,
        "identifier_value": value,
        "identifier_uri": uri,
        "section_category": category,
        "section_title": category.replace("_", " ").title(),
        "evidence_text": evidence or f"Available at {uri}",
        "source_location": availability_location(line),
    }


def author(position: int = 1, name: str = "Jane Doe") -> dict[str, Any]:
    """Build one ordered Phase A author."""
    given, family = name.split(" ", 1)
    return {
        "display_name": name,
        "given_names": [given],
        "family_name": family,
        "name_particles": [],
        "suffix": None,
        "literal_name": None,
        "raw_bibtex": f"{family}, {given}",
        "position": position,
    }


def publication(
    doi: str,
    *,
    title: str | None = None,
    authors: list[dict[str, Any]] | None = None,
    venue: str = "Journal of Tests",
    keywords: list[str] | None = None,
    references: list[dict[str, Any]] | None = None,
    availability_records: list[dict[str, Any]] | None = None,
    correction_of: str | None = None,
) -> dict[str, Any]:
    """Build one complete synthetic publication record."""
    artifact = f"https://doi.org/{doi}"
    local_id = stable_hash(doi)[:6]
    keyword_values = keywords or []
    return {
        "local_paper_id": local_id,
        "canonical_artifact_id": artifact,
        "canonical_identifier": {"scheme": "doi", "value": doi, "uri": artifact},
        "identifiers": [
            {"scheme": "doi", "value": doi, "uri": artifact},
            {"scheme": "url", "value": artifact, "uri": artifact},
        ],
        "record_type": "journal_article",
        "curation_status": "curated",
        "bibliographic": {
            "title": title or f"Paper {doi}",
            "authors": authors or [author()],
            "year": 2026,
            "venue": venue,
            "volume": "1",
            "issue": "2",
            "pages": "1-10",
            "publisher": "Test Publisher",
            "language": "en",
            "abstract": "A deterministic abstract.",
            "abstract_source": {"source_type": "markdown_explicit"},
        },
        "content": {
            "headings": [
                {"level": 1, "text": "Title", "normalized_text": "title", "line_number": 1}
            ],
            "explicit_keywords": [
                {
                    "raw_value": value,
                    "value": normalize_text_key(value),
                    "source_type": "markdown_explicit",
                    "source_location": {
                        **source_location(5, "Keywords"),
                        "source_artifact": artifact,
                    },
                }
                for value in keyword_values
            ],
            "reference_dois": references or [],
            "availability_identifiers": availability_records or [],
        },
        "document_structure": {
            "page_count": 10,
            "table_of_contents": [
                {"title": "Introduction", "page_id": 1, "heading_level": 1, "polygon": []}
            ],
        },
        "source_files": {
            "pdf_path": f"data/raw/papers/pdfs/{local_id}.pdf",
            "markdown_path": f"data/raw/papers/markdowns/{local_id}/markdown/{local_id}_md.md",
            "markdown_meta_path": f"data/raw/papers/markdowns/{local_id}/markdown/{local_id}_meta.json",
            "chunks_path": f"data/raw/papers/markdowns/{local_id}/chunks/{local_id}.json",
            "chunks_meta_path": f"data/raw/papers/markdowns/{local_id}/chunks/{local_id}_meta.json",
            "marker_json_path": f"data/raw/papers/markdowns/{local_id}/json/{local_id}.json",
            "marker_json_meta_path": f"data/raw/papers/markdowns/{local_id}/json/{local_id}_meta.json",
        },
        "bibliographic_relations": {
            "correction_of": (
                {
                    "scheme": "doi",
                    "value": correction_of,
                    "uri": f"https://doi.org/{correction_of}",
                }
                if correction_of
                else None
            )
        },
        "reconciliation": {
            "excel_matched": True,
            "zotero_key_original": "TEST",
            "bibtex_key": "TEST",
            "bibtex_match_method": "exact",
            "bibtex_entry_type": "article",
            "override_applied": False,
            "override_action": None,
            "conflicts": [],
            "warnings": [],
        },
    }


def corpus(publications: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a reconciled synthetic Phase A corpus."""
    return {
        "schema_version": "1.1.0",
        "phase_a_version": "1.0.9",
        "source": {
            "artifact_type": "publication",
            "corpus_cutoff": "2025-04-30",
            "raw_root": "data/raw/papers",
            "selection_method": "synthetic",
        },
        "publications": publications,
        "known_exclusions": [],
        "warnings": [],
        "summary": {
            "publication_count": len(publications),
            "known_exclusion_count": 0,
            "warning_count": sum(
                len(item["reconciliation"]["warnings"]) for item in publications
            ),
            "conflict_count": 0,
            "explicit_keyword_count": sum(
                len(item["content"]["explicit_keywords"]) for item in publications
            ),
            "reference_doi_count": sum(
                len(item["content"]["reference_dois"]) for item in publications
            ),
            "availability_identifier_count": sum(
                len(item["content"]["availability_identifiers"]) for item in publications
            ),
        },
    }


class PublicationExtractorTests(unittest.TestCase):
    """Exercise synthetic and frozen Publication Phase B behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the authoritative ontology once for this test class."""
        cls.ontology = load_ontology(DEFAULT_ONTOLOGY_SPEC)

    def extract(self, value: dict[str, Any]) -> dict[str, Any]:
        """Extract one synthetic corpus with a fixed diagnostic source hash."""
        return extract_corpus(
            value,
            self.ontology,
            source_corpus_sha256="0" * 64,
        )

    def test_stable_hash_and_normalizers(self) -> None:
        """Stable IDs and exact normalizers follow the mapping recipes."""
        self.assertEqual(stable_hash("abc"), hashlib.sha256(b"abc").hexdigest()[:20])
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC"), "10.1234/abc")
        self.assertEqual(
            normalize_github_repository_url("https://github.com/Owner/Repo.git/issues/1?q=x"),
            "https://github.com/Owner/Repo",
        )
        self.assertEqual(
            github_repository_identity_url(
                "https://github.com/Owner/Repo.git/issues/1?q=x"
            ),
            "https://github.com/owner/repo",
        )
        self.assertIsNone(
            normalize_github_repository_url(
                "https://github.com/user-attachments/assets/01234567"
            )
        )
        self.assertEqual(
            extract_hydroshare_resource_id(
                "https://www.hydroshare.org/resource/0123456789abcdef0123456789ABCDEF/"
            ),
            "0123456789abcdef0123456789abcdef",
        )

    def test_paper_identity_identifiers_and_exact_evidence(self) -> None:
        """A curated DOI Paper retains exact identifiers and five-field evidence."""
        output = self.extract(corpus([publication("10.1234/source")]))
        paper = next(node for node in output["nodes"] if node["class"] == "Paper")
        self.assertEqual(paper["canonicalKey"], "doi:10.1234/source")
        self.assertEqual(set(paper["evidence"]), set(EVIDENCE_REQUIRED_KEYS))
        self.assertEqual(output["stats"]["edgesByRelation"]["hasIdentifier"], 2)

    def test_url_only_paper_identity(self) -> None:
        """A DOI-absent curated publication uses its canonical public URL."""
        pub = publication("10.1234/temporary")
        url = "https://example.org/publication/one"
        pub["canonical_artifact_id"] = url
        pub["canonical_identifier"] = {"scheme": "url", "value": url, "uri": url}
        pub["identifiers"] = [{"scheme": "url", "value": url, "uri": url}]
        output = self.extract(corpus([pub]))
        paper = next(node for node in output["nodes"] if node["class"] == "Paper")
        self.assertEqual(paper["canonicalKey"], f"url:{url}")
        self.assertEqual(paper["identityRegime"], "canonical_url")

    def test_exact_identifier_is_reused_across_papers(self) -> None:
        """Equal scheme/value declarations share one exact Identifier node."""
        shared = {"scheme": "url", "value": "https://example.org/shared", "uri": "https://example.org/shared"}
        pubs = [publication("10.1234/a"), publication("10.1234/b")]
        for pub in pubs:
            pub["identifiers"].append(copy.deepcopy(shared))
        output = self.extract(corpus(pubs))
        matches = [node for node in output["nodes"] if node["canonicalKey"] == "url:https://example.org/shared"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            sum(edge["relation"] == "hasIdentifier" and edge["target"] == matches[0]["id"] for edge in output["edges"]),
            2,
        )

    def test_author_mentions_are_source_scoped_and_ordered(self) -> None:
        """Equal author names in separate papers never merge."""
        pubs = [
            publication("10.1234/a", authors=[author(1), author(2, "John Smith")]),
            publication("10.1234/b", authors=[author(1)]),
        ]
        output = self.extract(corpus(pubs))
        people = [node for node in output["nodes"] if node["class"] == "Person"]
        self.assertEqual(len(people), 3)
        self.assertEqual(len({node["id"] for node in people}), 3)
        self.assertEqual(
            sorted(edge["attributes"]["authorPosition"] for edge in output["edges"] if edge["relation"] == "hasAuthor"),
            [1, 1, 2],
        )
        self.assertNotEqual(
            make_person_mention_id("doi:10.1234/a", 1),
            make_person_mention_id("doi:10.1234/b", 1),
        )

    def test_exact_venue_and_subject_reuse(self) -> None:
        """NFKC/casefold-equal venues and subjects share exact nodes."""
        pubs = [
            publication("10.1234/a", venue="Test Journal", keywords=["Hydrology"]),
            publication("10.1234/b", venue=" test  journal ", keywords=["hydrology"]),
        ]
        output = self.extract(corpus(pubs))
        self.assertEqual(sum(node["class"] == "Venue" for node in output["nodes"]), 1)
        self.assertEqual(sum(node["class"] == "Subject" for node in output["nodes"]), 1)
        self.assertEqual(sum(edge["relation"] == "hasSubject" for edge in output["edges"]), 2)

    def test_curated_and_shared_external_citation_targets(self) -> None:
        """Curated DOI targets are reused and external targets are globally shared."""
        ext = reference("10.5678/external", "Author. https://doi.org/10.5678/external", occurrences=2)
        pubs = [
            publication("10.1234/a", references=[reference("10.1234/b", "B. doi:10.1234/b"), ext]),
            publication("10.1234/b", references=[reference("10.5678/external", "C. doi:10.5678/external")]),
        ]
        output = self.extract(corpus(pubs))
        curated_target = next(node for node in output["nodes"] if node["canonicalKey"] == "doi:10.1234/b")
        self.assertEqual(curated_target["curationStatus"], CURATED)
        external = [node for node in output["nodes"] if node["canonicalKey"] == "doi:10.5678/external"]
        self.assertEqual(len(external), 1)
        citation_edges = [edge for edge in output["edges"] if edge["relation"] == "cites"]
        self.assertEqual(len(citation_edges), 3)
        aggregated = next(edge for edge in citation_edges if len(edge["attributes"].get("sourceDeclarations", [])) == 2)
        self.assertEqual(len(aggregated["attributes"]["sourceDeclarations"]), 2)

    def test_dataset_citation_uses_c_p29(self) -> None:
        """Strong dataset DOI evidence creates referencesDataset, never usesDataset."""
        pub = publication(
            "10.1234/source",
            references=[reference("10.5678/data", "Creator. [Data set]. doi:10.5678/data")],
        )
        output = self.extract(corpus([pub]))
        edge = next(edge for edge in output["edges"] if edge["relation"] == "referencesDataset")
        self.assertEqual(edge["inventoryId"], "C-P29")
        self.assertFalse(any(edge["relation"] == "usesDataset" for edge in output["edges"]))

    def test_doi_local_context_does_not_borrow_neighbor_type(self) -> None:
        """A resource label associated with one DOI does not type its neighbor."""
        text = "[Data set] doi:10.5678/data; Article doi:10.5678/paper"
        context = extract_doi_local_context(text, "10.5678/paper")
        self.assertNotIn("[Data set]", context)

    def test_neighbor_dataset_and_software_markers_do_not_cross_targets(self) -> None:
        """A following bibliographic target cannot type the DOI before it."""
        cases = (
            (
                "Article doi:10.5678/paper. Next work [Dataset] doi:10.5678/data",
                "10.5678/data",
            ),
            (
                "Article doi:10.5678/paper. Next work [Software] doi:10.5678/tool",
                "10.5678/tool",
            ),
        )
        for text, neighboring_doi in cases:
            with self.subTest(text=text):
                paper_context = extract_doi_local_context(text, "10.5678/paper")
                self.assertEqual(classify_context_signals(paper_context, "10.5678/paper"), set())
                neighbor_context = extract_doi_local_context(text, neighboring_doi)
                self.assertTrue(classify_context_signals(neighbor_context, neighboring_doi))

    def test_multi_doi_and_unattributed_marker_do_not_share_type(self) -> None:
        """A multi-DOI occurrence retains only uniquely attributable type labels."""
        text = "[Dataset] doi:10.5678/data; ordinary article doi:10.5678/paper"
        data_context = extract_doi_local_context(text, "10.5678/data")
        paper_context = extract_doi_local_context(text, "10.5678/paper")
        self.assertEqual(
            classify_context_signals(data_context, "10.5678/data"),
            {"DatasetResource"},
        )
        self.assertEqual(classify_context_signals(paper_context, "10.5678/paper"), set())

        trailing = "doi:10.5678/first and doi:10.5678/second [Software]"
        for doi in ("10.5678/first", "10.5678/second"):
            context = extract_doi_local_context(trailing, doi)
            self.assertEqual(classify_context_signals(context, doi), set())

    def test_repeated_occurrences_are_classified_before_global_aggregation(self) -> None:
        """Untyped and strong occurrences remain separate before one global decision."""
        pub = publication(
            "10.1234/source",
            references=[
                reference(
                    "10.5678/shared",
                    "Creator. [Dataset]. doi:10.5678/shared",
                    occurrences=2,
                )
            ],
        )
        pub["content"]["reference_dois"][0]["occurrences"][0]["reference_text"] = (
            "Author. Ordinary article. doi:10.5678/shared"
        )
        contexts = extraction_module.contexts_from_corpus(corpus([pub]))
        registry = build_global_citation_target_registry(contexts, {"10.1234/source"})
        decision = registry["10.5678/shared"]
        self.assertEqual(decision.target_class, "DatasetResource")
        self.assertEqual(
            [item["occurrenceDecision"] for item in decision.declarations],
            ["untyped_scholarly_reference", "strong_dataset"],
        )

    def test_structural_type_labels_are_strong_but_title_language_is_not(self) -> None:
        """Only structural resource labels, not ordinary title wording, assign type."""
        strong_cases = {
            "[Dataset]": "DatasetResource",
            "[Data set]": "DatasetResource",
            "[Software]": "Tool",
            "[Computer software]": "Tool",
        }
        for label, expected in strong_cases.items():
            with self.subTest(label=label):
                doi = "10.5678/object"
                declaration = {"evidenceText": f"Creator. {label}. doi:{doi}"}
                target_class, _ = classify_cited_doi_target(doi, [declaration], set())
                self.assertEqual(target_class, expected)

        weak_cases = (
            "A miniature data repository on a small computer. doi:10.5678/article",
            "Evaluation of software version changes in hydrology. doi:10.5678/article",
            "An ordinary article discussing software tools and models. doi:10.5678/article",
        )
        for text in weak_cases:
            with self.subTest(text=text):
                target_class, _ = classify_cited_doi_target(
                    "10.5678/article", [{"evidenceText": text}], set()
                )
                self.assertEqual(target_class, "Paper")

    def test_scholarly_article_structure_prevents_label_based_retyping(self) -> None:
        """A journal citation remains Paper despite an adjacent loose artifact label."""
        text = (
            "Author. Article about a software package. *Journal of Open Source Software*, "
            "*3*(27), 821. [Software]. doi:10.5678/article"
        )
        target_class, reason = classify_cited_doi_target(
            "10.5678/article", [{"evidenceText": text}], set()
        )
        self.assertEqual((target_class, reason), ("Paper", "default_bibliographic_paper"))

    def test_consistent_and_conflicting_occurrence_aggregation(self) -> None:
        """Strong classes aggregate consistently and cross-class conflicts do not emit."""
        cases = (
            ("[Dataset]", "DatasetResource"),
            ("[Software]", "Tool"),
        )
        for label, expected in cases:
            declarations = [
                {"evidenceText": f"Creator {index}. {label}. doi:10.5678/object"}
                for index in range(2)
            ]
            with self.subTest(label=label):
                self.assertEqual(
                    classify_cited_doi_target("10.5678/object", declarations, set())[0],
                    expected,
                )

        conflict = [
            {"evidenceText": "Creator. [Dataset]. doi:10.5678/object"},
            {"evidenceText": "Creator. [Software]. doi:10.5678/object"},
        ]
        self.assertEqual(
            classify_cited_doi_target("10.5678/object", conflict, set()),
            (None, "conflicting_cited_doi_type"),
        )

    def test_curated_doi_always_wins_over_nonpaper_labels(self) -> None:
        """The curated DOI index has priority over every occurrence-level label."""
        doi = "10.5678/curated"
        target_class, reason = classify_cited_doi_target(
            doi,
            [{"evidenceText": f"Creator. [Software]. doi:{doi}"}],
            {doi},
        )
        self.assertEqual((target_class, reason), ("Paper", "curated_doi_match"))

    def test_ambiguous_and_conflicting_cited_dois_are_reported(self) -> None:
        """Ambiguous namespaces defer and conflicting strong types remain unresolved."""
        ambiguous = reference("10.5281/zenodo.1234", "Creator. doi:10.5281/zenodo.1234")
        conflict_a = reference("10.5678/object", "Creator. [Data set]. doi:10.5678/object")
        conflict_b = reference("10.5678/object", "Creator. [Software]. doi:10.5678/object")
        pubs = [
            publication("10.1234/a", references=[ambiguous, conflict_a]),
            publication("10.1234/b", references=[conflict_b]),
        ]
        output = self.extract(corpus(pubs))
        ambiguous_report = next(
            item
            for item in output["deferred"]
            if item["category"] == "ambiguous_cited_doi_type"
        )
        conflict_report = next(
            item
            for item in output["unresolved"]
            if item["category"] == "conflicting_cited_doi_type"
        )
        self.assertEqual(ambiguous_report["value"]["doi"], "10.5281/zenodo.1234")
        self.assertEqual(
            [
                item["occurrenceDecision"]
                for item in conflict_report["value"]["occurrenceDecisions"]
            ],
            ["strong_dataset", "strong_tool"],
        )
        target_classes = {node["class"] for node in output["nodes"] if node["canonicalKey"] == "doi:10.5678/object"}
        self.assertEqual(target_classes, set())

    def test_provider_prefixes_are_only_conservative_ambiguity_guards(self) -> None:
        """Generic repository namespaces never positively assign an artifact class."""
        dois = (
            "10.5281/zenodo.1234",
            "10.6084/m9.figshare.1234",
            "10.5061/dryad.abc12",
            "10.7910/dvn/abc123",
        )
        for doi in dois:
            with self.subTest(doi=doi):
                self.assertEqual(
                    classify_cited_doi_target(
                        doi, [{"evidenceText": f"Creator. doi:{doi}"}], set()
                    ),
                    (None, "ambiguous_cited_doi_type"),
                )

    def test_typed_repository_and_tool_citations_have_no_paper_relation(self) -> None:
        """Strong non-paper targets are preserved while their relation is deferred."""
        pub = publication(
            "10.1234/source",
            references=[
                reference("10.5678/repository", "Repository: doi:10.5678/repository"),
                reference("10.5678/software", "Creator. [Software]. doi:10.5678/software"),
            ],
        )
        output = self.extract(corpus([pub]))
        self.assertTrue(any(node["class"] == "Repository" for node in output["nodes"]))
        self.assertTrue(any(node["class"] == "Tool" for node in output["nodes"]))
        self.assertFalse(any(edge["relation"] in {"cites", "referencesDataset"} for edge in output["edges"]))
        self.assertEqual(
            {item["category"] for item in output["deferred"]},
            {"paper_repository_relation_not_declared", "paper_tool_relation_requires_semantic_context"},
        )

    def test_self_reference_is_skipped_without_loop(self) -> None:
        """Source DOI artifacts produce a skipped record and no cites self-loop."""
        pub = publication("10.1234/source", references=[reference("10.1234/source", "How to cite doi:10.1234/source")])
        output = self.extract(corpus([pub]))
        self.assertTrue(any(item["category"] == "self_reference_doi_matches_source" for item in output["skipped"]))
        self.assertFalse(any(edge["relation"] == "cites" for edge in output["edges"]))

    def test_deferred_phase_a_doi_warning_remains_audit_only(self) -> None:
        """A deferred Phase A DOI candidate creates no citation fact or Identifier node."""

        candidate = "10.7777/deferred-candidate"
        pub = publication("10.1234/source")
        pub["reconciliation"]["warnings"].append(
            {
                "category": "deferred_reference_doi_candidate",
                "detail": {
                    "action": "defer",
                    "context": "reference",
                    "candidate": candidate,
                    "reason": "Unresolved exact local boundary evidence.",
                    "evidence_text": f"Citation {candidate}",
                    "source_artifact": pub["canonical_artifact_id"],
                    "source_location": {
                        **source_location(12, "References"),
                        "source_artifact": pub["canonical_artifact_id"],
                    },
                },
            }
        )
        output = self.extract(corpus([pub]))
        semantic_output = json.dumps(
            {"nodes": output["nodes"], "edges": output["edges"]},
            sort_keys=True,
        )
        self.assertNotIn(candidate, semantic_output)
        self.assertFalse(
            any(edge["relation"] in {"cites", "referencesDataset"} for edge in output["edges"])
        )
        self.assertEqual(output["stats"]["sourceReferenceDoiCount"], 0)
        self.assertEqual(output["stats"]["citationRecordsProcessed"], 0)
        warning = next(
            item
            for item in output["warnings"]
            if item["category"] == "deferred_reference_doi_candidate"
        )
        self.assertEqual(warning["value"]["candidate"], candidate)

    def test_correction_resolves_curated_target(self) -> None:
        """A curated correction target produces one deterministic corrects edge."""
        pubs = [publication("10.1234/original"), publication("10.1234/correction", correction_of="10.1234/original")]
        output = self.extract(corpus(pubs))
        edge = next(edge for edge in output["edges"] if edge["relation"] == "corrects")
        self.assertEqual(edge["inventoryId"], "C-P22")

    def test_hydroshare_availability_creates_exact_dataset(self) -> None:
        """An exact HydroShare resource creates DatasetResource and usesDataset."""
        url = "https://www.hydroshare.org/resource/0123456789abcdef0123456789abcdef/"
        output = self.extract(corpus([publication("10.1234/source", availability_records=[availability("url", url)])]))
        self.assertTrue(any(node["canonicalKey"] == "hydroshare:0123456789abcdef0123456789abcdef" for node in output["nodes"]))
        self.assertTrue(any(edge["relation"] == "usesDataset" for edge in output["edges"]))
        self.assertFalse(any(node["class"] == "DatasetMention" for node in output["nodes"]))

    def test_generic_data_availability_is_source_scoped_mention(self) -> None:
        """A generic pure-data URL remains a paper-scoped DatasetMention."""
        output = self.extract(corpus([publication("10.1234/source", availability_records=[availability("url", "https://example.org/data")])]))
        mentions = [node for node in output["nodes"] if node["class"] == "DatasetMention"]
        self.assertEqual(len(mentions), 1)
        self.assertEqual(mentions[0]["identityRegime"], "paper_availability_mention")

    def test_data_availability_precedes_global_paper_typing(self) -> None:
        """A data DOI remains a scoped mention even when cited globally as a Paper."""
        doi = "10.5678/shared"
        pub = publication(
            "10.1234/source",
            references=[reference(doi, f"Ordinary article. doi:{doi}")],
            availability_records=[availability("doi", doi)],
        )
        output = self.extract(corpus([pub]))
        target_classes = {
            node["class"] for node in output["nodes"] if node["canonicalKey"] == f"doi:{doi}"
        }
        self.assertEqual(target_classes, {"Paper", "DatasetMention"})
        self.assertTrue(any(edge["relation"] == "cites" for edge in output["edges"]))
        self.assertTrue(any(edge["relation"] == "usesDataset" for edge in output["edges"]))
        self.assertFalse(
            any(
                item["category"] == "availability_identifier_already_typed_paper"
                for item in output["deferred"]
            )
        )

    def test_strong_dataset_target_is_reused_in_data_availability(self) -> None:
        """A strongly cited DatasetResource is reused by pure data availability."""
        doi = "10.5678/strong-dataset"
        pub = publication(
            "10.1234/source",
            references=[reference(doi, f"Example archive [Dataset]. doi:{doi}")],
            availability_records=[availability("doi", doi)],
        )
        output = self.extract(corpus([pub]))
        datasets = [
            node
            for node in output["nodes"]
            if node["canonicalKey"] == f"doi:{doi}" and node["class"] == "DatasetResource"
        ]
        self.assertEqual(len(datasets), 1)
        self.assertFalse(
            any(
                node["class"] == "DatasetMention"
                and node["canonicalKey"] == f"doi:{doi}"
                for node in output["nodes"]
            )
        )
        self.assertTrue(
            any(
                edge["relation"] == "referencesDataset" and edge["target"] == datasets[0]["id"]
                for edge in output["edges"]
            )
        )
        uses_edge = next(
            edge
            for edge in output["edges"]
            if edge["relation"] == "usesDataset"
            and edge["target"] == datasets[0]["id"]
        )
        self.assertEqual(uses_edge["attributes"]["identifierValue"], doi)
        self.assertEqual(
            uses_edge["internalLineage"]["phaseAField"],
            "content.availability_identifiers[0]",
        )
        declaration_fields = {
            item["phaseAField"]
            for item in datasets[0]["attributes"]["sourceDeclarations"]
        }
        self.assertEqual(
            declaration_fields,
            {
                "content.reference_dois[0].occurrences[0]",
                "content.availability_identifiers[0]",
            },
        )
        identifiers = [
            node
            for node in output["nodes"]
            if node["class"] == "Identifier"
            and node["canonicalKey"] == f"doi:{doi}"
        ]
        self.assertEqual(len(identifiers), 1)
        self.assertTrue(
            any(
                edge["relation"] == "usesDataset"
                and edge["target"] == datasets[0]["id"]
                for edge in output["edges"]
            )
        )

    def test_non_dataset_citation_types_do_not_override_data_mentions(self) -> None:
        """Ambiguous, Repository, and Tool DOI decisions remain scoped mentions."""
        cases = (
            ("10.5281/zenodo.999999", "Ordinary archive citation."),
            ("10.5678/repository", "Example artifact [Repository]."),
            ("10.5678/software", "Example artifact [Software]."),
        )
        for doi, label in cases:
            with self.subTest(doi=doi):
                pub = publication(
                    "10.1234/source",
                    references=[reference(doi, f"{label} doi:{doi}")],
                    availability_records=[availability("doi", doi)],
                )
                output = self.extract(corpus([pub]))
                matches = [
                    node
                    for node in output["nodes"]
                    if node["canonicalKey"] == f"doi:{doi}"
                ]
                self.assertEqual(
                    sum(node["class"] == "DatasetMention" for node in matches), 1
                )
                self.assertFalse(
                    any(node["class"] == "DatasetResource" for node in matches)
                )
    def test_github_availability_creates_repository_without_paper_edge(self) -> None:
        """An exact GitHub root creates Repository identity and a deferred relation."""
        output = self.extract(corpus([publication("10.1234/source", availability_records=[availability("url", "https://github.com/Owner/Repo/tree/main")])]))
        self.assertTrue(any(node["class"] == "Repository" for node in output["nodes"]))
        self.assertTrue(any(item["category"] == "paper_repository_relation_not_declared" for item in output["deferred"]))
        self.assertFalse(any(edge["source"].startswith("publication:paper:") and edge["relation"] not in {"hasIdentifier", "hasAuthor", "publishedIn", "hasSubject"} for edge in output["edges"]))

    def test_github_case_variants_share_one_consistent_identity(self) -> None:
        """Case-only variants and subpaths merge under one Repository identity."""
        records = [
            availability("url", "https://github.com/Owner/Repo/tree/main", line=20),
            availability("url", "https://github.com/owner/repo.git?tab=readme", line=21),
        ]
        output = self.extract(
            corpus([publication("10.1234/source", availability_records=records)])
        )
        repositories = [node for node in output["nodes"] if node["class"] == "Repository"]
        self.assertEqual(len(repositories), 1)
        repository = repositories[0]
        identity_url = "https://github.com/owner/repo"
        self.assertEqual(repository["canonicalKey"], f"url:{identity_url}")
        self.assertEqual(
            repository["id"],
            f"publication:repository:{stable_hash(f'github-repo-url|{identity_url}')}",
        )
        self.assertEqual(len(repository["attributes"]["sourceDeclarations"]), 2)
        identifiers = [
            node
            for node in output["nodes"]
            if node["class"] == "Identifier"
            and node["canonicalKey"] == f"url:{identity_url}"
        ]
        self.assertEqual(len(identifiers), 1)

    def test_github_display_identity_is_order_independent(self) -> None:
        """Source-form display attributes are deterministic under input reordering."""
        upper = publication(
            "10.1234/upper",
            availability_records=[
                availability("url", "https://github.com/Owner/Repo/issues/1", line=20)
            ],
        )
        lower = publication(
            "10.1234/lower",
            availability_records=[
                availability("url", "https://github.com/owner/repo", line=21)
            ],
        )
        outputs = [
            self.extract(corpus(list(publications)))
            for publications in ((upper, lower), (lower, upper))
        ]
        repositories = [
            next(node for node in output["nodes"] if node["class"] == "Repository")
            for output in outputs
        ]
        self.assertEqual(repositories[0], repositories[1])
        self.assertEqual(
            serialize_deterministically(outputs[0]),
            serialize_deterministically(outputs[1]),
        )

    def test_distinct_github_repositories_remain_distinct(self) -> None:
        """Case folding does not merge different GitHub repository roots."""
        output = self.extract(
            corpus(
                [
                    publication(
                        "10.1234/source",
                        availability_records=[
                            availability("url", "https://github.com/owner/one", line=20),
                            availability("url", "https://github.com/owner/two", line=21),
                        ],
                    )
                ]
            )
        )
        repositories = [node for node in output["nodes"] if node["class"] == "Repository"]
        self.assertEqual(len(repositories), 2)
        self.assertEqual(
            {node["canonicalKey"] for node in repositories},
            {"url:https://github.com/owner/one", "url:https://github.com/owner/two"},
        )

    def test_mixed_generic_availability_is_deferred(self) -> None:
        """A generic mixed data/code identifier does not imply an ontology target."""
        records = (
            availability("url", "https://example.org/archive", "data_and_code_availability"),
            availability("doi", "10.5678/archive", "code_and_data_availability"),
        )
        for record in records:
            with self.subTest(scheme=record["identifier_scheme"]):
                output = self.extract(
                    corpus([publication("10.1234/source", availability_records=[record])])
                )
                self.assertTrue(
                    any(
                        item["category"] == "availability_mixed_target_type"
                        for item in output["deferred"]
                    )
                )
                self.assertFalse(
                    any(node["class"] == "DatasetMention" for node in output["nodes"])
                )

    def test_provenance_separates_public_evidence_and_local_lineage(self) -> None:
        """Public evidence is URL-only while local files remain in lineage."""
        output = self.extract(corpus([publication("10.1234/source", keywords=["Hydrology"])]))
        for record in [*output["nodes"], *output["edges"]]:
            self.assertEqual(set(record["evidence"]), set(EVIDENCE_REQUIRED_KEYS))
            self.assertNotIn("data/raw", json.dumps(record["evidence"]))
        self.assertTrue(any("data/raw" in json.dumps(node["internalLineage"]) for node in output["nodes"]))
        self.assertFalse(any("data/raw" in json.dumps(node["attributes"]) for node in output["nodes"]))

    def test_ontology_registry_rejects_wrong_binding_and_domain(self) -> None:
        """Runtime validation rejects absent inventory pairs and bad signatures."""
        with self.assertRaises(ValueError):
            self.ontology.class_entry("Paper", "A-D01")
        with self.assertRaises(ValueError):
            self.ontology.validate_edge("referencesDataset", "C-P29", "Paper", "Paper")

    def test_graph_builder_rejects_conflicting_duplicate_node(self) -> None:
        """A duplicate node ID cannot silently overwrite conflicting content."""
        builder = GraphBuilder("1.0.9", self.ontology)
        base = Node("x", "Paper", "A-P01", {"title": "A"}, "doi:10.1/a", "doi", CURATED, {key: "x" for key in EVIDENCE_REQUIRED_KEYS}, {"phaseAField": "x"})
        builder.emit_node(base)
        with self.assertRaises(ValueError):
            builder.emit_node(copy.deepcopy(base).__class__(**{**base.__dict__, "attributes": {"title": "B"}}))

    def test_graph_builder_rejects_conflicting_duplicate_edge(self) -> None:
        """A semantic edge ID cannot carry conflicting edge attributes."""
        output = self.extract(corpus([publication("10.1234/source")]))
        edge_record = next(edge for edge in output["edges"] if edge["relation"] == "hasAuthor")
        builder = GraphBuilder("1.0.9", self.ontology)
        for node_record in output["nodes"]:
            if node_record["id"] in {edge_record["source"], edge_record["target"]}:
                builder.nodes[node_record["id"]] = copy.deepcopy(node_record)
        edge = Edge(
            edge_record["id"], edge_record["relation"], edge_record["inventoryId"],
            edge_record["source"], edge_record["target"], edge_record["attributes"],
            edge_record["evidence"], edge_record["internalLineage"],
        )
        builder.emit_edge(edge)
        conflicting = copy.deepcopy(edge)
        conflicting.attributes = {"authorPosition": 99}
        with self.assertRaises(ValueError):
            builder.emit_edge(conflicting)

    def test_field_dispositions_cover_current_schema(self) -> None:
        """All current Phase A field groups have explicit mapping dispositions."""
        value = corpus([publication("10.1234/source")])
        self.assertEqual(validate_field_coverage(value), [])
        self.assertIn("content.reference_dois[]", FIELD_DISPOSITIONS)
        self.assertIn("content.availability_identifiers[]", FIELD_DISPOSITIONS)

    def test_validation_rejects_domain_and_control_character_corruption(self) -> None:
        """Output validation independently catches ontology and string corruption."""
        value = corpus([publication("10.1234/source", keywords=["Hydrology"])])
        output = self.extract(value)
        corrupted = copy.deepcopy(output)
        corrupted["nodes"][0]["attributes"]["bad"] = "control\x01"
        issues = validate_output(corrupted, value, self.ontology)
        self.assertTrue(any("control character" in issue for issue in issues))
        bad_edge = copy.deepcopy(output)
        subject = next(node for node in bad_edge["nodes"] if node["class"] == "Subject")
        author_edge = next(edge for edge in bad_edge["edges"] if edge["relation"] == "hasAuthor")
        author_edge["target"] = subject["id"]
        author_edge["id"] = make_edge_id(author_edge["source"], "hasAuthor", subject["id"])
        bad_edge["edges"] = sorted(bad_edge["edges"], key=lambda item: item["id"])
        self.assertTrue(any("Range violation" in issue for issue in validate_output(bad_edge, value, self.ontology)))

    def test_failed_validation_preserves_existing_output(self) -> None:
        """The CLI never replaces an existing artifact after input validation fails."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "invalid.json"
            output_path = root / "existing.json"
            input_path.write_text('{"schema_version":"bad"}\n', encoding="utf-8")
            original = b'{"valid":"previous"}\n'
            output_path.write_bytes(original)
            status = main(["--input", str(input_path), "--output", str(output_path), "--log-level", "ERROR"])
            self.assertNotEqual(status, 0)
            self.assertEqual(output_path.read_bytes(), original)

    def test_failed_output_validation_preserves_existing_output(self) -> None:
        """A generated-but-invalid output is never installed over a valid artifact."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "valid.json"
            output_path = root / "existing.json"
            input_path.write_text(
                json.dumps(corpus([publication("10.1234/source")])), encoding="utf-8"
            )
            original = b'{"valid":"previous"}\n'
            output_path.write_bytes(original)
            with mock.patch.object(
                extraction_module,
                "validate_output",
                return_value=["forced output validation failure"],
            ):
                status = main(
                    [
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                        "--log-level",
                        "ERROR",
                    ]
                )
            self.assertNotEqual(status, 0)
            self.assertEqual(output_path.read_bytes(), original)

    def test_deterministic_serialization_is_input_order_independent(self) -> None:
        """Publication ordering cannot affect serialized Phase B bytes."""
        pubs = [publication("10.1234/a", keywords=["Water"]), publication("10.1234/b", keywords=["Flow"])]
        first = serialize_deterministically(self.extract(corpus(pubs)))
        second = serialize_deterministically(self.extract(corpus(list(reversed(pubs)))))
        self.assertEqual(first, second)

    def test_independent_process_builds_are_byte_identical(self) -> None:
        """Two separately spawned frozen-corpus builds produce identical bytes."""
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            command = [
                sys.executable,
                str(PROJECT_ROOT / "src/extraction/deterministic/extract_publication.py"),
                "--input",
                str(FROZEN_CORPUS),
                "--ontology-spec",
                str(DEFAULT_ONTOLOGY_SPEC),
                "--validate-frozen-snapshot",
                "--log-level",
                "ERROR",
            ]
            subprocess.run([*command, "--output", str(first)], check=True)
            subprocess.run([*command, "--output", str(second)], check=True)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_production_contains_no_snapshot_specific_exception_values(self) -> None:
        """Regression DOI values and paper IDs remain test data, never branches."""
        production = (
            PROJECT_ROOT / "src/extraction/deterministic/extract_publication.py"
        ).read_text(encoding="utf-8")
        regression_values = {
            "10.1002/2017wr021290",
            "10.1038/s41467-021-26107-z",
            "10.3390/electronics6010001",
            "10.3189/172756404781814825",
            "10.21105/joss.00821",
            "10.5066/p9uddhvd",
            "10.3334/ornldaac/2129",
            "10.5067/0ggpb220ex6a",
            "10.7265/n5tb14tc",
            "10.5281/zenodo.10183449",
            "10.24381/cds.adbb2d47",
            "10.25914/5fdb0902607e1",
            "10.5065/d6mw2f4d",
            "10.5067/modis/mcd12q1.006",
            "10.5281/zenodo.14827983",
            "10.5281/zenodo.4602277",
            "10.5281/zenodo.6326394",
        }
        for value in regression_values:
            self.assertNotIn(value, production)
        self.assertNotRegex(production, r"if\s+.*bibliographic.*\[.[\"'](?:title|venue)")

    def test_frozen_corpus_contract_anchors_and_accounting(self) -> None:
        """The complete frozen corpus satisfies every declared backbone anchor."""
        value, source_hash = load_json(FROZEN_CORPUS)
        output = extract_corpus(
            value,
            self.ontology,
            source_corpus_sha256=source_hash,
            validate_frozen_snapshot=True,
        )
        stats = output["stats"]
        self.assertEqual(output["schema_version"], "1.0.0")
        self.assertEqual(output["phase_b_version"], "1.0.2")
        self.assertEqual(output["source_phase_a_version"], "1.0.9")
        self.assertEqual(stats["sourcePublicationCount"], 228)
        self.assertEqual(source_hash, "6bce89579cb250d4ba94525bc31c327cc1ae7bdb48b71091cb648fd0502f1e25")
        self.assertEqual(FROZEN_CORPUS.stat().st_size, 18711023)
        self.assertEqual(stats["sourceReferenceDoiCount"], 8856)
        self.assertEqual(stats["sourceReferenceDoiOccurrenceCount"], 8963)
        self.assertEqual(stats["citationRecordsProcessed"], 8856)
        self.assertEqual(stats["sourceAvailabilityIdentifierCount"], 299)
        self.assertEqual(stats["availabilityRecordsProcessed"], 299)
        self.assertEqual(stats["nodesByClass"]["Person"], 1602)
        self.assertEqual(stats["nodesByClass"]["Venue"], 84)
        self.assertEqual(stats["nodesByClass"]["Subject"], 317)
        self.assertEqual(stats["edgesByRelation"]["hasAuthor"], 1602)
        self.assertEqual(stats["edgesByRelation"]["hasSubject"], 373)
        self.assertEqual(stats["edgesByInventoryId"]["C-P04"], 455)
        self.assertEqual(stats["edgesByInventoryId"]["C-P22"], 1)
        self.assertEqual(stats["citationSelfReferencesSkipped"], 23)
        self.assertNotIn("D-05", stats["edgesByInventoryId"])
        nodes_by_key: dict[str, list[dict[str, Any]]] = {}
        nodes_by_id: dict[str, dict[str, Any]] = {}
        for node in output["nodes"]:
            nodes_by_key.setdefault(node["canonicalKey"], []).append(node)
            nodes_by_id[node["id"]] = node
        edges_by_target: dict[str, list[dict[str, Any]]] = {}
        for edge in output["edges"]:
            edges_by_target.setdefault(edge["target"], []).append(edge)

        false_type_dois = {
            "10.1002/2017wr021290",
            "10.1038/s41467-021-26107-z",
            "10.3390/electronics6010001",
            "10.3189/172756404781814825",
            "10.21105/joss.00821",
        }
        for doi in false_type_dois:
            with self.subTest(false_type_doi=doi):
                matches = nodes_by_key[f"doi:{doi}"]
                paper = next(node for node in matches if node["class"] == "Paper")
                self.assertEqual({node["class"] for node in matches}, {"Paper"})
                self.assertTrue(
                    any(edge["relation"] == "cites" for edge in edges_by_target[paper["id"]])
                )

        contaminated_ambiguous_doi = "10.5281/zenodo.10183449"
        self.assertNotIn(f"doi:{contaminated_ambiguous_doi}", nodes_by_key)
        self.assertTrue(
            any(
                item["category"] == "ambiguous_cited_doi_type"
                and item["value"]["doi"] == contaminated_ambiguous_doi
                for item in output["deferred"]
            )
        )

        reused_availability_doi = "10.5066/p9uddhvd"
        reused_matches = nodes_by_key[f"doi:{reused_availability_doi}"]
        reused_resource = next(
            node for node in reused_matches if node["class"] == "DatasetResource"
        )
        self.assertNotIn("DatasetMention", {node["class"] for node in reused_matches})
        self.assertTrue(
            any(
                edge["relation"] == "usesDataset"
                for edge in edges_by_target[reused_resource["id"]]
            )
        )

        availability_dois = {
            "10.3334/ornldaac/2129",
            "10.5067/0ggpb220ex6a",
            "10.7265/n5tb14tc",
        }
        for doi in availability_dois:
            with self.subTest(availability_doi=doi):
                mentions = [
                    node
                    for node in nodes_by_key[f"doi:{doi}"]
                    if node["class"] == "DatasetMention"
                ]
                self.assertEqual(len(mentions), 1)
                self.assertTrue(
                    any(
                        edge["relation"] == "usesDataset"
                        for edge in edges_by_target[mentions[0]["id"]]
                    )
                )
        dataset_identifier_keys = {
            node["canonicalKey"]
            for node in output["nodes"]
            if node["class"] == "DatasetResource"
        }
        dataset_identifier_keys.update(
            nodes_by_id[edge["target"]]["canonicalKey"]
            for edge in output["edges"]
            if edge["relation"] == "hasIdentifier"
            and nodes_by_id[edge["source"]]["class"] == "DatasetResource"
        )
        mention_keys = {
            node["canonicalKey"]
            for node in output["nodes"]
            if node["class"] == "DatasetMention"
        }
        self.assertFalse(dataset_identifier_keys & mention_keys)
        self.assertFalse(
            any(
                item["category"] == "availability_identifier_already_typed_paper"
                for item in output["deferred"]
            )
        )

        deferred_warnings = [
            item
            for item in output["warnings"]
            if item["category"] == "deferred_reference_doi_candidate"
        ]
        self.assertEqual(len(deferred_warnings), 4)
        for warning in deferred_warnings:
            candidate = warning["value"]["candidate"].casefold()
            self.assertFalse(
                any(
                    node["canonicalKey"] == f"doi:{candidate}"
                    or node["attributes"].get("doi") == candidate
                    or (
                        node["class"] == "Identifier"
                        and node["attributes"].get("scheme") == "doi"
                        and node["attributes"].get("normalizedValue") == candidate
                    )
                    for node in output["nodes"]
                )
            )
            self.assertFalse(
                any(edge["attributes"].get("doi") == candidate for edge in output["edges"])
            )
        self.assertEqual(validate_output(output, value, self.ontology, validate_frozen_snapshot=True), [])


if __name__ == "__main__":
    unittest.main()
