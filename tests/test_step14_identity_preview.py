"""Synthetic identity fixtures; no corpus execution or provider calls."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_identity_preview as m

CLASSES = {'Paper': 'A-P01', 'DatasetResource': 'A-D01', 'Repository': 'A-C01',
           'Person': 'A-AG01', 'Organization': 'A-AG02', 'Identifier': 'A-ID01', 'Tool': 'A-DOM02'}


def node(nid, cls='Paper', **attrs):
    """Make a deterministic typed fixture with documentary evidence."""
    return dict(id=nid, **{'class': cls}, inventoryId=CLASSES[cls], attributes=attrs,
                curationStatus='referenced', evidence={'sourceArtifact': 'source:' + nid})


def native(nid, action='propose_new', target=None):
    """Make a hash-bound Publication occurrence sidecar fixture."""
    record = dict(candidate=dict(action=action, existingNodeID=target), candidateID='node-0001')
    return dict(kind='nodes', graphID=nid, nativeRecord=record,
                nativeRecordSha256=hashlib.sha256(m.encoded(record)).hexdigest(),
                provenance={'requestID': nid.split('#')[0]})


class PreviewTests(unittest.TestCase):
    def setUp(self):
        """Block network entry points throughout focused tests."""
        self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('NETWORK')))

    def preview(self, nodes, edges=None, rows=None):
        """Assert input preservation for every fixture."""
        graph = dict(nodes=nodes, edges=edges or [])
        saved = deepcopy(graph)
        result = m.prepare(graph, rows or [], CLASSES)
        self.assertEqual(graph, saved)
        return result

    def test_exact_doi_and_determinism(self):
        """Exact DOI groups ignore input ordering and preserve two occurrences."""
        nodes = [node('a', doi='10.1234/a'), node('b', doi='10.1234/a')]
        result = self.preview(nodes)
        self.assertEqual(result, self.preview(nodes[::-1]))
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(len(result['mappings']), 2)

    def test_class_role_conflict(self):
        """A dataset and paper with one DOI are a conflict, never an identity."""
        result = self.preview([node('a', doi='10.1234/a'), node('b', 'DatasetResource', doi='10.1234/a')])
        self.assertFalse(result['matches'])
        self.assertIn('class_or_artifact_role_conflict', result['conflicts'][0]['reasons'])

    def test_reference_is_not_owner_identity(self):
        """Citation strings and source identifiers cannot identify the citing entity."""
        result = self.preview([node('a', citation='10.1234/a', sourcePaperCanonicalKey='doi:10.1234/a'),
                               node('b', doi='10.1234/a'), node('tool', 'Tool', doi='10.1234/a')])
        self.assertFalse(result['matches'])

    def test_hydroshare_and_numeric_repository(self):
        """Only entity-own resource and numeric repository fields are eligible."""
        hs = 'a' * 32
        nodes = [node('a', 'DatasetResource', resourceId=hs), node('b', 'DatasetResource')]
        nodes[1]['canonicalKey'] = 'hydroshare:' + hs
        for nid in ('c', 'd'):
            n = node(nid, 'Repository', repoId=123)
            n.update(canonicalKey='github-repo-id:123', identityRegime='github_numeric_id'); nodes.append(n)
        self.assertEqual(len(self.preview(nodes)['matches']), 2)

    def test_orcid_and_ror(self):
        """Governed agent identifiers are eligible without name matching."""
        nodes = [node('a', 'Person', orcid='0000-0002-1825-0097'),
                 node('b', 'Person', orcid='https://orcid.org/0000-0002-1825-0097'),
                 node('c', 'Organization', ror='03yrm5c26', identifierRegime='ROR'),
                 node('d', 'Organization', ror='03yrm5c26', identifierRegime='ROR')]
        self.assertEqual(len(self.preview(nodes)['matches']), 2)

    def test_name_and_source_local_remain_unresolved(self):
        """Equal names and provisional claims supply no global identity."""
        nodes = [node('a', label='same'), node('b', label='same'),
                 node('c', doi='10.1234/a', identityScope='source_local'), node('d', doi='10.1234/a')]
        self.assertFalse(self.preview(nodes)['matches'])

    def test_publication_occurrences_and_link_existing(self):
        """Exact declarations are retained without promoting local occurrence IDs."""
        nodes = [node('r1#node#node-0001', doi='10.1234/a'), node('r2#node#node-0001', doi='10.1234/a'), node('target', doi='10.1234/a')]
        rows = [native(nodes[0]['id'], 'link_existing', 'target'), native(nodes[1]['id'])]
        result = self.preview(nodes, rows=rows)
        self.assertFalse(result['matches'])
        first = result['mappings'][0]
        self.assertEqual(first['declaredExistingNodeIDs'], ['target'])
        self.assertEqual(first['status'], 'publication_link_existing_requires_context')

    def test_versions_and_missing_versions(self):
        """Incompatible and partially specified versions remain unresolved."""
        for attrs in ({'version': 'v2'}, {}):
            result = self.preview([node('a', doi='10.1234/a', version='v1'), node('b', doi='10.1234/a', **attrs)])
            self.assertFalse(result['matches']); self.assertTrue(result['conflicts'])

    def test_transitive_conflicting_identifiers(self):
        """A multi-key bridge cannot silently merge conflicting DOI identities."""
        hs = 'a' * 32
        nodes = [node('a', 'DatasetResource', resourceId=hs, doi='10.1234/a'),
                 node('b', 'DatasetResource', resourceId=hs, doi='10.1234/b'),
                 node('c', 'DatasetResource', doi='10.1234/b')]
        result = self.preview(nodes)
        self.assertFalse(result['matches'])
        self.assertEqual(result['conflicts'][0]['occurrenceIDs'], ['a', 'b', 'c'])

    def test_governed_own_identifier_edge(self):
        """C-D04 identifies the dataset; reference edges do not identify the owner."""
        nodes = [node('a', 'DatasetResource'), node('b', 'DatasetResource', doi='10.1234/a'),
                 node('id', 'Identifier', identifierType='DOI', identifierValue='10.1234/a')]
        edge = dict(source='a', target='id', relation='hasIdentifier', inventoryId='C-D04', evidence={'quote': 'own DOI'})
        self.assertEqual(len(self.preview(nodes, [edge])['matches']), 1)
        edge['relation'] = 'referencesDataset'
        self.assertFalse(self.preview(nodes, [edge])['matches'])

    def test_drift_and_duplicate_fail_closed(self):
        """Untrustworthy native records and duplicate snapshot IDs block output."""
        row = native('a'); row['nativeRecord']['changed'] = True
        with self.assertRaisesRegex(ValueError, 'NATIVE_HASH_DRIFT'):
            self.preview([node('a')], rows=[row])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_NODE_ID'):
            self.preview([node('a'), node('a')])

    def test_runner_fixture_and_hash_failure(self):
        """Exercise pinned-file IO and deterministic artifacts on a tiny fixture only."""
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                root = Path('var/input'); root.mkdir(parents=True)
                spec = Path('src/ontology/ontology_spec.yaml'); spec.parent.mkdir(parents=True)
                spec.write_text('classes: [{name: Paper, id: A-P01}]')
                owl = spec.with_name('ciroh_ontology.owl'); owl.write_text('fixture ontology')
                sidecar = root / 'native.jsonl'; sidecar.write_text('')
                derivation = root / 'derivation-provenance.jsonl'; derivation.write_text('')
                snapshot = root / 'snapshot.json'
                snapshot.write_bytes(m.encoded(dict(nodes=[node('a', doi='10.1234/a'), node('b', doi='10.1234/a')], edges=[])))
                summary = root / 'summary.json'
                summary.write_bytes(m.encoded(dict(originalNativeProvenancePath=str(sidecar),
                    originalNativeProvenanceSha256=m.sha(sidecar), derivationProvenanceSha256=m.sha(derivation),
                    inputHashes={str(spec): m.sha(spec), str(owl): m.sha(owl)})))
                pins = {p.name: m.sha(p) for p in (snapshot, summary)}
                with patch.object(m, 'ROOT', root), patch.object(m, 'PINS', pins):
                    first = Path('var/study2_step14/one'); second = Path('var/study2_step14/two')
                    m.run(first); m.run(second)
                    self.assertEqual((first / 'preview.json').read_bytes(), (second / 'preview.json').read_bytes())
                    self.assertEqual(sorted(p.name for p in first.iterdir()), ['preview.json', 'report.md'])
                    sidecar.write_text('drift')
                    with self.assertRaisesRegex(ValueError, 'INPUT_HASH_DRIFT'):
                        m.run(Path('var/study2_step14/three'))
                    self.assertFalse(Path('var/study2_step14/three').exists())
            finally:
                os.chdir(old)

    def test_output_boundary(self):
        """The runner refuses existing and out-of-scope destinations before input IO."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'OUTPUT_ALREADY_EXISTS'):
                m.run(Path(directory))
            with self.assertRaisesRegex(ValueError, 'STEP14_OUTPUT_REQUIRED'):
                m.run(Path(directory) / 'new')


if __name__ == '__main__':
    unittest.main()
