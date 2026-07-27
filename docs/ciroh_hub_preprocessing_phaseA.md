# CIROH Hub Preprocessing — Phase A

**Study 2: Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**  
**Artifact type:** CIROH Hub documentation  
**Target script:** `src/preprocessing/build_ciroh_hub_corpus.py`  
**Target output:** `data/interim/documents/ciroh_hub_corpus.json`

---

## 1. Purpose

This document defines the contract for **Phase A preprocessing of the CIROH Hub corpus**. Its purpose is to transform the heterogeneous raw acquisition snapshot stored under:

```text
data/raw/documents/
```

into one deterministic, page-centric intermediate corpus:

```text
data/interim/documents/ciroh_hub_corpus.json
```

The intermediate corpus will be consumed by two downstream systems:

1. the CIROH AI Bot v2 retrieval pipeline; and
2. the deterministic CIROH Hub extractor used in Study 2.

The preprocessing stage must hide the acquisition-time heterogeneity of the source repository. All selected content-bearing JavaScript, JSON, YAML, GitHub README, and GitHub Wiki sources have already been materialized as `.md` or `.mdx` files in the raw corpus. Therefore, downstream preprocessing must operate only on the resulting Markdown/MDX files and must not interpret or execute JavaScript.

The unit of analysis in the output is the **public CIROH Hub page**, identified by its canonical Hub URL. A physical source file, generated MDX file, imported data file, or original JavaScript file is provenance metadata, not a separate public document.

---

## 2. Position in the pipeline

```text
Phase 0 — Acquisition and materialization
-----------------------------------------
data/raw/documents/**/*.md[x]

Selected content originally stored in JavaScript, JSON, YAML,
GitHub README, or GitHub Wiki sources is already represented in MDX.

                    ↓

Phase A — Page-centric preprocessing
------------------------------------
src/preprocessing/build_ciroh_hub_corpus.py

                    ↓

data/interim/documents/ciroh_hub_corpus.json

                    ↓

Phase B — Deterministic KG extraction
-------------------------------------
src/extraction/extract_ciroh_hub.py

                    ↓

data/interim/documents/ciroh_hub_nodes_edges.json
```

Phase A establishes the stable input contract for Phase B. It does not create ontology instances or KG relations.

---

## 3. Scope boundary

### 3.1 Phase A must

Phase A must:

- discover public page candidates in `data/raw/documents/`;
- exclude non-corpus files and acquisition artifacts;
- parse YAML front matter;
- separate front matter from the Markdown/MDX body;
- normalize page metadata;
- construct the canonical public CIROH Hub URL;
- preserve the complete materialized Markdown/MDX body;
- extract headings mechanically;
- extract links mechanically;
- detect explicit `GitHubReadme` and `GitHubWikiPage` component invocations;
- resolve blog and release-note author metadata already materialized in the page;
- calculate the nearest existing parent page from canonical URLs;
- calculate deterministic hashes;
- record warnings and exclusions;
- produce deterministic, byte-stable JSON.

### 3.2 Phase A must not

Phase A must not:

- create `DocumentationPage`, `Section`, `Link`, `Subject`, `Person`, `Organization`, `Tool`, `Repository`, or any other ontology node;
- create KG edges such as `hasSection`, `linksTo`, `hasSubject`, `isPartOf`, `hasSubPage`, `referencesRepository`, or `referencesDataset`;
- create `EvidenceSpan` nodes;
- create `File` nodes or instantiate `hasSourceFile`;
- infer procedures, steps, workflows, parameters, concepts, scientific models, tools, purposes, capabilities, or limitations from prose;
- classify product-catalog entries as ontology classes;
- consolidate or align entities across HydroShare, GitHub, Hub, or papers;
- execute JavaScript, JSX, TypeScript, React, or MDX components;
- make network calls;
- use an LLM;
- modify files under `data/raw/documents/`;
- repair or rewrite source claims.

---

## 4. Raw corpus scope

### 4.1 Candidate page locations

The builder must consider Markdown and MDX files under these page-bearing locations:

```text
data/raw/documents/docs/**/*.md
data/raw/documents/docs/**/*.mdx

data/raw/documents/blog/**/*.md
data/raw/documents/blog/**/*.mdx

data/raw/documents/release-notes/**/*.md
data/raw/documents/release-notes/**/*.mdx

data/raw/documents/_generated_js_pages/**/*.md
data/raw/documents/_generated_js_pages/**/*.mdx

data/raw/documents/src/pages/**/*.md
data/raw/documents/src/pages/**/*.mdx
```

The current frozen acquisition snapshot is expected to contain **242 public page candidates** after the exclusions below are applied.

