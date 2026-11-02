# Study 2 Step 12C — Source-diverse calibration plan candidate v0.2

**DRAFT / NOT AUTHORIZED FOR LIVE EXECUTION.** Prepared 2026-10-09 at
`b64b6c2bc9913755ff2a820e9054279fc8ab766e`. Researcher approval of the expanded
30-request scope permits this selection/design work, not provider execution.

## Purpose, authority and freeze

Identify systematic semantic errors and omission opportunities before Step 13 through
**10 distinct owners per family: 30 requests, including historical HS-01; at most
29 new calls**. This is purposive development calibration, not representative sampling,
a new gold standard or confirmatory evaluation. No P/R/F1 or population accuracy claims.

Binding authorities remain [Step 11 v0.3](study2_step11_source_specific_semantic_contracts_v0.3.md)
and its [acceptance](handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md), ontology
v0.1.6, accepted [12A](handoffs/STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md)
and [12B](handoffs/STUDY2_STEP12B_OFFLINE_VALIDATION_ACCEPTANCE.md), and the approved
[HydroShare clarification](study2_step12c_hydroshare_prompt_calibration_candidate_v0.1.md).
This candidate replaces the three-request *prospective workload assumption* without
editing the historical v0.1 plan, its original requests, envelopes or approvals.

The [exact selection manifest](study2_step12c_calibration_selection_manifest_candidate_v0.2.json)
is candidate-frozen before any new provider output; SHA-256 of exact JSON file bytes:
`2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`. It pins owner/accepted endpoint, corpus and canonical owner-record
hashes, original ordered unit IDs/spans, authority/selected-text hashes, lineage,
completeness and diagnostic projections, risk rationale and intended prompt version.
No raw prose, code, notebook output or credentials is included in tracked artifacts.
Owner titles are identifying metadata. Selection freeze is not live authorization.

## Bounded selection and context

Screened only metadata: 42 HydroShare titles/README availability; the first 45 GitHub
repository names; Hub titles/routes at indices 0–44 and 55–114. Then inspected the
nine new owners per family listed below through existing readers and targeted eligible
passages. Stop after nine additions per family; no exhaustive semantic/file audit,
LLM-output ranking or accepted-assertion yield optimization. Original HS-01 motivates
the approved general risk questions, not new truth labels or preferred outputs.

Use one owner per request. Keep complete selected adapter units in manifest order,
without stitching text, cross-owner evidence or executing code. Whole HydroShare
abstracts are retained. HS-03/07 add their complete original Phase A README text;
HS-04 adds only its complete opening file-role section before HTML markup, using
explicit original bounds. Raw README fields, not cleaned text, are authoritative;
source verification attests their association with the pinned record, not acquisition
integrity. Optional absent READMEs remain absent. Other context is deliberately bounded;
all GH/Hub requests declare incomplete caller coverage, and HS-04 does too.

GitHub retains Phase A readme.text precedence, additional eligible downloaded prose
and original notebook Markdown cells. Full original-reader diagnostic records are
reconstructable from pinned sources; the manifest projects locations/status/reasons
and hashes complete diagnostics/read records. Excluded code cells, dependencies,
licensing/admin content and uncertain passages are not selected merely because a
reader exposed a possible unit. Hub preserves static-visible unit and fenced-context
boundaries. No verified Section mapping is supplied: heading ordinals survive and
Section IDs remain null. A source read success never proves semantic completeness.

## Frozen request roster

Characters count selected original Unicode text only, not instructions, metadata,
JSON escaping or response schemas. Labels abbreviate owners; exact endpoints and
all spans/hashes are in the manifest. Every listed risk is an opportunity to review,
not a required positive prediction.

### HydroShare

| Wave | Request | Owner | Units / characters | Primary opportunity |
|---|---|---|---:|---|
| A | HS-01 | Stream Temperature Seasonal Thermal Regime Data | 1 / 1,056 | tool model typing |
| A | HS-02 | TempEst 2 development data | 1 / 2,195 | tool model typing |
| A | HS-03 | 2023 Vermont high-water marks | 2 / 2,218 | readme measurement |
| A | HS-04 | Scientific workflows in the cloud | 2 / 1,818 | scientific workflow |
| B | HS-05 | CONUS bankfull/mean-flow geometry | 1 / 815 | variable vs theme |
| B | HS-06 | CIROH-2i2c JupyterHub | 1 / 840 | sparse ambiguous |
| B | HS-07 | RIce-Net dataset | 2 / 2,165 | tool model typing |
| C | HS-08 | AORC across CAMELS basins | 1 / 2,428 | variable vs theme |
| C | HS-09 | SI23 Nextgen-aridity CFE outputs | 1 / 1,282 | generation vs reference |
| C | HS-10 | NextGen research-scale workflow | 1 / 2,315 | scientific workflow |

