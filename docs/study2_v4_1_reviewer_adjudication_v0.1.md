# Study 2 v4.1: narrowly scoped reviewer adjudication

Authority: `source-local-reviewer-adjudication/0.1.0`.
Status: three exclusions explicitly approved by the researcher; the completed v4.1 comparison still requires independent review. This is post-hoc scientific adjudication, not an autonomous extraction success, a new model call, or evidence of scientific closure.

The declarative authority is [the pinned adjudication record](study2_v4_1_reviewer_adjudications_v0.1.json). It records exact request/owner/candidate identities, candidate and bound-evidence hashes, source-unit hashes and original offsets, typed resolved endpoints, v4 group hashes, baseline/diagnostic hashes, reasons and researcher authorization. It contains references and hashes rather than copied source documents or response payloads.

| Excluded v4 winner | Authentic candidate reconsidered | Approved reason |
|---|---|---|
| has-procedure-multi | has-procedure-hybrid | Multi-node MPI evidence does not support the resolved hybrid MPI+OpenMP Procedure. |
| edge-reference-compute-paper | edge-reference-imagery-paper | Citation DOI 10.2139/ssrn.5451100 does not identify the resolved Paper DOI 10.2139/ssrn.5531964. |
| e-page-jupyter | e-page-python-path | Launching Jupyter does not independently support configuring Python's path and importing data grabbers. |

## Implementation boundary

The separate opt-in adjudication overlay runs after ordinary source-local validation/enrichment and before construction. It adds an explicit reviewer rejection finding to each pinned unsupported candidate. The existing construction schema consequently records it as **held**, with the adjudication reason; it is excluded from the derived accepted projection, not erased from the authentic output.

Only duplicate markers referencing an excluded winner are cleared. The counterpart must still satisfy all existing construction checks; no assertion is retargeted and no evidence is transferred. Explicit dependency/parent references remain unchanged. Native construction recomputes its fixed-point dependency closure and exact-triple duplicate selection. A descendant referencing an excluded parent cannot be repaired by substituting the surviving edge.

The runner verifies original queue/implementation pins, original receipts and supplemental selection using existing mechanisms. It preserves v4's implementation authorities. For the three affected requests it first reproduces the complete v4 report from authentic response bytes, then replays under the explicit adjudication overlay. Other groups reuse verified v4 records; native owner consolidation is reused for all owners. Unrelated owner reports must remain exactly identical. The comparison rejects changes outside the affected dependency closure, unexplained accepted losses, candidate/evidence/endpoint drift, derived-assertion drift, missing groups, incomplete owners, accounting drift and changes to the six quarantined abstentions.

Historical code, authentic candidates, requests, responses, v3/v4 outputs, ontology, Step 11, Publications and the materialized-content amendment remain unchanged. The new authority does not purport to have governed historical extraction. No general validator contains candidate-specific exceptions.

## Offline execution

From the repository root, in the existing `multigranular-kg` environment:

```bash
python -m src.evaluation.source_local_supplemental_review_v41
```

Requires the original ignored v6 queue/receipts, supplemental response, v2/v3 authority manifests, completed v4 reports and the pinned v1 semantic diagnostic. All socket connections are blocked. Existing output is refused; a failed/partial run must be preserved for investigation, never silently overwritten.

Output: `var/study2_step13/source-local-supplemental-review/v4.1/` with native `groups/`, `owners/`, `summary.json`, `selection-manifest.json`, `comparison.json`, and unchanged `quarantined-abstentions.json`. Share only `share/`: `synthesis.md`, `comparison.json`, `adjudications.json`, `manifest.json`. These compact records include all six reviewed decisions, any dependency consequences, typed endpoints and evidence references, group versus consolidated-owner counts, family counts and overall differences. Group counting units are request-local candidates; owner counts use existing exact consolidation. They are not accuracy, precision or recall estimates.

Full corpus execution is reserved for the researcher terminal. Focused tests include synthetic independent/dependent gates and, when ignored inputs are locally available, only the three affected authentic groups. The original v4 disposition and authentic evidence remain inspectable even for excluded records.
