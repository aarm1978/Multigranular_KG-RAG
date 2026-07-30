# Publication Ontology Observations Register — Final Pre-Pilot Register

**Status:** authoritative for Publication Pilot 1
**Artifact family:** Scientific publications
**Frozen ontology:** CIROH ontology 0.1.3
**Validated OWL SHA-256:** `ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57`
**Related document:** `publication_llm_extraction_target_inventory.md`
**Date consolidated:** 2026-07-30


## 0. Approved gate disposition summary

The pre-pilot gate assigned the following binding dispositions.

The source and documentation corrections below are implemented in ontology 0.1.3.
The authoritative HermiT gate completed successfully with consistency, zero
unsatisfiable named classes, and no execution errors; ontology 0.1.3 is formally frozen.
The ELK execution is retained only as a technical, profile-limited cross-check.

| Observation family | Approved disposition before Pilot 1 |
|---|---|
| `C-P08 testedBy` overload | **Ontology 0.1.3 change:** remove `TheoreticalBasis` from the domain; retain `Hypothesis → Method/Experiment` |
| `C-P12 summary` mismatch | **Documentation/formalization correction:** remove the unsupported summary branch; add no new property |
| `C-P09` missing Hypothesis/negative support | **Defer:** keep current positive support domain/range; collect cases |
| Model/tool introduction or development | **Defer:** record unrepresented cases; add no relation before the pilot |
| Metric and parameter concept/occurrence split | **Contract decision:** use contextual occurrences; add no classes before the pilot |
| Repository name without exact identity | **Candidate-layer decision:** source-scoped provisional candidate; add no `RepositoryMention` class |
| `usesModel` versus `appliesTo` | **Annotation/validator decision:** freeze functional discriminant and evaluate agreement |
| use/mention/reference precedence | **Validator decision:** stronger role suppresses weaker mention; dataset reference may coexist with use |
| asserted versus inferred types/properties | **Implementation decision:** preserve provenance distinction and do not score derived assertions as LLM output |
| Organization/Award/funding gap | **Deterministic and ontology review gap:** supported classes, affiliation, and Paper→Award funding remain outside the publication LLM pilot; Award→Organization is undeclared |
| Citation, corrigendum, numeric/unit, temporal, and cross-source needs | **Deferred:** separate follow-on or post-pilot review |

No other TBox expansion is authorized by this gate.

## 1. Purpose

This register records ontology, formalization, documentation, annotation, and
implementation observations identified while reviewing the publication extraction target
universe.

An entry in this register does not automatically justify an ontology change. The register
exists to prevent three opposite errors:

1. silently ignoring a known representational problem;
2. changing the ontology prematurely without corpus evidence;
3. changing the ontology during a comparable pilot run without versioning and rerunning
   affected cases.

## 2. Decision policy

### 2.1 Pre-pilot gate

Before Pilot 1, resolve issues that:

- make a core target impossible to represent;
- create a contradiction between the formal ontology and the operational contract;
- prevent valid domain/range checking;
- make human annotation and model output structurally incompatible;
- would invalidate the planned primary metrics.

A pre-pilot resolution may be:

```text
documentation_fix
annotation_guideline
extraction_contract_change
validator_change
ontology_version_change
defer_to_post_pilot
reject_change
```

### 2.2 Freeze during a comparable pilot run

After freezing ontology, target inventory, annotation guide, prompt, schema, validators,
sample, and evaluation rules, no silent ontology change is permitted.

A blocking defect discovered during execution requires:

```text
pause
→ document
→ approve versioned correction
→ update gold/contracts
→ rerun all affected cases
```

### 2.3 Post-pilot review

Non-blocking observations are reconsidered using:

- observed frequency;
- annotator agreement;
- extraction precision/recall;
- unsupported assertion rate;
- confusion patterns;
- duplication and graph-degree effects;
- retrieval-path utility;
- implementation cost;
- cross-source evidence from later pilots.

## 3. Severity interpretation

```text
blocking
    Pilot cannot validly represent or evaluate a core target.

pre-pilot correction required
    Documentation, annotation, schema, validator, or TBox must be corrected before freeze.

non-blocking
    Current conservative treatment permits a valid pilot.

implementation gap
    Ontology is adequate, but deterministic or pipeline implementation is incomplete.

separate follow-on protocol
    Methodologically different task requiring its own sample, contract, and evaluation.
```

## 4. Final gate disposition

The ten-block review did **not** identify a mandatory TBox expansion required to execute the
core publication pilot. It did identify several required pre-pilot corrections to
documentation, annotation guidance, candidate schema, and validator behavior.

The pre-pilot gate approved and ontology 0.1.3 implemented one TBox change: narrowing `C-P08 testedBy` to a `Hypothesis`-only domain. All other candidate ontology expansions are deferred or resolved through documentation, contracts, annotation guidance, candidate-layer rules, or validators. The final disposition is:

1. the `summary` documentation/formalization mismatch is corrected;
2. the Hypothesis-only `testedBy` property is formally frozen;
3. document source-specific production responsibility;
4. freeze usesModel/appliesTo and use/mention/reference discrimination;
5. freeze contextual occurrence policies for metrics and parameters;
6. distinguish provisional from exact repository identity;
7. distinguish asserted from inferred types and parent properties.

