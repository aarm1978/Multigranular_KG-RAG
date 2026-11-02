# Study 2 Step 7 — Corrected Secondary Researcher Judgment Ledger v1.0.0

**Status:** RESEARCHER CONFIRMED — ready for deterministic materialization  
**Researcher confirmation date:** 2026-09-30  
**Source instrument SHA-256:** `c3aefd029973da10b1cccd45b4558f864e9bcc75d55e3d2c5c219b753ec6a03b`  
**Ledger SHA-256:** `122319d188e4ee049ab6414b5bf2424382f0ff00634c003963f2aee3451db757`  
**Repository checkpoint used for the source instrument:** `bb6b934`

## Scope

This ledger is the researcher-confirmed exact decision record for all 356 review items in the corrected Step 7 secondary instrument:

- Pass A — 118 Human Core node correspondence items
- Pass B — 109 corrected node prediction source-support items
- Pass C — 61 Human Core relation correspondence items
- Pass D — 68 corrected relation prediction source-support items

The five exact-key reconciliation corrections identified during consolidation were reviewed and explicitly confirmed by the researcher on 2026-09-30. No decision remains pending researcher confirmation.

Strict Step 7B remains unchanged and primary. Human Core is not rewritten. No provider/model calls are authorized. No Step 7C action is authorized by this ledger. Secondary metrics are intentionally not computed here; Codex may compute them only after deterministic materialization and validation of all 356 judgments and global one-to-one constraints.

## Exact decision counts

### Pass A — node correspondence
- `semantic_equivalent`: 64
- `target_or_class_disagreement`: 7
- `not_equivalent`: 47

### Pass B — node prediction source support
- `supported_as_proposed`: 103
- `not_supported_as_proposed`: 6
- `insufficient_evidence_to_decide`: 0

### Pass C — relation correspondence
- `semantic_equivalent`: 33
- `not_equivalent`: 28
  - explanatory `P1`: 26
  - explanatory `P2`: 2

### Pass D — relation prediction source support
- `supported_as_proposed`: 66
- `not_supported_as_proposed`: 2
- `insufficient_evidence_to_decide`: 0

## Validation completed before materialization

- All 356 instrument review items are represented exactly once.
- All 64 node `semantic_equivalent` selections have exact corrected prediction keys.
- Node semantic selections are globally one-to-one: **64 selected / 64 unique**.
- All 33 relation `semantic_equivalent` selections have exact corrected prediction keys.
- Relation semantic selections are globally one-to-one: **33 selected / 33 unique**.
- Every semantic selection resolves to the same frozen source unit and operational target.
- Every `target_or_class_disagreement` selected prediction resolves to the same source unit.
- `insufficient_evidence_to_decide`: **0** across all four passes.
- The five reconciliation corrections are researcher-confirmed.
- No secondary metric values have been populated in the ledger.
- Step 7C remains unexecuted.

## Researcher-confirmed reconciliation corrections

### 1. `pub:15` — aggregate actor-critic architecture
Human Core has `actor-critic neural network architectures`, but the corrected run has separate `active pair`, `target pair`, `actor network μ`, and `critic network Q` records and no single same-target aggregate prediction.

**Confirmed ledger decision:** `not_equivalent / E3`.

Relations whose Human Core endpoint is the aggregate architecture are consequently `P1`; the two missing `target pair → hasComponent → actor/critic` edges remain `P2`.

### 2. `pub:15` — episodic training structure
The corrected run has no Method prediction for `episodic training structure`; the phrase occurs only inside evidence for another Method prediction.

**Confirmed ledger decision:** `not_equivalent / T1`.

### 3. `pub:16` — ResearchGoal and Conclusion records
The corrected review instrument contains no corrected ResearchGoal or Conclusion predictions for the three Human Core ResearchGoals and one Conclusion. Those equivalences belonged to the historical C1 discussion and cannot be transferred to this stochastic realization.

**Confirmed ledger decision:** all four `not_equivalent / T1`.

### 4. `pub:79` — visualization techniques
The corrected run contains a Method prediction explicitly stating that visualization techniques were included.

**Confirmed ledger decision:** `semantic_equivalent / E2`.

### 5. `pub:79` — `resolves` relation
Human Core uses the `deconstructed and integrated...` assertion as a **Contribution** source endpoint; the corrected relation uses the same content as a **Method** endpoint. Pass A records this node pair as `target_or_class_disagreement / R2`.

Because the frozen relation protocol requires researcher-reviewed equivalent endpoints, the relation cannot be counted as semantically equivalent.

**Confirmed ledger decision:** `not_equivalent / P1`.

## Other researcher-confirmed judgments preserved

- `pub:16` `the water crisis` remains `not_equivalent / T1`.
- The broad `pub:34` training sentence is assigned one-to-one to the `3,213 gages...` DataDescription; the date-only Human Core atom remains `not_equivalent / E3`.
- `pub:79` common-frameworks ResearchProblem remains `not_equivalent / T1`.
- `pub:79` HBV/TOPMODEL case studies remain `semantic_equivalent / E2` to the three-model experiment prediction.
- `NWC Innovators Program → Organization` remains `not_supported_as_proposed / R2`.
- `Paper → mentionsVariable → Variable` versus `DataDescription → mentionsVariable → Variable` remains non-equivalent for correspondence, coded `P1` with a granularity note; the DataDescription-source relations are independently source-supported in Pass D. The extractor's DataDescription source is consistent with the frozen target rule to prefer the local DataDescription source when evidence is contained there.
- Pass B remains 103 supported / 6 not-supported.
- Pass D remains 66 supported / 2 not-supported.

## Materialization gate

Codex should treat the JSON ledger as **authoritative input**, not as a request for semantic adjudication. It must:

1. verify the ledger SHA and bound source-instrument identity;
2. materialize exactly these 356 decisions into a separate versioned researcher-reviewed artifact;
3. validate all selected prediction keys and global one-to-one constraints;
4. fail closed on any mismatch rather than reinterpret a judgment;
5. compute the four frozen secondary metrics deterministically only after validation succeeds;
6. produce a versioned metrics/report artifact; and
7. **not execute Step 7C** in the same task.
