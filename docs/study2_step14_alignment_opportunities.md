# Study 2 Step 14: cross-artifact alignment opportunity diagnostic

This bounded, read-only inventory implements the researcher's revised direction:
identity consolidation and evidence-supported relation alignment need a joint
feasibility view. It does not perform either alignment operation. Step 14A remains
skipped. Frozen Step 13 acceptance, ontology v0.1.7, the v4 graph, order-50 metrics
and all existing Step 14 outputs remain unchanged.

## Inputs and authorities

The diagnostic reuses `step14_identity_preview.verified_inputs` to verify and load
the frozen v4 snapshot, summary, original native sidecar, derivation sidecar and
ontology hashes. It uses the pinned semantic-review dossier, oversized summaries,
and existing identifier triage. The saved triage manifest hash is
`529ffeddd981461fddeabdaa539a6758cae7a653f3378f1cc4b4aae4574e01d3`.
Review-manifest, candidate-manifest and ontology links are checked by the existing
triage input verifier. The triage implementation hash is checked against its saved
manifest. These local pins are integrity checkpoints, not independent signatures.
No candidate discovery, extraction, metric computation or review regeneration occurs.

Existing accepted relation representations are consumed as follows:

- Deterministic graph edges: inline evidence and original source metadata.
- Accepted authored semantic edges: immutable native records indexed by exact
  `graphID`, with each native-record hash checked. Non-Publication owner-report
  paths/hashes recover explicit owner IDs. Publication evidence retains canonical
  Paper IDs and request provenance.
- Pipeline-derived accepted edges: only `disposition=emitted` records in the pinned
  derivation sidecar. Their existing evidence, derivation rule and original record
  hash remain traceable. Suppressed/duplicate derivation proposals are not counted
  as new accepted edges.

No source family is inferred from occurrence-ID prefixes. Native provenance,
existing deterministic lineage discriminators and the governed derivation rule
supply families. Inline edge evidence may recover its family by exact
`sourceArtifact` lookup in documentary node origins; graph adjacency is not used
as a substitute for source provenance. Unavailable origins stay unresolved.

## Denominators and opportunity tiers

Every v4 edge ID is counted once as an accepted relation occurrence, including
records outside the opportunity scope or with incomplete provenance/signatures.
Predicate and source-family-set totals partition that denominator. Multi-family
sets are reported explicitly rather than multiplying edge counts across families.
Repeated native support records do not multiply graph-edge counts.

Potentially relevant targets include Paper, DatasetResource, Repository,
DocumentationPage, DatasetMention, Tool, Algorithm, Workflow, concrete
ComputationalModel subclasses, existing referenced/stub records, and endpoints
in the already prepared manageable candidate blocks. Other target classes remain
in the denominator as `outside_target_scope`. This bounded target-oriented view
does not claim every possible future cross-artifact relation direction is covered.

For relevant targets, the mutually exclusive descriptive tiers are:

- **a — explicit external target:** an accepted edge directly targets an existing
  independently observed curated artifact, or a referenced artifact with an
  existing deterministic entity-own identifier. The latter identifies an external
  reference target but need not connect to an independently observed artifact.
- **b — strong record candidate to observed artifact:** an existing non-owner
  reference/stub endpoint participates in a previously prepared, unadjudicated
  strong identifier block with a class-compatible curated artifact from a distinct
  recorded source family and artifact. No additional identifier matching is run.
- **c — exact locator coincidence only:** an existing local-literal identifier
  block supplies a class-compatible cross-origin peer. It remains locator evidence,
  not semantic entity or implementation identity, including previously unresolved
  locator scopes.
- **d — contextual/lexical unverified:** an existing manageable lexical block
  supplies a class-compatible cross-origin peer. Neither the target identity nor
  conceptual/implementation equivalence has been established.
- **e — unresolved/ambiguous:** no supported tier applies, or accepted edge evidence,
  endpoint provenance or exact ontology signature is unresolved/incompatible.

Source and target origins must be recorded; family and artifact sets must be
disjoint to count an independently observed target or possible cross-family peer.
An independently observed owner is an existing **curated artifact-class node**
with documentary origin; evidence on a referenced stub is not owner status.
An owning artifact's DOI/source URL is never transferred to a mentioned entity.

