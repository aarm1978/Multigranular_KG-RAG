"""Synthetic tests for read-only diagnostic counting and exact failure localization."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from src.evaluation import source_local_review_diagnostic as d


class DiagnosticTests(unittest.TestCase):
    def test_abstention_localization_preserves_exact_invalid_id(self):
        """Report each failed term without normalizing source identifiers."""
        body={'targetProfile':{'entities':['A'],'relations':[]},'selectedSourceUnitIDs':['source:exact']}
        payload={'candidateNodes':[],'candidateEdges':[],'abstentions':[
            {'abstentionID':'a','inventoryId':'A','sourceUnitIDs':['source: exact'],'reason':'none'},
            {'abstentionID':'b','inventoryId':'A','sourceUnitIDs':['source:exact'],'reason':'none'}]}
        original=copy.deepcopy(payload);issues=d.abstention_issues(payload,body)
        self.assertEqual(len(issues),1)
        self.assertEqual(issues[0]['field'],'abstentions[0]')
        self.assertFalse(issues[0]['conditions']['selectedSourceUnits'])
        self.assertEqual(issues[0]['offendingSourceUnitIDs'],['source: exact'])
        self.assertEqual(payload,original)

    def test_candidate_absence_and_held_candidates_remain_distinct(self):
        """Zero yield does not imply absence of model candidates."""
        payload={'candidateNodes':[{}],'candidateEdges':[],'abstentions':[{}]}
        report={'nativeValidationView':{'decisions':[{'disposition':'held'}]},
                'responseBytesHex':json.dumps(payload).encode().hex(),'zeroYield':True,
                'projection':{'nodes':[],'edges':[]},'unresolvedAssertions':[{}]}
        counts=d.group_stats(report)
        self.assertEqual(counts['candidateNodes'],1)
        self.assertEqual(counts['decision:held'],1)
        self.assertEqual(counts['acceptedNodes'],0)
        self.assertEqual(counts['zeroYieldRequests'],1)

    def test_report_hash_mismatch(self):
        """Reject changed reports rather than summarize unauthenticated counters."""
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'report.json';p.write_text(json.dumps({'reportSha256':'bad'}))
            with self.assertRaisesRegex(ValueError,'REPORT_HASH_DRIFT'):d.checked_report(p)


if __name__=='__main__':unittest.main()
