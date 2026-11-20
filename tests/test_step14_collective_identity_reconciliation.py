"""Regression tests for exact collective scopes, saved opposition and protected mappings."""
import unittest

from src.evaluation import step14_collective_identity_reconciliation as r


def fixture(uid, ids, category='strict_identity'):
    """Construct a v4 item with its exact member-level citation bindings."""
    return dict(unitID=uid, itemType='assessments', itemIndex=0, occurrenceIDs=ids, category=category,
                status=r.replay.VALID, v3Status='validated_hypotheses_only',externalEvidenceIDs=[],
                citations=[dict(binding=dict(occurrenceID=o),field='supportingEvidenceIDs',location='member') for o in ids],
                modelItem=dict(category=category,granularity='named model',contradictoryEvidenceIDs=[]))


def evaluate(items, *, protected=(), evidence=None, earlier=None, alternatives=None):
    """Run the real route and overlap guards over small offline fixtures."""
    ids={o for item in items for o in item['occurrenceIDs']}
    members={o:dict(ontologyClass='ComputationalModel',inventoryId='M',sourceFamilies=['publication'],
                    sourceArtifacts=['paper'],versions={},originalReference=o,evidencePointers=['pointer']) for o in ids}
    units={item['unitID']:dict(aliasBindings={o:o for o in item['occurrenceIDs']}) for item in items}
    prior=([],[],set(protected),earlier or {},alternatives or {},evidence or {})
    return r.reconcile(items,units,members,prior,check_v4=False)


class ReconciliationTests(unittest.TestCase):
    def test_exact_repeats_preserve_support_and_cid(self):
        items=[fixture('first',['a','b']),fixture('second',['b','a'])]
        groups=evaluate(items,earlier={('a','b'):dict(routes=['A','B'],id='baseline')})
        result=groups['a','b']
        self.assertEqual(len(result['appearanceReferences']),2)
        self.assertEqual(result['routes'],['A','B','C'])
        self.assertEqual(result['acceptedBy'],['A'])
        self.assertFalse(result['humanVerified'])
        self.assertEqual(result['provisionalCanonicalID'],evaluate(items[::-1])[('a','b')]['provisionalCanonicalID'])

    def test_chain_preserves_unresolved_alternatives(self):
        groups=evaluate([fixture('first',['a','b']),fixture('second',['b','c'])])
        self.assertEqual(set(groups),{('a','b'),('b','c')})
        for row in groups.values():
            self.assertEqual(row['state'],r.d.ab.HELD)
            self.assertEqual(len(row['competingCollectiveScopes']),1)

    def test_prior_negative_and_approval_block(self):
        items=[fixture('positive',['a','b','c'])]
        g=evaluate(items,protected=['c'],evidence={('a','b'):{('pair','negative')}})['a','b','c']
        self.assertEqual(set(g['reasons']),{'prior_opposition','protected_membership'})
        self.assertNotIn('provisionalCanonicalID',g)

    def test_held_version_relation_blocks_identity(self):
        rel=fixture('relationship',['a','b'])
        rel.update(category='typedRelations',itemType='typedRelations',status=r.replay.HELD,modelItem={'signatureID':'D-27'})
        g=evaluate([fixture('prediction',['a','b','c']),rel])['a','b','c']
        self.assertIn('opposed_or_held_membership',g['reasons'])
        self.assertEqual(g['opposingCollectiveItems'],[r.ref(rel)])

    def test_earlier_competing_contextual_scope(self):
        alt=dict(simulationID='old',occurrenceIDs=['a','c'],savedGroup=None,routeC=[dict(reasons=[])],conflicts={})
        out=evaluate([fixture('new',['a','b'])],alternatives={('a','c'):alt})
        self.assertIn('unresolved_equal_support',out['a','b']['reasons'])
        self.assertEqual(out['a','b']['priorOrCollectiveAlternatives'],['old'])

    def test_recovery_can_remove_a_previously_uncontested_group(self):
        original=fixture('original',['a','b'])
        recovered=fixture('recovered',['b','c'])
        recovered['v3Status']='invalid_or_incomplete'
        self.assertEqual(evaluate([original])['a','b']['state'],r.d.ab.ACCEPTED)
        self.assertTrue(all(g['state']==r.d.ab.HELD for g in evaluate([original,recovered]).values()))
