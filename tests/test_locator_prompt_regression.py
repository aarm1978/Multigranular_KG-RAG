"""Focused prospective locator wording and distinct smoke-state regression checks."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import compatibility_smoke as smoke
from src.extraction.llm.construction_acceptance import replay_and_project
from src.extraction.llm.format_conformance import build_conformant_preflight, SCHEMA_VERSION, VERSION
from src.extraction.llm.pilot_preflight import canonical, digest


class LocatorPromptTests(unittest.TestCase):
    def test_versions_preserve_inputs_and_process_responses(self):
        """Only prospective prompt metadata and appended wording change for all families."""
        for directory, family in [('datasets', 'hydroshare'), ('coderepos', 'github'), ('documents', 'ciroh_hub')]:
            with self.subTest(family=family):
                fixture = importlib.import_module('test_' + directory + '_semantic_offline_pipeline').OfflineReplayTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                before = deepcopy(fixture.inputs)
                contract = importlib.import_module('src.extraction.llm.' + directory + '.request_contract')
                old = contract.build_request(**fixture.inputs, request_version=family + '-request/1.2.0')
                new_inputs = {**fixture.inputs, 'request_version': contract.LOCATOR_REQUEST_VERSION}
                new = contract.build_request(**new_inputs)
                self.assertEqual(new['status'], 'request_ready')
                expected = deepcopy(old['request'])
                expected.update(schemaVersion=contract.LOCATOR_REQUEST_VERSION, promptIdentifier=contract.LOCATOR_PROMPT_IDENTIFIER)
                expected['instructions'] += list(contract.LOCATOR_INSTRUCTIONS)
                self.assertEqual(new['request'], expected)
                self.assertEqual(before, fixture.inputs)
                self.assertEqual(old, contract.build_request(**fixture.inputs, request_version=family + '-request/1.2.0'))
                self.assertNotEqual(old['requestSha256'], new['requestSha256'])
                preflights = [build_conformant_preflight(r, schema_version=SCHEMA_VERSION,
                    projection_version=('github-provider-input/' + v if family == 'github' else None))
                    for r, v in [(old, '1.2.0'), (new, '1.2.1')]]
                self.assertEqual(preflights[0]['schemaSha256'], preflights[1]['schemaSha256'])
                self.assertEqual(json.loads(preflights[1]['inputBytes'])['sourceUnits'], old['request']['sourceUnits'])
                result = replay_and_project(canonical(fixture.payload()), family=family, request_inputs=new_inputs,
                    expected_request_sha256=new['requestSha256'], conformance_version=VERSION, schema_version=SCHEMA_VERSION).to_record()
                self.assertEqual(result['status'], 'projection_completed')
                self.assertEqual(result['originalReplay']['requestAssociation'], 'matched_caller_supplied_digest')

    def test_manifest_digest_fixes_distinct_state_and_blocks_redispatch(self):
        """An alternate path for identical bytes cannot create a fresh attempt state."""
        with tempfile.TemporaryDirectory() as temporary, patch.multiple(smoke,
                MANIFEST=smoke.MANIFEST, MANIFEST_SHA256=smoke.MANIFEST_SHA256, STATE=smoke.STATE):
            root = Path(temporary)
            original_state = smoke.STATE
            old_state = root / original_state
            old_state.mkdir(parents=True)
            (old_state / 'completed.json').write_bytes(b'original')
            relative = 'var/study2_step13/new/manifest.json'
            path = root / relative
            path.parent.mkdir(parents=True)
            raw = canonical({'requests': []})
            path.write_bytes(raw)
            with self.assertRaises(ValueError): smoke.select_manifest(root, relative, '0' * 64)
            smoke.select_manifest(root, relative, digest(raw))
            state = smoke.STATE
            self.assertNotEqual(state, original_state)
            alternate = path.with_name('alias.json'); alternate.write_bytes(raw)
            smoke.select_manifest(root, str(alternate.relative_to(root)), digest(raw))
            self.assertEqual(smoke.STATE, state)
            (root / state).mkdir()
            with patch.object(smoke, 'load_bundle', return_value=({}, {})), patch.object(smoke, 'verify_approval'), \
                    patch.object(smoke, 'load_openai_api_key') as key, self.assertRaisesRegex(ValueError, 'no_redispatch'):
                smoke.execute(root, b'{}', 'synthetic')
            key.assert_not_called()
            self.assertEqual((old_state / 'completed.json').read_bytes(), b'original')
            with self.assertRaises(ValueError):
                smoke.select_manifest(root, relative, 'bee79a4d0f4ea23318ab19069af9c5b0af43cb4012492077136be7269cdf0245')
