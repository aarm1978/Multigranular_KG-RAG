# Publication Pilot 1 Sample and Input Freeze Record

> **Status:** candidate; not yet frozen
> **Document version:** 0.2.2
> **Artifact family:** scientific publications
> **Dissertation scope:** Study 2 — ontology-guided multigranular KG construction and intrinsic evaluation
> **Pilot:** Publication Pilot 1
> **Date drafted:** 2026-07-31
> **Date revised:** 2026-07-31
> **Required predecessor:** `docs/publication_evaluation_matching_contract.md`
> **Binding ontology:** CIROH ontology 0.1.3
> **Binding target profile:** `src/extraction/llm/publications/publication_target_inventory.yaml`
> **Binding source-unit contract:** `docs/publication_source_unit_contract.md`
> **Binding candidate-output schema:** `schemas/publication_candidate_output.schema.json`
> **Binding evidence-validation contract:** `docs/publication_evidence_validation_contract.md`
> **Binding annotation guideline:** `docs/publication_annotation_adjudication_guidelines.md`

## 1. Purpose

This document will freeze the exact Publication Pilot 1 evaluation sample and all inputs
required to reproduce:

1. human gold annotation;
2. inter-annotator reliability analysis;
3. ontology-guided LLM extraction;
4. automatic candidate validation;
5. evaluation against the adjudicated gold representation; and
6. the Publication Pilot 1 GO/REVISE/NO-GO decision.

This document does not define matching formulas, metric aggregation, or numeric decision
thresholds. Those are owned by the preceding Publication evaluation-matching contract.

The preceding matching contract is final and binding. This sample record remains a
candidate and must not be marked final until its own final freeze gate passes.

## 2. Dependency order

The methodological order is binding:

```text
evaluation-matching contract
→ sample and input freeze
→ model/reproducibility policy
→ annotation and implementation
→ pilot execution
```

The evaluation-matching contract comes first because it determines:

- what constitutes a scorable node or relation;
- which evidence-span conditions are required;
- how empty-gold and abstention cases are treated;
- which target-level denominators are required;
- how inter-annotator agreement is computed; and
- what minimum support is required for GO/REVISE/NO-GO decisions.

Those requirements are now established by the frozen matching contract. This sample
record remains a candidate until exact source units, partitions, routing, and hashes exist.

## 3. Authority order

Conflicts are resolved in this order:

1. frozen ontology 0.1.3;
2. frozen deterministic Publication Phase B outputs and tests;
3. frozen Publication Pilot 1 target inventory and observations register;
4. frozen machine-readable Publication target profile;
5. frozen Publication source-unit contract;
6. frozen Publication candidate-output schema;
7. frozen Publication evidence-validation contract;
8. frozen Publication annotation and adjudication guideline;
9. frozen Publication evaluation-matching contract;
10. this sample and input freeze record.

This record may select among eligible inputs but may not broaden the frozen target universe,
change ontology semantics, or alter evidence requirements.

## 4. Frozen upstream anchors

The following values must be recomputed and verified at the final freeze pass.

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

Publication evaluation matching contract version:
0.1.0

Publication evaluation matching contract SHA-256:
10f8dca24bf41acfb21f8d20c5cda7b022392040446a2e2e4bac137365c076d0
```

The final matching-contract version and hash above are binding upstream anchors for this
candidate record.

## 5. Fixed artifact pool

The Publication Pilot 1 artifact pool is fixed to the following twelve source artifacts:

```text
10
15
16
18
34
37
46
54
79
276
87
87-corrigendum
```

Interpretation:

- eleven primary-publication records, comprising ten regular primary-publication records
  and publication `87`, which has a related corrigendum;
- one separate corrigendum artifact.

The corrigendum pair is retained because it tests a special source condition already
recognized by the deterministic layer.

The deterministic `corrects` relation for `87-corrigendum` is not an LLM extraction target
and must not be recreated as a semantic candidate.

All twelve identifiers resolve to distinct curated records in the canonical Phase A
Publication corpus. Artifact `15`, the off-domain but deliberately curated member of this
frozen pilot pool, remains eligible; topical fit may be recorded as a coverage dimension
but may not be used to remove it. The final unit-level selection must preserve artifact
stratification. Every artifact in the fixed twelve-artifact pool must contribute at least
one eligible source unit to either the `reliability` or `remaining_evaluation` partition.
Calibration and `reserved_diagnostic` units may provide additional coverage but do not
satisfy this primary-evaluation representation requirement.

No artifact may be added or removed after final freeze without:

1. a documented reason;
2. a document-version increment;
3. regeneration of affected source units and hashes;
4. reassessment of target coverage and reliability partitions; and
5. explicit approval before pilot execution.

## 6. Pilot population versus evaluation sample

The twelve artifacts form the fixed pilot population.

The evaluation sample consists of selected canonical source units nested within those
artifacts.

The distinction is:

```text
pilot population
    all twelve fixed publication artifacts

