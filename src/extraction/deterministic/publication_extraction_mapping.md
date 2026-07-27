# CIROH Publications → Ontology — Deterministic Extraction Mapping

**Study 2 — Knowledge-graph construction, deterministic layer (Module 1: Scientific Publications)**

**Target implementation:** `src/extraction/deterministic/extract_publication.py`  
**Input:** `data/interim/papers/ciroh_publication_corpus.json` (`schema_version: 1.1.0`, `phase_a_version: 1.0.9`)  
**Output:** `data/interim/papers/publication_nodes_edges.json` (`schema_version: 1.0.0`, `phase_b_version: 1.0.2`)  
**Execution contract:** `docs/publication_extraction_phaseB.md`

---

## 1. Purpose and scope

This document is the field-level implementation mapping between the frozen Publication Phase A corpus and the Study 2 ontology.

For every deterministically processed Phase A field, it defines:

- node or edge produced;
- ontology inventory ID;
- stable identity rule;
- attributes;
- evidence;
- internal lineage;
- deduplication;
- guards;
- deferred or administrative disposition.

Only structured Phase A facts are mapped. Scientific prose interpretation, in-text citation-function extraction, fuzzy consolidation, and final graph assembly are outside this mapping.

---

## 2. Conventions

### 2.1 Source publication

For the rules below, `pub` denotes one `publications[]` record.

Required helpers:

```text
canonical_key(pub) =
  doi:{pub.canonical_identifier.value}  when scheme == doi
  url:{normalized canonical URL}        otherwise

paper_hash    = stable_hash(canonical_key(pub))
paper_node_id = publication:paper:{paper_hash}
paper_version = phase-a:{top-level phase_a_version}
```

### 2.2 Stable hash

```text
stable_hash(value) =
SHA-256(UTF-8(value)).hexdigest().lower()[0:20]
```

Hash inputs use `|` separators.

### 2.3 Common node shape

```text
id
class
inventoryId
attributes
canonicalKey
identityRegime
curationStatus
evidence
internalLineage
```

### 2.4 Common edge shape

```text
id
relation
inventoryId
source
target
attributes
evidence
internalLineage
```

Edge ID:

```text
publication:edge:{relation}:{stable_hash(source_id|relation|target_id)}
```

One semantic source–relation–target triple produces one edge. Multiple supporting occurrences are merged under `attributes.sourceDeclarations`.

### 2.5 Text normalization

`normalize_text_key(value)`:

```text
Unicode NFKC
→ trim
→ collapse whitespace
→ casefold
```

Original source values remain in attributes and evidence.

### 2.6 DOI normalization

Use the Phase A DOI policy:

```text
remove DOI resolver/prefix
trim
lowercase
validate conservative DOI syntax
preserve balanced valid parentheses
```

Phase B must reject rather than repair a DOI that does not already conform to the Phase A contract.

### 2.7 URL normalization

For exact identity:

```text
absolute HTTP(S)
lowercase scheme and host
preserve path/query/fragment unless a target-specific rule removes them
reject Markdown wrappers and nested URLs
```

DOI resolver URLs remain URL identifiers only when they are an explicitly curated URL. They never replace the DOI canonical key.

### 2.8 Evidence builders

#### Curated bibliographic declaration

```text
evidenceText    = source value supporting the node/edge
sourceArtifact  = pub.canonical_artifact_id
sourceLocation  = pub.canonical_artifact_id
extractionMethod = deterministic
version         = phase-a:1.0.9
```

#### Markdown-derived declaration already extracted by Phase A

Public evidence uses the same artifact URL. Internal location:

```jsonc
{
  "phaseAField": "content.explicit_keywords[3]",
  "localPaperId": "17",
  "markdownPath": "data/raw/papers/markdowns/17/markdown/17_md.md",
  "section": "Keywords",
  "lineStart": 22,
  "lineEnd": 22,
  "phaseAVersion": "1.0.9"
}
```

#### Merged exact entity

Choose primary declaration by:

1. `curationStatus == curated` before referenced;
2. lexicographically smallest `sourceArtifact`;
3. smallest `lineStart` (`null` sorts after integers);
4. smallest `lineEnd`;
5. lexicographically smallest `phaseAField`;
6. lexicographically smallest `evidenceText`.

Preserve all declarations in `attributes.sourceDeclarations`.

### 2.9 Exact versus mention identity

Exact globally reusable identities:

```text
Paper by DOI/URL
Identifier by scheme/value
Venue by exact normalized label
Subject by exact normalized value
DatasetResource by exact typed resource identifier
Repository by exact GitHub root or typed DOI
Tool by exact typed DOI
```

Source-scoped identities:

```text
Person author occurrence
DatasetMention availability occurrence
```

---

## 3. Canonicalizers and classifiers

### 3.1 Person alignment key

For a Phase A author:

