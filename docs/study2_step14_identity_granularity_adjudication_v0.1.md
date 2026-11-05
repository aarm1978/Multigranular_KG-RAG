# Study 2 Step 14: granularity-conditioned identity adjudication policy v0.1

## Status and authority

This document records the researcher-approved **prospective policy**, before
adjudication of the 43 completed semantic identity review cases. Approval of this
policy is not approval of any case, subset, equivalence, or canonical identity.
The case guidance below is researcher-proposed candidate framing for subsequent
evidence review. No adjudication or materialization is performed here.

The frozen authorities remain [ontology v0.1.7](../src/ontology/ontology_spec.yaml)
and its [OWL representation](../src/ontology/ciroh_ontology.owl), the
[Step 13 frozen checkpoint](study2_order50_frozen_scope_checkpoint.md), and the
Step 14 [semantic review](study2_step14_semantic_review.md),
[identity pilot](study2_step14_semantic_identity_pilot.md), and
[live recommendation](study2_step14_identity_live.md) contracts. This policy
specifies prospective granularity assessment within the pilot's lossless decision
contract; it does not revise historical contracts, extraction decisions, evidence
boundaries, or original LLM recommendations.

## Identity criterion and levels

Entity identity requires evidence that occurrences denote **the same scientific
referent at an explicitly compatible granularity and ontology class**. A common
label, ontology class, architecture, locator, or source artifact is insufficient.
Granularity must follow the evidence about the referent, not labels alone. These
granularity descriptions are adjudication metadata, not new ontology classes.

| Referent granularity | Question for evidence review | Distinction to preserve |
|---|---|---|
| Named technique | Do the occurrences denote the same named technique as an `Algorithm`? | Implementations and fitted models using the technique |
| Architecture or model family | Do they describe a common architecture/family, or actually denote the same family-level referent? | Concrete releases and independently trained instances |
| Concrete model release | Do they denote the same identified release? | Other releases and unspecified-release mentions |
| Trained implementation | Do they denote the same specific trained model/implementation? | Other training runs, fitted instances, and architecture-only descriptions |
| Named dataset resource | Do they denote the same base resource? | Releases, subsets, extensions, and derived products |
| Dataset subset | Do they denote the same explicitly identified selection? | The whole resource and other basin/spatial/temporal selections |
| Derived product | Do they denote the same resulting product? | Its inputs, parent resource, and other transformations/products |

A named technique can itself be the referent of an `Algorithm` occurrence.
Evidence that two such occurrences denote that same technique may support entity
identity **at that granularity**. This does not convert conceptual similarity
between concrete implementations into entity identity. Likewise, a shared family
description of release-specific occurrences cannot replace their actual referents
with a broader family. Do not discard specificity to make a match possible.

Keep three assessment levels separate:

- **Entity identity:** the same referent, with compatible class and explicit
  granularity, supported by the selected occurrences' evidence.
- **Reference-target identity:** references point to the same identified target;
  this does not by itself establish identical implementations, versions, contents,
  or scientific functions, and does not populate an entity canonical ID.
- **Conceptual similarity/identity:** a common technique, architecture, family,
  or concept across otherwise distinct or unresolved referents. This observation
  alone does not authorize occurrence consolidation.

Missing specificity is uncertainty, not evidence of identity or difference. An
unspecified version must not act as a bridge between incompatible releases.
Class compatibility must use existing ontology contracts; a common superclass
does not itself establish identity or authorize retyping. Unresolved class or
referent ambiguity requires researcher review, not a guessed mapping.

## Researcher-proposed case framing

`Cxxx` and `Oxxx` are aliases in the completed review package, not global entity
IDs. Any subsequent decision must resolve them through the saved case/audit
bindings to exact original occurrence IDs and package hashes. The statements
below record the researcher's specified case interpretation; they are not new
case adjudications or retrospective edits to model output.

### C002 — Random Forest