evaluation sample
    the source units selected for gold annotation and extraction scoring

calibration set
    source units used for annotator training; excluded from primary metrics

reliability subset
    evaluation source units annotated independently by at least two annotators

remaining evaluation set
    evaluation source units receiving one primary annotation and an independent expert
    second review

reserved diagnostic set
    source units withheld from primary scoring and used only for controlled error diagnosis
    or the single permitted revision cycle
```

Publication Pilot 1 does not require exhaustive annotation of every source unit in all twelve
artifacts.

The four partitions are mutually exclusive at source-unit level. A source unit has exactly
one partition and cannot migrate after freeze. An artifact may contribute different units
to more than one partition; whole-artifact exclusion is not required merely because one of
its units was used for calibration. The selection manifest records same-artifact
cross-partition exposure so later assignment can avoid giving an annotator reliability or
remaining-evaluation units from an artifact whose calibration content would materially
reveal their answer. This is an assignment control, not an automatic artifact-level ban.

Reliability and diagnostic separation is unit-level. Diagnostic units remain inaccessible
to annotators, second reviewers, and the primary model/prompt-selection workflow until an
observed error pattern authorizes the single controlled diagnostic use. Calibration and
diagnostic units are outside the evaluation sample used for primary scoring; the
reliability and remaining-evaluation partitions together form that primary evaluation
sample.

Every fixed artifact is represented in that primary evaluation sample. It therefore
receives either two independent annotations through at least one `reliability` unit or one
primary annotation plus one independent expert second review through at least one
`remaining_evaluation` unit. An artifact need not contribute to both primary partitions.

## 7. Canonical input unit

The canonical input unit is the source unit generated under:

`docs/publication_source_unit_contract.md`

The final sample manifest must identify every selected unit using at least:

```text
sourceArtifactID
sourceUnitID
sectionID
sectionTitle
sourceUnitOrdinal
sourceUnitTextHash
canonicalDocumentHash
startOffsetInDocument
endOffsetInDocument
characterCount
atomicBlockCount
routingMetadata
sourceConversionStatus
```

The source-unit builder must complete successfully before this record can be frozen.

Request-level context is not part of source-unit identity.

For every model request, the run manifest separately records:

```text
primarySourceUnitID
contextSourceUnitIDs
contextPolicyName
contextPolicyVersion
includedCompleteSection
omittedEligibleSourceUnitIDs
contextSelectionReason
modelContextBudgetTokens
estimatedInputTokens
```

## 8. Source-unit materialization requirements

Before source-unit selection, the builder must materialize all canonical source units for
the twelve-artifact pool.

Required outputs:

```text
data/curation/publications/pilot1/
    publication_pilot1_source_unit_inventory.jsonl
    publication_pilot1_source_unit_manifest.json