## 5. Summary register

| ID | Observation | Category | Affected targets | Preliminary severity | Current Pilot 1 treatment | Required pre-pilot action | Evidence needed after pilot | Candidate resolution | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OBS-PUB-001 | C-P12 documentation claims a Conclusion-to-Finding summary branch that is not formally declared | formalization/documentation inconsistency | C-P12 hasLimitation; Conclusion; Finding | pre-pilot correction required; non-blocking for current extraction | Do not emit Conclusion→Finding summary. Extract Conclusion and Finding separately. | Correct the narrative inventory, notes, and operational docs so they do not present summary as an available C-P12 branch. | Measure whether explicit conclusion-to-finding links are frequent and useful. | Removed the unsupported summary branch from current documentation and notes; no relation added. | implemented_pre_pilot |
| OBS-PUB-002 | C-P08 testedBy overloads theoretical grounding and hypothesis testing | semantic property overload | C-P08; TheoreticalBasis; Hypothesis; Method; Experiment | non-blocking; annotation risk | Extract only Hypothesis→testedBy→Method/Experiment. The TheoreticalBasis branch is out of scope. | Document the active branch explicitly in the target inventory and annotation guide. | Collect examples of theoretical grounding, operationalization, and direct theory testing. | Narrowed `testedBy` to a Hypothesis-only domain; grounding remains deferred. | implemented_pre_pilot |
| OBS-PUB-003 | C-P09 supports does not allow Finding-to-Hypothesis support | domain/range expressivity gap | C-P09; Finding; Hypothesis | non-blocking for Pilot 1 | Do not materialize Finding→supports→Hypothesis; retain nodes and textual evidence. | Include a specific unrepresentable-case label in annotation/adjudication notes. | Measure frequency and whether the relation is required by competency questions or retrieval paths. | Extend the range of supports to Hypothesis or add a hypothesis-specific relation. | deferred_to_post_pilot |
| OBS-PUB-004 | No formal negative support or refutation relation | argumentation expressivity gap | C-P09 supports; Finding; Claim; Conclusion; Hypothesis | non-blocking for Pilot 1 | Represent non-support, contradiction, or rejection in Finding/Discussion/Conclusion text; do not invert supports. | Ensure prompt and annotation guide prohibit positive supports edges for negative evidence. | Measure frequency and polarity ambiguity. | Add notSupports/refutes/contradicts or a formally modeled polarity attribute. | deferred_to_post_pilot |
| OBS-PUB-005 | Method usesModel and Method appliesTo may overlap | relation discrimination | C-P13; C-P14; Method; ComputationalModel | pre-pilot guideline required | usesModel = model as component/resource; appliesTo = model as object of operation. | Add matched positive/negative examples and adjudication rules; prohibit duplicate edges from the same evidence unless roles differ. | Evaluate annotator agreement and confusion matrix. | Clarify definitions, introduce subproperties, or retire one branch if the distinction is not reproducible. | accepted_for_contract_implementation |
| OBS-PUB-006 | No publication relation specifically represents introducing or developing a model/tool | relation expressivity gap | Paper; Tool; ComputationalModel; usesModel; usesTool; mentionsModel; mentionsTool; D-23 describedInPaper | non-blocking but potentially important | Use usesX only when actual use is supported; otherwise use mentionsX and flag an unrepresented introduction/development role. | Add an adjudication note so ownership or novelty is not silently converted into use. | Collect frequency and retrieval use cases for introduced/developed artifacts. | Add introducesModel/introducesTool/develops or a typed introduces relation; evaluate whether describedInPaper is sufficient. | deferred_to_post_pilot |
| OBS-PUB-007 | mentionsVariable is weaker than the operational study-relevance criterion | property naming and operational semantics | C-P16; Variable; DataDescription | pre-pilot documentation required | Extract only variables observed, predicted, modeled, derived, compared, or analyzed by the current study. | Freeze relevance criteria and prefer DataDescription as the local source when available. | Assess whether role-specific variable relations are needed. | Retain mentionsVariable with stronger documentation, or add inputVariable/targetVariable/measuresVariable/derivesVariable roles. | accepted_for_contract_implementation |
| OBS-PUB-008 | hasCodeRepository requires a reproducible ownership/association threshold | relation discrimination | C-P32 referencesRepository; C-P33 hasCodeRepository; Repository | pre-pilot guideline required | Use hasCodeRepository only for explicit associated implementation, source code, scripts, or reproducibility statements. | Create positive, negative, and ambiguous examples; define precedence over referencesRepository. | Measure role-classification agreement and false cross-artifact connections. | Clarify ontology notes or add narrower subproperties if repository roles remain heterogeneous. | accepted_for_contract_implementation |
| OBS-PUB-009 | Compound and hybrid models lack a frozen typing policy | class modeling and annotation | A-DOM03a/b/c/d; ComputationalModel; Method; Tool; Algorithm | pre-pilot guideline required | Decompose explicit components; type named composite entity by the best-supported concrete subtype; abstain when unsupported. | Create adjudication examples for multi-component and multi-typed systems; prohibit abstract fallback. | Assess frequency and whether multiple typing or a CompositeModel pattern is needed. | Permit justified multiple concrete types, introduce component relations, or add a composite/hybrid model construct. | accepted_for_contract_implementation |
| OBS-PUB-010 | EvaluationMetric conflates metric type and contextual metric occurrence | class granularity | A-DOM11; C-P25; C-P26 | non-blocking; contract workaround required | Create contextual metric occurrences distinguished by model, method, experiment, condition, and value. | Freeze occurrence-level identity and local reconciliation rules. | Assess duplication, alignment, and need for querying metric definitions separately from reported results. | Separate MetricType from MetricObservation/MetricResult, or formalize a metric occurrence pattern. | accepted_for_contract_implementation |
| OBS-PUB-011 | Parameter conflates parameter concept and contextual parameter setting | class granularity | A-DOM12; C-P27 | non-blocking; contract workaround required | Create contextual Parameter instances distinguished by owner, configuration, range, and value. | Freeze owner-aware identity and local reconciliation rules. | Assess cross-source matching between paper parameters, code configuration, and documentation. | Separate ParameterDefinition from ParameterSetting/ParameterValue or formalize a configuration pattern. | accepted_for_contract_implementation |
| OBS-PUB-012 | Metric and parameter values lack formal unit/operator/interval/uncertainty structure | datatype expressivity gap | EvaluationMetric; Parameter; value; range | non-blocking for Pilot 1 | Preserve values, ranges, units, inequalities, and intervals as exact source strings. | Prohibit invented normalization and numeric comparison claims. | Determine whether Study 3 queries require numeric filtering or comparison. | Adopt QUDT/OM/PropertyValue patterns or add structured fields for unit, operator, lower/upper bounds, and uncertainty. | deferred_to_post_pilot |
| OBS-PUB-013 | No paper-level temporal coverage relation or temporal-role model | relation expressivity gap | A-DOM10 TemporalCoverage; DataDescription; Experiment; Paper | non-blocking | Retain periods in DataDescription, Experiment, or Finding evidence; do not instantiate publication TemporalCoverage. | Document TemporalCoverage as out of scope for publication LLM extraction. | Collect cases for observation, training, validation, simulation, and projection periods. | Add paper/data-description temporal relations with role typing, or keep temporal information textual. | deferred_to_post_pilot |
| OBS-PUB-014 | Measurement is not connected to the publication discourse model | cross-module scope question | A-D12 Measurement; Variable; Finding; DataDescription | non-blocking | Measurement is out of scope for publications; quantitative observations remain in Finding/DataDescription. | No ontology change required for Pilot 1. | Review jointly with the HydroShare pilot and assess cross-source observation linking. | Retain Measurement only in the dataset module or add a formal observation pattern usable across sources. | deferred_to_cross_source_review |
| OBS-PUB-015 | No RepositoryMention class for unresolved repository names | identity and mention modeling | A-C01 Repository; C-P32; C-P33 | non-blocking; identity risk | Use a source-scoped provisional Repository candidate without global merge. | Ensure candidate schema distinguishes provisional identity from exact Repository endpoints. | Measure frequency and false-match risk. | Add RepositoryMention, adopt a generic Mention pattern, or keep provisional Repository only in the candidate layer. | accepted_for_contract_implementation |
| OBS-PUB-016 | Dataset version, subset, and derivative semantics are not fully modeled | identity and versioning | DatasetMention; DatasetResource; usesDataset; mentionsDataset; referencesDataset | non-blocking for local extraction | Preserve exact wording and source-scoped identity; do not merge CAMELS variants or versions by name. | Add negative examples for version/subset confusion. | Evaluate during dataset and cross-source alignment pilots. | Add version/subset/derivedFrom relations or a dataset-version pattern. | deferred_to_cross_source_review |
| OBS-PUB-017 | Concept extraction may produce high-volume, low-discrimination nodes | target utility and granularity | A-DOM05 Concept; C-P30 mentionsConcept; C-P11 relatesTo | non-blocking; monitor | Extract only specific, substantively discussed concepts not covered by a more precise class. | Freeze restricted positive/negative criteria. | Measure annotation agreement, graph degree, redundancy, and retrieval utility. | Restrict the class, retain only linked concepts, add controlled normalization, or omit publication Concept population. | deferred_to_post_pilot |
| OBS-PUB-018 | RelatedResearch relatesTo is broad and may generate low-value edges | relation granularity and utility | C-P11; RelatedResearch; Method; TheoreticalBasis; Concept; ResearchProblem | non-blocking; monitor | Require a substantive explicit connection to an already accepted local target. | Add strong negative examples for thematic co-occurrence. | Measure edge precision, degree, and retrieval contribution. | Replace or supplement relatesTo with typed subrelations. | deferred_to_post_pilot |
| OBS-PUB-019 | DOI-less and typed citation grounding require a separate method | methodological boundary | C-P21 cites; C-P11 RelatedResearch→Paper; cited Paper identity | not a Pilot 1 blocker | Keep generic DOI-backed citations as deterministic context; exclude typed and DOI-less grounding. | Ensure reference sections are excluded from ordinary semantic entity extraction. | Design a separate benchmark using in-text anchors, bibliography records, provider metadata, and semantic citation context. | Potentially add typed citation subproperties only after the grounding protocol is validated. | separate_follow_on_protocol |
| OBS-PUB-020 | Fine-grained corrigendum semantics are not represented | correction/provenance expressivity gap | C-P22 corrects; Finding; EvaluationMetric; Parameter; Experiment; Conclusion | not a Pilot 1 blocker | Retain generic 87-corrigendum→corrects→87 and extract local corrigendum semantics without targeted correction edges. | No TBox change required for Pilot 1. | Design a paired-document alignment protocol and collect correction types. | Add correctsFinding, replacesMetricValue, revisesExperiment, invalidatesConclusion, or a generic correction-event pattern. | separate_follow_on_protocol |
| OBS-PUB-021 | Publication Organization, Award, affiliation, and Paper-to-Award funding are ontology-supported but not implemented in publication Phase B; Award-to-funding-organization linkage is not formally declared | deterministic implementation and ontology review gap | A-AG02; A-D09; A-AG-R1; A-AG-R2 | non-blocking for LLM Pilot 1 | Keep the entire publication funding family out of scope; do not transfer responsibility to the LLM. | Record both the implementation gap and undeclared branch explicitly in the target inventory. | Plan a versioned deterministic publication enrichment and ontology review if required by competency questions. | Later deterministic and ontology review; no Pilot 1 change. | implementation_gap |
| OBS-PUB-022 | Global ontology extraction labels can be confused with source-specific production responsibility | documentation semantics | Parameter, DatasetMention, DatasetResource, Repository, Tool, models, and other classes marked hybrid globally | pre-pilot correction required | The publication inventory uses source_scope=publications and stage_scope=llm_semantic_overlay. | Add an explicit note that ontology extraction metadata is global/descriptive, while production responsibility is source- and stage-specific. | Apply the same convention to Hub, GitHub, and HydroShare inventories. | Add source-specific extraction profiles outside the TBox rather than changing class semantics. | accepted_for_contract_implementation |
| OBS-PUB-023 | Asserted and inferred superclass or parent-property memberships need provenance separation | reasoning and graph materialization | SoftwareEntity; ComputationalModel; Place; HydrologicFeature; hasCodeRepository; referencesRepository | pre-pilot implementation policy required | LLM emits the concrete class/specific property; pipeline derives ancestors or parent properties. | Define assertedType versus inferredType and ensure derived assertions are not scored as LLM predictions. | Evaluate Neo4j materialization strategy and query performance. | No TBox change necessarily required; add provenance/materialization metadata. | accepted_for_contract_implementation |
| OBS-PUB-024 | Use/mention/reference precedence must be enforced consistently | operational relation policy | usesModel/mentionsModel; usesTool/mentionsTool; usesDataset/mentionsDataset/referencesDataset | pre-pilot guideline and validator required | Use supersedes mention; formal dataset reference may coexist with use. | Add candidate reconciliation and conflict-validation rules. | Evaluate role-classification confusion and duplicate weaker edges. | Ontology structure is currently adequate; revise only if roles remain irreducibly ambiguous. | accepted_for_contract_implementation |
| OBS-PUB-025 | Theme, Background, and ResearchSignificance may be redundant for retrieval | target utility | A-P05; A-P06; A-P10; Subject; Concept; title/abstract text | non-blocking; monitor | Extract under restricted criteria and monitor frequency, redundancy, agreement, and retrieval utility. | Do not impose a cardinality, but flag excessive counts and near-duplicates. | Retain, constrain, or omit each target based on evidence rather than ontology availability alone. | Likely a target-scope decision rather than a TBox change. | deferred_to_post_pilot |

