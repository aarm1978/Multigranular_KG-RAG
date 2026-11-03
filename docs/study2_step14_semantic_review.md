# Study 2 Step 14: compact semantic candidate review dossier

This diagnostic consumer follows commit `4e02470` and the existing
[semantic candidate preparation contract](study2_step14_semantic_candidates.md).
It prepares evidence for review, without adjudication, embeddings, provider calls,
thresholds, identity decisions, new relations or graph changes. The frozen Step 13
acceptance and ontology v0.1.7 remain unchanged. No annotation campaign or acceptance
policy is introduced.

## Authoritative inputs and validation

Input root: `var/study2_step14/semantic-candidates/v1/`.
The existing `manifest.json` is the trust root. Its own byte hash is recorded in
the new manifest, not represented as an independently signed authority.
`occurrences.jsonl` and `candidate-blocks.jsonl` must match its `outputHashes`.
The two upstream Step 14 implementation hashes and ontology specification/OWL hashes
must also match the existing manifest before its v0.1.0 blocking rules are consumed.
Upstream corpus artifacts are not re-extracted or re-audited.

Every occurrence ID must be unique, including records outside candidate blocks.
The reader reconstructs eligible lexical and literal-identifier keys using exactly
the frozen candidate preparation rules and exclusion flags. Every reconstructed
multi-member key must correspond to exactly one original block; extra or missing
blocks fail closed. Original block IDs, cap/status, member counts, explicit member
lists and sorted-member hashes must agree. Duplicate blocks/members, unknown
mechanisms, class/inventory mismatches and missing member provenance also fail.
Oversized membership hashes are required by the current input contract and verified;
they are not silently skipped. Manifest occurrence/status coverage is reconciled.
All pinned bytes are checked again before publication to detect edits during reading.
Missing inputs or any integrity failure leave the destination uncreated.

## Classification and dossier coverage

Classification uses the union of each member's authoritative `sourceFamilies`.
Occurrence-ID prefixes play no role. Ordinary blocks with more than one family
are cross-family; remaining ordinary blocks are within-family. Oversized blocks
form a separate category and retain an independent `crossFamily` diagnostic flag.

The researcher-reported run contains 267 cross-family, 2,122 within-family and
25 oversized blocks. These numbers are context only, never hardcoded selection
limits or acceptance assertions. The terminal run recomputes them and includes
**every** cross-family ordinary block in the dossier. No corpus execution took
place during implementation, so fixture results do not independently confirm
those counts.

Each dossier block includes its ID, key, ontology class, candidate mechanism,
member count/hash, exact member IDs, family distributions, source artifacts,
original block flags and one compact record per member. Exact family-set counts
are also included: an occurrence carrying multiple families contributes to each
family's membership count, but remains one occurrence. No artifact-to-family
pairing is guessed when an occurrence has multiple origins.

Coverage is reported separately for cross-family, within-family and oversized
blocks, by ontology class, candidate mechanism and source-family combination.
Each coverage row reports block count, member-occurrence count, distinct occurrence
count and distinct recorded supporting artifact count. Artifact aliases are not
resolved. Multiple mentions from one recorded artifact count once toward distinct
artifact coverage; neither mentions nor distinct artifact IDs establish independent
corroboration.

## Scope, evidence and compactness

Identifier declarations retain their original values, basis and scope. The dossier
separately counts deterministic entity-own identifiers (including governed C-D04),
source-local literal declarations, literal geographic declarations and unsupported
scopes. Local `exactIdentifier` and request-local `link_existing` declarations never
become authoritative global identities. Lexical similarity is explicitly a separate
candidate mechanism, not an identity rule.

Original labels, versions, attributes, contextual descriptions and preparation
flags remain available. All attribute names are listed so potentially relevant
technical fields remain discoverable. Each member retains its source artifacts,
source families, original occurrence ID and a hash-bound reference to its complete
occurrence and original snapshot record. Missing identifiers, versions, descriptions,
labels, artifacts or evidence are reported as missing information, not disagreement.
Generic LSTM architecture and a particular trained implementation remain distinct
occurrences with identity unassessed, even if a label puts them in one block.

Fixed presentation limits:

- Two evidence records per member, chosen by canonical JSON ordering, with the
  original array indices retained. Each literal excerpt is at most 600 Unicode
  characters. Selection is mechanical and makes no support judgment.
- Three native provenance records per member, likewise selected deterministically.
  The full native-reference array remains referenced, with omitted counts explicit.
- Each serialized field preview is at most 1,200 characters. Short values are
  preserved verbatim; long values carry an explicitly truncated canonical-JSON
  excerpt, total character count, full-value hash and original field reference.

Full recovery: use the new manifest's `inputRoot` and pinned occurrence-file hash,
locate the exact `occurrenceID`, verify its canonical `occurrenceSha256`, then follow
the supplied JSON Pointer. Evidence entries additionally carry their full-record
hash. Metadata views identify `projectionExcludedKeys` (only `evidenceText`), so
filtered metadata hashes can be reproduced from the referenced evidence record.
Original native references lead back to accepted Step 13 provenance. The dossier
does not copy `embeddingText`, full original candidates or the full snapshot nodes.
It is a bounded view, not a substitute for reviewing omitted evidence when needed.

Oversized diagnostics reconstruct all members, verify the sorted membership hash,
and report the size, exact source-family composition and distinct artifact count.
They retain the original reconstruction key and artifact-set hash without emitting
member lists, unrestricted pairs or any selected subset. All membership can be
recovered from the pinned occurrence records with the same key rule.

## Researcher-terminal command and outputs

From the repository root in the existing environment:

```bash
conda run -n multigranular-kg python -m src.evaluation.step14_semantic_review
```

The fresh, ignored destination is `var/study2_step14/semantic-review/v1/`:

- `review-dossier.jsonl`: all ordinary cross-family blocks and bounded evidence.
- `oversized-summary.jsonl`: every oversized block with verified reconstruction.
- `manifest.json`: exact input/output/implementation hashes, presentation limits,
  computed coverage, provenance limitations and diagnostic-only status.
- `report.md`: computed classification counts, coverage table and limitations.

Existing destinations are refused. A subsequent run may use `--output` with a fresh
path under `var/study2_step14/semantic-review/`. Identical inputs produce identical
bytes; no timestamps or provider dependencies are included. No ignored outputs
belong in Git. The CLI disables socket connect/connect_ex.

Focused synthetic validation:

```bash
python -m unittest tests.test_step14_semantic_review -v
```

Tests cover provenance and full-evidence recovery, authoritative source-family
classification, local/global identifier scope, conceptual versus implementation
identity, truncation, oversized reconstruction, missing/duplicate/inconsistent
membership, frozen upstream preparer compatibility, hash checks, ordering,
reproducible writing and input preservation. Full-corpus run and substantive review
remain researcher-terminal actions.
