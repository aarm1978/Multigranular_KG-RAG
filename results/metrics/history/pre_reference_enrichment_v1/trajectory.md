# Structural Metrics Trajectory

This report implements the cumulative internal trajectory from `docs/evaluation_decisions.md`. Both variants are always reported. The full graph is the primary description of the actual KG product; the filtered view is a sensitivity analysis and does not alter graph content.

## Table A — Full KG

Primary description of the complete deterministic KG at each construction point.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) [HS v0.1.6] | 1303 | 1628 | 3.774367 | 1.275518 | 2.498849 | 1.342287 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) [HS v0.1.6] | 14011 | 14298 | 3.957319 | 1.916351 | 2.040968 | 1.047677 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) [HS v0.1.6] | 18678 | 20851 | 5.564354 | 3.331674 | 2.232680 | 1.152747 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) [HS v0.1.6] | 28334 | 32623 | 5.513129 | 3.210383 | 2.302746 | 1.133585 | 1.000000 (mention level pre consolidation) |

## Table B — File-inventory-excluded sensitivity analysis

Sensitivity analysis only. File-inventory entities remain legitimate content in the actual KG and are not deleted from graph outputs.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) [HS v0.1.6] | 546 | 871 | 4.849817 | 1.659341 | 3.190476 | 1.747253 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) [HS v0.1.6] | 1552 | 1839 | 4.269974 | 1.900129 | 2.369845 | 1.373067 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) [HS v0.1.6] | 5977 | 7908 | 8.731136 | 6.084992 | 2.646144 | 1.381295 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) [HS v0.1.6] | 15633 | 19680 | 6.682275 | 4.164524 | 2.517751 | 1.205399 | 1.000000 (mention level pre consolidation) |

## Table C — Sensitivity effect

Every delta is `file_inventory_excluded − full`. Parenthesized values are percentage deltas relative to the full value; `—` indicates a zero denominator.

| Construction point | Excluded nodes | Excluded edges | Excluded nodes as percentage of full graph | Delta information density | Delta informative attributes per node | Delta incident edges per node | Delta relational richness | Delta consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HydroShare (det.) [HS v0.1.6] | 757 | 757 | 58.096700% | +1.075450 (+28.494%) | +0.383823 (+30.092%) | +0.691627 (+27.678%) | +0.404966 (+30.170%) | +0.000000 (+0.000%) |
| + GitHub (det.) [HS v0.1.6] | 12459 | 12459 | 88.922989% | +0.312655 (+7.901%) | -0.016222 (-0.847%) | +0.328877 (+16.114%) | +0.325390 (+31.058%) | +0.000000 (+0.000%) |
| + Hub (det.) [HS v0.1.6] | 12701 | 12943 | 67.999786% | +3.166782 (+56.912%) | +2.753318 (+82.641%) | +0.413464 (+18.519%) | +0.228548 (+19.826%) | +0.000000 (+0.000%) |
| + Publications (det.) [HS v0.1.6] | 12701 | 12943 | 44.826004% | +1.169146 (+21.207%) | +0.954141 (+29.720%) | +0.215005 (+9.337%) | +0.071814 (+6.335%) | +0.000000 (+0.000%) |

## Counting Policy

Each nonempty informative attribute key counts once. Incoming and outgoing edge instances contribute to information density; distinct incident relation names contribute to relational richness. A self-loop counts once for its node.

**Administrative/identifier exclusion set:** `archiveFormat`, `bagUrl`, `canonicalName`, `checksum`, `contentAvailable`, `contributions`, `contributorType`, `createdAt`, `curationStatus`, `declaredLicenseMetadata`, `doi`, `downloadUrl`, `downloaded`, `downloadedFileCount`, `edgeId`, `email`, `extractionMethod`, `fileName`, `filePath`, `fileTotalCount`, `fullName`, `fundingAgencyUrl`, `githubId`, `githubStats`, `homepage`, `host`, `htmlUrl`, `hydroshareResourceId`, `hydroshareUserId`, `id`, `identifier`, `identifierRegime`, `identifierType`, `identifierValue`, `identifiers`, `identityRegime`, `internalId`, `inventoryId`, `launchURL`, `login`, `manifestType`, `mentionCount`, `metricExclusion`, `modifiedAt`, `moduleRoleId`, `nodeId`, `normalizedValue`, `orcid`, `originalValue`, `paperId`, `path`, `phaseAField`, `phaseAVersion`, `profileUrl`, `pushedAt`, `rawSource`, `repoId`, `requestUrlBase`, `requestUrlBaseFile`, `resourceId`, `ror`, `selectionReason`, `selectionReasonHistogram`, `sizeBytes`, `sourceArtifact`, `sourceDeclarations`, `sourceLocation`, `sourcePath`, `sourceRepoId`, `sourceType`, `spdxId`, `timestamp`, `toolIconUrl`, `toolId`, `updatedAt`, `url`, `urls`

**Class-specific administrative exclusions:** ExecutionEnvironment: `pinnedCount`, `pinnedSetEvidence`, `prefix`; Identifier: `idType`, `value`; License: `declarationKind`, `declarationScope`, `key`; Repository: `forkParent`, `owner`; Tool: `cffVersion`, `declaredLicenseKind`, `declaredLicenseSourceValue`, `repository`, `repositoryCode`

**File-inventory classes:** `DatasetFile` (A-D03), `File` (A-C02), and `RepoFile` (A-C02). Excluded edges are derived only from incident excluded endpoints; relation names and node degrees are not selectors.

**External URL stub note:** Because url and host are excluded as identifier/administrative fields, external-URL stub nodes may have near-zero informative-attribute density. This is intentional and honest: unresolved stubs are information-poor, while their incident relations still contribute to structural density.
