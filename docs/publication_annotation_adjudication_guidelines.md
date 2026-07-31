# Publication Annotation and Adjudication Guidelines — Publication Pilot 1

> **Status:** final and binding for Publication Pilot 1 Study 2 annotation and adjudication
> **Guideline version:** 0.1.1
> **Artifact family:** scientific publications
> **Dissertation scope:** Study 2 — multigranular KG construction and intrinsic evaluation
> **Source scope:** selected Publication Pilot 1 source units
> **Stage scope:** human gold annotation, disagreement resolution, and post-validation candidate adjudication
> **Frozen ontology:** CIROH ontology 0.1.3
> **Binding target profile:** `src/extraction/llm/publications/publication_target_inventory.yaml`
> **Binding source-unit contract:** `docs/publication_source_unit_contract.md`
> **Binding candidate-output schema:** `schemas/publication_candidate_output.schema.json`
> **Binding evidence-validation contract:** `docs/publication_evidence_validation_contract.md`
> **Date drafted:** 2026-07-30
> **Date revised:** 2026-07-31
> **Date frozen:** 2026-07-31

## 1. Purpose

This document defines how Publication Pilot 1 human annotations are created, reconciled,
adjudicated, and preserved. It governs two related but distinct activities:

1. **model-independent gold annotation**, used to construct the human reference
   representation; and
2. **candidate adjudication**, used after automatic validation to decide whether a
   validated LLM candidate should enter the source-level augmented representation.

The guideline does not define automatic validation, metric formulas, entity/relation
matching thresholds, model-selection thresholds, or production implementation. Those
responsibilities belong to separate frozen or forthcoming contracts.

This guideline is limited to **Study 2**. Study 2 ends with construction of the
multigranular KG, source-level and cross-source alignment/consolidation, intrinsic KG
evaluation, and comparison with GraphRAG using the two approved schema-agnostic graph
metrics. It does not include KG-RAG retrieval, question-answer benchmark construction,
comparison against the four Study 3 baselines, answer-quality evaluation, or expert
evaluation. Those activities belong to Studies 3 and 4.

The governing evidence rule remains:

> **No supported evidence span means no accepted semantic assertion.**

## 2. Authority and scope

Conflicts are resolved in this order:

1. frozen ontology 0.1.3 specification and generated OWL;
2. frozen deterministic Phase B outputs and tests;
3. final Publication Pilot 1 human-readable target inventory;
4. publication ontology observations register;
5. LLM extraction decision record;
6. final machine-readable publication target profile;
7. final publication source-unit contract;
8. final publication candidate-output JSON Schema;
9. final publication evidence-validation contract;
10. this annotation and adjudication guideline.

This guideline may narrow annotation behavior but may not broaden the frozen ontology or
Publication Pilot 1 target profile.

## 3. Separation of responsibilities

### 3.1 Annotation

Annotation identifies source-supported nodes, edges, attributes, and evidence directly
from the canonical source representation. Gold annotation is performed independently of
model output.

### 3.2 Automatic validation

Automatic validation determines whether a parsed candidate is structurally valid,
source-grounded, ontology-compatible, and permitted by the frozen target profile. A
candidate with `candidateValidationStatus: validated` is not automatically accepted as
scientifically correct.

### 3.3 Adjudication

Adjudication is a human decision. It resolves:

- disagreements between independent gold annotations;
- possible semantic duplicates;
- ambiguous atomicity;
- scientifically unsupported but structurally valid model candidates;
- localized normalized-label proposals;
- unresolved deferred-record proposals; and
- corrections required before a candidate can enter an augmented source snapshot.

### 3.4 Evaluation matching

Exact entity, relation, and evidence matching rules are defined in the later Publication
Pilot 1 evaluation-matching contract. Annotators must preserve sufficient detail for that
contract but must not alter annotations to optimize anticipated metrics.

## 4. Roles and independence

