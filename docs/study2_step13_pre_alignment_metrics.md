# Step 13 pre-alignment structural checkpoint — execution preparation

This is an **evaluation-only**, provisional order-50 checkpoint after the frozen order-40 deterministic graph (28,406 nodes / 32,809 edges). It does not close Step 13, perform Step 14 alignment, or construct the final KG. The twelve-case human review remains pending. It implements the cumulative checkpoint specified in `docs/evaluation_decisions.md`; the historical trajectory and metric policy are unchanged.

## Mechanical transformation

`src/evaluation/build_step13_pre_alignment.py` consumes the existing v4.1 owner consolidations and the latest persisted Publications outcomes. It verifies native report/projection hashes, Publications' pinned journal bytes and chain/head, selected request coverage, original terminal exceptions, and the deterministic snapshot hash. It never calls extraction, semantic validation or provider transport. Original historical authorities are retained; the evaluation manifest pins canonical ontology v0.1.7 and its frozen OWL hash.

- Existing deterministic nodes/edges retain their exact IDs and attributes.
- Non-Publication owner records already consolidate exact endpoint/typed-triple identities. Their native endpoint IDs and source-local edge IDs are reused. All original supporting group records remain in a provenance sidecar.
- Publications' native `requestID#node#candidateID` and `requestID#edge#candidateID` identities remain intact. Repeated occurrences of an identical ID/structural record are one graph record with multiple provenance records. Same labels or quotations across different request IDs do **not** establish equivalence. The 182,255 accepted node occurrences and 89,021 edge occurrences are input checks, not a claim of distinct final KG entities. Conflicting values under the same native ID block output; no preferred record is selected silently.
- A Publication `deterministic:` wrapper is a serialized endpoint reference, not a new node. Its explicit `referenceID` must identify an existing graph node. For the owning curated Paper, the request-manifest inventory `paperID` maps to the existing deterministic node's `internalLineage.localPaperId`; `canonicalArtifactId` and source-artifact evidence must also match exactly. This is a same-source inventory-lineage check, not DOI normalization, canonical-key matching, stub resolution or cross-source alignment. Original wrapper IDs and the graph endpoint mapping remain in provenance. Other missing references remain blockers.
- Semantic node attributes use the literal candidate label and explicit attribute key/value fields. Evidence, request metadata, authority hashes and native records are stored outside `attributes` to avoid inflating information density. The unchanged evaluator supplies all administrative exclusions and full/file-inventory-excluded filtering. Conflicting repeated attribute values fail closed rather than invent a representation.
- The **407 derived construction inputs** remain in `derived-construction-inputs.json`, excluded from primary metrics. This small adapter consumes accepted projections only; it does not introduce the additional approved-rule consumer needed to turn those construction inputs into graph edges. They must not silently be counted as 407 accepted edges or combined with the 9,463 group admissions.
- No node is created merely to satisfy an edge. Missing endpoint IDs or conflicting exact records produce `manifest.json` with `status=blocked` and no `snapshot.json`. Investigate those references rather than dropping edges or adding placeholders.

The existing cumulative builder cannot directly concatenate these semantic projections: each semantic component references the deterministic graph, and the builder deliberately rejects duplicate IDs and non-self-contained components. The adapter therefore performs the narrowly defined exact-identity join, reuses existing snapshot validation, and uses the existing metrics CLI unchanged.

## Researcher-terminal commands

Run from the repository root in the existing environment. The first command performs the potentially long record transformation; the second measures the resulting snapshot. Neither is executed on the complete corpus inside Codex.

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python \
  -m src.evaluation.build_step13_pre_alignment

/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python \
  -m src.evaluation.compute_structural_metrics \
  var/study2_step13/pre-alignment-metrics/v1/snapshot.json \
  --label step13_semantic_pre_alignment \
  --display-name '+ Accepted semantics (pre-alignment; closure pending)' \
  --order 50 \
  --consolidation-stage pre_consolidation \
  --results-dir var/study2_step13/pre-alignment-metrics/v1/metrics
```

Run the metric command only if the first command succeeds. Snapshot preparation refuses an existing output directory, including partial output. Preserve a failed directory and its diagnostics; do not silently overwrite it. The existing metric CLI replaces its labeled result when rerun, so execute it once for the prepared immutable snapshot.

Expected ignored outputs under `var/study2_step13/pre-alignment-metrics/v1/`:

- `snapshot.json`: evaluation-only cumulative graph, only when all endpoints resolve.
- `manifest.json`: pinned inputs/implementation/ontology, mechanical counts, seven terminal exceptions and any blockers.
- `native-provenance.jsonl`: authentic accepted records, evidence, original identities and graph-ID association; potentially large, do not share wholesale.
- `derived-construction-inputs.json`: 407 unconsumed inputs and owner-report provenance.
- `historical-metric-hashes.json`: exact byte-copy checks for prior metric rows.
- `metrics/snapshots/`: byte-identical historical rows plus the new order-50 record `step13_semantic_pre_alignment.json`.
- `metrics/trajectory.md`: **ignored draft only**, containing both full and filtered views.

Share `manifest.json`, the order-50 metric JSON and ignored draft trajectory for review. Do not copy the draft into `results/metrics/trajectory.md` or commit the new metric row as final until the researcher confirms Step 13 closure. Pre-consolidation ratios describe mechanically distinct source-local records, not a measure of scientific accuracy or cross-source entity uniqueness.
