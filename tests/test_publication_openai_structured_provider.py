"""No-network provider-guard and M2-B1 structured smoke tests."""

from __future__ import annotations

import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from typing import Any, Mapping
from urllib.error import HTTPError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from src.extraction.llm.publications.model_authorable_schema import (  # noqa: E402
    derive_model_authorable_schema,
)
from src.extraction.llm.publications.openai_provider import (  # noqa: E402
    OPENAI_RESPONSES_URL,
    OpenAIHTTPError,
    OpenAIProviderResponseError,
    _http_post_json,
    build_responses_api_request,
    call_openai_background_responses_detailed,
    call_openai_responses_detailed,
    resume_openai_background_response_detailed,
)
from src.extraction.llm.publications.request_builder import sha256_bytes  # noqa: E402
from src.extraction.llm.publications.run_publication_structured_development_smoke import (  # noqa: E402
    AUTHORIZED_TARGETS,
    PROMPT_PATH,
    PROMPT_VERSION,
    SOURCE_UNIT_ID,
    build_m2b1_request,
    run_structured_live_smoke,
)


VALID_FIXTURE = (
    PROJECT_ROOT / "data/curation/papers/m1/publication_m1_recorded_raw_response.json"
)


def synthetic_response(output_text: str) -> dict[str, Any]:
    """Return one completed exact-model Responses API-shaped response."""

    return {
        "id": "resp_m2b1_synthetic",
        "object": "response",
        "created_at": 1787835600,
        "status": "completed",
        "model": "gpt-5.6-sol",
        "output": [
            {
                "type": "message",
                "id": "msg_m2b1_synthetic",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": output_text}],
            }
        ],
        "usage": {
            "input_tokens": 1300,
            "output_tokens": 350,
            "total_tokens": 1650,
            "output_tokens_details": {"reasoning_tokens": 110},
        },
        "incomplete_details": None,
        "error": None,
    }


class StructuredProviderConfigurationTests(unittest.TestCase):
    """Verify strict Responses API configuration and exact prompt binding."""

    def test_structured_output_uses_current_responses_text_format(self) -> None:
        """The request carries strict json_schema under text.format and no tools."""

        schema = derive_model_authorable_schema()
        body = build_responses_api_request(
            b"bounded input", model_authorable_schema=schema
        )
        self.assertEqual(body["model"], "gpt-5.6-sol")
        self.assertEqual(body["reasoning"], {"effort": "medium"})
        self.assertFalse(body["store"])
        self.assertNotIn("tools", body)
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertTrue(body["text"]["format"]["strict"])
        self.assertEqual(body["text"]["format"]["schema"], schema)

    def test_prompt_v011_and_dev04_request_are_exactly_bounded(self) -> None:
        """The new request uses v0.1.1 and only the authorized Finding target."""

        request = build_m2b1_request()
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.assertEqual(request["primarySourceUnitID"], SOURCE_UNIT_ID)
        self.assertEqual(request["eligibleOperationalTargetIDs"], AUTHORIZED_TARGETS)
        self.assertEqual(request["prompt"]["version"], PROMPT_VERSION)
        self.assertEqual(request["prompt"]["sha256"], sha256_bytes(PROMPT_PATH.read_bytes()))
        self.assertIn("REQUIRED LOCAL OUTPUT IDENTIFIERS", prompt)
        self.assertIn("TRUSTED IDENTIFIERS", prompt)
        self.assertIn("node-0001", prompt)
        self.assertIn("evidence-0001", prompt)