Publication Pilot 1 uses the following logical roles:

```text
annotator
    Produces an independent source-grounded annotation.

adjudicator
    Resolves disagreements and records the final gold or candidate decision.

annotation_custodian
    Maintains versioned files, hashes, assignment manifests, and change logs.
```

One person may hold more than one role only when resource limitations require it. When
the adjudicator is also an original annotator, the role overlap must be recorded and the
final rationale must still be explicit.

External annotators are expected to perform only a simple interface-based task:

1. highlight exact source text;
2. select a human-readable node type;
3. connect already identified nodes using a human-readable relation when applicable; and
4. mark uncertainty with an optional concise note.

They are not expected to enter or calculate ontology IDs, operational target IDs,
source-unit IDs, section IDs, offsets, hashes, candidate IDs, endpoint IDs, graph IDs,
JSON records, schema fields, validation codes, merge or consolidation decisions, or
Neo4j identifiers. Candidate adjudication and normalization review are expert-adjudicator
tasks performed after the gold representation is frozen.

Annotators require relevant domain familiarity in hydrology, environmental science,
water resources, scientific computing, data-intensive environmental research, or closely
related graduate-level research. They do not need to master the full ontology. Training
and calibration focus on literal evidence, atomicity, uncertainty, frequent visible node
categories and relations, and these recurring distinctions:

- Model versus Method versus Algorithm versus Tool;
- Finding versus Conclusion;
- ResearchProblem versus ResearchGoal;
- use versus mention versus reference; and
- EvaluationMetric versus Parameter.

Annotators must be identified through stable pseudonymous IDs in released annotation
artifacts. A separate private roster may map those IDs to individuals.

## 5. Blinding and leakage control

### 5.1 Gold annotation precedes model inspection

Gold annotators must not see:

- model prompts;
- raw model responses;
- parsed model candidates;
- validator findings for model candidates;
- model confidence or probability;
- automated candidate labels or relations.

The initial gold representation must be frozen before candidate-level model adjudication
begins.

### 5.2 Deterministic context is permitted

Annotators may see frozen deterministic Phase B context explicitly provided for the same
source, including exact existing endpoints and deferred records. Deterministic context is
not a model prediction.

### 5.3 Post-model gold amendments

A model candidate may reveal a genuine omission in the frozen gold. Such a case must not
be silently reclassified as a model error or silently inserted into gold. It follows the
controlled amendment process in Section 18.

The required sequence is:

```text
independent gold annotation
-> gold adjudication
-> initial gold freeze
-> model execution
-> automatic candidate validation
-> model-candidate adjudication
```

## 6. Annotation phases

### Phase A — Training and calibration

Ordinary annotators review a concise annotator handbook and calibration materials derived
from the technical authorities. These annotator-facing materials contain only
human-readable categories, examples, boundaries, and uncertainty guidance. Ordinary
annotators are not expected to read or master the raw ontology, machine-readable target
profile, source-unit contract, or evidence-validation contract.

The expert adjudicator and annotation custodian are responsible for applying the technical
contracts. The annotators jointly discuss a small calibration set. The concise annotator
handbook remains a later implementation artifact and is not created in this guideline
review.

Calibration annotations are not used for inter-annotator agreement unless they are later
re-annotated independently after the guideline is frozen.

### Phase B — Independent reliability annotation

A predeclared reliability subset is annotated independently by at least two annotators.
The exact subset size and artifact IDs are frozen in the later pilot sample/input record.
This is the only portion that requires full duplicate annotation unless quality checks
justify expansion.

During independent annotation:

- annotators may not inspect one another's work;
- disagreements are not resolved inline;
- each annotator records uncertainty explicitly; and
- source-grounded positive assertions are retained even when classification is uncertain.

### Phase C — Remaining selected-unit annotation

