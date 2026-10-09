# Study 2 Step 12B — Offline validation acceptance

**Researcher approval date:** 2026-10-09
**Status:** CLOSED / ACCEPTED
**Accepted validation checkpoint:** `cefc241d15cdc340a51b02ab654a68b998e189d5`
**Branch:** `codex/publication-human-core-annotation-ui`

## Authority and scope

The researcher accepts focused offline readiness for the three non-Publication
families under [frozen Step 11 v0.3 §9](../study2_step11_source_specific_semantic_contracts_v0.3.md),
its [acceptance record](STUDY2_STEP11_SEMANTIC_CONTRACTS_ACCEPTANCE.md), ontology
v0.1.6 and the [Step 12A technical integration acceptance](STUDY2_STEP12A_TECHNICAL_INTEGRATION_ACCEPTANCE.md).
This record adds no methodological authority, context-selection policy or target.

Offline readiness is accepted; **semantic accuracy, contextual completeness,
authentic provider behavior and KG acceptance remain unproven**. Structural checks
and literal evidence binding do not satisfy semantic gates. Semantic acceptance
remains unevaluated and KG authorization remains false. Synthetic replay does not
demonstrate authentic provider execution or authorize a live pilot, production,
full-corpus extraction or graph materialization.

## Reported validation evidence

Codex reported **26 focused synthetic T1/T2 tests passing: 10 HydroShare, 8 GitHub
and 8 Hub**, comprising the 23 existing replay tests and three new integration
tests. The initial focused run reported 25 passes and one new-fixture failure;
after supplying the already-required per-fragment contribution descriptions, the
corrected test passed on its focused rerun. No implementation change was needed.
These are reported results, not an assertion of a single clean 26-test rerun.
**No tests were executed or independently re-audited for this documentation-only
closure.** Previously accepted component tests below were not part of that
26-test execution and are not added to its count.

The executed replay files were:

- [HydroShare replay tests](../../tests/test_datasets_semantic_offline_pipeline.py).
- [GitHub replay tests](../../tests/test_coderepos_semantic_offline_pipeline.py).
- [Hub replay tests](../../tests/test_documents_semantic_offline_pipeline.py).

The three new tests were respectively
`test_integrated_abstract_readme_and_prohibited_targets`,
`test_integrated_downloaded_authorities_and_own_product`, and
`test_integrated_visible_fence_and_parent_context`. They exercise synthetic source
reading, request construction, recorded-response parsing and offline replay,
including multiple selected units, independently bound evidence, exact provenance
and independent-candidate survival. Existing replay checks retain selected-unit
boundaries, parse-error quarantine, source completeness, immutable records,
duplicates and zero external effects.

## Seven §9 readiness criteria and supporting evidence

“Integrated” below means direct synthetic replay evidence in the three files above,
including existing tests rerun at the accepted checkpoint. “Component” means
previously accepted focused tests, cited for coverage without repeating them.

