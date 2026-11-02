# Publication Source-Unit Contract — Publication Pilot 1

> **Status:** final and binding for Publication Pilot 1 implementation
> **Contract version:** 0.1.2
> **Artifact family:** scientific publications
> **Source scope:** curated publication corpus
> **Stage scope:** source-preserving preparation for the ontology-guided LLM semantic overlay
> **Frozen ontology:** CIROH ontology 0.1.4
> **Validated OWL SHA-256:** `7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635`
> **Binding target inventory:** `docs/publication_llm_extraction_target_inventory.md`
> **Date drafted:** 2026-07-30
> **Date frozen:** 2026-07-30

## 1. Purpose

This contract defines the canonical, reproducible source units supplied to the
Publication Pilot 1 extraction pipeline. It establishes:

- which publication representation is authoritative;
- how that representation is normalized without semantic rewriting;
- how documents are divided into sections, blocks, and bounded source units;
- how identifiers, offsets, hashes, content types, and routing metadata are recorded;
- which source content is eligible, context-only, excluded, or requires review;
- how adjacent context and multi-unit evidence are handled; and
- which automatic checks must pass before a source unit can be used in an LLM request.

The contract operationalizes the frozen rule:

> **No supported evidence span means no accepted semantic assertion.**

The contract does not define the candidate-output JSON Schema, annotation guide,
adjudication procedure, prompt text, model configuration, or evaluation matching rules.
Those are separate Pilot 1 artifacts that must consume this contract without silently
changing it.

## 2. Authority and reviewed inputs

Conflicts are resolved in this order:

1. frozen ontology 0.1.4 specification and generated OWL
2. frozen deterministic Phase B outputs and tests
3. final Publication Pilot 1 human-readable target inventory
4. publication ontology observations register
5. LLM extraction decision record
6. this machine-readable profile
7. source-unit contract

Here, `this machine-readable profile` means
`src/extraction/llm/publications/publication_target_inventory.yaml`, and
`source-unit contract` means this document.

Reviewed inputs:

| Artifact | Reviewed SHA-256 | Role |
| --- | --- | --- |
| `src/ontology/ontology_spec.yaml` | `363cb4f92a2fc82f993baf808da56bc7d38bbb355669dd01ca03686c3551982d` | Formal class, relation, domain, range, and status authority |
| `docs/publication_llm_extraction_target_inventory.md` | `fcf5619006def7839f910881099f1534341b3b36fc64ad23e920311b9d07cba9` | Binding Publication Pilot 1 scope |
| `docs/publication_ontology_observations_register.md` | `d06dbdf64fa7bd2ac81c7c1e97d16eebb8ded3d432396414c03a3e0ebca79d5e` | Contract and validator decisions |
| `docs/publication_preprocessing_phaseA.md` | `636cf5babc2a42294fc1986b911e75f414f4564dd760d8079179b4a7aeb77722` | Canonical publication preprocessing boundary |
| `data/interim/papers/ciroh_publication_corpus.json` | `6bce89579cb250d4ba94525bc31c327cc1ae7bdb48b71091cb648fd0502f1e25` | Frozen Phase A publication corpus |
| Publication Pilot 1 design-sample ZIP | `9bfd5f0d5a26dd19276b2c11cb26aebab3157f48a03b157f63d5a37ca78b5509` | Twelve Marker-derived publication artifacts used for source-unit design |

The reviewed Phase A corpus has:

```text
schema_version: 1.1.0
phase_a_version: 1.0.9
publication_count: 228
```

## 3. Design principles

### 3.1 Source preserving

A source unit is a bounded view of canonical publication content. It is not an
LLM-generated summary, paraphrase, or reconstruction.

### 3.2 Canonical Markdown is authoritative

The benchmark representation is the Markdown file identified by:

```text
publication.source_files.markdown_path
```

