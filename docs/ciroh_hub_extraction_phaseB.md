# CIROH Hub Consolidated Corpus → Nodes/Edges — Extraction Contract (Phase B)

**Study 2 — Knowledge-graph construction, deterministic layer (Module 4: Documentation / CIROH Hub)**

**Target implementation:** `src/extraction/deterministic/extract_ciroh_hub.py`  
**Required input:** `data/interim/documents/ciroh_hub_corpus.json`  
**Target output:** `data/interim/documents/ciroh_hub_nodes_edges.json`

**Purpose.** This document is the execution contract for deterministic **Phase B** extraction of the frozen CIROH Hub Phase A corpus. It defines how page-level metadata and mechanically extracted structure are converted into ontology instances and relations. The companion `src/extraction/deterministic/ciroh_hub_extraction_mapping.md` contains the exhaustive field-to-ontology mapping.

**Core boundary.** Phase B maps structured Phase A facts to ontology instances and relations. It does not reopen `data/raw/documents/`, execute JavaScript or MDX, make network calls, infer semantic facts from prose, perform fuzzy entity resolution, or load the final graph database. It emits mention-level entities, exact-identifier targets, inline evidence records, and a complete deterministic extraction report for inspection before LLM extraction, alignment, and graph assembly.

---

## 1. Position in the pipeline

```text
Phase 0 — Acquisition and materialization
-----------------------------------------
data/raw/documents/**/*.md[x]

                    ↓

Phase A — Page-centric preprocessing
------------------------------------
src/preprocessing/build_ciroh_hub_corpus.py

                    ↓

data/interim/documents/ciroh_hub_corpus.json
schema_version: 1.0.0
phase_a_version: 1.0.2

                    ↓

Phase B — Deterministic ontology extraction
-------------------------------------------
src/extraction/deterministic/extract_ciroh_hub.py

                    ↓

data/interim/documents/ciroh_hub_nodes_edges.json

                    ↓

Later stages
------------
LLM extraction from prose
→ exact/fuzzy alignment and consolidation
→ cumulative graph assembly
→ Neo4j/RDF loading
→ evaluation
```

Phase B reads only the consolidated Phase A JSON. `corpus_path`, `source_path`, hashes, structural arrays, and normalized metadata are sufficient for this layer.

---

## 2. Input contract

### 2.1 Required input

```text
data/interim/documents/ciroh_hub_corpus.json
```

Required top-level shape:

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

Phase B must fail fast when:

- `schema_version` is not explicitly supported;
- `phase_a_version` is not explicitly supported;
- `source.artifact_type != "ciroh_hub"`;
- `pages` is missing or is not an array;
- a page lacks `canonical_url`, `page_key`, `title`, `source_group`, `corpus_path`, `source_path`, `content_sha256`, `file_sha256`, `headings`, `links`, `tags`, `authors`, or `warnings`;
- two pages share the same `canonical_url` or `corpus_path`;
- a non-null `parent_url` does not resolve to an included page;
- heading or link ordinals are not unique and contiguous within their page;
- a structural record has an invalid source line or references a nonexistent heading ordinal.

A later additive Phase A version may be accepted through an explicit compatibility list. Silent best-effort parsing is prohibited.

### 2.2 Source-repository configuration

`source_path` identifies the original source file in the CIROH Hub repository. Phase B may therefore create `RepoFile` nodes and instantiate `hasSourceFile`.

Default deterministic configuration:

```text
source repository URL: https://github.com/CIROH-UA/ciroh_hub
source repository ref: main
```

The CLI may expose these as explicit overrides:

```text
--source-repository-url
--source-repository-ref
```

The selected values must be written to the output and participate in determinism. No network lookup is permitted to discover a branch, commit, repository rename, or file existence.

The repository-ref URL is a public locator, not an immutable snapshot identifier. The frozen Phase A hashes remain the local version evidence. For generated JavaScript pages, Phase A preserves the hash of the materialized MDX rather than the original JavaScript bytes; the output must state this limitation explicitly.

### 2.3 Frozen-snapshot regression anchors

