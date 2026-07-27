# CIROH Publication Corpus → Nodes/Edges — Extraction Contract (Phase B)

**Study 2 — Knowledge-graph construction, deterministic layer (Module 1: Scientific Publications)**

**Target implementation:** `src/extraction/deterministic/extract_publication.py`  
**Required input:** `data/interim/papers/ciroh_publication_corpus.json`  
**Target output:** `data/interim/papers/publication_nodes_edges.json`  
**Companion mapping:** `src/extraction/deterministic/publication_extraction_mapping.md`

---

## 1. Purpose and boundary

This document defines the execution contract for deterministic **Phase B** extraction of the frozen CIROH publication corpus.

Phase B converts the structured facts produced by Publication Phase A into ontology-aligned nodes, edges, evidence, and audit reports. It establishes the deterministic bibliographic and citation backbone before LLM extraction, entity alignment, cumulative graph assembly, and graph loading.

Phase B must:

- create the 228 curated `Paper` nodes;
- create exact `Identifier` nodes and `hasIdentifier` edges;
- create source-scoped `Person` author mentions and ordered `hasAuthor` edges;
- create exact-normalized `Venue` and `Subject` nodes;
- create `publishedIn` and `hasSubject` edges;
- create one shared DOI target per deterministically typed cited DOI;
- create citation or dataset-reference edges only when their ontology domain and range are supported;
- create the deterministic corrigendum relation;
- process availability identifiers conservatively;
- preserve public evidence and private repository lineage separately;
- account for every Phase A field;
- validate the complete output before writing;
- produce byte-stable JSON.

Phase B must not:

- reopen Excel, BibTeX, PDFs, Marker JSON, chunks, or raw Markdown;
- repeat Phase A reconciliation or parsing;
- make network calls;
- query DOI registries or metadata services;
- use an LLM;
- infer scientific claims, methods, findings, models, variables, places, citation functions, or discourse roles;
- consolidate author mentions across papers;
- perform fuzzy entity resolution;
- load Neo4j, RDF, or another graph database;
- materialize `EvidenceSpan` nodes;
- create relations absent from `src/ontology/ontology_spec.yaml`.

---

## 2. Position in the pipeline

```text
Curated publication sources
---------------------------
Excel + BibTeX + PDFs + Marker outputs + curation overrides

                    ↓

Phase A — deterministic corpus preprocessing
--------------------------------------------
src/preprocessing/build_publication_corpus.py

                    ↓

data/interim/papers/ciroh_publication_corpus.json
schema_version: 1.1.0
phase_a_version: 1.0.9

                    ↓

Phase B — deterministic ontology extraction
-------------------------------------------
src/extraction/deterministic/extract_publication.py

                    ↓

data/interim/papers/publication_nodes_edges.json

                    ↓

Later stages
------------
LLM extraction from canonical Markdown
→ exact/fuzzy alignment and consolidation
→ cumulative graph assembly
→ Neo4j/RDF loading
→ intrinsic and extrinsic evaluation
```

Phase B reads the consolidated Phase A JSON as its sole publication-data input. The ontology specification and the two Phase B Markdown documents are implementation specifications, not data sources.

The canonical Markdown remains available to later LLM extraction through `source_files.markdown_path`, but Phase B does not open it.

---

## 3. Input contract

### 3.1 Required file

```text
data/interim/papers/ciroh_publication_corpus.json
```

Required top-level shape:

```jsonc
{
  "schema_version": "1.1.0",
  "phase_a_version": "1.0.9",
  "source": {
    "artifact_type": "publication"
  },
  "publications": [],
  "known_exclusions": [],
  "warnings": [],
  "summary": {}
}
```

The implementation must explicitly support:

```text
source schema version: 1.1.0
source Phase A version: 1.0.9
```

A later compatible version may be accepted only through an explicit compatibility list and tests. Silent best-effort parsing is prohibited.

### 3.2 Required publication record

Every `publications[]` item must provide the complete Phase A structure:

