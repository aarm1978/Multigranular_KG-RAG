# Publication Evidence-Validation Contract — Publication Pilot 1

> **Status:** final and binding for Publication Pilot 1 implementation
> **Contract version:** 0.1.0
> **Artifact family:** scientific publications
> **Source scope:** curated publication corpus
> **Stage scope:** automatic validation of parsed LLM candidates before adjudication
> **Frozen ontology:** CIROH ontology 0.1.3
> **Validated OWL SHA-256:** `ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57`
> **Binding target profile:** `src/extraction/llm/publications/publication_target_inventory.yaml`
> **Binding source-unit contract:** `docs/publication_source_unit_contract.md`
> **Candidate-output schema:** `schemas/publication_candidate_output.schema.json`
> **Date drafted:** 2026-07-30
> **Date frozen:** 2026-07-30

## 1. Purpose

This contract defines the deterministic validation boundary between a parsed ontology-guided
LLM response and a **validated Publication Pilot 1 candidate**. It specifies:

- the trusted inputs used by validation;
- the difference between model output, pipeline metadata, evidence validation, semantic
  evaluation, and adjudication;
- the validation sequence for evidence spans, candidate nodes, candidate edges,
  abstentions, and deferred-record resolutions;
- the conditions that produce `validated`, `rejected`, `needs_review`, `superseded`, or
  `deferred` outcomes;
- stable validation codes;
- deterministic output and provenance requirements; and
- the conditions that must be satisfied before the validator implementation is accepted.

The governing rule is:

> **No supported evidence span means no accepted semantic assertion.**

For this contract, passing automatic validation means that a candidate is structurally
well formed, source-grounded, ontology-compatible, and authorized by the frozen pilot
profile. It does **not** by itself establish that the candidate is scientifically correct
or equivalent to the adjudicated gold standard.

## 2. Authority and reviewed inputs

The first seven authorities retain the order frozen by the target-profile and source-unit
contracts. The two new contract artifacts are appended after them:

1. frozen ontology 0.1.3 specification and generated OWL;
2. frozen deterministic Phase B outputs and tests;
3. final Publication Pilot 1 human-readable target inventory;
4. publication ontology observations register;
5. LLM extraction decision record;
6. final machine-readable publication target profile;
7. final publication source-unit contract;
8. publication candidate-output JSON Schema; and
9. this evidence-validation contract.

Reviewed inputs:

| Artifact | Reviewed SHA-256 | Role |
| --- | --- | --- |
| `src/ontology/ontology_spec.yaml` | `a940dd79ac0c8b10980b3a17739d2f03ac5b0c23ce80dffb0bb90009cf19db54` | Formal ontology authority |
| `docs/publication_llm_extraction_target_inventory.md` | `b2055e9735c64c5dc5d712fa96bdc95cb4137c75390261902fbc3055fc3d9ffa` | Binding human-readable Pilot 1 scope |
| `docs/publication_ontology_observations_register.md` | `d06dbdf64fa7bd2ac81c7c1e97d16eebb8ded3d432396414c03a3e0ebca79d5e` | Binding contract and validator dispositions |
| `docs/llm_extraction_decisions.md` | `239730fc889f6cdf792894dc4bd7e8e247059b576b6e9ba6748e9bc7567ed42f` | LLM extraction lifecycle and evidence decisions |
| `src/extraction/llm/publications/publication_target_inventory.yaml` | `3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760` | Final executable target profile |
| `docs/publication_source_unit_contract.md` | `31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a` | Final source-unit and request-context contract |
| `schemas/publication_candidate_output.schema.json` | `affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d` | Final frozen parsed-candidate envelope structure |

The hashes above identify the artifacts reviewed for the initial contract freeze. Any
later approved content change requires the applicable version increment and hash update.

## 3. Validation boundary

### 3.1 Candidate lifecycle

Publication Pilot 1 uses the following lifecycle:

```text
source mention
    → parsed candidate
    → automatically validated candidate
    → human/adjudication decision
    → source-level augmented assertion
    → later inter-source alignment
    → later consolidation
    → final KG assertion
```

This contract governs only the transition:

```text
parsed candidate → automatically validated candidate
```

It does not authorize direct graph loading, global identity resolution, or final assertion
acceptance.

### 3.2 Model output and pipeline output are distinct

The canonical candidate artifact is a provider-neutral parsed envelope governed by:

```text
schemas/publication_candidate_output.schema.json
```

The model supplies the semantic payload, including target choices, labels, endpoint
references, evidence coordinates, abstentions, and proposed deferred-record dispositions.
The pipeline supplies or verifies trusted request/run metadata, hashes, and validation
results.

The pipeline must preserve the raw provider response separately. It may not silently
rewrite the model's semantic choices to make them valid.

### 3.3 Validation errors are not model-authored fields

Validation outcomes are stored in a separate validation artifact. They are deliberately
not part of the model-authored candidate payload. This prevents the model from declaring
its own output valid or selecting validator error codes strategically.

Recommended run artifacts are:

