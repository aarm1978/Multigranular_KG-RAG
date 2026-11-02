# Publication DEV-SET-0 Node Request Plan v0.1.0

Status: `approved_for_development`

This is a prospective applicability plan, not semantic extraction, annotation, gold, or evaluation.
No source prose, keyword rule, embedding, LLM, network request, or historical DEV-04 answer was used.

## Policy conclusion

Frozen authorities establish the Publication scope, active target metadata, and absence of a binding narrower applicability restriction. Researcher-approved extraction-policy decision `C0-POLICY-DECISION-001` supplies the prospective consequence that all 40 direct LLM node targets remain universally eligible in `open_discovery`. Four exact-existing context targets require exact deterministic endpoint bindings; two resolver-mediated targets are `deferred_resolution` only.
Universal eligibility is not asserted to be a frozen ontology axiom or a literal target-inventory rule, and it does not assert that any target instance exists in a unit.

Policy SHA-256: `4919da6a72e68117f8bc1dab0abfa65b3c45e38f61254eb52152168111e51e82`
Target audit SHA-256: `efa483e960bed9dfccf40e4d0ce5f3526d24f745bf97309ffa6ed00252b28049`
Plan SHA-256: `7f6642cd93033c04f59fbb92ebbb4a899fe7a9f2fe68f424a463beee87836928`

## DEV-SET-0 plan

| Development ID | Source unit | Section role | Channel | Eligible nodes | Deterministic-context excluded | Deferred-only excluded | Unresolved |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| DEV-01 | `pub:17:sec:0007:unit:0001` | introduction | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-02 | `pub:17:sec:0033:unit:0001` | other | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-03 | `pub:36:sec:0020:unit:0001` | data | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-04 | `pub:36:sec:0026:unit:0001` | results | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-05 | `pub:219:sec:0003:unit:0001` | methods | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-06 | `pub:219:sec:0008:unit:0001` | results | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-07 | `pub:243:sec:0003:unit:0001` | introduction | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-08 | `pub:243:sec:0013:unit:0001` | other | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-09 | `pub:270:sec:0005:unit:0001` | other | `open_discovery` | 40 | 4 | 2 | 0 |
| DEV-10 | `pub:270:sec:0010:unit:0001` | conclusion | `open_discovery` | 40 | 4 | 2 | 0 |

All ten units use inclusion rules `C0-NODE-SOURCE-001`, `C0-NODE-OPEN-001`, and `C0-NODE-OPEN-002`.
Every deterministic exclusion is bound to the exact rule IDs recorded in the JSON plan.

## Target-by-target audit

