"""Synthetic tests for diagnostic identifier scope; no corpus execution."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_identifier_scope_triage as m
from tests.test_step14_semantic_review import SPEC, occurrence


def dossier(raw='10.1234/example', scheme='doi', local=False, cls='Paper', suffix=''):
    """Build a hash-bound compact cross-family dossier fixture."""
    key = ['identifier_declaration_only', cls, scheme, raw]
    rows = [occurrence('a' + suffix), occurrence('b' + suffix, 'github')]
    classes = {c['name']: c['id'] for c in SPEC['classes']}
    for row in rows:
        row.update(ontologyClass=cls, inventoryId=classes[cls], lane='identity_declaration')
        row['identifierDeclarations'] = [dict(scheme=scheme, value=raw,
            basis='accepted_source_local_candidate' if local else 'deterministic_entity_own_field',
            **({'scope': 'source_local_no_global_equivalence', 'evidenceBound': True} if local else {}))]
    ids = sorted(r['occurrenceID'] for r in rows)
    return dict(blockID=m.digest(key), key=key, ontologyClass=cls, candidateMechanism=key[0],
        occurrenceIDs=ids, memberCount=2, membershipSha256=m.digest(ids), equivalenceAsserted=False,
        sourceFamilyDistribution={'publications': 1, 'github': 1}, existingBlockFlags=[],
        members=[m.review.compact_member(r) for r in rows])


def replace_field(member, field, new_value):
    """Update a fixture's bounded field and its integrity hash together."""
    member[field] = m.review.bounded(new_value, member[field]['reference'])


