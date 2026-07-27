"""Tests for deterministic CIROH Hub Phase A preprocessing."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.preprocessing.build_ciroh_hub_corpus import (
    BASE_URL,
    CorpusBuildError,
    build_canonical_url,
    build_corpus,
    build_page_record,
    classify_link,
    discover_candidate_files,
    extract_external_content_sources,
    extract_headings,
    extract_links,
    mask_html_image_tags,
    mask_nonvisible_content,
    normalize_date,
    parse_front_matter,
    resolve_parent_urls,
    serialize_corpus,
    validate_corpus,
    write_deterministic_json,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_RAW = PROJECT_ROOT / "data/raw/documents"


def page_text(front_matter: str, body: str = "") -> str:
    """Return one complete synthetic MDX page."""
    return f"---\n{front_matter.rstrip()}\n---\n{body}"


def write_page(raw_root: Path, relative: str, front_matter: str, body: str = "") -> Path:
    """Write a synthetic page fixture and return its path."""
    path = raw_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page_text(front_matter, body), encoding="utf-8")
    return path


class HubPhaseAUnitTests(unittest.TestCase):
    """Exercise contract rules with source-agnostic synthetic fixtures."""

    def test_front_matter_parsing_and_body_separation(self) -> None:
        """Safe YAML parsing preserves unknown keys and separates the body."""
        parsed, body = parse_front_matter(
            page_text('title: "Page"\ncustom: [one, two]', "\n# Heading\r\nBody\r\n"),
            "docs/page.mdx",
        )
        self.assertEqual(parsed, {"title": "Page", "custom": ["one", "two"]})
        self.assertEqual(body, "\n# Heading\nBody\n")

    def test_invalid_front_matter_rejected(self) -> None:
        """Malformed or absent front matter is never silently skipped."""
        with self.assertRaises(CorpusBuildError):
            parse_front_matter("# no front matter\n", "docs/bad.mdx")
        with self.assertRaises(CorpusBuildError):
            parse_front_matter("---\nitems: [\n---\n", "docs/bad-yaml.mdx")

    def test_canonical_url_rules(self) -> None:
        """Every source group follows its ratified URL construction rule."""
        self.assertEqual(
            build_canonical_url("generated_js_page", "_generated_js_pages/page.mdx", "contribute", None),
            f"{BASE_URL}/contribute",
        )
        self.assertEqual(
            build_canonical_url("src_page", "src/pages/home.mdx", "/", None),
            f"{BASE_URL}/",
        )
        self.assertEqual(
            build_canonical_url("docs", "docs/contribute/index.mdx", "docs/contribute/index", None),
            f"{BASE_URL}/docs/contribute/",
        )
        self.assertEqual(
            build_canonical_url("docs", "docs/contribute/page.mdx", "docs/contribute/page", None),
            f"{BASE_URL}/docs/contribute/page",
        )
        self.assertEqual(
            build_canonical_url("blog", "blog/post.mdx", "ignored", "post-slug"),
            f"{BASE_URL}/blog/post-slug",
        )
        self.assertEqual(
            build_canonical_url("release_notes", "release-notes/post.mdx", "ignored", "v1"),
            f"{BASE_URL}/release-notes/v1",
        )

    def test_segment_encoding_and_no_double_encoding(self) -> None:
        """Path segments encode spaces once while preserving separators and case."""
        expected = f"{BASE_URL}/docs/products/data-management/dataaccess/NWMURL%20Library"
        self.assertEqual(
            build_canonical_url(
                "docs",
                "docs/products/data-management/dataaccess/NWMURL Library.mdx",
                "docs/products/data-management/dataaccess/NWMURL Library",
                None,
            ),
            expected,
        )
        self.assertEqual(
            build_canonical_url(
                "docs",
                "docs/products/data-management/dataaccess/NWMURL Library.mdx",
                "docs/products/data-management/dataaccess/NWMURL%20Library",
                None,
            ),
            expected,
        )

    def test_blog_and_release_note_require_slug(self) -> None:
        """Blog and release-note candidates without slugs fail validation."""
        with self.assertRaises(CorpusBuildError):
            build_canonical_url("blog", "blog/post.mdx", "blog/post", None)
        with self.assertRaises(CorpusBuildError):
            build_canonical_url("release_notes", "release-notes/post.mdx", "release-notes/post", None)

    def test_title_fallbacks_and_date_normalization(self) -> None:
        """Page construction applies all title fallbacks and normalizes dates."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            front = write_page(root, "docs/front.mdx", 'title: Explicit\npath: docs/front', "\n# H1\n")
            h1 = write_page(root, "docs/h1.mdx", 'path: docs/h1', "\n# Heading title\n")
            description = write_page(root, "docs/description.mdx", 'description: Description title\npath: docs/description')
            fallback = write_page(root, "docs/path-name.mdx", 'path: docs/path-name')
            self.assertEqual(build_page_record(front, root)["title_source"], "front_matter")
            self.assertEqual(build_page_record(h1, root)["title_source"], "first_h1")
            self.assertEqual(build_page_record(description, root)["title_source"], "description")
            fallback_record = build_page_record(fallback, root)
            self.assertEqual(fallback_record["title"], "Path name")
            self.assertEqual(fallback_record["title_source"], "path_fallback")
            self.assertEqual(fallback_record["warnings"][0]["issue"], "title_from_path_fallback")
        warnings: list[dict[str, str]] = []
        self.assertEqual(normalize_date("02/04/2026", "x", warnings), ("2026-02-04", "02/04/2026"))
        self.assertEqual(warnings, [])

    def test_heading_extraction_ignores_fences_and_builds_hierarchy(self) -> None:
        """Headings retain source order, line numbers, and nearest lower-level parents."""
        content = "# One\n## Two\n```md\n# Not a heading\n```\n### Three\n## Four\n"
        headings = extract_headings(content)
        self.assertEqual([item["text"] for item in headings], ["One", "Two", "Three", "Four"])
        self.assertEqual([item["source_line"] for item in headings], [1, 2, 6, 7])
        self.assertEqual([item["parent_heading_ordinal"] for item in headings], [None, 1, 2, 1])

    def test_html_comments_are_masked_for_all_structural_extractors(self) -> None:
        """Inline and multiline HTML comments cannot contribute structure."""
        content = (
            "# Visible before <!-- hidden tail -->\n"
            "<!--\n"
            "# Hidden heading\n"
            "[Hidden link](https://example.org/hidden)\n"
            '<GitHubReadme username="hidden" repo="hidden" />\n'
            "-->\n"
            "[Visible link](https://example.org/visible) <!-- [Inline hidden](https://example.org/no) -->\n"
            '<GitHubReadme username="visible" repo="visible" />\n'
        )
        headings = extract_headings(content)
        warnings: list[dict[str, str]] = []
        sources = extract_external_content_sources(content, "docs/page.mdx", warnings)
        links = extract_links(content, f"{BASE_URL}/docs/page", headings)
        self.assertEqual([item["text"] for item in headings], ["Visible before"])
        self.assertEqual([item["raw_target"] for item in links], ["https://example.org/visible"])
        self.assertEqual([item["repository"] for item in sources], ["visible"])
        self.assertEqual(headings[0]["source_line"], 1)
        self.assertEqual(links[0]["source_line"], 7)

    def test_mdx_comments_are_masked_for_all_structural_extractors(self) -> None:
        """Inline and multiline MDX comments cannot contribute structure."""
        content = (
            "{/*\n"
            "# Hidden heading\n"
            "[Hidden link](https://example.org/hidden)\n"
            '<GitHubWikiPage username="hidden" repo="hidden" path="Hidden" />\n'
            "*/}\n"
            "## Visible {/* [Inline hidden](https://example.org/no) */}\n"
            "[Visible](https://example.org/visible)\n"
            '<GitHubWikiPage username="visible" repo="visible" path="Visible" />\n'
        )
        headings = extract_headings(content)
        warnings: list[dict[str, str]] = []
        sources = extract_external_content_sources(content, "docs/page.mdx", warnings)
        links = extract_links(content, f"{BASE_URL}/docs/page", headings)
        self.assertEqual([item["text"] for item in headings], ["Visible"])
        self.assertEqual([item["raw_target"] for item in links], ["https://example.org/visible"])
        self.assertEqual([item["repository"] for item in sources], ["visible"])
        self.assertEqual(headings[0]["source_line"], 6)

    def test_comment_markers_inside_fence_do_not_mask_later_content(self) -> None:
        """Comment-like code remains inert and cannot leak comment state past a fence."""
        content = (
            "```md\n"
            "<!-- never closes here\n"
            "{/* neither does this\n"
            "```\n"
            "# Visible after fence\n"
            "[Visible](https://example.org/visible)\n"
        )
        masked = mask_nonvisible_content(content)
        headings = extract_headings(content)
        links = extract_links(content, f"{BASE_URL}/docs/page", headings)
        self.assertEqual(len(masked), len(content))
        self.assertEqual(masked.count("\n"), content.count("\n"))
        self.assertEqual([item["text"] for item in headings], ["Visible after fence"])
        self.assertEqual([item["raw_target"] for item in links], ["https://example.org/visible"])

    def test_link_extraction_and_classification(self) -> None:
        """Supported links are extracted, classified, resolved, and associated with headings."""
        content = (
            "# Links\n"
            "[Hub](/docs/a) [GitHub](https://github.com/org/repo) <https://doi.org/10.1/x>\n"
            '<a href="mailto:test@example.org">Email</a> <Thing url="https://hydroshare.org/resource/id/" />\n'
            "![Image](https://example.org/image.png)\n"
            "```\n[Hidden](https://example.org)\n```\n"
        )
        headings = extract_headings(content)
        links = extract_links(content, f"{BASE_URL}/docs/page", headings)
        self.assertEqual(len(links), 5)
        self.assertEqual(
            [item["link_type"] for item in links],
            ["hub_internal", "github", "doi", "mailto", "hydroshare"],
        )
        self.assertTrue(all(item["heading_ordinal"] == 1 for item in links))
        self.assertEqual(classify_link("relative/page"), "relative")
        self.assertEqual(classify_link("#part"), "anchor")

    def test_nested_markdown_links_images_and_brackets(self) -> None:
        """Balanced scanning recovers outer image links and nested-bracket labels only once."""
        content = (
            "[![Binder](badge.svg)](https://mybinder.org/v2/repo)\n"
            "[[2]](/blog/example#references)\n"
            "![Ordinary](image.png)\n"
        )
        links = extract_links(content, f"{BASE_URL}/docs/page", [])
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["anchor_text"], "Binder")
        self.assertEqual(links[0]["raw_target"], "https://mybinder.org/v2/repo")
        self.assertEqual(links[1]["anchor_text"], "[2]")
        self.assertEqual(links[1]["raw_target"], "/blog/example#references")
        self.assertNotIn("badge.svg", [item["raw_target"] for item in links])
        self.assertNotIn("image.png", [item["raw_target"] for item in links])

    def test_html_image_sources_are_not_page_links(self) -> None:
        """Standalone inline and multiline image sources do not enter link inventory."""
        content = (
            '<img src="https://example.org/inline.png" />\n'
            "<img\n"
            '  alt="Multiline"\n'
            '  src="https://example.org/multiline.png"\n'
            "/>\n"
        )
        self.assertEqual(extract_links(content, f"{BASE_URL}/docs/page", []), [])
        masked = mask_html_image_tags(content)
        self.assertEqual(len(masked), len(content))
        self.assertEqual(masked.count("\n"), content.count("\n"))

    def test_linked_html_image_emits_only_enclosing_href(self) -> None:
        """A linked image retains its navigable anchor but not its image source."""
        content = (
            '<a href="https://example.org/page">\n'
            '  <img src="https://example.org/image.png" />\n'
            "</a>\n"
        )
        links = extract_links(content, f"{BASE_URL}/docs/page", [])
        self.assertEqual([item["raw_target"] for item in links], ["https://example.org/page"])
        self.assertEqual(links[0]["source_line"], 1)

    def test_non_image_mdx_url_attribute_remains_supported(self) -> None:
        """Filtering image sources does not suppress other URL-valued component props."""
        content = '<ToolCard repository="https://github.com/example/tool" />\n'
        links = extract_links(content, f"{BASE_URL}/docs/page", [])
        self.assertEqual([item["raw_target"] for item in links], ["https://github.com/example/tool"])

    def test_markdown_target_escapes_are_preserved_only_in_raw_target(self) -> None:
        """Resolved URLs remove punctuation escapes while raw targets remain source-faithful."""
        content = "[AWRA](2024-03-26\\_AWRA\\_GeospatialWaterTechnology)\n"
        link = extract_links(content, f"{BASE_URL}/docs/base/", [])[0]
        self.assertEqual(link["raw_target"], "2024-03-26\\_AWRA\\_GeospatialWaterTechnology")
        self.assertEqual(
            link["resolved_url"],
            f"{BASE_URL}/docs/base/2024-03-26_AWRA_GeospatialWaterTechnology",
        )

    def test_overlapping_link_syntax_is_not_duplicated(self) -> None:
        """An HTML href that is also a URL-valued attribute emits one occurrence."""
        content = '<a href="https://example.org/page">Example</a>\n'
        links = extract_links(content, f"{BASE_URL}/docs/page", [])
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["raw_target"], "https://example.org/page")

    def test_ambiguous_relative_link_is_preserved_unresolved(self) -> None:
        """Relative links in externally materialized pages retain raw targets without invention."""
        links = extract_links("[Relative](guide.md)\n", f"{BASE_URL}/docs/page", [], ambiguous_relative=True)
        self.assertEqual(links[0]["raw_target"], "guide.md")
        self.assertIsNone(links[0]["resolved_url"])

    def test_external_component_extraction(self) -> None:
        """Multiline README and Wiki declarations retain source order and normalized paths."""
        content = (
            '<GitHubReadme\n username="org"\n repo="repo"\n subfolder="docs"\n readmeFileName="GUIDE.md"\n/>\n'
            '<GitHubWikiPage username="org" repo="wiki" path="Start Here" />\n'
            '<GitHubReadme username="org" repo="default" />\n'
        )
        warnings: list[dict[str, str]] = []
        records = extract_external_content_sources(content, "docs/page.mdx", warnings)
        self.assertEqual([item["component"] for item in records], ["GitHubReadme", "GitHubWikiPage", "GitHubReadme"])
        self.assertEqual([item["path"] for item in records], ["docs/GUIDE.md", "Start Here", "README.md"])
        self.assertEqual([item["ordinal"] for item in records], [1, 2, 3])
        self.assertEqual(warnings, [])

    def test_generated_page_metadata_and_materialized_authors(self) -> None:
        """Generated provenance and materialized author details project without semantic entities."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = write_page(
                root,
                "_generated_js_pages/home.mdx",
                'title: Home\npath: /\ngenerated_from_js: true\nsource_path: src/pages/index.js',
                "\n# Home\n",
            )
            blog = write_page(
                root,
                "blog/post.mdx",
                'title: Post\npath: blog/post\nslug: post\nauthors: [person-id]',
                "\n## Authors\n\n- **A Person** - Researcher, Example University ([Profile](https://example.org/person))\n",
            )
            generated_record = build_page_record(generated, root)
            self.assertTrue(generated_record["generated_from_js"])
            self.assertEqual(generated_record["source_path"], "src/pages/index.js")
            author = build_page_record(blog, root)["authors"][0]
            self.assertEqual(author["name"], "A Person")
            self.assertEqual(author["role"], "Researcher")
            self.assertEqual(author["affiliation"], "Example University")

    def test_scalar_author_identifier_is_normalized_with_warning(self) -> None:
        """A scalar author identifier remains usable but is explicitly reported."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = write_page(root, "blog/post.mdx", "title: Post\npath: blog/post\nslug: post\nauthors: person-id")
            record = build_page_record(page, root)
            self.assertEqual(record["authors"][0]["source_identifier"], "person-id")
            self.assertEqual(record["warnings"][0]["issue"], "non_list_authors_normalized")

    def test_discovery_exclusions_and_public_resource_pages(self) -> None:
        """Path-based discovery excludes artifacts and includes public technical pages."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_page(root, "docs/page.mdx", "title: Page\npath: docs/page")
            write_page(root, "src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx", "title: Resource\npath: resources/RESOURCES_PAGE_DOCUMENTATION")
            write_page(root, ".github/ISSUE_TEMPLATE.md", "title: Ignore\npath: ignore")
            write_page(root, "README.md", "title: Ignore\npath: ignore")
            write_page(root, "release-notes-template.mdx", "title: Ignore\npath: ignore")
            (root / ".DS_Store").write_bytes(b"metadata")
            (root / "docs" / "._page.mdx").write_text("metadata", encoding="utf-8")
            (root / "__MACOSX" / "docs").mkdir(parents=True)
            (root / "__MACOSX" / "docs" / "page.mdx").write_text("metadata", encoding="utf-8")
            (root / "site-config.json").write_text("{}", encoding="utf-8")
            candidates, exclusions = discover_candidate_files(root)
            self.assertEqual(
                [item.relative_to(root).as_posix() for item in candidates],
                ["docs/page.mdx", "src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx"],
            )
            self.assertEqual(exclusions["github_metadata"], 1)
            self.assertEqual(exclusions["macos_metadata"], 3)
            self.assertEqual(exclusions["root_support_document"], 1)
            self.assertEqual(exclusions["template_document"], 1)

    def test_parent_resolution_uses_nearest_existing_url(self) -> None:
        """Hierarchy uses canonical ancestors and never creates fictitious pages."""
        pages = [
            {"canonical_url": f"{BASE_URL}/docs/", "parent_url": None},
            {"canonical_url": f"{BASE_URL}/docs/group/", "parent_url": None},
            {"canonical_url": f"{BASE_URL}/docs/group/child", "parent_url": None},
            {"canonical_url": f"{BASE_URL}/orphan/child", "parent_url": None},
        ]
        resolve_parent_urls(pages)
        self.assertEqual(pages[2]["parent_url"], f"{BASE_URL}/docs/group/")
        self.assertIsNone(pages[3]["parent_url"])

    def test_duplicate_canonical_url_rejected(self) -> None:
        """Two physical candidates may not represent the same public page."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_page(root, "docs/one.mdx", "title: One\npath: docs/same")
            write_page(root, "docs/two.mdx", "title: Two\npath: docs/same")
            with self.assertRaises(CorpusBuildError):
                build_corpus(root)

    def test_required_field_and_duplicate_path_validation(self) -> None:
        """Independent validation catches malformed shape and duplicate corpus paths."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_page(root, "docs/page.mdx", "title: Page\npath: docs/page")
            corpus = build_corpus(root)
            corpus["pages"].append(copy.deepcopy(corpus["pages"][0]))
            corpus["pages"][0]["title"] = ""
            report = validate_corpus(corpus, root)
            self.assertFalse(report["valid"])
            self.assertTrue(any("corpus paths are not unique" in issue for issue in report["issues"]))
            self.assertTrue(any("title must be a nonempty string" in issue for issue in report["issues"]))

    def test_byte_identical_repeated_output(self) -> None:
        """Repeated builds and writes over unchanged fixtures are byte-identical."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "raw"
            output_one = Path(directory) / "one.json"
            output_two = Path(directory) / "two.json"
            write_page(root, "docs/page.mdx", "title: Page\npath: docs/page", "\n# Page\n")
            first = build_corpus(root)
            second = build_corpus(root)
            self.assertEqual(serialize_corpus(first), serialize_corpus(second))
            first_hash = write_deterministic_json(first, output_one)
            second_hash = write_deterministic_json(second, output_two)
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(output_one.read_bytes(), output_two.read_bytes())


