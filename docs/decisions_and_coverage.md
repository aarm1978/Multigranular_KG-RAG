# Ontology — Decisions & Coverage Review (Study 2, Phase 1)

**Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**
**Purpose.** Validate *what the ontology covers* and *which decisions we took*, including where decisions **changed or refined** the four characterizations. Updated through **validation 2 (Etapa A) — GO**, schema-change log applied. Working documents:
- `Study2_Ontology_v0.1.md` — conceptual model + namespaces/import notes (§3.1).
- `Study2_Ontology_Inventory.md` — exhaustive Tables A–E (the ontology proper).
- `Study2_Validation2_EtapaA_Results.md` — the desk fit-check (6 artifacts) and the schema-change log.

---

## 1. Cross-cutting decisions

1. Anchored to the approved proposal (Ch. 3, Fig. 3.2); framed by the **breadth–depth** and **structure–semantics** tensions (Study 1).
2. Eight components: four modules + four cross-cutting layers (provenance, identifier, agent, shared CIROH domain).
3. **Provenance-first:** `hasEvidence min 1`; *no quote → no edge*.
4. Domain/range, not all-to-all.
5. **Curated vs. externally-referenced** (`curationStatus`); referenced = stub; a stub whose `relatedIdentifier` points to a curated repo is linked to it (validated frequent).
6. Inter-source = cross-type **and** same-type.
7. Two node kinds: discourse vs. domain entities.
8. Reuse-then-extend: the thin CIROH layer + cross-artifact relation semantics is the contribution.
9. Person consolidation across four identifier regimes (schema.org primary) — validated (a GitHub login = a paper author).
10. Three-level extraction model (LLM portions only).

---

## 2. Central methodological decision — TBox/ABox (S/E/F)

Extraction status `S` / `E` / `F` (the prose extractor must run for E). All proposal classes are in the schema → no schema-level divergence. Genuinely `future-only` = figure/table visual content and source-code AST only.

---

## 3. Validation 1 — vocabulary reuse (applied)

15 vocabularies checked; zero non-existent classes. **Reformulations:** CodeMeta = profile (classes are `schema:SoftwareSourceCode`/`SoftwareApplication`; `dependsOn`=`schema:softwareRequirements`; repo→paper=`codemeta:referencePublication`); CFF = evidence format (dropped the `Citation` class). **Consistency:** schema.org primary for Person/Org; geographic split (`gn:Feature` vs `geo:Feature`/`Geometry`); `Gauge`→`hyf:HY_HydrometricFeature`. **Adopted (shrink `ciroh:`):** DEO `Data`/`Evaluation`/`Motivation`; CiTO typed citations. **Deferred/discarded:** `deo:Materials` deferred; `deo:Model` not adopted. Import notes recorded (DEO canonical IRI; FaBiO/HY_Features by class IRI; `dcterms:`; GeoNames ≥ 2.2.1).

---

## 4. Validation 2 (Etapa A) — desk fit-check on 6 artifacts → GO

Walked 3 papers (process / deep-learning / conceptual+statistical) + 1 HydroShare Composite + 1 GitHub repo (`deep_bucket_lab`) + 3 CIROH Hub pages against the inventory. **No systematic failure:** "missing" items were *mislocated* classes (not absent concepts); relation gaps were *additive* (not contradictions). The five decisions:

| Decision | Verdict | Applied change |
|---|---|---|
| **D1 — Model/Method discriminant** | **PASS (strong)** | Rule lands cleanly across all four model subtypes; only per-instance ambiguities. No change. |
| **D2 — Hierarchy depth / `EmpiricalModel`** | Keep 4 leaves; no `EmpiricalModel` | **`StatisticalModel` demoted to E** (regression → `Method`; instantiates only for a *named* statistical model). |
| **D3 — `deo:Materials`** | Do **not** adopt | "Materials" decompose into `DatasetMention`/`ProcessBasedModel`/`HydrologicFeature`/`Parameter`. Removed from open items. |
| **D4 — `Measurement`** | Keep declared (E), coverage ≈ 0 | Demote-candidate; re-confirm in Etapa B. Useful distinction is `Variable` vs `DatasetMention`. |
| **D5 — Evidence + domain/range + split** | **PASS** | Zero un-evidenced nodes/edges; split holds per type. Relation gaps logged (not failures). |
| *(Watch)* `PhysicalModel` | Not seen | Keep `future`. |

