# Publication Human Core Amended Matching Contract v0.1

**Status:** FINAL AND FROZEN
**Date frozen:** 2026-09-21
**Scope:** Study 2 Publication Human Core reliability and extractor evaluation
**Contract version:** 0.1.0

## 1. Purpose and boundary

This contract prospectively defines correspondence, one-to-one assignment, evidence
comparison, reliability reporting, and Human Core Precision/Recall/F1 scoring for the
amended Study 2 Publication evaluation architecture.

It governs two different comparison modes:

1. Human-to-Human reliability on the frozen N=2 independent reliability subset.
2. Extractor-to-Human-Core scoring on the frozen N=5 Human Core.

The two modes share span measures and deterministic assignment machinery but do not share
the same eligibility conditions. Human-to-Human comparison is symmetric and measures
reproducibility. Extractor-to-Human-Core comparison is asymmetric and measures extractor
correctness against the bounded human reference.

This contract does not alter either human annotation, adjudicate disagreements, change the
ontology or target inventory, define production acceptance, define pooled-reference or
completeness-audit procedures, define the SciERC contract, or alter historical Publication
Pilot 1 evaluation results.

The historical Publication Pilot 1 matching contract remains frozen for its historical
scope. Where that contract differs from this document, this document controls only the
amended Human Core reliability and N=5 extractor evaluation.

## 2. Frozen authorities and inputs

The controlling ontology is CIROH ontology 0.1.5. The validated OWL SHA-256 is:

    ce5f6d3d8ac926dc8ff872c9a36066758a86068b6681417bf7edc6aaeccf1e71

The Human Core annotation guide is Publication Human Core Expert Annotation Guide v1.1,
bound prospectively with SHA-256:

    c937a86bfe2a920dac0ad0b7c9f16cc863f2c2ece68cd65e5b3bfa7aef2ba56e

The target universe is the v0.1.5 Publication target inventory:

    src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml

At the freeze commit immediately preceding this contract, its Git blob SHA is:

    8a4921d687e93d4e8db879ae2e9c611f07e04bd1

The frozen N=2 source units are exactly:

- pub:34:sec:0015:unit:0001
- pub:79:sec:0004:unit:0001

Annotator A is represented for N=2 by the deterministic, read-only composite view:

    data/curation/papers/m2/human_core_gold/
    publication_human_core_annotator_a_n2_composite_view_v0.1.5.json

That view was frozen at commit 66f3963610520d6784bc965d2028b37cb957f901 and preserves
the immutable primaryV014 and supplementalV015 partitions without semantic merge,
normalization, repair, relabeling, inference, or adjudication.

Annotator B is the independent second human reliability annotator. Its immutable raw export
is bound by:

    data/curation/papers/m2/human_core_gold/
    publication_human_core_reliability_annotation_preservation_v0.1.5.json

The bound raw-export SHA-256 is:

    b7af00881cf97bffce4630352c6ceb0b32a5e46ef0caed67f15853219bae6e97

The matcher must fail closed if a bound authority, exact N=2 membership, or required
provenance field does not match its frozen authority.

## 3. Non-contamination rule

This contract is frozen before A-versus-B disagreement inspection.

No observed A-versus-B agreement, disagreement, class confusion, endpoint disagreement, or
evidence-boundary result may be used to alter the rules below. No later adjudication result
may retroactively change pre-adjudication reliability.

## 4. Common character-span measures

All character offsets are zero-based, half-open Unicode code-point offsets within one
canonical source unit.

For predicted/comparator span P and reference/other span G:

    intersection = max(0, min(P.end, G.end) - max(P.start, G.start))
    span_precision = intersection / length(P)
    span_recall = intersection / length(G)
    span_F1 = 2 * span_precision * span_recall /
              (span_precision + span_recall)

A qualifying boundary-tolerant overlap requires all of:

- same sourceArtifactID;
- same canonical sourceUnitID;
- span_F1 at least 0.80;
- span_precision at least 0.70; and
- span_recall at least 0.70.

An exact span match additionally requires equal start and end unit offsets and equal literal
text. Exact-boundary agreement is always reported separately from boundary-tolerant
agreement.

These historical thresholds are retained prospectively. They must not be tuned after
inspection of A-versus-B results.

## 5. Fully qualified stable provenance keys

