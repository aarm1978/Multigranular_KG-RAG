# Materialized evidence implementation v0.5

Authority: `study2-materialized-corpus-evidence/0.1.0`, [amendment](study2_materialized_corpus_evidence_amendment_v0.1.md).
Implementation/derived interpretation: `source-local-materialized-evidence/0.5.0`.

## Explicit routes

- `src.extraction.llm.materialized_evidence.overlay()` activates source-local materialized binding for recorded historical requests without changing their envelopes. Hub uses the verified original content_mdx, literal binder and original offsets; GitHub removes only the documentary code-format hold. HydroShare and structured ModelVersion binding are unchanged.
- The Hub validator's new `materialized_evidence=False` default preserves historical behavior. Opt-in binding eligibility replaces the lexical prose prerequisite, **not** the pending `explanatory_parameter_prose` semantic gate. Example attachment, semantic conditions and dependency closure still use the existing validator/construction policy. No semantic gate is set true by the binder. No renderer or new semantic judge is introduced.
- `materialized_evidence.build_specialized(templates, ...)` builds future specialized envelopes with the new prompt/authority and contract hash. Use `prospective()` for their native verification/consolidation and `replay_specialized(...)` for their recorded-response replay. Never use that prospective prompt context when replaying historical envelopes. Existing production defaults are unchanged; no new production queue is prepared here.
- `src.extraction.llm.publications.materialized_source_units.build_document_units(...)` is a separate prospective builder. It makes code-formatted literal text eligible without changing raw text, offsets, section boundaries or independent source-quality rules. Historical Publication builders, generated units, production and evaluation are unchanged. Publications are not part of the three-family v4 comparison.

The scoped overlays restore their hooks on exit and are single-threaded; do not run overlapping validation/preparation contexts in concurrent threads.

## Offline v4 comparison

From the repository root, using the existing researcher environment:

```sh
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python -m src.evaluation.source_local_supplemental_review_v4
```

Requires the original v6 queue/journal/receipts, supplemental response, completed v2/v3 reviews, coverage diagnostic v1, and historical Git objects. Output is a new, overwrite-refusing `var/study2_step13/source-local-supplemental-review/v4/`. A partial failed run is not a completed interpretation and is never automatically overwritten.

The runner reuses native receipt verification, semantic replay and exact owner consolidation. It verifies the original validator pin against Git checkpoint `9679b8dcb1b29be622b781439932b8003285a133` for the explicit optional validator extension, in addition to the two existing v2 historical substitutions; it does not alter or relax any stored pin. Current overlay code and amendment hashes are separately recorded. Historical v3 can be reproduced at its original implementation checkpoint.

All 1,005 selected identities, 335 complete owners, authentic candidates, abstentions, six quarantined abstentions and separate Batch/live accounting must reconcile. Every accepted record must survive with identical semantic identity/evidence/provenance; comparison ignores only derived replay hashes and superseded lexical eligibility metadata. Explained changes to previously unbound held candidates retain their before/after source-local IDs and exact evidence references. Independent holds remain reported, with no assumed recovery count. Unexplained changes stop execution.

Local `groups/` and `owners/` contain native reproducibility reports and may be large. Share **only `share/`**, containing `synthesis.md`, `summary.json`, `manifest.json`, `comparison.json`, and `examples.json`. These contain counts, transitions, hashes, IDs, dependency causes and bounded quotations/offsets, not full source documents or authentic response bodies. The examples are diagnostic illustrations, not human adjudications.

Literal eligibility is not proof of the model's semantic interpretation. Existing construction-releasable interpretive conditions remain construction-releasable under the unchanged substantive policy; this implementation does not independently detect every unsupported execution claim. Prospective prompts explicitly prohibit those inferences. Historical model omissions/abstentions remain unchanged, and output differences are rule-induced information recovery, not precision, recall, F1 or Step 13 scientific completion.
