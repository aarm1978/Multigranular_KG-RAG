# Publication Production Acceptance Policy v0.1

**Project:** Dissertation CS — Study 2
**Workstream:** Publication semantic extraction
**Policy ID:** `publication-production-acceptance-policy`
**Policy version:** `0.1.0-draft.2`
**Status:** **APPROVED FOR IMPLEMENTATION — NOT FROZEN**
**Date:** 2026-09-24
**Roadmap milestone:** Step 4 — Publication Production Acceptance Policy

---

## 1. Purpose

This policy prospectively defines which automatically generated Publication semantic outputs are eligible to enter the **production accepted-semantic projection** used for downstream Publication graph construction and confirmatory extractor evaluation.

This policy is a **construction control**, not an additional semantic-correctness test.

Its purpose is to ensure that:

1. the Publication graph is produced by a predeclared autonomous procedure;
2. production inclusion is not changed after observing Human Core or other confirmatory evaluation results;
3. the same autonomous semantic output is used both for KG construction and as the extractor prediction set for Human Core N=5 evaluation;
4. previously frozen validation contracts remain authoritative rather than being reinterpreted by a new acceptance layer.

Passing production acceptance means only that an output is admissible under the frozen construction procedure. It does **not** establish that the assertion is scientifically true.

---

## 2. Scope

This policy applies only to **Publication production-scale semantic extraction** in Study 2.

It governs the boundary between:

1. provider/model response;
2. parsing and trusted deterministic bindings;
3. frozen V1–V12 Publication candidate validation;
4. production accepted-semantic projection;
5. downstream post-acceptance semantic materialization and pre-alignment graph construction.

This policy does **not** govern:

- Human Core N=5 annotation or scoring;
- N=2 human-to-human reliability;
- pooled-reference candidate eligibility or human adjudication;
- completeness audit;
- SciERC evaluation;
- ablations;
- cross-source semantic alignment;
- canonical entity consolidation;
- final KG assembly;
- GraphRAG comparison;
- semantic correctness adjudication.

Those remain separate roadmap stages and contracts.

---

## 3. Authority hierarchy

This policy MUST remain compatible with the frozen Publication authorities in force for the production run, including the frozen:

- ontology authority;
- Publication target inventory / target profile;
- source-unit contract;
- candidate-output schema;
- request/provider schema;
- prompt authority;
- parser contract;
- deterministic endpoint binding;
- deterministic evidence metadata binding;
- Publication evidence-validation contract and V1–V12 validator;
- authority bundle / run provenance requirements.

If this policy conflicts with an already-frozen upstream authority, the frozen upstream authority governs unless a reproducible blocker justifies a separately reviewed and versioned amendment.

This policy MUST NOT silently modify V1–V12 semantics.

---

## 4. Core acceptance rule

> **A Publication semantic candidate is automatically accepted for production if and only if it is present in the frozen V12 `usable_pipeline_output` for the processable response selected under Section 8 of this policy.**

Production acceptance therefore **inherits** the frozen automatic-validation boundary.

The acceptance layer MUST NOT:

- promote a `rejected` candidate to accepted;
- promote a `needs_review` candidate to accepted;
- reactivate a `superseded` candidate as an independent assertion;
- promote an unresolved `deferred` candidate;
- repair, split, rewrite, normalize, or reinterpret semantic candidates;
- introduce a new confidence threshold;
- introduce LLM-as-judge logic;
- use Human Core, pooled-reference, SciERC, or later human judgments to decide production inclusion.

---

## 5. Candidate lifecycle and production disposition

The frozen validator currently provides five candidate-level lifecycle states:

- `validated`
- `rejected`
- `needs_review`
- `superseded`
- `deferred`

Authorized abstentions and processing failures are separate record types/outcomes and are not candidate-level lifecycle states.

### 5.1 `validated`

**Production disposition:** `include`

A candidate whose final V12 `candidateValidationStatus` is `validated` and that appears in `usable_pipeline_output` is eligible for production inclusion.

