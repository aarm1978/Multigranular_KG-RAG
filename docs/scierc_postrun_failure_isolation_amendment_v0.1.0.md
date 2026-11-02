# SciERC post-run failure-isolation amendment v0.1.0

Researcher-approved on 2026-10-06 in this conversation, after the completed official
100-document traversal and test-output diagnostics. **This was not predeclared.**
Both policies below are fixed before accessing gold or computing their scores.
They must both be reported regardless of results, without a composite score.

This narrowly amends output failure handling only. Retained Step 5 §12 scoring,
the frozen native schema, exact-span/type entity matching and relation-type plus
endpoint-span matching remain unchanged. Endpoint entity types do not enter the
primary relation key; COMPARE/CONJUNCTION alone are symmetric. No coreference,
CIROH mapping or Publication Production Acceptance is introduced.

## A — Amended record-isolation view (post-run)

Apply one gold-independent rule uniformly to all 100 original responses. First
require strict JSON/schema, the correct document identity, unique nonblank entity
and relation IDs, valid source spans, resolvable same-document/same-sentence
endpoints, and all other existing structural/signature constraints. Any error
other than PREDICTED_MENTION_TEXT_NOT_EXACT_TOKEN_SPAN is a blocker, including
errors on records that would otherwise be excluded.

Find every entity whose mentionText differs from the authoritative indexed request
tokens for its zero-based inclusive span joined with one space. Exclude that entity
and every relation referencing it. Retain independent records with identical fields
and order. Do not repair text/spans, infer intent, reassign IDs/endpoints, normalize,
or add predictions. Retained payloads must pass the unchanged full validator.
Materialize separate projections and explicit direct/dependency rejection ledgers;
never rewrite authentic requests, responses, validation records or run outcomes.

## B — Document-rejection sensitivity (post-run reporting decision)

Use the original 98 completed_valid document predictions unchanged. For each of
the two originally rejected documents, use empty entity and relation collections
under its original document ID. These documents remain in the evaluation; all
their gold support remains in the complete 100-document denominator. This is a
post-run sensitivity policy, not a predeclared confirmatory policy.

## Ordering and preservation

Record this approval in evaluation_decisions.md before scoring. Materialize and
hash both gold-blind 100-document projection files, rejection ledger and provenance
manifest before loading benchmark gold. Verify canonical equality for the 98
previously valid predictions and exact retained-record field/order equality for
the affected documents. Then score both fixed files against the complete frozen
test split with the unchanged deterministic scorer: entity/relation TP, FP, FN,
gold/prediction support and micro P/R/F1. Preserve undefined zero-denominator cases.

No new provider/model calls, reruns, semantic adjudication, gold-guided filtering,
prompt tuning or additional exclusion categories are authorized. Existing frozen
authorities, smoke evidence and Step 8 remain byte-identical. Step 9 remains open.