All **six `Algorithm` occurrences** are candidates for identity at
**named-technique granularity**. Review whether their evidence denotes the same
Random Forest technique. This proposal does not assert identical code,
hyperparameters, training data, fitted forests, or trained-model instances.
`Algorithm` identity must not be extended to `MLModel` occurrences merely because
both use the words “Random Forest.”

### C031 — CAMELS-US

All **five `DatasetResource` occurrences** are candidates for identity at the
**named base-resource level**. Preserve distinct basin selections, extensions,
releases, and derived forcing products. Evidence that an artifact used a basin
selection from CAMELS-US does not make that selection identical to CAMELS-US as
a whole. Determine whether each occurrence denotes the base resource or a
specific subset/product; if that remains unclear, retain the uncertainty rather
than approving the whole candidate group by name alone.

### C032 — NWM

- **O001/O002:** candidates for **NWM v2.1 release-level identity**.
- **O004:** explicitly concerns **v3.0**; preserve that release specificity.
- **O003/O005:** release specificity remains **unresolved**; do not assign either
  release from neighboring occurrences or shared NWM labels.

Shared NWM family identity must not collapse these release-specific occurrences.
The v2.1 candidate subset is not approval of all five occurrences. Missing release
information in O003/O005 neither proves a different model nor permits transitive
consolidation of v2.1 and v3.0.

### LSTM — architecture versus trained instance

Two artifacts can describe LSTM architecture while using independently trained
`MLModel` instances. Shared architecture does not establish the same trained
instance. Conversely, an architecture-only description does not prove that two
instances differ. Keep architecture/family observations separate from an
evidence-supported claim about one concrete implementation; leave unresolved
granularity unresolved. No family-to-instance or model-to-version edge is implied.

## Ontology support and limits

The v0.1.7 specification describes `Algorithm` (A-DOM13) as a named technique.
`MLModel`, `ProcessBasedModel`, and `ConceptualModel` are subclasses of abstract
`ComputationalModel`. These class assignments do not encode a complete hierarchy
of architecture, family, release, and trained instance. In particular,
`ConceptualModel` is an existing model class, not a synonym for the assessment
level “conceptual identity.”

`ModelVersion` exists as metadata, but `hasModelVersion` (C-C09) has domain
**`Repository`** and range **`ModelVersion`**. It is not a general relation from
`MLModel` or `ProcessBasedModel` to a version. The current relation inventory does
not authorize a general model-family-to-instance relation. Preserve version
statements in their original records; do not invent such links or broaden
existing signatures to represent this policy.

`DatasetResource` can participate in these existing properties:

| Property | Frozen signature and evidence constraint |
|---|---|
| `hasMember` (C-D12) | `DatasetResource` → `DatasetResource`; collection membership supported by member resource IDs; inverse of `isMemberOf` |
| `isMemberOf` (C-D13) | `DatasetResource` → `DatasetResource`; collection membership supported by resource-link targets |
| `derivedFrom` (C-D14) | `DatasetResource` → `DatasetResource`; supported typed relations or explicit prose; reuse anchor `prov:wasDerivedFrom` |

These signatures do not prove membership or derivation for any candidate.
Collection notes and original evidence constraints remain applicable. A basin
selection, similar title, extension label, or version difference alone must not
be converted into one of these properties. The `derivedFrom` specification note
“aka versionedFrom” is not authority to infer a derivation from version strings.
This policy creates no relations, even where an existing property might later be
appropriate under separately authorized, evidence-supported work.