Production inclusion does not imply semantic truth.

### 5.2 `rejected`

**Production disposition:** `exclude_rejected`

A rejected candidate MUST NOT enter the accepted-semantic projection.

`rejected` means that the candidate violated an applicable hard construction/validation rule. Examples include, depending on the frozen validator:

- invalid or missing required evidence;
- source/request/authority mismatch;
- unauthorized target or action;
- ontology/class/relation mismatch;
- invalid endpoint lifecycle;
- invalid domain/range;
- insufficient relation-specific evidence;
- forbidden mutation or identity behavior.

A rejected candidate MUST be preserved in the validation/provenance record for audit and later error analysis.

`rejected` MUST NOT be interpreted as equivalent to “human-adjudicated false.”

### 5.3 `needs_review`

**Production disposition:** `exclude_needs_review`

A `needs_review` candidate MUST NOT enter the autonomous production accepted-semantic projection.

Under the currently frozen validator, `needs_review` is produced only through review-level ambiguity such as:

- `ATOMICITY_VIOLATION`;
- `POSSIBLE_LOCAL_DUPLICATE`.

This policy does not create a new human annotation step to resolve those cases before production.

A `needs_review` candidate:

- MUST remain preserved with its original candidate content, evidence references, validation findings, and provenance;
- MUST NOT be silently repaired;
- MUST NOT trigger semantic resampling;
- MAY later be eligible for separately frozen pooled-reference contribution under Step 5, but production exclusion does not itself determine pooled-reference eligibility.

#### 5.3.1 Preserved identity uncertainty for later semantic alignment

A preserved `POSSIBLE_LOCAL_DUPLICATE` record MAY later be supplied to the separately governed semantic-alignment stage as **unresolved identity evidence**.

This later use:

- MUST NOT make the record a member of the Step 4 production accepted-semantic projection;
- MUST NOT retroactively change the Human Core N=5 prediction set;
- MUST NOT be treated as proof of co-reference merely because the validator raised `POSSIBLE_LOCAL_DUPLICATE`;
- MAY allow the preserved source-local occurrence and its EvidenceSpan(s) to contribute additional provenance/evidence to an accepted or canonical entity **only if** the separately frozen alignment procedure later establishes co-reference;
- MUST preserve a reconstructable mention/source-occurrence → canonical mapping rather than silently moving or rewriting evidence.

`ATOMICITY_VIOLATION` candidates are not automatically eligible for this identity-resolution pathway because their uncertainty concerns semantic unit structure rather than merely local identity. `rejected` candidates are likewise not automatically eligible.

The exact Step 15 alignment method—including whether a bounded LLM-assisted same-entity classifier is used—belongs to the later semantic-alignment contract and is outside this policy.

The cost of conservative autonomous exclusion is measured by downstream evaluation rather than repaired retrospectively.

### 5.4 `superseded`

**Production disposition:** `exclude_superseded`

A superseded candidate MUST NOT be materialized as an independent production assertion.

The frozen validator may supersede candidates because of:

- exact duplicate suppression;
- repeated local candidate evidence merging;
- authorized stronger-role precedence, such as a stronger specialized relation superseding a weaker one for the same endpoint pair.

The superseded record MUST remain preserved with `supersededByRecordID` and relevant findings.

Supersession is a representation/lifecycle decision, not a declaration that the original text was unsupported.

### 5.5 `deferred`

**Production disposition:** `exclude_deferred`

A candidate whose final lifecycle state remains `deferred` MUST NOT enter the accepted-semantic projection.

A deferred record may have proposed dispositions such as:

- `resolved_accepted`;
- `resolved_rejected`;
- `remain_deferred`;
- `insufficient_evidence`;
- `out_of_scope`;
- `type_conflict`;
- `unsupported_role`.

If the frozen resolver/validator process successfully resolves the deferred case and the resulting candidate remains `validated`, normal validated-candidate acceptance applies.

If the case remains deferred at the end of the production request, it remains unresolved. The production policy MUST NOT force resolution merely to eliminate pending cases.