```text
data/interim/papers/llm/runs/<run_id>/raw_responses.jsonl
data/interim/papers/llm/runs/<run_id>/candidates.jsonl
data/interim/papers/llm/runs/<run_id>/validation_results.jsonl
```

An invalid or truncated raw response may produce a processing-failure record without a
candidate envelope.

## 4. Trusted validation inputs

The validator may use only:

1. the parsed candidate envelope;
2. the exact request record and request hash;
3. the source units included in that request;
4. the canonical Markdown and source-unit records governed by the frozen source-unit
   contract;
5. the final machine-readable Publication Pilot 1 target profile;
6. the frozen ontology specification;
7. deterministic nodes, edges, and deferred records explicitly supplied in the request;
8. previously accepted local candidates explicitly supplied in the request envelope; and
9. deterministic validator configuration and code.

The validator may not use:

- web search;
- model parametric memory;
- unrecorded external metadata;
- a PDF interpretation unavailable in canonical Markdown;
- name similarity to perform global consolidation;
- undocumented normalization; or
- a different ontology or target-profile version.

## 5. Candidate-output envelope requirements

### 5.1 Schema validation

The complete candidate envelope must validate against JSON Schema Draft 2020-12 using:

```text
schemas/publication_candidate_output.schema.json
```

The schema validates structural shape and controlled values. It does not replace the
semantic and cross-record checks in this contract.

### 5.2 Pipeline-owned metadata

The following metadata must be copied from trusted request/run records rather than trusted
as model evidence:

```text
outputID
requestID
runID
sourceArtifactID
primarySourceUnitID
contextSourceUnitIDs
requestScope
includedCompleteSection
extractionChannel
eligibleOperationalTargetIDs
deferredRecordIDs
ontologyVersion and hash
target-profile version and hash
source-unit-contract version and hash
candidate-schema version and hash
prompt version and hash
request input hash
raw response hash
provider and model metadata
generation parameters
token usage
cost
retry count
response timestamp
```

A mismatch between a candidate-envelope value and the trusted request/run record is an
error. The pipeline may replace the untrusted value in the canonical parsed envelope only
when the original raw response is preserved and the replacement is recorded as a
pipeline-binding operation rather than a model assertion.

The frozen target-profile and source-unit-contract hashes are schema constants. The
candidate-schema hash is pipeline-bound because a schema cannot contain its own byte hash
without creating a recursive hash dependency. Provider timestamps, token usage, cost,
retry count, and other mutable run observations belong to provenance metadata and are
excluded from every immutable candidate identity projection. Candidate identity is based
only on the versioned canonical semantic record and its evidence references; the later
request-builder contract must freeze that exact projection before implementation.

### 5.3 Local identifiers

Within one candidate envelope:

```text
node-0001
edge-0001
evidence-0001
abstention-0001
```

are request-local identifiers. They are not ontology instance identifiers and may not be
used as global graph IDs.

All local identifiers must be unique within their record type. Every reference must
resolve to exactly one declared record or one authorized request-context endpoint.

## 6. Validation sequence

Validation must run in the following order. A later stage must not hide or repair a failure
from an earlier stage.

```text
V1  transport and parse status
V2  JSON Schema validation
V3  request/run binding
V4  source-unit and evidence-span validation
V5  target-profile and ontology authorization
V6  candidate-node validation
V7  endpoint resolution
V8  candidate-edge domain/range and evidence validation
V9  use/mention/reference and other conflict rules
V10 exact-duplicate and local-reconciliation checks
V11 abstention and deferred-record checks
V12 deterministic result classification and output
```

## 7. Transport and parsing validation

### 7.1 Processing failures

The following remain processing failures and are not semantic abstentions:

```text
invalid_json
timeout
api_error
truncated_response
token_limit
retry_exhausted
```

A processing failure must not be scored as:

- a correct empty extraction;
- an appropriate abstention;
- a rejected semantic candidate; or
- evidence that a target is absent.

### 7.2 Partial recovery

The validator must not salvage individual candidates from malformed JSON through ad hoc
regular expressions or manual text extraction. A provider-level parser may perform only
versioned, deterministic repairs explicitly allowed by a separate parsing policy. Pilot 1
begins with no such repair policy.

## 8. Evidence-span validation

Every evidence span is validated independently before any candidate that references it.

### 8.1 Required source bindings

For each evidence span:

1. `sourceArtifactID` must equal both the request source artifact and
   `sourceUnit.canonicalArtifactID`;
2. `sourceUnitID` must identify either the primary unit or an explicitly included context
   unit;
3. `sourceUnitTextHash` must equal the source-unit record's `textHash`;
4. `sectionID` must match the source-unit record and `sectionTitle` must equal
   `sourceUnit.sectionTitleRaw` (including `null` for synthetic front matter); and
5. the source unit must belong to the same canonical document hash used by the request.

Anonymous copied snippets are invalid evidence.

