# Human Core N=5 secondary semantic-equivalence sensitivity protocol v0.1.1

Status: definitions fixed before researcher review; review pending. Step 7 remains
PRE-FREEZE. This is not a Step 7C freeze or closure record.

This corrected instrument replaces the unused sensitivity v0.1.0 instrument for
future review only. No researcher judgments have occurred. Preserve its protocol,
JSON and report byte-for-byte. Strict Step 7B v0.1.1 remains unchanged and primary.
No Human Core, C1, routing, acceptance, lifecycle or strict matching rule changes.

## Review and correspondence

Review all 118 Human Core nodes and 61 relations, including every strict TP.
Each item has an initially null `reviewedC1RecordKey` and
`researcherDisposition`. `semantic_equivalent` requires exactly one selected C1
key resolving to the same source unit, operational target and ontology class
(same relation target/type for relations). Fully qualified keys retain partition,
session/request and candidate provenance; bare candidate IDs are not sufficient.
Final semantic-equivalent selections must be globally one-to-one: no Human Core
record or C1 record may be consumed twice. Competing selections must be resolved
by the researcher before any metric is computed.

Node equivalence additionally requires researcher judgment that the records
represent the same source-local assertion/entity under the frozen target
definition and identity policy. Evidence-boundary differences, including anchored
containment in either direction, may support but never establish equivalence.
No target/class substitution, label similarity rule or automatic rescue is allowed.

Relation equivalence requires the same direction and researcher-reviewed
equivalent source and target endpoints. Endpoint context exposes exact identities,
labels, target/classes and evidence when available, without inferring equivalence.
Context-only endpoint nodes do not expand either metric population. A relation
absent from C1 cannot be rescued because its nodes exist. Review relation-specific
evidence as well as endpoints. Strict matches are review context, not judgments.

Allowed correspondence dispositions: `semantic_equivalent`, `not_equivalent`,
`target_or_class_disagreement`, `insufficient_to_decide`.
For `target_or_class_disagreement`, an optional selected key may identify any exact
same-unit C1 record motivating that judgment. Cross-target/class records remain
ineligible for semantic recovery. Candidate buckets are structural review aids,
not a ranking or automatic semantic decision.

## Independent source support

Every C1 prediction has exactly one independent source-support item: 102 nodes
and 59 relations, including strict TPs. Its initially null judgment is one of
`supported_as_proposed`, `not_supported_as_proposed`, or
`insufficient_evidence_to_decide`. Strict status does not imply support.
C1-only assertions remain outside Human Core and cannot rewrite it. These
judgments do not automatically select or remove correspondence pairs.

## Optional explanatory codes

| Code | Meaning |
|---|---|
| E1 | evidence-boundary equivalence |
| E2 | different-local-occurrence equivalence |
| E3 | assignment/competition artifact |
| M1 | semantically questionable strict TP |
| T1 | genuine extraction miss |
| T2 | unsupported/spurious C1 prediction |
| R1 | source-supported C1 assertion absent from Human Core |
| R2 | target/class disagreement |
| P1 | endpoint-propagated relation disagreement |
| P2 | genuine relation miss |

Codes are explanatory only and do not override eligibility or establish a match.
All disposition, selected-key, code and note fields begin unset.

## Secondary metrics fixed before review

Human-Core semantic recovery = one-to-one researcher-confirmed
`semantic_equivalent` Human Core records / all Human Core records, separately
for nodes (118) and relations (61).

C1 source-supported prediction rate = `supported_as_proposed` C1 predictions /
all C1 predictions, separately for nodes (102) and relations (59). Report
`not_supported_as_proposed` and `insufficient_evidence_to_decide` counts separately;
neither is removed from the denominator.

Do not compute or populate either metric before all researcher judgments are
complete and selections satisfy the global one-to-one constraint. Pending
metrics are null, never zero. These secondary metrics do not supersede strict
Step 7B P/R/F1. No provider/model calls, automatic judgments or Step 7C are part
of this instrument.
