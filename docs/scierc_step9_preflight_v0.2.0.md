# Step 9 SciERC prospective preflight candidate v0.2.0

Status: **NOT AUTHORIZED FOR PROVIDER EXECUTION**. Unfrozen review candidate.
Starting checkout: `b53582376c662b7595e9f8995d790cb9b1253dcd`.
This record does not close Step 9 or affect Step 8 reconciliation.

## Authority and source provenance

Retained Step 5 v0.1.1 §12, as retained by successors v0.1.2 §8,
v0.1.3 §§2–3 and v0.1.4 §5, governs the benchmark-native anchor.
Source freeze v0.1.0 and adapter freeze v0.1.2 under `step5_freeze/`
remain unchanged. Official archive SHA-256 is
`bce752fb7ebe4acf570937d76ffb27c239cfc907e477a69075dc7082d0e72e9b`.
Local archive: `var/scierc_external_anchor/source/sciERC_processed.tar.gz`.
All three member hashes/counts remain the frozen 350/50/100 train/dev/test bindings.

Official guideline: `https://nlp.cs.washington.edu/sciIE/annotation_guideline.pdf`,
local `var/scierc_external_anchor/source/scierc_annotation_guideline.pdf`, SHA-256
`0688907df3905cbe19c7d09c152c80b46a90abc9bddca7b019ec3925183b694d`.
It is source documentation, not a replacement methodological authority.
No download was performed for this correction.

The unfrozen recovery record is relocated byte-identically from
`data/curation/papers/m2/step5_freeze/scierc_external_anchor_source_recovery_v0.1.0.json`
to `data/curation/papers/m2/scierc_step9_preflight/scierc_external_anchor_source_recovery_v0.1.0.json`.
Its original history remains at `cfbbbb6`; no actual Step 5 freeze is relocated.

## Prompt provenance and prospective decision

`prompts/scierc_native_v0.2.0.txt` and `scierc_configuration_v0.2.0.json`
under `src/extraction/llm/publications/` are prospective review candidates.

| Content | Guideline source location |
| --- | --- |
| Six entity definitions | p.1, §1.1, six bullets; Evaluation Metric serializes as Metric, Other Scientific Terms as OtherScientificTerm per source freeze |
| USED-FOR and FEATURE-OF | p.1, §1.2; domain continuation at top of p.2 |
| HYPONYM-OF, PART-OF, COMPARE, CONJUNCTION | p.2, §1.2 |
| Directed B → A and sentence boundary | p.1, §1.2 opening paragraph |
| Embedded-span condition; determiner/adjective-pronoun exclusion; generic phrases requiring a relation | p.2, §1.4 notes 1–2 |
| Variable-bound and “which” relation exclusion | p.2, §1.4 note 3 |
| Negative-relation exclusion | p.3, §1.4 note 5 |

Guideline examples do not enter the prompt. Coreference rules (§1.3 and §1.4
note 4) are outside the frozen task. Note 1 references ACL RD-TEC without supplying
its full rules; no unavailable external boundary preference is invented here.
Exact token joining and IDs are serialization mechanics, not semantic repair.
No endpoint-type restrictions are imposed by validation.

The researcher approved on 2026-10-05 this prospective operational definition:

> EVALUATE-FOR = "links an evaluation measure or criterion to the scientific entity
> it evaluates; equivalently, in the inverse direction, the scientific entity is
> evaluated by that measure or criterion."

This definition is absent from the original guideline and is not attributed to it.
The serialization is measure/criterion first, evaluated entity second. The inverse
wording describes the same assertion; it does not make this relation symmetric.

## Bounded direction verification

The recorded check uses five fixed directed-relation records each from train/dev,
with exact line, document, sentence, relation index, spans and record hash in
`scierc_directionality_check_v0.2.0.json`. Archive and member hashes are verified.
The initial bounded locator pass stopped at the first occurrence of each of the
seven labels in each split (train lines 1–3, dev lines 1–6); only ten directed
records are retained for reproduction. There was no frequency/performance analysis.

