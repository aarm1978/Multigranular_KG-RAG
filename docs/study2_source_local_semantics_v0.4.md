# Study 2 prospective source-local semantics v0.4

Authority: researcher instruction following the 2026-10-28 ontology coverage audit.
This contract is opt-in. Frozen v0.1.6, Step 11 v0.3, Step 13 v0.1 and all historical
requests, results, projections and Publication production retain their original bytes
and behavior. It grants no provider execution, scientific correctness or final KG authority.

## Executable inventory and signature amendment

`src/extraction/llm/nonpublication_semantic_v04.yaml` is the versioned executable
inventory. It includes previously operative targets and approved dedicated omissions:
HydroShare concrete features/Concept, GitHub Variable/Parameter/Concept, Hub features,
Concept, weak model/dataset mentions and Paper citations, plus source-local references.
The inventory gives exact IDs; provider schemas, native validators and construction use
that inventory. The runtime coverage invariant checks every ID against actual schema
branches; focused offline examples exercise parsing, binding and acceptance.

For this prospective non-Publication contract only, C-C15 usesDataset and C-DC25 mentionsDataset additionally accept DatasetMention,
following the C-P20 occurrence/reference distinction. This is an explicit versioned
signature overlay, not a false claim to unchanged ontology v0.1.6 signatures. Exact
identifier-based references and C-DC27 describesDataset still require DatasetResource. A positive description claim without an identifiable resource endpoint remains unresolved; it is not silently downgraded to incidental mention. No Publication signatures
or production artifacts change. A downstream ontology export must explicitly incorporate
this overlay before accepting its records; this task does not construct that graph.

A DatasetMention is a named source-local occurrence with unresolved global identity.
DatasetResource creation requires a literal exact identifier in bound source evidence. Paper and Repository references can remain evidence-backed local occurrences without a global identifier; an explicitly supplied identifier must be bound literally. No name-based identity, guessed DOI or corpus-membership prerequisite.
Exact identifier matches reuse unambiguous accepted deterministic endpoints. New identities
are hashed from owner, type and exact identifier, or from bound occurrence coordinates
and label; model candidate IDs never determine semantic identities. Coincident names at
different source locations are not deduplicated. Independently quoted edges deduplicate
only by exact resolved type/source/target within the owner. All original candidate and
binding records remain available when projections suppress duplicates.

## Sources and evidence

HydroShare keeps original complete abstract and recovered complete README authorities.
Preparation must select the recovery bundle for an affected owner. GitHub aggregates
complete eligible documentary authorities over all supplied files and notebook Markdown
cells, using the full-document adapter without historical passage filtering. Hub sends
complete exact content_mdx through the full-content adapter. No code cells, inferred
execution, dynamically unmaterialized text or invented provenance are evidence.
Literal full-content availability and evidence admissibility are separate: uncertain Hub
visibility and code-only claims retain structured holds. Existing Example/Parameter
parent paths and independent node/edge bindings remain mandatory. No semantic judge is
introduced: ordinary acceptance remains mechanical/evidence validation plus the explicit
interpretive-gate policy, not proof of scientific truth.

## Method and versions

GitHub implementation claims retain exact evidence, methodSurfaceForm and unresolved
endpoint details. A-P13 remains a Publication discourse Method endpoint there. Neither
Algorithm nor Workflow is a substitute for an untyped reusable scientific method.
Researcher decision still needed: a reusable scientific-method class or a precise broader
Method interpretation. Unaffected targets execute; these positive claims stay structured
and outside accepted projections. Hub's already authorized source-local descriptive
Method behavior is preserved; no fabricated Publication endpoint is introduced.

