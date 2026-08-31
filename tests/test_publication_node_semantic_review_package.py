"""Focused no-network tests for the M2-C2B semantic-review package."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications import (
    build_publication_node_semantic_review_package as review_package_module,
)
from src.extraction.llm.publications.build_publication_node_semantic_review_package import (
    C2A_DIAGNOSTIC_PATH,
    evidence_occurrence_key,
    generate_review_package,
)
from src.extraction.llm.publications.request_builder import canonical_json, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    DEV_IDS,
    PROMPT_PATH,
)
from src.extraction.llm.publications.run_publication_trusted_evidence_metadata_binding import (
    C1B_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR as C2A_OUTPUT_DIR,
    _c1b_paths,
    _tree_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PublicationNodeSemanticReviewPackageTests(unittest.TestCase):
    """Prove C2B is complete, deterministic, neutral, and offline."""

    @classmethod
    def setUpClass(cls) -> None:
        """Generate one shared package while failing any attempted network access."""

        cls._temporary_directory = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls._temporary_directory.name)
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=AssertionError("C2B tests must not use network"),
        ):
            cls.package = generate_review_package(cls.output_dir)
        cls.candidates = cls.package["candidates"]["rows"]
        cls.evidence_groups = cls.package["evidenceGroups"]["rows"]

    @classmethod
    def tearDownClass(cls) -> None:
        """Release the shared temporary package directory."""

        cls._temporary_directory.cleanup()

    def test_exactly_254_authentic_candidates_appear_once(self) -> None:
        """Every authentic C1B candidate has one and only one review row."""

        keys = [row["reviewCandidateKey"] for row in self.candidates]
        self.assertEqual(len(keys), 254)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(self.package["summary"]["totalAuthenticCandidates"], 254)

    def test_candidate_content_is_unmodified_and_traces_to_raw_output(self) -> None:
        """Embedded candidate objects and hashes match the immutable raw outputs."""

        rows = {row["reviewCandidateKey"]: row for row in self.candidates}
        found = 0
        for development_id in DEV_IDS:
            raw_path = _c1b_paths(development_id)["raw"]
            raw_bytes = raw_path.read_bytes()
            payload = json.loads(raw_bytes.decode("utf-8"))
            for index, candidate in enumerate(payload["candidateNodes"]):
                key = f"{development_id}:{candidate['candidateID']}"
                row = rows[key]
                with self.subTest(candidateKey=key):
                    self.assertEqual(
                        canonical_json(row["authenticModelAuthoredCandidate"]),
                        canonical_json(candidate),
                    )
                    self.assertEqual(
                        row["authenticCandidateJSONPointer"],
                        f"/candidateNodes/{index}",
                    )
                    self.assertEqual(
                        row["authenticRawModelOutputSha256"],
                        sha256_bytes(raw_bytes),
                    )
                found += 1
        self.assertEqual(found, 254)

    def test_evidence_grouping_uses_identity_and_coordinates_not_text(self) -> None:
        """Text-identical evidence at different positions remains distinct."""

        first = {
            "evidenceSpanID": "evidence-0001",
            "startOffsetInUnit": 1,
            "endOffsetInUnit": 5,
            "startOffsetInDocument": 101,
            "endOffsetInDocument": 105,
            "evidenceText": "same",
        }
        second = {**first, "startOffsetInUnit": 8, "endOffsetInUnit": 12}
        second["startOffsetInDocument"] = 108
        second["endOffsetInDocument"] = 112
        self.assertNotEqual(
            evidence_occurrence_key("DEV-X", "unit-x", first),
            evidence_occurrence_key("DEV-X", "unit-x", second),
        )
        keys = [tuple(row["evidenceOccurrenceKey"]) for row in self.evidence_groups]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse(self.package["evidenceGroups"]["textAloneUsedForGrouping"])

    def test_every_candidate_evidence_reference_resolves(self) -> None:
        """Each candidate reference maps to one authentic source-position group."""

        groups = {
            (row["developmentID"], row["evidenceSpanID"]): row
            for row in self.evidence_groups
        }
        for candidate in self.candidates:
            for evidence_id in candidate["evidenceSpanIDs"]:
                key = (candidate["developmentID"], evidence_id)
                with self.subTest(candidateKey=candidate["reviewCandidateKey"], evidence=evidence_id):
                    self.assertIn(key, groups)
                    self.assertIn(candidate["reviewCandidateKey"], groups[key]["candidateKeys"])

    def test_multiclass_grouping_is_deterministic(self) -> None:
        """A second offline build is byte-identical to the first package."""

        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "src.extraction.llm.publications.openai_provider.urlopen",
                side_effect=AssertionError("C2B tests must not use network"),
            ):
                second = generate_review_package(Path(directory))
        self.assertEqual(
            canonical_json(self.package["multiclassGroups"]),
            canonical_json(second["multiclassGroups"]),
        )
        self.assertEqual(
            self.package["summary"]["canonicalContentSha256"],
            second["summary"]["canonicalContentSha256"],
        )

    def test_authentic_and_counterfactual_statuses_are_distinct(self) -> None:
        """Diagnostic improvements never overwrite authentic validator status."""

        changed = [
            row
            for row in self.candidates
            if row["authenticCandidateValidationStatus"] == "rejected"
            and row["counterfactualCandidateValidationStatus"] == "validated"
        ]
        residual = [
            row
            for row in self.candidates
            if row["counterfactualCandidateValidationStatus"] == "rejected"
        ]
        self.assertEqual(len(changed), 69)
        self.assertEqual(len(residual), 2)
        self.assertTrue(all(row["counterfactualStatusIsDiagnosticOnly"] for row in self.candidates))
        self.assertTrue(all(row["notGold"] and row["notFormalEvaluation"] for row in self.candidates))
        self.assertTrue(all(row["authenticUsable"] is False for row in changed))
        self.assertTrue(all(row["counterfactualHypotheticallyUsable"] is True for row in changed))

    def test_review_template_contains_only_empty_assessment_boxes(self) -> None:
        """The researcher template contains no pre-filled semantic judgment."""

        text = (self.output_dir / "publication_node_semantic_review_template.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("- [x]", text.lower())
        self.assertIn("- [ ] Appropriate ontology assignment(s)", text)
        self.assertIn("Researcher notes:", text)

    def test_package_is_offline_and_has_no_semantic_or_accuracy_labels(self) -> None:
        """Provenance records no provider/external use or formal assessment."""

        summary = self.package["summary"]
        self.assertEqual(summary["provenance"]["providerCalls"], 0)
        self.assertFalse(summary["provenance"]["externalDataUsed"])
        self.assertFalse(summary["semanticJudgmentsMade"])
        self.assertFalse(summary["accuracyMetricsComputed"])
        self.assertTrue(summary["notGold"])
        self.assertTrue(summary["notFormalEvaluation"])

    def test_generator_has_no_network_or_provider_mechanism(self) -> None:
        """The C2B source contains no client, socket, or HTTP execution path."""

        tree = ast.parse(inspect.getsource(review_package_module))
        forbidden_roots = {"httpx", "openai", "requests", "socket", "urllib"}
        imported_roots = set()
        called_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_names.add(node.func.attr)
        self.assertTrue(imported_roots.isdisjoint(forbidden_roots))
        self.assertTrue(
            called_names.isdisjoint(
                {"urlopen", "request", "create_connection", "OpenAI"}
            )
        )

    def test_target_view_contains_all_40_authorized_targets(self) -> None:
        """Target-centered review includes represented and zero-candidate targets."""

        rows = self.package["byTarget"]["rows"]
        self.assertEqual(len(rows), 40)
        self.assertEqual(
            [row["operationalTargetID"] for row in rows],
            sorted(row["operationalTargetID"] for row in rows),
        )
        self.assertTrue(any(row["totalAuthenticCandidates"] == 0 for row in rows))

    def test_historical_artifacts_remain_byte_identical(self) -> None:
        """Accepted C1B/C2A trees and prompt retain their reviewed hashes."""

        c1b = _tree_snapshot(C1B_OUTPUT_DIR)
        c2a = _tree_snapshot(C2A_OUTPUT_DIR)
        self.assertEqual(c1b["fileCount"], 184)
        self.assertEqual(
            c1b["treeInventorySha256"],
            "bee13c4501597cf7793d6c9e93f3d4a5b35a2881bc0cd98b1a0a24ea03682a28",
        )
        self.assertEqual(c2a["fileCount"], 55)
        self.assertEqual(
            c2a["treeInventorySha256"],
            "5313dfba026eba38bb53b45b9260cb7ac419b052aa5d95a8bef7214d815d8454",
        )
        self.assertEqual(
            hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
            "6b180b88d718dbda7d9f30b28c484d263998ed8caa88eab516f531e488b8317f",
        )
        self.assertEqual(
            hashlib.sha256(C2A_DIAGNOSTIC_PATH.read_bytes()).hexdigest(),
            "24a7f3e779d389a86249417d4ca184fb68302c3b2e36d15adaf2a6fa33bb17a3",
        )


if __name__ == "__main__":
    unittest.main()
