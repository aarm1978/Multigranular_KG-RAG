# Study 2 Step 5 Publication Evaluation Authority v0.1

**Project:** Dissertation CS — Study 2  
**Workstream:** Publication semantic extraction and evaluation  
**Authority ID:** `publication-step5-evaluation-authority`  
**Authority version:** `0.1.0-draft.2`  
**Status:** **DRAFT — NOT FROZEN**  
**Date:** 2026-09-25  
**Roadmap milestone:** Step 5 — Remaining Publication Evaluation Contracts

---

## 1. Purpose

This authority prospectively defines the remaining Publication evaluation procedures required by Study 2 after closure of the Publication Production Acceptance Policy.

It governs:

- pooled-reference contributor and source-unit scope;
- pooled candidate-layer eligibility;
- conservative source-local deduplication;
- system-provenance blinding;
- non-generative human pooled adjudication;
- the bounded model-blind completeness audit; and
- the SciERC external scientific-information-extraction anchor.

The procedures defined here serve distinct evaluation purposes and MUST remain separate from autonomous production acceptance, Human Core confirmatory scoring, later semantic alignment/consolidation, and final KG assembly.

This authority operationalizes the following overarching design:

1. the frozen autonomous Publication extractor produces C1;
2. C1 contributes candidate assertions but does not determine human truth judgments;
3. humans judge pooled C1 assertions without repairing or extending them;
4. an independent bounded human audit assesses observed pool saturation without seeing C1 output; and
5. SciERC provides an independent external scientific-IE anchor under its own native schema.

This authority does **not** claim that the pooled reference is exhaustive gold.

---

## 2. Scope and boundaries

### 2.1 In scope

This authority applies only to:

- Study 2 Publication semantic extraction;
- the six prospectively selected complementary pooled primary evaluation units;
- routed `extract_and_evaluate` Publication targets;
- the C1 production realization selected under the frozen Production Acceptance Policy;
- pooled human judgment;
- the six-unit completeness audit; and
- the bounded SciERC entity/relation external-anchor evaluation.

### 2.2 Out of scope

This authority does not define or modify:

- ontology design or expansion;
- deterministic Phase A or Phase B extraction;
- Publication source-unit construction;
- Publication candidate generation semantics;
- frozen V1–V12 automatic validation;
- Production Acceptance;
- Human Core N=5 annotation;
- Human Core N=2 reliability;
- Human Core N=5 Precision/Recall/F1 scoring;
- `extract_and_monitor` completeness;
- non-Publication semantic extraction;
- cross-source entity alignment;
- canonicalization or consolidation;
- final KG assembly;
- GraphRAG evaluation;
- Study 3 retrieval or QA evaluation;
- Study 4 expert evaluation.

---

## 3. Frozen upstream authorities

This authority MUST consume, and MUST NOT silently modify or reinterpret, the frozen authorities already governing Publication extraction and evaluation.

These include, as applicable at Step 5 freeze:

1. **CIROH ontology v0.1.5**
   - validated OWL SHA-256:
     `ce5f6d3d8ac926dc8ff872c9a36066758a86068b6681417bf7edc6aaeccf1e71`.

2. **Frozen deterministic Publication Phase B outputs and tests.**

3. **Publication target authority**
   - current v0.1.5 target universe:
     `src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml`.

4. **Publication Source-Unit Contract**
   - `docs/publication_source_unit_contract.md`;
   - its canonical source, request-context, evidence-boundary, primary/context-unit, offset, and hash rules remain binding within their original scope.

5. **Publication candidate-output and provider/request schemas** in force for the frozen production realization.

6. **Publication prompt authority** in force for the frozen production realization.

7. **Deterministic endpoint binding** and **deterministic evidence metadata binding** authorities.

8. **Publication Evidence-Validation Contract and V1–V12 validator**
   - candidate lifecycle statuses and validation findings retain their frozen meanings.

9. **Study 2 Evaluation Protocol Amendment v0.1**
   - `docs/study2_evaluation_protocol_amendment_v0.1.md`.

10. **Publication Human Core Amended Matching Contract v0.1**
    - `docs/publication_human_core_amended_matching_contract_v0.1.md`;
    - contract version `0.1.0`;
    - its formal scope remains Human Core reliability and extractor-to-Human-Core evaluation.
    - Step 5F adopts specified matching predicates and one-to-one assignment principles prospectively under a separately defined Step 5F comparison scope; this does not extend the formal scope of the Human Core contract.

11. **Publication Production Acceptance Policy v0.1**
    - `docs/publication_production_acceptance_policy_v0.1.md`;
    - policy ID `publication-production-acceptance-policy`;
    - version `0.1.0`;
    - status `FROZEN`.

12. **Frozen Human Core sampling analysis**
    - `data/curation/papers/m2/human_core_sampling_analysis/publication_human_core_sampling_analysis_v0.1.0.md`;
    - companion JSON artifact.

13. **Historical Publication Annotation and Adjudication Guidelines**
    - `docs/publication_annotation_adjudication_guidelines.md`;
    - retained as an upstream historical authority for its original annotation/candidate-adjudication scope.

The historical guideline's model-candidate resolutions such as:

- `edited_label`;
- `edited_class`;
- `edited_relation`;
- `edited_endpoint`;
- `edited_evidence`;
- `linked_existing`;
- `merged_local_duplicate`; and
- `split_candidate`

MUST NOT be inherited by pooled-reference adjudication under Section 10 of this authority.

If this Step 5 authority conflicts with a frozen upstream authority, the frozen upstream authority governs unless a reproducible blocker is documented and separately approved through versioned change control.

---

## 4. Terminology

### 4.1 C1

**C1** is the single frozen Publication production realization generated under the frozen production authorities and Production Acceptance Policy.

C1 is the sole model-generated contributor to the pooled reference.

No second stochastic replicate, additional LLM, additional architecture, ablation system, historical DEV output, Human Core annotation, or Annotator B record contributes pooled candidates.

### 4.2 Primary evaluation unit

A **primary evaluation unit** is one of the six prospectively selected `primarySourceUnitID` values defined under Section 6.

The pooled sample therefore has exactly six primary evaluation units from six distinct primary publications.

### 4.3 Context source unit

A **context source unit** is a canonical source unit legitimately included in a frozen C1 request envelope as context under the frozen source-unit/request-context authority.

A context source unit:

- may provide valid evidence when explicitly cited by a candidate;
- retains its own source-unit identity, offsets, and hashes;
- does not become an additional pooled sampling unit;
- does not increase N beyond six; and
- does not expand the sample to another publication.

### 4.4 Pre-dedup pooled candidate layer

The **pre-dedup pooled candidate layer** is the set of C1 candidate records that satisfy Section 7 eligibility before the conservative deduplication rules in Section 8 are applied.

### 4.5 Pooled judgment item

A **pooled judgment item** is an assertion-level item produced after Section 8 deduplication and projected through Section 9 blinding for human judgment.

### 4.6 Positive pooled reference

The **positive pooled reference** is the final set of C1 assertions retained after:

- pooled eligibility;
- conservative deduplication;
- human support judgment;
- required local-duplicate resolution; and
- exclusion of unresolved judgments.

It remains candidate-conditioned and MUST NOT be described as exhaustive gold.

### 4.7 Source-local assertion

A **source-local assertion** is an assertion whose semantic identity remains bounded to one source artifact before later cross-source semantic alignment and consolidation.

### 4.8 Duplicate-review group

A **duplicate-review group** is a blinded group of separate pooled candidates whose frozen validator lineage identified unresolved possible local duplication.

Grouping does not itself establish equivalence.

### 4.9 System provenance

**System provenance** includes model/provider/run/request/output identity, candidate lifecycle status, validator findings, production disposition, retry information, and other metadata revealing how the autonomous system produced or treated a candidate.

### 4.10 Source provenance

**Source provenance** includes the publication, source units, sections, exact evidence, offsets, hashes, and deterministic source context needed to judge an assertion.

Source provenance is not system provenance and remains visible when needed for human judgment.

### 4.11 Audit-supported assertion

An **audit-supported assertion** is a positive source-supported assertion independently identified by the bounded completeness-audit expert under Section 11.

The term does not imply independently replicated human truth.

### 4.12 Audit-supported unmatched assertion

An **audit-supported unmatched assertion** is an audit-supported assertion for which no qualifying one-to-one match exists in the frozen positive pooled reference under Section 11.9–11.12.

### 4.13 Observed pool saturation

