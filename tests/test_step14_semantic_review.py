"""Focused synthetic dossier tests; never execute the corpus."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import yaml
from src.evaluation import step14_semantic_review as m

SPEC = yaml.safe_load(Path('src/ontology/ontology_spec.yaml').read_text())


def occurrence(nid: str, family: str = 'publications', label: str = 'LSTM', artifact: str | None = None) -> dict:
    """Create an existing candidate fixture with recoverable original provenance."""
    return dict(occurrenceID=nid, ontologyClass='MLModel', inventoryId='A-DOM03d',
        sourceFamilies=[family], sourceArtifacts=[artifact or 'artifact:' + nid],
        lane='semantic_comparison', normalizedLabels=[label.casefold()], labels=[label],
        identifierDeclarations=[], preparationFlags=[], versions={}, attributes={'label': label},
        contextualDescriptions=['Original context for ' + nid], declaredExistingNodeIDs=[],
        granularity='unspecified_requires_context_review', identityDecision='not_assessed',
        automaticMergeEligible=False, originalSnapshotRecord={'id': nid},
        evidenceReferences=[dict(evidenceText='Original evidence for ' + nid, sourceLocation='line 3', sourceUnitID='unit:' + nid)],
        nativeReferences=[dict(nativeRecordSha256='native-hash', provenance={'family': family, 'requestID': 'request:' + nid})])


def block(ids: list[str], label: str = 'LSTM', cap: int = 32, key: list | None = None) -> dict:
    """Make a frozen block with explicitly supplied expected membership."""
    key = key or ['lexical_similarity_only', 'MLModel', label.casefold()]
    ids = sorted(ids)
    return dict(blockID=m.candidates.token(key), key=key, memberCount=len(ids),
        membershipSha256=m.candidates.token(ids), occurrenceIDs=ids if len(ids) <= cap else [],
        status='ambiguous_candidates_only' if len(ids) <= cap else 'oversized_not_expanded',
        flags=['unknown_version:version'], equivalenceAsserted=False)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        """Keep all focused checks offline."""
        self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('NETWORK')))

    def prepare(self, rows, blocks, cap=32):
        """Check input preservation for every diagnostic fixture."""
        saved = deepcopy((rows, blocks, SPEC))
        result = m.prepare(iter(rows), blocks, SPEC, cap)
        self.assertEqual((rows, blocks, SPEC), saved)
        return result

    def test_family_classification_ignores_id_prefix(self):
        """Misleading IDs cannot change authoritative source-family classification."""
        rows = [occurrence('github:1', 'publications'), occurrence('github:2', 'hydroshare'),
                occurrence('publications:3', 'github', 'ToolX'), occurrence('hydroshare:4', 'github', 'ToolX')]
        result = self.prepare(rows, [block(['github:1', 'github:2']), block(['publications:3', 'hydroshare:4'], 'ToolX')])
        self.assertEqual(result['summary']['classifications'], dict(cross_family=1, within_family=1, oversized=0))
        self.assertEqual(result['dossier'][0]['sourceFamilyDistribution'], {'hydroshare': 1, 'publications': 1})
        self.assertEqual(result['dossier'][0]['occurrenceIDs'], ['github:1', 'github:2'])

    def test_provenance_recovery_and_duplicate_artifacts(self):
        """Repeated documentary origins are counted once without independence claims."""
        rows = [occurrence('a', artifact='shared'), occurrence('b', 'github', artifact='shared')]
        d = self.prepare(rows, [block(['a', 'b'])])['dossier'][0]
        self.assertEqual(d['distinctSupportingArtifactCount'], 1)
        member = d['members'][0]
        self.assertEqual(member['occurrenceReference']['occurrenceSha256'], m.candidates.token(rows[0]))
        self.assertEqual(member['originalProvenance']['selected'][0]['value'], rows[0]['nativeReferences'][0])
        self.assertEqual(member['originalProvenance']['selected'][0]['reference']['jsonPointer'], '/nativeReferences/0')
        self.assertEqual(member['sourceArtifacts'], ['shared'])

    def test_identifier_scopes_stay_separate(self):
        """Global-field and source-local declarations never become equivalence decisions."""
        rows = [occurrence('a'), occurrence('b', 'github')]
        rows[0]['identifierDeclarations'] = [dict(scheme='doi', value='10.1234/x', basis='deterministic_entity_own_field')]
        rows[1]['identifierDeclarations'] = [dict(scheme='literal_exactIdentifier', value='10.1234/x', basis='accepted_source_local_candidate', scope='source_local_no_global_equivalence', evidenceBound=True)]
        rows[1]['declaredExistingNodeIDs'] = ['request-local-node']
        d = self.prepare(rows, [block(['a', 'b'])])['dossier'][0]
        self.assertEqual(d['members'][0]['identifierScopeCounts'], {'deterministic_entity_own_identifier': 1})
        self.assertEqual(d['members'][1]['identifierScopeCounts'], {'source_local_literal_declaration': 1})
        self.assertEqual(d['members'][1]['identifierDeclarations']['value'], rows[1]['identifierDeclarations'])
        self.assertEqual(d['members'][1]['declaredExistingNodeIDs']['value'], ['request-local-node'])
        self.assertFalse(d['equivalenceAsserted'])

    def test_literal_identifier_block_mechanism(self):
        """A literal-declaration block retains its mechanism and local scope."""
        rows = [occurrence('a'), occurrence('b', 'github')]
        for r in rows:
            r.update(lane='identity_declaration', ontologyClass='Paper', inventoryId='A-P01')
            r['identifierDeclarations'] = [dict(scheme='literal_exactIdentifier', value='10.1234/x', basis='accepted_source_local_candidate', evidenceBound=True)]
        b = block(['a', 'b'], key=['identifier_declaration_only', 'Paper', 'literal_exactIdentifier', '10.1234/x'])
        d = self.prepare(rows, [b])['dossier'][0]
        self.assertEqual(d['candidateMechanism'], 'identifier_declaration_only')
        self.assertTrue(all(r['identifierScopeCounts'] == {'source_local_literal_declaration': 1} for r in d['members']))

    def test_generic_specific_missing_and_flags(self):
        """Shared LSTM labels preserve generic/trained context and unknown identity."""
        rows = [occurrence('a'), occurrence('b', 'github')]
        rows[0]['contextualDescriptions'] = ['Generic LSTM architecture']
        rows[1]['contextualDescriptions'] = ['Specific LSTM trained on basin A']
        rows[1]['versions'] = {'version': 'v2'}
        b = block(['a', 'b']); b['flags'].append('explicit_version_conflict:version')
        d = self.prepare(rows, [b])['dossier'][0]
        self.assertIn('versions', d['members'][0]['missingInformation'])
        self.assertEqual(d['members'][1]['versions']['value'], {'version': 'v2'})
        self.assertEqual(d['existingBlockFlags'], b['flags'])
        self.assertTrue(all(r['identityDecision'] == 'not_assessed' for r in d['members']))
        self.assertEqual(d['members'][1]['contextualDescriptions']['value'], rows[1]['contextualDescriptions'])

    def test_bounded_evidence_and_full_recovery(self):
        """Excerpt omission is explicit and every chosen record resolves exactly."""
        rows = [occurrence('a'), occurrence('b', 'github')]
        rows[0]['evidenceReferences'] = [dict(evidenceText=letter * 2000, sourceLocation='line:' + letter) for letter in 'dcba']
        rows[0]['attributes']['technicalDescription'] = 'x' * 5000
        rows[0]['nativeReferences'] *= 5
        r = self.prepare(rows, [block(['a', 'b'])])['dossier'][0]['members'][0]
        self.assertEqual(r['evidenceSelection']['omitted'], 2)
        self.assertTrue(r['attributes']['truncated'])
        self.assertLessEqual(len(r['attributes']['canonicalJsonExcerpt']), m.FIELD_CHARS)
        self.assertEqual(r['originalProvenance']['omitted'], 2)
        for e in r['evidenceExcerpts']:
            index = int(e['reference']['jsonPointer'].split('/')[-1])
            original = rows[0]['evidenceReferences'][index]
            self.assertEqual(e['evidenceSha256'], m.candidates.token(original))
            self.assertEqual(e['excerpt'], original['evidenceText'][:600])
            self.assertTrue(e['truncated'])
        self.assertNotIn('originalSnapshotRecord', r)

    def test_oversized_complete_reconstruction(self):
        """Oversized diagnostics verify all members without pairs or subsets."""
        rows = [occurrence(str(i), 'github' if i == 0 else 'publications', artifact='shared') for i in range(4)]
        b = block([r['occurrenceID'] for r in rows], cap=3)
        result = self.prepare(rows, [b], 3)
        self.assertFalse(result['dossier'])
        o = result['oversized'][0]
        self.assertEqual(o['memberCount'], 4)
        self.assertEqual(o['sourceFamilyDistribution'], {'github': 1, 'publications': 3})
        self.assertEqual(o['membershipSha256'], b['membershipSha256'])
        self.assertEqual(o['distinctSupportingArtifactCount'], 1)
        self.assertNotIn('occurrenceIDs', o)
        self.assertFalse(o['subsetsSelected'])
        bad = deepcopy(b); bad['membershipSha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_HASH_DRIFT'):
            self.prepare(rows, [bad], 3)

    def test_duplicate_missing_and_inconsistent_membership(self):
        """Partial or contradictory membership never produces a dossier."""
        rows = [occurrence('a'), occurrence('b', 'github')]; b = block(['a', 'b'])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_OCCURRENCE_ID'):
            self.prepare(rows + [rows[0]], [b])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_BLOCK'):
            self.prepare(rows, [b, b])
        with self.assertRaisesRegex(ValueError, 'BLOCK_SET_MEMBERSHIP_DRIFT'):
            self.prepare(rows[:1], [b])
        for field, value, reason in [('occurrenceIDs', ['a', 'a'], 'DUPLICATE_BLOCK_MEMBER'),
                                     ('memberCount', 3, 'MEMBER_COUNT_DRIFT'),
                                     ('occurrenceIDs', ['a', 'missing'], 'BLOCK_MEMBERSHIP_DRIFT')]:
            bad = dict(b, **{field: value})
            with self.assertRaisesRegex(ValueError, reason):
                self.prepare(rows, [bad])
        with self.assertRaisesRegex(ValueError, 'BLOCK_SET_MEMBERSHIP_DRIFT'):
            self.prepare(rows, [])

    def test_authoritative_multi_family_and_missing_provenance(self):
        """One multi-family record retains exact set counts; missing origins fail."""
        rows = [occurrence('a'), occurrence('b')]
        rows[0]['sourceFamilies'] = ['github', 'publications']
        d = self.prepare(rows, [block(['a', 'b'])])['dossier'][0]
        self.assertEqual(d['sourceFamilyDistribution'], {'github': 1, 'publications': 2})
        self.assertEqual(d['sourceFamilySetDistribution'], {'github|publications': 1, 'publications': 1})
        rows[1]['sourceFamilies'] = []
        with self.assertRaisesRegex(ValueError, 'MISSING_MEMBER_PROVENANCE'):
            self.prepare(rows, [block(['a', 'b'])])

    def test_deterministic_ordering_and_coverage(self):
        """Occurrence/block iteration order cannot alter the dossier or coverage."""
        rows = [occurrence('a'), occurrence('b', 'github'), occurrence('c', label='X'), occurrence('d', 'hydroshare', 'X')]
        blocks = [block(['a', 'b']), block(['c', 'd'], 'X')]
        result = self.prepare(rows, blocks)
        self.assertEqual(result, self.prepare(rows[::-1], blocks[::-1]))
        classes = [c for c in result['coverage'] if c['dimension'] == 'class']
        self.assertEqual(classes[0]['blocks'], 2)
        self.assertEqual(classes[0]['distinctSupportingArtifacts'], 4)

    def test_frozen_preparation_contract(self):
        """Reconstruct blocks emitted by the real candidate preparer on a tiny graph."""
        nodes = []
        for i, cls in enumerate(['MLModel', 'MLModel', 'MLModel', 'Person', 'Person']):
            nodes.append(dict(id=str(i), **{'class': cls}, inventoryId='A-DOM03d' if cls == 'MLModel' else 'A-AG01',
                attributes={'label': 'LSTM'} if cls == 'MLModel' else {'orcid': '0000-0002-1825-0097'},
                curationStatus='referenced', internalLineage={'localPaperId': str(i)} if i % 2 else {},
                evidence={'sourceArtifact': 'paper:' + str(i) if i % 2 else 'hydroshare:' + str(i), 'evidenceText': 'original'}))
        prepared = m.candidates.prepare(dict(nodes=nodes, edges=[]), [], SPEC, max_block=2)
        result = self.prepare(prepared['records'], prepared['blocks'], cap=2)
        self.assertEqual(result['summary']['classifications'], dict(cross_family=1, within_family=0, oversized=1))
        self.assertEqual(result['dossier'][0]['candidateMechanism'], 'identifier_declaration_only')

    def fixture_files(self, root: Path) -> dict:
        """Build an on-disk synthetic input manifest using only existing small authorities."""
        root.mkdir(parents=True)
        rows = [occurrence('a'), occurrence('b', 'github')]
        for name, values in [('occurrences.jsonl', rows), ('candidate-blocks.jsonl', [block(['a', 'b'])])]:
            (root / name).write_bytes(b''.join(m.encoded(v) + b'\n' for v in values))
        manifest = dict(version=m.candidates.VERSION, candidatePreparationOnly=True, equivalencesAsserted=0, maxBlockSize=32,
            coverage=dict(preparedOccurrences=2, blockStatuses={'ambiguous_candidates_only': 1}),
            outputHashes={name: m.sha(root / name) for name in ('occurrences.jsonl', 'candidate-blocks.jsonl')},
            implementationHashes={p: m.sha(Path(p)) for p in ('src/evaluation/step14_semantic_candidates.py', 'src/evaluation/step14_identity_preview.py')},
            inputHashes={p: m.sha(Path(p)) for p in ('src/ontology/ontology_spec.yaml', 'src/ontology/ciroh_ontology.owl')})
        (root / 'manifest.json').write_bytes(m.encoded(manifest))
        return manifest

    def test_input_hash_verification_and_missing_file(self):
        """Missing files and byte drift are rejected by the production reader."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'; self.fixture_files(root)
            m.verify_inputs(root)
            path = root / 'occurrences.jsonl'; path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'INPUT_HASH_DRIFT'):
                m.verify_inputs(root)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                m.verify_inputs(root)

    def test_writer_reproducibility_preservation_and_boundaries(self):
        """Run only tiny fixtures through real IO; hashes and source bytes stay stable."""
        base = Path('var/study2_step14/semantic-review'); base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as directory:
            root = Path(directory) / 'input'; self.fixture_files(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            a = Path(directory) / 'a'; b = Path(directory) / 'b'
            result = m.run(root, a); m.run(root, b)
            self.assertEqual(result['summary']['classifications']['cross_family'], 1)
            self.assertEqual(sorted(p.name for p in a.iterdir()), ['manifest.json', 'oversized-summary.jsonl', 'report.md', 'review-dossier.jsonl'])
            for p in a.iterdir():
                self.assertEqual(p.read_bytes(), (b / p.name).read_bytes())
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            with self.assertRaisesRegex(ValueError, 'OUTPUT_ALREADY_EXISTS'):
                m.run(root, a)
            with self.assertRaisesRegex(ValueError, 'REVIEW_OUTPUT_REQUIRED'):
                m.run(root, Path('/private/tmp/step14-review-outside'))
            (root / 'candidate-blocks.jsonl').write_text('changed')
            c = Path(directory) / 'c'
            with self.assertRaisesRegex(ValueError, 'INPUT_HASH_DRIFT'):
                m.run(root, c)
            self.assertFalse(c.exists())


if __name__ == '__main__':
    unittest.main()
