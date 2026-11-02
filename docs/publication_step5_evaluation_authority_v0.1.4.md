# Study 2 Step 5 Publication Evaluation Authority v0.1.4

**Project:** Dissertation CS — Study 2
**Authority ID:** `publication-step5-evaluation-authority`
**Authority version:** `0.1.4`
**Status:** **FROZEN/CLOSED**
**Scope:** prospective Step 8 independent second-review coverage only

## 1. Authorized prospective successor

The researcher authorized this successor after accepting the Step 8 review UI at
`2f28cbe7825b1320635dc68976b572e88e2202b4`, before any Step 8 production human
judgments or production activation files existed. It prospectively supersedes
v0.1.3 only by replacing bounded independent 2/6 second review with full independent
6/6 review. Both reviewers judge the same 182 accepted pooled items, comprising
133 nodes and 49 relations. This is reviewer replication, not candidate resampling.

v0.1.3, v0.1.2, v0.1.1, their freeze records, the historical deterministic 2/6
selector/freeze, and the historical 45-item second-review package remain
byte-identical historical provenance. The old selector is not rerun or reinterpreted.

## 2. Controlling inheritance and scope

All v0.1.3 rules and its incorporated v0.1.2 rules remain controlling except the
Step 8 secondary-review coverage superseded here. Only the v0.1.1 rules still
retained by those successors apply. References in retained human-review rules to
the two-unit subset now apply prospectively to all six selected primary units.
This does not restore retired completeness-audit procedures, roles, exposure-ledger
requirements, ordering, matching, saturation, or missed-reference statistics.

- The primary reviewer independently judges every item in all six primary units.
- The independent second reviewer judges exactly the same six primary units and
  the same 182 opaque judgment items, with identical blinded semantic projections.
- Both complete independent initial judgments before reconciliation; neither sees
  the other's decisions or progress. Preserve both originals and their revision
  histories separately from any later reconciliation result.
- The retained non-generative judgments, blinding whitelist, neutral ordering,
  source/context boundaries, duplicate decisions, and reconciliation rules are
  unchanged. Reconciliation cannot edit an assertion and remains a later activity.

Ordinary initial judgments remain `supported_as_proposed`,
`not_supported_as_proposed`, and `insufficient_evidence_to_decide`. Duplicate
decisions remain `same_source_local_assertion`, `distinct_assertions`, and
`insufficient_evidence_to_resolve_duplicate_status`. The distinct final
`adjudication_unresolved` status is available only under the retained reconciliation
rules; it is not an initial judgment or a positive assertion.

The accepted Step 8A pool v1.0.1 and primary Step 8B package v1.0.0 are unchanged.
The six primary units are derived from the accepted N=6 selection and checked
against that primary package. Authorized context remains supporting context and
cannot become an additional evaluation unit or judgment-item source.

## 3. Predeclared paired candidate-support agreement

The analysis uses 182 paired independent initial candidate-support judgments,
joined exactly by opaque judgment item ID, before reconciliation. Report:

1. Exact observed agreement: matching initial categories divided by paired items.
2. Unweighted, three-category nominal Cohen's kappa: `(p_o - p_e) / (1 - p_e)`,
   with `p_e` calculated from the two reviewers' category marginal proportions.
3. Overall results (182), nodes (133), and relations (49), each with a 3-by-3
   category confusion/count table, row and column totals, and paired denominator.
4. Target-level agreement only descriptively where support is adequate; always
   disclose target item counts and category counts. No target-level inferential
   claims or unstated numerical adequacy threshold are introduced by this amendment.

All three categories, including insufficient evidence, remain in the denominators.
If `p_e = 1`, report kappa as undefined with its reason and observed agreement;
do not substitute zero or one. If either initial review is incomplete, report that
the planned paired analysis is incomplete; do not impute or silently drop missing
judgments. No agreement value is computed by this implementation task.

This is candidate-support judgment agreement conditional on the fixed pool, not
extraction IAA, extraction accuracy, or a replacement for Human Core N=2 reliability.
Reconciled judgments must not replace either initial judgment in this analysis.

## 4. Frozen successor bindings

The closure record is
`data/curation/papers/m2/publication_step5_evaluation_authority_freeze_v0.1.4.json`.
It binds this authority, amendment v0.3, retained predecessor provenance, accepted
primary package, and the following new artifacts:

- `data/curation/papers/m2/step5_freeze/publication_pool_secondary_review_scope_freeze_v0.1.4.json`;
- `data/curation/papers/m2/publication_step8_blinded_adjudication/publication_step8b_blinded_second_review_v1.1.0.json`;
- `data/curation/papers/m2/publication_step8_blinded_adjudication/publication_step8b_reviewer_instructions_v1.1.0.json`.

The new scope derives membership from the frozen N=6 primary selection and binds
the unchanged primary package. The second package inherits every blinded item,
opaque ID, evidence occurrence, context authorization, and duplicate group directly
from that package. Internal bindings are kept in the freeze record, not added to
reviewer-visible assertion fields. The preserved private opaque-lineage map continues
to reconstruct all items for both roles.

## 5. Unchanged boundaries and execution state

This successor does not change the candidate universe, N=6 sampling, Human Core
N=5 or N=2 reliability, evidence, ontology, extraction, LLM outputs, Production
Acceptance, SciERC, later KG construction, or GraphRAG comparison. It supports no
completeness or saturation claim. All existing interpretive exclusions remain.

Step 8A and the Step 8B primary package are accepted; the UI is accepted at the
checkpoint above. Full independent secondary review is prospectively authorized.
This successor implements only the new bindings. It creates no production human
judgment or activation file, executes no reconciliation, and performs no provider
call, extraction rerun, candidate regeneration, or positive-reference assembly.
Production activation requires the separate researcher execution decision and
role-specific approvals bound to the final runtime and package hashes.