```text
if literal_name:
  canonicalKey = person-name:{normalize_text_key(literal_name)}
else:
  canonicalKey = person-name:{
    normalize_text_key(
      given_names + name_particles + family_name + suffix
    )
  }
```

This is a weak later-alignment key. It does not control node ID.

Person node ID:

```text
publication:person:{paper_hash}:{position:04d}
```

### 3.2 Venue key

```text
venue_key = normalize_text_key(bibliographic.venue)
venue_id  = publication:venue:{stable_hash(venue_key)}
canonicalKey = venue-name:{venue_key}
```

### 3.3 Subject key

Phase A `explicit_keywords[].value` is already normalized.

```text
subject_key = normalize_text_key(keyword.value)
subject_id  = publication:subject:{stable_hash(subject_key)}
canonicalKey = subject:{subject_key}
```

### 3.4 Identifier key

```text
identifier_key = {scheme}|{normalized_value}
identifier_id  = publication:identifier:{stable_hash(identifier_key)}
canonicalKey   = {scheme}:{normalized_value}
```

Attributes:

```text
scheme
value
normalizedValue
uri
```

### 3.5 GitHub repository root

Accept a GitHub URL only when the first two path segments form `{owner}/{repository}`.

Canonical form:

```text
https://github.com/{owner}/{repository}
```

Rules:

- remove terminal `.git`;
- strip query and fragment;
- preserve one deterministic normalized source form in Repository display attributes;
- compare owner/repository case-insensitively and case-fold the exact identity URL;
- allow subpaths after the repository pair only for root resolution;
- reject profiles, organizations, gists, marketplace, settings, login, search, raw content, badges, user attachments, and hostnames other than `github.com`.

Repository ID:

```text
github_identity_url = canonical_url.casefold()
canonicalKey = url:{github_identity_url}
publication:repository:{stable_hash(github-repo-url|github_identity_url)}
```

The exact URL Identifier also uses `github_identity_url`. Case-only declarations merge into one Repository and one Identifier; their original forms remain in `sourceDeclarations`. The Repository `htmlUrl`, `owner`, and `name` use the lexicographically first normalized source form, independent of input order.

### 3.6 HydroShare resource URL

Accept host `hydroshare.org` or subdomains and path:

```text
/resource/{32 hexadecimal characters}
```

Normalize resource ID to lowercase.

Dataset ID:

```text
publication:dataset:{stable_hash(hydroshare|resource_id)}
canonicalKey = hydroshare:{resource_id}
```

### 3.7 HydroShare DOI

Recognize the exact DOI namespace:

```text
10.4211/hs.
```

A valid DOI in that namespace is a `DatasetResource`.

### 3.8 Occurrence-bounded DOI context

For citation typing, `content.reference_dois[].occurrences[].reference_text` is the maximum evidence boundary. For every occurrence independently:

1. locate the exact normalized DOI, resolver destination, or exact normalized DOI declaration;
2. identify every DOI declaration in that same occurrence;
3. bound the target-local segment at the closest preceding and following distinct DOI declarations and any intervening line/reference boundary;
4. treat repeated renderings of the same target DOI deterministically as one target declaration cluster;
5. return no positive signal when the target cannot be located uniquely or another DOI splits the target cluster.

No fixed character window is the classification unit. The exact Phase A `reference_text` remains unchanged in `evidenceText`; the smaller derived segment is retained only as `typeEvidenceText` for the occurrence audit.

### 3.9 Strong dataset markers

High-precision markers are explicit, structurally associated bibliographic resource labels before the target declaration, such as:

```text
[data set]
[dataset]
(data set)
(dataset)
```

A general paper title containing “dataset” or “data repository” is not a type marker. Exact HydroShare identity is handled only by §3.6–3.7, independently of title language.

### 3.10 Strong repository/software markers

Repository markers:

```text
repository:
[(code|source-code) repository]
((code|source-code) repository)
exact GitHub repository URL
```

Software markers:

```text
[software]
(software)
[computer software]
(computer software)
```

A paper title discussing software, a phrase such as “software version,” a journal name, or “Journal of Open Source Software” is not sufficient. A loose type label in an otherwise structurally scholarly journal citation is not promoted. A marker after the target DOI, beyond a neighboring DOI, or otherwise not uniquely attributable to the target provides no strong signal.

### 3.11 Ambiguous repository DOI namespaces

The following generic repository namespaces are not intrinsically Paper, Dataset, or Software types:

```text
10.5281/zenodo.
10.6084/m9.figshare.
10.5061/dryad.
10.7910/dvn/
```

They require explicit occurrence-local type evidence. The list is a conservative ambiguity guard only: it never assigns DatasetResource, Repository, or Tool. It is a tested centralized configuration constant and may be extended only through a documented contract revision.

### 3.12 Global cited-DOI type decision

