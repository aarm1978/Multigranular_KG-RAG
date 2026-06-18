# Ontology Inventory — Study 2 (Phase 1 closure)

**Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**
**Companion to `Study2_Ontology_v0.1.md` (concepts + namespaces §3.1). Vocabulary reuse verified (validation 1); schema fit-checked on 6 real artifacts (validation 2, Etapa A) — GO, with the schema-change log below applied.**

## Legend

- **Status (S/E/F):** `S` supported-now; `E` extract-where-evidence (declared; instances where a citable span exists; coverage/precision reported); `F` future-only (declared, not attempted).
- **Reuse anchor:** concrete CURIE, or `ciroh:` (the CIROH layer = contribution). CodeMeta is a **profile** (properties + schema.org classes), not a class source. CFF is an **evidence format**, not a vocabulary. PEO is a cited paper (no OWL); discourse classes reuse DEO where available else `ciroh:`.
- IDs stable across versions: `A-*` entities, `B-*` categories, `C-*` intra-module relations, `D-*` global relations, `E-*` competency questions.

---

# Part 1 — Shared cross-cutting layers

## Provenance — Table A
| # | Class | Kind | Extraction | Locus | Reuse anchor | Status |
|---|---|---|---|---|---|---|
| A-PROV01 | `EvidenceSpan` | metadata | det+llm | every node/edge | `prov:Entity`; RO-Crate | S |

Constraint: `hasEvidence min 1` on every node/edge; `wasExtractedBy → prov:Activity`. No Table B.

## Identifier backbone — Table A (deterministic; no Table B)
| # | Class | Locus | Reuse anchor | Status |
|---|---|---|---|---|
| A-ID01 | `Identifier` | DOI / `resource_id` / repo URL+SHA / page URL / ORCID / ROR / geoconnex / **related DOI** | `datacite:Identifier` (+ `datacite:relatedIdentifier` for archived snapshots) | S |

## Agent — Table A (schema.org primary; not mixed with FOAF)
| # | Class | Extraction | Locus | Reuse anchor | Status |
|---|---|---|---|---|---|
| A-AG01 | `Person` (`Author`/`Creator`/`Contributor` roles) | hybrid | creators / author block / `contributors.json` / doc lines | `schema:Person` (primary; `foaf:Person` optional equiv) | S |
| A-AG02 | `Organization` | det | affiliation; `awards[].funding_agency` | `schema:Organization` + ROR | S |

Person canonicalization across four regimes (ORCID / name+affiliation+email / name+email / GitHub login). **Confirmed at scale:** `jmframe` (GitHub login) = J.M. Frame (paper author, ORCID) — one Person across two artifact types.

**Agent relations.**
| # | Relation | Domain → Range | Reuse anchor | Evidence locus | Status |
|---|---|---|---|---|---|
| A-AG-R1 | `affiliatedWith` | `Person` → `Organization` | `schema:affiliation` / `org:` | affiliation block (det) | S |
| A-AG-R2 | `fundedBy` | `Paper`/`DatasetResource` → `Award`; `Award` → `Organization` | `schema:funder` / `ciroh:` | acknowledgments / `awards[]` (det) | S |

> `hasAuthor`/`hasCreator`/`hasContributor` are declared in the module Tables C (C-P01, C-D03, C-C04, C-DC05). `Award` is `A-D09`.


## Shared CIROH domain-entity layer — Table A (the contribution)
| # | Class | Kind | Extraction | Locus | Reuse anchor | Status |
|---|---|---|---|---|---|---|
| A-DOM01 | `SoftwareEntity` (abstract) | domain | — | — | `schema:SoftwareApplication` (CodeMeta = profile) | S |
| A-DOM02 | `Tool` ⊏ `SoftwareEntity` | domain | LLM | prose across artifact types | `schema:SoftwareApplication` | S |
| A-DOM03 | `ComputationalModel` (abstract) ⊏ `SoftwareEntity` | domain | LLM | prose | `ciroh:` under `schema:SoftwareApplication`/`SoftwareSourceCode` | S |
| A-DOM03a | `ProcessBasedModel` (VIC, Noah-MP, NWM, SWAT, CFE) | domain | LLM | prose | `ciroh:` | S |
| A-DOM03b | `ConceptualModel` (leaky bucket/tank) | domain | LLM | prose | `ciroh:` | S |
| A-DOM03c | `StatisticalModel` (named statistical model with own identity) | domain | LLM | prose | `ciroh:` | **E (vestigial — regression resolves to `Method`)** |
| A-DOM03d | `MLModel`/`DataDrivenModel` (LSTM, RF) | domain | LLM | prose | `ciroh:` | S |
| A-DOM04 | `Variable` | domain | LLM | abstract/README/paper/doc prose | `schema:variableMeasured`/`PropertyValue`; CF Standard Names | E |
| A-DOM05 | `Concept` | domain | LLM | prose | `skos:Concept` | S |
| A-DOM06 | `Place` (abstract) | domain | — | — | `schema:Place` | S |
| A-DOM07 | `HydrologicFeature` (abstract) ⊏ `Place` | domain | hybrid | prose; geoconnex | `geo:Feature`, typed by `hyf:` (geometry via `geo:hasGeometry`) | S/E |
| A-DOM07a | `Watershed`/`HydrologicUnit` (HUC) | domain | hybrid | prose; `geospatial_relations` | `hyf:HY_Catchment`; geoconnex `ref/hu*` | S/E |
| A-DOM07b | `RiverReach` (COMID) | domain | hybrid | prose; geoconnex | `hyf:HY_FlowPath`/`HY_River`; geoconnex `ref/mainstems` | S/E |
| A-DOM07c | `Gauge`/`MonitoringStation` (USGS Gages, SNOTEL) | domain | hybrid | prose; geoconnex | `hyf:HY_HydrometricFeature`; geoconnex `ref/gages` | S/E |
| A-DOM07d | `WaterBody` | domain | LLM | prose | `hyf:HY_WaterBody` | E |
| A-DOM07e | `Aquifer` | domain | LLM | prose | geoconnex `ref/aquifers`; else `ciroh:` | E |
| A-DOM07f | `VPU` | domain | hybrid | prose/config | `ciroh:` (NHDPlus VPU) | E |
| A-DOM08 | `NamedPlace` ⊏ `Place` (**not CIROH** — admin places) | domain | LLM | prose ("Western US", "Italy", "Gulf Coast") | `gn:Feature` (GeoNames ≥ 2.2.1) | E |
| A-DOM09 | `SpatialCoverage` (declared footprint — not a place) | metadata | det | `spatial_coverage` bbox | `geo:Geometry` + `dcterms:spatial` | S |
| A-DOM10 | `TemporalCoverage` | metadata | det | `temporal_coverage` | `dcterms:temporal` | S |
| A-DOM11 | `EvaluationMetric`/`PerformanceMetric` (NSE, RMSE, MAE, KGE, R², R²_Predicted, VIF, Durbin-Watson, sign test, bias) | domain | LLM | results prose / metric tables | `ciroh:` (value as `schema:PropertyValue`) | S |
| A-DOM12 | `Parameter` (attrs `range`, `value`, `calibrationStatus`∈{calibrated,default}) | domain | hybrid | param tables / config / doc | `schema:PropertyValue` | S (E at paper level) |
| A-DOM13 | `Algorithm` (named technique: SCE-UA, DDS) | domain | LLM | prose | `ciroh:` | E |

