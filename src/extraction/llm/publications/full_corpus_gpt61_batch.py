"""Unattended, resumable GPT-6.1 Batch execution of independent frozen Publications requests."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import json
import math
from pathlib import Path
import socket
import sys
import time
from typing import Any
from unittest.mock import patch

from . import full_corpus_gpt61_production as baseline
from . import batch_transport
from .batch_journal import batch_journal, TERMINAL
from .resumable_production_journal import require, replace_atomic
from .request_builder import canonical_json, sha256_bytes, PROJECT_ROOT as ROOT

RUN = ROOT / 'var/study2_step13/publications-gpt61-batch/v1'
CHECK = ROOT / 'var/study2_step13/publications-gpt61-batch/compatibility-v1'
POLICY = ROOT / 'docs/study2_publications_gpt61_batch_v1.0.md'
PRICING = {**baseline.PRICING, 'inputUSDPerMillion': 1, 'cachedUSDPerMillion': .05,
           'cacheWriteUSDPerMillion': 1.25, 'outputUSDPerMillion': 5,
           'reference': 'https://developers.openai.com/api/docs/pricing', 'transport': 'batch'}
MAX_BYTES = 190_000_000  # Below the documented 200 MB limit, in decimal bytes.
MAX_REQUESTS = 50_000
SAMPLE = 100


def variant(original: dict, paired: Any) -> dict:
    """Remove only streaming; retain exact model-adapted scientific request content."""
    p = baseline.model_variant(original, paired)
    p['body'].pop('stream')
    p['binding']['providerEnvelopeSha256'] = sha256_bytes(canonical_json(p['body']))
    p['binding']['productionModelProvenance']['transport'] = 'batch/non-streaming'
    return p


def verify_variant(p: dict, entry: dict, stream: Any) -> None:
    """Invert transport metadata and reuse the original frozen fingerprint verifier."""
    require('stream' not in p['body'] and p['binding']['productionModelProvenance']['transport'] == 'batch/non-streaming', 'BATCH_TRANSPORT_DRIFT')
    require(p['binding']['providerEnvelopeSha256'] == sha256_bytes(canonical_json(p['body'])), 'BATCH_BINDING_DRIFT')
    q = deepcopy(p)
    q['body']['stream'] = True
    q['binding']['providerEnvelopeSha256'] = sha256_bytes(canonical_json(q['body']))
    baseline.verify_variant(q, entry, stream)


def input_line(p: dict, number: int, fingerprint: Any) -> tuple[dict, bytes]:
    """One line is exactly one original request; attempts get distinct exact IDs."""
    identity = fingerprint(p)
    cid = sha256_bytes(canonical_json(dict(identity=identity, attempt=number, transport='batch-v1')))
    item = dict(rid=p['request']['requestID'], number=number, custom_id=cid, identity=identity)
    return item, canonical_json(dict(custom_id=cid, method='POST', url='/v1/responses', body=p['body'])) + b'\n'


def response_record(row: dict, p: dict, paired: Any, batch_id: str, number: int) -> dict:
    """Retain authentic per-request wrapper, body, usage and cost without inventing output."""
    wrapper = row.get('response') or {}
    body = wrapper.get('body')
    raw, metadata, metadata_error = None, None, None
    cost = dict(estimatedUSD=None, basis='unknown_error_usage')
    if isinstance(body, dict) and 'usage' in body:
        try:
            raw = baseline.provider.extract_model_output(body)
        except baseline.provider.OpenAIProviderError:
            pass
        cost = paired.usage_cost(body, PRICING)
        try:
            metadata = baseline.provider.provider_response_record(body, p['body'], raw, execution_mode='batch')
        except baseline.provider.OpenAIProviderError:
            metadata_error = 'INVALID_PROVIDER_METADATA'
    elif row.get('response') is None and (row.get('error') or {}).get('code') == 'batch_expired':
        cost = dict(estimatedUSD=0.0, basis='provider_explicitly_not_executed')
    return dict(row=row, batchID=batch_id, number=number, providerResponse=body,
                providerMetadata=metadata, metadataError=metadata_error,
                usage=body.get('usage') if isinstance(body, dict) else None,
                rawModelOutputBase64=base64.b64encode(raw).decode() if raw is not None else None,
                cost=cost, pricing=PRICING)


def native_process(p: dict, receipt: dict, n: int, first: Any, paired: Any, stream: Any) -> dict:
    """Reuse native retries for known API/processing failures; unknown billing remains held."""
    row, body = receipt['row'], receipt['providerResponse']
    if receipt['cost']['estimatedUSD'] is None:
        return dict(processable=False, retryEligible=False, transportHold='UNKNOWN_USAGE', productionResult=None)
    if body is not None:
        if (row.get('response') or {}).get('status_code') == 200 and row.get('error') is None:
            if receipt['metadataError']:
                return dict(processable=False, retryEligible=False, transportHold=receipt['metadataError'], productionResult=None)
            require(body.get('model') == 'gpt-6.1-sol' and body.get('service_tier') in ('default', 'batch'), 'BATCH_MODEL_OR_TIER_DRIFT')
            return baseline.process_native(p, receipt, n, first, paired, stream)
    else:
        require((row.get('error') or {}).get('code') == 'batch_expired', 'UNRESOLVED_BATCH_ERROR')
    *_, runner = paired.native_adapter(stream, baseline.provider)
    captured, used = [], []

    def controller(attempt: Any) -> dict:
        """Observe the existing two-attempt controller without selecting a new policy."""
        def observe(number: int) -> dict:
            result = attempt(number)
            captured.append(result)
            return result
        return baseline.acceptance.run_attempt_controller(observe)

    def recorded(body: dict, budget: int) -> None:
        """Represent a known billed API error or explicit expiration as a native exception."""
        require(body == p['body'] and budget == 32768, 'NATIVE_REQUEST_DRIFT')
        if used:
            raise baseline.NeedRetry()
        used.append(True)
        raise baseline.provider.OpenAIHTTPError(dict(httpStatus=(row.get('response') or {}).get('status_code'),
                                                     batchID=receipt['batchID'], batchResult=row))

    try:
        result = paired.rebind(runner, run_attempt_controller=controller)(p, recorded, initial_attempt=first)
    except baseline.NeedRetry:
        require(n == 1 and len(captured) == 1, 'NATIVE_RETRY_DRIFT')
        return dict(attempt=captured[0], processable=False, retryEligible=True, productionResult=None)
    return dict(attempt=captured[-1], processable=False, retryEligible=False, productionResult=result)


def verify_outcome(p: dict, receipt: dict, outcome: dict, n: int) -> None:
    """Keep native projection/provenance validation and explicit transport holds separate."""
    if 'transportHold' in outcome:
        require(not outcome['processable'] and not outcome['retryEligible'] and
                (receipt['cost']['estimatedUSD'] is None or receipt.get('metadataError') or (receipt['row'].get('response') or {}).get('status_code') != 200
                 or receipt['row'].get('error') is not None), 'UNJUSTIFIED_TRANSPORT_HOLD')
    else:
        baseline.verify_outcome(p, receipt, outcome, n)


def estimate(parent: dict, limit: int | None = None) -> dict:
    """Half-price original token scenarios, with capacity-dependent waves rather than an SLA."""
    costs = {key: value / 2 for key, value in baseline.estimate(parent)['costUSD'].items()}
    tokens = sum(e['cost']['inputTokenEstimates']['pooled'] for e in parent['requests'])
    return dict(requests=len(parent['requests']), pricing=PRICING, costUSD=costs,
                estimatedInputTokens=tokens, queuedTokenLimit=limit,
                approximateCapacityWaves=math.ceil(tokens / limit) if limit else None,
                assumptions='No cache savings/retries; conservative 30m cache-write input pricing. Count exact schema-aware input tokens JIT in the researcher terminal. One-request compatibility and 100-request measured ramp precede scaling; each batch has its own 24h window. Corpus ETA depends on account capacity, actual batch latency, JIT/token counting, native processing and retries; no corpus-wide 24h promise.')


def summary(log: Any) -> dict:
    """Report observed spend honestly: uncategorized cache usage is a conservative estimate."""
    complete = sum(s == 'completion' for s in log.state.values())
    failed = sum(s == 'failed' for s in log.state.values())
    outstanding = [log.job(j, 'submitted')['id'] for j, ev in log.jobs.items() if 'submitted' in ev and 'settled' not in ev]
    unpriced = sum(key not in log.receipts for key, (jid, _) in log.assignments.items()
                   if 'submitted' in log.jobs[jid])
    elapsed = time.time() - log.started_at if log.started_at else 0
    return dict(completed=complete, failed=failed, pending=len(log.entries)-complete-failed,
                operationalQueueCapacity=log.queue_capacity,
                initialOperationalQueueCapacity=log.manifest['queuedTokenLimit'],
                expectedTotalUSD=sum(e['estimatedCostUSD'] for e in log.entries.values()),
                cumulativeUsagePricedUSD=log.spent, actualFullyCategorizedUSD=log.exact_cost,
                actualUSD=log.spent if not log.conservative_costs and not log.unknown_usage else None,
                conservativeCostAttempts=log.conservative_costs, unknownUsageAttempts=len(log.unknown_usage),
                submittedAttemptsAwaitingUsage=unpriced,
                correspondingEstimatedUSD=log.estimated_processed, costAnomalyStop=baseline.anomaly(log),
                outstandingBatchIDs=outstanding, reservedInputTokens=log.reserved_tokens(),
                elapsedSeconds=elapsed, observedRequestsPerHour=complete * 3600 / elapsed if elapsed else None)


def save_status(log: Any) -> dict:
    """Publish a compact atomic status snapshot without locking out read-only status."""
    result = summary(log)
    result.update(journalSeq=log.seq, journalHead=log.head, observedAt=time.time(), startedAt=log.started_at)
    replace_atomic(log.path.parent / 'status.json', canonical_json(dict(summary=result,
                   sha256=sha256_bytes(canonical_json(result)))) + b'\n')
    print(json.dumps(result), flush=True)
    return result


def check_batch_binding(log: Any, jid: str, remote: dict) -> None:
    """Match a recovered job to the exact locally intended file and metadata."""
    require(remote['input_file_id'] == log.job(jid, 'uploaded')['id'] and
            remote.get('metadata') == log.job(jid, 'submit_intent')['metadata'] and
            remote.get('endpoint') == '/v1/responses', 'RECOVERED_BATCH_BINDING_DRIFT')


def submit(log: Any, jid: str, api: Any) -> bool:
    """Reconcile durable POST intents; never repeat an uncertain upload or submission."""
    ev = log.jobs[jid]
    plan = log.job(jid, 'plan')
    if 'submit_intent' not in ev:
        own_ids = {log.job(j, 'submitted')['id'] for j, events in log.jobs.items() if 'submitted' in events}
        if any(b['status'] not in TERMINAL and b['id'] not in own_ids for b in api.listing('batches')):
            return False
    path = log.path.parent / plan['filename']
    require(sha256_bytes(path.read_bytes()) == plan['sha256'], 'SEALED_INPUT_DRIFT')
    if 'uploaded' not in ev:
        if 'upload_intent' in ev:
            matches = [f for f in api.listing('files') if f['filename'] == path.name and f['bytes'] == plan['bytes']]
            require(len(matches) == 1, 'UNCERTAIN_UPLOAD_STOP; no unique remote file, no blind reupload')
            uploaded = matches[0]
            require(sha256_bytes(api.content(uploaded['id'])) == plan['sha256'], 'REMOTE_INPUT_HASH_DRIFT')
        else:
            log.append('upload_intent', jid, dict(filename=path.name, sha256=plan['sha256']))
            uploaded = api.upload(path)
        require(uploaded['filename'] == path.name and uploaded['bytes'] == plan['bytes'], 'UPLOAD_BINDING_DRIFT')
        log.append('uploaded', jid, uploaded)
    if 'submitted' not in ev:
        if 'submit_intent' in ev:
            matches = [b for b in api.listing('batches') if b.get('metadata') == log.job(jid, 'submit_intent')['metadata']]
            require(len(matches) == 1, 'UNCERTAIN_SUBMISSION_STOP; no unique remote batch, no blind resubmit')
            submitted = matches[0]
        else:
            require(not log.unknown_usage and not baseline.anomaly(log), 'COST_OR_USAGE_STOP')
            metadata = dict(run=log.pin, job=jid, input_sha256=plan['sha256'])
            log.append('submit_intent', jid, dict(metadata=metadata, unixTime=time.time()))
            submitted = api.create(log.job(jid, 'uploaded')['id'], metadata)
        check_batch_binding(log, jid, submitted)
        log.append('submitted', jid, submitted)
    return True


def download(log: Any, jid: str, remote: dict, api: Any) -> None:
    """Save both exact result files before parsing any rows or issuing any retry."""
    files = []
    for kind in ('output_file_id', 'error_file_id'):
        fid = remote.get(kind)
        if not fid:
            continue
        name = jid + '-' + kind + '.jsonl'
        data = api.content(fid)
        path = log.path.parent / name
        if path.exists():
            require(path.read_bytes() == data, 'REMOTE_RESULT_FILE_DRIFT')
        else:
            replace_atomic(path, data)
        files.append(dict(kind=kind, id=fid, filename=name, sha256=sha256_bytes(data)))
    log.append('downloads', jid, dict(files=files))


def reconcile_results(log: Any, jid: str, process: Any, record: Any) -> None:
    """Validate all custom IDs before applying any outcomes; partial jobs retain all evidence."""
    plan = log.job(jid, 'plan')
    expected = {i['custom_id']: i for i in plan['items']}
    rows = {}
    for file in log.job(jid, 'downloads')['files']:
        data = (log.path.parent / file['filename']).read_bytes()
        require(sha256_bytes(data) == file['sha256'], 'RESULT_FILE_HASH_DRIFT')
        for line in data.splitlines():
            row = batch_transport.decode(line)
            cid = row['custom_id']
            require(cid in expected and cid not in rows, 'UNKNOWN_OR_DUPLICATE_CUSTOM_ID')
            rows[cid] = row
    batch_id = log.job(jid, 'submitted')['id']
    # Persist every available response before native processing or missing-result STOP.
    for cid, row in rows.items():
        i = expected[cid]
        key = i['rid'], i['number']
        receipt = record(row, log.prepared(i['rid']), batch_id, i['number'])
        if key in log.receipts:
            require(receipt == log.payload_at(log.receipts[key]), 'PERSISTED_RESULT_DRIFT')
        else:
            log.append('receipt', i['rid'], receipt, i['number'])
    for cid in sorted(rows):
        i = expected[cid]
        rid, n = i['rid'], i['number']
        if (rid, n) in log.outcomes:
            continue
        receipt = log.payload_at(log.receipts[rid, n])
        first = log.payload_at(log.outcomes[rid, 1])['native']['attempt'] if n == 2 else None
        outcome = process(log.prepared(rid), receipt, n, first)
        log.append('outcome', rid, dict(number=n, receiptSha256=sha256_bytes(canonical_json(receipt)), native=outcome), n)
    require(set(rows) == set(expected), 'MISSING_BATCH_RESULTS_STOP; persisted partial results, no inferred retry')
    require(log.job(jid, 'snapshot')['status'] in ('completed', 'expired'), 'FAILED_OR_CANCELLED_BATCH_STOP')
    if 'settled' not in log.jobs[jid]:
        log.append('settled', jid, dict(resultCount=len(rows)))


def make_job(log: Any, api: Any, rebuild: Any, native: Any, fingerprint: Any,
             capacity: int, count_limit: int, allowed: set | None = None) -> str | None:
    """JIT-build only the next capacity-bounded file, preserving each complete request."""
    items, lines, size, tokens = [], [], 0, 0
    for rid, entry in log.entries.items():
        if allowed is not None and rid not in allowed:
            continue
        state = log.state.get(rid)
        if state not in (None, 'prepared', 'retry'):
            continue
        if state is None:
            log.append('prepared', rid, native.bundle(rebuild(entry)))
        p = log.prepared(rid)
        if rid not in log.tokens:
            counted = api.count(p['body'])
            log.append('token_count', rid, dict(provider=counted, bodySha256=fingerprint(p)['bodySha256']))
        n = 2 if log.state[rid] == 'retry' else 1
        item, line = input_line(p, n, fingerprint)
        require(log.tokens[rid] <= log.queue_capacity, 'SINGLE_REQUEST_EXCEEDS_OPERATIONAL_QUEUE_CAPACITY')
        require(len(line) <= MAX_BYTES, 'SINGLE_REQUEST_EXCEEDS_FILE_LIMIT')
        if tokens + log.tokens[rid] > capacity or size + len(line) > MAX_BYTES:
            break
        items.append(item)
        lines.append(line)
        tokens += log.tokens[rid]
        size += len(line)
        if len(items) >= min(MAX_REQUESTS, count_limit):
            break
    if not items:
        return None
    data = b''.join(lines)
    digest = sha256_bytes(data)
    jid = 'job-%06d' % (len(log.jobs) + 1)
    filename = 'pub-' + log.pin[:16] + '-' + digest + '.jsonl'
    path = log.path.parent / filename
    if path.exists():
        require(path.read_bytes() == data, 'BATCH_INPUT_DRIFT')
    else:
        replace_atomic(path, data)
    log.append('plan', jid, dict(filename=filename, sha256=digest, bytes=len(data), tokens=tokens, items=items))
    return jid


def cycle(log: Any, api: Any, rebuild: Any, process: Any, record: Any,
          native: Any, fingerprint: Any, pilot_only: bool = False) -> str:
    """Recover, collect, measure, then fill available capacity; one durable writer only."""
    allowed = set(list(log.entries)[:100]) if pilot_only else None
    if pilot_only:
        require(len(allowed) == 100, 'PILOT_REQUIRES_FIRST_100_PRODUCTION_REQUESTS')
        require(all('settled' in ev or all(i['rid'] in allowed for i in log.job(jid, 'plan')['items'])
                    for jid, ev in log.jobs.items()), 'OUT_OF_PILOT_JOB_ALREADY_PLANNED_STOP')
    for jid, ev in list(log.jobs.items()):
        if 'settled' in ev:
            continue
        # Reconcile uncertain POSTs even during an anomaly; do not create new work.
        safe_dispatch = not log.unknown_usage and not baseline.anomaly(log) and not any(s == 'failed' for s in log.state.values())
        if 'submitted' not in ev and ('submit_intent' in ev or safe_dispatch):
            submit(log, jid, api)
        if 'submitted' not in ev:
            continue
        if 'downloads' not in ev:
            remote = api.retrieve(log.job(jid, 'submitted')['id'])
            check_batch_binding(log, jid, remote)
            if 'snapshot' not in ev or log.job(jid, 'snapshot') != remote:
                log.append('snapshot', jid, remote)
            if remote['status'] in TERMINAL:
                download(log, jid, remote, api)
        if 'downloads' in ev:
            reconcile_results(log, jid, process, record)
    if log.unknown_usage or any(s == 'failed' for s in log.state.values()):
        # Poll/retrieve other in-flight jobs on subsequent cycles but never add work.
        return 'draining_failure' if any('submitted' in e and 'settled' not in e for e in log.jobs.values()) else 'technical_stop'
    if baseline.anomaly(log):
        return 'draining_anomaly' if any('submitted' in e and 'settled' not in e for e in log.jobs.values()) else 'cost_anomaly_stop'
    if pilot_only and all(log.state.get(r) == 'completion' for r in allowed):
        return 'pilot_complete'
    if all(log.state.get(r) == 'completion' for r in log.entries):
        return 'complete'
    # Other producers have unknown reservations; wait rather than invent their free capacity.
    own_ids = {log.job(j, 'submitted')['id'] for j, ev in log.jobs.items() if 'submitted' in ev}
    if any(b['status'] not in TERMINAL and b['id'] not in own_ids for b in api.listing('batches')):
        return 'waiting_foreign_batches'
    while True:
        capacity = log.queue_capacity - log.reserved_tokens()
        if capacity <= 0:
            break
        measured = len(log.costed_requests)
        if measured < min(SAMPLE, len(log.entries)):
            scheduled = len({rid for rid, _ in log.assignments})
            room = min(SAMPLE, len(log.entries)) - scheduled
            # Existing native retries of the pilot are allowed, but no new corpus units.
            count_limit = room if room > 0 else sum(s == 'retry' for s in log.state.values())
            if count_limit <= 0:
                break
        else:
            count_limit = MAX_REQUESTS
        jid = make_job(log, api, rebuild, native, fingerprint, capacity, count_limit, allowed)
        if jid is None:
            break
        if not submit(log, jid, api):
            return 'waiting_foreign_batches'
    return 'waiting'


def manifest(parent: dict, stream: Any, limit: int, compatibility: bool) -> dict:
    """Pin capacity, exact queue, implementation and scientific dependencies separately."""
    from . import batch_journal as journal_module
    from . import resumable_production_journal as staging
    paths = (Path(__file__), Path(batch_transport.__file__), Path(journal_module.__file__),
             Path(staging.__file__), Path(baseline.__file__), POLICY)
    requests = deepcopy(parent['requests'][:1] if compatibility else parent['requests'])
    for entry in requests:
        inputs = entry['cost']['inputTokenEstimates']['pooled']
        outputs = entry['cost']['outputTokenScenarios']['pooled']
        mi, mo = (2, 1.5) if inputs > 272000 else (1, 1)
        entry['estimatedCostUSD'] = (inputs * 1.25 * mi + outputs * 5 * mo) / 1e6
    return dict(version='publications-gpt61-batch/1.0.0', parentPreflightSha256=baseline.PARENT_SHA,
                generatorPins=stream.versions(), localAdapterPins=baseline.PINS,
                implementationPins={str(p.relative_to(ROOT)): sha256_bytes(p.read_bytes()) for p in paths},
                queuedTokenLimit=limit, capacitySource='Researcher-supplied operational capacity; not a verified account limit',
                requests=requests, pricing=PRICING, meaningfulSampleRequests=SAMPLE,
                maximumAttemptsPerRequest=2, transport='batch', compatibilityOnly=compatibility,
                diagnosticResultsImported=False, streamingResultsImported=False, kgAuthorized=False)


def offline_status(root: Path) -> dict:
    """Read a checksum snapshot even while the live writer owns the journal lock."""
    path = root / 'status.json'
    if not path.exists():
        return dict(initialized=(root / 'run-manifest.json').exists(), completed=0, failed=0,
                    pending=10893 if root == RUN else 1, cumulativeUsagePricedUSD=0,
                    outstandingBatchIDs=[], snapshotAvailable=False)
    value = baseline.read(path)
    require(sha256_bytes(canonical_json(value['summary'])) == value['sha256'], 'STATUS_HASH_DRIFT')
    value['summary']['snapshotAgeSeconds'] = time.time() - value['summary']['observedAt']
    return value['summary']


def increase_capacity(log: Any, capacity: int) -> None:
    """Append an operational increase; retain manifest, prior events and Batch identities."""
    require(type(capacity) is int and capacity >= log.queue_capacity, 'CAPACITY_DECREASE_FORBIDDEN')
    if capacity == log.queue_capacity:
        return
    log.append('capacity_increase', None, dict(previous=log.queue_capacity, new=capacity,
               source='researcher_supplied_operational_capacity', manifestSha256=log.pin,
               unixTime=time.time()))


def main() -> None:
    """Only check/live/pilot modes use the network, exclusively in the researcher terminal."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for mode in ('estimate', 'status', 'check', 'live', 'pilot-only'):
        modes.add_argument('--' + mode, action='store_true')
    modes.add_argument('--increase-queue-capacity', type=int, metavar='TOKENS', help='Offline append-only operational capacity increase')
    parser.add_argument('--queued-token-limit', type=int, help='Initial operational capacity saved by --check; may be provisional')
    parser.add_argument('--poll-seconds', type=int, default=60)
    args = parser.parse_args()
    require(args.poll_seconds >= 5, 'POLL_INTERVAL_TOO_SHORT')
    require(args.queued_token_limit is None or args.queued_token_limit > 0, 'INVALID_ACCOUNT_CAPACITY')
    if args.status:
        print(json.dumps(offline_status(RUN), indent=2))
        return
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_PREFLIGHT')):
        paired, stream, native, parent = baseline.dependencies()
    saved = CHECK / 'run-manifest.json'
    limit = args.queued_token_limit
    if saved.exists():
        previous = baseline.read(saved)
        require(limit is None or limit == previous['queuedTokenLimit'], 'PINNED_CAPACITY_DRIFT')
        limit = previous['queuedTokenLimit']
    if args.estimate:
        print(json.dumps(estimate(parent, limit), indent=2))
        return
    require(type(limit) is int and limit > 0, 'INITIAL_OPERATIONAL_CAPACITY_REQUIRED: use --check --queued-token-limit <tokens>')
    root = CHECK if args.check else RUN
    mf = manifest(parent, stream, limit, args.check)
    data = canonical_json(mf) + b'\n'
    def verify_receipt(p: dict, receipt: dict) -> None:
        """Recompute provider metadata and priced usage from the exact authentic wrapper."""
        require(receipt == response_record(receipt['row'], p, paired, receipt['batchID'], receipt['number']), 'RECEIPT_PROVENANCE_DRIFT')

    Journal = batch_journal(native, lambda p, e: verify_variant(p, e, stream), stream.fingerprint,
                            verify_outcome, verify_receipt)
    if args.live or args.pilot_only:
        require(saved.exists(), 'RUN_ONE_REQUEST_BATCH_COMPATIBILITY_CHECK_FIRST')
        expected = canonical_json(manifest(parent, stream, limit, True)) + b'\n'
        require(saved.read_bytes() == expected, 'COMPATIBILITY_MANIFEST_DRIFT')
        # Verify durable completion, not merely the convenient status snapshot.
        with Journal(CHECK / 'execution.jsonl', expected, sha256_bytes(expected)) as checked:
            require(len(checked.state) == 1 and all(s == 'completion' for s in checked.state.values()) and
                    not checked.unknown_usage, 'COMPATIBILITY_NOT_ACCEPTED')
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'run-manifest.json'
    if args.increase_queue_capacity is not None:
        require(path.exists(), 'INITIALIZE_PRODUCTION_BEFORE_CAPACITY_INCREASE')
    if path.exists():
        require(path.read_bytes() == data, 'BATCH_MANIFEST_DRIFT')
    with Journal(root / 'execution.jsonl', data, sha256_bytes(data)) as log:
        if path.exists():
            require(path.read_bytes() == data, 'BATCH_MANIFEST_DRIFT')
        else:
            replace_atomic(path, data)
        if args.increase_queue_capacity is not None:
            increase_capacity(log, args.increase_queue_capacity)
            save_status(log)
            return
        api = batch_transport.BatchAPI(baseline.provider.load_openai_api_key())
        with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_JIT_CONTEXT')):
            env, routing = stream.load()
        rows = {r['sourceUnitID']: r for r in routing['records']}
        originals = {e['identity']['requestID']: e for e in parent['requests']}

        def rebuild(entry: dict) -> dict:
            """Generate only the next unit, through the exact pinned JIT builder."""
            with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_JIT')):
                stream.load_manifest(baseline.PARENT, baseline.PARENT_SHA)
                row = rows[entry['sourceUnitID']]
                menu = next(m for m in row['menus'] if m['passIdentity'] == entry['passIdentity'])
                p = variant(stream.reconstruct(env, row, menu, originals[entry['identity']['requestID']]), paired)
                verify_variant(p, entry, stream)
                stream.old.native._SCHEMA_CACHE.clear()
                return p

        def process(p: dict, receipt: dict, n: int, first: Any) -> dict:
            """Apply the original native contracts with all network access blocked."""
            with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NATIVE')):
                stream.load_manifest(baseline.PARENT, baseline.PARENT_SHA)
                return native_process(p, receipt, n, first, paired, stream)

        try:
            while True:
                disposition = cycle(log, api, rebuild, process,
                    lambda row, p, bid, n: response_record(row, p, paired, bid, n), native, stream.fingerprint,
                    pilot_only=args.pilot_only)
                status = save_status(log)
                print(disposition, flush=True)
                if disposition in ('complete', 'pilot_complete', 'cost_anomaly_stop', 'technical_stop'):
                    if disposition == 'technical_stop':
                        raise ValueError('TECHNICAL_STOP: inspect preserved request errors')
                    return
                time.sleep(args.poll_seconds)
        finally:
            if not log.poisoned:
                save_status(log)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print('STOP:', str(exc), file=sys.stderr)
        raise SystemExit(1)
