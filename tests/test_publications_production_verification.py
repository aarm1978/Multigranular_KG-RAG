"""Focused offline reporting regressions; fixtures are not production findings."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation.publications_production_verification import checked_outcome, diagnostics, file_hash, inventory
from collections import Counter


class FixtureLog:
    """Small already-validated journal view for report-only tests."""

    def __init__(self):
        """Represent two passes on one unit plus one uncovered unit."""
        self.entries = {rid: dict(paperID='p', sourceUnitID=unit, passIdentity=rid)
                        for rid, unit in [('a', 'u1'), ('b', 'u1'), ('c', 'u2')]}
        self.latest = {rid: (rid, 1) for rid in self.entries}
        self.outcomes = {key: key for key in self.latest.values()}
        self.receipts = {key: key[0] for key in self.latest.values()}
        self.request = dict(requestID='a', sourcePublicationID='p', sourceArtifactID='canonical-p',
                            sourceUnit={'sourceUnitID': 'u1'})
        self.projection = dict(requestID='a', sourceArtifactID='canonical-p', sourceUnitID='u1',
                               acceptedNodes=[], acceptedEdges=[dict(relationName='uses',
                               sourceEndpoint={'referenceType': 'paper'}, targetEndpoint={'referenceType': 'external'})])

    def category(self, rid):
        """Keep terminal cases distinct from accepted zero-node output."""
        return 'completed_protected' if rid == 'a' else 'terminal_review'

    def prepared(self, rid):
        """Expose the fixture request for sidecar comparison."""
        return {'request': self.request}

    def payload_at(self, key):
        """Return fixture outcomes or recorded overload evidence."""
        if isinstance(key, str):
            return dict(row={'response': {'status_code': 503, 'body': {'error': {'code': 'server_is_overloaded'}}}},
                        cost={'estimatedUSD': None}, usage=None)
        if key[0] == 'a':
            return {'native': dict(processable=True, productionResult=dict(
                acceptedSemanticProjection=self.projection, unresolvedIdentitySidecar={'records': []},
                attemptSelection={'selectedAttemptNumber': 1, 'attempts': [dict(attemptNumber=1,
                    parserResult={'parsedEnvelope': {'deferredRecords': [{}]}},
                    validation={'recordResults': [{'candidateValidationStatus': 'needs_review'}]})]}))}
        return {'native': dict(processable=False, retryEligible=False, transportHold='UNKNOWN_USAGE')}


class VerificationTests(unittest.TestCase):
    """Check coverage, diagnostic distinctions, immutability and integrity failures."""

    @patch('src.extraction.llm.publications.production_acceptance.derive_unresolved_identity_sidecar',
           return_value={'records': []})
    def test_inventory(self, _derive):
        """Do not equate requests with units or external endpoints with orphans."""
        log = FixtureLog()
        self.assertNotEqual(log.entries['a']['paperID'], log.projection['sourceArtifactID'])
        before = copy.deepcopy(log.__dict__)
        report, exceptions = inventory(log)
        self.assertEqual(report['requests'], 3)
        self.assertEqual(set(report['coverage']['paperID']), {'p'})
        _derive.assert_called_with(unittest.mock.ANY, log.request)
        self.assertEqual(report['coverageDenominators']['sourceUnitID'],
                         {'uniqueTotal': 2, 'partial': 1, 'uncovered': 1})
        self.assertEqual(report['acceptedEdges'], 1)
        self.assertEqual(report['zeroYield']['zeroNodes'], 1)
        self.assertEqual(report['zeroYield']['zeroNodesAndEdges'], 0)
        self.assertEqual(report['selectedEnvelopeCollections']['deferredRecords'], 1)
        self.assertEqual(exceptions[0]['history'][0]['providerError']['code'], 'server_is_overloaded')
        self.assertIsNone(exceptions[0]['history'][0]['cost']['estimatedUSD'])
        self.assertFalse(exceptions[0]['retryEligible'])
        self.assertEqual(log.__dict__, before)
        self.assertEqual(inventory(log), (report, exceptions))

    def test_source_drift(self):
        """Independently reject each wrong projection identity."""
        for field in ('requestID', 'sourceArtifactID', 'sourceUnitID'):
            with self.subTest(field=field):
                log = FixtureLog()
                log.projection[field] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'PROJECTION_SOURCE_DRIFT'):
                    inventory(log)

    def test_request_manifest_drift(self):
        """Keep publication ownership and source-unit bindings separate from canonical IDs."""
        for field in ('requestID', 'sourcePublicationID', 'sourceUnitID'):
            with self.subTest(field=field):
                log = FixtureLog()
                target = log.request['sourceUnit'] if field == 'sourceUnitID' else log.request
                target[field] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'REQUEST_MANIFEST_SOURCE_DRIFT'):
                    inventory(log)

    @patch('src.extraction.llm.publications.full_corpus_gpt61_batch.verify_outcome',
           side_effect=ValueError('NATIVE_RESPONSE_BINDING_DRIFT'))
    def test_native_integrity_failure_propagates(self, native_check):
        """The reporting correction cannot bypass native provenance validation."""
        with self.assertRaisesRegex(ValueError, 'NATIVE_RESPONSE_BINDING_DRIFT'):
            checked_outcome({}, {}, {}, 1)
        native_check.assert_called_once_with({}, {}, {}, 1)

    @patch('src.extraction.llm.publications.production_acceptance.derive_unresolved_identity_sidecar',
           return_value={'records': ['different']})
    def test_sidecar_drift(self, _derive):
        """Unresolved content must retain its native policy derivation."""
        with self.assertRaisesRegex(ValueError, 'UNRESOLVED_SIDECAR_DRIFT'):
            inventory(FixtureLog())

    def test_diagnostic_labels(self):
        """Keep diagnostic locations and policy labels distinct."""
        counts = Counter()
        diagnostics({'held': [{'code': 'X'}], 'rejected': [{'code': 'X'}]}, counts)
        self.assertEqual(len(counts), 2)

    @patch('src.extraction.llm.publications.full_corpus_gpt61_batch.verify_outcome')
    def test_selected_hash_and_external_materialization(self, native_check):
        """Supplement native validation with reproducible hashes and policy materialization."""
        from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
        from src.extraction.llm.publications.candidate_validation import materialize_usable_pipeline_output
        validation = dict(requestID='r', requestSha256='h', outputID='o', evidenceResults=[], recordResults=[])
        validation['validationResultsHash'] = sha256_bytes(canonical_json(validation))
        envelope = dict(candidateNodes=[], candidateEdges=[], evidenceSpans=[])
        selected = dict(attemptNumber=1, validation=validation, parserResult={'parsedEnvelope': envelope},
                        usablePipelineOutput=materialize_usable_pipeline_output(envelope, validation))
        selection = dict(attempts=[selected], selectedAttemptNumber=1)
        selection['attemptSelectionHash'] = sha256_bytes(canonical_json(selection))
        outcome = dict(processable=True, attempt=selected, productionResult={'attemptSelection': selection})
        prepared = {'request': {'requestID': 'r', 'requestInputSha256': 'h'}}
        checked_outcome(prepared, {}, outcome, 1)
        native_check.assert_called_once()
        selection['attemptSelectionHash'] = 'corrupt'
        with self.assertRaisesRegex(ValueError, 'STORED_HASH_DRIFT'):
            checked_outcome(prepared, {}, outcome, 1)

    def test_byte_hash(self):
        """Input hashes depend on exact bytes and do not modify files."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input'
            path.write_bytes(b'abc')
            self.assertEqual(file_hash(path), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(path.read_bytes(), b'abc')


if __name__ == '__main__':
    unittest.main()
