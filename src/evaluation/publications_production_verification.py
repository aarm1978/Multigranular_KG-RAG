"""Read-only, offline inventory of the frozen Publications Batch journal.

Does not replay extraction, rescore semantics, recover events, or assemble a KG.
Run as a module from the repository root; operational dependencies remain local.
"""
from __future__ import annotations

import argparse
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from typing import Any
from unittest.mock import patch

from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.resumable_production_journal import require

DEFAULT_ROOT = Path('var/study2_step13/publications-gpt61-batch/v1')
DEFAULT_OUTPUT = Path('var/study2_step13/publications-production-verification/v1')


def file_hash(path: Path) -> str:
    """Hash exact bytes in bounded memory."""
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def diagnostics(value: Any, counts: Counter, pointer: str = '') -> None:
    """Count recorded diagnostic values by field path without recategorizing policy."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = pointer + '/' + key
            if key in {'code', 'candidateValidationStatus', 'envelopeStatus', 'processingCode',
                       'referenceType', 'valid', 'status', 'reasonCode'} and not isinstance(child, (dict, list)):
                counts[path + '=' + json.dumps(child)] += 1
            diagnostics(child, counts, path)
    elif isinstance(value, list):
        for child in value:
            diagnostics(child, counts, pointer + '/*')


def checked_outcome(prepared: dict, receipt: dict, outcome: dict, number: int) -> None:
    """Reuse native checks and verify selected stored validation/materialization hashes."""
    from src.extraction.llm.publications import full_corpus_gpt61_batch as batch
    from src.extraction.llm.publications.candidate_validation import materialize_usable_pipeline_output
    batch.verify_outcome(prepared, receipt, outcome, number)
    if not outcome['processable']:
        return
    selection = outcome['productionResult']['attemptSelection']
    selected = next(a for a in selection['attempts'] if a['attemptNumber'] == number)
    require(selected == outcome['attempt'], 'SELECTED_NATIVE_ATTEMPT_DRIFT')
    validation = selected['validation']
    for value, field in [(selection, 'attemptSelectionHash'), (validation, 'validationResultsHash')]:
        require(value[field] == sha256_bytes(canonical_json({k: v for k, v in value.items() if k != field})),
                'STORED_HASH_DRIFT:' + field)
    envelope = selected['parserResult']['parsedEnvelope']
    require(selected['usablePipelineOutput'] == materialize_usable_pipeline_output(envelope, validation),
            'USABLE_PIPELINE_DRIFT')
    require(validation['requestID'] == prepared['request']['requestID'] and
            validation['requestSha256'] == prepared['request']['requestInputSha256'], 'VALIDATION_IDENTITY_DRIFT')
    evidence = {e['evidenceSpanID']: e for e in envelope['evidenceSpans']}
    for result in validation['evidenceResults']:
        require(result['computedEvidenceHash'] == sha256_bytes(
            evidence[result['evidenceSpanID']]['evidenceText'].encode('utf-8')), 'EVIDENCE_TEXT_HASH_DRIFT')


def inventory(log: Any) -> tuple[dict, list]:
    """Summarize validated latest outcomes against every original queue entry."""
    coverage = {name: {} for name in ('paperID', 'sourceUnitID', 'passIdentity')}
    classes, relations, diag, categories = Counter(), Counter(), Counter(), Counter()
    yields, collections = Counter(), Counter()
    exceptions = []
    for rid, entry in sorted(log.entries.items()):
        category = log.category(rid)
        categories[category] += 1
        accepted = category == 'completed_protected'
        for dimension, groups in coverage.items():
            group = groups.setdefault(entry[dimension], dict(requests=0, accepted=0, exceptionRequestIDs=[]))
            group['requests'] += 1
            group['accepted'] += int(accepted)
            if not accepted:
                group['exceptionRequestIDs'].append(rid)
        key = log.latest.get(rid)
        outcome = log.payload_at(log.outcomes[key])['native'] if key else {}
        if accepted:
            require(outcome.get('processable') is True, 'LATEST_ACCEPTED_OUTCOME_MISSING:' + rid)
            result = outcome['productionResult']
            projection = result['acceptedSemanticProjection']
            require(projection['requestID'] == rid and
                    str(projection['sourceArtifactID']) == str(entry['paperID']) and
                    projection['sourceUnitID'] == entry['sourceUnitID'], 'PROJECTION_SOURCE_DRIFT:' + rid)
            nodes, edges = projection['acceptedNodes'], projection['acceptedEdges']
            classes.update(n['className'] for n in nodes)
            relations.update(e['relationName'] for e in edges)
            yields['zeroNodes'] += int(not nodes)
            yields['zeroEdges'] += int(not edges)
            yields['zeroNodesAndEdges'] += int(not nodes and not edges)
            selected = next(a for a in result['attemptSelection']['attempts']
                            if a['attemptNumber'] == result['attemptSelection']['selectedAttemptNumber'])
            diagnostics(selected, diag)
            envelope = (selected.get('parserResult') or {}).get('parsedEnvelope') or {}
            for name in ('candidateNodes', 'candidateEdges', 'abstentions', 'deferredRecords'):
                collections[name] += len(envelope.get(name, []))
            sidecar = result.get('unresolvedIdentitySidecar')
            require(sidecar is not None, 'MISSING_UNRESOLVED_SIDECAR:' + rid)
            from src.extraction.llm.publications.production_acceptance import derive_unresolved_identity_sidecar
            require(sidecar == derive_unresolved_identity_sidecar(result['attemptSelection'], log.prepared(rid)['request']),
                    'UNRESOLVED_SIDECAR_DRIFT:' + rid)
            collections['unresolvedIdentitySidecarRecords'] += len(sidecar['records'])
        else:
            history = []
            for attempt_key in sorted(k for k in log.outcomes if k[0] == rid):
                receipt = log.payload_at(log.receipts[attempt_key])
                native = log.payload_at(log.outcomes[attempt_key])['native']
                row = receipt['row']
                response = row.get('response') or {}
                codes = Counter()
                diagnostics(native, codes)
                history.append(dict(delivery=attempt_key[1], httpStatus=response.get('status_code'),
                                    providerError=row.get('error') or (response.get('body') or {}).get('error'),
                                    nativeDiagnostics=dict(codes), transportHold=native.get('transportHold'),
                                    retryEligible=native['retryEligible'], cost=receipt['cost'],
                                    usage=receipt.get('usage'), receiptSha256=sha256_bytes(canonical_json(receipt))))
            exceptions.append(dict(requestID=rid, **{k: entry[k] for k in coverage}, category=category,
                                   retryEligible=outcome.get('retryEligible'), history=history))
    for groups in coverage.values():
        for group in groups.values():
            group['coverage'] = ('complete' if group['accepted'] == group['requests'] else
                                 'uncovered' if not group['accepted'] else 'partial')
    denominators = {name: dict(uniqueTotal=len(groups), **dict(Counter(g['coverage'] for g in groups.values())))
                    for name, groups in coverage.items()}
    return dict(requests=len(log.entries), categories=dict(categories), coverageDenominators=denominators,
                coverage=coverage, acceptedNodes=sum(classes.values()), acceptedEdges=sum(relations.values()),
                nodesByClass=dict(classes), edgesByRelation=dict(relations), zeroYield=dict(yields),
                selectedEnvelopeCollections=dict(collections), recordedSelectedAttemptDiagnostics=dict(diag)), exceptions


def verify(root: Path) -> tuple[dict, list]:
    """Use native read-only replay under a shared lock; never enter writable journals."""
    from src.extraction.llm.publications import full_corpus_gpt61_batch as batch
    from src.extraction.llm.publications import batch_recovery as recovery
    from src.extraction.llm.publications.batch_journal import batch_journal

    paired, stream, native, parent = batch.baseline.dependencies()
    data = (root / 'run-manifest.json').read_bytes()
    manifest = json.loads(data)
    expected = batch.manifest(parent, stream, manifest['queuedTokenLimit'], False)
    require(manifest['requests'] == expected['requests'], 'ORIGINAL_QUEUE_DRIFT')
    require(manifest['parentPreflightSha256'] == batch.baseline.PARENT_SHA, 'PARENT_PIN_DRIFT')

    def receipt_check(prepared: dict, receipt: dict) -> None:
        """Revalidate original provider wrapper, provenance and priced usage."""
        require(receipt == batch.response_record(receipt['row'], prepared, paired, receipt['batchID'], receipt['number']),
                'RECEIPT_PROVENANCE_DRIFT')

    cls = batch_journal(native, lambda p, e: batch.verify_variant(p, e, stream),
                        stream.fingerprint, checked_outcome, receipt_check)
    cls = recovery.journal_type(cls, checked_outcome, stream.fingerprint)
    log = cls(root / 'execution.jsonl', data, sha256_bytes(data))
    require(not log.staging.exists(), 'PENDING_EVENT_REQUIRES_RESEARCHER_REVIEW')
    with log.path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        log.file = handle
        require(log.checkpoint.exists(), 'MISSING_HEAD_ANCHOR')
        log.anchor = native.decode(log.checkpoint.read_bytes())
        native.Journal.replay(log)
        recovery.migrate(log, expected, read_only=True)
        report, exceptions = inventory(log)
        hashes = {p.name: file_hash(p) for p in (root / 'run-manifest.json', log.path, log.checkpoint)}
        for jid, events in sorted(log.jobs.items()):
            for event in ('plan', 'downloads'):
                if event not in events:
                    continue
                payload = log.job(jid, event)
                files = [payload] if event == 'plan' else payload['files']
                for item in files:
                    path = root / item['filename']
                    require(path.resolve().parent == root.resolve(), 'UNSAFE_EVIDENCE_PATH')
                    digest = file_hash(path)
                    require(digest == item['sha256'], 'EVIDENCE_FILE_DRIFT:' + path.name)
                    hashes[path.name] = digest
        status = batch.summary(log)
        status.pop('elapsedSeconds', None)
        status.pop('observedRequestsPerHour', None)
        report.update(version='publications-source-local-verification/1.0', readOnly=True,
                      inputHashes=hashes, parentPreflightSha256=batch.baseline.PARENT_SHA,
                      implementationSha256=file_hash(Path(__file__)), journalSeq=log.seq, journalHead=log.head,
                      accounting=status, finalInvoiceVerified=False,
                      limitations='Accepted source-local candidates, not unique canonical KG entities. Acceptance is not semantic correctness, completeness, Precision, Recall or F1. Diagnostics retain original field paths and policy labels; missing diagnostics are not zero findings.')
        discrepancies = []
        for field, observed, target in [('requests', report['requests'], 10893),
                ('accepted', report['categories'].get('completed_protected', 0), 10886),
                ('terminal', report['categories'].get('terminal_review', 0), 7),
                *[(name, status[name], 0) for name in ('pending', 'outstandingBatches', 'uncertainSubmissionRequests')]]:
            if observed != target:
                discrepancies.append(dict(field=field, observed=observed, expected=target))
        report['discrepancies'] = discrepancies
    return report, exceptions


def main() -> None:
    """Write a new ignored report directory only after successful integrity replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    require(subprocess.run(['git', 'check-ignore', '-q', str(args.output / 'verification.json')]).returncode == 0,
            'REPORT_OUTPUT_MUST_BE_GIT_IGNORED')
    require(not args.output.exists(), 'OUTPUT_EXISTS: choose a new output directory')
    require(args.root.resolve() not in args.output.resolve().parents and args.root.resolve() != args.output.resolve(),
            'OUTPUT_MUST_BE_OUTSIDE_PRODUCTION_EVIDENCE')
    with patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_ONLY')):
        report, exceptions = verify(args.root)
    args.output.mkdir(parents=True)
    for name, value in [('verification.json', report), ('exceptions.json', exceptions)]:
        (args.output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    summary = ('# Publications source-local production verification\n\n'
               f"Requests: {report['requests']}; dispositions: {json.dumps(report['categories'], sort_keys=True)}.\n\n"
               f"Accepted source-local nodes: {report['acceptedNodes']}; edges: {report['acceptedEdges']}.\n\n"
               f"Coverage denominators: {json.dumps(report['coverageDenominators'], sort_keys=True)}.\n\n"
               f"Usage-priced cost: ${report['accounting']['cumulativeUsagePricedUSD']:.8f}; final invoice unverified.\n\n"
               f"Discrepancies: {json.dumps(report['discrepancies'])}.\n\n"
               f"{report['limitations']}\n\n"
               f"Manifest SHA-256: {report['inputHashes']['run-manifest.json']}; journal SHA-256: {report['inputHashes']['execution.jsonl']}.\n\n"
               'See verification.json for input SHA-256 hashes, class/relation distributions, zero yields, coverage and recorded diagnostics; exceptions.json preserves terminal delivery history and billing evidence.\n')
    (args.output / 'summary.md').write_text(summary)
    print(str(args.output))
    if report['discrepancies']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
