"""Focused offline full-inventory selection and submission-boundary regressions."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import source_local_specialized_production as p


class ProductionSelectionTests(unittest.TestCase):
    """Synthetic sources; no production replay, provider work or broad test suite."""
    def setUp(self):
        """Make complete synthetic historical inventories including three empty Hub pages."""
        self.network=patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK_FORBIDDEN'))
        self.network.start();self.addCleanup(self.network.stop)
        self.corpora={'hydroshare':[{'resource_id':str(i)} for i in range(42)],
            'github':{'repos':[{'repo_id':1,'html_url':'https://example.invalid/repo'}]},
            'ciroh_hub':{'pages':[{'canonical_url':'https://example.invalid/'+str(i)} for i in range(4)]}}
        self.original={'requests':[{'family':'hydroshare','ownerID':str(i)} for i in range(42)]+
            [{'family':'github','ownerID':'github:repo:1'},
             {'family':'ciroh_hub','ownerID':'hub:page:'+p.digest(b'https://example.invalid/0')[:20]}],
            'summary':{f:{'owners':n} for f,n in [('hydroshare',42),('github',1),('ciroh_hub',4)]}}
        self.recovery={'requests':[{'family':'hydroshare','ownerID':str(i)} for i in range(20)]}

    def test_parser_cache_is_exact_detached_and_still_hash_checked(self):
        """Acceleration preserves native authority checks and cannot leak mutations."""
        original=p.semantic.profiles.yaml
        expected=p.semantic.profiles.load_ontology()
        with p.ontology_parse_cache():
            actual=p.semantic.profiles.load_ontology()
            self.assertEqual(actual,expected)
            actual['ontology']['version']='mutated'
            self.assertEqual(p.semantic.profiles.load_ontology(),expected)
            with patch.object(p.semantic.profiles,'ONTOLOGY_SHA256','bad'):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):p.semantic.profiles.load_ontology()
        self.assertIs(p.semantic.profiles.yaml,original)

    def test_replacement_and_three_unqueued_hub_owners(self):
        """Recovery replaces whole input selection; all previously unqueued pages remain explicit."""
        rows=p.owner_inventory(self.original,self.recovery,self.corpora)
        self.assertEqual(len(rows),47)
        self.assertEqual(sum(r['sourceSelection']=='recovery' for r in rows),20)
        self.assertEqual(sum(r['sourceSelection']=='original' and r['family']=='hydroshare' for r in rows),22)
        self.assertEqual(sum(r['previouslyUnqueued'] for r in rows),3)
        self.assertEqual(len({(r['family'],r['ownerID']) for r in rows}),47)
        reordered=deepcopy(self.corpora);reordered['hydroshare'].reverse()
        self.assertEqual(rows,p.owner_inventory(self.original,self.recovery,reordered))

    def test_missing_duplicate_and_foreign_owner_fail_closed(self):
        """Never replace missing sources or accept ambiguous/foreign owner lineage."""
        for mode in ('missing','duplicate','foreign','missing_hub'):
            corpus=deepcopy(self.corpora);recovery=deepcopy(self.recovery)
            if mode=='missing':corpus['hydroshare'].pop()
            if mode=='duplicate':corpus['hydroshare'].append(corpus['hydroshare'][0])
            if mode=='foreign':recovery['requests'][0]['ownerID']='foreign'
            if mode=='missing_hub':corpus['ciroh_hub']['pages'].pop()
            with self.subTest(mode=mode),self.assertRaises(ValueError):p.owner_inventory(self.original,recovery,corpus)

    def test_complete_groups_and_blocked_owner_exclusion(self):
        """All three groups required; no duplicates or requests belonging to held owners."""
        rows=[dict(family='github',ownerID='one',status='prepared'),dict(family='github',ownerID='two',status='blocked')]
        with patch.object(p.grouped,'inventory',return_value={'a':{},'b':{},'c':{}}):
            requests=[dict(family='github',ownerID='one',groupID=g) for g in ('a','b','c')]
            p.check_groups(rows,requests)
            for changed in (requests[:-1],requests+[requests[0]],requests+[dict(family='github',ownerID='two',groupID='a')]):
                with self.assertRaises(ValueError):p.check_groups(rows,changed)

    def test_existing_output_is_immutable(self):
        """Refuse overwrite before reading any sources or generating new requests."""
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);root=repo/p.BASE;root.mkdir(parents=True)
            sentinel=root/'queue-manifest.json';sentinel.write_bytes(b'original')
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):p.prepare(repo,p.BASE)
            self.assertEqual(sentinel.read_bytes(),b'original')
            self.assertEqual(list(root.iterdir()),[sentinel])

    def test_new_hub_page_retains_full_authority_without_pilot_flags(self):
        """Historical empty units do not exclude complete MDX or release evidence holds."""
        from test_source_local_semantics import template
        with p.ontology_parse_cache():
            text="import Cards from './cards';\n<Cards />\n"
            t=template('ciroh_hub',text);inputs=t['requestInputs']
            self.assertFalse(inputs['reader_result']['sourceUnits'])
            inputs['request_version']='ciroh_hub-request/1.2.0'
            seed=p.full_hub_template(dict(ownerID=inputs['accepted_page_id'],inputs=inputs))
            context=p.semantic.build([seed]);body=context['semanticRequest']['request']
            self.assertNotIn('pilotOnly',body)
            self.assertEqual(body['sourceUnits'][0]['text'],text)
            self.assertEqual(context['requestInputs']['reader_result'],inputs['reader_result'])
            self.assertEqual(body['targetProfile'],p.semantic.profiles.get_profile('ciroh_hub',version=p.semantic.VERSION))

    def test_real_specialized_bundles_pass_streaming_preflight(self):
        """Native reconstruction checks exact context/provenance and catches file damage."""
        from test_source_local_semantics import template
        with p.ontology_parse_cache(), tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'queue').mkdir();(root/'contexts').mkdir()
            def write(path,value):
                """Seal synthetic canonical bytes exactly like preparation."""
                path=root/path;path.parent.mkdir(parents=True,exist_ok=True)
                raw=p.canonical(value)+b'\n';path.write_bytes(raw);return p.digest(raw)
            write(p.previous.ORIGINAL/'queue-manifest.json',self.original)
            write(p.previous.RECOVERY/'queue-manifest.json',self.recovery)
            for family,corpus in self.corpora.items():write(Path(p.CORPORA[family]),corpus)
            rows=p.owner_inventory(self.original,self.recovery,self.corpora)
            for row in rows:row['status']='prepared' if row['family']=='github' else 'blocked'
            row=next(r for r in rows if r['status']=='prepared')
            context=p.semantic.build([template('github','Streamflow is documented here.')],
                deferred_records=[{'recordID':'original-deferred','originalRecord':{'claim':'unresolved'}}])
            row['contextFile']='contexts/owner.json';row['contextSha256']=write(Path(row['contextFile']),context)
            requests=[];lines=[]
            for group in p.grouped.inventory('github'):
                q=p.grouped.build(context,group);raw=p.canonical(q)+b'\n';name=p.digest(raw)+'.json'
                write(Path('queue')/name,q);item,line=p.adapter.batch.input_line(q,1,p.adapter.fingerprint);lines.append(line)
                requests.append(dict(family='github',ownerID='github:repo:1',groupID=group,bundleFile=name,
                    bundleSha256=p.digest(raw),identity=p.adapter.fingerprint(q),batchItem=item,cost=p.previous.sizing.costs(q)))
                self.assertEqual(q['requestInputs']['baseContext'],context)
            blocked=[r['ownerID'] for r in rows if r['status']=='blocked']
            selection=dict(owners=rows,blockedOwners=blocked)
            selection_sha=write(Path('source-selection-manifest.json'),selection)
            manifest=dict(version=p.grouped.VERSION,selectionVersion=p.VERSION,sourceSelectionSha256=selection_sha,
                inputPins={},implementationPins={},requests=requests,blockedOwners=blocked,productionReady=False,
                batchInputSha256=p.digest(b''.join(lines)))
            sha=write(Path('queue-manifest.json'),manifest);(root/'batch-input.jsonl').write_bytes(b''.join(lines))
            actual,bundles=p.inspect_queue(root,Path('.'),sha,retain=True)
            self.assertEqual(actual,manifest);self.assertEqual(len(bundles),3)
            with self.assertRaisesRegex(ValueError,'PRODUCTION_BLOCKED'):p.load_queue(root,Path('.'),sha)
            (root/'queue'/requests[0]['bundleFile']).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'BUNDLE_DRIFT'):p.inspect_queue(root,Path('.'),sha)

    def test_partial_submission_and_corrupt_queue_fail_closed(self):
        """No partial owner selection can reach the native provider controller."""
        with patch.object(p,'inspect_queue',return_value=({'productionReady':False,'blockedOwners':['held']},{})):
            with self.assertRaisesRegex(ValueError,'PRODUCTION_BLOCKED'):p.load_queue(Path('.'),p.BASE,'hash')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'queue-manifest.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'QUEUE_MANIFEST_DRIFT'):p.inspect_queue(root,Path('.'),'bad-hash')
        with self.assertRaisesRegex(ValueError,'BATCH_ONLY'):p.operate('submit','live','hash')


if __name__=='__main__':unittest.main()
