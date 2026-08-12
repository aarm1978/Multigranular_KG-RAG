# Publication Pilot 1 Screening Interface

**Interface version:** 0.1.1
**Status:** frozen and ready for production human screening; production screening has not begun
**Boundary:** local human screening of the 267 structurally eligible Publication Pilot 1 source units

## Purpose and scope

This local browser application replaces direct editing of the canonical screening worklist. It presents one validated canonical source unit at a time and records only human screening judgments. It does not call an LLM or remote API, infer or recommend targets, rank units semantically, create annotations or evidence spans, run Gate 0, choose sample partitions, or materialize downstream Block A outputs.

The existing Block A worklist, policies, schemas, target mapping/catalog, inventory, manifest, and source documents are read-only upstream contracts. The app refuses to start if a protected hash differs.

## Technology choice

The interface uses Python's standard-library loopback HTTP server, a vanilla HTML/CSS/JavaScript browser client, and standard-library SQLite. PyYAML 6.0 is pinned in `src/annotation/publication_pilot1/requirements.txt` because the accepted target display catalog is YAML. There is no framework, Node build, Docker service, CDN, analytics, or production database server. A browser UI preserves a direct extension path for later browser-selection to Unicode-code-point conversion without implementing annotation mode now.

## Protected upstream anchors

| Contract | SHA-256 |
| --- | --- |
| Canonical worklist | `b950c8f4389d3af36c3c324572c53f4668304e7fd52c1539e079f72c658e232b` |
| Selection policy | `ea0b9fe9dad9fc05181f4c6e811d9b4df65512eacde78459c69e236da4ba0685` |
| Screening schema | `473e524e679fc19cf267a078cecd09bd21b2e06ddcdb05fdfcc5a8c8a21363f3` |
| Routing schema | `b023a4744d9064c286a608191181c51bc431e117e4abd8c8587c8b1906fdb6b1` |
| Target-family mapping | `fbf1da8f43174791a160106014975fd7084c18de5df2f14a5203368418f081fe` |
| Target display catalog | `06ce672fd0ab66a8faa46bb4a870778c99acebf9cdd242be8b8a0dba493cae96` |
| Gate-0 policy | `f9285a4912e55a154d9037e7fa97a6176f1e37194272ec6907ce8af4f10888ae` |
| Source-unit inventory | `7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e` |
| Source-unit manifest | `42684d340af99440d5f72129a5c5299edcb237d77ce2b3d36456b049bee83823` |

The frozen production-screening provenance anchor is:

| Screening authority | SHA-256 |
| --- | --- |
| Screening handbook 0.1.1 | `c8a8099286871e22616022b5964ef42b10e251601131732968977fcfc3711bc2` |

## Startup

From the repository root, install the one pinned runtime dependency in the chosen Publication interface environment:

```bash
python -m pip install -r src/annotation/publication_pilot1/requirements.txt
```

The server validates upstream files before creating/loading state, binds only to `127.0.0.1` by default, and prints the local URL and private draft path. A non-loopback `--host` is rejected.

For a dry run:

```bash
python -m src.annotation.publication_pilot1.app --dry-run
```

To delete only dry-run decisions and revisions:

```bash
python -m src.annotation.publication_pilot1.app --reset-dry-run
```

After this freeze task is independently accepted and committed, use the exact production-start sequence:

```bash
python -m src.annotation.publication_pilot1.app --reset-dry-run
python -m src.annotation.publication_pilot1.app
```

The production reviewer must then choose the stable production reviewer ID manually. The application does not hard-code or infer it.

`--state-dir` and `--export-dir` accept explicit local destinations. Production and dry-run always use distinct `production.sqlite3` and `dry-run.sqlite3` databases. A dry-run cannot create the compiler-ready filename.

## Review workflow

The reviewer deliberately sets a stable reviewer ID, then navigates with Previous, Next, Next pending, or an exact source-unit ID. The ID may be changed until the first draft revision is saved. The first saved revision locks the single-local-reviewer identity, preventing later drafts or completed units from being reattributed. Dry-run identity can be changed only after an explicit dry-run reset. Filters cover paper, section role, pending/reviewed status, and the interface-local Revisit bookmark. Progress reports reviewed and remaining counts against 267. A reviewed unit may remain bookmarked until the reviewer manually clears it; the bookmark never changes reviewed status.

Every open unit displays paper/artifact identity, source-unit identity, section title and role, character count, content types, conversion status, review-required metadata, and the exact canonical Markdown slice. Each debounced autosave captures an immutable source-unit ID and form snapshot. Every navigation action flushes and awaits that bound snapshot before replacing the form, and a stale response cannot populate another unit. “Mark reviewed & next” saves and validates completion before moving. The browser warns before close/reload while a pending, in-flight, or failed save leaves genuinely unsaved changes. Completion additionally requires a rationale, both densities, routing complexity, and explicit answers for all three boolean flags. Zero routed targets is valid.

The five recurring distinctions and all density/complexity values come from frozen controlled vocabularies. Open units never offer `not_applicable`.

## Frozen handbook and manual UI aids

The authoritative quick reference is [`publication_pilot1_screening_handbook.md`](publication_pilot1_screening_handbook.md), version `0.1.1`, frozen on 2026-08-11 after the final discarded smoke test was accepted. Its SHA-256 is `c8a8099286871e22616022b5964ef42b10e251601131732968977fcfc3711bc2`. The persistent **Handbook / Quick reference** control opens that repository document in a separate read-only browser view without replacing the current form.

