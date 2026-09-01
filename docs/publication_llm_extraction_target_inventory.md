# Publication LLM Extraction Target Inventory — Final for Pilot 1

**Status:** final and binding for Publication Pilot 1
**Artifact family:** Scientific publications
**Source scope:** curated publication corpus
**Stage scope:** ontology-guided LLM semantic overlay over the frozen Phase B backbone
**Frozen ontology:** CIROH ontology 0.1.4
**Validated OWL SHA-256:** `7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635`
**Decision basis:** Ten-block publication target review plus approved pre-pilot ontology gate
**Date consolidated:** 2026-07-30


## 0. Approved pre-pilot gate dispositions

The following decisions are binding for Pilot 1:

1. `C-P08 testedBy` is active only for
   `Hypothesis → Method / Experiment`.
2. `TheoreticalBasis` remains extractable, but no grounding/basis edge is active in
   Pilot 1.
3. `C-P12` represents only `hasLimitation`; no `summary` relation is available.
4. `C-P09 supports` remains positive-only with its current formal domain/range.
5. No pre-pilot introduction/development relations are added for models or tools.
6. `EvaluationMetric` and `Parameter` remain contextual occurrences.
7. No `RepositoryMention` class is added; unresolved repository names remain provisional
   candidate-layer objects.
8. The remaining ontology observations are assigned to annotation/validator changes,
   post-pilot review, source-specific pilots, or the alignment/consolidation pilot.

This inventory is final against the formally frozen ontology 0.1.4 baseline and the
validated OWL SHA recorded above.

## 1. Purpose

This document is the operational inventory for the first ontology-guided LLM extraction
pilot over scientific publications. It translates the frozen ontology and the completed
target-review decisions into source-specific extraction responsibilities, pilot
treatments, evidence boundaries, and evaluation expectations.

It does **not** replace the authoritative ontology specification. When this inventory and
the formal ontology conflict, the formal ontology governs until a versioned ontology
change is approved. Any such conflict must also be entered in the companion ontology
observations register.

## 2. Authoritative inputs

The inventory should be interpreted together with:

- `src/ontology/ontology_spec.yaml`
- `docs/ontology_inventory.md`
- `docs/ontology_formalization.md`
- `docs/ontology_v0.1.md`
- `docs/llm_extraction_decisions.md`
- `docs/evaluation_decisions.md`
- `docs/publication_ontology_observations_register.md`
- `docs/handoffs/STUDY2_HANDOFF_DETERMINISTIC_TO_LLM_EXTRACTION.md` — historical
  deterministic-to-LLM handoff; superseded for current ontology and Publication Pilot 1
  status by this inventory and the ontology formalization record
- publication Phase A preprocessing contract
- publication Phase B extraction contract
- publication deterministic mapping
- frozen Phase A corpus and Phase B node/edge snapshot

The completed and frozen implementation contracts under this inventory are:

- [`publication_target_inventory.yaml`](../src/extraction/llm/publications/publication_target_inventory.yaml)
  — the final and binding machine-readable executable target profile;
- [`publication_source_unit_contract.md`](publication_source_unit_contract.md) — the
  final and binding canonical source-unit and request-context contract;
- [`publication_candidate_output.schema.json`](../schemas/publication_candidate_output.schema.json)
  — the final and binding candidate-output structure; and
- [`publication_evidence_validation_contract.md`](publication_evidence_validation_contract.md)
  — the final and binding validation contract.

The source-unit builder, request builder, parser, candidate/evidence validator, and
development extractor components are implemented. Production extraction has not been
executed.

## 3. Scope and non-goals

Pilot 1 evaluates local, evidence-grounded semantic extraction from publications. It does
not perform:

- global entity consolidation;
- `sameAs` or cross-source canonicalization;
- direct Neo4j writes;
- mutation of deterministic nodes or edges;
- DOI-less citation grounding;
- citation-intent extraction;
- fine-grained corrigendum alignment;
- visual figure interpretation;
- reconstruction of damaged tables;
- standalone mathematical interpretation;
- cross-source implementation or documentation linking.

## 4. Controlled operational vocabulary

### 4.1 Production responsibility

```text
deterministic
    Produced by reproducible rules or exact identifier resolution.

pipeline_generated
    Materialized automatically for evidence, provenance, hierarchy,
    parent-property expansion, or validation.

llm
    Semantically interpreted from publication text by the LLM.

hybrid
    The final assertion requires both LLM semantic interpretation and
    an indispensable deterministic resolver or pre-existing exact endpoint.

alignment_consolidation
    Produced later by comparing candidates across artifacts or sources.
```

**Interpretation rule:** validation, domain/range checking, local duplicate checking,
linking to an exact existing endpoint, and later consolidation do not by themselves make
an LLM target hybrid.

### 4.2 Pilot treatment