DCAT 3 distinguishes datasets, distributions, dataset series, and version
relationships; it leaves domain-specific series organization to communities.
This provides methodological support for preserving resource, member, and version
distinctions instead of treating all related records as identical. DCAT does not
adjudicate CAMELS-US identity or import additional terms into CIROH v0.1.7.
See [W3C DCAT 3, sections 11–12](https://www.w3.org/TR/2024/REC-vocab-dcat-3-20240822/).

OWL individual equality is stronger than similarity: equal individuals denote
the same individual and can substitute for one another in ontology expressions.
See [OWL 2 Structural Specification, §9.6.1](https://www.w3.org/TR/owl2-syntax/#Individual_Equality)
and [OWL 2 Direct Semantics, Table 10](https://www.w3.org/TR/owl2-direct-semantics/#Assertions).
Consequently, `owl:sameAs` is not a way to say “same family but different release.”
The prohibition on implicit transitive merging is an operational review boundary,
not a claim that logical equality is nontransitive. Separate scope-qualified
proposals must not be unioned automatically. Any future combined identity set
would require explicit review of the complete membership, compatible referents,
classes, granularity, versions, and conflicts. This policy emits no equality axiom.

## Evidence preservation and decision states

Preserve every original occurrence ID, class, attribute, version statement,
source identity, source/reference role, evidence reference and quotation,
provenance authority, accepted relation predicate, and LLM recommendation.
Conflicting assertions remain attributable to their original occurrences; do not
select a winning value or rewrite evidence. An accepted `mentionsTool` is not
`usesTool`; `referencesRepository` is not `hasCodeRepository`; reference evidence
is not automatically endpoint identity evidence.

Entity-owned identifiers must retain their scope. A referring repository ID is
not a referenced entity ID, a source capture commit is not automatically an
entity version, and a shared URL is not automatically entity equivalence. Preserve
legitimate entity-level checksums and versions. Publication `link_existing`
retains its request-local authorization boundary. Repeated quotations or mirrored
documentation do not constitute independent confirmation.

The pilot supplies selected evidence, not exhaustive source evidence. Its original
context selected **419 of 421 relation-evidence occurrences**, omitting one of
three for each of the `referencePublication` and `usesTool` edges identified in
the [live contract's omission record](study2_step14_identity_live.md). These gaps
remain visible; this document does not restore evidence or expand cases. A gap
material to identity requires unresolved/abstaining treatment pending authorized
review of the existing evidence, not an invented conclusion.

| State | Meaning and permitted consequence |
|---|---|
| Researcher-proposed adjudication | A proposed exact subset, referent/granularity, rationale, and evidence assessment; no approved identity or canonical assignment |
| Approved entity identity | An explicit researcher decision recorded under the pilot's append-only, evidence-bound decision contract; distinct from an LLM recommendation and from materialization |
| Actual canonical materialization | A separately authorized implementation of approved mappings with its own allocation policy and lossless provenance; not performed or authorized by this document |

Subsequent decisions must retain the pilot's required decision revision, authority,
case/input hashes, exact occurrence membership, class, identity level,
granularity/version scope, supporting/conflicting evidence, original candidate
memberships, and supersession references. Partial or overlapping subset approvals
must not implicitly approve their union. No canonical IDs are allocated here.

The [five-category recommendation schema](study2_step14_identity_recommendation.schema.json)
remains unchanged: `same_entity_candidate`, `shared_reference_target_only`,
`conceptual_similarity_only`, `different_entities_candidate`, and `abstain`.
Keep subset assessments, unassessed occurrences, and abstention explicit. Original
model responses remain separate, unmodified recommendations, even if a subsequent
researcher decision disagrees. Neither schema validation nor this policy converts
a completed LLM review into adjudicated truth.

## Deferred questions and boundary

The policy resolves the prospective granularity criterion, not the evidence
judgments for the 43 cases. Release specificity for C032 O003/O005, any ambiguous
base-resource versus subset/product referents in C031, and architecture versus
trained-instance referents remain questions for later researcher adjudication.
Where an occurrence cannot support one compatible referent without losing
specificity, retain it unresolved; do not split, retype, or remap it as a workaround.

Representation of model families, releases, and instances beyond existing
signatures, and any eventual canonical allocation/materialization design, require
separate researcher decisions. No ontology extension is proposed here. Frozen v4,
order-50 metrics, source-local outputs, decision ledgers, original LLM responses,
canonical IDs, and KG files remain unchanged. No Step 14A extraction, provider
calls, embeddings, scientific relations, or KG construction accompanies this policy.
