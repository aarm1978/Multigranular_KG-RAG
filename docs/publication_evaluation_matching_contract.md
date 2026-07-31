# Publication Pilot 1 Evaluation Matching Contract

> **Status:** final and binding for Publication Pilot 1 evaluation matching and decision thresholds
> **Contract version:** 0.1.0
> **Date frozen:** 2026-07-31
> **Artifact family:** scientific publications
> **Dissertation scope:** Study 2 — ontology-guided multigranular KG construction and intrinsic evaluation
> **Pilot:** Publication Pilot 1
> **Date drafted:** 2026-07-31
> **Binding ontology:** CIROH ontology 0.1.3
> **Binding target profile:** `src/extraction/llm/publications/publication_target_inventory.yaml`
> **Binding source-unit contract:** `docs/publication_source_unit_contract.md`
> **Binding candidate-output schema:** `schemas/publication_candidate_output.schema.json`
> **Binding evidence-validation contract:** `docs/publication_evidence_validation_contract.md`
> **Binding annotation guideline:** `docs/publication_annotation_adjudication_guidelines.md`
> **Dependent sample record:** `docs/publication_pilot1_sample_input_freeze.md`

## 1. Purpose

This contract defines how Publication Pilot 1 human annotations and ontology-guided LLM
outputs are compared.

It specifies:

- the evaluation populations;
- node, relation, endpoint, and evidence matching;
- one-to-one assignment;
- treatment of invalid candidates, abstentions, duplicates, and empty-gold cases;
- inter-annotator agreement;
- Precision, Recall, and F1 aggregation;
- error analysis;
- GO/REVISE/NO-GO criteria; and
- the boundary between pilot extraction evaluation and later Study 2 evaluation.

This contract does not:

- select the exact source-unit sample or execute Publication Pilot 1;
- select the model;
- define the production prompt;
- implement the source-unit builder, parser, validator, or extractor;
- perform human annotation;
- create gold data;
- evaluate global entity alignment or consolidation;
- compute final graph-level information density or relational richness;
- construct a GraphRAG baseline;
- evaluate KG-RAG retrieval or answers; or
- define Study 4 expert evaluation.

Study 3 question answering, retrieval relevance, answer quality, latency, and baseline QA
comparisons are out of scope. Study 4 expert evaluation is also out of scope. This
contract covers Study 2 extraction evaluation only and does not claim completion of the
final cross-artifact benchmark, alignment/consolidation evaluation, ontology competency
checks, final KG evaluation, or the two-metric GraphRAG comparison.

## 2. Evaluation question

Publication Pilot 1 answers:

> Can the ontology-guided Publication extraction pipeline produce usable, source-grounded
> entity and relation candidates from canonical publication text with sufficient semantic
> accuracy, evidence fidelity, and contract compliance to justify full-corpus publication
> extraction?

The pilot does not test whether the final KG improves question answering.

## 3. Authority order

Conflicts are resolved in this order:

1. frozen ontology 0.1.3;
2. frozen deterministic Publication Phase B outputs and tests;
3. final human-readable Publication Pilot 1 target inventory;
4. Publication ontology observations register;
5. LLM extraction decision record;
6. frozen machine-readable Publication target profile;
7. frozen Publication source-unit contract;
8. frozen Publication candidate-output JSON Schema;
9. frozen Publication evidence-validation contract;
10. frozen Publication annotation and adjudication guideline;
11. this evaluation-matching contract;
12. the Publication Pilot 1 sample and input freeze record;
13. model/reproducibility policy;
14. implementation and run manifests.

This contract may operationalize comparison but may not alter ontology meaning, target
eligibility, evidence authority, annotation semantics, or candidate structure.

## 4. Frozen upstream anchors

The final freeze pass must recompute and verify:

```text
Ontology OWL SHA-256:
ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57

Publication target profile SHA-256:
3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760

Publication source-unit contract SHA-256:
31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a

Publication candidate-output schema SHA-256:
affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d

Publication evidence-validation contract SHA-256:
3529484f74f9c482bd38c68c9bafbc08723e6dfd960e3c8d5faa70e1b6d28ce2

Publication annotation/adjudication guideline SHA-256:
67d693edf8e42318a763aac58190675c90b944440dc12fce164212cf9552bd60

Publication deterministic Phase B SHA-256:
675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf
```

The final sample/input record and model-policy hashes are bound later by the run manifest.

## 5. Evaluation stages

The evaluation pipeline is:

```text
raw_response
→ parsed_candidate_document
→ parsed_candidate
→ automatically_validated_candidate
→ usable_pipeline_output
→ matching against frozen gold
→ metric computation
→ human_adjudicated_candidate
→ error analysis
→ GO / REVISE / NO-GO
```

The controlled meanings are:

```text
raw_response
    Immutable provider response, whether parseable or not.

parsed_candidate_document
    A JSON-parsed document before JSON Schema and semantic validation. It may be
    schema-invalid and never enters the production candidate stream unchanged.

parsed_candidate
    One model-authored node or edge record identifiable inside a parsed document before
    candidate-level validation. A record may still be structurally or semantically invalid.

automatically_validated_candidate
    A parsed candidate with its separate deterministic validation result. `validated`
    means structurally and contract compliant, not scientifically correct.

usable_pipeline_output
    The pre-adjudication active set whose validation status is `validated`, after frozen
    exact-duplicate and stronger-role supersession. `rejected`, `needs_review`,
    `superseded`, and `deferred` records are not usable output.

human_adjudicated_candidate
    A later candidate decision or edited record. It is not model output and cannot improve
    extraction metrics.
```

Primary end-to-end extraction metrics are computed on **usable pipeline output before
human candidate adjudication**. A second, mandatory raw parsed-output view scores every
addressable parsed node and edge before automatic filtering. The raw view is diagnostic,
is reported with node and relation Precision/Recall/F1 and failure counts, and is not a
second pilot decision score. It prevents automatic validation, duplicate suppression, or
role precedence from concealing poor model behavior.

A parsed candidate is *addressable* when its record type, source artifact, operational
target (or otherwise recognizable attempted target), and evidence or endpoint references
are sufficient for deterministic error attribution. An unaddressable fragment is not
invented into a prediction; it remains a request/document/candidate diagnostic failure.
No raw-view inspection authorizes malformed content to enter usable output.

Human edits, merges, reclassifications, endpoint corrections, and evidence corrections do
not improve the model's primary score.

Candidate adjudication supports:

- final source-level inclusion decisions;
- semantic error analysis;
- adjudication-burden analysis; and
- later KG construction.

Throughout this contract, `valid` refers only to a specified structural or validation
check; `accepted` refers only to human candidate adjudication; and `correct` refers to a
match against gold or a declared correct-empty case.

## 6. Gold versions

### 6.1 Initial gold

The initial gold is:

- created independently of model outputs;
- adjudicated before model execution;
- versioned and hashed; and
- retained permanently.

### 6.2 Corrected final gold

