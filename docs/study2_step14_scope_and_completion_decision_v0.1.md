# Study 2 Step 14: scope and completion decision v0.1

**Researcher-approved prospective scope clarification — 2026-11-06.**
Authority: `study2-step14-scope-and-completion/0.1.0`.
This records design and completion boundaries, not a new methodology, additional
identity-case approvals, or authorization to execute embeddings or materialize
canonical identities. Study 2 follows the accepted dissertation proposal; Step 14
must not become an independent research study.

## Approved design principles

- Canonical identity resolution covers repeated source-local occurrences within
  artifacts, across artifacts of one family, and across source families. These
  are coverage dimensions, not evidence of identity or blanket eligibility for
  every class. Apply the existing [identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md):
  the same scientific referent, compatible ontology class and supported
  granularity. Reference-target identity and conceptual similarity remain
  distinct from entity identity; overlapping approvals do not imply their union.
- Original occurrences, source relations, evidence spans and provenance remain
  unchanged and recoverable through their original identities and hashes.
  Equivalent assertions may share canonical subject–predicate–object
  representations while retaining every original assertion's provenance. No
  relation reification or new relation-node ontology is introduced by default;
  conflicting assertions remain attributable rather than overwritten.
- Preserve family, version, implementation and instance distinctions when
  supported. Missing specificity remains uncertainty. Do not merge different
  granularities, discard specificity, invent version relations or broaden
  frozen relation signatures.
- Candidate discovery combines identifiers, lexical matching and a simple
  two-view embedding approach: **name/class** and **entity-centered evidence**.
  Embeddings nominate candidates; they never determine identity. Start text
  representations from existing evidence. LLM-generated profiles are optional
  and outside the initial implementation.
- Local embedding storage/retrieval serves Step 14 only. Production vector
  infrastructure belongs to Study 3. Avoid new training pipelines, extensive
  alignment benchmarks, broad ontology expansion and large human-review
  campaigns.

## Completion boundary and remaining implementation choices

Complete necessary candidate review, the existing
[ontology/representation decision gate](study2_step14_identity_adjudication_proposals_v0.1.md#future-ontologyrepresentation-decision-gate),
approved canonical mappings under a separately authorized implementation, and
post-alignment measurement under the existing [evaluation policy](evaluation_decisions.md);
then proceed to Step 15. Explicitly unresolved cases may remain documented with
their evidence limitations and decision status. Completion does not require
universal identity resolution, zero isolated nodes or new ontology relations.
The gate remains necessary before canonical materialization; this scope decision
does not resolve its class, family/release or instance questions.

Embedding model, exact text composition, retrieval/index settings, candidate
budgets and review batching remain implementation details to be decided within
these boundaries. Canonical allocation and assertion-provenance storage must
follow the existing [lossless decision contract](study2_step14_semantic_identity_pilot.md#lossless-occurrence-to-canonical-decision-contract)
and require their own implementation decision. The historical
[embedding preflight](study2_step14_embedding_preflight.md) remains a planning
record: its single-text projection and bounded cross-family experiment do not
limit this approved two-view, within/across-artifact scope, and its proposed
eligibility/settings are not automatically approved here.

Ontology v0.1.7, the [accepted Step 13 closure](handoffs/STUDY2_STEP13_COMPLETION_ACCEPTANCE.md),
[order-50 checkpoint](study2_order50_frozen_scope_checkpoint.md), historical
contracts, case decisions and source artifacts retain their authorities unchanged.
This decision authorizes no new extraction, ontology amendment or KG write.