The handbook preserves two important routing boundaries. For Paper-branch `usesModel`, `usesTool`, `usesDataset`, `studiesFeature`, and `studiesPlace`, the subject is the current paper; a cited study's action must not be attributed to the current paper. Use-over-mention precedence applies to the same source–target pair, not globally to the unit, so use and mention targets may both be legitimate for different endpoints. Its mixed Introduction / Related Work fast path applies both rules explicitly.

The rationale-template selector contains the eleven handbook templates. It starts blank, runs only after a manual selection, inserts editable text, and requires confirmation before replacing a non-empty rationale. It never chooses a template from section role or source text and never fills bracketed placeholders. **No semantic targets** is a separately confirmed manual action that clears node routes, relation routes, exhaustive-empty choices, and recurring distinctions. It does not set either density, routing complexity, or any boolean flag; it offers the matching rationale only through a second explicit reviewer confirmation.

The compact deterministic/deferred-reference panel displays the exact accepted `deterministicNodeRefs`, `deterministicEdgeRefs`, and `deferredRecordRefs` strings, or `None`. It does not interpret them or set `deterministicEndpointLikely`. **Revisit** is a manual local SQLite/audit bookmark that persists across restarts and supports filtering, but is not a worklist field and cannot appear in either CSV export. A production-integrity banner repeats that screening is prospective routing, only the displayed unit and handbook may be used, and external search or AI assistance must not make unit-specific decisions. Dry-run mode instead remains visibly identified as discarded/non-production. None of these aids performs semantic inference, supplies a routing recommendation, or changes target semantics.

## Source-text validation

The server reads `sourceTextPath`, applies only the frozen BOM/line-ending/forbidden-control normalization, and slices with zero-based half-open Python Unicode code-point offsets. It compares the slice with the accepted inventory text, SHA-256, and character count before display. A deterministic mismatch blocks saving/completing that unit and shows the stable error in the UI. The UI does not keep a rewritten source-text copy.

## Target presentation and exhaustive-empty rule

All labels, definitions, boundary hints, groups, treatments, roles, and relation domain/range details come from the accepted target display catalog. Human-visible concrete targets are grouped and searchable. Nothing is selected initially; monitored targets remain ordinary routing choices; and there is no 12-target cap. Stored/exported values are operational IDs.

`likelyExhaustiveEmptyTargetIDs` is limited to the intersection of currently routed targets and `pilotTreatment == extract_and_evaluate`. Unrouting a selected target immediately removes it and shows a notice. The backend repeats this enforcement, so a manipulated browser request cannot preserve an invalid value.

## Persistence, audit, and privacy

Default private state is under:

```text
var/publication_pilot1_screening/
```

That directory is Git-ignored. SQLite holds reviewer identity, drafts, completion state, timestamps, immutable revision snapshots, and local Revisit bookmarks. On reopen, the application compares the stored interface version, state namespace, worklist hash, catalog hash, mapping hash, screening-schema hash, selection-policy hash, and `screeningHandbookSha256` with current expected values. Any mismatch stops startup with `SCREENING_STATE_CONTRACT_MISMATCH:<field>`; production state is never rewritten or reset automatically. A handbook-binding mismatch therefore fails with `SCREENING_STATE_CONTRACT_MISMATCH:screeningHandbookSha256`. The explicit dry-run reset deletes and reinitializes only dry-run state.

An adjacent `.session.json` sidecar records interface/contract hashes, `screeningHandbookSha256`, reviewer/session times, completed count, latest per-unit revision timestamps, `lastExportKind`, `lastExportTimestamp`, and `lastExportHash`. Bootstrap provenance exposes the interface version and frozen handbook digest. A successful complete production export additionally sets `exportedReviewedCsvHash` and `exportedReviewedCsvTimestamp`; later incomplete backups do not overwrite those compiler-ready provenance fields. Viewing a completed unit does not change `screenedAt`; editing and resaving preserves it while adding a local audit revision. No source text or screening decision is sent off-machine.

## Export

An incomplete backup is clearly timestamped and cannot be confused with the compiler-ready artifact. Production complete export is blocked until all 267 open units are complete. Both exports reconstruct all 358 canonical rows, preserve the exact 38-column schema and every deterministic field value, retain structurally prefilled rows unchanged, use lowercase boolean strings and pipe-delimited sorted multi-values, and add no app metadata columns.

The complete filename is:

```text
publication_pilot1_screening_worklist_reviewed.csv
```

The canonical blank worklist is never an allowed export destination. Export uses interface-side contract validation only; it never calls `compile_reviewed_worklist()` and therefore cannot create screening JSONL, routing JSONL, coverage, candidate-order, or calibration outputs.

## Tests

Run the focused interface suite:

```bash
python -m pytest tests/test_publication_pilot1_screening_interface.py
```

The suite covers hashes and cardinalities, the frozen handbook version/status/date/hash, exact handbook/UI template parity, handbook state binding and mismatch rejection, manual-only rationale templates and no-target clearing, exact reference display, local Revisit persistence/export exclusion, the integrity banner, canonical text slicing, no semantic defaults, immutable fields, source-unit-bound navigation/autosave ordering, persisted-state contract compatibility, reviewer locking, split export audit semantics, controlled values, target routing and exhaustive-empty enforcement, all-row exports, dry-run isolation, Git-ignore coverage, and the Block A materialization boundary. Existing Block A and Publication-focused tests remain separate acceptance checks.

## Known limitations and extension point

This is a single-local-reviewer application with no authentication, concurrent editing, network deployment, or in-browser file picker. The export directory is selected at startup. It intentionally has no evidence highlighting, annotations, endpoint linking, reliability blinding, adjudication, calibration telemetry, or Gate-0 behavior. Exact source text is rendered in a selection-capable browser element, while the server owns code-point offsets and canonical validation; Annotation Mode can add explicit selection-offset conversion later without changing source-unit identity or draft/export contracts.