This count is a regression anchor for the current snapshot, not a permanent rule for future corpus versions.

### 4.2 Mandatory exclusions

The builder must ignore:

```text
__MACOSX/**
**/.DS_Store
**/._*
.github/**
```

It must also exclude Markdown/MDX files at the raw-root level that are repository-support documents rather than public Hub pages, including files such as:

```text
README.md
CONTRIBUTING.md
SECURITY.md
INSTALL.md
GITHUB_LOGIN_FLOW.md
CHANGELOG.md
release-notes-template.mdx
```

The exclusion rule must be based on explicit path classification, not only filename extension.

### 4.3 Explicitly included public pages

The following pages must be included because they resolve to public Hub URLs, even if they may not be linked from the main site navigation:

```text
src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx
src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx
```

Expected public routes:

```text
https://hub.ciroh.org/community_products/RESOURCES_PAGE_DOCUMENTATION/
https://hub.ciroh.org/resources/RESOURCES_PAGE_DOCUMENTATION/
```

### 4.4 Explicitly excluded route

The public route below is intentionally excluded from the Hub corpus:

```text
https://hub.ciroh.org/publications
```

Reason:

```text
dynamic_zotero_catalog_delegated_to_paper_corpus
```

This exclusion must be recorded explicitly in the output so that the missing route cannot be mistaken for an acquisition failure.

---

## 5. Determinism requirements

The builder must be fully offline and deterministic.

The same raw input must produce byte-identical JSON across repeated executions.

Required conventions:

- no execution timestamps in the output;
- no random UUIDs;
- no dependence on filesystem traversal order;
- normalize line endings to `\n` before content parsing and content hashing;
- sort pages by `canonical_url`, then `corpus_path` as a deterministic tie-breaker;
- sort top-level exclusions by route or path;
- preserve heading and link arrays in source order;
- sort unordered metadata collections such as tags only when source order has no semantic meaning;
- write JSON with UTF-8 encoding, stable indentation, and stable key ordering;
- terminate the output file with one newline;
- use explicit `null`, `[]`, and `false` values rather than omitting schema keys;
- fail on canonical-URL collisions;
- fail on duplicate `corpus_path` values;
- perform no silent data correction.

Recommended serialization:

```python
json.dump(
    payload,
    handle,
    indent=2,
    ensure_ascii=False,
    sort_keys=True,
)
handle.write("\n")
```

---

## 6. Output contract

### 6.1 Top-level structure

The output must follow this conceptual schema:

```jsonc
{
  "schema_version": "1.0.0",
  "phase_a_version": "1.0.2",
  "source": {
    "artifact_type": "ciroh_hub",
    "base_url": "https://hub.ciroh.org",
    "raw_root": "data/raw/documents"
  },
  "pages": [],
  "known_exclusions": [],
  "warnings": [],
  "summary": {}
}
```

### 6.2 Required page record

Every page record must contain all keys below:

```jsonc
{
  "page_key": "hub-page:https://hub.ciroh.org/docs/contribute/",
  "canonical_url": "https://hub.ciroh.org/docs/contribute/",

  "path": "docs/contribute/index",
  "slug": null,

  "title": "Contributing to CIROH Hub",
  "title_source": "front_matter",
  "description": "Find out how to contribute information to Hub.",

  "last_updated_date": "2026-02-04",
  "last_updated_date_raw": "02/04/2026",

  "source_group": "docs",
  "corpus_path": "docs/contribute/index.mdx",
  "source_path": "docs/contribute/index.mdx",
  "generated_from_js": false,

  "front_matter": {},
  "tags": [],
  "authors": [],

  "content_mdx": "...",

  "headings": [],
  "links": [],
  "external_content_sources": [],

  "parent_url": null,

  "file_sha256": "...",
  "content_sha256": "...",

  "warnings": []
}
```

### 6.3 Field definitions

#### `page_key`

Stable page identifier for the Phase A corpus:

```text
hub-page:<canonical_url>
```

It is not yet an ontology identifier and does not imply that Phase B must use the same node-ID syntax.

#### `canonical_url`

Public CIROH Hub URL derived according to Section 8.

#### `path`

Raw `path` value from front matter, preserved as text after trimming surrounding whitespace. This is not assumed to equal the final public URL.

#### `slug`

Raw front-matter slug, normalized by trimming whitespace. `null` when absent.

#### `title`

Normalized page title after applying the fallback policy in Section 9.

#### `title_source`

Closed vocabulary:

```text
front_matter
first_h1
description
path_fallback
```

#### `description`

Front-matter description, trimmed. `null` when absent.

#### `last_updated_date`

ISO date (`YYYY-MM-DD`) when the raw value can be parsed unambiguously. Otherwise `null` plus a warning.

