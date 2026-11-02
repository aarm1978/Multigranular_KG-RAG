# Study 2 source-local specialized diagnostic v0.4.2

Prospective researcher-authorized specialization of the same three v0.4.1 pilot
owners; no new ontology targets, sources, acceptance policy or identity semantics.
The v0.4.1 modules, contract, defaults and existing queues remain unchanged. The
new route reuses them directly; it does not reinterpret old responses or repair
model-authored candidates. Historical implementation-pinned queues still require
their original checkout when their broad implementation pin set differs.

## Groups and closure

Each of the nine queued requests receives its owner's **complete v0.4.1 source
context**, exact deterministic endpoint catalog, original deferred records and
calibrated instructions. Only provider-visible discovery/relationship targets and
strict schema branches are specialized. No text is filtered or truncated.

| Family | Groups (three requests per owner) |
|---|---|
| HydroShare | observations_and_geography; software_and_processing; resource_references |
| GitHub | software_roles_and_use; quantities_and_concepts; datasets_and_citations |
| CIROH Hub | products_and_references; procedures_and_dependents; scientific_occurrences |

`source_local_specialized.GROUPS` is the versioned executable assignment. The
coverage invariant requires the exact union of all currently authorized entity
and relation targets, valid ontology endpoint inheritance, and co-location of Hub
Procedure/Step/Parameter/Example parent-path dependencies. Abstract and inactive
targets stay excluded. All groups may reuse the exact supplied deterministic
endpoints; being present in that catalog does not make an endpoint a discovery
target. Candidate and parent-path IDs are response-local. No group depends on an
unseen response or receives endpoints invented by another group. ModelVersion
own-product proof and the unresolved Method policy remain unchanged.

Repeated Repository and dataset endpoints are intentional. GitHub dataset use is
handled with software use; dataset references/citations and weak named dataset
occurrences have a dedicated group. Each relation retains independent evidence.
If repetitions resolve to different source-local identities under the accepted
v0.4.1 rules, consolidation keeps them different; names never establish equivalence.

## Evidence contribution correction

The v0.4.1 strict schema permits fragments lacking `contribution`, even when the
native validator requires a nonblank contribution on every member of a multi-
fragment assertion. v0.4.2 requires a nonblank contribution on **every fragment**,
including single-fragment assertions. Both strict fragment variants (with/without
locatorAnchor) require it. This is a prospective provider contract correction,
not validator weakening or post-generation filling of omitted contributions.

## Replay and source-local consolidation

Authentic group response bytes, response hash, specialized request hash and group
ID remain in the group report. Before native replay, the specialized schema checks
all targets and contributions. A separately labeled **native validation view**
changes only the response envelope's schemaVersion to v0.4.1; every candidate,
fragment, contribution, ID, abstention and endpoint reference remains exact. The
unchanged v0.4.1 full-context replay supplies source verification, semantic gates,
identity derivation, construction acceptance, unresolved records and D-26 inputs.
Its internal originalReplay refers to that explicit validation view, not a claim
that a full-context provider request was submitted. The actual provider request
and response associations are the enclosing specialized report's fields.

Owner consolidation fails if any expected group is missing, duplicated, associated
with a different owner/context, or hash-inconsistent. It retains every group report
(including authentic bytes, rejected/held/suppressed candidates, original evidence,
unresolved assertions, abstentions and native provenance) and deferred source records.
Accepted nodes aggregate only by exact resolved endpoint ID; accepted edges only by
exact inventory/source/target triple. Each aggregate's `records` retains all exact
native accepted records with request/group references, including original run-local
candidate IDs and dependencies. This is a source-local record collection, not a KG.
It does not splice unsupported fragments into new claims or repair dangling refs.

D-26 remains pipeline-derived. `derivedConstructionInputs` aggregates equal native
assertion IDs once while retaining every supporting construction input/projection
hash. A stronger accepted owner/target relation in **any** group suppresses the
weak fallback, including admitted duplicate edges. Suppressed derivations remain
in `suppressedDerivedMentions`. A held stronger claim cannot suppress an admitted
weak occurrence. No fuzzy merging, cross-source alignment, Step 14 or final KG.

## Offline preparation and researcher operation

Default new immutable root: `var/study2_step13/source-local-semantic-pilot/v042/`.
`contexts/` contains three full-context validation authorities generated offline
by the existing preparer; these are not additional queued provider requests.
`queue-manifest.json`, `queue/*.json`, `batch-input.jsonl` and `summary.md` contain
nine specialized requests, exact source/code/contract pins and byte-based cost
scenarios. No overwrite or replacement of existing output is permitted. Partial
preparation failures remain isolated; use a fresh output path after resolving them.

From the repository root, with the researcher's Python environment:

```bash
python -m src.evaluation.source_local_specialized_pilot prepare
# Copy queueSha256 from preparation output; use that exact pin below.
python -m src.evaluation.source_local_specialized_pilot preflight --transport live --queue-sha256 QUEUE_SHA
python -m src.evaluation.source_local_specialized_pilot submit --transport live --queue-sha256 QUEUE_SHA
python -m src.evaluation.source_local_specialized_pilot review --transport live --queue-sha256 QUEUE_SHA
```

Only explicit submit/status/collect may contact providers. Preparation, preflight
and review block sockets. For Batch, preflight with `--transport batch`, submit
with `--transport batch --queued-token-limit N`, then status/collect and review with
the same transport and queue pin. Native durable transport retains raw bytes and
receipts, and prohibits automatic response retries. Review verifies the native
journal read-only and refuses incomplete or held transport results before owner
consolidation. Output is `review-live/` or `review-batch/`, containing `groups/`,
`owners/` and `summary.json`. Review creates new files and refuses overwrite.

Cost estimates use the native UTF-8 full-envelope byte heuristics and recorded
rates, not measured tokens, empirical workload forecasts or guaranteed charges.
Repeated full context increases input volume; specialized scope does not imply
better extraction quality. No full-corpus preparation or production inference is
part of this diagnostic.
