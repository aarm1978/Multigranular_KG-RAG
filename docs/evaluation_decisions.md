# Evaluation Decisions — Study 2

**Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts — Intrinsic Evaluation Strategy**

**Purpose.** This document records the evaluation design for Study 2: which metrics are
computed, at which points in KG construction, how the three-LLM robustness analysis is
structured, and how the schema-agnostic comparison against Microsoft GraphRAG is framed.
It is a decisions record (rationale + table skeletons) intended as direct input to the
manuscript's evaluation section, and as the contract for the metrics-computation script.

**A note on justification.** Each methodological decision below is tagged with its
justification status: anchored (a verified source exists, e.g. MINE in the proposal),
`[CITE-NEEDED: …]` (a reference must be found before the manuscript), or argued (justified
by explicit reasoning rather than citation). Citations are NOT invented here; placeholders
mark where literature support must be added. This doubles as a checklist of what still
needs grounding.

---

## 1. Framing: intrinsic evaluation, two purposes

The proposal (Section 3.4) commits to a **multi-layer intrinsic evaluation** with three
components: (i) extraction accuracy and semantic depth against a gold standard, (ii)
consolidation measured by redundancy reduction, and (iii) ontology soundness via
competency questions and consistency checks. The proposal explicitly frames this as
"comparative only in an intrinsic sense — measuring improvements across stages of the
pipeline rather than against external baselines," because no external ontology/KG exists
for the CIROH ecosystem.

**Addition from the proposal defense.** During the defense, an external comparison was
added *for two schema-agnostic structural metrics only* (information density, relational
richness), against a KG produced by Microsoft GraphRAG. This is consistent with the
proposal because these two metrics do not depend on the schema, so they can compare two
KGs with different schemas fairly. This addition is recorded as a defense commitment, not
a post-hoc change. `[CITE-NEEDED: Microsoft GraphRAG — the original GraphRAG paper/library
reference for the baseline.]`

The evaluation therefore serves **two distinct purposes**, which must not be conflated:

- **Purpose 1 — Internal trajectory (self-comparison).** Structural metrics measured at
  successive construction points, each compared against earlier versions of the *same* KG.
  Characterizes how structural density and relation-type diversity change as additional
  sources are integrated and entities are later consolidated. No external baseline. This
  is the proposal's intrinsic stance.
- **Purpose 2 — External comparison (vs. GraphRAG).** The two schema-agnostic metrics
  measured on the *final assembled* KG and on GraphRAG's KG of the *same complete corpus*.
  Shows that the ontology-guided pipeline yields a structurally richer graph than a
  schema-agnostic one. GraphRAG enters only at the final state.

The two purposes meet at one state — the **final assembled KG** — which is both the last
point of the internal trajectory and the operand of the external comparison.

**Scope boundary (important for honest claims).** Density and richness measure *how much
structure*, not *how correct* it is. A denser graph is not automatically a better one.
Correctness is established separately by the gold-standard component (Precision/Recall/F1)
and logical soundness through the authoritative HermiT validation gate. ELK is retained
only as a profile-limited technical cross-check. The schema-agnostic comparison
supports a claim of *structural richness*, which—combined with correctness and consistency
evidence—supports the overall claim of a faithful, rich representation. It is one leg of
the argument, not the whole.

---

## 2. Metrics, defined

### 2.1 Structural metrics (schema-agnostic) — measurable now

Inspired by the Measure of Information in Nodes and Edges (MINE) benchmark (proposal ref
[97]). `[CITE-NEEDED: confirm MINE citation [97] resolves to the correct reference in
references.bib.]`

- **Information density** — average number of *semantically informative* attributes and
  relations per entity, **excluding purely administrative or identifier fields** (e.g.
  internal IDs, checksums, bag URLs, timestamps). *Decision (argued):* the exclusion list
  must be defined explicitly and applied identically to both KGs in the comparison, or the
  metric is not comparable. The script defines one fixed global administrative/identifier
  exclusion set plus a small class-specific mapping for keys whose meaning is contextual.
  Both sets and their observed per-class use are recorded in every metrics result. False
  Boolean values remain countable when their keys are informative; administrative Boolean
  keys are excluded by policy rather than treated as absent.
- **Relational richness** — average number of *distinct relation types* incident on each
  entity. Counts relation-type variety per node, not relation volume.