in the frozen Phase A corpus. Marker chunk JSON and hierarchical JSON may support
conversion diagnosis or optional provenance enrichment, but they do not replace the
canonical Markdown and do not define the evidence offsets used for Pilot 1 scoring.

### 3.3 Exact evidence remains recoverable

Every unit must retain enough information to reproduce the exact source substring,
including document, section, and unit offsets and content hashes.

### 3.4 Section aware and paragraph preserving

Units never cross section-segment boundaries. Ordinary prose paragraphs are not split
during standard unitization.

### 3.5 No overlapping canonical units

The canonical source-unit partition has zero overlap. Adjacent context is represented by
references to other units rather than by copying source text into multiple units.

### 3.6 Routing does not create evidence

Section labels, routing categories, deterministic endpoints, and previously accepted
local candidates help the extractor interpret the source. They do not constitute
evidence unless the assertion also cites a valid literal span from a canonical source
unit.

### 3.7 Source-unit size is distinct from request-context size

Canonical source units are stable evidence and evaluation objects. Their size parameters
do not define the total amount of source context that an LLM may receive in one request.

A request may contain:

- one primary source unit;
- additional complete source units from the same section;
- bounded neighboring units from adjacent sections when the task requires them; or
- a selective document-level context pass when local units cannot support the target.

Every included unit retains its own identifier, offsets, hashes, and evidence boundaries.
Large model context windows are therefore used through a flexible request envelope rather
than by making the canonical evidence units arbitrarily large.

## 4. Empirical basis for the bounded-unit policy

The working design sample contains:

```text
10, 15, 16, 18, 34, 37, 46, 54, 79, 276, 87, 87-corrigendum
```

Observed Markdown characteristics:

| Measure | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| Characters per artifact | 6,975 | 84,375 | 166,544 |
| Lines per artifact | 69 | 393 | 617 |
| Markdown headings per artifact | 10 | 27 | 42 |
| Marker blocks per artifact | 43 | 200.5 | 335 |

Using the heading and blank-line boundaries defined in this contract, the sample contains
330 section segments. Section-length percentiles are approximately:

```text
P90: 7,645 characters
P95: 9,453 characters
maximum: 54,515 characters
```

The 95th percentile of ordinary Markdown block length is approximately 1,813 characters.
The longest observed atomic blocks are predominantly reference lists; the longest
non-reference structured block observed in the sample is a table of approximately
6,500 characters.

These observations support a preferred unit maximum of 10,000 characters. This keeps
approximately 95% of observed section segments intact while substantially reducing the
chance that related paragraphs are assigned to different canonical units. A 20,000-character
atomic-block hard maximum permits unusually long but still structurally coherent tables,
lists, or paragraphs to remain intact when possible. Sections substantially larger than
these values are still partitioned at Markdown block boundaries.

These thresholds are source-unit engineering parameters, not model context-window or
token limits. Model-specific token budgets are applied later to the request envelope.
A request may include several complete source units or a complete section when the
model-specific budget allows.

## 5. Canonical source text

### 5.1 Source path

For each publication, load the repository-relative Markdown path stored in the frozen
Phase A record, for example:

```text
data/raw/papers/markdowns/109/markdown/109_md.md
```

The source-unit generator must not infer the path from the paper ID when the Phase A
record supplies an explicit path.

### 5.2 Canonical text normalization

Apply exactly the Phase A text-normalization policy:

1. decode as UTF-8;
2. remove one leading UTF-8 BOM when present;
3. normalize CRLF and CR line endings to LF;
4. replace every forbidden C0 control character with exactly one ordinary space,
   permitting only tab (`U+0009`) and line feed (`U+000A`);
5. make no other textual change.

Specifically, do **not**:

- normalize Unicode composition;
- collapse whitespace;
- repair hyphenation;
- repair OCR spelling;
- render Markdown to plain text;
- remove HTML spans;
- decode or rewrite links;
- reorder table cells;
- remove page anchors;
- infer missing characters; or
- rewrite equations.

