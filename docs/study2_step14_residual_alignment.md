# Step 14 bounded residual alignment extension

The comparison baseline is `relation-closure/v1` at commit 1967b1e. The ignored preparation under `var/study2_step14/residual-alignment/v1/` contains the complete initial coverage audit, residual-pair ledger, component inventory, Batch requests, reversible source bindings and baseline relation recheck list. Each residual row retains the original pair key, recommendation, source and evidence pointers, prior assessments and request routing.

## Pair population

For each of the 73,416 validated initial recommendations, project each original occurrence onto its final identity group, falling back to the occurrence itself. Direct alignment means common identity membership or an existing directed relation between the two projected endpoints in either direction. For joint presentation, intersect request postings for the **original occurrences**. The comparison uses the alignment workflow, collective requests and both complete-component rounds. A shared request identifies the evidence shown together. It does not establish an explicit pair judgment.

This definition reproduces 8,141 positive, 2,810 abstention and 3,275 different-entity pairs. The earlier exploratory anchor pilot also saw three of these pairs. Its saved assessments explicitly grouped one as strict identity and two as related nonidentity. Including that pilot in the exclusion would give 8,140, 2,810 and 3,273 respectively. The authorized extension retains the specified population and records these three assessment references separately.

| Pair scope | Residual pairs |
|---|---:|
| Within artifact | 7,716 |
| Across artifacts within a family | 5,309 |
| Across source families | 1,201 |

The single-family counts are Publications 12,802, GitHub 104, CIROH Hub 103 and HydroShare 16. Between families, Hub–Publications contributes 523 pairs, GitHub–Publications 513, Hub–GitHub 130, HydroShare–Publications 25, Hub–HydroShare 6 and GitHub–HydroShare 4. These 14,226 pairs cover 5,166 distinct original occurrences and 2,899 baseline referents.

## Prepared identity Batch

The 10,951 positive or abstention hypotheses nominate 3,229 occurrences and 6,825 distinct unordered pairs among 1,862 projected referents. Projected connectivity defines a joint adjudication question. Complete prior membership expansion gives 4,644 input occurrences in 262 disjoint components. All 571 affected automatic groups are supplied as hypotheses. The 13 touched exact researcher-approved scopes are supplied as locked boundaries; the other 16 approvals lie outside the requests. A member outside the unified queue uses its earlier saved literal-window projection with the original occurrence hash checked.

There are 151 components of size 2–12, 67 of size 13–24, 39 of size 25–100 and five larger ones. The largest have 325, 315, 124, 117 and 112 members. The summary contains the exact histogram and unit IDs. Every identity candidate is included jointly in one complete request. No component required subdivision.

The model partitions original occurrences and may return multiple strict groups, singleton distinctions, terminal abstentions and optional evidence-bound leads. Validation reuses structured qualification handling and direct-member evidence checks. Explicit evidence aliases may carry quotation text; resolution uses the request namespace and preserves the model-authored item. Granular validity never joins identities across components. Supersession records identify the old target, complete old membership and replacement assignment indices. A partial partition or abstention affecting a proposed change cannot silently replace a prior target. Preserve unaffected memberships and all historical approvals when forming the subsequent disjoint ledger.

Using observed whole-component v2 input-token/byte and output-token/member rates gives 924,806 estimated input tokens and 243,730 expected output tokens. The adaptive caps sum to 2,325,504 output tokens. At the preceding Batch assumptions of USD 1.25 and 5 per million input and output tokens respectively, the estimates are USD 2.37 expected and USD 12.78 with all output caps consumed at estimated input usage.

## Subsequent typed-relation pass

1. After retrieval, validate the complete partitions, record each supersession and construct the updated occurrence lookup. Retain granular failures and check final disjointness, locked memberships and the frozen v0.1.9 representation constraints. Preserve prior targets wherever competing or incomplete replacements prevent a consistent update.
2. Route every initially different-entity pair to relation consideration and every positive or abstention pair whose original endpoints still project apart. Add bound nonidentity leads independently. Retain original occurrence evidence and context; report unresolved or internal projections separately. Identity disagreement alone supplies no relational evidence.
3. Reproject **every supporting judgment of all 104 existing predictions** using its actual cited original occurrences and directed sides, as in `step14_relation_closure.triple`. The recheck inventory flags 72 predictions touching a candidate referent in this Batch. Compare old and new triples, preserve all support and record any supersession. Suppress self-loops and hold sides with ambiguous projections. Never distribute one judgment across all possible replacement groups.
4. Aggregate residual cases by the updated unordered referent pair while preserving original directions and support. Compare with saved adjudicated cases, including gaps and abstentions. Reuse an earlier outcome for the same evidence, endpoints and scientific question. Changed projection, new source evidence or a distinct relational hypothesis requires explicit accounting. Use the final-relations packer, compatible directional v0.1.9 signatures and granular relation-closure validation for the remaining cases. This is a single bounded follow-up; there is no recursive discovery or evaluation sampling.
5. With today's memberships and before new leads, the residuals project to 8,550 candidate relation pairs. Five overlap previously adjudicated referent pairs. Provisionally setting those five aside and applying the earlier five-referent packing gives 2,155 requests. This scenario can change with identity outcomes, new leads and the evidence-level reuse check. No typed requests have been constructed.

## Researcher terminal

Run from the repository root in the Step 14 Python environment.

```sh
python -m pytest -q tests/test_step14_residual_alignment.py tests/test_step14_final_components.py
python -m src.evaluation.step14_residual_alignment verify
```

For the identity Batch, submit once, check its status, then retrieve after it reaches a terminal state.

```sh
python -m src.evaluation.step14_residual_alignment submit
python -m src.evaluation.step14_residual_alignment status
python -m src.evaluation.step14_residual_alignment retrieve
```

A fresh offline reproduction uses `python -m src.evaluation.step14_residual_alignment prepare --root var/study2_step14/residual-alignment/v1-replay`.
