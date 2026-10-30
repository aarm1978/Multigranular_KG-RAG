# Study 2 Step 13 completion acceptance

Date: 2026-10-30. Code checkpoint: `f506ec9644707552c435b74400e63049ac27a738`.
**Status: CLOSED / ACCEPTED by the researcher, 2026-10-30, within the scientific limits below.**

Documentation closure starts from `86c65c7bb74f7a07aacae5bb0592a7e02a1a5831`; the separate pre-alignment metrics preparation is preserved. This record supersedes pending operational status in the historical draft and v4.1 authority, without rewriting those authorities.

The researcher explicitly accepts the completed v4.1 source-local interpretation for HydroShare, GitHub and CIROH Hub, and completed Publications production with seven terminal exceptions. Ontology v0.1.7 is formally frozen. The stale operational `docs/codex/CODEX_HANDOFF.md` is not used to override these decisions.

## Four selected outputs

| Family | Selected output and counting unit | Accepted nodes | Accepted edges |
|---|---|---:|---:|
| HydroShare | v4.1 `owners/`, `artifactFamily=hydroshare`, 42 complete owners | 429 | 388 |
| GitHub | v4.1 `owners/`, `artifactFamily=github`, 51 complete owners | 1,563 | 1,483 |
| CIROH Hub | v4.1 `owners/`, `artifactFamily=ciroh_hub`, 242 complete owners | 2,994 | 2,532 |
| Publications | `var/study2_step13/publications-gpt61-batch/v1/`, existing selected accepted-semantic outcomes referenced by `publications-production-verification/v1/verification.json` | 182,255 | 89,021 |

Non-Publication root: `var/study2_step13/source-local-supplemental-review/v4.1/`. Its 1,005 group reports contain **9,463 admissions: 5,060 nodes + 4,403 edges**. Native owner consolidation produces **4,986 nodes + 4,403 edges = 9,389 records** across 335 owners. The difference is 74 node occurrences consolidated by existing exact identity, not lost edges or evidence. **407 derived construction inputs** are separate (HydroShare 46; GitHub 135; Hub 226); do not add them to the 9,463 admission count. These records are not a final KG or globally unique entities.

The v4.1 diagnostics retain 91 held candidates, 55 suppressed duplicates, 11,017 valid abstentions, six quarantined malformed abstentions, and 39 zero-yield owners. The three approved exclusions remain identifiable as held reviewer-excluded candidates; their three authentic counterparts were reconsidered and accepted through existing rules. All six transitions and their provenance remain in `comparison.json`; unrelated decisions are unchanged. Historical v3/v4 outputs and original model bytes remain untouched.

Non-Publication accounting remains 1,005 original Batch requests, 1,004 completed Batch responses, one original incomplete response, and one separately recorded validated live supplement. This is 1,005 selected complete response identities, not 1,006 production requests. The original Batch usage and supplemental live usage remain separate.

Publications retains **10,893 requests: 10,886 completed-protected and seven terminal-review exceptions**. Coverage: 216 papers (209 complete, seven partial); 3,933 source units (3,926 complete, six partial, one uncovered). Terminal request IDs, source units and paper identities are preserved in `reconciliation.json`, with authentic delivery/billing history remaining in `publications-production-verification/v1/exceptions.json`. Acceptance with terminal exceptions does not mean those seven requests became successful. No retries or reprocessing are authorized by this closure.

## Authorities and integrity

- Current canonical ontology: `src/ontology/ontology_spec.yaml`, v0.1.7; generated OWL SHA-256 `ac64435ca02a703bdee8168a045a3897d7f6f5be1a8e25e6cdf485c66c85e0fa`, matching the researcher-confirmed HermiT freeze in `docs/ontology_formalization.md` §13. Formal consistency does not prove source-level semantic correctness.
- Non-Publication construction: `study2-construction-acceptance/0.1.0`; approved source-local specialized contracts and historical source/request pins; `study2-materialized-corpus-evidence/0.1.0` with implementation v0.5; `source-local-reviewer-adjudication/0.1.0` for the three explicit post-hoc corrections.
- Publications: frozen `publication-production-acceptance-policy/0.1.0`, its existing v0.1.5/schema v0.1.3 contracts and historical production pins. Current ontology freeze does not rewrite the ontology/contract bytes or authority labels used by completed historical production. No application of the materialized-evidence route to completed Publications is implied.
- `reconciliation.json` records hashes of current reports, verifies their internal report hashes and reconciles group/owner counts. The Publications verification's existing input hashes match the current manifest, journal, head, sealed inputs and downloaded evidence files; its journal anchor is sequence 46,294 / `ecccd49a4d8fe4c32416726389d703e1815f6657ce9becf573f43b29ada205b1`.
- `selection-integrity.json` checks v6 queue/run pins, supplemental record hashes and durable head sequence 4,045 / `b0f65658c8de8d7b9e96b125c8d89a26183d989d1aa2affe6ca1606759bcd8af`. New report-file hashes are audit anchors, not retroactively pre-existing signatures. No corpus or journal semantic replay was performed.

