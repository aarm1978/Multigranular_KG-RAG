# SciERC single-request smoke runtime and prospective plan

Unfrozen implementation for review. **NOT AUTHORIZED FOR PROVIDER EXECUTION.**
Starting HEAD: `90f8ad018598faeef2910b29b241d7ffe2237c9d`.
Step 9 remains open. Step 8 and the existing 100-request preflight are unchanged.

## Selection and request identity

`python -m src.extraction.llm.publications.scierc_smoke_runtime` creates metadata
only. It hashes the existing local archive against the frozen source authority,
then verifies the exact dev member hash and document count. Only the first JSONL
line in file order is selected: `ICCV_2003_158_abs`. It is parsed with
`include_gold=False`; gold fields are never used for request construction.

The separate plan is
`data/curation/papers/m2/scierc_step9_preflight/scierc_smoke_plan_v0.1.0.json`.
It binds archive/split/source authorities, source projection, request body, prompt,
schema, configuration and runtime implementation hashes. Request bytes come from
the unchanged `build_request_body()` and retain `scierc_native_payload`,
gpt-5.6-sol, medium, max_output_tokens=32768, store=false, synchronous stateless
requests without tools/retrieval. The runtime passes those canonical bytes directly
to one generation POST; it does not invoke a Publication request reconstruction.

## Approval and dispatch boundaries

No real acceptance, activation or authorization record is created by this task.
The existing preflight flags and the new plan flags remain false. Future execution
requires two externally supplied researcher records: `runtime_acceptance` and
`live_authorization`, with distinct nonempty record IDs and `approved: true`.
The authorization references the acceptance record ID. Both bind the exact scope,
plan hash, request-body hash, runtime hash, resolved runtime directory and
`maxGenerationPosts: 1`. The helper `approval_binding()` only describes that scope;
it grants nothing. Tests use temporary test-only records.

Every execution entry reconstructs the verified first-dev request and compares
the complete supplied plan. No arbitrary document/body argument exists; test-split
or substituted-document plans fail before dispatch. Acceptance and authorization
are checked before runtime creation or transport. The live transport uses only
the designated ignored directory `var/scierc_external_anchor/single_dev_smoke_v0.1.0/`.
The CLI exposes no execute switch. No official-test dispatcher is implemented.

## Timeout, provenance and interrupted state

The transport timeout is explicitly 180 seconds per blocking socket operation;
this is not a guaranteed total wall-clock deadline. Redirects are not followed,
and neither transport nor runtime retries or resamples. HTTP non-success responses
are confirmed HTTP failures with preserved bodies; they do not establish that
remote generation never happened. Timeout/connection/partial-read failures leave
delivery or completion unknown. There is no redispatch in either case.

An exclusive directory claim prevents concurrent attempts. Request bytes,
identity/approval records, and a dispatch-start marker are flushed with file and
directory fsync before transport. Any existing run directory blocks a restart,
even if it has only partial pre-dispatch writes, an interrupted nonterminal state,
or a terminal failure. It must not be deleted to retry this authorization.

The raw HTTP response bytes and full decoded provider response object are persisted
before semantic output validation. All available model text fragments and a single
exact model-output byte payload (when present) are preserved before JSON parsing
and prediction validation. Partial HTTP bytes, refusals, errors, incomplete output,
model mismatch, malformed JSON/schema, and invalid predictions remain explicit.
Duplicate JSON keys/non-JSON numeric constants are rejected, not repaired.
Raw evidence is never overwritten; later validation creates separate artifacts.

Terminal metadata retains requested/returned model, local request ID, provider
response/request IDs, full usage (including cached-input/reasoning details), provider
timestamps, client UTC start/end times and monotonic elapsed milliseconds. API keys,
request headers and arbitrary transport exception messages are not logged. If a
response echoes the supplied credential, it is redacted with an explicit flag;
such evidence is necessarily no longer byte-identical at the redacted positions.

## Accounting and offline validation

Planned smoke generation POSTs: **1**, concurrency **1**. The official test remains
a separate plan of **100** logical requests. No benchmark scores or semantic
assessment are produced here. Source size, repeated prompt/schema bytes and full
serialized request bytes are recorded as byte proxies, not provider tokens. No
compatible tokenizer is asserted. Token estimates, observed usage/latency, prices,
expected costs and account-specific rate limits remain unknown/null. Future full
usage is preserved verbatim; reasoning_tokens is a detail within output_tokens
and is not added a second time.

Focused validation command:
`python -m pytest -q tests/test_scierc_external_anchor.py tests/test_scierc_smoke_runtime.py`.
All responses/transports in runtime tests are injected synthetic fixtures with a
network guard. They cover body equality, approval/scope refusal, completion and
failure preservation, interruption, artifact conflicts, and no restart dispatch.

Offline result at this checkpoint: **30 passed** (16 existing SciERC tests and
14 new runtime tests). Zero provider/model calls. Final scoped diff check passed.
