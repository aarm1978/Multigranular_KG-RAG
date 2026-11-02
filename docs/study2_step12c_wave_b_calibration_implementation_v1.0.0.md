# Step 12C — Wave B calibration implementation v1.0.0

**OFFLINE IMPLEMENTATION COMPLETE. LIVE EXECUTION NOT AUTHORIZED. Step 12C OPEN.**

Researcher authorization following `c0515eb91f7d804bfe255d984ccbf89b60a35ebc`
approves the three additions in the [proposal](study2_step12c_wave_b_prompt_calibration_candidate_v0.1.md),
with this sole refinement to the GitHub Function opening:

> A Function candidate must identify a named programming function or object-oriented method explicitly described in eligible prose, including its stated computational role. A scientific Method is not a software Function.

All remaining addition wording is implemented as approved. The proposal remains an
unchanged historical candidate; this record supersedes its unapproved-wording status
only. Paragraphs become ordered instruction strings, joining Markdown line wrapping
with spaces. The focused wording check compares every paragraph to the proposal and
applies only the approved refinement.

| Explicit request version | Prompt identifier | Base instructions |
|---|---|---|
| `hydroshare-request/1.2.0` | `hydroshare-wave-b-clarification/0.1.0` | Exact 1.1.0, retaining the notebook/Tool clarification |
| `github-request/1.1.0` | `github-wave-b-clarification/0.1.0` | Exact 1.0.0 |
| `ciroh_hub-request/1.1.0` | `ciroh-hub-wave-b-clarification/0.1.0` | Exact 1.0.0 |

The family `request_contract.py` builders accept explicit `request_version` values;
all defaults remain 1.0.0 and HydroShare 1.1.0 remains available unchanged. Parsers
verify the exact version/prompt/instruction pairing. Existing replay adapters pass
that version through request construction and verify its hash. Response schemas,
candidate validators, target profiles, semantic gates and source readers are unchanged.
GitHub `provider_input.py` adds explicit `github-provider-input/1.1.0` for request
1.1.0, using the unchanged selected-text/provenance and audit-reduction policy;
projection 1.0.0 retains its old request-version guard and exact bytes.

## Immutable execution amendment

[Wave B execution amendment v1.0.0](study2_step12c_wave_b_execution_amendment_v1.0.0.json)
SHA-256: `0733e14e2ad0dfe13b158cdd3cad2b4867097c0406601cc09fb95061db6cfe60`.
It is an offline execution specification, **not an approval file** (`authorized=false`).

Base selection manifest v0.2 stays byte-identical:
`2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`.
Scope is exactly HS-05–07, GH-05–07 and HUB-05–07. Each amendment row pins its entire
original selection record, original request/preflight hashes, approved instruction
hash and new request/input/schema/envelope hashes. Source owners, snapshots, accepted
endpoints, ordered units, exact text, authority hashes, completeness and diagnostics
are identical. Only request version, prompt identifier and added instructions change.

`wave_b_amendment.py` checks historical implementation bytes against the baseline
Git commit and original manifest pins, then checks the new executable file hashes
against the externally selected amendment digest. It records old/new fingerprints
and the eight changed implementation files explicitly. Unchanged dependencies retain
their hashes. The original `calibration_preflight.rebuild_request()` still rejects
changed historical fingerprints; no old manifest or check is rewritten. Explicit
amendment compatibility verification reconstructs the old requests before producing
new ones. Git baseline objects and the pinned local snapshots must remain available;
missing or mismatched inputs fail closed without recovery/downloads.

New ignored artifacts are under:
`var/study2_step12c/wave-b-preflight/1.0.0/<amendment-sha256>/<request-id>/`.
Each contains the full semantic request/result, exact provider input and envelope,
preflight hashes/versions/size accounting, and a copy of the amendment. Creation is
exclusive; subsequent preparation must match existing bytes. GitHub's complete
semantic request remains replay authority. No historical file is overwritten.

## Offline results

**92 focused T1/T2 tests passed**, comprising 11 new Wave B tests and 81 directly
affected request-contract, replay, projection, preflight, terminal and wave tests.
Synthetic transport tests exercise v3 clearance/hash rejection, sequential nine-ID
execution, one-attempt recording and non-overwrite without live requests. Existing
lock, STOP, timeout and failure-isolation tests remain passing. An initial run in an
environment lacking `jsonschema` failed on that missing dependency; the complete
focused run passed in the existing Python 3.12 GraphRAG environment. No dependencies
were installed and no broad suite was run.

All **12 Wave A requests, provider-input/envelope bytes and replay-report bytes**
reproduced exactly, including HS-01's request SHA-256
`66a3fd974108b18b58d0b6effed8924669558509502760e43699b2858b07f8c0`.
Verification used read-only replay and wrote no historical output. The amendment
records all twelve association hashes. Historical artifacts, approvals, handoff,
base manifest and unrelated catalog modification passed before/after hash checks.

