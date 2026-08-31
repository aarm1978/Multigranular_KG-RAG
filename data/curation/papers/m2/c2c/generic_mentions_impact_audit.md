# M2-C2C — Generic `mentions` ontology and operational impact audit

**AUDIT_ONLY · NO_ONTOLOGY_CHANGE · NO_SCREENING_CHANGE · NO_CALIBRATION_CHANGE · NO_MODEL_CALL**

Status: `researcher_review_pending`

## Current ontology

The frozen ontology contains 125 relations. This audit identifies 16 existing `mentionsX` relations across Publication, dataset, repository, and documentation modules. No generic `mentions` superproperty currently exists.

| ID | Relation | Domain | Range | Module | Strength |
|---|---|---|---|---|---|
| `C-P03` | `hasSubject` | `"Paper"` | `"Subject"` | `publication` | `metadata_or_consolidation_not_generic_mention` |
| `C-P05` | `reports` | `"Paper"` | `["Background", "Theme", "ResearchProblem", "ResearchQuestion", "ResearchGoal", "ResearchSignificance", "Definition", "TheoreticalBasis", "Method", "Experiment", "Examples", "Finding", "Discussion", "RelatedResearch", "Limitation", "Conclusion", "Contribution", "FutureWork", "Hypothesis", "Claim", "DataDescription"]` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P11` | `relatesTo` | `"RelatedResearch"` | `["Method", "TheoreticalBasis", "Concept", "ResearchProblem", "Paper"]` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P13` | `usesModel` | `["Paper", "Method"]` | `"ComputationalModel"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P14` | `appliesTo` | `"Method"` | `"ComputationalModel"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P15` | `usesTool` | `"Paper"` | `"Tool"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P16` | `mentionsVariable` | `["Paper", "DataDescription"]` | `"Variable"` | `publication` | `weak_explicit_mention` |
| `C-P17` | `studiesFeature` | `["Paper", "Method"]` | `"HydrologicFeature"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P18` | `studiesPlace` | `["Paper", "Method"]` | `"NamedPlace"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P19` | `hasSpatialCoverage` | `["Paper", "Place"]` | `"SpatialCoverage"` | `publication` | `metadata_or_consolidation_not_generic_mention` |
| `C-P20` | `usesDataset` | `"Paper"` | `["DatasetMention", "DatasetResource"]` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P23` | `mentionsModel` | `"Paper"` | `"ComputationalModel"` | `publication` | `weak_explicit_mention` |
| `C-P24` | `mentionsDataset` | `"Paper"` | `["DatasetMention", "DatasetResource"]` | `publication` | `weak_explicit_mention` |
| `C-P25` | `reportsMetric` | `["Finding", "Experiment"]` | `"EvaluationMetric"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P26` | `evaluates` | `"EvaluationMetric"` | `["ComputationalModel", "Method"]` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P27` | `hasParameter` | `["Method", "Experiment", "ComputationalModel"]` | `"Parameter"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P28` | `usesAlgorithm` | `"Method"` | `"Algorithm"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-P29` | `referencesDataset` | `"Paper"` | `"DatasetResource"` | `publication` | `explicit_reference_stronger_than_generic_mention` |
| `C-P30` | `mentionsConcept` | `"Paper"` | `"Concept"` | `publication` | `weak_explicit_mention` |
| `C-P31` | `mentionsTool` | `"Paper"` | `"Tool"` | `publication` | `weak_explicit_mention` |
| `C-P32` | `referencesRepository` | `"Paper"` | `"Repository"` | `publication` | `explicit_reference_stronger_than_generic_mention` |
| `C-P33` | `hasCodeRepository` | `"Paper"` | `"Repository"` | `publication` | `role_specific_stronger_than_generic_mention` |
| `C-D06` | `hasSubject` | `"DatasetResource"` | `"Subject"` | `dataset` | `metadata_or_consolidation_not_generic_mention` |
| `C-D07` | `hasSpatialCoverage` | `"DatasetResource"` | `"SpatialCoverage"` | `dataset` | `metadata_or_consolidation_not_generic_mention` |
| `C-D15` | `referencesFeature` | `"DatasetResource"` | `"HydrologicFeature"` | `dataset` | `explicit_reference_stronger_than_generic_mention` |
| `C-D16` | `containsVariable` | `"DatasetResource"` | `"Variable"` | `dataset` | `role_specific_stronger_than_generic_mention` |
| `C-D18` | `usesTool` | `"DatasetResource"` | `"Tool"` | `dataset` | `role_specific_stronger_than_generic_mention` |
| `C-D20` | `isExecutedBy` | `"DatasetResource"` | `"Tool"` | `dataset` | `role_specific_stronger_than_generic_mention` |
| `C-D21` | `executes` | `"Tool"` | `"DatasetResource"` | `dataset` | `role_specific_stronger_than_generic_mention` |
| `C-D23` | `mentionsConcept` | `"DatasetResource"` | `"Concept"` | `dataset` | `weak_explicit_mention` |
| `C-D24` | `mentionsTool` | `"DatasetResource"` | `"Tool"` | `dataset` | `weak_explicit_mention` |
| `C-D25` | `usesModel` | `"DatasetResource"` | `"ComputationalModel"` | `dataset` | `role_specific_stronger_than_generic_mention` |
| `C-D26` | `mentionsModel` | `"DatasetResource"` | `"ComputationalModel"` | `dataset` | `weak_explicit_mention` |
| `C-C11` | `usesTool` | `"Repository"` | `"Tool"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C12` | `mentionsVariable` | `"Repository"` | `"Variable"` | `repository` | `weak_explicit_mention` |
| `C-C15` | `usesDataset` | `"Repository"` | `"DatasetResource"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C16` | `implementsMethod` | `["Repository", "Tool"]` | `"Method"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C19` | `referencesDataset` | `"Repository"` | `"DatasetResource"` | `repository` | `explicit_reference_stronger_than_generic_mention` |
| `C-C20` | `describesAlgorithm` | `"Repository"` | `"Algorithm"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C21` | `usesModel` | `"Repository"` | `"ComputationalModel"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C22` | `mentionsTool` | `"Repository"` | `"Tool"` | `repository` | `weak_explicit_mention` |
| `C-C23` | `mentionsModel` | `"Repository"` | `"ComputationalModel"` | `repository` | `weak_explicit_mention` |
| `C-C24` | `usesParameter` | `"Repository"` | `"Parameter"` | `repository` | `role_specific_stronger_than_generic_mention` |
| `C-C25` | `mentionsParameter` | `"Repository"` | `"Parameter"` | `repository` | `weak_explicit_mention` |
| `C-C26` | `mentionsConcept` | `"Repository"` | `"Concept"` | `repository` | `weak_explicit_mention` |
| `C-C27` | `referencesRepository` | `"Repository"` | `"Repository"` | `repository` | `explicit_reference_stronger_than_generic_mention` |
| `C-DC04` | `hasSubject` | `"DocumentationPage"` | `"Subject"` | `documentation` | `metadata_or_consolidation_not_generic_mention` |
| `C-DC07` | `describesTool` | `"DocumentationPage"` | `"Tool"` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC08` | `mentionsConcept` | `"DocumentationPage"` | `"Concept"` | `documentation` | `weak_explicit_mention` |
| `C-DC11` | `hasParameter` | `["Procedure", "Step"]` | `"Parameter"` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC13` | `documents` | `"DocumentationPage"` | `"Repository"` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC14` | `referencesRepository` | `"DocumentationPage"` | `"Repository"` | `documentation` | `explicit_reference_stronger_than_generic_mention` |
| `C-DC15` | `referencesDataset` | `"DocumentationPage"` | `"DatasetResource"` | `documentation` | `explicit_reference_stronger_than_generic_mention` |
| `C-DC16` | `describesModel` | `"DocumentationPage"` | `"ComputationalModel"` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC17` | `catalogs` | `"DocumentationPage"` | `["Tool", "ComputationalModel"]` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC19` | `hasComponent` | `["Tool", "ComputationalModel"]` | `["Tool", "ComputationalModel"]` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `C-DC23` | `referencesFeature` | `"DocumentationPage"` | `"HydrologicFeature"` | `documentation` | `explicit_reference_stronger_than_generic_mention` |
| `C-DC24` | `mentionsModel` | `"DocumentationPage"` | `"ComputationalModel"` | `documentation` | `weak_explicit_mention` |
| `C-DC25` | `mentionsDataset` | `"DocumentationPage"` | `"DatasetResource"` | `documentation` | `weak_explicit_mention` |
| `C-DC27` | `describesDataset` | `"DocumentationPage"` | `"DatasetResource"` | `documentation` | `role_specific_stronger_than_generic_mention` |
| `D-16` | `consolidatesTo` | `"owl:Thing"` | `["ComputationalModel", "Tool", "Variable", "Concept", "HydrologicFeature", "EvaluationMetric", "Parameter", "Algorithm"]` | `global_cross_artifact` | `metadata_or_consolidation_not_generic_mention` |
| `D-22` | `implementedBy` | `["Tool", "ComputationalModel"]` | `"Repository"` | `global_cross_artifact` | `role_specific_stronger_than_generic_mention` |

## Domain and range audit

The bounded candidate range includes models and subtypes, tools, dataset mentions/resources, variables, concepts, hydrologic features and concrete subtypes, named places, metrics, parameters, algorithms, and repositories. It does not use `owl:Thing`.

The domain is not Paper-only. Existing ontology evidence supports Paper, Repository, DocumentationPage, and DatasetResource as artifact containers. All accepted Publication discourse classes have a clear containment-bound generic-mention meaning, while their stronger role-specific relations retain precedence.

## Operational options

Recommendation: `OPTION_B_PIPELINE_DERIVED_GENERIC_RELATION`.

Option A creates a new independent LLM edge and human relation decision. Option B derives the weak edge from accepted entity evidence and trusted provenance. Discourse-to-entity derivation additionally requires exact valid evidence containment; endpoint coexistence is never sufficient.

Generic edges should be fallback-only. Existing specialized `mentionsX` relations remain and may become subproperties; stronger accepted relations suppress explicit generic materialization.

## Screening recoverability

Of 267 completed human-screened units, 224 (83.895131%) have at least one previously screened node target inside the candidate generic range. 43 do not. 206 have multiple causing targets.

This is derived routing possibility, not new screening and not evidence that a mention exists. Option B does not require this routing augmentation.

## Calibration impact

Option A would introduce a relation decision in 14 of 16 frozen calibration units and therefore mismatches the instructions shown to annotators. Option B introduces no new annotator decision and does not require repeating calibration.

## DEV-SET-0 empirical impact

The 254 C1B candidates contain 129 model-authored entity candidates in the candidate range; 94 were authentically usable and 128 are usable under the diagnostic C2A title-only counterfactual. The latter support 128 potential Paper edges and 133 strict-containment discourse edges.

DEV-01 demonstrates the motivating gap: RelatedResearch evidence contains US Midwest, Great Lakes regions, coastal Southeast, Southwest, and California. A generic RelatedResearch-to-NamedPlace mention preserves that local context without asserting current-study `studiesPlace` semantics.

## Change surface and recommendation

Recommended design: `B_GENERIC_MENTIONS_AS_PIPELINE_DERIVED_RELATION`. It preserves all historical screening and calibration provenance, retains specialized mention relations, rejects a Paper-only domain, and controls graph inflation through fallback-only materialization and superproperty inference.

No ontology ID/version is assigned and no recommendation is implemented by this audit.
