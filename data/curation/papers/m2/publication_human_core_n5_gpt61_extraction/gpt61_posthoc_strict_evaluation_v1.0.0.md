# GPT-6.1 Human Core N=5 — POST-HOC MODEL SENSITIVITY

Strict evaluation with the unchanged frozen Human Core matcher. This is not a new confirmatory Step 7.

| Model | Kind | TP | FP | FN | Reference | Scored predictions | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 (frozen corrected Step 7B) | nodes | 30 | 79 | 88 | 118 | 109 | 0.275229 | 0.254237 | 0.264317 |
| GPT-5.6 (frozen corrected Step 7B) | relations | 6 | 62 | 55 | 61 | 68 | 0.088235 | 0.098361 | 0.093023 |
| GPT-6.1 (post-hoc) | nodes | 32 | 95 | 86 | 118 | 127 | 0.251969 | 0.271186 | 0.261224 |
| GPT-6.1 (post-hoc) | relations | 7 | 60 | 54 | 61 | 67 | 0.104478 | 0.114754 | 0.109375 |

Only original unit-specific `extract_and_evaluate` opportunities are scored; `extract_and_monitor` is excluded. Reference support remains 118 nodes and 61 relations.

- nodes: 176 production accepted; 127 scored; 49 outside scoring scope.
- relations: 96 production accepted; 67 scored; 29 outside scoring scope.

## Per-unit strict counts

- `pub:10:sec:0008:unit:0001` — node: TP=4 FP=22 FN=32; relation: TP=1 FP=16 FN=16.
- `pub:15:sec:0004:unit:0001` — node: TP=2 FP=12 FN=9; relation: TP=2 FP=14 FN=14.
- `pub:16:sec:0033:unit:0001` — node: TP=4 FP=5 FN=12; relation: TP=0 FP=0 FN=3.
- `pub:34:sec:0015:unit:0001` — node: TP=15 FP=31 FN=14; relation: TP=3 FP=23 FN=12.
- `pub:79:sec:0004:unit:0001` — node: TP=7 FP=25 FN=19; relation: TP=1 FP=7 FN=9.

The JSON companion retains per-target metrics, scoring opportunities, matched pairs and unmatched records. The prediction-input package preserves the exact accepted projections and selected-provider provenance.

No semantic-equivalence review, historical judgment transfer, adjudication, provider calls or KG writes were performed. Historical references, GPT-5.6 Step 7 and Step 8 artifacts remain unchanged.