The remaining selected source units may be annotated once and reviewed by the expert
adjudicator through an independent second human review. This review examines the primary
annotation against the canonical source and may accept it, identify omissions, or route
records to adjudication; it does not require duplication of the full annotation workflow.
Publication Pilot 1 does not require exhaustive duplicate annotation of all twelve
publication artifacts.

### Phase D — Gold adjudication

The adjudicator receives the independent annotations, canonical evidence, bounded context,
and deterministic context. Model output remains hidden.

The adjudicator creates the final gold representation and a disagreement-resolution log.
The log preserves both original annotations.

### Phase E — Model-candidate adjudication

Only after the gold is frozen may the adjudicator inspect validated model candidates.
Candidate adjudication determines inclusion in the augmented source representation; it
does not retroactively redefine the initial model-independent gold except through the
formal amendment process.

## 7. Annotation unit and permitted context

### 7.1 Sample boundary

Annotation is exhaustive only within the source units selected and frozen in the pilot
sample/input record. It is not exhaustive over all twelve complete publication artifacts.

Pilot annotations are reusable. When the protocol and target definitions remain unchanged,
they become part of the final Study 2 evaluation sample; additional units are added rather
than re-annotating the pilot.

The final Study 2 benchmark is stratified by artifact family and includes selected
artifacts from every source type. Source-unit annotations may be nested within those
selected artifacts. Every artifact included in the final benchmark receives at least two
human reviews: the reliability subset receives two fully independent annotations before
adjudication, while remaining benchmark artifacts may receive one primary annotation plus
an independent expert second review. Inter-annotator agreement is computed only on the
independently annotated reliability subset.

Exact sample sizes, percentages, artifact IDs, and annotation volumes remain deferred to
the pilot sample/input freeze record. Different artifact families need not receive the
same annotation volume.

### 7.2 Canonical source

Canonical Markdown governed by the frozen source-unit contract is authoritative. The PDF
may be consulted only to diagnose conversion problems and may not supply evidence absent
from canonical Markdown.

### 7.3 Primary annotation unit

The primary annotation unit is one canonical publication source unit.

Every annotation batch must record:

```text
sourceArtifactID
sourceUnitID
sectionID
sectionTitle
sourceUnitTextHash
canonicalDocumentHash
```

These identifiers and hashes are pipeline-populated; ordinary annotators neither enter
nor calculate them.

### 7.4 Context scope

Annotators may inspect the same forms of bounded canonical context defined for extraction:

```text
local_unit
section_context
document_reconciliation
```

Every gold assertion records the narrowest `discoveryScope` sufficient to support it.

`discoveryScope` is pipeline-populated from the authorized annotation view rather than
entered by the ordinary annotator.

A document-level scope does not permit unsupported source-level summarization. Exact
evidence spans remain mandatory.

### 7.5 Distributed evidence

When an assertion requires distributed support:

- use multiple contiguous evidence spans;
- never create one span that crosses a source-unit boundary;
- retain each source-unit identifier and exact offsets;
- record why the spans are jointly required.

## 8. Coverage by pilot treatment

### 8.1 `extract_and_evaluate`

For routed `extract_and_evaluate` targets, annotation is **exhaustive within the declared
annotation scope**. Annotators must review every eligible source unit and record all
supported positive instances.

If exhaustive review finds no positive instance for an eligible target, record the target
as absent rather than as a semantic abstention.

### 8.2 `extract_and_monitor`

For `extract_and_monitor` targets, annotators record supported positive instances and
uncertainties. Absence is not interpreted as an exhaustive negative unless the annotation
batch explicitly declares:

```text
completenessMode: exhaustive
```

### 8.3 Other treatments

```text
context_only
    May be referenced but is not re-annotated as an open semantic discovery target.

required_infrastructure
    Created or checked by the pipeline, not independently annotated as an LLM prediction.

deferred_resolution
    Annotated as an explicit resolver task tied to the original deferred-record ID.

separate_follow_on_protocol
    Excluded from the primary Pilot 1 annotation set.

out_of_scope
    Not annotated.

audit_only
    Preserved for lineage but not reopened.
```

