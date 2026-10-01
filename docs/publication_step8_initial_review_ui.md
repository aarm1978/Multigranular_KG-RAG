# Publication Step 8 initial review UI

The local interface implements the accepted Step 8B candidate-review packages
under Step 5 v0.1.3/v0.1.2 and the retained human-review rules. It runs one reviewer
role and one session per server. Package membership supplies the primary units,
authorized context units, opaque item IDs, and second-review subset at runtime.
It does not read the internal opaque-lineage map or Step 8A records.

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
Begin candidate review to inspect nodes, then relations. All nodes must receive
an initial judgment before continuing to relations. Optional context controls
appear only for the authorized context units. Evidence appears in complete
intersecting paragraphs, bounded by the authorized source unit. Evidence is
yellow, literal node labels are darker, and literal relation endpoint mentions
have distinct underline colors. No inferred label or relation span is displayed.

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
Production access subsequently rechecks package and runtime bindings and the
activation file. A runtime or package change blocks access and resume; it never
silently migrates production state. Preserve existing state and seek an explicit
versioned migration decision if a later implementation change is needed.

Reviewer identity is stored with the session and each revision and cannot change
after the first decision. Every action is revision-checked and appended to the
history. Exports include mode, role, reviewer, session, input package binding,
interface/runtime bindings, opaque IDs, exact controlled decisions, unit/session
completion, and revision timestamps. Export bytes are deterministic for unchanged
state. Dry-run exports are explicitly marked `syntheticDryRun` and cannot resume
as production.

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
