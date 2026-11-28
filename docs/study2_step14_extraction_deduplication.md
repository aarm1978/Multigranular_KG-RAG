# Exact extraction deduplication before alignment evaluation

The frozen Step 13 v4 snapshot and Step 14 final-alignment/v1 remain historical authorities. This offline derivative resolves repeated extraction of a single source-local mention before projecting semantic hypotheses. It performs no new semantic adjudication. Its retained node IDs are original Step 13 IDs.

## Reproduce or verify

Run from the repository root in the existing Step 14 Python environment. The default output is the ignored directory `var/study2_step14/deduplicated-alignment/v1/`.

```bash
python -m src.evaluation.step14_deduplicated_alignment verify
python -m pytest -q tests/test_step14_extraction_reprojection.py
```

To reproduce independently, use a fresh output path:

```bash
python -m src.evaluation.step14_deduplicated_alignment build --output var/study2_step14/deduplicated-alignment/replay-v1
python -m src.evaluation.step14_deduplicated_alignment verify --output var/study2_step14/deduplicated-alignment/replay-v1
```

## Source occurrence and assertion contracts

The census visits every original node. It binds publication offsets to the actual raw and canonical document hashes and checks unit-to-document offsets. For the other three families it reads the hash-pinned owner report, original source unit, authority-relative coordinates, artifact key and revision. File paths, notebook cells, source fields and snapshots distinguish documentary contexts. Fingerprints retain complete evidence-span multiplicity, literal labels, ontology types, entity attributes and their evidence associations, identifiers, version and recorded granularity. Different request, candidate, evidence and unit aliases can resolve to the same original source coordinates. A label must have exactly one source location across the bound spans. Equal text at two positions does not suffice.

Structural keys remain source-specific. Deterministic records without bound document spans and controlled vocabulary seeds retain their IDs. Where required, ordered Hub parent paths resolve to source-bound ancestors. Conflicting contextual owners distinguish metric and parameter occurrences; an ambiguous owner cannot bridge alternatives. Ordinary node fingerprints are independent of incident assertion sets. The lexicographically smallest original node ID represents each verified block.

The assertion ledger records the redirected triple for each original edge. Identical directed triples share a retained assertion. Publication use/mention precedence and D-26 fallback suppression use the Step 13 policy tables. Source-local nonpublication D-26 follows the existing owner-pair rule. Suppression identifies the surviving stronger triples. Signature validation uses the v0.1.9 declarations, including shared class IRIs and the documented Phase B inventory spellings. A newly induced self-loop or invalid signature blocks publication of the derivative.

## Package and review boundary

- `graph/snapshot.json` contains only source-local nodes and assertions. `node-mapping.jsonl` links every original ID to its representative, native evidence lines and retention reasons. `assertion-mapping.jsonl` links every original assertion ID to its disposition. The pinned Step 13 snapshot, native sidecar and derivation sidecar retain original attributes, evidence and extraction lineage. `duplicate-blocks.jsonl` lists exact memberships, their fingerprint and their position relative to prior identities.
- `alignment/identity-dispositions.jsonl` retains every original group, its projected members, authority and exact conflicting representatives. Singletons resolve to their retained occurrence. Identical memberships can share one projection. Distinct intersecting scopes are withheld in full. Their ledger entries remain available. The original historical approvals stay in `historical-approvals.jsonl`; `historical-projections.jsonl` records their separate prospective representation. Approval and materialization restrictions continue to apply to the original exact memberships.
- `alignment/automatic-identity-frame.jsonl` and `typed-relation-frame.jsonl` are the revised unsampled populations. The occurrence provenance ledger resolves representative source evidence. Identity source records link back to complete original memberships and decisions. Relation support retains original bindings and directed cited endpoints alongside `projectedCitedOccurrences`. The relation disposition ledger accounts for each original prediction. Multiple incompatible endpoint projections, disputed memberships and self-relations are withheld without expanding the witnesses.
- `summary.json` contains the whole-graph census, including zero-yield classes and all source families. `manifest.json` pins inputs and outputs. Verification checks those hashes and independently accounts for original nodes, assertions, historical decisions and both frames.

The derivative reduces a census of identity cases from 2,084 automatic proposals to 1,629. Exact duplication accounts for 453 collapsed cases. Two competing memberships are withheld. The 221 directed relation cases remain. These are population counts. Sampling workload and reviewer minutes depend on the eventual evaluation design.
