"""Offline, read-only verification of persisted HydroShare/GitHub/Hub production.

Run from the repository root. No requests, readers, parsers, semantic validators,
conformance transforms or construction projections are executed. Counts describe
recorded source-local assertions, never aligned KG entities or scientific truth.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import socket
import subprocess
from typing import Any, Callable, Iterator
from unittest.mock import patch

from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.resumable_production_journal import require

DEFAULT_ROOT = Path('var/study2_step13/source-families-gpt61-batch/v1/production')
DEFAULT_OUTPUT = Path('var/study2_step13/source-family-production-verification/v1')
LIMITATIONS = ('Counts distinguish requests, candidate occurrences and accepted source-local assertions; '
              'they are not unique KG entities. Zero accepted yield is not proof of scientific absence. '
              'Construction acceptance is not independently established scientific truth, precision, recall or F1. '
              'Incomplete diagnostics without unit IDs remain owner-level records, not invented missing units. '
              'No source audit, semantic validation, evidence rebinding or cross-request deduplication was performed.')
BASES = {'policy_ordinary_inclusion', 'policy_conditional_inclusion'}


def file_hash(path: Path) -> str:
    """Hash persisted bytes without loading an entire journal into memory."""
    import hashlib
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def replay_hash(value: Any) -> str:
    """Use the frozen family request/replay ASCII serialization convention."""
    return digest(json.dumps(value, ensure_ascii=True, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode())


def indexed(rows: list, field: str) -> dict:
    """Reject duplicate persisted identities rather than silently collapse them."""
    result = {r[field]: r for r in rows}
    require(len(result) == len(rows), 'DUPLICATE_RECORD:' + field)
    return result


def checked_prepared(prepared: dict, entry: dict) -> None:
    """Check stored request identity and selection without rebuilding any request."""
    from src.extraction.llm.source_family_batch import fingerprint
    require(fingerprint(prepared) == entry['identity'], 'REQUEST_IDENTITY_DRIFT')
    semantic = prepared['semanticRequest']
    body = semantic['request']
    require(replay_hash(body) == semantic['requestSha256'], 'SEMANTIC_REQUEST_HASH_DRIFT')
    require(prepared['request']['requestID'] == body['artifactFamily'] + ':' + semantic['requestSha256'],
            'REQUEST_ID_DRIFT')
    require(body['artifactFamily'] == entry['family'] and body['owner']['endpointID'] == entry['ownerID'],
            'REQUEST_OWNER_DRIFT')
    require(body['selectedSourceUnitIDs'] == entry['coverage']['selectedSourceUnitIDs'], 'SELECTION_DRIFT')
    units = indexed(body['sourceUnits'], 'sourceUnitID')
    require(set(body['selectedSourceUnitIDs']) <= units.keys(), 'SELECTED_UNIT_MISSING')
    require(prepared['binding']['sourceSha256'] == digest(canonical(body['sourceUnits'])) and
            prepared['binding']['providerEnvelopeSha256'] == digest(canonical(prepared['body'])),
            'PREPARED_BINDING_DRIFT')


def checked_replay(replay: dict, sha: str, prepared: dict, raw: bytes) -> None:
    """Verify persisted replay bytes, request association and original source owner."""
    require(replay_hash(replay) == sha, 'REPLAY_HASH_DRIFT')
    require(replay['requestResult'] == prepared['semanticRequest'] and
            replay['artifactFamily'] == prepared['semanticRequest']['request']['artifactFamily'],
            'REPLAY_REQUEST_DRIFT')
    require(replay['requestSha256'] == replay['expectedRequestSha256'] ==
            prepared['semanticRequest']['requestSha256'] and
            replay['requestAssociation'] == 'matched_caller_supplied_digest', 'REQUEST_ASSOCIATION_DRIFT')
    require(replay['responseBytesHex'] == raw.hex() and replay['responseSha256'] == digest(raw),
            'REPLAY_RESPONSE_DRIFT')


def checked_outcome(prepared: dict, receipt: dict, outcome: dict, number: int) -> None:
    """Check recorded hashes and projection associations; do not reapply policy."""
    from src.extraction.llm.source_family_batch import fingerprint
    require(receipt['number'] == number, 'ATTEMPT_NUMBER_DRIFT')
    report = outcome.get('productionResult')
    require(outcome['processable'] == (report is not None and report['status'] == 'projection_completed'),
            'PROCESSABILITY_DRIFT')
    if report is None:
        require(not outcome.get('productionResultSha256'), 'MISSING_REPORT')
        return
    require(digest(canonical(report)) == outcome['productionResultSha256'], 'PRODUCTION_RESULT_HASH_DRIFT')
    require(outcome['provenance']['identity'] == fingerprint(prepared) and
            outcome['provenance']['responseSha256'] == digest(canonical(receipt)), 'OUTCOME_PROVENANCE_DRIFT')
    require(outcome['attempt']['attemptNumber'] == number and
            outcome['attempt']['requestInputSha256'] == prepared['semanticRequest']['requestSha256'],
            'ATTEMPT_ASSOCIATION_DRIFT')
    raw = base64.b64decode(receipt['rawModelOutputBase64'], validate=True)
    checked_replay(report['originalReplay'], report['originalReplaySha256'], prepared, raw)
    effective, effective_sha = report['originalReplay'], report['originalReplaySha256']
    if 'conformance' in report:
        conformance = report['conformance']
        require(conformance['originalResponseBytesHex'] == raw.hex() and
                conformance['originalResponseSha256'] == digest(raw) and
                conformance['semanticRequestSha256'] == prepared['semanticRequest']['requestSha256'],
                'CONFORMANCE_ASSOCIATION_DRIFT')
        derived = bytes.fromhex(conformance['derivedResponseBytesHex'])
        require(digest(derived) == conformance['derivedResponseSha256'], 'DERIVED_RESPONSE_HASH_DRIFT')
        effective, effective_sha = conformance['derivedReplay'], conformance['derivedReplaySha256']
        checked_replay(effective, effective_sha, prepared, derived)
    projection = report['projection']
    require(digest(canonical(projection)) == report['projectionSha256'], 'PROJECTION_HASH_DRIFT')
    body = prepared['semanticRequest']['request']
    require(projection['owner'] == body['owner'] and projection['artifactFamily'] == body['artifactFamily'] and
            projection['requestSha256'] == prepared['semanticRequest']['requestSha256'] and
            projection['replaySha256'] == effective_sha and projection['responseSha256'] == effective['responseSha256'],
            'PROJECTION_ASSOCIATION_DRIFT')
    require(projection['policySha256'] == outcome['provenance']['policySha256'], 'POLICY_PIN_DRIFT')
    decisions = indexed(report['decisions'], 'candidateID')
    rows = indexed(effective['finalRecords'], 'candidateID')
    require(decisions.keys() == rows.keys(), 'DECISION_COVERAGE_DRIFT')
    projected = indexed(projection['nodes'] + projection['edges'], 'candidateID')
    require(projected.keys() == {cid for cid, d in decisions.items() if d['disposition'] == 'accepted'},
            'ACCEPTED_ACCOUNTING_DRIFT')
    for cid, decision in decisions.items():
        require(decision['disposition'] in {'accepted', 'held', 'suppressed_duplicate'} and
                decision['originalDisposition'] == rows[cid]['finalDisposition'], 'DECISION_DISPOSITION_DRIFT')
        require(decision['acceptanceBasis'] in BASES if cid in projected else decision['acceptanceBasis'] is None,
                'ACCEPTANCE_BASIS_DRIFT')
    for kind, records in [('node', projection['nodes']), ('edge', projection['edges'])]:
        for record in records:
            cid = record['candidateID']
            row, decision = rows[cid], decisions[cid]
            validation = row['validationRecord']
            require(row['kind'] == kind and record['originalCandidate'] == row['originalCandidate'] and
                    record['acceptanceBasis'] == decision['acceptanceBasis'] and
                    record['boundEvidence'] == validation['boundEvidence'] and
                    record['sourceLocalCandidateID'] == validation['sourceLocalCandidateID'] and
                    set(validation.get('dependencies', [])) <= set(record['dependencies']) and
                    set(record['dependencies']) <= rows.keys() and
                    record['replayRecordReference'] == dict(replaySha256=effective_sha, candidateID=cid),
                    'PROJECTED_RECORD_DRIFT')
            for field in ('resolvedEndpoint', 'resolvedSource', 'resolvedTarget'):
                require(record.get(field) == validation.get(field), 'PROJECTED_ENDPOINT_DRIFT')
            require(all(e['sourceUnitID'] in body['selectedSourceUnitIDs'] for e in record['boundEvidence']),
                    'ACCEPTED_EVIDENCE_SELECTION_DRIFT')


def checked_coverage(queue: dict, manifest: dict) -> None:
    """Reconcile sealed queue groups without reopening source files or readers."""
    require(digest(canonical(queue)) == manifest['parentSha256'], 'SEALED_QUEUE_HASH_DRIFT')
    require(queue['requests'] == manifest['requests'], 'SEALED_QUEUE_REQUEST_DRIFT')
    entries = {
        e['identity']['requestID']: e for e in queue['requests']}
    require(len(entries) == len(queue['requests']), 'DUPLICATE_QUEUE_REQUEST')
    owners, seen = set(), set()
    for owner in queue['coverage']:
        key = owner['family'], owner['ownerID']
        require(key not in owners, 'DUPLICATE_COVERAGE_OWNER')
        owners.add(key)
        reader = owner['readerSourceUnitIDs']
        excluded = owner['excludedSourceUnitIDs']
        require(len(reader) == len(set(reader)) and len(excluded) == len(set(excluded)) and
                set(excluded) <= set(reader), 'COVERAGE_UNIT_DRIFT')
        primary = []
        for group in owner['groups']:
            primary.extend(group['primarySourceUnitIDs'])
            require((group['family'], group['ownerID']) == key and
                    set(group['selectedSourceUnitIDs']) <= set(reader) - set(excluded), 'GROUP_COVERAGE_DRIFT')
            rid = group.get('requestID')
            if rid:
                require(rid not in seen and rid in entries, 'GROUP_REQUEST_DRIFT')
                entry = entries[rid]
                require((entry['family'], entry['ownerID']) == key and
                        entry['coverage'] == {k: v for k, v in group.items() if k != 'requestID'},
                        'GROUP_ENTRY_DRIFT')
                seen.add(rid)
            else:
                require(bool(group.get('holdReason')), 'UNEXPLAINED_UNSELECTED_GROUP')
        require(primary == [u for u in reader if u not in set(excluded)], 'PRIMARY_COVERAGE_DRIFT')
    require(seen == entries.keys(), 'REQUEST_COVERAGE_GAP')


@contextmanager
def read_only_log(root: Path, native: Any, cls: type, wire: bytes) -> Iterator[Any]:
    """Bypass writable enter/recovery; hold the native journal inode's shared lock."""
    log = cls(root / 'execution.jsonl', wire, digest(wire))
    with log.path.open('rb') as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        require(not log.staging.exists(), 'PENDING_EVENT_REQUIRES_RESEARCHER_REVIEW')
        require(log.checkpoint.exists(), 'MISSING_HEAD_ANCHOR')
        log.file = handle
        anchor_bytes = log.checkpoint.read_bytes()
        log.anchor = native.decode(anchor_bytes)
        native.Journal.replay(log)
        require(log.seq == log.anchor['seq'] and log.head == log.anchor['headSha256'], 'HEAD_ANCHOR_DRIFT')
        yield log
        require(log.checkpoint.read_bytes() == anchor_bytes and not log.staging.exists(), 'JOURNAL_CHANGED_DURING_REPORT')


