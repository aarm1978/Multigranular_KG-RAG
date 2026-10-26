"""Short synthetic tests only; all sockets blocked, no production analysis."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import semantic_coverage_diagnosis as d


class DiagnosisTests(unittest.TestCase):
    """Protect structural distinctions without rerunning any accepted reader."""

    def setUp(self):
        """Use temporary synthetic authorities and block all sockets."""
        blocker = patch.object(socket, 'socket', side_effect=AssertionError('NO_NETWORK'))
        blocker.start()
        self.addCleanup(blocker.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)

    def authority(self, text):
        """Return a synthetic Hub authority with exact text hash."""
        return dict(path='page', cellIndex=None, text=text, authorityTextSha256=d.sha(text),
                    physicalBytesSha256=None, authorityStatus='snapshot_authority')

    def unit(self, text, start, end, cited=False):
        """Construct recorded coverage, optionally with an exact accepted citation."""
        evidence = dict(sourceUnitID='u', startOffsetInAuthority=start, endOffsetInAuthority=end,
                        evidenceText=text[start:end], authorityTextSha256=d.sha(text))
        return dict(sourceUnitID='u', _span=[start,end], selected=True, selectedRequestIDs=['r'],
                    acceptedEvidenceReferences=[dict(requestID='r', candidateID='c', evidence=evidence)] if cited else [])

    def test_self_closing_marker_does_not_exclude_following_materialized_markdown(self):
        """Selected following prose is reported without inferring component ownership."""
        text = '<GitHubReadme repo="x" />\n\n# Technical documentation\nRun the documented workflow.\n'
        start = text.index('#')
        for cited in (False, True):
            record = d.diagnose('ciroh_hub','owner',dict(reason='uncertain_component_visibility',sourceLine=1),
                                self.authority(text),[self.unit(text,start,len(text),cited)])
            self.assertEqual(record['mechanism'],'self_closing_external_component_marker')
            self.assertEqual(record['componentContext']['pageContextState'],
                '1_materialized_page_text_present_and_selected' if cited else '3_materialized_page_text_selected_but_uncited')
            self.assertEqual(record['componentContext']['componentBoundaryState'],'5_insufficient_component_boundary_evidence')
            self.assertEqual(record['derivedCoordinates']['endOffsetInAuthority'],text.index('\n')+1)
            self.assertNotIn('missing_external_authority',json.dumps(record))

    def test_no_demonstrable_content_is_not_a_claim_of_remote_absence(self):
        """A marker alone yields only a frozen-authority observation."""
        text = '<GitHubWikiPage repo="x" />\n'
        result=d.component_context(text,[0,len(text)],[])
        self.assertEqual(result['pageContextState'],'4_no_materialized_content_demonstrable')
        self.assertIn('insufficient',result['componentBoundaryState'])

    def test_admonition_nested_html_dynamic_and_unclosed_are_distinct(self):
        """Keep line-derived extents separate from unknown rollback boundaries."""
        for text, reason, expected in [
            (':::info[Run]\nTechnical workflow instructions.\n:::\n','uncertain_admonition_visibility','bracket_title_admonition'),
            ('<div class="x"><p>Technical method description.</p></div>\n','uncertain_component_visibility','nested_or_attributed_static_html_candidate'),
            ('{loadRemote()}\n','dynamic_or_runtime_content','dynamic_expression_or_module_declaration')]:
            result=d.diagnose('ciroh_hub','owner',dict(reason=reason,sourceLine=1),self.authority(text),[])
            self.assertEqual(result['mechanism'],expected)
            self.assertEqual(result['originalCoordinates'],{'sourceLine':1})
            self.assertIn('derived',result['derivedCoordinates']['coordinateStatus'])
        result=d.diagnose('ciroh_hub','owner',dict(reason='unclosed_static_wrapper_visibility'),self.authority('<p>\ntext'),[])
        self.assertIsNone(result['derivedCoordinates'])
        self.assertEqual(result['coverageState'],'unmeasurable')
        self.assertEqual(len(d.review_sample([result],12,True)),1)

    def test_github_gates_and_role_other_are_not_conflated(self):
        """Only actual reason/path/content supports structural exclusion labels."""
        for path in ['CHANGELOG.md','CONTRIBUTING.md']:
            label=d.mechanism('github',dict(path=path,reason='content_kind_or_purpose_requires_review'),'A scientific procedure.')
            self.assertTrue(label.startswith('trusted_passage_gate_'))
        self.assertEqual(d.mechanism('github',dict(reason='non_prose_file_type',file_role='other'),'def f():'),
                         'file_selector_non_prose_file_type')
        self.assertEqual(d.mechanism('github',dict(reason='content_kind_or_purpose_requires_review'),
                                     '<p>The model computes streamflow.</p>'),'markup_filtered_prose_candidate')
        self.assertEqual(d.mechanism('github',dict(reason='content_kind_or_purpose_requires_review'),'Copyright all rights reserved.'),
                         'administrative_passage_filter')

    def fixture(self):
        """Write two tiny frozen corpora and a minimal persisted verification report."""
        text='<GitHubReadme repo="x" />\nSelected technical workflow.\n:::info[Details]\nHidden technical detail.\n:::\n'
        page=dict(canonical_url='https://example.test/page',page_key='page',content_mdx=text,
                  content_sha256=d.sha(text),external_content_sources=[dict(component='GitHubReadme',source_line=1)])
        owner='hub:page:'+d.sha(page['canonical_url'])[:20]
        gh=dict(repo_id=1,name='repo',full_name='org/repo',archive={'frozen_commit_sha':'f'*40},
                files={'downloaded':[dict(path='docs/a.md',file_role='other',downloaded=True)]},
                readme={'source_path':'README.md','text':'Repository documentation.'})
        corpora={'github':{'repos':[gh]},'ciroh_hub':{'pages':[page]}}
        pins={}
        for family,path in d.CORPORA.items():
            target=self.repo/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(corpora[family]));pins[path]=d.file_hash(target)
        reports=self.repo/d.REPORTS;reports.mkdir(parents=True)
        (reports/'verification.json').write_text(json.dumps(dict(persistedSourcePins=pins)))
        start=text.index('Selected');end=text.index(':::')
        unit=self.unit(text,start,end,True);unit.pop('_span')
        unit.update(family='ciroh_hub',ownerID=owner,sourceMetadata=dict(page_key='page',authorityTextSha256=d.sha(text),
            startOffsetInAuthority=start,endOffsetInAuthority=end),citedByAcceptedEvidence=True,excluded=False,processingIncomplete=False)
        (reports/'source-unit-coverage.jsonl').write_text(json.dumps(unit)+'\n')
        diagnostics=[dict(recordType='source_diagnostic',family='ciroh_hub',ownerID=owner,
                         record=dict(reason=reason,sourceLine=line,authorityTextSha256=d.sha(text),page_key='page'))
                     for reason,line in [('uncertain_component_visibility',1),('uncertain_admonition_visibility',3)]]
        (reports/'exceptions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in diagnostics))
        return reports,unit

    def test_end_to_end_synthetic_read_only_and_partial_materialization(self):
        """Preserve inputs; report partial page exclusion without repository attribution."""
        reports,_=self.fixture()
        before={p:p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        records,summary=d.analyze(self.repo,reports)
        component=next(r for r in records['ciroh_hub'] if 'componentContext' in r)
        self.assertEqual(component['componentContext']['pageContextState'],'2_materialized_page_text_present_partly_reader_excluded')
        self.assertEqual(records['github'][0]['mechanism'],'file_role_other_not_a_selector_decision')
        self.assertEqual({p:p.read_bytes() for p in before},before)
        with patch.object(d.subprocess,'run') as ignored:
            ignored.return_value.returncode=0
            d.run(self.repo,reports,self.repo/d.OUTPUT)
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):
                d.run(self.repo,reports,self.repo/d.OUTPUT)
        self.assertTrue((self.repo/d.OUTPUT/'github.jsonl').exists())
        self.assertEqual({p:p.read_bytes() for p in before},before)
        self.assertLessEqual(len(summary['examples']),36)
        self.assertLessEqual(len(summary['difficultCases']),12)

    def test_hash_coordinate_and_citation_drift_fail_closed(self):
        """Never rebind altered evidence or bless changed frozen source text."""
        reports,unit=self.fixture()
        unit['acceptedEvidenceReferences'][0]['evidence']['evidenceText']='changed'
        (reports/'source-unit-coverage.jsonl').write_text(json.dumps(unit)+'\n')
        with self.assertRaisesRegex(ValueError,'STORED_EVIDENCE_COORDINATE_DRIFT'):
            d.analyze(self.repo,reports)
        corpus=self.repo/d.CORPORA['ciroh_hub'];corpus.write_text('{}')
        with self.assertRaisesRegex(ValueError,'FROZEN_CORPUS_HASH_DRIFT'):
            d.analyze(self.repo,reports)
        with self.assertRaisesRegex(ValueError,'INVALID_STORED_OFFSETS'):
            d.bounds({'startOffsetInAuthority':0,'endOffsetInAuthority':5},'x')

    def test_deduplicated_spans_and_bounded_diverse_review(self):
        """Overlapping diagnostic occurrences do not multiply affected characters."""
        r=d.diagnose('github','owner',dict(reason='content_kind_or_purpose_requires_review',path='a.md',
            startOffsetInAuthority=0,endOffsetInAuthority=12),self.authority('<p>text</p>\n'),[])
        stats=d.summarize([r,deepcopy(r)])
        count=stats['mechanisms'][r['mechanism']]
        self.assertEqual(count['records'],2)
        self.assertEqual(count['deduplicatedDiagnosticCharacters'],12)
        self.assertEqual(d.merge([[0,3],[2,5],[0,3]]),[[0,5]])
        many=[{**r,'ownerID':str(i)} for i in range(100)]
        self.assertEqual(len(d.review_sample(many,36)),36)

    def test_excluded_reader_units_without_metadata_remain_uncertain(self):
        """Unavailable metadata cannot turn a production exclusion into a reader exclusion."""
        reports,unit=self.fixture()
        missing=dict(unit,sourceUnitID='missing',sourceMetadata=None,selected=False,
                     selectedRequestIDs=[],acceptedEvidenceReferences=[],citedByAcceptedEvidence=False,excluded=True)
        with (reports/'source-unit-coverage.jsonl').open('a') as handle:
            handle.write(json.dumps(missing)+'\n')
        row=dict(recordType='source_diagnostic',family='ciroh_hub',ownerID=unit['ownerID'],
                 record=dict(reason='structural_review',sourceUnitIDs=['missing'],sourceLine=2))
        with (reports/'exceptions.jsonl').open('a') as handle:
            handle.write(json.dumps(row)+'\n')
        records,_=d.analyze(self.repo,reports)
        result=next(r for r in records['ciroh_hub'] if r.get('linkedReaderUnitsWithoutMetadata'))
        self.assertEqual(result['coverageState'],'reader_admitted_metadata_unavailable')
        self.assertEqual(result['unrepresentedInReaderSpans'],[])
        self.assertEqual(d.subtract([0,10],[[2,5],[4,7]]),[[0,2],[7,10]])

    def test_raw_hashes_decode_policy_and_cell_coordinates(self):
        """Keep notebook-cell authority text separate from physical JSON bytes."""
        gh=dict(repo_id=1,name='repo',full_name='org/repo',archive={'frozen_commit_sha':'f'*40},readme={})
        corpora={'github':{'repos':[gh]},'ciroh_hub':{'pages':[]}}
        path=self.repo/'data/raw/coderepos/repo/contents/n.ipynb'
        path.parent.mkdir(parents=True)
        text='Original cell.\r\n'
        path.write_text(json.dumps({'cells':[{'cell_type':'markdown','source':[text]}]}))
        reader=d.Authorities(self.repo,corpora)
        meta=dict(path='n.ipynb',cellIndex=0,authorityTextSha256=d.sha(text),rawFileSha256=d.file_hash(path))
        authority=reader.get('github','github:repo:1',meta)
        self.assertEqual(authority['text'],text)
        self.assertNotEqual(authority['physicalBytesSha256'],authority['authorityTextSha256'])
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_DRIFT'):
            reader.get('github','github:repo:1',{**meta,'rawFileSha256':'bad'})
        with self.assertRaisesRegex(ValueError,'UNSAFE_RAW_PATH'):
            reader.get('github','github:repo:1',dict(path='../escape.md'))


if __name__=='__main__':
    unittest.main()