```text
context_only
    Available to the extractor but not re-extracted or scored as an LLM target.

required_infrastructure
    Required for evidence, provenance, hierarchy, validation, or graph assembly,
    but not scored as an independent semantic prediction.

extract_and_evaluate
    Extracted and included in the formal Pilot 1 evaluation when gold support permits.

extract_and_monitor
    Extracted in the same architecture but assessed through frequency, pooled metrics,
    agreement, case analysis, and error analysis when target-level support is sparse.

deferred_resolution
    Resolves exact endpoints or relations explicitly omitted or deferred by Phase B.

separate_follow_on_protocol
    Requires a methodologically distinct pilot or resolver.

out_of_scope
    Not attempted in the publication LLM pilot.

audit_only
    Preserved for lineage and error accounting; not reopened by the LLM.
```

## 5. Frozen global rules

### 5.1 Evidence

> **No supported evidence span means no accepted semantic assertion.**

Every candidate node and every non-derived candidate edge must have verifiable evidence in
the canonical source representation. Node evidence does not automatically support an edge.

### 5.2 Atomicity

```text
one node = one atomic semantic unit
```

A Paper may contain zero, one, or many nodes of the same class.

```text
same class + same meaning within one Paper
    → one locally reconciled node with multiple EvidenceSpans

same class + distinct meaning
    → separate nodes
```

### 5.3 Frozen backbone

The LLM overlay may add candidates and evidence but may not modify, delete, or silently
replace frozen Phase B nodes or edges.

### 5.4 Local identity

The pilot ends at locally reconciled, validated candidates. Name similarity alone never
authorizes global identity.

### 5.5 Abstract classes

`SoftwareEntity`, `ComputationalModel`, `Place`, and `HydrologicFeature` cannot be directly
instantiated. The LLM emits the most specific supported concrete type; superclass
membership is derived later.

### 5.6 Use, mention, and reference precedence

```text
actual use supported
    → usesModel / usesTool / usesDataset

only mention supported
    → mentionsModel / mentionsTool / mentionsDataset

formal dataset citation supported
    → referencesDataset

repository ownership/associated code supported
    → hasCodeRepository

only generic repository reference supported
    → referencesRepository
```

For the same Paper–Entity pair:

- `usesModel` supersedes `mentionsModel`;
- `usesTool` supersedes `mentionsTool`;
- `usesDataset` supersedes `mentionsDataset`;
- `usesDataset` and `referencesDataset` may coexist;
- `hasCodeRepository` is emitted as the specific relation and its
  `referencesRepository` parent may be derived.

### 5.7 Contextual metric and parameter instances

`EvaluationMetric` and `Parameter` represent contextual occurrences. Same-named metrics or
parameters are not merged when owner, experiment, condition, version, range, or value
differs.

Values, ranges, operators, intervals, and units remain exact source strings in Pilot 1.
No unapproved numeric normalization is introduced.

## 6. Inventory summary

### 6.1 Node operational rows by treatment

| Treatment | Operational rows |
| --- | --- |
| context_only | 9 |
| deferred_resolution | 2 |
| extract_and_evaluate | 19 |
| extract_and_monitor | 21 |
| out_of_scope | 5 |
| required_infrastructure | 5 |

### 6.2 Relation operational rows by treatment

| Treatment | Operational rows |
| --- | --- |
| context_only | 8 |
| deferred_resolution | 1 |
| extract_and_evaluate | 16 |
| extract_and_monitor | 10 |
| out_of_scope | 3 |
| required_infrastructure | 5 |
| separate_follow_on_protocol | 1 |

The row counts are operational rather than unique ontology-property counts because a
single ontology class or relation may have different treatments for different source,
domain, or resolution cases.

# 7. Node target inventory

| Ontology ID | Operational target | Kind | Production responsibility | Pilot treatment | Direct instantiation | Positive criterion | Boundary / note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A-PROV01 | EvidenceSpan | metadata | pipeline_generated | required_infrastructure | No | Materialized only after the proposed evidence text, source unit, and offsets pass literal verification. | The LLM proposes evidence coordinates; the pipeline creates the EvidenceSpan. Not scored as an entity-class prediction. |
| A-ID01 | Identifier | metadata | deterministic | context_only | Yes | Exact DOI, resource ID, canonical repository URL, ORCID, ROR, or other authorized identifier. | The LLM may quote an identifier literal but may not mint, repair, normalize, or merge identifiers. |
| A-AG01 / A-P03 | Person / Author | agent | deterministic | context_only | Yes | Publication authors already represented in the frozen Phase B backbone. | Body-text person extraction and cross-source person consolidation are outside Pilot 1. |
| A-AG02 | Organization | agent | deterministic | out_of_scope | Yes | Affiliation or funding organization recoverable through structured or rule-based parsing. | Current publication implementation gap; it must not be reassigned to the LLM merely because Phase B does not yet implement it. |
| A-P01 | Paper | artifact | deterministic | context_only | Yes | Curated source Paper and DOI-backed cited-paper stubs already represented by Phase B. | DOI-less and unresolved citation targets require a separate citation-grounding protocol. |
| A-P02 | Venue | metadata | deterministic | context_only | Yes | Publication venue already represented by Phase B. | Not re-extracted. |
| A-P04 | Subject | metadata | deterministic | context_only | Yes | Explicit publication keywords or subjects already represented by Phase B. | Concepts interpreted from prose are Concept, not generated Subject instances. |
| A-D09 | Award | metadata | deterministic | out_of_scope | Yes | Award or grant recoverable from structured funding evidence. | Publication deterministic implementation gap; not an LLM target. |
| A-DOM01 | SoftwareEntity | abstract domain class | pipeline_generated | required_infrastructure | No | Superclass membership derived from an accepted Tool or concrete ComputationalModel subtype. | The LLM may not emit SoftwareEntity as a final class. |
| A-DOM03 | ComputationalModel | abstract domain class | pipeline_generated | required_infrastructure | No | Superclass membership derived from ProcessBasedModel, ConceptualModel, StatisticalModel, or MLModel. | The LLM may not use ComputationalModel as a fallback for ambiguous subtype classification. |
| A-DOM06 | Place | abstract domain class | pipeline_generated | required_infrastructure | No | Superclass membership derived from HydrologicFeature or NamedPlace. | The LLM must emit a supported concrete subtype. |
| A-DOM07 | HydrologicFeature | abstract domain class | pipeline_generated | required_infrastructure | No | Superclass membership derived from Watershed, RiverReach, Gauge, WaterBody, Aquifer, or VPU. | The LLM may not emit HydrologicFeature directly. |
| A-P05 | Background | discourse | llm | extract_and_monitor | Yes | Atomic contextual statement that directly motivates the current study. | Exclude generic introduction text, detailed related work, the research gap, and the study goal. |
| A-P06 | Theme | discourse | llm | extract_and_monitor | Yes | Text-supported central thematic focus of the paper. | Monitor redundancy with title, Subject, Concept, and Background; do not create unsupported abstractive summaries. |
| A-P07 | ResearchProblem | discourse | llm | extract_and_evaluate | Yes | Explicit gap, deficiency, uncertainty, unresolved challenge, or problem addressed by the current study. | Exclude general importance, study limitations, and objectives. |
| A-P08 | ResearchQuestion | discourse | llm | extract_and_monitor | Yes | Explicit question or clearly interrogative declarative formulation addressed by the current study. | Do not rewrite every objective as a question; exclude rhetorical and future-work questions. |
| A-P09 | ResearchGoal | discourse | llm | extract_and_evaluate | Yes | Explicit aim, objective, or intended scientific action of the current paper. | Exclude goals of simulated agents, cited studies, software components, and future recommendations. |
| A-P10 | ResearchSignificance | discourse | llm | extract_and_monitor | Yes | Explicit statement of why this study, result, or contribution matters. | Background is general importance; Contribution is what was added. |
| A-P11 | Definition | discourse | llm | extract_and_monitor | Yes | Explicit statement establishing the meaning of a term, measure, method, or concept. | Exclude general explanations, procedure descriptions, and formulas without textual interpretation. |
| A-P12 | TheoreticalBasis | discourse | llm | extract_and_monitor | Yes | Theory, conceptual framework, or scientific principle that grounds the study, hypothesis, method, or interpretation. | Exclude mere theory mentions and applied procedures. No TheoreticalBasis grounding relation is declared in ontology 0.1.4. |
| A-P13 | Method | discourse | llm | extract_and_evaluate | Yes | Technique, procedure, or applied approach used to perform part of the current study. | A named reusable entity may instead be an Algorithm, Tool, or concrete model; the applied activity remains Method. |
| A-P14 | Experiment | discourse | llm | extract_and_evaluate | Yes | Delimited empirical or computational test combining data, methods/models, conditions, and evaluation. | Exclude a single technique, a data description, or an illustrative example without evaluation. |
| A-P15 | Examples | discourse | llm | extract_and_monitor | Yes | Single illustrative case, scenario, or application used to demonstrate an idea or procedure. | Exclude evaluated experiments and incidental phrases introduced by 'for example'. |
| A-P16 | Finding | discourse | llm | extract_and_evaluate | Yes | Empirical, computational, analytical, qualitative, negative, or null result produced by the current study. | Exclude goals, expectations, recommendations, and findings attributed only to cited work. |
| A-P17 | Discussion | discourse | llm | extract_and_monitor | Yes | Atomic interpretation or explanation of a result. | Finding states what was observed; Discussion explains why it occurred or what it implies. |
| A-P18 | RelatedResearch | discourse | llm | extract_and_monitor | Yes | Substantive description, comparison, or synthesis of prior research. | Exclude bare citations and bibliographic records; cited-Paper grounding is a separate protocol. |
| A-P19 | Limitation | discourse | llm | extract_and_evaluate | Yes | Explicit constraint, weakness, uncertainty, or boundary of the current study, method, experiment, data, or finding. | ResearchProblem predates and motivates the study; FutureWork proposes a later action. |
| A-P20 | Conclusion | discourse | llm | extract_and_evaluate | Yes | Study-level synthesis or general conclusion derived by the authors. | A repeated metric or result is still a Finding unless the text performs a higher-level synthesis. |
| A-P21 | Contribution | discourse | llm | extract_and_evaluate | Yes | What the study claims to have added to knowledge, evidence, method, infrastructure, or practice. | ResearchGoal is intended action; ResearchSignificance is why the contribution matters. |
| A-P22 | FutureWork | discourse | llm | extract_and_evaluate | Yes | Explicit future research activity proposed by the authors. | Exclude current-study goals, generic aspirations, and future actions of an experimental agent. |
| A-P23 | Hypothesis | discourse | llm | extract_and_monitor | Yes | Explicit, testable proposition that the current study intends to evaluate. | Do not infer a hypothesis from a question, objective, design, or expected result. |
| A-P24 | Claim | discourse | llm | extract_and_monitor | Yes | Argumentatively important proposition asserted by the authors but not necessarily a direct empirical result. | Not every declarative sentence is a Claim; avoid duplicate Claim and Conclusion nodes for the same unit. |
| A-P26 | DataDescription | discourse | llm | extract_and_evaluate | Yes | Atomic description of data origin, period, coverage, sample, resolution, variables, partition, or composition. | DatasetMention identifies a dataset; DataDescription explains its characteristics. |
| A-DOM02 | Tool — existing exact endpoint | domain | deterministic | context_only | Yes | Exact Tool already created from authorized deterministic evidence, such as a typed software DOI. | The LLM may link to it but must not duplicate or globally merge it. |
| A-DOM02 | Tool — new from publication prose | domain | llm | extract_and_evaluate | Yes | Software application, platform, package, or system used or mentioned in the paper. | A system that represents or predicts a scientific process may instead be a model. |
| A-DOM03a | ProcessBasedModel | domain | llm | extract_and_evaluate | Yes | Named computational model explicitly representing physical, hydrologic, hydraulic, or environmental processes. | Exclude the method applied to the model and auxiliary software used to run it. |
| A-DOM03b | ConceptualModel | domain | llm | extract_and_monitor | Yes | Named computational model using a simplified conceptual representation such as buckets or tanks. | Monitor ambiguous hybrid models and the boundary with ProcessBasedModel. |
| A-DOM03c | StatisticalModel | domain | llm | extract_and_monitor | Yes | Named statistical model with stable identity that can be implemented, compared, or reused as an entity. | Generic regression, estimation, copula fitting, or Bayesian analysis is normally Method. |
| A-DOM03d | MLModel | domain | llm | extract_and_evaluate | Yes | Data-driven model or trained architecture used, proposed, compared, or evaluated by the current study. | Training procedure is Method; optimization procedure may be Algorithm. |
| A-DOM13 | Algorithm | domain | llm | extract_and_monitor | Yes | Named, reusable computational procedure such as SCE-UA, DDS, or Adam. | Optimization, calibration, training, and regression without a named algorithm are Methods. |
| A-DOM11 | EvaluationMetric | domain | llm | extract_and_evaluate | Yes | Contextual metric occurrence used to evaluate a model or method, optionally with an explicit value. | Do not merge same-named metrics across different models, experiments, conditions, or values. |
| A-DOM12 | Parameter | domain | llm | extract_and_evaluate | Yes | Contextual value, coefficient, threshold, or configuration controlling a model, method, algorithm, or experiment. | Variable is observed/predicted; EvaluationMetric evaluates performance. Preserve value/range as exact strings. |
| A-DOM04 | Variable | domain | llm | extract_and_evaluate | Yes | Study-relevant measurable, observed, predicted, derived, or analyzed quantity or characteristic. | Exclude broad concepts, metrics, parameters, units, and variables appearing only incidentally in prior work. |
| A-D12 | Measurement | domain | llm | out_of_scope | Yes | Individual quantified observation of a variable. | Designed primarily for HydroShare; publication observations remain within Finding/DataDescription in Pilot 1. |
| A-P25 | DatasetMention — existing Phase B instance | domain | deterministic | context_only | Yes | Source-scoped dataset mention already produced by Phase B. | Do not recreate it. |
| A-P25 | DatasetMention — new from prose | domain | llm | extract_and_evaluate | Yes | Dataset named or described in publication prose without sufficient exact identity for DatasetResource. | Preserve source-scoped identity and version wording; do not promote by name alone. |
| A-D01 | DatasetResource — existing exact endpoint | artifact | deterministic | context_only | Yes | Dataset with exact DOI, HydroShare ID, canonical URL, or other authorized identity already resolved. | The LLM may link to it; a name-only mention remains DatasetMention. |
| A-D01 | DatasetResource — exact identifier omitted by Phase B | artifact | hybrid | deferred_resolution | Yes | LLM locates and interprets the role; deterministic resolver validates and creates/reuses the exact resource. | Not scored as ordinary open entity discovery. |
| A-C01 | Repository — existing exact endpoint | artifact | deterministic | context_only | Yes | Canonical repository URL already resolved by Phase B. | The LLM interprets its role but does not recreate the repository. |
| A-C01 | Repository — exact URL omitted by Phase B | artifact | hybrid | deferred_resolution | Yes | LLM identifies relevance; deterministic resolver normalizes and verifies owner/repository identity. | Retain unresolved if URL or role cannot be validated. |
| A-C01 | Repository — named without exact identity | artifact candidate | llm | extract_and_monitor | Yes | Text clearly refers to a repository but provides no exact canonical identity. | Keep a source-scoped provisional candidate; never merge globally by name alone. |
| A-DOM05 | Concept | domain | llm | extract_and_monitor | Yes | Specific scientific or technical notion substantively discussed and not better represented by another class. | Avoid generic nouns and indiscriminate terminology extraction; connect through mentionsConcept or authorized relations. |
| A-DOM07a | Watershed | hydrologic feature | llm | extract_and_evaluate | Yes | Basin, catchment, watershed, subbasin, or drainage-defined hydrologic unit relevant to the study. | A river is RiverReach; an administrative region is NamedPlace. |
| A-DOM07b | RiverReach | hydrologic feature | llm | extract_and_monitor | Yes | River, stream, flowpath, channel, or explicit reach/segment relevant to the study. | Distinguish the river from its watershed. |
| A-DOM07c | Gauge | hydrologic feature | llm | extract_and_monitor | Yes | Hydrologic monitoring or measurement station relevant to the study. | Preserve explicit station IDs; do not invent external IDs. |
| A-DOM07d | WaterBody | hydrologic feature | llm | extract_and_monitor | Yes | Lake, reservoir, bay, estuary, or other water body relevant to the study. | Regional references surrounding a water body may instead be NamedPlace. |
| A-DOM07e | Aquifer | hydrologic feature | llm | extract_and_monitor | Yes | Named or source-scoped aquifer or hydrogeologic system relevant to the study. | Likely low frequency in the publication pilot. |
| A-DOM07f | VPU | hydrologic feature | llm | extract_and_monitor | Yes | Explicit NHDPlus Vector Processing Unit. | Do not infer from generic 'region', 'unit', or 'processing area'. |
| A-DOM08 | NamedPlace | place | llm | extract_and_evaluate | Yes | Study-relevant named geographic area that is not better classified as a hydrologic feature. | Exclude affiliations, publisher locations, bibliography-only places, and incidental toponyms. |
| A-DOM09 | SpatialCoverage | geometry | deterministic | out_of_scope | Yes | Explicit geometry, bounding box, polygon, or coordinate extent. | The LLM may not invent geometry from a place name. |
| A-DOM10 | TemporalCoverage | temporal entity | deterministic | out_of_scope | Yes | Structured temporal coverage associated primarily with DatasetResource. | Publication periods remain in DataDescription/Experiment evidence because paper-level temporal roles are not modeled. |

