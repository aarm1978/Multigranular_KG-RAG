# Study 2 — Step 11 Source-Specific Semantic Extraction Contracts

**Revision:** v0.3 — FINAL-APPROVAL REVIEW CANDIDATE; **NOT FROZEN**  
**Date:** 2026-10-08  
**Scope:** HydroShare, GitHub, and CIROH Hub semantic overlays only  
**Repository:** `aarm1978/Multigranular_KG-RAG`, branch `codex/publication-human-core-annotation-ui`  
**Prospective ontology:** v0.1.6; validated OWL SHA-256 `6ebf7f67f79d8aae4fada176911ed9311964beb567f40a097af9017f1ad9c730`  
**Purpose of this revision:** make three surgical clarifications to the v0.2 candidate: (1) versioned, predeclared `RepositoryPurpose` vocabulary instances distinct from evidence-dependent repository `hasPurpose` edges; (2) explicit post-Publications-production reconsideration gate for unresolved `implementsMethod` proposals without premature alignment; and (3) source-read failures, exact text/hash authority, and own-repository-software scope for `ModelVersion`. All other v0.2 boundaries are preserved.

## 1. Authorities, version boundaries, and preservation

1. `docs/handoffs/STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md` (researcher-closed Step 10) controls the accepted semantic-gap families. The explicitly bounded additions in this Step 11 review candidate do **not** reopen the Step 10 inspection or authorize new ontology classes/relations.
2. `docs/handoffs/STUDY2_HYDROSHARE_V016_ACCEPTANCE.md` and `docs/handoffs/STUDY2_REFERENCE_ENRICHMENT_V1_ACCEPTANCE.md` govern the accepted prospective deterministic backbone. Retain exact existing IDs and reference relations; no historical output is overwritten, deleted, rebuilt, or relabeled.
3. `src/ontology/ontology_spec.yaml`, `docs/ontology_inventory.md`, and `docs/ontology_formalization.md` §12 are the current v0.1.6 ontology authorities for class/relation IDs and domain/range signatures. A source-specific authorization here never alters the TBox.
4. Historical Phase A/Phase B input, mapping, and deterministic contracts remain frozen. **Prospective GitHub LLM-semantic-only exception:** read eligible, already-downloaded descriptive files from `data/raw/coderepos/{repo_name}/contents/` using the existing `repos[].files.downloaded[]` manifest, alongside `readme.text`. This is not a retrospective change to Phase B's statement that its LLM layer would read Phase A prose.
5. The separate frozen Publication semantic authority is the **v0.1.5 successor** (`src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml`), canonical bundle `publication-semantic-v0.1.5-schema-v0.1.3`, prompt `publication-development-0.1.8`. It includes `AgentBasedModel`, Publication-prose `Organization`, and `C-P34 hasComponent`. Do not substitute its superseded v0.1.4 base profile, rewrite closed Steps 7–9, or imply an automatic migration of Publication outputs to v0.1.6.
6. Source-local semantic extraction and validation precede cross-source consolidation. **Step 14** owns cross-artifact entity alignment. This document authorizes **design only**: no new acquisition, changes to Phase A or deterministic Phase B, provider calls, extractor runs, ontology edits, AST parsing, code execution, notebook execution, graph rebuilding, or Codex implementation instructions.

## 2. Cross-source semantic candidates, units, and evidence

### 2.1 Candidate admissibility and outcomes

- **Text-first, bounded targets:** A direct LLM candidate must arise from text explicitly eligible in the corresponding source profile and must fit an allowlisted class/relation. A documented capability is not automatically a claim that the capability was used, run, implemented, or generated in that artifact.
- **Independent node/edge support:** Every **model-authored semantic node** and every proposed semantic relation needs its own sufficient quoted evidence. The six **deterministically seeded controlled-vocabulary** `RepositoryPurpose` instances in §7 are the narrowly defined exception: their authority is the versioned, researcher-approved scheme, not repository prose. Each `hasPurpose` edge still requires repository-specific textual evidence. Endpoint co-occurrence does not supply relation evidence. Multi-fragment support is permissible only where each referenced span and its logical contribution are explicitly preserved.
- **Literal binding:** Preserve the genuine source quotation; validate it against the original permitted input text and bind the source location and frozen version deterministically. Do not invent, silently repair, extend, or re-anchor provider-authored evidence. Normalized text may aid request construction, but **evidenceText** must remain recoverable literally from the authority identified for that unit.
- **Disposition categories:** Distinguish `validated`, `abstained_no_evidence`, `abstained_ambiguous_semantics`, `rejected_invalid_assertion`, `failed_source_or_evidence_binding`, and `unresolved_endpoint`. `abstained_no_evidence` is permissible **only after the required eligible source text was successfully read and verified** and no admissible evidence was found. A manifest entry with `downloaded=true` whose content is missing, unreadable/malformed, or fails verified content integrity is a **source failure**, not no-evidence. Record `failed_source_or_evidence_binding` with a mandatory diagnostic reason distinguishing at least `downloaded_file_missing`, `downloaded_file_unreadable`, `source_content_integrity_failure`, and `evidence_quote_unbound`; preserve the affected repo/page/resource, path/field, and source version. A partial owner-level extraction must be marked incomplete if eligible inputs failed, even if other units succeeded. An empty accepted result is not proof that no such real-world entity exists.
- **Existing deterministic assertions:** Reuse exact-source artifact/entity IDs and existing edges. A stronger, separately evidenced semantic relation may coexist with an accepted syntactic reference without replacing it. Do not emit duplicate edges with equivalent predicate and endpoints; preserve new supporting evidence without duplicating accepted assertions.
- **Source-local identity:** New entity occurrences are source-local unless the target is an approved controlled-vocabulary value or a valid exact-source endpoint. No name-only cross-source merges; no arbitrary external identifier repair.
- **Role distinctions:** `uses`, `implementedBy`, `describes`, `references`, `generatedBy`, and specialized `mentionsX` have different positive criteria. URL presence, shared document, or co-occurrence never proves a stronger role.
- **D-26 `mentions`:** Not a fallback, model-authorable target, or default edge for unresolved roles. It is **pipeline-derived only** under its existing source-containment, accepted-evidence, and nonredundancy policy. Never create a separate generic parent edge merely because a specialized `mentionsX` already exists.
- **Conflicts:** Preserve incompatible assertions and their distinct evidence as candidates/diagnostics. Do not silently choose an apparently more plausible role, canonical label, or model subtype.
- **Reproducibility when later authorized:** Persist frozen source version, request/context and contract versions, exact provider response, evidence-binding results, and accepted/rejected/unresolved outcomes. No new provider calls are authorized by this candidate.

