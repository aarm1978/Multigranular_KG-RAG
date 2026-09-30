# Study 2 Step 5 Publication Evaluation Authority v0.1.2

**Project:** Dissertation CS — Study 2
**Authority ID:** `publication-step5-evaluation-authority`
**Authority version:** `0.1.2`
**Status:** **DRAFT — NOT FROZEN**
**Scope:** prospective, unexecuted pooled-evaluation work only

## 1. Prospective supersession and boundary

This draft prospectively supersedes v0.1.1 only for the still-unexecuted complementary
N=6 pooled-evaluation procedure. It neither changes nor reinterprets any frozen
selection, envelope, routing, realization, Human Core, secondary-review, SciERC, or
Step 7 closure artifact. `docs/publication_step5_evaluation_authority_v0.1.1.md` remains
a byte-unchanged historical frozen authority.

This authority defines candidate-conditioned pooled human validation. It does not define
an exhaustive completeness procedure, a separate reviewer role for such a procedure,
an ordering dependency before pool construction, matching against a separately authored
reference, saturation, missed-reference proportions, or completeness statistics.

## 2. Retained evaluation design

The current complementary pooled procedure retains:

- candidate-conditioned N=6 pooled human validation over six distinct primary units;
- conservative source-local deduplication before review;
- system-provenance blinding with necessary source provenance visible;
- one primary expert reviewing all 6/6 units;
- the frozen independent second-review subset for 2/6 units;
- non-generative candidate judgments; and
- the bounded SciERC external scientific-IE anchor in its native schema.

The positive pooled reference is a human-supported subset of candidate assertions. It is
source-local and candidate-conditioned, not exhaustive gold, and remains separate from
Production Acceptance, Human Core scoring, later alignment/consolidation, final KG
assembly, and GraphRAG structural comparison.

## 3. Frozen bindings retained without rematerialization

These controlling records MUST be consumed byte-identically; this draft creates no
replacements for them.

| Role | Frozen binding |
| --- | --- |
| Corrected N=6 selection and envelopes | `data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.2.json`; artifact SHA-256 `ee3b8ec8b1cc931fbcfe03e9659af992d26f6ab6705bebfedd3367d6903d7dce` |
| Corrected routing | `data/curation/papers/m2/publication_v015_routing_migration/publication_v015_corrected_routing_authority_v0.1.0.json`; routing SHA-256 `7a43f371ae9d70573082319ae26e2d2294ff58b1e801da23d662e27a4c01ec62` |
| Frozen 2/6 second-review subset | `data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_subset_freeze_v0.1.1.json`; artifact SHA-256 `2c9371f1893367f89f667aa9e871c970638d33b93e0d7f3f63dfbbf9d08a87e2` |
| Corrected evaluation realization | `data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_realization_freeze_v1.0.0.json`; artifact SHA-256 `5aad26c75be98c759dacb14d31878e3c9c678662198b307d305360e3c9515842` |
| Corrected SciERC adapter | `data/curation/papers/m2/step5_freeze/scierc_external_anchor_adapter_freeze_v0.1.2.json`; artifact SHA-256 `0f68abc78415b0c119ec75340d707dce1a8e0cea0df1e2124d0c5908140c5104` |
| Step 7C closure | `data/curation/papers/m2/human_core_gold/publication_human_core_n5_corrected_evaluation_step7c_closure_v1.0.0.json`; status `FROZEN_CLOSED` |

The selection remains exactly:

```text
pub:18:sec:0002:unit:0001
pub:276:sec:0019:unit:0001
pub:37:sec:0014:unit:0001
pub:46:sec:0006:unit:0001
pub:54:sec:0019:unit:0001
pub:87:sec:0007:unit:0001
```

The independent second-review subset remains exactly:

```text
pub:46:sec:0006:unit:0001
pub:276:sec:0019:unit:0001
```

## 4. Sole Step 8 candidate source

For future Step 8 pooled evaluation, the sole model-generated candidate source MUST be
the six records whose `executionCohort` is `step5_n6` in:

`data/curation/papers/m2/publication_pilot1_corrected_evaluation/publication_pilot1_corrected_evaluation_canonical_predictions_v1.0.0.jsonl`

That file is frozen by the corrected evaluation realization; its SHA-256 is
`e888c4c4c68ede19cb4c65275b96637fd183e64f887d9a649f70e57f98eadb86`.
Only those six `step5_n6` records may enter the pooled candidate layer. The historical
227-request C1 realization remains preserved provenance only and MUST NOT be the Step 8
candidate source.

No second replicate, model, configuration, ablation, historical DEV output, Human Core
record, or human-authored assertion contributes a pooled candidate.

## 5. Candidate layer, deduplication, and blinding

A pooled candidate is a preserved assertion from the bound `step5_n6` cohort that is
processable under its frozen validation and provenance lineage and source-groundable in
its exact corrected envelope. Deterministic Phase B endpoints may support a relation but
are not candidate contributors.

Deduplication is conservative and source-local. Automatic collapse is allowed only for
exact validator-lineage or governed exact node/relation identities already authorized by
the frozen v0.1.1 procedure. Lexical similarity, shared section/publication, ontology
compatibility, and later alignment are not duplicate signals. Unresolved possible
duplicates remain separately reviewable.

Pooled reviewers see opaque item IDs, assertion content, exact source evidence, and
minimum source-unit/context provenance. They do not see model/provider/run/request/output
identity, lifecycle or validator disposition, retry information, confidence, or other
system provenance.

## 6. Human pooled validation

One primary expert reviews every pooled item across all six units. The independently
frozen 2/6 subset receives the specified second review. Reconciliation records judgment
resolution without changing the original candidate.

Permitted ordinary judgments are `supported_as_proposed`, `not_supported_as_proposed`,
and `insufficient_evidence_to_decide`. Duplicate-review groups may record
`same_source_local_assertion`, `distinct_assertions`, or
`insufficient_evidence_to_resolve_duplicate_status`.

Review is non-generative: reviewers MUST NOT repair, rewrite, split, reclassify, relink,
normalize authoritatively, regenerate, or add a candidate. The positive pooled reference
contains only supported assertions originally present in the bound candidate source after
permitted source-local duplicate resolution. Unresolved judgments do not enter it.

## 7. Optional incidental omission observations

During candidate review, a reviewer MAY record an optional structured omitted-assertion
sidecar only for an assertion incidentally noticed in that review. It is descriptive and
non-exhaustive, outside the positive pooled reference, and MUST NOT create a candidate,
change a frozen prediction, trigger resampling, or alter Human Core, Production
Acceptance, SciERC, or KG construction.

The sidecar is excluded from Recall, F1, completeness, saturation, and
missed-reference statistics. It supports no completeness claim.

## 8. SciERC and execution boundary

SciERC remains the frozen corrected thin, benchmark-native external anchor. It retains
its official-source binding, native labels, base LLM, schema-independent configuration,
and prohibition on a CIROH-to-SciERC ontology mapping. It supplies no pooled candidates
and does not change pooled human judgments.

This document authorizes no execution. It does not freeze a new authority, does not
create a freeze record, and does not execute Step 8. Future execution requires researcher
review and explicit authorization of this draft or a later approved successor.