The current Phase A v1.0.2 corpus establishes these acceptance anchors:

```text
pages:                                       242
headings:                                  1,583
links:                                     1,767
external-content declarations:                50
  GitHubReadme:                               49
  GitHubWikiPage:                              1
unique raw tag spellings (case-sensitive):   127
tag occurrences:                           1,187
author occurrences:                          119
pages with authors:                           44
pages with parent_url:                       241
source_path values:                          242
  .mdx:                                      231
  .js:                                        11
Phase A warnings:                             14
```

These are regression anchors for the current snapshot, not hard-coded extraction logic. A later corpus conforming to the same schema may contain different counts.

---

## 3. Output contract

Phase B writes:

```text
data/interim/documents/ciroh_hub_nodes_edges.json
```

Top-level shape:

```jsonc
{
  "schema_version": "1.0.0",
  "phase_b_version": "1.0.0",
  "source_schema_version": "1.0.0",
  "source_phase_a_version": "1.0.2",
  "source_type": "ciroh_hub",
  "source_repository": {
    "url": "https://github.com/CIROH-UA/ciroh_hub",
    "ref": "main"
  },
  "nodes": [],
  "edges": [],
  "deferred": [],
  "skipped": [],
  "unresolved": [],
  "warnings": [],
  "stats": {}
}
```

No generation timestamp is included because it would break byte stability.

### 3.1 Node shape

```jsonc
{
  "id": "hub:page:<stable-hash>",
  "class": "DocumentationPage",
  "inventoryId": "A-DC01",
  "attributes": {},
  "canonicalKey": "hub-page-url:https://hub.ciroh.org/docs/products/intro",
  "identityRegime": "canonical_page_url",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "CIROH Products",
    "sourceLocation": "https://hub.ciroh.org/docs/products/intro",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://hub.ciroh.org/docs/products/intro",
    "version": "<content_sha256>"
  },
  "internalLineage": {
    "phaseAField": "pages[canonical_url=...]",
    "corpusPath": "docs/products/intro.mdx",
    "phaseAVersion": "1.0.2"
  }
}
```

### 3.2 Edge shape

```jsonc
{
  "id": "edge:hasSection:<stable-hash>",
  "relation": "hasSection",
  "inventoryId": "C-DC01",
  "source": "hub:page:<stable-hash>",
  "target": "hub:section:<stable-hash>:0001",
  "attributes": {},
  "evidence": {
    "evidenceText": "CIROH products",
    "sourceLocation": "https://hub.ciroh.org/docs/products/intro",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://hub.ciroh.org/docs/products/intro",
    "version": "<content_sha256>"
  },
  "internalLineage": {
    "phaseAField": "headings[ordinal=1]",
    "sourceLine": 24,
    "phaseAVersion": "1.0.2"
  }
}
```

### 3.3 Evidence representation

The ontology requires `EvidenceSpan` for every node and edge. To remain compatible with the existing deterministic interim format, Phase B represents the primary `EvidenceSpan` inline under `evidence`. Graph assembly may later materialize these objects as explicit `EvidenceSpan` nodes and `hasEvidence` relations.

Every emitted node and edge must contain one nonempty primary evidence object with:

```text
evidenceText
sourceLocation
extractionMethod = deterministic
sourceArtifact
version
```

When several source occurrences support one deduplicated semantic edge, the primary declaration is selected deterministically and all occurrences are retained under `attributes.sourceDeclarations`.

---

## 4. Determinism and idempotency

Phase B is a pure function of:

- the Phase A corpus;
- the frozen ontology inventory IDs;
- this Phase B contract and its mapping document;
- the explicit source-repository URL and ref supplied to the run.

It must not use:

- random UUIDs;
- current timestamps;
- network responses;
- LLM/model calls;
- filesystem mtimes;
- unordered-container iteration order;
- repository-, page-, product-, author-, or URL-specific branches not declared by general rules.

Required ordering:

- pages by `(canonical_url, corpus_path)`;
- nodes by `id`;
- edges by `id`;
- report records by `(pageUrl, category, sourcePath, sourceOrdinal, reason)`;
- `sourceDeclarations` by `(sourceLine, linkOrdinal, componentOrdinal, rawTarget)`;
- set-like attributes as sorted arrays.

Stable hashes are lowercase SHA-256 of UTF-8 canonical strings, truncated to 20 hexadecimal characters. Two runs with identical inputs and configuration must produce byte-identical JSON.

---

## 5. Identity model: deterministic mentions before consolidation

Phase B creates deterministic artifact and mention nodes. It does not perform fuzzy cross-page or cross-artifact consolidation.

### 5.1 Curated page identity

```text
id = hub:page:{stable_hash(canonical_url)}
canonicalKey = hub-page-url:{canonical_url}
identityRegime = canonical_page_url
curationStatus = curated
```

One curated `DocumentationPage` is emitted for every Phase A page.

### 5.2 Page-local structural identity

Sections and links are occurrence-level nodes scoped to a page:

```text
hub:section:{page_hash}:{ordinal:04d}
hub:link:{page_hash}:{ordinal:04d}
```

The same heading text or URL appearing twice produces distinct occurrence nodes.

### 5.3 Exact-label metadata identity

Hub subjects are deduplicated only by exact mechanical normalization:

```text
NFKC → trim/collapse whitespace → casefold
```

No stemming, synonym mapping, ontology expansion, or semantic merging is allowed.

### 5.4 Agent mention identity

Authors/contributors and affiliations are source-scoped mentions. Their `canonicalKey` records the best deterministic alignment candidate available, but Phase B does not merge people or organizations across pages.

Permitted candidate regimes include:

- ORCID, when explicitly present;
- GitHub login, when an explicit GitHub profile URL is present;
- normalized name + affiliation;
- normalized name only, as a weaker candidate.

LinkedIn and other profile URLs remain attributes; they do not override the identity regime unless the ontology later approves them as canonical identifiers.

### 5.5 Source file identity

Phase B creates one `RepoFile` for every distinct `source_path`, not for every `corpus_path`.

```text
id = hub:source-file:{stable_hash(source_repository_url|source_path)}
canonicalKey = github-file-path:{normalized_source_repository_url}:{source_path}
identityRegime = repository_relative_path
```

Rules:

- ordinary Markdown/MDX pages use their `.md`/`.mdx` `source_path`;
- generated pages use the original `.js` `source_path`;
- `_generated_js_pages/*.mdx` is a materialized corpus path and must not create a second `RepoFile`;
- a source path reused by multiple public pages creates one `RepoFile` and several `hasSourceFile` edges;
- the frozen corpus currently has 242 distinct source paths.

### 5.6 Exact external targets

Exact target identifiers create `referenced` stubs when the target is outside the curated Hub page set:

- GitHub repository root → `Repository` stub;
- HydroShare resource ID → `DatasetResource` stub;
- exact Hub URL absent from the included page set → `DocumentationPage` stub only when a declared relation such as `announces` requires a target, except known methodological exclusions;
- source Hub repository → one `Repository` stub used to own all `RepoFile` nodes.

Referenced stubs carry exact canonical keys for later alignment. Name similarity never resolves a target.

---

## 6. Two-pass processing architecture

### Pass 1 — Curated nodes and local structure

For every page:

1. create the curated `DocumentationPage`;
2. create its canonical-URL `Identifier` and `hasIdentifier`;
3. create or reuse its source `RepoFile` and instantiate `hasSourceFile`;
4. create every `Section` from `headings[]` and `hasSection`;
5. create every occurrence-level `Link` from `links[]` and `linksTo`;
6. create/reuse exact-label `Subject` nodes and `hasSubject`;
7. create source-scoped `Person` mentions and `hasContributor`;
8. create source-scoped affiliation `Organization` mentions and `affiliatedWith`;
9. index all curated page canonical URLs and normalized aliases.

The pass also creates one referenced source `Repository` for the configured CIROH Hub repository, its URL `Identifier`, and one `hasFile` edge to every source `RepoFile`.