A post-model amendment is permitted only under the frozen annotation guideline.

When amendments occur:

- the corrected final gold becomes the primary reference for final reported extraction
  metrics;
- all affected metrics are recomputed;
- the initial-gold metrics are retained as an audit and sensitivity result;
- the number and type of amendments are reported; and
- no amendment is justified solely because the model produced a plausible candidate.

If no amendment occurs, initial and corrected final gold are identical.

## 7. Evaluation populations

### 7.1 Gold-positive assertion

A gold-positive assertion is one adjudicated node or relation record that:

- is inside the frozen sample;
- belongs to an eligible operational target;
- has exact canonical evidence;
- is not excluded by treatment;
- is not a derived or inferred assertion; and
- is representable under the frozen target profile.

### 7.2 Usable-output prediction

A prediction for primary scoring is one parsed candidate that:

- belongs to the frozen sample;
- passes automatic validation as `validated`;
- belongs to an eligible operational target;
- has valid literal evidence;
- is not pipeline-generated infrastructure;
- is not a deterministic assertion presented as an LLM prediction; and
- has not been human-edited.

For usable-output scoring, every unmatched usable prediction is FP and every unmatched gold
positive is FN. If the only potentially corresponding model record was filtered,
superseded incorrectly, left in `needs_review`, deferred, or rejected, the gold positive
remains FN.

### 7.3 Raw-view prediction

For the mandatory raw parsed-output view, each addressable model-authored node or edge is
one prediction before validation or suppression. This includes exact duplicates, weaker
roles later superseded by precedence, and addressable candidates with forbidden fields,
nonliteral evidence, invalid offsets, unknown or mismatched targets, abstract classes,
domain/range errors, wrong direction, or wrong endpoints.

An unmatched addressable raw candidate is FP. A corresponding gold positive that receives
no raw true-positive match is FN. One invalid prediction can therefore cause both an FP
and an FN; the FP records what the model emitted and the FN records what it failed to emit
correctly. A request or document failure with no addressable candidate adds no invented FP,
but every eligible gold positive in its declared request coverage remains eligible to be
FN. Because matching is pooled across requests, each gold record is counted once: it is FN
only if no other prediction in the approved artifact/target pool matches it.

### 7.4 Excluded assertions

The following are excluded from primary node/relation Precision, Recall, and F1:

```text
context_only
required_infrastructure
separate_follow_on_protocol
out_of_scope
audit_only
derived superclass assertions
derived subproperty assertions
inverse relations generated by traversal
pipeline-generated reports edges
deterministic citations and corrects relations
global alignment or consolidation assertions
```

They may be reported separately when useful.

## 8. Treatment-specific evaluation

### 8.1 `extract_and_evaluate`

These targets contribute to the primary complete evaluation.

Within each routed source unit:

- all supported positives are gold;
- model predictions contribute to TP/FP;
- missed gold positives contribute to FN;
- an exhaustive zero-positive result is recorded as absence rather than abstention.

### 8.2 `extract_and_monitor`

These targets are analyzed separately.

Default reporting:

- positive-instance precision;
- positive-instance recall only where the batch declares `completenessMode: exhaustive`;
- support counts;
- error examples;
- no unqualified negative-absence interpretation.

Monitor targets do not determine GO/REVISE/NO-GO unless the final sample explicitly
promotes a monitor batch to exhaustive evaluation before annotation begins.

### 8.3 `deferred_resolution`

Deferred-resolution tasks are evaluated separately using exact deferred-record identity.

A correct resolution requires:

- the exact original deferred-record ID;
- the correct resolution type;
- the correct exact existing endpoint or permitted source-local proposal; and
- valid evidence when required.

Deferred-resolution results do not enter ordinary node/relation F1.

### 8.4 Other treatments

```text
context_only
    Available for context or exact endpoint linking; excluded from open-discovery scoring.

required_infrastructure
    Pipeline responsibility; excluded from model extraction scoring.

separate_follow_on_protocol
    Excluded from Pilot 1 primary evaluation.

out_of_scope
    Excluded.

audit_only
    Retained for history and not reopened.
```

## 9. Evaluation granularity

Primary evaluation is performed at two nested levels:

```text
assertion level
    Individual node and relation records.

artifact-clustered level
    Metrics aggregated while preserving the source artifact as the resampling and reporting
    cluster.
```

Candidates and gold records are pooled across selected source units only within the same
source artifact and operational target before one-to-one matching. Pooling across request
boundaries is preferable to request-by-request scoring because the frozen context policy
may expose the same assertion in multiple requests and a supported assertion may require
multiple canonical units. Pooling never crosses source artifacts or operational targets.

Artifact pooling does not erase occurrence identity. An eligible node pair must still
share a qualifying evidence match in the same canonical source unit (or satisfy the
declared multi-unit evidence-group rule), and must have compatible contextual identity.
An eligible relation pair must additionally have matched endpoints and relation-specific
evidence. Consequently, repeated surface forms in different units, owners, experiments,
conditions, values, or propositions cannot match merely because they occur in one paper.

This permits:

- distributed evidence;
- source-local repeated mentions;
- artifact-level duplicate detection; and
- avoidance of request-boundary artifacts.

The sample record preserves source-unit membership for every assertion.

## 10. Identity and occurrence policy

### 10.1 Source-local evaluation identity

Publication Pilot 1 does not perform global cross-source entity resolution.

Evaluation identity is bounded by:

```text
sourceArtifactID
operationalTargetID
contextual owner or role
canonical evidence
```

### 10.2 Repeated mentions

Repeated mentions are one local gold node when they represent the same semantic entity or
proposition under the same contextual owner.

They remain distinct when:

- owner differs;
- method, experiment, model, condition, or value differs;
- role differs;
- proposition differs; or
- the annotation guideline requires distinct atomic units.

### 10.3 Candidate duplicates

Extra model candidates that refer to an already matched gold assertion count as false
positives.

They are also counted in the duplicate-prediction rate.

No pre-scoring semantic merge may hide model duplication.

Exact byte-identical parser duplicates produced by the same raw response may be collapsed
only when the parser records the collapse and the duplicate count separately.

## 11. One-to-one assignment

All node and relation matching uses one-to-one bipartite assignment.

For each artifact and operational target:

1. construct all eligible gold–prediction pairs;
2. discard pairs failing mandatory class/relation, scope, endpoint, or evidence conditions;
3. score the remaining pairs;
4. select the maximum-cardinality assignment, then the maximum total match-quality weight;
5. classify matched pairs as TP;
6. classify unmatched predictions as FP; and
7. classify unmatched gold assertions as FN.

The implementation must be deterministic.

Pair weights use only the ordered criteria below; they may not use model confidence,
adjudication outcome, normalized-label similarity, or record input order. Assignment-level
ties are resolved by the lexicographically smallest sorted sequence of gold/prediction
stable-ID pairs after applying these criteria:

```text
1. exact evidence match
2. higher evidence overlap
3. exact verbatim-label match
4. smaller boundary difference
5. lexicographically smaller stable record ID
```

Stable record IDs are reproducible input identifiers. One prediction cannot satisfy more
than one gold record, one gold record cannot consume more than one prediction, and an extra
duplicate can never gain credit.

## 12. Evidence-span measures

For a predicted span `P` and gold span `G`, using zero-based half-open character offsets:

```text
intersection = max(0, min(P.end, G.end) - max(P.start, G.start))

span_precision = intersection / length(P)
span_recall    = intersection / length(G)

span_F1 = 2 * span_precision * span_recall /
          (span_precision + span_recall)
```

When both spans are empty, the record is invalid and not evaluated.

### 12.1 Exact span match

An exact span match requires:

```text
sourceArtifactID equal
sourceUnitID equal
startOffsetInUnit equal
endOffsetInUnit equal
evidenceText equal
```

### 12.2 Boundary-tolerant span match

A boundary-tolerant span match requires:

```text
same source artifact
same canonical source unit
span_F1 >= 0.80
span_precision >= 0.70
span_recall >= 0.70
```

These thresholds permit small boundary differences but reject weak topical overlap.
They are the primary evidence criterion for semantic node and relation matching. Exact
span equality is also reported as a separate strict reproducibility view; it is not the
primary semantic criterion because two annotators or a model can select slightly different
literal boundaries around the same supported proposition without changing its meaning.

The three thresholds are retained deliberately. `span_precision >= 0.70` limits a
containing prediction to at most about 1.43 times the gold length when gold is fully
covered, so paragraph- or sentence-scale over-selection cannot receive credit for a much
shorter gold phrase. `span_recall >= 0.70` prevents a narrow fragment from standing in for
most of the gold evidence. `span_F1 >= 0.80` requires balanced overlap. All are computed on
Unicode code-point offsets, not tokenized or normalized text.

### 12.3 Distributed evidence

When a gold assertion uses multiple spans because support is distributed:

- every jointly required gold evidence group must have a distinct matching predicted span
  for every member span;
- each matched pair must satisfy the boundary-tolerant criterion;
- one alternative span from each alternative group is sufficient;
- one predicted span cannot satisfy two jointly required gold spans;
- extra predicted spans remain in the evidence-set denominator; and
- unrelated or over-extended coverage therefore reduces evidence precision and is recorded
  as evidence over-extension.

The later annotation-record schema or frozen annotation manifest must encode stable
evidence groups and whether each group is `jointly_required` or `alternatives`. This
metadata belongs to gold construction; the frozen candidate-output schema already permits
the model to cite multiple ordinary evidence spans and need not be changed.

If that distinction cannot be represented before sample freeze, every attached gold span
is treated as jointly required; the sample is not eligible for distributed-evidence
scoring if that interpretation would be knowingly false.

### 12.4 Evidence-set score

For one assertion, evidence-set precision, recall, and F1 are computed over character
coverage after merging overlapping spans within each set **separately for each canonical
`sourceUnitID`**. Covered characters are coordinate keys `(sourceUnitID, offset)`; offsets
from different source units can never intersect. Counts are then micro-summed across units.
For alternative groups, use the gold alternative that gives the highest qualifying score,
with the stable evidence-span ID as the deterministic tie-break.

For a boundary-tolerant assertion match, all required groups must qualify and the complete
evidence set must also satisfy:

```text
evidence_set_F1 >= 0.80
evidence_set_precision >= 0.70
evidence_set_recall >= 0.70
```

This set-level check prevents a candidate from adding a full paragraph of irrelevant but
literal text while receiving credit from one good span.

Evidence scores are reported separately from entity/relation detection metrics.

Document offsets are validated and reported for audit, but matching uses unit offsets plus
the exact `sourceUnitID`. Exact deterministic endpoints still require exact endpoint
identity; evidence overlap cannot repair a wrong endpoint.

## 13. Node matching

A predicted node is an eligible match for a gold node only when all mandatory conditions
hold.

### 13.1 Mandatory node conditions

```text
same sourceArtifactID
same operationalTargetID
same ontology class
eligible treatment
valid candidate status
at least one required evidence match
compatible source-local contextual identity
```

A class edit is never an exact true positive.

`valid candidate status` is required only in the usable-output view. In the raw view the
same semantic conditions apply but addressable invalid candidates remain predictions and
normally become FP. Exact operational-target and class equality are mandatory for a
primary TP in both views. A superclass, sibling class, or otherwise plausible class earns
no fractional credit in primary Precision/Recall/F1; optional hierarchy-aware confusion
analysis remains separate.

A candidate adjudicated as `edited_class` remains incorrect for primary node scoring.

### 13.2 Named-entity nodes

For named entities such as Tool, Model, Algorithm, Dataset, Repository, Metric, Parameter,
Variable, Concept, and geographic entities:

- evidence overlap is the primary mention anchor;
- normalized labels do not establish a match;
- name similarity alone does not establish a match;
- exact deterministic linking is evaluated separately;
- same-named contextual occurrences may remain distinct.

`link_existing` and `propose_new` are not interchangeable when gold requires an exact
deterministic endpoint. For source-local gold, `propose_new` is appropriate; for a frozen
exact endpoint, only the exact permitted `link_existing` identity can match.

### 13.3 Discourse nodes

For discourse nodes such as ResearchProblem, ResearchGoal, Method, Finding, Limitation,
and Conclusion:

- class must match exactly;
- the proposition must be atomic under the guideline;
- evidence must satisfy the span criterion;
- a broad paragraph that merely contains the gold proposition is not sufficient when it
  fails the evidence-overlap thresholds;
- splitting or merging errors are handled under Section 17.

### 13.4 Node match quality labels

Every matched node receives one of:

```text
exact
boundary_tolerant
```

Unmatched but semantically related records are not partial true positives. They remain FP
and FN with an error category.

## 14. Existing-link versus new-node behavior

The candidate schema distinguishes:

```text
link_existing
propose_new
```

### 14.1 Correct `link_existing`

A correct existing link requires:

- exact permitted deterministic endpoint identity;
- compatible class;
- source-grounded mention or use evidence;
- no name-only resolution.

### 14.2 Incorrect `link_existing`

A wrong exact endpoint is:

- a false-positive predicted node/link;
- a false negative for the correct gold endpoint or source-local proposal; and
- an `wrong_endpoint` error.

### 14.3 Correct `propose_new`

A new proposal is correct when the gold represents a source-local node and the prediction
satisfies node matching.

A model is not penalized for failing to produce a global canonical identity that is outside
Pilot 1 scope.

## 15. Relation matching

A predicted relation is an eligible match for a gold relation only when all mandatory
conditions hold.

### 15.1 Mandatory relation conditions

```text
same sourceArtifactID
same operationalTargetID
same ontology relation
same operational direction
source endpoint matched to the gold source endpoint
target endpoint matched to the gold target endpoint
valid relation-specific evidence
eligible treatment
```

