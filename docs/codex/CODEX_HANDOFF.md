# CODEX_HANDOFF.md

> Tracked operational checkpoint, updated for a milestone transition on 2026-10-12. This is a concise navigation aid, not a methodological authority. Historical handoffs remain in git history; source-of-truth contracts and acceptance records are linked below.

## Current checkpoint

**Study 2 Step 12 (12A/12B/12C): CLOSED / ACCEPTED.** See [formal completion record](../handoffs/STUDY2_STEP12_COMPLETION_ACCEPTANCE.md). Step 11 is also CLOSED/ACCEPTED with a subsequent researcher-approved **narrow, explicit format-conformance amendment**.

**Step 13.0 construction-acceptance design: RESEARCHER-APPROVED / TRACKED** under `study2-construction-acceptance/0.1.0` ([policy](../study2_step13_construction_acceptance_policy_v0.1.md), documentation commit `dbee17e30dca2ad0f0358bef223b13a479c392bc`). **Step 13.1 minimal OFFLINE implementation: COMPLETED / PENDING RESEARCHER ACCEPTANCE.** The post-replay adapter, source-local projection and prospective opt-in conformance/schema integration are implemented; Step 13.1 is not declared accepted. No live provider calls, full-corpus dispatch or KG writes are authorized.

Branch: `codex/publication-human-core-annotation-ui`. Step 13.1 implementation starting checkpoint: `2c379d11ac8ac55c040918869763952402959f96`. This milestone commit contains the adapter, focused synthetic tests and this handoff update. Preserve the unrelated local `src/ontology/catalog-v001.xml` modification.

## Current accepted authorities

- Ontology v0.1.6, `src/ontology/ontology_spec.yaml`, formally frozen; accepted deterministic pre-alignment baseline **28,406 nodes / 32,809 edges**, **not** the final KG.
- Step 11 `docs/study2_step11_source_specific_semantic_contracts_v0.3.md` and `docs/handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md`.
- Specific approved revision: `docs/study2_step11_format_conformance_amendment_v1.0.0.md` and opt-in `src/extraction/llm/format_conformance.py`. Where there is a conflict on **format/localization only**, this newer narrowly approved amendment governs; source eligibility, ontology, evidence and semantic gates remain unchanged. The design is revisable by explicit justified researcher decision, not silently.
- Step 12A / 12B: `docs/handoffs/STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md` and `docs/handoffs/STUDY2_STEP12B_OFFLINE_VALIDATION_ACCEPTANCE.md`.
- Step 12C selection manifest: `docs/study2_step12c_calibration_selection_manifest_candidate_v0.2.json` (SHA-256 `2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`); accepted Wave B/C amendments: `docs/study2_step12c_wave_b_execution_amendment_v1.0.0.json` and `docs/study2_step12c_wave_c_execution_amendment_v1.0.0.json`.
- **Step 13.0 approved construction policy:** `docs/study2_step13_construction_acceptance_policy_v0.1.md`, `study2-construction-acceptance/0.1.0`. Same construction-control principle as Publications, conditional release of interpretive gates only, hard evidence/source/endpoint/dependency blocks, no new semantic judge. Bounded transport reuse and pre-production human audit/review caps.
- Earlier accepted Publication evaluation authorities and Step 10 source-gap/deterministic enrichments remain untouched. Read their acceptance records as needed rather than repeating discovery or audits.

## Closed Step 12 results — essential numbers only

Thirty authentic requests (ten distinct source owners per HydroShare/GitHub/CIROH Hub, including historical HS-01 and 29 additional calls); Waves A/B/C yielded **363 node+edge proposals, 10 abstentions, 246 mechanically validated, 89 semantic-condition holds, 20 endpoint holds, 4 rejected and 4 evidence-binding failures**. These are **not** semantic precision/recall/F1 or KG authorization. Final Wave C is a held-out *qualitative* challenge; do not tune prompts on C.

Final prospective **opt-in** prompt versions:
- HydroShare `hydroshare-request/1.2.0` — `hydroshare-wave-b-clarification/0.1.0`.
- GitHub `github-request/1.2.0` — `github-wave-c-role-purpose-clarification/0.1.0` (`github-provider-input/1.2.0`).
- Hub `ciroh_hub-request/1.2.0` — `ciroh-hub-wave-c-step-tool-clarification/0.1.0`.

**Format correction v1.0.0 (separate derived replay):** HS-09's four failures became 4 mechanically validated; HUB-08's eight original failed/endpoint-held assertions became 6 mechanically validated plus 2 semantic holds. Original A/B/C outputs and dispositions remain frozen; no corrective provider calls ran. Opt-in `study2-canonical-declaration-schema/1.0.0` constrains future response branch names; provider acceptance is not yet verified. Codex reported 25 focused conformance tests. Local `var/study2_step12c/` contains ignored original responses, replays, approvals, diagnostic packages and corrected views; GitHub does **not** expose these files.

