# Publication LLM Extraction Target Inventory — v0.1.5 Successor Addendum

**Status:** final and binding for the prospective Publication v0.1.5 authority bundle.
This concise successor incorporates the unchanged v0.1.4 inventory by reference; it does
not alter historical V014 artifacts or their provenance.

## Frozen authority bindings

- Ontology: CIROH 0.1.5; validated OWL SHA-256
  `ce5f6d3d8ac926dc8ff872c9a36066758a86068b6681417bf7edc6aaeccf1e71`.
- Machine inventory:
  `src/extraction/llm/publications/publication_target_inventory_v0.1.5.yaml`.
- Candidate schema:
  `schemas/publication_candidate_output_v0.1.1.json` (schema version 0.1.1).
- Prompt: `src/extraction/llm/publications/prompts/publication_development_v0.1.8.txt`
  (`publication-development-0.1.8`).

## Authorized V015 deltas

1. `AgentBasedModel` is the fifth concrete `ComputationalModel` subtype and is a
   direct LLM candidate target (`extract_and_evaluate`).
2. Publication-prose `Organization` is a direct open-discovery LLM target with
   `extract_and_evaluate` treatment. Ontology-level Organization extraction remains
   globally hybrid. This source-local prose target is intentionally cross-category:
   it is not assigned to a single routing category because organization mentions may
   occur in any publication section.
3. `C-P34 hasComponent` is a full-production model-authorable relation. The six
   affected full-production signatures (`C-P13`, `C-P14`, `C-P23`, `C-P26`, `C-P27`,
   and `C-P34`) include `AgentBasedModel` wherever the frozen V015 profile records it.
4. `D-26 mentions` remains non-model-authorable and post-acceptance only. Accepted,
   evidence-backed publication-prose Organization candidates derive `Paper → mentions
   → Organization`; discourse-derived D-26 requires strict evidence containment.
   Endpoint coexistence alone is never sufficient.

## Operational counts

The machine inventory contains 62 node rows: 9 `context_only`, 2
`deferred_resolution`, 21 `extract_and_evaluate`, 21 `extract_and_monitor`, 4
`out_of_scope`, and 5 `required_infrastructure`.

It contains 45 relation rows: 8 `context_only`, 1 `deferred_resolution`, 17
`extract_and_evaluate`, 10 `extract_and_monitor`, 3 `out_of_scope`, 5
`required_infrastructure`, and 1 `separate_follow_on_protocol`.

Candidate coverage is 48 nodes: 42 direct open-discovery, 4 deterministic context,
and 2 deferred-resolution. There are 28 candidate relations, of which 27 are
full-production model-authorable. D-26 is excluded.

All unchanged targets, routing categories, evidence rules, evaluation modes, and
historical V014 authority remain as specified by
[`publication_llm_extraction_target_inventory.md`](publication_llm_extraction_target_inventory.md).
