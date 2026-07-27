# CIROH Hub → Ontology — Deterministic Extraction Mapping

**Study 2 — Knowledge-graph construction, deterministic layer (Module 4: Documentation / CIROH Hub)**

**Target implementation:** `src/extraction/deterministic/extract_ciroh_hub.py`  
**Input:** `data/interim/documents/ciroh_hub_corpus.json` (`schema_version: 1.0.0`, `phase_a_version: 1.0.2`)  
**Output:** `data/interim/documents/ciroh_hub_nodes_edges.json`

**Purpose.** This document is the field-level implementation contract between the CIROH Hub Phase A corpus and the Study 2 ontology. For every Phase A field processed deterministically, it defines the node or edge produced, inventory ID, identity rule, evidence construction, deduplication rule, and guard conditions.

**Scope.** Deterministic only. Prose interpretation, product semantic typing, procedures/steps, tools/models/concepts, fuzzy consolidation, and final graph assembly are deferred.

---

## 1. Conventions

### 1.1 Source page

For the rules below, `page` denotes one element of `pages[]` containing at least:

```text
page_key
canonical_url
path
slug
title
title_source
description
last_updated_date
last_updated_date_raw
source_group
corpus_path
source_path
generated_from_js
front_matter
tags
authors
content_mdx
headings
links
external_content_sources
parent_url
file_sha256
content_sha256
warnings
```

Required helper values:

```text
page_hash    = stable_hash(canonical_url)
page_node_id = hub:page:{page_hash}
page_version = content_sha256
```

### 1.2 Deterministic hash

`stable_hash(value)` means:

```text
lowercase hexadecimal SHA-256 of UTF-8 value, truncated to 20 characters
```

Hash inputs use `|` as a separator. Canonicalized URLs are used where the rule explicitly requires URL normalization; otherwise source case is preserved.

### 1.3 Output ID authority

The implementation must validate class and relation IDs against:

```text
src/ontology/ontology_spec.yaml
```

Two documentation-inventory aliases require explicit handling. The left column is
the narrative alias and the right column is the machine-readable ID used in output:

| Meaning | Narrative inventory alias | Machine-readable ID used in output |
|---|---:|---:|
| shared `Subject` class | `A-DC04` | `A-P04` |
| `hasSubPage` relation | `C-DC21` | `C-DC02i` |

Ontology 0.1.1 declares `C-DC22 references` as the Documentation-module realization of D-15. Phase B v1 still does not emit C-DC22. Internal-link occurrences remain represented by `Link` + `linksTo`, and declared `announces` edges are emitted where the restricted rule applies. Future deterministic or hybrid extraction may emit C-DC22 only under an explicitly versioned contract; this declaration does not retroactively alter the frozen v1 output.

### 1.4 Mention-level identity

Except for curated Hub pages, exact-label Subjects, the configured source repository/files, and exact external identifiers, Phase B emits source-scoped mentions.

Every node carries:

```text
id
canonicalKey
identityRegime
curationStatus = curated | referenced
```

Phase B does not merge agents by fuzzy name similarity and does not merge external targets with nodes produced by other modules.

### 1.5 Public evidence builders

#### Page evidence

```text
sourceArtifact = page.canonical_url
sourceLocation = page.canonical_url
version = page.content_sha256
```

#### Structural occurrence evidence

```text
sourceArtifact = page.canonical_url
sourceLocation = page.canonical_url
version = page.content_sha256
```

The source line and ordinal are internal lineage. No public line anchor or Docusaurus anchor is invented.

#### Source repository file

Given explicit run configuration:

```text
source_repository_url
source_repository_ref
```

build:

```text
blob_url(source_path) =
{source_repository_url}/blob/{source_repository_ref}/{segment-encoded source_path}
```

Path encoding preserves `/` and case, rejects `..`, and percent-encodes each segment independently.

#### Internal lineage

```jsonc
{
  "phaseAField": "headings[ordinal=4]",
  "corpusPath": "docs/example/index.mdx",
  "sourcePath": "docs/example/index.mdx",
  "sourceLine": 27,
  "phaseAVersion": "1.0.2"
}
```

Local paths are internal lineage, not public evidence locations.

### 1.6 Primary-declaration selection

When several occurrences support one exact semantic edge, choose primary evidence by:

1. smallest `source_line`;
2. smallest link/component ordinal;
3. lexicographically smallest raw target/path;
4. lexicographically smallest page canonical URL.

Preserve every occurrence under:

```jsonc
"attributes": {
  "sourceDeclarations": []
}
```

Occurrence-level `Link` nodes are never deduplicated.

---

## 2. Canonicalizers and guards

### 2.1 Text key

For tags, names, affiliations, and weak alignment candidates:

```text
Unicode NFKC
→ trim
→ collapse internal whitespace
→ casefold for comparison
```

The original source text remains in attributes and evidence.

### 2.2 Hub URL

Normalize a candidate Hub URL by:

- requiring `https://hub.ciroh.org` after scheme/host normalization;
- removing query and fragment for page-target matching;
- preserving percent-encoded path semantics without double decoding;
- checking exact canonical URL first;
- toggling a terminal slash only when that alias resolves uniquely;
- never deriving a page target from anchor text.

Fragments remain on the `Link.resolvedUrl` attribute even when page matching uses the defragmented URL.

### 2.3 GitHub repository root

Accept URL forms from `github.com` only when an `{owner}/{repository}` pair can be identified.

Canonical result:

```text
https://github.com/{owner}/{repository}
```

Rules:

- remove terminal `.git`;
- strip query and fragment;
- preserve original target in source declarations;
- compare owner/repository case-insensitively;
- allow repository subpaths such as `/blob/`, `/tree/`, `/issues/`, `/pull/`, and `/actions/` after the first two path segments;
- reject user-profile URLs containing only one path segment;
- reject organization, marketplace, settings, login, search, gist, raw-content, attachment, badge, and non-repository routes;
- do not classify `github.com/orgs/{org}` as a repository;
- do not infer a repository from arbitrary text.

Pull-request parser:

```text
https://github.com/{owner}/{repo}/pull/{integer}
```

returns repository root + pull-request number.

### 2.4 HydroShare resource

Accept HTTP(S) URLs with host `hydroshare.org` or a subdomain and path containing:

```text
/resource/{32-character hexadecimal resource_id}
```

Normalize the resource ID to lowercase. A generic HydroShare page such as `/hsapi/` does not create a `DatasetResource` stub.

### 2.5 DOI

Normalize DOI links for reporting only:

- remove `doi:` and `https://doi.org/` prefixes;
- URL-decode once;
- trim whitespace and terminal citation punctuation;
- lowercase the comparison key;
- validate `10.<4–9 digits>/<suffix>`;
- reject image/badge suffixes.

A DOI string alone does not determine whether the target is a Paper, DatasetResource, Repository snapshot, or Tool. Phase B therefore retains the Link and records a deferred target-typing item unless a later cross-module resolver handles it.

### 2.6 Source repository

Normalize the configured source repository URL to an exact GitHub root. The current default is:

```text
https://github.com/CIROH-UA/ciroh_hub
```

The extractor creates one referenced `Repository` node for this root and reuses it for all source-file ownership edges and any page links resolving to the same root.

---

## 3. Node rules

### N1 — Curated DocumentationPage

| Item | Rule |
|---|---|
| Phase A source | each `pages[i]` |
| Class | `DocumentationPage` |
| Inventory ID | `A-DC01` |
| ID | `hub:page:{stable_hash(canonical_url)}` |
| canonicalKey | `hub-page-url:{canonical_url}` |
| identityRegime | `canonical_page_url` |
| curationStatus | `curated` |

Attributes:

```text
canonicalUrl
path
slug
title
titleSource
description
lastUpdatedDate
lastUpdatedDateRaw
sourceGroup
pageType
corpusPath
sourcePath
generatedFromJs
fileSha256
contentSha256
headingCount
linkCount
externalContentSourceCount
tagCount
authorCount
```

`last_updated_date` maps to `lastUpdatedDate`/date-modified semantics. Phase B does not reinterpret it as publication date.

`pageType` uses the deterministic path/source-group table in §7.

Administrative counts and hashes may carry:

```jsonc
"metricExclusion": ["administrative", "identifier_backbone"]
```

Evidence:

```text
evidenceText = title
sourceLocation = canonical_url
sourceArtifact = canonical_url
version = content_sha256
```

`content_mdx` is not copied into the deterministic graph node by default. It remains in Phase A for the LLM layer.

---

### N2 — Page URL Identifier

| Item | Rule |
|---|---|
| Phase A source | `page.canonical_url` |
| Class | `Identifier` |
| Inventory ID | `A-ID01` |
| ID | `hub:identifier:{stable_hash(page_url|canonical_url)}` |
| canonicalKey | `url:{canonical_url}` |
| identityRegime | `exact_url` |
| curationStatus | `curated` |

Attributes:

```text
idType = page_url
value = canonical_url
normalizedValue = canonical_url
```

Evidence uses the page URL and title.

---

### N3 — CIROH Hub source Repository

Created once per run configuration.

| Item | Rule |
|---|---|
| Source | configured `source_repository_url` |
| Class | `Repository` |
| Inventory ID | `A-C01` |
| ID | `hub:repository:{stable_hash(normalized_repository_url)}` |
| canonicalKey | `github-repo-url:{normalized_repository_url.casefold()}` |
| identityRegime | `github_repository_url` |
| curationStatus | `referenced` |

Attributes:

```text
htmlUrl
owner
name
repositoryRef
role = ciroh_hub_source_repository
```

Evidence:

```text
evidenceText = normalized repository URL
sourceLocation = normalized repository URL
sourceArtifact = normalized repository URL
version = configured repository ref
```

The node is a referenced stub until the later alignment stage determines whether the repository exists as a curated GitHub-module node.

---

### N4 — Source Repository Identifier

| Item | Rule |
|---|---|
| Source | normalized source repository URL |
| Class | `Identifier` |
| Inventory ID | `A-ID01` |
| ID | `hub:identifier:{stable_hash(github_repo_url|normalized_url)}` |
| canonicalKey | `github-repo-url:{normalized_url.casefold()}` |
| identityRegime | `exact_url` |
| curationStatus | `referenced` |

Attributes:

```text
idType = github_repository_url
value
normalizedValue
```

---

### N5 — RepoFile source node

| Item | Rule |
|---|---|
| Phase A source | every distinct `page.source_path` |
| Class | `RepoFile` |
| Inventory ID | `A-C02` |
| ID | `hub:source-file:{stable_hash(source_repository_url|source_path)}` |
| canonicalKey | `github-file-path:{source_repository_url.casefold()}:{source_path}` |
| identityRegime | `repository_relative_path` |
| curationStatus | `curated` |

Common attributes:

```text
path = source_path
fileName
extension
fileRole = hub_page_source
selectionReason = public_hub_page_source
sourceRepositoryUrl
sourceRepositoryRef
sourceUrl = blob_url(source_path)
generatedFromJs
```

For `generated_from_js == false`:

```text
downloaded = true
contentAvailable = true
sourceHashAvailable = true
fileSha256 = page.file_sha256
materializedCorpusPath = null
materializedFileSha256 = null
materializedContentSha256 = null
```

For `generated_from_js == true`:

```text
downloaded = false
contentAvailable = false
sourceHashAvailable = false
fileSha256 = null
materializedCorpusPath = page.corpus_path
materializedFileSha256 = page.file_sha256
materializedContentSha256 = page.content_sha256
```

Evidence for ordinary sources:

```text
evidenceText = source_path
sourceLocation = blob_url(source_path)
sourceArtifact = source_repository_url
version = page.file_sha256
```

Evidence for generated JS sources:

```text
evidenceText = source_path + " materialized as " + corpus_path
sourceLocation = blob_url(source_path)
sourceArtifact = source_repository_url
version = materialized:{page.content_sha256}
```

The materialized `_generated_js_pages/*.mdx` path never creates another RepoFile.

If two pages share a source path, create one RepoFile. Choose primary evidence by page canonical URL and retain all page declarations.

---

### N6 — Section occurrence

| Item | Rule |
|---|---|
| Phase A source | every `page.headings[i]` |
| Class | `Section` |
| Inventory ID | `A-DC02` |
| ID | `hub:section:{page_hash}:{ordinal:04d}` |
| canonicalKey | `hub-section:{canonical_url}:heading:{ordinal}` |
| identityRegime | `page_heading_ordinal` |
| curationStatus | `curated` |

Attributes:

```text
pageUrl
ordinal
level
text
rawText
sourceLine
parentHeadingOrdinal
parentSectionId = same-page Section ID or null
```

All headings are instantiated, including the first H1 even when it equals the page title.

No Section→Section ontology edge is emitted because the current ontology does not declare one. `parentSectionId` is a structural attribute retained for later graph projection.

Evidence:

```text
evidenceText = raw_text
sourceLocation = page.canonical_url
sourceArtifact = page.canonical_url
version = page.content_sha256
```

---

### N7 — Link occurrence

| Item | Rule |
|---|---|
| Phase A source | every `page.links[i]` |
| Class | `Link` |
| Inventory ID | `A-DC03` |
| ID | `hub:link:{page_hash}:{ordinal:04d}` |
| canonicalKey | `hub-link-occurrence:{canonical_url}:{ordinal}` |
| identityRegime | `page_link_ordinal` |
| curationStatus | `curated` |

Attributes:

```text
pageUrl
ordinal
anchorText
rawTarget
resolvedUrl
linkType
sourceLine
headingOrdinal
sectionId = same-page Section ID or null
```

Each Phase A link occurrence creates a separate node. No deduplication occurs even when several links share the same target.

Evidence text:

```text
anchorText + " → " + rawTarget
```

or `rawTarget` when the anchor is null.

---

### N8 — Subject

| Item | Rule |
|---|---|
| Phase A source | every value in `page.tags[]` |
| Class | `Subject` |
| Inventory ID | `A-P04` |
| ID | `hub:subject:{stable_hash(normalized_tag)}` |
| canonicalKey | `subject-label:{normalized_tag}` |
| identityRegime | `exact_normalized_label` |
| curationStatus | `curated` |

Attributes:

```text
preferredLabel
normalizedLabel
sourceLabels
```

`preferredLabel` is selected from all exact-normalization-equivalent declarations by:

1. most frequent original spelling;
2. case-sensitive lexical order as tie-breaker.

The Subject node retains all source page/tag declarations. No semantic synonym merge is performed.

---

### N9 — Person author/contributor mention

Created only when `author.name` is nonempty.

| Item | Rule |
|---|---|
| Phase A source | `page.authors[i]` |
| Class | `Person` |
| Inventory ID | `A-AG01` |
| ID | `hub:person:{page_hash}:{author_ordinal:03d}` |
| curationStatus | `curated` |

Candidate-key precedence:

1. explicit ORCID → `orcid:{normalized_orcid}`;
2. explicit GitHub profile login → `github-login:{login.casefold()}`;
3. name + affiliation → `person-name-affiliation:{normalized_name}|{normalized_affiliation}`;
4. name only → `person-name:{normalized_name}`.

`identityRegime` records the selected regime. The source-scoped ID remains page-specific even when canonical keys match across pages.

Attributes:

```text
name
normalizedName
role
affiliation
profileUrl
source
sourceIdentifier
authorOrdinal
alignmentCandidateKey
```

A LinkedIn/profile URL remains an attribute. It is not emitted as an Identifier node in v1.

Evidence:

```text
evidenceText = name; append role and affiliation when available
sourceLocation = page.canonical_url
version = page.content_sha256
```

When `name` is empty and only `source_identifier` exists, emit no Person and record `author_identifier_without_materialized_identity` as deferred.

---

### N10 — Organization affiliation mention

Created for every Person mention whose affiliation is nonempty.

| Item | Rule |
|---|---|
| Phase A source | `page.authors[i].affiliation` |
| Class | `Organization` |
| Inventory ID | `A-AG02` |
| ID | `hub:organization:{page_hash}:{author_ordinal:03d}` |
| canonicalKey | `organization-name:{normalized_affiliation}` |
| identityRegime | `exact_normalized_name_candidate` |
| curationStatus | `curated` |