# 6. Detailed observation records


## OBS-PUB-001 — C-P12 documentation claims a Conclusion-to-Finding summary branch that is not formally declared

- **Category:** formalization/documentation inconsistency
- **Affected targets:** C-P12 hasLimitation; Conclusion; Finding
- **Preliminary severity:** pre-pilot correction required; non-blocking for current extraction
- **Status:** `implemented_pre_pilot`

### Observed issue

C-P12 documentation claims a Conclusion-to-Finding summary branch that is not formally declared.

### Current Pilot 1 treatment

Do not emit Conclusion→Finding summary. Extract Conclusion and Finding separately.

### Required pre-pilot action

Correct the narrative inventory, notes, and operational docs so they do not present summary as an available C-P12 branch.

### Evidence required after the pilot

Measure whether explicit conclusion-to-finding links are frequent and useful.

### Implemented pre-pilot resolution

The unsupported summary branch was removed from current documentation and notes. No
summary relation was added.

## OBS-PUB-002 — C-P08 testedBy overloads theoretical grounding and hypothesis testing

- **Category:** semantic property overload
- **Affected targets:** C-P08; TheoreticalBasis; Hypothesis; Method; Experiment
- **Preliminary severity:** non-blocking; annotation risk
- **Status:** `implemented_pre_pilot`

