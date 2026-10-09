# Step 12C — Researcher-operated wave execution v0.1

**Step 12C OPEN. Live execution remains NOT AUTHORIZED.**
Implementation follows `47ee5221edc2de334d6501a8ba67241eaf256d33`.
The researcher may execute one complete approved wave before joint semantic
analysis. Transport completion does not establish semantic acceptance or KG authorization.
Frozen contracts, manifest, prompts and historical artifacts remain unchanged.

## Execution boundary

`src.extraction.llm.pilot_wave` calls the existing `pilot_terminal.execute()` once
per request, in this exact Wave A order:
HS-02, HS-03, HS-04, GH-01, GH-02, GH-03, GH-04, HUB-01, HUB-02, HUB-03, HUB-04.
HS-01 is historical and excluded. No new transport, retries, replacements or skips.

Before dispatch, every member's frozen preflight is reconstructed and verified and
the exact approval v2 bytes/SHA are checked against every request's hashes,
versions, wave, context and budgets. Partial-wave approvals cannot run this wrapper.
An existing attempt for any member stops the whole wave before its first call.
Each call retains credential resolution before request-attempt reservation, global
transport locking, elapsed-time progress and complete durable response preservation.
A separate exclusive `wave.lock` prevents simultaneous wrappers and interleaved
standalone requests. Neither stale lock nor STOP is automatically removed/recovered.

Advance requires the exact `response_recorded` return **and** matching persisted
request/approval associations, raw-response digest, completed response status,
extracted output bytes and lifecycle outcome. Every exception, ambiguous timeout,
non-completed response, missing credential, STOP or artifact mismatch stops the wave.
No individual semantic review is required between confirmed successes.

Wave records live at `var/study2_step12c/terminal/waves/<WAVE>/<APPROVAL_SHA>/`:
`approval.json`, append-only/fsynced `summary.jsonl`, and final `summary.json`.
The journal preserves in-flight entries on a hard crash; an in-flight entry is not
proof of dispatch or completion. Per-request lifecycle events are authoritative.
Summaries list invocation-attempted IDs, outcomes, provider status when available,
artifact directories and remaining unattempted IDs, without credentials or semantic
judgments. Existing wave records are never overwritten/resumed. A stopped invocation
requires researcher inspection, not an automatic retry. Missing credentials create
no request attempt or STOP, although the stopped wrapper invocation is recorded.

Waves B/C use the same CLI with separately reviewed complete-wave approval v2 files.
B requires explicit A clearance; C requires A and B clearances, each referencing a
researcher review record hash. These are never inferred from completed responses.
Only the current pinned manifest/versions run. Future prompt calibration requires
separately approved versioned execution hashes and compatible frozen preflights;
this wrapper cannot silently adopt it.

## Proposed Wave A draft (not authorization)

The offline helper verifies existing frozen preflights and writes a new draft with
`authorized=false`, `waves.A.authorized=false`, and blank researcher/approval dates.
It never loads credentials. During implementation, the draft was prepared at
`var/study2_step12c/approvals/wave-A.draft.json` under network/credential guards.
No authorized approval was created and no wave was executed.

