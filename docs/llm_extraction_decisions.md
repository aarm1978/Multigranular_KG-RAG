# LLM Extraction Decisions

**Project:** Multigranular KG-RAG for Operational Hydrology
**Study:** Dissertation Study 2
**Document purpose:** Methodological decision record for ontology-guided LLM extraction
**Current ontology baseline:** 0.1.4, formally frozen
**Initial decision date:** 2026-07-28
**Status vocabulary:** `decided`, `deferred`, `pilot-dependent`

---

## 1. Purpose and authority

This document records the methodological and implementation decisions that govern the ontology-guided LLM extraction phase. It does not replace the ontology, the ontology inventory, the formalization record, the deterministic extraction mappings, or the frozen Phase B outputs.

The ontology defines the permitted classes, relations, domains, ranges, and extraction statuses. This document defines how LLM-based extraction will operate against that frozen ontology, how it will interact with the deterministic ABox backbone, how candidate outputs will be stored and adjudicated, and which unresolved decisions must be revisited before each artifact module is implemented.

When this document conflicts with the frozen ontology or deterministic extraction artifacts, the following authority order applies:

1. frozen ontology 0.1.4 specification and generated OWL;
2. frozen deterministic Phase B outputs and tests;
3. current ontology inventory and formalization records;
4. this LLM extraction decision record;
5. later pilot notes and implementation discussions.

Any change to a frozen ontology decision requires explicit evidence, impact analysis, versioning, updated tests, regeneration of the OWL artifact, and reasoner validation.

The current additive generic-mentions authority is represented by formally frozen ontology
0.1.4. Its authoritative HermiT gate completed successfully with consistency, zero
unsatisfiable named classes, and no execution errors.

For current and future Publication provider requests, `evidenceSpan.sectionTitle` is a
request-bound transport specialization: the provider-facing schema constrains it to the
exact typed `const` value of trusted `sourceUnit.sectionTitleRaw` before generation. This
does not normalize the raw title, repair provider output, weaken V4 exact validation, or
bind any other evidence field. The frozen candidate-output schema remains the semantic
envelope authority.

Ontology D-26 `ciroh:mentions` is not model-authored or independently annotated. It is
materialized deterministically only after semantic acceptance. Paper-to-entity fallback
requires valid entity evidence and unambiguous trusted Paper provenance. A discourse-to-
entity fallback additionally requires the same Paper, the same source unit, and **EXACT
COORDINATE CONTAINMENT** in both unit and document coordinates; boundary equality is
permitted. An accepted stronger-role or specialized `mentionsX` edge for the exact same
endpoint pair suppresses the redundant explicit generic edge.

The zero-call pre-live C1B replay is a `DEVELOPMENT_DIAGNOSTIC_REPLAY` and
`COUNTERFACTUAL_TRANSPORT_EMULATION`. It is not authentic new model output, gold,
formal evaluation, or formal acceptance. Its V12-usable-node projection validates only
deterministic D-26 mechanics. Because C1B exposed zero relation targets, the no-call
routed-relation development gate was completed before authorizing a fresh ten-unit
semantic run. It provides structural coverage for all 26 model-authorable Publication
relations and confirms one combined nodes-plus-eligible-relations request per DEV unit is
mechanically ready. No recorded provider run has yet exposed those relations end to end.

Candidate `relationScope` is derived from resolved endpoint artifact ownership, not fixed
from ontology relation `type`. Same-artifact endpoints require `intra_source`; distinct-
artifact endpoints require `inter_source`. Thus source-local DatasetMention and
provisional Repository candidates remain local without invented identity, while exact or
resolver-bound external endpoints retain the external path. V8 remains authoritative;
the provider schema preserves the frozen scope enum and performs no post-generation
repair.

---

## 2. Decision-record format

Each decision includes:

- **ID**
- **Question**
- **Options considered**
- **Current decision**
- **Rationale**
- **Ontology impact**
- **Output-contract impact**
- **Status**
- **Decision date**
- **Evidence that would justify revision**

---

# 3. Global decisions

## G-01 — Layered module outputs and data lifecycle

**Question.** What outputs should each module produce, and where should they be stored?

**Options considered.**

1. Rewrite the frozen deterministic `nodes_edges.json` file with LLM additions.
2. Produce only an LLM-specific `nodes_edges` file.
3. Preserve the deterministic baseline and create separate LLM candidate, adjudication, and augmented pre-consolidation outputs.
4. Promote validated LLM outputs directly to `data/processed`.

**Current decision.**

Each module will preserve its frozen deterministic Phase B output and produce separate LLM-layer artifacts under:

```text
data/interim/<module>/llm/
```

The logical output layers are:

1. **Frozen deterministic baseline**
   - existing `<module>_nodes_edges.json`;
   - immutable and never rewritten by the LLM pipeline.