Attributes:

```text
name
normalizedName
authorOrdinal
alignmentCandidateKey
```

The source-scoped ID prevents premature consolidation. Later alignment may merge matching organization candidates or resolve ROR identifiers.

---

### N11 — Referenced Repository stub

Created from a valid exact GitHub repository root found in:

- a `github` Link;
- a `GitHubReadme` declaration;
- a `GitHubWikiPage` declaration;
- the configured source repository.

| Item | Rule |
|---|---|
| Class | `Repository` |
| Inventory ID | `A-C01` |
| ID | `hub:repository:{stable_hash(normalized_repository_url)}` |
| canonicalKey | `github-repo-url:{normalized_repository_url.casefold()}` |
| identityRegime | `github_repository_url` |
| curationStatus | `referenced` |

Attributes:

```text
htmlUrl
owner
name
originalTargets
sourceKinds
```

The configured source repository and a page-linked repository with the same normalized URL reuse one node.

---

### N12 — External exact Identifier

One Identifier is created per exact external stub key.

#### Repository URL Identifier

```text
idType = github_repository_url
canonicalKey = github-repo-url:{normalized_url.casefold()}
```

#### HydroShare resource Identifier

```text
idType = hydroshare_resource_id
canonicalKey = hydroshare-resource-id:{resource_id}
value = resource_id
```

#### Referenced Hub page URL Identifier

```text
idType = page_url
canonicalKey = url:{normalized_hub_url}
```

| Common item | Rule |
|---|---|
| Class | `Identifier` |
| Inventory ID | `A-ID01` |
| ID | `hub:identifier:{stable_hash(id_type|normalized_value)}` |
| identityRegime | `exact_identifier` |
| curationStatus | same as owner stub |

---

### N13 — Referenced DatasetResource stub

| Item | Rule |
|---|---|
| Source | valid HydroShare resource URL |
| Class | `DatasetResource` |
| Inventory ID | `A-D01` |
| ID | `hub:dataset:hydroshare:{resource_id}` |
| canonicalKey | `hydroshare-resource-id:{resource_id}` |
| identityRegime | `hydroshare_resource_id` |
| curationStatus | `referenced` |

Attributes:

```text
resourceId
resourceUrl
originalTargets
```

The stub is later aligned with the HydroShare curated layer by exact resource ID.

---

### N14 — Referenced DocumentationPage stub

Created only when a declared relation requires a Hub page target and the exact target is absent from the curated page index.

Current v1 use:

- `announces` from a release-note internal link.

| Item | Rule |
|---|---|
| Class | `DocumentationPage` |
| Inventory ID | `A-DC01` |
| ID | `hub:page-ref:{stable_hash(normalized_hub_url)}` |
| canonicalKey | `hub-page-url:{normalized_hub_url}` |
| identityRegime | `canonical_page_url` |
| curationStatus | `referenced` |

Do not create this stub for a route explicitly listed in `known_exclusions`.

Attributes:

```text
canonicalUrl
pageType = null
title = null
sourceGroup = null
```

---

## 4. Edge rules

### E1 — DocumentationPage hasIdentifier Identifier

| Item | Rule |
|---|---|
| Phase A source | `page.canonical_url` |
| Relation | `hasIdentifier` |
| Inventory ID | `ID-R1` |
| Source | N1 page |
| Target | N2 page URL Identifier |

One edge per curated page.

Evidence text is the canonical URL.

---

### E2 — Source Repository hasIdentifier Identifier

| Item | Rule |
|---|---|
| Source | N3 source Repository |
| Relation | `hasIdentifier` |
| Inventory ID | `ID-R1` |
| Target | N4 source repository URL Identifier |

---

### E3 — Source Repository hasFile RepoFile

| Item | Rule |
|---|---|
| Source | N3 source Repository |
| Relation | `hasFile` |
| Inventory ID | `C-C01` |
| Target | N5 RepoFile |

One edge per distinct source path.

Evidence uses the source file blob URL and the file-version rule from N5.

---

### E4 — DocumentationPage hasSourceFile RepoFile

| Item | Rule |
|---|---|
| Phase A source | `page.source_path` |
| Relation | `hasSourceFile` |
| Inventory ID | `C-DC06` |
| Source | N1 page |
| Target | N5 RepoFile for `source_path` |

One edge per curated page.

Attributes:

```text
generatedFromJs
corpusPath
sourcePath
```

For generated pages, the relation targets the original `.js` path. The materialized MDX path remains lineage and does not create another edge or file node.

---

### E5 — DocumentationPage hasSection Section

| Item | Rule |
|---|---|
| Phase A source | every `headings[i]` |
| Relation | `hasSection` |
| Inventory ID | `C-DC01` |
| Source | N1 page |
| Target | N6 Section occurrence |

One edge per heading, including H1.

---

### E6 — DocumentationPage linksTo Link

| Item | Rule |
|---|---|
| Phase A source | every `links[i]` |
| Relation | `linksTo` |
| Inventory ID | `C-DC03` |
| Source | N1 page |
| Target | N7 Link occurrence |

One edge per Link node. No semantic-target deduplication applies.

---

### E7 — DocumentationPage hasSubject Subject

| Item | Rule |
|---|---|
| Phase A source | every `tags[i]` |
| Relation | `hasSubject` |
| Inventory ID | `C-DC04` |
| Source | N1 page |
| Target | N8 Subject |