class TriageTests(unittest.TestCase):
    def setUp(self):
        """Block networking for every focused test."""
        self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('NETWORK')))

    def prepare(self, blocks):
        """Check nonmutation with every fixture."""
        saved = deepcopy(blocks)
        result = m.prepare(blocks, SPEC)
        self.assertEqual(blocks, saved)
        return result

    def test_authoritative_ids_and_missing_versions(self):
        """Missing versions alone do not invalidate strong record identity candidates."""
        for b in (dossier(), dossier('a' * 32, 'hydroshare', cls='DatasetResource')):
            r = self.prepare([b])['records'][0]
            self.assertEqual(r['provisionalReviewCategory'], 'strong_record_identity_candidate')
            self.assertIn('missing_version_information', r['riskFlags'])
            self.assertEqual(r['identityLevels']['conceptualIdentity'], 'outside_identifier_pass')
            self.assertEqual(r['equivalencesApproved'], 0)

    def test_local_literal_never_global(self):
        """A local DOI or repository URL remains only an exact locator candidate."""
        for raw in ('https://github.com/Org/Repo', 'https://doi.org/10.1234/example', '10.1234/example'):
            b = dossier(raw, 'literal_exactIdentifier', local=True)
            r = self.prepare([b])['records'][0]
            self.assertEqual(r['provisionalReviewCategory'], 'exact_locator_candidate_only')
            self.assertEqual(r['identifierScope'], {'source_local_literal_declaration': 2})
            self.assertEqual(r['occurrenceIDs'], b['occurrenceIDs'])

    def test_incompatible_class_and_version_conflict(self):
        """Class and explicit version contradictions require context review."""
        b = dossier(); b['members'][1]['ontologyClass'] = 'DatasetResource'
        r = self.prepare([b])['records'][0]
        self.assertEqual(r['provisionalReviewCategory'], 'unresolved_requires_context')
        self.assertIn('incompatible_ontology_class', r['riskFlags'])
        b = dossier(); replace_field(b['members'][0], 'versions', {'version': 'v1'})
        replace_field(b['members'][1], 'versions', {'version': 'v2'})
        self.assertEqual(self.prepare([b])['records'][0]['provisionalReviewCategory'], 'unresolved_requires_context')
        self.assertEqual(self.prepare([dossier(cls='Tool')])['records'][0]['provisionalReviewCategory'], 'unresolved_requires_context')

    def test_url_syntax_variants(self):
        """Paths distinguish roots, clones, trees, files and DOI resolver URLs."""
        cases = {
            'https://github.com/o/r': 'github_repository_root',
            'https://github.com/o/r.git': 'github_clone_url',
            'https://github.com/o/r/tree/main': 'github_branch_tree_path',
            'https://github.com/o/r/blob/main/a.py': 'github_specific_file_path',
            'https://www.hydroshare.org/resource/' + 'a' * 32 + '/': 'hydroshare_resource_url',
            'https://doi.org/10.1234/a': 'doi_resolver_url',
            '10.1234/a': 'doi_identifier',
            'https://github.com/o/r?ref=v1': 'query_or_fragment_locator_requires_context',
        }
        for raw, expected in cases.items():
            self.assertEqual(m.locator(raw)['category'], expected)
            self.assertEqual(m.locator(raw)['raw'], raw)

    def test_dynamic_and_specific_syntax(self):
        """Bucket roots/directories/indexes do not become specific object identities."""
        cases = {'s3://bucket': 'object_store_bucket_root', 's3://bucket/data/': 'object_store_directory_prefix',
                 's3://bucket/file.nc': 'object_store_specific_key_syntax',
                 'https://example.test/file.zip': 'specific_download_path_syntax',
                 'https://example.test/index.html': 'index_or_catalog_path',
                 'https://example.test/registry': 'registry_or_portal_path'}
        for raw, expected in cases.items():
            self.assertEqual(m.locator(raw)['category'], expected)
        r = self.prepare([dossier('s3://bucket', 'literal_exactIdentifier', local=True)])['records'][0]
        self.assertEqual(r['provisionalReviewCategory'], 'unresolved_requires_context')

    def test_cross_block_syntactic_relationships_only(self):
        """Only explicit root/clone, DOI and HydroShare syntax pairs are annotated."""
        blocks = [dossier('https://github.com/o/r', 'literal_exactIdentifier', True, 'Repository', '1'),
                  dossier('https://github.com/o/r.git', 'literal_exactIdentifier', True, 'Repository', '2'),
                  dossier('https://github.com/o/r/tree/main', 'literal_exactIdentifier', True, 'Repository', '3'),
                  dossier('a' * 32, 'hydroshare', cls='DatasetResource', suffix='4'),
                  dossier('https://hydroshare.org/resource/' + 'a' * 32, 'literal_exactIdentifier', True, 'DatasetResource', '5'),
                  dossier(suffix='6'), dossier('https://doi.org/10.1234/example', 'literal_exactIdentifier', True, suffix='7')]
        result = self.prepare(blocks)
        counts = {r['key'][3]: len(r['possibleCrossBlockRelationships']) for r in result['records']}
        self.assertEqual(counts['https://github.com/o/r/tree/main'], 0)
        self.assertEqual(sum(counts.values()), 6)
        self.assertTrue(all(not rel['equivalenceImplied'] for r in result['records'] for rel in r['possibleCrossBlockRelationships']))

    def test_divergent_labels_descriptions_and_evidence_reuse(self):
        """Variation/repeated excerpts prompt review without independent-confirmation claims."""
        b = dossier()
        replace_field(b['members'][0], 'labels', ['Generic LSTM'])
        replace_field(b['members'][1], 'labels', ['Basin-specific trained LSTM'])
        b['members'][1]['evidenceExcerpts'] = deepcopy(b['members'][0]['evidenceExcerpts'])
        r = self.prepare([b])['records'][0]
        self.assertIn('divergent_labels', r['riskFlags'])
        self.assertIn('potentially_conflicting_description_variants', r['riskFlags'])
        self.assertIn('duplicated_evidence_across_families', r['riskFlags'])
        self.assertEqual(r['identityLevels']['entityIdentity'], 'unadjudicated')

    def test_truncation_and_invalid_scope(self):
        """Truncated declarations or unsupported scopes cannot become strong candidates."""
        b = dossier(); b['members'][0]['identifierDeclarations'] = {'truncated': True}
        self.assertEqual(self.prepare([b])['records'][0]['provisionalReviewCategory'], 'unresolved_requires_context')
        b = dossier(); declarations = deepcopy(b['members'][0]['identifierDeclarations']['value'])
        declarations[0]['scope'] = 'source_local_no_global_equivalence'
        replace_field(b['members'][0], 'identifierDeclarations', declarations)
        self.assertEqual(self.prepare([b])['records'][0]['provisionalReviewCategory'], 'unresolved_requires_context')

    def test_membership_and_dossier_hash_failures(self):
        """Corrupt member lists and complete-field hashes fail closed."""
        b = dossier(); b['membershipSha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_HASH_DRIFT'):
            self.prepare([b])
        b = dossier(); b['members'][0]['labels']['value'] = ['changed']
        with self.assertRaisesRegex(ValueError, 'DOSSIER_FIELD_HASH_DRIFT'):
            self.prepare([b])

    def fixture_inputs(self, root):
        """Write only synthetic dossier/manifest inputs plus small ontology pins."""
        root.mkdir(parents=True); upstream = root / 'upstream'; upstream.mkdir()
        ontology = {p: m.sha(Path(p)) for p in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl')}
        cm = dict(version=m.review.candidates.VERSION, inputHashes=ontology,
                  outputHashes={'occurrences.jsonl': 'not-consumed', 'candidate-blocks.jsonl': 'not-consumed'})
        (upstream / 'manifest.json').write_bytes(m.encoded(cm))
        (root / 'review-dossier.jsonl').write_bytes(m.encoded(dossier()) + b'\n')
        rm = dict(version=m.review.VERSION, diagnosticOnly=True, equivalencesAsserted=0, inputRoot=str(upstream),
            implementationSha256=m.sha(Path('src/evaluation/step14_semantic_review.py')),
            summary={'dossierBlocks': 1}, outputHashes={'review-dossier.jsonl': m.sha(root / 'review-dossier.jsonl')},
            inputHashes={**ontology, str(upstream / 'manifest.json'): m.sha(upstream / 'manifest.json'),
                         **{str(upstream / name): 'not-consumed' for name in cm['outputHashes']}})
        (root / 'manifest.json').write_bytes(m.encoded(rm))
        return m.sha(root / 'manifest.json')

    def test_hash_manifest_verification_and_reproducible_writer(self):
        """Changed manifests/inputs fail without output; fixture runs preserve inputs."""
        base = Path('var/study2_step14/identifier-scope-triage'); base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temp:
            root = Path(temp) / 'input'; pin = self.fixture_inputs(root)
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(m, 'MANIFEST_SHA256', pin):
                a = Path(temp) / 'a'; b = Path(temp) / 'b'; m.run(root, a); m.run(root, b)
                for p in a.iterdir():
                    self.assertEqual(p.read_bytes(), (b / p.name).read_bytes())
                self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})
                with self.assertRaisesRegex(ValueError, 'OUTPUT_ALREADY_EXISTS'):
                    m.run(root, a)
                (root / 'manifest.json').write_bytes((root / 'manifest.json').read_bytes() + b'\n')
                with self.assertRaisesRegex(ValueError, 'INPUT_HASH_DRIFT'):
                    m.run(root, Path(temp) / 'c')
                self.assertFalse((Path(temp) / 'c').exists())
                (root / 'manifest.json').write_bytes(before[str(root / 'manifest.json')])
                (root / 'review-dossier.jsonl').write_text('drift')
                with self.assertRaisesRegex(ValueError, 'INPUT_HASH_DRIFT'):
                    m.inputs(root)

    def test_ordering_and_skip_lexical(self):
        """Order cannot change bytes; lexical member payloads are not inspected."""
        blocks = [dossier(), dossier('b' * 32, 'hydroshare', cls='DatasetResource')]
        blocks.append(dict(blockID='lexical-block', candidateMechanism='lexical_similarity_only'))
        self.assertEqual(self.prepare(blocks), self.prepare(blocks[::-1]))
        self.assertEqual(self.prepare(blocks)['summary']['skippedNonIdentifierBlocks'], 1)


if __name__ == '__main__':
    unittest.main()
