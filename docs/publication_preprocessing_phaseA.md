# CIROH Publications Preprocessing — Phase A

**Study 2: Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**  
**Artifact type:** Scientific publications  
**Target script:** `src/preprocessing/build_publication_corpus.py`  
**Target output:** `data/interim/papers/ciroh_publication_corpus.json`

---

## 1. Purpose

This document defines the contract for **Phase A preprocessing of the curated CIROH publication corpus**.

Phase A transforms the curated publication roster, bibliographic records, PDFs, and Marker-normalized Markdown files stored under:

```text
data/raw/papers/
```

into one deterministic intermediate corpus:

```text
data/interim/papers/ciroh_publication_corpus.json
```

The intermediate corpus is the stable input for the deterministic publication extractor implemented in Phase B.

Phase A is responsible for:

- reconciling the curated publication roster with the BibTeX export;
- applying explicit human-curated overrides;
- establishing a canonical public identifier for every publication;
- normalizing bibliographic metadata;
- preserving author order;
- reading the normalized Markdown text for deterministic structural extraction;
- mechanically extracting document headings;
- mechanically detecting explicitly declared keywords;
- mechanically detecting DOI occurrences in reference sections;
- mechanically detecting identifiers in data- and code-availability sections;
- recording repository-relative source-file locations;
- reporting conflicts and anomalies;
- producing deterministic, byte-stable JSON.

Phase A does not populate the ontology and does not create KG nodes or edges.

---

## 2. Position in the pipeline

```text
Curated source corpus
---------------------
data/raw/papers/publications.bib
data/raw/papers/bib_entries_metadata.xlsx
data/raw/papers/pdfs/
data/raw/papers/markdowns/

Human-curated exceptions
------------------------
data/curation/papers/publication_curation_overrides.yaml

                    ↓

Phase A — Publication corpus preprocessing
------------------------------------------
src/preprocessing/build_publication_corpus.py

                    ↓

data/interim/papers/ciroh_publication_corpus.json

                    ↓

Phase B — Deterministic ontology extraction
-------------------------------------------
src/extraction/deterministic/extract_publication.py

                    ↓

data/interim/papers/publication_nodes_edges.json
```

Phase B must consume the consolidated Phase A corpus as its authoritative manifest rather than independently reconciling Excel, BibTeX, and publication files again. It may load publication text only from the repository-relative `source_files.markdown_path` recorded for each publication. Phase B must not repeat Excel/BibTeX/file reconciliation.

---

## 3. Frozen corpus definition

The initial frozen corpus represents the manually curated CIROH publication collection as of March 2026.

Expected current-snapshot anchors:

```text
Curated Excel records:          228
Regular publications:           227
Corrigenda:                        1
BibTeX entries:                 227
Expected Phase A records:       228
```

The identifiers used for filenames and directory names, such as:

```text
1
5
87
87-corrigendum
109
```

are local corpus-management identifiers. They are not public bibliographic identifiers and have no meaning outside this corpus.

The local identifiers must not be renumbered because they already connect:

- the curated Excel roster;
- PDF filenames;
- Marker output directories;
- Markdown filenames;
- auxiliary Marker outputs.

---

## 4. Required inputs

### 4.1 Curated roster

```text
data/raw/papers/bib_entries_metadata.xlsx
```

Required columns:

```text
id
ZoteroID
title
year
doi
url
journal
```

The Excel workbook defines which 228 publication artifacts belong to the frozen corpus.

The `id` column becomes `local_paper_id` in Phase A.

### 4.2 Zotero BibTeX export

```text
data/raw/papers/publications.bib
```

The BibTeX export contains the bibliographic records available in the curated Zotero library.

The current snapshot is expected to contain:

```text
221 article entries
5 inproceedings entries
1 inbook entry
227 entries total
```

One BibTeX entry represents a preprint that is intentionally superseded by its peer-reviewed final publication through a curation override.

### 4.3 Original PDFs

```text
data/raw/papers/pdfs/{local_paper_id}.pdf
```

Examples:

```text
data/raw/papers/pdfs/1.pdf
data/raw/papers/pdfs/87.pdf
data/raw/papers/pdfs/87-corrigendum.pdf
```

Every curated publication must have exactly one corresponding PDF.

### 4.4 Marker-normalized publication directories

```text
data/raw/papers/markdowns/{local_paper_id}/
```

Expected structure:

```text
{local_paper_id}/
├── chunks/
│   ├── {local_paper_id}_chunks.json
│   └── {local_paper_id}_chunks_meta.json
├── json/
│   ├── {local_paper_id}_json.json
│   └── {local_paper_id}_json_meta.json
└── markdown/
    ├── {local_paper_id}_md.md
    ├── {local_paper_id}_md_meta.json
    └── extracted images
```

The canonical textual representation is:

```text
data/raw/papers/markdowns/{local_paper_id}/markdown/{local_paper_id}_md.md
```

### 4.5 Human-curated overrides

```text
data/curation/papers/publication_curation_overrides.yaml
```

This file resolves exceptional cases declaratively. Exceptional records must not be implemented as publication-specific `if` statements embedded in Python code.

---

## 5. Explicitly non-authoritative file

The following file is a historical artifact from the CIROH AI Bot pipeline:

```text
data/raw/papers/publication_artifacts.json
```

It is not an input to the dissertation publication pipeline.

The Phase A builder must:

- run successfully when this file does not exist;
- never use it to populate or replace a corpus field;
- never use it to resolve a bibliographic conflict;
- never use its generated keywords;
- never use its LLM-extracted affiliations, ORCID values, emails, or abstracts;
- produce byte-identical output regardless of whether this file is present.

The file may be inspected manually or by a separate diagnostic utility, but `build_publication_corpus.py` must not depend on it.

---

## 6. Phase boundary

### 6.1 Phase A must

Phase A must:

- read and validate the curated Excel roster;
- parse the BibTeX export with a real BibTeX parser;
- match Excel records to BibTeX entries using `ZoteroID`;
- apply only deterministic Unicode and encoding normalization during matching;
- apply the explicit YAML overrides;
- normalize DOI values;
- normalize public URLs conservatively;
- determine the canonical public identifier of every publication;
- parse BibTeX author names and preserve author order;
- derive publication type from BibTeX entry type or override;
- load the complete Marker-produced Markdown;
- normalize line endings to `\n`;
- extract headings mechanically in source order;
- extract an explicit abstract when mechanically identifiable;
- detect explicitly declared keywords only;
- detect DOI occurrences within mechanically identified reference sections;
- detect URLs and DOIs within mechanically identified availability sections;
- preserve repository-relative technical source paths;
- validate all required source files;
- record warnings and metadata conflicts;
- produce deterministic JSON;
- validate the generated corpus before writing it.

### 6.2 Phase A must not

Phase A must not:

- create `Paper`, `Venue`, `Person`, `Subject`, `Identifier`, or other ontology nodes;
- create KG relations such as `hasAuthor`, `publishedIn`, `hasSubject`, `hasIdentifier`, `cites`, `usesDataset`, or `corrects`;
- create `EvidenceSpan` nodes;
- assign ontology inventory IDs;
- infer research problems, methods, datasets, tools, models, findings, limitations, conclusions, or other discourse entities;
- infer keywords from title, abstract, or body text;
- use an LLM;
- make network calls;
- query Crossref, DataCite, ORCID, Zotero, journal websites, or search engines;
- semantically deduplicate authors or venues;
- align publication authors with persons extracted from GitHub, HydroShare, or CIROH Hub;
- interpret figures or tables;
- load extracted images;
- rewrite or silently repair scientific claims;
- use local file identifiers as public bibliographic identifiers;
- store per-file SHA-256 values in the corpus;
- modify any file under `data/raw/papers/`.

---

## 7. Identity and provenance rules

### 7.1 Local corpus identifier

Each record must contain:

```json
"local_paper_id": "109"
```

This field exists only to connect the publication to its local PDF and Marker directory.

It must not be emitted as an ontology `Identifier`.

It must not become the public identifier of a `Paper`.

It must not be used as the future `EvidenceSpan.sourceArtifact`.

### 7.2 Canonical identifier when a DOI exists

DOI values must be normalized by:

- trimming whitespace;
- removing `doi:` prefixes;
- removing `https://doi.org/` or `http://dx.doi.org/` prefixes;
- removing trailing punctuation introduced by prose;
- converting the DOI value to lowercase.

Example:

```text
10.5194/HESS-29-547-2025
```

becomes:

```text
10.5194/hess-29-547-2025
```

The public canonical identifier becomes:

```text
https://doi.org/10.5194/hess-29-547-2025
```

### 7.3 Canonical identifier when no DOI exists

When the publication has no DOI, the curated public URL becomes its canonical identifier.

This is a valid expected condition, not an extraction failure.

Paper 109 is the frozen-snapshot regression case:

```text
local_paper_id: 109
doi: null
canonical identifier scheme: url
canonical artifact:
https://scholarsarchive.byu.edu/cgi/viewcontent.cgi?article=1002&context=openwater
```

### 7.4 Required identity fields

Every record must contain:

```json
{
  "local_paper_id": "109",
  "canonical_artifact_id": "https://scholarsarchive.byu.edu/...",
  "canonical_identifier": {
    "scheme": "url",
    "value": "https://scholarsarchive.byu.edu/...",
    "uri": "https://scholarsarchive.byu.edu/..."
  },
  "identifiers": [
    {
      "scheme": "url",
      "value": "https://scholarsarchive.byu.edu/...",
      "uri": "https://scholarsarchive.byu.edu/..."
    }
  ]
}
```

When both DOI and URL exist, `identifiers` must contain both, in fixed order:

1. DOI;
2. URL.

`canonical_artifact_id` must equal the DOI URI when a DOI exists and otherwise the curated URL.

### 7.5 Future KG provenance

Phase B must use:

```text
canonical_artifact_id
```

as the publication-level provenance anchor.

For example:

```json
{
  "sourceArtifact": "https://doi.org/10.5194/hess-29-547-2025",
  "sourceLocation": "markdown:section:References:lines:442-447"
}
```

A local path such as:

```text
data/raw/papers/markdowns/71/markdown/71_md.md
```

may be used internally to retrieve the text, but it must not become the user-facing source artifact.

---

## 8. Source authority and precedence

### 8.1 Inclusion authority

The curated Excel roster is authoritative for:

- inclusion in the frozen corpus;
- `local_paper_id`;
- correspondence with PDFs and Marker directories.

No publication may be added merely because it appears in BibTeX.

No publication may be removed based on semantic-topic classification.

### 8.2 Field precedence

The default precedence is:

1. explicit curation override;
2. curated Excel value;
3. matched BibTeX value;
4. mechanically extracted explicit value from the publication Markdown;
5. `null`.

Field-specific rules:

| Field | Primary authority | Fallback |
|---|---|---|
| title | override, then Excel | BibTeX |
| year | override, then Excel | BibTeX |
| DOI | override, then Excel | BibTeX or explicit front matter |
| public URL | override, then Excel | BibTeX |
| venue | override, then Excel | BibTeX `journal` or `booktitle` |
| authors | override | BibTeX |
| entry type | override | BibTeX entry type |
| volume | override | BibTeX |
| issue/number | override | BibTeX |
| pages | override | BibTeX |
| publisher | override | BibTeX |
| language | override | BibTeX |
| abstract | explicit Markdown Abstract section | BibTeX abstract |
| explicit keywords | explicit Markdown or explicit BibTeX keyword field | none |

The builder must never fill a missing field from `publication_artifacts.json`.

### 8.3 Conflict recording

When non-empty Excel and BibTeX values disagree, the Excel value remains canonical unless an override says otherwise.

The conflict must be recorded as:

```json
{
  "field": "year",
  "excel_value": 2025,
  "bibtex_value": 2024,
  "resolution": "excel_authority"
}
```

