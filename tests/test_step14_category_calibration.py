"""Offline category instruction and sampling invariants."""
from copy import deepcopy
import unittest
from src.evaluation import step14_category_calibration as x
from test_step14_queue_compatibility_pilot import body,recommendation
from test_step14_calibration_sampling import SamplingTests

class CategoryTests(unittest.TestCase):
    def test_only_instructions_change(self):
        original=body();original['instructions']=x.c.p.PROMPT
        current=x.c.variant(original);before=deepcopy(current);new=x.revised(current)
        x.comparable(current,new);self.assertEqual(current,before)
        for arm in (current,new):self.assertEqual(x.c.p.validate(recommendation(),arm)['assessedPairs'],2)
        new['model']='other'
        with self.assertRaisesRegex(ValueError,'ARM_COMPARABILITY_DRIFT'):x.comparable(current,new)
        with self.assertRaisesRegex(ValueError,'CURRENT_INSTRUCTIONS_DRIFT'):x.comparable(original,x.revised(original))

    def test_selection_balance_exclusion_determinism(self):
        rows=SamplingTests().rows();before=deepcopy(rows);excluded={'U1','U25'}
        selected,report=x.select(rows,excluded)
        self.assertEqual(selected,x.select(list(reversed(rows)),excluded)[0])
        self.assertEqual(len(selected),8);self.assertEqual(sum(bool(r['crossPairs']) for r in selected),4)
        self.assertFalse(excluded & {r['unitID'] for r in selected});self.assertEqual(rows,before)
        self.assertTrue(report['available'])

    def test_insufficient_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_SCOPE'):x.select(SamplingTests().rows()[:3],set())

if __name__=='__main__':unittest.main()
