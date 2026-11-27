# Step 14 final offline semantic alignment closure

The pre-production package is `var/study2_step14/final-alignment/v1/`. It consumes the frozen v2 prospective membership overlay, the completed residual Batch and the retained relation judgments. The SHA-256 manifest identifies the original requests, source bindings, native output, per-request responses, historical receipts and final ledgers.

## Relation replay

The replay reproduced all 897 provider responses, 2,520 case judgments and the previous validator's 2,473 passes. The original predictions comprise 167 relations, 496 gaps and 1,857 abstentions. The parser reads explicit aliases at the start of a citation, including individually labeled aliases, conjunctions, punctuation and explicit dash-separated endpoints. It stops at the reproduced quotation or explanatory suffix. Only aliases explicitly listed can support a judgment. Original strings, authoritative source excerpts, exact case ownership and both endpoint bindings remain traceable in the judgment ledger.

The revised dispositions recover one relation, 16 gaps and 28 abstentions. Z00033/P1 remains mechanically unresolved because its abstention cites evidence outside the case. Z00890/P1 remains mechanically unresolved because its gap lacks support for one endpoint. The final residual dispositions are 167 relations, 495 gaps, 1,856 abstentions and two mechanical failures.

Each admissible relation is checked against its original directed signature and the v0.1.9 domain and range. Actual cited occurrences on each side must project to a single, different endpoint on each side. The 167 residual predictions and 54 retained predictions yield 221 unique ordered subject–predicate–object triples: 134 hasComponent, 80 isVersionOf and seven isVariantOf.

## Observed coverage

| Original candidate population | Identity | Typed relation | Without direct alignment |
|---|---:|---:|---:|
| All 73,416 validated pairs | 45,352 | 1,676 | 26,388 |
| Authorized subset of 14,226 residual pairs | 7,723 | 310 | 6,193 |

Each original pair key contributes once. Identity requires both occurrences to project to one final group. A typed relation requires a final triple between their distinct projected endpoints in either direction. Triples themselves preserve direction. The residual row is a subset of the first row. These descriptive counts do not enumerate implied within-group equivalences or estimate population precision or recall. In the pair ledger, `finalAlignment` gives this closure's result and the inherited `currentAlignment` field records the v2 preparation baseline.

## Unsampled populations

- `automatic-identity-frame.jsonl` contains all 2,084 automatic groups (9,809 occurrences), including the largest group of 234. Each entry records exact membership, size, ontology class, source families, scope and pointers to member evidence and the originating decision.
- `historical-approvals.jsonl` separately retains all 29 exact approvals (99 occurrences), their authority and original materialization restrictions. The combined identity population has 2,113 disjoint groups covering 9,908 occurrences.
- `typed-relation-frame.jsonl` contains every final directed prediction. Endpoint sizes count occurrences represented by the projected endpoints; an unconsolidated source occurrence has size one. Evidence scope is measured on the actual cited endpoint witnesses. Each support entry identifies its case, source bindings, signature, direction and citations. The occurrence provenance ledger joins on the exact occurrence ID.

These are complete pre-production frames. Independent evaluation design and sample selection remain pending.

## Offline verification

From the repository root in the Step 14 Python environment:

```sh
python -m src.evaluation.step14_final_alignment verify
python -m pytest -q tests/test_step14_final_alignment.py tests/test_step14_relation_closure.py tests/test_step14_residual_relations.py
```

A fresh replay can be generated with `python -m src.evaluation.step14_final_alignment close --output var/study2_step14/final-alignment/v1-replay`.
