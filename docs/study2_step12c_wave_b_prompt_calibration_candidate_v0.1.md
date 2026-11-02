# Step 12C — Prospective Wave B prompt clarification candidates v0.1

**DRAFT — wording, implementation and execution NOT AUTHORIZED.**
The researcher authorized preparation of this proposal only. Baseline:
`494f75fa829d71bbdec0debd3acea8eca6bbdc2d`. Step 12C remains OPEN;
this document neither accepts Wave A semantically nor clears Wave B.

Binding authorities: [frozen Step 11 v0.3](study2_step11_source_specific_semantic_contracts_v0.3.md),
[its acceptance](handoffs/STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md),
[ontology v0.1.6](../src/ontology/ontology_spec.yaml), accepted Steps 12A/B,
and the [v0.2 calibration plan](study2_step12c_calibration_plan_candidate_v0.2.md).

## Basis and scope

Read the consolidated and three family reports, `candidate-checks.json`, and
relevant original proposals/selected contexts under local
`var/study2_step12c/analysis/wave-A/`. These are advisory diagnostics, not gold
labels. Consolidated report SHA-256:
`75455d6ebd09bd15555fa079366c4fc65cc6d9923f688e4a30b8e0f8374f4d6b`;
candidate-checks SHA-256:
`4e82d269ef5e2c1c4ed8eec652f82734e0e9d835f11d5b6dbc4f8bda8c093c27`.
The recorded 102 mechanical validations and 69 unresolved assertions motivate
clarification, not claims of semantic error rates or prompt effectiveness.

Only prompt additions are proposed. Preserve source eligibility, exact quotations,
independent node/edge support, selected-unit boundaries, source-local identities,
endpoint inventories, conditional gates and failure isolation. No positive yield
quota, new ontology target, evidence-threshold reduction or new context-selection
policy is proposed. Empty candidate lists remain permissible; explicit abstentions
retain their existing preconditions, especially for incomplete sources.

## Exact recommended additions

Append each block as separately versioned instructions to that family's unchanged
base instructions. The HydroShare base includes the entire previously approved
[notebook/Tool clarification](study2_step12c_hydroshare_prompt_calibration_candidate_v0.1.md).
Do not insert Wave A filenames, candidate answers or case-specific corrections.

### HydroShare — proposed `hydroshare-request/1.2.0`

> Evaluate entity identity and the resource-level relation independently. For
> usesTool or usesModel, quote prose explicitly establishing this resource's use
> of the identified Tool or concrete model. A demonstration, possible future run,
> capability, or internal code dependency alone does not establish that relation.
> Multiple supplied fragments may jointly establish use when their contributions
> and connecting context are explicit; do not invent a missing connection. Source
> statements of use do not require runtime logs or external execution tests.
> mentionsTool and mentionsModel remain weaker alternatives only when the entity
> typing and the mention each have adequate independent evidence. Omit unsupported
> assertions; do not automatically downgrade or force a substitute predicate.
>
> Ground both model identity and its concrete subtype in the selected prose.
> A model-like filename, acronym, repository name, or ontology example alone does
> not establish which model the source describes. A named component or statistical
> technique does not by itself establish the subtype of the entire model. Preserve
> ambiguous or conflicting typing as an explicit ambiguity under the response
> contract, rather than guessing an abstract superclass or resolving it by outside
> knowledge. A described scientific Workflow need not imply verified execution.
>
> Propose Measurement only from selected README prose that individuates a specific
> observation through an observable with value/unit or an explicit observation
> identifier/conditions. Descriptions of columns, identifier templates, variable
> lists, or a collection's possible records alone do not instantiate a Measurement.
> Do not invent a row, value, identifier or observation from a schema. No Measurement
> yield is required. Keep the approved distinction between a functionally identified
> notebook Tool and an auxiliary code artifact; neither automatically accept nor
> categorically exclude notebooks.

### GitHub — proposed `github-request/1.1.0`