```

The manifest must record:

```text
builderVersion
sourceUnitContractVersion
sourceUnitContractHash
artifactCount
sourceUnitCount
canonicalDocumentHashes
sourceUnitInventoryHash
generationTimestamp
generationEnvironment
validationResults
phaseASchemaVersion
phaseAVersion
phaseBVersion
phaseBArtifactHash
sourceUnitBuilderConfigurationHash
artifactRecords
```

Each `artifactRecords` entry must bind the canonical artifact identifier, record type,
repository-relative Markdown path, raw and canonical text hashes, recoverable Marker
version or an explicit `unavailable_with_justification` value, chunks/metadata hashes,
unit and eligibility counts, and conversion-status summary required by the frozen
source-unit contract. The inventory fields must be a faithful superset of the canonical
source-unit record in that contract; aliases such as `sourceArtifactID`/`paperID` and
`sourceUnitTextHash`/`textHash` must be documented rather than silently substituted.

The inventory and manifest filenames may be adjusted during implementation, but their
logical content is required.

No unit may be manually rewritten after materialization.

## 9. Eligibility rules

A source unit is eligible for sample selection when:

1. it belongs to one of the twelve fixed artifacts;
2. it exists in the canonical source-unit inventory;
3. its source text passes literal-slice and offset validation;
4. its source artifact is not excluded because of unresolved conversion damage;
5. it contains or provides necessary context for at least one eligible Publication Pilot 1
   target; and
6. its inclusion is compatible with the frozen matching contract.

A source unit is not automatically eligible merely because it is long or comes from a
particular section.

Eligibility is decided before partition assignment. A unit that supplies necessary
context but has no independently eligible target is not selected as a primary unit merely
to manufacture a positive; it may be referenced through the frozen request-context policy.

### 9.1 Versioned source-unit screening

Screening is a preselection review of canonical source text. It may record likely coverage
and conversion quality, but it is not gold annotation and must not create assertion
records, exact positive counts, gold evidence spans, or adjudicated decisions.

Every screened unit receives:

```text
screeningReviewerID
screeningVersion
screeningStatus
screeningRationale
likelyReportingFamilies
likelySamplingStrata
likelyExhaustiveEmptyTargetIDs
sourceConversionStatus
screenedAt
```

`likelyReportingFamilies` and `likelySamplingStrata` are blinded expert expectations, not
realized support. Screening
may use deterministic corpus statistics and expert reading only. It may not use model
output, model-specific ease judgments, candidate-validator results, or external knowledge,
and it may not rewrite canonical unit text. Screening records are version-controlled and
hashed separately from later raw annotations, adjudication, and gold.

Screening does not certify semantic absence. `likelyExhaustiveEmptyTargetIDs` records only
a prospective expectation for a unit-target pair whose completeness mode will be frozen
as `exhaustive`. A unit-target pair becomes an exhaustive-empty case only after the
applicable independent annotation and review process establishes zero supported instances
under that prospectively frozen mode.

## 10. Eligibility, partition, and exclusion rules

A unit receives these separate fields:

```text
eligibilityStatus: eligible | ineligible | needs_review
partition: calibration | reliability | remaining_evaluation | reserved_diagnostic | null
exclusionReason: controlled value or null
```

`calibration` and `reserved_diagnostic` are partition roles, not exclusion reasons.
An ineligible unit may have only one primary exclusion reason from:

```text
no_eligible_target
source_conversion_blocked
duplicate_canonical_unit
administrative_or_reference_only
visual_only_evidence
equation_only_without_prose_support
outside_frozen_target_profile
corrigendum_structural_only
```

Every excluded unit remains in the complete source-unit inventory and receives:

```text
exclusionReason
exclusionRationale
reviewerID
decisionTimestamp
```

The record also preserves screening version and source-conversion status. A
`source_conversion_blocked` unit requires an audit record identifying the failed literal,
offset, table, or structure check. `administrative_or_reference_only` is applied
consistently with the source-unit contract: reference content remains auditable, while
typed/DOI-less citation grounding and fine-grained corrigendum alignment remain follow-on
work. `corrigendum_structural_only` cannot remove eligible local corrigendum semantics and
never reopens deterministic `corrects`.

Post hoc exclusion after model results are inspected is prohibited.

## 11. Sampling dimensions

The final sample must provide meaningful coverage across the following dimensions.

### 11.1 Artifact-level dimensions

```text
shorter and longer publications
standard and irregular section structures
computational and non-computational emphasis
model-intensive content
method-intensive content
metric- and parameter-rich content
dataset- and software-rich content
ordinary publication and corrigendum-related conditions
```

### 11.2 Section-level dimensions

At minimum, selection must consider units from:

```text
abstract
introduction/background
methods
results
discussion
conclusion
limitations or future work when present
```

A section label does not determine the target automatically.

### 11.3 Target-family dimensions

The final sample should support evaluation of:

```text
research framing
discourse structure
methods and experiments
models, algorithms, and tools
findings and conclusions
limitations and future work
metrics, parameters, and variables
datasets and repositories
concepts and geographic entities
eligible discourse relations
use/mention/reference relations
```

The final selection matrix must show which target families are eligible in each selected
source unit.

Every artifact-, section-, and target-family coverage dimension must be represented by:

```text
dimensionName
controlledValue
valueSource: deterministic_metadata | screened_expert_expectation
screeningMethod
selectionRationale
coverageStatus: covered | not_covered | not_present | insufficient_support | pending
```

Observed deterministic metadata and expert-screened expected semantic coverage must
remain separate columns. Neither is an actual gold count.

## 12. Treatment-aware selection

Only targets with these treatments may appear in Pilot 1 annotation or extraction, with
the following distinct evaluation roles:

```text
extract_and_evaluate
extract_and_monitor
deferred_resolution
```

Treatment rules:

```text
extract_and_evaluate
    Eligible for exhaustive positive annotation within the declared unit scope.

extract_and_monitor
    Positive instances are analyzed separately. They enter the primary extraction
    denominator only when a batch is predeclared `completenessMode: exhaustive` and the
    frozen matching contract permits promotion before annotation begins.

deferred_resolution
    Included only when tied to an exact original deferred-record ID and scored through
    separate resolution metrics, not ordinary node/relation F1.

context_only
    May be shown as context or used for exact endpoint linking; not scored as open semantic
    discovery.

required_infrastructure
    Pipeline responsibility; not a human or LLM prediction target.

separate_follow_on_protocol
    Excluded from Publication Pilot 1 primary scoring.

out_of_scope
    Excluded.

audit_only
    Preserved for lineage and not reopened.
