# Step 13: MDX lexical correction and v3 shadow interpretation

This implements the researcher's targeted parser correction. It does not amend the construction-acceptance policy, ontology, source-selection rules, prompts, identity algorithm, or evidence requirements. Step 13 scientific completion is not established.

## Demonstrated defect and bounded authentic evidence

The historical `source_local_hub_evidence.py` scanner pushes non-self-closing HTML void elements onto its open-container stack. An ensuing valid closing tag can then mismatch the stack and mark earlier content uncertain; an unclosed void scope marks later prose uncertain through end of source.

Two authenticated complete source inputs reproduce this with original evidence:

| Owner | Source text SHA-256 | Candidate | Original character offset |
|---|---|---|---:|
| `hub:page:103555bceed0fdd50c00` (FIMserv) | `dfa13ce7866d2a623d43f8c6b47e0ae0a0eaabf0f1f2907791ac5b7d120586a8` | `variable-streamflow` | 2170 |
| `hub:page:a43e995a4834e75d17db` (FIMbox) | `1cbe5996f2beb8eca4edaf64ca9ff33e61a24ebabff54e1f708cc68aae0ca11c` | `variable-streamflow` | 1904 |

In FIMserv, a non-self-closing image starts at offset 1368 inside a correctly closed link, and an opaque horizontal rule starts at offset 1995 before the quoted prose. FIMbox has the corresponding non-self-closing image at offset 1425. These elements cannot contain the later scientific prose; their tags remain opaque in v3.

The first quotation starts “It is a terrain-based fluvial flooding model”; the second is “driven by National Water Model retrospective and forecasted streamflow.” Tests load exact quotes from authentic v2 records, verify queue/bundle/source hashes, check the original offsets, and replay all three groups of each owner. No source excerpt is rewritten or substituted into a request.

The two bounded owner replays yield respectively 30 nodes/25 edges and 21 nodes/13 edges after native exact owner consolidation. These are rule-induced changes in two selected cases, not corpus recovery or accuracy estimates. A separate mixed accepted/held authentic group tests preservation of previously accepted records.

## Narrow correction and immutable authority

`source_local_hub_evidence_v044.py` is an isolated opt-in implementation overlay. Its scanner is the historical scanner with one structural correction: a recognized lowercase HTML void element with lexically complete static attribute syntax does not open a child-content scope. The tag itself remains opaque under the unchanged tag/attribute admissibility rules. Unknown JSX, expressions, code, examples, unsafe containers and malformed attributes retain conservative handling. Genuine mismatched tags retain the original fail-closed behavior; no general “ignore malformed markup” recovery is introduced. Other suspected defects require separate demonstrated evidence.

The original classifier and all frozen production implementation pins remain unchanged. The exact binder and validators are reused. `admissibilityVersion=hub-full-authority-admissibility/0.4.1` continues to identify the unchanged binding/admissibility contract, including its Parameter explanatory-prose gate. New bindings additionally record `lexicalClassifierVersion=hub-lexical-classifier/0.4.4`; the derived-run manifest pins the overlay implementation bytes. This separates the parser implementation from the substantive acceptance contract.

Previously held nodes may acquire different computed source-local identifiers when their empty bound-evidence anchors become actual exact source offsets. This follows the existing deterministic identity algorithm. Authentic candidateIDs and source evidence are unchanged; the comparison records both identifiers. Previously accepted records and endpoints must remain unchanged, apart from explicitly identified lexical-version and derived replay-hash provenance.

## v3 replay and comparison

Run from the repository root using the research environment:

```bash
python -m src.evaluation.source_local_supplemental_review_v3
```

The runner blocks socket connections and refuses an existing output directory. It first invokes the existing historical queue/code-pin verifier, verifies v2 corrected implementation hashes, replays the native journal read-only, verifies receipts and the supplemental recovery, and requires exactly the same 1,005 complete selected provider responses. It then re-executes schema validation, semantic replay, evidence binding, normal construction acceptance and owner consolidation under the lexical overlay. It never uses saved v2 decisions as v3 admission inputs.

The v2 reports serve only as a comparison baseline. Exact authored candidate fields, request context, authentic response bytes, abstentions, original deferred records, six quarantined abstentions and accounting must be preserved. Newly generated exact deferred-evidence associations are permitted only for candidates with changed lexical bindings; existing associations cannot disappear. Parent paths and dependency gates run normally.

Any loss or substantive change to a previously accepted record stops the run. Non-Hub validation views must be identical. Every changed decision must trace to changed lexical bindings, directly or through explicit dependencies. Recovery categories are exclusive: a candidate whose own binding changed is independent (even if it also depends on another recovery); otherwise it is downstream. Counts across targets/groups are not deduplicated owner counts.

Outputs under ignored `var/study2_step13/source-local-supplemental-review/v3/`:

- `groups/`, `owners/`: new native reports, kept separate from v2 and production.
- `selection-manifest.json`: historical selection, baseline hashes and overlay hashes.
- `quarantined-abstentions.json`: unchanged six records, never counted as valid no-evidence outcomes.
- `summary.json`: v3 counts and unchanged separate Batch/live accounting.
- `comparison.json`: all changed decisions/causes/identity transitions, group and owner counts, recovery strata, cohort/zero-yield gains, remaining held roots and candidate-bearing zero-yield owners.
- `comparison.md`: compact before/after summary without precision/recall/F1 claims.

A stopped run may leave partial group/owner files; absence of the final comparison/summary means it is not a completed review. Do not delete or overwrite it automatically. Inspect the stop before authorizing another derived output version.

## Limitations

No corpus replay is performed in Codex. Corpus-wide recovery totals, accepted-record regressions, all-six quarantine equality, remaining holds and zero-yield changes remain pending the full researcher-terminal run. No newly accepted assertion is independently scientifically adjudicated. Dynamic content, mixed example/prose evidence, endpoint identity and genuine parent-path insufficiency remain governed by their existing constraints. No provider calls, KG construction, or Step 14 alignment are authorized by this correction.
