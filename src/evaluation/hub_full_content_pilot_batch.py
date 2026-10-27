"""Researcher-operated raw-only Batch lifecycle for the immutable Hub v2 pilot.

Preflight is offline. Only explicit submit/status/collect operations use the
existing Batch transport. No semantic parser, construction, or retry of model
responses is permitted here. Restart submit to reconcile uncertain POSTs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import fcntl
import json
from pathlib import Path

from src.evaluation import hub_full_content_pilot as pilot
from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm.publications.resumable_production_journal import require

ROOT = pilot.ROOT
QUEUE = pilot.BASE
QUEUE_SHA = 'dea24ae1cb1b51d1dcf518cc8c64fd33fe18af3b372c1b7df677fae156691637'
batch = adapter.batch
canonical = batch.canonical_json
sha = adapter.digest


def verify_prepared(prepared: dict, entry: dict) -> None:
    """Verify sealed bytes and identity without reconstructing historical requests."""
    require(sha(canonical(prepared)+b'\n') == entry['bundleSha256'], 'BUNDLE_HASH_DRIFT')
    require(adapter.fingerprint(prepared) == entry['identity'], 'REQUEST_IDENTITY_DRIFT')
    require(prepared['semanticRequest']['request']['schemaVersion'] == pilot.VERSION,
            'PILOT_VERSION_DRIFT')


def load_queue(repo: Path) -> tuple[dict, dict]:
    """Verify the exact approved manifest, dependencies, bundles and Batch lines."""
    root = repo/QUEUE
    raw = (root/'queue-manifest.json').read_bytes()
    require(sha(raw) == QUEUE_SHA, 'QUEUE_MANIFEST_DRIFT')
    parent = batch.batch_transport.decode(raw)
    require(parent['version'] == pilot.VERSION and len(parent['requests']) == 8,
            'PILOT_QUEUE_DRIFT')
    for group in ('inputPins', 'implementationPins'):
        for relative, expected in parent[group].items():
            require(sha((repo/relative).read_bytes()) == expected, 'INPUT_PIN_DRIFT:'+relative)
    bundles, lines = {}, []
    for entry in parent['requests']:
        path = root/'queue'/entry['bundleFile']
        raw = path.read_bytes()
        require(sha(raw) == entry['bundleSha256'], 'BUNDLE_HASH_DRIFT')
        prepared = batch.batch_transport.decode(raw)
        verify_prepared(prepared, entry)
        rid = entry['identity']['requestID']
        require(rid not in bundles, 'DUPLICATE_REQUEST_ID')
        bundles[rid] = prepared
        item, line = batch.input_line(prepared, 1, adapter.fingerprint)
        require(item == entry['batchItem'], 'BATCH_ITEM_DRIFT')
        lines.append(line)
    raw = (root/'batch-input.jsonl').read_bytes()
    require(raw == b''.join(lines) and sha(raw) == parent['batchInputSha256'], 'BATCH_INPUT_DRIFT')
    return parent, bundles


def raw_outcome(prepared: dict, receipt: dict, number: int, first=None) -> dict:
    """Classify transport only; never parse candidates or release evidence holds."""
    require(number == 1 and first is None, 'PILOT_RESPONSE_RETRY_FORBIDDEN')
    body = receipt['providerResponse'] or {}
    row = receipt['row']
    if (row.get('error') or {}).get('code') == 'batch_expired':
        status = 'expired'
    elif row.get('error') or (row.get('response') or {}).get('status_code') != 200:
        status = 'failed'
    elif body.get('status') == 'incomplete':
        status = 'incomplete'
    elif body.get('status') == 'completed':
        status = 'completed'
    else:
        status = 'failed'
    holds = []
    if body and (body.get('model') != prepared['body']['model'] or
                 body.get('service_tier') not in ('default', 'batch')):
        holds.append('MODEL_OR_TIER_DRIFT')
    if receipt['metadataError']:
        holds.append(receipt['metadataError'])
    if receipt['cost']['estimatedUSD'] is None:
        holds.append('UNKNOWN_USAGE')
    return dict(transportStatus=status, transportHolds=holds,
                processable=status == 'completed' and not holds, retryEligible=False,
                scientificStatus='not_evaluated', evidenceDisposition='held',
                kgAuthorization=False, productionResult=None)


def infrastructure():
    """Bind native receipt/journal validation to raw-only pilot outcomes."""
    paired, native, pins = adapter.infrastructure()

    def record(row, prepared, bid, number):
        """Reuse original exact response and usage accounting."""
        return batch.response_record(row, prepared, paired, bid, number)

    def receipt_check(prepared, receipt):
        """Recompute the receipt from the preserved provider wrapper."""
        require(receipt == record(receipt['row'], prepared, receipt['batchID'], receipt['number']),
                'RECEIPT_DRIFT')

    def outcome_check(prepared, receipt, outcome, number):
        """Prohibit scientific processing and unrecorded retry decisions."""
        require(outcome == raw_outcome(prepared, receipt, number), 'RAW_OUTCOME_DRIFT')

    Journal = adapter.batch_journal(native, verify_prepared, adapter.fingerprint,
                                    outcome_check, receipt_check)
    return Journal, native, pins, record


def run_manifest(parent: dict, pins: dict, capacity: int) -> dict:
    """Pin the isolated execution adapter without modifying the approved queue."""
    require(type(capacity) is int and capacity > 0, 'SUPPLY_--queued-token-limit')
    entries = deepcopy(parent['requests'])
    for entry in entries:
        entry['estimatedCostUSD'] = entry['cost']['costUSD']['pooled']
    return dict(version='hub-full-content-pilot-raw-batch/1.0', parentSha256=QUEUE_SHA,
                generatorPins=pins, adapterSha256=sha(Path(__file__).read_bytes()),
                requests=entries, queuedTokenLimit=capacity, meaningfulSampleRequests=8,
                maximumAttemptsPerRequest=1, pricing=parent['pricing'], kgAuthorization=False,
                processing='raw_transport_only; scientific_verification_deferred')


def report(log) -> dict:
    """Separate transport completion, missing results, holds and scientific status."""
    rows = []
    for rid in log.entries:
        status, holds = 'unsubmitted', []
        key = (rid, 1)
        if key in log.outcomes:
            outcome = log.payload_at(log.outcomes[key])['native']
            status, holds = outcome['transportStatus'], outcome['transportHolds']
        elif key in log.assignments:
            jid, _ = log.assignments[key]
            events = log.jobs[jid]
            status = 'pending'
            if 'snapshot' in events and log.job(jid, 'snapshot')['status'] in batch.TERMINAL:
                status = 'missing' if 'downloads' in events else 'awaiting_collection'
        rows.append(dict(requestID=rid, transportStatus=status, transportHolds=holds,
                         scientificStatus='not_evaluated', kgAuthorization=False))
    return dict(requests=rows, counts=dict(Counter(r['transportStatus'] for r in rows)),
                batches=[dict(job=jid, batchID=log.job(jid, 'submitted')['id'] if 'submitted' in ev else None,
                    status=log.job(jid, 'snapshot')['status'] if 'snapshot' in ev else 'submission_pending')
                    for jid, ev in log.jobs.items()], accounting=batch.summary(log),
                note='Native completion counts are transport bookkeeping only; all evidence remains held.')


def verify_execution_files(log) -> None:
    """Check sealed local input and downloaded provider bytes even after settlement."""
    for jid, events in log.jobs.items():
        plan = log.job(jid, 'plan')
        require(sha((log.path.parent/plan['filename']).read_bytes()) == plan['sha256'],
                'SEALED_INPUT_DRIFT')
        if 'downloads' in events:
            for record in log.job(jid, 'downloads')['files']:
                require(sha((log.path.parent/record['filename']).read_bytes()) == record['sha256'],
                        'RESULT_FILE_HASH_DRIFT')


def operate(mode: str, capacity: int | None = None, *, repo: Path = ROOT, api=None) -> dict:
    """Verify before every operation; construct a provider client only for live modes."""
    require(mode in ('preflight', 'submit', 'status', 'collect'), 'UNKNOWN_OPERATION')
    parent, bundles = load_queue(repo)
    Journal, native, pins, record = infrastructure()
    root = repo/QUEUE/'production'
    path = root/'run-manifest.json'
    saved = batch.batch_transport.decode(path.read_bytes()) if path.exists() else None
    if saved is None:
        require(mode not in ('status', 'collect'), 'NOT_SUBMITTED; run preflight or explicitly submit')
        if mode == 'preflight':
            require(not (root/'execution.jsonl').read_bytes(), 'ORPHAN_JOURNAL')
            return dict(queueSha256=QUEUE_SHA, requests=8, verified=True, initialized=False,
                        costUSD=parent['costUSD'], providerCalls=0)
    else:
        require(capacity is None or capacity == saved['queuedTokenLimit'], 'CAPACITY_DRIFT')
        capacity = saved['queuedTokenLimit']
    manifest = run_manifest(parent, pins, capacity)
    wire = canonical(manifest)+b'\n'
    require(saved is None or path.read_bytes() == wire, 'RUN_MANIFEST_DRIFT')
    log = Journal(root/'execution.jsonl', wire, sha(wire))
    if mode == 'preflight':
        require(not log.staging.exists(), 'JOURNAL_RECOVERY_REQUIRED; restart explicit operation')
        with log.path.open('rb') as handle:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
            log.file = handle
            if log.checkpoint.exists():
                log.anchor = native.decode(log.checkpoint.read_bytes())
            native.Journal.replay(log)
            verify_execution_files(log)
            return dict(report(log), verified=True, queueSha256=QUEUE_SHA, providerCalls=0)
    with log:
        verify_execution_files(log)
        # Journal locking precedes creation of the immutable execution manifest.
        if path.exists():
            require(path.read_bytes() == wire, 'RUN_MANIFEST_DRIFT')
        else:
            from src.extraction.llm.full_corpus_source_family_batch import seal
            seal(path, wire)
        if api is None:
            api = batch.batch_transport.BatchAPI(batch.baseline.provider.load_openai_api_key())
        errors = []
        if mode == 'submit':
            log.disposition = batch.submit_all(log, api,
                lambda entry: bundles[entry['identity']['requestID']], native, adapter.fingerprint, 1)
        elif mode == 'collect':
            errors = batch.collect_once(log, api, raw_outcome, record)
        else:
            for jid, events in log.jobs.items():
                if 'submitted' in events:
                    remote = api.retrieve(log.job(jid, 'submitted')['id'])
                    batch.check_batch_binding(log, jid, remote)
                    if 'snapshot' not in events or log.job(jid, 'snapshot') != remote:
                        log.append('snapshot', jid, remote)
        result = report(log)
        result['collectionErrors'] = errors
        # Partial responses remain durable even when the caller receives a STOP.
        require(not errors, 'COLLECTION_STOP:'+json.dumps(result))
        return result


def main() -> None:
    """Expose explicit terminal operations; import and preflight never call APIs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('preflight', 'submit', 'status', 'collect'))
    parser.add_argument('--queued-token-limit', type=int,
                        help='Existing executor operational capacity, required only on first submit')
    args = parser.parse_args()
    print(json.dumps(operate(args.operation, args.queued_token_limit), indent=2))


if __name__ == '__main__':
    main()
