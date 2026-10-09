# CODEX_HANDOFF.md

> **Tracked operational checkpoint (development repository).**
> This document records the current implementation state and next workstream.
> It is not a methodological authority; frozen contracts and acceptance
> records remain authoritative. Update only at meaningful milestone
> transitions. Do not include secrets or private runtime information.

## Current checkpoint

**Study 2 Step 12A — CLOSED / ACCEPTED by the researcher, 2026-10-09.**
**Packages 1–3 complete. Next workstream: Step 12B focused integrated validation.**
Accepted implementation checkpoint: `7abba6faa79867992870bf405e4c8768cb67cb14`
on `codex/publication-human-core-annotation-ui`.
Acceptance: [Step 12A technical integration acceptance](../handoffs/STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md).
Closure establishes offline technical integration only, not demonstrated semantic
correctness, contextual completeness, KG acceptance, full-corpus extraction or
provider authorization. No context-selection policy is introduced. This closure
is documentation-only; prior test results below were not rerun or re-audited.
The unrelated `src/ontology/catalog-v001.xml` modification remains local.

Package 1 completed at `2d6c3022e627cb148234858cc881d0463d797be4` with
29 focused synthetic T1/T2 checks: caller-verified HydroShare README authorities,
GitHub descriptive-source/literal evidence interfaces, and Hub displayed-fence
binding solely as possible Example context. Acquisition/enrichment stays deferred.

Package 2 now provides source-specific batch candidate validation for every frozen
active target: HydroShare at `f2d4ac38c821e376212ed252dc5b0b28d176ebcf`,
GitHub at `66b9832f4f25a9901fff6499f9dbd0e085eca2e3`, and Hub at
`0a1e8c1990fbc62e07229b443ae6aec998f70a1b`.
Existing representative entry points remain compatible. Hub checks exact trusted
endpoints, independent multi-unit evidence, explicit page-local parent-relation
paths, scoped source failures, actual dependencies and duplicate assertions while
preserving original proposals and citations. Example fences remain possible context;
Parameter requires prose context. Parent acceptance and other semantic conditions
remain pending: structural/literal success is never semantic acceptance or KG
permission. No corpus/provider/graph execution occurred.

Hub milestone validation: 19 focused synthetic T1/T2 tests passed (11 candidate
validation tests, including legacy Procedure compatibility; four literal-evidence
and four Example-context regression tests). No broad suites were run.

**Package 3 — complete.** Package 3A at
`fadd2ef79b6a8404280341eb35be33e1729c3422` adds deterministic source-specific
request construction and strict recorded-response parsing; 25 focused tests passed.
Package 3B at `7abba6faa79867992870bf405e4c8768cb67cb14` adds the three
`offline_pipeline.py` adapters and their focused tests. Replay snapshots caller-trusted request inputs, preserves exact
recorded response bytes/hash, links request/contract/source identities, and invokes
the unchanged batch validators with only selected source units. An optional
caller-supplied recorded-request digest is checked; no provider association is
fabricated when it is absent.

Parse-invalid candidates remain unchanged in provenance and are quarantined from
validation; actual dependent references remain for existing validators to resolve
or hold. Independent candidates survive local failures. GitHub's six controlled
seed endpoints are separated from caller endpoints; HydroShare's accepted endpoint
and authorized-stub inventories remain distinct. Frozen report JSON, its hash and
exact response bytes provide immutable replay records; inspection views are detached.
Request-level source completeness remains separate from validator completeness for
the intentionally restricted unit view. Explicit abstentions remain recorded claims
or local errors, never inferred from empty output or source failure. Pending semantic
conditions, unresolved Method/Hub-parent records and duplicate citations are preserved.
Semantic acceptance stays unevaluated and KG authorization stays false.

Package 3B validation: **23 focused synthetic T1/T2 checks passed** (9 HydroShare,
7 GitHub, 7 Hub), covering round trips, hashes/immutability, inventory mappings,
parse/validation failure isolation, selected-unit enforcement, incomplete sources,
duplicate decisions, conditional gates and zero provider/graph effects. No existing
request contract, validator, reader, ontology or Publication component changed.
No broad suites, real-corpus processing, provider calls or graph writes occurred.

**Next workstream:** Step 12B focused integrated validation, with execution scope
to be separately authorized. Step 12C separately approved live pilot, Step 13
production and Step 14 alignment remain distinct later work. Pending semantic
gates and inactive targets remain unchanged; this technical closure authorizes
no live calls, full-corpus extraction, graph acceptance or production execution.