### Observed issue

C-P08 testedBy overloads theoretical grounding and hypothesis testing.

### Current Pilot 1 treatment

Extract only Hypothesis→testedBy→Method/Experiment. The TheoreticalBasis branch is out of scope.

### Required pre-pilot action

Document the active branch explicitly in the target inventory and annotation guide.

### Evidence required after the pilot

Collect examples of theoretical grounding, operationalization, and direct theory testing.

### Implemented pre-pilot resolution

Ontology 0.1.3 narrowed `testedBy` to a Hypothesis-only domain. TheoreticalBasis
grounding remains deferred pending corpus evidence, and no replacement relation was
added.

## OBS-PUB-003 — C-P09 supports does not allow Finding-to-Hypothesis support

- **Category:** domain/range expressivity gap
- **Affected targets:** C-P09; Finding; Hypothesis
- **Preliminary severity:** non-blocking for Pilot 1
- **Status:** `deferred_to_post_pilot`

### Observed issue

C-P09 supports does not allow Finding-to-Hypothesis support.

### Current Pilot 1 treatment

Do not materialize Finding→supports→Hypothesis; retain nodes and textual evidence.

### Required pre-pilot action

Include a specific unrepresentable-case label in annotation/adjudication notes.

### Evidence required after the pilot

Measure frequency and whether the relation is required by competency questions or retrieval paths.

