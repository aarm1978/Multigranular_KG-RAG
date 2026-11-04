# Step 14 bounded semantic identity review pilot

This is an **unadjudicated preparation contract**, authorized for the saved v2
checkpoint at implementation commit `5e9bae3`. It neither replaces Step 13
acceptance nor authorizes production consolidation. The ontology remains v0.1.7;
[order-50 scope](study2_order50_frozen_scope_checkpoint.md), original assertions,
source-local IDs, evidence and historical authorities remain immutable. Step 14A
is skipped. No provider requests, identity decisions, graph writes, sameAs,
canonical node allocation or scientific relations occur in this component.

## Fixed candidate universe and deduplication

Use only saved cross-family tier-A shared-reference rows with multiple target IDs,
all saved cross-family tier-B rows, and the existing 30-case lexical pilotQueue.
The manifest-pinned current selection has eight A and five B rows; counts are
computed from saved data, not used to manufacture cases. Oversized and other
lexical blocks are outside this pilot. No discovery or revised sampling is run.

V2 shared-reference rows have no explicit groupID. Preserve their original
identifier scheme/value, class/scope, row hash and source file/line. A
`v2-row-sha256:` reference identifies that original row; it is not an entity ID.
Lexical cases retain their original blockID/key, complete membership/hash,
dossier hash, preparation flags and exact source pointers.

Deduplicate cases **only** when ontology class and complete occurrence membership
are identical, retaining every original candidate membership. Partial overlaps
remain separate linked review cases, with one shared occurrence-context record.
No transitive union or pairwise expansion is performed. Review-case hashes are
package bookkeeping, never canonical entity identifiers.

## Lossless occurrence-to-canonical decision contract

The generated ledger covers every selected occurrence exactly once. It is not a
whole-graph identity map. All rows start `decisionStatus=unreviewed`,
`canonicalID=null`, `decisionAuthority=null`. Null means no decision; it does not
mean a distinct entity. Original graph record hashes, IDs, candidate memberships
and context references are mandatory and immutable.

A later separately authorized researcher adjudication must be append-only and
retain, at minimum: decision ID/revision, researcher authority and rationale,
review-case and input/package hashes, exact occurrence set, ontology class,
identity level, granularity/version scope, supporting and conflicting evidence
references, original candidate memberships and a supersession pointer if revised.
It must retain any model recommendation as a separate, unmodified attributed
artifact. A model recommendation, even if schema-valid, never changes the ledger.
This component provides no approval or canonical-ID assignment operation.

Only a researcher-approved **entity identity** decision at compatible class and
explicit granularity could later authorize an occurrence-to-canonical entity
mapping. Canonical identifiers and their allocation policy are deferred to that
separate implementation decision. A future mapping must retain every original
occurrence and its original class, attributes, version assertions, source owners,
evidence, relation endpoints/predicates and historical authority by immutable
reference. Conflicting values must remain occurrence-specific assertions; never
choose a winning attribute or delete a duplicate original record. Every mapped
occurrence must remain recoverable through its exact frozen snapshot record/hash.
There is no implicit transitive closure across separately reviewed subsets.

**Reference-target identity** is a separate result: occurrences may point to one
DOI record, resource or repository without establishing equal implementations,
versions, contents or scientific function. Reference-target recommendations do
not populate an entity canonicalID. **Conceptual similarity/identity** remains a
separate observation and does not authorize consolidation. Shared LSTM labels,
shared product names, shared dependency names or exact locators are insufficient
for implementation identity. Missing versions/detail indicate uncertainty, not
identity or difference. Version/granularity conflicts require explicit review.

Preserve owner-versus-reference roles. A citing artifact does not inherit a
cited target's identifier. Deterministic own identifiers, local literal declarations
and lexical candidates retain their original scopes. Publication `link_existing`
retains its declared target and request context; this pilot does not reconstruct
missing request-local authorization or promote local candidates globally. Such a
gap requires abstention/context review, not a workaround. Contextual/value-bearing
occurrences are not introduced into the selected identity universe.

