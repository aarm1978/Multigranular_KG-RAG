# Publication pre-live deterministic integration

**Version:** 0.1.1

**Ontology authority:** 0.1.4

**Status:** deterministic implementation and relation development gate complete; fresh full-semantic DEV run ready

This record covers the deterministic work completed after the ontology-authority
migration and before any fresh DEV-SET-0 provider call. It does not change the ontology,
prompt semantics, candidate target universe, screening, routing, calibration, annotation
decisions, evaluation matching, or frozen historical outputs.

## Trusted section-title transport

The current provider path derives its request-specialized JSON Schema through
`derive_trusted_evidence_metadata_schema(request)`. The schema narrows only
`evidenceSpan.sectionTitle` to the exact trusted
`request.sourceUnit.sectionTitleRaw` value:

- string authority: `{"type": "string", "const": <exact raw string>}`;
- null authority: `{"type": "null", "const": null}`.

Markup and whitespace are preserved byte-for-byte. The binding happens before provider
generation. Provider output is neither corrected nor normalized afterward, and the V4
validator continues to require exact equality. The frozen candidate-output schema remains
the semantic envelope authority; the narrower provider schema is a request-bound
transport projection.

## Post-acceptance D-26 materialization

Generic `ciroh:mentions` (`D-26`) is pipeline-derived after explicit acceptance. It is
not a candidate type, annotation decision, evaluation denominator, or routing target.
The materializer consumes a small neutral accepted-semantic projection so the same core
logic can receive future adjudication output or a clearly labelled development adapter.
It does not run in the response parser, V1–V12 validator, or pre-adjudication usable-output
materializer.

The frozen ontology specification supplies the D-26 domain and range; descendant class
compatibility is expanded mechanically from declared parent relationships. The separate
versioned operational policy records only materialization behavior and the reviewed
stronger-role/specialized-edge precedence.

Paper-to-entity fallback requires an accepted mentionable entity, at least one valid
evidence occurrence, exactly one canonical Paper across that evidence, and a trusted
pre-existing Paper endpoint. Missing or ambiguous Paper provenance fails closed; the
materializer never invents a Paper identifier.

Discourse-to-entity fallback requires accepted endpoints, the same canonical Paper, the
same source unit, valid endpoint evidence, and **EXACT COORDINATE CONTAINMENT**:

```text
discourse.startOffsetInUnit <= entity.startOffsetInUnit
entity.endOffsetInUnit <= discourse.endOffsetInUnit
discourse.startOffsetInDocument <= entity.startOffsetInDocument
entity.endOffsetInDocument <= discourse.endOffsetInDocument
```

Boundary equality is permitted. Partial overlap, containment in only one coordinate
system, cross-unit evidence, cross-Paper evidence, invalid evidence, and endpoint
coexistence alone are insufficient. Every emitted discourse edge persists the exact
evidence pair and both coordinate sets used.

Generic edges are fallback-only. An accepted stronger-role or specialized `mentionsX`
edge with the identical source and target suppresses explicit generic materialization.
No stronger relation is inferred from containment, lexical proximity, or shared
endpoints. Edge identity is the SHA-256-derived canonical tuple of derivation kind,
materializer version, D-26, relation name, source ID, and target ID. Output ordering and
hashes are stable, idempotent, and timestamp-free.

## Zero-call replay boundary

The new replay directory is explicitly labelled:

- `DEVELOPMENT_DIAGNOSTIC_REPLAY`;
- `COUNTERFACTUAL_TRANSPORT_EMULATION`;
- `NOT_AUTHENTIC_NEW_MODEL_OUTPUT`;
- `NOT_GOLD`;
- `NOT_FORMAL_EVALUATION`;
- `providerCalls = 0` and `modelCallMade = false`.

Only authentic C1B `evidenceSpan.sectionTitle` values are copied to the exact current
trusted title, emulating the approved pre-generation transport result. All other
provider semantic-payload fields remain equivalent to the authentic C1B payload. Current
ontology-0.1.4 requests are then processed by the unchanged parser and V1–V12 validator.
The development materializer adapter uses `DEVELOPMENT_VALIDATOR_USABLE_PROXY` and
`NOT_FORMAL_ACCEPTANCE`; it is not adjudication and cannot establish total semantic
recall.

The replay measured 254 candidates: 252 validated and 2 rejected. Both rejections remain
in DEV-05 and arise from the authentic offset/literal-evidence defect. DEV-06 retains one
non-fatal `UNREFERENCED_EVIDENCE_SPAN`; DEV-09 retains one non-fatal
`SEMANTIC_NORMALIZATION_PENDING_REVIEW`. No section-title failure remains.

DEV-01 produced nine Paper fallback edges and nine discourse fallback edges. Five
`RelatedResearch` to `NamedPlace` edges share evidence `evidence-0008`, including US
Midwest, Great Lakes regions, coastal Southeast, Southwest, and California. These are
diagnostic mechanics over usable nodes, not claims of node recall or gold correctness.
Because C1B contains no model-authored relations, empirical stronger-edge suppression is
not estimated from this replay; deterministic fixtures cover it.

## Target and fresh-call readiness

The target/routing authority remains unchanged: 46 candidate-authorable node targets,
40 direct open-discovery targets, 4 deterministic-context targets, and 2 deferred-
resolution targets. The 40 direct targets remain universally eligible across structurally
valid DEV source units; section-role semantic pre-screening remains unauthorized. D-26
adds zero model-authorable relation targets and never creates a missing entity node.

The methodological distinction remains:

```text
AVAILABLE TARGET + MODEL OMISSION = extraction-recall issue
TARGET NOT AUTHORIZED / binding unavailable = scope or binding issue
ACCEPTED NODE WITHOUT STRONGER CONNECTIVITY = possible generic fallback connectivity
```

The frozen target profile contains 26 model-authorable Publication relation targets.
Recorded provider development through C1B exposed nodes only and still provides no
authentic end-to-end provider observation for those relations. The deterministic relation
gate now provides 26/26 structural request/parser/V1–V12 fixture coverage and confirms all
26 are endpoint-bindable for DEV-01 through DEV-10.

Candidate `relationScope` is assertion-level endpoint provenance. V8 derives
`intra_source` when resolved endpoints share the same trusted artifact ID and
`inter_source` when their artifact IDs differ. Ontology relation metadata such as
`intra`, `cross`, and `same` does not universally fix this candidate field. Consequently,
a source-local DatasetMention or provisional Repository candidate can validly receive an
`intra_source` Paper edge, while an exact or resolver-bound external DatasetResource or
Repository receives `inter_source`. The provider compiler retains the frozen two-value
scope enum and does not infer identity or repair generated scope.

The next prospective run is frozen by
`data/curation/papers/m2/relation_development_gate/publication_relation_development_gate_plan.json`.
It uses one combined request per DEV unit with the existing 40 open-discovery nodes and
all 26 eligible model-authorable relations, trusted section-title binding, explicit
endpoint references, unchanged prompt/parser/V1–V12 validation, complete raw-response
provenance, and no post-generation correction. D-26 remains post-acceptance only. The
pre-committed review categories separately cover processing/structure, evidence, node
extraction, relation extraction, expected abstention, and derived generic connectivity.

The core accepted-semantic projection remains neutral between human-adjudicated gold and
a future automated production acceptance policy. The latter must be frozen separately
after the extraction evaluation gate and is not designed here.
