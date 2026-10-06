"""Read-only smoke verification and deterministic planning; no dispatch entry point."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path

from . import scierc_external_anchor as a
from . import scierc_smoke_runtime as r
from .openai_provider import extract_model_output, validate_provider_response

DIRECTORY = a.PROJECT_ROOT / "data/curation/papers/m2/scierc_step9_preflight"
INPUTS = DIRECTORY / "scierc_planning_inputs_v0.1.0.json"
CANDIDATE = DIRECTORY / "scierc_preflight_candidate_v0.2.0.json"
PRESERVATION = DIRECTORY / "scierc_smoke_preservation_v0.1.0.json"
REPORT = DIRECTORY / "scierc_cost_runtime_preflight_v0.1.0.json"
MARKDOWN = a.PROJECT_ROOT / "docs/scierc_cost_runtime_preflight_v0.1.0.md"
TERMINAL_SHA = "92d16707867982b9f219f5f05196c82bf26d4339e07ad6ad674ba71056440861"
BINDINGS = {
    "planSha256": "905f99e9813074ccfb6b89607b436d0947deb3aa2156578dab18f267f19e631b",
    "bodySha256": "aff25959d545279da589268a9f4ce87c0aee9df0b83f60664ea92df02120dcc5",
    "runtimeSha256": "87c0050932bb1c256671ba481e5efa80d07e9f04b0c5bae1c06c4e35e71d5251",
}


def require(condition: bool, message: str) -> None:
    """Fail closed on any unexplained evidence inconsistency."""
    if not condition:
        raise ValueError(message)


def read_json(path: Path):
    """Decode existing JSON without mutating it."""
    return r._strict_json(path.read_bytes())


def encoded(value: dict) -> bytes:
    """Encode stable review artifacts."""
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n"


def evidence(path: Path) -> dict:
    """Bind local bytes without copying private paths or raw payloads."""
    raw = path.read_bytes()
    return {"path": str(path.relative_to(a.PROJECT_ROOT)), "sizeBytes": len(raw), "sha256": a.sha256_bytes(raw)}


def verify_smoke() -> dict:
    """Cross-check authentic artifacts and revalidate structure, never gold or scores."""
    root = r.RUNTIME_ROOT
    require(evidence(root / "terminal.json")["sha256"] == TERMINAL_SHA, "TERMINAL_HASH_MISMATCH")
    paths = sorted(root.iterdir())
    before = [evidence(p) for p in paths]
    plan = read_json(r.PLAN_PATH)
    require(all(plan[k] == v for k, v in BINDINGS.items()), "APPROVED_BINDING_MISMATCH")
    prepared, document, body = r.prepare_smoke()
    require(prepared == plan, "PREPARED_PLAN_MISMATCH")
    require(document.document_id == "ICCV_2003_158_abs" and not document.gold_entities and not document.gold_relations, "SOURCE_SCOPE")
    require((root / "provider_request.json").read_bytes() == body, "REQUEST_BYTES")
    approvals = a.RUNTIME_ROOT / "approvals/single_dev_smoke_v0.1.0"
    acceptance_path, authorization_path = approvals / "runtime_acceptance.json", approvals / "live_authorization.json"
    acceptance, authorization = read_json(acceptance_path), read_json(authorization_path)
    approval_evidence = [evidence(acceptance_path), evidence(authorization_path)]
    r.check_approvals(plan, root, acceptance, authorization)
    identity = read_json(root / "identity.json")
    require(identity == {"plan": plan, "acceptance": acceptance, "authorization": authorization}, "IDENTITY_APPROVALS")
    terminal, marker = read_json(root / "terminal.json"), read_json(root / "dispatch_started.json")
    require(terminal["requestID"] == marker["requestID"] == plan["requestID"], "REQUEST_ID")
    require(marker["bodySha256"] == plan["bodySha256"] and marker["maxGenerationPosts"] == 1, "MARKER_SCOPE")
    require(terminal["timeoutSeconds"] == marker["timeoutSeconds"] == 180 and not terminal["automaticRedispatch"], "DISPATCH_SETTINGS")
    require(terminal["terminalStatus"] == "completed_valid" and terminal["httpStatus"] == 200, "TERMINAL_STATUS")
    raw_response = (root / "provider_response.bin").read_bytes()
    response = r._strict_json(raw_response)
    require(read_json(root / "provider_response.json") == response, "PROVIDER_OBJECT")
    validate_provider_response(response)
    require(terminal["requestedModel"] == terminal["returnedModel"] == response["model"] == plan["settings"]["model"], "MODEL")
    require(terminal["responseID"] == response["id"] and terminal["usage"] == response["usage"], "RESPONSE_USAGE_ID")
    output = extract_model_output(response)
    require(output == (root / "raw_model_output.bin").read_bytes() == (root / "model_output_part_000.bin").read_bytes(), "OUTPUT_BYTES")
    prediction = r._strict_json(output)
    a.validate_prediction(prediction, document)
    require(prediction == read_json(root / "validated_prediction.json"), "VALIDATED_PREDICTION")
    start = datetime.fromisoformat(terminal["startedAt"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(terminal["completedAt"].replace("Z", "+00:00"))
    for approval in (acceptance, authorization):
        require(datetime.fromisoformat(approval["createdAt"].replace("Z", "+00:00")) <= start,
                "APPROVAL_AFTER_DISPATCH")
    require(marker["startedAt"] == terminal["startedAt"] and marker["monotonicStartedNs"] > 0, "START_TIME")
    require(abs((end - start).total_seconds() * 1000 - terminal["elapsedMilliseconds"]) < 10, "CLIENT_TIMING")
    require(terminal["providerCreatedAt"] == response["created_at"] and terminal["providerCompletedAt"] == response["completed_at"], "PROVIDER_TIMING")
    require(start.timestamp() <= response["created_at"] <= response["completed_at"] <= end.timestamp(), "TIME_ORDER")
    usage = response["usage"]
    require(usage["input_tokens"] + usage["output_tokens"] == usage["total_tokens"], "USAGE_TOTAL")
    require(usage["output_tokens_details"]["reasoning_tokens"] <= usage["output_tokens"], "REASONING_SUBSET")
    require(before == [evidence(p) for p in paths], "AUTHENTIC_BYTES_CHANGED")
    require(approval_evidence == [evidence(acceptance_path), evidence(authorization_path)], "APPROVAL_BYTES_CHANGED")
    return {"version": "0.1.0", "documentID": document.document_id,
        "acceptedRuntimeCommit": "285eee025376628ce323461f7079d6e1dcd82f49",
        "bindings": BINDINGS, "planFile": evidence(r.PLAN_PATH),
        "artifacts": before, "approvalFiles": approval_evidence,
        "approvalRecordIDs": [acceptance["recordID"], authorization["recordID"]],
        "approvalBindingVerification": "exact resolved designated runtimeRoot checked locally; machine-specific root is not copied here",
        "terminal": terminal, "serviceTier": response.get("service_tier"),
        "verification": {"terminalHashMatchesResearcherUpload": True, "exactRequestParity": True,
            "planAndRuntimeIdentity": True, "approvalsAndStoredIdentity": True,
            "providerObjectAndModelOutputParity": True, "structuralValidation": "valid",
            "timestampOrderAndElapsedConsistency": True, "authenticBytesUnchanged": True,
            "goldCompared": False, "benchmarkMetricsComputed": False},
        "locallyRecordedDispatchAttempts": 1, "locallyRecordedProviderResponses": 1,
        "attemptLimits": "One dispatch marker and response in this namespace; not proof of global account activity or external service internal attempts. Provider request ID is recorded only in terminal metadata; no independent HTTP-header artifact exists. Monotonic end value is not stored; UTC duration corroborates recorded elapsed time, not independent monotonic recomputation.",
        "newProviderCalls": 0, "officialTestAuthorized": False}


def price(input_tokens, writes, reads, output, rates: dict) -> float:
    """Apply mutually exclusive input categories; output already includes reasoning."""
    i, w, c, o = map(lambda v: Decimal(str(v)), (input_tokens, writes, reads, output))
    require(min(i, w, c, o) >= 0 and w + c <= i, "INVALID_PRICING_CATEGORIES")
    value = ((i-w-c)*Decimal(str(rates["ordinaryInput"])) + w*Decimal(str(rates["cacheWrite"]))
             + c*Decimal(str(rates["cacheRead"])) + o*Decimal(str(rates["outputIncludingReasoning"]))) / Decimal(1000000)
    return float(value)


def estimate_inputs(sizes: list, smoke_bytes: int, smoke_tokens: int, multiplier=1) -> list:
    """Scale complete serialized request sizes; repeated overhead is already included."""
    return [int((Decimal(n)*Decimal(smoke_tokens)*Decimal(str(multiplier))/Decimal(smoke_bytes)).to_integral_value(rounding=ROUND_CEILING)) for n in sizes]


def build_report(smoke: dict, inputs: dict) -> dict:
    """Use only candidate request-size metadata for official planning, never test gold."""
    require(evidence(CANDIDATE)["sha256"] == "d5ed3987bc19c802087b8f214f8d96f371746c3b6a45c75e14768bb357bf04a1", "PRESERVED_CANDIDATE_BYTES")
    candidate = read_json(CANDIDATE)
    unsigned = dict(candidate); claimed = unsigned.pop("manifestSha256")
    require(a.sha256_bytes(a.canonical_json(unsigned)) == claimed, "CANDIDATE_SELF_HASH")
    require(candidate["logicalRequestCount"] == len(candidate["requests"]) == 100, "OFFICIAL_COUNT")
    require(not candidate["researcherLiveAuthorization"] and not candidate["runtimeAccepted"] and not candidate["automaticRedispatch"], "CANDIDATE_BOUNDARY")
    ids = [row["documentID"] for row in candidate["requests"]]
    require(len(set(ids)) == 100 and a.sha256_bytes(a.canonical_json(sorted(ids))) == candidate["documentIDsSha256"], "MEMBERSHIP")
    plan = read_json(r.PLAN_PATH)
    for key in ("schemaSha256", "promptSha256", "configurationSha256"):
        require(candidate[key] == plan[key], "CONFIG_PARITY")
    sizes = [row["inputTokenAccounting"]["serializedRequestUtf8Bytes"] for row in candidate["requests"]]
    require(sum(sizes) == candidate["preflightAccounting"]["totalSerializedRequestUtf8Bytes"], "SIZE_TOTAL")
    usage = smoke["terminal"]["usage"]; rates = inputs["usdPerMillionTokens"]
    smoke_bytes = plan["accounting"]["completeRequestUtf8Bytes"]
    baseline = estimate_inputs(sizes, smoke_bytes, usage["input_tokens"])
    upper = estimate_inputs(sizes, smoke_bytes, usage["input_tokens"], inputs["conservativeInputMultiplier"])
    reasoning = usage["output_tokens_details"]["reasoning_tokens"]
    nonreasoning = usage["output_tokens"] - reasoning
    elapsed = smoke["terminal"]["elapsedMilliseconds"] / 1000
    scenarios = []
    for scenario in inputs["outputLatencyScenarios"]:
        factor = scenario["multiplier"]
        total_output = 100 * usage["output_tokens"] * factor
        scenarios.append({**scenario, "nonReasoningOutputTokens": 100*nonreasoning*factor,
            "reasoningTokens": 100*reasoning*factor, "totalOutputTokens": total_output,
            "inputTokensHeldAtBaseline": sum(baseline),
            "usdAllInputCacheWritesNoReads": price(sum(baseline), sum(baseline), 0, total_output, rates),
            "sequentialSeconds": 100*(elapsed*factor + scenario["extraSecondsPerRequest"])})
    cap = 100 * 32768
    require(candidate["configuredOutputCeilingTokens"] == 32768 and candidate["preflightAccounting"]["configuredOutputCeilingTokensAllLogicalRequests"] == cap, "OUTPUT_CAP")
    return {"version": "0.1.0", "status": "PLANNING ONLY — NOT AUTHORIZED FOR PROVIDER EXECUTION",
        "candidateFile": evidence(CANDIDATE), "candidateManifestSha256": claimed,
        "smokePreservationSha256": a.sha256_bytes(encoded(smoke)), "planningInputsFile": evidence(INPUTS),
        "reportingCode": evidence(Path(__file__)),
        "officialPlannedGenerationPosts": 100, "completedSmokePostsSeparate": 1,
        "newProviderCalls": 0, "automaticRedispatch": False, "concurrency": 1,
        "sourceAuthority": candidate["source"], "documentIDsSha256": candidate["documentIDsSha256"],
        "smokeStandardRateReconstructionUSD": price(usage["input_tokens"], usage["input_tokens_details"]["cache_write_tokens"], usage["input_tokens_details"]["cached_tokens"], usage["output_tokens"], rates),
        "pricingLimits": inputs["pricingBasis"], "observedServiceTier": smoke["serviceTier"],
        "inputEstimation": {"method": "ceil(each exact complete request byte size * 2116/9741); no additional prompt/schema charge",
            "compatibleLocalTokenizerEstablished": False, "exactProviderTokens": None,
            "totalRequestBytes": sum(sizes), "smokeRequestBytes": smoke_bytes,
            "promptBytesPerRequest": plan["accounting"]["repeatedPromptUtf8Bytes"],
            "schemaBytesPerRequest": plan["accounting"]["repeatedSchemaUtf8Bytes"],
            "overheadAccounting": "Prompt/schema embedded in each complete body, already counted 100 times; raw component bytes are descriptive, not additive token estimates. JSON escaping/provider serialization may change effective overhead.",
            "totalEstimatedTokens": sum(baseline), "perRequestEstimatedTokens": baseline,
            "sensitivityTotals": {str(m):sum(estimate_inputs(sizes,smoke_bytes,usage["input_tokens"],m)) for m in inputs["inputSensitivityMultipliers"]},
            "limits": "N=1 whole-request ratio is not universal. Tokenization, source length/composition and schema representation vary. No gold-derived size adjustment."},
        "outputLatencyScenarios": scenarios,
        "baselineOrdinaryInputNoCachingUSD": price(sum(baseline), 0, 0, 100*usage["output_tokens"], rates),
        "configuredOutputTokensPerRequest": 32768, "configuredOutputTokensAllRequests": cap,
        "outputCapCostAloneUSD": price(0, 0, 0, cap, rates),
        "conditionalConservativePlanning": {"inputTokens": sum(upper), "inputMultiplier": inputs["conservativeInputMultiplier"],
            "allInputCacheWritesNoReads": True, "outputTokens": cap,
            "usd": price(sum(upper), sum(upper), 0, cap, rates),
            "condition": "Holds only if actual aggregate input <= assumed doubled estimate, output <= configured ceiling, these Standard short-context rates apply, and no extra billed calls/fees. Not a guaranteed spending cap or strict total upper bound."},
        "timeAndRateLimits": {"observedClientElapsedSeconds": elapsed, "baselineSequentialSeconds": elapsed*100,
            "baselineEquivalentRPM": 60/elapsed, "baselineEquivalentActualTokenTPM": (sum(baseline)+100*usage["output_tokens"])/(100*elapsed/60),
            "largestEstimatedInputTokens": max(baseline), "largestConditionalInputPlusOutputReservation": max(upper)+32768,
            "accountRPM": None, "accountTPM": None,
            "requirements": "Confirm account limits and token-reservation rules before launch. Pace starts to actual RPM/TPM windows; a one-request token reservation may include the 32768 output ceiling. Aggregate equivalent rates do not establish rolling-window safety. Concurrency 1 alone is insufficient. No inference from ChatGPT subscription.",
            "limits": "93.691190542s is one client elapsed observation, not a population mean or pure provider latency. Baseline adds no extra startup/disk/pacing time; upper sensitivity adds 10s/request after doubling elapsed. No empirical percentile or finite wall-clock bound; 180s socket timeout is not a total request deadline."},
        "remainingRequirements": ["Researcher preflight review and explicit official-run authorization; smoke approval cannot be reused",
            "Separately implemented, offline-tested and accepted sequential 100-document dispatcher with exact membership/body binding",
            "Separate ignored runtime namespace, durable per-request claims, raw evidence and no redispatch after unknown delivery",
            "Confirm actual account pricing/tier/region, billing limits and RPM/TPM; define pacing and explicit stop/budget policy",
            "Preserve authentic smoke; do not rerun or tune prompt/schema/scoring from it"],
        "observationLimits": "One mechanically valid dev completion establishes this request traversed transport/parsing/validation. It does not establish semantic correctness, benchmark performance, 100-document validity, cache-hit reliability, token/latency distribution, service availability or account limits."}


def render(report: dict) -> str:
    """Render concise human review from the same computed report."""
    inp = report["inputEstimation"]; conservative = report["conditionalConservativePlanning"]
    rows = "\n".join(f'| {s["name"]} | {s["nonReasoningOutputTokens"]:,.0f} | {s["reasoningTokens"]:,.0f} | {s["totalOutputTokens"]:,.0f} | ${s["usdAllInputCacheWritesNoReads"]:.6f} | {s["sequentialSeconds"]/3600:.3f} |' for s in report["outputLatencyScenarios"])
    return f'''# SciERC official cost/runtime planning supplement v0.1.0

NOT AUTHORIZED FOR PROVIDER EXECUTION. Step 9 remains open; Step 8 unchanged.
Reproduce offline: `python -m src.extraction.llm.publications.scierc_cost_preflight`.
Authentic ignored runtime bytes are read-only. No launch function is invoked.

## Preserved smoke

Frozen dev line 1 `ICCV_2003_158_abs`: completed_valid, HTTP 200, gpt-5.6-sol.
Terminal SHA-256: `{TERMINAL_SHA}`. One local dispatch marker and response;
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
= **${report['smokeStandardRateReconstructionUSD']:.6f}**, not an invoice.
Cache writes replace ordinary pricing; reasoning is not charged twice.

## Separate official plan

Exactly **100 planned generation POSTs**, one per frozen test document, sequential
concurrency 1; completed smoke is separate. No automatic redispatch or extra calls.
The unchanged v0.2.0 candidate and smoke preservation file are hash-bound in the JSON.

Local tiktoken 0.3.3 has no model/prefix mapping for gpt-5.6-sol; no encoding is
loaded/downloaded. Estimated input = sum ceil(request bytes * 2116 / 9741).
The {inp['totalRequestBytes']:,} complete-request bytes already include prompt/schema
on all 100 requests (raw prompt {inp['promptBytesPerRequest']:,} and schema
{inp['schemaBytesPerRequest']:,} bytes each). Do not add their token cost again.
Baseline input **{inp['totalEstimatedTokens']:,} estimated tokens**; 0.5x/1x/2x
sensitivity: {inp['sensitivityTotals']}. These are not exact tokens. The whole-body
ratio can vary with composition, source length, escaping and provider representation.

Output and elapsed scenarios simply multiply the one observation; no inferred gold
counts or semantic adjustment. Costs below hold input at the baseline estimate and
assume every input token uses cache-write pricing, with **no guaranteed cache reads**.
Half/baseline add zero extra seconds; double scenario adds 10 seconds/request.

| Assumption | Non-reasoning | Reasoning | Total output | USD | Sequential hours |
| --- | ---: | ---: | ---: | ---: | ---: |
{rows}

Baseline ordinary-input/no-caching alternative: ${report['baselineOrdinaryInputNoCachingUSD']:.6f}.
Output cap: 32,768/request, **3,276,800 total**, output-only cost **${report['outputCapCostAloneUSD']:.6f}**.
Conditional conservative scenario: {conservative['inputTokens']:,} input tokens
(2x byte-calibrated estimate), all cache writes/no reads, plus full output cap:
**${conservative['usd']:.6f}**. This is NOT a guaranteed spending cap: input must
stay within that assumed bound, the stated rates/context tier must apply, and no
extra billed calls/fees may occur. Input uncertainty prevents a strict total bound.

Sequential arithmetic baseline: 100 * 93.691190542 =
{report['timeAndRateLimits']['baselineSequentialSeconds']:.7f}s
({report['timeAndRateLimits']['baselineSequentialSeconds']/60:.3f} minutes).
N=1 is not a population mean, confidence interval, percentile, or predictive model.
Client elapsed is not pure provider latency. Extra startup, disk, rate-limit pacing,
service slowdown and interruption can increase time. 180s is a socket-operation
timeout, not a wall-clock guarantee.

## Before any official launch

Account RPM/TPM are unknown. Baseline equivalent rates are
{report['timeAndRateLimits']['baselineEquivalentRPM']:.3f} RPM and
{report['timeAndRateLimits']['baselineEquivalentActualTokenTPM']:.1f} actual-token TPM,
not verified permitted limits. The largest conditional input plus full output
reservation is {report['timeAndRateLimits']['largestConditionalInputPlusOutputReservation']:,} tokens.
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
'''


def write_review(path: Path, raw: bytes) -> None:
    """Create a new review artifact exclusively or verify identical prior generation."""
    if path.exists():
        require(path.read_bytes() == raw, "REVIEW_ARTIFACT_CONFLICT: " + path.name)
    else:
        r._write_new(path, raw)


def main() -> None:
    """Generate only sanitized preservation/planning artifacts offline."""
    smoke = verify_smoke()
    report = build_report(smoke, read_json(INPUTS))
    write_review(PRESERVATION, encoded(smoke))
    write_review(REPORT, encoded(report))
    write_review(MARKDOWN, render(report).encode())
    print(json.dumps({"verified": True, "officialPostsPlanned": 100, "newCalls": 0,
                      "estimatedInputTokens": report["inputEstimation"]["totalEstimatedTokens"]}))


if __name__ == "__main__":
    main()