Accepted predicates are immutable: mentions never become uses; references never
become implements. Evidence of an accepted relation is not automatically evidence
of endpoint identity. Historical signature problems are not repaired. Repeated
quotations, mirrored documentation or multiple artifacts do not constitute
independent identity confirmation.

## Review package and recommendation boundary

The package preserves original selected groups/dossiers and exact accepted node
and edge recovery pointers. Prepared occurrence hashes must agree with the frozen
node records and the selected lexical dossier. Classes/inventory IDs must agree
with the frozen ontology. Original flags, source artifact identities, identifiers,
versions and attributes are retained directly or as bounded values with full
hash-bound references. The already documented v2 exact GitHub root provenance
recovery is displayed separately from old preparation flags; no old record changes.

Context display uses at most four original evidence excerpts per occurrence,
1,600 characters each, and two incident edges per direction plus existing hub
examples. Edge display retains at most two original evidence excerpts. Selection
is deterministic canonical-JSON/ID order, not a judgment of evidentiary strength.
All omitted/truncated content retains full recovery pointers. Incident counts,
predicates and membership hashes cover all original incident edges, including
ones outside the displayed context. These references are not inferred relations.
Full documents are not retrieved or new evidence extracted. Original source
locations/native references allow a researcher to inspect additional context.

The recommendation JSON Schema is provider-neutral; nothing is submitted. It
requires `recommendation_only`, exact case ID/hash and displayed-context hash, explicit identity level,
subset membership, rationale, granularity/version/owner-reference assessment,
evidence/conflict citations, missing information and explicit abstention. Every
case member must be assessed or listed as unassessed. Non-abstaining assessments
must cite displayed original evidence. The local validator rejects unknown
members/citations, incompatible recommendation levels and missing coverage.
Schema validation checks structure and references, **not scientific truth**.
Same-entity/shared-target/conceptual assessments describe all listed subset members;
a different-entities recommendation must name an explicit pair, avoiding ambiguity
about which members differ. Overlapping subset recommendations require human reconciliation; they never
establish a transitive identity cluster.

Requests retain complete case membership. A payload exceeding 96,000 serialized
UTF-8 bytes is not emitted as a truncated request: its human package remains
available and its request record is marked for context review. Missing original
evidence/provenance also flags context review. Estimates use characters/4 and a
conservative byte-based budget, not a provider tokenizer. The proposed 4,096-token
response budget is planning metadata, not an executed model configuration.

## Feasibility and proposed incremental-value measurements

The generated report measures selection strata, deduplicated cases, unique
occurrences, context gaps, request readiness and approximate sizes. It does not
measure accuracy. After separate authorization and researcher decisions, proposed
measurements are: per-stratum entity/reference/conceptual/abstention yield; reasons
for unresolved cases; review time; model-human agreement and actual request costs;
distinct supported occurrence mappings and newly navigable artifact-to-artifact
paths using only unchanged accepted predicates in a hypothetical mapping view.

Use original edge IDs and distinct source artifacts to deduplicate gains; subtract
already-shared-node paths and overlapping cases. Report reference-target
navigability separately from entity consolidation. No high-degree pair count,
repeated quotation or weak-to-strong predicate promotion is an incremental gain.
This purposive pilot is not a population precision/recall estimate, independent
annotation campaign or replacement for frozen order-50 metrics. Scientific
usefulness and any production acceptance criteria remain researcher decisions.

## Offline generation

From the repository root, in the existing multigranular-kg environment:

```bash
python -m src.evaluation.step14_semantic_identity_pilot
```

Fresh ignored destination: `var/study2_step14/semantic-identity-pilot/v1/`:

- `original-groups.jsonl`, `review-cases.jsonl`, `occurrence-context.jsonl`
- `accepted-relation-context.jsonl`, `review-requests.jsonl`
- `decision-ledger-template.jsonl`, `recommendation.schema.json`
- `decision-contract.md`, `report.md`, `manifest.json`

Existing output directories are refused. Input hashes are checked before use and
again before writing; original v2/frozen outputs are never rewritten. The CLI
blocks network connections. Full package generation belongs in the researcher's
terminal, not the Codex shell. Focused synthetic validation:

```bash
python -m unittest tests.test_step14_semantic_identity_pilot -v
```
