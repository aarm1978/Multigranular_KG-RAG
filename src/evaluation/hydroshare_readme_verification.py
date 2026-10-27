"""Read-only, offline paired verification of the 20 HydroShare README successors.

Only native journal framing, receipt arithmetic and persisted-record checks run.
No request reconstruction, semantic validation, admission policy or model runs.
The original journal must be scanned for its hash chain; reporting is restricted
strictly to the 20 lineage-linked owners. Neither production root is writable.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from typing import Callable

from src.evaluation import hydroshare_readme_recovery as recovery
from src.evaluation import source_family_production_verification as native
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.resumable_production_journal import require

QUEUE_SHA = '57dab8abb6c4a78dbe6c22d184032872ae68764520e150c25de2ff40b084014c'
OVERLAY_SHA = 'b4cf402d12aa0de08186f17c2865cfa39fa680df567a2a8e48d9db07dd67675b'
BATCH_ID = 'batch_6adfcadf7a5081909520ffdf900d2342'
DEFAULT_OUTPUT = Path('var/study2_step13/hydroshare-readme-verification/v1')
LIMITATIONS = (native.LIMITATIONS + ' Candidate IDs are run-local, never cross-run entity identities. '
    'Ontology/evidence multiset differences describe recorded assertions only; no entity matching, merging, '
    'version selection or Step 14 work is performed. More accepted assertions do not establish improved '
    'precision/recall. README authority remains prospective caller attestation; historical acquisition '
    'is not independently verified.')


def checked_context(original: dict, successor: dict, old_entry: dict, entry: dict,
                    bindings: list, source: dict) -> None:
    """Compare complete persisted contexts and lineage without invoking source readers."""
    lineage = entry['recoveryProvenance']
    require(lineage == dict(version=recovery.VERSION, overlaySha256=OVERLAY_SHA,
        originalRequestID=old_entry['identity']['requestID'], originalIdentity=old_entry['identity'],
        originalBundleSha256=old_entry['bundleSha256'], attestationScope='prospective_recovery_only'),
        'LINEAGE_DRIFT')
    require(entry['ownerID'] == old_entry['ownerID'] == source['resource_id'] and
            entry['family'] == old_entry['family'] == 'hydroshare' and
            entry['identity']['requestID'] != old_entry['identity']['requestID'], 'PAIR_OWNER_DRIFT')
    before, after = [p['semanticRequest']['request'] for p in (original, successor)]
    units = after['sourceUnits']
    native.indexed(units, 'sourceUnitID')
    abstracts = [u for u in units if u['sourceField'] == 'abstract']
    require(len(before['sourceUnits']) == len(abstracts) == 1 and abstracts == before['sourceUnits'] and
            abstracts[0]['text'] == source['abstract'], 'COMPLETE_ORIGINAL_ABSTRACT_DRIFT')
    readmes = [u for u in units if u['sourceField'] == 'README']
    snapshot = native.indexed(source['documentation']['readme_files'], 'source_file')
    readers = successor['requestInputs']['readme_results']
    require(len(readmes) == len(bindings) == len(snapshot) == len(readers) and
            len(units) == 1 + len(readmes) and set(snapshot) == {b['source_path'] for b in bindings},
            'COMPLETE_README_COVERAGE_DRIFT')
    for unit, binding, reader in zip(readmes, bindings, readers):
        text = snapshot[binding['source_path']]['readme_text_raw']
        require(unit['text'] == text and digest(text.encode()) == binding['authorityTextSha256'] and
                len(text) == binding['characters'] and unit['sourceUnitID'] == binding['sourceUnitID'] and
                unit['source_path'] == binding['source_path'] and binding['ownerID'] == entry['ownerID'] and
                unit['startOffsetInAuthority'] == 0 and unit['endOffsetInAuthority'] == len(text),
                'COMPLETE_README_TEXT_OR_ID_DRIFT')
        for field in ('snapshotID', 'sourceVersion', 'authorityTextSha256',
                      'sourceVerification', 'acquisitionIntegrityStatus'):
            require(unit[field] == binding[field] == reader['authority'][field], 'README_PROVENANCE_DRIFT:' + field)
        require(reader['sourceUnits'] == [unit] and reader['authority']['text'] == text and
                reader['inputComplete'] and reader['status'] == 'source_read_success', 'PERSISTED_READER_DRIFT')
    ids = [u['sourceUnitID'] for u in units]
    require(after['selectedSourceUnitIDs'] == ids == entry['coverage']['selectedSourceUnitIDs'] ==
            entry['coverage']['primarySourceUnitIDs'] and after['sourceCompleteness']['inputComplete'] and
            not entry['coverage']['exceptionalSplit'], 'COMPLETE_SELECTION_DRIFT')
    for field in ('instructions', 'promptIdentifier', 'responseContract', 'targetProfile', 'schemaVersion', 'owner'):
        require(before.get(field) == after.get(field), 'POLICY_DRIFT:' + field)
    for field in ('abstract_results', 'accepted_endpoints', 'accepted_assertions', 'authorized_stubs',
                  'trusted_provenance', 'request_version'):
        require(original['requestInputs'].get(field) == successor['requestInputs'].get(field), 'INPUT_DRIFT:' + field)
    for prepared in (original, successor):
        envelope = prepared['body']
        require(envelope['model'] == 'gpt-6.1-sol' and envelope['reasoning'] == {'effort': 'medium'} and
                envelope['max_output_tokens'] == 32768 and envelope['store'] is False and
                'tools' not in envelope and envelope['text']['format']['strict'] is True, 'MODEL_CONFIGURATION_DRIFT')


def bundle(folder: Path, entry: dict) -> dict:
    """Load exact sealed bytes without rebuilding the stored provider envelope."""
    path = folder / 'queue' / entry['bundleFile']
    require(path.resolve().parent == (folder / 'queue').resolve(), 'UNSAFE_BUNDLE_PATH')
    require(native.file_hash(path) == entry['bundleSha256'], 'BUNDLE_DRIFT')
    prepared = recovery.read_json(path)
    native.checked_prepared(prepared, entry)
    return prepared


def evidence_files(log: object, root: Path) -> dict:
    """Check immutable submission/download files referenced by native journal events."""
    hashes = {p.name: native.file_hash(p) for p in
              (root / 'run-manifest.json', log.path, log.checkpoint)}
    for jid, events in sorted(log.jobs.items()):
        for event in ('plan', 'downloads'):
            if event not in events:
                continue
            payload = log.job(jid, event)
            for item in [payload] if event == 'plan' else payload['files']:
                path = root / item['filename']
                require(path.resolve().parent == root.resolve(), 'UNSAFE_EVIDENCE_PATH')
                sha = native.file_hash(path)
                require(sha == item['sha256'], 'EVIDENCE_FILE_DRIFT')
                hashes[path.name] = sha
    return hashes


def paired_inventory(log: object, queue: dict, owners: set, emit: Callable, version: str) -> dict:
    """Reuse native inventory on a read-only view restricted to the paired owners."""
    entries = {rid: e for rid, e in log.entries.items() if e['family'] == 'hydroshare' and e['ownerID'] in owners}
    require(len(entries) == len(owners) and {e['ownerID'] for e in entries.values()} == owners,
            'PAIRED_REQUEST_COVERAGE_DRIFT')
    require(all(log.state.get(rid) == 'completion' for rid in entries), 'PAIRED_REQUEST_INCOMPLETE')
    view = SimpleNamespace(entries=entries, state=log.state, offsets=log.offsets, outcomes=log.outcomes,
        receipts=log.receipts, prepared=log.prepared, payload_at=log.payload_at)
    coverage = [o for o in queue['coverage'] if o['family'] == 'hydroshare' and o['ownerID'] in owners]
    result = {owner: dict(statistics={}, candidateKinds=Counter(), ontology=Counter(),
        evidenceReferencesBySource=Counter(), acceptedAssertionsBySource=Counter(), citedReadmeIDs=[],
        ontologyEvidence=Counter(), recordedCostUSD='0', details=[]) for owner in sorted(owners)}

    def collect(name: str, row: dict) -> None:
        """Keep exact detailed records and count evidence occurrences, not entities."""
        emit(name, dict(version=version, **row))
        target = result[row['ownerID']]
        if name == 'family-owner':
            target['statistics'] = row
        elif name == 'requests':
            target['recordedCostUSD'] = str(sum((Decimal(str(d['cost']['estimatedUSD']))
                for d in row['deliveries']), Decimal(0)))
        elif name == 'candidate-decisions':
            target['details'].append(row)
            target['candidateKinds'][row['constructionReplayRecord']['kind']] += 1
            accepted = row['acceptedRecord']
            if accepted:
                kind = row['constructionReplayRecord']['kind']
                candidate = accepted['originalCandidate']
                key = kind + ':' + candidate['class' if kind == 'node' else 'relation']
                target['ontology'][key] += 1
                request = log.prepared(row['requestID'])['semanticRequest']['request']
                units = native.indexed(request['sourceUnits'], 'sourceUnitID')
                fields = set()
                for evidence in accepted['boundEvidence']:
                    unit = units[evidence['sourceUnitID']]
                    field = unit['sourceField']
                    fields.add(field)
                    target['evidenceReferencesBySource'][field] += 1
                    # Exact persisted evidence and type; deliberately no candidate/endpoint identity matching.
                    signature = json.dumps(dict(ontologyType=key, evidence=evidence), sort_keys=True, ensure_ascii=False)
                    target['ontologyEvidence'][signature] += 1
                target['acceptedAssertionsBySource'].update(fields)
        elif name == 'source-unit-coverage' and row['citedByAcceptedEvidence']:
            if row['sourceMetadata']['sourceField'] == 'README':
                target['citedReadmeIDs'].append(row['sourceUnitID'])

    native.inventory(view, dict(coverage=coverage), collect)
    return result


def difference(before: dict, after: dict) -> dict:
    """Return signed counts with explicit zeros, preserving all categories."""
    return {key: after.get(key, 0) - before.get(key, 0) for key in sorted(before.keys() | after.keys())}


def compare(original: dict, successor: dict) -> tuple[list, list]:
    """Pair owners, never candidate IDs; retain literal ontology/evidence differences."""
    require(original.keys() == successor.keys(), 'PAIRED_OWNER_DRIFT')
    pairs, details = [], []
    for owner in sorted(original):
        old, new = original[owner], successor[owner]
        views = []
        for item in (old, new):
            views.append({k: v for k, v in item.items() if k not in ('details', 'ontologyEvidence')})
        numeric = ('requests', 'processable', 'candidateOccurrences', 'acceptedNodes', 'acceptedEdges',
                   'abstentions', 'zeroYieldRequests', 'originalCandidateOccurrences')
        delta = {k: new['statistics'][k] - old['statistics'][k] for k in numeric}
        for key in ('constructionDecisions', 'acceptanceBases', 'originalReplayDispositions',
                    'constructionReplayDispositions', 'coverage'):
            delta[key] = difference(old['statistics'][key], new['statistics'][key])
        for key in ('candidateKinds', 'ontology', 'evidenceReferencesBySource', 'acceptedAssertionsBySource'):
            delta[key] = difference(old[key], new[key])
        delta['recordedCostUSD'] = str(Decimal(new['recordedCostUSD']) - Decimal(old['recordedCostUSD']))
        pairs.append(dict(ownerID=owner, original=views[0], successor=views[1], delta=delta))
        changes = difference(old['ontologyEvidence'], new['ontologyEvidence'])
        details.append(dict(ownerID=owner, originalCandidates=old['details'], successorCandidates=new['details'],
            ontologyEvidenceDifferences=[dict(signature=json.loads(k), originalOccurrences=old['ontologyEvidence'][k],
                successorOccurrences=new['ontologyEvidence'][k], delta=v) for k, v in changes.items() if v],
            comparisonMeaning='Literal ontology/evidence occurrence differences, not new/lost entities. '
                              'Candidate IDs and local endpoints are not aligned across runs.'))
    return pairs, details


def checked_completion(log: object, status: dict) -> None:
    """Require the recorded settled batch and fully categorized expected spend."""
    require(status['completed'] == 20 and all(status[k] == 0 for k in
        ('failed', 'pending', 'unknownUsageAttempts', 'outstandingBatches', 'outstandingRequests',
         'uncertainSubmissionRequests', 'conservativeCostAttempts')), 'SUCCESSOR_NOT_SETTLED')
    require(status['actualUSD'] is not None and
            abs(Decimal(str(status['actualUSD'])) - Decimal('0.5696416')) < Decimal('0.000000000001'),
            'RECORDED_COST_DRIFT')
    require({log.payload_at(offset)['batchID'] for offset in log.receipts.values()} == {BATCH_ID},
            'PROVIDER_BATCH_DRIFT')


def verify(original: Path, successor: Path, emit: Callable) -> dict:
    """Verify pinned sources, lineage and two native journals, then compare persisted views."""
    manifest, overlay = recovery.load_queue(successor, QUEUE_SHA)
    require(manifest['bindingOverlaySha256'] == OVERLAY_SHA, 'EXPECTED_OVERLAY_DRIFT')
    parent = recovery.read_json(original / 'queue-manifest.json')
    old_run = recovery.read_json(original / 'production/run-manifest.json')
    native.checked_coverage(parent, old_run)
    require(native.file_hash(original / 'queue-manifest.json') == recovery.ORIGINAL_PINS[str(recovery.ORIGINAL / 'queue-manifest.json')] and
            native.file_hash(original / 'production/run-manifest.json') == recovery.ORIGINAL_PINS[str(recovery.ORIGINAL / 'production/run-manifest.json')],
            'ORIGINAL_ROOT_PIN_DRIFT')
    owners = {e['ownerID'] for e in manifest['requests']}
    require(len(manifest['requests']) == len(owners) == 20,
            'EXPECTED_20_PAIRED_OWNERS')
    old_entries = native.indexed([e for e in parent['requests'] if e['family'] == 'hydroshare'], 'ownerID')
    sources = native.indexed(recovery.read_json(recovery.ROOT / recovery.SOURCE), 'resource_id')
    require(owners == {b['ownerID'] for b in overlay['bindings']}, 'OVERLAY_OWNER_DRIFT')
    coverage = []
    for entry in manifest['requests']:
        owner = entry['ownerID']
        require(digest(canonical(sources[owner])) == entry['coverage']['sourceRecordSha256'] ==
                old_entries[owner]['coverage']['sourceRecordSha256'], 'SOURCE_RECORD_PIN_DRIFT')
        prepared = bundle(successor, entry)
        checked_context(bundle(original, old_entries[owner]), prepared, old_entries[owner], entry,
                        [b for b in overlay['bindings'] if b['ownerID'] == owner], sources[owner])
        coverage.append(dict(family='hydroshare', ownerID=owner, inputComplete=True,
            readerSourceUnitIDs=entry['coverage']['selectedSourceUnitIDs'], excludedSourceUnitIDs=[],
            diagnostics=[], groups=[dict(entry['coverage'], requestID=entry['identity']['requestID'])]))
    run = recovery.read_json(successor / 'production/run-manifest.json')
    require(run['parentSha256'] == QUEUE_SHA and run['requests'] == manifest['requests'] and
            all(run[k] == manifest[k] for k in ('generatorPins', 'implementationPins', 'pricing', 'bindingOverlaySha256')),
            'SUCCESSOR_RUN_DRIFT')
    journal_reports, inventories = {}, {}
    for version, folder, queue, run_manifest in [('original', original, parent, old_run),
            ('successor', successor, dict(manifest, coverage=coverage), run)]:
        infrastructure, _, paired = recovery.journal_class(run_manifest)

        def check_prepared(prepared: dict, entry: dict) -> None:
            """Match persisted bundles only for the paired HydroShare requests."""
            if entry['family'] == 'hydroshare' and entry['ownerID'] in owners:
                require(prepared == bundle(folder, entry), 'JOURNAL_BUNDLE_DRIFT')

        def check_outcome(prepared: dict, receipt: dict, outcome: dict, number: int) -> None:
            """Check paired persisted outcomes without rerunning validators or policy."""
            body = prepared['semanticRequest']['request']
            if body['artifactFamily'] == 'hydroshare' and body['owner']['endpointID'] in owners:
                native.checked_outcome(prepared, receipt, outcome, number)

        def check_receipt(prepared: dict, receipt: dict) -> None:
            """Replay the native provider receipt and cost check for every journal receipt."""
            require(receipt == recovery.adapter.batch.response_record(receipt['row'], prepared, paired,
                    receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

        cls = recovery.adapter.batch_journal(infrastructure, check_prepared,
            recovery.adapter.fingerprint, check_outcome, check_receipt)
        root = folder / 'production'
        with native.read_only_log(root, infrastructure, cls, (root / 'run-manifest.json').read_bytes()) as log:
            hashes = evidence_files(log, root)
            hashes['queue-manifest.json'] = native.file_hash(folder / 'queue-manifest.json')
            status = recovery.adapter.batch.summary(log)
            for key in ('elapsedSeconds', 'observedRequestsPerHour'):
                status.pop(key)
            if version == 'successor':
                checked_completion(log, status)
            inventories[version] = paired_inventory(log, queue, owners, emit, version)
            journal_reports[version] = dict(journalSeq=log.seq, journalHead=log.head, inputHashes=hashes,
                journalWideStatus=status, pairedRequests=20,
                scope='Entire native hash chain and receipts; persisted outcome checks and inventory only for paired owners.')
    pairs, details = compare(inventories['original'], inventories['successor'])
    for row in pairs:
        emit('per-owner', row)
    for row in details:
        emit('comparison', row)
    totals = {}
    for version, items in inventories.items():
        totals[version] = {key: sum(v['statistics'][key] for v in items.values()) for key in
            ('candidateOccurrences', 'acceptedNodes', 'acceptedEdges', 'abstentions', 'zeroYieldRequests')}
        for key in ('constructionDecisions', 'acceptanceBases'):
            totals[version][key] = dict(sum((Counter(v['statistics'][key]) for v in items.values()), Counter()))
        totals[version]['recordedCostUSD'] = str(sum((Decimal(v['recordedCostUSD']) for v in items.values()), Decimal(0)))
        for key in ('candidateKinds', 'ontology', 'evidenceReferencesBySource', 'acceptedAssertionsBySource'):
            totals[version][key] = dict(sum((v[key] for v in items.values()), Counter()))
        totals[version]['citedReadmeUnits'] = sum(len(v['citedReadmeIDs']) for v in items.values())
    require(native.file_hash(successor / 'queue-manifest.json') == QUEUE_SHA and
            native.file_hash(successor / 'binding-overlay.json') == OVERLAY_SHA, 'SUCCESSOR_INPUT_CHANGED')
    recovery.check_pins(manifest['originalArtifactPins'])
    recovery.check_pins(manifest['implementationPins'])
    return dict(version='hydroshare-readme-verification/1.0', owners=sorted(owners), totals=totals,
        journals=journal_reports, queueSha256=QUEUE_SHA, bindingOverlaySha256=OVERLAY_SHA,
        implementationSha256=native.file_hash(Path(__file__)), persistedImplementationPins=manifest['implementationPins'],
        persistedInputPins=manifest['originalArtifactPins'], technicalIntegrity='verified',
        inputCoverage=dict(completeAbstracts=20, completeReadmes=21, selectedUnits=41),
        evidenceCoverage='Recorded accepted citations counted separately by source field; see per-owner and source-unit-coverage.',
        scientificCorrectness='Not evaluated', limitations=LIMITATIONS, readOnly=True, providerCalls=0)


def main() -> None:
    """Publish reports atomically in a new ignored directory outside both production roots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-root', type=Path, default=recovery.ORIGINAL)
    parser.add_argument('--successor-root', type=Path, default=recovery.DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), 'OUTPUT_EXISTS: choose a new report directory')
    for root in (args.original_root.resolve(), args.successor_root.resolve()):
        require(output != root and root not in output.parents and output not in root.parents,
                'OUTPUT_MUST_BE_OUTSIDE_PRODUCTION_ROOTS')
    require(subprocess.run(['git', 'check-ignore', '-q', str(output / 'verification.json')],
                          cwd=recovery.ROOT).returncode == 0, 'OUTPUT_MUST_BE_GIT_IGNORED')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.hydroshare-verification-', dir=output.parent) as temporary:
        stage = Path(temporary)
        with ExitStack() as stack, recovery.offline():
            files = {name: stack.enter_context((stage / (name + '.jsonl')).open('w', encoding='utf-8')) for name in
                ('per-owner', 'comparison', 'requests', 'family-owner', 'ontology-types', 'candidate-decisions',
                 'source-unit-coverage', 'exceptions')}

            def emit(name: str, record: dict) -> None:
                """Persist deterministic detailed records without modifying evidence roots."""
                files[name].write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')

            result = verify(args.original_root.resolve(), args.successor_root.resolve(), emit)
        (stage / 'verification.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        lines = ['# HydroShare paired README verification', '',
            'Technical integrity: verified. Input coverage: 20 complete abstracts and 21 complete READMEs.',
            'Comparison: exactly 20 paired owners. Scientific correctness: not evaluated.', '',
            '| View | Candidates | Accepted nodes | Accepted edges | Abstentions | Zero-yield requests | Cited README units |',
            '|---|---:|---:|---:|---:|---:|---:|']
        for version, counts in result['totals'].items():
            lines.append('| ' + version + ' | ' + ' | '.join(str(counts[k]) for k in
                ('candidateOccurrences', 'acceptedNodes', 'acceptedEdges', 'abstentions', 'zeroYieldRequests', 'citedReadmeUnits')) + ' |')
        for version, counts in result['totals'].items():
            lines.extend(['', version.capitalize() + ' construction decisions: ' + json.dumps(counts['constructionDecisions'], sort_keys=True),
                'Acceptance bases: ' + json.dumps(counts['acceptanceBases'], sort_keys=True),
                'Accepted evidence references by source: ' + json.dumps(counts['evidenceReferencesBySource'], sort_keys=True)])
        lines.extend(['', 'Successor recorded cost: USD 0.5696416. No provider calls made.', '', LIMITATIONS, '',
            'See per-owner.jsonl for paired counts and signed differences; comparison.jsonl for exact candidate '
            'records and ontology/evidence differences; verification.json for input hashes and journal heads.', ''])
        (stage / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
        require(not output.exists(), 'OUTPUT_EXISTS')
        stage.rename(output)
    print(args.output)


if __name__ == '__main__':
    main()
