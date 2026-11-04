# Step 14 researcher-terminal identity recommendation execution

This runner consumes the saved `semantic-identity-pilot/v1` package from commit
`85cc2a1`, pinned by manifest SHA-256
`45654787b5545e37bab65c95e9fdd770452651518db20fe6402e9980b0ac209a`.
It prepares all 43 saved cases, including the ten whose old planning payloads were
withheld. No candidate discovery, extraction, graph mutation, adjudication or
canonical-ID allocation occurs. Step 14A remains skipped. Frozen v4, ontology
v0.1.7, order-50 metrics and all existing pilot outputs are unchanged.

## Audit versus model context

The complete original package and its input authorities remain hash-bound. A new
per-case audit records the original case, complete occurrence membership, accepted
relation context, full recovered selected evidence, original candidate memberships,
source provenance and exact alias/evidence mappings. Truncated identity fields and
selected evidence metadata are resolved only through existing hash-bound original
references, in one read per needed source file. This is recovery of accepted saved
context, not new extraction or an audit of the full candidate population.

The model sees concise scientific context: original labels/descriptions, ontology
class, own-versus-local identifier scope, recorded versions, curation/reference
status, source artifacts, accepted predicate/endpoints and full selected quotations.
Only known administrative keys, extraction provenance narrative and redundant
wrappers are removed. Unknown scientific attributes are retained. Capture versions
are explicitly separate from entity versions. Candidate tiers, diagnostic conflict
labels and historical extraction rationale are not model instructions. Actual
version values and statements remain available; the model must identify any
contradiction from evidence, rather than receiving a preassigned contradiction.

Short IDs (`C001`, `O001`, `E001`, etc.) bind exactly to original cases, occurrences,
evidence and sources in the audit. These are request-local identifiers, never
canonical nodes. Scientific DOI/resource/repository identifiers and meaningful
source URLs are retained; opaque provenance hashes and local audit filenames are
not sent as scientific context. The input and output aliases are scoped to one
request and cannot be reused across cases.

All v1 selected evidence is retained without a new character/byte cutoff. Original
v1 relation-context sampling remains documented; this is not a claim to include all
possible source documents or incident relations. The ten missing payloads are
reconstructed from saved cases, occurrence contexts and accepted-relation contexts,
not replaced with smaller member subsets. Accepted quotations embedded in original
source-declaration attributes receive explicit additional evidence bindings instead
of being discarded as administrative metadata. There is **no 96 KB rejection rule**.
`report.md` records actual serialized request bytes/input characters and approximate
input tokens. Actual tokenizer usage is recorded only after a live response.
Genuinely missing evidence or source provenance blocks selected live dispatch;
unknown entity versions alone do not. A provider context-limit error is retained,
never worked around by silently dropping evidence or changing models.

## Recommendation and provider contracts

Model: **gpt-6.1-sol**, reasoning effort **medium**, `store=false`, no tools,
retrieval or conversation. Default maximum output budget is 16,384 tokens, covering
reasoning and output; it is preparation configuration, not an identity criterion.
The existing Publication provider module supplies credential loading, the stateless
Responses HTTP transport, safe HTTP error diagnostics and exact model-text
extraction. Its historical model constant is not modified: the new prepared body
supplies the authorized model directly to the transport.

The five categories, subset assessments, explicit abstention, evidence citations
and missing-information fields remain unchanged. The wire schema excludes
application-owned case/context hashes and uses short case IDs. Unsupported
`uniqueItems` syntax is omitted only from the provider schema; the original local
validator still enforces uniqueness and the complete original recommendation
contract. The wire `const` is expressed as an equivalent one-value enum.

Raw model output is never repaired. A separate `validated-recommendation.json`
contains the untouched parsed model object plus an explicitly **application-bound**
view: aliases are resolved and the original case/context headers are attached.
Unknown aliases, duplicate JSON keys, incomplete membership, invalid scope,
unsupported citations, missing abstention reasons or schema failures are rejected.
This structural validation does not adjudicate scientific truth. A validated
recommendation is still only a recommendation; original decision ledgers stay
unreviewed and canonical IDs remain unassigned.

The request format follows the official
[Responses structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs).
Model/account access is not probed by preparation; smoke execution is the first
provider compatibility check. There is no silent model fallback.

## Commands

From the repository root, using the existing multigranular-kg Python environment:

```bash
python -m src.evaluation.step14_identity_live prepare
python -m src.evaluation.step14_identity_live run --live --smoke --concurrency 1
python -m src.evaluation.step14_identity_live run --live --all --concurrency 2
```