One edge per page/tag occurrence. Edge evidence uses the original tag spelling from that page.

---

### E8 — DocumentationPage hasContributor Person

| Item | Rule |
|---|---|
| Phase A source | every materialized `authors[i]` with nonempty name |
| Relation | `hasContributor` |
| Inventory ID | `C-DC05` |
| Source | N1 page |
| Target | N9 Person mention |

Attributes:

```text
role = author
sourceRole = author.role
ordinal = author ordinal
```

The documentation ontology uses `hasContributor`; the edge attribute preserves that the Phase A record came from `authors[]`.

---

### E9 — Person affiliatedWith Organization

| Item | Rule |
|---|---|
| Phase A source | nonempty `authors[i].affiliation` |
| Relation | `affiliatedWith` |
| Inventory ID | `A-AG-R1` |
| Source | N9 Person mention |
| Target | N10 Organization mention |

One edge per author affiliation occurrence.

---

### E10 — DocumentationPage isPartOf DocumentationPage

| Item | Rule |
|---|---|
| Phase A source | non-null `page.parent_url` |
| Relation | `isPartOf` |
| Inventory ID | `C-DC02` |
| Source | child N1 page |
| Target | curated N1 page whose canonical URL equals `parent_url` |

The target must exist. Missing parent targets are validation errors, not stubs.

Evidence text:

```text
child canonical URL is part of parent canonical URL
```

Evidence source is the child page; internal lineage points to `parent_url`.

---

### E11 — DocumentationPage hasSubPage DocumentationPage

Inverse of E10.

| Item | Rule |
|---|---|
| Relation | `hasSubPage` |
| Inventory ID | `C-DC02i` |
| Source | parent page |
| Target | child page |

One inverse edge for every E10 edge. No additional path inference is performed.

---

### E12 — External exact target hasIdentifier Identifier

Applies to:

- N11 Repository stub → N12 repository URL Identifier;
- N13 DatasetResource stub → N12 HydroShare resource Identifier;
- N14 referenced DocumentationPage → N12 page URL Identifier.

| Item | Rule |
|---|---|
| Relation | `hasIdentifier` |
| Inventory ID | `ID-R1` |

Evidence uses the originating link/component declaration.

---

### E13 — DocumentationPage referencesRepository Repository

Created when a Phase A GitHub Link or external-content declaration yields a valid exact repository root.

| Item | Rule |
|---|---|
| Relation | `referencesRepository` |
| Inventory ID | `C-DC14` |
| Source | N1 page |
| Target | N11 Repository stub |

Qualifying sources:

```text
page.links[] where link_type == github and repository canonicalization succeeds
page.external_content_sources[] GitHubReadme
page.external_content_sources[] GitHubWikiPage
```

Nonqualifying examples:

```text
GitHub user profile
GitHub organization page
badge/image URL
raw.githubusercontent.com URL
unparseable GitHub route
```

Semantic edge deduplication key:

```text
(source page, referencesRepository, normalized repository URL)
```

All source occurrences remain in `sourceDeclarations`.

---

### E14 — DocumentationPage documents Repository

Created only for explicit `GitHubReadme` declarations.

| Item | Rule |
|---|---|
| Phase A source | `external_content_sources[i].component == GitHubReadme` |
| Relation | `documents` |
| Inventory ID | `C-DC13` |
| Source | N1 page |
| Target | N11 Repository stub |

Edge attributes:

```text
component = GitHubReadme
username
repository
repositoryPath
componentOrdinal
sourceLine
mirrorKind = materialized_repository_file
```

Deduplication key:

```text
(source page, documents, repository root, repositoryPath)
```

A page may create more than one `documents` edge to the same repository when distinct explicit repository paths are materialized.

A `GitHubReadme` declaration also contributes to E13 because the page both documents and references the repository.

A `GitHubWikiPage` declaration creates E13 only. Record `github_wiki_mirror_relation_not_declared` as deferred; do not broaden C-DC13 without an ontology decision.

---

### E15 — DocumentationPage referencesDataset DatasetResource

| Item | Rule |
|---|---|
| Phase A source | link target containing a valid HydroShare resource ID |
| Relation | `referencesDataset` |
| Inventory ID | `C-DC15` |
| Source | N1 page |
| Target | N13 DatasetResource stub |

Qualifying links may have Phase A `link_type == hydroshare` or another absolute type if the resource pattern is exact. Generic HydroShare URLs without `/resource/{id}` remain Link-only.

Deduplication key:

```text
(source page, referencesDataset, resource_id)
```

All occurrences remain in `sourceDeclarations`.

---

### E16 — DocumentationPage announces Repository

Created only when:

- pageType is `release-note` or `blog-post`; and
- a GitHub target is an exact pull-request URL.

| Item | Rule |
|---|---|
| Relation | `announces` |
| Inventory ID | `C-DC18` |
| Source | N1 page |
| Target | N11 Repository stub |

Attributes:

```text
announcementTargetType = pull_request
pullRequestNumber
targetUrl
pageType
sourceDeclarations
```

The same occurrence may also support E13 `referencesRepository`.

A GitHub repository root, issue, action, release, or blob URL without `/pull/{integer}` does not create E16.

---

### E17 — Release-note DocumentationPage announces DocumentationPage

Created only when:

- pageType is `release-note`;
- an internal Hub link has a non-null resolvable target;
- the target is not the source page;
- the target is not a known excluded route.

