# Study 2 Step 12C — Bounded semantic pilot plan candidate v0.1

**DRAFT / NOT AUTHORIZED — researcher review required before execution.**
Prepared 2026-10-09; offline provider preflight follows selection checkpoint
`d091d9be476cb636bb614a88dcdc0dbf8e04ec4e`, originally based on
`02559039f348a638c6aeb86575c31ba1b93126a5`, on
`codex/publication-human-core-annotation-ui`.

## Purpose and authority

Propose a non-confirmatory feasibility pilot of source-specific request formation,
authentic response processing and researcher review burden. This is not a semantic
accuracy estimate, representative sample, contextual-completeness demonstration or
production acceptance study. No live calls have occurred. Binding authorities are
[frozen Step 11 v0.3](study2_step11_source_specific_semantic_contracts_v0.3.md), its
[acceptance](handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md), ontology v0.1.6,
and accepted [Step 12A](handoffs/STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md)
and [Step 12B](handoffs/STUDY2_STEP12B_OFFLINE_VALIDATION_ACCEPTANCE.md).
All procedures, review labels and ceilings proposed here await researcher approval;
they do not amend the frozen contracts or establish a production selection policy.

## Bounded selection and request grouping

Propose **three requests, one per family**, with no second request selected. The
outer ceiling is two per family / six total, but this draft authorizes none and
proposes only three. Unused slots are not retry or replacement permission.

Selection was by local convenience, not outcome-driven ranking: use the first
HydroShare resource and GitHub repository in their current Phase A arrays; for Hub,
inspect the first eight page titles/routes and choose the AORC access article as a
compact procedural-context candidate. Inspect these three records with the existing
source readers; do not search for favorable semantic outputs. The readers were
invoked locally only to identify units and provenance, without candidate extraction,
tests, providers, downloads or graph writes. No corpus-wide eligibility audit or
coverage claim is made. Freeze the selections below before any live run; a failed
preflight means hold, not automatic substitution or context expansion.

- **HS-01:** Stream Temperature Seasonal Thermal Regime Data; exact DatasetResource
  endpoint `7d960b7fdfee480895fd845bade1b75a`. Supply the entire abstract as one unit.
  It describes data, analysis files and supporting workflow; these are opportunities
  to inspect grounded proposals, not required target outputs. Documentation metadata
  says no README; none is acquired or synthesized. Measurement is therefore out of
  evidence scope for this request, not a semantic no-evidence conclusion.
- **GH-01:** `CIROH-UA/api-nwm-gcp`; exact Repository endpoint
  `github:repo:921792119`, frozen commit
  `3e445c6ba0043b5c2625e75813285603639cd932`. Select only the complete opening
  descriptive prose unit from authoritative `readme.text`, path `README.md`.
  This is a bounded repository-description/purpose opportunity, not an attempt to
  reconstruct deployment procedure from omitted command blocks. Do not consume
  its mirrored raw README. No notebook or additional-file unit enters this request.
- **HUB-01:** `https://hub.ciroh.org/blog/aorc-data-access`; exact DocumentationPage
  endpoint `hub:page:83a1aceb2c34ed513d83`; page key
  `hub-page:https://hub.ciroh.org/blog/aorc-data-access`. Select all adapter units
  from original MDX lines 13–37 listed below in original order: dataset introduction,
  four notebook descriptions, capabilities, access instructions and prerequisites.
  Keep them separate, jointly supplied in one request; do not concatenate or rewrite
  evidence. This retains antecedents and access prerequisites around the procedure
  opportunity without promising substantive Procedure/Step or Example support.

Owner IDs were matched to existing `nodes[].id` and class in respectively
`data/interim/datasets/hydroshare_nodes_edges_v016.json`,
`data/interim/coderepos/github_nodes_edges.json`, and
`data/interim/documents/ciroh_hub_nodes_edges.json`. No graph was changed.
Only these owner endpoints and GitHub's existing six controlled purpose seeds are
proposed as trusted endpoints. External inventories, accepted assertions and
HydroShare authorized stubs are empty for this pilot. URLs/names in prose do not
create external endpoints. Preserve unresolved proposals instead.