### GitHub (CIROH-UA)

| Wave | Request | Owner | Units / characters | Primary opportunity |
|---|---|---|---:|---|
| A | GH-01 | api-nwm-gcp | 1 / 287 | repository purpose |
| A | GH-02 | cfe_v1.0 | 4 / 5,021 | uses mentions implementedBy |
| A | GH-03 | ciroh_pyngiab | 15 / 4,188 | notebook markdown |
| A | GH-04 | hydrotools | 16 / 5,673 | function algorithm |
| B | GH-05 | forcingprocessor | 6 / 2,223 | workflow dataset use |
| B | GH-06 | neuralhydrology | 16 / 4,596 | own product model version |
| B | GH-07 | PINN_workshop_ciroh | 12 / 2,156 | function algorithm |
| C | GH-08 | CAMELS_data_sample | 4 / 986 | sparse ambiguous |
| C | GH-09 | NGIAB_data_preprocess | 10 / 2,759 | workflow dataset use |
| C | GH-10 | rust-lstm | 5 / 1,329 | uses mentions implementedBy |

### CIROH Hub

| Wave | Request | Owner | Units / characters | Primary opportunity |
|---|---|---|---:|---|
| A | HUB-01 | AORC data-access article | 20 / 2,641 | procedure step ancestry |
| A | HUB-02 | nwmurl library | 50 / 4,501 | example parameter parent |
| A | HUB-03 | NETWA Getting Started | 19 / 3,946 | procedure step ancestry |
| A | HUB-04 | NGIAB Data Preprocess | 32 / 3,541 | workflow |
| B | HUB-05 | Hydrofabric introduction | 5 / 583 | typed products |
| B | HUB-06 | TEEHR | 9 / 1,063 | describes relations |
| B | HUB-07 | PyNGIAB | 21 / 2,538 | example parameter parent |
| C | HUB-08 | NWM-ML | 34 / 2,782 | typed products |
| C | HUB-09 | NGIAB Contact Us | 10 / 958 | sparse ambiguous |
| C | HUB-10 | NGIAB Getting Started | 12 / 2,092 | describes relations |

## Coverage, gaps and integrity

- **HydroShare:** Tool/Model roles (02, 07, 10); variables versus themes (05, 08);
  README-only Measurement opportunity (03, not presumed sufficient); scientific
  Workflow (04, 09, 10); generation versus reference (05, 08, 09); sparse/ambiguous
  scientific support (06 and original 01). HS-08's abstract units cannot authorize
  Measurement even though units of measure occur there.
- **GitHub:** purpose across diverse repositories, including learning-only 08;
  uses/mentions/implementedBy (02, 05, 10); Workflow/data use (03, 05, 09);
  prose Function/Algorithm (02, 04, 07); own-package version statement (06) versus
  referenced NWM/dependency versions (02/10). Root README, additional metrics README
  (04), descriptive MODEL.md (02), RST tutorial prose (06) and original notebook
  Markdown (03/06/07) are represented. Eligible CITATION prose is **unavailable in
  the selected manifests**; `.cff` is not a substitute. This is not a corpus-wide
  absence claim. No external accepted Method inventory is supplied.
- **Hub:** typed products/describes (05/06/08/10), Procedure/Step ancestry (01–04),
  possible Example and prose-supported parent-bound Parameter (02/07), Workflow
  (04/07/08), multi-unit and uncertain-MDX boundaries, and sparse/admin-overreach
  challenge (09/10). Operational onboarding may not support a substantive scientific
  Procedure. Displayed snippets are only possible Example context.

All 27 new request constructions succeeded; the three original request-result
records reconstructed exactly. No selected-source integrity failure was observed.
Computed hashes are local fingerprints; Hub content_sha256 was checked, while its
file_sha256 is retained without raw-file acquisition verification. Original scoped
warnings remain, including many GitHub passage holds and Hub dynamic/component
visibility holds. No held passage is silently declared visible or used as evidence.
No positive target, parent acceptance or semantic gate satisfaction is inferred.
No missing stratum is filled by forced predictions or unapproved source expansion.

## Prompt versions, waves and tuning boundary