`sourceArtifactID` is the evidence-interface name for the source-unit record's
`canonicalArtifactID`, and `sourceUnitTextHash` is the candidate-interface name for the
frozen source-unit record's `textHash`; neither alias defines a second identity or hash
algorithm. The remaining evidence fields are
exactly `sourceArtifactID`, `sourceUnitID`, `sectionID`, `sectionTitle`, `evidenceText`,
`startOffsetInUnit`, `endOffsetInUnit`, `startOffsetInDocument`,
`endOffsetInDocument`, and `evidenceHash`. Likewise, candidate `sectionTitle` is the
evidence-interface alias for `sectionTitleRaw`; the routing-only
`sectionTitleNormalized` never replaces it and is not evidence.

### 8.2 Offset convention

Offsets are:

```text
zero-based
half-open [start, end)
Unicode code-point offsets
```

The following must both hold exactly:

```text
unit.text[startOffsetInUnit:endOffsetInUnit] == evidenceText
canonicalDocument[startOffsetInDocument:endOffsetInDocument] == evidenceText
```

Additionally:

```text
startOffsetInDocument
    == sourceUnit.startOffsetInDocument + startOffsetInUnit

endOffsetInDocument
    == sourceUnit.startOffsetInDocument + endOffsetInUnit
```

A span may not cross a source-unit boundary.

### 8.3 Evidence hash

After successful literal and offset validation, the pipeline computes:

```text
evidenceHash = sha256(UTF-8(evidenceText))
```

The model is not required to calculate this hash. A non-null model-supplied hash is still
recomputed and must match.

### 8.4 Eligible source content

Evidence may support a candidate only when its source unit is `eligible`, or when a
specific contract rule permits a context-only unit to participate as non-exclusive
support.

The following cannot independently support an accepted semantic candidate:

- a structural heading;
- reference-list content;
- excluded units;
- unresolved `needs_review` units;
- visual-only figure meaning;
- unrecoverable table content;
- standalone equation interpretation; or
- an LLM-generated summary.

### 8.5 Multiple spans

A candidate may cite multiple contiguous evidence spans. Each span is validated
independently. Multiple spans are required when the evidence is distributed across source
units.

One evidence span may support more than one candidate only when the literal text genuinely
supports each candidate. Shared evidence does not remove the requirement for candidate-
specific validation.

### 8.6 Edge evidence independence

Evidence that establishes two endpoint nodes does not automatically establish the
relation between them. Every non-derived candidate edge must cite evidence that supports
the relation semantics, not merely the presence of both endpoint labels.

## 9. Target-profile and ontology authorization

For every candidate node or edge:

1. its operational target must exist in the final machine-readable target profile;
2. it must be listed in the request's `eligibleOperationalTargetIDs`;
3. its ontology ID and class/relation name must match the operational target row;
4. its action must be permitted by that row;
5. its emission mode must permit a model or resolver-mediated candidate;
6. its treatment must not be `out_of_scope`, `context_only` without a permitted
   `link_existing` action, `required_infrastructure`, or
   `separate_follow_on_protocol`; and
7. the candidate may not broaden an operational signature to the full ontology signature.

An ontology-valid class or relation remains invalid when it is outside the frozen
Publication Pilot 1 profile.

## 10. Candidate-node validation

### 10.1 Common node requirements

A node candidate must have:

- one authorized operational target;
- one matching ontology class ID and class name;
- one permitted action;
- one non-empty label;
- at least one valid evidence span;
- an identity scope consistent with the action and target; and
- no forbidden field or behavior.

### 10.2 `propose_new`

For `propose_new`:

- `existingNodeID` must be `null`;
- direct instantiation must be permitted for the target class;
- the class must not be abstract;
- the candidate remains source-local; and
- no global identity or canonical ID may be asserted.

### 10.3 `link_existing`

For `link_existing`:

- `existingNodeID` must identify an exact deterministic endpoint or authorized accepted
  local candidate present in the request context;
- the endpoint's class must be compatible with the operational target;
- the link may not be based solely on approximate name similarity; and
- linking does not mutate or merge the existing endpoint.

### 10.4 Labels and normalization proposals

`labelMode` is fixed to `verbatim`. The complete authoritative `label` must occur literally
in at least one cited evidence span.

`normalizedLabelProposal` may contain a concise normalized form proposed from the
evidence-grounded label, or `null` when no normalization is proposed. The proposal:

- is not evidence;
- is not authoritative;
- does not replace the verbatim label;
- does not by itself change an otherwise valid candidate to `needs_review`; and
- may not be used for identity resolution, linking, duplicate suppression, merging, or
  consolidation until it is separately validated or adjudicated.

The validator first attempts approved, versioned deterministic normalization rules. When
one of those rules exactly reproduces the normalized form, the normalization receives
`normalizationStatus: validated` and records the rule identifier. When an LLM-proposed
semantic normalization cannot be reproduced by an approved deterministic rule, it receives
`normalizationStatus: pending_review`; the candidate may still receive
`candidateValidationStatus: validated`, and the verbatim label remains its operational
label.

The later review is localized to the normalization field. It presents the ontology target,
verbatim label, proposed normalized label, cited evidence, and bounded surrounding context.
The adjudication layer may accept the normalization, retain only the verbatim label, edit
the normalized form, or reject the normalization without reopening the whole candidate.

For discourse nodes, the preferred Pilot 1 behavior is a verbatim atomic proposition or
source-supported atomic text unit. For named domain entities, the authoritative label is
the exact source surface form.

