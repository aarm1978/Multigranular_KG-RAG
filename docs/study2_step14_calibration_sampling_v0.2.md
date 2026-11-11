# Step 14 held-out sampling correction v0.2

Sampling authority: `step14-held-out-sampling/0.2.0`. This changes only the held-out
sample, not the [instruction calibration](study2_step14_semantic_calibration_v0.1.md),
identity policy, validator, provider settings or once-only execution.

Exclude development units and exact pairs, and the original unexecuted v1 held-out
units. Select eight cross-family-containing and eight within-family-only units.
Classify actual pairs from their endpoint source families, not unit-level tags.
Seek 24 cross-family pairs in eight cross-containing units (therefore at least six).
If fewer than 24 are available in any eight units, record that limitation; fewer
than eight units in either scope is a preparation blocker.

Predeclared selection, separately within each scope: greedily maximize previously
uncovered density (sparse ≤2, dense ≥10, otherwise medium), source-family combination,
and recorded specificity/instance/generic-name features. Break ties by SHA-256 of
`[sampling-policy, unitID]`. At each choice require that the remaining slots can
still reach the cross-pair target, using the largest available remaining counts.
This feasibility check does not use recommendations or presumed identity. Available
features, achieved coverage, per-unit concentration and exclusions are recorded.
This is a purpose-stratified diagnostic sample, not population gold.

The separate adapter delegates held-out construction, binding audits, matched-arm
checks, validation, reporting and execution to unchanged v1 components. It intercepts
preparation writes to omit development requests entirely. V1 development outcomes
are verified and retained as hashed historical comparison evidence; every v1 file
except its advisory lock is pinned. V1 remains byte-identical. No development live
gate is exposed by this adapter. Historical development is in
`historical-development.json`; new `report.json` covers held-out results, with an
empty development stage. Neither arm is gold; fewer abstentions imply no accuracy claim.

From the repository root, use the existing research interpreter:
`python -m src.evaluation.step14_calibration_sampling prepare` (fresh v2 only),
then `dry-run`, `report`, or separately `run-held-out --execute`.
All commands accept `--root`; default is
`var/study2_step14/semantic-calibration/v2/`. Share `sampling.json`, `sampling.md`,
`historical-development.json`, `report.json`, `comparison.json`, `worksheet.json`.
No original files or original implementation pins are modified.
