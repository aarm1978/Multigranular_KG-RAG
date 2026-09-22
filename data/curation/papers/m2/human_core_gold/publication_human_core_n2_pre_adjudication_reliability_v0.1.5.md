# Human-to-Human N=2 Pre-Adjudication Reliability

This is a deterministic descriptive comparison under the frozen amended matching contract. It contains no adjudication, annotation modification, reliability gate, PASS/FAIL result, or production-acceptance inference.

## Detection and evidence

- Nodes: A=73, B=67, matched=38, A coverage=0.520548, B coverage=0.567164, symmetric pairwise F1=0.542857.
- Node mention boundaries: exact=34/38 (0.894737); tolerant=38/38; mean F1=0.991053.
- Node supporting evidence: exact=12/38 (0.315789); mean P/R/F1=0.795374/0.945311/0.822765.
- Relations: A=30, B=32, matched=15, A coverage=0.500000, B coverage=0.468750, symmetric pairwise F1=0.483871.
- Relation evidence: exact=13/15 (0.866667); mean P/R/F1=0.969181/1.000000/0.982570.

## Characterization and exhaustive presence/absence

- Nodes: class=33/38; operational target=33/38.
- Relations: type=13/15; target=13/15; direction (same type)=1/13; source endpoint=14/15; target endpoint=12/15; both=11/15.
- Exhaustive node table (++,+−,−+,−−)=19,1,1,2 (n=23; observed agreement=0.913043).
- Exhaustive relation table (++,+−,−+,−−)=10,2,2,3 (n=17; observed agreement=0.764706).

## Permitted disagreement diagnostics

- Detection-only: nodes A=35, B=29; relations A=15, B=17.
- Characterization: node class=5, node operational target=5, relation type=2, relation operational target=2.

The accompanying JSON artifact carries pairing keys, boundary/evidence summaries, and raw diagnostic keys for deterministic reproduction.