### 10.5 Atomicity and local identity

```text
one candidate node = one atomic semantic unit
```

A candidate that combines distinct findings, methods, goals, limitations, variables, or
other semantic units is marked `needs_review` or rejected when the conflation is clear.

Same-named entities are not automatically merged across papers. Within one paper:

```text
same class + same meaning
    → one locally reconciled candidate with multiple evidence spans

same class + distinct meaning or context
    → separate candidates
```

### 10.6 Abstract classes

The following may not be directly emitted:

```text
SoftwareEntity
ComputationalModel
Place
HydrologicFeature
```

The model must select the most specific supported concrete subtype or abstain.

### 10.7 Contextual `EvaluationMetric` and `Parameter`

`EvaluationMetric` and `Parameter` candidates represent contextual occurrences. They may
not be merged solely because they share a name.

Their identity must remain sensitive to available evidence about:

- owner;
- experiment;
- model or method;
- condition;
- value;
- range; and
- configuration.

Authorized attributes are limited to the candidate-output schema and target profile.
`value`, `range`, and `calibrationStatus` require their own cited evidence. Values, units,
operators, intervals, and ranges remain exact source strings; the validator performs no
numeric normalization.

The permitted structured attributes are `EvaluationMetric.value`;
`Parameter.value`, `Parameter.range`, and `Parameter.calibrationStatus`; and
`Repository.fork` and `Repository.commitSHA`. No other Pilot 1 node target may carry a
structured candidate attribute. Every populated attribute has its own non-empty evidence
reference list, independently of the node-level evidence list.

### 10.8 Repository identity

A repository named without an exact canonical URL may be emitted only through the
source-scoped provisional repository operational target.

```text
provisionalIdentity: true
identityScope: source_local
```

must not be interpreted as a global repository assertion. When an exact URL is supplied,
the resolver-mediated or exact-existing endpoint route must be used.

### 10.9 Forbidden behaviors

The validator rejects attempts to emit or imply:

```text
sameAs
mergeWith
consolidatesTo
global canonical ID
invented external identifier
Neo4j internal ID
direct database write
mutation of deterministic output
direct instantiation of abstract classes
```

## 11. Endpoint resolution

Every candidate-edge endpoint must resolve through one of these routes:

```text
candidate_node
    → a candidate node in the same candidate envelope

deterministic_node
    → an exact node explicitly supplied in the request's deterministic context

accepted_local_candidate
    → a previously accepted local candidate explicitly supplied in the request envelope
```

An endpoint reference based only on a raw label is not permitted.

For an inter-source relation, the target may remain a source-scoped unresolved candidate,
but final cross-source identity and consolidation remain outside Pilot 1 validation.

## 12. Candidate-edge validation

### 12.1 Common edge requirements

A candidate edge must have:

- one authorized operational relation;
- a matching ontology relation ID and relation name;
- a permitted action;
- two resolvable endpoints;
- an accurate `relationScope`;
- at least one valid edge-specific evidence span; and
- an operational domain/range signature compatible with the endpoint classes.

### 12.2 Operational domain and range

The validator checks the source and target endpoint classes against the operational
signature recorded in the target profile. Subclass compatibility is allowed when the
profile specifies or entails it. The validator must not broaden a Pilot 1 operational
signature merely because the ontology property has a broader formal domain or range.

Domain and range are checked separately and receive separate validation codes.

### 12.3 Relation-specific boundaries

The target profile's `positive_criterion` and `boundary` fields are binding validation and
adjudication guidance. In particular:

- `resolves` requires explicit addressing, responding to, or resolving semantics, not
  co-occurrence;
- `produces` requires evidence connecting a Method or Experiment to a Finding;
- `testedBy` permits only `Hypothesis → Method/Experiment`;
- `supports` is positive-only and does not permit `Finding → Hypothesis`;
- `relatesTo` in Pilot 1 permits only the local semantic-target branch, not cited-Paper
  grounding;
- `hasLimitation` model output permits only the `Finding → Limitation` branch;
- `reports`, `discussesRelatedWork`, and `Paper → hasLimitation → Limitation` are
  pipeline-derived and are not direct LLM predictions;
- `usesModel` and `appliesTo` must reflect distinct functional roles;
- `reportsMetric`, `evaluates`, and `hasParameter` require contextually aligned endpoints;
- `usesAlgorithm` has no Paper-level shortcut;
- `referencesDataset` resolver output requires the exact omitted-identifier channel; and
- no summary relation or TheoreticalBasis-grounding relation is authorized.

### 12.4 Relation scope

```text
intra_source
    Both endpoints belong to the current source representation.

inter_source
    The relation connects the current Paper to a distinct artifact or source-local
    representation of a distinct artifact.
```

Same artifact family does not imply intra-source. `Paper A → Paper B` is inter-source.

## 13. Use, mention, reference, and repository precedence

For the same source and target entity pair:

```text
usesModel supersedes mentionsModel
usesTool supersedes mentionsTool
usesDataset supersedes mentionsDataset
hasCodeRepository supersedes referencesRepository
```

