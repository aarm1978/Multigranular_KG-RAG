# Ontology Formalization (OWL/RDF) — Study 2, Phase 1 Record

**Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**

**Current semantic version:** 0.1.3, formally frozen. The generated and structurally
validated OWL passed the authoritative manual HermiT gate: classification completed
successfully, the ontology was consistent, no named classes were inferred under
`owl:Nothing`, and no execution errors occurred. Frozen deterministic Phase B graphs
remain ontology-0.1.1 products accepted unchanged.

**Purpose.** This document records the *formalization* phase: how the validated
conceptual schema was translated into a machine-readable OWL/RDF ontology, the
translation decisions taken, and the reasoner-based validation of the result. It
is the companion to the design documents that precede it — `ontology_inventory.md`
(the exhaustive schema), `ontology_v0.1.md` (the conceptual model + namespaces),
`decisions_and_coverage.md` (decisions + S/E/F coverage), and the three validation
records (vocabulary reuse, desk fit-check, competency-question dry-run). Those cover
*what the schema is and why*; this document covers *how it became a formal artifact*
and *the proof that it is logically sound*. It is written to serve as direct input to
the manuscript's ontology-implementation section.

---

## 1. From validated schema to formal artifact

The schema entered formalization already validated on four fronts: vocabulary reuse
(15 vocabularies verified against official specifications, zero non-existent classes),
desk fit-check against six real artifacts spanning the four artifact types,
competency-question dry-run (23/26 traced unchanged; three resolved by additive
fixes), and the resulting decision log. Formalization was therefore a *translation*
task, not a design task — the conceptual decisions were settled before any OWL was
written. This ordering is deliberate and is itself a methodological point: validating
the design before formalizing avoids discovering contradictions in the reasoner and
having to redesign.

The translation is **specification-driven and reproducible**. Rather than authoring
OWL by hand in an editor (which would break the link between the inventory and the
formal artifact, and risk divergence), the ontology is *generated* from a single
machine-readable specification:

```
ontology_inventory.md   (human-readable schema, stable IDs, rationale)
        │  faithful manual translation
        ▼
ontology_spec.yaml      (machine-readable master specification — source of truth)
        │  build_ontology.py  (owlready2)
        ▼
ciroh_ontology.owl      (OWL/RDF TBox — the generated artifact)
        │  HermiT validation (ELK technical cross-check)
        ▼
consistency + satisfiability validation
```

Every class and relation carries its inventory ID (`A-*`, `C-*`, `D-*`) as an OWL
annotation, so the generated ontology traces back to the inventory and, through it,
to the empirical justification in the validation records. The build is deterministic:
re-running `build_ontology.py` on the same specification produces the same ontology,
so version-control diffs are meaningful.

---

## 2. The master specification (`ontology_spec.yaml`)

The specification is a faithful, structured translation of the inventory. It has four
parts: a header binding the `ciroh:` namespace to `https://w3id.org/ciroh/ontology#`;
a **prefixes** block (18 vocabularies) where each entry declares how it is used; a
**global_constraints** block; and the **classes** and **relations** themselves, each
preserving its inventory ID, reuse anchor, domain/range, and S/E/F extraction status.

The single most important field is the per-prefix `use` flag, which encodes the
import-versus-reference decision that keeps the ontology lightweight:

| `use` value | Meaning | Vocabularies |
|---|---|---|
| `import` | `owl:imports` — the vocabulary's axioms are loaded | DEO, CiTO, DataCite, PROV-O, SKOS, P-Plan |
| `reference` | class IRIs are used but the vocabulary is **not** imported (avoids dragging large dependency closures, e.g. FaBiO→FRBR, full HY_Features) | FaBiO, HY_Features, schema.org, GeoSPARQL, GeoNames, dcterms, DoCO, FOAF, SPDX, DOAP |
| `profile` | properties only, treated as a profile, not imported | CodeMeta |
| `mint` | the `ciroh:` contribution namespace itself | ciroh |