## Frozen methodological checkpoint

**Study 2 Step 11 — CLOSED / ACCEPTED (FROZEN_CLOSED), 2026-10-08.**
Accepted commit: `0e1cd64e8aa2de8e0240e520ee2e30c36a8fcdc5`.
Authority: `study2-step11-semantic-contracts/v0.3`.
Contract: `docs/study2_step11_source_specific_semantic_contracts_v0.3.md`.
Exact approved bytes: 51,901; SHA-256:
`d5d32c1d7662fb581901dbbd1129e99a7216a845782a025d642cfba083ed47f3`.
Acceptance: `docs/handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md`.
The acceptance supersedes the contract's preapproval NOT FROZEN wording without
changing approved bytes. Controlled vocabulary: `ciroh-repository-purpose/1.0.0`.
Remote branch commit and downloaded contract bytes verified after push. Only the
contract and acceptance record were committed. Administrative checks only; no tests,
provider calls, extraction, corpus audits, or graph rebuilding occurred. Git whitespace
checking reported five original Markdown hard-break lines; approved bytes preserved.

## Accepted deterministic baseline

**Bounded post-Step-10 deterministic reference enrichment — COMPLETE / ACCEPTED
on 2026-10-08.** Candidate `10c1227`, corrected baseline `a1f0c3b`.
Acceptance authority: `docs/handoffs/STUDY2_REFERENCE_ENRICHMENT_V1_ACCEPTANCE.md`.
GitHub: 59 C-C27 edges; Hub: 91 C-DC22 edges after three homepage-target removals.
Final cumulative graph: 28,406 nodes / 32,809 edges; inventory-excluded:
15,705 nodes / 19,866 edges. Candidate run: 130 focused tests passed; correction
run: 10 passed. No validation or generation was repeated for this handoff update.
Current hashes: `tests/fixtures/reference_enrichment/prospective_hashes.json`.
Current metrics/trajectory: `results/metrics/`. Scope and prior candidate provenance:
`docs/handoffs/STUDY2_POST_STEP10_REFERENCE_ENRICHMENT_V1.md`; correction evidence:
`tests/fixtures/reference_enrichment/hub_homepage_correction_v1.json`.

**Study 2 Step 10 — CLOSED** at `a2cb542` (2026-10-07).

Branch: `codex/publication-human-core-annotation-ui`.

Accepted scope authority:
`docs/handoffs/STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md`.
The HydroShare, GitHub, and CIROH Hub inspections are complete; do not repeat them.

**Ontology v0.1.6 — formally frozen** at
`b2c735bce9692e8937abcc08c4d9ac48a85b255e`; new prospective TBox baseline.
Validated OWL SHA-256:
`6ebf7f67f79d8aae4fada176911ed9311964beb567f40a097af9017f1ad9c730`.
The 44-test focused ontology suite passed, including reproducibility and saved-output
compatibility. Researcher-confirmed Protégé/HermiT classification passed with no
reported inconsistency or HermiT exception and zero named unsatisfiable classes.
See `docs/ontology_formalization.md` §12 for exact validation scope and import/parser
limitations; do not claim a fully resolved third-party import closure.

## Accepted HydroShare prerequisite

Minimal HydroShare v0.1.6 corrections remain accepted at `269f498`; acceptance
record commit `5cf6422`, document `docs/handoffs/STUDY2_HYDROSHARE_V016_ACCEPTANCE.md`.
15 own DOI Identifier/hasIdentifier pairs, 18 C-D27 contributor alignments and
21 C-D28 funding-agency alignments; relation semantics/endpoints preserved.
Historical/prospective hashes remain in `tests/fixtures/hydroshare/`. Its former
cumulative counts are historical; use the corrected current baseline above.

## Active implementation authority

Step 11 remains FROZEN_CLOSED. Step 12A is CLOSED / ACCEPTED for offline technical
integration under the researcher-approved acceptance record above. Use the frozen
v0.3 contract, its acceptance record and ontology v0.1.6. Step 12B is next;
further execution requires its own authorization. Do not rerun accepted source
audits, corrections, reference enrichment or frozen Publication evaluations.

## Deferred scope and frozen Step 11 boundary

