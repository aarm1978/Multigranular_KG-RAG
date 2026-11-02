# Study 2 order-50 frozen-scope pre-alignment checkpoint

Researcher-authorized promotion, 2026-10-30. Inspection HEAD: `c0469f8daa2a0920bd6fa95e4897d63a3ab66f63`. Step 13 remains [CLOSED / ACCEPTED](handoffs/STUDY2_STEP13_COMPLETION_ACCEPTANCE.md). Step 14 alignment is a separate authorized workstream and has not begun here.

The existing v4 order-50 JSON was copied **byte-for-byte** to `results/metrics/snapshots/step13_semantic_pre_alignment.json`. The existing trajectory renderer regenerated `results/metrics/trajectory.md` from saved records only; no full-corpus metric computation or graph construction occurred.

| View | Nodes | Edges | Information density | Relational richness |
|---|---:|---:|---:|---:|
| Full | 215,653 | 337,562 | 4.471021 | 1.617979 |
| File-inventory-excluded | 202,952 | 324,619 | 4.495861 | 1.653825 |

## Verified provenance

Local v4 root: `var/study2_step13/pre-alignment-metrics/v4/`.

| Artifact | SHA-256 |
|---|---|
| v4 snapshot.json; matches recorded metric input | `1f3e3ca0ba8d6e012652ab986875a994aa2ba700cb0cdd8ddb409d99c6238209` |
| v4 summary.json; matches metric component pin | `6de09a028ca9dde1f0053b4f0e16f3f239ae2efd5dfa3fc78650bd835b7791c5` |
| Original and promoted order-50 metric JSON | `d98c065cc0f0bc78aa40e7552bdb809de2a44a11d02bf19abe2a0c77e137a43e` |
| Relationship consumer authority v0.1 JSON; matches summary | `9e7e61c6a6caa16dcc93ac4f9e14ec82ff6d89001be8fda97dd4d12402df921d` |
| v4 derivation-provenance.jsonl; matches summary | `4ffbffa5b9c275721af3a8b3ec1e4f91811d267f35a59c04ecd792e1f3b5df3e` |

The metric file hash is recorded here as a promotion integrity anchor; it is not claimed to have been independently signed before measurement. Snapshot, summary, derivation-sidecar and residual-review input pins reconcile. All historical graph inputs match their recorded metric hashes. Canonical ontology v0.1.7 and historical extraction versions retain their existing authorities.

Historical metric files under `results/metrics/snapshots/` remain byte-identical to the saved pre-alignment historical hash manifest and v4's historical copies:

| Order / filename | SHA-256 |
|---|---|
| 10 / hydroshare_deterministic.json | `f170423aef593bfb7d5832b7139c181512f216c0d73fe2aa77ac0da92e41c3fd` |
| 20 / hydroshare_github_deterministic.json | `504dfd9e5c6f97fdf4de83b7d4f33f917b98e34769a83d5c1cd6afd4dace8f73` |
| 30 / hydroshare_github_hub_deterministic.json | `dd26b5913e678373ebda899fca0a41d4fb3d5e2eb3b847c3bad891b468fb6569` |
| 40 / hydroshare_github_hub_publications_deterministic.json | `3e5529be4338455098da92b0edbf2db9f6ef9c79f802496a2fec34ab4d6a9ba3` |

## Frozen scope and limitations

The [versioned consumer](study2_step13_relationship_consumer_v0.1.md) added **211,329 already-approved derived edges** and suppressed **67,928 generic mentions** by stronger-relation precedence. It preserved original nodes/edges and historical evidence. Counts include request-local Publication occurrences and existing exact owner consolidation, not globally unique real-world entities. Information density and relational richness describe structure; neither demonstrates accuracy, completeness, precision or recall.

The read-only residual review at `var/study2_step13/residual-source-anchoring/v1/` reconciles **472 zero-degree nodes**: 445 literal evidence-bound occurrences outside active family D-26 profiles, four Hub provenance-only records, and 23 deterministic Publication bibliographic Tool stubs. No missing active D-26 input or clearly justified existing-rule repair was established within that audit's scope. Literal binding is not independent semantic certification. Original held relations, typing uncertainties and source restrictions remain in effect; seven Publications terminal exceptions and the three v4.1 reviewer corrections remain unchanged.

The **445 potential weak-mention extensions remain a separately governed prospective option**. Ontology-valid signatures alone do not authorize new operational targets. No profile expansion, blanket mentions, new relationships or residual repair accompanies this promotion. Frozen-scope acceptance does not promise zero isolated nodes.

## Step 15 provenance obligation

During separately authorized Step 15 assembly, **every retained entity should have an explicitly navigable, evidence-grounded source provenance path**, preserving exact source identity, evidence locations/hashes, extraction or derivation lineage and original candidate identities. This provenance infrastructure is separate from ontology-authorized substantive semantic relationships; it must not fabricate use, citation, execution or generic-mention assertions merely to connect a node.

A zero-degree audit alone is **not a complete source-reachability audit**. A node may be connected to other entities yet lack a valid path to its originating source. Step 15 must check source-specific navigability for all retained entities, including connected nodes, and distinguish documentary provenance paths from arbitrary graph connectivity. The implementation and representation of that infrastructure require the Step 15 workstream; nothing is assembled or aligned in this milestone.
