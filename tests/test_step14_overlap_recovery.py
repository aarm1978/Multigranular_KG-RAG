"""Exact-scope overlap recovery without scientific tie-breaking or transitive closure."""
import unittest
from copy import deepcopy
from src.evaluation import step14_overlap_recovery as r


def row(uid,ids,route='B'):
    """Minimal saved complete-scope support for resolver tests."""
    return dict(simulationID=uid,occurrenceIDs=ids,state=r.d.ab.HELD,holdReasons=[r.OVERLAP],holdKinds=['overlap'],acceptedBy=[],
        conflicts={},routeC=[dict(reasons=[])] if route=='C' else [],
        savedGroup=dict(safeguards={route:dict(complete=True)}) if route!='C' else None)


class OverlapTests(unittest.TestCase):
    def test_chain_does_not_merge_or_choose_tie(self):
        accepted,notes=r.reconcile([row('ab',['a','b']),row('bc',['b','c'])],set())
        self.assertEqual(accepted,[])
        self.assertTrue(all(x['status']=='unresolved_equal_support' for x in notes))

    def test_explicit_complete_larger_scope(self):
        accepted,_=r.reconcile([row('ab',['a','b']),row('bc',['b','c']),row('abc',['a','b','c'])],set())
        self.assertEqual([x['simulationID'] for x in accepted],['abc'])

    def test_fully_supported_pairs_do_not_invent_new_scope(self):
        accepted,_=r.reconcile([row('ab',['a','b']),row('bc',['b','c']),row('ac',['a','c'])],set())
        self.assertEqual(accepted,[])

    def test_strength_and_conflict(self):
        accepted,_=r.reconcile([row('a',['x','y'],'A'),row('b',['y','z'],'C')],set())
        self.assertEqual([x['simulationID'] for x in accepted],['a'])
        conflict=row('a',['x','y'],'A');conflict['conflicts']={'savedPairs':[{'negative':True}]}
        accepted,notes=r.reconcile([conflict],set());self.assertEqual(accepted,[])
        self.assertEqual(notes[0]['status'],'held_conflict')

    def test_historical_and_existing_protection(self):
        self.assertEqual(r.reconcile([row('a',['x','y'],'A')],{'x'})[0],[])

    def test_reproducible_and_preserves_inputs(self):
        rows=[row('a',['x','y'],'C'),row('b',['y','z']),row('c',['p','q'])];before=deepcopy(rows)
        first=r.reconcile(rows,set());second=r.reconcile(list(reversed(rows)),set())
        self.assertEqual(first,second);self.assertEqual(rows,before)


if __name__=='__main__':unittest.main()
