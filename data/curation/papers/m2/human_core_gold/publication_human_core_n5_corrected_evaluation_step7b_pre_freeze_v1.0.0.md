# Publication Human Core N=5 Corrected Evaluation Step 7B — PRE-FREEZE

This is the prospective strict deterministic Step 7B result against the frozen corrected Pilot 1 evaluation realization. It does not alter historical C1 Step 7B artifacts and is not a Step 7C freeze or closure record.

## Aggregate confirmatory metrics

- Nodes: TP=30, FP=79, FN=88, reference support=118, prediction support=109, micro P/R/F1=0.275229/0.254237/0.264317.
- Relations: TP=6, FP=62, FN=55, reference support=61, prediction support=68, micro P/R/F1=0.088235/0.098361/0.093023.

Only frozen unit-specific `extract_and_evaluate` opportunities are scored. `extract_and_monitor` is excluded. The JSON companion contains every scoring opportunity, matched pair, unmatched reference, unmatched prediction, and per-unit/per-target breakdown.

## Per-unit descriptive counts

- `pub:10:sec:0008:unit:0001` — node: TP=4 FP=17 FN=32 ref=36 pred=21; relation: TP=0 FP=12 FN=17 ref=17 pred=12.
- `pub:15:sec:0004:unit:0001` — node: TP=2 FP=11 FN=9 ref=11 pred=13; relation: TP=2 FP=12 FN=14 ref=16 pred=14.
- `pub:16:sec:0033:unit:0001` — node: TP=3 FP=4 FN=13 ref=16 pred=7; relation: TP=0 FP=0 FN=3 ref=3 pred=0.
- `pub:34:sec:0015:unit:0001` — node: TP=14 FP=24 FN=15 ref=29 pred=38; relation: TP=3 FP=23 FN=12 ref=15 pred=26.
- `pub:79:sec:0004:unit:0001` — node: TP=7 FP=23 FN=19 ref=26 pred=30; relation: TP=1 FP=15 FN=9 ref=10 pred=16.

Status remains **PRE-FREEZE**. Step 7C was not executed and Step 7 is not marked FROZEN/CLOSED.