**Model hierarchy (validation-2 confirmed; all four subtypes lands cleanly).** `StatisticalModel` demoted to **E** — stepwise regression resolved to `Method`, not a model entity (paper 221); it instantiates only if a *named* statistical model with its own identity appears. No intermediate `EmpiricalModel`. Literal `PhysicalModel` (lab-scale) → future, not seen.
**Model / Method / Algorithm discriminant:** *named thing that could own a repo/dataset/paper* → `ComputationalModel`/`Tool`/`Algorithm`; *technique applied* → `Method`. Relations: `Method appliesTo ComputationalModel`; `Method usesAlgorithm Algorithm` (a named algorithm is an entity; applying it is the Method). Cross-cutting shared relations: `reportsMetric`/`evaluates` (`EvaluationMetric`), `hasParameter` (`Parameter`), `usesAlgorithm` (`Algorithm`) — all consolidate like `Variable` (→ D-16).
**Geographic split** (validated at scale — HUC-10, USGS/SNOTEL gauges, VPU): `gn:Feature` for `NamedPlace`; `geo:Feature`/`geo:Geometry` for `HydrologicFeature`/`SpatialCoverage`; never both on one entity. Relation `hasSpatialCoverage`.

---

# Part 2 — Module 1: Research Paper

## PEO grounding (Du & Li 2022)

**Source.** Du, X. & Li, N. (2022). ICBASE 2022, CEUR-WS Vol-3304, paper03, pp. 15–27. No OWL release → cited, not imported.
**Anchoring (Co-occurrence Framework):** `deo:` where DEO co-occurs and has the class (`Background`, `ProblemStatement`, `Motivation`←Research-Goal, `Methods`, `Data`←DataDescription, `Results`, `Evaluation`←Result-Evaluation, `Discussion`, `RelatedWork`, `Scenario`←Examples, `Conclusion`, `Contribution`, `FutureWork`); `ciroh:` (aligned PEO) otherwise (`Theme`, `Research-Significance`, `Theoretical-Basis`, `Definition`, `Experiment`, `Limitation`). `deo:Materials` **not adopted** (validation 2: "materials" decompose into `DatasetMention`/`ProcessBasedModel`/`HydrologicFeature`/`Parameter` — no residual). `deo:Model` not adopted (captured by `EvidenceSpan`). `Research-Content` = scaffolding.
**CIROH additions** (not PEO classes): `ResearchQuestion`, `Hypothesis`, `Claim` (SAO/Micropublications); PEO models argumentation as relations (`argues`/`supports`/`not_support`) which these reuse. `Hypothesis` ≠ `Claim`; `ResearchSignificance` ≠ `Contribution`.
**Relation vocabulary = PEO's 18** (`ciroh:` aligned PEO; RST/SAO). **Internal attributes** `tendency`, `source`. **29 second-level** = E fine layer (Result-Evaluation → `deo:Evaluation`).

## Table A — Entity classes
| # | Class | Kind | Extraction | Reuse anchor | Status |
|---|---|---|---|---|---|
| A-P01 | `Paper` | artifact | hybrid | `fabio:JournalArticle` (ref. IRI) / `schema:ScholarlyArticle`; DataCite | S |
| A-P02 | `Venue` | metadata | det | `fabio:Journal` (ref. IRI); `fabio:hasPublicationVenue` | S |
| A-P03 | `Author` (→ A-AG01) | agent | hybrid | `schema:Person` | S |
| A-P04 | `Subject` (keywords) | metadata | det | `dcterms:subject`; `skos:Concept` | S |
| A-P05 | `Background` | discourse | LLM | `deo:Background` | S |
| A-P06 | `Theme` | discourse | LLM | `ciroh:` (PEO) | S |
| A-P07 | `ResearchProblem` | discourse | LLM | `deo:ProblemStatement` | S |
| A-P08 | `ResearchQuestion` | discourse | LLM | `ciroh:` (CIROH — PEO uses `Problem`) | S |
| A-P09 | `ResearchGoal` | discourse | LLM | `deo:Motivation` | S |
| A-P10 | `ResearchSignificance` | discourse | LLM | `ciroh:` (PEO; ≠ Contribution) | S |
| A-P11 | `Definition` | discourse | LLM | `ciroh:` (PEO) | S |
| A-P12 | `TheoreticalBasis` | discourse | LLM | `ciroh:` (PEO) | S |
| A-P13 | `Method` | discourse | LLM | `deo:Methods` | S |
| A-P14 | `Experiment` | discourse | LLM | `ciroh:` (PEO) | S |
| A-P15 | `Examples` | discourse | LLM | `deo:Scenario` | S |
| A-P16 | `Finding` (Result) | discourse | LLM | `deo:Results` | S |
| A-P17 | `Discussion` | discourse | LLM | `deo:Discussion` | S |
| A-P18 | `RelatedResearch` | discourse | LLM | `deo:RelatedWork` | S |
| A-P19 | `Limitation` | discourse | LLM | `ciroh:` (PEO Discussion-Limitation) | S |
| A-P20 | `Conclusion` | discourse | LLM | `deo:Conclusion` | S |
| A-P21 | `Contribution` | discourse | LLM | `deo:Contribution` (≠ Significance) | S |
| A-P22 | `FutureWork` | discourse | LLM | `deo:FutureWork` | S |
| A-P23 | `Hypothesis` | discourse | LLM | `ciroh:` (CIROH; SAO/Micropublications) | E |
| A-P24 | `Claim` | discourse | LLM | `ciroh:` (CIROH; SAO/Micropublications) | E |
| A-P25 | `DatasetMention` | domain/metadata | hybrid | `deo:ExternalResourceDescription`; DataCite | S |
| A-P26 | `DataDescription` (PEO "Data") | discourse | LLM | `deo:Data` | S |
| (refs) | A-DOM02/03(+leaves)/04/05/11/12/13 + `HydrologicFeature`/`NamedPlace` | domain | LLM/hybrid | Part 1 | S (E: `Variable`, `Algorithm`, `StatisticalModel`) |

> Discourse-unit nodes carry `ciroh:` attributes `tendency` and `source`. Papers reach the promoted shared classes `EvaluationMetric` (A-DOM11), `Parameter` (A-DOM12), `Algorithm` (A-DOM13).

## Table B — Categories (LLM portion)
| # | Category | Region | Reachable entities (→ A) |
|---|---|---|---|
| B-P01 | Background & Motivation | Intro | A-P05, A-P06, A-P09, A-P10, A-DOM05 |
| B-P02 | Problem & Questions | Intro | A-P07, A-P08 |
| B-P03 | Hypotheses & Claims | Intro/Discussion | A-P23, A-P24 |
| B-P04 | Definitions & Theory | body | A-P11, A-P12 |
| B-P05 | Study Area & Setting | Study Area | A-DOM07*, A-DOM08, A-DOM09 |
| B-P06 | Data & Datasets | Data/Methods | A-P25, A-P26, A-DOM04 |
| B-P07 | Methods, Models, Algorithms & Experiments | Methods | A-P13, A-P14, A-DOM03*, A-DOM13 |
| B-P08 | Tools & Software | Methods | A-DOM02 |
| B-P09 | Parameters & Configuration | Methods | A-DOM12 |
| B-P10 | Results, Findings & Metrics | Results | A-P16, A-P15, A-DOM11 |
| B-P11 | Discussion & Interpretation | Discussion | A-P17, A-P19 |
| B-P12 | Conclusions, Contribution & Future Work | Conclusion | A-P20, A-P21, A-P22 |
| B-P13 | Related Work | Related Work | A-P18 |

