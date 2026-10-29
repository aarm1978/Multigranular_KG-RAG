"""Offline 1004+1 derived review; immutable inputs and no provider operations."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import socket
from unittest.mock import patch

from src.evaluation import source_local_single_live_retry as retry
from src.evaluation import source_local_specialized_production as production
from src.evaluation import source_local_specialized_pilot as pilot
from src.evaluation import github_full_document_pilot_execution as execution
from src.evaluation import hub_full_content_pilot_batch as hub
from src.extraction.llm import source_local_specialized as semantic

require, digest, canonical = retry.require, retry.digest, retry.canonical
SUPPLEMENT_ID = 'resp_03dac430efd48bbb016ae354d96be487d28f63e0aff5b883ae'
SUPPLEMENT_SHA = 'd911d7478b41bc65f4994c85ce0c2ad72499db038c55bd957ee7199c91b86913'
OUTPUT = Path('var/study2_step13/source-local-supplemental-review/v1')


def select(entries, receipts, supplement, expected_count=1005):
    """Replace exactly the designated incomplete response in a new selection mapping."""
    ids = [e['identity']['requestID'] for e in entries]
    require(len(ids) == expected_count and len(set(ids)) == expected_count, 'DUPLICATE_OR_MISSING_REQUESTS')
    require(set(receipts) == set(ids), 'MISSING_OR_EXTRA_RESPONSES')
    incomplete = [rid for rid, row in receipts.items() if row['providerResponse']['status'] != 'completed']
    require(incomplete == [retry.REQUEST_ID], 'UNEXPECTED_INCOMPLETE_SET')
    original = receipts[retry.REQUEST_ID]['providerResponse']
    require(original['id'] == retry.RESPONSE_ID and original['status'] == 'incomplete' and
            original['incomplete_details'] == {'reason': 'max_output_tokens'}, 'ORIGINAL_RESPONSE_DRIFT')
    require(supplement['id'] == SUPPLEMENT_ID and digest(canonical(supplement)) == SUPPLEMENT_SHA and
            supplement['status'] == 'completed', 'SUPPLEMENT_HASH_OR_ID_DRIFT')
    return {rid: supplement if rid == retry.REQUEST_ID else receipts[rid]['providerResponse'] for rid in ids}


def load_supplement(repo, prepared):
    """Bind response, intent, outcome and authentic saved replay to the frozen request."""
    root = repo / retry.OUTPUT
    records = {name: json.loads((root / (name + '.json')).read_bytes())
               for name in ('intent', 'outcome', 'response', 'semantic-replay')}
    intent, outcome, response = (records[k] for k in ('intent', 'outcome', 'response'))
    expected = dict(requestID=retry.REQUEST_ID, originalResponseID=retry.RESPONSE_ID,
        originalJobID='job-000003', queueSha256=retry.QUEUE_SHA, runManifestSha256=retry.files.RUN_SHA,
        bundleSha256=retry.BUNDLE_SHA, providerBodySha256=digest(canonical(prepared['body'])),
        providerParameterChanges={}, timeoutSeconds=600, maxRetries=0, authorizedPosts=1, sdkVersion='1.109.1')
    require(intent == expected, 'SUPPLEMENT_INTENT_DRIFT')
    require(response['id'] == SUPPLEMENT_ID and digest(canonical(response)) == SUPPLEMENT_SHA,
            'SUPPLEMENT_HASH_OR_ID_DRIFT')
    require(outcome == dict(status='validated_supplemental_response', usable=True,
        responseID=SUPPLEMENT_ID, usage=response['usage'], responseSha256=SUPPLEMENT_SHA,
        integrated=False, kgAuthorization=False), 'SUPPLEMENT_OUTCOME_DRIFT')
    report = retry.validate_response(prepared, response)
    require(report == records['semantic-replay'], 'SUPPLEMENT_REPLAY_DRIFT')
    return response, {name: digest((root / (name + '.json')).read_bytes()) for name in records}


def read_original(repo, bundles):
    """Reuse native journal replay, receipt validation and sealed execution-file checks."""
    root = repo / retry.QUEUE / 'execution/batch'
    raw = (root / 'run-manifest.json').read_bytes()
    require(digest(raw) == retry.files.RUN_SHA, 'RUN_MANIFEST_DRIFT')
    def verify(prepared, entry):
        """Enforce queue identity and exact bundle bytes at the native replay boundary."""
        rid = entry['identity']['requestID']
        require(prepared == bundles[rid] and retry.adapter.fingerprint(prepared) == entry['identity'] and
                digest(canonical(prepared) + b'\n') == entry['bundleSha256'], 'BUNDLE_IDENTITY_DRIFT')
    Journal, native, _, _ = pilot.bind(hub.infrastructure, verify_prepared=verify)()
    log = Journal(root / 'execution.jsonl', raw, digest(raw))
    def collect(log):
        """Require exactly one receipt and outcome per original identity, with no holds."""
        expected = {(rid, 1) for rid in bundles}
        require(set(log.receipts) == expected and set(log.outcomes) == expected, 'RECEIPT_COVERAGE_DRIFT')
        rows = {}
        for rid in bundles:
            outcome = log.payload_at(log.outcomes[rid, 1])['native']
            require(not outcome['transportHolds'], 'TRANSPORT_HOLD:' + rid)
            rows[rid] = log.payload_at(log.receipts[rid, 1])
        return rows, dict(seq=log.seq, headSha256=log.head)
    return execution.readonly(log, native, collect)


def derive(entries, bundles, responses, destination):
    """Validate every selected response; retain failures and consolidate complete owners only."""
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'groups').mkdir(); (destination / 'owners').mkdir()
    by_owner = defaultdict(list); expected = Counter(e['ownerID'] for e in entries)
    counts = Counter({k: 0 for k in ('successfulValidations', 'failedValidations', 'unresolvedAssertions',
        'abstentions', 'zeroYieldRequests', 'completeOwners', 'incompleteOwners', 'nodes', 'edges',
        'derivedConstructionInputs', 'zeroYieldOwners')}); dispositions = Counter(); families = Counter(); groups = Counter(); failures = []
    for entry in entries:
        rid = entry['identity']['requestID']; prepared = bundles[rid]
        families[entry['family']] += 1; groups[entry['family'] + ':' + entry['groupID']] += 1
        try:
            report = retry.validate_response(prepared, responses[rid])
            require(report['nativeValidationView']['status'] == 'projection_completed', 'SEMANTIC_PROJECTION_BLOCKED')
        except Exception as exc:
            failures.append(dict(requestID=rid, ownerID=entry['ownerID'], exceptionType=type(exc).__name__, reason=str(exc)))
            counts['failedValidations'] += 1
            continue
        counts['successfulValidations'] += 1
        native = report['nativeValidationView']
        dispositions.update(d['disposition'] for d in native['decisions'])
        counts['unresolvedAssertions'] += len(report['unresolvedAssertions'])
        counts['abstentions'] += len(report['abstentions'])
        counts['zeroYieldRequests'] += bool(report['zeroYield'])
        retry.files.seal(destination / 'groups' / (digest(rid.encode()) + '.json'), report)
        by_owner[entry['ownerID']].append((prepared, report))
    owner_failures = []
    for owner, total in sorted(expected.items()):
        try:
            require(len(by_owner[owner]) == total, 'INCOMPLETE_VALIDATED_GROUPS')
            consolidated = semantic.consolidate(by_owner[owner])
        except Exception as exc:
            counts['incompleteOwners'] += 1
            owner_failures.append(dict(ownerID=owner, exceptionType=type(exc).__name__, reason=str(exc)))
            continue
        counts['completeOwners'] += 1
        for key in ('nodes', 'edges', 'derivedConstructionInputs'):
            counts[key] += len(consolidated[key])
        counts['zeroYieldOwners'] += bool(consolidated['zeroYield'])
        retry.files.seal(destination / 'owners' / (digest(owner.encode()) + '.json'), consolidated)
    return dict(counts=dict(counts), decisionDispositions=dict(dispositions), requestsByFamily=dict(families),
        requestsByFamilyAndGroup=dict(groups), validationFailures=failures, ownerFailures=owner_failures,
        acceptedCountScope='Consolidated complete owners only; successful group projections retained separately',
        diagnosticCountScope='Successful group reports; not deduplicated across groups', providerCalls=0, kgAuthorization=False)


def run(repo=retry.ROOT, output=OUTPUT):
    """Write a new derived review only after all immutable-input and replacement checks."""
    destination = repo / output
    require(not destination.exists(), 'OUTPUT_ALREADY_EXISTS')
    parent, bundles = production.load_queue(repo, retry.QUEUE, retry.QUEUE_SHA)
    receipts, head = read_original(repo, bundles)
    supplement, supplement_hashes = load_supplement(repo, bundles[retry.REQUEST_ID])
    selected = select(parent['requests'], receipts, supplement)
    summary = derive(parent['requests'], bundles, selected, destination)
    paired, _, _ = retry.adapter.infrastructure()
    summary['accounting'] = dict(originalBatch=dict(requests=1005, completed=1004, incomplete=1,
        receiptCosts={rid: row['cost'] for rid, row in receipts.items()},
        receiptUsage={rid: row['usage'] for rid, row in receipts.items()}),
        supplementalLive=dict(usage=supplement['usage'],
            pricing=retry.adapter.batch.baseline.PRICING,
            cost=paired.usage_cost(supplement, retry.adapter.batch.baseline.PRICING)))
    manifest = dict(queueSha256=retry.QUEUE_SHA, runManifestSha256=retry.files.RUN_SHA,
        journalHead=head, supplementalFileHashes=supplement_hashes,
        selection=[dict(requestID=e['identity']['requestID'], ownerID=e['ownerID'],
            source='supplemental_live' if e['identity']['requestID'] == retry.REQUEST_ID else 'original_batch',
            responseID=selected[e['identity']['requestID']]['id'],
            responseSha256=digest(canonical(selected[e['identity']['requestID']]))) for e in parent['requests']],
        replacement=dict(requestID=retry.REQUEST_ID, originalResponseID=retry.RESPONSE_ID,
            supplementalResponseID=SUPPLEMENT_ID, supplementalResponseSha256=SUPPLEMENT_SHA))
    retry.files.seal(destination / 'selection-manifest.json', manifest)
    retry.files.seal(destination / 'summary.json', summary)
    text = ('# Derived supplemental review\n\n'
        'Selection: 1004 original completed Batch responses + 1 supplemental live response.\n\n'
        'Supplemental response: `' + SUPPLEMENT_ID + '`.\n\n'
        'Counts are technical validation/construction results, not scientific correctness estimates.\n\n'
        + json.dumps({k: summary[k] for k in ('counts', 'decisionDispositions', 'requestsByFamily',
            'requestsByFamilyAndGroup', 'acceptedCountScope', 'diagnosticCountScope')}, indent=2)
        + '\n\nSee summary.json for explicit failures and separate accounting; selection-manifest.json for provenance.')
    with (destination / 'summary.md').open('x') as handle: handle.write(text + '\n')
    return dict(output=str(destination), **summary['counts'], providerCalls=0)


def main():
    """Block sockets for the entire offline review, including dependency loading."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    with patch.object(socket.socket, 'connect', side_effect=RuntimeError('OFFLINE_ONLY')), \
         patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('OFFLINE_ONLY')), \
         production.ontology_parse_cache():
        print(json.dumps(run(), indent=2))


if __name__ == '__main__': main()