#### `last_updated_date_raw`

Original value of the `Last updated date` front-matter field converted to a string. `null` when absent.

#### `source_group`

Closed vocabulary:

```text
docs
blog
release_notes
generated_js_page
src_page
```

This field describes source organization only. It is not the ontology `pageType`.

#### `corpus_path`

Project-relative path of the consumed `.md` or `.mdx` file under `data/raw/documents/`.

Examples:

```text
docs/contribute/index.mdx
_generated_js_pages/contribute.mdx
src/pages/impact.mdx
```

#### `source_path`

Original repository source path.

For ordinary Markdown/MDX pages:

```text
source_path == corpus_path
```

For generated pages:

```yaml
generated_from_js: true
source_path: src/pages/contribute/index.js
```

produces:

```json
{
  "corpus_path": "_generated_js_pages/contribute.mdx",
  "source_path": "src/pages/contribute/index.js",
  "generated_from_js": true
}
```

`source_path` is provenance metadata in Phase A. Phase A must not create a `File` entity or instantiate a `hasSourceFile` relation. Phase B may use the explicit `source_path` value to create a deterministic `RepoFile` node and instantiate `hasSourceFile`, as defined by the CIROH Hub Phase B extraction contract. `corpus_path` remains the path of the materialized file consumed by Phase A and must not generate a second source-file node.

#### `generated_from_js`

Boolean projected from front matter. It must be `true` only for materialized pages generated from selected JavaScript sources.

#### `front_matter`

Complete parsed YAML front matter represented as JSON-compatible values. The builder must preserve unknown front-matter keys rather than discarding them.

#### `tags`

Normalized list projected from front matter. Scalar values must be converted to a one-item list. Empty or missing values produce `[]`.

#### `authors`

Normalized author records already available in the materialized page or front matter. Phase A must not perform cross-document entity consolidation.

The minimum normalized author representation is:

```jsonc
{
  "name": "Ayman Nassar",
  "role": "Postdoctoral Researcher",
  "affiliation": "Utah State University",
  "url": null,
  "source": "materialized_author_block"
}
```

When only an author identifier is available and no materialized author details can be read, retain:

```jsonc
{
  "name": null,
  "role": null,
  "affiliation": null,
  "url": null,
  "source": "front_matter_identifier",
  "source_identifier": "author-id"
}
```

#### `content_mdx`

Complete Markdown/MDX body after front matter removal and line-ending normalization. No summarization or semantic rewriting is allowed.

#### `headings`

Mechanically extracted heading records defined in Section 11.

#### `links`

Mechanically extracted link records defined in Section 12.

#### `external_content_sources`

Explicit `GitHubReadme` and `GitHubWikiPage` source declarations defined in Section 13.

#### `parent_url`

Canonical URL of the nearest ancestor page included in the corpus. `null` when no included ancestor exists.

#### `file_sha256`

SHA-256 of the exact raw file bytes as found under `data/raw/documents/`.

#### `content_sha256`

SHA-256 of `content_mdx` encoded as UTF-8 after line-ending normalization.

#### `warnings`

Page-local warnings using the schema in Section 15.

---

## 7. Source-group classification

Classification must be path-based and deterministic.

```text
blog/**                 → blog
release-notes/**        → release_notes
_generated_js_pages/**  → generated_js_page
src/pages/**            → src_page
docs/**                 → docs
```

A file matching none of these groups must not silently become a page. It must either be explicitly excluded or cause validation failure.

---

## 8. Canonical URL construction

### 8.1 Base domain

Use the fixed canonical base URL:

```text
https://hub.ciroh.org
```

Do not use `http`.

### 8.2 URL rules by source group

#### Generated JavaScript pages and `src/pages`

```text
canonical_url = base_url + front_matter.path
```

Example:

```yaml
path: contribute
```

produces:

```text
https://hub.ciroh.org/contribute
```

The root path must produce exactly:

```text
https://hub.ciroh.org/
```

#### `docs/**/index.md[x]`

Build from front-matter `path`, removing only the terminal `/index` segment.

Example:

```text
path: docs/contribute/index
```

produces:

```text
https://hub.ciroh.org/docs/contribute/
```

The word `index` must not be removed when it is not the terminal path segment.

#### Other `docs` pages

```text
canonical_url = base_url + front_matter.path
```

Example:

```text
path: docs/contribute/repository
```

produces:

```text
https://hub.ciroh.org/docs/contribute/repository
```

#### Blog posts

Use:

```text
base_url + "/blog/" + slug
```

The physical filename and raw `path` must not override a valid blog slug.

A blog post without `slug` must fail validation unless an explicit documented fallback is later approved.

#### Release notes

