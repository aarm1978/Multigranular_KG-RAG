# Human Core Ontology Coverage Review v1.0

**Status:** Frozen researcher decisions for one bounded additive refinement.

The immutable primary Human Core baseline is preserved by the deterministic local session
export recorded in
`publication_human_core_primary_annotation_baseline_v1.0.json`. Its five selected units
are all submitted. The runtime SQLite remains ignored and is not versioned. The immutable
researcher observation log is
`publication_human_core_ontology_gap_observations_v1.0.json`.

| Observation | Decision for planned v0.1.5 | Boundary |
| --- | --- | --- |
| AgentBasedModel | ACCEPT: new concrete `ComputationalModel` subtype | Additive only; preserve v0.1.4 annotations. |
| Publication composition | ACCEPT: reuse `hasComponent` with a Publication prose realization | Do not create a property or change `hasComponent` semantics. |
| Prose Organization | ACCEPT for Publication LLM/hybrid extraction | Generic mentions only; no organization-specific semantic relations. |

These observations authorize one bounded additive ontology refinement, planned as v0.1.5.
After v0.1.5 is frozen, further ontology expansion is deferred unless a reproducible
blocker invalidates the frozen Study 2 evaluation protocol.

After v0.1.5, conduct a targeted supplemental review of the five Human Core units only
for new or affected targets and relations. Preserve all v0.1.4 annotations; a full manual
re-screening of the 358 units is not authorized. Ontology v0.1.5 is not implemented by
this review.
