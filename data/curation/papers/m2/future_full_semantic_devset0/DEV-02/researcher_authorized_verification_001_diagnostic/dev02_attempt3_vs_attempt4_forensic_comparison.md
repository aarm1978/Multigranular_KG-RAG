# DEV-02 attempt-3 ↔ attempt-4 forensic comparison

**Development-only diagnostic.** This is a zero-cost comparison of preserved authentic artifacts. It does not alter, repair, supersede, accept, annotate, or evaluate either attempt, and it does not establish an acceptance threshold for a future run.

## Inputs and configuration

| Dimension | Attempt 3 | Attempt 4 |
| --- | --- | --- |
| Authentic attempt root | `researcher_authorized_recovery_002/DEV-02` | `researcher_authorized_verification_001/DEV-02` |
| Prompt | `publication-development-0.1.6` | `publication-development-0.1.7` |
| Request-specialized schema | `publication-request-specialized-0.4.0` | `publication-request-specialized-0.5.0` |
| Provider-input SHA-256 | `ea450a435e747dc3cda0d12120a6424a6af09380d4429576ee173e97f3be3874` | `2fdc86e178ea3990da967f40aa9b13532f8af2aae3f5f1c7e63d0b61b12d67bf` |
| Model-authorable schema SHA-256 | `7c0b8ff150dc0af790a5c27a7c8046c287a317eb3ff3b4bcf40c16556d21f4b7` | `64a10f9371cdd9ad3616140f0548341a18ec9e128abb4f459bf02ef7fc356884` |
| Raw-output SHA-256 | `e9ce2dcdce26ad3307a9ef44a2bdcd829b01aaae5a6fbbc3b111174776ad20d8` | `f5c90100c785d0c301d26305a16ab5119499bca727b6f4cc132a263ebe7fc38c` |

The reviewed v0.1.6→v0.1.7 prompt/schema diff preserves semantic target search, relation instructions, completeness instructions, and abstention instructions. The prospective change is endpoint `artifactID` authorship: attempt 3 required it in model output; attempt 4 makes it trusted pipeline metadata, deterministically bound before deterministic evidence binding and unchanged V1–V12.

## Structural comparison

| Dimension | Attempt 3 | Attempt 4 |
| --- | ---: | ---: |
| Candidate nodes | 53 | 43 |
| Candidate edges | 26 | 23 |
| Evidence spans | 29 | 24 |
| Usable nodes / edges | 17 / 0 authentic; 53 / 26 only in the separately rooted endpoint counterfactual | 42 / 23 |
| Envelope | `partially_valid` (36 `SCHEMA_VALIDATION_FAILED`; 36 `ENDPOINT_LIFECYCLE_INVALID`) | `partially_valid` (no schema or endpoint-lifecycle findings) |
| Other findings | none beyond the endpoint-artifact cascade | `ATOMICITY_VIOLATION` ×1; `UNREFERENCED_EVIDENCE_SPAN` ×6 |

### Node class frequencies

| Class | A3 | A4 | Class | A3 | A4 |
| --- | ---: | ---: | --- | ---: | ---: |
| ProcessBasedModel | 3 | 3 | Variable | 4 | 4 |
| EvaluationMetric | 7 | 7 | Definition | 4 | 6 |
| Method | 6 | 3 | Limitation | 5 | 4 |
| DatasetMention | 4 | 1 | DataDescription | 3 | 1 |
| RiverReach | 3 | 4 | Finding | 2 | 1 |
| Watershed | 2 | 1 | Parameter | 0 | 2 |
| Claim / RelatedResearch / ResearchProblem | 1 / 1 / 1 | 0 / 0 / 0 | Tool / Concept / ResearchGoal / Experiment / NamedPlace / WaterBody | 1 each | 1 each |
| Gauge | 1 | 0 |  |  |  |

### Node target frequencies

```text
A3: DOM02:1 DOM03A:3 DOM04:4 DOM05:1 DOM07A:2 DOM07B:3 DOM07C:1
    DOM07D:1 DOM08:1 DOM11:7 P07:1 P09:1 P11:4 P13:6 P14:1 P16:2
    P18:1 P19:5 P24:1 P25:4 P26:3
A4: DOM02:1 DOM03A:3 DOM04:4 DOM05:1 DOM07A:1 DOM07B:4 DOM07D:1
    DOM08:1 DOM11:7 DOM12:2 P09:1 P11:6 P13:3 P14:1 P16:1 P19:4
    P25:1 P26:1
```

Prefixes above are the suffixes of the existing operational IDs (for example, `DOM12` is `PUB-N-A-DOM12-PARAMETER`); no target contract is implied or altered.

### Relation-type frequencies

| Relation | A3 | A4 | Relation | A3 | A4 |
| --- | ---: | ---: | --- | ---: | ---: |
| usesModel | 4 | 4 | mentionsVariable | 4 | 4 |
| reportsMetric | 7 | 3 | studiesFeature | 2 | 5 |
| mentionsDataset | 3 | 0 | hasParameter | 0 | 2 |
| hasLimitation / mentionsConcept / mentionsTool / studiesPlace / usesDataset | 1 each | 1 each | resolves | 1 | 0 |

## Semantic assertion method and partitions

Node identity ignores candidate/evidence IDs and order. It compares ontology class, normalized referent/value, and the source-supported evidence proposition; label shortening and different span segmentation are treated as equivalent where they assert the same source proposition. Edge identity compares relation type, semantically matched endpoints, and relation-specific evidence proposition. This is a diagnostic matching rule, not an acceptance rule.

