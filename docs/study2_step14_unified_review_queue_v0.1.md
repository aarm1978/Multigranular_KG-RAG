# Step 14 unified proposed LLM review queue v0.1

`step14-unified-review-queue/0.1.0` implements the researcher-selected union:
**49,731 alias_extended pairs + 24,320 explicit-alias additions = 74,051 unique
candidate pairs**. Selection is reused from pinned existing outputs, not recalculated.
The [scope](study2_step14_scope_and_completion_decision_v0.1.md),
[granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md),
[v0.2 baseline](study2_step14_adjudication_eligibility_v0.2.md), and
[explicit-alias preview](study2_step14_explicit_alias_preview_v0.1.md) remain intact.
No identity approvals, canonical allocation or provider requests are performed.

## Exact reconciliation and dispositions

Verify the consumed manifests and hashes, 29 approved subsets / 99 memberships,
original occurrence evidence, and the prior validated model assessments and alias maps.
Deduplicate only exact unordered occurrence pairs. Stop if the specified union or
its two component counts differ. Any exact approved pair in the selected pool is a
blocker rather than a candidate silently redispatched. Approval never propagates
through overlapping subsets, labels, connected components or prior case membership.

Each of the 74,051 original candidates receives one disposition in `coverage.sqlite`:

- `queued`: assigned exactly once to a prepared unit and an explicit local pair ID.
- `prior_completed_pair_assessment`: the two exact occurrences already formed an
  individual completed model assessment. Preserve its reference for researcher
  reconciliation; do not blindly repeat it or turn it into an approval.
- `prior_group_assessment_overlap`: both occur in the same larger explicit model
  assessment. Preserve that exact scope and defer for reconciliation. This does
  **not** assert that every pair within the group was independently examined.

Being in one pilot case, different assessments, a proposed queue or candidate block
alone does not cause deferral. Prior recommendation values are not shown to the new
LLM. Deferrals remain unresolved and locally inspectable, not rejected identities or
scientifically completed pair judgments. The researcher may later authorize a
specific reassessment; this preparation does not make that choice automatically.

## Compact coherent presentation

Reuse existing smallest direct-key referent containers; otherwise use exact
occurrence-centered stars. Partition by recorded class/version/granularity signatures.
Only the original selected pairs are listed, never induced leaf comparisons. Grouping
is for presentation; no relation or canonical identity follows from it. Preserve
family/architecture/release/implementation/trained-instance uncertainty and shared
reference-target distinctions. Insufficient evidence remains an explicit outcome.

Split deterministically at twelve explicit comparisons, twelve entities or 12,000
UTF-8 payload bytes. These are readability/context bounds, not population quotas.
An individual pair exceeding the context bound fails closed instead of silently
truncating more evidence or overloading a request.

Reuse the compact-context constructor: local entity/source/evidence/pair IDs,
original names/classes, literal source-bound excerpts, recorded entity specificity,
and available accepted incident relations. Source/reference role is unresolved unless
the quoted evidence or incident relation supports it. Full relation neighborhoods
are not rebuilt. Shortened evidence retains exact original offsets through the local
bindings; never fabricate missing context.

Only the `payload` field of `contexts.jsonl` is prospective model-facing input.
Original IDs, paths, hashes, evidence pointers, scores and prior decisions remain
in local sidecars or their pinned original references. Save full endpoint provenance
once; unit bindings reference it by ID/hash rather than repeating an administrative
corpus. The 29 original approval records are retained unchanged in a small local file.

## Execution and outputs

```bash
python -m src.evaluation.step14_unified_review_queue --output var/study2_step14/unified-review-queue/v1
```

Fresh ignored output required. Existing artifacts remain read-only. This consumes
v2 accounting and explicit-alias additions, not new embeddings/retrieval/eligibility.
No live runner or provider dispatch capability is added.

Share `summary.md`, `summary.json`, `examples.json` and optionally `manifest.json`.
Examples are bounded authentic contexts for NWM, LSTM, GEE, NextGen, cross-family
comparisons and specificity ambiguity; unavailable categories are reported explicitly.
They are not a quality sample or identity judgments. Large local files:
`contexts.jsonl`, `unit-bindings.jsonl`, `coverage.sqlite`, `endpoint-provenance.jsonl`
and `prior-decisions.jsonl`. The coverage database maps every exact candidate to
its source reference, disposition and, where queued, its unit. Unit bindings map
local pair and evidence IDs back to that provenance.

The summary reports candidate/disposition/unit counts, packaging savings and actual
serialized compact input bytes. Bytes/4 is an approximate input-token proxy; bytes
are a conservative upper bound. Output planning scenarios use 64–256 tokens per
listed comparison for category, short rationale and evidence references, not measured
usage or a provider/schema guarantee. Future provider envelope/schema overhead is
excluded. Full preparation is reserved for the researcher's terminal.

Focused tests: `python -m unittest discover -s tests -p test_step14_unified_review_queue.py`.
