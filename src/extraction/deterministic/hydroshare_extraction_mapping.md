# HydroShare → Ontology — Deterministic Extraction Mapping

**Study 2 — Knowledge-graph construction, deterministic layer (Module 2: Dataset/HydroShare)**

**Purpose.** This document is the *contract* between the HydroShare corpus records
(`data/interim/datasets/ciroh_hydroshare_corpus.json`, 42 resources) and the ontology
(`docs/ontology_inventory.md` / `src/ontology/ontology_spec.yaml`). For every JSON field
that is extracted **deterministically** (no LLM), it states which ontology node or edge
it produces, the inventory ID, and how the `EvidenceSpan` is filled. It is the
specification the deterministic HydroShare extractor implements; it is also a
manuscript-ready record of how the KG's dataset layer is populated.

**Scope.** Deterministic only. Fields requiring LLM interpretation (abstract/README
prose → `Variable`, `DatasetMention`, `Tool`/`Model` mentions, `Measurement`) are listed
in §5 as out-of-scope here and deferred to the LLM extractor.

---

## 1. Conventions

**Node identity.** Every node needs a stable, deterministic ID so the same real-world
entity is not duplicated within or across resources. IDs are derived from the source
field, never random, so re-runs are idempotent:
- `DatasetResource` → `resource_id` (HydroShare's 32-char hex).
- `Person` → ORCID if present (from `creator_identifiers`/`contributor_identifiers`),
  else a normalized `name`-based key. Google Scholar and ResearchGate identifiers are
  also emitted as attached `Identifier` nodes, but do not replace ORCID/name as the
  Person key (consolidation across regimes happens later, per the agent layer).
- `Organization` → ROR if present, else normalized name.
- `License` → SPDX id if resolvable, else the `rights_url`.
- `Subject` → normalized subject string.
- `Award` → funding agency + award number.
- `Identifier` → the identifier string itself (DOI/URL/ORCID/ROR).
- `SpatialCoverage`, `TemporalCoverage`, `ToolConfiguration` → scoped to their owner
  resource (`{resource_id}:spatial`, etc.); these are per-resource, not shared.

**EvidenceSpan (every node and edge).** Two fields, per the corrected design:
- `evidenceText` = the **value** that semantically supports the node/edge (the license
  text, the creator name, the period, the abstract). For purely structural facts (a
  file exists), this is the structural descriptor (the filename).
- `sourceLocation` = the **provenance path**: `{resource_id}` + the JSON field path
  (e.g. `rights.rights_statement`, `creators[2].name`, `hydroshare_links[0]`).
- `extractionMethod` = `"deterministic"`.
- `sourceArtifact` = `"hydroshare:{resource_id}"`.

**Subtype gating.** The three `resource_type` values populate different fields. Rules
tagged **[Composite]**, **[Collection]**, or **[Tool]** apply only to that subtype;
untagged rules apply to all three. (Composite has `files`; Collection has
`collection_summary`/members and no own files; Tool has `tool_config` and no own files.)

**curationStatus.** Resources in the corpus are `curated`. Targets referenced by
identifier but not themselves in the corpus (e.g. a related DOI outside the 42) are
emitted as `referenced` stubs (see §3, relations).

**Shared entities and consolidation.** `Person` and `Organization` are shared,
consolidated entities. The same organization may appear as an author's affiliation
(`creators[i].organization`) in one resource and as a `funding_agency` in another, and
the same person across resources (and later across artifact types). The deterministic
extractor **seeds** each mention as a node with the best deterministic key it has
(ORCID/ROR where present, else a normalized name key) and records which identifier
regime was used; it does **not** itself merge duplicates. Entity unification (e.g.
"University of Alabama" = "Univ. of Alabama" = "UA"; "D. Tarboton" = "David Tarboton")
is a separate consolidation step run after extraction.

---

## 2. Node rules (field → entity)

| # | JSON field | → Node (class) | Inventory ID | evidenceText | sourceLocation | Notes |
|---|---|---|---|---|---|---|
| N1 | `resource_id` (+ `resource_type`, `title`, `abstract`, `language`) | `DatasetResource` | A-D01 | `title` (+ abstract as a longer evidence value) | `{resource_id}` (record root) | the artifact node; `abstract` is rich evidence text |
| N2 | `resource_type` | `ResourceType` (controlled: Composite/Collection/Tool) | A-D02 | the type string | `resource_type` | drives subtype gating |
| N3 | `creators[i]` | `Person` (`schema:Person`) | A-D04→A-AG01 | `creators[i].name` | `creators[i]` | role = creator; match ORCID from `creator_identifiers` |
| N4 | `contributors[i]` | `Person` | A-AG01 | `contributors[i].name` | `contributors[i]` | role = contributor; may be empty |
| N5 | `creator_identifiers[i]` / `contributor_identifiers[i]` | `Identifier` (ORCID, GoogleScholarID, or ResearchGateID) attached to the Person | A-ID01 | the identifier URL | `creator_identifiers[i]` | records `id_type`; links Person→Identifier for later consolidation |
| N6 | `rights.rights_statement` (+ `rights.rights_url`) | `License` | A-D05 | the rights statement text (e.g. "Creative Commons Attribution CC BY 4.0") | `rights` | anchor `dcterms:license`/SPDX; resolve SPDX id from URL where possible |
| N7 | `subjects[i]` | `Subject` (`ciroh:Subject` ⊑ `skos:Concept`) | A-D06 | the subject string | `subjects[i]` | controlled tags + free keywords |
| N8 | `spatial_coverage` | `SpatialCoverage` (`geo:Geometry`) | A-D07→A-DOM09 | human-readable extent (e.g. bbox / "CONUS") | `spatial_coverage` | per-resource footprint, not a place |
| N9 | `temporal_coverage` | `TemporalCoverage` | A-D08→A-DOM10 | the period (e.g. "1979–2023") | `temporal_coverage` | start/end |
| N10 | `awards[i]` | `Award` | A-D09 | award title/number | `awards[i]` | funding |
| N11 | `awards[i].funding_agency` | `Organization` | A-AG02 | agency name | `awards[i].funding_agency` | ROR if resolvable; funding source |
| N11b | `creators[i].organization` / `contributors[i].organization` (where non-empty) | `Organization` | A-AG02 | the organization string | `creators[i].organization` | affiliation source; same `Organization` class as funding agencies — a shared, consolidated entity |
| N12 | `identifier` / `url` (+ DOI if present) | `Identifier` | A-ID01 | the identifier string | `identifier` / `url` | the resource's own identifier(s) |
| N13 | **[Composite]** `files[i]` | `DatasetFile` (`schema:DataDownload`) | A-D03 | `files[i].file_name` (+ extension) | `files[i]` | only Composite has own files; carry checksum/size as attributes |
| N14 | **[Tool]** `tool_config` | `ToolConfiguration` | A-D10 | a descriptor (e.g. "CIROH 2i2c JupyterHub, v{tool_version}") | `tool_config` | + `launchURL` attribute (see N15) |
| N15 | **[Tool]** `tool_config.app_home_page_url` | `launchURL` attribute on the `ToolConfiguration` (literal) | A-D10 attr | the URL string | `tool_config.app_home_page_url` | the launch endpoint as a literal (datatype) |
| N16 | **[Tool]** the launched application | `Tool` (entity) | A-DOM02 | app name (from title / home-page host) | `tool_config.app_home_page_url` | the launched app as a NODE (so it can consolidate with a Hub-described Tool); target of `launchesApp` |

---

## 3. Edge rules (field → relation)

| # | JSON field | → Edge (relation) | Inventory ID | evidenceText | sourceLocation | Notes |
|---|---|---|---|---|---|---|
| E1 | `resource_type` | `DatasetResource` —hasResourceType→ `ResourceType` | C-D01 | the type string | `resource_type` | |
| E2 | **[Composite]** `files[i]` | `DatasetResource` —hasFile→ `DatasetFile` | C-D02 | `files[i].file_name` | `files[i]` | one edge per file |
| E3 | `creators[i]` | `DatasetResource` —hasCreator→ `Person` | C-D03 | `creators[i].name` | `creators[i]` | ordered (creator order matters) |
| E4 | `contributors[i]` | `DatasetResource` —hasContributor→ `Person` | C-DC05/A-AG | `contributors[i].name` | `contributors[i]` | reuse agent contributor relation |
| E5 | `identifier`/`url`/DOI | `DatasetResource` —hasIdentifier→ `Identifier` | C-D04 | the identifier string | `identifier` | |
| E6 | `creator_identifiers[i]` / `contributor_identifiers[i]` | `Person` —hasIdentifier→ `Identifier` | A-ID01 (ID-R1) | the identifier URL | `creator_identifiers[i]` | ORCID, Google Scholar, and ResearchGate identifiers |
| E7 | `rights` | `DatasetResource` —hasLicense→ `License` | C-D05 | rights statement text | `rights` | |
| E8 | `subjects[i]` | `DatasetResource` —hasSubject→ `Subject` | C-D06 | the subject string | `subjects[i]` | |
| E9 | `spatial_coverage` | `DatasetResource` —hasSpatialCoverage→ `SpatialCoverage` | C-D07 | the extent | `spatial_coverage` | |
| E10 | `temporal_coverage` | `DatasetResource` —coversPeriod→ `TemporalCoverage` | C-D08 | the period | `temporal_coverage` | |
| E11 | `awards[i]` | `DatasetResource` —fundedBy→ `Award` | C-D09 / A-AG-R2 | award title/number | `awards[i]` | |
| E12 | `awards[i].funding_agency` | `Award` —(funder)→ `Organization` | A-AG-R2 | agency name | `awards[i].funding_agency` | award↔agency |
| E13 | `creators[i].organization` / `contributors[i].organization` (where non-empty) | `Person` —affiliatedWith→ `Organization` | A-AG-R1 | the organization string | `creators[i].organization` | the `organization` key inside each creator/contributor dict; not always filled |
| E14 | **[Tool]** `tool_config` | `DatasetResource` —hasToolConfig→ `ToolConfiguration` | C-D10 | tool descriptor | `tool_config` | Tool subtype only |
| E15 | **[Tool]** `tool_config.app_home_page_url` | `ToolConfiguration` —launchesApp→ `Tool` | C-D11 | the launched-app name/URL | `tool_config.app_home_page_url` | object property to the Tool node (N16) |
| E16 | **[Collection]** `hydroshare_links[i]` where `predicate_qname == dcterms:hasPart` | `DatasetResource`(Collection) —hasMember→ `DatasetResource` | C-D12 | `target` citation text | `hydroshare_links[i]` | target via `target_resource_id`; if target ∉ corpus → `referenced` stub |
| E17 | `hydroshare_links[i]` / `typed_relations[i]` where `predicate_qname == dcterms:isPartOf` | `DatasetResource` —isMemberOf→ `DatasetResource`(Collection) | C-D13 | `target` citation text | `hydroshare_links[i]` | the inverse direction; resolved by `target_resource_id` |
| E18 | `typed_relations[i]` where predicate is a derivation (e.g. `prov`/version) | `DatasetResource` —derivedFrom→ `DatasetResource` | C-D14 | `target` text | `typed_relations[i]` | status S/E; only for derivation predicates with dataset targets; code-host `dcterms:source` is handled by E19 |
| E19 | `related_resources[i]` / `typed_relations[i]` with DOI/URL to paper/repo/dataset | `DatasetResource` —references→ `Paper`/`Repository`/`DatasetResource` | C-D19 | `target` text | `related_resources[i]` | HydroShare IDs → DatasetResource; paper DOI → Paper; code-host URL → Repository; other external URL → referenced DatasetResource with URL+host; text-only targets are deferred to the LLM layer |
| E20 | `geospatial_relations[i]` (geoconnex URI) | `DatasetResource` —referencesFeature→ `HydrologicFeature` | C-D15 | geoconnex URI/label | `geospatial_relations[i]` | empty in the three examples; deterministic when present (geoconnex) |
| E21 | `typed_relations[i]` / `related_resources[i]` / `relations_from_meta[i]` / `hydroshare_links[i]` where `predicate_qname == hsterms:isExecutedBy` (or equivalent metadata label) | `DatasetResource` —isExecutedBy→ `Tool` | C-D20 | `target` text | the originating relation entry | resolve a corpus ToolResource to its launched Tool entity; otherwise emit a referenced Tool stub from HydroShare ID or URL; semantic dedup yields one edge per unique source/target |

---

## 4. Subtype field-presence summary (gating reference)

| Field | Composite | Collection | Tool |
|---|---|---|---|
| `files` | populated | empty | empty |
| `collection_summary` / members | null | populated | null |
| `tool_config` | null | null | populated |
| creators/subjects/rights/coverage/awards/identifiers | populated | populated | populated |
| relations (`hydroshare_links`, `typed_relations`, `related_resources`) | as present | as present (incl. `hasPart` members) | as present |

The shared rows (creators, subjects, rights, coverages, awards, identifiers, relations,
including `isExecutedBy`)
run for all three subtypes; only N13/E2 (files), N14–N16/E14–E15 (tool config), and
E16 (collection members) are subtype-specific.

---

## 5. Deferred to the LLM extractor (NOT in this deterministic layer)

These fields require interpretation of prose and are out of scope here; recorded so the
contract is explicit about the boundary:
- `abstract` and README text → `Variable` (C-D16, E), `DatasetMention`, `Tool`/
  `ComputationalModel` mentions (C-D18), `Measurement` (C-D17, coverage ≈ 0), domain
  `Concept`. The deterministic layer stores the abstract/README only as candidate
  evidence text; it does not mint these domain nodes.
- `EvaluationMetric` / `Parameter` where a README reports them → LLM layer.

The deterministic extractor emits the abstract verbatim as an attribute of the
`DatasetResource` so the LLM layer can later read it from the interim output without
re-opening the raw corpus.

---

## 6. Output (interim format)

The extractor writes a **rich JSON** interim file (per the decision to inspect before
loading), with two top-level arrays:
- `nodes`: each `{id, class, inventoryId, attributes{…}, evidence{evidenceText,
  sourceLocation, extractionMethod, sourceArtifact}, curationStatus}`.
- `edges`: each `{id, relation, inventoryId, source, target, evidence{…}}`.

This interim JSON is the single faithful source from which both the Neo4j load (evidence
on nodes and relationship properties) and any RDF export (with reification/RDF-star for
edge evidence) are later derived — so the two representations stay consistent without
converting one into the other directly.

---

## 7. Validation checks (after extraction, before loading)

- Node/edge counts per class/relation, per resource subtype, vs. expectation.
- Every node and edge has a non-empty `evidence.sourceLocation` and `extractionMethod`.
- No duplicate node IDs for the same real-world entity within a resource.
- Every `hasMember`/`isMemberOf`/`references`/`isExecutedBy` target either resolves to a corpus
  `resource_id` or is emitted as a `referenced` stub (none silently dropped).
- Person nodes carry their identifier regime (ORCID vs. name-key), and available
  ORCID/GoogleScholarID/ResearchGateID nodes, for later consolidation.