# 8. Relation target inventory

| Ontology ID | Operational relation | Domain → Range | Production responsibility | Pilot treatment | Positive criterion | Boundary / note |
| --- | --- | --- | --- | --- | --- | --- |
| PROV-R1 | hasEvidence | Accepted node/edge → EvidenceSpan | pipeline_generated | required_infrastructure | Created only after evidence literal and offsets validate. | Not an independent LLM relation prediction. |
| PROV-R2 | wasExtractedBy | EvidenceSpan → prov:Activity | pipeline_generated | required_infrastructure | Created from run/model/prompt/schema metadata. | Not an independent LLM prediction. |
| ID-R1 / C-P04 | hasIdentifier | Entity/Paper → Identifier | deterministic | context_only | Exact authorized identifier link. | The LLM cannot mint, repair, or merge identifiers. |
| A-AG-R1 | affiliatedWith | Person → Organization | deterministic | out_of_scope | Publication affiliation parsing. | Implementation gap, not an LLM target. |
| A-AG-R2 | fundedBy | Paper → Award | deterministic | out_of_scope | Publication funding parsing. | Implementation gap, not an LLM target. An Award-to-funding-organization branch is not formally declared in ontology 0.1.4 and remains deferred outside Publication Pilot 1. |
| C-P01 | hasAuthor | Paper → Author | deterministic | context_only | Frozen Phase B author edge. | Not re-extracted. |
| C-P02 | publishedIn | Paper → Venue | deterministic | context_only | Frozen Phase B venue edge. | Not re-extracted. |
| C-P03 | hasSubject | Paper → Subject | deterministic | context_only | Frozen explicit keyword edge. | Not interchangeable with mentionsConcept. |
| C-P05 | reports | Paper → accepted discourse node | pipeline_generated | required_infrastructure | Derived from accepted discourse candidate provenance. | No independent edge span is required beyond the node evidence. |
| C-P06 | resolves | Method/Contribution/ResearchQuestion → ResearchProblem | llm | extract_and_evaluate | Explicitly addresses, responds to, fills, or resolves the stated problem. | Do not infer from co-occurrence; operational meaning is 'addresses', not necessarily complete solution. |
| C-P07 | produces | Method/Experiment → Finding | llm | extract_and_evaluate | Edge evidence explicitly links the procedure/test to the result. | Prefer Experiment→Finding when the result belongs to a combined experimental configuration. |
| C-P08 | testedBy — Hypothesis branch | Hypothesis → Method/Experiment | llm | extract_and_monitor | Explicit statement that the hypothesis is tested by the method or experiment. | Low frequency; do not infer the hypothesis. |
| C-P09 | supports | Finding/Claim → Claim/Conclusion | llm | extract_and_monitor | Explicit positive support, demonstration, or confirmation relation. | Do not infer from compatibility; Finding→Hypothesis and negative-support edges are not authorized. |
| C-P10 | discussesRelatedWork | Paper → RelatedResearch | pipeline_generated | required_infrastructure | Derived when a RelatedResearch node is accepted for the source Paper. | May coexist with the general reports edge. |
| C-P11 | relatesTo — local semantic target | RelatedResearch → Method/TheoreticalBasis/Concept/ResearchProblem | llm | extract_and_monitor | Substantive explicit connection to an accepted local target. | Avoid generic thematic co-occurrence. |
| C-P11 | relatesTo — cited Paper | RelatedResearch → cited Paper | hybrid | separate_follow_on_protocol | Requires semantic citation context plus bibliographic anchor resolution. | Typed citation grounding, not part of Pilot 1 primary metrics. |
| C-P12 | hasLimitation — Paper branch | Paper → Limitation | pipeline_generated | required_infrastructure | Derived from accepted Limitation provenance. | Not independently scored. |
| C-P12 | hasLimitation — Finding branch | Finding → Limitation | llm | extract_and_monitor | Evidence explicitly restricts or qualifies a particular Finding. | Do not attach every study limitation to every Finding. |
| C-P13 | usesModel — Paper branch | Paper → ComputationalModel subtype | llm | extract_and_evaluate | Model was trained, executed, calibrated, compared, evaluated, or otherwise used in the current study. | Use takes precedence over mentionsModel for the same pair. |
| C-P13 | usesModel — Method branch | Method → ComputationalModel subtype | llm | extract_and_monitor | Model functions as a component or resource of the Method. | Distinguish from appliesTo, where the model is the object of the operation. |
| C-P14 | appliesTo | Method → ComputationalModel subtype | llm | extract_and_evaluate | Method is applied to, configures, analyzes, explains, calibrates, or evaluates the model. | Do not emit both usesModel and appliesTo unless two roles are explicitly supported. |
| C-P15 | usesTool | Paper → Tool | llm | extract_and_evaluate | Tool was actually employed in the current study. | Use takes precedence over mentionsTool. |
| C-P16 | mentionsVariable | Paper/DataDescription → Variable | llm | extract_and_evaluate | Variable is relevant to the current study and explicitly observed, predicted, modeled, derived, or analyzed. | Prefer DataDescription as source when it locally contains the evidence. |
| C-P17 | studiesFeature — Paper branch | Paper → concrete HydrologicFeature | llm | extract_and_evaluate | Feature is a study object, domain, or hydrologic unit of analysis. | Do not use for affiliations or incidental locations. |
| C-P17 | studiesFeature — Method branch | Method → concrete HydrologicFeature | llm | extract_and_monitor | A specific Method is explicitly applied to the feature. | Do not derive automatically from Paper-level study area. |
| C-P18 | studiesPlace — Paper branch | Paper → NamedPlace | llm | extract_and_evaluate | NamedPlace is a study area, model domain, data coverage area, or result location. | Use studiesFeature for watersheds, rivers, gauges, water bodies, aquifers, and VPUs. |
| C-P18 | studiesPlace — Method branch | Method → NamedPlace | llm | extract_and_monitor | A specific Method is explicitly applied in the place. | Do not derive automatically from Paper-level location. |
| C-P19 | hasSpatialCoverage | Paper/Place → SpatialCoverage | deterministic | out_of_scope | Explicit structured geometry only. | No LLM-generated geometry. |
| C-P20 | usesDataset — existing Phase B edge | Paper → DatasetMention/DatasetResource | deterministic | context_only | Frozen Phase B data-use edge. | Not recreated. |
| C-P20 | usesDataset — new prose evidence | Paper → DatasetMention/DatasetResource | llm | extract_and_evaluate | Dataset was actually used for training, testing, forcing, analysis, observation, or benchmarking. | Use takes precedence over mentionsDataset; may coexist with referencesDataset. |
| C-P21 | cites | Paper → Paper | deterministic | context_only | Generic DOI-backed citation edge. | Typed citation semantics require a separate protocol. |
| C-P22 | corrects | Corrigendum Paper → original Paper | deterministic | context_only | Frozen generic corrigendum relation. | Fine-grained correction targets require a separate protocol. |
| C-P23 | mentionsModel | Paper → ComputationalModel subtype | llm | extract_and_evaluate | Model appears in background, related work, definition, comparison context, or future work without proof of use. | Do not retain alongside usesModel for the same pair. |
| C-P24 | mentionsDataset | Paper → DatasetMention/DatasetResource | llm | extract_and_evaluate | Dataset is discussed without proof of use or formal dataset citation. | Do not retain alongside usesDataset for the same pair. |
| C-P25 | reportsMetric | Finding/Experiment → EvaluationMetric | llm | extract_and_evaluate | Metric occurrence is explicitly reported by the Finding or Experiment. | Metric and endpoint must be contextually aligned, especially in tables. |
| C-P26 | evaluates | EvaluationMetric → ComputationalModel/Method | llm | extract_and_evaluate | Evidence identifies what the metric evaluates. | Textual proximity alone is insufficient. |
| C-P27 | hasParameter | Method/Experiment/ComputationalModel → Parameter | llm | extract_and_evaluate | Evidence identifies the parameter owner or experimental context. | Do not connect every parameter only to the Paper. |
| C-P28 | usesAlgorithm | Method → Algorithm | llm | extract_and_monitor | Method explicitly uses a named, reusable Algorithm. | No Paper→usesAlgorithm shortcut is created. |
| C-P29 | referencesDataset — existing Phase B edge | Paper → DatasetResource | deterministic | context_only | Formal bibliographic dataset reference already typed by Phase B. | Distinct from use and mention. |
| C-P29 | referencesDataset — exact omitted identifier | Paper → DatasetResource | hybrid | deferred_resolution | LLM identifies citation/reference role; deterministic resolver validates and types the exact dataset identity. | Not ordinary open discovery. |
| C-P30 | mentionsConcept | Paper → Concept | llm | extract_and_monitor | Specific concept is substantively discussed, defined, analyzed, or applied. | Weaker than hasSubject; avoid terminology flooding. |
| C-P31 | mentionsTool | Paper → Tool | llm | extract_and_evaluate | Tool is mentioned without proof of actual use. | Do not retain alongside usesTool for the same pair. |
| C-P32 | referencesRepository | Paper → Repository | llm | extract_and_monitor | Explicit repository reference without evidence that it is the associated code repository. | Stronger hasCodeRepository takes precedence. |
| C-P33 | hasCodeRepository | Paper → Repository | llm | extract_and_evaluate | Explicit evidence that the repository contains code, implementation, scripts, or workflow associated with the study. | Emit only this specific edge; referencesRepository may be derived as its parent property. |

