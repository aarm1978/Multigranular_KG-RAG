# Final N=2 Human-to-Human Reliability Synthesis

## Authorities and scope

The primary frozen deterministic reliability result is [data/curation/papers/m2/human_core_gold/publication_human_core_n2_pre_adjudication_reliability_v0.1.5.json](data/curation/papers/m2/human_core_gold/publication_human_core_n2_pre_adjudication_reliability_v0.1.5.json) (SHA-256 `e65787c02073907631efbc996e658e6abce2114d39524d6a1c794bbac2ac5eea`), finalized at historical checkpoint `cce912f3d30a0925deb6db858eb1b5961f942285`; its companion frozen report is `data/curation/papers/m2/human_core_gold/publication_human_core_n2_pre_adjudication_reliability_v0.1.5.md`. The deterministic analysis is primary and remains unchanged.

The secondary artifact is `publication_human_core_n2_manual_equivalence_sensitivity_v0.1.json`. It is a **human-reviewed equivalence sensitivity analysis**, not adjudication, not a gold standard, and not a replacement for or retrospective modification of the frozen matching contract or deterministic pairings. Annotator A and Annotator B remain unmodified.

## Primary frozen deterministic reliability

- `extract_and_evaluate` nodes: A=55, B=48, M=28, symmetric F1=0.543689.
- `extract_and_evaluate` relations: A=25, B=28, M=13, symmetric F1=0.490566.
- Node target presence/absence agreement: 25/27 = 92.6%.
- Relation target presence/absence agreement: 20/24 = 83.3%.

## Secondary human-reviewed equivalence sensitivity analysis

- `extract_and_evaluate` nodes: A=55, B=48, M=39, symmetric F1=0.7572815533980582.
- `extract_and_evaluate` relations: A=25, B=28, M=23, symmetric F1=0.8679245283018868.
- `extract_and_monitor` nodes: A=18, B=19, M=11, symmetric F1=0.5945945945945946.
- `extract_and_monitor` relations: A=5, B=4, M=3, symmetric F1=0.6666666666666666.

Only the 26 positive researcher-approved equivalence cases were preserved. No exhaustive negative discrepancy classification was reconstructed. `extract_and_monitor` remains non-exhaustive. This bounded N=2 assessment must not be presented as a corpus-wide inter-annotator-agreement estimate.
