# Ontology Formalization (OWL/RDF) — Study 2, Phase 1 Record

**Multi-Granular Knowledge Graph for Heterogeneous CIROH Artifacts**

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
        │  HermiT / ELK (in Protégé)
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

Five translation decisions required explicit resolution because the conceptual schema
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
- `documentedBy` ⇄ `describes`, with `describesTool` and `describesModel` as
  sub-properties of a parent `describes` — this realizes the `documentedBy` inverse
  named in the competency-question validation and completes the product-hub aggregation
  (`catalogs` + `hasComponent` + `implementedBy` + `describedInPaper` + `documentedBy`).

Most other reverse traversals were **deliberately not** given inverse properties,
because both SPARQL and the property-graph query layer (Cypher) traverse relations in
either direction without an inverse being declared. An inverse property is warranted
only when the reverse direction needs a name in the schema (as `documentedBy` does) or
when the reasoner should materialize it; minting inverses for every relation would
contradict the lightweight design without adding query capability.

---

## 4. The generated ontology

`build_ontology.py` (owlready2) reads the specification and emits `ciroh_ontology.owl`
in RDF/XML. The build prints a summary; the current figures are:

| Element | Count |
|---|---|
| Minted CIROH classes | 51 |
| Referenced external classes | 22 |
| Object properties | 81 |
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

Traceability annotations attached to every entity include the inventory ID, the reuse
anchor, the S/E/F status, the node kind, and — for property-anchored classes — the
alignment property recorded as a non-logical annotation.

---

## 5. Reasoner validation

The generated ontology was loaded in Protégé (with the six imported vocabularies
resolved) and checked with the **HermiT 1.4.3.456** reasoner. The result:

- **Consistent** — no contradiction among the class, property, domain/range,
  cardinality, inverse, and sub-property axioms. A consistent ontology admits a model;
  an inconsistent one would be unusable, since any statement could be "derived" from a
  contradiction.
- **No unsatisfiable classes** — nothing was inferred as a subclass of `owl:Nothing`.
  Every class is satisfiable, i.e. capable of having instances. No node type in the
  schema is defined in a self-contradictory way; when the ABox is populated, every
  designed node type can exist with real data.

The result was cross-checked with a second reasoner, **ELK 0.6.0**, which likewise
reported consistency and no unsatisfiable classes. (ELK covers a smaller OWL profile
than HermiT, so agreement is expected rather than independent confirmation across the
full expressivity, but the concurrence is a useful sanity check.)

A clean reasoner result was the expected — not accidental — outcome of validating the
design before formalizing: the schema reached the reasoner already sound, so it passed
after the planned refinements rather than requiring redesign.

---

## 6. What this phase establishes, and what remains

**Established.** The Study 2 conceptual schema is now a formal OWL/RDF TBox, generated
reproducibly from a single specification, traceable to the inventory and the empirical
validations, and verified logically consistent with no unsatisfiable classes by two
reasoners. The TBox is frozen.

**Stated as out-of-TBox (for the manuscript).** Two design commitments are enforced
outside OWL and must be described as such: (i) evidence completeness for
externally-typed nodes is guaranteed by the extraction rule and validated in the ABox,
not by an OWL restriction; (ii) edge-level evidence is materialized as relationship
properties in the property graph, not as OWL axioms.

**Remaining (next phases).** Populate the ABox by extracting instances from the corpus
— first the deterministic extractor (metadata, manifests, identifiers, file roles;
no LLM required), then the LLM extractor for the discourse and domain-entity layers —
loading the result into the property graph under this schema. Reasoner-based ABox
checks (e.g. consistency of the populated graph) and the competency questions as
executable queries follow once instances exist.
