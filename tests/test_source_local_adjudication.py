"""Bounded offline reviewer-adjudication regressions; no production writes."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
import test_source_local_semantics as fixtures
from src.evaluation import source_local_adjudication as a
from src.evaluation import source_local_supplemental_review_v41 as runner
from src.extraction.llm import materialized_evidence as m


class AdjudicationTests(unittest.TestCase):
    """Exercise actual native construction, duplicate and dependent-parent machinery."""
    build = fixtures.SourceLocalTests.build
    node = fixtures.SourceLocalTests.node
    edge = fixtures.SourceLocalTests.edge
    run_payload = fixtures.SourceLocalTests.run_payload

    def setUp(self):
        """Disable sockets and cache ontology parsing within a focused test only."""
        fixtures.SourceLocalTests.setUp(self)
        self.enterContext(runner.old.production.ontology_parse_cache())
        self.enterContext(m.overlay())

    def fixture(self, winner='bad', counterpart='good', dependent_parent=None):
        """Make source-bound but reviewer-distinguished same-triple evidence."""
        wrong = 'Launch the notebook.'
        right = 'To retrieve observations, configure the notebook path and import data grabbers.'
        parameter = 'Set start_date to the first date of the retrieval period.'
        p = self.build('ciroh_hub', wrong+'\n'+right+'\n'+parameter)
        nodes = [self.node(p,'A-DC05','Procedure',right,cid='proc'),
                 self.node(p,'A-DOM02','Tool',right,cid='unrelated')]
        edges = [self.edge(p,'C-DC20','hasProcedure',wrong,target='proc',cid=winner),
                 self.edge(p,'C-DC20','hasProcedure',right,target='proc',cid=counterpart)]
        if dependent_parent:
            nodes.append(self.node(p,'A-DOM12','Parameter',parameter,cid='param',parentPath=[
                dict(referenceType='candidate_edge',referenceID=x) for x in (dependent_parent,'attach')]))
            edge = self.edge(p,'C-DC11','hasParameter',parameter,target='param',cid='attach')
            edge['source'] = dict(referenceType='candidate_node',referenceID='proc')
            edges.append(edge)
        prior = self.run_payload(p,nodes,edges)
        checks = {c['candidateID']:c for c in prior['originalReplay']['validationResult']['candidateChecks']}
        entry = dict(adjudicationID='test-review',reason='Explicit fixture reviewer exclusion',
            excluded=a.pin(checks[winner],p['semanticRequest']['request']),
            counterpart=a.pin(checks[counterpart],p['semanticRequest']['request']))
        return p,nodes,edges,prior,entry

    def test_three_named_pairs_and_historical_compatibility(self):
        """No candidate ID has special meaning; all approved pairs use identical machinery."""
        pairs=[('has-procedure-multi','has-procedure-hybrid'),
               ('edge-reference-compute-paper','edge-reference-imagery-paper'),
               ('e-page-jupyter','e-page-python-path')]
        for winner,counterpart in pairs:
            p,n,e,prior,entry=self.fixture(winner,counterpart)
            frozen=deepcopy(prior)
            with a.overlay([entry]): current=self.run_payload(p,n,e)
            decisions={d['candidateID']:d for d in current['decisions']}
            self.assertEqual(decisions[winner]['disposition'],'held')
            self.assertEqual(decisions[counterpart]['disposition'],'accepted')
            self.assertIn('reviewer_adjudicated_evidence_endpoint_mismatch',decisions[winner]['blockingReasons'])
            self.assertEqual(prior,frozen)
            self.assertEqual(self.run_payload(p,n,e),prior)
            self.assertEqual(next(d for d in prior['decisions'] if d['candidateID']=='unrelated'),decisions['unrelated'])
            self.assertEqual([c['originalCandidate'] for c in prior['originalReplay']['validationResult']['candidateChecks']],
                [c['originalCandidate'] for c in current['originalReplay']['validationResult']['candidateChecks']])

    def test_excluded_parent_not_retargeted(self):
        """Children explicitly depending on an excluded edge remain held, never repaired."""
        p,n,e,prior,entry=self.fixture(dependent_parent='bad')
        with a.overlay([entry]): current=self.run_payload(p,n,e)
        decisions={d['candidateID']:d for d in current['decisions']}
        self.assertEqual(decisions['good']['disposition'],'accepted')
        self.assertEqual(decisions['param']['disposition'],'held')
        self.assertEqual(decisions['attach']['disposition'],'held')

    def test_matching_parent_reconsidered_normally(self):
        """A genuine parent path to the authentic counterpart traverses normal closure."""
        p,n,e,prior,entry=self.fixture(dependent_parent='good')
        with a.overlay([entry]): current=self.run_payload(p,n,e)
        self.assertEqual(next(d for d in current['decisions'] if d['candidateID']=='param')['disposition'],'accepted')

    def test_pin_mismatch_and_duplicate_authorization_stop(self):
        """Reviewer decisions cannot migrate across evidence, source, identity or endpoint."""
        p,n,e,prior,entry=self.fixture()
        for field in ('candidateSha256','boundEvidenceSha256','ownerID','resolvedTarget','evidence'):
            bad=deepcopy(entry);bad['excluded'][field]='tampered'
            with self.assertRaisesRegex(ValueError,'PIN_DRIFT'), a.overlay([bad]):self.run_payload(p,n,e)
        with self.assertRaisesRegex(ValueError,'DUPLICATE_ADJUDICATION'), a.overlay([entry,entry]):self.run_payload(p,n,e)

    def test_reconsideration_does_not_waive_findings(self):
        """Clearing a duplicate marker retains all other blockers and original fields."""
        p,n,e,prior,entry=self.fixture()
        validation=deepcopy(prior['originalReplay']['validationResult'])
        good=next(c for c in validation['candidateChecks'] if c['candidateID']=='good')
        good['findings'].append(dict(reason='independent_semantic_failure',disposition='needs_review'))
        good['disposition']=good['validationDisposition']='needs_review'
        revised=a.apply(validation,p['semanticRequest']['request'],[entry])
        result=next(c for c in revised['candidateChecks'] if c['candidateID']=='good')
        self.assertEqual(result['disposition'],'needs_review')
        self.assertEqual(result['findings'],good['findings'])
        self.assertFalse(result['suppressedDuplicate'])


class OutputTests(unittest.TestCase):
    def test_existing_output_refused_without_writes(self):
        """Refuse a previous projection before any authority reads or processing."""
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dest=root/runner.OUTPUT;dest.mkdir(parents=True)
            marker=dest/'marker';marker.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):runner.run(root)
            self.assertEqual(marker.read_bytes(),b'original')
            self.assertEqual(list(dest.iterdir()),[marker])


class LocalAuthenticTests(unittest.TestCase):
    """Optional three-group T2 check using local originals; never full corpus replay."""
    def test_three_pinned_groups(self):
        """Reproduce v4, apply each reviewed exclusion and verify bounded comparisons."""
        repo=runner.old.retry.ROOT
        if not (repo/runner.v4.OUTPUT/'summary.json').exists():
            self.skipTest('Ignored authentic v4 records unavailable')
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NO_NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NO_NETWORK')))
        self.enterContext(runner.old.production.ontology_parse_cache())
        artifact=json.loads((repo/runner.ARTIFACT).read_bytes())
        queue=json.loads((repo/runner.old.retry.QUEUE/'queue-manifest.json').read_bytes())
        for entry in artifact['entries']:
            rid=entry['requestID'];q=next(q for q in queue['requests'] if q['identity']['requestID']==rid)
            raw=(repo/runner.old.retry.QUEUE/'queue'/q['bundleFile']).read_bytes()
            self.assertEqual(runner.digest(raw),q['bundleSha256']);prepared=json.loads(raw)
            path=repo/runner.v4.OUTPUT/'groups'/(runner.digest(rid.encode())+'.json')
            self.assertEqual(runner.digest(path.read_bytes()),entry['baselineGroupSha256'])
            prior=runner.v2.checked(path);raw=bytes.fromhex(prior['responseBytesHex'])
            from src.extraction.llm import source_local_specialized as specialized
            with m.overlay():
                before=m.stamp_report(specialized.replay(prepared,raw,expected_request_sha256=prior['requestSha256']))
                self.assertEqual(before,prior)
                with a.overlay([entry]):
                    after=m.stamp_report(specialized.replay(prepared,raw,expected_request_sha256=prior['requestSha256']))
            changes=runner.compare(prior,after,[entry])
            decisions={d['candidateID']:d for d in after['nativeValidationView']['decisions']}
            self.assertEqual(decisions[entry['excluded']['candidateID']]['disposition'],'held')
            self.assertEqual(decisions[entry['counterpart']['candidateID']]['disposition'],'accepted')
            self.assertEqual(len(changes),2)
            for field in ('responseSha256', 'abstentions', 'quarantinedAbstentions'):
                corrupt=deepcopy(after);corrupt[field]='changed'
                with self.assertRaises(runner.v2.RegressionStop):runner.compare(prior,corrupt,[entry])
            corrupt=deepcopy(after)
            untouched=next(d for d in corrupt['nativeValidationView']['decisions'] if d['candidateID'] not in
                {entry['excluded']['candidateID'],entry['counterpart']['candidateID']} and d['disposition']=='accepted')
            untouched['disposition']='held'
            with self.assertRaises(runner.v2.RegressionStop):runner.compare(prior,corrupt,[entry])
            items=[];before_items=[]
            for sibling in queue['requests']:
                if sibling['ownerID'] != entry['excluded']['ownerID']:continue
                sibling_id=sibling['identity']['requestID']
                sibling_raw=(repo/runner.old.retry.QUEUE/'queue'/sibling['bundleFile']).read_bytes()
                self.assertEqual(runner.digest(sibling_raw),sibling['bundleSha256'])
                sibling_prepared=json.loads(sibling_raw)
                sibling_report=runner.v2.checked(repo/runner.v4.OUTPUT/'groups'/(runner.digest(sibling_id.encode())+'.json'))
                before_items.append((sibling_prepared,sibling_report))
                items.append((sibling_prepared,after if sibling_id==rid else sibling_report))
            baseline_owner=runner.v2.checked(repo/runner.v4.OUTPUT/'owners'/(runner.digest(entry['excluded']['ownerID'].encode())+'.json'))
            self.assertEqual(specialized.consolidate(before_items),baseline_owner)
            revised_owner=specialized.consolidate(items)
            self.assertEqual(len(revised_owner['nodes']),len(baseline_owner['nodes']))
            self.assertEqual(len(revised_owner['edges']),len(baseline_owner['edges']))
            print('Bounded authentic group:',rid,'changed decisions:',len(changes),'owner consolidation verified')


if __name__=='__main__':unittest.main()