### 2.2 Minimum source-unit contract — reuse existing tooling

Every eligible semantic input unit must retain, through existing components or a minimal source-specific adapter:

| Field or property | Requirement |
|---|---|
| `artifactFamily`, accepted owner ID | `hydroshare`, `github`, or `ciroh_hub`; exact Phase B artifact endpoint when present |
| `sourceUnitID` | Stable *within the frozen source snapshot*, derived from the owner and original textual boundaries; not a new global identity service |
| Source identity | HydroShare resource/field or README path; GitHub full repository name, pinned commit, repository-relative path; Hub `page_key` and `canonical_url` |
| Snapshot/version | Resource source/version when available; GitHub `archive.frozen_commit_sha`; Hub `content_sha256` (plus `file_sha256`/original-source lineage when relevant) |
| Text span and coordinates | Exact original evidence text and deterministic field, line, offset, or Markdown-cell location sufficient for reproducible lookup |
| Authoritative text and hashes | Identify the exact content representation used for quoted evidence, its SHA-256, and (for downloaded raw files) the original file-byte SHA-256; preserve the unit bounds in that authority, never in a re-rendered or model-normalized reconstruction |
| Read/integrity result | Record success or a file/field-specific failure reason before interpreting absence of semantic evidence |
| Structural context | Existing source heading/section IDs or nearby heading labels for interpretation; context is not automatically assertion evidence |

**Unit boundaries:** HydroShare uses abstract and README sections; GitHub uses README/document sections, self-contained CITATION/changelog passages, or individual notebook **Markdown** cells and their nested headings; Hub uses a page heading section or bounded visible MDX block. Preserve context for resolving references, but do not assume that separate facts in the same section imply a relation. Avoid a new common framework or fixed universal chunk size. Where an existing deterministic section ID applies exactly, reuse it; otherwise retain a stable page/file-and-span anchor without inventing a new ontology node.

### 2.3 Exact text authority, content integrity, and coordinate binding

The **evidence authority** is the actual input text representation verified for that unit, not a summary, model prompt rewrite, visually reconstructed page, or repository-relative path alone. Persist `authorityTextSha256 = SHA256(UTF-8 bytes of the exact authoritative text)` and the immutable source-version identity for each utilized authority. Where a large authority is segmented, preserve both its full-text hash and the original segment bounds (a unit-text hash may also be retained). Evidence quotations must match a literal substring of that authority; line numbers are one-based and character offsets are zero-based, half-open Unicode-code-point positions **within that authority**. Snapshot SHA, path, and text hash play different roles and must not be conflated.

- **HydroShare:** For an abstract, the exact frozen Phase A/Phase B text field identified as the extraction input is the authority; for a source-verified README, use that actual README text. Record the resource ID, field or original README path, available source version, and hash of the precise text used. Do not infer unavailable README contents or read dataset files.
- **GitHub README from Phase A:** For the one README represented by `repos[].readme.text`, the **existing, Phase A-decoded and line-ending-normalized `readme.text` string** is the sole textual authority for that read; record its UTF-8 SHA-256, `readme.source_path`, owner and `frozen_commit_sha`. Do not also create a raw-file semantic unit for the same repository-relative path.
- **Additional downloaded GitHub prose files:** Resolve only `files.downloaded[]` paths in the existing pinned `contents/` tree. Preserve `rawFileSha256 = SHA256(original downloaded file bytes)` and `authorityTextSha256` over the exact decoded text used for extraction. The minimal reader must use a documented fixed decode/line-ending policy (consistent with the existing Phase A text-reader conventions) and record it; quotations/offsets bind to that resulting authority string, never silently to differently decoded raw bytes or a cleaned prompt view.
- **GitHub notebooks:** Preserve the full downloaded `.ipynb` file-byte SHA-256. For each eligible Markdown cell use the original JSON `source` text (joining string-array fragments in order where necessary), its own `authorityTextSha256`, the original zero-based cell index, and cell-local original offsets/lines. Code cells, outputs, and inferred runtime state cannot supply this authority.
- **CIROH Hub:** `pages[].content_mdx` is the sole semantic text authority, with its frozen `content_sha256` (SHA-256 of the normalized UTF-8 MDX body) verified before use. Quote positions refer to the original `content_mdx` string, including its preserved structural characters; a masked visibility view, stripped MDX, or reconstructed rendering may aid selection but cannot redefine positions or evidence text. Preserve `page_key`, `canonical_url`, `corpus_path`/`source_path` lineage, and `file_sha256` when relevant.

A missing or unreadable `downloaded=true` file, invalid notebook JSON/Markdown-cell source, unavailable required field, or hash mismatch must produce an explicit technical failure for that source; it must **not** become `abstained_no_evidence`, silently change the evidence authority, or cause a replacement download. Previously verified evidence from other unaffected source units may remain usable, with partial-completeness recorded. These rules are contract-level requirements for Step 12, not an instruction to re-audit the corpus now.

## 3. HydroShare semantic profile

