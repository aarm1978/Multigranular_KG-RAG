# Full-semantic input-contract efficiency audit

Offline only: 0 provider/model calls. Sizes are UTF-8 canonical JSON bytes.

| Unit | Text | Prompt | Targets | Guide | Metadata | Schema | Provider input | API body |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DEV-01 | 2372 | 4777 | 60061 | 87296 | 6078 | 110329 | 160684 | 287047 |
| DEV-02 | 8329 | 4777 | 60061 | 286710 | 10174 | 110359 | 370151 | 515954 |
| DEV-03 | 2921 | 4777 | 60061 | 87314 | 5841 | 110370 | 161014 | 287230 |
| DEV-04 | 602 | 4777 | 60061 | 27167 | 4880 | 110336 | 97587 | 217913 |
| DEV-05 | 3753 | 4777 | 60061 | 106436 | 6135 | 110338 | 181262 | 309376 |
| DEV-06 | 6215 | 4777 | 60061 | 242132 | 11868 | 110324 | 325153 | 466951 |
| DEV-07 | 2446 | 4777 | 60061 | 67018 | 5497 | 110322 | 139899 | 264135 |
| DEV-08 | 4762 | 4777 | 60061 | 129625 | 6872 | 110390 | 206197 | 336519 |
| DEV-09 | 1545 | 4777 | 60061 | 42140 | 5540 | 110340 | 114163 | 236011 |
| DEV-10 | 774 | 4777 | 60061 | 19911 | 5220 | 110325 | 90843 | 210448 |

## Findings

- The guide repeats source tokens with two coordinate systems; it is a methodological/contractual candidate, not a transport-only reduction.
- Target definitions repeat target identity and constraints also represented in the structured schema. Pipeline/evaluation/provenance fields are separately measurable transport-only candidates pending semantic-equivalence review.
- Across DEV-01–DEV-10, omitting only the classified pipeline/evaluation/provenance target-definition fields would reduce the provider input by 127190 bytes and the API body by 140930 bytes; this is an estimate, not an implemented change.
- Literal evidence can yield offsets only when it appears exactly once in the canonical source-unit text. Repeated or absent literals are ambiguous and must fail closed; current returned coordinates remain required.
- Smallest next experiment: an offline, one-unit differential equivalence audit of pipeline/evaluation/provenance target-definition fields only; do not alter evidence, target, schema, or validation rules.
