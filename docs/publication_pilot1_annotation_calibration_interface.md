# Publication Pilot 1 Annotation / Calibration Interface MVP

## Boundary and versions

This synthetic/dry-run MVP is isolated under
`src/annotation/publication_pilot1/calibration/`; it does not change the accepted
Screening Mode. It uses Python stdlib HTTP, vanilla JavaScript/CSS, SQLite, and the
existing PyYAML dependency, with no network service, LLM, web search, or telemetry.

- interface: `publication-pilot1-annotation-calibration/0.1.1`
- annotation output schema: `0.1.1`
- annotation guideline: `0.1.1`
- operational annotation handbook: `0.1.1`
- effective routing: `0.1.2`

The new handbook is required because the existing handbook governs screening, not
annotation-time evidence, two-pass workflow, timing, or submission. It operationalizes
but does not redefine the frozen guideline.

## Default synthetic mode

```bash
python -m src.annotation.publication_pilot1.calibration.app \
  --annotation-session-id synthetic-smoke-a \
  --annotator-id annotator-a
```

State is ignored under:

```text
var/publication_pilot1_annotation/synthetic/sessions/<session>.sqlite3
var/publication_pilot1_annotation/synthetic/exports/
```

Synthetic reset is rejected for every other namespace.

## Production activation guard

Real calibration requires `--mode calibration --activation-file <ignored-json>`. Before
creating state, the application validates all accepted hashes, the exact 16-unit order,
the 215-candidate order, routing/text/document bindings, exact Phase-B endpoint refs,
effective-route consistency, and this
exact activation document:

```json
{
  "activation": "ACTIVATE_PUBLICATION_PILOT1_CALIBRATION_V1",
  "interfaceVersion": "publication-pilot1-annotation-calibration/0.1.1",
  "guidelineVersion": "0.1.1",
  "handbookVersion": "0.1.1",
  "routingVersion": "0.1.2",
  "calibrationIdentityOrderHash": "182710041594edb979dcfd8e39041cf98523e383c9f3498ac1d74293d0378b98"
}
```

No activation file or production state is created by this checkpoint. Activated state is
separate under `var/publication_pilot1_annotation/calibration/production/`, and production
reset is always forbidden.

## Effective routing

Menus consume only `eligibleNodeOperationalTargetIDs` and
`eligibleRelationOperationalTargetIDs`. `humanScreened*` fields remain provenance only.
Anything in `structurallyUnavailableOperationalTargets` is rejected as an annotation
target and is not interpreted as a negative or abstention. A deferred target is valid
only with an exact accepted `deferredRecordRef`; the application never synthesizes one.

## Unicode evidence

The source panel uses `textContent`, preserving canonical text. JavaScript explicitly
converts browser UTF-16 indices to zero-based half-open Unicode code-point offsets,
rejects offsets inside surrogate pairs, and round-trips selected text. The server then
requires `sourceText[start:end] == exactText` under Python code-point semantics and
derives document offsets and evidence hashes.

Each node also stores one independently validated `mentionSpan` with the same exact
source-unit, document, hash, and Unicode code-point provenance. This span identifies the
literal node mention; it does not replace or imply the separately required supporting
evidence. Node discovery scope is derived from the union of its mention, node evidence,
and attribute evidence source units.

## Canonical context and discovery scope

The source manifest's accepted `canonicalDocumentHashes` entry is bound independently of
the source-unit text hash in unit metadata, every evidence span, normalized output,
schema, export, and production integrity checks. Context candidates are limited to
`eligible` and `context_only` canonical units from that same accepted document;
`excluded` and `needs_review` units are not evidence context. Primary-unit eligibility
remains separate: context-only units cannot be opened as annotation units and never gain
target menus or completeness states.

The human policy is `bounded_human_annotation_context/0.1.0`. Initial open reads only the
primary text. Same-section and other-section candidates are returned as metadata without
text. One same-section unit is loaded only when explicitly inspected. One other-section
unit is loaded only after a request binds a routed primary-unit operational target or an
existing unresolved local assertion and one annotation-owned reason:
`distributed_assertion_evidence`, `cross_section_coreference`,
`relation_endpoint_reconciliation`, or `document_local_entity_reconciliation`. The
selector never concatenates units or enables unrestricted document text browsing.

