# Publication Pilot 1 calibration distribution pipeline

This operational layer packages the accepted local Annotation/Calibration application for
one assigned macOS annotator, exports immutable JSON/JSONL exchange bundles, and validates
those bundles into a researcher-side SQLite index. Annotator SQLite databases are working
state only and are never exchanged or merged. The module does not calculate Gate 0, IAA, or
adjudication.

All real generated activations, packages, exports, and master databases belong under the
ignored `var/publication_pilot1_annotation/` runtime tree or external private storage. Never
place them in tracked data. The commands below show placeholders only; this checkpoint must
not be used to create the real A/B packages until independent acceptance.

## Researcher commands

Run from the accepted repository root with the dependencies in
`src/annotation/publication_pilot1/requirements.txt` available.

```text
python -m src.annotation.publication_pilot1.calibration.distribution create-activation \
  --annotator-id <assigned-id> --annotation-session-id <assigned-session-id> \
  --output var/publication_pilot1_annotation/distribution/<assigned-id>/activation.json

python -m src.annotation.publication_pilot1.calibration.distribution build-package \
  --annotator-id <assigned-id> --annotation-session-id <assigned-session-id> \
  --output var/publication_pilot1_annotation/distribution/<assigned-id>.zip
```

Package creation preserves two distinct checkpoints: `annotationMVPBaseCheckpoint` is the
historical accepted Annotation/Calibration MVP base
`a67c5f3d70a3f4a71f79561646572781eeae89b4`, while `packageBuildCheckpoint` is read dynamically
from the actual clean Git `HEAD` containing the distribution implementation. The builder
requires the accepted base to be an ancestor of that HEAD and rejects any tracked or untracked
worktree change. It also binds interface/schema/routing versions, calibration identity/order,
Gate-0 policy hash, frozen input hashes, and the one assigned annotator/session identity. It copies only local runtime code, frozen contracts/inputs,
canonical source files, the private activation, and the annotator guide. It does not create a
session database or open a calibration unit. The generated `.command` launchers validate the
unpacked package before the application can start.

The provenance dependency order is deliberately acyclic: validate clean Git and capture HEAD;
write an activation containing both checkpoints; hash that activation and all package payload
files into `package_manifest.json`; then create the ZIP. The manifest is not included in its own
file-hash map. After extraction, verification needs no `.git` directory: it checks payload file
hashes, requires manifest and activation to agree on `packageBuildCheckpoint`, and revalidates
the activation against the frozen inputs in the package.

Validate a returned final bundle and import two independent bundles with:

```text
python -m src.annotation.publication_pilot1.calibration.distribution validate-bundle <bundle.zip>

python -m src.annotation.publication_pilot1.calibration.distribution import-bundles \
  <annotator-a.zip> <annotator-b.zip> \
  --master-database var/publication_pilot1_annotation/researcher/calibration_master.sqlite3
```

Use `validate-bundle --allow-partial` only for a recovery bundle. Partial bundles remain
`partial / non_gate0_ready` and the default importer rejects them.

## Exchange and provenance

Every bundle has the exact closed file set `activation.json`, `manifest.json`,
`annotations.jsonl`, `timing_events.jsonl`, `context_exposures.jsonl`,
`revision_audit.json`, and `checksums.json`. ZIP metadata and record serialization are
deterministic. Re-exporting unchanged state produces identical bytes. A different bundle may
not overwrite an existing path.

Validation checks checksums before parsing, then both checkpoint bindings,
activation/version/hash bindings, exact
calibration membership, annotation schema, canonical unit/document/evidence reconstruction,
submitted revision snapshots, timing sequences, and context exposure snapshots. Two-bundle
import additionally requires distinct annotator and session identities and identical
assignment order. It stores each source bundle SHA-256, source path, activation, manifest,
revision audit, annotation records, timing events, context exposures, import timestamp, and
validation result without modifying the source ZIP. The immutable ZIP remains authoritative;
the SQLite master is a derived index.