**Eligible input:** Source-verified resource abstract (`DatasetResource` metadata/attribute) and materialized original README prose belonging to the same resource. Deterministic resource type, exact ID, and graph are context only. Evidence must identify resource ID and source field/README path. No dataset-file content inspection, external service probing, or reinterpretation of heuristic `data_services` inferred from extensions.

| Entity (ontology ID) | Relation (inventory ID) | Positive criterion and abstention |
|---|---|---|
| `Variable` (A-DOM04) | `DatasetResource containsVariable Variable` (C-D16) | The text explicitly identifies a measurable variable contained in or represented by the resource; topic-only mentions are insufficient. |
| `Measurement` (A-D12) — bounded Step 11 activation | `DatasetResource hasMeasurement Measurement` (C-D17) | README documents a specific observation/measurement with individuating context, e.g., observable and value/unit or an explicit observation identifier/conditions. A mere variable list is not a measurement. `E` status permits zero yield. |
| `Tool` (A-DOM02) | `usesTool` (C-D18) or `mentionsTool` (C-D24) | Distinguish actual tool use from incidental mention; a link alone is not use. |
| Concrete `ComputationalModel` subtype (A-DOM03a–e) | `usesModel` (C-D25) or `mentionsModel` (C-D26) | Establish specific model role and subtype; never mint an abstract `ComputationalModel` as a fallback. |
| `Workflow` (A-C11) | `explainsWorkflow` (C-D22) | Substantive scientific/data-processing sequence, not a directory list or incidental install steps. |
| Exact `Repository` (A-C01) endpoint or admissible source-scoped stub | `DatasetResource generatedBy Repository` (D-17) | Explicit dataset-generation provenance with an identifiable implementation repository, not an unrelated repository citation. |

**Exclusions:** `DataService` (A-D13) and `servesDataset` (C-D29) remain inactive; no inferred generation provenance, exhaustive README URL parsing, or new geographic-identifier coverage.

## 4. GitHub semantic profile — source acquisition, admissibility, and targets

**Accepted availability facts:** 51 repositories, 11,702 inventoried files, 499 `downloaded:true`; all 499 files were confirmed locally present in a read-only file-availability check. Those numbers do not prescribe the number of semantic input units or provider calls.

### 4.1 Two evidence channels and README nonduplication

1. **Phase A representation:** use `repos[].readme.text` for the **one** README whose exact repository-relative path is `repos[].readme.source_path`, when both are present. Its location is that original file at the repo's `frozen_commit_sha`, not a fabricated JSON page URL.
2. **Already downloaded descriptive files:** inspect only entries in `repos[].files.downloaded[]` where `downloaded=true`. Resolve their original case-sensitive `path` below `data/raw/coderepos/{repo_name}/contents/`; reject absolute paths, traversal (`..`), or path escapes. Preserve `selection_reason`, `file_role`, extension, original relative path, repository identity, and `archive.frozen_commit_sha`.
3. **No double-read:** if a manifest path equals `readme.source_path` and `readme.text` is available, do not read the corresponding raw file as a second semantic unit. Distinct additional README files remain eligible. Suppress duplicate semantic assertions within a repository even when supported by different files, while preserving their distinct citations.
4. A `downloaded:false` entry has **no eligible text** and is not treated as a failed download. By contrast, when `files.downloaded[]` declares `downloaded=true`, a missing, unreadable, or integrity-inconsistent raw source is `failed_source_or_evidence_binding` with the specific diagnostic required by §2.3, **never** `abstained_no_evidence`. Do not reacquire content or infer it from `files.inventory[]`.

### 4.2 Eligibility must use selection reason + extension + path + content (not `file_role` alone)

**Gate A — authoritative download:** `downloaded` must be true and `selection_reason` must be a non-null accepted acquisition reason: `allowed_exact_filename`, `allowed_path_prefix`, `allowed_semantic_folder`, `allowed_top_level_doc`, or `allowed_top_level_notebook`. An unrecognized reason is recorded for review rather than silently treated as eligible. These values describe why a file was acquired, **not** whether its entire content is appropriate for an LLM.

**Gate B — safe and relevant file type:** Eligible *textual prose* formats are `.md`, `.markdown`, `.rst`, and `.txt`, plus extensionless original README/CITATION-type filenames **when verified to contain readable descriptive text**. `.ipynb` is eligible **only for Markdown cells**. The extension is matched case-insensitively for eligibility; the original case-sensitive path remains the identity/evidence path. Structured `.cff` may supply already available Phase A/B metadata context; distinct explicit descriptive prose may be considered only without duplicating accepted structured assertions. `.py`, `.toml`, `.cfg`, `.yml`, `.yaml`, `.lock`, and source-code cells are **not** semantic prose inputs under this contract.

**Gate C — semantic context, including `other`:** Use `selection_reason`, repository-relative directories, filename, and text type together. README, technical documentation, workshop/tutorial/example Markdown, and explanatory passages in citation files are eligible whether their derived `file_role` is `readme`, `documentation`, `example`, `citation_md`, **or `other`**. In particular, `.md`/`.markdown`/`.rst`/`.txt` files acquired through `allowed_path_prefix` (e.g., `workshops/`, `workshop/`, `notebooks/`) or `allowed_semantic_folder` (e.g., nested tutorial/workflow folders) must not be dropped because `derive_file_role()` mapped them to `other`. Exclude administrative or machine-oriented files based on actual path/name/content purpose even if they happen to use `.md`.

**Gate D — actual admissible passage:** Use the source's descriptive scientific/software prose, not the whole document merely because it passed Gates A–C. Do not ask the LLM to infer runtime behavior from code, configuration, badges, dependency declarations, repository topics, or hyperlinks. Noninformative/administrative documents may legitimately yield no eligible semantic unit. These are extraction-time gating rules, **not** a request to audit or pre-read the 499 files before Step 12.

