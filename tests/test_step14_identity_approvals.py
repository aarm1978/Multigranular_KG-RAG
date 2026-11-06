"""Focused offline checks of explicit researcher approval scope and preservation."""
import json
import socket
import unittest
from copy import deepcopy
from unittest.mock import patch

from src.evaluation import step14_identity_proposals_validation as validation


class ApprovalTests(unittest.TestCase):
    """Exercise the tracked approval records without corpus reads or provider calls."""

    def setUp(self):
        """Load only the tracked proposals and decision records; forbid networking."""
        self.document = json.loads(validation.DOCUMENT.read_text())
        self.records = [json.loads(line) for line in validation.APPROVALS.read_text().splitlines()]
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('No calls'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def check(self, records):
        """Validate in-memory records with direct authority-file reads disabled."""
        return validation.validate_approvals(self.document, records, verify_files=False)

    def test_exact_scope_and_nonmutation(self):
        """Only 99 occurrences receive approval; all other 133 remain unapproved."""
        before = deepcopy((self.document, self.records))
        result = self.check(self.records)
        self.assertEqual(result, dict(approvedSubsets=29, approvedOccurrences=99,
                                     remainingUnapprovedOccurrences=133, canonicalIDsAllocated=0))
        self.assertEqual(before, (self.document, self.records))

    def test_unapproved_case_rejected(self):
        """C020/C031 cannot enter this explicitly bounded batch."""
        for alias in ('C020', 'C031'):
            with self.subTest(alias=alias):
                records = deepcopy(self.records)
                records[0]['caseAlias'] = alias
                with self.assertRaises(ValueError):
                    self.check(records)

    def test_partial_expansion_rejected(self):
        """The v3.0 NWM occurrence cannot join the approved v2.1 pair."""
        record = next(r for r in self.records if r['caseAlias'] == 'C032')
        record['memberAliases'].append('O004')
        with self.assertRaises(ValueError):
            self.check(self.records)

    def test_restrictions_and_evidence_preserved(self):
        """Approval cannot erase class, granularity, conflicts, or provenance."""
        for field in ('ontologyClass', 'granularity', 'versionAndRoleRestrictions',
                      'supportingEvidenceIDs', 'conflictingEvidenceIDs', 'retainedReviewConcerns',
                      'originalModelRecommendation', 'caseSha256', 'sourcePackage'):
            with self.subTest(field=field):
                records = deepcopy(self.records)
                records[0][field] = 'altered'
                with self.assertRaises(ValueError):
                    self.check(records)

    def test_allocation_and_union_forbidden(self):
        """Decision approval does not authorize canonical allocation or union."""
        for field, value in (('canonicalID', 'not-allowed'), ('transitiveUnionAuthorized', True),
                             ('materializationStatus', 'authorized')):
            with self.subTest(field=field):
                records = deepcopy(self.records)
                records[0][field] = value
                with self.assertRaises(ValueError):
                    self.check(records)

    def test_revision_and_duplicates_rejected(self):
        """Initial decision identity and revision cannot be silently rewritten."""
        for field, value in (('revision', 2), ('supersedes', 'invented'),
                             ('decisionAuthority', 'model'), ('decisionStatus', 'rejected')):
            with self.subTest(field=field):
                records = deepcopy(self.records)
                records[0][field] = value
                with self.assertRaises(ValueError):
                    self.check(records)
        with self.assertRaises(ValueError):
            self.check(self.records + [self.records[0]])

    def test_proposals_and_attribution_preserved(self):
        """The provisional triage remains unchanged and is not blanket approval."""
        for field, value in (('reviewAuthority', 'Researcher adjudicated all 43 cases'),
                             ('cases', [])):
            with self.subTest(field=field):
                document = deepcopy(self.document)
                document[field] = value
                with self.assertRaises(ValueError):
                    validation.validate_approvals(document, self.records, verify_files=False)


if __name__ == '__main__':
    unittest.main()