## 9. Two-pass human workflow

Ordinary annotation uses two separate passes:

```text
Pass 1
    Highlight exact source text and classify supported nodes.

Pass 2
    Connect identified nodes or exact deterministic endpoints with supported relations.
```

The interface presents human-readable categories and relations filtered by routed
eligible targets, section context, endpoint types, allowed domain/range, and Pilot 1
treatment. It does not present all 46 node targets and 27 relation targets simultaneously.
Interface design and implementation remain later work.

## 10. Evidence annotation

Every positive node and non-derived edge requires one or more evidence spans.

For each span, the stored gold record contains:

```text
evidenceSpanID
sourceArtifactID
sourceUnitID
sourceUnitTextHash
sectionID
sectionTitle
evidenceText
startOffsetInUnit
endOffsetInUnit
startOffsetInDocument
endOffsetInDocument
```

The ordinary annotator highlights literal text. The interface and pipeline populate span
IDs, source and section IDs, zero-based half-open offsets measured in Unicode code points,
and hashes. One span cannot cross a source-unit boundary; distributed support uses
multiple spans.

The annotation interface must verify both literal slices:

```text
unit.text[startOffsetInUnit:endOffsetInUnit] == evidenceText

canonicalDocument[
    startOffsetInDocument:endOffsetInDocument
] == evidenceText
```

Annotators may not use:

- paraphrases as evidence;
- a normalized label as evidence;
- visual-only figure interpretation;
- standalone equation reconstruction;
- unsupported table reconstruction;
- external web or bibliographic knowledge;
- source text not present in the canonical requestable representation.

Node evidence does not automatically support an edge. Each edge needs evidence that
supports the relation semantics.

## 11. Node annotation rules

### 11.1 Atomicity

```text
one gold node = one atomic semantic unit
```

Separate nodes are required when one passage contains distinct findings, goals, methods,
limitations, variables, parameters, or other independently meaningful assertions.

A single node may use multiple evidence spans when the same semantic unit is expressed
across locations.

### 11.2 Labels

The authoritative gold label is the exact source-grounded surface form:

```text
labelMode: verbatim
```

For discourse nodes, use the smallest complete source-supported proposition that preserves
the intended meaning. For named entities, use the exact source surface form.

### 11.3 Normalized labels

A normalized label is optional and non-authoritative.

The expert adjudicator may record a normalized form, but the verbatim label remains
authoritative. Ordinary annotators are not asked to normalize labels. Normalization cannot
establish identity, linking, duplicate suppression, merging, or consolidation.

### 11.4 Class assignment

Annotators select the most specific supported concrete class. The following abstract
classes cannot be directly annotated:

```text
SoftwareEntity
ComputationalModel
Place
HydrologicFeature
```

When evidence does not support a concrete class, annotators record uncertainty rather than
using an abstract fallback.

### 11.5 Model, method, algorithm, and tool discriminant

Use this operational sequence:

```text
named thing that could own a repository, dataset, or paper
    → concrete ComputationalModel subtype, Tool, or Algorithm

technique, procedure, or applied activity
    → Method

named statistical model with stable reusable identity
    → StatisticalModel

generic regression, estimation, calibration, training, or analysis
    → Method
```

The same passage may support both a reusable entity and the Method that applies or uses it
when the roles are distinct and separately evidenced.

### 11.6 Finding, conclusion, problem, and goal discriminants

```text
Finding
    A source-supported result, observation, or outcome.

Conclusion
    An interpretive synthesis or concluding claim drawn from findings.

ResearchProblem
    The issue, gap, or need the research addresses.

ResearchGoal
    The intended objective or outcome of the research activity.
```

Do not label an aim as a problem merely because it motivates the work, and do not label a
reported result as a conclusion unless the passage makes the interpretive role explicit.

