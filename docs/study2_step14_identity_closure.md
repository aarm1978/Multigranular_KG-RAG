# Step 14 identity adjudication closure

The offline consumer consolidates the 115 preserved component v1 partitions, the 42 v2 responses, the earlier occurrence mappings and the 29 exact researcher approvals. Automatic group membership is a semantic prediction. The standing acceptance and independent evaluation policy applies.

## Decision contract

The consumer replays the frozen v2 validator against the original request, alias binding and completed Batch body, comparing each result with its saved receipt. A strict group with a structured `compatible_qualification` can clear the legacy contradictory-citation and external-context reasons when every member has its own supporting citation and qualifying citations resolve. All other reasons survive, including an incompatible class, protected membership change, unsupported strict identity or missing support. The original model rationale, contradictory citations, qualifying citations and their source roles remain available. Failures affect only their own assignment. Abstentions and residual mechanical failures are terminal for this identity stage.

Each occurrence belongs to at most one final group. Only exact agreement retains an affected prior membership. Each supersession identifies the prior target, exact members and their new group or terminal disposition. Historical approvals retain their original authority and materialization restriction. The ontology v0.1.8 D-16 range governs whether an automatic group can supply a provisional endpoint projection.

The typed-relation inventory groups earlier proposals and all v4 typed observations by ordered original endpoints and predicate. Each supporting item retains its validation status and citations. A component lead can identify two different admissible assignments through explicit local occurrence aliases with cited evidence from both assignments. The inventory retains the literal endpoint strings, the occurrences named on each side, and the assignment memberships. A grouped endpoint supplies context for later interpretation. It authorizes neither a predicate nor expansion over its members. Unbound leads and historical leads from superseded v1 partitions are recorded separately.

## Verified closure counts

| Authority or outcome | Groups | Occurrences |
|---|---:|---:|
| Historical exact approvals | 29 | 99 |
| Automatic proposals | 2,166 | 8,813 |
| Combined disjoint memberships | 2,195 | 8,912 |
| Within one artifact | 1,607 | 4,740 |
| Across artifacts in one source family | 396 | 2,181 |
| Across source families | 192 | 1,991 |

The v2 correction recovered three groups covering 34 occurrences. Its 38 complete and four partial partitions contribute 128 groups covering 2,246 occurrences. With the preserved v1 partitions, all 157 components contribute 267 groups covering 3,373 occurrences. Their other 155 occurrences comprise 48 distinct singletons, 102 abstentions and five mechanical failures. The five include two members of a strict group with unresolved ambiguity, two singleton assignments with residual evidence failures, and one occurrence omitted from its partition. The final ledger records 45 superseded prior targets. Five automatic Workflow groups (10 occurrences) and six historical Repository groups (13 occurrences) fall outside D-16's range.

There are 356 distinct directed typed proposals and 85 bound component leads. Among the 44 originally held v2 leads, 36 resolve against already admissible assignments and one more resolves through a newly admissible group. Seven v2 leads remain unresolved. Two historical leads from replaced v1 partitions retain their original held dispositions.

## Reproduce and verify

From the repository root with the Step 14 Python environment:

```sh
python -m pytest -q tests/test_step14_identity_closure.py tests/test_step14_final_components.py
python -m src.evaluation.step14_identity_closure verify
```

The package under `var/study2_step14/identity-closure/v1/` contains the groups, original occurrence mappings, supersessions, component assignments, terminal occurrences, relation inputs, unresolved leads and SHA-256 manifest. The summary reports groups and occurrences by authority, actual source scope, ontology class, exact group size and range compatibility, including their joint distribution. Verification checks the pinned inputs and every output. To reproduce the package in a fresh directory:

```sh
python -m src.evaluation.step14_identity_closure run --output var/study2_step14/identity-closure/v1-replay
python -m src.evaluation.step14_identity_closure verify --output var/study2_step14/identity-closure/v1-replay
```
