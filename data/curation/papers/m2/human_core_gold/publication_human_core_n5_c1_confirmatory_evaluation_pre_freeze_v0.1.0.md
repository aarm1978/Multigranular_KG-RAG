# Publication Human Core N=5 C1 Confirmatory Evaluation — PRE-FREEZE

This is the one-time Step 7B result under the frozen amended matching contract. It is not a Step 7C freeze or closure record.

## Aggregate confirmatory metrics

- Nodes: TP=29, FP=73, FN=89, reference support=118, prediction support=102, micro P/R/F1=0.284314/0.245763/0.263636.
- Relations: TP=6, FP=53, FN=55, reference support=61, prediction support=59, micro P/R/F1=0.101695/0.098361/0.100000.

Only frozen unit-specific `extract_and_evaluate` opportunities are scored. `extract_and_monitor` is excluded. The JSON companion contains every scoring opportunity, matched pair, unmatched reference, unmatched prediction, and per-unit/per-target breakdown.

## Per-unit descriptive counts

- `pub:10:sec:0008:unit:0001` — node: TP=5 FP=18 FN=31 ref=36 pred=23; relation: TP=1 FP=14 FN=16 ref=17 pred=15.
- `pub:15:sec:0004:unit:0001` — node: TP=1 FP=12 FN=10 ref=11 pred=13; relation: TP=1 FP=8 FN=15 ref=16 pred=9.
- `pub:16:sec:0033:unit:0001` — node: TP=4 FP=4 FN=12 ref=16 pred=8; relation: TP=0 FP=0 FN=3 ref=3 pred=0.
- `pub:34:sec:0015:unit:0001` — node: TP=13 FP=25 FN=16 ref=29 pred=38; relation: TP=3 FP=22 FN=12 ref=15 pred=25.
- `pub:79:sec:0004:unit:0001` — node: TP=6 FP=14 FN=20 ref=26 pred=20; relation: TP=1 FP=9 FN=9 ref=10 pred=10.

Status remains **PRE-FREEZE**. Step 7C was not executed and Step 7 is not marked FROZEN/CLOSED.
