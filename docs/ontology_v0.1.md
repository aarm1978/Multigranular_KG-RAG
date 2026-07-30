# Ontology v0.1 — Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts

**Current semantic version: 0.1.3, formally frozen.** The ontology IRI and this stable v0.1 filename are unchanged. HermiT completed successfully, found the validated ontology consistent with zero unsatisfiable named classes, and reported no execution errors.

**Study 2 — Phase 1 deliverable (conceptual companion to the exhaustive `Study2_Ontology_Inventory.md`).**
**Historical 0.1 planning status:** vocabulary reuse verified (validation 1); schema fit-checked on 6 real artifacts (validation 2, Etapa A) → GO, schema-change log applied. The former next step was OWL/RDF formalization in Protégé followed by HermiT. Current formalization and validation status is maintained in `ontology_formalization.md`.

> **Scope (TBox/ABox).** The schema declares *all* proposal classes; instance-level extraction status is `S` (supported-now) / `E` (extract-where-evidence) / `F` (future-only). Genuinely `future-only` = figure/table visual content and source-code AST parsing only.

---

## 1. Architecture

Four artifact modules (Paper, Dataset, Code, Documentation) over four shared layers (provenance, identifier, agent, CIROH domain), joined by an integration layer. Framed as a response to the **breadth–depth** and **structure–semantics** tensions (Study 1).

## 2. Cross-cutting design rules

1. **Provenance-first:** every node/edge has an `EvidenceSpan`; `hasEvidence min 1`; *no quote → no edge*.
2. **Domain/range, not all-to-all.**
3. **Curated vs. externally-referenced** (`curationStatus`); referenced = stub. *Validated frequent*, and a stub whose `relatedIdentifier` points to a curated repo is linked to it (see §12).
4. **Inter-source = cross-type and same-type.**
5. **Two node kinds:** discourse/rhetorical vs. domain entities.
6. **Reuse-then-extend:** the thin CIROH layer + cross-artifact relation semantics is the contribution.
7. **Effort profile varies by source** (HydroShare deterministic-heavy → papers LLM-heavy); split validated per type.
8. **Person consolidation across four identifier regimes** (schema.org primary), validated (a GitHub login = a paper author).
9. **Three-level extraction model** (LLM portions only): categories → entities → relations.

## 3. Vocabulary reuse map

| Concern | Reuse |
|---|---|
| Provenance / packaging | PROV-O; RO-Crate |
| Identifiers | DataCite (+ `relatedIdentifier`); ORCID; ROR; geoconnex |
| Persons / organizations | **schema.org primary**; FOAF optional equivalence |
| Paper discourse | DEO (`deo:`); PEO = conceptual reference (no OWL) |
| Citations (typed) | CiTO (`cites`, `citesAsDataSource`, `citesAsEvidence`, `usesMethodIn`, `extends`) |
| Paper/dataset/doc typing | schema.org; FaBiO (ref. IRIs) |
| Dataset metadata | schema.org `Dataset`; DataCite; PROV-O; Dublin Core (`dcterms:`); `hsterms` |
| Document structure / concepts / procedures | DoCO; SKOS; schema.org `HowTo`; P-Plan |
| Software / repositories | schema.org `SoftwareSourceCode`/`SoftwareApplication` (CodeMeta = profile); DOAP; SPDX |
| Geographic | HY_Features + GeoSPARQL (features & coverage); GeoNames (`gn:Feature`, named places) |
| Variables / parameters | `schema:variableMeasured`/`PropertyValue`; CF Standard Names |
| **New (contribution)** | **the `ciroh:` domain layer** (incl. `ComputationalModel` hierarchy, `EvaluationMetric`, `Algorithm`) **+ cross-artifact relation semantics** |

### 3.1 Namespace declarations + Protégé import notes

