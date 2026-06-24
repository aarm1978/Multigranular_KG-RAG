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
  Shows progressive enrichment as sources are integrated and entities consolidated. No
  external baseline. This is the proposal's intrinsic stance.
- **Purpose 2 — External comparison (vs. GraphRAG).** The two schema-agnostic metrics
  measured on the *final assembled* KG and on GraphRAG's KG of the *same complete corpus*.
  Shows that the ontology-guided pipeline yields a structurally richer graph than a
  schema-agnostic one. GraphRAG enters only at the final state.

The two purposes meet at one state — the **final assembled KG** — which is both the last
point of the internal trajectory and the operand of the external comparison.

**Scope boundary (important for honest claims).** Density and richness measure *how much
structure*, not *how correct* it is. A denser graph is not automatically a better one.
Correctness is established separately by the gold-standard component (Precision/Recall/F1)
and logical soundness by the reasoner (HermiT/ELK). The schema-agnostic comparison
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
  metric is not comparable. The exclusion set is recorded with the script.
- **Relational richness** — average number of *distinct relation types* incident on each
  entity. Counts relation-type variety per node, not relation volume.

Both are schema-agnostic: they ask "how many informative attributes / distinct relation
types per entity," never "does class X exist." This is precisely why they can compare KGs
with different schemas (ours vs. GraphRAG's).

### 2.2 Consolidation metric — measurable across stages

- **Consolidation ratio** = (unique canonical entities) / (total extracted entity
  mentions). Higher = better consolidation, less redundancy. Measured at three points
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
HermiT (DONE — consistent, no unsatisfiable classes; cross-checked with ELK), and
constraint validation during assembly. Recorded for completeness; the formalization phase
already established consistency.

---

## 3. Measurement points (the trajectory)

Two granularities of trajectory are distinguished. **Fine granularity is adopted** (decision
confirmed), because density and richness evolve as sources are added and entities
consolidated, and the fine trajectory makes progressive improvement visible at low marginal
cost (re-running the same script).

The construction pipeline stages and their measurement points:

| Stage | Measurement point | Structural metrics | Consolidation ratio | LLM-model dimension? |
|---|---|---|---|---|
| Extraction (per source) | after HydroShare det. | density, richness | (mentions, pre-consolidation) | no (deterministic) |
| | after +GitHub det. | density, richness | | no |
| | after +Hub det. | density, richness | | no |
| | after +Papers det. | density, richness | | no |
| | after LLM layer added | density, richness | ratio "before alignment" | **yes — ×3 models** |
| Alignment (consolidation) | after semantic alignment | density, richness | ratio "after alignment" | yes — ×3 models |
| Assembly | after graph assembly | density, richness | ratio "after assembly" | yes — ×3 models |

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

**Identical metric definitions both sides.** The administrative/identifier exclusion set
(§2.1) and the counting rules must be applied identically to both KGs, or the comparison is
not fair. Recorded as a hard requirement for the script.

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

| Construction point | Information density | Relational richness | (Consolidation ratio where applicable) |
|---|---|---|---|
| HydroShare (det.) | | | — |
| + GitHub (det.) | | | — |
| + Hub (det.) | | | — |
| + Papers (det.) | | | — |
| + LLM layer [per model] | | | before-alignment |
| after alignment [per model] | | | after-alignment |
| after assembly [per model] | | | after-assembly |

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

- **Now:** information density, relational richness, and (mention-level) counts on the
  existing HydroShare nodes/edges output — capturing the **first trajectory point**
  (HydroShare deterministic, pre-consolidation) before it is lost. Requires only a script
  that reads the nodes/edges JSON.
- **As construction proceeds:** re-run the same script after each source and each
  consolidation stage (the fine trajectory).
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
- Define the administrative/identifier **exclusion set** for information density (§2.1) —
  must be fixed and applied identically to both KGs.
- Decide whether the "Multi-granular KG" in the GraphRAG comparison is strictly the
  assembled state (recommended) — confirm.
- Budget and ordering for the ×3 (and GraphRAG ×3) runs, with the advisor.
- Gold-standard protocol: separate design (annotators, stratification, adjudication).
