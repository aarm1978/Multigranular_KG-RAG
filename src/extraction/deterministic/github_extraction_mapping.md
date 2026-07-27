# GitHub → Ontology — Deterministic Extraction Mapping

**Study 2 — Knowledge-graph construction, deterministic layer (Module 3: Code Repository / GitHub)**

**Purpose.** This document is the field-level contract between the GitHub Phase A consolidated corpus (`ciroh_github_corpus.json`, schema `1.1.0`) and the Study 2 ontology. For each structured field that Phase B processes deterministically, it specifies the ontology node or edge produced, stable inventory ID, identity rule, public evidence construction, and special guards. It is the implementation specification for `extract_github.py` and the manuscript-ready record of how the GitHub layer is populated.

**Scope.** Deterministic only. README/CITATION prose interpretation, source-code interpretation, fuzzy consolidation, and cross-artifact semantic inference are explicitly deferred.

---

## 1. Conventions

### 1.1 Source record

For the rules below, `repo` denotes one element of `repos[]` with:

```text
repo_id
full_name
html_url
archive.frozen_commit_sha
archive.downloaded_at_epoch
provenance.source_artifact
```

Required helper values:

```text
repo_node_id = github:repo:{repo_id}
snapshot_url = {html_url}/tree/{frozen_commit_sha}
metadata_api_url = https://api.github.com/repos/{full_name}
contributors_api_url = https://api.github.com/repos/{full_name}/contributors
```

### 1.2 Deterministic hash

`stable_hash(value)` means:

```text
lowercase hex SHA-256 of UTF-8 value, truncated to 20 characters
```

Hash inputs use `|` as a separator and preserve source case unless a rule explicitly calls for canonicalization.

### 1.3 Mention-level identity

Except for curated repositories and exact external artifact identifiers, Phase B emits source-scoped mentions. Each mention carries:

- `id`: unique source-scoped node ID;
- `canonicalKey`: best deterministic alignment key;
- `identityRegime`: how the key was produced;
- `curationStatus`: `curated` or `referenced`.

Phase B does not merge names across regimes.

### 1.4 Public evidence builders

#### Repository file

```text
blob_url(path) = {html_url}/blob/{frozen_commit_sha}/{encoded_path}
```

`encoded_path` percent-encodes path segments but preserves `/` and case.

#### Repository metadata

```text
sourceArtifact = html_url
sourceLocation = metadata_api_url
version = archive.downloaded_at_epoch
```

#### Contributors

```text
sourceArtifact = html_url
sourceLocation = contributors_api_url
version = archive.downloaded_at_epoch
```

#### Internal lineage

Local lineage is stored separately:

```json
{
  "phaseAField": "files.inventory[17]",
  "rawSource": "files_manifest.json:path/to/file",
  "phaseAVersion": "1.1.0"
}
```

Local raw filenames never become the primary public `sourceLocation`.

### 1.5 Canonicalizers

#### GitHub repository URL

Normalize recognized GitHub repository forms to:

```text
https://github.com/{owner}/{repo}
```

Rules:

- remove `git+` and terminal `.git`;
- convert `git@github.com:owner/repo`;
- strip query and fragment;
- preserve original URL as an attribute;
- compare `owner/repo` case-insensitively;
- do not treat badges, `raw.githubusercontent.com`, user attachments, issue URLs, action URLs, or arbitrary blobs as repository roots.

#### Package name

Use `packaging.utils.canonicalize_name()` for PyPI-compatible names. Conda names are lower-cased and normalized mechanically without changing the original `name`/`raw` values.

#### DOI

Normalize by:

- removing `doi:` and `https://doi.org/` prefixes;
- URL-decoding;
- trimming surrounding whitespace and terminal citation punctuation;
- lower-casing the comparison key;
- validating `10.<4–9 digits>/<suffix>`;
- rejecting badge/image suffixes such as `.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` and candidates embedded in shields/badge URLs.

DOI type comes from structured context, not from string shape alone.

#### HydroShare URL

Accept URLs containing:

```text
hydroshare.org/resource/{32-character-resource-id}
```

Extract the resource ID and preserve the original URL.

---

## 2. Node rules

### N1 — Curated Repository

| Item | Rule |
|---|---|
| Phase A source | repository record root |
| Class | `Repository` |
| Inventory ID | A-C01 |
| ID | `github:repo:{repo_id}` |
| canonicalKey | `github-repo-id:{repo_id}` |
| identityRegime | `github_numeric_id` |
| curationStatus | `curated` |

Attributes:

```text
repoId, name, fullName, htmlUrl, description, homepage,
defaultBranch, language, topics, fork, archived, disabled, visibility,
createdAt, updatedAt, pushedAt, githubStats,
fileTotalCount, downloadedFileCount, selectionReasonHistogram,
hasDockerfile
```

Administrative fields (`githubStats`, timestamps, counts, archive metadata) are retained but marked `metricExclusion: administrative` for information-density computation.

Evidence:

```text
evidenceText = full_name
sourceLocation = metadata_api_url
sourceArtifact = html_url
version = archive.downloaded_at_epoch
```

`fork=true` is an attribute. It does not by itself create `forkedFrom` without a parent target.

---

### N2 — Repository Identifier mention