| Prefix | Vocabulary | Namespace IRI | Import note |
|---|---|---|---|
| `dcterms:` | DCMI Terms | `http://purl.org/dc/terms/` | use this, not legacy `dc:` |
| `schema:` | Schema.org | `https://schema.org/` | primary for Person/Org/Software/Parameter |
| `skos:` | SKOS | `http://www.w3.org/2004/02/skos/core#` | |
| `prov:` | PROV-O | `http://www.w3.org/ns/prov#` | |
| `foaf:` | FOAF | `http://xmlns.com/foaf/0.1/` | optional `owl:equivalentClass` only |
| `fabio:` | FaBiO (SPAR) | `http://purl.org/spar/fabio/` | reference class IRIs, don't import |
| `cito:` | CiTO (SPAR) | `http://purl.org/spar/cito/` | import IRI `http://purl.org/spar/cito` |
| `doco:` | DoCO (SPAR) | `http://purl.org/spar/doco/` | |
| `deo:` | DEO (SPAR) | `http://purl.org/spar/deo/` | import canonical `http://purl.org/spar/deo` |
| `datacite:` | DataCite ontology (SPAR) | `http://purl.org/spar/datacite/` | import IRI `http://purl.org/spar/datacite`; `relatedIdentifier` for archived snapshots |
| `codemeta:` | CodeMeta **profile** | `https://codemeta.github.io/terms/` | context `https://doi.org/10.5063/schema/codemeta-2.0`; properties only |
| `doap:` | DOAP | `http://usefulinc.com/ns/doap#` | |
| `spdx:` | SPDX | `http://spdx.org/rdf/terms#` | |
| `p-plan:` | P-Plan | `http://purl.org/net/p-plan#` | |
| `hyf:` | OGC HY_Features | `https://www.opengis.net/def/schema/hy_features/hyf/` | reference class IRIs, don't import |
| `geo:` | GeoSPARQL | `http://www.opengis.net/ont/geosparql#` | `Feature` vs `Geometry` |
| `gn:` | GeoNames | `http://www.geonames.org/ontology#` | version ≥ 2.2.1 |
| `peo:` | Paper Expression Ontology (Du & Li 2022) | *(no OWL)* | cite, don't import |
| `ciroh:` | **CIROH domain layer (this work)** | `https://w3id.org/ciroh/ontology#` | mint |

> **CFF** is not a vocabulary — a deterministic *evidence format* (like Zotero), feeding `Person`/`Identifier`/`referencePublication`.

---

## 4. Provenance layer

`EvidenceSpan` (`prov:Entity`); attributes `sourceArtifact`, `sourceLocation`, `evidenceText`, `extractionMethod`, `version`; relations `hasEvidence` (min 1), `wasExtractedBy`.

## 5. Identifier backbone

`Identifier` (`datacite:Identifier`) by scheme: DOI, HydroShare ID, GitHub URL + SHA, doc URL, ORCID, ROR, geoconnex, related DOI (`datacite:relatedIdentifier`). Relation `hasIdentifier`.

## 6. Agent layer

`Person` (`schema:Person`) and `Organization` (`schema:Organization` + ROR) — schema.org primary, not mixed with FOAF. Relations `hasAuthor`/`hasCreator`/`hasContributor` (module tables); `affiliatedWith` (`Person` → `Organization`, `schema:affiliation`); `fundedBy` (`Paper`/`DatasetResource` → `Award`; `Award` → `Organization`, `schema:funder`). Four identifier regimes reconciled (validated: a GitHub login resolves to a paper author).

## 7. Shared CIROH domain-entity layer (the contribution)

**Software (siblings):** `SoftwareEntity` (`schema:SoftwareApplication`) → `Tool` and `ComputationalModel`.

**Model hierarchy (`ciroh:` under `schema:SoftwareApplication`/`SoftwareSourceCode`):** `ComputationalModel` → `ProcessBasedModel` (VIC, Noah-MP, NWM, SWAT, CFE), `ConceptualModel` (bucket/tank), `StatisticalModel` *(E — vestigial: regression resolves to `Method`; instantiates only for a named statistical model with own identity)*, `MLModel`/`DataDrivenModel` (LSTM, RF). No intermediate `EmpiricalModel`. Literal `PhysicalModel` → future (not seen).

**Model / Method / Algorithm discriminant:** named thing that could own a repo/dataset/paper → `ComputationalModel`/`Tool`/`Algorithm`; technique applied → `Method`. `Method appliesTo ComputationalModel`; `Method usesAlgorithm Algorithm`.

**Other domain entities:** `Variable` (`schema:variableMeasured`/CF) vs. `Concept` (`skos:`). **Promoted to shared (validation 2):** `EvaluationMetric`/`PerformanceMetric` (`ciroh:`; NSE, RMSE, KGE, R², VIF…; reached via `reportsMetric`/`evaluates`), `Parameter` (`schema:PropertyValue`; `range`/`value`, `calibrated|default`; via `hasParameter`), `Algorithm` (`ciroh:`; SCE-UA, DDS; via `usesAlgorithm`). All consolidate like `Variable`.

