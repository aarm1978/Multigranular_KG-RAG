"""Focused metadata-only held-out selection regressions."""
import unittest
from copy import deepcopy
from src.evaluation import step14_calibration_sampling as s

class SamplingTests(unittest.TestCase):
    def rows(self):
        """Synthetic scopes include low-count cross units and diverse features."""
        return [dict(unitID=f'U{i}',crossPairs=(1+i%5 if i<20 else 0),withinPairs=2,
            features=[f'density:{i%3}',f'family:{i%4}'],tags=[],familyPairs={'a|b' if i<20 else 'a|a':2}) for i in range(40)]

    def test_balanced_deterministic_feasible_and_immutable(self):
        rows=self.rows();before=deepcopy(rows)
        selected,report=s.select(rows,{'U1','U22'})
        self.assertEqual(selected,s.select(list(reversed(rows)),{'U1','U22'})[0])
        self.assertEqual(report['crossUnits'],8);self.assertEqual(report['withinOnlyUnits'],8)
        self.assertGreaterEqual(report['crossPairs'],24);self.assertEqual(rows,before)
        self.assertFalse({'U1','U22'}&{x['unitID'] for x in selected})

    def test_unavailable_target_honest(self):
        rows=self.rows()
        for row in rows:row['crossPairs']=int(row['crossPairs']>0)
        _,report=s.select(rows,set());self.assertEqual(report['crossPairs'],8)
        self.assertTrue(report['unmetTargets'])
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_CROSS'):s.select(rows,{'U'+str(i) for i in range(15)})

    def test_pair_structure_not_unit_tag(self):
        payload=dict(entities=[dict(id='E1',sourceFamilies=['github'],names=['X'],ontologyClass='Tool'),
            dict(id='E2',sourceFamilies=['ciroh_hub'],names=['X'],ontologyClass='Tool'),
            dict(id='E3',sourceFamilies=['github'],names=['Y'],ontologyClass='Tool')],
            pairs=[dict(entities=['E1','E2']),dict(entities=['E1','E3'])])
        for entity in payload['entities']:entity.update(evidence=[],recordedVersionOrImplementation={})
        row=s.describe('u',payload)
        self.assertEqual((row['crossPairs'],row['withinPairs']),(1,1))
        self.assertEqual(row['familyPairs'],{'ciroh_hub|github':1,'github|github':1})

if __name__=='__main__':unittest.main()
