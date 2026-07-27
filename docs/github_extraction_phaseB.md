# GitHub Consolidated Corpus → Nodes/Edges — Extraction Contract (Phase B)

**Study 2 — Knowledge-graph construction, deterministic layer (Module 3: Code Repository / GitHub)**

**Purpose.** This document is the execution contract for **Phase B** of the GitHub pipeline. It defines how the stable Phase A corpus (`data/interim/coderepos/ciroh_github_corpus.json`, schema `1.1.0`) is transformed into an inspectable deterministic nodes/edges file (`data/interim/coderepos/github_nodes_edges.json`). The companion `github_extraction_mapping.md` contains the exhaustive field-to-ontology rules.

**Core boundary.** Phase B maps structured Phase A facts to ontology instances and relations. It does not re-open the raw corpus, make network calls, interpret source code, infer facts from prose, perform fuzzy entity resolution, or load the final graph database. It emits mention-level entities, exact-identifier resolutions, public evidence provenance, and a complete extraction report for inspection before alignment and assembly.

---

## 1. Position in the pipeline

The GitHub path has four distinct stages:

1. **Raw acquisition** — `data/raw/coderepos/{repo_name}/`, produced by the frozen download notebook.
2. **Phase A preprocessing** — raw → `ciroh_github_corpus.json` (`schema_version: 1.1.0`).
3. **Phase B deterministic extraction** — consolidated corpus → `github_nodes_edges.json` (**this contract**).
4. **Later stages** — LLM extraction from prose, semantic alignment/consolidation, graph assembly, Neo4j/RDF loading, and evaluation.

Phase B reads only the consolidated corpus. Internal fields such as `source_path` and `manifest_path` are sufficient to resolve evidence to public GitHub locations; no raw file needs to be reopened.

---

## 2. Input contract

### 2.1 Required input

```text
data/interim/coderepos/ciroh_github_corpus.json
```

Required top-level shape:

```json
{
  "schema_version": "1.1.0",
  "repos": []
}
```

Phase B must fail fast when:

- `schema_version` is not an explicitly supported version;
- `repos` is missing or not an array;
- a repository lacks `repo_id`, `html_url`, or `archive.frozen_commit_sha`;
- `files.inventory` is missing;
- a required source path cannot be converted to a repository-relative path where a public file URL is required.

A configurable compatibility list may accept later additive Phase A versions, but silent best-effort parsing is not allowed.

### 2.2 Expected complete-corpus baseline

The Phase A 1.1.0 closure validation established the following corpus-level expectations:

```text
repositories: 51
file inventory records: 11,702
downloaded file records: 499
dockerfile records: 15
dependencies: 305
repo dependencies: 8
execution-environment records: 35
parse warnings: 5
```

These counts are regression anchors, not hard-coded extraction logic. A different corpus conforming to the same schema may contain different counts.

---

## 3. Output contract

Phase B writes a deterministic, inspectable JSON artifact:

```text
data/interim/coderepos/github_nodes_edges.json
```

Top-level shape:

```jsonc
{
  "schema_version": "1.0.0",
  "phase_b_version": "1.0.0",
  "source_schema_version": "1.1.0",
  "source_type": "github",
  "nodes": [],
  "edges": [],
  "deferred": [],
  "skipped": [],
  "unresolved": [],
  "warnings": [],
  "stats": {}
}
```

No generation timestamp is included because it would break byte stability. The source acquisition time already exists in each repository record.

### 3.1 Node shape

```jsonc
{
  "id": "github:repo:807668057",
  "class": "Repository",
  "inventoryId": "A-C01",
  "attributes": {},
  "canonicalKey": "github-repo-id:807668057",
  "identityRegime": "github_numeric_id",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": "CIROH-UA/deep_bucket_lab",
    "sourceLocation": "https://api.github.com/repos/CIROH-UA/deep_bucket_lab",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/deep_bucket_lab",
    "version": "<downloaded_at_epoch>"
  },
  "internalLineage": {
    "phaseAField": "repo root",
    "phaseAVersion": "1.1.0"
  }
}
```

### 3.2 Edge shape

```jsonc
{
  "id": "edge:hasFile:<stable-hash>",
  "relation": "hasFile",
  "inventoryId": "C-C01",
  "source": "github:repo:807668057",
  "target": "github:file:807668057:<stable-hash>",
  "attributes": {},
  "evidence": {
    "evidenceText": "README.md",
    "sourceLocation": "https://github.com/CIROH-UA/deep_bucket_lab/blob/<sha>/README.md",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/deep_bucket_lab/tree/<sha>",
    "version": "<sha>"
  },
  "internalLineage": {
    "phaseAField": "files.inventory[path=README.md]",
    "phaseAVersion": "1.1.0"
  }
}
```

### 3.3 Evidence cardinality

Every emitted node and edge must have one non-empty primary `evidence` object. When Phase A merged several equivalent declarations, Phase B selects a primary declaration deterministically and preserves all declarations under an attribute such as `sourceDeclarations`. The primary selection order is:

1. `manifest_scope: root`;
2. `manifest_scope: docs`;
3. `manifest_scope: example`;
4. lexicographically smallest `manifest_path`;
5. lexicographically smallest `raw_line`.

This preserves compatibility with the existing interim format while retaining all Phase A source declarations for audit.

---

## 4. Determinism and idempotency

Phase B is a pure function of:

- the Phase A corpus;
- the frozen ontology inventory IDs;
- the Phase B mapping contract;
- optional exact-identifier lookup indices supplied by already-extracted modules.

It must not use random UUIDs, current timestamps, network responses, model calls, filesystem mtimes, or iteration order from unordered containers.

Required ordering:

- repositories by `(name.casefold(), repo_id)`;
- nodes by `id`;
- edges by `id`;
- report entries by `(repo_id, category, sourcePath, reason)`;
- attributes containing sets as sorted arrays;
- source declarations by the primary-evidence order in §3.3.

Two runs on identical inputs and indices must produce byte-identical JSON.

---

## 5. Identity model: mention seeding, not semantic consolidation

Phase B creates deterministic **entity mentions**. It does not merge possible real-world duplicates across identity regimes or artifacts. Each mention carries a `canonicalKey` that the later alignment stage can use.

### 5.1 Curated repository identity

```text
id = github:repo:{repo_id}
canonicalKey = github-repo-id:{repo_id}
```

GitHub numeric ID is the curated repository key. `full_name` and canonical URL are aliases and attributes, not the primary ID.

### 5.2 Source-scoped mention identity

Files, dependencies, environments, people from CFF/package metadata, licenses, tools, and versions use stable source-scoped IDs. The general pattern is:

```text
{source}:{class}:{owner-key}:{stable-hash(canonical source discriminator)}
```

The hash is lowercase SHA-256 truncated to 20 hexadecimal characters. The unhashed canonical values remain in attributes and `canonicalKey`.

Examples:

```text
github:file:{repo_id}:{hash(path)}
github:dependency:{repo_id}:{hash(ecosystem|canonical_name)}
github:env:{repo_id}:{hash(kind|source_path)}
github:person:{repo_id}:{hash(regime|source_path|ordinal)}
github:tool:{repo_id}:{hash(source_path|canonical_name)}
github:version:{repo_id}:{hash(source_path|version)}
```

### 5.3 Exact target handling

Exact persistent identifiers are not fuzzy evidence, but Phase B still preserves the pre-alignment mention layer. The rule is:

- targets inside the same GitHub corpus resolve to the existing curated Repository node;
- targets outside the GitHub corpus become source-scoped referenced stubs carrying an exact `canonicalKey` (DOI, HydroShare ID, GitHub URL, ORCID/ROR/SPDX as applicable);
- the later alignment/assembly stage merges or links those stubs to curated nodes from other modules by exact identifier;
- name similarity alone never resolves a target.

This keeps `github_nodes_edges.json` self-contained and preserves the extraction-before-alignment measurement point.

---

## 6. Two-pass processing architecture

### Pass 1 — Curated entities and local mentions

For every repository record:

1. create the curated `Repository`;
2. create repository `Identifier` mentions;
3. create all `File` nodes from `files.inventory`;
4. create package `Dependency` mentions;
5. create `ExecutionEnvironment` nodes;
6. create contributor/author mentions;
7. create license declarations;
8. create structured Tool and ModelVersion mentions where rules permit;
9. build indices for curated repository ID, canonical URL, and `owner/repo`.

### Pass 2 — Relations and external targets

After all curated repositories are indexed:

1. create repository-internal edges;
2. resolve VCS repository dependencies;
3. handle monorepo self-references without self-loops;
4. resolve CFF preferred citations and typed references;
5. resolve HydroShare URLs;
6. create referenced stubs where exact targets are outside the curated corpus;
7. record deferred, skipped, unresolved, and warning entries.

This architecture guarantees that target resolution does not depend on source order.

---

## 7. Provenance model

Phase B maintains two non-interchangeable provenance channels.

### 7.1 Internal pipeline lineage