# 9. Deferred and follow-on cases

| Operational case | Responsibility | Treatment | Pilot rule |
| --- | --- | --- | --- |
| Exact Paper→Repository role deferred by Phase B | hybrid | deferred_resolution | LLM classifies hasCodeRepository/referencesRepository/unsupported; deterministic endpoint is reused. |
| Exact Paper→Tool role deferred by Phase B | hybrid | deferred_resolution | LLM classifies usesTool/mentionsTool/unsupported; deterministic endpoint is reused. |
| Exact dataset or repository identifier omitted by Phase B | hybrid | deferred_resolution | LLM locates and interprets; deterministic resolver validates, normalizes, and creates/reuses endpoint. |
| Availability identifier with ambiguous semantic role | hybrid | deferred_resolution | Resolve only for pilot papers; allow remain_deferred, rejected, type_conflict, or unsupported_role. |
| Ambiguous or conflicting cited DOI type | hybrid | separate_follow_on_protocol | Requires provider metadata, bibliographic resolution, and adjudication. |
| DOI-less citation grounding | hybrid | separate_follow_on_protocol | Requires in-text anchor and reference-list resolution. |
| Typed citation grounding and citation intent | hybrid | separate_follow_on_protocol | Requires citation-context semantics plus bibliographic endpoint resolution. |
| Fine-grained corrigendum targeting | hybrid | separate_follow_on_protocol | Align corrected statement, Finding, Metric, Experiment, Parameter, or Conclusion with original paper. |
| Cross-source identity and consolidation | alignment_consolidation | separate_follow_on_protocol | Global identity, versions, sameAs-like decisions, and cross-source implementation/documentation relations. |

