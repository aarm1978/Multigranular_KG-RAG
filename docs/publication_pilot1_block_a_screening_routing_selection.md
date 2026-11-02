# Publication Pilot 1 Block A — Screening, Routing, Selection, and Gate 0

**Block A infrastructure version:** 0.1.4

**Screening/routing schema versions:** 0.1.1 / 0.1.2

**Status:** Publication Pilot 1 Block A screening/routing and calibration-selection artifacts available for independent review; Gate 0 not yet executed; final sample not frozen

**Boundary:** Publication Pilot 1 only

Artifact versions are intentionally independent:

```text
Block A infrastructure       0.1.4
screening/schema             0.1.1
routing/schema               0.1.2
selection policy             0.1.4
target coverage matrix       0.1.0
pre-Gate-0 candidate order   0.1.3
calibration manifest         0.1.3
target-family mapping        0.1.0
target display catalog       0.1.0
Gate-0 policy                0.1.0
```

The mapping, display catalog, artifact quota-role policy, and Gate-0 policy remain at
0.1.0 because their semantics did not change. Screening remains at 0.1.1 because the
human-reviewed record is unchanged. Routing advances to 0.1.2 to distinguish historical
human routing from structurally available effective routing. The coverage matrix gains
an explicit 0.1.0 artifact version; candidate order and calibration manifest advance to
0.1.3 because they were prospectively recompiled from corrected effective routing.

## Purpose and inputs

Block A converts the accepted 358-unit Publication Pilot 1 population into a human
screening worklist and deterministic routing/selection inputs. The accepted builder
v0.1.4, its fifth materialization, the source-unit contract, and the frozen target
profile are immutable inputs. The implementation makes no network calls and uses no
model output.

The generator is:

```text
src/extraction/llm/publications/build_publication_pilot1_block_a.py
```

The initial infrastructure-only materialization, used before a reviewed worklist exists,
is run from the repository root as:

```bash
python -m src.extraction.llm.publications.build_publication_pilot1_block_a
```

It validates the accepted inventory, accepted manifest, and target-profile hashes, then regenerates the
worklist, complete target-family mapping, display catalog, selection-policy draft, and
Publication-only Gate-0 policy byte-for-byte. Re-running it with unchanged inputs is
idempotent.

The completed production compilation path uses the authoritative reviewed worklist:

```bash
python -m src.extraction.llm.publications.build_publication_pilot1_block_a \
  --reviewed-worklist var/publication_pilot1_screening/exports/publication_pilot1_screening_worklist_reviewed.csv
```

This path validates the human-reviewed input and materializes screening JSONL, routing,
coverage, calibration selection, and the pre-Gate-0 per-artifact candidate order.

## Human-screening boundary

The generated worklist is:

```text
data/curation/papers/pilot1/publication_pilot1_screening_worklist.csv
```

Columns through `deferredRecordRefs` are deterministic and must not be edited. Human
multi-valued columns use a pipe (`|`) delimiter, no JSON, and are serialized in lexical
order. A qualified reviewer must complete these fields for every structurally eligible
row:

```text
screeningReviewerID
screenedAt
screeningStatus
screeningRationale
likelyExhaustiveEmptyTargetIDs
likelyRecurringDistinctions
expectedAssertionDensity
expectedRelationDensity
routingComplexity
distributedEvidenceLikely
sectionContextUseful
deterministicEndpointLikely
routedNodeOperationalTargetIDs
routedRelationOperationalTargetIDs
screeningNotes
```

`screeningStatus` must be `reviewed` for each of the 267 open rows. Density fields use
`none | low | medium | high`; routing complexity uses `low | medium | high`; and boolean
fields use lowercase `true | false`. Routed operational target IDs must come from the
generated mapping/catalog. `sectionContextUseful` and
`distributedEvidenceLikely` are separate human judgments and may differ.
`likelyExhaustiveEmptyTargetIDs` is only a prospective expectation; it is not absence,
annotation, or gold. It may contain only routed `extract_and_evaluate` targets, because
those are the only targets that default to prospective `exhaustive` completeness.
`extract_and_monitor` targets remain fully routable and contribute to reporting-family,
sampling-stratum, primary-candidate, calibration-diversity, and candidate-order coverage,
but default to `non_exhaustive_monitor` and are rejected from the exhaustive-empty field.
A future monitored-pair promotion would require an explicit pre-annotation completeness
decision not present in Block A 0.1.4. Closed, out-of-scope, and deferred-resolution-only
targets also remain rejected.

`likelyRecurringDistinctions` uses only these exact values:

```text
Model/Method/Algorithm/Tool
Finding/Conclusion
ResearchProblem/ResearchGoal
use/mention/reference
EvaluationMetric/Parameter
```