```

### 12.1 Reporting families, decision roles, and sampling strata

The final freeze must include a machine-readable
`publication_pilot1_target_family_mapping.yaml` with three distinct fields:

```text
reportingFamily
decisionRole
samplingStratum
```

Their authorities are separate:

```text
reportingFamily
    Controls reporting and family-level interpretation under the frozen matching contract
    for blocking and monitored targets; it is null for separately scored or excluded roles.

decisionRole
    Controls blocking, monitoring, deferred, or excluded treatment.

samplingStratum
    Supports practical sample balancing only and has no direct metric or decision authority.
```

#### 12.1.1 Frozen reporting families

`reportingFamily` uses exactly these machine-readable values:

```text
research_framing
discourse_structure
methods_and_experiments
models_algorithms_and_tools
findings_conclusions_limitations_and_future_work
metrics_parameters_and_variables
datasets_and_repositories
concepts_and_geography
discourse_relations
use_mention_reference_relations
```

They correspond exactly, in order, to the ten human-readable target families in Section
21.3 of the frozen evaluation matching contract. No eleventh reporting family is
authorized. For `blocking` and `monitored` targets, `reportingFamily` is required, non-null,
and contains exactly one authorized value. For `deferred_resolution_only` and
`excluded_or_follow_on` targets, the field is required to be `null`; no artificial
reporting-family assignment is created for separately scored or non-primary targets.

#### 12.1.2 Decision roles

`decisionRole` uses exactly:

```text
blocking
monitored
deferred_resolution_only
excluded_or_follow_on
```

Every current operational target in the frozen profile maps to exactly one decision role.
`extract_and_evaluate` targets are `blocking`; `extract_and_monitor` targets are
`monitored`; `deferred_resolution` targets are `deferred_resolution_only`; and
`context_only`, `required_infrastructure`, `separate_follow_on_protocol`, `out_of_scope`,
and `audit_only` targets are `excluded_or_follow_on` for open semantic discovery. A
monitor batch may be promoted only under the pre-annotation rule in this document and the
frozen matching contract.

Descriptive reporting is an evaluation behavior for sparse individual targets or
insufficiently supported reporting families. It is not an exclusive target-level
`decisionRole` and cannot be used to bypass `INSUFFICIENT_SUPPORT`.

#### 12.1.3 Optional sampling strata

The five broader groupings introduced during methodological review are retained only as
optional `samplingStratum` values:

```text
core_discourse_nodes
scientific_entity_nodes
core_discourse_relations
entity_role_and_study_context_relations
measurement_context_relations
```

An operational target may have one of these values or `null`. Sampling strata may balance
unit selection, but they do not replace reporting families, govern the frozen family-level
F1 floor, merge node and relation reporting requirements, or hide weak performance in a
frozen reporting family.

Before final sample freeze, the mapping is validated against every current operational ID
in both `node_targets` and `relation_targets` in the frozen target profile. Every
operational target appears exactly once and has exactly one valid `decisionRole`. For
`blocking` and `monitored`, `reportingFamily` contains exactly one authorized value. For
`deferred_resolution_only` and `excluded_or_follow_on`, `reportingFamily` is `null`.
`samplingStratum` is optional for every target, contains at most one authorized value or
`null`, and has no metric or decision authority. Validation fails for a missing,
duplicate, or unknown operational ID and for any field value inconsistent with these
conditional rules.

## 13. Selection procedure

The final source-unit selection must be performed without access to model outputs.

The selection procedure is:

```text
1. materialize and validate all canonical source units;
2. apply eligibility and exclusion rules;
3. assign section and artifact descriptors;
4. route eligible target families;
5. construct a coverage matrix;
6. select calibration units;
7. select the reliability subset;
8. select the remaining evaluation set;
9. select the reserved diagnostic set;
10. verify that every fixed artifact contributes an eligible unit to `reliability` or
    `remaining_evaluation`;