## 9.1 Phase B skipped and warning records

The following remain `audit_only` or `context_only`:

- self-reference citation skips;
- curated known exclusions;
- malformed DOI candidates;
- metadata conflicts and propagated warnings;
- rejected or unresolved DOI strings without an authorized deterministic correction.

The LLM may not repair identifiers from parametric memory or visual similarity.

# 10. Source-unit and evidence policy

## 10.1 Canonical unit

Each extraction unit must preserve at least:

```text
paperID
sectionID
sectionTitle
chunkNumber
text
startOffsetInSection
endOffsetInSection
sourceFile
inputHash
```

The extractor may receive a bounded section hierarchy, adjacent context, relevant
deterministic endpoints, and previously accepted local candidates when required for
cross-unit relations.

## 10.2 Canonical representation

The primary benchmark uses the same canonical Markdown representation supplied to the
model. The PDF may be used for conversion diagnosis, not to score information unavailable
to the extractor.

## 10.3 Tables, captions, and equations

- Correctly linearized tables are eligible.
- Partially recoverable tables support only unequivocal rows or cells.
- Broken table structure produces abstention.
- Self-contained caption text is eligible.
- Visual-only figure meaning is out of scope.
- Equation semantics are extracted only when supported by explanatory prose.
- Standalone mathematical reconstruction is out of scope.