| Source group or derived `file_role` | Decision and boundary |
|---|---|
| `readme` | Read textual README once using Phase A where available; other selected READMEs are eligible. `.md`, `.markdown`, `.rst`, `.txt`, or verified extensionless README. |
| `documentation`, `example`, and descriptive `other` | Admit `.md`, `.markdown`, `.rst`, `.txt` from relevant paths when they contain genuine technical/scientific explanations, including `workshop[s]/` and semantically signaled nested folders. No inference from adjacent scripts. |
| `notebook` (`.ipynb`) | Parse the downloaded notebook JSON solely to expose `cell_type="markdown"` cell `source`; preserve original zero-based cell index and exact text. Do not expose, parse semantically, or execute code cells or outputs. |
| `citation_md` | Include `CITATION.md`, **`CITATION.txt`**, or verified extensionless `CITATION` when present in the accepted downloaded manifest. Extract relevant *prose* only; do not re-mint DOI, author, or citation assertions already materialized deterministically. |
| `citation_cff` | Reuse existing structured parsing; separate descriptive declarations only if genuinely new and verbatim-grounded. No broad re-parsing of structured metadata. |
| `changelog` | Only explicit, traceable software/model version statements and semantically relevant descriptive changes, not all release bookkeeping. |
| `contributing` | Only substantive scientific/operational procedure explanations; exclude participation and project-administration instructions. |
| `dependency_manifest`, `environment_manifest`, `license`, `security`, `code_of_conduct`, `source`, and non-descriptive `other` | Exclude from LLM text extraction. Existing deterministic metadata may remain context. Derived role is advisory, not the sole selector. |

**Acquisition/Phase A distinction:** `notebooks/exploration/coderepos/GitHubCIROHRepos.ipynb::classify_selection_reason()` may download text from a semantically meaningful folder, while `src/preprocessing/build_github_corpus.py::derive_file_role()` can classify the same path as `other`. This prospective LLM rule reconciles the two without modifying either program. Support for `.markdown` or `CITATION.txt` is a rule for *already acquired files*, not a claim that either extension occurred in the current 499-file inventory.

### 4.3 GitHub source units and provenance

- Canonical source identity: accepted repository node or `repo_id` + `full_name` + `archive.frozen_commit_sha` + **unchanged** repository-relative `path`. Use the SHA-pinned GitHub `/blob/{sha}/{path}` URL as public file evidence when supported. Internal `contents/` paths are lineage, not the primary public citation. Bind original quotation coordinates to the *actual* authority text specified in §2.3; preserve the authority-text SHA-256 and, for raw files, the file-byte SHA-256.
- A prose file may yield stable units by heading/section and original line offsets; a notebook yields units from original Markdown cells, identified by **zero-based cell index**, with an optional inner heading/offset. Preserve notebook Markdown exactly; no output/result screenshots or runtime inspection.
- Source-specific adapters may resolve existing Phase A fields and read the accepted raw paths; do **not** create a new shared ingestion framework, alter Phase A's consolidated schema, or use an unpinned GitHub URL as the evidence authority.
- Duplicate suppression uses source file identity for duplicate reads and existing node/edge IDs for duplicate assertions. Textually similar files at distinct paths are not assumed to be the same provenance source.

### 4.4 GitHub semantic targets

| Entity (ontology ID) | Relation (inventory ID) | Positive criterion and abstention |
|---|---|---|
| `RepositoryPurpose` (A-C07) | `Repository hasPurpose RepositoryPurpose` (C-C07) | A statement attributable to the **repository's own purpose**, with quoted evidence; use controlled categories and materialization in §7, not heuristics from language/topics/dependencies. |
| `Tool` (A-DOM02) | `usesTool` (C-C11), `mentionsTool` (C-C22), or `Tool implementedBy Repository` (D-22) | Independently distinguish actual use, incidental mention, and explicit source/implementation provision. Reuse deterministically represented Tool/implementation if exact. |
| Concrete `ComputationalModel` subtype (A-DOM03a–e) | `usesModel` (C-C21), `mentionsModel` (C-C23), or `ComputationalModel implementedBy Repository` (D-22) | Evidence of model's specific role and admissible concrete subtype; use is not implementation. |
| Identifiable `DatasetResource` (A-D01) | `usesDataset` (C-C15) | Explicit dataset use with identifiable endpoint; URL presence alone is only reference evidence. |
| `Workflow` (A-C11) | `explainsWorkflow` (C-C10) | Substantive scientific/technical processing sequence with discernible actions or dependencies. |
| `Function` (A-C08) — bounded Step 11 addition | `describesFunction` (C-C08) | A named function **described in prose**; no symbol-only extraction or code interpretation. |
| `Algorithm` (A-DOM13) — bounded Step 11 addition | `describesAlgorithm` (C-C20) | An algorithm explicitly identified and characterized in human-authored text; distinguish Algorithm from Method/Model. |
| `ModelVersion` (A-C10) — bounded Step 11 addition | `Repository hasModelVersion ModelVersion` (C-C09) | A concrete, source-quoted version declaration for **the software/model product provided by the source repository itself**, absent from accepted deterministic assertions. Do **not** mint a repository ModelVersion from a third-party dependency version, runtime/framework version, version of a separately referenced upstream product, or a mere filename. A version declaration does not establish execution/use. |
| Existing accepted `Method` (A-P13) endpoint | `implementsMethod` (C-C16) — **conditional** | Both explicit implementation evidence and a valid, traceable Publication-`Method` endpoint are required. Preserve unresolvable proposals outside the accepted KG; see §6. |

**Excluded here:** generic README DOI/GitHub reference enrichment already deferred; fork parent guessed from prose; `implementsMethod` from mere technique use; AST/import/function analysis; general parameters/metrics/concepts mined because the ontology permits them; ambiguous software archives inferred by name. Reference-enrichment edges already accepted remain untouched.

