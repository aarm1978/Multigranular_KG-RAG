# Step 14 production recommendation selection v0.1

Authority: `step14-production-recommendations/0.1.0`. Semantic calibration is
closed by researcher decision. Select **exactly** the original compatibility-pilot
instructions plus `step14-semantic-calibration/0.1.0`'s existing `CLARIFICATION`.
Do not append the later category-calibration clarification.

Evidence: v1 development 83 matched pairs; v2 held-out 89; v3 category diagnostic
39. The category clarification recovered conceptual relationships but also weakened
supported entity-identity and distinct-referent recommendations, notably Algorithm/MLP
and PP-ML variants, according to the researcher's diagnostic review. Selection is a
methodological/operational judgment, not a gold-standard accuracy estimate. Historical
requests, results and hashes retain their actual authorities. All five categories
remain unapproved recommendations. No canonical mappings or graph writes follow.

The isolated adapter reuses Publications BatchAPI, batch_journal, shared pinned
infrastructure loading, make_job/submit_all/collect_once, authentic receipt pricing,
and exact custom-ID reconciliation. Historical Publications parent checks are never
invoked or changed. Each frozen queued unit has one stable request; exact pair
memberships, endpoint provenance, selected instructions and body hashes are pinned.
Previously deferred/approved pool cases remain governed by the frozen queue accounting.

Offline files contain complete UTF-8 serialized native request lines, at most
20,000,000 bytes and 50,000 requests per file. No scientific unit is split. Local
input estimates are complete provider-body bytes/4 rounded up, not provider-confirmed
tokens or final costs. Provider counting includes top-level instructions, unlike the
historical extraction helper whose count projection omitted them. The small Step 14
count adapter uses the same native HTTP transport and safe-count retry rules.

Configured capacity is 15,000,000,000 input tokens, not assumed availability. Native
reservations include planned and uncertain jobs until settled. Unrelated active
remote Batches cause the native submit gate to wait because their remaining capacity
is unknown. Provider counts must exist for every request before submission. Operational
files are sealed again by native make_job using exact counted tokens; token-capacity
splits can differ from the offline byte-only packing. Custom IDs remain unchanged.

Commands (existing research interpreter, repository root):
`python -m src.evaluation.step14_production_batch prepare`, then `verify` and `status`.
Default root: `var/study2_step14/production-batch/v1/`; refuse overwrite.
Separate researcher gates: `count --execute`, `submit --execute`, `collect --execute`.
Count generates no model response. Submit includes upload and Batch creation under
native durable intents. Restarting submit reconciles uncertain upload/submission
acknowledgements without repeating an uncertain POST; zero/multiple remote matches
STOP. Collection is read-only remotely and preserves authentic outputs locally.
No file-only repeated upload authorization or automatic failed-response redelivery is
introduced. Any genuinely unresolved upload needs separately authorized recovery.

Failures/incompleteness stay failed, never become identity decisions or automatic
retries. Pair/citation validation and abstentions are retained in journal outcomes;
status reports native completion/failure/cost/unknown usage and reservations. Original
provider rows remain in receipts. The preflight and manifest are the compact sizing,
instruction-hash, request-membership and provenance authorities. No provider calls
are needed to prepare or verify this contract.