Both are schema-agnostic: they ask "how many informative attributes / distinct relation
types per entity," never "does class X exist." This is precisely why they can compare KGs
with different schemas (ours vs. GraphRAG's).

#### File-inventory sensitivity policy

`File`, `DatasetFile`, and `RepoFile` are legitimate semantic KG content: they represent
declared repository files, dataset distributions, and documentation source files. They
remain in every actual KG output. Structural metrics are always reported in two variants:

- `full` is the primary description of the actual KG product and uses every node and edge;
- `file_inventory_excluded` is a sensitivity analysis introduced after the deterministic
  trajectory revealed the effect of explicit file-level granularity. Its policy was frozen
  before generating the GraphRAG baseline and conducting the external comparison. It
  excludes the complete explicit file-inventory layer and all edges incident to it.

Both variants are always reported together and neither result is suppressed. The
sensitivity analysis does not delete or alter graph content. Its frozen executable class
policy is:

```python
FILE_INVENTORY_CLASSES = frozenset({"DatasetFile", "File", "RepoFile"})
```

The approved class-to-inventory-ID audit is `DatasetFile` → A-D03, `File` → A-C02, and
`RepoFile` → A-C02. The class set is the selector; inventory IDs are validation checks,
not a second filtering rule. An approved class with an unexpected inventory ID causes
evaluation to fail.

The frozen artifacts contain 757 `DatasetFile` nodes, all degree one and incident only to
`hasFile`; 11,702 `File` nodes, all degree one and incident only to `hasFile`; and 242
`RepoFile` nodes, all degree two and incident to both `hasFile` and `hasSourceFile`.
`DatasetFile` represents 58.773292% of the HydroShare graph and `File` represents
92.083727% of the GitHub graph. Thus the explicit file-inventory layer is dominated by
degree-one `File` and `DatasetFile` nodes, while CIROH Hub `RepoFile` nodes connect both
their source repository and their derived documentation page. Removing `RepoFile` in the
sensitivity view also removes its `hasSourceFile` edges because the complete inventory
layer is excluded—not merely leaf edges.

Selection is never based on degree or relation name. Excluded edges are derived only from
whether their source or target is an excluded node. Consequently, a file-inventory node
with several relations remains excluded and an unrelated degree-one node remains retained.
Every numerator and denominator is recomputed independently on the retained graph.

Metric snapshots use `schemaVersion: "1.2"` and `evaluatorVersion: "1.2.0"`. They record
the input path and SHA-256, the
attribute-exclusion policy, excluded classes, counts by class, endpoint-derived excluded
edge counts by relation, and deterministic digests of excluded node and edge IDs. Each ID
digest sorts IDs lexicographically, joins them with `"\n"`, appends one final `"\n"`,
encodes UTF-8, and computes lowercase SHA-256. Individual excluded IDs are not persisted.

### 2.2 Consolidation metric — measurable across stages

- **Consolidation ratio** = (unique canonical entities) / (total extracted entity
  mentions). Lower values indicate greater consolidation of extracted mentions into
  shared canonical entities. The ratio measures the degree of consolidation, not its
  correctness; erroneous over-merging can also lower the ratio. Measured at three points
  (§3): before semantic alignment, after alignment, after assembly. *Decision (argued,
  from proposal):* computed **globally and per entity type**, to separate intended
  multiplicity (e.g. versioned datasets) from undesirable duplication.

### 2.3 Gold-standard metrics — deferred (framework only)

Precision, Recall, F1, and a **fact-recoverability** measure (whether extracted triples
suffice to reconstruct core scientific assertions — problem–method–result chains, dataset
lineage, code–documentation links — without generative inference). These require a manually
annotated gold standard (stratified subset, ≥2 annotators, adjudication, inter-annotator
agreement as upper bound). *Decision:* the gold-standard protocol is a separate sub-design,
documented elsewhere; this document only records that these metrics exist, are measured
**once on the extraction output** (not as a trajectory), and apply mainly to the LLM layer
(deterministic extraction is correct-by-construction w.r.t. source fields).
`[CITE-NEEDED: standard IE evaluation (P/R/F1) reference; inter-annotator agreement
measure, e.g. the specific agreement coefficient chosen.]`

### 2.4 Ontology validation — partially done

Competency questions as Cypher/SPARQL queries (pending instances), logical consistency via
the authoritative HermiT gate (DONE for ontology 0.1.3 — consistent, zero unsatisfiable
named classes, no execution errors), and constraint validation during assembly. Recorded
for completeness; the formalization phase already established consistency.

---

## 3. Measurement points (the trajectory)

Two granularities of trajectory are distinguished. **Fine granularity is adopted** (decision
confirmed), because density and richness evolve as sources are added and entities
consolidated, and the fine trajectory makes source-driven structural changes visible at low marginal
cost (re-running the same script).

The construction pipeline stages and their measurement points are cumulative:

| Stage | Measurement point | Structural metrics | Consolidation ratio | LLM-model dimension? |
|---|---|---|---|---|
| Extraction (per source) | after HydroShare det. | density, richness | (mentions, pre-consolidation) | no (deterministic) |
| | after +GitHub det. | density, richness | | no |
| | after +Hub det. | density, richness | | no |
| | after +Papers det. | density, richness | | no |
| | after LLM layer added | density, richness | ratio "before alignment" | **yes — ×3 models** |
| Alignment (consolidation) | after semantic alignment | density, richness | ratio "after alignment" | yes — ×3 models |
| Assembly | after graph assembly | density, richness | ratio "after assembly" | yes — ×3 models |

Thus “+ GitHub” means the concatenated HydroShare and GitHub mention graphs, not GitHub in
isolation. Module-only diagnostics may be computed for quality control, but they are stored
separately and do not become internal-trajectory rows. Pre-alignment cumulative snapshots
perform no canonical-key matching, stub resolution, semantic merging, or consolidation.

The cumulative structural metrics are not expected to be monotonic. Adding a source
dominated by low-degree or attribute-sparse entity classes can lower a global average while
still increasing graph coverage and total represented information. Global values must
therefore be interpreted together with node and edge counts and per-class diagnostics.

*Reading the table:* the deterministic-only points have no model dimension (no LLM
involved). The model dimension (×3) appears only from the LLM layer onward, because only
the LLM-produced portion of the graph varies by model; the deterministic portion, the
ontology, the consolidation logic, and assembly are model-invariant. This keeps the matrix
manageable: it is "the LLM-dependent points × 3," not "everything × 3."

*Decision (argued):* the three proposal-mandated consolidation-ratio points (before/after
alignment, after assembly) are the coarse trajectory; the per-source structural points are
the fine trajectory. Both use the same script on different node/edge snapshots.

*What "before vs. after alignment" means.* The deterministic and LLM extractors **seed**
entity mentions with their best deterministic key (ORCID/ROR/SPDX, else name key) but do
**not** merge duplicates. Semantic alignment is the separate step that merges equivalent
mentions (the multiple "David Tarboton"s, the "University of Alabama" variants, the same
Tool across HydroShare and the Hub). The difference between the two ratios is exactly the
effect of consolidation. (This alignment step is not yet built; it is a pending pipeline
component.)

---

## 4. The three-LLM robustness analysis

**Models (confirmed):** `gpt-oss-120b`, `qwen3.6-27b`, `gpt-5.5-2026-04-23`.
`[VERIFY: confirm these exact identifiers at experiment time — model names version
rapidly; qwen version was confirmed by the lab.]`

**The claim is robustness, not model selection.** The contribution is NOT "which LLM is
best." It is that the **intrinsic improvement holds regardless of the model used** — i.e.
the ontology-guided pipeline produces a structurally rich KG, and its advantage over the
schema-agnostic baseline persists, across all three models. `[CITE-NEEDED: a reference
motivating multi-model robustness / sensitivity analysis as a validity practice in
LLM-based extraction.]`

**Why the model dimension is bounded.** The LLM affects only the interpretive extraction
layer. Everything else (deterministic extraction, ontology, consolidation, assembly) is
identical across models. So a model change varies only the LLM-produced subgraph.

**Reporting decision (argued):** report structural metrics on the **full KG** per model
(the real product; the primary robustness evidence), and, as a supporting analysis, on the
**isolated LLM-layer subgraph** per model (which isolates the model's effect, since the
large deterministic portion can otherwise dilute model differences). The full-KG view
carries the main robustness argument; the isolated view shows even the model-sensitive part
is stable.

**Cost/ordering note (pending).** Running the LLM extraction ×3 (and GraphRAG ×3, see §5)
multiplies compute. Open models (`gpt-oss-120b`, `qwen3.6-27b`) are cheaper/local;
`gpt-5.5-2026-04-23` is the paid one. *Suggested order:* validate the full evaluation
pipeline with the open models first, reserve the paid model for last, to avoid burning
costly credits while debugging. Budget to be defined with the advisor (ties to the pending
lab OpenAI-credit item).

---

## 5. External comparison vs. Microsoft GraphRAG

**Design (confirmed): paired, per-model.** GraphRAG is run with *each* model, and the
ontology-guided pipeline is run with *each* model, and comparison is **within each model**:
GraphRAG-with-model-M vs. ours-with-model-M. This controls for the model: any difference is
attributable to the *approach* (ontology-guided vs. schema-agnostic), not the model — and
it yields two robustness arguments at once (our advantage holds across models; our metrics
are stable across models).

**What is compared.** The two schema-agnostic metrics only (information density, relational
richness), on the **final assembled** ontology-guided KG vs. GraphRAG's KG, both over the
**complete corpus** (all four artifact types). *Decision (argued):* comparing partial
trajectory points against GraphRAG would be invalid — only same-corpus KGs are comparable,
so the comparison is at the final state only.

**Formal comparison and supporting sensitivity view.** The formal schema-agnostic
comparison is GraphRAG `full` versus Multigranular KG `full`, using the same
administrative/identifier attribute exclusions and metric-counting rules. The
Multigranular KG `file_inventory_excluded` result is a supporting granularity sensitivity
analysis, and GraphRAG `full` may be shown alongside it as contextual reference. This does
not constitute a symmetrically filtered comparison. The file-inventory filter must not be
claimed or applied symmetrically across the two schemas unless a common cross-schema
file-inventory identification protocol is defined and frozen before evaluating the
baseline. The external comparison remains limited to information density and relational
richness. Consolidation remains an internal pipeline metric, although it is calculated in
both Multigranular KG variants for consistency.

### Table skeleton — schema-agnostic comparison (Purpose 2)

| Model | Information density — GraphRAG KG | Information density — Multi-granular KG | Relational richness — GraphRAG KG | Relational richness — Multi-granular KG |
|---|---|---|---|---|
| gpt-oss-120b | | | | |
| qwen3.6-27b | | | | |
| gpt-5.5-2026-04-23 | | | | |

*Reading:* each row fixes the model; compare GraphRAG vs. Multi-granular within the row
(approach effect, model held constant). Read down our columns to see stability across
models. "Multi-granular KG" = the final assembled KG. `[VERIFY: confirm GraphRAG's exact
configuration/version used.]`

---

## 6. Report table skeletons

### 6.1 Internal trajectory — structural metrics (Purpose 1)

The trajectory report uses three tables. Table A is the primary full-KG result. Table B is
explicitly labeled as a sensitivity analysis and is not a replacement graph. Table C
reports `file_inventory_excluded − full`, with absolute and percentage deltas wherever the
full value is nonzero.

#### Table A — Full KG

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) | | | | | | | |
| + GitHub (det.) | | | | | | | |
| + Hub (det.) | | | | | | | |
| + Papers (det.) | | | | | | | |

