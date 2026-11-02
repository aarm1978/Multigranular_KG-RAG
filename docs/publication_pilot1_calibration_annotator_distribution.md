# Publication Pilot 1 calibration: local annotator instructions

This private macOS package runs the accepted Annotation/Calibration interface entirely on
your computer. It does not use a central server, telemetry, an LLM, web search, or another
annotator's state. Follow the accepted Annotation/Calibration Handbook linked in the app
for semantic and evidence decisions; this document only covers local operation.

## Before starting

Keep this package and its exports private. Do not inspect, exchange, or compare annotations,
timing, positive counts, or answers with the second annotator before calibration completion.

The launcher requires macOS, Python 3.10 or newer, PyYAML, and `jsonschema`. It checks an
explicit `PUBLICATION_PILOT1_PYTHON` override first, then every `python3`/`python` on PATH,
then a bounded set of common macOS locations, and uses the first fully compatible candidate
for package verification, the app, readiness checks, and exports. It never installs or
changes Python, Conda, or global packages. If its prerequisite check fails, stop and send
the displayed message to the researcher. Do not substitute a different package or activation.

## Start or restart

1. Unzip the package into a private local folder. Do not rename or edit files inside it.
2. Double-click `launch_annotation.command`. If macOS requires confirmation, Control-click it,
   choose **Open**, and confirm once.
3. The launcher validates the package, accepted hashes, assigned annotator identity, and
   activation before it starts the local server or opens the browser.
4. Leave the Terminal window open while annotating. To restart later, close the prior server
   with Control-C if necessary and run `launch_annotation.command` again. Your local SQLite
   working state is retained under `var/publication_pilot1_annotation/calibration/production/`.

The application autosaves validated work locally. A submitted unit is immutable. If a
submitted unit must be revised, use the explicit reopen action and provide a reason; the old
submission and revision history remain preserved.

## Timing and interruptions

Use **Pause** whenever you stop annotation for a personal break or unrelated work, then use
**Resume** before continuing. Use **Technical interruption** for application, computer, or
source-display problems and end the interruption after the problem is resolved. Do not use
ordinary wall-clock time as an annotation-time substitute.

Complete the reading, node, relation, and review passes in order. Submit only after final
review and after every routed target has an actual completion state.

## Back up or return results

- Double-click `export_backup.command` for an immutable partial recovery bundle. It is marked
  `partial / non_gate0_ready` and may be created before all 16 units are submitted.
- After all 16 units are validly submitted, double-click `export_final.command`. Final export
  fails closed if activation, identity, hashes, submissions, timing, or assignment completeness
  is invalid.

Both commands write a ZIP under `exports/`. Return the resulting final ZIP file—not the SQLite
database, unpacked JSON files, or package folder—to the researcher through the agreed private
transfer method. Keep your package until the researcher confirms that its checksum and content
were validated and imported.
