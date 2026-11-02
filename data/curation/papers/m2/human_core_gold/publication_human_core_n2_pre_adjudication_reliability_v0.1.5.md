# Human-to-Human N=2 Pre-Adjudication Reliability

This is a deterministic descriptive comparison under the frozen amended matching contract. It contains no adjudication, annotation modification, reliability gate, PASS/FAIL result, or production-acceptance inference.

## Detection and evidence

- Nodes: A=55, B=48, matched=28, A coverage=0.509091, B coverage=0.583333, symmetric pairwise F1=0.543689.
- Node mention boundaries: exact=25/28 (0.892857); tolerant=28/28; mean F1=0.988484.
- Node supporting evidence: exact=7/28 (0.250000); mean P/R/F1=0.772439/0.931198/0.795983.
- Relations: A=25, B=28, matched=13, A coverage=0.520000, B coverage=0.464286, symmetric pairwise F1=0.490566.
- Relation evidence: exact=12/13 (0.923077); mean P/R/F1=0.981325/1.000000/0.989372.

## Characterization and exhaustive presence/absence

- Nodes: class=33/38; operational target=33/38.
- Relations: type=13/15; target=13/15; direction (same type)=10/13; source endpoint=14/15; target endpoint=12/15; both=11/15.
- Exhaustive node table (++,+−,−+,−−)=21,1,1,4 (n=27; observed agreement=0.925926).
- Exhaustive relation table (++,+−,−+,−−)=10,2,2,10 (n=24; observed agreement=0.833333).
- Monitor positive-set only (non-exhaustive): nodes A/B/shared=18/19/7; relations A/B/shared=5/4/2. No monitor absence enters a 2x2 table.

## Permitted disagreement diagnostics

- Detection-only: nodes A=35, B=29; relations A=15, B=17.
- Nodes: class=5, operational target=5, mention boundary=4, supporting evidence=26.
- Relations: type=2, operational target=2, direction=3, source endpoint=1, target endpoint=3, relation evidence=2.

The accompanying JSON artifact carries pairing keys, boundary/evidence summaries, and raw diagnostic keys for deterministic reproduction.
