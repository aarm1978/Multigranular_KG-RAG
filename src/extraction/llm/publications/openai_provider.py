"""Minimal stateless OpenAI Responses API adapter for Publication development.

The adapter intentionally supports one provider and one configured model. It sends no
tools, retrieval configuration, or conversation identifier. The model-authored output
is returned as exact UTF-8 bytes separately from provider response metadata.
"""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Mapping
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.extraction.llm.publications.request_builder import (
    PROJECT_ROOT,
    canonical_json,
    sha256_bytes,
)


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
PROVIDER_NAME = "OpenAI"
REQUESTED_MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "medium"
MAX_OUTPUT_TOKENS = 4096
STORE = False
PROVIDER_ADAPTER_VERSION = "0.2.0"
RESPONSE_FORMAT = "textual_json"
STRICT_RESPONSE_FORMAT = "json_schema_strict"
STRUCTURED_OUTPUT_NAME = "publication_model_authorable_payload"


class OpenAIProviderError(RuntimeError):
    """Report a safe provider configuration, transport, or response failure."""


class OpenAIHTTPError(OpenAIProviderError):
    """Carry credential-free diagnostics for one failed HTTP provider call."""

    def __init__(self, diagnostic: Mapping[str, Any]) -> None:
        """Initialize a concise exception while retaining its safe audit record."""

        super().__init__(f"OpenAI API HTTP error ({diagnostic['httpStatus']})")
        self.diagnostic = deepcopy(dict(diagnostic))


class OpenAIProviderResponseError(OpenAIProviderError):
    """Carry an auditable provider response that must not enter semantic processing."""

    def __init__(
        self,
        failure_code: str,
        response: Mapping[str, Any],
        response_record: Mapping[str, Any],
    ) -> None:
        """Initialize a safe failure without exposing response content in its message."""

        super().__init__(f"OpenAI provider response rejected: {failure_code}")
        self.failure_code = failure_code
        self.response = deepcopy(dict(response))
        self.response_record = deepcopy(dict(response_record))


def load_openai_api_key(
    environ: Mapping[str, str] | None = None,
    *,
    env_path: Path = PROJECT_ROOT / ".env",
) -> str:
    """Load ``OPENAI_API_KEY`` from the process or the repository's ignored .env.

    The value is never included in an exception. The small parser supports the existing
    repository convention without modifying the file or requiring python-dotenv.
    """

    source = os.environ if environ is None else environ
    process_value = source.get("OPENAI_API_KEY", "").strip()
    if process_value:
        return process_value
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.removeprefix("export ").strip() != "OPENAI_API_KEY":
            continue
        candidate = value.strip()
        if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in "\"'":
            candidate = candidate[1:-1]
        if candidate:
            return candidate
    raise OpenAIProviderError("OPENAI_API_KEY is unavailable")


def provider_input_projection(request: Mapping[str, Any]) -> dict[str, Any]:
    """Select the bounded semantic request fields produced by the M1 request builder."""

    return {
        "purpose": request["purpose"],
        "runID": request["runID"],
        "sourcePublicationID": request["sourcePublicationID"],
        "sourceArtifactID": request["sourceArtifactID"],
        "primarySourceUnitID": request["primarySourceUnitID"],
        "contextSourceUnitIDs": list(request["contextSourceUnitIDs"]),
        "requestScope": request["requestScope"],
        "includedCompleteSection": request["includedCompleteSection"],
        "extractionChannel": request["extractionChannel"],
        "eligibleOperationalTargetIDs": list(request["eligibleOperationalTargetIDs"]),
        "sourceUnit": request["sourceUnit"],
        "deterministicEndpoints": list(request["deterministicEndpoints"]),
        "acceptedLocalCandidateEndpoints": list(request["acceptedLocalCandidateEndpoints"]),
        "deferredRecords": list(request["deferredRecords"]),
        "targetDefinitions": list(request["targetDefinitions"]),
    }


def build_provider_input(request: Mapping[str, Any]) -> bytes:
    """Build the exact UTF-8 prompt and bounded request input sent to OpenAI."""

    prompt = str(request["prompt"]["text"])
    separator = "\n\nBounded trusted development request JSON:\n"
    return prompt.encode("utf-8") + separator.encode("utf-8") + canonical_json(
        provider_input_projection(request)
    )