**Observed pool saturation** is the proportion of audit-supported assertions represented in the frozen positive pooled reference within the six bounded audit scopes.

It is relative to the independent bounded audit and is not an estimate of universal or true completeness.

---

## 5. Step 5 freeze-time order and later execution order

The integrated Step 5 authority MUST NOT become frozen before the exact bindings required by its own Freeze Gate have been deterministically materialized, validated, and incorporated.

The normative order is:

```text
researcher methodological approval of DRAFT
    ↓
deterministic freeze-time materialization and validation
    ↓
incorporation of exact bindings, IDs, versions, and hashes into the authority/freeze artifacts
    ↓
final researcher approval of the fully bound authority
    ↓
Step 5 authority FROZEN/CLOSED
    ↓
Step 6: execute and freeze C1 production outputs
    ↓
model-blind exhaustive audit on all six units by an eligible independent audit expert
    ↓
freeze independent audit artifact
    ↓
construct C1 eligible pooled candidate layer
    ↓
apply conservative pooled deduplication
    ↓
generate blinded pooled judgment projection
    ↓
perform pooled human adjudication
    ↓
freeze positive pooled human-adjudicated reference and unresolved side records
    ↓
perform post-freeze audit ↔ pooled-reference comparison
```

SciERC execution may proceed after Step 5 is FROZEN/CLOSED, in parallel with later pooled-reference/completeness work, provided its own freeze-time bindings are complete and it does not alter C1 or any Publication evaluation authority.

The following information-flow restrictions are mandatory:

1. Step 5 MUST remain `DRAFT — NOT FROZEN` during freeze-time materialization/validation.
2. Exact freeze-time bindings and hashes MUST be incorporated before final researcher approval.
3. C1 MUST be executed only after Step 5 is FROZEN/CLOSED.
4. C1 MUST be frozen before any completeness-audit result exists.
5. The completeness auditor MUST NOT see C1 outputs before freezing the audit artifact.
6. Pooled adjudicators MUST NOT modify C1 or the production prediction set.
7. Audit findings MUST NOT modify C1, Human Core Step 7 scoring, Production Acceptance, or the production KG.
8. The audit artifact MUST be frozen before audit-to-pool comparison.
9. The pooled reference MUST be frozen before audit-to-pool comparison.
10. Incidental observations from pooled adjudication MUST NOT be exposed to the completeness auditor before audit freeze.
11. A person previously exposed to pooled C1 judgment items from a unit MUST NOT later perform the model-blind exhaustive audit for that same unit.

---

# 5A — Pooled Contributor and Complementary N=6 Source-Unit Scope

## 6. Contributor rule

C1 is the **sole model-generated pooled contributor**.

The following MUST NOT contribute candidate assertions:

- a second C1 replicate;
- another LLM;
- another model configuration;
- an ablation;
- an alternative extraction architecture;
- historical DEV outputs;
- diagnostic outputs;
- Human Core annotations;
- Human Core reliability annotations;
- pooled human additions;
- completeness-audit findings.

The pooled reference does not claim exhaustiveness. Candidate omission is assessed separately under Section 11.

## 6.1 Complementary publication scope

The pooled sample MUST contain exactly one eligible primary evaluation unit from each primary publication not represented in Human Core.

The six publication IDs are:

```text
18
276
37
46
54
87
```

Human Core covers:

```text
10
15
16
34
79
```

Together, Human Core N=5 plus the complementary pooled N=6 cover all eleven primary publications.

This joint publication coverage MUST NOT be described as statistical representativeness.

## 6.2 Model-blind selection authority

Selection MUST use only the frozen, model-blind structural/routing metadata permitted by the existing sampling-analysis authority.

Selection MUST NOT use:

- canonical unit text;
- semantic content inspection;
- LLM output;
- provider output;
- candidate counts;
- candidate labels;
- extraction correctness;
- Human Core positive annotations;
- DEV semantic results;
- later pooled judgments;
- audit findings.

Screening/routing metadata may determine where evaluation occurs, but screening expectations MUST NOT be passed to C1 as semantic hints.

In particular, screening fields such as expected semantic content, likely reporting families, likely strata descriptions, screening rationale, expected density, or related human expectations MUST NOT augment the frozen production prompt or source evidence.

C1 receives only the ordinary frozen production inputs and routed/authorized operational targets required by its existing contracts.

## 6.3 Hard selection constraints

An eligible six-unit set MUST satisfy all of the following before any workload tie-breaker is applied:

1. exactly one primary evaluation unit from each of:
   `18`, `276`, `37`, `46`, `54`, and `87`;
2. all existing frozen source-unit exclusions;
3. complete routed scored-node-target coverage:
   **19/19**;
4. complete routed scored-relation-target coverage:
   **16/16**;
5. complete frozen sampling-stratum coverage:
   **5/5**.

No burden-control criterion may override any hard scientific coverage constraint.

## 6.4 Deterministic N=6 tie-breaker

Among all six-unit sets satisfying Section 6.3, selection MUST use this exact ordering:

1. minimize the **maximum per-unit routed scored-target exposure**;
2. among ties, minimize the **total routed scored-target exposure** across the six units;
3. among remaining ties, use lexical `sourceUnitID` ordering as the deterministic final tie-breaker.

Routed scored-target exposure is solely a **pre-semantic structural workload proxy**.

It MUST NOT be interpreted as:

- predicted adjudication time;
- semantic density;
- expected number of C1 candidates;
- expected correctness;
- semantic difficulty;
- information richness.

The exact six resulting `primarySourceUnitID` values MUST be deterministically materialized, validated, and incorporated into the Step 5 freeze artifacts before final researcher approval and before Step 5 can become FROZEN/CLOSED.

They MUST NOT be manually invented.

## 6.5 Context-unit boundary

The six selected `primarySourceUnitID` values define the sample.

A frozen C1 request may legitimately include authorized `contextSourceUnitIDs` under the frozen source-unit/request-context contract.

Valid assertions may cite evidence occurrences from those context units.

Such context units:

- remain part of the same bounded C1 request/evaluation envelope;
- MUST belong to the authorized source context for the selected primary unit;
- do not create additional pooled sampling units;
- do not expand the N=6 sample; and
- do not authorize cross-paper candidate pooling.

## 6.6 Deterministic-neutral two-unit selector for pooled second review

The two primary evaluation units used for the independent bounded second review under Section 10 MUST be selected from the already materialized six `primarySourceUnitID` values by the following fixed, content-independent procedure.

### Selector identity

```text
selectorNamespace = publication-step5-pooled-second-review-selector-v0.1.0
hashAlgorithm = SHA-256
textEncoding = UTF-8
rankingDirection = ascending hexadecimal digest
```

### Canonical hash input

For each of the six exact `primarySourceUnitID` strings, construct exactly:

```text
publication-step5-pooled-second-review-selector-v0.1.0|<primarySourceUnitID>
```

with:

- no leading or trailing whitespace;
- one literal ASCII vertical bar (`|`) between namespace and ID;
- the exact frozen `primarySourceUnitID` string;
- no newline appended before hashing.

Compute:

```text
SHA256(UTF8(canonicalHashInput))
```

and encode the digest as 64 lowercase hexadecimal characters.

### Ranking and selection

1. sort the six units by ascending lowercase SHA-256 hexadecimal digest;
2. if two digests are identical, break the collision tie by ascending lexical `primarySourceUnitID`;
3. select the first two units.

No source content, routing burden, candidate output, semantic result, or human judgment may influence this two-unit selector.

The selector namespace/version, all six canonical hash inputs, all six digests, the complete ranking, and the selected two IDs MUST be recorded in the freeze-time second-review subset artifact.

---

# 5B — Candidate-Layer Eligibility

## 7. Core eligibility principle

> A pooled-eligible candidate is a preserved C1 output that constitutes a well-defined, source-groundable semantic assertion suitable for blinded human judgment.

Pooled eligibility does **not** mean:

- production accepted;
- human supported;
- scientifically true;
- canonical;
- globally aligned.

Eligibility is evaluated independently of the Production Acceptance disposition.

## 7.1 Treatment boundary

Only candidates for routed:

```text
extract_and_evaluate
```

targets are eligible for the pooled reference.

`extract_and_monitor` outputs may remain available for separate descriptive/error analysis but MUST NOT:

- generate pooled-reference judgment items;
- enter pooled-reference denominators;
- enter the Section 11 completeness audit.

Pipeline-derived assertions, including post-acceptance generic D-26 `ciroh:mentions`, provenance edges, superclass materialization, or other derived graph semantics, MUST NOT enter the pooled candidate layer.

