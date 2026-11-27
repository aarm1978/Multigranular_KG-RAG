# Residual identity closure and final relation Batch

The ignored package is `var/study2_step14/residual-relations/v1/`. The consumer verifies the original submission, provider bodies, 262 per-unit raw responses, exact partitions and saved item-level receipts. The prior relation closure remains the comparison baseline. The new ledger contains 2,088 automatic groups covering 9,820 occurrences and 29 protected exact approvals covering 99 occurrences. No confirmatory sample has been drawn.

## Membership decisions

Start with prior scopes touched by an abstention or mechanical failure. Preserve each such scope as a whole. An otherwise admissible strict assignment that crosses a preserved boundary is blocked as a whole. Preserve any additional prior memberships this blocks from receiving their proposed replacements. Repeat until the preserved set stops changing. Unrelated valid assignments in the same component remain eligible. Exact historical memberships remain locked. This procedure propagates preservation constraints only; it cannot infer strict identity.

Of 483 mechanically admissible strict assignments, 461 remain eligible and 22 conflict with preserved memberships. The original 93 distinct singletons, 142 abstentions and 43 mechanically unresolved occurrences retain their assignment dispositions. The supersession ledger identifies 384 changed prior scopes, each supporting source item and the resulting target or unconsolidated state of each original member. New memberships carry the automatic-prediction authority and references to the model assessments. Unaffected prior memberships retain their evidence and authority.

The exceptions ledger retains the exact assessment, semantic conflict category and citation roles for every reported material conflict. Four preserved prior groups carry an explicit production consistency hold: X0001, X0002, X0040 and X0076. They are included in the comparison population of 2,117 groups and 9,919 occurrences. Their original evidence and the incompatible or ambiguous assessment remain available together. A hold prevents treating preservation as clearance to materialize that group.

## Pair coverage

Counts describe the 73,416 original occurrence pairs. The last column counts pairs outside identity in both ledgers. The 382 newly separated pairs also enter relation consideration.

| Original recommendation | Retained identity | Newly identity-aligned | Newly separated | Still outside identity |
|---|---:|---:|---:|---:|
| Same entity | 33,982 | 7,833 | 350 | 9,156 |
| Abstain | 2,187 | 767 | 27 | 10,173 |
| Different entities | 3 | 18 | 0 | 3,962 |
| Shared reference | 414 | 62 | 5 | 2,540 |
| Conceptual similarity | 97 | 2 | 0 | 1,838 |
| **Total** | **36,683** | **8,682** | **382** | **27,669** |

| Actual scope | Retained identity | Newly identity-aligned | Newly separated | Still outside identity |
|---|---:|---:|---:|---:|
| Within artifact | 14,573 | 4,779 | 52 | 7,433 |
| Across artifacts within a family | 16,258 | 3,082 | 254 | 15,877 |
| Across families | 5,852 | 821 | 76 | 4,359 |

The case-by-case ledger and summary also distinguish retained typed alignment. Before this Batch, 45,365 original pairs share an identity, 258 other pairs project onto a retained typed triple in either direction, and 27,793 have no current direct alignment.

## Final relation preparation

Of the 14,226 authorized residual pairs, 7,723 share a resulting identity and 6,503 remain distinct. The latter comprise 940 initially positive, 2,304 abstaining and 3,259 different-entity pairs. All 6,503 enter the ledger with their original endpoints, assessment, evidence and provenance. They project to 2,428 distinct unordered pairs. The 382 newly separated pairs contribute six further distinct pairs.

A previously admissible lead is narrowed to the original cited occurrences on each bound assignment side. Both witness sets must project unambiguously. A previously unresolved lead needs explicit local aliases, two distinct unambiguous endpoints and cited support on both sides. Of the 148 admissible leads, 146 bind under the new memberships. Of the 31 previously unresolved leads, 20 bind. All 13 remaining ambiguous leads retain their source records. The admissible leads add 21 distinct pairs beyond the residual-only 2,428. Counts from different discovery routes overlap.

All 104 previous typed predictions were reprojected from their cited occurrences. Fifty changed and are sent for targeted reassessment, preserving predicate, direction and original witness sets. The remaining 54 distinct triples retain support under the same memberships. The final union contains 2,492 cases in 891 gpt-6.1-sol requests in one Batch shard. Source-local evidence and v0.1.9 signatures govern each directed judgment. Gaps and abstentions are permissible. Retrieval retains raw model strings and validates each item's normalized explicit citations against its own case and both endpoint bindings.

The planning estimate is 1,818,455 input and 801,200 output tokens, approximately USD 6.28 at the prior Batch rates (USD 1.25 and 5 per million). At the summed output caps of 4,376,576 tokens and estimated input usage, the scenario costs USD 24.16. Actual usage will come from provider receipts.

## Researcher terminal

From the repository root in the Step 14 environment:

```sh
python -m pytest -q tests/test_step14_residual_relations.py tests/test_step14_residual_alignment.py tests/test_step14_final_relations.py
python -m src.evaluation.step14_residual_relations verify
```

For separately authorized execution, submit the single shard once, check status and retrieve after it reaches a terminal state:

```sh
python -m src.evaluation.step14_residual_relations submit --shard 1
python -m src.evaluation.step14_residual_relations status --shard 1
python -m src.evaluation.step14_residual_relations retrieve --shard 1
```

A fresh offline reproduction uses `python -m src.evaluation.step14_residual_relations prepare --root var/study2_step14/residual-relations/v1-replay`.
