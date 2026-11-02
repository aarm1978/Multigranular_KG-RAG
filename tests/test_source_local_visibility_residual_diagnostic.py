"""Focused mechanism-attribution tests, never an acceptance-policy correction."""
import sys
import unittest
from src.evaluation import source_local_visibility_residual_diagnostic as d


class ResidualTests(unittest.TestCase):
    def mechanisms(self,text):
        """Trace unchanged classifier decisions for a small source."""
        marks,writers,events=d.trace_regions(text)
        self.assertEqual(marks,d.classifier.regions(text))
        return {d.mechanism(e,text) for e in events if e['kind']=='uncertain'}

    def test_closed_unsupported_container(self):
        """Static literal attributes are distinguished from expression-valued attributes."""
        self.assertIn('closed_html_unsupported_attributes',self.mechanisms('<div className="container">text</div>'))
        self.assertIn('closed_html_expression_attributes',self.mechanisms('<div className={styles.x}>text</div>'))
        self.assertIn('closed_unknown_component_or_html',self.mechanisms('<Tabs>text</Tabs>'))

    def test_malformed_and_unclosed_are_distinct(self):
        """A backward-reaching unmatched close is not an unclosed known admonition."""
        self.assertIn('mismatched_close_prefix_contamination',self.mechanisms('text\n</invoke>'))
        self.assertIn('unclosed_admonition',self.mechanisms(':::warning\ntext'))
        self.assertIn('unclosed_markup_scope',self.mechanisms('<div>text'))

    def test_markdown_tokens_are_not_actual_open_containers(self):
        """Reproduce both observed Markdown-token scope defects without correcting them."""
        self.assertIn('markdown_autolink_misparsed_as_tag',self.mechanisms('<https://example.test/path>\nLater prose.'))
        self.assertIn('escaped_angle_placeholder_misparsed_as_tag',self.mechanisms(r'log-\<jobid\>.txt'+'\nLater prose.'))

    def test_offset_attribution_and_profile_restoration(self):
        """Original character coordinates and profiler state survive observation."""
        text='before\n</content>\nafter';previous=sys.getprofile()
        marks,writers,events=d.trace_regions(text)
        self.assertIs(sys.getprofile(),previous)
        self.assertEqual(events[writers[0]]['start'],0)
        self.assertEqual(events[writers[0]]['end'],text.index('</content>')+len('</content>'))
        self.assertEqual(marks[-5:],['prose']*5)

    def test_primary_is_exclusive_and_target_specific(self):
        """Mixed Example evidence-form mismatch is not generalized to arbitrary code semantics."""
        self.assertEqual(d.primary(set(),'C-DC12'),'mixed_displayed_example_contract_form')
        self.assertEqual(d.primary(set(),'A-DC05'),'mixed_prose_code_other_target')
        self.assertEqual(d.primary({'unclosed_admonition','mismatched_close_prefix_contamination'},'C-DC12'),
                         'mismatched_close_prefix_contamination')


if __name__=='__main__':unittest.main()