@unittest.skipUnless(FROZEN_RAW.exists(), "CIROH Hub frozen raw corpus unavailable")
class HubPhaseAFrozenRegressionTests(unittest.TestCase):
    """Keep current-snapshot anchors separate from general extraction logic."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build and validate the frozen corpus once for regression assertions."""
        cls.corpus = build_corpus(FROZEN_RAW)
        cls.report = validate_corpus(cls.corpus, FROZEN_RAW, expected_page_count=242, validate_frozen_snapshot=True)
        cls.by_path = {page["corpus_path"]: page for page in cls.corpus["pages"]}

    def test_frozen_acceptance_anchors(self) -> None:
        """Current page counts and all frozen contract anchors validate."""
        self.assertTrue(self.report["valid"], self.report["issues"])
        self.assertEqual(self.report["page_count"], 242)
        self.assertEqual(self.report["generated_from_js"], 11)
        self.assertIn("src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx", self.by_path)
        self.assertIn("src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx", self.by_path)
        self.assertEqual(
            self.by_path["src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx"]["canonical_url"],
            f"{BASE_URL}/community_products/RESOURCES_PAGE_DOCUMENTATION/",
        )
        self.assertEqual(
            self.by_path["src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx"]["canonical_url"],
            f"{BASE_URL}/resources/RESOURCES_PAGE_DOCUMENTATION/",
        )

    def test_frozen_publications_and_artifact_exclusions(self) -> None:
        """Publications is documented while raw artifacts never become pages."""
        urls = {page["canonical_url"] for page in self.corpus["pages"]}
        self.assertNotIn(f"{BASE_URL}/publications", urls)
        self.assertEqual(self.corpus["known_exclusions"][0]["reason"], "dynamic_zotero_catalog_delegated_to_paper_corpus")
        self.assertFalse(any(page["corpus_path"].startswith(".github/") for page in self.corpus["pages"]))
        self.assertFalse(any("__MACOSX" in page["corpus_path"] for page in self.corpus["pages"]))

    def test_frozen_quality_corrections_and_url_regressions(self) -> None:
        """Events, Home, Impact, title fallback, and encoded URL regressions remain corrected."""
        events = self.by_path["_generated_js_pages/events.mdx"]["content_mdx"]
        self.assertNotIn("getResourceStats(events), [events]); return (", events)
        for corpus_path in ("_generated_js_pages/home.mdx", "src/pages/impact.mdx"):
            content = self.by_path[corpus_path]["content_mdx"]
            for key in ("projects", "projectsBar", "users", "usersBar"):
                self.assertEqual(content.count(f"- {key}:"), 4)
        title_page = self.by_path["docs/services/cloudservices/aws/documentation/data-science-tools/index.mdx"]
        self.assertEqual(title_page["title_source"], "first_h1")
        nwm = next(page for page in self.corpus["pages"] if page["path"] == "docs/products/data-management/dataaccess/NWMURL Library")
        self.assertEqual(nwm["canonical_url"], f"{BASE_URL}/docs/products/data-management/dataaccess/NWMURL%20Library")

    def test_frozen_structural_records_are_visible(self) -> None:
        """No frozen heading, link, or external declaration originates in a masked region."""
        for page in self.corpus["pages"]:
            masked = mask_nonvisible_content(page["content_mdx"])
            lines = masked.splitlines()
            for heading in page["headings"]:
                source_line = lines[heading["source_line"] - 1]
                self.assertIn(heading["raw_text"], source_line, page["corpus_path"])
            for link in page["links"]:
                source_line = lines[link["source_line"] - 1]
                self.assertIn(link["raw_target"], source_line, page["corpus_path"])
            for source in page["external_content_sources"]:
                source_line = lines[source["source_line"] - 1]
                self.assertIn(f"<{source['component']}", source_line, page["corpus_path"])

    def test_frozen_links_do_not_originate_exclusively_from_image_sources(self) -> None:
        """Frozen link records remain visible after complete image tags are masked."""
        for page in self.corpus["pages"]:
            visible = mask_nonvisible_content(page["content_mdx"])
            image_masked_lines = mask_html_image_tags(visible).splitlines()
            for link in page["links"]:
                source_line = int(link["source_line"])
                self.assertIn(
                    link["raw_target"],
                    image_masked_lines[source_line - 1],
                    msg=f"image-only link in {page['corpus_path']}:{source_line}",
                )

    def test_frozen_parent_and_summary_reconciliation(self) -> None:
        """All parent targets resolve and summary counts reconcile."""
        urls = {page["canonical_url"] for page in self.corpus["pages"]}
        self.assertTrue(all(page["parent_url"] is None or page["parent_url"] in urls for page in self.corpus["pages"]))
        self.assertEqual(sum(self.corpus["summary"]["by_source_group"].values()), 242)
        self.assertEqual(self.corpus["summary"]["page_warning_count"], sum(len(page["warnings"]) for page in self.corpus["pages"]))

    def test_frozen_repeated_build_is_byte_identical(self) -> None:
        """The frozen corpus is byte-stable across independent builds."""
        second = build_corpus(FROZEN_RAW)
        first_bytes = serialize_corpus(self.corpus)
        second_bytes = serialize_corpus(second)
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), hashlib.sha256(second_bytes).hexdigest())
        self.assertEqual(json.loads(first_bytes)["summary"], json.loads(second_bytes)["summary"])


if __name__ == "__main__":
    unittest.main()
