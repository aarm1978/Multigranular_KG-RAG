# DEV-02 attempt-4 ↔ attempt-5 prospective test-retest specification

**Development-only prospective specification.** This freezes comparison dimensions only. It authorizes no provider call, creates no attempt 5, and sets no acceptance threshold.

## Preconditions

- Attempt 4 remains the preserved source of truth at `researcher_authorized_verification_001/DEV-02`.
- A future attempt 5, if separately authorized, must be created through its own auditable lifecycle location without modifying attempts 1–4.
- The comparison must use preserved raw outputs, bound parser artifacts, validation results, usable outputs, provenance records, and exact source/target authorities.

## Frozen dimensions

1. **Exact configuration identity** — compare prompt version/hash, request-specialized schema version/hash, provider-input SHA-256, model/reasoning/output-budget/store settings, ontology and target-inventory authorities, endpoint/evidence binding versions, and V1–V12 validator authorities. Report identity and every difference; do not pre-classify any difference as acceptable.
2. **Structural and validation stability** — compare raw candidate-node, candidate-edge, evidence-span, abstention, and deferred-record counts; binding status/findings; V1–V12 envelope; node/edge/evidence status counts; usable node/edge counts; finding codes with occurrence counts; token usage; and output-budget pressure.
3. **Semantic node assertion overlap** — normalize away candidate/evidence IDs and ordering. Compare ontology class, referent/value, and supporting source evidence. Partition into shared, A4-only, and A5-only.
4. **Semantic edge assertion overlap** — normalize away candidate/evidence IDs and ordering. Compare relation type, semantically matched endpoints, and relation-specific supporting source evidence. Partition into shared, A4-only, and A5-only.
5. **Run-only valid assertions** — for each exclusive assertion, record source evidence, existing target/ontology contract, and a `strongly_supported` or `plausible / needs semantic review` classification without altering output.
6. **Run-only questionable or unsupported assertions** — for each exclusive assertion, record source evidence, existing target/ontology contract, and an `unsupported or likely over-extraction` classification; retain it as an observation and do not repair or tune the prompt.

No overlap percentage, count threshold, acceptance threshold, retry policy, or prompt/contract remediation decision is specified here.