### Pass 2 — Page hierarchy and exact external relations

After all curated pages are indexed:

1. instantiate `isPartOf` from each non-null `parent_url`;
2. instantiate inverse `hasSubPage`;
3. resolve internal Hub links when a declared semantic relation requires a target;
4. canonicalize GitHub URLs and create `referencesRepository` where a repository root is identifiable;
5. parse HydroShare resource URLs and create `referencesDataset`;
6. instantiate deterministic `documents` from `GitHubReadme` declarations;
7. retain `GitHubWikiPage` declarations as repository references while deferring the stronger mirror relation;
8. create `announces` for explicitly identifiable pull-request targets and for internal page links in release notes;
9. record deferred, skipped, unresolved, and warning entries.

This architecture guarantees that target resolution is independent of page order.

---

## 7. Public evidence and internal lineage

Phase B preserves two non-interchangeable provenance channels.

### 7.1 Documentation-page evidence

For page-level facts:

```text
sourceArtifact = canonical_url
sourceLocation = canonical_url
version = content_sha256
```

The public page URL is the user-facing evidence source. `corpus_path`, `source_path`, field paths, source lines, and ordinals are internal lineage.

### 7.2 Section and link evidence

For a heading or link occurrence:

```text
sourceArtifact = page canonical_url
sourceLocation = page canonical_url
evidenceText = exact visible heading/link declaration
version = page content_sha256
```

No Docusaurus anchor or public line anchor is invented. `sourceLine`, heading/link ordinal, and raw target remain in `internalLineage` and node attributes.

### 7.3 Source repository and source-file evidence

Public locator:

```text
{source_repository_url}/blob/{source_repository_ref}/{segment-encoded source_path}
```

For ordinary Markdown/MDX sources:

```text
version = file_sha256
contentAvailable = true
downloaded = true
```

For generated JavaScript sources:

```text
version = materialized:{content_sha256}
contentAvailable = false
downloaded = false
sourceHashAvailable = false
materializedCorpusPath = _generated_js_pages/<page>.mdx
```

This does not claim that the materialized MDX hash is the JavaScript file hash. The original JS path is represented because Phase A explicitly records it as the page source.

### 7.4 Authors, affiliations, and subjects

Evidence uses the public page URL and the exact normalized value:

```text
author evidenceText = name + role + affiliation, as available
affiliation evidenceText = affiliation string
subject evidenceText = original tag string
version = page content_sha256
```

### 7.5 External targets

Referenced target nodes and semantic edges use the originating visible link or explicit external-content declaration as evidence. The exact source occurrence is retained in `sourceDeclarations`.

---

## 8. Deterministic extraction scope

### 8.1 Nodes emitted now

- `DocumentationPage` — A-DC01;
- `Section` — A-DC02;
- `Link` — A-DC03;
- `Subject` — A-P04 (narrative alias A-DC04);
- `Person` — A-AG01;
- `Organization` — A-AG02;
- `Identifier` — A-ID01;
- `RepoFile` — A-C02;
- exact-target `Repository` stubs — A-C01;
- exact-target `DatasetResource` stubs — A-D01;
- referenced `DocumentationPage` stubs for non-curated Hub routes when allowed.

### 8.2 Relations emitted now

- `hasIdentifier` — ID-R1;
- `hasSection` — C-DC01;
- `linksTo` — C-DC03;
- `hasSubject` — C-DC04;
- `hasContributor` — C-DC05;
- `hasSourceFile` — C-DC06;
- `affiliatedWith` — A-AG-R1;
- `isPartOf` — C-DC02;
- `hasSubPage` — C-DC02i;
- source repository `hasFile` — C-C01;
- `documents` — C-DC13, for explicit `GitHubReadme` declarations;
- `referencesRepository` — C-DC14;
- `referencesDataset` — C-DC15;
- `announces` — C-DC18, under the restricted deterministic rules in the mapping.

### 8.3 Deterministic `pageType`

Assign `DocumentationPage.pageType` only under these path/source rules:

| Rule | pageType |
|---|---|
| `source_group == blog` | `blog-post` |
| `source_group == release_notes` | `release-note` |
| `docs/policies/**` | `policy` |
| `docs/services/**` | `service-doc` |
| exactly `docs/products/intro.mdx` | `product-catalog` |
| other `docs/products/**` | `product-doc` |
| `docs/contribute/**` | `guide` |
| generated `/contribute` and `/contribute/develop` pages | `guide` |
| exactly `src/pages/news.mdx` | `news` |
| all other pages | `null` + explicit disposition |

Frozen-snapshot expectations:

```text
product-doc:     86
service-doc:     53
blog-post:       44
release-note:    30
policy:           8
guide:            5
product-catalog:  1
news:              1
null/unclassified:14
```

The mapping must not infer page genre from title words or prose.


### 8.4 Machine-readable ontology compatibility

The extraction uses the canonical IDs from ontology_spec.yaml. Subject is the shared formal class A-P04 (`ciroh:Subject`), corresponding to narrative alias A-DC04. The formal inverse documentation hierarchy relation is C-DC02i (`ciroh:hasSubPage`), corresponding to narrative alias C-DC21. In both mappings, the narrative alias is on the left (`A-DC04`, `C-DC21`) and the machine-readable ID used in output is on the right (`A-P04`, `C-DC02i`). Narrative aliases are traceability labels, not additional formal inventory IDs.

Ontology 0.1.1 now declares `C-DC22 references` as the Documentation-module realization of D-15. CIROH Hub deterministic Phase B v1 does **not** emit C-DC22: every internal-link occurrence remains represented by its `Link` node and `linksTo`, while release-note announcements may additionally use the declared `C-DC18 announces` relation. A future deterministic or hybrid extractor may emit C-DC22 only under an explicitly versioned contract. This formalization correction does not retroactively alter the frozen Phase B v1 output.

The extractor must not maintain a second hard-coded mapping between ontology names and inventory IDs. For every emitted node and edge, the formal inventory ID is resolved at runtime from ontology_spec.yaml by its unique class or relation name. Extraction fails if the name is absent or non-unique. The Markdown mapping remains the behavioral specification and is not parsed at runtime.

---

## 9. Deferred to later extraction/alignment

The deterministic extractor must not mint these from prose or weak structural cues:

- `Procedure`, `Step`, `Parameter`, `Example`, or `Workflow`;
- `Concept`, `Tool`, `ComputationalModel`, `Variable`, `EvaluationMetric`, or `Algorithm` from body text;
- `describesTool`, `describesModel`, `mentionsConcept`, `explainsWorkflow`, `hasProcedure`, `hasStep`, `hasParameter`, or `hasExample`;
- semantic typing of product cards as `Tool` versus `ComputationalModel`;
- `catalogs`, `hasComponent`, `implementedBy`, `describedInPaper`, or `documentedBy` until product/component identity and type are established;
- paper typing from a DOI, publisher URL, Zotero collection URL, or citation prose without a structured cross-module match;
- a stronger `documents`/`mirrors` assertion from `GitHubWikiPage` until that relation is explicitly approved for wiki materialization;
- semantic interpretation of arbitrary `other_absolute` links;
- person/organization consolidation across pages or artifact modules;
- author identity inferred only from an unresolved front-matter identifier;
- Docusaurus anchor generation;
- cross-page workflow reconstruction;
- code-block or admonition interpretation;
- product-category semantics derived from headings or prose.

The LLM layer must read `content_mdx` from the Phase A corpus rather than reopening raw files.

---

## 10. Report categories

### 10.1 `deferred`

Valid source information exists, but interpretation belongs to a later layer.

Examples:

```text
page_type_not_deterministically_classified
product_card_semantic_typing_deferred
product_component_semantics_deferred
doi_target_type_requires_context
publisher_url_target_type_requires_context
github_wiki_mirror_relation_not_declared
author_identifier_without_materialized_identity
other_absolute_link_semantics_unknown
```

### 10.2 `skipped`

The input is intentionally excluded by a ratified rule.

Examples:

```text
known_excluded_route_delegated
image_source_not_a_link
commented_content_not_structural
front_matter_projection_already_consumed
administrative_field_not_nodalized
materialized_corpus_path_not_second_source_file
```

Phase A already removes image-only and commented structural records; Phase B does not re-extract them. These reasons may appear in coverage documentation rather than one report row per absent item.

### 10.3 `unresolved`

A deterministic relation was expected, but a valid target could not be constructed.

Examples:

```text
hub_internal_target_unparseable
github_repository_target_unparseable
invalid_hydroshare_resource_url
parent_target_missing
relative_link_without_resolved_url
external_component_missing_repository_identity
```

### 10.4 `warnings`

All Phase A top-level and page-local warnings are propagated with page identity and internal lineage. They do not create KG nodes.

Every report record follows:

```jsonc
{
  "pageUrl": "https://hub.ciroh.org/example",
  "pagePath": "docs/example.mdx",
  "category": "deferred",
  "sourcePath": "links[ordinal=3]",
  "sourceOrdinal": 3,
  "value": "https://doi.org/10.x/example",
  "reason": "doi_target_type_requires_context"
}
```

---

## 11. Validation requirements

Phase B must validate before writing a successful output.

### 11.1 Structural validation

- every node ID is unique;
- every edge ID is unique;
- every edge source and target exists in `nodes`;
- every node and edge has `class`/`relation`, `inventoryId`, `curationStatus` where applicable, and nonempty evidence;
- `curationStatus ∈ {curated, referenced}`;
- all arrays and set-like attributes are deterministically sorted;
- inventory IDs used by the output exist in `ontology_spec.yaml`;
- every emitted relation satisfies its declared domain and range.

### 11.2 Page and identifier validation

- exactly one curated `DocumentationPage` per Phase A page;
- exactly one canonical-URL `Identifier` and one `hasIdentifier` edge per curated page;
- page title, canonical URL, source group, paths, dates, hashes, and generated flag reconcile with Phase A;
- pageType counts reconcile with the deterministic rules in §8.3.

### 11.3 Source-file validation

- exactly one `hasSourceFile` edge per curated page;
- exactly one `RepoFile` per distinct `source_path`;
- no second `RepoFile` is emitted from `_generated_js_pages/*.mdx` when `generated_from_js=true`;
- the configured source `Repository` owns every source file through `hasFile`;
- ordinary source files use `file_sha256` as version evidence;
- generated JS source files explicitly state that the original source hash is unavailable;
- source paths are repository-relative and cannot escape with `..`;
- source file URLs encode path segments while preserving `/` and case.

### 11.4 Section, link, and subject validation

- one `Section` and one `hasSection` edge per Phase A heading;
- all headings, including the first H1, are instantiated;
- one `Link` and one `linksTo` edge per Phase A link occurrence;
- Link attributes reproduce `anchor_text`, `raw_target`, `resolved_url`, `link_type`, `source_line`, and `heading_ordinal` exactly;
- no image source or commented/fenced declaration reappears as a Link;
- every `heading_ordinal` points to a Section in the same page or is null;
- subject occurrence count equals the total Phase A tag count;
- exact normalized tag identity does not merge nonidentical strings semantically.

### 11.5 Agent validation

- every materialized author with a nonempty name creates one source-scoped Person and one `hasContributor` edge;
- every nonempty affiliation creates one Organization and one `affiliatedWith` edge;
- roles and profile URLs are preserved as attributes;
- unresolved source identifiers do not create unsupported identity claims;
- no fuzzy person or organization merging occurs.

### 11.6 Hierarchy and cross-target validation

- every non-null `parent_url` creates one `isPartOf` and one inverse `hasSubPage`;
- no page hierarchy edge is derived from filesystem path when `parent_url` is null;
- every internal-page target used by a declared semantic edge either resolves to a curated page, becomes an allowed referenced page stub, or is explicitly reported;
- `/publications` remains a known exclusion and is not silently recreated as a curated Hub page;
- every `GitHubReadme` declaration creates one `documents` relation when its repository identity is valid;
- GitHub profile/org/badge URLs do not become Repository stubs;
- every HydroShare reference edge has a valid 32-character resource ID;
- deduplicated semantic edges retain all source occurrences under `sourceDeclarations`.

