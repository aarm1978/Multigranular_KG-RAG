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

## v0.1.8 refresh — current execution package

The current default package is `var/study2_step14/alignment-workflow/prepared-v018/`.
The `prepared-v1` population and all its files remain unchanged. `refresh` verifies
that package's saved hashes and transforms its requests without running selection,
candidate discovery, upstream evaluations or the original preparation routine.
The earlier sections record the v0.1.7 checkpoint, not current predicate availability.

All **1,795 requests are retained and modified** (clarified evidence instructions);
**zero added or removed**. Original occurrence payloads, quotation aliases, unit IDs,
routing inventories, decisions and provenance are preserved. Only instructions,
admissible ontology signatures, response schemas, representation gates and derived
summary/manifest files change. D-27 becomes available in **984 requests**, D-28 in
**104**. **W01566 and W01572** remain predicate-empty Workflow cases. Ten artifact
mapping range holds resolve under D-16; the Workflow mapping remains held. None
of these changes approves identities or establishes a relation's scientific validity.

Identity may use independent source-local spans without cross-artifact citations.
Artifact-to-entity mention/use evidence retains its artifact role. Nonidentity
entity-to-entity relations may use jointly evaluated source-local spans, but must
support the specific predicate and direction. Shared mentions do not establish an
artifact-to-artifact relation. Co-occurrence, similarity, version numbers alone and
predicate availability do not force an edge; abstention remains valid. D-27/D-28
use the exact v0.1.8 signatures and evidence requirements, not a universal family
or variant rule. The original acceptance and evaluation gates remain in force.

Approximate totals: **4.16–6.93 million input tokens**, **1.80–8.98 million output
tokens**. These retain the existing coarse estimation method, not exact counts.

```bash
# Offline refresh (already performed; destination must be fresh)
python -m src.evaluation.step14_alignment_workflow refresh
# Offline verification of the current package
python -m src.evaluation.step14_alignment_workflow verify
# Later researcher-terminal execution, using unchanged transport infrastructure
python -m src.evaluation.step14_alignment_workflow live --units W00001
python -m src.evaluation.step14_alignment_workflow submit
python -m src.evaluation.step14_alignment_workflow status
python -m src.evaluation.step14_alignment_workflow retrieve
```

The historical `prepare` routine is not the v0.1.8 migration entry point; use
`refresh`, optionally with `--source` and a fresh `--root`. No execution records
are copied or provider calls made by refresh. Do not dispatch both package versions.
The refresh passed eight focused synthetic tests and offline verification, including
exact evidence preservation and applicability of new predicates.

## Final payload cleanup — current execution package

The current default is `alignment-workflow/prepared-v018-clean/` under
`var/study2_step14/`. Both `prepared-v1` and `prepared-v018` remain unchanged.
This is a transformation of all **1,795 existing requests**, not new selection:
zero added/removed, unchanged candidates, evidence spans, provider model,
reasoning settings, ontology v0.1.8 and predicate constraints.

The actual model-visible audit found **10,708 occurrence slots** with long internal
IDs, empty `versions: {}` and placeholder granularity, plus **4,466** predicate
entries duplicating `id` and `signatureID`. All empty version objects/placeholders
are removed; `signatureID` alone identifies predicates. The response's granularity
assessment remains required. Original meaningful names/aliases and literal evidence
are preserved, including scientific DOI/resource identifiers, version statements,
URLs and code/notebook paths. A lexical scan found URL/path-like source text in
289 requests; these source quotations are not pipeline metadata and are not edited.
No nonempty structured version metadata existed in the audited input population.

No input fields for previous predictions/scores, eligibility, blocking/adjudication,
execution history or local provenance files/hashes were present. Remaining predicate
fields are name, signatureID, domain, range, compatible subject/object classes,
evidenceRequirement and meaning. Necessary ontology evidence/semantic notes remain.
The removed internal IDs also formerly appeared repeatedly in response schema enums.
They now use deterministic request-local `E1`, `E2`, … aliases. Quotation identifiers
(`E1Q1`, etc.) are unchanged. `alias-bindings.json` is local-only and maps each unit's
aliases bijectively to exact original occurrence IDs. The full original provenance
and unit membership files remain byte-identical outside provider bodies.

