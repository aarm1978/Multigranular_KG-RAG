# Publications GPT-6.1 Batch execution v1.0

Prospective transport implementation under the researcher's Batch decision. The
pinned v0.2 10,893-request queue and all scientific/acceptance authorities remain
unchanged. Each JSONL line contains one complete original independent request.
Only GPT-6.1 provider/binding lineage and non-streaming Batch transport change.
Medium reasoning, strict structured-output schema, 32,768 output tokens and
`store=false` remain unchanged. The streaming runner remains an untouched fallback;
no streaming/diagnostic completions are imported into Batch production.

Official references checked 2026-10-20:
[Batch](https://developers.openai.com/api/docs/guides/batch),
[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[pricing](https://developers.openai.com/api/docs/pricing), and
[token counting](https://developers.openai.com/api/docs/guides/token-counting).
Batch supports `/v1/responses` endpoint bodies; the model supports medium reasoning
and structured outputs. Account-specific acceptance is verified by one authentic
original request in an isolated compatibility journal, never production-relabelled.

## Operation

Use Anaconda base Python from the repository root. Module:
`src.extraction.llm.publications.full_corpus_gpt61_batch`.

- `--estimate`: offline repricing; optionally supply `--queued-token-limit N`.
- `--status`: offline atomic snapshot, including snapshot age.
- `--check --queued-token-limit N`: researcher-terminal one-request Batch check;
  N is an operational queued-input-token capacity, not synchronous TPM or a
  verified account-limit claim. The researcher provisionally selected **1,000,000**
  tokens pending the lab's actual limit. Rerun the same command to resume.
- `--pilot-only`: run exactly the first 100 entries of the original production
  queue, with native processing and bounded retries, then stop. This uses the
  full production manifest/journal; it never prepares or schedules request 101.
  Restart with the same command. Existing out-of-scope unsettled jobs cause STOP.
- `--live`: one unattended start/resume command after the compatibility check.
  After the pilot, this continues at request 101 without replaying pilot outputs.
- `--increase-queue-capacity N`: offline, locked, append-only increase of the
  production operational capacity after obtaining the lab limit. The event records
  old/new values, source, timestamp and unchanged manifest hash. Equal-value
  repetition is a no-op; decreases are rejected. Prior journal entries, scientific
  queue, completed outputs, custom IDs, file IDs and Batch IDs remain unchanged.
  Subsequent `--live` automatically uses the increased capacity. Stop the local
  writer before changing capacity; remote jobs need not be cancelled.

Existing key loading is reused only by researcher-terminal network modes. No
admin key, new credential setup, distributed service or approval machinery is
introduced. Account capacity cannot be established by public docs or offline code.
The account must expose Batch/Files/token-count endpoints to that existing key.

Files are automatically packed at at most 190,000,000 bytes (below 200 MB) and
50,000 requests. Exact schema-aware input-token counts are requested JIT using
`/v1/responses/input_tokens`, persisted with the body hash, and reused on restart.
Only count-relevant body fields are sent to that non-generation endpoint. Token
counts bound aggregate outstanding reservations against the current journaled
operational capacity. Unrelated outstanding
batches cause a capacity wait because their input-token reservation is unknown;
use an otherwise idle project for predictable throughput. No whole-corpus set of
individual request files is precreated. JSONL input/output files and one durable
journal stay under ignored `var/study2_step13/publications-gpt61-batch/`.

Production starts with 100 distinct requests (split further if capacity requires).
Only after their measured usage/native outcomes are reconciled does scheduling
scale to available capacity. Before further submissions, cumulative Batch-priced
usage (including retries) is compared with pooled estimates for distinct measured
requests. After 100 measured requests, spending greater than 2x that estimate
stops new dispatch; already-submitted work is drained and remains billable. No
absolute monetary cutoff applies. All scientific and technical STOP rules remain.

## Durability and errors

The existing journal's exclusive lock, canonical hash chain, write-ahead staging,
fsync, offset access and recovery are reused with separate Batch state transitions.
Exact bundles, token counts, input hashes, custom IDs, upload intents, file IDs,
submission intents, Batch IDs/metadata, snapshots, result files, raw responses,
usage, native attempts, validation, held assertions and accepted projections are
retained. Results are matched by exact custom ID, never output order. All output
and error files are validated for duplicate/foreign IDs before native processing.

A lost upload acknowledgement is reconciled by a unique filename/size/content
hash; a lost Batch acknowledgement by unique exact submission metadata and file
ID, through fully paginated listings. Zero or multiple matches are an explicit
uncertainty STOP, never permission to resubmit. No automatic retry of mutating
HTTP POSTs. Read-only/token-count transient failures have bounded backoff.

Explicit per-request `batch_expired` evidence is a known unexecuted API failure,
with zero execution usage. It passes through the unchanged native technical retry
controller, at most two attempts of the same request. Known incomplete/model
processing failures use that controller too. Semantic holds/rejections do not
trigger resampling. Missing outputs, ambiguous billing, failed/cancelled jobs,
unknown/duplicate IDs and exhausted native retries remain technical STOPs; partial
results are retained. Running/uncertain jobs are never automatically resubmitted.
Only incomplete temporary staging may be discarded by inherited recovery.

## Cost and throughput

Batch rates per million tokens: input $1, cache read $0.05, 30-minute cache write
$1.25, output $5. Existing long-context multipliers remain. Original scenarios
repriced at conservative cache-write input rates give **$414.37 low / $491.80
pooled / $590.79 high**; output-ceiling scenario **$2,007.26**, not a spending cap.
No assumed cache savings or retries. Measured usage is retained exactly; where
cache-write categories are absent, the reused cost adapter explicitly labels its
conservative estimate rather than claiming exact invoice cost.

Estimated pooled input volume is **174.64 million tokens**. Dividing that by N
and rounding up gives approximate capacity waves, before the compatibility/pilot
ramp, retries, JIT/counting and native processing. Each batch has its own 24-hour
window; entire-corpus completion within 24 hours is not promised. Public docs do
not establish this account's limit or actual latency. Status reports observed
throughput and elapsed time; asynchronous jobs execute while the local process is
polling or offline. Native processing remains local and sequential.
