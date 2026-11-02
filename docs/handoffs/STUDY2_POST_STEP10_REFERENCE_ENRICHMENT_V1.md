# Study 2 — Post-Step-10 deterministic reference enrichment v1

**Status:** Researcher-authorized bounded scope; implementation/results pending
researcher and ChatGPT review. This is not scientific acceptance or Step 11 completion.
Baseline: accepted HydroShare implementation `269f4985ae97d7a34d6779a83dfc6f080e6eac8b`,
acceptance record `5cf64227fd16807f9cfa9178045c0d0ec30e9b42`, and
[Step 10 decisions](STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md).
The TBox remains frozen **ontology v0.1.6** at `b2c735b`; no v0.1.7 is implied.

## Authorized scope and evidence requirements

- GitHub **C-C27 referencesRepository**: exact repository-root URLs from existing
  Phase A README `deterministic_urls`, bound to exact README occurrences and
  SHA-pinned provenance. Reuse curated targets; external targets use source-scoped
  Repository stubs and the existing URL Identifier representation. Deduplicate
  source/target pairs, retaining declarations. Exclude self links, badges, actions,
  issues/PRs, attachments, arbitrary files and ambiguous targets. Approved stronger
  dependency/fork/archive/implementation associations take precedence; hyperlinks
  alone never establish those roles, use, or equivalence.
- Hub **C-DC22 references**: explicit content links between existing curated
  DocumentationPage nodes, using Phase A canonical URLs and terminal-slash aliases.
  Retain raw target, anchor, source page, exact line, ordinal, Link ID, content hash
  and lineage on aggregated declarations. Exclude self/navigation/hierarchy links,
  announcements already represented, excluded routes and ambiguous/missing pages.
  No speculative page stubs. Preserve existing Link, linksTo, announces, isPartOf,
  hasSubPage and all other prior graph assertions.
- Conservative sufficiency gate: GitHub URLs must occur outside fenced/indented code, image/badge
  or comment lines. Hub requires the exact inline Markdown token on the declared
  line, with at least three surrounding alphabetic words after removing inline
  links; navigation/comment/code contexts abstain. Standalone link lists, cards, query/fragment-bearing GitHub roots,
  other markup and ambiguous occurrences may therefore remain unpromoted.
  These rules are deliberately incomplete, not exhaustive annotation.

**HydroShare DataService materialization is excluded.** The preceding read-only raw
corpus check found no explicit resource-published service assertions across 42
resources. Interim `data_services` candidates were generated heuristically; they
are not verified service evidence and must not be passed to future LLM contracts
as verified services. This package does not rerun that audit or alter those inputs.
DOI citation typing, Hub bibliography parsing, HydroShare README enrichment,
stronger semantic extraction, Step 11 implementation and cross-source alignment
remain outside scope. Publication authorities and the separate Step 13 full-corpus
semantic production dependency remain unchanged.

## Prospective implementation and preservation boundary

Both source extractors expose `--enrich-references` / `enrich_references=True` for
prospective **Phase B 1.1.0**. Historical API/validation behavior remains the default,
including the prior prohibition on these new reference branches. Frozen output
paths are write-protected; the separate default prospective paths require the
prospective profile. Mapping addenda describe the exact rules:

- `src/extraction/deterministic/extract_github.py` and `github_extraction_mapping.md`
- `src/extraction/deterministic/extract_ciroh_hub.py` and `ciroh_hub_extraction_mapping.md`

The prospective GitHub dependency validator now selects an external stub within
its originating repository's scope. New same-URL README stubs exposed the old
first-match ambiguity; historical validator behavior/expectations remain intact.

New local source outputs:
`data/interim/coderepos/github_nodes_edges_refs_v1.json` and
`data/interim/documents/ciroh_hub_nodes_edges_refs_v1.json`.
Three cumulative outputs are under `data/interim/evaluation/`, with stems
`hydroshare_github_deterministic`, `hydroshare_github_hub_deterministic`, and
`hydroshare_github_hub_publications_deterministic`, each suffixed `_refs_v1.json`.
They use accepted `data/interim/datasets/hydroshare_nodes_edges_v016.json`, the two
prospective sources, and unchanged `data/interim/papers/publication_nodes_edges.json`.
No cross-source consolidation occurs.

Exact SHA-256 authorities:

- `tests/fixtures/reference_enrichment/pre_enrichment_hashes.json`: frozen source
  graphs, accepted cumulative graphs, unchanged Phase A inputs, ontology, prior
  HydroShare fixtures and archived metrics.
- `tests/fixtures/reference_enrichment/prospective_hashes.json`: new source and
  cumulative graphs plus the unchanged HydroShare/Publication component hashes.