```text
local_paper_id
canonical_artifact_id
canonical_identifier
identifiers
record_type
curation_status
bibliographic
content
document_structure
source_files
bibliographic_relations
reconciliation
```

Required nested content:

```text
bibliographic.title
bibliographic.authors
bibliographic.year
bibliographic.venue
bibliographic.volume
bibliographic.issue
bibliographic.pages
bibliographic.publisher
bibliographic.language
bibliographic.abstract
bibliographic.abstract_source

content.headings
content.explicit_keywords
content.reference_dois
content.availability_identifiers

document_structure.page_count
document_structure.table_of_contents

bibliographic_relations.correction_of
```

### 3.3 Fail-fast input validation

Phase B must fail before extraction when:

- the input file is missing or invalid JSON;
- an unsupported schema or Phase A version is supplied;
- `source.artifact_type != "publication"`;
- `publications` is absent or is not an array;
- the Phase A summary does not reconcile with the records;
- publication IDs or canonical artifact IDs are duplicated;
- a curated publication lacks title, year, venue, authors, or canonical identity;
- a DOI or URL identifier is malformed or inconsistent with its URI;
- author positions are missing, duplicated, or noncontiguous;
- a keyword or reference DOI is duplicated within one publication;
- an evidence line range is invalid;
- `correction_of` is malformed;
- a source path is absolute or escapes the expected repository-relative form;
- a forbidden control character occurs in any input string;
- any current frozen invariant required by §14 fails.

Phase B must not repair a broken Phase A corpus. It must report the contradiction and stop.

---

## 4. Output contract

Phase B writes:

```text
data/interim/papers/publication_nodes_edges.json
```

Top-level shape:

```jsonc
{
  "schema_version": "1.0.0",
  "phase_b_version": "1.0.2",
  "source_schema_version": "1.1.0",
  "source_phase_a_version": "1.0.9",
  "source_type": "publication",
  "nodes": [],
  "edges": [],
  "deferred": [],
  "skipped": [],
  "unresolved": [],
  "warnings": [],
  "stats": {}
}
```

No current timestamp, host-specific path, random identifier, or environment-dependent value may be emitted.

### 4.1 Node shape

Every node must contain exactly the common structural keys:

```jsonc
{
  "id": "publication:paper:<stable-hash>",
  "class": "Paper",
  "inventoryId": "A-P01",
  "attributes": {},
  "canonicalKey": "doi:10.xxxx/example",
  "identityRegime": "doi",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "Publication title",
    "sourceLocation": "https://doi.org/10.xxxx/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.xxxx/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "publications[canonical_artifact_id=...]",
    "localPaperId": "1",
    "markdownPath": "data/raw/papers/markdowns/1/markdown/1_md.md",
    "phaseAVersion": "1.0.9"
  }
}
```

### 4.2 Edge shape

Every edge must contain exactly the common structural keys:

```jsonc
{
  "id": "publication:edge:hasAuthor:<stable-hash>",
  "relation": "hasAuthor",
  "inventoryId": "C-P01",
  "source": "publication:paper:<stable-hash>",
  "target": "publication:person:<stable-hash>:0001",
  "attributes": {
    "authorPosition": 1
  },
  "evidence": {
    "evidenceText": "Jane Doe",
    "sourceLocation": "https://doi.org/10.xxxx/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.xxxx/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "bibliographic.authors[position=1]",
    "localPaperId": "1",
    "phaseAVersion": "1.0.9"
  }
}
```

### 4.3 Evidence representation

The ontology requires evidence for graph facts. The deterministic interim format represents the primary `EvidenceSpan` inline under `evidence`. A later assembly step may reify it as an `EvidenceSpan` node with `hasEvidence`.

Every node and edge must have one nonempty primary evidence object containing:

```text
evidenceText
sourceLocation
extractionMethod = deterministic
sourceArtifact
version
```

Rules:

- `sourceArtifact` is the public canonical artifact of the publication supplying the evidence.
- `sourceLocation` is also the public canonical artifact unless a distinct public locator is explicitly available.
- local paths and line numbers belong only in `internalLineage`;
- no DOI fragment, PDF page anchor, or Markdown anchor may be invented;
- `version` is `phase-a:1.0.9` because Phase A contains no immutable public document hash;
- merged exact nodes retain all supporting occurrences in deterministic `attributes.sourceDeclarations`;
- citation edges retain all Phase A occurrences in deterministic `attributes.sourceDeclarations`.

### 4.4 Report record shape

`deferred`, `skipped`, `unresolved`, and `warnings` use deterministic records containing the applicable subset of:

```jsonc
{
  "publicationId": "https://doi.org/...",
  "category": "ambiguous_cited_doi_type",
  "phaseAField": "content.reference_dois[12]",
  "reason": "repository DOI namespace lacks explicit resource type",
  "value": "10.5281/zenodo.12345",
  "sourceLine": 412
}
```

Report arrays are part of the scientific audit trail. They must not contain absolute paths or unserializable objects.

---

## 5. Determinism and idempotency

Phase B is a pure function of:

- the Phase A corpus;
- `src/ontology/ontology_spec.yaml`;
- this execution contract;
- `publication_extraction_mapping.md`.

It must not depend on:

- random UUIDs;
- current time;
- network responses;
- LLM output;
- filesystem mtimes;
- hash-randomized collection order;
- individual publication IDs, titles, authors, venues, keywords, or DOI-specific branches outside general canonicalization and provider rules.

### 5.1 Stable hash

`stable_hash(value)` means:

```text
lowercase SHA-256 of the UTF-8 canonical string,
truncated to 20 hexadecimal characters
```

Hash components use `|` separators and the canonicalized values defined by the mapping.

### 5.2 Required ordering

Before serialization:

- nodes sorted by `id`;
- edges sorted by `id`;
- report records sorted by `(publicationId, category, phaseAField, sourceLine, reason, value)`;
- source declarations sorted by `(sourceArtifact, lineStart, lineEnd, phaseAField, evidenceText)`;
- set-like attributes represented as sorted arrays;
- author order preserved by `position`;
- keyword order on a paper preserved through edge evidence, even though Subject nodes are globally deduplicated.

Serialization must use UTF-8, `ensure_ascii=False`, sorted object keys, two-space indentation, and exactly one terminal newline.

Two independent runs over identical inputs must be byte-identical.

---

## 6. Identity model

### 6.1 Curated Paper

A curated publication is identified by its exact canonical public identifier:

```text
DOI present: canonicalKey = doi:{normalized DOI}
otherwise:   canonicalKey = url:{normalized canonical URL}
```

Node ID:

```text
publication:paper:{stable_hash(canonicalKey)}
```

The local paper ID is internal lineage only and never becomes a public `Identifier`.

### 6.2 Author mentions

Each author occurrence creates a distinct source-scoped `Person` node:

```text
publication:person:{paper_hash}:{position as four digits}
```

Two papers sharing the same author name therefore create two Person mentions. They may share the same weak alignment `canonicalKey`, but Phase B does not merge them.

This preserves mention-level identity for later consolidation evaluation.

### 6.3 Exact-normalized metadata entities

Within the publication module:

- `Venue` nodes are deduplicated by exact normalized venue label;
- `Subject` nodes are deduplicated by exact normalized keyword value;
- `Identifier` nodes are deduplicated by exact `(scheme, normalized value)`;
- exact DOI targets are deduplicated globally after deterministic target typing.

No fuzzy synonym, abbreviation, name, or semantic consolidation occurs.

### 6.4 Cited DOI targets

A DOI appearing in several papers must resolve to one target node, not one target per citation occurrence.

The extractor first indexes all curated Paper DOI values. It then performs one global deterministic type decision for each external cited DOI.

Possible target classes:

```text
Paper
DatasetResource
Repository
Tool
```

A DOI must not produce nodes of multiple classes in the same Phase B output.