## 7.2 Eligible lifecycle cases

From the processable C1 production response selected under the frozen Step 4 retry/attempt policy:

### Eligible

```text
validated
```

is eligible.

A candidate with:

```text
candidateValidationStatus = validated
normalizationStatus = pending_review
```

remains eligible.

Its authoritative verbatim label governs pooled identity and judgment.

Pending normalization MUST NOT define candidate identity.

### Eligible before deduplication

```text
needs_review / POSSIBLE_LOCAL_DUPLICATE
```

is eligible for the pre-dedup pooled candidate layer.

It remains unresolved until the duplicate-review procedure defined in Sections 8 and 10.

### Eligible after an authorized resolver outcome

A deferred case that is prospectively and legitimately resolved into an ordinary:

```text
validated
```

candidate under existing frozen authority is eligible by the ordinary `validated` rule.

## 7.3 Ineligible cases

The following MUST NOT generate pooled judgment items:

```text
needs_review / ATOMICITY_VIOLATION
rejected
unresolved deferred
authorized abstention
processing failure
```

Reasons:

- an atomicity violation cannot be repaired or split by pooled adjudication;
- a hard rejected candidate failed the frozen candidate contract;
- unresolved deferred content is not a resolved assertion;
- abstentions and processing failures do not assert semantics.

Pool-ineligible does **not** mean human-adjudicated false.

## 7.4 `superseded`

A `superseded` record MUST NOT generate an independent pooled judgment item.

Its original record, evidence, and lineage MUST remain preserved.

Section 8 governs whether evidence from particular supersession reasons may be attached to a retained representative.

## 7.5 Deterministic Phase B endpoints

Deterministic Phase B endpoints may serve as:

- authorized context;
- exact existing endpoint identity; or
- relation endpoint identity

when the frozen extraction authorities already permit them.

They are **not** model contributors and MUST NOT become pooled candidate nodes merely because a C1 relation refers to them.

A C1-authored relation involving an exact deterministic endpoint may still be pooled-eligible.

## 7.6 No candidate repair

No candidate may gain pooled eligibility through:

- manual correction;
- rewriting;
- splitting;
- reclassification;
- endpoint substitution;
- evidence substitution;
- semantic resampling;
- normalization;
- name-based linking;
- canonicalization;
- cross-source alignment.

---

# 5C — Conservative Pooled Deduplication

## 8. Purpose

Pooled deduplication exists only to reduce redundant human judgment.

It MUST NOT perform:

- semantic alignment;
- canonicalization;
- cross-paper merging;
- cross-source merging;
- semantic repair;
- ontology-driven co-reference inference;
- fuzzy matching;
- embedding similarity;
- label-based identity resolution.

The fail-conservative rule is:

> If duplicate identity cannot be established from the exact governed authorities enumerated below, retain the candidates separately.

Candidates from different `sourceArtifactID` values MUST NEVER be automatically merged by Step 5C.

## 8.1 Exhaustive auto-deduplication authorities

Automatic pooled deduplication is authorized only by the following three authority classes.

No fourth implicit authority exists.

### Authority A — Frozen validator lineage establishing exact local identity

Step 5C may project an identity already established by frozen V1–V12 lineage when that lineage explicitly records:

1. exact candidate duplication; or
2. repeated local candidate evidence merging for the same assertion.

For exact duplicate validation, the frozen node duplicate key includes:

```text
sourceArtifactID
operationalTargetID
action
existingNodeID
label
attributes
sorted evidence coordinates
```

and the frozen relation duplicate key includes:

```text
sourceArtifactID
operationalRelationID
action
source endpoint
target endpoint
sorted evidence coordinates
```

A `propose_new` node may be automatically consolidated only when this frozen deterministic lineage has already established assertion identity.

Exact or case-insensitive label equality alone is never sufficient.

### Authority B — Exact governed `link_existing` node identity

Within one `sourceArtifactID`, multiple eligible `link_existing` node candidates may be consolidated when all material governed identity fields match exactly, including:

```text
operationalTargetID
action = link_existing
existingNodeID
governed structured attributes, when applicable
```

The `existingNodeID` MUST be an exact identity already authorized by the frozen request/validator context.

Name similarity or normalization cannot establish this identity.

For `propose_new`:

```text
existingNodeID = null
```

so Authority B does not apply.

### Authority C — Exact governed relation identity

After constructing the exact node representative map authorized only by Authorities A and B, relation candidates within the same `sourceArtifactID` may be consolidated when all material governed relation fields match exactly, including:

```text
operationalRelationID
action
source endpoint representative
target endpoint representative
relationScope, when governed
other frozen material structured relation fields, when applicable
```

If two endpoints require semantic interpretation to establish equivalence, the relations remain separate.

## 8.2 Explicitly forbidden duplicate signals

The following MUST NOT establish auto-deduplication:

- exact label equality for `propose_new`;
- case-insensitive label equality;
- `normalizedLabelProposal`;
- `normalizationStatus`;
- substring similarity;
- synonym inference;
- fuzzy matching;
- embedding similarity;
- ontology parent/child similarity;
- relation-strength interpretation;
- common evidence sentence alone;
- evidence proximity;
- human intuition during the deterministic dedup phase.

## 8.3 Multiple evidence occurrences

When assertion identity has already been established under Section 8.1:

- repeated evidence may be consolidated into one pooled judgment item;
- every distinct evidence occurrence MUST remain preserved.

Two evidence occurrences with identical text but different canonical coordinates remain distinct occurrences.

Evidence identity MUST retain sufficient exact source information to reconstruct:

```text
sourceArtifactID
sourceUnitID
canonical coordinates
evidenceHash
original evidenceSpanID
original contributing candidate record(s)
```

A primary pooled item may contain evidence from:

- its selected primary evaluation unit; and
- authorized context units included in the corresponding frozen C1 request/evaluation envelope.

This does not expand the N=6 sampling frame.

## 8.4 `superseded` evidence

When frozen validator lineage establishes:

- exact duplication; or
- repeated local candidate evidence merging

for the same assertion, eligible valid evidence occurrences from superseded records may be retained in the representative assertion's evidence bundle.

When supersession reflects stronger-role precedence rather than exact assertion identity:

- the weaker record does not generate an independent judgment item;
- its lineage and original evidence remain preserved;
- its evidence MUST NOT automatically be reclassified as evidence for the stronger relation.

Deduplication MUST NOT perform semantic promotion.

## 8.5 `POSSIBLE_LOCAL_DUPLICATE`

`POSSIBLE_LOCAL_DUPLICATE` candidates MUST NOT be automatically merged.

They remain separate candidate members and are placed into an opaque local duplicate-review group derived from their existing frozen validator lineage.

A duplicate-review group means only:

> these source-local candidates require an explicit later same-assertion/distinct-assertions human decision.

It does not mean that the candidates are duplicates.

Case-insensitive label equality MUST NOT create such a group by itself.

Section 10 requires human resolution of these groups before positive-reference counting, unless the group remains explicitly unresolved.

## 8.6 Required lineage after deduplication

The internal pooled artifact MUST preserve enough information to reconstruct every pooled item back to C1.

At minimum, preserve:

### Pooled-item identity
- internal pooled item ID;
- record kind;
- deduplication disposition/reason.

### Candidate membership
- retained representative candidate ID;
- all member candidate IDs;
- original lifecycle status;
- supersession lineage.

### Source scope
- `sourceArtifactID`;
- primary evaluation `sourceUnitID`;
- relevant authorized context source units.

### Semantic fields
- operational target/relation ID;
- ontology class/relation;
- action;
- authoritative exact existing IDs where applicable;
- verbatim labels;
- structured attributes;
- exact relation endpoints;
- relation scope.

### Evidence
- all evidence occurrence IDs;
- exact source units;
- coordinates;
- hashes;
- candidate-to-evidence membership.

### Validation lineage
- validation records/findings needed to reproduce the deterministic disposition.

### Duplicate uncertainty
- `POSSIBLE_LOCAL_DUPLICATE` lineage;
- duplicate-review-group membership.

### Normalization provenance
- original proposals/status, if present;
- explicit record that normalization was not used for pooled identity.

### C1 run provenance
- request/run/output/provider/model mappings;
- preserved internally for reproducibility.

## 8.7 Deterministic representative for a human-resolved same-assertion group

When a duplicate-review group receives the final human decision:

```text
same_source_local_assertion
```

and more than one group member has final judgment:

```text
supported_as_proposed
```