### 11.7 Contextual metrics and parameters

`EvaluationMetric` and `Parameter` are contextual occurrences. Same-named items remain
separate when owner, experiment, model, method, condition, value, range, or configuration
differs.

Values and ranges are preserved as exact source strings.

### 11.8 Existing and provisional identities

Use an existing deterministic endpoint only when exact identity is available in the
authorized deterministic context.

A repository named without exact identity remains:

```text
identityScope: source_local
provisionalIdentity: true
```

Name similarity alone never authorizes a global merge or exact link.

Repeated surface forms within a source are one local node only when they express the same
contextual identity. Distinct occurrences remain separate when their owners, roles,
conditions, values, or meanings differ.

## 12. Relation annotation rules

### 12.1 Edge-specific evidence

Evidence for endpoint nodes does not automatically support a relation. Each non-derived
gold edge requires evidence for the relation semantics.

### 12.2 Direction

Relations must follow the frozen operational direction and domain/range. Annotators must
not reverse an edge for linguistic convenience.

### 12.3 Endpoint references

Every edge endpoint must refer to:

- a gold node in the current annotation set;
- an exact deterministic endpoint; or
- a previously adjudicated local endpoint explicitly available in context.

Raw name-only endpoints are not allowed.

### 12.4 Relation boundaries

The frozen target inventory governs each relation. In particular:

- `resolves` follows `Method / Contribution / ResearchQuestion → ResearchProblem` and
  requires explicit addressing of that ResearchProblem;
- `produces` requires an explicit Method/Experiment-to-Finding connection;
- `testedBy` is limited to `Hypothesis → Method/Experiment`;
- `supports` is positive-only and excludes `Finding → Hypothesis`;
- local `relatesTo` excludes cited-Paper grounding;
- model-authored `hasLimitation` is limited to `Finding → Limitation`;
- `usesModel` and `appliesTo` encode distinct roles;
- `reportsMetric`, `evaluates`, and `hasParameter` require aligned context;
- `usesAlgorithm` has no Paper-level shortcut;
- no summary or TheoreticalBasis-grounding relation is available.

### 12.5 Use, mention, and reference precedence

For the same Paper–Entity pair:

```text
usesModel supersedes mentionsModel
usesTool supersedes mentionsTool
usesDataset supersedes mentionsDataset
hasCodeRepository supersedes referencesRepository
```

`usesDataset` and `referencesDataset` may coexist.

Annotators should record the strongest supported role, not all weaker entailed roles.

## 13. Uncertainty and abstention

Annotator uncertainty is not equivalent to model abstention.

An annotation uncertainty record may identify:

```text
ambiguous_class
ambiguous_relation
ambiguous_atomicity
insufficient_evidence
unresolved_endpoint
source_conversion_problem
possible_local_duplicate
target_boundary_unclear
```

The annotator must retain the relevant evidence and competing options when available.

Uncertainty is resolved during gold adjudication. It does not create a positive gold
assertion until adjudicated.

## 14. Gold disagreement categories

Disagreements are classified as:

```text
missed_positive
unsupported_positive
span_boundary
atomicity
class_assignment
relation_assignment
relation_direction
endpoint_identity
use_mention_reference
model_method_algorithm_tool
metric_parameter_context
local_duplicate
scope_or_eligibility
source_conversion
other_documented
```

Each disagreement record includes:

```text
disagreementID
sourceArtifactID
sourceUnitIDs
annotatorRecordIDs
category
evidenceSpanIDs
adjudicationDecision
adjudicationRationale
guidelineSection
```

## 15. Gold adjudication decisions

Gold adjudication produces one of:

```text
accept_one_original
accept_adjudicated_revision
accept_both_as_distinct
merge_as_one_local_gold_record
split_into_multiple_gold_records
reject_all_unsupported
defer_unresolved
exclude_out_of_scope
source_conversion_blocked
```

