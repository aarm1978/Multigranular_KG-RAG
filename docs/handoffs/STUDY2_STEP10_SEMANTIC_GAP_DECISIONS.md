# Study 2 Step 10 — Source-specific semantic-gap decisions

**Status:** Closed by researcher approval on 2026-10-07. This record captures the
accepted decisions from the completed HydroShare, GitHub, and CIROH Hub inspections;
it does not repeat the audits or assert exhaustive semantic coverage.

## Prospective baseline and preservation boundary

Ontology **v0.1.6**, formally frozen in commit
`b2c735bce9692e8937abcc08c4d9ac48a85b255e`, is the new prospective TBox baseline.
Its validation and import limitations are recorded in
[ontology_formalization.md](../ontology_formalization.md#12-study-2-step-10-additive-amendment-016-formally-frozen).
Historical ontology fixtures, hashes, and Publication deterministic and evaluation
authorities remain unchanged. Cross-source identity resolution remains in **Step 14**.

## Next authorized implementation item: minimal HydroShare corrections

Before Step 11, implement only:

1. Own-resource DOI extraction from `system_metadata.doi`.
2. Prospective inventory-ID alignment, where needed by current contracts, for the
   existing `DatasetResource hasContributor Person` edges (C-D27) and
   `Award fundedBy Organization` edges (C-D28).

These are prospective corrections, not changes to existing relation semantics or
permission to rewrite historical artifacts. This closure task performs no implementation,
tests, or graph regeneration. The minimal package must be handled as a separate work item.

`DataService` and `servesDataset` remain available in v0.1.6 but **service extraction
is not activated** by the minimal package. GitHub/Hub deterministic extraction and
Publication deterministic/evaluation authorities are outside this correction package.

## Accepted narrow LLM-semantic families

| Source | Accepted family scope |
|---|---|
| HydroShare | Scientific variables; evidence-backed tool/model roles; workflows; explicitly supported dataset-to-code provenance. |
| GitHub | RepositoryPurpose; evidence-backed tool/model/dataset roles; workflows; selective implementation semantics. |
| CIROH Hub | Clearly typed scientific products/components; describes relations; substantive procedures/steps/workflows. |

These are family-level scope decisions, not final target contracts or accepted instances.
**Step 11** owns exact target contracts, evidence rules, and abstention behavior.
No exhaustive extraction is promised. Exact links alone do not establish use,
implementation, or generation provenance; procedural structure alone does not establish
a scientifically meaningful workflow.

## Deferred work

- HydroShare and GitHub README generic-reference enhancements.
- Hub direct doc-to-doc references and citation parsing.
- Additional typed geographic identifiers.
- Service extraction and other comprehensive-scenario enhancements.

Deferral does not reclassify mechanically recoverable information as an LLM target.
No additional ontology expansion, cross-source identity resolution, or comprehensive
deterministic implementation is authorized by this record.

**Handoff:** Step 10 is closed. The next work item is the minimal HydroShare
deterministic correction package above; Step 11 contract work follows that package.
