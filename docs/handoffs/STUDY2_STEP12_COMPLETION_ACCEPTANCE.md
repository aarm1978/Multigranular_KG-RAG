# Study 2 — Step 12 completion acceptance

**Researcher-directed closure date:** 2026-10-12  
**Status:** **Step 12 (12A/12B/12C) CLOSED / ACCEPTED** for technical integration, offline validation, and bounded authentic calibration.  
**Accepted implementation checkpoint prior to this documentation closure:** `594992023112a19b81b11f81f1f8e885fe0b4a10`  
**Branch:** `codex/publication-human-core-annotation-ui`  
**Boundary:** This is **not** semantic acceptance of candidate assertions, full-corpus production, KG authorization, or approval for Step 13 live provider calls.

## Accepted milestones and authorities

- **Step 11** remains closed under [source-specific semantic contract v0.3](../study2_step11_source_specific_semantic_contracts_v0.3.md) and [its acceptance](STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md), with ontology v0.1.6. Its approved [format-conformance amendment v1.0.0](../study2_step11_format_conformance_amendment_v1.0.0.md) prospectively supersedes **only** conflicting exact representation/locator rules; it does not change the ontology, source eligibility, or semantic gates. Researcher-approved contracts are revisable through explicit scoped amendments; a freeze preserves historical authority, not a known design defect.
- **Step 12A CLOSED:** [technical integration acceptance](STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md).
- **Step 12B CLOSED:** [offline validation acceptance](STUDY2_STEP12B_OFFLINE_VALIDATION_ACCEPTANCE.md).
- **Step 12C CLOSED HERE:** 30 authentic versioned calibration requests (10 distinct source owners each for HydroShare, GitHub and CIROH Hub), including historical HS-01 plus 29 new calls. Wave C was a predeclared held-out **qualitative challenge**; its outputs must not be used for further prompt tuning.

The exact [selection manifest v0.2](../study2_step12c_calibration_selection_manifest_candidate_v0.2.json) is preserved (SHA-256 `2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`). B and C used separate authorized execution amendments with SHA-256 `0733e14e2ad0dfe13b158cdd3cad2b4867097c0406601cc09fb95061db6cfe60` and `bf41e0951630b3d395ed5cffc1ef7877eef13287b06d2ac5d083ce4e103ac85b`, respectively. Full semantic requests, not GitHub's projected provider inputs, remain replay authority.

## Authentic pilot results (historical, unchanged)

| Wave | Proposed node/edge assertions | Mechanically validated | Semantic-condition holds | Endpoint holds | Rejected | Evidence-binding failures | Separate abstentions |
|---|---:|---:|---:|---:|---:|---:|---:|
| A: 12 incl. HS-01 | 171 | 102 | 56 | 13 | 0 | 0 | 2 |
| B: 9 | 99 | 74 | 22 | 3 | 0 | 0 | 4 |
| C: 9 | 93 | 70 | 11 | 4 | 4 | 4 | 4 |
| **Total: 30** | **363** | **246** | **89** | **20** | **4** | **4** | **10** |

These are deterministic parser/validator dispositions and qualitative diagnostic counts, **not** precision, recall, F1, model generalization or semantic authorization. Some holds are dependency cascades. No mechanically validated candidate is automatically KG-authorized. A/B/C preserved responses and locally ignored analysis live under `var/study2_step12c/`; those ignored materials are not retrievable from GitHub solely because the tracked manifests exist.

**Final prospective, opt-in request/prompt variants** (historic versions unchanged):
- HydroShare: `hydroshare-request/1.2.0` / `hydroshare-wave-b-clarification/0.1.0`.
- GitHub: `github-request/1.2.0` / `github-wave-c-role-purpose-clarification/0.1.0`; projection `github-provider-input/1.2.0`.
- CIROH Hub: `ciroh_hub-request/1.2.0` / `ciroh-hub-wave-c-step-tool-clarification/0.1.0`.

## Step 11 narrow correction and separate revalidation

