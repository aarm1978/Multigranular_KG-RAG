# Step 12C — Prospective GitHub provider-input projection v0.1

**Offline implementation; NOT AUTHORIZED FOR LIVE EXECUTION.** Based on checkpoint
`e079c397a63771e9fd5e0eaaaea25388932677b3`. This addendum does not amend the frozen
Step 11 v0.3 contract, ontology v0.1.6, sample selection or semantic prompt.

## Diagnosis and exact size attribution

Rebuilt only GH-06 (CIROH-UA/neuralhydrology) and GH-04 (CIROH-UA/hydrotools) from
pinned local snapshots and the v0.2 selection manifest. Their full semantic request
hashes match the manifest. No corpus-wide screening or provider calls occurred.

The following disjoint attribution totals the accepted semantic serialization
(UTF-8 JSON, ensure_ascii=True, sorted keys, compact separators). Top-level fields
include key, colon and one separator byte. The nested reads row counts its array
value only; the remainder includes its key, completeness flags and the net outer
brace/separator adjustment. This makes totals exact rather than approximate.

| Serialized contribution (bytes) | GH-06 | GH-04 |
|---|---:|---:|
| Selected sourceUnits, including text and provenance | 22,816 | 22,158 |
| sourceDiagnostics | 621,879 | 78,345 |
| sourceCompleteness.reads array | 671,845 | 100,140 |
| authorityMetadata | 2,437 | 1,481 |
| Target profile, instructions, endpoint/assertion inventories and purpose vocabulary | 16,981 | 16,981 |
| Other fields and completeness remainder | 3,680 | 3,675 |
| **Total semantic request bytes** | **1,339,638** | **222,780** |

Within sourceUnits, the serialized text string values alone occupy 4,659 / 5,729
bytes; their original UTF-8 text is 4,596 / 5,673 bytes and characters. These are
subtotals, not additional rows. Diagnostics plus reads account for approximately
96.6% / 80.1% of the complete semantic request. GH-06 has 870 read records and 792
review diagnostics; GH-04 has 148 and 106. Much of the size is repeated repository,
commit, path, hash and decoder metadata attached to unselected passage warnings.

Selected notebook spans were matched to the original zero-based **Markdown** cells
and authority coordinates. Code-cell source and outputs are not selected text or
provider request fields. The full authority metadata is text-free; reader audit
records contain metadata, not notebook code/output payloads. A synthetic notebook
regression additionally checks distinct code/output sentinels are absent from both
full semantic and projected bytes. This does not exclude literal code-like terms
already present in eligible explanatory Markdown or interpret their execution.

## Explicit prospective projection

`src/extraction/llm/coderepos/provider_input.py` implements the opt-in transport version
`github-provider-input/1.0.0`, limited to trusted ready `github-request/1.0.0` records.
No request, response, target-profile or scientific instruction version changes.

`pilot_preflight.build_preflight(request, output_ceiling=32768,
projection_version="github-provider-input/1.0.0")` applies it explicitly. Omission
retains the original envelope path byte-for-byte; unknown versions/families or a
mismatched semantic digest fail closed. The existing three-request writer/terminal
path does not opt in automatically.

All selected units, exact strings, order, authority metadata, hashes, Unicode
coordinates, instructions, response schema, profile, owner, purpose seeds and other
endpoint inventories are unchanged. Only the audit lists are projected:

- Known routine successful-read, excluded-file and duplicate-README records are
  replaced by exact status/reason counts and a hash of the complete original list.
- The known passage-review warning is omitted individually only when path/cell or
  original offsets establish disjointness from every selected unit. Its count and
  original-list hash remain visible. No lines are reinterpreted across cells.
- All technical failures, global/file-wide or potentially overlapping warnings,
  unknown reasons/fields and conflicting explicit unit locators remain in full.
  Completeness booleans remain unchanged, including false for both measured requests.

The projected body explicitly states that only selected units are evidence, full
audit detail remains in the trusted request, and omitted metadata does not establish
semantic no-evidence or acceptance. All measured review warnings are disjoint;
792/106 remain reported as omitted-review counts, not converted to successful reads.
No scientific source text is summarized, rewritten or truncated. No source failure
or selected-unit eligibility gate is relaxed.

The full request, all original diagnostics/read records and original request hash
remain the parser/replay authority. The reduced input is **not** a replacement replay
request. Projection returns exact full semantic bytes and separate exact provider
input bytes/hash; preflight also binds the projection version and exact envelope
bytes/hash. Replay must continue using the full request and original expected hash.

## Measured reduction and preserved artifacts

| Exact bytes | GH-06 before | GH-06 projected | GH-04 before | GH-04 projected |
|---|---:|---:|---:|---:|
| Provider input (ensure_ascii=False) | 1,339,627 | **47,181** | 222,769 | **45,564** |
| Complete provider envelope | 1,481,526 | **70,504** | 262,938 | **68,735** |

The 11-byte difference between full semantic and original provider-input sizes is
existing JSON Unicode escaping, not changed source text. GH-06 input shrinks by
96.5%. These are bytes, not measured tokens, cost or remote API acceptance.

GH-06 full semantic SHA-256 remains
`ef96920cd4df5f846ef77ebe92213592d1ca5c85a9a62a4214fa6acee3313613`;
projected input SHA-256 is
`a46f573d31ef27f2af6348ed605118d63153e14777110f08a30104de7c0c7e74`;
projected envelope SHA-256 is
`5217423bfc918fb988658ba0f84da6c135025b095ae8ec4170312766adcccf1b`.
GH-04 full semantic SHA-256 remains
`751c81fd1b4fc9a73e03de5fe0c241627e247aa1d7678148f7ae54aebc1a2cc2`.

Ignored local artifacts:
`var/study2_step12c/analysis/github-provider-projection-v1/`, containing `sizes.json`
and per-ID full request-result, semantic-request, projected provider-input/envelope
bytes and preflight hash associations. No historical artifacts were overwritten.
All 32 preserved pilot artifact hashes match; default preflight reconstructs the
HS-01/GH-01/HUB-01 envelopes byte-identically. The selection manifest, handoff and
historical plans are unchanged.

## Validation and remaining execution dependencies

**All nine focused tests passed:** five new synthetic projection tests and four
directly affected preflight tests cover exact Unicode/unit retention, conservative warnings/failures, unknown-version
and hash rejection, separate input/envelope hashes, immutable inputs, notebook
code/output exclusion and unchanged parser/replay failure isolation. No broad suites.

No frozen-authority conflict was found: this changes transport audit verbosity,
not evidence scope or semantic rules. Before live use, separately implement the
already planned manifest-aware terminal ID/approval routing, explicitly reconstruct
this projection version during envelope verification, and approve its new input/
envelope hashes plus token/cost bounds. The current legacy terminal verifier does
not silently accept projected envelopes. The 30-request selection remains fixed;
this addendum resolves its metadata-size issue prospectively, not its live approval,
semantic uncertainty or Step 12C closure.
