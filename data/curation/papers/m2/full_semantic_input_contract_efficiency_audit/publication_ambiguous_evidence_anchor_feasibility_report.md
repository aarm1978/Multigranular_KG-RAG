# Ambiguous evidence exact-anchor feasibility audit

Offline only; no historic output or live contract was changed.

| Span | Occurrences | Original cp | Unique anchor cp | Added left/right cp | Anchor unique | Structural line unique | Semantic extension |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| DEV-06 evidence-0006 | 4 | 30 | 31 | 1/0 | yes | true | not established (fail closed) |
| DEV-06 evidence-0010 | 3 | 18 | 20 | 0/2 | yes | true | not established (fail closed) |
| DEV-07 evidence-0004 | 2 | 30 | 31 | 0/1 | yes | true | not established (fail closed) |

All three historic ambiguous spans admit a unique exact locator anchor without normalization, fuzzy matching, the coordinate guide, or model-generated offsets. This establishes location-only feasibility, not a semantic-extension or live-contract decision.