11. verify reporting-family and optional sampling-stratum coverage;
12. freeze IDs, hashes, partitions, and rationales.
```

After step 12, a unit cannot move partitions. A pre-execution discovery that a selected
unit is unusable is an input-affecting change, not an informal replacement. No evaluation
unit may be added after model exposure to repair realized support.

Selection may use deterministic corpus statistics and expert reading of source text.

Selection may not use:

- model predictions;
- model confidence;
- prompt outcomes;
- validator outcomes for model candidates; or
- knowledge of which units appear easier for a particular model.

## 14. Calibration set

Calibration units are used to teach the annotation workflow and recurring distinctions.

Calibration units:

- are drawn from the fixed twelve-artifact population;
- are partitioned explicitly as `calibration`;
- are excluded from primary extraction metrics;
- are excluded from IAA unless later re-annotated independently after calibration;
- may be discussed jointly; and
- should contain representative but manageable examples.

They should include both screened likely positive cases and units screened as likely to
contain an exhaustive-empty unit-target case where available, and collectively exercise
the recurring distinctions in the frozen
annotation guideline: Model/Method/Algorithm/Tool, Finding/Conclusion,
ResearchProblem/ResearchGoal, use/mention/reference, EvaluationMetric/Parameter, node
versus edge evidence, atomicity, and uncertainty. Joint discussion is expected.
Calibration exposure is recorded at both unit and artifact level. Calibration units never
enter primary metrics; later independent re-annotation may be retained only as a training
quality record and does not move the unit out of the frozen calibration partition.

The screening expectation is not a calibration label or known gold fact. If a prospective
empty case is not realized, record the realized annotation result; do not replace the unit,
add a unit after model exposure, or reinterpret screening as gold.

The final record must list:

```text
calibrationSourceUnitIDs
selectionRationale
reportingFamiliesCovered
samplingStrataCovered
knownDifficulties
exposureRecordingPolicy
```

Exact unit IDs remain pending source-unit materialization.

## 15. Reliability subset

The reliability subset is annotated independently by at least two annotators.

It must be selected to cover:

```text
multiple artifacts
multiple section types
multiple target families
both node and relation annotation
at least one difficult semantic distinction
at least one source unit screened as likely to contain an exhaustive-empty unit-target case
distributed-evidence capability where likely
exact deterministic endpoints and relation direction where available
```

The matching contract determines the minimum support needed for meaningful IAA.

The final record must list:

```text
reliabilitySourceUnitIDs
annotatorAssignmentPolicy
eligibleTargetIDsPerUnit
completenessModePerUnit
artifactCoverage
sectionCoverage
targetCoverage
```

No reliability unit may be replaced after freeze. A newly discovered source-conversion
failure is reported against the frozen unit and triggers the applicable change-control
decision; it does not authorize migration or substitution inside the same frozen sample.

Reliability work is blind, independent, and completed before adjudication. Diagnostic
model runs cannot include reliability units or expose predictions to reliability
annotators. Selection seeks prospective support for the frozen node, relation, class,
direction, endpoint, and evidence-span IAA analyses across multiple artifacts and section
types without claiming their realized denominators in advance.

An expected empty case that is not realized remains in the frozen reliability subset. The
realized result is reported, and `INSUFFICIENT_SUPPORT` is used when the applicable
agreement analysis lacks support; the unit is not replaced and screening is not
reinterpreted as gold.

## 16. Remaining evaluation set

Each remaining evaluation unit receives:

1. one primary annotation; and
2. one independent expert second review against the canonical source.

The second review may:

```text
accept
identify_omission
identify_unsupported_annotation
route_to_adjudication
source_conversion_blocked
```

The second review is not counted as a second independent annotation for IAA.

The second reviewer works from the canonical source and a preserved read-only primary
annotation, records omissions and unsupported records separately, and routes disagreement
to adjudication. The primary record is never silently rewritten. The final assignment
policy must ensure that every artifact in the fixed twelve-artifact pool is represented in
the primary evaluation sample and receives two human reviews: either two blind annotations
for its reliability unit or a primary annotation plus independent expert second review
for its remaining-evaluation unit. An artifact may use either route and need not use both.

The final record must list:

```text
evaluationSourceUnitIDs
primaryAnnotatorAssignmentPolicy
secondReviewerAssignmentPolicy
eligibleTargetIDsPerUnit
completenessModePerUnit
```

The fields above are assignment-policy placeholders only. Named or pseudonymous IDs and
exact assignments belong exclusively to the later execution manifest.

## 17. Reserved diagnostic set

The diagnostic set is withheld from primary scoring.

It may be used only to:

- reproduce an observed error pattern;
- test a bounded correction during the single permitted revision cycle;
- diagnose parser, routing, context, or evidence failures; or
- determine whether a failure is local or systematic.

Diagnostic results must not be merged into primary pilot metrics.

Diagnostic units are frozen before model execution, unavailable during primary gold
annotation and initial prompt selection, and may be opened only after an error pattern is
observed in the primary run. They support only the single controlled revision cycle.
Original and revised diagnostic and evaluation runs remain separate, results are reported
separately, and diagnostic units can never migrate into calibration, reliability, or
remaining evaluation.

After an observed primary-run error authorizes diagnostic use, diagnostic units may
receive a separately versioned diagnostic annotation and expert review. Those records
support debugging only and never enter the primary gold, primary evaluation sample, or
primary metrics. Diagnostic annotations remain separate from calibration, reliability,
and remaining-evaluation annotations; original and revised diagnostic runs remain
separately versioned; and diagnostic labels cannot retroactively alter primary gold.
Diagnostic units cannot migrate into the primary evaluation sample.

The final record must list:

```text
diagnosticSourceUnitIDs
selectionRationale
allowedDiagnosticUses
```

## 18. Sample-size determination

Exact sample sizes are intentionally not frozen in this candidate draft.

They must be determined after the evaluation-matching contract defines:

- primary metric units;
- target-level minimum support;
- macro/micro aggregation;
- empty-gold treatment;
- IAA matching;
- GO/REVISE/NO-GO thresholds; and
- required error-analysis resolution.

The final sample must be prospectively designed to attempt the approved metrics while
remaining small enough to complete human annotation and adjudication without delaying
Study 2 unnecessarily. This design objective does not certify realized gold support.

Without prescribing an invented sample size, the final coverage audit must attempt to
materialize:

```text
at least 20 node records per annotator in the reliability subset
at least 10 relation records per annotator in the reliability subset
at least 20 detection-paired nodes for node-class agreement
at least 20 same-type paired edges for the direction-agreement gate
at least 20 paired assertions for evidence-span agreement
at least 10 gold instances for each predeclared blocking target family
enough attempted requests and parsed candidates to report every compliance denominator
```

These are support objectives from the matching contract, not guaranteed positive counts
and not permission to inspect model output during selection. A support objective that the
fixed artifact pool cannot supply is recorded as `INSUFFICIENT_SUPPORT` with artifact and
target-family counts; it is not manufactured by adding source units after model exposure.

Blinded screening must attempt likely coverage across enough artifacts and unit types to
make overall node IAA, relation IAA, evidence-span IAA, blocking-family interpretation,
and artifact-clustered uncertainty plausible. The fixed twelve-artifact pool does not by
itself guarantee any of those realized gold-dependent denominators. If a prospective
objective appears implausible before freeze, narrow the planned interpretation or record
the limitation; after freeze, use `INSUFFICIENT_SUPPORT` rather than changing evaluation
units. The only permitted calibration response is the guideline's controlled handbook
clarification, recalibration, and affected-reliability re-annotation under a new annotation
batch—not sample replacement.

Realized support is evaluated only after annotation:

```text
realized support sufficient
    Compute and interpret the corresponding metric under the frozen matching contract.