#### Table B — File-inventory-excluded sensitivity analysis

Uses the same rows and columns as Table A.

#### Table C — Sensitivity effect

| Construction point | Excluded nodes | Excluded edges | Excluded nodes as percentage of full graph | Delta information density | Delta informative attributes per node | Delta incident edges per node | Delta relational richness | Delta consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HydroShare (det.) | | | | | | | | |
| + GitHub (det.) | | | | | | | | |
| + Hub (det.) | | | | | | | | |
| + Papers (det.) | | | | | | | | |

For the LLM-onward rows, this table is instantiated **once per model** (×3), per §4.

### 6.2 Consolidation ratio — global and per entity type (Purpose 1)

| Stage | Global | Person | Organization | Tool | ComputationalModel | DatasetResource | … |
|---|---|---|---|---|---|---|---|
| before alignment | | | | | | | |
| after alignment | | | | | | | |
| after assembly | | | | | | | |

Per-type columns separate intended multiplicity (e.g. versioned datasets) from undesirable
duplication.

### 6.3 Gold-standard (deferred — framework only)

| Layer / source | Precision | Recall | F1 | Fact recoverability |
|---|---|---|---|---|
| (to be defined with the gold-standard protocol) | | | | |

---

## 7. What is measurable now vs. later

- **Now:** information density, relational richness, and mention-level counts at the
  HydroShare deterministic point and the cumulative HydroShare + GitHub deterministic
  point. GitHub alone is retained only as a module diagnostic.