class ProviderSafetyGuardTests(unittest.TestCase):
    """Reject incomplete, errored, or substituted responses before semantics."""

    def _assert_rejected(self, response: Mapping[str, Any], code: str) -> None:
        """Assert a mocked provider response fails with one stable safe code."""

        def transport(_key: str, _body: Mapping[str, Any]) -> dict[str, Any]:
            """Return the selected mocked response without network access."""

            return deepcopy(dict(response))

        with self.assertRaises(OpenAIProviderResponseError) as caught:
            call_openai_responses_detailed(
                "synthetic-secret",
                b"input",
                model_authorable_schema=derive_model_authorable_schema(),
                transport=transport,
            )
        self.assertEqual(caught.exception.failure_code, code)

    def test_noncompleted_status_is_rejected(self) -> None:
        """A non-completed status cannot enter candidate processing."""

        response = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        response["status"] = "incomplete"
        self._assert_rejected(response, "STATUS_NOT_COMPLETED")

    def test_provider_error_is_rejected(self) -> None:
        """A response carrying provider error details cannot enter semantics."""

        response = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        response["error"] = {"code": "provider_error"}
        self._assert_rejected(response, "PROVIDER_ERROR_PRESENT")

    def test_incomplete_details_are_rejected(self) -> None:
        """Incomplete details fail closed even if status is unexpectedly completed."""

        response = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        response["incomplete_details"] = {"reason": "max_output_tokens"}
        self._assert_rejected(response, "INCOMPLETE_DETAILS_PRESENT")

    def test_model_substitution_is_rejected_exactly(self) -> None:
        """A versioned alias or fallback is not accepted for the exact model contract."""

        response = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        response["model"] = "gpt-5.6-sol-2026-08-01"
        self._assert_rejected(response, "RETURNED_MODEL_MISMATCH")

    def test_failed_response_is_preserved_without_semantic_artifacts(self) -> None:
        """The runner records a rejected provider response before stopping semantics."""

        response = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        response["status"] = "incomplete"

        def transport(_key: str, _body: Mapping[str, Any]) -> dict[str, Any]:
            """Return one incomplete provider response without network access."""

            return response

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            with self.assertRaises(OpenAIProviderResponseError):
                run_structured_live_smoke(
                    "synthetic-secret", output_dir=output_dir, transport=transport
                )
            self.assertTrue(
                (
                    output_dir
                    / "publication_m2b1_attempt4_provider_failure_response.json"
                ).exists()
            )
            self.assertTrue(
                (
                    output_dir
                    / "publication_m2b1_attempt4_provider_failure_metadata.json"
                ).exists()
            )
            self.assertFalse(
                (output_dir / "publication_m2b1_attempt4_parser_result.json").exists()
            )

    def test_background_interruption_resumes_by_persisted_response_id(self) -> None:
        """Polling can resume a created response without a second creation request."""

        created = {"id": "resp_resume", "created_at": 1787835600, "status": "in_progress", "model": "gpt-5.6-sol", "error": None, "incomplete_details": None, "output": []}
        completed = synthetic_response(VALID_FIXTURE.read_text(encoding="utf-8"))
        completed["id"] = "resp_resume"
        creations: list[Mapping[str, Any]] = []

        def create(_key: str, body: Mapping[str, Any]) -> dict[str, Any]:
            creations.append(body)
            return deepcopy(created)

        def interrupt(_created: Mapping[str, Any], _body: Mapping[str, Any]) -> None:
            raise KeyboardInterrupt("synthetic interruption after ID persistence")

        with self.assertRaises(KeyboardInterrupt):
            call_openai_background_responses_detailed(
                "synthetic-secret", b"input", creation_transport=create,
                on_response_created=interrupt,
            )
        raw, metadata, response = resume_openai_background_response_detailed(
            "synthetic-secret", "resp_resume", b"input",
            retrieval_transport=lambda _key, response_id: completed if response_id == "resp_resume" else {},
            sleep=lambda _seconds: None,
        )
        self.assertEqual(len(creations), 1)
        self.assertTrue(creations[0]["background"])
        self.assertEqual(response["id"], "resp_resume")
        self.assertEqual(metadata["requestSettings"]["executionMode"], "background")
        self.assertTrue(raw)