Documentation-category scaffolding (inventory Table B) is intentionally excluded from
the specification: categories guide LLM extraction but are not OWL classes, so they do
not belong in the TBox. They will live in a separate extraction configuration in the
KG-construction phase.

---

## 3. Translation decisions

Six translation decisions required explicit resolution because the conceptual schema
expressed intent that OWL cannot represent verbatim. Each was decided deliberately,
not defaulted.

### 3.1 Reuse anchoring: subClassOf, useDirectly, or pure CIROH
Each class connects to its reused vocabulary via one of three relations, recorded in
the spec as `anchor.relation`:
- **subClassOf** — the CIROH class specializes an external class (e.g. `ciroh:Tool`
  ⊑ `schema:SoftwareApplication`; `ciroh:Watershed` ⊑ `hyf:HY_Catchment`).
- **useDirectly** — no CIROH class is minted; the external IRI is used as-is
  (e.g. `schema:Person`, `skos:Concept`, `datacite:Identifier`). This keeps the CIROH
  layer thin: where a standard class suffices, no parallel class is created.
- **none** — a pure CIROH contribution with no external parent (e.g.
  `ciroh:ProcessBasedModel`, `ciroh:EvaluationMetric`, `ciroh:Algorithm`), which is
  where the domain layer adds what no standard vocabulary provides.

An optional `alt_anchor` records an additional reuse alignment. Primary and
alternative anchors are serialized as distinct `ciroh:reuseAnchor` annotations and
comments only; an alternative anchor does not create a subclass, subproperty, or
equivalence axiom.

### 3.2 Property-as-class anchors → alignment annotations
Several inventory entries anchored a *class* to what is, in the reused vocabulary, a
*property* (e.g. `Variable`→`schema:variableMeasured`, `TemporalCoverage`→
`dcterms:temporal`, `Link`→`schema:url`, `ModelVersion`→`schema:softwareVersion`). A
class cannot be `rdfs:subClassOf` a property. These are therefore minted as CIROH
classes (e.g. `ciroh:Variable` ⊑ `schema:PropertyValue`) with the property recorded as
an informative **alignment annotation**, never as a logical axiom. This preserves the
intended reuse signal without an ill-formed axiom that a reasoner would reject.

### 3.3 Same-named relations merged with union domains/ranges
Relations that share a name across modules but differ in domain (e.g. `hasIdentifier`,
`hasSubject`, `hasLicense`, `usesDataset`, `mentionsModel`, `fundedBy`) are merged into
one property with a union (`owl:unionOf`) domain/range, keeping all contributing
inventory IDs as annotations. One conceptual relation maps to one property; the union
domain expresses "any of these subject types," avoiding the design smell of encoding
the domain in suffixed property names.

Ontology 0.1.3 retains the merged-property mechanism introduced in 0.1.2 for the
approved LLM-facing families. The merged
signatures are: `mentionsConcept` (`Paper`/`DatasetResource`/`Repository`/
`DocumentationPage` → `Concept`); `usesTool` (`Paper`/`DatasetResource`/`Repository`
→ `Tool`); `mentionsTool` over the same domains and range; `usesModel` (`Paper`/
`Method`/`DatasetResource`/`Repository` → `ComputationalModel`); `mentionsModel`
(`Paper`/`DocumentationPage`/`DatasetResource`/`Repository` →
`ComputationalModel`); `mentionsVariable` (`Paper`/`DataDescription`/`Repository` →
`Variable`); `explainsWorkflow` (`DocumentationPage`/`Procedure`/`Repository`/
`DatasetResource` → `Workflow`); `referencesRepository` (`DocumentationPage`/
`Paper`/`Repository` → `Repository`, with the DatasetResource conceptual branch kept
as generic `references`); and `referencePublication` (`Repository`/
`DocumentationPage` → `Paper`). Use and mention properties remain distinct.

`isPartOf` was the exception: it carried two genuinely distinct senses — dataset→
collection membership and documentation page→page hierarchy. These were **split** into
`isMemberOf` (dataset↔collection) and `isPartOf` (page hierarchy), each with its own
inverse, rather than merged, because they are different relations (the page sense is a
parent-child hierarchy, not collection membership).