Offsets and literal evidence checks use this canonical normalized string.

### 5.3 Required document hashes

Record:

```text
rawFileSha256
    SHA-256 of the original source-file bytes.

canonicalTextSha256
    SHA-256 of the UTF-8 bytes of the canonical normalized string.
```

Both hashes are lowercase hexadecimal.

## 6. Offset convention

All offsets are:

```text
zero-based
half-open [start, end)
measured in Unicode code points
measured against the canonical normalized Python-style string
```

Therefore:

```text
text[startOffset:endOffset] == evidenceText
```

must hold exactly.

Offsets are not byte offsets and are not measured against rendered Markdown, PDF text,
Marker HTML, or a Unicode-normalized copy.

Line numbers are one-based and inclusive for human inspection. They are supplemental;
character offsets remain authoritative.

## 7. Section-segment model

### 7.1 Heading recognition

Recognize ATX Markdown headings outside fenced code blocks using the equivalent pattern:

```regex
^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$
```

A heading starts at the first character of its Markdown line.

### 7.2 Section boundaries

A **section segment** starts at a recognized heading and ends immediately before the next
recognized heading of any level. This produces a non-overlapping sequential partition;
parent sections do not duplicate the text of child sections.

Text before the first heading is assigned to a synthetic front-matter segment:

```text
sectionOrdinal: 0
sectionID: pub:<paperID>:sec:0000
sectionLevel: 0
sectionTitleRaw: null
sectionTitleNormalized: front matter
```

All later section ordinals are one-based in document order.

### 7.3 Section identifiers

Use:

```text
pub:<paperID>:sec:<sectionOrdinal padded to four digits>
```

Examples:

```text
pub:10:sec:0000
pub:10:sec:0001
pub:87-corrigendum:sec:0004
```

The section ID is source-snapshot local. It must not be interpreted as a permanent global
identifier across different canonical-text hashes.

### 7.4 Section title fields

Record:

```text
sectionTitleRaw
    Exact heading payload after the Markdown # markers, without rewriting.

sectionTitleNormalized
    Routing-only form produced by stripping HTML tags, Markdown emphasis and link
    markup, collapsing internal whitespace, trimming, and Unicode case-folding.
```

`sectionTitleNormalized` is not evidence and must never replace `sectionTitleRaw`.

### 7.5 Structural path

Maintain a heading-level stack and record:

```text
sectionPath
```

as an ordered list of section IDs from the current interpreted top-level ancestor to the
current section. Marker heading levels may be noisy; preserve them rather than silently
correcting document structure. The path is routing metadata, not an ontological assertion.

### 7.6 Section roles

Assign one routing-only role:

```text
front_matter
abstract
highlights
introduction
background
related_work
study_area
data
methods
results
discussion
limitations
conclusion
future_work
appendix
acknowledgments
author_contributions
data_availability
references
other
```

The rule that assigned the role must be recorded as `sectionRoleRule`.

Section roles guide eligible target categories but do not authorize a target outside the
machine-readable Publication Pilot 1 inventory.

## 8. Reference-section exclusion

Ordinary semantic extraction must not process reference-list content as publication prose.

### 8.1 Reference start

A reference scope begins when `sectionTitleNormalized` matches one of:

```regex
^references?$
^bibliography$
^literature cited$
^works cited$
^reference list$
```

### 8.2 Reference end

The scope ends at:

1. the next heading whose Markdown level is equal to or higher than the reference heading
   in the structural hierarchy; or
2. a semantic reset heading matching `appendix`, `supplementary material`, or
   `supporting information`, regardless of noisy Markdown level.

This reset rule is required because the Marker-derived sample contains documents in which
an appendix follows the reference list but is assigned a deeper heading level.

### 8.3 Reference units

Reference content remains materialized for auditability but is marked:

```text
eligibility: excluded
exclusionReasons:
  - reference_section
```