2. **Source-preserving evidence units and run artifacts**
   - structural source units;
   - requests;
   - raw model responses;
   - parsed candidates;
   - validation results;
   - run metadata.

3. **LLM candidate layer**
   - proposed new nodes;
   - proposed new edges;
   - links to existing deterministic entities;
   - attribute enrichments;
   - semantic upgrades;
   - correction proposals;
   - deferred-record resolutions;
   - abstentions.

4. **Adjudication layer**
   - accepted;
   - rejected;
   - still deferred;
   - exact duplicate;
   - linked to existing;
   - semantic upgrade;
   - correction accepted;
   - correction rejected;
   - excluded from the augmented snapshot.

5. **Augmented pre-consolidation module snapshot**
   - frozen deterministic assertions;
   - accepted LLM additions;
   - accepted deferred resolutions;
   - accepted enrichments and semantic upgrades;
   - approved correction effects;
   - no inter-source consolidation.

Suggested artifacts include:

```text
data/interim/<module>/llm/evidence_units.jsonl
data/interim/<module>/llm/runs/<run_id>/requests.jsonl
data/interim/<module>/llm/runs/<run_id>/raw_responses.jsonl
data/interim/<module>/llm/runs/<run_id>/candidates.jsonl
data/interim/<module>/llm/runs/<run_id>/validation_results.jsonl
data/interim/<module>/llm/<module>_llm_candidates.json
data/interim/<module>/llm/<module>_llm_adjudication.json
data/interim/<module>/llm/<module>_augmented_nodes_edges.json
```

`data/processed` is reserved for outputs produced after inter-source alignment, inter-source consolidation, final graph assembly, and preparation for graph loading or evaluation.

**Rationale.**

This design preserves the deterministic baseline as an auditable dissertation milestone while allowing accepted LLM-supported knowledge to be assembled into a usable source-level representation. It also preserves raw model behavior, validation outcomes, and adjudication decisions for reproducibility.

**Ontology impact.**

None. This is a pipeline and data-lifecycle decision.

**Output-contract impact.**

The contract must distinguish raw candidates, validation outcomes, adjudication outcomes, and accepted augmented-graph records. Every accepted augmented record must retain provenance linking it to its deterministic or LLM origin.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

- operational evidence that the layered artifacts create unnecessary duplication without improving auditability;
- storage constraints that require a normalized event-log representation;
- a later graph-assembly design that can preserve the same provenance guarantees with fewer physical files.

---

## G-02 — Authority of the LLM over the deterministic baseline

**Question.** May the LLM modify, delete, or overwrite deterministic Phase B outputs?

**Options considered.**

1. Allow the LLM to rewrite deterministic records.
2. Allow the LLM to modify only records with low deterministic confidence.
3. Preserve Phase B and allow only additive or separately adjudicated correction proposals.

**Current decision.**

The LLM may not directly modify, delete, or overwrite any frozen Phase B output. It may produce the following controlled actions:

```text
add_node
add_edge
link_existing
enrich_existing
semantic_upgrade
propose_correction
resolve_deferred
```

A correction proposal must be adjudicated. If accepted, the deterministic baseline remains unchanged, while the augmented snapshot may mark the original assertion as superseded or excluded from the working graph.

**Rationale.**

The deterministic output is a frozen, reproducible milestone. Preserving it prevents hidden retrospective changes and permits direct comparison between deterministic-only and augmented representations.

**Ontology impact.**

None unless accepted correction patterns reveal a systematic ontology defect.

**Output-contract impact.**

Every candidate must carry an action type and may not imply direct mutation of the baseline. Correction proposals must reference the exact deterministic node, edge, attribute, warning, or deferred record being challenged.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Only a formal redesign of the dissertation’s reproducibility strategy or a versioned replacement of the deterministic milestone.

---

## G-03 — Treatment of deterministic deferred records

**Question.** Should LLM extraction operate only on records deferred by deterministic Phase B?

**Options considered.**

1. Limit the LLM to deferred records.
2. Ignore deferred records and perform unrestricted semantic extraction.
3. Treat deferred records as a priority channel while also permitting open semantic discovery over approved targets.

**Current decision.**

The LLM pipeline will have two complementary channels:

1. **Deferred-resolution channel**
   - deterministic deferred records are passed as explicit, prioritized tasks;
   - each receives a final disposition.

2. **Open semantic-discovery channel**
   - the LLM may identify ontology-supported entities and relations that were never emitted as deferred records.

Permitted deferred dispositions include:

```text
resolved_accepted
resolved_rejected
still_unresolved
insufficient_evidence
out_of_scope
```

**Rationale.**

Deferred records represent known unresolved cases, but deterministic extraction cannot enumerate every semantic assertion that it failed to identify. Restricting the LLM to deferred records would underestimate the ontology-guided semantic layer.

