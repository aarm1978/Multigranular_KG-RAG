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
from src.extraction.llm import source_family_inputs as sources
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
        previous = dict(cli.implementation_pins())
        previous.pop(str(run.batch.OPERATIONAL_COMPATIBILITY.relative_to(cli.ROOT)))
        previous.update(json.loads(run.batch.OPERATIONAL_COMPATIBILITY.read_bytes())['sourceFamilyPreviousPins'])
        parent = dict(requests=entries, implementationPins=previous, pricing=run.batch.PRICING, sizing=queue.SIZING)
        (self.root / 'queue-manifest.json').write_bytes(run.canonical(parent) + b'\n')
        production = self.root / 'production'
        production.mkdir()
        original_manifest = run.canonical(cli.manifest(parent, self.pins, 100)) + b'\n'
        (production / 'run-manifest.json').write_bytes(original_manifest)
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
            self.assertEqual((production / 'run-manifest.json').read_bytes(), original_manifest)
            bridge = json.loads((self.root / 'operational-compatibility-v1.json').read_bytes())
            self.assertEqual(bridge['previousImplementationPins'], previous)


class OperationalCompatibilityTests(unittest.TestCase):
    """A finite exact pin bridge preserves previously sealed source-family queues."""

    def test_exact_bridge_and_fail_closed_scientific_pins(self):
        """Only the reviewed operational hashes migrate; unknown drift remains fatal."""
        authority = json.loads(run.batch.OPERATIONAL_COMPATIBILITY.read_bytes())
        current = cli.implementation_pins()
        previous = dict(current)
        previous.pop(str(run.batch.OPERATIONAL_COMPATIBILITY.relative_to(cli.ROOT)))
        previous.update(authority['sourceFamilyPreviousPins'])
        report = cli.operational_compatibility(previous, current)
        self.assertEqual(report['previousImplementationPins'], previous)
        self.assertEqual(report['implementationPins'], current)
        for path in ('src/extraction/llm/source_family_inputs.py', 'src/extraction/llm/format_conformance.py',
                     'src/extraction/llm/publications/full_corpus_gpt61_batch.py'):
            changed = dict(current)
            changed[path] = 'f' * 64
            with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_DRIFT'):
                cli.operational_compatibility(previous, changed)
        self.assertIsNone(cli.operational_compatibility(current, current))

    def test_previously_sealed_queue_remains_byte_identical(self):
        """Exercise the accessible queue read-only; no regeneration, sidecar or runtime writes."""
        path = cli.BASE / 'queue-manifest.json'
        if not path.exists():
            self.skipTest('Ignored source-family queue unavailable; synthetic bridge test still applies')
        before = path.read_bytes()
        with cli.offline():
            saved = cli.load_queue()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(saved, json.loads(before))