It is not sent through ordinary semantic entity or relation extraction. DOI-backed
citation context remains available through the frozen deterministic Phase B backbone and
any later dedicated citation-grounding protocol.

## 9. Markdown block model

Within each section segment, identify exact, contiguous Markdown blocks. Preserve source
spans and intervening whitespace.

Supported block families:

```text
heading
prose
list
table
caption
equation
code
blockquote
html
metadata
mixed
```

The block parser must recognize at least:

- fenced code blocks;
- contiguous Markdown pipe tables;
- contiguous list items and their continuation lines;
- blockquotes;
- display equations delimited by `$$...$$`, `\[...\]`, or an equivalent Marker block;
- HTML blocks;
- ordinary paragraphs separated by blank lines.

Marker chunk block IDs may be attached later when an exact deterministic mapping exists.
They are not required to define the canonical source span.

## 10. Unitization algorithm

### 10.1 Frozen parameters

```text
preferredUnitMaxCharacters: 10000
atomicBlockHardMaxCharacters: 20000
overlapCharacters: 0
crossSectionUnitsAllowed: false
ordinaryParagraphSplittingAllowed: false
```

### 10.2 Assembly rule

For each section segment:

1. begin at the section start;
2. append complete Markdown blocks in source order;
3. continue while adding the next block keeps the unit at or below
   `preferredUnitMaxCharacters`;
4. when the next complete block would exceed the target, close the current unit and begin
   the next unit at the next block start;
5. a single complete block larger than the target but no larger than the hard limit forms
   one unit by itself;
6. the final unit ends at the section end.

A unit's text is the exact canonical substring from its first character through its end
offset, including all intervening blank lines and Markdown syntax.

### 10.3 Oversized atomic blocks

A block larger than `atomicBlockHardMaxCharacters` is handled conservatively:

- a well-formed table may be split only between complete rows;
- a list may be split only between complete list items;
- repeated table headers may be supplied as referenced context but may not be duplicated
  into the canonical unit text;
- an oversized prose paragraph, equation block, code block, or structurally ambiguous
  block is marked `needs_review`;
- no ordinary LLM request is created for an unresolved oversized atomic block.

Do not split ordinary prose at arbitrary character or token positions.

### 10.4 Unit numbering and identifiers

`chunkNumber` is one-based within each section segment.

Use:

```text
pub:<paperID>:sec:<sectionOrdinal four digits>:unit:<chunkNumber four digits>
```

Example:

```text
pub:34:sec:0017:unit:0002
```

### 10.5 Partition invariant

Within each section:

- source-unit spans must not overlap;
- source-unit spans must not leave unaccounted gaps;
- concatenating unit substrings in order must reproduce the exact section substring.

Excluded and context-only units remain part of this partition.

## 11. Content eligibility

Each unit has one `eligibility` value:

```text
eligible
context_only
excluded
needs_review
```

and zero or more `exclusionReasons`.

### 11.1 Eligible content

Eligible when source quality permits:

- prose in abstracts, introductions, methods, data, results, discussions, conclusions,
  appendices, and other scientific sections;
- key points and highlights;
- data and software availability statements;
- complete lists;
- correctly linearized tables;
- unequivocal rows or cells in partially recoverable tables;
- self-contained caption text;
- equations accompanied by explanatory prose in the same or explicitly referenced unit.

### 11.2 Context-only content

Normally context-only:

- title and section headings;
- journal and publisher metadata;
- author and affiliation blocks;
- article-history metadata;
- acknowledgments;
- author-contribution statements;
- repeated page-header or page-footer noise;
- table headers supplied only to interpret a separately bounded table row group.

A heading may be supplied to the model as context, but a semantic assertion may not be
accepted when its only support is a structural heading.

### 11.3 Excluded content

Exclude from ordinary Pilot 1 semantic extraction:

- reference-list sections;
- visual-only figure meaning;
- image links with no self-contained caption text;
- standalone equations without explanatory prose;
- unrecoverable table structures;
- empty or conversion-artifact blocks;
- source code with no explanatory publication prose;
- content outside the frozen target inventory.

### 11.4 Needs-review content

Use `needs_review` when the unitizer cannot safely preserve meaning and exact offsets,
including:

- oversized unsplittable atomic blocks;
- ambiguous reference-section boundaries;
- broken tables with uncertain row or column alignment;
- damaged text whose missing content changes interpretation;
- malformed Markdown fences or structures that prevent deterministic partitioning.

No `needs_review` unit is treated as a correct empty extraction.

## 12. Tables, captions, equations, and figures

### 12.1 Tables

Record:

```text
tableQuality:
  well_formed
  partially_recoverable
  broken
```

- `well_formed`: eligible as exact Markdown.
- `partially_recoverable`: only unequivocal row or cell spans may support assertions.
- `broken`: excluded and paired with `unrecoverable_table_structure`.

Metric values, parameter values, units, inequalities, intervals, and ranges remain exact
source strings. The unitizer performs no numeric normalization.

### 12.2 Captions

A self-contained textual caption is eligible. The evidence is the caption text, not the
associated image.

### 12.3 Equations

Equation semantics are eligible only when explanatory prose supports the interpretation.
A candidate may cite the explanatory prose and, when necessary, the exact equation span as
separate evidence spans. Equation-only reconstruction is out of scope.

### 12.4 Figures

Visual figure content is out of scope. The PDF or extracted image may be consulted for
conversion diagnosis, but it cannot supply benchmark evidence unavailable in the canonical
Markdown given to the extractor.

## 13. Canonical source-unit record

Every JSONL record must contain all required fields. Absence is represented by `null`,
`[]`, or `false`, never by omitting a required key.

```json
{
  "contractVersion": "0.1.2",
  "paperID": "34",
  "canonicalArtifactID": "https://doi.org/...",
  "recordType": "journal_article",
  "phaseASchemaVersion": "1.1.0",
  "phaseAVersion": "1.0.9",

  "sourceFile": "data/raw/papers/markdowns/34/markdown/34_md.md",
  "rawFileSha256": "...",
  "canonicalTextSha256": "...",

  "sourceUnitID": "pub:34:sec:0017:unit:0002",
  "sectionID": "pub:34:sec:0017",
  "sectionOrdinal": 17,
  "sectionLevel": 3,
  "sectionTitleRaw": "**3.4. Further Discussion**",
  "sectionTitleNormalized": "3.4. further discussion",
  "sectionPath": [
    "pub:34:sec:0014",
    "pub:34:sec:0017"
  ],
  "sectionRole": "discussion",
  "sectionRoleRule": "normalized_heading_pattern",

  "chunkNumber": 2,
  "contentTypes": ["prose"],
  "eligibility": "eligible",
  "exclusionReasons": [],

  "text": "Exact canonical Markdown substring...",
  "sectionStartOffsetInDocument": 51000,
  "sectionEndOffsetInDocument": 58700,
  "startOffsetInDocument": 54810,
  "endOffsetInDocument": 56800,
  "startOffsetInSection": 3810,
  "endOffsetInSection": 5800,
  "startLine": 280,
  "endLine": 297,

  "textHash": "...",
  "inputHash": "...",

  "markerBlockRefs": [],
  "pageRefs": [],

  "deterministicNodeRefs": [],
  "deterministicEdgeRefs": [],
  "deferredRecordRefs": [],
  "eligibleCategories": ["B-P11"],
  "eligibleOperationalTargetIDs": [],
  "adjacentUnitRefs": {
    "previous": "pub:34:sec:0017:unit:0001",
    "next": null
  }
}
```

The numeric values above are illustrative only.

### 13.1 Required core fields

