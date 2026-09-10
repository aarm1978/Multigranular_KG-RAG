# Publication Pilot 1 — Prospective Human Core Sampling Analysis v0.1.0

**Status:** prospective comparison only; not a sample freeze and not an annotation package.

## Boundary

This is a deterministic, model-blind comparison. It reads only the whitelist declared in the companion JSON and does not read canonical unit text, section titles, model/provider material, candidate counts, or semantic extraction results.

Researcher-authorized: CORE_FEAS used only units already contained in the frozen 16-unit Publication Calibration manifest (CORE_FEAS subset Calibration); therefore no separate CORE_FEAS exclusion manifest is created or required.

## Eligible universe and exclusions

- Fixed population: 358 units.
- Eligible routed prospective universe: 210 units across 11 papers.
- Available sampling strata (5): core_discourse_nodes, core_discourse_relations, entity_role_and_study_context_relations, measurement_context_relations, scientific_entity_nodes.
- Routed scored target universe: 19 node IDs and 16 relation IDs.

| Exclusion reason | Units |
| --- | ---: |
| `calibration_manifest` | 16 |
| `no_routed_scored_target` | 37 |
| `reserved_nonprimary_artifact` | 4 |
| `source_eligibility:context_only` | 49 |
| `source_eligibility:excluded` | 39 |
| `source_eligibility:needs_review` | 3 |

## N comparison

### N=4

- Feasible: `true`; all 5 available strata are represented by the deterministic best candidate.
- Best candidate: `pub:10:sec:0008:unit:0001, pub:18:sec:0023:unit:0001, pub:34:sec:0016:unit:0001, pub:46:sec:0005:unit:0001`.
- Papers: 4; node targets: 19; relation targets: 16; strata: 5.
- Uncovered target IDs: node `none`; relation `none`.
- Nondominated greedy candidates: 17 (from 203 unique seed completions); the published candidate is the stable tie-break representative.

### N=5

- Feasible: `true`; all 5 available strata are represented by the deterministic best candidate.
- Best candidate: `pub:10:sec:0008:unit:0001, pub:15:sec:0004:unit:0001, pub:16:sec:0033:unit:0001, pub:34:sec:0015:unit:0001, pub:79:sec:0004:unit:0001`.
- Papers: 5; node targets: 19; relation targets: 16; strata: 5.
- Uncovered target IDs: node `none`; relation `none`.
- Nondominated greedy candidates: 159 (from 202 unique seed completions); the published candidate is the stable tie-break representative.

### N=6

- Feasible: `true`; all 5 available strata are represented by the deterministic best candidate.
- Best candidate: `pub:10:sec:0008:unit:0001, pub:15:sec:0004:unit:0001, pub:16:sec:0010:unit:0001, pub:18:sec:0005:unit:0001, pub:34:sec:0023:unit:0001, pub:79:sec:0004:unit:0001`.
- Papers: 6; node targets: 19; relation targets: 16; strata: 5.
- Uncovered target IDs: node `none`; relation `none`.
- Nondominated greedy candidates: 174 (from 202 unique seed completions); the published candidate is the stable tie-break representative.

## Structural/burden indicators

The JSON records each candidate’s per-unit routed node/relation/total target counts, union of observed deterministic content types, and source-conversion-status counts. These indicators are shown separately and are not combined into a burden score.

## Reproduction

```bash
PYTHONPATH=. python -m src.annotation.publication_pilot1.build_human_core_sampling_analysis
```
