"""Single dev-document smoke runtime; plan creation never authorizes dispatch.

There is no test dispatcher, retry, resume dispatch, or CLI execution command.
Future execution requires two separate, exact scope-bound researcher records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import tarfile
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.request import Request

from . import scierc_external_anchor as anchor
from .openai_provider import OPENAI_RESPONSES_URL, extract_model_output, validate_provider_response


VERSION = "scierc-single-dev-smoke/0.1.0"
TIMEOUT_SECONDS = 180
SCOPE = "scierc_frozen_dev_first_document_mechanical_smoke"
RUNTIME_ROOT = anchor.RUNTIME_ROOT / "single_dev_smoke_v0.1.0"
PLAN_PATH = anchor.PROJECT_ROOT / "data/curation/papers/m2/scierc_step9_preflight/scierc_smoke_plan_v0.1.0.json"


class SmokeRuntimeError(ValueError):
    """Reject scope, approval, identity, or existing-state conflicts before dispatch."""


@dataclass(frozen=True)
class TransportReply:
    """Raw response bytes with credential-free HTTP response identifiers."""

    body: bytes
    http_status: int
    request_id: str | None = None


class PartialTransportFailure(Exception):
    """Carry partial response bytes without an unsafe exception message."""

    def __init__(self, partial: bytes, http_status: int | None = None, request_id: str | None = None) -> None:
        """Retain incomplete HTTP body evidence for durable recording."""
        super().__init__("partial HTTP response")
        self.partial = partial
        self.http_status = http_status
        self.request_id = request_id


Transport = Callable[[str, bytes, int], TransportReply]


def exact_post(api_key: str, body: bytes, timeout: int) -> TransportReply:
    """Send one exact prepared body with a 180-second socket timeout; never retry.

    urllib's timeout is a blocking socket-operation timeout, not a guaranteed
    total deadline. HTTP error bodies are returned as evidence. No redirect is
    followed: a redirect is a terminal HTTP response, not a second request.
    """
    from urllib.request import HTTPRedirectHandler, build_opener

    class NoRedirect(HTTPRedirectHandler):
        """Prevent redirect-driven resends of an authorized one-POST request."""

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            """Return no redirected request."""
            return None

    request = Request(OPENAI_RESPONSES_URL, data=body,
                      headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
                      method="POST")
    def read_reply(response, status):
        """Retain observed response identity even if the body read is interrupted."""
        request_id = response.headers.get("x-request-id")
        try:
            return TransportReply(response.read(), status, request_id)
        except IncompleteRead as exc:
            raise PartialTransportFailure(exc.partial, status, request_id) from None

    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            return read_reply(response, response.status)
    except HTTPError as exc:
        return read_reply(exc, exc.code)


def runtime_identity() -> str:
    """Bind this runtime and the exact compatible primitives it consumes."""
    paths = [Path(__file__), Path(anchor.__file__), Path(anchor.__file__).with_name("openai_provider.py"),
             Path(anchor.__file__).with_name("request_builder.py")]
    return anchor.sha256_bytes(anchor.canonical_json({str(p.relative_to(anchor.PROJECT_ROOT)):
        anchor.sha256_bytes(p.read_bytes()) for p in paths}))


def prepare_smoke(archive_path: Path = anchor.ARCHIVE_PATH) -> tuple[dict[str, Any], anchor.SciERCDocument, bytes]:
    """Verify the frozen archive/dev split; select only JSONL line 1 without gold."""
    source = anchor.source_freeze()
    with archive_path.open("rb") as handle:
        archive_hash = anchor._sha256_stream(handle)
    if archive_hash != source["officialArchive"]["sha256"]:
        raise SmokeRuntimeError("ARCHIVE_IDENTITY_MISMATCH")
    spec = source["splits"]["dev"]
    with tarfile.open(archive_path, "r:gz") as archive:
        payload = archive.extractfile(spec["path"]).read()
    if anchor.sha256_bytes(payload) != spec["sha256"]:
        raise SmokeRuntimeError("DEV_SPLIT_IDENTITY_MISMATCH")
    lines = payload.splitlines()
    if len(lines) != spec["documentCount"]:
        raise SmokeRuntimeError("DEV_SPLIT_COUNT_MISMATCH")
    document = anchor.parse_processed_document(json.loads(lines[0]), include_gold=False)
    body = anchor.build_request_body(document)
    body_bytes = anchor.canonical_json(body)
    projection = anchor.canonical_json(anchor.inference_projection(document))
    schema = anchor.canonical_json(body["text"]["format"]["schema"])
    plan = {
        "version": VERSION, "scope": SCOPE, "split": "dev", "documentID": document.document_id,
        "selectionRule": "first JSONL document in frozen dev split, file order, line 1",
        "status": "NOT AUTHORIZED FOR PROVIDER EXECUTION", "runtimeAccepted": False,
        "researcherLiveAuthorization": False, "plannedSmokeGenerationPosts": 1,
        "separateOfficialTestLogicalRequests": 100, "concurrency": 1, "automaticRedispatch": False,
        "source": {"archiveSha256": archive_hash, "splitPath": spec["path"], "splitSha256": spec["sha256"],
            "sourceFreezeSha256": anchor.sha256_bytes(anchor.SOURCE_FREEZE_PATH.read_bytes()),
            "adapterFreezeSha256": anchor.sha256_bytes(anchor.ADAPTER_FREEZE_PATH.read_bytes()),
            "sourceProjectionSha256": anchor.sha256_bytes(projection)},
        "bodySha256": anchor.sha256_bytes(body_bytes), "schemaSha256": anchor.sha256_bytes(schema),
        "promptSha256": anchor.sha256_bytes(anchor.PROMPT_PATH.read_bytes()),
        "configurationSha256": anchor.sha256_bytes(anchor.CONFIG_PATH.read_bytes()),
        "runtimeSha256": runtime_identity(),
        "settings": {k: body[k] for k in ("model", "reasoning", "max_output_tokens", "store")},
        "executionMode": "synchronous_stateless", "transportTimeoutSeconds": TIMEOUT_SECONDS,
        "timeoutMeaning": "blocking socket-operation timeout; delivery/processing unknown on transport failure; never resend",
        "accounting": {"sourceTokenCount": len(document.tokens), "sourceProjectionUtf8Bytes": len(projection),
            "sourceTextUtf8Bytes": len(" ".join(document.tokens).encode()),
            "repeatedPromptUtf8Bytes": len(anchor.PROMPT_PATH.read_bytes()), "repeatedSchemaUtf8Bytes": len(schema),
            "completeRequestUtf8Bytes": len(body_bytes), "interpretation": "byte proxies, not provider token counts",
            "tokenizer": None, "estimatedProviderInputTokens": None, "observedUsage": None,
            "observedLatency": None, "apiPricing": None, "expectedCost": None, "accountRateLimits": None,
            "reasoningTokenRule": "output_tokens already includes reasoning; retain details without adding twice"},
    }
    plan["requestID"] = "scierc-dev-smoke-" + plan["bodySha256"]
    plan["planSha256"] = anchor.sha256_bytes(anchor.canonical_json(plan))
    return plan, document, body_bytes


def approval_binding(plan: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Describe required approval scope without granting either approval."""
    return {"scope": SCOPE, "planSha256": plan["planSha256"], "bodySha256": plan["bodySha256"],
            "runtimeSha256": plan["runtimeSha256"], "runtimeRoot": str(root.resolve()), "maxGenerationPosts": 1}


