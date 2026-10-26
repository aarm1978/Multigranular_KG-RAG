"""Quick synthetic reporting tests; no authentic production verification runs."""
from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import source_family_production_verification as reporting
from src.extraction.llm.pilot_preflight import canonical, digest
from src.extraction.llm.source_family_batch import fingerprint


def fixture() -> tuple[dict, dict, dict, dict, dict]:
    """Build stored synthetic records, including distinct authentic/derived views."""
    body = dict(artifactFamily='github', owner={'endpointID': 'owner'}, selectedSourceUnitIDs=['u1', 'u2'],
                sourceUnits=[{'sourceUnitID': 'u1', 'text': 'é'}, {'sourceUnitID': 'u2', 'text': 'two'}])
    sha = reporting.replay_hash(body)
    prepared = dict(request={'requestID': 'github:' + sha}, semanticRequest=dict(request=body, requestSha256=sha),
                    requestInputs={}, body={'model': 'synthetic'}, binding={})
    prepared['binding'] = dict(sourceSha256=digest(canonical(body['sourceUnits'])),
                               providerEnvelopeSha256=digest(canonical(prepared['body'])))
    rid = prepared['request']['requestID']
    group = dict(family='github', ownerID='owner', primarySourceUnitIDs=['u1', 'u2'], selectedSourceUnitIDs=['u1', 'u2'])
    entry = dict(identity=fingerprint(prepared), family='github', ownerID='owner', coverage=group, bundleSha256='bundle')
    receipt = dict(number=1, rawModelOutputBase64=base64.b64encode(b'original').decode(), row={}, cost={})
    rows = []
    for cid, disposition, kind, inv, name in [('a', 'validated', 'node', 'A-C08', 'Function'),
            ('b', 'unresolved_condition', 'edge', 'C-C08', 'hasFunction'),
            ('c', 'unresolved_condition', 'node', 'A-C10', 'ModelVersion'),
            ('d', 'suppressed_duplicate', 'edge', 'C-C08', 'hasFunction')]:
        candidate = dict(candidateID=cid, inventoryId=inv, **{'class' if kind == 'node' else 'relation': name})
        validation = dict(boundEvidence=[dict(sourceUnitID='u1', evidenceText='é', startLine=1)],
                          sourceLocalCandidateID='local:' + cid, dependencies=[])
        rows.append(dict(candidateID=cid, kind=kind, originalCandidate=candidate,
                         finalDisposition=disposition, validationRecord=validation))
    replay = dict(requestResult=prepared['semanticRequest'], artifactFamily='github', requestSha256=sha,
                  expectedRequestSha256=sha, requestAssociation='matched_caller_supplied_digest',
                  responseBytesHex=b'original'.hex(), responseSha256=digest(b'original'),
                  finalRecords=deepcopy(rows), abstentionRecords=[{'abstentionID': 'skip', 'disposition': 'abstained_no_evidence'}])
    replay['finalRecords'][1]['finalDisposition'] = 'unresolved_endpoint'
    effective = {**deepcopy(replay), 'finalRecords': rows, 'responseBytesHex': b'derived'.hex(),
                 'responseSha256': digest(b'derived')}
    effective_sha = reporting.replay_hash(effective)
    projection = dict(owner=body['owner'], artifactFamily='github', requestSha256=sha, replaySha256=effective_sha,
                      responseSha256=effective['responseSha256'], policySha256='policy', nodes=[], edges=[])
    decisions = []
    for row in rows:
        cid = row['candidateID']
        disposition = 'accepted' if cid in ('a', 'b') else 'held' if cid == 'c' else 'suppressed_duplicate'
        basis = ('policy_ordinary_inclusion' if cid == 'a' else 'policy_conditional_inclusion') if disposition == 'accepted' else None
        decisions.append(dict(candidateID=cid, disposition=disposition, originalDisposition=row['finalDisposition'],
                              acceptanceBasis=basis, blockingReasons=['version_identity_unavailable'] if cid == 'c' else []))
        if disposition == 'accepted':
            projection['nodes' if row['kind'] == 'node' else 'edges'].append(dict(candidateID=cid,
                originalCandidate=row['originalCandidate'], acceptanceBasis=basis, **row['validationRecord'],
                replayRecordReference=dict(candidateID=cid, replaySha256=effective_sha)))
    report = dict(status='projection_completed', blockingReasons=[], originalReplay=replay,
                  originalReplaySha256=reporting.replay_hash(replay), decisions=decisions, projection=projection,
                  projectionSha256=digest(canonical(projection)), conformance=dict(originalResponseBytesHex=b'original'.hex(),
                  originalResponseSha256=digest(b'original'), semanticRequestSha256=sha,
                  derivedResponseBytesHex=b'derived'.hex(), derivedResponseSha256=digest(b'derived'),
                  derivedReplay=effective, derivedReplaySha256=effective_sha, changes=[]))
    outcome = dict(processable=True, productionResult=report, productionResultSha256=digest(canonical(report)),
                   attempt=dict(attemptNumber=1, requestInputSha256=sha), provenance=dict(identity=fingerprint(prepared),
                   responseSha256=digest(canonical(receipt)), policySha256='policy'))
    owner = dict(family='github', ownerID='owner', inputComplete=False, readerSourceUnitIDs=['u1', 'u2', 'excluded'],
                 excludedSourceUnitIDs=['excluded'], diagnostics=[dict(reason='license_legal_text_step11_4_2',
                 status='not_attempted_authorized_exclusion', sourceUnitIDs=['excluded'])], groups=[dict(group, requestID=rid)])
    empty = dict(family='github', ownerID='empty', inputComplete=True, readerSourceUnitIDs=[],
                 excludedSourceUnitIDs=[], diagnostics=[], groups=[])
    queue = dict(requests=[entry], coverage=[owner, empty])
    return prepared, entry, receipt, outcome, queue


