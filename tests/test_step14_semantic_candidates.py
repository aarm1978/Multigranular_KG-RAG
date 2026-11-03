"""Synthetic-only tests for bounded candidate preparation."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import yaml
from src.evaluation import step14_semantic_candidates as m

SPEC = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())
CLASSES = {c['name']: c['id'] for c in SPEC['classes']}


def node(nid, cls='MLModel', **attributes):
    """Create an evidence-bearing deterministic fixture."""
    return dict(id=nid, **{'class': cls}, inventoryId=CLASSES[cls], attributes=attributes,
                curationStatus='referenced', internalLineage={'localPaperId': nid},
                evidence=dict(sourceArtifact='paper:' + nid, evidenceText='Evidence for ' + nid))


def native(nid, candidate, family='publications', **extra):
    """Create an immutable accepted native record fixture."""
    record = dict(candidate=candidate, evidenceOccurrences=[dict(canonicalPaperID='paper:source', evidenceText='Own identifier 10.1234/a')], **extra)
    return dict(kind='nodes', graphID=nid, nativeRecord=record, nativeRecordSha256=m.token(record),
                provenance=dict(family=family, requestID='request:' + nid))


class CandidateTests(unittest.TestCase):
    def setUp(self):
        """Disable network in every focused test."""
        self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('NETWORK')))

    def prepare(self, nodes, rows=None, cap=32, edges=None):
        """Check nonmutation with each fixture."""
        graph = dict(nodes=nodes, edges=edges or []); rows = rows or []
        saved = deepcopy((graph, rows, SPEC))
        result = m.prepare(graph, iter(rows), SPEC, cap)
        self.assertEqual((graph, rows, SPEC), saved)
        self.assertTrue(all(not r['automaticMergeEligible'] for r in result['records']))
        return result

    def test_identity_versus_reference(self):
        """Own identifiers do not spread to citing owners or mention nodes."""
        nodes = [node('a', 'Paper', doi='10.1234/a'), node('b', 'Paper', doi='10.1234/a'),
                 node('c', 'Paper', citation='10.1234/a'), node('d', 'DatasetMention', doi='10.1234/a')]
        result = self.prepare(nodes)
        self.assertEqual(result['blocks'][0]['occurrenceIDs'], ['a', 'b'])
        self.assertFalse(result['records'][2]['identifierDeclarations'])
        self.assertEqual(result['coverage']['excludedByClass'], {'DatasetMention': 1})

    def test_generic_specific_and_missing_detail(self):
        """A generic and trained LSTM share a candidate block, never an identity."""
        result = self.prepare([node('generic', label='LSTM', description='Generic LSTM architecture'),
                               node('specific', label='LSTM', description='Trained for basin A using weights W'),
                               node('unknown', label='LSTM')])
        self.assertEqual(len(result['blocks']), 1)
        self.assertFalse(result['blocks'][0]['equivalenceAsserted'])
        for r in result['records']:
            self.assertEqual(r['granularity'], 'unspecified_requires_context_review')
            self.assertEqual(r['identityDecision'], 'not_assessed')
        self.assertIn('weights W', result['records'][1]['embeddingText'])

    def test_version_conflict_and_unknown(self):
        """Known unequal versions are flagged; absent values stay unknown."""
        result = self.prepare([node('a', label='LSTM', version='v1'), node('b', label='LSTM', version='v2'), node('c', label='LSTM')])
        flags = result['blocks'][0]['flags']
        self.assertIn('explicit_version_conflict:version', flags)
        self.assertIn('unknown_version:version', flags)

    def test_ontology_incompatibility(self):
        """Same label in distinct classes never creates a comparison block."""
        result = self.prepare([node('a', 'Algorithm', label='X'), node('b', 'Tool', label='X'), node('c', 'MLModel', label='X')])
        self.assertFalse(result['blocks'])
        broken = node('d', label='X'); broken['inventoryId'] = 'A-DOM02'
        result = self.prepare([node('a', label='X'), broken])
        self.assertFalse(result['blocks'])
        self.assertIn('ontology_class_inventory_mismatch', result['records'][1]['preparationFlags'])

    def test_missing_provenance_retained_not_blocked(self):
        """Missing origins are reported and retained outside candidate blocks."""
        broken = node('b', label='X'); broken.pop('evidence')
        result = self.prepare([node('a', label='X'), broken])
        self.assertEqual(len(result['records']), 2)
        self.assertFalse(result['blocks'])
        self.assertIn('missing_provenance', result['records'][1]['preparationFlags'])

    def test_native_identifiers_and_local_link(self):
        """Exact declarations are bound locally; Publication links remain declarations."""
        nodes = [node('a', 'Paper', label='P'), node('b', 'Paper', label='P')]
        rows = [native('a', dict(exactIdentifier='10.1234/a')), native('b', dict(action='link_existing', existingNodeID='a'))]
        result = self.prepare(nodes, rows)
        self.assertTrue(result['records'][0]['identifierDeclarations'][0]['evidenceBound'])
        self.assertEqual(result['records'][1]['declaredExistingNodeIDs'], ['a'])
        self.assertFalse(result['blocks'])
        rows[0]['nativeRecord']['candidate']['exactIdentifier'] = '10.1234/absent'
        rows[0]['nativeRecordSha256'] = m.token(rows[0]['nativeRecord'])
        self.assertFalse(self.prepare(nodes, rows)['records'][0]['identifierDeclarations'][0]['evidenceBound'])

    def test_geographic_literal_and_no_inference(self):
        """Only explicit governed URI declarations are retained, never inferred HUCs."""
        nodes = [node('a', 'Watershed', identifierRegime='geoconnex-url', identifierValue='https://geoconnex.us/ref/hu02/01'),
                 node('b', 'Watershed', label='HUC 01'), node('c', 'HydrologicFeature', identifierRegime='geoconnex-url', identifierValue='https://geoconnex.us/ref/hu02/01')]
        result = self.prepare(nodes)
        self.assertEqual(result['records'][0]['identifierDeclarations'][0]['scheme'], 'geoconnex-url')
        self.assertFalse(result['records'][1]['identifierDeclarations'])
        self.assertIn('abstract_class_retained_not_retyped', result['records'][2]['preparationFlags'])

    def test_contextual_records_excluded(self):
        """Metrics, parameters and discourse never enter automatic comparisons."""
        result = self.prepare([node('a', 'EvaluationMetric', label='NSE', value='0.9'),
                               node('b', 'Parameter', label='k', value='1'), node('c', 'Finding', label='result')])
        self.assertFalse(result['records']); self.assertFalse(result['blocks'])
        self.assertEqual(sum(result['coverage']['excludedByClass'].values()), 3)

    def test_caps_ambiguity_and_ordering(self):
        """Oversized blocks never enumerate pairs or emit a selected subset."""
        nodes = [node(str(i), label=' LSTM ') for i in range(5)]
        result = self.prepare(nodes, cap=3)
        self.assertEqual(result, self.prepare(nodes[::-1], cap=3))
        self.assertEqual(result['blocks'][0]['status'], 'oversized_not_expanded')
        self.assertEqual(result['blocks'][0]['occurrenceIDs'], [])
        self.assertEqual(result['blocks'][0]['memberCount'], 5)
        result = self.prepare([node('a', label=['LSTM', 'Long short-term memory']), node('b', label='LSTM')])
        self.assertFalse(result['blocks'])
        self.assertIn('multiple_lexical_labels', result['records'][0]['preparationFlags'])
        self.assertNotEqual(m.normalize('LSTM-v1'), m.normalize('LSTM v1'))

    def test_nonpublication_owner_and_original_candidate(self):
        """Owner-report lineage preserves non-Publication artifact and exact declaration."""
        n = node('a', 'DatasetResource', label='dataset')
        record = dict(originalCandidate=dict(exactIdentifier='10.1234/a'),
                      boundEvidence=[dict(sourceUnitID='unit', evidenceText='10.1234/a')])
        row = dict(kind='nodes', graphID='a', nativeRecord=record,
                   nativeRecordSha256=m.token(record), provenance=dict(family='hydroshare', path='owner.json'))
        result = m.prepare(dict(nodes=[n], edges=[]), [row], SPEC, owners={'owner.json': 'owner-id'})
        r = result['records'][0]
        self.assertEqual(r['sourceArtifacts'], ['owner-id'])
        self.assertEqual(r['sourceFamilies'], ['hydroshare'])
        self.assertEqual(r['originalCandidates'], [record['originalCandidate']])
        self.assertTrue(r['identifierDeclarations'][0]['evidenceBound'])

    def test_own_doi_relation_not_citation(self):
        """Only governed own-identifier assertions populate dataset declarations."""
        nodes = [node('a', 'DatasetResource'), node('b', 'DatasetResource', doi='10.1234/a'),
                 node('id', 'Identifier', identifierType='DOI', identifierValue='10.1234/a')]
        edge = dict(id='edge', source='a', target='id', relation='hasIdentifier', inventoryId='C-D04', evidence={'evidenceText': 'own'})
        self.assertEqual(len(self.prepare(nodes, edges=[edge])['blocks']), 1)
        edge['relation'] = 'referencesDataset'
        self.assertFalse(self.prepare(nodes, edges=[edge])['blocks'])

    def test_output_and_cap_boundaries(self):
        """Invalid caps and non-Step-14 outputs are refused before corpus access."""
        for cap in (1, 129):
            with self.assertRaisesRegex(ValueError, 'BLOCK_CAP'):
                self.prepare([], cap=cap)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'SEMANTIC_OUTPUT_REQUIRED'):
                m.run(Path(directory) / 'outside')

    def test_hash_drift(self):
        """Native hash failures stop preparation."""
        row = native('a', {}); row['nativeRecord']['changed'] = True
        with self.assertRaisesRegex(ValueError, 'NATIVE_HASH_DRIFT'):
            self.prepare([node('a')], [row])

    def test_fixture_output_reproducibility(self):
        """Only synthetic data exercises the writer; no real corpus job runs."""
        with tempfile.TemporaryDirectory(dir='var') as directory:
            sidecar = Path(directory) / 'native.jsonl'; sidecar.write_text('')
            graph = dict(nodes=[node('a', label='X'), node('b', label='X')], edges=[])
            base = Path('var/study2_step14/semantic-candidates')
            with patch.object(m.identity, 'verified_inputs', return_value=(graph, SPEC, sidecar, {})):
                # Redirect only the destination boundary in this fixture.
                with tempfile.TemporaryDirectory(dir=base.parent if base.parent.exists() else 'var') as out:
                    dest = Path(out) / 'one'
                    with patch.object(Path, 'is_relative_to', return_value=True):
                        manifest = m.run(dest)
                        other = Path(out) / 'two'; m.run(other)
                    for name in ('occurrences.jsonl', 'candidate-blocks.jsonl', 'manifest.json', 'report.md'):
                        self.assertEqual((dest / name).read_bytes(), (other / name).read_bytes())
                    self.assertEqual(manifest['equivalencesAsserted'], 0)
                    with self.assertRaisesRegex(ValueError, 'OUTPUT_ALREADY_EXISTS'):
                        m.run(dest)


if __name__ == '__main__':
    unittest.main()