Use:

```text
base_url + "/release-notes/" + slug
```

A release note without `slug` must fail validation unless an explicit documented fallback is later approved.

### 8.3 URL encoding

The builder must:

- preserve `/` path separators;
- URL-encode each path segment independently;
- encode spaces as `%20`;
- not convert spaces to hyphens;
- not double-encode already encoded sequences;
- remove duplicate slashes in the path portion;
- preserve a terminal slash when the canonical route represents an index page;
- reject canonical URLs outside `https://hub.ciroh.org`.

Mandatory regression case:

```text
path:
docs/products/data-management/dataaccess/NWMURL Library

canonical URL:
https://hub.ciroh.org/docs/products/data-management/dataaccess/NWMURL%20Library
```

### 8.4 URL validation

The builder must fail on:

- missing `path` for a non-blog and non-release-note page;
- missing `slug` for a blog post;
- missing `slug` for a release note;
- duplicate canonical URLs;
- a canonical URL outside the Hub domain;
- an empty route except for the home page.

---

## 9. Front matter and title fallback

### 9.1 YAML parsing

Every candidate page must contain valid YAML front matter delimited by `---`.

The builder must:

- parse the complete front matter;
- preserve unknown keys;
- project known keys into normalized page fields;
- fail on invalid YAML;
- warn on unexpected data types when a deterministic normalization is possible;
- never execute YAML tags or arbitrary constructors.

Use a safe YAML loader.

### 9.2 Projected fields

At minimum, project:

```text
title
description
path
slug
tags
authors
Last updated date
generated_from_js
source_path
```

### 9.3 Title selection

Apply this ordered fallback:

```text
1. nonempty front-matter title
2. first nonempty H1 in the Markdown/MDX body
3. nonempty front-matter description
4. humanized final path segment
```

Record the selected source in `title_source`.

The known page:

```text
docs/services/cloudservices/aws/documentation/data-science-tools/index.mdx
```

must use its first H1 when the front matter has no `title`.

A `path_fallback` title must generate a warning.

### 9.4 Date normalization

The current corpus commonly uses:

```text
MM/DD/YYYY
```

Normalize unambiguous values to:

```text
YYYY-MM-DD
```

Preserve the source text in `last_updated_date_raw`.

An absent date is allowed. An unparseable nonempty date produces:

```text
last_updated_date = null
```

and a warning.

---

## 10. Content preservation

Phase A must separate front matter from the body and preserve the complete body under `content_mdx`.

Allowed normalization:

- convert `\r\n` and `\r` to `\n`;
- preserve Unicode;
- preserve Markdown, MDX tags, comments, code fences, lists, tables, and inline HTML;
- optionally ensure exactly one terminal newline in `content_mdx`, provided this rule is applied consistently.

Not allowed:

- summarizing;
- removing paragraphs;
- interpreting JavaScript;
- executing components;
- converting numbered lists to semantic steps;
- rewriting headings;
- repairing source grammar;
- deleting unknown MDX components merely because they are not understood.

The raw acquisition already materializes selected JavaScript payloads and remote GitHub content. Phase A consumes that materialized representation as the authoritative page body for downstream processing.

### 10.1 Non-visible structural regions

The complete source body, including comments and fenced code, remains unchanged in
`content_mdx`. For mechanical structural extraction only, Phase A must mask fenced code
blocks, HTML comments (`<!-- ... -->`), and MDX/JSX comments (`{/* ... */}`). Comments may
be inline or multiline. The common masked representation must preserve all newline
positions so extracted `source_line` values remain relative to the original `content_mdx`.
Comment markers inside fenced code blocks are code content and must not start or end a
comment region.

---

## 11. Heading extraction

### 11.1 Heading record

Each ATX Markdown heading must produce:

```jsonc
{
  "ordinal": 1,
  "level": 2,
  "text": "Community impact",
  "raw_text": "Community impact",
  "source_line": 18,
  "parent_heading_ordinal": null
}
```

### 11.2 Rules

- recognize `#` through `######` ATX headings;
- ignore headings inside fenced code blocks, HTML comments, and MDX/JSX comments;
- preserve source order;
- assign one-based ordinals;
- record one-based source-line numbers relative to `content_mdx`;
- remove surrounding Markdown emphasis and inline-code markers for normalized `text` when this can be done mechanically;
- preserve the unnormalized heading content in `raw_text`;
- calculate `parent_heading_ordinal` using the nearest preceding heading with a lower level;
- do not generate section IDs in Phase A;
- do not attempt to replicate exact Docusaurus anchor-generation behavior in Phase A;
- do not interpret headings as `Procedure`, `Workflow`, `Concept`, or any other semantic class.

