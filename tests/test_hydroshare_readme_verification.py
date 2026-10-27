"""Short synthetic tests for paired reporting; all network access is blocked."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.evaluation import hydroshare_readme_verification as report
import test_hydroshare_readme_recovery as recovery_fixtures
from test_source_family_production_verification import fixture, FixtureLog


class PairedTests(unittest.TestCase):
    """Protect pairing, source completeness, accounting and read-only publication."""

    def setUp(self) -> None:
        """Block sockets for every test, including synthetic fixture setup."""
        blocker = patch.object(socket, 'socket', side_effect=RuntimeError('OFFLINE_ONLY'))
        blocker.start()
        self.addCleanup(blocker.stop)

    def context(self) -> tuple:
        """Build a small synthetic predecessor/successor with two full READMEs."""
        helper = recovery_fixtures.RecoveryTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        item = helper.fixture()
        item['entry'].update(ownerID=item['ownerID'], family='hydroshare')
        successor, entry = report.recovery.successor(item, report.OVERLAY_SHA)
        return item['original'], successor, item['entry'], entry, item['bindings'], item['source']

    def test_context_exact_and_immutable(self) -> None:
        """Verify Unicode text, complete dual README units and unchanged source provenance."""
        args = self.context()
        before = deepcopy(args)
        with patch.object(report.recovery, 'successor', side_effect=AssertionError('rebuild')), \
             patch.object(report.recovery.adapter, 'prepare', side_effect=AssertionError('prepare')), \
             patch.object(report.recovery.adapter, 'process', side_effect=AssertionError('process')):
            report.checked_context(*args)
        self.assertEqual(args, before)

    def test_context_tampering(self) -> None:
        """Reject truncation, lineage changes, selection gaps, provenance drift and model changes."""
        original = self.context()
        for damage in ('abstract', 'text', 'id', 'provenance', 'selection', 'lineage', 'model', 'reader', 'source'):
            args = deepcopy(original)
            units = args[1]['semanticRequest']['request']['sourceUnits']
            if damage == 'abstract':
                units[0]['text'] += 'truncated'
            elif damage == 'text':
                units[1]['text'] = units[1]['text'][:-1]
            elif damage == 'id':
                units[1]['sourceUnitID'] = 'different'
            elif damage == 'provenance':
                units[1]['snapshotID'] = 'different'
            elif damage == 'selection':
                args[1]['semanticRequest']['request']['selectedSourceUnitIDs'].pop()
            elif damage == 'lineage':
                args[3]['recoveryProvenance']['originalRequestID'] = 'different'
            elif damage == 'model':
                args[1]['body']['reasoning']['effort'] = 'high'
            elif damage == 'reader':
                args[1]['requestInputs']['readme_results'][0]['inputComplete'] = False
            else:
                args[5]['documentation']['readme_files'].append(dict(source_file='omitted', readme_text_raw='extra'))
            with self.subTest(damage=damage), self.assertRaises(ValueError):
                report.checked_context(*args)

    def inventory(self) -> tuple:
        """Adapt persisted synthetic records to a HydroShare owner and mixed evidence fields."""
        prepared, entry, receipt, outcome, queue = fixture()
        entry['family'] = 'hydroshare'
        for owner in queue['coverage']:
            owner['family'] = 'hydroshare'
        prepared['semanticRequest']['request']['sourceUnits'][0]['sourceField'] = 'abstract'
        prepared['semanticRequest']['request']['sourceUnits'][1]['sourceField'] = 'README'
        receipt['cost']['estimatedUSD'] = 0.125
        accepted = outcome['productionResult']['projection']['edges'][0]
        accepted['boundEvidence'] = [dict(sourceUnitID='u2', evidenceText='two', startLine=1)]
        log = FixtureLog(prepared, entry, receipt, outcome)
        emitted = []
        result = report.paired_inventory(log, queue, {'owner'}, lambda *row: emitted.append(row), 'synthetic')
        return result, log, queue, emitted

    def test_paired_accounting(self) -> None:
        """Separate node/edge proposals, acceptance, holds, suppression, abstentions and citations."""
        result, _, _, emitted = self.inventory()
        owner = result['owner']
        self.assertEqual(owner['candidateKinds'], {'node': 2, 'edge': 2})
        self.assertEqual(owner['statistics']['constructionDecisions'], {'accepted': 2, 'held': 1, 'suppressed_duplicate': 1})
        self.assertEqual(owner['statistics']['abstentions'], 1)
        self.assertEqual(owner['statistics']['zeroYieldRequests'], 0)
        self.assertEqual(owner['evidenceReferencesBySource'], {'abstract': 1, 'README': 1})
        self.assertEqual(owner['acceptedAssertionsBySource'], {'abstract': 1, 'README': 1})
        self.assertEqual(owner['citedReadmeIDs'], ['u2'])
        self.assertEqual(owner['recordedCostUSD'], '0.125')
        self.assertTrue(all(row['ownerID'] == 'owner' for _, row in emitted))

    def test_candidate_ids_do_not_establish_novelty(self) -> None:
        """Renamed IDs leave ontology/evidence occurrence comparisons unchanged."""
        old, _, _, _ = self.inventory()
        new = deepcopy(old)
        for row in new['owner']['details']:
            row['candidateID'] = 'new-' + row['candidateID']
        before = deepcopy((old, new))
        pairs, details = report.compare(old, new)
        self.assertEqual(details[0]['ontologyEvidenceDifferences'], [])
        self.assertEqual(pairs[0]['delta']['candidateOccurrences'], 0)
        self.assertEqual((old, new), before)

    def test_signed_ontology_evidence_and_cost_differences(self) -> None:
        """Persist both removed and added literal evidence signatures with signed counts."""
        old, _, _, _ = self.inventory()
        new = deepcopy(old)
        key = next(iter(new['owner']['ontologyEvidence']))
        del new['owner']['ontologyEvidence'][key]
        replacement = json.dumps(dict(ontologyType='node:Measurement', evidence={'sourceUnitID': 'u2'}))
        new['owner']['ontologyEvidence'][replacement] = 2
        new['owner']['recordedCostUSD'] = '0.25'
        pairs, details = report.compare(old, new)
        self.assertEqual(sorted(r['delta'] for r in details[0]['ontologyEvidenceDifferences']), [-1, 2])
        self.assertEqual(pairs[0]['delta']['recordedCostUSD'], '0.125')
        self.assertEqual(report.compare(old, new), (pairs, details))

    def test_incomplete_or_unpaired_requests_fail(self) -> None:
        """A missing/completion-gap owner cannot masquerade as a zero-yield owner."""
        _, log, queue, _ = self.inventory()
        for owners in ({'absent'}, {'owner', 'absent'}):
            with self.assertRaises(ValueError):
                report.paired_inventory(log, queue, owners, lambda *args: None, 'test')
        log.state = {rid: 'received' for rid in log.entries}
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE'):
            report.paired_inventory(log, queue, {'owner'}, lambda *args: None, 'test')

    def test_zero_yield_retains_held_candidates(self) -> None:
        """Completed zero-yield requests retain candidates and explicit abstentions."""
        _, log, queue, _ = self.inventory()
        production = log.payloads['outcome']['native']['productionResult']
        production['projection'].update(nodes=[], edges=[])
        for decision in production['decisions']:
            if decision['disposition'] == 'accepted':
                decision.update(disposition='held', acceptanceBasis=None)
        result = report.paired_inventory(log, queue, {'owner'}, lambda *args: None, 'test')['owner']
        self.assertEqual(result['statistics']['zeroYieldRequests'], 1)
        self.assertEqual(result['statistics']['candidateOccurrences'], 4)
        self.assertEqual(result['statistics']['abstentions'], 1)
        self.assertEqual(result['citedReadmeIDs'], [])

    def test_completion_cost_and_batch_guards(self) -> None:
        """Reject uncertain spend, unsettled work and wrong provider batch identity."""
        status = dict(completed=20, actualUSD=0.5696416, failed=0, pending=0, unknownUsageAttempts=0,
            outstandingBatches=0, outstandingRequests=0, uncertainSubmissionRequests=0, conservativeCostAttempts=0)
        log = SimpleNamespace(receipts={('request', 1): 1}, payload_at=lambda offset: {'batchID': report.BATCH_ID})
        report.checked_completion(log, status)
        for field in status:
            bad = dict(status)
            bad[field] = None if field == 'actualUSD' else 19 if field == 'completed' else 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                report.checked_completion(log, bad)
        with self.assertRaisesRegex(ValueError, 'COST'):
            report.checked_completion(log, dict(status, actualUSD=0.57))
        log.payload_at = lambda offset: {'batchID': 'different'}
        with self.assertRaisesRegex(ValueError, 'BATCH'):
            report.checked_completion(log, status)

    def test_bundle_bytes_and_paths(self) -> None:
        """Reject corrupt bytes and path escapes before inspecting a persisted bundle."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'queue').mkdir()
            (root / 'queue/a.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'BUNDLE_DRIFT'):
                report.bundle(root, dict(bundleFile='a.json', bundleSha256='bad'))
            with self.assertRaisesRegex(ValueError, 'UNSAFE'):
                report.bundle(root, dict(bundleFile='../a.json', bundleSha256='bad'))

    def test_publish_failure_and_boundaries(self) -> None:
        """No partial report is published on failure; input roots and existing reports are protected."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            original, successor = base / 'original', base / 'successor'
            original.mkdir()
            successor.mkdir()
            (original / 'sentinel').write_bytes(b'original')
            (successor / 'sentinel').write_bytes(b'successor')
            for output in (original / 'report', successor / 'report', base):
                with patch.object(sys, 'argv', ['verify', '--original-root', str(original),
                        '--successor-root', str(successor), '--output', str(output)]), self.assertRaises(ValueError):
                    report.main()
            output = base / 'reports/v1'
            argv = ['verify', '--original-root', str(original), '--successor-root', str(successor), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(report.subprocess, 'run',
                    return_value=SimpleNamespace(returncode=0)), patch.object(report, 'verify', side_effect=ValueError('broken')):
                with self.assertRaisesRegex(ValueError, 'broken'):
                    report.main()
            self.assertFalse(output.exists())
            self.assertEqual(list(output.parent.iterdir()), [])
            self.assertEqual((original / 'sentinel').read_bytes(), b'original')
            self.assertEqual((successor / 'sentinel').read_bytes(), b'successor')

    def test_publish_deterministic_files_and_socket_block(self) -> None:
        """CLI blocks networking and publishes only a successfully completed report."""
        def synthetic_verify(original, successor, emit):
            """Use tiny deterministic output without replaying production evidence."""
            with self.assertRaisesRegex(RuntimeError, 'OFFLINE_ONLY'):
                socket.socket()
            return dict(totals={v: dict(candidateOccurrences=1, acceptedNodes=1, acceptedEdges=0,
                abstentions=0, zeroYieldRequests=0, citedReadmeUnits=1, constructionDecisions={'accepted': 1},
                acceptanceBases={'policy_ordinary_inclusion': 1}, evidenceReferencesBySource={'README': 1}) for v in ('original', 'successor')})

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / 'reports/v1'
            with patch.object(sys, 'argv', ['verify', '--original-root', str(base / 'original'),
                    '--successor-root', str(base / 'successor'), '--output', str(output)]), \
                 patch.object(report.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
                 patch.object(report, 'verify', synthetic_verify):
                report.main()
                self.assertEqual({p.name for p in output.iterdir()}, {'summary.md', 'verification.json',
                    'per-owner.jsonl', 'comparison.jsonl', 'requests.jsonl', 'family-owner.jsonl',
                    'ontology-types.jsonl', 'candidate-decisions.jsonl', 'source-unit-coverage.jsonl', 'exceptions.jsonl'})
                with self.assertRaisesRegex(ValueError, 'OUTPUT_EXISTS'):
                    report.main()


if __name__ == '__main__':
    unittest.main()