### Candidate resolution

Extend the range of supports to Hypothesis or add a hypothesis-specific relation.

## OBS-PUB-004 — No formal negative support or refutation relation

- **Category:** argumentation expressivity gap
- **Affected targets:** C-P09 supports; Finding; Claim; Conclusion; Hypothesis
- **Preliminary severity:** non-blocking for Pilot 1
- **Status:** `deferred_to_post_pilot`

### Observed issue

No formal negative support or refutation relation.

### Current Pilot 1 treatment

Represent non-support, contradiction, or rejection in Finding/Discussion/Conclusion text; do not invert supports.

### Required pre-pilot action

Ensure prompt and annotation guide prohibit positive supports edges for negative evidence.

### Evidence required after the pilot

Measure frequency and polarity ambiguity.

### Candidate resolution

Add notSupports/refutes/contradicts or a formally modeled polarity attribute.

## OBS-PUB-005 — Method usesModel and Method appliesTo may overlap

- **Category:** relation discrimination
- **Affected targets:** C-P13; C-P14; Method; ComputationalModel
- **Preliminary severity:** pre-pilot guideline required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Method usesModel and Method appliesTo may overlap.

### Current Pilot 1 treatment

usesModel = model as component/resource; appliesTo = model as object of operation.

### Required pre-pilot action

Add matched positive/negative examples and adjudication rules; prohibit duplicate edges from the same evidence unless roles differ.

### Evidence required after the pilot

Evaluate annotator agreement and confusion matrix.

### Candidate resolution

Clarify definitions, introduce subproperties, or retire one branch if the distinction is not reproducible.

## OBS-PUB-006 — No publication relation specifically represents introducing or developing a model/tool

- **Category:** relation expressivity gap
- **Affected targets:** Paper; Tool; ComputationalModel; usesModel; usesTool; mentionsModel; mentionsTool; D-23 describedInPaper
- **Preliminary severity:** non-blocking but potentially important
- **Status:** `deferred_to_post_pilot`

### Observed issue

No publication relation specifically represents introducing or developing a model/tool.

### Current Pilot 1 treatment

Use usesX only when actual use is supported; otherwise use mentionsX and flag an unrepresented introduction/development role.

### Required pre-pilot action

Add an adjudication note so ownership or novelty is not silently converted into use.

### Evidence required after the pilot

Collect frequency and retrieval use cases for introduced/developed artifacts.

### Candidate resolution

Add introducesModel/introducesTool/develops or a typed introduces relation; evaluate whether describedInPaper is sufficient.

## OBS-PUB-007 — mentionsVariable is weaker than the operational study-relevance criterion

- **Category:** property naming and operational semantics
- **Affected targets:** C-P16; Variable; DataDescription
- **Preliminary severity:** pre-pilot documentation required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

mentionsVariable is weaker than the operational study-relevance criterion.

### Current Pilot 1 treatment

Extract only variables observed, predicted, modeled, derived, compared, or analyzed by the current study.

### Required pre-pilot action

Freeze relevance criteria and prefer DataDescription as the local source when available.

### Evidence required after the pilot

Assess whether role-specific variable relations are needed.

### Candidate resolution

Retain mentionsVariable with stronger documentation, or add inputVariable/targetVariable/measuresVariable/derivesVariable roles.

## OBS-PUB-008 — hasCodeRepository requires a reproducible ownership/association threshold

- **Category:** relation discrimination
- **Affected targets:** C-P32 referencesRepository; C-P33 hasCodeRepository; Repository
- **Preliminary severity:** pre-pilot guideline required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

hasCodeRepository requires a reproducible ownership/association threshold.

### Current Pilot 1 treatment

Use hasCodeRepository only for explicit associated implementation, source code, scripts, or reproducibility statements.

### Required pre-pilot action

Create positive, negative, and ambiguous examples; define precedence over referencesRepository.

### Evidence required after the pilot

Measure role-classification agreement and false cross-artifact connections.

### Candidate resolution

Clarify ontology notes or add narrower subproperties if repository roles remain heterogeneous.

## OBS-PUB-009 — Compound and hybrid models lack a frozen typing policy

