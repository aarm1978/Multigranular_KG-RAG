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
conda run -n multigranular-kg python -m src.evaluation.step14_alignment_opportunities
```

Fresh ignored destination: `var/study2_step14/alignment-opportunities/v1/`:

- `report.md`: denominators, opportunity tiers, queue coverage and limitations.
- `inventory.json`: compact stratified relation summaries, pilot cases and separately
  retained oversized cross-family summaries.
- `pilot-review-queue.tsv`: bounded evidence and source pointers for selected cases.
- `manifest.json`: input/output/implementation hashes and diagnostic-only status.

Existing destinations are refused; `--output` may name another fresh path below the
same diagnostic root. The CLI disables network connections. No full-corpus run took
place in Codex; actual relation coverage remains pending the researcher-terminal run.

Focused tests: `python -m unittest tests.test_step14_alignment_opportunities -v`.
Synthetic fixtures cover exact targets versus locators, owner versus reference
identity, non-promotion, class compatibility, duplicate evidence, missing provenance,
native/derived lineage, reproducible selection, zero coverage, hashes and reversible
output behavior.
