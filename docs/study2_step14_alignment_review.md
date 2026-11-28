# Step 14 alignment review instrument

The researcher pilot tests usability and workload. Its judgments stay outside alignment decisions and confirmatory evaluation. Pilot v2 uses the verified `deduplicated-alignment/v1` automatic frames. They contain 1,629 identity groups with 7,966 retained source-local representatives, and 221 directed relations. The 29 historical approvals are excluded from automatic identity evaluation. Pilot v1 and its local session remain at `researcher-pilot-v1/`.

## Run the portable pilot

From the repository root, use the prepared local package:

```bash
P=var/study2_step14/alignment-evaluation/researcher-pilot-v2
python "$P/reviewer/app.py" serve --port 8794
```

Open `http://127.0.0.1:8794` and choose **Start review**. **Pause** saves the current case. After stopping the server, the same command and **Resume review** restore the cursor, judgments and comments. **Previous** permits corrections. **Save & Next** also works for unanswered cases. On the last case, **Save & finish** saves and pauses even if some cases remain unanswered.

**Export results** downloads a JSON snapshot. To export from the terminal, including after closing the server:

```bash
P=var/study2_step14/alignment-evaluation/researcher-pilot-v2
python "$P/reviewer/app.py" export --output "$P/pilot-results.json"
```

Choose a fresh export filename for each snapshot. The export contains every neutral case alias, current judgment, optional comment and problematic occurrences, correction history, cursor, session transitions, per-case visits and revisits, elapsed and active seconds, and totals. The custodian joins the export to the private crosswalk by package digest and case alias.

## Data preparation and distribution

To reproduce the package under a fresh ignored directory, run:

```bash
python -m src.annotation.alignment_review.projected \
  --evaluator researcher \
  --output var/study2_step14/alignment-evaluation/researcher-pilot-v2-replay
```

Distribute only a fresh `reviewer/` folder. It runs with standard-library Python 3.9+ independently of the repository or corpus. Use a separate package and evaluator identifier for each person. Keep `private/mapping.json`, the SQLite session and exported judgments local. To prepare a different explicitly selected exploratory set, pass `--selection FILE` with private JSON arrays `identity` (frame group keys) and `relations` (ordered subject, predicate, object keys). The preparer never draws a probability sample.

The default resolves each v1 private case key against the revised dispositions. It reuses C02–C06. The original C01 became a singleton. Its replacement preserves the within-artifact, two-member task. C07 exercises a changed directed relation whose two original citation witnesses both differ from their retained representatives. Pilot timings and judgments have no population-level interpretation.

| Case | Hypothesis | Original extraction members → representatives | Original excerpt references → distinct excerpts | Original surrounding windows → distinct windows |
|---|---|---:|---:|---:|
| C01 | Within-artifact identity, replacement | 4 → 2 | 4 → 2 | 4 → 2 |
| C02 | CuPy, same-family cross-artifact | 5 → 5 | 5 → 5 | 5 → 5 |
| C03 | NextGen framework, cross-family | 150 → 122 | 180 → 131 | 167 → 118 |
| C04 | hasComponent | 2 → 2 | 2 → 2 | 2 → 2 |
| C05 | isVariantOf | 2 → 2 | 2 → 2 | 2 → 2 |
| C06 | isVersionOf | 2 → 2 | 5 → 5 | 5 → 5 |
| C07 | hasComponent, reprojected endpoints | 2 → 2 | 2 → 1 | 2 → 1 |

Relation member counts describe displayed witnesses. In C07 the subject and object each have an original citation at the same excerpt. Both directional bindings remain available.

## Evidence and review behavior

The public view presents each retained representative once. The private crosswalk joins each representative and each displayed evidence row to its original extraction records, evidence pointers, hashes and frame membership or directed citation bundle. The preparer checks both sides of each original citation bundle through the duplicate mapping and current membership ledger. Original witness records supply the quotations even when their retained representatives have different source-record IDs.

Exact surrounding windows are indexed across the whole case. Each distinct window has one expandable display, with links from other uses. Individual source locations and offsets remain attached to each mention. Cases with different document coordinates or different surrounding text preserve those differences.

Case, artifact, occurrence and quote aliases apply locally. The identity heading uses a frequent member label. Every member keeps its own original labels, class, available version and granularity, artifact and evidence references. One exact source text has one displayed quote per case. Repeated references link back to that quote and keep their own locations. Distinct text, including differences in whitespace, stays separate. Optional surrounding text uses exact offsets in hash-matched publication units or Hub source text. Original artifact links and recorded file, section or line locations provide further context where available. Missing spans are visible.

Directed relation cases retain the frozen subject and object witness sets, applicable ontology v0.1.9 signature, original full excerpts and the exact cited slices. Case preparation checks the source-record hash, evidence-record hash, full-quote hash and offsets. Reviewers judge the predicate and direction. They see the relevant witnesses without having to assess the full endpoint groups. Model reasoning, confidence, previous decisions, routes and private identifiers are outside the reviewer data.

A reviewer can record a counterexample immediately. For identity **Supported**, reaching the end of the evidence enables a single whole-group attestation. Scrolling measures presentation only. The reviewer decides whether every member supports the hypothesis. Each single-choice change and optional comment autosaves. A case-bound browser draft protects the short debounce interval; the SQLite record survives restarts. Use one active tab per package. Revision checks prevent stale tabs from overwriting newer commits.

Timing uses five-second heartbeats and saved actions. Elapsed seconds cover observed intervals while a case is open. Active seconds approximate focused, visible time within 60 seconds of interaction. Quiet reading can exceed that threshold. Inactive seconds are the measured difference. Explicit pauses and heartbeat gaps longer than 20 seconds receive no time credit. Interruption can lose the unobserved tail of a visit. Browser focus on an external source also falls outside active instrument time.
