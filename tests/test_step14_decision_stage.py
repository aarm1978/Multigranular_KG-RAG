"""Synthetic decision-stage safeguards; no provider or corpus execution."""
import unittest
from copy import deepcopy
from src.evaluation import step14_decision_stage as d


def member(cls='Tool',granularity='unspecified_requires_context_review'):
    """Minimal provenance-bearing member with no invented version role."""
    return dict(ontologyClass=cls,inventoryId=cls,granularity=granularity,versions={},
                originalReference={'file':'original'},evidencePointers=[{'quote':'source'}],identifierDeclarations=[])


def assessment(ids):
    """Explicit complete strict prediction with preserved scope uncertainty."""
    return dict(occurrenceIDs=ids,category='strict_identity',granularity='named tool',
                contradictoryEvidenceIDs=[],uncertainty='Release is unspecified; identity is at tool level.')


class DecisionTests(unittest.TestCase):
    def test_route_c_uncertainty_is_not_a_boolean_gate(self):
        a=assessment(['a','b']);original=deepcopy(a)
        self.assertEqual(d.route_c(a,{'a':member(),'b':member()}),[])
        self.assertEqual(a,original)

    def test_classes_granularity_and_conflicts_hold(self):
        a=assessment(['a','b'])
        self.assertIn('class_inventory_conflict',d.route_c(a,{'a':member(),'b':member('MLModel')}))
        self.assertIn('different_explicit_referent_granularities',d.route_c(a,{'a':member(granularity='release'),'b':member(granularity='family')}))
        a['contradictoryEvidenceIDs']=['E1Q1']
        self.assertIn('contradictory_evidence',d.route_c(a,{'a':member(),'b':member()}))

    def test_owned_identifier_conflict_preserved(self):
        members={'a':member('Paper'),'b':member('Paper')}
        for o in members:members[o]['identifierDeclarations']=[dict(scheme='doi',value=o,basis='deterministic_entity_own_field')]
        self.assertIn('contradictory_entity_owned_identifiers:doi',d.route_c(assessment(['a','b']),members))

    def test_no_transitive_union_and_overlap_held(self):
        groups=[dict(simulationID=str(i),occurrenceIDs=ids,state=d.ab.ACCEPTED,acceptedBy=['C'],holdReasons=[],holdKinds=[]) for i,ids in enumerate([['a','b'],['b','c']])]
        d.overlapping(groups)
        self.assertTrue(all(x['state']==d.ab.HELD for x in groups))
        self.assertEqual([x['occurrenceIDs'] for x in groups],[['a','b'],['b','c']])
        self.assertNotEqual(d.membership(['a','b']),d.membership(['a','b','c']))

    def test_exact_membership_and_missing_provenance(self):
        self.assertEqual(d.membership(['b','a']),('a','b'))
        with self.assertRaises(ValueError):d.membership(['a','a'])
        members={'a':member(),'b':member()};members['b']['evidencePointers']=[]
        self.assertIn('missing_original_evidence',d.route_c(assessment(['a','b']),members))


if __name__=='__main__':unittest.main()
