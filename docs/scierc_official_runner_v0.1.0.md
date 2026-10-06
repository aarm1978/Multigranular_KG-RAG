# SciERC sequential runner — preparatory implementation

Implementation only. No real official acceptance/authorization records exist from
this task. The accepted cost report, v0.2.0 candidate, smoke and frozen authorities
are unchanged. Step 8 remains ACCEPTED / FROZEN_CLOSED; Step 9 remains open.

## Scope and identities

`src/extraction/llm/publications/scierc_official_runner.py` reconstructs requests
from the hash-verified official test split with `include_gold=False`. All 100 IDs
must match the candidate exactly; dispatch follows the candidate's existing order.
Every canonical outgoing body must match its existing SHA-256 before any dispatch.
There is no benchmark scoring, semantic repair, prompt change, or gold comparison.

Settings remain gpt-5.6-sol, medium, max_output_tokens=32768, synchronous stateless,
store=false, no tools/retrieval. Only the NEW runner uses a **600-second blocking
socket-operation timeout**, not a total wall-clock deadline. The accepted smoke
still uses 180 seconds. Compatible exact-byte transport, exclusive/fsynced storage,
strict parsing and prediction validation are reused without changing those helpers.

Future separate `runtime_acceptance.json` and `live_authorization.json` belong in
ignored `var/scierc_external_anchor/approvals/official_sequential_v0.1.0/`.
They require distinct IDs, approved=true, the acceptanceRecordID link, and the exact
`binding(candidate, ROOT)` value. That binding includes scope, candidate/ordered
request identities, new runner/dependency hashes, designated root, concurrency=1,
timeout=600, maximum 100 generation POSTs and no automatic redispatch.
Describing the binding does not grant approval. Historical candidate flags stay false.

## Evidence, progress and failure behavior

The separate ignored execution root is
`var/scierc_external_anchor/official_sequential_v0.1.0/`. An exclusive root claim
and per-document directory claims prevent competing launchers and overwrites.
Request and dispatch-start evidence are durable before transport. Raw provider
bytes, transport metadata, decoded response and all model-output fragments are
preserved before model JSON/prediction validation. Full usage retains reasoning as
part of output, not an additive second output count. Credential echoes alone are
explicitly redacted. Raw exception text from unexpected errors is not logged.

Flushed before/after progress includes [i/100], document ID, status, elapsed time
and successful/failed counts. Refusals, incomplete output, invalid JSON/schema/spans
and ordinary per-document transport uncertainty are recorded in `failures.jsonl`
and traversal continues. HTTP 400/401/403/404/422/429, recognized authentication,
quota/schema/model errors, returned-model mismatch, integrity/persistence failures
and unexpected shared implementation exceptions stop traversal. There is no
frequency-based rule declaring repeated invalid model outputs a shared blocker.
HTTP error evidence does not prove that the service performed no generation.

`summary.json` covers every candidate ID as successful, failed/uncertain, or not
started, with available usage, timing, IDs and artifact paths. Completed traversal
is distinct from 100 valid outputs. A global persistence failure may prevent writing
the summary/ledger; the runner stops and returns/prints the available summary.
Interrupted attempts are uncertain, never silently omitted or retried.

**Restart is report-only.** Any existing execution namespace with matching identity
returns a reconstructed summary and dispatches nothing, including unstarted IDs.
Conflicting/incomplete run identity fails closed. Do not remove the root to resume.
Deciding how to handle failures or unstarted IDs requires separate researcher action;
this runner implements no retry/resume policy. It creates no budget manager, pricing
report, account probe, rate discovery or parallel execution.

## Review-only prospective manual command

From the repository root in the researcher's own foreground Terminal, ONLY after
separate official runtime acceptance and explicit live authorization:

```bash
python -m src.extraction.llm.publications.scierc_official_runner --execute
```

Without `--execute`, the CLI prints a non-execution notice and does nothing else.
This command is documented for review, not authorized or run by this task.
Account constraints and operational launch decisions remain the researcher's;
the accepted planning report is not regenerated.

Focused offline tests: `python -m pytest -q tests/test_scierc_official_runner.py`.
Only synthetic documents, test-only approval fixtures and injected transports are
used. No real activation, official runtime directory, provider call, or smoke occurs.
Result: 13 focused orchestration tests passed. Starting HEAD:
`3bdebbb1f15ad67d5a85dcc82e678ced76567eaa`.
