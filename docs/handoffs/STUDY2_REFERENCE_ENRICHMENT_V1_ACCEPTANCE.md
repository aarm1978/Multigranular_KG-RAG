# Study 2 — Corrected deterministic reference-enrichment baseline acceptance

**Status: ACCEPTED on 2026-10-08**, as directed by the researcher following
ChatGPT review and recommendation. Acceptance covers the bounded deterministic
baseline, not exhaustive semantic coverage or Step 11 completion.

## Implementation and scope authorities

- Reference-enrichment candidate: `10c12279ec87b4d19d24e97ac48218b12b95f071`.
- Final homepage correction: `a1f0c3b0febc97d3c36fb95d3d17cf85f7db635c`.
- Ontology **v0.1.6**, frozen at `b2c735b`, remains unchanged.
- [Authorized scope and candidate results](STUDY2_POST_STEP10_REFERENCE_ENRICHMENT_V1.md).
- [Homepage correction fixture](../../tests/fixtures/reference_enrichment/hub_homepage_correction_v1.json),
  retaining prior candidate hashes, the three removed edges and their exact evidence.

This acceptance supersedes the scope addendum's pending-review status and its
pre-correction Hub/cumulative counts; the addendum remains intact as candidate
provenance. Step 10 remains closed at `a2cb542`; no source audit is reopened.

## Accepted results and validation checkpoint

- GitHub: **59 C-C27 referencesRepository edges**, unchanged by the correction.
- Hub: **91 C-DC22 references edges**. Three homepage-target edges were removed:
  repository contribution guide, data/code-sharing recommendations, and AWS best
  practices, each pointing to the Hub homepage. Homepage identity is derived from
  the Phase A base URL. All original Link/linksTo assertions and retained graph
  records are preserved.
- Final cumulative graph: **28,406 nodes / 32,809 edges**.
- File-inventory-excluded final graph: **15,705 nodes / 19,866 edges**.
- Candidate implementation: **130 focused tests passed**.
- Targeted correction: **10 focused tests passed**, including Hub eligibility,
  validator rejection, retained records, reproducibility, historical preservation,
  and affected cumulative/metric integration.

These results refer to the recorded implementation runs. **No tests, extraction,
reasoning, evaluation, graph rebuilding or metric generation were repeated for
this acceptance documentation.** Current full, inventory-excluded, sensitivity
and trajectory results are in `results/metrics/`, including `trajectory.md`, under
unchanged metric definitions.

## Exact accepted graph hashes

The following SHA-256 values are transcribed from the
[prospective manifest](../../tests/fixtures/reference_enrichment/prospective_hashes.json)
at the final correction checkpoint. This documentation task did not independently
rehash the graph files.

| Local artifact | SHA-256 |
|---|---|
| `data/interim/coderepos/github_nodes_edges_refs_v1.json` | `ea49b820903ae102068783c3a890632f648974f0d0e83a3688697ad618d8de3b` |
| `data/interim/datasets/hydroshare_nodes_edges_v016.json` | `4fbfcb2548f51323e9bfc83a0ea9ffa76bfa8344f9c86c4550efce7373515576` |
| `data/interim/documents/ciroh_hub_nodes_edges_refs_v1.json` | `4e2939bce4ecec0080111e5415a841b1502c56f92ca44289d88c0cb5c1235277` |
| `data/interim/evaluation/hydroshare_github_deterministic_refs_v1.json` | `57e60ab935fe1041fc80e9aca87feee024a9c28163b00776bf20f90a0bb3154c` |
| `data/interim/evaluation/hydroshare_github_hub_deterministic_refs_v1.json` | `5a3230fe1170713cc39a43802fb7970c6af55d1ad1598a3bfc5ccd3c59a4f03b` |
| `data/interim/evaluation/hydroshare_github_hub_publications_deterministic_refs_v1.json` | `b5e28c5437be2df9a615f2e17c919279dae262515def4f69458bf3547e17e127` |
| `data/interim/papers/publication_nodes_edges.json` | `675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf` |

The accepted assembly uses the unchanged HydroShare v0.1.6 graph, the accepted
GitHub graph, corrected Hub graph, and unchanged historical Publication deterministic
graph. Corpora and graph files under `data/interim/` remain gitignored local artifacts;
a repository checkout alone does not provide those inputs/outputs. Reproduction
requires the matching local artifacts and pinned hashes.

Historical source graphs, accepted HydroShare artifacts, ontology fixtures, hashes,
metrics and Publication authorities remain preserved. The
[pre-enrichment manifest](../../tests/fixtures/reference_enrichment/pre_enrichment_hashes.json)
pins the historical boundary; prior accepted metric copies remain under
`results/metrics/history/pre_reference_enrichment_v1/`. The previous unaccepted
candidate remains traceable through commit `10c1227` and the correction fixture.

## Limitations and next workstream

Generic references do **not** imply use, implementation, dependency, identity,
or scientific correctness. Conservative extraction does not establish exhaustiveness;
exact source links do not establish remote availability or stronger semantic roles.
Heuristically generated HydroShare `data_services` are **not admissible evidence**
for published DataService assertions and must not enter future LLM contracts as
verified services. DataService/WMS/WCS materialization and other optional enhancements
remain deferred pending separate researcher authorization.

Frozen Publication deterministic and evaluation authorities remain unchanged.
**Publication full-corpus semantic production is still required before Step 13
completion**; accepted evaluation and these cumulative deterministic graphs do not
satisfy that dependency. Cross-source identity resolution remains Step 14.

The next pending workstream is **Step 11 source-specific semantic extraction
contract design**, using the [accepted Step 10 decisions](STUDY2_STEP10_SEMANTIC_GAP_DECISIONS.md)
and ontology v0.1.6. Exact targets, evidence rules and abstention behavior remain
Step 11 responsibilities. This record authorizes no Step 11 implementation or
provider calls and preserves all accepted artifacts.
