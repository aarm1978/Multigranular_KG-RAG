# Study 2 Step 11 — Semantic contract acceptance

**Researcher approval date:** 2026-10-08
**Status:** FROZEN_CLOSED
**Authority ID:** `study2-step11-semantic-contracts/v0.3`

## Exact approved authority

| Field | Accepted value |
|---|---|
| Contract | [`docs/study2_step11_source_specific_semantic_contracts_v0.3.md`](../study2_step11_source_specific_semantic_contracts_v0.3.md) |
| Version | v0.3 |
| Byte count | 51,901 |
| SHA-256 | `d5d32c1d7662fb581901dbbd1129e99a7216a845782a025d642cfba083ed47f3` |
| Binding scope | HydroShare, GitHub, and CIROH Hub semantic extraction contracts |
| Controlled vocabulary | `ciroh-repository-purpose/1.0.0` |
| Prospective ontology | v0.1.6, formally frozen |
| Validated OWL SHA-256 | `6ebf7f67f79d8aae4fada176911ed9311964beb567f40a097af9017f1ad9c730` |

The approved contract was extracted byte-for-byte from the sole member of
`STUDY2_STEP11_V03_CODEX_FREEZE_INPUT.zip`. This researcher acceptance supersedes
its preapproval “NOT FROZEN” and final-approval review-candidate wording, including
statements that approval or freezing authorization is pending. The approved bytes
remain unchanged. The contract is now binding within the scope above; its future
implementation requirements do not authorize execution in this administrative task.

The accepted controlled vocabulary is the exact six-category scheme, stable node-ID
format, and provenance policy in contract §7. Vocabulary acceptance does not
materialize nodes or establish repository-specific `hasPurpose` assertions.

## Preservation and execution boundaries

This documentation-only freeze changes no ontology, Phase A/B implementation or
contracts, deterministic graphs, Publication v0.1.5 authorities, or accepted Steps
7–9 artifacts. Historical identities, hashes, evidence, and evaluation decisions
remain preserved. Ontology validation retains the scope and import limitations in
[formalization §12](../ontology_formalization.md#12-study-2-step-10-additive-amendment-016-formally-frozen).

D-26 `mentions` remains pipeline-derived, never a model-authored fallback.
`DataService`/`servesDataset` extraction remains inactive; heuristic HydroShare
`data_services` are not verified published-service evidence.

Unresolved `implementsMethod` proposals remain immutable, non-graph records.
Read-only endpoint reconsideration becomes eligible only after accepted full-corpus
Publication semantic production supplies stable A-P13 Method occurrences. Any
materialization requires the separately authorized Step 14 resolution/validation
gate and an explicitly supported, uniquely identified accepted Method endpoint;
this freeze neither resolves proposals nor backfills historical outputs.

## Milestone closure

**Step 11 is CLOSED / ACCEPTED (FROZEN_CLOSED). Step 12 remains pending and requires
separate implementation authorization.** This freeze authorizes no extractor runs,
model/provider calls, corpus audits, graph rebuilds, tests, or semantic redesign.
Only administrative checksum, file-scope, and Git whitespace/staging checks are
performed for this milestone.
