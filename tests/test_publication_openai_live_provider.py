"""Focused no-network tests for the Publication M2-A OpenAI live adapter."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.openai_provider import (  # noqa: E402
    REASONING_EFFORT,
    REQUESTED_MODEL,
    STORE,
    OpenAIProviderError,
    build_provider_input,
    build_responses_api_request,
    call_openai_responses,
    load_openai_api_key,
)
from src.extraction.llm.publications.request_builder import (  # noqa: E402
    build_development_request,
)
from src.extraction.llm.publications.run_publication_live_development_smoke import (  # noqa: E402
    AUTHORIZED_TARGETS,
    RUN_ID,
    SOURCE_UNIT_ID,
    replay_preserved,
    run_live_smoke,
)


FIXTURE_PATH = (
    PROJECT_ROOT / "data/curation/papers/m1/publication_m1_recorded_raw_response.json"
)


def synthetic_api_response(output_text: str) -> dict[str, Any]:
    """Return one completed Responses API-shaped synthetic response."""

    return {
        "id": "resp_m2a_synthetic",
        "object": "response",
        "created_at": 1787832000,
        "status": "completed",
        "model": "gpt-5.6-sol",
        "output": [
            {
                "type": "message",
                "id": "msg_synthetic",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output_text}],
            }
        ],
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 300,
            "total_tokens": 1500,
            "output_tokens_details": {"reasoning_tokens": 100},
        },
        "incomplete_details": None,
        "error": None,
    }


class OpenAIProviderConfigurationTests(unittest.TestCase):
    """Verify exact provider configuration and safe credential handling."""

    def test_missing_api_key_fails_without_echoing_any_value(self) -> None:
        """An absent key fails before a provider call with a fixed safe message."""

        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / ".env"
            with self.assertRaisesRegex(OpenAIProviderError, "OPENAI_API_KEY is unavailable"):
                load_openai_api_key({}, env_path=missing)

    def test_exact_model_reasoning_and_no_tool_or_state_configuration(self) -> None:
        """The API body pins Sol/medium/store=false and exposes no tools or retrieval."""

        body = build_responses_api_request(b"bounded input")
        self.assertEqual(body["model"], REQUESTED_MODEL)
        self.assertEqual(REQUESTED_MODEL, "gpt-5.6-sol")
        self.assertEqual(body["reasoning"], {"effort": REASONING_EFFORT})
        self.assertEqual(REASONING_EFFORT, "medium")
        self.assertIs(body["store"], STORE)
        self.assertFalse(STORE)
        for prohibited in ("tools", "previous_response_id", "conversation", "web_search", "file_search"):
            self.assertNotIn(prohibited, body)

    def test_provider_input_is_bounded_and_excludes_pipeline_owned_output_metadata(self) -> None:
        """The model sees M1 semantic request content but cannot author envelope metadata."""

        request = build_development_request(
            SOURCE_UNIT_ID, AUTHORIZED_TARGETS, run_id=RUN_ID
        )
        provider_input = build_provider_input(request).decode("utf-8")
        supplied = json.loads(
            provider_input.split("Bounded trusted development request JSON:\n", 1)[1]
        )
        self.assertEqual(supplied["eligibleOperationalTargetIDs"], AUTHORIZED_TARGETS)
        self.assertEqual(supplied["primarySourceUnitID"], SOURCE_UNIT_ID)
        self.assertNotIn("offlineResponseMetadata", supplied)
        self.assertNotIn("authorities", supplied)
        self.assertNotIn("requestInputSha256", supplied)
        self.assertNotIn("metadata", supplied)

    def test_model_output_and_provider_metadata_remain_separate(self) -> None:
        """Exact model bytes are returned separately from credential-free API metadata."""

        expected = FIXTURE_PATH.read_bytes()

        def transport(_key: str, _body: Mapping[str, Any]) -> dict[str, Any]:
            """Return one synthetic response without network access."""

            return synthetic_api_response(expected.decode("utf-8"))

        actual, metadata = call_openai_responses("synthetic-secret", b"input", transport=transport)
        self.assertEqual(actual, expected)
        self.assertNotIn("output", metadata)
        self.assertNotIn(expected.decode("utf-8"), json.dumps(metadata))
        self.assertEqual(metadata["rawModelOutputSha256"], __import__("hashlib").sha256(expected).hexdigest())


class OpenAILivePipelineTests(unittest.TestCase):
    """Exercise mocked valid and malformed outputs through unchanged M1 stages."""

    def test_mocked_valid_response_reaches_validator_and_replays_identically(self) -> None:
        """The authentic fixture payload traverses parser, validator, usable output, and replay."""

        expected = FIXTURE_PATH.read_text(encoding="utf-8")
        call_count = 0

        def transport(_key: str, body: Mapping[str, Any]) -> dict[str, Any]:
            """Assert configuration and return one synthetic successful response."""

            nonlocal call_count
            call_count += 1
            self.assertEqual(body["model"], "gpt-5.6-sol")
            self.assertNotIn("tools", body)
            return synthetic_api_response(expected)

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            result = run_live_smoke(
                "synthetic-secret", output_dir=output_dir, transport=transport
            )
            replay = replay_preserved(output_dir)
        self.assertEqual(call_count, 1)
        self.assertEqual(result["parserResult"]["parseStatus"], "parsed")
        self.assertEqual(result["validation"]["envelopeStatus"], "valid")
        self.assertEqual(len(result["usablePipelineOutput"]["candidateNodes"]), 1)
        self.assertTrue(replay["byteIdentical"])

    def test_malformed_model_output_is_preserved_and_fails_honestly(self) -> None:
        """Malformed bytes are not repaired and remain the exact saved model output."""

        malformed = '{"candidateNodes": ['

        def transport(_key: str, _body: Mapping[str, Any]) -> dict[str, Any]:
            """Return malformed model text inside a successful provider response."""

            return synthetic_api_response(malformed)

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            result = run_live_smoke(
                "synthetic-secret", output_dir=output_dir, transport=transport
            )
            preserved = Path(result["artifactPaths"]["rawModelOutput"]).read_bytes()
        self.assertEqual(preserved, malformed.encode("utf-8"))
        self.assertEqual(result["parserResult"]["parseStatus"], "processing_failed")
        self.assertEqual(result["validation"]["envelopeStatus"], "processing_failed")

    def test_pipeline_owned_injection_is_preserved_but_rejected(self) -> None:
        """A model-authored metadata attempt cannot replace trusted pipeline bindings."""

        payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        payload["metadata"] = {"provider": "model-controlled"}

        def transport(_key: str, _body: Mapping[str, Any]) -> dict[str, Any]:
            """Return one forbidden injection attempt without network access."""

            return synthetic_api_response(json.dumps(payload, separators=(",", ":")))

        with tempfile.TemporaryDirectory() as temporary_directory:
            result = run_live_smoke(
                "synthetic-secret",
                output_dir=Path(temporary_directory),
                transport=transport,
            )
        self.assertEqual(
            result["parserResult"]["pipelineOwnedFieldInjectionAttempts"], ["metadata"]
        )
        self.assertEqual(result["validation"]["envelopeStatus"], "invalid")
        self.assertEqual(
            result["parserResult"]["parsedEnvelope"]["metadata"]["provider"], "OpenAI"
        )


if __name__ == "__main__":
    unittest.main()