Bare local candidate IDs are not assumed globally unique.

Every human record used in assignment must receive a deterministic fully qualified stable
provenance key:

    human | annotator-role | partition | annotationSessionID |
    sourceUnitID | record-kind | candidateID

For Annotator A, partition is primaryV014 or supplementalV015 as preserved by the composite
view. For Annotator B, partition is reliabilityV015. record-kind is node or relation.

If a future extractor record requires a deterministic tie break, use an equivalently
qualified key containing immutable run/request provenance, sourceUnitID, record kind, and
candidate ID. Input order is never a tie breaker.

If the required provenance fields are unavailable, matching fails closed rather than
falling back to a bare local ID or array position.

## 6. Human-to-Human N=2 node detection pairing

Annotator A and Annotator B are symmetric peers. Neither is gold for reliability.

### 6.1 Eligibility

A node pair is eligible for Human-to-Human detection pairing only when:

- both records belong to the same frozen primary source unit;
- their primary mentionSpan values satisfy the qualifying boundary-tolerant overlap rule;
  and
- their occurrence/contextual identities are compatible.

Class, ontology class ID, operational target ID, and label similarity are ignored during
detection eligibility.

The Human Core guide distinguishes identifying mentions from supporting evidence.
Accordingly, node detection pairing uses mentionSpan, not supporting evidence, as its
primary occurrence anchor.

### 6.2 Compatible occurrence/contextual identity

Occurrence/contextual identity is a deterministic conflict guard, not a semantic
normalization step. A pair is incompatible when both records encode a frozen
source-local identity discriminator and those values conflict.

Applicable discriminators include, when present and authoritative for the record:

- exact existing endpoint identity;
- identity scope;
- artifact scope;
- contextual owner, model, method, experiment, condition, value, or role fields explicitly
  represented by the annotation schema; and
- other frozen source-local identity fields explicitly designated by an upstream
  annotation authority.

Class and operational target are not identity discriminators for Human-to-Human detection
pairing. Missing discriminator values do not authorize invented normalization or
name-similarity resolution.

For composite human mentions, legacy mentionSpan remains the primary first-fragment anchor
as defined by the guide. Additional mentionSpans may be reported diagnostically but do not
replace the required qualifying primary mentionSpan overlap.

### 6.3 One-to-one assignment

Within each source unit, eligible node pairs are assigned one-to-one.

Optimization order is:

1. maximum cardinality;
2. exact primary mentionSpan equality;
3. greater primary mentionSpan F1;
4. smaller total primary mention boundary difference;
5. lexicographically smaller sequence of fully qualified stable provenance-key pairs.

Neither class nor operational target may influence the pairing.

## 7. Human-to-Human N=2 relation detection pairing

Relation detection is separated from relation characterization. A wrong relation type,
wrong direction, or wrong selected endpoint must remain observable as characterization
disagreement rather than automatically becoming a detection failure.

### 7.1 Eligibility and atomic relational proposition

A relation pair is eligible only within the same frozen primary source unit and only when
its relation-specific evidence has qualifying boundary-tolerant overlap.

Relation type, operational relation target, direction, and selected endpoints are ignored
as hard eligibility conditions.

For this contract, "same atomic relational proposition" is operationalized
deterministically through evidence-compatible one-to-one proposition assignment:

1. Build a bipartite graph whose candidate edges are relation-record pairs with qualifying
   relation-specific evidence overlap in the same source unit.
2. Form ambiguity components from connected candidate edges. Evidence overlap admits a
   relation pair to a proposition-assignment component; it does not by itself declare the
   records matched.
3. Perform maximum-cardinality one-to-one assignment inside each component using the
   preference order in Section 7.2.
4. Only assigned pairs are treated as detection-paired atomic relational propositions.

This preserves the historical rule that relation-specific evidence overlap alone cannot
declare two distinct edge propositions matched merely because they share a sentence or
evidence span.

### 7.2 Ambiguous relation-assignment preference

After maximum cardinality, ambiguous relation assignment uses this ordered preference:

1. greater unordered endpoint-occurrence correspondence;
2. exact relation-specific evidence-set equality;
3. greater relation-specific evidence-set F1;
4. smaller total evidence-boundary difference;
5. lexicographically smaller sequence of fully qualified stable provenance-key pairs.

Unordered endpoint-occurrence correspondence is an assignment preference only. It is not
an eligibility gate and does not establish endpoint correctness. Endpoint selection and
direction are evaluated after relation detection pairing.

No relation type, operational relation target, or direction may be used to improve
assignment.

## 8. Separate evidence and boundary agreement views

The reliability report must keep three evidence/boundary concepts separate.

### 8.1 Node mention-boundary agreement

For detection-paired nodes report:

- exact primary mentionSpan match count/rate;
- boundary-tolerant primary mentionSpan count/rate; and
- mean primary mentionSpan F1.

### 8.2 Node supporting-evidence agreement

Resolve each paired node's evidenceSpanIDs to canonical supporting spans and compare
supporting-evidence character coverage by sourceUnitID.

Report:

- exact supporting-evidence-set match count/rate;
- mean supporting-evidence-set precision;
- mean supporting-evidence-set recall; and
- mean supporting-evidence-set F1.

These measures are supporting-evidence agreement, not node mention-boundary agreement.

### 8.3 Relation-specific evidence agreement

For detection-paired relations, compare only relation-specific evidence.

Report:

- exact relation-evidence-set match count/rate;
- mean relation-evidence-set precision;
- mean relation-evidence-set recall; and
- mean relation-evidence-set F1.

Node evidence may not substitute for relation-specific evidence.

## 9. Multiple and distributed evidence

Multiple evidence spans, multiple sourceUnitIDs, or a distributedEvidenceReason field do
not automatically mean that every span or source unit is jointly required for a future
Extractor-to-Human-Core true positive.

The current records do not formally encode the historical distinction between
jointly_required and alternatives for every multi-span assertion.

Therefore:

- use the ordinary qualifying-evidence rule by default;
- impose a multi-span or multi-unit joint requirement only when a frozen annotation
  authority explicitly establishes that the spans/units were jointly necessary for that
  assertion; and
- otherwise report distributed-evidence cases separately as diagnostics.

No joint-evidence obligation may be inferred retrospectively from distributedEvidenceReason
alone.

## 10. Human-to-Human N=2 reliability measures

### 10.1 Symmetric detection measures

For a comparison stratum, let A be Annotator A's positive records, B Annotator B's positive
records, and M the number of one-to-one detection pairs.

Report:

    A coverage = M / |A|, when |A| > 0
    B coverage = M / |B|, when |B| > 0
    symmetric pairwise F1 = 2M / (|A| + |B|), when |A| + |B| > 0

If both sides have zero positives, the pairwise F1 is undefined and the zero supports are
reported.

Do not describe A coverage or B coverage as accuracy. A and B are symmetric.

Report node and relation detection separately.

### 10.2 Characterization agreement on detection-paired nodes

Report numerator, denominator, and observed agreement for:

- exact ontology class;
- exact operational target.

### 10.3 Characterization agreement on detection-paired relations

Report numerator, denominator, and observed agreement for:

- exact ontology relation type;
- exact operational relation target;
- relation direction when the paired records use the same relation type;
- source endpoint selection;
- target endpoint selection; and
- both endpoints selected consistently.

Endpoint agreement is evaluated through already established node-occurrence pairing or
exact deterministic endpoint identity. It is not assumed from labels.

### 10.4 Exhaustive presence/absence view

For routed extract_and_evaluate unit-target decisions, report:

- the raw 2x2 positive/absent table; and
- observed agreement.

Cohen's kappa is not a required primary statistic for this amended N=2 design.

### 10.5 No reliability gate

All N=2 reliability measures are descriptive and pre-adjudication.

There is no IAA threshold, PASS/FAIL decision, GO/REVISE/NO-GO gate, or production
acceptance consequence in this contract. Low or sparse agreement is reported with its raw
support and disagreement categories; it does not authorize rewriting A or B.

## 11. Treatment-specific reliability

### 11.1 extract_and_evaluate

Routed extract_and_evaluate targets are exhaustive within their frozen Human Core unit
scope. They support detection reproducibility, classification agreement, and the
unit-target positive/absent view.

### 11.2 extract_and_monitor

Monitor positives may be compared as a separate symmetric positive-set reproducibility
view.

Absence of a monitor annotation is not a confirmed negative, does not enter the
positive/absent table, and does not establish exhaustive human disagreement.

Monitor-only results must be labeled separately from the exhaustive
extract_and_evaluate reliability results.

## 12. Extractor-to-Human-Core N=5 mode

This mode is asymmetric. The frozen Human Core is the bounded reference and the extractor
output is the prediction set.

Annotator A's N=5 reference remains the non-destructive composition of immutable
primaryV014 plus immutable supplementalV015 records. Partition provenance is preserved.
No semantic deduplication or reinterpretation of those partitions is authorized by this
contract.

### 12.1 Node true-positive eligibility

An extractor node can match a Human Core node only when all mandatory conditions hold:

- same bounded source-artifact/unit evaluation scope;
- same operational target ID;
- same ontology class;
- compatible source-local occurrence/contextual identity;
- ordinary qualifying supporting evidence under Section 4 and Section 9; and
- one-to-one assignment.

A class edit, target substitution, superclass/sibling substitution, or label similarity
does not create a primary true positive.

### 12.2 Relation true-positive eligibility

An extractor relation can match a Human Core relation only when all mandatory conditions
hold:

- same bounded source-artifact/unit evaluation scope;
- same operational relation target;
- same ontology relation;
- same operational direction;
- source endpoint matched to the Human Core source endpoint;
- target endpoint matched to the Human Core target endpoint;
- qualifying relation-specific evidence under Section 4 and Section 9; and
- one-to-one assignment.

A wrong endpoint, wrong direction, or wrong relation type is not a partial true positive.

Local human endpoints are matched through the node assignment. Frozen deterministic
endpoints require exact deterministic identity.

### 12.3 One-to-one scoring assignment

For each source scope and operational target:

1. build all eligible reference-prediction pairs;
2. maximize cardinality;
3. prefer exact evidence;
4. prefer greater qualifying evidence overlap;
5. prefer smaller boundary difference; and
6. resolve remaining ties with fully qualified stable provenance keys.

One prediction can satisfy at most one Human Core record and one Human Core record can
consume at most one prediction. Extra duplicates remain false positives.

## 13. N=5 Precision, Recall, F1, and aggregation

Confirmatory Human Core P/R/F1 uses extract_and_evaluate targets only.

For nodes and relations separately:

    Precision = TP / (TP + FP)
    Recall = TP / (TP + FN)
    F1 = 2 * Precision * Recall / (Precision + Recall)

A zero denominator produces undefined, never an invented zero or one.

Primary reporting is:

- node micro Precision/Recall/F1; and
- relation micro Precision/Recall/F1.

Always report TP, FP, FN, reference support, and prediction support beside the metrics.

Per-unit, per-target, and target-family breakdowns may be reported descriptively with
support counts. Sparse target-level values must not be presented without their
denominators.

extract_and_monitor is excluded from confirmatory N=5 micro P/R/F1 unless a separate
prospectively frozen authority had declared that target exhaustive before annotation. No
such promotion is created by this contract.

## 14. Pre-adjudication disagreement taxonomy

After the frozen matcher has computed N=2 reliability, descriptive disagreement analysis
may classify cases as:

- detection;
- class;
- operational target;
- node mention boundary;
- node supporting evidence;
- relation type;
- relation operational target;
- relation direction;
- source endpoint;
- target endpoint;
- relation-specific evidence;
- atomicity; or
- other documented.

This taxonomy describes disagreement. It does not alter the pre-adjudication records or
the frozen matching rules.

## 15. Explicit exclusions

This contract does not define:

- IAA acceptance thresholds;
- PASS/FAIL criteria;
- GO/REVISE/NO-GO criteria;
- production acceptance thresholds;
- pooled-reference contributor or deduplication rules;
- pooled human-adjudication rules;
- completeness-audit sampling or statistics;
- SciERC evaluation rules;
- GraphRAG structural-comparison rules; or
- a procedure for rewriting historical Pilot 1 results.

Those are separate components of the Study 2 evaluation critical path.

## 16. Freeze statement

This contract is frozen prospectively before A-versus-B disagreement inspection and before
confirmatory N=2 reliability or N=5 Human Core P/R/F1 computation.

Implementation may encode these rules deterministically but may not change them to improve
observed agreement or extractor scores. Any future methodological revision requires a new
version, an explicit rationale independent of the observed result being optimized, and
preservation of this frozen version.