Published [GPT-5.6 Sol specifications](https://developers.openai.com/api/docs/models/gpt-5.6-sol),
checked 2026-10-09: context 1,050,000 tokens; maximum output 128,000.
The pilot retains 32,768 output tokens. Standard prices are $4/$20 per million
input/output tokens, with cache writes at 1.25 times uncached input pricing;
above 272,000 input tokens, input/output rates multiply by 2/1.5.
The helper conservatively reserves cache-write rates ($5 input/$20 output here),
without cache-read discounts, and rounds each request upward to cents.
These published promotional rates require rechecking before authorization.

Input allowances are the existing input-plus-schema byte allowance plus a proposed
4,096-token framing margin, **not measured token counts**. Researcher review must
confirm the margin, applicable account/service tier, surcharges, current rates and
expiry. Monetary reservations are local admission checks, not a provider-enforced
billing cap. The unchanged envelopes do not add a service-tier parameter.

| Request | Input allowance | Proposed USD reservation |
|---|---:|---:|
| HS-02 | 33,478 | 0.83 |
| HS-03 | 34,444 | 0.83 |
| HS-04 | 34,030 | 0.83 |
| GH-01 | 51,729 | 0.92 |
| GH-02 | 55,202 | 0.94 |
| GH-03 | 72,734 | 1.02 |
| GH-04 | 68,973 | 1.01 |
| HUB-01 | 63,920 | 0.98 |
| HUB-02 | 123,046 | 1.28 |
| HUB-03 | 71,181 | 1.02 |
| HUB-04 | 89,822 | 1.11 |

Reservations total $10.77; proposed wave/total cap rounds up to **$11**.
Maximum input allowance plus output is 155,814 tokens. No selected context was changed.

## Mac terminal commands — researcher only

Run from the repository root with the project's Python environment active.
The preparation command requires a **new** output path; the draft above already
exists, so inspect it directly or choose a different unused draft filename.

```bash
python -m src.extraction.llm.pilot_wave prepare-wave-a \
  --output var/study2_step12c/approvals/wave-A.draft.json
python -m json.tool var/study2_step12c/approvals/wave-A.draft.json
```

Review every ID/hash/version, context allowance and reservation against preflights.
Create a separate reviewed copy; `cp -n` avoids overwriting an existing approval.
Only the researcher may fill approvalID, researcher, approvedAt/expiresAt (timezone
required), confirm currency/pricingReference and caps, change the status label and
explicitly set both authorization booleans true. Do not change request hashes to
bypass drift. No program in this task performs those authorization edits.

```bash
cp -n var/study2_step12c/approvals/wave-A.draft.json \
  var/study2_step12c/approvals/wave-A.approved.json
open -e var/study2_step12c/approvals/wave-A.approved.json
python -m json.tool var/study2_step12c/approvals/wave-A.approved.json
shasum -a 256 var/study2_step12c/approvals/wave-A.approved.json
```

After reviewing the exact bytes and independently retaining their digest, paste it
below. These execution commands are **not authorized by this note** and were not run.
Credentials remain local environment/ignored `.env`; never paste them into commands.

```bash
PILOT_APPROVAL_SHA256='PASTE_REVIEWED_64_HEX_SHA256'
printf '%s  %s\n' "$PILOT_APPROVAL_SHA256" \
  var/study2_step12c/approvals/wave-A.approved.json | shasum -a 256 -c -
python -m src.extraction.llm.pilot_wave execute --wave A \
  --approval var/study2_step12c/approvals/wave-A.approved.json \
  --approval-sha256 "$PILOT_APPROVAL_SHA256" \
  --timeout 1800 --progress-interval 15
python -m json.tool \
  "var/study2_step12c/terminal/waves/A/$PILOT_APPROVAL_SHA256/summary.json"
```

If a hard interruption prevented a final summary, inspect the journal without
relaunching the wave:

```bash
tail -n 1 "var/study2_step12c/terminal/waves/A/$PILOT_APPROVAL_SHA256/summary.jsonl"
```

Offline replay and joint researcher review follow the complete successful wave.
No Step 12C closure, semantic adjudication or graph acceptance is implied.

## Focused verification

25 offline synthetic tests passed: 9 in `test_pilot_wave.py`, 8 in
`test_pilot_terminal.py`, and 8 in `test_calibration_terminal.py`. They cover full-wave
scope and version/hash checks, draft non-authorization, sequential confirmed-only
advancement, artifact tampering, missing credentials, incomplete/ambiguous responses,
locks, immutable attempts and later-wave clearances. All 11 actual Wave A frozen
preflights verified offline; all 32 pinned historical artifact hashes still match.
No live execution, real credentials, semantic replay or graph writes occurred.
