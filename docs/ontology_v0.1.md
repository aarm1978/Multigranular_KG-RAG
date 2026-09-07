# Ontology Conceptual Overview — Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts

> **Role and authority.** This is the concise conceptual overview for Study 2, not
> the exhaustive schema or formalization record. `ontology_inventory.md` is the
> exhaustive human-readable schema with stable IDs; `src/ontology/ontology_spec.yaml`
> is the current machine-readable authority; and `ontology_formalization.md` records
> formalization history, exact hashes, generated-artifact counts, and reasoner
> validation. The current formally frozen ontology release is **0.1.4**.

**Current 0.1.4 summary.** The frozen ontology has 75 source class declarations and
126 source relation declarations: 51 minted CIROH classes, 22 referenced external
classes, 91 object properties, 18 datatype properties, and 6 direct OWL imports. The
generated RDF/XML OWL SHA-256 is
`7d94a10aca96dd098d40f50fbd66d0c53f92a5b5f0d317621e7b29da71bc2635`.
The formal HermiT gate passed: classification completed, the ontology is consistent,
zero named unsatisfiable classes were found under `owl:Nothing`, and no execution
errors were observed.

> **Scope (TBox/ABox).** The schema declares all proposal classes. Instance-level
> extraction status is `S` (supported-now), `E` (extract where evidence supports it),
> or `F` (future-only); genuinely `F` targets are figure/table visual content and
> source-code AST parsing. Categories are extraction-routing scaffolding, not OWL
> classes.

---

## 1. Architecture

Four artifact modules—Paper, Dataset, Code, and Documentation—sit over four shared
layers: provenance, identifier, agent, and shared CIROH domain entities. An integration
layer connects them. The design addresses the breadth–depth and structure–semantics
tensions identified in Study 1.

## 2. Cross-cutting design rules

1. **Provenance-first:** **no supported evidence → no accepted semantic assertion.**
   The TBox applies `hasEvidence min 1 EvidenceSpan` to applicable minted CIROH node
   classes. Externally typed nodes are enforced through extraction/ABox validation;
   edge evidence is materialized as property-graph relationship data, not attached to
   ordinary OWL triples.
2. **Domain/range, not all-to-all.**
3. **Curated versus externally referenced:** `curationStatus` distinguishes curated
   nodes from reference stubs. Identifier evidence can support deterministic or
   high-confidence canonicalization; cross-source semantic alignment and consolidation
   remain later operations, not automatic source-specific extraction outcomes.
4. **Inter-source includes cross-type and same-type links.**
5. **Two node kinds:** discourse/rhetorical and domain entities.
6. **Reuse then extend:** the thin `ciroh:` layer and cross-artifact relation semantics
   are the contribution.
7. **Effort profiles vary by source:** HydroShare is deterministic-heavy; papers are
   LLM-heavy.
8. **Identity policy is evidence-led:** schema.org is primary for persons and the
   four identifier regimes provide canonicalization evidence. A validated GitHub-login
   to paper-author example supports that policy; it does not claim completed global
   person consolidation during source extraction.
9. **Three-level extraction organization:** categories/routing scaffolding, ontology
   entity targets, and ontology relation targets. This is a semantic organization, not
   a prescription for sequential provider calls. Publication extraction may author
   eligible nodes and relations jointly within one source-unit request.

## 3. Vocabulary reuse map

| Concern | Reuse |
|---|---|
| Provenance / packaging | PROV-O; RO-Crate |
| Identifiers | DataCite; ORCID; ROR; geoconnex |
| Persons / organizations | schema.org primary; FOAF optional equivalence |
| Paper discourse | DEO; PEO is a conceptual reference, not an OWL import |
| Typed citations | CiTO |
| Artifact typing and metadata | schema.org; DataCite; PROV-O; Dublin Core; `hsterms` |
| Document structure / concepts / procedures | DoCO; SKOS; schema.org `HowTo`; P-Plan |
| Software / repositories | schema.org; CodeMeta profile; DOAP; SPDX |
| Geographic entities | HY_Features; GeoSPARQL; GeoNames |
| Variables / parameters | schema.org; CF Standard Names |
| Generic semantic mention | MiTO `mito:mentions` as a reference-only reuse anchor |
| Contribution | `ciroh:` domain layer and cross-artifact relation semantics |

