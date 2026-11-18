"""The versioned validator preserves narrative text and the original scientific guards."""
import json
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_collective_validation as v


def fixture():
    """Two independently cited occurrences with an explicitly descriptive referent."""
    ends = [dict(occurrenceID=o, names=['model'], ontologyClass='ComputationalModel',
                 evidence=[dict(evidenceID=o+'Q1', text='A source statement')]) for o in ('E1','E2')]
    payload = dict(occurrences=ends, allowedPredicates=[])
    body = dict(input=json.dumps(payload), text=dict(format=dict(schema=v.legacy.schema(payload))))
    assessment = dict(category='strict_identity', occurrenceIDs=['E1','E2'], broaderReferent=' family wording ',
                      supportingEvidenceIDs=['E1Q1','E2Q1'], contradictoryEvidenceIDs=[], granularity='model',
                      rationale='Independent evidence', uncertainty='prediction')
    return body, dict(assessments=[assessment], typedRelations=[], ontologyGaps=[])


class ValidationTests(unittest.TestCase):
    def test_unchanged_narrative_and_null(self):
        body, value = fixture()
        for desc in (' family wording ', None):
            value['assessments'][0]['broaderReferent'] = desc
            before = deepcopy(value)
            v.validate(value, body)
            self.assertEqual(value, before)
            result = v.w.resolve_output(value, {'E1':'occ-a','E2':'occ-b'})
            self.assertEqual(result['assessments'][0]['broaderReferent'], desc)

    def test_only_description_guard_removed(self):
        body, value = fixture()
        with self.assertRaisesRegex(ValueError,'NO_CANONICAL_ANCHOR'):
            v.legacy.validate(value,body)
        v.validate(value,body)
        for key, replacement, rule in [('supportingEvidenceIDs',['E1Q1'],'UNCITED_MEMBER'),
                                        ('contradictoryEvidenceIDs',['E2Q1'],'CONTRADICTORY_IDENTITY'),
                                        ('supportingEvidenceIDs',['E9Q1'],'MISBOUND_EVIDENCE')]:
            broken = deepcopy(value)
            broken['assessments'][0][key] = replacement
            with self.assertRaisesRegex(ValueError,rule):
                v.validate(broken,body)

    def test_invalid_receipt_records_rule_and_preserves_raw(self):
        body, value = fixture()
        for bad,rule in [([], 'EXACT_PARTITION_REQUIRED'), ([{}], 'JSON_SCHEMA:required')]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                value['assessments'] = bad
                raw = dict(status='completed',usage={'total_tokens':25})
                with patch.object(v.w.live.provider,'extract_model_output',return_value=json.dumps(value)):
                    report = v.process(root,'U',body,raw)
                self.assertEqual(report['failedRule'],rule)
                self.assertEqual(v.w.live.load(root/'execution/U.response.json'),raw)
                self.assertFalse((root/'execution/U.hypotheses.json').exists())