| Assertion kind | Shared | Attempt-3-only | Attempt-4-only |
| --- | ---: | ---: | ---: |
| Nodes | 32 | 21 | 11 |
| Edges | 14 | 12 | 9 |

The 32 shared nodes include the same core models, variables, named place, evaluation metrics, several definitions, methods, experiment, and recurring limitations despite changed IDs and span segmentation. The 14 shared edges include the recurring `usesModel`, `mentionsVariable`, `mentionsConcept`, `mentionsTool`, `studiesFeature`, `studiesPlace`, and metric assertions where both endpoint propositions match.

**Reconciliation note.** The original exclusive-review prose mistakenly listed two semantically shared A3/A4 node propositions as exclusive (the dataset-selection description and shortened research goal), omitted three A3-only nodes (HEC-RAS/BLE dataset mention, approximately-six-HUC8 limitation, and the two-span TN definition), omitted two A4-only shortened limitations, and listed two shared A4 edges (`mentionsConcept` and `mentionsTool`) as exclusive. The inventories below are the reconciled projection and sum exactly to the table above.

### Exclusive node review

The entries below are individual semantic assertions; short labels identify the normalized referent. Classification uses only the bound source evidence and the existing target contract.

| Attempt | Classification | Assertions |
| --- | --- | --- |
| A3-only | strongly supported | `DataDescription — 1%/0.2% maps, discharges, and extents`; `DataDescription — 49 HUC8 coverage`; `DatasetMention — HEC-RAS/BLE dataset`; `DatasetMention — high-water marks`; `DatasetMention — remote-sensing observations`; `DatasetMention — modeled local extents`; `Definition — TN (two-span definition)`; `Finding — BLE reservoir extents / false negatives`; `Limitation — NWM reservoirs not accounted for`; `Limitation — approximately six HUC8s lack NWM-MS reaches`; `Method — HAND approach coupled with SRCs`; `Method — imputation for missing reaches`; `ResearchProblem — missing streamflow`; `Variable — corresponding discharges`; `Watershed — 49 HUC8s`. |
| A3-only | plausible / needs semantic review | `Claim — detangling exogenous variables`; `RelatedResearch — CSI utility statement`; `Method — use of existing HEC-RAS models`; `Limitation — single-source information limit`; `Limitation — frequency dependence of CSI/FAR`. |
| A3-only | unsupported or likely over-extraction | `Gauge — gages` (generic type, no station identity). |
| A4-only | strongly supported | `Definition — POD indicator of inundated-region skill`; `Definition — FAR indicator of non-inundated-region skill`; `Limitation — lack of headwater representation in NWM`; `Parameter — 1%`; `Parameter — 0.2%`; `RiverReach — NWM reach`; `Variable — median recurrence discharge`. |
| A4-only | plausible / needs semantic review | `DatasetMention — BLE benchmark data set` (source names the benchmark context); `Limitation — reservoir treatment not properly accounted for`; `Limitation — frequency dependence of CSI/FAR`. |
| A4-only | unsupported or likely over-extraction | `Definition — true negatives` because the bound literal crosses intervening page/figure material and is the sole `ATOMICITY_VIOLATION` node. |

### Exclusive edge review

| Attempt | Classification | Assertions |
| --- | --- | --- |
| A3-only | strongly supported | `mentionsDataset(Paper, high-water marks)`; `mentionsDataset(Paper, remote-sensing observations)`; `mentionsDataset(Paper, modeled local extents)`; `mentionsVariable(Paper, corresponding discharges)`; `studiesFeature(Paper, 49 HUC8s)`; `usesDataset(Paper, HEC-RAS/BLE dataset)`. |
| A3-only | plausible / needs semantic review | `hasLimitation(BLE-reservoir finding, reservoir limitation)`; `resolves(HEC-RAS method, missing-streamflow problem)`. |
| A3-only | unsupported or likely over-extraction | `reportsMetric(Experiment, TP)`; `reportsMetric(Experiment, FP)`; `reportsMetric(Experiment, FN)`; `reportsMetric(Experiment, TN)` — all are contingency-table components, not explicitly reported experiment metrics. |
| A4-only | strongly supported | `hasParameter(spatial-intersection method, 1%)`; `hasParameter(spatial-intersection method, 0.2%)`; `mentionsVariable(Paper, median recurrence discharge)`; `studiesFeature(Method, NWM reach)`; `studiesFeature(Paper, West Fork Plum Creek)`; `studiesFeature(Paper, Clear Fork Plum Creek)`; `studiesFeature(Paper, Plum Creek)`; `hasLimitation(headwater-FN finding, NWM-representation limitation)`. |
| A4-only | plausible / needs semantic review | `usesDataset(Paper, BLE benchmark data set)`. |
| A4-only | unsupported or likely over-extraction | none identified from the bound source evidence. |

### Interpretation limited to this diagnostic

Likely recall loss in A4: A3's direct source-supported dataset mentions, 49-HUC8 coverage/descriptive assertions, missing-streamflow problem/method/relation, and the `corresponding discharges` assertion were not re-emitted. Likely precision improvement in A4: it does not re-emit the four A3 `reportsMetric` edges for TP/FP/FN/TN and avoids A3's generic `Gauge` assertion. A4 adds strongly supported parameters, NWM-reach, median-discharge, creek, and headwater-limitation assertions, but its page-crossing TN definition remains a discrete quality concern.