## Table C — Relations (domain/range)
| # | Relation | Domain → Range | Reuse anchor | Evidence locus | Type | Status |
|---|---|---|---|---|---|---|
| C-P01 | `hasAuthor` | `Paper` → `Author` | `schema:author` | Zotero (det) | intra | S |
| C-P02 | `publishedIn` | `Paper` → `Venue` | `fabio:hasPublicationVenue` | Zotero (det) | intra | S |
| C-P03 | `hasSubject` | `Paper` → `Subject` | `dcterms:subject` | "Keywords:" (det) | intra | S |
| C-P04 | `hasIdentifier` | `Paper` → `Identifier` | DataCite | Zotero/Marker (det) | intra | S |
| C-P05 | `reports`/`hasComponent` | `Paper` → discourse units A-P05–24, A-P26 | `deo:`/`ciroh:` | body chunk (LLM, quote) | intra | S (E: A-P23/24) |
| C-P06 | `resolves`/`addresses` | `Method`/`Contribution` → `ResearchProblem`; `ResearchQuestion` → `ResearchProblem` | `ciroh:` (PEO `resolves`/`leads_to`) | body | intra | S |
| C-P07 | `produces` | `Method`/`Experiment` → `Finding` | `ciroh:` (PEO `produces`, SAO) | Results prose | intra | S |
| C-P08 | `basis`/`testedBy` | `TheoreticalBasis` → `Method`; `Hypothesis` → `Method`/`Experiment` | `ciroh:` (PEO `basis`; `testedBy` CIROH) | body | intra | S (E: testedBy) |
| C-P09 | `supports`/`notSupports`/`argues` | `Finding` → `Claim`/`Conclusion`; `Claim` → `Claim` | `ciroh:` (PEO, SAO) | body | intra | E |
| C-P10 | `review`/`discussesRelatedWork` | `Paper` → `RelatedResearch` | `ciroh:` (PEO `review`) | Related Work | intra | S |
| C-P11 | `relatesTo`/`elaboration` | `RelatedResearch` → `Method`/`TheoreticalBasis`/`Concept`/`ResearchProblem`/`Paper`(stub) | `ciroh:` (PEO) | Related Work prose | intra/cross | S |
| C-P12 | `hasLimitation`/`summary` | `Paper`/`Finding` → `Limitation`; `Conclusion` → `Finding` | `ciroh:` (PEO) | Discussion/Conclusion | intra | S |
| C-P13 | `usesModel` | `Paper`/`Method` → `ComputationalModel` | `ciroh:` (PEO `uses`) | Methods prose (quote) | cross+same | S · consol |
| C-P14 | `appliesTo` | `Method` → `ComputationalModel` | `ciroh:` (Model/Method discriminant) | Methods prose | intra/cross | S |
| C-P15 | `usesTool` | `Paper` → `Tool` | `ciroh:` | prose | cross+same | S · consol |
| C-P16 | `mentionsVariable` | `Paper`/`DataDescription` → `Variable` | `ciroh:` | prose (quote) | cross+same | E · consol |
| C-P17 | `studiesFeature` | `Paper`/`Method` → `HydrologicFeature` | `ciroh:` | Study Area + geoconnex | cross+same | S · consol |
| C-P18 | `studiesPlace` | `Paper`/`Method` → `NamedPlace` | `ciroh:` | prose | cross+same | E |
| C-P19 | `hasSpatialCoverage` | `Paper`/`Place` → `SpatialCoverage` | `ciroh:` (≈ `geo:hasGeometry`) | declared extent | intra | E |
| C-P20 | `usesDataset` | `Paper` → `DatasetMention`/`DatasetResource` | `ciroh:` | data-availability URL (det) + prose | cross | S · consol (→ D-01) |
| C-P21 | `cites` (+ typed) | `Paper` → `Paper`(stub) | `cito:cites` (+ `citesAsEvidence`/`usesMethodIn`/`extends`) | reference DOI (det) | same | S (→ D-08) |
| C-P22 | `corrects`/`isCorrigendumOf` | `Paper` → `Paper` | `cito:`/`ciroh:` | corrigendum record (det) | same | S (→ D-09) |
| C-P23 | `mentionsModel` | `Paper` → `ComputationalModel` | `ciroh:` (mentioned, **not** used; ≠ C-P13) | related-work prose (quote) | cross+same | S · consol |
| C-P24 | `mentionsDataset` | `Paper` → `DatasetMention`/`DatasetResource` | `ciroh:` (≠ C-P20) | prose (quote) | cross | S |
| C-P25 | `reportsMetric` | `Finding`/`Experiment` → `EvaluationMetric` | `ciroh:` | Results / metric tables (quote) | intra · consol | S |
| C-P26 | `evaluates` | `EvaluationMetric` → `ComputationalModel`/`Method` | `ciroh:` | Results prose | intra | S |
| C-P27 | `hasParameter` | `Method`/`Experiment`/`ComputationalModel` → `Parameter` | `schema:` (`PropertyValue`) | param tables / prose (quote) | intra · consol | S (E paper) |
| C-P28 | `usesAlgorithm` | `Method` → `Algorithm` | `ciroh:` | Methods prose (quote) | intra · consol | E |

> Remaining PEO relations (`condition`, `motivation`, `background`, `introduces`, `improves`, `guides`, `purpose-behavior`) declared `ciroh:`, instantiated extract-where-evidence.

---

# Part 3 — Module 2: Dataset (HydroShare)

## Table A — Entity classes
| # | Class | Kind | Extraction | Locus | Reuse anchor | Status |
|---|---|---|---|---|---|---|
| A-D01 | `DatasetResource` | artifact | hybrid | `meta_dump`/`sys_meta` | `schema:Dataset`; DataCite; `prov:Entity`; `hsterms` | S |
| A-D02 | `ResourceType` (Composite/Collection/Tool) | metadata | det | `resource_type` | `ciroh:` (controlled) | S |
| A-D03 | `File` (inventory) | metadata | det | `file_inventory` | `schema:DataDownload` | S |
| A-D04 | `Creator` (→ A-AG01) | agent | det | `creators[]` | `schema:Person` | S |
| A-D05 | `License` | metadata | det | `rights` | `dcterms:license`; SPDX | S |
| A-D06 | `Subject` | metadata | det | `subjects[]` | `dcterms:subject`; `skos:Concept` | S |
| A-D07 | `SpatialCoverage` (→ A-DOM09) | metadata | det | `spatial_coverage` | `geo:Geometry`; `dcterms:spatial` | S |
| A-D08 | `TemporalCoverage` (→ A-DOM10) | metadata | det | `temporal_coverage` | `dcterms:temporal` | S |
| A-D09 | `Award`/funding | metadata | det | `awards[]` | `schema:Grant`; `prov` | S |
| A-D10 | `ToolConfiguration` (ToolResource) | metadata | det | `tool_config` | `ciroh:` + `schema:WebApplication`/`url` | S |
| A-D11 | `Variable` (→ A-DOM04) | domain | LLM | abstract/README prose | `schema:variableMeasured`; CF | E |
| A-D12 | `Measurement` | domain | LLM | README prose | `ciroh:` | **E · coverage ≈ 0 · demote-candidate** |
| (refs) | A-DOM02/03 + `HydrologicFeature` (via `geospatial_relations`); `EvaluationMetric`/`Parameter` (where README reports them) | domain | LLM/det | abstract/README; geoconnex | Part 1 | S/E |