## Exact local snapshot and unit manifest

All offsets are original-authority Unicode character offsets, zero-based and
end-exclusive; lines are one-based. SHA-256 values below are local snapshot
fingerprints, not independent acquisition verification. Full source bytes remain
local; this draft records identifiers/hashes without committing raw corpus content.

| Phase A snapshot | SHA-256 of exact local corpus file bytes |
|---|---|
| `data/interim/datasets/ciroh_hydroshare_corpus.json` | `51453913c034c49c1751db1f111ebdc7d2c87e4cd6f8ce8573aee29d91338992` |
| `data/interim/coderepos/ciroh_github_corpus.json` | `be5747c29f992362a545f9ff0600b4e4e74b560395e2aecfbf3a1a85f04f0c1c` |
| `data/interim/documents/ciroh_hub_corpus.json` | `ea2d7a56e5fe2621b8a58405318efae3b178699355f85691bafa3e450aff8baa` |

HydroShare adapter provenance is proposed explicitly as `snapshotID=sha256:` plus
its corpus digest above and `sourceVersion=2024-09-16T20:16:47.723282Z` (the stored
resource update time). This is a local snapshot identifier, not a provider version.
Its unit has `integrityStatus=computed_only`; no independent expected digest was
supplied. GitHub likewise retains its computed-only README authority digest and no
raw README byte hash. Hub's supplied `content_sha256` was checked against exact
`content_mdx`; its stored `file_sha256` is preserved but the raw MDX file was not
independently checked. Recheck snapshots and adapter outputs before any approved run.

| Request | Authority-text SHA-256 |
|---|---|
| HS-01 | `aa4a6451568d355df6238376027a7b2bdfc534b8639a4fcb5c35b6c64001f7d1` |
| GH-01 | `0bfb01f0feb2e2592551ccfd8697d563c2158fb849b2a18c13445e9ae55bcf41` |
| HUB-01 | `cea86ff7f8bbd4fee91b9d4931c8c595c91fec4a04cc6d1c8c44da0aae1c73f4` |

Hub `corpus_path` and `source_path` are both
`blog/2025-07-01-Aorc-Data-Access.mdx`; `source_group=blog`;
`file_sha256=720ffb33447a8d18efbc09188835f5b61c5282c948ccde82ca62d37fb9c19474`.
No verified Section mapping is supplied: preserve heading ordinals/context and
null Section IDs, without inventing anchors or Section nodes.

