"""Synthetic tests for the one-off offline diagnostic, not alignment decisions."""
import copy
import unittest
from scripts.diagnostics import step14_scale_bottleneck as d


class DiagnosticTests(unittest.TestCase):
    """Protect set counting, overlap semantics and evidence limitations."""

    def group(self, ids, originals=1):
        """Build a complete saved scope."""
        return dict(occurrenceIDs=ids,originalGroupIDs=list(range(originals)))

    def test_subset_partial_duplicate_are_separate(self):
        """Different overlap forms coexist without authorizing their union."""
        groups=[self.group(['a','b'],2),self.group(['a','b']),self.group(['a','b','c']),self.group(['b','d'])]
        before=copy.deepcopy(groups);result=d.component_shapes(groups)
        self.assertEqual(result['duplicateScopes'],1)
        self.assertEqual(result['duplicateOriginalProposals'],1)
        self.assertEqual(result['properSubsetSupersetPairs'],2)
        self.assertTrue(result['hasPartialOverlap'])
        self.assertEqual(result['distinctOccurrences'],4)
        self.assertEqual(groups,before)

    def test_singleton_and_subset_only(self):
        """A singleton component is one proposal, not one occurrence."""
        result=d.component_shapes([self.group(['a','b'])])
        self.assertEqual(result['groups'],1);self.assertEqual(result['distinctOccurrences'],2)
        self.assertFalse(result['hasPartialOverlap'])
        result=d.component_shapes([self.group(['a','b']),self.group(['a','b','c'])])
        self.assertEqual(result['properSubsetSupersetPairs'],1)
        self.assertFalse(result['hasPartialOverlap'])

    def test_text_presence_not_semantic_support(self):
        """A detector hold with quotations is distinct from missing selected evidence."""
        endpoint=dict(labels=['NWM'],selectedEvidence=[dict(literalExcerpt='NWM uses a trained implementation.')])
        f=d.endpoint_features(endpoint,{})
        record=dict(category='same_entity_candidate',assessment={'missingInformation':['version unknown']})
        flags=d.pair_flags(f,f,record,'held')
        self.assertIn('quotations_present_detector_did_not_establish_broader_support',flags)
        self.assertIn('matching_names_without_explicit_version_cues',flags)
        self.assertIn('related_but_distinct_language_cue_not_judgment',flags)
        empty=d.endpoint_features(dict(labels=[],selectedEvidence=[]),{})
        self.assertIn('selected_quotation_missing_one_or_both',d.pair_flags(empty,f,record,'held'))

    def test_local_identifier_never_becomes_owned(self):
        """Keep local declaration presence separate from verified ownership."""
        endpoint=dict(labels=['X'],selectedEvidence=[])
        member=dict(identifierDeclarations=[dict(scheme='doi',value='one',basis='accepted_source_local_candidate')])
        f=d.endpoint_features(endpoint,member)
        self.assertTrue(f['declarations']);self.assertEqual(f['own'],set())

if __name__=='__main__':unittest.main()