### 3.4 Provenance-first: scope of the evidence constraint
The provenance-first principle ("no quote → no edge") is expressed in the TBox as a
qualified cardinality restriction, `hasEvidence min 1 EvidenceSpan`, applied to the
**CIROH knowledge-graph node classes** — the minted classes whose kind is artifact,
domain, discourse, instructional, metadata, or agent — and **excluding** `EvidenceSpan`
itself (which would be recursive) and the externally-referenced vocabulary classes
(over which CIROH should not impose axioms).

This scoping is a deliberate modeling decision with a precise consequence: **OWL
declares the evidence policy for CIROH classes; it does not, by itself, guarantee
evidence for every node and every edge.** Two gaps are filled outside the TBox:
- *Externally-typed nodes* (e.g. a `schema:Person` author, a `deo:Background` discourse
  unit) do not carry the OWL restriction. Their evidence is guaranteed during KG
  construction by the extraction rule "no quote → no edge" and validated in the ABox,
  not asserted in the TBox.
- *Edges* cannot carry evidence in plain RDF/OWL without reification, RDF-star, named
  graphs, or an n-ary pattern (see §3.5).

The reason scoping is harmless: minting wrapper classes (e.g. `ciroh:Background` ⊑
`deo:Background`) solely to attach the restriction would inflate the CIROH layer to
duplicate a guarantee the pipeline already enforces. The TBox states intent for CIROH
classes; the pipeline and the ABox enforce completeness.

### 3.5 Edge-level evidence lives in the property graph, not the TBox
A simple triple (`Paper usesDataset Dataset`) has nowhere to attach an `EvidenceSpan`
in plain RDF. Because the knowledge graph is materialized in a **property graph**
(Neo4j), edge-level evidence is stored as **properties of the relationship** (the
quote, source location, extraction method), which property graphs support natively —
the capability that requires reification in a triple store. The TBox declares the
provenance policy; the property-graph data layer materializes evidence on both nodes
and edges. This is the honest division of labor and should be stated as such in the
manuscript: the OWL artifact is the schema-level declaration, not the per-instance
enforcement mechanism.

### 3.6 Inverses and sub-properties: declared judiciously
A small set of inverse and sub-property axioms was declared, guided by the competency
questions and the lightweight principle:
- `hasMember` ⇄ `isMemberOf` (dataset collection membership)
- `hasSubPage` ⇄ `isPartOf` (documentation page hierarchy)
- `documentedBy` ⇄ `describes`, with `describesTool`, `describesModel`,
  `describesDataset`, and `describesMethod` as
  sub-properties of a parent `describes` — this realizes the `documentedBy` inverse
  named in the competency-question validation and completes the product-hub aggregation
  (`catalogs` + `hasComponent` + `implementedBy` + `describedInPaper` + `documentedBy`).

The historical product-hub decision here is hierarchical aggregation. The separate
ontology-modeling decision of whether product cards directly represent domain entities
or use a `CatalogEntry`/`ResearchProduct` intermediate class remains deferred and is
retained in ontology 0.1.3 after being left unchanged by ontology 0.1.2.

Most other reverse traversals were **deliberately not** given inverse properties,
because both SPARQL and the property-graph query layer (Cypher) traverse relations in
either direction without an inverse being declared. An inverse property is warranted
only when the reverse direction needs a name in the schema (as `documentedBy` does) or
when the reasoner should materialize it; minting inverses for every relation would
contradict the lightweight design without adding query capability.

This applies specifically to D-22: `implementedBy` retains the logical direction
`Tool`/`ComputationalModel` → `Repository`, and queries may traverse it in reverse.
Its evidence may be an explicit product card/DocCardList or quoted README, CITATION,
or repository prose stating implementation or source-code provision. Repository
`usesModel` instead requires actual use, execution, configuration, dependency, or
workflow invocation. **Use is not implementation**, so no duplicate
`implementsModel` inverse is introduced.

---

## 4. The generated ontology