| Item | Rule |
|---|---|
| Relation | `announces` |
| Inventory ID | `C-DC18` |
| Source | release-note N1 page |
| Target | curated N1 target or N14 referenced page stub |

Attributes:

```text
announcementTargetType = documentation_page
targetUrl
sourceDeclarations
```

This restricted rule operationalizes the ontology evidence locus “dated entry + page links.” It is not applied to generic blogs or non-release documentation.

No generic doc→doc `references` edge is emitted in v1. Although ontology 0.1.1 now declares `C-DC22`, adding that edge requires a future explicitly versioned extraction contract.

---

## 5. PageType mapping

`pageType` is a deterministic attribute on N1. Evaluate rules in the following order:

```text
1. source_group == blog
   → blog-post

2. source_group == release_notes
   → release-note

3. corpus_path starts docs/policies/
   → policy

4. corpus_path starts docs/services/
   → service-doc

5. corpus_path == docs/products/intro.mdx
   → product-catalog

6. corpus_path starts docs/products/
   → product-doc

7. corpus_path starts docs/contribute/
   → guide

8. canonical_url in {
     https://hub.ciroh.org/contribute,
     https://hub.ciroh.org/contribute/develop
   }
   and source_group == generated_js_page
   → guide

9. corpus_path == src/pages/news.mdx
   → news

10. otherwise
    → null
```

Do not infer pageType from title, tags, heading text, or prose.

Frozen counts:

| pageType | Count |
|---|---:|
| `product-doc` | 86 |
| `service-doc` | 53 |
| `blog-post` | 44 |
| `release-note` | 30 |
| `policy` | 8 |
| `guide` | 5 |
| `product-catalog` | 1 |
| `news` | 1 |
| `null` | 14 |

Each null page is recorded as an administrative/deferred disposition, not a validation failure.

---

## 6. Product-card handling

The current product catalog page contains mechanically recoverable product-card structure under headings and links. However, deterministic Phase B cannot safely classify every card target as `Tool` versus `ComputationalModel` because the catalog includes heterogeneous entries such as frameworks, models, methods, courses, and datasets.

Phase B v1 therefore:

1. emits all card headings as `Section` nodes;
2. emits every card URL as a `Link` node;
3. emits exact Repository and DatasetResource references under E13/E15;
4. emits one `product_card_semantic_typing_deferred` report record per detected card heading;
5. does not emit `Tool`, `ComputationalModel`, `catalogs`, or `hasComponent` from the card alone.

A product card may be detected mechanically when a heading is a direct child of the catalog’s product-list section. Detection must use heading hierarchy and source order, not product names.

The later semantic layer may create:

```text
Tool / ComputationalModel
catalogs
hasComponent
implementedBy
describedInPaper
documentedBy
```

using the card’s section range and links as evidence.

---

## 7. Link semantic-disposition matrix

Every N7 Link is retained. Additional semantic handling follows:

| Phase A `link_type` / pattern | Deterministic disposition |
|---|---|
| `github` + valid repository root | N11/N12 + E12/E13 |
| GitHub pull request on blog/release-note | also E16 |
| GitHub user/profile/org/non-repo route | Link only; deferred or unresolved as appropriate |
| `hydroshare` + `/resource/{32hex}` | N13/N12 + E12/E15 |
| generic HydroShare URL | Link only |
| Hub internal on release-note | E17 when resolvable |
| Hub internal on other page | Link only in v1 |
| `anchor` | Link only |
| `mailto` | Link only |
| `relative` with resolved Hub URL on release-note | E17 when resolvable |
| `relative` with null `resolved_url` | Link + unresolved report |
| `doi` or DOI URL | Link + deferred DOI typing |
| publisher/article/Zotero URL | Link + deferred semantic typing when methodologically relevant |
| other absolute URL | Link only; optional deferred summary, not a generic target node |

No URL is turned into a semantic artifact node solely because its anchor text says “paper,” “dataset,” “model,” “tool,” or “documentation.”

---

## 8. External-content declaration mapping

### 8.1 GitHubReadme

For every valid declaration:

```jsonc
{
  "component": "GitHubReadme",
  "username": "CIROH-UA",
  "repository": "NGIAB-CloudInfra",
  "path": "docs/01_GETTING_STARTED.md",
  "source_line": 8,
  "ordinal": 1
}
```

emit:

- N11 Repository stub;
- N12 exact repository Identifier;
- E12 Repository `hasIdentifier`;
- E13 page `referencesRepository`;
- E14 page `documents` Repository, preserving `path`.

The component’s explicit repository file path is an edge attribute. Do not create a second RepoFile for the external repository in the Hub output; the GitHub module owns its file inventory.

### 8.2 GitHubWikiPage

For every valid declaration:

- N11 Repository stub;
- N12 exact repository Identifier;
- E12 Repository `hasIdentifier`;
- E13 page `referencesRepository`;
- deferred record `github_wiki_mirror_relation_not_declared` containing the wiki path.

Do not emit E14 `documents` in v1.

### 8.3 Malformed declaration

If username/repository is absent or cannot form a valid root:

- preserve the Phase A Link/external declaration data;
- emit no Repository target;
- record `external_component_missing_repository_identity` as unresolved.

---

## 9. Field-disposition matrix

Every Phase A field is accounted for below.

### 9.1 Top-level fields