The report separately counts direct accepted connections to curated independent
artifact endpoints, possible cross-family opportunities by tier, complete versus
unresolved source/target provenance, and schema-level `cross` annotations. Schema
`cross` is not instance evidence. Class checks use exact relation inventory IDs,
names, declared class ancestry and explicit ontology class aliases only. Unknown
historical signature IDs and incompatible records are reported, not repaired,
rejected from frozen acceptance or silently matched to another relation.

**The exact accepted predicate is always preserved.** `mentionsTool` never becomes
`usesTool`; `referencesRepository` never becomes `hasCodeRepository`;
`referencesDataset` never becomes `usesDataset`. Locators, names, co-occurrence and
graph proximity never create or strengthen an assertion.

## Evidence and compactness

“Confirmed provenance” means existing recorded evidence plus a traceable source
family/artifact, not semantic correctness, literal rebinding or independent
validation. Reused exact quotation hashes are counted across accepted edge IDs;
multiple mentions, repeated quotations or mirrored documents are never treated as
independent corroboration. Source-local records that cannot establish endpoint
origins remain unresolved, with no fallback relation.

`inventory.json` contains counts grouped by exact predicate/inventory, source family
set, evidence tier, signature status, provenance completeness and cross-family
opportunity status. Each group retains only its first two lexicographic edge IDs
and bounded source/target/evidence recovery references. Full evidence stays in the
pinned graph and sidecars. Native references recover by `graphID` and native-record
hash; derivation references recover by edge ID and record hash. Examples are not a
new acceptance sample and the diagnostic is not a full duplicated edge export.
These structural counts are neither precision nor recall.

## Lexical pilot and oversized blocks

The pilot uses only saved manageable lexical cross-family dossier blocks. All
members must have recorded source families/artifacts and existing evidence excerpts.
It selects at most **30 cases** by round-robin ontology class, with Tool, Algorithm,
MLModel, ProcessBasedModel and ConceptualModel first, followed by other available
classes. Within each class it round-robins exact source-family combinations. Within
a stratum, blocks with incident evidence-backed signature-compatible accepted
relations precede other blocks; block ID breaks ties. Selection is deterministic
coverage sampling, not randomized or statistically representative evaluation.

Each selected case retains complete original occurrence membership/hash, existing
block flags, incident **unchanged** accepted predicates and the dossier-block hash.
For a compact display, the first occurrence ID per family supplies one existing
evidence excerpt capped at 400 characters and its exact recovery pointers. This
representative display does not claim to cover every member's evidence. The full
membership remains reviewable in the pinned dossier. Identities stay unadjudicated.
Fewer cases are selected when fewer are supported; missing strata are not imputed.

Oversized cross-family summaries are retained separately with their saved counts,
keys and hashes. Their members are not reconstructed or expanded for this pilot.
The reported totals (including lexical and oversized coverage) are derived from the
saved data, not hardcoded to the researcher's observed run.

## Researcher-terminal command and outputs

From the repository root in the existing environment:

```bash
python -m src.evaluation.step14_alignment_opportunities
```

Fresh ignored v2 destination: `var/study2_step14/alignment-opportunities/v2/` (v1 is never overwritten):

- `report.md`: denominators, opportunity tiers, queue coverage and limitations.
- `inventory.json`: compact stratified relation summaries, pilot cases and separately
  retained oversized cross-family summaries.
- `pilot-review-queue.tsv`: bounded evidence and source pointers for selected cases.
- `shared-reference-hubs.jsonl`: provisional exact-key groups, distinct documentary referrers, unchanged predicates, versions and bounded recovery pointers.
- `manifest.json`: input/output/implementation hashes and diagnostic-only status.

Existing destinations are refused; `--output` may name another fresh path below the
same diagnostic root. The CLI disables network connections. No full-corpus run took
place in Codex; v2 relation coverage remains pending the researcher-terminal run.

Focused tests: `python -m unittest tests.test_step14_alignment_opportunities tests.test_step14_shared_references -v`.
Synthetic fixtures cover exact targets versus locators, owner versus reference
identity, non-promotion, class compatibility, duplicate evidence, missing provenance,
native/derived lineage, reproducible selection, zero coverage, hashes and reversible
output behavior.


## v2: exact GitHub provenance recovery

A bounded inspection of eight frozen curated Repository roots and nine accepted
edge examples found that `RepoContext.lineage("repo root")` deliberately omits
optional `rawSource`. The v1 family discriminator required that field for GitHub,
although each sampled root had its original numeric repository ID, full name,
HTML URL, canonical key, repo-root lineage and deterministic metadata evidence.
All eight pass the new exact constructor-contract check. No provenance is inferred
from graph IDs, labels, neighbors or a URL prefix.

