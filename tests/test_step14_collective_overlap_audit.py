"""Guard the audit distinction between eligible competition and independent holds."""
import unittest
from src.evaluation.step14_collective_overlap_audit import COMP, eligible_before_competition


class EligibilityTests(unittest.TestCase):
    def test_opposition_remains_independent_of_overlap(self):
        self.assertFalse(eligible_before_competition({'reasons':[COMP,'opposed_or_held_membership']}))
        self.assertFalse(eligible_before_competition({'reasons':['prior_opposition']}))

    def test_overlap_outcome_does_not_disqualify_a_peer_circularly(self):
        self.assertTrue(eligible_before_competition({'reasons':[COMP]}))
        self.assertTrue(eligible_before_competition({'reasons':['unresolved_equal_support']}))
