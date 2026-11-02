"""Focused synthetic preflight checks; no local corpus or provider execution."""
from copy import deepcopy
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator, ValidationError

from src.extraction.llm import pilot_preflight as preflight
import test_datasets_semantic_offline_pipeline as hs_fixture
import test_coderepos_semantic_offline_pipeline as gh_fixture
import test_documents_semantic_offline_pipeline as hub_fixture


class PilotPreflightTests(unittest.TestCase):
    """Check only new envelope/schema boundaries with existing synthetic fixtures."""

    def fixtures(self):
        """Supply three bounded synthetic requests without running historical tests."""
        for module in (hs_fixture, gh_fixture, hub_fixture):
            fixture = module.OfflineReplayTests()
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            yield module, fixture, module.contract.build_request(**fixture.inputs)

    def test_three_envelopes_hashes_immutability_no_transport(self):
        """Bind exact input/wire bytes without reading credentials or networking."""
        for module, fixture, request in self.fixtures():
            before = deepcopy(request)
            with patch('socket.socket', side_effect=AssertionError('network')), patch('builtins.open', side_effect=AssertionError('credential/file IO')):
                result = preflight.build_preflight(request, output_ceiling=32768)
                self.assertEqual(result, preflight.build_preflight(request, output_ceiling=32768))
                restored = json.loads(preflight.canonical(request))
                self.assertEqual(result, preflight.build_preflight(restored, output_ceiling=32768))
            body = json.loads(result['wireBytes'])
            self.assertEqual(body['model'], 'gpt-5.6-sol')
            self.assertEqual(body['max_output_tokens'], 32768)
            self.assertEqual(body['reasoning'], {'effort':'medium'})
            self.assertIs(body['store'], False)
            self.assertNotIn('tools', body)
            self.assertTrue(body['text']['format']['strict'])
            self.assertEqual(body['input'].encode(), result['inputBytes'])
            self.assertEqual(result['providerEnvelopeSha256'], preflight.digest(result['wireBytes']))
            self.assertEqual(result['semanticRequestSha256'], request['requestSha256'])
            self.assertEqual(request, before)
            corrupt = deepcopy(request)
            corrupt['request']['kgAuthorization'] = True
            with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
                preflight.build_preflight(corrupt, output_ceiling=32768)

    def test_schemas_and_original_parser_local_failure_isolation(self):
        """Strict shape success cannot promote bad evidence or erase siblings."""
        for module, fixture, request in self.fixtures():
            schema = preflight.strict_schema(request['request']['responseContract'], request['request']['targetProfile'])
            preflight.check_strict_structure(schema)
            validator = Draft202012Validator(schema)
            payload = fixture.payload()
            validator.validate(payload)
            bad = deepcopy(payload['candidateNodes'][0])
            bad['candidateID'] = 'bad'
            bad['evidence'][0]['sourceUnitID'] = 'unselected'
            payload['candidateNodes'].append(bad)
            validator.validate(payload)  # unit eligibility is intentionally downstream
            parsed = module.contract.parse_recorded_response(json.dumps(payload), request=request)
            self.assertEqual([r['parseDisposition'] for r in parsed['candidateRecords'][:2]],
                             ['pending_validation', 'local_candidate_error'])
            self.assertEqual(parsed['originalParsedResponse'], payload)
            records = fixture.records(fixture.replay(payload))
            self.assertEqual(records['tool']['finalDisposition'], 'validated')
            self.assertEqual(records['bad']['finalDisposition'], 'rejected_invalid_assertion')
            bad['evidence'][0]['locatorAnchor'] = None
            with self.assertRaises(ValidationError):
                validator.validate(payload)

    def test_optional_variants_and_special_fields(self):
        """All generated closed-object variants fit parser field boundaries."""
        def witness(schema, root):
            """Construct shape-only examples to check field compatibility."""
            if '$ref' in schema:
                return witness(root['$defs'][schema['$ref'].split('/')[-1]], root)
            if 'anyOf' in schema:
                return witness(schema['anyOf'][0], root)
            if 'enum' in schema:
                return schema['enum'][0]
            if schema.get('type') == 'object':
                return {k:witness(v, root) for k,v in schema['properties'].items()}
            if schema.get('type') == 'array':
                return []
            return 'synthetic'
        for module, fixture, request in self.fixtures():
            schema = preflight.strict_schema(request['request']['responseContract'], request['request']['targetProfile'])
            validator = Draft202012Validator(schema)
            for group in ('candidateNodes','candidateEdges'):
                for branch in schema['properties'][group]['items']['anyOf']:
                    row = witness(branch, schema)
                    row['evidence'] = [{'sourceUnitID':fixture.uid, 'evidenceText':fixture.quote}]
                    payload = {'schemaVersion':module.contract.RESPONSE_VERSION,
                               'candidateNodes':[], 'candidateEdges':[], 'abstentions':[]}
                    payload[group] = [row]
                    validator.validate(payload)
                    parsed = module.contract.parse_recorded_response(json.dumps(payload), request=request)
                    self.assertEqual(parsed['candidateRecords'][0]['parseDisposition'], 'pending_validation', row)
            for anchor in (False, True):
                payload = fixture.payload()
                fragment = payload['candidateNodes'][0]['evidence'][0]
                fragment['contribution'] = 'independent support'
                if anchor:
                    fragment['locatorAnchor'] = fixture.quote
                validator.validate(payload)
                self.assertEqual(module.contract.parse_recorded_response(json.dumps(payload), request=request)['candidateRecords'][0]['parseDisposition'], 'pending_validation')

    def test_source_drift_and_schema_fail_closed(self):
        """Selection, source bytes, coordinates and strict objects fail closed."""
        for module, fixture, request in self.fixtures():
            body = request['request']
            expected = [{k:u[k] for k in ('sourceUnitID','authorityTextSha256')} for u in body['sourceUnits']]
            preflight.verify_selection(request, expected, body['owner']['endpointID'])
            for field in ('sourceUnitID','authorityTextSha256'):
                changed = deepcopy(expected)
                changed[0][field] = 'drift'
                with self.assertRaises(ValueError):
                    preflight.verify_selection(request, changed, body['owner']['endpointID'])
            with self.assertRaises(ValueError):
                preflight.verify_selection(request, expected, 'wrong-owner')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = root / next(iter(preflight.SNAPSHOTS))
            first.parent.mkdir(parents=True)
            first.write_text('[]')
            with self.assertRaisesRegex(ValueError, 'corpus_snapshot_drift'):
                preflight.rebuild_selected(root)
        with self.assertRaises(ValueError):
            preflight.check_strict_structure({'type':'object','properties':{'x':{'type':'string'}},'required':[],'additionalProperties':False})
