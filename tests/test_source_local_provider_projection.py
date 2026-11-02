"""Offline diagnostics projection and immutable source/provenance regressions."""
from copy import deepcopy
import json
import socket
import unittest
from unittest.mock import patch

from test_source_local_semantics import template
from src.evaluation.source_local_specialized_production import ontology_parse_cache
from src.extraction.llm import source_local_specialized as s


class ProviderProjectionTests(unittest.TestCase):
    """Exercise real specialized envelopes without contacting any provider."""
    def setUp(self):
        """Block sockets and reuse only detached frozen ontology parsing."""
        for name in ('connect','connect_ex'):
            blocker=patch.object(socket.socket,name,side_effect=AssertionError('NETWORK_FORBIDDEN'))
            blocker.start();self.addCleanup(blocker.stop)
        cache=ontology_parse_cache();cache.__enter__();self.addCleanup(cache.__exit__,None,None,None)

    def test_all_families_keep_full_sources_and_private_diagnostics(self):
        """Every group is clean; original context and local diagnostic records stay exact."""
        for family in s.GROUPS:
            t=template(family,'Complete first paragraph.\n\nComplete last paragraph.')
            t['semanticRequest']['request']['sourceDiagnostics']=[{'reason':'historical diagnostic','payload':{'historicalSourceDiagnostics':[{'reason':'nested'}]}}]
            t['semanticRequest']['requestSha256']=s.digest(json.dumps(t['semanticRequest']['request'],ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
            context=s.base.build([t]);before=deepcopy(context)
            for group in s.inventory(family):
                q=s.build(context,group,provider_projection_version=s.PROVIDER_PROJECTION_VERSION)
                s.verify(q);s.assert_provider_clean(q['body'])
                self.assertNotIn('historicalSourceDiagnostics',s.canonical(q['body']).decode())
                self.assertEqual(json.loads(q['body']['input'])['sourceUnits'],context['semanticRequest']['request']['sourceUnits'])
                self.assertEqual(q['requestInputs']['baseContext'],before)
                self.assertTrue(q['requestInputs']['localHistoricalDiagnostics'])
            self.assertEqual(context,before)
            old=s.build(context,next(iter(s.inventory(family))))
            self.assertIn('historicalSourceDiagnostics',old['semanticRequest']['request'])
            s.verify(old)

    def test_nested_encoded_payloads_and_no_source_filtering(self):
        """Nested dict/list/JSON diagnostics are removed; exact eligible text is retained."""
        units=[{'sourceUnitID':'one','text':'Full code and prose remain unchanged.\n'}]
        payload={'sourceUnits':units,'nested':[{'historicalSourceDiagnostics':[1]}],
            'encoded':json.dumps({'nested':json.dumps({'historicalSourceDiagnostics':[2],'keep':'yes'})})}
        removed=[];clean=s.provider_projection(payload,removed=removed)
        s.assert_provider_clean(clean)
        self.assertEqual(clean['sourceUnits'],units)
        self.assertEqual(json.loads(json.loads(clean['encoded'])['nested']),{'keep':'yes'})
        self.assertEqual([r['value'] for r in removed],[[1],[2]])
        with self.assertRaisesRegex(ValueError,'FORBIDDEN'):s.assert_provider_clean(payload)
        with self.assertRaisesRegex(ValueError,'DIAGNOSTIC_FIELD_IN_SOURCE_UNIT'):
            s.provider_projection({'sourceUnits':[{'text':'{"historicalSourceDiagnostics":[]}'}]})

    def test_clean_projection_replay_keeps_native_provenance(self):
        """Empty authentic response follows unchanged native replay without provider work."""
        context=s.base.build([template('github','No scientific assertion is supported.')])
        q=s.build(context,'quantities_and_concepts',provider_projection_version=s.PROVIDER_PROJECTION_VERSION)
        raw=s.canonical(dict(schemaVersion=s.VERSION,candidateNodes=[],candidateEdges=[],abstentions=[]))
        r=s.replay(q,raw,expected_request_sha256=q['semanticRequest']['requestSha256'])
        self.assertTrue(r['zeroYield']);self.assertEqual(r['responseSha256'],s.digest(raw))
        self.assertEqual(r['baseContextSha256'],context['semanticRequest']['requestSha256'])
        damaged=deepcopy(q);damaged['body']['extra']={'historicalSourceDiagnostics':[]}
        with self.assertRaisesRegex(ValueError,'SPECIALIZED_REQUEST_DRIFT'):s.verify(damaged)


if __name__=='__main__':unittest.main()
