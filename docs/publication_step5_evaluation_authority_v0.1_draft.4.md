# Study 2 Step 5 Publication Evaluation Authority v0.1

**Project:** Dissertation CS — Study 2
**Workstream:** Publication semantic extraction and evaluation
**Authority ID:** `publication-step5-evaluation-authority`
**Authority version:** `0.1.0-draft.4`
**Status:** **DRAFT — NOT FROZEN**
**Date:** 2026-09-25

## 1. Successor and incorporation rule

This is the fully bound successor to `docs/publication_step5_evaluation_authority_v0.1_draft.3.md`.
All normative methodological content in draft.3, including Sections 1–19 and decisions
5A–5G, is incorporated unchanged. This successor adds only the deterministic freeze-time
materialization authorized by draft.3 Sections 15 and 17 and the approved C1
context-budget binding below. It does not freeze or close Step 5 and does not authorize
C1 execution, pooled adjudication, completeness audit, audit↔pool comparison, or SciERC
inference/scoring.

## 2. Freeze-time artifact register

All paths are repository-relative. File SHA-256 hashes cover canonical tracked artifact
bytes, including their terminal LF.

| Artifact | Path | SHA-256 |
| --- | --- | --- |
| Complementary N=6 selection | `data/curation/papers/m2/step5_freeze/publication_pool_n6_selection_freeze_v0.1.0.json` | `4839bcef9293f3d50ae1c80f10464a138a3f2d505c36388d3c945be0e86af3e3` |
| C1 evaluation envelopes | `data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.0.json` | `626d89687baa9eefad0a3398495fd8eb67bae3afe14bbd13473f88cf2c2c7a04` |
| Bounded second-review subset | `data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_subset_freeze_v0.1.0.json` | `515642a5c19ef58b3bc690c9c7a49552cc9b2fed6031aef2491af248c0ce58a7` |
| Role/exposure ledger schema | `data/curation/papers/m2/step5_freeze/publication_step5_role_exposure_ledger_schema_v0.1.0.json` | `c42fc3020e56e626c2e372c626ccbc63bb427bb171d1c5174886c6b7c9ff4b00` |
| SciERC source/split binding | `data/curation/papers/m2/step5_freeze/scierc_external_anchor_source_freeze_v0.1.0.json` | `47869e3c724ed3eee35319dd860ac7b0e032deed0b1d4d5a27da52dac8018f7c` |
| SciERC adapter/configuration binding | `data/curation/papers/m2/step5_freeze/scierc_external_anchor_adapter_freeze_v0.1.0.json` | `d68cba4baf3c40cc90297fce51fa1f5458cacd73305dbd38908ef48b2fff5016` |

The materializer is `src/extraction/llm/publications/step5_freeze_materialization.py`.
It makes no network or provider/model call and fails closed if an envelope’s conservative
input bound exceeds its authorized budget.

## 3. Complementary pooled N=6 and second-review subset

The approved model-blind N=6 result is reused without semantic re-audit:

```text
pub:18:sec:0002:unit:0001
pub:276:sec:0004:unit:0001
pub:37:sec:0016:unit:0001
pub:46:sec:0030:unit:0001
pub:54:sec:0019:unit:0001
pub:87:sec:0007:unit:0001
```

The selection artifact preserves the established one-unit-per-paper, 19/19 routed
scored-node, 16/16 routed scored-relation, and 5/5 stratum proof; its minimax exposure is
15, total exposure is 59, and the final tie-break is lexical `sourceUnitID` ordering.

The Section 6.6 selector is exactly
`publication-step5-pooled-second-review-selector-v0.1.0`. Its complete digest ranking is
in the subset artifact. The selected independent second-review units are:

```text
pub:46:sec:0030:unit:0001
pub:37:sec:0016:unit:0001
```

## 4. C1 evaluation-envelope context and configuration binding

```text
contextPolicyName = complete_section_when_budget_allows
contextPolicyVersion = 0.1.2
modelContextWindowTokens = 1050000
maxOutputTokens = 32768
modelContextBudgetTokens = 1017232
estimatedInputTokensMethod = utf8_byte_upper_bound_v0.1.0
```

`estimatedInputTokens` is the UTF-8 byte count of the exact canonical non-secret
Responses request body. It is a conservative upper bound, not exact provider tokenization.
The envelope materializer fails closed when that bound exceeds `1017232`.

Each primary is the sole canonical unit in its section. Applying the frozen source-unit
policy mechanically yields `includedCompleteSection = true`, empty `contextSourceUnitIDs`,
empty `omittedEligibleSourceUnitIDs`, and
`contextSelectionReason = singleton_primary_section_complete` for all six envelopes. No
semantic context is added.

C1 uses OpenAI, `gpt-5.6-sol`, `medium` reasoning effort, `32768` max output tokens,
`store = false`, no tools, no web/retrieval, strict structured output, authority bundle
`publication-semantic-v0.1.5-schema-v0.1.3`, and provider schema
`publication-request-specialized-0.5.0`.

## 5. Role/exposure and information-flow binding

The role/exposure schema is an initially empty, fail-closed future execution ledger. It
records a pseudonymous person/role, primary evaluation unit, role, pooled-C1 judgment
exposure, audit eligibility, and time. A missing/unknown row or any pooled-C1 exposure
makes the person ineligible to audit that unit. It preserves the incidental-observation
firewall, requires an explicit blinded-projection allowlist, and keeps
`adjudication_unresolved` distinct from `insufficient_evidence_to_decide`.

## 6. SciERC source and adapter binding

The benchmark source is the official UW SciIE processed archive:

```text
http://nlp.cs.washington.edu/sciIE/data/sciERC_processed.tar.gz
SHA-256 bce752fb7ebe4acf570937d76ffb27c239cfc907e477a69075dc7082d0e72e9b
```

The source artifact binds `train.json` (350 documents), `dev.json` (50), and the complete
required `test.json` (100), with exact split hashes. Native labels are preserved exactly:
entities `Generic`, `Material`, `Method`, `Metric`, `OtherScientificTerm`, `Task`; and
relations `COMPARE`, `CONJUNCTION`, `EVALUATE-FOR`, `FEATURE-OF`, `HYPONYM-OF`, `PART-OF`,
`USED-FOR`. `COMPARE` and `CONJUNCTION` are symmetric; the other relations are directed.

The thin adapter binds the same C1 base model and schema-independent reasoning settings.
Benchmark token spans are authoritative document-global zero-based inclusive token spans;
no character-span representation is used. It excludes CIROH mapping/targets, coreference,
training, fine-tuning, retrieval, and manual adjudication. It permits only non-test
mechanical smoke validation before one complete official test run after Step 5 is frozen.

## 7. Freeze-gate state

The Section 15 deterministic bindings are materialized. Final researcher review and
explicit approval remain required before changing status. This document is and remains
**DRAFT — NOT FROZEN**.