> Three subtypes (corpus JSON): Composite has files; Collection groups members (no own files); Tool has `tool_config`, no files. `Measurement` did not fire across the validated artifacts (corpus does not open data files); the useful distinction is `Variable` vs `DatasetMention`.

## Table B — Categories (LLM portion = abstract + README)
| # | Category | Reachable entities (→ A) |
|---|---|---|
| B-D01 | Resource Purpose & Scope | A-DOM05, A-DOM02, A-DOM03* |
| B-D02 | Models/Tools Referenced | A-DOM03*, A-DOM02 |
| B-D03 | README: Contents & File Roles | A-C11 (Workflow), A-DOM05 |
| B-D04 | README: Workflow / Usage | A-C11, A-DOM02 |
| B-D05 | README: Variables & Measurements | A-D11, A-D12 |
| B-D06 | README: External References | A-P01, A-C01, A-D01 (→ D-05/D-19) |

## Table C — Relations
| # | Relation | Domain → Range | Reuse anchor | Evidence locus | Type | Status |
|---|---|---|---|---|---|---|
| C-D01 | `hasResourceType` | `DatasetResource` → `ResourceType` | `ciroh:` | `resource_type` (det) | intra | S |
| C-D02 | `hasFile` | → `File` | `schema:distribution` | `file_inventory` (det) | intra | S |
| C-D03 | `hasCreator` | → `Creator` | `dcterms:creator` | `creators[]` (det) | intra | S |
| C-D04 | `hasIdentifier` | → `Identifier` | DataCite | `resource_id`/DOI (det) | intra | S |
| C-D05 | `hasLicense` | → `License` | `dcterms:license` | `rights` (det) | intra | S |
| C-D06 | `hasSubject` | → `Subject` | `dcterms:subject` | `subjects[]` (det) | intra | S |
| C-D07 | `hasSpatialCoverage` | → `SpatialCoverage` | `geo:hasGeometry`/`dcterms:spatial` | `spatial_coverage` (det) | intra | S |
| C-D08 | `coversPeriod` | → `TemporalCoverage` | `dcterms:temporal` | `temporal_coverage` (det) | intra | S |
| C-D09 | `fundedBy` | → `Award`/`Organization` | `schema:funding` | `awards[]` (det) | prov | S |
| C-D10 | `hasToolConfig` | `DatasetResource`(Tool) → `ToolConfiguration` | `ciroh:` | `tool_config` (det) | intra | S |
| C-D11 | `launchesApp` | `ToolConfiguration` → `Tool` | `ciroh:` | `app_home_page_url` / app-launching URL pattern | cross | S |
| C-D12 | `hasMember` | `DatasetResource`(Collection) → `DatasetResource` | `dcterms:hasPart` | `members[].member_resource_id` (det) | same | S |
| C-D13 | `isMemberOf` | `DatasetResource` → `DatasetResource`(Collection) | `dcterms:isPartOf` | `hydroshare_links`/`target_resource_id` (det) | same | S |
| C-D14 | `derivedFrom`/`versionedFrom` | → `DatasetResource` | `prov:wasDerivedFrom` | `typed_relations` (det)/prose | same | S/E |
| C-D15 | `referencesFeature` | → `HydrologicFeature` | `ciroh:` | `geospatial_relations` geoconnex URI (det) | cross | S · consol |
| C-D16 | `containsVariable` | → `Variable` | `ciroh:` | abstract/README prose (quote) | intra | E |
| C-D17 | `hasMeasurement` | → `Measurement` | `ciroh:` | README prose | intra | E |
| C-D18 | `mentionsModel`/`usesTool` | → `ComputationalModel`/`Tool` | `ciroh:` | abstract/README prose | cross+same | S · consol |
| C-D19 | `references` (README URLs / citation) | → `Paper`/`Repository`/`DatasetResource` | `cito:citesAsDataSource` (paper→dataset) / `dcterms:references` | README URL regex / `related_resources` DOI (det) | cross | S (→ D-05) |
| C-D20 | `isExecutedBy` | `DatasetResource` → `Tool` | `ciroh:` (alignment: `hsterms:isExecutedBy`) | `typed_relations` `hsterms:isExecutedBy` / `target_resource_id` (det) | cross | S · consol |
| C-D21 | `executes` | `Tool` → `DatasetResource` | `ciroh:` | inverse of `isExecutedBy` | cross | S |

---

# Part 4 — Module 3: Code Repository

> **File model:** one `File` class with derived `fileRole` (filename+ext+path), `downloaded` flag, `selectionReason` (raw rule). **Validated:** `deep_bucket_lab` 5/25 downloaded with explicit `selection_reason` — the selection policy is a visible methodological contribution. `Function`/`Algorithm` live in source files (`.py`) → `F` (no AST) / `E` (README describes at file level). CodeMeta = profile; CITATION.cff/CITATION.md = evidence format.

## Table A — Entity classes
| # | Class | Kind | Extraction | Locus | Reuse anchor | Status |
|---|---|---|---|---|---|---|
| A-C01 | `Repository` (+`fork` flag, `RepositoryPurpose`, `commitSHA`) | artifact | hybrid | `repo_metadata`/`archive_info` | `schema:SoftwareSourceCode` (CodeMeta profile; DOAP — ref. IRIs) | S |
| A-C02 | `File` (`fileRole`; `downloaded`; `selectionReason`) | metadata | det | `files_manifest` | `schema:MediaObject` | S |
| A-C03 | `Dependency` | metadata | det | dependency-manifest files | `schema:SoftwareApplication` (target of `schema:softwareRequirements`) | S |
| A-C04 | `ExecutionEnvironment` | metadata | det | Dockerfile/`environment.yml` | `ciroh:` (`codemeta:runtimePlatform`) | S |
| A-C05 | `Person`/`Contributor` (→ A-AG01) | agent | det | `contributors.json` | `schema:Person` | S |
| A-C06 | `License` | metadata | det | `repo_metadata.license` | SPDX | S |
| A-C07 | `RepositoryPurpose` | metadata | LLM (controlled) | README | `ciroh:` (controlled) | S |
| A-C08 | `Function` | domain | LLM (prose only) | dossier files | `ciroh:` | E |
| A-C09 | `Algorithm` (→ A-DOM13, shared) | domain | LLM (prose only) | dossier files | `ciroh:` | E |
| A-C10 | `ModelVersion` | metadata | hybrid | release tags / `CITATION.cff` / README | `schema:softwareVersion`; `ciroh:` | E |
| A-C11 | `Workflow` (shared w/ doc) | domain | LLM | README/notebook md | `p-plan:Plan`; `schema:HowTo` | S |
| (refs) | A-DOM02/03/04/05/11/12/13; `Parameter` | domain | LLM | prose | Parts 1, 5 | S (E: Variable/Param/Algorithm) |