class ProviderHTTPErrorAuditTests(unittest.TestCase):
    """Preserve safe HTTP failure diagnostics without credential-bearing headers."""

    @staticmethod
    def _raise_http_error(body: bytes, content_type: str) -> HTTPError:
        """Build one urllib HTTP 400 carrying deterministic response bytes."""

        return HTTPError(
            OPENAI_RESPONSES_URL,
            400,
            "Bad Request",
            {"content-type": content_type, "x-request-id": "req_http_audit"},
            io.BytesIO(body),
        )

    def test_json_http_400_body_and_request_id_are_preserved(self) -> None:
        """A JSON provider error retains exact safe bytes and decoded content."""

        body = b'{"error":{"code":"invalid_json_schema","message":"unsupported"}}'
        error = self._raise_http_error(body, "application/json")
        request = build_responses_api_request(
            b"bounded", model_authorable_schema=derive_model_authorable_schema()
        )
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=error,
        ):
            with self.assertRaises(OpenAIHTTPError) as caught:
                _http_post_json("synthetic-secret", request)
        diagnostic = caught.exception.diagnostic
        self.assertEqual(diagnostic["httpStatus"], 400)
        self.assertEqual(diagnostic["xRequestID"], "req_http_audit")
        self.assertEqual(base64.b64decode(diagnostic["responseBodyBase64"]), body)
        self.assertEqual(
            diagnostic["decodedJSONError"]["error"]["code"], "invalid_json_schema"
        )
        self.assertIsNotNone(diagnostic["requestBodySha256"])
        self.assertIsNotNone(diagnostic["structuredSchemaSha256"])

    def test_non_json_http_body_is_preserved_without_false_decoding(self) -> None:
        """A non-JSON provider body remains auditable as bytes and safe text."""

        body = b"upstream rejected request"
        error = self._raise_http_error(body, "text/plain")
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=error,
        ):
            with self.assertRaises(OpenAIHTTPError) as caught:
                _http_post_json("synthetic-secret", {"model": "gpt-5.6-sol"})
        diagnostic = caught.exception.diagnostic
        self.assertEqual(base64.b64decode(diagnostic["responseBodyBase64"]), body)
        self.assertEqual(diagnostic["responseBodyText"], body.decode("utf-8"))
        self.assertIsNone(diagnostic["decodedJSONError"])

    def test_credentials_are_redacted_and_request_headers_are_never_recorded(self) -> None:
        """Even a hostile reflected body cannot place the API key in diagnostics."""

        credential = "synthetic-secret"
        body = b'{"error":{"message":"reflected synthetic-secret"}}'
        error = self._raise_http_error(body, "application/json")
        with patch(
            "src.extraction.llm.publications.openai_provider.urlopen",
            side_effect=error,
        ):
            with self.assertRaises(OpenAIHTTPError) as caught:
                _http_post_json(credential, {"model": "gpt-5.6-sol"})
        encoded = json.dumps(caught.exception.diagnostic, sort_keys=True)
        self.assertNotIn(credential, encoded)
        self.assertTrue(caught.exception.diagnostic["credentialRedactionApplied"])
        self.assertFalse(caught.exception.diagnostic["requestHeadersPreserved"])


class StructuredLivePipelineTests(unittest.TestCase):
    """Exercise one mocked structured response through the unchanged M1 pipeline."""

    def test_valid_structured_response_traverses_and_replays(self) -> None:
        """One mocked call reaches valid usable output with deterministic replay."""

        output_text = VALID_FIXTURE.read_text(encoding="utf-8")
        call_count = 0

        def transport(_key: str, body: Mapping[str, Any]) -> dict[str, Any]:
            """Assert strict configuration and return one completed response."""

            nonlocal call_count
            call_count += 1
            self.assertTrue(body["text"]["format"]["strict"])
            self.assertNotIn("tools", body)
            return synthetic_response(output_text)

        with tempfile.TemporaryDirectory() as temporary_directory:
            result = run_structured_live_smoke(
                "synthetic-secret",
                output_dir=Path(temporary_directory),
                transport=transport,
            )
        self.assertEqual(call_count, 1)
        self.assertEqual(result["parserResult"]["parseStatus"], "parsed")
        self.assertEqual(result["validation"]["envelopeStatus"], "valid")
        self.assertEqual(len(result["usablePipelineOutput"]["candidateNodes"]), 1)
        self.assertTrue(result["replayByteIdentical"])


if __name__ == "__main__":
    unittest.main()