Classify each Phase A occurrence first as:

```text
curated_paper
untyped_scholarly_reference
strong_dataset
strong_repository
strong_tool
ambiguous
conflicting
```

Then aggregate the occurrence decisions for each normalized cited DOI and choose exactly one global disposition:

```text
curated Paper
referenced Paper
DatasetResource
Repository
Tool
unresolved conflicting type
deferred ambiguous repository DOI type
```

Priority:

```text
curated DOI index
→ exact resource/provider rule
→ one or more consistent strong occurrence decisions
→ ambiguity namespace guard
→ referenced Paper default
```

Untyped scholarly occurrences do not conflict with a consistent strong declaration. Conflicting strong classes produce one unresolved target disposition. One weak or contaminated occurrence cannot retype the DOI, and one DOI can create at most one global target class. Every source declaration retains `occurrenceDecision`, `typeEvidenceCategory`, `typeEvidenceText`, and the unchanged Phase A evidence and lineage. When no node is emitted, the deferred/unresolved report `value` contains the DOI, global decision, and all public occurrence decisions.

Conflict example:

```text
one strong dataset declaration + one strong software declaration
```

Disposition:

```text
no target node/edge
unresolved: conflicting_cited_doi_type
```

A DOI may never create nodes in multiple classes.

---

## 4. Node rules

### N1 — Curated Paper

| Item | Rule |
|---|---|
| Phase A source | each `publications[i]` |
| Class | `Paper` |
| Inventory ID | `A-P01` |
| ID | `publication:paper:{stable_hash(canonicalKey)}` |
| canonicalKey | DOI key, otherwise canonical URL key |
| identityRegime | `doi` or `canonical_url` |
| curationStatus | `curated` |

Attributes:

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

`abstractSourceType` is the source type from `bibliographic.abstract_source`, or `null`.

`headings` mapping:

```text
level            ← content.headings[].level
text             ← content.headings[].text
normalizedText   ← content.headings[].normalized_text
lineNumber       ← content.headings[].line_number
```

`tableOfContents` mapping:

```text
title            ← document_structure.table_of_contents[].title
pageId           ← document_structure.table_of_contents[].page_id
headingLevel     ← document_structure.table_of_contents[].heading_level
```

Do not copy polygons.

Evidence:

```text
evidenceText = bibliographic.title
```

Lineage includes the local paper ID, source files, match method, override flags, and Phase A version.

---

### N2 — Curated/exact Identifier

| Item | Rule |
|---|---|
| Source | every exact identifier declaration requiring an ontology Identifier |
| Class | `Identifier` |
| Inventory ID | `A-ID01` |
| ID | `publication:identifier:{stable_hash(scheme|normalized_value)}` |
| canonicalKey | `{scheme}:{normalized_value}` |
| identityRegime | `exact_identifier` |
| curationStatus | `curated` if attached to a curated paper; otherwise `referenced` |

Attributes:

```text
scheme
value
normalizedValue
uri
```

When the same Identifier is supported by curated and referenced declarations, keep one node with `curationStatus = curated` and merge declarations.

---

### N3 — Paper-scoped Person author mention

| Item | Rule |
|---|---|
| Source | `bibliographic.authors[i]` |
| Class | `Person` |
| Inventory ID | `A-AG01` |
| ID | `publication:person:{paper_hash}:{position:04d}` |
| canonicalKey | weak normalized person-name key |
| identityRegime | `paper_author_mention` |
| curationStatus | `curated` |

Attributes:

```text
displayName
givenNames
familyName
nameParticles
suffix
literalName
rawBibtex
authorPosition
sourcePaperCanonicalKey
```

Do not merge nodes with equal canonical keys.

Evidence:

```text
evidenceText = display_name
```

Fallback to `raw_bibtex` only when display name is absent, which should fail the current Phase A contract.

---

### N4 — Exact-normalized Venue

| Item | Rule |
|---|---|
| Source | `bibliographic.venue` |
| Class | `Venue` |
| Inventory ID | `A-P02` |
| ID | `publication:venue:{stable_hash(normalized_venue)}` |
| canonicalKey | `venue-name:{normalized_venue}` |
| identityRegime | `normalized_exact_name` |
| curationStatus | `curated` |

Attributes:

```text
name
normalizedName
sourceDeclarations
```

Equal exact-normalized labels share one node. Alternative abbreviations remain separate.

Evidence is selected from the supporting papers.

---

### N5 — Exact-normalized Subject

| Item | Rule |
|---|---|
| Source | `content.explicit_keywords[i]` |
| Class | `Subject` |
| Inventory ID | `A-P04` |
| ID | `publication:subject:{stable_hash(normalized_keyword)}` |
| canonicalKey | `subject:{normalized_keyword}` |
| identityRegime | `normalized_exact_label` |
| curationStatus | `curated` |

