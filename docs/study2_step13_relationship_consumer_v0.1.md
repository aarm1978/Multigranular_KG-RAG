# Step 13 evaluation-only post-acceptance relationships v0.1

Authority: `step13-post-acceptance-relationships/0.1.0`. Researcher-approved implementation of existing construction responsibilities, not a metric-optimization or semantic-repair policy. The [compatibility manifest](study2_step13_relationship_consumer_v0.1.json) pins the accepted v3 snapshot, manifest, derivation inputs, read-only audit and applicable authorities. Step 13 closure remains accepted; this is not Step 14 or final KG assembly.

The separate `src.evaluation.materialize_step13_relationships` route preserves every original v3 node and edge, including Publication request-local occurrences. It appends only:

- Publication C-P05 discourse attachments, C-P10 RelatedResearch attachments, and C-P12 Paper-branch Limitation attachments from accepted occurrence evidence and exact curated Paper inventory lineage.
- Publication D-26 Paper/entity and within-request discourse/entity fallback, using accepted evidence, unique Paper provenance, exact dual-coordinate containment, and the historical policy's stronger/specialized relation precedence.
- The existing 407 non-Publication governed D-26 inputs, after owner/group hash checks, exact accepted-projection hashes, retained assertion membership, admitted supporting decisions, exact endpoints/types, authorized family target scope, literal source containment and offsets, and stronger owner-relation precedence.

The frozen Publication v0.1.5 extraction inventory, D-26 policy v0.1.1, historical materializer and production acceptance implementation are checked against their production input pins. Their guards remain unchanged. A separate compatibility manifest pins canonical ontology v0.1.7 and explicitly verifies the four applicable relation signatures. No current ontology is falsely relabeled as the historical v0.1.5 bytes. The historical materializer continues to reject its v0.1.5 policy against a v0.1.7 runtime; the new consumer reuses its exact-coordinate containment predicate without patching that guard.

Derived IDs hash the version, inventory ID and exact endpoint pair. Exact triples deduplicate without name matching. Per-rule candidate, stronger-suppressed, duplicate and emitted counts are reported. Independent derivation provenance retains original evidence, candidate/request references and construction provenance in `derivation-provenance.jsonl`; no evidence/activity nodes or provenance edges inflate the primary metric graph. Original native records remain referenced through the unchanged v3 sidecar and its hash. The new snapshot adds a distinct derivation component.

The consumer reconciles rule counts and isolation with the pinned read-only audit, failing before publishing a snapshot on unexplained differences. The expected audit union is 89,315 formerly isolated nodes connected, leaving 472; these are rule consequences, not semantic accuracy targets. No residual node is repaired automatically. Original record equality, endpoint existence, canonical signatures and deterministic output serialization are mandatory. Existing/partial output directories are refused; failed output must be preserved.

## Researcher-terminal execution

From the repository root, using the existing environment:

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python \
  -m src.evaluation.materialize_step13_relationships
```

Default fresh output: `var/study2_step13/pre-alignment-metrics/v4/`. Requires the pinned v3 snapshot/sidecar, v4.1 owner/group reports, baseline components, Publication manifest and historical input pins, and the relationship-gap audit. No response replay, source re-extraction or provider calls occur. Both socket connection entry points are blocked.

After successful completion and review of the comparison:

```bash
/Users/aramirezm/micromamba/envs/multigranular-kg/bin/python \
  -m src.evaluation.compute_structural_metrics \
  var/study2_step13/pre-alignment-metrics/v4/snapshot.json \
  --label step13_semantic_pre_alignment \
  --display-name '+ Accepted semantics and approved derivations (pre-alignment)' \
  --order 50 --consolidation-stage pre_consolidation \
  --results-dir var/study2_step13/pre-alignment-metrics/v4/metrics
```

Share `summary.json` and `summary.md`, then the ignored order-50 metric JSON and draft trajectory. The large snapshot and derivation sidecar remain local. Historical metric rows are copied unchanged into the ignored metrics directory; official `results/metrics/trajectory.md` is not modified. No full-corpus materialization or measurement is performed inside Codex. The retained 472 residual nodes require a separate researcher-reviewed examination, not a generic-mentions expansion.
