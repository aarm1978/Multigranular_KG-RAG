# Step 14 decision/materialization preparation v0.1

Prospective route C is authorized by the researcher instruction accompanying this
implementation. It supplements, not replaces, the existing automatic-acceptance
policy. All outputs are provisional and local: no final KG, owl:sameAs, source
rewriting, provider execution or human-verification claim.

A/B reuse saved complete-group outcomes and original safeguards, preserving the
full baseline row in the ledger. Route C requires an explicit complete
`strict_identity` assessment, validated evidence bindings for every member,
a nonempty granularity assessment, exact class/inventory compatibility, retained
original provenance, and no structured granularity, identifier, preparation or
contradictory-evidence conflict. Raw capture-version inequality is not a model
release conflict. The model's assessment is predicted semantic support, not truth.
Free-text uncertainty is preserved verbatim; its presence or absence is not a
Boolean acceptance rule. Unexpressed semantic conflicts cannot be mechanically
certified away; independent human evaluation remains required.

Exact membership is the reconciliation key. Original scopes and explicitly
proposed anchor subsets remain distinct. A spanning original group without any
single complete assessment does not acquire C eligibility from partial subsets,
pair coverage or transitive chains. Existing saved negative/conflicting comparisons,
new distinct/nonidentity or contradictory assessments intersecting at least two
members, and internal D-27/D-28 relationships conservatively hold affected identity
proposals. Partial historical approval overlaps never propagate approval; exact
historical scopes remain separately identified and the full ledger is preserved.
The existing conservative overlap guard holds every differing eligible membership
sharing an occurrence. No maximal-clique selection or overlap winner is invented.

Every original pair and routing row is retained. The consumer asserts 74,051 pairs,
51,079 complete original scopes, 1,795 contextual units and 31 unresolved units.
It explicitly checks 27,310 deferred and 36,573 non-renominated comparisons.
Non-renomination means preserved, not rejected. The 25 oversized scopes remain
unexpanded. All unresolved unit records are retained exactly; no repairs occur.

Typed proposals deduplicate exact directed (subject, predicate, object) triples
while retaining every supporting assessment, inventory signature, original quote
binding and receipt pointer. Existing workflow validation and v0.1.8 domain/range
checks apply. Related-but-nonidentical assessments without a supported predicate
remain in the assessment inventory, alongside separately exported abstentions and
ontology gaps. These are not automatically approved edges. The original Step 13
assertion files are referenced with hashes, not regenerated or rewritten. A later
materializer must retain those assertions and provenance, using the separate mapping
view rather than overwriting their source-local endpoints.

The versioned decision ledger separates historical exact approvals, saved A/B
states, C-supported provisional proposals, holds and unresolved evidence. Provisional
canonical identifiers are deterministic hashes of exact memberships in an explicitly
provisional namespace. Mapping rows retain original source member records and
representation holds (including Workflow). They are materialization inputs, not
production allocations. Identity and relation sampling frames are separate and
unsampled; they are preparer frames containing model information, not model-blind
review sheets or population accuracy estimates. Freeze rules and construct an
independent blinded evaluation before production decisions.

Run from the repository root, using the existing Python environment with PyYAML
and jsonschema:

```bash
python -m src.evaluation.step14_decision_stage --output var/study2_step14/decision-stage/v1
python -m unittest discover -s tests -p test_step14_decision_stage.py -v
```

The full run is researcher-terminal work; no full-corpus decision yield is claimed
before it completes. Fresh destinations are required. Outputs include
`decision-ledger.jsonl`, `occurrence-mappings.jsonl`, `original-group-reconciliation.jsonl`,
`historical-approvals.jsonl`, original pair/routing inventories, `invalid-units.jsonl`,
`typed-relation-proposals.jsonl`, `assessment-inventory.jsonl`, `abstentions.jsonl`,
`ontology-gaps.jsonl`, separate identity/relation evaluation frames, oversized scopes,
original assertion references, `summary.json`, and an input/output hash manifest.
All outputs remain ignored. Any input count/hash, quote binding, alias or ontology
signature mismatch fails rather than silently repairing data.
