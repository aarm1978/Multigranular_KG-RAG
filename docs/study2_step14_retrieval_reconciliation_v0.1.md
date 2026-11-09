# Step 14 retrieval reconciliation v0.1

`step14-retrieval-reconciliation/0.1.0` is an offline diagnostic consumer of the
completed `two-view-retrieval/retrieval-v2/` nominations and `v2/` preparation.
It implements the [approved scope](study2_step14_scope_and_completion_decision_v0.1.md)
under the [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md).
It makes no identity decisions, canonical allocations, ontology changes or KG writes.

## Integrity and counting units

Verify the retrieval summary's preparation hash, all preparation input/output pins,
nomination and normalized-vector hashes, and every recorded embedding receipt,
response hash, completed outcome and exact durable request-intent binding. Reuse
the existing approval validator and pinned preflight/review/queue authorities.
No vectors are generated or scored again. Original files remain immutable.

Stream nominations into temporary SQLite storage with a 16-MiB page cache and
file-backed temporary storage. Keep only occurrence metadata and review memberships
in memory; memory does not grow with the number of nominations. No oversized block
is expanded into pairs. Disk space is required for the scratch database and final
pair JSONL (several GB for the existing approximately 957-MB input). Scratch storage
is removed after a successful export; original files are never deleted.

The unordered pair key hashes the sorted **exact occurrence IDs** and identifies
only a diagnostic pair, never a canonical entity. Each pair retains its one or two
original directed nominations, individual view scores, nomination views, scope,
references, original JSONL line numbers and raw-line hashes. Repeated nominations
in the same direction are an error. Missing endpoints, altered references/text
hashes, invalid scores or scope/class conflicts stop processing. There is no label
matching, transitive union, retargeting or automatic evidence repair.

Counts use unique unordered pairs, with directed totals and reciprocal pairs
reported separately. Report scope, exact ontology class, explicit source-family
pair, union of nomination views, and existing review status. Directed per-view
nomination overlap is also reported, so reciprocal one-view nominations are not
mistaken for a single two-view nomination. Scores retain their original values;
descriptive moments/histograms cover directed scores and arithmetic means within
unordered pairs, globally and by scope. Bins are descriptive, not identity thresholds
or calibrated probabilities. Floating-point endpoint roundoff is clipped only for
histogram placement, never in preserved scores.

## Exact prior-status reconciliation

Use exact memberships from the 43 pilot cases, explicit batch-01 approved subsets,
the existing identifier/lexical queue inventory and reserved sample, and all saved
candidate-block memberships (including oversized blocks). Primary status precedence:

1. Both occurrences in the **same explicit approved subset**.
2. Both in the same prior pilot case (co-reviewed context, not necessarily a
   pair-specific judgment or approval).
3. Both in the same reserved queue block.
4. Both in the same existing ordinary review-queue block.
5. Both in the same existing candidate block.
6. New pair relative to these pinned authorities.

Preserve all co-occurring shared memberships and each endpoint's memberships; the
primary status never replaces them. A–B and B–C approvals do not approve A–C.
Endpoints separately reviewed or approved elsewhere do not make their pairing
reviewed or approved. "New" means no shared explicit membership above, not
scientific novelty or proof that no other possible review exists. Unexpanded
candidate-block co-membership conservatively excludes a pair from the new shortlist
without claiming that it has received human review.

## Bounded diagnostic shortlist

Default maximum: 24 new pairs, configurable up to 48. This is **post-retrieval,
purposive diagnostic selection**, not a random population sample, adjudication or
accuracy evaluation. For each scope/class/family-pair/challenge stratum, retain a
stable-hash representative and the largest absolute name-versus-evidence score-gap
candidate (stable-hash tie-break). From this bounded pool, round-robin over the
three scopes, preferring underrepresented classes, family pairs and challenge
categories, then fewer reused endpoints and stable hashes. Report empty strata or
fewer available pairs honestly; do not fill them with old pairs.

Challenges include differing structured version metadata, weak/label-only context,
multiple labels and short labels. These flags request investigation; structured
metadata is not automatically a release identifier. Preserve exact version and
granularity fields, selected literal evidence with original offsets/hashes, and
pointers to the complete original evidence. Repeated quotations or mirrored sources
are not independent confirmation. The existing ontology decision gate and unresolved
referent/implementation/version cases remain unchanged.

## Execution and handoff

Bounded implementation checks verified 873 input hashes, 280 embedding receipts,
13,528 eligible occurrences and 256 authentic nominations. The pinned retrieval
summary reports 630,849 directed nominations: 225,903 between families, 235,185
within a family/between artifacts, and 169,761 within an artifact. These are input
counts, not computed unordered-pair or new-pair totals. Full reconciliation is left
to the researcher terminal because it scans and indexes the large JSONL.

From repository root, in the existing environment (no new dependencies):

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_retrieval_reconciliation --output var/study2_step14/retrieval-reconciliation/v1 --shortlist-size 24
```

Refuse an existing output directory; use a new version for another run. Outputs:
`pairs.jsonl` (large local detail), `shortlist.json` (bounded evidence cases),
`summary.json`, `summary.md`, and `manifest.json` (exact pins). Share only
`summary.json`, `summary.md` and optionally `shortlist.json` for initial review.
A completed manifest marks a finished reconciliation; do not interpret incomplete
output as a completed result. No provider client or credential loader is invoked.
