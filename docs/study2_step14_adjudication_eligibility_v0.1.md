# Step 14 offline adjudication eligibility analysis v0.1

Implementation `step14-adjudication-eligibility/0.1.0`; **proposed criteria, not an
identity authority or authorization to dispatch**. Follows the approved
[scope](study2_step14_scope_and_completion_decision_v0.1.md),
[identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md),
[two-view retrieval](study2_step14_two_view_retrieval_v0.1.md),
[reconciliation](study2_step14_retrieval_reconciliation_v0.1.md), and
[direct-key grouping](study2_step14_referent_groups_v0.1.md).

## Alternatives for the next researcher decision

No calibrated score cutoff is available. Do not invent one to control cost or case
counts. Original top-k nominations in either view supply the candidate population.
Compare three transparent evidence-readiness alternatives, all excluding only pairs
already covered by the same exact researcher-approved subset:

- **literal:** both endpoints have nonempty selected literal evidence and original
  provenance. Maximizes retained opportunities but includes label-only fragments.
- **context_either:** literal plus at least one endpoint has three distinct
  non-generic words beyond its label words in a selected fragment. Proposed starting
  point for discussion, not approved policy. Allows name-only and evidence-only
  retrieval, unmatched labels and missing versions. The context cue reuses existing
  review utility tokenization; it is not a scientific sufficiency test.
- **context_both:** require that contextual cue at both endpoints. Restrictive
  sensitivity alternative, with a greater risk of losing equivalent referents whose
  selected windows omit useful context.

None requires exact labels, identifiers, high scores in both views or reciprocal
nominations. Unknown and differing version/granularity metadata, generic names,
weak label context and reused quotations are explicit review flags. Metadata
versions are not automatically interpreted as entity releases. Scientific identity
still requires compatible referents and granularity, which this analysis does not
adjudicate. Same names/quotes can describe competing entities; contextual words
can describe function without identifying a referent. Missing context may reflect
window selection rather than the original corpus. No false-positive or recall rate
is inferred from these flags or examples.

Joint cosine histograms use two-dimensional width-0.1 bins, separately by class,
scope and nomination pathway. They are descriptive, not eligibility thresholds.
Class/scope/family/pathway/prior-status eligibility tables expose imbalance without
quotas. Exact-class blocking was already enforced by vector retrieval; this is not
a newly achieved exclusion and no cross-class vector retrieval is introduced.

All 512,024 original unordered pairs receive an accounting row, including approved,
previously identified unresolved, new, insufficient-evidence and thin-context
nonselected cases. Previously reviewed/queued/block co-membership is not approval.
The existing evidence-review-batch01/v1 exact pairs are also pinned and counted as
previously queued, unresolved cases without changing their eligibility. The exact 29 approved subsets and 99 occurrence memberships remain unchanged.
Partial/overlapping approvals never expand through transitivity. Original pilot
recommendations and prior concerns remain reachable through pinned review records;
this analysis does not reinterpret model recommendations as decisions. Nonselected
pairs remain unresolved, not rejected identities. Identifier-only inventory records
outside this original vector-pair population are not silently submitted.

## Packaging and workload

Select the smallest shared existing direct-key group (stable-ID tie-break) only as
an organizational container. Otherwise use a star centered on the lexically smaller
exact occurrence ID. Each unit contains at most eight **explicit original pairs**;
there is no limit on total units or eligible pairs. This is a context-presentation
bound, not a review population budget. Oversized groups are split, not expanded;
leaf-to-leaf comparisons, connected components and overlapping-group unions are
never inferred. Review recommendations must remain pair-specific. An ambiguous
shared name does not turn a presentation container into an identity group.

Each alternative reports pairwise requests versus packaged units and serialized
context bytes, including instructions, exact original excerpts/offsets/source
metadata, original labels, versions, granularity, prior memberships/approval records,
pair scores and pointers. Estimate tokens as UTF-8 bytes / 4, and also report a
conservative byte upper bound. This is approximate draft input workload, not exact
model tokenization, final provider-envelope usage, cost or output-token demand.
No SDK/token-counting API is used. The context recipe and hash permit exact local
reconstruction without duplicating all original response or pair bodies.

## Execution

From the repository root in the existing research environment:

```bash
python -m src.evaluation.step14_adjudication_eligibility --output var/study2_step14/adjudication-eligibility/v1
```

Fresh ignored output required. Verify pinned input hashes before and after execution;
validate every nomination, exact original evidence binding and prior status. Stream
the large pairs file into compact SQLite accounting (16-MiB cache; disk-backed
sorting), without copying the entire input file or keeping it in memory. A failed
run remains untouched and has no completion manifest. Use a fresh version directory
to rerun. The module blocks network connections.

Share `summary.md`, `summary.json`, `criteria.json`, `distributions.json` and
`examples.json`. Keep `accounting.sqlite`, `review-units.jsonl`, `contexts.jsonl`,
`prior-decisions.jsonl` and `manifest.json` locally. Examples are deterministic
minimum-pair-hash representatives by scope and risk/pathway, not a random quality
sample. Complete pair accounting and precise original byte offsets support later
inspection without duplicating the 1.77-GB input.

The researcher chooses criteria after inspecting actual counts/tradeoffs. This task
creates no provider requests, new embeddings, approvals, canonical IDs, ontology
changes, graph writes or alignment production. Focused tests:
`python -m unittest discover -s tests -p test_step14_adjudication_eligibility.py`.