| Operational target | Ontology class | Emission mode | Actions | Channels | Status | Rule IDs |
| --- | --- | --- | --- | --- | --- | --- |
| `PUB-N-A-C01-REPOSITORY-EXACT-URL-OMITTED-BY-PHASE-B` | A-C01 / Repository | `resolver_mediated_candidate` | propose_new, link_existing | deferred_resolution | `DEFERRED_ONLY` | C0-NODE-DEFERRED-001, C0-NODE-DEFERRED-002 |
| `PUB-N-A-C01-REPOSITORY-EXISTING-EXACT-ENDPOINT` | A-C01 / Repository | `deterministic_context` | link_existing | open_discovery | `DETERMINISTICALLY_APPLICABLE` | C0-NODE-SOURCE-001, C0-NODE-CONTEXT-001, C0-NODE-CONTEXT-002 |
| `PUB-N-A-C01-REPOSITORY-NAMED-WITHOUT-EXACT-IDENTITY` | A-C01 / Repository | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B` | A-D01 / DatasetResource | `resolver_mediated_candidate` | propose_new, link_existing | deferred_resolution | `DEFERRED_ONLY` | C0-NODE-DEFERRED-001, C0-NODE-DEFERRED-002 |
| `PUB-N-A-D01-DATASETRESOURCE-EXISTING-EXACT-ENDPOINT` | A-D01 / DatasetResource | `deterministic_context` | link_existing | open_discovery | `DETERMINISTICALLY_APPLICABLE` | C0-NODE-SOURCE-001, C0-NODE-CONTEXT-001, C0-NODE-CONTEXT-002 |
| `PUB-N-A-DOM02-TOOL-EXISTING-EXACT-ENDPOINT` | A-DOM02 / Tool | `deterministic_context` | link_existing | open_discovery | `DETERMINISTICALLY_APPLICABLE` | C0-NODE-SOURCE-001, C0-NODE-CONTEXT-001, C0-NODE-CONTEXT-002 |
| `PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE` | A-DOM02 / Tool | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | A-DOM03a / ProcessBasedModel | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM03B-CONCEPTUALMODEL` | A-DOM03b / ConceptualModel | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM03C-STATISTICALMODEL` | A-DOM03c / StatisticalModel | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM03D-MLMODEL` | A-DOM03d / MLModel | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM04-VARIABLE` | A-DOM04 / Variable | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM05-CONCEPT` | A-DOM05 / Concept | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07A-WATERSHED` | A-DOM07a / Watershed | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07B-RIVERREACH` | A-DOM07b / RiverReach | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07C-GAUGE` | A-DOM07c / Gauge | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07D-WATERBODY` | A-DOM07d / WaterBody | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07E-AQUIFER` | A-DOM07e / Aquifer | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM07F-VPU` | A-DOM07f / VPU | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM08-NAMEDPLACE` | A-DOM08 / NamedPlace | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM11-EVALUATIONMETRIC` | A-DOM11 / EvaluationMetric | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM12-PARAMETER` | A-DOM12 / Parameter | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-DOM13-ALGORITHM` | A-DOM13 / Algorithm | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P05-BACKGROUND` | A-P05 / Background | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P06-THEME` | A-P06 / Theme | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P07-RESEARCHPROBLEM` | A-P07 / ResearchProblem | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P08-RESEARCHQUESTION` | A-P08 / ResearchQuestion | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P09-RESEARCHGOAL` | A-P09 / ResearchGoal | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P10-RESEARCHSIGNIFICANCE` | A-P10 / ResearchSignificance | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P11-DEFINITION` | A-P11 / Definition | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P12-THEORETICALBASIS` | A-P12 / TheoreticalBasis | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P13-METHOD` | A-P13 / Method | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P14-EXPERIMENT` | A-P14 / Experiment | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P15-EXAMPLES` | A-P15 / Examples | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P16-FINDING` | A-P16 / Finding | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P17-DISCUSSION` | A-P17 / Discussion | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P18-RELATEDRESEARCH` | A-P18 / RelatedResearch | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P19-LIMITATION` | A-P19 / Limitation | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P20-CONCLUSION` | A-P20 / Conclusion | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P21-CONTRIBUTION` | A-P21 / Contribution | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P22-FUTUREWORK` | A-P22 / FutureWork | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P23-HYPOTHESIS` | A-P23 / Hypothesis | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P24-CLAIM` | A-P24 / Claim | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P25-DATASETMENTION-EXISTING-PHASE-B-INSTANCE` | A-P25 / DatasetMention | `deterministic_context` | link_existing | open_discovery | `DETERMINISTICALLY_APPLICABLE` | C0-NODE-SOURCE-001, C0-NODE-CONTEXT-001, C0-NODE-CONTEXT-002 |
| `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | A-P25 / DatasetMention | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |
| `PUB-N-A-P26-DATADESCRIPTION` | A-P26 / DataDescription | `llm_candidate` | propose_new | open_discovery | `UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL` | C0-NODE-SOURCE-001, C0-NODE-OPEN-001, C0-NODE-OPEN-002 |

## Coverage implications

The approved coarse policy preserves request-level target-space coverage and avoids answer-informed false exclusions, but it exposes 40 target definitions per unit. This increases provider-input and schema size compared with the historical one-target DEV-04 smoke. Future narrowing requires a new, versioned, prospective extraction-policy decision or binding target-inventory applicability clarification. Semantic pre-screening of a particular unit is not authorized.

Request-level target-space coverage is distinct from target-level explicit negative assessment. The frozen abstention contract does not require one abstention for every eligible target that is absent. No candidate and no abstention remains permissible when no supported assertion is emitted. Accordingly, this plan supports the claim that every structurally eligible source unit receives its complete applicable ontology-authorized node target space; it does not claim that the model explicitly confirmed presence or absence for every target.