`usesDataset` and `referencesDataset` may coexist because they encode different evidence
roles.

A weaker candidate that is fully subsumed by a stronger candidate which has passed all
applicable automatic checks is marked:

```text
superseded
```

rather than counted as a separate valid prediction. The original model output remains
preserved for error analysis.

The validator must not infer actual use from:

- a citation;
- a name occurrence;
- a comparison of prior work;
- a future-work statement; or
- availability without evidence of use.

## 14. Duplicate and local-reconciliation validation

### 14.1 Exact duplicates

The validator may automatically identify exact duplicates when all material fields match.

For nodes, the exact-duplicate key includes:

```text
sourceArtifactID
operationalTargetID
action
existingNodeID
label
attributes
sorted evidence coordinates
```

For edges, the exact-duplicate key includes:

```text
sourceArtifactID
operationalRelationID
action
source endpoint
target endpoint
sorted evidence coordinates
```

Only one record remains `validated`; the others are `superseded` as exact duplicates.

### 14.2 Possible semantic duplicates

Potential same-meaning candidates with different labels or evidence are not merged
silently. They are marked `needs_review` with a possible-local-duplicate code. This is
especially important for discourse units and contextual metric/parameter occurrences.

### 14.3 No global consolidation

The validator does not create `sameAs`, perform cross-paper canonicalization, or merge
source-local candidates with entities from other artifact families.

## 15. Abstention validation

### 15.1 Meaning of an abstention

An abstention records an explicit decision not to assert a plausible candidate because a
specified semantic condition prevents a defensible output.

Absence of a candidate is not automatically an abstention. The model need not emit one
abstention for every eligible target that does not occur in a source unit.

### 15.2 Authorized reasons

Reasons must come from the frozen target profile:

```text
insufficient_evidence
ambiguous_class
ambiguous_relation
unresolved_endpoint
invalid_domain_range
target_outside_ontology
incomplete_source_text
unrecoverable_table_structure
visual_only_evidence
equation_only_evidence
unresolved_cross_reference
```

### 15.3 Abstention evidence

Evidence is optional when the reason is the absence or unrecoverability of evidence. When
an abstention cites a span, that span must pass the same literal and offset validation as
candidate evidence.

An abstention must not conceal a processing failure, forbidden target, or malformed model
response.

## 16. Deferred-record validation

Every proposed deferred-record disposition must reference a deferred record explicitly
included in the request.

Authorized canonical dispositions are:

```text
resolved_accepted
resolved_rejected
remain_deferred
insufficient_evidence
out_of_scope
type_conflict
unsupported_role
```

Rules:

- `resolved_accepted` must reference at least one candidate that passes automatic
  validation;
- `resolved_rejected` must provide a rationale and may provide evidence;
- `remain_deferred`, `insufficient_evidence`, `type_conflict`, and `unsupported_role`
  must not claim a resolved endpoint;
- `out_of_scope` must agree with the frozen target profile;
- a disposition may not modify the original deferred record; and
- the original Phase B deferred identifier and reason remain preserved.

The candidate field is named `proposedDisposition`. The controlled values above retain
the frozen lifecycle semantics, but they are non-authoritative model proposals. The final
human target inventory and machine-readable profile use `remain_deferred`, while the
earlier G-03 decision text uses the historical synonym `still_unresolved`; this contract
uses the final target-inventory spelling. The inventory's prose shorthand `rejected` is
represented by G-03's unambiguous `resolved_rejected`. These are vocabulary
reconciliations, not additional lifecycle outcomes.
In particular, `resolved_accepted` means "the model proposes a resolution candidate for
automatic validation"; it does not mean adjudication acceptance or graph acceptance.
Likewise, `resolved_rejected` is a proposed semantic disposition, not a validator result
or adjudication decision. Only the separate validator and later adjudication artifacts
may assign their respective lifecycle outcomes.

## 17. Automatic validation outcomes

### 17.1 Candidate-level statuses

```text
validated
    Passes all applicable automatic structural, provenance, target, ontology,
    endpoint, and conflict checks. Semantic correctness still requires evaluation or
    adjudication.

rejected
    Violates a hard contract rule and cannot proceed unchanged.

needs_review
    Passes basic structural checks but requires human or separately specified semantic
    review because of possible semantic duplication or ambiguous atomicity.

superseded
    Structurally valid but removed from the active candidate set by an exact duplicate or
    stronger-role precedence rule.

deferred
    Belongs to an unresolved resolver-mediated case that remains open.
```

A pending label normalization is a field-level state and does not by itself assign
`needs_review` to the candidate.

Validator records use `candidateValidationStatus` for these states. They never reuse this
field for normalization review or later adjudication.

### 17.2 Normalization-level statuses

```text
not_applicable
    No normalized label was proposed or produced.

validated
    An approved, versioned deterministic rule produced the normalized label exactly.

pending_review
    A semantic normalization was proposed but cannot be reproduced by an approved
    deterministic rule. The verbatim label remains authoritative.

rejected
    The proposed normalization was rejected or could not be retained safely. The
    candidate may remain valid using its verbatim label.
```