class FixtureLog:
    """Minimal indexed journal view; no accepted processing code is invoked."""

    def __init__(self, prepared: dict, entry: dict, receipt: dict, outcome: dict) -> None:
        """Expose immutable payload references for one completed delivery."""
        rid = entry['identity']['requestID']
        self.entries = {rid: entry}
        self.state = {rid: 'completion'}
        self.offsets = {rid: {'prepared': 0}}
        self.outcomes = {(rid, 1): 'outcome'}
        self.receipts = {(rid, 1): 'receipt'}
        self.payloads = {'receipt': receipt, 'outcome': {'native': outcome}}
        self.bundle = prepared

    def payload_at(self, offset: str) -> dict:
        """Return a persisted fixture payload."""
        return self.payloads[offset]

    def prepared(self, rid: str) -> dict:
        """Return the fixture bundle without rebuilding it."""
        return self.bundle


class ReportingTests(unittest.TestCase):
    """Accounting and integrity checks for the new reporter only."""

    def test_persisted_hashes_and_immutability(self) -> None:
        """No replay, reconstruction or acceptance function may be reached."""
        p, e, receipt, outcome, _ = fixture()
        before = deepcopy((p, e, receipt, outcome))
        with patch('src.extraction.llm.source_family_batch.prepare', side_effect=AssertionError('rebuild')), \
             patch('src.extraction.llm.source_family_batch.process', side_effect=AssertionError('processing')), \
             patch('src.extraction.llm.construction_acceptance.project_replay', side_effect=AssertionError('projection')):
            reporting.checked_prepared(p, e)
            reporting.checked_outcome(p, receipt, outcome, 1)
        self.assertEqual((p, e, receipt, outcome), before)

    def test_category_separation_and_coverage(self) -> None:
        """Accepted edges, held nodes, duplicates and abstentions use distinct totals."""
        p, e, receipt, outcome, queue = fixture()
        log = FixtureLog(p, e, receipt, outcome)
        before = deepcopy(log.__dict__)
        records = {}
        report = reporting.inventory(log, queue, lambda name, row: records.setdefault(name, []).append(row))
        family = report['families']['github']
        self.assertEqual((family['requests'], family['owners'], family['ownersWithRequests']), (1, 2, 1))
        self.assertEqual((family['acceptedNodes'], family['acceptedEdges'], family['candidateOccurrences']), (1, 1, 4))
        self.assertEqual(family['constructionDecisions'], {'accepted': 2, 'held': 1, 'suppressed_duplicate': 1})
        self.assertEqual(family['originalReplayDispositions']['unresolved_endpoint'], 1)
        self.assertEqual(family['constructionReplayDispositions']['unresolved_condition'], 2)
        self.assertEqual((family['abstentions'], family['sourceIncompleteOwners']), (1, 1))
        self.assertEqual((family['readerAdmittedUnits'], family['productionAdmittedUnits'], family['selectedUnits'],
                          family['citedUnits'], family['excludedUnits'], family['zeroYieldSelectedUnits']), (3, 2, 2, 1, 1, 1))
        self.assertEqual(family['specialRecords']['A-C10:held'], 1)
        self.assertEqual(sum(x['acceptedSourceLocalAssertions'] for x in records['ontology-types']), 2)
        self.assertEqual(log.__dict__, before)

    def test_incomplete_request_is_not_zero_yield(self) -> None:
        """Missing outcomes remain incomplete, while no-request owners are separate."""
        p, e, receipt, outcome, queue = fixture()
        log = FixtureLog(p, e, receipt, outcome)
        rid = e['identity']['requestID']
        log.outcomes = {}
        log.state[rid] = 'received'
        report = reporting.inventory(log, queue, lambda *args: None)
        family = report['families']['github']
        self.assertEqual(family['processingIncompleteUnits'], 2)
        self.assertEqual(family['zeroYieldSelectedUnits'], 0)
        self.assertEqual(family['zeroYieldProcessedOwners'], 0)

    def test_repeated_context_not_unique_entities(self) -> None:
        """Repeated requests increase occurrences without doubling source-unit coverage."""
        p, e, receipt, outcome, queue = fixture()
        log = FixtureLog(p, e, receipt, outcome)
        second = deepcopy(e)
        second['identity']['requestID'] = 'second'
        log.entries['second'] = second
        log.state['second'] = 'completion'
        log.offsets['second'] = {'prepared': 0}
        log.outcomes['second', 1] = 'outcome'
        log.receipts['second', 1] = 'receipt'
        queue['coverage'][0]['groups'].append(dict(e['coverage'], requestID='second'))
        report = reporting.inventory(log, queue, lambda *args: None)
        family = report['families']['github']
        self.assertEqual((family['requests'], family['selectedUnitOccurrences'], family['selectedUnits']), (2, 4, 2))
        self.assertEqual(family['acceptedNodes'], 2)

    def test_fail_closed_hashes_and_associations(self) -> None:
        """Rehashing a tampered report cannot hide association/accounting mismatches."""
        for target in ('projection_hash', 'association', 'accepted', 'replay', 'request', 'basis', 'source'):
            with self.subTest(target=target):
                p, e, receipt, outcome, _ = fixture()
                report = outcome['productionResult']
                if target == 'projection_hash':
                    report['projectionSha256'] = 'bad'
                elif target == 'association':
                    report['projection']['owner'] = {'endpointID': 'other'}
                elif target == 'accepted':
                    report['projection']['nodes'] = []
                elif target == 'replay':
                    report['originalReplay']['requestAssociation'] = 'unknown'
                    report['originalReplaySha256'] = reporting.replay_hash(report['originalReplay'])
                elif target == 'request':
                    p['semanticRequest']['requestSha256'] = 'bad'
                elif target == 'basis':
                    report['decisions'][0]['acceptanceBasis'] = 'invented'
                else:
                    report['projection']['nodes'][0]['boundEvidence'] = [{'sourceUnitID': 'unselected'}]
                if target != 'projection_hash':
                    report['projectionSha256'] = digest(canonical(report['projection']))
                outcome['productionResultSha256'] = digest(canonical(report))
                with self.assertRaises(ValueError):
                    reporting.checked_outcome(p, receipt, outcome, 1)

    def test_sealed_coverage_inconsistencies(self) -> None:
        """Reject omitted owners, duplicate primary accounting and mismatched selections."""
        _, _, _, _, queue = fixture()
        manifest = dict(requests=queue['requests'], parentSha256=digest(canonical(queue)))
        reporting.checked_coverage(queue, manifest)
        for problem in ('primary', 'missing', 'exclusion', 'duplicate'):
            bad = deepcopy(queue)
            if problem == 'primary':
                bad['coverage'][0]['groups'][0]['primarySourceUnitIDs'] = ['u1']
            elif problem == 'missing':
                bad['coverage'] = bad['coverage'][1:]
            elif problem == 'exclusion':
                bad['coverage'][0]['excludedSourceUnitIDs'].append('u1')
            else:
                bad['coverage'].append(bad['coverage'][0])
            mf = dict(requests=bad['requests'], parentSha256=digest(canonical(bad)))
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                reporting.checked_coverage(bad, mf)

    def test_output_publish_and_failure(self) -> None:
        """Only a successfully verified report becomes a new output directory."""
        import socket
        import sys
        from types import SimpleNamespace
        p, e, receipt, outcome, queue = fixture()
        log = FixtureLog(p, e, receipt, outcome)

        def synthetic_verify(root, emit):
            """Exercise publishing under the CLI network block using synthetic input."""
            with self.assertRaisesRegex(RuntimeError, 'OFFLINE_ONLY'):
                socket.socket()
            report = reporting.inventory(log, queue, emit)
            report['discrepancies'] = []
            return report

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'reports' / 'v1'
            root = Path(tmp) / 'inputs' / 'production'
            argv = ['report', '--root', str(root), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(reporting.subprocess, 'run',
                    return_value=SimpleNamespace(returncode=0)), patch.object(reporting, 'verify', synthetic_verify):
                reporting.main()
                self.assertEqual({f.name for f in output.iterdir()}, {'summary.md', 'verification.json',
                    'requests.jsonl', 'family-owner.jsonl', 'ontology-types.jsonl', 'candidate-decisions.jsonl',
                    'source-unit-coverage.jsonl', 'exceptions.jsonl'})
                self.assertEqual(json.loads((output / 'verification.json').read_text())['acceptedNodes'], 1)
                with self.assertRaisesRegex(ValueError, 'OUTPUT_EXISTS'):
                    reporting.main()
            failed = output.parent / 'failed'
            with patch.object(sys, 'argv', ['report', '--root', str(root), '--output', str(failed)]), \
                 patch.object(reporting.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
                 patch.object(reporting, 'verify', side_effect=ValueError('integrity failure')):
                with self.assertRaisesRegex(ValueError, 'integrity failure'):
                    reporting.main()
            self.assertFalse(failed.exists())
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_output_boundaries(self) -> None:
        """Refuse a production descendant or any output not covered by gitignore."""
        import sys
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'production'
            for output, ignored, error in [(root / 'report', 0, 'OUTSIDE_PRODUCTION'),
                    (Path(tmp).parent / 'unignored-test-output', 1, 'GIT_IGNORED')]:
                with patch.object(sys, 'argv', ['report', '--root', str(root), '--output', str(output)]), \
                     patch.object(reporting.subprocess, 'run', return_value=SimpleNamespace(returncode=ignored)), \
                     patch.object(reporting, 'verify', side_effect=AssertionError('must not verify')):
                    with self.assertRaisesRegex(ValueError, error):
                        reporting.main()

    def test_native_read_only_journal_and_failures(self) -> None:
        """Use native framing on a tiny synthetic header; reject damage without writes."""
        from src.extraction.llm import source_family_batch as adapter
        from src.extraction.llm.publications import full_corpus_gpt61_production as baseline
        paths = [baseline.V2 / 'stream.py', baseline.V2 / 'journal.py',
                 baseline.V2.parent / 'v0.1/preflight.py', baseline.V2.parent / 'v0.1/input-pins.json']
        pins = {str(p.relative_to(baseline.ROOT)): reporting.file_hash(p) for p in paths}
        with patch.object(adapter, 'infrastructure', side_effect=AssertionError('full-corpus audit')), \
             patch.object(baseline, 'dependencies', side_effect=AssertionError('full-corpus audit')):
            _, native = reporting.infrastructure(pins)
        cls = adapter.batch_journal(native, reporting.checked_prepared, fingerprint, reporting.checked_outcome)
        wire = canonical(dict(generatorPins=pins, requests=[], queuedTokenLimit=100))
        rec = dict(seq=1, previous='0' * 64, event='header', requestID=None, attemptID=None,
                   payload=dict(manifestSha256=digest(wire), generatorPins=pins))
        head = digest(canonical(rec))
        framed = canonical(dict(record=rec, sha256=head)) + b'\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'execution.jsonl'
            anchor = root / 'head.json'
            path.write_bytes(framed)
            anchor.write_bytes(canonical(dict(seq=1, headSha256=head)) + b'\n')
            before = {f.name: f.read_bytes() for f in root.iterdir()}
            with patch.object(cls, '__enter__', side_effect=AssertionError('writable enter')), \
                 reporting.read_only_log(root, native, cls, wire) as log:
                self.assertEqual(log.seq, 1)
            self.assertEqual(before, {f.name: f.read_bytes() for f in root.iterdir()})
            for damage in ('truncated', 'hash', 'anchor', 'pending'):
                path.write_bytes(framed)
                anchor.write_bytes(canonical(dict(seq=1, headSha256=head)) + b'\n')
                if damage == 'truncated':
                    path.write_bytes(framed[:-1])
                elif damage == 'hash':
                    path.write_bytes(framed.replace(b'header', b'broken'))
                elif damage == 'anchor':
                    anchor.write_bytes(canonical(dict(seq=2, headSha256=head)) + b'\n')
                else:
                    (root / 'pending-event.json').write_bytes(b'pending')
                before = {f.name: f.read_bytes() for f in root.iterdir()}
                with self.subTest(damage=damage), self.assertRaises(ValueError):
                    with reporting.read_only_log(root, native, cls, wire):
                        self.fail('corrupt journal accepted')
                self.assertEqual(before, {f.name: f.read_bytes() for f in root.iterdir()})


if __name__ == '__main__':
    unittest.main()