**Geographic (one vocabulary each):** `HydrologicFeature` ⊏ `Place` (`geo:Feature` typed by `hyf:`; `Gauge`→`hyf:HY_HydrometricFeature`) — CIROH; `NamedPlace` ⊏ `Place` (`gn:Feature`) — not CIROH; `SpatialCoverage` (`geo:Geometry`+`dcterms:spatial`) — footprint. Relation `hasSpatialCoverage`. Validated at scale (HUC-10, USGS/SNOTEL gauges, VPU).

## 8. Module 1 — Research Paper

PEO-grounded discourse layer anchored to **DEO** via PEO's Co-occurrence Framework (incl. `deo:Motivation`/`Data`/`Evaluation`), `ciroh:` (aligned PEO) for the rest; `deo:Materials` **not adopted** (materials decompose into DatasetMention/ProcessBasedModel/HydrologicFeature/Parameter). **CIROH additions:** `ResearchQuestion`, `Hypothesis`, `Claim`. PEO 18-relation vocabulary; attributes `tendency`/`source`; 29 second-level = E. **Cross-cutting reach (validation 2):** `EvaluationMetric` (via `reportsMetric`/`evaluates`), `Parameter` (`hasParameter`), `Algorithm` (`usesAlgorithm`). LLM-facing relations distinguish explicit use (`usesModel`, `usesTool`), content mention (`mentionsModel`, `mentionsTool`, `mentionsConcept`, `mentionsDataset`), generic repository reference (`referencesRepository`), and the paper's implementation repository (`hasCodeRepository` ⊑ `referencesRepository`, anchored at `schema:codeRepository`). A citation or name occurrence alone never establishes use. **Cited-DOI typing rule (validation 3):** a software/dataset DOI in the reference list is typed as a `Tool`/`Repository`/`DatasetResource` stub (not a `Paper`-stub) so `archivedAs` can attach. **E:** Hypothesis, Claim, PEO second-level. **F:** figure/table visual content, in-text citation-marker resolution. See inventory Part 2.

## 9. Module 2 — Dataset (HydroShare)

`DatasetResource` (`schema:Dataset`) with `ResourceType` (Composite/Collection/Tool); `File`, `Creator` (`schema:Person`), `License`, `Subject`, `SpatialCoverage` (`geo:Geometry`), `TemporalCoverage`, `Award`; `ToolConfiguration` + `launchesApp` to `Tool` with literal `launchURL`; collection membership `hasMember`/`isMemberOf` (cross-ID resolution via `target_resource_id`); `referencesFeature` → `HydrologicFeature`. The LLM layer separates `usesTool` → `Tool` from `usesModel` → `ComputationalModel`, and separates both from weaker `mentionsTool`/`mentionsModel`; it may also emit `mentionsConcept` and `explainsWorkflow` from quoted abstract/README evidence. **E:** `Variable` (abstract/README); `Measurement` (coverage ≈ 0, demote-candidate — did not fire; the useful distinction is `Variable` vs `DatasetMention`). Dataset parameter, metric, and DatasetMention relations remain out of scope. See inventory Part 3.

## 10. Module 3 — Code Repository