The v0.3 contract binds HydroShare, GitHub, and CIROH Hub semantic extraction design,
including exact target/evidence/abstention rules and the accepted controlled vocabulary.
It does not authorize execution or promise exhaustive extraction. D-26 remains
pipeline-derived. Unresolved `implementsMethod` proposals remain immutable non-KG
records; endpoint reconsideration follows accepted full-corpus Publication production,
and materialization requires a separately authorized Step 14 resolution/validation gate.

`DataService`/`servesDataset` remain declared but service extraction is not activated.
Heuristically generated HydroShare `data_services` are not admissible evidence for
published services; do not pass them to future LLM contracts as verified facts.
HydroShare README enrichment, Hub citation parsing, additional geographic identifiers,
DataService/WMS/WCS materialization and other optional comprehensive enhancements
remain deferred pending separate authorization. The bounded GitHub C-C27 and Hub
C-DC22 enrichment is complete; it does not imply use, implementation, dependency,
identity, scientific correctness or exhaustive coverage. Mechanically recoverable
omissions are not thereby LLM targets.
Cross-source identity resolution remains **Step 14**; names alone do not establish
canonical external identities. No provider/model calls are authorized by this handoff.

## Historical authorities to preserve

Publication deterministic, production, annotation, and evaluation authorities are
unchanged by the v0.1.6 freeze and Step 10 closure. Their original version bindings
remain authoritative; do not infer a Publication migration to v0.1.6.

- Ontology v0.1.5 formalization remains in `docs/ontology_formalization.md` §11;
  exact inventory/spec/OWL fixtures are in `tests/fixtures/ontology/v0.1.5/`.
- Step 9 is ACCEPTED / FROZEN_CLOSED at `29fa652`; closure:
  `data/curation/papers/m2/scierc_step9_closure_v0.1.0.json`.
- Step 8 is ACCEPTED / FROZEN_CLOSED in `docs/evaluation_decisions.md`.
  Closure: `data/curation/papers/m2/publication_step8_final_evaluation/publication_step8_closure_freeze_v1.0.0.json`,
  SHA-256 `f1b434fbc995f17222ba4bb65a4e220af5856d5a3f6be9d4a10b4f3c6ba56b94`.
  Preserve both independent reviews, original agreement, joint reconciliation,
  182 final outcomes, and the 179 supported assertions (130 nodes, 49 relations).
- Step 7 is FROZEN/CLOSED at `6b6e081`; corrected N=5 Human Core scoring and
  `publication_human_core_n5_corrected_evaluation_step7c_closure_v1.0.0.json`
  remain immutable. Strict results remain primary; researcher-reviewed results secondary.
- Step 5 v0.1.3 closure is at `5bf2720`; v0.1.4 supersedes only secondary-review
  coverage and predeclares paired candidate-support agreement, not extraction IAA.
  See the versioned Step 5 authorities and `docs/study2_evaluation_protocol_amendment_v0.3.md`.
- Step 4 Production Acceptance is frozen at `4cd90bb` in
  `docs/publication_production_acceptance_policy_v0.1.md`.
  Historical Step 6 C1 freeze remains at `1a28c0064485abca5828e7a58f613f1cedad62aa`.
- Preserve the corrected evaluation realization in
  `data/curation/papers/m2/publication_pilot1_corrected_evaluation/`, its 11 selected
  authentic requests, and the separate historical C1 realization. Evaluation completion
  does not constitute the full Publication production KG. Full-corpus Publication
  semantic production remains a distinct dependency for Step 13.
- Human Core primary and supplemental exports remain separate immutable authorities
  under `data/curation/papers/m2/human_core_gold/`. DEVSET0 closure and development-only
  stability diagnostics remain historical, non-gold records under `data/curation/papers/m2/`.

Publication's canonical semantic pipeline and evidence-failure-isolation authorities
remain in force. Preserve exact evidence binding, pipeline-owned endpoint provenance,
unchanged V1–V12 validation, and pipeline-derived D-26 mentions. Endpoint coexistence
alone never establishes a semantic relation. No post-generation evidence repair.

## Operational discipline

For future authorized implementation, use focused T1/T2 checks; broaden only for an
actual cross-cutting change or failure. Do not re-audit accepted milestones or rerun frozen human/model work.
Stop on semantic contradictions, historical-mutation requirements, or unexpected broad
hash cascades. Leave unrelated local changes untouched, including the existing
`src/ontology/catalog-v001.xml` timestamp-only change.

Update this handoff at the next accepted milestone or workstream transition, not after
routine implementation commits. Keep detailed historical truth in its versioned authorities.
