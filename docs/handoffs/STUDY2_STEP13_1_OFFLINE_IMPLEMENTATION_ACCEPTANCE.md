# Study 2 — Step 13.1 offline construction-acceptance implementation acceptance

**Researcher approval date:** 2026-10-13  
**Status:** **CLOSED / ACCEPTED — bounded OFFLINE implementation only**  
**Accepted implementation checkpoint:** `fc084ce1bfc640a2837ce6d65a8992a40fd9e6ce`  
**Branch:** `codex/publication-human-core-annotation-ui`  
**Policy authority:** [Study 2 source-local construction acceptance v0.1.0](../study2_step13_construction_acceptance_policy_v0.1.md), ID `study2-construction-acceptance/0.1.0`, approved prospectively at `dbee17e30dca2ad0f0358bef223b13a479c392bc`.  
**Predecessors:** Step 11 v0.3 with its narrow `study2-format-conformance/1.0.0` amendment; accepted Step 12A/12B/12C. Historical acceptance and pilot outputs remain unchanged.

## What the researcher accepts

The researcher approves the completed **offline** implementation of the Step 13.0 policy for HydroShare, GitHub and CIROH Hub at the exact code checkpoint above. The approval is for reproducible **source-local construction admissibility**, not independent verification of semantic truth, a new Human Core, extraction generalization, corpus completeness, KG assembly/materialization or permission for a provider call.

The approved implementation consists of:
- `src/extraction/llm/construction_acceptance.py`: a post-replay `project_replay()` adapter consuming sealed, caller-associated existing Step 12 reports, and `replay_and_project()` for the prospective recorded-response offline path; immutable, hashable decision reports and construction-accepted source-local projections with original replay and evidence/provenance references.
- Reuse of unchanged family readers, request builders, parsers, evidence binders, candidate validators and immutable replay outputs. Ordinary `validated` admissions and narrowly authorized conditional interpretive admissions depend on examination of **all original findings**, evidence, source/endpoint integrity, pending gates, duplicate markers and dependencies; disposition alone is not authoritative.
- Deterministic, candidate-order-independent dependency closure (including structurally established Hub procedural attachment cycles); rejected/absent parents and invalid paths remain blocked. The Hub may produce a source-local `Method`; GitHub `implementsMethod` remains non-KG until separately authorized Step 14 resolution. HydroShare `Measurement` requires verified README evidence. GitHub `RepositoryPurpose` uses its six approved seeds and source-specific assignment requirements.
- The existing explicit opt-in `study2-format-conformance/1.0.0` and `study2-canonical-declaration-schema/1.0.0` prospective **offline** path, without changing legacy defaults or asserting actual provider/schema compatibility.
- No new semantic judge, confidence scoring, annotation interface, ontology revision, live transport controller, historical validator changes, corpus extraction or KG writes.

Implementation commits: initial adapter/tests/handoff `1ddb385860918e87ba4c741873dfdf008727073b`; narrow ModelVersion corrective commit `fc084ce1bfc640a2837ce6d65a8992a40fd9e6ce`.

## Recorded validation evidence (not rerun for closure)

| Previously reported Codex check | Scope | Reported result |
|---|---|---:|
| Initial implementation at `1ddb385` | Focused synthetic T1/T2: 19 new acceptance checks and 33 existing replay/conformance checks | **52 passed** |
| Correction at `fc084ce` | Focused synthetic T1/T2: ModelVersion endpoint-only holds, matching/mismatching/unavailable identity information, direct/dependent edge holds, independent Tool survival, historical replay/hash preservation | **6 passed** |

These are two **separate reported executions**, not a fresh combined 58-test run. The researcher and ChatGPT reviewed the code, focused test cases and exact commits; **no tests, provider calls, audits, corpus processing, or graph writes were performed as part of this documentation-only acceptance**. Synthetic results do not establish authentic provider compatibility, complete-source recall, or semantic precision.

## Explicitly accepted known limitation — GitHub ModelVersion

The current `A-C10 ModelVersion` and `C-C09 hasModelVersion` LLM-generated candidates **all remain held**, including apparent same-repository deterministic duplicates, because their authorized candidate/evidence schema does **not** independently bind a quoted version/product to the structured deterministic version identity. The correction prevents treating the model's choice of an existing endpoint or assertion as proof of exact duplication; existing `duplicateOf`, original findings, quotations and evidence remain as diagnostic provenance only. Neither automatic acceptance of novel LLM versions **nor proven positive duplicate suppression** is available under this implementation.

This is an **explicit coverage limitation**, not a claim that new versions do not exist or that the extractor cannot propose them. Existing deterministic `ModelVersion` nodes and `hasModelVersion` edges remain unaffected. The researcher accepts this constraint for Step 13.1 closure; it does **not** require a new identity engine or immediate reengineering before advancing. Report the limitation in future production coverage and the dissertation. Any later correction requires separate justification and prospective authorization.

## Boundary of this acceptance and next workstream

- **Step 13.1 is CLOSED / ACCEPTED.** Step 13 in full is **NOT** closed. `semanticStatus=not_evaluated` and `kgAuthorization=false` in preserved Step 12 records remain historically true; the new construction projection has separate policy authority. No production KG is authorized by this record.
- **Next: smallest separately authorized, real-provider canonical strict-schema compatibility check** on the explicitly opt-in path; preserve exact model/prompt/request/schema/source/version identities, genuine response bytes, token usage and provider metadata. This is a technical compatibility check, not an additional semantic calibration on the held-out Step 12C wave.
- **Then: four-family full-corpus production preparation**, including Publications under its separate frozen Step 4/production authorities. Define corpus/eligible context selection, selected-unit coverage and partial-source reporting, transport/retry behavior, STOP rules, complete provenance and the predeclared human diagnostic-audit and exceptional-review workload ceilings. Do not rescreen Steps 7–12 or generate a new gold standard.
- **Cost planning is an estimate-first exercise**, not an arbitrary spend-cap exercise: estimate per family from available request/input/output-token and usage evidence (pilot records where applicable), anticipated source/selected-unit volume, current provider billing categories/prices, schema overhead, output variability and technical retry scenarios. Give a transparent expected range and assumptions; record actual spending as execution proceeds. The accepted policy nevertheless requires explicit later per-run authorization and a monetary budget/guardrail in the execution manifest. Do not treat this closure as approval of any cost or provider call, and do not invent a dollar ceiling now.
- **Step 14** owns cross-source entity/method alignment; Step 14A remains optional/default SKIPPED. Nothing here changes the ontology v0.1.6, the accepted Publication extraction/evaluation boundary or prior deterministic baseline.

This closure changes only this acceptance document and the [tracked operational handoff](../codex/CODEX_HANDOFF.md). No other file, implementation, test output or history is modified.