| Phase A field | Disposition |
|---|---|
| `schema_version` | output `source_schema_version`; compatibility gate |
| `phase_a_version` | output `source_phase_a_version`; compatibility gate |
| `source.artifact_type` | source-type gate |
| `source.base_url` | validation/configuration evidence |
| `source.raw_root` | internal administrative lineage only; never public evidence |
| `pages[]` | N1–N14 / E1–E17 as applicable |
| `known_exclusions[]` | output `skipped`/methodological exclusions; no curated page node |
| top-level `warnings[]` | propagated to output warnings |
| `summary` | validation/stats only; no KG node |

### 9.2 Page identity and metadata

| Phase A field | Disposition |
|---|---|
| `page_key` | internal lineage and identity validation; N1 ID derives from canonical URL |
| `canonical_url` | N1 attribute/key; N2; E1; public evidence |
| `path` | N1 attribute |
| `slug` | N1 attribute |
| `title` | N1 attribute/evidence |
| `title_source` | N1 attribute |
| `description` | N1 attribute |
| `last_updated_date` | N1 `lastUpdatedDate` |
| `last_updated_date_raw` | N1 `lastUpdatedDateRaw` |
| `source_group` | N1 attribute + pageType gate |
| `corpus_path` | N1 attribute/internal lineage; generated materialization lineage |
| `source_path` | N5 + E3/E4; N1 attribute |
| `generated_from_js` | N1/N5/E4 attributes and gating |
| `file_sha256` | N1/N5 attribute; source-file evidence where direct |
| `content_sha256` | N1 attribute; page/structure evidence version |
| `parent_url` | E10/E11 |

### 9.3 Rich source content and metadata

| Phase A field | Disposition |
|---|---|
| `front_matter` complete mapping | retained in Phase A; projected known values mapped above; unknown keys administrative/deferred, not silently interpreted |
| `tags[]` | N8 + E7 |
| `authors[]` | N9/N10 + E8/E9 |
| `content_mdx` | deferred input for LLM extraction; not copied to deterministic graph by default |
| `warnings[]` | propagated to output warnings |

### 9.4 Structural arrays

| Phase A field | Disposition |
|---|---|
| `headings[]` | N6 + E5 |
| heading `ordinal`, `level`, `text`, `raw_text`, `source_line`, `parent_heading_ordinal` | N6 attributes/internal lineage |
| `links[]` | N7 + E6; optional N11–N14/E12–E17 by exact patterns |
| link `ordinal`, `anchor_text`, `raw_target`, `resolved_url`, `link_type`, `source_line`, `heading_ordinal` | N7 attributes/internal lineage |
| `external_content_sources[]` | E13/E14 mapping; all declarations accounted for |

### 9.5 Phase A summary fields

| Summary field | Disposition |
|---|---|
| `total_pages` | validation/stats |
| `total_headings` | validation/stats |
| `total_links` | validation/stats |
| `total_external_content_sources` | validation/stats |
| `by_source_group` | validation/stats |
| `generated_from_js` | validation/stats |
| warning counts | validation/stats + propagated warnings |
| exclusion counts | validation/stats |
| author/tag/parent coverage counts | validation/stats |

---

## 10. Deferred to the LLM/semantic layer

Phase B must not mint the following from page prose, heading text, tags, or URL anchor text alone:

- `Procedure`, `Step`, `Workflow`, `Parameter`, `Example`;
- `Concept`, `Tool`, `ComputationalModel`, `Variable`, `EvaluationMetric`, `Algorithm`;
- `describesTool`, `describesModel`, `mentionsConcept`, `explainsWorkflow`;
- `hasProcedure`, `hasStep`, `hasParameter`, `hasExample`;
- `catalogs`, `hasComponent`, `implementedBy`, `documentedBy`, `describedInPaper`;
- paper/dataset/software typing from DOI or publisher URLs without exact structured context;
- semantic interpretation of category, role, capability, limitation, purpose, procedure, or workflow prose;
- cross-page workflow reconstruction;
- person or organization fuzzy alignment;
- Docusaurus anchor reconstruction;
- code-block/admonition semantics;
- `documents` from GitHub Wiki until ontology approval.

The LLM layer reads `page.content_mdx` and may use Section/Link IDs as deterministic anchors.

---

## 11. Output examples

### 11.1 Curated page and source file

```jsonc
{
  "id": "hub:page:<hash>",
  "class": "DocumentationPage",
  "inventoryId": "A-DC01",
  "attributes": {
    "canonicalUrl": "https://hub.ciroh.org/docs/contribute/",
    "title": "Contributing to CIROH Hub",
    "pageType": "guide",
    "sourcePath": "docs/contribute/index.mdx",
    "generatedFromJs": false,
    "contentSha256": "..."
  },
  "canonicalKey": "hub-page-url:https://hub.ciroh.org/docs/contribute/",
  "identityRegime": "canonical_page_url",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "Contributing to CIROH Hub",
    "sourceLocation": "https://hub.ciroh.org/docs/contribute/",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://hub.ciroh.org/docs/contribute/",
    "version": "<content_sha256>"
  }
}
```

```jsonc
{
  "id": "hub:source-file:<hash>",
  "class": "RepoFile",
  "inventoryId": "A-C02",
  "attributes": {
    "path": "docs/contribute/index.mdx",
    "fileRole": "hub_page_source",
    "downloaded": true,
    "contentAvailable": true,
    "fileSha256": "...",
    "sourceUrl": "https://github.com/CIROH-UA/ciroh_hub/blob/main/docs/contribute/index.mdx"
  },
  "canonicalKey": "github-file-path:https://github.com/ciroh-ua/ciroh_hub:docs/contribute/index.mdx",
  "identityRegime": "repository_relative_path",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "docs/contribute/index.mdx",
    "sourceLocation": "https://github.com/CIROH-UA/ciroh_hub/blob/main/docs/contribute/index.mdx",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/ciroh_hub",
    "version": "<file_sha256>"
  }
}
```

