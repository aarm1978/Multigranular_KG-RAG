# Structural Metrics Trajectory

This report implements the cumulative internal trajectory from `docs/evaluation_decisions.md`. Both variants are always reported. The full graph is the primary description of the actual KG product; the filtered view is a sensitivity analysis and does not alter graph content.

## Table A — Full KG

Primary description of the complete deterministic KG at each construction point.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) | 1288 | 1613 | 3.795031 | 1.290373 | 2.504658 | 1.346273 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) | 13996 | 14283 | 3.959417 | 1.918405 | 2.041012 | 1.047728 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) | 18663 | 20836 | 5.567219 | 3.334351 | 2.232867 | 1.152869 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) | 28319 | 32608 | 5.514990 | 3.212084 | 2.302906 | 1.133656 | 1.000000 (mention level pre consolidation) |

## Table B — File-inventory-excluded sensitivity analysis

Sensitivity analysis only. File-inventory entities remain legitimate content in the actual KG and are not deleted from graph outputs.

| Construction point | Nodes | Edges | Information density | Informative attributes per node | Incident edges per node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---|
| HydroShare (det.) | 531 | 856 | 4.930320 | 1.706215 | 3.224105 | 1.768362 | 1.000000 (mention level pre consolidation) |
| + GitHub (det.) | 1537 | 1824 | 4.292128 | 1.918673 | 2.373455 | 1.376708 | 1.000000 (mention level pre consolidation) |
| + Hub (det.) | 5962 | 7893 | 8.748071 | 6.100302 | 2.647769 | 1.382254 | 1.000000 (mention level pre consolidation) |
| + Publications (det.) | 15618 | 19665 | 6.686772 | 4.168523 | 2.518248 | 1.205596 | 1.000000 (mention level pre consolidation) |

## Table C — Sensitivity effect

Every delta is `file_inventory_excluded − full`. Parenthesized values are percentage deltas relative to the full value; `—` indicates a zero denominator.

| Construction point | Excluded nodes | Excluded edges | Excluded nodes as percentage of full graph | Delta information density | Delta informative attributes per node | Delta incident edges per node | Delta relational richness | Delta consolidation ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HydroShare (det.) | 757 | 757 | 58.773292% | +1.135289 (+29.915%) | +0.415842 (+32.226%) | +0.719447 (+28.724%) | +0.422089 (+31.352%) | +0.000000 (+0.000%) |
| + GitHub (det.) | 12459 | 12459 | 89.018291% | +0.332711 (+8.403%) | +0.000268 (+0.014%) | +0.332443 (+16.288%) | +0.328980 (+31.399%) | +0.000000 (+0.000%) |
| + Hub (det.) | 12701 | 12943 | 68.054439% | +3.180852 (+57.135%) | +2.765951 (+82.953%) | +0.414902 (+18.582%) | +0.229385 (+19.897%) | +0.000000 (+0.000%) |
| + Publications (det.) | 12701 | 12943 | 44.849748% | +1.171782 (+21.247%) | +0.956439 (+29.776%) | +0.215342 (+9.351%) | +0.071940 (+6.346%) | +0.000000 (+0.000%) |

## Counting Policy

Each nonempty informative attribute key counts once. Incoming and outgoing edge instances contribute to information density; distinct incident relation names contribute to relational richness. A self-loop counts once for its node.

**Administrative/identifier exclusion set:** `archiveFormat`, `bagUrl`, `canonicalName`, `checksum`, `contentAvailable`, `contributions`, `contributorType`, `createdAt`, `curationStatus`, `declaredLicenseMetadata`, `doi`, `downloadUrl`, `downloaded`, `downloadedFileCount`, `edgeId`, `email`, `extractionMethod`, `fileName`, `filePath`, `fileTotalCount`, `fullName`, `fundingAgencyUrl`, `githubId`, `githubStats`, `homepage`, `host`, `htmlUrl`, `hydroshareResourceId`, `hydroshareUserId`, `id`, `identifier`, `identifierRegime`, `identifierType`, `identifierValue`, `identifiers`, `identityRegime`, `internalId`, `inventoryId`, `launchURL`, `login`, `manifestType`, `mentionCount`, `metricExclusion`, `modifiedAt`, `moduleRoleId`, `nodeId`, `normalizedValue`, `orcid`, `originalValue`, `paperId`, `path`, `phaseAField`, `phaseAVersion`, `profileUrl`, `pushedAt`, `rawSource`, `repoId`, `requestUrlBase`, `requestUrlBaseFile`, `resourceId`, `ror`, `selectionReason`, `selectionReasonHistogram`, `sizeBytes`, `sourceArtifact`, `sourceDeclarations`, `sourceLocation`, `sourcePath`, `sourceRepoId`, `sourceType`, `spdxId`, `timestamp`, `toolIconUrl`, `toolId`, `updatedAt`, `url`, `urls`

**Class-specific administrative exclusions:** ExecutionEnvironment: `pinnedCount`, `pinnedSetEvidence`, `prefix`; Identifier: `idType`, `value`; License: `declarationKind`, `declarationScope`, `key`; Repository: `forkParent`, `owner`; Tool: `cffVersion`, `declaredLicenseKind`, `declaredLicenseSourceValue`, `repository`, `repositoryCode`

**File-inventory classes:** `DatasetFile` (A-D03), `File` (A-C02), and `RepoFile` (A-C02). Excluded edges are derived only from incident excluded endpoints; relation names and node degrees are not selectors.

**External URL stub note:** Because url and host are excluded as identifier/administrative fields, external-URL stub nodes may have near-zero informative-attribute density. This is intentional and honest: unresolved stubs are information-poor, while their incident relations still contribute to structural density.