Normalization status is stored in the deterministic validation result, not authored as a
self-validation claim by the model. A `pending_review` normalization does not change the
candidate or envelope validation status.

### 17.3 Envelope-level statuses

```text
valid
    Every candidate is validated, superseded, or represented by an authorized abstention
    or deferred disposition.

partially_valid
    At least one candidate validates and at least one is rejected, deferred, or needs
    review.

invalid
    The envelope fails schema/request binding or no candidate can be processed safely.

processing_failed
    No valid candidate envelope exists because transport or parsing failed.
```

### 17.4 Validation is not adjudication

The validator must not convert `validated` directly into `accepted` for the augmented KG.
`accepted` and `rejected` adjudication outcomes belong to the later adjudication layer.

## 18. Stable validation codes

Each validation result contains zero or more stable codes. Codes are grouped below by
stage. A code's default consequence may be overridden only by a versioned contract change.

### 18.1 Processing

```text
INVALID_JSON
TIMEOUT
API_ERROR
TRUNCATED_RESPONSE
TOKEN_LIMIT
RETRY_EXHAUSTED
```

### 18.2 Schema

```text
SCHEMA_VALIDATION_FAILED
FORBIDDEN_FIELD
```

### 18.3 Request and provenance binding

```text
REQUEST_ID_MISMATCH
RUN_ID_MISMATCH
SOURCE_ARTIFACT_MISMATCH
PRIMARY_SOURCE_UNIT_MISMATCH
CONTEXT_SOURCE_UNIT_MISMATCH
TARGET_PROFILE_VERSION_MISMATCH
TARGET_PROFILE_HASH_MISMATCH
SOURCE_UNIT_CONTRACT_VERSION_MISMATCH
SOURCE_UNIT_CONTRACT_HASH_MISMATCH
CANDIDATE_SCHEMA_VERSION_MISMATCH
CANDIDATE_SCHEMA_HASH_MISMATCH
ONTOLOGY_VERSION_MISMATCH
ONTOLOGY_HASH_MISMATCH
PROMPT_HASH_MISMATCH
REQUEST_INPUT_HASH_MISMATCH
RAW_RESPONSE_HASH_MISMATCH
```

### 18.4 Evidence spans

```text
EVIDENCE_SPAN_ID_DUPLICATE
SOURCE_UNIT_NOT_FOUND
SOURCE_UNIT_NOT_IN_REQUEST
SOURCE_UNIT_HASH_MISMATCH
SECTION_ID_MISMATCH
SECTION_TITLE_MISMATCH
EVIDENCE_TEXT_EMPTY
EVIDENCE_NOT_LITERAL
OFFSET_OUT_OF_BOUNDS
OFFSET_MISMATCH_IN_UNIT
OFFSET_MISMATCH_IN_DOCUMENT
UNIT_DOCUMENT_OFFSET_INCONSISTENT
EVIDENCE_HASH_MISMATCH
EVIDENCE_FROM_EXCLUDED_UNIT
EVIDENCE_FROM_NEEDS_REVIEW_UNIT
CROSS_UNIT_EVIDENCE_SPAN
UNREFERENCED_EVIDENCE_SPAN
```

### 18.5 Target and action authorization

```text
CANDIDATE_ID_DUPLICATE
UNKNOWN_OPERATIONAL_TARGET
TARGET_NOT_INCLUDED_IN_REQUEST
TARGET_NOT_EMITTABLE
OUT_OF_SCOPE_TARGET
FOLLOW_ON_TARGET
ONTOLOGY_ID_MISMATCH
CLASS_NAME_MISMATCH
RELATION_NAME_MISMATCH
ACTION_NOT_ALLOWED
ABSTRACT_CLASS_OUTPUT
DETERMINISTIC_MUTATION_ATTEMPT
```

### 18.6 Candidate nodes

```text
NODE_EVIDENCE_MISSING
NODE_EVIDENCE_INVALID
LABEL_EMPTY
VERBATIM_LABEL_NOT_IN_EVIDENCE
PROPOSE_NEW_HAS_EXISTING_ENDPOINT
LINK_EXISTING_ENDPOINT_MISSING
LINK_EXISTING_ENDPOINT_NOT_AUTHORIZED
LINK_EXISTING_CLASS_MISMATCH
INVALID_IDENTITY_SCOPE
INVALID_PROVISIONAL_IDENTITY
ATTRIBUTE_NOT_ALLOWED_FOR_TARGET
ATTRIBUTE_EVIDENCE_MISSING
ATOMICITY_VIOLATION
```

### 18.7 Endpoint resolution

```text
ENDPOINT_REFERENCE_MISSING
ENDPOINT_REFERENCE_AMBIGUOUS
ENDPOINT_CLASS_UNRESOLVED
ENDPOINT_LIFECYCLE_INVALID
```

### 18.8 Candidate edges

```text
EDGE_EVIDENCE_MISSING
EDGE_EVIDENCE_INVALID
RELATION_EVIDENCE_INSUFFICIENT
INVALID_DOMAIN
INVALID_RANGE
RELATION_SCOPE_MISMATCH
UNAUTHORIZED_RELATION_BRANCH
NEGATIVE_SUPPORT_NOT_AUTHORIZED
SUMMARY_RELATION_NOT_AUTHORIZED
THEORY_GROUNDING_RELATION_NOT_AUTHORIZED
```