the positive pooled reference MUST retain exactly one already existing supported member as the representative.

No merged, rewritten, relabeled, or newly synthesized assertion may be created.

### Fully qualified stable C1 provenance key

For each supported member, construct the deterministic fully qualified key:

```text
c1|<runID>|<requestID>|<outputID>|<primarySourceUnitID>|<recordType>|<candidateID>
```

where:

- `runID` is the immutable governed C1 run identifier;
- `requestID` is the immutable governed C1 request identifier;
- `outputID` is the immutable governed C1 output identifier;
- `primarySourceUnitID` is the exact governed primary source-unit identifier associated with the candidate's C1 request;
- `recordType` is exactly `candidate_node` or `candidate_edge`;
- `candidateID` is the original immutable candidate identifier.

The separator is one literal ASCII vertical bar (`|`), with no added whitespace.

The representative is the supported member with the lexicographically smallest fully qualified stable C1 provenance key.

If two keys are identical, the condition is a provenance-integrity error because the key is required to uniquely qualify the candidate. The process MUST fail closed rather than use input order or another semantic tie-break.

If any required key component is absent, representative materialization MUST fail closed until the governed provenance record is complete. Missing provenance MUST NOT authorize a different representative rule.

All non-representative supported members, evidence occurrences, human judgments, and duplicate-group lineage remain preserved.

---

# 5D — System-Provenance Blinding

## 9. Blinding principle

Human pooled adjudication MUST operate on a deterministic **adjudicator-facing blinded projection** derived from a complete internal pooled artifact.

The internal artifact retains full reproducibility.

The blinded projection exposes only source-grounded semantic content and context required for human judgment.

A whitelist projection SHOULD be used rather than ad hoc field redaction.

## 9.1 Information hidden from pooled adjudicators

The adjudicator-facing projection MUST NOT reveal:

- contributor/system identity beyond the fact that the task is candidate review;
- provider;
- model name/version;
- generation parameters;
- prompt ID/version/hash;
- request ID/hash;
- raw output ID/hash;
- run ID;
- original candidate IDs;
- validation-result IDs/hashes;
- `candidateValidationStatus`;
- `validated`;
- `needs_review`;
- `superseded`;
- `rejected`;
- `deferred`;
- `POSSIBLE_LOCAL_DUPLICATE` as a validator code;
- validator rationales/findings;
- `supersededByRecordID`;
- retry/attempt information;
- token usage/cost;
- production acceptance disposition;
- membership in `usable_pipeline_output`;
- production accepted-semantic projection membership;
- confidence-like metadata;
- normalization mechanism/status when it would reveal system handling.

## 9.2 Information visible to pooled adjudicators

The blinded projection MAY expose, when necessary to judge the assertion:

- opaque `judgmentItemID`;
- node vs relation;
- operational semantic target in human-readable form;
- ontology class/relation needed to understand the assertion;
- verbatim candidate label/assertion;
- material structured attributes;
- relation endpoints;
- evidence text;
- all evidence occurrences;
- source publication identity;
- primary source unit;
- authorized context source units;
- section metadata;
- canonical coordinates;
- bounded canonical context;
- exact deterministic Phase B endpoint/context needed to interpret an endpoint.

Source provenance remains visible.

System provenance remains hidden.

## 9.3 Opaque IDs

Adjudicator-facing item identifiers MUST NOT encode:

- model;
- run;
- request;
- lifecycle status;
- production disposition;
- candidate ID;
- validator finding.

Internal mapping from each opaque judgment ID to complete lineage MUST remain deterministic and preserved.

## 9.4 Duplicate-review groups under blinding

A `POSSIBLE_LOCAL_DUPLICATE` cluster may be exposed as a neutral opaque duplicate-review group.

The interface/projection may state only that:

> the grouped candidate assertions require a same-source duplicate decision before final reference counting.

It MUST NOT expose:

- `POSSIBLE_LOCAL_DUPLICATE`;
- `needs_review`;
- the automatic validator rationale;
- a preferred representative;
- a system confidence.

## 9.5 Item ordering

Judgment items MUST NOT be ordered by:

- validation status;
- production disposition;
- confidence;
- model/provider output status;
- retry status.

A deterministic neutral order may be used.

No fake contributor identities or fabricated provenance may be introduced.

---

# 5E — Non-Generative Human Pooled Adjudication

## 10. Core principle

> **Pooled adjudication is evaluation-only and non-generative. Humans judge the C1 assertion as proposed; they do not repair, split, rewrite, reclassify, regenerate, normalize authoritatively, relink, or add assertions to make the pool more correct or complete.**

A candidate that points toward a plausible underlying fact but is materially incorrect as proposed is judged:

```text
not_supported_as_proposed
```

It is not converted into a corrected assertion.

Completeness is assessed separately in Section 11.

## 10.1 Human-review architecture

Pooled adjudication uses:

1. **one primary expert adjudicator** for all pooled judgment items across all six primary evaluation units; and
2. **one independent second reviewer** for every pooled judgment item belonging to the prospectively selected two-primary-unit subset determined exactly by Section 6.6.

The exact two `primarySourceUnitID` values and their selector digests/ranking MUST be materialized during freeze-time validation and incorporated into the Step 5 freeze artifacts before final researcher approval.

The two reviewers MUST work independently on the bounded second-review subset before reconciliation.

The second-review subset is a quality-control/reproducibility component.

It MUST NOT be represented as a probability sample of all pooled judgments or as a replacement for the already existing Human Core N=2 reliability result.

## 10.2 Ordinary pooled-item judgment categories

Every ordinary pooled judgment item receives exactly one initial human judgment:

```text
supported_as_proposed
not_supported_as_proposed
insufficient_evidence_to_decide
```

### `supported_as_proposed`

All material components of the proposed assertion are supported by the authorized source evidence/context.

### `not_supported_as_proposed`

At least one material component of the assertion, as proposed, is unsupported or incorrect.

For nodes, material components include, as applicable:

- target/class;
- verbatim assertion/label;
- source-local identity action;
- structured attributes.

For relations, material components include, as applicable:

- relation type;
- direction;
- source endpoint;
- target endpoint;
- relation scope.

No partial repair converts a non-supported assertion into a supported assertion.

### `insufficient_evidence_to_decide`

This category is reserved exclusively for a case where the authorized source/evidence context genuinely does not permit a responsible support-versus-non-support decision.

It MUST NOT be used merely because two humans disagree.

## 10.3 Second-review reconciliation

Within the predeclared two-unit second-review subset:

1. primary and second reviewer first judge independently;
2. disagreements may then undergo bounded human reconciliation;
3. reconciliation may choose only among the categories and duplicate decisions authorized by this authority;
4. reconciliation MUST NOT edit the underlying C1 assertion.

If the authorized evidence is genuinely insufficient:

```text
insufficient_evidence_to_decide
```

may be the final status.

If evidence is sufficient to make the task adjudicable but the reviewers remain unable to resolve their disagreement after the permitted reconciliation:

```text
adjudication_unresolved
```

MUST be preserved as a distinct final status.

`adjudication_unresolved`:

- is not equivalent to insufficient evidence;
- is not a positive assertion;
- remains outside the positive pooled reference.

No third-round semantic repair is authorized.

## 10.4 Duplicate-review decisions

Each duplicate-review group receives exactly one of:

```text
same_source_local_assertion
distinct_assertions
insufficient_evidence_to_resolve_duplicate_status
```

### `same_source_local_assertion`

The grouped candidates represent one source-local assertion.

The group may contribute at most one assertion to the positive pooled reference.

If exactly one member has final:

```text
supported_as_proposed
```

that member is retained.

If more than one member has final:

```text
supported_as_proposed
```

the representative MUST be selected exactly under Section 8.7.

No new merged/rephrased assertion is authored.

All relevant member/evidence lineage remains preserved.

### `distinct_assertions`

The candidates represent distinct source-local assertions.

Each independently `supported_as_proposed` member may contribute separately.

### `insufficient_evidence_to_resolve_duplicate_status`

The authorized context does not permit a defensible same-versus-distinct decision.

The group is preserved as duplicate-unresolved.

Its members MUST NOT be counted as multiple independent positive-reference assertions because doing so could create source-local double counting.

This is separate from cross-paper alignment, which remains out of scope.

## 10.5 Evidence/context visible during adjudication

The pooled adjudicator may inspect:

- the blinded proposed assertion;
- all cited evidence occurrences;
- the complete selected primary source unit;
- all `contextSourceUnitIDs` legitimately included in the corresponding frozen C1 request/evaluation envelope;
- deterministic Phase B context/endpoints legitimately supplied to that request;
- the human-readable target semantics necessary to interpret the proposed assertion.