| Item | Rule |
|---|---|
| Phase A source | `identifiers[i]` |
| Class | `Identifier` |
| Inventory ID | A-ID01 |
| ID | `github:identifier:{repo_id}:{stable_hash(id_type|value|source_path)}` |
| canonicalKey | `{normalized id_type}:{normalized value}` |
| identityRegime | `exact_identifier` |
| curationStatus | `curated` |

Attributes:

```text
idType, value, normalizedValue
```

Public evidence:

- `repo_url` → `sourceLocation = normalized repository URL`, version = acquisition epoch;
- `commit_sha` → `sourceLocation = snapshot_url`, version = SHA;
- CFF top-level DOI → CFF blob URL, version = SHA.

Internal `source_path` determines which public builder applies but is not copied as public provenance.

---

### N3 — File

| Item | Rule |
|---|---|
| Phase A source | every `files.inventory[i]` |
| Class | `File` |
| Inventory ID | A-C02 |
| ID | `github:file:{repo_id}:{stable_hash(path)}` |
| canonicalKey | `github-file:{repo_id}:{path}` |
| identityRegime | `repository_relative_path` |
| curationStatus | `curated` |

Attributes:

```text
path, fileName, extension, sizeBytes,
downloaded, contentAvailable (= downloaded),
selectionReason, fileRole
```

Evidence:

```text
evidenceText = path
sourceLocation = blob_url(path)
sourceArtifact = snapshot_url
version = frozen_commit_sha
```

Rules:

- create File nodes for downloaded and non-downloaded entries;
- never read or interpret content when `downloaded=false`;
- do not create additional nodes from `files.downloaded` or `files.dockerfiles`;
- a Dockerfile with no downloaded content remains only a File node.

---

### N4 — Package Dependency mention

| Item | Rule |
|---|---|
| Phase A source | `dependencies[i]` |
| Class | `Dependency` |
| Inventory ID | A-C03 |
| ID | `github:dependency:{repo_id}:{stable_hash(ecosystem|canonical_name)}` |
| canonicalKey | `package:{ecosystem}:{canonical_name}` |
| identityRegime | `ecosystem_package_name` |
| curationStatus | `curated` |

Node attributes:

```text
name, canonicalName, ecosystem, isVcs=false
```

Constraint-specific values belong primarily on the `dependsOn` edge:

```text
raw, versionSpec, extras, marker, depGroup, sourceDeclarations
```

Evidence uses the deterministic primary source from `sources[]`:

```text
evidenceText = primary.raw_line if present else raw
sourceLocation = blob_url(primary.manifest_path)
version = frozen_commit_sha
```

Lockfile-resolved packages are not emitted here because Phase A does not place them in `dependencies[]`.

---

### N5 — Internal VCS package Dependency mention

Created only when a `repo_dependencies[i]` target canonicalizes to the source repository itself and identifies an internal component through `subdirectory` and/or `egg`.

| Item | Rule |
|---|---|
| Class | `Dependency` |
| Inventory ID | A-C03 |
| ID | `github:dependency:{repo_id}:{stable_hash(internal-vcs|name|subdirectory|egg)}` |
| canonicalKey | `internal-vcs:{repo_id}:{normalized component key}` |
| identityRegime | `internal_vcs_subpackage` |
| curationStatus | `curated` |

Attributes:

```text
name, dependencyKind="internal_vcs_package",
ref, subdirectory, egg, ecosystem, depGroup, raw, sourceDeclarations
```

This rule prevents a misleading repository self-loop.

---

### N6 — ExecutionEnvironment

| Item | Rule |
|---|---|
| Phase A source | `execution_environment[i]` |
| Class | `ExecutionEnvironment` |
| Inventory ID | A-C04 |
| ID | `github:env:{repo_id}:{stable_hash(kind|source_path)}` |
| canonicalKey | `github-env:{repo_id}:{kind}:{source_path}` |
| identityRegime | `repository_manifest_path` |
| curationStatus | `curated` |

Attributes:

```text
kind, name, channels, pythonVersion, prefix,
isLock, pinnedCount, pinnedSetEvidence, sourcePath
```

`pinnedSetEvidence` is retained as structured/raw evidence but marked for metric exclusion because it is a large resolved-set payload.

Evidence:

```text
evidenceText = concise environment descriptor
sourceLocation = blob_url(source_path)
version = frozen_commit_sha
```

Examples of descriptor:

```text
conda_env: deep_bucket_env; python=3.9
requirements_lock: 123 pinned packages
python_constraint: >=3.10
```

Dockerfile existence does not create this node without downloaded/parsed content.

---

### N7 — GitHub contributor Person mention

| Item | Rule |
|---|---|
| Phase A source | `contributors[i]` where `is_bot=false` |
| Class | `Person` |
| Inventory ID | A-AG01 |
| ID | `github:person:{repo_id}:{stable_hash(github|source_path|github_id|login)}` |
| canonicalKey | `github-user-id:{github_id}` if present, else `github-login:{login.casefold()}` |
| identityRegime | `github_login` |
| curationStatus | `curated` |

Attributes:

```text
githubId, login, profileUrl, contributions, contributorType, moduleRoleId="A-C05"
```

Evidence:

```text
evidenceText = "{login} ({contributions} contributions)"
sourceLocation = contributors_api_url
sourceArtifact = html_url
version = archive.downloaded_at_epoch
```

Bots produce no Person node and are recorded in `skipped`.

---

### N8 — CFF software-author Person mention

| Item | Rule |
|---|---|
| Phase A source | valid non-placeholder `citation.software_authors[i]` |
| Class | `Person` |
| Inventory ID | A-AG01 |
| ID | `github:person:{repo_id}:{stable_hash(cff-software-author|citation.source_path|i)}` |
| canonicalKey | ORCID if present; else email; else normalized verbatim name |
| identityRegime | `cff_orcid`, `cff_email`, or `cff_name` |
| curationStatus | `curated` |

Attributes:

```text
familyNames, givenNames, displayName, orcid, affiliation, email,
role="softwareAuthor", moduleRoleId="A-C05"
```

Names are copied as provided. Swapped source fields are not corrected.

Evidence:

```text
evidenceText = structured author descriptor
sourceLocation = blob_url(citation.source_path)
version = frozen_commit_sha
```

---

### N9 — Package-metadata author Person mention

| Item | Rule |
|---|---|
| Phase A source | `software_metadata[j].authors[i]` |
| Class | `Person` |
| Inventory ID | A-AG01 |
| ID | `github:person:{repo_id}:{stable_hash(package-author|source_path|i)}` |
| canonicalKey | normalized email if present, else normalized verbatim name |
| identityRegime | `name_email` or `name_only_source_scoped` |
| curationStatus | `curated` |

Attributes:

```text
name, email, role="packageAuthor", softwareName, manifestType,
moduleRoleId="A-C05"
```

Do not reparse names containing an embedded email if Phase A did not separate it.

Evidence uses the package manifest blob URL.

---

### N10 — Paper-author Person mention

Created from a valid DOI-bearing CFF preferred citation or DOI-bearing article-like CFF reference.

| Item | Rule |
|---|---|
| Class | `Person` |
| Inventory ID | A-AG01 |
| ID | `github:paper-author:{stable_hash(paper-node-id|source-index)}` |
| canonicalKey | ORCID if present, else normalized verbatim name scoped to the citation |
| identityRegime | `citation_orcid` or `citation_name` |
| curationStatus | `referenced` unless resolved to an existing curated paper-author mention later |

Attributes include `moduleRoleId="A-P03"`. These people attach to the Paper, never to the Repository merely because they appear in `preferred_citation` or `references`.

---

### N11 — Organization mention

Created when a CFF software author has a non-empty `affiliation`.

| Item | Rule |
|---|---|
| Class | `Organization` |
| Inventory ID | A-AG02 |
| ID | `github:organization:{repo_id}:{stable_hash(citation.source_path|affiliation)}` |
| canonicalKey | normalized verbatim organization name |
| identityRegime | `organization_name` |
| curationStatus | `curated` |

No ROR is invented. Later alignment may resolve the name to a canonical organization.

---

### N12 — License declaration

Created from one of:

- `repo.license` when non-null and not merely `NOASSERTION`;
- valid non-placeholder `citation.license`;
- a semantic text declaration in `software_metadata[i].license`.

Software-metadata licenses may be plain strings or structured mappings. A
non-empty plain string and a mapping with non-empty `text` normalize to the same
semantic declaration. Empty `text` is skipped as
`empty_structured_license_text`. A non-empty `file` is deferred as
`license_file_reference_requires_content_resolution`; it identifies where terms
may be read, not the license identity. Unsupported mappings are deferred for
audit and are never converted to Python dictionary strings.

| Item | Rule |
|---|---|
| Class | `License` |
| Inventory ID | A-C06 |
| ID | `github:license:{repo_id}:{stable_hash(scope|normalized declaration|source path)}` |
| canonicalKey | `spdx:{spdx_id}` when valid, else normalized declaration |
| identityRegime | `spdx` or `custom_license_declaration` |
| curationStatus | `curated` |

Attributes:

```text
name, key, spdxId, url, isSpdx,
declaration, declarationScope, declarationKind, sourceType,
originalValue, sourceDeclarations
```

Scopes:

```text
repository_metadata
cff_software
software_metadata:{software name}
```

`NOASSERTION` is retained as a Repository administrative attribute but does not mint a License node. Placeholder CFF licenses are ignored with the placeholder block.

---

### N13 — Tool mention from structured software metadata

Structured package/CFF declarations are treated as deterministic Tool seeds; prose-derived Tool mentions remain LLM work. This is a mapping-level hybrid refinement based on explicit software metadata, not a change to the Tool class semantics.

Created from:

- every `software_metadata[i]` with non-empty `name`;
- valid non-placeholder CFF with non-empty `title` when `type` is null or explicitly software-like. An explicitly non-software top-level type (for example `dataset` or `article`) is not forced into `Tool`.

| Item | Rule |
|---|---|
| Class | `Tool` |
| Inventory ID | A-DOM02 |
| ID | `github:tool:{repo_id}:{stable_hash(source_path|canonical_name)}` |
| canonicalKey | normalized software/package name |
| identityRegime | `structured_software_declaration` |
| curationStatus | `curated` |

Attributes may include:

```text
name, title, type, abstract, manifestType, sourcePath,
urls, keywords, cffVersion, dateReleased,
versionExpression, declaredLicense
```

Rules:

- exact duplicate records from the same source path/name collapse within Phase B;
- differently named CFF/package declarations remain separate mentions;
- no fuzzy name matching is performed;
- CFF keywords remain Tool attributes because the frozen code-module schema does not declare a Repository/Tool `hasSubject` edge.

