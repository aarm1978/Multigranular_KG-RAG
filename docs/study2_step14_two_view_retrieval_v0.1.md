# Step 14 two-view candidate retrieval v0.1

Implementation: `step14-two-view-retrieval/0.1.0`. This implements the researcher-approved
[scope](study2_step14_scope_and_completion_decision_v0.1.md) and retrieval request,
not new identity approvals. The [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md)
and ontology decision gate remain unchanged. Historical identifier/lexical candidates,
reviews, reservations, approvals, preflight and source records are read-only.

## Projection and eligibility

Use the accepted `semantic-candidates/v1/occurrences.jsonl`, verified through the
existing `embedding-preflight/v1/manifest.json` (SHA-256
`8779917e3ab5d086d0605897ffcdd7d3654570b5758ead67023debc2553994d1`)
and its direct authority pins. This route retains the existing semantic-comparison
classes: Tool, Algorithm, Workflow and nonabstract ComputationalModel subclasses.
Identifier/geographic-lane records remain inventoried but are not newly embedded.
Abstract/incompatible classes, existing blocking provenance flags, missing labels
or literal evidence, and missing/ambiguous source-family membership remain held.
Multiple original labels are preserved and flagged; they do not establish identity.

Name text is class followed by sorted distinct **original** labels. Evidence text
adds at most three distinct literal excerpts (600 Unicode characters each), ranked
first by case-insensitive literal label occurrence, then original evidence index.
A window starts up to 160 characters before the first match and shifts back at the
end of a short quote. Without a label match, use the beginning of the quotation and
flag weak context. This is mechanical retrieval context, not semantic sufficiency.
No descriptions, inferred aliases or generated profiles are added. Window offsets
are relative to the original quotation, not fabricated document offsets. Every
selected fragment has its original JSON pointer, full quote/evidence-record hashes,
and exact substring offsets; all omitted evidence and native provenance remain
recoverable through the original manifest-pinned row and its hash.

Versions, granularity and source memberships remain unchanged metadata. Missing
versions indicate uncertainty; different structured versions are flagged for review,
not silently normalized or merged. The two views do not resolve the ontology gate.

## Embeddings and execution

Exact text hashes deduplicate requests across occurrences and views; postings retain
all original occurrence IDs. Configuration is `text-embedding-3-large`, 3,072
dimensions, float output. Inputs above 8,191 UTF-8 bytes are held conservatively
rather than truncated again. Byte length bounds byte-BPE tokens; it is not an exact
billable token count. Batches contain at most 64 inputs and 240,000 UTF-8 bytes.
See the [official API reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create).

Only `embed --execute` makes requests, using the official SDK, the researcher's
shared `src.extraction.llm.publications.openai_provider.load_openai_api_key()`
loader, passed explicitly to the SDK. It checks `OPENAI_API_KEY` in the process
environment first, then the repository's ignored `.env`. Timeout remains 600 seconds
and `max_retries=0`. No credentials are printed, recorded or stored by this module. An exclusive execution lock protects concurrency.
Each batch has an fsynced intent before dispatch, an authentic response and a
sanitized outcome with usage and response hash. Completed batches are verified and
skipped on resume. An intent without a completed verified outcome stops execution;
there is no automatic uncertain-request retry or reset. Partial-response crashes
require separate investigation, not deletion of the intent. `--max-new-batches`
limits a terminal invocation without changing the prepared batch identities.

## Local retrieval and interpretation

A NumPy float32 memory-mapped normalized matrix supports exhaustive exact cosine
search (no approximate index). Score matrices are bounded by configurable query
and target blocks. For each eligible query and exact ontology class, retrieve top-k
**per view per scope**, then union the nominees and retain both scores. Ties use
occurrence-ID order. Scores are floating-point cosine values, not identity confidence;
near ties can vary across numerical-library/platform implementations.

Scopes are mutually exclusive: shared exact artifact ID first; otherwise same
explicit family between artifacts; otherwise different families. These are recorded
source memberships, not inferred artifact equivalences or independent corroboration.
Every eligible occurrence can query, including previously reviewed/reserved records;
new nominations do not change their review state. No 500-query/1,000-pair ceiling,
threshold-based identity decision, or induced expansion of oversized lexical blocks
is applied. Exact search does compare all eligible same-class pairs in bounded
blocks; stored output is limited to configurable top-k nominations, not a quadratic
pair file. Directed/reverse nominations and two-view overlap are not independent
cases. A later reviewer must consult prior decisions and full original evidence.

Outputs record eligible peer coverage and directed nomination counts for all three
scopes. No canonical IDs, equality axioms, relation assertions or KG writes occur.
Local vectors serve Step 14; production vector infrastructure remains Study 3 work.

## Researcher-terminal stages

Run from repository root. NumPy is newly declared in the existing environment
specification; update the environment if it is absent (no installation in Codex):

```bash
micromamba run -n multigranular-kg python -m pip install numpy==2.2.6
```

Offline preview (fresh output; inspect the at-most-16 cases before execution).
The implementation handoff supplies `preview-v2/`; the command below creates a
separate preview without overwriting earlier artifacts:

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_two_view_retrieval preview --output var/study2_step14/two-view-retrieval/preview-v3
```

Credential-loading correction (2026-11-09): preserve the original `v1/`
preparation and failed `embeddings/batch-000000/` intent/outcome unchanged. Its
implementation pin no longer matches this corrected module; do not reset or
redispatch it. Prepare a fresh `v2/`. First unset the manually exported key so
the shared loader uses the established repository `.env` key:

```bash
unset OPENAI_API_KEY
```

Offline full preparation (immutable inputs and occurrence mappings):

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_two_view_retrieval prepare --output var/study2_step14/two-view-retrieval/v2
```

**Two-batch live smoke test — researcher terminal only**, after inspecting the
fresh v2 preview/summary. Run once; the limit is two **new** batches per invocation,
not a lifetime cap. Completed batches are verified and skipped; uncertain or failed
outcomes stop without redispatch. Inspect both outcomes before continuing:

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_two_view_retrieval embed --root var/study2_step14/two-view-retrieval/v2 --execute --max-new-batches 2
```

Offline exact retrieval, after all embeddings complete:

```bash
micromamba run -n multigranular-kg python -m src.evaluation.step14_two_view_retrieval retrieve --root var/study2_step14/two-view-retrieval/v2 --output var/study2_step14/two-view-retrieval/retrieval-v2 --top-k 10 --query-block 32 --target-block 512
```

Preparation produces `manifest.json`, `summary.json`, `preview.json`,
`occurrences.jsonl` and `inputs.jsonl`; preview-only omits the last two. Embedding
receipts are under `embeddings/batch-*/`. Retrieval produces `normalized.npy`,
`candidates.jsonl`, `summary.json` and `summary.md`. Outputs remain ignored.
Share compact preview/summary files; evidence text is corpus-derived research material.