The train EVALUATE-FOR locator is line 3, `INTERSPEECH_2013_31_abs`, sentence 3,
relation 0: first span 82–83, second span 85–88. The dev locator is line 5,
`C04-1116`, sentence 1, relation 0: first span 31–31, second span 34–36.
These are measure/criterion → evaluated-entity serializations, compatible with
the approved wording. Four other directed labels agree with guideline B → A.
COMPARE/CONJUNCTION canonicalization remains symmetric. No test gold is used
for these checks, and no source examples are copied into model instructions.

## Parsing, scoring and isolation

Sentence ranges and unchanged string tokens define document-global zero-based
inclusive spans. Mentions must fit one sentence; both direct-relation endpoints
must fit the same sentence. Malformed tokens, Boolean/float offsets, extra fields,
invalid labels, missing endpoints and invalid/duplicate relation IDs fail explicitly.
No invalid predictions are silently dropped or repaired.

Primary entity keys are (document, start, end, type). Primary relation keys are
(document, relation type, source span, target span), with canonical endpoint order
only for COMPARE/CONJUNCTION. Endpoint entity types are excluded. Existing exact
signature set semantics are retained; duplicate predicted signatures are rejected.
Duplicate documents cannot enter scoring twice. There is no composite score.

Micro F1 = 2TP/(2TP+FP+FN), including zero when TP=0 and the denominator is positive.
Precision is undefined (null) if TP+FP=0; recall if TP+FN=0; F1 if 2TP+FP+FN=0.
These are separate denominator cases, not substituted zeros or ones.

Synthetic counterfactuals replace gold entities/relations/clusters while preserving
document ID and source tokens; exact canonical provider request bytes must remain
identical. The official builder reads verified JSON mechanically with
`include_gold=False`; it neither validates nor scores test annotations. Its only
input is an archive path verified against the original frozen SHA, not a caller's
document list. All 100 unique frozen test IDs enter exactly once. The candidate
contains identity/hash/accounting metadata, not test text or gold annotations.

## Runtime boundary and accounting

One document means one logical request: 100 requests. Configuration remains
gpt-5.6-sol, medium, max_output_tokens=32768, synchronous, stateless, store=false,
without automatic redispatch or Production Acceptance. The coding-agent model
is unrelated. Source, prompt, configuration, schema, implementation, document IDs
and every request body are hash-bound. Build readiness does not imply runtime
acceptance or researcher authorization; both latter flags remain false.

Serialized complete-request UTF-8 bytes include repeated prompt/schema overhead
and are explicitly a byte proxy, not an exact provider token count. The total
output ceiling is 3,276,800 tokens. Exact provider input tokens, observed usage,
latency, prices and costs remain unknown/null. Runtime skeleton fields preserve
raw response/output, usage, model/configuration hashes and client timing for later
separately authorized work. No dispatch implementation or authorization is added.

Reproduce locally: `python -m src.extraction.llm.publications.scierc_preflight`.
This writes metadata candidates under `scierc_step9_preflight/` only. Raw source
bytes remain ignored. No final runtime manifest or live adapter is frozen.

## Baseline failure comparison

Exact node:
`tests/test_publication_openai_structured_provider.py::StructuredLivePipelineTests::test_valid_structured_response_traverses_and_replays`.
It fails at line 324 (`invalid` != `valid`) on both starting `b535823` and historical
`574802b` in detached temporary worktrees, using the same local source file
`data/raw/papers/markdowns/36/markdown/36_md.md` (SHA-256
`107ad70b252f24f09a933f646904982e05a35eb6559893b0c7bf925ab51f2d6f`).
Initially both isolated worktrees lacked this ignored fixture; copying this one
file reproduced the same original assertion failure at both commits.
All transport calls in that test are injected local mocks. The failure predates
Step 9. SciERC shares only provider body construction, not that Publication
downstream validation/fixture behavior. No unrelated repair was made.
