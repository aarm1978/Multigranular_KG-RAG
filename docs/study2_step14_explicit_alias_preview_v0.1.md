# Step 14 explicit-alias complement: read-only preview v0.1

`step14-explicit-alias-preview/0.1.0` complements, without changing, the
[unapproved alias_extended baseline](study2_step14_adjudication_eligibility_v0.2.md).
The approved [scope](study2_step14_scope_and_completion_decision_v0.1.md) and
[identity/granularity policy](study2_step14_identity_granularity_adjudication_v0.1.md)
remain authoritative. This is candidate nomination, not identity adjudication.
The separate small consumer preserves v2's implementation and input pins rather
than modifying the code that generated those frozen local results.

## Explicit route

Within the existing exact-class retrieved pairs, nominate whole-name case,
punctuation and formatting variants; explicit parenthesized acronyms and their
expanded labels; or a full distinctive base name plus trailing descriptive words
(framework, software, package, library, tool, model, algorithm, workflow,
implementation). Generic-only names and generic token overlap cannot qualify.
No inferred initials, substring-name similarity or new acronym dictionary is used.
For example, GEE / Google Earth Engine (GEE), HEC-HMS / Hydrologic Modeling System
(HEC-HMS), and NextGen / NextGen framework provide direct candidate cues.
GEE / Google Earth Engine without an explicit acronym declaration is not inferred.
ARLSTM / LSTM and different numeric version labels are not formatting aliases.

Both original labels must be traceable as whole names in selected literal evidence
(case/presentation separators may differ). Exact original evidence hashes and offsets
are checked using the existing enrichment reader. One endpoint may have thin context;
that nomination is explicitly flagged. Original labels, versions, granularity and
source records are never rewritten. Different structured version metadata is retained
as a review flag, not silently erased or adjudicated; matching names cannot approve
incompatible implementations. Missing specificity remains uncertainty. A same-name
collision can still be nominated, so this route does not establish identity.

## Positive-control diagnosis, not population gold

A bounded primary-key lookup of the 250 retrieved pairs inside the 29 approved
subsets (99 memberships) confirms 26 fail the baseline's selection signals before
its mandatory approval exclusion:

- 17 Backpropagation case-variant pairs miss the score conditions.
- Five Random Forest algorithm case-variant pairs miss the score conditions.
- Four AWS CLI pairs fail the both-endpoints contextual-evidence condition.

These are general score/context failure mechanisms, not changed approvals. The
explicit route nominates 21 of these 26 controls. The remaining five have “Random
Forest (RF) Algorithm” in a selected quotation, interrupting the full label's literal
match. This conservative grounding limitation is reported, not repaired merely to
recover every approved control. The controls are retrospective, selected and
nonrepresentative; no population precision/recall or optimality claim is justified.
All approved pairs remain excluded from incremental and combined candidate counts.
Prior pilot/queue/block co-membership remains unresolved rather than becoming approval.

## Lightweight execution and outputs

The consumer opens existing v2 `accounting.sqlite` in read-only/query-only mode and
streams it once. It verifies the consumed accounting, baseline summary/criteria and
original authorities against saved hashes. It does not read/copy v2 LLM contexts,
regenerate accounting, or prepare any model requests. No provider calls, new embeddings,
identity approvals, canonical allocation, ontology changes or KG writes occur.

```bash
python -m src.evaluation.step14_explicit_alias_preview --output var/study2_step14/explicit-alias-preview/v1
```

Fresh output required. `summary.json` and `summary.md` report complete 512,024-pair
accounting, baseline/combined counts, incremental unique pairs by class, scope,
family combination and prior status. `controls.json` preserves the baseline-missed
control identities, reasons and bounded authentic evidence. `examples.json` holds
deterministic representatives of new routes, thin-context/specificity risks and
nonselection. Share these four small diagnostic files. `incremental-pairs.jsonl`
contains only compact exact identities, pointers and flags, not full contexts;
`manifest.json` pins all consumed inputs and generated outputs.

No request quota or desired retention count controls selection. Full incremental
counts await the researcher-terminal run; bounded control counts do not predict them.
Focused tests: `python -m unittest discover -s tests -p test_step14_explicit_alias_preview.py`.