Original **HS-09** had four evidence-binding failures: six literal uniquely locatable evidence fragments were accompanied by an invalid, redundant descriptive `locatorAnchor`. Original **HUB-08** had four rejected nodes and four dependent endpoint holds because exact ontology IRIs (`ciroh:MLModel`, `ciroh:ProcessBasedModel`, `ciroh:Workflow`, `deo:Methods`) were supplied where the response validator expected local class names.

At implementation checkpoint `594992023112a19b81b11f81f1f8e885fe0b4a10`, `study2-format-conformance/1.0.0` introduced **explicit opt-in, versioned, deterministic** equivalence for exact declared ontology names/IRIs and unique literal citations with invalid redundant anchors. Authentic responses, original dispositions, source versions, and all original hashes remain immutable; derived output and replay carry distinct hashes and diagnostics. No arbitrary namespace stripping, fuzzy matching, source-text modification or semantic decision is permitted. A separate `study2-canonical-declaration-schema/1.0.0` prospectively constrains class/relation names per inventory ID, without editing historical envelopes. Codex reported **25 focused tests passed**.

**Corrective offline outcomes, NOT replacements for the original C row:** HS-09 recovered **2 nodes + 2 edges** as mechanically validated; HUB-08 recovered **3 nodes + 3 edges**, while its `Method` and `describesMethod` retained `supported_method` and `substantive_method_description` conditions. The derived C view is **80 mechanically validated + 13 semantic holds**, separate from the authentic C view. The optional corrective live IDs HS-09-FC01/HUB-08-FC01 are **unexecuted, unauthorized and not required** for Step 12 closure.

## Observed limitations and explicit nonclaims

HydroShare's documented use/capability distinction, named model-instance granularity and README-only individuated Measurement require source-specific judgment. GitHub's RepositoryPurpose assignments, exact Function/Algorithm identity and `uses` versus `mentions` versus `implementedBy` remain evidentiary judgments, not automatic consequences of quoted strings. CIROH Hub Procedure/Step must be substantive and not simply navigation/administrative guidance; Example/Parameter require accepted parent paths. Incomplete source/context flags preclude owner-level coverage/exhaustiveness claims. Content-rich sources with failed output conformance must not be mislabeled as semantically empty.

The Step 12C pilot is a **purposive development/held-out qualitative diagnostic**, not new gold and not a population metric. It provides evidence about reproducibility, error isolation, evidence-binding behavior and semantic risk, but does **not** demonstrate full-corpus extraction completeness or automatic scientific correctness.

## Step 13 entry requirements (next workstream, NOT YET AUTHORIZED)

1. With the researcher, specify and accept a **versioned, scalable, conservative semantic-acceptance policy**: independently sufficient evidence, scientific identity/type/granularity, role and direction of relations, conditional gates, dependencies, and admissible automatic vs bounded-human vs rejected/unresolved non-KG outcomes. An LLM's own verdict cannot serve as independent ground truth. Avoid exhaustive human annotation.
2. Integrate the approved **opt-in** format-conformance adapter and canonical strict response schema into a prospective production path. Verify schema/provider compatibility in a separately approved bounded integration check; historical defaults/outputs remain unchanged.
3. Plan and authorize corpus and context coverage, owner-level source-failure reporting, request/model/schema pinning, conservative budgets and preserved authentic provider responses before broad dispatch.
4. Produce **four source-local** semantic outputs, explicitly including **full-corpus Publication semantic production under its separate accepted Publication authority**. Bounded Publication N=5/N=6 evaluation is not this production pass.
5. Preserve source-local identity until Step 14 cross-artifact alignment. Step 14A evidence-grounded relation completion is **optional and default SKIPPED**, never a prerequisite for final KG/Study 3 handoff.

This documentation-only closure performs **no provider calls, extraction, tests, graph writes or semantic candidate promotion**. New active workstream: **Step 13 acceptance-policy design**, not production execution. The [tracked Codex handoff](../codex/CODEX_HANDOFF.md) records the operational transition.