When target type is unresolved, the DOI is retained in `unresolved` or `deferred`; it must not be guessed into `Paper`.

### 6.5 Availability mentions

A generic DOI or URL in a pure data-availability section does not automatically prove a globally canonical dataset entity. Phase B first reuses an exact `DatasetResource` already established by strong deterministic evidence in the same run. When no such exact resource exists, it creates a source-scoped `DatasetMention`:

```text
publication:dataset-mention:{paper_hash}:{stable_hash(scheme|normalized_value)}
```

The mention carries the identifier as attributes and a weak exact alignment key for later consolidation.

---

## 7. Deterministic graph scope

### 7.1 Nodes

Phase B may emit only ontology-declared instances needed by the mapping:

| Class | Inventory ID | Identity regime |
|---|---:|---|
| `Paper` | `A-P01` | DOI or canonical URL |
| `Venue` | `A-P02` | exact normalized name |
| `Person` | `A-AG01` | paper-scoped author mention |
| `Subject` | `A-P04` | exact normalized keyword |
| `Identifier` | `A-ID01` | exact scheme + value |
| `DatasetMention` | `A-P25` | paper-scoped availability mention |
| `DatasetResource` | `A-D01` | exact HydroShare/resource DOI or other strongly typed identifier |
| `Repository` | `A-C01` | exact GitHub repository URL or strongly typed repository DOI |
| `Tool` | `A-DOM02` | strongly and explicitly typed software DOI |

No discourse-unit node is created deterministically.

### 7.2 Edges

Phase B may emit only these relations:

| Relation | Inventory ID | Domain → range |
|---|---:|---|
| `hasAuthor` | `C-P01` | Paper → Person |
| `publishedIn` | `C-P02` | Paper → Venue |
| `hasSubject` | `C-P03` | Paper → Subject |
| `hasIdentifier` | `C-P04` | Paper → Identifier |
| `cites` | `C-P21` | Paper → Paper |
| `corrects` | `C-P22` | Paper → Paper |
| `usesDataset` | `C-P20` | Paper → DatasetMention/DatasetResource |
| `referencesDataset` | `C-P29` | Paper → DatasetResource |
| `hasIdentifier` | `C-D04` | DatasetResource → Identifier |
| `hasIdentifier` | `C-C06` | Repository → Identifier |

The relation name may repeat with different inventory IDs where the module-specific mapping requires it.

No generic Paper→Repository or Paper→Tool relation is declared for bibliographic presence alone. Such relation candidates are deferred.

---

## 8. Paper, author, venue, subject, and identifier rules

### 8.1 Paper attributes

A curated Paper node carries:

```text
title
recordType
year
volume
issue
pages
publisher
language
abstract
abstractSourceType
canonicalArtifactId
pageCount
headingCount
headings
tableOfContentsEntryCount
tableOfContents
```

`headings` preserve only:

```text
level
text
normalizedText
lineNumber
```

`tableOfContents` preserves only:

```text
title
pageId
headingLevel
```

Marker polygons are not copied. They are administrative/visual geometry and remain in Phase A.

The complete Markdown and complete abstract source record are not copied. The canonical Markdown path remains in `internalLineage`.

### 8.2 Author mentions

Each ordered Phase A author creates one Person and one `hasAuthor`.

Person attributes preserve:

```text
displayName
givenNames
familyName
nameParticles
suffix
literalName
rawBibtex
authorPosition
```

The edge also carries `authorPosition`.

No author mention is omitted because its name matches another mention.

### 8.3 Venue

Every curated paper creates one `publishedIn` edge. Exact-normalized equal venue labels share one Venue node. Abbreviations and alternative spellings remain separate.

### 8.4 Subjects

Every emitted Phase A explicit keyword creates one `hasSubject` edge. Equal normalized keyword values share one Subject node.

Warnings for deferred or rejected Phase A keyword declarations do not create Subject nodes.

### 8.5 Identifiers

Every curated paper identifier creates:

- one exact Identifier node, reused when already present;
- one Paper `hasIdentifier` edge.

A DOI Identifier and a URL Identifier remain different nodes even when the URL is a DOI resolver.

---

## 9. Citation strategy

### 9.1 Two-pass curated resolution

Before processing citations:

1. create all 228 curated Paper nodes;
2. index the 227 curated DOI values;
3. index the one URL-only publication separately.

When a cited DOI equals a curated paper DOI, the citation targets the curated Paper node.

### 9.2 Global DOI target typing

For every external DOI, classify every Phase A `occurrences[].reference_text` independently before minting a target. The complete Phase A occurrence is the maximum evidence boundary. Within a multi-DOI occurrence, the target-local segment begins and ends at the closest neighboring DOI declarations or reference boundaries; evidence cannot cross either boundary.

Each occurrence receives one auditable decision:

```text
curated_paper
untyped_scholarly_reference
strong_dataset
strong_repository
strong_tool
ambiguous
conflicting
```

Type decision order:

1. **Curated DOI match** → `Paper`.
2. **Exact HydroShare DOI namespace or exact HydroShare resource evidence** → `DatasetResource`.
3. **One or more consistent strong occurrence-local dataset declarations** → `DatasetResource`.
4. **One or more consistent strong occurrence-local repository declarations or exact attributable GitHub repository evidence** → `Repository`.
5. **One or more consistent strong occurrence-local software declarations** → `Tool`.
6. **Known multi-type repository DOI namespace without an explicit type** → unresolved/deferred.
7. **No non-paper signal** → `Paper` referenced stub.

Strong labels must be structurally associated publication metadata such as bracketed or parenthetical resource types (`[Data set]`, `[Dataset]`, `[Software]`, `(Computer software)`), an exact repository declaration, or an exact recognized resource URL. Natural title or prose language—including “data repository,” “software version,” a journal name, or “Journal of Open Source Software”—is weak evidence and never independently assigns a non-Paper class. A loose label embedded in an otherwise structurally scholarly journal citation is likewise not sufficient.

Typing must use occurrence-bounded, target-local evidence. Repeated Phase A occurrences are classified independently. When a Phase A reference text contains multiple DOI values, a non-Paper label may be used only when it can be mechanically and uniquely associated with the target DOI. A marker after the target or beyond a neighboring DOI declaration is not borrowed. An unattributable marker provides no strong signal.

Global aggregation preserves every occurrence decision in deterministic `sourceDeclarations`; when no target is emitted, the same complete occurrence audit is retained in the deferred/unresolved report value. Untyped scholarly occurrences do not conflict with a consistent strong class. Conflicting strong classes produce one unresolved global disposition and no target. One weak or contaminated occurrence cannot retype the DOI, and one DOI cannot create more than one global citation-target class.

Known multi-type repository namespaces are configuration constants documented in the mapping. They are ambiguity guards, not type assignments.

Conflicting strong type evidence for one DOI is fatal to that target’s graph emission and must produce an `unresolved` record.

### 9.3 Citation edges

For a Paper target:

```text
source Paper —cites→ target Paper
```

For a deterministically typed DatasetResource target:

```text
source Paper —referencesDataset→ target DatasetResource
```

For Repository or Tool targets:

- emit the typed referenced node when supported by strong evidence;
- preserve its DOI identity as declared by the mapping;
- do not emit an undeclared generic citation relation;
- record the missing semantic relation under `deferred`.

### 9.4 Shared targets and occurrence evidence

One source Paper and one target create at most one semantic edge. The edge preserves every Phase A occurrence under `attributes.sourceDeclarations`.

Different source papers citing the same DOI create different edges to the same target node.

Reference location belongs to the edge evidence, not to the target node’s intrinsic attributes.

### 9.5 Self-reference artifacts

When a cited DOI equals the source paper’s own DOI:

- do not create a self-loop;
- record `self_reference_doi_matches_source` under `skipped`;
- preserve the original Phase A record unchanged.