The final gold record must be representable under the frozen target profile and source
evidence rules.

`accept_one_original` records the selected annotator-record ID. An adjudicated revision is
newly recorded by the adjudicator and is not described as pre-adjudication consensus.

Adjudication does not authorize ontology expansion. A genuine schema gap is logged for
post-pilot review or handled through the formal ontology-change process.

## 16. Model-candidate adjudication

Only candidates that pass the automatic-validation boundary, or are explicitly routed as
`needs_review` or `deferred`, enter candidate adjudication.

### 16.1 Candidate adjudication decision

```text
accepted
rejected
deferred
superseded
excluded
```

`accepted` enters the source-level augmented representation; `rejected` is an eligible but
incorrect candidate; `deferred` awaits an authorized unresolved task; `superseded` is
represented by a stronger or retained candidate; and `excluded` was never eligible for
the primary Pilot 1 task.

### 16.2 Candidate resolution

An adjudication decision also records one resolution:

```text
as_proposed
edited_label
edited_class
edited_relation
edited_endpoint
edited_evidence
linked_existing
merged_local_duplicate
split_candidate
remain_deferred
not_applicable
```

A candidate that requires a semantic edit is not treated as an exact true positive in
later evaluation unless the forthcoming matching contract explicitly permits that match.

### 16.3 Candidate rejection reasons

```text
unsupported_by_evidence
wrong_class
wrong_relation
wrong_direction
wrong_endpoint
invalid_atomicity
duplicate
weaker_relation
outside_pilot_scope
source_conversion_problem
identifier_or_identity_not_resolved
other_documented
```

### 16.4 Preservation

The original parsed candidate and automatic-validation result remain immutable. Human
adjudication produces a separate record referencing both.

## 17. Normalization adjudication

Normalization review is field-local and independent of candidate acceptance.

Allowed normalization decisions are:

```text
not_applicable
accept_proposal
accept_edited_form
keep_verbatim_only
reject_proposal
```

A candidate may be accepted while its normalization proposal is rejected.

The normalization record includes:

```text
verbatimLabel
normalizedLabelProposal
adjudicatedNormalizedLabel
normalizationDecision
normalizationRationale
```

An accepted normalized label remains a convenience representation, not evidence and not a
global identity assertion.

## 18. Gold amendment after model exposure

After model candidates become visible, a proposed gold amendment requires:

1. a specific validated candidate or later review finding;
2. exact canonical evidence;
3. review by an adjudicator who did not originate the model output;
4. an amendment category;
5. a written rationale;
6. the affected gold and candidate record IDs;
7. a new gold version and hash;
8. recomputation of all affected metrics.

Allowed amendment categories are:

```text
gold_omission
gold_wrong_class
gold_wrong_relation
gold_wrong_endpoint
gold_span_error
gold_duplicate
gold_atomicity_error
source_conversion_correction
guideline_interpretation_change
```

Reports must distinguish:

- performance against the initially frozen gold; and
- performance against any corrected final gold.

No amendment is made solely because the model produced a plausible alternative.

## 19. Guideline change control

During a comparable pilot run, no silent guideline change is allowed.

A change affecting class boundaries, relation semantics, evidence authority, atomicity,
identity, eligibility, or adjudication outcomes requires:

```text
pause
→ document issue
→ assess affected records
→ approve version increment
→ update tests and examples
→ re-annotate or re-adjudicate affected cases
→ recompute agreement and evaluation
```

Editorial clarifications that do not change decisions may be recorded without changing
previous outcomes, but they still require a documented revision note.

## 20. Required annotation artifacts

Recommended version-controlled curation artifacts are:

```text
data/curation/publications/pilot1/
    annotation_assignment_manifest.json
    annotator_a_annotations.jsonl
    annotator_b_annotations.jsonl
    gold_adjudication_log.jsonl
    adjudicated_gold.jsonl
    candidate_adjudication.jsonl
    normalization_adjudication.jsonl
    gold_amendments.jsonl
    annotation_manifest.json
```