class ReadmeAuthorityTests(unittest.TestCase):
    """Synthetic exact-binding checks; never read corpus data or contact providers."""

    def setUp(self):
        """Create three frozen-shaped attestations and prohibit network access."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.rows = []
        self.provenance = dict(snapshotID='sha256:' + 'a' * 64, sourceVersion='frozen-version')
        for rid in ('HS-03', 'HS-04', 'HS-07'):
            unit = dict(resource_id=rid, source_path='README.md', sourceField='README',
                sourceUnitID=rid + ':original', authorityTextSha256=run.digest((rid + ' original text').encode()),
                sourceVerification='caller_attested', acquisitionIntegrityStatus='not_independently_verified',
                **self.provenance)
            self.rows.append(dict(requestID=rid, artifactFamily='hydroshare', owner=dict(resource_id=rid),
                sourceSnapshot=dict(sha256='a' * 64), orderedUnits=[unit]))
        wire = run.canonical(dict(requests=self.rows))
        target = self.root / sources.MANIFEST_PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(wire)
        pin = patch.object(sources, 'MANIFEST_SHA256', run.digest(wire))
        pin.start()
        self.addCleanup(pin.stop)
        self.bindings = sources.accepted_readme_bindings(self.root)

    def test_all_three_exact_bindings_preserve_caller_attestation(self):
        """Every accepted identity is usable without upgrading acquisition provenance."""
        for row in self.rows:
            rid = row['requestID']
            reader = sources.production_readme(dict(source_file='README.md', readme_text_raw=rid + ' original text'),
                                               rid, self.provenance, self.bindings)
            self.assertTrue(reader['inputComplete'])
            self.assertEqual(len(reader['sourceUnits']), 1)
            self.assertEqual(reader['authority']['sourceVerification'], 'caller_attested')
            self.assertEqual(reader['authority']['acquisitionIntegrityStatus'], 'not_independently_verified')
            self.assertEqual(reader['authority']['integrityStatus'], 'computed_only')
            self.assertIsNone(reader['authority']['expectedAuthorityTextSha256'])
            self.assertEqual(reader['productionAuthority']['acceptedBinding']['originalSourceUnitID'], rid + ':original')

    def test_unverified_identity_hash_snapshot_and_version_fail_closed(self):
        """A matching name, local text or different owner's attestation is insufficient."""
        for owner, path, text, provenance in (
                ('unverified', 'README.md', 'HS-03 original text', self.provenance),
                ('HS-03', 'other.md', 'HS-03 original text', self.provenance),
                ('HS-03', 'README.md', 'changed text', self.provenance),
                ('HS-03', 'README.md', 'HS-03 original text', {**self.provenance, 'snapshotID': 'different'}),
                ('HS-03', 'README.md', 'HS-03 original text', {**self.provenance, 'sourceVersion': 'different'})):
            with self.subTest(owner=owner, path=path, text=text, provenance=provenance):
                result = sources.production_readme(dict(source_file=path, readme_text_raw=text),
                                                   owner, provenance, self.bindings)
                self.assertEqual(result['sourceUnits'], [])
                self.assertFalse(result['inputComplete'])
                self.assertEqual(result['diagnostics'][0]['reason'], 'readme_source_not_verified')
                self.assertEqual(result['diagnostics'][0]['source_path'], path)
                self.assertEqual(result['diagnostics'][0]['status'], 'failed_source_or_evidence_binding')

    def test_manifest_drift_is_not_new_authority(self):
        """An edited attestation manifest cannot extend the production allowlist."""
        (self.root / sources.MANIFEST_PATH).write_text('{}')
        with self.assertRaisesRegex(Exception, 'README_BINDING_MANIFEST_DRIFT'):
            sources.accepted_readme_bindings(self.root)

    def test_unverified_readme_keeps_abstract_request_incomplete(self):
        """Source failures survive through owner accounting and the native request builder."""
        source = dict(resource_id='unverified', abstract='Verified frozen abstract.',
            system_metadata=dict(date_last_updated='frozen-version'),
            documentation=dict(readme_files=[dict(source_file='README.md', readme_text_raw='Unverified text.')]))
        data = dict(hydroshare=dict(records=[source], sourceSha256='a' * 64,
            graph=dict(nodes=[dict(id='unverified', **{'class': 'DatasetResource'})], edges=[])))
        original = deepcopy(data)
        with patch.object(sources, 'catalog', return_value=([], [])):
            owner = next(sources.owners(self.root, data))
        self.assertEqual(data, original)
        self.assertFalse(owner['inputComplete'])
        self.assertEqual([u['sourceField'] for u in owner['units']], ['abstract'])
        groups = list(queue.requests(owner))
        self.assertEqual(len(groups), 1)
        prepared = groups[0][0]
        self.assertIsNotNone(prepared)
        request = prepared['semanticRequest']['request']
        self.assertFalse(request['sourceCompleteness']['inputComplete'])
        self.assertEqual(request['sourceDiagnostics'][0]['authorityDecision'], 'no_accepted_readme_binding')
        self.assertNotIn('Unverified text.', prepared['body']['input'])
        run.verify_prepared(prepared, {'identity': run.fingerprint(prepared)})