> A Function candidate must identify a named software function or method described
> in eligible prose, including its stated role. Do not turn a repository goal,
> notebook task, API as a whole, or broad capability into a Function by inventing an
> action label. A mathematical function name alone does not establish software
> Function identity; use the prose context without examining code or inferring
> signatures. Preserve ambiguity when identity or granularity is unclear.
>
> Distinguish a named, prose-characterized Algorithm from a formula, distribution,
> model, broad method or Workflow. A formula or technique mention alone does not
> establish every one of those classes. A StatisticalModel needs its own named model
> identity under the frozen profile. A Workflow requires a substantive processing
> sequence. Do not create a GitHub-local Publication Method or use Algorithm as a
> fallback for an unsupported Method. Preserve conflicting subtype evidence rather
> than resolving it through names or background knowledge.
>
> Evaluate each hasPurpose category independently against the exact six frozen
> definitions and the repository's own purpose. An external product's purpose,
> incidental example, dependency or keyword does not establish repository membership.
> scientific_experimentation requires that supporting simulations, experiments,
> calibration or evaluation is central to the repository's purpose; it does not
> require proof that the repository executed experiments. Multiple categories need
> independent support for each assignment; one sufficiently explicit passage may
> support more than one. Reuse the exact controlled seed endpoints, never create
> new category nodes, and retain unclassified/ambiguous outcomes outside the KG.
>
> Consider the repository's own identifiable software product when prose supports
> it; do not replace that identity with generic capability Functions. Independently
> quote an implementedBy relation only when the prose establishes that this exact
> repository implements or provides the source for the valid Tool/model. Its
> direction is Tool/model to Repository. uses and mentions retain their separate
> evidence criteria; use, a dependency or a link alone is not implementation.
> Do not force an own-product node, merge by name, infer external endpoints, or
> turn dependency/upstream versions into the repository's ModelVersion. Preserve
> every existing ModelVersion and implementsMethod condition and unresolved outcome.

### CIROH Hub — proposed `ciroh_hub-request/1.1.0`

> Distinguish a substantive scientific/data-processing Workflow from access,
> navigation, installation or launch instructions. Such instructions may support
> a coherent task-directed Procedure without also supporting a Workflow. Do not
> duplicate a Procedure as a Workflow solely because it has multiple steps. A
> processing sequence can be described without evidence of execution or success.
>
> A Step needs an identified instructional action in its Procedure. An automatic
> consequence or resulting state is not by itself a separately instructed action.
> Do not invent a check, confirmation or command to turn that outcome into a Step.
> Use the stated action and sequence context, preserving incomplete instructions
> when hidden, dynamic or unselected content leaves a gap.
>
> When selected prose independently supports a Procedure/Step and a procedural
> Parameter or identifiable displayed Example, you may propose the parent,
> dependent and required attachment edges together as candidates. Supply separate
> evidence for each assertion and valid ordered parentPath references from this
> page through hasProcedure, optionally hasStep, to the dependent's own attachment.
> Use the response contract's candidate_edge or trusted accepted_assertion references.
> These proposed paths are not accepted parents and do not satisfy semantic gates.
> If a parent or required relation is invalid or unresolved, its actual dependents
> remain held; independent candidates may survive. Do not invent a parent merely
> to enable Parameter or Example extraction.
>
> Parameter identity and procedural role require explanatory prose, including
> quoted wording/value when stated; a code key or argument alone is insufficient.
> Do not convert example values into defaults. A displayed fence may support only
> a literal possible Example with independently supported procedural attachment;
> never infer its execution, code semantics or parameters. No free-floating
> Parameters/Examples or nonempty output requirement is introduced. Parent semantic
> acceptance and all required relation/evidence gates remain pending until an
> independently authorized validation stage resolves them; never output attestations.

## Versioning and legacy compatibility