def check_approvals(plan: Mapping[str, Any], root: Path, acceptance: Mapping[str, Any] | None,
                    authorization: Mapping[str, Any] | None) -> None:
    """Require separate explicit acceptance and live authorization before any I/O dispatch."""
    binding = approval_binding(plan, root)
    for record, kind in ((acceptance, "runtime_acceptance"), (authorization, "live_authorization")):
        if not isinstance(record, Mapping) or record.get("kind") != kind or record.get("approved") is not True:
            raise SmokeRuntimeError("MISSING_" + kind.upper())
        if record.get("binding") != binding or not isinstance(record.get("recordID"), str) or not record["recordID"].strip():
            raise SmokeRuntimeError("MISMATCHED_" + kind.upper())
    if authorization.get("acceptanceRecordID") != acceptance["recordID"] or authorization["recordID"] == acceptance["recordID"]:
        raise SmokeRuntimeError("ACCEPTANCE_AUTHORIZATION_LINK_MISMATCH")


def _utc() -> str:
    """Return an actual UTC event timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sync_directory(path: Path) -> None:
    """Flush directory entries so durable dispatch claims survive process interruption."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_new(path: Path, data: bytes) -> None:
    """Persist exact bytes exclusively; never overwrite an existing artifact."""
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory(path.parent)


