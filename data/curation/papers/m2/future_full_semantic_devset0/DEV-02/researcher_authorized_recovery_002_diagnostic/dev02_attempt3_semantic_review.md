# DEV-02 attempt-3 endpoint forensic diagnostic

Development-only, no-call counterfactual. It does not alter, repair, supersede, accept, annotate, or evaluate the authentic attempt.

- Authentic raw SHA-256: `e9ce2dcdce26ad3307a9ef44a2bdcd829b01aaae5a6fbbc3b111174776ad20d8`
- Counterfactual changes: 36 endpoint `artifactID` values only
- Counterfactual V1–V12 envelope: `valid`; usable nodes/edges: 53/26

## Semantic review

| ID | Kind | Class / relation | Bucket | Rationale |
|---|---|---|---|---|
| node-0001 | node | Tool | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0002 | node | ProcessBasedModel | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0003 | node | ProcessBasedModel | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0004 | node | ProcessBasedModel | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0005 | node | Variable | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0006 | node | Variable | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0007 | node | Variable | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0008 | node | Variable | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0009 | node | Concept | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0010 | node | Watershed | needs_semantic_review | Plural coverage set, not one individually identified watershed; verify whether the target permits an aggregate HUC8 collection. |
| node-0011 | node | Watershed | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0012 | node | RiverReach | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0013 | node | RiverReach | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0014 | node | RiverReach | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0015 | node | Gauge | likely_unsupported | Generic plural noun identifies a measurement-source type, not a hydrologic station; no station identity is supplied. |
| node-0016 | node | WaterBody | needs_semantic_review | The text names a reservoir collection, but not an individual water body; verify collection-level WaterBody treatment. |
| node-0017 | node | NamedPlace | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0018 | node | EvaluationMetric | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0019 | node | EvaluationMetric | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0020 | node | EvaluationMetric | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0021 | node | EvaluationMetric | needs_semantic_review | TP is explicitly defined and used to calculate evaluation metrics, but is a contingency-table component rather than a reported metric result. |
| node-0022 | node | EvaluationMetric | needs_semantic_review | FP is explicitly defined and used to calculate evaluation metrics, but is a contingency-table component rather than a reported metric result. |
| node-0023 | node | EvaluationMetric | needs_semantic_review | FN is explicitly defined and used to calculate evaluation metrics, but is a contingency-table component rather than a reported metric result. |
| node-0024 | node | EvaluationMetric | needs_semantic_review | TN is explicitly defined across the cited continuation, but is a contingency-table component rather than a reported metric result. |
| node-0025 | node | ResearchProblem | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0026 | node | ResearchGoal | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0027 | node | Method | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0028 | node | Method | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0029 | node | Method | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0030 | node | Method | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0031 | node | Method | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0032 | node | Experiment | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0033 | node | Finding | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0034 | node | Finding | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0035 | node | RelatedResearch | needs_semantic_review | This is a substantive statement attributed to cited work; verify whether it is sufficiently about prior research rather than a bare citation context. |
| node-0036 | node | Limitation | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0037 | node | Limitation | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0038 | node | Limitation | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0039 | node | Limitation | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0040 | node | Limitation | needs_semantic_review | The missing reaches constrain a subset of sites and supports a limitation, but the phrase is incomplete as an atomic limitation statement. |
| node-0041 | node | Claim | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0042 | node | DatasetMention | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0043 | node | DatasetMention | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0044 | node | DatasetMention | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0045 | node | DatasetMention | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0046 | node | DataDescription | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0047 | node | DataDescription | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0048 | node | DataDescription | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0049 | node | Method | needs_semantic_review | The sentence is cut off at the source-unit boundary; it supports an imputation procedure but leaves its comparison object incomplete. |
| node-0050 | node | Definition | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0051 | node | Definition | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0052 | node | Definition | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| node-0053 | node | Definition | strongly_supported | The exact cited text directly names or states the candidate in the applicable target role. |
| edge-0001 | relation | mentionsTool | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0002 | relation | usesModel | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0003 | relation | usesModel | needs_semantic_review | NWM is operationally linked and its network is used, but the cited sentence does not unambiguously establish paper-level model use under the relation criterion. |
| edge-0004 | relation | usesModel | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0005 | relation | mentionsVariable | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0006 | relation | mentionsVariable | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0007 | relation | mentionsVariable | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0008 | relation | mentionsVariable | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0009 | relation | mentionsConcept | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0010 | relation | studiesFeature | needs_semantic_review | The paper selects 49 HUC8s for evaluation, but the endpoint is an aggregate rather than one watershed feature. |
| edge-0011 | relation | studiesFeature | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0012 | relation | studiesPlace | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0013 | relation | resolves | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0014 | relation | usesModel | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0015 | relation | usesDataset | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0016 | relation | mentionsDataset | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0017 | relation | mentionsDataset | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0018 | relation | mentionsDataset | strongly_supported | The cited text explicitly states the modeled relation or direct study-level use/mention. |
| edge-0019 | relation | reportsMetric | strongly_supported | The experiment text expressly says CSI is employed to evaluate inundation extents. |
| edge-0020 | relation | reportsMetric | strongly_supported | The experiment text expressly says POD is employed to evaluate inundation extents. |
| edge-0021 | relation | reportsMetric | strongly_supported | The experiment text expressly says FAR is employed to evaluate inundation extents. |
| edge-0022 | relation | reportsMetric | likely_unsupported | TP is introduced as a primary component needed to calculate secondary metrics, not as a metric explicitly reported by the experiment. |
| edge-0023 | relation | reportsMetric | likely_unsupported | FP is introduced as a primary component needed to calculate secondary metrics, not as a metric explicitly reported by the experiment. |
| edge-0024 | relation | reportsMetric | likely_unsupported | FN is introduced as a primary component needed to calculate secondary metrics, not as a metric explicitly reported by the experiment. |
| edge-0025 | relation | reportsMetric | likely_unsupported | TN is defined as a contingency-table component, not explicitly reported by the experiment as an evaluation metric. |
| edge-0026 | relation | hasLimitation | strongly_supported | The evidence directly connects reservoir handling to false negatives/under-prediction, qualifying that finding. |

Full labels/endpoints, evidence text, and applicable positive criteria/boundaries are in the adjacent JSON artifact.