As with nodes, automatic-validation status is an additional usable-output condition, not a
raw-view escape hatch. A wrong but recognizable relation, direction, endpoint, or
domain/range attempt remains an FP in the raw view and leaves the unmatched correct gold
edge as FN. A structurally valid wrong semantic prediction remains FP/FN in both views.

### 15.2 Endpoint matching

An endpoint is matched when it is:

- the same matched gold/predicted local node pair; or
- the same exact deterministic endpoint ID permitted by the sample manifest.

Raw endpoint labels cannot substitute for endpoint identity.

For source-local provisional endpoints, equality is established only through the matched
local node pair and its contextual identity. For deterministic endpoints, exact frozen ID
equality is required. Endpoint matching is performed after node assignment, so an edge
cannot repair or bypass a node error.

### 15.3 Direction

Reversed direction is always incorrect.

For example:

```text
Method / Contribution / ResearchQuestion -> resolves -> ResearchProblem
```

An edge placing `ResearchProblem` in the source position and a resolving discourse unit in
the target position cannot match.

This direction is derived from operational target
`PUB-R-C-P06-RESOLVES` in the frozen YAML profile, whose domain is
`Method / Contribution / ResearchQuestion` and range is `ResearchProblem`.

### 15.4 Relation evidence

Node evidence does not automatically support the edge.

The predicted edge must include evidence that supports the relation semantics and satisfies
the evidence criterion.

For a relation supported across units, its own evidence groups must satisfy Section 12;
the union of endpoint-node evidence cannot be substituted for edge evidence.

### 15.5 Relation match quality

Every matched relation receives:

```text
exact
boundary_tolerant
```

A relation requiring `edited_relation`, `edited_endpoint`, `edited_evidence`, or
`edited_direction` during adjudication is not a true positive in primary scoring.

## 16. Stronger and weaker relations

The frozen relation-precedence rules apply.

Examples:

```text
usesModel supersedes mentionsModel
usesTool supersedes mentionsTool
usesDataset supersedes mentionsDataset
hasCodeRepository supersedes referencesRepository
```

When gold contains the stronger relation and the model predicts only the weaker relation:

- the weaker prediction is FP;
- the stronger gold relation is FN;
- the case is labeled `weaker_relation`.

When gold contains only the weaker relation and the model predicts an unsupported stronger
relation:

- the stronger prediction is FP;
- the weaker gold relation is FN;
- the case is labeled `unsupported_stronger_relation`.

No semantic partial credit is added to primary F1.

A separate relation-confusion matrix records these near misses.

## 17. Atomicity, split, and merge errors

### 17.1 Over-merged prediction

One predicted node that combines multiple gold nodes:

- may match at most one gold node;
- unmatched gold nodes are FN;
- the prediction receives `invalid_atomicity`;
- no fractional TP is awarded.

### 17.2 Over-split prediction

Multiple predicted nodes corresponding to one gold node:

- one prediction may match the gold;
- extra predictions are FP;
- extra predictions contribute to duplicate or atomicity error rates.

### 17.3 Gold correction

If adjudication determines that the gold itself was incorrectly split or merged, the
controlled amendment process applies before final metrics are reported.

## 18. Invalid and non-validated model output

Automatic filtering affects only the usable-output view. It never deletes the immutable
raw response, parsed document, parsed records, or failure attribution used by the raw view.

| Case | Usable-output treatment | Raw-view semantic consequence | Required diagnostic or safety consequence |
| --- | --- | --- | --- |
| request parse failure | no output from the request | no invented FP; after pooled matching, each otherwise-unmatched gold positive covered by the failed request is FN exactly once | request failure with processing code; denominator is attempted requests |
| candidate-document schema failure | no candidate from that document is usable | each addressable attempted record is scored; otherwise gold positives remain FN without an invented FP | failed documents / parsed candidate documents |
| candidate-level schema failure | because the frozen JSON Schema governs the complete envelope, the document fails schema validation and no record from it is usable | addressable failing record is FP; corresponding unmatched gold remains FN | failing parsed candidates / parsed candidates, nested under the document schema failure |
| forbidden field | candidate is rejected | addressable attempted assertion is FP; associated unmatched gold is FN | forbidden-field candidates / parsed candidates; any leak into usable output is blocking |
| nonliteral evidence | candidate is rejected | addressable attempted assertion is FP and cannot be TP; associated gold is FN | nonliteral-evidence candidates / parsed candidates |
| invalid evidence offsets | candidate is rejected | addressable attempted assertion is FP and cannot be TP; associated gold is FN | offset-invalid candidates / parsed candidates |
| unknown ontology ID | candidate is rejected | addressable attempted assertion is FP; associated gold is FN | unknown-ID candidates / parsed candidates |
| unknown operational target | candidate is rejected | addressable attempted assertion is FP when its attempted type can be attributed; associated gold is FN | unknown-target candidates / parsed candidates |
| invalid domain or range | edge is rejected | attempted edge is FP; correctly directed gold edge with correct endpoints remains FN | domain-invalid and range-invalid edges / parsed edges |
| abstract-class instantiation | node is rejected | attempted node is FP; correct concrete gold node remains FN | abstract-class candidates / parsed nodes |
| wrong class that is otherwise a valid target | may validate structurally | FP plus FN under exact-class matching | semantic `wrong_class`, not a generic validator failure |
| wrong relation that is otherwise a valid target | may validate structurally | FP plus FN under exact-relation matching | semantic `wrong_relation` |
| wrong relation direction | rejected when operational domain/range exposes it; otherwise remains structurally valid but wrong | FP plus FN | semantic `wrong_direction`; systematic recurrence is blocking |
| wrong endpoint | rejected if unresolved/incompatible; otherwise may validate structurally | FP plus FN | semantic `wrong_endpoint` |
| exact duplicate prediction | extra record is `superseded` and not usable | first eligible record may match; every extra model-authored duplicate is FP | duplicate raw predictions / parsed candidates |
| weaker-role prediction superseded by a stronger role | superseded weaker record is not usable | weaker raw prediction is still scored and is FP when gold requires only the stronger role | precedence-suppression count and relation-confusion category |

The frozen parser prohibition on salvaging malformed JSON remains binding. Diagnostic
inspection of an addressable record inside a JSON-parsed but schema-invalid document does
not repair, canonicalize, or admit that record to the pipeline.

Every rate reports its numerator, denominator, and absolute count. Candidate rates use all
parsed candidates of the applicable record type, including superseded and invalid records;
document rates use JSON-parsed candidate documents; request rates use all attempted
requests. When a denominator is zero, the rate is `undefined`.

Report both views side by side:

```text
primary end-to-end usable-output view
    usable pipeline output versus gold; determines extraction quality thresholds

mandatory raw parsed-output diagnostic view
    addressable pre-validation predictions versus gold plus all processing and validation
    failure rates; determines contract-compliance thresholds and error attribution
```