def _json_new(path: Path, data: Mapping[str, Any]) -> None:
    """Persist canonical JSON in a new artifact only."""
    _write_new(path, anchor.canonical_json(data))


def _strict_json(raw: bytes) -> Any:
    """Reject duplicate keys and non-JSON numbers instead of repairing output."""
    def pairs(items):
        """Reject duplicate object keys."""
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def constant(value):
        """Reject NaN and infinity."""
        raise ValueError("NON_JSON_NUMBER")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def execute_smoke(plan: Mapping[str, Any], *, acceptance: Mapping[str, Any] | None = None,
                  authorization: Mapping[str, Any] | None = None, api_key: str = "",
                  root: Path = RUNTIME_ROOT, transport: Transport | None = None) -> dict[str, Any]:
    """Execute at most one approved dev POST; never accept a caller-supplied document.

    Every entry reconstructs line 1 of the hash-verified dev split. Existing run
    directories fail closed, including pre-dispatch partial writes and terminal
    failures. The root is included in both approvals. No authorization is created.
    """
    expected, document, body_bytes = prepare_smoke()
    if dict(plan) != expected:
        raise SmokeRuntimeError("SMOKE_PLAN_IDENTITY_MISMATCH")
    check_approvals(plan, root, acceptance, authorization)
    if not api_key:
        raise SmokeRuntimeError("CREDENTIAL_UNAVAILABLE")
    if transport is None and root.resolve() != RUNTIME_ROOT.resolve():
        raise SmokeRuntimeError("LIVE_RUNTIME_NAMESPACE_MISMATCH")
    root.parent.mkdir(parents=True, exist_ok=True)
    try:
        root.mkdir()  # Atomic claim: competing processes cannot both send.
    except FileExistsError:
        raise SmokeRuntimeError("EXISTING_RUNTIME_STATE_NO_REDISPATCH") from None
    _sync_directory(root.parent)
    _write_new(root / "provider_request.json", body_bytes)
    _json_new(root / "identity.json", {"plan": dict(plan), "acceptance": acceptance, "authorization": authorization})
    started_at, started = _utc(), time.monotonic_ns()
    _json_new(root / "dispatch_started.json", {"requestID": plan["requestID"], "bodySha256": plan["bodySha256"],
        "startedAt": started_at, "monotonicStartedNs": started, "maxGenerationPosts": 1,
        "delivery": "unknown_until_response", "timeoutSeconds": TIMEOUT_SECONDS})
    result: dict[str, Any] = {"requestID": plan["requestID"], "requestedModel": plan["settings"]["model"],
        "startedAt": started_at, "returnedModel": None, "responseID": None, "providerRequestID": None,
        "usage": None, "timeoutSeconds": TIMEOUT_SECONDS, "automaticRedispatch": False}
    secret = api_key.encode()

    def preserve(name: str, raw: bytes) -> bytes:
        """Preserve evidence, redacting only a credential echo with explicit notice."""
        if secret in raw:
            raw = raw.replace(secret, b"[CREDENTIAL_REDACTED]")
            result["credentialEchoRedacted"] = True
        _write_new(root / name, raw)
        return raw

    try:
        reply = (exact_post if transport is None else transport)(api_key, body_bytes, TIMEOUT_SECONDS)
    except Exception as exc:
        if isinstance(exc, PartialTransportFailure):
            preserve("partial_provider_response.bin", exc.partial)
            result.update(httpStatus=exc.http_status,
                          providerRequestID=exc.request_id.replace(api_key, "[CREDENTIAL_REDACTED]") if exc.request_id else None)
        # Exception messages can contain credentials: never persist them.
        result.update(terminalStatus="transport_failure", delivery="unknown", errorType=type(exc).__name__)
        if isinstance(exc, PartialTransportFailure) and exc.http_status is not None:
            result["delivery"] = "http_response_received_partial_body"
    else:
        raw = preserve("provider_response.bin", reply.body)
        safe_request_id = reply.request_id.replace(api_key, "[CREDENTIAL_REDACTED]") if reply.request_id else None
        result.update(httpStatus=reply.http_status, providerRequestID=safe_request_id,
                      delivery="http_response_received")
        stage = "provider_json_invalid"
        try:
            response = _strict_json(raw)
            if not isinstance(response, dict):
                raise ValueError("PROVIDER_RESPONSE_NOT_OBJECT")
            _json_new(root / "provider_response.json", response)
            result.update(returnedModel=response.get("model"), responseID=response.get("id"),
                          usage=response.get("usage"), providerCreatedAt=response.get("created_at"),
                          providerCompletedAt=response.get("completed_at"))
            # Preserve all text fragments even for refusals/incomplete/invalid responses.
            fragments = []
            for item in response.get("output", []):
                if isinstance(item, dict) and isinstance(item.get("content"), list):
                    for content in item["content"]:
                        if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                            fragments.append(content["text"].encode())
            for index, fragment in enumerate(fragments):
                preserve(f"model_output_part_{index:03d}.bin", fragment)
            if len(fragments) == 1:
                preserve("raw_model_output.bin", fragments[0])
            if not 200 <= reply.http_status < 300:
                result.update(terminalStatus="http_failure", processing="unknown_or_failed_http_response")
            else:
                stage = "provider_response_invalid"
                if response.get("model") != plan["settings"]["model"]:
                    stage = "returned_model_mismatch"
                elif response.get("status") != "completed" or response.get("incomplete_details") is not None:
                    stage = "incomplete_or_failed_response"
                elif response.get("error") is not None:
                    stage = "provider_error"
                validate_provider_response(response)
                stage = "refusal_or_missing_output"
                if any(isinstance(item, dict) and isinstance(item.get("content"), list) and
                       any(isinstance(content, dict) and content.get("type") == "refusal" for content in item["content"])
                       for item in response.get("output", [])):
                    raise ValueError("PROVIDER_REFUSAL")
                output = extract_model_output(response)
                stage = "model_json_invalid"
                prediction = _strict_json(output)
                stage = "prediction_invalid"
                anchor.validate_prediction(prediction, document)
                _json_new(root / "validated_prediction.json", prediction)
                result["terminalStatus"] = "completed_valid"
        except Exception as exc:
            result.update(terminalStatus="http_failure" if not 200 <= reply.http_status < 300 else stage,
                          errorType=type(exc).__name__)
            if isinstance(exc, anchor.SciERCAnchorError):
                result["validationFailure"] = str(exc).replace(api_key, "[CREDENTIAL_REDACTED]")
    result.update(completedAt=_utc(), elapsedMilliseconds=(time.monotonic_ns() - started) / 1_000_000)
    _json_new(root / "terminal.json", result)
    return result


def main() -> None:
    """Write reviewable plan metadata only; there is deliberately no execute flag."""
    plan, _, _ = prepare_smoke()
    data = json.dumps(plan, indent=2, sort_keys=True).encode() + b"\n"
    if PLAN_PATH.exists():
        if PLAN_PATH.read_bytes() != data:
            raise SmokeRuntimeError("SMOKE_PLAN_ARTIFACT_CONFLICT")
    else:
        _write_new(PLAN_PATH, data)
    print(json.dumps({"documentID": plan["documentID"], "planSha256": plan["planSha256"],
                      "bodySha256": plan["bodySha256"], "status": plan["status"]}))


if __name__ == "__main__":
    main()
