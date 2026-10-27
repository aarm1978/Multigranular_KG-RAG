"""Materialize the researcher-selected 22 original + 20 recovery HydroShare owners.

Inputs are read-only. Native projections/records are copied, never reconstructed,
revalidated semantically, deduplicated or merged. Run in the researcher terminal.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack, contextmanager
import fcntl
from pathlib import Path
import subprocess
import tempfile
from typing import Callable, Iterator

from src.evaluation import hydroshare_readme_verification as verification
from src.evaluation.hydroshare_readme_verification import recovery, native
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.publications.resumable_production_journal import require

DEFAULT_OUTPUT = Path('var/study2_step13/hydroshare-definitive-selection/v1')
DECISION = Path('docs/study2_step13_hydroshare_definitive_selection.md')
VERIFIER_CHECKPOINT = '3e1468f293bba04e7de69d14fd64aa2eea1ee4e7'
VERIFIER_SHA = '5227ddd2973db4ca6bb6eb9ae715b3bc93dbb5ed7d2c1d7ba3a33e25ab4a27c9'
EXPECTED_COUNTS = (187, 188)
FILES = ('accepted-projections', 'accepted-nodes', 'accepted-edges', 'selected-outcomes', 'per-owner')


def selection_plan(original: dict, successor: dict) -> list[dict]:
    """Require exact unique owner sets and select whole runs, irrespective of yield."""
    old = native.indexed([e for e in original['requests'] if e['family'] == 'hydroshare'], 'ownerID')
    new = native.indexed(successor['requests'], 'ownerID')
    require(len(old) == 42 and len(new) == 20 and new.keys() <= old.keys() and
            all(e['family'] == 'hydroshare' for e in new.values()), 'OWNER_SET_DRIFT')
    native.indexed([e['identity'] for e in old.values()], 'requestID')
    native.indexed([e['identity'] for e in new.values()], 'requestID')
    require(not {e['identity']['requestID'] for e in old.values()} &
            {e['identity']['requestID'] for e in new.values()}, 'CROSS_RUN_REQUEST_COLLISION')
    for owner, entry in new.items():
        lineage = entry['recoveryProvenance']
        require(lineage['originalRequestID'] == old[owner]['identity']['requestID'] and
                lineage['originalIdentity'] == old[owner]['identity'] and
                lineage['originalBundleSha256'] == old[owner]['bundleSha256'] and
                lineage['overlaySha256'] == verification.OVERLAY_SHA, 'LINEAGE_DRIFT')
    return [dict(ownerID=owner, sourceRun='recovery' if owner in new else 'original',
                 entry=new[owner] if owner in new else old[owner]) for owner in sorted(old)]


def tree_hashes(root: Path) -> dict:
    """Hash all persisted root files; reject links and detect changed input trees."""
    require(root.is_dir() and not root.is_symlink(), 'MISSING_OR_LINKED_INPUT_ROOT')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'LINKED_INPUT_FILE')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = native.file_hash(path)
        else:
            require(path.is_dir(), 'UNSUPPORTED_INPUT_FILE')
    return result


def load_inputs(original: Path, successor: Path) -> tuple[dict, dict, dict, dict, list]:
    """Reuse sealed-queue, source-context and lineage checks without quality comparison."""
    require(native.file_hash(Path(verification.__file__)) == VERIFIER_SHA, 'VERIFIER_CHECKPOINT_DRIFT')
    new, overlay = recovery.load_queue(successor, verification.QUEUE_SHA)
    require(new['bindingOverlaySha256'] == verification.OVERLAY_SHA, 'OVERLAY_DRIFT')
    old = recovery.read_json(original / 'queue-manifest.json')
    runs = {name: recovery.read_json(root / 'production/run-manifest.json')
            for name, root in (('original', original), ('recovery', successor))}
    for relative in ('queue-manifest.json', 'production/run-manifest.json'):
        require(native.file_hash(original / relative) == recovery.ORIGINAL_PINS[str(recovery.ORIGINAL / relative)],
                'ORIGINAL_ROOT_PIN_DRIFT')
    native.checked_coverage(old, runs['original'])
    require(runs['recovery']['parentSha256'] == verification.QUEUE_SHA and
            all(runs['recovery'][k] == new[k] for k in
                ('requests', 'generatorPins', 'implementationPins', 'pricing', 'bindingOverlaySha256')),
            'RECOVERY_RUN_DRIFT')
    plan = selection_plan(old, new)
    sources = native.indexed(recovery.read_json(recovery.ROOT / recovery.SOURCE), 'resource_id')
    predecessors = native.indexed([e for e in old['requests'] if e['family'] == 'hydroshare'], 'ownerID')
    require({b['ownerID'] for b in overlay['bindings']} ==
            {p['ownerID'] for p in plan if p['sourceRun'] == 'recovery'}, 'OVERLAY_OWNER_DRIFT')
    for entry in new['requests']:
        owner = entry['ownerID']
        require(digest(canonical(sources[owner])) == entry['coverage']['sourceRecordSha256'] ==
                predecessors[owner]['coverage']['sourceRecordSha256'], 'SOURCE_RECORD_PIN_DRIFT')
        verification.checked_context(verification.bundle(original, predecessors[owner]),
            verification.bundle(successor, entry), predecessors[owner], entry,
            [b for b in overlay['bindings'] if b['ownerID'] == owner], sources[owner])
    return old, new, runs, overlay, plan


@contextmanager
def open_log(root: Path, run: dict, selected: dict) -> Iterator[object]:
    """Replay the native chain/receipts; check only selected HydroShare construction results."""
    infrastructure, _, paired = recovery.journal_class(run)

    def check_prepared(prepared: dict, entry: dict) -> None:
        """Bind a selected native prepared event to its sealed bundle."""
        if entry['identity']['requestID'] in selected:
            require(entry == selected[entry['identity']['requestID']] and
                    prepared == verification.bundle(root, entry), 'SELECTED_BUNDLE_DRIFT')

    def check_outcome(prepared: dict, receipt: dict, outcome: dict, number: int) -> None:
        """Check hashes/associations in persisted selected outcomes; never apply policy."""
        if prepared['request']['requestID'] in selected:
            native.checked_outcome(prepared, receipt, outcome, number)

    def check_receipt(prepared: dict, receipt: dict) -> None:
        """Reuse native provider receipt and recorded-cost verification."""
        require(receipt == recovery.adapter.batch.response_record(receipt['row'], prepared, paired,
                receipt['batchID'], receipt['number']), 'RECEIPT_DRIFT')

    cls = recovery.adapter.batch_journal(infrastructure, check_prepared,
        recovery.adapter.fingerprint, check_outcome, check_receipt)
    production = root / 'production'
    with native.read_only_log(production, infrastructure, cls, (production / 'run-manifest.json').read_bytes()) as log:
        require(all(log.entries.get(rid) == entry for rid, entry in selected.items()), 'JOURNAL_SELECTION_DRIFT')
        yield log


def selected_owner(log: object, choice: dict) -> dict:
    """Copy the selected terminal outcome and all deliveries from that run only."""
    entry = choice['entry']
    rid = entry['identity']['requestID']
    require(log.entries.get(rid) == entry and log.state.get(rid) == 'completion', 'SELECTED_OWNER_INCOMPLETE')
    receipts = sorted(k for k in log.receipts if k[0] == rid)
    outcomes = sorted(k for k in log.outcomes if k[0] == rid)
    require(receipts == outcomes and bool(outcomes), 'SELECTED_DELIVERY_GAP')
    prepared = log.prepared(rid)
    native.checked_prepared(prepared, entry)
    require(prepared['semanticRequest']['request']['owner']['endpointID'] == choice['ownerID'] and
            prepared['semanticRequest']['request']['artifactFamily'] == 'hydroshare', 'SELECTED_OWNER_DRIFT')
    deliveries = []
    for key in outcomes:
        receipt = log.payload_at(log.receipts[key])
        outcome = log.payload_at(log.outcomes[key])['native']
        native.checked_outcome(prepared, receipt, outcome, key[1])
        deliveries.append(dict(number=key[1], receipt=receipt, native=outcome))
    require(deliveries[-1]['native']['processable'] and
            sum(d['native']['processable'] for d in deliveries) == 1, 'AMBIGUOUS_TERMINAL_OUTCOME')
    return dict(ownerID=choice['ownerID'], sourceRun=choice['sourceRun'], requestID=rid,
                selectedAttempt=outcomes[-1][1], prepared=prepared, deliveries=deliveries)


def emit_selection(plan: list, logs: dict, old_coverage: list, emit: Callable) -> dict:
    """Copy native records without schema changes and index their exact output row ranges."""
    require(len(plan) == len({p['ownerID'] for p in plan}) == 42 and
            Counter(p['sourceRun'] for p in plan) == {'original': 22, 'recovery': 20}, 'SELECTION_COMPLETENESS_DRIFT')
    coverage = native.indexed([o for o in old_coverage if o['family'] == 'hydroshare'], 'ownerID')
    selections, node_count, edge_count = [], 0, 0
    for line, choice in enumerate(sorted(plan, key=lambda p: p['ownerID']), 1):
        selected = selected_owner(logs[choice['sourceRun']], choice)
        outcome = selected['deliveries'][-1]['native']
        report = outcome['productionResult']
        projection = report['projection']
        # All fields, including externalEndpoints, dependencies and local IDs, stay native.
        emit('accepted-projections', projection)
        for record in projection['nodes']:
            emit('accepted-nodes', record)
        for record in projection['edges']:
            emit('accepted-edges', record)
        emit('selected-outcomes', selected)
        original_replay = report['originalReplay']
        effective = report.get('conformance', {}).get('derivedReplay', original_replay)
        entry = choice['entry']
        owner_coverage = coverage[choice['ownerID']] if choice['sourceRun'] == 'original' else dict(
            family='hydroshare', ownerID=choice['ownerID'], inputComplete=True,
            readerSourceUnitIDs=entry['coverage']['selectedSourceUnitIDs'], excludedSourceUnitIDs=[],
            diagnostics=[], groups=[dict(entry['coverage'], requestID=selected['requestID'])])
        count = dict(ownerID=choice['ownerID'], sourceRun=choice['sourceRun'], requestID=selected['requestID'],
            selectedAttempt=selected['selectedAttempt'], acceptedNodes=len(projection['nodes']),
            acceptedEdges=len(projection['edges']), zeroYield=not (projection['nodes'] or projection['edges']),
            constructionDispositions=Counter(d['disposition'] for d in report['decisions']),
            originalReplayDispositions=Counter(r['finalDisposition'] for r in original_replay['finalRecords']),
            constructionReplayDispositions=Counter(r['finalDisposition'] for r in effective['finalRecords']),
            originalAbstentions=original_replay['abstentionRecords'], constructionAbstentions=effective['abstentionRecords'],
            sealedCoverage=owner_coverage)
        emit('per-owner', count)
        selections.append(dict(ownerID=choice['ownerID'], sourceRun=choice['sourceRun'],
            requestID=selected['requestID'], selectedAttempt=selected['selectedAttempt'], identity=entry['identity'],
            bundleSha256=entry['bundleSha256'], productionResultSha256=outcome['productionResultSha256'],
            projectionSha256=report['projectionSha256'], ownerRow=line,
            nodeRows=dict(start=node_count + 1, count=count['acceptedNodes']),
            edgeRows=dict(start=edge_count + 1, count=count['acceptedEdges']), zeroYield=count['zeroYield']))
        node_count += count['acceptedNodes']
        edge_count += count['acceptedEdges']
    require((node_count, edge_count) == EXPECTED_COUNTS,
            f'ACCEPTED_COUNT_DISCREPANCY: expected {EXPECTED_COUNTS}, observed {(node_count, edge_count)}')
    return dict(selections=selections, acceptedNodes=node_count, acceptedEdges=edge_count,
                acceptedTotal=node_count + edge_count, owners=42, originalOwners=22, recoveryOwners=20)


def materialize(original: Path, successor: Path, emit: Callable) -> dict:
    """Verify both read-only roots, copy the selected owners, and prove inputs unchanged."""
    roots = dict(original=original, recovery=successor)
    before = {name: tree_hashes(root) for name, root in roots.items()}
    old, new, runs, _, plan = load_inputs(original, successor)
    with ExitStack() as stack:
        logs = {name: stack.enter_context(open_log(root, runs[name],
            {p['entry']['identity']['requestID']: p['entry'] for p in plan if p['sourceRun'] == name}))
            for name, root in roots.items()}
        require(all(logs['original'].state.get(e['identity']['requestID']) == 'completion'
                    for e in old['requests'] if e['family'] == 'hydroshare'), 'ORIGINAL_HYDROSHARE_INCOMPLETE')
        verification.checked_completion(logs['recovery'], recovery.adapter.batch.summary(logs['recovery']))
        journals = {name: dict(journalSeq=log.seq, journalHead=log.head,
            checkedEvidenceHashes=verification.evidence_files(log, roots[name] / 'production'),
            framingScope='Entire native journal chain and receipts; construction checks restricted to selected owners.')
            for name, log in logs.items()}
        result = emit_selection(plan, logs, old['coverage'], emit)
        require(before == {name: tree_hashes(root) for name, root in roots.items()}, 'PRODUCTION_INPUT_CHANGED')
        recovery.check_pins(new['originalArtifactPins'])
        recovery.check_pins(new['implementationPins'])
    return dict(version='hydroshare-definitive-selection/1.0', **result, journals=journals,
        inputFileHashes=before, recoveryQueueSha256=verification.QUEUE_SHA,
        bindingOverlaySha256=verification.OVERLAY_SHA, sourcePins=new['originalArtifactPins'],
        implementationPins=new['implementationPins'], verifierCheckpoint=VERIFIER_CHECKPOINT,
        verifierSha256=VERIFIER_SHA, materializerSha256=native.file_hash(Path(__file__)),
        selectionDecisionSha256=native.file_hash(recovery.ROOT / DECISION),
        selectionRule='Complete owner replacement: recovery for its 20 owners; original for the other 22.',
        recordSchema='Unchanged native construction projection and accepted records; ownerRow indexes accepted-projections, '
                     'selected-outcomes and per-owner; nodeRows/edgeRows index accepted-nodes/accepted-edges. All rows '
                     'are 1-based JSONL positions. Zero-count ranges select no records. These positions are not semantic IDs.',
        diagnostics='selected-outcomes contains complete native outcomes and receipts for all deliveries of selected runs; '
                    'per-owner retains coverage, abstentions and zero yield. No superseded original owner diagnostics are copied.',
        technicalIntegrity='verified', scientificCorrectness='not adjudicated', kgAuthorization=False, providerCalls=0)


def publish(original: Path, successor: Path, output: Path) -> None:
    """Publish once, serializing materializer writers and refusing every existing destination."""
    require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
    output = output.resolve()
    for root in (original.resolve(), successor.resolve()):
        require(output != root and root not in output.parents and output not in root.parents, 'OUTPUT_OVERLAPS_INPUT')
    require(subprocess.run(['git', 'check-ignore', '-q', str(output / 'selection-manifest.json')],
                          cwd=recovery.ROOT).returncode == 0, 'OUTPUT_MUST_BE_IGNORED')
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.parent / ('.' + output.name + '.lock')).open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not output.exists(), 'OUTPUT_EXISTS')
        with tempfile.TemporaryDirectory(prefix='.selection-', dir=output.parent) as temporary:
            stage = Path(temporary)
            with ExitStack() as stack, recovery.offline():
                files = {name: stack.enter_context((stage / (name + '.jsonl')).open('wb')) for name in FILES}

                def emit(name: str, row: dict) -> None:
                    """Write canonical native JSON records in deterministic selected-owner order."""
                    files[name].write(canonical(row) + b'\n')

                result = materialize(original.resolve(), successor.resolve(), emit)
            (stage / 'summary.md').write_text(
                '# Definitive HydroShare source-local selection\n\n'
                '42 owners: 22 original outcomes and 20 complete recovery replacements.\n'
                f"Accepted records: {result['acceptedNodes']} nodes + {result['acceptedEdges']} edges = {result['acceptedTotal']}.\n\n"
                'Native projections, identities, evidence, dependencies and selected-run diagnostics are preserved.\n'
                'Superseded original owner outcomes are excluded. No candidate merging or identity alignment occurred.\n'
                'Technical integrity and exact selection completeness verified; scientific correctness not adjudicated.\n'
                'See selection-manifest.json for run selection, row mappings, input/output hashes and journal heads.\n', encoding='utf-8')
            result['outputFileHashes'] = {p.name: native.file_hash(p) for p in sorted(stage.iterdir())}
            (stage / 'selection-manifest.json').write_bytes(canonical(result) + b'\n')
            require(not output.exists() and not output.is_symlink(), 'OUTPUT_EXISTS')
            stage.rename(output)


def main() -> None:
    """Expose only offline materialization; full production execution belongs in the terminal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-root', type=Path, default=recovery.ORIGINAL)
    parser.add_argument('--recovery-root', type=Path, default=recovery.DEFAULT_ROOT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    publish(args.original_root, args.recovery_root, args.output)
    print(args.output)


if __name__ == '__main__':
    main()