| Request | Exact sourceUnitID | Offsets [start,end) | Lines |
|---|---|---|---|
| HS-01 | `hydroshare:7d960b7fdfee480895fd845bade1b75a:abstract:d677e83c412e4859cefff88119b9b914514216a535f465c8acde505db1da7466` | 0, 1056 | 1–5 |
| GH-01 | `github:unit:b3ffadb0835b7881333ce08fd467f831d22e19c6c733a5666a0853970faacbf7` | 14, 301 | 2–2 |
| HUB-01 | `hub:unit:e2cca66b5137afd351f37123fc2880e8fb65c5d515459858feb9f79504cadb5b` | 730, 859 | 13–13 |
| HUB-01 | `hub:unit:5e8c022b1755675364e554d737c689647fdd27794d32f9caf3377764517db1be` | 859, 961 | 14–14 |
| HUB-01 | `hub:unit:f3d3769fc5ca33c66101d20f5057b6ed6b3363cab2cfcb9a1482a0bf7dc9a48f` | 961, 1046 | 15–15 |
| HUB-01 | `hub:unit:44553e557599dbf77ebaf0c8bd5ca6bf586800f1d1a8c599a993a4523e2fd933` | 1046, 1185 | 16–16 |
| HUB-01 | `hub:unit:553840e51ab1ea38a631bbf81e7d73ee076fb0a0513296107763b6ede841ed77` | 1185, 1405 | 17–17 |
| HUB-01 | `hub:unit:be722b4836083d307187dbe80235cdb00369b0c7675c6c2f6dcf6d1a09b67fe1` | 1424, 1591 | 21–21 |
| HUB-01 | `hub:unit:c21ba39348438541b64fc2a136f57d5f9921d86d170d41bc01e1b20492f12dc0` | 1591, 1750 | 22–22 |
| HUB-01 | `hub:unit:35da192c9972d22d2a2fb31e015f3dcbd660a57eff7454a353712724343eeba6` | 1750, 1909 | 23–23 |
| HUB-01 | `hub:unit:6ef237d9ca2a78bdae60ccfa7cdd79b6ce4a129d8c72f49541d9d73567611ebe` | 1909, 2060 | 24–24 |
| HUB-01 | `hub:unit:02e6c19d21bff98feec0f813b4fe99ec0544fd3679a931cb150dfc347153d452` | 2061, 2197 | 26–26 |
| HUB-01 | `hub:unit:4d5372cf01f66386b7ef5a5c7e375d3edd2393f7eeb3df57b14295816ffbe38a` | 2197, 2361 | 27–27 |
| HUB-01 | `hub:unit:f2c7a268009b4702611b1bdeb1229585571e6cc3816dd299c1ef6c6188527421` | 2361, 2458 | 28–28 |
| HUB-01 | `hub:unit:96bedc8ad716f67c31dce06e47b35bd8aeecebb07ea2d132e4414fb3e970036a` | 2458, 2582 | 29–29 |
| HUB-01 | `hub:unit:7a345074b0c82d7441212ef5315193ea1611314cc82e7d3ec65b9da35e461569` | 2582, 2762 | 30–30 |
| HUB-01 | `hub:unit:d821019916b1dd9bf2e62540256d47b4cbfda40e6e664eb592a47aa631c495f7` | 2763, 2891 | 32–32 |
| HUB-01 | `hub:unit:d328388712e6ed56ab75e8fdce733c84208feaf388795a489a676bdb1c247655` | 2891, 2964 | 33–33 |
| HUB-01 | `hub:unit:88da035041117aed4e5000ec0ac65a4e0876d9f1890b5d70fb8d9753c528d746` | 2964, 3066 | 34–34 |
| HUB-01 | `hub:unit:500b172ae5a3f73c4d04969781ff2bdd5daafb34e4d70b48c49f1209b684c495` | 3066, 3127 | 35–35 |
| HUB-01 | `hub:unit:6b40a13f6746fc86b72b35c9365d1207feeaf190532f443b8ec626298d4fa84d` | 3127, 3246 | 36–36 |
| HUB-01 | `hub:unit:01f61d9f42ae01b28f2c0cd86f00334579e8a016b5c2b852ba33a7e84b18da9a` | 3246, 3392 | 37–37 |

HydroShare's abstract reader succeeds; the README is optional absent. GitHub's
full one-repository reader reports `needs_review` at README lines 4 and 86 and
notebook Markdown cell 0; these are outside GH-01. Hub reports uncertain markup
visibility at line 11, outside HUB-01. Retain all reader diagnostics; GitHub and
Hub input completeness remain false. Scoped warnings must not poison independently
verified selected prose, nor be hidden to permit `abstained_no_evidence`. Unselected
material is unavailable for evidence even when present in the trusted reader.

## Approval fields and hard execution bounds

| Field | Proposed value / approval state |
|---|---|
| Execution authorization / approver / approval timestamp | NOT AUTHORIZED / PENDING / PENDING |
| Provider/API and configured model ID | Confirmed Publications configuration: OpenAI Responses API, `gpt-5.6-sol`; returned model/version unknown until an authorized response |
| Reasoning / retention / tools / format | Confirmed `reasoning.effort=medium`, `store=false`, no tools; strict `text.format` JSON Schema where supported; synchronous prospective envelope |
| Temperature, top-p, seed and other unsupported settings | Unset; support/values remain pending, no assumed defaults |
| Maximum input tokens per request | PENDING approval; conservative allowances below include semantic input and response schema, with API overhead still unknown |
| Configured maximum output tokens | 32768 for HS-01, GH-01 and HUB-01, adopted by researcher instruction; live execution remains unauthorized |
| Planned requests | 3 (HS-01, GH-01, HUB-01); approve individually |
| Outer request limit | At most 2 per family / 6 total; additional slots require revised exact selection and approval |
| Attempts, retries and concurrency | Proposed 1 attempt per selected request, 0 automatic retries, sequential execution; approval pending |
| Currency, pricing source/date, per-request cost cap, aggregate cost cap | PENDING researcher approval; no invented price or estimated cost |
| Artifact destination, access controls, retention | PENDING approval; restricted local pilot directory, separate from frozen outputs; never commit raw corpus or credentials |
| Researcher review ceiling | Proposed 60 candidate assertions/abstention records total and 90 minutes total; approval pending |