Attributes:

```text
label
normalizedLabel
sourceDeclarations
```

Evidence text is `raw_value`; normalized identity uses `value`.

---

### N6 — Referenced Paper DOI stub

| Item | Rule |
|---|---|
| Source | globally typed external cited DOI |
| Class | `Paper` |
| Inventory ID | `A-P01` |
| ID | `publication:paper:{stable_hash(doi|normalized_doi)}` |
| canonicalKey | `doi:{normalized_doi}` |
| identityRegime | `doi` |
| curationStatus | `referenced` |

Attributes:

```text
title = null
recordType = null
year = null
doi
canonicalArtifactId = https://doi.org/{doi}
referenceStub = true
sourceDeclarations
```

Do not copy a citing paper’s `reference_text` into intrinsic title or bibliographic attributes.

Primary evidence comes from the deterministic first source declaration.

---

### N7 — Referenced DatasetResource

Created for:

- exact HydroShare resource URL;
- exact HydroShare DOI;
- strongly typed cited dataset DOI;
- an exact target already typed as DatasetResource elsewhere in the same run.

| Item | Rule |
|---|---|
| Class | `DatasetResource` |
| Inventory ID | `A-D01` |
| ID | exact resource-specific ID or DOI-key hash |
| canonicalKey | `hydroshare:{resource_id}`, `doi:{doi}`, or exact typed URL |
| identityRegime | exact resource identifier |
| curationStatus | `referenced` |

Attributes:

```text
title = null
resourceId when known
doi when known
url when known
referenceStub = true
sourceDeclarations
```

Exact Identifier nodes are emitted with N2.

---

### N8 — Paper-scoped DatasetMention

Created for a generic identifier in a pure data-availability section when no exact target class is known.

| Item | Rule |
|---|---|
| Class | `DatasetMention` |
| Inventory ID | `A-P25` |
| ID | `publication:dataset-mention:{paper_hash}:{stable_hash(scheme|value)}` |
| canonicalKey | `{scheme}:{normalized_value}` |
| identityRegime | `paper_availability_mention` |
| curationStatus | `curated` |

Attributes:

```text
identifierScheme
identifierValue
identifierUri
sectionCategory
sectionTitle
sourcePaperCanonicalKey
```

The canonical key is an alignment candidate; it does not cause cross-paper mention merging.

No separate Identifier node is required because the current ontology does not declare `DatasetMention —hasIdentifier→ Identifier`.

---

### N9 — Referenced Repository

Created for:

- exact GitHub repository URL in availability evidence;
- strongly typed repository DOI in citation evidence.

| Item | Rule |
|---|---|
| Class | `Repository` |
| Inventory ID | `A-C01` |
| ID | GitHub: `publication:repository:{stable_hash(github-repo-url\|github_identity_url)}`; DOI: DOI-key hash |
| canonicalKey | case-folded exact GitHub root URL key or DOI key |
| identityRegime | `github_repository_url` or `repository_doi` |
| curationStatus | `referenced` |

Attributes:

```text
htmlUrl when known
owner when known
name when known
doi when known
referenceStub = true
sourceDeclarations
```

Exact Identifier nodes are emitted with N2 and attached with `C-C06`.

No Paper→Repository edge is emitted by this mapping.

---

### N10 — Referenced Tool

Created only from a strongly explicit software DOI whose evidence does not support Repository typing.

| Item | Rule |
|---|---|
| Class | `Tool` |
| Inventory ID | `A-DOM02` |
| ID | `publication:tool:{stable_hash(doi|normalized_doi)}` |
| canonicalKey | `doi:{normalized_doi}` |
| identityRegime | `software_doi` |
| curationStatus | `referenced` |

Attributes:

```text
name = null
doi
canonicalArtifactId = https://doi.org/{doi}
referenceStub = true
sourceDeclarations
```

The DOI remains an intrinsic exact identity attribute. Do not emit an undeclared Tool `hasIdentifier` edge.

No Paper→Tool edge is emitted from bibliographic presence alone.

---

## 5. Edge rules

### E1 — Curated Paper hasIdentifier

| Item | Rule |
|---|---|
| Source | `pub.identifiers[i]` |
| Relation | `hasIdentifier` |
| Inventory ID | `C-P04` |
| Source node | N1 Paper |
| Target node | N2 Identifier |

Attributes:

```text
identifierOrder = i + 1
isCanonical = identifier.uri == pub.canonical_artifact_id
```

Evidence text is the identifier value.

---

### E2 — Paper hasAuthor

| Item | Rule |
|---|---|
| Source | `bibliographic.authors[i]` |
| Relation | `hasAuthor` |
| Inventory ID | `C-P01` |
| Source | N1 Paper |
| Target | N3 Person |

Attributes:

```text
authorPosition
```

Exactly one edge per author occurrence.