`build_ontology.py` (owlready2) reads the specification and emits `ciroh_ontology.owl`
in RDF/XML. Ontology 0.1.3 retains the declaration counts introduced in 0.1.2:

| Element | Count |
|---|---|
| Minted CIROH classes | 51 |
| Referenced external classes | 22 |
| Source class declarations | 75 |
| Source relation declarations | 125 |
| Object properties | 90 |
| Datatype properties | 18 |
| `owl:imports` | 6 |

The 51 minted CIROH classes plus the externally-reused classes correspond to the 75
classes of the inventory (the `useDirectly` classes are counted among the referenced
externals rather than as minted CIROH classes). The 6 imports are DEO, CiTO, DataCite,
PROV-O, SKOS, and P-Plan. Object properties exceed the raw relation count's net after
merging because the inverse and sub-property axioms (`describes`, `documentedBy`,
`hasSubPage`, the separated `isMemberOf`, and `launchesApp` promoted from a datatype to
an object property) were added; the corresponding `launchURL` literal endpoint is
retained as a datatype attribute.

The earlier value of 81 was accurate for the initial formalization commit
`49b0137`. Commit `57dbcc7` subsequently added the two formal object properties
`isExecutedBy` and `executes` while the ontology version remained 0.1, increasing the
count to 83. Rebuilding both historical commits reproduces 81 and 83 respectively.
The 0.1.1 `C-P29` declaration does not add another property because it merges into the
already-existing `referencesDataset` property.

Relative to 0.1.1, the class count is unchanged, source relation declarations increase
from 105 to 125, and generated object properties increase from 83 to 90. The seven
new property names are `mentionsTool`, `hasCodeRepository`, `describesAlgorithm`,
`usesParameter`, `mentionsParameter`, `describesDataset`, and `describesMethod`; the
other new declarations merge into existing properties. The generated 0.1.2 artifact
SHA-256 is `2857dc9f8e578367f6d2608da7e05d2ff5b2113fd41ff6c34047b90574b53ee7`.

Traceability annotations attached to every entity include the inventory ID, the reuse
anchor, the S/E/F status, the node kind, and — for property-anchored classes — the
alignment property recorded as a non-logical annotation.

---

## 5. Reasoner validation

The historical validation record in this section applies to ontology **0.1**. That
generated ontology was loaded in Protégé (with the six imported vocabularies
resolved) and checked with the **HermiT 1.4.3.456** reasoner. The result:

- **Consistent** — no contradiction among the class, property, domain/range,
  cardinality, inverse, and sub-property axioms. A consistent ontology admits a model;
  an inconsistent one would be unusable, since any statement could be "derived" from a
  contradiction.
- **No unsatisfiable classes** — nothing was inferred as a subclass of `owl:Nothing`.
  Every class is satisfiable, i.e. capable of having instances. No node type in the
  schema is defined in a self-contradictory way; when the ABox is populated, every
  designed node type can exist with real data.

The authoritative validation used HermiT. Its result was additionally cross-checked
with **ELK 0.6.0**, which reported no unsatisfiable classes. ELK covers a smaller OWL
profile, so this is a profile-limited technical cross-check rather than independent
full consistency or satisfiability validation.

A clean reasoner result was the expected — not accidental — outcome of validating the
design before formalizing: the schema reached the reasoner already sound, so it passed
after the planned refinements rather than requiring redesign.

---

## 6. What this phase establishes, and what remains

**Established for ontology 0.1.** The Study 2 conceptual schema became a formal
OWL/RDF TBox, generated reproducibly from a single specification, traceable to the
inventory and empirical validations, and was validated authoritatively with HermiT and
additionally cross-checked with ELK. Ontology 0.1 was frozen at that validation point.

**Historical 0.1.1 status.** The formalization patch passed structural and
deterministic-build validation and was manually validated with HermiT and cross-checked with ELK in Protégé on 2026-07-23. Ontology 0.1.1 is formally frozen for deterministic KG extraction; the complete validation record appears in Section 7.1.