### 18.9 Precedence and conflict rules

```text
WEAKER_RELATION_SUPERSEDED
CONFLICTING_RELATION_ROLES
```

### 18.10 Duplicate and local reconciliation

```text
EXACT_DUPLICATE_NODE
EXACT_DUPLICATE_EDGE
EXACT_DUPLICATE_EVIDENCE_SPAN
INCOMPATIBLE_DUPLICATE_ID
REPEATED_LOCAL_CANDIDATE_EVIDENCE_MERGED
POSSIBLE_LOCAL_DUPLICATE
```

### 18.11 Normalization

```text
SEMANTIC_NORMALIZATION_PENDING_REVIEW
UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY
NORMALIZATION_RULE_NOT_APPROVED
NORMALIZATION_RULE_OUTPUT_MISMATCH
```

`SEMANTIC_NORMALIZATION_PENDING_REVIEW` is informational and does not reject or mark the
candidate `needs_review`. `UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY` blocks the
attempted identity, linking, duplicate-suppression, merge, or consolidation operation.

### 18.12 Abstentions

```text
ABSTENTION_REASON_INVALID
ABSTENTION_SCOPE_INVALID
ABSTENTION_TARGET_MISMATCH
ABSTENTION_EVIDENCE_INVALID
PROCESSING_FAILURE_MISCLASSIFIED_AS_ABSTENTION
```

### 18.13 Deferred resolution

```text
DEFERRED_RECORD_NOT_FOUND
DEFERRED_RECORD_NOT_IN_REQUEST
DEFERRED_DISPOSITION_INVALID
DEFERRED_ACCEPTED_WITHOUT_VALIDATED_CANDIDATE
DEFERRED_CANDIDATE_MISMATCH
```

## 19. Validation-result record

Each parsed candidate, abstention, deferred resolution, and processing failure must have a
corresponding deterministic validation result.

Recommended record shape:

```json
{
  "validationContractVersion": "0.1.0",
  "validatorVersion": "...",
  "ruleVersion": "...",
  "requestID": "...",
  "requestSha256": "...",
  "outputID": "...",
  "parsedOutputSha256": "...",
  "recordType": "candidate_node",
  "recordID": "node-0001",
  "candidateValidationStatus": "validated",
  "normalizationStatus": "pending_review",
  "normalizedLabel": "VIC",
  "normalizationMethod": "llm_proposed_semantic",
  "normalizationRuleID": null,
  "findings": [
    {
      "stage": "V6",
      "code": "SEMANTIC_NORMALIZATION_PENDING_REVIEW",
      "severity": "info",
      "message": "Semantic normalization requires localized review.",
      "jsonPointer": "/candidateNodes/0/normalizedLabelProposal",
      "expected": "approved deterministic normalization or later review",
      "observed": "VIC"
    }
  ],
  "validatedEvidenceSpanIDs": ["evidence-0001"],
  "resolvedSourceEndpointID": null,
  "resolvedTargetEndpointID": null,
  "supersededByRecordID": null,
  "inputRecordHash": "...",
  "ontologySha256": "...",
  "targetInventorySha256": "...",
  "sourceUnitContractSha256": "...",
  "candidateSchemaSha256": "...",
  "validationResultHash": "..."
}
```

Allowed `recordType` values are:

```text
candidate_node
candidate_edge
abstention
deferred_record
processing_failure
envelope
```


For `candidate_node` results, the following normalization fields are required:

```text
normalizationStatus
normalizedLabel
normalizationMethod
normalizationRuleID
```

`candidateValidationStatus` and `normalizationStatus` are independent required fields for
candidate-node results. Other record types use `recordValidationStatus`; adjudication
status is never present in this artifact. Each finding records exactly one stage-owned
stable code, severity, concise public message, affected JSON Pointer, and safe expected
and observed values. Unsafe or sensitive values are represented by hashes. The result
also binds the request, parsed output, validator version, rule version, and relevant
ontology/profile/contract/schema hashes.

Allowed `normalizationMethod` values are:

```text
none
deterministic_rule
llm_proposed_semantic
```

The normalized label in this validation artifact is pipeline-owned metadata. A later
adjudication artifact may record its own normalization decision separately. Neither is
evidence, and neither alters the verbatim candidate label in the parsed candidate.

The record must not include a free-form hidden reasoning trace. A concise public
`validationNote` may be added only when a stable code is insufficient for human review.

## 20. Determinism and hashes

### 20.1 Deterministic validation

Given identical:

- candidate envelope;
- request record;
- source-unit artifacts;
- target profile;
- ontology specification;
- Phase B context;
- validator configuration; and
- validator version;

validation results must be byte-identical after canonical serialization.

### 20.2 Canonical serialization

Canonical validation JSON uses:

- UTF-8;
- sorted object keys;
- no insignificant whitespace;
- `ensure_ascii=false`;
- deterministic record ordering; and
- LF line termination.

