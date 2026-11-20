# Final collective overlap audit

At checkpoint 94cc5b7, 2,330 of 2,355 held unique strict memberships had a collective overlap flag. The v4 index includes all proposed strict memberships. The automatic-acceptance amendment describes an overlap between *eligible* groups. To avoid circular eligibility, this audit asks whether a peer had any admissible appearance and passed the independent pre-competition guards in the saved reconciliation ledger. Earlier tie/superset outcomes are downstream. A peer can itself have competitors.

| Scope | At least one eligible peer | Admissible peer(s) but none independently eligible | Only review-required peers |
|---|---:|---:|---:|
| Within artifact | 683 | 12 | 5 |
| Within family across artifacts | 1,060 | 6 | 1 |
| Cross-family | 562 | 1 | 0 |

These columns partition the 2,330 flags. Of the 25 groups without an eligible collective peer, ten have independent reasons for holding the group itself. Fifteen are held solely at the collective gate by ineligible competition, including five of the six with exclusively review-required peers. Twelve of the fifteen also intersect a differing earlier complete candidate with saved support and unprotected membership. The sensitivity retains all twelve without adjudicating precedence. Filtering only review-required peers adds zero uncontested groups. Filtering all independently ineligible peers adds three groups (13 occurrences), all within artifact. This is an additive, conservative sensitivity with earlier v1 proposals fixed, not an optimization or a new acceptance decision.

Among 225 recovered appearances blocked only by competition, 223 had an eligible competitor. Among 49 blocked by competition and opposition, 47 had an eligible competitor. In both cohorts the other two had mechanically admissible but independently blocked peers. In within-artifact / within-family cross-artifact / cross-family order the cohorts split 104/86/35 and 19/26/4. The 11 displaced unique groups split 6/4/1 by scope. Seven had competition alone, one competition and opposition, and three opposition alone. Six had eligible competitors, two had exclusively review-required competitors and three had no competitor. All eleven remain held in the sensitivity.

Prior opposition occurs in 68 groups: 3 with a prior different-entity pair, 16 with pair-level conflict citations, 53 with contextual contradictory citations and 5 with related-nonidentical assessments (overlapping counts). Four groups have internal proposed D-27 links. The ledger reports zero independently established structured granularity conflicts in this already mechanically admissible population. A version proposal or contradiction citation is evidence of scientific disagreement, not a verified incompatible release. Separately, 12 groups encounter held strict opposition with ambiguous external evidence and three with contradictory identity evidence.

Singleton distinct opposition touches 228 groups. Every cited distinct occurrence and at least one other group member shared its originating request; the implementation applies the resulting pair hold across windows. Only four groups have a distinct item citing evidence owned by another group member. Co-presentation establishes the comparison context, not a verified pair-specific difference. Retain the local comparison as an unresolved warning; the audit neither converts it to global negative truth nor erases it as a safeguard.

**Recommendation.** Freeze v1 at 1,355 groups and 3,777 occurrences. If prospectively authorized, restrict the overlap index to complete memberships passing independent safeguards while retaining every excluded alternative as a provenance-bearing warning. The sensitivity reaches 1,358 groups and 3,790 occurrences, with no between-artifact gain. There is no evidence here to justify relaxing scientific opposition or opening another review round.

Reproduce the count-only audit from the repository root:

```bash
python -m src.evaluation.step14_collective_overlap_audit
```