- **Category:** class modeling and annotation
- **Affected targets:** A-DOM03a/b/c/d; ComputationalModel; Method; Tool; Algorithm
- **Preliminary severity:** pre-pilot guideline required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Compound and hybrid models lack a frozen typing policy.

### Current Pilot 1 treatment

Decompose explicit components; type named composite entity by the best-supported concrete subtype; abstain when unsupported.

### Required pre-pilot action

Create adjudication examples for multi-component and multi-typed systems; prohibit abstract fallback.

### Evidence required after the pilot

Assess frequency and whether multiple typing or a CompositeModel pattern is needed.

### Candidate resolution

Permit justified multiple concrete types, introduce component relations, or add a composite/hybrid model construct.

## OBS-PUB-010 — EvaluationMetric conflates metric type and contextual metric occurrence

- **Category:** class granularity
- **Affected targets:** A-DOM11; C-P25; C-P26
- **Preliminary severity:** non-blocking; contract workaround required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

EvaluationMetric conflates metric type and contextual metric occurrence.

### Current Pilot 1 treatment

Create contextual metric occurrences distinguished by model, method, experiment, condition, and value.

### Required pre-pilot action

Freeze occurrence-level identity and local reconciliation rules.

### Evidence required after the pilot

Assess duplication, alignment, and need for querying metric definitions separately from reported results.

### Candidate resolution

Separate MetricType from MetricObservation/MetricResult, or formalize a metric occurrence pattern.

## OBS-PUB-011 — Parameter conflates parameter concept and contextual parameter setting

- **Category:** class granularity
- **Affected targets:** A-DOM12; C-P27
- **Preliminary severity:** non-blocking; contract workaround required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Parameter conflates parameter concept and contextual parameter setting.

### Current Pilot 1 treatment

Create contextual Parameter instances distinguished by owner, configuration, range, and value.

### Required pre-pilot action

Freeze owner-aware identity and reconciliation rules.

### Evidence required after the pilot

Assess cross-source matching between paper parameters, code configuration, and documentation.

### Candidate resolution

Separate ParameterDefinition from ParameterSetting/ParameterValue or formalize a configuration pattern.

## OBS-PUB-012 — Metric and parameter values lack formal unit/operator/interval/uncertainty structure

- **Category:** datatype expressivity gap
- **Affected targets:** EvaluationMetric; Parameter; value; range
- **Preliminary severity:** non-blocking for Pilot 1
- **Status:** `deferred_to_post_pilot`

### Observed issue

Metric and parameter values lack formal unit/operator/interval/uncertainty structure.

### Current Pilot 1 treatment

Preserve values, ranges, units, inequalities, and intervals as exact source strings.

### Required pre-pilot action

Prohibit invented normalization and numeric comparison claims.

### Evidence required after the pilot

Determine whether Study 3 queries require numeric filtering or comparison.

### Candidate resolution

Adopt QUDT/OM/PropertyValue patterns or add structured fields for unit, operator, lower/upper bounds, and uncertainty.

## OBS-PUB-013 — No paper-level temporal coverage relation or temporal-role model

- **Category:** relation expressivity gap
- **Affected targets:** A-DOM10 TemporalCoverage; DataDescription; Experiment; Paper
- **Preliminary severity:** non-blocking
- **Status:** `deferred_to_post_pilot`

### Observed issue

No paper-level temporal coverage relation or temporal-role model.

### Current Pilot 1 treatment

Retain periods in DataDescription, Experiment, or Finding evidence; do not instantiate publication TemporalCoverage.

### Required pre-pilot action

Document TemporalCoverage as out of scope for publication LLM extraction.

### Evidence required after the pilot

Collect cases for observation, training, validation, simulation, and projection periods.

### Candidate resolution

Add paper/data-description temporal relations with role typing, or keep temporal information textual.

## OBS-PUB-014 — Measurement is not connected to the publication discourse model

- **Category:** cross-module scope question
- **Affected targets:** A-D12 Measurement; Variable; Finding; DataDescription
- **Preliminary severity:** non-blocking
- **Status:** `deferred_to_cross_source_review`

### Observed issue

Measurement is not connected to the publication discourse model.

### Current Pilot 1 treatment

Measurement is out of scope for publications; quantitative observations remain in Finding/DataDescription.

### Required pre-pilot action

No ontology change required for Pilot 1.

### Evidence required after the pilot

Review jointly with the HydroShare pilot and assess cross-source observation linking.

### Candidate resolution

Retain Measurement only in the dataset module or add a formal observation pattern usable across sources.

## OBS-PUB-015 — No RepositoryMention class for unresolved repository names

- **Category:** identity and mention modeling
- **Affected targets:** A-C01 Repository; C-P32; C-P33
- **Preliminary severity:** non-blocking; identity risk
- **Status:** `accepted_for_contract_implementation`

### Observed issue

No RepositoryMention class for unresolved repository names.

### Current Pilot 1 treatment

Use a source-scoped provisional Repository candidate without global merge.

### Required pre-pilot action

Ensure candidate schema distinguishes provisional identity from exact Repository endpoints.

### Evidence required after the pilot

Measure frequency and false-match risk.