```text
contractVersion
paperID
canonicalArtifactID
recordType
phaseASchemaVersion
phaseAVersion
sourceFile
rawFileSha256
canonicalTextSha256
sourceUnitID
sectionID
sectionOrdinal
sectionLevel
sectionTitleRaw
sectionTitleNormalized
sectionPath
sectionRole
sectionRoleRule
chunkNumber
contentTypes
eligibility
exclusionReasons
text
sectionStartOffsetInDocument
sectionEndOffsetInDocument
startOffsetInDocument
endOffsetInDocument
startOffsetInSection
endOffsetInSection
startLine
endLine
textHash
inputHash
```

### 13.2 Required context fields

The following keys are required but may contain empty arrays or null values:

```text
markerBlockRefs
pageRefs
deterministicNodeRefs
deterministicEdgeRefs
deferredRecordRefs
eligibleCategories
eligibleOperationalTargetIDs
adjacentUnitRefs
```

## 14. Hash definitions

### 14.1 `textHash`

```text
sha256(UTF-8(text))
```

### 14.2 `inputHash`

Compute SHA-256 over the UTF-8 encoding of canonical JSON with:

- sorted object keys;
- no insignificant whitespace;
- `ensure_ascii=false`;
- the following projection only:

```text
contractVersion
paperID
sourceFile
canonicalTextSha256
sourceUnitID
sectionID
chunkNumber
startOffsetInDocument
endOffsetInDocument
text
```

`inputHash` identifies the immutable source-unit input. Model prompts, adjacent context,
eligible targets, deterministic endpoints, and run settings receive separate hashes in
the later request/run contract.

## 15. Routing and context envelope

### 15.1 Ontology-native routing

`eligibleCategories` uses the publication routing categories `B-P01`–`B-P13`.

`eligibleOperationalTargetIDs` must reference operational IDs from:

```text
src/extraction/llm/publications/publication_target_inventory.yaml
```

Routing may narrow the target set but may not authorize a class or relation outside the
binding inventory.

### 15.2 Deterministic context

`deterministicNodeRefs`, `deterministicEdgeRefs`, and `deferredRecordRefs` contain exact
identifiers from the frozen Phase B publication output. They are context or resolver
inputs; they are not LLM-generated evidence.

### 15.3 Previously accepted local candidates

Previously accepted local candidates are run-specific and must not be embedded into the
immutable source-unit record. They belong in the later request envelope and must retain
their own candidate IDs and evidence references.

## 16. Request context across source units

The canonical units themselves have zero overlap. Request context is assembled separately
and never changes source-unit identity or evidence offsets.

### 16.1 Default context policy

The default policy name is:

```text
complete_section_when_budget_allows
```

Every request must include its primary source unit. The request builder then applies these
rules in order:

1. when all eligible units from the primary unit's section fit within the model-specific
   request budget, include the complete section;
2. otherwise include bounded complete neighboring units from the same section according
   to routing relevance and proximity;
3. include units from adjacent sections only when the target requires distributed context,
   such as cross-section discourse relations or coreference;
4. use a selective document-level pass only for targets that cannot be supported or
   reconciled through bounded section-aware context;
5. never truncate or anonymously copy a canonical unit merely to fill a context window.

The policy uses the available model context window without treating that maximum capacity
as the preferred extraction granularity.

### 16.2 Required request-context record

The request must record:

```text
primarySourceUnitID
contextSourceUnitIDs
contextPolicyName
contextPolicyVersion
modelContextBudgetTokens
estimatedInputTokens
includedCompleteSection
omittedEligibleSourceUnitIDs
contextSelectionReason
```

### 16.3 Evidence rules across units

1. copied anonymous snippets are forbidden;
2. every supplied context text retains its own `sourceUnitID`, offsets, and hashes;
3. evidence from a context unit is valid only when the candidate explicitly references
   that unit;
4. one evidence span may not cross a unit boundary;
5. distributed evidence is represented by multiple evidence spans;
6. node evidence does not automatically establish a relation;
7. an edge requiring cross-unit support must cite edge-specific evidence from one or more
   identified units;
