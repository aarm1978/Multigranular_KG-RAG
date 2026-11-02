"""Synthetic offline tests for whole-owner selection; no production materialization."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.evaluation import hydroshare_definitive_selection as selection
from test_source_family_production_verification import fixture


def sealed_fixture(owner: str, run: str, zero: bool = False) -> tuple:
    """Reseal synthetic native records, retaining intentionally colliding candidate IDs."""
    p, entry, receipt, outcome, queue = fixture()
    body = p['semanticRequest']['request']
    body.update(artifactFamily='hydroshare', owner={'endpointID': owner})
    body['sourceUnits'][0]['text'] = run
    sha = selection.native.replay_hash(body)
    p['semanticRequest']['requestSha256'] = sha
    p['request']['requestID'] = 'hydroshare:' + sha
    p['binding']['sourceSha256'] = selection.digest(selection.canonical(body['sourceUnits']))
    entry.update(family='hydroshare', ownerID=owner, identity=selection.recovery.adapter.fingerprint(p),
                 bundleSha256=selection.digest(selection.canonical(p)))
    entry['coverage'].update(family='hydroshare', ownerID=owner)
    receipt['batchID'] = selection.verification.BATCH_ID
    report = outcome['productionResult']
    original = report['originalReplay']
    effective = report['conformance']['derivedReplay']
    for replay in (original, effective):
        replay.update(requestResult=p['semanticRequest'], artifactFamily='hydroshare',
                      requestSha256=sha, expectedRequestSha256=sha, diagnostics=[{'selectedRunMarker': run}])
    projection = report['projection']
    if zero:
        projection.update(nodes=[], edges=[])
        for decision in report['decisions']:
            if decision['disposition'] == 'accepted':
                decision.update(disposition='held', acceptanceBasis=None)
    # Persist a dependency and external endpoints to test exact native preservation.
    projection['externalEndpoints'] = [{'endpointID': 'external:' + owner, 'provenance': run}]
    if projection['edges']:
        projection['edges'][0]['dependencies'] = ['a']
    effective_sha = selection.native.replay_hash(effective)
    report['originalReplaySha256'] = selection.native.replay_hash(original)
    report['conformance'].update(derivedReplaySha256=effective_sha, semanticRequestSha256=sha)
    projection.update(owner=body['owner'], artifactFamily='hydroshare', requestSha256=sha, replaySha256=effective_sha)
    for row in projection['nodes'] + projection['edges']:
        row['replayRecordReference']['replaySha256'] = effective_sha
    report['projectionSha256'] = selection.digest(selection.canonical(projection))
    outcome['productionResultSha256'] = selection.digest(selection.canonical(report))
    outcome['attempt']['requestInputSha256'] = sha
    outcome['provenance'].update(identity=entry['identity'], responseSha256=selection.digest(selection.canonical(receipt)))
    coverage = queue['coverage'][0]
    coverage.update(family='hydroshare', ownerID=owner,
                    groups=[dict(entry['coverage'], requestID=p['request']['requestID'])])
    return p, entry, receipt, outcome, coverage


class Log:
    """Small in-memory native journal view containing only synthetic records."""

    def __init__(self, fixtures: list) -> None:
        """Index distinct requests and payloads using the production reader interface."""
        self.entries, self.state, self.receipts, self.outcomes, self.bundles, self.payloads = {}, {}, {}, {}, {}, {}
        self.seq, self.head = 1, 'synthetic-head'
        for p, entry, receipt, outcome, _ in fixtures:
            rid = entry['identity']['requestID']
            self.entries[rid] = entry
            self.state[rid] = 'completion'
            self.bundles[rid] = p
            self.receipts[rid, 1] = ('receipt', rid)
            self.outcomes[rid, 1] = ('outcome', rid)
            self.payloads['receipt', rid] = receipt
            self.payloads['outcome', rid] = {'native': outcome}

    def prepared(self, rid: str) -> dict:
        """Return a stored prepared fixture, never reconstruct a request."""
        return self.bundles[rid]

    def payload_at(self, offset: tuple) -> dict:
        """Read a synthetic persisted payload."""
        return self.payloads[offset]


def inputs(zero: bool = False) -> tuple:
    """Create 42 original owners and 20 exact lineage-linked successors."""
    old = [sealed_fixture(f'owner-{i:02}', 'original') for i in range(42)]
    new = [sealed_fixture(f'owner-{i:02}', 'recovery', zero and i == 0) for i in range(20)]
    for before, after in zip(old, new):
        after[1]['recoveryProvenance'] = dict(originalRequestID=before[1]['identity']['requestID'],
            originalIdentity=before[1]['identity'], originalBundleSha256=before[1]['bundleSha256'],
            overlaySha256=selection.verification.OVERLAY_SHA)
    queues = dict(requests=[x[1] for x in old], coverage=[x[4] for x in old]), dict(requests=[x[1] for x in new])
    return *queues, {'original': Log(old), 'recovery': Log(new)}


class SelectionTests(unittest.TestCase):
    """Test only the new materializer's selection and publication boundaries."""

    def setUp(self) -> None:
        """Block sockets and all processing/quality comparison entry points."""
        for target in ('socket.socket', 'src.extraction.llm.source_family_batch.prepare',
                       'src.extraction.llm.source_family_batch.process',
                       'src.extraction.llm.construction_acceptance.project_replay',
                       'src.evaluation.hydroshare_readme_verification.verify',
                       'src.evaluation.hydroshare_readme_verification.compare'):
            blocker = patch(target, side_effect=AssertionError('FORBIDDEN_CALL:' + target))
            blocker.start()
            self.addCleanup(blocker.stop)

    def test_replacement_identity_diagnostics_and_zero_yield(self) -> None:
        """A zero-yield successor still replaces its productive original in full."""
        old, new, logs = inputs(zero=True)
        plan = selection.selection_plan(old, new)
        before = deepcopy((old, new, [log.__dict__ for log in logs.values()]))
        emitted = {}
        with patch.object(selection, 'EXPECTED_COUNTS', (41, 41)):
            result = selection.emit_selection(plan, logs, old['coverage'],
                lambda name, row: emitted.setdefault(name, []).append(row))
        self.assertEqual((result['owners'], result['originalOwners'], result['recoveryOwners']), (42, 22, 20))
        self.assertEqual(len(emitted['selected-outcomes']), 42)
        for i, selected in enumerate(emitted['selected-outcomes']):
            expected_run = 'recovery' if i < 20 else 'original'
            self.assertEqual(selected['sourceRun'], expected_run)
            self.assertEqual(selected['deliveries'][-1]['native']['productionResult']['originalReplay']['diagnostics'],
                             [{'selectedRunMarker': expected_run}])
            self.assertEqual(selected['prepared']['semanticRequest']['request']['sourceUnits'][0]['text'], expected_run)
            native = selected['deliveries'][-1]['native']['productionResult']['projection']
            self.assertEqual(emitted['accepted-projections'][i], native)
            self.assertEqual(result['selections'][i]['projectionSha256'], selection.digest(selection.canonical(native)))
            self.assertEqual(len(emitted['per-owner'][i]['originalAbstentions']), 1)
        self.assertTrue(emitted['per-owner'][0]['zeroYield'])
        self.assertEqual(emitted['per-owner'][0]['constructionDispositions'], {'held': 3, 'suppressed_duplicate': 1})
        self.assertEqual(result['selections'][0]['nodeRows']['count'], 0)
        self.assertEqual(len(emitted['accepted-nodes']), 41)
        self.assertEqual({r['candidateID'] for r in emitted['accepted-nodes']}, {'a'})
        self.assertTrue(all(r['dependencies'] == ['a'] for r in emitted['accepted-edges']))
        self.assertEqual((old, new, [log.__dict__ for log in logs.values()]), before)
        again = {}
        with patch.object(selection, 'EXPECTED_COUNTS', (41, 41)):
            self.assertEqual(selection.emit_selection(plan, logs, old['coverage'],
                lambda name, row: again.setdefault(name, []).append(row)), result)
        self.assertEqual(selection.canonical(emitted), selection.canonical(again))

    def test_owner_sets_and_lineage_fail_closed(self) -> None:
        """Refuse missing, duplicate, foreign or wrongly linked owners and requests."""
        original, successor, _ = inputs()
        for problem in ('old_missing', 'new_missing', 'duplicate', 'foreign', 'lineage', 'request_collision', 'family'):
            old, new = deepcopy((original, successor))
            if problem == 'old_missing':
                old['requests'].pop()
            elif problem == 'new_missing':
                new['requests'].pop()
            elif problem == 'duplicate':
                new['requests'][1] = new['requests'][0]
            elif problem == 'foreign':
                new['requests'][0]['ownerID'] = 'foreign'
            elif problem == 'lineage':
                new['requests'][0]['recoveryProvenance']['originalBundleSha256'] = 'wrong'
            elif problem == 'request_collision':
                new['requests'][0]['identity']['requestID'] = old['requests'][0]['identity']['requestID']
            else:
                new['requests'][0]['family'] = 'github'
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                selection.selection_plan(old, new)

    def test_missing_corrupt_or_incomplete_selected_outcome(self) -> None:
        """Never substitute the original if a selected successor is unavailable or corrupt."""
        old, new, logs = inputs()
        choice = selection.selection_plan(old, new)[0]
        rid = choice['entry']['identity']['requestID']
        for problem in ('receipt', 'outcome', 'state', 'hash', 'owner'):
            log = deepcopy(logs['recovery'])
            if problem == 'receipt':
                del log.receipts[rid, 1]
            elif problem == 'outcome':
                del log.outcomes[rid, 1]
            elif problem == 'state':
                log.state[rid] = 'pending'
            elif problem == 'hash':
                log.payloads['outcome', rid]['native']['productionResult']['projection']['nodes'][0]['sourceLocalCandidateID'] = 'corrupt'
            else:
                log.bundles[rid]['semanticRequest']['request']['owner']['endpointID'] = 'wrong'
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                selection.selected_owner(log, choice)

    def test_expected_authoritative_counts_are_enforced(self) -> None:
        """Synthetic totals cannot silently replace the researcher-provided 187/188 expectation."""
        old, new, logs = inputs()
        self.assertEqual(selection.EXPECTED_COUNTS, (187, 188))
        with self.assertRaisesRegex(ValueError, 'ACCEPTED_COUNT_DISCREPANCY'):
            selection.emit_selection(selection.selection_plan(old, new), logs, old['coverage'], lambda *args: None)

    def test_missing_or_corrupt_pinned_queue(self) -> None:
        """The real queue loader rejects missing bytes and a wrong sealed queue digest."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original, successor = root / 'original', root / 'recovery'
            successor.mkdir()
            with patch.object(selection.recovery, 'assert_isolated'):
                with self.assertRaises(FileNotFoundError):
                    selection.load_inputs(original, successor)
                (successor / 'queue-manifest.json').write_bytes(b'{}\n')
                with self.assertRaisesRegex(ValueError, 'RECOVERY_QUEUE_PIN_DRIFT'):
                    selection.load_inputs(original, successor)
                self.assertEqual((successor / 'queue-manifest.json').read_bytes(), b'{}\n')

    def test_input_tree_hashes_detect_changes_and_missing_inputs(self) -> None:
        """Full input hashes retain exact bytes; missing roots and symlinks fail closed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'file').write_bytes(b'original')
            before = selection.tree_hashes(root)
            (root / 'file').write_bytes(b'changed')
            self.assertNotEqual(before, selection.tree_hashes(root))
            with self.assertRaisesRegex(ValueError, 'MISSING'):
                selection.tree_hashes(root / 'absent')
            (root / 'link').symlink_to(root / 'file')
            with self.assertRaisesRegex(ValueError, 'LINKED'):
                selection.tree_hashes(root)

    def test_materialize_composition_preserves_roots_and_detects_drift(self) -> None:
        """Exercise orchestration and exact selected records without a production journal replay."""
        old, new, logs = inputs()
        new.update(originalArtifactPins={}, implementationPins={})
        plan = selection.selection_plan(old, new)

        @contextmanager
        def synthetic_log(root, run, selected):
            """Supply a stored synthetic journal view and assert exact selected request scope."""
            name = root.name
            self.assertEqual(len(selected), 22 if name == 'original' else 20)
            yield logs[name]

        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp) / name for name in ('original', 'recovery')]
            for root in roots:
                root.mkdir()
                (root / 'evidence').write_bytes(b'unchanged')
            with patch.object(selection, 'load_inputs', return_value=(old, new, {'original': {}, 'recovery': {}}, {}, plan)), \
                 patch.object(selection, 'open_log', synthetic_log), \
                 patch.object(selection.verification, 'checked_completion'), \
                 patch.object(selection.recovery.adapter.batch, 'summary', return_value={}), \
                 patch.object(selection.verification, 'evidence_files', return_value={}), \
                 patch.object(selection, 'EXPECTED_COUNTS', (42, 42)):
                result = selection.materialize(*roots, lambda *args: None)
                self.assertEqual(result['owners'], 42)
                self.assertEqual(result['journals']['recovery']['journalHead'], 'synthetic-head')
                self.assertEqual([root.joinpath('evidence').read_bytes() for root in roots], [b'unchanged'] * 2)

                def change_input(name, row):
                    """Simulate an independent writer to prove publication fails on input drift."""
                    roots[0].joinpath('evidence').write_bytes(b'concurrent-change')

                with self.assertRaisesRegex(ValueError, 'PRODUCTION_INPUT_CHANGED'):
                    selection.materialize(*roots, change_input)

    def test_publish_immutable_and_no_partial_output(self) -> None:
        """Publish native bytes once; failed or repeated runs cannot overwrite outputs or inputs."""
        def synthetic(original, successor, emit):
            """Produce a tiny result with the CLI network block active."""
            with self.assertRaises(RuntimeError):
                socket.socket()
            for name in selection.FILES:
                emit(name, {'native': 'unchanged'})
            return dict(acceptedNodes=187, acceptedEdges=188, acceptedTotal=375)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original, successor, output = base / 'original', base / 'recovery', base / 'reports/v1'
            original.mkdir()
            successor.mkdir()
            (original / 'input').write_bytes(b'preserve')
            with patch.object(selection.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
                 patch.object(selection, 'materialize', synthetic):
                selection.publish(original, successor, output)
                before = selection.tree_hashes(output)
                self.assertEqual(set(before), {name + '.jsonl' for name in selection.FILES} | {'summary.md', 'selection-manifest.json'})
                manifest = json.loads((output / 'selection-manifest.json').read_bytes())
                self.assertEqual(manifest['outputFileHashes'], {k: v for k, v in before.items() if k != 'selection-manifest.json'})
                with self.assertRaisesRegex(ValueError, 'OUTPUT_EXISTS'):
                    selection.publish(original, successor, output)
                self.assertEqual(before, selection.tree_hashes(output))
                with self.assertRaisesRegex(ValueError, 'OVERLAPS'):
                    selection.publish(original, successor, original / 'output')
            with patch.object(selection.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
                 patch.object(selection, 'materialize', side_effect=ValueError('corrupt-input')):
                with self.assertRaisesRegex(ValueError, 'corrupt-input'):
                    selection.publish(original, successor, base / 'reports/failed')
                self.assertFalse((base / 'reports/failed').exists())
            with patch.object(selection.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
                with self.assertRaisesRegex(ValueError, 'IGNORED'):
                    selection.publish(original, successor, base / 'unignored')
            self.assertEqual((original / 'input').read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
