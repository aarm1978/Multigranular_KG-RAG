"""Focused Step 13.1 synthetic T1/T2 tests; no provider or graph IO."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import importlib
import json
import unittest
from unittest.mock import patch

from src.extraction.llm import construction_acceptance as acceptance
from src.extraction.llm.pilot_preflight import canonical, digest


class ConstructionAcceptanceTests(unittest.TestCase):
    """Exercise acceptance downstream of the unchanged family replay pipelines."""

    def fixture(self, family):
        """Reuse synthetic sources without running their original test cases."""
        directory = acceptance.DIRECTORIES[family]
        module = importlib.import_module('test_' + directory + '_semantic_offline_pipeline')
        fixture = module.OfflineReplayTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def run_case(self, family, fixture, payload=None, inputs=None, pin=True, raw=None, **kwargs):
        """Run a caller-pinned in-memory request and prohibit network access."""
        inputs = fixture.inputs if inputs is None else inputs
        contract = importlib.import_module('src.extraction.llm.' + acceptance.DIRECTORIES[family] + '.request_contract')
        request = contract.build_request(**inputs)
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            return acceptance.replay_and_project(
                raw if raw is not None else canonical(fixture.payload() if payload is None else payload),
                family=family, request_inputs=inputs,
                expected_request_sha256=request.get('requestSha256') if pin else None, **kwargs)

    def decisions(self, report):
        """Index detached construction decisions."""
        return {r['candidateID']: r for r in report.to_record()['decisions']}

    def pair(self, fixture, node_id, node_class, edge_id, relation):
        """Retarget the synthetic independently evidenced pair."""
        payload = fixture.payload()
        payload['candidateNodes'][0].update(inventoryId=node_id, **{'class': node_class})
        payload['candidateEdges'][0].update(inventoryId=edge_id, relation=relation)
        return payload

    def hub_path(self, fixture):
        """Create a complete page/Procedure/Step/Example path with attachment cycles."""
        payload = self.pair(fixture, 'A-DC05', 'Procedure', 'C-DC20', 'hasProcedure')
        for cid, cls, nid, eid, rel, parent, path in (
            ('step', 'Step', 'A-DC06', 'C-DC10', 'hasStep', 'tool', ['edge', 'step-edge']),
            ('example', 'Example', 'A-DC08', 'C-DC12', 'hasExample', 'step', ['edge', 'step-edge', 'example-edge']),
            ('parameter', 'Parameter', 'A-DOM12', 'C-DC11', 'hasParameter', 'step', ['edge', 'step-edge', 'parameter-edge'])):
            node = deepcopy(payload['candidateNodes'][0])
            node.update(candidateID=cid, inventoryId=nid, **{'class': cls},
                        parentPath=[{'referenceType': 'candidate_edge', 'referenceID': p} for p in path])
            edge = deepcopy(payload['candidateEdges'][0])
            edge.update(candidateID=cid+'-edge', inventoryId=eid, relation=rel,
                        source={'referenceType': 'candidate_node', 'referenceID': parent},
                        target={'referenceType': 'candidate_node', 'referenceID': cid})
            payload['candidateNodes'].append(node)
            payload['candidateEdges'].append(edge)
        return payload

    def test_ordinary_and_immutable_hashes_all_families(self):
        """All three ordinary paths preserve exact replay provenance and hashes."""
        for family in acceptance.DIRECTORIES:
            with self.subTest(family=family):
                f = self.fixture(family)
                before = deepcopy(f.inputs)
                result = self.run_case(family, f)
                record = result.to_record()
                self.assertEqual([d['disposition'] for d in record['decisions']], ['accepted'] * 2)
                self.assertEqual(result, self.run_case(family, f))
                self.assertEqual(result.report_sha256, digest(result.report_json.encode()))
                self.assertEqual(record['projectionSha256'], digest(canonical(record['projection'])))
                self.assertEqual(before, f.inputs)
                record['projection']['nodes'].clear()
                self.assertEqual(len(result.to_record()['projection']['nodes']), 1)
                with self.assertRaises(FrozenInstanceError):
                    result.report_json = '{}'
                self.assertFalse(result.to_record()['kgAuthorization'])

    def test_request_association_and_processing_failures(self):
        """Computed request hashes alone cannot authorize construction."""
        for family in acceptance.DIRECTORIES:
            f = self.fixture(family)
            for kwargs in ({'pin': False}, {'raw': b'{'}, {'raw': b'\xff'}):
                result = self.run_case(family, f, **kwargs).to_record()
                self.assertEqual(result['status'], 'processing_blocked')
                self.assertFalse(result['projection']['nodes'] or result['projection']['edges'])

    def test_github_function_and_algorithm_conditions(self):
        """Interpretive prose gates release independently evidenced nodes and edges."""
        f = self.fixture('github')
        for values in (('A-C08', 'Function', 'C-C08', 'providesFunction'),
                       ('A-DOM13', 'Algorithm', 'C-C20', 'implementsAlgorithm')):
            payload = self.pair(f, *values)
            # Use the frozen declaration rather than an assumed predicate name.
            from src.extraction.llm.semantic_target_profiles import get_profile
            payload['candidateEdges'][0]['relation'] = get_profile('github')['relations'][values[2]]['declaration']['name']
            result = self.run_case('github', f, payload)
            self.assertEqual([d['disposition'] for d in self.decisions(result).values()], ['accepted'] * 2)
            self.assertTrue(all(d['acceptanceBasis'] == 'policy_conditional_inclusion' for d in self.decisions(result).values()))

    def test_measurement_requires_verified_readme(self):
        """Only verified README evidence releases Measurement and its edge."""
        f = self.fixture('hydroshare')
        from src.extraction.llm.semantic_target_profiles import get_profile
        relation = get_profile('hydroshare')['relations']['C-D17']['declaration']['name']
        payload = self.pair(f, 'A-D12', 'Measurement', 'C-D17', relation)
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(self.run_case('hydroshare', f, payload)).values()))
        inputs = deepcopy(f.inputs)
        inputs['selected_unit_ids'] = [f.other_uid]
        for row in payload['candidateNodes'] + payload['candidateEdges']:
            row['evidence'] = [{'sourceUnitID': f.other_uid, 'evidenceText': f.other_quote}]
        result = self.run_case('hydroshare', f, payload, inputs)
        self.assertTrue(all(d['disposition'] == 'accepted' for d in self.decisions(result).values()))
        inputs['readme_results'][0]['authority']['sourceVerification'] = 'unverified'
        self.assertFalse(self.run_case('hydroshare', f, payload, inputs).to_record()['projection']['nodes'])

    def test_hub_local_method_and_github_boundary(self):
        """Hub Method has no Publication prerequisite; GitHub remains Step 14."""
        f = self.fixture('ciroh_hub')
        payload = self.pair(f, 'A-P13', 'Method', 'C-DC28', 'describesMethod')
        self.assertTrue(all(d['disposition'] == 'accepted' for d in self.decisions(self.run_case('ciroh_hub', f, payload)).values()))
        f = self.fixture('github')
        payload = self.pair(f, 'A-P13', 'Method', 'C-C16', 'implementsMethod')
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(self.run_case('github', f, payload)).values()))
        inputs = deepcopy(f.inputs)
        inputs['accepted_endpoints'] = [{'endpointID': 'publication-method', 'inventoryId': 'A-P13', 'class': 'Method'}]
        payload['candidateNodes'][0]['endpoint'] = {'referenceType': 'accepted_endpoint', 'referenceID': 'publication-method'}
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(self.run_case('github', f, payload, inputs)).values()))

    def test_six_purpose_seeds_and_classification(self):
        """Every frozen purpose seed works; ambiguous/missing classification does not."""
        from src.extraction.llm.coderepos.purpose_validation import purpose_vocabulary
        f = self.fixture('github')
        for seed in purpose_vocabulary():
            payload = f.payload()
            payload['candidateNodes'] = []
            payload['candidateEdges'][0].update(inventoryId='C-C07', relation='hasPurpose', classification='proposed',
                categoryKey=seed['categoryKey'], target={'referenceType': 'accepted_endpoint', 'referenceID': seed['nodeID']})
            result = self.run_case('github', f, payload)
            self.assertEqual(self.decisions(result)['edge']['disposition'], 'accepted')
        del payload['candidateEdges'][0]['classification']
        self.assertEqual(self.decisions(self.run_case('github', f, payload))['edge']['disposition'], 'held')
        payload['candidateEdges'][0].update(classification='ambiguous', categoryKey=None, target=None, reason='ambiguous')
        self.assertEqual(self.decisions(self.run_case('github', f, payload))['edge']['disposition'], 'held')

    def test_hub_dependency_closure_and_order(self):
        """Verified attachment cycles survive in any candidate order."""
        f = self.fixture('ciroh_hub')
        payload = self.hub_path(f)
        result = self.run_case('ciroh_hub', f, payload)
        self.assertTrue(all(d['disposition'] == 'accepted' for d in self.decisions(result).values()), self.decisions(result))
        payload['candidateNodes'].reverse()
        payload['candidateEdges'].reverse()
        other = self.run_case('ciroh_hub', f, payload)
        self.assertEqual(self.decisions(result), self.decisions(other))
        for record in other.to_record()['projection']['edges']:
            endpoints = {n['resolvedEndpoint']['endpointID'] for n in other.to_record()['projection']['nodes']}
            endpoints.add(f.owner)
            self.assertIn(record['resolvedSource']['endpointID'], endpoints)
            self.assertIn(record['resolvedTarget']['endpointID'], endpoints)

    def test_hub_hard_failure_closure_and_parent_path(self):
        """Evidence or ordered-path defects block every affected attachment."""
        f = self.fixture('ciroh_hub')
        for defect in ('evidence', 'path', 'parse'):
            payload = self.hub_path(f)
            if defect == 'evidence':
                payload['candidateEdges'][0]['evidence'][0]['evidenceText'] = 'absent'
            elif defect == 'path':
                payload['candidateNodes'][1]['parentPath'].reverse()
            else:
                payload['candidateEdges'][0]['unknownField'] = True
            decisions = self.decisions(self.run_case('ciroh_hub', f, payload))
            self.assertEqual(decisions['tool']['disposition'], 'accepted')
            self.assertTrue(all(decisions[c]['disposition'] == 'held' for c in ('step', 'step-edge', 'example', 'example-edge', 'parameter')))

    def test_all_findings_not_only_final_disposition(self):
        """Even a validated disposition cannot conceal another original hard reason."""
        f = self.fixture('ciroh_hub')
        base = self.run_case('ciroh_hub', f).to_record()['originalReplay']
        pipeline = importlib.import_module('src.extraction.llm.documents.offline_pipeline')
        for field in ('findings', 'parseDiagnostics', 'replayDiagnostics', 'pendingGates', 'binding'):
            report = deepcopy(base)
            row = report['finalRecords'][0]
            c = row['validationRecord']
            if field == 'findings':
                c['findings'].append({'reason': 'source_integrity_failure', 'disposition': 'failed_source_or_evidence_binding'})
            elif field == 'pendingGates':
                c['targetProfileCheck']['pendingGates'].append('unknown_gate')
            elif field == 'binding':
                c['evidenceBindings'][0]['binding']['status'] = 'needs_review'
            else:
                row[field].append({'reason': 'hard_original_failure'})
            wire = canonical(report)
            result = acceptance.project_replay(pipeline.ReplayReport(wire.decode(), digest(wire), None))
            self.assertFalse(result.to_record()['projection']['nodes'] or result.to_record()['projection']['edges'])

    def test_mixed_conditional_evidence_failure(self):
        """Releasable Method gates cannot mask a simultaneous invalid quotation."""
        f = self.fixture('ciroh_hub')
        payload = self.pair(f, 'A-P13', 'Method', 'C-DC28', 'describesMethod')
        payload['candidateNodes'][0]['evidence'][0]['evidenceText'] = 'missing'
        result = self.run_case('ciroh_hub', f, payload)
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(result).values()))

    def test_model_version_endpoint_duplicates_are_not_identity_proof(self):
        """Same-owner endpoint/assertion references remain held without identity proof."""
        f = self.fixture('github')
        payload = self.pair(f, 'A-C10', 'ModelVersion', 'C-C09', 'hasModelVersion')
        payload['candidateNodes'][0].update(productRepositoryID=f.owner, label='1.0')
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(self.run_case('github', f, payload)).values()))
        inputs = deepcopy(f.inputs)
        inputs['accepted_endpoints'] = [{'endpointID': 'version-1', 'inventoryId': 'A-C10', 'class': 'ModelVersion',
                                         'productRepositoryID': f.owner}]
        inputs['accepted_assertions'] = [{'assertionID': 'version-edge', 'inventoryId': 'C-C09', 'relation': 'hasModelVersion',
                                         'sourceID': f.owner, 'targetID': 'version-1'}]
        payload['candidateNodes'][0]['endpoint'] = {'referenceType': 'accepted_endpoint', 'referenceID': 'version-1'}
        result = self.run_case('github', f, payload, inputs)
        self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(result).values()), self.decisions(result))
        self.assertEqual(self.decisions(result)['tool']['duplicateOf'], ['version-1'])
        self.assertEqual(self.decisions(result)['edge']['duplicateOf'], [])
        self.assertTrue(all('candidate_version_product_identity_not_established' in d['blockingReasons']
                            for d in self.decisions(result).values()))
        self.assertFalse(result.to_record()['projection']['nodes'] or result.to_record()['projection']['edges'])
        self.assertTrue(result.to_record()['originalReplay']['finalRecords'][0]['validationRecord']['boundEvidence'])
        inputs['accepted_endpoints'][0]['productRepositoryID'] = 'github:repo:8'
        self.assertFalse(self.run_case('github', f, payload, inputs).to_record()['projection']['edges'])

    def test_duplicate_evidence_and_external_endpoint_no_orphan(self):
        """Suppressed exact nodes may support edges to their trusted endpoint."""
        f = self.fixture('ciroh_hub')
        payload = f.payload()
        inputs = deepcopy(f.inputs)
        inputs['accepted_endpoints'] = [{'endpointID': 'trusted-tool', 'inventoryId': 'A-DOM02', 'class': 'Tool'}]
        payload['candidateNodes'][0]['endpoint'] = {'referenceType': 'accepted_endpoint', 'referenceID': 'trusted-tool'}
        result = self.run_case('ciroh_hub', f, payload, inputs).to_record()
        self.assertFalse(result['projection']['nodes'])
        self.assertEqual(len(result['projection']['edges']), 1)
        self.assertIn('trusted-tool', {e['endpointID'] for e in result['projection']['externalEndpoints']})

    def test_source_failures_and_unaffected_units(self):
        """Scope source failures using unchanged readers and binders."""
        for family in ('github', 'ciroh_hub'):
            f = self.fixture(family)
            inputs = deepcopy(f.inputs)
            inputs['reader_result']['diagnostics'].append({'status': 'failed_source_or_evidence_binding',
                'sourceUnitID': f.other_uid, 'reason': 'downloaded_file_missing'})
            result = self.run_case(family, f, inputs=inputs).to_record()
            self.assertEqual(len(result['projection']['nodes']), 1)
            self.assertTrue(result['originalReplay']['sourceDiagnostics'])
            inputs['reader_result']['diagnostics'][-1]['sourceUnitID'] = f.uid
            result = self.run_case(family, f, inputs=inputs).to_record()
            self.assertFalse(result['projection']['nodes'] or result['projection']['edges'])

    def test_opt_in_conformance_and_legacy_compatibility(self):
        """Only the explicit prospective path conforms; raw replay stays immutable."""
        for family in acceptance.DIRECTORIES:
            f = self.fixture(family)
            payload = f.payload()
            payload['candidateNodes'][0]['class'] = 'ciroh:Tool'
            old = self.run_case(family, f, payload)
            self.assertFalse(old.to_record()['projection']['nodes'])
            result = self.run_case(family, f, payload, conformance_version=acceptance.VERSION,
                                   schema_version=acceptance.SCHEMA_VERSION).to_record()
            self.assertEqual(len(result['projection']['nodes']), 1)
            self.assertEqual(result['originalReplay'], old.to_record()['originalReplay'])
            self.assertEqual(result['projection']['replaySha256'], result['conformance']['derivedReplaySha256'])
            self.assertEqual(result['prospectiveSchema']['authorization'], 'NOT AUTHORIZED')
            self.assertEqual(old, self.run_case(family, f, payload))
            self.assertNotEqual(result['conformance']['originalResponseSha256'], result['conformance']['derivedResponseSha256'])

    def test_conditional_duplicates_remain_single_assertion(self):
        """Exact released edges are deduplicated even when upstream held both."""
        f = self.fixture('hydroshare')
        from src.extraction.llm.semantic_target_profiles import get_profile
        relation = get_profile('hydroshare')['relations']['C-D17']['declaration']['name']
        payload = self.pair(f, 'A-D12', 'Measurement', 'C-D17', relation)
        inputs = deepcopy(f.inputs)
        inputs['selected_unit_ids'] = [f.other_uid]
        for row in payload['candidateNodes'] + payload['candidateEdges']:
            row['evidence'] = [{'sourceUnitID': f.other_uid, 'evidenceText': f.other_quote}]
        duplicate = deepcopy(payload['candidateEdges'][0])
        duplicate['candidateID'] = 'second-edge'
        payload['candidateEdges'].append(duplicate)
        result = self.run_case('hydroshare', f, payload, inputs)
        self.assertEqual(len(result.to_record()['projection']['edges']), 1)
        self.assertEqual(self.decisions(result)['second-edge']['disposition'], 'suppressed_duplicate')
        payload['candidateEdges'].reverse()
        self.assertEqual(self.decisions(result), self.decisions(self.run_case('hydroshare', f, payload, inputs)))

    def test_independent_edge_evidence_and_unknown_endpoint(self):
        """A healthy node never supplies missing edge evidence or invented endpoints."""
        for family in acceptance.DIRECTORIES:
            f = self.fixture(family)
            for defect in ('quote', 'endpoint', 'direction'):
                payload = f.payload()
                edge = payload['candidateEdges'][0]
                if defect == 'quote':
                    edge['evidence'][0]['evidenceText'] = 'unbound'
                elif defect == 'endpoint':
                    edge['target']['referenceID'] = 'missing'
                else:
                    edge['source'], edge['target'] = edge['target'], edge['source']
                result = self.run_case(family, f, payload).to_record()['projection']
                self.assertEqual(len(result['nodes']), 1)
                self.assertFalse(result['edges'])

    def test_model_version_labels_never_prove_exact_identity(self):
        """Matching labels and same-owner inventories do not establish absence."""
        f = self.fixture('github')
        payload = self.pair(f, 'A-C10', 'ModelVersion', 'C-C09', 'hasModelVersion')
        inputs = deepcopy(f.inputs)
        inputs['accepted_endpoints'] = [{'endpointID': 'existing-version', 'inventoryId': 'A-C10',
            'class': 'ModelVersion', 'productRepositoryID': f.owner}]
        for label in ('1.0', 'v1.0', 'version 1.0'):
            payload['candidateNodes'][0].update(label=label, productRepositoryID=f.owner)
            result = self.run_case('github', f, payload, inputs)
            self.assertTrue(all(d['disposition'] == 'held' for d in self.decisions(result).values()))
            self.assertIn('exact_deterministic_version_comparison_unavailable', self.decisions(result)['tool']['blockingReasons'])

    def test_mismatched_association_empty_and_io_boundaries(self):
        """Empty projections are not absence claims; hashes cannot fix a wrong pin."""
        import io
        f = self.fixture('hydroshare')
        result = acceptance.replay_and_project(canonical(f.payload()), family='hydroshare',
            request_inputs=f.inputs, expected_request_sha256='0' * 64).to_record()
        self.assertEqual(result['status'], 'processing_blocked')
        original_open = io.open

        def read_only(file, mode='r', *args, **kwargs):
            """Forbid filesystem writes during the offline acceptance operation."""
            self.assertFalse(any(flag in mode for flag in ('w', 'a', '+', 'x')))
            return original_open(file, mode, *args, **kwargs)

        payload = f.payload()
        payload.update(candidateNodes=[], candidateEdges=[])
        with patch('io.open', side_effect=read_only):
            result = self.run_case('hydroshare', f, payload).to_record()
        self.assertEqual(result['status'], 'projection_completed')
        self.assertFalse(result['projection']['nodes'] or result['projection']['edges'])
        self.assertFalse(result['kgAuthorization'])
        self.assertNotIn('providerID', result['projection'])

    def test_quarantined_malformed_rows_are_preserved(self):
        """Parser-rejected arbitrary fields never crash projection or regain entry."""
        f = self.fixture('ciroh_hub')
        for malformed in (None, 'not-evidence', [None], {'unknown': True}):
            payload = f.payload()
            payload['candidateNodes'][0]['evidence'] = malformed
            result = self.run_case('ciroh_hub', f, payload).to_record()
            self.assertFalse(result['projection']['nodes'] or result['projection']['edges'])
            self.assertEqual(result['originalReplay']['finalRecords'][0]['originalCandidate']['evidence'], malformed)

    def version_identity_case(self, quote):
        """Build literal version evidence alongside an independent Tool assertion."""
        from pathlib import Path
        import tempfile
        from src.extraction.llm.coderepos.source_units import read_repository_sources
        f = self.fixture('github')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repo = {'repo_id': 7, 'name': 'Demo', 'full_name': 'Example/Demo',
                'archive': {'frozen_commit_sha': 'a' * 40},
                'readme': {'source_path': 'README.md', 'text': '# Guide\n\n' + quote + '\n\n' + f.quote},
                'files': {'downloaded': []}}
        reader = read_repository_sources(repo, Path(temporary.name))
        version_uid, tool_uid = [u['sourceUnitID'] for u in reader['sourceUnits']]
        payload = f.payload()
        for row in payload['candidateNodes'] + payload['candidateEdges']:
            row['evidence'][0]['sourceUnitID'] = tool_uid
        version = deepcopy(payload['candidateNodes'][0])
        version.update(candidateID='version', inventoryId='A-C10', **{'class': 'ModelVersion'},
                       label='1.0', productRepositoryID=f.owner,
                       endpoint={'referenceType': 'accepted_endpoint', 'referenceID': 'deterministic-version'},
                       evidence=[{'sourceUnitID': version_uid, 'evidenceText': quote}])
        edge = deepcopy(payload['candidateEdges'][0])
        edge.update(candidateID='version-edge', inventoryId='C-C09', relation='hasModelVersion',
                    target={'referenceType': 'candidate_node', 'referenceID': 'version'},
                    evidence=deepcopy(version['evidence']))
        payload['candidateNodes'].append(version)
        payload['candidateEdges'].append(edge)
        inputs = deepcopy(f.inputs)
        inputs.update(reader_result=reader, selected_unit_ids=[version_uid, tool_uid],
            accepted_endpoints=[{'endpointID': 'deterministic-version', 'inventoryId': 'A-C10',
                'class': 'ModelVersion', 'productRepositoryID': f.owner,
                'identityRegime': 'structured_version_literal',
                'attributes': {'sourceRepoId': 7, 'version': '1.0', 'softwareName': 'Demo',
                               'toolId': 'deterministic-product', 'sourceType': 'software_metadata',
                               'sourcePath': 'pyproject.toml'}}],
            accepted_assertions=[{'assertionID': 'deterministic-version-edge', 'inventoryId': 'C-C09',
                'relation': 'hasModelVersion', 'sourceID': f.owner, 'targetID': 'deterministic-version',
                'attributes': {'toolId': 'deterministic-product', 'softwareName': 'Demo'}}])
        return f, payload, inputs

    def test_version_mismatch_and_dependent_edges_preserve_provenance(self):
        """A quoted 2.0 must not be suppressed as deterministic 1.0 by reference."""
        from src.extraction.llm.coderepos import offline_pipeline, request_contract
        f, payload, inputs = self.version_identity_case('This repository provides Demo version 2.0.')
        for label in ('1.0', '2.0'):
            payload['candidateNodes'][1]['label'] = label
            before = deepcopy((payload, inputs))
            raw = canonical(payload)
            request = request_contract.build_request(**inputs)
            replay = offline_pipeline.replay_recorded_response(raw, request_inputs=inputs,
                expected_request_sha256=request['requestSha256'])
            result = self.run_case('github', f, payload, inputs)
            decisions = self.decisions(result)
            self.assertEqual(decisions['version']['disposition'], 'held')
            self.assertEqual(decisions['version-edge']['disposition'], 'held')
            self.assertEqual(decisions['tool']['disposition'], 'accepted')
            self.assertEqual(decisions['edge']['disposition'], 'accepted')
            self.assertEqual(result.to_record()['originalReplay'], json.loads(replay.report_json))
            self.assertEqual(result.to_record()['originalReplaySha256'], replay.report_sha256)
            original = next(r for r in result.to_record()['originalReplay']['finalRecords'] if r['candidateID'] == 'version')
            self.assertTrue(original['validationRecord']['suppressedDuplicate'])
            self.assertEqual(original['validationRecord']['duplicateOf'], ['deterministic-version'])
            self.assertEqual(before, (payload, inputs))
            self.assertEqual(result, self.run_case('github', f, payload, inputs))

    def test_apparent_version_match_missing_or_ambiguous_identity_stays_held(self):
        """Even matching prose/attributes lack a frozen evidence-to-product binding."""
        for quote in ('This repository provides Demo version 1.0.',
                      'Demo version 1.0 and Demo version 2.0 are described here.'):
            f, payload, inputs = self.version_identity_case(quote)
            for defect in ('none', 'missing_attributes', 'missing_assertion', 'contradictory_product'):
                context = deepcopy(inputs)
                if defect == 'missing_attributes':
                    del context['accepted_endpoints'][0]['attributes']
                elif defect == 'missing_assertion':
                    context['accepted_assertions'] = []
                elif defect == 'contradictory_product':
                    context['accepted_assertions'][0]['attributes']['toolId'] = 'another-product'
                result = self.run_case('github', f, payload, context)
                for cid in ('version', 'version-edge'):
                    decision = self.decisions(result)[cid]
                    self.assertEqual(decision['disposition'], 'held')
                    self.assertIn('candidate_version_product_identity_not_established', decision['blockingReasons'])
                self.assertEqual(len(result.to_record()['projection']['nodes']), 1)
                self.assertEqual(len(result.to_record()['projection']['edges']), 1)

    def test_direct_version_edge_cannot_bypass_identity_hold(self):
        """A direct accepted-endpoint edge remains held despite an upstream duplicate."""
        for quote in ('This repository provides Demo version 1.0.',
                      'This repository provides Demo version 2.0.'):
            f, payload, inputs = self.version_identity_case(quote)
            payload['candidateNodes'].pop()
            payload['candidateEdges'][1]['target'] = {
                'referenceType': 'accepted_endpoint', 'referenceID': 'deterministic-version'}
            result = self.run_case('github', f, payload, inputs)
            decision = self.decisions(result)['version-edge']
            self.assertEqual(decision['disposition'], 'held')
            self.assertEqual(decision['duplicateOf'], ['deterministic-version-edge'])
            original = next(r for r in result.to_record()['originalReplay']['finalRecords'] if r['candidateID'] == 'version-edge')
            self.assertTrue(original['validationRecord']['suppressedDuplicate'])
            self.assertEqual(len(result.to_record()['projection']['edges']), 1)