Timestamps belong in a run manifest and do not participate in canonical validation-result
identity.

### 20.3 Result hash

`inputRecordHash` is computed over the canonical serialized input record.

`validationResultHash` is computed over the canonical validation-result projection that
excludes `validationResultHash` itself.

## 21. Pipeline-generated assertions after validation

Automatic candidate validation does not count pipeline-derived ontology assertions as
independent model predictions.

After later adjudication accepts the underlying candidate, the pipeline may materialize:

- `EvidenceSpan` nodes;
- `hasEvidence` relations;
- `wasExtractedBy` relations;
- concrete-class superclass membership;
- authorized parent-property assertions;
- `Paper → reports → accepted discourse node`;
- `Paper → discussesRelatedWork → RelatedResearch`; and
- `Paper → hasLimitation → Limitation`.

These assertions retain pipeline provenance and are evaluated as pipeline behavior, not
LLM extraction output.

## 22. Warnings versus failures

Warnings do not change a candidate from `validated` unless this contract explicitly says
otherwise. Initial warning-level conditions are limited to:

```text
UNREFERENCED_EVIDENCE_SPAN
```

The following produce candidate-level `needs_review` rather than automatic rejection:

```text
POSSIBLE_LOCAL_DUPLICATE
ATOMICITY_VIOLATION when the conflation is plausible but not deterministic
```

`SEMANTIC_NORMALIZATION_PENDING_REVIEW` is a field-level normalization outcome. It does
not change an otherwise valid candidate to `needs_review` and does not make the envelope
`partially_valid`. `UNVALIDATED_NORMALIZATION_USED_FOR_IDENTITY` is a hard failure for the
attempted identity, linking, duplicate-suppression, merge, or consolidation operation, but
the underlying candidate may remain valid under its verbatim label.

All other applicable codes are hard failures, suppressions, or deferred outcomes as
specified in this contract.

## 23. Non-goals

This contract does not:

- determine scientific truth;
- perform gold-standard matching;
- define inter-annotator agreement;
- set model-comparison thresholds;
- calibrate model confidence;
- perform global entity consolidation;
- resolve DOI-less citations;
- interpret figures unavailable in canonical Markdown;
- repair damaged source text;
- normalize metric or parameter values numerically;
- adjudicate ontology revisions;
- write to Neo4j; or
- mutate frozen Phase B artifacts.

## 24. Contract-freeze gate

This contract may be marked final after:

- [x] the candidate-output schema passes Draft 2020-12 validation;
- [x] every model-emittable operational target is authorized consistently with the final
      machine-readable target profile;
- [x] no pipeline-generated, context-only, out-of-scope, or follow-on target can be
      emitted improperly;
- [x] evidence literal, offset, source-unit, and document-offset rules align exactly with
      the frozen source-unit contract;
- [x] model-owned and pipeline-owned fields are separated explicitly;
- [x] validation outcomes are separated from adjudication outcomes;
- [x] verbatim labels remain authoritative and normalization review is represented as a
      separate field-level lifecycle that does not block an otherwise valid candidate;
- [x] domain/range validation uses operational signatures without broadening them;
- [x] edge-specific evidence independence is frozen;
- [x] use/mention/reference precedence is frozen;
- [x] duplicate, local-reconciliation, abstention, and deferred-resolution rules are
      frozen;
- [x] stable validation codes are unique and classified;
- [x] validation-result determinism and hashing are frozen;
- [x] focused static contract tests pass; and
- [x] no unresolved methodological contradiction remains.

## 25. Implementation-acceptance gate

After the contract is frozen, the validator implementation is accepted only after:

- [ ] a validator loads the frozen target profile and ontology without duplicating their
      semantic content in code;
- [ ] representative valid and invalid candidate envelopes exercise all validation
      stages;
- [ ] evidence offsets are tested for ASCII, non-ASCII Unicode, repeated strings, Markdown
      syntax, tables, captions, and equation-with-prose cases;
- [ ] node action, identity, attribute, and abstract-class cases are tested;
- [ ] deterministic and semantic label-normalization cases are tested, including the rule
      that pending normalization cannot drive identity or consolidation;
- [ ] every active relation operational signature is tested with valid and invalid
      endpoints;
- [ ] edge-specific evidence and precedence rules are tested;
- [ ] deferred-record and abstention cases are tested;
- [ ] exact duplicates and possible semantic duplicates are distinguished;
- [ ] processing failures remain distinct from semantic abstentions;
- [ ] repeated validations are byte-identical;
- [ ] validation-result hashes reproduce exactly;
- [ ] all twelve Pilot 1 artifacts can be validated after source-unit generation; and
- [ ] no frozen ontology, Phase A, Phase B, target-profile, or source-unit artifact is
      mutated.

## 26. Acceptance statement

Passing the contract-freeze gate makes this document the final binding evidence-validation
contract for Publication Pilot 1. Passing the later implementation-acceptance gate proves
that the validator implementation conforms to the frozen contract.

Any later change to evidence authority, offset semantics, operational target eligibility,
domain/range rules, precedence, status interpretation, or stable validation codes requires
a contract-version increment and rerunning all affected candidate validations.
