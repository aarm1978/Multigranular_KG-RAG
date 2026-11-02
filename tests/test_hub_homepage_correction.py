"""Narrow homepage-target exclusion for the unaccepted Hub reference candidate."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from src.extraction.deterministic import extract_ciroh_hub as hub
from src.evaluation.build_cumulative_snapshot import build_cumulative_snapshot
from src.evaluation.compute_structural_metrics import build_results_record, render_trajectory_markdown
from test_extract_ciroh_hub import make_page, make_link, make_corpus
from test_reference_enrichment import set_content

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/reference_enrichment'
AFFECTED = {
    'data/interim/documents/ciroh_hub_nodes_edges_refs_v1.json',
    'data/interim/evaluation/hydroshare_github_hub_deterministic_refs_v1.json',
    'data/interim/evaluation/hydroshare_github_hub_publications_deterministic_refs_v1.json',
}


def record_hash(records: list[dict]) -> str:
    """Use the fixture's canonical serialization for exact record preservation."""
    return hashlib.sha256((json.dumps(records, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()).hexdigest()


class HomepageRuleTests(unittest.TestCase):
    """Exclude homepage aliases without excluding links from the homepage."""

    def test_homepage_aliases_abstain_and_original_links_survive(self) -> None:
        """Slashless, slash and fragment roots are excluded while document links remain."""
        roots = ['https://hub.ciroh.org', '/', '/#section']
        raw = roots + ['/docs/target']
        links = [make_link(i, target, target if target.startswith('https:') else 'https://hub.ciroh.org' + target,
                           'hub_internal', i, anchor_text='guide') for i, target in enumerate(raw, 1)]
        source = make_page('https://hub.ciroh.org/docs/source', 'docs/source.mdx', 'docs/source.mdx', links=links)
        set_content(source, '\n'.join(f'Please consult this [guide]({target}) for further details.' for target in raw))
        home = make_page('https://hub.ciroh.org/', 'home.mdx', 'home.mdx')
        target = make_page('https://hub.ciroh.org/docs/target', 'docs/target.mdx', 'docs/target.mdx')
        corpus = make_corpus([source, home, target])
        for base_url in ['https://hub.ciroh.org', 'https://hub.ciroh.org/']:
            corpus['source']['base_url'] = base_url
            old = hub.extract_corpus(corpus)
            new = hub.extract_corpus(corpus, enrich_references=True)
            self.assertEqual(new['nodes'], old['nodes'])
            self.assertEqual([e for e in new['edges'] if e['inventoryId'] != 'C-DC22'], old['edges'])
            refs = [e for e in new['edges'] if e['inventoryId'] == 'C-DC22']
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0]['target'], hub.make_page_id(target['canonical_url']))
            self.assertEqual(sum(r['reason'] == 'reference_enrichment_homepage_target' for r in new['skipped']), 3)

    def test_homepage_can_still_reference_document(self) -> None:
        """The correction is target-only and derives identity from the corpus base."""
        target = make_page('https://hub.ciroh.org/docs/target', 'docs/target.mdx', 'docs/target.mdx')
        home = make_page('https://hub.ciroh.org/', 'home.mdx', 'home.mdx', links=[
            make_link(1, '/docs/target', target['canonical_url'], 'hub_internal', 1, anchor_text='guide')])
        set_content(home, 'Please consult the [guide](/docs/target) for detailed instructions.')
        corpus = make_corpus([home, target])
        output = hub.extract_corpus(corpus, enrich_references=True)
        self.assertEqual(len([e for e in output['edges'] if e['inventoryId'] == 'C-DC22']), 1)
        changed_base = copy.deepcopy(corpus)
        changed_base['source']['base_url'] = 'https://hub.ciroh.org/subsite/'
        self.assertEqual(hub.hub_homepage_url(changed_base), 'https://hub.ciroh.org/subsite/')