## Diagnostic evidence and retained limitations

The researcher confirmed all 12 post-production diagnostic judgments: **11 Supported and R03 Questionable; R09 Supported**. The [tracked confirmed decision record](../evaluation/study2_step13_diagnostic_review_confirmed_2026-10-30.json) preserves exact case/candidate/request/owner identities, response and evidence hashes, rationales and reviewer attribution. All six family × ordinary/conditional admission strata have two judgments. These are **ChatGPT-assisted, researcher-confirmed**, not independent or blinded judgments. Three existing researcher-approved selective exceptions are reused; no new exception judgments were added. Automated validation and the v4.1 adjudications are not independent population-quality estimates.

**R03 (`algorithm-clark-routing`, A-DOM13)** remains a questionable Method-versus-Algorithm semantic-typing case. Its authentic accepted candidate is preserved without retyping or exclusion. This single diagnostic case does not establish a systematic error. **R09 (`edge-measurement-nwm-peak`, C-D17)** is Supported as a documented modeled measurement, not a field observation or proof of execution.

Archive provenance is resolved without a waiver: the researcher-confirmed uploaded outer `closure-review.zip` has SHA-256 `f87dc2f2640b67ef0fca32e475339a80b2671cfbbb68e69d3323e780875e8b17`; its member `closure-review/v1/researcher-review.zip` has SHA-256 `8392d4e8a94bb5e4f38a19d1a6b82d70c0ede442b6d33ec86dfed234dcf089c5`, independently matching the local inner archive. All nine review members reconcile. The outer container relationship is researcher-confirmed; original archive bytes remain unchanged. The original local review's blank fields remain historical; the separate confirmed record supplies the judgments.

This sampling was not predeclared before extraction. It cannot fulfill the historical pre-production timing requirement retroactively. This closure retains that timing deviation and the researcher’s explicit acceptance of the bounded retrospective diagnostic; it does not claim prospective compliance. No independent gold, recall, precision, F1, or population accuracy estimate results from these reviews or automated admission counts.

Remaining holds, abstentions, zero-yield sources, unresolved identity/method/dependency records, seven Publications terminal exceptions and evidence-to-endpoint interpretation risk remain limitations. Source-local identifiers do not establish cross-source equivalence. Source presence does not establish assertion truth. Publications' recorded usage-priced cost is not a verified final invoice. Historical output selection and all provenance must remain reproducible.

## Closure decision and Step 14 readiness

The researcher accepts the four selected source-local outputs, the three explicit v4.1 post-hoc corrections, seven Publications terminal exceptions, and the bounded diagnostic with R03 retained as questionable. The previously missing six-stratum judgments are now documented. **Study 2 Step 13 is CLOSED / ACCEPTED within these limits.** This is source-local production acceptance, not proof of exhaustive scientific coverage or assertion-level truth.

Step 14 may proceed under separate authorization and unchanged identity/provenance boundaries. This closure does not begin alignment, construct the final KG, or change evaluation policy. The pre-alignment cumulative structural checkpoint is prepared separately; its metrics have not been measured or finalized by this documentation task. `results/metrics/trajectory.md` is unchanged.

Focused closure checks verify the 12 identity/evidence associations, original package member hashes, and confirmed judgment totals. Existing reconciliations are reused; no corpus replay, provider call, ontology change, source modification or KG write occurred. Historical policy and production authority versions remain reproducible rather than being relabeled as current versions.