The generator never infers these values from real source text.

The deterministic identity columns preserve two distinct identifiers:

```text
sourceArtifactID = canonicalArtifactID from the accepted source-unit record
paperID = local artifact key used for grouping and per-artifact candidate order
```

`sourceConversionStatus` is also deterministic. It preserves the accepted manifest's
artifact-level `conversionStatusSummary`, not source-unit eligibility or review state.
The current controlled values are `canonical_markdown_available` and
`canonical_markdown_sanitized_forbidden_controls`.

The 49 context-only, 39 excluded, and three Publication 34 needs-review rows are
structurally prefilled. They remain non-open, and their semantic fields must not be
populated. In particular, the three ambiguous-reference units remain
`blocked_needs_review` and cannot enter calibration or the post-Gate-0 candidate pool.

No actual annotations, relations, evidence spans, gold labels, positive counts,
adjudication decisions, predictions, confidence, or validator outcomes belong in the
worklist.

## Target-family mapping

The mapping covers all 105 operational rows in frozen profile order. Treatment maps
mechanically to decision role: `extract_and_evaluate` is `blocking`,
`extract_and_monitor` is `monitored`, `deferred_resolution` is
`deferred_resolution_only`, and every other treatment is `excluded_or_follow_on`.
Only blocking and monitored rows receive one of the frozen ten reporting families.

The human reviewer makes one semantic routing decision through
`routedNodeOperationalTargetIDs` and `routedRelationOperationalTargetIDs`.
`likelyReportingFamilies` and `likelySamplingStrata` are not human-editable worklist
columns. During compilation they are deterministically derived as sorted unique values
from the routed blocking/monitored targets and the mapping. Deferred-resolution-only
targets contribute neither a reporting family nor a sampling stratum. The derived values
are then propagated to screening JSONL, routing, coverage, calibration selection, and
candidate ordering.

Open node rows follow the frozen family headings: research framing; discourse structure;
methods/experiments; models/algorithms/tools; findings/conclusions/limitations/future
work; metrics/parameters/variables; datasets/repositories; and concepts/geography. Open
relations whose operational name expresses use, mention, reference, or code-repository
association map to `use_mention_reference_relations`; the remaining open semantic
relations map to `discourse_relations`. The five sampling strata are decision-neutral:
discourse versus scientific-entity nodes, core discourse relations, entity-role/study
context relations, and measurement-context relations. Completeness and conditional
family/role validation are enforced against the frozen target profile.

## Reviewed-worklist compilation

Production human screening is complete. The reviewed CSV is compiled with:

```bash
python -m src.extraction.llm.publications.build_publication_pilot1_block_a \
  --reviewed-worklist var/publication_pilot1_screening/exports/publication_pilot1_screening_worklist_reviewed.csv
```

The compiler rejects missing/duplicate units, hash or metadata drift, unknown controlled
values, out-of-profile/closed/abstract targets, structurally blocked routing, and any
arm/model field. A reviewed eligible unit with no blocking or monitored routed target is
assigned `reviewed_no_eligible_target`. Deferred-resolution-only routing cannot satisfy
primary eligibility. Such units remain non-open and cannot enter calibration or the
post-Gate-0 candidate order. Only after validation does the compiler create screening JSONL, unit routing,
population coverage, the per-artifact candidate order, and the 16-unit calibration
manifest. Synthetic reviewed fixtures are used by tests; no generated semantic labels
from the real population are test truth.

Routing 0.1.2 separately records `humanScreenedNodeOperationalTargetIDs` and
`humanScreenedRelationOperationalTargetIDs` as immutable screening provenance. The
existing `eligibleNodeOperationalTargetIDs` and `eligibleRelationOperationalTargetIDs`
are the effective operational route consumed downstream. Blocking and monitored targets
pass through unchanged. A `deferred_resolution` target enters the effective route only
when the accepted source-unit record supplies at least one exact `deferredRecordRef`.
Otherwise the target remains visible in the human-screened fields and is recorded in
`structurallyUnavailableOperationalTargets` with reason
`deferred_record_binding_absent`; it contributes no prospective coverage and cannot
influence calibration or candidate ordering. This is a deterministic availability check,
not a replacement human judgment.

## Routing and interface contract

Routing means that a target is available for annotation if supported by the source. It
does not assert that the target is present, and it never infers an edge merely because
endpoint types are available. Relation catalog records preserve direction, domain/range
signatures, and deterministic-endpoint requirements. The later interface intersects the
unit route with endpoint-class compatibility, domain/range compatibility, and treatment
eligibility.

The 5–12 interface objective is a presentation goal, not a semantic cap. The compiler
never truncates a legitimate route; the interface groups longer menus by `displayGroup`.
Annotators see labels, definitions, and boundary hints, while operational/ontology IDs,
hashes, offsets, JSON, graph IDs, and validation codes remain backend metadata.