def inventory(log: Any, queue: dict, emit: Callable[[str, dict], None]) -> dict:
    """Count latest outcomes; retain all delivery histories and separate categories."""
    owners = {(o['family'], o['ownerID']): o for o in queue['coverage']}
    stats = {key: dict(requests=0, processable=0, requestStates=Counter(), candidateOccurrences=0,
                       constructionDecisions=Counter(), originalReplayDispositions=Counter(),
                       constructionReplayDispositions=Counter(), acceptanceBases=Counter(),
                       acceptedNodes=0, acceptedEdges=0, abstentions=0, zeroYieldRequests=0,
                       originalCandidateOccurrences=0, sourceDiagnosticReasons=Counter(),
                       sourceDiagnosticStatuses=Counter(), specialRecords=Counter())
             for key in owners}
    units, ontology = {}, Counter()
    for key, owner in owners.items():
        selected = {}
        held = set()
        for group in owner['groups']:
            if group.get('requestID'):
                for uid in group['selectedSourceUnitIDs']:
                    selected.setdefault(uid, []).append(group['requestID'])
            else:
                held.update(group['primarySourceUnitIDs'])
        for uid in owner['readerSourceUnitIDs']:
            units[key + (uid,)] = dict(family=key[0], ownerID=key[1], sourceUnitID=uid,
                readerAdmitted=True, productionAdmitted=uid not in owner['excludedSourceUnitIDs'],
                excluded=uid in owner['excludedSourceUnitIDs'], selectedRequestIDs=selected.get(uid, []),
                packagingHeld=uid in held, processableRequestIDs=[], acceptedEvidenceReferences=[],
                sourceMetadata=None, sourceDiagnosticRecords=[])
        for diagnostic in owner['diagnostics']:
            count = stats[key]
            diagnostic_units = set(diagnostic.get('sourceUnitIDs', []))
            if diagnostic.get('sourceUnitID'):
                diagnostic_units.add(diagnostic['sourceUnitID'])
            for uid in diagnostic_units:
                if key + (uid,) in units:
                    units[key + (uid,)]['sourceDiagnosticRecords'].append(diagnostic)
            if diagnostic.get('reason'):
                count['sourceDiagnosticReasons'][diagnostic['reason']] += 1
            if diagnostic.get('status'):
                count['sourceDiagnosticStatuses'][diagnostic['status']] += 1
            if key[0] == 'hydroshare':
                if diagnostic.get('status') == 'source_authority_reused':
                    count['specialRecords']['caller_attested_readme_authorities'] += 1
                elif diagnostic.get('authorityDecision') in {'no_accepted_readme_binding', 'frozen_readme_binding_mismatch'}:
                    count['specialRecords']['unverified_readme_diagnostics'] += 1
            if diagnostic.get('reason') == 'license_legal_text_step11_4_2':
                count['specialRecords']['ODbL_exclusion_records'] += 1
            emit('exceptions', dict(recordType='source_diagnostic', family=key[0], ownerID=key[1], record=diagnostic))
    for rid, entry in sorted(log.entries.items()):
        key = entry['family'], entry['ownerID']
        count = stats[key]
        state = log.state.get(rid, 'untouched')
        count['requests'] += 1
        count['requestStates'][state] += 1
        deliveries = sorted(k for k in log.outcomes if k[0] == rid)
        latest = deliveries[-1] if deliveries else None
        outcome = log.payload_at(log.outcomes[latest])['native'] if latest else {}
        processable = outcome.get('processable') is True
        require((state == 'completion') == processable, 'COMPLETION_ACCOUNTING_DRIFT')
        count['processable'] += processable
        prepared = log.prepared(rid) if rid in log.offsets else None
        body = prepared['semanticRequest']['request'] if prepared else {}
        for source in body.get('sourceUnits', []):
            unit = units.get(key + (source['sourceUnitID'],))
            if unit is not None:
                metadata = {k: v for k, v in source.items() if k != 'text'}
                require(unit['sourceMetadata'] in (None, metadata), 'SOURCE_METADATA_DRIFT')
                unit['sourceMetadata'] = metadata
        for uid in entry['coverage']['selectedSourceUnitIDs']:
            if processable:
                units[key + (uid,)]['processableRequestIDs'].append(rid)
        history = []
        for delivery in sorted(k for k in log.receipts if k[0] == rid):
            receipt = log.payload_at(log.receipts[delivery])
            attempt_out = log.payload_at(log.outcomes[delivery])['native'] if delivery in log.outcomes else None
            if attempt_out is not None and delivery != latest:
                emit('exceptions', dict(recordType='prior_delivery_outcome', requestID=rid, family=key[0],
                    ownerID=key[1], number=delivery[1], outcome=attempt_out))
            history.append(dict(number=delivery[1], receiptSha256=digest(canonical(receipt)),
                rawResponseSha256=digest(base64.b64decode(receipt['rawModelOutputBase64'], validate=True))
                    if receipt.get('rawModelOutputBase64') is not None else None,
                providerMetadata=receipt.get('providerMetadata'), cost=receipt.get('cost'),
                responseStatus=(receipt.get('providerResponse') or {}).get('status'),
                providerError=receipt['row'].get('error'), httpStatus=(receipt['row'].get('response') or {}).get('status_code'),
                processable=attempt_out.get('processable') if attempt_out else None,
                transportHold=attempt_out.get('transportHold') if attempt_out else None,
                attempt=attempt_out.get('attempt') if attempt_out else None,
                attemptSelection=attempt_out.get('attemptSelection') if attempt_out else None,
                productionResultSha256=attempt_out.get('productionResultSha256') if attempt_out else None))
        report = outcome.get('productionResult')
        provenance = dict(requestID=rid, family=key[0], ownerID=key[1], state=state, processable=processable,
            identity=entry['identity'], bundleSha256=entry['bundleSha256'], deliveries=history,
            outcomeProvenance=outcome.get('provenance'), requestBinding=prepared.get('binding') if prepared else None,
            sealedRequestCoverage=entry['coverage'], prospectiveSchema=(report or {}).get('prospectiveSchema'),
            conformanceHashes={k: v for k, v in (report or {}).get('conformance', {}).items() if k.endswith('Sha256')},
            reportHashes={k: v for k, v in (report or {}).items() if k.endswith('Sha256')})
        emit('requests', provenance)
        if not processable:
            emit('exceptions', dict(recordType='request_not_processable', **provenance))
        if report is None:
            continue
        original = report['originalReplay']
        effective = report.get('conformance', {}).get('derivedReplay', original)
        originals = indexed(original['finalRecords'], 'candidateID')
        rows = indexed(effective['finalRecords'], 'candidateID')
        count['originalCandidateOccurrences'] += len(originals)
        count['originalReplayDispositions'].update(r['finalDisposition'] for r in originals.values())
        count['constructionReplayDispositions'].update(r['finalDisposition'] for r in rows.values())
        projection = report['projection']
        accepted = indexed(projection['nodes'] + projection['edges'], 'candidateID')
        count['zeroYieldRequests'] += processable and not accepted
        count['acceptedNodes'] += len(projection['nodes'])
        count['acceptedEdges'] += len(projection['edges'])
        for decision in report['decisions']:
            cid = decision['candidateID']
            row = rows[cid]
            count['candidateOccurrences'] += 1
            count['constructionDecisions'][decision['disposition']] += 1
            identifier = (row.get('originalCandidate') or {}).get('inventoryId')
            if key[0] == 'github' and identifier in {'A-C10', 'C-C09', 'C-C16'}:
                count['specialRecords'][identifier + ':' + decision['disposition']] += 1
            if key[0] == 'ciroh_hub' and ((row.get('validationRecord') or {}).get('dependencies')
                    or (row.get('originalCandidate') or {}).get('parentPath')):
                count['specialRecords']['parent_or_evidence_dependency:' + decision['disposition']] += 1
            record = dict(requestID=rid, family=key[0], ownerID=key[1], candidateID=cid,
                decision=decision, originalReplayRecord=originals.get(cid), constructionReplayRecord=row,
                acceptedRecord=accepted.get(cid))
            emit('candidate-decisions', record)
            if decision['disposition'] != 'accepted':
                emit('exceptions', dict(recordType='candidate_not_accepted', **record))
            if cid in accepted:
                assertion = accepted[cid]
                candidate = assertion['originalCandidate']
                basis = assertion['acceptanceBasis']
                count['acceptanceBases'][basis] += 1
                ontology[(key[0], key[1], row['kind'], candidate['inventoryId'],
                          candidate['class' if row['kind'] == 'node' else 'relation'], basis)] += 1
                for evidence in assertion['boundEvidence']:
                    uid = evidence['sourceUnitID']
                    require(key + (uid,) in units and rid in units[key + (uid,)]['selectedRequestIDs'],
                            'CITED_UNIT_COVERAGE_DRIFT')
                    units[key + (uid,)]['acceptedEvidenceReferences'].append(dict(requestID=rid,
                        candidateID=cid, sourceLocalCandidateID=assertion['sourceLocalCandidateID'], evidence=evidence))
        count['abstentions'] += len(original['abstentionRecords'])
        for view, replay in [('originalReplay', original), ('constructionReplay', effective)]:
            for abstention in replay['abstentionRecords']:
                emit('exceptions', dict(recordType='abstention', requestID=rid, family=key[0], ownerID=key[1],
                                        replayView=view, record=abstention))
        emit('exceptions', dict(recordType='replay_diagnostics', requestID=rid, family=key[0], ownerID=key[1],
            blockingReasons=report['blockingReasons'], conformanceChanges=report.get('conformance', {}).get('changes'),
            originalReplay={k: original.get(k) for k in ('diagnostics', 'sourceDiagnostics', 'sourceCompleteness', 'sourceSnapshot')},
            constructionReplay={k: effective.get(k) for k in ('diagnostics', 'sourceDiagnostics', 'sourceCompleteness')}))
    for unit in units.values():
        unit['selected'] = bool(unit['selectedRequestIDs'])
        unit['citedByAcceptedEvidence'] = bool(unit['acceptedEvidenceReferences'])
        unit['processingIncomplete'] = set(unit['selectedRequestIDs']) != set(unit['processableRequestIDs'])
        unit['zeroYield'] = unit['selected'] and not unit['processingIncomplete'] and not unit['citedByAcceptedEvidence']
        emit('source-unit-coverage', unit)
    families = {}
    for key, count in sorted(stats.items()):
        owner = owners[key]
        owned = [u for k, u in units.items() if k[:2] == key]
        coverage = dict(readerAdmittedUnits=len(owned), productionAdmittedUnits=sum(u['productionAdmitted'] for u in owned),
            excludedUnits=sum(u['excluded'] for u in owned), selectedUnits=sum(u['selected'] for u in owned),
            selectedUnitOccurrences=sum(len(u['selectedRequestIDs']) for u in owned),
            citedUnits=sum(u['citedByAcceptedEvidence'] for u in owned), zeroYieldSelectedUnits=sum(u['zeroYield'] for u in owned),
            processingIncompleteUnits=sum(u['processingIncomplete'] for u in owned),
            packagingHeldUnits=sum(u['packagingHeld'] for u in owned))
        flags = dict(owners=1, ownersWithRequests=int(count['requests'] > 0),
            ownersWithReaderUnits=int(bool(owned)), ownersWithAdmittedUnits=int(coverage['productionAdmittedUnits'] > 0),
            ownersWithCitedUnits=int(coverage['citedUnits'] > 0), ownersWithExcludedUnits=int(coverage['excludedUnits'] > 0),
            sourceIncompleteOwners=int(not owner['inputComplete']),
            processingIncompleteOwners=int(count['requests'] != count['processable']),
            zeroYieldProcessedOwners=int(count['requests'] > 0 and count['requests'] == count['processable'] and
                                        count['acceptedNodes'] + count['acceptedEdges'] == 0))
        emit('family-owner', dict(family=key[0], ownerID=key[1], **count, coverage=coverage, **flags,
            sealedCoverage=owner))
        family = families.setdefault(key[0], {})
        for name, value in {**count, **coverage, **flags}.items():
            if isinstance(value, Counter):
                family.setdefault(name, Counter()).update(value)
            else:
                family[name] = family.get(name, 0) + value
    for (family, owner, kind, inventory_id, name, basis), n in sorted(ontology.items()):
        emit('ontology-types', dict(family=family, ownerID=owner, kind=kind, inventoryId=inventory_id,
            ontologyType=name, acceptanceBasis=basis, acceptedSourceLocalAssertions=n))
    return dict(version='source-family-production-verification/1.0', requests=len(log.entries), families=families,
        acceptedNodes=sum(c['acceptedNodes'] for c in stats.values()), acceptedEdges=sum(c['acceptedEdges'] for c in stats.values()),
        limitations=LIMITATIONS, coverageDefinitions=dict(readerAdmittedUnits='sealed readerSourceUnitIDs',
            productionAdmittedUnits='reader units minus explicit sealed exclusions',
            selectedUnits='distinct owner/unit pairs selected in queued requests',
            citedUnits='selected owner/unit pairs cited by persisted accepted evidence',
            zeroYieldSelectedUnits='selected units with all requests processable and no accepted citation',
            sourceIncompleteOwners='sealed inputComplete=false; not a unit count',
            sourceIncompleteUnits='not inferred from owner flags; exact unit-linked diagnostics appear in sourceDiagnosticRecords'),
        readOnly=True, kgAuthorization=False)