No request may be sent until every execution/budget field is approved and a
conservative maximum cost fits both per-request and aggregate caps. Count failed
or interrupted attempts against limits; an unknown billing outcome is a stop.
Do not silently truncate selected context to fit a token cap. Stop for plan revision
if the complete approved request cannot fit. A researcher-operated terminal runner is now provided below. Its availability does not authorize execution.

## Request preservation and deterministic replay

1. Before a separately authorized pilot, freeze code commit, ontology digest,
   contract `study2-step11-semantic-contracts/v0.3`, selected unit IDs/order,
   full authority snapshots, source-read diagnostics and both completeness views.
   Build with the existing family `request_contract.build_request`; require success.
   Preserve exact serialized request record and its `requestSha256`. Record target
   profile/version and the actual endpoint inventories, including empty mappings.
2. Use current family request/response contracts `hydroshare-request/1.0.0` /
   `hydroshare-response/1.0.0`, `github-request/1.0.0` / `github-response/1.0.0`,
   and `ciroh_hub-request/1.0.0` / `ciroh_hub-response/1.0.0`. Freeze the complete
   approved provider envelope separately (instructions, settings and schema), exact
   transmitted body bytes/hash and its association to the semantic request hash.
   Request and provider-envelope hashes are distinct. The provisional request/envelope hashes from offline construction are recorded
   below; any approved setting change creates a new envelope hash. They establish
   no association with a live response.
3. If subsequently authorized, preserve raw response body bytes before parsing,
   exact model text, timestamps, actual returned provider/model/request metadata,
   finish reason, usage and charge information when available. Do not invent absent
   metadata. Store errors and interrupted/truncated responses unchanged; no evidence
   normalization, JSON repair, quote correction or automated retry. Never log secrets.
4. Replay the preserved candidate-response bytes using each existing
   `offline_pipeline.replay_recorded_response` and the frozen request inputs plus
   `expected_request_sha256`. Preserve raw provider envelope separately from the
   exact extracted model-response bytes; document their deterministic association.
   Record response hash, parse result, validator result, final dispositions, report
   JSON/hash, duplicates, abstentions and pending gates. Replay uses each family's
   `*-offline-replay/1.0.0` version. No provider is called by replay.
5. Require identical report hashes for identical replay inputs. Quarantine locally
   identifiable parse/evidence failures and retain independent valid candidates;
   globally unprocessable responses remain processing failures. Structural/literal
   success is never semantic approval. No accepted graph output is produced.

## Minimal researcher semantic review and reporting

Proposed review unit: each original node, edge or explicit abstention plus its
linked source context and dependency path. Review independently supplied node/edge
support, even when their quotations match. Researcher records: (a) claim supported,
unsupported or ambiguous within selected context; (b) target/type/relation role and
direction appropriate or inappropriate; (c) context sufficient, insufficient or
uncertain; (d) endpoint/parent condition satisfied by independent authority or
pending; (e) short rationale with exact unit references. These are proposed pilot
review labels, not new gold/evaluation or KG acceptance rules. No precision/recall,
representativeness or exhaustive-recall claim is justified by this convenience set.

Review all records if within the ceiling, including invalid, unresolved and
abstention records. If more than 60 records or 90 minutes are needed, stop review
at the ceiling, report the reviewed IDs and unreviewed count explicitly, and hold
any go decision; do not select only successful assertions. Preserve machine
records unchanged and store researcher judgments separately. Record obvious
context omissions as qualitative feasibility findings without constructing a gold
corpus or searching for additional evidence during this pilot.

