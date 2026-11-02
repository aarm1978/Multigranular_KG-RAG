# Study 2 — Materialized corpus evidence amendment v0.1

**Authority ID:** `study2-materialized-corpus-evidence/0.1.0`

**Date:** 2026-10-29

**Status:** Researcher-approved evidence-eligibility decision; Phase 1 documentation only. Implementation and corpus reclassification have not occurred under this authority.

**Inspection checkpoint:** `e906d36cd9a75ee8de24b6091bcfff2f2fb6bdb5`.

## 1. Rule and rationale

Literal content present in an authorized, materialized source unit is eligible for semantic evidence consideration regardless of browser visibility or presentation structure. Construction admission requires exact source grounding and satisfaction of the applicable semantic, ontology, identity, endpoint, dependency, duplication and provenance requirements.

This rule applies to **CIROH Hub, GitHub, HydroShare and Publications**. Study 2 extracts scientific knowledge from the materialized research corpus; it does not reconstruct a browser presentation. For Hub, `pages[].content_mdx` is the authoritative materialized text, including already incorporated repository content and already materialized JavaScript-generated text. Rendering state, CSS, selected tabs, wrapper recognition and uncertain component presentation cannot independently disqualify literal source evidence.

Eligibility is permission to consider evidence, **not automatic assertion admission**. This amendment changes a methodological eligibility restriction, rather than claiming that every historical visibility hold was a parser bug or an incorrect decision under its original authority.

## 2. Implications and unchanged safeguards

- Text in every materialized tab or interactive component is eligible; no browser execution is needed or authorized.
- Already materialized JavaScript output or incorporated repository text is eligible with its existing source provenance. Do not fetch missing external content or infer unmaterialized outputs.
- Unsupported HTML/MDX/JSX attributes, dynamic presentation properties, unknown wrappers and malformed presentation markup do not independently invalidate otherwise source-bound literal text.
- Mixed prose, code, examples and configuration are not categorically inadmissible because of their format. Comments are not excluded merely because they are non-rendered. No replacement blanket ban or component allowlist is authorized.
- Interpret the proposed assertion in its actual context. Planned, hypothetical, conditional, negated, deprecated or commented-out behavior does not automatically establish current implementation or execution. Code examples do not prove execution or scientific results; literal binding alone does not establish semantic support.
- Preserve source identity/integrity, authorized source-unit boundaries, exact quotations and offsets, provenance, schema/global identity checks, ontology types/signatures, endpoint identity/direction, independently sufficient node and edge evidence, parent paths/dependency closure, duplicate suppression and prohibitions on invention. Preserve source-local identities and Step 14 boundaries.
- Preserve genuine semantic requirements: a Parameter needs an explicitly explained identity and role, not an unexplained key; Function/Algorithm descriptions need explicit semantic support; Procedure/Step/Example attachments need their independently evidenced parents. Explanatory language does not cease to be explanatory merely because it occurs in a comment or wrapper. This does not authorize AST execution/analysis as a substitute for source-supported meaning, invented defaults, or inference of behavior from an unexplained command.
- This amendment does not add source files, notebook code cells, external resources or absent visual information to authorized units, change ontology targets, reopen Steps 1–12, or alter unrelated Publications evaluation, annotation or matching policies.

## 3. Narrow supersession and historical authorities

The following restrictions are superseded **only insofar as presentation or rendering independently determines eligibility**. Their other semantic and integrity requirements remain effective. Original documents and implementation versions remain intact.