**Historical 0.1.2 status.** Local generation, RDF/XML structural checks, merged-property
regressions, inventory reconciliation, frozen-output compatibility checks, and
three-build byte determinism are complete. Manual Protégé validation is also complete:
HermiT passed with ontology consistency and zero unsatisfiable named classes; ELK
completed with profile-incompleteness warnings and is retained only as a profile-limited
classification cross-check. Ontology 0.1.2 is formally frozen. The 0.1.1 reasoner
record below remains historical.

**Stated as out-of-TBox (for the manuscript).** Two design commitments are enforced
outside OWL and must be described as such: (i) evidence completeness for
externally-typed nodes is guaranteed by the extraction rule and validated in the ABox,
not by an OWL restriction; (ii) edge-level evidence is materialized as relationship
properties in the property graph, not as OWL axioms.

**Current 0.1.3 status.** The approved minimal pre-pilot patch has been generated,
structurally validated, and manually validated with HermiT. HermiT completed
successfully, found the ontology consistent with zero unsatisfiable named classes, and
reported no execution errors. HermiT is authoritative for the formal validation and
freeze decision, and ontology 0.1.3 is formally frozen. The deterministic ABox backbone
remains unchanged, and no deterministic extractor has been rerun.

---

## 7. Formalization patch 0.1.1 (2026-07-23)

Publication Phase B exposed a translation omission in ontology 0.1. The approved
global relation `D-05 referencesDataset` already included the domain branch `Paper` →
`DatasetResource`, but `ontology_spec.yaml` represented only the documentation-module
realization (`C-DC15`). This was a formalization error rather than a conceptual
redesign.

Version 0.1.1 adds `C-P29 referencesDataset` as the Paper-module realization of
`D-05`, with `cito:citesAsDataSource` as its primary reuse anchor and
`dcterms:references` as an alternative anchor. It records bibliographic references
deterministically typed as dataset citations and remains distinct from `C-P20
usesDataset` and `C-P24 mentionsDataset`. The patch also removes the incorrect
`C-D19 → D-05` mapping: `C-D19 references` remains a generic outgoing relation whose
domain is `DatasetResource`.

A final completeness review found the same translation omission for the already
approved `Repository` domain branch of D-05. `C-C19 referencesDataset` completes that
branch as `Repository` → `DatasetResource`, using `dcterms:references` for an explicit
dataset DOI or URL without sufficient evidence of use. It remains distinct from
`C-C15 usesDataset`. This is another module realization of the existing D-05 relation,
not a conceptual ontology change.

The final branch audit then added four omitted Documentation-module realizations of
relations already present in the conceptual global inventory: `C-DC22 references` →
D-15, `C-DC23 referencesFeature` → D-18, and `C-DC24 mentionsModel` plus
`C-DC25 mentionsDataset` → D-21. The formal `mentionsModel` merge also exposed that
`C-D18`, whose DatasetResource range includes `Tool`, had been serialized under its
narrative `mentionsModel` alias rather than its use semantics. It is now formally
`usesTool`, keeping D-21 `mentionsModel` restricted to `Paper` and
`DocumentationPage`. These corrections complete the existing conceptual branches;
they do not add a relation family or change extraction behavior.

`C-DC02i` remains the canonical machine-readable inventory ID for `hasSubPage`, and
`C-DC21` remains a narrative alias recorded in the inventory and OWL comment only.
No second formal inventory annotation was minted and the frozen CIROH Hub graph was
not migrated. Likewise, `C-DC18` is formally `announces`; D-19 remains the broader
conceptual announcement/reference family.

Files changed across this patch are `ontology_v0.1.md`, `ontology_inventory.md`,
`ontology_formalization.md`, `ontology_spec.yaml`, the generated
`ciroh_ontology.owl`, the Publication Phase B contract and mapping, the CIROH Hub v1
compatibility notes, and the focused ontology structural test. `build_ontology.py`
required no relation-specific modification because its generic same-name grouping
already merges module relations, constructs union domains/ranges, and retains all
inventory and `maps_to` annotations.
The cleanup did require one generic builder capability: every class or relation
`alt_anchor` is now retained as a second `reuseAnchor` annotation and deterministic
explanatory comment, without adding logical axioms or entity-specific branches.