**Ontology impact.**

None.

**Output-contract impact.**

Candidate records must indicate whether they originated from open discovery or from a specific deferred record. Deferred resolutions must retain the original deferred identifier and reason.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot evidence showing that open discovery produces unmanageable false positives or that deferred-only extraction unexpectedly covers the approved LLM target inventory.

---

## G-04 — Source-preserving intermediate representation

**Question.** What common intermediate representation should be used across heterogeneous artifact modules?

**Options considered.**

1. Use full raw artifacts directly in every LLM request.
2. Generate LLM summaries and use those summaries as the exclusive source for subsequent extraction.
3. Create source-preserving structural evidence units that retain original text and location.
4. Use only the existing Phase A corpus JSON without additional unitization.

**Current decision.**

The LLM pipeline will use a **source-preserving intermediate representation** composed of structural evidence units. Each unit must retain the original source content and enough structure to verify and reproduce every accepted assertion.

A source unit should include, as applicable:

```text
artifact_id
artifact_type
artifact_version
source_unit_id
structural_path
section_title
content_type
source_location
original_text
text_hash
deterministic_node_refs
deterministic_edge_refs
applicable_deferred_refs
eligible_categories
eligible_ontology_targets
```

The representation may be derived from the frozen Phase A corpora but must not replace original content with an LLM-generated summary.

**Rationale.**

A source-preserving representation standardizes heterogeneous artifacts without introducing an irreversible semantic bottleneck. It supports evidence verification, bounded prompting, deterministic routing, and reproducible extraction.

**Ontology impact.**

None. Structural evidence units are pipeline artifacts, not new ontology classes unless later evidence justifies formalization.

**Output-contract impact.**

Every candidate node or edge must reference one or more source units and exact evidence spans from `original_text`.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot evidence that a different source unit is required for specific content types, such as tables, equations, notebook cells, product cards, or code blocks.

---

## G-05 — Ontology-native category routing

**Question.** How should categories be used in LLM extraction?

**Options considered.**

1. Create a new extraction taxonomy independent of the ontology.
2. Use categories as LLM-generated summaries that replace the source text.
3. Use the module-specific Table B categories in the ontology inventory as routing scaffolds.
4. Do not use categories.

**Current decision.**

The module-specific categories defined in the ontology inventory’s Table B sections will serve as routing scaffolds between source-preserving evidence units and eligible ontology targets.

Categories:

- guide attention;
- identify eligible target families;
- may route one unit to multiple target groups;
- do not replace the original source text;
- are not KG entities;
- do not limit extraction to a single summary or one category per unit;
- do not authorize targets outside the frozen ontology.

**Rationale.**

Using the ontology’s own extraction scaffolding preserves traceability between conceptual design and implementation and avoids maintaining a second, disconnected classification system.

**Ontology impact.**

None. The categories remain extraction scaffolds rather than OWL classes.

**Output-contract impact.**

Run metadata should record the category or categories used to route each source unit and the resulting eligible ontology targets.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot evidence that one or more categories are too broad, overlap in a way that harms precision, or fail to route source units containing approved ontology targets.

---

## G-06 — Intra-source extraction before inter-source integration

**Question.** How should the multigranular distinction between intra-source and inter-source representation govern the pipeline?

**Options considered.**

1. Perform source-level extraction and inter-source consolidation simultaneously.
2. Treat same-artifact-family connections as intra-source and cross-family connections as inter-source.
3. Define intra-source as representation within one individual source and inter-source as connections across distinct sources, regardless of artifact family.

**Current decision.**

LLM extraction is performed independently for each individual source and produces an evidence-grounded **intra-source representation** integrated with that source’s frozen deterministic backbone.

During this stage:

- mentions and candidates within the same source may be reconciled;
- deterministic and LLM assertions for the same source may be combined in the augmented source representation;
- candidate references to other sources may be recorded;
- definitive identity resolution and consolidation across distinct sources are not performed.

Any relation connecting two distinct source artifacts is **inter-source**, regardless of whether the artifacts belong to the same family or different families. Examples include:

```text
Paper A cites Paper B
Paper A uses Dataset B
Repository A references Publication B
Documentation Page A documents Repository B
```

Inter-source candidates may be discovered while processing the originating source, but final target alignment, identity resolution, and consolidation occur only after extraction quality has been evaluated and the extraction protocol has been frozen.

**Rationale.**

This preserves the dissertation’s two-level multigranular definition:

```text
intra-source = detailed representation within one source
inter-source = connections across distinct sources
```

**Ontology impact.**

None. The ontology already supports both relation scopes.

**Output-contract impact.**

Candidates must distinguish:

- intra-source nodes and relations;
- unresolved inter-source references;
- inter-source candidates with a deterministic target already known;
- inter-source candidates awaiting later alignment.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Only an explicit revision to the dissertation’s multigranular framing.

