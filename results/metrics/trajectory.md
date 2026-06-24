# Structural Metrics Trajectory

This table implements the internal trajectory structure from `docs/evaluation_decisions.md` §6.1. Information density is shown with its attribute and incident-edge components for diagnosis.

| Construction point | Information density | Informative attributes / node | Incident edges / node | Relational richness | Consolidation ratio |
|---|---:|---:|---:|---:|---:|
| HydroShare (det.) | 4.382764 | 1.878106 | 2.504658 | 1.346273 | 1.000000 (mention level pre consolidation) |

## Counting Policy

Each nonempty informative attribute key counts once. Incoming and outgoing edge instances contribute to information density; distinct incident relation names contribute to relational richness. A self-loop counts once for its node.

**Administrative/identifier exclusion set:** `bagUrl`, `checksum`, `createdAt`, `curationStatus`, `doi`, `downloadUrl`, `edgeId`, `extractionMethod`, `filePath`, `fundingAgencyUrl`, `host`, `hydroshareResourceId`, `hydroshareUserId`, `id`, `identifier`, `identifierRegime`, `identifierType`, `identifierValue`, `identifiers`, `internalId`, `inventoryId`, `launchURL`, `mentionCount`, `modifiedAt`, `nodeId`, `normalizedValue`, `orcid`, `path`, `requestUrlBase`, `requestUrlBaseFile`, `resourceId`, `ror`, `sourceArtifact`, `sourceLocation`, `spdxId`, `timestamp`, `toolIconUrl`, `updatedAt`, `url`

**External URL stub note:** Because url and host are excluded as identifier/administrative fields, external-URL stub nodes may have near-zero informative-attribute density. This is intentional and honest: unresolved stubs are information-poor, while their incident relations still contribute to structural density.
