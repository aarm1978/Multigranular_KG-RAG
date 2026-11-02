# SciERC secondary contextual-equivalence analysis v0.1.0

Status: materialized for researcher acceptance; Step 9 remains open.

## Authority and limitations

The researcher explicitly authorized materialization of the final local ignored
`scierc_overlap_review_progress_v0.6.0` package. This is a post-run,
LLM-assisted contextual-equivalence sensitivity under the researcher-approved
rubric, **not independently human-adjudicated gold**, a replacement extraction
score, or evidence of an improved/adapted extractor. No new semantic judgments
are made here. Strict A, document-rejection B, and mechanical overlap remain
unchanged. See the preserved `scierc_postrun_evaluation_v0.1.0.md`,
`scierc_overlap_sensitivity_addendum_v0.1.0.md`, and
`scierc_overlap_sensitivity_report_v0.1.0.md`. The complete bytes of
`evaluation_decisions.md` are preserved; this document does not amend them.

The final package's rubric accepts contextual specificity/boundary differences,
explicit aliases and relation granularity where the same local scientific unit
or assertion is retained. It excludes changed heads, member/whole substitutions,
problem/domain and representation/object substitutions. This implementation
ingests those existing decisions, not their semantic validity. Four relation
decisions remain equivalence-not-established, not proven non-equivalence.
Original per-case researcher-acceptance and assistant-review provenance statuses
are retained; authorization of this analysis does not convert them to human gold.

## Deterministic materialization

Only v0.6.0 supplies interpretations: 447 selected cases and 61 unique competing
alternatives associated with 52 nonaccepted selected cases. The original review
package is used solely to verify source identities/hashes, recover alternative
endpoint identities, and check collisions with strict-locked identities. No
earlier progress package or raw gold is read. Every selected source payload is
compared with its original identity. Where present (124 cases), source-case hashes
are also checked; all 447 are newly hash-bound. Alternative identities are checked
against original case ID, document/layer, labels, argument text, context and IoU.

All strict matches are locked. Accepted selected pairs then accepted alternatives
claim prediction and gold IDs globally within document/layer. Any collision,
duplicate case, missing coverage or source drift aborts; no rematching choice is
invented. The seven accepted alternatives are disjoint from every already accepted
pair. Counts are recomputed from the two ledgers, not the supplied summary.
All original prediction/gold supports remain in the denominators; rejected and
undetermined correspondences are not removed from the evaluation universe.

## Results

| Layer | TP | FP | FN | Gold / prediction support | Precision | Recall | F1 | Added over strict A |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Entity contextual | 994 | 1348 | 691 | 1685 / 2342 | 0.4244235696 | 0.5899109792 | 0.4936677427 | 167 |
| Relation contextual | 594 | 1007 | 380 | 974 / 1601 | 0.3710181137 | 0.6098562628 | 0.4613592233 | 200 |

| Ledger / layer | Accepted equivalent | Rejected not-equivalent | Undetermined |
|---|---:|---:|---:|
| Selected entities | 161 | 54 | 0 |
| Selected relations | 199 | 29 | 4 |
| Alternative entities | 6 | 32 | 0 |
| Alternative relations | 1 | 22 | 0 |

Selected totals are 360 accepted, 83 rejected, 4 undetermined. Alternative totals
are 7 accepted, 54 rejected, 0 undetermined. Contextual additions are 161+6 entity
and 199+1 relation correspondences. These are secondary rubric-based
correspondences, not new predictions. No composite score is computed.

## Reproduction and provenance

Run `python -B -m src.extraction.llm.publications.scierc_contextual_review` with the
existing local ignored inputs. The generator performs exclusive/idempotent writes
only to `data/curation/papers/m2/scierc_contextual_equivalence_v0.1.0/`:
`decision_ledger.jsonl`, `alternative_rematch_ledger.jsonl`,
`aggregate_metrics.json`, and `provenance_manifest.json`. Compact ledgers omit
sentence payloads and narrative judgments while retaining IDs, categories,
interpretations, provenance and source-case hashes. The manifest binds all five
final-package files, source identity files, accepted prior metrics/projections,
and implementation. Authentic ignored inputs are never rewritten.

Focused checks: `python -B -m pytest -q tests/test_scierc_contextual_review.py`.
No provider/model calls, extraction, prompt changes or new adjudication occurred.