---

### N14 — ModelVersion mention

Created from:

- valid non-placeholder `citation.version` when concrete **and the CFF record is in software context under N13**;
- `software_metadata[i].version` when concrete.

| Item | Rule |
|---|---|
| Class | `ModelVersion` |
| Inventory ID | A-C10 |
| ID | `github:version:{repo_id}:{stable_hash(source_path|software_name|version)}` |
| canonicalKey | `software-version:{normalized software name}:{version}` |
| identityRegime | `structured_version_literal` |
| curationStatus | `curated` |

Attributes:

```text
version, softwareName, dateReleased, sourceType, sourcePath
```

A version is not concrete when it is empty, starts with `attr:`, contains an unresolved template/expression, or is otherwise a code reference. Such values remain Tool attributes as `versionExpression` and are recorded in `deferred`.

---

### N15 — Paper stub

Created when structured citation context identifies a paper and provides a valid DOI.

| Item | Rule |
|---|---|
| Class | `Paper` |
| Inventory ID | A-P01 |
| ID | `github:paper-ref:{repo_id}:{stable_hash(citation.source_path|citation role|index|normalized_doi)}` |
| canonicalKey | `doi:{normalized_doi}` |
| identityRegime | `doi` |
| curationStatus | `referenced` |

Attributes:

```text
title, type, journal, year, volume, number,
startPage, endPage, publisher, url, doi
```

Create an Identifier DOI mention and `hasIdentifier` edge for the Paper.

Text-only preferred citations/references are deferred; no title-based Paper ID is invented.

---

### N16 — DatasetResource target/stub

Created from:

- a valid HydroShare README URL;
- a DOI/URL in structured CFF context explicitly typed as dataset.

Identity key priority:

1. exact HydroShare resource ID;
2. exact dataset DOI;
3. otherwise no node — defer/unresolved.

The node ID is source-scoped:

```text
github:dataset-ref:{repo_id}:{stable_hash(source path|canonical target key)}
```

`canonicalKey` is `hydroshare:{resource_id}` or `doi:{normalized_doi}`. `curationStatus` is `referenced`. The later alignment stage resolves it to a curated DatasetResource by exact identifier. Attributes retain the original URL/DOI and target type.

---

### N17 — Referenced Repository target/stub

Created from an external `repo_dependencies[i].vcs_url` or a structured software `repository`/`repository-code` field that resolves to a GitHub repository root. Resolution to a curated node is limited to repositories present in the same GitHub corpus; otherwise Phase B emits a source-scoped referenced stub.

| Item | Rule |
|---|---|
| Class | `Repository` |
| Inventory ID | A-C01 |
| ID if target is in this GitHub corpus | existing `github:repo:{repo_id}` |
| ID if external | `github:repo-ref:{source_repo_id}:{stable_hash(normalized target URL)}` |
| canonicalKey | normalized GitHub repository URL |
| identityRegime | `github_repository_url` |
| curationStatus | `curated` for an in-corpus target; otherwise `referenced` |

Referenced stubs contain:

```text
fullName, htmlUrl, owner, name
```

and an Identifier URL mention. No API call is made to enrich them.

---

## 3. Edge rules

### E1 — `hasIdentifier`

| Item | Rule |
|---|---|
| Relation | `hasIdentifier` |
| Inventory ID | C-C06 for Repository; C-P04 for Paper; module-appropriate relation for DatasetResource |
| Source | Repository/Paper/DatasetResource |
| Target | Identifier |

Evidence matches the identifier node evidence.

For the curated Repository, emit one edge for each `identifiers[]` entry.

---

### E2 — `hasFile`

| Item | Rule |
|---|---|
| Phase A source | `files.inventory[i]` |
| Relation | `hasFile` |
| Inventory ID | C-C01 |
| Source | curated Repository |
| Target | File |

Create exactly one edge per inventory entry. Evidence is the file path and SHA-pinned blob URL.

---

### E3 — `dependsOn`

| Item | Rule |
|---|---|
| Phase A source | `dependencies[i]` or internal VCS package rule |
| Relation | `dependsOn` |
| Inventory ID | C-C02 |
| Source | curated Repository |
| Target | Dependency mention |

Edge attributes:

```text
raw, versionSpec, extras, marker, depGroup,
ecosystem, manifestScopes, sourceDeclarations,
dependencyKind
```

Evidence comes from the deterministic primary source. Phase A may have several source declarations; all are retained in `sourceDeclarations`.

---

### E4 — `hasExecutionEnvironment`

| Item | Rule |
|---|---|
| Phase A source | `execution_environment[i]` |
| Relation | `hasExecutionEnvironment` |
| Inventory ID | C-C03 |
| Source | curated Repository |
| Target | ExecutionEnvironment |

Evidence is the source manifest/lockfile blob URL.

---

### E5 — `hasContributor`

| Item | Rule |
|---|---|
| Relation | `hasContributor` |
| Inventory ID | C-C04 |
| Source | curated Repository |
| Target | GitHub contributor, CFF software author, or package author Person mention |

Edge attributes:

```text
role = contributor | softwareAuthor | packageAuthor
contributions (GitHub only)
softwareName / toolId (when applicable)
```

