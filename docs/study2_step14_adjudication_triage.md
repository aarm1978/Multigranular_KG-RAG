# Step 14 offline adjudication triage consumer

This narrow saved-artifact consumer follows the [scope decision](study2_step14_scope_and_completion_decision_v0.1.md), [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md), batch01 approval ledger, and [next-review queue](study2_step14_next_review_queue.md). Recommendations remain model-authored nondecisions. No canonical allocation, graph write, discovery, retrieval/reconciliation rerun, or provider call occurs.

The 73,416 validated recommendations concern the selected semantic/alias queue, not the entire Step 14 universe. The consumer reads its saved SQLite coverage, bindings and endpoint provenance; consolidated recommendations/summary; referent groups and member sidecar; the saved ordinary/oversized next-review inventories; and the existing candidate-block inventory. It never loads the full occurrence corpus, graph, embeddings or raw responses. Saved manifests retain the upstream authority chain; consumed output hashes, direct document/manifest pins and the approval validator are checked. The consolidation summary supplies its dataset pin. Inputs are checked again before publication. This does not revalidate historical generation or rerun a large pipeline.

Every selected unordered pair appears once in the pair inventory. Category, class, exact family combination, within/across-artifact/family scope, nomination origin and model identity level receive marginal and joint counts. `alias_extended` and `explicit_alias` retain the original selected-pool origin labels; original candidate references retain upstream vector/alias nomination provenance. Generation origin (Batch versus recovery) is separately counted by unit.

Original identifier and lexical blocks remain separate review scopes. Only already-listed selected comparisons are intersected with their exact memberships. Pair memberships across blocks can overlap and must not be added as distinct candidates. The full saved block inventory is retained, including within-family blocks; this is not new candidate generation. No implied block pair is enumerated. Paper, DatasetResource and Repository identifier lanes are not filtered by embedding eligibility. Oversized blocks keep their original counts/hashes and unknown overlap; the 17 cross-family summaries are copied unchanged. The next-review inventory preserves 237 ordinary blocks without direct review (79 identifier, 158 lexical), as well as direct pilot review and full/partial occurrence overlaps. Exact approvals remain scope-qualified subsets, never whole-block approvals or transitive unions.

Review containers reuse original direct keys, with member sidecar references, prior memberships, exact-key identifier scope and exact approvals. Selected pairs outside ordinary containers retain their original explicit pair scope. Priority is mechanical: invalid comparisons, recorded conflicts/version/granularity tensions, ordinary keys, then uncovered explicit pairs. Mixed categories on different pairs are explicitly not logical contradictions. Authentic recommendation text and local evidence bindings remain available for substantive researcher assessment. No free-text semantic adjudication or label-based version inference is attempted.

One proposed review set is limited to 30 complete groups, 8 members per group, and 160 member occurrences. The consumer estimates 5–15 minutes per group as an unmeasured planning assumption. These are workload proposals, not researcher-approved acceptance criteria. Its proposed stopping rule is one bounded pass, explicit unresolved dispositions for remaining work, and retention of the existing ontology decision gate before separately authorized canonicalization. Six invalid pairs remain local assessment gaps; failure is neither identity rejection nor a reason to invalidate unrelated recommendations or reopen generation.

Researcher-terminal execution, from the repository root with the existing `multigranular-kg` environment activated:

```bash
python -m src.evaluation.step14_adjudication_triage --output var/study2_step14/adjudication-triage/v1
```

Fresh ignored output root: `var/study2_step14/adjudication-triage/v1/`. Existing destinations are refused. Outputs:

- `summary.json`, `report.md`, `manifest.json`: counts, workload/stopping proposal and hash bindings.
- `pair-inventory.jsonl`: exact selected comparisons, dispositions, authentic assessments, evidence pointers and risk flags.
- `block-coverage.jsonl`: all existing blocks, exact selected-pair intersections, prior cross-family reviews and approvals.
- `oversized-inventory.jsonl`: unchanged cross-family oversized summaries, without expansion.
- `review-groups.jsonl`, `proposed-review.jsonl`: complete scopes, priority and bounded proposed review.
- `invalid-pairs.jsonl`: exact failed comparisons, affected scopes, provenance, risks and local criticality.
- `prior-decisions.jsonl`: unchanged approved decision records.

Outputs have no timestamps or output-path-dependent records. No full-corpus execution is part of implementation validation. Synthetic validation:

```bash
python -m unittest discover -s tests -p test_step14_adjudication_triage.py -v
```
