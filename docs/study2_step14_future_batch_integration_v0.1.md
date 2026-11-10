# Step 14 future Batch integration: minimal reuse plan v0.1

Planning only, following the [compatibility pilot](study2_step14_queue_compatibility_pilot_v0.1.md).
No production runner, Batch files, submission, token-counting call or new transport
is implemented by this note. Existing historical authorities and artifacts remain
unchanged. Pilot compatibility results must be reviewed before production binding.

## Established operational constraints

The researcher confirms laboratory queued-input-token capacity of
**15,000,000,000 tokens**. Preserve the four-family production convention of
**20 MB = 20,000,000 bytes per JSONL input file**, not 20 MiB or a higher provider
maximum. The current selected queue has 14,549 review units, with approximately
18.8 million context-input tokens estimated before final provider-envelope accounting.
That estimate is not a verified input-token reservation or production-readiness claim.

## Reuse, not a second Batch subsystem

- `src/extraction/llm/publications/batch_transport.py`: existing Batch/Files transport,
  paginated reconciliation, token counting and result download operations.
- `src/extraction/llm/publications/batch_journal.py`: existing durable native journal
  adapter, request/body fingerprinting, state replay and protected outcomes.
- `src/extraction/llm/publications/full_corpus_gpt61_batch.py`: established packing,
  capacity reservation, sealed file hashes, upload/submit intent handling, status,
  collection and reconciliation conventions. Its `MAX_BYTES` is 20,000,000; retain
  the existing request-count ceiling as an additional constraint.
- `src/extraction/llm/source_family_batch.py::infrastructure`: the existing mechanism
  for loading pinned shared transport/journal infrastructure without validating a
  historical Publications parent queue against current authorities. Step 14 needs
  its own queue-authority adapter; never bypass or rewrite Publications dependency
  guards, historic ontology pins, parent manifests or completed journals.

Retain established upload/submit uncertainty handling and file-only recovery:
reconcile remote files/jobs and exact sealed hashes before reuse; never automatically
redispatch an uncertain POST. Use new isolated Step 14 journals and recovery records.
Do not hardcode old job IDs or reuse Step 13 sidecars. Existing SDK/manual upload
recovery helpers may need a narrow run/job binding adapter, not another transport.

## Genuinely missing integration pieces

1. Freeze the pilot-confirmed pair response schema, shared instructions and compact
   context projection as a production request contract. Bind each original review
   unit and exact pair list to one stable request/custom ID and body fingerprint.
   Preserve deferred prior assessments separately; no new comparison or identity is
   inferred by batching. Do not use pilot-local case IDs as production identities.
2. Add a narrow Step 14 adapter to the existing Batch journal/runner interfaces for
   queue verification, prepared bodies, request fingerprints and outcome validation.
   Reuse the pilot's exact-pair/category/evidence validation adapter; preserve authentic
   responses and recommendation-only status. Batch arrival order must not determine
   pair identity or coverage.
3. Size and pack the **complete serialized Batch JSONL lines** in stable queue order:
   custom ID, method, endpoint, full body (instructions, input, structured-output
   schema and settings), UTF-8 encoding and newline. Seal each file at no more than
   20,000,000 bytes and preserve each complete review unit. A single oversized unit
   is a blocker, not permission to split its scientific comparisons or truncate it.
4. Produce an offline preflight with actual per-request/per-file byte counts, file
   hashes, stable request memberships, aggregate pair coverage and final-body token
   estimates. Before submission use the established schema-aware input-token counting
   path, under explicit researcher-terminal authorization, recording counts against
   exact body hashes. Local bytes/4 proxies are not provider token counts.
5. Initialize the isolated operational journal with the confirmed 15,000,000,000-token
   capacity. Reserve tokens for all outstanding jobs and respect the existing wait
   behavior when unrelated jobs make available capacity uncertain. Multiple sealed
   jobs can be submitted safely within verified available capacity; there is no new
   one-file or one-Batch restriction. Preserve established submission/recovery gates.
6. Reconcile every submitted request and listed pair with downloaded receipts,
   completeness, token usage and validated recommendation results. Preserve failures,
   abstentions and uncertain outcomes explicitly. No silent duplicate execution,
   missing-pair coverage or researcher identity acceptance follows from collection.

## Bounded sizing evidence and remaining verification

A read-only check of the 16 current pilot requests serialized complete Batch-style
lines using the existing canonical encoder: **104,079 bytes total**, **4,106–11,736
bytes per line**, compared with **48,177 bytes** of projected context input. This
uses pilot-local IDs solely for size diagnostics; it is not a production file or
proof of final production sizes. Instructions, schemas and envelope fields account
for substantial additional bytes. Their tokenization is not obtained by subtracting
context estimates or assuming a constant ratio.

The complete 14,549-unit production envelope has not yet been frozen or measured.
Therefore final file count, exact input-token reservations, cost and submission
readiness remain unconfirmed. Verify them after the pilot, before any production
submission. No provider or token-counting call occurred for this planning note.