---

## G-07 — Evidence must be anchored to original source content

**Question.** What qualifies as evidence for an LLM-generated node or relation?

**Options considered.**

1. Accept an LLM-generated summary as evidence.
2. Accept unverified quotations.
3. Require exact, verifiable spans from the original source content.
4. Permit unsupported assertions when model confidence is high.

**Current decision.**

Every accepted LLM-generated semantic assertion must reference one or more verifiable evidence spans from the original source content. An LLM-generated paraphrase may be stored as a normalized description but never serves as evidence by itself.

The governing rule is:

> No supported evidence span means no accepted semantic assertion.

**Rationale.**

This implements the frozen provenance-first principle at the pipeline and ABox levels and permits independent verification of all LLM-supported knowledge.

**Ontology impact.**

None. The ontology already declares the evidence policy.

**Output-contract impact.**

Evidence references are mandatory for accepted candidates. The contract must support exact text, source-unit identifiers, location information, and span verification.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Only source types for which exact textual spans are impossible, requiring a separately defined evidence representation for structured tables, figures, or executable artifacts.

---

## G-08 — First pilot artifact family

**Question.** Which artifact family should be used for the first controlled LLM extraction pilot?

**Options considered.**

1. Scientific publications.
2. HydroShare resources.
3. GitHub repositories.
4. CIROH Hub documentation.
5. A mixed-source pilot.

**Current decision.**

The first pilot will use **scientific publications**.

**Rationale.**

Publications contain the richest ontology-guided semantic content, have frozen deterministic bibliographic structure, support section-aware evidence units, and allow controlled evaluation of:

- discourse entities;
- Method versus ComputationalModel versus Algorithm;
- use versus mention;
- Findings;
- EvaluationMetrics;
- Parameters;
- evidence grounding.

This pilot does not require immediate resolution of module-specific product-catalog, repository-version, or documentation-example decisions.

**Ontology impact.**

None.

**Output-contract impact.**

The first contract implementation must support publication discourse nodes, domain entities, intra-source relations, inter-source candidates, and exact textual evidence.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

A feasibility review showing that the publication corpus cannot preserve adequate structural locations or that another module offers substantially clearer annotation and evaluation conditions.

---

## G-09 — Criteria for reopening the ontology

**Question.** When may LLM extraction results justify a future ontology revision?

**Options considered.**

1. Modify the ontology whenever the model produces an unrecognized output.
2. Modify the ontology when prompting is difficult.
3. Require empirical pilot evidence of a genuine modeling gap.
4. Never modify a frozen ontology baseline.

**Current decision.**

No LLM result changes a frozen ontology automatically. The approved 0.1.3 pre-pilot
candidate followed the versioned gate process in this section. Any later update may be
proposed only when pilot evidence demonstrates one or more of the following:

- a necessary class is absent;
- a necessary relation is absent;
- an existing relation cannot be applied consistently;
- a domain or range is incorrect;
- two concepts must be divided or merged;
- an attribute is required to answer the approved competency questions;
- expert annotators cannot consistently apply a frozen distinction because of a schema problem rather than a prompting problem.

Any update requires:

- documented evidence;
- rationale;
- impact analysis;
- version increment;
- updated specification and documentation;
- structural tests;
- OWL regeneration;
- reasoner validation;
- protocol-version update.

**Rationale.**

This protects the frozen ontology from ad hoc model-driven expansion while allowing evidence-based refinement.

**Ontology impact.**

Defines the change-control boundary.

**Output-contract impact.**

Out-of-ontology candidates must be rejected or deferred, not silently added as new schema elements.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

The formal ontology-change process described above.

---

## G-10 — Prompt scope and extraction granularity

**Question.** How much source content and ontology context should be included in each LLM request?

**Options considered.**

1. Send the complete artifact for every target.
2. Make one request per ontology class or relation.
3. Extract related target families jointly from bounded structural evidence units.
4. Use only summaries or embeddings.

**Current decision.**

LLM extraction will operate primarily on source-preserving structural evidence units rather than repeatedly submitting complete artifacts.

A typical request will include:

1. extraction and abstention instructions;
2. a task-specific subset of ontology targets;
3. minimal artifact metadata;
4. the original source-unit text;
5. bounded structural context when needed;
6. relevant deterministic entities and assertions for that source;
7. applicable deferred records;
8. a strict output schema.

Related entities and relations will be extracted jointly rather than through one request per ontology target.

A selective document-level pass is permitted only when needed for:

- coreference;
- distributed evidence;
- discourse relations spanning multiple units;
- source-level reconciliation;
- relations that cannot be supported from a local unit.

The full artifact may be submitted only when justified by the task, artifact length, model context window, reproducibility design, and cost analysis.