> `CITATION.cff`/`CITATION.md` = deterministic **evidence locus** feeding `Person`/`Identifier` and the repo→paper link (`codemeta:referencePublication`), not a class.

## Table B — Categories (content-based, over the priority-ordered *dossier*)
| # | Category | Reachable entities (→ A) |
|---|---|---|
| B-C01 | Repository Purpose & Overview | A-C07, A-DOM05, A-DOM02, A-DOM03* |
| B-C02 | Installation & Environment | A-C04, A-C03 (context), A-DOM05 |
| B-C03 | Usage & Workflow | A-C11, A-DOM02 |
| B-C04 | Tools/Models Referenced | A-DOM02, A-DOM03* |
| B-C05 | Functions/Algorithms (prose) | A-C08, A-DOM13 |
| B-C06 | Variables/Parameters (prose) | A-DOM04, A-DOM12 |
| B-C07 | External References & Citations | A-P01, A-D01, A-C01 (→ D) |

## Table C — Relations
| # | Relation | Domain → Range | Reuse anchor | Evidence locus | Type | Status |
|---|---|---|---|---|---|---|
| C-C01 | `hasFile` | `Repository` → `File` | `schema:hasPart` | `files_manifest` (det) | intra | S |
| C-C02 | `dependsOn` | `Repository` → `Dependency` (library) | `schema:softwareRequirements` | dependency-manifest (det) | intra | S |
| C-C03 | `hasExecutionEnvironment` | → `ExecutionEnvironment` | `codemeta:runtimePlatform` | Dockerfile/env (det) | intra | S |
| C-C04 | `hasContributor` | → `Person` | `schema:contributor` | `contributors.json` (det) | intra | S |
| C-C05 | `hasLicense` | → `License` | SPDX | `repo_metadata` (det) | intra | S |
| C-C06 | `hasIdentifier` | → `Identifier` (URL, SHA, DOI) | `schema:codeRepository`; `prov` | `archive_info` (det) | intra | S |
| C-C07 | `hasPurpose` | → `RepositoryPurpose` | `ciroh:` | README (LLM, quote) | intra | S |
| C-C08 | `describesFunction`/`describesAlgorithm` | `Repository` → `Function`/`Algorithm` | `ciroh:` | dossier prose (LLM, quote) | intra | E |
| C-C09 | `hasModelVersion` | → `ModelVersion` | `schema:softwareVersion` | release tag/`CITATION`/README | intra | E |
| C-C10 | `explainsWorkflow`/`documentsUsage` | → `Workflow` | `p-plan:`; `ciroh:` | README/notebook md (LLM) | intra | S |
| C-C11 | `usesTool`/`mentionsModel` | → `Tool`/`ComputationalModel` | `ciroh:` | prose | cross+same | S · consol |
| C-C12 | `mentionsVariable`/`usesParameter` | → `Variable`/`Parameter` | `ciroh:`/`schema:` | prose (quote) | cross+same | E · consol |
| C-C13 | `dependsOnRepository` | `Repository` → `Repository` | `ciroh:` (no standard repo→repo dep) | `github.com` links / dep files | same | S/E |
| C-C14 | `forkedFrom` | `Repository` → `Repository` | `ciroh:` | `fork` flag (det); parent via README/Binder badge | same | flag S · **parent E** |
| C-C15 | `usesDataset` | → `DatasetResource` | `ciroh:` | README/notebook HydroShare URL | cross | S (→ D-01) |
| C-C16 | `implementsMethod` | `Repository`/`Tool` → `Method` (in `Paper`) | `ciroh:` (+ `cito:usesMethodIn` by reference) | README + Methods prose | cross | S (→ D-02) |
| C-C17 | `referencePublication`/`citesPaper` | → `Paper` | `codemeta:referencePublication` (+ `cito:cites`) | `CITATION.cff`/`.md` (det) / prose | cross | S (→ D-07) |
| C-C18 | `archivedAs`/`sameSoftwareAs` | `Repository` → archived DOI snapshot | `datacite:relatedIdentifier` (IsVersionOf/IsDerivedFrom) | repo README DOI ↔ paper-cited DOI (det where matched) | same | E (→ D-20) |

---

# Part 5 — Module 4: Documentation (CIROH Hub)

> **`pageType`:** {product-catalog, product-doc, service-doc, policy, guide, blog-post, news, release-note}; gating **confirmed** (catalog fires the hub, not Procedure/Step; guide fires Procedure/Step, not the hub). **Product = Option B** with **hierarchical aggregation** (a composite product e.g. NGIAB → distributions/components → repos/docs), not flat. Source provenance: "Edit this page" → `.mdx` path. MDX admonitions (`:::warning`/`:::note`) → `Example`/structured note (minor).

## Table A — Entity classes
| # | Class | Kind | Extraction | Reuse anchor | Status |
|---|---|---|---|---|---|
| A-DC01 | `DocumentationPage` (+`pageType`, `datePublished?`, `author?`) | artifact | hybrid | `schema:TechArticle`/`WebPage`; DCMI | S |
| A-DC02 | `Section` | metadata | det | `doco:Section` | S |
| A-DC03 | `Link` | metadata | det | `dcterms:references`; `schema:url` | S |
| A-DC04 | `Subject` (tags) | metadata | det | `dcterms:subject`; `skos:Concept` | S |
| A-DC05 | `Procedure` | instructional | LLM | `schema:HowTo`; `p-plan:Plan` | S |
| A-DC06 | `Step` | instructional | LLM | `schema:HowToStep`; `p-plan:Step` | S |
| A-DC07 | `Parameter` (→ A-DOM12, shared) | instructional | LLM | `schema:PropertyValue` | S |
| A-DC08 | `Example` (incl. MDX admonitions) | instructional | LLM | `schema:SoftwareSourceCode` | S |
| A-DC09 | `Creator`/`Person` (→ A-AG01) | agent | det | `schema:Person` | S |
| (refs) | A-DOM02/03/05/11/13; `Workflow`; `productCategory` on `Tool`/`ComputationalModel` (`ciroh:`) | domain | LLM | Parts 1, 4 | S |

## Table B — Categories (markdown body; genre-aware)
| # | Category | Applies to | Reachable entities (→ A) |
|---|---|---|---|
| B-DC01 | Page Purpose & Overview | all | A-DOM05, A-DOM02 |
| B-DC02 | Tools/Frameworks Described | product/service/blog | A-DOM02, A-DOM03* |
| B-DC03 | Domain Concepts & Policy | policy/product/blog | A-DOM05 |
| B-DC04 | Procedures & Steps | product-doc/service-doc/guide | A-DC05, A-DC06, A-C11 |
| B-DC05 | Parameters & Configuration | product-doc/service-doc/guide | A-DC07 (A-DOM12) |
| B-DC06 | Examples & Commands | product-doc/service-doc/guide | A-DC08 |
| B-DC07 | Product Catalog Entry | product-catalog | A-DOM02/03* (+`productCategory`) → D-06 |
| B-DC08 | Cross-References & Announcements | release-note/blog/all | A-C01, A-D01, A-DC01 (→ D) |