This division aligns the proposal's extraction-accuracy commitment with the actual
production boundary: rejected candidates do not pretend to enter the KG, while their raw
errors remain visible and can block GO through the compliance gates in Section 29.

## 19. Abstention and no-output behavior

An `abstention` is an explicit, schema-conforming semantic record with an authorized
reason. It is distinct from a request parse failure, an empty parsed document, a document
whose candidates are all rejected, and an exhaustive gold absence. `No parsed output` is
a processing failure. `No validated output` may result from an empty candidate document,
appropriate abstention, or complete filtering and is reported by cause.

### 19.1 Gold-positive case

When gold contains an eligible positive and the model abstains or emits no validated
candidate:

```text
FN += 1
```

The abstention may still be judged appropriate in a separate uncertainty analysis, but it
does not recover recall.

An abstention is `incorrect` when eligible gold contains a supported assertion the model
should have emitted. It may be `appropriate` only when the frozen target/evidence rules
make non-assertion defensible; appropriateness is descriptive and does not create a TP.

### 19.2 Exhaustive empty-gold case

When an `extract_and_evaluate` target is routed exhaustively and gold contains no positive:

- no prediction or an explicit appropriate abstention is recorded as `correct_empty`;
- an unsupported prediction is FP;
- `correct_empty` is not a true negative in Precision/Recall/F1;
- correct-empty accuracy is reported separately.

### 19.3 Monitor target

For a non-exhaustive monitor target:

- absence of gold is not treated as a confirmed negative;
- no-output behavior is descriptive only;
- unsupported predictions found during adjudication count against monitor precision.

### 19.4 Abstention reasons

Report abstentions by:

```text
insufficient_evidence
ambiguous_class
ambiguous_relation
unresolved_endpoint
invalid_domain_range
target_outside_ontology
incomplete_source_text
unrecoverable_table_structure
visual_only_evidence
equation_only_evidence
unresolved_cross_reference
```

Hallucinated or non-contract abstention reasons are validation errors.

Report abstention counts and adjudicated appropriateness by reason, target, and artifact.
No additional abstention-quality scalar is required for Pilot 1: a single rate would mix
gold-positive caution, exhaustive absence, and non-exhaustive monitor cases. Extraction
recall and correct-empty reporting already capture the decision-relevant consequences.

## 20. Precision, Recall, and F1

For nodes and relations separately:

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
```

When a denominator is zero:

- the metric is `undefined`;
- it is not silently set to zero or one;
- the support count and reason are reported.

## 21. Aggregation

### 21.1 Primary aggregate metrics

Report:

```text
node micro Precision / Recall / F1
relation micro Precision / Recall / F1
```

over all primary `extract_and_evaluate` targets.

Report these separately for the usable-output and raw parsed-output views. Only the
usable-output view is the primary quality score; raw metrics are mandatory diagnostics.

### 21.2 Macro metrics

Report unweighted macro averages across operational targets with at least one gold positive
in the frozen sample.

Also report:

```text
number of included targets
number of zero-support targets
gold support per target
prediction support per target
```

Do not report a macro average without its support distribution.

Restricting the numeric macro mean to targets with at least one gold positive avoids
undefined recall and artificial target scores. It does not make unobserved targets
disappear: list every zero-gold target, its prediction count, treatment, and `unobserved`
status. A zero-gold target with predictions has undefined recall but its predictions still
contribute FP to micro precision and are disclosed separately.

### 21.3 Target-family metrics

Report grouped results for:

```text
research framing
discourse structure
methods and experiments
models, algorithms, and tools
findings, conclusions, limitations, and future work
metrics, parameters, and variables
datasets and repositories
concepts and geography
discourse relations
use/mention/reference relations
```

### 21.4 Artifact-clustered uncertainty

When at least five source artifacts contribute primary gold or predictions, compute 95%
bootstrap confidence intervals by resampling source artifacts, not individual assertions.
With fewer than five contributing artifacts, label intervals `INSUFFICIENT_SUPPORT` and
report the exact artifact-level results instead.

Use a fixed random seed recorded in the evaluation manifest.

Confidence intervals are descriptive and do not replace the frozen decision thresholds.
They are useful for exposing instability in the planned small clustered sample, but are
not inferential proof of general-corpus performance.

## 22. Evidence metrics

Report separately for matched nodes and matched relations:

```text
exact evidence match rate
boundary-tolerant evidence match rate
mean character-level evidence precision
mean character-level evidence recall
mean character-level evidence F1
evidence over-extension rate
missing-joint-span rate
```

A semantically correct class/relation with invalid evidence is not a primary TP because it
cannot pass automatic validation.

In the raw view it is an evidence-invalid FP and the unmatched gold assertion is FN.
Evidence metrics are never computed only after dropping failed evidence attempts: report
the matched-span scores together with missing-evidence, invalid-evidence, over-extension,
and missing-joint-span counts.

## 23. Contract-compliance metrics

Report:

```text
request parse success rate
candidate-document schema-valid rate
candidate-level schema-valid rate
candidate-level evidence-valid rate
candidate-level ontology-valid rate
candidate-level target-eligible rate
candidate-level domain/range-valid rate
forbidden-field rate
abstract-class-instantiation rate
duplicate-prediction rate
usable-output invalid-leakage rate
```

Rates must identify their denominator.

For example:

```text
request parse success rate
    successful parsed responses / attempted requests

candidate-document schema-valid rate
    schema-valid candidate documents / JSON-parsed candidate documents

candidate-level schema-valid rate
    schema-valid candidate records / parsed candidate records

candidate-level evidence-valid rate
    evidence-valid candidates / parsed candidates

candidate-level ontology-valid rate
    ontology-ID-compatible candidates / parsed candidates

candidate-level target-eligible rate
    eligible-target candidates / parsed candidates

candidate-level domain/range-valid rate
    domain-and-range-valid candidate edges / parsed candidate edges

duplicate-prediction rate
    extra model-authored exact duplicate candidates / parsed candidates

usable-output invalid-leakage rate
    structurally contract-invalid records present in usable pipeline output /
    usable pipeline output records