8. request-level context may support interpretation, but only cited source-unit spans may
   support accepted assertions.

## 17. Evidence interface

A later candidate schema must be able to reference:

```text
sourceArtifactID
sourceUnitID
sectionID
sectionTitle
evidenceText
startOffsetInUnit
endOffsetInUnit
startOffsetInDocument
endOffsetInDocument
evidenceHash
```

For every evidence span:

```text
unit.text[startOffsetInUnit:endOffsetInUnit] == evidenceText
canonicalDocument[startOffsetInDocument:endOffsetInDocument] == evidenceText
```

must both hold.

Repeated identical strings require offsets; text matching alone is insufficient.

## 18. Source-unit validation

A unit is valid only when all applicable invariants pass.

### 18.1 Structural invariants

- publication exists in the frozen Phase A corpus;
- source path equals the Phase A `markdown_path`;
- source file exists and is valid UTF-8 after the allowed BOM handling;
- document and section partitions have no overlaps or gaps;
- unit is contained inside exactly one section;
- section and unit IDs match their ordinals;
- unit text equals the canonical document substring;
- section-relative and document-relative offsets agree;
- line numbers contain the unit span;
- text and input hashes recompute exactly;
- required fields are present;
- controlled vocabulary values are valid.

### 18.2 Routing invariants

- every category is one of `B-P01`–`B-P13`;
- every operational target exists in the machine-readable target inventory;
- no out-of-scope or follow-on target is routed to ordinary Pilot 1 extraction;
- abstract classes are never routed as directly instantiable targets;
- reference units have no ordinary semantic target routing;
- excluded and needs-review units do not generate ordinary model requests.

### 18.3 Stable source-unit error codes

```text
SOURCE_FILE_NOT_FOUND
SOURCE_PATH_MISMATCH
INVALID_UTF8
RAW_FILE_HASH_MISMATCH
CANONICAL_TEXT_HASH_MISMATCH
FORBIDDEN_CONTROL_CHARACTER_UNSANITIZED
SECTION_PARTITION_GAP
SECTION_PARTITION_OVERLAP
UNIT_PARTITION_GAP
UNIT_PARTITION_OVERLAP
UNIT_OUTSIDE_SECTION
UNIT_TEXT_MISMATCH
OFFSET_MISMATCH
LINE_RANGE_MISMATCH
TEXT_HASH_MISMATCH
INPUT_HASH_MISMATCH
UNKNOWN_SECTION_ROLE
UNKNOWN_CONTENT_TYPE
UNKNOWN_ELIGIBILITY
UNKNOWN_ROUTING_CATEGORY
UNKNOWN_OPERATIONAL_TARGET
OUT_OF_SCOPE_TARGET_ROUTED
ABSTRACT_TARGET_ROUTED
REFERENCE_SCOPE_AMBIGUOUS
OVERSIZE_ATOMIC_BLOCK
BROKEN_TABLE_STRUCTURE
```

Generation failures are not semantic abstentions and must not be counted as correct empty
outputs.

## 19. Output artifact and determinism

Recommended repository locations:

```text
docs/publication_source_unit_contract.md
src/extraction/llm/publications/publication_source_unit_config.yaml
src/extraction/llm/publications/build_publication_source_units.py
data/interim/papers/llm/evidence_units.jsonl
```

The JSONL output must be:

- UTF-8;
- LF-terminated;
- one source-unit object per line;
- ordered by natural `paperID`, then `sectionOrdinal`, then `chunkNumber`;
- byte-identical across repeated runs with identical inputs and configuration.

The generator must record:

```text
generatorVersion
contractVersion
targetInventoryVersion
ontologyVersion
canonicalCorpusSha256
configurationSha256
generatedAt
```

`generatedAt` belongs in run metadata and must not make the canonical unit records
nondeterministic.