The frozen corpus currently contains publisher headers or “How to cite this article” blocks that create such records. They are not scholarly self-citations.

### 9.6 Typed citation function

Phase B emits only generic deterministic `cites` or `referencesDataset`.

It does not emit:

```text
cito:citesAsEvidence
cito:usesMethodIn
cito:extends
supports
contrastsWith
usesDatasetFrom
```

These require in-text citation-marker resolution and semantic context from the body and are deferred to the later LLM/hybrid layer.

---

## 10. Availability-identifier strategy

Availability sections are evidence that an identifier is associated with data, code, or software availability, but they do not all establish the same artifact type or relation. This section-specific decision table is authoritative: exact availability rules run first, and a weak, default-Paper, ambiguous, Repository, or Tool citation decision cannot suppress the availability disposition.

### 10.1 Exact HydroShare target

A valid URL containing:

```text
hydroshare.org/resource/{32-character hexadecimal resource_id}
```

or an exact recognized HydroShare DOI creates/reuses a referenced `DatasetResource` and:

```text
Paper —usesDataset→ DatasetResource
```

The resource receives an exact Identifier and `hasIdentifier`.

### 10.2 Exact GitHub repository target

A URL that mechanically resolves to:

```text
https://github.com/{owner}/{repository}
```

creates/reuses a referenced `Repository` and its URL Identifier.

The exact Repository identity is the case-folded root URL. Both the Repository ID and `canonicalKey` derive from that same identity, and the URL Identifier uses the same normalized root. `htmlUrl`, `owner`, and `name` preserve the lexicographically first normalized source form so case-only declarations merge deterministically regardless of input order.

Phase B does not emit Paper→Repository merely because the repository appears in an availability section. The candidate relation is recorded under `deferred`.

Profile, organization, issue, pull request, action, attachment, raw-content, and badge URLs must not be treated as repository roots unless the canonical owner/repository pair can be extracted by the general URL rule.

### 10.3 Pure data-availability identifier

For a DOI or URL in `data_availability`, Phase B first checks whether the exact identifier already resolves to a `DatasetResource` established by strong deterministic evidence in the current run. If so, Phase B reuses that node, merges the availability source declaration, reuses its Identifier, and emits `Paper —usesDataset→ DatasetResource` with the availability evidence and lineage.

When no exact strongly typed DatasetResource exists:

- create a paper-scoped `DatasetMention`;
- store scheme, value, URI, section category, and section title as attributes;
- emit `Paper —usesDataset→ DatasetMention`;
- do not promote it to a global DatasetResource in Phase B.

This fallback also applies when the same identifier is globally classified as a Paper, Tool, Repository, ambiguous target, or untyped citation. The DatasetMention records only how this source paper presents the identifier; it does not retype the global DOI target. Reusing an existing DatasetResource likewise does not retype any other target. Exact authorized HydroShare identities are handled by §10.1 first.

### 10.4 Code, software, and mixed sections

For `code_availability`, `software_availability`, `data_and_code_availability`, or `code_and_data_availability`:

- exact HydroShare targets still map to DatasetResource;
- exact GitHub repository targets still map to Repository with a deferred Paper relation;
- strongly typed software/repository DOI targets may create referenced stubs;
- a generic DOI or URL with unresolved type is deferred;
- no `usesDataset`, `usesTool`, or repository relation is guessed from the section label alone.

### 10.5 Accounting

Every one of the 299 availability identifiers must resolve to exactly one disposition:

```text
DatasetResource node + usesDataset
DatasetMention node + usesDataset
Repository/Tool node + deferred relation
deferred unresolved type
skipped duplicate or invalid record
```

Phase A already guarantees no duplicate availability identifier within one paper. Phase B must preserve that invariant.

### 10.6 Phase A deferred DOI candidates

Every Phase A `deferred_reference_doi_candidate` warning propagates exactly once as an audit warning. Its candidate is not an accepted reference or availability identifier and creates no target node, Identifier, citation edge, availability edge, or accepted-source count.

---

