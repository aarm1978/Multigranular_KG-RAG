# Ontology v0.1 — Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts

**Study 2 — Phase 1 deliverable (conceptual companion to the exhaustive `Study2_Ontology_Inventory.md`).**
**Vocabulary reuse verified (validation 1); schema fit-checked on 6 real artifacts (validation 2, Etapa A) → GO, schema-change log applied. OWL/RDF formalization in Protégé follows after Etapa B + validation 3; HermiT = Phase 4.**

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

PEO-grounded discourse layer anchored to **DEO** via PEO's Co-occurrence Framework (incl. `deo:Motivation`/`Data`/`Evaluation`), `ciroh:` (aligned PEO) for the rest; `deo:Materials` **not adopted** (materials decompose into DatasetMention/ProcessBasedModel/HydrologicFeature/Parameter). **CIROH additions:** `ResearchQuestion`, `Hypothesis`, `Claim`. PEO 18-relation vocabulary; attributes `tendency`/`source`; 29 second-level = E. **Cross-cutting reach (validation 2):** `EvaluationMetric` (via `reportsMetric`/`evaluates`), `Parameter` (`hasParameter`), `Algorithm` (`usesAlgorithm`); **`mentionsModel`/`mentionsDataset`** distinct from `usesModel`/`usesDataset`; citations typed via CiTO. **Cited-DOI typing rule (validation 3):** a software/dataset DOI in the reference list is typed as a `Tool`/`Repository`/`DatasetResource` stub (not a `Paper`-stub) so `archivedAs` can attach. **E:** Hypothesis, Claim, PEO second-level. **F:** figure/table visual content, in-text citation-marker resolution. See inventory Part 2.

## 9. Module 2 — Dataset (HydroShare)

`DatasetResource` (`schema:Dataset`) with `ResourceType` (Composite/Collection/Tool); `File`, `Creator` (`schema:Person`), `License`, `Subject`, `SpatialCoverage` (`geo:Geometry`), `TemporalCoverage`, `Award`; `ToolConfiguration` + `launchesApp` to `Tool` with literal `launchURL`; collection membership `hasMember`/`isMemberOf` (cross-ID resolution via `target_resource_id`); `referencesFeature` → `HydrologicFeature`. **E:** `Variable` (abstract/README); `Measurement` (coverage ≈ 0, demote-candidate — did not fire; the useful distinction is `Variable` vs `DatasetMention`). See inventory Part 3.

## 10. Module 3 — Code Repository

`Repository` (`schema:SoftwareSourceCode`; CodeMeta profile; DOAP). `File` + `fileRole` + `downloaded` + `selectionReason` (selection policy = reportable contribution). `Dependency` via `dependsOn` = `schema:softwareRequirements`; repo→repo = `ciroh:dependsOnRepository`. Repo→paper = `codemeta:referencePublication` (+ `cito:cites`), with `CITATION.cff`/`.md` as evidence locus. `implementsMethod` (Repository/**Tool**→Method, + `cito:usesMethodIn` by reference). **`forkedFrom` parent promoted to E** (README/Binder evidence). **`archivedAs`/`sameSoftwareAs`** (repo ↔ archived DOI snapshot; `datacite:relatedIdentifier`; **E** — deterministic only where cross-identifier matches, never inferred by name). `Algorithm` moved to shared. **E:** `Function`/`Algorithm` (prose), `ModelVersion`; **F:** source-code AST. See inventory Part 4.

## 11. Module 4 — Documentation (CIROH Hub)

`DocumentationPage` (+ `pageType`; gating confirmed) with `Section`, `Link`, `Subject`, instructional `Procedure`/`Step`/`Parameter`(shared)/`Example` (admonitions → `Example`), `Creator` (`schema:Person`); `Procedure` reached via explicit `hasProcedure` (and via `hasSection`→`Section`). **Product = Option B with hierarchical aggregation** (`catalogs` + `hasComponent` + backing edges `implementedBy` [product→`Repository`] / `describedInPaper` [product→`Paper`] / `describes` parent relation (`describesTool`/`describesModel` subproperties) + `documentedBy` [inverse of `describes`]: a composite product e.g. NGIAB → distributions/components → repos/docs/papers — the densest cross-artifact hub). `hasSourceFile` (".mdx"); **`documents`/`mirrors` doc→repo is deterministic (S)** when sourced from the `<GitHubReadme>` tag; `announces`/`references` (release-note/blog). See inventory Part 5.

## 12. Integration layer

Cross-type (`usesDataset`, `implementsMethod`+`cito:usesMethodIn`, `documents`/`mirrors`, `referencesRepository`/`Dataset`, hierarchical product hub [`catalogs`+`hasComponent`+`implementedBy`+`describedInPaper`+`documentedBy`], `referencePublication`, `launchesApp`, **`mentionsModel`/`mentionsDataset`**) and same-type (`cites`+typed CiTO, `corrects`, dataset `hasMember`/`isMemberOf`, doc-page `isPartOf`/`hasSubPage`, `derivedFrom`, `dependsOnRepository`, `forkedFrom` [parent E], doc→doc `references`, **`archivedAs`/`sameSoftwareAs`** [E], shared-domain consolidation incl. `EvaluationMetric`/`Parameter`/`Algorithm`). `generatedBy` evidence-gated. **Stub resolution:** an externally-referenced stub whose `relatedIdentifier` points to a curated corpus repo is linked to it, so paper mentions reach the curated entity; where identifiers do not match, low-confidence/omit. See inventory Part 6.

## 13. Next step

**Validations 1–3 complete; schema frozen.** Validation 3 (CQ dry-run): 23/26 CQs traced unchanged; the other 3 (product hub) resolved by 5 additive fixes (backing edges `implementedBy`/`describedInPaper`, cited-DOI typing rule, agent-layer `affiliatedWith`/`fundedBy`, `hasProcedure`, E-21/E-22 ID corrections). Remaining: **Etapa B** — LLM pilot on the same 6+ artifacts (same OpenAI backbone, when credits return): calibrates prompt overhead/quality/projected cost for Dr. Gong's approval; re-tests the Model/Method rule and `Measurement` coverage; seeds the Phase-2 gold standard. → **Protégé** per §3.1 + inventory Part 8 (declare classes + constrained imports, domain/range axioms, `hasEvidence min 1`, `curationStatus`, bind `ciroh:`). HermiT = Phase 4.