Preferred-citation and reference authors do not use this edge.

---

### E6 — `affiliatedWith`

| Item | Rule |
|---|---|
| Phase A source | CFF software author `affiliation` |
| Relation | `affiliatedWith` |
| Inventory ID | A-AG-R1 |
| Source | CFF software-author Person mention |
| Target | Organization mention |

Evidence is the CFF file with the affiliation string. Each edge preserves the
specific author's source index in `internalLineage.phaseAField`; shared
Organization-node evidence must not replace per-author edge lineage.

---

### E7 — `hasLicense`

| Item | Rule |
|---|---|
| Relation | `hasLicense` |
| Inventory ID | C-C05 |
| Source | curated Repository |
| Target | License declaration |

Edge attributes:

```text
declarationScope, sourceType, softwareName, isPrimary
```

`repo.license` is primary repository metadata. CFF/package declarations are additional scoped declarations and never overwrite the primary declaration. Conflicting declarations are retained with separate provenance and reported in `warnings`.

---

### E8 — `implementedBy`

| Item | Rule |
|---|---|
| Phase A source | structured CFF/package software declaration |
| Relation | `implementedBy` |
| Inventory ID | D-22 |
| Source | Tool mention |
| Target | curated source Repository or exact structured external repository target |

Default: every Tool created from a manifest inside the curated repository is implemented by the curated repository.

For CFF `repository-code`/`repository` or package URL keys semantically equivalent to source/repository/code:

- same normalized repository → same curated target;
- different GitHub root → referenced/curated external target;
- generic homepage/documentation/tracker URLs do not change the implementation target.

Evidence is the structured manifest field, not README URL presence.

---

### E9 — `hasModelVersion`

| Item | Rule |
|---|---|
| Phase A source | concrete CFF/package version |
| Relation | `hasModelVersion` |
| Inventory ID | C-C09 |
| Source | curated Repository |
| Target | ModelVersion mention |

Edge attributes identify the corresponding `toolId`/`softwareName` where available. This preserves multiple component versions in a monorepo without changing the frozen ontology domain.

---

### E10 — `dependsOnRepository`

| Item | Rule |
|---|---|
| Phase A source | external `repo_dependencies[i]` |
| Relation | `dependsOnRepository` |
| Inventory ID | C-C13 / D-13 |
| Source | curated Repository |
| Target | curated or referenced Repository |

Edge attributes:

```text
name, raw, ref, subdirectory, egg,
depGroup, ecosystem, sourceDeclarations
```

Rules:

- canonicalize VCS target URL;
- resolve against the complete curated repository index before creating a stub;
- do not create a self-loop;
- self-target with component metadata uses N5/E3;
- self-target with no component evidence is `unresolved`.

README GitHub URLs do not independently create this relation.

---

### E11 — `referencePublication`

| Item | Rule |
|---|---|
| Phase A source | DOI-bearing `citation.preferred_citation` |
| Relation | `referencePublication` |
| Inventory ID | C-C17 / D-07 |
| Source | curated Repository |
| Target | Paper stub/curated Paper |

Evidence is the preferred-citation descriptor in `CITATION.cff`.

This is the citation recommended for the software, not merely any cited paper.

---

### E12 — `citesPaper`

| Item | Rule |
|---|---|
| Phase A source | DOI-bearing article-like `citation.references[i]` |
| Relation | `citesPaper` |
| Inventory ID | C-C17 / D-07 |
| Source | curated Repository |
| Target | Paper stub/curated Paper |

Article-like types include explicit CFF types such as article, conference-paper, proceedings, thesis, report, or other publication types accepted by the implementation's controlled mapping. Unknown types are deferred rather than guessed.

---

### E13 — `hasAuthor`

| Item | Rule |
|---|---|
| Phase A source | authors in preferred citation/article-like reference |
| Relation | `hasAuthor` |
| Inventory ID | C-P01 |
| Source | Paper |
| Target | Paper-author Person mention |

Evidence is the same CFF citation locus.

---

### E14 — `referencesDataset`

| Item | Rule |
|---|---|
| Phase A source | valid `readme.deterministic_urls.hydroshare[]`; explicitly dataset-typed CFF reference |
| Relation | `referencesDataset` |
| Inventory ID | D-05 |
| Source | curated Repository |
| Target | DatasetResource target/stub |

For README URLs, evidence is the exact URL and README blob location.

A bare HydroShare URL supports `referencesDataset`, not automatically `usesDataset`. `usesDataset` is deferred to the LLM layer unless structured context explicitly expresses use.

---

### E15 — `forkedFrom`

| Item | Rule |
|---|---|
| Phase A source | `fork=true` plus non-null exact `fork_parent` |
| Relation | `forkedFrom` |
| Inventory ID | C-C14 / D-14 |

Current Phase A records normally have `fork_parent=null`; therefore no deterministic edge is created. Preserve `fork=true` on Repository and emit `unresolved: fork_parent_unavailable`.

README/badge inference is deferred.

---

### E16 — `archivedAs` / `sameSoftwareAs`

| Item | Rule |
|---|---|
| Relation | `archivedAs` / `sameSoftwareAs` |
| Inventory ID | C-C18 / D-20 |

Do not create this edge from title similarity or an isolated README DOI.

It may be created only during cross-module exact-identifier resolution when:

1. a DOI is deterministically typed as a software/archive identifier;
2. the DOI identifier is linked to a referenced software/repository stub;
3. an exact identifier rule links that stub to the curated Repository.

Standalone GitHub Phase B records a candidate as `deferred: archived_as_requires_cross_module_identifier_match`
only when at least one valid normalized candidate identifier exists. Archived
status alone creates neither an edge nor a deferred cross-module match.

A DOI already deterministically typed as a Paper or DatasetResource is excluded
from `archivedAs` candidate resolution. Repository-level DOI identifiers are
preserved as Identifier mentions, but identifier presence alone does not
establish an archived software relationship. Candidate calculation inspects all
structured citation contexts before subtracting Paper- and DatasetResource-typed
DOIs, so the result does not depend on extraction order.

---

## 4. Structured citation rules

### 4.1 Placeholder guard

When:

```text
citation.present=true
citation.format="cff"
citation.placeholder=true
```

Phase B creates no CFF-derived:

- Tool;
- Person;
- Organization;
- License;
- ModelVersion;
- Paper;
- citation edge.

The `CITATION.cff` File node still exists. Record `cff_placeholder_excluded`.

### 4.2 Valid CFF top-level fields

| CFF field | Deterministic disposition |
|---|---|
| `title` | Tool attribute / Tool seed |
| `type` | Tool attribute; does not override ontology class without a controlled rule |
| `software_authors[]` | Person mentions + Repository `hasContributor` |
| `doi` | already represented in repo `identifiers[]`; no duplicate DOI node |
| `version` | ModelVersion if concrete |
| `date_released` | ModelVersion/Tool attribute |
| `url` | Tool homepage attribute |
| `repository_code`, `repository` | exact Tool `implementedBy` target when GitHub root resolvable |
| `keywords[]` | Tool attributes |
| `license` | scoped License declaration |
| `abstract` | Tool attribute and candidate LLM text |
| `cff_version` | Tool administrative attribute |

### 4.3 Preferred citation

- valid DOI + publication semantics → Paper + `referencePublication`;
- its authors → Paper `hasAuthor`;
- text-only citation → deferred;
- source names remain verbatim.

### 4.4 References

- explicit publication type + DOI → Paper + `citesPaper`;
- explicit dataset type + HydroShare ID/DOI → DatasetResource + `referencesDataset`;
- explicit software type + DOI/URL → typed candidate retained for later cross-module relation resolution; no generic Repository→Tool reference edge is invented;
- unknown type or untyped DOI → deferred.

---

## 5. Software metadata rules

For each `software_metadata[i]`:

1. create a Tool mention when `name` is non-empty;
2. create `implementedBy` Tool→source Repository;
3. create package-author Person mentions and Repository `hasContributor` edges;
4. create ModelVersion only for concrete literals;
5. create scoped License declaration when non-empty and meaningful;
6. preserve URL map as Tool attributes;
7. use semantically explicit repository/source/code URL keys for additional implementation targets;
8. treat documentation, tracker, issues, and generic homepage URLs as attributes only;
9. never infer identity by fuzzy package/repository name similarity.

Dynamic version examples such as:

```text
attr: datastreamcli._version.__version__
```

are preserved as `versionExpression` and deferred.

---

## 6. README URL rules

Phase A mechanically extracts URL candidates. Phase B applies conservative typing.

### 6.1 HydroShare URLs

A valid HydroShare resource URL creates N16/E14 (`referencesDataset`).

### 6.2 GitHub URLs

Classify each URL as:

- same-repository root;
- same-repository blob/tree/file;
- external repository root;
- issue/pull/action/workflow/badge;
- user attachment/raw asset;
- unrecognized GitHub URL.

Deterministic disposition:

- same-repository links → no edge; preserve in deferred/diagnostic counts if needed;
- external root repository URL → no generic edge because the frozen ontology does not define `Repository → referencesRepository`;
- if the same target is already supported by `repo_dependencies[]`, the manifest-derived `dependsOnRepository` remains authoritative;
- issue/action/badge/blob/tree URLs → no Repository relation;
- semantic meaning of external GitHub README links → deferred to LLM.

### 6.3 DOI candidates

- normalize and validate;
- reject badge/image false positives;
- if exact match to a structured CFF DOI, do not duplicate;
- otherwise preserve as a deferred candidate because README string shape alone does not type Paper/Dataset/Software.

### 6.4 Other URLs

No node or edge unless a separately defined exact resolver supports the host/type. Retain only in Phase A or deferred report.

---

## 7. Repository dependency special cases

### 7.1 External target

```text
canonical(vcs_url) != canonical(source html_url)
```

Create/resolve target Repository and emit `dependsOnRepository`.

### 7.2 Monorepo internal component

```text
canonical(vcs_url) == canonical(source html_url)
AND (subdirectory or egg or component name is present)
```

Create internal Dependency mention and `dependsOn`. Do not create a Repository self-loop.

### 7.3 Uninformative self-reference

```text
canonical(vcs_url) == canonical(source html_url)
AND no component discriminator exists
```

Emit no edge and record `self_vcs_reference_without_component`.

---

## 8. License precedence and conflicts

No source silently overwrites another.

Priority for identifying the repository-level primary declaration:

1. GitHub `repo.license` with valid SPDX or meaningful custom declaration;
2. CFF license;
3. software metadata license.

