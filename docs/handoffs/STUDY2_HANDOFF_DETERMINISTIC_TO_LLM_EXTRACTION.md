# Study 2 Handoff: From Deterministic Extraction to LLM-Guided Extraction

**Project:** Multigranular KG-RAG for Operational Hydrology
**Repository:** `https://github.com/aarm1978/Multigranular_KG-RAG`
**Primary branch:** `main`
**Deterministic milestone commit:** `4f04001ff0d7791220990605c3db83fc858b006a`
**Context freeze date:** 2026-07-27
**Owner / doctoral researcher:** Abel Andrés Ramírez Molina

---

## 1. Purpose of this document

This document is the canonical handoff between:

1. the completed and frozen deterministic ABox phase plus the formally frozen ontology 0.1.2; and
2. the next phase: ontology-guided LLM extraction, cross-source alignment, graph assembly, and later KG-RAG evaluation.

Use it to begin a new ChatGPT thread without reconstructing the full history of the preceding conversation. It records the current frozen state, the decisions that should not be reopened without new evidence, the repository artifacts that contain the authoritative details, and the immediate next steps.

This file should be treated as a **context index**, not as a replacement for the repository documentation or source code.

---

## 2. Dissertation framing

The dissertation contains three connected studies:

- **Study 1:** Systematic review of knowledge graphs for academic papers.
- **Study 2:** Construction of an ontology and multigranular knowledge graph over heterogeneous CIROH scientific artifacts.
- **Study 3:** Construction and evaluation of a scientific workflow-aware KG-RAG system for cross-artifact question answering in operational hydrology.

The target artifact families are:

- HydroShare resources and datasets;
- GitHub repositories and source-code artifacts;
- CIROH Hub documentation; and
- scientific publications.

The final comparison design for Study 3 includes:

- Standard LLM without retrieval;
- Web-RAG;
- Vector-RAG;
- Microsoft GraphRAG; and
- the proposed multigranular KG-RAG system.

The same selected LLM should be used across comparable methods wherever methodologically possible.

---

## 3. Current milestone

The following components are complete and should be considered frozen for the present study snapshot:

| Component | Status |
|---|---|
| Conceptual ontology design | Complete |
| OWL/RDF formalization | Complete |
| Ontology version | `0.1.2` |
| Ontology structural validation | Complete |
| Ontology 0.1.2 reasoner validation | Complete: HermiT PASS; ELK profile-limited cross-check completed with warnings |
| Ontology 0.1.2 freeze | Complete |
| HydroShare deterministic preprocessing and extraction | Complete |
| GitHub deterministic preprocessing and extraction | Complete |
| CIROH Hub deterministic preprocessing and extraction | Complete |
| Publication deterministic preprocessing and extraction | Complete |
| Cumulative deterministic graph snapshots | Complete |
| Initial structural evaluation | Complete |
| File-inventory sensitivity analysis | Complete |
| LLM-guided extraction | Not started as a frozen implementation |
| Cross-source alignment and consolidation | Not started |
| Final graph assembly and loading | Not started |
| GraphRAG baseline | Not started |
| KG-RAG retrieval and QA evaluation | Not started |

The deterministic milestone was committed and pushed to `main` in:

```text
4f04001ff0d7791220990605c3db83fc858b006a
Finalize ontology and deterministic extraction
```

At the close of the preceding chat, a draft `README.md`, `LICENSE`, and
`THIRD_PARTY_NOTICES.md` had been prepared, but their commit and push had not yet been
confirmed. Check the repository before assuming they are published.

---

## 4. Current ontology review state

### 4.1 Version and artifact

- Ontology version: `0.1.2`
- Generated OWL artifact:
  `src/ontology/ciroh_ontology.owl`
- Ontology specification:
  `src/ontology/ontology_spec.yaml`
- Builder:
  `src/ontology/build_ontology.py`
- SHA-256:

```text
2857dc9f8e578367f6d2608da7e05d2ff5b2113fd41ff6c34047b90574b53ee7
```

### 4.2 Formalization counts

| Element | Count |
|---|---:|
| Source class declarations | 75 |
| Source relation declarations | 125 |
| Minted CIROH classes | 51 |
| Referenced external classes | 22 |
| Object properties | 90 |
| Datatype properties | 18 |
| Direct `owl:imports` | 6 |

### 4.3 Reasoner validation

Ontology 0.1.2 passed local structural validation and manual Protégé review:

- **HermiT: PASS** — ontology consistent; zero unsatisfiable named classes.
- **ELK: COMPLETED WITH PROFILE-INCOMPLETENESS WARNINGS** — classification completed
  without an execution error and zero named unsatisfiable classes were observed, but
  constructs outside OWL 2 EL prevent a guarantee of complete satisfiability or
  classification results for the full import closure. ELK is retained only as a
  profile-limited classification cross-check, not a full independent consistency
  validation.

Ontology 0.1.2 is formally frozen at the validated SHA-256 above. The following record
is historical and applies only to ontology 0.1.1.

Ontology `0.1.1` was manually validated in Protégé on 2026-07-23.

**HermiT 1.4.3.456**

- classification completed without reporting inconsistency;
- zero named classes were inferred under `owl:Nothing`;
- the complete locally resolved import closure was loaded;
- P-Plan was resolved through `src/ontology/catalog-v001.xml` to
  `src/ontology/imports/p-plan.owl`.

**ELK 0.6.0**

- classification completed without reporting inconsistency;
- zero named classes were inferred under `owl:Nothing`;
- ELK is treated as a supporting cross-check, not as fully independent confirmation
  across the ontology's complete expressivity.

### 4.4 Important modeling boundaries

Do not silently change these decisions:

- The ontology is specification-driven and generated, not manually authored as the
  primary source of truth.
- External classes may be used directly rather than wrapped in redundant CIROH classes.
- Property-to-class reuse anchors are represented as non-logical alignment annotations.
- Same-named relations may be formally merged through union domains and ranges.
- Evidence policy is declared in the TBox but fully enforced in the extraction pipeline
  and ABox.
- Edge-level evidence belongs to the property-graph representation, not to plain OWL
  triples without reification.
- Reverse traversal does not justify minting inverse properties for every relation.
- The deterministic ABox backbone and ontology 0.1.2 are complete and formally frozen.

Authoritative documentation:

- `docs/ontology_v0.1.md`
- `docs/ontology_inventory.md`
- `docs/ontology_formalization.md`
- `docs/decisions_and_coverage.md`, when present in the working documentation set
- `src/ontology/ontology_spec.yaml`

---

## 5. Deterministic extraction state

### 5.1 Separation of phases

The implemented pipeline distinguishes:

- **Phase A — deterministic preprocessing:** source-specific parsing, normalization,
  inventory construction, and preservation of raw provenance.
- **Phase B — deterministic extraction:** frozen ontology-aligned construction of nodes,
  edges, attributes, identifiers, evidence, warnings, deferred records, and skips.

Deterministic extraction must remain separate from LLM inference. The LLM phase should
add only information that cannot be reliably derived through deterministic rules.

### 5.2 Module status

| Module | Nodes | Edges | Status |
|---|---:|---:|---|
| HydroShare | 1,288 | 1,613 | Frozen |
| GitHub | 12,708 | 12,670 | Frozen |
| CIROH Hub | 4,667 | 6,553 | Frozen |
| Publications | 9,656 | 11,772 | Frozen |
| **Cumulative** | **28,319** | **32,608** | Frozen pre-alignment snapshot |

Publication graph artifact:

```text
data/interim/papers/publication_nodes_edges.json
```

Publication artifact SHA-256:

```text
675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf
```

Large generated artifacts under `data/interim/` are generally ignored by Git and must
not be assumed to be available from the repository clone.

### 5.3 Authoritative implementation records

**GitHub**

- `docs/github_preprocessing_phaseA.md`
- `docs/github_extraction_phaseB.md`
- `src/extraction/deterministic/github_extraction_mapping.md`
- `src/preprocessing/build_github_corpus.py`
- `src/extraction/deterministic/extract_github.py`

**CIROH Hub**

- `docs/ciroh_hub_preprocessing_phaseA.md`
- `docs/ciroh_hub_extraction_phaseB.md`
- `src/extraction/deterministic/ciroh_hub_extraction_mapping.md`
- `src/preprocessing/build_ciroh_hub_corpus.py`
- `src/extraction/deterministic/extract_ciroh_hub.py`

**Publications**

- `docs/publication_preprocessing_phaseA.md`
- `docs/publication_extraction_phaseB.md`
- `src/extraction/deterministic/publication_extraction_mapping.md`
- `src/preprocessing/build_publication_corpus.py`
- `src/extraction/deterministic/extract_publication.py`
- `data/curation/papers/publication_curation_overrides.yaml`

