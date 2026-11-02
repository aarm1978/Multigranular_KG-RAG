# Secondary sensitivity review instrument v0.1.1

Review pending. Step 7 remains PRE-FREEZE. v0.1.0 is preserved as an unused pre-review instrument.

Select reviewedC1RecordKey for each semantic-equivalent correspondence. Global one-to-one selection is required.
Review source support independently for every C1 prediction, including strict TPs.
For target_or_class_disagreement, an exact same-unit C1 key may document the disagreement; it cannot recover a cross-target/class match.

Human-Core semantic recovery: confirmed one-to-one equivalents / 118 nodes or 61 relations.
C1 source-supported prediction rate: supported_as_proposed / 102 nodes or 59 relations; report unsupported and insufficient separately.
Both metrics remain unset until researcher review is complete. See the bound protocol and endpoint context in JSON.

## Populations

{"c1OnlyAssertions": 126, "candidateGroups": 179, "correspondenceReviewItems": 179, "humanCoreByKind": {"node": 118, "relation": 61}, "predictionSourceSupportReviewItems": 161, "predictionsByKind": {"node": 102, "relation": 59}, "reviewItems": 340, "sourceUnitCount": 5, "strictTruePositivePairs": 35, "unmatchedHumanCoreRecords": 144}

## Unit / target index

### pub:10:sec:0008:unit:0001

- PUB-N-A-AG02-ORGANIZATION-PROSE: 9 correspondence; 0 support items.
- PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE: 1 correspondence; 1 support items.
- PUB-N-A-DOM03A-PROCESSBASEDMODEL: 12 correspondence; 12 support items.
- PUB-N-A-DOM04-VARIABLE: 1 correspondence; 2 support items.
- PUB-N-A-DOM08-NAMEDPLACE: 3 correspondence; 0 support items.
- PUB-N-A-P07-RESEARCHPROBLEM: 4 correspondence; 3 support items.
- PUB-N-A-P09-RESEARCHGOAL: 1 correspondence; 1 support items.
- PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE: 3 correspondence; 2 support items.
- PUB-N-A-P26-DATADESCRIPTION: 2 correspondence; 2 support items.
- PUB-R-C-P16-MENTIONSVARIABLE: 1 correspondence; 2 support items.
- PUB-R-C-P23-MENTIONSMODEL: 12 correspondence; 11 support items.
- PUB-R-C-P24-MENTIONSDATASET: 3 correspondence; 2 support items.
- PUB-R-C-P31-MENTIONSTOOL: 1 correspondence; 0 support items.

### pub:15:sec:0004:unit:0001

- PUB-N-A-DOM03D-MLMODEL: 5 correspondence; 3 support items.
- PUB-N-A-DOM03E-AGENTBASEDMODEL: 1 correspondence; 0 support items.
- PUB-N-A-DOM04-VARIABLE: 2 correspondence; 5 support items.
- PUB-N-A-P13-METHOD: 3 correspondence; 5 support items.
- PUB-R-C-P13-USESMODEL-PAPER-BRANCH: 6 correspondence; 3 support items.
- PUB-R-C-P14-APPLIESTO: 2 correspondence; 1 support items.
- PUB-R-C-P16-MENTIONSVARIABLE: 2 correspondence; 5 support items.
- PUB-R-C-P34-HASCOMPONENT: 6 correspondence; 0 support items.

### pub:16:sec:0033:unit:0001

- PUB-N-A-AG02-ORGANIZATION-PROSE: 3 correspondence; 0 support items.
- PUB-N-A-P07-RESEARCHPROBLEM: 2 correspondence; 1 support items.
- PUB-N-A-P09-RESEARCHGOAL: 3 correspondence; 3 support items.
- PUB-N-A-P13-METHOD: 3 correspondence; 0 support items.
- PUB-N-A-P20-CONCLUSION: 1 correspondence; 1 support items.
- PUB-N-A-P22-FUTUREWORK: 4 correspondence; 3 support items.
- PUB-R-C-P06-RESOLVES: 3 correspondence; 0 support items.