ModelVersion requires an own-product repository and exact product endpoint. The initial
verifiable release supports root CITATION.cff / package.json or pyproject.toml project/tool.poetry version fields bound at their actual source
coordinates, a deterministic version record containing version/toolId/sourceRepoId/sourcePath,
and an accepted Tool implementedBy owner assertion. Dependency/nested version fields and
matching labels cannot release it. The root literal must agree with the trusted structured
record; exact existing version assertions are suppressed, not relabeled as novel extraction.
A novel structured version can be materialized only with a complete pinned owner catalog, an exact deterministic own-product Tool from that source path, matching root title/version fields, and no conflicting existing version for that product. Its ID is derived from owner/product/version, never a surface label. Novel prose-only versions and unavailable structured comparison remain positive unresolved
records. Broadening to other or ambiguous/dynamic structured version formats requires an equally explicit
field/own-product verifier, not removal of the hold.

## Deliberate limits and diagnostics

Keep abstract-class restrictions, deterministic structural metadata, controlled Purpose
seeds, inactive DataService, code-semantic exclusions and Step 14 alignment boundary.
D-26 is derived only from accepted independent occurrence evidence for the explicitly
listed HydroShare NamedPlace/Metric/Parameter, GitHub Metric and Hub Variable/Metric/Algorithm loci. These restore explicit deterministic-to-semantic mapping handoffs; they do not activate every generic endpoint class. Stronger accepted relations suppress
the redundant fallback. Other generic-only audit opportunities remain outside this bounded
activation, rather than indiscriminately authorizing every D-26 range class.

Retain source-local deferred records unchanged as context/provenance. They are not authority
to promote an assertion. Distinguish insufficient evidence, ambiguous semantics, unresolved
identity and valid exact endpoint reuse. Invalid syntax fails closed; evidence/endpoint holds,
explicit abstentions and legitimate zero-yield outcomes remain reproducible. No automatic
promotion of abstention to assertion, cross-run merging or Step 14 consolidation.

## Operation

`source_local_semantics.build` prepares coherent per-owner requests and `replay` consumes
recorded bytes through existing candidate validators and construction acceptance. The
prospective pilot CLI prepares immutable ignored artifacts; its transport adapter reuses
the existing live/Batch write-ahead journals. Explicit researcher-terminal submission is
required; preparation and replay do not call providers. No historical production root may
be an output. Every pilot is diagnostic, not a definitive family-version selection.

## Ontology-to-executable coverage summary

All IDs below share request/schema construction, native versioned candidate validation,
source-local identity processing and Step 13 construction. Counts include reused endpoint
classes/controlled seeds, not independent discoveries or recall estimates. The inventory
also retains every prior target; no permanent old/new category pipelines are introduced.

| Family | Entity entries | Explicit predicates | Newly represented entity entries | Newly represented predicates |
|---|---:|---:|---|---|
| hydroshare | 22 | 13 | A-D01 DatasetResource, A-DOM05 Concept, A-DOM07a Watershed, A-DOM07b RiverReach, A-DOM07c Gauge, A-DOM07d WaterBody, A-DOM07e Aquifer, A-DOM07f VPU, A-DOM08 NamedPlace, A-DOM11 EvaluationMetric, A-DOM12 Parameter, A-P01 Paper | C-D14 derivedFrom, C-D15 referencesFeature, C-D19 references, C-D23 mentionsConcept, D-22 implementedBy |
| github | 20 | 19 | A-C01 Repository, A-DOM04 Variable, A-DOM05 Concept, A-DOM11 EvaluationMetric, A-DOM12 Parameter, A-P01 Paper, A-P25 DatasetMention | C-C12 mentionsVariable, C-C17 referencePublication, C-C19 referencesDataset, C-C24 usesParameter, C-C25 mentionsParameter, C-C26 mentionsConcept, D-17 generatedBy |
| ciroh_hub | 26 | 18 | A-DOM04 Variable, A-DOM05 Concept, A-DOM07a Watershed, A-DOM07b RiverReach, A-DOM07c Gauge, A-DOM07d WaterBody, A-DOM07e Aquifer, A-DOM07f VPU, A-DOM11 EvaluationMetric, A-DOM13 Algorithm, A-P01 Paper, A-P25 DatasetMention | C-DC08 mentionsConcept, C-DC23 referencesFeature, C-DC24 mentionsModel, C-DC25 mentionsDataset, C-DC26 referencePublication, D-23 describedInPaper |

