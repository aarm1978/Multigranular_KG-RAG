# CODEX_HANDOFF.md

> Tracked operational checkpoint, updated for a milestone transition on 2026-10-12. This is a concise navigation aid, not a methodological authority. Historical handoffs remain in git history; source-of-truth contracts and acceptance records are linked below.

## Current checkpoint

**Study 2 Step 12 (12A/12B/12C): CLOSED / ACCEPTED.** See [formal completion record](../handoffs/STUDY2_STEP12_COMPLETION_ACCEPTANCE.md). Step 11 is also CLOSED/ACCEPTED with a subsequent researcher-approved **narrow, explicit format-conformance amendment**.

**Step 13.0 construction-acceptance design: RESEARCHER-APPROVED / TRACKED** under `study2-construction-acceptance/0.1.0` ([policy](../study2_step13_construction_acceptance_policy_v0.1.md), documentation commit `dbee17e30dca2ad0f0358bef223b13a479c392bc`). **Next: Step 13.1 — focused offline acceptance-projection implementation and opt-in conformance/schema integration.** No live provider calls, full-corpus dispatch or KG writes are authorized.

Branch: `codex/publication-human-core-annotation-ui`. Last technical implementation checkpoint before this closure: `594992023112a19b81b11f81f1f8e885fe0b4a10`. The closure commit updates this handoff and adds the acceptance record. Preserve the unrelated local `src/ontology/catalog-v001.xml` modification.

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

## Step 13 — approved method, next bounded implementation

Implement the approved policy as a **post-replay construction acceptance and provenance projection** for HydroShare/GitHub/Hub, reusing the existing validators, complete original findings, source-local dependency paths, exact deterministic ModelVersion duplicates, and immutable replay reports. `validated` is admissible for construction within the policy; conditional interpretive holds may be released only when all nonwaivable requirements are met. GitHub `implementsMethod` remains Step 14; CIROH Hub `Method` may be source-local. No second classifier, LLM judge, confidence system, or per-assertion human approval. Focused T1/T2 only; no provider calls or corpus writes.

After offline implementation acceptance, verify the approved **opt-in** schema/conformance path with the smallest separately authorized real-provider compatibility smoke check before production. Then plan separately authorized full-corpus **four-family source-local semantic production**, including Publications under their own accepted extraction profile (bounded Publication evaluation is NOT full-corpus production). Cross-source alignment stays Step 14; Step 14A is optional/default SKIPPED. Remaining critical path: Step 13 → Step 14 → Step 15 final KG → Step 16 intrinsic evaluation → Step 17 GraphRAG comparison → Step 18 dissertation consolidation and Study 3 handoff.

## Operating limits

Follow local `AGENTS.md` and targeted T1/T2 tests when implementation is authorized. **Do not** start with an audit of Steps 7–12, another calibration round, corpus re-screening, unapproved provider calls, gold-creation work, ontology revision, or graph writes. Source-of-truth records already exist. The ChatGPT-only `CHATGPT_CODEX_WORKFLOW_v2.md` and roadmap are not available to Codex unless explicitly supplied. Update this handoff again only at a meaningful future milestone change.
