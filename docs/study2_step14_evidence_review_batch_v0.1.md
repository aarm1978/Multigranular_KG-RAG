# First evidence-bound Step 14 retrieval review batch v0.1

Implementation: `step14-evidence-review-batch/0.1.0`. This prepares new review
questions under the [approved scope](study2_step14_scope_and_completion_decision_v0.1.md),
[identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md)
and [lossless decision contract](study2_step14_semantic_identity_pilot.md).
It neither changes historical pilot membership nor approves new identities.
The prior 24-case shortlist was diversity-selected, not precision-ranked;
it must not be used to estimate alignment accuracy.

## Inputs and integrity

Consume the completed `retrieval-reconciliation/v1/pairs.jsonl` under its recorded
manifest/output hashes and original input pins. The recorded population is 512,024
unique pairs, including 460,550 new relative to prior authorities. Verify these
counts from the saved summary and streamed records, not as hardcoded selection
quotas. Never regenerate embeddings, retrieval, reconciliation or source records.

Each main case contains exactly the two occurrences of one explicit existing
candidate pair. No connected-component grouping, implied transitive identity,
label-based entity allocation or enlarged approved subset is produced. Recheck
selected directional references and exact prior memberships through the existing
utilities. Recover only selected original occurrence/evidence records; verify
original row hashes, selected evidence hashes and exact quote-relative offsets.
Preserve original source metadata, source offsets, candidate/native-record pointers,
labels, scores, versions, granularity and all prior-review memberships.

## Reproducible review-utility priority

Main cases come from pairs marked new relative to the pinned authorities. For
batch selection only, require both endpoints to have a literal label-bearing
excerpt with at least three non-generic context tokens beyond the label. Also
require either a shared non-generic name token (at least three characters) or the
other original label literally present in an endpoint's excerpt. Cross-mentions
can describe comparisons between distinct entities: they are cues to inspect,
not aliases or identity evidence by themselves. Generic tokens are the small
explicit list in the implementation; no generated descriptions or aliases are used.

Priority is lexicographic and documented in each case:

1. No differing recorded version metadata or explicitly differing recorded
   granularity; unknown granularity remains unknown, not confirmed compatibility.
2. Shared literal name tokens before cross-mention-only cues.
3. Matching explicit recorded granularity, where available, still subject to review.
4. Rarity of shared name tokens among eligible **occurrences**, using the sum of
   `log((N+1)/(token_occurrence_count+1))`. This is a lexical distinctiveness proxy,
   not proof of referent specificity or a population entity frequency.
5. Nonidentical full quote hashes before identical quotes. Distinct quotes do not
   by themselves establish independent evidence; identical quotes do not establish identity.
6. Complementary nomination views, then the lower of the two mean view scores,
   then reciprocity; stable exact pair hash resolves ties.

Version metadata may describe schemas or other administrative details, not an
entity release. Preserve the fields for review rather than normalizing or assigning
versions. Exact class compatibility comes from the pinned candidate universe; the
ontology decision gate remains unchanged. Family, release, implementation, trained
instance and unresolved distinctions must be examined in the actual evidence.

Selection keeps a bounded pool of at most 64 distinct lexical cues per
scope/class/source-family-pair stratum, retaining the highest-priority existing pair
for each cue. The cue is the rarest shared name token, or literal cross-mention text;
it controls batch repetition only and is never an identity or grouping key.
Choose 11 main cases per scope (33 total when available), without reused endpoints
or repeated cues **within a scope**. The same endpoint may participate in a distinct
explicit pair in another scope. Do not fill a shortfall with insufficient-context
pairs. `--cases-per-scope` allows 10–12; report actual coverage and shortfalls.
This is review-utility prioritization, not a calibrated precision ranking. Short
names, aliases with no literal overlap, missing context and oversubscribed cues can
be underrepresented. All unselected pairs remain unchanged and **not rejected**.

## Separate diagnostic anchors and outputs

Select at most one previously approved pair per available scope, up to three,
without reusing the same approval subset across anchors. Both endpoints must be
members of the same exact explicit approved subset. Preserve the original approval
record, full subset membership, rationale, restrictions, authority and reference/hash.
Anchors request no new judgment and do not extend or reinterpret those approvals.

New cases remain `unreviewed`, with null decision authority/canonical ID. Each has
an explicit identity question, original endpoints and excerpts, both directional
scores where available, prior status and priority reasons. Questions distinguish
same referent, shared reference target, conceptual similarity, different entities
and unresolved evidence; they do not prepopulate an answer.

Fresh ignored output: `var/study2_step14/evidence-review-batch01/v1/`:
`cases.json`, `anchors.json`, `review.md`, `summary.json`, `summary.md`, and
`manifest.json`. Share the compact review/case/anchor files, not source corpora.
The manifest pins inputs, implementation and outputs. Existing directories are
refused. Source records and all prior reviews/decisions remain immutable.

## Researcher-terminal execution

Full selection scans the existing large pair JSONL and is left to the researcher
terminal rather than the time-limited Codex shell. It uses existing dependencies
and no provider client:

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_evidence_review_batch --output var/study2_step14/evidence-review-batch01/v1 --cases-per-scope 11
```

No identity approvals, canonical allocation, ontology changes, provider calls or
KG writes occur. The first batch is a post-retrieval, targeted review opportunity,
not an independent blinded evaluation, precision/recall estimate or claim of
alignment completeness.
