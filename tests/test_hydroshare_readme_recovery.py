"""Focused synthetic recovery tests. Every test blocks sockets; no live requests."""
from __future__ import annotations

from copy import deepcopy
import io
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import hydroshare_readme_recovery as recovery
from src.extraction.llm.datasets import request_contract
from src.extraction.llm.datasets.source_units import build_abstract_source_unit, read_readme_source_units
from src.extraction.llm.pilot_preflight import canonical, digest


class RecoveryTests(unittest.TestCase):
    """Exercise only the new overlay, preparation boundaries and journal isolation."""

    def setUp(self) -> None:
        """Keep all test IO local and every source synthetic."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.owner = 'synthetic-owner'
        self.provenance = dict(snapshotID='sha256:synthetic', sourceVersion='v1')

    def readme(self, name: str, text: str, raw: bytes | None = None) -> dict:
        """Create a snapshot row and optionally matching physical bytes."""
        if raw is not None:
            path = self.repo / 'data/raw/datasets' / self.owner / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        return dict(source_file=name, readme_text_raw=text, readme_char_count=len(text))

    def fixture(self, readmes: list | None = None) -> dict:
        """Seal one abstract-only predecessor with unverified README diagnostics."""
        if readmes is None:
            readmes = [self.readme('README.md', 'A café tool.\n', 'A café tool.\r\n'.encode()),
                       self.readme('Readme.txt', 'A second document.\n', b'A second document.\n')]
        source = dict(resource_id=self.owner, abstract='The resource contains temperature observations.',
                      documentation={'readme_files': readmes})
        abstract = build_abstract_source_unit(source, accepted_owner_id=self.owner, provenance=self.provenance)
        inputs = dict(accepted_owner_id=self.owner, trusted_provenance=self.provenance,
            abstract_results=[abstract], readme_results=[read_readme_source_units(dict(resource_id=self.owner,
            source_path=r['source_file'], text=r['readme_text_raw']), accepted_owner_id=self.owner,
            provenance=self.provenance) for r in readmes], input_complete=False,
            selected_unit_ids=[abstract['unit'].source_unit_id], request_version='hydroshare-request/1.2.0',
            accepted_endpoints=[], accepted_assertions=[], authorized_stubs=[])
        original = recovery.adapter.prepare(request_contract.build_request(**inputs), inputs)
        entry = dict(identity=recovery.adapter.fingerprint(original), bundleSha256=digest(canonical(original)))
        return dict(ownerID=self.owner, source=source, original=original, entry=entry,
            coverage=dict(sourceRecordSha256=digest(canonical(source)), endpointRecordSha256='synthetic-endpoint'),
            bindings=[recovery.make_binding(r, source, self.provenance, self.repo) for r in readmes])

    def test_notebook_decoding_and_distinct_hashes(self) -> None:
        """Universal newlines/replacement match the notebook, without byte normalization claims."""
        row = self.readme('README.md', 'café\nreplacement: �\n', b'caf\xc3\xa9\r\nreplacement: \xff\r')
        comparison = recovery.physical_comparison(row, self.owner, self.repo)
        self.assertEqual(comparison['comparison'], 'exact_decoded_text_match')
        self.assertEqual(comparison['decodedTextSha256'], digest(row['readme_text_raw'].encode()))
        self.assertNotEqual(comparison['physicalBytesSha256'], comparison['decodedTextSha256'])
        self.assertEqual((comparison['crlfCount'], comparison['loneCRCount'], comparison['replacementCharacterCount']), (1, 1, 1))
        self.assertFalse(comparison['historicalAcquisitionVerified'])

    def test_absence_is_not_historical_verification(self) -> None:
        """A snapshot-only prospective binding preserves the absence explicitly."""
        row = self.readme('README.md', 'Snapshot only.')
        binding = recovery.make_binding(row, {'resource_id': self.owner}, self.provenance, self.repo)
        self.assertEqual(binding['physicalComparison']['comparison'], 'physical_file_absent')
        self.assertIsNone(binding['physicalComparison']['physicalBytesSha256'])
        reader = recovery.reader_from_binding(row, self.owner, self.provenance, binding)
        self.assertEqual(reader['authority']['sourceVerification'], 'caller_attested')
        self.assertEqual(reader['authority']['acquisitionIntegrityStatus'], 'not_independently_verified')

    def test_physical_mismatch_character_count_and_path_fail_closed(self) -> None:
        """Never repair a mismatched source, changed character count or unsafe path."""
        row = self.readme('README.md', 'Expected.', b'Unexpected.')
        with self.assertRaisesRegex(ValueError, 'PHYSICAL_SNAPSHOT_MISMATCH'):
            recovery.physical_comparison(row, self.owner, self.repo)
        row['readme_char_count'] += 1
        with self.assertRaisesRegex(ValueError, 'CHARACTER_COUNT'):
            recovery.physical_comparison(row, self.owner, self.repo)
        row['source_file'] = '../README.md'
        with self.assertRaisesRegex(ValueError, 'UNSAFE_README_PATH'):
            recovery.physical_comparison(row, self.owner, self.repo)

    def test_two_readmes_full_context_and_original_unchanged(self) -> None:
        """Keep both exact README authorities, original abstract IDs and frozen predecessor."""
        item = self.fixture()
        before = deepcopy(item)
        original_file = self.repo / 'original-bundle.json'
        original_file.write_bytes(canonical(item['original']))
        before_bytes = original_file.read_bytes()
        prepared, entry = recovery.successor(item, 'overlay')
        self.assertEqual(item, before)
        self.assertEqual(original_file.read_bytes(), before_bytes)
        units = prepared['semanticRequest']['request']['sourceUnits']
        self.assertEqual(len(units), 3)
        self.assertEqual([u['source_path'] for u in units[1:]], ['README.md', 'Readme.txt'])
        self.assertEqual([u['text'] for u in units[1:]], [r['readme_text_raw'] for r in item['source']['documentation']['readme_files']])
        self.assertEqual(entry['coverage']['primarySourceUnitIDs'], [u['sourceUnitID'] for u in units])
        self.assertEqual(entry['coverage']['selectedSourceUnitIDs'], entry['coverage']['primarySourceUnitIDs'])
        self.assertFalse(entry['coverage']['exceptionalSplit'])
        self.assertNotEqual(entry['identity']['requestID'], item['entry']['identity']['requestID'])
        self.assertEqual(entry['recoveryProvenance']['originalIdentity'], item['entry']['identity'])
        self.assertEqual(recovery.successor(item, 'overlay'), (prepared, entry))
        recovery.adapter.verify_prepared(prepared, entry)
        for readme, binding, unit in zip(item['source']['documentation']['readme_files'], item['bindings'], units[1:]):
            legacy = read_readme_source_units(dict(resource_id=self.owner, source_path=readme['source_file'],
                text=readme['readme_text_raw']), accepted_owner_id=self.owner,
                provenance={**self.provenance, 'sourceVerified': True})
            self.assertEqual(unit['sourceUnitID'], legacy['sourceUnits'][0]['sourceUnitID'])
            self.assertEqual(unit['sourceUnitID'], binding['sourceUnitID'])

    def test_overlay_identity_and_digest_drift(self) -> None:
        """Every attestation pin is checked, including scope and acquisition semantics."""
        row = self.readme('README.md', 'A tool.')
        binding = recovery.make_binding(row, {'resource_id': self.owner}, self.provenance, self.repo)
        for field in ('ownerID', 'source_path', 'snapshotID', 'sourceVersion', 'authorityTextSha256',
                      'sourceUnitID', 'characters', 'attestationScope', 'sourceVerification', 'acquisitionIntegrityStatus'):
            bad = deepcopy(binding)
            bad[field] = 'changed'
            with self.subTest(field=field), self.assertRaises(ValueError):
                recovery.reader_from_binding(row, self.owner, self.provenance, bad)

    def test_size_hold_never_truncates(self) -> None:
        """Reject the full oversized context without dropping either README."""
        item = self.fixture([self.readme('README.md', 'x' * (recovery.packaging.SIZING['maxSelectedTextBytes'] + 1))])
        before = deepcopy(item)
        with self.assertRaisesRegex(ValueError, 'RECOVERY_SIZE_OR_REQUEST_HOLD'):
            recovery.successor(item, 'overlay')
        self.assertEqual(item, before)

    def test_original_roots_rejected(self) -> None:
        """No new journal or preparation may target historical workstream directories."""
        for relative in (recovery.ORIGINAL, recovery.ORIGINAL / 'production',
                         Path('var/study2_step13/publications-gpt61-batch/v1')):
            with self.subTest(path=relative), self.assertRaisesRegex(ValueError, 'ISOLATED'):
                recovery.assert_isolated(self.repo / relative, self.repo)

    def test_simulated_submit_recovery_collect_and_no_redispatch(self) -> None:
        """A lost simulated acknowledgement resumes once and collects a native outcome."""
        import json
        from test_full_corpus_gpt61_batch import FakeAPI
        item = self.fixture()
        prepared, entry = recovery.successor(item, 'overlay')
        baseline = recovery.adapter.batch.baseline
        paths = [baseline.V2 / 'stream.py', baseline.V2 / 'journal.py',
                 baseline.V2.parent / 'v0.1/preflight.py', baseline.V2.parent / 'v0.1/input-pins.json']
        pins = {str(p.relative_to(baseline.ROOT)): recovery.verification.file_hash(p) for p in paths}
        queue = dict(generatorPins=pins, implementationPins={}, requests=[entry], bindingOverlaySha256='overlay',
                     pricing=recovery.adapter.batch.PRICING, summary={})
        folder = self.repo / 'synthetic-run'
        (folder / 'production').mkdir(parents=True)
        (folder / 'production/execution.jsonl').touch()
        wire = canonical(queue) + b'\n'
        (folder / 'queue-manifest.json').write_bytes(wire)
        queue_sha = digest(wire)
        remote = FakeAPI()
        remote.lose_create = True

        class API:
            """Inject a local fake account into the new terminal wrapper only."""

            def __init__(self, key):
                """No key use or network operations in this test double."""
                pass

            def __getattr__(self, name):
                """Delegate file/listing operations to the shared fake account."""
                return getattr(remote, name)

            def count(self, body):
                """Return synthetic token counts without any API request."""
                return remote.count(body)

            def create(self, file_id, metadata):
                """Retain fake submission state across restarted controller instances."""
                return remote.create(file_id, metadata)

            def retrieve(self, bid):
                """Supply an empty but processable HydroShare response fixture."""
                result = remote.retrieve(bid)
                fid = result.get('output_file_id')
                if fid:
                    rows = [json.loads(line) for line in remote.contents[fid].splitlines()]
                    for row in rows:
                        payload = dict(schemaVersion=request_contract.RESPONSE_VERSION,
                                       candidateNodes=[], candidateEdges=[], abstentions=[])
                        row['response']['body']['output'] = [dict(type='message', content=[dict(
                            type='output_text', text=canonical(payload).decode())])]
                    remote.contents[fid] = b''.join(canonical(row) + b'\n' for row in rows)
                return result

        with patch.object(recovery, 'load_queue', return_value=(queue, {})), \
             patch.object(recovery, 'load_bundle', return_value=prepared), \
             patch.object(recovery.adapter.batch.batch_transport, 'BatchAPI', API), \
             patch.object(baseline.provider, 'load_openai_api_key', return_value='synthetic-not-a-key'), \
             patch('sys.stdout', new_callable=io.StringIO):
            with self.assertRaisesRegex(OSError, 'lost create'):
                recovery.operate(folder, queue_sha, 'submit', 1000000)
            recovery.operate(folder, queue_sha, 'submit', None)
            result = recovery.operate(folder, queue_sha, 'collect', None)
            self.assertEqual(result['completed'], 1)
            recovery.operate(folder, queue_sha, 'submit', None)
            recovery.operate(folder, queue_sha, 'collect', None)
            self.assertEqual((remote.counts, remote.uploads, remote.creates), (1, 1, 1))
            self.assertEqual(recovery.status(folder, queue_sha)['completed'], 1)

    def test_isolated_native_journal_and_no_dispatch_without_capacity(self) -> None:
        """Initialize only a synthetic recovery journal; missing capacity cannot reach credentials."""
        item = self.fixture()
        prepared, entry = recovery.successor(item, 'overlay')
        baseline = recovery.adapter.batch.baseline
        paths = [baseline.V2 / 'stream.py', baseline.V2 / 'journal.py',
                 baseline.V2.parent / 'v0.1/preflight.py', baseline.V2.parent / 'v0.1/input-pins.json']
        pins = {str(p.relative_to(baseline.ROOT)): recovery.verification.file_hash(p) for p in paths}
        queue = dict(generatorPins=pins, implementationPins={}, requests=[entry], bindingOverlaySha256='overlay',
                     pricing=recovery.adapter.batch.PRICING, summary={})
        native, cls, _ = recovery.journal_class(queue)
        folder = self.repo / 'new-recovery'
        production = folder / 'production'
        production.mkdir(parents=True)
        historical = self.repo / 'original-execution.jsonl'
        historical.write_bytes(b'historical journal unchanged\n')
        wire = recovery.adapter.batch.canonical_json(dict(generatorPins=pins, requests=[entry], queuedTokenLimit=1000000)) + b'\n'
        with cls(production / 'execution.jsonl', wire, digest(wire)) as log:
            log.append('prepared', entry['identity']['requestID'], native.bundle(prepared))
        before = {p.name: p.read_bytes() for p in production.iterdir()}
        with recovery.verification.read_only_log(production, native, cls, wire) as log:
            self.assertEqual(len(log.entries), 1)
            self.assertEqual(log.prepared(entry['identity']['requestID']), prepared)
        self.assertEqual(before, {p.name: p.read_bytes() for p in production.iterdir()})
        self.assertEqual(historical.read_bytes(), b'historical journal unchanged\n')
        for capacity in (None, 0, -1):
            with patch.object(recovery, 'load_queue', return_value=(queue, {})), \
                 patch.object(recovery.adapter.batch.baseline.provider, 'load_openai_api_key',
                              side_effect=AssertionError('credentials reached')), \
                 self.subTest(capacity=capacity), self.assertRaises(ValueError):
                recovery.operate(folder, 'queue-pin', 'submit', capacity)
        self.assertFalse((production / 'run-manifest.json').exists())
        self.assertEqual(historical.read_bytes(), b'historical journal unchanged\n')


class OperationalCorrectionTests(unittest.TestCase):
    """Only the relocation, metadata reseal and native executor delegation correction."""

    def setUp(self) -> None:
        """Block sockets and allocate synthetic, isolated successor artifacts."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def legacy(self) -> tuple[Path, dict, dict]:
        """Construct small accepted-shaped artifacts without readers or original sources."""
        source = self.root / 'v1'
        (source / 'queue').mkdir(parents=True)
        (source / 'production').mkdir()
        (source / 'production/execution.jsonl').touch()
        overlay = dict(bindings=[])
        overlay_wire = canonical(overlay) + b'\n'
        (source / 'binding-overlay.json').write_bytes(overlay_wire)
        entries = []
        for index in range(20):
            name = f'{index}.json'
            wire = canonical({'synthetic': index}) + b'\n'
            (source / 'queue' / name).write_bytes(wire)
            entries.append(dict(bundleFile=name, bundleSha256=digest(wire)))
        current = {'src/evaluation/hydroshare_readme_recovery.py': 'new', 'unchanged.py': 'same'}
        old = {'src/extraction/llm/hydroshare_readme_recovery.py': 'old', 'unchanged.py': 'same'}
        manifest = dict(implementationPins=old, bindingOverlaySha256=digest(overlay_wire), requests=entries,
            summary=dict(requests=20, owners=20, addedReadmes=21, selectedUnits=41, sizeHolds=0,
                         costUSD={'low': .4, 'pooled': 1.1, 'high': 2.1, 'outputCeiling': 4.2},
                         twoAttemptPlanningReserveUSD=8.4))
        wire = canonical(manifest) + b'\n'
        (source / 'queue-manifest.json').write_bytes(wire)
        for target, replacement in [('assert_isolated', None), ('implementation_pins', current)]:
            mock = patch.object(recovery, target, return_value=replacement)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(recovery, 'ACCEPTED_PREFLIGHT_SHA256', digest(wire))
        mock.start()
        self.addCleanup(mock.stop)
        for name in ('physical_comparison', 'discover', 'successor', 'check_pins', 'load_queue'):
            mock = patch.object(recovery, name, side_effect=AssertionError('NO_REPEAT_AUDIT_OR_RECONSTRUCTION'))
            mock.start()
            self.addCleanup(mock.stop)
        return source, manifest, current

    def test_relocation_preserves_original_runner_pins(self) -> None:
        """The original sealed queue remains supported through its existing operational bridge."""
        from src.extraction.llm import full_corpus_source_family_batch as original
        pins = original.implementation_pins()
        self.assertFalse(any('hydroshare_readme_recovery' in name for name in pins))
        parent = recovery.read_json(recovery.ROOT / recovery.ORIGINAL / 'queue-manifest.json')
        original.operational_compatibility(parent['implementationPins'], pins)

    def test_reseal_preserves_accepted_bytes_and_costs_without_source_audit(self) -> None:
        """Refresh only operational metadata; preserve the predecessor and all request bytes."""
        source, manifest, pins = self.legacy()
        before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        destination = self.root / 'v2'
        result = recovery.refresh_preflight(source, destination)
        for name, wire in before.items():
            self.assertEqual((source / name).read_bytes(), wire)
            if name.parts[0] == 'queue' or name.name == 'binding-overlay.json':
                self.assertEqual((destination / name).read_bytes(), wire)
        updated = recovery.read_json(destination / 'queue-manifest.json')
        self.assertEqual(updated['requests'], manifest['requests'])
        self.assertEqual(updated['summary']['costUSD'], manifest['summary']['costUSD'])
        self.assertEqual(updated['implementationPins'], pins)
        self.assertNotIn('twoAttemptPlanningReserveUSD', updated['summary'])
        self.assertEqual(result['queueSha256'], recovery.verification.file_hash(destination / 'queue-manifest.json'))
        self.assertEqual((destination / 'production/execution.jsonl').read_bytes(), b'')
        self.assertFalse((destination / 'production/run-manifest.json').exists())
        with self.assertRaisesRegex(ValueError, 'NEW_RECOVERY_ROOT_REQUIRED'):
            recovery.refresh_preflight(source, destination)

    def test_reseal_rejects_started_predecessor(self) -> None:
        """A started journal cannot silently spawn a duplicate execution root."""
        source, _, _ = self.legacy()
        (source / 'production/execution.jsonl').write_bytes(b'started\n')
        with self.assertRaisesRegex(ValueError, 'PREDECESSOR_ALREADY_STARTED'):
            recovery.refresh_preflight(source, self.root / 'v2')
        self.assertFalse((self.root / 'v2').exists())

    def test_reseal_fails_closed_on_bundle_and_dependency_drift(self) -> None:
        """Never bless different requests or scientific dependencies during relocation."""
        source, _, pins = self.legacy()
        with patch.object(recovery, 'implementation_pins', return_value={**pins, 'unchanged.py': 'changed'}):
            with self.assertRaisesRegex(ValueError, 'RECOVERY_DEPENDENCY_DRIFT'):
                recovery.refresh_preflight(source, self.root / 'v2')
        (source / 'queue/0.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SUCCESSOR_BUNDLE_DRIFT'):
            recovery.refresh_preflight(source, self.root / 'v2')
        self.assertFalse((self.root / 'v2').exists())

    def test_submit_collect_restart_delegate_without_budget_gate(self) -> None:
        """All execution modes use native APIs/controllers, with capacity as the only numeric input."""
        from unittest.mock import MagicMock
        production = self.root / 'production'
        production.mkdir()
        (production / 'execution.jsonl').touch()
        queue = dict(generatorPins={}, implementationPins={}, requests=[], pricing={}, bindingOverlaySha256='overlay')
        log = MagicMock()
        log.poisoned = False
        cls = MagicMock()
        cls.return_value.__enter__.return_value = log
        api = object()
        with patch.object(recovery, 'load_queue', return_value=(queue, {})), \
             patch.object(recovery, 'journal_class', return_value=('native', cls, 'paired')), \
             patch.object(recovery.adapter.batch.batch_transport, 'BatchAPI', return_value=api) as api_class, \
             patch.object(recovery.adapter.batch.baseline.provider, 'load_openai_api_key', return_value='fake'), \
             patch.object(recovery.adapter.batch, 'submit_all', return_value='submitted') as submit, \
             patch.object(recovery.adapter.batch, 'collect_once', return_value=[]) as collect, \
             patch.object(recovery.adapter.batch, 'summary', return_value={}), \
             patch.object(recovery.adapter.batch, 'save_status') as save:
            recovery.operate(self.root, 'queue-pin', 'submit', 1000000)
            first = (production / 'run-manifest.json').read_bytes()
            recovery.operate(self.root, 'queue-pin', 'collect', None)
            recovery.operate(self.root, 'queue-pin', 'submit', None)
            self.assertEqual((production / 'run-manifest.json').read_bytes(), first)
            self.assertNotIn('budget', first.decode().lower())
            self.assertEqual((submit.call_count, collect.call_count, save.call_count, api_class.call_count), (2, 1, 3, 3))
            self.assertIs(submit.call_args.args[1], api)
            self.assertIs(collect.call_args.args[1], api)


if __name__ == '__main__':
    unittest.main()
