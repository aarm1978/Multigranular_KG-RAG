# Study 2 Step 14: offline semantic candidate preparation

This stage prepares comparison inputs only. It does not execute the identity preview,
compute embeddings, adjudicate similarity, assert equivalence, consolidate nodes,
rewrite edges, infer relations, measure the graph or modify Step 13.
The [frozen order-50 scope](study2_order50_frozen_scope_checkpoint.md) and ontology
v0.1.7 remain authoritative. Existing identity-preview behavior is unchanged; its
hash-verified input loader, serializer, hashing and entity-own field reader are reused.

## Inputs and preserved information

The loader checks the existing frozen v4 snapshot and summary hashes, the original
v3 native-provenance sidecar hash, v4 derivation-provenance hash, and frozen ontology
specification/OWL hashes. It reads only accepted snapshot nodes. Native node records
are individually hash-checked; non-Publication owner reports are checked against
native provenance pins to recover explicit owner endpoint IDs. No upstream extraction
or validation is rerun. Historical nonaccepted identity-sidecar records remain outside
accepted content. Derivation provenance is integrity-checked, not used to infer identity.

Each selected occurrence preserves its original ID, class/inventory ID, full original
snapshot node, attributes, literal entity version fields, native candidates, evidence
records and native provenance references. Publication `canonicalPaperID`, explicit
owner report IDs and deterministic evidence source artifacts establish origin.
Source families come from native provenance or documented deterministic lineage
(`localPaperId`, `corpusPath`, HydroShare source prefix, GitHub `rawSource`). Unknown
origins are reported as missing provenance and excluded from blocks, not guessed.
No records in the original graph are deleted, including those outside this preparation.

Two preparation lanes are separate:

- **Identity declarations:** Paper, DatasetResource, Repository, Person, Organization,
  and geographic classes. Existing deterministic entity-own identifiers and governed
  dataset C-D04 `hasIdentifier` DOI assertions are retained. Accepted source-local
  `exactIdentifier` declarations retain literal text, evidence-binding status and
  local scope; URLs are not resolved into inferred identifiers. A referenced Paper
  stub can carry its own DOI; citation strings on the citing entity cannot.
  `link_existing` remains an exact request-local declaration with no global promotion.
- **Semantic comparisons:** Tool, Algorithm, Workflow, and nonabstract descendants
  of ComputationalModel read from ontology v0.1.7. Descriptions and evidence quotations
  provide literal context in `embeddingText`. No generated description or label alias
  is added. Architecture similarity and implementation identity remain distinct.

The existing HydroShare `geoconnex-url` / `identifierValue` channel is retained only
for explicit geoconnex.us URI declarations on geographic nodes. No HUC, COMID,
GeoNames, namespace/version conversion, geographic subtype, or URI is inferred.
Historical abstract HydrologicFeature records are retained and flagged, not retyped;
they do not enter candidate blocks. Other unsupported geographic channels need a
separately justified field/namespace adapter.

## Blocking and uncertainty

NFC Unicode normalization, case folding and whitespace collapse affect lexical
blocking keys only. Original strings remain intact. Punctuation, numbers, version
suffixes and words are retained. No stemming, aliases, substring/token expansion,
transitive identity union or unrestricted pair generation occurs.

Blocks require exact ontology class/inventory compatibility and complete origin
provenance. Semantic blocks require one unambiguous normalized label. Identity
blocks use a literal identifier declaration and its scheme within one class. These
are candidate buckets, not matching decisions; semantic and identity keys are never
interchangeable. Multiple distinct labels are explicitly flagged and excluded from
lexical blocking. Different labels are not compared by this bounded first stage,
so recall is deliberately limited.

Default block cap: **32 occurrences**, configurable from 2 through 128. An oversized
block records its key, full member count and membership hash but no selected subset
or member expansion. Its membership can be recovered from occurrence records and
the recorded key. Even small blocks emit only occurrence lists, never all pairs.
Every emitted block is marked ambiguous/candidate-only and `equivalenceAsserted=false`.

Generic LSTM, a trained LSTM and an underspecified LSTM may share a block. The stage
never infers granularity from their labels or descriptions. Every record has
`granularity=unspecified_requires_context_review`, `identityDecision=not_assessed`
and `automaticMergeEligible=false`. Literal version/commit/fork conflicts are review
flags. Missing values are unknown, never evidence of identity or difference.
Evidence acquisition versions are preserved separately and are not entity versions.
Contextual/discourse classes, EvaluationMetric and Parameter are excluded from these
comparison lanes and counted by class; their original graph records stay unchanged.

## Researcher-terminal execution

From the repository root, with the existing environment:

```bash
conda run -n multigranular-kg python -m src.evaluation.step14_semantic_candidates
```

Fresh ignored output directory: `var/study2_step14/semantic-candidates/v1/`:

- `occurrences.jsonl`: embedding-ready selected occurrences, original records,
  evidence, identifier declarations and preparation flags.
- `candidate-blocks.jsonl`: bounded candidate blocks and oversized-block diagnostics.
- `manifest.json`: input/implementation/output hashes, configuration, coverage and limits.
- `report.md`: concise coverage and limitations.

Existing output directories are refused. Later runs can use `--output` with a fresh
path below `var/study2_step14/semantic-candidates/`. `--max-block-size` changes only
preparation limits and is recorded in the manifest. Identical inputs/configuration
produce identical bytes; there are no timestamps. Socket connect/connect_ex are
blocked by the CLI. Full corpus execution remains a researcher-terminal action.
No corpus coverage or alignment quality claims follow from synthetic tests.

Focused checks:

```bash
python -m unittest tests.test_step14_identity_preview tests.test_step14_semantic_candidates -v
```

Researcher review remains necessary for actual entity identity, conceptual similarity,
generic/specific implementation distinctions, version interpretation, ambiguous and
oversized blocks, missing provenance, geographic namespace rules and any future
cross-class or embedding-based candidate generation. No acceptance policy is added.