---

### E3 — Paper publishedIn Venue

| Item | Rule |
|---|---|
| Source | `bibliographic.venue` |
| Relation | `publishedIn` |
| Inventory ID | `C-P02` |
| Source | N1 Paper |
| Target | N4 Venue |

One edge per curated Paper.

---

### E4 — Paper hasSubject Subject

| Item | Rule |
|---|---|
| Source | `content.explicit_keywords[i]` |
| Relation | `hasSubject` |
| Inventory ID | `C-P03` |
| Source | N1 Paper |
| Target | N5 Subject |

Attributes:

```text
keywordOrder
sourceType
```

Evidence text is `raw_value`. Internal lineage uses keyword source lines.

---

### E5 — Paper cites Paper

| Item | Rule |
|---|---|
| Source | `content.reference_dois[i]` typed as Paper |
| Relation | `cites` |
| Inventory ID | `C-P21` |
| Source | N1 Paper |
| Target | curated N1 Paper or referenced N6 Paper |

Attributes:

```text
doi
sourceDeclarations
targetIsCurated
```

Primary evidence text is the selected occurrence’s `reference_text`.

No self-loop. Duplicate source–target citations merge.

Typed CiTO subproperties are not emitted.

---

### E6 — Paper corrects Paper

| Item | Rule |
|---|---|
| Source | `bibliographic_relations.correction_of` |
| Relation | `corrects` |
| Inventory ID | `C-P22` |
| Source | corrigendum N1 Paper |
| Target | exact curated Paper by canonical identifier |

Attributes:

```text
relationSource = curation_override
```

The target must resolve. Failure is fatal.

Do not emit an undeclared inverse edge.

---

### E7 — DatasetResource hasIdentifier

| Item | Rule |
|---|---|
| Source | exact DatasetResource DOI/URL |
| Relation | `hasIdentifier` |
| Inventory ID | `C-D04` |
| Source | N7 DatasetResource |
| Target | N2 Identifier |

One edge per exact identifier.

---

### E8 — Paper referencesDataset DatasetResource

| Item | Rule |
|---|---|
| Source | reference DOI deterministically typed as DatasetResource |
| Relation | `referencesDataset` |
| Inventory ID | `C-P29` (Paper-module realization of global `D-05`) |
| Source | N1 Paper |
| Target | N7 DatasetResource |

Attributes:

```text
doi
sourceDeclarations
typingEvidence
```

A reference-list dataset citation does not imply `usesDataset`.

---

### E9 — Paper usesDataset DatasetResource

| Item | Rule |
|---|---|
| Source | exact HydroShare/typed dataset availability identifier |
| Relation | `usesDataset` |
| Inventory ID | `C-P20` |
| Source | N1 Paper |
| Target | N7 DatasetResource |

Attributes:

```text
sectionCategory
sectionTitle
identifierScheme
identifierValue
sourceDeclarations
```

Duplicate source–target declarations merge.

---

### E10 — Paper usesDataset DatasetMention

| Item | Rule |
|---|---|
| Source | generic identifier in `data_availability` |
| Relation | `usesDataset` |
| Inventory ID | `C-P20` |
| Source | N1 Paper |
| Target | N8 DatasetMention |

Attributes:

```text
sectionCategory
sectionTitle
identifierScheme
identifierValue
```

One edge per source-scoped mention.

---

### E11 — Repository hasIdentifier

| Item | Rule |
|---|---|
| Source | exact GitHub URL or typed repository DOI |
| Relation | `hasIdentifier` |
| Inventory ID | `C-C06` |
| Source | N9 Repository |
| Target | N2 Identifier |

No Paper→Repository edge is emitted.

---

## 6. Citation occurrence mapping

For each Phase A `reference_dois[i]`:

```text
doi
uri
reference_text
source_location
occurrences[]
```

Disposition:

1. validate DOI and URI;
2. classify every occurrence independently within its Phase A evidence boundary;
3. aggregate the occurrence decisions into one global target disposition;
4. detect self-reference;
5. create/reuse at most one target class;
6. emit the relation allowed for the target class;
7. retain every occurrence and its decision.

`sourceDeclarations` entry:

```jsonc
{
  "sourceArtifact": "https://doi.org/source-paper",
  "evidenceText": "Complete Phase A reference text",
  "section": "References",
  "lineStart": 412,
  "lineEnd": 412,
  "phaseAField": "content.reference_dois[12].occurrences[0]",
  "occurrenceDecision": "strong_dataset",
  "typeEvidenceCategory": "structural_dataset_label",
  "typeEvidenceText": "Target-local segment bounded by neighboring DOI declarations"
}
```

The top-level `reference_text`/`source_location` duplicates the primary Phase A occurrence and is used only for validation/compatibility. Occurrences are authoritative for merged declaration accounting.