realized support insufficient
    Report INSUFFICIENT_SUPPORT.
    Do not replace frozen units.
    Do not add units after model exposure.
    Do not reinterpret screening expectations as gold.
```

The sample freeze certifies prospective design adequacy only. It does not certify realized
gold counts, target-family support, IAA denominators, or metric interpretability.

No sample-size value may be inserted solely because it was proposed in an earlier planning
conversation.

## 19. Deterministic context allowed during annotation

For each selected unit, the manifest must specify which frozen deterministic context is
visible to annotators.

Permitted context may include:

```text
Paper node
Section node
exact deterministic Dataset endpoint
exact deterministic Repository endpoint
exact deterministic Model or Tool endpoint
original deferred-record ID
existing deterministic citation or corrigendum relation
```

Deterministic context must be:

- source-specific;
- exact;
- frozen;
- labeled as deterministic; and
- distinct from model output.

Name-only similarity does not authorize an exact endpoint.

For every selected unit and exact endpoint, the selection manifest records:

```text
deterministicEndpointID
endpointClass
endpointProvenance
endpointSource
visibilityRoles:
  - annotation
  - model
  - adjudication
requiredForLinkExisting
deferredRecordID
readOnlyCitationOrCorrigendumContext
```

Visibility is role-specific. Exact endpoint context required for scoring is supplied
symmetrically to annotators and the model unless a predeclared task-specific reason is
recorded; adjudicators may additionally see preserved deterministic audit context.
Citation and corrigendum relations are read-only. Context may never contain model
predictions, validator findings about predictions, or name-only candidate links.

## 19.1 Prospective completeness assignment

Completeness is frozen at selected-unit/operational-target level using exactly:

```text
exhaustive
non_exhaustive_monitor
not_applicable
```

Every routed `extract_and_evaluate` unit-target pair is `exhaustive`. A routed
`extract_and_monitor` pair is `non_exhaustive_monitor` unless explicitly promoted to
`exhaustive` before annotation begins under the matching contract. Unrouted or ineligible
pairs are `not_applicable`. Section- or artifact-level declarations may be stored only as
auditable shorthand that expands deterministically to unit-target assignments. Absence is
scorable only for pairs predeclared `exhaustive`; missing annotations never imply
completeness. Routing must remain small enough for annotators to review every presented
target realistically.

## 20. Model input and later run binding

The frozen sample record binds the selected input material for every eventual model
request to:

```text
sourceArtifactID
primarySourceUnitID
primarySourceUnitTextHash
contextSourceUnitIDs
contextSourceUnitTextHashes
contextPolicyName
contextPolicyVersion
targetProfileVersion
targetProfileHash
sourceUnitContractVersion
sourceUnitContractHash
candidateSchemaVersion
candidateSchemaHash
evidenceContractVersion
evidenceContractHash
```

The sample record remains immutable after its own freeze. The model/reproducibility policy
is frozen separately and later, in the dependency order in Section 2. Before model
execution, the run or evaluation manifest binds:

```text
sampleFreezeVersion
sampleFreezeHash
modelPolicyVersion
modelPolicyHash
promptVersion
promptHash
```

Every eventual model request records those model-policy and prompt versions and hashes in
the run manifest. Adding this later binding does not require or permit modification of the
already frozen sample document.

## 21. Artifact and unit partition table

The following table is populated only after source-unit materialization and selection.

| Source artifact | Artifact role | Calibration units | Reliability units | Remaining evaluation units | Diagnostic units | Notes |
|---|---|---:|---:|---:|---:|---|
| 10 | regular primary publication | TBD | TBD | TBD | TBD | |
| 15 | regular primary publication | TBD | TBD | TBD | TBD | |
| 16 | regular primary publication | TBD | TBD | TBD | TBD | |
| 18 | regular primary publication | TBD | TBD | TBD | TBD | |
| 34 | regular primary publication | TBD | TBD | TBD | TBD | |
| 37 | regular primary publication | TBD | TBD | TBD | TBD | |
| 46 | regular primary publication | TBD | TBD | TBD | TBD | |
| 54 | regular primary publication | TBD | TBD | TBD | TBD | |
| 79 | regular primary publication | TBD | TBD | TBD | TBD | |
| 276 | regular primary publication | TBD | TBD | TBD | TBD | |
| 87 | primary publication in corrigendum pair | TBD | TBD | TBD | TBD | deterministic relation preserved |
| 87-corrigendum | corrigendum artifact | TBD | TBD | TBD | TBD | no LLM recreation of `corrects` |

## 22. Target-coverage matrix

The final freeze must include or reference a machine-readable matrix with one row per
selected source unit and at least:

```text
sourceArtifactID
sourceUnitID
sectionTitle
partition
eligibleNodeOperationalTargetIDs
eligibleRelationOperationalTargetIDs
completenessModeByTarget
deterministicContextByRole
evidenceGroupCapabilityRequired
expectedSpecialCondition
selectionRationale
screeningVersion
screeningStatus
likelyReportingFamilies
likelySamplingStrata
sourceConversionStatus
observedDeterministicMetadata
expectedSemanticCoverage
coverageStatus
primaryEvaluationRepresentationSatisfied
```

`evidenceGroupCapabilityRequired` records that the later annotation schema and interface
must support both `jointly_required` and `alternatives`; it does not predict which mode a
future gold assertion will use. Actual `goldEvidenceGroups`, their spans, and their modes
are created only during blinded annotation and adjudication. The candidate-output schema
is unchanged.

The matrix must distinguish observed deterministic metadata, expert-screened expected
semantic coverage, routed eligible targets, prospective completeness, deterministic
context, partition, and future realized gold support. Actual gold counts are not columns
in the frozen selection matrix; they belong to later annotation/evaluation outputs.
For every fixed artifact, `primaryEvaluationRepresentationSatisfied` is true only when at
least one eligible selected unit is assigned to `reliability` or `remaining_evaluation`;
calibration and `reserved_diagnostic` units do not satisfy it.

Recommended output:

```text
data/curation/publications/pilot1/
    publication_pilot1_target_coverage_matrix.csv
