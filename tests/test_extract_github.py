"""Focused tests for the deterministic GitHub Phase B extractor."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.extraction.deterministic.extract_github import (
    CURATED,
    Evidence,
    GraphBuilder,
    InternalLineage,
    Node,
    build_blob_url,
    canonicalize_package_name,
    classify_github_url,
    extract_corpus,
    extract_hydroshare_resource_id,
    is_concrete_version,
    load_corpus,
    make_edge_id,
    normalize_doi,
    normalize_github_repo_url,
    normalize_software_license_declaration,
    select_primary_source,
    stable_hash,
    stable_json,
    validate_output,
    write_output,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = PROJECT_ROOT / "data/interim/coderepos/github_phaseB_sample_repos.json"
FULL_INPUT = PROJECT_ROOT / "data/interim/coderepos/ciroh_github_corpus.json"


def empty_reference() -> dict[str, object]:
    """Return the fixed empty Phase A citation-reference shape."""
    return {
        "type": None,
        "authors": [],
        "doi": None,
        "title": None,
        "journal": None,
        "year": None,
        "volume": None,
        "number": None,
        "start": None,
        "end": None,
        "publisher": None,
        "url": None,
    }


def empty_citation() -> dict[str, object]:
    """Return the fixed empty Phase A citation shape."""
    return {
        "present": False,
        "format": "none",
        "placeholder": False,
        "source_path": None,
        "cff_version": None,
        "type": None,
        "title": None,
        "software_authors": [],
        "doi": None,
        "version": None,
        "date_released": None,
        "url": None,
        "repository_code": None,
        "repository": None,
        "keywords": [],
        "license": None,
        "abstract": None,
        "preferred_citation": empty_reference(),
        "references": [],
    }


def structured_citation() -> dict[str, object]:
    """Return a valid non-placeholder CFF citation shell for synthetic tests."""
    citation = empty_citation()
    citation.update(
        {
            "present": True,
            "format": "cff",
            "source_path": "CITATION.cff",
            "cff_version": "1.2.0",
            "type": "software",
            "title": "Synthetic software",
        }
    )
    return citation


def typed_reference(reference_type: str, doi: str, title: str) -> dict[str, object]:
    """Return one DOI-bearing structured CFF reference."""
    reference = empty_reference()
    reference.update({"type": reference_type, "doi": doi, "title": title})
    return reference


def add_repository_doi(repo: dict[str, object], doi: str) -> None:
    """Append one repository-level DOI Identifier declaration."""
    repo["identifiers"].append(
        {"id_type": "doi", "value": doi, "source_path": "CITATION.cff:doi"}
    )


def file_record(path: str, downloaded: bool = False, file_role: str = "other") -> dict[str, object]:
    """Build one synthetic Phase A file inventory record."""
    file_name = path.rsplit("/", 1)[-1]
    extension = Path(file_name).suffix
    return {
        "path": path,
        "file_name": file_name,
        "extension": extension,
        "size_bytes": 10,
        "downloaded": downloaded,
        "selection_reason": "test" if downloaded else None,
        "file_role": file_role,
        "source_path": f"files_manifest.json:{path}",
    }


def make_repo(repo_id: int, name: str) -> dict[str, object]:
    """Build a complete synthetic Phase A repository record."""
    full_name = f"example/{name}"
    html_url = f"https://github.com/{full_name}"
    sha = f"{repo_id:040x}"[-40:]
    return {
        "repo_id": repo_id,
        "name": name,
        "full_name": full_name,
        "html_url": html_url,
        "description": None,
        "homepage": None,
        "default_branch": "main",
        "language": "Python",
        "topics": [],
        "fork": False,
        "fork_parent": None,
        "archived": False,
        "disabled": False,
        "visibility": "public",
        "timestamps": {"created_at": None, "updated_at": None, "pushed_at": None},
        "github_stats": {
            "size_kb": 0,
            "stargazers_count": 0,
            "watchers_count": 0,
            "forks_count": 0,
            "open_issues_count": 0,
        },
        "archive": {
            "frozen_commit_sha": sha,
            "downloaded_at_epoch": 1.0,
            "archive_format": "zip",
        },
        "license": None,
        "identifiers": [
            {
                "id_type": "commit_sha",
                "value": sha,
                "source_path": "archive_info.json:frozen_commit_sha",
            },
            {
                "id_type": "repo_url",
                "value": html_url,
                "source_path": "repo_metadata.json:html_url",
            },
        ],
        "contributors": [],
        "files": {
            "total_count": 0,
            "downloaded_count": 0,
            "selection_reason_histogram": {},
            "has_dockerfile": False,
            "inventory": [],
            "downloaded": [],
            "dockerfiles": [],
        },
        "dependencies": [],
        "repo_dependencies": [],
        "execution_environment": [],
        "citation": empty_citation(),
        "citation_md": None,
        "software_metadata": [],
        "readme": {
            "present": False,
            "source_path": None,
            "text": None,
            "deterministic_urls": {"hydroshare": [], "github": [], "dois": [], "other": []},
        },
        "provenance": {
            "source_artifact": f"{html_url}/tree/{sha}",
            "phase_a_version": "1.1.0",
            "manifest_classifications": {},
            "parse_warnings": [],
        },
    }


def set_inventory(repo: dict[str, object], records: list[dict[str, object]]) -> None:
    """Install authoritative inventory and derived views on a synthetic repository."""
    ordered = sorted(records, key=lambda item: str(item["path"]))
    downloaded = [dict(item) for item in ordered if item["downloaded"]]
    dockerfiles = [
        {"path": item["path"], "file_name": item["file_name"], "size_bytes": item["size_bytes"]}
        for item in ordered
        if item["file_role"] == "dockerfile"
    ]
    reasons: dict[str, int] = {}
    for item in ordered:
        key = str(item["selection_reason"])
        reasons[key] = reasons.get(key, 0) + 1
    repo["files"] = {
        "total_count": len(ordered),
        "downloaded_count": len(downloaded),
        "selection_reason_histogram": dict(sorted(reasons.items())),
        "has_dockerfile": bool(dockerfiles),
        "inventory": ordered,
        "downloaded": downloaded,
        "dockerfiles": dockerfiles,
    }


def make_corpus(*repos: dict[str, object]) -> dict[str, object]:
    """Build a supported synthetic Phase A corpus."""
    return {"schema_version": "1.1.0", "repos": list(repos)}


def vcs_dependency(url: str, subdirectory: str | None, egg: str | None) -> dict[str, object]:
    """Build one complete Phase A VCS dependency record."""
    return {
        "name": egg or "component",
        "raw": f"component @ git+{url}",
        "version_spec": None,
        "extras": [],
        "marker": None,
        "ecosystem": "pypi",
        "dep_group": "runtime",
        "is_vcs": True,
        "vcs_url": url,
        "ref": "main",
        "subdirectory": subdirectory,
        "egg": egg,
        "sources": [
            {
                "manifest_path": "pyproject.toml",
                "manifest_type": "pyproject_toml",
                "manifest_scope": "root",
                "raw_line": f"component @ git+{url}",
            }
        ],
    }


def software_metadata_record(
    name: str,
    source_path: str,
    license_value: object,
) -> dict[str, object]:
    """Build one complete synthetic Phase A software-metadata record."""
    return {
        "name": name,
        "version": None,
        "authors": [],
        "urls": {},
        "license": license_value,
        "manifest_type": "pyproject_toml",
        "source_path": source_path,
    }


class HelperTests(unittest.TestCase):
    """Test deterministic canonicalizers and evidence selectors."""

    def test_stable_sha256_id_generation(self) -> None:
        """Stable hashes use SHA-256 and exactly 20 lowercase characters."""
        expected = hashlib.sha256(b"alpha").hexdigest()[:20]
        self.assertEqual(stable_hash("alpha"), expected)
        self.assertRegex(stable_hash("alpha"), r"^[0-9a-f]{20}$")

    def test_github_repository_url_normalization(self) -> None:
        """HTTPS, .git, git+HTTPS, SSH, query, and fragments normalize identically."""
        expected = "https://github.com/Owner/Repo"
        cases = [
            "https://github.com/Owner/Repo",
            "https://github.com/Owner/Repo.git",
            "git+https://github.com/Owner/Repo.git",
            "git@github.com:Owner/Repo.git",
            "ssh://git@github.com/Owner/Repo.git",
            "https://github.com/Owner/Repo?tab=readme#section",
        ]
        self.assertEqual([normalize_github_repo_url(value) for value in cases], [expected] * len(cases))

    def test_github_url_classification(self) -> None:
        """Repository roots and non-root GitHub URL classes remain distinct."""
        self.assertEqual(classify_github_url("https://github.com/a/b"), "repository_root")
        self.assertEqual(classify_github_url("https://github.com/a/b/blob/main/x.py"), "blob_tree")
        self.assertEqual(classify_github_url("https://github.com/a/b/issues/1"), "issues")
        self.assertEqual(classify_github_url("https://github.com/a/b/actions/workflows/x/badge.svg"), "actions_badge")
        self.assertEqual(classify_github_url("https://raw.githubusercontent.com/a/b/main/x"), "raw_asset")

    def test_blob_url_path_encoding(self) -> None:
        """Blob URLs preserve slash and case while percent-encoding path segments."""
        url = build_blob_url("https://github.com/A/B", "abc", "Docs/My File+#.md")
        self.assertEqual(url, "https://github.com/A/B/blob/abc/Docs/My%20File%2B%23.md")

    def test_doi_normalization_and_badge_rejection(self) -> None:
        """DOIs normalize while badge and image candidates are rejected."""
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC.9."), "10.1234/abc.9")
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC.9?source=test"), "10.1234/abc.9")
        self.assertIsNone(normalize_doi("https://example.org/badge/DOI/10.1234/test.svg"))
        self.assertIsNone(normalize_doi("10.1234/test.png"))

    def test_hydroshare_resource_id_extraction(self) -> None:
        """Only exact 32-character HydroShare resource IDs are accepted."""
        resource_id = "0123456789abcdef0123456789abcdef"
        self.assertEqual(
            extract_hydroshare_resource_id(f"https://www.hydroshare.org/resource/{resource_id}/"),
            resource_id,
        )
        self.assertIsNone(extract_hydroshare_resource_id("https://hydroshare.org/resource/short"))

    def test_package_name_canonicalization(self) -> None:
        """Package names canonicalize deterministically by ecosystem."""
        self.assertEqual(canonicalize_package_name("My_Package.Name", "pypi"), "my-package-name")
        self.assertEqual(canonicalize_package_name("My_Package.Name", "conda"), "my-package-name")

    def test_primary_evidence_ordering(self) -> None:
        """Root, docs, example, path, and raw line determine primary evidence."""
        sources = [
            {"manifest_scope": "example", "manifest_path": "examples/r.txt", "raw_line": "z"},
            {"manifest_scope": "root", "manifest_path": "z.txt", "raw_line": "b"},
            {"manifest_scope": "root", "manifest_path": "a.txt", "raw_line": "c"},
            {"manifest_scope": "root", "manifest_path": "a.txt", "raw_line": "a"},
        ]
        primary, ordered = select_primary_source(sources)
        self.assertEqual(primary["raw_line"], "a")
        self.assertEqual(ordered[0], primary)

    def test_concrete_and_dynamic_versions(self) -> None:
        """Literal versions are concrete while expressions remain deferred."""
        self.assertTrue(is_concrete_version("1.2.3"))
        self.assertFalse(is_concrete_version("attr: package.__version__"))
        self.assertFalse(is_concrete_version("${VERSION}"))

    def test_software_license_normalization_cases(self) -> None:
        """Plain, structured, serialized, empty, file, and unsupported licenses are distinct."""
        cases = [
            ("MIT", "text", "MIT"),
            ({"text": "MIT"}, "text", "MIT"),
            ({"text": "DOC"}, "text", "DOC"),
            ({"text": ""}, "empty_text", None),
            ({"file": "LICENSE"}, "file", "LICENSE"),
            ({"unknown": "value"}, "unsupported", None),
            ("{'text': 'MIT'}", "text", "MIT"),
            ("{'file': 'LICENSE'}", "file", "LICENSE"),
        ]
        for value, expected_kind, expected_value in cases:
            with self.subTest(value=value):
                disposition = normalize_software_license_declaration(value)
                self.assertEqual(disposition.kind, expected_kind)
                self.assertEqual(disposition.normalized_value, expected_value)


class SyntheticExtractionTests(unittest.TestCase):
    """Test rule behavior using source-agnostic synthetic Phase A records."""

    def test_human_contributor_and_bot_behavior(self) -> None:
        """Humans create Person nodes and bots create only skipped records."""
        repo = make_repo(1, "contributors")
        repo["contributors"] = [
            {
                "github_id": 10,
                "login": "human",
                "html_url": "https://github.com/human",
                "type": "User",
                "contributions": 2,
                "is_bot": False,
                "source_path": "contributors.json[0]",
            },
            {
                "github_id": 11,
                "login": "automation[bot]",
                "html_url": "https://github.com/apps/automation",
                "type": "Bot",
                "contributions": 1,
                "is_bot": True,
                "source_path": "contributors.json[1]",
            },
        ]
        corpus = make_corpus(repo)
        output = extract_corpus(copy.deepcopy(corpus))
        people = [node for node in output["nodes"] if node["class"] == "Person"]
        self.assertEqual([node["attributes"]["login"] for node in people], ["human"])
        self.assertIn("bot_contributor_excluded", {item["reason"] for item in output["skipped"]})

    def test_valid_and_placeholder_cff(self) -> None:
        """Valid CFF seeds semantic nodes while placeholder CFF seeds none."""
        valid = make_repo(2, "valid-cff")
        placeholder = make_repo(3, "placeholder-cff")
        for repo, is_placeholder in ((valid, False), (placeholder, True)):
            citation_file = file_record("CITATION.cff", True, "citation_cff")
            set_inventory(repo, [citation_file])
            citation = empty_citation()
            citation.update(
                {
                    "present": True,
                    "format": "cff",
                    "placeholder": is_placeholder,
                    "source_path": "CITATION.cff",
                    "cff_version": "1.2.0",
                    "title": "FIXME" if is_placeholder else "Structured Tool",
                    "software_authors": [
                        {
                            "family_names": "Author",
                            "given_names": "Valid",
                            "orcid": None,
                            "affiliation": "Example University",
                            "email": None,
                        },
                        {
                            "family_names": "Second",
                            "given_names": "Valid",
                            "orcid": None,
                            "affiliation": "Example University",
                            "email": None,
                        },
                    ],
                    "version": "1.0.0",
                    "license": "MIT",
                }
            )
            repo["citation"] = citation
        output = extract_corpus(make_corpus(valid, placeholder))
        placeholder_semantic = [
            node
            for node in output["nodes"]
            if node["attributes"].get("sourceRepoId") == 3
            and node["class"] in {"Person", "Organization", "Tool", "License", "ModelVersion", "Paper"}
        ]
        self.assertFalse(placeholder_semantic)
        self.assertTrue(any(node["class"] == "Tool" and node["attributes"].get("sourceRepoId") == 2 for node in output["nodes"]))
        valid_organizations = [
            node
            for node in output["nodes"]
            if node["class"] == "Organization" and node["attributes"].get("sourceRepoId") == 2
        ]
        self.assertEqual(len(valid_organizations), 1)
        valid_people = {
            node["id"]
            for node in output["nodes"]
            if node["class"] == "Person"
            and node["attributes"].get("sourceRepoId") == 2
            and node["attributes"].get("role") == "softwareAuthor"
        }
        affiliation_edges = [
            edge
            for edge in output["edges"]
            if edge["relation"] == "affiliatedWith" and edge["source"] in valid_people
        ]
        self.assertEqual(len(valid_people), 2)
        self.assertEqual(len(affiliation_edges), 2)
        self.assertEqual({edge["source"] for edge in affiliation_edges}, valid_people)
        self.assertEqual({edge["target"] for edge in affiliation_edges}, {valid_organizations[0]["id"]})
        self.assertEqual(
            {edge["internalLineage"]["phaseAField"] for edge in affiliation_edges},
            {
                "citation.software_authors[0].affiliation",
                "citation.software_authors[1].affiliation",
            },
        )
        expected_location = (
            f"{valid['html_url']}/blob/{valid['archive']['frozen_commit_sha']}/CITATION.cff"
        )
        self.assertEqual(
            {edge["evidence"]["sourceLocation"] for edge in affiliation_edges},
            {expected_location},
        )

    def test_structured_license_text_semantics_and_scope_deduplication(self) -> None:
        """Plain/structured MIT deduplicate within scope while DOC remains custom text."""
        repo = make_repo(15, "licenses-text")
        set_inventory(
            repo,
            [
                file_record("pyproject.toml", True, "dependency_manifest"),
                file_record("packages/tool/pyproject.toml", True, "dependency_manifest"),
                file_record("packages/doc/pyproject.toml", True, "dependency_manifest"),
            ],
        )
        repo["software_metadata"] = [
            software_metadata_record("same-tool", "pyproject.toml", "MIT"),
            software_metadata_record("same-tool", "packages/tool/pyproject.toml", {"text": "MIT"}),
            software_metadata_record("doc-tool", "packages/doc/pyproject.toml", {"text": "DOC"}),
        ]
        corpus = make_corpus(repo)
        output = extract_corpus(copy.deepcopy(corpus))
        licenses = [node for node in output["nodes"] if node["class"] == "License"]
        self.assertEqual(len(licenses), 2)
        mit = next(node for node in licenses if node["attributes"]["declaration"] == "MIT")
        doc = next(node for node in licenses if node["attributes"]["declaration"] == "DOC")
        self.assertEqual(mit["canonicalKey"], "spdx:MIT")
        self.assertEqual(mit["identityRegime"], "spdx")
        self.assertEqual(len(mit["attributes"]["sourceDeclarations"]), 2)
        self.assertEqual(doc["identityRegime"], "custom_license_declaration")
        conflicts = [
            item for item in output["warnings"] if item["reason"] == "license_declaration_conflict"
        ]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["value"], ["doc", "mit"])
        self.assertEqual(output, extract_corpus(copy.deepcopy(corpus)))

    def test_nonsemantic_structured_licenses_are_reported_not_nodalized(self) -> None:
        """Empty, file-pointer, and unsupported mappings create reports but no License nodes."""
        repo = make_repo(16, "licenses-nonsemantic")
        set_inventory(
            repo,
            [
                file_record("empty.toml", True, "dependency_manifest"),
                file_record("file.toml", True, "dependency_manifest"),
                file_record("unsupported.toml", True, "dependency_manifest"),
                file_record("LICENSE", False, "license"),
            ],
        )
        repo["license"] = {
            "key": "apache-2.0",
            "name": "Apache License 2.0",
            "spdx_id": "Apache-2.0",
            "url": "https://api.github.com/licenses/apache-2.0",
            "is_spdx": True,
            "source_path": "repo_metadata.json:license",
        }
        repo["software_metadata"] = [
            software_metadata_record("empty", "empty.toml", {"text": ""}),
            software_metadata_record("file", "file.toml", {"file": "LICENSE"}),
            software_metadata_record("unsupported", "unsupported.toml", {"other": "value"}),
        ]
        output = extract_corpus(make_corpus(repo))
        licenses = [node for node in output["nodes"] if node["class"] == "License"]
        self.assertEqual(len(licenses), 1)
        self.assertEqual(licenses[0]["canonicalKey"], "spdx:Apache-2.0")
        deferred = {record["reason"]: record["value"] for record in output["deferred"]}
        skipped = {record["reason"]: record["value"] for record in output["skipped"]}
        self.assertEqual(deferred["license_file_reference_requires_content_resolution"], "LICENSE")
        self.assertEqual(deferred["unsupported_structured_license_mapping"], {"other": "value"})
        self.assertEqual(skipped["empty_structured_license_text"], {"text": ""})
        self.assertNotIn("license_declaration_conflict", {item["reason"] for item in output["warnings"]})
        self.assertEqual(sum(node["class"] == "File" and node["attributes"]["path"] == "LICENSE" for node in output["nodes"]), 1)

    def test_archived_repository_without_identifier_has_no_archive_deferral(self) -> None:
        """Archived status remains an attribute but cannot create an empty archive candidate."""
        repo = make_repo(17, "archived-without-id")
        repo["archived"] = True
        output = extract_corpus(make_corpus(repo))
        repository = next(node for node in output["nodes"] if node["class"] == "Repository")
        self.assertTrue(repository["attributes"]["archived"])
        self.assertFalse(any(edge["relation"] == "archivedAs" for edge in output["edges"]))
        self.assertFalse(
            any(
                record["reason"] == "archived_as_requires_cross_module_identifier_match"
                for record in output["deferred"]
            )
        )

    def test_archived_repository_with_doi_has_normalized_archive_deferral(self) -> None:
        """A valid DOI candidate is retained in normalized form for later alignment."""
        repo = make_repo(18, "archived-with-doi")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        repo["identifiers"].append(
            {
                "id_type": "doi",
                "value": "https://doi.org/10.1234/ARCHIVE.1",
                "source_path": "CITATION.cff:doi",
            }
        )
        output = extract_corpus(make_corpus(repo))
        repository = next(
            node
            for node in output["nodes"]
            if node["class"] == "Repository" and node["curationStatus"] == "curated"
        )
        self.assertTrue(repository["attributes"]["archived"])
        record = next(
            record
            for record in output["deferred"]
            if record["reason"] == "archived_as_requires_cross_module_identifier_match"
        )
        self.assertEqual(record["value"], ["10.1234/archive.1"])

    def test_preferred_citation_doi_is_excluded_from_archive_candidates(self) -> None:
        """A preferred-citation Paper DOI remains identified but is not an archive candidate."""
        repo = make_repo(181, "preferred-paper-doi")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        doi = "10.1234/PREFERRED.1"
        add_repository_doi(repo, doi)
        citation = structured_citation()
        citation["preferred_citation"] = typed_reference("article", doi, "Preferred paper")
        repo["citation"] = citation
        output = extract_corpus(make_corpus(repo))
        doi_key = "doi:10.1234/preferred.1"
        identifier = next(
            node
            for node in output["nodes"]
            if node["class"] == "Identifier" and node["canonicalKey"] == doi_key
        )
        paper = next(
            node for node in output["nodes"] if node["class"] == "Paper" and node["canonicalKey"] == doi_key
        )
        self.assertTrue(
            any(edge["relation"] == "hasIdentifier" and edge["target"] == identifier["id"] for edge in output["edges"])
        )
        self.assertTrue(
            any(edge["relation"] == "referencePublication" and edge["target"] == paper["id"] for edge in output["edges"])
        )
        self.assertFalse(
            any(record["reason"] == "archived_as_requires_cross_module_identifier_match" for record in output["deferred"])
        )

    def test_article_reference_doi_is_excluded_from_archive_candidates(self) -> None:
        """An article-like reference DOI is Paper-typed before archive disposition."""
        repo = make_repo(182, "reference-paper-doi")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        doi = "10.1234/REFERENCE.1"
        add_repository_doi(repo, doi)
        citation = structured_citation()
        citation["references"] = [typed_reference("journal-article", doi, "Referenced paper")]
        repo["citation"] = citation
        output = extract_corpus(make_corpus(repo))
        self.assertTrue(
            any(node["class"] == "Paper" and node["canonicalKey"] == "doi:10.1234/reference.1" for node in output["nodes"])
        )
        self.assertFalse(
            any(record["reason"] == "archived_as_requires_cross_module_identifier_match" for record in output["deferred"])
        )

    def test_dataset_reference_doi_is_excluded_from_archive_candidates(self) -> None:
        """A dataset-typed structured DOI cannot become an archive candidate."""
        repo = make_repo(183, "dataset-doi")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        doi = "10.1234/DATASET.1"
        add_repository_doi(repo, doi)
        citation = structured_citation()
        citation["references"] = [typed_reference("dataset", doi, "Structured dataset")]
        repo["citation"] = citation
        output = extract_corpus(make_corpus(repo))
        self.assertTrue(
            any(
                node["class"] == "DatasetResource" and node["canonicalKey"] == "doi:10.1234/dataset.1"
                for node in output["nodes"]
            )
        )
        self.assertTrue(any(edge["relation"] == "referencesDataset" for edge in output["edges"]))
        self.assertFalse(
            any(record["reason"] == "archived_as_requires_cross_module_identifier_match" for record in output["deferred"])
        )

    def test_mixed_typed_and_unresolved_archive_candidates(self) -> None:
        """Only an untyped repository DOI remains in a mixed archive candidate set."""
        repo = make_repo(184, "mixed-dois")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        paper_doi = "10.1234/PAPER.A"
        dataset_doi = "10.1234/DATA.B"
        unresolved_doi = "10.1234/SOFTWARE.C"
        for doi in (paper_doi, dataset_doi, unresolved_doi):
            add_repository_doi(repo, doi)
        citation = structured_citation()
        citation["preferred_citation"] = typed_reference("article", paper_doi, "Paper")
        citation["references"] = [typed_reference("dataset", dataset_doi, "Dataset")]
        repo["citation"] = citation
        first = extract_corpus(make_corpus(repo))
        record = next(
            record
            for record in first["deferred"]
            if record["reason"] == "archived_as_requires_cross_module_identifier_match"
        )
        self.assertEqual(record["value"], ["10.1234/software.c"])
        second = extract_corpus(make_corpus(copy.deepcopy(repo)))
        self.assertEqual(stable_json(first), stable_json(second))

    def test_validation_rejects_paper_typed_archive_candidate(self) -> None:
        """Validation reconstructs structured DOI typing from Phase A input."""
        repo = make_repo(185, "invalid-typed-archive")
        repo["archived"] = True
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        doi = "10.1234/TYPED.1"
        add_repository_doi(repo, doi)
        citation = structured_citation()
        citation["preferred_citation"] = typed_reference("article", doi, "Typed paper")
        repo["citation"] = citation
        corpus = make_corpus(repo)
        output = extract_corpus(copy.deepcopy(corpus))
        output["deferred"].append(
            {
                "repoId": 185,
                "repoName": "invalid-typed-archive",
                "category": "deferred",
                "sourcePath": "identifiers",
                "value": ["10.1234/typed.1"],
                "reason": "archived_as_requires_cross_module_identifier_match",
            }
        )
        issues = validate_output(output, corpus)
        self.assertTrue(
            any(
                "repoId=185" in issue
                and "DOI='10.1234/typed.1'" in issue
                and "citation.preferred_citation.doi" in issue
                for issue in issues
            )
        )

    def test_validation_rejects_malformed_license_and_empty_archive_report(self) -> None:
        """Independent validation rejects dict-string licenses and empty archive candidates."""
        repo = make_repo(19, "invalid-output")
        set_inventory(repo, [file_record("pyproject.toml", True, "dependency_manifest")])
        repo["software_metadata"] = [
            software_metadata_record("tool", "pyproject.toml", "MIT")
        ]
        corpus = make_corpus(repo)
        output = extract_corpus(copy.deepcopy(corpus))
        license_node = next(node for node in output["nodes"] if node["class"] == "License")
        license_node["attributes"]["declaration"] = "{'text': 'MIT'}"
        license_node["attributes"]["name"] = "{'text': 'MIT'}"
        license_node["canonicalKey"] = "license-declaration:{'text': 'mit'}"
        output["deferred"].append(
            {
                "repoId": 19,
                "repoName": "invalid-output",
                "category": "deferred",
                "sourcePath": "identifiers",
                "value": [],
                "reason": "archived_as_requires_cross_module_identifier_match",
            }
        )
        issues = validate_output(output, corpus)
        self.assertTrue(any("malformed Python-dictionary license" in issue for issue in issues))
        self.assertTrue(any("empty identifier value" in issue for issue in issues))

    def test_external_vcs_target_resolution(self) -> None:
        """An in-corpus exact VCS target resolves to its curated Repository."""
        source = make_repo(4, "source")
        target = make_repo(5, "target")
        set_inventory(source, [file_record("pyproject.toml", True, "dependency_manifest")])
        source["repo_dependencies"] = [vcs_dependency(str(target["html_url"]), None, None)]
        output = extract_corpus(make_corpus(target, source))
        edges = [edge for edge in output["edges"] if edge["relation"] == "dependsOnRepository"]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["target"], "github:repo:5")
        self.assertFalse(any(node["id"].startswith("github:repo-ref:4:") for node in output["nodes"]))

    def test_monorepo_self_reference(self) -> None:
        """A component-qualified self VCS reference becomes Dependency + dependsOn."""
        repo = make_repo(6, "monorepo")
        set_inventory(repo, [file_record("pyproject.toml", True, "dependency_manifest")])
        repo["repo_dependencies"] = [vcs_dependency(str(repo["html_url"]), "packages/core", "core")]
        output = extract_corpus(make_corpus(repo))
        self.assertTrue(any(node["identityRegime"] == "internal_vcs_subpackage" for node in output["nodes"]))
        self.assertTrue(any(edge["relation"] == "dependsOn" for edge in output["edges"]))
        self.assertFalse(any(edge["relation"] == "dependsOnRepository" for edge in output["edges"]))

    def test_uninformative_self_reference(self) -> None:
        """A component-free self VCS reference emits no edge and becomes unresolved."""
        repo = make_repo(7, "self-reference")
        set_inventory(repo, [file_record("pyproject.toml", True, "dependency_manifest")])
        repo["repo_dependencies"] = [vcs_dependency(str(repo["html_url"]), None, None)]
        output = extract_corpus(make_corpus(repo))
        self.assertFalse(any(edge["relation"] == "dependsOnRepository" for edge in output["edges"]))
        self.assertIn("self_vcs_reference_without_component", {item["reason"] for item in output["unresolved"]})

    def test_one_file_per_inventory_entry(self) -> None:
        """Downloaded and non-downloaded entries each produce exactly one File and hasFile."""
        repo = make_repo(8, "files")
        set_inventory(
            repo,
            [file_record("README.md", True, "readme"), file_record("src/code.py", False, "source")],
        )
        output = extract_corpus(make_corpus(repo))
        files = [node for node in output["nodes"] if node["class"] == "File"]
        self.assertEqual(len(files), 2)
        self.assertEqual(sum(node["attributes"]["contentAvailable"] for node in files), 1)
        self.assertEqual(sum(edge["relation"] == "hasFile" for edge in output["edges"]), 2)

    def test_public_provenance_and_internal_lineage(self) -> None:
        """Public evidence uses blob URLs while raw filenames remain internal lineage."""
        repo = make_repo(9, "provenance")
        set_inventory(repo, [file_record("Docs/A File.md", False, "documentation")])
        output = extract_corpus(make_corpus(repo))
        node = next(node for node in output["nodes"] if node["class"] == "File")
        self.assertIn("/blob/", node["evidence"]["sourceLocation"])
        self.assertIn("Docs/A%20File.md", node["evidence"]["sourceLocation"])
        self.assertNotIn("files_manifest.json", node["evidence"]["sourceLocation"])
        self.assertIn("files_manifest.json", node["internalLineage"]["rawSource"])

    def test_duplicate_node_and_edge_conflicts(self) -> None:
        """Conflicting content under one deterministic node/edge ID fails loudly."""
        builder = GraphBuilder()
        evidence = Evidence("x", "https://example.org/x", "https://example.org", "v")
        lineage = InternalLineage("field", "1.1.0")
        first = Node("n", "Tool", "A-DOM02", {"name": "a"}, "a", "r", CURATED, evidence, lineage)
        second = Node("n", "Tool", "A-DOM02", {"name": "b"}, "a", "r", CURATED, evidence, lineage)
        builder.emit_node(first)
        with self.assertRaises(ValueError):
            builder.emit_node(second)
        builder.add_edge("implementedBy", "D-22", "n", "n2", {}, evidence, lineage)
        with self.assertRaises(ValueError):
            builder.add_edge("implementedBy", "D-22", "n", "n2", {"changed": True}, evidence, lineage)

    def test_deterministic_repeated_extraction(self) -> None:
        """Repeated extraction and serialization are byte-identical."""
        repo = make_repo(10, "deterministic")
        set_inventory(repo, [file_record("README.md", False, "readme")])
        corpus = make_corpus(repo)
        first = extract_corpus(copy.deepcopy(corpus))
        second = extract_corpus(copy.deepcopy(corpus))
        first_bytes = (json.dumps(first, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        second_bytes = (json.dumps(second, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.assertEqual(first_bytes, second_bytes)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output.json"
            write_output(first, output_path)
            self.assertEqual(output_path.read_bytes(), first_bytes)

    def test_repository_input_order_independence(self) -> None:
        """Reversing Phase A repository order does not alter Phase B output."""
        source = make_repo(13, "order-source")
        target = make_repo(14, "order-target")
        set_inventory(source, [file_record("pyproject.toml", True, "dependency_manifest")])
        source["repo_dependencies"] = [vcs_dependency(str(target["html_url"]), None, None)]
        forward = extract_corpus(make_corpus(source, target))
        reverse = extract_corpus(make_corpus(target, source))
        self.assertEqual(forward, reverse)

    def test_structured_cff_paper_and_dataset_references(self) -> None:
        """Typed CFF references create Paper/Dataset stubs and declared edges."""
        repo = make_repo(11, "structured-references")
        set_inventory(repo, [file_record("CITATION.cff", True, "citation_cff")])
        citation = empty_citation()
        article = empty_reference()
        article.update(
            {
                "type": "article",
                "doi": "https://doi.org/10.1234/EXAMPLE.1",
                "title": "Structured publication",
                "authors": [
                    {"family_names": "Author", "given_names": "Paper", "orcid": None}
                ],
            }
        )
        resource_id = "0123456789abcdef0123456789abcdef"
        dataset = empty_reference()
        dataset.update(
            {
                "type": "dataset",
                "title": "Structured dataset",
                "url": f"https://www.hydroshare.org/resource/{resource_id}/",
            }
        )
        citation.update(
            {
                "present": True,
                "format": "cff",
                "source_path": "CITATION.cff",
                "cff_version": "1.2.0",
                "title": "Structured software",
                "references": [article, dataset],
            }
        )
        repo["citation"] = citation
        output = extract_corpus(make_corpus(repo))
        self.assertEqual(sum(node["class"] == "Paper" for node in output["nodes"]), 1)
        self.assertEqual(sum(node["class"] == "DatasetResource" for node in output["nodes"]), 1)
        self.assertEqual(sum(edge["relation"] == "citesPaper" for edge in output["edges"]), 1)
        self.assertEqual(sum(edge["relation"] == "referencesDataset" for edge in output["edges"]), 1)
        self.assertEqual(sum(edge["relation"] == "hasAuthor" for edge in output["edges"]), 1)

    def test_exact_external_fork_parent_becomes_stub(self) -> None:
        """An exact external fork parent creates a referenced endpoint and forkedFrom."""
        repo = make_repo(12, "fork")
        repo["fork"] = True
        repo["fork_parent"] = "https://github.com/external/upstream"
        output = extract_corpus(make_corpus(repo))
        edge = next(edge for edge in output["edges"] if edge["relation"] == "forkedFrom")
        target = next(node for node in output["nodes"] if node["id"] == edge["target"])
        self.assertEqual(target["curationStatus"], "referenced")
        self.assertEqual(target["canonicalKey"], "https://github.com/external/upstream")


@unittest.skipUnless(SAMPLE_INPUT.exists(), "frozen Phase B sample is unavailable")
class FrozenSampleIntegrationTests(unittest.TestCase):
    """Run executable validation against the frozen ten-repository sample."""

    @classmethod
    def setUpClass(cls) -> None:
        """Extract the sample once for all integration assertions."""
        cls.corpus = load_corpus(SAMPLE_INPUT)
        cls.output = extract_corpus(copy.deepcopy(cls.corpus))

    def test_sample_regression_anchors_and_sweml_file(self) -> None:
        """Sample repository, File, hasFile, and SWEML record anchors hold."""
        stats = self.output["stats"]
        self.assertEqual(stats["inputRepositoryCount"], 10)
        self.assertEqual(stats["nodesByClass"]["Repository"] - stats["repositoryStubCount"], 10)
        self.assertEqual(stats["fileNodeCount"], 4962)
        self.assertEqual(self.output["stats"]["edgesByRelation"]["hasFile"], 4962)
        sweml = next(repo for repo in self.corpus["repos"] if repo["name"] == "SWEML")
        node = next(
            node
            for node in self.output["nodes"]
            if node["class"] == "File"
            and node["attributes"]["sourceRepoId"] == sweml["repo_id"]
            and node["attributes"]["path"] == ".github/actions/README.md"
        )
        self.assertFalse(node["attributes"]["downloaded"])
        self.assertFalse(node["attributes"]["contentAvailable"])
        self.assertEqual(node["attributes"]["fileRole"], "readme")
        self.assertIn(f"/blob/{sweml['archive']['frozen_commit_sha']}/.github/actions/README.md", node["evidence"]["sourceLocation"])

    def test_sample_semantic_guards_and_validation(self) -> None:
        """Sample target resolution, citation, bot, placeholder, and validation guards pass."""
        self.assertFalse(
            any(
                edge["relation"] == "dependsOnRepository" and edge["source"] == edge["target"]
                for edge in self.output["edges"]
            )
        )
        self.assertFalse(any(node["attributes"].get("login") == "dependabot[bot]" for node in self.output["nodes"]))
        reasons = {record["reason"] for record in self.output["deferred"] + self.output["skipped"]}
        self.assertIn("citation_md_deferred_to_llm", reasons)
        self.assertIn("cff_placeholder_excluded", reasons)
        paper_authors = {
            node["id"]
            for node in self.output["nodes"]
            if node["class"] == "Person" and node["attributes"].get("moduleRoleId") == "A-P03"
        }
        self.assertTrue(paper_authors)
        self.assertFalse(
            any(
                edge["relation"] == "hasContributor" and edge["target"] in paper_authors
                for edge in self.output["edges"]
            )
        )
        self.assertFalse(validate_output(self.output, self.corpus))

    def test_sample_repeated_hashes_match(self) -> None:
        """Two sample extractions have identical deterministic SHA-256 hashes."""
        second = extract_corpus(copy.deepcopy(self.corpus))
        first_bytes = (json.dumps(self.output, sort_keys=True, ensure_ascii=False) + "\n").encode()
        second_bytes = (json.dumps(second, sort_keys=True, ensure_ascii=False) + "\n").encode()
        self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), hashlib.sha256(second_bytes).hexdigest())


@unittest.skipUnless(FULL_INPUT.exists(), "full Phase A corpus is unavailable")
class FrozenFullCorrectionRegressionTests(unittest.TestCase):
    """Exercise correction invariants on the frozen full corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        """Extract the full corpus once for correction-specific assertions."""
        cls.corpus = load_corpus(FULL_INPUT)
        cls.output = extract_corpus(copy.deepcopy(cls.corpus))

    def test_training_ngiab_affiliation_edges_keep_author_lineage(self) -> None:
        """All four shared-affiliation edges preserve their own CFF author indices."""
        repo = next(repo for repo in self.corpus["repos"] if repo["name"] == "training-NGIAB-101")
        people = {
            node["id"]
            for node in self.output["nodes"]
            if node["class"] == "Person"
            and node["attributes"].get("sourceRepoId") == repo["repo_id"]
            and node["attributes"].get("affiliation")
        }
        edges = [
            edge
            for edge in self.output["edges"]
            if edge["relation"] == "affiliatedWith" and edge["source"] in people
        ]
        self.assertEqual(len(people), 4)
        self.assertEqual(len(edges), 4)
        self.assertEqual(len({edge["target"] for edge in edges}), 1)
        self.assertEqual(
            {edge["internalLineage"]["phaseAField"] for edge in edges},
            {
                "citation.software_authors[0].affiliation",
                "citation.software_authors[1].affiliation",
                "citation.software_authors[2].affiliation",
                "citation.software_authors[3].affiliation",
            },
        )

    def test_full_corrections_have_no_malformed_or_empty_records(self) -> None:
        """Full output contains no dict-string License or empty archive candidate."""
        for node in self.output["nodes"]:
            if node["class"] != "License":
                continue
            semantic_text = stable_json(
                {
                    "canonicalKey": node["canonicalKey"],
                    "name": node["attributes"].get("name"),
                    "declaration": node["attributes"].get("declaration"),
                }
            )
            self.assertNotIn("{'text':", semantic_text)
            self.assertNotIn("{'file':", semantic_text)
            self.assertTrue(str(node["attributes"].get("declaration") or "").strip())
        self.assertFalse(
            any(
                record["reason"] == "archived_as_requires_cross_module_identifier_match"
                and not record["value"]
                for record in self.output["deferred"]
            )
        )

    def test_neuralhydrology_publication_doi_is_not_an_archive_candidate(self) -> None:
        """The frozen publication DOI retains its graph facts without archive deferral."""
        repo = next(repo for repo in self.corpus["repos"] if repo["name"] == "neuralhydrology")
        doi_key = "doi:10.21105/joss.04050"
        repository_id = f"github:repo:{repo['repo_id']}"
        paper = next(
            node for node in self.output["nodes"] if node["class"] == "Paper" and node["canonicalKey"] == doi_key
        )
        repository_identifier = next(
            node
            for node in self.output["nodes"]
            if node["class"] == "Identifier"
            and node["canonicalKey"] == doi_key
            and any(
                edge["relation"] == "hasIdentifier"
                and edge["source"] == repository_id
                and edge["target"] == node["id"]
                for edge in self.output["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["relation"] == "hasIdentifier"
                and edge["source"] == repository_id
                and edge["target"] == repository_identifier["id"]
                for edge in self.output["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["relation"] == "referencePublication"
                and edge["source"] == repository_id
                and edge["target"] == paper["id"]
                for edge in self.output["edges"]
            )
        )
        self.assertFalse(
            any(
                record["reason"] == "archived_as_requires_cross_module_identifier_match"
                and record["repoId"] == repo["repo_id"]
                and "10.21105/joss.04050" in record["value"]
                for record in self.output["deferred"]
            )
        )


if __name__ == "__main__":
    unittest.main()
