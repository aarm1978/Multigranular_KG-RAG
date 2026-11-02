"""One local sequential command for the pinned 10,893-request Publications queue.

Offline estimate/status are read-only. --live is researcher-terminal execution;
there is no hard budget, batch preparation, model judgment or KG-writing path.
"""
from __future__ import annotations

import argparse
import ast
import base64
from copy import deepcopy
import datetime
import importlib.util
import json
from pathlib import Path
import socket
import statistics
import sys
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from . import openai_provider as provider
from . import production_acceptance as acceptance
from .request_builder import PROJECT_ROOT as ROOT, canonical_json, sha256_bytes
from .resumable_production_journal import journal_class, require, replace_atomic

V2 = ROOT / 'var/study2_step13/publication-extraction-plan/v0.2'
PARENT = V2 / 'candidate/preflight-manifest.json'
PARENT_SHA = '180ed58aed739cfafd5234170a03301f7a384325288824b080762df82ffa45e7'
RUN = ROOT / 'var/study2_step13/publications-gpt61-production/v1'
POLICY = ROOT / 'docs/study2_publications_gpt61_cost_control_clarification_v1.0.md'
PRICING = dict(inputUSDPerMillion=2, cachedUSDPerMillion=.1, cacheWriteUSDPerMillion=2.5,
               outputUSDPerMillion=10, longContextThreshold=272000,
               reference='https://developers.openai.com/api/docs/models/gpt-6.1-sol')
SAMPLE = 100
PINS = {
 'var/study2_step13/publication-paired-gpt61-smoke/v0.1/paired.py': '249386b6d166fbafb30f77321d7ce05cae1aae1de969f6d12715eaa964c88eda',
 'var/study2_step13/publication-paired-gpt61-streaming/v0.1/recover.py': '19d0ecd1ff8220a50c9fface3573bd8df13f56b5d17bc6d251fa9d2bc6ab532c',
 'var/study2_step13/publication-jit-generation-smoke/v0.1/run.py': '6ed051c6212e9455366386c3c6541ad9341c6641a4625c925ca7a73cab33fa11',
 'var/study2_step13/publication-paired-gpt61-streaming/v0.1/consolidated-018142.json': '9eb06c4d45d4c952690240d397313d4691d27f5b258787c69fa8f03ed8469f36',
}


def read(path: Path) -> Any:
    """Read local JSON without printing source material or secrets."""
    return json.loads(path.read_bytes())


