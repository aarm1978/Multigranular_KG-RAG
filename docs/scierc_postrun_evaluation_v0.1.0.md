# SciERC post-run evaluation views v0.1.0

Both views are **post-run decisions, not predeclared confirmatory policies**.
The researcher approved the bounded amendment after test-output diagnostics;
see `scierc_postrun_failure_isolation_amendment_v0.1.0.md` and the dated entry in
`evaluation_decisions.md`. No semantic correction or provider rerun occurred.
Starting HEAD: `92c1bec485a3cf8ecfe34cc4525af1eaf13f3d3e`. Step 9 remains open.

## Fixed projections before gold

The gold-blind projection manifest was materialized at
2026-10-06T14:41:41.695467Z, before gold loading and scoring. Its SHA-256 is
`405b63f7d4f78f206bcfb6b6ed3572139b35e19d30c9117c0a3e652795fddbf6`.

| View | Separate ignored projection SHA-256 |
| --- | --- |
| A — amended record isolation | `0f51ad5e98bd8aebec4c3079f8320c2e0b66ebf843db9f23a448bcf987db2d94` |
| B — document-rejection sensitivity | `73627288166ce98bf937299a342ec35ddadb15817bc9a6f04c6aecad1620795f` |

Both files live under `var/scierc_external_anchor/postrun_projections_v0.1.0/`.
Tracked manifests, rejection ledger, preserved-evidence hashes and metrics live
under `data/curation/papers/m2/scierc_step9_postrun_v0.1.0/`. Original requests,
provider responses, model output, approvals, terminals, summary and failures ledger
remain byte-identical, as do smoke evidence and frozen authorities. The unchanged
validator/scorer file hash is
`951e0a295cd19caf9d5d2d35b2fae4fea5b0a3e1a8977942eba2dee4b5b70f9e`.

## Exclusions and retention

| Document | Direct entity exclusions | Dependency relation exclusions | A retained entities / relations | B retained entities / relations |
| --- | --- | --- | ---: | ---: |
| C08-2010 | e11 | r6, r8 | 20 / 9 | 0 / 0 |
| ICCV_2001_47_abs | e1, e18 | r1 | 21 / 11 | 0 / 0 |

A excludes three inconsistent entities and three dependent relations in total.
Every retained field and record order is unchanged. The other 98 documents have
canonically identical original predictions in both views. No other error category
was excluded; all 100 A payloads pass the unchanged full validator. B retains
empty collections for both original document failures without removing documents
or their gold support from scoring. No unresolved validation blocker remains.

## Complete-test results

Scored at 2026-10-06T14:42:32.064532Z against all 100 documents of the exact frozen
test member SHA-256 `7424da64e6214a90e39b09e47a74b3ded57dde86b4a7f848b3625d2c8ecdfbe1`.
Percentages below are rounded for display; full precision is in `metrics.json`.

| View | Layer | TP | FP | FN | Gold support | Prediction support | Micro P % | Micro R % | Micro F1 % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A — record isolation | Entity | 827 | 1515 | 858 | 1685 | 2342 | 35.3117 | 49.0801 | 41.0728 |
| A — record isolation | Relation | 394 | 1207 | 580 | 974 | 1601 | 24.6096 | 40.4517 | 30.6019 |
| B — document rejection | Entity | 810 | 1491 | 875 | 1685 | 2301 | 35.2021 | 48.0712 | 40.6422 |
| B — document rejection | Relation | 387 | 1194 | 587 | 974 | 1581 | 24.4782 | 39.7331 | 30.2935 |

Matching is unchanged: exact global inclusive span + entity type; exact relation
type + endpoint spans, with COMPARE/CONJUNCTION symmetry and all others directed.
Endpoint types are excluded from the primary relation key. There is no composite
score, additional metric, gold-guided filtering, or semantic adjudication.

## Reproduction and checks

Two distinct offline phases:

```bash
python -m src.extraction.llm.publications.scierc_postrun_evaluation project
python -m src.extraction.llm.publications.scierc_postrun_evaluation score
```

Project verifies an existing materialization rather than replacing it. Score
requires both exact projection files and manifest first; it cannot build or alter
them. Versioned writes reject divergence, including replacement of an existing
timestamped metric record. These commands never invoke a runner or provider.

Focused tests: `python -m pytest -q tests/test_scierc_postrun_projection.py` —
**7 passed**. Coverage includes all local mismatches, dependent-edge exclusion,
independent retention, malformed JSON/schema and ambiguous/global error refusal,
errors on otherwise-excluded records, synthetic gold independence and canonical
equality of the original 98 valid documents. An initial test-file syntax typo was
corrected before the passing gate and before gold scoring.

Both metric views are reported regardless of outcome. Test-output exposure and
post-run failure-handling amendment must be disclosed in downstream reporting.
Zero new provider/model calls. Step 8 remains unchanged; Step 9 is not closed.
