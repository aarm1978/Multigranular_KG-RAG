"""Focused offline lexical, binding, dependency and authentic-offset regressions."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
import test_source_local_semantics_v041 as fixtures
from src.extraction.llm import source_local_hub_evidence as historical
from src.extraction.llm import source_local_hub_evidence_v044 as fixed
from src.evaluation import source_local_supplemental_review_v3 as review


class LexicalTests(unittest.TestCase):
    def test_void_elements_do_not_capture_following_prose(self):
        """Opaque tags have no children; attributes are not automatically evidence."""
        for tag in ('<br>','<hr style="border: 1px solid black;">','<img src="x.png" width="400">'):
            text='<div><a>'+tag+'</a></div>\nIndependent scientific prose.'
            start=text.index('Independent')
            self.assertEqual(set(fixed.regions(text)[start:]),{'prose'})
            self.assertEqual(set(historical.regions(text)[start:]),{'uncertain'})
            self.assertIn('uncertain',fixed.regions(tag))

    def test_malformed_unknown_and_dynamic_scopes_stay_opaque(self):
        """Do not repair genuine mismatches or reinterpret component children."""
        for text in ('<div><span>content</div>', '<Widget>content</Widget>',
                     '<div hidden>content</div>', '<img src="unfinished>content',
                     '<img src={value}>content', '{condition && "content"}', '<div>content'):
            offset=text.index('content')
            self.assertNotEqual(set(fixed.regions(text)[offset:offset+7]),{'prose'},text)
        self.assertEqual(fixed.regions('before\n</div>\nafter'),historical.regions('before\n</div>\nafter'))

    def test_prior_static_nested_evidence_and_offsets(self):
        """Closed static markup preserves exact character coordinates and prior behavior."""
        text='<div><p><strong>RiverTool processes streamflow.</strong></p></div>'
        self.assertEqual(fixed.regions(text),historical.regions(text))
        self.assertEqual(len(fixed.regions(text)),len(text))


class BindingTests(unittest.TestCase):
    """Run only the directly affected existing positive and negative contracts."""
    build=fixtures.CorrectionTests.build
    node=fixtures.CorrectionTests.node
    edge=fixtures.CorrectionTests.edge
    run_payload=fixtures.CorrectionTests.run_payload

    def setUp(self):
        fixtures.CorrectionTests.setUp(self)
        self.enterContext(review.old.production.ontology_parse_cache())
        self.enterContext(fixed.overlay())

    test_preserved_static_binding=fixtures.CorrectionTests.test_recovered_static_mdx_outside_historical_units
    test_parent_dependency=fixtures.CorrectionTests.test_positive_parameter_parent_path
    test_dynamic_code_and_examples=fixtures.CorrectionTests.test_inadmissible_regions_and_example_only_boundary
    test_example_parent=fixtures.CorrectionTests.test_example_remains_parent_bound

    def test_corrected_void_prose_binding(self):
        """Source hashes, exact quotation and original offsets remain authoritative."""
        q='RiverTool processes streamflow.';text='<hr>\n'+q
        p=self.build('ciroh_hub',text)
        r=self.run_payload(p,[self.node(p,'A-DOM02','Tool',q)],[self.edge(p,'C-DC07','describesTool',q)])
        e=r['projection']['nodes'][0]['boundEvidence'][0]
        self.assertEqual(e['lexicalClassifierVersion'],fixed.VERSION)
        self.assertEqual(e['startOffsetInAuthority'],5)
        self.assertEqual(text[e['startOffsetInAuthority']:e['endOffsetInAuthority']],q)


class AuthenticTests(unittest.TestCase):
    def test_authentic_mixed_group_preserves_accepted_records(self):
        """Exercise the accepted-record guard against real mixed accepted/held output."""
        root=review.old.retry.ROOT;qroot=root/review.old.retry.QUEUE
        if not (qroot/'queue-manifest.json').exists():self.skipTest('Ignored authentic fixtures unavailable')
        rid='ciroh_hub:v042:products_and_references:9da9139959fcc38b58a9d75a512335a8ec5bebe1fb66ed2c842526666d33e236'
        raw=(qroot/'queue-manifest.json').read_bytes();self.assertEqual(review.digest(raw),review.old.retry.QUEUE_SHA)
        entry=next(e for e in json.loads(raw)['requests'] if e['identity']['requestID']==rid)
        raw_bundle=(qroot/'queue'/entry['bundleFile']).read_bytes();self.assertEqual(review.digest(raw_bundle),entry['bundleSha256'])
        p=json.loads(raw_bundle);before=review.v2.checked(root/review.v2.OUTPUT/'groups'/(review.digest(rid.encode())+'.json'))
        self.assertTrue(before['projection']['nodes'] or before['projection']['edges'])
        from unittest.mock import patch
        import socket
        with patch.object(socket.socket,'connect',side_effect=AssertionError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=AssertionError('OFFLINE')),review.old.production.ontology_parse_cache(),fixed.overlay():
            after=review.old.semantic.replay(p,bytes.fromhex(before['responseBytesHex']),expected_request_sha256=before['requestSha256'])
        review.compare_group(before,after)

    def test_two_authentic_scientific_groups(self):
        """Replay two bounded immutable source cases, not a corpus recovery estimate."""
        root=review.old.retry.ROOT;qroot=root/review.old.retry.QUEUE
        if not (qroot/'queue-manifest.json').exists():self.skipTest('Ignored authentic fixtures unavailable')
        raw=(qroot/'queue-manifest.json').read_bytes()
        self.assertEqual(review.digest(raw),review.old.retry.QUEUE_SHA)
        queue=json.loads(raw);results=[]
        cases=[('hub:page:103555bceed0fdd50c00',2170,'dfa13ce7866d2a623d43f8c6b47e0ae0a0eaabf0f1f2907791ac5b7d120586a8'),
               ('hub:page:a43e995a4834e75d17db',1904,'1cbe5996f2beb8eca4edaf64ca9ff33e61a24ebabff54e1f708cc68aae0ca11c')]
        from unittest.mock import patch
        import socket
        with patch.object(socket.socket,'connect',side_effect=AssertionError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=AssertionError('OFFLINE')),review.old.production.ontology_parse_cache():
            for owner,offset,text_sha in cases:
                entry=next(e for e in queue['requests'] if e['ownerID']==owner and e['groupID']=='scientific_occurrences')
                bundle=(qroot/'queue'/entry['bundleFile']).read_bytes();self.assertEqual(review.digest(bundle),entry['bundleSha256'])
                p=json.loads(bundle);rid=entry['identity']['requestID']
                before=review.v2.checked(root/review.v2.OUTPUT/'groups'/(review.digest(rid.encode())+'.json'))
                text=p['requestInputs']['baseContext']['semanticRequest']['request']['sourceUnits'][0]['text']
                self.assertEqual(review.digest(text.encode()),text_sha)
                candidate=next(c for c in before['nativeValidationView']['originalReplay']['validationResult']['candidateChecks'] if c['candidateID']=='variable-streamflow')
                quote=candidate['originalCandidate']['evidence'][0]['evidenceText']
                self.assertEqual(text.find(quote),offset)
                self.assertEqual(set(historical.regions(text)[offset:offset+len(quote)]),{'uncertain'})
                self.assertEqual(set(fixed.regions(text)[offset:offset+len(quote)]),{'prose'})
                original=deepcopy(before)
                with fixed.overlay():after=review.old.semantic.replay(p,bytes.fromhex(before['responseBytesHex']),expected_request_sha256=before['requestSha256'])
                changes=review.compare_group(before,after)
                self.assertEqual(before,original)
                self.assertTrue(any(c['candidateID']=='variable-streamflow' and c['after']['disposition']=='accepted' for c in changes))
                items=[(p,after)]
                for sibling in queue['requests']:
                    if sibling['ownerID']!=owner or sibling['groupID']=='scientific_occurrences':continue
                    raw_bundle=(qroot/'queue'/sibling['bundleFile']).read_bytes()
                    self.assertEqual(review.digest(raw_bundle),sibling['bundleSha256'])
                    prepared=json.loads(raw_bundle);request_id=sibling['identity']['requestID']
                    prior=review.v2.checked(root/review.v2.OUTPUT/'groups'/(review.digest(request_id.encode())+'.json'))
                    with fixed.overlay():current=review.old.semantic.replay(prepared,bytes.fromhex(prior['responseBytesHex']),expected_request_sha256=prior['requestSha256'])
                    changes.extend(review.compare_group(prior,current));items.append((prepared,current))
                owner_report=review.old.semantic.consolidate(items)
                self.assertFalse(owner_report['zeroYield'])
                results.append((owner,len(changes),dict(nodes=len(owner_report['nodes']),edges=len(owner_report['edges']))))
        print('Bounded authentic cases:',results)


if __name__=='__main__':unittest.main()
