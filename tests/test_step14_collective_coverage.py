"""Regressions for joint input presentation independently of scientific adjudication."""
import unittest
from src.evaluation import step14_collective_coverage as c


def scope(name, *ids, lane='overlap', status='prepared'):
    """Construct a candidate carrying its original disposition."""
    return dict(candidateID=name, occurrenceIDs=list(ids), lane=lane, status=status)


class PackingTests(unittest.TestCase):
    def test_chain_and_duplicate_candidate_memberships(self):
        scopes = [scope('ab','a','b'), scope('bc','b','c'),
                  scope('ba','b','a',lane='typed_relation')]
        old = {'u':['a','b'], 'v':['c']}
        units = c.pack(scopes, 2)
        audit = c.audit(scopes, old, units)
        self.assertEqual(units, c.pack(list(reversed(scopes)), 2))
        self.assertEqual(len(units), 2)
        self.assertEqual(audit[0]['v2JointRequests'], audit[2]['v2JointRequests'])
        self.assertEqual((audit[1]['v1'],audit[1]['v2']), ('split','fully_co_present'))
        self.assertEqual(len(c.pack(scopes)), 1)

    def test_hub_repeated_only_across_windows(self):
        scopes = [scope(str(i),'hub',str(i)) for i in range(40)]
        units = c.pack(scopes)
        self.assertEqual(len(units),4)
        self.assertTrue(all('hub' in ids and len(set(ids))==len(ids)<=12 for ids in units.values()))
        self.assertTrue(all(r['v2JointRequests'] for r in c.audit(scopes,units,units)))

    def test_limit_exclusions_and_reconciliation(self):
        ids = list('abcdefghijklmn')
        scopes = [scope('fits',*ids[:12]), scope('large',*ids),
                  scope('excluded',*ids,status='protected_resolved_membership_boundary')]
        old = {'a':ids[:12], 'b':ids[12:]}
        rows = c.audit(scopes,old,c.pack(scopes))
        self.assertEqual(rows[0]['v2'],'fully_co_present')
        self.assertTrue(rows[1]['pendingBoundedReconciliation'])
        self.assertEqual(rows[1]['v2'],'missing_members')
        self.assertEqual(rows[2]['v2'],'excluded')
        self.assertTrue(rows[2]['overLimit'])
        self.assertEqual(sum(r['count'] for r in c.profile(rows)),len(scopes))

    def test_submission_audit_fails_on_split_pair(self):
        units = {'u':['a','b'],'v':['c','d']}
        with self.assertRaisesRegex(ValueError, 'MISSING_JOINT_PRESENTATION:bc'):
            c.audit([scope('bc','b','c')],units,units)