## 20. Pilot sample freeze record

Before annotation or formal Pilot 1 execution, record for each of the twelve artifacts:

- `paperID`;
- `recordType`;
- canonical artifact identifier;
- repository-relative Markdown path;
- raw Markdown SHA-256;
- canonical text SHA-256;
- Marker conversion version, when recoverable;
- chunks and metadata file SHA-256 values;
- Phase A schema and version;
- Phase B artifact/version and hash;
- ontology version and OWL SHA-256;
- target-inventory version and hash;
- source-unit-contract version and hash;
- source-unit generator version and configuration hash;
- unit count and eligibility counts.

The Marker version is not present in the reviewed retained metadata and therefore remains
a required freeze-record item to recover from the original conversion environment or
record explicitly as unavailable with justification. It must not be guessed.

## 21. Non-goals

This contract does not:

- resolve DOI-less citations;
- interpret visual figures;
- reconstruct damaged tables;
- infer standalone equation meaning;
- merge entities across papers or sources;
- create global canonical IDs;
- mutate frozen Phase B outputs;
- write to Neo4j;
- define the candidate lifecycle after extraction;
- define gold matching or evaluation thresholds; or
- choose a model or provider.

## 22. Validation gates

### 22.1 Contract-freeze gate

This design contract may be marked final for implementation after all of the following
static and methodological conditions pass. Production code is not required for this gate.

- [x] the machine-readable target inventory has been reviewed;
- [x] all ontology IDs and operational signatures have been statically validated against
      frozen ontology 0.1.4;
- [x] the binding authority order is aligned across the contract artifacts;
- [x] all reviewed-source hashes match the current repository bytes;
- [x] compatibility with the frozen Publication Phase A corpus is established;
- [x] canonical Markdown is frozen as the evidence authority;
- [x] section segmentation and Markdown-block-boundary unitization rules are frozen;
- [x] `preferredUnitMaxCharacters: 10000` and
      `atomicBlockHardMaxCharacters: 20000` are frozen;
- [x] zero-overlap partitioning and zero-based, half-open Unicode code-point offsets are
      frozen;
- [x] `complete_section_when_budget_allows` is frozen as the request-context policy,
      separately from canonical source-unit size;
- [x] supported, context-only, excluded, needs-review, and unsupported content rules are
      frozen;
- [x] the twelve-artifact design sample is identified; and
- [x] no unresolved methodological contradiction remains.

### 22.2 Implementation-acceptance gate

After this contract is frozen, the later implementation is accepted only after:

- [ ] the production source-unit builder is implemented;
- [ ] the builder reproduces source units over all twelve design-sample artifacts;
- [ ] section and unit partitions pass no-gap/no-overlap checks;
- [ ] reference sections and post-reference appendices are handled correctly;
- [ ] table-quality, damaged-content, malformed-content, and oversized-block handling
      conforms to this contract;
- [ ] exact evidence slicing passes for representative prose, list, table, caption, and
      equation-with-prose cases;
- [ ] repeated builds are byte-identical;
- [ ] source-unit tests cover the stable error codes;
- [ ] the pilot sample hashes and conversion provenance are recorded in the freeze record;
- [ ] the candidate-output schema uses the same IDs, offsets, and evidence semantics; and
- [ ] the request builder implements `complete_section_when_budget_allows` without
      changing canonical source-unit identity, text, offsets, or hashes.

## 23. Acceptance statement

Passing the contract-freeze gate makes this document the final binding design contract
used to build the Publication Pilot 1 implementation. Passing the later
implementation-acceptance gate validates that implementation against the already frozen
contract. Implementation acceptance is not a prerequisite for freezing the design
contract.

Any later change to canonical text normalization, section boundaries, unitization
thresholds, offset semantics, eligibility rules, request-context policy, or hash
definitions requires a version increment and regeneration of all affected source units,
annotations, requests, predictions, and evaluation results.