# 11. Candidate actions and forbidden fields

## 11.1 Allowed entity actions

```text
propose_new
link_existing
```

`link_existing` requires an exact or locally unambiguous authorized endpoint. It does not
perform global consolidation.

## 11.2 Forbidden output behavior

```text
sameAs
mergeWith
consolidatesTo
global canonical ID
invented external identifier
Neo4j internal ID
direct database write
mutation of deterministic output
direct instantiation of abstract classes
```

# 12. Validation rules

A candidate is eligible for acceptance only when:

1. the ontology ID exists;
2. the class or relation is allowed in the publication target inventory;
3. abstract classes are not directly instantiated;
4. domain and range are valid;
5. endpoints exist or are valid candidates in the current local lifecycle;
6. evidence text occurs literally in the canonical source unit;
7. offsets are valid;
8. the source unit exists and matches its hash;
9. forbidden fields are absent;
10. no deterministic mutation is attempted;
11. local duplication rules are satisfied;
12. use/mention/reference precedence is satisfied.

# 13. Abstention and processing status

## 13.1 Semantic abstention reasons

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

## 13.2 Automatic rejection reasons

```text
evidence_not_literal
invalid_offsets
source_unit_not_found
unknown_ontology_id
abstract_class_instantiated
forbidden_field
endpoint_not_found
deterministic_mutation_attempt
```

## 13.3 Processing failures

```text
invalid_json
timeout
api_error
truncated_response
token_limit
retry_exhausted
```

Processing failures must not be counted as semantic abstentions or correct empty outputs.

# 14. Pilot sample boundary

The working sample contains eleven principal publications and one corrigendum:

```text
10, 15, 16, 18, 34, 37, 46, 54, 79, 276, 87, 87-corrigendum
```

The sample freeze must record the exact input files, hashes, Phase A and Phase B versions,
Marker version, ontology version, and snapshot date.

# 15. Evaluation mapping

## 15.1 Extract-and-evaluate targets

Where gold support permits:

- entity precision, recall, and F1;
- relation precision, recall, and F1;
- evidence validity;
- offset accuracy;
- schema and domain/range validity;
- unsupported-assertion rate;
- local linking accuracy;
- duplicate and incorrect-merge rates;
- use/mention/reference role accuracy;
- abstention appropriateness.

## 15.2 Extract-and-monitor targets

Use target frequency, pooled metrics, inter-annotator agreement, adjudicated examples,
error taxonomy, retrieval-path utility, and a post-pilot retain/revise/defer decision.
Do not report unstable target-level F1 from only a few positives.

## 15.3 Derived infrastructure

Pipeline-generated relations, superclass membership, and parent-property expansion are
validated as pipeline behavior but are not counted as independent LLM predictions.

# 16. Pre-pilot freeze checklist

Before implementation or benchmark annotation begins:

- [x] Complete the ontology observations gate.
- [x] Correct documentation/formalization inconsistencies in the 0.1.3 sources.
- [x] Approve and implement the minimal ontology 0.1.3 change.
- [x] Regenerate the OWL and pass the complete ontology-focused automated suite.
- [x] Complete authoritative manual HermiT validation and the technical ELK cross-check.
- [x] Freeze this inventory version.
- [x] Freeze the source-unit contract.
- [ ] Freeze the evidence-validation contract.
- [ ] Freeze output JSON schema.
- [ ] Freeze annotation and adjudication guidelines.
- [ ] Freeze evaluation matching rules and GO/REVISE/NO-GO thresholds.
- [ ] Freeze pilot sample and input hashes.
- [ ] Record model and reproducibility policy.

# 17. Acceptance statement

This document is the binding Publication Pilot 1 target inventory against formally
frozen ontology 0.1.4 and validated OWL SHA-256
`7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635`.
