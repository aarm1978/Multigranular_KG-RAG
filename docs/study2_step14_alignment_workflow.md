# Step 14 identity and typed-relation workflow — offline preparation

This preparation reuses saved Step 14 artifacts and ontology **v0.1.7**, under the existing scope, identity/granularity and automatic-acceptance policies. It changes no acceptance rule. “Final workflow” means a prepared path toward closure, not finalized identities. Production still requires the frozen acceptance procedure, independent bounded evaluation, representation decisions and separately authorized materialization. No provider calls, canonical allocation, ontology edits, approvals or graph writes occur during preparation.

## Saved populations and prepared scope

| Population / output | Count |
|---|---:|
| Disjoint provisional groups / occurrence mapping proposals | 364 / 970 |
| Overlap-blocked scopes / existing components / distinct occurrences | 13,244 / 240 / 3,261 |
| Initially ineligible scopes / distinct occurrences | 37,471 / 11,267 |
| Ineligible occurrences overlapping eligible pool / outside it | 3,492 / 7,775 |
| Shared-reference / conceptual-similarity comparisons prioritized | 3,021 / 1,937 |
| Additional negative/abstaining comparisons with affirmative literal leads | 114 |
| Overall oversized scopes / saved cross-family oversized scopes | 25 / 17 |
| Prepared requests / distinct request occurrences / cross-family requests | 1,795 / 4,586 / 422 |

These are distinct denominators, not recall, validated recovery, or approved identity counts. All 74,051 saved pair records retain routing entries (including 635 unassessed records); no old pair evaluation is rerun. The original approval ledger is copied byte-for-byte. The 37,471 initially ineligible population includes 20 researcher-approved exact scopes and 3,701 provisional nonidentity scopes: “initially ineligible” is not synonymous with rejected or unreviewed.

Mapping proposals preserve each original occurrence ID and reference, the exact saved complete group, its safeguards and approval subsets. `local-proposal:scope:...` is a proposal-local reference, **not a production canonical ID**; `canonicalID` remains null. There is no `owl:sameAs` output. **Eleven groups require a D-16 range decision**: nine DatasetResource, one Workflow and one Paper. Their proposals remain present and explicitly gated. Signature-compatible proposals also remain gated by scientific acceptance/evaluation, not automatically approved.

The actual nonexclusive exclusion counts are reported in `summary.json`, with distinct occurrences per reason, and per-scope details in `ineligible-inventory.jsonl`. Leading failed safeguards are `noModelConflictOrMissingInformation` (33,612 scopes / 10,479 occurrences), `noUnresolvedReportedAmbiguity` (33,524 / 10,205), and `completePositiveComparisons` (14,263 / 6,289). Pilot-scope compatibility fails for 775 scopes / 466 occurrences. Counts overlap and must not be summed. Saved states, actual reasons, evidence limitations, prior approval subsets and original group identifiers remain recoverable.

Routing identifies 19,270 ineligible scopes as identity-reconciliation candidates, 3,938 for typed-relation consideration, and 14,313 unresolved (identity/relation routes may overlap). Identity leads require available endpoint quotations, one class, no saved demonstrated conflict, no negative-pair flag or prior approval intersection, and existing positive comparisons. These are **review leads, not a new acceptance rule**. Any missing information or scientific version/granularity ambiguity remains unresolved until supported. The inventory preserves other scopes; they are not silently converted to identity. Of 32,406 positive comparison leads, 27,310 are deliberately not dispatched as new pair evaluations; the remainder are co-located in the prepared neighborhoods. This preparation inventories identity headroom without restarting the completed pair campaign.

## Request construction and limits

The 240 existing components produce **915 bounded neighborhoods**, each containing at most 12 occurrences. Choose a source occurrence by original-group degree and stable ID, include neighbors sharing original memberships, then cover remaining occurrences. This is evidence packaging, never a component identity union. All component occurrences appear, but **4,888 original scopes span requests** and cannot receive a complete-group conclusion from those requests. `component-coverage.jsonl` preserves exact original group IDs, occurrence membership, unit indices and complete-versus-spanning scope counts. It does not declare cross-request consistency or fill missing comparisons.

Another **880 requests** cover remaining typed-relation leads by deterministic witness-star packing of existing explicit nominated edges. Comparisons already co-located in an overlap request reuse that request. All 4,958 shared-reference/conceptual comparisons enter consideration; their old labels alone establish no relationship. Negative/abstaining cases enter only when a saved sentence contains distinguishable names for both endpoints and an affirmative relational phrase, excluding explicit negation/speculation. This is a conservative **literal lead**, not a semantic certificate: attachment, role, name ambiguity and version specificity still require reasoning. Equal/shared names alone cannot pass this screen. Unrecognized phrasing stays preserved and unresolved. No full candidate discovery, embeddings, extraction, pairwise expansion of oversized scopes, or new connected-component identity inference occurs.