```

Rates are computed before candidate adjudication. A zero parsed-candidate denominator is
`undefined`, not perfect compliance.

## 24. Deferred-resolution metrics

Report:

```text
exact deferred-record resolution accuracy
wrong-endpoint count
unresolved count
unsupported-resolution count
```

A deferred item remaining unresolved is not automatically an error when the model
appropriately abstains and the evidence is insufficient.

The denominator distinguishes:

```text
gold_resolvable
gold_unresolvable
```

## 25. Inter-annotator agreement

IAA is computed before gold adjudication on the frozen reliability subset.

The independent expert second review used for remaining evaluation units is quality
control, not IAA, because it is performed against an existing primary annotation rather
than as a blind duplicate annotation.

### 25.1 Primary IAA

Use deterministic one-to-one assignment and the same artifact, occurrence-identity, and
evidence-overlap rules as model evaluation, with one important non-tautological change:
IAA *detection pairing* pools eligible node targets within the same artifact and ignores
operational target and class when pairing nodes. It pools eligible relation targets within
the same artifact and ignores operational relation target, relation type, and direction
when pairing edges. Otherwise, class, relation-type, and direction agreement would be 1.00
by construction and could not measure annotation disagreement.

Node detection pairs require compatible atomic proposition or contextual identity plus
qualifying evidence. Edge detection pairs require qualifying relation-specific evidence
for the same atomic relational proposition; class, relation type, direction, and both
endpoint selections are ignored only while constructing the IAA pairing and are then
compared as classification fields. Evidence overlap alone cannot pair two distinct edge
propositions in a sentence. When multiple edge propositions share qualifying evidence,
assignment weight prefers greater unordered endpoint-occurrence overlap, then applies the
stable-ID tie-break; endpoint equality is not an eligibility condition. Unpaired records
contribute to pairwise detection FP/FN. This IAA-only pairing does not weaken exact
class/relation matching for model TP.

Report both annotator directions and the symmetric pairwise F1:

```text
node agreement Precision / Recall / F1
relation agreement Precision / Recall / F1
evidence-span F1
```

For two annotators, precision with A as reference equals recall with B as reference, while
F1 is identical in both directions. Do not describe directional Precision or Recall as
symmetric; report both supports and both directional values.

### 25.2 Classification agreement on matched assertions

For evidence-matched annotation pairs, report:

```text
node-class agreement
relation-type agreement
relation-direction agreement
endpoint agreement
```

Report the numerator and denominator for each. Relation-direction agreement is evaluated
on paired edges for which both annotators selected the same relation type; endpoint
agreement reports source endpoint, target endpoint, and both-endpoints-correct agreement.
Relation-type disagreements remain visible rather than being discarded before pairing.

### 25.3 Unit-target presence agreement

For each routed `extract_and_evaluate` target, report unit-level positive/absent agreement.

Cohen's kappa may be reported when both positive and negative cases occur, but it is
secondary because sparse targets can make kappa unstable.

Always report the raw 2×2 table and observed agreement.

Kappa is `INSUFFICIENT_SUPPORT` when either annotator has no variation in the binary
presence decision or when fewer than 20 unit-target decisions are available. It is never
computed on adjudicated gold.

### 25.4 IAA acceptance gate

Before model scoring is treated as interpretable, the reliability subset should meet the
following calibration gates when their support conditions are satisfied:

```text
node pairwise F1 >= 0.80
    support: at least 20 node records from each annotator

relation pairwise F1 >= 0.70
    support: at least 10 relation records from each annotator

node-class agreement on detection-paired nodes >= 0.85
    support: at least 20 paired nodes

relation-direction agreement on same-type paired edges >= 0.95
    support: at least 20 paired edges

evidence-span F1 >= 0.80
    support: at least 20 detection-paired assertions, including relation pairs when present
```

The retained floors are calibration targets rather than claims of universal reliability.
Node F1 0.80 and evidence F1 0.80 require solid reproducibility; relation F1 0.70 allows
the greater sparsity and dependency on endpoint annotation in a first pilot; class 0.85
and direction 0.95 reflect that classification and direction should be more reproducible
once an occurrence has been independently detected. Direction is not a hard gate below
20 paired edges because one error would otherwise create a discontinuous sparse-sample
failure. Relation-type and endpoint agreement remain mandatory reported diagnostics but
receive no independent numeric gate until Pilot 1 provides a defensible empirical support
distribution.

If a threshold is missed:

- do not change the gold silently;
- inspect disagreement categories;
- revise handbook examples or boundary guidance if appropriate;
- recalibrate;
- re-annotate only the affected reliability material under a new annotation-batch version.

Low IAA caused by too little target support is classified as `INSUFFICIENT_SUPPORT`, not
automatic methodological failure.

`INSUFFICIENT_SUPPORT` is assigned metric by metric when its stated denominator is below
the support minimum. It is neither a pass nor a fail, cannot be averaged as a numeric
value, and requires the report to give raw counts and disagreement categories. If a
blocking IAA metric has sufficient support and misses its floor, model scoring is not yet
interpretable and the outcome is `REVISE` before model changes are considered. Insufficient
support for a target-specific classification analysis is non-blocking and prohibits only
that target-specific reliability claim. Insufficient support for the overall node or
relation pairwise IAA gate does not become a failure score, but the corresponding overall
extraction result cannot support `GO`; the initial outcome is `REVISE`, followed by
`NO_GO` or a formally narrowed, newly versioned target scope if the single controlled
cycle cannot establish interpretable reliability without changing frozen evaluation units.

## 26. Candidate-adjudication analysis

Candidate adjudication occurs after primary metrics.

Report:

```text
accepted_as_proposed_rate
accepted_with_edit_rate
rejected_rate
deferred_rate
superseded_rate
excluded_rate
```

Break edits down by:

```text
edited_label
edited_class
edited_relation
edited_endpoint
edited_evidence
linked_existing
merged_local_duplicate
split_candidate
```

Primary model F1 uses pre-adjudication usable pipeline output. No accepted, edited, linked,
merged, split, or otherwise human-adjudicated record replaces the original model record in
primary extraction metrics.

Adjudication outcomes quantify human correction burden and support final KG inclusion.

## 27. Error taxonomy

Every FP, FN, and non-exact adjudication outcome receives one primary error category:

```text
missed_positive
unsupported_positive
wrong_class
wrong_relation
wrong_direction
wrong_endpoint
span_boundary
missing_joint_evidence
evidence_over_extension
invalid_atomicity
duplicate_prediction
weaker_relation
unsupported_stronger_relation
use_mention_reference
model_method_algorithm_tool
metric_parameter_context
local_identity
scope_or_eligibility
source_conversion
parse_or_schema_failure
ontology_or_domain_range_failure
other_documented
```

Secondary tags may be added, but the primary category is mandatory.

Report:

- frequency;
- percentage;
- affected targets;
- affected artifacts;
- representative evidence-grounded examples;
- whether the error is systematic or isolated; and
- whether it is addressable in the single controlled revision cycle.

## 28. Fact-recoverability pilot measure

Fact recoverability is exploratory in Publication Pilot 1 and is not a GO-blocking metric.

The pilot may evaluate publication-internal chains such as:

```text
ResearchProblem <- resolves - Method -> produces -> Finding
Method / Experiment -> produces -> Finding
Paper -> usesDataset -> Dataset
Paper -> hasCodeRepository -> Repository
```

A chain is recoverable only when:

- all required nodes are present;
- all required directed relations are present;
- endpoints match;
- every assertion has valid evidence; and
- no generative inference is needed to fill a missing step.

Report:

```text
recoverable chains / gold chains
```

Cross-source lineage and code-documentation chains remain later Study 2 evaluation tasks.

## 29. Primary pilot decision thresholds

These thresholds are preregistered engineering-quality gates for scaling publication
extraction, not statistically estimated universal constants. They protect usable KG quality
while allowing one controlled correction cycle. Every threshold report includes the metric
view, numerator, denominator, support category, initial/revised run applicability, and
whether it is a safety, quality, or support gate.

Extraction-quality thresholds apply to the primary usable-output view after an
interpretable IAA gate and on corrected final gold, with initial-gold sensitivity retained.
Raw contract-compliance thresholds apply to the immutable initial and revised model output
separately. No run may combine provider/model versions.

Rates are computed from integer counts without rounding. The GO floors apply at every
nonzero denominator. The raw-validity `NO_GO` floors below apply directly only when the
applicable candidate denominator is at least 20; with 1–19 candidates, missing GO is
`REVISE` unless the failure is systematic under the cross-artifact and rate rule or
violates a zero-tolerance safety gate. Request-level parse floors apply regardless of
request count because every attempted request is an operational unit and its exact count
is reported.

### 29.1 GO

Classify `GO` when all blocking conditions hold:

```text
request parse success rate >= 0.98
candidate-document schema-valid rate >= 0.95
candidate-level schema-valid rate >= 0.95
candidate-level evidence-valid rate >= 0.95
candidate-level ontology-valid rate >= 0.95
candidate-level target-eligible rate >= 0.95
candidate-level domain/range-valid rate >= 0.95
forbidden-field rate == 0.00
usable-output invalid-leakage rate == 0.00