Report per family: attempted/completed requests, actual token/cost usage, parse and
binding failures, local survival, unresolved/duplicate/abstention counts, reviewed
and unreviewed counts, semantic-support and context-sufficiency judgments, and
qualitative defects. Separate processing failures from semantic ambiguities and
unsupported claims. Empty output/source failure is not semantic no-evidence.

## Frozen exclusions, stop conditions and Step 13 decision

Retain the full frozen family instructions; do not force targets because they are
listed. HydroShare Measurement requires explicit verified README evidence (absent
here). GitHub hasPurpose uses exactly six controlled seeds but requires independent
repository-specific support; ModelVersion is own-product only. C-C16 stays unresolved
and non-KG: accepted full-corpus Publication A-P13 endpoints in Step 13 precede
read-only reconsideration; materialization requires separate Step 14 authorization.
No name/URL matching substitutes for identity resolution. Hub Example/Parameter
require accepted Procedure/Step parents and required relations; displayed code is
only possible Example context and Parameter role requires prose. DataService /
servesDataset are inactive. Abstract-class predictions and D-26 are not model-
authorable; C-D26 HydroShare mentionsModel remains distinct. Publication authorities,
Phase A/B, Steps 7–9, deterministic graphs and all historical outputs stay unchanged.

Stop/hold for missing approval, changed snapshot/unit identity, hash mismatch,
uncertain selected visibility, untrusted endpoint, source failure affecting a
selected unit, budget/token/review overflow, malformed global response, response
association failure, any attempted provider-generated gate attestation, or a
contract/identity contradiction. Local candidate failures remain isolated; they
are findings, not a reason to erase independently valid records. Technical issues
may prompt a separately scoped fix/replay; semantic ambiguity stays unresolved
for researcher judgment, never automatic acceptance.

Proposed **go to Step 13 planning only** requires all three approved requests to
complete, exact replay/provenance association, review of all records within the
ceiling, no unresolved critical integrity/identity/contract defect, and explicit
researcher judgment that usefulness and review burden warrant a separately scoped
production plan. No minimum target yield or statistical accuracy threshold is
invented. Any missing family, unreviewed output, unresolved critical defect or
unapproved cost is no-go/hold. A favorable pilot never automatically authorizes
Step 13 execution, KG acceptance or Step 14 alignment. Full Publication production
and other frozen production dependencies remain separate.

## Decisions required before any live work

Approve or revise the three exact selections and incomplete-input treatment;
confirm execution using the specified provider/model configuration; approve remaining
settings, token and monetary caps, attempt limits and
artifact storage; approve review rubric/ceiling and decision procedure; separately
authorize provider integration and execution. Context changes require a revised
manifest and request hash, not silent expansion. This draft and its commit provide
no live authorization. The tracked operational handoff remains unchanged.


## Offline provider preflight (execution remains NOT AUTHORIZED)

Implementation: `src/extraction/llm/pilot_preflight.py`; focused checks:
`tests/test_pilot_provider_preflight.py`. Four new synthetic T1/T2 tests passed;
no historical tests, provider calls, credentials or network access were used.
The three local requests rebuilt with the exact original 22-unit manifest, order,
owner IDs/classes and authority offsets/hashes. Corpus-byte hashes match the draft;
reader diagnostics match the pinned scoped warning signatures. No context was
resampled, added or replaced. GitHub and Hub remain input-incomplete; HydroShare
retains explicit optional README absence. Computed-only acquisition integrity is
not upgraded by this preflight. The handoff and accepted contracts are unchanged.

### Structural schema compatibility and limits

The accepted `responseContract` objects are field descriptions, not JSON Schemas.
Preflight projects them to a closed root object with closed nested objects,
`additionalProperties=false`, all properties required within each object variant,
arrays, references, enums and nested `anyOf` alternatives. Optional endpoint,
locator, contribution and source-specific fields are represented by omission
variants, not inserted nulls. This avoids altering original responses to satisfy
the parsers. GitHub unclassified/ambiguous purpose nulls retain their existing
parser-supported treatment; invalid classification/null combinations remain local
errors. Inventory alternatives use the existing profile, not Publication schemas.