### pub:34:sec:0015:unit:0001

- PUB-N-A-AG02-ORGANIZATION-PROSE: 2 correspondence; 0 support items.
- PUB-N-A-DOM03A-PROCESSBASEDMODEL: 0 correspondence; 1 support items.
- PUB-N-A-DOM03D-MLMODEL: 1 correspondence; 1 support items.
- PUB-N-A-DOM04-VARIABLE: 6 correspondence; 16 support items.
- PUB-N-A-DOM07A-WATERSHED: 3 correspondence; 2 support items.
- PUB-N-A-DOM08-NAMEDPLACE: 1 correspondence; 1 support items.
- PUB-N-A-DOM11-EVALUATIONMETRIC: 1 correspondence; 1 support items.
- PUB-N-A-P13-METHOD: 3 correspondence; 3 support items.
- PUB-N-A-P16-FINDING: 1 correspondence; 1 support items.
- PUB-N-A-P19-LIMITATION: 3 correspondence; 1 support items.
- PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE: 3 correspondence; 2 support items.
- PUB-N-A-P26-DATADESCRIPTION: 5 correspondence; 9 support items.
- PUB-R-C-P13-USESMODEL-PAPER-BRANCH: 1 correspondence; 2 support items.
- PUB-R-C-P16-MENTIONSVARIABLE: 6 correspondence; 16 support items.
- PUB-R-C-P17-STUDIESFEATURE-PAPER-BRANCH: 3 correspondence; 2 support items.
- PUB-R-C-P18-STUDIESPLACE-PAPER-BRANCH: 0 correspondence; 1 support items.
- PUB-R-C-P20-USESDATASET-NEW-PROSE-EVIDENCE: 3 correspondence; 2 support items.
- PUB-R-C-P25-REPORTSMETRIC: 1 correspondence; 1 support items.
- PUB-R-C-P26-EVALUATES: 1 correspondence; 1 support items.

### pub:79:sec:0004:unit:0001

- PUB-N-A-AG02-ORGANIZATION-PROSE: 1 correspondence; 0 support items.
- PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE: 3 correspondence; 4 support items.
- PUB-N-A-DOM03A-PROCESSBASEDMODEL: 4 correspondence; 4 support items.
- PUB-N-A-DOM04-VARIABLE: 1 correspondence; 1 support items.
- PUB-N-A-DOM11-EVALUATIONMETRIC: 3 correspondence; 1 support items.
- PUB-N-A-DOM12-PARAMETER: 0 correspondence; 1 support items.
- PUB-N-A-P07-RESEARCHPROBLEM: 6 correspondence; 3 support items.
- PUB-N-A-P09-RESEARCHGOAL: 1 correspondence; 2 support items.
- PUB-N-A-P13-METHOD: 2 correspondence; 1 support items.
- PUB-N-A-P14-EXPERIMENT: 2 correspondence; 2 support items.
- PUB-N-A-P21-CONTRIBUTION: 2 correspondence; 1 support items.
- PUB-N-A-P26-DATADESCRIPTION: 1 correspondence; 0 support items.
- PUB-R-C-P06-RESOLVES: 2 correspondence; 0 support items.
- PUB-R-C-P13-USESMODEL-PAPER-BRANCH: 3 correspondence; 3 support items.
- PUB-R-C-P15-USESTOOL: 2 correspondence; 4 support items.
- PUB-R-C-P16-MENTIONSVARIABLE: 1 correspondence; 1 support items.
- PUB-R-C-P27-HASPARAMETER: 0 correspondence; 1 support items.
- PUB-R-C-P31-MENTIONSTOOL: 1 correspondence; 0 support items.
- PUB-R-C-P33-HASCODEREPOSITORY: 1 correspondence; 1 support items.
