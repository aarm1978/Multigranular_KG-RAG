# Step 14 final relation closure

The pre-production population under `var/study2_step14/relation-closure/v1/` contains 2,195 disjoint identity groups (8,911 occurrences) and 104 unique directed relation predictions. The identity and relation ledgers supply separate unsampled populations for independent evaluation. The identity ledger identifies all 29 historical approvals and retains their original approval records. Automatic predictions have no human verification.

## Replay and provenance

The consumer verifies the prepared requests, Batch input, returned provider bodies, per-unit copies, and original validator results. It uses the archived v0.1.8 ontology when checking historical closure inputs and the frozen v0.1.9 signatures for final triples. The manifest pins source and output bytes. Each judgment retains its original response text, unit, item index, request-local case, candidate key, and original sides. The candidate key joins to the preparation's `candidates.jsonl` for the original proposals and their supporting records.

Normalization parses explicit alias prefixes before the quotation, including lists and descriptive parentheticals. The bound source excerpt supplies the evidence. The ledger records each original string, resolved alias, scope and binding. The authorized T0018/P2 exception admits O2Q2 only at its original endpoint in the same request. The original validator passed 17 judgments. Of its 204 rejected judgments, 203 resolved with ordinary case-bound aliases and one required that exception. All 221 now have terminal dispositions.

## Scoped supersession and projection

The eight T0117 decisions preserve the 245-member general NWM group. The five T0118 exceptions identify one shared generic occurrence and five different v1.2 baseline occurrences. The supersession records the earlier six-member group, the reduced five-member proposal, the excluded occurrence and its original source provenance, the authorizing decision and the five judgment references. The generic occurrence remains a source-local endpoint outside consolidation.

T0003/P2 predicts a v2.0 release-to-general relation and T0098/P1 predicts a v1.2 release-to-general relation. Both cite the excluded occurrence as their object. Each final triple is projected from the actual cited occurrences on its two original sides. Ambiguous projections, self-relations and incompatible signatures cannot enter the relation population. Deduplication uses ordered projected endpoints and the ontology predicate name, preserving every supporting judgment and its signature. All 104 predictions remain distinct after this operation.

The judgment ledger retains 43 ontology gaps, 61 abstentions, eight mistaken hypotheses and five material exceptions separately from the relation predictions. There are zero residual mechanical failures among the 221 adjudicated cases. The six unbound leads outside the Batch retain their earlier dispositions in the preparation package.

## Offline verification

From the repository root in the Step 14 environment:

```sh
python -m src.evaluation.step14_relation_closure verify
python -m pytest -q tests/test_step14_relation_closure.py tests/test_step14_final_relations.py
```

A fresh replay can be produced with `python -m src.evaluation.step14_relation_closure run --output var/study2_step14/relation-closure/v1-replay`.