All meaningful declarations may be represented as separate License mentions with scoped `hasLicense` edges.

Conflict rule (over normalized semantic declarations only):

```text
if two normalized non-empty declarations differ:
    retain both
    mark primary according to priority
    emit warning license_declaration_conflict
```

`NOASSERTION` is not a License entity. File-based license references such as
`{"file":"LICENSE"}` are deferred for content resolution and do not create a
License or participate in conflict comparison. Their path is preserved in the
report. Empty or unsupported structured declarations likewise create no License;
the original value remains available in the deterministic report record.

---

## 9. Field-disposition matrix

### 9.1 Repository core

| Phase A field | Disposition |
|---|---|
| `repo_id` | Repository identity + attribute |
| `name`, `full_name`, `html_url` | Repository attributes/evidence/aliases |
| `description`, `homepage` | Repository attributes |
| `default_branch`, `language`, `topics` | Repository attributes |
| `fork` | Repository attribute; possible unresolved fork parent |
| `fork_parent` | `forkedFrom` only when exact non-null target exists |
| `archived`, `disabled`, `visibility` | Repository attributes |
| `timestamps.*` | administrative Repository attributes; API provenance |
| `github_stats.*` | administrative Repository attributes; metric-excluded |
| `archive.frozen_commit_sha` | Identifier + evidence version/public snapshot builder |
| `archive.downloaded_at_epoch` | API snapshot version/internal lineage |
| `archive.archive_format` | internal/administrative attribute |
| `license` | License + `hasLicense` or skip NOASSERTION/null |
| `identifiers[]` | Identifier + `hasIdentifier` |

### 9.2 Contributors and files

| Phase A field | Disposition |
|---|---|
| `contributors[]` human | Person + `hasContributor` |
| `contributors[]` bot | skipped with reason |
| `files.total_count` | Repository methodological/admin attribute + validation |
| `files.downloaded_count` | Repository methodological/admin attribute + validation |
| `files.selection_reason_histogram` | Repository methodological attribute; metric-excluded |
| `files.has_dockerfile` | Repository attribute + validation |
| `files.inventory[]` | File + `hasFile` for every entry |
| `files.downloaded[]` | derived compatibility view; validation only |
| `files.dockerfiles[]` | derived convenience view; validation only |

### 9.3 Dependencies and environments

| Phase A field | Disposition |
|---|---|
| `dependencies[]` | Dependency + `dependsOn` |
| `dependencies[].sources[]` | primary evidence + edge `sourceDeclarations` |
| `repo_dependencies[]` external | Repository target/stub + `dependsOnRepository` |
| `repo_dependencies[]` self component | internal Dependency + `dependsOn` |
| `execution_environment[]` | ExecutionEnvironment + `hasExecutionEnvironment` |
| `pinned_set_evidence` | environment attribute; no dependency explosion |

### 9.4 Citation

| Phase A field | Disposition |
|---|---|
| `citation.present`, `format`, `placeholder` | gating/admin attributes/report |
| `citation.source_path` | internal lineage → public CFF blob builder |
| `citation.cff_version` | Tool administrative attribute |
| `citation.type`, `title`, `abstract` | structured Tool attributes/seed when valid |
| `citation.software_authors[]` | Person + Repository `hasContributor` |
| `citation.doi` | already in `identifiers[]`; no duplicate |
| `citation.version`, `date_released` | ModelVersion/Tool attributes when concrete and software-scoped; otherwise deferred |
| `citation.url` | Tool homepage attribute |
| `citation.repository_code`, `repository` | Tool `implementedBy` when exact GitHub root |
| `citation.keywords[]` | Tool attributes |
| `citation.license` | scoped License + `hasLicense` |
| `citation.preferred_citation` DOI-bearing | Paper + `referencePublication` + authors |
| `citation.references[]` | type-gated Paper/Dataset mapping; otherwise deferred |
| `citation_md` | deferred to LLM; no deterministic semantic nodes |

### 9.5 Software metadata and README

| Phase A field | Disposition |
|---|---|
| `software_metadata[]` | Tool seed + `implementedBy`; authors/licenses/versions by rules |
| `software_metadata[].license` | normalized text License + `hasLicense`; file pointer deferred; empty text skipped; unsupported mapping deferred |
| `software_metadata[].urls` | Tool attributes; explicit repository/source keys may resolve implementation target |
| `readme.present`, `source_path` | gating/internal lineage |
| `readme.text` | retained in Phase A for LLM; not copied into deterministic graph by default |
| `readme.deterministic_urls.hydroshare[]` | DatasetResource + `referencesDataset` |
| `readme.deterministic_urls.github[]` | classified; generally deferred/no edge |
| `readme.deterministic_urls.dois[]` | normalize; structured-match or deferred |
| `readme.deterministic_urls.other[]` | no deterministic graph mapping |

### 9.6 Provenance

| Phase A field | Disposition |
|---|---|
| `provenance.source_artifact` | public snapshot root / EvidenceSpan sourceArtifact |
| `provenance.phase_a_version` | internalLineage |
| `provenance.manifest_classifications` | internal extraction lineage/stats; no KG node |
| `provenance.parse_warnings[]` | propagated to output warnings |

---

## 10. Deferred to the LLM extractor

The deterministic mapping must not mint the following from README/CITATION prose alone:

- `RepositoryPurpose` and `hasPurpose`;
- `Function`, `Algorithm`, `describesFunction`, `describesAlgorithm`;
- `Workflow`, `explainsWorkflow`, `documentsUsage`;
- prose-derived `Tool`/`ComputationalModel` mentions;
- `usesTool`, `mentionsModel`;
- `Variable`, `Parameter`, `EvaluationMetric`, `Concept`;
- `mentionsVariable`, `usesParameter`, `reportsMetric`, `evaluates`;
- `implementsMethod`;
- `usesDataset` based only on URL presence;
- fork-parent inference;
- CITATION.md citation parsing;
- source-code functions, imports, AST, or runtime behavior.

The LLM layer reads prose from Phase A, not from local raw files.

---

## 11. Output examples

### 11.1 Non-downloaded README File

```jsonc
{
  "id": "github:file:<sweml_repo_id>:<hash>",
  "class": "File",
  "inventoryId": "A-C02",
  "attributes": {
    "path": ".github/actions/README.md",
    "fileName": "README.md",
    "extension": ".md",
    "sizeBytes": 3070,
    "downloaded": false,
    "contentAvailable": false,
    "selectionReason": null,
    "fileRole": "readme"
  },
  "canonicalKey": "github-file:<sweml_repo_id>:.github/actions/README.md",
  "identityRegime": "repository_relative_path",
  "curationStatus": "curated",
  "evidence": {
    "evidenceText": ".github/actions/README.md",
    "sourceLocation": "https://github.com/CIROH-UA/SWEML/blob/<sha>/.github/actions/README.md",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/SWEML/tree/<sha>",
    "version": "<sha>"
  },
  "internalLineage": {
    "phaseAField": "files.inventory[path=.github/actions/README.md]",
    "rawSource": "files_manifest.json:.github/actions/README.md",
    "phaseAVersion": "1.1.0"
  }
}
```

### 11.2 External VCS dependency

```jsonc
{
  "relation": "dependsOnRepository",
  "inventoryId": "C-C13",
  "source": "github:repo:<source_repo_id>",
  "target": "github:repo-ref:<source_repo_id>:<hash>",
  "attributes": {
    "name": "hypy",
    "ref": "master",
    "subdirectory": "python",
    "egg": "hypy",
    "depGroup": "runtime"
  },
  "evidence": {
    "evidenceText": "git+https://github.com/noaa-owp/hypy@master#egg=hypy&subdirectory=python",
    "sourceLocation": "https://github.com/CIROH-UA/ngen-cal/blob/<sha>/requirements.txt",
    "extractionMethod": "deterministic",
    "sourceArtifact": "https://github.com/CIROH-UA/ngen-cal/tree/<sha>",
    "version": "<sha>"
  }
}
```

### 11.3 Monorepo self-reference

```jsonc
{
  "class": "Dependency",
  "inventoryId": "A-C03",
  "attributes": {
    "name": "ngen_config",
    "dependencyKind": "internal_vcs_package",
    "subdirectory": "python/ngen_conf",
    "egg": "ngen_config"
  }
}
```

The source Repository connects to this node with `dependsOn`; no self `dependsOnRepository` edge is emitted.

---

## 12. Validation checks specific to this mapping

- every Phase A repository produces exactly one curated Repository;
- every `files.inventory` record produces exactly one File and one `hasFile`;
- the full-corpus File total must be 11,702 for the frozen CIROH corpus;
- `downloaded=false` files still have valid SHA-pinned public URLs;
- no duplicate File IDs within a repository;
- no nodes are created from derived file views;
- bots and placeholder CFF records produce explicit skip records;
- no Repository self-loop exists for `dependsOnRepository`;
- every external VCS target resolves or becomes a referenced stub;
- every CFF Paper has a valid DOI;
- every Paper author is attached to its Paper rather than the source Repository;
- software License values contain normalized semantic declarations, never Python
  mapping representations, empty text, or unresolved file pointers;
- semantically equivalent plain and structured software-license text does not
  create conflicting duplicate declarations in one scope;
- every CFF `affiliatedWith` edge retains lineage for its own software-author
  index, even when several authors share one Organization;
- every `archived_as_requires_cross_module_identifier_match` report contains at
  least one valid normalized candidate identifier;
- no archived-match candidate is also typed as a Paper or DatasetResource by the
  same repository's structured preferred citation or reference fields;
- every HydroShare reference has a valid resource ID or explicit unresolved record;
- README GitHub URLs do not create an undeclared generic relation;
- all evidence is public-facing; internal raw paths remain internal lineage only;
- all fields in §9 are accounted for;
- output is byte-stable across two runs.

---

## 13. Implementation boundary for `extract_github.py`

The implementation should be organized around reusable, domain-general functions rather than repository names:

```text
normalize_github_repo_url
classify_github_url
normalize_doi
extract_hydroshare_resource_id
canonicalize_package_name
build_blob_url
build_api_url
make_stable_id
select_primary_source
resolve_repository_target
resolve_or_stub_dataset
is_concrete_version
emit_node
emit_edge
record_deferred
record_skipped
record_unresolved
validate_output
```

No rule may branch on a specific repository, organization, author, package, DOI, or CIROH product name. CIROH specificity belongs to the selected corpus and ontology, not to per-repository code paths.

*End of deterministic GitHub extraction mapping.*