All **nine preflights and terminal dry-runs passed** (three per family). These counts
are exact UTF-8 serialization sizes; allowances are **one token per input/schema
byte, not measured tokens**, and exclude researcher-approved provider overhead.
Output ceilings stay 32,768. GPT-5.6 Sol, medium reasoning, store=false and no tools
remain unchanged. Local strict-schema checks pass; no new remote acceptance claim.

| Request | Input bytes | Envelope bytes | Conservative input + schema allowance |
|---|---:|---:|---:|
| HS-05 | 17,561 | 31,503 | 29,935 |
| HS-06 | 17,593 | 31,541 | 29,967 |
| HS-07 | 19,843 | 33,867 | 32,217 |
| GH-05 | 31,943 | 54,080 | 51,256 |
| GH-06 | 49,768 | 73,103 | 69,081 |
| GH-07 | 41,820 | 64,792 | 61,133 |
| HUB-05 | 25,564 | 46,750 | 44,284 |
| HUB-06 | 37,241 | 59,207 | 55,961 |
| HUB-07 | 48,825 | 71,419 | 67,545 |

| GitHub request | Previous 1.0.0 projected bytes | New full semantic input bytes | New 1.1.0 projected bytes |
|---|---:|---:|---:|
| GH-05 | 29,356 | 117,615 | 31,943 |
| GH-06 | 47,181 | 1,342,214 | 49,768 |
| GH-07 | 39,233 | 152,906 | 41,820 |

The 2,587-byte projected increase per GitHub request contains the approved prompt
and identifier changes. No selected scientific text was truncated or rewritten.
Verification results are local at
`var/study2_step12c/wave-b-preflight/verification/dry-runs.json`.
There are no technical holds; **all nine remain held for live authorization**.

## Explicit approval routing and operation

Terminal/wave CLIs require both `--amendment` and `--amendment-sha256` for this route.
Only the nine Wave B IDs are admissible. `step12c-terminal-approval/3` retains v2's
researcher identity, validity window, base-manifest hash, per-request hash/version
fields, monetary reservations, context limits, maximumAttempts=1, wave authorization
and prior-wave clearance rules. It additionally requires:

- Top-level `executionAmendmentSha256` and `executionAmendmentVersion`
  (`study2-step12c-wave-b-execution/1.0.0`).
- The identical `executionAmendmentSha256` on each approved request row.
- Wave B only, with all nine IDs for whole-wave execution. Context bounds may not
  exceed the existing published-limit constant (1,050,000 tokens); allowance plus
  separately approved overhead and 32,768 output tokens must fit.

Approval v2 cannot authorize amended envelopes. Researcher review must separately
supply Wave A clearance with its review-record digest, the exact amendment and new
hashes, individual/aggregate monetary reservations, currency/pricing reference,
context allowances/overhead and an approval validity window. No prices, budget
approvals or authorized files are created here. Credential loading still occurs
only after approval verification, before reserving an irreversible attempt.

The existing one-request transport and sequential wrapper are reused. Amendment
bytes/hash/version are preserved with each attempt and in the wave summary.
Attempt directories remain `terminal/<request-id>` across versions; an amendment
cannot create a retry namespace. Global/wave locks, STOP behavior, non-overwrite,
no retries and advancement only after verified `response_recorded` remain enforced.
Historical HS-01 cannot dispatch; this amendment cannot dispatch any Wave A ID.

From the repository root, with an existing compatible Python environment:

```bash
AMENDMENT=docs/study2_step12c_wave_b_execution_amendment_v1.0.0.json
AMENDMENT_SHA=0733e14e2ad0dfe13b158cdd3cad2b4867097c0406601cc09fb95061db6cfe60
shasum -a 256 "$AMENDMENT"
python -m src.extraction.llm.wave_b_amendment preflight \
  --amendment "$AMENDMENT" --amendment-sha256 "$AMENDMENT_SHA"
python -m src.extraction.llm.wave_b_amendment verify-legacy \
  --amendment "$AMENDMENT" --amendment-sha256 "$AMENDMENT_SHA"
python -m src.extraction.llm.pilot_terminal dry-run --request-id GH-06 \
  --amendment "$AMENDMENT" --amendment-sha256 "$AMENDMENT_SHA"
```

Only after separate researcher authorization, the existing terminal or wave `execute`
command accepts these same amendment arguments plus `--approval` and the independently
verified `--approval-sha256`; the wave command must specify `--wave B`. No execute
command was run against real inputs. Transport, parsing and literal validation remain
separate from semantic acceptance. No Step 13 acceptance process is implemented;
Wave C calibration/version changes remain separately controlled.