```

The matrix hash is recorded in this document before freeze.

## 23. Assignment policy and later assignment manifest

This sample freeze records the assignment policy but does not require named annotator
assignments.

The assignment policy must define:

```text
calibration assignment rule
reliability-subset independence rule
remaining-evaluation primary-annotation rule
independent expert second-review rule
adjudicator conflict-of-role rule
diagnostic-set access rule
```

After this sample record is frozen and before annotation begins, a separate execution
manifest must record:

```text
annotationBatchID
guidelineVersion
guidelineHash
matchingContractVersion
matchingContractHash
sampleFreezeVersion
sampleFreezeHash
sourceUnitInventoryHash
targetCoverageMatrixHash
sampleSelectionManifestHash
targetFamilyMappingHash
annotatorIDs
adjudicatorID
annotationCustodianID
calibrationAssignments
reliabilityAssignments
remainingEvaluationAssignments
secondReviewAssignments
diagnosticAssignments
```

Assignments must use pseudonymous annotator IDs in released artifacts.

Recommended later artifact:

```text
data/curation/publications/pilot1/
    publication_pilot1_annotation_assignment_manifest.json
```

The assignment manifest is an annotation-execution prerequisite, not a prerequisite for
freezing the sample itself.

## 24. Required sample-freeze artifacts

Before this document can be marked final, the following must exist:

```text
publication_pilot1_source_unit_inventory.jsonl
publication_pilot1_source_unit_manifest.json
publication_pilot1_target_coverage_matrix.csv
publication_pilot1_sample_selection_manifest.json
publication_pilot1_target_family_mapping.yaml
```

This document must record the SHA-256 of each.

The selection manifest is the authoritative join across selected and excluded unit IDs,
eligibility status, partition, exclusion reason, coverage dimensions, expected reporting
families and optional sampling strata,
unit-target routing and completeness, role-visible deterministic context, screening
provenance, sample-freeze version, and hashes. The coverage CSV is a reviewable projection;
it does not replace the manifest. The source-unit inventory remains the complete
population-level trace, including unselected and excluded units.

The selection manifest also records, for each fixed artifact, the eligible `reliability`
and/or `remaining_evaluation` unit IDs that satisfy primary-evaluation representation.
Calibration and `reserved_diagnostic` IDs are recorded separately and cannot satisfy that
requirement. The target-family mapping records `reportingFamily`, `decisionRole`, and
optional `samplingStratum` for every frozen-profile operational ID.

## 25. Pre-execution leakage controls

Before annotation begins:

- calibration, reliability, evaluation, and diagnostic partitions are frozen;
- annotators receive no model output;
- the model has not been executed on evaluation units;
- no model-specific prompt outcomes influence sample selection;
- deterministic context is explicitly listed;
- all source-unit hashes validate;
- all excluded units have predeclared reasons.

Before model execution begins:

- the initial gold is frozen;
- model/reproducibility policy is frozen;
- prompt package is frozen;
- every model request is bound to frozen input hashes.

## 26. Change control

After final freeze, changes are classified as:

```text
editorial
    No semantic or input change. Record a revision note; no reannotation, metric
    recomputation, or model rerun is required. A document hash change is propagated to
    downstream manifests without pretending that source inputs changed.

