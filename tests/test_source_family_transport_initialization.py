"""Offline regression for independent non-Publications native transport loading."""
from copy import deepcopy
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import source_family_batch as adapter
from src.evaluation import source_local_semantic_pilot as pilot
from src.evaluation import source_local_specialized_pilot as specialized


@unittest.skipUnless(all((adapter.batch.baseline.ROOT / p).exists() for p in adapter.TRANSPORT_PINS),
                     'Pinned local transport implementation files are unavailable')
class TransportInitializationTests(unittest.TestCase):
    """Use the unchanged native loader, journal and controller with synthetic queues."""

    def setUp(self):
        """Forbid network operations throughout each regression."""
        for method in ('connect', 'connect_ex'):
            block = patch.object(socket.socket, method, side_effect=AssertionError('NETWORK_FORBIDDEN'))
            block.start(); self.addCleanup(block.stop)

    def test_parent_drift_still_blocks_publications_but_not_family_preflight(self):
        """Reproduce the actual v0.1.6 OWL guard, then verify the independent path."""
        historical = adapter.batch.baseline
        if not historical.PARENT.exists():
            self.skipTest('Historical Publications parent is unavailable')
        before = historical.PARENT.read_bytes()
        with self.assertRaisesRegex(ValueError, 'AUTHORITY_DRIFT src/ontology/ciroh_ontology.owl'):
            historical.dependencies()
        sentinel = object(); paths = list(sys.path)
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(historical, 'dependencies', side_effect=AssertionError('HISTORICAL_PARENT_CALLED')) as guard, \
             patch.object(historical, 'PARENT', Path(directory) / 'absent-publications-parent.json'), \
             patch.dict(sys.modules, {'stream': sentinel}):
            paired, native, pins = adapter.infrastructure()
            self.assertIs(sys.modules['stream'], sentinel)
            self.assertEqual(sys.path, paths)
            self.assertTrue(callable(paired.usage_cost)); self.assertTrue(callable(native.Journal))
            parent = {'requests': [], 'implementationPins': {}}
            operate = specialized.bind(pilot.operate, load_queue=lambda repo, output, sha: (parent, {'synthetic': {}}))
            result = operate('preflight', 'batch', 'synthetic-queue-hash', repo=Path(directory), output=Path('queue'))
            self.assertTrue(result['verified']); self.assertFalse(result['initialized'])
            self.assertEqual(result['requests'], 1); self.assertEqual(result['providerCalls'], 0)
            self.assertFalse((Path(directory) / 'queue').exists())
            guard.assert_not_called()
        self.assertEqual(historical.PARENT.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'AUTHORITY_DRIFT src/ontology/ciroh_ontology.owl'):
            historical.dependencies()

    def test_transport_pin_drift_and_missing_files_fail_before_import(self):
        """Every reusable component remains pinned; missing dependencies never fall back."""
        for path in adapter.TRANSPORT_PINS:
            changed = {**adapter.TRANSPORT_PINS, path: '0' * 64}
            with self.subTest(path=path), patch.object(adapter, 'TRANSPORT_PINS', changed), \
                 patch.object(adapter.batch.baseline, 'load_module') as loader:
                with self.assertRaisesRegex(ValueError, 'TRANSPORT_DEPENDENCY_DRIFT'):
                    adapter.infrastructure()
                loader.assert_not_called()
        with tempfile.TemporaryDirectory() as directory, patch.object(adapter.batch.baseline, 'ROOT', Path(directory)):
            with self.assertRaises(FileNotFoundError): adapter.infrastructure()

    def test_native_journal_roundtrip_and_integrity_guards(self):
        """Keep exact prepared bytes, native hash chains and generator/manifest guards."""
        _, native, pins = adapter.infrastructure()
        prepared = dict(request={'requestID': 'synthetic'}, semanticRequest={'requestSha256': 'source'},
                        body={'input': 'unchanged evidence'}, requestInputs={'private': 'provenance'}, binding={})
        entry = {'identity': adapter.fingerprint(prepared), 'estimatedCostUSD': 0}
        def verify(value, row):
            """Check exact native request association without semantic execution."""
            adapter.require(value == prepared and adapter.fingerprint(value) == row['identity'], 'REQUEST_DRIFT')
        Journal = adapter.batch_journal(native, verify, adapter.fingerprint, lambda *args: None)
        manifest = dict(generatorPins=pins, requests=[entry], queuedTokenLimit=1000)
        wire = adapter.canonical(manifest) + b'\n'; sha = adapter.digest(wire)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'execution.jsonl'
            with Journal(path, wire, sha) as journal:
                journal.append('prepared', 'synthetic', native.bundle(prepared))
                head = journal.head
            original = path.read_bytes()
            with Journal(path, wire, sha) as journal:
                self.assertEqual(journal.prepared('synthetic'), prepared)
                self.assertEqual(journal.head, head)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'PREFLIGHT_PIN_MISMATCH'):
                Journal(path, wire, 'incorrect')
            bad = deepcopy(manifest); bad['generatorPins'] = {}
            bad_wire = adapter.canonical(bad) + b'\n'
            with self.assertRaisesRegex(ValueError, 'JOURNAL_GENERATOR_DRIFT'):
                Journal(path, bad_wire, adapter.digest(bad_wire))
            damaged = original.replace(b'unchanged evidence', b'altered evidence')
            self.assertNotEqual(original, damaged); path.write_bytes(damaged)
            with self.assertRaises(ValueError):
                with Journal(path, wire, sha): pass


if __name__ == '__main__': unittest.main()