The regenerated build reports:

| Element | Count |
|---|---:|
| Source class declarations | 75 |
| Source relation declarations | 105 |
| Minted CIROH classes | 51 |
| Referenced external classes | 22 |
| Object properties | 83 |
| Datatype properties | 18 |
| `owl:imports` | 6 |

The generated RDF/XML is 215,494 bytes with SHA-256
`dc873cad75979ae4599ef48051a5cb11ee2d7425299d6dbfdb3f9ad1d759209b`.
The single generated `referencesDataset` property has effective domain `Paper ∪
DocumentationPage ∪ Repository`, range `DatasetResource`, and inventory annotations
`C-P29`, `C-DC15`, and `C-C19`. Its addition does not increase the object-property
count because all three declarations share the same formal relation name.

The four added declarations merge into existing properties and therefore leave the
object-property count at 83. Their signatures are: `references` with domain
`DatasetResource ∪ DocumentationPage` and range `Paper ∪ Repository ∪
DatasetResource ∪ DocumentationPage`; `referencesFeature` with domain
`DatasetResource ∪ DocumentationPage` and range `HydrologicFeature`;
`mentionsModel` with domain `Paper ∪ DocumentationPage` and range
`ComputationalModel`; and `mentionsDataset` with domain `Paper ∪ DocumentationPage`
and range `DatasetMention ∪ DatasetResource`.

Twenty ontology-focused structural tests passed. They cover version `0.1.1`, all
merged signatures and inventory annotations, `C-DC02i`/`C-DC21` alias traceability,
the unchanged frozen Hub hierarchy ID, relation-semantic distinctions, 105 unique
source relation declarations, generic alternative-anchor preservation, and three
independent-process deterministic builds. The complete project suite passed with 174
tests before Publication Phase B was added, with 1 environment-based skip and 64
subtests; the skipped Owlready2 test passed in
the dedicated ontology environment.

The inventory/YAML reconciliation reports zero unexplained mismatches. Exact IDs,
shared-entity narrative aliases (including `A-DC04` → `A-P04`), the hierarchy alias
`C-DC21` → `C-DC02i`, unnumbered technical shared-relation IDs, conceptual D rows,
extraction-category B rows, and competency-question E rows each have an explicit
disposition. All 180 class/relation inventory IDs in YAML are unique.

The checked D-01 through D-25 audit now reports zero unexplained missing domain
branches. Each branch is tied to a compatible relation with explicit `maps_to`, a
documented grouped-relation realization, or an explicit multi-property mechanism
such as D-06 or D-16. Three separately spawned builds were byte-identical to the
canonical artifact and shared the SHA-256 above.

### 7.1 Manual HermiT validation and ontology freeze

Ontology 0.1.1 was manually validated on 2026-07-23 in Protégé 5.6.5 with
HermiT 1.4.3.456. The validated ontology SHA-256 was
`dc873cad75979ae4599ef48051a5cb11ee2d7425299d6dbfdb3f9ad1d759209b`.
Protégé loaded the complete import closure with all six direct imports. The P-Plan
logical IRI `http://purl.org/net/p-plan` resolved through
`src/ontology/catalog-v001.xml` to the local document
`src/ontology/imports/p-plan.owl` before classification.

HermiT completed classification without reporting inconsistency. The ontology was
consistent, the inferred hierarchy contained zero named classes under `owl:Nothing`,
and HermiT reported no execution errors. `prov:EmptyCollection` is an imported
PROV-O class/individual punning case, not an unsatisfiable CIROH class. PROV-O
generated non-blocking redeclaration warnings for `prov:wasRevisionOf` and
`prov:specializationOf`. A Fact++ startup warning was unrelated to the HermiT run.

These results apply to ontology 0.1.1 and its complete locally resolved import
closure.

