# Step 12C — Manifest-driven terminal integration v0.1

**Step 12C OPEN. All unexecuted requests NOT AUTHORIZED FOR LIVE EXECUTION.**
Implementation follows checkpoint `d399b6ccba62a98a6bcb2530a2dc2569154e374a`.
No provider call or real credential access occurred during this integration.

## Frozen routing and provenance

The loader pins the exact [v0.2 manifest](study2_step12c_calibration_selection_manifest_candidate_v0.2.json),
SHA-256 `2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`. It rejects changed bytes, IDs, family/wave/owner/version
mismatches, missing sources, snapshot/endpoint drift, changed ordered units, text,
coordinates or full semantic hashes. It uses the existing family readers/builders
and checks frozen authority/implementation fingerprints, without source expansion.
Runtime load/dry-run/execute reconstructs the selected owner's request and compares
all saved preflight bytes; it does not trust a saved envelope alone.

Routing is explicit: HS-01 stays historical request 1.0.0 and cannot execute;
HS-02–10 use HydroShare request 1.1.0 and the approved tool-role clarification.
GH-01 retains its original envelope; GH-02–10 use github-request/1.0.0 with
`github-provider-input/1.0.0`. All Hub requests retain ciroh_hub-request/1.0.0.
No automatic new prompt version, retry, source substitution or semantic gate change.
The full semantic request/hash remains separate from exact provider input, its hash,
strict-schema hash and envelope hash. Complete audit records remain in the full
request even when GitHub transport uses the accepted projection.

New artifacts reside only under ignored
`var/study2_step12c/calibration-preflight/1.0.0/<ID>/`:
`request-result.json`, `semantic-request.json`, `provider-input.txt`,
`provider-envelope.json` and `preflight.json`. Files are exclusively created;
repeated preparation verifies identical bytes, never overwrites drift or partial
artifacts. The three original records have separate copies here; their original
preflight paths, outputs and approval files are unchanged. All 32 previously pinned
pilot artifact hashes match. The original three envelopes reconstruct byte-for-byte.

## Exact sizes (bytes) and conservative allowances

Input is exact UTF-8 provider text, distinct from escaped semantic-hash bytes.
Envelope includes input, response schema and fixed provider settings. All cases use
OpenAI Responses API, gpt-5.6-sol, medium reasoning, store=false, no tools and 32768
maximum output tokens. Strict schemas are checked locally, not remotely certified.

Allowance is **one token per input-plus-schema UTF-8 byte**, not measured tokenization
or usage. Provider framing overhead is unknown and requires a separately approved
positive margin. Add the 32768 output ceiling when checking the researcher-approved
model context limit. Prices, caps and that context limit are not invented here.

| Request | Input bytes | Envelope bytes | Conservative input/schema allowance | GitHub unprojected input bytes |
|---|---:|---:|---:|---:|
| HS-01 | 14,130 | 28,054 | 26,504 | — |
| HS-02 | 17,008 | 30,950 | 29,382 | — |
| HS-03 | 17,974 | 32,020 | 30,348 | — |
| HS-04 | 17,560 | 31,572 | 29,934 | — |
| HS-05 | 15,623 | 29,559 | 27,997 | — |
| HS-06 | 15,655 | 29,597 | 28,029 | — |
| HS-07 | 17,905 | 31,923 | 30,279 | — |
| HS-08 | 17,257 | 31,210 | 29,631 | — |
| HS-09 | 16,103 | 30,056 | 28,477 | — |
| HS-10 | 17,155 | 31,117 | 29,529 | — |
| GH-01 | 28,320 | 50,646 | 47,633 | 28320 |
| GH-02 | 31,793 | 53,903 | 51,106 | 136455 |
| GH-03 | 49,325 | 72,831 | 68,638 | 132100 |
| GH-04 | 45,564 | 68,735 | 64,877 | 222769 |
| GH-05 | 29,356 | 51,481 | 48,669 | 115028 |
| GH-06 | 47,181 | 70,504 | 66,494 | 1339627 |
| GH-07 | 39,233 | 62,193 | 58,546 | 150319 |
| GH-08 | 25,867 | 47,790 | 45,180 | 25779 |
| GH-09 | 33,825 | 56,261 | 53,138 | 93211 |
| GH-10 | 27,334 | 49,373 | 46,647 | 28433 |
| HUB-01 | 41,104 | 63,501 | 59,824 | — |
| HUB-02 | 100,230 | 126,333 | 118,950 | — |
| HUB-03 | 48,365 | 70,989 | 67,085 | — |
| HUB-04 | 67,006 | 90,887 | 85,726 | — |
| HUB-05 | 23,345 | 44,519 | 42,065 | — |
| HUB-06 | 35,022 | 56,976 | 53,742 | — |
| HUB-07 | 46,606 | 69,188 | 65,326 | — |
| HUB-08 | 56,508 | 80,019 | 75,228 | — |
| HUB-09 | 31,556 | 53,219 | 50,276 | — |
| HUB-10 | 36,369 | 58,240 | 55,089 | — |

GH-06 remains reduced from 1,339,627 to 47,181 input bytes. GH-08 increases by
88 bytes because projection association metadata exceeds its small audit savings;
there is no silent size-based routing switch. No preflight construction failed.
HUB-02 has the largest conservative requirement: 151,718 tokens including output,
before the separately approved overhead margin. This is a planning allowance, not
a claim about model capacity or sufficient output budget.

**Hold status:** HS-01 is permanently non-dispatchable. All other 29 cases remain
held for explicit request/wave authorization and approved context/budget bounds.
Dry-run success cannot clear these holds. A too-small approved bound fails before
credential loading, attempt creation or transport; no text is truncated to fit.

