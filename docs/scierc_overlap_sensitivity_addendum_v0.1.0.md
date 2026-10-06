# SciERC boundary-overlap sensitivity addendum v0.1.0

Researcher-authorized supplementary analysis, 2026-10-06, after the official run
and accepted A/B evaluation. This is not predeclared confirmatory evaluation.
Purpose: characterize mechanical boundary discrepancies and possible adaptation
needs, not change the extractor or make semantic judgments. Preserve
`evaluation_decisions.md`, `scierc_postrun_evaluation_v0.1.0.md`, the A/B artifacts,
all original evidence, validators/scorers, extraction settings and Step 8.
This new addendum fixes the following single rule before computation.

## Matching rule

Use A_record_isolation and all 100 frozen gold documents. Keep the strict scorer's
unique-signature item universe and all its supports. Lock every exact match first,
removing those items only from the residual matching problem, never denominators.

Residual entity pairs require identical native type, the same document/sentence,
and a nonempty intersection of inclusive token spans. Score an eligible pair by
intersection-over-union of its token indices. Residual relations require identical
native relation type and positive overlap of each corresponding endpoint, with
all endpoints in the same document/sentence. Direction is preserved; only
COMPARE/CONJUNCTION permit swapping. No endpoint-entity-type requirement is added.
Relation pair weight is mean endpoint IoU for the best eligible orientation.
If both orientations have equal weight, direct precedes swapped; export both.

For each document/layer, select a maximum-cardinality one-to-one residual matching;
among those maximize summed IoU using exact rational arithmetic, then choose the
lexicographically smallest sorted list of (prediction item ID, gold item ID) pairs.
Prediction IDs retain native entity/relation IDs. Gold IDs are full SHA-256 hashes
of the canonical strict signature, prefixed by layer. Stable case IDs hash the
document/layer/category/item IDs; no text-based or performance-based selection.
Lexical preference is implemented by distinct descending binary edge weights as a
secondary exact objective, after rational IoU, within min-cost maximum flow.

Export every eligible residual pair and orientation, including unselected competing
alternatives (not necessarily globally co-optimal). Selection flags distinguish
the chosen solution. Locked exact pairs and every residual unmatched item are
also exported. No threshold search or favorable-example sampling is permitted.

## Separate, overlapping diagnostic flags

Across the entire item universe, flag each entity prediction/gold pair with the
same exact span but different type. For relations flag exact corresponding endpoint
pairs with different labels, and reversed exact endpoints where the predicted or
gold label is directed (distinct head/tail spans). If labels differ, endpoints may
be compared in either exact orientation for diagnosis, without changing matching.
Symmetric-label reversal alone is not a direction discrepancy. Equal endpoint
spans cannot establish a direction discrepancy. A pair can have multiple flags;
report flagged-pair counts by flag and their union, not disjoint error totals.
Flags may also involve already matched items; they are not a confusion matrix.

## Reporting and review boundary

Report strict A and sensitivity entity/relation TP/FP/FN, gold/prediction support,
micro P/R/F1 and additional matches, with no composite. Overlap pairs are mechanical
correspondences, NOT human-validated semantic equivalences or improved extraction.
Review JSONL and Markdown include stable case IDs, sentence tokens/context,
prediction/gold spans and labels, relation arguments, selected/alternative pairs,
flags and unmatched items. Semantic judgment fields remain null/empty. Raw context
and a shareable ZIP stay in a new ignored namespace; tracked artifacts contain only
aggregate results, provenance hashes, code and this addendum. No new annotations,
UI, provider calls, retries, repairs or extraction changes are authorized.
