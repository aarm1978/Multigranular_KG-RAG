# SciERC boundary-overlap sensitivity v0.1.0

Supplementary post-run analysis, not predeclared confirmatory evaluation or improved extraction.
Overlap pairs are mechanical correspondences, NOT human-validated semantic equivalences.
Original A/B metrics, evidence, configuration and decisions remain unchanged. Step 9 remains open.

| Layer/view | TP | FP | FN | Gold | Predictions | Micro P | Micro R | Micro F1 | Additional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| entity/strictA | 827 | 1515 | 858 | 1685 | 2342 | 0.353117 | 0.490801 | 0.410728 | 0 |
| entity/overlapSensitivity | 1042 | 1300 | 643 | 1685 | 2342 | 0.444919 | 0.618398 | 0.517507 | 215 |
| relation/strictA | 394 | 1207 | 580 | 974 | 1601 | 0.246096 | 0.404517 | 0.306019 | 0 |
| relation/overlapSensitivity | 626 | 975 | 348 | 974 | 1601 | 0.391006 | 0.642710 | 0.486214 | 232 |

## Nonexclusive discrepancy flags

{
  "exact_span_different_type": 406,
  "exact_endpoints_different_label": 62,
  "exact_endpoints_direction_reversal": 26,
  "entityFlaggedPairUnion": 406,
  "relationFlaggedPairUnion": 73
}

Counts are prediction/gold pairs, not mutually exclusive error totals. Flags can involve already matched items.
All selected additional pairs and all eligible residual alternatives are in the unjudged review export.
Alternatives are not necessarily globally co-optimal. No semantic assessment or inferred adaptation prescription is supplied.

Rules and exact rational/lexical tie-break: `docs/scierc_overlap_sensitivity_addendum_v0.1.0.md`.
Reproduce offline: `python -m src.extraction.llm.publications.scierc_overlap_analysis`.
Ignored shareable ZIP: `var/scierc_external_anchor/overlap_sensitivity_v0.1.0/scierc_overlap_review_v0.1.0.zip`.
No provider calls, thresholds searched, new reference annotations, or extraction changes.