**Rationale.**

This avoids both excessive repetition and insufficient context while preserving consistency among semantically related outputs.

**Ontology impact.**

None.

**Output-contract impact.**

Each run must record the source units, bounded context, eligible targets, routing category, ontology-subset version, and whether the request was local or document-level.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot comparisons showing that another granularity materially improves extraction quality, evidence grounding, or cost without reducing reproducibility.

---

# 4. Publication decisions

## P-01 — Publication pilot scope

**Question.** Which publication targets will be included in the first pilot?

**Options considered.**

1. Extract every publication class, relation, and attribute in ontology 0.1.4.
2. Begin with a focused target subset.
3. Extract only domain entities.
4. Extract only discourse entities.

**Current decision.**

A focused Publication Pilot 1 target inventory has been completed and is final and
binding. It is stored at
`docs/publication_llm_extraction_target_inventory.md`, is governed by ontology 0.1.4,
and uses the validated OWL SHA-256
`7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635`.

The binding target groups include:

- discourse entities and relations;
- Method, ComputationalModel, Tool, Algorithm, Parameter, EvaluationMetric;
- use versus mention;
- Method-to-Finding and metric-reporting relations;
- DatasetMention and DatasetResource relations where evidence is available;
- intra-source representation and bounded inter-source candidates.

Targets outside that final inventory are not authorized for Publication Pilot 1 output.
The corresponding executable profile is complete, frozen, and final and binding:
[`publication_target_inventory.yaml`](../src/extraction/llm/publications/publication_target_inventory.yaml).

**Rationale.**

A focused pilot permits reliable annotation and diagnosis before full-corpus scaling.

**Ontology impact.**

None.

**Output-contract impact.**

The publication contract must reject ontology-valid targets that are outside the frozen pilot target list.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Target-inventory review or pilot-sample analysis.

---

## P-02 — `tendency` and `source` discourse attributes

**Question.** Should the first publication pilot extract the discourse attributes `tendency` and `source`?

**Options considered.**

1. Include both as free text.
2. Define controlled vocabularies before the pilot.
3. Exclude both from the first pilot.
4. Include only one.

**Current decision.**

Exclude both from the first pilot unless the publication target-inventory review demonstrates that they are required for a pilot competency question.

**Rationale.**

Their operational values are not yet frozen, and they would add annotation complexity before the core node, relation, and evidence contract is validated.

**Ontology impact.**

None.

**Output-contract impact.**

These fields are not permitted in the first pilot contract unless this decision is revised.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

A controlled-vocabulary proposal, annotation guidelines, and evidence that the attributes contribute to retrieval or competency-question performance.

---

## P-03 — Tables, figures, equations, and citation markers

**Question.** Which non-prose elements should the first publication pilot process?

**Options considered.**

1. Process all modalities.
2. Process only continuous prose.
3. Process prose and structured table text already available in the corpus.
4. Add separate multimodal and citation-resolution subpilots.

**Current decision.**

For the first pilot:

- include prose;
- include table content only when already available as structured or reliably linearized text;
- exclude interpretation of figure visual content;
- exclude equation interpretation as a semantic extraction target;
- exclude full in-text citation-marker resolution from the initial GO criterion.

**Rationale.**

This isolates the basic ontology-guided extraction problem from multimodal interpretation and citation-resolution complexity.

**Ontology impact.**

None.

**Output-contract impact.**

Source units must record their content type. Unsupported content types must be abstained from or excluded by routing.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot evidence that essential targets are systematically lost without one of these content types.

---

## P-04 — Typed citation-context relations

**Question.** Should the first pilot determine typed semantic relationships between publications?

**Options considered.**

1. Include all typed citation-context relations in the first pilot.
2. Exclude them permanently.
3. Treat them as a separate pilot-dependent subpilot after baseline extraction is validated.

**Current decision.**

Treat typed citation-context extraction as a **pilot-dependent follow-on subpilot**.

It requires reliable resolution of:

```text
in-text citation marker
→ bibliographic reference
→ cited source entity
```

Potential relations include ontology-supported typed citation semantics such as:

- cites as evidence;
- uses method in;
- extends;
- positive support, when permitted by the ontology version used for that subpilot;
- a negative-polarity relation only if it is formally declared by a later version.

No new relation may be introduced without the ontology change-control process.

**Rationale.**

This capability could materially distinguish the final KG from retrieval-only baselines, but it requires a separate grounding and evaluation protocol.

**Ontology impact.**

Potential future ontology impact if pilot evidence supports a missing citation-context relation.

**Output-contract impact.**

A later contract extension must represent citation markers, resolved references, evidence spans, relation type, and resolution confidence or adjudication status.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Successful marker-to-reference resolution and an annotated citation-context sample demonstrating acceptable precision and evidence grounding.