def infrastructure(generator_pins: dict) -> tuple[Any, Any]:
    """Load only pinned journal/cost utilities, avoiding full-corpus dependency audits.

    The operational adapter's infrastructure() also loads the Publications
    preflight and audits its source pins. Reporting needs only the shared journal
    implementation and receipt cost function, so import those pinned modules
    directly through the existing module loader.
    """
    from copy import deepcopy
    import sys
    from types import SimpleNamespace
    from src.extraction.llm.publications import full_corpus_gpt61_production as baseline
    paths = [baseline.V2 / 'stream.py', baseline.V2 / 'journal.py',
             baseline.V2.parent / 'v0.1/preflight.py', baseline.V2.parent / 'v0.1/input-pins.json']
    require(generator_pins == {str(p.relative_to(baseline.ROOT)): file_hash(p) for p in paths},
            'JOURNAL_GENERATOR_DRIFT')
    paired_path = next(p for p in baseline.PINS if p.endswith('/paired.py'))
    require(file_hash(baseline.ROOT / paired_path) == baseline.PINS[paired_path], 'COST_ADAPTER_DRIFT')
    paired = baseline.load_module('source_family_report_cost', baseline.ROOT / paired_path)
    stream = baseline.load_module('source_family_report_stream', paths[0])
    with patch.dict(sys.modules, {'stream': stream}):
        journal = baseline.load_module('source_family_report_journal', paths[1])
    return paired, SimpleNamespace(Journal=journal.Journal, decode=journal.decode, unbundle=deepcopy)


