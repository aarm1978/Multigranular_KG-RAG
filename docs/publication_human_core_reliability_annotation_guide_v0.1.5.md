# Human Core Independent Reliability Annotation Guide v0.1.5

## Purpose and controlling authority

This is the single, consolidated guide for Annotator 2's independent N=2 Human Core
reliability annotation. It governs session `HUMAN_CORE_N2_RELIABILITY_V015` and package
`publication-human-core-gold-n2-reliability-v015`. Ontology v0.1.5 governs this task;
the package binds both `src/ontology/ontology_spec.yaml` and the generated OWL by hash.
This guide incorporates the mature general evidence, span, identity, context, uncertainty,
workflow, and submission rules of Human Core Guide v1.1, with the v0.1.5 rules below
integrated directly. Annotator 2 does not need to combine Guide v1.1 with the supplemental
addendum.

Annotate only canonical material displayed by the application. This is a source-bounded,
model-blind annotation from scratch: do not access or use primary researcher annotations,
supplemental annotations, baseline nodes, adjudications, prompts, candidate outputs,
validator results, confidence, or any provider/model output. Do not use PDFs, web sources,
repositories, or external material to repair source text. Expert knowledge may interpret
canonical text and ontology rules, but never substitutes for canonical evidence.

**No supported evidence span means no accepted semantic assertion.**

## Exact scope

Only these frozen units are available:

- `pub:34:sec:0015:unit:0001`
- `pub:79:sec:0004:unit:0001`

For each displayed target, read the entire primary unit. `extract_and_evaluate` targets
require exhaustive search of the declared scope: record every supported positive or
**Exhaustively reviewed — no positive**. For `extract_and_monitor`, record clear
positives when found, but a completed zero is not a negative assertion. A visible target
is never a prediction that a positive exists.

The application presents each unit's consolidated target union: its original frozen
routed/scored targets plus the v0.1.5 delta—`AgentBasedModel`, publication-prose
`Organization`, affected AgentBasedModel relation branches, and `hasComponent`.

## Evidence, mentions, and identity

Use literal, smallest-sufficient canonical spans. The application validates text,
code-point offsets, source-unit hashes, and document coordinates. Do not paraphrase,
normalize, silently repair corruption, or select across units. A node mention identifies
what the node is; supporting evidence establishes its class/assertion; relation evidence
must establish the edge itself. Endpoint coexistence, proximity, a shared table row, or
general knowledge never proves a relation.

Create one node per atomic semantic unit. Do not duplicate a node merely because wording
recurs. Use **link existing** only for an exact deterministic endpoint offered by the
application, never name similarity. Structured attributes (`EvaluationMetric.value`,
`Parameter.value`, `Parameter.range`, `Parameter.calibrationStatus`, `Repository.fork`,
and `Repository.commitSHA`) each require exact evidence.

Composite mentions are allowed only where a canonical conversion artifact interrupts one
semantic proposition: fragments must be literal, contiguous, non-overlapping, in source
order, and in the same unit. The first fragment remains `mentionSpan`; the UI's ellipsis
display is not source text. Use separate evidence spans for support.

## Context and uncertainty

Open bounded canonical context only through **Inspect bounded canonical context**, one
authorized unit at a time and only to support an assertion belonging to the primary unit.
Opening context does not create an annotation surface. Use the narrowest context reason;
when final evidence spans cross units, state why both are necessary in the
distributed-evidence reason.

Use uncertainty only for a genuine unresolved class, relation, atomicity, evidence,
endpoint, conversion, duplicate, or target-boundary issue. A confident exhaustive
zero-positive review is not uncertainty. If source conversion is defective, retain only
what remains supported and record `source_conversion_problem`; do not repair it.

## General operational boundaries

- A measured, predicted, derived, or analyzed scientific quantity can be a Variable; a
  configuration, condition, threshold, or scenario constraint is a Parameter.
- Theme requires text-supported central focus. Incidental geography is not NamedPlace or
  `studiesPlace`; it must serve a study/model/data/result role.
- DatasetMention identifies a dataset; DataDescription describes its origin, period,
  coverage, sample, resolution, variables, partition, or composition. Both may coexist.
- `reportsMetric` requires a metric explicitly calculated or reported by an Experiment.
  `evaluates` requires evidence identifying what the metric evaluates.
- A Limitation is an explicit substantive boundary, not rhetorical emphasis.

## Ontology v0.1.5 rules

`AgentBasedModel` is a concrete `ComputationalModel` subtype. Use it only for a named
agent-based simulation model (including ABM), not MLModel or an unspecified model.
For the affected relation branches, apply the ordinary relation evidence rule and the
displayed direction. `usesModel` takes precedence over `mentionsModel` for the same
Paper/AgentBasedModel pair. Do not emit both `usesModel` and `appliesTo` unless text
supports two distinct roles. `evaluates` needs relation-specific evidence; `hasParameter`
must identify the parameter owner. `hasComponent` requires explicit Tool/ComputationalModel
composition—never infer it from co-occurrence.

Publication-prose **Organization is human-annotated as a node** when canonical evidence
supports it. Generic **D-26 `Paper -> mentions -> Organization` is pipeline-derived and
MUST NOT be manually annotated.** Absence of that human-authored edge is expected, not an
omission. No organization-specific semantic relation is authorized.

## Workflow and submission

Read the full unit, annotate nodes, then annotate relations using the displayed
source → relation → target direction. Create endpoints before dependent relations. In
Final Review, complete every target state and confirm every positive has a node or
relation card. Validate and submit an immutable revision. To correct a submission, reopen
with a concise reason, reset affected target states, preserve dependency order, and submit
a new immutable revision. Export only through the session control.

Pause for breaks; use technical interruption only for package, interface, computer, or
source-access problems. The audit trail—not a wall-clock estimate—records active work.
