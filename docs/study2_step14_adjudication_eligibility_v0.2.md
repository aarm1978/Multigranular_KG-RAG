# Step 14 semantic eligibility correction v0.2

Implementation `step14-adjudication-eligibility/0.2.0`; a **proposed screening
policy requiring researcher review**, not identity authority. Preserve the
[scope](study2_step14_scope_and_completion_decision_v0.1.md),
[granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md),
[retrieval](study2_step14_two_view_retrieval_v0.1.md),
[reconciliation](study2_step14_retrieval_reconciliation_v0.1.md) and exact approvals.
Historical v0.1 code is recoverable from Git; its document and local outputs remain
unchanged. This route never reads or copies adjudication-eligibility/v1.

## Why the correction is needed

Context availability alone is not semantic candidate selection. The researcher
reported that the three v0.1 alternatives retained 97.6–99.95% of original pairs.
No v1 output is an input to this implementation.

A bounded inspection of the first 4,096 original reconciled pairs (sorted by exact
IDs, **not a representative sample**) examined their joint cosine bins. Most were
in moderate joint regions; high name similarity also occurred with moderate evidence
similarity. The pre-existing 24-case diagnostic contains ARLSTM/LSTM at approximately
0.862 name / 0.545 evidence, and generic agent-based-model labels at 0.903 / 0.606.
These illustrate why a high name score or substantial prose alone cannot establish
referent compatibility. They are risk examples, not gold labels or calibration data.

Bounded selected examples include `forcingprocessor` occurrences describing invocation
and linking the named repository, with name 1.0 / evidence 0.740, and case variants
at approximately 0.956 / 0.765. These motivate retaining single-view named-reference
opportunities without claiming that versions or implementations are identical.
A 0.901 / 0.689 case with explicit specificity language illustrates a potentially
missed-equivalence risk under the stricter screens, not a demonstrated equivalence.

## Proposed conditions, not fitted request counts

Every route requires original literal grounding, contextual text at both endpoints,
no shared exact approved subset, and the inherited exact-class compatibility check.
Context uses the existing transparent three-non-generic-word availability cue; it
is not a semantic sufficiency test. Evaluate nested alternatives:

1. **dual:** name >= 0.85 and evidence >= 0.80; corroboration by reciprocal nomination
   or a distinctive shared lexical/reference cue.
2. **alias_extended:** dual, or either score >= 0.95 with the same corroboration.
   There is no floor on the other score and no exact-name/identifier requirement.
   Reciprocal vector-only aliases therefore remain possible.
3. **ambiguity_extended:** alias_extended, or max score >= 0.85 and min >= 0.65,
   reciprocity, a distinctive cue, and explicit version/implementation/family
   specificity language or structured version metadata. This route asks a question
   about granularity; it does not resolve it.

These rounded upper-tail operating hypotheses are motivated by the bounded joint
inspection and contrasting cases, **not empirically calibrated optimal cutoffs**.
The evidence cannot justify an identity-probability interpretation, population recall
claim, or one definitive threshold. The full run reports all alternatives by class,
scope, family and prior status, with joint distributions and concrete examples.
The researcher must choose or revise the criteria before any dispatch. No thresholds
are adjusted automatically to satisfy a request budget or target retention rate.

A distinctive cue is a shared non-generic name token present in at most 1% of the
existing eligible occurrence inventory, or an exact literal shared URL/DOI in selected
evidence. This is corpus-specific nomination support, not identifier ownership or
an equivalence rule. Generic collisions, shared quotations and mirrored documentation
can still pass and require review. Missing versions remain uncertainty, never automatic
nonidentity. All nonselected pairs stay unresolved with explicit reasons. Existing
class blocking is inherited, not a new exclusion achievement.

Preserve the 29 approved subsets / 99 memberships and prior pilot, block, queue and
33-case evidence-batch distinctions. Only exact shared approved subsets exclude pairs
as already adjudicated; overlapping approvals do not approve their union.

## Referent-centered contexts and administrative separation

Use an existing smallest direct-key group only as a referent-review container;
otherwise use a star around one exact occurrence. Partition containers by recorded
class/version/granularity signatures, preserving missing metadata rather than
bridging releases. List only selected original pairs. Do not add leaf comparisons
or infer identity through chains. Split a container only when its compact context
would exceed twelve entities or 12,000 UTF-8 bytes; these are readability bounds,
not request quotas. All eligible pairs remain covered, even in large groups.

Each LLM-facing `payload` contains short local entity, source, evidence and pair IDs,
original names, class, source family, literal recorded entity version/implementation
fields, granularity, and at most two 420-character literal evidence fragments per
entity. CFF schema metadata is not recast as an entity version. Include up to three
existing accepted incident relations from the pinned pilot context where available,
with exact direction and bounded literal evidence. This limited context does not
supply full relation neighborhoods; absence is not evidence that relations do not
exist. Source/reference roles remain explicitly unresolved unless supported by the
quotations or incident relations. No generated role descriptions or aliases are used.

Hashes, original IDs, paths, pointers, scores, exact prior decisions and full
provenance remain **only in local sidecars**. The JSONL wrapper's context hash is
administrative; only its `payload` is prospective model input. No previous model
recommendations or score metadata appear in that payload. Local sidecars map every
short ID and substring back to original evidence; truncation is recorded. Ambiguity
requiring omitted context remains a limitation, not permission to infer identity.

Identical payloads across alternatives are stored once. The full pair file is not
copied, and no near-complete v1 review-context corpus is regenerated. SQLite retains
compact accounting and original offsets for every pair. Unit counts and actual
serialized input bytes are computed separately for each alternative, alongside a
bytes/4 token proxy and a conservative byte upper bound. These estimates exclude
future schema/envelope/output overhead and are not billable tokenizer counts.

## Run and review

From the repository root in the existing environment:

```bash
python -m src.evaluation.step14_adjudication_eligibility --output var/study2_step14/adjudication-eligibility/v2
```

Fresh output required; no v1 dependency or overwrite. Share `summary.md`,
`summary.json`, `criteria.json`, `distributions.json`, and `examples.json`.
`llm-contexts.jsonl` contains deduplicated compact payloads; `unit-sidecars.jsonl`,
`review-units.jsonl`, `accounting.sqlite`, original decisions and the manifest remain
local. No dispatch capability or identity approval is introduced. Use only focused
module tests; full analysis is reserved for the researcher terminal.