def verify(root: Path, emit: Callable[[str, dict], None]) -> dict:
    """Verify native journal integrity and stored evidence files, then inventory."""
    from src.extraction.llm import source_family_batch as adapter
    wire = (root / 'run-manifest.json').read_bytes()
    manifest = json.loads(wire)
    queue_path = root.parent / 'queue-manifest.json'
    queue = json.loads(queue_path.read_bytes())
    checked_coverage(queue, manifest)
    paired, native = infrastructure(manifest['generatorPins'])

    def receipt_check(prepared: dict, receipt: dict) -> None:
        """Use existing provider-wrapper/hash/usage verification without extraction."""
        require(receipt == adapter.batch.response_record(receipt['row'], prepared, paired,
                receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

    def prepared_check(prepared: dict, entry: dict) -> None:
        """Match journal payload to the exact sealed original bundle bytes."""
        checked_prepared(prepared, entry)
        path = root.parent / 'queue' / entry['bundleFile']
        require(path.resolve().parent == (root.parent / 'queue').resolve(), 'UNSAFE_BUNDLE_PATH')
        data = path.read_bytes()
        require(digest(data) == entry['bundleSha256'] and json.loads(data) == prepared, 'BUNDLE_DRIFT')

    cls = adapter.batch_journal(native, prepared_check, adapter.fingerprint, checked_outcome, receipt_check)
    with read_only_log(root, native, cls, wire) as log:
        hashes = {p.name: file_hash(p) for p in (root / 'run-manifest.json', queue_path, log.path, log.checkpoint)}
        for jid, events in sorted(log.jobs.items()):
            for event in ('plan', 'downloads'):
                if event not in events:
                    continue
                payload = log.job(jid, event)
                for item in [payload] if event == 'plan' else payload['files']:
                    path = root / item['filename']
                    require(path.resolve().parent == root.resolve(), 'UNSAFE_EVIDENCE_PATH')
                    sha = file_hash(path)
                    require(sha == item['sha256'], 'EVIDENCE_FILE_DRIFT:' + path.name)
                    hashes[path.name] = sha
        report = inventory(log, queue, emit)
        report.update(inputHashes=hashes, journalSeq=log.seq, journalHead=log.head,
            implementationSha256=file_hash(Path(__file__)), sealedSummary=queue['summary'],
            persistedAuthorityPins=queue['implementationPins'], persistedSourcePins=queue['sourcePins'])
        report['expectedRequestCounts'] = {'hydroshare': 42, 'github': 275, 'ciroh_hub': 239}
        report['discrepancies'] = [dict(family=f, field=field, expected=n,
            observed=report['families'].get(f, {}).get(field, 0))
            for f, n in report['expectedRequestCounts'].items() for field in ('requests', 'processable')
            if report['families'].get(f, {}).get(field, 0) != n]
        return report


def main() -> None:
    """Publish a new ignored directory only if all offline checks succeed."""
    from contextlib import ExitStack
    import tempfile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output, root = args.output.resolve(), args.root.resolve()
    require(not output.exists(), 'OUTPUT_EXISTS: choose a new output directory')
    require(root.parent != output and root.parent not in output.parents, 'OUTPUT_MUST_BE_OUTSIDE_PRODUCTION_EVIDENCE')
    require(subprocess.run(['git', 'check-ignore', '-q', str(output / 'verification.json')]).returncode == 0,
            'REPORT_OUTPUT_MUST_BE_GIT_IGNORED')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.verification-', dir=output.parent) as temporary:
        folder = Path(temporary)
        with ExitStack() as stack, patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_ONLY')):
            files = {name: stack.enter_context((folder / (name + '.jsonl')).open('w')) for name in
                     ('requests', 'family-owner', 'ontology-types', 'candidate-decisions', 'source-unit-coverage', 'exceptions')}

            def emit(name: str, record: dict) -> None:
                """Stream detailed records without retaining the entire corpus in memory."""
                files[name].write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n')

            report = verify(root, emit)
        (folder / 'verification.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        lines = ['# Three-family production verification', '',
                 f"Requests: {report['requests']}; accepted source-local nodes: {report['acceptedNodes']}; edges: {report['acceptedEdges']}.", '']
        for family, count in sorted(report['families'].items()):
            lines.append(f"- {family}: {count['processable']}/{count['requests']} processable requests; "
                         f"{count['acceptedNodes']} nodes, {count['acceptedEdges']} edges; "
                         f"{count['citedUnits']}/{count['selectedUnits']} selected units cited; "
                         f"{count['sourceIncompleteOwners']}/{count['owners']} owners source-incomplete; "
                         f"construction decisions {dict(count['constructionDecisions'])}; bases {dict(count['acceptanceBases'])}.")
        lines.extend(['', LIMITATIONS, '', 'See verification.json for denominators and hashes; JSONL files retain '
                      'owner coverage, ontology counts, candidate decisions, source spans, abstentions and exceptions.', '',
                      'Expected-count discrepancies: ' + json.dumps(report['discrepancies']), ''])
        (folder / 'summary.md').write_text('\n'.join(lines))
        require(not output.exists(), 'OUTPUT_EXISTS')
        folder.rename(output)
    print(str(args.output))
    if report['discrepancies']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