## Table C — Relations
| # | Relation | Domain → Range | Reuse anchor | Evidence locus | Type | Status |
|---|---|---|---|---|---|---|
| C-DC01 | `hasSection` | `DocumentationPage` → `Section` | `doco:hasPart` | heading hierarchy (det) | intra | S |
| C-DC02 | `isPartOf` | → `DocumentationPage` | `dcterms:isPartOf` | path/folder (det) | same | S |
| C-DC03 | `linksTo` | → `Link` | `dcterms:references` | URL regex (det) | intra | S |
| C-DC04 | `hasSubject` | → `Subject` | `dcterms:subject` | frontmatter (det) | intra | S |
| C-DC05 | `hasContributor` | → `Person` | `schema:contributor` | contributor lines (det) | intra | S |
| C-DC06 | `hasSourceFile` | → `File`(in `ciroh_hub`) | `prov:wasDerivedFrom` | "Edit this page" `.mdx` (det) | cross | S |
| C-DC07 | `describesTool` ⊑ `describes` | → `Tool` | `ciroh:` | body prose (LLM, quote) | cross+same | S · consol |
| C-DC08 | `mentionsConcept` | → `Concept` | `skos:Concept` | body (LLM) | intra | S |
| C-DC09 | `explainsWorkflow` | `DocumentationPage`/`Procedure` → `Workflow` | `p-plan:`; `ciroh:` | body (LLM) | intra | S |
| C-DC10 | `hasStep` | `Procedure` → `Step` | `schema:step`; `p-plan:` | body (LLM, quote) | intra | S |
| C-DC11 | `hasParameter` | `Procedure`/`Step` → `Parameter` | `schema:PropertyValue` | body (LLM) | intra | S |
| C-DC12 | `hasExample` | `Procedure`/`Step` → `Example` | `ciroh:` | body code block / admonition | intra | S |
| C-DC13 | `documents`/`mirrors` | → `Repository` | `ciroh:` | `<GitHubReadme repo file>` tag (det) | cross | **S (deterministic — repo+file explicit)** |
| C-DC14 | `referencesRepository` | → `Repository` | `ciroh:` | `github.com` URL (det) | cross | S (→ D-04) |
| C-DC15 | `referencesDataset` | → `DatasetResource` | `ciroh:` | `hydroshare.org/resource/{id}` URL (det) | cross | S (→ D-05) |
| C-DC16 | `describesModel` ⊑ `describes` | → `ComputationalModel` | `ciroh:` | body prose (LLM, quote) | cross+same | S · consol |
| C-DC17 | `catalogs` | `DocumentationPage`(product-catalog) → `Tool`/`ComputationalModel` (product node) | `ciroh:` | product card (det links) | cross | S · consol (→ D-06) |
| C-DC18 | `announces`/`references` | `DocumentationPage`(release-note/blog) → PR(`Repository`)/page/`Tool` | `ciroh:`; `dcterms:references` | dated entry + PR/page links (det) | cross | S |
| C-DC19 | `hasComponent` | product node → component `Tool`/`ComputationalModel`/distribution | `ciroh:` (hierarchical aggregation) | DocCardList / card links (det) | cross | S (→ D-06) |
| C-DC20 | `hasProcedure` | `DocumentationPage` → `Procedure` | `schema:hasPart`/`ciroh:` | body (LLM) | intra | S |
| C-DC21 | `hasSubPage` | `DocumentationPage` → `DocumentationPage` | `ciroh:` | path/folder (det) | same | S; inverse of C-DC02 |

> `Procedure` is reachable both directly (`hasProcedure`) and via `hasSection` (C-DC01) → `Section` → `Procedure`; the explicit edge is what E-09 traverses.

---

# Part 6 — Table D: Global cross-artifact relations