- **As construction proceeds:** materialize the next cumulative snapshot and re-run the
  same evaluator after each added source and each consolidation stage (the fine trajectory).
- **Later (requires LLM layer):** the model dimension (×3), the before/after-alignment
  consolidation ratios.
- **Later (requires gold standard):** Precision/Recall/F1, fact recoverability.
- **Later (requires GraphRAG runs):** the §5 comparison.

---

## 8. Open items / pending decisions

- `[CITE-NEEDED]` items above: MINE [97] verification; GraphRAG reference; IE-metrics and
  inter-annotator-agreement references; multi-model-robustness rationale reference.
- Confirm exact model identifiers at experiment time (§4).
- Confirm GraphRAG configuration/version and that its run uses the same corpus (§5).
- Preserve the ratified global and class-specific administrative/identifier exclusion
  policy for information density (§2.1) and apply it identically to both KGs.
- Preserve the frozen Multigranular KG file-inventory class policy and endpoint-derived
  edge filtering as a supporting sensitivity analysis; do not claim symmetric GraphRAG
  filtering without a pre-defined common cross-schema identification protocol.
- Decide whether the "Multi-granular KG" in the GraphRAG comparison is strictly the
  assembled state (recommended) — confirm.
- Budget and ordering for the ×3 (and GraphRAG ×3) runs, with the advisor.
- Gold-standard protocol: separate design (annotators, stratification, adjudication).
