# GPT-6.1 Sol — Human Core N=5 post-hoc researcher judgment ledger

**Status:** `RESEARCHER_CONFIRMED_READY_FOR_MATERIALIZATION`. No secondary metric has been computed; no new Step 7C closure.

This is **ChatGPT-assisted researcher confirmation**, not independent human re-annotation of all 373 items. The researcher confirmed grouped recommendations and individually escalated cases.

**Frozen neutral instrument:** SHA-256 `75c8654292df8f9df2b23a1bf6b4c18359ad74d67cac1b1e91da8c552662b8f4` (commit `3ff341e`).

## Decision counts (not secondary metrics)

| Pass | Decisions | Count |
|---|---|---:|
| A — 118 Human Core node correspondences | semantic_equivalent / not_equivalent / target_or_class_disagreement | 78 / 30 / 10 |
| B — 127 GPT-6.1 node predictions | supported / not_supported / insufficient | 120 / 7 / 0 |
| C — 61 Human Core relation correspondences | semantic_equivalent / not_equivalent P1 / not_equivalent P2 / target_or_class_disagreement | 41 / 17 / 2 / 1 |
| D — 67 GPT-6.1 relation predictions | supported / not_supported / insufficient | 65 / 2 / 0 |

## Reconciliation

- All 373 exact reviewItemIDs and source record keys exist in the neutral instrument.
- 78 distinct selected node predictions and 41 distinct selected relation predictions; no selection reused.
- Exact source unit, target, class/type and relation endpoints validated against the proposed Pass A equivalence map.
- One context-only GitHub repository endpoint checked by target and label; it is not added to scored node support.
- One strict node true positive was rejected semantically because the same composite GPT-6.1 DataDescription is assigned to the 3,213-gages reference instead of the temporal sub-assertion. Frozen strict scoring remains unchanged.
- Pass B supersedes **only** the original National Weather Service citation proposal: `supported_as_proposed`, per researcher confirmation.
- No matched relationship relies on a prediction rejected in Pass D; no node correspondence uses a prediction rejected in Pass B.

## Next action

Use Codex only to deterministically materialize these **exact researcher-confirmed ledger decisions** against the frozen GPT-6.1 instrument, call the original one-to-one validator, and compute the four frozen secondary metrics. Do not re-adjudicate, call an LLM, modify strict results or reopen Step 7C.