| Historical provision | Superseded restriction | Retained requirement |
|---|---|---|
| [Step 11 v0.3](study2_step11_source_specific_semantic_contracts_v0.3.md), §2 Hub unit description and §5.1 items 2–3, 6 | Bounded “visible” MDX; static-visible-only eligibility; exclusion of comments/runtime or unknown-component regions solely for visibility; uncertainty about visibility as an abstention/hold reason | Authoritative `content_mdx`, exact boundaries, offsets, hashes and lineage; no inference of absent content |
| Step 11 §5.1 item 4 and related §5.2 Example/Parameter provisions | Fence format as an exclusive Example-only evidence channel; categorical format exclusion before assessing meaning | Substantive identifiable Example, explicit Parameter role, independent attachment evidence, valid parent paths; no inferred execution/defaults/results |
| Step 11 §4 Gate D and related descriptive-prose wording | Any application that excludes otherwise explanatory literal content solely because it is wrapped, commented or formatted as code | Actual scientific/software description and role support; no inferred runtime behavior from code, badges, configuration or links alone; unchanged authorized documentary sources |
| [Step 13 construction policy v0.1](study2_step13_construction_acceptance_policy_v0.1.md), §3 Hub dependent-target row | “visible static MDX only” | All other independent source, semantic, parent and dependency conditions in that row |
| Step 13 §§2–4 eligibility references and descriptive/explanatory-prose requirements | Inherited visibility/format-only disqualification of literal evidence | Complete-reason inspection, non-inclusion of genuine hard failures, no semantic repair; explanatory semantic content remains required |
| [Source-local v0.4.1](study2_source_local_semantics_v0.4.1.md), full-page admissibility; [v0.4.4 lexical overlay](study2_step13_mdx_lexical_shadow_v0.4.4.md) | Static-wrapper classification, comment/dynamic/uncertain/code-only masks as autonomous eligibility gates | Historical algorithms and their outputs remain reproducible; source-grounding and substantive safeguards remain |
| [Publication source-unit contract](publication_source_unit_contract.md), §11 code-without-prose exclusion and its block-level implementation | Code format alone as a reason to make literal materialized text unavailable for consideration in a future amended route | No unsupported code/equation/visual interpretation; unchanged historical source selection, production and evaluation authorities |

The accepted [Step 12 interfaces](handoffs/STUDY2_STEP12_COMPLETION_ACCEPTANCE.md) include HydroShare request 1.2.0, GitHub request 1.2.0 and Hub request 1.2.0 with their recorded Wave B/C prompts; later locator/repetition and specialized source-local variants remain independently versioned. Their source-selection, prompt and binding restrictions implementing the superseded rule must not silently become the new authority. This amendment neither edits those historical instructions nor represents their authentic outputs as generated under this decision. Repeated summaries/checklists of the superseded visibility rule have the same narrow prospective supersession.

The residual diagnostic at `var/study2_step13/source-local-visibility-residual-diagnostic/v1/` evaluated the earlier rule. Its recommendations to retain unknown/dynamic visibility holds are historical recommendations, not controlling authority after this researcher decision. Its evidence records remain unchanged; their counts do not establish recoverable or scientifically correct assertions.

## 4. Two distinct applications

**Future extraction.** A separately versioned request/prompt and validation path must name and pin this amendment. Replace categorical visibility/format instructions with the rule in §1 and contextual safeguards in §2; retain calibrated target-specific positive criteria. Preserve historical provider envelopes. No future call is authorized by this documentation change.

**Post-hoc offline interpretation.** A separately versioned derived review may revalidate existing authentic responses against their exact authorized source units under this new authority. It must retain the original request, prompt, response, source and accounting identities and explicitly identify the changed validation authority. It must not claim this rule governed the model calls, repair output, reverse abstentions into assertions, or invent omitted candidates. Re-run the necessary validation and construction dependency closure; do not simply release old holds or re-project unchanged visibility findings. Preserve v2/v3 and all frozen outputs.

Compare to completed v3 using stable request/candidate identities: group and consolidated-owner node/edge dispositions, every changed decision and cause, independent versus dependency consequences, remaining blockers and zero-yield owners. Preserve quarantined malformed abstentions. Stop on unexplained losses or changes to previously accepted assertions. Report rule-induced information recovery, never empirical precision/recall/F1 or scientific completion.

## 5. Phase 2 boundary

Reuse the current complete-source preparation, literal binders, parsers, semantic validators, exact endpoint reuse, source-local identities, D-26 derivation, construction/dependency machinery and consolidation. Introduce an explicit versioned eligibility path rather than changing pinned historical implementations or developing a renderer. Prospective prompt composition and eligibility metadata must agree with this authority. Publications changes, if implemented prospectively, must remain isolated from its completed production and evaluation; the three-family v3 comparison cannot evaluate Publication effects.

Focused tests must cover materialized tabs/incorporated text, unknown/dynamic presentation wrappers, malformed markup, comments, mixed prose/code/configuration, exact original offsets, unsupported execution claims, insufficient semantic evidence, bad source hashes/IDs, independent edge evidence, parent/dependency failures and duplicate suppression. Historical compatibility and previously accepted dispositions require explicit regression checks. Compact future outputs should contain a pinned manifest, summary, decision changes and bounded evidence references, not copied corpora. No acceptance implementation, provider call, corpus replay, KG write or Phase 2 execution is part of this amendment's creation.