Offline checks establish valid Draft 2020-12 JSON Schema, the conservative strict
object/required-field shape, and compatibility of every generated candidate-object
variant with its unchanged family parser. They also check optional evidence fields,
exact envelope hashes, drift rejection, immutability and local invalid-evidence
isolation through replay. Required fields do not establish nonempty evidence,
literal binding, trusted endpoints, contextual support or semantic truth. An empty
or invalid evidence record remains a localized parser/validator finding, without
invalidating identifiable siblings. A malformed global envelope remains a processing
failure. No repair layer or generic candidate execution framework is added.

The pure `build_responses_api_request()` constructor is reused from the accepted
Publication provider module; its Publication-specific format name is replaced by
the family response name. No Publication extraction schema, retry policy, key loader,
transport or production orchestration is called. Input consists of the exact
source-specific semantic request JSON, including its instructions and selected
units. Provider field names/configuration follow that existing local adapter.
**Remote schema acceptance, account/model access and model-specific strict-output
support remain untested.** Network documentation lookup was intentionally omitted
under this offline task. Strict mode must not silently fall back or change contracts
if an authorized future call rejects the schema; preserve the error and stop.

### Actual sizes and prospective ceilings

Installed `tiktoken.encoding_for_model("gpt-5.6-sol")` raises `KeyError`; no verified
compatible tokenizer mapping is available locally. No tokenizer files were fetched.
The table therefore gives actual serialized UTF-8 byte sizes and a deliberately
conservative **one-token-per-byte allowance for input plus schema**, not measured
tokens, billing usage or an exact model count. Unknown provider framing/schema
processing overhead is additional and requires a margin when approving input caps.

| Request | Input bytes | Schema bytes | Exact envelope bytes | Conservative input+schema token allowance (not count) | Proposed output-token ceiling |
|---|---:|---:|---:|---:|---:|
| HS-01 | 14130 | 12374 | 28054 | 26504 | 32768 |
| GH-01 | 28320 | 19313 | 50646 | 47633 | 32768 |
| HUB-01 | 41104 | 18720 | 63501 | 59824 | 32768 |

The larger envelope sizes include JSON escaping and the strict schema; source
context was not expanded. The researcher instructed adoption of the Publications
ceiling: **max_output_tokens=32768 for all three requests**. This supersedes the
previous 4096/3072/8192 proposals without authorizing live execution. Reasoning and
visible output share the provider's actual output-budget behavior; no split or
sufficient-output guarantee is assumed. Truncation is preserved as an incomplete
response, never repaired or automatically retried. Monetary caps and actual prices
remain pending. No usage or cost is claimed.

### Deterministic associations and ignored local artifacts

All generated artifacts are under ignored `var/study2_step12c/preflight/` and are
excluded from this commit. Each request directory contains `request-result.json`,
`semantic-request.json`, `provider-input.txt`, `provider-envelope.json` and
`preflight.json`. The semantic digest uses the accepted request contract's exact
canonical serialization; input uses deterministic UTF-8 JSON; envelope bytes are
separately serialized and hashed. An authorized sender must transmit the stored
envelope bytes unchanged, not reserialize with an SDK. The semantic digest differs
legitimately from the input digest because their Unicode escaping policies differ;
the JSON values are the same. No network request has been transmitted.

