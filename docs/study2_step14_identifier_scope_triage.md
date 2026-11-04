# Study 2 Step 14: identifier-scope triage preview

This deterministic, read-only consumer follows the
[semantic review dossier](study2_step14_semantic_review.md) at `dc66b66`.
It implements the researcher's identifier-only diagnostic decision contract.
Recommendations remain unadjudicated; no equivalences, canonical IDs, graph writes,
scientific relations, embeddings or provider calls are produced.

## Frozen input boundary

Only `identifier_declaration_only` records from
`var/study2_step14/semantic-review/v1/review-dossier.jsonl` are processed.
Lexical blocks are counted as skipped, without inspecting or expanding their
members. The oversized file is not consumed. Candidate discovery and membership
reconstruction from the full occurrence dataset are not repeated.

The current existing review manifest is pinned by SHA-256:
`2ef9062cac151ed73342e39793cbedd76e4e631ca37a3e2c3b448d95bf59ae69`.
This is an explicit local input-integrity checkpoint, not an independent signature.
The reader refuses any different manifest. It verifies the dossier hash, the saved
review implementation hash, the pinned candidate manifest, its occurrence/block
hash links, and the ontology specification/OWL hashes for frozen v0.1.7.
It does not reread the full occurrence corpus or original Step 13 files.
Pinned bytes are rechecked before writing fresh outputs. Existing destinations,
missing files, inconsistent manifests, member counts/hashes, duplicate block IDs,
source-family distributions and complete bounded-field hash mismatches fail closed.
A genuinely new upstream run requires an explicitly reviewed input-pin update;
there is no automatic repair, regeneration or accept-new-hash option.

All counts come from the consumed data. No expected category, identifier-block,
lexical-block or oversized-block totals control selection or acceptance.

## Scientific interpretation

Three levels remain distinct:

1. **Entity identity:** occurrences may denote one entity at compatible granularity.
   Exact authoritative entity-own DOI or HydroShare resource identifiers supply
   strong candidates, subject to the guards below. They are not accepted identities.
2. **Reference-target identity:** occurrences can point to one identifiable target
   while versions, implementations and scientific content remain undetermined.
   Source-local literal matches provide only exact-locator coincidence in this pass.
3. **Conceptual identity:** shared product, method, model family or architecture
   identity is outside this pass. Generic and trained LSTM implementations are not
   identified merely because of a shared label.

Provisional categories:

- `strong_record_identity_candidate`: every member's exact key declaration has
  deterministic entity-own basis (`deterministic_entity_own_field` or governed
  `C-D04`), with no local scope; DOI is on Paper/DatasetResource or HydroShare ID
  on DatasetResource; the original class/inventory pairs agree; no detected
  material identifier/version contradiction, truncated declaration/version field,
  unsupported scope or missing evidence excerpt is present.
- `exact_locator_candidate_only`: matching complete declarations include accepted,
  evidence-bound source-local literals, without the above material flags, and
  their explicit syntax describes a recognizable locator. Mixed local/own evidence
  cannot qualify for the strong category. Equal URL text never becomes equivalence.
- `unresolved_requires_context`: material flags, unsupported identifier/class rules,
  unavailable declaration/version detail or unclear target scope prevent the above
  diagnostic recommendations. Other identifiers are not automatically granted the
  DOI/HydroShare strong rule.

Missing versions alone never invalidate record-level identity. Version differences
are review flags, not proof of distinct entities. Literal description and label
variation is flagged as potentially conflicting, without semantic contradiction
judgments or similarity thresholds; it does not by itself overturn an otherwise
strong own-identifier candidate. Granularity stays unresolved where the dossier
has not established it. Every category requires researcher judgment before any
future alignment action.

## Locator syntax and narrow cross-block relationships

Original strings, query/fragment text and path case are preserved. No URL decoding,
redirect following, alias expansion or canonicalization occurs.

- GitHub repository root, `.git` clone, `tree` branch/directory path and `blob`/`raw`
  file path are distinct. Branch/reference boundaries are not inferred beyond the
  literal path pattern.
- HydroShare resource IDs and exact `/resource/<32 lowercase hex>` URLs are distinct.
- Bare DOI identifiers and doi.org/dx.doi.org resolver URLs are distinct.
- S3 bucket-root syntax, directory/prefix syntax and specific object-key syntax
  are distinguished. Generic download extensions, directory/site roots, explicit
  index/catalog paths, and registry/portal paths are recorded separately.
- Query/fragment locators, encoded/nonliteral paths, unfamiliar URL paths and
  unknown literals require context. A bucket root is not a fixed downloadable
  object; no claim about its actual contents, mutability or service behavior is made.

Indexed cross-block relationships are limited to: exact HydroShare ID versus its
literal resource-URL path, exact DOI versus its resolver-URL path, and exact GitHub
repository path versus the `.git` path variant. Only counterpart syntax categories
are linked, with class compatibility separately recorded. Trees/files do not
inherit root/clone equivalence. These output annotations are possible syntactic
relationships requiring review, not KG edges or equivalences. A syntax group above
32 blocks is flagged and not expanded; no selected subset is silently substituted.

## Evidence, uncertainty and queue

Each triage record retains the original block key/ID, exact occurrence list,
membership hash, class, source-family distribution, declarations and scope,
locator syntax, risk flags, possible relationships and category. Member entries
retain the dossier's bounded labels/versions/descriptions, evidence excerpts,
original provenance references and original occurrence references. A block hash
locates the complete original dossier record. Full evidence recovery follows the
existing dossier references and manifest chain; truncated content is never guessed.

Exact full evidence hashes and exact complete quotation strings are checked for
reuse across source families within each selected block. A matching truncated
excerpt is explicitly only a shared prefix, not proof of equal full evidence.
Omitted/truncated evidence is flagged as incomplete reuse coverage. No mirror is
inferred from a quotation alone. Mirrored documentation, repeated quotations and
multiple source artifacts never contribute an independent-confirmation score.
Distinct artifact IDs are documentary coverage only.

`review-queue.tsv` contains every selected block, ordered by unresolved cases first,
then locator-only candidates, then strong candidates; within each category, more
risk flags appear first with block ID breaking ties. This is a diagnostic review
queue, not a new annotation campaign or acceptance policy.

## Researcher-terminal execution

From the repository root in the existing environment:

```bash
conda run -n multigranular-kg python -m src.evaluation.step14_identifier_scope_triage
```

Fresh ignored output root: `var/study2_step14/identifier-scope-triage/v1/`.

- `identifier-triage.jsonl`: one compact diagnostic record per identifier block.
- `review-queue.tsv`: categories, exact locator, risks and relationship counts.
- `report.md`: computed category/occurrence coverage and uncertainty limitations.
- `manifest.json`: input/implementation/output hashes and diagnostic-only status.

A subsequent run can select a fresh directory under the same triage root with
`--output`. Identical inputs yield identical bytes. No full-corpus run occurred in
Codex; actual coverage and recommendations await the researcher's terminal run.

Focused synthetic validation:

```bash
python -m unittest tests.test_step14_identifier_scope_triage -v
```

Fixtures cover own/local scope, class compatibility, URL variants, dynamic versus
specific locator syntax, cross-block annotations, label/description divergence,
missing/conflicting versions, reused evidence, truncation, provenance/membership,
hash verification, deterministic ordering, input preservation and fresh outputs.