**Schema-change log applied (A–D):**
- **A — three classes promoted to the shared domain layer** (cross-cutting like Model/Tool/Variable): `EvaluationMetric`/`PerformanceMetric` (`ciroh:`); `Parameter` (`schema:PropertyValue`; moved from doc/code); `Algorithm` (`ciroh:`; moved from code-E; + `usesAlgorithm`).
- **B — relations added/confirmed:** `mentionsModel`/`mentionsDataset` (≠ uses); `reportsMetric`/`evaluates`; `hasParameter`; `usesAlgorithm`; **`archivedAs`/`sameSoftwareAs`** (`datacite:relatedIdentifier`, **E**, with the cross-ID resolution rule); **`forkedFrom` parent F→E**; confirmed `implementsMethod` (Repository/**Tool**→Method) + `cito:usesMethodIn`.
- **C — decision applications:** `StatisticalModel` → E; no `EmpiricalModel`; `deo:Materials` not adopted; `Measurement` E/demote-candidate.
- **D — documentation refinements:** **D-06 hierarchical aggregation** (`catalogs` + `hasComponent` + `implementedBy` + `describedInPaper` + `describes`/`documentedBy`: composite product → distributions/components → repos/docs/papers); doc→repo `mirrors`/`documents` is **deterministic (S)** via `<GitHubReadme>`; MDX admonitions → `Example` (minor).

**Confirmed-positive (no change; for the manuscript's evaluation narrative):** curated-vs-referenced frequent; geographic split holds at scale (HUC-10, USGS/SNOTEL, VPU); person consolidation across regimes real; CiTO typed citations pay off; CITATION as evidence source; deterministic/LLM split holds per type.

---

## 4b. Validation 3 (CQ dry-run) — 23/26 clean → 5 additive fixes → schema frozen

The 26 competency questions were traced as query patterns over the schema. **23 traced unchanged.** The other 3 (E-05, E-10, E-14 — the product hub) pointed to a single well-bounded schema gap plus minor items; all additive (no restructuring):
1. **Product-hub backing edges (significant):** D-06 named `implementedBy`/`describedInPaper` but they were not declared relations — repos hung off pages and papers off repos, blocking direct traversal from a product/component node. Added `implementedBy` (`Tool`/`ComputationalModel` → `Repository`, D-22) and `describedInPaper` (`Tool`/`ComputationalModel` → `Paper`, D-23); added parent `describes` with `describesTool`/`describesModel` as subproperties and `documentedBy` as its inverse.
2. **Cited-DOI typing rule:** a software/dataset DOI in the reference list is typed as a `Tool`/`Repository`/`DatasetResource` stub (not a `Paper`-stub), so `archivedAs` (domain `Repository`) can attach (E-26).
3. **Agent-layer relations declared:** `affiliatedWith` (`Person`→`Organization`) and `fundedBy` (`Paper`/`Dataset`→`Award`→`Organization`) — needed by E-07/E-22 (A-AG-R1/R2).
4. **`Procedure` containment:** added explicit `hasProcedure` (`DocumentationPage`→`Procedure`, C-DC20) so E-09 traverses directly (also reachable via `hasSection`→`Section`).
5. **Cosmetic:** corrected relation-ID references in E-21 (→ D-18 `referencesFeature`, `hasSpatialCoverage`, `studiesPlace`) and E-22 (→ `fundedBy`, `Award`).

---

## 5. Shared-layer decisions

- `ciroh:` = `https://w3id.org/ciroh/ontology#`; `peo:` cited, not imported.
- **Software:** `SoftwareEntity` (`schema:SoftwareApplication`) → siblings `Tool`, `ComputationalModel`.
- **Model hierarchy:** `ComputationalModel` → `ProcessBasedModel` / `ConceptualModel` / `StatisticalModel` (**E**) / `MLModel`. Model/Method/Algorithm discriminant: `Method appliesTo ComputationalModel`; `Method usesAlgorithm Algorithm`.
- **Promoted shared entities:** `EvaluationMetric`, `Parameter`, `Algorithm` (consolidate like `Variable`).
- **`Variable` vs. `Concept`:** measurable vs. non-measurable.
- **Geographic:** `HydrologicFeature` (CIROH) vs. `NamedPlace` (not CIROH) vs. `SpatialCoverage` (footprint geometry).

---

## 6. Per-module decisions and **delta vs. the characterization**

### 6.1 Paper (char 02) — refined most
**Kept:** deterministic bibliographic layer + LLM semantic layer; three-level design; discourse-vs-domain split; constrained relations; prototype as template.
**Changed/refined:** discourse set = PEO 17 first-level, anchored to DEO (incl. `Motivation`/`Data`/`Evaluation`) else `ciroh:`; `ResearchQuestion`/`Hypothesis`/`Claim` are CIROH additions; `Significance` ≠ `Contribution`; PEO 18-relation vocabulary; `tendency`/`source`; PEO 29 second-level = E; `DataDescription` (`deo:Data`); geographic mentions → `Place` hierarchy. **Validation 2:** papers now reach the promoted shared classes `EvaluationMetric` (`reportsMetric`/`evaluates`), `Parameter` (`hasParameter`), `Algorithm` (`usesAlgorithm`); **`mentionsModel`/`mentionsDataset`** added (≠ uses); citations CiTO-typed.

### 6.2 Dataset / HydroShare (char 01)
**Kept:** deterministic-heavy profile; transformation-stage reuse; three `ResourceType` subtypes; abstract+README LLM portion.
**Changed/refined:** `Variable`/`Measurement` deferred → E (`Measurement` coverage ≈ 0, demote-candidate); collection membership `hasMember`/`isMemberOf` (cross-ID resolution via `target_resource_id`); documentation hierarchy `isPartOf`/`hasSubPage`; `ToolConfiguration` + `launchesApp` to `Tool` with literal `launchURL`; `referencesFeature`; `SpatialCoverage` = `geo:Geometry`; `Creator` = `schema:Person`.

### 6.3 Documentation / CIROH Hub (char 03)
**Kept:** deterministic frontmatter/structure/links/mirror-tag + LLM instructional/domain; `Procedure`/`Step`/`Parameter`/`Example`; dual representation; thin CIROH layer.
**Changed/refined:** `pageType` (8 genres, gating confirmed); product catalog as cross-artifact hub, **Option B with hierarchical aggregation** (`hasComponent`); `announces`/`references`; `hasSourceFile`; **doc→repo mirror deterministic (S)** via `<GitHubReadme>`; admonitions → `Example`.

### 6.4 Code / GitHub (char 04)
**Kept:** deterministic-intermediate profile; metadata/manifest/deps deterministic; LLM on dossier; file-selection policy as contribution; `RepositoryPurpose`; dossier reuse.
**Changed/refined:** `File` + `fileRole` (+ `selectionReason`, `downloaded`); CodeMeta-as-profile / CFF-as-evidence; `dependsOn`=`schema:softwareRequirements`; repo→repo=`ciroh:dependsOnRepository`; repo→paper=`codemeta:referencePublication`. **Validation 2:** `Algorithm` moved to shared; **`forkedFrom` parent E**; **`archivedAs`/`sameSoftwareAs`** (E, with resolution rule); `implementsMethod` extended to `Tool`; `Function`/`Algorithm` E, AST = F.

---

## 7. Coverage validation checklist

| Layer / module | Entity classes | Relations | Reuse vs. `ciroh:` | S / E / F | Not covered (F) |
|---|---|---|---|---|---|
| Provenance | `EvidenceSpan` | `hasEvidence` (min 1), `wasExtractedBy` | PROV-O, RO-Crate | S | — |
| Identifier | `Identifier` (+ related DOI) | `hasIdentifier` | DataCite (+`relatedIdentifier`), ORCID, ROR, geoconnex | S | — |
| Agent | `Person`, `Organization` | `hasAuthor`/`hasCreator`/`hasContributor` (module tables), `affiliatedWith` (`Person`→`Organization`), `fundedBy` (`Paper`/`Dataset`→`Award`→`Organization`) | schema.org primary, ROR | S | residual name-only disambiguation |
| Shared domain | `SoftwareEntity`→{`Tool`, `ComputationalModel`→4 leaves}, `Variable`, `Concept`, `Place`→{`HydrologicFeature`×6, `NamedPlace`}, `SpatialCoverage`, `TemporalCoverage`, **`EvaluationMetric`, `Parameter`, `Algorithm`** | `hasSpatialCoverage`, `appliesTo`, `reportsMetric`/`evaluates`, `hasParameter`, `usesAlgorithm`, consolidation | schema.org, SKOS, HY_Features, GeoSPARQL, GeoNames, geoconnex; `ciroh:` for model hierarchy + `EvaluationMetric` + `Algorithm` + Aquifer/VPU | S (E: `Variable`, `Algorithm`, `StatisticalModel`) | literal `PhysicalModel` |
| Paper | ~26 (+ reaches `EvaluationMetric`/`Parameter`/`Algorithm`) | ~28 (PEO-18 subset + domain + integration + CiTO-typed + mention-vs-use + metric/param/algorithm) | DEO, FaBiO, CiTO, DataCite, schema.org; `ciroh:` aligned-PEO | S (E: Hyp, Claim, PEO 2nd-level) | figure/table visual content; in-text citation-marker resolution |
| Dataset | ~12 (+`ToolConfiguration`, `Variable`, `Measurement`) | ~19 | schema.org, DataCite, PROV-O, dcterms, SPDX, GeoSPARQL; `ciroh:` | S (E: `Variable`; `Measurement` coverage ≈ 0) | opening data files; `ToolResource`→dedicated class |
| Code | ~11 (`File`+`fileRole`; `Dependency`, `ExecutionEnvironment`, `RepositoryPurpose`, `Function`, `ModelVersion`, `Workflow`; `Algorithm`→shared) | ~18 (+`forkedFrom` parent E, `archivedAs`) | schema.org (CodeMeta profile), DOAP, SPDX, `cito:`/`codemeta:referencePublication`, DataCite `relatedIdentifier`; `ciroh:` | S (E: `Function`, `Algorithm`, `ModelVersion`, `archivedAs`, fork parent) | source-code AST |
| Documentation | ~9 (+`pageType`; `Procedure`/`Step`/`Parameter`/`Example`) | ~20 (+`hasComponent`, `hasProcedure`) | schema.org, DoCO, SKOS, P-Plan, dcterms, prov; `ciroh:` | S | cross-page workflow reconstruction |
| Integration (global) | — | 23 cross-artifact relations (+`implementedBy`, `describedInPaper`) | mostly `ciroh:`; typed citations (CiTO); `referencePublication` (CodeMeta); `archivedAs` (DataCite) | S (E: `archivedAs`, cross-granular alignment; `generatedBy` inferred=F) | `generatedBy` by inference |

**The contribution (`ciroh:` short list):** the `ComputationalModel` hierarchy + Model/Method/Algorithm discriminant; `EvaluationMetric`; `Algorithm`; `Aquifer`/`VPU`; controlled classifications (`ResourceType`, `RepositoryPurpose`, `productCategory`); `Variable`/`Measurement` semantics; `ToolConfiguration`; `dependsOnRepository`; mention-vs-use + the `archivedAs` resolution rule; the PEO-aligned discourse classes not in DEO + the PEO relation vocabulary; the cross-artifact (R2O) relation semantics. (`Parameter` reuses `schema:PropertyValue`.)

---

## 8. Status of open decisions

**All five open decisions resolved (validation 2):** D1 PASS (strong); D2 keep 4 leaves + `StatisticalModel` E; D3 `deo:Materials` not adopted (closed); D4 `Measurement` E/coverage ≈ 0 (re-confirm in Etapa B); D5 PASS. `PhysicalModel` stays `future`.

**Validation 3 (CQ dry-run) complete:** 23/26 CQs unchanged; 3 resolved by 5 additive fixes (§4b). **Schema frozen — ready for Protégé.**

**To re-confirm empirically in Etapa B (LLM pilot, same OpenAI backbone, when credits return):** the Model/Method rule under automatic extraction; `Measurement` coverage (drop if still empty); plus prompt overhead / quality / projected cost for Dr. Gong's approval, and seeding the Phase-2 gold standard.

---

## 9. Next step

**Etapa B** (LLM pilot) → OWL/RDF (TBox) in Protégé per the import notes (v0.1 §3.1 / inventory Part 8): declare classes + constrained imports, encode domain/range axioms, add `hasEvidence min 1` and `curationStatus`, bind `ciroh:`. HermiT validation is Phase 4.