The backend derives the narrowest frozen `discoveryScope` from the evidence-unit set:
primary only is `local_unit`, another unit in the primary section is `section_context`,
and another section is `document_reconciliation`. Multi-unit assertions require the
interface-owned `distributedEvidenceReason`; this does not alter the frozen LLM
candidate-output schema.

SQLite stores append-only exposure events with primary/context IDs, policy name/version,
scope, reason, task binding, and timestamp. Normalized annotation snapshots bind the
distinct exposed context IDs and the exposure history; deterministic session export also
contains the complete exposure log. Context inspection does not add timing-event types.

## Deterministic endpoints, attributes, and relation scope

`deterministicNodeRefs` from the primary and already exposed context units are resolved by exact ID against the
hash-bound frozen Phase-B output. The UI receives only the stable ID, exact class,
artifact identity, and a concise label. Unknown IDs and raw labels fail; no fuzzy lookup,
deferred-ID synthesis, or global entity discovery occurs. The exact Current Paper
endpoint remains available.

The node editor exposes only the six frozen class-bound attributes. Attribute evidence
is validated and referenced separately from node evidence. The backend derives
`relationScope`: a relation whose endpoint represents a distinct external artifact is
`inter_source`; otherwise it is `intra_source`. A supplied contradictory scope is
rejected. Consequently, an unconditional `intra_source` value was not a valid invariant.

## Persistence and timing

Each database binds one `annotationSessionID` to one `annotatorID`; opening it under a
different identity fails. Autosaves append revisions. Submissions create immutable
snapshots. Reopen preserves submissions, records a reason/action, and starts a new timed
revision pass.

Every timing event carries the frozen required bindings. Phase order is validated;
pause and technical-interruption intervals cannot overlap or nest. Active time is derived
from phase intervals after exclusion, not browser wall-clock time. No Gate 0 aggregation
is performed.

## Interface-specific validation codes

| Code family | Meaning |
|---|---|
| `ANNOTATION_UPSTREAM_*`, `ANNOTATION_PRIVATE_SCREENING_*` | accepted input drift |
| `CALIBRATION_PRODUCTION_ACTIVATION_*` | explicit activation failure |
| `CALIBRATION_*_DRIFT`, `CALIBRATION_*_MISMATCH` | frozen identity, membership, or binding drift |
| `ANNOTATION_EFFECTIVE_ROUTE_*` | effective routing contract failure |
| `ANNOTATION_STRUCTURALLY_UNAVAILABLE_*` | unavailable target attempted/effective |
| `ANNOTATION_DEFERRED_*` | missing or unauthorized exact deferred binding |
| `ANNOTATION_SOURCE_*`, `ANNOTATION_EVIDENCE_*` | source/hash/span failure |
| `ANNOTATION_CANONICAL_DOCUMENT_*`, `ANNOTATION_CONTEXT_*` | document binding or authorized context failure |
| `ANNOTATION_DISCOVERY_SCOPE_*`, `ANNOTATION_DISTRIBUTED_EVIDENCE_*` | scope or multi-unit rationale failure |
| `ANNOTATION_DETERMINISTIC_NODE_REF_*` | exact Phase-B endpoint resolution failure |
| `ANNOTATION_NODE_ATTRIBUTE_*` | frozen attribute name, class, value, or evidence failure |
| `ANNOTATION_NODE_*`, `ANNOTATION_RELATION_*` | target, action, endpoint, signature, direction, or evidence failure |
| `ANNOTATION_TARGET_STATE_*`, `ANNOTATION_UNCERTAINTY_*` | completion/uncertainty failure |
| `ANNOTATION_TIMING_*` | vocabulary, order, pause, or interruption failure |
| `ANNOTATION_STATE_CONTRACT_MISMATCH` | stable session identity/version mismatch |
| `ANNOTATION_SUBMITTED_*`, `ANNOTATION_REOPEN_*` | immutable revision/audit failure |
| `ANNOTATION_FORBIDDEN_FIELD`, `ANNOTATION_UNKNOWN_FIELD` | hidden/model/gold/negative/consolidation state |
| `CALIBRATION_PRODUCTION_RESET_FORBIDDEN` | production isolation |

Exports are backend-revalidated before deterministic serialization.
