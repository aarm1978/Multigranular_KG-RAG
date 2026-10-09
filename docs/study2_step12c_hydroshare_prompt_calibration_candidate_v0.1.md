# Step 12C — Prospective HydroShare prompt calibration candidate v0.1

**Wording and opt-in version mechanism APPROVED; offline implementation complete.**
**Live calibration NOT AUTHORIZED; Step 12C remains open.** Original proposal checkpoint:
`a1faeb5ac7843ce5de9add45e095b37065aed306`.

## Authority and historical boundary

Binding authorities remain [Step 11 v0.3 §§2–3, 6 and 8](study2_step11_source_specific_semantic_contracts_v0.3.md),
its acceptance record and [ontology v0.1.6](../src/ontology/ontology_spec.yaml).
Steps 12A/12B establish technical integration/readiness, not semantic truth.

Inputs read: preserved HS-01 terminal request/response and analysis replay records,
plus local `var/study2_step12c/analysis/HS-01/HS01_independent_semantic_review_candidate.md`
(SHA-256 `7c88cd980a41090dbe8d1ccbbbd12b07de7aaba69b708296fcf7b9ca30842b16`).
That review is **advisory, not accepted labels or semantic truth**. Its reported
four-supported/four-adjudication tally is not an accuracy estimate. This draft does
not ratify it or relabel any authentic assertion.

Preserve HS-01 exactly:

| Artifact | SHA-256 |
|---|---|
| Semantic request | `66a3fd974108b18b58d0b6effed8924669558509502760e43699b2858b07f8c0` |
| Provider envelope | `402190f9a94eb6e2c3c966406d1a745bcc23fec9d1b0908dd2fe767276d464a7` |
| Raw provider response | `382ffe161467211dc0284b6f68c9115e5efa7c90312f196b37a5326d7d58cc93` |
| Exact model-output bytes | `d6359d15315db2060ede123f0236d8ed4df92db3d7f15861f841db7195e37d04` |
| Original replay report | `c894965f4506242f92f1e4f9a30d82285cefea7d5ecbe5893fc330c0901ee19a` |

All eight original records remain machine-validated, with semantic acceptance
unevaluated and KG authorization false. The original drafting task did not rerun
replay; the implementation verification below reproduced it offline without writes.

## What the frozen authorities establish, and what remains interpretive

`Tool` (A-DOM02) is a subclass of abstract `SoftwareEntity` (A-DOM01), anchored
under `schema:SoftwareApplication`. SoftwareEntity is not an authorized prediction
fallback. The ontology does not make every executable file a Tool, nor expressly
exclude notebooks or require a packaged, standalone application. A filename
identifies an artifact; it does not by itself establish its functional software
identity. An executable notebook can plausibly embody an identifiable computational
Tool. An auxiliary source file can instead be part of its implementation. These
are distinctions for evidence-based typing, not new ontology classes.

C-D18 `DatasetResource usesTool Tool` needs prose explicitly establishing tool use;
C-D24 `mentionsTool` permits reference without sufficient use evidence but retains
Tool as its range. Internal code-call relationships do not automatically lift to
the resource-level predicate. Conversely, require source-grounded use evidence,
not an invented requirement for runtime logs or independent execution experiments.

`Workflow` (A-C11), anchored to `p-plan:Plan`, with C-D22 `explainsWorkflow`, concerns
a substantive scientific/data-processing sequence. It is neither a synonym for a
code file nor a claim that execution happened or succeeded. A described workflow
may remain supportable even if an associated Tool typing or use edge is unresolved.
Directory requirements alone are insufficient; their role in the described
scientific sequence matters.

## Four HS-01 assertions: separate typing from predicate strength

The four original candidate IDs are listed below; exact quotations remain in the
local review packet and authentic output.

