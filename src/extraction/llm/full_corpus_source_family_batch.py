"""Researcher-terminal HydroShare/GitHub/Hub GPT-6.1 Batch production.

Run --estimate offline first. --check submits at most one request per family,
without retries; repeat it to collect. --submit-all requires successful checks.
--collect never dispatches. All modes use only this workstream's local directory.

Operational packaging: <=250KB full UTF-8 envelope, <=24KB selected text and
<=48 intact units; 32768 output tokens. Whole owners/files/heading trees are
preferred. Oversized blocks split at existing unit boundaries with Hub ancestor
prose repeated as explicit context. No cross-group relation is inferred.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import socket
import time
from unittest.mock import patch

from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm import source_family_inputs as sources
from src.extraction.llm import source_family_queue as queue
from src.extraction.llm.publications.resumable_production_journal import replace_atomic, require

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'var/study2_step13/source-families-gpt61-batch/v1'


@contextmanager
def offline():
    """Prohibit network access during construction, verification and native replay."""
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_NO_NETWORK')):
        yield


def implementation_pins() -> dict:
    """Pin relevant code and authorities without touching any active runtime file."""
    paths = list((ROOT / 'src/extraction/llm').glob('*.py'))
    for directory in adapter.conformance.DIRECTORIES.values():
        paths.extend((ROOT / 'src/extraction/llm' / directory).glob('*.py'))
    for name in ('batch_transport.py', 'batch_journal.py', 'resumable_production_journal.py',
                 'full_corpus_gpt61_batch.py', 'full_corpus_gpt61_production.py',
                 'openai_provider.py', 'production_acceptance.py', 'deterministic_evidence_binding.py'):
        paths.append(ROOT / 'src/extraction/llm/publications' / name)
    paths.extend([adapter.acceptance.POLICY_PATH, ROOT / 'src/ontology/ontology_spec.yaml'])
    return {str(p.relative_to(ROOT)): adapter.digest(p.read_bytes()) for p in sorted(set(paths))}


def seal(path: Path, data: bytes) -> None:
    """Create or verify deterministic local artifacts without overwriting drift."""
    if path.exists():
        require(path.read_bytes() == data, 'SEALED_ARTIFACT_DRIFT:' + str(path.relative_to(BASE)))
    else:
        replace_atomic(path, data)


def estimate() -> dict:
    """Build a source-pinned queue offline, preserving complete owner accounting."""
    BASE.mkdir(parents=True, exist_ok=True)
    folder = BASE / 'queue'
    folder.mkdir(exist_ok=True)
    with (BASE / 'queue.lock').open('a+b') as lock, offline():
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data, pins = sources.snapshots(ROOT)
        entries, coverage, totals = [], [], {}
        for owner in sources.owners(ROOT, data):
            family = owner['family']
            stats = totals.setdefault(family, dict(owners=0, readerUnits=0, selectedUniqueUnits=0,
                selectedUnitOccurrences=0, requests=0, heldUnits=0, incompleteOwners=0,
                sourceFailureDiagnostics=0, reviewDiagnostics=0, emptyOwners=0,
                costUSD={k: 0.0 for k in ('low', 'pooled', 'high', 'outputCeiling')}))
            stats['owners'] += 1
            stats['readerUnits'] += len(owner['units'])
            stats['emptyOwners'] += not owner['units']
            stats['sourceFailureDiagnostics'] += sum(d.get('status') == 'failed_source_or_evidence_binding'
                or d.get('disposition') == 'failed_source_or_evidence_binding' for d in owner['diagnostics'])
            stats['reviewDiagnostics'] += sum(d.get('status') == 'needs_review' for d in owner['diagnostics'])
            record = {k: owner[k] for k in ('family', 'ownerID', 'sourceRecordSha256',
                'endpointRecordSha256', 'diagnostics', 'inputComplete', 'rawSourcePins')}
            record.update(readerSourceUnitIDs=[u['sourceUnitID'] for u in owner['units']], groups=[])
            accounted, selected = [], set()
            for p, group in queue.requests(owner):
                accounted.extend(group['primarySourceUnitIDs'])
                if p is None:
                    stats['heldUnits'] += len(group['primarySourceUnitIDs'])
                    record['inputComplete'] = False
                else:
                    identity = adapter.fingerprint(p)
                    name = adapter.digest(adapter.canonical(identity)) + '.json'
                    wire = adapter.canonical(p) + b'\n'
                    seal(folder / name, wire)
                    cost = queue.costs(p)
                    entries.append(dict(identity=identity, family=family, ownerID=owner['ownerID'],
                        bundleFile=name, bundleSha256=adapter.digest(wire), coverage=group,
                        rawSourcePins=owner['rawSourcePins'], cost=cost,
                        estimatedCostUSD=cost['costUSD']['pooled']))
                    group = {**group, 'requestID': identity['requestID']}
                    selected.update(group['selectedSourceUnitIDs'])
                    stats['selectedUnitOccurrences'] += len(group['selectedSourceUnitIDs'])
                    stats['requests'] += 1
                    for scenario, amount in cost['costUSD'].items():
                        stats['costUSD'][scenario] += amount
                record['groups'].append(group)
            require(accounted == record['readerSourceUnitIDs'], 'SOURCE_COVERAGE_GAP_OR_DUPLICATION')
            stats['selectedUniqueUnits'] += len(selected)
            stats['incompleteOwners'] += not record['inputComplete']
            coverage.append(record)
            print(json.dumps(dict(family=family, ownersProcessed=stats['owners'], requests=stats['requests'])), flush=True)
        result = dict(version='source-family-batch-queue/1.0', sourcePins=pins,
            implementationPins=implementation_pins(), requests=entries, coverage=coverage,
            summary=totals, sizing=queue.SIZING, pricing=adapter.batch.PRICING,
            limitations=['GitHub ModelVersion remains held; implementsMethod deferred to Step 14.',
                'Review-held source passages remain unselected, not absent evidence.',
                'Repeated Hub ancestor context may yield repeated source-local proposals; no cross-group merging.',
                'Estimates are byte-based scenarios, not exact token counts or invoices.',
                'Already accepted Batches remain billable after a later cost pause.'], kgAuthorization=False)
        seal(BASE / 'queue-manifest.json', adapter.canonical(result) + b'\n')
        return result


def load_queue() -> dict:
    """Verify sealed source/code pins before any future provider operation."""
    result = json.loads((BASE / 'queue-manifest.json').read_bytes())
    require(result['implementationPins'] == implementation_pins(), 'IMPLEMENTATION_DRIFT')
    for relative, expected in result['sourcePins'].items():
        require(adapter.digest((ROOT / relative).read_bytes()) == expected, 'SOURCE_SNAPSHOT_DRIFT:' + relative)
    return result


def rebuild(entry: dict) -> dict:
    """Verify exact persisted bundle and raw authorities immediately before dispatch."""
    with offline():
        for path, expected in entry['rawSourcePins'].items():
            require(adapter.digest((ROOT / path).read_bytes()) == expected, 'RAW_SOURCE_DRIFT:' + path)
        data = (BASE / 'queue' / entry['bundleFile']).read_bytes()
        require(adapter.digest(data) == entry['bundleSha256'], 'BUNDLE_HASH_DRIFT')
        p = json.loads(data)
        adapter.verify_prepared(p, entry)
        return p


def manifest(parent: dict, pins: dict, limit: int) -> dict:
    """Use one shared journal so successful compatibility requests cannot be redispatched."""
    representatives = []
    for family in adapter.conformance.DIRECTORIES:
        entry = next((e for e in parent['requests'] if e['family'] == family), None)
        require(entry is not None, 'NO_COMPATIBILITY_REPRESENTATIVE:' + family)
        representatives.append(entry['identity']['requestID'])
    return dict(version='source-family-batch-run/1.0', generatorPins=pins,
        parentSha256=adapter.digest(adapter.canonical(parent)), implementationPins=parent['implementationPins'],
        queuedTokenLimit=limit, capacitySource='researcher-supplied operational capacity; not verified entitlement',
        requests=parent['requests'], compatibilityRequestIDs=representatives,
        meaningfulSampleRequests=min(100, len(parent['requests'])), maximumAttemptsPerRequest=2,
        compatibilityMaximumAttempts=1, pricing=parent['pricing'], sizing=parent['sizing'], kgAuthorization=False)


def save_status(log: object) -> dict:
    """Persist family-level usage alongside shared global accounting and progress."""
    result = adapter.batch.summary(log)
    families = {}
    for rid, entry in log.entries.items():
        family = families.setdefault(entry['family'], dict(requests=0, completed=0, failed=0,
            usagePricedUSD=0.0, fullyCategorizedUSD=0.0, conservativeAttempts=0, unknownUsageAttempts=0))
        family['requests'] += 1
        family['completed'] += log.state.get(rid) == 'completion'
        family['failed'] += log.state.get(rid) == 'failed'
    for (rid, _), offset in log.receipts.items():
        family = families[log.entries[rid]['family']]
        cost = log.payload_at(offset)['cost']
        amount = cost['estimatedUSD']
        if amount is None:
            family['unknownUsageAttempts'] += 1
        else:
            family['usagePricedUSD'] += amount
            if cost['basis'] == 'reported_cache_details':
                family['fullyCategorizedUSD'] += amount
            elif amount:
                family['conservativeAttempts'] += 1
    result.update(families=families, journalSeq=log.seq, journalHead=log.head,
                  observedAt=time.time(), startedAt=log.started_at)
    replace_atomic(log.path.parent / 'status.json', adapter.batch.canonical_json(dict(summary=result,
                   sha256=adapter.digest(adapter.batch.canonical_json(result)))) + b'\n')
    return result


def operate(args: argparse.Namespace) -> dict:
    """Dispatch only explicit terminal modes, sharing the proven transport journal."""
    with offline():
        parent = load_queue()
        paired, native, pins = adapter.infrastructure()
    root = BASE / 'production'
    path = root / 'run-manifest.json'
    saved = json.loads(path.read_bytes()) if path.exists() else None
    limit = saved['queuedTokenLimit'] if saved else args.queued_token_limit
    require(type(limit) is int and limit > 0, 'SUPPLY_VERIFIED_OPERATIONAL_CAPACITY_WITH_--queued-token-limit')
    require(not args.collect or saved is not None, 'NO_JOURNAL_TO_COLLECT')
    mf = manifest(parent, pins, limit)
    checks = set(mf['compatibilityRequestIDs'])
    # Compatibility never gets a technical retry, including after a later collect.
    def process(p: dict, receipt: dict, number: int, first: dict | None) -> dict:
        """Apply accepted native replay with sockets blocked."""
        with offline():
            return adapter.process(p, receipt, number, first,
                                   compatibility=p['request']['requestID'] in checks)

    def verify_outcome(p: dict, receipt: dict, outcome: dict, n: int) -> None:
        """Recompute exact sealed native outcome and technical attempt selection."""
        selection = outcome.get('attemptSelection')
        first = selection['attempts'][0] if n == 2 and selection else None
        require(outcome == process(p, receipt, n, first), 'NATIVE_OUTCOME_DRIFT')

    def record(row: dict, p: dict, bid: str, n: int) -> dict:
        """Retain authentic per-request wrapper, metadata and usage pricing."""
        return adapter.batch.response_record(row, p, paired, bid, n)

    def verify_receipt(p: dict, receipt: dict) -> None:
        """Verify stored provider lineage from original result bytes."""
        require(receipt == record(receipt['row'], p, receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

    Journal = adapter.batch_journal(native, adapter.verify_prepared, adapter.fingerprint,
                                    verify_outcome, verify_receipt)
    root.mkdir(parents=True, exist_ok=True)
    wire = adapter.batch.canonical_json(mf) + b'\n'
    with Journal(root / 'execution.jsonl', wire, adapter.digest(wire)) as log:
        seal(path, wire)
        if args.queued_token_limit is not None:
            adapter.batch.increase_capacity(log, args.queued_token_limit)
        if args.submit_all:
            require(all(log.state.get(r) == 'completion' for r in checks), 'COMPATIBILITY_CHECK_REQUIRED')
        api = adapter.batch.batch_transport.BatchAPI(adapter.batch.baseline.provider.load_openai_api_key())
        try:
            if args.collect or args.check:
                errors = adapter.batch.collect_once(log, api, process, record)
                require(not errors, 'COLLECTION_ERRORS:' + json.dumps(errors))
            if args.submit_all:
                log.disposition = adapter.batch.submit_all(log, api, rebuild, native, adapter.fingerprint, args.count_workers)
            elif args.check:
                for jid, events in list(log.jobs.items()):
                    if 'submitted' not in events and 'settled' not in events:
                        require(all(i['rid'] in checks for i in log.job(jid, 'plan')['items']), 'CHECK_CANNOT_SUBMIT_PRODUCTION')
                        if not adapter.batch.submit(log, jid, api):
                            log.disposition = 'waiting_foreign_batches'
                            return adapter.batch.summary(log)
                require(not any(log.state.get(r) in ('failed', 'retry') for r in checks), 'COMPATIBILITY_FAILED_NO_RETRY')
                while not all(log.state.get(r) in ('pending', 'received', 'completion') for r in checks):
                    jid = adapter.batch.make_job(log, api, rebuild, native, adapter.fingerprint,
                        log.queue_capacity - log.reserved_tokens(), 3, allowed=checks, count_workers=1)
                    if jid is None or not adapter.batch.submit(log, jid, api):
                        break
                log.disposition = 'compatibility_complete' if all(log.state.get(r) == 'completion' for r in checks) else 'compatibility_pending'
            return adapter.batch.summary(log)
        finally:
            if not log.poisoned:
                save_status(log)


def main() -> None:
    """Keep estimate/status offline; all genuine calls require explicit terminal modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for name in ('estimate', 'status', 'check', 'submit-all', 'collect'):
        modes.add_argument('--' + name, action='store_true')
    parser.add_argument('--queued-token-limit', type=int)
    parser.add_argument('--count-workers', type=int, default=8, choices=range(1, 17))
    args = parser.parse_args()
    if args.estimate:
        result = estimate()
        print(json.dumps(dict(families=result['summary'], pricing=result['pricing'],
                             overallCostUSD={k: sum(f['costUSD'][k] for f in result['summary'].values())
                                             for k in ('low', 'pooled', 'high', 'outputCeiling')},
                             sizing=result['sizing'], limitations=result['limitations']), indent=2))
    elif args.status:
        path = BASE / 'production/status.json'
        with offline():
            if path.exists():
                result = json.loads(path.read_bytes())
                require(adapter.digest(adapter.batch.canonical_json(result['summary'])) == result['sha256'], 'STATUS_DRIFT')
                result = result['summary']
                result['snapshotAgeSeconds'] = time.time() - result['observedAt']
            else:
                result = dict(initialized=False, liveCallsMadeByStatus=0)
            print(json.dumps(result, indent=2))
    else:
        print(json.dumps(operate(args), indent=2))


if __name__ == '__main__':
    main()