Differences caused only by harmless presentation normalization may be omitted from the conflict list.

Examples of harmless normalization include:

- DOI letter case;
- DOI URL versus bare DOI;
- repeated whitespace;
- Unicode composed versus decomposed forms;
- typographic apostrophe versus equivalent BibTeX escape after decoding.

The builder must not use fuzzy matching to silently resolve substantive differences.

---

## 9. BibTeX matching rules

### 9.1 Primary match

For records with a non-empty `ZoteroID`, match the Excel value to the BibTeX entry key exactly.

### 9.2 Safe encoding repair

When an exact key match fails, Phase A may attempt reversible encoding repairs for known mojibake patterns.

Examples include strings such as:

```text
Ram√≠rez
Mu√±oz
Le≈°ƒçe≈°en
Baydaroƒülu
```

The matching procedure must:

1. preserve the original Excel value;
2. attempt only deterministic reversible decoding candidates;
3. accept a repaired key only when it matches exactly one BibTeX key;
4. record the repair in the reconciliation metadata;
5. fail when multiple candidates match;
6. avoid fuzzy string similarity.

A repair record must have the form:

```json
{
  "original_zotero_key": "...",
  "matched_bibtex_key": "...",
  "match_method": "reversible_encoding_repair"
}
```

### 9.3 Unmatched records

A curated record without a BibTeX match is valid only when an explicit override supplies the missing bibliographic information.

The frozen snapshot contains two intentional exceptions:

- publication 71, whose Zotero preprint is replaced by the final peer-reviewed publication;
- `87-corrigendum`, which does not have a separate Zotero record.

All other unmatched curated records are fatal validation errors.

### 9.4 Intentionally unused BibTeX entry

The BibTeX preprint key:

```text
Farmani_Behrangi_Gupta_Tavakoly_Geheran_Niu_2024
```

must be recorded as intentionally superseded rather than as an unexplained orphan.

Its final peer-reviewed replacement is:

```text
https://doi.org/10.5194/hess-29-547-2025
```

---

## 10. Publication types

Map BibTeX entry types as follows:

| BibTeX type | Phase A `record_type` |
|---|---|
| `article` | `journal_article` |
| `inproceedings` | `conference_paper` |
| `inbook` | `book_chapter` |

The corrigendum override uses:

```text
corrigendum
```

Unknown future BibTeX types must be preserved in `bibtex_entry_type`, mapped to `other`, and recorded as warnings rather than silently mapped to an existing type.

Expected current output:

```text
221 journal_article
5 conference_paper
1 book_chapter
1 corrigendum
228 total
```

---

## 11. Author processing

Authors must come from the matched BibTeX entry or an explicit override.

Author order must be preserved.

Each author record must contain all keys:

```json
{
  "position": 1,
  "display_name": "Mohamed Abdelkader",
  "given_names": ["Mohamed"],
  "family_name": "Abdelkader",
  "name_particles": [],
  "suffix": null,
  "literal_name": null,
  "raw_bibtex": "Abdelkader, Mohamed"
}
```

The actual shape may follow the selected BibTeX library, but it must preserve:

- display form;
- family name;
- given name or names;
- particles;
- suffix;
- literal/corporate-author form;
- raw source value;
- author position.

Phase A must not:

- merge authors across publications;
- assign ORCID values from `publication_artifacts.json`;
- assign affiliations from `publication_artifacts.json`;
- infer that two spelling variants are the same person;
- correct personal names using external sources.

Name consolidation and enrichment occur after extraction.

---

## 12. Use of Marker outputs

### 12.1 Canonical text

The canonical text is:

```text
markdown/{local_paper_id}_md.md
```

Phase A reads the canonical Markdown to perform deterministic structural extraction, but the consolidated corpus stores only its repository-relative path and the deterministic elements derived from it. The complete Markdown remains in the raw corpus and is loaded by later stages through `source_files.markdown_path`.

While reading the Markdown for deterministic extraction, normalize only:

- UTF-8 BOM removal;
- CRLF and CR line endings to LF.

Raw files remain immutable. Audit the original normalized Markdown for forbidden C0 control characters, permitting tab and line feed. For extraction only, replace each forbidden control character with exactly one ordinary space so line numbers and character positions do not shift. Use this sanitized copy for headings, abstracts, keywords, reference text and DOI evidence, availability evidence, and Markdown-derived section titles. Do not infer a replacement character or silently rewrite the raw source.

Each affected publication must retain one `unexpected_control_characters` warning whose structured detail includes the repository-relative source path, occurrence count, sorted distinct Unicode code points, and sorted source line numbers.

### 12.2 Markdown metadata

The builder may read:

```text
markdown/{local_paper_id}_md_meta.json
```

to obtain:

- table of contents;
- page count, derived from the number of `page_stats` entries.

Sanitize forbidden control characters in retained Marker-derived textual metadata, including table-of-contents titles, using the same one-character-to-one-space rule.

The builder must not include:

- absolute `debug_data_path`;
- token accounting;
- model-call diagnostics;
- machine-specific paths.

### 12.3 Chunks and hierarchical JSON

The files below are part of the frozen raw corpus:

```text
chunks/{local_paper_id}_chunks.json
chunks/{local_paper_id}_chunks_meta.json
json/{local_paper_id}_json.json
json/{local_paper_id}_json_meta.json
```

For this initial Phase A implementation:

- their existence and JSON validity must be checked;
- their repository-relative paths may be recorded;
- their complete contents must not be copied into the consolidated corpus;
- the complete hierarchical Marker JSON must not be embedded;
- image base64 data must not be embedded;
- extracted images must not be inventoried individually.

Markdown line ranges and heading context are sufficient for the initial deterministic evidence locations.

A later enhancement may use Marker block IDs and page geometry without changing the canonical publication identity.

---

## 13. Mechanical document extraction

### 13.1 Headings

Extract Markdown headings mechanically in source order.

Each heading record must contain:

```json
{
  "level": 2,
  "text": "Methods",
  "normalized_text": "methods",
  "line_number": 87
}
```

Support:

- ATX headings;
- numbered headings such as `## 2 Methods`;
- headings containing Markdown emphasis or HTML span markup.

Preserve the original heading `text`. For controlled matching, normalize a separate value by removing HTML tags, Markdown emphasis, trailing heading markers, section numbering, and repeated whitespace.

Do not classify headings semantically beyond the explicit controlled section patterns below.

### 13.2 Abstract

An explicit Markdown abstract may be extracted when a heading normalizes to:

```text
abstract
```

after removal of section numbering.

After the heading, skip leading blank lines and treat the first contiguous substantive paragraph block as the ordinary abstract. A blank-line boundary before a subsequent ordinary prose block ends the abstract even when the article has no immediately following Introduction heading. A later block may continue the abstract only when it begins with an explicit structured-abstract label such as Background, Context, Objective, Purpose, Methods, Results, Findings, Conclusion, Significance, or Implications. Structured labels may be plain, emphasized, or colon-delimited.

The abstract also ends before the next Markdown heading of any level, an explicit keyword or author-keyword label, Introduction, Main Text, correspondence or affiliation information, email addresses, DOI or publication metadata, manuscript-status dates, copyright or licensing notices, figures, tables, captions, or image Markdown. Keyword values, author names, editorial metadata, correspondence details, affiliations, and unheaded article body text must not enter the abstract.

Validate the logical Markdown candidate using deterministic structural signals. Reject candidates containing image syntax, figure or table captions, embedded article sections, editorial or affiliation blocks, or multiple ordinary body paragraphs beyond the initial block. Length alone is not a rejection rule, although an unusually large structurally contaminated block may strengthen a rejection disposition. When a Markdown candidate is rejected, use an explicit BibTeX abstract when available and record `markdown_abstract_rejected` with a machine-readable reason; otherwise emit `null` and retain the warning.

If no explicit Markdown abstract is found, use the BibTeX abstract when present.

Do not generate or summarize an abstract.

### 13.3 Explicit keywords

Keywords may be extracted only when explicitly declared through a heading or label such as:

```text
Keywords
Key words
Author keywords
Index terms
```

Valid sources:

- an explicit Markdown keyword field;
- an explicit BibTeX `keywords` field.

A heading-delimited keyword declaration skips leading blanks and consumes only its first contiguous non-empty declaration block. It ends at the first subsequent blank line, the next Markdown heading of any level, or an explicit front-matter/body boundary. Boundaries include Abstract, Summary, Introduction, DOI, correspondence, supplemental information, manuscript received/revised/accepted/published statements, copyright or license notices, affiliations, email addresses, ORCID declarations, and clearly formatted institutional or postal affiliation blocks. The same boundaries apply whether represented as headings, emphasized labels, or plain colon-delimited labels. Record `keyword_section_stopped_at_metadata` when a nonblank metadata boundary terminates the block.

Inline labels and emphasized forms such as `**Keywords:**` are supported. Explicit separators are comma, semicolon, middle dot, bullet, newline, vertical-bar variants, and the TeX presentation forms `\cdot`, `$\cdot$`, `\( \cdot \)`, `\bullet`, and `$\bullet$`. Normalize these presentation forms before splitting. Remove surrounding emphasis and list markers, including a leading en dash or em dash, unmatched surrounding parentheses, trailing separators, and one trailing sentence period. Preserve internal hyphens, periods, decimal points, parenthetical punctuation, and a whole-keyword periodic abbreviation. Reject empty or unmatched Markdown values and preserve cleaned keyword order.

Marker may collapse several visually separate keywords into one whitespace-only string. To prioritize precision over recall, a candidate with no recognized explicit separator is ambiguous when it exceeds 80 normalized characters or contains at least 6 whitespace-delimited tokens. Do not emit such a candidate or infer its boundaries. Record `ambiguous_keyword_declaration` with its original value so a later LLM-mediated stage can recover it from the warning or canonical Markdown. An otherwise valid undelimited phrase containing five or fewer tokens remains eligible. Explicit separators override the aggregate declaration token threshold; each resulting candidate is then evaluated independently.

Reject candidate values containing abstract prose, DOI or URL declarations, email addresses, correspondence statements, manuscript-status dates, copyright or licensing statements, affiliations, or supplemental-information statements. Record `rejected_keyword_candidate` with the deterministic reason and original candidate.

Do not infer keywords from:

- title;
- abstract;
- headings;
- body text;
- references;
- `publication_artifacts.json`.

Each keyword record must preserve:

```json
{
  "value": "river ice",
  "raw_value": "River ice",
  "source_type": "markdown_explicit",
  "source_location": {
    "source_artifact": "https://doi.org/...",
    "section": "Keywords",
    "line_start": 24,
    "line_end": 24
  }
}
```

Ambiguous keyword formatting must produce a warning and no inferred keywords.

### 13.4 Reference DOI extraction

Reference DOIs may be extracted only from a mechanically identified reference section.

Recognized headings include normalized forms of:

```text
references
bibliography
literature cited
works cited
```

The reference section may continue to the end of the document unless a clear subsequent terminal heading begins. It must never begin outside a mechanically identified reference section.

Within reference text, parse identifiers in this order:

1. balanced standard Markdown-link destinations;
2. Markdown autolinks;
3. bare DOI declarations and resolver URLs in the remaining visible text after complete links are masked.

The link destination is authoritative over a fragmented visible label. Marker may insert presentation whitespace or a single line break inside a DOI suffix. Phase A may remove that formatting boundary only when the adjacent source token provides mechanical continuation evidence, the combined value passes the strict DOI policy, and the scan remains within the same reference occurrence. It must not cross a blank line, Markdown heading, or new list item, and it must not join a DOI to prose, a publication year, another URL, or a neighboring DOI.

