# Step 13 pre-alignment structural checkpoint — execution preparation

This is an **evaluation-only**, provisional order-50 checkpoint after the frozen order-40 deterministic graph (28,406 nodes / 32,809 edges). It does not close Step 13, perform Step 14 alignment, or construct the final KG. The twelve-case human review remains pending. It implements the cumulative checkpoint specified in `docs/evaluation_decisions.md`; the historical trajectory and metric policy are unchanged.

## Mechanical transformation

`src/evaluation/build_step13_pre_alignment.py` consumes the existing v4.1 owner consolidations and the latest persisted Publications outcomes. It verifies native report/projection hashes, Publications' pinned journal bytes and chain/head, selected request coverage, original terminal exceptions, and the deterministic snapshot hash. It never calls extraction, semantic validation or provider transport. Original historical authorities are retained; the evaluation manifest pins canonical ontology v0.1.7 and its frozen OWL hash.

- Existing deterministic nodes/edges retain their exact IDs and attributes.
- Non-Publication owner records already consolidate exact endpoint/typed-triple identities. Their native endpoint IDs and source-local edge IDs are reused. All original supporting group records remain in a provenance sidecar.
- Publications' native `requestID#node#candidateID` and `requestID#edge#candidateID` identities remain intact. Repeated occurrences of an identical ID/structural record are one graph record with multiple provenance records. Same labels or quotations across different request IDs do **not** establish equivalence. The 182,255 accepted node occurrences and 89,021 edge occurrences are input checks, not a claim of distinct final KG entities. Conflicting values under the same native ID block output; no preferred record is selected silently.
- A Publication `deterministic:` wrapper is a serialized endpoint reference, not a new node. Its explicit `referenceID` must identify an existing graph node. For the owning curated Paper, the request-manifest inventory `paperID` maps to the existing deterministic node's `internalLineage.localPaperId`; `canonicalArtifactId` and source-artifact evidence must also match exactly. This is a same-source inventory-lineage check, not DOI normalization, canonical-key matching, stub resolution or cross-source alignment. Original wrapper IDs and the graph endpoint mapping remain in provenance. Other missing references remain blockers.
- Semantic node attributes use the literal candidate label and explicit attribute key/value fields. Evidence, request metadata, authority hashes and native records are stored outside `attributes` to avoid inflating information density. The unchanged evaluator supplies all administrative exclusions and full/file-inventory-excluded filtering. Repeated attribute names preserve all distinct literal JSON values in a deterministic list (ordered by canonical JSON bytes); identical values collapse in the metric projection only. Single-valued keys remain scalar. Every original attribute entry and its evidence remain unchanged in the native sidecar. Each informative key still counts once. Conflicting separate records under the same exact node identity remain blockers.
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

## Bounded attribute correction and identity interpretation (2026-10-30)

The interrupted `v1/` execution must remain unchanged. For the corrected transformation use a fresh directory:

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python -m src.evaluation.build_step13_pre_alignment --output var/study2_step13/pre-alignment-metrics/v2
```

After successful transformation, the existing metric command above can use `v2` in both paths. It must remain an evaluation-only record; no historical trajectory update is authorized by this correction.

**Exact endpoint inspection:** `publication_evidence_validation_contract.md` §10.3 requires `link_existing.existingNodeID` to identify an exact authorized deterministic or accepted local endpoint. Linking does not create or merge that endpoint. The frozen `production_acceptance.py` projection nevertheless serializes each accepted candidate as `requestID#node#candidateID`. This adapter preserves that serialization without inspecting `action`, including for `link_existing`. It is consistent with the declared request-local occurrence unit, but counts repeated linking assertions as additional nodes alongside their existing endpoints. Consequently the mixed deterministic-node/semantic-occurrence snapshot is not a distinct-entity structural measurement; connectivity and density inherit that representation limitation.

`publication_step5_evaluation_authority_v0.1.1.md` §Authority B permits governed exact `link_existing` consolidation within a source artifact using target, action, existingNodeID and structured attributes. That evaluation authority must not silently become a new snapshot identity rule. No such consolidation or edge retargeting is implemented here. Researcher confirmation is required before treating this occurrence-based snapshot as the intended dissertation structural checkpoint, or separately authorizing an exact-endpoint projection rule (not fuzzy or semantic alignment). Attribute correction alone does not settle that measurement decision.

Step 13 closure is now recorded separately in `handoffs/STUDY2_STEP13_COMPLETION_ACCEPTANCE.md`; older pending-closure text and adapter manifest labels reflect the preparation checkpoint and are not changed by this attribute-only patch.

## v3 endpoint/consolidation correction

Adapter version `step13-evaluation-pre-alignment/0.1.1` addresses the saved v2 manifest's 138 blockers. Bounded checks verified all 17 conflicting IDs against hash-checked v4.1 owner records: 12 GitHub and five HydroShare cases have matching exact IDs, classes, inventory IDs and non-label attributes, with different literal labels. The adapter now projects each existing consolidated node with sorted distinct label variants (scalar for one), retaining every native occurrence and its evidence in the sidecar. Label still contributes one informative key. Any other incompatibility fails closed. This is consumption of existing owner consolidation, not new identity resolution.

All 121 missing endpoints are members of the existing authorized `purpose_vocabulary()`. Exactly six shared `RepositoryPurpose` seeds are materialized with their original stable IDs and A-C07 type. Their label/definition are semantic attributes; scheme, category and contract metadata remain in native provenance, outside informative attributes. No LLM evidence is fabricated. Existing exact-ID collisions still block output. Vocabulary/profile implementations are pinned in the manifest.

Preserve failed v1/v2 directories. Run from the repository root:

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python -m src.evaluation.build_step13_pre_alignment --output var/study2_step13/pre-alignment-metrics/v3
```

Only after successful preparation, measure the ignored snapshot with the unchanged evaluator:

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python -m src.evaluation.compute_structural_metrics var/study2_step13/pre-alignment-metrics/v3/snapshot.json --label step13_semantic_pre_alignment --display-name '+ Accepted semantics (pre-alignment occurrences)' --order 50 --consolidation-stage pre_consolidation --results-dir var/study2_step13/pre-alignment-metrics/v3/metrics
```

Output layout is unchanged, now under v3. Publication request-local occurrences, all accepted edges and the 407 separately excluded derived inputs are unchanged. The previously documented occurrence-versus-distinct-entity interpretation remains; these corrections do not authorize Publication identity consolidation. The accepted Step 13 closure is preserved. Neither full transformation nor measurement was executed inside Codex.