## Researcher-operated commands

From the repository root, offline preparation only (safe to repeat when identical):

```bash
python -m src.extraction.llm.calibration_preflight --all
```

Prepare one case instead with `--request-id GH-06`. Neither form dispatches.
Individual dry-runs (one chosen ID per invocation):

```bash
python -m src.extraction.llm.pilot_terminal dry-run --request-id HS-02
python -m src.extraction.llm.pilot_terminal dry-run --request-id GH-06
python -m src.extraction.llm.pilot_terminal dry-run --request-id HUB-02
```

No batch execution exists. After separate researcher approval, the terminal command
for one approved request is the following; **it was not executed by Codex**:

```bash
python -m src.extraction.llm.pilot_terminal execute --request-id HS-02 \
  --approval var/study2_step12c/calibration-approval-v2.json \
  --approval-sha256 RESEARCHER_VERIFIED_APPROVAL_FILE_SHA256 \
  --timeout 3600 --progress-interval 15
```

Replace the approval digest with the separately reviewed exact file hash. Choose
each next ID explicitly; the CLI never advances automatically. GH-01/HUB-01 can
be individually authorized under version 2 without changing their original envelopes
or approval files. The old approval version is not accepted by the manifest workflow.
HS-01 is rejected before any source/credential read or attempt reservation.

## Approval version 2: fields still required

No live approval file is generated by this task. Supply a local
`step12c-terminal-approval/2` document containing:

- `authorized: true`, `approvalID`, `researcher`, timezone-aware `approvedAt` and
  `expiresAt`, and `manifestSha256` matching the pinned manifest.
- `currency`, researcher-verified `pricingReference`, positive `totalCostCap`.
  Prices and worst-case cost calculations remain the researcher's responsibility.
- `requests`, keyed by individually approved frozen IDs (never HS-01). Each row
  contains `maximumAttempts: 1`, positive `reservedMaximumCost`, and exact
  `semanticRequestSha256`, `providerInputSha256`, `schemaSha256`,
  `providerEnvelopeSha256`, `requestVersion`, `promptIdentifier` and
  `providerInputProjectionVersion` from that ID's new `preflight.json`. Include
  explicit null for the two nullable version fields when the metadata has null.
  Also include `wave`, `outputTokenCeiling: 32768`, positive integer
  `providerOverheadTokenAllowance`, `inputTokenAllowance` and `contextTokenLimit`.
  Input allowance must cover the printed conservative allowance plus overhead;
  context limit must cover input allowance plus output ceiling. These are approved
  bounds, not provider-measured facts. Confirm model support before authorizing.
- `waves`, keyed by A/B/C as applicable. Each entry has boolean `authorized`,
  `requestIDs` exactly matching approved request rows belonging to that wave, and
  positive `reservedCostCap`. Every row must belong to a declared wave. Request
  cost reservations must fit that wave's cap; summed wave caps must fit total cap.
  The selected wave must explicitly be authorized. Listing an ID alone is insufficient.
- `waveClearances`, an object (empty for A). B requires an A clearance; C requires
  both A and B clearances. Each includes `decision: "cleared_for_next_wave"`,
  `researcher`, timezone-aware past/current `clearedAt` and a 64-character lowercase
  `reviewRecordSha256` identifying the researcher's review record. This is an explicit
  researcher attestation bound by the approval-file hash, not automatic verification
  of review quality or inferred acceptance from prior transport completion.

Approve the review/storage plan, budgets, context/overhead bounds and wave-specific
execution before supplying these fields. Freeze any separately approved prompt
amendment before its wave; the current integration accepts only this exact manifest
and current approved versions. Wave C remains a qualitative challenge, not tuning
input. No full-corpus or production authorization follows from this approval format.

## Attempt lifecycle and separate semantic review

The existing global `var/study2_step12c/terminal/dispatch.lock`, STOP marker and
exclusive per-ID attempt directories remain shared across old/new approvals.
There is no second attempt namespace. Credentials resolve through the existing
Publications environment/ignored-.env loader only after all approval checks and
before irreversible reservation. A missing credential consumes no attempt.
Transport remains one synchronous request, configurable timeout/progress, no retry,
no substitution; ambiguous timeout blocks further dispatch. Approval bytes, exact
semantic/input/envelope bytes, manifest/version/hash associations and lifecycle
records are durable before dispatch. Complete raw response bytes are saved before
metadata/output extraction. No credential is logged.

Transport completion only reports recording status. Offline replay still uses
full frozen requests and expected semantic hashes. Researcher semantic review and
wave clearance are separate; structural/literal binding never authorizes KG writes.
Source incompleteness, conditional gates, inactive targets and all frozen exclusions
remain intact. No Step 12C closure, Step 13 execution or Step 14 alignment is implied.

## Focused offline verification

25 focused tests passed: eight new manifest/routing/wave/attempt tests plus the
17 directly affected terminal, preflight and projection tests. The existing
synthetic terminal tests now exercise unexecuted GH-01 rather than reopening HS-01;
a new regression blocks HS-01 before credentials. The eight new tests also passed
a focused rerun after adding an explicit existing-global-lock assertion.

Prepared 30 preflight cases; ran CLI dry-runs for **27 new selections only**:
9 HydroShare, 9 GitHub, 9 Hub. Network and actual credential-loader guards remained
active during these dry-runs. Their local results are in the ignored versioned
preflight directory's `dry-runs.json`. No original-three CLI dry-run, provider call,
broad suite, re-screening, graph write or handoff change occurred.