Calibration timing events and required bindings are frozen in
`publication_pilot1_gate0_policy.yaml`. The annotation MVP consumes the routing schema,
display catalog, relation signatures, the representative synthetic fixtures in
`tests/fixtures/publication_pilot1_block_a_synthetic_routing.jsonl`, and the timing-event
vocabulary. The routed fixture intentionally contains 13 node targets to prove that the
presentation objective is not a semantic truncation rule. Full interface implementation
and final context-package construction are separate workstreams.

## Arm blindness and future input packaging

Screening, routing, calibration selection, and candidate order contain no A0/A1/A2/A3,
experiment-arm, model, prompt-result, validator-result, annotation-count, gold, or timing
field. The future arm-invariant source package contains source-unit identity, canonical
text/context IDs, hashes, and structural provenance only. Routed ontology targets belong
to a detachable ontology module and therefore are not injected into ontology-off A0.
Deterministic endpoint/assertion context similarly belongs to its detachable deterministic
module. All arms later share the same primary and context source-unit IDs.

## Selection and Block-B boundary

Calibration is a deterministic greedy diversity selection over every declared prospective
dimension, including assertion/relation density, routing complexity, conversion/special
condition, recurring distinctions, context expectations, target/family/stratum coverage,
section group, length, and routing load, with lexical source-unit ID as the final tie-break. After removing
calibration, each artifact receives its own fully prospective deterministic ordering.
Gate 0 may activate a quota of five (GREEN) or four (AMBER); Block B takes the applicable
prefix without semantic or timing-based reranking. RED pauses Block B and does not invent
a smaller quota.

The accepted manifest's predeclared artifact role controls quota applicability through
machine-readable artifact quota-role policy 0.1.0:

```text
recordType != corrigendum
    artifactQuotaRole = primary_publication
    quotaBearing = true
    Block-B partitions = reliability | remaining_evaluation | reserved_diagnostic

recordType = corrigendum
    artifactQuotaRole = corrigendum_diagnostic
    quotaBearing = false
    Block-B partition = reserved_diagnostic only
```

Accordingly, the GREEN/AMBER quota applies to the eleven primary publication artifacts.
`87-corrigendum` is exempt. Its three post-calibration candidates remain in their frozen
order but cannot enter primary reliability or remaining-evaluation partitions. Block A
does not select any reserved-diagnostic IDs. Compilation fails if any quota-bearing
artifact has fewer than five post-calibration candidates, ensuring both GREEN and AMBER
remain mechanically activatable before timing is observed.

Block A does not select reliability, remaining-evaluation, or reserved-diagnostic IDs; it
does not freeze final completeness or publication quota; and it does not update the
candidate sample scaffold before reviewed screening and independent Block A review.

## Production screening and current handoff

Production human screening was completed before the quota-role amendment. The
authoritative reviewed CSV remains unchanged:

```text
var/publication_pilot1_screening/exports/publication_pilot1_screening_worklist_reviewed.csv
SHA-256: 2cba7bdb025f063b0cfbc0b05c375feee341231b34926abe43e7cd9790ce2c01
```

Quota-role amendment 0.1.3 changed only post-screening sample/quota handling. It did not
change screening semantics, the reviewed worklist, or any human decision.

Accepted checkpoint `1a6f4a306ac52fbbdff00d2d8803584e6d7de121` exposed an upstream
availability defect before calibration execution: ten human-screened units routed one or
more deferred-resolution targets, but none of the 358 accepted source-unit records had a
`deferredRecordRef`. The frozen Phase B output contains 175 descriptive deferred records
with `category`, `phaseAField`, `publicationId`, `reason`, `sourceLine`, and `value`, but
no stable `deferredRecordID`. Therefore no exact resolver binding can be established under
the frozen contracts, and no identifier is synthesized or inferred from text, proximity,
publication identity, DOI, or citation data. Stable Phase B deferred-record identity and
resolver binding remain a dedicated follow-on implementation gap.

Block A 0.1.4 filters those unavailable deferred targets structurally while preserving
their human-screened history. The reviewed CSV and screening JSONL remain byte-identical;
no unit was re-screened. No real calibration annotation, timing observation, or model
exposure occurred before this correction. The prior calibration and candidate selection
are superseded prospectively before exposure, using the same timing-blind greedy policy.
Gate 0 has not been executed, no Block-B IDs have been selected, the publication quota is
not frozen, and the final sample remains candidate and unfrozen. Current stop condition:

```text
PUBLICATION_PILOT1_BLOCK_A_DEFERRED_ROUTING_CORRECTION_READY_FOR_INDEPENDENT_REVIEW
```