## 5. CIROH Hub semantic profile and visible MDX contract

### 5.1 Source authority, visible text, and unit boundaries

1. **Authoritative text:** `pages[].content_mdx` in `data/interim/documents/ciroh_hub_corpus.json` contains the complete materialized Markdown/MDX **body**, after front-matter removal and normalized line endings. It is not a file path or a newly downloaded resource. Keep original `canonical_url`, `page_key`, `corpus_path`, `source_path`, `generated_from_js`, `content_sha256`, and (where relevant) `file_sha256`. Do not re-read/re-scrape raw source or execute JavaScript/MDX.
2. **Visible semantic regions:** Headings, visible paragraph/list/table text, literal textual labels and explanation inside static Markdown/MDX admonitions/components, and contextually relevant fenced blocks *as displayed examples* are eligible. Never infer execution behavior from code. Markdown link **text** may be context, but URL/anchor presence alone does not substantiate `describes`, `uses`, `hasProcedure`, or implementation.
3. **Non-visible or unreliable regions:** Do not use HTML comments (`<!-- ... -->`), MDX/JSX comments (`{/* ... */}`), JavaScript expressions, script/runtime logic, generated-but-unmaterialized component contents, hidden navigation/configuration scaffolding, or hypothetical outputs of interactive components as evidence. For unknown component visibility, abstain rather than implement an MDX renderer. Static component text already materialized in `content_mdx` may be read, but raw component names/props alone do not establish domain semantics.
4. **Fenced code blocks:** Their literal visible text may support an explicitly identified `Example` under an accepted `Procedure`/`Step`, with evidence tied to a source span. Do not parse code to discover tools, methods, parameters, actions, outputs, or scientific results. For a `Parameter`, require explanatory prose establishing parameter identity/role; an unexplained configuration key in a code block is not sufficient.
5. **Unit formation:** Prefer heading-defined segments using existing Phase A `headings` and exact Phase B `Section` IDs when available; otherwise use page-local source-line/offset bounds and nearby heading context. Units stay within a page. Preserve each exact span's line position in the **original `content_mdx`**, not in a stripped/pretty-rendered reconstruction. Do not invent Docusaurus anchor rules, assemble cross-page workflows, or infer absent component content.
6. **Evidence binding:** Store the source quote, page `canonical_url`, `page_key`, and the verified `content_sha256`/`authorityTextSha256` of the **exact `content_mdx` used**, plus the original MDX body line/span or accepted Section occurrence. The body string, not a visible-text mask or rendered view, is the coordinate authority; static visible text must be a literal span within it. `corpus_path` and `source_path` provide lineage; neither substitutes for the user-facing public page citation. Page type (`pageType`) gates likely unit relevance but never proves the meaning of a passage.

**Page eligibility:** Prioritize product-catalog, product-doc, service-doc, and guide material. A blog post, release note, news item or policy page may supply an allowed, substantive technical description, but its genre/link/announcement alone cannot establish product typing or an instructional workflow.

### 5.2 CIROH Hub semantic targets

| Entity (ontology ID) | Relation (inventory ID) | Positive criterion and abstention |
|---|---|---|
| Clearly typed `Tool` or concrete `ComputationalModel` subtype | `catalogs` (C-DC17); `hasComponent` (C-DC19) | Explicit product/catalog or genuine Tool/Model component hierarchy; do not coerce a dataset, training module, course, method, link, or page into Tool/Model. |
| `Tool`, `ComputationalModel`, exact `DatasetResource`, or supported `Method` | `describesTool` (C-DC07); `describesModel` (C-DC16); `describesDataset` (C-DC27); `describesMethod` (C-DC28) | Substantive explanation identifying the entity, not a bare navigation link or announcement. |
| Identifiable `Repository` | `Tool/Model implementedBy Repository` (D-22) | Explicit source-code/implementation relation; bare GitHub URL is insufficient. |
| `Procedure` (A-DC05) | `DocumentationPage hasProcedure Procedure` (C-DC20) | A coherent, substantive set of instructions with a supported task/goal, not any ordered list. |
| `Step` (A-DC06) | `Procedure hasStep Step` (C-DC10) | An identified action in an accepted procedure, with supported sequence/context. |
| `Workflow` (A-C11) | `DocumentationPage/Procedure explainsWorkflow Workflow` (C-DC09) | Meaningful scientific/processing workflow, not a single shell command or navigation sequence. |
| `Example` (A-DC08) — bounded Step 11 addition | `Procedure/Step hasExample Example` (C-DC12) | Substantive, identifiable example anchored to an **accepted** Procedure or Step; a verbatim displayed snippet/admonition is permissible, but code semantics are not inferred. |
| **`Parameter` (A-DOM12) — bounded procedural Step 11 addition** | **`Procedure/Step hasParameter Parameter` (C-DC11)** | **Only** where the Procedure/Step is already accepted (or becomes accepted in the same validated unit) **and** local prose explicitly identifies a parameter and its role/configuration meaning. Parameter's wording/value, when stated, must be quoted; do not invent defaults or values. Do not mine all configuration, API arguments, code blocks, page-level settings, or unrelated parameters. |

**Parent-dependent rule:** `Example` and procedural `Parameter` are **not general Hub discovery targets**. If the supporting Procedure/Step or its `hasProcedure`/`hasStep` parent relations fail validation, suppress or hold the dependent candidate rather than leaving a free-floating instructional node/edge in the accepted projection. Validated parent and dependent assertions each retain adequate, independently verifiable evidence. No inferred parameter from unlabeled YAML/JSON/code or a code snippet alone.

**Other exclusions:** No Hub DOI/citation parsing, all-topic ontology mining, live `DataService` activation, code execution, or speculative cross-page workflow synthesis.

## 6. Identity, endpoint resolution, and nonduplication