If `occurrences` is unexpectedly empty, fail.

---

## 7. Availability mapping decision table

This table is authoritative and is applied before any citation-registry default. Pure data availability first reuses an exact DatasetResource already established by strong deterministic evidence. A Paper, Tool, Repository, ambiguous, or untyped citation decision cannot suppress the fallback `data_availability` DatasetMention rule. Neither reuse nor a DatasetMention globally retypes another DOI or URL target.

| Section category | Identifier target | Node/edge disposition |
|---|---|---|
| any | exact HydroShare resource URL/DOI | N7 + N2 + E7 + E9 |
| any | exact GitHub repository URL | N9 + N2 + E11; Paper relation deferred |
| `data_availability` | exact strongly typed DatasetResource established in this run | reuse N7 + merge declaration + E9 |
| `data_availability` | generic DOI/URL with no exact strongly typed DatasetResource | N8 + E10 |
| `code_availability` | strongly typed Repository/Tool DOI | N9/N10; Paper relation deferred |
| `software_availability` | strongly typed Repository/Tool DOI | N9/N10; Paper relation deferred |
| `data_and_code_availability` | exact HydroShare or exact GitHub | exact rule above |
| `data_and_code_availability` | generic DOI/URL | deferred ambiguous mixed target |
| `code_and_data_availability` | exact HydroShare or exact GitHub | exact rule above |
| `code_and_data_availability` | generic DOI/URL | deferred ambiguous mixed target |
| any | malformed target | fatal, because Phase A should already reject it |
| any | duplicate within paper | fatal, because Phase A should already reject it |

Availability source declaration:

```jsonc
{
  "sourceArtifact": "https://doi.org/source-paper",
  "evidenceText": "...availability statement...",
  "sectionCategory": "data_availability",
  "sectionTitle": "Data Availability",
  "lineStart": 215,
  "lineEnd": 216,
  "identifierScheme": "doi",
  "identifierValue": "10.xxxx/example",
  "phaseAField": "content.availability_identifiers[2]"
}
```

Each Phase A `deferred_reference_doi_candidate` warning is propagated exactly once as audit-only metadata. Because the candidate is absent from accepted `reference_dois` and `availability_identifiers`, it creates no node, Identifier, semantic edge, or accepted-source count.

---

## 8. Phase A field-disposition matrix

### 8.1 Top level

| Phase A field | Disposition |
|---|---|
| `schema_version` | output `source_schema_version`; validation |
| `phase_a_version` | output `source_phase_a_version`; evidence version; lineage |
| `source.artifact_type` | output `source_type`; validation |
| other `source.*` | stats/administrative-only |
| `publications[]` | N1 and all child mappings |
| `known_exclusions[]` | one `skipped` administrative record per exclusion |
| `warnings[]` | propagated to output warnings |
| `summary` | validation and source stats only |

### 8.2 Publication identity and metadata

| Phase A field | Disposition |
|---|---|
| `local_paper_id` | internal lineage only |
| `canonical_artifact_id` | Paper identity; public evidence |
| `canonical_identifier` | Paper identity; validation |
| `identifiers[]` | N2 + E1 |
| `record_type` | N1 attribute |
| `curation_status` | N1 `curationStatus` |
| `bibliographic.title` | N1 attribute/evidence |
| `bibliographic.year` | N1 attribute |
| `bibliographic.volume` | N1 attribute |
| `bibliographic.issue` | N1 attribute |
| `bibliographic.pages` | N1 attribute |
| `bibliographic.publisher` | N1 attribute |
| `bibliographic.language` | N1 attribute |
| `bibliographic.abstract` | N1 attribute |
| `bibliographic.abstract_source` | N1 `abstractSourceType`; lineage |
| `bibliographic.authors[]` | N3 + E2 |
| `bibliographic.venue` | N4 + E3 |

### 8.3 Deterministic content

| Phase A field | Disposition |
|---|---|
| `content.headings[]` | simplified N1 `headings` attribute |
| `content.explicit_keywords[]` | N5 + E4 |
| `content.reference_dois[]` | N6/N7/N9/N10 + E5/E8 or report disposition |
| `content.availability_identifiers[]` | N7/N8/N9/N10 + E9/E10/E11 or report disposition |

### 8.4 Structure and files

| Phase A field | Disposition |
|---|---|
| `document_structure.page_count` | N1 attribute |
| `document_structure.table_of_contents[].title` | simplified N1 attribute |
| `document_structure.table_of_contents[].page_id` | simplified N1 attribute |
| `document_structure.table_of_contents[].heading_level` | simplified N1 attribute |
| `document_structure.table_of_contents[].polygon` | skipped/administrative-only; not copied |
| `source_files.*` | N1 internal lineage only |

### 8.5 Relations and reconciliation