| §9 criterion | Direct integrated evidence | Previously accepted component evidence / boundary |
|---|---|---|
| 1. Approved IDs, domain/range and exclusions against v0.1.6; no abstract-class predictions or model-authored D-26. | New HydroShare mixed-authority test rejects abstract Model, inactive DataService and D-26 while independent Tool assertions survive. | [Target-profile tests](../../tests/test_nonpublication_semantic_target_profiles.py): exact allowlists/ontology correspondence, signatures/direction/declared unions, conditional/inactive/pipeline targets. Source-specific batch-validator tests cover complete allowlists and wrong signatures; three replay examples do not replace that coverage. |
| 2. GitHub downloaded/selection-reason/extension/path/content-kind gates, including descriptive `other`, workshop Markdown, CITATION and code exclusion. | New GitHub integration uses downloaded `workshops/Flow.markdown` with `file_role=other`, `CITATION.txt` and additional prose; excludes `examples/run.py`; an actual missing synthetic downloaded file leaves surviving candidates and incomplete-source diagnostics. | [GitHub source-unit tests](../../tests/test_coderepos_semantic_source_units.py): `test_eligibility_and_descriptive_other`, scoped changelog/contributing review, and `test_paths_hashes_coordinates_and_source_failures` cover unsafe paths, unknown metadata, unreadable/malformed sources and digest failures. No corpus audit was repeated. |
| 3. Phase A README precedence/deduplication, distinct additional READMEs and original notebook Markdown only. | New GitHub integration retains one authoritative `README.md`, distinct `docs/README.md`, notebook Markdown cell identity and raw/authority hashes through replay; code/output text is excluded. | GitHub source-unit tests `test_readme_precedence_and_additional_readmes` and `test_notebook_markdown_fidelity_and_cell_identity` cover raw duplicate disagreement, zero-based cell indices and original text fidelity. No cell execution or code interpretation. |
| 4. Hub original MDX coordinates, static visibility, displayed examples and parent/prose restrictions for Parameter. | New Hub integration excludes comments/dynamic expressions, binds original MDX offsets/hash and verified Section provenance, retains fenced evidence only as possible Example context, and holds fenced Parameter and its dependent edge while independent prose assertions survive. Existing replay parent-path test isolates invalid parent relations. | [Hub source-unit tests](../../tests/test_documents_semantic_source_units.py), [evidence-binding tests](../../tests/test_documents_semantic_evidence_binding.py), [Example-context tests](../../tests/test_documents_semantic_example_context_binding.py) and [candidate tests](../../tests/test_documents_semantic_candidate_validation.py) cover line coordinates, visibility, accepted-parent paths, attachment agreement and Parameter prose. Parent semantic acceptance remains pending. |
| 5. Exactly six versioned RepositoryPurpose seeds, distinct from evidence-dependent C-C07; no invented categories, clones or duplicate emissions. | Existing GitHub replay `test_seed_endpoint_mapping_purpose_and_unresolved_method` separates six controlled seeds from caller endpoints and holds hasPurpose gates; replay duplicate tests preserve citations and suppression decisions. | [Purpose tests](../../tests/test_coderepos_semantic_purpose_validation.py): exact vocabulary/stability, independent endpoint binding, invalid categories/quotes and duplicates. [GitHub candidate tests](../../tests/test_coderepos_semantic_candidate_validation.py) cover seed stability and purpose delegation. Scheme remains `ciroh-repository-purpose/1.0.0`; no implicit memberships. |
| 6. C-C16 valid Publication A-P13 endpoint conditions versus immutable unresolved/nonmaterialized proposals; later resolution remains Step 14-governed. | Existing GitHub seed/Method replay supplies a typed synthetic Method endpoint yet preserves `unresolved_endpoint` and pending gates. It does not demonstrate an authorized positive semantic acceptance or materialization path. | GitHub candidate `test_conditional_own_product_and_method_nonresolution` and target-profile conditional checks cover the frozen constraints. Accepted full-corpus Publication production in Step 13 is still required before read-only endpoint reconsideration; separately approved Step 14 resolution must be source-grounded and non-retroactive. Closure does not waive these deferred conditions. |
| 7. Source-read/integrity prerequisites for no-evidence claims; explicit technical failures; exact hashes/coordinates; own-product ModelVersion; authentic outputs only under separate authorization. | Existing replay empty/abstention/incomplete-source tests reject invalid no-evidence claims and infer none from failures. New tests carry mixed HydroShare, raw/README/notebook GitHub and Hub authority provenance; GitHub own-product ModelVersion remains conditional and a dependency-repository claim is rejected. Round-trip tests preserve exact synthetic response bytes/hashes and immutable reports. | Source-unit/evidence tests for all three families cover missing/unreadable/hash-failed sources and Unicode/line coordinates. GitHub candidate tests cover own-product restrictions. Synthetic recorded bytes establish replay fidelity only; authentic provider behavior/output preservation during live execution is not demonstrated here. |

## Preserved boundaries and next workstream

Frozen Step 11 v0.3, ontology v0.1.6, Phase A/B, Publication v0.1.5 authorities,
Steps 7–9 artifacts and deterministic graphs/hashes remain unchanged. Source-local
identity, trusted endpoint inventories, original evidence and source-specific
eligibility/exclusion rules remain binding. No automatic cross-source alignment,
model-authored provenance/gate attestations or post-generation evidence repair is
introduced.

HydroShare Measurement remains README-only with its semantic gate pending.
GitHub purpose membership and own-product ModelVersion gates remain pending.
Hub Example/Parameter retain accepted Procedure/Step parent and required-relation
conditions; displayed fences are only possible Example context, and Parameter
identity/role requires explanatory prose. DataService/servesDataset remain inactive.
D-26 remains pipeline-derived and distinct from HydroShare C-D26 mentionsModel.
Source failures and incomplete inputs never become inferred semantic abstentions.
All other frozen inactive/deferred scope remains unchanged.

**Step 12B is CLOSED / ACCEPTED. Step 12C pilot planning is next.** Planning and
any subsequent live pilot require their own authorized scope; this closure grants
no provider permission. Steps 13 production and 14 alignment retain their separate
dependencies and approvals. No contextual-completeness policy is established.

This task changes only this record and the tracked
[operational handoff](../codex/CODEX_HANDOFF.md). It performs no code changes,
test execution, audit repetition, corpus processing, provider calls or graph
writes. Unrelated local modifications remain outside the commit.