## 11. Provenance and lineage

### 11.1 Public evidence

Public evidence always uses the publication’s canonical artifact:

```text
sourceArtifact = canonical_artifact_id
sourceLocation = canonical_artifact_id
version = phase-a:1.0.9
```

For a merged external target, the primary evidence is selected deterministically from all citing publications and every occurrence is preserved under `sourceDeclarations`.

### 11.2 Internal lineage

Internal lineage may contain:

```text
phaseAField
localPaperId
markdownPath
pdfPath
section
lineStart
lineEnd
authorPosition
phaseAVersion
```

Local paths must never appear in public `evidence`.

### 11.3 Reconciliation information

Excel/BibTeX match method, overrides, conflicts, source-file paths, and Phase A warnings do not create ontology nodes. They are preserved as:

- Paper administrative attributes where compact and useful;
- `internalLineage`;
- propagated warnings;
- `stats`;
- field-disposition accounting.

---

## 12. Deferred semantic extraction

The deterministic extractor must not create the following from abstracts, headings, titles, reference text, or availability prose:

- discourse units (`ResearchProblem`, `Method`, `Finding`, `Conclusion`, etc.);
- `ComputationalModel`, `Variable`, `Concept`, `Algorithm`, `Parameter`, or `EvaluationMetric` mentions;
- `usesModel`, `mentionsModel`, `usesTool`, `mentionsVariable`, `studiesFeature`, or `studiesPlace`;
- scientific claims or claim-support relations;
- in-text citation anchors;
- citation intent or rhetorical function;
- author or venue disambiguation;
- paper–repository implementation relations;
- full-text chunks or embeddings.

The later LLM/hybrid publication extractor will load the canonical Markdown through Phase A lineage and may enrich the deterministic backbone.

---

## 13. Field-disposition requirement

Every Phase A field must be accounted for by the companion mapping as one of:

```text
node
edge
node attribute
edge attribute
evidence
internal lineage
deferred
skipped
unresolved
warning
validation-only
administrative-only
```

No field may be silently ignored.

The implementation should maintain a field-coverage registry and validate that the current Phase A schema is completely covered.

---

## 14. Frozen-snapshot anchors

The current Phase A corpus establishes the following source anchors:

```text
publications:                         228
curated DOI identities:              227
curated URL-only identities:           1
curated identifier declarations:     455
author occurrences:                1,602
exact-normalized venues:              84
papers with abstracts:               129
papers with explicit keywords:        70
keyword occurrences:                 373
exact-normalized keyword values:      317
papers with reference DOI values:     210
reference DOI records:              8,856
reference DOI occurrences:          8,963
unique cited DOI values:            6,720
cited DOI values overlapping corpus:  112
self-reference artifacts:              23
non-self reference records:         8,833
non-self references to curated DOI:   297
unique curated cited targets:          98
unique external cited DOI values:   6,610
papers with availability IDs:          73
availability identifiers:             299
  URL:                                252
  DOI:                                 47
  data_availability:                  240
  software_availability:               27
  code_availability:                   18
  data_and_code_availability:          14
corrigendum relations:                  1
Phase A warnings:                     147
deferred reference DOI candidates:      4
```

Required deterministic graph anchors:

```text
curated Paper nodes:                 228
Person mention nodes:              1,602
hasAuthor edges:                   1,602
Venue nodes:                          84
publishedIn edges:                   228
Subject nodes:                        317
hasSubject edges:                     373
curated Paper hasIdentifier edges:    455
corrects edges:                         1
```

External target counts and citation-edge counts by target class are calculated after the Phase B type audit. They must reconcile exactly with the 8,856 source reference records through emitted edges plus skipped/deferred/unresolved dispositions.

Availability dispositions must reconcile exactly with 299.

Counts are regression anchors for this frozen snapshot, not production branches.

---

## 15. Output validation

Validation must reject the output when:

### 15.1 Structural integrity