Exact filenames may be adjusted during implementation, but the logical separation among
raw annotations, gold adjudication, candidate adjudication, normalization decisions, and
gold amendments is binding.

## 21. Annotation-record minimum fields

Every raw annotation record includes at least the fields below, but the interface separates
human input from pipeline-generated metadata.

Human-entered fields:

```text
highlighted text
human-readable node type
human-readable relation
selected endpoints
uncertainty category
optional concise note
```

Pipeline-populated or derived fields:

```text
annotationRecordID
annotationGuidelineVersion
annotationBatchID
annotatorID
sourceArtifactID
sourceUnitIDs
discoveryScope
completenessMode
eligibleOperationalTargetIDsReviewed
recordType
operationalTargetID
ontologyID
label
endpointReferences
attributeValues
evidence spans and offsets
source and evidence hashes
createdAt
```

Expert-adjudicator-entered fields include adjudication decisions and rationales,
candidate resolutions and rejection reasons, normalization decisions, gold-amendment
categories, and any approved normalized label. Thus the responsibility classes are:

```text
human_entered
    Highlight, human-readable classification or relation, endpoints selected through the
    relation action, uncertainty, and an optional concise note.

pipeline_populated
    All identifiers, ontology/profile mappings, offsets, hashes, schema fields,
    provenance metadata, and derived evidence records.

expert_adjudicator_entered
    Adjudication, candidate, normalization, amendment, and source-level duplicate
    decisions with their rationales.
```

`createdAt` is provenance metadata and is excluded from semantic identity hashes.

Annotators must not be asked to calculate or transcribe pipeline-populated fields. The
exact machine-readable annotation and adjudication schemas may be implemented later, but
they may not weaken these required semantics.

## 22. Quality-control checks

Before gold freeze:

- every record references existing canonical source units;
- all evidence slices reproduce their literal text;
- all targets exist in the frozen profile;
- all ontology IDs and names correspond to the operational target;
- all node and edge endpoints resolve locally or deterministically;
- every non-derived edge has relation-specific evidence;
- no abstract class is instantiated;
- no forbidden or follow-on relation is annotated;
- all reliability-subset annotations are independent;
- every disagreement has a final disposition;
- all gold records have stable IDs and hashes;
- the annotation manifest records versions and input hashes.


## 23. Study 2 evaluation support and boundaries

### 23.1 Extraction gold standard

The adjudicated records form an ontology-aligned entity-and-relation gold-standard
benchmark for Study 2 extraction evaluation and intrinsic KG evaluation. They preserve
target membership, exact evidence, contextual identity, endpoints, and relation direction
for later per-target analysis, macro and micro aggregation, and error analysis.

Precision, Recall, F1, and entity/relation matching rules and formulas are defined only in
the forthcoming evaluation-matching contract.

### 23.2 Semantic depth and fact recoverability

Evidence-bearing nodes and directed relations preserve the foundation for later Study 2
chain-level fact-recoverability evaluation. A preferred problem-method-result traversal is:

```text
ResearchProblem <- resolves - Method -> produces -> Finding
```

The individually explicit directed relations are:

```text
Method / Contribution / ResearchQuestion -> resolves -> ResearchProblem
Method / Experiment -> produces -> Finding
```

Other supported chains include `Paper -> usesDataset -> Dataset` and
`Paper -> hasCodeRepository -> Repository`. Cross-source documentation chains depend on
later artifact-family annexes and alignment. This guideline does not define
fact-recoverability scoring.

### 23.3 Separate Study 2 graph and ontology evaluations

Information density and relational richness remain the two approved schema-agnostic,
graph-level metrics for comparison with GraphRAG. Redundancy reduction is evaluated later
during alignment and consolidation. None is an ordinary annotation task.

