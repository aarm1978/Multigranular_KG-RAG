# Study 2 Step 12C — Bounded semantic pilot plan candidate v0.1

**DRAFT / NOT AUTHORIZED — researcher review required before execution.**
Prepared 2026-10-09 against `02559039f348a638c6aeb86575c31ba1b93126a5` on
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
| Provider and exact versioned model ID | PENDING researcher approval |
| Temperature, top-p, seed, reasoning effort, response format/API mode | PENDING approval and actual model support; no assumed defaults |
| Maximum input tokens and output tokens per request | PENDING approval; include instructions, schema, inventories and source units in accounting |
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
if the complete approved request cannot fit. No provider runner is implemented here.

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
   Request and provider-envelope hashes are distinct. Request hashes are pending
   until final construction/approval; they are not fabricated in this draft.
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
approve provider/model/settings, token and monetary caps, attempt limits and
artifact storage; approve review rubric/ceiling and decision procedure; separately
authorize provider integration and execution. Context changes require a revised
manifest and request hash, not silent expansion. This draft and its commit provide
no live authorization. The tracked operational handoff remains unchanged.