| Request | Semantic request SHA-256 | Provider input SHA-256 | Provider envelope SHA-256 |
|---|---|---|---|
| HS-01 | `66a3fd974108b18b58d0b6effed8924669558509502760e43699b2858b07f8c0` | `198cf18594357644ed2debd19aa455fce74a849b15a31f493f4dbdc979cd7878` | `402190f9a94eb6e2c3c966406d1a745bcc23fec9d1b0908dd2fe767276d464a7` |
| GH-01 | `bcece9e5d4752cb5804151fcf80c6b74864c62db5430acdc122cee642dea7d45` | `d694226746702b5fd4c11eaf4c82049aa4fb1a42e643bc134f22e8cb929c2344` | `4db77ac6fd0f9aea7e47e3b2c5073892aff2483540a0ec7e0128bdf78aeb4e85` |
| HUB-01 | `5a1db2a4da2c43d09c1aa52fdb993e58ef8b9e9600d6d8b3a8197380ff52ae45` | `8b9f0c4fb64ff2d3ae1faf02d7333ebe22f06a4fa92c58afdea8a551bf6ad252` | `086a42828f4fbf4dfe6595712689cb5fdc4a100a0571e0a38e1f373ebe15982c` |

Proposed future layout, still requiring storage/execution approval:
`var/study2_step12c/runs/<approved-run-id>/<request-id>/` with immutable
`source-snapshot/` (exact selected-owner records, full authority text and reader
results), `request-inputs/` (reconstructable family arguments, endpoint inventories,
selected IDs and versions), the five preflight artifacts above, `response.raw`
(exact HTTP body), `model-output.utf8` (one exact response text, no repairs),
`provider-metadata.json` (only returned metadata/usage), and `replay/` (parse,
validation, disposition JSON and hashes). Keep API headers/credentials out of
artifacts. Record failures, refusals and incomplete responses separately rather
than inventing candidate output. Researcher review lives in a distinct record.
No response/run artifacts are fabricated by preflight.

Approval still required: three requests and incomplete-source treatment, input-overhead margin, monetary caps and approved pricing,
optional supported settings, storage, attempt/review limits, and explicit live
execution authorization. The terminal transport below is implemented; using it live still requires separate approval.


## Researcher-operated terminal runner — NOT AUTHORIZED to execute

`src/extraction/llm/pilot_terminal.py` provides explicit `dry-run` and `execute`
modes. Importing the module does not dispatch. Each invocation selects exactly one
of HS-01, GH-01 or HUB-01; there is no batch execute, retry or replacement mode.
It loads saved preflight bytes, verifies their hashes and selected-unit manifest,
and reconstructs the pure envelope to detect drift. Schema alternatives now have
stable inventory ordering across JSON save/load; a focused regression protects
this serialization defect found during dry-run. Semantic request hashes and
selected input text are unchanged; updated envelope hashes above include the
32768 ceiling and deterministic schema ordering.

The runner reuses only compatible pure Publication envelope/output-text helpers;
it does not adopt Publication extraction schemas, retry, validation or acceptance
policies. It makes one synchronous Responses API POST with exact stored body bytes,
with redirects disabled, configurable socket timeout and an overall elapsed-time
deadline. A separate daemon worker permits periodic elapsed-time messages while
the researcher's terminal waits. No background API mode, retrieval polling or
automatic retry occurs. A local deadline cannot prove remote cancellation: timeout,
transport exception, interruption or incomplete preservation marks an ambiguous
attempt and blocks further dispatch. A late remote response may remain unavailable;
do not delete state or retry to resolve unknown billing/execution.

### Local approval manifest and budget gate

No authorized manifest is created by this task. Before execution the researcher
must supply a local file with schema `step12c-terminal-approval/1` and separately
review/pass its exact SHA-256. This is a local approval integrity check, not a
digital signature or identity-verification service. Required fields:

- `authorized: true`, nonempty `approvalID` and `researcher`, timezone-aware
  `approvedAt` and `expiresAt` covering dispatch time.
- `currency`, `pricingReference` and positive `totalCostCap`, all researcher-approved.
  Each approved request has positive `reservedMaximumCost`, calculated by the
  researcher from approved prices and worst-case input/output allowances. Their
  sum must not exceed `totalCostCap`; no invented price or measured cost is used.
- `requests`: a map containing only individually approved IDs from the three frozen
  selections. Each entry contains `maximumAttempts: 1`, `reservedMaximumCost`,
  `semanticRequestSha256` and `providerEnvelopeSha256` exactly matching the table.