| Original assertion | Reading that may support it | Unresolved issue; no final judgment |
|---|---|---|
| `node-d677e83c-tool-analysis-rmd` | The abstract identifies an R Notebook that reproduces analysis and generates figures with supplied data. This is functional evidence beyond its extension. | Is that sufficient to identify a Tool occurrence, rather than only a notebook implementation artifact? Plausible; do not categorically reject notebooks. |
| `node-d677e83c-tool-functions-r` | The abstract identifies a named file whose functions the notebook calls; supporting computational functionality is evident. | A called helper file is not necessarily a distinct Tool/SoftwareApplication. Evidence for independent functional identity is weaker, but filename granularity alone does not prove the assertion false. |
| `edge-d677e83c-uses-tool-analysis-rmd` | The notebook processes resource data and generates outputs in the described reproducibility setting, if its Tool typing is accepted. | Its own quotation is conditional: “will reproduce” / “when run.” The general statement about analysis code used to develop the analysis is context, not independently supplied evidence for this edge. Does its actual quoted evidence establish use rather than capability/instructions? Do not repair the original edge by adding evidence. |
| `edge-d677e83c-uses-tool-functions-r` | Unlike the notebook edge, this edge supplies two fragments: the general code/data-use statement and the notebook-to-helper call statement. Consider their combined contribution fairly. | Neither the valid Tool endpoint nor the resource-to-Tool relationship follows automatically from the internal dependency. Whether the combined fragments sufficiently establish resource use remains adjudicative; do not invent a Tool-to-Tool edge or assume all indirect implementation relationships are invalid. |

A weaker `mentionsTool` proposal would still need supported Tool typing and its own
independent evidence. It cannot rescue an invalid Tool node. No original edge is
converted, deleted or downgraded by this draft.

## Approved general prompt addition (prospective only)

> Distinguish an identifiable computational Tool from a source-code artifact that
> merely implements part of another program. A filename, extension, executability,
> or statement that one file calls another does not by itself establish a separate
> Tool entity. A notebook may qualify when the selected prose sufficiently identifies
> its functional software role; do not automatically accept or exclude notebooks.
>
> Evaluate Tool identity and each resource-to-Tool relation separately. Propose
> usesTool only when independently supplied evidence explicitly establishes this
> DatasetResource's use of that valid Tool. Internal code dependencies, availability
> of reproducibility code, or instructions about what will happen if code is run
> do not by themselves establish the stronger use relation. Interpret multiple
> supplied fragments together without inventing missing links; give each fragment's
> contribution. Source statements of use do not require external execution testing.
>
> mentionsTool is weaker than usesTool, but still requires a valid Tool entity and
> independent evidence that the resource mentions it. If an entity typing or a
> proposed relation lacks support, omit that unsupported assertion rather than force
> it into an available class or predicate. Preserve independent supported proposals;
> explicit abstention records retain the existing contract's preconditions.
>
> A Workflow describes a substantive scientific or data-processing sequence and
> its meaningful actions/dependencies. Describing that sequence need not establish
> verified execution or success. Do not infer a Workflow solely from filenames,
> directory arrangements or incidental installation instructions.

This addition deliberately contains no HS-01 names or output-specific corrections.
It proposes no new Tool eligibility threshold such as packaging, publication,
separate distribution or runtime proof. The researcher approved this wording for explicit prospective opt-in use; original
HS-01 semantic ambiguities remain unresolved.

## Approved version mechanism and implementation status

Do not edit the existing `INSTRUCTIONS` in place. `build_request()` embeds them in
the hashed body, and offline replay rebuilds that body. An unversioned edit would
break historical reconstruction even with the same source units.

Implemented explicit opt-in request variant:
`hydroshare-request/1.1.0`, with immutable prompt identifier
`hydroshare-tool-role-clarification/0.1.0`. Keep the existing default
`hydroshare-request/1.0.0` and its exact instruction bytes/serialization unchanged.
The version selector appends the approved text only on explicit selection
of 1.1.0 and includes the prompt identifier in that new hashed body. Unknown variants
fail closed. No global monkey-patching, silent latest-version default or post-build
prompt replacement is acceptable.