@unittest.skipUnless(hub.DEFAULT_INPUT.exists(), 'Local Hub corpus unavailable')
class HubCorrectionIntegrationTests(unittest.TestCase):
    """Compare with the prior candidate without rebuilding unaffected source modules."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the pinned prior evidence and build only Hub in memory."""
        cls.fixture = json.loads((FIXTURES / 'hub_homepage_correction_v1.json').read_text())
        cls.corpus, cls.source_hash = hub.load_corpus(hub.DEFAULT_INPUT)
        cls.new = hub.extract_corpus(cls.corpus, cls.source_hash, enrich_references=True)

    def test_only_three_homepage_edges_removed(self) -> None:
        """Every original node and retained edge, including H1/H3-H7, is identical."""
        self.assertEqual(len(self.fixture['removedEdges']), 3)
        self.assertEqual(record_hash(self.new['nodes']), self.fixture['expectedNodesSha256'])
        self.assertEqual(record_hash(self.new['edges']), self.fixture['expectedRetainedEdgesSha256'])
        self.assertEqual(len(self.new['nodes']), 4667)
        self.assertEqual(len(self.new['edges']), 6644)
        self.assertEqual(sum(e['inventoryId'] == 'C-DC22' for e in self.new['edges']), 91)
        ids = {e['id'] for e in self.new['edges']}
        for edge in self.fixture['removedEdges']:
            self.assertNotIn(edge['id'], ids)

    def test_validator_rejects_reintroduced_homepage_edges(self) -> None:
        """Previously eligible exact source evidence cannot bypass the new target rule."""
        bad = copy.deepcopy(self.new)
        bad['edges'].extend(self.fixture['removedEdges'])
        issues = hub.validate_page_reference_evidence(bad, self.corpus)
        self.assertEqual(len(issues), 3)
        self.assertTrue(all('(homepage target)' in issue for issue in issues))

    def test_hub_repeated_build_is_byte_identical(self) -> None:
        """Only Hub is rerun; the unaffected source graphs are never regenerated."""
        second = hub.extract_corpus(copy.deepcopy(self.corpus), self.source_hash, enrich_references=True)
        self.assertEqual(hub.serialize_deterministically(self.new), hub.serialize_deterministically(second))

    def test_historical_and_unaffected_inputs_preserved(self) -> None:
        """Accepted inputs, frozen artifacts and the unaffected cumulative point stay pinned."""
        hashes = json.loads((FIXTURES / 'pre_enrichment_hashes.json').read_text())
        hashes.update({p: sha for p, sha in self.fixture['priorProspectiveHashes'].items() if p not in AFFECTED})
        for path, digest in hashes.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

    def test_saved_graphs_metrics_and_trajectory(self) -> None:
        """Saved prospective artifacts match current hashes and unchanged generation formulas."""
        self.assertEqual(json.loads(hub.DEFAULT_OUTPUT.read_text()), self.new)
        for path, digest in json.loads((FIXTURES / 'prospective_hashes.json').read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        records = []
        for path in sorted((ROOT / 'results/metrics/snapshots').glob('*.json')):
            record = json.loads(path.read_text())
            input_path = ROOT / record['input']['path']
            graph = json.loads(input_path.read_text())
            if str(input_path.relative_to(ROOT)) in AFFECTED:
                self.assertEqual(graph, build_cumulative_snapshot([(c['label'], ROOT / c['path']) for c in graph['components']]))
                self.assertEqual(record, build_results_record(graph, input_path, record['label'], record['displayName'], record['trajectoryOrder'], 'mentionCount', 'pre_consolidation'))
            records.append(record)
        records.sort(key=lambda r: r['trajectoryOrder'])
        self.assertEqual((ROOT / 'results/metrics/trajectory.md').read_text(), render_trajectory_markdown(records))
        record = json.loads((ROOT / 'results/metrics/modules/ciroh_hub_deterministic.json').read_text())
        self.assertEqual(record, build_results_record(self.new, hub.DEFAULT_OUTPUT, record['label'], record['displayName'], record['trajectoryOrder'], 'mentionCount', 'pre_consolidation', 'module'))


if __name__ == '__main__':
    unittest.main()
