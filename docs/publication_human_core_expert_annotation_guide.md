# Publication Pilot 1 — Human Core Expert Annotation Guide v1.1

## Purpose, role, and authority

This is the practical guide for the researcher/expert, the primary prospective Human
Core annotator. It is an annotator-facing operational guide, not a new semantic
authority. If it conflicts with frozen CIROH ontology `0.1.4`, the Publication target
inventory (`src/extraction/llm/publications/publication_target_inventory.yaml`), the
annotation/adjudication guideline, evidence contract, routing contract, or the
implemented application, those authorities control.

Guide v1.1 prospectively supersedes Guide v1.0 before any Human Core annotation was
created. It preserves the same source-bounded task, frozen N=5 sample, reliability
subset, schema, interface, routing, and ontology authorities.

Human Core annotation is **model-blind**. Do not view LLM prompts, candidate outputs,
parser/validator results, confidence, or proposed labels while creating the Human Core
record. The task is source-bounded representation of what the canonical text supports;
it is not a determination of hydrological truth in the world.

During primary Human Core annotation, use only canonical material available through the
application, including bounded canonical context opened through the application. Do not
use PDFs, web sources, repositories, LLMs, or other external material to repair, resolve,
or enrich an assertion. Record source uncertainty instead when canonical material is
insufficient or defective. Expert knowledge may help interpret canonical text and apply
the ontology, but it cannot substitute for canonical evidence or introduce unsupported
facts.

**Governing rule: no supported evidence span means no accepted semantic assertion.**

Current prospective application identifiers:

- Annotation schema: `0.1.2`
- Annotation interface: `publication-pilot1-annotation-calibration/0.1.3`

Historical Calibration records use schema `0.1.1` and interface
`publication-pilot1-annotation-calibration/0.1.2`. They are preserved unchanged; this
guide does not migrate, reinterpret, or replace them.

## Scope and completeness

The target menu is a bounded inspection task, not a prediction that a positive exists.

- For routed `extract_and_evaluate` targets, search the declared unit scope
  exhaustively and record every supported positive.
- `extract_and_monitor` targets are not systematically searched. Incidental clear
  positives may be recorded, but are optional unless a node is needed as an endpoint for
  a scored relation; no exhaustive absence claim applies.
- A monitor-only node may be created when it is needed as an endpoint for a scored
  relation. That supporting node does not independently enter the primary entity Recall
  denominator unless its own target is scored.
- Structurally unavailable targets are not annotation tasks, positives, negatives, or
  abstentions.

Use the review state that describes what you actually did:

| Target treatment | Positive(s) recorded | No supported positive |
| --- | --- | --- |
| `extract_and_evaluate` | **Reviewed — positive(s) recorded** | **Exhaustively reviewed — no positive** |
| `extract_and_monitor` | **Reviewed — positive(s) recorded** | **Monitored review complete** — not a negative assertion |
| genuinely unresolved | **Abstention / uncertainty**, with an uncertainty record when appropriate | **Abstention / uncertainty**, with an uncertainty record when appropriate |

## Evidence and node mentions

### Separate roles

A node mention identifies *what* the node is. Supporting evidence establishes *why* the
class or assertion is supported. They may overlap, but neither is inferred from the
other. Relation evidence is separate again: evidence establishing two endpoints does not
automatically establish a relation between them.

Use literal, smallest-sufficient text selections. The application validates each selected
span against its canonical text and coordinates. Do not paraphrase, normalize, repair,
or select across a source-unit boundary.

### Tabular results and gauge mentions

Exhaustive annotation applies to routed semantic targets, not every numeric or result
cell in a table. Annotate a table value only when the target contract explicitly models
it as a target or attribute, or when it is necessary evidence for a routed assertion.
Do not transcribe a table merely because it contains results.

For a Gauge mention, select the smallest sufficient literal canonical span. Do not
normalize or invent a form such as `USGS <id>` unless that exact form is literal in the
canonical text. A gauge ID alone may be the identifying mention when canonical evidence
establishes its Gauge role. If conversion corruption prevents safe interpretation, record
`source_conversion_problem`; do not repair it from an external source.

Multiple supporting evidence spans from one `sourceUnitID` are local multi-span evidence.
When the final node or relation cites spans from more than one `sourceUnitID`, it is
distributed evidence and requires a concise **Distributed-evidence reason** explaining
why the units must be combined.

### Composite node mentions

Schema `0.1.2` permits one node's identifying mention to have two or more fragments when
a canonical conversion artifact (for example, a table or figure) interrupts one semantic
proposition.

- Every fragment is an ordinary contiguous, literal, coordinate-valid source span.
- All fragments belong to the same `sourceUnitID`; they are retained in source order and
  cannot overlap or duplicate.
- The legacy `mentionSpan` is the primary, first fragment. `mentionSpans` contains that
  fragment and every additional fragment.