Accepted tracked metrics were copied byte-for-byte before replacement to
`results/metrics/history/pre_reference_enrichment_v1/` (snapshots, GitHub module,
trajectory). Current snapshots/modules and trajectory remain in `results/metrics/`.
Hub gains an isolated module diagnostic; it is not an extra cumulative trajectory
point. Full, file-inventory-excluded and sensitivity results use unchanged formulas.
The previous HydroShare metric regression now targets the preserved archive with
its original expectations; historical hashes and assertions were not replaced.

## Validation and observed implementation results

**130 focused T1/T2 tests passed**, with no final skips:
GitHub 38; Hub 31; new reference enrichment 14; historical HydroShare boundary 12;
cumulative builder 7; structural metrics 28. New checks cover eligibility/abstention,
identity, inventory branches, exact evidence, stronger-role suppression, duplicate
aggregation, protected paths, preserved graph values/hashes, two CLI builds per
source, cumulative integrity, and persisted metric/trajectory reproducibility.
No ontology reasoning or Publication evaluation was rerun.

| Source | Screened input | Eligible evidence | Emitted pair edges | Duplicate occurrences retained on those edges | Rejected/abstained |
|---|---|---|---|---|---|
| GitHub | 169 source-scoped distinct README URL entries | 59 entries / 76 occurrences across 22 repositories | 59 C-C27 (23 curated-target associations; 36 external) | 17 | 110 URL entries: 97 non-root/ambiguous, 6 self, 7 no qualifying prose occurrence |
| Hub | 283 internal/relative link occurrences | 105 occurrences across 43 pages | 94 C-DC22 | 11 | 178 occurrences: 70 unresolved/ambiguous, 47 stronger/hierarchy, 42 navigation/insufficient prose, 13 uncurated targets, 4 self, 2 excluded routes |

GitHub adds 36 Repository nodes (A-C01), 36 Identifier nodes (A-ID01), 36
hasIdentifier edges (C-C06), and 59 C-C27 edges: **+72 nodes / +95 edges**.
Hub adds **0 nodes / 94 C-DC22 edges**. All prior node and edge records compare
identically. Rejection totals use URL entries for GitHub and occurrences for Hub;
they are not directly comparable measures of semantic recall.

| Graph | Full nodes/edges before → after | Inventory-excluded nodes/edges before → after |
|---|---|---|
| GitHub module | 12708/12670 → 12780/12765 | 1006/968 → 1078/1063 |
| Hub module | 4667/6553 → 4667/6647 | 4425/6069 → 4425/6163 |
| HydroShare + GitHub | 14011/14298 → 14083/14393 | 1552/1839 → 1624/1934 |
| + Hub | 18678/20851 → 18750/21040 | 5977/7908 → 6049/8097 |
| + Publications | 28334/32623 → 28406/32812 | 15633/19680 → 15705/19869 |

| Graph | Full information density before → after | Inventory-excluded information density before → after |
|---|---|---|
| GitHub module | 3.976078 → 3.971362 | 3.955268 → 3.900742 |
| Hub module | 10.388901 → 10.429184 | 10.295819 → 10.338305 |
| HydroShare + GitHub | 3.957319 → 3.953135 | 4.269974 → 4.219828 |
| + Hub | 5.564354 → 5.565067 | 8.731136 → 8.695652 |
| + Publications | 5.513129 → 5.513729 | 6.682275 → 6.678001 |

Hub's before-module values were computed from its unchanged historical graph,
not an earlier tracked module record. Final relational richness changes from
1.133585 to 1.138316 (full), and 1.205399 to 1.213626 (inventory-excluded).
Informative-attribute totals rise by 36 from the GitHub stubs; Hub attributes and
all inventory-exclusion counts are unchanged. HydroShare-only metrics are unchanged.
These structural changes do not establish scientific extraction quality or acceptance.

## Reproduction and limitations

The successful run used Python 3.14.6 in the existing `github-preprocessing`
environment (with packaging and PyYAML). The ontology environment lacked packaging;
the base Python 3.9 cannot parse existing GitHub code. Neither environment nor
repository dependencies were modified to work around those initial launch failures.

Run each source module with `python -B -m src.extraction.deterministic.extract_github
--enrich-references` and the corresponding `extract_ciroh_hub` command. Use unchanged
`src.evaluation.build_cumulative_snapshot` with `--component LABEL=PATH` for the
component combinations recorded in each cumulative graph, then unchanged
`src.evaluation.compute_structural_metrics` with the existing labels/orders and
`--record-series module` for isolated diagnostics. The coordinated rebuild was
performed once after source validation. Test commands use `python -B -m unittest
discover -s tests -p <test filename>` for the six focused files listed above.

Graphs and corpora remain gitignored local artifacts; a checkout alone does not
supply them. Reproduction requires matching inputs and manifest hashes. URLs were
not contacted: exact source references do not establish remote availability or
stronger roles. The conservative prose gates can omit legitimate links; that
limitation awaits review rather than manufactured coverage. No provider calls,
Phase A rebuild, ontology change, historical graph mutation, or local handoff update.