The first H1 must remain in the heading inventory even when it is also used as the title fallback. Phase B may later decide whether to instantiate it as a separate `Section`.

---

## 12. Link extraction

### 12.1 Link record

Each extracted link occurrence must produce:

```jsonc
{
  "ordinal": 1,
  "anchor_text": "AWS Data Science Tools",
  "raw_target": "https://github.com/example/repository",
  "resolved_url": "https://github.com/example/repository",
  "link_type": "github",
  "source_line": 15,
  "heading_ordinal": 1
}
```

### 12.2 Supported link forms

Extract mechanically:

- Markdown inline links: `[text](target)`;
- labels containing nested brackets, such as `[[2]](target)`;
- the outer clickable destination of nested image links, such as
  `[![Binder](badge.svg)](target)`;
- Markdown autolinks: `<https://example.org>`;
- absolute URLs appearing in MDX attributes when they can be identified without executing code;
- ordinary HTML anchor `href` values when present directly in the MDX body.

Ordinary Markdown images such as `![Alt](image.png)` are excluded from the page-link
inventory. URLs used exclusively as image sources, including `src` attributes on inline or
multiline HTML/MDX `<img>` elements, are also excluded. For a nested image link, the inner
image source is not a page link. For an image wrapped by an HTML anchor, the enclosing
`href` is extracted while the `<img src>` is not. Other supported URL-valued component
properties remain eligible. Links inside fenced code blocks, HTML comments, and MDX/JSX
comments are ignored. Overlapping syntax must not create duplicate link occurrences.

### 12.3 Syntactic link types

Use this closed vocabulary:

```text
hub_internal
github
hydroshare
doi
mailto
anchor
relative
other_absolute
```

This is syntactic classification only. It does not create ontology relations.

### 12.4 Resolution rules

- absolute HTTP(S) targets retain their normalized absolute URL;
- `raw_target` preserves Markdown backslash escaping, while `resolved_url` removes
  backslashes used to escape valid Markdown punctuation without percent-decoding or
  double-decoding the URL;
- `mailto:` targets remain unchanged;
- `#anchor` targets may be resolved against the current canonical page URL;
- Hub-absolute paths beginning with `/` may be resolved against `https://hub.ciroh.org`;
- relative links may be resolved only when their page-level base is unambiguous;
- relative links inside materialized GitHub README or Wiki content may have an external repository base that Phase A cannot infer reliably from source-line position; in such cases preserve `raw_target`, set `resolved_url` to `null`, and add no warning unless the syntax itself is invalid;
- never invent a target based on anchor text.

### 12.5 Heading association

`heading_ordinal` must reference the nearest preceding heading in source order, or `null` when the link occurs before the first heading.

---

## 13. External content declarations

The materialized body may retain explicit invocations of:

```text
GitHubReadme
GitHubWikiPage
```

Phase A must detect their declared props and preserve source order.

### 13.1 GitHub README record

```jsonc
{
  "ordinal": 1,
  "component": "GitHubReadme",
  "username": "CIROH-UA",
  "repository": "SWEML",
  "path": "README.md",
  "source_line": 42
}
```

If `path` is omitted by the component, normalize it to the component's documented default only when that default is already enforced by the acquisition code; otherwise use `null`.

### 13.2 GitHub Wiki record

```jsonc
{
  "ordinal": 1,
  "component": "GitHubWikiPage",
  "username": "CIROH-UA",
  "repository": "awi-ciroh-image",
  "path": "2i2c-image-list",
  "source_line": 30
}
```

### 13.3 Rules

- detect multiline MDX component invocations;
- ignore declarations inside fenced code blocks, HTML comments, and MDX/JSX comments;
- support quoted string props;
- do not execute the component;
- do not attempt to locate the end of the materialized external block;
- do not create repository nodes or relations in Phase A;
- retain multiple external sources in declaration order;
- preserve missing optional props as `null`;
- warn only when a required identifying prop is absent or malformed.

The known page containing two external GitHub sources must preserve both declarations and their order.

---

## 14. Parent-page hierarchy

The builder must calculate parent relationships only after all canonical URLs have been constructed and validated.

### 14.1 Rule

For each page:

1. parse its canonical URL path;
2. remove the terminal path segment;
3. search upward for the nearest ancestor URL that exists in the included page set;
4. assign that URL as `parent_url`;
5. return `null` when no included ancestor exists.

### 14.2 Constraints

- operate on `canonical_url`, never `source_path` or physical directory structure;
- do not create synthetic pages for folders;
- the selected parent must exist in `pages`;
- the home page has `parent_url = null`;
- blog posts and release notes may remain parentless when `/blog/` or `/release-notes/` are not represented as included page records;
- the relation is page hierarchy, not filesystem hierarchy.

