"""Focused offline tests of the new family adapter and reused Batch machinery."""
from copy import deepcopy
import argparse
import importlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm import source_family_batch as run
from src.extraction.llm import source_family_queue as queue
from src.extraction.llm import full_corpus_source_family_batch as cli
from test_full_corpus_gpt61_batch import FakeAPI


class FamilyBatchTests(unittest.TestCase):
    """Use synthetic accepted reader fixtures and mocked provider operations only."""

    @classmethod
    def setUpClass(cls):
        """Load existing read-only transport dependencies with sockets prohibited."""
        with patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK')):
            cls.paired, cls.native, cls.pins = run.infrastructure()

    def setUp(self):
        """Block every network socket throughout each test."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, family):
        """Prepare one family through its accepted synthetic request builder."""
        directory = run.conformance.DIRECTORIES[family]
        module = importlib.import_module('test_' + directory + '_semantic_offline_pipeline')
        fixture = module.OfflineReplayTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        inputs = deepcopy(fixture.inputs)
        inputs['request_version'] = family + '-request/1.2.0'
        contract = importlib.import_module('src.extraction.llm.' + directory + '.request_contract')
        return run.prepare(contract.build_request(**inputs), inputs), fixture.payload()

    def receipt(self, p, payload, *, status='completed', raw=None):
        """Create an authentic-shape response wrapper, never a real response."""
        text = raw if raw is not None else run.canonical(payload).decode()
        body = dict(id='resp-fixture', model='gpt-6.1-sol', status=status,
                    service_tier='batch', created_at=1,
                    usage=dict(input_tokens=100, output_tokens=20),
                    output=[dict(type='message', content=[dict(type='output_text', text=text)])])
        row = dict(custom_id=run.batch.input_line(p, 1, run.fingerprint)[0]['custom_id'],
                   error=None, response=dict(status_code=200, body=body))
        return run.batch.response_record(row, p, self.paired, 'batch-fixture', 1)

    def test_family_envelopes_replay_and_acceptance(self):
        """Every family retains strict schema, evidence, replay and source identity."""
        for family in run.conformance.DIRECTORIES:
            with self.subTest(family=family):
                p, payload = self.fixture(family)
                run.verify_prepared(p, {'identity': run.fingerprint(p)})
                self.assertEqual(p['body']['model'], 'gpt-6.1-sol')
                self.assertTrue(p['body']['text']['format']['strict'])
                receipt = self.receipt(p, payload)
                outcome = run.process(p, receipt, 1)
                self.assertTrue(outcome['processable'])
                self.assertFalse(outcome['retryEligible'])
                self.assertEqual(outcome['productionResult']['status'], 'projection_completed')
                self.assertEqual(len(outcome['productionResult']['decisions']), 2)
                self.assertFalse(outcome['productionResult']['kgAuthorization'])

    def test_retry_controller_and_one_attempt_compatibility(self):
        """Only native technical errors allow a second identical production attempt."""
        p, payload = self.fixture('hydroshare')
        receipt = self.receipt(p, payload, raw='{')
        first = run.process(p, receipt, 1)
        self.assertTrue(first['retryEligible'])
        self.assertFalse(run.process(p, receipt, 1, compatibility=True)['retryEligible'])
        second = run.process(p, receipt, 2, first['attempt'])
        self.assertFalse(second['retryEligible'])
        self.assertEqual(second['attemptSelection']['selectionDisposition'], 'retry_exhausted_processing_failure')
        payload['candidateNodes'][0]['evidence'][0]['evidenceText'] = 'absent quotation'
        held = run.process(p, self.receipt(p, payload), 1)
        self.assertTrue(held['processable'])
        self.assertFalse(held['retryEligible'])

    def test_unknown_usage_and_cost_categories(self):
        """Unknown billing stops retries; uncategorized usage is explicitly estimated."""
        p, payload = self.fixture('hydroshare')
        receipt = self.receipt(p, payload)
        self.assertIn('conservative', receipt['cost']['basis'])
        body = deepcopy(receipt['providerResponse'])
        body['usage']['input_tokens_details'] = {'cached_tokens': 10, 'cache_write_tokens': 20}
        self.assertEqual(self.paired.usage_cost(body, run.batch.PRICING)['basis'], 'reported_cache_details')
        receipt['cost']['estimatedUSD'] = None
        outcome = run.process(p, receipt, 1)
        self.assertEqual(outcome['transportHold'], 'UNKNOWN_USAGE')
        self.assertFalse(outcome['retryEligible'])

    def test_interrupted_posts_restart_and_no_duplicate_dispatch(self):
        """The new bundle works with real journal replay and unique remote recovery."""
        for lost in ('lose_upload', 'lose_create'):
            with self.subTest(lost=lost):
                p, payload = self.fixture('hydroshare')
                manifest = dict(generatorPins=self.pins, requests=[dict(identity=run.fingerprint(p),
                    estimatedCostUSD=.1)], queuedTokenLimit=100, meaningfulSampleRequests=100)
                data = run.batch.canonical_json(manifest) + b'\n'
                Journal = run.journal_type(self.paired, self.native)
                path = self.root / lost / 'execution.jsonl'
                api = FakeAPI()
                setattr(api, lost, True)
                with Journal(path, data, run.digest(data)) as log:
                    with self.assertRaises(OSError):
                        run.batch.submit_all(log, api, lambda e: p, self.native, run.fingerprint, 1)
                with Journal(path, data, run.digest(data)) as log:
                    run.batch.submit_all(log, api, lambda e: p, self.native, run.fingerprint, 1)
                    run.batch.submit_all(log, api, lambda e: p, self.native, run.fingerprint, 1)
                    self.assertEqual(api.uploads, 1)
                    self.assertEqual(api.creates, 1)
                    self.assertEqual(api.counts, 1)
                    self.assertEqual(log.reserved_tokens(), 10)

    def test_foreign_publications_capacity_wait(self):
        """An outstanding foreign Batch prevents submission without assuming entitlement."""
        p, _ = self.fixture('github')
        mf = dict(generatorPins=self.pins, requests=[dict(identity=run.fingerprint(p),
            estimatedCostUSD=.1)], queuedTokenLimit=100, meaningfulSampleRequests=100)
        data = run.batch.canonical_json(mf) + b'\n'
        api = FakeAPI()
        api.foreign = True
        with run.journal_type(self.paired, self.native)(self.root / 'execution.jsonl', data, run.digest(data)) as log:
            self.assertEqual(run.batch.submit_all(log, api, lambda e: p, self.native, run.fingerprint, 1),
                             'waiting_foreign_batches')
        self.assertEqual(api.creates, 0)
        self.assertEqual(api.uploads, 0)

    def test_cli_compatibility_collection_association_and_no_redispatch(self):
        """Three genuine-shaped checks share production identity and reverse result order."""
        prepared = [self.fixture(family) for family in run.conformance.DIRECTORIES]
        payloads = {run.batch.input_line(p, 1, run.fingerprint)[0]['custom_id']: payload for p, payload in prepared}

        class API(FakeAPI):
            """Add family output fixtures to the common simulated Batch transport."""

            def retrieve(self, bid):
                """Preserve reversed exact custom IDs while supplying valid source responses."""
                result = super().retrieve(bid)
                fid = result.get('output_file_id')
                if fid:
                    rows = [json.loads(line) for line in self.contents[fid].splitlines()]
                    for row in rows:
                        row['response']['body']['output'] = [dict(type='message', content=[dict(
                            type='output_text', text=run.canonical(payloads[row['custom_id']]).decode())])]
                    self.contents[fid] = b''.join(run.canonical(row) + b'\n' for row in rows)
                return result

        api = API()
        folder = self.root / 'queue'
        folder.mkdir()
        entries = []
        for index, (p, _) in enumerate(prepared):
            wire = run.canonical(p) + b'\n'
            name = str(index) + '.json'
            (folder / name).write_bytes(wire)
            entries.append(dict(identity=run.fingerprint(p), family=p['semanticRequest']['request']['artifactFamily'],
                estimatedCostUSD=.1, bundleFile=name, bundleSha256=run.digest(wire), rawSourcePins={}))
        parent = dict(requests=entries, implementationPins={}, pricing=run.batch.PRICING, sizing=queue.SIZING)
        args = argparse.Namespace(check=True, submit_all=False, collect=False, queued_token_limit=100, count_workers=1)
        with patch.object(cli, 'BASE', self.root), patch.object(cli, 'load_queue', return_value=parent), \
             patch.object(run, 'infrastructure', return_value=(self.paired, self.native, self.pins)), \
             patch.object(run.batch.batch_transport, 'BatchAPI', return_value=api), \
             patch.object(run.batch.baseline.provider, 'load_openai_api_key', return_value='mock-only'):
            cli.operate(args)
            self.assertEqual(api.creates, 1)
            result = cli.operate(args)
            self.assertEqual(result['completed'], 3)
            args.check, args.submit_all = False, True
            cli.operate(args)
            self.assertEqual(api.creates, 1)
            self.assertEqual(api.uploads, 1)
            args.submit_all, args.collect = False, True
            cli.operate(args)
            self.assertEqual(api.creates, 1)
            status = json.loads((self.root / 'production/status.json').read_bytes())['summary']
            self.assertEqual(set(status['families']), set(run.conformance.DIRECTORIES))
            self.assertTrue(all(v['completed'] == 1 for v in status['families'].values()))

    def test_packaging_accounts_for_oversized_units_without_dropping_owner(self):
        """Intact native units either fit or receive individual explicit holds."""
        p, _ = self.fixture('github')
        inputs = run.unpack_inputs(p['requestInputs'])
        units = inputs['reader_result']['sourceUnits']
        owner = dict(family='github', ownerID='github:repo:7', units=units, inputs=inputs,
                     sourceRecordSha256='source-pin', endpointRecordSha256='endpoint-pin')
        with patch.dict(queue.SIZING, maxSelectedUnits=1):
            groups = list(queue.requests(owner))
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(p is not None for p, _ in groups))
        self.assertEqual([g['primarySourceUnitIDs'][0] for _, g in groups], [u['sourceUnitID'] for u in units])
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        reader = read_repository_sources(dict(repo_id=7, name='Demo', full_name='Example/Demo',
            archive={'frozen_commit_sha': 'a' * 40}, files={'downloaded': []},
            readme=dict(source_path='README.md', text='# Guide\n\nA short description.\n\nA much longer scientific tool description.\n')), self.root)
        units = reader['sourceUnits']
        owner['units'] = units
        owner['inputs']['reader_result'] = reader
        sizes = [len(u['text'].encode()) for u in units]
        with patch.dict(queue.SIZING, maxSelectedTextBytes=min(sizes)):
            groups = list(queue.requests(owner))
        self.assertEqual(sum(p is not None for p, _ in groups), 1)
        self.assertEqual(sum(p is None for p, _ in groups), 1)
        self.assertEqual([uid for _, g in groups for uid in g['primarySourceUnitIDs']],
                         [u['sourceUnitID'] for u in units])

    def test_large_ancestor_does_not_hold_independent_descendant(self):
        """Unsafe ancestor context is omitted explicitly rather than cascading owner holds."""
        units = [dict(sourceUnitID='parent', text='a' * 25000, headingOrdinal=1, contentKind='prose'),
                 dict(sourceUnitID='child', text='A documented action.', headingOrdinal=2, contentKind='prose')]
        owner = dict(family='ciroh_hub', units=units, inputs=dict(page=dict(headings=[
            dict(ordinal=1, parent_heading_ordinal=None), dict(ordinal=2, parent_heading_ordinal=1)])))
        self.assertEqual(queue.context(owner, units[1:]), units[1:])
        self.assertEqual(queue.ancestor_units(owner, units[1:]), units[:1])


if __name__ == '__main__':
    unittest.main()