- The UI may display fragments joined by `…`. That display is not literal source text:
  do not create a synthetic joined span, a synthetic range, or a discontinuous
  `EvidenceSpan`.
- Composite mention fragments identify the node; they are not supporting evidence. Add
  supporting evidence separately.
- If an added fragment was a mistake, use **Remove mention fragment**. When one fragment
  remains, the application serializes the valid legacy single-mention representation and
  removes `mentionSpans`.

### Practical node procedure

1. Read the complete primary unit.
2. Highlight the exact identifying mention and click **Set node mention from highlight**.
3. Choose the visible node type and identity action. Use **link existing** only for an
   exact deterministic endpoint offered by the interface; never link from name similarity.
4. Highlight class/assertion support and click **Add node with supporting evidence**.
5. To add local or distributed support, select the node card, highlight a new support
   span, and use **Add highlight to selected node**.
6. To add a conversion-interrupted mention fragment, select the node card, highlight a
   later non-overlapping same-unit fragment, and use **Add mention fragment to selected
   node**.

## Frozen operational boundaries

Apply these prospective rules directly. If canonical text still leaves the applicable
target boundary genuinely unresolved, record uncertainty rather than inventing a rule.

1. **Variable versus Parameter.** Semantic role governs classification. A quantity that
   is observed, predicted, derived, measured, or analyzed as a scientific object may be
   a Variable. A quantity functioning primarily as a configuration, condition, setting,
   threshold, or scenario constraint is closer to Parameter and is not forced into
   Variable.
2. **Theme.** Require text-supported central thematic focus. A subordinate catalogue
   entry, working-group title, or topical label is not automatically a Theme just because
   its wording is thematic.
3. **`reportsMetric`.** A metric explicitly calculated or reported as part of an
   Experiment qualifies even when another metric receives more narrative attention.
4. **`evaluates`.** Textual proximity is insufficient. Evidence must identify what the
   EvaluationMetric evaluates. Multiple local same-unit spans may jointly resolve an
   unambiguous model or method.
5. **NamedPlace / `studiesPlace`.** Incidental geographic localization is not a scored
   NamedPlace or `studiesPlace` assertion. The place must serve as a study area, model
   domain, data coverage area, result location, or otherwise meet the displayed target
   definition.
6. **Limitation.** An explicit substantive boundary on what the current study, method,
   experiment, data, or findings address or support may qualify. Mere rhetorical
   emphasis does not.
7. **DatasetMention versus DataDescription.** DatasetMention identifies a dataset.
   DataDescription describes its origin, period, coverage, sample, resolution,
   variables, partition, or composition. Both can coexist when separately supported.
8. **Source-conversion defects.** The canonical evaluation input governs. Do not silently
   repair corrupted text from a PDF, web source, or other material. Retain assertions
   that remain supported, omit unsupported corrupted propositions/attributes, and record
   `source_conversion_problem` uncertainty.

## A. Unit reading

Read all displayed primary text before creating annotations. Decide whether the unit
itself is sufficient. Do not treat a visible target as mandatory, and do not turn a
plausible interpretation into an assertion without canonical evidence.

### Inspect bounded canonical context

Use **Inspect bounded canonical context** only when the primary text needs controlled
same-document context. It opens one authorized canonical unit at a time.

A primary unit may have multiple bounded-context requests. “One authorized canonical
unit at a time” means one context unit per exposure/request, not one total context unit
per primary unit. Every request must identify the primary-unit target or task it serves.

- **Context-request reason** explains why another unit is opened. For another section,
  select the narrowest offered reconciliation reason and the affected primary-unit
  target/task. It is exposure-audit metadata.
- **Distributed-evidence reason** is free text on a particular final node or relation.
  It explains why that assertion cites more than one source unit.

Opening context alone neither changes a claim nor makes it distributed evidence.
Context is claim-scoped, not an additional annotation surface: do not create nodes or
relations merely because they are discovered in context. Use context only to identify,
reconcile, or support an assertion that belongs to the current primary unit.

## B. Node annotation pass

Create one node per atomic semantic unit. Do not create a duplicate solely because the
same wording recurs. Add a further evidence span when it supports the same node; use
`possible_local_duplicate` uncertainty when identity cannot be safely reconciled.

Only displayed structured fields are annotator-facing: `EvaluationMetric.value`,
`Parameter.value`, `Parameter.range`, `Parameter.calibrationStatus`, `Repository.fork`,
and `Repository.commitSHA`. Each populated attribute needs its own exact evidence span.

## C. Relation annotation pass

Read the displayed direction literally: **source → relation → target**. Choose only
compatible endpoints, then highlight text that supports the edge semantics itself. Use
**Add with edge evidence**; add further edge support with **Add highlight to selected
relation**. Do not infer an edge from endpoint co-occurrence, proximity, shared table
row, or general scientific knowledge.

Create endpoint nodes before dependent relations. If correcting an existing graph,
remove dependent relations before deleting an endpoint node.

