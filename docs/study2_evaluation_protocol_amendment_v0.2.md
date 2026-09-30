# Study 2 Evaluation Protocol Amendment v0.2

**Status:** **DRAFT — NOT FROZEN**; prospective current architecture
**Scope:** Study 2 Publication semantic-extraction evaluation architecture

## 1. Prospective amendment boundary

This amendment supersedes v0.1 only for future, unexecuted evaluation architecture. It
does not alter frozen Human Core selection, annotation, reliability, matching, corrected
N=6 selection/envelopes/routing, corrected evaluation realization, secondary-review
subset, SciERC binding, or Step 7 closure. It does not rerun or rematerialize frozen
artifacts.

## 2. Current architecture

The current Study 2 architecture has five distinct components:

1. **Human Core N=5:** frozen bounded, model-blind, source-grounded human reference.
2. **N=2 reliability:** frozen independent reliability subset under its existing boundary.
3. **Complementary candidate-conditioned N=6 pooled validation:** one primary expert
   reviews eligible candidates from the six frozen corrected selected processable
   `step5_n6` provider attempts; frozen 2/6 units receive independent second review.
   Judgments are non-generative, source-local, and provenance-blinded.
4. **Optional non-exhaustive omission observations:** sidecar observations only when
   incidentally noticed during candidate review; descriptive, outside the positive pooled
   reference, and excluded from Recall/F1 and completeness-related statistics.
5. **SciERC external anchor and GraphRAG:** SciERC is benchmark-native; GraphRAG is
   structural comparison only, never a correctness baseline.

The N=6 candidate source is solely the six selected processable `step5_n6` provider
attempts bound by the frozen corrected evaluation realization and preserved raw/validation
provenance. Its canonical prediction JSONL is the frozen accepted-semantic projection and
provenance authority, not a narrowing rule for otherwise eligible pooled candidates. The
historical 227-request C1 realization is preserved provenance and is not the N=6 candidate
source.

## 3. Pooled-reference boundary

The pooled positive reference is a human-supported subset of pre-existing model candidates
after conservative source-local deduplication and blinded, non-generative human review.
It is not exhaustive gold. No standalone exhaustive/model-blind completeness procedure,
separate completeness-review role, or pre-pool ordering requirement is part of this
architecture. No audit-to-pool matching, saturation, missed-reference proportion, or
completeness statistic is a current evaluation procedure.

## 4. Status

| Component | Status | Boundary |
| --- | --- | --- |
| Human Core N=5 and N=2 reliability | **FROZEN/CLOSED** | Existing frozen authorities retain control. |
| Corrected N=6 selection, envelopes, routing, realization, and 2/6 subset | **FROZEN/CLOSED** | Consumed unchanged by future pooled validation. |
| Pooled validation architecture | **DRAFT — NOT FROZEN** | Requires researcher review before Step 8. |
| SciERC corrected adapter binding | **FROZEN/CLOSED** | Separate benchmark-native external anchor. |
| GraphRAG | Current boundary | Structural comparison only. |