| Family | Explicit prospective version | Proposed immutable prompt identifier | Instruction base |
|---|---|---|---|
| HydroShare | `hydroshare-request/1.2.0` | `hydroshare-wave-b-clarification/0.1.0` | Exact 1.1.0 instructions, including approved notebook distinction |
| GitHub | `github-request/1.1.0` | `github-wave-b-clarification/0.1.0` | Exact 1.0.0 instructions |
| Hub | `ciroh_hub-request/1.1.0` | `ciroh-hub-wave-b-clarification/0.1.0` | Exact 1.0.0 instructions |

Keep HydroShare 1.0.0 as its default and 1.1.0 unchanged; keep GitHub/Hub 1.0.0
defaults. New identifiers belong only in new hashed request bodies. Hash exact
ordered instructions and version metadata; no post-hash replacement, mutable
instruction globals, implicit latest-version selection or retroactive prompt-ID
insertion. Unknown/malformed versions and mismatched instruction/identifier pairs
must fail closed.

Builders, recorded-response parsers and replay must explicitly route the chosen
request version and reconstruct its exact semantic hash. Preserve all response
contracts at 1.0.0, schemas, candidate parsing/failure isolation and semantic profiles.
Legacy request serialization and replay report bytes must remain identical.
HS-01's request stays
`66a3fd974108b18b58d0b6effed8924669558509502760e43699b2858b07f8c0`.
No Wave A request, envelope, response or analysis artifact is regenerated in place.

## Additive Wave B execution amendment

The frozen selection manifest v0.2 remains byte-identical, SHA-256
`2efbcfc9280888228d06a669c6b26cefe1191d223c61cd1b036ee96215ef49fb`.
Scope is exactly **HS-05–07, GH-05–07, HUB-05–07**. Owners, accepted endpoints,
snapshots, ordered sourceUnitIDs/spans/text hashes, endpoint inventories, Section
mappings and completeness diagnostics are inherited unchanged. No resampling.

A separately reviewed, versioned execution-amendment artifact must reference:

- The exact base manifest digest, this wording's approved digest, approved code
  checkpoint and base/new implementation file fingerprints with explicit changed-file
  scope. Unchanged source readers, ontology and target profiles retain their pins.
- Each inherited request ID and original semantic hash, its explicit new request/
  prompt version and instruction digest, and its new full semantic request hash.
- Exact provider-input bytes/hash, projection version where applicable, response-schema
  hash, envelope bytes/hash and recomputed size/context/budget reservations. Identical
  response schema hashes should remain identical; changed schema content is a stop.
- Separate new artifact paths and the prior preflight hashes. Old preflights are
  retained as superseded prospective alternatives, never overwritten or executable
  under an approval for the new hashes. One-attempt identity stays per frozen request
  ID across versions; no second execution through an amendment namespace.

**Concrete fingerprint dependency:** `calibration_preflight.py` checks the pinned
`implementationFiles`, request versions and semantic hashes. Editing request-contract
modules will make the unamended loader reject them, even if legacy serialization is
unchanged. Do not replace the base manifest's pins or disable these checks. A future
explicit amendment-aware path must verify the old manifest as immutable provenance
and the newly approved executable files against the amendment, with a bounded
old/new request-field comparison. Legacy reproducibility remains demonstrable at
the frozen checkpoint and through byte-identical legacy version routes; do not claim
the unamended file-fingerprint check will pass changed files. Historical verification
must use its frozen implementation or an explicitly approved compatibility record,
never an implicit hash exception.

**Projection dependency:** `github-provider-input/1.0.0` currently accepts only
`github-request/1.0.0`. Propose an explicit compatible
`github-provider-input/1.1.0` for new GitHub requests, retaining exactly the accepted
selection/text/provenance and audit-reduction policy. Preserve projection 1.0.0
behavior/bytes. Never relabel a 1.1.0 semantic request as 1.0.0 to bypass that guard;
the full semantic request, not its projection, remains replay authority.

Approval/preflight/terminal verification must bind the amendment digest as well as
the base manifest and every per-request hash/version. Specify that association in a
reviewed approval extension/version; do not silently add ignored fields to approval
v2 or accept an old approval for new envelopes. Wave B requires separate researcher
Wave A clearance, individual IDs, current budgets and explicit live authorization.
No such approval or execution amendment is created here.

This is HydroShare clarification round **two** (1.1.0 was round one), and proposed
round **one** for GitHub/Hub. Preserve the two-round ceiling. Wave C selections stay
frozen and its outputs must never drive tuning; any later execution-version amendment
for C requires separate approval before dispatch.

## Focused offline checks before any execution

1. **Version/byte compatibility:** all legacy default/explicit routes, new instruction
   hashes and identifiers, unknown versions, parser/replay routing; compare the twelve
   Wave A request hashes and historical replay bytes without overwriting artifacts.
2. **Synthetic contrasts:** explicit resource use versus capability; concrete model
   identity versus filename/component hints; actual README observation versus schema;
   named software Function versus capability; Algorithm/model/Method distinctions;
   independently supported purpose and correctly directed own-product implementation.
   These check instruction inclusion and preserved validators, not model comprehension.
3. **Hub dependencies:** separately evidenced candidate parent paths and prose Parameters/
   displayed Examples remain admissible as proposals but unresolved where acceptance is
   pending. Missing/invalid parent relations affect only actual dependents; code-only
   Parameters, invented coordinates and model-authored gate flags remain rejected/held.
4. **Amendment/preflight boundary:** nine unchanged owner/unit selections and inventories;
   exact old/new fingerprints; projection preserves selected text and relevant warnings;
   unchanged response schemas; new request/input/envelope hashes; wrong amendment,
   version, approval, wave clearance or budget fails closed. Preserve locks, no-retry
   behavior and one-attempt records. No live calls or broad suite is needed for these checks.

## Step 13 acceptance work still requiring approval

Prompt improvements cannot turn `validated` into semantic acceptance. Step 13 needs
a separately specified, versioned acceptance process and recorded decisions, not
exhaustive human annotation or implicit acceptance of all mechanically valid records.
Propose targeted researcher review of unresolved/conflicting families of cases plus
bounded quality checks of any authorized semantic decision stage; exact automation,
review limits and release criteria require approval. Unreviewed unresolved assertions
remain non-KG. Neither another model's unverified claim nor literal binding alone
may attest a gate.

| Gate/dependency | Remaining acceptance question |
|---|---|
| All families | Sufficient identity, typing, granularity, role and contextual support; preservation of conflicts and independent evidence. Mechanical success alone answers none of these. |
| HydroShare Measurement | `explicit_readme_measurement`: a genuinely individuated observation, not merely an eligible README span. |
| GitHub Function/Algorithm, Purpose, ModelVersion | `explicit_descriptive_prose`; repository-specific purpose with exact approved seed; own repository product, explicit prose version and absence from deterministic assertions. Trusted endpoint checks and semantic judgments remain distinct. |
| Hub ancestry and dependents | Accepted Procedure/Step semantics and required parent relations, independently supported dependent identity/attachment, explanatory Parameter prose; supported/substantively described Method when applicable. Proposed ancestry is insufficient. |
| GitHub C-C16 | Accepted traceable Publication A-P13 endpoint, explicit binding and implementation evidence. Endpoint reconsideration follows accepted Step 13 Publication production; materialization remains separately authorized Step 14 work. |

No new acceptance policy, gate resolver or validator weakening is adopted here.
DataService/servesDataset stay inactive; D-26 and superclass assertions remain
pipeline-derived. Source incompleteness is never converted into no-evidence.

## Decisions requested

Approve or revise the exact three additions and opt-in version/prompt identifiers;
confirm contingent Hub dependent proposals remain distinct from acceptance. Resolve
any desired interpretation of mathematical versus software Function, model subtype
conflicts with ontology exemplars, notebook identity and Measurement individuation
through explicit researcher decisions, not case-specific prompt answers.

Separately authorize implementation and the additive fingerprint/projection/approval
amendment design, then review its exact generated hashes and budget before live
Wave B authorization. Define the Step 13 acceptance process separately. This proposal
alone authorizes none of those actions and leaves the handoff unchanged.