---

## 6. Normalization boundary

A candidate may be:

- `candidateValidationStatus = validated`
- while simultaneously having `normalizationStatus = pending_review`.

Such a candidate remains eligible for production inclusion because the semantic candidate itself passed V1–V12.

However:

- the verbatim source-grounded label remains authoritative for production;
- a pending semantic normalization MUST NOT be used to establish identity;
- it MUST NOT cause duplicate suppression;
- it MUST NOT cause canonical merging;
- it MUST NOT be used for cross-source consolidation.

Semantic alignment and cross-source canonicalization remain later Study 2 stages.

---

## 7. Abstention and omission

### 7.1 Authorized abstention

A validated authorized abstention produces **no production semantic assertion**.

An abstention is not equivalent to rejection.

It records that the extractor explicitly declined to assert a plausible target under an authorized semantic abstention reason.

The policy MUST preserve the abstention record and its provenance.

If the Human Core contains an assertion corresponding to an abstained target, the absence of a production prediction may contribute to false-negative behavior in confirmatory evaluation.

### 7.2 Candidate absence

Absence of a candidate is not automatically an abstention.

The production policy MUST NOT synthesize missing candidates, missing abstention records, or inferred semantic assertions.

---

## 8. Processing failures and bounded technical retry

Processing failures are distinct from semantic outputs.

Examples recognized by the current validation path include:

- `INVALID_JSON`;
- `TIMEOUT`;
- `API_ERROR`;
- `TRUNCATED_RESPONSE`;
- `TOKEN_LIMIT`;
- `RETRY_EXHAUSTED`.

A processing failure is not:

- a semantic rejection;
- a semantic abstention;
- evidence that a target is absent.

### 8.1 Maximum attempts

Each production request permits:

> **one initial provider attempt plus at most one technical retry**

for a maximum of **two provider attempts per request**.

### 8.2 Retry eligibility

A technical retry MAY occur only when the prior attempt produced no processable semantic response because of a processing failure.

The retry MUST use the same immutable:

- source/request content;
- eligible targets;
- model;
- prompt;
- ontology and contract authorities;
- generation parameters;
- provider configuration, except unavoidable provider-generated request identifiers or timestamps.

Every attempt MUST be preserved with provenance.

### 8.3 First-processable-response rule

The first processable semantic response ends provider sampling for that request.

The pipeline MUST NOT retry because a processable response:

- contains rejected candidates;
- contains `needs_review` candidates;
- contains deferred candidates;
- contains abstentions;
- produces fewer candidates than expected;
- produces lower apparent semantic quality than desired.

This prohibition prevents semantic resampling until a more favorable model output appears.

### 8.4 Retry exhaustion

If both permitted attempts fail to produce a processable semantic response:

- the request receives a terminal processing-failure disposition;
- no semantic assertion from that request enters the production accepted-semantic projection;
- the failure MUST remain explicit and auditable;
- the failure MUST NOT be converted into an abstention or semantic rejection.

---

## 9. Production accepted-semantic projection

Step 4 implementation MUST create an immutable accepted-semantic projection for each processable production output.

The projection MUST be derived deterministically from the frozen `usable_pipeline_output`.

It MUST contain, directly or by stable reference, sufficient provenance to identify:

- production acceptance policy ID/version;
- acceptance basis;
- authority bundle;
- request ID;
- output ID;
- selected provider attempt;
- validation result hash;
- usable-pipeline-output hash;
- accepted nodes;
- accepted edges;
- provider/model/run provenance;
- source/evidence bindings required by downstream materialization.

The projection SHOULD preserve stable references to exclusion/validation artifacts rather than copying rejected or unresolved candidates into the accepted projection itself.

Preserved unresolved-identity records MAY be emitted to a **separate alignment/provenance sidecar artifact** for later Step 15 use. That sidecar:

- is not part of the accepted semantic projection;
- is not part of the Step 7 prediction set;
- must preserve the original validation status and evidence references;
- must not contain silently repaired or newly asserted semantics.

