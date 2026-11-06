# Step 14: next prospective candidate-review queue

This is a read-only reconciliation and workload proposal after `cce026a`, not
candidate discovery, new adjudication, or canonical materialization. It follows
the [semantic-candidate](study2_step14_semantic_candidates.md),
[semantic-review](study2_step14_semantic_review.md),
[identity-pilot](study2_step14_semantic_identity_pilot.md), and
[granularity](study2_step14_identity_granularity_adjudication_v0.1.md) contracts.
Original proposals, LLM recommendations, batch-01 decisions, ontology v0.1.7,
Step 13, and order-50 metrics remain unchanged. Step 14A remains skipped.

## Authority and reconciliation

Reuse saved `semantic-review/v1` dossiers and oversized summaries,
`semantic-identity-pilot/v1/review-cases.jsonl`, live v2 audit/request/completion
bindings, the tracked proposal bindings, and approved batch-01 decisions.
Verify the pilot/live manifest pins, the review manifest pin recorded in the
pilot, consumed output hashes, current ontology hashes, and each completed case's
direct audit/request/response references. Reuse the approval validator for the
exact approved scopes. Do not replay extraction, model execution, full-package
adjudication checks, or the full candidate-occurrence/graph scan. The output
manifest records consumed input hashes and implementation hashes.

A **directly reviewed block** has its original block ID among a saved case's
original candidate IDs, with identical class and membership. Shared-reference hub
cases use their original row identities: they do not silently count as reviews
of ordinary identifier blocks. Record their occurrence overlap separately,
including exact same-membership cases. Preserve exact occurrence IDs, overlapping
case IDs, and prior approval decision IDs for each affected occurrence. An
approved occurrence does not confer identity on another member of its block.

Identifier scope is taken only from declarations matching the block's exact
scheme/value key. Deterministic entity-own declarations, source-local literal
declarations, literal geographic declarations, and unsupported/truncated scope
remain distinct. A different identifier elsewhere on the same occurrence cannot
upgrade the block's locator. No URL resolution or identifier inference occurs.

## Recomputed coverage

The bounded saved-artifact run produced these descriptive counts; none is a
hardcoded acceptance criterion in the reconciliation implementation:

| Ordinary cross-family blocks | Count |
|---|---:|
| Total | 267 |
| Directly reviewed lexical blocks | 30 |
| Not directly reviewed | 237 |
| Of these: identifier-based | 79 |
| Of these: lexical | 158 |
| Of these: full prior occurrence overlap | 8 |
| Of these: partial prior occurrence overlap | 2 |

The prior package contains 43 cases / 232 occurrences; batch 01 approves only
99 occurrences. The eight full-overlap blocks are not automatically approved:
they include both approved and unapproved prior review material. The two
partial-overlap blocks concern NGIAB data-preprocess and ngiab-cal repository
locators; remaining members do not inherit their neighbors' approvals.

| Unreviewed stratum | Blocks | Proposed sample |
|---|---:|---:|
| Identifier — DatasetResource | 39 | 8 |
| Identifier — Paper | 6 | 1 |
| Identifier — Repository | 34 | 3 |
| Lexical — Algorithm | 5 | 4 |
| Lexical — MLModel | 10 | 5 |
| Lexical — ProcessBasedModel | 9 | 5 |
| Lexical — Tool | 134 | 4 |

There are **17 oversized cross-family blocks** among the 25 saved oversized
summaries. Retain their original keys, classes, family distributions, member
counts, reconstruction references, and membership hashes. Those hashes were
verified by the original pinned semantic-review run; this queue does not
reconstruct their members or assert newly verified overlap. Their overlap state
is explicitly unknown here. No pairs or subsets are expanded.

## Bounded prioritization and proposed workload

Propose at most **12 identifier blocks and 18 lexical blocks**, with **8 members
per block** and **160 member occurrences overall**. These are prospective workload
limits, not semantic thresholds or a new acceptance policy. Require a complete
block with at least one new occurrence and selected evidence plus source artifacts
for every member. Keep ineligible blocks in the inventory, not rejected.

Round-robin strata are `(ontology class, sorted exact-key identifier-scope set)`;
lexical strata use class alone. Within a stratum, prefer no prior overlap, then
fewer members, then original block ID. Identifier and lexical budgets are separate.
Use complete original membership, never a smaller convenient subset. This
prioritizes incremental review coverage and bounded effort, not presumed identity
likelihood. The current sample contains **30 blocks / 74 distinct occurrences**,
all 74 new to the previous review; it preserves 74 member occurrences without
pairwise expansion. This is a proposed human-review workload, not 30 authorized
provider requests or a model-ready execution package.

The four lexical classes above are the remaining eligible class inventory, not a
new ontology scope. No unreviewed ConceptualModel or Workflow block is imputed.
Large Tool coverage and blocks exceeding the workload cap remain visible and
unresolved. No precision, recall, or population generalization follows from this
purposive sample.

## Reproduction and ignored outputs

From the repository root in the existing `multigranular-kg` environment:

```bash
python -m src.evaluation.step14_next_review_queue
```

Fresh ignored destination: `var/study2_step14/next-review-queue/v1/`:

- `block-inventory.jsonl`: every ordinary cross-family block, review/overlap states,
  exact memberships, identifier scopes, and original dossier references.
- `proposed-sample.jsonl`: the complete selected blocks with bounded original
  excerpts, evidence hashes/pointers, source artifacts, declaration/version fields,
  and full provenance/snapshot recovery references.
- `oversized-inventory.jsonl`: separate summaries, no member expansion.
- `report.md`: coverage, selection rule, exact selected block IDs/keys, limitations.
- `manifest.json`: input/output/implementation hashes, selection limits, counts.

Existing directories are refused. To reproduce after v1 exists, use a fresh
destination under the same root, for example `--output
var/study2_step14/next-review-queue/v1-recheck`. Outputs contain no timestamp or
output-directory-dependent scientific records. Inputs are checked again before
writing. The command blocks network connections and never loads API credentials.

Evidence is the existing selected dossier evidence, not exhaustive source context.
Original truncation remains explicit, with full recovery pointers rooted at
`semantic-candidates/v1`; the pinned input manifests retain that upstream authority
chain. Repeated evidence/artifacts are not independent corroboration. Original
attributes and accepted predicates remain recoverable through the dossier and
frozen snapshot references, without generating or strengthening any relation.

Focused validation:

```bash
python -m unittest tests.test_step14_next_review_queue tests.test_step14_semantic_review -q
```

Tests cover direct review versus overlap, non-propagation of approval, exact-key
identifier scope, unknown scope, oversized non-expansion, reproducible stratified
selection and workload caps, nonmutation, missing context, and fail-closed
membership/class checks. The saved-artifact run verifies input hashes and records
the observed coverage; it does not read the full graph or rebuild candidates.
