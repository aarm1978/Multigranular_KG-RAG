# Authentic evidence-binding feasibility audit

Offline only. Authentic C1B output is read-only; C2A is validator context only.

- Evidence spans: 135; unique exact literals: 132 (97.8%); ambiguous: 3 (2.2%); non-literal/zero: 0 (0.0%).
- Unique bindings: 131 coordinate agreements and 1 mismatches.
- Candidate evidence groups: 254; all-unique: 251; ambiguous: 3; non-literal: 0.
- Conservative title-corrected historical candidate failures preventable by unique deterministic coordinate binding: 2.
- DEV-05: authentic `evidence-0003` is uniquely bindable at unit offset 541, not the returned 545. Its coordinate-local validator `EVIDENCE_NOT_LITERAL` finding follows from that incorrect claimed offset; unique deterministic binding would have prevented the two dependent candidate rejections prospectively.
- Hypothetical guide omission: 1096309 provider-input bytes across DEV-01–DEV-10. This is methodological/contractual and not implemented.
- Conclusion: authentic evidence supports investigating a strictly fail-closed binding layer for unique exact literals only; it does not support weakening literal-evidence or coordinate validation.