The accepted projection MUST be content-addressable or otherwise hashed so the exact prediction set can be frozen before confirmatory evaluation.

---

## 10. Relationship to post-acceptance semantic materialization

The existing post-acceptance semantic materializer consumes a neutral accepted-semantic projection and may derive deterministic non-model-authored semantics under separately frozen rules.

In particular, deterministic post-acceptance derivation such as generic `ciroh:mentions`:

- MUST operate only from the accepted semantic projection;
- MUST NOT rescue a rejected, deferred, superseded, or `needs_review` model candidate;
- MUST retain its explicit `notModelAuthored` / derivation provenance;
- MUST remain distinguishable from model-authored extraction quality.

Derived post-acceptance relations are construction outputs, not evidence that the model itself extracted those relations.

---

## 11. Relationship to Human Core N=5 evaluation

The accepted semantic projection frozen under this policy is the authoritative autonomous Publication semantic output used for both:

1. downstream Publication KG construction; and
2. extractor-vs-Human-Core N=5 confirmatory evaluation.

The evaluation MUST NOT substitute:

- a human-corrected prediction set;
- pooled-adjudicated candidates;
- retrospectively repaired `needs_review` candidates;
- later canonicalization results;
- semantic resampling outputs selected after observing Human Core performance.

Consequences are intentional:

- a valid Human Core assertion omitted from the production projection may contribute a false negative;
- duplicate overproduction that survives the accepted production boundary may contribute false positives;
- conservative autonomous behavior may trade recall for a stricter evidence/validation boundary.

These outcomes are empirical properties of the frozen extractor/construction procedure and MUST be reported rather than repaired post hoc.

---

## 12. Relationship to pooled human adjudication

Production acceptance and pooled-reference construction answer different questions.

- **Production acceptance:** What is the autonomous Publication construction pipeline willing to assert under the frozen contracts?
- **Pooled adjudication:** Which blinded candidate assertions are judged by humans to be supported?

Therefore:

- production exclusion does not automatically imply pooled-reference ineligibility;
- pooled-reference contributors and candidate-layer eligibility MUST be frozen separately in Step 5;
- later human pooled adjudication MUST NOT retrospectively alter the frozen production projection used in Step 7.

### 12.1 Relationship to later semantic alignment

Production exclusion also does not imply that every preserved record is permanently irrelevant to final KG construction.

A preserved identity-uncertain source-local occurrence may later contribute to **identity resolution and provenance enrichment** if the separately frozen Step 15 alignment procedure establishes that it is co-referential with an accepted/canonical entity.

That later alignment outcome:

- changes the final aligned/consolidated representation, not the historical Step 4 prediction;
- may add the preserved occurrence/EvidenceSpan(s) as contributing provenance to the canonical entity;
- must preserve the original `needs_review` lifecycle record;
- must not be used to recompute or improve Step 7 Human Core P/R/F1.

---

## 13. Auditability requirements

The production run MUST preserve enough information to reconstruct, for every request:

- all provider attempts;
- which attempt, if any, became the first processable response;
- raw-response hashes;
- parse status;
- deterministic endpoint/evidence bindings;
- V1–V12 validation outputs;
- candidate lifecycle states;
- abstentions;
- deferred records;
- processing failures;
- accepted semantic projection;
- preserved unresolved-identity sidecar records, when applicable;
- acceptance policy version/hash;
- downstream derived semantic outputs.

No excluded semantic record may be silently deleted merely because it did not enter the production graph.

---

## 14. Scientific rationale

This policy is intentionally thin. It does not introduce a new inference or quality-estimation subsystem.