input_affecting
    Changes a selected unit, partition, context unit, target routing, or source hash.

method_affecting
    Changes a binding upstream contract.
```

An input-affecting change requires a sample document version increment, regenerated
selection/request manifests and hashes, reannotation and metric recomputation for affected
records, and rerunning every affected model request. It does not reopen the matching
contract unless the proposed change would alter matching semantics, thresholds, or
evaluation populations.

A method-affecting change requires a version increment to the changed frozen authority,
impact review across the complete sample, reannotation/recomputation/reruns wherever the
semantics or inputs changed, and reopening the matching contract when its own governed
rules are affected. Frozen-authority changes cannot be made through this candidate
document.

`input_affecting` and `method_affecting` changes require:

1. pause;
2. written rationale;
3. version increment;
4. regenerated manifests and hashes;
5. reassessment of annotations and metrics;
6. re-execution of affected model requests; and
7. explicit approval.

No category permits a silent source-unit replacement, partition migration, completeness
change, context change, canonical hash change, or model-result-driven resampling.

## 27. Candidate-completion checklist

This candidate draft is complete when:

- [x] the twelve-artifact pool is fixed;
- [x] pilot partitions are defined;
- [x] eligibility and exclusion rules are defined;
- [x] treatment-aware selection is defined;
- [x] leakage controls are defined;
- [x] required manifests and matrices are defined;
- [x] the dependency on the matching contract is explicit;
- [x] the evaluation-matching contract is final and binding;
- [ ] canonical source units are materialized;
- [ ] exact source-unit IDs are selected;
- [ ] calibration units are listed;
- [ ] reliability units are listed;
- [ ] remaining evaluation units are listed;
- [ ] diagnostic units are listed;
- [ ] prospective target and reporting-family coverage is verified;
- [ ] deterministic context is frozen per unit;
- [ ] the assignment policy is frozen;
- [ ] all sample and input hashes are recorded;
- [ ] no unresolved sampling contradiction remains.

## 28. Final freeze gate

This document may be marked final and binding only after:

- [ ] the evaluation-matching contract is frozen;
- [ ] source-unit materialization passes all validations;
- [ ] the selected sample is prospectively designed to support the approved metrics and
      thresholds, based on blinded screening, frozen coverage objectives, and the fixed
      twelve-artifact pool;
- [ ] every selected unit has a stable ID and hash;
- [ ] every partition is fixed;
- [ ] every fixed artifact contributes an eligible unit to `reliability` or
      `remaining_evaluation`;
- [ ] every selected unit has target-routing metadata;
- [ ] deterministic context is fixed;
- [ ] calibration units are excluded from primary metrics;
- [ ] the reliability subset is prospectively sufficient to attempt the approved IAA
      procedure without guaranteeing realized gold-dependent denominators;
- [ ] the assignment policy supports primary annotation and independent second review;
- [ ] diagnostic units are excluded from primary metrics;
- [ ] the target-coverage matrix is frozen;
- [ ] all upstream hashes remain unchanged;
- [ ] focused tests pass; and
- [ ] no model output influenced sample selection.

## 29. Acceptance statement

Passing the final freeze gate makes this document the binding Publication Pilot 1 sample
and input record.

Until that gate passes, this file is a candidate scaffold and must not be cited as evidence
that the sample, source units, annotation assignments, or model inputs are frozen.
