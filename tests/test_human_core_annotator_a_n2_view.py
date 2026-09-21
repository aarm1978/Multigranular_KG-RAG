"""Focused tests for the read-only Annotator A N=2 composite view."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from src.annotation.publication_pilot1.build_human_core_annotator_a_n2_view import (
    DEFAULT_OUTPUT,
    N2_UNITS,
    build_annotator_a_n2_view,
    serialize_annotator_a_n2_view,
)


ROOT = Path(__file__).resolve().parents[1]


class HumanCoreAnnotatorAN2ViewTests(unittest.TestCase):
    """Prove source binding, exact scope, composition, and stable preservation."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the checked-in deterministic projection."""

        cls.view = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_source_authorities_and_exports_are_byte_bound(self) -> None:
        """All preservation/package/export hashes remain exact."""

        for partition in ("primaryV014", "supplementalV015"):
            for authority in ("preservationRecord", "package", "export"):
                item = self.view["sourceAuthorities"][partition][authority]
                self.assertEqual(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest(), item["sha256"])
        freeze = self.view["sourceAuthorities"]["n2MembershipFreeze"]
        self.assertEqual(hashlib.sha256((ROOT / freeze["path"]).read_bytes()).hexdigest(), freeze["sha256"])

    def test_exact_n2_membership_and_partition_composition(self) -> None:
        """The view contains only the frozen pair, once in each A partition."""

        self.assertEqual(tuple(self.view["sourceUnitIDs"]), N2_UNITS)
        self.assertEqual(tuple(row["sourceUnitID"] for row in self.view["units"]), N2_UNITS)
        for row in self.view["units"]:
            self.assertEqual(row["primaryV014"]["sourceUnitID"], row["sourceUnitID"])
            self.assertEqual(row["supplementalV015"]["sourceUnitID"], row["sourceUnitID"])
            self.assertEqual(row["primaryV014"]["status"], "submitted")
            self.assertEqual(row["supplementalV015"]["status"], "submitted")

    def test_assertions_and_provenance_are_verbatim_source_records(self) -> None:
        """Embedded records equal their selected immutable export records exactly."""

        result = build_annotator_a_n2_view()
        self.assertEqual(self.view["units"], result["units"])
        self.assertTrue(self.view["readOnly"])
        self.assertFalse(self.view["destructiveMergeAuthorized"])

    def test_output_is_deterministic(self) -> None:
        """The checked-in bytes reproduce without timestamps or unstable ordering."""

        self.assertEqual(DEFAULT_OUTPUT.read_bytes(), serialize_annotator_a_n2_view())


if __name__ == "__main__":
    unittest.main()