---

## P-05 — Publication source-unit granularity

**Question.** What should constitute a publication evidence unit?

**Options considered.**

1. Full paper.
2. Section.
3. Paragraph.
4. Fixed-token chunk.
5. Section-aware bounded chunk with preserved paragraph structure.

**Current decision.**

Use section-aware bounded source units that preserve paragraph boundaries and structural paths. Adjacent context may be supplied when required. Exact token limits and overlap policy will be selected during pilot design.

The complete and frozen source-unit parameters and request-context policy are specified
in the final and binding
[`publication_source_unit_contract.md`](publication_source_unit_contract.md). That
contract resolves the historical open-parameter sentence above without replacing
section-aware unitization with fixed-token chunking.

The candidate-output JSON Schema and evidence-validation contract are next. The
production source-unit builder and LLM extractor are not yet implemented.

**Rationale.**

This balances semantic coherence, evidence localization, context-window efficiency, and reproducibility.

**Ontology impact.**

None.

**Output-contract impact.**

Every candidate must reference the source-unit ID and exact evidence spans. Run metadata must identify any adjacent context supplied.

**Status.** `decided`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot comparison of paragraph, section, and bounded-chunk extraction.

---

# 5. HydroShare decisions

## D-01 — Parameter extraction from HydroShare text

**Question.** Should the HydroShare LLM module extract Parameters from abstracts and README content?

**Options considered.**

1. Exclude Parameters.
2. Extract mentions only.
3. Extract use/configuration relations where explicit evidence exists.
4. Add a HydroShare-specific parameter model.

**Current decision.**

Deferred until HydroShare module design.

**Rationale.**

The evidence loci and semantics must be tested against actual HydroShare abstracts and README files before defining the allowed relations.

**Ontology impact.**

Potential additive relation decision if current ontology coverage is insufficient.

**Output-contract impact.**

May require parameter value, range, unit, and calibration-status fields.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

A representative HydroShare sample and target-coverage audit.

---

## D-02 — EvaluationMetric extraction from HydroShare text

**Question.** Should EvaluationMetrics reported in HydroShare descriptions or README files be extracted?

**Current decision.**

Deferred until HydroShare module design.

**Rationale.**

The module must distinguish metrics reported as resource content from metrics merely mentioned in linked documentation.

**Ontology impact.**

Potential relation-scope review.

**Output-contract impact.**

May require metric values, units, evaluated targets, and evidence-source distinctions.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Representative-resource analysis.

---

## D-03 — DatasetMention outside publications

**Question.** Should DatasetMention be used in HydroShare or other non-publication sources?

**Current decision.**

Deferred until module-specific evidence demonstrates a need.

**Rationale.**

DatasetMention currently has publication-centered semantics. Extending it should not occur solely for implementation convenience.

**Ontology impact.**

Potential class-scope or relation-scope change requiring a versioned ontology decision.

**Output-contract impact.**

Would affect how unresolved external datasets are represented.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Cases in which a non-publication source clearly mentions a dataset that cannot yet be represented as a DatasetResource.

---

## D-04 — Measurement demotion or retention

**Question.** Should the low-coverage Measurement class remain an active LLM target?

**Current decision.**

Retain in ontology 0.1.3 but exclude from implementation until pilot or module evidence justifies activation.

**Rationale.**

Low observed coverage is insufficient by itself to remove a frozen class.

**Ontology impact.**

Potential future status change or ontology cleanup.

**Output-contract impact.**

No Measurement output in the initial HydroShare contract unless activated.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Observed instances and reproducible annotation guidelines.

---

## D-05 — Dataset-file role modeling

**Question.** Does dataset-file role information require an ontology or output-contract extension?

**Current decision.**

Deferred. Treat as a separate deterministic or hybrid modeling decision rather than a prerequisite for publication LLM extraction.

**Rationale.**

It does not block the first pilot.

**Ontology impact.**

Potential datatype or controlled-vocabulary addition.

**Output-contract impact.**

Potential file-level attributes.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

HydroShare file-inventory analysis showing direct value for competency questions or retrieval.

---

# 6. GitHub decisions

## C-01 — ModelVersion versus SoftwareVersion

**Question.** Should repository version information remain ModelVersion or be generalized to SoftwareVersion?

**Current decision.**

Deferred until GitHub module design.

**Rationale.**

The decision requires evidence from release tags, CITATION files, README descriptions, tools, and computational models.

**Ontology impact.**

Potential class rename, superclass addition, or new relation.

**Output-contract impact.**

Version type, value, source, release date, and target entity fields.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Representative repository version patterns.

---

## C-02 — RepositoryPurpose controlled vocabulary

**Question.** What controlled values should RepositoryPurpose permit?

**Current decision.**

Deferred until GitHub sample review.

**Rationale.**