This rule corrects the Phase A 1.0.5 failure mode in which the contiguous DOI regular expression stopped at Marker-inserted whitespace and accepted the left fragment before examining the adjacent source token. Destination or resolver evidence takes precedence over visible text reconstruction. A prefix may be repaired only when deterministic local evidence identifies one exact longer value and establishes that the current occurrence was formatting-truncated. Exact structured citation evidence may confirm the same cited work or disambiguate several local extensions. A shorter DOI is not replaced merely because another local DOI begins with the same characters, especially when the shorter value is independently present as a complete authoritative destination. Phase A must not use fuzzy matching, guessed suffixes, external lookup, or publisher templates. An exact local repair is recorded as `repaired_reference_doi_candidate`.

Phase A 1.0.9 also reconciles accepted candidates against parser diagnostics at the source-occurrence level. A candidate extracted from a visible Markdown label or other source start must not remain accepted when the corresponding destination or continuation at that same source construct is rejected as malformed or unresolved and begins with the accepted candidate. The contradicted occurrence is omitted and recorded as `deferred_reference_doi_candidate`; its deterministic reason names the parser diagnostic, and its candidate, complete evidence text, canonical source artifact, section, and line bounds remain auditable. This rule is local to the parser occurrence. It does not reject an independently authoritative exact short DOI merely because a different occurrence or DOI shares its prefix.

A text-derived DOI must match the conservative form `10\.\d{4,9}/[-._;()/:A-Z0-9]+` case-insensitively, contain no whitespace, resolver URL, or Markdown delimiter, and have balanced parentheses. Preserve balanced parentheses and remove only unmatched trailing prose punctuation. DOI suffixes are opaque strings: Phase A does not infer completeness from suffix length, namespace familiarity, publisher, provider, repository, or registration-agency conventions. A valid short or base DOI remains valid when another local DOI has a longer suffix, and a non-DOI service URL ending in `/bibtex` does not alter DOI completeness. Markdown contamination, unbalanced delimiters, resolver text inside a bare DOI, neighboring URL/DOI contamination, and invalid source continuations are objective rejection grounds.

Phase A performs deterministic extraction and normalization; it does not verify DOI registration, existence, artifact type, or universal completeness. A new syntactically valid DOI namespace requires no code or configuration change. When a syntactically plausible candidate has a genuine boundary or completeness concern that neither source structure nor exact local evidence can resolve, omit it from accepted identifiers and preserve it as `deferred_reference_doi_candidate` with its candidate, evidence text, source artifact, source location, context, and reason. Deferred candidates remain available for later human, LLM-assisted, or registry-assisted review, but Phase A itself performs none of those review methods.

Each reference DOI record must include:

```json
{
  "doi": "10.1029/2022wr033075",
  "uri": "https://doi.org/10.1029/2022wr033075",
  "reference_text": "...",
  "source_location": {
    "source_artifact": "https://doi.org/...",
    "section": "References",
    "line_start": 742,
    "line_end": 746
  }
}
```

Duplicate occurrences of the same normalized DOI within one paper must be collapsed into one record with an ordered list of unique source-line occurrences.

Phase A must not decide whether an external DOI identifies a paper, dataset, or software artifact. It must preserve the reference text needed for Phase B to apply the ontology’s cited-DOI typing rule.

### 13.5 Availability identifiers

Mechanically identify sections such as:

```text
Data Availability
Data Availability Statement
Data and Code Availability
Code Availability
Software Availability
Availability of Data and Materials
Code and Data Availability
```

Extract explicit URLs and DOIs appearing within those sections using the same destination-first, source-bounded split parser as reference DOI extraction. The same structural syntax, exact-local-evidence repair, and deferred-disposition policy applies to availability DOIs; unresolved candidates use `deferred_availability_doi_candidate`. Normalize only absolute HTTP(S) URLs, preserve balanced URL parentheses, remove unmatched trailing prose punctuation, and reject Markdown wrappers or nested malformed URL text. A DOI-resolver URL is emitted only as a DOI, never as a generic URL.

An availability section ends at the earliest of the next Markdown heading of any level, the beginning of another recognized terminal section, or the end of the document. Terminal sections include References, Bibliography, Acknowledgments, Author Contributions, Funding, institutional-review and informed-consent statements, Conflicts of Interest, Declarations, Supplementary Materials, and Appendix. Explicit bold terminal labels are boundaries even when Marker places them inline or does not assign a reliable heading level.

Each record must preserve:

- normalized identifier;
- identifier scheme;
- exact section title;
- mechanically assigned section category;
- surrounding evidence text;
- line range;
- publication canonical artifact.

Example:

```json
{
  "section_category": "data_and_code_availability",
  "section_title": "Code and data availability",
  "identifier_scheme": "doi",
  "identifier_value": "10.5281/zenodo.7314083",
  "identifier_uri": "https://doi.org/10.5281/zenodo.7314083",
  "evidence_text": "Interactive Python scripts ... are available at ...",
  "source_location": {
    "source_artifact": "https://doi.org/10.5194/hess-26-3377-2022-corrigendum",
    "line_start": 118,
    "line_end": 121
  }
}
```

Phase A records the explicit identifier and section context. It does not create a `usesDataset`, `mentionsDataset`, or `usesTool` relation.

Correct boundary and identifier validation is expected to reduce false-positive reference DOI and availability-identifier totals relative to earlier Phase A parser versions. Historical counts are not acceptance anchors.

---

## 14. Curation overrides

The override file must have a stable declarative schema:

```yaml
schema_version: "1.1.0"

records:
  "42":
    identifier_dispositions:
      - context: reference
        candidate: 10.9999/example
        action: defer
        reason: >
          Corpus curation flags an unresolved source-boundary concern that
          cannot be repaired from deterministic local evidence.

  "71":
    action: replace_bibliographic_record
    source_zotero_key: Farmani_Behrangi_Gupta_Tavakoly_Geheran_Niu_2024
    reason: >
      The Zotero record represents a preprint, while the curated corpus
      contains the final peer-reviewed publication.
    metadata:
      bibtex_entry_type: article
      record_type: journal_article
      title: Do land models miss key soil hydrological processes controlling soil moisture memory?
      authors:
        - display_name: M. A. Farmani
          raw_name: Farmani, M. A.
        - display_name: A. Behrangi
          raw_name: Behrangi, A.
        - display_name: A. Gupta
          raw_name: Gupta, A.
        - display_name: A. Tavakoly
          raw_name: Tavakoly, A.
        - display_name: M. Geheran
          raw_name: Geheran, M.
        - display_name: G.-Y. Niu
          raw_name: Niu, G.-Y.
      venue: Hydrology and Earth System Sciences
      year: 2025
      volume: "29"
      issue: "2"
      pages: "547--566"
      doi: 10.5194/hess-29-547-2025
      url: https://hess.copernicus.org/articles/29/547/2025/

  "87-corrigendum":
    action: add_non_zotero_artifact
    reason: >
      The corrigendum is a separate published artifact discovered while
      retrieving the original publication and has no independent Zotero entry.
    metadata:
      bibtex_entry_type: null
      record_type: corrigendum
      title: 'Corrigendum to "Deep learning rainfall–runoff predictions of extreme events"'
      authors:
        - display_name: Jonathan M. Frame
          raw_name: Frame, Jonathan M.
        - display_name: Frederik Kratzert
          raw_name: Kratzert, Frederik
        - display_name: Daniel Klotz
          raw_name: Klotz, Daniel
        - display_name: Martin Gauch
          raw_name: Gauch, Martin
        - display_name: Guy Shalev
          raw_name: Shalev, Guy
        - display_name: Oren Gilon
          raw_name: Gilon, Oren
        - display_name: Logan M. Qualls
          raw_name: Qualls, Logan M.
        - display_name: Hoshin V. Gupta
          raw_name: Gupta, Hoshin V.
        - display_name: Grey S. Nearing
          raw_name: Nearing, Grey S.
      venue: Hydrology and Earth System Sciences
      year: 2023
      volume: null
      issue: null
      pages: null
      doi: 10.5194/hess-26-3377-2022-corrigendum
      url: https://doi.org/10.5194/hess-26-3377-2022-corrigendum
    correction_of:
      scheme: doi
      value: 10.5194/hess-26-3377-2022
      uri: https://doi.org/10.5194/hess-26-3377-2022
```

The Python implementation must interpret this general override schema. It must not contain code branches such as:

```python
if local_paper_id == "71":
    ...
```

or:

```python
if local_paper_id == "87-corrigendum":
    ...
```

An `identifier_dispositions` entry is exact and source-scoped. `context` is `reference` or `availability`; `candidate` is the exact normalized DOI candidate; `action` is `defer`; and `reason` records the curation basis without supplying a corrected DOI. When candidate and context do not uniquely identify one occurrence, an optional `occurrence` mapping may add exact `evidence_text`, section, and source-relative line bounds. Exact evidence text is required whenever an occurrence discriminator is used. Every disposition must match exactly one extracted source occurrence. Unused, duplicate, overlapping, or ambiguous dispositions are fatal. The generated deferred warning preserves the source evidence rather than replacing it with YAML text.

Corpus-specific DOI dispositions belong in this declarative file. They must not require publication IDs, exact corpus DOI values, publisher tables, or namespace exceptions in production Python.

---

## 15. Output contract

### 15.1 Top-level structure

```json
{
  "schema_version": "1.1.0",
  "phase_a_version": "1.0.9",
  "source": {
    "artifact_type": "publication",
    "raw_root": "data/raw/papers",
    "corpus_cutoff": "2026-03",
    "selection_method": "manually_curated_zotero_roster"
  },
  "publications": [],
  "known_exclusions": [],
  "warnings": [],
  "summary": {}
}
```

### 15.2 Publication record

Every publication record must contain all keys:

```json
{
  "local_paper_id": "109",
  "canonical_artifact_id": "https://scholarsarchive.byu.edu/...",
  "canonical_identifier": {
    "scheme": "url",
    "value": "https://scholarsarchive.byu.edu/...",
    "uri": "https://scholarsarchive.byu.edu/..."
  },
  "identifiers": [
    {
      "scheme": "url",
      "value": "https://scholarsarchive.byu.edu/...",
      "uri": "https://scholarsarchive.byu.edu/..."
    }
  ],
  "record_type": "journal_article",
  "curation_status": "curated",
  "bibliographic": {
    "title": "Facilitating Effective Utilization of Water Science Research Among Emergency Flood Responders",
    "authors": [],
    "year": 2021,
    "venue": "Open Water Journal",
    "volume": null,
    "issue": null,
    "pages": null,
    "publisher": null,
    "language": null,
    "abstract": null,
    "abstract_source": null
  },
  "content": {
    "headings": [],
    "explicit_keywords": [],
    "reference_dois": [],
    "availability_identifiers": []
  },
  "document_structure": {
    "page_count": null,
    "table_of_contents": []
  },
  "source_files": {
    "pdf_path": "data/raw/papers/pdfs/109.pdf",
    "markdown_path": "data/raw/papers/markdowns/109/markdown/109_md.md",
    "markdown_meta_path": "data/raw/papers/markdowns/109/markdown/109_md_meta.json",
    "chunks_path": "data/raw/papers/markdowns/109/chunks/109_chunks.json",
    "chunks_meta_path": "data/raw/papers/markdowns/109/chunks/109_chunks_meta.json",
    "marker_json_path": "data/raw/papers/markdowns/109/json/109_json.json",
    "marker_json_meta_path": "data/raw/papers/markdowns/109/json/109_json_meta.json"
  },
  "bibliographic_relations": {
    "correction_of": null
  },
  "reconciliation": {
    "excel_matched": true,
    "zotero_key_original": "Henson_Garth_Franklin_2021",
    "bibtex_key": "Henson_Garth_Franklin_2021",
    "bibtex_match_method": "exact",
    "bibtex_entry_type": "article",
    "override_applied": false,
    "override_action": null,
    "conflicts": [],
    "warnings": []
  }
}
```