Example:

```text
child:
https://hub.ciroh.org/docs/contribute/repository

parent:
https://hub.ciroh.org/docs/contribute/
```

---

## 15. Warning contract

### 15.1 Warning schema

Top-level and page-local warnings must use:

```jsonc
{
  "file": "docs/example/page.mdx",
  "issue": "unparseable_last_updated_date",
  "detail": "Value could not be normalized: ..."
}
```

### 15.2 Stable warning vocabulary

Initial warning codes may include:

```text
missing_optional_date
unparseable_last_updated_date
non_list_tags_normalized
non_list_authors_normalized
title_from_path_fallback
missing_generated_source_path
malformed_external_content_component
unresolved_relative_link
unexpected_front_matter_type
```

Warnings must be deterministic and sorted by:

```text
file, issue, detail
```

Do not emit warnings for expected absent optional fields unless the absence is methodologically relevant. For example, an absent optional date does not need a warning unless the project chooses to audit date coverage explicitly.

Errors that violate the acceptance contract must stop execution rather than becoming warnings.

---

## 16. Known materialization quality checks

Before or during Phase A validation, the current corpus must satisfy these checks.

### 16.1 Events page

The generated Events page must not contain the known JavaScript residue:

```text
getResourceStats(events), [events]); return (
```

If present, fail validation with an instruction to regenerate the raw acquisition snapshot.

### 16.2 Home and Impact statistics

The generated Home page and the Impact page materialization must preserve the original semantic keys for each platform:

```text
projects
projectsBar
users
usersBar
```

for:

```text
aws
gcp
hpc
nsf
```

A normalized Markdown representation may use labels such as:

```markdown
### AWS

- Projects: 24
- Projects bar: 38%
- Users: 69
- Users bar: 17%
```

`projectsBar` and `usersBar` are preserved as source content but must not be interpreted in Phase A as scientific indicators or as percentages with a known analytical denominator.

### 16.3 Missing title fallback

The known AWS Data Science Tools page must obtain its title from the first H1 when front matter lacks `title`.

### 16.4 Generated pages

The current snapshot is expected to contain **11** records with:

```text
generated_from_js = true
```

Each such record must contain a nonempty `source_path` pointing to its original JavaScript source.

---

## 17. Known exclusions

The top-level `known_exclusions` array must contain explicit methodological exclusions.

Minimum required record:

```jsonc
{
  "route": "https://hub.ciroh.org/publications",
  "source_path": "src/pages/publications/index.js",
  "reason": "dynamic_zotero_catalog_delegated_to_paper_corpus"
}
```

File-system artifacts excluded by generic rules do not each require an individual record. Their aggregate counts should be included in `summary.exclusions_by_rule`.

---

## 18. Summary contract

The top-level `summary` must include deterministic counts derived from the output.

```jsonc
{
  "total_pages": 242,
  "by_source_group": {
    "blog": 0,
    "docs": 0,
    "generated_js_page": 0,
    "release_notes": 0,
    "src_page": 0
  },
  "generated_from_js": 11,
  "with_title_fallback": 0,
  "with_tags": 0,
  "with_authors": 0,
  "with_external_content": 0,
  "total_external_content_sources": 0,
  "total_headings": 0,
  "total_links": 0,
  "with_parent_url": 0,
  "page_warning_count": 0,
  "top_level_warning_count": 0,
  "exclusions_by_rule": {
    "github_metadata": 0,
    "macos_metadata": 0,
    "root_support_document": 0,
    "template_document": 0
  }
}
```

The builder must compute actual values rather than hard-code them, except that regression tests may assert the expected values for the current frozen snapshot.

---

## 19. CLI contract

The script should expose a minimal deterministic CLI similar to other project preprocessing scripts.

Recommended interface:

```bash
python src/preprocessing/build_ciroh_hub_corpus.py \
  --raw-root data/raw/documents \
  --output data/interim/documents/ciroh_hub_corpus.json
```

Recommended optional arguments:

```text
--expected-page-count 242
--validate-frozen-snapshot
```

The script must:

- create the output directory when necessary;
- never modify the input tree;
- print a concise deterministic summary;
- return a nonzero exit code on validation failure;
- support invocation from the project root;
- resolve project-relative paths consistently.

---

## 20. Validation and acceptance criteria

The Phase A implementation is accepted only when all conditions below pass.

### 20.1 Corpus membership

- exactly 242 pages for the current frozen raw snapshot;
- no page sourced from `.github/**`;
- no page sourced from `__MACOSX/**`, `.DS_Store`, or `._*` files;
- no repository-support Markdown from the raw root;
- both `RESOURCES_PAGE_DOCUMENTATION.mdx` pages are included;
- `/publications` is absent from `pages` and present in `known_exclusions`.

