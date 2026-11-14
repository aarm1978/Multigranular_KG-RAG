# Step 14 bounded anchor pilot

Preparation only. The current scope, identity/granularity and automatic-acceptance contracts remain authoritative; the multigranular ontology proposal remains unapproved. No hypothesis is an approval or production mapping. This pilot uses existing saved evidence and candidates, not new discovery or another acceptance preview.

The frozen ignored package is `var/study2_step14/anchor-pilot/prepared-v1/`. It contains 12 requests and 78 distinct occurrences: six overlap neighborhoods (66 occurrences), four initially ineligible comparisons (8), and two challenging comparisons (4). Ten units cross source families; two remain within Publications. Publications, CIROH Hub, GitHub and HydroShare are represented. All 78 occurrences are outside saved provisional coverage; that is not a claim of recovery or absence of historical subset decisions, which remain in local provenance.

| Unit | Stratum | Neighborhood | Occurrences |
|---|---|---|---:|
| U01 | A | CFE, complete small component | 9 |
| U02 | A | WSL, complete small component | 9 |
| U03 | A | Grid search, complete within-family component | 12 |
| U04 | A | NextGen, bounded witness neighborhood | 12 |
| U05 | A | Google Earth Engine, bounded witness neighborhood | 12 |
| U06 | A | Docker, bounded witness neighborhood | 12 |
| U07 | B | Singularity | 2 |
| U08 | B | HBV2.0 / HBV | 2 |
| U09 | B | NWM, Hub / Publications | 2 |
| U10 | B | NWM, GitHub / Publications | 2 |
| U11 | C | δHBV2.0 / δHBV1.0 | 2 |
| U12 | C | Grid LSTM-RAPID / Grid LSTM | 2 |

Selection is deterministic and purposive: source diversity then size for small components (two cross-family, one within-family); source diversity then group count for large components; a high-degree witness and its bounded existing neighbors, retaining family diversity. No component union is an identity rule. B uses explicit selected comparisons in initially ineligible scopes, excluding any initially eligible pair, prioritizing cross-family and literal version/family cues. C uses prior negative predictions or challenging context, selecting one cross-family and one within-family pair. Stable IDs break ties. Occurrences are disjoint across units. Prior predictions influence development selection but are not gold or supplied to the model. Version cues can concern surrounding context rather than the entity (notably Singularity); the model must resolve or abstain. Mirrored NWM evidence is not independent corroboration.

`selection.json` records exact membership and baseline coverage; `manifest.json` pins consumed inputs and prepared outputs. `provenance/Uxx.json` retains original endpoint records, literal evidence pointers, prior pair assessments and exact approval subsets. Requests contain only occurrence IDs, names/classes, source families, granularity/version metadata and source excerpts with local quotation aliases. Raw version metadata may describe source capture, not an entity release. Evidence aliases resolve to untouched original quotations locally. No hashes, execution history or previous decisions enter the prompt. The strict response schema is embedded identically in each live/Batch request. Validation checks schema, exact members, endpoint-bound supporting/contradictory citations, complete occurrence assessment and strict class compatibility; it cannot establish semantic truth. Overlapping hypotheses never imply a transitive identity union.

Approximate totals: **15,500–25,900 input tokens**, **12,000–60,000 output tokens** across **12 requests**. Input uses serialized bytes / 5 to / 3; output is a rough planning range, including reasoning, not a guarantee. The inherited per-request output limit is 16,384. Actual `usage` is preserved from native responses. No pricing or token-count API is used.

## Commands

From the repository root, with the existing Python environment containing `jsonschema` (the local preparation used `python`):

```bash
# Offline: verify prepared files; no provider or credential access
python -m src.evaluation.step14_anchor_pilot verify
# Synchronous: execute just U01 (provider call; researcher terminal only)
python -m src.evaluation.step14_anchor_pilot live --units U01
# Submit all remaining unattempted units through Batch
python -m src.evaluation.step14_anchor_pilot submit
python -m src.evaluation.step14_anchor_pilot status
python -m src.evaluation.step14_anchor_pilot retrieve
# Validate a model JSON object offline (not the native Responses envelope)
python -m src.evaluation.step14_anchor_pilot validate --units U01 --response /path/to/model-output.json
```

Alternatively, submit all 12 directly without the live command. `live --units U01 U02` supports a few synchronous requests. Both transports use exactly the same prepared bodies and schema. Existing credential loading and `batch_transport.BatchAPI` are reused. Per-unit durable intents prevent repeat execution across transports. There is one Batch submission; no automatic generation retries or scientific repairs. An uncertain submission stops with its retained intent/upload receipt and requires manual reconciliation, never blind resubmission. Live failures conservatively leave remaining claimed requests unexecuted rather than risking duplicate sends. Status/retrieval never dispatch generation. Retrieval preserves output/error files, native receipts and usage, separately reports missing/invalid outputs, and can be repeated unchanged. Validated files are explicitly hypotheses, not accepted mappings.

Outputs: `requests/U01.json` … `U12.json`, `requests.jsonl`, `provenance/`, `selection.json`, `manifest.json`; terminal execution adds `execution/` receipts, raw Batch files, hypotheses and validation reports. All remain ignored. The earlier local `anchor-pilot/v1/` was a preparation draft and is not the selected package. Frozen baseline artifacts are unchanged.

To reproduce preparation in a **fresh** ignored directory:

```bash
python -m src.evaluation.step14_anchor_pilot prepare --root var/study2_step14/anchor-pilot/reproduction-v1
python -m unittest discover -s tests -p test_step14_anchor_pilot.py -v
```

Use `--root` on subsequent commands for a nondefault package. Do not dispatch both copies. No ontology property, canonical ID, approval or graph assertion is produced by any command.
