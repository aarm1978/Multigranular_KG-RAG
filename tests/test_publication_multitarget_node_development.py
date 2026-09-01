"""Focused no-network tests for M2-C1A multi-target node development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications.evidence_coordinate_guide import (
    audit_evidence_coordinate_guide,
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.openai_provider import (
    MAX_OUTPUT_TOKENS,
    build_responses_api_request,
)
from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.run_publication_coordinate_guided_development_smoke import (
    build_m2b3_request,
)
from src.extraction.llm.publications.run_publication_multitarget_node_development import (
    BASE_PROMPT_PATH,
    C1A_MAX_OUTPUT_TOKENS,
    DEVELOPMENT_ID,
    EXPECTED_DIRECT_NODE_TARGET_COUNT,
    PROMPT_PATH,
    PROMPT_VERSION,
    SOURCE_UNIT_ID,
    _exposed_targets,
    _persist_pre_live_artifacts,
    build_c1a_request,
    build_prompt_semantic_diff,
    load_c0_dev01_binding,
    run_multitarget_node_live_extraction,
)
from src.extraction.llm.publications.request_specialized_schema import (
    derive_request_specialized_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MultiTargetNodeDevelopmentTests(unittest.TestCase):
    """Prove C1A is C0-bound, node-only, compatible, and historically isolated."""

    def test_dev01_targets_are_loaded_exactly_from_accepted_c0_plan(self) -> None:
        """The request mechanically consumes the one accepted DEV-01 plan row."""

        plan = json.loads(
            (
                PROJECT_ROOT
                / "data/curation/papers/m2/c0/publication_devset0_node_request_plan_v0.1.0.json"
            ).read_text(encoding="utf-8")
        )
        plan_unit = next(row for row in plan["units"] if row["developmentID"] == DEVELOPMENT_ID)
        binding = load_c0_dev01_binding()
        request = build_c1a_request()
        self.assertEqual(request["primarySourceUnitID"], SOURCE_UNIT_ID)
        self.assertEqual(
            request["eligibleOperationalTargetIDs"],
            plan_unit["eligibleNodeOperationalTargetIDs"],
        )
        self.assertEqual(
            request["eligibleOperationalTargetIDs"],
            binding["eligibleNodeOperationalTargetIDs"],
        )
        self.assertEqual(len(request["eligibleOperationalTargetIDs"]), 40)

    def test_request_excludes_context_deferred_and_relation_targets(self) -> None:
        """Only the 40 direct node targets may enter C1A open discovery."""

        binding = load_c0_dev01_binding()
        request = build_c1a_request()
        self.assertEqual(len(binding["excludedDeterministicContextTargetIDs"]), 4)
        self.assertEqual(len(binding["excludedDeferredOnlyTargetIDs"]), 2)
        self.assertTrue(
            set(request["eligibleOperationalTargetIDs"]).isdisjoint(
                binding["excludedDeterministicContextTargetIDs"]
                + binding["excludedDeferredOnlyTargetIDs"]
            )
        )
        self.assertTrue(all(row["emission_mode"] == "llm_candidate" for row in request["targetDefinitions"]))
        self.assertTrue(all(row["operational_id"].startswith("PUB-N-") for row in request["targetDefinitions"]))
        self.assertEqual(binding["unresolvedApplicabilityTargetIDs"], [])

    def test_specialized_schema_exposes_exactly_the_c0_node_targets(self) -> None:
        """The strict schema has 40 node IDs and no relation operational ID."""

        request = build_c1a_request()
        schema = derive_request_specialized_schema(request)
        self.assertEqual(
            _exposed_targets(schema, "operationalTargetID"),
            sorted(request["eligibleOperationalTargetIDs"]),
        )
        self.assertEqual(_exposed_targets(schema, "operationalRelationID"), [])
        self.assertEqual(schema["properties"]["candidateEdges"]["maxItems"], 0)

    def test_schema_action_and_identity_constraints_follow_target_definitions(self) -> None:
        """Every exposed branch retains frozen action and source-local identity constraints."""

        request = build_c1a_request()
        schema = derive_request_specialized_schema(request)
        branches = schema["properties"]["candidateNodes"]["items"]["anyOf"]
        definitions = {row["operational_id"]: row for row in request["targetDefinitions"]}
        self.assertEqual(len(branches), EXPECTED_DIRECT_NODE_TARGET_COUNT)
        for branch in branches:
            properties = branch["properties"]
            target_id = properties["operationalTargetID"]["const"]
            with self.subTest(target=target_id):
                self.assertIn(properties["action"]["const"], definitions[target_id]["allowed_actions"])
                self.assertEqual(properties["identityScope"]["const"], "source_local")
                self.assertEqual(properties["artifactScope"]["const"], "source_artifact")
                self.assertEqual(properties["origin"]["const"], "open_discovery")

    def test_dev01_coordinate_guide_satisfies_all_accepted_invariants(self) -> None:
        """The unchanged guide is deterministic, exact, ordered, and Unicode code-point based."""

        source = build_c1a_request()["sourceUnit"]
        first = build_evidence_coordinate_guide(source)
        second = build_evidence_coordinate_guide(source)
        self.assertEqual(canonical_json(first), canonical_json(second))
        audit = audit_evidence_coordinate_guide(source, first)
        self.assertTrue(audit["valid"], audit["findings"])
        self.assertGreater(audit["entryCount"], 0)
        for entry in first["entries"]:
            start, end = entry["startOffsetInUnit"], entry["endOffsetInUnit"]
            self.assertEqual(source["text"][start:end], entry["tokenText"])
            self.assertEqual(
                entry["startOffsetInDocument"],
                source["startOffsetInDocument"] + start,
            )
            self.assertEqual(
                entry["endOffsetInDocument"],
                source["startOffsetInDocument"] + end,
            )

    def test_prompt_diff_is_only_version_and_coverage_instruction(self) -> None:
        """v0.1.2 remains frozen and v0.1.3 has only the reviewed prospective change."""

        record = build_prompt_semantic_diff()
        self.assertEqual(
            hashlib.sha256(BASE_PROMPT_PATH.read_bytes()).hexdigest(),
            "d7d3fdc9a2941f28d9eba393c6067fa2b25d248a5f0f48ecfe5da2f2496ed0ca",
        )
        self.assertEqual(record["newPromptVersion"], PROMPT_VERSION)
        self.assertEqual(record["newPromptSha256"], hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest())
        self.assertTrue(record["basePromptOtherwiseByteIdentical"])
        self.assertFalse(record["unrelatedExtractionInstructionsChanged"])
        self.assertEqual(record["removedSemanticInstructions"], [])

    def test_c1a_output_override_preserves_historical_default_and_b3_input(self) -> None:
        """C1A gets 32768 capacity while historical provider behavior remains 4096."""

        default_body = build_responses_api_request(b"bounded")
        c1a_body = build_responses_api_request(
            b"bounded", max_output_tokens=C1A_MAX_OUTPUT_TOKENS
        )
        self.assertEqual(default_body["max_output_tokens"], MAX_OUTPUT_TOKENS)
        self.assertEqual(MAX_OUTPUT_TOKENS, 4096)
        self.assertEqual(c1a_body["max_output_tokens"], 32768)
        b3_request = build_m2b3_request()
        b3_guide = build_evidence_coordinate_guide(b3_request["sourceUnit"])
        b3_input = build_coordinate_guided_provider_input(b3_request, b3_guide)
        self.assertEqual(
            hashlib.sha256(b3_input).hexdigest(),
            "030996ad9653ef16d628d2bf24b2e33ea8745bcfdcd570be43bd68fe9e91a802",
        )

    def test_preflight_is_deterministic_and_passes_complete_gate(self) -> None:
        """Repeated no-network preflight produces identical strict-provider records."""

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = _persist_pre_live_artifacts(Path(first_dir))
            second = _persist_pre_live_artifacts(Path(second_dir))
        self.assertEqual(canonical_json(first["preflight"]), canonical_json(second["preflight"]))
        preflight = first["preflight"]
        self.assertEqual(preflight["providerCompatibilityGate"], "PASS")
        self.assertEqual(preflight["eligibleNodeOperationalTargetCount"], 40)
        self.assertEqual(preflight["relationTargetsIncluded"], 0)
        for key in (
            "schemaRefSiblingCount",
            "schemaUnresolvedRefCount",
            "schemaConstMissingExplicitTypeCount",
            "schemaEnumMissingExplicitTypeCount",
            "schemaIncompatibleDirectConstraintCount",
            "schemaInvalidAnyOfBranchCount",
        ):
            self.assertEqual(preflight[key], 0)

    def test_mocked_runner_calls_provider_once_without_tools_and_replays(self) -> None:
        """One synthetic response uses the C1A controls and deterministic downstream replay."""

        payload = {
            "candidateNodes": [],
            "candidateEdges": [],
            "evidenceSpans": [],
            "abstentions": [],
            "deferredRecords": [],
        }
        calls = []

        def transport(_api_key: str, body: dict[str, object]) -> dict[str, object]:
            """Return one completed exact-model response after inspecting controls."""

            calls.append(body)
            self.assertEqual(body["model"], "gpt-5.6-sol")
            self.assertEqual(body["reasoning"], {"effort": "medium"})
            self.assertEqual(body["max_output_tokens"], 32768)
            self.assertFalse(body["store"])
            self.assertNotIn("tools", body)
            self.assertIn("COMPLETE AUTHORIZED TARGET-SPACE SEARCH", body["input"])
            return {
                "id": "resp_m2c1a_synthetic",
                "object": "response",
                "created_at": 1788000000,
                "status": "completed",
                "model": "gpt-5.6-sol",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "type": "message",
                        "id": "msg_m2c1a_synthetic",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": canonical_json(payload).decode("utf-8"),
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "output_tokens_details": {"reasoning_tokens": 10},
                },
            }

        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "src.extraction.llm.publications.openai_provider.urlopen",
                side_effect=AssertionError("ordinary tests must not use network"),
            ):
                result = run_multitarget_node_live_extraction(
                    "synthetic-secret", output_dir=Path(directory), transport=transport
                )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["parserResult"]["parseStatus"], "parsed")
        self.assertTrue(result["replayByteIdentical"])
        self.assertEqual(result["diagnostics"]["candidateTotals"]["candidateNodes"], 0)

    def test_accepted_c0_b3_and_frozen_artifacts_remain_byte_identical(self) -> None:
        """Representative accepted authorities and historical artifacts retain reviewed hashes."""

        accepted = {
            "schemas/publication_candidate_output.schema.json": "50132ce01a16a21736f65e4b5d4b0354b3d1c53f07878352159d6ff36e94fce2",
            "src/extraction/llm/publications/publication_target_inventory.yaml": "6401c15b861c2362b67e03d56acd4a7304964f595d706311fd4f149eb69b3a5e",
            "src/extraction/llm/publications/request_builder.py": "9f45a128b09e05d174868eef072d84727844cecb72e473818fca9f08da405a21",
            "src/extraction/llm/publications/response_parser.py": "8f5ee5c455868240f8de8451611999c82354873cd4422a2d311de0566146eec2",
            "src/extraction/llm/publications/candidate_validation.py": "8c6074aa5708f519b73612ff7f1574de8311180d7b4a0e36551f6529415611d9",
            "src/extraction/llm/publications/evidence_coordinate_guide.py": "d677a5b01d05357d14b404942f6024d6dc195ce6275a5cb771e5fbfa7624af29",
            "src/extraction/llm/publications/prompts/publication_development_v0.1.2.txt": "d7d3fdc9a2941f28d9eba393c6067fa2b25d248a5f0f48ecfe5da2f2496ed0ca",
            "data/curation/papers/m2/b3/publication_m2b3_exact_structured_model_output.json": "f6ca56b303e9fd61b5011f5d5d35edc097e828cda5d3637b72c44f2f119a89be",
            "data/curation/papers/m2/c0/publication_node_target_applicability_policy_v0.1.0.json": "856041ed782457ecd8176833adb1714cac496ae124dfba7e760c2561b9266da3",
            "data/curation/papers/m2/c0/publication_node_target_applicability_audit_v0.1.0.json": "a8df1e294034851824605019b166a6fbccbe1e61a64782982e9fb71c189aad8e",
            "data/curation/papers/m2/c0/publication_devset0_node_request_plan_v0.1.0.json": "8c0c8b11e31f22738e56e103891ecfb8e7947860c57a159e51fa68cf645d73d8",
            "data/curation/papers/m2/c0/publication_devset0_node_request_plan_v0.1.0.md": "bdc352b2e8b38b98016c95aad4b728d62860f8a11072f23e5572ebe63caaae0b",
        }
        for relative, expected in accepted.items():
            with self.subTest(path=relative):
                self.assertEqual(
                    hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