The adjudicator MUST NOT use:

- unrestricted search across the complete paper beyond the authorized frozen request/evaluation envelope;
- another publication;
- web search;
- external literature;
- Human Core annotations;
- C1 validator status;
- Production Acceptance disposition;
- hidden system provenance.

Pooled adjudication is candidate judgment, not exhaustive search.

## 10.6 Positive pooled-reference assembly

An ordinary item enters the positive pooled reference only if its final judgment is:

```text
supported_as_proposed
```

The following do not enter:

```text
not_supported_as_proposed
insufficient_evidence_to_decide
adjudication_unresolved
```

Duplicate-group assembly then applies Section 10.4 and the representative rule in Section 8.7.

Therefore:

```text
positive pooled reference
    ⊆ human-supported assertions originally proposed by C1
```

No human-authored assertion may enter the positive pooled reference unless that assertion existed as an eligible C1 candidate.

## 10.7 Incidental omitted-assertion observations

If a pooled adjudicator incidentally notices a potentially relevant assertion that C1 did not propose:

1. it MUST NOT be added to the pooled reference;
2. it MUST NOT alter another candidate;
3. it MUST NOT trigger a new C1 candidate;
4. it MUST NOT trigger C1 resampling.

The ordinary adjudication record may contain only a neutral:

```text
incidentalObservationFlag
```

when preservation is necessary.

Any detailed incidental note MUST be stored separately in a sealed incidental-observation log.

Before completion/freeze of the Section 11 model-blind audit, detailed incidental observations MUST NOT be used to:

- select audit units;
- select audit targets;
- prioritize source locations;
- assign auditors;
- widen audit context;
- inform the audit expert.

## 10.8 Exposure constraint

A person with prior exposure to pooled C1 judgment items for a particular primary evaluation unit MUST NOT subsequently perform the Section 11 model-blind exhaustive-search audit for that same unit.

This is a cognitive-exposure restriction, not merely a user-interface restriction.

A role/exposure ledger MUST preserve this eligibility state by person/pseudonymous role and primary evaluation unit.

---

# 5F — Six-Unit Model-Blind Completeness Audit

## 11. Purpose

The completeness audit provides independent bounded evidence about:

- pool saturation; and
- missed-reference risk

within the exact six pooled evaluation scopes.

It does not convert the pooled reference into exhaustive gold.

It does not estimate universal completeness.

## 11.1 Audit sample

The completeness audit MUST cover:

```text
6 / 6
```

of the prospectively selected pooled primary evaluation units.

No secondary audit subsample is used.

This supports a direct descriptive statement about observed pool saturation across the entire complementary pooled N=6 sample.

It does not support statistical generalization to:

- all 210 eligible units;
- all Publication units;
- all 11 publications;
- all scientific semantic conditions.

## 11.2 Auditor allocation

The exhaustive-search audit MUST be performed by:

> one independent audit expert.

The audit expert MUST NOT previously have seen, for any audited unit:

- C1 candidates;
- pooled judgment items;
- pooled adjudication outcomes;
- duplicate-review groups;
- validator findings/status;
- Production Acceptance disposition;
- detailed incidental-observation logs.

The audit expert MUST be distinct from the pooled adjudicators for the six audited units.

The exposure ledger MUST demonstrate eligibility before audit execution.

## 11.3 Required temporal independence

The following order is mandatory:

```text
Step 5 FROZEN/CLOSED
    ↓
execute and freeze C1 production outputs
    ↓
model-blind exhaustive audit
    ↓
freeze audit artifact
    ↓
pooled adjudication
    ↓
freeze pooled reference
    ↓
audit ↔ pooled-reference comparison
```

This ensures:

- C1 cannot adapt to audit results; and
- the audit expert cannot adapt to C1 outputs.

## 11.4 Exhaustive-search task

For each of the six primary evaluation units, the audit expert MUST:

> identify all source-supported positive node and relation assertions belonging to the same routed `extract_and_evaluate` targets under the exact frozen C1 primary-request/evaluation envelope.

The audit is exhaustive only within that declared bounded scope.

The audit expert MUST NOT search for:

- `extract_and_monitor` assertions;
- unrouted targets;
- out-of-scope targets;
- new ontology classes;
- new relation types;
- assertions outside the C1 evaluation opportunity.

## 11.5 Audit source/context authority

For each audited primary evaluation unit, the audit expert may consult only the source/context opportunity frozen for C1, including:

- the selected `primarySourceUnitID`;
- authorized `contextSourceUnitIDs` included in the frozen C1 evaluation envelope;
- the corresponding canonical text;
- deterministic Phase B endpoint/context information legitimately available to C1;
- frozen human-readable definitions of routed `extract_and_evaluate` targets.

The audit expert MUST NOT use:

- unrestricted full-paper search beyond the frozen evaluation envelope;
- other publications;
- external web search;
- external literature;
- C1 outputs;
- pooled judgments;
- Human Core annotations;
- incidental-observation logs.

The bounded audit therefore measures missed-reference behavior relative to the information opportunity that was available to C1.

## 11.6 Independent audit-reference construction

The audit expert authors audit records independently of C1.

Each supported audit assertion MUST preserve, as applicable:

```text
auditAssertionID
primarySourceUnitID
sourceArtifactID
recordKind
operationalTargetID
ontology class or relation
source-local identity
relation endpoints
exact evidence occurrences
```

Evidence MUST satisfy the existing canonical source/evidence authority.

Within the audit artifact:

- repeated source-local mentions of the same assertion should be reconciled source-locally;
- no cross-paper merge is permitted;
- no C1 candidate may seed or constrain audit discovery.

For every routed `extract_and_evaluate` target in every audited primary unit, the audit artifact MUST record completion of exhaustive review, including target-unit combinations with zero supported assertions.

## 11.7 Audit dispositions

Audit findings use:

```text
audit_supported_assertion
audit_unresolved
```

### `audit_supported_assertion`

The audit expert identifies a positive source-supported assertion within the bounded audit authority.

### `audit_unresolved`

The audit expert cannot defensibly resolve the assertion under the authorized source/evidence context.

`audit_unresolved` findings:

- remain preserved;
- are reported separately;
- MUST NOT enter the saturation denominator.

Because only one audit expert performs this task, the authority MUST NOT describe `audit_supported_assertion` as human truth, confirmed truth, or exhaustive gold.

## 11.8 Audit freeze

The complete audit artifact MUST be:

- frozen;
- hashed;
- immutable for the primary comparison

before the audit expert, implementation, or analyst may inspect the positive pooled reference for comparison purposes.

## 11.9 Step 5F comparison scope

The audit-to-pool matcher has its own explicit Step 5F scope:

> the exact frozen C1 primary-request/evaluation envelope for each of the six primary evaluation units, including its authorized context source units.

Step 5F prospectively adopts relevant matching predicates and one-to-one assignment principles from the frozen Publication Human Core Amended Matching Contract.

This adoption does **not** extend the formal scope of that Human Core contract.

No new semantic matching heuristic is introduced.

## 11.10 Node matching

An audit-supported node may match a positive pooled node only when all required conditions hold:

- same bounded C1 evaluation envelope;
- same source artifact;
- same operational target ID;
- same ontology class;
- compatible source-local occurrence/contextual identity;
- qualifying canonical supporting-evidence correspondence;
- one-to-one assignment.

Label similarity alone does not produce a match.

Where evidence-span overlap is required, the adopted common span predicate is:

```text
same sourceArtifactID
same canonical sourceUnitID
span_F1 >= 0.80
span_precision >= 0.70
span_recall >= 0.70
```

with zero-based, half-open canonical character spans.

## 11.11 Relation matching

An audit-supported relation may match a positive pooled relation only when all required conditions hold:

- same bounded C1 evaluation envelope;
- same operational relation target;
- same ontology relation;
- same operational direction;
- audit source endpoint corresponds to pooled source endpoint;
- audit target endpoint corresponds to pooled target endpoint;
- qualifying relation-specific evidence;
- one-to-one assignment.

Source-local endpoints are resolved through the corresponding node matching.

Frozen deterministic endpoints require exact deterministic identity.

A wrong relation, direction, or endpoint does not constitute a qualifying match.

## 11.12 One-to-one assignment

Within each bounded comparison scope and operational target, assignment MUST:

1. maximize eligible match cardinality;
2. prefer exact evidence correspondence;
3. prefer greater qualifying evidence overlap;
4. prefer smaller evidence-boundary difference;
5. resolve remaining ties using deterministic fully qualified stable provenance keys.

One pooled assertion may match at most one audit-supported assertion.

One audit-supported assertion may match at most one pooled assertion.

## 11.13 Completeness/saturation statistics

Nodes and relations MUST be reported separately.

Let:

```text
A_N = number of audit-supported node assertions
M_N = number of those audit-supported nodes matched one-to-one to the positive pooled reference
```

Then:

```text
Observed Node Pool Saturation = M_N / A_N
```

and:

```text
Observed Node Missed-Reference Proportion = (A_N - M_N) / A_N
```

Let:

```text
A_R = number of audit-supported relation assertions
M_R = number of those audit-supported relations matched one-to-one to the positive pooled reference
```

Then:

```text
Observed Relation Pool Saturation = M_R / A_R
```

and:

```text
Observed Relation Missed-Reference Proportion = (A_R - M_R) / A_R
```

If an audit-supported denominator is zero, the corresponding proportion is:

```text
undefined
```

not zero and not one.

Always report raw counts with each proportion.

At minimum report:

- audit-supported count;
- matched count;
- unmatched count;
- audit-unresolved count;
- observed saturation;
- observed missed-reference proportion.

Per-unit or per-target breakdowns may be descriptive if reported with raw support.

No node/relation composite completeness score is authorized.

No confidence interval or probability-based population inference is authorized by this six-unit coverage-oriented design.

## 11.14 Interpretation

Permitted interpretation:

> observed pool saturation relative to the independent bounded audit across the six pooled evaluation units.

Forbidden interpretation:

> true completeness of the pooled reference.

Also forbidden:

- exhaustive gold;
- population-level recall estimate;
- statistically representative completeness estimate;
- universal Publication completeness;
- completeness of the full KG.

## 11.15 Audit-supported unmatched assertions

An `audit_supported_assertion` with no qualifying pooled match is recorded as:

```text
audit_supported_unmatched_assertion
```

Such an assertion is evidence of an observed pooled-reference omission within the bounded audit.

It MUST NOT:

- be inserted into the positive pooled reference;
- create a retrospective C1 candidate;
- change C1;
- alter Step 7 Human Core scoring;
- alter Production Acceptance;
- alter the frozen production accepted-semantic projection;
- alter the production KG;
- trigger semantic resampling.

It remains an audit-only finding.

## 11.16 Incidental-observation firewall

Before audit freeze, the audit expert MUST NOT receive:

- `incidentalObservationFlag` prioritization;
- detailed incidental-observation logs;
- source locations derived from incidental observations;
- target hints derived from incidental observations;
- candidate-derived duplicate groups.

Incidental observations MUST NOT influence:

- audit sample selection;
- audit target selection;
- audit ordering;
- audit context;
- auditor allocation.

---

# 5G — Bounded SciERC External IE Anchor

## 12. Purpose

SciERC serves only as a bounded external scientific-information-extraction anchor.

Its role is to test whether the underlying structured scientific entity/relation extraction mechanism shows transfer to an independently defined scientific IE schema.

SciERC does not replace any CIROH human reference.

## 12.1 Benchmark-native schema

SciERC MUST be evaluated using its native semantic schema.

No mapping from SciERC labels into the CIROH ontology is authorized.

The adapter MUST bind to the exact label strings in the selected official SciERC dataset release.

The benchmark contains six scientific entity categories conceptually corresponding to:

```text
Task
Method
Metric
Material
Other-ScientificTerm
Generic
```

and seven relation categories conceptually corresponding to:

```text
Compare
Part-of
Conjunction
Evaluate-for
Feature-of
Used-for
Hyponym-Of
```

The exact serialization strings used by the dataset release are authoritative.

`Compare` and `Conjunction` are symmetric under the benchmark semantics.

The other benchmark relations retain their benchmark-defined directionality.

SciERC coreference annotations are out of scope.

## 12.2 Portable extractor components

The SciERC anchor MUST preserve the C1 extraction mechanism where the setting is schema-independent.

Specifically, SciERC MUST use:

- the same underlying base LLM used for C1;
- the same inference/reasoning settings used for C1 whenever those settings are schema-independent;
- the same structured entity/relation extraction pattern where schema-independent;
- the same conservative source-grounding behavior where schema-independent;
- the same no-semantic-resampling rule;
- deterministic output parsing/binding/scoring appropriate to the benchmark.

The adapter MAY change only what is inherently necessary to express and score the SciERC-native task, including:

- benchmark-native entity vocabulary;
- benchmark-native relation vocabulary;
- benchmark-native structured output schema;
- official token/span representation and deterministic token↔character binding;
- benchmark relation directionality/symmetry handling;
- benchmark-native serialization required for evaluation.

The adapter MUST NOT change the base model or schema-independent inference/reasoning settings merely to improve SciERC performance.

## 12.3 Explicitly excluded C1 components

SciERC MUST NOT test or import:

- CIROH ontology classes as benchmark labels;
- CIROH relation targets as benchmark labels;
- Publication `extract_and_evaluate` routing;
- Publication `extract_and_monitor` routing;
- Phase B Publication deterministic entities as SciERC gold;
- deferred-record resolution;
- Production Acceptance;
- pooled candidate adjudication;
- completeness audit;
- cross-paper identity resolution;
- cross-source alignment;
- D-26 generic mention derivation;
- SciERC coreference prediction.

## 12.4 Thin benchmark adapter

SciERC support MUST be implemented as a thin benchmark-native adapter rather than a second extraction subsystem.

The input authority is the official benchmark representation and tokenization.

The adapter MUST maintain a deterministic reversible mapping between:

- benchmark token spans; and
- any character-span representation used for prompting/binding.

The minimal entity output requires:

```text
entityID
SciERC entity type
mention text
exact bound mention span
```

The minimal relation output requires:

```text
relationID
SciERC relation type
source entity reference
target entity reference
```

Relation endpoints MUST refer to entities extracted within the same benchmark document.

The adapter MUST NOT add:

- CIROH ontology IDs;
- Publication operational target IDs;
- global canonical IDs;
- semantic normalization requirements;
- Publication candidate lifecycle machinery not needed for benchmark validity.

## 12.5 Prompt adaptation

Permitted prompt adaptation is limited to what is necessary to express the benchmark-native task:

1. replace CIROH target definitions with official SciERC label definitions;
2. replace the output vocabulary/schema with the six entity and seven relation categories;
3. specify exact mention/span requirements;
4. specify benchmark relation directionality/symmetry;
5. retain the general conservative extraction and source-grounding behavior.

The following are prohibited:

- test-set examples in the prompt;
- retrieval of gold benchmark records during inference;
- performance-driven few-shot selection;
- train-set fitting;
- fine-tuning;
- repeated prompt optimization against test performance;
- benchmark-specific semantic repair rules discovered from prediction errors.

## 12.6 Mechanical validation before test execution

A bounded mechanical smoke test MAY use non-test benchmark material only to verify:

- parsing;
- serialization;
- legal entity labels;
- legal relation labels;
- exact span binding;
- endpoint resolution;
- symmetric/directional relation encoding;
- deterministic output conversion.

Mechanical validation MUST NOT become performance optimization.

Once the adapter and configuration are operationally valid, they MUST be frozen before official test execution.

## 12.7 Evaluation split and execution

The complete official SciERC test split MUST be used.

No test subsampling is authorized.

The evaluation is:

- zero-shot/external-transfer in the sense that no SciERC training/fine-tuning is performed;
- a single prospectively configured benchmark execution.

A processable valid official test run ends performance-oriented execution.

Test-set reruns solely to improve Precision/Recall/F1 are prohibited.

Mechanical execution failures may be corrected only under documented non-semantic repair that does not use observed test performance to change extraction semantics.

## 12.8 Entity metric

Primary entity evaluation is:

> exact benchmark mention span + exact SciERC entity type.

Report micro:

```text
Precision
Recall
F1
```

with:

```text
TP
FP
FN
gold support
prediction support
```

## 12.9 Relation metric

Primary relation evaluation follows the SciERC-style relation criterion:

> correct relation type plus exact head offsets for both entity-mention arguments.

The primary relation metric does not additionally require the predicted endpoint entity types to be correct unless the official evaluation implementation being frozen explicitly does so.

Report micro:

```text
Precision
Recall
F1
```

with:

```text
TP
FP
FN
gold support
prediction support
```