| Phase A field | Disposition |
|---|---|
| `bibliographic_relations.correction_of` | E6 |
| `reconciliation.excel_matched` | validation/lineage |
| `reconciliation.zotero_key_original` | lineage |
| `reconciliation.bibtex_key` | lineage |
| `reconciliation.bibtex_match_method` | lineage/stats |
| `reconciliation.bibtex_entry_type` | validation/lineage |
| `reconciliation.override_applied` | lineage/stats |
| `reconciliation.override_action` | lineage/stats |
| `reconciliation.conflicts[]` | propagated warnings/admin stats |
| `reconciliation.warnings[]` | propagated warnings |

No field is silently ignored.

---

## 9. Report categories

### 9.1 Deferred

Examples:

```text
paper_repository_relation_not_declared
paper_tool_relation_requires_semantic_context
availability_mixed_target_type
typed_citation_function_requires_body_context
author_consolidation_deferred
venue_consolidation_deferred
```

Do not create one redundant author-consolidation report per author. Cross-cutting future work may be represented once in output metadata/stats; occurrence-specific ambiguity must be a report record.

### 9.2 Skipped

Examples:

```text
self_reference_doi_matches_source
known_phase_a_exclusion
table_of_contents_polygon_not_mapped
duplicate_supporting_occurrence_after_exact_merge
```

### 9.3 Unresolved

Examples:

```text
ambiguous_cited_doi_type
conflicting_cited_doi_type
github_url_not_repository_root
hydroshare_url_missing_resource_id
correction_target_not_found
```

A missing correction target is also fatal.

### 9.4 Warnings

Propagate:

```text
Phase A top-level warnings
publication reconciliation warnings
Excel/BibTeX conflicts
control-character audit warnings
ambiguous/rejected keyword warnings
```

Warnings remain audit records and do not create graph facts.

---

## 10. Deferred to the LLM/hybrid publication layer

The deterministic mapping does not create:

- Paper discourse-unit nodes A-P05–A-P24/A-P26;
- `reports`, `resolves`, `produces`, `testedBy`, `supports`, `hasLimitation`;
- models, tools, methods, algorithms, variables, parameters, metrics, places, or hydrologic features from prose;
- `usesModel`, `mentionsModel`, `usesTool`, `mentionsVariable`, `studiesFeature`, `studiesPlace`;
- in-text citation spans;
- CiTO citation-function subproperties;
- relation between a cited software DOI and the citing Paper;
- author, venue, or subject fuzzy consolidation;
- abstract inference for missing Phase A abstracts;
- figure/table interpretation.

The later layer reads canonical Markdown through Phase A lineage and enriches the same curated Paper IDs.

---

## 11. Output examples

### 11.1 Curated Paper

```jsonc
{
  "id": "publication:paper:<hash>",
  "class": "Paper",
  "inventoryId": "A-P01",
  "attributes": {
    "title": "Example paper",
    "recordType": "journal_article",
    "year": 2025,
    "volume": "10",
    "issue": "2",
    "pages": "1-20",
    "publisher": null,
    "language": "en",
    "abstract": "Explicit abstract text.",
    "abstractSourceType": "markdown_explicit",
    "canonicalArtifactId": "https://doi.org/10.1234/example",
    "pageCount": 20,
    "headingCount": 12,
    "headings": [],
    "tableOfContentsEntryCount": 12,
    "tableOfContents": []
  },
  "canonicalKey": "doi:10.1234/example",
  "identityRegime": "doi",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "Example paper",
    "sourceLocation": "https://doi.org/10.1234/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.1234/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "publications[canonical_artifact_id=https://doi.org/10.1234/example]",
    "localPaperId": "17",
    "markdownPath": "data/raw/papers/markdowns/17/markdown/17_md.md",
    "phaseAVersion": "1.0.9"
  }
}
```

### 11.2 Author mention

```jsonc
{
  "id": "publication:person:<paper-hash>:0001",
  "class": "Person",
  "inventoryId": "A-AG01",
  "attributes": {
    "displayName": "Jane Doe",
    "givenNames": ["Jane"],
    "familyName": "Doe",
    "nameParticles": [],
    "suffix": null,
    "literalName": null,
    "rawBibtex": "Doe, Jane",
    "authorPosition": 1,
    "sourcePaperCanonicalKey": "doi:10.1234/example"
  },
  "canonicalKey": "person-name:jane doe",
  "identityRegime": "paper_author_mention",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "Jane Doe",
    "sourceLocation": "https://doi.org/10.1234/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.1234/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "bibliographic.authors[position=1]",
    "localPaperId": "17",
    "authorPosition": 1,
    "phaseAVersion": "1.0.9"
  }
}
```

### 11.3 Shared cited Paper target and citation edge