| Problem / validity threat | Rationale | Policy decision | Status |
|---|---|---|---|
| Post-hoc adaptation of graph contents to confirmatory evaluation | The evaluated artifact should be produced by a procedure fixed before viewing confirmatory outcomes | Freeze production acceptance before production-scale extraction / Human Core scoring | **anchored** |
| Conflating automatic admissibility with semantic truth | Construction contracts and human-reference evaluation serve different epistemic roles | Production acceptance establishes admissibility only; correctness is measured independently | **anchored** |
| Duplicating or overriding frozen V1–V12 logic | A second semantic-quality layer would add unvalidated rules and unnecessary scope | Inherit `usable_pipeline_output`; do not override candidate lifecycle states | **anchored / argued** |
| Repeatedly sampling until an LLM produces a preferred answer | Semantic resampling can make the prediction procedure adaptive and difficult to interpret | Stop at the first processable response | **anchored / argued** |
| Losing an entire request because of transport/parsing failure | Technical failure is distinct from semantic behavior | Permit one bounded identical technical retry, with all attempts preserved | **argued** |
| Treating unresolved outputs as if they were human-adjudicated false | Automatic uncertainty and human semantic judgment are different | Preserve all excluded/unresolved outputs and separate later pooled adjudication | **anchored** |
| Losing potentially useful evidence from local identity uncertainty | Production exclusion and later entity-resolution have different roles | Preserve `POSSIBLE_LOCAL_DUPLICATE` as unresolved identity evidence that may later contribute provenance if Step 15 establishes co-reference, without changing Step 7 predictions | **argued** |
| Losing provenance during construction | Study 2 requires evidence-grounded, auditable graph construction | Preserve provider/run, validation, evidence, and disposition provenance | **anchored** |

### Literature basis

The research-design rationale is consistent with:

- Hevner et al. (2004): rigorous construction and evaluation of artifacts in design-oriented research;
- Peffers et al. (2007): separation of design/development and evaluation activities;
- Gregor & Hevner (2013): distinction between artifact construction and the broader knowledge contribution;
- Venable, Pries-Heje, & Baskerville (2016): purposeful evaluation and the distinction between formative and summative evaluation;
- W3C PROV / PROV-O (2013): explicit representation of provenance;
- Dwork et al. (2015): risks of adaptive reuse of evaluation information;
- Nosek et al. (2018): value of prospectively separating analytic/design decisions from confirmatory evaluation.

These sources justify the research-design principles. They do not imply that every implementation detail is a separate research contribution.

---

## 15. Non-goals

This policy MUST NOT expand into:

- manual adjudication of all production candidates;
- LLM-as-judge acceptance;
- two-model consensus acceptance;
- confidence calibration;
- active learning;
- cross-source identity resolution;
- semantic alignment;
- canonical entity construction;
- final graph assembly;
- pooled-reference adjudication;
- a new Publication annotation program.

Those are outside Step 4.

---

## 16. Freeze criteria

This policy may be frozen only after:

1. the researcher approves the normative rules in this document;
2. the implementation is shown to derive production acceptance deterministically from the existing frozen V1–V12 `usable_pipeline_output`;
3. the one-retry technical policy is implemented and tested without semantic resampling;
4. the accepted-semantic projection is deterministic and hashable;
5. focused tests demonstrate lifecycle preservation for:
   - `validated`;
   - `rejected`;
   - `needs_review`;
   - `superseded`;
   - `deferred`;
   - authorized abstention;
   - processing failure;
6. no Human Core, pooled-reference, SciERC, or LLM-judge data are consumed by the production acceptance implementation;
7. the policy artifact itself records its final hash/version and the accepted implementation checkpoint.

Until those conditions are met, this document remains **APPROVED FOR IMPLEMENTATION / NOT FROZEN**.

---

## 17. Intended next implementation boundary

Following researcher approval, Codex should implement only the smallest Step 4 increment necessary to:

1. encode this production acceptance policy without changing V1–V12 semantics;
2. implement the bounded technical retry rule;
3. materialize the deterministic accepted-semantic projection;
4. preserve exclusion/failure provenance and, where applicable, emit a separate unresolved-identity sidecar without treating it as accepted KG content;
5. add focused regression tests;
6. create the policy/freeze artifacts required to close Step 4.

Codex should not begin Publication production-scale provider calls until the policy is reviewed, implemented, tested, and formally frozen.