`hydroshare-response/1.0.0` and its field/evidence schema remain unchanged.
The recorded-response parser explicitly recognizes the new **request** version;
new replay inputs must carry the opt-in variant so the same builder reconstructs
its exact hash. Preserve the legacy replay path and report bytes. Existing report
fields already retain the complete request/version; no generic orchestration
framework is needed. Provider envelopes and approval hashes must be newly generated
for the prospective case; never reuse HS-01 approval or overwrite its attempt.
Implementation changes only the HydroShare request contract plus focused tests.
`build_request(..., request_version="hydroshare-request/1.1.0")` selects the approved
addition and hashes `promptIdentifier` with its instructions. Omitting the argument
or explicitly choosing 1.0.0 retains the exact legacy body. Parsing recognizes
both request versions, retains response 1.0.0, and checks the prospective prompt
identifier/wording. Unknown or malformed versions fail closed.

The existing offline replay already forwards `request_inputs` to `build_request`;
passing the same explicit `request_version` there reconstructs the selected hash.
No replay-module or provider-envelope change was needed. New live preflight and
approval artifacts for a separately selected development case remain future work.

Focused validation passed **22 tests**: four new version tests plus directly affected
existing HydroShare request/replay tests. It checks pinned pre-change synthetic request and
replay hashes, deterministic opt-in construction, version/hash routing, malformed
versions and unchanged local failure isolation. A bounded offline reconstruction
also verified the original HS-01 request SHA-256 and byte-identical saved replay
report listed above. All 32 files in the inspected HS-01 terminal/analysis and
three-request preflight directories retained their original hashes. No provider
call, new response, historical artifact write or semantic adjudication occurred.

Authority issue: if adjudication requires a new categorical exclusion of notebooks
or helper scripts, or a new execution-proof requirement, that exceeds this draft's
discriminating guidance and must return to the researcher. Do not encode such a
policy as an implementation fix or silently alter frozen authorities.

## Prospective checks and precise approval questions

The completed offline checks above establish version compatibility and routing,
not whether a model interprets semantics correctly. A prospective semantic review
can distinguish a named functional program, a merely called helper, use evidence,
conditional reproducibility and a described workflow.

Then propose **one separately approved development request, not HS-01**: choose one
other eligible HydroShare abstract/verified README with enough context to judge
functional identity and resource role. Freeze its exact owner, units, hashes and
review questions before the call; no source is selected or audited in this task.
Use one attempt under separate budget/approval, preserve authentic bytes, replay
unchanged, and review all proposals/omissions qualitatively. No forced target yield,
paired improvement claim, Recall/F1 or new gold labels follow from one development
case. Do not rerun HS-01 or consume its reserved historical identity.

Researcher decision status:

1. Does the notebook's functional description suffice for Tool typing, and what
   additional selected-source evidence, if any, distinguishes the helper as a Tool?
   Decide each original node separately with rationale; packaging is not presumed.
2. Does each edge's **already supplied** evidence support DatasetResource usesTool?
   In particular, how should the helper edge's two fragments be interpreted without
   treating an internal call as sufficient by itself?
3. **Approved for prospective opt-in implementation:** The general wording clarifies
   the frozen profile, including valid-Tool prerequisites for mentionsTool and
   described-not-executed Workflow; it does not adjudicate questions 1–2.
4. **Approved and implemented:** Explicit 1.1.0 opt-in version mechanism and legacy hash/replay invariant.
5. Separately approve the new development case, exact source/context, call budget
   and review procedure? Until then, no live calibration occurs.

Only the HydroShare request contract, focused version tests and this status record
change. Default legacy instructions, original pilot artifacts, selected envelopes,
frozen contracts, ontology, evaluations, graphs and the tracked handoff remain
unchanged. This implementation does not complete live calibration or Step 12C.
