"""Focused synthetic tests for opt-in conformance; no provider/corpus IO."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import test_datasets_semantic_offline_pipeline as fixtures
from src.extraction.llm import format_conformance as conformance
from src.extraction.llm.datasets import request_contract, offline_pipeline
from src.extraction.llm.pilot_preflight import canonical, strict_schema, check_strict_structure, digest, build_preflight


class FormatConformanceTests(unittest.TestCase):
    """Recover representation only, retaining independent validation boundaries."""

    def setUp(self):
        """Reuse the accepted synthetic two-assertion fixture, not its tests."""
        self.fixture = fixtures.OfflineReplayTests()
        self.fixture.setUp()
        self.request = request_contract.build_request(**self.fixture.inputs)

    def run_case(self, payload):
        """Run only in-memory replay with network access prohibited."""
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            return conformance.replay_conformant(canonical(payload), family='hydroshare',
                request_inputs=self.fixture.inputs, expected_request_sha256=self.request['requestSha256'],
                conformance_version=conformance.VERSION)

    def test_exact_name_and_iri(self):
        """Declared CURIE/expanded IRI recover exactly without modifying originals."""
        for value in ('Tool', 'ciroh:Tool', 'https://w3id.org/ciroh/ontology#Tool'):
            with self.subTest(value=value):
                payload=self.fixture.payload(); payload['candidateNodes'][0]['class']=value
                payload['candidateEdges'][0]['relation']='ciroh:usesTool'
                original=deepcopy(payload)
                result=self.run_case(payload)
                self.assertEqual([r['finalDisposition'] for r in result['derivedReplay']['finalRecords']], ['validated']*2)
                self.assertEqual(payload,original)
                self.assertEqual(bytes.fromhex(result['originalResponseBytesHex']),canonical(original))
                self.assertFalse(result['kgAuthorization'])

    def test_mismatch_and_dependents(self):
        """Wrong declaration/inventory rejects the node and never validates its edge."""
        for identifier,value in [('A-DOM02','https://unrelated.test/Tool'),('A-DOM04','ciroh:Tool'),('unknown','Tool')]:
            payload=self.fixture.payload(); payload['candidateNodes'][0].update(inventoryId=identifier, **{'class':value})
            result=self.run_case(payload)
            self.assertTrue(all(r['finalDisposition']!='validated' for r in result['derivedReplay']['finalRecords']))

    def test_unique_invalid_anchor(self):
        """Ignore only redundant invalid anchors; quotations and coordinates survive."""
        payload=self.fixture.payload()
        for row in payload['candidateNodes']+payload['candidateEdges']:
            row['evidence'][0]['locatorAnchor']='paragraph one'
        result=self.run_case(payload)
        self.assertEqual(len(result['changes']),2)
        self.assertTrue(all(r['finalDisposition']=='validated' for r in result['derivedReplay']['finalRecords']))
        self.assertEqual(json.loads(bytes.fromhex(result['derivedResponseBytesHex']))['candidateNodes'][0]['evidence'][0]['evidenceText'],self.fixture.quote)

    def test_repeated_and_missing_literal(self):
        """Repeated quotes require a unique literal anchor; absent quotes stay absent."""
        from src.extraction.llm.publications.deterministic_evidence_binding import bind_evidence_spans
        body={'artifactFamily':'hydroshare','sourceUnits':[{'sourceUnitID':'u','text':'x café; y café'}]}
        trusted={'text':body['sourceUnits'][0]['text'],'startOffsetInDocument':0,
                 'canonicalArtifactID':'owner','sourceUnitID':'u','textHash':'hash','sectionID':None,'sectionTitleRaw':None}
        for quote,anchor,expected in [('café','café','failed'),('café','y café','bound'),('missing','y café','failed'),('CAFE','y café','failed')]:
            payload={'candidateNodes':[{'evidence':[{'sourceUnitID':'u','evidenceText':quote,'locatorAnchor':anchor}]}]}
            derived,changes=conformance.derive(payload,body)
            self.assertFalse(changes)
            _,report=bind_evidence_spans({'evidenceSpans':derived['candidateNodes'][0]['evidence']},trusted)
            self.assertEqual(report['bindingStatus'],expected)

    def test_historical_compatibility(self):
        """No-op conformance keeps historical response and replay bytes identical."""
        raw=canonical(self.fixture.payload())
        before=offline_pipeline.replay_recorded_response(raw,request_inputs=self.fixture.inputs,
            expected_request_sha256=self.request['requestSha256'])
        result=self.run_case(self.fixture.payload())
        self.assertEqual(result['derivedReplaySha256'],before.report_sha256)
        self.assertEqual(result['originalResponseSha256'],result['derivedResponseSha256'])
        with self.assertRaises(ValueError):
            conformance.replay_conformant(raw,family='hydroshare',request_inputs=self.fixture.inputs,
                expected_request_sha256=self.request['requestSha256'],conformance_version='unknown')
        payload=self.fixture.payload();payload['candidateNodes'][0]['modelGate']=True
        result=self.run_case(payload)
        self.assertTrue(all(r['finalDisposition']!='validated' for r in result['derivedReplay']['finalRecords']))

    def test_prospective_schema(self):
        """Each inventory branch pins canonical names; historical schema stays exact."""
        body=self.request['request']; original=strict_schema(body['responseContract'],body['targetProfile'])
        schema=conformance.canonical_response_schema(body['responseContract'],body['targetProfile'],schema_version=conformance.SCHEMA_VERSION)
        check_strict_structure(schema)
        for group,field in [('candidateNodes','class'),('candidateEdges','relation')]:
            for branch in schema['properties'][group]['items']['anyOf']:
                self.assertEqual(len(branch['properties'][field]['enum']),1)
        self.assertEqual(original,strict_schema(body['responseContract'],body['targetProfile']))
        self.assertNotEqual(original,schema)

    def test_envelope_is_prospective(self):
        """Versioned schema changes wire hash, never source/request/input bytes."""
        old=build_preflight(self.request,output_ceiling=32768)
        new=conformance.build_conformant_preflight(self.request,schema_version=conformance.SCHEMA_VERSION)
        for key in ('semanticRequestBytes','semanticRequestSha256','inputBytes','providerInputSha256'):
            self.assertEqual(old[key],new[key])
        self.assertNotEqual(old['schemaSha256'],new['schemaSha256'])
        self.assertEqual(new['providerEnvelopeSha256'],digest(new['wireBytes']))
        self.assertEqual(old,build_preflight(self.request,output_ceiling=32768))
        self.assertEqual(new['authorization'],'NOT AUTHORIZED')
