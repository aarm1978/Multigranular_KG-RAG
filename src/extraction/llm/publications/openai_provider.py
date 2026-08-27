"""Minimal stateless OpenAI Responses API adapter for Publication development.

The adapter intentionally supports one provider and one configured model. It sends no
tools, retrieval configuration, or conversation identifier. The model-authored output
is returned as exact UTF-8 bytes separately from provider response metadata.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping
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
PROVIDER_ADAPTER_VERSION = "0.1.0"
RESPONSE_FORMAT = "textual_json"


class OpenAIProviderError(RuntimeError):
    """Report a safe provider configuration, transport, or response failure."""


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


def build_responses_api_request(input_bytes: bytes) -> dict[str, Any]:
    """Build the one-model, no-tools, stateless Responses API request body."""

    return {
        "model": REQUESTED_MODEL,
        "reasoning": {"effort": REASONING_EFFORT},
        "input": input_bytes.decode("utf-8"),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": STORE,
    }


def _http_post_json(api_key: str, body: Mapping[str, Any]) -> dict[str, Any]:
    """POST one JSON request to OpenAI and return the decoded response object."""

    request = Request(
        OPENAI_RESPONSES_URL,
        data=canonical_json(body),
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
        raise OpenAIProviderError(f"OpenAI API HTTP error ({exc.code})") from None
    except (URLError, TimeoutError):
        raise OpenAIProviderError("OpenAI API transport error") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OpenAIProviderError("OpenAI API returned an invalid JSON response") from None
    if not isinstance(decoded, dict):
        raise OpenAIProviderError("OpenAI API response must be a JSON object")
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
    response: Mapping[str, Any], request_body: Mapping[str, Any], raw_output: bytes
) -> dict[str, Any]:
    """Create a credential-free API response audit record separate from model output."""

    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
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
            "tools": "none",
            "webSearch": False,
            "fileSearch": False,
            "codeInterpreter": False,
            "externalRetrieval": False,
            "conversationState": False,
            "responseFormat": RESPONSE_FORMAT,
        },
        "retryCount": 0,
        "rawModelOutputSha256": sha256_bytes(raw_output),
        "rawProviderResponseSha256": sha256_bytes(canonical_json(response)),
    }


def bind_live_response_metadata(
    request: Mapping[str, Any], response_record: Mapping[str, Any]
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
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
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


def call_openai_responses(
    api_key: str,
    input_bytes: bytes,
    *,
    transport: Transport = _http_post_json,
) -> tuple[bytes, dict[str, Any]]:
    """Perform one Responses API call and return output bytes plus safe metadata."""

    if not api_key:
        raise OpenAIProviderError("OPENAI_API_KEY is unavailable")
    body = build_responses_api_request(input_bytes)
    response = transport(api_key, body)
    raw_output = extract_model_output(response)
    record = provider_response_record(response, body, raw_output)
    return raw_output, record