### Candidate resolution

Add RepositoryMention, adopt a generic Mention pattern, or keep provisional Repository only in the candidate layer.

## OBS-PUB-016 — Dataset version, subset, and derivative semantics are not fully modeled

- **Category:** identity and versioning
- **Affected targets:** DatasetMention; DatasetResource; usesDataset; mentionsDataset; referencesDataset
- **Preliminary severity:** non-blocking for local extraction
- **Status:** `deferred_to_cross_source_review`

### Observed issue

Dataset version, subset, and derivative semantics are not fully modeled.

### Current Pilot 1 treatment

Preserve exact wording and source-scoped identity; do not merge CAMELS variants or versions by name.

### Required pre-pilot action

Add negative examples for version/subset confusion.

### Evidence required after the pilot

Evaluate during dataset and cross-source alignment pilots.

### Candidate resolution

Add version/subset/derivedFrom relations or a dataset-version pattern.

## OBS-PUB-017 — Concept extraction may produce high-volume, low-discrimination nodes

- **Category:** target utility and granularity
- **Affected targets:** A-DOM05 Concept; C-P30 mentionsConcept; C-P11 relatesTo
- **Preliminary severity:** non-blocking; monitor
- **Status:** `deferred_to_post_pilot`

### Observed issue

Concept extraction may produce high-volume, low-discrimination nodes.

### Current Pilot 1 treatment

Extract only specific, substantively discussed concepts not covered by a more precise class.

### Required pre-pilot action

Freeze restricted positive/negative criteria.

### Evidence required after the pilot

Measure annotation agreement, graph degree, redundancy, and retrieval utility.

### Candidate resolution

Restrict the class, retain only linked concepts, add controlled normalization, or omit publication Concept population.

## OBS-PUB-018 — RelatedResearch relatesTo is broad and may generate low-value edges

- **Category:** relation granularity and utility
- **Affected targets:** C-P11; RelatedResearch; Method; TheoreticalBasis; Concept; ResearchProblem
- **Preliminary severity:** non-blocking; monitor
- **Status:** `deferred_to_post_pilot`

### Observed issue

RelatedResearch relatesTo is broad and may generate low-value edges.

### Current Pilot 1 treatment

Require a substantive explicit connection to an already accepted local target.

### Required pre-pilot action

Add strong negative examples for thematic co-occurrence.

### Evidence required after the pilot

Measure edge precision, degree, and retrieval contribution.

### Candidate resolution

Replace or supplement relatesTo with typed subrelations.

## OBS-PUB-019 — DOI-less and typed citation grounding require a separate method

- **Category:** methodological boundary
- **Affected targets:** C-P21 cites; C-P11 RelatedResearch→Paper; cited Paper identity
- **Preliminary severity:** not a Pilot 1 blocker
- **Status:** `separate_follow_on_protocol`

### Observed issue

DOI-less and typed citation grounding require a separate method.

### Current Pilot 1 treatment

Keep generic DOI-backed citations as deterministic context; exclude typed and DOI-less grounding.

### Required pre-pilot action

Ensure reference sections are excluded from ordinary semantic entity extraction.

### Evidence required after the pilot

Design a separate benchmark using in-text anchors, bibliography records, provider metadata, and semantic citation context.

### Candidate resolution

Potentially add typed citation subproperties only after the grounding protocol is validated.

## OBS-PUB-020 — Fine-grained corrigendum semantics are not represented

- **Category:** correction/provenance expressivity gap
- **Affected targets:** C-P22 corrects; Finding; EvaluationMetric; Parameter; Experiment; Conclusion
- **Preliminary severity:** not a Pilot 1 blocker
- **Status:** `separate_follow_on_protocol`

### Observed issue

Fine-grained corrigendum semantics are not represented.

### Current Pilot 1 treatment

Retain generic 87-corrigendum→corrects→87 and extract local corrigendum semantics without targeted correction edges.

### Required pre-pilot action

No TBox change required for Pilot 1.

### Evidence required after the pilot

Design a paired-document alignment protocol and collect correction types.

### Candidate resolution

Add correctsFinding, replacesMetricValue, revisesExperiment, invalidatesConclusion, or a generic correction-event pattern.

## OBS-PUB-021 — Publication funding has both an implementation gap and an undeclared agency branch

- **Category:** deterministic implementation gap
- **Affected targets:** A-AG02; A-D09; A-AG-R1; A-AG-R2
- **Preliminary severity:** non-blocking for LLM Pilot 1
- **Status:** `implementation_gap`

### Observed issue

The `Organization` and `Award` classes, `Person` → `Organization` affiliation, and
`Paper`/`DatasetResource` → `Award` funding are formally supported. Publication Phase B
does not implement those publication facts. Ontology 0.1.3 does not formally declare an
`Award` → funding `Organization` relation; the A-AG-R2 `funding_agency` note is
non-logical. Dataset-module C-D09 separately permits direct `DatasetResource` →
`Organization` behavior and does not establish the missing Award branch.

### Current Pilot 1 treatment

Keep the entire publication funding family out of scope; do not transfer responsibility
to the LLM.

### Required pre-pilot action

Record the implementation gap and undeclared Award-to-Organization branch explicitly in
the target inventory.

