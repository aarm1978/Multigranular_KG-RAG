# Human Core Supplemental Annotation Addendum v0.1.5

This addendum governs only session `HUMAN_CORE_N5_SUPPLEMENTAL_V015` under package
`publication-human-core-gold-n5-supplemental-v015`. It supplements, and does not replace,
the **Human Core Expert Annotation Guide v1.1**. Guide 1.1 continues to govern all general
annotation rules: evidence, exact spans, atomicity, identity, context, uncertainty,
workflow, and submission behavior.

## Frozen authorities

- Ontology: v0.1.5, `src/ontology/ontology_spec.yaml`, SHA-256
  `eac8ec2e0eeec380d05e75c804dc386e9e8aaf8f443b79e20a25a163e513efc5`.
- Generated OWL: `src/ontology/ciroh_ontology.owl`, SHA-256
  `ce5f6d3d8ac926dc8ff872c9a36066758a86068b6681417bf7edc6aaeccf1e71`.
- Supplemental package: `publication-human-core-gold-n5-supplemental-v015`.
- Primary reference: immutable `HUMAN_CORE_N5_PRIMARY_V1` export, verified before use.

## Bounded task

Review only the five frozen Human Core units and only these targets:

- Nodes: `AgentBasedModel`; publication-prose `Organization`.
- Relations: C-P13 `usesModel` (Paper and Method branches), C-P14 `appliesTo`, C-P23
  `mentionsModel`, C-P26 `evaluates`, C-P27 `hasParameter`, and C-P34 `hasComponent`.

C-P13, C-P14, C-P23, C-P26, and C-P27 are **AgentBasedModel delta branches only**.
Their supplemental signatures admit only `AgentBasedModel` on the changed model side;
they do not reopen ProcessBasedModel, ConceptualModel, StatisticalModel, MLModel, Method,
or Experiment branches already covered by the immutable primary review. C-P34 is new and
retains its full Tool/ComputationalModel concrete endpoint signature, including eligible
immutable baseline endpoints.

Do not reopen, copy, revise, normalize, or recreate any primary annotation. Submitted
same-unit primary nodes shown in the interface are immutable relation endpoints only.
Their saved artifact scope is preserved when relation scope is calculated. D-26 generic
`mentions` remains pipeline-derived and is not a supplemental human-authored relation.

No target outside this list is available for supplemental review. This addendum does not
authorize 358-unit re-screening, ontology modification, production-contract migration, or
provider/model calls.