Provider inputs contain occurrence IDs, source names/classes/families, raw version/granularity information, original selected quotation text and local evidence aliases. Versions can be capture metadata and must not be inferred entity versions. Hashes, source references, safeguards, recommendation history and approval decisions remain local. `E<i>Q<j>` binds to the i-th occurrence in the unit's ordered membership and j-th untouched selected quotation in `occurrence-provenance.jsonl`. No incident relation is relabeled as a quotation. Original member/provenance records retain available identifiers and scientific provenance; no fresh semantic summaries are generated.

## Ontology and output validation

Allowed predicates come from exact ontology inventory signatures, with declared superclass closure, direction, evidence requirements and semantic notes. Signature alternatives remain individual inventory IDs rather than accidental domain/range Cartesian products. Existing `hasComponent` denotes explicit composition, not version/family membership. `hasModelVersion` retains its Repository domain; dataset `isMemberOf` remains collection-specific. Neither the generic mention relation nor shared-target evidence authorizes stronger uses/implementation claims. Unknown classes fail closed. Provenance and identity predicates are not offered as typed nonidentity relationships.

Responses contain the existing anchor assessments (strict identity, broader correspondence, related nonidentity, distinct, abstention), plus directed `typedRelations` and separate `ontologyGaps`. Every non-abstaining assessment and relation needs evidence bound to its exact endpoints; all occurrences must be assessed. Typed relations require an allowed signature and compatible subject/object classes. Response validation checks structure, citation ownership and signatures, **not semantic truth**. All strict subsets and broader anchors remain local hypotheses. No overlapping subsets are merged, no approval is propagated, and no model result is promoted automatically.

**106 requests have no compatible existing nonidentity predicate.** Abstention or an evidence-bound gap is legitimate. `ontology-gaps.md` records prospective representation issues; `execution/Wxxxxx.ontology-gaps.json` will separately retain model-proposed gaps. Family/release or architecture/instance semantics, including the previously proposed `correspondsToBroaderReferent`, require researcher review before any ontology amendment. The absence of a compatible predicate does not prove an amendment is necessary. No schema generation or ontology modification is part of this workflow.

## Local package and execution

The ignored package is `var/study2_step14/alignment-workflow/prepared-v1/`:

- `mapping-proposals.jsonl`, `ineligible-inventory.jsonl`, `component-coverage.jsonl`, `pair-routing.jsonl`;
- `requests.jsonl`, `units.jsonl`, `occurrence-provenance.jsonl`;
- unchanged `prior-decisions.jsonl`, complete `oversized-inventory.jsonl`, original `saved-cross-family-oversized.jsonl`;
- `ontology-signatures.jsonl`, `ontology-gaps.md`, `summary.json`, `manifest.json`.

The earlier ignored `alignment-workflow/v1/` is a development draft, not this execution package. Manifests bind saved producer hashes and current implementation/authority bytes; existing artifacts remain untouched. Preparation completed under the 25-second offline guard. It is fresh-directory-only; incomplete preparation has no dispatchable manifest.

Rough totals for **1,795 planned requests**: **3.77–6.29 million input tokens**, **1.80–8.98 million output tokens**, including reasoning. Input estimates use serialized bytes / 5 to / 3; output uses 1,000–5,000 per request as a planning range, not a guarantee. The inherited output limit is 16,384 per request. Actual usage is saved from responses. No budget-control or token-counting API is introduced.

From the repository root, use the existing Python environment with `jsonschema` and `PyYAML`:

```bash
# Offline verification of the already-prepared package
python -m src.evaluation.step14_alignment_workflow verify

# Later researcher-terminal live execution of one or a few units
python -m src.evaluation.step14_alignment_workflow live --units W00001

# Later submit all remaining unattempted requests through Batch
python -m src.evaluation.step14_alignment_workflow submit
python -m src.evaluation.step14_alignment_workflow status
python -m src.evaluation.step14_alignment_workflow retrieve

# Validate a model JSON object offline (not its Responses envelope)
python -m src.evaluation.step14_alignment_workflow validate --units W00001 --response /path/to/model-output.json

# Reproduce offline only if needed, in a fresh ignored destination
python -m src.evaluation.step14_alignment_workflow prepare --root var/study2_step14/alignment-workflow/reproduction-v1 --time-limit 0

python -m unittest discover -s tests -p test_step14_alignment_workflow.py -v
```

Skip live to submit the whole package directly. Live and Batch consume identical bodies/schema and reuse the existing `BatchAPI`, credential loader, immutable writers and per-unit dispatch claims. No credential is accessed during offline preparation or verification. A unit attempted in one transport cannot be dispatched in the other. Existing Batch size limits are enforced. Generation POSTs are not retried; interrupted or uncertain execution requires receipt reconciliation, never blind resubmission. Read-only status/retrieval can repeat. Native responses/error files, actual usage, validated hypotheses and separately labeled gaps remain under ignored `execution/`. No command writes identities or production graph mappings.