All keys must always be present. Absence must be represented with `null`, `[]`, or `false`.

### 15.3 Known exclusion record

The intentionally superseded preprint must be represented at top level:

```json
{
  "source_type": "bibtex_entry",
  "source_key": "Farmani_Behrangi_Gupta_Tavakoly_Geheran_Niu_2024",
  "reason": "superseded_by_peer_reviewed_final",
  "replacement_canonical_artifact_id": "https://doi.org/10.5194/hess-29-547-2025"
}
```

---

## 16. Summary contract

The top-level summary must be calculated from the output records and must not contain manually inserted totals.

Required summary fields:

```json
{
  "excel_record_count": 228,
  "bibtex_entry_count": 227,
  "publication_count": 228,
  "with_doi": 227,
  "without_doi": 1,
  "without_doi_but_with_url": 1,
  "by_record_type": {
    "book_chapter": 1,
    "conference_paper": 5,
    "corrigendum": 1,
    "journal_article": 221
  },
  "exact_bibtex_matches": 0,
  "encoding_repair_matches": 0,
  "override_record_count": 2,
  "non_zotero_record_count": 1,
  "known_exclusion_count": 1,
  "pdf_count": 228,
  "markdown_count": 228,
  "chunks_count": 228,
  "papers_with_abstract": 0,
  "papers_with_explicit_keywords": 0,
  "explicit_keyword_count": 0,
  "papers_with_reference_dois": 0,
  "reference_doi_count": 0,
  "papers_with_availability_identifiers": 0,
  "availability_identifier_count": 0,
  "conflict_count": 0,
  "warning_count": 0
}
```

Values shown as zero above are schema examples except where identified as frozen acceptance anchors. They must be computed from the actual corpus.

---

## 17. Validation requirements

### 17.1 Fatal validation failures

The builder must fail and must not overwrite a previously valid output when:

- the Excel file is missing;
- the BibTeX file is missing;
- the override file is missing or invalid;
- required Excel columns are missing;
- Excel contains duplicate `local_paper_id` values;
- a curated record lacks both DOI and URL;
- two final records have the same `canonical_artifact_id`;
- a publication title is empty;
- a publication year is missing or invalid;
- a publication venue is empty without a documented exception;
- a publication has no authors without a documented exception;
- a required PDF is missing;
- a required Markdown file is missing;
- a required Markdown file is not valid UTF-8;
- a required chunks JSON file is missing or invalid;
- an unmatched Zotero key is not resolved by an override;
- one Zotero key matches multiple BibTeX entries;
- an override targets an unknown local paper ID;
- an identifier disposition is unused, duplicated, overlapping, ambiguous, or does not match exactly one source occurrence;
- a `correction_of` target is not a canonical DOI or URL;
- any stored source path is absolute;
- any stored source path escapes the repository raw root;
- an extracted reference DOI fails the strict text-derived DOI policy or has an inconsistent resolver URI;
- an extracted reference DOI contradicts its own exact source boundary evidence;
- duplicate normalized reference DOI records or duplicate source-line occurrences exist within a publication;
- an availability DOI or URL is malformed, contains Markdown wrappers, contradicts its own exact source boundary evidence, or duplicates another normalized availability identifier within a publication;
- a DOI-resolver URL is emitted as a generic availability URL;
- a Markdown-derived abstract, reference DOI, or availability identifier has an invalid source line range;
- a Markdown abstract contains image syntax, figure/table captions, editorial metadata, or content outside its accepted logical block;
- a rejected Markdown abstract remains selected instead of using the explicit BibTeX fallback or `null`;
- an explicit keyword contains an email, DOI/URL declaration, manuscript-status, copyright/license, affiliation, or supplemental-information contamination;
- an emitted undelimited keyword exceeds the documented ambiguity threshold;
- an emitted keyword retains a leading en/em dash list marker or a trailing sentence period;
- an emitted keyword is not identical to the deterministic result of keyword presentation cleanup, or its normalized value is inconsistent with the cleaned value;
- a Markdown keyword source location falls outside the accepted first declaration block;
- any string value anywhere in the in-memory Phase A corpus contains a forbidden C0 control character, including authoritative Excel, BibTeX, or override values that cannot be deterministically repaired;
- an `unexpected_control_characters` warning does not exactly reconcile with the original raw Markdown occurrence count, code points, and source lines;
- a deferred DOI warning lacks its exact candidate, context, reason, evidence text, source artifact, or source-relative location; does not reconcile to one omitted source occurrence; or its candidate remains emitted as accepted;
- the generated corpus fails its internal reconciliation checks.

### 17.2 Nonfatal warnings

Examples of warnings:

- Excel and BibTeX metadata differ but Excel authority resolves the field;
- an auxiliary Marker meta file is missing;
- a Markdown abstract candidate is structurally rejected, with a machine-readable reason and BibTeX fallback disposition;
- keyword formatting is ambiguous and retained only in the warning for later semantic recovery;
- a keyword section stops at front-matter metadata;
- an individual keyword candidate is rejected as contaminated;
- a reference section is absent;
- a malformed or ambiguous split reference DOI is omitted with its original local candidate and source line retained for audit;
- a formatting-truncated reference DOI is repaired only from one exact local full-DOI value with exact structured citation evidence, with the original and corrected values retained in the warning detail;
- a syntactically plausible but locally unresolved reference or availability candidate is omitted as a deferred warning with its complete source evidence and curation reason;
- an availability section is absent;
- unexpected control characters occur in Marker text; the warning preserves source path, occurrence count, code points, and source lines even though emitted derivatives use the sanitized extraction copy;
- an unknown future BibTeX entry type is mapped to `other`;
- an extra raw directory does not correspond to a curated publication.

The absence of abstract, keywords, references, or availability statements is not itself an error.

### 17.3 Frozen-snapshot acceptance anchors

When run with frozen-snapshot validation enabled, require:

```text
Excel rows:                         228
BibTeX entries:                    227
Output publications:               228
Publications with DOI:             227
Publications without DOI:            1
The DOI-less publication ID:       109
Publications with canonical URL:   228
Overrides applied:                   2
Known superseded BibTeX entries:     1
Papers with explicit keywords:      70
Explicit keyword records:          373
Raw publications with controls:     18
Forbidden controls in output:        0
Output schema version:           1.1.0
Phase A version:                 1.0.9
Reference DOI records:            8,856
Distinct normalized reference DOIs: 6,720
Reference DOI occurrences:        8,963
Papers with availability identifiers: 73
Availability identifier records:    299
Structured warnings:                147
Deferred DOI candidates:              4
```

Specific record checks:

#### Publication 71

```text
title:
Do land models miss key soil hydrological processes controlling soil moisture memory?

canonical artifact:
https://doi.org/10.5194/hess-29-547-2025

year:
2025

record type:
journal_article

override:
replace_bibliographic_record
```

#### Publication 87

```text
canonical artifact:
https://doi.org/10.5194/hess-26-3377-2022
```

#### Publication 87-corrigendum

```text
canonical artifact:
https://doi.org/10.5194/hess-26-3377-2022-corrigendum

year:
2023

record type:
corrigendum

correction_of:
https://doi.org/10.5194/hess-26-3377-2022
```

#### Publication 93

Title must be non-empty and equal to:

```text
EASYMORE: A Python package to streamline the remapping of variables for Earth System models
```

#### Publication 109

```text
doi:
null

canonical identifier scheme:
url
```

#### Publication 207

Title must be non-empty and equal to:

```text
Nature-based solutions as buffers against coastal compound flooding: Exploring potential framework for process-based modeling of hazard mitigation
```

#### Publication 244

The Markdown abstract must contain only the explicit logical abstract paragraph. It begins with `Climate risk assessments typically focus on large rivers` and ends with `elucidates the fine-scale distribution of climate risks across communities.` It must not include the unheaded introductory body, Figure 1, or Main Text.

#### Publication 265

The explicit keywords, in source order, must be exactly:

```text
Hydrology
Hydrometeorology
Uncertainty
Ensembles
Hydrologic models
Forcing
```

The abstract, DOI, correspondence, manuscript dates, copyright notice, and affiliations following the declaration must not be emitted as keywords.

---

## 18. Determinism requirements

The same authoritative inputs must produce byte-identical output.

Required conventions:

- no execution timestamps;
- no random UUIDs;
- no network-derived values;
- no absolute filesystem paths;
- no filesystem traversal-order dependence;
- normalize Markdown line endings to `\n`;
- serialize UTF-8 with `ensure_ascii=False`;
- use stable indentation;
- use stable key ordering;
- terminate the file with exactly one newline;
- naturally sort publication records by numeric local ID, placing suffix records immediately after their numeric base;
- preserve author order;
- preserve heading order;
- preserve explicit keyword order;
- preserve reference occurrence order;
- preserve availability-identifier order;
- sort warnings and conflicts by stable keys;
- sort top-level exclusions by source key;
- use explicit `null`, `[]`, and `false` values;
- perform no silent source correction.

Recommended serialization:

```python
json.dumps(
    corpus,
    indent=2,
    ensure_ascii=False,
    sort_keys=True,
) + "\n"
```

Per-file SHA-256 values must not appear in the corpus schema.

Tests may calculate hashes externally or compare generated bytes to verify determinism. Such hashes are test artifacts, not publication metadata and not KG provenance.

---

## 19. Required CLI

The script must expose:

```text
--raw-root
--output
--overrides
--expected-record-count
--validate-frozen-snapshot
```

Default values:

```text
--raw-root data/raw/papers
--output data/interim/papers/ciroh_publication_corpus.json
--overrides data/curation/papers/publication_curation_overrides.yaml
```

Expected execution:

```bash
python -m src.preprocessing.build_publication_corpus \
  --validate-frozen-snapshot
```

The script must:

1. build the corpus in memory;
2. validate it;
3. avoid writing when validation fails;
4. write deterministic JSON only after successful validation;
5. print a concise validation report;
6. return exit code `0` on success and nonzero on failure.

---

## 20. Expected validation report

The CLI report must include:

```text
schema version
Phase A version
Excel records
BibTeX entries
publications emitted
records by publication type
publications with DOI
publications without DOI
exact BibTeX matches
encoding-repair matches
override records
known exclusions
PDFs found
Markdown files found
chunks files found
papers with explicit abstracts
papers with explicit keywords
reference DOIs
availability identifiers
metadata conflicts
warnings by category
validation status
output path
```

The report may calculate and print an output-file SHA-256 for development verification, but the hash must not be stored in the corpus and must not be used as user-facing provenance.

---

## 21. Completion criteria

Phase A is complete when:

- `build_publication_corpus.py` implements this contract;
- the override file declaratively resolves publication 71 and the corrigendum;
- the builder succeeds without `publication_artifacts.json`;
- exactly 228 publication records are produced;
- all 228 records have a unique canonical public identifier;
- DOI is preferred over URL for canonical identity;
- paper 109 correctly uses its URL because no DOI exists;
- the corrigendum has its own DOI and corrects the original paper DOI;
- all required raw publication files are accounted for;
- every publication retains its repository-relative `source_files.markdown_path`;
- deterministic headings, abstracts, explicit keywords, reference DOIs, and availability identifiers are extracted from the canonical Markdown without embedding its complete text;
- no title is empty;
- all authors come from BibTeX or an explicit override;
- no AI Bot metadata enters the canonical corpus;
- no per-file hashes are stored;
- no KG nodes or edges are created;
- two independent builds are byte-identical;
- focused preprocessing tests pass;
- the complete Phase A preprocessing test module and frozen-snapshot validation pass.

Downstream Phase B compatibility is versioned and validated in Publication Phase B; closing a new Phase A version does not authorize regenerating or modifying Phase B artifacts.