### 11.2 Generated JavaScript source

```jsonc
{
  "id": "hub:source-file:<hash>",
  "class": "RepoFile",
  "inventoryId": "A-C02",
  "attributes": {
    "path": "src/pages/index.js",
    "fileRole": "hub_page_source",
    "downloaded": false,
    "contentAvailable": false,
    "sourceHashAvailable": false,
    "generatedFromJs": true,
    "materializedCorpusPath": "_generated_js_pages/home.mdx",
    "materializedFileSha256": "...",
    "materializedContentSha256": "..."
  },
  "evidence": {
    "evidenceText": "src/pages/index.js materialized as _generated_js_pages/home.mdx",
    "sourceLocation": "https://github.com/CIROH-UA/ciroh_hub/blob/main/src/pages/index.js",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/ciroh_hub",
    "version": "materialized:<content_sha256>"
  }
}
```

### 11.3 Explicit GitHubReadme mirror

```jsonc
{
  "id": "edge:documents:<hash>",
  "relation": "documents",
  "inventoryId": "C-DC13",
  "source": "hub:page:<page-hash>",
  "target": "hub:repository:<repo-hash>",
  "attributes": {
    "component": "GitHubReadme",
    "username": "CIROH-UA",
    "repository": "NGIAB-CloudInfra",
    "repositoryPath": "docs/01_GETTING_STARTED.md",
    "componentOrdinal": 1,
    "sourceLine": 8
  },
  "evidence": {
    "evidenceText": "GitHubReadme CIROH-UA/NGIAB-CloudInfra:docs/01_GETTING_STARTED.md",
    "sourceLocation": "https://hub.ciroh.org/docs/products/ngiab/distributions/ngiab-docker/getting-started",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://hub.ciroh.org/docs/products/ngiab/distributions/ngiab-docker/getting-started",
    "version": "<content_sha256>"
  }
}
```

---

## 12. Validation checks specific to this mapping

- every Phase A page produces exactly one curated DocumentationPage;
- every curated page has exactly one page-URL Identifier and `hasIdentifier`;
- the source repository exists exactly once and has an exact URL Identifier;
- every distinct source path produces one RepoFile and one source-repository `hasFile`;
- every page produces exactly one `hasSourceFile`;
- generated pages target `.js` source paths and do not create RepoFiles for materialized `_generated_js_pages/*.mdx`;
- every heading produces one Section and one `hasSection`;
- every link occurrence produces one Link and one `linksTo`;
- no structural record originates from Phase A-excluded comments, fences, or image sources;
- every tag occurrence produces one `hasSubject` and exact tag normalization is deterministic;
- every named author produces one source-scoped Person and one `hasContributor`;
- every nonempty affiliation produces one Organization and one `affiliatedWith`;
- every non-null parent URL produces one `isPartOf` and one `hasSubPage`;
- every GitHubReadme declaration produces a valid `documents` edge or explicit unresolved record;
- GitHubWikiPage produces no undeclared mirror edge;
- GitHub profile/org routes never create Repository nodes;
- every referenced Repository/DatasetResource/DocumentationPage has at least one exact Identifier and `hasIdentifier`;
- no C-DC22 `references` relation is emitted under the frozen Phase B v1 scope;
- product cards produce no unsupported Tool/ComputationalModel typing;
- all Phase A warnings are propagated;
- every Phase A field is accounted for in §9;
- all node/edge IDs and arrays are byte-stable across repeated runs.

Frozen regression anchors:

```text
DocumentationPage curated: 242
RepoFile:                  242
Section:                 1,583
Link:                    1,767
Subject exact nodes:       125
hasSubject:              1,187
Person mentions:           119
Organization mentions:     119
hasContributor:            119
affiliatedWith:            119
isPartOf:                  241
hasSubPage:                241
GitHubReadme declarations:  49
GitHubWikiPage declarations: 1
```

The 127 distinct case-sensitive source spellings produce 125 normalized Subject identities. The pairs `Hydrology`/`hydrology` and `NSF ACCESS`/`NSF Access` collapse under the approved NFKC, whitespace-collapse, and casefold rule.

External stub and semantic-edge totals are calculated by the implementation after exact canonicalization and deduplication.

---

## 13. Implementation boundary for `extract_ciroh_hub.py`

The implementation should use reusable, source-general functions rather than page/product-specific branches:

```text
stable_hash
normalize_text_key
normalize_hub_url
build_hub_page_alias_index
normalize_github_repo_url
parse_github_pull_request
extract_hydroshare_resource_id
normalize_doi
encode_repository_path
build_source_blob_url
derive_page_type
make_page_id
make_section_id
make_link_id
make_source_file_id
make_exact_identifier_id
select_primary_declaration
emit_node
emit_edge
merge_source_declarations
record_deferred
record_skipped
record_unresolved
propagate_warning
validate_inventory_id
validate_domain_range
validate_output
serialize_deterministically
```

No rule may branch on a specific product, page title, author, institution, repository name, HydroShare ID, DOI, or CIROH project. Frozen-corpus names may appear only in tests as regression fixtures, never in production extraction logic.

*End of deterministic CIROH Hub extraction mapping.*
