# Step 14 queued-pair LLM compatibility pilot v0.1

`step14-queue-compatibility-pilot/0.1.0` consumes only the existing
[unified queue](study2_step14_unified_review_queue_v0.1.md), pinned by manifest SHA-256
`8f73a9a4bc23587203a1ba4151bf73f21aee9cb863a46dce0a059a9f471afb7d`.
No eligibility, embedding, retrieval, candidate-pool or accounting regeneration occurs.
The [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md)
and existing five recommendation categories remain unchanged. Outputs are model
recommendations, never researcher decisions, canonical mappings or graph writes.

## Selection and independent projection audit

Select sixteen authentic queued units deterministically: twelve greedily maximize
coverage of origin, cross/within-family, sparse (at most two pairs), dense (at least
ten pairs), NWM, LSTM, NextGen, NGIAB, explicit acronyms, recorded specificity
differences, instance language and generic-name risk tags; SHA-256 of unit ID breaks
ties and fills exhausted coverage. Four additional units follow hash order outside
that set. Tags are literal diagnostic cues, not scientifically adjudicated labels.
Report missing available tags honestly. This is a compatibility pilot, not a
population accuracy sample or an independent evaluation campaign.

For every selected unit, verify original queued pair dispositions and exact bindings,
endpoint record hashes, and exact reconstruction of the original payload with the
existing compact-context constructor. Then independently project the model context:
retain all literal evidence, original names/classes, material source and specificity
fields, incident relations and explicit pairs. Remove repeated source-role guidance,
empty fields and the exact unspecified-granularity placeholder; shared instructions
make omitted specificity explicitly unknown. Store original/projected contexts,
bindings and request hashes in local audits. Do not mutate the source queue.

## Pair contract and provider boundary

Adapt the existing strict recommendation schema from open occurrence subsets to
local pair IDs. Require exactly one assessment for every listed pair, no duplicates
or omitted comparisons. Preserve all five categories and their identity-level mapping,
granularity/version/source-role assessments, rationale, evidence/conflict citations
and missing-information fields. Every non-abstaining assessment must cite available
evidence grounded in both endpoints; foreign-pair citations are invalid. Abstention
must name missing information. These are structural grounding checks, not independent
confirmation that the rationale or recommendation is scientifically correct.

Reuse `step14_identity_live` canonical serialization, atomic fsynced writes, native
Responses transport, shared key loader and schema translation. Configuration remains
`gpt-6.1-sol`, medium reasoning, `store=false`; output ceiling 16,384 tokens. The
existing native POST timeout is 180 seconds, with no automatic retry. This pilot does
not introduce a new transport or change historical runners.

Sequential execution has an exclusive file lock. Persist an intent before each POST.
Completed responses can be finalized offline; terminal results are hash-verified and
skipped on resume. A durable intent without a response, or any uncertain transport
outcome, permanently blocks redispatch under this preparation. There is no retry flag.
A researcher must investigate uncertain outcomes separately. Sanitized errors record
exception type only, never headers, keys or exception text. Authentic response JSON,
model output, usage, incomplete details, latency and validation outcomes are retained.
A crash before receipt persistence leaves latency unknown rather than inventing it.

## Researcher-terminal commands

From the repository root using the established environment (replace `python` below
with the existing micromamba interpreter if not activated):

```bash
python -m src.evaluation.step14_queue_compatibility_pilot prepare
python -m src.evaluation.step14_queue_compatibility_pilot dry-run
# Live execution is explicitly researcher-triggered, never run by Codex:
python -m src.evaluation.step14_queue_compatibility_pilot run --execute
python -m src.evaluation.step14_queue_compatibility_pilot report
```

Default ignored root: `var/study2_step14/queue-compatibility-pilot/v2/`. Preparation
refuses an existing directory. After preparation, repeat only dry-run/run/report;
`run --execute` resumes undispatched cases without redispatching recorded attempts.
Credential resolution preserves environment-first / ignored `.env` fallback. Use the
established repository key; do not export a replacement key merely for this pilot.

Share `preparation.json`, `report.json`, `report.md` and optionally `manifest.json`.
Requests and audit/attempt directories remain local. Reports distinguish actual
input/output tokens, unknown usage, provider completeness, structural citation
validity, validated abstentions, failures and per-request latency. No production
approval, scientific quality estimate or automatic identity acceptance follows.
Focused tests: `python -m unittest discover -s tests -p test_step14_queue_compatibility_pilot.py`.

The initial offline v1 preparation is preserved locally. Before any dispatch, the
selection audit was tightened so NWM/LSTM/NextGen/NGIAB strata use candidate names,
not incidental mentions in evidence. The delivered preparation uses fresh v2.