### 3.1 Namespaces and import/reference policy

`ciroh:` is `https://w3id.org/ciroh/ontology#`. Six vocabularies are directly
imported: DEO, CiTO, DataCite, PROV-O, SKOS, and P-Plan. MiTO uses the exact prefix
`mito:` = `http://purl.org/spar/mito/`; it is reference-only and is not imported.
FaBiO, HY_Features, schema.org, GeoSPARQL, GeoNames, DCMI Terms, DoCO, FOAF, SPDX, and
DOAP are referenced where specified rather than generally imported. CodeMeta is a
profile, not the source of the software classes.

## 4. Provenance layer

`EvidenceSpan` is a `prov:Entity` carrying source artifact, location, evidence text,
extraction method, and version. The provenance-first constraint is deliberately layered:
the TBox restriction covers applicable CIROH node classes, extraction/ABox validation
enforces evidence for externally typed nodes, and the property graph carries edge-level
evidence. This preserves the rule that unsupported assertions are not accepted without
overclaiming what plain OWL triples can enforce.

## 5. Identifier backbone

`Identifier` uses `datacite:Identifier` for DOI, HydroShare ID, GitHub URL plus SHA,
documentation URL, ORCID, ROR, geoconnex, and related DOI evidence. `hasIdentifier`
and `datacite:relatedIdentifier` support deterministic or high-confidence identity
evidence. They do not themselves materialize cross-source semantic consolidation;
later alignment/consolidation applies the canonicalization policy.

## 6. Agent layer

`Person` uses `schema:Person` and `Organization` uses `schema:Organization`; schema.org
remains primary, with FOAF only as an optional equivalence. Module relations include
`hasAuthor`, `hasCreator`, `hasContributor`, `affiliatedWith`, and `fundedBy`.
Formally, `fundedBy` is declared for `Paper`/`DatasetResource` subjects; the current
machine-readable ontology does not declare an `Award`-subject funding relation. The
Dataset branch `C-D09` additionally permits `DatasetResource` → `Organization` funding
assertions. Historical inventory prose describing `Award` → `Organization` reflects a
conceptual funding-agency note rather than a formal ontology relation. Identifier-regime
evidence supports later person alignment; it is not a claim that all person identities
are already globally consolidated.

## 7. Shared CIROH domain-entity layer

`SoftwareEntity` has sibling specializations `Tool` and `ComputationalModel`.
`ComputationalModel` includes `ProcessBasedModel`, `ConceptualModel`,
`StatisticalModel` (`E`, only when a named statistical model has its own identity), and
`MLModel`/`DataDrivenModel`; no `EmpiricalModel` class is introduced. A named entity
that can own a repository, dataset, or paper is a model, tool, or `Algorithm`; an
applied technique is a `Method`. `Method` may `appliesTo` a `ComputationalModel` and
`usesAlgorithm` an `Algorithm`.

Other shared entities distinguish `Variable` from `Concept`, and include
`EvaluationMetric`, `Parameter`, and `Algorithm`. Geographic modeling distinguishes
CIROH `HydrologicFeature`, `NamedPlace`, and footprint `SpatialCoverage`; `Gauge` is a
HY_Features hydrometric feature. Cross-source consolidation of these entities is later
alignment work, even where deterministic identifier evidence is already available.

## 8. Module 1 — Research Paper

The discourse layer is anchored to DEO and conceptually informed by PEO. CIROH adds
`ResearchQuestion`, `Hypothesis`, and `Claim`; `deo:Materials` is not adopted because
materials decompose into existing entity types. Paper relations distinguish explicit
`usesModel`/`usesTool` from weaker `mentionsModel`, `mentionsTool`, `mentionsConcept`,
and `mentionsDataset`; `referencesRepository` is distinct from the paper implementation
repository relation `hasCodeRepository`. A citation or name occurrence alone does not
establish use. Cited software/dataset DOI stubs are typed as `Tool`, `Repository`, or
`DatasetResource`, not as Paper stubs, when the evidence supports that typing.

## 9. Module 2 — Dataset (HydroShare)

`DatasetResource` uses `schema:Dataset` with resource type, files, creators, license,
subjects, spatial and temporal coverage, awards, membership, and feature references.
`ToolConfiguration` can `launchesApp` a `Tool` with a literal `launchURL`.
`usesTool` and `usesModel` remain distinct from the weaker `mentionsTool` and
`mentionsModel`; `mentionsConcept` and `explainsWorkflow` retain their own semantics.
`Variable` and `Measurement` remain `E` where the inventory so specifies.