node micro Precision >= 0.80
node micro Recall >= 0.75
node micro F1 >= 0.78

relation micro Precision >= 0.75
relation micro Recall >= 0.65
relation micro F1 >= 0.70

matched-node evidence-span F1 >= 0.85
matched-relation evidence-span F1 >= 0.85

duplicate-prediction rate <= 0.05
```

The 0.98 request-parse gate is retained because structured output is an operational
precondition for scaling, while the 0.95 raw document/candidate compliance gates allow an
isolated caught failure without pretending that filtered output was flawless. The former
tautological requirements that already-validated candidates be 100% valid are removed.
The only 1.00-equivalent safety gates are zero forbidden model behavior and zero
structurally invalid leakage into usable output. A nonliteral or offset-invalid raw
candidate is never usable; systematic evidence-invalid raw output is governed by the 0.95
evidence-valid gate and the safety rules below.

The node and relation Precision/Recall/F1 floors are retained as pragmatic scale-up floors:
Precision is set higher than Recall to limit unsupported KG assertions, while independent
Recall and F1 floors prevent a conservative system from passing through abstention. The
node and relation evidence gates are both revised to 0.85 because 0.80 would be guaranteed
by the per-match eligibility rule and therefore tautological. Each is the arithmetic mean
of assertion-level evidence-set F1 across usable-output TPs of that record type; support is
the number of matched assertions. The revised means exceed the 0.80 eligibility floor so a
system that barely clears every boundary match does not pass on evidence fidelity alone.
These thresholds apply to
both the initial and revised run; the revised run does not receive relaxed gates.

Additionally:

- no supported target family with at least ten gold instances has F1 below 0.50;
- no systematic reversed-direction failure exists;
- no systematic abstract-class instantiation exists;
- no systematic raw nonliteral-evidence, invalid-offset, unknown-target, or
  invalid-domain/range failure exists;
- no forbidden-field behavior exists;
- no unresolved evidence-authority contradiction exists;
- no model-output leakage affected sample selection or gold creation; and
- remaining errors are operationally correctable during full-corpus execution without
  changing frozen ontology semantics.

For an ordinary non-zero-tolerance raw failure, `systematic` means that the same failure
category has **at least two instances across at least two source artifacts** **and** those
instances constitute **more than 5% of the applicable raw denominator**. Both conditions
are required. An ordinary failure rate of exactly 5% is therefore not automatically
systematic, and 19 valid cases out of 20 remain consistent with a numeric validity gate of
at least 0.95. Numeric raw-compliance gates still apply independently: a non-systematic
failure can miss a numeric GO floor, and a systematic failure can block GO even when a
rounded display would obscure the underlying integer rate.

The following are separate zero-tolerance safety failures and block GO regardless of
count: any forbidden-field behavior, any structurally invalid record leaking into usable
output, and any model-output leakage into sample selection or gold construction. They do
not use the ordinary `systematic` frequency test. Repeated reversed-direction,
abstract-class, evidence-authority, or other semantic failures may also block GO when a
rule in this contract identifies them as a safety failure or methodological contradiction;
the ordinary frequency definition does not override those explicit protections.

### 29.2 GO with non-blocking notes

A report may say **GO with non-blocking notes** when all GO thresholds are met but:

- one or more monitor targets have sparse support;
- confidence intervals are wide because of sample size;
- fact recoverability remains underpowered;
- a non-blocking prompt or handbook clarification is recommended; or
- source-conversion limitations affect a predeclared small subset.

This classification still advances to full publication extraction.

The formal decision remains `GO`; this wording is not a fourth decision state.

### 29.3 REVISE

Classify `REVISE` when the approach appears viable but one controlled correction cycle is
needed.

Typical quantitative region:

```text
node micro F1 >= 0.65 and < 0.78
or
relation micro F1 >= 0.50 and < 0.70
or
request parse success rate >= 0.90 and < 0.98
or
any raw schema/evidence/ontology/target/domain-range validity rate is >= 0.85 and < 0.95
or
duplicate-prediction rate > 0.05 and <= 0.15
```

Also use `REVISE` for a bounded systematic problem in:

- prompt wording;
- target routing;
- request context;
- parser normalization;
- validator implementation;
- handbook example; or
- one operational boundary that does not require ontology redesign.

Only one controlled revision cycle is permitted for the same pilot decision.

The revised run:

- receives a new prompt or implementation version;
- reuses the frozen primary evaluation set;
- may use the reserved diagnostic set during debugging;
- reports both original and revised results; and
- does not alter gold to improve performance.

Permitted bounded revisions include prompt wording, request-context selection within the
frozen source-unit contract, target routing that stays within the frozen profile, parser or
validator implementation corrections, and handbook examples or interface guidance that do
not change annotation semantics. The ontology, target universe, source units, evaluation
partitions, initial gold, matching rules, and thresholds remain frozen. A provider/model
version change is not mixed into the revision; it creates a separately versioned run and
requires re-execution of every affected request. Diagnostic units may guide debugging but
never enter primary metrics.

On the initial run, any failure to meet all GO conditions that does not meet a `NO_GO`
condition is `REVISE`; the illustrative quantitative region is not an exhaustive loophole.
After the single revised run, the only formal outcomes are `GO` or `NO_GO` (including a
formally approved narrowed automated target scope followed by a newly versioned decision).

### 29.4 NO_GO

Classify `NO_GO` when:

- node micro F1 is below 0.65;
- relation micro F1 is below 0.50;
- request parse success is below 0.90;
- any raw schema/evidence/ontology/target/domain-range validity rate is below 0.85;
- any forbidden-field behavior occurs;
- any structurally invalid record enters usable pipeline output;
- evidence-invalid output remains systematic;
- model-output leakage affects sample selection or gold construction;
- a core target family is operationally unextractable under the frozen approach;
- the method requires prohibited external knowledge;
- one controlled revision cycle fails to satisfy every GO gate; or
- a frozen methodological contradiction makes the pilot result uninterpretable.

`NO_GO` does not require abandoning Study 2.

Permitted responses include:

- narrowing the automated LLM target set;
- moving selected targets to manual or monitor-only treatment;
- retaining deterministic-only coverage for some semantics; or
- documenting a justified limitation.

Any ontology or target-profile change follows formal versioning and renewed validation.

The formal decision vocabulary is exactly:

```text
GO
REVISE
NO_GO
```

Undefined or `INSUFFICIENT_SUPPORT` metrics are never silently treated as passes. A
missing IAA support condition is handled under Section 25; a missing extraction target
support condition is disclosed under Section 30 and does not fabricate a target-specific
decision.

## 30. Threshold support rule

A target-specific threshold is interpreted only when the target has sufficient gold support.

Default support categories:

```text
0 instances
    unobserved

