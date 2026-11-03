# Study 2 Step 14: bounded deterministic identity preview

This additive, offline consumer reads the existing frozen v4 snapshot and its
hash-pinned original native provenance and derivation sidecars. It does not build
an aligned graph, retarget edges, infer relations, run metrics or alter Step 13
acceptance, ontology v0.1.7, original assertions, provider outputs or source IDs.
The [order-50 frozen scope](study2_order50_frozen_scope_checkpoint.md) remains intact.

## Implemented boundary

The deterministic extractors establish entity-own fields used here:

- `extract_hydroshare.py`: `extract_dataset_resource` / `resourceId`,
  `extract_resource_identifiers` / C-D04 own DOI, `add_paper_stub` / typed Paper DOI,
  `best_person_key` / ORCID, `organization_id` / ROR.
- `extract_github.py`: `repository_node` / numeric `repoId`,
  `github_numeric_id` and agreeing `canonicalKey`; `seed_cff_authors_and_organizations`
  / own ORCID; validated typed Paper DOI and DatasetResource HydroShare keys.
- `extract_publication.py`: typed deterministic DOI targets and
  `ensure_hydroshare_target`; source-local DatasetMention keys are not dataset identities.

Only deterministic records with documentary evidence and curated/referenced status
are eligible. Semantic records found in the original native sidecar stay source-local.
Exact canonical values are compared; DOI URL/case repair, repository URL-to-numeric-ID
lookup, fuzzy names and identifier extraction from citation strings are not performed.
A cited typed Paper stub can match the Paper it identifies; its citing owner cannot
inherit that DOI. DatasetMention, Tool bibliographic stubs and Identifier nodes are
not promoted into Paper/DatasetResource identities. Geographic identifiers remain
unimplemented pending a governed namespace/version and concrete-class identity rule.

Connected exact-key groups must have one exact ontology class/inventory pair and
at most one value per identifier namespace. Contradictory bridges withhold the
whole group. Entity `version`, `versionNumber`, `commitSHA`, `fork`, and `forkParent`
differences (including missing versus present values) withhold proposals. Evidence
acquisition versions are not entity versions. This is a conservative preview guard,
not a determination that distinct versions necessarily mean distinct real-world entities.
Subclass compatibility and version reconciliation need researcher review.

Publication `link_existing` follows [validation contract §10.3](publication_evidence_validation_contract.md#103-link_existing):
the exact declared target is retained, but no request-context authorization is inferred
from matching strings in the global occurrence snapshot. These cases stay unresolved;
no local candidate ID is treated as a global identity. Frozen nonaccepted
`POSSIBLE_LOCAL_DUPLICATE` identity-sidecar records remain excluded; their upstream
sidecars are neither regenerated nor admitted. Implementing a request-context-aware
link preview would require an additional bounded adapter, not an identity assumption.

Preview canonical IDs are hashes of class and exact identifier sets, in an explicitly
provisional namespace. They are review labels, not final canonical KG identifiers.
Every v4 node receives a mapping row, with null canonical ID for unresolved/conflicting
cases. Each row retains its exact occurrence ID, snapshot-record hash and native
record/provenance references. Original evidence and assertions remain in the pinned
inputs, not rewritten copies. Groups list documentary source artifacts; these are
provenance origins, not an assertion of independent cross-family corroboration.

## Researcher-terminal execution

From the repository root, using the existing `multigranular-kg` environment:

```bash
conda run -n multigranular-kg python -m src.evaluation.step14_identity_preview
```

Default ignored outputs (fresh directory required):

- `var/study2_step14/identity-preview/v1/preview.json`: mappings, matched groups,
  conflicts, unresolved counts, rule coverage, blockers and immutable input hashes.
- `var/study2_step14/identity-preview/v1/report.md`: concise counts and review limits.

An existing output directory is refused. For a later run select another fresh path
under `var/study2_step14/` with `--output`. No metric or graph files are emitted.
The CLI blocks socket connect/connect_ex. Full corpus execution is reserved for the
researcher's terminal; no corpus match counts are claimed from fixture results.

Focused validation: `python -m unittest tests.test_step14_identity_preview -v`.
The fixtures cover accepted exact IDs, class/role conflicts, nonidentity references,
Publication local/link occurrences, names/provisional scopes, version ambiguity,
contradictory multi-key bridges, input preservation, ordering, hashes and output boundaries.

The separate [semantic candidate preparation stage](study2_step14_semantic_candidates.md)
reuses the verified input loader without executing these identity proposals.