| # | Relation | Domain → Range | Cross/Same | Reuse anchor | Evidence locus | Consol? | Status |
|---|---|---|---|---|---|---|---|
| D-01 | `usesDataset` | `Paper`/`Repository` → `DatasetResource` | cross | `ciroh:` | data-availability / README HydroShare URL (det)+prose | yes | S |
| D-02 | `implementsMethod`/`implementedBy` | `Repository`/`Tool` ↔ `Method`-in-`Paper` | cross | `ciroh:` (+ `cito:usesMethodIn` by reference) | README + Methods prose | via Method/Model | S |
| D-03 | `documents`/`mirrors` | `DocumentationPage` → `Repository` | cross | `ciroh:` | `<GitHubReadme>` tag (det) | yes | S (deterministic) |
| D-04 | `referencesRepository` | `DocumentationPage`/`DatasetResource` → `Repository` | cross | `ciroh:` | `github.com` URL (det) | — | S |
| D-05 | `referencesDataset` | `DocumentationPage`/`Repository`/`Paper` → `DatasetResource` | cross | `cito:citesAsDataSource` (paper→dataset) / `ciroh:` | `hydroshare.org/resource/{id}` URL (det) | yes | S |
| D-06 | product-catalog **hierarchical** aggregation (`catalogs` + `hasComponent` + `implementedBy`+`documentedBy`+`referencesDataset`+`describedInPaper`) | `DocumentationPage`(product-catalog) → product `Tool`/`ComputationalModel` → {components/distributions} → {repo, doc, dataset, paper} | cross | `ciroh:` | product card / DocCardList links (det) | **densest hub** | S |
| D-07 | `referencePublication`/`citesPaper` | `Repository` → `Paper` | cross | `codemeta:referencePublication` (+ `cito:cites`) | `CITATION.cff`/`.md` (det) / prose | — | S |
| D-08 | `cites` (+ typed) | `Paper` → `Paper` | same | `cito:cites` (+ `citesAsEvidence`/`usesMethodIn`/`extends`) | reference DOI (det) | — | S |
| D-09 | `corrects`/`isCorrigendumOf` | `Paper` → `Paper` | same | `cito:`/`ciroh:` | corrigendum record (det) | — | S |
| D-10 | `hasMember`/`isMemberOf` | `DatasetResource`(Collection) ↔ `DatasetResource` | same | `dcterms:hasPart`/`dcterms:isPartOf` | `collection_summary`/`target_resource_id` (det) | — | S |
| D-11 | `derivedFrom`/`versionedFrom` | `DatasetResource` → `DatasetResource` | same | `prov:wasDerivedFrom` | `typed_relations` (det)/prose | — | S/E |
| D-12 | `launchesApp` + `launchURL` | `ToolConfiguration` → `Tool`; `launchURL` literal endpoint | cross | `ciroh:` + `schema:url` attribute | `app_home_page_url` / app-launching URL pattern | — | S |
| D-13 | `dependsOnRepository` | `Repository` → `Repository` | same | `ciroh:` (no standard); library deps use `schema:softwareRequirements` | `github.com` links/dep files | — | S/E |
| D-14 | `forkedFrom` | `Repository` → `Repository` | same | `ciroh:` | `fork` flag (det); parent via README/Binder badge | — | flag S · **parent E** |
| D-15 | `references` (doc→doc) | `DocumentationPage` → `DocumentationPage` | same | `dcterms:references` | internal/relative links (det) | — | S |
| D-16 | shared-domain consolidation | any module → canonical `ComputationalModel`/`Tool`/`Variable`/`Concept`/`HydrologicFeature`/**`EvaluationMetric`/`Parameter`/`Algorithm`** | cross+same | `ciroh:` | prose (LLM) + geoconnex (det) | **the mechanism** | S (E: Variable/Algorithm) |
| D-17 | `generatedBy` | `DatasetResource` → `Repository` | cross | `prov:wasGeneratedBy` | explicit metadata/README (det/quote) | — | S explicit · F inferred |
| D-18 | `studiesFeature`/`referencesFeature` | `Paper`/`Dataset`/`Doc` → `HydrologicFeature` | cross+same | `ciroh:` | geoconnex URI (det) + prose | yes | S/E |
| D-19 | `announces`/`references` | `DocumentationPage`(release-note/blog) → PR(`Repository`)/page/`Tool` | cross | `ciroh:` | dated entry + PR/page links (det) | — | S |
| D-20 | `archivedAs`/`sameSoftwareAs` | `Repository` ↔ archived DOI snapshot (Zenodo) | same | `datacite:relatedIdentifier` (IsVersionOf/IsDerivedFrom) | repo DOI ↔ paper-cited DOI (det **where the cross-identifier matches**) | links stub↔curated | **E** |
| D-21 | `mentionsModel`/`mentionsDataset` | `Paper`/`Doc` → `ComputationalModel`/`DatasetResource` (mentioned, **not** used) | cross+same | `ciroh:` (distinct from `usesModel`/`usesDataset`) | related-work / prose (quote) | yes | S |
| D-22 | `implementedBy` | product/component `Tool`/`ComputationalModel` → `Repository` | cross | `ciroh:` (backs D-06) | product card / DocCardList links (det) | yes | S |
| D-23 | `describedInPaper` | `Tool`/`ComputationalModel` → `Paper` | cross | `ciroh:` (backs D-06) | product card links (det) | yes | S |
| D-24 | `describes` | `DocumentationPage` → `Tool`/`ComputationalModel` | cross | `ciroh:` | documentation body prose | yes | S |
| D-25 | `documentedBy` | `Tool`/`ComputationalModel` → `DocumentationPage` | cross | `ciroh:` | inverse of `describes` | yes | S |

> **D-06 backing edges:** the aggregation now has explicit, traversable relations — `catalogs` (C-DC17), `hasComponent` (C-DC19), **`implementedBy`** (D-22), **`describedInPaper`** (D-23), and **`documentedBy`** (D-25). `describesTool`/`describesModel` are subproperties of `describes` (D-24), and `documentedBy` is its inverse. This lets E-05, E-10, and E-14 traverse directly from a product/component node to its repo and paper.
> **Declared inverse pairs:** `hasMember` ⇄ `isMemberOf` for dataset collection membership; `isExecutedBy` ⇄ `executes` for dataset/tool execution; `hasSubPage` ⇄ `isPartOf` for documentation page hierarchy; `documentedBy` ⇄ `describes`, with `describesTool`/`describesModel` as subproperties of `describes`.
> **D-20 resolution rule:** an externally-referenced stub (e.g. a Zenodo DOI) whose `relatedIdentifier` metadata points to a curated corpus repository is **linked to that repository**, so paper mentions reach the curated entity. Where the cross-identifier does **not** match (the `deep_bucket_lab` case: paper DOI `10.5281/zenodo.14538196` ≠ repo README sandbox DOI), the link is low-confidence/omitted — **never inferred by name**.
> **Cited-DOI typing rule** (citation extractor): classify a reference by identifier type — a **software/dataset DOI** (e.g. a Zenodo software DOI) in the reference list is typed as a stub `Tool`/`Repository`/`DatasetResource`, **not** a `Paper`-stub; a **paper DOI** is a `Paper`-stub. Required so `archivedAs` (domain `Repository`, D-20) can attach to a software stub (E-26).
> **Promoted cross-cutting relations** (live in module Table C, consolidate via D-16): `reportsMetric`/`evaluates` (`EvaluationMetric`), `hasParameter` (`Parameter`), `usesAlgorithm` (`Algorithm`).

---

# Part 7 — Table E: Competency questions

| # | Competency question | Entities (→ A) | Relations (→ C/D) | Cross-artifact? |
|---|---|---|---|---|
| E-01 | Which methods does paper X report, and what findings do they produce? | A-P13, A-P16 | C-P05, C-P07 | no |
| E-02 | Which computational models are *used* (vs. merely *mentioned*) across more than one paper? | A-P01, A-DOM03 | C-P13 vs C-P23, D-16 | same-type |
| E-03 | Which repositories implement a method described in a given paper? | A-C01, A-P13 | C-C16, D-02 | yes |
| E-04 | Which datasets are used by papers that study a given watershed? | A-P01, A-D01, A-DOM07a | C-P20, C-P17, D-01, D-18 | yes |
| E-05 | Which documentation pages describe a tool implemented by a CIROH repository? | A-DC01, A-DOM02, A-C01 | C-DC07, D-22 (`implementedBy`), D-06 | yes |
| E-06 | For a dataset, which repositories use it and which papers cite/use it? | A-D01, A-C01, A-P01 | D-01, D-05 | yes |
| E-07 | Which contributors appear across both a repository and a paper? | A-AG01 | C-C04, C-P01 | yes |
| E-08 | What is the provenance (source + evidence) of "repo R implements method M"? | A-PROV01 | `hasEvidence`, D-02 | yes |
| E-09 | Which procedures document a given product, and what steps do they contain? | A-DC05, A-DOM02, A-DC06 | C-DC17/C-DC07, C-DC20 (`hasProcedure`), C-DC10 | yes |
| E-10 | Which tools are documented in the Hub but absent from the curated 51 repos? | A-DOM02, A-DC01, A-C01 | C-DC07, D-22 (`implementedBy`), D-03 (+`curationStatus`) | yes |
| E-11 | Which variables are mentioned in papers about a given river reach (COMID)? | A-DOM04, A-P01, A-DOM07b | C-P16, C-P17 | yes |
| E-12 | Which datasets were generated by a given repository (where explicitly stated)? | A-D01, A-C01 | D-17 | yes (evidence-gated) |
| E-13 | Which hypotheses does a paper test, and which claims does it support — kept distinct? | A-P23, A-P24, A-P16 | C-P08, C-P09 | no (E-class) |
| E-14 | For a composite product (e.g. NGIAB), what are its components/distributions, repos, docs, dataset, and paper? | A-DOM02, A-C01, A-DC01, A-D01, A-P01 | D-06 (`catalogs` + `hasComponent` + `implementedBy` D-22 + `describedInPaper` D-23 + `documentedBy` D-25) | yes (hierarchical hub) |
| E-15 | Which papers cite a given paper *as a data source* vs. *as evidence* vs. *extend* it? | A-P01 | D-08 (typed CiTO) | same-type |
| E-16 | For NWM (process-based): which papers use it, repos implement it, docs describe it? | A-DOM03a, A-P01, A-C01, A-DC01 | C-P13, C-C11, C-DC16, D-16 | yes (consolidation) |
| E-17 | Which configuration files / dependencies and which file roles does a repo expose? | A-C01, A-C02, A-C03 | C-C01, C-C02 | no (deterministic; `fileRole`) |
| E-18 | Which functions/algorithms are described in prose for a given repository? | A-C01, A-C08, A-DOM13 | C-C08 | no (E-class) |
| E-19 | Which collections does a HydroShare resource belong to, and what app does a ToolResource launch? | A-D01, A-D10 | D-10, D-12 | yes |
| E-20 | Which release notes announce PRs to a given repository, and which pages did they add? | A-DC01, A-C01 | D-19 | yes |
| E-21 | Which hydrologic features vs. named places vs. spatial-coverage geometries link to a dataset? | A-DOM07*, A-DOM08, A-DOM09, A-D01 | D-18 (`referencesFeature`), `hasSpatialCoverage` (C-D07/C-P19), `studiesPlace` (C-P18) | yes |
| E-22 | Which awards fund resources/papers, and through which agency (incl. ROR)? | A-D09, A-AG02, A-D01 | `fundedBy` (A-AG-R2), `Award` (A-D09) | yes (funding trace) |
| E-23 | For a given model, which methods are *applied to* it, which *algorithms* do those methods use, and what type is the model? | A-DOM03*, A-P13, A-DOM13 | C-P14, C-P28 | no (Model/Method/Algorithm) |
| E-24 | Which performance metrics (and values) are reported for model M, and which method/experiment produced them? | A-DOM11, A-DOM03*, A-P13 | C-P25, C-P26 | same-type (metric consolidation) |
| E-25 | Which calibrated parameters (with physical ranges) does a process-based model use, across papers and repos? | A-DOM12, A-DOM03a, A-C01 | C-P27, C-C12, D-16 | yes |
| E-26 | For a paper-cited Zenodo DOI, which curated corpus repository archives the same software? | A-C01, A-ID01 | D-20 (+ resolution rule) | yes (stub↔curated) |

---

# Part 8 — Completeness passes

**1. Category↔entity orphan check.** Every LLM/hybrid entity reachable from ≥1 category; deterministic entities skip Table B. New shared classes reached: `EvaluationMetric` (B-P10/B-D-results), `Parameter` (B-P09/B-C06/B-DC05), `Algorithm` (B-P07/B-C05). ✔ *Watch:* `Measurement` (A-D12) coverage ≈ 0.

**2. Cross-artifact coverage check.** All four characterizations' candidates present, plus the validation-2 additions: `mentionsModel`/`mentionsDataset` (D-21), `archivedAs` (D-20), hierarchical product hub (D-06 + `hasComponent`), `forkedFrom` parent (E). Nothing dropped.

**3. Competency-question coverage (validation 3 dry-run).** E-01..E-26 trace cleanly as query patterns: **23/26 unchanged**; the other 3 (E-05/E-10/E-14 on the product hub) drove the additive fixes below. Newly exercised: mention-vs-use (E-02), composite-product hierarchy (E-14), metrics (E-24), parameters (E-25), archived-snapshot resolution (E-26), Model/Method/Algorithm (E-23).

**4. Reuse-vs-CIROH audit (validations 1–3 applied).**
- **Reformulated (val 1):** CodeMeta = profile; CFF = evidence; schema.org-primary agents; geographic split (`gn:Feature` vs `geo:Feature`/`Geometry`); `Gauge`→`hyf:HY_HydrometricFeature`; CiTO typed citations; DEO adoptions (`Data`/`Evaluation`/`Motivation`); `deo:Materials` **not adopted**, `deo:Model` discarded.
- **Promoted to shared domain (val 2):** `EvaluationMetric` (`ciroh:`), `Parameter` (`schema:PropertyValue`), `Algorithm` (`ciroh:`). `StatisticalModel` demoted to **E**; `Measurement` E coverage ≈ 0 (demote-candidate). New relations: `mentionsModel`/`mentionsDataset`, `reportsMetric`/`evaluates`, `hasParameter`, `usesAlgorithm`, `archivedAs`/`sameSoftwareAs` (`datacite:relatedIdentifier`, E), `forkedFrom` parent (E), `hasComponent` (hierarchical hub). Confirmed: `implementsMethod` (Repository/Tool→Method) + `cito:usesMethodIn`; doc→repo mirror deterministic (S).
- **Added (val 3, all additive):** product-hub backing edges `implementedBy` (D-22) + `describedInPaper` (D-23), `documentedBy` confirmed as inverse of C-DC07/C-DC16; agent-layer `affiliatedWith` (A-AG-R1) + `fundedBy` (A-AG-R2); `hasProcedure` (C-DC20); cited-DOI typing rule (software/dataset DOI → software stub, not `Paper`-stub); E-21/E-22 relation-ID corrections.
- **`ciroh:` short list (the contribution):** `ComputationalModel` hierarchy + Model/Method/Algorithm discriminant; `EvaluationMetric`; `Algorithm`; `Aquifer`/`VPU`; controlled classifications (`ResourceType`, `RepositoryPurpose`, `productCategory`); `Variable`/`Measurement` semantics; `ToolConfiguration`; `dependsOnRepository`; mention-vs-use + `archivedAs` resolution + product-hub backing edges; the PEO-aligned discourse classes not in DEO + PEO relation vocabulary; the cross-artifact (R2O) relation semantics. `Parameter` reuses `schema:PropertyValue`.

**Outcome.** Validations 1–3 complete; schema-change logs applied. Validation 3 (CQ dry-run): **23/26 CQs unchanged; the remaining 3 resolved by 5 additive fixes** (no restructuring). **Schema frozen — ready for Protégé.** Remaining: **Etapa B** (LLM pilot on the same 6+ artifacts — re-tests Model/Method and `Measurement` coverage, calibrates cost for Dr. Gong's approval, seeds the Phase-2 gold standard) → Protégé → HermiT (Phase 4).

## Protégé import notes (from validation 1)
- DEO: prefix `deo:` expands with slash `http://purl.org/spar/deo/`; **import canonical** `http://purl.org/spar/deo`.
- FaBiO (`http://purl.org/spar/fabio`) and HY_Features (`https://www.opengis.net/def/schema/hy_features/hyf/`): **reference class IRIs**, don't `owl:imports`; CIROH classes `rdfs:subClassOf` the reused class.
- CodeMeta: profile (context `https://doi.org/10.5063/schema/codemeta-2.0`); reuse properties, not classes.
- Dublin Core `dcterms:` only; GeoNames ≥ 2.2.1. SPDX `http://spdx.org/rdf/terms#`; DOAP `http://usefulinc.com/ns/doap#`; PROV-O `http://www.w3.org/ns/prov#`; SKOS `http://www.w3.org/2004/02/skos/core#`; CiTO `http://purl.org/spar/cito`; DataCite `http://purl.org/spar/datacite` (+ `relatedIdentifier`); GeoSPARQL `http://www.opengis.net/ont/geosparql#`; `ciroh:` = `https://w3id.org/ciroh/ontology#`.