The vocabulary must emerge from the corpus and be frozen before extraction.

**Ontology impact.**

Potential controlled-vocabulary documentation or schema extension.

**Output-contract impact.**

Purpose values must be enumerated and validated.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Corpus-derived purpose inventory and annotation agreement.

---

## C-03 — Repository LLM dossier

**Question.** Which repository files should be included and prioritized for LLM extraction?

**Current decision.**

Deferred until GitHub module design.

Candidate loci include:

- README;
- notebook Markdown;
- CITATION;
- selected documentation;
- configuration explanations;
- downloaded high-priority files.

Source-code AST extraction remains out of scope for the current phase.

**Rationale.**

The dossier must align with the existing deterministic selection policy and token budget.

**Ontology impact.**

None.

**Output-contract impact.**

Each evidence unit must retain repository path, commit SHA, file hash, content type, and selection reason.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Coverage and cost analysis over representative repositories.

---

## C-04 — Repository semantic distinctions

**Question.** What operational rules will distinguish:

- usesParameter versus mentionsParameter;
- describesFunction versus describesAlgorithm;
- usesModel versus implementedBy;
- usesTool versus mentionsTool?

**Current decision.**

The ontology distinctions are frozen, but extraction guidelines and examples remain deferred until GitHub module design.

**Rationale.**

The evidence thresholds must be tested against repository prose.

**Ontology impact.**

None unless the distinctions prove unworkable for expert annotators.

**Output-contract impact.**

Requires relation-specific evidence criteria and competing-target rejection reasons.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Annotated repository examples and pilot error analysis.

---

## C-05 — Monorepository handling

**Question.** How should LLM extraction treat repositories containing multiple products, models, tools, or workflows?

**Current decision.**

Deferred until GitHub module design.

**Rationale.**

The solution must align with deterministic monorepository representation and avoid conflating repository-level and component-level entities.

**Ontology impact.**

Potential component-modeling review.

**Output-contract impact.**

May require component paths and repository-local entity scopes.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Representative monorepository cases.

---

# 7. CIROH Hub decisions

## H-01 — Direct product entities versus intermediate catalog entities

**Question.** Should product cards directly represent Tool, ComputationalModel, DatasetResource, or Method entities, or should they use an intermediate CatalogEntry/ResearchProduct class?

**Current decision.**

Deferred until CIROH Hub module design.

**Rationale.**

Ontology 0.1.3 retains the hierarchical product aggregation introduced in 0.1.2 but explicitly defers this modeling choice.

**Ontology impact.**

Potential new class and relation structure requiring ontology versioning.

**Output-contract impact.**

Determines whether product cards yield domain entities directly or catalog-record candidates linked to domain entities.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Representative product-card analysis and competency-question evaluation.

---

## H-02 — Example versus CodeExample

**Question.** Should documentation examples remain one Example class or be divided into CodeExample and other example types?

**Current decision.**

Deferred until documentation module design.

**Rationale.**

The corpus must demonstrate a stable, useful distinction.

**Ontology impact.**

Potential class specialization.

**Output-contract impact.**

Content-type-specific example fields.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Coverage and annotation agreement across MDX examples, commands, and admonitions.

---

## H-03 — ProductCategory controlled vocabulary

**Question.** What product-category values should be allowed?

**Current decision.**

Deferred until product-catalog analysis.

**Rationale.**

The vocabulary must be corpus-grounded and methodologically justified.

**Ontology impact.**

Potential controlled vocabulary.

**Output-contract impact.**

Enumerated and validated category values.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Catalog inventory and annotation study.

---

## H-04 — Page-type gating and MDX content

**Question.** How should page type control eligible targets and processing of MDX components, procedures, admonitions, and product cards?

**Current decision.**

The general gating principle is frozen, but exact extraction rules remain deferred until CIROH Hub module design.

**Rationale.**

Different page genres support different ontology targets and evidence structures.

**Ontology impact.**

None unless corpus evidence reveals missing page or entity types.

**Output-contract impact.**

Requires page-type metadata, component type, structural path, and target eligibility.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Representative page-type sample and routing evaluation.

---

## H-05 — Documentation relation thresholds

**Question.** What evidence thresholds distinguish describes, mentions, references, announces, catalogs, and documents?

**Current decision.**

Ontology semantics are frozen; operational extraction guidance remains deferred until the CIROH Hub module design.

**Rationale.**

These distinctions require module-specific positive and negative examples.

**Ontology impact.**

None unless expert annotation shows a schema defect.

**Output-contract impact.**

Relation-specific evidence rules and rejection reasons.

**Status.** `deferred`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Annotated documentation sample and disagreement analysis.

---

# 8. Decisions deferred until pilot evidence

## PE-01 — Low-coverage targets

**Question.** Which ontology targets should remain active after the pilot?