class PackagingTests(unittest.TestCase):
    """Focused source-context correction tests with all sockets blocked."""

    def setUp(self):
        """Prevent genuine provider operations in every packaging test."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)

    def owner(self, family, units, headings=None, authorities=None):
        """Create minimal trusted structural context for deterministic packaging tests."""
        return dict(family=family, ownerID='owner', units=units,
            sourceRecordSha256='source-pin', endpointRecordSha256='endpoint-pin',
            inputs=dict(page=dict(headings=headings or []),
                        reader_result=dict(authorities=authorities or [])))

    def package(self, owner):
        """Stub only native construction; expose exact selected original units as the envelope."""
        from types import SimpleNamespace
        def build(**inputs):
            """Mirror the native success boundary without judging source evidence."""
            return dict(status='request_ready', selected=inputs['selected_unit_ids'])
        def prepare(request, inputs):
            """Retain selected original records so input/output size guards are exercised."""
            return dict(body=dict(units=[u for u in owner['units'] if u['sourceUnitID'] in request['selected']]))
        with patch.object(queue.importlib, 'import_module', return_value=SimpleNamespace(build_request=build)), \
             patch.object(queue.adapter, 'prepare', side_effect=prepare):
            return list(queue.requests(owner))

    def test_resource_combines_abstract_and_readmes(self):
        """HydroShare preserves its resource-wide context regardless of field boundaries."""
        units = [dict(sourceUnitID='abstract', text='Abstract description.', sourceField='abstract'),
                 dict(sourceUnitID='readme', text='Verified README description.', sourceField='README')]
        owner = self.owner('hydroshare', units)
        groups = self.package(owner)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][1]['selectedSourceUnitIDs'], ['abstract', 'readme'])
        with patch.dict(queue.SIZING, maxSelectedTextBytes=10):
            held = self.package(owner)
        self.assertEqual(len(held), 1)
        self.assertIsNone(held[0][0])
        self.assertEqual(held[0][1]['primarySourceUnitIDs'], ['abstract', 'readme'])

    def test_confirmed_license_exclusion_preserves_reader_and_document_context(self):
        """The prospective overlay excludes exact legal authorities without editing readers."""
        units = [dict(sourceUnitID=str(n), text='Original authority text.', path=path,
                      cellIndex=None, startOffsetInAuthority=0)
                 for n, path in enumerate(('README.md', 'ODbl.md', 'docs/guide.md'))]
        reader = dict(sourceUnits=units, authorities=[dict(path=u['path'], cellIndex=None,
            text=u['text'], rawFileSha256='dddcdfa70ce72d0e964160d2f16ddb22501256089dbf9c775e3eced0d031e658')
            for u in units])
        original = deepcopy(reader)
        for owner_id in ('github:repo:1052799392', 'github:repo:706266756', 'github:repo:1052790271'):
            exclusions = sources.github_production_exclusions(owner_id, reader)
            self.assertEqual(exclusions[0]['status'], 'not_attempted_authorized_exclusion')
            self.assertEqual(exclusions[0]['sourceUnitIDs'], ['1'])
            owner = self.owner('github', units, authorities=reader['authorities'])
            owner['excludedSourceUnitIDs'] = exclusions[0]['sourceUnitIDs']
            groups = self.package(owner)
            self.assertEqual([g['documentPath'] for _, g in groups], ['README.md', 'docs/guide.md'])
            self.assertFalse(any(g['exceptionalSplit'] for _, g in groups))
        self.assertEqual(reader, original)
        self.assertEqual(sources.github_production_exclusions('github:repo:other', reader), [])
        reader['authorities'][1]['rawFileSha256'] = 'changed'
        with self.assertRaisesRegex(Exception, 'INSPECTED_ODBL_AUTHORITY_DRIFT'):
            sources.github_production_exclusions('github:repo:706266756', reader)

    def test_small_github_documents_are_never_combined_by_repository(self):
        """Separate autonomous files stay separate even when the whole repository fits."""
        units = [dict(sourceUnitID=str(n), text='Descriptive text.', path=path,
                      cellIndex=None, startOffsetInAuthority=0)
                 for n, path in enumerate(('README.md', 'docs/guide.md'))]
        owner = self.owner('github', units, authorities=[dict(path=u['path'], cellIndex=None,
                           text=u['text']) for u in units])
        original = deepcopy(owner)
        groups = self.package(owner)
        self.assertEqual([g['documentPath'] for _, g in groups], ['README.md', 'docs/guide.md'])
        self.assertEqual([g['selectedSourceUnitIDs'] for _, g in groups], [['0'], ['1']])
        self.assertFalse(any(g['exceptionalSplit'] for _, g in groups))
        self.assertEqual(owner, original)
        self.assertEqual(groups, self.package(owner))

    def test_notebook_cells_stay_together_by_default(self):
        """Autonomous notebook context includes every admitted Markdown cell."""
        units = [dict(sourceUnitID=str(n), text='Markdown prose.', path='guide.ipynb',
                      cellIndex=n, startOffsetInAuthority=0) for n in range(3)]
        owner = self.owner('github', units, authorities=[dict(path='guide.ipynb', cellIndex=n,
                           text='Markdown prose.') for n in range(3)])
        groups = self.package(owner)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][1]['selectedSourceUnitIDs'], ['0', '1', '2'])

    def test_large_unit_count_pages_and_both_resources_pages_remain_whole(self):
        """217 intact units and 50KB of content are manageable, including Example context."""
        units = [dict(sourceUnitID=str(n), text='Descriptive content. ' * 12, headingOrdinal=1,
                      contentKind='fenced_snippet' if n == 0 else 'static_visible_context',
                      eligibility='possible_example_context' if n == 0 else 'static_visible_context') for n in range(217)]
        for path in ('src/pages/resources/RESOURCES_PAGE_DOCUMENTATION.mdx',
                     'src/pages/community_products/RESOURCES_PAGE_DOCUMENTATION.mdx'):
            owner = self.owner('ciroh_hub', units, headings=[dict(ordinal=1, parent_heading_ordinal=None)])
            owner['inputs']['page']['source_path'] = path
            original = deepcopy(owner)
            groups = self.package(owner)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0][0]['body']['units'], units)
            self.assertFalse(groups[0][1]['exceptionalSplit'])
            self.assertEqual(owner, original)

    def test_exceptional_page_split_retains_complete_procedure_ancestor(self):
        """Split only an oversized tree and repeat original parent/Example context unchanged."""
        units = [dict(sourceUnitID='parent', text='p' * 10, headingOrdinal=1, contentKind='fenced_snippet'),
                 dict(sourceUnitID='step1', text='a' * 30, headingOrdinal=2),
                 dict(sourceUnitID='step2', text='b' * 30, headingOrdinal=3)]
        owner = self.owner('ciroh_hub', units, headings=[dict(ordinal=1, parent_heading_ordinal=None),
            dict(ordinal=2, parent_heading_ordinal=1), dict(ordinal=3, parent_heading_ordinal=1)])
        with patch.dict(queue.SIZING, maxSelectedTextBytes=50):
            groups = self.package(owner)
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(g['exceptionalSplit'] for _, g in groups))
        self.assertEqual([uid for _, g in groups for uid in g['primarySourceUnitIDs']], ['parent', 'step1', 'step2'])
        self.assertEqual(groups[1][1]['selectedSourceUnitIDs'], ['parent', 'step2'])
        self.assertEqual(groups[1][1]['repeatedContextUnitIDs'], ['parent'])
        self.assertTrue(all(g['omittedAncestorContextUnitIDs'] == [] for _, g in groups))
        self.assertEqual(groups[1][0]['body']['units'][0], units[0])

    def test_unsafe_ancestor_is_held_explicitly_never_silently_trimmed(self):
        """An indivisible oversized parent is reported; descendants never lose its context."""
        units = [dict(sourceUnitID='parent', text='p' * 60, headingOrdinal=1),
                 dict(sourceUnitID='child', text='c' * 10, headingOrdinal=2)]
        owner = self.owner('ciroh_hub', units, headings=[dict(ordinal=1, parent_heading_ordinal=None),
            dict(ordinal=2, parent_heading_ordinal=1)])
        with patch.dict(queue.SIZING, maxSelectedTextBytes=50):
            groups = self.package(owner)
        self.assertTrue(all(p is None for p, _ in groups))
        self.assertTrue(all(g['omittedAncestorContextUnitIDs'] == [] for _, g in groups))
        self.assertEqual(groups[-1][1]['selectedSourceUnitIDs'], ['parent', 'child'])
        self.assertIn('required_context', groups[-1][1]['holdReason'])

    def test_exceptional_document_split_uses_heading_subtrees_and_envelope_guard(self):
        """Full-envelope pressure can split coherent sections, retaining parent prose."""
        text = '# Guide\nintro\n## First\n' + 'a' * 30 + '\n## Second\n' + 'b' * 30 + '\n'
        units = [dict(sourceUnitID=key, text=value, path='README.md', cellIndex=None,
                      startOffsetInAuthority=text.index(value))
                 for key, value in (('intro', 'intro'), ('first', 'a' * 30), ('second', 'b' * 30))]
        owner = self.owner('github', units, authorities=[dict(path='README.md', cellIndex=None, text=text)])
        # Both sections fit the output margin, but together exceed this envelope margin.
        two_size = len(run.canonical(dict(units=units[:2])))
        with patch.dict(queue.SIZING, maxEnvelopeBytes=two_size + 5):
            groups = self.package(owner)
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(p is not None for p, _ in groups))
        self.assertEqual(groups[1][1]['selectedSourceUnitIDs'], ['intro', 'second'])
        self.assertTrue(all(g['splitReason'] == 'complete_envelope_exceeds_input_safety_margin' for _, g in groups))

    def test_native_builder_preserves_complete_document_and_hashes(self):
        """The real accepted request builder receives the full verified document."""
        from test_coderepos_semantic_offline_pipeline import OfflineReplayTests
        fixture = OfflineReplayTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        inputs = deepcopy(fixture.inputs)
        inputs['request_version'] = 'github-request/1.2.0'
        units = inputs['reader_result']['sourceUnits']
        owner = self.owner('github', units)
        owner['inputs'] = inputs
        groups = list(queue.requests(owner))
        self.assertEqual(len(groups), 1)
        prepared, coverage = groups[0]
        self.assertEqual(prepared['semanticRequest']['request']['sourceUnits'], units)
        self.assertEqual(coverage['selectedSourceUnitIDs'], [u['sourceUnitID'] for u in units])
        run.verify_prepared(prepared, {'identity': run.fingerprint(prepared)})


if __name__ == '__main__':
    unittest.main()
