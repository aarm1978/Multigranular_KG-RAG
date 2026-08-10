# Publication Pilot 1 Source-Unit Builder Implementation

> **Implementation status:** source-unit builder component version 0.1.4 and fifth twelve-artifact materialization independently accepted
> **Builder version:** 0.1.4
> **Binding source-unit contract:** 0.1.1
> **Contract SHA-256:** `31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a`
> **Fifth materialization:** 2026-08-10

## Implementation boundary and history

The offline builder reads the explicit Phase A Markdown paths, applies the frozen
normalization, creates exact section/block/unit partitions, validates source slices and
hashes, and atomically writes the inventory and manifest. It does not use a network or
LLM, alter upstream artifacts, perform screening or selection, assign partitions, or
create annotations, gold, requests, predictions, or evaluation results.

The implementation sequence is:

1. 0.1.0 — initial materialization;
2. 0.1.1 — first correction and rematerialization;
3. 0.1.2 — page-anchor, table, validation, and authority correction plus third
   materialization; and
4. 0.1.3 — reference-conflict detection and residual page-anchor predicate correction plus
   fourth materialization; and
5. 0.1.4 — contract-conformance correction for the ambiguous reference boundary plus
   fifth materialization.

The canonical outputs remain under `data/curation/papers/pilot1/`.

## Fifth materialization command

```bash
python src/extraction/llm/publications/build_publication_source_units.py \
  --phase-a-corpus data/interim/papers/ciroh_publication_corpus.json \
  --artifact-ids 10 15 16 18 34 37 46 54 79 276 87 87-corrigendum \
  --output-inventory data/curation/papers/pilot1/publication_pilot1_source_unit_inventory.jsonl \
  --output-manifest data/curation/papers/pilot1/publication_pilot1_source_unit_manifest.json \
  --phase-b-artifact data/interim/papers/publication_nodes_edges.json \
  --generation-timestamp 2026-08-10T22:36:09Z
```

The defaults resolve the fixed Phase A corpus, Phase B artifact, twelve artifact IDs, and
both canonical output paths. The same timestamp was reused for the controlled rerun.

## Second-to-third comparison