**HydroShare**

HydroShare deterministic extraction predates the latest milestone and remains the
first frozen module. Use its existing extraction mapping, extractor, tests, and graph
artifact as the authoritative record.

---

## 6. Structural evaluation state

The cumulative deterministic trajectory is a **pre-alignment** representation. It
concatenates module outputs without semantic deduplication across sources.

### 6.1 Cumulative trajectory

| Construction point | Full nodes | Full edges | File-inventory-excluded nodes | File-inventory-excluded edges |
|---|---:|---:|---:|---:|
| HydroShare | 1,288 | 1,613 | 531 | 856 |
| + GitHub | 13,996 | 14,283 | 1,537 | 1,824 |
| + CIROH Hub | 18,663 | 20,836 | 5,962 | 7,893 |
| + Publications | 28,319 | 32,608 | 15,618 | 19,665 |

### 6.2 Evaluation policy

The evaluation record uses:

- schema version `1.2`;
- evaluator version `1.2.0`;
- a `full` graph variant; and
- a `fileInventoryExcluded` / `file_inventory_excluded` sensitivity variant.

The excluded ontology classes are:

```text
DatasetFile
File
RepoFile
```

The filter is class-based and removes edges through excluded endpoints.

### 6.3 Interpretation constraints

These methodological decisions are frozen:

- The **full graph** is the primary representation of the actual research product.
- The file-inventory-excluded view is a supporting granularity sensitivity analysis.
- The sensitivity view was introduced after the deterministic trajectory revealed the
  effect of explicit per-file representation.
- Its policy was frozen before generating the GraphRAG baseline and conducting the
  external comparison.
- The formal external schema-agnostic comparison must be:
  **GraphRAG full vs. Multigranular KG full**.
- GraphRAG full may be shown as contextual reference beside the Multigranular KG
  sensitivity result.
- Do not claim or apply symmetric GraphRAG filtering unless a common cross-schema
  identification protocol is explicitly defined and frozen.

Authoritative records:

- `docs/evaluation_decisions.md`
- `results/metrics/trajectory.md`
- `src/evaluation/build_cumulative_snapshot.py`
- `src/evaluation/compute_structural_metrics.py`

---

## 7. Validation state

The completed implementation was validated through focused and full test runs.

Most recent reported compatible-environment full-suite result:

```text
244 passed, 1 skipped, 102 subtests
```

Additional checks included:

- byte-identical repeated outputs;
- frozen-snapshot validation;
- deterministic artifact hashing;
- schema migration checks;
- ontology structural checks;
- `git diff --check`.

A default Python 3.9 environment previously failed test collection because of missing
dependencies and newer syntax. This was an environment mismatch, not a reason to
change the validated implementation. Use the compatible project environment documented
in the repository.

---

## 8. Next phase: ontology-guided LLM extraction

### 8.1 Objective

Use an LLM only for entities, relations, discourse structures, and semantic assertions
that cannot be obtained reliably from deterministic metadata or document structure.

The phase should preserve the project's central provenance principle:

> No supported evidence span means no accepted semantic assertion.

### 8.2 Work should begin with design, not immediate batch extraction

Before processing the full corpus, define and freeze:

1. **LLM extraction scope**
   - ontology classes and relations assigned to LLM extraction;
   - artifact types to which each target applies;
   - explicit exclusions and non-goals;
   - distinction between entity mention, candidate entity, and consolidated entity.

2. **Input units**
   - document, section, paragraph, chunk, code unit, README unit, or page;
   - stable source identifiers;
   - token-window and overlap policy;
   - treatment of tables, figures, equations, references, and code blocks.

3. **Output contract**
   - strict machine-readable schema;
   - ontology IDs and permitted values;
   - source and target references;
   - exact evidence quotations or bounded evidence spans;
   - source locations;
   - extraction method and model metadata;
   - confidence or abstention fields only when methodologically justified;
   - validation status and rejection reasons.

4. **Prompting protocol**
   - system and task prompts;
   - ontology definitions presented to the model;
   - positive and negative examples;
   - instructions to abstain rather than infer beyond evidence;
   - rules for ambiguity, aliases, and nested entities.

5. **Validation**
   - JSON/schema validation;
   - ontology domain/range validation;
   - evidence-span verification;
   - deduplication only within clearly defined boundaries;
   - automatic rejection and deferred-review categories;
   - no direct mutation of deterministic frozen outputs.

6. **Evaluation design**
   - stratified hand-annotated sample;
   - class- and relation-level precision, recall, and F1 where feasible;
   - evidence-grounding accuracy;
   - hallucination / unsupported-assertion rate;
   - schema-validity rate;
   - abstention behavior;
   - inter-annotator agreement for the human reference set;
   - model and prompt sensitivity analysis.

7. **Reproducibility**
   - model name and exact version;
   - provider and API configuration;
   - temperature and decoding parameters;
   - prompt and schema hashes;
   - request/response provenance;
   - retry and failure policy;
   - deterministic post-processing;
   - frozen input-corpus snapshot;
   - cost and token accounting.

### 8.3 Recommended implementation sequence

Completed prerequisites: ontology 0.1.2 source review, OWL regeneration and structural
tests, manual HermiT/ELK review, and the ontology 0.1.2 freeze.

1. Produce the ontology-guided LLM extraction target inventory and evidence/output
   contract before writing production extraction code.
2. Choose one artifact family for a small pilot.
3. Define the strict extraction schema and evidence contract.
4. Create a manually annotated validation sample.
5. Implement pilot extraction without entity consolidation.
6. Evaluate extraction quality and revise the protocol.
7. Freeze the protocol before full-corpus execution.
8. Run artifact-specific LLM extraction.
9. Preserve deterministic and LLM outputs as separate layers.
10. Design cross-source identity resolution and consolidation only after extraction
    quality is established.
11. Assemble the final multigranular graph.
12. Recompute intrinsic metrics after alignment and consolidation.
13. Begin retrieval and baseline comparisons for Study 3.

### 8.4 Suggested pilot

A publication pilot is a reasonable first candidate because:

- papers contain rich discourse and domain semantics;
- deterministic bibliographic and citation structure is already frozen;
- sections and evidence spans can be bounded clearly;
- manual annotation is easier to define than across heterogeneous repository files;
- the systematic-review background provides methodological grounding.

This is a recommendation, not a frozen decision. Compare it against a CIROH Hub pilot
before implementation if documentation-centered operational questions are the immediate
priority.

---

## 9. Decisions that should not be reopened casually

Do not revisit the following merely because a new chat starts:

- the formally frozen ontology 0.1.2 structure and mappings;
- deterministic module outputs;
- publication Phase A and Phase B frozen contracts;
- the distinction between deterministic and LLM extraction;
- the full-versus-file-inventory-excluded evaluation policy;
- the full-versus-full external baseline comparison;
- the use of explicit evidence and provenance;
- the decision to delay cross-source consolidation until after extraction;
- the decision not to commit large generated `data/interim/` artifacts;
- the move of Phase A and Phase B records into `docs/`.

A change requires new evidence, an explicit rationale, impact analysis, versioning, and
updated tests and documentation.

---

## 10. Repository and licensing note

The repository did not initially contain a top-level README or license.

A proposed first release included:

- `README.md`;
- `LICENSE` using the MIT License for original project code and documentation; and
- `THIRD_PARTY_NOTICES.md`.

The bundled local P-Plan ontology must retain its original third-party licensing and
must not be represented as relicensed under MIT.

Before relying on the licensing files, confirm:

- whether they were committed and pushed after commit `4f04001`;
- whether The University of Alabama, CIROH funding, employment, or collaboration terms
  affect copyright ownership;
- whether all bundled third-party materials have adequate notices.

---

## 11. Recommended project-file set

### 11.1 Persistent core context

Keep these files in the ChatGPT project as the persistent, current context:

1. **This handoff document**
   - `STUDY2_HANDOFF_DETERMINISTIC_TO_LLM_EXTRACTION.md`

2. **Current repository overview**
   - `README.md`

3. **Current dissertation design**
   - `Dissertation Research Design.docx`
   - update or replace it if it predates the final Study 2/Study 3 design.

4. **Ontology definition**
   - `ontology_v0.1.md`
   - `ontology_inventory.md`
   - `ontology_formalization.md`
   - `decisions_and_coverage.md`
   - `ontology_spec.yaml`

5. **Evaluation policy and current trajectory**
   - `evaluation_decisions.md`
   - `trajectory.md`

### 11.2 Background files worth retaining

These provide scholarly and historical framing and can remain:

- `Mapping_Scholarly_Knowledge__A_Systematic_Review_of_Knowledge_Graphs_for_Academic_Papers.pdf`
- `Dissertation_Papers_Initial Scope.pdf`
- `NRT Final Project Report.pdf`
- `CIROH_AI_Bot Abstract.pdf`
- `Dissertation Proposal AARM.pdf`

Treat the proposal and initial-scope documents as historical. When they conflict with
this handoff, the current repository documentation and this handoff take precedence.

### 11.3 File that should be replaced or clearly marked historical

The existing `Project Context.docx` may now be stale. Avoid keeping two competing
documents that both appear authoritative.

Preferred options:

- replace it with this handoff document; or
- rename it as historical context and state clearly that this Markdown handoff is the
  current source of truth.

### 11.4 Files to attach only when needed

Do not overload persistent project context with every script and long Phase A/Phase B
record. Attach the relevant files to the new thread when working on a specific module.

For LLM extraction design, likely on-demand attachments include:

- the target artifact's Phase A record;
- the target artifact's Phase B record;
- its deterministic extraction mapping;
- its current preprocessing and extraction scripts;
- representative input and output samples;
- the relevant tests;
- the proposed LLM extraction schema and prompt files as they are created.

---

## 12. How to begin the next ChatGPT thread

This document should be uploaded to the project **and** attached or explicitly referenced
in the first message of the new thread.

Project files provide durable background, but the opening message should still identify
the immediate task and the authoritative handoff. This reduces retrieval ambiguity and
prevents the new thread from treating older proposal documents as the current design.

Suggested opening message:

```text
I am beginning the ontology-guided LLM extraction phase of Study 2.

Use the attached
STUDY2_HANDOFF_DETERMINISTIC_TO_LLM_EXTRACTION.md
as the authoritative project handoff. The deterministic ABox backbone and ontology
0.1.2 are complete and formally frozen. Do not reopen those decisions unless new
evidence requires a versioned change.

For this thread, I want to design the LLM extraction methodology before implementing
the full pipeline. First, review the handoff and the attached current ontology files.
Then help me produce an explicit inventory of which ontology classes, relations, and
attributes still require LLM extraction, separated by artifact family and tied to
evidence requirements. Do not write production code until that inventory and the
output contract are methodologically agreed.
```

Recommended first deliverable in the new thread:

```text
LLM extraction target inventory:
- ontology item;
- artifact family;
- extraction unit;
- evidence requirement;
- deterministic information already available;
- LLM-added information;
- allowed output;
- abstention condition;
- validation rule;
- evaluation approach.
```

---

## 13. Authority order for future work

When sources conflict, use this order:

1. frozen repository artifacts and tests at or after the named milestone commit;
2. current ontology specification and formalization records;
3. this handoff document;
4. current dissertation research-design document;
5. earlier proposals, abstracts, reports, and initial-scope documents;
6. conversational recollection.

This order prevents older planning documents from overriding implemented and validated
decisions.

---

## 14. Immediate checklist for the next thread

- [ ] Confirm whether `README.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md` are on `main`.
- [ ] Upload this handoff to the ChatGPT project.
- [ ] Replace or mark the older `Project Context.docx` as historical.
- [ ] Upload the current ontology and evaluation files listed in Section 11.
- [x] Complete manual HermiT and ELK validation of ontology 0.1.2 in Protégé.
- [x] Freeze ontology 0.1.2 after the manual reasoner review.
- [ ] Start a new chat using the prompt in Section 12.
- [ ] Build the LLM target inventory before writing the extraction pipeline.
- [ ] Select and justify the first pilot artifact family.
- [ ] Define a strict output and evidence schema.
- [ ] Design the human-annotated evaluation sample.
- [ ] Freeze the pilot protocol before scaling to the full corpus.

---

## 15. Closing statement

The deterministic ABox backbone and ontology 0.1.2 are complete, formally frozen
dissertation milestones. The next authorized KG-construction activity is design of the
ontology-guided LLM extraction target inventory and evidence/output contract before
production extraction code.

The central methodological transition is:

```text
deterministic artifact structure
        +
evidence-grounded LLM semantic extraction
        +
explicit cross-source alignment
        =
final multigranular scientific knowledge graph
```

The immediate priority is not full-corpus generation. It is to define a defensible,
auditable, and reproducible LLM extraction contract that preserves the rigor already
established in the deterministic phase.