ELK 0.6.0 was also run in Protégé on 2026-07-23 against the same ontology 0.1.1
artifact (`dc873cad75979ae4599ef48051a5cb11ee2d7425299d6dbfdb3f9ad1d759209b`)
and complete locally resolved import closure used for the HermiT validation. ELK
completed classification without reporting an inconsistency, and zero named classes
were inferred under `owl:Nothing`. Because ELK supports a smaller OWL profile than
HermiT, this agreement is expected and is treated as a cross-check rather than fully
independent confirmation across the ontology's complete expressivity.

The historical ontology 0.1 reasoner record in Section 5 remains separate. With
structural validation and authoritative manual HermiT classification complete, and
with ELK retained as an additional profile-limited technical cross-check, ontology
0.1.1 is formally frozen for deterministic KG extraction.

---

## 8. LLM-readiness relation patch 0.1.2 (2026-07-27)

Ontology 0.1.2 is an additive and corrective relation patch. It adds no class and
does not reopen deterministic extraction. It separates the collapsed 0.1.1 ranges
`C-D18 usesTool` (`Tool` only), `C-C08 describesFunction` (`Function` only),
`C-C11 usesTool` (`Tool` only), and `C-C12 mentionsVariable` (`Variable` only), then
adds the approved model, algorithm, parameter, mention, reference, workflow, and
typed-description declarations under new stable IDs. D-04, D-07, D-21, D-24, and
D-25 are broadened exactly as recorded in the inventory.

The preflight inspected all four frozen Phase B outputs and found no edge using
`C-C08`, `C-C11`, `C-C12`, or `C-D18`. Their recorded SHA-256 values were:

| Frozen ontology-0.1.1 output | SHA-256 before and after the 0.1.2 build |
|---|---|
| `data/interim/papers/publication_nodes_edges.json` | `675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf` |
| `data/interim/datasets/hydroshare_nodes_edges.json` | `c76c1cf9c88fe2a91f4927bd3bd4fc03456e3a2a83190bd3d8c47076f2acb7e3` |
| `data/interim/coderepos/github_nodes_edges.json` | `2f752295a7d465acd094672b0a5961ffd1fe5453d6d576fc497e284068d901a6` |
| `data/interim/documents/ciroh_hub_nodes_edges.json` | `c106c410b6f84a2755d17cec4629b90d5b145c0813c2866005cb20bcea649602` |

The compatibility regression resolves every frozen node class/inventory ID and edge
relation/inventory ID directly or through the extraction contracts' explicit 0.1.1
spellings: class aliases `A-D06` → `A-P04`, `A-D07→A-DOM09` → `A-DOM09`,
`A-D08→A-DOM10` → `A-DOM10`, frozen `A-C02 File` → formal `A-C02 RepoFile`, and
`A-C06` → `A-D05`; edge spellings `A-ID01 (ID-R1)` → `ID-R1`,
`C-D09 / A-AG-R2` → `C-D09`, `C-DC05/A-AG` → `C-DC05`, and frozen global `D-05
referencesDataset` → its `C-C19` module realization. These compatibility rules accept
the existing bytes; they do not rewrite, consolidate, or migrate any node or edge.

The canonical build reports 51 minted CIROH classes, 22 specification-referenced
external classes, 90 object properties, 18 datatype properties, six imports, and 125
source relation declarations. Its SHA-256 is
`2857dc9f8e578367f6d2608da7e05d2ff5b2113fd41ff6c34047b90574b53ee7`.

### 8.1 Authoritative HermiT validation and ELK technical cross-check

Ontology 0.1.2 was manually validated in Protégé against the generated OWL artifact with SHA-256 `2857dc9f8e578367f6d2608da7e05d2ff5b2113fd41ff6c34047b90574b53ee7`.

HermiT completed classification of the ontology and its resolved import closure without reporting an inconsistency or an execution error. No named classes were inferred under `owl:Nothing`. Ontology 0.1.2 was therefore found to be logically consistent, with zero unsatisfiable named classes under HermiT.