def build_responses_api_request(
    input_bytes: bytes,
    *,
    model_authorable_schema: Mapping[str, Any] | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    background: bool = False,
) -> dict[str, Any]:
    """Build the one-model, no-tools, stateless Responses API request body."""

    body: dict[str, Any] = {
        "model": REQUESTED_MODEL,
        "reasoning": {"effort": REASONING_EFFORT},
        "input": input_bytes.decode("utf-8"),
        "max_output_tokens": max_output_tokens,
        "store": STORE,
    }
    if background:
        body["background"] = True
    if model_authorable_schema is not None:
        body["text"] = {
            "format": {
                "type": "json_schema",
                "name": STRUCTURED_OUTPUT_NAME,
                "strict": True,
                "schema": deepcopy(dict(model_authorable_schema)),
            }
        }
    return body


def _http_post_json(api_key: str, body: Mapping[str, Any]) -> dict[str, Any]:
    """POST one JSON request to OpenAI and return the decoded response object."""

    request_body = canonical_json(body)
    request = Request(
        OPENAI_RESPONSES_URL,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_body = exc.read()
        api_key_bytes = api_key.encode("utf-8")
        credential_redacted = bool(api_key_bytes and api_key_bytes in response_body)
        safe_response_body = (
            response_body.replace(api_key_bytes, b"[REDACTED]")
            if api_key_bytes
            else response_body
        )
        decoded_error: Any = None
        response_text: str | None = None
        try:
            response_text = safe_response_body.decode("utf-8")
            candidate = json.loads(response_text)
            if isinstance(candidate, (dict, list)):
                decoded_error = candidate
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        text_format = body.get("text", {}).get("format", {})
        structured_schema = (
            text_format.get("schema") if isinstance(text_format, Mapping) else None
        )
        headers = exc.headers
        diagnostic = {
            "diagnosticSchemaVersion": "0.1.0",
            "artifactRole": "provider_http_error_diagnostic",
            "provider": PROVIDER_NAME,
            "providerEndpoint": OPENAI_RESPONSES_URL,
            "httpStatus": exc.code,
            "xRequestID": headers.get("x-request-id") if headers is not None else None,
            "contentType": headers.get("content-type") if headers is not None else None,
            "requestBodySha256": sha256_bytes(request_body),
            "structuredSchemaSha256": (
                sha256_bytes(canonical_json(structured_schema))
                if structured_schema is not None
                else None
            ),
            "responseBodyByteCount": len(response_body),
            "responseBodySha256": sha256_bytes(response_body),
            "responseBodyBase64": base64.b64encode(safe_response_body).decode("ascii"),
            "responseBodyText": response_text,
            "decodedJSONError": decoded_error,
            "credentialRedactionApplied": credential_redacted,
            "requestHeadersPreserved": False,
        }
        raise OpenAIHTTPError(diagnostic) from None
    except (URLError, TimeoutError):
        raise OpenAIProviderError("OpenAI API transport error") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OpenAIProviderError("OpenAI API returned an invalid JSON response") from None
    if not isinstance(decoded, dict):
        raise OpenAIProviderError("OpenAI API response must be a JSON object")
    return decoded


def _http_get_response_json(api_key: str, response_id: str) -> dict[str, Any]:
    """Retrieve one background Response without changing its provider state."""

    request = Request(
        f"{OPENAI_RESPONSES_URL}/{quote(response_id, safe='')}",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=180) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise OpenAIProviderError(
            f"OpenAI background retrieval HTTP error ({exc.code})"
        ) from None
    except (URLError, TimeoutError):
        raise OpenAIProviderError("OpenAI background retrieval transport error") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OpenAIProviderError(
            "OpenAI background retrieval returned invalid JSON"
        ) from None
    if not isinstance(decoded, dict):
        raise OpenAIProviderError("OpenAI background retrieval must be a JSON object")
    return decoded


def extract_model_output(response: Mapping[str, Any]) -> bytes:
    """Extract the exact model-authored output text from one Responses API response."""

    output_texts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, Mapping) and content.get("type") == "output_text":
                text = content.get("text")
                if not isinstance(text, str):
                    raise OpenAIProviderError("OpenAI output_text content is not a string")
                output_texts.append(text)
    if len(output_texts) != 1:
        raise OpenAIProviderError("OpenAI response must contain exactly one output_text payload")
    return output_texts[0].encode("utf-8")


def _created_at_iso(value: Any) -> str:
    """Convert a provider epoch timestamp or ISO string to a schema-valid UTC value."""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and value:
        return value
    raise OpenAIProviderError("OpenAI response omitted created_at")


def normalized_token_usage(response: Mapping[str, Any]) -> dict[str, int | None]:
    """Normalize actual provider token counts for the frozen M1 metadata shape."""

    usage = response.get("usage", {})
    if not isinstance(usage, Mapping):
        usage = {}
    return {
        "inputTokens": usage.get("input_tokens"),
        "outputTokens": usage.get("output_tokens"),
        "totalTokens": usage.get("total_tokens"),
    }


