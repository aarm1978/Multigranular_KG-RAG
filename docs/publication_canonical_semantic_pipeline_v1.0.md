# Canonical Publication semantic pipeline v1.0.0

The prospective implementation is
`src/extraction/llm/publications/publication_semantic_pipeline.py:semantic_attempt`.
All future Publication corpus expansion uses request/context preparation → provider
execution → this canonical semantic attempt → frozen Step 4 acceptance. Do not
introduce another Publication semantic runner for a new corpus or artifact family.
Batch runners own population, transport, persistence and resume, not semantic stages.

The authority is the whole frozen DEVSET0 schema013 closure
(`publication_devset0_schema013_closure_v1.0.json`, implementation `7d48e94`,
closure `ddb2511`), bundle `publication-semantic-v0.1.5-schema-v0.1.3`, prompt
`publication-development-0.1.8`, candidate schema 0.1.3, ontology/targets 0.1.5.
DEV-09/10 are authentic schema013 witnesses; DEV-01–08 retain authentic schema012
generations with schema013 compatibility replay. The witnesses alone are not the
semantic authority. Production also composes the frozen Step 5 request/context/
configuration authority and frozen Step 4 acceptance/retry policy.

`semantic_attempt(raw, request, provider_metadata=..., production=..., attempt_number=...)`
binds authentic metadata, parses, binds exact endpoint and evidence provenance,
runs unchanged V1–V12, and materializes usable output. Production metadata binding
retains the original requestID and requestInputSha256 and projects `complete_section`
to candidate-validation `section_context` only with includedCompleteSection=true.
Provider requests are never constructed from this validation view. DEV metadata
binding retains its existing request-hash behavior. The legacy DEV runner delegates
schema013 processing to this implementation; earlier historical behavior remains.

## Methodological amendment: evidence failure isolation 1.0.0

Researcher-authorized `publication-evidence-failure-isolation/1.0.0` changes failure
granularity from response to evidence/record for identifiable span-local failures.
Exact grounding, locatorAnchor semantics, and V1–V12 remain unchanged. The original
`bind_evidence_spans` implementation and all historical artifacts remain preserved.
There is no normalization, fuzzy matching, case folding, locator fabrication,
semantic repair, or choice between ambiguous occurrences.

The isolatable codes are LITERAL_NOT_FOUND,
AMBIGUOUS_LITERAL_REQUIRES_LOCATOR_ANCHOR, INVALID_LOCATOR_ANCHOR and
AMBIGUOUS_LITERAL_WITHIN_LOCATOR_ANCHOR (each prefixed `EVIDENCE_BINDING_`).
The pipeline retains every finding and failed evidenceSpanID, and projects only
successfully bound spans into validation. It excludes every node, edge, abstention
or deferred record that references a failed span at any depth, including attributes.
Each exclusion records original ID, type, full record, failed reference paths and
`UNBINDABLE_EVIDENCE_DEPENDENCY`. Retained records keep their original references.
V1–V12 determines subsequent missing-endpoint/lifecycle effects. A safely empty
projection is processable, not a reason for another provider sample.

Unidentifiable records, duplicate/missing evidence IDs, invalid structures and
non-isolatable binding failures retain response-level failure. This amendment does
not change Step 4; offline reapplication may select a formerly terminal authentic
attempt because its amended deterministic result is now processable. Original
selections remain immutable and the change is recorded in replay provenance.

## Offline canonical C1 replay

From the repository root:

```sh
python -m src.extraction.llm.publications.production_runner --replay-canonical-semantics
```

The action denies network and key access, verifies DEV witnesses, then requires
semantic parity for all 217 originally processable requests. Its baseline is the
first 177 downstream-replay-v0.1.0 artifacts and the later 40 native attempts.
Only derived artifact hashes may differ in the parity comparison; semantic content,
identities, statuses, findings and evidence coordinates may not. A mismatch aborts
before replaying any of the 10 terminal requests. The original attempt count and
the timeout request's attempt-2 selection are preserved.

Results are append-only in each request's `canonical-semantic-replay-v1.0.0/`.
The root namespace contains an aggregate report and before/after-verified hash
inventory of all original artifacts, including prior replay and selections. Raw
and provider artifacts are read directly from original attempts. No semantic or
gold-correctness claim follows from this technical replay. Step 6C closure is
separately bound by
`data/curation/papers/m2/publication_step6c_canonical_c1_freeze_v1.0.0.json`;
its tracked prediction, lifecycle, and result-index artifacts are the authoritative
autonomous C1 realization for Step 7 and later Publication KG construction.