The contradictory instruction requiring exact quotations to affirm a relation
between both named endpoints is removed. Independent/jointly evaluated source-local
spans may establish compatible strict identity or support a specific directed typed
relationship without a direct cross-artifact citation. Shared mentions, co-occurrence
or similarity alone do not suffice. Existing signatures, strict-group safeguards,
artifact-versus-entity roles and abstention remain authoritative. Predicate evidence
requirements from the approved ontology are retained without reinterpretation.

Native responses and `*.hypotheses.json` preserve authentic model aliases/text.
Both live and Batch processing additionally write `*.resolved-hypotheses.json`,
resolving structured endpoint fields in **assessments, typedRelations and ontologyGaps**.
Evidence aliases and free-text reasoning are not rewritten. Original IDs therefore
remain exactly recoverable without modifying authentic model output. Missing or
inconsistent alias bindings fail validation; these files remain hypotheses, not approvals.

The ignored `payload-audit.json` records transformation counts. Preparation verifies
all source package hashes, complete occurrence reconstruction, unchanged quotations
and predicates, no long IDs in instructions/schema, and unchanged provider settings.
Nine focused tests passed, including alias recovery through mocked live and Batch
retrieval. Offline package verification passed. Approximate totals now are
**3.25–5.42 million input tokens** and **1.80–8.98 million output tokens**; output
estimates remain the same coarse planning range, not exact counts or guarantees.
Two Workflow predicate-empty units and the one Workflow mapping range hold remain.
Textual citation matching validates bindings, not the scientific truth of any inference.

```bash
# Offline cleanup reproduction; destination must be fresh (already generated locally)
python -m src.evaluation.step14_alignment_workflow cleanup --source var/study2_step14/alignment-workflow/prepared-v018
python -m src.evaluation.step14_alignment_workflow verify
# Later researcher-terminal execution; no calls performed during preparation
python -m src.evaluation.step14_alignment_workflow live --units W00001
python -m src.evaluation.step14_alignment_workflow submit
python -m src.evaluation.step14_alignment_workflow status
python -m src.evaluation.step14_alignment_workflow retrieve
```

Skip live to submit the complete package through Batch. Do not dispatch multiple
package versions. No additional controls or approval workflow are introduced.

## Localized source-artifact context correction

The current default package is `alignment-workflow/prepared-v018-source-context/`.
It is derived only from `prepared-v018-clean`, which remains unchanged along with
its five-request live pilot execution records. All 1,795 requests, occurrence aliases,
source evidence, predicate options, response schemas and provider settings are retained.
The only provider-input changes are `sourceArtifactRef` and the instruction clarification.

Each occurrence gets a short request-local S1/S2/... reference, assigned in occurrence
order using the saved endpoint's single source artifact. The member sidecar must agree.
Missing, multiple or conflicting artifacts fail closed rather than guessing. All actual
prepared occurrences passed this check. The local-only `source-artifact-bindings.json`
retains exact artifact identifiers; no original artifact ID, path, hash, history or
previous assessment is added to provider input. Occurrences sharing an artifact share
an S alias; different artifact identifiers receive distinct aliases within each request.

Instructions now explicitly state that identical wording or a shared generic procedure
does not independently establish strict identity; different artifacts can describe the
same named entity; and shared source membership provides context without proving
identity or model version. Evidence-based cross-artifact identity, directed typed and
version relationships, existing ontology constraints, and abstention remain intact.

Verified actual package cases:

| Request | Source-artifact references |
|---|---|
| W01566 | E1=S1; E2=S2 (different GitHub repositories) |
| W00119 | E4=E5=E6=S4 (one publication) |
| W00001 | E9=E10=S9; E11=E12=S10 (two distinct publications) |

Ten focused tests and offline package hash verification passed. Mocked live and Batch
retrieval continue to reconstruct original occurrence IDs. No pilot outcomes or
execution claims are copied to the new package. A later rerun is a separate execution,
not a continuation that silently reuses old dispatch records. Approximate input tokens:
3.50–5.83 million; output estimate remains 1.80–8.98 million. No provider calls occurred.

```bash
# Offline generation (already completed; use a fresh --root to reproduce)
python -m src.evaluation.step14_alignment_workflow source-context --source var/study2_step14/alignment-workflow/prepared-v018-clean
python -m src.evaluation.step14_alignment_workflow verify
# Subsequent researcher-terminal execution uses the new default package
python -m src.evaluation.step14_alignment_workflow live --units W01566 W00119 W00001
python -m src.evaluation.step14_alignment_workflow submit
python -m src.evaluation.step14_alignment_workflow status
python -m src.evaluation.step14_alignment_workflow retrieve
```