def load_module(name: str, path: Path) -> Any:
    """Import a previously hash-verified existing local implementation."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dependencies() -> tuple[Any, Any, Any, dict[str, Any]]:
    """Verify the pinned preflight/generators; never replay diagnostic response journals."""
    require(sha256_bytes(PARENT.read_bytes()) == PARENT_SHA, 'PARENT_PREFLIGHT_DRIFT')
    for relative, digest in PINS.items():
        require(sha256_bytes((ROOT / relative).read_bytes()) == digest, 'LOCAL_DEPENDENCY_DRIFT:' + relative)
    paired = load_module('production_paired_adapter', ROOT / next(p for p in PINS if p.endswith('/paired.py')))
    baseline = load_module('production_module_loader', ROOT / next(p for p in PINS if p.endswith('/run.py')))
    stream, journal, _ = baseline.modules()
    parent = stream.load_manifest(PARENT, PARENT_SHA)
    require(len(parent['requests']) == 10893, 'QUEUE_COUNT_DRIFT')
    return paired, stream, journal, parent


def estimate(parent: dict[str, Any]) -> dict[str, Any]:
    """Reprice each original scenario from token estimates; use observed GPT-6.1 latency."""
    totals = {k: 0.0 for k in ('low', 'pooled', 'high', 'outputCeiling')}
    for entry in parent['requests']:
        cost = entry['cost']
        for scenario in totals:
            ik = 'high' if scenario == 'outputCeiling' else scenario
            ok = 'ceiling' if scenario == 'outputCeiling' else scenario
            tokens = cost['inputTokenEstimates'][ik]
            mi, mo = (2, 1.5) if tokens > 272000 else (1, 1)
            totals[scenario] += (tokens * 2.5 * mi + cost['outputTokenScenarios'][ok] * 10 * mo) / 1e6
    diagnostic = read(ROOT / next(p for p in PINS if p.endswith('/consolidated-018142.json')))
    durations = [a['summary']['durationSeconds'] for row in diagnostic['rows'] for a in row['attempts']
                 if a['summary'].get('durationSeconds') is not None]
    mean, median = statistics.mean(durations), statistics.median(durations)
    return dict(requests=len(parent['requests']), pricing=PRICING, costUSD=totals,
                observedLatencySamples=len(durations), meanSeconds=mean, medianSeconds=median,
                sequentialMeanHours=mean * len(parent['requests']) / 3600,
                sequentialMedianHours=median * len(parent['requests']) / 3600,
                assumption='Pinned four-request output/token scenarios repriced at GPT-6.1 cache-write input and standard output rates; no assumed cache savings or retries. Diagnostic 14-request GPT-6.1 latency subset; missing durations excluded. Not a billing maximum or confidence interval; native processing, retries and rate limits add time.',
                diagnosticResultsReusedAsProduction=False, concurrency=1, meaningfulSampleRequests=SAMPLE)


def model_variant(p: dict[str, Any], paired: Any) -> dict[str, Any]:
    """Reuse model-only adapter, then bind streaming and actual production lineage."""
    q = paired.adapt(p)
    q['binding'].pop('pairedModelProvenance')
    q['body']['stream'] = True
    q['binding']['providerEnvelopeSha256'] = sha256_bytes(canonical_json(q['body']))
    q['binding']['productionModelProvenance'] = dict(model='gpt-6.1-sol', parentPreflightSha256=PARENT_SHA,
        baselineBindingSha256=sha256_bytes(canonical_json(p['binding'])),
        baselineBodySha256=sha256_bytes(canonical_json(p['body'])), semanticRequestUnchanged=True)
    return q


def verify_variant(p: dict[str, Any], entry: dict[str, Any], stream: Any) -> None:
    """Invert only provider/transport metadata and verify the exact historical fingerprint."""
    require(p['body']['model'] == 'gpt-6.1-sol' and p['body']['stream'] is True, 'MODEL_OR_STREAM_DRIFT')
    q = deepcopy(p)
    provenance = q['binding'].pop('productionModelProvenance')
    require(provenance['parentPreflightSha256'] == PARENT_SHA and provenance['semanticRequestUnchanged'] is True, 'MODEL_LINEAGE_DRIFT')
    require(q['binding']['providerEnvelopeSha256'] == sha256_bytes(canonical_json(q['body'])), 'PROVIDER_BINDING_DRIFT')
    q['body'].pop('stream')
    q['body']['model'] = 'gpt-5.6-sol'
    q['binding']['providerEnvelopeSha256'] = sha256_bytes(canonical_json(q['body']))
    require(sha256_bytes(canonical_json(q['body'])) == provenance['baselineBodySha256'] and
            sha256_bytes(canonical_json(q['binding'])) == provenance['baselineBindingSha256'], 'BASELINE_LINEAGE_DRIFT')
    require(stream.fingerprint(q) == entry['identity'], 'FROZEN_REQUEST_FINGERPRINT_DRIFT')


class NeedRetry(Exception):
    """The original native controller requested its second technical attempt."""


def process_native(p: dict[str, Any], response: dict[str, Any], number: int,
                   first: dict[str, Any] | None, paired: Any, stream: Any) -> dict[str, Any]:
    """Run the original model-correct parser/binder/validators and acceptance controller."""
    _, _, validate, _, _, runner = paired.native_adapter(stream, provider)
    used = []
    captured = []

    def controller(attempt: Any) -> Any:
        """Observe native attempt records without changing their classification or selection."""
        def observe(n: int) -> Any:
            value = attempt(n)
            captured.append(value)
            return value
        return acceptance.run_attempt_controller(observe)

    def recorded(body: dict[str, Any], budget: int) -> dict[str, Any]:
        """Supply only this persisted response; a second callback cannot contact a provider."""
        require(body == p['body'] and budget == 32768, 'NATIVE_DISPATCH_IDENTITY_DRIFT')
        if used:
            raise NeedRetry()
        used.append(True)
        try:
            validate(response['providerResponse'])
        except ValueError as exc:
            raise provider.OpenAIProviderResponseError(str(exc), response['providerResponse'], response['providerMetadata']) from None
        raw = response['rawModelOutputBase64']
        if raw is None:
            raise provider.OpenAIProviderResponseError('MODEL_OUTPUT_UNAVAILABLE', response['providerResponse'], response['providerMetadata'])
        return dict(rawOutput=base64.b64decode(raw, validate=True), providerMetadata=response['providerMetadata'],
                    providerResponse=response['providerResponse'])

    runner = paired.rebind(runner, run_attempt_controller=controller)
    try:
        result = runner(p, recorded, initial_attempt=first)
    except NeedRetry:
        require(number == 1 and len(captured) == 1, 'RETRY_STATE_DRIFT')
        return dict(attempt=captured[0], retryEligible=True, processable=False, productionResult=None)
    selected = result['attemptSelection']['selectedAttemptNumber']
    processable = selected is not None
    if processable:
        attempt = next(a for a in result['attemptSelection']['attempts'] if a['attemptNumber'] == selected)
        validation = attempt['validation']
        processable = (validation.get('envelopeStatus') not in ('invalid', 'processing_failed') and
                       not any(f.get('severity') == 'error' for f in validation.get('globalFindings', [])))
    return dict(attempt=captured[-1], retryEligible=False, processable=processable, productionResult=result)


def verify_outcome(p: dict[str, Any], response: dict[str, Any], outcome: dict[str, Any], number: int) -> None:
    """Check stored provenance/hashes cheaply; never rerun thousands of completed validations."""
    attempt = outcome['attempt']
    require(attempt['attemptNumber'] == number and attempt['requestedModel'] == 'gpt-6.1-sol' and
            attempt['requestInputSha256'] == p['request']['requestInputSha256'], 'NATIVE_ATTEMPT_IDENTITY_DRIFT')
    if attempt['status'] == 'processed':
        require(attempt['providerResponseSha256'] == sha256_bytes(canonical_json(response['providerResponse'])) and
                attempt['rawOutputSha256'] == sha256_bytes(base64.b64decode(response['rawModelOutputBase64'], validate=True)), 'NATIVE_RESPONSE_BINDING_DRIFT')
    if outcome['retryEligible']:
        require(number == 1 and not acceptance._is_processable(attempt) and
                acceptance._retry_processing_code(attempt) is not None, 'NON_NATIVE_RETRY')
    if outcome['processable']:
        result = outcome['productionResult']
        require(result['attemptSelection']['selectedAttemptNumber'] == number and
                result['acceptedSemanticProjection'] == acceptance.derive_accepted_semantic_projection(result['attemptSelection'], p['request']), 'ACCEPTANCE_PROJECTION_DRIFT')


def transport_functions(paired: Any) -> Any:
    """Reuse exact proven streaming helpers without importing diagnostic controllers."""
    path = ROOT / next(p for p in PINS if p.endswith('/recover.py'))
    selected = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in ('stamp', 'unique', 'consume', 'transport')]
    require(len(selected) == 4, 'STREAM_IMPLEMENTATION_DRIFT')
    namespace = dict(datetime=datetime, time=time, socket=socket, json=json, require=require, a=paired)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(**namespace)


def response_record(response: dict[str, Any], p: dict[str, Any], paired: Any, elapsed: float | None) -> dict[str, Any]:
    """Preserve terminal response and usage before native parsing, including incomplete output."""
    try:
        raw = provider.extract_model_output(response)
    except provider.OpenAIProviderError:
        raw = None
    metadata = provider.provider_response_record(response, p['body'], raw, execution_mode='streaming')
    return dict(providerResponse=response, usage=response.get('usage'), providerMetadata=metadata,
                rawModelOutputBase64=base64.b64encode(raw).decode() if raw is not None else None,
                cost=paired.usage_cost(response, PRICING), pricing=PRICING, elapsedSeconds=elapsed)


def anomaly(log: Any) -> bool:
    """Use only actual usage-priced attempts versus distinct processed request estimates."""
    return len(log.costed_requests) >= log.manifest['meaningfulSampleRequests'] and log.spent > 2 * log.estimated_processed


def progress(log: Any) -> dict[str, Any]:
    """Return compact live/restart progress and transparent cost uncertainty."""
    completed = sum(state == 'completion' for state in log.state.values())
    return dict(completed=completed, remaining=len(log.entries) - completed,
                cumulativeUsagePricedUSD=log.spent, estimatedProcessedUSD=log.estimated_processed,
                unknownUsageAttempts=len(log.unknown_usage), costAnomalyStop=anomaly(log),
                elapsedSeconds=0 if log.started_at is None else time.time() - log.started_at)


def execute(log: Any, entries: list[dict[str, Any]], rebuild: Any, transport: Any,
            process: Any, record_response: Any, bundle: Any, fingerprint: Any,
            prepare_dispatch: Any = None) -> None:
    """Sequential JIT traversal; restart recovers persisted responses and never repeats completion."""
    for entry in entries:
        rid = entry['identity']['requestID']
        if log.state.get(rid) == 'completion':
            continue
        if rid not in log.state:
            require(not log.unknown_usage, 'UNKNOWN_BILLING_STOP')
            if anomaly(log):
                print('COST_ANOMALY_STOP', json.dumps(progress(log)), flush=True)
                return
            p = rebuild(entry)
            data = bundle(p)
            data['executionIdentity'] = fingerprint(p)
            log.append('prepared', rid, data)
        p = log.prepared(rid)
        while log.state[rid] != 'completion':
            state = log.state[rid]
            number = max(1, log.number(rid))
            if state in ('prepared', 'retry'):
                require(not log.unknown_usage, 'UNKNOWN_BILLING_STOP')
                if anomaly(log):
                    print('COST_ANOMALY_STOP', json.dumps(progress(log)), flush=True)
                    return
                number = 2 if state == 'retry' else 1
                if prepare_dispatch is not None:
                    prepare_dispatch()
                log.append('dispatch_intent', rid, dict(identity=fingerprint(p), unixTime=time.time()), number)
                print('DISPATCH', rid, 'attempt', number, json.dumps(progress(log)), flush=True)
                try:
                    transport(log, rid, p['body'])
                except Exception:
                    # The proven SSE transport retains terminal evidence before raising.
                    if 'terminal' not in log.attempt_context(rid, number):
                        raise ValueError('UNCERTAIN_DISPATCH_STOP_NO_TERMINAL_EVIDENCE') from None
                state = log.state[rid]
            if state == 'dispatch_intent':
                context = log.attempt_context(rid, number)
                terminal = context.get('terminal')
                require(terminal is not None and isinstance(terminal.get('terminalEvent', {}).get('response'), dict),
                        'UNCERTAIN_DISPATCH_STOP_NO_TERMINAL_EVIDENCE')
                require(not (terminal['terminalEvent'].get('type') == 'response.completed' and
                             'transport_failure' in context), 'COMPLETED_STREAM_VALIDATION_FAILURE_STOP')
                response = terminal['terminalEvent']['response']
                record = record_response(response, p, terminal.get('elapsedSeconds'))
                record['cumulativeUsagePricedUSD'] = log.spent + (record['cost']['estimatedUSD'] or 0)
                log.append('response', rid, record, number)
                state = 'response'
            if state == 'response':
                context = log.attempt_context(rid, number)
                response = context['response']
                require(response['providerResponse'].get('service_tier') == 'default', 'UNPLANNED_SERVICE_TIER_STOP')
                require(response['providerResponse'].get('model') == 'gpt-6.1-sol', 'RETURNED_MODEL_STOP')
                require(response['cost']['estimatedUSD'] is not None, 'UNKNOWN_USAGE_STOP')
                first = log.attempt_context(rid, 1)['native_outcome']['attempt'] if number == 2 else None
                outcome = process(p, response, number, first)
                log.append('native_outcome', rid, outcome, number)
                state = 'native_outcome'
            if state == 'native_outcome':
                outcome = log.attempt_context(rid, number)['native_outcome']
                if outcome['retryEligible']:
                    log.append('retry', rid, dict(reason='existing_native_bounded_technical_retry'), number)
                else:
                    require(outcome['processable'], 'NATIVE_TERMINAL_PROCESSING_FAILURE_STOP')
                    log.append('completion', rid, dict(nativeOutcomeSha256=sha256_bytes(canonical_json(outcome)), identity=fingerprint(p),
                                                      cumulativeUsagePricedUSD=log.spent), number)
                    print('COMPLETE', rid, json.dumps(progress(log)), flush=True)


def runtime_manifest(parent: dict[str, Any], stream: Any) -> dict[str, Any]:
    """Pin one compact queue manifest; derive model-specific body identities lazily."""
    entries = []
    for e in parent['requests']:
        inputs = e['cost']['inputTokenEstimates']['pooled']
        outputs = e['cost']['outputTokenScenarios']['pooled']
        mi, mo = (2, 1.5) if inputs > 272000 else (1, 1)
        entries.append(dict(identity=e['identity'], sourceUnitID=e['sourceUnitID'], passIdentity=e['passIdentity'],
                            estimatedCostUSD=(inputs * 2.5 * mi + outputs * 10 * mo) / 1e6))
    from . import resumable_production_journal
    pins = {str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in (Path(__file__), Path(resumable_production_journal.__file__), POLICY)}
    return dict(version='publications-gpt61-production/1.0.0', parentPreflightSha256=PARENT_SHA,
                generatorPins=stream.versions(), implementationPins=pins, localAdapterPins=PINS,
                executionJournalPath=str((RUN / 'execution.jsonl').relative_to(ROOT)), requests=entries,
                model='gpt-6.1-sol', pricing=PRICING, meaningfulSampleRequests=SAMPLE,
                kgAuthorized=False, diagnosticResultsImported=False, maximumAttemptsPerRequest=2)


def main() -> None:
    """Estimate/status remain offline; the same --live command starts or resumes the full queue."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--estimate', action='store_true')
    modes.add_argument('--status', action='store_true')
    modes.add_argument('--live', action='store_true')
    args = parser.parse_args()
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_PREFLIGHT')):
        paired, stream, journal, parent = dependencies()
        manifest = runtime_manifest(parent, stream)
    if args.estimate:
        print(json.dumps(estimate(parent), indent=2))
        return
    data = canonical_json(manifest) + b'\n'
    path = RUN / 'run-manifest.json'
    if not path.exists():
        if args.status:
            print(json.dumps(dict(completed=0, remaining=10893, cumulativeUsagePricedUSD=0, elapsedSeconds=0, initialized=False)))
            return
        RUN.mkdir(parents=True, exist_ok=True)
        # The journal lock below serializes initialization, too.
    Journal = journal_class(journal, lambda p, e: verify_variant(p, e, stream), verify_outcome)
    log = Journal(RUN / 'execution.jsonl', data, sha256_bytes(data))
    if args.status:
        require(path.read_bytes() == data, 'RUNTIME_MANIFEST_DRIFT')
        require(log.path.exists(), 'MISSING_JOURNAL_WITH_RUN_MANIFEST')
        # An atomic checkpoint permits status while the live process owns the writer lock.
        snapshot = read(log.checkpoint)
        summary = snapshot['summary']
        require(sha256_bytes(canonical_json(summary)) == snapshot['summarySha256'], 'STATUS_CHECKSUM_DRIFT')
        summary.update(remaining=summary['total'] - summary['completed'],
                       elapsedSeconds=0 if summary['startedAt'] is None else time.time() - summary['startedAt'],
                       checkpointSnapshot=True,
                       costAnomalyStop=summary['costedRequests'] >= SAMPLE and summary['cumulativeUsagePricedUSD'] > 2 * summary['estimatedProcessedUSD'])
        print(json.dumps(summary, indent=2))
        return
    if path.exists():
        require(path.read_bytes() == data, 'RUNTIME_MANIFEST_DRIFT')
    with log:
        if path.exists():
            require(path.read_bytes() == data, 'RUNTIME_MANIFEST_DRIFT')
        else:
            replace_atomic(path, data)
        with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_JIT_CONTEXT')):
            env, routing = stream.load()
        rows = {r['sourceUnitID']: r for r in routing['records']}
        entries = {e['identity']['requestID']: e for e in parent['requests']}
        streaming = transport_functions(paired)
        key = None

        def rebuild(entry: dict[str, Any]) -> dict[str, Any]:
            """Construct just the next original request through the pinned JIT builder."""
            with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_JIT')):
                stream.load_manifest(PARENT, PARENT_SHA)
                row = rows[entry['sourceUnitID']]
                menu = next(m for m in row['menus'] if m['passIdentity'] == entry['passIdentity'])
                original = stream.reconstruct(env, row, menu, entries[entry['identity']['requestID']])
                p = model_variant(original, paired)
                verify_variant(p, entry, stream)
                stream.old.native._SCHEMA_CACHE.clear()
                return p

        def prepare_dispatch() -> None:
            """Check local credentials before recording an uncertain external dispatch."""
            nonlocal key
            if key is None:
                key = provider.load_openai_api_key()

        def transport(active: Any, rid: str, body: dict[str, Any]) -> Any:
            """Use the existing streaming transport after durable dispatch intent."""
            return streaming.transport(provider, active, rid, key, body)

        def process(p: dict[str, Any], r: dict[str, Any], n: int, first: Any) -> dict[str, Any]:
            """Recheck authorities before every new or recovered native processing outcome."""
            with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NATIVE_PROCESSING')):
                stream.load_manifest(PARENT, PARENT_SHA)
                return process_native(p, r, n, first, paired, stream)

        execute(log, manifest['requests'], rebuild, transport, process,
                lambda r, p, elapsed: response_record(r, p, paired, elapsed), journal.bundle, stream.fingerprint,
                prepare_dispatch)
        print(json.dumps(progress(log), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print('STOP:', str(error), file=sys.stderr)
        raise SystemExit(1)