`Repository` (`schema:SoftwareSourceCode`; CodeMeta profile; DOAP). `File` + `fileRole` + `downloaded` + `selectionReason` (selection policy = reportable contribution). `Dependency` via `dependsOn` = `schema:softwareRequirements`; repo→repo generic references use `referencesRepository`, while the stronger `dependsOnRepository`, `forkedFrom`, and `archivedAs` relations take precedence. Repo→paper = `codemeta:referencePublication` (+ `cito:cites`), with `CITATION.cff`/`.md` as evidence locus. `implementsMethod` (Repository/**Tool**→Method, + `cito:usesMethodIn` by reference). LLM-facing semantics separate `describesFunction` from `describesAlgorithm`; `usesTool` from `usesModel`; mention from use for tools, models, variables, and parameters; and add quoted-evidence `mentionsConcept`. Repository `usesModel` requires actual use, execution, configuration, dependency, or workflow invocation; implementation alone is represented by model/tool → repository `implementedBy` (D-22), which queries may traverse in reverse. **Use ≠ implementation.** **`forkedFrom` parent promoted to E** (README/Binder evidence). **`archivedAs`/`sameSoftwareAs`** (repo ↔ archived DOI snapshot; `datacite:relatedIdentifier`; **E** — deterministic only where cross-identifier matches, never inferred by name). `Algorithm` moved to shared. **E:** `Function`/`Algorithm` (prose), `ModelVersion`; **F:** source-code AST. See inventory Part 4.

## 11. Module 4 — Documentation (CIROH Hub)

`DocumentationPage` (+ `pageType`; gating confirmed) with `Section`, `Link`, `Subject`, instructional `Procedure`/`Step`/`Parameter`(shared)/`Example` (admonitions → `Example`), `Creator` (`schema:Person`); `Procedure` reached via explicit `hasProcedure` (and via `hasSection`→`Section`). Typed description subproperties are `describesTool`, `describesModel`, `describesDataset`, and `describesMethod`, all under `describes`; inverse `documentedBy` covers those four target classes. Documentation publication citations reuse the merged `referencePublication` property. `hasSourceFile` (".mdx"); **`documents`/`mirrors` doc→repo is deterministic (S)** when sourced from the `<GitHubReadme>` tag; `announces`/`references` retain distinct semantics. **Historical product-hub design: hierarchical aggregation.** Ontology 0.1.3 retains the decision, left unchanged in 0.1.2, to defer whether product cards directly represent domain entities or use a `CatalogEntry`/`ResearchProduct` intermediate class. See inventory Part 5.

## 12. Integration layer

Cross-type relation families preserve distinct evidence semantics: **use** requires actual use/execution/configuration/dependency/workflow invocation; **implementation** is model/tool → repository `implementedBy`; **mention** records a named entity without proof of use; **reference** requires an explicit identifier/link/citation but not ownership or use; **description** requires prose substantially explaining the target. Thus **use ≠ implementation**. D-04 now covers DocumentationPage, DatasetResource (through generic C-D19), Paper, and Repository references to Repository. D-07 covers Repository and DocumentationPage publication references. The model branch of D-21 covers Paper, DocumentationPage, Repository, and DatasetResource; its dataset branch is unchanged. D-24/D-25 cover Tool, ComputationalModel, DatasetResource, and Method. Existing integration relations and consolidation behavior remain unchanged. See inventory Part 6.

## 13. Next step

**Historical 0.1 status:** validations 1–3 were complete and the conceptual schema was frozen. Validation 3 (CQ dry-run) traced 23/26 CQs unchanged; the other 3 (product hub) were resolved by 5 additive fixes (backing edges `implementedBy`/`describedInPaper`, cited-DOI typing rule, agent-layer `affiliatedWith`/`fundedBy`, `hasProcedure`, E-21/E-22 ID corrections). The former Protégé → HermiT next-step statement is superseded by the versioned formalization and reasoner record in `ontology_formalization.md`.

The deterministic ABox backbone and ontology 0.1.3 are complete and formally frozen.
HermiT is the authoritative reasoner for the formal validation and freeze decision. The
frozen deterministic graphs remain unchanged.

### Formalization patch 0.1.1

The conceptual schema remains frozen. Version 0.1.1 is a formalization patch correcting the machine-readable translation of already-approved global relations. It completes the three module branches of `D-05 referencesDataset` and the previously omitted DocumentationPage branches of D-15, D-18, and D-21. `C-DC02i` remains the machine-readable ID for `hasSubPage`; `C-DC21` is its earlier narrative alias. No conceptual class or relation family was added, and use, mention, reference, description, and announcement semantics remain distinct.

### LLM-readiness relation patch 0.1.2

Version 0.1.2 is additive and corrective: it separates previously collapsed tool/model, function/algorithm, and variable/parameter semantics; completes approved LLM-facing mention, use, reference, workflow, publication-reference, and typed-description branches; and broadens D-04, D-07, D-21, D-24, and D-25 accordingly. It adds no classes and makes no entity-consolidation or controlled-vocabulary decision. The frozen deterministic graphs remain products of ontology 0.1.1 and are accepted byte-for-byte unchanged by 0.1.2; no deterministic extractor is rerun for this patch.

### Minimal pre-pilot patch 0.1.3

Version 0.1.3 narrows `C-P08 testedBy` to `Hypothesis →
Method/Experiment`; `TheoreticalBasis` remains a class, but its possible grounding
relation is deferred. It removes the unsupported summary branch from the `C-P12`
documentation and clarifies that `C-P09 supports` is positive-only under the current
formalization. No class, property name, stable ID, or relation family is added or
removed, and all other domains and ranges remain unchanged. Structural validation and
the authoritative manual HermiT gate are complete, and ontology 0.1.3 is formally
frozen at the validated SHA recorded in `ontology_formalization.md`.
