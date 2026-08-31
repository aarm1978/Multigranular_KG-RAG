# Publication node semantic development review

Status: `researcher_semantic_review_pending`

This package contains no semantic adjudication, gold labels, or formal evaluation. C2A status is counterfactual diagnostic evidence only and is not authentic extraction output.

C1B tree SHA-256: `bee13c4501597cf7793d6c9e93f3d4a5b35a2881bc0cd98b1a0a24ea03682a28`

C2A diagnostic SHA-256: `24a7f3e779d389a86249417d4ca184fb68302c3b2e36d15adaf2a6fa33bb17a3`

Target inventory SHA-256: `3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760`

## C2B-EVID-0001 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0001`
- Unit offsets: `25:154`
- Document offsets: `6074:6203`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Flooding is one of the most significant natural disasters in the United States (US) affecting both the loss of life and property.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-P06-THEME` | `Theme` | "Flooding" | `validated` | `validated` |
| `node-0002` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "United States" | `validated` | `validated` |
| `node-0003` | `PUB-N-A-P05-BACKGROUND` | `Background` | "Flooding is one of the most significant natural disasters in the United States (US) affecting both the loss of life and property." | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0002 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0002`
- Unit offsets: `155:419`
- Document offsets: `6204:6468`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
In 2017 and 2019, river and flash flooding combined represented the leading cause of death and the second leading cause in 2018 among all natural disasters in the US (National Weather Service, [2018](#page-29-0), [2019](#page-29-1); Service, [2020b\)](#page-30-0).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-P05-BACKGROUND` | `Background` | "In 2017 and 2019, river and flash flooding combined represented the leading cause of death and the second leading cause in 2018 among all natural disasters in the US (National Weather Service, [2018](#page-29-0), [2019](#page-29-1); Service, [2020b\\)](#page-30-0)." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0003 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0003`
- Unit offsets: `420:566`
- Document offsets: `6469:6615`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
More than an average of 104 deaths per year are attributed to flood events from the 10 year period ending in 2019 (Service, [2020a\)](#page-30-1).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-P05-BACKGROUND` | `Background` | "More than an average of 104 deaths per year are attributed to flood events from the 10 year period ending in 2019 (Service, [2020a\\)](#page-30-1)." | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0004 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0004`
- Unit offsets: `567:755`
- Document offsets: `6616:6804`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
With respect to property damages, river and flash flooding have contributed to 60.7, 1.6, and 3.7 billion non-inflation adjusted US dollars in the annual periods of 2017–2019, respectively
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0006` | `PUB-N-A-P05-BACKGROUND` | `Background` | "With respect to property damages, river and flash flooding have contributed to 60.7, 1.6, and 3.7 billion non-inflation adjusted US dollars in the annual periods of 2017–2019, respectively" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0005 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0005`
- Unit offsets: `1397:1488`
- Document offsets: `7446:7537`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
with the large spike in 2017 attributed to the Hurricane Harvey event along the Gulf Coast.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0007` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "Gulf Coast" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0006 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0006`
- Unit offsets: `1489:1784`
- Document offsets: `7538:7833`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Trends related to flood damages and fatalities have been steadily increasing over recent decades (Corringham & Cayan, [2019;](#page-27-0) Downton et al., [2005;](#page-27-1) Kunkel et al., [1999](#page-28-0); Mallakpour & Villarini, [2015](#page-28-1); Pielke Jr. & Downton, [2000](#page-29-2)).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0008` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Trends related to flood damages and fatalities have been steadily increasing over recent decades (Corringham & Cayan, [2019;](#page-27-0) Downton et al., [2005;](#page-27-1) Kunkel et al., [1999](#page-28-0); Mallakpour & Villarini, [2015](#page-28-1); Pielke Jr. & Downton, [2000](#page-29-2))." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0007 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0007`
- Unit offsets: `1785:2061`
- Document offsets: `7834:8110`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Some are expecting that the hydrologic cycle will intensify due to climate change which will lead to more extreme precipitation in some areas along with a greater risk of flooding (Milly et al., [2002;](#page-29-3) Tabari, [2020;](#page-30-2) Wing et al., [2018](#page-30-3)).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0009` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "hydrologic cycle" | `validated` | `validated` |
| `node-0010` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "climate change" | `validated` | `validated` |
| `node-0011` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Some are expecting that the hydrologic cycle will intensify due to climate change which will lead to more extreme precipitation in some areas along with a greater risk of flooding (Milly et al., [2002;](#page-29-3) Tabari, [2020;](#page-30-2) Wing et al., [2018](#page-30-3))." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0008 — DEV-01

- Source unit: `pub:17:sec:0007:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0008`
- Unit offsets: `2062:2350`
- Document offsets: `8111:8399`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Increasing trends in frequency and risk are not uniform across spatial regions with work by Slater and Villarini [\(2016](#page-30-4)) indicating that trends are increasing across the US Midwest and Great Lakes regions while decreasing in the coastal Southeast, Southwest, and California.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "US Midwest" | `validated` | `validated` |
| `node-0013` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "Great Lakes regions" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "coastal Southeast" | `validated` | `validated` |
| `node-0015` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "Southwest" | `validated` | `validated` |
| `node-0016` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "California" | `validated` | `validated` |
| `node-0017` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Increasing trends in frequency and risk are not uniform across spatial regions with work by Slater and Villarini [\\(2016](#page-30-4)) indicating that trends are increasing across the US Midwest and Great Lakes regions while decreasing in the coastal Southeast, Southwest, and California." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0009 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0001`
- Unit offsets: `53:177`
- Document offsets: `75305:75429`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
OWP FIM is linked with the NWM for operational purposes, utilizing streamflow inputs, to produce FIM at a continental scale.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "streamflow inputs" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0010 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0002`
- Unit offsets: `641:770`
- Document offsets: `75893:76022`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Although they have advantages, the three data sources mentioned do not have streamflow information, which is required by OWP FIM.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0024` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "Although they have advantages, the three data sources mentioned do not have streamflow information, which is required by OWP FIM." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0011 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0003`
- Unit offsets: `771:1006`
- Document offsets: `76023:76258`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Using the NWM as a source of streamflow input would be a logical choice due to its operational use, but this would introduce hydro-climatic uncertainties that could impact the results of adding a multi-fluvial source extension to HAND.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0025` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "Using the NWM as a source of streamflow input would be a logical choice due to its operational use, but this would introduce hydro-climatic uncertainties that could impact the results of adding a multi-fluvial source extension to HAND." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0012 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0004`
- Unit offsets: `1217:1394`
- Document offsets: `76469:76646`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Given these limitations, we investigated the use of existing HEC-RAS based models to address the limitations caused by hydro-climatic uncertainties and sparse streamflow inputs.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0022` | `PUB-N-A-P07-RESEARCHPROBLEM` | `ResearchProblem` | "limitations caused by hydro-climatic uncertainties and sparse streamflow inputs" | `rejected` | `validated` |
| `node-0023` | `PUB-N-A-P09-RESEARCHGOAL` | `ResearchGoal` | "Given these limitations, we investigated the use of existing HEC-RAS based models to address the limitations caused by hydro-climatic uncertainties and sparse streamflow inputs." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0013 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0005`
- Unit offsets: `1396:1565`
- Document offsets: `76648:76817`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Our HAND based approach coupled with SRCs requires streamflow as input and is agnostic as to the source of that streamflow whether forecasted, observed, or probablistic.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0017` | `PUB-N-A-P13-METHOD` | `Method` | "HAND based approach coupled with SRCs" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0014 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0006`
- Unit offsets: `1566:1715`
- Document offsets: `76818:76967`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Due to this fact, evaluation of our relative elevation CFIM method was conducted by comparison to the HEC-RAS 1D models produced within FEMA region 6
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "HEC-RAS 1D models" | `rejected` | `validated` |
| `node-0010` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "FEMA region 6" | `rejected` | `validated` |
| `node-0018` | `PUB-N-A-P13-METHOD` | `Method` | "comparison to the HEC-RAS 1D models" | `rejected` | `validated` |
| `node-0021` | `PUB-N-A-P14-EXPERIMENT` | `Experiment` | "evaluation of our relative elevation CFIM method was conducted by comparison to the HEC-RAS 1D models produced within FEMA region 6" | `rejected` | `validated` |
| `node-0030` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "HEC-RAS 1D models produced within FEMA region 6" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0015 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0007`
- Unit offsets: `1788:1801`
- Document offsets: `77040:77053`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
estBFE Viewer
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE` | `Tool` | "estBFE Viewer" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0016 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0008`
- Unit offsets: `1854:2117`
- Document offsets: `77106:77369`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This data set was selected due to its large spatial coverage, availability of cross-sections with streamflow information, higher level of sophistication when compared to HAND, engineering scale detail, and a storied use in the literature as an evaluation data set
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0030` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "HEC-RAS 1D models produced within FEMA region 6" | `rejected` | `validated` |
| `node-0031` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "This data set was selected due to its large spatial coverage, availability of cross-sections with streamflow information, higher level of sophistication when compared to HAND, engineering scale detail, and a storied use in the literature as an evaluation data set" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `LONG_DISCOURSE_LABEL`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0017 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0009`
- Unit offsets: `2595:2713`
- Document offsets: `77847:77965`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
We selected 49 available HUC8s, shown in Figure [7](#page-16-0), which span about 185 thousand km2 across nine states.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0032` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "We selected 49 available HUC8s, shown in Figure [7](#page-16-0), which span about 185 thousand km2 across nine states." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0018 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0010`
- Unit offsets: `2714:2910`
- Document offsets: `77966:78162`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The maps of the 1% recurrence flow (1 in 100 years) and the 0.2% recurrence flow (1 in 500 years) are furnished by InFRM as well as the corresponding discharges and mapping extents for evaluation.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0033` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "The maps of the 1% recurrence flow (1 in 100 years) and the 0.2% recurrence flow (1 in 500 years) are furnished by InFRM as well as the corresponding discharges and mapping extents for evaluation." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0019 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0011`
- Unit offsets: `2911:3046`
- Document offsets: `78163:78298`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
We did exclude NWM V2.1 Reservoirs from evaluation because these are not properly accounted for in the inundation sourced from OWP FIM.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0035` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "We did exclude NWM V2.1 Reservoirs from evaluation because these are not properly accounted for in the inundation sourced from OWP FIM." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0020 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0012`
- Unit offsets: `3775:3919`
- Document offsets: `79027:79171`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
We elected to spatially intersect the HEC-RAS cross sections with the NWM stream network assigning the 1% and 0.2% flow rates to each NWM reach.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0019` | `PUB-N-A-P13-METHOD` | `Method` | "spatially intersect the HEC-RAS cross sections with the NWM stream network assigning the 1% and 0.2% flow rates to each NWM reach" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0021 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0013`
- Unit offsets: `3920:4045`
- Document offsets: `79172:79297`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
To handle multiple intersections, we opted to use a filter to select the median discharge value attributed to each NWM reach.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0020` | `PUB-N-A-P13-METHOD` | `Method` | "use a filter to select the median discharge value attributed to each NWM reach" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0022 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0014`
- Unit offsets: `4181:4523`
- Document offsets: `79433:79775`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Additionally, the stream network of the InFRM furnished models are of higher stream densities and bifurcation ratios, as evident in Figure [8](#page-16-1), leading to a significant amount of FNs along headwater streams with unit Horton-Strahler order due to the lack of representation of these additional headwater streams in the NWM network.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0034` | `PUB-N-A-P16-FINDING` | `Finding` | "Additionally, the stream network of the InFRM furnished models are of higher stream densities and bifurcation ratios, as evident in Figure [8](#page-16-1), leading to a significant amount of FNs along headwater streams with unit Horton-Strahler order due to the lack of representation of these additional headwater streams in the NWM network." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0023 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0015`
- Unit offsets: `4678:4894`
- Document offsets: `79930:80146`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The metrics employed in this study to evaluate inundation extents include CSI, Probability of Detection (POD), and False Alarm Ratio (FAR) and are presented in Equations [6](#page-17-0)[–8,](#page-17-1) respectively.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "inundation extents" | `rejected` | `validated` |
| `node-0011` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "CSI" | `rejected` | `validated` |
| `node-0012` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "Probability of Detection (POD)" | `rejected` | `validated` |
| `node-0013` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "False Alarm Ratio (FAR)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0024 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0016`
- Unit offsets: `4985:5066`
- Document offsets: `80237:80318`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
true positives (TP) which is predicted wet and wet in the BLE benchmark data set.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0014` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "true positives (TP)" | `rejected` | `validated` |
| `node-0027` | `PUB-N-A-P11-DEFINITION` | `Definition` | "true positives (TP) which is predicted wet and wet in the BLE benchmark data set." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0025 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0017`
- Unit offsets: `5102:5189`
- Document offsets: `80354:80441`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
false positives (FP), or type I errors, which is dry in the benchmark but predicted wet
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0015` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "false positives (FP)" | `rejected` | `validated` |
| `node-0028` | `PUB-N-A-P11-DEFINITION` | `Definition` | "false positives (FP), or type I errors, which is dry in the benchmark but predicted wet" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0026 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0018`
- Unit offsets: `5194:5283`
- Document offsets: `80446:80535`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
false negatives (FN), or type II errors, which is wet in the benchmark but predicted dry.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0016` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "false negatives (FN)" | `rejected` | `validated` |
| `node-0029` | `PUB-N-A-P11-DEFINITION` | `Definition` | "false negatives (FN), or type II errors, which is wet in the benchmark but predicted dry." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0027 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0019`
- Unit offsets: `6614:6792`
- Document offsets: `81866:82044`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Illustrates Base Level Engineering (BLE) cross sections and flowpaths at the HUC8 12100203 near the confluences of West Fork Plum Creek and Clear Fork Plum Creek with Plum Creek.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0006` | `PUB-N-A-DOM07A-WATERSHED` | `Watershed` | "HUC8 12100203" | `rejected` | `validated` |
| `node-0007` | `PUB-N-A-DOM07B-RIVERREACH` | `RiverReach` | "West Fork Plum Creek" | `rejected` | `validated` |
| `node-0008` | `PUB-N-A-DOM07B-RIVERREACH` | `RiverReach` | "Clear Fork Plum Creek" | `rejected` | `validated` |
| `node-0009` | `PUB-N-A-DOM07B-RIVERREACH` | `RiverReach` | "Plum Creek" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0028 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0020`
- Unit offsets: `7302:7412`
- Document offsets: `82554:82664`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This creates additional inundation areas in the validation data that are not modeled with our HAND based FIMs.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "HAND based FIMs" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0029 — DEV-02

- Source unit: `pub:17:sec:0033:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0021`
- Unit offsets: `7471:7854`
- Document offsets: `82723:83106`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
While these metrics are commonly employed in the evaluation of FIM and binary weather prediction communities in general, they do come with some notable limitations including frequency dependence in the case of CSI and FAR (Gerapetritis & Pelissier, [2004](#page-28-34); Jolliffe & Stephenson, [2012](#page-28-35); Schaefer, [1990;](#page-29-34) Stephens et al., [2014](#page-30-32)).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0026` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "frequency dependence in the case of CSI and FAR" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0030 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0001`
- Unit offsets: `127:248`
- Document offsets: `19379:19500`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
First, applying the in-cluster means of nutrient balance parameters discards some of the variability present in the NMPs.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0025` | `PUB-N-A-P13-METHOD` | `Method` | "applying the in-cluster means of nutrient balance parameters" | `validated` | `validated` |
| `node-0035` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "applying the in-cluster means of nutrient balance parameters discards some of the variability present in the NMPs" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0031 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0002`
- Unit offsets: `249:392`
- Document offsets: `19501:19644`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Second, when assigning a proportion of MBB fields in each cluster with manure or fertilizer application values, we chose those fields randomly.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0006` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "manure or fertilizer application values" | `validated` | `validated` |
| `node-0026` | `PUB-N-A-P13-METHOD` | `Method` | "assigning a proportion of MBB fields in each cluster with manure or fertilizer application values, we chose those fields randomly" | `validated` | `validated` |
| `node-0036` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "we chose those fields randomly" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0032 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0003`
- Unit offsets: `393:489`
- Document offsets: `19645:19741`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This means that each iteration of this redistribution is only one of numerous possible outcomes.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0037` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "each iteration of this redistribution is only one of numerous possible outcomes" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0033 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0004`
- Unit offsets: `491:658`
- Document offsets: `19743:19910`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
To counteract the possibility that random chance would produce results far away from the theoretical "mean" situation, we ran the NMP → MBB extrapolation 10,000 times.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0021` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "10,000" | `validated` | `validated` |
| `node-0031` | `PUB-N-A-P14-EXPERIMENT` | `Experiment` | "we ran the NMP → MBB extrapolation 10,000 times" | `validated` | `validated` |

Descriptive review flags: `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0034 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0005`
- Unit offsets: `659:914`
- Document offsets: `19911:20166`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
For each of the 10,000 unique iterations, we calculated and saved the mean value of the following parameters of the MBB dataset: per-ha P balance, corn cropland per-ha P balance, hay cropland per-ha P balance, PSR, corn cropland PSR, and hay cropland PSR.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "MBB dataset" | `validated` | `validated` |
| `node-0007` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "per-ha P balance" | `validated` | `validated` |
| `node-0008` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "corn cropland per-ha P balance" | `validated` | `validated` |
| `node-0009` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "hay cropland per-ha P balance" | `validated` | `validated` |
| `node-0010` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "PSR" | `validated` | `validated` |
| `node-0011` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "corn cropland PSR" | `validated` | `validated` |
| `node-0012` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "hay cropland PSR" | `validated` | `validated` |
| `node-0027` | `PUB-N-A-P13-METHOD` | `Method` | "we calculated and saved the mean value" | `validated` | `validated` |
| `node-0041` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "the following parameters of the MBB dataset: per-ha P balance, corn cropland per-ha P balance, hay cropland per-ha P balance, PSR, corn cropland PSR, and hay cropland PSR" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0035 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0006`
- Unit offsets: `915:1179`
- Document offsets: `20167:20431`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
For each iteration, we also saved the value of net partial P balance and calculated the total proportion (by area) of the MBB that received a PSR observation of *>*0.1, the broadly applicable M3-PSR threshold value identified by Dari et al. [\(2018\)](#page-10-0).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0013` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "net partial P balance" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "total proportion (by area)" | `validated` | `validated` |
| `node-0022` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "M3-PSR threshold value" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0036 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0007`
- Unit offsets: `1180:1291`
- Document offsets: `20432:20543`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This approach resulted in distributions of possible results for each parameter, helping to clarify uncertainty.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "uncertainty" | `validated` | `validated` |
| `node-0032` | `PUB-N-A-P16-FINDING` | `Finding` | "This approach resulted in distributions of possible results for each parameter" | `validated` | `validated` |
| `node-0034` | `PUB-N-A-P17-DISCUSSION` | `Discussion` | "helping to clarify uncertainty" | `validated` | `validated` |

Descriptive review flags: `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0037 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0008`
- Unit offsets: `1293:1653`
- Document offsets: `20545:20905`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Lastly, we repeated iterations of the NMP → MBB extrapolation model until it produced an output with means *<* |0.1 × SD| away from the mean values of 10,000 runs for per-ha P balance and PSR, and *<* |0.25\*SD| away from the mean values of 10,000 runs for corn cropland per-ha P balance, hay cropland per-ha P balance, corn cropland PSR, and hay cropland PSR.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0023` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "\|0.1 × SD\|" | `validated` | `validated` |
| `node-0024` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "\|0.25\\*SD\|" | `validated` | `validated` |
| `node-0028` | `PUB-N-A-P13-METHOD` | `Method` | "we repeated iterations of the NMP → MBB extrapolation model until it produced an output" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0038 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0009`
- Unit offsets: `1654:1834`
- Document offsets: `20906:21086`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
We refer to this result as the "centrally trending model iteration" and regard this model iteration as being as close to the theoretical mean basin-wide extrapolation as practical.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0039` | `PUB-N-A-P11-DEFINITION` | `Definition` | "We refer to this result as the \"centrally trending model iteration\"" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0039 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0010`
- Unit offsets: `1836:1937`
- Document offsets: `21088:21189`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
To protect farmer privacy when displaying the prediction in GIS, we performed some minor aggregation.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE` | `Tool` | "GIS" | `validated` | `validated` |
| `node-0003` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "farmer privacy" | `validated` | `validated` |
| `node-0029` | `PUB-N-A-P13-METHOD` | `Method` | "minor aggregation" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0040 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0011`
- Unit offsets: `1938:2127`
- Document offsets: `21190:21379`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
We computed spatially weighted mean values of P balance, PSR, and MMP for the centrally trending model iteration within each combination of land use type and NHDPlus HR HUC-12 subwatershed.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM07A-WATERSHED` | `Watershed` | "NHDPlus HR HUC-12 subwatershed" | `validated` | `validated` |
| `node-0015` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "MMP" | `validated` | `validated` |
| `node-0016` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "land use type" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0041 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0012`
- Unit offsets: `2128:2247`
- Document offsets: `21380:21499`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
A total of 25 HUC-12-level subwatersheds existed in the MBB, with 82 distinct combinations of HUC-12 and land use type.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0042` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "A total of 25 HUC-12-level subwatersheds existed in the MBB, with 82 distinct combinations of HUC-12 and land use type" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0042 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0013`
- Unit offsets: `2248:2471`
- Document offsets: `21500:21723`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Spatially weighted means were computed by multiplying each field's P balance rate by the field's area, summing these totals within one HUC-12/land use type group, then dividing by the total area of all fields in that group.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0017` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance rate" | `validated` | `validated` |
| `node-0018` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "field's area" | `validated` | `validated` |
| `node-0030` | `PUB-N-A-P13-METHOD` | `Method` | "Spatially weighted means were computed by multiplying each field's P balance rate by the field's area, summing these totals within one HUC-12/land use type group, then dividing by the total area of all fields in that group" | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0043 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0014`
- Unit offsets: `2472:2644`
- Document offsets: `21724:21896`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This provided smoother visualization of trends by cluster across the landscape, highlighting areas with higher or lower P parameter values, as opposed to individual fields.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0033` | `PUB-N-A-P16-FINDING` | `Finding` | "This provided smoother visualization of trends by cluster across the landscape" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0044 — DEV-03

- Source unit: `pub:36:sec:0020:unit:0001`
- Section role: `data`
- Evidence span: `evidence-0015`
- Unit offsets: `2645:2897`
- Document offsets: `21897:22149`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Second, smoothing the data for public representation reinforces that the model is an informed estimate of spatial P saturation and soil test P conditions for agricultural land types across the MBB but should not be used to make field-level conclusions.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0019` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "spatial P saturation" | `validated` | `validated` |
| `node-0020` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "soil test P conditions" | `validated` | `validated` |
| `node-0038` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "should not be used to make field-level conclusions" | `validated` | `validated` |
| `node-0040` | `PUB-N-A-P24-CLAIM` | `Claim` | "the model is an informed estimate of spatial P saturation and soil test P conditions for agricultural land types across the MBB" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0045 — DEV-04

- Source unit: `pub:36:sec:0026:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0001`
- Unit offsets: `31:155`
- Document offsets: `27231:27355`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Key results of our clustering and data analysis are shown in Table [1,](#page-8-0) with PSR and P balance ranked by cluster.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-P13-METHOD` | `Method` | "clustering" | `validated` | `validated` |
| `node-0002` | `PUB-N-A-P13-METHOD` | `Method` | "data analysis" | `validated` | `validated` |
| `node-0003` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "PSR" | `validated` | `validated` |
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0046 — DEV-04

- Source unit: `pub:36:sec:0026:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0002`
- Unit offsets: `156:291`
- Document offsets: `27356:27491`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The corn cluster with medium slope and high soil clay content had the highest P balance (27 ± 1 kg P ha−<sup>1</sup> year<sup>−</sup>1)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance" | `validated` | `validated` |
| `node-0005` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "slope" | `validated` | `validated` |
| `node-0006` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "soil clay content" | `validated` | `validated` |
| `node-0007` | `PUB-N-A-P16-FINDING` | `Finding` | "The corn cluster with medium slope and high soil clay content had the highest P balance (27 ± 1 kg P ha−<sup>1</sup> year<sup>−</sup>1)" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0047 — DEV-04

- Source unit: `pub:36:sec:0026:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0003`
- Unit offsets: `293:393`
- Document offsets: `27493:27593`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
other corn clusters had mean P balances ranging from 6 to 19 kg P ha−<sup>1</sup> year<sup>−</sup>1,
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance" | `validated` | `validated` |
| `node-0008` | `PUB-N-A-P16-FINDING` | `Finding` | "other corn clusters had mean P balances ranging from 6 to 19 kg P ha−<sup>1</sup> year<sup>−</sup>1" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0048 — DEV-04

- Source unit: `pub:36:sec:0026:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0004`
- Unit offsets: `398:490`
- Document offsets: `27598:27690`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
all hay clusters had mean P balances between 1 and 8 kg P ha−<sup>1</sup> year<sup>−</sup>1.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance" | `validated` | `validated` |
| `node-0009` | `PUB-N-A-P16-FINDING` | `Finding` | "all hay clusters had mean P balances between 1 and 8 kg P ha−<sup>1</sup> year<sup>−</sup>1" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0049 — DEV-04

- Source unit: `pub:36:sec:0026:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0005`
- Unit offsets: `491:583`
- Document offsets: `27691:27783`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Cluster-mean PSR and P balance values were not correlated (Spearman rho = 0.36; *p* = 0.34).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "PSR" | `validated` | `validated` |
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "P balance" | `validated` | `validated` |
| `node-0010` | `PUB-N-A-P16-FINDING` | `Finding` | "Cluster-mean PSR and P balance values were not correlated (Spearman rho = 0.36; *p* = 0.34)." | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0050 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0001`
- Unit offsets: `77:336`
- Document offsets: `8876:9135`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
A set of 249 self-calibrated Palmer Drought Severity Index (scPDSI) cells located within a 450 km radius of the SRB and a portion of the Old Water Drought Atlas (OWDA) developed from summer-related tree-ring proxies over a period from year 0 to 2012 were used
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "Palmer Drought Severity Index (scPDSI) cells" | `validated` | `validated` |
| `node-0002` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "Old Water Drought Atlas (OWDA)" | `validated` | `validated` |
| `node-0003` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "A set of 249 self-calibrated Palmer Drought Severity Index (scPDSI) cells located within a 450 km radius of the SRB and a portion of the Old Water Drought Atlas (OWDA) developed from summer-related tree-ring proxies over a period from year 0 to 2012 were used" | `validated` | `validated` |
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "Palmer Drought Severity Index (scPDSI)" | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0051 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0002`
- Unit offsets: `360:516`
- Document offsets: `9159:9315`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This index has been shown to have significant and positive correlations with SR water flux, making it a valuable proxy for streamflow reconstructions in SRB
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "SR water flux" | `validated` | `validated` |
| `node-0006` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "streamflow" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0052 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0003`
- Unit offsets: `545:708`
- Document offsets: `9344:9507`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `false`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The reconstructed alpine monthly precipitation dataset, also known as the Long-term Alpine Precipitation Reconstruction (LAPrec), is derived from in situ observations.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0007` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "Long-term Alpine Precipitation Reconstruction (LAPrec)" | `rejected` | `rejected` |
| `node-0008` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "The reconstructed alpine monthly precipitation dataset, also known as the Long-term Alpine Precipitation Reconstruction (LAPrec), is derived from in situ observations." | `rejected` | `rejected` |

Descriptive review flags: `AUTHENTIC_REJECTED_RESIDUAL_EVIDENCE`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0053 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0004`
- Unit offsets: `709:819`
- Document offsets: `9508:9618`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This dataset provides gridded fields of monthly precipitation for the Alpine region, covering eight countries.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0009` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "This dataset provides gridded fields of monthly precipitation for the Alpine region, covering eight countries." | `validated` | `validated` |
| `node-0010` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "Alpine region" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0054 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0005`
- Unit offsets: `1000:1078`
- Document offsets: `9799:9877`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The dataset spans from 1871 to 2020 and boasts a horizontal resolution of 5 km
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0011` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "The dataset spans from 1871 to 2020 and boasts a horizontal resolution of 5 km" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0055 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0006`
- Unit offsets: `1102:1143`
- Document offsets: `9901:9942`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
LAPrec combines two primary data sources:
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "LAPrec combines two primary data sources:" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0056 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0007`
- Unit offsets: `1154:1346`
- Document offsets: `9953:10145`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Historical Instrumental Climatological Surface Time Series of the Greater Alpine Region (HISTALP) offers homogenized station series of monthly precipitation that date back to the 19th century.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0013` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "Historical Instrumental Climatological Surface Time Series of the Greater Alpine Region (HISTALP)" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "Historical Instrumental Climatological Surface Time Series of the Greater Alpine Region (HISTALP) offers homogenized station series of monthly precipitation that date back to the 19th century." | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0057 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0008`
- Unit offsets: `1347:1486`
- Document offsets: `10146:10285`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This version of the dataset, which starts in 1871, uses 85 almost-continuous series that are uniformly distributed across the Alpine region
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0015` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "This version of the dataset, which starts in 1871, uses 85 almost-continuous series that are uniformly distributed across the Alpine region" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0058 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0009`
- Unit offsets: `1520:1672`
- Document offsets: `10319:10471`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Alpine Precipitation Grid Dataset (APGD) provides daily precipitation gridded data for the period 1971–2008 constructed from more than 8500 rain gauges.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0016` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "Alpine Precipitation Grid Dataset (APGD)" | `validated` | `validated` |
| `node-0017` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "Alpine Precipitation Grid Dataset (APGD) provides daily precipitation gridded data for the period 1971–2008 constructed from more than 8500 rain gauges." | `validated` | `validated` |
| `node-0018` | `PUB-N-A-DOM07C-GAUGE` | `Gauge` | "rain gauges" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0059 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0010`
- Unit offsets: `1673:1889`
- Document offsets: `10472:10688`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This dataset incorporates daily precipitation measurements from over 5500 rain gauges on average per day, covering the entire Alpine region and ensuring a dense in situ observation network over high-alpine topography
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0019` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "This dataset incorporates daily precipitation measurements from over 5500 rain gauges on average per day, covering the entire Alpine region and ensuring a dense in situ observation network over high-alpine topography" | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0060 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0011`
- Unit offsets: `1915:2072`
- Document offsets: `10714:10871`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The LAPrec dataset was developed using the Reduced Space Optimal Interpolation (RSOI) method, which establishes a linear model between station and grid data.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0020` | `PUB-N-A-P13-METHOD` | `Method` | "Reduced Space Optimal Interpolation (RSOI) method" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0061 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0012`
- Unit offsets: `2073:2234`
- Document offsets: `10872:11033`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This method involves Principal Component Analysis (PCA) of the high-resolution grid data followed by Optimal Interpolation (OI) using the long-term station data.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0021` | `PUB-N-A-DOM13-ALGORITHM` | `Algorithm` | "Principal Component Analysis (PCA)" | `validated` | `validated` |
| `node-0022` | `PUB-N-A-DOM13-ALGORITHM` | `Algorithm` | "Optimal Interpolation (OI)" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0062 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0013`
- Unit offsets: `2235:2467`
- Document offsets: `11034:11266`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The dataset was developed as a collaboration between the national meteorological services of Switzerland (MeteoSwiss, Federal Office of Meteorology and Climatology) and Austria (ZAMG, Zentralanstalt für Meteorologie und Geodynamik).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0023` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "The dataset was developed as a collaboration between the national meteorological services of Switzerland (MeteoSwiss, Federal Office of Meteorology and Climatology) and Austria (ZAMG, Zentralanstalt für Meteorologie und Geodynamik)." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0063 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0014`
- Unit offsets: `2470:2614`
- Document offsets: `11269:11413`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
It is important to note that climate conditions have been changing through the decades, and the selection of the dataset can impact the results.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0024` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "It is important to note that climate conditions have been changing through the decades, and the selection of the dataset can impact the results." | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0064 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0015`
- Unit offsets: `2615:2824`
- Document offsets: `11414:11623`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
However, the dataset chosen for this study was constructed using state-of-the-art climatological approaches, ensuring a homogeneous dataset that adheres to the standards set by European meteorological offices.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0025` | `PUB-N-A-P24-CLAIM` | `Claim` | "However, the dataset chosen for this study was constructed using state-of-the-art climatological approaches, ensuring a homogeneous dataset that adheres to the standards set by European meteorological offices." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0065 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0016`
- Unit offsets: `2827:3029`
- Document offsets: `11626:11828`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
For this study, the SRB catchment average monthly precipitation was extracted based on the gridded precipitation data, with a focus on the seasonal April–May–June–July– August–September (AMJJAS) period.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0026` | `PUB-N-A-DOM07A-WATERSHED` | `Watershed` | "SRB catchment" | `validated` | `validated` |
| `node-0027` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "SRB catchment average monthly precipitation" | `validated` | `validated` |
| `node-0028` | `PUB-N-A-P13-METHOD` | `Method` | "the SRB catchment average monthly precipitation was extracted based on the gridded precipitation data" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0066 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0017`
- Unit offsets: `3031:3263`
- Document offsets: `11830:12062`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The techniques used to perform the SRB AMJJAS precipitation reconstruction are divided into two groups. The first consists of nine "General Machine Learning Models" that use cross-validation techniques to evaluate their performance.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0029` | `PUB-N-A-P06-THEME` | `Theme` | "SRB AMJJAS precipitation reconstruction" | `validated` | `validated` |
| `node-0030` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "General Machine Learning Models" | `validated` | `validated` |
| `node-0031` | `PUB-N-A-P13-METHOD` | `Method` | "cross-validation techniques" | `validated` | `validated` |

Descriptive review flags: `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0067 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0018`
- Unit offsets: `3264:3441`
- Document offsets: `12063:12240`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The second group, referred to in this study as "Specialized Machine Learning Models", consists of optimized

*Hydrology* **2023**, *10*, 207 4 of 15

or more advanced DL models.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0032` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Specialized Machine Learning Models" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0068 — DEV-05

- Source unit: `pub:219:sec:0003:unit:0001`
- Section role: `methods`
- Evidence span: `evidence-0019`
- Unit offsets: `3442:3702`
- Document offsets: `12241:12501`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
In both groups, the AMJJAS precipitation data accumulated between the months of April and September (AMJJAS) for the period from 1876 to 2012 were used as the dependent variable (label), while the 249 scPSDI cells were used as independent variables (features).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0033` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "AMJJAS precipitation data" | `validated` | `validated` |
| `node-0034` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "249 scPSDI cells" | `validated` | `validated` |
| `node-0035` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "In both groups, the AMJJAS precipitation data accumulated between the months of April and September (AMJJAS) for the period from 1876 to 2012 were used as the dependent variable (label), while the 249 scPSDI cells were used as independent variables (features)." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0069 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0001`
- Unit offsets: `19:157`
- Document offsets: `20714:20852`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The performance of the nine General Machine Learning models, as evaluated through cross-validation, is summarized in Table [1.](#page-5-0)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0018` | `PUB-N-A-P13-METHOD` | `Method` | "cross-validation" | `rejected` | `validated` |
| `node-0022` | `PUB-N-A-P14-EXPERIMENT` | `Experiment` | "The performance of the nine General Machine Learning models, as evaluated through cross-validation, is summarized in Table [1.](#page-5-0)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0070 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0002`
- Unit offsets: `173:303`
- Document offsets: `20868:20998`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
the GLM and RF models demonstrated superior accuracy, both achieving an RMSE below 120 mm, an NSE above 0.25, and a KGE above 0.4.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0010` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "RMSE" | `rejected` | `validated` |
| `node-0011` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "NSE" | `rejected` | `validated` |
| `node-0012` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "KGE" | `rejected` | `validated` |
| `node-0024` | `PUB-N-A-P16-FINDING` | `Finding` | "the GLM and RF models demonstrated superior accuracy, both achieving an RMSE below 120 mm, an NSE above 0.25, and a KGE above 0.4." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0071 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0003`
- Unit offsets: `503:525`
- Document offsets: `21198:21220`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Linear Regression (LR)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Linear Regression (LR)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0072 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0004`
- Unit offsets: `562:590`
- Document offsets: `21257:21285`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Support Vector Machine (SVM)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Support Vector Machine (SVM)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0073 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0005`
- Unit offsets: `621:639`
- Document offsets: `21316:21334`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Deep Learning (DL)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Deep Learning (DL)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0074 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0006`
- Unit offsets: `679:709`
- Document offsets: `21374:21404`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Generalized Linear Model (GLM)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Generalized Linear Model (GLM)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0075 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0007`
- Unit offsets: `734:759`
- Document offsets: `21429:21454`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
k-Nearest Neighbors (kNN)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "k-Nearest Neighbors (kNN)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0076 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0008`
- Unit offsets: `780:808`
- Document offsets: `21475:21503`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Gradient Boosted Trees (GBT)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0006` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Gradient Boosted Trees (GBT)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0077 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0009`
- Unit offsets: `829:847`
- Document offsets: `21524:21542`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Decision Tree (DT)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0007` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Decision Tree (DT)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0078 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0010`
- Unit offsets: `868:886`
- Document offsets: `21563:21581`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Random Forest (RF)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0008` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Random Forest (RF)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0079 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0011`
- Unit offsets: `911:932`
- Document offsets: `21606:21627`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Gaussian Process (GP)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0009` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "Gaussian Process (GP)" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0080 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0012`
- Unit offsets: `1042:1161`
- Document offsets: `21737:21856`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
During the automated feature engineering phase, several scPDSI cells emerged as significant contributors to the models.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0013` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "scPDSI" | `rejected` | `validated` |
| `node-0019` | `PUB-N-A-P13-METHOD` | `Method` | "automated feature engineering" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0081 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0013`
- Unit offsets: `1162:1231`
- Document offsets: `21857:21926`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The GLM model included 67 of these cells, while the RF model used 66.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0025` | `PUB-N-A-P16-FINDING` | `Finding` | "The GLM model included 67 of these cells, while the RF model used 66." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0082 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0014`
- Unit offsets: `1232:1364`
- Document offsets: `21927:22059`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Of these, 21 cells were consistently selected by both models, highlighting their importance in the SRB precipitation reconstruction.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0014` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "precipitation" | `rejected` | `validated` |
| `node-0026` | `PUB-N-A-P16-FINDING` | `Finding` | "Of these, 21 cells were consistently selected by both models, highlighting their importance in the SRB precipitation reconstruction." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0083 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0015`
- Unit offsets: `1523:1650`
- Document offsets: `22218:22345`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
For the GLM model, there was an improvement in performance, while for the RF model, there was a slight decrease in performance.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0027` | `PUB-N-A-P16-FINDING` | `Finding` | "For the GLM model, there was an improvement in performance, while for the RF model, there was a slight decrease in performance." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0084 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0016`
- Unit offsets: `1809:2105`
- Document offsets: `22504:22800`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
GLM, being a linear model that benefits from feature selection because it reduces multicollinearity and improves model interpretation by reducing irrelevant or redundant features, allows the model to focus on the most significant linear relationships between the features and the target variable.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0015` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "multicollinearity" | `rejected` | `validated` |
| `node-0020` | `PUB-N-A-P13-METHOD` | `Method` | "feature selection" | `rejected` | `validated` |
| `node-0029` | `PUB-N-A-P17-DISCUSSION` | `Discussion` | "GLM, being a linear model that benefits from feature selection because it reduces multicollinearity and improves model interpretation by reducing irrelevant or redundant features, allows the model to focus on the most significant linear relationships between the features and the target variable." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `LONG_DISCOURSE_LABEL`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0085 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0017`
- Unit offsets: `2106:2242`
- Document offsets: `22801:22937`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
RF, on the other hand, is a model that can handle a large number of features and automatically determine the importance of each feature.
~~~~

Candidates:

No candidate references this authentic evidence span.

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0086 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0018`
- Unit offsets: `2243:2399`
- Document offsets: `22938:23094`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Therefore, by reducing the number of features, it is possible that some information that the model could have used to make splits in the trees is eliminated
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0030` | `PUB-N-A-P17-DISCUSSION` | `Discussion` | "Therefore, by reducing the number of features, it is possible that some information that the model could have used to make splits in the trees is eliminated" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0087 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0019`
- Unit offsets: `3450:3600`
- Document offsets: `24145:24295`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
As mentioned above, the time-based analysis process implemented a 10-year moving window, which resulted in multiplying the features by a factor of 10.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0017` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "10-year moving window" | `rejected` | `validated` |
| `node-0021` | `PUB-N-A-P13-METHOD` | `Method` | "time-based analysis process" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0088 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0020`
- Unit offsets: `3601:3708`
- Document offsets: `24296:24403`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The purpose of this analysis was to use the information from the preceding 10 years to predict the present.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0023` | `PUB-N-A-P09-RESEARCHGOAL` | `ResearchGoal` | "The purpose of this analysis was to use the information from the preceding 10 years to predict the present." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0089 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0021`
- Unit offsets: `3873:3990`
- Document offsets: `24568:24685`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
NSE and KGE metrics are not included because increasing the number of features artificially distorts the calculation.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0033` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "NSE and KGE metrics are not included because increasing the number of features artificially distorts the calculation." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0090 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0022`
- Unit offsets: `4137:4192`
- Document offsets: `24832:24887`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
the time-based analysis led to a decline in performance
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0028` | `PUB-N-A-P16-FINDING` | `Finding` | "the time-based analysis led to a decline in performance" | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0091 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0023`
- Unit offsets: `4383:4441`
- Document offsets: `25078:25136`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
features may have led to overfitting in the training data.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0016` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "overfitting" | `rejected` | `validated` |
| `node-0031` | `PUB-N-A-P17-DISCUSSION` | `Discussion` | "features may have led to overfitting in the training data." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0092 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0024`
- Unit offsets: `4442:4557`
- Document offsets: `25137:25252`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This may explain the decline in performance observed in the test data for each fold during the time-based analysis.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0032` | `PUB-N-A-P17-DISCUSSION` | `Discussion` | "This may explain the decline in performance observed in the test data for each fold during the time-based analysis." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0093 — DEV-06

- Source unit: `pub:219:sec:0008:unit:0001`
- Section role: `results`
- Evidence span: `evidence-0025`
- Unit offsets: `4628:4767`
- Document offsets: `25323:25462`
- Authentic evidence valid: `false`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Spatial distribution of the 249 scPDSI cells used in this study, which are located within a 450 km radius around the upper part of the SRB.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0034` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "Spatial distribution of the 249 scPDSI cells used in this study, which are located within a 450 km radius around the upper part of the SRB." | `rejected` | `validated` |

Descriptive review flags: `AUTHENTIC_REJECTED_SECTION_TITLE_ONLY`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0094 — DEV-07

- Source unit: `pub:243:sec:0003:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0001`
- Unit offsets: `1559:1604`
- Document offsets: `7679:7724`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
parameterizations (empirical representations)
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-P11-DEFINITION` | `Definition` | "parameterizations (empirical representations)" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0095 — DEV-07

- Source unit: `pub:243:sec:0003:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0002`
- Unit offsets: `1792:1983`
- Document offsets: `7912:8103`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Further, many of these process representations and parameterizations are subject to considerable uncertainty, some of which is related to scale, and thus has significant room for improvement.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-P07-RESEARCHPROBLEM` | `ResearchProblem` | "Further, many of these process representations and parameterizations are subject to considerable uncertainty, some of which is related to scale, and thus has significant room for improvement." | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0096 — DEV-07

- Source unit: `pub:243:sec:0003:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0003`
- Unit offsets: `1984:2190`
- Document offsets: `8104:8310`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Here we argue that differentiable implementations

of geoscientific models offer a transformative approach to simultaneously advancing process representations, parameter estimation, and predictive accuracy.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-P06-THEME` | `Theme` | "Here we argue that differentiable implementations\n\nof geoscientific models offer a transformative approach to simultaneously advancing process representations, parameter estimation, and predictive accuracy." | `validated` | `validated` |
| `node-0005` | `PUB-N-A-P09-RESEARCHGOAL` | `ResearchGoal` | "Here we argue that differentiable implementations\n\nof geoscientific models offer a transformative approach to simultaneously advancing process representations, parameter estimation, and predictive accuracy." | `validated` | `validated` |
| `node-0006` | `PUB-N-A-P10-RESEARCHSIGNIFICANCE` | `ResearchSignificance` | "Here we argue that differentiable implementations\n\nof geoscientific models offer a transformative approach to simultaneously advancing process representations, parameter estimation, and predictive accuracy." | `validated` | `validated` |
| `node-0007` | `PUB-N-A-P24-CLAIM` | `Claim` | "Here we argue that differentiable implementations\n\nof geoscientific models offer a transformative approach to simultaneously advancing process representations, parameter estimation, and predictive accuracy." | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_DIFFERENT_TARGET`, `LONG_DISCOURSE_LABEL`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0097 — DEV-07

- Source unit: `pub:243:sec:0003:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0004`
- Unit offsets: `2003:2033`
- Document offsets: `8123:8153`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
differentiable implementations
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "differentiable implementations" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0098 — DEV-07

- Source unit: `pub:243:sec:0003:unit:0001`
- Section role: `introduction`
- Evidence span: `evidence-0005`
- Unit offsets: `2191:2432`
- Document offsets: `8311:8552`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
In particular, differentiable implementations provide an unprecedentedly seamless connection between process-based and machinelearning-based model components, potentially enabling us to realize the value and minimize the limitations of each.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0008` | `PUB-N-A-P24-CLAIM` | `Claim` | "In particular, differentiable implementations provide an unprecedentedly seamless connection between process-based and machinelearning-based model components, potentially enabling us to realize the value and minimize the limitations of each." | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0099 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0001`
- Unit offsets: `111:230`
- Document offsets: `44543:44662`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
directly differentiating numerical models is the most straightforward method and is most similar to traditional models.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-P13-METHOD` | `Method` | "directly differentiating numerical models" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0100 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0002`
- Unit offsets: `719:862`
- Document offsets: `45151:45294`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
They can also migrate the learned relationships to existing implementations, e.g., the national water model, to immediately support operations.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "national water model" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0101 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0003`
- Unit offsets: `863:943`
- Document offsets: `45295:45375`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
However, reimplementing a model does incur non-trivial initial development cost.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "reimplementing a model does incur non-trivial initial development cost" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0102 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0004`
- Unit offsets: `944:1162`
- Document offsets: `45376:45594`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Mathematical changes may be required to adapt previously nondifferentiable mathematical operations to be mathematically differentiable, e.g., by replacing indexing with convolutions, and to improve parallel efficiency.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "Mathematical changes may be required to adapt previously nondifferentiable mathematical operations to be mathematically differentiable" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0103 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0005`
- Unit offsets: `1163:1320`
- Document offsets: `45595:45752`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
While DG models may not always have to run on Graphical Process Units (GPUs), enabling GPUs will improve the computational efficiency by orders of magnitude,
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-P24-CLAIM` | `Claim` | "enabling GPUs will improve the computational efficiency by orders of magnitude" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0104 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0006`
- Unit offsets: `1419:1566`
- Document offsets: `45851:45998`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Our position is that in most cases, the cost is well justified due to the potential to interrogate into the model, make changes, and learn physics.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0006` | `PUB-N-A-P24-CLAIM` | `Claim` | "Our position is that in most cases, the cost is well justified due to the potential to interrogate into the model, make changes, and learn physics" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0105 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0007`
- Unit offsets: `1677:1893`
- Document offsets: `46109:46325`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
As an example, Feng et al.<sup>102</sup> implemented the conceptual hydrologic model HBV (a system of ODEs) on PyTorch and used coupled NNs for parameterization and optionally replaced processes with NNs (Figure 4a).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0007` | `PUB-N-A-DOM03B-CONCEPTUALMODEL` | `ConceptualModel` | "HBV" | `validated` | `validated` |
| `node-0008` | `PUB-N-A-DOM02-TOOL-NEW-FROM-PUBLICATION-PROSE` | `Tool` | "PyTorch" | `validated` | `validated` |
| `node-0009` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "coupled NNs" | `validated` | `validated` |
| `node-0010` | `PUB-N-A-P15-EXAMPLES` | `Examples` | "As an example, Feng et al.<sup>102</sup> implemented the conceptual hydrologic model HBV (a system of ODEs) on PyTorch and used coupled NNs for parameterization and optionally replaced processes with NNs (Figure 4a)." | `validated` | `validated` |
| `node-0011` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Feng et al.<sup>102</sup> implemented the conceptual hydrologic model HBV (a system of ODEs) on PyTorch and used coupled NNs for parameterization and optionally replaced processes with NNs" | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0106 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0008`
- Unit offsets: `1894:2171`
- Document offsets: `46326:46603`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Strikingly, they approached the performance level of LSTM, giving a median Nash Sutcliffe model Efficiency coefficient (NSE) of 0.732 for the CAMELS streamflow benchmark, compared to LSTM's 0.748 for the same dataset, or 0.715 vs. 0.722 for another forcing dataset (Figure 4b).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "LSTM" | `validated` | `validated` |
| `node-0013` | `PUB-N-A-DOM11-EVALUATIONMETRIC` | `EvaluationMetric` | "Nash Sutcliffe model Efficiency coefficient (NSE)" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "CAMELS streamflow benchmark" | `validated` | `validated` |
| `node-0015` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "streamflow" | `validated` | `validated` |
| `node-0016` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "they approached the performance level of LSTM, giving a median Nash Sutcliffe model Efficiency coefficient (NSE) of 0.732 for the CAMELS streamflow benchmark, compared to LSTM's 0.748 for the same dataset, or 0.715 vs. 0.722 for another forcing dataset" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0107 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0009`
- Unit offsets: `2172:2307`
- Document offsets: `46604:46739`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
They also output untrained variables such as evapotranspiration and baseflow, which agreed well with alternative estimates (Figure 4e).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0017` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "evapotranspiration" | `validated` | `validated` |
| `node-0018` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "baseflow" | `validated` | `validated` |
| `node-0019` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "They also output untrained variables such as evapotranspiration and baseflow, which agreed well with alternative estimates" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0108 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0010`
- Unit offsets: `2308:2570`
- Document offsets: `46740:47002`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Moreover, in spatial extrapolation test cases, the differentiable model outperformed LSTM with respect to daily metrics and decadal trends<sup>116</sup> (Figure 4 c-d) due to the structural constraints, demonstrating its potential for global hydrologic modeling.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0020` | `PUB-N-A-DOM05-CONCEPT` | `Concept` | "structural constraints" | `validated` | `validated` |
| `node-0021` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "in spatial extrapolation test cases, the differentiable model outperformed LSTM with respect to daily metrics and decadal trends<sup>116</sup> (Figure 4 c-d) due to the structural constraints, demonstrating its potential for global hydrologic modeling" | `validated` | `validated` |

Descriptive review flags: `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0109 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0011`
- Unit offsets: `2571:2797`
- Document offsets: `47003:47229`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Similarly, Jiang et al.118 encoded the hydrologic model EXP-HYDRO as a recurrent NN architecture and coupled it with fully connected NNs which served as the parameterization pipeline as well as postprocessor to improve runoff.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0022` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "EXP-HYDRO" | `validated` | `validated` |
| `node-0023` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "recurrent NN architecture" | `validated` | `validated` |
| `node-0024` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "fully connected NNs" | `validated` | `validated` |
| `node-0025` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "runoff" | `validated` | `validated` |
| `node-0026` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Jiang et al.118 encoded the hydrologic model EXP-HYDRO as a recurrent NN architecture and coupled it with fully connected NNs which served as the parameterization pipeline as well as postprocessor to improve runoff" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0110 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0012`
- Unit offsets: `2798:2941`
- Document offsets: `47230:47373`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
They showed that a symbiotic integration between NN and physics led to robust transferability and that snow water equivalent was well captured.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0027` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "snow water equivalent" | `validated` | `validated` |
| `node-0028` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "They showed that a symbiotic integration between NN and physics led to robust transferability and that snow water equivalent was well captured" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0111 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0013`
- Unit offsets: `2942:3084`
- Document offsets: `47374:47516`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
In the Biogeosciences or ecosystem modeling, differentiable models found improved parameters for photosynthesis<sup>123</sup> at large scales.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0029` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "photosynthesis" | `validated` | `validated` |
| `node-0030` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "In the Biogeosciences or ecosystem modeling, differentiable models found improved parameters for photosynthesis<sup>123</sup> at large scales" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0112 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0014`
- Unit offsets: `3086:3250`
- Document offsets: `47518:47682`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Apart from models similar to ODEs, direct differentiation can also be applied to models operating on graphs representing the natural systems such as river networks.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0031` | `PUB-N-A-P13-METHOD` | `Method` | "direct differentiation" | `validated` | `validated` |
| `node-0032` | `PUB-N-A-DOM07B-RIVERREACH` | `RiverReach` | "river networks" | `validated` | `validated` |

Descriptive review flags: `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0113 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0015`
- Unit offsets: `3251:3539`
- Document offsets: `47683:47971`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Bindas et al.<sup>124</sup> created a differentiable river routing model that was trained on daily discharge at a gauge downstream of a river network (with pretrained LSTM producing runoff as inputs to the graph) to learn a parameterization scheme for Manning's roughness coefficient (n).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-DOM03D-MLMODEL` | `MLModel` | "LSTM" | `validated` | `validated` |
| `node-0025` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "runoff" | `validated` | `validated` |
| `node-0033` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "daily discharge" | `validated` | `validated` |
| `node-0034` | `PUB-N-A-DOM07C-GAUGE` | `Gauge` | "gauge" | `validated` | `validated` |
| `node-0035` | `PUB-N-A-DOM07B-RIVERREACH` | `RiverReach` | "river network" | `validated` | `validated` |
| `node-0036` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "Manning's roughness coefficient (n)" | `validated` | `validated` |
| `node-0037` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Bindas et al.<sup>124</sup> created a differentiable river routing model that was trained on daily discharge at a gauge downstream of a river network (with pretrained LSTM producing runoff as inputs to the graph) to learn a parameterization scheme for Manning's roughness coefficient (n)" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `LONG_DISCOURSE_LABEL`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0114 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0016`
- Unit offsets: `3540:3655`
- Document offsets: `47972:48087`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
They obtained a power-law-like curve between n and catchment area that was consistent with the expected n behavior.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0038` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "catchment area" | `validated` | `validated` |
| `node-0039` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "They obtained a power-law-like curve between n and catchment area that was consistent with the expected n behavior" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0115 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0017`
- Unit offsets: `3656:3861`
- Document offsets: `48088:48293`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Similarly, Bao et al.<sup>125</sup> implemented an advective dispersion equation on the river graph to simulate stream water temperature and found that the model performed better in data-sparse situations.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0040` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "stream water temperature" | `validated` | `validated` |
| `node-0041` | `PUB-N-A-P18-RELATEDRESEARCH` | `RelatedResearch` | "Bao et al.<sup>125</sup> implemented an advective dispersion equation on the river graph to simulate stream water temperature and found that the model performed better in data-sparse situations" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0116 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0018`
- Unit offsets: `4065:4197`
- Document offsets: `48497:48629`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
For temporal test using NLDAS forcings, δ models can approach the performance of LSTM and greatly outperform traditional approaches;
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0042` | `PUB-N-A-P25-DATASETMENTION-NEW-FROM-PROSE` | `DatasetMention` | "NLDAS forcings" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0117 — DEV-08

- Source unit: `pub:243:sec:0013:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0019`
- Unit offsets: `4243:4306`
- Document offsets: `48675:48738`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
train in some regions and test in another large ungauged region
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0043` | `PUB-N-A-P26-DATADESCRIPTION` | `DataDescription` | "train in some regions and test in another large ungauged region" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0118 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0001`
- Unit offsets: `36:106`
- Document offsets: `5688:5758`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
TELEMAC-2D simulates the depth-averaged shallow water equations (SWE).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "TELEMAC-2D" | `validated` | `validated` |

Descriptive review flags: `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0119 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0002`
- Unit offsets: `205:295`
- Document offsets: `5857:5947`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
FV is used in this study because it easily handles dry areas compared to FE in TELEMAC-2D.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0002` | `PUB-N-A-P13-METHOD` | `Method` | "FV" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0120 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0003`
- Unit offsets: `296:332`
- Document offsets: `5948:5984`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The Courant number is set to be 0.94
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "Courant number" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0121 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0004`
- Unit offsets: `296:426`
- Document offsets: `5948:6078`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The Courant number is set to be 0.94, and time steps are varied accordingly throughout the simulation to closely match this value.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "time steps" | `validated` | `validated` |

Descriptive review flags: `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0122 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0005`
- Unit offsets: `428:499`
- Document offsets: `6080:6151`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
SISYPHE utilizes the Exner equation for bed sediment mass conservation.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "SISYPHE" | `validated` | `validated` |
| `node-0006` | `PUB-N-A-P13-METHOD` | `Method` | "Exner equation" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`, `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0123 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0006`
- Unit offsets: `500:581`
- Document offsets: `6152:6233`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The Meyer-Peter and Muller (1948) formula is used for modeling bedload transport.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0007` | `PUB-N-A-P13-METHOD` | `Method` | "Meyer-Peter and Muller (1948) formula" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0124 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0007`
- Unit offsets: `582:788`
- Document offsets: `6234:6440`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
A correction is made to the direction of the sediment transport to account for secondary currents and transverse slopes using the van Bendegom equation (van Bendegom, 1947) reported in Talmon et al. (1995).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0008` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "direction of the sediment transport" | `validated` | `validated` |
| `node-0009` | `PUB-N-A-P13-METHOD` | `Method` | "van Bendegom equation" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0125 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0008`
- Unit offsets: `789:878`
- Document offsets: `6441:6530`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Another correction is made to the critical shear stress value using the Soulsby equation.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0010` | `PUB-N-A-DOM12-PARAMETER` | `Parameter` | "critical shear stress value" | `validated` | `validated` |
| `node-0011` | `PUB-N-A-P13-METHOD` | `Method` | "Soulsby equation" | `validated` | `validated` |

Descriptive review flags: `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0126 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0009`
- Unit offsets: `880:1003`
- Document offsets: `6532:6655`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Two options are available for integrating TELEMAC-2D and SISYPH to develop the T2D/SIS couple: fully coupled and decoupled.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "T2D/SIS couple" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0127 — DEV-09

- Source unit: `pub:270:sec:0005:unit:0001`
- Section role: `other`
- Evidence span: `evidence-0010`
- Unit offsets: `1400:1535`
- Document offsets: `7052:7187`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
TELEMAC-2D and SISYPHE are fully coupled in this study for better temporal and spatial estimation of breach evolution (Hervouet, 2007).
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0013` | `PUB-N-A-P13-METHOD` | `Method` | "fully coupled" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "breach evolution" | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MANY_CANDIDATES_SAME_TARGET_SAME_UNIT`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0128 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0001`
- Unit offsets: `21:221`
- Document offsets: `12418:12618`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
This study compares the performance of TELEMAC-2D/SISYPHE with the USC slumping model to simulate the breaching of the Upper Rocky Ford dam during the historic flood in October 2015 in South Carolina.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0001` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "TELEMAC-2D/SISYPHE" | `validated` | `validated` |
| `node-0002` | `PUB-N-A-DOM03A-PROCESSBASEDMODEL` | `ProcessBasedModel` | "USC slumping model" | `validated` | `validated` |
| `node-0006` | `PUB-N-A-DOM08-NAMEDPLACE` | `NamedPlace` | "South Carolina" | `validated` | `validated` |
| `node-0007` | `PUB-N-A-P06-THEME` | `Theme` | "the breaching of the Upper Rocky Ford dam during the historic flood in October 2015 in South Carolina" | `validated` | `validated` |
| `node-0008` | `PUB-N-A-P09-RESEARCHGOAL` | `ResearchGoal` | "This study compares the performance of TELEMAC-2D/SISYPHE with the USC slumping model to simulate the breaching of the Upper Rocky Ford dam during the historic flood in October 2015 in South Carolina." | `validated` | `validated` |
| `node-0009` | `PUB-N-A-P13-METHOD` | `Method` | "compares the performance of TELEMAC-2D/SISYPHE with the USC slumping model" | `validated` | `validated` |
| `node-0010` | `PUB-N-A-P14-EXPERIMENT` | `Experiment` | "This study compares the performance of TELEMAC-2D/SISYPHE with the USC slumping model to simulate the breaching of the Upper Rocky Ford dam during the historic flood in October 2015 in South Carolina." | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_DIFFERENT_TARGET`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0129 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0002`
- Unit offsets: `223:344`
- Document offsets: `12620:12741`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
The slumping model showed a slightly better comparison of the breach evolution with the final measured breach dimensions.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0003` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "breach evolution" | `validated` | `validated` |
| `node-0011` | `PUB-N-A-P16-FINDING` | `Finding` | "The slumping model showed a slightly better comparison of the breach evolution with the final measured breach dimensions." | `validated` | `validated` |

Descriptive review flags: `IDENTICAL_LABEL_MULTIPLE_EVIDENCE`, `MULTI_CLASS_EVIDENCE`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0130 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0003`
- Unit offsets: `311:343`
- Document offsets: `12708:12740`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
final measured breach dimensions
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0004` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "final measured breach dimensions" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0131 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0005`
- Unit offsets: `345:408`
- Document offsets: `12742:12805`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
TELEMAC-2D/SISYPHE tends to underestimate the breach dimensions
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0012` | `PUB-N-A-P16-FINDING` | `Finding` | "TELEMAC-2D/SISYPHE tends to underestimate the breach dimensions" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0132 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0006`
- Unit offsets: `345:602`
- Document offsets: `12742:12999`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
TELEMAC-2D/SISYPHE tends to underestimate the breach dimensions while having an unsymmetric final breach with an apparent deviation in the erosion rate from one breach side to another, showing the need for improvement in the hydrodynamic and erosion models.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0013` | `PUB-N-A-P16-FINDING` | `Finding` | "having an unsymmetric final breach" | `validated` | `validated` |
| `node-0014` | `PUB-N-A-P16-FINDING` | `Finding` | "an apparent deviation in the erosion rate from one breach side to another" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0133 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0004`
- Unit offsets: `484:496`
- Document offsets: `12881:12893`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
erosion rate
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0005` | `PUB-N-A-DOM04-VARIABLE` | `Variable` | "erosion rate" | `validated` | `validated` |

Descriptive review flags: `VERY_SHORT_DOMAIN_LABEL`

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0134 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0007`
- Unit offsets: `530:602`
- Document offsets: `12927:12999`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
showing the need for improvement in the hydrodynamic and erosion models.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0015` | `PUB-N-A-P19-LIMITATION` | `Limitation` | "the need for improvement in the hydrodynamic and erosion models" | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:


## C2B-EVID-0135 — DEV-10

- Source unit: `pub:270:sec:0010:unit:0001`
- Section role: `conclusion`
- Evidence span: `evidence-0008`
- Unit offsets: `603:766`
- Document offsets: `13000:13163`
- Authentic evidence valid: `true`
- C2A diagnostic evidence valid: `true`
- C2A status is diagnostic only: `true`

Exact evidence text:

~~~~text
Integrating the slumping model with TELEMAC-2D is recommended for a better simulation of both dam breach evolution and downstream flood inundation in future works.
~~~~

Candidates:

| Candidate | Target | Class | Label | Authentic | C2A diagnostic |
|---|---|---|---|---|---|
| `node-0016` | `PUB-N-A-P22-FUTUREWORK` | `FutureWork` | "Integrating the slumping model with TELEMAC-2D is recommended for a better simulation of both dam breach evolution and downstream flood inundation in future works." | `validated` | `validated` |

Descriptive review flags: none

Researcher semantic assessment:

- [ ] Appropriate ontology assignment(s)
- [ ] Potential over-classification
- [ ] Potential under-classification
- [ ] Wrong ontology class
- [ ] Granularity concern
- [ ] Candidate redundancy concern
- [ ] Label concern
- [ ] Other

Researcher notes:
