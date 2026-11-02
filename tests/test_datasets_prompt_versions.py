"""Focused synthetic legacy/prospective request and replay version compatibility."""
from copy import deepcopy
import hashlib
import json
import unittest
import test_datasets_semantic_offline_pipeline as fixture_module
from src.extraction.llm.datasets import request_contract as contract
from src.extraction.llm.datasets.offline_pipeline import replay_recorded_response


class PromptVersionTests(unittest.TestCase):
    """Version instructions without mutating historical request or output bytes."""
    def setUp(self):
        """Reuse a synthetic source fixture, never authentic pilot files."""
        self.fixture = fixture_module.OfflineReplayTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.inputs = self.fixture.inputs
        self.raw = json.dumps(self.fixture.payload(), ensure_ascii=False).encode()

    def test_legacy_exact_hashes_and_explicit_default(self):
        """Pinned pre-change synthetic hashes protect complete serialization/replay."""
        request = contract.build_request(**self.inputs)
        self.assertEqual(request['requestSha256'], '0f39093182d6f1cc0f2c7d4d63deeba8fb77ebde036f966efac002f3e0391acf')
        self.assertEqual(request, contract.build_request(**self.inputs, request_version=contract.REQUEST_VERSION))
        self.assertNotIn('promptIdentifier', request['request'])
        self.assertEqual(replay_recorded_response(self.raw, request_inputs=self.inputs).report_sha256,
                         '8fccea59b5e1c58cddd043ca6d857ac9564a8c3cb6851889733ccdaf49837840')

    def test_opt_in_hash_routing_and_immutability(self):
        """Only version/prompt instructions change; replay reconstructs exact opt-in."""
        before = deepcopy(self.inputs)
        inputs = {**self.inputs, 'request_version': contract.PROSPECTIVE_REQUEST_VERSION}
        old = contract.build_request(**self.inputs)
        new = contract.build_request(**inputs)
        self.assertNotEqual(old['requestSha256'], new['requestSha256'])
        self.assertEqual(new, contract.build_request(**inputs))
        self.assertEqual(new['request']['promptIdentifier'], contract.PROMPT_IDENTIFIER)
        self.assertEqual(new['request']['instructions'], old['request']['instructions'] + list(contract.CLARIFICATION_INSTRUCTIONS))
        for field in old['request']:
            if field not in ('schemaVersion','instructions'):
                self.assertEqual(old['request'][field], new['request'][field])
        report = replay_recorded_response(self.raw, request_inputs=inputs, expected_request_sha256=new['requestSha256'])
        self.assertEqual(report.to_record()['status'], 'replay_completed')
        self.assertEqual(report.to_record()['parseResult']['requestContractVersion'], contract.PROSPECTIVE_REQUEST_VERSION)
        self.assertEqual(report.to_record()['parseResult']['responseContractVersion'], 'hydroshare-response/1.0.0')
        self.assertEqual(report.response_bytes, self.raw)
        self.assertEqual(report, replay_recorded_response(self.raw, request_inputs=inputs, expected_request_sha256=new['requestSha256']))
        self.assertEqual(before, self.inputs)
        mismatch = replay_recorded_response(self.raw, request_inputs=inputs, expected_request_sha256=old['requestSha256'])
        self.assertEqual(mismatch.to_record()['status'], 'processing_failed')

    def test_unknown_versions_and_mislabeled_prompt_fail_closed(self):
        """No malformed selection or recomputed hash can silently pick new wording."""
        for version in (None, '', [], {}, 1, 'hydroshare-request/9.0.0'):
            inputs = {**self.inputs, 'request_version': version}
            self.assertEqual(contract.build_request(**inputs)['status'], 'request_failed')
            self.assertEqual(replay_recorded_response(self.raw, request_inputs=inputs).to_record()['status'], 'processing_failed')
            request = contract.build_request(**self.inputs)
            request['request']['schemaVersion'] = version
            request['requestSha256'] = hashlib.sha256(contract._json(request['request']).encode()).hexdigest()
            self.assertEqual(contract.parse_recorded_response(self.raw, request=request)['status'], 'processing_failed')
        request = contract.build_request(**self.inputs, request_version=contract.PROSPECTIVE_REQUEST_VERSION)
        request['request']['instructions'] = list(contract.INSTRUCTIONS)
        request['requestSha256'] = hashlib.sha256(contract._json(request['request']).encode()).hexdigest()
        self.assertEqual(contract.parse_recorded_response(self.raw, request=request)['status'], 'processing_failed')

    def test_local_failure_isolation_unchanged_across_versions(self):
        """Invalid sibling evidence stays local; neither variant repairs proposals."""
        payload = self.fixture.payload()
        bad = deepcopy(payload['candidateNodes'][0])
        bad.update(candidateID='bad', evidence=[{'sourceUnitID': self.fixture.uid, 'evidenceText':'fabricated'}])
        payload['candidateNodes'].append(bad)
        dependent = deepcopy(payload['candidateEdges'][0])
        dependent.update(candidateID='dependent', target={'referenceType':'candidate_node','referenceID':'bad'})
        payload['candidateEdges'].append(dependent)
        raw = json.dumps(payload).encode()
        outcomes = []
        for version in (contract.REQUEST_VERSION, contract.PROSPECTIVE_REQUEST_VERSION):
            report = replay_recorded_response(raw, request_inputs={**self.inputs,'request_version':version}).to_record()
            rows = {r['candidateID']:r for r in report['finalRecords']}
            self.assertEqual(rows['tool']['finalDisposition'],'validated')
            self.assertEqual(rows['bad']['finalDisposition'],'failed_source_or_evidence_binding')
            self.assertNotEqual(rows['dependent']['finalDisposition'],'validated')
            self.assertEqual(rows['bad']['originalCandidate'],bad)
            self.assertFalse(report['kgAuthorization'])
            outcomes.append(report['finalRecords'])
        self.assertEqual(*outcomes)