def provider_response_record(
    response: Mapping[str, Any],
    request_body: Mapping[str, Any],
    raw_output: bytes | None,
    *,
    execution_mode: str = "synchronous",
) -> dict[str, Any]:
    """Create a credential-free API response audit record separate from model output."""

    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    text_format = request_body.get("text", {}).get("format", {})
    structured_schema = text_format.get("schema")
    return {
        "recordSchemaVersion": "0.1.0",
        "artifactRole": "provider_api_response_metadata",
        "developmentOnly": True,
        "liveOpenAIOutput": True,
        "notAnnotation": True,
        "notGold": True,
        "notFormalEvaluation": True,
        "provider": PROVIDER_NAME,
        "responseID": response.get("id"),
        "returnedModel": response.get("model"),
        "status": response.get("status"),
        "createdAt": _created_at_iso(response.get("created_at")),
        "usage": deepcopy(usage),
        "inputTokens": usage.get("input_tokens"),
        "outputTokens": usage.get("output_tokens"),
        "reasoningTokens": (
            usage.get("output_tokens_details", {}).get("reasoning_tokens")
            if isinstance(usage.get("output_tokens_details"), Mapping)
            else None
        ),
        "incompleteDetails": deepcopy(response.get("incomplete_details")),
        "error": deepcopy(response.get("error")),
        "requestSettings": {
            "endpoint": OPENAI_RESPONSES_URL,
            "model": request_body["model"],
            "reasoningEffort": request_body["reasoning"]["effort"],
            "maxOutputTokens": request_body["max_output_tokens"],
            "store": request_body["store"],
            "executionMode": execution_mode,
            "tools": "none",
            "webSearch": False,
            "fileSearch": False,
            "codeInterpreter": False,
            "externalRetrieval": False,
            "conversationState": False,
            "responseFormat": (
                STRICT_RESPONSE_FORMAT if structured_schema is not None else RESPONSE_FORMAT
            ),
            "structuredOutputName": text_format.get("name"),
            "structuredOutputStrict": text_format.get("strict"),
            "modelAuthorableSchemaSha256": (
                sha256_bytes(canonical_json(structured_schema))
                if structured_schema is not None
                else None
            ),
        },
        "retryCount": 0,
        "rawModelOutputSha256": (
            sha256_bytes(raw_output) if raw_output is not None else None
        ),
        "rawProviderResponseSha256": sha256_bytes(canonical_json(response)),
    }


def validate_provider_response(response: Mapping[str, Any]) -> None:
    """Require a completed, error-free, exact-model semantic provider response."""

    if response.get("status") != "completed":
        raise ValueError("STATUS_NOT_COMPLETED")
    if response.get("error") is not None:
        raise ValueError("PROVIDER_ERROR_PRESENT")
    if response.get("incomplete_details") is not None:
        raise ValueError("INCOMPLETE_DETAILS_PRESENT")
    if response.get("model") != REQUESTED_MODEL:
        raise ValueError("RETURNED_MODEL_MISMATCH")


