"""Prospective C-C27/C-DC22 evidence gates and preserved historical boundaries."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.extraction.deterministic import extract_github as gh, extract_ciroh_hub as hub
from src.evaluation.build_cumulative_snapshot import build_cumulative_snapshot
from src.evaluation.compute_structural_metrics import (
    build_results_record, render_trajectory_markdown, validate_snapshot,
)
from test_extract_github import make_repo, make_corpus as github_corpus, vcs_dependency, software_metadata_record
from test_extract_ciroh_hub import make_page, make_link, make_corpus as hub_corpus

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'results/metrics/history/pre_reference_enrichment_v1'
FIXTURES = ROOT / 'tests/fixtures/reference_enrichment'


def readme(repo: dict, text: str, urls: list[str]) -> None:
    """Attach exact Phase A README evidence without any acquisition."""
    repo['readme'].update(present=True, source_path='README.md', text=text)
    repo['readme']['deterministic_urls']['github'] = urls


def reference_edges(output: dict, inventory: str) -> list[dict]:
    """Select only the newly authorized reference branch."""
    return [e for e in output['edges'] if e['inventoryId'] == inventory]


def set_content(page: dict, text: str) -> None:
    """Set matching source content and hashes in a synthetic Hub page."""
    page['content_mdx'] = text
    page['content_sha256'] = page['file_sha256'] = hashlib.sha256(text.encode()).hexdigest()


class GithubReferenceTests(unittest.TestCase):
    """Eligibility, identity, evidence and stronger-role precedence for C-C27."""

    def test_curated_identity_exact_evidence_and_duplicate_suppression(self) -> None:
        """Repeated/case-varied URLs retain every occurrence on one curated pair."""
        a, b = make_repo(1, 'source'), make_repo(2, 'target')
        url = b['html_url']
        raw = url.replace('example', 'EXAMPLE')
        readme(a, f'See [target]({raw}).\nAgain [target]({url}).\nAgain [target]({url}).', [url, raw])
        corpus = github_corpus(a, b)
        output = gh.extract_corpus(corpus, enrich_references=True)
        edges = reference_edges(output, 'C-C27')
        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual((edge['source'], edge['target']), ('github:repo:1', 'github:repo:2'))
        declarations = edge['attributes']['sourceDeclarations']
        self.assertEqual(len(declarations), 3)
        self.assertEqual({d['rawTarget'] for d in declarations}, {raw, url})
        self.assertIn('/blob/' + a['archive']['frozen_commit_sha'] + '/README.md', edge['evidence']['sourceLocation'])
        self.assertEqual(edge['evidence']['version'], a['archive']['frozen_commit_sha'])
        self.assertTrue(gh.validate_output(output, corpus))  # historical prohibition survives
        self.assertEqual(gh.validate_output(output, corpus, True), [])
        broken = copy.deepcopy(output)
        reference_edges(broken, 'C-C27')[0]['attributes']['sourceDeclarations'][0]['rawTarget'] = 'https://github.com/other/fake'
        self.assertTrue(gh.validate_output(broken, corpus, True))

    def test_external_stubs_are_source_scoped(self) -> None:
        """External roots reuse within a source, never unify independent sources."""
        a, b = make_repo(1, 'a'), make_repo(2, 'b')
        url = 'https://github.com/Other/External'
        for repo in (a, b):
            readme(repo, f'Please see [code]({url}).', [url])
        output = gh.extract_corpus(github_corpus(a, b), enrich_references=True)
        edges = reference_edges(output, 'C-C27')
        self.assertEqual(len(edges), 2)
        self.assertEqual(len({e['target'] for e in edges}), 2)
        targets = [n for n in output['nodes'] if n['id'] in {e['target'] for e in edges}]
        self.assertEqual({n['curationStatus'] for n in targets}, {'referenced'})
        self.assertEqual({n['inventoryId'] for n in targets}, {'A-C01'})

    def test_excluded_urls_badges_missing_evidence_and_code(self) -> None:
        """Non-roots, self URLs, forged declarations, badges and code abstain."""
        a = make_repo(1, 'a')
        invalid = ['https://github.com/o/r/issues/1', 'https://github.com/o/r/pull/1',
                   'https://github.com/o/r/actions', 'https://github.com/o/r/blob/main/a.py',
                   'https://github.com/user-attachments/assets/123', 'https://github.com/o/r?tab=readme',
                   'https://github.com/o/r%2Fx', 'https://github.com/search/code', a['html_url']]
        roots = ['https://github.com/o/badge', 'https://github.com/o/absent', 'https://github.com/o/code']
        text = '\n'.join(invalid) + f'\n[![build](badge.svg)]({roots[0]})\n```\n{roots[2]}\n```'
        readme(a, text, invalid + roots)
        self.assertEqual(reference_edges(gh.extract_corpus(github_corpus(a), True), 'C-C27'), [])

    def test_dependencies_and_implementation_take_precedence(self) -> None:
        """No generic association duplicates dependency or owned-tool implementation."""
        a = make_repo(1, 'a')
        dep, implementation = 'https://github.com/Other/Dep', 'https://github.com/Other/Impl'
        a['repo_dependencies'] = [vcs_dependency(dep, None, None)]
        software = software_metadata_record('Tool', 'pyproject.toml', None)
        software['urls'] = {'repository': implementation}
        a['software_metadata'] = [software]
        readme(a, f'See [dependency]({dep}) and [implementation]({implementation}).', [dep, implementation])
        output = gh.extract_corpus(github_corpus(a), True)
        self.assertEqual(reference_edges(output, 'C-C27'), [])
        self.assertEqual(sum(r['reason'] == 'reference_enrichment_stronger_relation' for r in output['skipped']), 2)

    def test_validator_uses_correct_source_scoped_dependency(self) -> None:
        """A README stub in another source cannot hide an existing dependency target."""
        a, b = make_repo(1, 'a'), make_repo(2, 'b')
        url = 'https://github.com/Other/Shared'
        readme(a, f'See [source]({url}).', [url])
        b['repo_dependencies'] = [vcs_dependency(url, None, None)]
        corpus = github_corpus(a, b)
        output = gh.extract_corpus(corpus, True)
        self.assertEqual(len(reference_edges(output, 'C-C27')), 1)
        self.assertEqual(gh.validate_output(output, corpus, True), [])


class HubReferenceTests(unittest.TestCase):
    """Exact page occurrence gates and evidence retention for C-DC22."""

    def fixture(self, lines: list[str], targets: list[str] | None = None) -> dict:
        """Build linked source and target curated pages."""
        targets = targets or ['/docs/target'] * len(lines)
        links = [make_link(i, raw, 'https://hub.ciroh.org' + raw, 'hub_internal', i, anchor_text='guide')
                 for i, raw in enumerate(targets, 1)]
        source = make_page('https://hub.ciroh.org/docs/source', 'docs/source.mdx', 'docs/source.mdx', links=links)
        set_content(source, '\n'.join(lines))
        target = make_page('https://hub.ciroh.org/docs/target', 'docs/target.mdx', 'docs/target.mdx')
        return hub_corpus([source, target])

    def test_curated_pair_preserves_occurrences_and_original_graph(self) -> None:
        """A pair edge retains raw target, anchor, line, ordinal and content hash."""
        corpus = self.fixture(['Please consult the [guide](/docs/target) for details.',
                               'Additional details are in the [guide](/docs/target#section).'],
                              ['/docs/target', '/docs/target#section'])
        old, new = hub.extract_corpus(corpus), hub.extract_corpus(corpus, enrich_references=True)
        edge = reference_edges(new, 'C-DC22')[0]
        self.assertEqual(len(reference_edges(new, 'C-DC22')), 1)
        self.assertEqual(new['nodes'], old['nodes'])
        self.assertTrue(all(e in new['edges'] for e in old['edges']))
        declarations = edge['attributes']['sourceDeclarations']
        self.assertEqual([d['sourceOrdinal'] for d in declarations], [1, 2])
        self.assertEqual([d['sourceLine'] for d in declarations], [1, 2])
        self.assertEqual(declarations[1]['rawTarget'], '/docs/target#section')
        self.assertEqual(declarations[0]['anchorText'], 'guide')
        self.assertEqual(edge['evidence']['version'], corpus['pages'][0]['content_sha256'])
        self.assertTrue(hub.validate_output(new, corpus))
        self.assertEqual(hub.validate_output(new, corpus, enrich_references=True), [])
        broken = copy.deepcopy(new)
        reference_edges(broken, 'C-DC22')[0]['attributes']['sourceDeclarations'][0]['sourceLine'] = 99
        self.assertTrue(hub.validate_output(broken, corpus, enrich_references=True))

    def test_navigation_missing_code_and_excluded_targets_abstain(self) -> None:
        """Standalone navigation, missing routes, query targets and code yield no edge."""
        lines = ['[guide](/docs/target)', 'Please consult the [guide](/missing) for details.',
                 'Please consult the [guide](/publications) for details.',
                 'Please consult the [guide](/docs/target?x=1) for details.',
                 '    Please consult the [guide](/docs/target) for details.',
                 'Please consult the [guide](/docs/source) for details.']
        corpus = self.fixture(lines, ['/docs/target', '/missing', '/publications', '/docs/target?x=1', '/docs/target', '/docs/source'])
        new = hub.extract_corpus(corpus, enrich_references=True)
        self.assertEqual(reference_edges(new, 'C-DC22'), [])
        self.assertEqual(new['nodes'], hub.extract_corpus(corpus)['nodes'])

    def test_parent_and_announcement_take_precedence(self) -> None:
        """Existing page hierarchy and release-note announcements remain sole semantics."""
        corpus = self.fixture(['Please consult the [guide](/docs/target) for details.'])
        corpus['pages'][0]['parent_url'] = corpus['pages'][1]['canonical_url']
        corpus = hub_corpus(corpus['pages'])
        self.assertEqual(reference_edges(hub.extract_corpus(corpus, enrich_references=True), 'C-DC22'), [])
        corpus['pages'][0]['parent_url'] = None
        corpus['pages'][0]['canonical_url'] = 'https://hub.ciroh.org/release-notes/test'
        corpus['pages'][0]['source_group'] = 'release_notes'
        corpus['pages'][0]['corpus_path'] = 'release-notes/test.mdx'
        corpus['pages'][0]['source_path'] = 'release-notes/test.mdx'
        corpus = hub_corpus(corpus['pages'])
        output = hub.extract_corpus(corpus, enrich_references=True)
        self.assertTrue(any(e['relation'] == 'announces' for e in output['edges']))
        self.assertEqual(reference_edges(output, 'C-DC22'), [])


class PreservationTests(unittest.TestCase):
    """Frozen artifacts and prospective schema versions stay distinct."""

    def test_frozen_output_paths_are_write_protected(self) -> None:
        """No profile can overwrite either accepted unsuffixed source graph."""
        for module in (gh, hub):
            with self.assertRaisesRegex(ValueError, 'Frozen'):
                module.write_output({}, module.HISTORICAL_OUTPUT)

    def test_historical_and_phase_a_hashes(self) -> None:
        """Compare byte hashes of preserved graphs, corpora, ontology and metric archive."""
        for path, expected in json.loads((FIXTURES / 'pre_enrichment_hashes.json').read_text()).items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected)

    def test_ontology_inventory_bindings(self) -> None:
        """Only already-frozen v0.1.6 branches are activated; no reasoning run."""
        registry = hub.load_ontology_registry()
        self.assertEqual(registry.version, '0.1.6')
        for inventory, name, cls in [('C-C27', 'referencesRepository', 'Repository'), ('C-DC22', 'references', 'DocumentationPage')]:
            record = registry.relations_by_id[inventory]
            self.assertEqual((record['name'], record['domain'], record['range']), (name, cls, cls))


@unittest.skipUnless(gh.DEFAULT_INPUT.exists() and hub.DEFAULT_INPUT.exists(), 'Local Phase A corpora unavailable')
class CorpusIntegrationTests(unittest.TestCase):
    """Bounded full-corpus additive delta and deterministic generation checks."""

    @classmethod
    def setUpClass(cls) -> None:
        """Extract prospective sources in memory once for integration assertions."""
        cls.outputs = {}
        for module in (gh, hub):
            corpus = json.loads(module.DEFAULT_INPUT.read_text())
            if module is hub:
                cls.outputs[module.SOURCE_TYPE] = module.extract_corpus(corpus, source_corpus_sha256=hashlib.sha256(module.DEFAULT_INPUT.read_bytes()).hexdigest(), enrich_references=True)
            else:
                cls.outputs[module.SOURCE_TYPE] = module.extract_corpus(corpus, enrich_references=True)

    def test_additive_only_source_graph_delta(self) -> None:
        """Every preexisting node/edge remains byte-value identical; only allowed additions."""
        for module in (gh, hub):
            old = json.loads(module.HISTORICAL_OUTPUT.read_text())
            new = self.outputs[module.SOURCE_TYPE]
            for kind in ('nodes', 'edges'):
                new_by_id = {r['id']: r for r in new[kind]}
                for r in old[kind]:
                    self.assertEqual(new_by_id[r['id']], r)
                old_ids = {x['id'] for x in old[kind]}
                added = [r for r in new[kind] if r['id'] not in old_ids]
                if kind == 'nodes':
                    self.assertTrue(all(module is gh and r['class'] in {'Repository', 'Identifier'} for r in added))
                else:
                    self.assertTrue(all(r['inventoryId'] in ({'C-C27', 'C-C06'} if module is gh else {'C-DC22'}) for r in added))
            validate_snapshot(new)

    def test_cli_repeated_bytes_and_cumulative_integrity(self) -> None:
        """Two CLI builds per source and a temporary coordinated graph remain deterministic."""
        with tempfile.TemporaryDirectory() as directory:
            components = [('hydroshare', ROOT / 'data/interim/datasets/hydroshare_nodes_edges_v016.json'),
                          ('publications', ROOT / 'data/interim/papers/publication_nodes_edges.json')]
            for module in (gh, hub):
                paths = [Path(directory) / (module.SOURCE_TYPE + str(i) + '.json') for i in range(2)]
                for path in paths:
                    subprocess.run([sys.executable, '-B', '-m', module.__name__, '--enrich-references', '--out', str(path)], cwd=ROOT, check=True, capture_output=True)
                self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
                self.assertEqual(json.loads(paths[0].read_text()), self.outputs[module.SOURCE_TYPE])
                components.append((module.SOURCE_TYPE, paths[0]))
            combined = build_cumulative_snapshot(components)
            validate_snapshot(combined)
            self.assertEqual(len(combined['nodes']), sum(len(json.loads(p.read_text())['nodes']) for _, p in components))
            self.assertEqual(len(combined['edges']), sum(len(json.loads(p.read_text())['edges']) for _, p in components))

    @unittest.skipUnless((FIXTURES / 'prospective_hashes.json').exists(), 'Prospective artifacts not yet generated')
    def test_saved_hashes_metrics_and_trajectory(self) -> None:
        """Final persisted graphs and records match unchanged generators and fixed hashes."""
        for path, digest in json.loads((FIXTURES / 'prospective_hashes.json').read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        for module in (gh, hub):
            self.assertEqual(json.loads(module.DEFAULT_OUTPUT.read_text()), self.outputs[module.SOURCE_TYPE])
        records = []
        for series, folder in [('trajectory', 'snapshots'), ('module', 'modules')]:
            for path in sorted((ROOT / 'results/metrics' / folder).glob('*.json')):
                record = json.loads(path.read_text())
                input_path = ROOT / record['input']['path']
                graph = json.loads(input_path.read_text())
                if 'components' in graph:
                    self.assertEqual(graph, build_cumulative_snapshot([(c['label'], ROOT / c['path']) for c in graph['components']]))
                rebuilt = build_results_record(graph, input_path, record['label'], record['displayName'], record['trajectoryOrder'], 'mentionCount', 'pre_consolidation', series)
                self.assertEqual(record, rebuilt)
                if series == 'trajectory':
                    records.append(record)
        records.sort(key=lambda r: r['trajectoryOrder'])
        self.assertEqual((ROOT / 'results/metrics/trajectory.md').read_text(), render_trajectory_markdown(records))


if __name__ == '__main__':
    unittest.main()
