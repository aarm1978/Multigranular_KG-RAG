# Study 2 Step 12A — Technical integration acceptance

**Researcher approval date:** 2026-10-09
**Status:** CLOSED / ACCEPTED
**Accepted implementation checkpoint:** `7abba6faa79867992870bf405e4c8768cb67cb14`
**Branch:** `codex/publication-human-core-annotation-ui`

## Authority and meaning of closure

This record documents researcher approval of the completed Step 12A offline
technical integration for HydroShare, GitHub and CIROH Hub. The binding semantic
authority remains [frozen Step 11 v0.3](../study2_step11_source_specific_semantic_contracts_v0.3.md)
and its [acceptance record](STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md), with
ontology v0.1.6 and the accepted source-specific target profiles. This acceptance
introduces no new methodological authority or context-selection policy.

Closure establishes **offline technical integration only**. It does not establish
demonstrated semantic correctness, contextual completeness, KG acceptance,
full-corpus extraction, or authorization for provider/model calls. Structural
compatibility and literal evidence binding do not satisfy semantic gates.
Source-read completeness and enforcement of caller-selected unit boundaries do
not demonstrate that the selected context is sufficient or semantically complete.
Semantic acceptance remains unevaluated and KG authorization remains false.

## Accepted packages and implementation checkpoints

| Package | Accepted implementation checkpoint | Accepted technical scope |
|---|---|---|
| 1 — source/evidence interfaces | `2d6c3022e627cb148234858cc881d0463d797be4` | Caller-verified HydroShare README authority/section reading and literal binding; GitHub source/evidence interfaces and scoped descriptive-passage eligibility; Hub displayed-fence binding solely as possible Example context. |
| 2 — HydroShare batch validation | `f2d4ac38c821e376212ed252dc5b0b28d176ebcf` | Frozen active HydroShare targets, exact endpoints and separately authorized source-scoped stubs, independent evidence, local failure isolation, duplicate handling and pending semantic gates. |
| 2 — GitHub batch validation | `66b9832f4f25a9901fff6499f9dbd0e085eca2e3` | Frozen active GitHub targets, six controlled RepositoryPurpose seeds distinct from evidence-backed assignments, exact endpoints, source-local candidates, own-product ModelVersion constraints and unresolved Method proposals. |
| 2 — Hub batch validation | `0a1e8c1990fbc62e07229b443ae6aec998f70a1b` | Frozen active Hub targets, multi-unit literal evidence, exact page/external endpoints, explicit parent-relation paths, visibility holds, dependency isolation and duplicate provenance. |
| 3A — request/recorded-response contracts | `fadd2ef79b6a8404280341eb35be33e1729c3422` | Deterministic versioned requests over caller-selected verified units; strict recorded-response parsing; original bytes/text and hashes; local parse errors, explicit abstention claims and trusted provenance boundaries. |
| 3B — deterministic offline replay | `7abba6faa79867992870bf405e4c8768cb67cb14` | Source-specific request construction, parsing and unchanged batch validation connected to immutable disposition/provenance reports; selected-unit enforcement, parse-invalid quarantine, actual-dependency handling and separate endpoint inventories. |

The accepted scope preserves exact source-local identities, snapshots, authority
hashes, Unicode coordinates, verified Section bindings where available, original
proposals and quotations, duplicate citations, and explicit unresolved outcomes.
Replay separates deterministic GitHub seed endpoints from caller endpoints and
HydroShare accepted endpoints from authorized stubs. It does not repair authentic
responses, invent provider metadata, align cross-source identities or materialize
assertions. Existing representative validator interfaces remain preserved.

## Reported focused validation evidence

The following are prior Codex-reported synthetic T1/T2 results recorded with the
implementation milestones; they were **not rerun or independently re-audited for
this documentation-only closure**:

| Milestone | Reported focused checks passed |
|---|---:|
| Package 1 | 29 |
| Package 2 HydroShare | 10 |
| Package 2 GitHub | 14 |
| Package 2 Hub | 19 |
| Package 3A | 25 |
| Package 3B | **23: 9 HydroShare, 7 GitHub, 7 Hub** |

Package 3B's reported checks cover deterministic round trips, request/response
hashes and immutable reports, endpoint-inventory mappings, parse/validation
failure isolation, selected-unit boundaries, incomplete sources, duplicate
decisions, conditional gates and zero provider/graph effects. They include a
case where downstream literal validation passes but the stricter response parse
failure still prevents validation promotion. These counts describe milestone
checks, not a new aggregate evaluation or evidence of semantic accuracy.

## Preserved boundaries and dependencies

- All pending semantic conditions remain pending. HydroShare Measurement retains
  its README-only evidence restriction; GitHub purpose assignments require their
  own repository-specific evidence and ModelVersion remains own-product only.
  Hub Example/Parameter remain parent-dependent; displayed fences are possible
  Example context only, and Parameter identity/role requires explanatory prose.
- `DataService`/`servesDataset` remain inactive. D-26 `mentions` and superclass/
  superproperty assertions remain pipeline-governed, not model-authored fallback
  targets. C-D26 HydroShare `mentionsModel` remains distinct from D-26.
- Source failures and incomplete inputs remain separate from semantic abstention.
  Empty output is not `abstained_no_evidence`; explicit abstention records remain
  claims subject to the frozen evidence and validation requirements.
- Unresolved C-C16 `implementsMethod` proposals remain immutable non-KG records.
  Endpoint reconsideration depends on accepted full-corpus Publication semantic
  production in Step 13 supplying stable, traceable A-P13 Method occurrences.
  That permits only read-only endpoint review; resolution/materialization still
  requires separately approved Step 14 validation. No automatic alignment,
  name/DOI-based identity inference or historical backfill is authorized.
- Frozen Step 11 v0.3, ontology v0.1.6, Phase A/B, Publication v0.1.5 authorities,
  deterministic graphs/hashes and accepted Steps 7–9 artifacts remain unchanged.
  Existing inactive/deferred scope remains as recorded in those authorities and
  the operational handoff; closure activates none of it.

## Next workstream and administrative scope

**Step 12A is CLOSED / ACCEPTED. Step 12B focused integrated validation is the
next workstream**, with execution scope to be separately authorized. Step 12C
live pilot, Step 13 production and Step 14 alignment remain distinct later work.
This closure grants no provider or production authorization.

This administrative task changes only this acceptance record and the tracked
[operational handoff](../codex/CODEX_HANDOFF.md). No code changes, tests, re-audits,
corpus processing, provider calls or graph writes were performed. The unrelated
local ontology catalog modification remains outside this commit.