`source_path`, `manifest_path`, `repo_metadata.json:*`, `contributors.json[*]`, `archive_info.json:*`, and `files_manifest.json:<path>` describe how the local frozen snapshot was processed. They are preserved under `internalLineage` and in the extraction report.

They must not be presented as the primary public evidence location.

### 7.2 Public evidence provenance for repository files

For evidence contained in a version-controlled file:

```text
sourceArtifact = {html_url}/tree/{frozen_commit_sha}
sourceLocation = {html_url}/blob/{frozen_commit_sha}/{percent-encoded repository path}
version = frozen_commit_sha
```

The path is encoded segment-wise while preserving `/`. The path's case is preserved.

This applies to:

- file existence;
- dependency manifests;
- environment manifests and lockfiles;
- `CITATION.cff` / `CITATION.md`;
- package metadata manifests;
- README URL evidence;
- license declarations sourced from files.

No line anchor is invented. When Phase A lacks line numbers, the blob URL identifies the file and `evidenceText` contains the exact structured value or raw line.

### 7.3 Public provenance for GitHub API-derived metadata

The commit freezes repository files but does not freeze mutable API metadata. For repository metadata:

```text
sourceArtifact = html_url
sourceLocation = https://api.github.com/repos/{full_name}
version = archive.downloaded_at_epoch
```

For contributors:

```text
sourceArtifact = html_url
sourceLocation = https://api.github.com/repos/{full_name}/contributors
version = archive.downloaded_at_epoch
```

The repository page remains a user-friendly alias in attributes. The local raw JSON is the exact acquisition snapshot, retained in internal lineage. A future published RO-Crate/Zenodo corpus may provide a persistent public snapshot of those API responses.

### 7.4 Evidence text

`evidenceText` is the semantic value supporting the assertion, not the internal field path. Examples:

- repository: `CIROH-UA/deep_bucket_lab`;
- file: `.github/actions/README.md`;
- dependency: `numpy>=1.24`;
- contributor: `jmframe (41 contributions)`;
- license: `MIT`;
- preferred citation: DOI or full structured citation descriptor.

---

## 8. Curation status and stubs

- `curated`: the entity is directly represented by a record or structured component in the curated GitHub corpus.
- `referenced`: the entity is mentioned by an exact identifier but is not itself present in the curated corpus/module.

Referenced targets are never silently discarded. Each exact target must either:

1. resolve to an existing curated node;
2. produce a referenced stub allowed by the ontology and mapping;
3. be recorded as deferred/unresolved with an explicit reason when no valid relation can be asserted.

A referenced stub must have at least one identifier and public evidence.

---

## 9. Deterministic-versus-LLM frontier

Phase B deterministically extracts only what structured Phase A fields support.

### Deterministic now

- Repository metadata and identifiers;
- complete File inventory and `hasFile`;
- package dependencies and repository dependencies;
- execution environments and lockfile summaries;
- GitHub contributors, CFF software authors, and package authors;
- licenses and version declarations;
- valid structured CFF preferred citations;
- exact HydroShare resource references;
- structured Tool mentions from CFF/package metadata;
- exact `implementedBy` links from structured repository/source fields.

### Deferred to LLM/prose layer

- RepositoryPurpose;
- Function and Algorithm from prose;
- Workflow and usage instructions;
- Tool/model mentions in README prose;
- `implementsMethod`;
- Variables, parameters, metrics, and concepts from prose;
- `usesDataset` unless explicit semantics beyond URL presence are available;
- `forkedFrom` parent inferred from README/badges;
- CITATION.md interpretation;
- semantic typing of unstructured README DOI/GitHub links.

Source-code AST, import mining, function extraction, and code execution remain out of scope.

---

## 10. Report categories

### 10.1 `deferred`

Valid evidence exists, but interpretation belongs to a later layer.

Examples:

- `citation_md_deferred_to_llm`;
- `readme_github_url_semantics_unknown`;
- `readme_doi_type_unknown`;
- `dynamic_version_expression`;
- `software_reference_relation_not_in_schema`;
- `license_file_reference_requires_content_resolution`;
- `unsupported_structured_license_mapping`;
- `archived_as_requires_cross_module_identifier_match` when at least one valid
  normalized identifier requires later matching.

### 10.2 `skipped`

The input is intentionally excluded by a ratified rule.

Examples:

- `bot_contributor_excluded`;
- `cff_placeholder_excluded`;
- `noassertion_not_a_license`;
- `empty_structured_license_text`;
- `derived_view_not_reprocessed` (`files.downloaded`, `files.dockerfiles`);
- `administrative_field_not_nodalized`.

### 10.3 `unresolved`