```jsonc
{
  "id": "publication:edge:cites:<hash>",
  "relation": "cites",
  "inventoryId": "C-P21",
  "source": "publication:paper:<source-hash>",
  "target": "publication:paper:<target-doi-hash>",
  "attributes": {
    "doi": "10.5678/target",
    "targetIsCurated": false,
    "sourceDeclarations": [
      {
        "sourceArtifact": "https://doi.org/10.1234/example",
        "evidenceText": "Target reference text...",
        "section": "References",
        "lineStart": 412,
        "lineEnd": 412,
        "phaseAField": "content.reference_dois[12].occurrences[0]"
      }
    ]
  },
  "evidence": {
    "evidenceText": "Target reference text...",
    "sourceLocation": "https://doi.org/10.1234/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.1234/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "content.reference_dois[12]",
    "localPaperId": "17",
    "section": "References",
    "lineStart": 412,
    "lineEnd": 412,
    "phaseAVersion": "1.0.9"
  }
}
```

### 11.4 Generic availability DatasetMention

```jsonc
{
  "id": "publication:dataset-mention:<paper-hash>:<identifier-hash>",
  "class": "DatasetMention",
  "inventoryId": "A-P25",
  "attributes": {
    "identifierScheme": "url",
    "identifierValue": "https://example.org/data",
    "identifierUri": "https://example.org/data",
    "sectionCategory": "data_availability",
    "sectionTitle": "Data Availability",
    "sourcePaperCanonicalKey": "doi:10.1234/example"
  },
  "canonicalKey": "url:https://example.org/data",
  "identityRegime": "paper_availability_mention",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "Data are available at https://example.org/data.",
    "sourceLocation": "https://doi.org/10.1234/example",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://doi.org/10.1234/example",
    "version": "phase-a:1.0.9"
  },
  "internalLineage": {
    "phaseAField": "content.availability_identifiers[0]",
    "localPaperId": "17",
    "section": "Data Availability",
    "lineStart": 215,
    "lineEnd": 215,
    "phaseAVersion": "1.0.9"
  }
}
```

---

## 12. Validation requirements

### 12.1 Exact frozen anchors

Validate the frozen counts stated in the Phase B execution contract.

### 12.2 Node and edge rules

- exactly 228 curated Paper nodes;
- exactly 1,602 Person mention nodes and `hasAuthor` edges;
- author positions contiguous within each paper;
- exactly 84 exact-normalized Venue nodes and 228 `publishedIn` edges;
- exactly 317 Subject nodes and 373 `hasSubject` edges;
- exactly 455 curated Paper `hasIdentifier` edges;
- exactly one `corrects` edge;
- every curated Paper contains the correct abstract and structural attributes;
- no full Markdown or polygon data is copied.

### 12.3 Citation rules

- 8,856 source DOI records and 8,963 occurrence declarations accounted for;
- 23 self-reference artifacts skipped and no self-loop emitted;
- one target identity/class per DOI;
- cited DOI matching a curated DOI reuses the curated Paper;
- duplicate citation edges do not occur;
- citation occurrence evidence remains on edges;
- `cites` targets only Paper;
- dataset citations use `referencesDataset` with inventory ID `C-P29`;
- Repository/Tool citation relation candidates are deferred.

### 12.4 Availability rules

- 299 source records accounted for;
- pure-data identifiers reuse an exact strongly typed DatasetResource before falling back to DatasetMention + `usesDataset`;
- exact HydroShare resources produce DatasetResource + `usesDataset`;
- exact GitHub roots produce Repository + Identifier and a deferred Paper relation;
- mixed generic identifiers are deferred;
- no generic availability URL is promoted to DatasetResource without exact typing.

### 12.5 Provenance and determinism

- every node and edge has complete evidence;
- local paths appear only in lineage;
- node/edge/report arrays are sorted;
- IDs are deterministic;
- repeated builds are byte-identical;
- the previous valid output is not overwritten on validation failure.

---

## 13. Implementation boundary

Use reusable source-general helpers, including:

```text
stable_hash
normalize_text_key
normalize_doi
normalize_url
normalize_github_repository_url
extract_hydroshare_resource_id
make_paper_id
make_person_mention_id
make_venue_id
make_subject_id
make_identifier_id
make_dataset_resource_id
make_dataset_mention_id
make_repository_id
make_tool_id
make_edge_id
build_evidence
build_internal_lineage
select_primary_declaration
merge_source_declarations
extract_doi_local_context
classify_cited_doi_target
build_global_citation_target_registry
emit_node
emit_edge
record_deferred
record_skipped
record_unresolved
propagate_warning
validate_input
validate_inventory_id
validate_domain_range
validate_field_coverage
validate_output
serialize_deterministically
```

Production logic must not branch on current local paper IDs, titles, author names, venue names, keywords, or individual DOI values. Provider namespaces and exact host/path patterns are general configuration rules and must be tested.

*End of deterministic Publication extraction mapping.*