HS-01 remains executed `hydroshare-request/1.0.0`; its authentic response, replay,
ambiguities and hashes remain historical. HS-02–10 explicitly use
`hydroshare-request/1.1.0`, prompt `hydroshare-tool-role-clarification/0.1.0`.
Response remains `hydroshare-response/1.0.0`. GH retains `github-request/1.0.0`;
Hub retains `ciroh_hub-request/1.0.0`; response contracts/profile remain unchanged.
The legacy GH/Hub contracts have no separate prompt-ID field: manifest instruction
hashes identify their exact wording. Never invent an identifier in their hashed body.

- **Wave A:** 12 requests, 11 new calls; IDs 01–04 per family. Review all within the
  ceiling before deciding any new prompt wording. Do not rerun HS-01. GH-01/HUB-01
  execute only their unchanged existing selections/envelopes after separate approval.
- **Wave B:** 9 new calls; IDs 05–07. Use only prospectively approved versions
  finalized before dispatch. Outcomes may diagnose residual systematic issues.
- **Wave C:** 9 new calls; IDs 08–10. Lock every family's final prompt and rubric
  before *any* C output. Reserve these outputs for an independent qualitative
  challenge check; do not use them for prompt tuning, case replacement or reruns.

At most **two approved prospective clarification rounds per family**; HydroShare
v1.1.0 counts as round one. One remaining HS round may follow A or B; GH/Hub have
at most two. No round automatically authorizes another call or reuses an executed ID.
A later approved version needs a new immutable version/hash amendment referencing
this selection freeze; owner/unit context stays fixed. Preserve the old manifest
and request hashes, and never relabel historical requests with new instructions.
If no amendment is approved, use the versions already pinned here.

Wave C independence means its outcomes cannot inform tuning. Its source metadata
and selected passages were inspected for eligibility, so it is not blinded or a
statistically independent test set. Related NextGen products recur across families;
report this overlap and never make independent-sample performance claims. A defect
found in C can block production, but repairing/tuning it requires a separately
approved future development/challenge design, not reuse of this C as fresh evidence.

## Two-direction review and workload (proposed, pending approval)

For each request, preserve machine dispositions, originals, independent node/edge
citations, dependencies and semantic gates before recording researcher judgments.
Review **output-to-source**: supported, unsupported, ambiguous, or insufficient
selected context, with exact unit references and a short reason. Separately read
the selected source once **source-to-output** and note at most five salient omission
opportunities: the potential allowlisted claim, its span, and whether it is absent,
unresolved or outside eligible context. Opportunities are not exhaustive gold labels.
Record no-evidence/ambiguous claims separately from technical incompleteness.

Proposed ceiling: **25 minutes/request** (15 assertion support, 10 source-to-output),
at most 40 proposed node/edge/abstention records and five omission notes/request;
30 requests at most 750 minutes plus 30 minutes synthesis/family = **14 hours**.
Review in original candidate order, not cherry-picked successes. Stop at either
ceiling, log reviewed IDs and exact unreviewed count, and hold production readiness;
request an explicit workload revision rather than inferring acceptance. Historical
HS-01 is reviewed as preserved output, not regenerated; any advisory review remains
advisory until researcher judgment. No exhaustive corpus labeling or LLM truth labels.

Diagnostic taxonomy: (1) source/eligibility/integrity failure; (2) parse or literal
binding failure; (3) wrong entity type or unsupported granularity; (4) relation
strength/direction or capability-versus-use/generation error; (5) identity/endpoint
or parent-dependency error; (6) own-product/version confusion; (7) selected-context
omission or context insufficiency; (8) duplicate/abstention misuse. Record multiple
codes and uncertainty where appropriate. Tally qualitative patterns with reviewed
workload denominators, not precision, recall, F1, confidence intervals or gold scores.

## Sizes, approval fields and narrow implementation dependencies

Selected text totals are approximately **17.1k HydroShare, 29.2k GitHub and 24.6k Hub
characters**. Per-request text ranges from 287 to 5,673 characters. Exact bytes,
characters, unit counts and canonical semantic-request bytes are recorded separately.
Serialized requests are much larger because they retain profiles and read records:
HydroShare 14–18 kB, GitHub 26–1,340 kB, Hub 23–100 kB (decimal kB, rounded).
**GH-06 is 1,339,638 bytes**, largely due to full reader diagnostics/read records.
These are actual serialization sizes, not measured tokens. No verified compatible
model tokenizer is established here. A conservative one-token-per-UTF-8-byte allowance
would exceed 1.34M for GH-06 before schema/framing overhead; this flags a mandatory
context/budget feasibility hold, not an assertion about the model's supported limit.
Do not silently truncate context, compress diagnostics inside a frozen request,
substitute a repository or dispatch this oversized request without approved fit.