### Evidence required after the pilot

Plan a versioned deterministic publication enrichment and ontology review if required by
competency questions.

### Candidate resolution

Any future publication funding addition requires later deterministic and ontology review;
no change is authorized for Pilot 1.

## OBS-PUB-022 — Global ontology extraction labels can be confused with source-specific production responsibility

- **Category:** documentation semantics
- **Affected targets:** Parameter, DatasetMention, DatasetResource, Repository, Tool, models, and other classes marked hybrid globally
- **Preliminary severity:** pre-pilot correction required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Global ontology extraction labels can be confused with source-specific production responsibility.

### Current Pilot 1 treatment

The publication inventory uses source_scope=publications and stage_scope=llm_semantic_overlay.

### Required pre-pilot action

Add an explicit note that ontology extraction metadata is global/descriptive, while production responsibility is source- and stage-specific.

### Evidence required after the pilot

Apply the same convention to Hub, GitHub, and HydroShare inventories.

### Candidate resolution

Add source-specific extraction profiles outside the TBox rather than changing class semantics.

## OBS-PUB-023 — Asserted and inferred superclass or parent-property memberships need provenance separation

- **Category:** reasoning and graph materialization
- **Affected targets:** SoftwareEntity; ComputationalModel; Place; HydrologicFeature; hasCodeRepository; referencesRepository
- **Preliminary severity:** pre-pilot implementation policy required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Asserted and inferred superclass or parent-property memberships need provenance separation.

### Current Pilot 1 treatment

LLM emits the concrete class/specific property; pipeline derives ancestors or parent properties.

### Required pre-pilot action

Define assertedType versus inferredType and ensure derived assertions are not scored as LLM predictions.

### Evidence required after the pilot

Evaluate Neo4j materialization strategy and query performance.

### Candidate resolution

No TBox change necessarily required; add provenance/materialization metadata.

## OBS-PUB-024 — Use/mention/reference precedence must be enforced consistently

- **Category:** operational relation policy
- **Affected targets:** usesModel/mentionsModel; usesTool/mentionsTool; usesDataset/mentionsDataset/referencesDataset
- **Preliminary severity:** pre-pilot guideline and validator required
- **Status:** `accepted_for_contract_implementation`

### Observed issue

Use/mention/reference precedence must be enforced consistently.

### Current Pilot 1 treatment

Use supersedes mention; formal dataset reference may coexist with use.

### Required pre-pilot action

Add candidate reconciliation and conflict-validation rules.

### Evidence required after the pilot

Evaluate role-classification confusion and duplicate weaker edges.

### Candidate resolution

Ontology structure is currently adequate; revise only if roles remain irreducibly ambiguous.

## OBS-PUB-025 — Theme, Background, and ResearchSignificance may be redundant for retrieval

- **Category:** target utility
- **Affected targets:** A-P05; A-P06; A-P10; Subject; Concept; title/abstract text
- **Preliminary severity:** non-blocking; monitor
- **Status:** `deferred_to_post_pilot`

### Observed issue

Theme, Background, and ResearchSignificance may be redundant for retrieval.

### Current Pilot 1 treatment

Extract under restricted criteria and monitor frequency, redundancy, agreement, and retrieval utility.

### Required pre-pilot action

Do not impose a cardinality, but flag excessive counts and near-duplicates.

### Evidence required after the pilot

Retain, constrain, or omit each target based on evidence rather than ontology availability alone.

### Candidate resolution

Likely a target-scope decision rather than a TBox change.


# 7. Future ontology-change checklist

For any later ontology change proposal, record:

- final severity;
- gate decision;
- responsible document or code owner;
- affected ontology IDs;
- affected annotation examples;
- affected validators;
- whether a new ontology version is required;
- whether OWL regeneration is required;
- whether authoritative HermiT validation and a technical ELK cross-check must be rerun;
- whether pilot inputs or gold annotations must be regenerated;
- final status and decision date.

## 8. Versioning rule

If the TBox changes before Pilot 1:

1. increment the ontology version;
2. update `ontology_spec.yaml`;
3. update ontology inventory and formalization documents;
4. regenerate the OWL artifact;
5. rerun unit tests;
6. rerun HermiT;
7. rerun ELK cross-check;
8. record commit and SHA-256;
9. update the target inventory and annotation guide;
10. freeze the new baseline before benchmark annotation or extraction.

If only documentation or operational contracts change, record that no TBox axiom changed.

## 9. Post-pilot disposition vocabulary

```text
implemented_pre_pilot
retained_without_change
documentation_only
accepted_for_contract_implementation
accepted_for_post_pilot_revision
deferred_to_source_specific_pilot
deferred_to_alignment_pilot
rejected_after_evidence
superseded
```

`accepted_for_contract_implementation` means the semantic decision is closed, but it
must still be encoded in the Publication Pilot 1 contracts, annotation guide, candidate
schema, adjudication rules, or validators.

## 10. Acceptance statement

This is the authoritative Publication Pilot 1 ontology observations register against
formally frozen ontology 0.1.3 and validated OWL SHA-256
`ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57`.
New observations discovered during annotation or implementation must receive a new
stable ID rather than being inserted silently into an existing decision.