## D. Final Review and uncertainty

Final Review records completion for every target shown by the application. It is not a
second opportunity to guess missing assertions. Confirm that every claimed positive has
an actual node or relation card.

Use uncertainty for a genuine unresolved class, relation, atomicity, evidence,
endpoint, source-conversion, local-duplicate, or target-boundary issue. A confidently
completed zero-positive exhaustive review is **not** an uncertainty.

## E. Validate and immutable submit

Review cards, evidence, attributes, uncertainties, and every Final Review state. Click
**E. Validate and submit immutable revision**. Correct any displayed validation error;
successful submission preserves an immutable snapshot and audit trail.

To correct a submitted unit, use **Reopen submitted work** and give a concise reason.
Before editing reopened content, reset affected Final Review states so they again reflect
the work being reviewed. Preserve dependency order: remove relations before endpoint
nodes, then recreate nodes before dependent relations. Resubmission creates another
immutable revision; it does not overwrite the earlier one. Use the session **Export this
session** control to write a validated, deterministic session export.

## Timing and interruption controls

- **Pause** is for breaks, meals, unrelated work, or an intentional stop. Resume before
  active annotation.
- **Technical interruption** is only for interface, computer, package, or source-access
  problems. It is not for ordinary semantic difficulty; record genuine uncertainty
  instead.

Autosave validates and retains draft revisions locally. The audit trail, rather than a
wall-clock estimate, is authoritative for active timing and revisions.

## Concise synthetic examples

All examples below are invented for this guide. They are not Human Core, calibration,
or feasibility material.

### Straightforward node

Synthetic text: “The study applied the BasinSketch package to prepare catchment maps.”

- Tool mention: `BasinSketch`
- Supporting evidence: the full sentence
- Do: create the Tool only if it is among the routed visible targets.
- Do not: infer a repository or a relation that the sentence does not establish.

### Variable versus Parameter

Synthetic text: “Daily nitrate concentration was measured at each outlet; the routing
threshold was fixed at 0.15.”

- `Daily nitrate concentration` may be Variable because it is measured/analyzed.
- `routing threshold` is Parameter because it is a configuration constraint.

### Use versus mention

Synthetic text: “FlowForge is described in prior work. We used FlowForge to aggregate
the gauge records.”

The second sentence supports actual use. Select the strongest supported use relation;
do not retain both use and a weaker mention relation for the same pair.

### Relation-specific evidence

Synthetic text: “The HydroGrid model and MAE appear in Appendix B. MAE was computed to
evaluate HydroGrid forecasts.”

The first sentence may support endpoint occurrence but not `evaluates`. The second,
which identifies what MAE evaluates, supports the directed `evaluates` relation.

### Multiple local evidence spans

Synthetic text: “A field experiment compared two routing schemes. Its reported metric
was Kling-Gupta efficiency.”

For `reportsMetric`, retain both same-unit spans if the first identifies the Experiment
and the second identifies its reported metric. This is local multi-span evidence, not
distributed evidence.

### Distributed cross-unit evidence

Synthetic primary unit: “We applied DeltaTune during all sensitivity trials.”

Synthetic authorized context unit: “DeltaTune is a perturbation-based calibration
method for hydrologic response experiments.”

After opening the context with the appropriate **Context-request reason**, cite both
units only if both are needed for the Method assertion and write a
**Distributed-evidence reason** such as: “The primary unit establishes study use; the
context unit supplies the explicit method characterization.”

### Composite mention interrupted by a figure

Synthetic canonical unit: “The calibrated flow … [Figure 4] … error declined during
storm events.”

If the two literal clauses are one Finding but the figure interrupts the canonical text,
set the initial identifying fragment `The calibrated flow`, create the node, then add
the later same-unit fragment `error declined during storm events`. Keep each fragment
literal and contiguous. Select a separate supporting clause or the same individual
literal span as warranted; never create one joined source span across `[Figure 4]`.

### Source-conversion uncertainty

Synthetic canonical unit: “Table 3 indicates a … [column order lost] … reduction in
error.”

Do not consult a PDF to reconstruct the missing column. Retain only assertions the
canonical text still supports and record `source_conversion_problem` for the affected
target with a concise note.

### Exhaustive Final Review with no positive

For a routed `extract_and_evaluate` target, after reading the required scope and finding
no supported instance, choose **Exhaustively reviewed — no positive**. Do not choose
uncertainty merely because the result is zero.

## Common safeguards

- Do not use model assistance, web lookup, memory, or another source as evidence.
- Do not silently correct canonical conversion defects.
- Do not convert monitor completion into a negative assertion.
- Do not infer a relation from two supported endpoints.
- Do not merge identities by similar names.
- Do not serialize the UI's `…` composite display as source text.
- Do not edit historical CAL_A, CAL_B, CORE_FEAS, calibration submissions, or exports.
