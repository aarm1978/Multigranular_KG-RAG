"""Focused verbatim instruction repetition checks."""
from copy import deepcopy
import importlib
import json
import unittest

from src.extraction.llm.construction_acceptance import replay_and_project
from src.extraction.llm.format_conformance import build_conformant_preflight, SCHEMA_VERSION, VERSION
from src.extraction.llm.pilot_preflight import canonical


class InstructionRepetitionTests(unittest.TestCase):
    def test_exact_repetition_final_field_and_replay(self):
        """Only prospective prompt metadata and appended wording change for all families."""
        for directory, family in [('datasets', 'hydroshare'), ('coderepos', 'github'), ('documents', 'ciroh_hub')]:
            with self.subTest(family=family):
                fixture = importlib.import_module('test_' + directory + '_semantic_offline_pipeline').OfflineReplayTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                before = deepcopy(fixture.inputs)
                contract = importlib.import_module('src.extraction.llm.' + directory + '.request_contract')
                old = contract.build_request(**fixture.inputs, request_version=family + '-request/1.2.1')
                new_inputs = {**fixture.inputs, 'request_version': contract.REPETITION_REQUEST_VERSION}
                new = contract.build_request(**new_inputs)
                self.assertEqual(new['status'], 'request_ready')
                expected = deepcopy(old['request'])
                expected.update(schemaVersion=contract.REPETITION_REQUEST_VERSION, promptIdentifier=contract.REPETITION_PROMPT_IDENTIFIER)
                expected['zzRepeatedInstructions'] = deepcopy(expected['instructions'])
                self.assertEqual(new['request'], expected)
                self.assertEqual(before, fixture.inputs)
                self.assertEqual(old, contract.build_request(**fixture.inputs, request_version=family + '-request/1.2.1'))
                self.assertNotEqual(old['requestSha256'], new['requestSha256'])
                preflights = [build_conformant_preflight(r, schema_version=SCHEMA_VERSION,
                    projection_version=('github-provider-input/' + v if family == 'github' else None))
                    for r, v in [(old, '1.2.1'), (new, '1.2.2')]]
                self.assertEqual(preflights[0]['schemaSha256'], preflights[1]['schemaSha256'])
                provider = json.loads(preflights[1]['inputBytes'])
                self.assertEqual(list(provider)[-1], 'zzRepeatedInstructions')
                self.assertEqual(provider['zzRepeatedInstructions'], old['request']['instructions'])
                self.assertEqual(provider['instructions'], provider['zzRepeatedInstructions'])
                self.assertNotIn('zzRepeatedInstructions', json.loads(preflights[0]['inputBytes']))
                self.assertEqual(preflights[1]['inputBytes'], canonical(provider))
                repeat = build_conformant_preflight(new, schema_version=SCHEMA_VERSION,
                    projection_version='github-provider-input/1.2.2' if family == 'github' else None)
                self.assertEqual(repeat, preflights[1])
                self.assertEqual(json.loads(preflights[1]['inputBytes'])['sourceUnits'], old['request']['sourceUnits'])
                result = replay_and_project(canonical(fixture.payload()), family=family, request_inputs=new_inputs,
                    expected_request_sha256=new['requestSha256'], conformance_version=VERSION, schema_version=SCHEMA_VERSION).to_record()
                self.assertEqual(result['status'], 'projection_completed')
                self.assertEqual(result['originalReplay']['requestAssociation'], 'matched_caller_supplied_digest')