- **Source artifacts:** Reuse exact accepted Phase B artifact IDs using source identity plus appropriate frozen version. Do not create a second curated DatasetResource, Repository, or DocumentationPage to support a semantic extraction.
- **Occurrence semantics:** LLM-authored domain entities are source-local unless they reference an exact accepted endpoint. Existing exact stubs are used where the source-specific contract permits them. Shared controlled `RepositoryPurpose` nodes in §7 are an **explicit within-profile vocabulary exception**, not an authorization for cross-source entity alignment.
- **Duplicate suppression:** A semantic relation identical to an existing accepted predicate/endpoints must not be materialized again. A new positive semantic role may coexist with a weaker exact syntactic reference if independently evidenced, with its provenance retained. No silent upgrade of `referencesRepository`, `referencesDataset`, or Hub `references` to `uses`/`implementedBy`.
- **`implementsMethod` signature:** C-C16 is `Repository` or `Tool` → `Method` (A-P13). A-P13 is a **Publication scientific-discourse Method**, not a generic reusable Algorithm, Function, or GitHub-local free-text technique. Positive evidence must state that the source repository/tool *implements* the method; neither citation nor use of the method alone qualifies.
- **Valid Method endpoint gate:** Materialize C-C16 only when an eligible Method endpoint exists as a valid, accepted, traceable Publication `Method` occurrence under the applicable frozen Publication authority, and the claimed implementation linkage has sufficient evidence. A paper DOI, a matching method label, or a repository README by itself does **not** identify an individual accepted Method endpoint. Do not invent a canonical Method, promote a GitHub-local mention to A-P13, or perform cross-source fuzzy matching in Step 11/12/13.
- **Unresolved candidate record:** Where implementation is explicit but a valid Method endpoint/binding is unavailable, retain a **non-graph** unresolved proposal recording source repo/tool, exact quoted implementation language, method surface form, candidate publication identifier if explicit, source file/section/commit, the source authority hash, and failure reason (`publication_method_not_yet_produced`, `method_endpoint_missing`, `binding_unverified`, or `method_semantics_ambiguous`). The original proposal, model/provider provenance, and disposition must remain immutable. This is provenance for a later approved resolution operation, not an accepted C-C16 edge or a false negative by fiat.
- **When reconsideration becomes eligible:** Reconsideration is **not triggered merely by the completion of GitHub extraction**. It becomes eligible only **after full-corpus Publication semantic production in Step 13 is completed and its accepted A-P13 `Method` occurrences, IDs, source evidence, and versioned authority are available as a stable output**. That event permits a read-only endpoint-availability review of previously unresolved records; it does not itself accept any relationship or alter Publication outputs.
- **Who may resolve and materialize:** An unresolved C-C16 may be materialized **only by a separately approved Step 14 cross-artifact resolution/validation procedure**, using the preserved GitHub implementation quote and a uniquely identified, valid accepted A-P13 Publication `Method` endpoint supported by explicit publication/method linkage. A matching method name, generic algorithm label, shared DOI/Paper identifier without a Method occurrence binding, or fuzzy similarity is insufficient. Ambiguous, missing, contradictory, or multiply plausible bindings remain non-graph unresolved records. Preserve the original extraction decision and separately record any later Step 14 decision/provenance; do not silently backfill Step 12/13 outputs or invent a GitHub-local A-P13 node.
- **D-26 and superclass derivation:** Both remain pipeline-governed, not model-authored fallbacks. Subclass/superproperty assertions are not separately model-predicted simply because valid semantic nodes/edges are accepted.

## 7. Controlled `RepositoryPurpose`: exact representation policy

**Authority and separation:** `RepositoryPurpose` (A-C07) and `Repository hasPurpose RepositoryPurpose` (C-C07) are existing v0.1.6 declarations. The following **six shared ABox instances are deterministically seeded from a versioned controlled vocabulary**, independently of whether any repository receives a purpose assertion. The **LLM may propose only a repository-to-category assignment**, not the category nodes; each accepted C-C07 edge separately requires a literal repository-specific purpose statement. These are not six OWL subclasses or a new TBox scheme.

| Stable category key | Label | Repository-level positive meaning |
|---|---|---|
| `model_implementation` | Model implementation | Implements or develops a computational model as a repository purpose |
| `data_processing` | Data processing | Prepares, transforms, processes, or analyzes scientific data |
| `scientific_experimentation` | Scientific experimentation | Supports simulations, experiments, calibration, or evaluation as a central repository purpose |
| `workflow_orchestration` | Workflow orchestration | Coordinates multi-stage scientific computation or data-processing workflows |
| `software_infrastructure` | Software infrastructure | Provides a software library, interface, runtime, or reusable infrastructure |
| `tutorial_demonstration` | Tutorial / demonstration | Exists principally to explain, teach, or demonstrate a technical or scientific task |

**Controlled-instance identity and provenance (proposed for the Step 11 freeze):** Declare `purposeSchemeID = "ciroh-repository-purpose"` and immutable `purposeSchemeVersion = "1.0.0"`. For each of the six exact category keys in the table, seed **exactly one** `RepositoryPurpose` (A-C07) node, with stable `nodeID = "repo-purpose:1.0.0:" + category_key`, `schemeID`, `schemeVersion`, `categoryKey`, `label`, and the approved table definition. Reject unknown category keys; do not produce per-repository copies. These six IDs are the complete v1.0.0 scheme and remain unchanged across runs under this contract; a future substantive vocabulary edit needs a separately approved new scheme version, not an in-place mutation. The six seed nodes have **contract/scheme provenance** and `extractionMethod = controlled_vocabulary_seed`, not fabricated per-repository `evidenceText` or LLM-discovery status. Step 12 must verify that the ID namespace does not collide with existing node identities. Vocabulary reuse is *within this GitHub purpose scheme* and is not cross-artifact entity alignment.

