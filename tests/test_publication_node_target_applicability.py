"""Tests for the approved M2-C0 Publication node-target applicability policy."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications.node_target_applicability import (
    DEFAULT_OUTPUT_DIR,
    EXPECTED_CANDIDATE_AUTHORABLE_NODE_COUNT,
    POLICY_DECISION_UNIVERSAL_OPEN,
    POLICY_STATUS,
    derive_devset0_plan,
    derive_policy,
    derive_target_audit,
    evaluate_node_target_applicability,
    write_policy_artifacts,
)
from src.extraction.llm.publications.request_builder import (
    TARGET_INVENTORY_PATH,
    canonical_json,
    load_yaml_object,
    sha256_bytes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "src/extraction/llm/publications/node_target_applicability.py"


class NodeTargetApplicabilityTests(unittest.TestCase):
    """Prove C0 derives only answer-independent node applicability decisions."""

    def test_policy_audit_and_plan_are_byte_deterministic(self) -> None:
        """Repeated derivation produces byte-identical canonical artifacts."""

        first_policy = derive_policy()
        second_policy = derive_policy()
        self.assertEqual(canonical_json(first_policy), canonical_json(second_policy))
        first_audit = derive_target_audit(first_policy)
        second_audit = derive_target_audit(second_policy)
        self.assertEqual(canonical_json(first_audit), canonical_json(second_audit))
        self.assertEqual(
            canonical_json(derive_devset0_plan(first_policy)),
            canonical_json(derive_devset0_plan(second_policy)),
        )

    def test_target_universe_and_statuses_match_frozen_inventory(self) -> None:
        """All and only the 46 frozen candidate-authorable node targets are audited."""

        profile = load_yaml_object(TARGET_INVENTORY_PATH)
        expected = {
            row["operational_id"]
            for row in profile["node_targets"]
            if row.get("emission_mode") in {"llm_candidate", "resolver_mediated_candidate"}
            or "link_existing" in row.get("allowed_actions", [])
        }
        audit = derive_target_audit(derive_policy())
        actual = {row["operationalTargetID"] for row in audit["targets"]}
        self.assertEqual(len(actual), EXPECTED_CANDIDATE_AUTHORABLE_NODE_COUNT)
        self.assertEqual(actual, expected)
        self.assertEqual(
            audit["statusCounts"],
            {
                "DEFERRED_ONLY": 2,
                "DETERMINISTICALLY_APPLICABLE": 4,
                "UNIVERSALLY_ELIGIBLE_WITHIN_CHANNEL": 40,
            },
        )
        self.assertTrue(all(row["policyRuleIDs"] for row in audit["targets"]))

    def test_researcher_decision_is_distinct_from_frozen_authority(self) -> None:
        """Universal eligibility is an approved policy consequence, not a frozen axiom."""

        policy = derive_policy()
        decisions = policy["researcherApprovedExtractionPolicyDecisions"]
        self.assertEqual([row["decisionID"] for row in decisions], [POLICY_DECISION_UNIVERSAL_OPEN])
        decision = decisions[0]
        self.assertEqual(decision["decisionType"], "prospective_extraction_policy")
        self.assertEqual(decision["approvalStatus"], "researcher_approved")
        self.assertTrue(decision["notOntologyAxiom"])
        self.assertTrue(decision["notLiteralTargetInventoryRule"])
        open_rule = next(
            row for row in policy["rules"] if row["ruleID"] == "C0-NODE-OPEN-001"
        )
        self.assertEqual(open_rule["policyDecisionID"], POLICY_DECISION_UNIVERSAL_OPEN)
        self.assertEqual(
            open_rule["ruleNature"], "researcher_approved_extraction_policy_consequence"
        )

        direct = [
            row
            for row in derive_target_audit(policy)["targets"]
            if row["emissionMode"] == "llm_candidate"
        ]
        self.assertEqual(len(direct), 40)
        self.assertTrue(
            all(not row["applicabilityConsequenceFullyDerivableFromFrozenAuthorities"] for row in direct)
        )
        self.assertTrue(
            all(not row["universalEligibilityExplicitlyEncodedInFrozenAuthorities"] for row in direct)
        )

    def test_narrowing_and_coverage_semantics_are_explicit(self) -> None:
        """Policy forbids semantic pre-screening and distinguishes coverage from negatives."""

        policy = derive_policy()
        direct = [
            row
            for row in derive_target_audit(policy)["targets"]
            if row["emissionMode"] == "llm_candidate"
        ]
        self.assertTrue(all(row["narrowerApplicabilityRequiresNewPolicyOrAuthority"] for row in direct))
        self.assertTrue(all(not row["semanticPrescreeningRequired"] for row in direct))
        self.assertTrue(all(not row["semanticPrescreeningAuthorized"] for row in direct))
        coverage = policy["coverageSemantics"]
        self.assertTrue(coverage["requestLevelTargetSpaceCoverage"])
        self.assertFalse(coverage["targetLevelExplicitNegativeAssessmentRequired"])
        self.assertFalse(coverage["oneAbstentionRequiredForEveryEligibleAbsentTarget"])
        self.assertTrue(coverage["noCandidateAndNoAbstentionPermitted"])
        self.assertEqual(policy["status"], POLICY_STATUS)
        self.assertEqual(POLICY_STATUS, "approved_for_development")

    def test_dev_plan_has_explicit_inclusion_and_exclusion_rules(self) -> None:
        """Every unit and every excluded group has stable policy-rule justification."""

        plan = derive_devset0_plan(derive_policy())
        profile = load_yaml_object(TARGET_INVENTORY_PATH)
        open_ids = {
            row["operational_id"]
            for row in profile["node_targets"]
            if row.get("emission_mode") == "llm_candidate"
            and row.get("pilot_treatment") in {"extract_and_evaluate", "extract_and_monitor"}
            and row.get("direct_instantiation") is True
        }
        self.assertEqual(plan["status"], POLICY_STATUS)
        self.assertEqual(len(plan["units"]), 10)
        self.assertEqual(plan["coverageSummary"]["distinctEligibleTargetSets"], 1)
        self.assertFalse(plan["relationsPlanned"])
        for unit in plan["units"]:
            self.assertEqual(unit["extractionChannel"], "open_discovery")
            self.assertEqual(unit["eligibleNodeTargetCount"], 40)
            self.assertEqual(len(unit["eligibleNodeOperationalTargetIDs"]), 40)
            self.assertEqual(set(unit["eligibleNodeOperationalTargetIDs"]), open_ids)
            self.assertTrue(
                all(target_id.startswith("PUB-N-") for target_id in unit["eligibleNodeOperationalTargetIDs"])
            )
            self.assertTrue(unit["inclusionPolicyRuleIDs"])
            self.assertEqual(unit["unresolvedApplicabilityTargetIDs"], [])
            self.assertFalse(unit["historicalSmokeBindingUsedAsPolicyEvidence"])
            self.assertEqual(sum(len(row["targetIDs"]) for row in unit["excludedTargetsByReason"]), 6)
            self.assertTrue(all(row["policyRuleIDs"] for row in unit["excludedTargetsByReason"]))

    def test_deferred_targets_never_enter_open_discovery(self) -> None:
        """Even an exact deferred ref cannot authorize a deferred target in open discovery."""

        source = {
            "eligibility": "eligible",
            "requestEligible": True,
            "validationResults": {"valid": True, "errorCodes": []},
            "deterministicNodeRefs": [],
            "deferredRecordRefs": ["deferred:exact-1"],
        }
        deferred_target = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
        binding = {"deferredRecordID": "deferred:exact-1", "operationalTargetID": deferred_target}
        open_result = evaluate_node_target_applicability(
            source,
            extraction_channel="open_discovery",
            deferred_record_bindings=[binding],
        )
        self.assertNotIn(deferred_target, open_result["eligibleTargetIDs"])
        self.assertIn(
            deferred_target,
            open_result["excludedTargetIDsByReason"]["deferred_only_target_in_open_discovery"],
        )

    def test_deferred_resolution_requires_exact_ref_and_target_binding(self) -> None:
        """Only the exact referenced deferred record and exact target authorize resolution."""

        source = {
            "eligibility": "eligible",
            "requestEligible": True,
            "validationResults": {"valid": True, "errorCodes": []},
            "deterministicNodeRefs": [],
            "deferredRecordRefs": ["deferred:exact-1"],
        }
        target = "PUB-N-A-D01-DATASETRESOURCE-EXACT-IDENTIFIER-OMITTED-BY-PHASE-B"
        missing = evaluate_node_target_applicability(
            source, extraction_channel="deferred_resolution"
        )
        wrong_ref = evaluate_node_target_applicability(
            source,
            extraction_channel="deferred_resolution",
            deferred_record_bindings=[
                {"deferredRecordID": "deferred:other", "operationalTargetID": target}
            ],
        )
        exact = evaluate_node_target_applicability(
            source,
            extraction_channel="deferred_resolution",
            deferred_record_bindings=[
                {"deferredRecordID": "deferred:exact-1", "operationalTargetID": target}
            ],
        )
        self.assertNotIn(target, missing["eligibleTargetIDs"])
        self.assertNotIn(target, wrong_ref["eligibleTargetIDs"])
        self.assertEqual(exact["eligibleTargetIDs"], [target])

    def test_deterministic_context_requires_exact_endpoint_ref(self) -> None:
        """A target label alone cannot introduce an existing endpoint candidate."""

        source = {
            "eligibility": "eligible",
            "requestEligible": True,
            "validationResults": {"valid": True, "errorCodes": []},
            "deterministicNodeRefs": ["node:exact-1"],
            "deferredRecordRefs": [],
        }
        target = "PUB-N-A-DOM02-TOOL-EXISTING-EXACT-ENDPOINT"
        absent = evaluate_node_target_applicability(
            source, extraction_channel="open_discovery"
        )
        exact = evaluate_node_target_applicability(
            source,
            extraction_channel="open_discovery",
            deterministic_endpoint_bindings=[
                {"recordID": "node:exact-1", "operationalTargetID": target}
            ],
        )
        self.assertNotIn(target, absent["eligibleTargetIDs"])
        self.assertIn(target, exact["eligibleTargetIDs"])

    def test_derivation_source_has_no_semantic_or_network_mechanism(self) -> None:
        """AST audit forbids prose-field access and semantic/network dependencies."""

        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_roots.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue(
            imported_roots.isdisjoint(
                {"openai", "requests", "urllib", "socket", "httpx", "sklearn", "numpy"}
            )
        )
        prose_field_reads = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "text"
        ]
        self.assertEqual(prose_field_reads, [])
        boundary = derive_policy()["methodologicalBoundary"]
        self.assertFalse(boundary["sourceProseInspectedForApplicability"])
        self.assertFalse(boundary["semanticClassifierAllowed"])
        self.assertFalse(boundary["keywordOrLexicalTriggerAllowed"])
        self.assertFalse(boundary["embeddingAllowed"])
        self.assertFalse(boundary["llmAllowed"])
        self.assertFalse(boundary["networkAllowed"])

    def test_generation_makes_no_network_call(self) -> None:
        """Artifact generation succeeds while common network entry points are blocked."""

        with tempfile.TemporaryDirectory() as directory:
            with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
                paths = write_policy_artifacts(Path(directory))
        self.assertEqual(len(paths), 4)

    def test_self_hashes_are_canonical_projection_hashes(self) -> None:
        """Policy and plan hashes bind their canonical contents without recursion."""

        policy = derive_policy()
        policy_projection = dict(policy)
        policy_projection.pop("policySha256")
        self.assertEqual(policy["policySha256"], sha256_bytes(canonical_json(policy_projection)))
        plan = derive_devset0_plan(policy)
        plan_projection = dict(plan)
        plan_projection.pop("planSha256")
        self.assertEqual(plan["planSha256"], sha256_bytes(canonical_json(plan_projection)))

    def test_accepted_m1_m2_and_b3_guide_hashes_remain_unchanged(self) -> None:
        """Accepted historical observations and B3 inputs retain reviewed byte hashes."""

        accepted = {
            "data/curation/papers/m1/publication_m1_recorded_raw_response.json": "21391572918e5bb17411667b5e6194b81db2cc8105be17f4461e992e35b4b00e",
            "data/curation/papers/m2/publication_m2a_exact_raw_model_output.json": "6c16dfe0c46806f7918a5e911a9c7aa5e4324fdb7baa57a92603f07d998f08ec",
            "data/curation/papers/m2/b1/publication_m2b1_attempt4_exact_structured_model_output.json": "444c10228ddffbfd30458752dfd8e2532dacb3ada44742ed06c5e07c6de4b68c",
            "data/curation/papers/m2/b2/publication_m2b2_exact_structured_model_output.json": "4f1d05c83ba0a088c23c1080fdad96de3a0b6c916c6496ca3d8d7ef30b439d5d",
            "data/curation/papers/m2/b3/publication_m2b3_exact_structured_model_output.json": "f6ca56b303e9fd61b5011f5d5d35edc097e828cda5d3637b72c44f2f119a89be",
            "src/extraction/llm/publications/prompts/publication_development_v0.1.2.txt": "d7d3fdc9a2941f28d9eba393c6067fa2b25d248a5f0f48ecfe5da2f2496ed0ca",
        }
        for relative, expected in accepted.items():
            with self.subTest(path=relative):
                actual = hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)
        guide = json.loads(
            (PROJECT_ROOT / "data/curation/papers/m2/b3/publication_m2b3_evidence_coordinate_guide.json").read_text()
        )
        self.assertEqual(
            sha256_bytes(canonical_json(guide)),
            "2be93d47efa8eed70daaa0bbbcb924f00b13fc2a0c8a297e8f1259386e172565",
        )
        artifact_sets = {
            "m1": (
                [path for path in (PROJECT_ROOT / "data/curation/papers/m1").rglob("*") if path.is_file()],
                8,
                "1b32c34011f534bb5189ea78a0e6de42bd6c400ad50b66b1eefa2d93b349e4c9",
            ),
            "m2a": (
                [
                    path
                    for path in (PROJECT_ROOT / "data/curation/papers/m2").glob("publication_m2a_*")
                    if path.is_file()
                ],
                9,
                "eb5d278056d116be647f32c5a88488a59d94034eacda1092a06d5c6cb9d515e6",
            ),
            "m2b1": (
                [path for path in (PROJECT_ROOT / "data/curation/papers/m2/b1").rglob("*") if path.is_file()],
                26,
                "f307cb3ef1ce56f32560b96dcd8a749c64abb5b2691e2dcfa142327db4e70d6b",
            ),
            "m2b2": (
                [path for path in (PROJECT_ROOT / "data/curation/papers/m2/b2").rglob("*") if path.is_file()],
                14,
                "55a11fcd1b7254f2948c95191e0b3a44441f8b9b52ffb28eeb2d3943e568a26e",
            ),
            "m2b3": (
                [path for path in (PROJECT_ROOT / "data/curation/papers/m2/b3").rglob("*") if path.is_file()],
                16,
                "d0a62bb0095e04ce5d97cb072a22986c0627630f62a64e7744c4182ca8fbc1a5",
            ),
        }
        for label, (paths, expected_count, expected_hash) in artifact_sets.items():
            with self.subTest(artifactSet=label):
                rows = [
                    (
                        str(path.relative_to(PROJECT_ROOT)),
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                    for path in sorted(paths)
                ]
                aggregate = hashlib.sha256(
                    json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                self.assertEqual(len(rows), expected_count)
                self.assertEqual(aggregate, expected_hash)


if __name__ == "__main__":
    unittest.main()