Future implementation, separately scoped; **no runner/preflight change in this task**:

1. Extend `src/extraction/llm/pilot_preflight.py` from three hard-coded selections
   to explicit manifest/version loading. Verify manifest digest, exact owner/endpoint
   and source snapshots, unit order/spans, diagnostic hashes and semantic request
   digest. Reconstruct from the pinned Phase A fields and declared README sections;
   use original reader settings. Verify saved raw/text digests externally without
   changing computed-only integrity metadata, which would change request hashes.
   Keep original three envelopes byte-identical. New IDs get separate ignored
   preflight directories. Compute exact transmitted input/envelope hashes, strict
   schema checks and token/context/cost bounds. GH-06 size must be resolved by an
   approved feasibility decision; changing the accepted serialized diagnostic
   contract would be a separate proposal, not an incidental optimization.
2. Extend `src/extraction/llm/pilot_terminal.py` ID/owner checks and approval schema
   to bind manifest digest, individual request ID, exact semantic/prompt version,
   request/envelope hashes, wave lock and approved budget. Preserve individually
   selected sequential researcher-terminal dispatch, pre-dispatch credential loading,
   no automatic retries, one exclusive attempt/ID, global lock and ambiguous-timeout
   stop. Historical HS-01 is permanently non-dispatchable. Preserve original GH/HUB
   attempt identities, not a second namespace allowing duplicate calls.
3. Retain durable exact envelope/transmitted bytes, approval association, lifecycle,
   raw HTTP response, extracted output bytes, metadata/usage before offline replay.
   Replay from the exact versioned source/request inputs with expected_request_sha256;
   preserve local parse/evidence failure isolation and selected-unit enforcement.
   Use ignored `var/study2_step12c/` with distinct preflight/terminal/analysis/review
   artifacts, no overwrites. Add only focused manifest-routing, drift, version,
   per-ID approval, wave gate, no-retry and immutable-replay tests when implemented.

Proposed provider settings retain OpenAI Responses API, `gpt-5.6-sol`, reasoning
`medium`, `store=false`, no tools, existing strict schemas. Existing original output
ceilings remain 32768. Propose 32768 for new IDs, **pending per-request approval**;
no provider compatibility, sufficiency or billing guarantee. Monetary caps, pricing
reference/date, input/output token bounds, transport timeout, reserved cost per ID,
aggregate/wave budgets, approver/window, storage and review ceilings remain pending.
No credentials or approval manifest is created. There are zero automatic retries
and no replacement slots among the 30. A failure consumes its dispatched attempt.

## Stop conditions and production-readiness decision

Stop/hold on source/request/approval drift, unsafe or unverified selected evidence,
unknown version, unsupported schema/provider behavior, token/budget overflow,
ambiguous transport status, lost raw bytes or unreproducible replay. Keep technical
failures distinct from semantic ambiguity and incomplete input. Local candidate
failures exclude only actual dependents, never independent valid records. No repair
of model output or automatic semantic gate attestation.

Researcher may approve **Step 13 planning only** after all three families and every
wave have documented dispositions, both-direction review within approved ceilings,
no unresolved critical integrity/identity/contract defect, and a recorded judgment
that systematic errors/omissions and review workload are manageable. Any unreviewed
output, unresolved C challenge defect, failed feasibility bound or missing family
is HOLD with explicit remaining work. No minimum yield or invented accuracy cutoff.
A go decision does not authorize production calls, KG acceptance or Step 14.

Keep README-only Measurement, own-product ModelVersion, six purpose seeds plus
independent hasPurpose evidence, and Hub Procedure/Step parent gates unchanged.
No accepted external endpoints or authorized HydroShare stubs are added; GH seed
endpoints stay distinct. C-C16 remains unresolved/non-KG pending accepted Publication
production and later authorization; no name/URL identity alignment. DataService /
servesDataset remain inactive; abstract superclasses and D-26 are not model-authorable.
Frozen Publication authorities, Steps 7–9, Phase A/B and ontology remain unchanged.
No live calibration or Step 12C closure is claimed. CODEX_HANDOFF.md is unchanged.

## Offline preparation checks

Constructed the 27 new requests using accepted source readers/builders only; rebuilt
and compared all three original request-result records exactly. Verified 30 IDs,
10 distinct accepted owners/family, assigned wave counts, unit order and source/hash
associations. All originals in the three-request preflight and HS-01 terminal/analysis
trees retained their hashes. No test suite, provider call, corpus acquisition,
extractor prediction, graph write or source/authority modification occurred.
