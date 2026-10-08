# Structural Metrics Trajectory

This report implements the cumulative internal trajectory from `docs/evaluation_decisions.md`. Both variants are always reported. The full graph is the primary description of the actual KG product; the filtered view is a sensitivity analysis and does not alter graph content.

## Table A — Full KG

Primary description of the complete deterministic KG at each construction point.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) [HS v0.1.6] | 1303 | 1628 | 3.774367 | 1.275518 | 2.498849 | 1.342287 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) [HS v0.1.6; refs v1] | 14083 | 14393 | 3.953135 | 1.909110 | 2.044025 | 1.051765 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) [HS v0.1.6; refs v1] | 18750 | 21037 | 5.564747 | 3.320800 | 2.243947 | 1.159680 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) [HS v0.1.6; refs v1] | 28406 | 32809 | 5.513518 | 3.203513 | 2.310005 | 1.138210 | 1.000000 (mention level pre consolidation) |

## Table B — File-inventory-excluded sensitivity analysis

Sensitivity analysis only. File-inventory entities remain legitimate content in the actual KG and are not deleted from graph outputs.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) [HS v0.1.6] | 546 | 871 | 4.849817 | 1.659341 | 3.190476 | 1.747253 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) [HS v0.1.6; refs v1] | 1624 | 1934 | 4.219828 | 1.838054 | 2.381773 | 1.394089 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) [HS v0.1.6; refs v1] | 6049 | 8094 | 8.694660 | 6.018515 | 2.676145 | 1.400066 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) [HS v0.1.6; refs v1] | 15705 | 19866 | 6.677619 | 4.147724 | 2.529895 | 1.213435 | 1.000000 (mention level pre consolidation) |

## Table C — Sensitivity effect

Every delta is `file_inventory_excluded − full`. Parenthesized values are percentage deltas relative to the full value; `—` indicates a zero denominator.

| Construction point | Excluded nodes | Excluded edges | Excluded nodes as percentage of full graph | Delta information density | Delta informative attributes per node | Delta incident edges per node | Delta relational richness | Delta consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HydroShare (det.) [HS v0.1.6] | 757 | 757 | 58.096700% | +1.075450 (+28.494%) | +0.383823 (+30.092%) | +0.691627 (+27.678%) | +0.404966 (+30.170%) | +0.000000 (+0.000%) |
| + GitHub (det.) [HS v0.1.6; refs v1] | 12459 | 12459 | 88.468366% | +0.266693 (+6.746%) | -0.071056 (-3.722%) | +0.337748 (+16.524%) | +0.342324 (+32.548%) | +0.000000 (+0.000%) |
| + Hub (det.) [HS v0.1.6; refs v1] | 12701 | 12943 | 67.738667% | +3.129913 (+56.245%) | +2.697715 (+81.237%) | +0.432198 (+19.261%) | +0.240386 (+20.729%) | +0.000000 (+0.000%) |
| + Publications (det.) [HS v0.1.6; refs v1] | 12701 | 12943 | 44.712385% | +1.164101 (+21.114%) | +0.944211 (+29.474%) | +0.219890 (+9.519%) | +0.075225 (+6.609%) | +0.000000 (+0.000%) |

## Counting Policy

Each nonempty informative attribute key counts once. Incoming and outgoing edge instances contribute to information density; distinct incident relation names contribute to relational richness. A self-loop counts once for its node.

**Administrative/identifier exclusion set:** `archiveFormat`, `bagUrl`, `canonicalName`, `checksum`, `contentAvailable`, `contributions`, `contributorType`, `createdAt`, `curationStatus`, `declaredLicenseMetadata`, `doi`, `downloadUrl`, `downloaded`, `downloadedFileCount`, `edgeId`, `email`, `extractionMethod`, `fileName`, `filePath`, `fileTotalCount`, `fullName`, `fundingAgencyUrl`, `githubId`, `githubStats`, `homepage`, `host`, `htmlUrl`, `hydroshareResourceId`, `hydroshareUserId`, `id`, `identifier`, `identifierRegime`, `identifierType`, `identifierValue`, `identifiers`, `identityRegime`, `internalId`, `inventoryId`, `launchURL`, `login`, `manifestType`, `mentionCount`, `metricExclusion`, `modifiedAt`, `moduleRoleId`, `nodeId`, `normalizedValue`, `orcid`, `originalValue`, `paperId`, `path`, `phaseAField`, `phaseAVersion`, `profileUrl`, `pushedAt`, `rawSource`, `repoId`, `requestUrlBase`, `requestUrlBaseFile`, `resourceId`, `ror`, `selectionReason`, `selectionReasonHistogram`, `sizeBytes`, `sourceArtifact`, `sourceDeclarations`, `sourceLocation`, `sourcePath`, `sourceRepoId`, `sourceType`, `spdxId`, `timestamp`, `toolIconUrl`, `toolId`, `updatedAt`, `url`, `urls`

**Class-specific administrative exclusions:** ExecutionEnvironment: `pinnedCount`, `pinnedSetEvidence`, `prefix`; Identifier: `idType`, `value`; License: `declarationKind`, `declarationScope`, `key`; Repository: `forkParent`, `owner`; Tool: `cffVersion`, `declaredLicenseKind`, `declaredLicenseSourceValue`, `repository`, `repositoryCode`

**File-inventory classes:** `DatasetFile` (A-D03), `File` (A-C02), and `RepoFile` (A-C02). Excluded edges are derived only from incident excluded endpoints; relation names and node degrees are not selectors.

**External URL stub note:** Because url and host are excluded as identifier/administrative fields, external-URL stub nodes may have near-zero informative-attribute density. This is intentional and honest: unresolved stubs are information-poor, while their incident relations still contribute to structural density.
