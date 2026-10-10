# Step 12C — Final clarification and Wave C offline preparation v1.0.0

**OFFLINE IMPLEMENTATION AUTHORIZED; LIVE EXECUTION NOT AUTHORIZED. Step 12C OPEN.**
Baseline: `31e8d528c86b4915704cd68512a3d8e390c53d18`.
Wave C is the final qualitative challenge, not a prompt-development sample.
Its results must not drive further tuning. Critical defects may block production;
they never authorize silent retries, response repairs or retrospective corrections.
Step 13 semantic acceptance is a separate workstream and is not implemented here.

## Approved final additions

The following paragraphs append to the exact respective 1.1.0 instructions.
All prior wording, default 1.0.0 routes, response schemas, source eligibility and
semantic gates remain unchanged. HydroShare 1.2.0 and its prompt are unchanged.

### GitHub

> Distinguish repository-level usesModel/usesTool from tutorial demonstrations, optional capabilities and illustrative examples. A model shown as an example in a tutorial does not alone establish that the repository uses it in scientific processing. However, explicit source-grounded repository use remains admissible, including genuinely documented example execution; do not categorically exclude tutorials or require runtime logs. Evaluate mentions and uses separately.
>
> Assign each RepositoryPurpose category only when eligible prose supports that purpose of the repository itself. An individual notebook's processing sequence does not automatically establish workflow_orchestration as a central repository purpose. Multiple categories require independently sufficient support, although one explicit passage may support several. Preserve the existing six-category vocabulary and unresolved classifications.

### CIROH Hub

> A Step must represent a supported instructional action within a coherent Procedure. Lists of available capabilities, possible operations or automatic consequences do not by themselves constitute a sequence of instructed Steps. Narrative instructions are admissible; do not require imperative wording or numbered lists.
>
> Do not classify a data warehouse, storage system, infrastructure layer or generic services stack as Tool merely because it appears in a component hierarchy. Require independent evidence of an identifiable software Tool. Preserve valid hasComponent relations only when their endpoints are adequately typed. Do not invent alternative classes or activate excluded DataService targets.
>
> Preserve parent-dependent Example extraction, exact parentPath requirements and prose-grounded Parameter rules. Never promote proposed parent relationships to semantic acceptance.

## Frozen prospective versions

| Requests | Request version | Immutable prompt identifier | Projection |
|---|---|---|---|
| HS-08–10 | `hydroshare-request/1.2.0` | `hydroshare-wave-b-clarification/0.1.0` (unchanged) | None |
| GH-08–10 | `github-request/1.2.0` | `github-wave-c-role-purpose-clarification/0.1.0` | `github-provider-input/1.2.0` |
| HUB-08–10 | `ciroh_hub-request/1.2.0` | `ciroh-hub-wave-c-step-tool-clarification/0.1.0` | None |

The existing family builders/parsers enforce explicit opt-in and exact instruction/
prompt/version pairings; unknown versions fail closed. The GitHub projection retains
its audit-reduction policy and every selected unit unchanged. Full semantic requests
remain replay authority. Old projection versions retain their original version guards.

## Amendment and execution boundary

The existing `wave_b_amendment.py` now accepts explicit `--wave C`; its default stays
B. It does not create a new transport or weaken the original manifest/B checks.
The additive [Wave C amendment](study2_step12c_wave_c_execution_amendment_v1.0.0.json)
pins the original v0.2 selection manifest and exact accepted B amendment
`0733e14e2ad0dfe13b158cdd3cad2b4867097c0406601cc09fb95061db6cfe60`.
C's old implementation fingerprints must equal B's accepted new fingerprints at the
baseline commit. Its new fingerprints explicitly declare changed files. No prior
record is rewritten; unamended historical loaders still reject changed executable
files. Historical reconstruction remains available at the frozen checkpoint.

Every C row pins its entire original selection record, source/owner/endpoints and
ordered units through that record, original and new semantic request hashes,
instruction digest, projection/version, unchanged schema hash and exact input/envelope
hashes. Construction compares every non-instruction/version field to the original
request. Scientific text, authority hashes and completeness records cannot drift.

C preparation never invokes historical replay. Artifacts are exclusively created or
byte-verified under `var/study2_step12c/wave-c-preflight/1.0.0/<amendment-sha>/<ID>/`.
The provider configuration stays GPT-5.6 Sol, medium reasoning, store=false, no tools,
and 32,768 maximum output tokens. Context allowances use one token per input/schema
UTF-8 byte, **not measured token counts**, plus separately approved provider overhead.