def bind_live_response_metadata(
    request: Mapping[str, Any],
    response_record: Mapping[str, Any],
    *,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> dict[str, Any]:
    """Bind actual live provider metadata into a copy of the trusted M1 request."""

    bound = deepcopy(dict(request))
    bound["offlineResponseMetadata"] = {
        "provider": PROVIDER_NAME,
        "modelName": REQUESTED_MODEL,
        "modelVersion": response_record["returnedModel"],
        "generationParameters": {
            "temperature": None,
            "topP": None,
            "seed": None,
            "maxOutputTokens": max_output_tokens,
            "responseFormat": "structured_json",
        },
        "tokenUsage": {
            "inputTokens": response_record["inputTokens"],
            "outputTokens": response_record["outputTokens"],
            "totalTokens": response_record["usage"].get("total_tokens"),
        },
        "costUSD": None,
        "retryCount": response_record["retryCount"],
        "responseCreatedAt": response_record["createdAt"],
    }
    bound.pop("requestInputSha256", None)
    bound["requestInputSha256"] = sha256_bytes(canonical_json(bound))
    return bound


Transport = Callable[[str, Mapping[str, Any]], dict[str, Any]]
ResponseRetrieveTransport = Callable[[str, str], dict[str, Any]]
ResponseCreatedCallback = Callable[[Mapping[str, Any], Mapping[str, Any]], None]


def call_openai_responses(
    api_key: str,
    input_bytes: bytes,
    *,
    model_authorable_schema: Mapping[str, Any] | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    transport: Transport = _http_post_json,
) -> tuple[bytes, dict[str, Any]]:
    """Perform one Responses API call and return output bytes plus safe metadata."""

    raw_output, record, _response = call_openai_responses_detailed(
        api_key,
        input_bytes,
        model_authorable_schema=model_authorable_schema,
        max_output_tokens=max_output_tokens,
        transport=transport,
    )
    return raw_output, record


def call_openai_responses_detailed(
    api_key: str,
    input_bytes: bytes,
    *,
    model_authorable_schema: Mapping[str, Any] | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    transport: Transport = _http_post_json,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Perform one guarded call and also return the exact decoded API response."""

    if not api_key:
        raise OpenAIProviderError("OPENAI_API_KEY is unavailable")
    body = build_responses_api_request(
        input_bytes,
        model_authorable_schema=model_authorable_schema,
        max_output_tokens=max_output_tokens,
    )
    response = transport(api_key, body)
    record = provider_response_record(response, body, None)
    try:
        validate_provider_response(response)
    except ValueError as exc:
        raise OpenAIProviderResponseError(str(exc), response, record) from None
    try:
        raw_output = extract_model_output(response)
    except OpenAIProviderError:
        raise OpenAIProviderResponseError(
            "MODEL_OUTPUT_UNAVAILABLE", response, record
        ) from None
    record = provider_response_record(response, body, raw_output)
    return raw_output, record, deepcopy(dict(response))


def call_openai_background_responses_detailed(
    api_key: str,
    input_bytes: bytes,
    *,
    model_authorable_schema: Mapping[str, Any] | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    creation_transport: Transport = _http_post_json,
    retrieval_transport: ResponseRetrieveTransport = _http_get_response_json,
    on_response_created: ResponseCreatedCallback | None = None,
    poll_interval_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Create, durably expose, and poll one background Response to a terminal state."""

    if not api_key:
        raise OpenAIProviderError("OPENAI_API_KEY is unavailable")
    body = build_responses_api_request(
        input_bytes,
        model_authorable_schema=model_authorable_schema,
        max_output_tokens=max_output_tokens,
        background=True,
    )
    created = creation_transport(api_key, body)
    response_id = created.get("id")
    if not isinstance(response_id, str) or not response_id:
        raise OpenAIProviderError("OpenAI background creation omitted response id")
    if on_response_created is not None:
        on_response_created(created, body)
    response = _poll_background_response(
        api_key, response_id, initial_response=created,
        retrieval_transport=retrieval_transport, poll_interval_seconds=poll_interval_seconds,
        sleep=sleep,
    )
    return _completed_background_response(response, body)


def _poll_background_response(
    api_key: str,
    response_id: str,
    *,
    initial_response: Mapping[str, Any] | None = None,
    retrieval_transport: ResponseRetrieveTransport = _http_get_response_json,
    poll_interval_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Poll one created background response until it leaves active provider states."""

    response = (
        deepcopy(dict(initial_response)) if initial_response is not None
        else retrieval_transport(api_key, response_id)
    )
    while response.get("status") in {"queued", "in_progress"}:
        sleep(poll_interval_seconds)
        response = retrieval_transport(api_key, response_id)
    return response


def _completed_background_response(
    response: Mapping[str, Any], body: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Validate a terminal background response and retain exact output when complete."""

    record = provider_response_record(
        response, body, None, execution_mode="background"
    )
    try:
        validate_provider_response(response)
    except ValueError as exc:
        raise OpenAIProviderResponseError(str(exc), response, record) from None
    try:
        raw_output = extract_model_output(response)
    except OpenAIProviderError:
        raise OpenAIProviderResponseError(
            "MODEL_OUTPUT_UNAVAILABLE", response, record
        ) from None
    record = provider_response_record(
        response, body, raw_output, execution_mode="background"
    )
    return raw_output, record, deepcopy(dict(response))


def resume_openai_background_response_detailed(
    api_key: str,
    response_id: str,
    input_bytes: bytes,
    *,
    model_authorable_schema: Mapping[str, Any] | None = None,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    retrieval_transport: ResponseRetrieveTransport = _http_get_response_json,
    poll_interval_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """Resume polling an already-created background response by its persisted ID."""

    if not api_key:
        raise OpenAIProviderError("OPENAI_API_KEY is unavailable")
    body = build_responses_api_request(
        input_bytes,
        model_authorable_schema=model_authorable_schema,
        max_output_tokens=max_output_tokens,
        background=True,
    )
    response = _poll_background_response(
        api_key, response_id, retrieval_transport=retrieval_transport,
        poll_interval_seconds=poll_interval_seconds, sleep=sleep,
    )
    return _completed_background_response(response, body)