**Current decision.**

Do not remove or demote targets before measuring:

- observed coverage;
- precision;
- recall;
- abstention;
- annotation agreement;
- evidence-grounding success.

**Ontology impact.**

Potential later status revision.

**Output-contract impact.**

Pilot metrics must be reported by target.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot metrics and expert review.

---

## PE-02 — Difficult semantic distinctions

**Question.** Can experts and the LLM consistently distinguish:

```text
ComputationalModel
Tool
Method
Algorithm
Concept
```

and:

```text
uses
mentions
describes
references
implements
```

**Current decision.**

Evaluate empirically before revising definitions.

**Ontology impact.**

Potential versioned refinement only if disagreement reflects schema ambiguity.

**Output-contract impact.**

Record competing classes or relations and rejection reasons.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Inter-annotator agreement and error analysis.

---

## PE-03 — Evidence granularity

**Question.** Should evidence be an exact sentence, multi-sentence span, paragraph, table region, or discontinuous set of spans?

**Current decision.**

Begin with exact contiguous spans in source-preserving evidence units. Permit multiple evidence references for one candidate. Evaluate whether discontinuous evidence is required.

**Ontology impact.**

None.

**Output-contract impact.**

The initial contract must support multiple evidence spans but need not support one discontinuous span object.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Pilot candidates that cannot be supported accurately through one or more contiguous spans.

---

## PE-04 — Confidence scores

**Question.** Should candidates include model confidence scores and acceptance thresholds?

**Current decision.**

Do not use an uncalibrated confidence threshold as an acceptance criterion in the first pilot. Confidence may be recorded experimentally if the model or protocol produces it, but acceptance depends on evidence and validation.

**Ontology impact.**

None.

**Output-contract impact.**

Confidence is optional experimental metadata, not a substitute for evidence or adjudication.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Calibration analysis demonstrating that confidence predicts correctness and supports a defensible threshold.

---

## PE-05 — Necessity of a post-pilot ontology revision

**Question.** Does the pilot demonstrate a genuine need to revise the ontology baseline used for Pilot 1?

**Current decision.**

Evaluate after the publication pilot. Prompt failures, parsing failures, or model hallucinations do not by themselves justify ontology revision.

**Ontology impact.**

A potential later version is permitted only through G-09.

**Output-contract impact.**

The adjudication layer must record out-of-ontology proposals and schema-related failure hypotheses.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

Repeated, expert-validated schema gaps that affect competency questions or defensible representation.

---

## PE-06 — Inter-source relation quality

**Question.** At what point should inter-source candidates be aligned and consolidated?

**Current decision.**

Inter-source candidates may be recorded during source-level extraction, but final inter-source identity resolution and consolidation will begin only after:

- publication pilot quality is evaluated;
- extraction targets and evidence rules are stable;
- the extraction protocol is frozen;
- source-level augmented outputs are reproducible.

**Ontology impact.**

None.

**Output-contract impact.**

Inter-source candidates require unresolved-target representations and later alignment status.

**Status.** `pilot-dependent`

**Decision date.** 2026-07-28

**Evidence that would justify revision.**

A pilot architecture demonstrating that earlier alignment is necessary and does not introduce leakage or error propagation.

---

# 9. Immediate next deliverables

The decisions above authorize the following design work, in order:

1. Create the publication LLM extraction target inventory.
2. Define the evidence and output contract.
3. Define publication source-unit construction and routing.
4. Design the human-annotated pilot sample.
5. Define automatic validation and adjudication rules.
6. Conduct a methodological GO/NO-GO review.
7. Implement a pilot scaffold without full-corpus extraction.
8. Run and evaluate the controlled publication pilot.
9. Decide whether a post-pilot ontology revision is required.
10. Freeze the extraction protocol before scaling and before final inter-source consolidation.

Production extraction code must not be written before the target inventory and evidence/output contract are agreed.

---

# 10. Current decision summary

| Decision area | Current state |
|---|---|
| Ontology baseline | 0.1.4 formally frozen |
| Deterministic Phase B | Frozen and immutable |
| First pilot | Scientific publications |
| Intermediate representation | Source-preserving evidence units |
| Category use | Ontology-native routing scaffolds |
| Prompting | Bounded source units plus task-specific ontology subsets |
| LLM authority | Add, link, enrich, upgrade, propose correction, resolve deferred |
| Direct baseline mutation | Prohibited |
| Intra-source representation | Built per individual source |
| Inter-source connections | Across any two distinct sources |
| Inter-source consolidation | After pilot evaluation and protocol freeze |
| LLM outputs | Stored under `data/interim/<module>/llm/` |
| `data/processed` | Reserved for aligned and consolidated graph products |
| Evidence | Mandatory original-source spans |
| Ontology revision | Evidence-gated and versioned |
