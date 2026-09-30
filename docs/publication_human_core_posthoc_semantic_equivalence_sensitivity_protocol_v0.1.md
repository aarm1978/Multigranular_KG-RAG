# Publication Human Core Post-hoc Semantic-Equivalence Sensitivity Protocol v0.1

**Status:** secondary researcher-reviewed sensitivity protocol; not a replacement for Step 7B strict evaluation.

## Purpose and boundary

This protocol creates a neutral, read-only review package for the same frozen N=5
Human Core units and C1 predictions used by strict Step 7B v0.1.1. It permits a
researcher to record post-hoc semantic-equivalence judgments for a sensitivity
analysis. It does not change, supersede, recompute, or reinterpret the strict
Step 7B v0.1.1 result, Human Core, C1, routing, Production Acceptance, lifecycle
interpretation, or the frozen amended matching contract.

The strict result remains the primary confirmatory result. This protocol creates
no automatic semantic matches, no rescue rules, no pooled reference, no
adjudication, and no production consequence.

## Review population

The review package must include all strict true-positive pairs, unmatched Human
Core records, and unmatched C1 records in the frozen N=5 `extract_and_evaluate`
scope. C1-only assertions receive a separate source-support review and are never
inserted into, merged with, or used to rewrite Human Core.

## Node equivalence

A researcher may mark a Human Core node and C1 node `semantic_equivalent` only
when all conditions hold:

1. they are from the same frozen source unit;
2. they have the same operational target ID and ontology class; and
3. the researcher judges that they represent the same source-local assertion or
   entity under the frozen target definition and identity policy.

Evidence-boundary differences, including anchored span containment in either
direction, may inform a judgment but are never sufficient by themselves.
Target or ontology-class substitution is not permitted. Correspondence remains
one-to-one in any later sensitivity analysis.

## Relation equivalence

A researcher may mark a Human Core relation and C1 relation
`semantic_equivalent` only when they have the same source unit, operational
relation target, ontology relation type, and direction, and the researcher has
reviewed their endpoints as equivalent. A C1 relation cannot be rescued merely
because its nodes exist.

## Researcher disposition fields

For Human Core/C1 correspondence review, the permitted unset-or-selected values
are:

- `semantic_equivalent`
- `not_equivalent`
- `target_or_class_disagreement`
- `insufficient_to_decide`

For C1-only source-support review, the permitted unset-or-selected values are:

- `supported_as_proposed`
- `not_supported_as_proposed`
- `insufficient_evidence_to_decide`

Optional explanatory codes are restricted to `E1`, `E2`, `E3`, `M1`, `T1`, `T2`,
`R1`, `R2`, `P1`, and `P2`. The package leaves all disposition, code, and note
fields unset; it does not assign meanings or judgments automatically.

## Interpretation

Any completed review is a post-hoc secondary sensitivity artifact. It must report
its denominator and one-to-one correspondence decisions separately, and must not
replace strict Step 7B metrics or create a Step 7C closure record.
