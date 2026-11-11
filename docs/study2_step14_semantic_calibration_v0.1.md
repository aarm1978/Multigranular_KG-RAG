# Step 14 prospective semantic instruction calibration v0.1

`step14-semantic-calibration/0.1.0` is one bounded recommendation experiment under
the [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md)
and [compatibility pilot contract](study2_step14_queue_compatibility_pilot_v0.1.md).
It makes no researcher identity decisions, canonical allocations, ontology changes,
KG writes or production Batch implementation.

## One prospective instruction clarification

Append the researcher-approved clarification to the original instructions: a named
scientific referent at family/framework/technique granularity is distinct from a
specific release, implementation, subset or trained instance. A distinctive name or
acronym plus discriminating technical, functional, ownership or project context can
support a same-entity candidate at the granularity actually denoted by both records;
independent confirmation of every technical attribute is not required. Mirrored
quotations are not independent confirmations, but lack of independence alone does
not require abstention when compatible referent identity is otherwise supported.
Complementary functions do not establish distinct entities; a difference recommendation
needs positive incompatible-referent evidence. Never discard explicit specificity
to manufacture family identity. Missing specificity remains unknown. Preserve
source/reference roles, mentions/uses, class compatibility, non-transitivity and
evidence-grounded abstention. No external knowledge, browsing, case-specific rules
or indiscriminate evidence-threshold reduction is permitted.

The five categories, strict pairID schema, endpoint-local evidence validation,
`gpt-6.1-sol`, medium reasoning, `store=false` and 16,384 output-token ceiling are
unchanged. For matched contexts the request bodies must differ **only** in instructions.
No previous recommendation or prior researcher decision enters model-facing input.

## Immutable baseline and frozen held-out selection

Original v2 manifest SHA-256:
`aee87a85c1b12315c3c8a5b7a4933b33972ad589074683f0b1328575ec19b3de`.
Verify and pin its preparation, requests, responses, validation records and reports.
Use read-only response validation, never the historical writer/finalizer. Do not
modify the original pilot module or waive its hash guards.

- **Development:** replay the exact 16 contexts / 83 original pair bindings with
  the new instructions only: sixteen new prospective requests. Baseline comparisons
  reference the sixteen completed authentic v2 responses; they are never redispatched.
- **Held-out:** freeze sixteen additional units from the same queued population,
  excluding every development unit and pair. Select the hash-minimum unit in each
  available cross-family/within-family × sparse/medium/dense stratum, then hash-minimum
  additional units for recorded-specificity, instance-language and generic-name cues
  where available. Fill remaining positions by deterministic salted unit-ID hash.
  Selection never consults response categories. Freeze both matched instruction arms
  before any new responses: thirty-two requests with exactly identical contexts,
  pairs, model, settings and schemas within each pair of arms.

These are source-grounded diagnostic strata, not independently judged semantic labels.
This held-out sample tests the fixed instruction variant; it is not representative
population gold. Original/prospective arm order alternates deterministically by case
to avoid executing all requests from one arm first. There is no automatic parameter
search, variant selection, extra review campaign or automatic retry experiment.

## Execution gates and reporting

Reuse the original pilot's native transport, credential loader, atomic fsynced writes,
response persistence, strict validator and once-only attempt function unchanged.
Retain its 180-second native timeout and no automatic retries. A single lock protects
both stages. Development and held-out have separate explicit terminal commands;
development cannot trigger held-out execution. An uncertain outcome stops that stage
and blocks redispatch under the same intent, including a repeated command. Resume
valid saved outcomes without provider calls; never reset historical attempts.

Report development and held-out separately. Compare only response pairs that both
pass structural validation and exact pair coverage; expose unmatched/failed/incomplete/
uncertain outcomes instead of pretending they are valid recommendations. Preserve
actual usage, unknown usage and latency per request. Development historical baseline
usage is marked historical and kept separate from prospective spending.

Outputs include per-pair category transitions, cross-family/within-family abstention
changes, co-occurring **pair-level** literal ambiguity tags, new same-entity and
new different-entity proposals, lost same-entity proposals, new abstentions and citation
changes requiring inspection. A worksheet includes up to six changed and six unchanged
category decisions per stage, selected by stable pair hash with exact occurrence IDs,
local source/evidence bindings and literal excerpts. It is an unreviewed worksheet,
not a model judge or a new gold set. All comparisons retain both original recommendations.
No decrease in abstention, transition count or model agreement establishes precision,
recall, population accuracy or scientific improvement.

## Researcher-terminal commands

Use the existing `multigranular-kg` interpreter from the repository root. Default fresh
ignored directory: `var/study2_step14/semantic-calibration/v1/`.

```bash
python -m src.evaluation.step14_semantic_calibration prepare
python -m src.evaluation.step14_semantic_calibration dry-run
python -m src.evaluation.step14_semantic_calibration report
# Explicit live development gate; researcher terminal only:
python -m src.evaluation.step14_semantic_calibration run-development --execute
python -m src.evaluation.step14_semantic_calibration report
# Separately authorized live held-out gate; never triggered by development:
python -m src.evaluation.step14_semantic_calibration run-held-out --execute
python -m src.evaluation.step14_semantic_calibration report
```

Preparation refuses existing output. Use `--root` for a different fresh preparation;
keep all subsequent commands bound to that same root. No provider or token-counting
calls occur during prepare/dry-run/report. Share `preparation.json`, `report.md`,
`report.json`, `comparison.json` and `worksheet.json`. Request/audit/attempt artifacts
remain ignored locally. Focused tests:
`python -m unittest discover -s tests -p test_step14_semantic_calibration.py`.