ELK also completed class, object-property, data-property, and instance taxonomy computation without an execution error, and no named classes were observed under `owl:Nothing`. ELK reported potential incompleteness because the loaded ontology closure contains constructs outside the OWL 2 EL profile, including data-cardinality axioms and other unsupported OWL constructs. Consequently, the ELK run is recorded as a profile-limited classification cross-check rather than an independent full-consistency validation.

The reasoner-validation outcome for ontology 0.1.2 is therefore:

* HermiT: PASS — ontology consistent; zero unsatisfiable named classes.
* ELK: COMPLETED WITH PROFILE-INCOMPLETENESS WARNINGS — no execution error and zero observed unsatisfiable named classes, but full satisfiability checking was not available for the complete ontology closure.

With structural validation and authoritative HermiT validation complete, and with the
profile-limited ELK technical cross-check recorded separately, ontology 0.1.2 is
formally frozen at the validated SHA-256 recorded above.

---

## 9. Minimal pre-pilot patch and freeze 0.1.3 (2026-07-30)

The approved pre-pilot gate narrowed `C-P08 testedBy` from a
`TheoreticalBasis/Hypothesis` union domain to `Hypothesis` only while retaining range
`Method/Experiment`. The possible TheoreticalBasis grounding relation is deferred and
no replacement property was added. The unsupported `Conclusion → Finding` summary
branch was removed from the `C-P12 hasLimitation` notes; its formal
`Paper/Finding → Limitation` signature is unchanged. `C-P09 supports` retains its
`Finding/Claim → Claim/Conclusion` signature and now documents positive support only,
without undeclared negative or generic argument aliases.

Preflight inspection found no `C-P08` or `testedBy` edge in any frozen Phase B output.
The four recorded deterministic SHA-256 values remained unchanged before and after the
build:

| Frozen deterministic output | SHA-256 before and after the 0.1.3 build |
|---|---|
| `data/interim/papers/publication_nodes_edges.json` | `675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf` |
| `data/interim/datasets/hydroshare_nodes_edges.json` | `c76c1cf9c88fe2a91f4927bd3bd4fc03456e3a2a83190bd3d8c47076f2acb7e3` |
| `data/interim/coderepos/github_nodes_edges.json` | `2f752295a7d465acd094672b0a5961ffd1fe5453d6d576fc497e284068d901a6` |
| `data/interim/documents/ciroh_hub_nodes_edges.json` | `c106c410b6f84a2755d17cec4629b90d5b145c0813c2866005cb20bcea649602` |

The canonical generated ontology contains 75 source class declarations, 125 source
relation declarations, 51 minted CIROH classes, 22 referenced external classes, 90
object properties, 18 datatype properties, and six direct imports. The generated RDF/XML
is 231,853 bytes with SHA-256
`ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57`.

Thirty-one ontology-focused regression tests passed in the dedicated ontology
environment. They cover the 0.1.3 spec and OWL version, exact `C-P08`, `C-P09`, and
`C-P12` signatures and notes, unchanged declaration counts, inventory reconciliation,
all existing compatibility checks, frozen-output hashes, absence of frozen `C-P08`
assertions, and three independent byte-identical builds.

### 9.1 Authoritative manual HermiT validation and freeze

The manual Protégé reasoner gate used the OWL with SHA-256
`ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57`.
HermiT completed successfully, found the ontology consistent, inferred no named classes
under `owl:Nothing`, and reported no execution errors. HermiT is the authoritative
reasoner for the formal ontology validation and freeze decision.

**HermiT: PASS — ontology consistent; zero unsatisfiable named classes; no execution
errors.** With structural validation and the authoritative manual HermiT gate complete,
ontology 0.1.3 is formally frozen at the validated SHA-256 above.

### 9.2 Technical ELK cross-check

ELK completed against the same validated OWL and produced no named classes under
`owl:Nothing`. It reported profile-related potential incompleteness because the
ontology contains constructs outside the OWL 2 EL profile. The ELK execution is retained
only as a technical, profile-limited cross-check: it is not an independent full
satisfiability validation and is not part of the formal PASS criterion. Detailed ELK
warnings belong in this technical record or a repository log rather than the
manuscript-facing ontology validation summary.