1–4 instances
    descriptive only

5–9 instances
    limited support

10 or more instances
    eligible for target-specific blocking interpretation
```

Overall micro metrics remain valid over the complete primary sample.

The sample/input freeze must attempt to provide at least ten gold instances for each
target family designated as blocking, not necessarily every individual target.

Ten is retained as the minimum blocking family support, not as a claim of precise
target-level estimation. Below ten, family F1 is descriptive and cannot trigger the 0.50
family floor. At ten or more, the floor is a coarse catastrophic-failure screen and must be
reported with its artifact distribution and confidence interval. Individual-target metrics
remain descriptive unless they independently reach ten gold positives; one weak supported
family cannot be hidden by micro averaging.

The sample freeze must also reserve enough reliability material to attempt the Section 25
support conditions and enough attempted requests/candidates to report every compliance
denominator. If the fixed artifact pool cannot supply a requested target-family support
without inventing a sample size, cherry-picking units, or leaking model output, record the
family as `INSUFFICIENT_SUPPORT`; do not broaden the target or add artifacts silently.

## 31. Model comparison and version changes

Publication Pilot 1 is not a multi-model leaderboard.

The pilot uses one frozen model configuration.

If a model version changes during comparable execution:

- pause the run;
- document the provider/model change;
- assign a new run and policy version;
- do not combine results across versions;
- rerun all affected evaluation requests; and
- report the change.

Exploratory model comparisons, when any, use diagnostic material and do not replace the
frozen primary run.

## 32. Reproducibility manifest

The evaluation manifest records:

```text
evaluationContractVersion
evaluationContractHash
goldVersion
goldHash
sampleFreezeVersion
sampleFreezeHash
targetProfileVersion
targetProfileHash
sourceUnitContractVersion
sourceUnitContractHash
candidateSchemaVersion
candidateSchemaHash
evidenceContractVersion
evidenceContractHash
annotationGuidelineVersion
annotationGuidelineHash
modelPolicyVersion
modelPolicyHash
promptVersion
promptHash
runIDs
inputManifestHash
validatedCandidateManifestHash
matchingImplementationVersion
matchingImplementationHash
randomSeed
evaluationTimestamp
softwareEnvironment
```

## 33. Required evaluation outputs

Recommended outputs:

```text
results/evaluation/publications/pilot1/
    publication_pilot1_evaluation_manifest.json
    publication_pilot1_request_diagnostics.csv
    publication_pilot1_node_matches.jsonl
    publication_pilot1_relation_matches.jsonl
    publication_pilot1_node_metrics.json
    publication_pilot1_relation_metrics.json
    publication_pilot1_evidence_metrics.json
    publication_pilot1_iaa_metrics.json
    publication_pilot1_deferred_resolution_metrics.json
    publication_pilot1_candidate_adjudication_metrics.json
    publication_pilot1_error_analysis.csv
    publication_pilot1_fact_recoverability.json
    publication_pilot1_decision.md
```

Exact filenames may change, but logical separation is required.

## 34. Reporting requirements

The pilot report must include:

- sample composition;
- artifact and section coverage;
- target support distribution;
- annotation and adjudication counts;
- IAA;
- raw-output diagnostic rates;
- node micro and macro metrics;
- relation micro and macro metrics;
- target-family metrics;
- evidence metrics;
- abstention and correct-empty behavior;
- duplicate rate;
- deferred-resolution results;
- candidate-adjudication burden;
- error taxonomy;
- initial versus corrected-gold sensitivity, when applicable;
- fact-recoverability exploratory result;
- original and revised-run results, when applicable;
- GO/REVISE/NO-GO classification;
- remaining limitations; and
- exact reproducibility hashes.

## 35. Prohibited evaluation practices

Do not:

- inspect model output before freezing gold;
- select source units because the model performs well on them;
- alter gold silently after model exposure;
- use normalized labels as evidence;
- match by name similarity alone;
- reverse relations for linguistic convenience;
- award fractional TP in primary P/R/F1;
- count monitor-target absence as a negative without exhaustive coverage;
- count correct-empty cases as true negatives in extraction F1;
- use candidate adjudication edits to improve primary model metrics;
- hide invalid raw outputs behind the validator;
- collapse semantic duplicates before scoring;
- compare final Study 2 QA performance;
- compare information density or relational richness during this pilot; or
- claim GraphRAG superiority/inferiority from Publication Pilot 1 extraction metrics.

## 36. Contract-review checklist

This contract was frozen after:

- [x] evaluation populations are approved;
- [x] gold-version policy is approved;
- [x] treatment-specific evaluation is approved;
- [x] artifact-level pooling is approved;
- [x] one-to-one matching is approved;
- [x] evidence-overlap formulas and thresholds are approved;
- [x] node matching is approved;
- [x] relation and endpoint matching are approved;
- [x] atomicity and duplicate handling are approved;
- [x] invalid-output treatment is approved;
- [x] abstention and empty-gold treatment are approved;
- [x] micro and macro aggregation are approved;
- [x] IAA measures and thresholds are approved;
- [x] candidate-adjudication analysis is approved;
- [x] fact recoverability remains exploratory;
- [x] GO/REVISE/NO-GO thresholds are approved;
- [x] target-support rules are approved;
- [x] required outputs and manifest fields are approved;
- [x] no Study 3 or Study 4 evaluation has been introduced;
- [x] focused static tests pass; and
- [x] no unresolved contradiction with a frozen upstream contract remains.

## 37. Acceptance statement

The contract-review checklist has passed. This document is final and binding and governs
Publication Pilot 1 matching, metric aggregation, IAA, invalid-output treatment, and
GO/REVISE/NO_GO thresholds.

The downstream `publication_pilot1_sample_input_freeze.md` record remains a candidate and
cannot be completed until exact source units, partitions, routing, and hashes exist.
