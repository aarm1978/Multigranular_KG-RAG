# Publication Step 8 initial review UI

The local interface implements the accepted Step 8B candidate-review packages
under Step 5 v0.1.4 (amendment v0.3), v0.1.3/v0.1.2 and the retained human-review rules. It runs one reviewer
role and one session per server. Package membership supplies the primary units,
authorized context units, opaque item IDs, and full second-review scope at runtime.
It does not read the internal opaque-lineage map or Step 8A records.

Interface version 1.1.0 binds primary v1.0.0 unchanged and second v1.1.0: both
contain the same six primary units and 182 blinded items (133 nodes, 49 relations),
with identical opaque IDs, semantic projections, evidence, and zero duplicate groups.
Full independent second review was authorized before any production judgment or
activation file. The historical two-unit, 45-item second package v1.0.0 and its
selector/freeze remain historical artifacts and are not active UI inputs.

The frozen coverage binding is
`data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_scope_freeze_v0.1.4.json`;
the complete successor binding is
`data/curation/papers/m2/publication_step5_evaluation_authority_freeze_v0.1.4.json`.
Reproduce only the new artifacts with:

```bash
python -m src.extraction.llm.publications.step8_full_secondary_review
```

The historical `step8_blinded_adjudication` materializer remains a reproducibility
path for the old 2/6 artifacts; it is not the active full-review materializer.
Both reviewers must complete independent initial judgments before reconciliation.
Preserve their original exports separately. Pre-reconciliation candidate-support
agreement (observed agreement, three-category nominal Cohen's kappa and confusion
counts overall/by node/by relation) follows Step 5 v0.1.4 Section 3; it is not
extraction IAA or a replacement for Human Core reliability. No analysis or
reconciliation is performed by the UI.

## Dry run

Use the repository's Python environment with PyYAML installed, from the repository
root. The default execution mode is `dry-run`:

```bash
python -m src.annotation.publication_step8.app \
  --role primary --session-id interface-check --reviewer-id dry-run-reviewer
```

Open `http://127.0.0.1:8788`. For an independent second-review dry run, use
`--role second`, a distinct reviewer identity, and a different port if both
servers run simultaneously. State is stored under
`var/publication_step8_review/<mode>/<role>/<session-id>.sqlite`.
`--state-root` can select a separate local parent directory. Never distribute a
reviewer's database or activation file to the other reviewer.

The source-orientation page contains the exact complete authorized primary text.
Begin candidate review in Nodes. Nodes and Relations can then be revisited freely;
unit completion remains unavailable until every assigned node and relation judgment
and every duplicate decision is present. Optional controls are labeled **Additional
authorized context** and appear only for authorized context units. Evidence appears
as a complete **Cited-evidence paragraph for evidence occurrence N**, bounded by
the authorized source unit. Evidence is yellow. Literal node labels and relation
endpoint mentions are highlighted only for every exact occurrence wholly inside the
frozen cited-evidence interval; same-string occurrences elsewhere in the paragraph
are never highlighted. No inferred label or relation span is displayed.

Each target displays its frozen `positive_criterion` and `boundary`, derived from
`publication_target_inventory_v0.1.5.yaml`. A deterministic endpoint that is the
current source artifact is displayed to the reviewer only as **Current paper**; the
exact identifier remains in the accepted package and deterministic internal export
binding, not in the endpoint display.

Each selection autosaves before navigation resumes. `Saved ✓` acknowledges the
committed revision. A failure leaves the previous confirmed choice visible and
reports the error; a stale revision requires a reload. Reopen the same command
with the same role, session ID, and reviewer ID to resume decisions and phase.
There is no state-reset endpoint. Completed units are read-only. Notes are not
required or collected. Initial-review exports are available from the session's
export link even when incomplete.

## Explicit production activation

Production review has **not** been started by this implementation. A separate
researcher decision is required to begin it.

After authorization, choose the real reviewer identity, role, and stable session
ID. Print the required activation fields without creating a session:

```bash
python -m src.annotation.publication_step8.app \
  --role primary --session-id CHOSEN_SESSION --reviewer-id CHOSEN_REVIEWER \
  --print-activation-requirements
```

The operator must explicitly approve and save those exact fields to a local
activation JSON file. They bind the reviewer, session, role, accepted blinded
package bytes, source inventory, interface version, and all Python/JS/CSS/HTML
runtime files. Start the approved session with:

```bash
python -m src.annotation.publication_step8.app \
  --role primary --session-id CHOSEN_SESSION --reviewer-id CHOSEN_REVIEWER \
  --mode production --activation-file PATH_TO_APPROVED_LOCAL_ACTIVATION.json
```

Use the corresponding second role/package and separate activation for the second
reviewer. Production activation is verified before any database is created.
The package/runtime change invalidates earlier runtime approvals and session bindings;
use fresh dry-run session IDs for this version. No historical session is migrated.
Before production activation, obtain the researcher execution authorization, choose
the two reviewer identities and role-specific session IDs, and approve the exact
activation requirements from this final runtime separately for each role.
Production access subsequently rechecks package and runtime bindings and the
activation file. A runtime or package change blocks access and resume; it never
silently migrates production state. Preserve existing state and seek an explicit
versioned migration decision if a later implementation change is needed.

Reviewer identity is stored with the session and each revision and cannot change
after the first decision. Every action is revision-checked and appended to the
history. Exports include mode, role, reviewer, session, input package binding,
interface/runtime bindings, opaque IDs, exact controlled decisions, internal
current-paper endpoint bindings, unit/session completion, and revision timestamps.
Export bytes are deterministic for unchanged state. Dry-run exports are explicitly
marked `syntheticDryRun` and cannot resume as production.

Only this session's progress and decisions are served. The server binds to
loopback, serves fixed routes, and requires a session token for POST actions.
This is a local research interface, not a multi-user deployment. No judgments,
reconciliation, positive reference, omission sidecar, model calls, or later
evaluation are created by installing or starting the dry-run interface.

## Focused verification

```bash
PYTHONPATH=. python -m unittest discover -s tests \
  -p 'test_publication_step8_review_ui.py' -v
node --test tests/test_publication_step8_review_ui_client.cjs
```

The HTTP test needs permission to bind an ephemeral localhost port. All test
decisions, including production-boundary fixtures, use synthetic IDs and temporary
directories. Accepted package/source checks are read-only.