The recovery requires `A-C01`/Repository, curated status, positive integer repoId,
`github_numeric_id`, matching `github-repo-id:` canonical key, fullName/htmlUrl
agreement, `phaseAField=repo root`, phaseAVersion, and matching metadata evidence
sourceArtifact/API sourceLocation, extractionMethod, evidenceText and version.
Other absent provenance stays unresolved. The new source/target recovery counters
measure endpoint occurrences restored by this rule, not accepted alignments.

The hash-verified saved v1 inventory contains 551 source-unconfirmed occurrences
across referencesDataset, usesDataset, referencesRepository, referencePublication,
usesTool and usesModel. Of these, 527 have compatible signatures and confirmed
target provenance (35, 92, 36, 48, 276 and 40 respectively). Another 99 implementedBy
occurrences have unconfirmed target provenance. These counts identify potential
suppression; only the researcher-run v2 can measure opportunity changes. A sampled
referencePublication edge (`github:edge:referencePublication:78085a50fecd916924e6`)
has original CITATION.cff evidence and its Paper stub's own DOI, while its curated
repository source was unconfirmed. Missing family classification is distinct from
missing evidence on the source-local projected semantic nodes, whose evidence is
in the immutable native sidecar.

The 11,702 GitHub hasFile occurrences have the separate historical File-versus-
RepoFile signature incompatibility. Recovering repository provenance does not make
their signatures compatible or change frozen acceptance. The remaining unknown
historical relation signatures are also left unchanged.

## v2: shared external-reference groups

This diagnostic reads all v4 targets in Paper, DatasetResource, Repository, Tool
and Dependency, including targets absent from the previous semantic preparation.
The implementation explicitly lists eligible accepted predicates and independently
requires their exact ontology signature and recorded edge evidence. Exclusions
remain in denominators. Groups never create entities, edges or pairwise connections.

- **A:** existing typed own DOI, HydroShare resource ID, GitHub numeric ID, or an
  explicitly established `github_repository_url` root. The original constructor's
  canonical-key wrappers are read without URL resolution or new normalization.
  A fully verified curated GitHub root also supplies its recorded root URL. These
  are repository-record keys, never commit/implementation equivalences. Existing
  software/repository DOI regimes and accepted DatasetResource hasIdentifier DOI
  assertions retain record scope.
- **B:** exact target locator fields and original evidence-bound local literal
  declarations. GitHub branch/file/clone locators remain distinct from root keys;
  DOI resolver URLs and HydroShare resource URLs are not promoted to record IDs.
- **C:** ecosystem-qualified package declarations without proven registry/release
  identity, or exact original names when no stronger key exists. No alias/fuzzy
  expansion occurs. Package `versionSpec` is read from the accepted dependsOn edge;
  absent or divergent constraints are retained, not silently reconciled.

Each key is grouped within its target class and scope. Multiple keys can describe
the same target; group totals overlap and are not unioned transitively. Separate
accepted-edge denominators and shared-edge counts deduplicate original edge IDs.
Singleton groups remain visible to distinguish possible from observed shared hubs.
Matching curated-artifact IDs are exact A-key candidates, never adjudications.

Referrers resolve only through original curated-artifact fields and evidence,
including explicit native owner IDs and accepted sourceDeclarations. GitHub file
sourceArtifact tree/SHA, sourceLocation blob/SHA/path and evidence.version must
agree with an explicitly recorded curated repository root. Root metadata and file
snapshots then count as one original artifact. Ambiguous aliases and unavailable
owners remain unresolved; edge source adjacency is not a fallback. Explicit
materialized_repository_file mirror pages are conservatively excluded from distinct
referrer counts, with their IDs reported. Undocumented mirrors cannot be inferred.
Distinct originating artifacts are documentary counts, never independent scientific
confirmation, even when their quotations differ. Repeated edges or quotations from
one artifact cannot inflate that artifact count.

Outputs preserve target IDs, exact predicates, identifier scopes, version variants,
origin IDs/families, membership hashes and bounded graph/native evidence references.
The pinned inputs recover complete edge membership by the same deterministic rules;
no raw evidence dump or high-degree artifact-pair expansion is written. Shared
citations imply neither shared methods nor functional/scientific equivalence.