A stricter endpoint-type-aware relation result MAY be reported only as a clearly labeled secondary diagnostic if it is mechanically trivial to compute.

No combined entity/relation composite score is authorized.

## 12.10 Permitted claims

SciERC results may support claims of the following form:

- the frozen base extraction mechanism was evaluated on an independently annotated scientific IE benchmark;
- the structured extraction mechanism exhibits measurable external transfer to a benchmark-native scientific entity/relation schema;
- external performance provides evidence that the extraction mechanism is not evaluated solely against the CIROH Human Core task.

All claims MUST be bounded to:

- SciERC;
- its scientific-domain corpus;
- its native label schema;
- the exact frozen benchmark configuration used.

## 12.11 Prohibited claims

SciERC MUST NOT be used to claim that:

- the CIROH ontology generalizes to SciERC;
- SciERC validates the CIROH ontology;
- SciERC validates the final multigranular KG;
- SciERC validates Publication reference completeness;
- SciERC replaces Human Core;
- SciERC validates Production Acceptance;
- operational-hydrology extraction generalizes to all scientific domains;
- cross-source provenance/alignment generalizes;
- the full KG-construction pipeline generalizes;
- coreference capability has been externally validated;
- the system is state of the art merely because its result exceeds a reported historical number.

Published SciERC systems may be cited as contextual reference points only when configurations and evaluation conditions are described accurately.

## 12.12 SciERC stop rule

SciERC MUST remain a bounded external anchor.

Adaptation MUST stop, be reduced in scope, or be abandoned if supporting SciERC requires any of the following:

- modifying the CIROH ontology;
- creating and validating a CIROH↔SciERC semantic ontology mapping;
- adding new CIROH target families;
- implementing coreference extraction;
- training or fine-tuning a model;
- creating a new model architecture;
- adding retrieval;
- adding multi-agent or LLM-as-judge systems;
- performance-driven prompt-search loops;
- benchmark-specific semantic repair heuristics;
- repeated official test runs to optimize scores;
- manual adjudication of benchmark predictions;
- creation of a new SciERC gold/reference set;
- changing C1 because of SciERC outcomes;
- substantial refactoring of the Production extractor solely to support the benchmark.

Operational rule:

> If SciERC cannot be supported by a thin benchmark-native adapter over the frozen extraction runtime, exact-span binding, and deterministic evaluator, the external anchor is reduced or abandoned rather than expanded into a separate benchmark project.

---

# 13. Cross-Cutting Prohibitions

Under Step 5, no component may:

- turn LLM agreement into gold;
- use pooled adjudication to repair C1;
- use audit findings to repair C1;
- use SciERC to tune C1 after production freeze;
- modify Step 7 predictions;
- alter Production Acceptance retrospectively;
- add human-authored pooled assertions;
- silently merge candidates across papers;
- canonicalize source-local entities;
- use normalized labels as identity;
- convert uncertainty into forced semantic closure;
- describe candidate-conditioned pooled reference coverage as exhaustive truth.

---

# 14. Non-Claims

Step 5 does not establish:

- statistical representativeness of N=6;
- representativeness of Human Core + pooled N=11 publication coverage;
- exhaustive semantic coverage of all Publication source units;
- exhaustive pooled-reference gold;
- true completeness;
- population-level missed-reference probability;
- general correctness of C1 beyond the bounded evaluations;
- global identity correctness;
- final KG correctness;
- generalization to all scientific domains.

---

# 15. Freeze-Time Artifacts and Bindings Required Before Step 5 Can Close

The artifacts in this section MUST be materialized, validated, and bound before final researcher approval and before this authority may change from `DRAFT — NOT FROZEN` to `FROZEN/CLOSED`.

Exact repository subdirectories may follow existing project conventions, but the logical artifacts and their contents are mandatory.

## 15.1 Integrated Step 5 authority

Recommended path:

```text
docs/publication_step5_evaluation_authority_v0.1.md
```

Before freeze, it MUST incorporate the exact binding identifiers, versions, and hashes produced by Sections 15.2–15.7.

## 15.2 Complementary N=6 selection freeze

Must include:

- source sampling-analysis authority and hashes;
- eligible population authority;
- six remaining publication IDs;
- hard constraints;
- routed-target exposure for selected units;
- tie-break calculations;
- exact six selected `primarySourceUnitID` values;
- proof of 19/19 node coverage;
- proof of 16/16 relation coverage;
- proof of 5/5 strata;
- proof of one unit per remaining publication.

Recommended logical artifact:

```text
publication_pool_n6_selection_freeze_v0.1.0.json
```

## 15.3 C1 pooled evaluation-envelope freeze

For each selected primary unit, bind prospectively:

- exact primary source unit;
- authorized context source units;
- routed `extract_and_evaluate` targets;
- frozen source hashes;
- request-envelope identity/hash;
- deterministic endpoint/context authority;
- prompt/provider/model/configuration authority that Step 6 will use.

Recommended logical artifact:

```text
publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.0.json
```

This artifact freezes the future C1 evaluation opportunity. It does not execute C1.

## 15.4 Bounded second-review subset freeze

Must include:

- selector namespace/version;
- canonical hash input for each of the six primary units;
- lowercase SHA-256 digest for each unit;
- complete ascending ranking;
- lexical collision tie-break rule;
- exact selected two `primarySourceUnitID` values.

Recommended logical artifact:

```text
publication_pool_secondary_review_subset_freeze_v0.1.0.json
```

## 15.5 Role/exposure control specification

The Step 5 authority MUST freeze the semantics of a role/exposure ledger capable of representing:

- pseudonymous human role/person;
- primary evaluation unit;
- C1/pool exposure state;
- audit eligibility state.

Recommended future ledger path:

```text
publication_step5_role_exposure_ledger.json
```

The freeze-time artifact defines its schema/eligibility semantics. Human exposure rows are populated during future execution.

## 15.6 SciERC benchmark-source/split binding

Before Step 5 closes, bind the exact official benchmark authority that future SciERC execution will use, including:

- dataset/release identifier;
- exact test split identity;
- source/hash/version information available from the chosen official distribution;
- exact native entity-label serialization;
- exact native relation-label serialization;
- symmetry/directionality authority.

Recommended logical artifact:

```text
scierc_external_anchor_source_freeze_v0.1.0.json
```

This artifact does not execute SciERC.

## 15.7 SciERC adapter/configuration authority

Before Step 5 closes, freeze prospectively:

- base LLM identity, which MUST equal C1's underlying base LLM;
- schema-independent inference/reasoning settings, which MUST equal C1's;
- benchmark-native schema;
- exact token/span binding policy;
- relation endpoint policy;
- relation symmetry/direction policy;
- allowed prompt adaptation boundary;
- mechanical smoke-test boundary;
- single official test-run policy;
- stop rule.

Recommended logical artifact:

```text
scierc_external_anchor_adapter_freeze_v0.1.0.json
```

This artifact does not execute SciERC.

---

# 16. Future Execution Artifacts Governed by the Frozen Step 5 Authority

The artifacts in this section MUST NOT be prerequisites for declaring Step 5 methodology FROZEN/CLOSED.

They are future outputs generated only after the integrated Step 5 authority and all Section 15 freeze-time bindings have been frozen.

## 16.1 C1 execution artifacts — Step 6

Future execution will materialize and freeze:

- production provider/model responses;
- processable-response selection;
- C1 validated candidate records;
- production accepted-semantic projection;
- complete run/request/output provenance.

These artifacts are governed by Step 4 and the frozen Step 5 evaluation envelopes.

## 16.2 Pooled-reference execution artifacts

After C1 is frozen, future execution will materialize:

### Eligible candidate-layer projection
Preserve:

- eligible C1 candidate membership;
- eligibility reason;
- excluded candidate disposition;
- exact lineage.

### Internal deduplicated pooled artifact
Preserve:

- dedup representative map;
- all members;
- evidence bundles;
- duplicate-review groups;
- full system provenance.

### Blinded adjudication package
Contain only the Section 9 whitelist projection.

### Primary pooled judgments

### Independent bounded second-review judgments

### Reconciliation/unresolved record
Preserve:

- initial judgments;
- reconciliation;
- `adjudication_unresolved`;
- duplicate-group resolution.

### Positive pooled reference
Preserve:

- final supported assertions;
- same-assertion representative mapping under Section 8.7;
- excluded/unresolved side records;
- stable hash.

### Sealed incidental-observation log
When nonempty, remain separate from pooled reference and audit input.

## 16.3 Completeness-audit execution artifacts

Future execution will materialize:

### Audit assignment/package
Bind:

- six primary evaluation units;
- frozen C1 evaluation envelopes;
- routed `extract_and_evaluate` targets;
- audit-expert eligibility under the exposure ledger;
- absence of C1/pool/incidental inputs.

### Independent audit artifact
Preserve:

- audit-supported assertions;
- audit-unresolved records;
- target-unit review-completion records;
- exact evidence;
- freeze hash.

### Audit ↔ pooled comparison
Preserve:

- Step 5F matching authority/version;
- comparison scope;
- one-to-one assignments;
- unmatched audit-supported assertions;
- node statistics;
- relation statistics;
- raw counts;
- descriptive per-unit/per-target diagnostics if generated.

## 16.4 SciERC execution artifacts

Future execution will materialize:

### SciERC execution manifest
Bind:

- frozen adapter/config;
- model/runtime;
- official test input hash;
- raw outputs;
- run identity.

### SciERC metrics artifact
Report:

- entity TP/FP/FN/P/R/F1;
- relation TP/FP/FN/P/R/F1;
- optional strict relation diagnostic if authorized;
- no composite score.

---

# 17. Step 5 Freeze Gate

Step 5 MUST remain:

```text
DRAFT — NOT FROZEN
```

until all conditions below are satisfied.

## 17.1 Initial researcher methodological approval

- [ ] Researcher confirms that the DRAFT faithfully represents accepted Sections 5A–5G.
- [ ] No methodological alternative is being reopened.
- [ ] No unresolved methodological contradiction remains.
- [ ] No result-derived rule has been introduced.

This approval authorizes deterministic freeze-time materialization/validation only. It does not freeze Step 5 and does not authorize Step 6 provider execution.

## 17.2 Upstream-authority binding

- [ ] Current frozen ontology authority is bound.
- [ ] Current target authority is bound.
- [ ] Source-unit/request-context authority is bound.
- [ ] Candidate/provider/prompt authorities required for future C1 are bound.
- [ ] V1–V12 validation authority is bound.
- [ ] Human Core amended matching authority is bound without extending its formal scope.
- [ ] Production Acceptance Policy v0.1.0 is bound.
- [ ] Human Core sampling-analysis authority is bound.

## 17.3 N=6 deterministic freeze-time materialization

- [ ] Deterministic N=6 selection is reproduced from the approved model-blind rule.
- [ ] Exact six `primarySourceUnitID` values are materialized.
- [ ] One selected unit comes from each of `18`, `276`, `37`, `46`, `54`, `87`.
- [ ] 19/19 scored node targets are covered.
- [ ] 16/16 scored relation targets are covered.
- [ ] 5/5 sampling strata are covered.
- [ ] All frozen exclusions are honored.
- [ ] Minimax routed-target exposure rule is verified.
- [ ] Total-exposure tie-break is verified.
- [ ] Lexical final tie-break is verified where applicable.

## 17.4 C1 evaluation-envelope freeze-time materialization

- [ ] Exact future C1 primary-request/evaluation envelopes for the six selected units are materialized prospectively.
- [ ] Authorized context units are bound.
- [ ] Routed `extract_and_evaluate` scope is bound.
- [ ] Source/context hashes are bound.
- [ ] Model/prompt/provider/configuration authorities are bound.
- [ ] No screening expectations are injected as semantic hints.
- [ ] No provider/model call has been made as part of freeze-time materialization.

## 17.5 Two-unit second-review freeze-time materialization

- [ ] The Section 6.6 selector namespace/version is recorded exactly.
- [ ] Six canonical hash inputs are materialized.
- [ ] Six SHA-256 digests are materialized.
- [ ] Full ranking is reproducibly materialized.
- [ ] Lexical collision tie-break is implemented.
- [ ] Exact two selected `primarySourceUnitID` values are bound.

## 17.6 Human-role and information-flow controls

- [ ] Role/exposure ledger schema and eligibility semantics are frozen.
- [ ] Auditor-exposure prohibition is enforceable.
- [ ] Incidental-observation isolation is specified operationally.
- [ ] Blinded projection is defined by an explicit field whitelist or equivalently fail-closed projection.
- [ ] `adjudication_unresolved` remains distinct from `insufficient_evidence_to_decide`.

## 17.7 Deterministic pooled-reference controls

Focused deterministic validation MUST demonstrate that:

- [ ] 5B candidate eligibility is reproducible from governed fields/status/code.
- [ ] `POSSIBLE_LOCAL_DUPLICATE` enters the pre-dedup layer.
- [ ] `ATOMICITY_VIOLATION` does not.
- [ ] monitor-only candidates cannot enter the pooled reference.
- [ ] 5C auto-dedup uses only the three enumerated authority classes.
- [ ] label equality alone cannot merge `propose_new`.
- [ ] cross-paper candidates cannot auto-merge.
- [ ] evidence occurrences are preserved after assertion deduplication.
- [ ] stronger-role supersession evidence is not silently promoted.
- [ ] the Section 8.7 fully qualified C1 provenance key is constructible under the governed production provenance contract.
- [ ] the Section 8.7 representative selection is deterministic and fails closed on missing/non-unique provenance.
- [ ] blinded projection excludes all prohibited system-provenance fields.
- [ ] opaque IDs do not encode hidden status.
- [ ] audit statistics reproduce the Section 11 formulas.
- [ ] `audit_unresolved` is excluded from saturation denominators.
- [ ] no Step 5 procedure mutates the frozen Step 4 production projection.

## 17.8 SciERC freeze-time binding

Before Step 5 closes:

- [ ] exact official benchmark release/split authority is bound;
- [ ] native label serialization is bound;
- [ ] adapter is limited to the approved thin-adapter boundary;
- [ ] underlying base LLM is bound and exactly matches C1;
- [ ] schema-independent inference/reasoning settings are bound and exactly match C1;
- [ ] coreference remains excluded;
- [ ] no CIROH↔SciERC ontology mapping is introduced;
- [ ] mechanical smoke testing is separated from performance optimization;
- [ ] official test execution policy is frozen;
- [ ] the stop rule is operationally preserved.

SciERC execution results are **not** required to declare Step 5 methodology frozen.

## 17.9 Incorporation of exact freeze-time bindings

Before final researcher approval:

- [ ] exact N=6 IDs are incorporated into the final authority/freeze record;
- [ ] exact C1 evaluation-envelope identifiers/hashes are incorporated;
- [ ] exact two-unit second-review IDs and selector digests/ranking are incorporated;
- [ ] exact relevant upstream versions/hashes are incorporated;
- [ ] exact SciERC benchmark-source and adapter/configuration bindings are incorporated;
- [ ] all freeze-time artifact hashes are recorded.

## 17.10 Final researcher approval and closure

Only after Sections 17.1–17.9 pass:

- [ ] Researcher reviews the fully bound authority.
- [ ] Researcher explicitly approves the final authority.
- [ ] Authority status changes from `DRAFT — NOT FROZEN` to `FROZEN`.
- [ ] A versioned Step 5 freeze record is materialized.
- [ ] Step 5 is declared `FROZEN/CLOSED`.
- [ ] Only then may Step 6 production execution begin.

C1 outputs, pooled judgments, audit results, and SciERC test results are future execution artifacts and MUST NOT be prerequisites for Step 5 closure.

---

# 18. Freeze and Change-Control Rule

Once frozen, this authority MUST NOT be changed in response to:

- C1 candidate volume;
- observed pooled acceptance rate;
- duplicate frequency;
- human disagreement;
- completeness-audit saturation;
- unmatched audit-supported assertions;
- SciERC performance.

Any later methodological change requires:

```text
documented reproducible blocker
    →
new version
    →
prospective rationale independent of the observed result being optimized
    →
preservation of this frozen authority
```

Mechanical implementation fixes that do not change semantic eligibility, human judgment meaning, comparison scope, statistics, or permitted claims may be handled under normal implementation change control.

---

# 19. Draft Acceptance Statement

This document is currently:

> **DRAFT — NOT FROZEN**

The intended closure sequence is:

```text
researcher approval of this DRAFT
    →
deterministic freeze-time materialization/validation
    →
incorporation of exact IDs, bindings, versions, and hashes
    →
final researcher approval
    →
Step 5 authority FROZEN/CLOSED
    →
Step 6 execution
```

Freezing this authority will not itself:

- execute C1;
- create pooled human judgments;
- run the completeness audit;
- compare audit findings to the pooled reference; or
- run SciERC.

Those are future executions governed by the frozen Step 5 authority.
