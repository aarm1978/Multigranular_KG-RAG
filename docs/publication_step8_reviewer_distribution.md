# Step 8 reviewer distribution

The tracked builder `src.annotation.publication_step8.distribution` creates two
private, checkpoint-bound macOS reviewer ZIPs after Step 8 production authorization.
It creates no review state, judgment, reconciliation, or provider call. The ZIPs go to
the ignored `var/publication_step8_distribution/` directory; their exact paths and
SHA-256 values are bound by the tracked
`data/curation/papers/m2/publication_step8_review_distribution_manifest_v1.0.0.json`.

Build only from a clean checkout:

```bash
python -m src.annotation.publication_step8.distribution
```

The builder packages role-specific accepted inputs, activation, reviewer-visible source
text/context, the accepted UI runtime, and a bundled pure-Python PyYAML 6.0 runtime. It
does not include the other role package, private opaque-lineage map, SQLite state, or
exports. `reviewer_1` is bound to `primary` and
`step8-production-reviewer-1-v1`; `reviewer_2` is bound to `second` and
`step8-production-reviewer-2-v1`.

Reviewers need a local Python 3.10 or newer. The launchers find it from
`STEP8_REVIEW_PYTHON`, standard `python3`/`python`, or common macOS locations; PyYAML
is bundled and no package installation, Git checkout, role/session argument, or
activation edit is required. A missing compatible Python stops with a clear message
and does not create state.

Each ZIP contains `START_REVIEW.command`, `EXPORT_BACKUP.command`,
`EXPORT_FINAL.command`, `README_REVIEWER.md`, an exact role activation, immutable
review runtime/input files, and a package checksum manifest. State remains under
the unzipped package's `state/` directory. The app binds only loopback and opens the
local browser. Backup export is explicitly non-final. Final export fails closed until
all 182 assigned judgments are complete. Reviewers return only the final JSON export.