**Relation and provenance:** For each eligible repository and one of the six seeded category node IDs, create **at most one** accepted C-C07 `hasPurpose` edge **only after** a repository-specific statement has been accepted under the semantic-evidence contract. The edge must retain that repository's *own* verbatim purpose quote, source path/section/offset, pinned commit, `authorityTextSha256`, candidate/validator authority, and exact source and target IDs; multiple corroborating quotes attach as multiple evidence references, not duplicate edges. Seeding the six category nodes is **not evidence** that any repository belongs to a category. Do not attach repository-specific quotes as globally shared category-node attributes.

**Category decision:** The quoted passage must explicitly characterize the **repository's own purpose**, not merely the purpose of a referenced external tool or a single incidental example. `README` purpose statements are preferred, but an eligible descriptive file may serve if its subject is unambiguously the repository. Use one or more of the six categories only when the wording supports each assignment. Neither name, repository language, topics, file composition, dependencies, DOI links, nor a category-specific keyword alone suffices.

**No admissible classification:**

- **No purpose statement:** abstain (`abstained_no_evidence`); do not create a purpose node/edge on behalf of this repository.
- **Explicit purpose statement but no fitting category:** retain a quoted `unclassified_purpose` diagnostic/candidate with the source location and reason **outside the accepted KG**. Do not introduce an `other`/`unknown` category or a misleading C-C07 edge.
- **Conflicting or genuinely ambiguous categories:** preserve the statement and mark `abstained_ambiguous_semantics` (or an unresolved category diagnostic); do not guess. Multiple categories are allowed only if each has independently adequate support.

This v0.3 candidate proposes the **exact six category keys, scheme ID/version, and stable node-ID format** for final researcher approval. They are not yet frozen or materialized. No SKOS node/property or ontology modification is required.

## 8. Ontology-coverage and explicitly inactive scope

- Ontology **v0.1.6** is the prospective class/relation authority for HydroShare, GitHub and Hub. Abstract `SoftwareEntity`, `ComputationalModel`, `Place`, and `HydrologicFeature` are **not generic prediction fallbacks**; authorized concrete class typing and reasoned/pipeline superclass derivation govern them.
- Publication extraction/evaluation authorities **v0.1.5 + schema v0.1.3** already include `AgentBasedModel`, prose `Organization`, and `C-P34 hasComponent` via the accepted successor; do not reopen or silently reinterpret those evaluations.
- `Measurement` is activated only for explicit HydroShare README measurements (not data-file measurements); E status and zero accepted instances are compatible with full design coverage.
- `Function`, `Algorithm`, and new prose-only `ModelVersion` instances are authorized GitHub targets, with C-C16 `implementsMethod` strictly dependent on a validated Publication Method endpoint.
- `Example` and **procedural `Parameter`** are authorized **only** under accepted Hub Procedure/Step contexts. Generic Hub parameter and example mining remains inactive.
- `RepositoryPurpose` uses exactly six deterministically seeded, versioned shared ABox nodes; only repository-specific `hasPurpose` edge candidates are LLM-authored and require repository prose evidence. Never guess membership from repository metadata or source links.
- `DataService` and `servesDataset` remain **inactive**, despite heuristic HydroShare `data_services`; extension-derived serviceability is not published service evidence.
- Publication `Award` (A-D09) is still documented as a source-specific deterministic-gap/out-of-scope target in its v0.1.5 profile. Whether a separate prospective Publication treatment is warranted before full-corpus production belongs outside these Step 11 three-source semantic contracts and must preserve accepted Steps 7–9.
- A class that yields zero accepted instances differs from one omitted by design. Record `attempted_no_admissible_evidence`, `not_attempted_authorized_exclusion`, `pipeline_derived`, and unresolved outcomes distinctly.

## 9. Focused readiness criteria for a later Step 12 (NOT executed)

1. Validate approved IDs, domain/range, and exclusions against frozen ontology v0.1.6: no direct abstract predictions and no model-authored D-26.
2. Verify GitHub gating using **downloaded + selection_reason + extension + relative path + content kind**, including a downloaded `.md`/`.markdown` file under `workshops/` with derived `file_role=other`, eligible `CITATION.txt`, exclusion of `.py` under examples, malformed/unsafe paths, and missing/unrecognized source metadata. These are targeted contract checks, not a second 499-file audit.
3. Verify that the README mirrored in `readme.text` is not consumed twice, additional READMEs retain individual paths, and notebook JSON exposes **Markdown cells only** with preserved zero-based indices and original text. No cell execution or code interpretation.
4. Verify Hub `content_mdx` source-line/offset anchoring, visible static prose versus comments/dynamic expressions, literal displayed-example handling, and rejection of parameters derived only from configuration/code or unattached to an accepted Procedure/Step.
5. Verify deterministic seeding of exactly six `RepositoryPurpose` instance IDs under `ciroh-repository-purpose/1.0.0`, separate from evidence-backed C-C07 edges; no unsupported `other` key, per-repository duplicate category nodes, implicit memberships, or duplicate-edge emissions.
6. Verify C-C16 positive implementation with a valid Publication A-P13 endpoint versus immutable unresolved/nonmaterialized evidence-backed candidates; confirm that no re-evaluation is eligible before accepted full-corpus Publications production and that any later accepted resolution is Step 14-governed, source-grounded, and non-retroactive.
7. Verify `abstained_no_evidence` only after successful source-read/integrity checks; when `downloaded=true`, missing/unreadable/hash-failed files produce explicit source-failure diagnostics, not absence claims. Check hashes and exact quote coordinates for Phase A README, additional downloaded prose, notebook Markdown cells, HydroShare text, and Hub `content_mdx`. Verify `ModelVersion` refers only to the source repository's own software/model product, not dependency versions. Preserve authentic raw provider outputs when execution is **separately** authorized. No automatic corpus-wide audit, reasoner rerun, full suite, provider call, graph rebuild, or historical contract mutation is a Step 11 requirement.