Use the researcher's environment Python explicitly if it is not activated.
Preparation is offline, blocks network connections and never loads the API key.
Live mode reuses `OPENAI_API_KEY` from the process or ignored repository `.env`
through the existing credential loader, without printing or persisting the key. The run command exits nonzero if any
selected case does not finish as a locally validated recommendation.

The smoke selection is deterministic: first case by stable case ID in each of
shared tier A, shared tier B and lexical strata, deduplicated if necessary. Inspect
smoke validation/status before running all cases. The complete run reuses the same
prepared directory and skips already completed attempts, so successful smoke cases
are not called twice. Exact selection is also supported, for example:

```bash
python -m src.evaluation.step14_identity_live run --live --case-id C001 --concurrency 1
```

Default ignored destination: `var/study2_step14/semantic-identity-live/v1/`.
`prepare --output <fresh-directory>` and `run --output <same-directory>` may select
a different fresh path under `semantic-identity-live/`. Existing preparation
outputs are refused. Input/request/audit/implementation drift blocks execution.
Changing output budget requires a new preparation, not an in-place edit.

## Durable execution, failures and resumption

Concurrency is bounded to 1–4 workers (default 2). A process lock excludes competing
runners on the same directory. Interruption cancels queued work; already dispatched
requests may finish and retain their durable response or ambiguous journal. Each request has an immutable numbered attempt:
request body and initiation journal are fsynced before POST; the complete decoded
provider response is durably saved before parsing or validation; model-authored
text is saved as exact UTF-8 bytes. HTTP-error diagnostics use the existing
credential-redacting adapter. Successful decoded JSON is preserved canonically;
this is not a claim to preserve HTTP transport whitespace/headers.

Completed responses, refusal/incomplete/wrong-model responses, and validation
failures retain usage/status. A crash after saving the provider response resumes
local validation without another POST. An initiation without a durable response,
a timeout, invalid transport response, or ambiguous HTTP 5xx/408 remains
`remote_outcome_unknown`; default resumption never resends it. Unknown usage is
reported as unknown, not zero. Status summaries include all attempts and their
known usage, including failures and explicitly requested retries.

There are no automatic retries. To intentionally retry a failed selected case:

```bash
python -m src.evaluation.step14_identity_live run --live --case-id C001 --retry-failed
```

For an ambiguous remote outcome, additionally pass `--allow-duplicate-risk` only
if the researcher accepts possible duplicate provider processing/billing. A new
attempt preserves all earlier files. Valid completed recommendations are protected
even with retry flags. Retrying an invalid recommendation is a separate attributed
attempt, never repair of authentic output or automatic scientific selection.

## Files and future Batch compatibility

- `manifest.json`, `report.md`, `requests/Cxxx.json`: pinned configuration and sizes.
- `audit/Cxxx.json`: complete bindings and validation context, excluded from prompts.
- `recommendation.schema.json`: unchanged local recommendation contract.
- `batch-compatible-requests.jsonl`: identical POST bodies with stable `custom_id`,
  `method`, and `/v1/responses` URL. No Batch upload/polling subsystem is added.
- `attempts/Cxxx/0001/`: immutable request/initiation, provider response or safe
  transport error, raw model output, validated bound recommendation if valid,
  and terminal status with usage and artifact hashes.
- `status-summary.json`: current per-case status and accumulated known usage.

Focused tests mock every provider call and forbid sockets:

```bash
python -m unittest tests.test_step14_identity_live tests.test_step14_semantic_identity_pilot -v
```

## Verified offline checkpoint

Bounded offline assembly of the saved 43 cases completed with networking disabled
and no API-key loading. All ten previously withheld payloads were reconstructed;
no case had a missing-evidence/source-provenance flag. The actual serialized body
sizes total **768,038 bytes**, ranging from **6,758 to 53,316 bytes**. Approximate
input tokens total 177,802 including instruction/schema text; this is not measured
provider usage. Complete membership and quote-to-audit bindings were checked for
all 43 requests. The deterministic smoke IDs are `C005`, `C001`, `C002`.

The checked assembly is ignored under
`var/study2_step14/semantic-identity-live/preflight-audit-v3/`; it contains no live
attempts. Default commands above prepare a separate fresh `v1/` execution folder.
The original pilot package remained hash-identical. Nineteen focused synthetic
runner/contract tests passed, including interrupted-response recovery, duplicate
risk gating, process locking, alias/citation validation, drift checks and bounded
concurrency. No provider compatibility or scientific identity result is claimed
until the researcher runs and reviews live smoke outputs.