Monetary fields are still pending. The runner checks approved reserved-cost bounds;
it cannot independently verify pricing or guarantee a provider's actual charge.
Approve a bound including 32768 output tokens and input/schema overhead before
setting `authorized: true`. Actual returned usage is preserved separately.

The API key is read from `OPENAI_API_KEY` only after execution approval and artifact
preparation, only in the researcher's execute invocation. No `.env` loader is used.
Never put the key in arguments, manifests, artifacts or source control.

### Attempt artifacts and stop state

Each request has one exclusive directory at
`var/study2_step12c/terminal/<request-id>/`. Existing attempts are never overwritten,
even under a replacement approval file. The global atomic `dispatch.lock` prevents
concurrent calls and remains after a process crash. A durable `STOP` marker prevents
any further request after ambiguous/error/incomplete outcomes. Stale locks and stop
markers require separate researcher investigation; the CLI offers no reset/bypass.

Before dispatch, the runner durably writes the exact approval bytes, semantic
request, provider input, envelope and association hashes. `events.jsonl` records
preparation, dispatch, elapsed progress, response preservation and terminal status.
It writes complete received HTTP body bytes to `response.raw` before parsing or
extracting anything. `provider-metadata.json` preserves returned ID/model/status,
usage, timing and error/incomplete fields; the raw body retains the full response.
`model-output.utf8` preserves the single exact output text when available, even if
subsequent review is required. HTTP headers and credentials are never logged.
All files stay in the ignored local pilot tree; no response artifact was fabricated
or obtained during this task.

The terminal reports transport/provenance status only (`response_recorded` or
`response_requires_review`); neither means semantic success. Semantic replay and
researcher review remain separate, explicitly requested tasks. No graph write or
provider response repair is performed.

### Offline checks and schema limits

Ten directly relevant focused tests cover pure envelope round trips, parser/local
failure isolation, approval gates, exact raw-byte preservation, non-overwrite,
timeout progress/blocking, HTTP errors and dry-run isolation. All passed after
correcting a test guard to permit argparse's noncredential locale lookup. All
transport tests use injected synthetic responses/keys; no actual credential lookup
or network call was made. The three real selected preflight requests were rebuilt
and all three terminal dry-runs succeeded.

Strict-schema checks use the documented limits already recorded in the local
Publication schema module: 10 nesting levels, 5000 object properties, 120000 total
schema-name/enum/constant characters, 1000 enum values, and 15000 string characters
for an individual enum with more than 250 values. They count local-reference depth
and fail closed on unsupported recursion/references; no Publication policy/schema
is imported. These are local structural checks, not remote API acceptance claims.

| Request | Nesting depth | Object properties | Schema string budget | Enum values |
|---|---:|---:|---:|---:|
| HS-01 | 5 | 183 | 1941 | 36 |
| GH-01 | 5 | 290 | 2982 | 51 |
| HUB-01 | 5 | 278 | 2812 | 50 |

### Exact terminal commands (from repository root)

Safe offline dry-runs, with no credentials or network:

```bash
python -m src.extraction.llm.pilot_terminal dry-run --request-id HS-01
python -m src.extraction.llm.pilot_terminal dry-run --request-id GH-01
python -m src.extraction.llm.pilot_terminal dry-run --request-id HUB-01
```

**Do not run execute until separately approved.** After placing a reviewed approval
file at the path shown, replace `RESEARCHER_APPROVED_SHA256` with the independently
reviewed digest. Run only the individually approved request; GH-01 or HUB-01 must
be selected explicitly in separate invocations, never automatically substituted.

```bash
python -m src.extraction.llm.pilot_terminal execute --request-id HS-01 \
  --approval var/study2_step12c/approval.json \
  --approval-sha256 RESEARCHER_APPROVED_SHA256 \
  --timeout 3600 --progress-interval 15
```

The command above is documentation only and was not executed by Codex. The plan
remains DRAFT / NOT AUTHORIZED. Monetary caps, pricing, approval identity/window,
approved request hashes, storage/review decisions and actual live execution await
researcher approval. CODEX_HANDOFF.md is unchanged.