### 20.2 Page completeness

Every page has:

- nonempty `page_key`;
- nonempty `canonical_url`;
- nonempty `title`;
- valid `title_source`;
- nonempty `corpus_path`;
- nonempty `source_path`;
- nonempty `file_sha256`;
- nonempty `content_sha256`;
- `content_mdx` present, including when the page body is empty;
- all required array and boolean fields.

### 20.3 URL correctness

- all URLs begin with `https://hub.ciroh.org`;
- no duplicate canonical URLs;
- `docs/**/index.mdx` pages do not retain terminal `/index`;
- blog URLs use `/blog/<slug>`;
- release-note URLs use `/release-notes/<slug>`;
- generated pages use front-matter `path`;
- the home page resolves to `https://hub.ciroh.org/`;
- `NWMURL Library` resolves with `%20`, not a hyphen or literal space;
- no URL is double-encoded.

### 20.4 Generated-page provenance

- exactly 11 current-snapshot pages have `generated_from_js = true`;
- each has nonempty `source_path`;
- each retains its generated MDX location in `corpus_path`;
- no JavaScript is executed by the builder.

### 20.5 Content quality

- the Events residue is absent;
- Home retains `projects`, `projectsBar`, `users`, and `usersBar` labels;
- Impact retains `projects`, `projectsBar`, `users`, and `usersBar` labels;
- the AWS Data Science Tools page uses the first H1 title fallback;
- all front matter parses with a safe YAML loader;
- no source page is silently discarded because of unknown front-matter fields.

### 20.6 Structural extraction

- headings have deterministic one-based ordinals;
- links have deterministic one-based ordinals;
- heading and link source-line numbers are valid;
- parent heading references point backward to existing heading ordinals;
- link heading references point to existing heading ordinals or `null`;
- external-content declarations preserve source order;
- headings, links, and external-content declarations inside fenced code blocks, HTML
  comments, or MDX/JSX comments are absent from the structural arrays;
- structural masking preserves original line numbering;
- nested image links emit only their outer clickable destination;
- nested-bracket labels are preserved mechanically;
- ordinary Markdown image sources are not emitted as links;
- inline and multiline HTML/MDX `<img src>` values are not emitted as links;
- an HTML anchor wrapping an image emits its navigable `href` but not the image `src`;
- escaped Markdown punctuation is preserved in `raw_target` and unescaped only in
  `resolved_url`;
- all nonnull `parent_url` values resolve to included pages.

### 20.7 Accounting

- summary totals reconcile with the page records;
- warning totals reconcile with page-local and top-level warnings;
- exclusion counts reconcile with ignored files;
- `by_source_group` sums to `total_pages`.

### 20.8 Reproducibility

- two consecutive executions over unchanged input produce byte-identical output;
- SHA-256 of the output is identical across the two executions;
- tests do not depend on internet access;
- tests do not depend on local wall-clock time.

---

## 21. Required tests

The implementation must include:

```text
tests/test_build_ciroh_hub_corpus.py
```

### 21.1 Synthetic unit tests

At minimum, tests must cover:

- safe front-matter parsing;
- front-matter/body separation;
- URL rule for a generated page;
- URL rule for `docs/**/index.mdx`;
- URL rule for a non-index docs page;
- blog slug rule;
- release-note slug rule;
- root-home URL;
- per-segment URL encoding;
- no double encoding;
- `NWMURL Library` regression;
- title from front matter;
- title from first H1;
- title from description;
- title from path with warning;
- date normalization;
- heading extraction outside code fences;
- heading, link, and external-component exclusion inside inline and multiline HTML comments;
- heading, link, and external-component exclusion inside inline and multiline MDX/JSX comments;
- comment-like syntax inside fenced code without affecting later visible content;
- heading hierarchy;
- Markdown link extraction;
- nested image links and exclusion of their inner image sources;
- ordinary Markdown image exclusion;
- inline and multiline HTML/MDX `<img src>` exclusion;
- linked HTML images emitting only the enclosing navigable `href`;
- preservation of non-image URL-valued MDX component properties;
- nested-bracket link labels;
- overlap deduplication;
- Markdown escape preservation in `raw_target` and removal in `resolved_url`;
- HTML anchor extraction;
- syntactic link classification;
- ambiguous relative-link preservation;
- multiline `GitHubReadme` extraction;
- multiline `GitHubWikiPage` extraction;
- multiple external sources in one page;
- parent URL selection using nearest included ancestor;
- no synthetic parent creation;
- exclusion of `.github`, macOS metadata, and root support documents;
- deterministic JSON ordering;
- duplicate canonical-URL rejection;
- duplicate corpus-path rejection.