### 11.7 Provenance and coverage validation

- no public `sourceLocation` is a local filesystem path;
- no raw-root or interim JSON path is presented as public evidence;
- source lines and Phase A field paths occur only in attributes/internal lineage/report records;
- every Phase A field is accounted for by the disposition matrix as node, edge, attribute, evidence, lineage, deferred, skipped, warning, or administrative-only;
- no source field is silently ignored.

---

## 12. Frozen-corpus acceptance criteria

Before the deterministic Hub layer is considered complete, the implementation must demonstrate:

```text
curated DocumentationPage nodes: 242
page URL Identifier nodes/edges:  242 / 242
source RepoFile nodes:            242
hasSourceFile edges:              242
Section nodes/hasSection edges: 1,583 / 1,583
Link nodes/linksTo edges:        1,767 / 1,767
Subject nodes:                    125
hasSubject edges:               1,187
Person mentions:                  119
hasContributor edges:             119
Organization mentions:            119
expected affiliatedWith edges:    119
isPartOf edges:                    241
hasSubPage edges:                  241
GitHubReadme declarations seen:     49
GitHubWikiPage declarations seen:    1
Phase A warnings propagated:        14
```

The 127 distinct case-sensitive source spellings produce 125 normalized Subject identities. The pairs `Hydrology`/`hydrology` and `NSF ACCESS`/`NSF Access` collapse under the approved NFKC, whitespace-collapse, and casefold rule.

The Organization and `affiliatedWith` counts assume the current frozen corpus, in which all 119 materialized authors have nonempty affiliations. The extractor must calculate rather than hard-code them.

Cross-target Repository/Dataset/referenced-page counts and relation counts must be reported after canonicalization and semantic-edge deduplication; they are not prescribed before implementation.

Additional acceptance checks:

- the source repository is represented once as a referenced Repository;
- every source RepoFile is owned by that Repository through `hasFile`;
- generated JavaScript pages point to their original `.js` source path;
- no materialized `_generated_js_pages/*.mdx` file becomes a second RepoFile;
- all 50 external-content declarations are accounted for;
- product cards are preserved structurally and explicitly deferred rather than silently typed;
- all validations pass;
- two independent runs are byte-identical and have the same SHA-256;
- no raw or Phase A file is modified;
- no LLM-only node or edge is emitted.

---

## 13. CLI expectations

At minimum:

```bash
python -m src.extraction.deterministic.extract_ciroh_hub
```

Equivalent explicit invocation:

```bash
python -m src.extraction.deterministic.extract_ciroh_hub \
  --input data/interim/documents/ciroh_hub_corpus.json \
  --output data/interim/documents/ciroh_hub_nodes_edges.json \
  --source-repository-url https://github.com/CIROH-UA/ciroh_hub \
  --source-repository-ref main \
  --validate-frozen-snapshot
```

Useful CLI output:

- input schema/Phase A version;
- pages processed;
- node counts by class;
- edge counts by relation;
- pageType counts;
- report counts by category/reason;
- cross-target resolution counts;
- validation status;
- output path and SHA-256.

---

## 14. Companion artifacts

- `docs/ciroh_hub_preprocessing_phaseA.md` — raw/materialized corpus → page-centric corpus contract;
- `src/extraction/deterministic/ciroh_hub_extraction_mapping.md` — exhaustive Phase B field-to-ontology mapping;
- `docs/ontology_inventory.md` — authoritative entity/relation inventory and stable IDs;
- `src/ontology/ontology_spec.yaml` — machine-readable ontology inventory;
- `docs/ontology_v0.1.md` — conceptual ontology record;
- `docs/decisions_and_coverage.md` — ratified ontology decisions;
- `docs/github_extraction_phaseB.md` / `github_extraction_mapping.md` — deterministic implementation precedent.

*End of CIROH Hub Phase B execution contract.*