- top-level versions are wrong;
- required arrays or keys are missing;
- node or edge IDs are duplicated;
- nodes or edges are not sorted;
- an edge references a missing node;
- a node or edge lacks complete evidence or lineage;
- a report record is malformed;
- a forbidden control character remains;
- serialization is not byte-stable.

### 15.2 Ontology integrity

- a class/inventory pair is not declared;
- a relation/inventory pair is not declared;
- an edge violates ontology domain or range;
- an abstract ontology class is instantiated;
- an undeclared Paper→Repository or Paper→Tool edge is emitted;
- `cites` targets anything other than Paper;
- `referencesDataset` (`C-P29`) or `usesDataset` targets an invalid class.

### 15.3 Identity integrity

- two nodes have the same ID;
- one DOI is assigned to more than one target class;
- a cited DOI that matches a curated Paper creates a duplicate referenced Paper;
- equal exact Venue, Subject, or Identifier keys create duplicate nodes;
- authors from separate papers are merged;
- author positions are lost;
- local paper IDs become public identifiers;
- a self-reference loop is emitted.

### 15.4 Coverage integrity

- curated Paper, author, venue, subject, identifier, or corrigendum anchors differ;
- citation source records do not reconcile;
- availability records do not reconcile;
- a Phase A field lacks a declared disposition;
- Phase A warnings or known exclusions disappear without an administrative report.

### 15.5 Provenance integrity

- a local path appears in public evidence;
- evidence uses another publication as `sourceArtifact`;
- line numbers are placed in invented public URL fragments;
- merged nodes or edges lose source declarations;
- evidence text is empty.

The extractor must validate completely before replacing an existing output file.

---

## 16. Reports and statistics

`stats` must be computed from emitted output and reports. At minimum it contains:

```text
sourcePublicationCount
sourceAuthorOccurrenceCount
sourceKeywordOccurrenceCount
sourceReferenceDoiCount
sourceAvailabilityIdentifierCount

nodeCount
edgeCount
nodesByClass
edgesByRelation
curatedNodeCount
referencedNodeCount

citationRecordsProcessed
citationSelfReferencesSkipped
citationEdgesToCuratedPapers
citationEdgesToReferencedPapers
citationDatasetReferences
citationRepositoryTargets
citationToolTargets
citationTargetsDeferred
uniqueCitationTargetsByClass

availabilityRecordsProcessed
availabilityDatasetResources
availabilityDatasetMentions
availabilityRepositoryTargets
availabilityToolTargets
availabilityDeferred

deferredCount
skippedCount
unresolvedCount
warningCount
```

Statistics do not replace the underlying report records.

---

## 17. Scope restrictions

The implementation must not:

- modify the Phase A corpus;
- modify raw publication files;
- modify ontology files;
- hardcode current paper IDs or bibliographic values;
- use fuzzy matching;
- use name-based cross-paper author merging;
- treat every DOI as a Paper without applying the target-typing policy;
- treat every availability identifier as a DatasetResource;
- infer `usesDataset` from a citation alone;
- infer `usesTool` from a code/software availability section alone;
- infer citation function from the bibliography;
- copy complete Markdown, Marker JSON, chunks, or polygons;
- emit hashes as ontology identifiers unless declared by the mapping;
- create EvidenceSpan nodes at this stage.

---

## 18. Companion artifacts

- `docs/publication_preprocessing_phaseA.md` — raw sources to authoritative publication corpus.
- `docs/publication_extraction_phaseB.md` — this execution contract.
- `src/extraction/deterministic/publication_extraction_mapping.md` — exhaustive field-to-ontology mapping.
- `src/ontology/ontology_spec.yaml` — machine-readable ontology authority.
- `docs/ontology_inventory.md` — narrative ontology inventory and stable IDs.
- `src/extraction/deterministic/extract_publication.py` — target implementation.
- `tests/test_extract_publication.py` — focused and frozen-snapshot tests.
- `data/interim/papers/publication_nodes_edges.json` — deterministic Phase B output.

*End of Publication Phase B extraction contract.*
