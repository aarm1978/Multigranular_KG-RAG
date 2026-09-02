"""Focused no-network tests for M2-C1B full DEV-SET-0 node development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.extraction.llm.publications.evidence_coordinate_guide import (
    build_coordinate_guided_provider_input,
    build_evidence_coordinate_guide,
)
from src.extraction.llm.publications.openai_provider import MAX_OUTPUT_TOKENS
from src.extraction.llm.publications.request_builder import canonical_json
from src.extraction.llm.publications.openai_provider import OpenAIProviderResponseError
from src.extraction.llm.publications.run_publication_coordinate_guided_development_smoke import (
    build_m2b3_request,
)
from src.extraction.llm.publications.run_publication_full_devset0_node_development import (
    BASE_PROMPT_PATH,
    C1B_MAX_OUTPUT_TOKENS,
    DEV_IDS,
    NEW_SENTENCE,
    OLD_SENTENCE,
    HISTORICAL_PROMPT_V013_PATH,
    PROMPT_PATH,
    build_c1b_request,
    build_full_semantic_request,
    build_historical_prompt_v014_diff,
    build_prompt_semantic_diff,
    load_c0_bindings,
    prepare_unit,
    prepare_all,
    run_live_unit,
    run_unresolved_attempt_recovery,
    resolve_next_recovery_attempt,
    _validation_finding_code_counts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FullDevset0NodeDevelopmentTests(unittest.TestCase):
    """Prove all C1B units share one C0-bound, node-only, no-network configuration."""

    def test_all_requests_come_from_exact_accepted_c0_plan(self) -> None:
        """All ten requests consume plan IDs and source-unit bindings mechanically."""

        plan = json.loads(
            (
                PROJECT_ROOT
                / "data/curation/papers/m2/c0/publication_devset0_node_request_plan_v0.1.0.json"
            ).read_text(encoding="utf-8")
        )
        plan_rows = {row["developmentID"]: row for row in plan["units"]}
        bindings = load_c0_bindings()
        self.assertEqual(tuple(row["developmentID"] for row in bindings), DEV_IDS)
        for binding in bindings:
            development_id = binding["developmentID"]
            request = build_c1b_request(binding)
            with self.subTest(developmentID=development_id):
                self.assertEqual(request["primarySourceUnitID"], plan_rows[development_id]["sourceUnitID"])
                self.assertEqual(
                    request["eligibleOperationalTargetIDs"],
                    plan_rows[development_id]["eligibleNodeOperationalTargetIDs"],
                )
                self.assertEqual(len(request["eligibleOperationalTargetIDs"]), 40)

    def test_no_context_deferred_or_relation_target_leaks(self) -> None:
        """Each open-discovery request contains only the 40 direct node targets."""

        for binding in load_c0_bindings():
            request = build_c1b_request(binding)
            excluded = set(binding["excludedDeterministicContextTargetIDs"]) | set(
                binding["excludedDeferredOnlyTargetIDs"]
            )
            with self.subTest(developmentID=binding["developmentID"]):
                self.assertEqual(len(binding["excludedDeterministicContextTargetIDs"]), 4)
                self.assertEqual(len(binding["excludedDeferredOnlyTargetIDs"]), 2)
                self.assertTrue(set(request["eligibleOperationalTargetIDs"]).isdisjoint(excluded))
                self.assertEqual(binding["unresolvedApplicabilityTargetIDs"], [])
                self.assertTrue(all(row["emission_mode"] == "llm_candidate" for row in request["targetDefinitions"]))
                self.assertTrue(all(row["operational_id"].startswith("PUB-N-") for row in request["targetDefinitions"]))

    def test_full_offline_preflight_is_deterministic_and_compatible(self) -> None:
        """All ten schemas, guides, and provider inputs pass one deterministic gate."""

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = prepare_all(Path(first_dir))["preflight"]
            second = prepare_all(Path(second_dir))["preflight"]
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual(first["unitCount"], 10)
        self.assertTrue(first["allProviderCompatibilityGatesPass"])
        self.assertTrue(first["allUnitsExposeFortyNodesAndZeroRelations"])
        self.assertEqual(first["promptSemanticDiff"]["newPromptVersion"], "publication-development-0.1.4")
        self.assertGreater(first["aggregateProviderInputBytes"], 0)
        for row in first["units"]:
            with self.subTest(developmentID=row["developmentID"]):
                self.assertEqual(row["exposedNodeTargetCount"], 40)
                self.assertEqual(row["exposedRelationTargetCount"], 0)
                self.assertEqual(row["promptVersion"], "publication-development-0.1.4")
                self.assertEqual(row["schemaRefSiblingCount"], 0)
                self.assertEqual(row["schemaUnresolvedReferenceCount"], 0)
                self.assertEqual(row["schemaMissingExplicitTypeCount"], 0)
                self.assertEqual(row["schemaInvalidAnyOfBranchCount"], 0)
                self.assertGreater(row["coordinateGuideEntryCount"], 0)
                self.assertEqual(row["providerCompatibilityGate"], "PASS")

    def test_historical_prompt_v014_has_only_the_reviewed_sentence_correction(self) -> None:
        """The frozen v0.1.3 to v0.1.4 correction remains independently pinned."""

        record = build_historical_prompt_v014_diff()
        self.assertEqual(
            hashlib.sha256(HISTORICAL_PROMPT_V013_PATH.read_bytes()).hexdigest(),
            "ca68cbb6ab4b326f10993e2fdc200ad518f34a3c8020b3ac43226e0adf186a87",
        )
        self.assertEqual(record["oldSentence"], OLD_SENTENCE)
        self.assertEqual(record["newSentence"], NEW_SENTENCE)
        self.assertEqual(record["semanticSentenceChangeCount"], 1)
        self.assertTrue(record["basePromptOtherwiseByteIdentical"])
        self.assertEqual(record["newPromptSha256"], hashlib.sha256(BASE_PROMPT_PATH.read_bytes()).hexdigest())

    def test_prospective_prompt_v016_is_limited_to_trusted_metadata_binding(self) -> None:
        """v0.1.6 removes only trusted evidence-envelope reproduction."""

        record = build_prompt_semantic_diff()
        self.assertEqual(record["basePromptVersion"], "publication-development-0.1.5")
        self.assertEqual(record["newPromptVersion"], "publication-development-0.1.6")
        self.assertFalse(record["coordinateGuideTransportChanged"])
        self.assertEqual(record["coordinateGuideTransport"], "excluded_before_and_after")
        self.assertTrue(record["trustedEvidenceMetadataAuthorshipChanged"])
        self.assertTrue(record["evidenceRulesChanged"])
        self.assertEqual(record["evidenceChange"], "model authors exact evidenceText and locatorAnchor; pipeline binds trusted source metadata, coordinates, and hash")
        for key in (
            "authorizedTargetRulesChanged", "extractionCompletenessInstructionsChanged",
            "abstentionRulesChanged", "targetDefinitionContentChanged",
            "unrelatedSemanticInstructionsChanged",
        ):
            self.assertFalse(record[key])
        self.assertEqual(record["newPromptSha256"], hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest())

    def test_output_budget_is_prospective_and_historical_inputs_are_unchanged(self) -> None:
        """C1B uses accepted C1A capacity without changing older 4096-token behavior."""

        self.assertEqual(C1B_MAX_OUTPUT_TOKENS, 32768)
        self.assertEqual(MAX_OUTPUT_TOKENS, 4096)
        request = build_m2b3_request()
        guide = build_evidence_coordinate_guide(request["sourceUnit"])
        historical_input = build_coordinate_guided_provider_input(request, guide)
        self.assertEqual(
            hashlib.sha256(historical_input).hexdigest(),
            "030996ad9653ef16d628d2bf24b2e33ea8745bcfdcd570be43bd68fe9e91a802",
        )

    def test_mocked_unit_run_calls_provider_once_and_replays(self) -> None:
        """One synthetic C1B unit uses no tools and traverses deterministic downstream stages."""

        payload = {
            "candidateNodes": [],
            "candidateEdges": [],
            "evidenceSpans": [],
            "abstentions": [],
            "deferredRecords": [],
        }
        calls = []

        def transport(_api_key: str, body: dict[str, object]) -> dict[str, object]:
            """Return one completed exact-model response after checking uniform controls."""

            calls.append(body)
            self.assertEqual(body["model"], "gpt-5.6-sol")
            self.assertEqual(body["reasoning"], {"effort": "medium"})
            self.assertEqual(body["max_output_tokens"], 32768)
            self.assertFalse(body["store"])
            self.assertNotIn("tools", body)
            return {
                "id": "resp_m2c1b_synthetic",
                "object": "response",
                "created_at": 1788000000,
                "status": "completed",
                "model": "gpt-5.6-sol",
                "error": None,
                "incomplete_details": None,
                "output": [
                    {
                        "type": "message",
                        "id": "msg_m2c1b_synthetic",
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
                result = run_live_unit(
                    "DEV-10",
                    "synthetic-secret",
                    output_dir=Path(directory),
                    transport=transport,
                )
            reproducibility = json.loads((Path(directory) / "DEV-10/publication_m2c1b_dev10_reproducibility_record.json").read_text(encoding="utf-8"))
        self.assertEqual(len(calls), 1)
        self.assertTrue(result["replayByteIdentical"])
        self.assertEqual(result["diagnostics"]["candidateTotals"]["candidateNodes"], 0)
        self.assertEqual(reproducibility["promptVersion"], "publication-development-0.1.4")

    def test_full_semantic_attempt_lifecycle_reaches_terminal_completion(self) -> None:
        """A durable initiated record is updated with its terminal success outcome."""

        payload = {
            "candidateNodes": [],
            "candidateEdges": [],
            "evidenceSpans": [],
            "abstentions": [],
            "deferredRecords": [],
        }

        def transport(_api_key: str, _body: dict[str, object]) -> dict[str, object]:
            """Return a no-network completed full-semantic response."""

            return {
                "id": "resp_lifecycle_success",
                "object": "response",
                "created_at": 1788000000,
                "status": "completed",
                "model": "gpt-5.6-sol",
                "error": None,
                "incomplete_details": None,
                "output": [{"type": "message", "id": "msg", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": canonical_json(payload).decode("utf-8")}]}],
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "output_tokens_details": {"reasoning_tokens": 10}},
            }

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=transport, full_semantic=True)
            attempt_path = output_dir / "DEV-10/publication_full_semantic_dev10_attempt_record.json"
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            reproducibility = json.loads((output_dir / "DEV-10/publication_full_semantic_dev10_reproducibility_record.json").read_text(encoding="utf-8"))
        self.assertEqual(attempt["status"], "completed")
        self.assertTrue(attempt["semanticResponseProduced"])
        self.assertEqual(attempt["requestInputSha256"], build_full_semantic_request(load_c0_bindings()[-1])["requestInputSha256"])
        self.assertEqual(len(attempt["providerInputSha256"]), 64)
        self.assertEqual(len(attempt["modelAuthorableSchemaSha256"]), 64)
        self.assertEqual(reproducibility["requestSpecializedSchemaVersion"], "publication-request-specialized-0.4.0")
        self.assertEqual(reproducibility["coordinateGuideTransport"], "excluded_from_prospective_full_semantic_provider_input")

    def test_background_creation_persists_response_id_and_polls_to_completion(self) -> None:
        """Full-semantic mode persists the background ID before terminal parsing."""

        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        creation_bodies: list[dict[str, object]] = []

        def create(_key: str, body: dict[str, object]) -> dict[str, object]:
            creation_bodies.append(body)
            return {"id": "resp_background", "created_at": 1788000000, "status": "in_progress", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": []}

        def retrieve(_key: str, response_id: str) -> dict[str, object]:
            self.assertEqual(response_id, "resp_background")
            return {"id": response_id, "created_at": 1788000000, "status": "completed", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": [{"type": "message", "id": "msg", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": canonical_json(payload).decode("utf-8")}]}], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "output_tokens_details": {"reasoning_tokens": 0}}}

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=create, retrieval_transport=retrieve, full_semantic=True)
            attempt = json.loads((output_dir / "DEV-10/publication_full_semantic_dev10_attempt_record.json").read_text())
            metadata = json.loads((output_dir / "DEV-10/publication_full_semantic_dev10_provider_metadata.json").read_text())
        self.assertTrue(creation_bodies[0]["background"])
        self.assertFalse(creation_bodies[0]["store"])
        self.assertEqual(attempt["responseID"], "resp_background")
        self.assertEqual(attempt["status"], "completed")
        self.assertEqual(metadata["requestSettings"]["executionMode"], "background")

    def test_background_incomplete_response_is_preserved_without_semantics(self) -> None:
        """A terminal incomplete background response never reaches parser or validator."""

        def create(_key: str, _body: dict[str, object]) -> dict[str, object]:
            return {"id": "resp_incomplete", "created_at": 1788000000, "status": "queued", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": []}

        def retrieve(_key: str, response_id: str) -> dict[str, object]:
            return {"id": response_id, "created_at": 1788000000, "status": "incomplete", "model": "gpt-5.6-sol", "error": None, "incomplete_details": {"reason": "max_output_tokens"}, "output": [], "usage": {}}

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with self.assertRaises(OpenAIProviderResponseError):
                run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=create, retrieval_transport=retrieve, full_semantic=True)
            attempt = json.loads((output_dir / "DEV-10/publication_full_semantic_dev10_attempt_record.json").read_text())
            self.assertEqual(attempt["status"], "incomplete")
            self.assertEqual(attempt["responseID"], "resp_incomplete")
            self.assertTrue((output_dir / "DEV-10/publication_full_semantic_dev10_provider_failure_response.json").exists())
            self.assertFalse((output_dir / "DEV-10/publication_full_semantic_dev10_parser_result.json").exists())

    def test_submitted_background_attempt_resumes_by_persisted_response_id(self) -> None:
        """An interrupted poll resumes without making a second creation request."""

        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}
        creations: list[dict[str, object]] = []

        def create(_key: str, body: dict[str, object]) -> dict[str, object]:
            creations.append(body)
            return {"id": "resp_runner_resume", "created_at": 1788000000, "status": "in_progress", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": []}

        def interrupted_retrieve(_key: str, _response_id: str) -> dict[str, object]:
            raise KeyboardInterrupt("synthetic poll interruption")

        def completed_retrieve(_key: str, response_id: str) -> dict[str, object]:
            return {"id": response_id, "created_at": 1788000000, "status": "completed", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": [{"type": "message", "id": "msg", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": canonical_json(payload).decode("utf-8")}]}], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "output_tokens_details": {"reasoning_tokens": 0}}}

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with self.assertRaises(KeyboardInterrupt):
                run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=create, retrieval_transport=interrupted_retrieve, full_semantic=True)
            attempt_path = output_dir / "DEV-10/publication_full_semantic_dev10_attempt_record.json"
            self.assertEqual(json.loads(attempt_path.read_text())["status"], "submitted")
            result = run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, retrieval_transport=completed_retrieve, full_semantic=True, resume=True)
        self.assertEqual(len(creations), 1)
        self.assertEqual(result["providerResponse"]["responseID"], "resp_runner_resume")

    def test_recovery_preserves_prior_unresolved_attempt(self) -> None:
        """Explicit recovery creates a separate attempt without overwriting prior evidence."""

        payload = {"candidateNodes": [], "candidateEdges": [], "evidenceSpans": [], "abstentions": [], "deferredRecords": []}

        def create(_key: str, _body: dict[str, object]) -> dict[str, object]:
            return {"id": "resp_recovery", "created_at": 1788000000, "status": "completed", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": [{"type": "message", "id": "msg", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": canonical_json(payload).decode("utf-8")}]}], "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "output_tokens_details": {"reasoning_tokens": 0}}}

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            prior_path = output_dir / "DEV-02/publication_full_semantic_dev02_attempt_record.json"
            prior_path.parent.mkdir(parents=True)
            prior_path.write_text(json.dumps({"developmentID": "DEV-02", "attemptCount": 1, "status": "initiated", "providerInputSha256": "prior"}, sort_keys=True) + "\n")
            prior_bytes = prior_path.read_bytes()
            result = run_unresolved_attempt_recovery("DEV-02", "synthetic-secret", output_dir=output_dir, transport=create)
            recovery_attempt = next((output_dir / "DEV-02/researcher_authorized_recovery_001").rglob("*_attempt_record.json"))
            recovery = json.loads(recovery_attempt.read_text())
            self.assertEqual(prior_path.read_bytes(), prior_bytes)
        self.assertEqual(result["providerResponse"]["responseID"], "resp_recovery")
        self.assertEqual(recovery["attemptCount"], 2)
        self.assertEqual(recovery["recoveryOf"]["priorAttemptStatus"], "initiated")

    def test_resolve_terminal_incomplete_recovery_advances_without_writing(self) -> None:
        """A terminal recovery resolves the next chain link without creating it."""

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            root = output_dir / "DEV-02/publication_full_semantic_dev02_attempt_record.json"
            second = output_dir / "DEV-02/researcher_authorized_recovery_001/DEV-02/publication_full_semantic_dev02_attempt_record.json"
            root.parent.mkdir(parents=True); second.parent.mkdir(parents=True)
            root.write_bytes(b'{"attemptCount":1,"status":"initiated"}\n')
            second.write_bytes(b'{"attemptCount":2,"responseID":"resp_attempt_2","status":"incomplete"}\n')
            root_bytes, second_bytes = root.read_bytes(), second.read_bytes()
            resolved = resolve_next_recovery_attempt(output_dir, "DEV-02")
            self.assertEqual(resolved["recoveryRoot"], output_dir / "DEV-02/researcher_authorized_recovery_002")
            self.assertEqual(resolved["attemptCount"], 3)
            self.assertEqual(resolved["recoveryOf"]["priorAttemptPath"], "DEV-02/researcher_authorized_recovery_001/DEV-02/publication_full_semantic_dev02_attempt_record.json")
            self.assertEqual(resolved["recoveryOf"]["priorAttemptStatus"], "incomplete")
            self.assertEqual(resolved["recoveryOf"]["priorAttemptResponseID"], "resp_attempt_2")
            self.assertEqual(resolved["recoveryOf"]["priorAttemptSha256"], hashlib.sha256(second_bytes).hexdigest())
            self.assertEqual(root.read_bytes(), root_bytes); self.assertEqual(second.read_bytes(), second_bytes)
            self.assertFalse(resolved["recoveryRoot"].exists())

    def test_resolve_submitted_response_requires_resumption(self) -> None:
        """A persisted submitted response can never be redispatched."""

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            attempt = output_dir / "DEV-02/publication_full_semantic_dev02_attempt_record.json"
            attempt.parent.mkdir(parents=True)
            attempt.write_text('{"attemptCount":1,"responseID":"resp_submitted","status":"submitted"}\n')
            with self.assertRaisesRegex(ValueError, "exact-response resumption"):
                resolve_next_recovery_attempt(output_dir, "DEV-02")
            self.assertFalse((output_dir / "DEV-02/researcher_authorized_recovery_001").exists())

    def test_interrupted_full_semantic_attempt_remains_auditable_and_blocks_retry(self) -> None:
        """An interruption leaves initiated state and prevents automatic redispatch."""

        dispatches: list[dict[str, object]] = []

        def interrupted_transport(_api_key: str, body: dict[str, object]) -> dict[str, object]:
            """Simulate external interruption after the durable lifecycle write."""

            dispatches.append(body)
            raise KeyboardInterrupt("synthetic interruption")

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with self.assertRaises(KeyboardInterrupt):
                run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=interrupted_transport, full_semantic=True)
            attempt_path = output_dir / "DEV-10/publication_full_semantic_dev10_attempt_record.json"
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
            self.assertEqual(attempt["status"], "initiated")
            self.assertFalse(attempt["semanticResponseProduced"])
            self.assertEqual(attempt["developmentID"], "DEV-10")
            self.assertEqual(len(attempt["providerInputSha256"]), 64)
            with self.assertRaisesRegex(ValueError, "already has a provider-attempt artifact"):
                run_live_unit("DEV-10", "synthetic-secret", output_dir=output_dir, transport=interrupted_transport, full_semantic=True)
        self.assertEqual(len(dispatches), 1)

    def test_dev02_full_semantic_provider_input_remains_identical_offline(self) -> None:
        """DEV-02's large request remains deterministic without provider dispatch."""

        binding = next(row for row in load_c0_bindings() if row["developmentID"] == "DEV-02")
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = prepare_unit(binding, output_dir=Path(first_dir), full_semantic=True)
            second = prepare_unit(binding, output_dir=Path(second_dir), full_semantic=True)
        self.assertEqual(first["providerInput"], second["providerInput"])
        self.assertEqual(
            hashlib.sha256(first["providerInput"]).hexdigest(),
            "ea450a435e747dc3cda0d12120a6424a6af09380d4429576ee173e97f3be3874",
        )

    def test_aggregate_finding_frequencies_count_occurrences_not_units(self) -> None:
        """Repeated authoritative findings retain their actual occurrence frequency."""

        validation = {
            "globalFindings": [{"code": "GLOBAL"}],
            "evidenceResults": [
                {"findings": [{"code": "OFFSET"}, {"code": "OFFSET"}]},
                {"findings": [{"code": "OFFSET"}]},
            ],
            "recordResults": [
                {"findings": [{"code": "NODE"}]},
                {"findings": [{"code": "NODE"}, {"code": "NODE"}]},
            ],
        }
        self.assertEqual(
            dict(_validation_finding_code_counts(validation)),
            {"GLOBAL": 1, "OFFSET": 3, "NODE": 3},
        )

    def test_accepted_historical_artifacts_remain_byte_identical(self) -> None:
        """Representative accepted artifacts and complete C0/C1A directories are unchanged."""

        accepted = {
            "schemas/publication_candidate_output.schema.json": "50132ce01a16a21736f65e4b5d4b0354b3d1c53f07878352159d6ff36e94fce2",
            "src/extraction/llm/publications/publication_target_inventory.yaml": "6401c15b861c2362b67e03d56acd4a7304964f595d706311fd4f149eb69b3a5e",
            "src/extraction/llm/publications/prompts/publication_development_v0.1.3.txt": "ca68cbb6ab4b326f10993e2fdc200ad518f34a3c8020b3ac43226e0adf186a87",
            "data/curation/papers/m2/c1a/publication_m2c1a_exact_structured_model_output.json": "db63a5f9cbb4e9f10d537f56d17ce54fac2c20266f067e10bd94d4f3ed696a0b",
            "data/curation/papers/m2/b3/publication_m2b3_exact_structured_model_output.json": "f6ca56b303e9fd61b5011f5d5d35edc097e828cda5d3637b72c44f2f119a89be",
        }
        for relative, expected in accepted.items():
            with self.subTest(path=relative):
                self.assertEqual(
                    hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest(),
                    expected,
                )
        directories = {
            "c0": (
                PROJECT_ROOT / "data/curation/papers/m2/c0",
                4,
                "9b240739c4a4469746313a327c2474ddfcd97ece41d008a079612d3b47c377ec",
            ),
            "c1a": (
                PROJECT_ROOT / "data/curation/papers/m2/c1a",
                18,
                "b799a35caa86108eaa2e94bd4ce1f7f14fdca22e0386fcbfe8bd3de8b765fad1",
            ),
        }
        for label, (directory, count, expected) in directories.items():
            rows = [
                (
                    str(path.relative_to(PROJECT_ROOT)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in sorted(directory.rglob("*"))
                if path.is_file()
            ]
            aggregate = hashlib.sha256(
                json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            with self.subTest(directory=label):
                self.assertEqual(len(rows), count)
                self.assertEqual(aggregate, expected)


if __name__ == "__main__":
    unittest.main()