## Step 13.1 — offline implementation, pending researcher acceptance

Implemented `src/extraction/llm/construction_acceptance.py`: `project_replay` consumes a sealed Step 12 replay and returns an immutable, hashable decision report and accepted-semantic projection. `replay_and_project` integrates recorded bytes only; both explicit conformance/schema versions are required for the prospective opt-in path. Historical replay defaults, validators, scientific contracts and frozen artifacts are unchanged. The original replay and exact derived-replay hash, request/source/evidence/authority references and policy hash remain linked; no provider identity is inferred. Construction requires a processable replay and existing caller-pinned `expected_request_sha256` / `requestAssociation` verification.

The adapter applies ordinary and approved conditional inclusion after original findings, gates, evidence, endpoints, duplicate flags and dependencies are inspected. Deterministic dependency closure admits structurally verified Hub attachment cycles together and removes dependencies on held assertions; projections retain exact external endpoints and produce no orphan edges. Hub Method is source-local, GitHub Method/implementsMethod remains held for Step 14, Measurement requires verified README evidence, and RepositoryPurpose uses the six frozen seeds with explicit `classification=proposed`.

**ModelVersion duplicate correction (starting checkpoint `1ddb385860918e87ba4c741873dfdf008727073b`):** GitHub A-C10 and C-C09 now remain held, including selected existing endpoints and matching accepted assertion triples. The earlier endpoint/repository comparison did not prove that the candidate's evidence describes the stored version/product. Trusted deterministic `version`/`toolId` attributes identify the stored record, but the frozen candidate/evidence contract supplies no independently verified mapping to that structured identity. Both `exact_deterministic_version_comparison_unavailable` and `candidate_version_product_identity_not_established` explain the conservative hold. No label, name, quoted-token or endpoint-reference inference was added. Original replay findings and duplicate references remain unchanged as provenance; direct and dependent hasModelVersion edges cannot bypass the hold. Positive exact suppression is unavailable under this bounded implementation; frozen authorities and upstream validators remain unchanged. Step 13.1 remains pending researcher acceptance.

Correction validation: **6 focused synthetic tests passed** (22.969 seconds, existing ontology Python environment): endpoint-only/missing-authority holds; novel-version/label holds; quoted 2.0 referencing deterministic 1.0; apparent matching/ambiguous prose and contradictory product attributes; direct/dependent version edges; unaffected Tool assertions and non-ModelVersion duplicate handling. Tests also preserve input/replay immutability and reproducible hashes. No broad suite, provider calls, corpus processing or KG writes ran for this correction.

Prior implementation checkpoint validation: **52 tests passed** using the existing GraphRAG Python 3.12 environment and `PYTHONPATH=tests:. python -m unittest test_construction_acceptance test_format_conformance test_datasets_semantic_offline_pipeline test_coderepos_semantic_offline_pipeline test_documents_semantic_offline_pipeline -q` (157.445 seconds). This includes 19 new acceptance tests plus 33 unchanged replay/conformance tests. Coverage includes ordinary/conditional inclusion, mixed hard findings, missing/mismatched request association, dependency closure and ordering, Hub/GitHub Method boundaries, exact version duplicates and unavailable-authority holds, scoped source failures, immutable reproducible hashes and legacy compatibility.

Only focused synthetic T1/T2 validation is authorized here. Zero provider/model calls, corpus processing, KG writes or retries were performed. No new semantic validator, live transport path or retry controller was added.

After offline implementation acceptance, verify the approved **opt-in** schema/conformance path with the smallest separately authorized real-provider compatibility smoke check before production. Then plan separately authorized full-corpus **four-family source-local semantic production**, including Publications under their own accepted extraction profile (bounded Publication evaluation is NOT full-corpus production). Cross-source alignment stays Step 14; Step 14A is optional/default SKIPPED. Remaining critical path: Step 13 → Step 14 → Step 15 final KG → Step 16 intrinsic evaluation → Step 17 GraphRAG comparison → Step 18 dissertation consolidation and Study 3 handoff.

## Operating limits

Follow local `AGENTS.md` and targeted T1/T2 tests when implementation is authorized. **Do not** start with an audit of Steps 7–12, another calibration round, corpus re-screening, unapproved provider calls, gold-creation work, ontology revision, or graph writes. Source-of-truth records already exist. The ChatGPT-only `CHATGPT_CODEX_WORKFLOW_v2.md` and roadmap are not available to Codex unless explicitly supplied. Update this handoff again only at a meaningful future milestone change.
