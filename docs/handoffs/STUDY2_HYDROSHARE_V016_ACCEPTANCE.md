# Study 2 — Minimal HydroShare v0.1.6 correction acceptance

**Status:** Researcher ACCEPTED on 2026-10-07. Implementation and validation
checkpoint: `269f4985ae97d7a34d6779a83dfc6f080e6eac8b`, pushed on
`codex/publication-human-core-annotation-ui`.
This record documents researcher acceptance of that checkpoint; no tests,
extractors, or metrics were rerun during this documentation task.

## Authority and accepted result

Step 10 closed at `a2cb542639e15dbf9d14f6ec661a6cb26bb084a9`; scope remains
[STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md](STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md).
The prospective TBox is ontology v0.1.6, formally frozen at
`b2c735bce9692e8937abcc08c4d9ac48a85b255e`.

- Own-resource `system_metadata.doi`: 15 new Identifier nodes and 15
  hasIdentifier edges across the 42-resource corpus.
- 18 DatasetResource hasContributor Person edges aligned to C-D27.
- 21 Award fundedBy Organization edges aligned to C-D28.
- Existing relation semantics and endpoints preserved. Inventory-ID alignment
  changes the derived IDs of those 39 edges prospectively.
- HydroShare graph: 1,303 nodes / 1,628 edges.
- Final cumulative graph: 28,334 nodes / 32,623 edges; file-inventory-excluded:
  15,633 nodes / 19,680 edges.

Implementation and mapping are in
`src/extraction/deterministic/extract_hydroshare.py` and
`src/extraction/deterministic/hydroshare_extraction_mapping.md`.
DOI handling preserves exact raw evidence at `<resource_id>:system_metadata.doi`,
uses normalized source-local identifier identity, rejects malformed/foreign-resource
HydroShare DOI assertions, and deduplicates equivalent own identifier forms.
This is deterministic lexical validation, not remote DOI resolution or cross-source
identity resolution; it does not guarantee coverage of every possible DOI syntax.

## Validation and reproducible artifact boundary

The accepted implementation run passed **47 focused T1/T2 tests**:
`tests/test_extract_hydroshare.py` (12),
`tests/test_build_cumulative_snapshot.py` (7), and
`tests/test_compute_structural_metrics.py` (28).
The run used the `ontology` environment's Python with `-B -m unittest discover
-s tests -p <test filename>`. Coverage included DOI evidence/rejection/deduplication,
inventory alignment, reproducibility, historical hash preservation, frozen-ontology
compatibility, and cumulative snapshot/metric integration.

Source corpus: `data/interim/datasets/ciroh_hydroshare_corpus.json`.
Prospective graph outputs and their exact SHA-256 values are recorded in
`tests/fixtures/hydroshare/prospective_v016_hashes.json`:

- `data/interim/datasets/hydroshare_nodes_edges_v016.json`
- `data/interim/evaluation/hydroshare_github_deterministic_v016.json`
- `data/interim/evaluation/hydroshare_github_hub_deterministic_v016.json`
- `data/interim/evaluation/hydroshare_github_hub_publications_deterministic_v016.json`

Generation used the HydroShare extractor and the unchanged
`src/evaluation/build_cumulative_snapshot.py` and
`src/evaluation/compute_structural_metrics.py`. Current tracked records are the four
`results/metrics/snapshots/*deterministic.json` files and
`results/metrics/trajectory.md`, covering full, file-inventory-excluded, and sensitivity
results under unchanged metric definitions. Each cumulative stage gained 15 nodes
and 15 edges; informative-attribute totals and inventory exclusions stayed unchanged.

Historical unsuffixed graphs remain separate and unchanged. The historical
HydroShare output path is write-protected by the extractor. Historical graphs,
unchanged GitHub/Hub/Publication graph inputs, ontology hash, and preserved metric
copies are pinned in `tests/fixtures/hydroshare/pre_v016_hashes.json`.
Prior metrics and trajectory remain at
`results/metrics/history/pre_hydroshare_v016/`. Historical regression expectations
were retained; prospective expectations were added separately.

Corpus and graph files under `data/interim/` are gitignored local inputs/outputs,
not distributed by this commit. Reproducing corpus-level checks requires these
local artifacts; tests with unavailable local prerequisites may skip and must not
be reported as equivalent to the accepted complete run. Use the pinned implementation,
matching local inputs and hash manifests, and the existing generators; do not
replace historical graphs to reproduce prospective results.
Publication deterministic, evaluation, and production authorities remain unchanged.

## Next pending phase and exclusions

The minimal correction package is complete and accepted. **Step 11 source-specific
semantic extraction contract design** is next, using the accepted Step 10 scope
and ontology v0.1.6. Exact targets, evidence rules, and abstention behavior remain
Step 11 decisions; this acceptance does not implement them or promise exhaustive
semantic extraction.

Optional comprehensive enhancements remain deferred pending separate researcher
authorization, including DataService/servesDataset and WMS/WCS materialization,
README references, Hub doc-to-doc references/citation parsing, and additional typed
geographic identifiers. Mechanically recoverable omissions do not become LLM targets.
Cross-source identity resolution remains Step 14.

**Step 13 retains a distinct Publication full-corpus semantic production dependency.**
Accepted Publication evaluation and the deterministic cumulative graph do not satisfy
that production requirement or authorize rerunning frozen evaluation artifacts.
