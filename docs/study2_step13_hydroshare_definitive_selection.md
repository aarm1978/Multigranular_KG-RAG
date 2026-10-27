# Study 2 Step 13 — definitive HydroShare source-local selection

Researcher-approved selection decision, 2026-10-27: retain the original production
outcomes for the 22 HydroShare owners unaffected by omitted README inputs. For
exactly the 20 affected owners, select the complete completed README-recovery
outcome in place of the original outcome, including when recovery has zero yield.
Exclude the superseded original accepted records and diagnostics. Do not union,
merge, reconcile, or choose individual candidates across executions.

The original root is `var/study2_step13/source-families-gpt61-batch/v1/`; the recovery
root is `var/study2_step13/hydroshare-readme-recovery/v2/`. Recovery queue SHA-256:
`57dab8abb6c4a78dbe6c22d184032872ae68764520e150c25de2ff40b084014c`.
Verification implementation checkpoint: `3e1468f293bba04e7de69d14fd64aa2eea1ee4e7`.
The selection expects **187 accepted nodes and 188 accepted edges (375 total)**;
authoritative journal discrepancies must stop materialization, never cause repair
or an adjustment to the expected totals.

Run from the repository root in the researcher terminal:

```bash
/Users/aramirezm/opt/anaconda3/bin/python -m src.evaluation.hydroshare_definitive_selection
```

The ignored, publish-once destination is
`var/study2_step13/hydroshare-definitive-selection/v1/`. Existing destinations are
refused. Both input trees are hashed before and after reading and remain untouched.
Native journal chains, receipt checks, pinned sources, lineage, and persisted
construction records are checked offline; neither extraction nor semantic
validation/admission is rerun. Reading the shared original journal for technical
integrity does not select or materialize GitHub/CIROH Hub records.

Output contract:

- `selection-manifest.json`: exactly one selected run/request/attempt per owner,
  original input hashes and journal heads, output hashes, expected totals, and
  one-based JSONL row mappings. Zero-count ranges select no records.
- `accepted-projections.jsonl`: one unchanged native construction projection per
  owner, including its external endpoints, source snapshot and policy provenance.
- `accepted-nodes.jsonl`, `accepted-edges.jsonl`: unchanged native records in
  selected-owner order. Use the manifest row ranges and projection context;
  candidate IDs remain local to their original run/request, not globally unique.
- `selected-outcomes.jsonl`: a transport envelope containing the exact selected
  prepared request and all persisted receipts/native outcomes for that selected
  request. The latest terminal processable outcome supplies the accepted
  projection. Earlier deliveries within that same selected run remain diagnostic
  history; no replaced original owner outcome is copied.
- `per-owner.jsonl`: selected coverage, construction/replay disposition counts,
  explicit abstentions and zero-yield status. Complete rejection, hold and other
  diagnostic records remain in `selected-outcomes.jsonl` without reinterpretation.
  Native `originalReplay` denotes the pre-conformance replay within the selected
  run, not the superseded original execution.
- `summary.md`: concise technical selection summary.

This is a source-local execution selection, not scientific correctness
adjudication, precision/recall evaluation, candidate deduplication, cross-artifact
alignment, KG construction or Step 14. Historical production artifacts and their
authorities remain unchanged. Full materialization is to be run by the researcher;
implementation tests use synthetic records only.
