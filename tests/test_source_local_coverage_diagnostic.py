"""Offline checks of diagnostic provenance, dependency reasoning and visibility signals."""
import copy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.evaluation import source_local_coverage_diagnostic as d


class CoverageDiagnosticTests(unittest.TestCase):
    def test_all_validation_stages_and_simultaneous_reasons_survive(self):
        """Do not substitute final disposition for original evidence and gate findings."""
        native={'originalReplay':{'finalRecords':[{'candidateID':'c',
            'parseDiagnostics':[{'reason':'parse_reason'}]}]}}
        check={'candidateID':'c','findings':[{'reason':'semantic_gates_pending',
            'gates':['g'],'disposition':'unresolved_condition'}],
            'targetProfileCheck':{'pendingGates':['g']},
            'evidenceBindings':[{'binding':{'diagnostics':[{'reason':'literal_failure'}]}}]}
        original=copy.deepcopy((native,check))
        rows=d.reasons_at_stages(native,check,{'blockingReasons':['parent_failure','literal_failure']})
        self.assertEqual({r['stage'] for r in rows},
            {'construction','candidate_validation','target_profile','parseDiagnostics','evidence_binding'})
        self.assertEqual(sum(r['reason']=='literal_failure' for r in rows),2)
        self.assertEqual((native,check),original)

    def test_existing_outputs_are_never_overwritten(self):
        """Repeated aggregation fails before reading or changing any inputs."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'diagnostic.json').write_bytes(b'preserved')
            with patch.object(d,'ROOT',root),patch.object(d,'DEST',Path('.')):
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):d.finish()
            self.assertEqual((root/'diagnostic.json').read_bytes(),b'preserved')

    def test_dependency_roots_preserve_independent_simultaneous_reasons(self):
        """Dependency closure cannot conceal an edge's independent evidence defect."""
        graph={'parent':[],'edge':['parent']}
        local={'parent':['visibility_uncertain'],'edge':['quote_unbound']}
        result=d.reachable_roots('edge',graph,local,set(graph))
        self.assertEqual({(r['candidateID'],r['reason']) for r in result['rootCauses']},
                         {('parent','visibility_uncertain'),('edge','quote_unbound')})

    def test_cycles_and_missing_dependencies_are_explicit(self):
        """A dependency cycle is not proof of eligibility or an infinite traversal."""
        result=d.reachable_roots('a',{'a':['b'],'b':['a','missing']},{'a':[],'b':[]},{'a','b','missing'})
        self.assertEqual(result['missingDependencies'],['missing'])
        self.assertTrue(result['cycles'])

    def test_visibility_void_tag_contaminates_later_plain_prose(self):
        """Demonstrate the current classifier mechanism without changing it."""
        text='Earlier plain text.\n<hr>\nLater independent plain prose.\n'
        original=text
        marks=d.regions(text)
        start=text.index('Later')
        self.assertEqual(set(marks[start:]),{'uncertain'})
        self.assertEqual(text,original)
        self.assertEqual(d.source_characteristics(text,'ciroh_hub')['lexicalSignals']['unclosedHtmlVoidTags'],1)

    def test_unmatched_close_contaminates_preceding_prose(self):
        """Record the classifier's broad fallback; do not infer real-world visibility."""
        text='Independent prose.\n</div>\n'
        self.assertEqual(set(d.regions(text)[:len('Independent prose.')]),{'uncertain'})

    def test_abstention_conflicts_are_only_scoped_flags(self):
        """Shared target without shared source scope is not marked as conflicting."""
        a=dict(requestID='r',abstentionID='a',ownerID='o',inventoryId='T',sourceUnitIDs=['u'])
        groups=[dict(requestID='p',ownerID='o',positive=[dict(candidateID='n',inventoryId='T',disposition='held',sourceUnitIDs=['v'])])]
        original=copy.deepcopy(a)
        self.assertFalse(d.conflict_flags([a],groups))
        groups[0]['positive'][0]['sourceUnitIDs']=['u']
        flag=d.conflict_flags([a],groups)[0]
        self.assertEqual(flag['interpretation'],'potential_scope_conflict_not_proven_contradiction')
        self.assertEqual(a,original)


if __name__=='__main__':unittest.main()