| Measure | Second, builder 0.1.1 | Third, builder 0.1.2 |
|---|---:|---:|
| Artifacts | 12 | 12 |
| Sections | 330 | 330 |
| Source units | 358 | 358 |
| Eligible | 261 | 269 |
| Context only | 55 | 50 |
| Excluded | 42 | 39 |
| Needs review | 0 | 0 |
| Image-containing units | 88 | 88 |
| Pure visual-only units | 8 | 8 |
| Mixed textual/visual units | 80 | 80 |
| Well-formed table units | 23 | 23 |
| Partially recoverable table units | 0 | 3 |
| Broken table units | 3 | 0 |
| Equation-containing units | 30 | 30 |
| Maximum unit characters | 17,850 | 17,850 |
| Units above preferred maximum | 6 | 6 |
| Inventory SHA-256 | `540de3353f3b4ede80a38cff7f363f668fe8d209a0b386179977c576805ad90d` | `d3217ad14111c998965f89391523a5a3482cfbda42bf3f095c5eb07bf449e0fe` |
| Manifest SHA-256 | `1aa82c24fc2baaae29f49968f065187fb5a3996b43254164d2cff3a7c17dd3de` | `063c82cb2d83546811eb39ef70db61edc6e8ef0fdc68027e9eda84f9741de421` |
| Configuration SHA-256 | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` |

## Reference-scope correction and third-to-fourth comparison

The third inventory reproduced a false structural reset in Publication 34. Section 0030
was the normalized `references` heading. A level-1 conversion-generated running header
then opened section 0031 as `other`. Its three units were respectively `context_only`,
`eligible`, and `eligible`; the latter two were request eligible and contained 10,489 and
2,856 bibliography characters.

Frozen Phase A provides the conservative resolution. After the false heading, it records
38 reference-DOI occurrences on 35 unique line spans from source lines 569 through 615.
Every occurrence retains the authoritative section label `**References**`. Those
occurrences bracket the first and last Markdown list-item lines in section 0031.

Version 0.1.3's conflict detector applied only while reference scope was active and a same/higher-level
heading would structurally reset it. An explicit Appendix, Supplementary Material, or
Supporting Information heading always resets. Otherwise, continuation requires locally
frozen Phase A reference-labeled occurrence ranges inside the candidate section to reach
both its first and last Markdown list-item lines. Without that exact bracketing evidence,
an ordinary same/higher-level scientific heading resets as before. No paper ID, venue
title, journal dictionary, external lookup, or text rewriting is used. Although 0.1.3
detected the correct real-corpus conflict, it assigned the wrong contractual consequence:
it extended the `references` role across the frozen same/higher-level structural reset by
using `phase_a_reference_continuation`. That fourth-state behavior was nonconforming and is
preserved here only as implementation history, not as the final rule.

The residual page predicate was also narrowed: only supported Marker page tokens matched
by the existing page-anchor grammar receive metadata treatment. An arbitrary HTML
`<span id="...">` now follows normal HTML parsing and is not page metadata merely because
it has an ID. Existing supported page-anchor splitting and the zero substantive-suffix
materialization invariant remain unchanged.

| Measure | Third, builder 0.1.2 | Fourth, builder 0.1.3 |
|---|---:|---:|
| Artifacts | 12 | 12 |
| Sections | 330 | 330 |
| Source units | 358 | 358 |
| Eligible | 269 | 267 |
| Context only | 50 | 49 |
| Excluded | 39 | 42 |
| Needs review | 0 | 0 |
| Reference-role units | 31 | 34 |
| Request-eligible units | 269 | 267 |
| Inventory SHA-256 | `d3217ad14111c998965f89391523a5a3482cfbda42bf3f095c5eb07bf449e0fe` | `78ff583f680e88b34fae810646dcb15e929c9a4ec453721aafd4691c7df38fc8` |
| Manifest SHA-256 | `063c82cb2d83546811eb39ef70db61edc6e8ef0fdc68027e9eda84f9741de421` | `14f126bccfddfd75f4677275cb19152ba3668287b7f19a0b1264c94a7c2e361e` |
| Configuration SHA-256 | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` |

Exactly three records changed:

| Source unit | Old role/rule | New role/rule | Old eligibility/reasons/request | New eligibility/reasons/request | Unchanged structure |
|---|---|---|---|---|---|
| `pub:34:sec:0031:unit:0001` | other / normalized_heading_default | references / phase_a_reference_continuation | context_only / structural_or_metadata_only / false | excluded / reference_section / false | `[103648,103680)`, heading, 1 block |
| `pub:34:sec:0031:unit:0002` | other / normalized_heading_default | references / phase_a_reference_continuation | eligible / none / true | excluded / reference_section / false | `[103680,114169)`, list, 1 block |
| `pub:34:sec:0031:unit:0003` | other / normalized_heading_default | references / phase_a_reference_continuation | eligible / none / true | excluded / reference_section / false | `[114169,117025)`, list+prose, 3 blocks |

No source-unit ID, offset, boundary, content type, atomic-block count, unit text, text hash,
input hash, block classification, table quality, or review state changed.

## Contract-conformance correction and fourth-to-fifth comparison

Version 0.1.4 preserves the same deterministic Phase A bracketing logic but renames and
uses it only as `_phase_a_reference_boundary_conflict`. The structural reference reset now
always occurs first. Normal heading classification then assigns section 0031 to `other`
with `normalized_heading_default`. The separate Phase A contradiction marks the internal
section boundary ambiguous and propagates to every unit as:

```text
eligibility: needs_review
exclusionReasons: [ambiguous_reference_section_boundary]
requestEligible: false
reviewRequired: true
reviewReasons: [ambiguous_reference_section_boundary]
validationResults: {valid: true, errorCodes: []}
```

