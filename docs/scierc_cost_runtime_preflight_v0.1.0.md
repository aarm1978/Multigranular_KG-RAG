# SciERC official cost/runtime planning supplement v0.1.0

NOT AUTHORIZED FOR PROVIDER EXECUTION. Step 9 remains open; Step 8 unchanged.
Reproduce offline: `python -m src.extraction.llm.publications.scierc_cost_preflight`.
Authentic ignored runtime bytes are read-only. No launch function is invoked.

## Preserved smoke

Frozen dev line 1 `ICCV_2003_158_abs`: completed_valid, HTTP 200, gpt-5.6-sol.
Terminal SHA-256: `92d16707867982b9f219f5f05196c82bf26d4339e07ad6ad674ba71056440861`. One local dispatch marker and response;
not proof of global account activity or internal service attempts. Structural replay
passes; no semantic review, gold comparison or benchmark metrics. Exact artifact and
approval hashes are in `scierc_smoke_preservation_v0.1.0.json`.
Observed input 2,116 (2,113 cache writes, zero reads); total output 5,290 includes
3,744 reasoning and 1,546 non-reasoning tokens. Total usage 7,406.
Observed client elapsed: 93.691190542 seconds. No rerun.

## Pricing basis and accounting

Researcher-supplied external verification dated 2026-10-05, NOT independently
browsed by Codex: [model](https://developers.openai.com/api/docs/models/gpt-5.6-sol),
[caching](https://developers.openai.com/api/docs/guides/prompt-caching).
Standard/short-context USD per million: ordinary input 4, cache read 0.40,
cache write 5, output including reasoning 20. Observed service_tier is `default`;
applicable Standard tier, region and account/custom billing remain unverified.
Smoke reconstruction: ((2116-2113-0)*4 + 2113*5 + 0*0.40 + 5290*20)/1e6
= **$0.116377**, not an invoice.
Cache writes replace ordinary pricing; reasoning is not charged twice.

## Separate official plan

Exactly **100 planned generation POSTs**, one per frozen test document, sequential
concurrency 1; completed smoke is separate. No automatic redispatch or extra calls.
The unchanged v0.2.0 candidate and smoke preservation file are hash-bound in the JSON.

Local tiktoken 0.3.3 has no model/prefix mapping for gpt-5.6-sol; no encoding is
loaded/downloaded. Estimated input = sum ceil(request bytes * 2116 / 9741).
The 995,967 complete-request bytes already include prompt/schema
on all 100 requests (raw prompt 2,933 and schema
968 bytes each). Do not add their token cost again.
Baseline input **216,403 estimated tokens**; 0.5x/1x/2x
sensitivity: {'0.5': 108225, '1': 216403, '2': 432746}. These are not exact tokens. The whole-body
ratio can vary with composition, source length, escaping and provider representation.

Output and elapsed scenarios simply multiply the one observation; no inferred gold
counts or semantic adjustment. Costs below hold input at the baseline estimate and
assume every input token uses cache-write pricing, with **no guaranteed cache reads**.
Half/baseline add zero extra seconds; double scenario adds 10 seconds/request.

| Assumption | Non-reasoning | Reasoning | Total output | USD | Sequential hours |
| --- | ---: | ---: | ---: | ---: | ---: |
| half_observation | 77,300 | 187,200 | 264,500 | $6.372015 | 1.301 |
| one_observation_baseline | 154,600 | 374,400 | 529,000 | $11.662015 | 2.603 |
| double_plus_overhead | 309,200 | 748,800 | 1,058,000 | $22.242015 | 5.483 |

Baseline ordinary-input/no-caching alternative: $11.445612.
Output cap: 32,768/request, **3,276,800 total**, output-only cost **$65.536000**.
Conditional conservative scenario: 432,746 input tokens
(2x byte-calibrated estimate), all cache writes/no reads, plus full output cap:
**$67.699730**. This is NOT a guaranteed spending cap: input must
stay within that assumed bound, the stated rates/context tier must apply, and no
extra billed calls/fees may occur. Input uncertainty prevents a strict total bound.

Sequential arithmetic baseline: 100 * 93.691190542 =
9369.1190542s
(156.152 minutes).
N=1 is not a population mean, confidence interval, percentile, or predictive model.
Client elapsed is not pure provider latency. Extra startup, disk, rate-limit pacing,
service slowdown and interruption can increase time. 180s is a socket-operation
timeout, not a wall-clock guarantee.

## Before any official launch

Account RPM/TPM are unknown. Baseline equivalent rates are
0.640 RPM and
4773.6 actual-token TPM,
not verified permitted limits. The largest conditional input plus full output
reservation is 40,493 tokens.
Confirm reservation rules and rolling-window limits, then explicitly pace starts;
sequential concurrency alone does not ensure compliance. No subscription inference.

Required: researcher preflight review and separate explicit official authorization;
an offline-tested/accepted sequential dispatcher with exact 100-document membership,
durable per-request no-redispatch claims and full evidence preservation; separate
ignored runtime namespace; confirmed account pricing/limits and stop/budget policy.
None of these approvals or the official dispatcher is created here.

One successful mechanical smoke does not establish semantic quality, test performance,
cache reliability, full-run structural success, future latency or account limits.
Frozen authorities, prompt/configuration/schema/scoring and candidate flags stay unchanged.