A deterministic relation was expected but its target or valid semantics could not be resolved.

Examples:

- `self_vcs_reference_without_component`;
- `fork_parent_unavailable`;
- `invalid_hydroshare_resource_url`;
- `invalid_doi_candidate`;
- `repository_target_url_unparseable`.

### 10.4 `warnings`

Phase A `parse_warnings` are propagated with repository identity and internal lineage. They do not create KG nodes.

Every report record contains:

```jsonc
{
  "repoId": 807668057,
  "repoName": "deep_bucket_lab",
  "category": "deferred",
  "sourcePath": "CITATION.md",
  "value": null,
  "reason": "citation_md_deferred_to_llm"
}
```

---

## 11. Validation requirements

Phase B must validate before writing a successful output.

### 11.1 Structural validation

- every node ID is unique;
- every edge ID is unique;
- every edge source and target exists in `nodes`; cross-module entities appear as referenced stubs until alignment;
- every node and edge has `class/relation`, `inventoryId`, and non-empty public evidence;
- `curationStatus ∈ {curated, referenced}`;
- all arrays and set-like attributes are deterministically sorted.

### 11.2 Repository and file validation

- exactly one curated Repository node per Phase A repository;
- exactly one File node and one `hasFile` edge per `files.inventory` entry;
- no additional File nodes from `files.downloaded` or `files.dockerfiles`;
- File count per repository equals `files.total_count`;
- File `downloaded` count equals `files.downloaded_count`;
- every File public location contains `/blob/{sha}/` and the exact repository-relative path.

### 11.3 Dependency/environment validation

- one dependency mention per Phase A `dependencies[]` entry;
- no lockfile package explosion;
- external VCS targets resolve or become referenced repository stubs;
- no `Repository dependsOnRepository` self-loop;
- self VCS subpackages become internal Dependency mentions;
- every environment has a source file public URL;
- Dockerfile existence alone does not create an ExecutionEnvironment.

### 11.4 Agent/citation validation

- bots create no Person node;
- CFF placeholders create no CFF-derived Person, Tool, License, ModelVersion, or Paper node;
- preferred-citation authors attach to Paper, not Repository;
- source names are preserved without correcting swapped CFF given/family fields;
- exact DOI targets use normalized DOI keys;
- text-only citations are deferred, not guessed.
- structured software-license text is normalized semantically; Python mapping
  representations, empty declarations, and file pointers never create License
  nodes;
- each CFF affiliation edge retains lineage for its own software-author index;
- `archived_as_requires_cross_module_identifier_match` reports always contain a
  non-empty normalized identifier collection.
- archive candidates exclude repository DOI identifiers already typed as Paper
  or DatasetResource by structured citation context; those Identifier mentions
  remain in the graph.

### 11.5 Provenance validation

- no `evidence.sourceLocation` begins with a local path;
- no public `sourceLocation` uses `files_manifest.json`, `repo_metadata.json`, `contributors.json`, or `archive_info.json` as the source;
- internal raw field names occur only under `internalLineage` or report records;
- file-derived evidence is SHA-pinned;
- API-derived evidence records acquisition epoch as version.

### 11.6 Coverage accounting

Every Phase A field must be accounted for by the mapping disposition matrix as one of:

- node;
- edge;
- node/edge attribute;
- evidence;
- internal lineage;
- deferred;
- skipped;
- administrative-only.

No source field is silently ignored.

---

## 12. Acceptance criteria before full-corpus extraction

The implementation must first run on `github_phaseB_sample_repos.json` and demonstrate:

- schema `1.1.0` accepted;
- ten curated Repository nodes;
- File counts equal the sample inventory counts, including 3,129 SWEML files;
- `.github/actions/README.md` represented as `File(downloaded=false, fileRole=readme)` with a public SHA-pinned URL;
- external and monorepo VCS dependency cases handled without self-loops;
- valid CFF, CITATION.md, and placeholder CFF cases separated;
- bots excluded;
- all output validations pass;
- two runs are byte-identical.

Only after sample review should the extractor run across all 51 repositories.

---

## 13. Companion artifacts

- `github_preprocessing_phaseA.md` — raw → consolidated corpus contract.
- `github_extraction_mapping.md` — exhaustive Phase B field-to-ontology mapping.
- `ontology_inventory.md` — authoritative entity/relation inventory and stable IDs.
- `ontology_v0.1.md` / `ontology_formalization.md` — conceptual and OWL records.
- `hydroshare_extraction_mapping.md` — precedent for deterministic nodes/edges and evidence.

*End of Phase B execution contract.*