Extraction annotation alone does not validate global entity consolidation. The final
Study 2 evaluation plan requires a later alignment/consolidation reference sample or
human audit; this guideline does not design it.

Ontology competency questions, HermiT consistency, unsatisfiable-class checks, and other
ontology validation remain separate from extraction annotation.

No Study 3 question-answering gold answers, QA benchmark, retrieval-relevance judgments,
answer-quality rubrics, or four-baseline comparison are created here. Study 4 expert
evaluation is also out of scope.

## 24. Reuse across other Study 2 artifact families

This Publication Pilot 1 guideline establishes the reusable annotation core for Study 2.

For CIROH Hub, HydroShare, and GitHub:

1. reuse the common evidence, blinding, adjudication, amendment, and audit rules;
2. create a concise artifact-family annex defining source-unit differences, visible
   categories, eligible relations, source-specific evidence boundaries, artifact-specific
   calibration examples, and an artifact-specific reliability sample;
3. execute a small artifact-family calibration and reliability subset; and
4. expand only enough to support the final Study 2 intrinsic evaluation sample.

A complete independent protocol is not rewritten from zero for every artifact family.
The order and size of the remaining artifact-family annotation pilots are determined after
Publication Pilot 1 demonstrates that the common workflow is usable.

## 25. Study 2 stopping rule

Once Publication Pilot 1 demonstrates that the annotation workflow is usable, the
extraction and validation contracts are implementable, and agreed semantic-quality
thresholds are met or corrected through one controlled revision cycle, the project moves
to full publication extraction. The numeric GO/REVISE/NO-GO thresholds remain in the
forthcoming evaluation-matching contract.

Additional annotation or protocol work is required only for:

- the final Study 2 intrinsic evaluation sample;
- artifact-family annex validation;
- an alignment/consolidation reference audit; or
- records affected by an approved methodological change.

This stopping rule prohibits an open-ended annotation or protocol-refinement loop.

## 26. Contract-freeze gate

This guideline may be marked final after:

- [x] the Study 2 boundary and stopping rule are approved;
- [x] the simplified human workflow is approved;
- [x] human-entered and pipeline-populated fields are separated;
- [x] sample-based exhaustive coverage is approved;
- [x] cross-artifact-family reuse through concise annexes is approved;
- [x] roles and blinding rules are approved;
- [x] annotation phases are approved;
- [x] exhaustive versus monitored coverage is approved;
- [x] source-unit and context rules align with the frozen source-unit contract;
- [x] node atomicity and class distinctions are approved;
- [x] edge-specific evidence and relation boundaries are approved;
- [x] uncertainty and disagreement categories are approved;
- [x] gold adjudication decisions are approved;
- [x] model-candidate adjudication decisions and reasons are approved;
- [x] normalization adjudication remains field-local;
- [x] post-model gold amendment control is approved;
- [x] required annotation artifacts and minimum fields are approved;
- [x] focused static contract tests pass; and
- [x] no unresolved methodological contradiction remains.

## 27. Annotation-execution acceptance gate

Annotation execution is accepted only after:

- [ ] the annotation assignment manifest is frozen;
- [ ] annotator training and calibration are documented;
- [ ] the reliability subset is independently annotated;
- [ ] all required source units are reviewed at the declared completeness level;
- [ ] all evidence spans validate literally;
- [ ] all disagreements are adjudicated;
- [ ] adjudicated gold is frozen with a reproducible hash;
- [ ] inter-annotator agreement is computed under the frozen matching rules;
- [ ] candidate adjudication begins only after initial gold freeze;
- [ ] all post-model gold amendments follow Section 18;
- [ ] no frozen upstream artifact is mutated.

## 28. Acceptance statement

Passing the contract-freeze gate makes this document the final binding Publication Pilot 1
annotation and adjudication guideline. Passing the later annotation-execution acceptance
gate demonstrates that the human annotation process conforms to the frozen guideline.