Conditional paths remain explicit: GitHub Method is positive-unresolved; ModelVersion
requires structured own-product proof; Hub dependent nodes require valid parents; uncertain
MDX visibility is held even though its text remains in the request. Generic-only classes
without a dedicated family predicate or an explicit deterministic-to-semantic mapping
handoff are not blanket-enabled (for example GitHub geographic occurrences, HydroShare
Algorithm, and generic Organization mentions). These are bounded activation limits, not a
claim that every ontology-valid triple or every possible D-26 endpoint is now discoverable.

Native deferred/unresolved records retain their original record and graph location/hash.
The inspected HydroShare baseline has no deferred-record arrays; none are fabricated.
GitHub has prose handoff/unknown-reference/dynamic-version/fork-parent records; Hub has
unknown-link typing/product-card/DOI-target records. Fork-parent inference, arbitrary DOI
resolution and heuristic service candidates are not automatically promoted.

## Researcher-terminal diagnostic

Use the researcher's Python executable in place of `python`. From the repository root:

```bash
python -m src.evaluation.source_local_semantic_pilot prepare
QUEUE_SHA=$(python -c 'import hashlib; from pathlib import Path; print(hashlib.sha256(Path("var/study2_step13/source-local-semantic-pilot/v04/queue-manifest.json").read_bytes()).hexdigest())')
python -m src.evaluation.source_local_semantic_pilot preflight --transport live --queue-sha256 "$QUEUE_SHA"
python -m src.evaluation.source_local_semantic_pilot submit --transport live --queue-sha256 "$QUEUE_SHA"
python -m src.evaluation.source_local_semantic_pilot review-live --queue-sha256 "$QUEUE_SHA"
```

`prepare`, `preflight` and `review-live` explicitly block sockets. `submit` is a real,
researcher-invoked provider operation; it is not run by Codex. The ignored immutable queue
contains `queue-manifest.json`, `queue/*.json`, `batch-input.jsonl`, and `summary.md`.
Execution has its own native journal under `execution/live/`; offline accepted/held reports
are written once under `review-live/`. Preparation/review refuse overwrites. The pilot
selects the recovered Logan River HydroShare owner, GitHub data_access_example (all available
eligible documentary authorities), and the Hub awi-psu-collab2 page. These are diagnostics,
not a definitive version choice. Missing pinned production inputs fail rather than regenerate.

For Batch, use the same queue with `submit --transport batch --queued-token-limit N
--queue-sha256 "$QUEUE_SHA"`, then `status` / `collect` with `--transport batch` and the
same pin. The existing one-attempt raw pilot controller preserves receipts and unknown
submission holds. Offline individual replay is also available with `replay --prepared
PATH --response EXACT_MODEL_PAYLOAD --report NEW_PATH`; full production's native Batch
adapter directly dispatches v0.4 recorded outputs to the same semantic replay route.
All new preparation and individual replay destinations must remain under
`var/study2_step13/source-local-semantic-pilot/`; existing outputs cannot be overwritten.

Preparing the three-owner pilot computes native envelope-byte token/cost scenarios using
recorded pricing assumptions, not measured token counts or current-price certification.
The original queue has 42 HydroShare, 51 GitHub and 239 Hub owners: 332 owner contexts before
new full-content sizing. The Hub corpus has 242 pages; the three unqueued pages and any
oversize owner contexts must be accounted for before full-production request/cost estimates.
No extrapolated dollar estimate is supported by this small diagnostic selection. Preparation
holds oversized owner contexts rather than truncating input or silently changing aggregation.