The existing terminal and sequential wave CLIs use approval v3. For C they require
`executionAmendmentVersion=study2-step12c-wave-c-execution/1.0.0`, the exact C digest
at top level and per request, and top-level `priorExecutionAmendmentSha256` equal to
the accepted B digest. Every request retains exact request/input/envelope/schema
hashes, version/prompt/projection fields and one-attempt bounds. Both A and B must
have separate researcher clearances with review-record hashes. Wave execution requires
all nine C IDs; B authorization cannot authorize C.

Monetary reservations (individual and aggregate), pricing reference/currency, context
allowances/overhead, approval identity and explicit validity window remain pending.
No authorized approval file is produced. Credential loading, global/wave locks, STOP,
no-retry and advance-only-after-confirmed-response rules remain unchanged. Attempts
stay at `terminal/<request-ID>` across versions, preventing amendment-based retries.
The C→B amendment association is preserved in per-request artifacts and wave summary.

## Verification and frozen execution record

Wave C amendment SHA-256:
`bf41e0951630b3d395ed5cffc1ef7877eef13287b06d2ac5d083ce4e103ac85b`.
The original selection manifest SHA-256 remains
`2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`.
The amendment is an immutable offline specification with `authorized=false`, not a
live approval. It pins all nine final prompt/version selections before any C output.

**13 focused tests passed:** nine new tests for exact wording, final/legacy routing,
schema stability, local parse failures, projection fidelity, amendment chain/selection
checks, two prior clearances, budget/window/hash gates and synthetic sequential C
recording; four existing B amendment/approval/transport regressions directly affected
by the routing extension. The earlier 92-test implementation suite was not repeated.

Targeted pure serialization checks reproduced **all 21 A/B semantic request and
provider-input byte sequences** from their preserved trusted request records, with
the original independently pinned semantic hashes. This includes HS-01's historical
`66a3fd974108b18b58d0b6effed8924669558509502760e43699b2858b07f8c0`.
No historical source reconstruction, preflight, response parsing or replay was needed
for these byte checks. Before/after hashes protect 557 local historical files,
including approvals, replays and raw outputs; the handoff, HydroShare request module
and unrelated catalog modification remain untouched.

**Nine preflights and nine terminal dry-runs passed**, three per family. Local strict
schema checks pass with unchanged response-schema hashes. Remote provider acceptance
is not claimed. There are no technical holds; all nine retain the live-approval hold.

| Request | Input bytes | Envelope bytes | Conservative input + schema allowance |
|---|---:|---:|---:|
| HS-08 | 19,195 | 33,154 | 31,569 |
| HS-09 | 18,041 | 32,000 | 30,415 |
| HS-10 | 19,093 | 33,061 | 31,467 |
| GH-08 | 29,378 | 51,317 | 48,691 |
| GH-09 | 37,336 | 59,788 | 56,649 |
| GH-10 | 30,845 | 52,900 | 50,158 |
| HUB-08 | 59,624 | 83,153 | 78,344 |
| HUB-09 | 34,672 | 56,353 | 53,392 |
| HUB-10 | 39,485 | 61,374 | 58,205 |

Local verification records:
`var/study2_step12c/wave-c-preflight/verification/`.
No C attempt directories, authorized approval files, provider calls, credential
access, graph writes or semantic acceptance decisions were produced.

Offline commands from the repository root with an existing compatible Python environment:

```bash
AMENDMENT=docs/study2_step12c_wave_c_execution_amendment_v1.0.0.json
AMENDMENT_SHA=bf41e0951630b3d395ed5cffc1ef7877eef13287b06d2ac5d083ce4e103ac85b
shasum -a 256 "$AMENDMENT"
python -m src.extraction.llm.wave_b_amendment preflight --wave C \
  --amendment "$AMENDMENT" --amendment-sha256 "$AMENDMENT_SHA"
python -m src.extraction.llm.pilot_terminal dry-run --request-id GH-08 \
  --amendment "$AMENDMENT" --amendment-sha256 "$AMENDMENT_SHA"
```

For separately authorized execution, the existing terminal/wave `execute` modes
accept the same amendment arguments plus the researcher's approval path and exact
approval SHA-256. The wave wrapper requires `--wave C` and all nine frozen C IDs.
No live command was executed. Subsequent code or prompt changes invalidate these
fingerprints and require explicit prospective authorization, never silent repinning.