## 10. Module 3 — Code Repository

`Repository` uses `schema:SoftwareSourceCode`, CodeMeta profile metadata, and DOAP.
Repository references are separated from stronger `dependsOnRepository`, `forkedFrom`,
and `archivedAs` semantics. `implementsMethod` is distinct from model/tool
`implementedBy`: use requires actual use, execution, configuration, dependency, or
workflow invocation, whereas implementation identifies a repository as implementation
of a tool or model. `archivedAs`/`sameSoftwareAs` rely on cross-identifier evidence,
never name-only inference. `Function`, prose `Algorithm`, and `ModelVersion` are `E`;
source-code AST parsing is `F`.

## 11. Module 4 — Documentation (CIROH Hub)

`DocumentationPage` contains sections, links, subjects, and instructional procedures,
steps, parameters, and examples. `describesTool`, `describesModel`,
`describesDataset`, and `describesMethod` are narrower properties under `describes`;
`documentedBy` is its inverse. Deterministic documentation-to-repository
`documents`/`mirrors` assertions use the specified GitHubReadme evidence. The
hierarchical product-hub decision remains current; direct product-card representation
versus a `CatalogEntry`/`ResearchProduct` intermediate remains deferred.

## 12. Integration layer

The integration layer preserves the distinctions:

> **use != implementation != mention != reference != description**

Use requires actual use, execution, configuration, dependency, or workflow invocation.
Implementation is model/tool → repository `implementedBy`. Mention records an explicit
entity occurrence without proving a stronger role. Reference requires an explicit
identifier, link, or citation. Description requires prose that substantially explains
the target. These meanings are not collapsed by the generic mention parent.

### 12.1 Generic semantic mention amendment (0.1.4)

`ciroh:mentions` is D-26, the weak generic semantic-mention relation. Its reuse anchor
is MiTO's `mito:mentions`; MiTO is reference-only and is not imported. The existing
`mentionsConcept`, `mentionsDataset`, `mentionsModel`, `mentionsParameter`,
`mentionsTool`, and `mentionsVariable` properties are direct sub-properties of
`ciroh:mentions`. Their narrower domains, ranges, and specialized semantics are
unchanged. No named generic CIROH inverse mention property is introduced.

The generic relation is a weak parent/fallback: it does not imply use, study,
evaluation, reporting, description, implementation, citation, or another stronger
role. Specialized mention semantics remain authoritative; generic connectivity may be
derived downstream from accepted evidence without replacing those relations.

## 13. Version history and current status

### 0.1 conceptual freeze

The conceptual schema was frozen after vocabulary-reuse review, artifact fit checks,
and competency-question review. The historical product-hub refinements added backing
relations, the cited-DOI typing rule, agent relations, explicit procedure containment,
and stable-ID corrections.

### 0.1.1 formalization patch

The formalization patch corrected machine-readable translations of approved global
relations, including the relevant branches of `referencesDataset` and documentation
relations. It added no conceptual class or relation family.

### 0.1.2 LLM-readiness relation patch

This additive/corrective patch separated previously collapsed tool/model,
function/algorithm, and variable/parameter semantics and completed approved mention,
use, reference, workflow, publication-reference, and typed-description branches. It
did not make an entity-consolidation or controlled-vocabulary decision.

### 0.1.3 minimal pre-pilot patch

This patch narrowed `testedBy` to `Hypothesis` → `Method`/`Experiment`, retained
`TheoreticalBasis` while deferring its possible grounding relation, removed an
unsupported documentation summary branch, and clarified positive-only `supports`.

### 0.1.4 generic semantic mention amendment and freeze

Version 0.1.4 adds only D-26 `ciroh:mentions` as the generic weak semantic-mention
parent anchored to reference-only `mito:mentions`. The six specialized `mentionsX`
properties remain direct sub-properties with their prior domains, ranges, and meanings;
no named inverse was added. Structural validation and the formal HermiT gate passed,
and 0.1.4 is the current formally frozen release. For exact counts, hashes,
deterministic-build records, and reasoner history, see `ontology_formalization.md`.
