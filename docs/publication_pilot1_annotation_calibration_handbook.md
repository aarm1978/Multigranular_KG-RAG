# Publication Pilot 1 Annotation / Calibration Handbook

> **Status:** operational MVP for independent review; not a semantic authority  
> **Handbook version:** 0.1.2
> **Binding guideline:** Publication Annotation and Adjudication Guidelines 0.1.1

## Purpose and authority

This handbook explains how to operate Annotation / Calibration Mode. It does not change
category boundaries, evidence rules, completeness rules, or relation signatures. The
frozen annotation/adjudication guideline and target inventory remain controlling.

**No supported evidence span means no accepted semantic assertion.** Use only the
canonical text shown in the application. Do not use web search, memory, another paper,
or model knowledge.

## Workflow

1. Read the complete unit, then select **Reading complete**.
2. In the node pass, select the primary unit or an authorized context unit. First highlight
   the exact node mention and choose **Set node mention from highlight**. Then highlight
   independently supporting text and choose one available node category. Add further spans when the same
   atomic assertion requires distributed support and briefly record why the units must
   be combined.
3. In the relation pass, choose the displayed directional relation and compatible
   endpoints. Highlight evidence that supports the edge itself; endpoint evidence alone
   is insufficient.
4. In final review, record the actual completion state for every available target.
   Routing means a target is legitimate to inspect, not that a positive is present.
5. Correct validation errors and submit.

Structurally unavailable targets are routing provenance, not annotation tasks, positives,
negatives, or abstentions. They are never shown in the annotation menu.

## Evidence mechanics

Select literal text in the source panel. The browser converts UTF-16 selection indices to
zero-based, half-open Unicode code-point offsets. The server independently reconstructs
the canonical slice and rejects any mismatch. Never normalize, edit, or paraphrase a
highlight. A span cannot cross a source-unit boundary.

The primary unit remains the annotation unit. Use `local_unit` when its text is
sufficient, `section_context` only when another canonical unit in the same section is
needed, and `document_reconciliation` only when canonical units elsewhere in the same
document are needed. Every span retains the identity and hash of its own source unit;
never treat adjacent units as one selectable string.

Opening a unit loads only its primary text. Use **Inspect bounded canonical context** to
load one additional unit. Same-section choices may include `eligible` and `context_only`
units; a `context_only` unit supplies evidence but never receives a target menu or
completeness task. To inspect another section, choose one primary-unit routed target and
the narrowest displayed reconciliation reason. Each request loads only the selected
canonical unit and is retained in the context-exposure audit. Exposure alone does not
change discovery scope—only evidence actually cited from that unit does.

The controlled **Context-request reason** explains why a particular other-section unit
must be opened for document reconciliation. It is exposure-audit metadata, not an
assertion-level evidence rationale. The free-text **Distributed-evidence reason** belongs
to one node or relation and explains why that assertion actually needs cited spans from
multiple source units. Opening context alone neither requires a distributed-evidence
reason nor changes `discoveryScope`; the reason becomes required only when the resulting
node or relation cites spans from more than one source unit.

Create one node per atomic semantic unit and use the most specific available concrete
class. Do not merge by similar names. Link an existing entity only when the interface
offers an exact deterministic identity.

Every positive node has one exact `mentionSpan`: the literal text that identifies the
node or atomic proposition. It is not a normalized name and must not be paraphrased. A
named entity mention is usually its name; a Finding, Claim, or Limitation may use the
atomic clause it represents. The mention and supporting evidence are separate roles.
For example, `hydroGOF` can be the Tool mention while `we used the R package hydroGOF`
supports its Tool classification. They may overlap or be identical when the mention
alone is sufficient, but neither is inferred from the other. Both must be selected and
retained explicitly. A mention from bounded context contributes to discovery scope in
the same way as a cited evidence span.

Only the displayed class-specific structured fields may be recorded:
`EvaluationMetric.value`; `Parameter.value`, `Parameter.range`, and
`Parameter.calibrationStatus`; and `Repository.fork` and `Repository.commitSHA`. Every
populated field needs its own highlighted evidence, even when that evidence is also used
for the node.

Relations remain directional. Read the displayed `source → relation → target` signature.
The interface does not reverse edges, infer relations from co-occurrence, or offer summary
relations.

## Completeness and uncertainty

For routed `extract_and_evaluate` targets, record every supported positive; an exhaustive
review with none is an actual completed-zero-positive state. For
`extract_and_monitor`, record supported positives and complete the non-exhaustive monitor
review; do not turn this into a negative assertion. Prospective screening expectations
are not annotation states.

Use an allowed uncertainty category when needed. Uncertainty is distinct from completed
zero-positive review and does not create a positive assertion.

## Timing, pauses, and technical interruptions

The application records phase transitions. Use **Pause** for breaks or idle time and
**Resume** before continuing. Use **Technical interruption** only for interface,
computer, or source-access problems, ending it when work can resume. These intervals are
excluded from active annotation time. Training and joint discussion occur outside an
independent timed session.

The exported event stream—not browser wall-clock duration—is authoritative.

## Submit and reopen

Autosave appends revisions. Submission freezes an immutable submitted snapshot and never
overwrites it. A deliberate reopen records a reason and action, preserves prior
submissions, and begins a new timed revision pass. Annotator identity remains stable for
the session.