This preserves the frozen structural rule and the distinction between structural validity
and review state. Phase A does not determine the section role. Appendix, Supplementary
Material, Supporting Information, and same/higher-level scientific headings without the
bracketing contradiction remain normal, non-ambiguous resets. No frozen authority changed.

| Measure | Fourth, builder 0.1.3 | Fifth, builder 0.1.4 |
|---|---:|---:|
| Artifacts | 12 | 12 |
| Sections | 330 | 330 |
| Source units | 358 | 358 |
| Eligible | 267 | 267 |
| Context only | 49 | 49 |
| Excluded | 42 | 39 |
| Needs review | 0 | 3 |
| Reference-role units | 34 | 31 |
| Request-eligible units | 267 | 267 |
| Inventory SHA-256 | `78ff583f680e88b34fae810646dcb15e929c9a4ec453721aafd4691c7df38fc8` | `7a3a4941e6c07deee96b19c7619e0b9c5000ad6fadf5bf17379e37229562b07e` |
| Manifest SHA-256 | `14f126bccfddfd75f4677275cb19152ba3668287b7f19a0b1264c94a7c2e361e` | `42684d340af99440d5f72129a5c5299edcb237d77ce2b3d36456b049bee83823` |
| Configuration SHA-256 | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` | `0a0fff14241fd2afa7b59a7b1061d542bde246d8f4985e12abe0db9d83f8a541` |

Exactly three records changed:

| Source unit | Fourth role/rule/status | Fifth role/rule/status | Unchanged offsets/textHash/inputHash | Reason |
|---|---|---|---|---|
| `pub:34:sec:0031:unit:0001` | references / phase_a_reference_continuation / excluded / reference_section / non-review / non-requestable | other / normalized_heading_default / needs_review / ambiguous_reference_section_boundary / review / non-requestable | `[103648,103680)` / `973cc76a0b7aeaad739c751f3f494fad9dd675bcd8cb15c8aa07c6c01c7cf104` / `87cab9c78de584d72e7b96f4afbae3712679f252beeaca66a64fde7607735633` | Frozen reset plus contradictory Phase A provenance |
| `pub:34:sec:0031:unit:0002` | references / phase_a_reference_continuation / excluded / reference_section / non-review / non-requestable | other / normalized_heading_default / needs_review / ambiguous_reference_section_boundary / review / non-requestable | `[103680,114169)` / `e727a9e5f53a7b12491eb38d0dd943abb6c6714d230af4499851e381ba6904ed` / `d69a43ddc74acde36911dc773a2ac8086bc3129ebb14b483bb5c7fe5976c8c2f` | Frozen reset plus contradictory Phase A provenance |
| `pub:34:sec:0031:unit:0003` | references / phase_a_reference_continuation / excluded / reference_section / non-review / non-requestable | other / normalized_heading_default / needs_review / ambiguous_reference_section_boundary / review / non-requestable | `[114169,117025)` / `a28ecec95678cf9a0fdf7c7eafa9dc728419df0e474979742a805a59949a071d` / `1f7ba284c1ac6f0db646e9c6c0982454e8c211d719c213a62c1cd900f902e00f` | Frozen reset plus contradictory Phase A provenance |

All three fifth records have `exclusionReasons` and `reviewReasons` exactly
`[ambiguous_reference_section_boundary]`. No source-unit ID, section ID, offset, boundary,
text, content type, atomic-block count, block classification, table quality, text hash, or
input hash changed.

## Page-anchor audit and correction

The independently recomputed second-state audit found 739 page-marker occurrences. Of
166 metadata blocks containing a marker, 119—not the approximate review count of 122—contained
non-whitespace after exact supported-marker removal. The independent recount operates on
the second JSONL's emitted block boundaries, where adjacent marker and blank lines may be
grouped, rather than estimating from physical lines. Exactly 77 blocks contained
substantive text after page-anchor and image-markup removal: 54,635 stripped characters
across 52 units and artifacts 10, 15, 16, 18, 34, 37, 46, 87, 87-corrigendum, and 276.
Thirty-five self-contained caption lines across 24 units were among the swallowed
substantive blocks.

Version 0.1.2 assigns leading whitespace and each consecutive supported Marker page-anchor
prefix to metadata. The first character after that prefix begins a separately classified
block; an anchor-only line's newline remains metadata. It recognizes only leading
Marker-style page spans and page comments. It does not rewrite text, infer page geometry,
or populate `pageRefs`. The third inventory has 200 metadata blocks containing page
markers and zero with non-whitespace residual after marker removal. All 54,635 substantive
characters are again available to normal block classification, including all 35 captions.

The five previously context-only scientific units are now eligible and contain
evidence-eligible prose:

- `pub:16:sec:0004:unit:0002`
- `pub:16:sec:0031:unit:0001`
- `pub:16:sec:0032:unit:0001`
- `pub:37:sec:0008:unit:0001`
- `pub:37:sec:0010:unit:0001`

## Table audit and correction

The three reviewed tables have equal header/separator/data cell counts, an empty trailing
header and every trailing data cell, valid preceding alignment cells, and only a one- or
two-dash final padding separator. They are now narrowly `partially_recoverable`. Their
table blocks remain non-evidence-eligible and `needs_review`, while independent prose in
the same units keeps each whole unit eligible and request eligible:

- `pub:18:sec:0014:unit:0001`
- `pub:54:sec:0033:unit:0001`
- `pub:87:sec:0008:unit:0001`

No table text was changed. Meaningful malformed separator columns remain broken. Pure
broken-table fixtures are excluded; pure partially recoverable table fixtures require
review; prose-plus-broken and prose-plus-partial fixtures preserve the independent prose.

## Required fields, stable codes, and authority safety

`REQUIRED_SOURCE_UNIT_FIELDS` is the canonical implementation set covering the complete
contract record and compatibility review fields. `validate_document_units` performs a
deterministic shape check before invariant checks and reports sorted missing field names.
Shape failures are deliberately outside the stable validation vocabulary. Emitted records
must contain the required set but may add contract-compatible implementation metadata.

The frozen `STABLE_ERROR_CODES` vocabulary contains exactly 26 codes. Tests assert its
length and exact membership and exercise every code. No missing-field code was added.

Production builds centrally require the source-unit contract, target inventory, ontology
OWL, and Phase B artifact. Missing files, hash mismatches, and Phase B version mismatches
raise `BLOCKED_BY_FROZEN_AUTHORITY_DRIFT` with the path and reason. The CLI always uses
strict verification and exposes no bypass. Synthetic tests alone may call the internal
build API with `verify_frozen_authorities=False`; such manifests do not claim unverified
authority hashes. Production manifest provenance is derived from bytes read and verified
during that run.

## Exact changed-record and span audit

Seventy-five JSONL records changed. The list below identifies 72 additional page-anchor
rows; the three reviewed table rows complete the exact set. Two reviewed table rows
(`pub:18:sec:0014:unit:0001` and `pub:87:sec:0008:unit:0001`) also contain corrected page
anchors, so 74 rows are page-anchor-affected and the two categories overlap:

```text
10: 0008/0001, 0008/0002, 0010/0001, 0012/0001, 0013/0001, 0017/0001, 0022/0001, 0025/0001
15: 0004/0001, 0010/0001, 0010/0002, 0011/0001, 0013/0001, 0014/0001, 0015/0001
16: 0004/0001, 0004/0002, 0010/0001, 0013/0001, 0014/0001, 0016/0001, 0019/0001, 0020/0001, 0021/0001, 0023/0001, 0025/0001, 0027/0001, 0030/0001, 0031/0001, 0032/0001, 0037/0005
18: 0007/0001, 0009/0001, 0016/0001, 0018/0001, 0020/0001, 0021/0001, 0026/0001, 0030/0003
34: 0007/0001, 0012/0001, 0013/0001, 0014/0001, 0018/0001, 0021/0001, 0022/0001, 0023/0001, 0023/0002, 0026/0001
37: 0006/0001, 0008/0001, 0009/0001, 0010/0001, 0011/0001, 0012/0001, 0014/0001, 0015/0001, 0017/0001
46: 0013/0001, 0015/0001, 0017/0001, 0023/0001
87: 0001/0001, 0011/0001, 0014/0001, 0015/0001, 0016/0001
87-corrigendum: 0010/0001
276: 0013/0001, 0015/0001, 0017/0001, 0020/0001
```

Entries use `section-ordinal/unit-ordinal`. Eight units changed whole-unit status: the five
scientific units above changed from `context_only` to `eligible`, and the three reviewed
tables changed from `excluded/broken` to `eligible/partially_recoverable`.

No source-unit ID was added, removed, or renamed. Two spans in paper 16 section 0004 were
remapped at the preferred-size boundary: unit 0001 changed from `[6313,11446)` to
`[6313,15805)`, and unit 0002 changed from `[11446,22206)` to `[15805,22206)`. Thus the
exact source range `[11446,15805)` moved from unit 0002 to unit 0001; the section still has
a complete gap-free partition. All other unit spans are unchanged.

## Protected hashes and deterministic rerun

The following protected bytes were verified before and after the work:

| Authority | SHA-256 |
|---|---|
| Ontology OWL | `ecfcd7058b3404dd1a02875654cc8c7f905e20bdf2e559b4498aa2e7d0f12a57` |
| Target inventory | `3d8a80c4ff8794588e2551e63a61e72c60a9afcb89d8b7a7058ff23e25ee4760` |
| Source-unit contract | `31fbd6c76e0efbccdde3e6945191e2a174f19565711b11aedc27d4d63e8e1c3a` |
| Candidate-output schema | `affd13215dc8023723e7e497f6fce9696cbf8af9bb7c01a85e8aa560033a776d` |
| Evidence-validation contract | `3529484f74f9c482bd38c68c9bafbc08723e6dfd960e3c8d5faa70e1b6d28ce2` |
| Annotation guideline | `67d693edf8e42318a763aac58190675c90b944440dc12fce164212cf9552bd60` |
| Evaluation matching contract | `10f8dca24bf41acfb21f8d20c5cda7b022392040446a2e2e4bac137365c076d0` |
| Phase B artifact | `675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf` |
| Curation override | `418bff362e3965a78caf5f3f2a761ad8d2fb27b2ee6a062ee60f561e72a27871` |

The fifth controlled rerun used timestamp `2026-08-10T22:36:09Z` and produced
byte-identical inventory and manifest files, including ordering, IDs, spans, texts, hashes,
summaries, and provenance.

## Historical guideline note and limitations

The frozen annotation/adjudication guideline contains a historical noncanonical
curation-path recommendation. Its byte sequence is intentionally preserved to protect the
frozen authority. The active implementation uses only `data/curation/papers/pilot1/` and
does not use that historical recommendation. Any future editorial cleanup requires a
controlled guideline version change and dependent-hash update.

Marker version and exact page geometry remain unavailable, so page and Marker block
references remain empty. Image meaning remains outside text evidence. Partially
recoverable table blocks are retained exactly but are not themselves evidence eligible.
Reference-boundary review detection depends on frozen Phase A reference-occurrence
coverage. Every same/higher-level heading still performs the frozen structural reset; a
future case without the exact bracketing conflict signal receives normal post-reset routing
rather than being guessed from citation style or a venue name.

The source-unit builder component version 0.1.4 and its fifth twelve-artifact materialization
have been independently accepted. Full source-unit/request implementation acceptance still
awaits the future request builder. The sample/input record remains a candidate and is not
frozen; screening and selection have not started. No annotation, gold construction, request
building, LLM extraction, or pilot evaluation occurred.