## 10. Freeze boundary and review decisions

**Status remains FINAL-APPROVAL REVIEW CANDIDATE v0.3 — NOT FROZEN. No repository commit, freezing action, extractor implementation, or Codex prompt is authorized by this document.** It incorporates only the three narrowly requested clarifications to v0.2. The exact text requires final researcher approval before any binding freeze.

Reviewer should confirm that:

1. The **role-independent but content-aware GitHub eligibility policy** in §4 admits legitimate descriptive `other` files, `.markdown` and `CITATION.txt`, without admitting code or authorizing new acquisition.
2. Hub `Parameter` is allowed **only** via C-DC11 on a validated Procedure/Step; `Example` is comparably parent-dependent (§5).
3. Exactly six controlled, `ciroh-repository-purpose/1.0.0`-versioned `RepositoryPurpose` nodes are deterministically seeded and reusable regardless of repository membership; only individual C-C07 `hasPurpose` edges require repository-specific literal evidence. Unclassified purposes do not become fabricated edges or categories (§7).
4. C-C16 `implementsMethod` needs a **valid Publication-discourse A-P13 Method endpoint** and direct implementation evidence; unresolved proposals remain immutable and outside the accepted graph until a separately approved Step 14 resolution after full-corpus Publications production (§6).
5. Markdown/MDX units, actual authoritative text and hashes, static visible MDX content, literal source coordinates, and source-read failure dispositions are reproducible without a new shared pipeline framework; GitHub `ModelVersion` refers only to the repository's own software/model (§2, §4, §5).
6. The bounded family matrices and documented exclusions (§3–§8) accurately express the intended prospective scope without reauditing ontology coverage or altering frozen deterministic/Publications authorities.

Only after an explicit researcher approval may these candidate contracts be marked binding. Step 12 implementation and any provider execution require **separate** authorization.

## Appendix A. v0.1 → v0.2 review delta (informational)

| Area | Change |
|---|---|
| GitHub downloaded prose | Replace `file_role`-only exclusions with a conjunction of `downloaded`, `selection_reason`, extension, path, and text admissibility; expressly permit semantically relevant `other`. |
| Supported file types | Add `.markdown`, `CITATION.txt`, and eligible downloaded documentation/workshop/nested semantic-folder text, without extra acquisition. |
| README/notebook | Clarify `readme.text` dedup by original path; preserve Markdown-only cell index/quote; no source-code extraction. |
| Hub `Parameter` | Activate bounded A-DOM12/C-DC11 when Procedure/Step parent and distinct text evidence are accepted. |
| `RepositoryPurpose` | Six shared, version-keyed class instances with separate repository-specific `hasPurpose` evidence and explicit abstention/unclassified handling. |
| `implementsMethod` | Tie C-C16 to traceable accepted Publication A-P13 Method endpoints; preserve unresolved candidates outside accepted KG. |
| MDX and units | Specify authority of `content_mdx`, visible static content, comment/JS exclusion, line/offset binding, page heading anchors and minimal adaptation. |
| Frozen boundaries | No Phase A or deterministic contract edits; no v0.1.6 migration of Publication semantic history; no tests, model calls, or freeze here. |

## Appendix B. Read-only source references consulted for this draft

- Acquisition: `notebooks/exploration/coderepos/GitHubCIROHRepos.ipynb` (`classify_selection_reason`, selection reasons/path prefixes).
- GitHub Phase A: `src/preprocessing/build_github_corpus.py` (`derive_file_role`, `build_files`, `parse_readme`); `docs/github_preprocessing_phaseA.md`.
- CIROH Hub Phase A: `src/preprocessing/build_ciroh_hub_corpus.py` (`build_page_record`, `content_mdx`, `content_sha256`); `docs/ciroh_hub_preprocessing_phaseA.md`.
- Ontology v0.1.6: `src/ontology/ontology_spec.yaml`; `docs/ontology_inventory.md`; `docs/ontology_formalization.md` §12.
- Frozen source-specific mappings: `src/extraction/deterministic/{hydroshare,github,ciroh_hub}_extraction_mapping.md`.
- Publication successor: `docs/publication_llm_extraction_target_inventory_v0.1.5.md`; `src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml`; `docs/publication_canonical_semantic_pipeline_v1.0.md`.
- Preservation/closure: `docs/handoffs/STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md`; `docs/handoffs/STUDY2_HYDROSHARE_V016_ACCEPTANCE.md`; `docs/handoffs/STUDY2_REFERENCE_ENRICHMENT_V1_ACCEPTANCE.md`.

## Appendix C. v0.2 → v0.3 final-approval delta (informational)

| Requested clarification | Exact contract change |
|---|---|
| Controlled `RepositoryPurpose` | Six deterministic A-C07 seed nodes, `ciroh-repository-purpose/1.0.0`, exact `repo-purpose:1.0.0:{category_key}` identity; C-C07 edges remain distinct, model-proposed and quote-dependent; no inferred memberships or per-repository clones. |
| Unresolved `implementsMethod` | Preserve immutable non-KG proposals. Only after full-corpus Publication semantic production provides accepted A-P13 Method occurrences can candidates undergo read-only reconsideration; any edge materialization needs separate Step 14 approval and a uniquely justified endpoint binding. |
| Source integrity | Mandatory source-text hash and original file-byte hash when applicable, with unambiguous authority/coordinate rules for HydroShare, GitHub README/raw/notebook Markdown and Hub MDX. `downloaded=true` missing/unreadable/mismatched sources are recorded as technical failures, never no-evidence. |
| GitHub `ModelVersion` | C-C09 may reflect only the own software/model product of the repository; dependency, environment and referenced upstream versions do not qualify. |

**No other v0.2 semantic targets, source-eligibility gates, ontology declarations, frozen mappings, evaluation protocols, or implementation boundaries are changed in v0.3.**