### 21.2 Frozen-corpus regression tests

When `data/raw/documents/` is available, regression tests must verify:

- current page count: 242;
- current generated-page count: 11;
- both public `RESOURCES_PAGE_DOCUMENTATION` pages are present;
- publications is excluded and documented;
- no excluded artifact is included;
- the known title-fallback page has `title_source = first_h1`;
- the Events residue is absent;
- Home labels are present;
- Impact labels are present;
- no heading, link, or external-content declaration originates inside an HTML or MDX/JSX comment;
- no link originates exclusively from an HTML/MDX `<img src>`;
- the NWMURL Library canonical URL is correct;
- no duplicate canonical URLs;
- all parent URLs resolve;
- summary reconciliation;
- two builds are byte-identical.

Frozen-corpus tests may be skipped with an explicit message when the raw corpus is unavailable, but synthetic tests must always run.

---

## 22. Implementation guidance

The script should be modular and testable. Suggested pure or near-pure functions include:

```python
discover_candidate_files(...)
classify_source_group(...)
should_exclude_path(...)
read_and_normalize_text(...)
parse_front_matter(...)
normalize_front_matter_fields(...)
derive_title(...)
normalize_date(...)
build_canonical_url(...)
extract_headings(...)
extract_links(...)
extract_external_content_sources(...)
resolve_parent_urls(...)
build_page_record(...)
build_summary(...)
validate_corpus(...)
write_deterministic_json(...)
sha256_file(...)
sha256_text(...)
```

Implementation should favor explicit, auditable handlers over a universal MDX or React parser.

A Markdown parser may be used when it preserves source order and line information reliably.
When no suitable parser is already available, a small deterministic scanner may handle the
supported Markdown link forms. Regular expressions may be used for narrowly defined
syntactic extraction. Tests must cover multiline MDX components and the common masking of
fenced code, HTML comments, and MDX/JSX comments.

No parser choice may introduce network access or component execution.

---

## 23. Phase A freeze conditions

Phase A may be frozen when:

1. the raw acquisition corrections for Events, Home, and Impact are present;
2. all acceptance criteria pass;
3. the full test suite passes;
4. the generated corpus is manually spot-checked across every source group;
5. two executions are byte-identical;
6. the output SHA-256 is recorded;
7. the script, tests, contract, and generated corpus are committed together;
8. no Phase B ontology mapping has been introduced into the builder.

After the freeze, changes to:

- page-membership rules;
- URL canonicalization;
- title fallback;
- output schema;
- content-preservation rules;
- heading or link extraction;

must be treated as a Phase A contract revision and must update `phase_a_version` and, when structurally necessary, `schema_version`.

---

## 24. Deferred Phase B decisions

The following decisions are intentionally deferred to the CIROH Hub deterministic extraction specification:

- `DocumentationPage` node identity;
- whether the first H1 becomes a `Section`;
- `Section` node IDs and anchors;
- `Link` node identity and whether every link occurrence becomes a node;
- `Subject` normalization;
- person and organization identity rules;
- `isPartOf` and `hasSubPage` edge IDs;
- mapping explicit GitHub links to `Repository` stubs;
- mapping HydroShare links to `DatasetResource` stubs;
- mapping DOI links to paper, dataset, or software identifiers;
- product-catalog-entry classification;
- evidence-span generation;
- alignment with HydroShare and GitHub modules;
- information-density attribute policy for Hub classes.

Phase A must preserve enough explicit source information for these later decisions without implementing them prematurely.

---

## 25. Ratified decisions

The following decisions are ratified for Phase A v1.0.2:

```text
1. The output is page-centric.
2. One public CIROH Hub URL corresponds to one Phase A page record.
3. Selected JavaScript, JSON, YAML, README, and Wiki content is consumed only
   through its materialized Markdown/MDX representation.
4. The builder does not interpret or execute JavaScript.
5. Canonical URL, not source file path, is the page identity anchor.
6. Terminal /index is removed only for docs index pages.
7. Blog and release-note URLs use slug.
8. Spaces in path segments are encoded as %20 and are not rewritten.
9. /publications is deliberately delegated to the paper corpus.
10. Both RESOURCES_PAGE_DOCUMENTATION pages are included.
11. source_path and corpus_path are provenance metadata.
12. File nodes and hasSourceFile are not created for the Hub module v1.
13. Parent hierarchy is based on the nearest included canonical URL ancestor.
14. Phase A preserves structure but performs no semantic interpretation.
15. The current frozen snapshot is expected to contain 242 pages, including
    11 pages materialized from selected JavaScript sources.
```
