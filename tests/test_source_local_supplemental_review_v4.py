"""Focused v4 regression and immutable-selection guards, with one bounded authentic group."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from test_source_local_supplemental_review_v3 import report as fixture
from src.evaluation import source_local_supplemental_review_v4 as r
from src.extraction.llm import materialized_evidence as m


def report(disposition='held', reason='full_content_not_static_visible:uncertain'):
    """Minimal native report carrying an explicit eligibility cause."""
    value=fixture(disposition,'bound' if disposition=='accepted' else 'needs_review')
    check=value['nativeValidationView']['originalReplay']['validationResult']['candidateChecks'][0]
    check['findings']=[] if disposition=='accepted' else [{'reason':reason}]
    return value


class ComparisonTests(unittest.TestCase):
    def test_direct_and_dependency_transitions(self):
        """Attribute one cause per candidate and retain explicit dependency effects."""
        a=report();b=report('accepted')
        for view,disposition in ((a,'held'),(b,'accepted')):
            native=view['nativeValidationView'];check=deepcopy(native['originalReplay']['validationResult']['candidateChecks'][0])
            check.update(candidateID='child',dependencies=['n'],findings=[],evidenceBindings=[])
            check['originalCandidate']['candidateID']='child'
            native['originalReplay']['validationResult']['candidateChecks'].append(check)
            native['decisions'].append(dict(candidateID='child',disposition=disposition,blockingReasons=[]))
        rows=r.compare_group(a,b)
        self.assertEqual([x['cause'] for x in rows],['direct_eligibility','downstream_dependency'])

    def test_loss_identity_abstention_and_unexplained_drift_stop(self):
        """No provider or candidate mutation can be disguised as eligibility recovery."""
        a=report('accepted')
        with self.assertRaisesRegex(r.v2.RegressionStop,'PREVIOUSLY_ACCEPTED_LOST'):r.compare_group(a,report())
        b=deepcopy(a);b['nativeValidationView']['projection']['nodes'][0]['boundEvidence'][0]['startOffsetInAuthority']=99
        with self.assertRaisesRegex(r.v2.RegressionStop,'PREVIOUSLY_ACCEPTED_CHANGED'):r.compare_group(a,b)
        for key,value in [('abstentions',[{'reason':'invented'}]),('quarantinedAbstentions',[{}]),('responseBytesHex','00')]:
            b=deepcopy(a);b[key]=value
            with self.assertRaisesRegex(r.v2.RegressionStop,'IMMUTABLE_GROUP_DRIFT'):r.compare_group(a,b)
        with self.assertRaisesRegex(r.v2.RegressionStop,'UNEXPLAINED_DECISION_CHANGE'):
            r.compare_group(report(reason='independent_semantic_failure'),report('accepted'))

    def test_output_immutability(self):
        """Refuse output before any loading or replay."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/r.OUTPUT).mkdir(parents=True)
            with patch.object(r.v2,'load_frozen') as load:
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):r.run(root)
                load.assert_not_called()

    def test_authentic_group_preserves_originals_and_accepted_records(self):
        """One small authentic group exercises the new route, never a corpus replay."""
        root=r.old.retry.ROOT;qroot=root/r.old.retry.QUEUE
        if not (qroot/'queue-manifest.json').exists():self.skipTest('Ignored authentic inputs unavailable')
        raw=(qroot/'queue-manifest.json').read_bytes();self.assertEqual(r.digest(raw),r.old.retry.QUEUE_SHA)
        entries=json.loads(raw)['requests']
        owner='hub:page:103555bceed0fdd50c00'
        entry=next(e for e in entries if e['ownerID']==owner and e['groupID']=='scientific_occurrences')
        bundle=(qroot/'queue'/entry['bundleFile']).read_bytes();self.assertEqual(r.digest(bundle),entry['bundleSha256'])
        p=json.loads(bundle);rid=entry['identity']['requestID']
        path=root/r.v3.OUTPUT/'groups'/(r.digest(rid.encode())+'.json')
        if not path.exists():self.skipTest('Ignored v3 group unavailable')
        before=r.v2.checked(path);original=deepcopy(before)
        with patch.object(socket.socket,'connect',side_effect=AssertionError('OFFLINE')),patch.object(socket.socket,'connect_ex',side_effect=AssertionError('OFFLINE')),r.old.production.ontology_parse_cache(),m.overlay():
            after=r.old.semantic.replay(p,bytes.fromhex(before['responseBytesHex']),expected_request_sha256=before['requestSha256'])
        r.compare_group(before,after)
        self.assertEqual(before,original)
        self.assertEqual((qroot/'queue'/entry['bundleFile']).read_bytes(),bundle)


if __name__=='__main__':unittest.main()
